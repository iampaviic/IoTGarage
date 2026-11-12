"""Build the garage rule chain (varijanta B) from the TBEL scripts in scripts/.

    python build_rule_chain.py          # writes garaza.json next to this file
    python ../provision/provision.py    # imports garaza.json and makes it the root rule chain

garaza.json is committed: it can also be imported by hand (Rule chains -> + -> Import).
Edit the scripts and this file, not the JSON; changes made in the ThingsBoard UI are
lost on the next provision.py run unless they are copied back here.

What the chain does (details in PROJEKT/sustav/varijanta-b.md):
  * every device message: alarm rules of the device profile, telemetry and attributes saved
  * esp32-spots counts (freeSpots, occupiedSpots) -> Garage attributes -> summary, alarm "Garaža puna"
  * gate telemetry vehicleArrived=true -> RPC readPlate to ALPR-Entrance / ALPR-Exit -> decision ->
    session in the Garage attribute "sessions", decision telemetry, RPC open to the gate, alarms
  * dashboard RPC approve / deny to a gate -> same decision path (manual), the gate answers the dashboard
  * connect / disconnect of devices -> online, spots UNKNOWN/OFFLINE, alarm "Uređaj nije dostupan"
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "Garaža (varijanta B)"
OUT = os.path.join(HERE, "garaza.json")

PKG = "org.thingsboard.rule.engine."
GARAGE_ATTRS = ["sessions", "totalSpots", "sensorFree", "sensorOccupied", "policy", "allowlist", "acceptThreshold",
                "freeMinutes", "pricePerHourCents", "dailyCapCents", "timeMultiplier", "lastPlateEntrance",
                "lastPlateExit", "manualPlate", "exitFuzzyMatch"]
# Messages that change the Garage asset (sessions, counts, summary, alarms) are processed one at a time:
# the device profiles put device messages into this queue (in order per device) and a checkpoint after
# "Na asset Garage" re-queues them with the Garage as originator, so they are serialised for the whole garage.
# The default queue "Main" processes messages in parallel, which can apply an older count after a newer one.
QUEUE = "SequentialByOriginator"
ALPR_RPC_TIMEOUT_S = 15   # ALPR takes up to 3 photos; no answer in time = unreadable plate -> operator
GATE_RPC_TIMEOUT_S = 5    # the gate must confirm a command, otherwise alarm "Rampa ne potvrđuje naredbe"


def script(name: str) -> str:
    with open(os.path.join(HERE, "scripts", name + ".tbel"), encoding="utf-8") as f:
        return f.read()


class Chain:
    def __init__(self) -> None:
        self.nodes: List[Dict[str, Any]] = []
        self.index: Dict[str, int] = {}
        self.connections: List[Dict[str, Any]] = []

    def node(self, key: str, clazz: str, name: str, config: Dict[str, Any], col: int, row: int,
             version: int = 0, queue: Any = None) -> str:
        self.index[key] = len(self.nodes)
        self.nodes.append({"type": PKG + clazz, "name": name, "debugSettings": None, "singletonMode": False,
                           "queueName": queue, "configurationVersion": version, "configuration": config,
                           "additionalInfo": {"description": "", "layoutX": 60 + col * 290, "layoutY": 60 + row * 90}})
        return key

    def link(self, frm: str, to: str, *types: str) -> None:
        for t in types:
            self.connections.append({"fromIndex": self.index[frm], "toIndex": self.index[to], "type": t})

    # --------------------------------------------------------------- node helpers
    def tbel(self, key, name, script_name, col, row):
        return self.node(key, "transform.TbTransformMsgNode", name,
                         {"scriptLang": "TBEL", "jsScript": "return {msg: msg, metadata: metadata, msgType: msgType};",
                          "tbelScript": script(script_name)}, col, row)

    def filter(self, key, name, expr, col, row):
        return self.node(key, "filter.TbJsFilterNode", name,
                         {"scriptLang": "TBEL", "jsScript": "return true;", "tbelScript": expr}, col, row)

    def switch(self, key, name, expr, col, row):
        return self.node(key, "filter.TbJsSwitchNode", name,
                         {"scriptLang": "TBEL", "jsScript": "return [];", "tbelScript": expr}, col, row)

    def to_entity(self, key, name, entity_type, pattern, col, row):
        return self.node(key, "transform.TbChangeOriginatorNode", name,
                         {"originatorSource": "ENTITY", "entityType": entity_type, "entityNamePattern": pattern,
                          "relationsQuery": {"direction": "FROM", "maxLevel": 1, "fetchLastLevelOnly": False,
                                             "filters": [{"relationType": "Contains", "entityTypes": [],
                                                          "negate": False}]}}, col, row)

    def checkpoint(self, key, name, col, row):
        return self.node(key, "flow.TbCheckpointNode", name, {"version": 0}, col, row, version=1, queue=QUEUE)

    def rpc(self, key, name, timeout_s, col, row):
        return self.node(key, "rpc.TbSendRPCRequestNode", name, {"timeoutInSeconds": timeout_s}, col, row)

    def alarm(self, key, name, alarm_type, severity, details, col, row, clear=False):
        details_script = "var details = {};\n" + details + "\nreturn details;"
        cfg = {"alarmType": alarm_type, "scriptLang": "TBEL", "alarmDetailsBuildTbel": details_script,
               "alarmDetailsBuildJs": "return {};"}
        if clear:
            return self.node(key, "action.TbClearAlarmNode", name, cfg, col, row)
        cfg.update(severity=severity, propagate=True, propagateToOwner=False, propagateToTenant=False,
                   useMessageAlarmData=False, overwriteAlarmDetails=True, dynamicSeverity=False, relationTypes=[])
        return self.node(key, "action.TbCreateAlarmNode", name, cfg, col, row)

    def export(self) -> Dict[str, Any]:
        return {
            "ruleChain": {"name": NAME, "type": "CORE", "firstRuleNodeId": None, "root": False, "debugMode": False,
                          "configuration": None,
                          "additionalInfo": {"description": "IoT Garaža, varijanta B: odluke, sesije, naplata i "
                                                            "alarmi. Generira SOFTWARE/thingsboard/rulechain/"
                                                            "build_rule_chain.py"}},
            "metadata": {"firstNodeIndex": 0, "nodes": self.nodes, "connections": self.connections,
                         "ruleChainConnections": None},
        }


def build() -> Dict[str, Any]:
    c = Chain()
    # ---------------------------------------------------------------- column 0-1: every message
    c.node("profile", "profile.TbDeviceProfileNode", "Pravila alarma profila",
           {"persistAlarmRulesState": False, "fetchAlarmRulesStateOnStart": False}, 0, 0, version=1)
    c.node("type", "filter.TbMsgTypeSwitchNode", "Vrsta poruke", {"version": 0}, 0, 2)
    c.node("save_ts", "telemetry.TbMsgTimeseriesNode", "Spremi telemetriju",
           {"defaultTTL": 0, "useServerTs": False, "processingSettings": {"type": "ON_EVERY_MESSAGE"}}, 1, 0, version=1)
    c.node("save_client", "telemetry.TbMsgAttributesNode", "Spremi atribute uređaja",
           {"processingSettings": {"type": "ON_EVERY_MESSAGE"}, "scope": "CLIENT_SCOPE", "notifyDevice": False,
            "sendAttributesUpdatedNotification": False, "updateAttributesOnlyOnValueChange": True}, 1, 1, version=3)
    c.node("save_server", "telemetry.TbMsgAttributesNode", "Spremi atribute garaže",
           {"processingSettings": {"type": "ON_EVERY_MESSAGE"}, "scope": "SERVER_SCOPE", "notifyDevice": False,
            "sendAttributesUpdatedNotification": False, "updateAttributesOnlyOnValueChange": False}, 4, 0, version=3)
    c.link("profile", "type", "Success")
    c.link("type", "save_ts", "Post telemetry")
    c.link("type", "save_client", "Post attributes")

    # ---------------------------------------------------------------- spot counts -> Garage summary
    c.filter("f_counts", "Brojevi mjesta?", "return msg.freeSpots != null && msg.occupiedSpots != null;", 1, 2)
    c.to_entity("to_garage_counts", "Na asset Garage", "ASSET", "Garage", 2, 2)
    c.checkpoint("cp_counts", "Red garaže (brojevi)", 2, 3)
    c.tbel("counts", "Brojevi senzora", "sensor_counts", 3, 2)
    c.node("summary_attrs", "metadata.TbGetAttributesNode", "Atributi garaže (sažetak)",
           {"fetchTo": "METADATA", "clientAttributeNames": [], "sharedAttributeNames": [],
            "serverAttributeNames": ["sessions", "totalSpots", "sensorFree", "sensorOccupied"],
            "latestTsKeyNames": [], "tellFailureIfAbsent": False, "getLatestValueWithTs": False}, 5, 0, version=1)
    c.tbel("summary", "Sažetak garaže", "summary", 5, 1)
    c.filter("f_full", "Garaža puna?", "return msg.full == true;", 5, 2)
    c.alarm("full_on", "Alarm: garaža puna", "Garaža puna", "WARNING",
            "details.message = 'Nema slobodnih mjesta';", 6, 2)
    c.alarm("full_off", "Ugasi: garaža puna", "Garaža puna", None, "", 6, 3, clear=True)
    c.link("type", "f_counts", "Post telemetry")
    c.link("f_counts", "to_garage_counts", "True")
    c.link("to_garage_counts", "cp_counts", "Success")
    c.link("cp_counts", "counts", "Success")
    c.link("counts", "save_server", "Success")
    c.link("save_server", "summary_attrs", "Success")
    c.link("summary_attrs", "summary", "Success")
    c.link("summary", "save_ts", "Success")
    c.link("summary", "f_full", "Success")
    c.link("f_full", "full_on", "True")
    c.link("f_full", "full_off", "False")

    # ---------------------------------------------------------------- vehicle at a gate -> ALPR
    c.filter("f_arrival", "Vozilo na rampi?",
             "return msg.vehicleArrived == true && "
             "(metadata.deviceName == 'EntranceGate' || metadata.deviceName == 'ExitGate');", 1, 4)
    c.tbel("alpr_req", "Zahtjev readPlate", "alpr_request", 1, 5)
    c.to_entity("to_alpr", "Na ALPR uređaj rampe", "DEVICE", "${alprDevice}", 1, 6)
    c.rpc("rpc_alpr", "RPC readPlate", ALPR_RPC_TIMEOUT_S, 1, 7)
    c.tbel("alpr_timeout", "ALPR ne odgovara", "alpr_timeout", 2, 7)
    c.link("type", "f_arrival", "Post telemetry")
    c.link("f_arrival", "alpr_req", "True")
    c.link("alpr_req", "to_alpr", "Success")
    c.link("to_alpr", "rpc_alpr", "Success")
    c.link("rpc_alpr", "alpr_timeout", "Failure")

    # ---------------------------------------------------------------- dashboard RPC to a gate
    c.switch("rpc_kind", "Ručna radnja?",
             "if (msg.method == 'approve' || msg.method == 'deny') { return ['manual']; }\nreturn ['device'];", 0, 4)
    c.rpc("rpc_device", "RPC uređaju", 10, 0, 5)
    c.node("origin_name", "metadata.TbGetOriginatorFieldsNode", "Ime rampe",
           {"fetchTo": "METADATA", "dataMapping": {"name": "originatorName"}, "ignoreNullStrings": False}, 0, 6,
           version=1)
    c.filter("f_gate", "Je li rampa?",
             "return metadata.originatorName == 'EntranceGate' || metadata.originatorName == 'ExitGate';", 0, 7)
    c.tbel("manual_req", "Ručno odobri / odbij", "manual_request", 0, 8)
    c.link("type", "rpc_kind", "RPC Request to Device")
    c.link("rpc_kind", "rpc_device", "device")
    c.link("rpc_kind", "origin_name", "manual")
    c.link("origin_name", "f_gate", "Success")
    c.link("f_gate", "manual_req", "True")

    # ---------------------------------------------------------------- decision (automatic and manual)
    c.to_entity("to_garage", "Na asset Garage (odluka)", "ASSET", "Garage", 2, 5)
    c.checkpoint("cp_decide", "Red garaže (odluka)", 2, 6)
    c.node("decide_attrs", "metadata.TbGetAttributesNode", "Atributi garaže (odluka)",
           {"fetchTo": "METADATA", "clientAttributeNames": [], "sharedAttributeNames": [],
            "serverAttributeNames": GARAGE_ATTRS, "latestTsKeyNames": [], "tellFailureIfAbsent": False,
            "getLatestValueWithTs": False}, 3, 5, version=1)
    c.tbel("decide", "Odluka, sesija, cijena", "decide", 3, 6)
    c.tbel("decision_attrs", "Sesije i zadnje registracije", "decision_attributes", 4, 1)
    c.filter("f_manual", "Treba operater?", "return msg.manualRequired == true;", 4, 6)
    c.alarm("manual_on", "Alarm: ručna intervencija", "Potrebna ručna intervencija", "WARNING",
            "details.plate = metadata.decisionPlate;\ndetails.reason = metadata.decisionReason;\n"
            "details.gate = metadata.gate;\n"
            "details.message = metadata.gate + ': ' + metadata.decisionPlate + ' (' + metadata.decisionReason + ')';",
            5, 6)
    c.alarm("manual_off", "Ugasi: ručna intervencija", "Potrebna ručna intervencija", None, "", 5, 7, clear=True)
    c.link("rpc_alpr", "to_garage", "Success")
    c.link("alpr_timeout", "to_garage", "Success")
    c.link("manual_req", "to_garage", "Success")
    c.link("to_garage", "cp_decide", "Success")
    c.link("cp_decide", "decide_attrs", "Success")
    c.link("decide_attrs", "decide", "Success")
    c.link("decide", "save_ts", "Success")
    c.link("decide", "decision_attrs", "Success")
    c.link("decision_attrs", "save_server", "Success")
    c.link("decide", "f_manual", "Success")
    c.link("f_manual", "manual_on", "True")
    c.link("f_manual", "manual_off", "False")

    # ---------------------------------------------------------------- command to the gate
    c.filter("f_cmd", "Naredba rampi?", "return metadata.openGate == 'true' || metadata.manual == 'true';", 3, 7)
    c.to_entity("to_gate", "Na rampu", "DEVICE", "${gateDevice}", 3, 8)
    c.tbel("gate_cmd", "RPC open / deny", "gate_command", 3, 9)
    c.rpc("rpc_gate", "RPC rampi", GATE_RPC_TIMEOUT_S, 3, 10)
    c.tbel("gate_ack", "Rampa potvrdila", "gate_ack", 4, 9)
    c.tbel("gate_no_ack", "Rampa ne odgovara", "gate_no_ack", 4, 10)
    c.alarm("ack_off", "Ugasi: rampa ne potvrđuje", "Rampa ne potvrđuje naredbe", None, "", 5, 9, clear=True)
    c.alarm("ack_on", "Alarm: rampa ne potvrđuje", "Rampa ne potvrđuje naredbe", "MAJOR",
            "details.message = metadata.gateDevice + ' nije potvrdila naredbu';", 5, 10)
    c.link("decide", "f_cmd", "Success")
    c.link("f_cmd", "to_gate", "True")
    c.link("to_gate", "gate_cmd", "Success")
    c.link("gate_cmd", "rpc_gate", "Success")
    c.link("rpc_gate", "gate_ack", "Success")
    c.link("rpc_gate", "gate_no_ack", "Failure")
    c.link("gate_ack", "save_ts", "Success")
    c.link("gate_ack", "ack_off", "Success")
    c.link("gate_no_ack", "save_ts", "Success")
    c.link("gate_no_ack", "ack_on", "Success")

    # ---------------------------------------------------------------- connect / disconnect
    c.switch("lost_kind", "Veza izgubljena: tko?", "return [metadata.deviceType];", 6, 4)
    c.switch("back_kind", "Veza uspostavljena: tko?", "return [metadata.deviceType];", 6, 0)
    c.tbel("spot_offline", "Mjesto UNKNOWN / OFFLINE", "spot_offline", 7, 4)
    c.tbel("node_offline", "online = false", "node_offline", 7, 5)
    c.tbel("node_online", "online = true", "node_online", 7, 0)
    c.alarm("offline_on", "Alarm: uređaj nije dostupan", "Uređaj nije dostupan", "MAJOR",
            "details.message = metadata.deviceName + ' se ne javlja';", 7, 6)
    c.alarm("offline_off", "Ugasi: uređaj nije dostupan", "Uređaj nije dostupan", None, "", 7, 1, clear=True)
    c.filter("f_spots_node", "Čvor senzora?", "return metadata.deviceName == 'esp32-spots';", 6, 6)
    c.tbel("sensors_lost", "Nema slobodnih (nepoznato)", "sensors_lost", 6, 7)
    for t in ("Disconnect Event", "Inactivity Event"):
        c.link("type", "lost_kind", t)
    for t in ("Connect Event", "Activity Event"):
        c.link("type", "back_kind", t)
    c.link("lost_kind", "spot_offline", "ParkingSpot")
    c.link("lost_kind", "node_offline", "Controller")
    c.link("spot_offline", "save_ts", "Success")
    c.link("node_offline", "save_ts", "Success")
    c.link("node_offline", "offline_on", "Success")
    c.link("node_offline", "f_spots_node", "Success")
    c.link("f_spots_node", "sensors_lost", "True")
    c.link("sensors_lost", "to_garage_counts", "Success")
    c.link("back_kind", "node_online", "Controller")
    c.link("node_online", "save_ts", "Success")
    c.link("node_online", "offline_off", "Success")
    return c.export()


def main() -> int:
    chain = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(chain, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s (%d nodes, %d connections)" % (OUT, len(chain["metadata"]["nodes"]),
                                                   len(chain["metadata"]["connections"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
