"""End-to-end test of the whole system (simulators + edge service + real MQTT broker).

Needs the `mosquitto` binary (apt install mosquitto); skipped otherwise.
    pytest osoba-1-voditelj/integracija/tests -v
"""

import os
import shutil
import socket
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from garage_contract import MqttSettings, topics  # noqa: E402
from scenarij import Driver  # noqa: E402
from simulacija import System  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("mosquitto") is None, reason="mosquitto not installed")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def system(tmp_path_factory):
    port = free_port()
    sysm = System("127.0.0.1", port, spots=4, workdir=str(tmp_path_factory.mktemp("e2e")), start_broker=True).start()
    drv = Driver(MqttSettings(host="127.0.0.1", port=port), verbose=False).start()
    yield sysm, drv
    drv.stop()
    sysm.stop()


def test_entry_park_exit_creates_complete_session(system):
    sysm, drv = system
    d = drv.drive_in("ZG1234AB", spot="P02")
    assert d["decision"] == "GRANTED" and d["confidence"] >= 0.85
    opened = drv.wait_for(topics.SESSION_EVENT, lambda p: p["plate"] == "ZG1234AB", since=0)
    assert opened["eventType"] == "SESSION_OPENED"
    closed = drv.drive_out("ZG1234AB", spot="P02")
    assert closed["durationS"] > 0
    # demo pricing: 1 real minute is billed as 1 hour, the first 15 s are free
    from parking_sessions import PricingPolicy
    assert closed["price"] == PricingPolicy.demo().price_cents(closed["durationS"]) / 100.0
    db = sqlite3.connect(os.path.join(sysm.workdir, "garage.db"))
    row = db.execute("SELECT status, spot_id, price_cents FROM sessions WHERE plate='ZG1234AB'").fetchone()
    assert row == ("CLOSED", "P02", int(round(closed["price"] * 100)))


def test_unreadable_plate_needs_operator_and_gate_stays_closed(system):
    sysm, drv = system
    since = drv.mark()
    d = drv.arrive("entrance", "ST555B", quality="unreadable")
    assert d["decision"] == "MANUAL_REQUIRED"
    commands = [p for _, t, p in drv.messages[since:] if t == topics.gate_command("entrance")]
    assert commands == []  # never opened automatically
    since = drv.mark()
    drv.manual("APPROVE_ENTRY", "entrance", "ST555B", note="e2e test")
    d = drv.wait_for(topics.ACCESS_DECISION, lambda p: p["manual"], since=since)
    assert d["decision"] == "GRANTED" and d["reason"] == "MANUAL_APPROVAL"
    drv.pass_gate("entrance")


def test_exit_without_session_is_denied(system):
    sysm, drv = system
    d = drv.arrive("exit", "KA4321ZZ")
    assert (d["decision"], d["reason"]) == ("DENIED", "NO_ACTIVE_SESSION")
    drv.presence("exit", False)
    drv.vehicle_at("exit", None)


def test_broken_sensor_is_not_counted_as_free(system):
    sysm, drv = system
    since = drv.mark()
    drv.spot("P04", None)
    s = drv.wait_for(topics.GARAGE_SUMMARY, lambda p: p["unknownSpots"] >= 1, since=since)
    assert s["freeSpots"] + s["occupiedSpots"] + s["unknownSpots"] == s["totalSpots"]
    drv.spot("P04", False)


def test_all_messages_follow_the_contract(system):
    sysm, drv = system
    assert drv.contract_errors == []
