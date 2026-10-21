"""Labelled dataset format shared by the synthetic generator, the capture and
labelling tools and the evaluation scripts (detection here, OCR at osoba 6).

    <dataset>/
        images/0001.jpg ...
        labels.csv

labels.csv columns:
    file, plate, x1, y1, x2, y2, x3, y3, x4, y4, lighting, angle, distance, note
corners are TL, TR, BR, BL in pixels; empty corners = plate not labelled yet;
plate empty = image without a plate (negative example).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

import numpy as np

FIELDS = ["file", "plate", "x1", "y1", "x2", "y2", "x3", "y3", "x4", "y4", "lighting", "angle", "distance", "note"]


@dataclass
class Sample:
    file: str
    plate: str = ""
    corners: Optional[np.ndarray] = None
    lighting: str = ""
    angle: str = ""
    distance: str = ""
    note: str = ""
    extra: dict = field(default_factory=dict)

    def to_row(self) -> dict:
        row = {"file": self.file, "plate": self.plate, "lighting": self.lighting, "angle": self.angle,
               "distance": self.distance, "note": self.note}
        if self.corners is not None:
            for i, (x, y) in enumerate(self.corners, 1):
                row["x%d" % i], row["y%d" % i] = round(float(x), 1), round(float(y), 1)
        return row


def read_labels(dataset_dir: str) -> List[Sample]:
    path = os.path.join(dataset_dir, "labels.csv")
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            corners = None
            if row.get("x1"):
                corners = np.array([[float(row["x%d" % i]), float(row["y%d" % i])] for i in range(1, 5)], np.float32)
            out.append(Sample(file=row["file"], plate=row.get("plate", ""), corners=corners,
                              lighting=row.get("lighting", ""), angle=row.get("angle", ""),
                              distance=row.get("distance", ""), note=row.get("note", "")))
    return out


def write_labels(dataset_dir: str, samples: List[Sample]) -> None:
    os.makedirs(dataset_dir, exist_ok=True)
    with open(os.path.join(dataset_dir, "labels.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for s in samples:
            w.writerow(s.to_row())


def image_path(dataset_dir: str, sample: Sample) -> str:
    return os.path.join(dataset_dir, "images", sample.file)


def iter_images(dataset_dir: str) -> Iterator[str]:
    img_dir = os.path.join(dataset_dir, "images")
    for name in sorted(os.listdir(img_dir)):
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            yield name
