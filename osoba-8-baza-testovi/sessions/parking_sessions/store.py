"""SQLite-backed store for parking sessions, the allow-list and the local audit log.

    store = SessionStore("garage.db", PricingPolicy.demo())
    s = store.open_session("ZG1234AB", confidence=0.91)
    ...
    s = store.close_session(s.id, confidence=0.88)
    print(s.duration_s, s.price)

All times are timezone-aware UTC datetimes; they are stored as ISO 8601 text
('2026-10-19T08:31:12Z') so the database is readable with any SQLite tool.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from parking_sessions.errors import ActiveSessionExists, SessionNotActive, SessionNotFound
from parking_sessions.models import Session, Stats, from_iso, to_iso
from parking_sessions.pricing import PricingPolicy

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS sessions (
    id               TEXT PRIMARY KEY,
    plate            TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED', 'CANCELLED')),
    entry_time       TEXT NOT NULL,
    exit_time        TEXT,
    duration_s       INTEGER,
    price_cents      INTEGER,
    currency         TEXT NOT NULL DEFAULT 'EUR',
    entry_confidence REAL,
    exit_confidence  REAL,
    entry_mode       TEXT NOT NULL DEFAULT 'AUTO' CHECK (entry_mode IN ('AUTO', 'MANUAL')),
    exit_mode        TEXT CHECK (exit_mode IN ('AUTO', 'MANUAL')),
    spot_id          TEXT,
    note             TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
-- a vehicle can be inside only once
CREATE UNIQUE INDEX IF NOT EXISTS ux_sessions_active_plate ON sessions(plate) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS ix_sessions_entry_time ON sessions(entry_time);

CREATE TABLE IF NOT EXISTS allowed_plates (
    plate       TEXT PRIMARY KEY,
    label       TEXT,            -- fictional label only, never a real person's name
    valid_from  TEXT,
    valid_until TEXT,
    created_at  TEXT NOT NULL
);

-- local audit log: decisions, manual interventions, alerts (synced to ThingsBoard by MQTT)
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    type       TEXT NOT NULL,
    plate      TEXT,
    session_id TEXT,
    details    TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_ts ON events(ts);
"""

_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def normalize_plate_key(plate: str) -> str:
    """Canonical key used in the database: uppercase, letters and digits only."""
    fold = plate.upper().translate(str.maketrans("ČĆŠŽĐ", "CCSZD"))
    key = _NON_ALNUM.sub("", fold)
    if not key:
        raise ValueError("empty plate")
    return key


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return _now()
    if dt.tzinfo is None:
        raise ValueError("naive datetime; pass timezone-aware UTC datetimes")
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class SessionStore:
    def __init__(self, path: str = ":memory:", pricing: Optional[PricingPolicy] = None) -> None:
        self.path = path
        self.pricing = pricing or PricingPolicy()
        if path != ":memory:":
            parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(parent, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")  # CLI can read while the service writes
        self._migrate()

    @classmethod
    def from_env(cls) -> "SessionStore":
        return cls(os.environ.get("GARAGE_DB", "garage.db"), PricingPolicy.from_env())

    def close(self) -> None:
        self._conn.close()

    # ----------------------------------------------------------------- schema
    def _migrate(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            row = self._conn.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                self._conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] > SCHEMA_VERSION:
                raise RuntimeError("database schema v%s is newer than this code (v%s)" % (row["version"], SCHEMA_VERSION))

    # --------------------------------------------------------------- sessions
    def open_session(
        self,
        plate: str,
        entry_time: Optional[datetime] = None,
        confidence: Optional[float] = None,
        mode: str = "AUTO",
        note: Optional[str] = None,
    ) -> Session:
        plate = normalize_plate_key(plate)
        entry = _utc(entry_time)
        existing = self.find_active(plate)
        if existing is not None:
            raise ActiveSessionExists(plate, existing.id)
        session = Session(
            id="S-%s-%s" % (entry.strftime("%Y%m%d-%H%M%S"), secrets.token_hex(2).upper()),
            plate=plate,
            status="ACTIVE",
            entry_time=entry,
            currency=self.pricing.currency,
            entry_confidence=confidence,
            entry_mode=mode,
            note=note,
        )
        now = to_iso(_now())
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO sessions (id, plate, status, entry_time, currency, entry_confidence,"
                    " entry_mode, note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (session.id, plate, "ACTIVE", to_iso(entry), session.currency, confidence, mode, note, now, now),
                )
            except sqlite3.IntegrityError:
                # raced with another writer; report the session that won
                other = self.find_active(plate)
                raise ActiveSessionExists(plate, other.id if other else "?")
        return session

    def get(self, session_id: str) -> Optional[Session]:
        row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row(row) if row else None

    def find_active(self, plate: str) -> Optional[Session]:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE plate = ? AND status = 'ACTIVE'", (normalize_plate_key(plate),)
        ).fetchone()
        return self._row(row) if row else None

    def find_active_similar(self, plate: str, max_distance: int = 1) -> List[Session]:
        """Active sessions whose plate differs by at most max_distance characters.
        Used only to *suggest* a match at the exit; the caller decides."""
        key = normalize_plate_key(plate)
        return [s for s in self.active_sessions() if _levenshtein(key, s.plate) <= max_distance]

    def close_session(
        self,
        session_id: str,
        exit_time: Optional[datetime] = None,
        confidence: Optional[float] = None,
        mode: str = "AUTO",
    ) -> Session:
        session = self.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        if session.status != "ACTIVE":
            raise SessionNotActive("session %s is %s" % (session_id, session.status))
        exit_dt = _utc(exit_time)
        if exit_dt < session.entry_time:
            raise ValueError("exit time before entry time")
        duration = int((exit_dt - session.entry_time).total_seconds())
        price = self.pricing.price_cents(duration)
        with self._lock:
            cur = self._conn.execute(
                "UPDATE sessions SET status='CLOSED', exit_time=?, duration_s=?, price_cents=?,"
                " exit_confidence=?, exit_mode=?, updated_at=? WHERE id=? AND status='ACTIVE'",
                (to_iso(exit_dt), duration, price, confidence, mode, to_iso(_now()), session_id),
            )
            if cur.rowcount != 1:
                raise SessionNotActive("session %s was closed concurrently" % session_id)
        return self.get(session_id)  # type: ignore[return-value]

    def cancel_session(self, session_id: str, note: str) -> Session:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE sessions SET status='CANCELLED', note=?, updated_at=? WHERE id=? AND status='ACTIVE'",
                (note, to_iso(_now()), session_id),
            )
        if cur.rowcount != 1:
            raise SessionNotActive(session_id)
        return self.get(session_id)  # type: ignore[return-value]

    def assign_spot(self, session_id: str, spot_id: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE sessions SET spot_id=?, updated_at=? WHERE id=?",
                               (spot_id, to_iso(_now()), session_id))

    def quote_cents(self, session_id: str, at: Optional[datetime] = None) -> int:
        """Price the session would cost if it ended at `at` (default: now)."""
        session = self.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        end = _utc(at)
        return self.pricing.price_cents(max(0, int((end - session.entry_time).total_seconds())))

    def active_sessions(self) -> List[Session]:
        rows = self._conn.execute("SELECT * FROM sessions WHERE status='ACTIVE' ORDER BY entry_time").fetchall()
        return [self._row(r) for r in rows]

    def count_active(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM sessions WHERE status='ACTIVE'").fetchone()[0]

    def history(
        self,
        plate: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Session]:
        sql, args = "SELECT * FROM sessions WHERE 1=1", []  # type: str, List[Any]
        if plate:
            sql += " AND plate = ?"
            args.append(normalize_plate_key(plate))
        if since:
            sql += " AND entry_time >= ?"
            args.append(to_iso(_utc(since)))
        if until:
            sql += " AND entry_time < ?"
            args.append(to_iso(_utc(until)))
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY entry_time DESC LIMIT ?"
        args.append(limit)
        return [self._row(r) for r in self._conn.execute(sql, args).fetchall()]

    def stats(self, since: Optional[datetime] = None, until: Optional[datetime] = None) -> Stats:
        where, args = " WHERE 1=1", []  # type: str, List[Any]
        if since:
            where += " AND entry_time >= ?"
            args.append(to_iso(_utc(since)))
        if until:
            where += " AND entry_time < ?"
            args.append(to_iso(_utc(until)))
        row = self._conn.execute(
            "SELECT"
            " SUM(status='CLOSED') AS closed, SUM(status='ACTIVE') AS active,"
            " AVG(CASE WHEN status='CLOSED' THEN duration_s END) AS avg_d,"
            " COALESCE(SUM(CASE WHEN status='CLOSED' THEN price_cents END), 0) AS revenue,"
            " SUM(entry_mode='MANUAL') AS manual"
            " FROM sessions" + where, args).fetchone()
        per_hour = {
            int(r[0]): r[1]
            for r in self._conn.execute(
                "SELECT CAST(substr(entry_time, 12, 2) AS INTEGER) AS h, COUNT(*) FROM sessions"
                + where + " GROUP BY h ORDER BY h", args)
        }
        return Stats(
            closed_sessions=row["closed"] or 0,
            active_sessions=row["active"] or 0,
            avg_duration_s=row["avg_d"],
            revenue_cents=row["revenue"] or 0,
            entries_per_hour=per_hour,
            manual_entries=row["manual"] or 0,
        )

    # -------------------------------------------------------------- allow-list
    def allow(self, plate: str, label: Optional[str] = None,
              valid_from: Optional[datetime] = None, valid_until: Optional[datetime] = None) -> None:
        with self._lock:
            self._conn.execute(
                # INSERT OR REPLACE instead of UPSERT: Ubuntu 18.04 (Jetson) ships SQLite 3.22
                "INSERT OR REPLACE INTO allowed_plates (plate, label, valid_from, valid_until, created_at)"
                " VALUES (?,?,?,?,?)",
                (normalize_plate_key(plate), label,
                 to_iso(valid_from) if valid_from else None,
                 to_iso(valid_until) if valid_until else None, to_iso(_now())),
            )

    def disallow(self, plate: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM allowed_plates WHERE plate=?", (normalize_plate_key(plate),))
        return cur.rowcount > 0

    def is_allowed(self, plate: str, at: Optional[datetime] = None) -> bool:
        row = self._conn.execute("SELECT * FROM allowed_plates WHERE plate=?",
                                 (normalize_plate_key(plate),)).fetchone()
        if row is None:
            return False
        when = _utc(at)
        if row["valid_from"] and when < from_iso(row["valid_from"]):
            return False
        if row["valid_until"] and when >= from_iso(row["valid_until"]):
            return False
        return True

    def allowed_plates(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM allowed_plates ORDER BY plate")]

    # ---------------------------------------------------------------- events
    def log_event(self, type: str, plate: Optional[str] = None, session_id: Optional[str] = None,
                  ts: Optional[datetime] = None, **details: Any) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (ts, type, plate, session_id, details) VALUES (?,?,?,?,?)",
                (to_iso(_utc(ts)), type, plate, session_id,
                 json.dumps(details, ensure_ascii=False) if details else None),
            )
        return int(cur.lastrowid)

    def events(self, limit: int = 50, type: Optional[str] = None) -> List[Dict[str, Any]]:
        sql, args = "SELECT * FROM events", []  # type: str, List[Any]
        if type:
            sql += " WHERE type = ?"
            args.append(type)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        out = []
        for r in self._conn.execute(sql, args):
            d = dict(r)
            d["details"] = json.loads(d["details"]) if d["details"] else {}
            out.append(d)
        return out

    # --------------------------------------------------------------- privacy
    def purge(self, older_than_days: int, now: Optional[datetime] = None) -> int:
        """Delete finished sessions and events older than N days (data minimisation).
        ACTIVE sessions are never deleted. Returns number of deleted rows."""
        cutoff = to_iso(_utc(now) - timedelta(days=older_than_days))
        with self._lock:
            a = self._conn.execute(
                "DELETE FROM sessions WHERE status != 'ACTIVE' AND COALESCE(exit_time, entry_time) < ?",
                (cutoff,)).rowcount
            b = self._conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,)).rowcount
        return a + b

    # ----------------------------------------------------------------- utils
    def import_sessions(self, sessions: Iterable[Session]) -> int:
        """Bulk insert (used by the test-data generator)."""
        now = to_iso(_now())
        n = 0
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                for s in sessions:
                    self._conn.execute(
                        "INSERT INTO sessions (id, plate, status, entry_time, exit_time, duration_s, price_cents,"
                        " currency, entry_confidence, exit_confidence, entry_mode, exit_mode, spot_id, note,"
                        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (s.id, s.plate, s.status, to_iso(s.entry_time), to_iso(s.exit_time), s.duration_s,
                         s.price_cents, s.currency, s.entry_confidence, s.exit_confidence, s.entry_mode,
                         s.exit_mode, s.spot_id, s.note, now, now))
                    n += 1
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return n

    @staticmethod
    def _row(row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            plate=row["plate"],
            status=row["status"],
            entry_time=from_iso(row["entry_time"]),  # type: ignore[arg-type]
            exit_time=from_iso(row["exit_time"]),
            duration_s=row["duration_s"],
            price_cents=row["price_cents"],
            currency=row["currency"],
            entry_confidence=row["entry_confidence"],
            exit_confidence=row["exit_confidence"],
            entry_mode=row["entry_mode"],
            exit_mode=row["exit_mode"],
            spot_id=row["spot_id"],
            note=row["note"],
        )
