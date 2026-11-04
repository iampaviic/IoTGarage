"""Command line tool for the session database.

    parking-sessions --db garage.db list --active
    parking-sessions --db garage.db show S-20261019-083112-4F2A
    parking-sessions --db garage.db stats --days 7
    parking-sessions --db garage.db allow add ZG1234AB --label "Testno vozilo 1"
    parking-sessions --db garage.db generate --days 14 --per-day 40
    parking-sessions --db garage.db export sessions.csv
    parking-sessions --db garage.db purge --days 30

The database path defaults to $GARAGE_DB or ./garage.db and the pricing
profile to $PRICING_PROFILE (real|demo).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List

from parking_sessions.generator import generate_sessions
from parking_sessions.models import Session
from parking_sessions.pricing import PricingPolicy
from parking_sessions.store import SessionStore


def _fmt_duration(seconds) -> str:
    if seconds is None:
        return "-"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return "%d:%02d:%02d" % (h, m, s)


def _fmt_price(session: Session) -> str:
    return "-" if session.price is None else "%.2f %s" % (session.price, session.currency)


def _print_table(sessions: List[Session]) -> None:
    print("%-26s %-10s %-9s %-20s %-20s %9s %10s %-4s %-6s" % (
        "ID", "PLATE", "STATUS", "ENTRY (UTC)", "EXIT (UTC)", "DURATION", "PRICE", "SPOT", "MODE"))
    for s in sessions:
        print("%-26s %-10s %-9s %-20s %-20s %9s %10s %-4s %-6s" % (
            s.id, s.plate, s.status, s.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            s.exit_time.strftime("%Y-%m-%d %H:%M:%S") if s.exit_time else "-",
            _fmt_duration(s.duration_s), _fmt_price(s), s.spot_id or "-", s.entry_mode))
    print("(%d rows)" % len(sessions))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="parking-sessions", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.environ.get("GARAGE_DB", "garage.db"))
    ap.add_argument("--pricing", choices=["real", "demo"], default=os.environ.get("PRICING_PROFILE", "real"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list sessions")
    p.add_argument("--active", action="store_true")
    p.add_argument("--plate")
    p.add_argument("--limit", type=int, default=30)

    p = sub.add_parser("show", help="show one session")
    p.add_argument("session_id")

    p = sub.add_parser("stats", help="statistics for the last N days")
    p.add_argument("--days", type=int, default=7)

    p = sub.add_parser("open", help="manually open a session (testing)")
    p.add_argument("plate")
    p = sub.add_parser("close", help="manually close the active session of a plate (testing)")
    p.add_argument("plate")

    p = sub.add_parser("allow", help="manage the allow-list")
    p.add_argument("action", choices=["add", "remove", "list"])
    p.add_argument("plate", nargs="?")
    p.add_argument("--label")
    p.add_argument("--days", type=int, help="valid for N days")

    p = sub.add_parser("events", help="local audit log")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--type")

    p = sub.add_parser("generate", help="insert fictional test sessions")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--per-day", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)

    p = sub.add_parser("export", help="export all sessions to CSV")
    p.add_argument("path")

    p = sub.add_parser("purge", help="delete finished sessions/events older than N days")
    p.add_argument("--days", type=int, required=True)

    args = ap.parse_args(argv)
    pricing = PricingPolicy.demo() if args.pricing == "demo" else PricingPolicy.real()
    store = SessionStore(args.db, pricing)

    if args.cmd == "list":
        rows = store.active_sessions() if args.active else store.history(plate=args.plate, limit=args.limit)
        _print_table(rows)
    elif args.cmd == "show":
        s = store.get(args.session_id)
        if s is None:
            print("not found", file=sys.stderr)
            return 1
        for k, v in s.to_row().items():
            print("%-17s %s" % (k, v))
        if s.status == "ACTIVE":
            print("%-17s %.2f %s" % ("price_if_now", store.quote_cents(s.id) / 100.0, s.currency))
    elif args.cmd == "stats":
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        st = store.stats(since=since)
        print("pricing:          %s" % pricing.describe())
        print("closed sessions:  %d" % st.closed_sessions)
        print("active sessions:  %d" % st.active_sessions)
        print("avg duration:     %s" % _fmt_duration(st.avg_duration_s))
        print("revenue:          %.2f %s" % (st.revenue_cents / 100.0, pricing.currency))
        print("manual entries:   %d" % st.manual_entries)
        print("entries per hour (UTC):")
        peak = max(st.entries_per_hour.values() or [1])
        for h in range(24):
            n = st.entries_per_hour.get(h, 0)
            print("  %02d  %4d %s" % (h, n, "#" * int(40 * n / peak)))
    elif args.cmd == "open":
        s = store.open_session(args.plate, mode="MANUAL", note="cli")
        print("opened", s.id)
    elif args.cmd == "close":
        s = store.find_active(args.plate)
        if s is None:
            print("no active session for", args.plate, file=sys.stderr)
            return 1
        s = store.close_session(s.id, mode="MANUAL")
        print("closed %s duration=%s price=%s" % (s.id, _fmt_duration(s.duration_s), _fmt_price(s)))
    elif args.cmd == "allow":
        if args.action == "list":
            for row in store.allowed_plates():
                print("%-10s %-25s %s .. %s" % (row["plate"], row["label"] or "", row["valid_from"] or "",
                                                 row["valid_until"] or ""))
        elif not args.plate:
            ap.error("plate required")
        elif args.action == "add":
            until = datetime.now(timezone.utc) + timedelta(days=args.days) if args.days else None
            store.allow(args.plate, label=args.label, valid_until=until)
            print("allowed", args.plate)
        else:
            print("removed" if store.disallow(args.plate) else "not on list", args.plate)
    elif args.cmd == "events":
        for e in reversed(store.events(limit=args.limit, type=args.type)):
            print(e["ts"], e["type"], e["plate"] or "-", e["session_id"] or "-", e["details"])
    elif args.cmd == "generate":
        rows = generate_sessions(days=args.days, per_day=args.per_day, pricing=pricing, seed=args.seed)
        print("inserted %d sessions" % store.import_sessions(rows))
    elif args.cmd == "export":
        rows = store.history(limit=10 ** 9)
        with open(args.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(Session.to_row(rows[0]).keys()) if rows else ["id"])
            w.writeheader()
            for s in reversed(rows):
                w.writerow(s.to_row())
        print("exported %d sessions to %s" % (len(rows), args.path))
    elif args.cmd == "purge":
        print("deleted %d rows" % store.purge(args.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
