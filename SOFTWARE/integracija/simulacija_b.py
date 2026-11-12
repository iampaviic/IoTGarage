"""Varijanta B: the whole system against a running ThingsBoard, without hardware.

    python integracija/simulacija_b.py                  # play the demo scenario and check every step
    python integracija/simulacija_b.py --interactive    # only run the simulated devices (use the dashboard)
    python integracija/simulacija_b.py --alpr sim       # real ALPR + OCR on synthetic frames (needs Tesseract)

Needs ThingsBoard prepared by provision.py (devices, tokens, rule chain), see SOFTWARE/thingsboard:
    TB_URL       REST API          default http://localhost:8080
    TB_HOST      MQTT host         default localhost
    TB_MQTT_PORT MQTT port         default 1883
    TB_USER / TB_PASSWORD          default tenant@thingsboard.org / tenant
    TB_TOKEN_SPOTS, TB_TOKEN_GATES, TB_TOKEN_ALPR   access tokens (defaults of provision.py)

In-process devices: sensor node (esp32-spots), gate node (esp32-gates) and the ALPR device
(alpr-service). With --alpr fake (default) the "camera" reads exactly the plate and confidence
the scenario puts in front of it, so every decision branch of the rule chain can be checked.
WARNING: the scenario clears the parking sessions of the Garage asset - not on the demo instance!
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SOFTWARE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(SOFTWARE, "senzori", "simulator"))
sys.path.insert(0, os.path.join(SOFTWARE, "rampe", "simulator"))

from gate_simulator_tb import GateNodeSim  # noqa: E402
from spot_simulator_tb import SpotNodeSim  # noqa: E402

from garage_contract.tb import ALPR_DEVICES, ALPR_GATEWAY, GATE_DEVICES, TbGateway, TbSettings  # noqa: E402


# ------------------------------------------------------------------ ThingsBoard REST
class TbRest:
    def __init__(self, url: str, user: str, password: str) -> None:
        self.url = url.rstrip("/")
        r = requests.post(self.url + "/api/auth/login", json={"username": user, "password": password}, timeout=10)
        r.raise_for_status()
        self.h = {"X-Authorization": "Bearer " + r.json()["token"]}
        self._ids: Dict[str, Dict[str, str]] = {}

    def get(self, path: str, **params) -> Any:
        r = requests.get(self.url + path, headers=self.h, params=params, timeout=10)
        r.raise_for_status()
        return r.json() if r.text else None

    def post(self, path: str, body: Any, timeout: float = 10, **params) -> requests.Response:
        return requests.post(self.url + path, headers=self.h, json=body, params=params, timeout=timeout)

    def entity(self, name: str, kind: str = "DEVICE") -> Dict[str, str]:
        if name not in self._ids:
            path = "/api/tenant/devices" if kind == "DEVICE" else "/api/tenant/assets"
            found = self.get(path, **({"deviceName": name} if kind == "DEVICE" else {"assetName": name}))
            self._ids[name] = found["id"]
        return self._ids[name]

    def latest(self, name: str, keys: str, kind: str = "DEVICE") -> Dict[str, Tuple[int, Any]]:
        e = self.entity(name, kind)
        data = self.get("/api/plugins/telemetry/%s/%s/values/timeseries" % (e["entityType"], e["id"]), keys=keys,
                        useStrictDataTypes="true")
        return {k: (v[0]["ts"], v[0]["value"]) for k, v in (data or {}).items() if v and v[0].get("value") is not None}

    def attributes(self, name: str, kind: str = "ASSET") -> Dict[str, Any]:
        e = self.entity(name, kind)
        data = self.get("/api/plugins/telemetry/%s/%s/values/attributes/SERVER_SCOPE" % (e["entityType"], e["id"]))
        return {a["key"]: a["value"] for a in data or []}

    def set_attributes(self, name: str, values: Dict[str, Any], kind: str = "ASSET") -> None:
        e = self.entity(name, kind)
        self.post("/api/plugins/telemetry/%s/%s/attributes/SERVER_SCOPE" % (e["entityType"], e["id"]),
                  values).raise_for_status()

    def active_alarms(self, name: str, kind: str = "DEVICE") -> List[str]:
        e = self.entity(name, kind)
        page = self.get("/api/alarm/%s/%s" % (e["entityType"], e["id"]), searchStatus="ACTIVE", pageSize=50, page=0)
        return [a["type"] for a in page["data"]]

    def rpc(self, device: str, method: str, params: Dict[str, Any], timeout_ms: int = 10000) -> requests.Response:
        e = self.entity(device)
        return self.post("/api/plugins/rpc/twoway/%s" % e["id"], {"method": method, "params": params,
                                                                 "timeout": timeout_ms}, timeout=timeout_ms / 1000 + 5)


# ------------------------------------------------------------------ ALPR stand-in
class FakeAlpr:
    """alpr-service that 'reads' the plate the scenario put in front of the camera."""

    def __init__(self, settings: TbSettings) -> None:
        self.front: Dict[str, Tuple[Optional[str], float]] = {"ENTRANCE": (None, 0.0), "EXIT": (None, 0.0)}
        self.gw = TbGateway(ALPR_GATEWAY, settings, {d: "ALPR" for d in ALPR_DEVICES.values()})
        self.gw.on_device_rpc = self.on_device_rpc

    def put(self, gate: str, plate: Optional[str], confidence: float) -> None:
        self.front[gate] = (plate, confidence)

    def on_device_rpc(self, device: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gate = {v: k for k, v in ALPR_DEVICES.items()}.get(device)
        if method != "readPlate" or gate is None:
            return None
        plate, conf = self.front[gate]
        status = "NO_PLATE" if not plate else ("OK" if conf >= 0.85 else "LOW_CONFIDENCE")
        self.gw.device_telemetry(device, {"plate": plate or "-", "status": status, "ocrConfidence": conf,
                                          "accepted": status == "OK", "alprFailing": False})
        return {"status": status, "plate": plate, "ocrConfidence": conf, "accepted": status == "OK", "gate": gate}


class SimAlpr:
    """The real ALPR service (detection + OCR) on synthetic frames of the plate in front of the camera."""

    def __init__(self, settings: TbSettings) -> None:
        from edge_service.config import EdgeConfig
        from edge_service.tb_alpr import TbAlprService, make_source

        cfg = EdgeConfig()
        cfg.alpr.source = "sim"
        cfg.thingsboard.host, cfg.thingsboard.port, cfg.thingsboard.token = settings.host, settings.port, settings.token
        self.svc = TbAlprService(cfg, make_source(cfg))
        self.gw = self.svc.gw

    def put(self, gate: str, plate: Optional[str], confidence: float) -> None:
        quality = "good" if confidence >= 0.85 else "unreadable"
        self.svc.on_rpc("simVehicle", {"gate": gate, "plate": plate, "quality": quality})


# ------------------------------------------------------------------ the system
class SystemB:
    def __init__(self, alpr: str = "fake", spots: int = 6, verbose: bool = True) -> None:
        self.tb = TbRest(os.environ.get("TB_URL", "http://localhost:8080"),
                         os.environ.get("TB_USER", "tenant@thingsboard.org"), os.environ.get("TB_PASSWORD", "tenant"))
        self.verbose = verbose
        self.spot_ids = ["P%02d" % i for i in range(1, spots + 1)]
        self.spots = SpotNodeSim(self.spot_ids, TbSettings.from_env("TB_TOKEN_SPOTS", "esp32-spots-token"),
                                 verbose=False)
        self.gates = GateNodeSim(TbSettings.from_env("TB_TOKEN_GATES", "esp32-gates-token"), verbose=False)
        alpr_settings = TbSettings.from_env("TB_TOKEN_ALPR", "alpr-service-token")
        self.alpr = SimAlpr(alpr_settings) if alpr == "sim" else FakeAlpr(alpr_settings)
        self._stop = threading.Event()

    def start(self) -> "SystemB":
        for gw in (self.spots.gw, self.gates.gw, self.alpr.gw):
            if not gw.start():
                raise RuntimeError("%s cannot connect to ThingsBoard %s:%s (token?)" % (
                    gw.name, gw.settings.host, gw.settings.port))
        threading.Thread(target=self.gates.loop_forever, args=(self._stop,), daemon=True).start()
        threading.Thread(target=self.spots.periodic, args=(self._stop,), daemon=True).start()
        return self

    def stop(self) -> None:
        self._stop.set()
        for gw in (self.spots.gw, self.gates.gw, self.alpr.gw):
            gw.stop()

    def say(self, text: str) -> None:
        if self.verbose:
            print(text, flush=True)

    # ------------------------------------------------------------- waiting for ThingsBoard
    def wait(self, what: str, check: Callable[[], Any], timeout: float = 15.0) -> Any:
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = check()
            except requests.RequestException as e:   # ThingsBoard busy for a moment
                last = e
            if last:
                return last
            time.sleep(0.3)
        raise AssertionError("timeout waiting for: %s (last: %r)" % (what, last))

    def decision_after(self, t0_ms: int, timeout: float = 25.0) -> Dict[str, Any]:
        keys = "decision,decisionReason,decisionPlate,decisionDirection,decisionManual,sessionEvent,price,durationS"

        def check():
            d = self.tb.latest("Garage", keys, "ASSET")
            if d.get("decision", (0, None))[0] >= t0_ms:
                return {k: v for k, (ts, v) in d.items() if ts >= t0_ms}
            return None
        return self.wait("decision", check, timeout)

    def gate_state(self, gate: str) -> str:
        return self.tb.latest(GATE_DEVICES[gate], "state").get("state", (0, ""))[1]

    # ------------------------------------------------------------- actions
    def vehicle_arrives(self, gate: str, plate: Optional[str], confidence: float) -> Dict[str, Any]:
        """Vehicle drives up to a closed gate; returns the decision of the rule chain."""
        self.wait(gate + " closed", lambda: self.gates.gates[gate].state == "CLOSED", 20)
        self.alpr.put(gate, plate, confidence)
        t0 = int(time.time() * 1000) - 50
        self.gates.set_vehicle(gate, True)
        return self.decision_after(t0)

    def vehicle_passes(self, gate: str) -> None:
        """The vehicle drives through once the barrier is up (or backs away if it stays closed)."""
        if self.gates.gates[gate].state in ("OPENING", "OPEN"):
            self.wait(gate + " open", lambda: self.gates.gates[gate].state == "OPEN", 5)
        self.gates.set_vehicle(gate, False)

    def operator(self, gate: str, method: str, plate: Optional[str] = None) -> Dict[str, Any]:
        t0 = int(time.time() * 1000) - 50
        r = self.tb.rpc(GATE_DEVICES[gate], method, {"plate": plate} if plate else {})
        if r.status_code != 200:
            raise AssertionError("RPC %s -> %s %s" % (method, r.status_code, r.text[:200]))
        return self.decision_after(t0)

    def reset(self) -> None:
        """Empty garage: no sessions, all spots free."""
        self.tb.set_attributes("Garage", {"sessions": {}, "manualPlate": "", "timeMultiplier": 60})
        for s in self.spot_ids:
            self.spots.set(s, False)
        self.spots.publish_all()
        self.wait("all spots free", lambda: self.tb.attributes("Garage").get("sensorFree") == len(self.spot_ids))


# ------------------------------------------------------------------ scenario
def scenario(s: SystemB) -> None:
    """Demo scenario of PREZENTACIJA/demo-scenarij.md, every step checked in ThingsBoard."""
    def check(cond: bool, text: str) -> None:
        if not cond:
            raise AssertionError(text)
        s.say("   ok: " + text)

    s.say("0. prazna garaža")
    s.reset()

    s.say("1. ZG1234AB na ulazu, dobro čitanje (0,93)")
    d = s.vehicle_arrives("ENTRANCE", "ZG1234AB", 0.93)
    check(d.get("decision") == "GRANTED" and d.get("sessionEvent") == "SESSION_OPENED", "GRANTED, sesija otvorena")
    s.wait("ulazna rampa otvorena", lambda: s.gate_state("ENTRANCE") == "OPEN")
    check("ZG1234AB" in s.tb.attributes("Garage")["sessions"], "sesija u atributu sessions")
    s.vehicle_passes("ENTRANCE")
    s.wait("ulazna rampa zatvorena", lambda: s.gate_state("ENTRANCE") == "CLOSED", 10)
    check(True, "rampa se sama zatvorila")

    s.say("2. vozilo parkira na P03")
    s.spots.set("P03", True)
    s.wait("P03 zauzeto", lambda: s.tb.latest("ParkingSpot-03", "state")["state"][1] == "OCCUPIED")
    s.wait("sažetak", lambda: s.tb.latest("Garage", "freeSpots", "ASSET")["freeSpots"][1] == len(s.spot_ids) - 1)
    check(True, "P03 zauzeto, freeSpots = %d" % (len(s.spot_ids) - 1))

    s.say("3. prljava pločica na ulazu (0,40) -> operater")
    d = s.vehicle_arrives("ENTRANCE", "ST555CD", 0.40)
    check(d.get("decision") == "MANUAL_REQUIRED", "MANUAL_REQUIRED (%s)" % d.get("decisionReason"))
    check(s.gate_state("ENTRANCE") == "CLOSED", "rampa se nije otvorila")
    s.wait("alarm ručne intervencije", lambda: "Potrebna ručna intervencija" in s.tb.active_alarms("Garage", "ASSET"))
    check(True, "alarm „Potrebna ručna intervencija“")
    d = s.operator("ENTRANCE", "approve", "ST 555-CD")
    check(d.get("decision") == "GRANTED" and d.get("decisionReason") == "MANUAL_APPROVAL"
          and d.get("decisionManual") is True, "operater odobrio: GRANTED MANUAL_APPROVAL")
    s.wait("alarm ugašen", lambda: "Potrebna ručna intervencija" not in s.tb.active_alarms("Garage", "ASSET"))
    check("ST555CD" in s.tb.attributes("Garage")["sessions"], "sesija ST555CD otvorena")
    s.vehicle_passes("ENTRANCE")

    s.say("4. ZG1234AB ponovno na ulazu -> već je unutra")
    d = s.vehicle_arrives("ENTRANCE", "ZG1234AB", 0.95)
    check(d.get("decision") == "DENIED" and d.get("decisionReason") == "ALREADY_INSIDE", "DENIED ALREADY_INSIDE")
    s.vehicle_passes("ENTRANCE")

    s.say("5. ZG1234AB na izlazu -> trajanje i cijena")
    s.spots.set("P03", False)
    d = s.vehicle_arrives("EXIT", "ZG1234AB", 0.92)
    check(d.get("decision") == "GRANTED" and d.get("sessionEvent") == "SESSION_CLOSED", "GRANTED, sesija zatvorena")
    check("price" in d and "durationS" in d, "trajanje %ss, cijena %s EUR" % (d.get("durationS"), d.get("price")))
    s.wait("izlazna rampa otvorena", lambda: s.gate_state("EXIT") == "OPEN")
    s.vehicle_passes("EXIT")

    s.say("6. nepoznato vozilo na izlazu")
    d = s.vehicle_arrives("EXIT", "RI999XX", 0.95)
    # with real OCR (--alpr sim) a misread with low confidence goes to the operator instead - also safe
    check((d.get("decision"), d.get("decisionReason")) in (("DENIED", "NO_ACTIVE_SESSION"), ("MANUAL_REQUIRED",
          "LOW_CONFIDENCE")) and s.gate_state("EXIT") == "CLOSED", "%s %s, rampa zatvorena" % (
          d.get("decision"), d.get("decisionReason")))
    d = s.operator("EXIT", "deny")
    check(d.get("decision") == "DENIED" and d.get("decisionReason") == "MANUAL_DENIAL", "operater odbio")
    s.vehicle_passes("EXIT")

    s.say("7. garaža puna")
    for spot in s.spot_ids:
        s.spots.set(spot, True)
    s.wait("alarm garaža puna", lambda: "Garaža puna" in s.tb.active_alarms("Garage", "ASSET"))
    d = s.vehicle_arrives("ENTRANCE", "OS111AA", 0.95)
    check(d.get("decision") == "DENIED" and d.get("decisionReason") == "GARAGE_FULL", "DENIED GARAGE_FULL")
    s.vehicle_passes("ENTRANCE")
    for spot in s.spot_ids:
        s.spots.set(spot, False)
    s.wait("alarm ugašen", lambda: "Garaža puna" not in s.tb.active_alarms("Garage", "ASSET"))

    s.say("8. čvor senzora izgubi vezu (nestanak struje / Wi-Fi-ja)")
    s.spots.gw.kill()
    s.wait("mjesta OFFLINE", lambda: s.tb.latest("ParkingSpot-01", "sensorStatus")["sensorStatus"][1] == "OFFLINE", 90)
    check(s.tb.latest("ParkingSpot-01", "state")["state"][1] == "UNKNOWN", "mjesta UNKNOWN / OFFLINE")
    s.wait("alarm uređaja", lambda: "Uređaj nije dostupan" in s.tb.active_alarms("esp32-spots"))
    check(s.tb.attributes("Garage").get("sensorFree") == 0, "slobodnih 0 (nepoznato se ne broji)")
    s.spots.gw = TbGateway(s.spots.gw.name, s.spots.gw.settings, s.spots.gw.devices)
    s.spots.gw.on_connect, s.spots.gw.on_rpc = s.spots.publish_all, s.spots.on_rpc
    s.spots.gw.start()
    s.wait("mjesta ponovno javljena", lambda: s.tb.latest("ParkingSpot-01", "state")["state"][1] == "FREE")
    s.wait("alarm ugašen", lambda: "Uređaj nije dostupan" not in s.tb.active_alarms("esp32-spots"))
    check(True, "nakon ponovnog spajanja stanja su točna, alarm ugašen")
    s.say("scenarij prošao")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alpr", choices=["fake", "sim"], default="fake")
    ap.add_argument("--interactive", action="store_true", help="only run the devices; drive them from the dashboard")
    args = ap.parse_args(argv)
    s = SystemB(alpr=args.alpr).start()
    try:
        if args.interactive:
            print("simulated devices connected; Ctrl+C to stop")
            while True:
                time.sleep(1)
        else:
            scenario(s)
    except KeyboardInterrupt:
        pass
    finally:
        s.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
