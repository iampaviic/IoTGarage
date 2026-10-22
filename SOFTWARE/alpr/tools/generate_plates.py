"""Print fictional plates for the model cars at exact size.

    python tools/generate_plates.py                          # 8 demo plates, 60 mm wide, 2 copies each
    python tools/generate_plates.py --plates ZG1234AB ST555B --width-mm 70
    python tools/generate_plates.py --count 12 --out plates_print

Outputs (in --out):
    plates_A4.pdf      print at 100 % / "actual size" (NOT "fit to page")
    plates_A4.png      the same page as an image
    png/<PLATE>.png    one high-resolution image per plate
    plates.txt         list of the plates (for the allow-list)

Check the 50 mm ruler on the sheet with a real ruler after printing.
Laminate or use matt photo paper: glossy paper reflects light into the camera.
"""

from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plate_detector.synth import FONT_PATH, PLATE_ASPECT, format_plate, plates_for_demo, render_plate, split_plate  # noqa: E402

DPI = 300
A4_MM = (210, 297)


def mm(v: float) -> int:
    return int(round(v / 25.4 * DPI))


def build_sheet(plates, width_mm: float, copies: int, shield: bool) -> Image.Image:
    page = Image.new("RGB", (mm(A4_MM[0]), mm(A4_MM[1])), "white")
    d = ImageDraw.Draw(page)
    font = ImageFont.truetype(FONT_PATH, mm(3))
    small = ImageFont.truetype(FONT_PATH, mm(2.2))
    height_mm = width_mm / PLATE_ASPECT
    margin, gap_x, gap_y = 12.0, 8.0, 9.0
    cols = max(1, int((A4_MM[0] - 2 * margin + gap_x) // (width_mm + gap_x)))

    d.text((mm(margin), mm(5)), "IoT Garaza - testne (izmisljene) registracije, plocica %.0f x %.1f mm" % (width_mm, height_mm),
           fill="black", font=font)
    # 50 mm calibration ruler
    y_r = mm(A4_MM[1] - 10)
    d.line([(mm(margin), y_r), (mm(margin + 50), y_r)], fill="black", width=mm(0.4))
    for t in range(0, 51, 10):
        d.line([(mm(margin + t), y_r - mm(2)), (mm(margin + t), y_r)], fill="black", width=mm(0.3))
    d.text((mm(margin + 53), y_r - mm(3)), "kontrola: 50 mm", fill="black", font=small)

    items = [p for p in plates for _ in range(copies)]
    x0, y0 = margin, 14.0
    for i, plate in enumerate(items):
        r, c = divmod(i, cols)
        x = x0 + c * (width_mm + gap_x)
        y = y0 + r * (height_mm + gap_y)
        if y + height_mm > A4_MM[1] - 16:
            print("page full, %d plates not placed" % (len(items) - i))
            break
        px_per_mm = DPI / 25.4
        img = Image.fromarray(render_plate(plate, px_per_mm=px_per_mm * width_mm / 520.0, shield=shield))
        img = img.resize((mm(width_mm), mm(height_mm)), Image.LANCZOS)
        page.paste(img, (mm(x), mm(y)))
        # dashed cut marks
        for dx in (0, width_mm):
            d.line([(mm(x + dx), mm(y - 2)), (mm(x + dx), mm(y - 0.5))], fill=(150, 150, 150), width=2)
            d.line([(mm(x + dx), mm(y + height_mm + 0.5)), (mm(x + dx), mm(y + height_mm + 2))], fill=(150, 150, 150), width=2)
        d.text((mm(x), mm(y + height_mm + 2.2)), format_plate(plate), fill=(90, 90, 90), font=small)
    return page


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plates", nargs="*", help="plates like ZG1234AB (default: deterministic demo set)")
    ap.add_argument("--count", type=int, default=8, help="how many demo plates if --plates is not given")
    ap.add_argument("--width-mm", type=float, default=60.0, help="printed plate width (real plate: 520 mm)")
    ap.add_argument("--copies", type=int, default=2, help="copies per plate (front + rear = 2)")
    ap.add_argument("--no-shield", action="store_true", help="omit the chequered shield")
    ap.add_argument("--out", default="plates_print")
    args = ap.parse_args(argv)

    plates = [p.upper().replace(" ", "").replace("-", "") for p in (args.plates or plates_for_demo(args.count))]
    for p in plates:
        split_plate(p)  # validates format
    os.makedirs(os.path.join(args.out, "png"), exist_ok=True)
    for p in plates:
        cv2.imwrite(os.path.join(args.out, "png", p + ".png"),
                    cv2.cvtColor(render_plate(p, px_per_mm=4, shield=not args.no_shield), cv2.COLOR_RGB2BGR))
    page = build_sheet(plates, args.width_mm, args.copies, not args.no_shield)
    page.save(os.path.join(args.out, "plates_A4.pdf"), resolution=DPI)
    page.save(os.path.join(args.out, "plates_A4.png"))
    with open(os.path.join(args.out, "plates.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(plates) + "\n")
    print("wrote %d plates to %s/ (print plates_A4.pdf at 100 %%)" % (len(plates), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
