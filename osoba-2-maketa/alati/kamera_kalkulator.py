"""Camera placement calculator for the model (osoba 2 + osoba 5).

Answers, before anything is glued:
  * does the line of sight pass the barrier arm?           (arm must NOT cover the plate)
  * how many pixels will the plate and its characters get? (OCR needs >= ~25 px character height)
  * how steep is the view?                                 (> 35 deg distorts the plate a lot)
  * is the plate inside the camera's focus range?

    python kamera_kalkulator.py                                   # default model values
    python kamera_kalkulator.py --cam-behind 250 --cam-height 150 --stop 40 --arm-bottom 50
    python kamera_kalkulator.py --hfov 78 --width-px 1920         # e.g. Logitech C920 at 1080p

Geometry (side view along the lane, distances in mm from the barrier line):

    camera  *  (height H, D behind the barrier on the side away from the car)
             \\
              \\   line of sight
    arm  ======\\===  (from arm-bottom to arm-top)     <- the ray must pass below or above
              | \\
    barrier ->|  \\     [plate]  (centre at plate-height, `stop` mm in front of the barrier)
"""

from __future__ import annotations

import argparse
import math
import sys


def analyse(a) -> int:
    dx = a.cam_behind + a.stop                      # horizontal distance camera -> plate
    dz = a.cam_height - a.plate_height              # vertical drop
    slant = math.hypot(dx, dz)
    pitch = math.degrees(math.atan2(dz, dx))
    ray_at_barrier = a.cam_height - dz * (a.cam_behind / dx)

    # plate seen at pitch: its height is foreshortened by cos(pitch); lateral offset adds yaw
    yaw = math.degrees(math.atan2(a.lateral, slant))
    fov_w = 2 * slant * math.tan(math.radians(a.hfov / 2))
    px_per_mm = a.width_px / fov_w
    plate_h_mm = a.plate_width / (520.0 / 110.0)
    plate_px = a.plate_width * px_per_mm * math.cos(math.radians(yaw))
    char_px = plate_h_mm * 0.64 * px_per_mm * math.cos(math.radians(pitch))

    problems = 0
    print("udaljenost kamera-pločica     %6.0f mm (vodoravno %d, okomito %d)" % (slant, dx, dz))
    print("kut gledanja prema dolje      %6.1f °" % pitch)
    print("bočni kut (yaw)               %6.1f °" % yaw)
    print("širina vidnog polja na pločici%6.0f mm" % fov_w)
    print("pločica u slici               %6.0f px široka" % plate_px)
    print("visina znakova                %6.0f px" % char_px)
    print("zraka na crti rampe           %6.1f mm iznad poda (ruka rampe %d-%d mm)" % (
        ray_at_barrier, a.arm_bottom, a.arm_top))
    print()
    if a.arm_bottom <= ray_at_barrier <= a.arm_top:
        print("PROBLEM  ruka rampe zaklanja pločicu -> podigni kameru, pomakni je dalje ili spusti/podigni ruku")
        problems += 1
    else:
        print("OK       ruka rampe ne zaklanja pogled")
    if pitch > 35:
        print("PROBLEM  pogled je prestrm (> 35°) -> spusti kameru ili je odmakni")
        problems += 1
    else:
        print("OK       kut gledanja")
    if char_px < 25:
        print("PROBLEM  znakovi premali za OCR (< 25 px) -> približi kameru, veća pločica ili veća rezolucija")
        problems += 1
    elif char_px > 140:
        print("PAZI     znakovi vrlo veliki - pločica može izaći iz kadra kad auto stane malo drugačije")
    else:
        print("OK       veličina znakova za OCR")
    if slant < a.min_focus:
        print("PROBLEM  bliže od minimalne udaljenosti fokusa kamere (%d mm) -> slika mutna" % a.min_focus)
        problems += 1
    else:
        print("OK       udaljenost veća od minimalnog fokusa (%d mm)" % a.min_focus)
    margin = (fov_w - a.plate_width) / 2
    print("         rezerva za neprecizno zaustavljanje: ±%.0f mm lijevo/desno" % max(0.0, margin))
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cam-height", type=float, default=150, help="camera lens height above the floor [mm]")
    ap.add_argument("--cam-behind", type=float, default=250, help="camera distance behind the barrier line [mm]")
    ap.add_argument("--stop", type=float, default=40, help="plate distance in front of the barrier line [mm]")
    ap.add_argument("--lateral", type=float, default=0, help="sideways offset camera vs lane centre [mm]")
    ap.add_argument("--plate-height", type=float, default=30, help="plate centre height above the floor [mm]")
    ap.add_argument("--plate-width", type=float, default=60, help="printed plate width [mm]")
    ap.add_argument("--arm-bottom", type=float, default=50, help="barrier arm lower edge [mm]")
    ap.add_argument("--arm-top", type=float, default=58, help="barrier arm upper edge [mm]")
    ap.add_argument("--hfov", type=float, default=60, help="horizontal field of view [deg] (C270 ~55, C920 ~70-78)")
    ap.add_argument("--width-px", type=int, default=1280, help="horizontal resolution used by the edge service")
    ap.add_argument("--min-focus", type=int, default=200, help="closest sharp distance of the camera [mm]")
    return analyse(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
