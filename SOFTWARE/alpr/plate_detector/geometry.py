"""Small geometry helpers: corner ordering, perspective warp, quad IoU."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Return 4 points ordered TL, TR, BR, BL (image coordinates)."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    # sort by angle around the centroid, then rotate so TL (min x+y) is first
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    pts = pts[np.argsort(ang)]  # clockwise in image coords starting from left-ish
    start = int(np.argmin(pts.sum(axis=1)))
    pts = np.roll(pts, -start, axis=0)
    # make sure the second point is the top-right one (smaller y than BL)
    if pts[1][1] > pts[3][1]:
        pts = np.array([pts[0], pts[3], pts[2], pts[1]], np.float32)
    return pts


def warp_plate(image: np.ndarray, corners: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    w, h = size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    m = cv2.getPerspectiveTransform(order_corners(corners), dst)
    return cv2.warpPerspective(image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def quad_aspect(corners: np.ndarray) -> float:
    c = order_corners(corners)
    top = np.linalg.norm(c[1] - c[0])
    bottom = np.linalg.norm(c[2] - c[3])
    left = np.linalg.norm(c[3] - c[0])
    right = np.linalg.norm(c[2] - c[1])
    return float((top + bottom) / max(1e-6, left + right))


def quad_area(corners: np.ndarray) -> float:
    return float(cv2.contourArea(order_corners(corners)))


def quad_iou(a: np.ndarray, b: np.ndarray) -> float:
    a, b = order_corners(a), order_corners(b)
    inter, _ = cv2.intersectConvexConvex(a, b)
    union = cv2.contourArea(a) + cv2.contourArea(b) - inter
    return float(inter / union) if union > 0 else 0.0


def bbox_of(corners: np.ndarray) -> Tuple[int, int, int, int]:
    x, y, w, h = cv2.boundingRect(np.asarray(corners, np.float32).reshape(-1, 1, 2))
    return int(x), int(y), int(w), int(h)


def expand_quad(corners: np.ndarray, fx: float, fy: float) -> np.ndarray:
    """Scale a quad around its centre along its own axes."""
    c = order_corners(corners)
    centre = c.mean(axis=0)
    ux = ((c[1] - c[0]) + (c[2] - c[3])) / 2.0
    uy = ((c[3] - c[0]) + (c[2] - c[1])) / 2.0
    ux, uy = ux * fx / 2.0, uy * fy / 2.0
    return np.array([centre - ux - uy, centre + ux - uy, centre + ux + uy, centre - ux + uy], np.float32)
