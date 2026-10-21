"""Local MQTT (Mosquitto) -> ThingsBoard bridge with an offline buffer.

Every local message is first written to a small SQLite queue and only removed
after ThingsBoard has acknowledged it (MQTT QoS 1 PUBACK). If ThingsBoard or
the network is down, data piles up locally and is sent - with the original
timestamps - when the connection returns (degraded mode from the project plan).

Dashboard buttons call RPC on ThingsBoard devices; the bridge turns them into
garage/access/manual messages so access control executes AND logs them.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from garage_contract import MqttSettings, topics
from garage_contract.mqtt import MqttConnection, new_paho_client
from garage_contract.timeutil import utc_now_iso

from tb_bridge.mapping import ALPR_DEVICES, GATE_DEVICES, GATEWAY_NAME, Mapper

log = logging.getLogger(__name__)

GATEWAY_TELEMETRY = "v1/gateway/telemetry"
GATEWAY_CONNECT = "v1/gateway/connect"
GATEWAY_RPC = "v1/gateway/rpc"
DEVICE_TELEMETRY = "v1/devices/me/telemetry"
DEVICE_RPC_REQUEST = "v1/devices/me/rpc/request/+"


class Buffer:
    """Persistent FIFO of (device, type, ts, values)."""

    def __init__(self, path: str, max_rows: int = 200000) -> None:
        self.max_rows = max_rows
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("CREATE TABLE IF NOT EXISTS q (id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT,"
                        " type TEXT, ts INTEGER, data TEXT)")
        self.lock = threading.Lock()

    def put(self, device: Optional[str], type_: str, ts: int, values: Dict[str, Any]) -> None:
        with self.lock:
            self.db.execute("INSERT INTO q (device, type, ts, data) VALUES (?,?,?,?)",
                            (device, type_, ts, json.dumps(values)))
            n = self.db.execute("SELECT COUNT(*) FROM q").fetchone()[0]
            if n > self.max_rows:  # protect the SD card: drop the oldest
                self.db.execute("DELETE FROM q WHERE id IN (SELECT id FROM q ORDER BY id LIMIT ?)", (n - self.max_rows,))

    def peek(self, limit: int = 50) -> List[Tuple[int, Optional[str], str, int, Dict[str, Any]]]:
        with self.lock:
            rows = self.db.execute("SELECT id, device, type, ts, data FROM q ORDER BY id LIMIT ?", (limit,)).fetchall()
        return [(r[0], r[1], r[2], r[3], json.loads(r[4])) for r in rows]

    def delete(self, ids: List[int]) -> None:
        with self.lock:
            self.db.executemany("DELETE FROM q WHERE id = ?", [(i,) for i in ids])

    def size(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM q").fetchone()[0]


class ThingsBoardBridge:
    def __init__(self, local: MqttSettings, tb_host: str, tb_port: int, token: str,
                 buffer_path: str = "buffer.db") -> None:
        self.mapper = Mapper()
        self.buffer = Buffer(buffer_path)
        self.local = MqttConnection("tb-bridge", local, device_id="tb-bridge", device_type="TB_BRIDGE")
        self.local.subscribe("garage/#", self.on_local)
        self.tb_host, self.tb_port = tb_host, tb_port
        self.tb = new_paho_client("garage-edge-gateway")
        self.tb.username_pw_set(token)
        self.tb.reconnect_delay_set(1, 30)
        self.tb.on_connect = self._tb_connected
        self.tb.on_disconnect = self._tb_disconnected
        self.tb.on_message = self._tb_message
        self.tb_ok = threading.Event()
        self.known: Dict[str, str] = {}  # device -> type, announced with v1/gateway/connect
        self.stop_ev = threading.Event()
        self.sent = 0

    # ------------------------------------------------------------ local side
    def on_local(self, topic: str, msg: Any) -> None:
        if not isinstance(msg, dict) or topic.startswith("garage/sim/"):
            return
        for device, type_, ts, values in self.mapper.map(topic, msg, int(time.time() * 1000)):
            self.buffer.put(device, type_, ts, {k: v for k, v in values.items() if v is not None})

    # --------------------------------------------------------- ThingsBoard side
    def _tb_connected(self, client, userdata, flags, rc, *args) -> None:
        if int(getattr(rc, "value", rc)) != 0:
            log.error("ThingsBoard refused the connection (rc=%s) - wrong gateway token?", rc)
            return
        log.info("connected to ThingsBoard %s:%s", self.tb_host, self.tb_port)
        client.subscribe(GATEWAY_RPC, qos=1)
        client.subscribe(DEVICE_RPC_REQUEST, qos=1)
        self.known.clear()
        self.tb_ok.set()

    def _tb_disconnected(self, client, userdata, *args) -> None:
        if self.tb_ok.is_set():
            log.warning("ThingsBoard connection lost - buffering locally")
        self.tb_ok.clear()

    def _announce(self, device: str, type_: str) -> None:
        if self.known.get(device) != type_:
            self.tb.publish(GATEWAY_CONNECT, json.dumps({"device": device, "type": type_}), qos=1)
            self.known[device] = type_

    def flush_once(self, batch: int = 50) -> int:
        """Send up to `batch` buffered records; returns how many were acknowledged."""
        rows = self.buffer.peek(batch)
        if not rows or not self.tb_ok.is_set():
            return 0
        gateway: List[Dict[str, Any]] = []
        devices: Dict[str, List[Dict[str, Any]]] = {}
        for _, device, type_, ts, values in rows:
            if device is None or device == GATEWAY_NAME:
                gateway.append({"ts": ts, "values": values})
            else:
                self._announce(device, type_)
                devices.setdefault(device, []).append({"ts": ts, "values": values})
        infos = []
        if devices:
            infos.append(self.tb.publish(GATEWAY_TELEMETRY, json.dumps(devices), qos=1))
        if gateway:
            infos.append(self.tb.publish(DEVICE_TELEMETRY, json.dumps(gateway), qos=1))
        for info in infos:
            try:
                info.wait_for_publish(timeout=10)
            except Exception:  # not connected any more
                return 0
            if not info.is_published():
                return 0
        self.buffer.delete([r[0] for r in rows])
        self.sent += len(rows)
        return len(rows)

    def _tb_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except ValueError:
            return
        if msg.topic == GATEWAY_RPC:
            device, rpc = data.get("device"), data.get("data", {})
            result = self.handle_rpc(device, rpc.get("method", ""), rpc.get("params") or {})
            client.publish(GATEWAY_RPC, json.dumps({"device": device, "id": rpc.get("id"), "data": result}), qos=1)
        elif msg.topic.startswith("v1/devices/me/rpc/request/"):
            req_id = msg.topic.rsplit("/", 1)[1]
            result = self.handle_rpc(GATEWAY_NAME, data.get("method", ""), data.get("params") or {})
            client.publish("v1/devices/me/rpc/response/" + req_id, json.dumps(result), qos=1)

    def handle_rpc(self, device: str, method: str, params: Any) -> Dict[str, Any]:
        """Dashboard buttons -> manual operator actions (executed and logged by access control)."""
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except ValueError:
                params = {"plate": params}
        params = params if isinstance(params, dict) else {}
        gate = {v: k for k, v in GATE_DEVICES.items()}.get(device) or {v: k for k, v in ALPR_DEVICES.items()}.get(device)
        m = method.lower()
        action = None
        if m in ("open", "close") and gate:
            action = {"action": "OPEN_GATE" if m == "open" else "CLOSE_GATE", "gate": gate.upper()}
        elif m == "reset" and gate:
            self.local.publish_json(topics.gate_command(gate), {"requestId": "tb-%d" % int(time.time() * 1000),
                                                               "command": "RESET", "reason": "MANUAL",
                                                               "timestamp": utc_now_iso()})
            return {"success": True}
        elif m in ("approveentry", "approve_entry"):
            action = {"action": "APPROVE_ENTRY", "gate": "ENTRANCE"}
        elif m in ("approveexit", "approve_exit"):
            action = {"action": "APPROVE_EXIT", "gate": "EXIT"}
        elif m == "deny":
            action = {"action": "DENY", "gate": (params.get("gate") or "ENTRANCE").upper()}
        if action is None:
            return {"success": False, "error": "unknown method %s for %s" % (method, device)}
        plate = (params.get("plate") or "").upper().replace(" ", "").replace("-", "") or None
        payload = dict(action, requestId="tb-%d" % int(time.time() * 1000), plate=plate,
                       operator=params.get("operator") or "thingsboard",
                       note=params.get("note") or "ThingsBoard dashboard", timestamp=utc_now_iso())
        ok = self.local.publish_json(topics.ACCESS_MANUAL, payload)
        log.info("RPC %s.%s -> %s", device, method, payload["action"])
        return {"success": bool(ok)}

    # ------------------------------------------------------------------ run
    def run(self) -> None:
        self.local.start()
        self.tb.connect_async(self.tb_host, self.tb_port, keepalive=30)
        self.tb.loop_start()
        last_report = time.monotonic()
        while not self.stop_ev.is_set():
            sent = self.flush_once()
            if time.monotonic() - last_report > 60:
                last_report = time.monotonic()
                log.info("sent %d records, %d waiting in buffer, ThingsBoard %s",
                         self.sent, self.buffer.size(), "connected" if self.tb_ok.is_set() else "OFFLINE")
            if not sent:
                self.stop_ev.wait(0.2)

    def stop(self) -> None:
        self.stop_ev.set()
        self.tb.loop_stop()
        self.tb.disconnect()
        self.local.stop()


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="garage/# -> ThingsBoard gateway bridge")
    ap.add_argument("--tb-host", default=os.environ.get("TB_HOST", "localhost"))
    ap.add_argument("--tb-port", type=int, default=int(os.environ.get("TB_MQTT_PORT", "1884")))
    ap.add_argument("--token", default=os.environ.get("TB_GATEWAY_TOKEN", "garage-edge-gateway-token"),
                    help="access token of the Garage-Edge gateway device (provision.py sets it)")
    ap.add_argument("--buffer", default=os.environ.get("TB_BUFFER", "data/tb-buffer.db"))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    os.makedirs(os.path.dirname(os.path.abspath(args.buffer)), exist_ok=True)
    bridge = ThingsBoardBridge(MqttSettings.from_env(), args.tb_host, args.tb_port, args.token, args.buffer)
    try:
        bridge.run()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
