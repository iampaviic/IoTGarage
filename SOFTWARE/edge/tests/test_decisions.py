import itertools

import pytest

from edge_service.decisions import AlprInfo, Thresholds, decide_entry, decide_exit

T = Thresholds(accept=0.85, retry=0.60, max_attempts=3)


def entry(conf, status="OK", plate="ZG1234AB", attempt=1, spots=3, inside=False, allowlist=False, allowed=True):
    return decide_entry(AlprInfo(status, plate, conf), T, attempt, spots, inside, allowlist, allowed)


def test_confident_reading_with_free_spot_is_granted():
    d = entry(0.9)
    assert (d.decision, d.reason) == ("GRANTED", "AUTHORIZED")


@pytest.mark.parametrize("conf,expected", [
    (0.86, "GRANTED"),
    (0.85, "GRANTED"),
    (0.84, "RETRY"),
    (0.60, "RETRY"),
    (0.59, "MANUAL_REQUIRED"),
    (0.0, "MANUAL_REQUIRED"),
])
def test_confidence_bands(conf, expected):
    assert entry(conf).decision == expected


def test_retry_turns_into_manual_after_max_attempts():
    assert entry(0.7, attempt=2).decision == "RETRY"
    assert entry(0.7, attempt=3).decision == "MANUAL_REQUIRED"


def test_no_plate_retries_then_manual():
    assert entry(0.0, status="NO_PLATE", plate=None).decision == "RETRY"
    d = entry(0.0, status="NO_PLATE", plate=None, attempt=3)
    assert (d.decision, d.reason) == ("MANUAL_REQUIRED", "NO_PLATE")


def test_denials():
    assert entry(0.95, spots=0).reason == "GARAGE_FULL"
    assert entry(0.95, inside=True).reason == "ALREADY_INSIDE"
    assert entry(0.95, allowlist=True, allowed=False).reason == "NOT_ON_ALLOWLIST"
    assert entry(0.95, allowlist=True, allowed=True).decision == "GRANTED"


def test_exit():
    assert decide_exit(AlprInfo("OK", "ZG1234AB", 0.9), T, 1, True).decision == "GRANTED"
    d = decide_exit(AlprInfo("OK", "ZG1234AB", 0.9), T, 1, False)
    assert (d.decision, d.reason) == ("DENIED", "NO_ACTIVE_SESSION")
    assert decide_exit(AlprInfo("OK", "ZG1234AB", 0.7), T, 1, True).decision == "RETRY"


def test_never_opens_below_accept_threshold():
    """Project success criterion: the gate is never opened automatically when the
    confidence is below the agreed threshold - checked over a grid of all inputs."""
    statuses = ["OK", "LOW_CONFIDENCE", "INVALID_FORMAT", "NO_PLATE", "CAMERA_ERROR"]
    confidences = [i / 100.0 for i in range(0, 101)]
    for status, conf, attempt, spots, inside, allowlist, allowed, has_session in itertools.product(
            statuses, confidences, (1, 2, 3, 4), (0, 1, 5), (False, True), (False, True), (False, True), (False, True)):
        e = decide_entry(AlprInfo(status, "ZG1234AB", conf), T, attempt, spots, inside, allowlist, allowed)
        x = decide_exit(AlprInfo(status, "ZG1234AB", conf), T, attempt, has_session)
        if conf < T.accept:
            assert not e.opens_gate and not x.opens_gate, (status, conf)


def test_invalid_thresholds():
    with pytest.raises(ValueError):
        Thresholds(accept=0.5, retry=0.7)
