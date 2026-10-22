import random

import pytest

from plate_ocr import PlateReader, best_candidate, candidates, clean, format_plate, is_valid
from plate_ocr.reader import OcrConfig


@pytest.mark.parametrize("raw,expected", [
    ("ZG 1234-AB", "ZG1234AB"),
    ("zg1234ab", "ZG1234AB"),
    ("Z6 1234-A8", "ZG1234AB"),     # letter positions: 6->G, 8->B
    ("ZG 12O4-AB", "ZG1204AB"),     # digit position: O->0
    ("ZG 1234-A8", "ZG1234AB"),     # letter position: 8->B
    ("ZGH1234AB", "ZG1234AB"),      # shield read as 'H' and dropped
    ("ZG|1234-AB", "ZG1234AB"),
    ("ST555-B", "ST555B"),
    ("ČK 123-A", "CK123A"),          # diacritics folded
    ("ŠI 4567-ZZ", "SI4567ZZ"),
])
def test_normalisation(raw, expected):
    assert best_candidate(raw).plate == expected


def test_substitutions_are_counted():
    exact = best_candidate("ZG1234AB")
    fixed = best_candidate("Z61234A8")
    assert exact.substitutions == 0 and fixed.substitutions == 2
    assert fixed.cost > exact.cost


def test_unknown_city_costs_more():
    assert best_candidate("XY1234AB") is None or not best_candidate("XY1234AB").known_city
    assert best_candidate("ZG1234AB").known_city


@pytest.mark.parametrize("raw", ["", "HELLO", "1234", "ZG123456AB", "XQ99WW"])
def test_garbage_is_rejected(raw):
    assert best_candidate(raw) is None


def test_helpers():
    assert clean(" zg-12 ") == "ZG12"
    assert is_valid("ZG1234AB") and not is_valid("ZG1234ABC")
    assert is_valid("ZG1234AB", strict_city=True) and not is_valid("XX1234AB", strict_city=True)
    assert format_plate("ZG1234AB") == "ZG 1234-AB"
    assert len(candidates("ZG1234AB")) >= 1


@pytest.fixture(scope="module")
def reader():
    return PlateReader(OcrConfig(engines=("template",)))  # template engine needs no tesseract


def test_reads_rendered_plate(reader):
    from plate_detector import make_variants
    from plate_detector.synth import render_plate
    import cv2

    for plate in ["ZG1234AB", "ST555B", "RI0913T", "BJ4456JK"]:
        crop = cv2.cvtColor(render_plate(plate, px_per_mm=1.0), cv2.COLOR_RGB2BGR)
        r = reader.read(crop, make_variants(crop))
        assert r.plate == plate
        assert r.accepted and r.confidence >= 0.85


def test_reads_detected_plates_in_scenes(reader):
    from plate_detector import PlateDetector
    from plate_detector.synth import SceneParams, render_scene

    det = PlateDetector()
    rng = random.Random(5)
    correct = wrong_accepts = 0
    for _ in range(15):
        scene = render_scene(rng=rng, params=SceneParams.controlled())
        d = det.detect(scene.image)
        if not d.found:
            continue
        r = reader.read(d.crop, d.variants)
        correct += r.plate == scene.plate
        wrong_accepts += r.accepted and r.plate != scene.plate
    assert correct >= 12
    assert wrong_accepts == 0


def test_blank_plate_is_not_accepted(reader):
    import numpy as np

    blank = np.full((110, 520, 3), 255, np.uint8)
    r = reader.read(blank)
    assert r.plate is None and r.level == "MANUAL" and r.status in ("NO_TEXT", "INVALID_FORMAT")


def test_tesseract_engine_if_installed():
    from plate_ocr.engines import TesseractEngine

    if not TesseractEngine.available():
        pytest.skip("tesseract not installed")
    import cv2
    from plate_detector import make_variants
    from plate_detector.synth import render_plate

    crop = cv2.cvtColor(render_plate("ZG1234AB", px_per_mm=1.0), cv2.COLOR_RGB2BGR)
    r = PlateReader().read(crop, make_variants(crop))
    assert r.plate == "ZG1234AB"
    assert {x.engine for x in r.readings} == {"template", "tesseract"}
