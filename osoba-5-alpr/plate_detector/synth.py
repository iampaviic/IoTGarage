"""Synthetic Croatian-style licence plates and camera scenes.

Used for
  * printing plates for the model cars (tools/generate_plates.py)
  * building a labelled synthetic test set before real photos exist
  * the simulated camera of the edge service (no hardware needed)

All plates are FICTIONAL test plates. Geometry follows the real 520 x 110 mm
plate: blue EU band with "HR", city code, a simplified red/white chequered
shield, 3-4 digits, a dash and 1-2 letters, e.g. "ZG 1234-AB".
"""

from __future__ import annotations

import math
import os
import random
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PLATE_W_MM = 520
PLATE_H_MM = 110
PLATE_ASPECT = PLATE_W_MM / PLATE_H_MM

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf")
EU_BLUE = (0, 51, 153)
EU_YELLOW = (255, 204, 0)
SHIELD_RED = (200, 16, 46)

PLATE_RE = re.compile(r"^([A-Z]{2})(\d{3,4})([A-Z]{1,2})$")
CITY_CODES = ["ZG", "ST", "RI", "OS", "ZD", "PU", "KA", "SB", "DU", "BJ", "KC", "SK", "VK", "VU", "GS", "KR"]
SUFFIX_LETTERS = "ABCDEFGHIJKLMNOPRSTUVZ"


def split_plate(plate: str) -> Tuple[str, str, str]:
    m = PLATE_RE.match(plate)
    if not m:
        raise ValueError("plate must look like ZG1234AB (city, 3-4 digits, 1-2 letters): %r" % plate)
    return m.group(1), m.group(2), m.group(3)


def random_plate(rng: random.Random) -> str:
    return (rng.choice(CITY_CODES)
            + "".join(rng.choice("0123456789") for _ in range(rng.choice((3, 4))))
            + "".join(rng.choice(SUFFIX_LETTERS) for _ in range(rng.choice((1, 2)))))


def format_plate(plate: str) -> str:
    """'ZG1234AB' -> 'ZG 1234-AB' (how it is printed)."""
    city, digits, letters = split_plate(plate)
    return "%s %s-%s" % (city, digits, letters)


# --------------------------------------------------------------------- plate
def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, px)


def _glyph(ch: str, cap_height_px: int, condense: float) -> Image.Image:
    """One character as a tight white-on-black mask, exactly cap_height_px high.
    Every glyph is scaled to the same height (like real plate lettering), which
    also keeps descenders (e.g. 'J') inside the line."""
    font = _font(max(8, int(cap_height_px * 1.6)))
    x0, y0, x1, y1 = font.getbbox(ch)
    img = Image.new("L", (x1 - x0 + 4, y1 - y0 + 4), 0)
    ImageDraw.Draw(img).text((2 - x0, 2 - y0), ch, font=font, fill=255)
    bbox = img.getbbox() or (0, 0, 1, 1)
    img = img.crop(bbox)
    w = max(1, int(round(img.width * cap_height_px / float(img.height) * condense)))
    return img.resize((w, cap_height_px), Image.LANCZOS)


def _text_image(text: str, cap_height_px: int, condense: float, spacing: float = 0.12) -> Image.Image:
    """Render text as a tight mask: uniform glyph height, fixed gap between glyphs
    (gap = spacing * cap height) so neighbouring characters never touch."""
    glyphs = [_glyph(ch, cap_height_px, condense) for ch in text]
    gap = int(round(spacing * cap_height_px))
    width = sum(g.width for g in glyphs) + gap * (len(glyphs) - 1)
    img = Image.new("L", (max(1, width), cap_height_px), 0)
    x = 0
    for g in glyphs:
        img.paste(g, (x, 0))
        x += g.width + gap
    return img


def _star(cx: float, cy: float, r: float) -> List[Tuple[float, float]]:
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def _shield(img: Image.Image, x: float, y: float, w: float, h: float) -> None:
    """Simplified Croatian chequered shield: 5 x 5 red/white fields, round bottom."""
    W, H = max(2, int(round(w))), max(2, int(round(h)))
    board = Image.new("RGB", (W, H), (255, 255, 255))
    bd = ImageDraw.Draw(board)
    n = 5
    fw, fh = W / float(n), H / float(n)
    for r in range(n):
        for c in range(n):
            if (r + c) % 2 == 0:
                bd.rectangle([c * fw, r * fh, (c + 1) * fw, (r + 1) * fh], fill=SHIELD_RED)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 0, W, H * 0.55], fill=255)
    md.ellipse([0, H * 0.1, W, H], fill=255)
    img.paste(board, (int(round(x)), int(round(y))), mask)


def render_plate(plate: str, px_per_mm: float = 2.0, shield: bool = True, border: bool = True) -> np.ndarray:
    """Render a plate as an RGB numpy array of size (110*px_per_mm, 520*px_per_mm)."""
    city, digits, letters = split_plate(plate)
    s = px_per_mm
    W, H = int(round(PLATE_W_MM * s)), int(round(PLATE_H_MM * s))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    # blue EU band with stars and "HR"
    band_w = 42 * s
    d.rectangle([0, 0, band_w, H], fill=EU_BLUE)
    for i in range(12):
        a = 2 * math.pi * i / 12
        d.polygon(_star(band_w / 2 + 11 * s * math.cos(a), 32 * s + 11 * s * math.sin(a), 2.4 * s), fill=EU_YELLOW)
    hr = _text_image("HR", int(17 * s), 0.9)
    img.paste((255, 255, 255), (int(band_w / 2 - hr.width / 2), int(74 * s)), hr)

    # text line: CITY [shield] DIGITS - LETTERS
    cap = int(round(70 * s))
    condense = 0.78
    parts = [_text_image(city, cap, condense)]
    gaps = [7 * s]
    shield_w = 24 * s if shield else 10 * s
    digits_img = _text_image(digits, cap, condense)
    dash_w, dash_h = 12 * s, 7 * s
    letters_img = _text_image(letters, cap, condense)
    total = parts[0].width + gaps[0] + shield_w + 7 * s + digits_img.width + 5 * s + dash_w + 5 * s + letters_img.width
    avail = W - band_w - 16 * s
    k = min(1.0, avail / total)
    if k < 1.0:  # long plates: squeeze horizontally
        parts[0] = parts[0].resize((int(parts[0].width * k), parts[0].height), Image.LANCZOS)
        digits_img = digits_img.resize((int(digits_img.width * k), digits_img.height), Image.LANCZOS)
        letters_img = letters_img.resize((int(letters_img.width * k), letters_img.height), Image.LANCZOS)
        shield_w, dash_w = shield_w * k, dash_w * k
        total = total * k
    x = band_w + 8 * s + (avail - total) / 2
    y = (H - parts[0].height) / 2
    img.paste((0, 0, 0), (int(x), int(y)), parts[0])
    x += parts[0].width + 7 * s * k
    if shield:
        _shield(img, x, H * 0.22, shield_w, H * 0.56)
    x += shield_w + 7 * s * k
    img.paste((0, 0, 0), (int(x), int(y)), digits_img)
    x += digits_img.width + 5 * s * k
    d.rectangle([x, H / 2 - dash_h / 2, x + dash_w, H / 2 + dash_h / 2], fill=(0, 0, 0))
    x += dash_w + 5 * s * k
    img.paste((0, 0, 0), (int(x), int(y)), letters_img)

    if border:
        bw = max(1, int(round(2.5 * s)))
        d.rounded_rectangle([bw / 2, bw / 2, W - 1 - bw / 2, H - 1 - bw / 2], radius=int(6 * s),
                            outline=(0, 0, 0), width=bw)
    return np.array(img)


# --------------------------------------------------------------------- scenes
@dataclass
class SceneParams:
    width: int = 1280
    height: int = 720
    plate_width_frac: Tuple[float, float] = (0.18, 0.40)  # plate width / image width
    max_roll_deg: float = 8.0
    max_yaw_deg: float = 30.0
    max_pitch_deg: float = 20.0
    brightness: Tuple[float, float] = (0.6, 1.25)
    blur_prob: float = 0.3
    noise_sigma: Tuple[float, float] = (0.0, 8.0)
    distractors: int = 4
    jpeg_quality: Tuple[int, int] = (60, 95)
    region: Optional[Tuple[float, float, float, float]] = None  # plate centre inside (x0, y0, x1, y1) fractions

    @classmethod
    def controlled(cls) -> "SceneParams":
        """Conditions we can guarantee on the model: fixed camera, stop line,
        diffuse light, plate roughly perpendicular to the camera."""
        return cls(plate_width_frac=(0.22, 0.38), max_roll_deg=4, max_yaw_deg=15, max_pitch_deg=12,
                   brightness=(0.8, 1.15), blur_prob=0.1, noise_sigma=(0, 4), distractors=3)

    @classmethod
    def fixed_camera(cls, region: Optional[Tuple[float, float, float, float]] = None) -> "SceneParams":
        """What the real, fixed camera sees when a car stops at the stop line."""
        return cls(plate_width_frac=(0.26, 0.32), max_roll_deg=2, max_yaw_deg=8, max_pitch_deg=6,
                   brightness=(0.9, 1.1), blur_prob=0.05, noise_sigma=(0, 3), distractors=2, region=region)

    @classmethod
    def hard(cls) -> "SceneParams":
        return cls(plate_width_frac=(0.10, 0.45), max_roll_deg=15, max_yaw_deg=45, max_pitch_deg=30,
                   brightness=(0.35, 1.4), blur_prob=0.6, noise_sigma=(2, 16), distractors=8,
                   jpeg_quality=(30, 85))


@dataclass
class Scene:
    image: np.ndarray            # BGR
    plate: str
    corners: np.ndarray          # 4x2 float32: TL, TR, BR, BL in image pixels
    params: dict


def _background(rng: random.Random, w: int, h: int) -> np.ndarray:
    base = rng.randint(60, 190)
    img = np.full((h, w, 3), base, np.uint8)
    # floor gradient + texture
    grad = np.linspace(rng.uniform(-40, 0), rng.uniform(0, 40), h, dtype=np.float32)[:, None, None]
    img = np.clip(img.astype(np.float32) + grad, 0, 255)
    nrs = np.random.RandomState(rng.randint(0, 2 ** 31 - 1))
    texture = cv2.GaussianBlur(nrs.normal(0, 18, (h // 8, w // 8)).astype(np.float32), (0, 0), 1.5)
    img += cv2.resize(texture, (w, h))[:, :, None]
    tint = np.array([rng.uniform(0.85, 1.15) for _ in range(3)], np.float32)
    return np.clip(img * tint, 0, 255).astype(np.uint8)


def _distractor(rng: random.Random, img: np.ndarray) -> None:
    h, w = img.shape[:2]
    kind = rng.choice(["rect", "stripes", "lane", "text", "white_rect"])
    x, y = rng.randrange(w), rng.randrange(h)
    if kind == "rect":
        color = tuple(rng.randrange(256) for _ in range(3))
        cv2.rectangle(img, (x, y), (x + rng.randint(30, 300), y + rng.randint(30, 200)), color, -1)
    elif kind == "stripes":  # barrier arm: red/white stripes
        length, thick = rng.randint(200, 600), rng.randint(10, 25)
        angle = rng.uniform(-0.3, 0.3)
        for i in range(0, length, 40):
            p1 = (int(x + i * math.cos(angle)), int(y + i * math.sin(angle)))
            p2 = (int(x + (i + 40) * math.cos(angle)), int(y + (i + 40) * math.sin(angle)))
            cv2.line(img, p1, p2, (40, 40, 220) if (i // 40) % 2 else (240, 240, 240), thick)
    elif kind == "lane":
        cv2.line(img, (x, 0), (x + rng.randint(-200, 200), h), (230, 230, 230), rng.randint(4, 12))
    elif kind == "text":
        txt = "".join(rng.choice("ABCDEFGHJKLMNPRSTUVZ0123456789 ") for _ in range(rng.randint(3, 8)))
        cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, rng.uniform(0.8, 2.5), (20, 20, 20), rng.randint(2, 5))
    else:  # white sign without characters (looks like a plate, must be rejected)
        cw, ch = rng.randint(80, 260), rng.randint(20, 70)
        cv2.rectangle(img, (x, y), (x + cw, y + ch), (245, 245, 245), -1)
        cv2.rectangle(img, (x, y), (x + cw, y + ch), (10, 10, 10), 2)


def _project_corners(rng: random.Random, p: SceneParams) -> np.ndarray:
    """Random 3D pose of the plate rectangle projected with a pinhole camera."""
    w_frac = rng.uniform(*p.plate_width_frac)
    plate_w = w_frac * p.width
    plate_h = plate_w / PLATE_ASPECT
    roll = math.radians(rng.uniform(-p.max_roll_deg, p.max_roll_deg))
    yaw = math.radians(rng.uniform(-p.max_yaw_deg, p.max_yaw_deg))
    pitch = math.radians(rng.uniform(-p.max_pitch_deg, p.max_pitch_deg))
    f = p.width * 1.0  # focal length in pixels (about 53 deg horizontal FOV)
    z0 = f  # plate at distance where 1 unit ~ 1 px
    pts = np.array([[-plate_w / 2, -plate_h / 2, 0], [plate_w / 2, -plate_h / 2, 0],
                    [plate_w / 2, plate_h / 2, 0], [-plate_w / 2, plate_h / 2, 0]], np.float64)
    rx = np.array([[1, 0, 0], [0, math.cos(pitch), -math.sin(pitch)], [0, math.sin(pitch), math.cos(pitch)]])
    ry = np.array([[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0], [-math.sin(yaw), 0, math.cos(yaw)]])
    rz = np.array([[math.cos(roll), -math.sin(roll), 0], [math.sin(roll), math.cos(roll), 0], [0, 0, 1]])
    world = pts @ (rz @ ry @ rx).T + np.array([0, 0, z0])
    proj = world[:, :2] * (f / world[:, 2:3])
    # random placement fully inside the image (or the requested region), with margin
    mn, mx = proj.min(axis=0), proj.max(axis=0)
    margin = 20
    x_lo, x_hi, y_lo, y_hi = margin - mn[0], p.width - margin - mx[0], margin - mn[1], p.height - margin - mx[1]
    if p.region is not None:
        rx0, ry0, rx1, ry1 = p.region
        x_lo, x_hi = max(x_lo, rx0 * p.width - mn[0] + margin), min(x_hi, rx1 * p.width - mx[0] - margin)
        y_lo, y_hi = max(y_lo, ry0 * p.height - mn[1] + margin), min(y_hi, ry1 * p.height - mx[1] - margin)
    cx = rng.uniform(x_lo, x_hi) if x_hi > x_lo else (x_lo + x_hi) / 2
    cy = rng.uniform(y_lo, y_hi) if y_hi > y_lo else (y_lo + y_hi) / 2
    return (proj + np.array([cx, cy])).astype(np.float32)


def render_scene(plate: Optional[str] = None, rng: Optional[random.Random] = None,
                 params: Optional[SceneParams] = None, quality: str = "good",
                 with_plate: bool = True) -> Scene:
    """Render a camera frame containing one plate on a 'car' plus distractors.

    quality: good | poor | unreadable  (used by the simulated camera)
    with_plate=False renders an empty scene (negative example, corners are zeros)
    """
    rng = rng or random.Random()
    p = params or SceneParams.controlled()
    if quality == "poor":
        p = SceneParams.hard()
    plate = plate or random_plate(rng)
    img = _background(rng, p.width, p.height)
    for _ in range(rng.randint(0, p.distractors)):
        _distractor(rng, img)

    corners = _project_corners(rng, p)
    if not with_plate:
        img = img.astype(np.float32) * rng.uniform(*p.brightness)
        out = np.clip(img, 0, 255).astype(np.uint8)
        return Scene(image=out, plate="", corners=np.zeros((4, 2), np.float32), params={"quality": "empty"})
    plate_rgb = render_plate(plate, px_per_mm=2.0, shield=True)
    ph, pw = plate_rgb.shape[:2]
    src = np.array([[0, 0], [pw - 1, 0], [pw - 1, ph - 1], [0, ph - 1]], np.float32)
    H = cv2.getPerspectiveTransform(src, corners)

    # the "car" around the plate: a coloured body larger than the plate
    car_color = tuple(int(c) for c in rng.choice([(30, 30, 30), (40, 40, 160), (160, 60, 30), (200, 200, 200),
                                                    (40, 120, 40), (20, 20, 90), (120, 120, 120)]))
    body = np.array([[-0.35, -1.6], [1.35, -1.6], [1.35, 1.9], [-0.35, 1.9]], np.float32) * np.array([pw, ph], np.float32)
    body_img = cv2.perspectiveTransform(body[None], H)[0]
    cv2.fillConvexPoly(img, body_img.astype(np.int32), car_color, lineType=cv2.LINE_AA)

    warped = cv2.warpPerspective(cv2.cvtColor(plate_rgb, cv2.COLOR_RGB2BGR), H, (p.width, p.height),
                                 flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.full((ph, pw), 255, np.uint8), H, (p.width, p.height))
    m = (mask.astype(np.float32) / 255.0)[:, :, None]
    img = (img.astype(np.float32) * (1 - m) + warped.astype(np.float32) * m)

    # lighting: global brightness, directional shadow, glare spot
    img *= rng.uniform(*p.brightness)
    if rng.random() < 0.4:
        gx = np.linspace(rng.uniform(0.6, 1.0), rng.uniform(1.0, 1.2), p.width, dtype=np.float32)[None, :, None]
        img *= gx
    if quality == "unreadable":
        img = cv2.GaussianBlur(img, (0, 0), 9)
    elif rng.random() < p.blur_prob:
        k = rng.choice([3, 5, 7])
        img = cv2.GaussianBlur(img, (k, k), 0) if rng.random() < 0.5 else _motion_blur(img, k)
    sigma = rng.uniform(*p.noise_sigma)
    if sigma > 0:
        img += np.random.RandomState(rng.randint(0, 2 ** 31 - 1)).normal(0, sigma, img.shape).astype(np.float32)
    out = np.clip(img, 0, 255).astype(np.uint8)
    q = rng.randint(*p.jpeg_quality)
    ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])
    out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return Scene(image=out, plate=plate, corners=corners,
                 params={"quality": quality, "jpeg": q, "noise": round(sigma, 1)})


def _motion_blur(img: np.ndarray, k: int) -> np.ndarray:
    kernel = np.zeros((k, k), np.float32)
    kernel[k // 2, :] = 1.0 / k
    return cv2.filter2D(img, -1, kernel)


def plates_for_demo(n: int = 8, seed: int = 7) -> List[str]:
    """Deterministic list of fictional demo plates."""
    rng = random.Random(seed)
    out: List[str] = []
    while len(out) < n:
        p = random_plate(rng)
        if p not in out:
            out.append(p)
    return out


def contact_sheet(plates: Sequence[str], px_per_mm: float = 1.0) -> np.ndarray:
    tiles = [render_plate(p, px_per_mm) for p in plates]
    h = sum(t.shape[0] + 10 for t in tiles)
    sheet = np.full((h, tiles[0].shape[1] + 20, 3), 230, np.uint8)
    y = 5
    for t in tiles:
        sheet[y:y + t.shape[0], 10:10 + t.shape[1]] = t
        y += t.shape[0] + 10
    return sheet
