"""Edge service command line.

    python -m edge_service --config edge.yaml all          run access control + ALPR
    python -m edge_service --config edge.yaml access       only access control
    python -m edge_service --config edge.yaml alpr         only ALPR
    python -m edge_service read IMAGE [IMAGE ...]          offline: detect + read plates in photos
    python -m edge_service manual approve-entry --plate ZG1234AB --note "OCR nije uspio"
    python -m edge_service manual approve-exit  --plate ZG1234AB
    python -m edge_service manual open --gate exit
    python -m edge_service manual deny --gate entrance
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from edge_service.config import EdgeConfig


def _manual(cfg: EdgeConfig, args) -> int:
    from garage_contract import topics
    from garage_contract.mqtt import MqttConnection
    from garage_contract.timeutil import utc_now_iso

    action = {"approve-entry": "APPROVE_ENTRY", "approve-exit": "APPROVE_EXIT", "deny": "DENY",
              "open": "OPEN_GATE", "close": "CLOSE_GATE"}[args.action]
    gate = args.gate or ("entrance" if action == "APPROVE_ENTRY" else "exit")
    payload = {"requestId": "man-%d" % int(time.time() * 1000), "action": action, "gate": gate.upper(),
               "plate": args.plate, "operator": args.operator, "note": args.note or "", "timestamp": utc_now_iso()}
    conn = MqttConnection("manual-cli-%d" % int(time.time()), cfg.mqtt)
    if not conn.start():
        print("MQTT broker %s:%s not reachable" % (cfg.mqtt.host, cfg.mqtt.port), file=sys.stderr)
        return 1
    conn.publish_json(topics.ACCESS_MANUAL, payload)
    time.sleep(0.3)
    conn.stop()
    print("sent", json.dumps(payload, ensure_ascii=False))
    return 0


def _read(paths) -> int:
    import cv2

    from plate_detector import PlateDetector
    from plate_ocr import PlateReader

    det, reader = PlateDetector(), PlateReader()
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            print(p, "cannot read", file=sys.stderr)
            continue
        d = det.detect(img)
        if not d.found:
            print("%-40s no plate (detection conf %.2f, %.0f ms)" % (p, d.confidence, d.processing_ms))
            continue
        r = reader.read(d.crop, d.variants)
        print("%-40s %-12s conf=%.2f %-6s det=%.2f %4.0f ms  raw=%r" % (
            p, r.plate or "-", r.confidence, r.level, d.confidence, d.processing_ms + r.processing_ms, r.raw_text))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="edge_service", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="YAML config (see edge.example.yaml)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("all")
    sub.add_parser("access")
    sub.add_parser("alpr")
    p = sub.add_parser("read")
    p.add_argument("images", nargs="+")
    p = sub.add_parser("manual")
    p.add_argument("action", choices=["approve-entry", "approve-exit", "deny", "open", "close"])
    p.add_argument("--plate")
    p.add_argument("--gate", choices=["entrance", "exit"])
    p.add_argument("--operator", default="cli")
    p.add_argument("--note")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    if args.cmd == "read":
        return _read(args.images)
    cfg = EdgeConfig.load(args.config)
    if args.cmd == "manual":
        return _manual(cfg, args)
    from edge_service.runner import run

    run(cfg, ["access", "alpr"] if args.cmd == "all" else [args.cmd])
    return 0


if __name__ == "__main__":
    sys.exit(main())
