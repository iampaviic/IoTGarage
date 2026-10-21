"""Local access control: the brain of the edge computer.

Inputs (MQTT):  spot telemetry, gate state (incl. vehicle presence), ALPR events,
                manual operator actions, device status
Outputs (MQTT): ALPR triggers, gate commands, access decisions, session events,
                garage summary, system alerts
Storage:        parking_sessions.SessionStore (SQLite, owned by osoba 8)

Works without ThingsBoard: it only needs the local MQTT broker. All handlers
run on ONE thread (see EventLoop in runner.py) so no locking is needed here,
and every method can be unit-tested by calling it directly with a fake clock.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from garage_contract import topics
from garage_contract.timeutil import to_iso
from parking_sessions import ActiveSessionExists, SessionStore

from edge_service.config import AccessConfig
from edge_service.decisions import AlprInfo, Decision, Thresholds, decide_entry, decide_exit

log = logging.getLogger(__name__)

Publish = Callable[[str, Dict[str, Any], bool], None]   # (topic, payload, retain)
GATE_NAMES = ("entrance", "exit")


@dataclass
class Transaction:
    """A vehicle waiting at a gate until it is let through, denied or leaves."""
    gate: str
    trigger_id: str
    attempt: int = 1
    started: float = 0.0
    waiting_since: float = 0.0          # when the current ALPR trigger was sent
    awaiting_alpr: bool = True
    last_plate: Optional[str] = None
    last_confidence: float = 0.0
    manual_required: bool = False


@dataclass
class PendingCommand:
    request_id: str
    gate: str
    command: str
    sent_at: float
    retries_left: int
    payload: Dict[str, Any] = field(default_factory=dict)


class AccessController:
    def __init__(self, store: SessionStore, publish: Publish, spot_ids: List[str],
                 config: Optional[AccessConfig] = None,
                 clock: Callable[[], float] = time.monotonic,
                 utcnow: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.store = store
        self.publish = publish
        self.cfg = config or AccessConfig()
        self.thresholds = Thresholds(self.cfg.accept_threshold, self.cfg.retry_threshold, self.cfg.max_attempts)
        self.clock = clock
        self.utcnow = utcnow
        self.spots: Dict[str, str] = {s: "UNKNOWN" for s in spot_ids}
        self.spot_seen: Dict[str, float] = {}
        self.spot_device: Dict[str, str] = {}
        self.gates: Dict[str, Dict[str, Any]] = {g: {"state": None, "vehiclePresent": False} for g in GATE_NAMES}
        self.transactions: Dict[str, Transaction] = {}
        self.pending: Dict[str, PendingCommand] = {}
        self.alpr_failures: Dict[str, int] = {g: 0 for g in GATE_NAMES}
        self.active_alerts: Dict[str, bool] = {}
        self._last_summary: Optional[Dict[str, Any]] = None
        self._counter = 0
        self._retry_at: Dict[str, float] = {}

    # ================================================================ helpers
    def _id(self, prefix: str) -> str:
        self._counter += 1
        return "%s-%s-%04d" % (prefix, self.utcnow().strftime("%H%M%S"), self._counter % 10000)

    def _now_iso(self) -> str:
        return to_iso(self.utcnow())

    def available_spots(self) -> int:
        free = sum(1 for s in self.spots.values() if s == "FREE")
        return max(0, min(free, len(self.spots) - self.store.count_active()))

    def summary(self) -> Dict[str, Any]:
        total = len(self.spots)
        free = sum(1 for s in self.spots.values() if s == "FREE")
        occupied = sum(1 for s in self.spots.values() if s == "OCCUPIED")
        unknown = total - free - occupied
        return {
            "totalSpots": total, "freeSpots": free, "occupiedSpots": occupied, "unknownSpots": unknown,
            "occupancyPct": round(100.0 * occupied / total, 1) if total else 0.0,
            "activeSessions": self.store.count_active(), "full": self.available_spots() == 0,
            "timestamp": self._now_iso(),
        }

    def publish_summary(self, force: bool = False) -> None:
        s = self.summary()
        key = {k: v for k, v in s.items() if k != "timestamp"}
        if force or self._last_summary != key:
            self._last_summary = key
            self.publish(topics.GARAGE_SUMMARY, s, True)
            self._alert("GARAGE_FULL", s["full"], "WARNING", "Nema slobodnih mjesta")

    def _alert(self, type_: str, active: bool, severity: str, message: str, **extra: Any) -> None:
        key = type_ + ":" + ":".join(str(v) for v in extra.values())
        if self.active_alerts.get(key, False) == active:
            return
        self.active_alerts[key] = active
        payload = {"type": type_, "severity": severity, "source": "access-control", "message": message,
                   "active": active, "timestamp": self._now_iso()}
        payload.update(extra)
        self.publish(topics.SYSTEM_ALERT, payload, False)
        if active:
            self.store.log_event("ALERT_" + type_, **extra)

    def _decision(self, gate: str, decision: Decision, plate: Optional[str], confidence: Optional[float],
                  gate_request: Optional[str] = None, session_id: Optional[str] = None,
                  manual: bool = False, operator: Optional[str] = None) -> None:
        payload = {
            "decisionId": self._id("dec"), "direction": topics.GATE_TO_DIRECTION[gate], "plate": plate,
            "confidence": None if confidence is None else round(confidence, 3), "decision": decision.decision,
            "reason": decision.reason, "gateRequestId": gate_request, "sessionId": session_id,
            "freeSpots": self.available_spots(), "manual": manual, "operator": operator,
            "timestamp": self._now_iso(),
        }
        self.publish(topics.ACCESS_DECISION, payload, False)
        self.store.log_event("DECISION_" + decision.decision, plate=plate, session_id=session_id,
                             gate=gate, reason=decision.reason, confidence=payload["confidence"], manual=manual,
                             operator=operator)
        log.info("%s %s %s (%s) conf=%s", gate, decision.decision, plate, decision.reason, payload["confidence"])

    def send_gate_command(self, gate: str, command: str, reason: str, plate: Optional[str] = None) -> str:
        rid = self._id("req")
        payload = {"requestId": rid, "command": command, "reason": reason, "plate": plate,
                   "timestamp": self._now_iso()}
        self.pending[rid] = PendingCommand(rid, gate, command, self.clock(), self.cfg.gate_command_retries, payload)
        self.publish(topics.gate_command(gate), payload, False)
        return rid

    def _trigger_alpr(self, tx: Transaction, reason: str) -> None:
        tx.awaiting_alpr = True
        tx.waiting_since = self.clock()
        self.publish(topics.alpr_trigger(tx.gate), {
            "requestId": tx.trigger_id, "reason": reason, "attempt": tx.attempt, "timestamp": self._now_iso()}, False)

    def start_transaction(self, gate: str, reason: str = "VEHICLE_DETECTED") -> Transaction:
        tx = Transaction(gate=gate, trigger_id=self._id("trg-" + gate), started=self.clock())
        self.transactions[gate] = tx
        self._trigger_alpr(tx, reason)
        return tx

    # ============================================================== handlers
    def on_spot(self, topic: str, msg: Dict[str, Any]) -> None:
        spot = msg.get("spotId") or topics.segment(topic, 3)
        if spot not in self.spots:
            log.warning("telemetry for unknown spot %s ignored (GARAGE_SPOTS=%d)", spot, len(self.spots))
            return
        old = self.spots[spot]
        new = msg.get("state", "UNKNOWN")
        if msg.get("sensorStatus") not in ("OK", "SIMULATED"):
            new = "UNKNOWN"  # never treat a broken sensor as a free spot
        self.spots[spot] = new
        self.spot_seen[spot] = self.clock()
        if msg.get("deviceId"):
            self.spot_device[spot] = msg["deviceId"]
        if old != "OCCUPIED" and new == "OCCUPIED":
            self._assign_spot(spot)
        self.publish_summary()

    def _assign_spot(self, spot: str) -> None:
        """Remember which spot the most recently arrived car took (for the demo/history)."""
        horizon = self.utcnow() - timedelta(seconds=self.cfg.spot_assign_window_s)
        recent = [s for s in self.store.active_sessions() if s.spot_id is None and s.entry_time >= horizon]
        if recent:
            self.store.assign_spot(recent[-1].id, spot)

    def on_device_status(self, topic: str, msg: Dict[str, Any]) -> None:
        device = msg.get("deviceId") or topics.segment(topic, 3)
        if msg.get("online") is False:
            changed = False
            for spot, dev in self.spot_device.items():
                if dev == device and self.spots.get(spot) != "UNKNOWN":
                    self.spots[spot] = "UNKNOWN"
                    changed = True
            if changed:
                self._alert("SENSOR_OFFLINE", True, "MAJOR", "Senzorski uredaj %s nije dostupan" % device,
                            deviceId=device)
                self.publish_summary()
        elif msg.get("online") is True:
            self._alert("SENSOR_OFFLINE", False, "MAJOR", "Senzorski uredaj %s ponovno dostupan" % device,
                        deviceId=device)

    def on_gate_state(self, topic: str, msg: Dict[str, Any]) -> None:
        gate = topics.segment(topic, 2)
        if gate not in self.gates:
            return
        g = self.gates[gate]
        was_present = g.get("vehiclePresent", False)
        g.update(state=msg.get("state"), vehiclePresent=bool(msg.get("vehiclePresent")))

        rid = msg.get("requestId")
        if rid and rid in self.pending:
            cmd = self.pending.pop(rid)
            if msg.get("success"):
                self._alert("GATE_NO_ACK", False, "MAJOR", "Rampa ponovno potvrduje naredbe",
                            gate=topics.GATE_TO_PAYLOAD[gate])
            else:
                log.warning("gate %s refused %s: %s", gate, cmd.command, msg.get("reason"))
                self.store.log_event("GATE_REFUSED", gate=gate, command=cmd.command, reason=msg.get("reason"))

        present = g["vehiclePresent"]
        tx = self.transactions.get(gate)
        if present and not was_present and tx is None and g["state"] in ("CLOSED", "CLOSING", "ERROR"):
            self.start_transaction(gate)
        elif not present and was_present and tx is not None and not tx.awaiting_alpr and g["state"] in ("OPEN", "CLOSING", "CLOSED"):
            # vehicle passed (gate was opened) or drove away
            self.transactions.pop(gate, None)
        elif not present and was_present and tx is not None and g["state"] == "CLOSED":
            log.info("vehicle left %s before a decision", gate)
            self.transactions.pop(gate, None)

    def on_alpr_event(self, topic: str, msg: Dict[str, Any]) -> None:
        gate = topics.segment(topic, 2)
        if gate not in self.gates:
            return
        tx = self.transactions.get(gate)
        if tx is None:
            g = self.gates[gate]
            if not g["vehiclePresent"] and g["state"] is not None:
                # late answer for a vehicle that already left: never open the gate for nobody
                log.info("ignoring ALPR event %s: no vehicle at %s", msg.get("requestId"), gate)
                return
            # trigger sent by a tool (or no gate controller connected yet): treat as a new vehicle
            tx = Transaction(gate=gate, trigger_id=msg.get("requestId", "?"), started=self.clock())
            self.transactions[gate] = tx
        elif msg.get("requestId") != tx.trigger_id:
            log.info("ignoring stale ALPR event %s (waiting for %s)", msg.get("requestId"), tx.trigger_id)
            return
        tx.awaiting_alpr = False
        alpr = AlprInfo(status=msg.get("status", "NO_PLATE"), plate=msg.get("plate"),
                        confidence=float(msg.get("ocrConfidence") or 0.0))
        if alpr.plate:
            tx.last_plate, tx.last_confidence = alpr.plate, alpr.confidence
        self._decide(tx, alpr)

    def _decide(self, tx: Transaction, alpr: AlprInfo) -> None:
        gate = tx.gate
        if gate == "entrance":
            already = bool(alpr.plate) and self.store.find_active(alpr.plate) is not None
            allowed = bool(alpr.plate) and self.store.is_allowed(alpr.plate)
            d = decide_entry(alpr, self.thresholds, tx.attempt, self.available_spots(), already,
                             self.cfg.policy == "allowlist", allowed)
        else:
            session = self._find_exit_session(alpr.plate) if alpr.plate else None
            d = decide_exit(alpr, self.thresholds, tx.attempt, session is not None)

        ok_reading = d.decision in ("GRANTED", "DENIED")
        self.alpr_failures[gate] = 0 if ok_reading else self.alpr_failures[gate] + 1
        if self.alpr_failures[gate] >= self.cfg.alpr_failure_alert_after:
            self._alert("ALPR_REPEATED_FAILURE", True, "MAJOR",
                        "ALPR na %s %d puta zaredom bez pouzdanog ocitanja" % (gate, self.alpr_failures[gate]),
                        gate=topics.GATE_TO_PAYLOAD[gate])
        elif ok_reading:
            self._alert("ALPR_REPEATED_FAILURE", False, "MAJOR", "ALPR ponovno radi", gate=topics.GATE_TO_PAYLOAD[gate])

        if d.decision == "GRANTED":
            if gate == "entrance":
                self._grant_entry(tx, alpr.plate, alpr.confidence, manual=False)  # type: ignore[arg-type]
            else:
                self._grant_exit(tx, alpr.plate, alpr.confidence, manual=False)  # type: ignore[arg-type]
        elif d.decision == "RETRY":
            self._decision(gate, d, alpr.plate, alpr.confidence)
            tx.attempt += 1
            self._retry_at[gate] = self.clock() + self.cfg.retry_delay_s
        elif d.decision == "MANUAL_REQUIRED":
            tx.manual_required = True
            self._decision(gate, d, alpr.plate or tx.last_plate, alpr.confidence)
        else:  # DENIED - vehicle has to back out, or an operator overrides
            tx.manual_required = True
            self._decision(gate, d, alpr.plate, alpr.confidence)

    def _find_exit_session(self, plate: str):
        session = self.store.find_active(plate)
        if session is None and self.cfg.exit_fuzzy_match:
            similar = self.store.find_active_similar(plate, 1)
            if len(similar) == 1:
                session = similar[0]
                self.store.log_event("EXIT_FUZZY_MATCH", plate=plate, session_id=session.id, matched=session.plate)
        return session

    def _grant_entry(self, tx: Transaction, plate: str, confidence: Optional[float], manual: bool,
                     operator: Optional[str] = None) -> None:
        try:
            session = self.store.open_session(plate, entry_time=self.utcnow(), confidence=confidence,
                                              mode="MANUAL" if manual else "AUTO",
                                              note="operator %s" % operator if operator else None)
        except ActiveSessionExists:
            self._decision(tx.gate, Decision("DENIED", "ALREADY_INSIDE"), plate, confidence, manual=manual,
                           operator=operator)
            return
        rid = self.send_gate_command("entrance", "OPEN", "MANUAL" if manual else "AUTHORIZED_ENTRY", plate)
        reason = "MANUAL_APPROVAL" if manual else "AUTHORIZED"
        self._decision("entrance", Decision("GRANTED", reason), plate, confidence, rid, session.id, manual, operator)
        self.publish(topics.SESSION_EVENT, session.to_event("SESSION_OPENED", self.utcnow()), False)
        tx.awaiting_alpr = False
        tx.manual_required = False
        self.publish_summary()

    def _grant_exit(self, tx: Transaction, plate: str, confidence: Optional[float], manual: bool,
                    operator: Optional[str] = None) -> None:
        session = self._find_exit_session(plate)
        session_id = None
        if session is not None:
            closed = self.store.close_session(session.id, exit_time=self.utcnow(), confidence=confidence,
                                              mode="MANUAL" if manual else "AUTO")
            session_id = closed.id
            self.publish(topics.SESSION_EVENT, closed.to_event("SESSION_CLOSED", self.utcnow()), False)
        elif manual:
            self.store.log_event("EXIT_WITHOUT_SESSION", plate=plate, operator=operator)
        rid = self.send_gate_command("exit", "OPEN", "MANUAL" if manual else "AUTHORIZED_EXIT", plate)
        reason = "MANUAL_APPROVAL" if manual else "AUTHORIZED"
        self._decision("exit", Decision("GRANTED", reason), plate, confidence, rid, session_id, manual, operator)
        tx.awaiting_alpr = False
        tx.manual_required = False
        self.publish_summary()

    def on_manual(self, topic: str, msg: Dict[str, Any]) -> None:
        action = msg.get("action")
        operator = msg.get("operator") or "operator"
        gate_payload = msg.get("gate") or ("ENTRANCE" if action == "APPROVE_ENTRY" else "EXIT")
        gate = gate_payload.lower()
        if gate not in self.gates:
            log.warning("manual action for unknown gate %r", gate_payload)
            return
        self.store.log_event("MANUAL_" + str(action), plate=msg.get("plate"), operator=operator,
                             note=msg.get("note"), gate=gate)
        tx = self.transactions.get(gate) or Transaction(gate=gate, trigger_id="manual", started=self.clock(),
                                                        awaiting_alpr=False)
        self.transactions[gate] = tx
        plate = msg.get("plate") or tx.last_plate
        if plate:
            plate = plate.upper().replace(" ", "").replace("-", "")
        if action == "APPROVE_ENTRY":
            if plate:
                self._grant_entry(tx, plate, None, manual=True, operator=operator)
            else:
                rid = self.send_gate_command("entrance", "OPEN", "MANUAL")
                self._decision("entrance", Decision("GRANTED", "MANUAL_APPROVAL"), None, None, rid,
                               manual=True, operator=operator)
        elif action == "APPROVE_EXIT":
            self._grant_exit(tx, plate or "UNKNOWN", None, manual=True, operator=operator)
        elif action == "DENY":
            self._decision(gate, Decision("DENIED", "MANUAL_DENIAL"), plate, None, manual=True, operator=operator)
            self.transactions.pop(gate, None)
        elif action in ("OPEN_GATE", "CLOSE_GATE"):
            self.send_gate_command(gate, "OPEN" if action == "OPEN_GATE" else "CLOSE", "MANUAL", plate)

    # ================================================================= timers
    def tick(self) -> None:
        now = self.clock()
        # gate command acknowledgements
        for rid, cmd in list(self.pending.items()):
            if now - cmd.sent_at < self.cfg.gate_ack_timeout_s:
                continue
            if cmd.retries_left > 0:
                cmd.retries_left -= 1
                cmd.sent_at = now
                log.warning("no ack for %s on %s gate, resending", rid, cmd.gate)
                self.publish(topics.gate_command(cmd.gate), cmd.payload, False)  # same requestId: gate dedups
            else:
                self.pending.pop(rid)
                self._alert("GATE_NO_ACK", True, "MAJOR",
                            "Rampa %s nije potvrdila naredbu %s (%s)" % (cmd.gate, cmd.command, rid),
                            gate=topics.GATE_TO_PAYLOAD[cmd.gate])
        # scheduled ALPR retries
        for gate, at in list(self._retry_at.items()):
            if now >= at:
                del self._retry_at[gate]
                tx = self.transactions.get(gate)
                if tx is not None:
                    self._trigger_alpr(tx, "RETRY")
        # ALPR service not answering
        for gate, tx in list(self.transactions.items()):
            if tx.awaiting_alpr and now - tx.waiting_since > self.cfg.alpr_timeout_s:
                log.warning("no ALPR answer for %s on %s", tx.trigger_id, gate)
                tx.awaiting_alpr = False
                self._decide(tx, AlprInfo("CAMERA_ERROR", None, 0.0))
        # stale spot sensors -> UNKNOWN
        changed = False
        for spot, seen in self.spot_seen.items():
            if self.spots[spot] != "UNKNOWN" and now - seen > self.cfg.spot_timeout_s:
                log.warning("no data from %s for %.0f s -> UNKNOWN", spot, now - seen)
                self.spots[spot] = "UNKNOWN"
                changed = True
        if changed:
            self.publish_summary()
