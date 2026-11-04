"""Shared communication contract for the IoT Garage system.

Every service (simulators, ALPR, access control, ThingsBoard bridge) imports
topic names, message builders and validation from here, so there is exactly
one definition of the MQTT interface. The human-readable version lives in
PROJEKT/sustav/komunikacijski-ugovor.md and must be kept in sync.
"""

from garage_contract import topics
from garage_contract.config import GarageConfig, MqttSettings
from garage_contract.timeutil import parse_iso, to_iso, utc_now, utc_now_iso
from garage_contract.validation import ContractError, message_type_for_topic, validate

__version__ = "0.1.0"
CONTRACT_VERSION = "1.0"

__all__ = [
    "CONTRACT_VERSION",
    "ContractError",
    "GarageConfig",
    "MqttSettings",
    "message_type_for_topic",
    "parse_iso",
    "to_iso",
    "topics",
    "utc_now",
    "utc_now_iso",
    "validate",
]
