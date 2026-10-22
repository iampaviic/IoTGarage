"""Prepare a rectified plate crop for character recognition.

Steps (all on the 520x110 crop from the detector):
  1. find the blue EU band (left) and cut it away
  2. find the red/white shield between city code and digits and paint it white
     (otherwise OCR reads it as 'H', 'B', '3', 'I' ...)
  3. cut the black border
  4. make sure text is black on white, add a white margin, scale to a fixed height
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

TARGET_HEIGHT = 90  # px of the whole prepared strip; characters end up ~60 px high


def _hsv_masks(crop_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    blue = (h > 95) & (h < 135) & (s > 70) & (v > 40)
    red = ((h < 10) | (h > 165)) & (s > 70) & (v > 50)
    return blue, red


def find_band_edge(crop_bgr: np.ndarray) -> int:
    """x where the blue EU band ends (0 if there is none)."""
    blue, _ = _hsv_masks(crop_bgr)
    w = crop_bgr.shape[1]
    cols = blue.mean(axis=0)
    edge = 0
    for x in range(int(w * 0.2)):
        if cols[x] > 0.3:
            edge = x + 1
    return edge


def find_shield_span(crop_bgr: np.ndarray, start_x: int = 0) -> Optional[Tuple[int, int]]:
    """Column range [x0, x1) of the red chequered shield, or None."""
    _, red = _hsv_masks(crop_bgr)
    w = crop_bgr.shape[1]
    cols = red.mean(axis=0)
    xs = [x for x in range(max(start_x, int(w * 0.12)), int(w * 0.6)) if cols[x] > 0.08]
    if not xs:
        return None
    # largest contiguous run (allow 2 px gaps)
    runs: List[List[int]] = [[xs[0], xs[0]]]
    for x in xs[1:]:
        if x - runs[-1][1] <= 3:
            runs[-1][1] = x
        else:
            runs.append([x, x])
    x0, x1 = max(runs, key=lambda r: r[1] - r[0])
    if x1 - x0 < w * 0.015:
        return None
    pad = max(2, int(w * 0.006))
    return max(0, x0 - pad), min(w, x1 + pad + 1)


def prepare(crop_bgr: np.ndarray, variants: Dict[str, np.ndarray],
            target_height: int = TARGET_HEIGHT) -> Dict[str, np.ndarray]:
    """Return OCR-ready grayscale images (black text on white) for each variant."""
    h, w = crop_bgr.shape[:2]
    band = find_band_edge(crop_bgr)
    left = band + int(w * 0.008) if band else int(w * 0.02)
    shield = find_shield_span(crop_bgr, start_x=left)
    blue, red = _hsv_masks(crop_bgr)
    colour_mask = cv2.dilate((blue | red).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    top, bottom, right = int(h * 0.07), int(h * 0.93), int(w * 0.985)

    out: Dict[str, np.ndarray] = {}
    for name, img in variants.items():
        g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        g = g.copy()
        if g.shape[:2] != (h, w):
            g = cv2.resize(g, (w, h))
        g[colour_mask] = 255
        if shield:
            g[:, shield[0]:shield[1]] = 255
        g = g[top:bottom, left:right]
        # polarity: the plate background (most pixels) must be white
        if np.median(g) < 128:
            g = 255 - g
        scale = target_height / float(g.shape[0])
        g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        out[name] = cv2.copyMakeBorder(g, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
    return out


def binarize(gray: np.ndarray) -> np.ndarray:
    """Black text (0) on white (255)."""
    _, th = cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return th


def segment_characters(gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Bounding boxes (x, y, w, h) of character blobs, left to right."""
    th = binarize(gray)
    inv = 255 - th
    n, _, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
    H, W = gray.shape
    boxes = []
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        if ch < 0.45 * H or ch > 0.95 * H or cw > 0.25 * W or area < 30:
            continue
        boxes.append((int(x), int(y), int(cw), int(ch)))
    if boxes:  # characters of a plate have a similar height; drop outliers (dash, dirt)
        med = float(np.median([b[3] for b in boxes]))
        boxes = [b for b in boxes if 0.75 * med <= b[3] <= 1.25 * med]
    return sorted(boxes, key=lambda b: b[0])
