"""Gate state machine - Python twin of firmware/lib/GateLogic (keep them in sync!).

States: CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED, and ERROR.
Rules (same as the ESP32 firmware):
  * OPEN command: CLOSED/CLOSING -> OPENING; already OPEN/OPENING -> success, no-op
  * CLOSE command: refused (success=false, reason VEHICLE_PRESENT) while a vehicle is under the barrier
  * auto-close: AUTO_CLOSE_AFTER_PASS_S after the vehicle has passed, or AUTO_CLOSE_TIMEOUT_S
    after opening if nobody drives through
  * safety: vehicle detected while CLOSING -> reopen immediately
  * MAX_REVERSALS reopenings in a row -> ERROR (stays open); RESET command clears it
  * every command carries a requestId; a repeated requestId is answered again but not executed again
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional

MOVE_S = 1.0
AUTO_CLOSE_AFTER_PASS_S = 2.0
AUTO_CLOSE_TIMEOUT_S = 10.0
MAX_REVERSALS = 3
REMEMBERED_IDS = 8


@dataclass
class GateEvent:
    state: str
    vehicle_present: bool
    request_id: Optional[str]
    success: bool
    reason: Optional[str]
    source: str


@dataclass
class GateSim:
    name: str                                   # ENTRANCE | EXIT
    clock: Callable[[], float]
    state: str = "CLOSED"
    vehicle_present: bool = False
    ack_commands: bool = True                   # False simulates a dead gate (alarm test)
    move_s: float = MOVE_S
    _since: float = 0.0
    _opened_at: float = 0.0
    _passed_at: Optional[float] = None
    _seen_vehicle: bool = False
    _reversals: int = 0
    _ids: Deque[str] = field(default_factory=lambda: deque(maxlen=REMEMBERED_IDS))
    events: List[GateEvent] = field(default_factory=list)

    def _emit(self, request_id=None, success=True, reason=None, source="SENSOR") -> None:
        self.events.append(GateEvent(self.state, self.vehicle_present, request_id, success, reason, source))

    def _set(self, state: str, source: str, request_id: Optional[str] = None) -> None:
        self.state = state
        self._since = self.clock()
        if state == "OPEN":
            self._opened_at = self.clock()
            self._passed_at = None
            self._seen_vehicle = self.vehicle_present
        self._emit(request_id, True, None, source)

    # ------------------------------------------------------------- inputs
    def command(self, command: str, request_id: str, source: str = "MQTT") -> None:
        if not self.ack_commands:
            return
        if request_id in self._ids:
            self._emit(request_id, True, "DUPLICATE", source)
            return
        self._ids.append(request_id)
        cmd = command.upper()
        if cmd == "RESET":
            self._reversals = 0
            self._set("OPEN" if self.vehicle_present else "CLOSING", source, request_id)
        elif self.state == "ERROR":
            self._emit(request_id, False, "ERROR_STATE", source)
        elif cmd == "OPEN":
            if self.state in ("OPEN", "OPENING"):
                if self.state == "OPEN":
                    self._opened_at = self.clock()  # keep it open a little longer
                self._emit(request_id, True, None, source)
            else:
                self._set("OPENING", source, request_id)
        elif cmd == "CLOSE":
            if self.vehicle_present:
                self._emit(request_id, False, "VEHICLE_PRESENT", source)
            elif self.state in ("CLOSED", "CLOSING"):
                self._emit(request_id, True, None, source)
            else:
                self._set("CLOSING", source, request_id)
        else:
            self._emit(request_id, False, "INVALID_COMMAND", source)

    def button(self) -> None:
        """Physical manual-open button."""
        if self.state == "ERROR":
            return
        if self.state in ("CLOSED", "CLOSING"):
            self._set("OPENING", "BUTTON")

    def set_vehicle(self, present: bool) -> None:
        if present == self.vehicle_present:
            return
        self.vehicle_present = present
        if present and self.state == "CLOSING":
            self._reversals += 1
            if self._reversals >= MAX_REVERSALS:
                self.state = "ERROR"
                self._since = self.clock()
                self._emit(None, False, "CLOSE_OBSTRUCTED", "SAFETY")
                return
            self._set("OPENING", "SAFETY")
            return
        if present and self.state == "OPEN":
            self._seen_vehicle = True
        if not present and self.state == "OPEN" and self._seen_vehicle:
            self._passed_at = self.clock()
        self._emit(None, True, None, "SENSOR")

    # --------------------------------------------------------------- time
    def tick(self) -> None:
        now = self.clock()
        if self.state == "OPENING" and now - self._since >= self.move_s:
            self._set("OPEN", "SENSOR")
        elif self.state == "CLOSING" and now - self._since >= self.move_s:
            self._reversals = 0
            self._set("CLOSED", "AUTO_CLOSE")
        elif self.state == "OPEN" and not self.vehicle_present:
            passed = self._passed_at is not None and now - self._passed_at >= AUTO_CLOSE_AFTER_PASS_S
            timeout = now - self._opened_at >= AUTO_CLOSE_TIMEOUT_S
            if passed or timeout:
                self._set("CLOSING", "AUTO_CLOSE")

    def drain(self) -> List[GateEvent]:
        out, self.events = self.events, []
        return out

    def snapshot(self) -> Dict[str, object]:
        return {"state": self.state, "vehiclePresent": self.vehicle_present}
