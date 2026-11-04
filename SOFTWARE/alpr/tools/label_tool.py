"""Check / draw plate corners in a dataset (needs a screen).

    python tools/label_tool.py dataset/real/v1 [--only-unchecked]

Mouse: click the 4 plate corners in order TOP-LEFT, TOP-RIGHT, BOTTOM-RIGHT, BOTTOM-LEFT.
Keys:
    ENTER / n   accept and go to the next image (marks it as checked)
    a           take the automatic detection as the label
    r           reset corners
    x           image has no plate (negative example)
    t           type the plate text in the terminal
    b           back one image
    q / ESC     save and quit
labels.csv is saved after every image.
"""

from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector import PlateDetector  # noqa: E402
from plate_detector.dataset import image_path, read_labels, write_labels  # noqa: E402

clicks = []


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < 4:
        clicks.append((x / param["scale"], y / param["scale"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--only-unchecked", action="store_true")
    args = ap.parse_args(argv)

    samples = read_labels(args.dataset)
    det = PlateDetector()
    state = {"scale": 1.0}
    cv2.namedWindow("label")
    cv2.setMouseCallback("label", on_mouse, state)
    i = 0
    while 0 <= i < len(samples):
        s = samples[i]
        if args.only_unchecked and "checked" in s.note:
            i += 1
            continue
        img = cv2.imread(image_path(args.dataset, s))
        state["scale"] = min(1.0, 1280.0 / img.shape[1])
        clicks.clear()
        auto = det.detect(img)
        while True:
            view = cv2.resize(img, None, fx=state["scale"], fy=state["scale"])
            sc = state["scale"]
            if s.corners is not None:
                cv2.polylines(view, [(s.corners * sc).astype(np.int32)], True, (0, 255, 0), 2)
            if auto.found:
                cv2.polylines(view, [(auto.corners * sc).astype(np.int32)], True, (0, 0, 255), 1)
            for c in clicks:
                cv2.circle(view, (int(c[0] * sc), int(c[1] * sc)), 4, (255, 255, 0), -1)
            cv2.putText(view, "%d/%d %s plate=%s [%s]" % (i + 1, len(samples), s.file, s.plate or "-", s.note),
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("label", view)
            key = cv2.waitKey(30) & 0xFF
            if len(clicks) == 4:
                s.corners = np.array(clicks, np.float32)
                clicks.clear()
            if key in (13, ord("n")):
                s.note = "checked"
                i += 1
                break
            if key == ord("a") and auto.found:
                s.corners = auto.corners
            if key == ord("r"):
                s.corners = None
                clicks.clear()
            if key == ord("x"):
                s.plate, s.corners, s.note = "", None, "checked"
                i += 1
                break
            if key == ord("t"):
                s.plate = input("plate for %s: " % s.file).strip().upper().replace(" ", "").replace("-", "")
            if key == ord("b"):
                i = max(0, i - 1)
                break
            if key in (ord("q"), 27):
                write_labels(args.dataset, samples)
                cv2.destroyAllWindows()
                return 0
        write_labels(args.dataset, samples)
    cv2.destroyAllWindows()
    print("done, labels saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
