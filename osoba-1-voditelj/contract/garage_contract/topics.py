"""MQTT topic names (contract version 1.0).

Conventions:
- spot ids are "P01".."P06" in both topics and payloads
- gate names are lowercase in topics ("entrance", "exit") and uppercase in
  payloads ("ENTRANCE", "EXIT")
- all payloads are UTF-8 JSON objects, QoS 1
- RETAINED topics always hold the latest state; commands and events are never
  retained
"""

ROOT = "garage"

GATES = ("entrance", "exit")
GATE_TO_PAYLOAD = {"entrance": "ENTRANCE", "exit": "EXIT"}
GATE_TO_DIRECTION = {"entrance": "ENTRY", "exit": "EXIT"}
DIRECTION_TO_GATE = {"ENTRY": "entrance", "EXIT": "exit"}

# --- parking spots (owner: osoba 3) -------------------------------------
SPOT_TELEMETRY = "garage/parking/spot/{spot_id}/telemetry"  # retained
SPOT_TELEMETRY_ALL = "garage/parking/spot/+/telemetry"

# --- gates (owner: osoba 4) ----------------------------------------------
GATE_COMMAND = "garage/gate/{gate}/command"
GATE_COMMAND_ALL = "garage/gate/+/command"
GATE_STATE = "garage/gate/{gate}/state"  # retained
GATE_STATE_ALL = "garage/gate/+/state"

# --- ALPR (owners: osoba 5 + 6) -------------------------------------------
ALPR_TRIGGER = "garage/alpr/{gate}/trigger"
ALPR_TRIGGER_ALL = "garage/alpr/+/trigger"
ALPR_EVENT = "garage/alpr/{gate}/event"
ALPR_EVENT_ALL = "garage/alpr/+/event"

# --- access control and sessions (owners: osoba 6 + 8) --------------------
ACCESS_DECISION = "garage/access/decision"
ACCESS_MANUAL = "garage/access/manual"
SESSION_EVENT = "garage/session/event"
GARAGE_SUMMARY = "garage/summary"  # retained

# --- system ----------------------------------------------------------------
HEARTBEAT = "garage/system/heartbeat"
DEVICE_STATUS = "garage/system/status/{device_id}"  # retained, used as LWT
DEVICE_STATUS_ALL = "garage/system/status/+"
SYSTEM_ALERT = "garage/system/alert"

# --- simulation only (never used by production logic) ----------------------
SIM_SPOT = "garage/sim/spot/{spot_id}"
SIM_SPOT_ALL = "garage/sim/spot/+"
SIM_GATE_PRESENCE = "garage/sim/gate/{gate}/presence"
SIM_GATE_PRESENCE_ALL = "garage/sim/gate/+/presence"
SIM_VEHICLE = "garage/sim/vehicle/{gate}"  # retained: plate currently in front of camera
SIM_VEHICLE_ALL = "garage/sim/vehicle/+"

ALL = "garage/#"

RETAINED = (
    SPOT_TELEMETRY_ALL,
    GATE_STATE_ALL,
    GARAGE_SUMMARY,
    DEVICE_STATUS_ALL,
    SIM_VEHICLE_ALL,
)


def spot_telemetry(spot_id: str) -> str:
    return SPOT_TELEMETRY.format(spot_id=spot_id)


def gate_command(gate: str) -> str:
    return GATE_COMMAND.format(gate=_gate(gate))


def gate_state(gate: str) -> str:
    return GATE_STATE.format(gate=_gate(gate))


def alpr_trigger(gate: str) -> str:
    return ALPR_TRIGGER.format(gate=_gate(gate))


def alpr_event(gate: str) -> str:
    return ALPR_EVENT.format(gate=_gate(gate))


def device_status(device_id: str) -> str:
    return DEVICE_STATUS.format(device_id=device_id)


def sim_spot(spot_id: str) -> str:
    return SIM_SPOT.format(spot_id=spot_id)


def sim_gate_presence(gate: str) -> str:
    return SIM_GATE_PRESENCE.format(gate=_gate(gate))


def sim_vehicle(gate: str) -> str:
    return SIM_VEHICLE.format(gate=_gate(gate))


def segment(topic: str, index: int) -> str:
    """Return one '/'-separated part of a topic, e.g. segment(t, 3) -> 'P01'."""
    return topic.split("/")[index]


def _gate(gate: str) -> str:
    g = gate.lower()
    if g not in GATES:
        raise ValueError("unknown gate %r (expected one of %s)" % (gate, GATES))
    return g
