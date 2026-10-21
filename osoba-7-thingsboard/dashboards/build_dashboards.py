"""Generate the two garage dashboards from code (needs a running ThingsBoard for the widget defaults).

    python build_dashboards.py --url http://localhost:8080        # writes glavni.json + analitika.json here
    python ../provision/provision.py                              # imports them

The generated JSON files are committed, so normally you only re-run this script
after changing the dashboards in code. Changes made in the ThingsBoard UI can be
exported (Dashboard -> Export) over the JSON files instead.

Entity aliases use device TYPES and NAMES, never IDs, so the JSON works on any
ThingsBoard where provision.py created the devices.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
import uuid
from typing import Any, Dict, List, Optional

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(42)

# ------------------------------------------------------------------ JS used in widgets
FLOOR_PLAN_FUNCTION = r"""
var spots = [], gates = {}, alpr = {}, edge = {};
for (var i = 0; i < data.length; i++) {
  var d = data[i], n = d.entityName || '';
  if (n.indexOf('ParkingSpot') === 0) spots.push(d);
  else if (n === 'EntranceGate' || n === 'ExitGate') gates[n] = d;
  else if (n.indexOf('ALPR') === 0) alpr[n] = d;
  else if (n === 'Garage-Edge') edge = d;
}
spots.sort(function (a, b) { return a.entityName < b.entityName ? -1 : 1; });
function spotClass(s) { return s === 'FREE' ? 'free' : (s === 'OCCUPIED' ? 'occ' : 'unk'); }
function spotText(s) { return s === 'FREE' ? 'slobodno' : (s === 'OCCUPIED' ? 'zauzeto' : 'nepoznato'); }
function gateClass(s) { return s === 'OPEN' ? 'open' : (s === 'ERROR' ? 'err' : (s === 'OPENING' || s === 'CLOSING' ? 'moving' : 'closed')); }
var gateNames = { CLOSED: 'zatvorena', OPENING: 'otvara se', OPEN: 'otvorena', CLOSING: 'zatvara se', ERROR: 'KVAR' };
function fmtPlate(p) {
  var m = /^([A-Z]{2})(\d{3,4})([A-Z]{1,2})$/.exec(p || '');
  return m ? m[1] + ' ' + m[2] + '-' + m[3] : (p || '-');
}
function gateHtml(name, label, camera) {
  var g = gates[name] || {}, a = alpr[camera] || {};
  var conf = a.alprConfidence !== undefined && a.alprConfidence !== '' ? Math.round(Number(a.alprConfidence) * 100) + ' %' : '';
  return '<div class="gate ' + gateClass(g.gateState) + '">' +
    '<div class="gname">' + label + '</div>' +
    '<div class="barrier"></div>' +
    '<div class="gstate">' + (gateNames[g.gateState] || '-') + (String(g.vehiclePresent) === 'true' ? ' &middot; vozilo' : '') + '</div>' +
    '<div class="plate">' + fmtPlate(a.alprPlate) + '</div>' +
    '<div class="conf">' + (conf ? 'pouzdanost ' + conf : '') + '</div></div>';
}
var html = '<div class="garage"><div class="spots">';
for (var j = 0; j < spots.length; j++) {
  var s = spots[j];
  html += '<div class="spot ' + spotClass(s.spotState) + '"><div class="sid">P' + s.entityName.slice(-2) + '</div>' +
          '<div class="car"></div><div class="stxt">' + spotText(s.spotState) + '</div></div>';
}
html += '</div><div class="lane">&larr; &nbsp; prometnica &nbsp; &rarr;</div><div class="gates">' +
        gateHtml('EntranceGate', 'ULAZ', 'ALPR-Entrance') +
        '<div class="free-count"><div class="num">' + (edge.freeSpots !== undefined && edge.freeSpots !== '' ? edge.freeSpots : '-') +
        '</div><div>slobodnih mjesta</div></div>' +
        gateHtml('ExitGate', 'IZLAZ', 'ALPR-Exit') + '</div></div>';
return html;
"""

FLOOR_PLAN_CSS = """
.garage { font-family: Roboto, Arial, sans-serif; height: 100%; display: flex; flex-direction: column; gap: 10px; }
.spots { display: flex; gap: 8px; flex: 1; min-height: 110px; }
.spot { flex: 1; border-radius: 8px; border: 3px dashed #ffffff; color: #fff; display: flex; flex-direction: column;
        align-items: center; justify-content: space-between; padding: 6px 0; font-weight: 500; }
.spot .sid { font-size: 20px; }
.spot .stxt { font-size: 13px; text-transform: uppercase; letter-spacing: .5px; }
.spot.free { background: #2e7d32; }
.spot.occ { background: #c62828; }
.spot.unk { background: #757575; }
.spot .car { width: 46%; height: 34%; border-radius: 6px; }
.spot.occ .car { background: rgba(255,255,255,.85); }
.lane { text-align: center; background: #424242; color: #fafafa; padding: 6px; border-radius: 6px; letter-spacing: 2px; }
.gates { display: flex; gap: 10px; }
.gate { flex: 1; border-radius: 8px; padding: 8px; background: #eceff1; text-align: center; border-left: 8px solid #c62828; }
.gate.open { border-left-color: #2e7d32; }
.gate.moving { border-left-color: #f9a825; }
.gate.err { border-left-color: #6a1b9a; background: #f3e5f5; }
.gate .gname { font-weight: 700; letter-spacing: 1px; }
.gate .barrier { height: 6px; margin: 6px 20%; background: repeating-linear-gradient(90deg, #c62828 0 12px, #fff 12px 24px); }
.gate.open .barrier { transform: rotate(-60deg); transform-origin: left; width: 30px; }
.gate .plate { display: inline-block; margin-top: 6px; padding: 2px 10px; border: 2px solid #212121; border-radius: 4px;
               background: #fff; font: 700 20px 'DejaVu Sans Condensed', Arial Narrow, sans-serif; letter-spacing: 1px; }
.gate .conf, .gate .gstate { font-size: 12px; color: #455a64; margin-top: 2px; }
.free-count { flex: 0 0 140px; background: #1565c0; color: #fff; border-radius: 8px; display: flex; flex-direction: column;
              justify-content: center; align-items: center; }
.free-count .num { font-size: 44px; font-weight: 700; line-height: 1; }
"""

STATE_COLOR = """var c = {FREE: '#2e7d32', OCCUPIED: '#c62828', UNKNOWN: '#757575', OPEN: '#2e7d32', OPENING: '#f9a825',
 CLOSING: '#f9a825', CLOSED: '#c62828', ERROR: '#6a1b9a', GRANTED: '#2e7d32', DENIED: '#c62828',
 RETRY: '#f9a825', MANUAL_REQUIRED: '#6a1b9a'}[value];
return c ? {color: '#fff', background: c, fontWeight: 500, borderRadius: '4px'} : {};"""


# ------------------------------------------------------------------ helpers
def uid() -> str:
    return str(uuid.UUID(int=rnd.getrandbits(128)))


def deep_merge(base: Any, over: Any) -> Any:
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = deep_merge(base.get(k), v) if k in base else v
        return out
    return copy.deepcopy(over)


def key(name: str, label: Optional[str] = None, type_: str = "timeseries", color: str = "#2196f3",
        settings: Optional[Dict[str, Any]] = None, units: Optional[str] = None, decimals: Optional[int] = None,
        agg: Optional[str] = None) -> Dict[str, Any]:
    k = {"name": name, "type": type_, "label": label or name, "color": color, "settings": settings or {},
         "_hash": rnd.random(), "units": units, "decimals": decimals, "funcBody": None,
         "usePostProcessing": None, "postFuncBody": None}
    if agg:
        k["aggregationType"] = agg
    return k


def ds(alias_id: str, keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "entity", "entityAliasId": alias_id, "filterId": None, "dataKeys": keys}


class Builder:
    def __init__(self, tb_url: str, user: str, password: str) -> None:
        self.url = tb_url.rstrip("/")
        tok = requests.post(self.url + "/api/auth/login", json={"username": user, "password": password}, timeout=20)
        tok.raise_for_status()
        self.h = {"X-Authorization": "Bearer " + tok.json()["token"]}
        self._defaults: Dict[str, Dict[str, Any]] = {}

    def defaults(self, fqn: str) -> Dict[str, Any]:
        if fqn not in self._defaults:
            r = requests.get(self.url + "/api/widgetType", params={"fqn": fqn}, headers=self.h, timeout=20)
            r.raise_for_status()
            desc = r.json()["descriptor"]
            self._defaults[fqn] = {"type": desc["type"], "config": json.loads(desc.get("defaultConfig") or "{}"),
                                   "sizeX": desc.get("sizeX", 8), "sizeY": desc.get("sizeY", 5)}
        return self._defaults[fqn]

    def widget(self, fqn: str, title: str, datasources: Optional[List[Dict[str, Any]]], over: Dict[str, Any]) -> Dict[str, Any]:
        d = self.defaults(fqn)
        cfg = copy.deepcopy(d["config"])
        cfg = deep_merge(cfg, {"title": title, "showTitle": True})
        if datasources is not None:
            cfg["datasources"] = datasources
        cfg = deep_merge(cfg, over)
        return {"typeFullFqn": fqn, "type": d["type"], "sizeX": d["sizeX"], "sizeY": d["sizeY"], "config": cfg,
                "row": 0, "col": 0, "id": uid()}


def dashboard(title: str, aliases: Dict[str, Dict[str, Any]], placed: List[tuple], description: str) -> Dict[str, Any]:
    widgets, layout = {}, {}
    for w, col, row, sx, sy in placed:
        w["sizeX"], w["sizeY"], w["col"], w["row"] = sx, sy, col, row
        widgets[w["id"]] = w
        layout[w["id"]] = {"sizeX": sx, "sizeY": sy, "row": row, "col": col}
    return {
        "title": title,
        "configuration": {
            "description": description,
            "widgets": widgets,
            "states": {"default": {"name": title, "root": True, "layouts": {"main": {
                "widgets": layout,
                "gridSettings": {"backgroundColor": "#eceff1", "columns": 24, "margin": 10, "outerMargin": True,
                                 "backgroundSizeMode": "100%", "autoFillHeight": False, "mobileAutoFillHeight": False,
                                 "mobileRowHeight": 70, "layoutType": "default"}}}}},
            "entityAliases": aliases,
            "filters": {},
            "timewindow": {"displayValue": "", "hideInterval": False, "hideAggregation": False,
                           "selectedTab": 0, "realtime": {"realtimeType": 0, "interval": 1000, "timewindowMs": 3600000},
                           "aggregation": {"type": "NONE", "limit": 25000}},
            "settings": {"stateControllerId": "entity", "showTitle": True, "showDashboardsSelect": True,
                         "showEntitiesSelect": False, "showDashboardTimewindow": True, "showDashboardExport": True,
                         "toolbarAlwaysOpen": True},
        },
        "name": title,
    }


def aliases() -> Dict[str, Dict[str, Any]]:
    def device_type(name, types):
        return {"alias": name, "filter": {"type": "deviceType", "resolveMultiple": True, "deviceTypes": types,
                                          "deviceType": types[0], "deviceNameFilter": ""}}

    def by_name(name, entity_type, entity_name, multiple=False):
        return {"alias": name, "filter": {"type": "entityName", "resolveMultiple": multiple,
                                          "entityType": entity_type, "entityNameFilter": entity_name}}
    a = {
        "spots": device_type("Parkirna mjesta", ["ParkingSpot"]),
        "gates": device_type("Rampe", ["Gate"]),
        "alpr": device_type("Kamere", ["ALPR"]),
        "edge": by_name("Edge", "DEVICE", "Garage-Edge"),
        "entrance": by_name("Ulazna rampa", "DEVICE", "EntranceGate"),
        "exit": by_name("Izlazna rampa", "DEVICE", "ExitGate"),
        "garage": by_name("Garaža", "ASSET", "Garage"),
        "controllers": device_type("Kontroleri", ["Controller"]),
    }
    out = {}
    for short, alias in a.items():
        alias_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "garage.alias." + short))
        alias["id"] = alias_id
        out[short] = alias
    return out


def rpc_button(b: Builder, title: str, text: str, alias_id: str, method: str, primary: bool = True) -> Dict[str, Any]:
    return b.widget("system.control_widgets.rpcbutton", title, None, {
        "showTitle": False,
        "targetDeviceAliases": [alias_id],
        "targetDevice": {"type": "entity", "entityAliasId": alias_id},
        "settings": {"requestTimeout": 5000, "oneWayElseTwoWay": False, "buttonText": text,
                     "styleButton": {"isRaised": True, "isPrimary": primary}, "methodName": method,
                     "methodParams": "{}"},
    })


def value_card(b: Builder, title: str, alias_id: str, k: Dict[str, Any], icon: str, color_fn: Optional[str] = None) -> Dict[str, Any]:
    over: Dict[str, Any] = {"showTitle": False, "units": k.get("units") or "", "decimals": k.get("decimals"),
                            "settings": {"icon": icon, "showDate": True, "layout": "square"}}
    if color_fn:
        over["settings"]["valueColor"] = {"type": "function", "color": "rgba(0, 0, 0, 0.87)", "colorFunction": color_fn}
        over["settings"]["iconColor"] = {"type": "function", "color": "#5469FF", "colorFunction": color_fn}
    return b.widget("system.cards.value_card", title, [ds(alias_id, [k])], over)


def ts_table(b: Builder, title: str, alias_id: str, keys: List[Dict[str, Any]], window_ms: int) -> Dict[str, Any]:
    return b.widget("system.cards.timeseries_table", title, [ds(alias_id, keys)], {
        "useDashboardTimewindow": False, "displayTimewindow": True,
        "timewindow": {"realtime": {"realtimeType": 0, "interval": 1000, "timewindowMs": window_ms},
                       "aggregation": {"type": "NONE", "limit": 500}},
        "settings": {"showTimestamp": True, "displayPagination": True, "defaultPageSize": 8,
                     "defaultSortOrder": "-0", "hideEmptyLines": True, "showMilliseconds": False},
    })


def chart(b: Builder, title: str, alias_id: str, keys: List[Dict[str, Any]], window_ms: int, interval_ms: int,
          agg: str, bar: bool = False, units: str = "") -> Dict[str, Any]:
    fqn = "system.bar_chart" if bar else "system.time_series_chart"
    for k in keys:
        k["settings"] = deep_merge({"type": "bar" if bar else "line"}, k.get("settings", {}))
        if not bar:
            k["settings"].setdefault("lineSettings", {"step": True, "stepType": "end", "smooth": False,
                                                      "showPoints": False, "lineWidth": 2})
    return b.widget(fqn, title, [ds(alias_id, keys)], {
        "useDashboardTimewindow": False, "displayTimewindow": True,
        "timewindow": {"realtime": {"realtimeType": 0, "interval": interval_ms, "timewindowMs": window_ms},
                       "aggregation": {"type": agg, "limit": 50000}},
        "units": units,
    })


# ------------------------------------------------------------------ dashboards
def build_main(b: Builder) -> Dict[str, Any]:
    a = aliases()
    A = {k: v["id"] for k, v in a.items()}
    floor = b.widget("system.cards.markdown_card", "Tlocrt garaže", [
        ds(A["spots"], [key("state", "spotState")]),
        ds(A["gates"], [key("state", "gateState"), key("vehiclePresent", "vehiclePresent")]),
        ds(A["alpr"], [key("plate", "alprPlate"), key("ocrConfidence", "alprConfidence")]),
        ds(A["edge"], [key("freeSpots", "freeSpots")]),
    ], {"settings": {"useMarkdownTextFunction": True, "markdownTextFunction": FLOOR_PLAN_FUNCTION,
                     "markdownCss": FLOOR_PLAN_CSS, "applyDefaultMarkdownStyle": False}, "padding": "8px"})
    free = value_card(b, "Slobodna mjesta", A["edge"], key("freeSpots", "Slobodna mjesta", decimals=0), "local_parking",
                      "return value > 0 ? '#2e7d32' : '#c62828';")
    occ = value_card(b, "Popunjenost", A["edge"], key("occupancyPct", "Popunjenost", units="%", decimals=0), "pie_chart")
    act = value_card(b, "Aktivne sesije", A["edge"], key("activeSessions", "Vozila u garaži", decimals=0), "directions_car")
    ent_state = value_card(b, "Ulazna rampa", A["entrance"], key("state", "Ulazna rampa"), "fence", STATE_ICON_COLOR)
    ex_state = value_card(b, "Izlazna rampa", A["exit"], key("state", "Izlazna rampa"), "fence", STATE_ICON_COLOR)
    btns = [
        rpc_button(b, "Otvori ulaz", "Otvori ulaz", A["entrance"], "open"),
        rpc_button(b, "Otvori izlaz", "Otvori izlaz", A["exit"], "open"),
        rpc_button(b, "Odobri ulaz", "Ručno odobri ulaz", A["edge"], "approveEntry"),
        rpc_button(b, "Odobri izlaz", "Ručno odobri izlaz", A["edge"], "approveExit"),
        rpc_button(b, "Odbij", "Odbij vozilo na ulazu", A["edge"], "deny", primary=False),
    ]
    decisions = ts_table(b, "Odluke pristupa (zadnji sat)", A["edge"], [
        key("decisionDirection", "Smjer"), key("decisionPlate", "Registracija"),
        key("decision", "Odluka", settings={"useCellStyleFunction": True, "cellStyleFunction": STATE_COLOR}),
        key("decisionReason", "Razlog"), key("decisionConfidence", "Pouzdanost", decimals=2),
        key("decisionManual", "Ručno"),
    ], 3600 * 1000)
    alarms = b.widget("system.alarm_widgets.alarms_table", "Alarmi", None, {
        "alarmSource": {"type": "entity", "entityAliasId": A["garage"], "dataKeys": b.defaults(
            "system.alarm_widgets.alarms_table")["config"]["alarmSource"]["dataKeys"]},
        "alarmsTitle": "Alarmi", "settings": {"alarmsTitle": "Alarmi", "defaultPageSize": 6},
        "alarmSearchStatus": "ANY", "alarmStatusList": [], "useDashboardTimewindow": False,
        # alarms of all devices are propagated to the Garage asset (relation "Contains")
        "alarmFilterConfig": {"statusList": [], "severityList": [], "typeList": [], "searchPropagatedAlarms": True},
        "timewindow": {"realtime": {"realtimeType": 0, "interval": 1000, "timewindowMs": 7 * 86400000},
                       "aggregation": {"type": "NONE", "limit": 200}},
    })
    placed = [
        (floor, 0, 0, 16, 9),
        (free, 16, 0, 4, 3), (occ, 20, 0, 4, 3),
        (act, 16, 3, 4, 3), (ent_state, 20, 3, 4, 3),
        (ex_state, 20, 6, 4, 3),
        (btns[0], 16, 6, 4, 1), (btns[1], 16, 7, 4, 1), (btns[2], 16, 8, 4, 1),
        (decisions, 0, 9, 14, 7),
        (alarms, 14, 9, 10, 6), (btns[3], 14, 15, 5, 1), (btns[4], 19, 15, 5, 1),
    ]
    return dashboard("Garaža - nadzor", {v["id"]: v for v in a.values()}, placed,
                     "Stanje mjesta, rampi i kamera u stvarnom vremenu; ručno upravljanje; odluke i alarmi.")


STATE_ICON_COLOR = """var c = {OPEN: '#2e7d32', OPENING: '#f9a825', CLOSING: '#f9a825', CLOSED: '#c62828', ERROR: '#6a1b9a'}[value];
return c || 'rgba(0,0,0,0.54)';"""


def build_analytics(b: Builder) -> Dict[str, Any]:
    a = aliases()
    A = {k: v["id"] for k, v in a.items()}
    day, week, hour = 86400000, 7 * 86400000, 3600000
    occupancy = chart(b, "Zauzetost kroz vrijeme", A["edge"], [
        key("occupiedSpots", "Zauzeta mjesta", color="#c62828"), key("freeSpots", "Slobodna mjesta", color="#2e7d32"),
        key("unknownSpots", "Nepoznato", color="#757575")], day, 60000, "NONE")
    pct = chart(b, "Popunjenost [%] (prosjek po satu)", A["edge"], [
        key("occupancyPct", "Popunjenost", color="#1565c0", units="%", decimals=0)], week, hour, "AVG", bar=True, units="%")
    entries = chart(b, "Broj ulazaka po satu", A["edge"], [
        key("entry", "Ulasci", color="#1565c0", decimals=0), key("exit", "Izlasci", color="#f9a825", decimals=0)],
        day, hour, "SUM", bar=True)
    duration = chart(b, "Prosječno trajanje parkiranja [min] po danu", A["edge"], [
        key("durationMin", "Trajanje", color="#6a1b9a", units="min", decimals=0)], week, day, "AVG", bar=True, units="min")
    revenue = chart(b, "Prihod po danu [EUR]", A["edge"], [
        key("price", "Prihod", color="#2e7d32", units="EUR", decimals=2)], week, day, "SUM", bar=True, units="EUR")
    avg_card = b.widget("system.cards.aggregated_value_card", "Prosječno trajanje (7 dana)", [ds(A["edge"], [
        key("durationMin", "Prosječno trajanje", units="min", decimals=0)])], {
        "useDashboardTimewindow": False,
        "timewindow": {"realtime": {"realtimeType": 0, "interval": day, "timewindowMs": week},
                       "aggregation": {"type": "AVG", "limit": 50000}}})
    sessions = ts_table(b, "Završene parkirne sesije (7 dana)", A["edge"], [
        key("sessionPlate", "Registracija"), key("sessionEvent", "Događaj"), key("sessionEntryTime", "Ulazak (UTC)"),
        key("durationMin", "Trajanje [min]", decimals=1), key("price", "Cijena [EUR]", decimals=2)], week)
    placed = [
        (occupancy, 0, 0, 12, 6), (entries, 12, 0, 12, 6),
        (pct, 0, 6, 12, 6), (duration, 12, 6, 8, 6), (avg_card, 20, 6, 4, 6),
        (revenue, 0, 12, 10, 6), (sessions, 10, 12, 14, 6),
    ]
    return dashboard("Garaža - analitika", {v["id"]: v for v in a.values()}, placed,
                     "Zauzetost kroz vrijeme, ulasci po satu, prosječno trajanje, popunjenost i prihod.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("TB_URL", "http://localhost:8080"))
    ap.add_argument("--user", default=os.environ.get("TB_USER", "tenant@thingsboard.org"))
    ap.add_argument("--password", default=os.environ.get("TB_PASSWORD", "tenant"))
    args = ap.parse_args(argv)
    b = Builder(args.url, args.user, args.password)
    for name, dash in (("glavni.json", build_main(b)), ("analitika.json", build_analytics(b))):
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            json.dump(dash, f, ensure_ascii=False, indent=1)
        print("wrote", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
