"""Small wrapper around paho-mqtt used by every Python service.

Why a wrapper:
- works with paho-mqtt 1.x (Jetson / older Pi images) and 2.x
- automatic reconnect with back-off, re-subscribes after reconnect
- Last Will: garage/system/status/<deviceId> = {"online": false} (retained)
- optional heartbeat thread on garage/system/heartbeat
- handlers receive already-decoded JSON

    conn = MqttConnection("access-control", settings, device_type="ACCESS_CONTROL")
    conn.subscribe(topics.SPOT_TELEMETRY_ALL, on_spot)   # on_spot(topic, payload)
    conn.start()
    conn.publish_json(topics.GARAGE_SUMMARY, {...}, retain=True)
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import paho.mqtt.client as paho

from garage_contract import topics
from garage_contract.config import MqttSettings
from garage_contract.timeutil import utc_now_iso

log = logging.getLogger(__name__)

Handler = Callable[[str, Any], None]


def new_paho_client(client_id: str) -> paho.Client:
    """Create a paho client regardless of the installed major version."""
    if hasattr(paho, "CallbackAPIVersion"):  # paho-mqtt >= 2.0
        return paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True)
    return paho.Client(client_id=client_id, clean_session=True)


def _rc_value(rc: Any) -> int:
    return int(getattr(rc, "value", rc))


class MqttConnection:
    def __init__(
        self,
        client_id: str,
        settings: Optional[MqttSettings] = None,
        *,
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        fw_version: str = "0.1.0",
        heartbeat_s: float = 30.0,
    ) -> None:
        self.settings = settings or MqttSettings.from_env()
        self.client_id = client_id
        self.device_id = device_id or client_id
        self.device_type = device_type
        self.fw_version = fw_version
        self.heartbeat_s = heartbeat_s
        self._handlers: List[Tuple[str, Handler]] = []
        self._connected = threading.Event()
        self._stop = threading.Event()
        self._started_at = time.monotonic()
        self._hb_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.client = new_paho_client(client_id)
        if self.settings.username:
            self.client.username_pw_set(self.settings.username, self.settings.password)
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)
        if self.device_type:
            self.client.will_set(
                topics.device_status(self.device_id),
                json.dumps({"deviceId": self.device_id, "online": False}),
                qos=1,
                retain=True,
            )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    # ------------------------------------------------------------------ API
    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def subscribe(self, topic_filter: str, handler: Handler) -> None:
        with self._lock:
            self._handlers.append((topic_filter, handler))
        if self.connected:
            self.client.subscribe(topic_filter, qos=1)

    def start(self, wait_s: float = 5.0) -> bool:
        """Connect in the background. Returns True if connected within wait_s.
        Even when it returns False the client keeps retrying."""
        self.client.connect_async(self.settings.host, self.settings.port, keepalive=self.settings.keepalive)
        self.client.loop_start()
        if self.device_type and self.heartbeat_s > 0:
            self._hb_thread = threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True)
            self._hb_thread.start()
        ok = self._connected.wait(wait_s)
        if not ok:
            log.warning("MQTT broker %s:%s not reachable yet, retrying in background",
                        self.settings.host, self.settings.port)
        return ok

    def stop(self) -> None:
        self._stop.set()
        if self.device_type and self.connected:
            self.publish_json(topics.device_status(self.device_id),
                              {"deviceId": self.device_id, "online": False, "timestamp": utc_now_iso()},
                              retain=True)
            time.sleep(0.2)
        self.client.disconnect()
        self.client.loop_stop()

    def publish_json(self, topic: str, payload: Dict[str, Any], *, retain: bool = False, qos: int = 1) -> bool:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        info = self.client.publish(topic, data, qos=qos, retain=retain)
        if info.rc != paho.MQTT_ERR_SUCCESS:
            log.warning("publish to %s failed (rc=%s), connected=%s", topic, info.rc, self.connected)
            return False
        return True

    def wait_connected(self, timeout: float) -> bool:
        return self._connected.wait(timeout)

    # ------------------------------------------------------------ callbacks
    def _on_connect(self, client, userdata, flags, rc, *args) -> None:
        if _rc_value(rc) != 0:
            log.error("MQTT connect refused rc=%s", rc)
            return
        log.info("MQTT connected to %s:%s as %s", self.settings.host, self.settings.port, self.client_id)
        with self._lock:
            filters = sorted({f for f, _ in self._handlers})
        for f in filters:
            client.subscribe(f, qos=1)
        if self.device_type:
            self.publish_json(topics.device_status(self.device_id),
                              {"deviceId": self.device_id, "online": True, "timestamp": utc_now_iso()},
                              retain=True)
        self._connected.set()
        if self.device_type:
            self._send_heartbeat()

    def _on_disconnect(self, client, userdata, *args) -> None:
        self._connected.clear()
        if not self._stop.is_set():
            now = time.monotonic()
            quick = now - getattr(self, "_last_disconnect", 0.0) < 5.0
            self._last_disconnect = now
            log.warning("MQTT disconnected, reconnecting...%s", (
                " (repeats quickly: is another instance with client id '%s' running?)" % self.client_id)
                if quick else "")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload: Any = json.loads(msg.payload.decode("utf-8")) if msg.payload else None
        except (ValueError, UnicodeDecodeError):
            log.warning("ignoring non-JSON message on %s", msg.topic)
            return
        with self._lock:
            handlers = [h for f, h in self._handlers if paho.topic_matches_sub(f, msg.topic)]
        for handler in handlers:
            try:
                handler(msg.topic, payload)
            except Exception:  # a broken handler must never kill the MQTT thread
                log.exception("handler for %s failed", msg.topic)

    # ------------------------------------------------------------ heartbeat
    def _send_heartbeat(self) -> None:
        self.publish_json(topics.HEARTBEAT, {
            "deviceId": self.device_id,
            "deviceType": self.device_type,
            "uptimeS": int(time.monotonic() - self._started_at),
            "fwVersion": self.fw_version,
            "timestamp": utc_now_iso(),
        })

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.heartbeat_s):
            if self.connected:
                self._send_heartbeat()
