"""Edge service configuration (YAML file + environment variables).

    python -m edge_service --config edge.yaml all

Copy edge.example.yaml to edge.yaml (git-ignored) and adjust. Environment
variables MQTT_HOST, MQTT_PORT, GARAGE_DB, GARAGE_SPOTS and PRICING_PROFILE
override the file, which is handy in Docker.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from garage_contract import MqttSettings


@dataclass
class GateCameraConfig:
    camera_id: str
    roi: Optional[Tuple[float, float, float, float]] = None   # (x0, y0, x1, y1) fractions
    camera: Optional[str] = None                              # own camera for this gate (else shared)


@dataclass
class AccessConfig:
    policy: str = "open"              # open | allowlist
    accept_threshold: float = 0.85
    retry_threshold: float = 0.60
    max_attempts: int = 3
    retry_delay_s: float = 0.5
    gate_ack_timeout_s: float = 3.0
    gate_command_retries: int = 1
    alpr_timeout_s: float = 10.0
    spot_timeout_s: float = 90.0
    exit_fuzzy_match: bool = False
    alpr_failure_alert_after: int = 3
    spot_assign_window_s: float = 300.0


@dataclass
class AlprConfig:
    source: str = "camera"            # camera | sim | images
    camera: str = "0"
    width: int = 1280
    height: int = 720
    images_dir: Optional[str] = None
    frames_per_trigger: int = 3
    # default: ONE camera that is moved between the entrance and the exit mount
    # (see PROJEKT/maketa/nacrt-makete.md); with two cameras set `camera` per gate
    gates: Dict[str, GateCameraConfig] = field(default_factory=lambda: {
        "entrance": GateCameraConfig("entrance-camera"),
        "exit": GateCameraConfig("exit-camera"),
    })


@dataclass
class PrivacyConfig:
    save_crops: bool = False          # store rectified plate crops (never full frames)
    crops_dir: str = "data/crops"
    retention_days: int = 30


@dataclass
class EdgeConfig:
    mqtt: MqttSettings = field(default_factory=MqttSettings)
    spots: int = 6
    database: str = "data/garage.db"
    pricing: str = "demo"
    access: AccessConfig = field(default_factory=AccessConfig)
    alpr: AlprConfig = field(default_factory=AlprConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "EdgeConfig":
        data: Dict[str, Any] = {}
        if path:
            import yaml

            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        cfg = cls()
        m = data.get("mqtt", {})
        cfg.mqtt = MqttSettings(host=m.get("host", "localhost"), port=int(m.get("port", 1883)),
                                username=m.get("username"), password=m.get("password"))
        g = data.get("garage", {})
        cfg.spots = int(g.get("spots", cfg.spots))
        cfg.database = data.get("database", cfg.database)
        cfg.pricing = data.get("pricing", cfg.pricing)
        _update(cfg.access, data.get("access", {}))
        alpr = dict(data.get("alpr", {}))
        gates = alpr.pop("gates", None)
        _update(cfg.alpr, alpr)
        if gates:
            cfg.alpr.gates = {
                name: GateCameraConfig(camera_id=v.get("camera_id", name + "-camera"),
                                       roi=tuple(v["roi"]) if v.get("roi") else None,
                                       camera=str(v["camera"]) if v.get("camera") is not None else None)
                for name, v in gates.items()
            }
        _update(cfg.privacy, data.get("privacy", {}))

        # environment wins (Docker / systemd)
        env = os.environ
        if env.get("MQTT_HOST"):
            cfg.mqtt.host = env["MQTT_HOST"]
        if env.get("MQTT_PORT"):
            cfg.mqtt.port = int(env["MQTT_PORT"])
        if env.get("MQTT_USERNAME"):
            cfg.mqtt.username, cfg.mqtt.password = env["MQTT_USERNAME"], env.get("MQTT_PASSWORD")
        if env.get("GARAGE_DB"):
            cfg.database = env["GARAGE_DB"]
        if env.get("GARAGE_SPOTS"):
            cfg.spots = int(env["GARAGE_SPOTS"])
        if env.get("PRICING_PROFILE"):
            cfg.pricing = env["PRICING_PROFILE"]
        if env.get("ALPR_SOURCE"):
            cfg.alpr.source = env["ALPR_SOURCE"]
        if cfg.access.policy not in ("open", "allowlist"):
            raise ValueError("access.policy must be 'open' or 'allowlist'")
        return cfg


def _update(obj: Any, values: Dict[str, Any]) -> None:
    for k, v in values.items():
        if not hasattr(obj, k):
            raise ValueError("unknown config key %r in section %s" % (k, type(obj).__name__))
        current = getattr(obj, k)
        setattr(obj, k, type(current)(v) if current is not None and v is not None and not isinstance(current, (dict, tuple)) else v)
