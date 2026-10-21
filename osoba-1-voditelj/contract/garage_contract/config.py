"""System-wide configuration shared by all Python services.

Values come from environment variables so the same code runs on a laptop,
the Raspberry Pi and the Jetson Nano without edits:

    MQTT_HOST=192.168.1.10 MQTT_PORT=1883 GARAGE_SPOTS=6 python ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MqttSettings:
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    keepalive: int = 30

    @classmethod
    def from_env(cls) -> "MqttSettings":
        return cls(
            host=os.environ.get("MQTT_HOST", "localhost"),
            port=int(os.environ.get("MQTT_PORT", "1883")),
            username=os.environ.get("MQTT_USERNAME") or None,
            password=os.environ.get("MQTT_PASSWORD") or None,
            keepalive=int(os.environ.get("MQTT_KEEPALIVE", "30")),
        )


def spot_ids(count: int) -> List[str]:
    return ["P%02d" % i for i in range(1, count + 1)]


@dataclass
class GarageConfig:
    """Physical layout of the model. 4-6 spots, two gates."""

    spot_count: int = 6
    spots: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.spot_count <= 99:
            raise ValueError("spot_count must be 1..99")
        if not self.spots:
            self.spots = spot_ids(self.spot_count)

    @classmethod
    def from_env(cls) -> "GarageConfig":
        return cls(spot_count=int(os.environ.get("GARAGE_SPOTS", "6")))
