"""OCR accuracy table on a labelled dataset (same format as osoba-5-alpr/dataset).

    python tools/evaluate_ocr.py ../osoba-5-alpr/dataset/real/v1
    python tools/evaluate_ocr.py ../osoba-5-alpr/dataset/synthetic/controlled --engines template

Runs detection + OCR exactly like the edge service (one frame per image) and
writes rezultati/ocr_<dataset>.md with:
  * exact-match accuracy, accepted / retry / manual shares
  * WRONG ACCEPTS - plates accepted automatically but read wrongly. This must be 0:
    a wrong accept opens the gate for the wrong car or closes the wrong session.
  * accuracy per plate and per recording condition
"""

from __future__ import annotations

import argparse
import collections
import os
import statistics
import sys
import time

import cv2

from plate_detector import PlateDetector
from plate_detector.dataset import image_path, read_labels
from plate_ocr import PlateReader
from plate_ocr.reader import OcrConfig


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--engines", nargs="+", default=["template", "tesseract"])
    ap.add_argument("--accept", type=float, default=0.85)
    ap.add_argument("--retry", type=float, default=0.60)
    ap.add_argument("--report")
    args = ap.parse_args(argv)

    name = os.path.basename(os.path.normpath(args.dataset))
    report = args.report or os.path.join(os.path.dirname(__file__), "..", "rezultati", "ocr_%s.md" % name)
    det = PlateDetector()
    reader = PlateReader(OcrConfig(engines=tuple(args.engines), accept_threshold=args.accept,
                                   retry_threshold=args.retry))
    samples = [s for s in read_labels(args.dataset) if s.plate]
    levels = collections.Counter()
    exact = 0
    wrong_accepts = []
    per_plate = collections.defaultdict(lambda: [0, 0])
    per_cond = collections.defaultdict(lambda: [0, 0])
    times = []
    rows = []
    for s in samples:
        img = cv2.imread(image_path(args.dataset, s))
        d = det.detect(img)
        if not d.found:
            levels["NO_DETECTION"] += 1
            per_plate[s.plate][1] += 1
            rows.append((s.file, s.plate, "-", 0.0, "NO_DETECTION"))
            continue
        r = reader.read(d.crop, d.variants)
        times.append(d.processing_ms + r.processing_ms)
        ok = r.plate == s.plate
        exact += ok
        levels[r.level] += 1
        if r.accepted and not ok:
            wrong_accepts.append((s.file, s.plate, r.plate, r.confidence))
        per_plate[s.plate][0] += ok
        per_plate[s.plate][1] += 1
        cond = "%s/%s/%s" % (s.lighting or "-", s.angle or "-", s.distance or "-")
        per_cond[cond][0] += ok
        per_cond[cond][1] += 1
        rows.append((s.file, s.plate, r.plate or "-", r.confidence, r.level))

    n = len(samples) or 1
    lines = [
        "# Točnost OCR-a - %s" % name, "",
        "- skup: `%s` (%d slika s pločicom), motori: %s" % (args.dataset, len(samples), ", ".join(reader.engine_names)),
        "- pragovi: prihvati >= %.2f, ponovi >= %.2f; datum %s" % (args.accept, args.retry, time.strftime("%Y-%m-%d %H:%M")),
        "", "| metrika | vrijednost |", "|---|---|",
        "| točno pročitano (bilo koja razina) | %.1f %% (%d/%d) |" % (100.0 * exact / n, exact, len(samples)),
        "| automatski prihvaćeno (ACCEPT) | %.1f %% |" % (100.0 * levels["ACCEPT"] / n),
        "| ponovno snimanje (RETRY) | %.1f %% |" % (100.0 * levels["RETRY"] / n),
        "| ručna intervencija (MANUAL) | %.1f %% |" % (100.0 * levels["MANUAL"] / n),
        "| pločica nije pronađena | %.1f %% |" % (100.0 * levels["NO_DETECTION"] / n),
        "| **POGREŠNO prihvaćeno** (mora biti 0) | **%d** |" % len(wrong_accepts),
        "| vrijeme detekcija + OCR (medijan) | %.0f ms |" % (statistics.median(times) if times else 0),
        "", "## Po registraciji", "", "| registracija | točno | ukupno |", "|---|---|---|",
    ]
    lines += ["| %s | %d | %d |" % (p, ok, tot) for p, (ok, tot) in sorted(per_plate.items())]
    lines += ["", "## Po uvjetima snimanja", "", "| uvjeti | točno | ukupno |", "|---|---|---|"]
    lines += ["| %s | %d | %d |" % (c, ok, tot) for c, (ok, tot) in sorted(per_cond.items())]
    if wrong_accepts:
        lines += ["", "## Pogrešno prihvaćeno", ""]
        lines += ["- `%s` stvarno %s, pročitano %s (conf %.2f)" % w for w in wrong_accepts]
    lines += ["", "## Sva očitanja", "", "| slika | stvarno | pročitano | confidence | razina |", "|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %.2f | %s |" % r for r in rows]
    os.makedirs(os.path.dirname(os.path.abspath(report)), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("exact %.1f %%, accepted %.1f %%, wrong accepts %d, report %s" % (
        100.0 * exact / n, 100.0 * levels["ACCEPT"] / n, len(wrong_accepts), os.path.normpath(report)))
    return 0 if not wrong_accepts else 1


if __name__ == "__main__":
    sys.exit(main())
