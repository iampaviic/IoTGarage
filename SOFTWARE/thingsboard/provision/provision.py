"""Create every ThingsBoard entity of the garage in one go (idempotent - run it again any time).

    python provision.py                                   # localhost:8080, demo tenant, varijanta B
    python provision.py --url http://192.168.1.20:8080 --user tenant@thingsboard.org --password tenant
    python provision.py --demo-pricing                    # 1 minute is billed as 1 hour (demonstration)
    python provision.py --spots 4 --no-dashboards
    python provision.py --varijanta a                     # old setup: Garage-Edge gateway for tb_bridge

Varijanta B (default, PROJEKT/sustav/varijanta-b.md) creates
  * device profiles with alarm rules: ParkingSpot, Gate, ALPR, Controller
  * gateway devices with fixed access tokens: esp32-spots, esp32-gates, alpr-service
  * their devices ParkingSpot-01..06, EntranceGate, ExitGate, ALPR-Entrance, ALPR-Exit
  * asset "Garage" with "Contains" relations to all devices and the settings of the rule chain
    (pricing, accept threshold, policy); parking sessions live in its attribute "sessions"
  * the rule chain ../rulechain/garaza.json as the ROOT rule chain (decisions, sessions, alarms)
  * dashboards from ../dashboards/*.json (overwritten by title)
Running it again never deletes sessions or telemetry.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TOKEN = "garage-edge-gateway-token"           # varijanta A: tb_bridge
RULE_CHAIN = os.path.join(HERE, "..", "rulechain", "garaza.json")

# varijanta B: gateway devices (one MQTT connection each) and the devices they speak for.
# The access token is the MQTT user name; use secret tokens for the demonstration.
GATEWAYS = {
    "esp32-spots": ("TB_TOKEN_SPOTS", "esp32-spots-token", "ESP32 senzora mjesta"),
    "esp32-gates": ("TB_TOKEN_GATES", "esp32-gates-token", "ESP32 rampi"),
    "alpr-service": ("TB_TOKEN_ALPR", "alpr-service-token", "ALPR servis (kamera + OCR)"),
}
# a device that sends nothing for this long is inactive (alarm "Uređaj nije dostupan"); heartbeat is 30 s
INACTIVITY_TIMEOUT_MS = 90000
# Garage settings read by the rule chain; written only when missing, so changes made in ThingsBoard stay
GARAGE_SETTINGS = {"policy": "open", "allowlist": [], "acceptThreshold": 0.85, "freeMinutes": 15,
                   "pricePerHourCents": 150, "dailyCapCents": 1500, "timeMultiplier": 1,
                   "exitFuzzyMatch": False, "sessions": {}, "sensorFree": 0, "sensorOccupied": 0,
                   "manualPlate": ""}


# --------------------------------------------------------------------- alarm rule helpers
def _key(name: str) -> Dict[str, str]:
    return {"type": "TIME_SERIES", "key": name}


def _val(v: Any) -> Dict[str, Any]:
    return {"defaultValue": v, "userValue": None, "dynamicValue": None}


def cond_bool(key: str, value: bool) -> Dict[str, Any]:
    return {"key": _key(key), "valueType": "BOOLEAN", "value": None,
            "predicate": {"type": "BOOLEAN", "operation": "EQUAL", "value": _val(value)}}


def cond_num(key: str, op: str, value: float) -> Dict[str, Any]:
    return {"key": _key(key), "valueType": "NUMERIC", "value": None,
            "predicate": {"type": "NUMERIC", "operation": op, "value": _val(value)}}


def cond_str_in(key: str, values: List[str], negate: bool = False) -> Dict[str, Any]:
    preds = [{"type": "STRING", "operation": "NOT_EQUAL" if negate else "EQUAL", "value": _val(v),
              "ignoreCase": False} for v in values]
    return {"key": _key(key), "valueType": "STRING", "value": None,
            "predicate": {"type": "COMPLEX", "operation": "AND" if negate else "OR", "predicates": preds}}


def alarm(alarm_type: str, severity: str, create: List[Dict[str, Any]], clear: List[Dict[str, Any]],
          details: str) -> Dict[str, Any]:
    def rule(conditions):
        return {"condition": {"condition": conditions, "spec": {"type": "SIMPLE"}}, "schedule": None,
                "alarmDetails": details, "dashboardId": None}
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "garage." + alarm_type)), "alarmType": alarm_type,
            "createRules": {severity: rule(create)}, "clearRule": rule(clear),
            "propagate": True, "propagateToOwner": False, "propagateToTenant": False,
            "propagateRelationTypes": None}


PROFILES_A: Dict[str, List[Dict[str, Any]]] = {
    "ParkingSpot": [
        alarm("Senzor mjesta ne radi", "MAJOR",
              [cond_str_in("sensorStatus", ["OK", "SIMULATED"], negate=True)],
              [cond_str_in("sensorStatus", ["OK", "SIMULATED"])],
              "Mjesto ${entityName}: senzor javlja ${sensorStatus}"),
    ],
    "Gate": [
        alarm("Rampa ne potvrđuje naredbe", "MAJOR", [cond_bool("ackTimeout", True)], [cond_bool("ackTimeout", False)],
              "${entityName} nije potvrdila naredbu"),
        alarm("Rampa u kvaru", "CRITICAL", [cond_num("stateCode", "EQUAL", 4)], [cond_num("stateCode", "NOT_EQUAL", 4)],
              "${entityName} je u stanju ERROR (zatvaranje blokirano)"),
    ],
    "ALPR": [
        alarm("ALPR uzastopno ne uspijeva", "MAJOR", [cond_bool("alprFailing", True)], [cond_bool("alprFailing", False)],
              "${entityName}: više očitanja zaredom bez pouzdanog rezultata"),
    ],
    "GarageEdge": [
        alarm("Garaža puna", "WARNING", [cond_bool("full", True)], [cond_bool("full", False)],
              "Nema slobodnih mjesta"),
        alarm("Potrebna ručna intervencija", "WARNING", [cond_bool("manualRequired", True)],
              [cond_bool("manualRequired", False)], "Registracija ${decisionPlate}: ${decisionReason}"),
    ],
    "Controller": [
        alarm("Uređaj nije dostupan", "MAJOR", [cond_bool("online", False)], [cond_bool("online", True)],
              "${entityName} se ne javlja (MQTT Last Will)"),
    ],
}

# varijanta B: "Rampa ne potvrđuje naredbe", "Uređaj nije dostupan", "Garaža puna" and
# "Potrebna ručna intervencija" are raised by the rule chain (create/clear alarm nodes), not by profiles
PROFILES_B: Dict[str, List[Dict[str, Any]]] = {
    "ParkingSpot": PROFILES_A["ParkingSpot"],
    "Gate": [a for a in PROFILES_A["Gate"] if a["alarmType"] == "Rampa u kvaru"],
    "ALPR": PROFILES_A["ALPR"],
    "Controller": [],
}

PROFILE_DESCRIPTIONS = {
    "ParkingSpot": "Parkirno mjesto (HC-SR04 + ESP32)",
    "Gate": "Ulazna ili izlazna rampa (SG90 + IR senzor + ESP32)",
    "ALPR": "Kamera s prepoznavanjem registracija",
    "GarageEdge": "Edge računalo: access control, sesije, gateway prema ThingsBoardu",
    "Controller": "ESP32 / servis (heartbeat, online); u varijanti B gateway za svoje uređaje",
}


def default_positions(n: int) -> Dict[str, Dict[str, float]]:
    """Floor plan positions (0..1) - spots in a row along the top wall."""
    out = {}
    for i in range(1, n + 1):
        out["P%02d" % i] = {"x": round((i - 0.5) / n, 3), "y": 0.25}
    return out


class TbClient:
    def __init__(self, url: str, user: str, password: str, wait_s: float = 0) -> None:
        self.url = url.rstrip("/")
        self.h = {"X-Authorization": "Bearer " + self._login(user, password, wait_s)}

    def _login(self, user: str, password: str, wait_s: float) -> str:
        """Log in; while ThingsBoard is still starting (first start installs the database) retry up to wait_s."""
        end = time.time() + wait_s
        while True:
            try:
                r = requests.post(self.url + "/api/auth/login", json={"username": user, "password": password},
                                  timeout=20, allow_redirects=False)
                if r.status_code == 200 and "token" in r.text:
                    return r.json()["token"]
                if r.status_code == 401:
                    raise SystemExit("login failed (401): wrong user or password")
                problem = "HTTP %s" % r.status_code
            except requests.RequestException as e:
                problem = type(e).__name__
            if time.time() >= end:
                raise SystemExit("ThingsBoard at %s is not ready (%s)" % (self.url, problem))
            print("waiting for ThingsBoard (%s) ..." % problem)
            time.sleep(5)

    def get(self, path: str, **params) -> Any:
        r = requests.get(self.url + path, headers=self.h, params=params, timeout=20)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json() if r.text else None

    def post(self, path: str, body: Any = None, **params) -> Any:
        r = requests.post(self.url + path, headers=self.h, json=body, params=params, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError("POST %s -> %s %s" % (path, r.status_code, r.text[:300]))
        return r.json() if r.text else None

    # ------------------------------------------------------------- entities
    def find_profile(self, name: str) -> Optional[Dict[str, Any]]:
        page = self.get("/api/deviceProfiles", pageSize=100, page=0, textSearch=name)
        for p in page["data"]:
            if p["name"] == name:
                return p
        return None

    def ensure_profile(self, name: str, alarms: List[Dict[str, Any]], queue: Optional[str] = None) -> Dict[str, Any]:
        p = self.find_profile(name) or {
            "name": name, "type": "DEFAULT", "transportType": "DEFAULT", "provisionType": "DISABLED",
            "profileData": {"configuration": {"type": "DEFAULT"}, "transportConfiguration": {"type": "DEFAULT"},
                            "provisionConfiguration": {"type": "DISABLED", "provisionDeviceSecret": None}}}
        p["description"] = PROFILE_DESCRIPTIONS.get(name, "")
        p["profileData"]["alarms"] = alarms
        p["defaultQueueName"] = queue
        return self.post("/api/deviceProfile", p)

    def ensure_device(self, name: str, profile: Dict[str, Any], label: str = "", gateway: bool = False,
                      token: Optional[str] = None) -> Dict[str, Any]:
        dev = self.get("/api/tenant/devices", deviceName=name)
        body = dev or {"name": name}
        body.update(type=profile["name"], label=label, deviceProfileId=profile["id"])
        info = body.get("additionalInfo") or {}
        if gateway:
            info.update(gateway=True, overwriteActivityTime=False, description="IoT Garage edge gateway")
        body["additionalInfo"] = info
        if dev is None and token:
            return self.post("/api/device", body, accessToken=token)
        saved = self.post("/api/device", body)
        if token:
            creds = self.get("/api/device/%s/credentials" % saved["id"]["id"])
            if creds["credentialsId"] != token:
                creds["credentialsId"] = token
                self.post("/api/device/credentials", creds)
        return saved

    def ensure_asset(self, name: str, type_: str, label: str = "") -> Dict[str, Any]:
        asset = self.get("/api/tenant/assets", assetName=name)
        body = asset or {"name": name, "type": type_}
        body["label"] = label
        if asset is None:
            # asset profile is created automatically from the type name
            body.pop("assetProfileId", None)
        return self.post("/api/asset", body)

    def server_attributes_missing(self, entity: Dict[str, Any], attrs: Dict[str, Any]) -> List[str]:
        """Write only the attributes that do not exist yet (keeps sessions and settings changed in ThingsBoard)."""
        eid = entity["id"]
        have = self.get("/api/plugins/telemetry/%s/%s/values/attributes/SERVER_SCOPE" % (eid["entityType"], eid["id"]))
        names = {a["key"] for a in have or []}
        missing = {k: v for k, v in attrs.items() if k not in names}
        if missing:
            self.server_attributes(entity, missing)
        return sorted(missing)

    def ensure_root_rule_chain(self, path: str) -> Dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        name = data["ruleChain"]["name"]
        page = self.get("/api/ruleChains", pageSize=100, page=0, textSearch=name, type="CORE")
        existing = [r for r in page["data"] if r["name"] == name]
        chain = existing[0] if existing else self.post("/api/ruleChain", {
            "name": name, "type": "CORE", "debugMode": False, "additionalInfo": data["ruleChain"]["additionalInfo"]})
        md = dict(data["metadata"])
        md["ruleChainId"] = chain["id"]
        if existing:
            md["version"] = (self.get("/api/ruleChain/%s/metadata" % chain["id"]["id"]) or {}).get("version")
        self.post("/api/ruleChain/metadata", md)
        if not chain.get("root"):
            self.post("/api/ruleChain/%s/root" % chain["id"]["id"])
        return chain

    def relate(self, frm: Dict[str, Any], to: Dict[str, Any], rel_type: str = "Contains") -> None:
        self.post("/api/relation", {"from": frm["id"], "to": to["id"], "type": rel_type, "typeGroup": "COMMON"})

    def server_attributes(self, entity: Dict[str, Any], attrs: Dict[str, Any]) -> None:
        eid = entity["id"]
        self.post("/api/plugins/telemetry/%s/%s/attributes/SERVER_SCOPE" % (eid["entityType"], eid["id"]), attrs)

    def upsert_dashboard(self, dashboard: Dict[str, Any]) -> Dict[str, Any]:
        page = self.get("/api/tenant/dashboards", pageSize=100, page=0, textSearch=dashboard["title"])
        existing = [d for d in page["data"] if d["title"] == dashboard["title"]]
        body = dict(dashboard)
        body.pop("id", None)
        body.pop("tenantId", None)
        body.pop("createdTime", None)
        if existing:
            body["id"] = existing[0]["id"]
            body["version"] = self.get("/api/dashboard/%s" % existing[0]["id"]["id"]).get("version")
        return self.post("/api/dashboard", body)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("TB_URL", "http://localhost:8080"))
    ap.add_argument("--user", default=os.environ.get("TB_USER", "tenant@thingsboard.org"))
    ap.add_argument("--password", default=os.environ.get("TB_PASSWORD", "tenant"))
    ap.add_argument("--spots", type=int, default=int(os.environ.get("GARAGE_SPOTS", "6")))
    ap.add_argument("--varijanta", choices=["a", "b"], default=os.environ.get("GARAGE_VARIJANTA", "b").lower(),
                    help="b (default): everything in ThingsBoard; a: old setup with the Garage-Edge gateway")
    ap.add_argument("--token", default=os.environ.get("TB_GATEWAY_TOKEN", DEFAULT_TOKEN),
                    help="varijanta A: access token for the Garage-Edge gateway (use a secret one for the demo!)")
    ap.add_argument("--demo-pricing", action="store_true",
                    help="varijanta B: 1 minute is billed as 1 hour (sets timeMultiplier=60 on Garage)")
    ap.add_argument("--positions", help="spots.json from SOFTWARE/maketa (floor plan positions)")
    ap.add_argument("--no-dashboards", action="store_true")
    ap.add_argument("--wait", type=float, default=300, metavar="SECONDS",
                    help="wait this long for ThingsBoard to start (default 300)")
    args = ap.parse_args(argv)

    tb = TbClient(args.url, args.user, args.password, args.wait)
    print("connected to", args.url, "- varijanta", args.varijanta.upper())
    b = args.varijanta == "b"
    # varijanta B: messages of every device in order (see QUEUE in rulechain/build_rule_chain.py)
    queue = "SequentialByOriginator" if b else None
    profiles = {name: tb.ensure_profile(name, alarms, queue) for name, alarms in (PROFILES_B if b else PROFILES_A).items()}
    print("device profiles:", ", ".join(profiles))

    positions = default_positions(args.spots)
    if args.positions:
        with open(args.positions, encoding="utf-8") as f:
            positions.update(json.load(f))
    garage = tb.ensure_asset("Garage", "Garage", "IoT Garaža (maketa)")
    tb.server_attributes(garage, {"name": "IoT Garaža", "totalSpots": args.spots,
                                  "address": "Maketa - laboratorij", "timezone": "Europe/Zagreb"})
    devices = []
    for i in range(1, args.spots + 1):
        spot = "P%02d" % i
        d = tb.ensure_device("ParkingSpot-%02d" % i, profiles["ParkingSpot"], "Mjesto %s" % spot)
        tb.server_attributes(d, {"spotId": spot, "name": "Mjesto %s" % spot, "index": i,
                                 "xPos": positions[spot]["x"], "yPos": positions[spot]["y"]})
        devices.append(d)
    for name, label, gate in (("EntranceGate", "Ulazna rampa", "ENTRANCE"), ("ExitGate", "Izlazna rampa", "EXIT")):
        d = tb.ensure_device(name, profiles["Gate"], label)
        tb.server_attributes(d, {"gate": gate, "name": label})
        devices.append(d)
    for name, label, gate in (("ALPR-Entrance", "Kamera ulaz", "ENTRANCE"), ("ALPR-Exit", "Kamera izlaz", "EXIT")):
        d = tb.ensure_device(name, profiles["ALPR"], label)
        tb.server_attributes(d, {"gate": gate, "name": label})
        devices.append(d)
    tokens = {}
    if b:
        for name, (env, default, label) in GATEWAYS.items():
            tokens[name] = os.environ.get(env, default)
            d = tb.ensure_device(name, profiles["Controller"], label, gateway=True, token=tokens[name])
            tb.server_attributes(d, {"name": label, "inactivityTimeout": INACTIVITY_TIMEOUT_MS})
            devices.append(d)
        settings = dict(GARAGE_SETTINGS, totalSpots=args.spots)
        added = tb.server_attributes_missing(garage, settings)
        if args.demo_pricing:
            tb.server_attributes(garage, {"timeMultiplier": 60})
        print("garage settings added:", ", ".join(added) or "none (kept the existing ones)")
    else:
        edge = tb.ensure_device("Garage-Edge", profiles["GarageEdge"], "Edge računalo", gateway=True, token=args.token)
        tb.server_attributes(edge, {"name": "Edge računalo", "totalSpots": args.spots})
        devices.append(edge)
    for d in devices:
        tb.relate(garage, d)
    print("devices:", ", ".join(d["name"] for d in devices))
    if b:
        chain = tb.ensure_root_rule_chain(RULE_CHAIN)
        print("root rule chain: %s -> %s/ruleChains/%s" % (chain["name"], args.url, chain["id"]["id"]))
        for name, token in tokens.items():
            print("access token %-13s %s" % (name, token))
    else:
        print("gateway token for the bridge: TB_GATEWAY_TOKEN=%s" % args.token)

    if not args.no_dashboards:
        for path in sorted(glob.glob(os.path.join(HERE, "..", "dashboards", "*.json"))):
            with open(path, encoding="utf-8") as f:
                dash = json.load(f)
            saved = tb.upsert_dashboard(dash)
            print("dashboard: %s -> %s/dashboards/%s" % (dash["title"], args.url, saved["id"]["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
