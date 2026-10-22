import json
import os
from datetime import timezone

import pytest

from garage_contract import ContractError, GarageConfig, parse_iso, to_iso, topics, validate
from garage_contract.validation import message_type_for_topic, message_types

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def load_example(name):
    with open(os.path.join(EXAMPLES, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("message_type", message_types())
def test_every_schema_has_a_valid_example(message_type):
    validate(message_type, load_example(message_type))


def test_unknown_spot_must_have_null_occupied():
    msg = load_example("spot_telemetry")
    msg.update(state="UNKNOWN", occupied=False, sensorStatus="TIMEOUT")
    with pytest.raises(ContractError):
        validate("spot_telemetry", msg)
    msg["occupied"] = None
    validate("spot_telemetry", msg)


def test_gate_command_rejects_unknown_command():
    msg = load_example("gate_command")
    msg["command"] = "SMASH"
    with pytest.raises(ContractError) as exc:
        validate("gate_command", msg)
    assert "command" in str(exc.value)


def test_timestamp_must_be_utc_z():
    msg = load_example("alpr_event")
    msg["timestamp"] = "2026-10-19 08:31:12"
    with pytest.raises(ContractError):
        validate("alpr_event", msg)


def test_plate_must_be_normalised():
    msg = load_example("alpr_event")
    msg["plate"] = "ZG 1234-AB"
    with pytest.raises(ContractError):
        validate("alpr_event", msg)


def test_manual_open_gate_requires_gate():
    msg = {"requestId": "m1", "action": "OPEN_GATE", "timestamp": "2026-10-19T08:00:00Z"}
    with pytest.raises(ContractError):
        validate("access_manual", msg)
    msg["gate"] = "EXIT"
    validate("access_manual", msg)


@pytest.mark.parametrize("topic,expected", [
    ("garage/parking/spot/P03/telemetry", "spot_telemetry"),
    ("garage/gate/entrance/command", "gate_command"),
    ("garage/gate/exit/state", "gate_state"),
    ("garage/alpr/exit/event", "alpr_event"),
    ("garage/alpr/entrance/trigger", "alpr_trigger"),
    ("garage/system/status/esp32-gates", "device_status"),
    ("garage/summary", "garage_summary"),
    ("garage/something/else", None),
])
def test_topic_mapping(topic, expected):
    assert message_type_for_topic(topic) == expected


def test_topic_builders():
    assert topics.spot_telemetry("P02") == "garage/parking/spot/P02/telemetry"
    assert topics.gate_command("ENTRANCE") == "garage/gate/entrance/command"
    with pytest.raises(ValueError):
        topics.gate_state("side-door")


def test_iso_roundtrip():
    dt = parse_iso("2026-10-19T08:31:12Z")
    assert dt.tzinfo == timezone.utc
    assert to_iso(dt) == "2026-10-19T08:31:12Z"
    assert to_iso(parse_iso("2026-10-19T10:31:12+02:00")) == "2026-10-19T08:31:12Z"
    assert parse_iso("2026-10-19T08:31:12.250Z").microsecond == 250000


def test_garage_config_default_spots():
    assert GarageConfig().spots == ["P01", "P02", "P03", "P04", "P05", "P06"]
    assert GarageConfig(spot_count=4).spots[-1] == "P04"
