from datetime import datetime, timedelta, timezone

import pytest

from parking_sessions import (
    ActiveSessionExists,
    PricingPolicy,
    SessionNotActive,
    SessionNotFound,
    SessionStore,
    normalize_plate_key,
)
from parking_sessions.cli import main as cli_main
from parking_sessions.generator import generate_sessions

T0 = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def store():
    s = SessionStore(":memory:", PricingPolicy.real())
    yield s
    s.close()


# --------------------------------------------------------------- pricing
@pytest.mark.parametrize("minutes,expected_cents", [
    (0, 0),
    (14, 0),
    (15, 0),          # exactly 15 min is still free
    (15.02, 150),     # 15 min 1 s -> first started hour
    (60, 150),
    (60.02, 300),
    (75, 300),
    (24 * 60, 1500),  # daily cap
    (25 * 60, 1650),  # cap for the first day + 1 started hour
])
def test_real_pricing(minutes, expected_cents):
    assert PricingPolicy.real().price_cents(minutes * 60) == expected_cents


def test_demo_pricing_bills_minutes_as_hours():
    demo = PricingPolicy.demo()
    assert demo.price_cents(10) == 0          # 10 s -> 10 billed min -> free
    assert demo.price_cents(120) == 300       # 2 real min -> 2 billed h


def test_negative_duration_rejected():
    with pytest.raises(ValueError):
        PricingPolicy().price_cents(-1)


# --------------------------------------------------------------- lifecycle
def test_full_session_lifecycle(store):
    s = store.open_session("zg 1234-ab", entry_time=T0, confidence=0.91)
    assert s.plate == "ZG1234AB"
    assert s.status == "ACTIVE"
    assert store.find_active("ZG1234AB").id == s.id

    closed = store.close_session(s.id, exit_time=T0 + timedelta(minutes=77), confidence=0.88)
    assert closed.status == "CLOSED"
    assert closed.duration_s == 77 * 60
    assert closed.price_cents == 300
    assert closed.price == 3.0
    assert closed.exit_confidence == 0.88
    assert store.find_active("ZG1234AB") is None


def test_session_event_payload_matches_contract(store):
    s = store.open_session("ZG1234AB", entry_time=T0, confidence=0.9)
    s = store.close_session(s.id, exit_time=T0 + timedelta(minutes=20))
    event = s.to_event("SESSION_CLOSED")
    assert event["entryTime"] == "2026-10-19T08:00:00Z"
    assert event["exitTime"] == "2026-10-19T08:20:00Z"
    assert event["durationS"] == 1200 and event["price"] == 1.5
    try:
        from garage_contract import validate
    except ImportError:
        pytest.skip("garage_contract not installed")
    validate("session_event", event)


def test_vehicle_cannot_enter_twice(store):
    s = store.open_session("ZG1234AB", entry_time=T0)
    with pytest.raises(ActiveSessionExists) as exc:
        store.open_session("ZG1234AB", entry_time=T0 + timedelta(minutes=1))
    assert exc.value.session_id == s.id


def test_close_twice_fails(store):
    s = store.open_session("ZG1234AB", entry_time=T0)
    store.close_session(s.id, exit_time=T0 + timedelta(minutes=5))
    with pytest.raises(SessionNotActive):
        store.close_session(s.id, exit_time=T0 + timedelta(minutes=6))


def test_close_unknown_session(store):
    with pytest.raises(SessionNotFound):
        store.close_session("S-nope")


def test_exit_before_entry_rejected(store):
    s = store.open_session("ZG1234AB", entry_time=T0)
    with pytest.raises(ValueError):
        store.close_session(s.id, exit_time=T0 - timedelta(seconds=1))


def test_naive_datetime_rejected(store):
    with pytest.raises(ValueError):
        store.open_session("ZG1234AB", entry_time=datetime(2026, 1, 1))


def test_reentry_after_exit_is_new_session(store):
    a = store.open_session("ST555B", entry_time=T0)
    store.close_session(a.id, exit_time=T0 + timedelta(minutes=30))
    b = store.open_session("ST555B", entry_time=T0 + timedelta(hours=1))
    assert a.id != b.id
    assert len(store.history(plate="ST555B")) == 2


def test_similar_plate_suggestion(store):
    store.open_session("ZG1234AB", entry_time=T0)
    assert [s.plate for s in store.find_active_similar("ZG1234A8")] == ["ZG1234AB"]
    assert store.find_active_similar("RI9999XX") == []


def test_cancel_and_assign_spot(store):
    s = store.open_session("ZG1234AB", entry_time=T0)
    store.assign_spot(s.id, "P03")
    assert store.get(s.id).spot_id == "P03"
    c = store.cancel_session(s.id, note="test vehicle removed by hand")
    assert c.status == "CANCELLED"
    assert store.count_active() == 0


def test_quote_for_active_session(store):
    s = store.open_session("ZG1234AB", entry_time=T0)
    assert store.quote_cents(s.id, at=T0 + timedelta(minutes=90)) == 300


# --------------------------------------------------------------- queries
def test_history_and_stats(store):
    for i, plate in enumerate(["ZG1111A", "ZG2222B", "ZG3333C"]):
        s = store.open_session(plate, entry_time=T0 + timedelta(hours=i))
        store.close_session(s.id, exit_time=T0 + timedelta(hours=i, minutes=30))
    store.open_session("ZG4444D", entry_time=T0 + timedelta(hours=5), mode="MANUAL")

    assert len(store.history()) == 4
    assert len(store.history(status="CLOSED")) == 3
    assert len(store.history(since=T0 + timedelta(hours=2))) == 2

    st = store.stats()
    assert st.closed_sessions == 3
    assert st.active_sessions == 1
    assert st.avg_duration_s == 1800
    assert st.revenue_cents == 3 * 150
    assert st.manual_entries == 1
    assert st.entries_per_hour == {8: 1, 9: 1, 10: 1, 13: 1}


# --------------------------------------------------------------- allow-list
def test_allow_list_with_validity(store):
    store.allow("ZG1234AB", label="Testno vozilo", valid_from=T0, valid_until=T0 + timedelta(days=1))
    assert store.is_allowed("ZG 1234-AB", at=T0 + timedelta(hours=1))
    assert not store.is_allowed("ZG1234AB", at=T0 - timedelta(seconds=1))
    assert not store.is_allowed("ZG1234AB", at=T0 + timedelta(days=1))
    assert not store.is_allowed("RI1A")
    store.allow("ZG1234AB")  # re-adding replaces the validity window
    assert store.is_allowed("ZG1234AB", at=T0 + timedelta(days=30))
    assert store.disallow("ZG1234AB")
    assert not store.is_allowed("ZG1234AB")


# --------------------------------------------------------------- audit + privacy
def test_event_log(store):
    store.log_event("MANUAL_OVERRIDE", plate="ZG1234AB", operator="dezurni", note="OCR failed")
    ev = store.events()[0]
    assert ev["type"] == "MANUAL_OVERRIDE"
    assert ev["details"] == {"operator": "dezurni", "note": "OCR failed"}


def test_purge_keeps_active_sessions(store):
    old = store.open_session("ZG1111A", entry_time=T0 - timedelta(days=40))
    store.close_session(old.id, exit_time=T0 - timedelta(days=40) + timedelta(hours=1))
    still_inside = store.open_session("ZG2222B", entry_time=T0 - timedelta(days=40))
    store.log_event("TEST", ts=T0 - timedelta(days=40))
    deleted = store.purge(30, now=T0)
    assert deleted == 2
    assert store.get(old.id) is None
    assert store.get(still_inside.id) is not None


# --------------------------------------------------------------- misc
def test_normalize_plate_key():
    assert normalize_plate_key(" vž 123-a ") == "VZ123A"
    with pytest.raises(ValueError):
        normalize_plate_key(" - ")


def test_generator_is_deterministic_and_consistent(store):
    a = generate_sessions(days=3, per_day=20, end=T0, seed=1)
    b = generate_sessions(days=3, per_day=20, end=T0, seed=1)
    assert [s.id for s in a] == [s.id for s in b]
    assert store.import_sessions(a) == len(a)
    for s in a:
        if s.status == "CLOSED":
            assert s.exit_time > s.entry_time
            assert s.price_cents == PricingPolicy().price_cents(s.duration_s)
    assert store.count_active() == 2


def test_file_database_persists(tmp_path):
    path = str(tmp_path / "garage.db")
    s1 = SessionStore(path)
    sid = s1.open_session("ZG1234AB", entry_time=T0).id
    s1.close()
    s2 = SessionStore(path)
    assert s2.get(sid).plate == "ZG1234AB"
    s2.close()


def test_cli_smoke(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    assert cli_main(["--db", db, "generate", "--days", "2", "--per-day", "10"]) == 0
    assert cli_main(["--db", db, "allow", "add", "ZG1234AB", "--label", "Test"]) == 0
    assert cli_main(["--db", db, "open", "ZG1234AB"]) == 0
    assert cli_main(["--db", db, "close", "ZG1234AB"]) == 0
    assert cli_main(["--db", db, "stats", "--days", "3"]) == 0
    assert cli_main(["--db", db, "list", "--limit", "5"]) == 0
    assert cli_main(["--db", db, "export", str(tmp_path / "out.csv")]) == 0
    out = capsys.readouterr().out
    assert "inserted" in out and "closed" in out and "exported" in out
