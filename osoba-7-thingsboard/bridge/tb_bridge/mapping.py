"""How local garage/# messages become ThingsBoard devices and telemetry.

ThingsBoard CE has no generic MQTT integration (that is a PE feature), so the
bridge talks to ThingsBoard as a *gateway device* ("Garage-Edge") using the
Gateway MQTT API: one connection carries the data of all garage devices.

    local topic                          ThingsBoard device (type)
    garage/parking/spot/P01/telemetry -> ParkingSpot-01 (ParkingSpot)
    garage/gate/entrance/state        -> EntranceGate   (Gate)
    garage/alpr/entrance/event        -> ALPR-Entrance  (ALPR)
    garage/summary, access/decision,
    session/event, system/alert       -> Garage-Edge    (GarageEdge, the gateway itself)
    garage/system/heartbeat|status    -> <deviceId>     (Controller), e.g. esp32-spots
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from garage_contract import topics
from garage_contract.timeutil import parse_iso, to_epoch_ms

GATEWAY_NAME = "Garage-Edge"
GATE_DEVICES = {"entrance": "EntranceGate", "exit": "ExitGate"}
ALPR_DEVICES = {"entrance": "ALPR-Entrance", "exit": "ALPR-Exit"}
GATE_STATE_CODE = {"CLOSED": 0, "OPENING": 1, "OPEN": 2, "CLOSING": 3, "ERROR": 4}
SPOT_STATE_CODE = {"FREE": 0, "OCCUPIED": 1, "UNKNOWN": -1}

# (device name or None for the gateway itself, device type, telemetry values)
Record = Tuple[Optional[str], str, Dict[str, Any]]


def spot_device(spot_id: str) -> str:
    return "ParkingSpot-" + spot_id[1:]


def _ts(msg: Dict[str, Any], now_ms: int) -> int:
    ts = msg.get("timestamp")
    if ts:
        try:
            return to_epoch_ms(parse_iso(ts))
        except ValueError:
            pass
    return now_ms


class Mapper:
    def __init__(self) -> None:
        self.spot_owner: Dict[str, str] = {}   # spot -> deviceId of the sensor node

    def map(self, topic: str, msg: Dict[str, Any], now_ms: int) -> List[Tuple[Optional[str], str, int, Dict[str, Any]]]:
        """Return [(device or None=gateway, type, ts_ms, values)]."""
        ts = _ts(msg, now_ms)
        out: List[Tuple[Optional[str], str, int, Dict[str, Any]]] = []
        parts = topic.split("/")

        if topic.startswith("garage/parking/spot/") and topic.endswith("/telemetry"):
            spot = msg.get("spotId") or parts[3]
            if msg.get("deviceId"):
                self.spot_owner[spot] = msg["deviceId"]
            out.append((spot_device(spot), "ParkingSpot", ts, {
                "state": msg.get("state"), "stateCode": SPOT_STATE_CODE.get(msg.get("state"), -1),
                "occupied": msg.get("occupied"), "distanceCm": msg.get("distanceCm"),
                "sensorStatus": msg.get("sensorStatus"),
            }))

        elif parts[:2] == ["garage", "gate"] and parts[-1] == "state" and parts[2] in GATE_DEVICES:
            values = {"state": msg.get("state"), "stateCode": GATE_STATE_CODE.get(msg.get("state"), -1),
                      "vehiclePresent": msg.get("vehiclePresent"), "lastSource": msg.get("source")}
            if msg.get("requestId"):
                values.update(lastRequestId=msg["requestId"], lastCommandSuccess=msg.get("success"),
                              lastCommandReason=msg.get("reason"))
                if msg.get("success"):
                    values["ackTimeout"] = False
            out.append((GATE_DEVICES[parts[2]], "Gate", ts, values))

        elif parts[:2] == ["garage", "alpr"] and parts[-1] == "event" and parts[2] in ALPR_DEVICES:
            out.append((ALPR_DEVICES[parts[2]], "ALPR", ts, {
                "plate": msg.get("plate") or "-", "status": msg.get("status"),
                "ocrConfidence": msg.get("ocrConfidence"), "detectionConfidence": msg.get("detectionConfidence"),
                "accepted": msg.get("accepted"), "processingMs": msg.get("processingMs"),
                "consecutiveFailures": msg.get("consecutiveFailures", 0),
            }))

        elif topic == topics.GARAGE_SUMMARY:
            out.append((None, "GarageEdge", ts, {k: msg.get(k) for k in (
                "totalSpots", "freeSpots", "occupiedSpots", "unknownSpots", "occupancyPct", "activeSessions", "full")}))

        elif topic == topics.ACCESS_DECISION:
            out.append((None, "GarageEdge", ts, {
                "decision": msg.get("decision"), "decisionReason": msg.get("reason"),
                "decisionPlate": msg.get("plate") or "-", "decisionDirection": msg.get("direction"),
                "decisionConfidence": msg.get("confidence"), "decisionManual": msg.get("manual"),
                "decisionOperator": msg.get("operator") or "",
                "manualRequired": msg.get("decision") == "MANUAL_REQUIRED",
            }))

        elif topic == topics.SESSION_EVENT:
            values: Dict[str, Any] = {"sessionEvent": msg.get("eventType"), "sessionPlate": msg.get("plate"),
                                      "sessionId": msg.get("sessionId")}
            if msg.get("eventType") == "SESSION_OPENED":
                values["entry"] = 1
            elif msg.get("eventType") == "SESSION_CLOSED":
                values.update(exit=1, durationMin=round((msg.get("durationS") or 0) / 60.0, 1),
                              price=msg.get("price"), sessionEntryTime=msg.get("entryTime"))
            out.append((None, "GarageEdge", ts, values))

        elif topic == topics.SYSTEM_ALERT:
            active = bool(msg.get("active"))
            kind = msg.get("type", "")
            gate = (msg.get("gate") or "").lower()
            if kind == "GATE_NO_ACK" and gate in GATE_DEVICES:
                out.append((GATE_DEVICES[gate], "Gate", ts, {"ackTimeout": active}))
            elif kind == "ALPR_REPEATED_FAILURE" and gate in ALPR_DEVICES:
                out.append((ALPR_DEVICES[gate], "ALPR", ts, {"alprFailing": active}))
            out.append((None, "GarageEdge", ts, {"alert_" + kind: active, "lastAlert": msg.get("message", kind)}))

        elif topic == topics.HEARTBEAT and msg.get("deviceId"):
            out.append((msg["deviceId"], "Controller", ts, _heartbeat_values(msg)))

        elif topic.startswith("garage/system/status/"):
            device = msg.get("deviceId") or parts[3]
            online = bool(msg.get("online"))
            out.append((device, "Controller", ts, {"online": online}))
            if not online:  # sensor node gone: its spots are UNKNOWN, never "free"
                for spot, owner in self.spot_owner.items():
                    if owner == device:
                        out.append((spot_device(spot), "ParkingSpot", ts, {
                            "state": "UNKNOWN", "stateCode": -1, "occupied": None, "sensorStatus": "OFFLINE"}))
        return out


def _heartbeat_values(msg: Dict[str, Any]) -> Dict[str, Any]:
    values = {k: msg.get(k) for k in ("uptimeS", "rssi", "freeHeap", "fwVersion", "ip", "deviceType")}
    values["online"] = True
    return values
