"""Drive a simulated vehicle through the whole system over MQTT.

Used by simulacija.py (demo without hardware) and by tests/test_e2e.py.
Works against simulators AND against the real model: on the real model the
sim topics are simply ignored and you move the car by hand while the driver
waits for the same messages.

    drv = Driver(MqttSettings(host="localhost"))
    drv.start()
    drv.drive_in("ZG1234AB", spot="P03")
    drv.drive_out("ZG1234AB", spot="P03")
    print(drv.timeline())
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from garage_contract import MqttSettings, topics
from garage_contract.mqtt import MqttConnection
from garage_contract.validation import errors_for, message_type_for_topic


class ScenarioError(AssertionError):
    pass


class Driver:
    def __init__(self, settings: Optional[MqttSettings] = None, verbose: bool = True) -> None:
        self.conn = MqttConnection("scenario-driver-%d" % int(time.time() * 1000 % 100000), settings)
        self.messages: List[Tuple[float, str, Dict[str, Any]]] = []
        self.contract_errors: List[str] = []
        self.lock = threading.Condition()
        self.t0 = time.monotonic()
        self.verbose = verbose

    def start(self) -> "Driver":
        self.conn.subscribe("garage/#", self._on_message)
        if not self.conn.start(10):
            raise ScenarioError("MQTT broker not reachable")
        time.sleep(0.3)
        return self

    def stop(self) -> None:
        self.conn.stop()

    def _on_message(self, topic: str, payload: Any) -> None:
        mt = message_type_for_topic(topic)
        if mt:
            errs = errors_for(mt, payload)
            if errs:
                self.contract_errors.append("%s: %s" % (topic, errs))
        with self.lock:
            self.messages.append((time.monotonic() - self.t0, topic, payload))
            self.lock.notify_all()
        if self.verbose and not topic.startswith("garage/system/heartbeat"):
            print("  %6.2fs %-36s %s" % (time.monotonic() - self.t0, topic, _short(payload)))

    # ---------------------------------------------------------------- waits
    def mark(self) -> int:
        with self.lock:
            return len(self.messages)

    def wait_for(self, topic: str, pred: Callable[[Dict[str, Any]], bool] = lambda p: True,
                 timeout: float = 15.0, since: Optional[int] = None) -> Dict[str, Any]:
        start = since if since is not None else self.mark()
        deadline = time.monotonic() + timeout
        with self.lock:
            while True:
                for _, t, p in self.messages[start:]:
                    if t == topic and isinstance(p, dict) and pred(p):
                        return p
                left = deadline - time.monotonic()
                if left <= 0:
                    raise ScenarioError("timeout waiting for %s" % topic)
                self.lock.wait(left)

    def pub(self, topic: str, payload: Dict[str, Any], retain: bool = False) -> None:
        self.conn.publish_json(topic, payload, retain=retain)

    # -------------------------------------------------------------- actions
    def vehicle_at(self, gate: str, plate: Optional[str], quality: str = "good") -> None:
        self.pub(topics.sim_vehicle(gate), {"plate": plate, "quality": quality}, retain=True)

    def presence(self, gate: str, present: bool) -> None:
        self.pub(topics.sim_gate_presence(gate), {"present": present})

    def spot(self, spot: str, occupied: Optional[bool]) -> None:
        self.pub(topics.sim_spot(spot), {"occupied": occupied})

    def arrive(self, gate: str, plate: str, quality: str = "good") -> Dict[str, Any]:
        """Vehicle stops at the barrier; returns the final decision (GRANTED/DENIED/MANUAL_REQUIRED)."""
        self.vehicle_at(gate, plate, quality)
        time.sleep(0.2)
        since = self.mark()
        self.presence(gate, True)
        direction = topics.GATE_TO_DIRECTION[gate]
        return self.wait_for(topics.ACCESS_DECISION,
                             lambda p: p["direction"] == direction and p["decision"] != "RETRY",
                             timeout=30, since=since)

    def latest(self, topic: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for _, t, p in reversed(self.messages):
                if t == topic:
                    return p
        return None

    def pass_gate(self, gate: str) -> None:
        state = self.latest(topics.gate_state(gate))
        if not state or state.get("state") != "OPEN":
            self.wait_for(topics.gate_state(gate), lambda p: p["state"] == "OPEN", timeout=10)
        since = self.mark()
        self.presence(gate, False)
        self.vehicle_at(gate, None)
        self.wait_for(topics.gate_state(gate), lambda p: p["state"] == "CLOSED", timeout=20, since=since)

    def drive_in(self, plate: str, spot: Optional[str] = None) -> Dict[str, Any]:
        decision = self.arrive("entrance", plate)
        if decision["decision"] != "GRANTED":
            raise ScenarioError("entry not granted: %s" % json.dumps(decision))
        self.pass_gate("entrance")
        if spot:
            since = self.mark()
            self.spot(spot, True)
            self.wait_for(topics.GARAGE_SUMMARY, lambda p: True, since=since)
        return decision

    def drive_out(self, plate: str, spot: Optional[str] = None) -> Dict[str, Any]:
        if spot:
            self.spot(spot, False)
        since = self.mark()
        decision = self.arrive("exit", plate)
        if decision["decision"] != "GRANTED":
            raise ScenarioError("exit not granted: %s" % json.dumps(decision))
        closed = self.wait_for(topics.SESSION_EVENT, lambda p: p["eventType"] == "SESSION_CLOSED"
                               and p["plate"] == plate, since=since)
        self.pass_gate("exit")
        return closed

    def manual(self, action: str, gate: str, plate: Optional[str] = None, note: str = "scenario") -> None:
        self.pub(topics.ACCESS_MANUAL, {"requestId": "man-%d" % int(time.time() * 1000), "action": action,
                                        "gate": gate.upper(), "plate": plate, "operator": "scenario",
                                        "note": note, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    def timeline(self) -> str:
        return "\n".join("%6.2fs %-36s %s" % (t, topic, _short(p)) for t, topic, p in self.messages
                         if not topic.startswith("garage/system/heartbeat"))


def _short(p: Any) -> str:
    if not isinstance(p, dict):
        return str(p)
    keys = ("spotId", "state", "gate", "command", "requestId", "reason", "plate", "status", "ocrConfidence",
            "decision", "eventType", "durationS", "price", "freeSpots", "type", "active", "online", "deviceId")
    return " ".join("%s=%s" % (k, p[k]) for k in keys if k in p and p[k] is not None)
