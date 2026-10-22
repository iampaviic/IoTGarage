"""Plate detection for the IoT Garage ALPR (owner: osoba 5).

    from plate_detector import PlateDetector
    result = PlateDetector().detect(frame_bgr)
    if result.found:
        result.crop, result.corners, result.confidence, result.variants
"""

from plate_detector.detector import DetectionResult, DetectorConfig, PlateDetector
from plate_detector.variants import make_variants

__all__ = ["DetectionResult", "DetectorConfig", "PlateDetector", "make_variants"]
