"""ALPR as a ThingsBoard device (varijanta B), without network: a fake gateway records what is sent."""


from edge_service.config import EdgeConfig
from edge_service.tb_alpr import TbAlprService
from garage_contract.tb import ALPR_DEVICES


class FakeGateway:
    def __init__(self):
        self.telemetry_sent = []

    def device_telemetry(self, device, values, ts=None):
        self.telemetry_sent.append((device, values))
        return True

    def telemetry(self, values, ts=None):
        return True

    def attributes(self, values):
        return True


class FakeService:
    """Stands in for AlprService: returns a prepared reading."""

    def __init__(self, event):
        self.event = event
        self.reader = type("R", (), {"engine_names": ["fake"]})()
        self.calls = []

    def process(self, gate, request_id):
        self.calls.append(gate)
        return dict(self.event)


def reading(plate="ZG1234AB", conf=0.93, failures=0):
    return {"requestId": "x", "cameraId": "c", "direction": "ENTRY", "status": "OK" if plate else "NO_PLATE",
            "plate": plate, "rawText": plate, "detectionConfidence": 0.9, "ocrConfidence": conf,
            "accepted": conf >= 0.85, "processingMs": 400, "consecutiveFailures": failures,
            "timestamp": "2026-10-19T08:31:12Z"}


def make(event):
    gw = FakeGateway()
    svc = TbAlprService(EdgeConfig(), source=None, gateway=gw, service=FakeService(event))
    return svc, gw


def test_read_plate_rpc_answers_and_publishes_telemetry():
    svc, gw = make(reading())
    answer = svc.on_device_rpc(ALPR_DEVICES["ENTRANCE"], "readPlate", {"gate": "ENTRANCE"})
    assert answer["plate"] == "ZG1234AB" and answer["ocrConfidence"] == 0.93 and answer["gate"] == "ENTRANCE"
    assert svc.service.calls == ["entrance"]
    device, values = gw.telemetry_sent[-1]
    assert device == "ALPR-Entrance" and values["plate"] == "ZG1234AB" and values["alprFailing"] is False


def test_repeated_failures_raise_alpr_failing():
    svc, gw = make(reading(plate=None, conf=0.0, failures=3))
    answer = svc.on_device_rpc(ALPR_DEVICES["EXIT"], "readPlate", {})
    assert answer["status"] == "NO_PLATE" and svc.service.calls == ["exit"]
    assert gw.telemetry_sent[-1][1]["alprFailing"] is True and gw.telemetry_sent[-1][1]["plate"] == "-"


def test_unknown_method_and_device_are_not_handled():
    svc, _ = make(reading())
    assert svc.on_device_rpc("ALPR-Entrance", "reboot", {}) is None
    assert svc.on_device_rpc("EntranceGate", "readPlate", {}) is None
    assert svc.on_rpc("simVehicle", {"gate": "ENTRANCE", "plate": "ZG1234AB"}) is None  # not a sim camera
