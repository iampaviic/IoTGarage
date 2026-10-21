"""Pure decision rules for entry and exit (no MQTT, no database, easy to test).

Confidence policy from the project plan:
    confidence >= 0.85        accept automatically
    0.60 <= confidence < 0.85 take a new photo (RETRY) up to max_attempts
    confidence < 0.60         no automatic decision -> MANUAL_REQUIRED
The gate is NEVER opened automatically below the accept threshold; the
invariant is checked in code (assert) and by tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Thresholds:
    accept: float = 0.85
    retry: float = 0.60
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not 0.0 < self.retry <= self.accept <= 1.0:
            raise ValueError("need 0 < retry <= accept <= 1")


@dataclass(frozen=True)
class AlprInfo:
    status: str                    # OK | NO_PLATE | LOW_CONFIDENCE | INVALID_FORMAT | CAMERA_ERROR
    plate: Optional[str]
    confidence: float              # OCR confidence 0..1


@dataclass(frozen=True)
class Decision:
    decision: str                  # GRANTED | DENIED | RETRY | MANUAL_REQUIRED
    reason: str

    @property
    def opens_gate(self) -> bool:
        return self.decision == "GRANTED"


def _reading_problem(alpr: AlprInfo, t: Thresholds, attempt: int) -> Optional[Decision]:
    """Shared part of entry and exit: is the reading good enough to decide at all?"""
    can_retry = attempt < t.max_attempts
    if alpr.status in ("NO_PLATE", "CAMERA_ERROR") or not alpr.plate:
        reason = "CAMERA_ERROR" if alpr.status == "CAMERA_ERROR" else "NO_PLATE"
        return Decision("RETRY" if can_retry else "MANUAL_REQUIRED", reason)
    if alpr.status == "INVALID_FORMAT":
        return Decision("RETRY" if can_retry else "MANUAL_REQUIRED", "INVALID_FORMAT")
    if alpr.confidence < t.retry:
        return Decision("MANUAL_REQUIRED", "LOW_CONFIDENCE")
    if alpr.confidence < t.accept:
        return Decision("RETRY" if can_retry else "MANUAL_REQUIRED", "LOW_CONFIDENCE")
    return None


def decide_entry(alpr: AlprInfo, t: Thresholds, attempt: int, available_spots: int,
                 already_inside: bool, allowlist_policy: bool, allowed: bool) -> Decision:
    problem = _reading_problem(alpr, t, attempt)
    if problem is not None:
        return problem
    if already_inside:
        decision = Decision("DENIED", "ALREADY_INSIDE")
    elif allowlist_policy and not allowed:
        decision = Decision("DENIED", "NOT_ON_ALLOWLIST")
    elif available_spots <= 0:
        decision = Decision("DENIED", "GARAGE_FULL")
    else:
        decision = Decision("GRANTED", "AUTHORIZED")
    assert not decision.opens_gate or alpr.confidence >= t.accept
    return decision


def decide_exit(alpr: AlprInfo, t: Thresholds, attempt: int, has_active_session: bool) -> Decision:
    problem = _reading_problem(alpr, t, attempt)
    if problem is not None:
        return problem
    decision = Decision("GRANTED", "AUTHORIZED") if has_active_session else Decision("DENIED", "NO_ACTIVE_SESSION")
    assert not decision.opens_gate or alpr.confidence >= t.accept
    return decision
