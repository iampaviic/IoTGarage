"""Sensor node simulator for varijanta B: publishes to ThingsBoard exactly what the sensor ESP32 publishes.

    python spot_simulator_tb.py                       # 6 spots, all free, keyboard control
    python spot_simulator_tb.py --random 20           # random car arrives/leaves every ~20 s (dashboard demo)
    TB_HOST=192.168.1.20 TB_MQTT_PORT=1883 TB_TOKEN_SPOTS=... python spot_simulator_tb.py

Keyboard (type + ENTER):
    3        toggle P03 free/occupied
    3x       P03 sensor broken (state UNKNOWN, sensorStatus TIMEOUT)
    a        all free          f   all occupied
    s        print states      k   cut the connection (like a power cut)      q   quit

ThingsBoard sees the gateway device "esp32-spots" and its devices ParkingSpot-01..06:
    v1/gateway/connect       one per spot after every (re)connect
    v1/gateway/telemetry     {"ParkingSpot-03": [{"ts": ..., "values": {state, stateCode, occupied, distanceCm,
                             sensorStatus}}]}  on change, every 30 s and after every reconnect
    v1/devices/me/telemetry  {freeSpots, occupiedSpots, unknownSpots, totalSpots} + heartbeat (uptimeS, rssi, ...)
    RPC to esp32-spots       sim {"spot": "P03", "occupied": true|false|null}, simOff
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import threading
import time
from typing import Dict, Optional

from garage_contract.tb import SPOT_STATE_CODE, SPOTS_GATEWAY, TbGateway, TbSettings, spot_device

FREE_CM, OCCUPIED_CM = 14.0, 6.5   # distance sensor -> floor / -> car roof on the model
FW_VERSION = "sim-b"


class SpotNodeSim:
    def __init__(self, spots, settings: TbSettings, periodic_s: float = 30.0, verbose: bool = True) -> None:
        self.state: Dict[str, Optional[bool]] = {s: False for s in spots}  # None = broken sensor
        self.periodic_s = periodic_s
        self.verbose = verbose
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.gw = TbGateway(SPOTS_GATEWAY, settings, {spot_device(s): "ParkingSpot" for s in spots})
        self.gw.on_connect = self.publish_all
        self.gw.on_rpc = self.on_rpc

    # ------------------------------------------------------------- messages
    def spot_values(self, spot: str) -> dict:
        occ = self.state[spot]
        if occ is None:
            return {"state": "UNKNOWN", "stateCode": -1, "sensorStatus": "TIMEOUT"}
        state = "OCCUPIED" if occ else "FREE"
        dist = (OCCUPIED_CM if occ else FREE_CM) + random.uniform(-0.3, 0.3)
        return {"state": state, "stateCode": SPOT_STATE_CODE[state], "occupied": occ,
                "distanceCm": round(dist, 1), "sensorStatus": "SIMULATED"}

    def counts(self) -> dict:
        free = sum(1 for v in self.state.values() if v is False)
        occupied = sum(1 for v in self.state.values() if v is True)
        return {"freeSpots": free, "occupiedSpots": occupied, "unknownSpots": len(self.state) - free - occupied,
                "totalSpots": len(self.state)}

    def heartbeat(self) -> dict:
        return {"uptimeS": int(time.monotonic() - self.started), "rssi": -55, "freeHeap": 200000,
                "fwVersion": FW_VERSION}

    def publish_spot(self, spot: str) -> None:
        values = self.spot_values(spot)
        self.gw.device_telemetry(spot_device(spot), values)
        if self.verbose:
            print("%s %-8s %s cm" % (spot, values["state"], values.get("distanceCm")))

    def publish_all(self) -> None:
        with self.lock:
            self.gw.attributes({"fwVersion": FW_VERSION, "deviceType": "SPOT_SENSORS", "spotCount": len(self.state)})
            for s in self.state:
                self.publish_spot(s)
            self.gw.telemetry(dict(self.counts(), **self.heartbeat()))

    # ------------------------------------------------------------- inputs
    def set(self, spot: str, occupied: Optional[bool]) -> None:
        with self.lock:
            if spot not in self.state:
                print("unknown spot", spot)
                return
            if self.state[spot] == occupied and occupied is not None:
                return
            self.state[spot] = occupied
            self.publish_spot(spot)
            self.gw.telemetry(self.counts())

    def on_rpc(self, method: str, params: dict) -> Optional[dict]:
        if method == "sim":
            self.set(str(params.get("spot", "")), params.get("occupied"))
            return {"success": True}
        if method == "simOff":
            return {"success": True}
        return None

    def periodic(self, stop: threading.Event, random_every: float = 0.0) -> None:
        next_random = time.monotonic() + random_every
        last = time.monotonic()
        while not stop.wait(0.5):
            if time.monotonic() - last >= self.periodic_s:
                last = time.monotonic()
                if self.gw.connected.is_set():
                    self.publish_all()
            if random_every and time.monotonic() >= next_random:
                next_random = time.monotonic() + random.uniform(0.5, 1.5) * random_every
                spot = random.choice(list(self.state))
                self.set(spot, not bool(self.state[spot]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spots", type=int, default=6)
    ap.add_argument("--random", type=float, default=0.0, metavar="SECONDS", help="random changes every ~N s")
    ap.add_argument("--no-keyboard", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    spots = ["P%02d" % i for i in range(1, args.spots + 1)]
    sim = SpotNodeSim(spots, TbSettings.from_env("TB_TOKEN_SPOTS", "esp32-spots-token"))
    if not sim.gw.start():
        print("ThingsBoard %s:%s not reachable yet - retrying" % (sim.gw.settings.host, sim.gw.settings.port))
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
                print(sim.state, sim.counts())
            elif cmd == "k":
                sim.gw.kill()
                print("connection cut; restart the simulator to reconnect")
            elif cmd.rstrip("x").isdigit():
                spot = "P%02d" % int(cmd.rstrip("x"))
                sim.set(spot, None if cmd.endswith("x") else not bool(sim.state.get(spot)))
    stop.set()
    sim.gw.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
