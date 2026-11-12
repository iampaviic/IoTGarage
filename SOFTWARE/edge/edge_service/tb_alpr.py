"""Varijanta B: the ALPR service as a ThingsBoard device.

    python -m edge_service --config edge.yaml tb-alpr              # camera
    ALPR_SOURCE=sim python -m edge_service tb-alpr                 # synthetic frames, no camera

The service connects to ThingsBoard as the gateway device "alpr-service" (access token from
edge.yaml `thingsboard.token` or TB_TOKEN_ALPR) and speaks for ALPR-Entrance and ALPR-Exit.

    rule chain --RPC readPlate {"gate": "ENTRANCE"}--> ALPR-Entrance
        up to frames_per_trigger photos: detection -> OCR -> voting (the best reading wins)
    ALPR-Entrance telemetry: plate, status, ocrConfidence, detectionConfidence, accepted, processingMs,
                             consecutiveFailures, alprFailing
    answer to the RPC:       {"status", "plate", "ocrConfidence", "detectionConfidence", "accepted", ...}

The service only reports what it read and how sure it is; the rule chain decides.
With ALPR_SOURCE=sim the simulation puts a plate in front of a camera with the RPC
simVehicle {"gate": "ENTRANCE", "plate": "ZG1234AB", "quality": "good"} to alpr-service.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Any, Dict, Optional

from garage_contract.tb import ALPR_DEVICES, ALPR_GATEWAY, TbGateway, TbSettings

from edge_service.alpr_service import AlprService, CameraSource, FrameSource, ImageFolderSource, SimCameraSource
from edge_service.config import EdgeConfig

log = logging.getLogger(__name__)
GATE_KEYS = {"ENTRANCE": "entrance", "EXIT": "exit"}   # ThingsBoard gate name -> edge.yaml gate


class TbAlprService:
    def __init__(self, cfg: EdgeConfig, source: FrameSource, gateway: Optional[TbGateway] = None,
                 service: Optional[AlprService] = None) -> None:
        self.cfg = cfg
        self.source = source
        self.service = service or AlprService(cfg, source, publish=lambda *a: None)
        settings = TbSettings(cfg.thingsboard.host, cfg.thingsboard.port, cfg.thingsboard.token)
        self.gw = gateway or TbGateway(ALPR_GATEWAY, settings, {d: "ALPR" for d in ALPR_DEVICES.values()})
        self.gw.on_device_rpc = self.on_device_rpc
        self.gw.on_rpc = self.on_rpc
        self.gw.on_connect = self.on_connect
        self._busy = threading.Lock()     # one reading at a time: the camera can be shared
        self._seq = 0

    def on_connect(self) -> None:
        self.gw.attributes({"alprSource": self.cfg.alpr.source, "engines": ", ".join(self.service.reader.engine_names)})
        self.gw.telemetry({"uptimeS": int(time.monotonic())})

    def read_plate(self, gate: str) -> Dict[str, Any]:
        """gate = ENTRANCE | EXIT. Returns the answer for the rule chain and publishes the telemetry."""
        key = GATE_KEYS.get(str(gate).upper())
        if key is None or key not in self.cfg.alpr.gates:
            return {"status": "CAMERA_ERROR", "ocrConfidence": 0.0, "accepted": False, "error": "unknown gate"}
        with self._busy:
            self._seq += 1
            event = self.service.process(key, "tb-%s-%d" % (key, self._seq))
        failing = event["consecutiveFailures"] >= self.cfg.access.alpr_failure_alert_after
        values = {k: event.get(k) for k in ("status", "ocrConfidence", "detectionConfidence", "accepted",
                                            "processingMs", "consecutiveFailures")}
        values.update(plate=event.get("plate") or "-", alprFailing=failing)
        self.gw.device_telemetry(ALPR_DEVICES[str(gate).upper()], values)
        log.info("%s: %s %s conf=%.2f (%d ms)", gate, event["status"], event.get("plate") or "-",
                 event["ocrConfidence"], event["processingMs"])
        answer = {k: event.get(k) for k in ("status", "plate", "rawText", "ocrConfidence", "detectionConfidence",
                                            "accepted", "processingMs", "consecutiveFailures", "timestamp")}
        answer["gate"] = str(gate).upper()
        return answer

    # ------------------------------------------------------------- RPC
    def on_device_rpc(self, device: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gate = {v: k for k, v in ALPR_DEVICES.items()}.get(device)
        if method == "readPlate" and gate:
            return self.read_plate(params.get("gate") or gate)
        return None

    def on_rpc(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """RPC to alpr-service itself; simVehicle only with ALPR_SOURCE=sim."""
        if method == "simVehicle" and isinstance(self.source, SimCameraSource):
            key = GATE_KEYS.get(str(params.get("gate", "")).upper())
            if key is None:
                return {"success": False, "reason": "unknown gate"}
            self.source.on_sim_vehicle("garage/sim/vehicle/" + key,
                                       {"plate": params.get("plate"), "quality": params.get("quality", "good")})
            return {"success": True}
        return None


def make_source(cfg: EdgeConfig) -> FrameSource:
    if cfg.alpr.source == "sim":
        return SimCameraSource(rois={g: gc.roi for g, gc in cfg.alpr.gates.items()})
    if cfg.alpr.source == "images":
        if not cfg.alpr.images_dir:
            raise ValueError("alpr.images_dir is required for source=images")
        return ImageFolderSource(cfg.alpr.images_dir)
    return CameraSource(cfg)


def run(cfg: EdgeConfig) -> None:
    source = make_source(cfg)
    svc = TbAlprService(cfg, source)
    log.info("ALPR (varijanta B): source=%s, ThingsBoard %s:%s, engines=%s", cfg.alpr.source,
             cfg.thingsboard.host, cfg.thingsboard.port, svc.service.reader.engine_names)
    removed = svc.service.purge_crops()
    if removed:
        log.info("privacy: deleted %d old plate crops", removed)
    if not svc.gw.start():
        log.warning("ThingsBoard not reachable yet, retrying in the background")
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *a: stop.set())
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    started = time.monotonic()
    while not stop.wait(30):   # heartbeat; the rule chain marks the device offline when it stops
        if svc.gw.connected.is_set():
            svc.gw.telemetry({"uptimeS": int(time.monotonic() - started)})
    log.info("stopping")
    source.close()
    svc.gw.stop()
