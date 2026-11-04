from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@dataclass
class Session:
    id: str
    plate: str
    status: str  # ACTIVE | CLOSED | CANCELLED
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_s: Optional[int] = None
    price_cents: Optional[int] = None
    currency: str = "EUR"
    entry_confidence: Optional[float] = None
    exit_confidence: Optional[float] = None
    entry_mode: str = "AUTO"
    exit_mode: Optional[str] = None
    spot_id: Optional[str] = None
    note: Optional[str] = None

    @property
    def price(self) -> Optional[float]:
        return None if self.price_cents is None else round(self.price_cents / 100.0, 2)

    def to_event(self, event_type: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Build a garage/session/event payload (see communication contract)."""
        ts = timestamp or self.exit_time or self.entry_time
        return {
            "eventType": event_type,
            "sessionId": self.id,
            "plate": self.plate,
            "entryTime": to_iso(self.entry_time),
            "exitTime": to_iso(self.exit_time),
            "durationS": self.duration_s,
            "price": self.price,
            "currency": self.currency,
            "entryMode": self.entry_mode,
            "exitMode": self.exit_mode,
            "entryConfidence": self.entry_confidence,
            "exitConfidence": self.exit_confidence,
            "timestamp": to_iso(ts),
        }

    def to_row(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plate": self.plate,
            "status": self.status,
            "entry_time": to_iso(self.entry_time),
            "exit_time": to_iso(self.exit_time),
            "duration_s": self.duration_s,
            "price": self.price,
            "currency": self.currency,
            "entry_confidence": self.entry_confidence,
            "exit_confidence": self.exit_confidence,
            "entry_mode": self.entry_mode,
            "exit_mode": self.exit_mode,
            "spot_id": self.spot_id,
            "note": self.note,
        }


@dataclass
class Stats:
    closed_sessions: int = 0
    active_sessions: int = 0
    avg_duration_s: Optional[float] = None
    revenue_cents: int = 0
    entries_per_hour: Dict[int, int] = field(default_factory=dict)  # UTC hour -> count
    manual_entries: int = 0
