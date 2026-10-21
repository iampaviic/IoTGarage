"""Image variants of a rectified plate for the OCR stage.

OCR is run on several versions and the results are voted (osoba 6), because
no single preprocessing works for every lighting condition.
"""

from __future__ import annotations

from typing import Dict

import cv2
import numpy as np


def make_variants(crop_bgr: np.ndarray) -> Dict[str, np.ndarray]:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 8)).apply(gray)
    _, otsu = cv2.threshold(cv2.GaussianBlur(clahe, (3, 3), 0), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    block = max(15, (crop_bgr.shape[0] // 3) | 1)
    adaptive = cv2.adaptiveThreshold(clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 10)
    return {
        "original": crop_bgr,
        "gray": gray,
        "contrast": clahe,
        "threshold": otsu,
        "adaptive": adaptive,
    }
