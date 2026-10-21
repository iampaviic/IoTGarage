"""Parking spot simulator: publishes exactly what the sensor ESP32 publishes.

    python spot_simulator.py                  # 6 spots, all free, keyboard control
    python spot_simulator.py --spots 4
    python spot_simulator.py --random 20      # random car arrives/leaves every ~20 s (dashboard demo)

Keyboard (type + ENTER):
    3        toggle P03 free/occupied
    3x       P03 sensor broken (state UNKNOWN, sensorStatus TIMEOUT)
    a        all free          f   all occupied
    s        print states      q   quit
Other tools can set a spot with garage/sim/spot/<P03> {"occupied": true|false|null}.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import threading
import time
from typing import Dict, Optional

from garage_contract import GarageConfig, MqttSettings, topics
from garage_contract.mqtt import MqttConnection
from garage_contract.timeutil import utc_now_iso

DEVICE_ID = "sim-spots"
FREE_CM, OCCUPIED_CM = 14.0, 6.5   # distance sensor -> floor / -> car roof on the model


class SpotSimulator:
    def __init__(self, conn: MqttConnection, spots, periodic_s: float = 30.0) -> None:
        self.conn = conn
        self.state: Dict[str, Optional[bool]] = {s: False for s in spots}  # None = broken sensor
        self.periodic_s = periodic_s
        self.lock = threading.Lock()
        self.started = time.monotonic()

    def payload(self, spot: str) -> dict:
        occ = self.state[spot]
        if occ is None:
            return {"spotId": spot, "state": "UNKNOWN", "occupied": None, "distanceCm": None,
                    "sensorStatus": "TIMEOUT", "deviceId": DEVICE_ID,
                    "uptimeMs": int((time.monotonic() - self.started) * 1000), "timestamp": utc_now_iso()}
        dist = (OCCUPIED_CM if occ else FREE_CM) + random.uniform(-0.3, 0.3)
        return {"spotId": spot, "state": "OCCUPIED" if occ else "FREE", "occupied": occ,
                "distanceCm": round(dist, 1), "sensorStatus": "SIMULATED", "deviceId": DEVICE_ID,
                "uptimeMs": int((time.monotonic() - self.started) * 1000), "timestamp": utc_now_iso()}

    def publish(self, spot: str) -> None:
        p = self.payload(spot)
        self.conn.publish_json(topics.spot_telemetry(spot), p, retain=True)
        print("%s %-8s %s cm" % (spot, p["state"], p["distanceCm"]))

    def set(self, spot: str, occupied: Optional[bool]) -> None:
        with self.lock:
            if spot not in self.state:
                print("unknown spot", spot)
                return
            if self.state[spot] != occupied:
                self.state[spot] = occupied
                self.publish(spot)

    def on_sim(self, topic: str, msg) -> None:
        self.set(topics.segment(topic, 3), (msg or {}).get("occupied"))

    def periodic(self, stop: threading.Event, random_every: float = 0.0) -> None:
        next_random = time.monotonic() + random_every
        with self.lock:
            for s in self.state:
                self.publish(s)
        last = time.monotonic()
        while not stop.wait(0.5):
            if time.monotonic() - last >= self.periodic_s:
                last = time.monotonic()
                with self.lock:
                    for s in self.state:
                        self.publish(s)
            if random_every and time.monotonic() >= next_random:
                next_random = time.monotonic() + random.uniform(0.5, 1.5) * random_every
                spot = random.choice(list(self.state))
                self.set(spot, not bool(self.state[spot]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spots", type=int, default=GarageConfig.from_env().spot_count)
    ap.add_argument("--random", type=float, default=0.0, metavar="SECONDS", help="random changes every ~N s")
    ap.add_argument("--no-keyboard", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    spots = GarageConfig(spot_count=args.spots).spots
    conn = MqttConnection(DEVICE_ID, MqttSettings.from_env(), device_id=DEVICE_ID, device_type="SPOT_SENSORS")
    sim = SpotSimulator(conn, spots)
    conn.subscribe(topics.SIM_SPOT_ALL, sim.on_sim)
    conn.start()
    stop = threading.Event()
    threading.Thread(target=sim.periodic, args=(stop, args.random), daemon=True).start()
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
            if cmd == "q":
                break
            if cmd == "a":
                for s in spots:
                    sim.set(s, False)
            elif cmd == "f":
                for s in spots:
                    sim.set(s, True)
            elif cmd == "s":
                print(sim.state)
            elif cmd.rstrip("x").isdigit():
                spot = "P%02d" % int(cmd.rstrip("x"))
                if cmd.endswith("x"):
                    sim.set(spot, None)
                else:
                    sim.set(spot, not bool(sim.state.get(spot)))
    stop.set()
    conn.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
