"""Scenario tests of the access controller with a fake clock and no MQTT.

Every message the controller publishes is validated against the
communication contract (osoba-1-voditelj/contract).
"""

from datetime import datetime, timedelta, timezone

import pytest

from edge_service.access_control import AccessController
from edge_service.config import AccessConfig
from garage_contract import validate
from garage_contract.validation import message_type_for_topic
from parking_sessions import PricingPolicy, SessionStore


class Harness:
    def __init__(self, spots=4, **cfg):
        self.t = 1000.0
        self.now = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
        self.sent = []
        self.store = SessionStore(":memory:", PricingPolicy.real())
        self.ctrl = AccessController(self.store, self.publish, ["P%02d" % i for i in range(1, spots + 1)],
                                     AccessConfig(**cfg), clock=lambda: self.t, utcnow=lambda: self.now)

    def publish(self, topic, payload, retain=False):
        validate(message_type_for_topic(topic), payload)  # contract check on every message
        self.sent.append((topic, payload))

    def advance(self, seconds):
        self.t += seconds
        self.now += timedelta(seconds=seconds)
        self.ctrl.tick()

    def last(self, topic):
        for t, p in reversed(self.sent):
            if t == topic:
                return p
        return None

    def all(self, topic):
        return [p for t, p in self.sent if t == topic]

    # ---- device simulation helpers
    def spot(self, spot, state):
        self.ctrl.on_spot("garage/parking/spot/%s/telemetry" % spot, {
            "spotId": spot, "state": state, "occupied": {"FREE": False, "OCCUPIED": True}.get(state),
            "sensorStatus": "OK" if state != "UNKNOWN" else "TIMEOUT", "timestamp": None})

    def gate(self, gate, state, present, request_id=None, success=True):
        self.ctrl.on_gate_state("garage/gate/%s/state" % gate, {
            "gate": gate.upper(), "state": state, "vehiclePresent": present, "requestId": request_id,
            "success": success, "timestamp": None})

    def alpr(self, gate, plate, conf, status="OK", request_id=None):
        trig = self.last("garage/alpr/%s/trigger" % gate)
        self.ctrl.on_alpr_event("garage/alpr/%s/event" % gate, {
            "requestId": request_id or (trig["requestId"] if trig else "manual"), "cameraId": gate + "-camera",
            "direction": "ENTRY" if gate == "entrance" else "EXIT", "status": status, "plate": plate,
            "detectionConfidence": 0.9, "ocrConfidence": conf, "accepted": conf >= 0.85,
            "timestamp": "2026-10-19T08:00:00Z"})

    def ack_last_command(self, gate, state="OPEN", present=True):
        cmd = self.last("garage/gate/%s/command" % gate)
        self.gate(gate, state, present, cmd["requestId"])
        return cmd


@pytest.fixture
def h():
    h = Harness()
    for i in range(1, 5):
        h.spot("P%02d" % i, "FREE")
    h.gate("entrance", "CLOSED", False)
    h.gate("exit", "CLOSED", False)
    return h


def test_full_entry_park_exit_flow(h):
    # vehicle arrives -> ALPR is triggered
    h.gate("entrance", "CLOSED", True)
    assert h.last("garage/alpr/entrance/trigger")["reason"] == "VEHICLE_DETECTED"
    # confident reading -> gate opens, session opened
    h.alpr("entrance", "ZG1234AB", 0.93)
    cmd = h.last("garage/gate/entrance/command")
    assert cmd["command"] == "OPEN" and cmd["plate"] == "ZG1234AB"
    dec = h.last("garage/access/decision")
    assert dec["decision"] == "GRANTED" and dec["gateRequestId"] == cmd["requestId"]
    assert h.last("garage/session/event")["eventType"] == "SESSION_OPENED"
    h.ack_last_command("entrance")
    h.gate("entrance", "OPEN", False)          # car passed
    assert "entrance" not in h.ctrl.transactions
    h.spot("P03", "OCCUPIED")                  # parks on P03
    assert h.store.find_active("ZG1234AB").spot_id == "P03"
    assert h.last("garage/summary")["freeSpots"] == 3

    # 77 minutes later at the exit
    h.advance(77 * 60)
    h.spot("P03", "FREE")
    h.gate("exit", "CLOSED", True)
    h.alpr("exit", "ZG1234AB", 0.91)
    closed = h.last("garage/session/event")
    assert closed["eventType"] == "SESSION_CLOSED"
    assert closed["durationS"] == 77 * 60
    assert closed["price"] == 3.0
    assert h.last("garage/gate/exit/command")["command"] == "OPEN"
    assert h.store.count_active() == 0


def test_low_confidence_retries_then_needs_operator(h):
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.75)
    assert h.last("garage/access/decision")["decision"] == "RETRY"
    assert h.last("garage/gate/entrance/command") is None
    h.advance(1)  # retry delay passed -> second trigger
    triggers = h.all("garage/alpr/entrance/trigger")
    assert len(triggers) == 2 and triggers[1]["attempt"] == 2 and triggers[1]["reason"] == "RETRY"
    h.alpr("entrance", "ZG1234AB", 0.7)
    h.advance(1)
    h.alpr("entrance", "ZG1234AB", 0.7)
    assert h.last("garage/access/decision")["decision"] == "MANUAL_REQUIRED"
    assert h.last("garage/gate/entrance/command") is None

    # operator approves on the dashboard: plate from the last reading is used
    h.ctrl.on_manual("garage/access/manual", {"requestId": "m1", "action": "APPROVE_ENTRY", "gate": "ENTRANCE",
                                              "operator": "dezurni", "timestamp": "2026-10-19T08:00:00Z"})
    dec = h.last("garage/access/decision")
    assert dec["decision"] == "GRANTED" and dec["manual"] and dec["reason"] == "MANUAL_APPROVAL"
    session = h.store.find_active("ZG1234AB")
    assert session.entry_mode == "MANUAL"
    assert any(e["type"] == "MANUAL_APPROVE_ENTRY" for e in h.store.events())


def test_very_low_confidence_goes_straight_to_operator(h):
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.4)
    assert h.last("garage/access/decision")["decision"] == "MANUAL_REQUIRED"
    assert h.last("garage/gate/entrance/command") is None


def test_full_garage_is_denied():
    h = Harness(spots=2)
    h.spot("P01", "OCCUPIED")
    h.spot("P02", "OCCUPIED")
    assert h.last("garage/summary")["full"] is True
    alert = h.last("garage/system/alert")
    assert alert["type"] == "GARAGE_FULL" and alert["active"]
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.95)
    assert h.last("garage/access/decision")["reason"] == "GARAGE_FULL"


def test_unknown_spots_are_not_free():
    h = Harness(spots=2)
    h.spot("P01", "FREE")
    # P02 never reported -> UNKNOWN -> only one available
    assert h.ctrl.available_spots() == 1
    h.spot("P01", "UNKNOWN")
    assert h.ctrl.available_spots() == 0


def test_active_sessions_reserve_spots(h):
    # 4 free spots but 4 cars already let in that did not park yet -> full
    for i, plate in enumerate(["ZG1111A", "ZG2222B", "ZG3333C", "ZG4444D"]):
        h.store.open_session(plate, entry_time=h.now)
    assert h.ctrl.available_spots() == 0


def test_vehicle_cannot_enter_twice(h):
    h.store.open_session("ZG1234AB", entry_time=h.now)
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.95)
    assert h.last("garage/access/decision")["reason"] == "ALREADY_INSIDE"


def test_exit_without_session_is_denied(h):
    h.gate("exit", "CLOSED", True)
    h.alpr("exit", "RI555X", 0.95)
    assert h.last("garage/access/decision")["reason"] == "NO_ACTIVE_SESSION"
    assert h.last("garage/gate/exit/command") is None


def test_allowlist_policy():
    h = Harness(policy="allowlist")
    h.spot("P01", "FREE")
    h.store.allow("ZG1234AB")
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ST555B", 0.95)
    assert h.last("garage/access/decision")["reason"] == "NOT_ON_ALLOWLIST"
    h.gate("entrance", "CLOSED", False)
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.95)
    assert h.last("garage/access/decision")["decision"] == "GRANTED"


def test_gate_without_ack_is_resent_then_alarm(h):
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.95)
    first = h.last("garage/gate/entrance/command")
    h.advance(3.5)
    commands = h.all("garage/gate/entrance/command")
    assert len(commands) == 2 and commands[1]["requestId"] == first["requestId"]  # same id -> no double action
    h.advance(3.5)
    alert = h.last("garage/system/alert")
    assert alert["type"] == "GATE_NO_ACK" and alert["active"] and alert["gate"] == "ENTRANCE"
    # a later successful ack clears the alarm
    h.gate("entrance", "OPEN", True, request_id=None)
    h.ctrl.on_manual("garage/access/manual", {"requestId": "m2", "action": "OPEN_GATE", "gate": "ENTRANCE",
                                              "timestamp": "2026-10-19T08:00:00Z"})
    h.ack_last_command("entrance")
    assert h.last("garage/system/alert")["active"] is False


def test_duplicate_alpr_answer_is_ignored(h):
    """QoS 1 may deliver the same ALPR event twice: the second copy must not produce a second decision."""
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.93)
    first = h.last("garage/alpr/entrance/trigger")["requestId"]
    decisions = len(h.all("garage/access/decision"))
    h.alpr("entrance", "ZG1234AB", 0.93, request_id=first)
    assert len(h.all("garage/access/decision")) == decisions
    assert h.last("garage/access/decision")["decision"] == "GRANTED"


def test_late_answer_to_previous_attempt_is_ignored(h):
    h.gate("entrance", "CLOSED", True)
    h.alpr("entrance", "ZG1234AB", 0.75)                 # attempt 1 -> RETRY
    old = h.all("garage/alpr/entrance/trigger")[0]["requestId"]
    h.advance(1)                                           # attempt 2 triggered with a new requestId
    new = h.last("garage/alpr/entrance/trigger")["requestId"]
    assert new != old
    h.alpr("entrance", "ZG1234AB", 0.95, request_id=old)  # late duplicate of attempt 1
    assert h.last("garage/gate/entrance/command") is None
    h.alpr("entrance", "ZG1234AB", 0.95)                  # real answer to attempt 2
    assert h.last("garage/access/decision")["decision"] == "GRANTED"


def test_alpr_timeout_counts_as_camera_error(h):
    h.gate("entrance", "CLOSED", True)
    h.advance(11)
    dec = h.last("garage/access/decision")
    assert dec["decision"] == "RETRY" and dec["reason"] == "CAMERA_ERROR"


def test_repeated_alpr_failures_raise_alert(h):
    for _ in range(3):
        h.gate("entrance", "CLOSED", True)
        h.alpr("entrance", None, 0.0, status="NO_PLATE")
        h.gate("entrance", "CLOSED", False)
    alert = h.last("garage/system/alert")
    assert alert["type"] == "ALPR_REPEATED_FAILURE" and alert["active"]


def test_vehicle_leaving_cancels_transaction(h):
    h.gate("entrance", "CLOSED", True)
    h.gate("entrance", "CLOSED", False)
    assert "entrance" not in h.ctrl.transactions
    # a late ALPR answer must not open the gate for nobody
    h.ctrl.on_alpr_event("garage/alpr/entrance/event", {
        "requestId": "old", "cameraId": "c", "direction": "ENTRY", "status": "OK", "plate": "ZG1234AB",
        "detectionConfidence": 0.9, "ocrConfidence": 0.95, "accepted": True, "timestamp": "2026-10-19T08:00:00Z"})
    assert h.last("garage/access/decision") is None
    assert h.last("garage/gate/entrance/command") is None


def test_sensor_device_offline_marks_spots_unknown(h):
    h.ctrl.on_spot("garage/parking/spot/P01/telemetry", {
        "spotId": "P01", "state": "FREE", "occupied": False, "sensorStatus": "OK", "deviceId": "esp32-spots",
        "timestamp": None})
    h.ctrl.on_device_status("garage/system/status/esp32-spots", {"deviceId": "esp32-spots", "online": False})
    assert h.ctrl.spots["P01"] == "UNKNOWN"
    assert h.last("garage/system/alert")["type"] == "SENSOR_OFFLINE"


def test_stale_spot_becomes_unknown(h):
    h.advance(100)
    assert all(s == "UNKNOWN" for s in h.ctrl.spots.values())


def test_manual_exit_without_session_opens_and_logs(h):
    h.ctrl.on_manual("garage/access/manual", {"requestId": "m3", "action": "APPROVE_EXIT", "gate": "EXIT",
                                              "plate": "RI555X", "operator": "dezurni", "note": "test",
                                              "timestamp": "2026-10-19T08:00:00Z"})
    assert h.last("garage/gate/exit/command")["reason"] == "MANUAL"
    assert any(e["type"] == "EXIT_WITHOUT_SESSION" for e in h.store.events())
