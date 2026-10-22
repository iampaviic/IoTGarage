"""UTC time helpers. All messages and the database use ISO 8601 UTC with 'Z'.

Local time is only ever shown in user interfaces (ThingsBoard does that).
datetime.fromisoformat() cannot parse 'Z' before Python 3.11, so we parse
manually to stay compatible with Python 3.8 on the edge devices.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

_ISO_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Format as '2026-10-19T08:31:12Z' (second precision, always UTC)."""
    if dt.tzinfo is None:
        raise ValueError("naive datetime; use timezone-aware UTC datetimes")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_iso() -> str:
    return to_iso(utc_now())


def parse_iso(value: str) -> datetime:
    """Parse an ISO 8601 timestamp with 'Z' or an explicit offset."""
    m = _ISO_RE.match(value)
    if not m:
        raise ValueError("not an ISO 8601 UTC timestamp: %r" % (value,))
    year, month, day, hour, minute, second, frac, tz = m.groups()
    micro = int((frac or "0").ljust(6, "0"))
    dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), micro)
    if tz == "Z":
        return dt.replace(tzinfo=timezone.utc)
    sign = 1 if tz[0] == "+" else -1
    offset_min = sign * (int(tz[1:3]) * 60 + int(tz[4:6]))
    return dt.replace(tzinfo=timezone(timedelta(minutes=offset_min))).astimezone(timezone.utc)


def to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)
