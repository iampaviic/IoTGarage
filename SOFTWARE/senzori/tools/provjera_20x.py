"""Acceptance test of the spot sensors: 20x place and remove the car on every spot.

    python provjera_20x.py --port COM5 --spot P03 --cycles 20              # Linux: --port /dev/ttyUSB0
    python provjera_20x.py --port COM5 --all --cycles 20 --out ../testni-zapis-P0x.md

Reads the state changes the sensor ESP32 prints on its serial port ("P03 -> OCCUPIED (6.4 cm, OK)",
the same changes it sends to ThingsBoard) and guides you:
"put the car on P03" -> waits for OCCUPIED -> "remove it" -> waits for FREE ...
It counts every state change, so flicker (extra changes) or a missed change is
caught. Criterion (project plan): 20 correct cycles per spot, no flicker.
Writes a Markdown test record for the test log (PROJEKT/testiranje/testni-zapisnik.md).
Without --port it listens to garage/parking/spot/+/telemetry on Mosquitto (varijanta A).
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
import time

from garage_contract import GarageConfig, MqttSettings, topics
from garage_contract.mqtt import MqttConnection


class Recorder:
    def __init__(self) -> None:
        self.cond = threading.Condition()
        self.state = {}
        self.changes = {}
        self.log = []

    def on_msg(self, topic, msg) -> None:
        spot = msg.get("spotId") or topics.segment(topic, 3)
        new = msg.get("state")
        with self.cond:
            if self.state.get(spot) is not None and self.state[spot] != new:
                self.changes[spot] = self.changes.get(spot, 0) + 1
                self.log.append((time.time(), spot, self.state[spot], new, msg.get("distanceCm")))
            self.state[spot] = new
            self.cond.notify_all()

    def wait_state(self, spot: str, want: str, timeout: float) -> float:
        t0 = time.time()
        with self.cond:
            while self.state.get(spot) != want:
                left = timeout - (time.time() - t0)
                if left <= 0:
                    return -1.0
                self.cond.wait(left)
        return time.time() - t0


CHANGE_RE = re.compile(r"^(P\d\d) -> (FREE|OCCUPIED|UNKNOWN) \((-?[\d.]+) cm")
STATUS_RE = re.compile(r"^(P\d\d) (FREE|OCCUPIED|UNKNOWN)\s+filtered=(-?[\d.]+)")


def read_serial(port: str, rec: Recorder, stop: threading.Event) -> None:
    """Feed the recorder from the firmware's serial output (varijanta B: no broker needed)."""
    import serial  # pyserial

    with serial.Serial(port, 115200, timeout=0.5) as ser:
        time.sleep(2.0)                 # opening the port may reset the ESP32
        ser.write(b"status\n")          # current state of every spot
        while not stop.is_set():
            line = ser.readline().decode("utf-8", "replace").strip()
            m = CHANGE_RE.match(line) or STATUS_RE.match(line)
            if m:
                rec.on_msg("", {"spotId": m.group(1), "state": m.group(2), "distanceCm": float(m.group(3))})


def test_spot(rec: Recorder, spot: str, cycles: int, timeout: float, settle: float):
    results = []
    if rec.state.get(spot) != "FREE":
        print("  %s is %s - make it FREE first" % (spot, rec.state.get(spot)))
        rec.wait_state(spot, "FREE", 120)
    start_changes = rec.changes.get(spot, 0)
    for i in range(1, cycles + 1):
        print("  [%2d/%d] put the car on %s" % (i, cycles, spot), end="", flush=True)
        t_on = rec.wait_state(spot, "OCCUPIED", timeout)
        print(" -> %s" % ("OCCUPIED after %.1f s" % t_on if t_on >= 0 else "TIMEOUT"))
        time.sleep(settle)
        print("         remove the car", end="", flush=True)
        t_off = rec.wait_state(spot, "FREE", timeout)
        print(" -> %s" % ("FREE after %.1f s" % t_off if t_off >= 0 else "TIMEOUT"))
        time.sleep(settle)
        results.append((i, t_on, t_off))
    changes = rec.changes.get(spot, 0) - start_changes
    return results, changes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--spot")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--cycles", type=int, default=20)
    ap.add_argument("--timeout", type=float, default=15.0, help="max seconds for a state change")
    ap.add_argument("--settle", type=float, default=2.0, help="wait after each change (flicker shows up here)")
    ap.add_argument("--out", help="Markdown test record")
    ap.add_argument("--port", help="serial port of the sensor ESP32 (COM5, /dev/ttyUSB0); without it: MQTT (A)")
    args = ap.parse_args(argv)

    rec = Recorder()
    stop = threading.Event()
    conn = None
    if args.port:
        threading.Thread(target=read_serial, args=(args.port, rec, stop), daemon=True).start()
        time.sleep(3.0)
    else:
        conn = MqttConnection("provjera-20x-%d" % int(time.time()), MqttSettings.from_env())
        conn.subscribe(topics.SPOT_TELEMETRY_ALL, rec.on_msg)
        if not conn.start():
            print("MQTT broker not reachable", file=sys.stderr)
            return 2
        time.sleep(1.0)
    spots = GarageConfig.from_env().spots if args.all else [args.spot.upper()]
    lines = ["# Testni zapis senzora - %s" % time.strftime("%Y-%m-%d %H:%M"), "",
             "| mjesto | ciklusa | točno | promjena stanja (očekivano) | prosj. vrijeme detekcije | rezultat |",
             "|---|---|---|---|---|---|"]
    all_ok = True
    for spot in spots:
        print("\n=== %s" % spot)
        results, changes = test_spot(rec, spot, args.cycles, args.timeout, args.settle)
        good = sum(1 for _, a, b in results if a >= 0 and b >= 0)
        times = [t for _, a, b in results for t in (a, b) if t >= 0]
        ok = good == args.cycles and changes == 2 * args.cycles
        all_ok &= ok
        lines.append("| %s | %d | %d | %d (%d) | %.1f s | %s |" % (
            spot, args.cycles, good, changes, 2 * args.cycles, sum(times) / len(times) if times else 0,
            "PROLAZ" if ok else "PAD"))
        print("=== %s: %d/%d cycles, %d state changes (expected %d) -> %s" % (
            spot, good, args.cycles, changes, 2 * args.cycles, "PASS" if ok else "FAIL"))
    lines += ["", "Kriterij: svako mjesto %d puta ispravno, bez treperenja (broj promjena = 2 x ciklusa)." % args.cycles]
    stop.set()
    if conn:
        conn.stop()
    text = "\n".join(lines) + "\n"
    print("\n" + text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
