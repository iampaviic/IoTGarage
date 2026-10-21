"""Plate OCR for the IoT Garage (owner: osoba 6).

    from plate_ocr import PlateReader
    result = PlateReader().read(detection.crop, detection.variants)
"""

from plate_ocr.normalize import best_candidate, candidates, clean, format_plate, is_valid
from plate_ocr.reader import OcrConfig, OcrResult, PlateReader

__all__ = ["OcrConfig", "OcrResult", "PlateReader", "best_candidate", "candidates", "clean", "format_plate", "is_valid"]
