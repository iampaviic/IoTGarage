"""Run the WHOLE system on one laptop without any hardware.

    python simulacija.py                 # start everything and play the demo scenario
    python simulacija.py --interactive   # start everything, you drive (see printed hints)
    python simulacija.py --broker        # also start a local mosquitto (if installed)
    python simulacija.py --tb            # also start the ThingsBoard bridge (osoba 7)

Started processes:
    spot simulator (osoba 3), gate simulator (osoba 4),
    edge service: ALPR with a simulated camera (osoba 5+6) + access control (osoba 6)
    with the session database of osoba 8 in a temporary folder.
Needs an MQTT broker on $MQTT_HOST:$MQTT_PORT (default localhost:1883), e.g.
    docker run -d -p 1883:1883 eclipse-mosquitto:2 mosquitto -c /mosquitto-no-auth.conf
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)


def port_open(host: str, port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


class System:
    """Starts and stops the simulated system as child processes."""

    def __init__(self, host: str = "localhost", port: int = 1883, spots: int = 6, workdir: str = "",
                 start_broker: bool = False, with_tb: bool = False, quiet: bool = True) -> None:
        self.host, self.port, self.spots = host, port, spots
        self.workdir = workdir or tempfile.mkdtemp(prefix="garage-sim-")
        self.start_broker = start_broker
        self.with_tb = with_tb
        self.quiet = quiet
        self.procs = []

    def env(self) -> dict:
        e = dict(os.environ)
        e.update(MQTT_HOST=self.host, MQTT_PORT=str(self.port), GARAGE_SPOTS=str(self.spots),
                 GARAGE_DB=os.path.join(self.workdir, "garage.db"), PRICING_PROFILE="demo",
                 ALPR_SOURCE="sim", PYTHONUNBUFFERED="1")
        return e

    def _spawn(self, name: str, args) -> None:
        log = open(os.path.join(self.workdir, name + ".log"), "w")
        p = subprocess.Popen(args, env=self.env(), stdout=log if self.quiet else None, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, cwd=self.workdir)
        self.procs.append((name, p, log))

    def start(self) -> "System":
        if self.start_broker and not port_open(self.host, self.port):
            exe = shutil.which("mosquitto")
            if not exe:
                raise SystemExit("mosquitto not installed; start a broker yourself (see docstring)")
            self._spawn("mosquitto", [exe, "-p", str(self.port)])
            for _ in range(50):
                if port_open(self.host, self.port):
                    break
                time.sleep(0.1)
        if not port_open(self.host, self.port):
            raise SystemExit("no MQTT broker on %s:%d (use --broker or start mosquitto)" % (self.host, self.port))
        py = sys.executable
        self._spawn("spots", [py, os.path.join(ROOT, "osoba-3-senzori", "simulator", "spot_simulator.py"),
                              "--no-keyboard", "--spots", str(self.spots)])
        self._spawn("gates", [py, os.path.join(ROOT, "osoba-4-rampe", "simulator", "gate_simulator.py"),
                              "--no-keyboard"])
        self._spawn("edge", [py, "-m", "edge_service", "all"])
        if self.with_tb:
            self._spawn("tb-bridge", [py, "-m", "tb_bridge"])
        time.sleep(3.0)  # let services connect and publish retained states
        for name, p, _ in self.procs:
            if p.poll() is not None:
                raise SystemExit("%s exited early, see %s" % (name, os.path.join(self.workdir, name + ".log")))
        return self

    def stop(self) -> None:
        for name, p, log in reversed(self.procs):
            p.terminate()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
            log.close()


def demo(drv) -> None:
    from garage_contract import topics

    print("\n=== 1. vozilo ZG1234AB ulazi i parkira na P03")
    d = drv.drive_in("ZG1234AB", spot="P03")
    print("    odluka: %s (%s), confidence %s" % (d["decision"], d["reason"], d["confidence"]))
    print("\n=== 2. drugo vozilo ST555B, ulazi i parkira na P05")
    drv.drive_in("ST555B", spot="P05")
    print("\n=== 3. nečitljiva pločica -> ručno odobrenje operatera")
    d = drv.arrive("entrance", "RI0913T", quality="unreadable")
    print("    odluka: %s (%s)" % (d["decision"], d["reason"]))
    since = drv.mark()
    drv.manual("APPROVE_ENTRY", "entrance", "RI0913T", note="pločica prljava, provjereno vizualno")
    d = drv.wait_for(topics.ACCESS_DECISION, lambda p: p["manual"], since=since)
    print("    ručno: %s (%s)" % (d["decision"], d["reason"]))
    drv.pass_gate("entrance")
    drv.spot("P01", True)
    print("\n=== 4. pokušaj izlaska vozila bez sesije")
    d = drv.arrive("exit", "KA4321ZZ")
    print("    odluka: %s (%s)" % (d["decision"], d["reason"]))
    drv.presence("exit", False)
    drv.vehicle_at("exit", None)
    time.sleep(1)
    print("\n=== 5. ZG1234AB izlazi (demo naplata: 1 min = 1 h)")
    time.sleep(2)
    closed = drv.drive_out("ZG1234AB", spot="P03")
    print("    trajanje %s s, cijena %.2f %s" % (closed["durationS"], closed["price"], closed["currency"]))
    print("\n=== gotovo; poruke koje krše ugovor: %d" % len(drv.contract_errors))
    for e in drv.contract_errors:
        print("   ", e)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--broker", action="store_true", help="start a local mosquitto if none is running")
    ap.add_argument("--tb", action="store_true", help="also run the ThingsBoard bridge")
    ap.add_argument("--spots", type=int, default=6)
    ap.add_argument("--host", default=os.environ.get("MQTT_HOST", "localhost"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    args = ap.parse_args(argv)

    from garage_contract import MqttSettings
    from scenarij import Driver

    system = System(args.host, args.port, args.spots, start_broker=args.broker, with_tb=args.tb).start()
    print("system running, logs and database in", system.workdir)
    drv = Driver(MqttSettings(host=args.host, port=args.port)).start()
    try:
        if args.interactive:
            print(__doc__)
            print("Upravljanje (u drugom terminalu):\n"
                  "  python -m garage_contract.monitor\n"
                  "  python -m garage_contract.monitor --pub garage/sim/vehicle/entrance '{\"plate\":\"ZG1234AB\"}' --retain\n"
                  "  python -m garage_contract.monitor --pub garage/sim/gate/entrance/presence '{\"present\":true}'\n"
                  "  python -m garage_contract.monitor --pub garage/sim/spot/P03 '{\"occupied\":true}'\n"
                  "Ctrl+C za kraj.")
            while True:
                time.sleep(1)
        else:
            demo(drv)
            print("\nbaza: parking-sessions --db %s list" % os.path.join(system.workdir, "garage.db"))
    except KeyboardInterrupt:
        pass
    finally:
        drv.stop()
        system.stop()
    return 0 if not drv.contract_errors else 1


if __name__ == "__main__":
    sys.exit(main())
