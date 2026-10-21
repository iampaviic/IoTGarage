"""PlateReader: from a detected plate crop to a validated registration.

    reader = PlateReader()
    result = reader.read(detection.crop, detection.variants)
    result.plate        'ZG1234AB' or None
    result.confidence   0..1
    result.level        'ACCEPT' (>= 0.85) | 'RETRY' (0.60-0.85) | 'MANUAL' (< 0.60)

How the confidence is computed
  every engine reads every image variant -> many readings
  each reading is normalised to the plate format (position-aware O/0, I/1, ...)
  readings vote; a reading supports a plate with weight w(engine) * quality
      quality = engine confidence * 0.9^(fixes needed to fit the format)
  confidence = support of the winner / total weight of all readings
So a plate is only accepted when (nearly) all engines and variants agree.
A reading that fails counts against the winner - silence is not agreement.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from plate_ocr.engines import EngineReading, TemplateEngine, TesseractEngine
from plate_ocr.normalize import PlateCandidate, best_candidate, format_plate
from plate_ocr.preprocess import prepare

log = logging.getLogger(__name__)


@dataclass
class OcrConfig:
    accept_threshold: float = 0.85
    retry_threshold: float = 0.60
    engines: Sequence[str] = ("template", "tesseract")
    # which image variants each engine reads (tesseract is slow and weak on 'adaptive')
    engine_variants: Dict[str, Sequence[str]] = field(default_factory=lambda: {
        "template": ("gray", "contrast", "threshold", "adaptive"),
        "tesseract": ("gray", "contrast", "threshold"),
    })
    # tuned on synthetic scenes (tools/evaluate_ocr.py): 0 wrong accepts, ~75-80 % accepted
    # on the first frame in controlled conditions; re-tune on REAL photos
    engine_weights: Dict[str, float] = field(default_factory=lambda: {"template": 2.0, "tesseract": 0.75})
    # Tesseract's own confidence is optimistic for wrong readings; cap it
    tesseract_max_quality: float = 0.9
    fix_penalty: float = 0.9
    unknown_city_penalty: float = 0.85
    tesseract_cmd: Optional[str] = None


@dataclass
class Reading:
    engine: str
    variant: str
    raw_text: str
    plate: Optional[str]
    quality: float
    weight: float
    fixes: float = 0.0


@dataclass
class OcrResult:
    plate: Optional[str]
    confidence: float
    level: str                     # ACCEPT | RETRY | MANUAL
    status: str                    # OK | LOW_CONFIDENCE | INVALID_FORMAT | NO_TEXT
    raw_text: Optional[str]
    readings: List[Reading]
    processing_ms: float

    @property
    def accepted(self) -> bool:
        return self.level == "ACCEPT"

    @property
    def display(self) -> str:
        return format_plate(self.plate) if self.plate else "-"

    def to_dict(self) -> dict:
        return {
            "plate": self.plate, "confidence": round(self.confidence, 3), "level": self.level,
            "status": self.status, "rawText": self.raw_text, "processingMs": round(self.processing_ms, 1),
            "readings": [{"engine": r.engine, "variant": r.variant, "raw": r.raw_text, "plate": r.plate,
                          "quality": round(r.quality, 3)} for r in self.readings],
        }


class PlateReader:
    def __init__(self, config: Optional[OcrConfig] = None) -> None:
        self.config = config or OcrConfig()
        self._engines = []
        for name in self.config.engines:
            if name == "template":
                self._engines.append(TemplateEngine())
            elif name == "tesseract":
                if TesseractEngine.available(self.config.tesseract_cmd):
                    self._engines.append(TesseractEngine(tesseract_cmd=self.config.tesseract_cmd))
                else:
                    log.warning("tesseract not installed - running with the template engine only")
            else:
                raise ValueError("unknown OCR engine %r" % name)
        if not self._engines:
            raise RuntimeError("no OCR engine available")

    @property
    def engine_names(self) -> List[str]:
        return [e.name for e in self._engines]

    def level_for(self, confidence: float) -> str:
        if confidence >= self.config.accept_threshold:
            return "ACCEPT"
        if confidence >= self.config.retry_threshold:
            return "RETRY"
        return "MANUAL"

    def read(self, crop_bgr: np.ndarray, variants: Optional[Dict[str, np.ndarray]] = None) -> OcrResult:
        t0 = time.perf_counter()
        if variants is None:
            from plate_detector import make_variants
            variants = make_variants(crop_bgr)
        wanted = {v for e in self._engines for v in self.config.engine_variants.get(e.name, ())}
        prepared = prepare(crop_bgr, {k: v for k, v in variants.items() if k in wanted})
        readings: List[Reading] = []
        for engine in self._engines:
            for name in self.config.engine_variants.get(engine.name, ()):
                if name not in prepared:
                    continue
                img = prepared[name]
                try:
                    er = engine.read(img, name)
                except Exception:  # an engine crash must not stop the gate logic
                    log.exception("OCR engine %s failed on %s", engine.name, name)
                    er = EngineReading(engine.name, name, "", None)
                readings.append(self._score_reading(er))
        return self._vote(readings, (time.perf_counter() - t0) * 1000.0)

    # ----------------------------------------------------------------- voting
    def _score_reading(self, er: EngineReading) -> Reading:
        cfg = self.config
        weight = cfg.engine_weights.get(er.engine, 1.0)
        cand: Optional[PlateCandidate] = best_candidate(er.text) if er.text else None
        if cand is None:
            return Reading(er.engine, er.variant, er.text, None, 0.0, weight)
        q = er.confidence if er.confidence is not None else 0.7
        if er.engine == "tesseract":
            q = min(q, cfg.tesseract_max_quality)
        q *= cfg.fix_penalty ** cand.fix_cost
        if not cand.known_city:
            q *= cfg.unknown_city_penalty
        return Reading(er.engine, er.variant, er.text, cand.plate, float(q), weight, cand.fix_cost)

    def _vote(self, readings: List[Reading], ms: float) -> OcrResult:
        total = sum(r.weight for r in readings)
        support: Dict[str, float] = {}
        for r in readings:
            if r.plate:
                support[r.plate] = support.get(r.plate, 0.0) + r.weight * r.quality
        raw = next((r.raw_text for r in readings if r.raw_text), None)
        if not support:
            status = "INVALID_FORMAT" if raw else "NO_TEXT"
            return OcrResult(None, 0.0, "MANUAL", status, raw, readings, ms)
        plate = max(support, key=lambda p: support[p])
        confidence = float(min(1.0, support[plate] / total)) if total else 0.0
        level = self.level_for(confidence)
        status = "OK" if level == "ACCEPT" else "LOW_CONFIDENCE"
        raw = next((r.raw_text for r in readings if r.plate == plate), raw)
        return OcrResult(plate, confidence, level, status, raw, readings, ms)
