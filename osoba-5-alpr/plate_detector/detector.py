"""Licence plate detection: find the plate, correct perspective, crop it.

Classic computer vision (OpenCV only, no neural network) so it runs on the
Raspberry Pi and Jetson Nano CPU in ~50-150 ms per 1280x720 frame.

Pipeline
  1. candidate quads from three independent detectors
       a) edges   - Canny + 4-corner contours (plate border)
       b) text    - black-hat + horizontal gradient (row of dark characters)
       c) bright  - white, low-saturation regions
  2. every candidate is rectified to 520x110 px and scored:
       aspect ratio, character-like blobs, contrast, ink ratio, blue EU band
  3. best candidate wins; confidence = its score (0..1)

Only *where* the plate is and how good the crop is is decided here. Reading
the characters is the job of the OCR module (osoba 6).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from plate_detector.geometry import bbox_of, expand_quad, order_corners, quad_aspect, quad_iou, warp_plate
from plate_detector.variants import make_variants

PLATE_ASPECT = 520.0 / 110.0


@dataclass
class DetectorConfig:
    output_size: Tuple[int, int] = (520, 110)      # rectified plate size (w, h)
    max_work_width: int = 960                      # frames are downscaled to this for speed
    min_plate_width_frac: float = 0.06             # plate narrower than 6 % of the frame is ignored
    max_plate_width_frac: float = 0.9
    aspect_range: Tuple[float, float] = (2.3, 7.5)
    min_confidence: float = 0.5                    # below this "found" is False (>= 0.8 is a strong hit)
    roi: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1) as fractions of the frame


@dataclass
class Candidate:
    corners: np.ndarray
    method: str
    score: float = 0.0
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class DetectionResult:
    found: bool
    confidence: float
    corners: Optional[np.ndarray] = None            # 4x2 TL,TR,BR,BL in full-frame pixels
    bbox: Optional[Tuple[int, int, int, int]] = None
    crop: Optional[np.ndarray] = None               # rectified BGR plate
    variants: Dict[str, np.ndarray] = field(default_factory=dict)
    processing_ms: float = 0.0
    method: str = ""
    candidates: int = 0
    features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """JSON-friendly summary (no images)."""
        return {
            "found": self.found,
            "confidence": round(self.confidence, 3),
            "corners": None if self.corners is None else [[round(float(x), 1), round(float(y), 1)] for x, y in self.corners],
            "bbox": self.bbox,
            "processingMs": round(self.processing_ms, 1),
            "method": self.method,
            "candidates": self.candidates,
            "features": {k: round(v, 3) for k, v in self.features.items()},
        }


def refine_corners(frame: np.ndarray, corners: np.ndarray) -> Optional[np.ndarray]:
    """Snap a rough plate quad to the real plate outline.

    The region around the rough quad is rectified, the white plate area (plus
    the blue EU band) is segmented and its 4-corner outline is mapped back to
    the frame. This recovers the true perspective, which matters a lot for OCR
    (a wrong quad shears the characters and cuts their tops off).
    Returns None when the outline is not clear enough - keep the rough quad then.
    """
    big = expand_quad(corners, 1.3, 1.8)
    W = 640
    H = int(round(W / max(1.0, quad_aspect(big))))
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], np.float32)
    M = cv2.getPerspectiveTransform(order_corners(big), dst)
    region = cv2.warpPerspective(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    v, sat, hue = hsv[:, :, 2], hsv[:, :, 1], hsv[:, :, 0]
    otsu, _ = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    white = (v >= otsu) & (sat < 80)
    blue = (hue > 95) & (hue < 135) & (sat > 70) & (v > 40)
    mask = (white | blue).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 0.25 * W * H or area > 0.9 * W * H:
        return None
    hull = cv2.convexHull(cnt)
    peri = cv2.arcLength(hull, True)
    quad = None
    for eps in (0.01, 0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype(np.float32)
            break
    if quad is None:
        return None
    a = quad_aspect(quad)
    if not 3.0 <= a <= 6.5:
        return None
    # the outline found is the inside of the thin black border: grow by its width
    quad = expand_quad(quad, 1 + 5.0 / 520, 1 + 5.0 / 110)
    back = cv2.perspectiveTransform(quad[None], np.linalg.inv(M))[0]
    return order_corners(back)


class PlateDetector:
    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self.config = config or DetectorConfig()

    # ------------------------------------------------------------------ API
    def detect(self, frame: np.ndarray, roi: Optional[Tuple[float, float, float, float]] = None) -> DetectionResult:
        t0 = time.perf_counter()
        cfg = self.config
        roi = roi or cfg.roi
        H0, W0 = frame.shape[:2]
        ox, oy = 0, 0
        view = frame
        if roi is not None:
            x0, y0 = int(roi[0] * W0), int(roi[1] * H0)
            x1, y1 = int(roi[2] * W0), int(roi[3] * H0)
            view = frame[y0:y1, x0:x1]
            ox, oy = x0, y0

        scale = min(1.0, cfg.max_work_width / float(view.shape[1]))
        small = cv2.resize(view, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else view
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        cands = self._edge_candidates(gray) + self._text_candidates(gray) + self._bright_candidates(small, gray)
        cands = [c for c in cands if self._plausible(c.corners, small.shape)]
        frame_bright = float(max(1.0, np.percentile(gray, 99)))
        for c in cands:
            self._score(small, gray, c, frame_bright)
        cands = self._refine(small, gray, cands)
        cands.sort(key=lambda c: c.score, reverse=True)

        ms = (time.perf_counter() - t0) * 1000.0
        if not cands or cands[0].score < cfg.min_confidence:
            best_score = cands[0].score if cands else 0.0
            return DetectionResult(found=False, confidence=float(best_score), processing_ms=ms, candidates=len(cands))

        best = cands[0]
        corners = best.corners / scale + np.array([ox, oy], np.float32)
        refined = refine_corners(frame, corners)
        if refined is not None:
            corners = refined
        crop = warp_plate(frame, corners, cfg.output_size)
        ms = (time.perf_counter() - t0) * 1000.0
        return DetectionResult(
            found=True,
            confidence=float(best.score),
            corners=order_corners(corners),
            bbox=bbox_of(corners),
            crop=crop,
            variants=make_variants(crop),
            processing_ms=ms,
            method=best.method,
            candidates=len(cands),
            features=best.features,
        )

    # ------------------------------------------------------------ candidates
    def _edge_candidates(self, gray: np.ndarray) -> List[Candidate]:
        out = []
        blur = cv2.bilateralFilter(gray, 7, 50, 50)
        for lo, hi in ((30, 120), (60, 200)):
            edges = cv2.Canny(blur, lo, hi)
            edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) < 200:
                    continue
                peri = cv2.arcLength(cnt, True)
                for eps in (0.02, 0.04):
                    approx = cv2.approxPolyDP(cnt, eps * peri, True)
                    if len(approx) == 4 and cv2.isContourConvex(approx):
                        out.append(Candidate(approx.reshape(4, 2).astype(np.float32), "edges"))
                        break
                else:
                    rect = cv2.minAreaRect(cnt)
                    out.append(Candidate(cv2.boxPoints(rect).astype(np.float32), "edges-rect"))
        return out

    def _text_candidates(self, gray: np.ndarray) -> List[Candidate]:
        h, w = gray.shape
        k = max(9, int(w / 60)) | 1
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(5, k // 3))))
        gx = np.absolute(cv2.Sobel(blackhat, cv2.CV_32F, 1, 0, ksize=3))
        gx = (255 * (gx - gx.min()) / max(1e-6, gx.max() - gx.min())).astype(np.uint8)
        gx = cv2.GaussianBlur(gx, (5, 5), 0)
        closed = cv2.morphologyEx(gx, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(3, k // 4))))
        _, th = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        th = cv2.erode(th, None, iterations=1)
        th = cv2.dilate(th, None, iterations=2)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for cnt in contours:
            if cv2.contourArea(cnt) < 150:
                continue
            box = cv2.boxPoints(cv2.minAreaRect(cnt)).astype(np.float32)
            # the text block covers ~85 % of the width and ~65 % of the height of the plate
            out.append(Candidate(expand_quad(box, 1.18, 1.5), "text"))
        return out

    def _bright_candidates(self, bgr: np.ndarray, gray: np.ndarray) -> List[Candidate]:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2]
        thr = max(90, int(np.percentile(v, 90)) - 25)
        mask = ((v >= thr) & (hsv[:, :, 1] < 70)).astype(np.uint8) * 255
        h, w = gray.shape
        k = max(5, int(w / 80)) | 1
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for cnt in contours:
            if cv2.contourArea(cnt) < 200:
                continue
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, 0.03 * peri, True)
            if len(approx) == 4:
                out.append(Candidate(approx.reshape(4, 2).astype(np.float32), "bright"))
            out.append(Candidate(cv2.boxPoints(cv2.minAreaRect(cnt)).astype(np.float32), "bright-rect"))
        return out

    # -------------------------------------------------------------- filtering
    def _plausible(self, corners: np.ndarray, shape: Sequence[int]) -> bool:
        h, w = shape[:2]
        c = order_corners(corners)
        width = (np.linalg.norm(c[1] - c[0]) + np.linalg.norm(c[2] - c[3])) / 2
        if not (self.config.min_plate_width_frac * w <= width <= self.config.max_plate_width_frac * w):
            return False
        a = quad_aspect(c)
        if not (self.config.aspect_range[0] <= a <= self.config.aspect_range[1]):
            return False
        # reject strongly rotated quads (plates are roughly horizontal)
        angle = abs(math.degrees(math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0])))
        return angle < 30

    def _score(self, bgr: np.ndarray, gray: np.ndarray, cand: Candidate, frame_bright: float) -> None:
        W, H = 260, 55  # small canonical size is enough for scoring
        warped_gray = warp_plate(gray, cand.corners, (W, H))
        warped_bgr = warp_plate(bgr, cand.corners, (W, H))

        a = quad_aspect(cand.corners)
        aspect_score = math.exp(-(math.log(a / PLATE_ASPECT) ** 2) / (2 * 0.3 ** 2))

        inner = warped_gray[int(H * 0.1):int(H * 0.9), int(W * 0.1):int(W * 0.97)]
        p10, p50, p90 = np.percentile(inner, (10, 50, 90))
        contrast = float(min(1.0, (p90 - p10) / 140.0))
        # plate background is white: among the brightest things in the frame and unsaturated
        rel = p50 / frame_bright
        sat = float(np.percentile(cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2HSV)[:, :, 1], 50))
        whiteness = float(min(1.0, max(0.0, (rel - 0.55) / 0.35)) * min(1.0, max(0.0, 1.0 - sat / 60.0)))

        _, binv = cv2.threshold(inner, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        ink = float(np.count_nonzero(binv)) / binv.size
        ink_score = 1.0 if 0.12 <= ink <= 0.5 else max(0.0, 1.0 - abs(ink - 0.3) * 3)

        n, _, stats, _ = cv2.connectedComponentsWithStats(binv, connectivity=8)
        ih, iw = inner.shape
        chars = 0
        heights = []
        for i in range(1, n):
            x, y, cw, ch, area = stats[i]
            if 0.35 * ih <= ch <= 0.98 * ih and 0.015 * iw <= cw <= 0.2 * iw and area > 0.15 * cw * ch:
                chars += 1
                heights.append(ch)
        if 4 <= chars <= 10:
            char_score = 1.0
        elif chars in (3, 11, 12):
            char_score = 0.5
        else:
            char_score = 0.0
        if len(heights) >= 3:  # characters of one plate have similar height
            char_score *= max(0.3, 1.0 - float(np.std(heights) / max(1.0, np.mean(heights))) * 2)

        band = cv2.cvtColor(warped_bgr[:, : int(W * 0.09)], cv2.COLOR_BGR2HSV)
        blue = (band[:, :, 0] > 95) & (band[:, :, 0] < 135) & (band[:, :, 1] > 80) & (band[:, :, 2] > 50)
        blue_score = float(min(1.0, np.count_nonzero(blue) / max(1, blue.size) / 0.4))

        cand.features = {
            "aspect": a, "aspectScore": aspect_score, "contrast": contrast, "whiteness": whiteness,
            "ink": ink, "chars": float(chars), "charScore": char_score, "blueBand": blue_score,
        }
        score = (0.18 * aspect_score + 0.32 * char_score + 0.10 * contrast + 0.17 * whiteness
                 + 0.08 * ink_score + 0.15 * blue_score)
        if chars < 3:
            score *= 0.5
        if whiteness < 0.3 and blue_score < 0.3:  # text on a wall, a poster, ... but not a plate
            score *= 0.5
        cand.score = float(max(0.0, min(1.0, score)))

    def _refine(self, bgr: np.ndarray, gray: np.ndarray, cands: List[Candidate]) -> List[Candidate]:
        """Non-maximum suppression; when two candidates overlap keep the better one,
        preferring true 4-corner quads (they carry the perspective)."""
        cands = sorted(cands, key=lambda c: c.score, reverse=True)
        kept: List[Candidate] = []
        for c in cands:
            dup = False
            for k in kept:
                if quad_iou(c.corners, k.corners) > 0.5:
                    if c.method in ("edges", "bright") and k.method not in ("edges", "bright") and c.score >= k.score - 0.08:
                        k.corners, k.method, k.features = c.corners, c.method + "+" + k.method, c.features
                        k.score = max(k.score, c.score)
                    dup = True
                    break
            if not dup:
                kept.append(c)
        return kept[:10]
