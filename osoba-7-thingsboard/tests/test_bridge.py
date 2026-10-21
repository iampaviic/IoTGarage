import json
import os

import pytest

from tb_bridge.bridge import Buffer, ThingsBoardBridge
from tb_bridge.mapping import GATEWAY_NAME, Mapper

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "..", "..", "osoba-1-voditelj", "contract", "examples")


def example(name):
    with open(os.path.join(EXAMPLES, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def test_spot_mapping_uses_message_timestamp():
    out = Mapper().map("garage/parking/spot/P01/telemetry", example("spot_telemetry"), now_ms=1)
    device, type_, ts, values = out[0]
    assert (device, type_) == ("ParkingSpot-01", "ParkingSpot")
    assert ts == 1792398600000  # 2026-10-19T08:30:00Z
    assert values["occupied"] is True and values["stateCode"] == 1


def test_spot_without_time_uses_receive_time():
    msg = dict(example("spot_telemetry"), timestamp=None)
    assert Mapper().map("garage/parking/spot/P01/telemetry", msg, now_ms=1234)[0][2] == 1234


def test_gate_ack_clears_timeout_flag():
    device, type_, _, values = Mapper().map("garage/gate/entrance/state", example("gate_state"), 0)[0]
    assert device == "EntranceGate" and values["stateCode"] == 2 and values["ackTimeout"] is False


def test_summary_decision_session_go_to_gateway():
    m = Mapper()
    for topic, name in (("garage/summary", "garage_summary"), ("garage/access/decision", "access_decision"),
                        ("garage/session/event", "session_event")):
        device, type_, _, values = m.map(topic, example(name), 0)[0]
        assert device is None and type_ == "GarageEdge"
    closed = m.map("garage/session/event", example("session_event"), 0)[0][3]
    assert closed["exit"] == 1 and closed["durationMin"] == 77.5 and closed["price"] == 3.0


def test_alert_sets_flag_on_gate_and_edge():
    out = Mapper().map("garage/system/alert", example("system_alert"), 0)
    assert ("EntranceGate", "Gate") == out[0][:2] and out[0][3] == {"ackTimeout": True}
    assert out[1][0] is None and out[1][3]["alert_GATE_NO_ACK"] is True


def test_sensor_node_offline_marks_its_spots_unknown():
    m = Mapper()
    m.map("garage/parking/spot/P02/telemetry", dict(example("spot_telemetry"), spotId="P02"), 0)
    out = m.map("garage/system/status/esp32-spots", {"deviceId": "esp32-spots", "online": False}, 0)
    assert out[0][:2] == ("esp32-spots", "Controller") and out[0][3] == {"online": False}
    assert out[1][0] == "ParkingSpot-02" and out[1][3]["sensorStatus"] == "OFFLINE"


def test_buffer_is_persistent_fifo(tmp_path):
    path = str(tmp_path / "b.db")
    b = Buffer(path)
    for i in range(5):
        b.put("ParkingSpot-01", "ParkingSpot", i, {"i": i})
    rows = b.peek(3)
    assert [r[4]["i"] for r in rows] == [0, 1, 2]
    b.delete([r[0] for r in rows])
    assert Buffer(path).size() == 2  # survives a restart


def test_buffer_limit_drops_oldest(tmp_path):
    b = Buffer(str(tmp_path / "b.db"), max_rows=3)
    for i in range(5):
        b.put(None, "GarageEdge", i, {"i": i})
    assert [r[4]["i"] for r in b.peek(10)] == [2, 3, 4]


@pytest.fixture
def bridge(tmp_path):
    br = ThingsBoardBridge.__new__(ThingsBoardBridge)
    sent = []

    class Local:
        def publish_json(self, topic, payload, retain=False):
            sent.append((topic, payload))
            return True
    br.local = Local()
    br.sent_local = sent
    return br


def test_rpc_open_gate_becomes_manual_action(bridge):
    assert bridge.handle_rpc("EntranceGate", "open", {})["success"]
    topic, payload = bridge.sent_local[-1]
    assert topic == "garage/access/manual"
    assert payload["action"] == "OPEN_GATE" and payload["gate"] == "ENTRANCE"


def test_rpc_approve_entry_with_plate(bridge):
    bridge.handle_rpc(GATEWAY_NAME, "approveEntry", {"plate": "zg 1234-ab"})
    payload = bridge.sent_local[-1][1]
    assert payload["action"] == "APPROVE_ENTRY" and payload["plate"] == "ZG1234AB"
    from garage_contract import validate
    validate("access_manual", payload)


def test_rpc_unknown_method(bridge):
    assert not bridge.handle_rpc("ExitGate", "fly", {})["success"]
