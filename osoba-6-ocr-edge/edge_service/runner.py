"""Wiring: MQTT <-> AccessController / AlprService, run on the edge computer.

    python -m edge_service --config edge.yaml all       # access control + ALPR in one process
    python -m edge_service --config edge.yaml access    # only access control
    python -m edge_service --config edge.yaml alpr      # only ALPR (e.g. on the Jetson next to the camera)
"""

from __future__ import annotations

import logging
import queue
import signal
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from garage_contract import GarageConfig, topics
from garage_contract.mqtt import MqttConnection
from parking_sessions import PricingPolicy, SessionStore

from edge_service.access_control import AccessController
from edge_service.alpr_service import AlprService, CameraSource, ImageFolderSource, SimCameraSource
from edge_service.config import EdgeConfig

log = logging.getLogger(__name__)


class EventLoop:
    """Serialises MQTT callbacks (paho network thread) onto one worker thread."""

    def __init__(self, tick: Optional[Callable[[], None]] = None, tick_s: float = 0.2) -> None:
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.tick = tick
        self.tick_s = tick_s
        self.stopped = threading.Event()

    def wrap(self, handler: Callable[[str, Any], None]) -> Callable[[str, Any], None]:
        return lambda topic, payload: self.q.put((handler, topic, payload))

    def run(self) -> None:
        next_tick = time.monotonic()
        while not self.stopped.is_set():
            timeout = max(0.0, next_tick - time.monotonic())
            try:
                handler, topic, payload = self.q.get(timeout=timeout)
                try:
                    handler(topic, payload if isinstance(payload, dict) else {})
                except Exception:
                    log.exception("handler failed for %s", topic)
            except queue.Empty:
                pass
            if time.monotonic() >= next_tick:
                if self.tick:
                    try:
                        self.tick()
                    except Exception:
                        log.exception("tick failed")
                next_tick = time.monotonic() + self.tick_s


def build_access(cfg: EdgeConfig) -> tuple:
    garage = GarageConfig(spot_count=cfg.spots)
    pricing = PricingPolicy.demo() if cfg.pricing == "demo" else PricingPolicy.real()
    store = SessionStore(cfg.database, pricing)
    conn = MqttConnection("access-control", cfg.mqtt, device_id="access-control", device_type="ACCESS_CONTROL")
    ctrl = AccessController(store, lambda t, p, r=False: conn.publish_json(t, p, retain=r), garage.spots, cfg.access)
    loop = EventLoop(tick=ctrl.tick)
    conn.subscribe(topics.SPOT_TELEMETRY_ALL, loop.wrap(ctrl.on_spot))
    conn.subscribe(topics.GATE_STATE_ALL, loop.wrap(ctrl.on_gate_state))
    conn.subscribe(topics.ALPR_EVENT_ALL, loop.wrap(ctrl.on_alpr_event))
    conn.subscribe(topics.ACCESS_MANUAL, loop.wrap(ctrl.on_manual))
    conn.subscribe(topics.DEVICE_STATUS_ALL, loop.wrap(ctrl.on_device_status))
    return conn, ctrl, loop


def build_alpr(cfg: EdgeConfig) -> tuple:
    conn = MqttConnection("alpr-service", cfg.mqtt, device_id="alpr-service", device_type="ALPR")
    if cfg.alpr.source == "sim":
        source = SimCameraSource(rois={g: gc.roi for g, gc in cfg.alpr.gates.items()})
        conn.subscribe(topics.SIM_VEHICLE_ALL, source.on_sim_vehicle)
    elif cfg.alpr.source == "images":
        if not cfg.alpr.images_dir:
            raise ValueError("alpr.images_dir is required for source=images")
        source = ImageFolderSource(cfg.alpr.images_dir)
    else:
        source = CameraSource(cfg)
    service = AlprService(cfg, source, lambda t, p, r=False: conn.publish_json(t, p, retain=r))
    # ALPR work is slow (~0.5-2 s): run it on its own thread, never on the MQTT thread
    loop = EventLoop()
    conn.subscribe(topics.ALPR_TRIGGER_ALL, loop.wrap(service.on_trigger))
    return conn, service, loop, source


def run(cfg: EdgeConfig, parts: List[str]) -> None:
    conns: List[MqttConnection] = []
    loops: List[EventLoop] = []
    sources = []
    if "access" in parts:
        conn, ctrl, loop = build_access(cfg)
        conns.append(conn)
        loops.append(loop)
        log.info("access control: %d spots, policy=%s, pricing=%s, db=%s",
                 len(ctrl.spots), cfg.access.policy, cfg.pricing, cfg.database)
    if "alpr" in parts:
        conn, service, loop, source = build_alpr(cfg)
        conns.append(conn)
        loops.append(loop)
        sources.append(source)
        log.info("ALPR: source=%s, gates=%s, engines=%s", cfg.alpr.source, list(cfg.alpr.gates),
                 service.reader.engine_names)
        removed = service.purge_crops()
        if removed:
            log.info("privacy: deleted %d old plate crops", removed)

    for c in conns:
        c.start()
    threads = [threading.Thread(target=lp.run, daemon=True) for lp in loops]
    for t in threads:
        t.start()

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *a: stop.set())
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    if "access" in parts:
        # first summary once retained spot states had a moment to arrive
        time.sleep(1.0)
        loops[0].q.put((lambda t, p: ctrl.publish_summary(force=True), "", {}))
    stop.wait()
    log.info("stopping")
    for lp in loops:
        lp.stopped.set()
    for s in sources:
        s.close()
    for c in conns:
        c.stop()
