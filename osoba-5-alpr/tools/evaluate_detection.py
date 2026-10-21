"""Measure plate detection on a labelled dataset.

    python tools/evaluate_detection.py dataset/real/v1
    python tools/evaluate_detection.py dataset/synthetic/controlled --report rezultati/detekcija_synthetic.md

A detection is correct when IoU(detected quad, labelled quad) >= 0.5.
For images without a plate, any detection counts as a false positive.
Writes a Markdown report and debug images of every failure (rezultati/debug/).
Success criterion of the project: >= 90 % on the controlled REAL photo set.
"""

from __future__ import annotations

import argparse
import collections
import os
import statistics
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector import DetectorConfig, PlateDetector  # noqa: E402
from plate_detector.dataset import image_path, read_labels  # noqa: E402
from plate_detector.geometry import quad_iou  # noqa: E402


def draw_debug(img, sample, result):
    out = img.copy()
    if sample.corners is not None:
        cv2.polylines(out, [sample.corners.astype(np.int32)], True, (0, 255, 0), 2)
    if result.found:
        cv2.polylines(out, [result.corners.astype(np.int32)], True, (0, 0, 255), 2)
        cv2.putText(out, "conf %.2f %s" % (result.confidence, result.method), (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(out, "green = label, red = detection", (10, out.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--report", help="Markdown report path (default rezultati/detekcija_<name>.md)")
    ap.add_argument("--debug-dir", default=os.path.join(os.path.dirname(__file__), "..", "rezultati", "debug"))
    ap.add_argument("--min-confidence", type=float, default=DetectorConfig().min_confidence)
    args = ap.parse_args(argv)

    name = os.path.basename(os.path.normpath(args.dataset))
    report = args.report or os.path.join(os.path.dirname(__file__), "..", "rezultati", "detekcija_%s.md" % name)
    det = PlateDetector(DetectorConfig(min_confidence=args.min_confidence))
    samples = read_labels(args.dataset)
    os.makedirs(args.debug_dir, exist_ok=True)

    tp = fn = fp = tn = 0
    times, ious, failures = [], [], []
    by_condition = collections.defaultdict(lambda: [0, 0])
    t_start = time.time()
    for s in samples:
        img = cv2.imread(image_path(args.dataset, s))
        if img is None:
            print("cannot read", s.file)
            continue
        r = det.detect(img)
        times.append(r.processing_ms)
        cond = "%s/%s/%s" % (s.lighting or "-", s.angle or "-", s.distance or "-")
        if s.plate and s.corners is not None:
            iou = quad_iou(r.corners, s.corners) if r.found else 0.0
            ok = iou >= args.iou
            by_condition[cond][1] += 1
            if ok:
                tp += 1
                ious.append(iou)
                by_condition[cond][0] += 1
            else:
                fn += 1
                failures.append((s, r, "missed" if not r.found else "wrong place (IoU %.2f)" % iou))
        elif not s.plate:
            if r.found:
                fp += 1
                failures.append((s, r, "false positive"))
            else:
                tn += 1
    positives = tp + fn
    rate = tp / positives if positives else 0.0

    for s, r, why in failures:
        cv2.imwrite(os.path.join(args.debug_dir, "%s_%s" % (name, s.file)), draw_debug(cv2.imread(image_path(args.dataset, s)), s, r))

    lines = [
        "# Detekcija pločica - %s" % name,
        "",
        "- skup: `%s`, slika: %d (s pločicom %d, bez pločice %d)" % (args.dataset, len(samples), positives, fp + tn),
        "- kriterij: IoU >= %.2f, min. confidence %.2f" % (args.iou, args.min_confidence),
        "- datum: %s" % time.strftime("%Y-%m-%d %H:%M"),
        "",
        "| metrika | vrijednost |",
        "|---|---|",
        "| **uspješnost detekcije** | **%.1f %%** (%d / %d) |" % (100 * rate, tp, positives),
        "| lažno pozitivni (slike bez pločice) | %d / %d |" % (fp, fp + tn),
        "| srednji IoU točnih detekcija | %s |" % ("%.3f" % statistics.mean(ious) if ious else "-"),
        "| vrijeme obrade (medijan / p95) | %.0f ms / %.0f ms |" % (
            statistics.median(times) if times else 0, float(np.percentile(times, 95)) if times else 0),
        "| kriterij projekta (>= 90 %%) | %s |" % ("ZADOVOLJEN" if rate >= 0.9 else "NIJE zadovoljen"),
        "",
        "## Po uvjetima snimanja (osvjetljenje / kut / udaljenost)",
        "",
        "| uvjeti | točno | ukupno | % |",
        "|---|---|---|---|",
    ]
    for cond, (ok, total) in sorted(by_condition.items()):
        lines.append("| %s | %d | %d | %.0f %% |" % (cond, ok, total, 100.0 * ok / total if total else 0))
    lines += ["", "## Neuspjesi", "", "Slike s ucrtanom oznakom (zeleno) i detekcijom (crveno): `%s`" % args.debug_dir, ""]
    for s, r, why in failures[:50]:
        lines.append("- `%s` %s - %s (conf %.2f)" % (s.file, s.plate or "(bez pločice)", why, r.confidence))
    os.makedirs(os.path.dirname(os.path.abspath(report)), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("detection rate %.1f %% (%d/%d), false positives %d/%d, median %.0f ms, %.1f s total"
          % (100 * rate, tp, positives, fp, fp + tn, statistics.median(times) if times else 0, time.time() - t_start))
    print("report:", os.path.normpath(report))
    return 0 if rate >= 0.9 else 1


if __name__ == "__main__":
    sys.exit(main())
