"""Varijanta B: ThingsBoard device API (MQTT) as used by the garage devices.

Every node (both ESP32s and the ALPR service) is a *gateway device* in ThingsBoard: one MQTT
connection, the access token as the user name, and it speaks for its own devices:

    node            gateway device   devices (ThingsBoard)
    ESP32 senzora   esp32-spots      ParkingSpot-01 .. ParkingSpot-06
    ESP32 rampi     esp32-gates      EntranceGate, ExitGate
    ALPR servis     alpr-service     ALPR-Entrance, ALPR-Exit

Topics (https://thingsboard.io/docs/reference/gateway-mqtt-api/, .../mqtt-api/):

    v1/gateway/connect          {"device": "ParkingSpot-01", "type": "ParkingSpot"}
    v1/gateway/telemetry        {"ParkingSpot-01": [{"ts": 1700000000000, "values": {...}}]}
    v1/gateway/rpc              in:  {"device": "EntranceGate", "data": {"id": 3, "method": "open", "params": {}}}
                                out: {"device": "EntranceGate", "id": 3, "data": {"success": true}}
    v1/devices/me/telemetry     telemetry of the gateway itself (heartbeat, counts)
    v1/devices/me/attributes    client attributes of the gateway itself (fwVersion, ip)
    v1/devices/me/rpc/request/+ RPC to the gateway itself, answer on v1/devices/me/rpc/response/<id>

The firmware does exactly the same in C++; this module is used by the simulators and the ALPR service.
Decisions are made by the rule chain (SOFTWARE/thingsboard/rulechain), never by the devices.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from garage_contract.mqtt import _rc_value, new_paho_client

log = logging.getLogger(__name__)

# ------------------------------------------------------------------ names shared with the rule chain
SPOTS_GATEWAY = "esp32-spots"
GATES_GATEWAY = "esp32-gates"
ALPR_GATEWAY = "alpr-service"
GATE_DEVICES = {"ENTRANCE": "EntranceGate", "EXIT": "ExitGate"}
ALPR_DEVICES = {"ENTRANCE": "ALPR-Entrance", "EXIT": "ALPR-Exit"}
SPOT_STATE_CODE = {"FREE": 0, "OCCUPIED": 1, "UNKNOWN": -1}
GATE_STATE_CODE = {"CLOSED": 0, "OPENING": 1, "OPEN": 2, "CLOSING": 3, "ERROR": 4}


def spot_device(spot_id: str) -> str:
    """P03 -> ParkingSpot-03"""
    return "ParkingSpot-" + spot_id[1:]


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class TbSettings:
    host: str = "localhost"
    port: int = 1883
    token: str = ""

    @classmethod
    def from_env(cls, token_env: str, default_token: str = "") -> "TbSettings":
        """TB_HOST, TB_MQTT_PORT and the token from the given variable (e.g. TB_TOKEN_SPOTS)."""
        return cls(host=os.environ.get("TB_HOST", "localhost"), port=int(os.environ.get("TB_MQTT_PORT", "1883")),
                   token=os.environ.get(token_env, default_token))


class TbGateway:
    """Gateway connection to ThingsBoard with automatic reconnect.

    gw = TbGateway("esp32-spots", settings, {"ParkingSpot-01": "ParkingSpot"})
    gw.on_device_rpc = lambda device, method, params: {...}   # RPC to one of its devices
    gw.on_rpc = lambda method, params: {...}                   # RPC to the gateway itself
    gw.on_connect = lambda: ...                                # (re)connected: publish all states
    gw.start()
    gw.device_telemetry("ParkingSpot-01", {"state": "FREE"})
    """

    def __init__(self, name: str, settings: TbSettings, devices: Dict[str, str], keepalive: int = 30) -> None:
        self.name = name
        self.settings = settings
        self.devices = dict(devices)          # device name -> device type (profile)
        self.keepalive = keepalive
        self.on_rpc: Optional[Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]]] = None
        self.on_device_rpc: Optional[Callable[[str, str, Dict[str, Any]], Optional[Dict[str, Any]]]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.connected = threading.Event()
        self._stopping = False
        self._lock = threading.Lock()
        self.client = new_paho_client(name)
        self.client.username_pw_set(settings.token)
        self.client.reconnect_delay_set(min_delay=1, max_delay=5)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    # ------------------------------------------------------------- lifecycle
    def start(self, wait_s: float = 10.0) -> bool:
        self._stopping = False
        self.client.connect_async(self.settings.host, self.settings.port, keepalive=self.keepalive)
        self.client.loop_start()
        return self.connected.wait(wait_s)

    def stop(self) -> None:
        """Clean disconnect: ThingsBoard sees the devices as disconnected at once."""
        self._stopping = True
        self.client.disconnect()
        self.client.loop_stop()
        self.connected.clear()

    def kill(self) -> None:
        """Drop the connection without DISCONNECT (like a power cut or Wi-Fi loss) - for tests."""
        self._stopping = True
        self.client.loop_stop()
        sock = self.client.socket()
        if sock is not None:
            sock.close()
        self.connected.clear()

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if _rc_value(rc) != 0:
            log.error("%s: ThingsBoard refused the connection (rc=%s) - wrong access token?", self.name, rc)
            return
        client.subscribe("v1/devices/me/rpc/request/+", qos=1)
        client.subscribe("v1/gateway/rpc", qos=1)
        for device, type_ in self.devices.items():
            self._publish("v1/gateway/connect", {"device": device, "type": type_})
        self.connected.set()
        log.info("%s: connected to ThingsBoard %s:%s", self.name, self.settings.host, self.settings.port)
        if self.on_connect:
            self.on_connect()

    def _on_disconnect(self, client, userdata, *args) -> None:
        self.connected.clear()
        if not self._stopping:
            log.warning("%s: connection to ThingsBoard lost, reconnecting", self.name)

    # ------------------------------------------------------------- publish
    def _publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        with self._lock:
            info = self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)
        return _rc_value(info.rc) == 0

    def device_telemetry(self, device: str, values: Dict[str, Any], ts: Optional[int] = None) -> bool:
        values = {k: v for k, v in values.items() if v is not None}
        return self._publish("v1/gateway/telemetry", {device: [{"ts": ts or now_ms(), "values": values}]})

    def telemetry(self, values: Dict[str, Any], ts: Optional[int] = None) -> bool:
        values = {k: v for k, v in values.items() if v is not None}
        return self._publish("v1/devices/me/telemetry", {"ts": ts or now_ms(), "values": values})

    def attributes(self, values: Dict[str, Any]) -> bool:
        return self._publish("v1/devices/me/attributes", values)

    # ------------------------------------------------------------- RPC
    def _on_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8") or "{}")
        except ValueError:
            log.warning("%s: invalid JSON on %s", self.name, msg.topic)
            return
        # handlers may take seconds (ALPR); answer from a worker so the connection keeps running
        threading.Thread(target=self._handle, args=(msg.topic, data), daemon=True).start()

    def _handle(self, topic: str, data: Dict[str, Any]) -> None:
        try:
            if topic == "v1/gateway/rpc":
                device, req = data.get("device"), data.get("data") or {}
                result = self.on_device_rpc(device, req.get("method", ""), req.get("params") or {}) \
                    if self.on_device_rpc else None
                self._publish("v1/gateway/rpc", {"device": device, "id": req.get("id"),
                                                 "data": result if result is not None else {"success": False,
                                                                                            "reason": "UNSUPPORTED"}})
            elif topic.startswith("v1/devices/me/rpc/request/"):
                rid = topic.rsplit("/", 1)[1]
                result = self.on_rpc(data.get("method", ""), data.get("params") or {}) if self.on_rpc else None
                self._publish("v1/devices/me/rpc/response/" + rid,
                              result if result is not None else {"success": False, "reason": "UNSUPPORTED"})
        except Exception:  # never let a handler kill the network thread
            log.exception("%s: RPC handler failed", self.name)
