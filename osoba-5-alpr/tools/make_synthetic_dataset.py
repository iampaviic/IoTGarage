"""Create a labelled synthetic dataset (images + labels.csv).

    python tools/make_synthetic_dataset.py --out dataset/synthetic/controlled --n 200 --preset controlled
    python tools/make_synthetic_dataset.py --out dataset/synthetic/hard --n 200 --preset hard --negatives 20

Synthetic images are only a stand-in until the real photo set of the model
exists. The final success criterion (>= 90 %) must be measured on REAL photos.
"""

from __future__ import annotations

import argparse
import os
import random
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector.dataset import Sample, write_labels  # noqa: E402
from plate_detector.synth import SceneParams, render_scene  # noqa: E402

PRESETS = {"controlled": SceneParams.controlled, "default": SceneParams, "hard": SceneParams.hard}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--negatives", type=int, default=0, help="extra images without any plate")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="controlled")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    params = PRESETS[args.preset]()
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    samples = []
    for i in range(args.n + args.negatives):
        negative = i >= args.n
        scene = render_scene(rng=rng, params=params, with_plate=not negative)
        name = "%04d.jpg" % (i + 1)
        cv2.imwrite(os.path.join(args.out, "images", name), scene.image)
        samples.append(Sample(file=name, plate=scene.plate, corners=None if negative else scene.corners,
                              lighting="synthetic", angle=args.preset, distance="", note="synthetic"))
    write_labels(args.out, samples)
    print("wrote %d images to %s" % (len(samples), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
