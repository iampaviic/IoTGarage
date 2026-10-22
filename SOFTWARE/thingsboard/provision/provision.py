"""Create every ThingsBoard entity of the garage in one go (idempotent - run it again any time).

    python provision.py                                   # localhost:8080, demo tenant
    python provision.py --url http://192.168.1.20:8080 --user tenant@thingsboard.org --password tenant
    python provision.py --spots 4 --no-dashboards

Creates
  * device profiles with alarm rules: ParkingSpot, Gate, ALPR, GarageEdge, Controller
  * devices ParkingSpot-01..06, EntranceGate, ExitGate, ALPR-Entrance, ALPR-Exit
  * the gateway device Garage-Edge with a fixed access token (used by the bridge)
  * asset "Garage" with "Contains" relations to all devices
  * server attributes: name, position on the floor plan, ...
  * dashboards from ../dashboards/*.json (overwritten by title)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TOKEN = "garage-edge-gateway-token"


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


PROFILES: Dict[str, List[Dict[str, Any]]] = {
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

PROFILE_DESCRIPTIONS = {
    "ParkingSpot": "Parkirno mjesto (HC-SR04 + ESP32)",
    "Gate": "Ulazna ili izlazna rampa (SG90 + IR senzor + ESP32)",
    "ALPR": "Kamera s prepoznavanjem registracija",
    "GarageEdge": "Edge računalo: access control, sesije, gateway prema ThingsBoardu",
    "Controller": "ESP32 / servis na edge računalu (heartbeat, online)",
}


def default_positions(n: int) -> Dict[str, Dict[str, float]]:
    """Floor plan positions (0..1) - spots in a row along the top wall."""
    out = {}
    for i in range(1, n + 1):
        out["P%02d" % i] = {"x": round((i - 0.5) / n, 3), "y": 0.25}
    return out


class TbClient:
    def __init__(self, url: str, user: str, password: str) -> None:
        self.url = url.rstrip("/")
        r = requests.post(self.url + "/api/auth/login", json={"username": user, "password": password}, timeout=20)
        if r.status_code != 200:
            raise SystemExit("login failed (%s): %s" % (r.status_code, r.text[:200]))
        self.h = {"X-Authorization": "Bearer " + r.json()["token"]}

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

    def ensure_profile(self, name: str, alarms: List[Dict[str, Any]]) -> Dict[str, Any]:
        p = self.find_profile(name) or {
            "name": name, "type": "DEFAULT", "transportType": "DEFAULT", "provisionType": "DISABLED",
            "profileData": {"configuration": {"type": "DEFAULT"}, "transportConfiguration": {"type": "DEFAULT"},
                            "provisionConfiguration": {"type": "DISABLED", "provisionDeviceSecret": None}}}
        p["description"] = PROFILE_DESCRIPTIONS.get(name, "")
        p["profileData"]["alarms"] = alarms
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
    ap.add_argument("--token", default=os.environ.get("TB_GATEWAY_TOKEN", DEFAULT_TOKEN),
                    help="access token for the Garage-Edge gateway (use a secret one for the demo!)")
    ap.add_argument("--positions", help="spots.json from SOFTWARE/maketa (floor plan positions)")
    ap.add_argument("--no-dashboards", action="store_true")
    args = ap.parse_args(argv)

    tb = TbClient(args.url, args.user, args.password)
    print("connected to", args.url)
    profiles = {name: tb.ensure_profile(name, alarms) for name, alarms in PROFILES.items()}
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
    edge = tb.ensure_device("Garage-Edge", profiles["GarageEdge"], "Edge računalo", gateway=True, token=args.token)
    tb.server_attributes(edge, {"name": "Edge računalo", "totalSpots": args.spots})
    devices.append(edge)
    for d in devices:
        tb.relate(garage, d)
    print("devices:", ", ".join(d["name"] for d in devices))
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
