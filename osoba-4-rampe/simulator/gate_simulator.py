"""Gate simulator: behaves like the gate ESP32 on MQTT (no hardware needed).

    python gate_simulator.py                 # both gates
    python gate_simulator.py --no-ack exit   # exit gate ignores commands (alarm test)

Keyboard (type + ENTER):
    e / x      toggle vehicle under the ENTRANCE / EXIT barrier
    be / bx    press the manual button of ENTRANCE / EXIT
    s          print states
    q          quit
Vehicle presence can also be set by other tools on garage/sim/gate/<gate>/presence.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_sim import GateSim  # noqa: E402

from garage_contract import MqttSettings, topics  # noqa: E402
from garage_contract.mqtt import MqttConnection  # noqa: E402
from garage_contract.timeutil import utc_now_iso  # noqa: E402

DEVICE_ID = "sim-gates"


class GateSimulator:
    def __init__(self, conn: MqttConnection, no_ack=(), periodic_s: float = 30.0) -> None:
        self.conn = conn
        self.lock = threading.Lock()
        self.gates = {g: GateSim(topics.GATE_TO_PAYLOAD[g], time.monotonic, ack_commands=g not in no_ack)
                      for g in topics.GATES}
        self.periodic_s = periodic_s
        self._last_periodic = 0.0

    def publish_events(self) -> None:
        for name, gate in self.gates.items():
            for ev in gate.drain():
                self._publish(name, gate, ev.request_id, ev.success, ev.reason, ev.source, ev.state, ev.vehicle_present)

    def _publish(self, name, gate, request_id, success, reason, source, state=None, present=None) -> None:
        payload = {"gate": gate.name, "state": state or gate.state,
                   "vehiclePresent": gate.vehicle_present if present is None else present,
                   "requestId": request_id, "success": success, "reason": reason, "source": source,
                   "deviceId": DEVICE_ID, "timestamp": utc_now_iso()}
        self.conn.publish_json(topics.gate_state(name), payload, retain=True)
        print("[%s] %-8s present=%s %s %s" % (name, payload["state"], payload["vehiclePresent"],
                                              request_id or "", reason or ""))

    def on_command(self, topic, msg) -> None:
        name = topics.segment(topic, 2)
        with self.lock:
            self.gates[name].command(msg.get("command", ""), msg.get("requestId", ""), "MQTT")
            self.publish_events()

    def on_presence(self, topic, msg) -> None:
        name = topics.segment(topic, 3)
        with self.lock:
            self.gates[name].set_vehicle(bool(msg.get("present")))
            self.publish_events()

    def loop_forever(self, stop: threading.Event) -> None:
        with self.lock:
            for name, gate in self.gates.items():
                self._publish(name, gate, None, True, None, "BOOT")
        while not stop.is_set():
            with self.lock:
                for gate in self.gates.values():
                    gate.tick()
                self.publish_events()
                if time.monotonic() - self._last_periodic > self.periodic_s:
                    self._last_periodic = time.monotonic()
                    for name, gate in self.gates.items():
                        self._publish(name, gate, None, True, None, "PERIODIC")
            stop.wait(0.05)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-ack", nargs="*", default=[], choices=list(topics.GATES), help="gates that ignore commands")
    ap.add_argument("--no-keyboard", action="store_true", help="do not read commands from stdin")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    conn = MqttConnection(DEVICE_ID, MqttSettings.from_env(), device_id=DEVICE_ID, device_type="GATE_CONTROLLER")
    sim = GateSimulator(conn, no_ack=args.no_ack)
    conn.subscribe(topics.GATE_COMMAND_ALL, sim.on_command)
    conn.subscribe(topics.SIM_GATE_PRESENCE_ALL, sim.on_presence)
    conn.start()
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
            with sim.lock:
                if cmd in ("e", "x"):
                    g = sim.gates["entrance" if cmd == "e" else "exit"]
                    g.set_vehicle(not g.vehicle_present)
                elif cmd in ("be", "bx"):
                    sim.gates["entrance" if cmd == "be" else "exit"].button()
                elif cmd == "s":
                    print({n: g.snapshot() for n, g in sim.gates.items()})
                elif cmd == "q":
                    break
                sim.publish_events()
    stop.set()
    conn.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
