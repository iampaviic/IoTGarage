"""OCR engines. Each engine turns a prepared plate image into text + confidence.

TesseractEngine  general purpose OCR (any font); what the project plan asks for
TemplateEngine   compares every character with templates rendered from the same
                 font our plates are printed with (plate_detector/fonts). Very
                 accurate for our own printed plates, useless for other fonts.
The reader (reader.py) runs both and votes.
"""

from __future__ import annotations

import itertools
import logging
import re
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from plate_ocr.preprocess import binarize, segment_characters

log = logging.getLogger(__name__)

LETTERS = "ABCDEFGHIJKLMNOPRSTUVZ"  # no Q, W, X, Y on Croatian plates
DIGITS = "0123456789"


@dataclass
class EngineReading:
    engine: str
    variant: str
    text: str                       # raw text as read
    confidence: Optional[float]     # 0..1, None if the engine cannot tell
    char_scores: List[float] = field(default_factory=list)


class TesseractEngine:
    name = "tesseract"

    def __init__(self, psm: int = 7, tesseract_cmd: Optional[str] = None) -> None:
        import pytesseract

        self._pt = pytesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.psm = psm

    @staticmethod
    def available(tesseract_cmd: Optional[str] = None) -> bool:
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            return False
        return bool(tesseract_cmd or shutil.which("tesseract"))

    def read(self, image: np.ndarray, variant: str) -> EngineReading:
        # no whitelist: with a whitelist Tesseract 5 reports confidence 0
        data = self._pt.image_to_data(image, config="--oem 1 --psm %d" % self.psm,
                                      output_type=self._pt.Output.DICT)
        words = [(str(t), float(c)) for t, c in zip(data["text"], data["conf"]) if str(t).strip()]
        text = "".join(w for w, _ in words)
        conf = None
        if words:
            # weight by number of alphanumerics so a stray '-' does not dominate
            weights = [max(1, len(re.sub(r"[^A-Za-z0-9]", "", w))) for w, _ in words]
            conf = sum(max(0.0, c) * k for (_, c), k in zip(words, weights)) / (100.0 * sum(weights))
        return EngineReading(self.name, variant, text, conf)


class TemplateEngine:
    name = "template"
    BOX = (40, 56)  # w, h of the normalised character image

    def __init__(self) -> None:
        self.templates: Dict[str, List[np.ndarray]] = {}
        self._build_templates()

    def _normalise(self, binary_char: np.ndarray) -> np.ndarray:
        """Black-on-white crop -> fixed box, height-fitted, centred. Returns float32 ink map."""
        ink = (binary_char < 128).astype(np.uint8) * 255
        ys, xs = np.nonzero(ink)
        if len(xs) == 0:
            return np.zeros((self.BOX[1], self.BOX[0]), np.float32)
        ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = ink.shape
        bw, bh = self.BOX
        scale = (bh - 4) / float(h)
        nw = max(1, min(bw - 2, int(round(w * scale))))
        ink = cv2.resize(ink, (nw, bh - 4), interpolation=cv2.INTER_AREA)
        out = np.zeros((bh, bw), np.uint8)
        x0 = (bw - nw) // 2
        out[2:bh - 2, x0:x0 + nw] = ink
        out = cv2.GaussianBlur(out, (3, 3), 0)
        return out.astype(np.float32)

    def _build_templates(self) -> None:
        from plate_detector.synth import _text_image  # same font + rendering as printed plates

        for ch in LETTERS + DIGITS:
            variants = []
            for condense in (0.62, 0.78, 0.92):
                img = np.array(_text_image(ch, 60, condense))
                binary = np.where(img > 127, 0, 255).astype(np.uint8)  # black text on white
                for op in (None, "erode", "dilate"):
                    b = binary
                    if op == "erode":
                        b = cv2.dilate(binary, np.ones((3, 3), np.uint8))  # white grows -> thinner ink
                    elif op == "dilate":
                        b = cv2.erode(binary, np.ones((3, 3), np.uint8))
                    variants.append(self._normalise(b))
            self.templates[ch] = variants

    @staticmethod
    def _ncc(a: np.ndarray, b: np.ndarray) -> float:
        a = a - a.mean()
        b = b - b.mean()
        den = float(np.sqrt((a * a).sum() * (b * b).sum()))
        return float((a * b).sum() / den) if den > 0 else 0.0

    def _scores(self, char_img: np.ndarray, alphabet: str) -> List[Tuple[float, str]]:
        n = self._normalise(char_img)
        res = [(max(self._ncc(n, t) for t in self.templates[ch]), ch) for ch in alphabet]
        return sorted(res, reverse=True)

    def read(self, image: np.ndarray, variant: str) -> EngineReading:
        binary = binarize(image)
        boxes = segment_characters(image)
        if not 6 <= len(boxes) <= 8:
            return EngineReading(self.name, variant, "", None)
        chars = [binary[y:y + h, x:x + w] for x, y, w, h in boxes]
        letter_scores = [self._scores(c, LETTERS) for c in chars]
        digit_scores = [self._scores(c, DIGITS) for c in chars]
        best = None
        n = len(chars)
        for n_digits, n_letters in itertools.product((3, 4), (1, 2)):
            if 2 + n_digits + n_letters != n:
                continue
            classes = "LL" + "D" * n_digits + "L" * n_letters
            picks = [(letter_scores if c == "L" else digit_scores)[i][0] for i, c in enumerate(classes)]
            total = sum(s for s, _ in picks)
            if best is None or total > best[0]:
                best = (total, picks, classes)
        if best is None:
            return EngineReading(self.name, variant, "", None)
        _, picks, classes = best
        text = "".join(ch for _, ch in picks)
        # per-character confidence: similarity, reduced when the runner-up is close
        char_conf = []
        for i, (score, ch) in enumerate(picks):
            alts = (letter_scores if classes[i] == "L" else digit_scores)[i]
            margin = score - alts[1][0] if len(alts) > 1 else score
            char_conf.append(float(np.clip((score - 0.45) / 0.4, 0, 1) * np.clip(margin / 0.08, 0.3, 1)))
        conf = float(min(char_conf) * 0.5 + np.mean(char_conf) * 0.5)
        return EngineReading(self.name, variant, text, conf, char_conf)
