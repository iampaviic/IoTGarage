import random

import numpy as np
import pytest

from plate_detector import DetectorConfig, PlateDetector
from plate_detector.geometry import expand_quad, order_corners, quad_aspect, quad_iou
from plate_detector.synth import SceneParams, format_plate, render_plate, render_scene, split_plate


@pytest.fixture(scope="module")
def detector():
    return PlateDetector()


def test_render_plate_size_and_colours():
    img = render_plate("ZG1234AB", px_per_mm=1.0)
    assert img.shape == (110, 520, 3)
    # blue EU band on the left, white background on the right side
    assert img[55, 5, 2] > 120 and img[55, 5, 0] < 60
    assert img[8, 500].min() > 200


def test_plate_format_helpers():
    assert split_plate("ZG1234AB") == ("ZG", "1234", "AB")
    assert format_plate("ST555B") == "ST 555-B"
    with pytest.raises(ValueError):
        split_plate("ZG-12")


def test_order_corners_any_input_order():
    tl, tr, br, bl = [10, 10], [110, 12], [108, 40], [9, 38]
    shuffled = np.array([br, tl, bl, tr], np.float32)
    assert np.allclose(order_corners(shuffled), [tl, tr, br, bl])


def test_quad_iou_and_aspect():
    a = np.array([[0, 0], [100, 0], [100, 20], [0, 20]], np.float32)
    assert quad_iou(a, a) == pytest.approx(1.0)
    assert quad_iou(a, a + [50, 0]) == pytest.approx(1 / 3, abs=0.01)
    assert quad_aspect(a) == pytest.approx(5.0)
    assert quad_aspect(expand_quad(a, 2.0, 1.0)) == pytest.approx(10.0)


def test_detects_plate_in_controlled_scenes(detector):
    rng = random.Random(2024)
    hits = 0
    for _ in range(20):
        scene = render_scene(rng=rng, params=SceneParams.controlled())
        r = detector.detect(scene.image)
        if r.found and quad_iou(r.corners, scene.corners) >= 0.5:
            hits += 1
            assert r.crop.shape == (110, 520, 3)
            assert {"gray", "contrast", "threshold", "adaptive"} <= set(r.variants)
            assert 0.0 <= r.confidence <= 1.0
    assert hits >= 19


def test_empty_scene_mostly_not_detected(detector):
    rng = random.Random(7)
    found = sum(detector.detect(render_scene(rng=rng, with_plate=False).image).found for _ in range(20))
    assert found <= 3


def test_roi_limits_search(detector):
    scene = render_scene(rng=random.Random(3), params=SceneParams.controlled())
    xs = scene.corners[:, 0] / scene.image.shape[1]
    # ROI that does not contain the plate
    roi = (0.0, 0.0, 0.05, 0.05) if xs.min() > 0.1 else (0.9, 0.9, 1.0, 1.0)
    assert not detector.detect(scene.image, roi=roi).found
    # ROI around the plate gives the same corners in full-frame coordinates
    full = detector.detect(scene.image)
    pad = 0.08
    roi = (max(0, xs.min() - pad), max(0, scene.corners[:, 1].min() / scene.image.shape[0] - pad),
           min(1, xs.max() + pad), min(1, scene.corners[:, 1].max() / scene.image.shape[0] + pad))
    inside = detector.detect(scene.image, roi=roi)
    assert inside.found and quad_iou(inside.corners, full.corners) > 0.8


def test_result_serialisable(detector):
    import json
    r = detector.detect(render_scene(rng=random.Random(1)).image)
    json.dumps(r.to_dict())


def test_min_confidence_config():
    scene = render_scene(rng=random.Random(4))
    assert not PlateDetector(DetectorConfig(min_confidence=1.01)).detect(scene.image).found
