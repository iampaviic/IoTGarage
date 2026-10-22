"""Take labelled photos of the model with the USB camera (needs a screen).

    python tools/capture_dataset.py --out dataset/real/v1 --plate ZG1234AB --lighting svijetlo --angle 0 --distance blizu

Keys in the preview window:
    SPACE  save the current frame (the detector pre-labels the corners)
    d      toggle the live detection overlay
    q/ESC  quit

Change --plate / --lighting / --angle / --distance between series so the set
covers: several plates, bright and dim light, straight and angled, near and far.
Corners found automatically must be checked with tools/label_tool.py.
Privacy: photograph only the model - no real cars, no people.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector import PlateDetector  # noqa: E402
from plate_detector.camera import Camera  # noqa: E402
from plate_detector.dataset import Sample, read_labels, write_labels  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--camera", default="0")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--plate", default="", help="plate on the car in front of the camera (empty = no car)")
    ap.add_argument("--lighting", default="")
    ap.add_argument("--angle", default="")
    ap.add_argument("--distance", default="")
    args = ap.parse_args(argv)

    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    samples = read_labels(args.out) if os.path.exists(os.path.join(args.out, "labels.csv")) else []
    next_id = len(samples) + 1
    cam = Camera(args.camera, args.width, args.height).start()
    det = PlateDetector()
    overlay = True
    print(__doc__)
    try:
        while True:
            frame = cam.read_latest()
            view = frame.copy()
            r = det.detect(frame) if overlay else None
            if r is not None and r.found:
                cv2.polylines(view, [r.corners.astype("int32")], True, (0, 0, 255), 2)
                cv2.putText(view, "%.2f" % r.confidence, tuple(int(v) for v in r.corners[0]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(view, "plate=%s light=%s angle=%s dist=%s  saved=%d" % (
                args.plate or "-", args.lighting, args.angle, args.distance, next_id - 1),
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("capture", view)
            key = cv2.waitKey(30) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("d"):
                overlay = not overlay
            if key == ord(" "):
                name = "%04d_%s.jpg" % (next_id, time.strftime("%H%M%S"))
                cv2.imwrite(os.path.join(args.out, "images", name), frame)
                auto = det.detect(frame) if args.plate else None
                samples.append(Sample(file=name, plate=args.plate.upper(),
                                      corners=auto.corners if auto is not None and auto.found else None,
                                      lighting=args.lighting, angle=args.angle, distance=args.distance,
                                      note="auto-corners" if auto is not None and auto.found else ""))
                write_labels(args.out, samples)
                next_id += 1
                print("saved", name)
    finally:
        cam.stop()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
