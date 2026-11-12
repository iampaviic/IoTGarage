"""Gate node simulator for varijanta B: behaves like the gate ESP32 towards ThingsBoard.

    python gate_simulator_tb.py                  # both gates
    python gate_simulator_tb.py --no-ack exit    # exit gate ignores commands (alarm test)
    TB_HOST=192.168.1.20 TB_MQTT_PORT=1883 TB_TOKEN_GATES=... python gate_simulator_tb.py

Keyboard (type + ENTER):
    e / x      toggle vehicle under the ENTRANCE / EXIT barrier
    be / bx    press the manual button of ENTRANCE / EXIT
    s          print states            q   quit

ThingsBoard sees the gateway device "esp32-gates" and its devices EntranceGate and ExitGate:
    telemetry   {state, stateCode, vehiclePresent, lastSource} on every change, every 30 s
                {vehicleArrived: true, ...} when a vehicle reaches a CLOSED gate -> rule chain asks ALPR
    RPC         open | close | reset | deny  ->  answer {"success", "state", "reason"}
The gate logic is the same state machine as the firmware (gate_sim.py <-> lib/GateLogic).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
import uuid
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_sim import GateSim  # noqa: E402

from garage_contract.tb import GATE_DEVICES, GATE_STATE_CODE, GATES_GATEWAY, TbGateway, TbSettings  # noqa: E402

FW_VERSION = "sim-b"
COMMANDS = {"open": "OPEN", "close": "CLOSE", "reset": "RESET"}


class GateNodeSim:
    def __init__(self, settings: TbSettings, no_ack=(), periodic_s: float = 30.0, verbose: bool = True) -> None:
        self.lock = threading.Lock()
        self.verbose = verbose
        self.gates: Dict[str, GateSim] = {g: GateSim(g, time.monotonic, ack_commands=g not in no_ack)
                                          for g in GATE_DEVICES}
        self.periodic_s = periodic_s
        self.started = time.monotonic()
        self.gw = TbGateway(GATES_GATEWAY, settings, {d: "Gate" for d in GATE_DEVICES.values()})
        self.gw.on_connect = self.publish_all
        self.gw.on_device_rpc = self.on_device_rpc

    def _values(self, gate: GateSim, source: str) -> dict:
        return {"state": gate.state, "stateCode": GATE_STATE_CODE[gate.state],
                "vehiclePresent": gate.vehicle_present, "lastSource": source}

    def publish_events(self) -> None:
        for name, gate in self.gates.items():
            for ev in gate.drain():
                values = {"state": ev.state, "stateCode": GATE_STATE_CODE[ev.state],
                          "vehiclePresent": ev.vehicle_present, "lastSource": ev.source}
                self.gw.device_telemetry(GATE_DEVICES[name], values)
                if self.verbose:
                    print("[%s] %-8s present=%s %s" % (name, ev.state, ev.vehicle_present, ev.reason or ""))

    def publish_all(self) -> None:
        with self.lock:
            self.gw.attributes({"fwVersion": FW_VERSION, "deviceType": "GATE_CONTROLLER"})
            for name, gate in self.gates.items():
                self.gw.device_telemetry(GATE_DEVICES[name], self._values(gate, "BOOT"))
            self.gw.telemetry({"uptimeS": int(time.monotonic() - self.started), "rssi": -60, "fwVersion": FW_VERSION})

    # ------------------------------------------------------------- inputs
    def set_vehicle(self, name: str, present: bool) -> None:
        with self.lock:
            gate = self.gates[name]
            arrived = present and not gate.vehicle_present and gate.state == "CLOSED"
            gate.set_vehicle(present)
            self.publish_events()
            if arrived:   # the rule chain starts the ALPR reading on this event
                self.gw.device_telemetry(GATE_DEVICES[name], dict(self._values(gate, "SENSOR"), vehicleArrived=True))

    def button(self, name: str) -> None:
        with self.lock:
            self.gates[name].button()
            self.publish_events()

    def on_device_rpc(self, device: str, method: str, params: dict) -> Optional[dict]:
        name = {v: k for k, v in GATE_DEVICES.items()}.get(device)
        if name is None:
            return None
        if not self.gates[name].ack_commands:
            time.sleep(30)   # dead gate: ThingsBoard times out
            return None
        with self.lock:
            gate = self.gates[name]
            if method == "deny":   # firmware: short red blink + beep; the barrier stays closed
                return {"success": True, "state": gate.state, "reason": None}
            if method not in COMMANDS:
                return {"success": False, "state": gate.state, "reason": "INVALID_COMMAND"}
            rid = str(uuid.uuid4())
            gate.command(COMMANDS[method], rid, "RPC")
            events = gate.events[:]
            self.publish_events()
        answer = next((e for e in events if e.request_id == rid), None)
        if answer is None:
            return {"success": False, "state": gate.state, "reason": "NO_ANSWER"}
        return {"success": answer.success, "state": answer.state, "reason": answer.reason}

    def loop_forever(self, stop: threading.Event) -> None:
        last = time.monotonic()
        while not stop.is_set():
            with self.lock:
                for gate in self.gates.values():
                    gate.tick()
                self.publish_events()
            if time.monotonic() - last > self.periodic_s:
                last = time.monotonic()
                if self.gw.connected.is_set():
                    self.publish_all()
            stop.wait(0.05)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-ack", nargs="*", default=[], choices=["entrance", "exit"], help="gates that ignore commands")
    ap.add_argument("--no-keyboard", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sim = GateNodeSim(TbSettings.from_env("TB_TOKEN_GATES", "esp32-gates-token"),
                      no_ack=[g.upper() for g in args.no_ack])
    if not sim.gw.start():
        print("ThingsBoard %s:%s not reachable yet - retrying" % (sim.gw.settings.host, sim.gw.settings.port))
    stop = threading.Event()
    threading.Thread(target=sim.loop_forever, args=(stop,), daemon=True).start()
    if args.no_keyboard:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print(__doc__)
        for line in sys.stdin:
            cmd = line.strip().lower()
            if cmd in ("e", "x"):
                name = "ENTRANCE" if cmd == "e" else "EXIT"
                sim.set_vehicle(name, not sim.gates[name].vehicle_present)
            elif cmd in ("be", "bx"):
                sim.button("ENTRANCE" if cmd == "be" else "EXIT")
            elif cmd == "s":
                print({n: g.snapshot() for n, g in sim.gates.items()})
            elif cmd == "q":
                break
    stop.set()
    sim.gw.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
