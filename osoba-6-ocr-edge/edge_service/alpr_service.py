"""ALPR service: on every trigger take frames, find the plate, read it, publish.

    garage/alpr/<gate>/trigger  ->  capture -> PlateDetector (osoba 5) -> PlateReader (osoba 6)
                                ->  garage/alpr/<gate>/event

Frame sources
  camera  USB camera(s); one shared camera can serve both gates with a ROI each
  sim     synthetic frames of the plate announced on garage/sim/vehicle/<gate>
  images  cycle through stored photos (test the pipeline on the dataset)

The service only reports what it read and how sure it is. Whether the gate
opens is decided by access control.
"""

from __future__ import annotations

import glob
import itertools
import logging
import os
import random
import threading
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np

from garage_contract import topics
from garage_contract.timeutil import utc_now_iso
from plate_detector import PlateDetector
from plate_ocr import PlateReader
from plate_ocr.reader import OcrConfig

from edge_service.config import EdgeConfig

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ sources
class FrameSource:
    def frame(self, gate: str) -> np.ndarray:
        raise NotImplementedError

    def close(self) -> None:
        pass


class CameraSource(FrameSource):
    def __init__(self, cfg: EdgeConfig) -> None:
        from plate_detector.camera import Camera

        self.cameras: Dict[str, Any] = {}
        shared = None
        for gate, gc in cfg.alpr.gates.items():
            if gc.camera is not None:
                self.cameras[gate] = Camera(gc.camera, cfg.alpr.width, cfg.alpr.height).start()
            else:
                shared = shared or Camera(cfg.alpr.camera, cfg.alpr.width, cfg.alpr.height).start()
                self.cameras[gate] = shared

    def frame(self, gate: str) -> np.ndarray:
        return self.cameras[gate].read_latest()

    def close(self) -> None:
        for cam in set(self.cameras.values()):
            cam.stop()


class ImageFolderSource(FrameSource):
    def __init__(self, folder: str) -> None:
        files = sorted(f for ext in ("*.jpg", "*.jpeg", "*.png") for f in glob.glob(os.path.join(folder, "**", ext), recursive=True))
        if not files:
            raise FileNotFoundError("no images in %s" % folder)
        self._it = itertools.cycle(files)

    def frame(self, gate: str) -> np.ndarray:
        path = next(self._it)
        log.info("using image %s", path)
        img = cv2.imread(path)
        if img is None:
            raise IOError("cannot read %s" % path)
        return img


class SimCameraSource(FrameSource):
    """Renders a synthetic frame for the plate that the simulator put in front of the gate.
    Like the real fixed camera, the plate appears inside that gate's ROI."""

    def __init__(self, seed: Optional[int] = None, rois: Optional[Dict[str, Any]] = None) -> None:
        self.rois = rois or {}
        self.vehicles: Dict[str, Dict[str, Any]] = {}
        self.rng = random.Random(seed)
        self._lock = threading.Lock()

    def on_sim_vehicle(self, topic: str, msg: Dict[str, Any]) -> None:
        with self._lock:
            self.vehicles[topics.segment(topic, 3)] = msg or {}

    def frame(self, gate: str) -> np.ndarray:
        from plate_detector.synth import SceneParams, render_scene

        with self._lock:
            v = dict(self.vehicles.get(gate) or {})
        plate = v.get("plate")
        params = SceneParams.fixed_camera(self.rois.get(gate))
        if not plate:
            return render_scene(rng=self.rng, params=params, with_plate=False).image
        return render_scene(plate=plate, rng=self.rng, params=params, quality=v.get("quality", "good")).image


# ------------------------------------------------------------------ service
class AlprService:
    def __init__(self, cfg: EdgeConfig, source: FrameSource, publish, reader: Optional[PlateReader] = None,
                 detector: Optional[PlateDetector] = None) -> None:
        self.cfg = cfg
        self.source = source
        self.publish = publish
        self.detector = detector or PlateDetector()
        self.reader = reader or PlateReader(OcrConfig(accept_threshold=cfg.access.accept_threshold,
                                                      retry_threshold=cfg.access.retry_threshold))
        self.failures = {g: 0 for g in cfg.alpr.gates}
        self._busy = threading.Lock()

    def on_trigger(self, topic: str, msg: Dict[str, Any]) -> None:
        gate = topics.segment(topic, 2)
        if gate not in self.cfg.alpr.gates:
            log.warning("trigger for unknown gate %s", gate)
            return
        with self._busy:  # one reading at a time; the camera is shared
            event = self.process(gate, (msg or {}).get("requestId") or "manual-%d" % int(time.time()))
        self.publish(topics.alpr_event(gate), event, False)

    def process(self, gate: str, request_id: str) -> Dict[str, Any]:
        """Take up to N frames and return the best reading as an alpr_event payload."""
        t0 = time.perf_counter()
        gc = self.cfg.alpr.gates[gate]
        best = None  # (ocr confidence, detection, ocr result)
        status = "NO_PLATE"
        best_det_conf = 0.0
        for _ in range(max(1, self.cfg.alpr.frames_per_trigger)):
            try:
                frame = self.source.frame(gate)
            except Exception as e:
                log.error("camera error on %s: %s", gate, e)
                status = "CAMERA_ERROR"
                continue
            det = self.detector.detect(frame, roi=gc.roi)
            best_det_conf = max(best_det_conf, det.confidence)
            if not det.found:
                continue
            ocr = self.reader.read(det.crop, det.variants)
            if best is None or ocr.confidence > best[0]:
                best = (ocr.confidence, det, ocr)
            if ocr.accepted:
                break  # good enough, do not keep the driver waiting
        ms = int((time.perf_counter() - t0) * 1000)

        if best is None:
            plate, raw, ocr_conf, det_conf, accepted = None, None, 0.0, best_det_conf, False
        else:
            _, det, ocr = best
            plate, raw, ocr_conf, det_conf, accepted = ocr.plate, ocr.raw_text, ocr.confidence, det.confidence, ocr.accepted
            status = ocr.status if ocr.plate or ocr.status != "NO_TEXT" else "NO_PLATE"
            if self.cfg.privacy.save_crops:
                self._save_crop(gate, request_id, det.crop)
        self.failures[gate] = 0 if accepted else self.failures[gate] + 1
        return {
            "requestId": request_id,
            "cameraId": gc.camera_id,
            "direction": topics.GATE_TO_DIRECTION[gate],
            "status": status,
            "plate": plate,
            "rawText": raw,
            "detectionConfidence": round(float(det_conf), 3),
            "ocrConfidence": round(float(ocr_conf), 3),
            "accepted": bool(accepted),
            "processingMs": ms,
            "consecutiveFailures": self.failures[gate],
            "timestamp": utc_now_iso(),
        }

    def _save_crop(self, gate: str, request_id: str, crop: np.ndarray) -> None:
        """Privacy: only the plate crop is stored, never the full frame; purge_crops() deletes old ones."""
        os.makedirs(self.cfg.privacy.crops_dir, exist_ok=True)
        cv2.imwrite(os.path.join(self.cfg.privacy.crops_dir, "%s_%s.jpg" % (gate, request_id)), crop)

    def purge_crops(self) -> int:
        folder = self.cfg.privacy.crops_dir
        if not os.path.isdir(folder):
            return 0
        cutoff = time.time() - self.cfg.privacy.retention_days * 86400
        n = 0
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
                n += 1
        return n
