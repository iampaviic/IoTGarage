"""Parking sessions: the business record of every vehicle entry and exit.

Owner: osoba 8. Used by the edge access-control service (osoba 6).
Only depends on the Python standard library (sqlite3).
"""

from parking_sessions.errors import (
    ActiveSessionExists,
    SessionError,
    SessionNotActive,
    SessionNotFound,
)
from parking_sessions.models import Session, Stats
from parking_sessions.pricing import PricingPolicy
from parking_sessions.store import SessionStore, normalize_plate_key

__all__ = [
    "ActiveSessionExists",
    "PricingPolicy",
    "Session",
    "SessionError",
    "SessionNotActive",
    "SessionNotFound",
    "SessionStore",
    "Stats",
    "normalize_plate_key",
]
