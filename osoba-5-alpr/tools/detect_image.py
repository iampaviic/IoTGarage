"""Run the detector on images and save what it saw.

    python tools/detect_image.py photo1.jpg photo2.jpg --out rezultati/probe
    python tools/detect_image.py dataset/real/v1/images/*.jpg --roi 0 0.3 0.5 1.0

For every image writes <name>_overlay.jpg, <name>_crop.png and one PNG per
OCR variant (gray, contrast, threshold, adaptive) and prints a JSON summary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector import DetectorConfig, PlateDetector  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default="rezultati/probe")
    ap.add_argument("--roi", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                    help="region of interest as fractions of the frame")
    args = ap.parse_args(argv)

    det = PlateDetector(DetectorConfig(roi=tuple(args.roi) if args.roi else None))
    os.makedirs(args.out, exist_ok=True)
    for path in args.images:
        img = cv2.imread(path)
        if img is None:
            print("cannot read", path, file=sys.stderr)
            continue
        r = det.detect(img)
        base = os.path.join(args.out, os.path.splitext(os.path.basename(path))[0])
        overlay = img.copy()
        if args.roi:
            h, w = img.shape[:2]
            cv2.rectangle(overlay, (int(args.roi[0] * w), int(args.roi[1] * h)),
                          (int(args.roi[2] * w), int(args.roi[3] * h)), (255, 200, 0), 2)
        if r.found:
            cv2.polylines(overlay, [r.corners.astype("int32")], True, (0, 0, 255), 3)
            cv2.imwrite(base + "_crop.png", r.crop)
            for name, v in r.variants.items():
                if name != "original":
                    cv2.imwrite("%s_%s.png" % (base, name), v)
        cv2.imwrite(base + "_overlay.jpg", overlay)
        print(json.dumps(dict(file=path, **r.to_dict())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
