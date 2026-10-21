"""Parametric floor plan of the model garage (all dimensions in mm, 1:1).

    python tlocrt.py                         # 1:24 cars, 6 spots -> ../nacrt/
    python tlocrt.py --scale 32 --spots 4    # smaller model
    python tlocrt.py --print-tiles           # also A4 tiles (PDF) to glue together as a template

Outputs (in --out):
    tlocrt.svg        exact 1:1 drawing - print at 100 % (plotter / print shop) or use as a cutting template
    tlocrt.png        preview
    tlocrt_A4.pdf     (--print-tiles) the plan split into A4 pages with 10 mm overlap and alignment marks
    spots.json        spot centres as fractions of the base -> provision.py --positions (ThingsBoard)
    dimenzije.md      table of all dimensions for the build log

Layout (top view, north = up):
    +-----------------------------------------------+
    | P01 | P02 | P03 | P04 | P05 | P06 |  <- HC-SR04 above every spot (ceiling bridge)
    |---------------- aisle -----------------------|
    |   [cam A] entrance ^ |island| exit lane v     |   cam A: inside, on a bridge over the lane,
    |                    |      |                   |          looks at the waiting car's FRONT plate
    |===== barrier ======|  ESP |===== barrier =====|
    |   stop line        |      |   [cam B]         |   cam B: outside, looks at the leaving car's FRONT plate
    |                    street                     |
    +-----------------------------------------------+
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

# real-world sizes in metres, divided by the scale
REAL = {"spot_w": 2.6, "spot_d": 5.3, "aisle": 4.8, "lane_w": 3.2, "island": 1.6}


def layout(scale: int, spots: int) -> dict:
    s = lambda metres: round(metres * 1000.0 / scale)  # noqa: E731
    m = 20
    spot_w, spot_d = s(REAL["spot_w"]), s(REAL["spot_d"])
    lane_w, island = s(REAL["lane_w"]), s(REAL["island"])
    aisle = s(REAL["aisle"])
    car_len = s(4.4)
    cam_behind = 200                     # camera distance behind the barrier line (see kamera_kalkulator.py)
    outside = cam_behind + 60            # lane length outside the barrier
    inside = 100                         # lane length inside; the entrance camera bridge may stand over the aisle
    width = max(spots * spot_w, 2 * lane_w + island + 2 * 60) + 2 * m
    height = m + spot_d + aisle + inside + outside + m
    L = {"scale": scale, "spots": spots, "W": width, "H": height, "margin": m, "spot_w": spot_w, "spot_d": spot_d,
         "aisle": aisle, "lane_w": lane_w, "island": island, "car_len": car_len, "cam_behind": cam_behind}
    x0 = (width - spots * spot_w) / 2
    L["spot_rects"] = [(x0 + i * spot_w, m, spot_w, spot_d) for i in range(spots)]
    L["aisle_rect"] = (m, m + spot_d, width - 2 * m, aisle)
    y_barrier = m + spot_d + aisle + inside
    L["y_barrier"] = y_barrier
    lanes_w = 2 * lane_w + island
    lx = (width - lanes_w) / 2
    L["entrance_lane"] = (lx, m + spot_d + aisle, lane_w, inside + outside)
    L["island_rect"] = (lx + lane_w, m + spot_d + aisle, island, inside + outside)
    L["exit_lane"] = (lx + lane_w + island, m + spot_d + aisle, lane_w, inside + outside)
    stop = 40
    L["entrance_stop_y"] = y_barrier + stop     # entering car waits outside (south)
    L["exit_stop_y"] = y_barrier - stop         # leaving car waits inside (north)
    L["cam_entrance"] = (lx + lane_w / 2, y_barrier - cam_behind)
    L["cam_exit"] = (lx + lane_w + island + lane_w / 2, y_barrier + cam_behind)
    return L


def svg(L: dict) -> str:
    W, H = L["W"], L["H"]
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%dmm" height="%dmm" viewBox="0 0 %d %d" '
         'font-family="DejaVu Sans, Arial, sans-serif">' % (W, H, W, H),
         '<rect x="0" y="0" width="%d" height="%d" fill="#f5f5f5" stroke="#000" stroke-width="1"/>' % (W, H),
         '<text x="%d" y="12" font-size="9">IoT Garaža - tlocrt 1:1 (mm), mjerilo vozila 1:%d, %d mjesta, '
         'baza %d x %d mm</text>' % (L["margin"], L["scale"], L["spots"], W, H)]
    # spots
    for i, (x, y, w, h) in enumerate(L["spot_rects"]):
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#e8f5e9" stroke="#fff" '
                 'stroke-width="3" stroke-dasharray="8,5"/>' % (x, y, w, h))
        o.append('<text x="%.1f" y="%.1f" font-size="22" text-anchor="middle" fill="#2e7d32">P%02d</text>' % (
            x + w / 2, y + h - 18, i + 1))
        # HC-SR04 footprint above the spot centre (45 x 20 mm)
        o.append('<rect x="%.1f" y="%.1f" width="45" height="20" fill="none" stroke="#1565c0" stroke-width="1.2"/>'
                 % (x + w / 2 - 22.5, y + h / 2 - 10))
        o.append('<text x="%.1f" y="%.1f" font-size="6" text-anchor="middle" fill="#1565c0">HC-SR04 iznad</text>' % (
            x + w / 2, y + h / 2 + 18))
    x, y, w, h = L["aisle_rect"]
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#cfd8dc"/>' % (x, y, w, h))
    o.append('<text x="%.1f" y="%.1f" font-size="14" text-anchor="middle" fill="#455a64">PROMETNICA  &#8596;</text>'
             % (x + w / 2, y + h / 2 + 5))
    for name, key, arrow in (("ULAZ", "entrance_lane", "&#8593;"), ("IZLAZ", "exit_lane", "&#8595;")):
        x, y, w, h = L[key]
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#cfd8dc"/>' % (x, y, w, h))
        o.append('<text x="%.1f" y="%.1f" font-size="16" text-anchor="middle" fill="#37474f">%s %s</text>' % (
            x + w / 2, y + h - 12, name, arrow))
    x, y, w, h = L["island_rect"]
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#a5d6a7"/>' % (x, y, w, h))
    o.append('<text x="%.1f" y="%.1f" font-size="7" text-anchor="middle" transform="rotate(-90 %.1f %.1f)">'
             'otok: ESP32 rampi, kabeli</text>' % (x + w / 2, L["y_barrier"] + 70, x + w / 2, L["y_barrier"] + 70))
    yb = L["y_barrier"]
    for key, side in (("entrance_lane", 1), ("exit_lane", -1)):
        x, y, w, h = L[key]
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#c62828" stroke-width="5" '
                 'stroke-dasharray="12,8"/>' % (x, yb, x + w, yb))
        post_x = x + w if key == "entrance_lane" else x - 14
        o.append('<rect x="%.1f" y="%.1f" width="14" height="14" fill="#212121"/>' % (post_x, yb - 7))
        stop_y = L["entrance_stop_y"] if side == 1 else L["exit_stop_y"]
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#fff" stroke-width="3"/>' % (
            x + 10, stop_y, x + w - 10, stop_y))
        o.append('<text x="%.1f" y="%.1f" font-size="6" fill="#000">zaustavna crta</text>' % (x + 12, stop_y - 3 if side == -1 else stop_y + 9))
        # IR sensor at the barrier line, opposite to the post
        ir_x = x + 2 if key == "entrance_lane" else x + w - 12
        o.append('<rect x="%.1f" y="%.1f" width="10" height="6" fill="#ff8f00"/>' % (ir_x, yb - 3))
    for key, label in (("cam_entrance", "kamera ULAZ (most 130 mm)"), ("cam_exit", "kamera IZLAZ (most 130 mm)")):
        cx, cy = L[key]
        o.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#6a1b9a"/>' % (cx, cy))
        o.append('<text x="%.1f" y="%.1f" font-size="7" text-anchor="middle" fill="#6a1b9a">%s</text>' % (cx, cy - 12, label))
        target = L["entrance_stop_y"] if key == "cam_entrance" else L["exit_stop_y"]
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#6a1b9a" stroke-width="1" '
                 'stroke-dasharray="4,3"/>' % (cx, cy, cx, target))
    # sensor ESP32 + LED strip near the spots, power supply corner
    o.append('<rect x="%d" y="%d" width="55" height="28" fill="#fff" stroke="#000"/>' % (W - L["margin"] - 55, L["margin"] + L["spot_d"] + 6))
    o.append('<text x="%d" y="%d" font-size="6">ESP32 senzora</text>' % (W - L["margin"] - 52, L["margin"] + L["spot_d"] + 18))
    o.append('<rect x="%d" y="%d" width="60" height="30" fill="#fff8e1" stroke="#000"/>' % (L["margin"], H - L["margin"] - 30))
    o.append('<text x="%d" y="%d" font-size="6">5 V / 4 A napajanje</text>' % (L["margin"] + 3, H - L["margin"] - 14))
    # 100 mm scale bar
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#000" stroke-width="2"/>' % (W - 130, H - 8, W - 30, H - 8))
    o.append('<text x="%d" y="%d" font-size="7">100 mm</text>' % (W - 95, H - 11))
    o.append("</svg>")
    return "\n".join(o)


def render_png(L: dict, px_per_mm: float):
    """Raster version (for preview and A4 tiles), drawn with Pillow from the same geometry."""
    from PIL import Image, ImageDraw

    k = px_per_mm
    img = Image.new("RGB", (int(L["W"] * k), int(L["H"] * k)), (245, 245, 245))
    d = ImageDraw.Draw(img)

    def R(rect, fill, outline=None, width=1):
        x, y, w, h = rect
        d.rectangle([x * k, y * k, (x + w) * k, (y + h) * k], fill=fill, outline=outline, width=width)

    d.rectangle([0, 0, L["W"] * k - 1, L["H"] * k - 1], outline=(0, 0, 0), width=max(1, int(k)))
    for i, r in enumerate(L["spot_rects"]):
        R(r, (232, 245, 233), (255, 255, 255), max(1, int(3 * k)))
        x, y, w, h = r
        d.text(((x + w / 2 - 10) * k, (y + h - 30) * k), "P%02d" % (i + 1), fill=(46, 125, 50))
        R((x + w / 2 - 22.5, y + h / 2 - 10, 45, 20), None, (21, 101, 192), max(1, int(k)))
    for key in ("aisle_rect", "entrance_lane", "exit_lane"):
        R(L[key], (207, 216, 220))
    R(L["island_rect"], (165, 214, 167))
    yb = L["y_barrier"]
    for key in ("entrance_lane", "exit_lane"):
        x, y, w, h = L[key]
        d.line([x * k, yb * k, (x + w) * k, yb * k], fill=(198, 40, 40), width=max(1, int(5 * k)))
    for key in ("entrance_stop_y", "exit_stop_y"):
        lane = L["entrance_lane"] if key == "entrance_stop_y" else L["exit_lane"]
        d.line([(lane[0] + 10) * k, L[key] * k, (lane[0] + lane[2] - 10) * k, L[key] * k], fill=(255, 255, 255),
               width=max(1, int(3 * k)))
    for key in ("cam_entrance", "cam_exit"):
        cx, cy = L[key]
        d.ellipse([(cx - 9) * k, (cy - 9) * k, (cx + 9) * k, (cy + 9) * k], fill=(106, 27, 154))
    return img


def a4_tiles(img, px_per_mm: float, path: str) -> int:
    from PIL import ImageDraw

    page_w, page_h, overlap, margin = 297, 210, 10, 8   # landscape A4, printable area with margins
    tile_w, tile_h = page_w - 2 * margin, page_h - 2 * margin
    step_x, step_y = tile_w - overlap, tile_h - overlap
    W, H = img.width / px_per_mm, img.height / px_per_mm
    pages = []
    rows = int(math.ceil((H - overlap) / step_y))
    cols = int(math.ceil((W - overlap) / step_x))
    for r in range(rows):
        for c in range(cols):
            from PIL import Image

            page = Image.new("RGB", (int(page_w * px_per_mm), int(page_h * px_per_mm)), "white")
            box = (int(c * step_x * px_per_mm), int(r * step_y * px_per_mm),
                   int(min(img.width, (c * step_x + tile_w) * px_per_mm)),
                   int(min(img.height, (r * step_y + tile_h) * px_per_mm)))
            page.paste(img.crop(box), (int(margin * px_per_mm), int(margin * px_per_mm)))
            d = ImageDraw.Draw(page)
            d.rectangle([margin * px_per_mm, margin * px_per_mm, (margin + tile_w) * px_per_mm,
                         (margin + tile_h) * px_per_mm], outline=(160, 160, 160))
            d.text((margin * px_per_mm, 2 * px_per_mm), "list %s%d  (red %d/%d, stupac %d/%d) - preklop %d mm" % (
                chr(65 + r), c + 1, r + 1, rows, c + 1, cols, overlap), fill=(0, 0, 0))
            pages.append(page)
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=px_per_mm * 25.4)
    return len(pages)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=int, default=24, help="model car scale 1:N (24, 32, 43)")
    ap.add_argument("--spots", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nacrt"))
    ap.add_argument("--print-tiles", action="store_true")
    args = ap.parse_args(argv)

    L = layout(args.scale, args.spots)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "tlocrt.svg"), "w", encoding="utf-8") as f:
        f.write(svg(L))
    render_png(L, 1.0).save(os.path.join(args.out, "tlocrt.png"))
    spots = {"P%02d" % (i + 1): {"x": round((x + w / 2) / L["W"], 3), "y": round((y + h / 2) / L["H"], 3)}
             for i, (x, y, w, h) in enumerate(L["spot_rects"])}
    with open(os.path.join(args.out, "spots.json"), "w", encoding="utf-8") as f:
        json.dump(spots, f, indent=1)
    rows = [("baza makete (Š x D)", "%d x %d mm" % (L["W"], L["H"])),
            ("parkirno mjesto (Š x D)", "%d x %d mm" % (L["spot_w"], L["spot_d"])),
            ("prometnica (širina)", "%d mm" % L["aisle"]),
            ("ulazna/izlazna traka (širina)", "%d mm" % L["lane_w"]),
            ("otok između traka", "%d mm" % L["island"]),
            ("duljina vozila 1:%d (približno)" % L["scale"], "%d mm" % L["car_len"]),
            ("kamera iza crte rampe (na mostu iznad trake)", "%d mm, objektiv 130 mm iznad poda" % L["cam_behind"]),
            ("zaustavna crta ispred rampe", "40 mm"),
            ("ruka rampe (donji/gornji rub)", "50 / 58 mm iznad poda"),
            ("HC-SR04 iznad poda (strop mosta)", "%d mm" % max(110, round(1.6 * 1000 / L["scale"] * 1.7)))]
    with open(os.path.join(args.out, "dimenzije.md"), "w", encoding="utf-8") as f:
        f.write("# Dimenzije makete (generirano: `python alati/tlocrt.py --scale %d --spots %d`)\n\n"
                "| element | mjera |\n|---|---|\n" % (args.scale, args.spots))
        f.write("\n".join("| %s | %s |" % r for r in rows) + "\n")
    print("base %d x %d mm, files in %s" % (L["W"], L["H"], os.path.normpath(args.out)))
    if args.print_tiles:
        n = a4_tiles(render_png(L, 150 / 25.4), 150 / 25.4, os.path.join(args.out, "tlocrt_A4.pdf"))
        print("A4 tiles:", n, "pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
