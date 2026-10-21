"""Validate payloads against the JSON schemas in ./schemas.

    from garage_contract import validate, message_type_for_topic
    validate("spot_telemetry", payload)            # raises ContractError
    validate(message_type_for_topic(topic), payload)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from paho.mqtt.client import topic_matches_sub

from garage_contract import topics

_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")

# topic filter -> message type (= schema file name without .schema.json)
TOPIC_TYPES = (
    (topics.SPOT_TELEMETRY_ALL, "spot_telemetry"),
    (topics.GATE_COMMAND_ALL, "gate_command"),
    (topics.GATE_STATE_ALL, "gate_state"),
    (topics.ALPR_TRIGGER_ALL, "alpr_trigger"),
    (topics.ALPR_EVENT_ALL, "alpr_event"),
    (topics.ACCESS_DECISION, "access_decision"),
    (topics.ACCESS_MANUAL, "access_manual"),
    (topics.SESSION_EVENT, "session_event"),
    (topics.GARAGE_SUMMARY, "garage_summary"),
    (topics.HEARTBEAT, "heartbeat"),
    (topics.DEVICE_STATUS_ALL, "device_status"),
    (topics.SYSTEM_ALERT, "system_alert"),
    (topics.SIM_SPOT_ALL, "sim_spot"),
    (topics.SIM_GATE_PRESENCE_ALL, "sim_gate_presence"),
    (topics.SIM_VEHICLE_ALL, "sim_vehicle"),
)

_cache: Dict[str, Any] = {}


class ContractError(ValueError):
    """Payload does not match the communication contract."""

    def __init__(self, message_type: str, errors: List[str]):
        self.message_type = message_type
        self.errors = errors
        super().__init__("%s: %s" % (message_type, "; ".join(errors)))


def message_types() -> List[str]:
    return sorted(f[: -len(".schema.json")] for f in os.listdir(_SCHEMA_DIR) if f.endswith(".schema.json"))


def load_schema(message_type: str) -> Dict[str, Any]:
    if message_type not in _cache:
        path = os.path.join(_SCHEMA_DIR, message_type + ".schema.json")
        if not os.path.exists(path):
            raise KeyError("no schema for message type %r" % message_type)
        with open(path, encoding="utf-8") as f:
            _cache[message_type] = json.load(f)
    return _cache[message_type]


def message_type_for_topic(topic: str) -> Optional[str]:
    for topic_filter, message_type in TOPIC_TYPES:
        if topic_matches_sub(topic_filter, topic):
            return message_type
    return None


def errors_for(message_type: str, payload: Any) -> List[str]:
    """Return a list of human-readable problems (empty list = valid)."""
    import jsonschema

    validator_cls = jsonschema.validators.validator_for(load_schema(message_type))
    validator = validator_cls(load_schema(message_type))
    out = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        out.append("%s: %s" % (where, err.message))
    return out


def validate(message_type: str, payload: Any) -> None:
    errors = errors_for(message_type, payload)
    if errors:
        raise ContractError(message_type, errors)


def validate_topic(topic: str, payload: Any) -> Optional[str]:
    """Validate by topic. Returns the message type, raises on mismatch,
    returns None for topics outside the contract."""
    message_type = message_type_for_topic(topic)
    if message_type is not None:
        validate(message_type, payload)
    return message_type
