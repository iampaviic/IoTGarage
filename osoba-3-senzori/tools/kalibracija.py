"""Find the occupancy thresholds for every spot from real measurements.

1. flash the firmware, open the serial port, type `cal` (prints CAL,<spot>,<cm>)
2. run this tool and follow the prompts: first all spots EMPTY, then a car on every spot

    pip install pyserial
    python kalibracija.py --port COM5            # Windows
    python kalibracija.py --port /dev/ttyUSB0    # Linux
    python kalibracija.py --log saved_output.txt # offline: a saved serial log with
                                                 # lines "EMPTY" and "CAR" marking the phases

Output: a table for tablica-pragova.md and the SPOTS[] lines for include/config.h.
Thresholds: occupied below = car + 40 % of the gap, free above = car + 60 % of the gap,
so the hysteresis band sits in the middle and noise (3 sigma) stays outside it.
"""

from __future__ import annotations

import argparse
import collections
import statistics
import sys
import time

PINS = {"P01": (23, 36), "P02": (22, 39), "P03": (21, 34), "P04": (19, 35), "P05": (18, 32), "P06": (5, 33)}


def parse(line: str):
    parts = line.strip().split(",")
    if len(parts) == 3 and parts[0] == "CAL":
        try:
            return parts[1], float(parts[2])
        except ValueError:
            return None
    return None


def collect_serial(port: str, seconds: float):
    import serial  # pyserial

    phases = {}
    with serial.Serial(port, 115200, timeout=0.2) as ser:
        time.sleep(2)
        ser.write(b"cal\n")
        for phase in ("EMPTY", "CAR"):
            input("\n>>> %s: %s, then press ENTER " % (
                phase, "remove all cars" if phase == "EMPTY" else "put a car on EVERY spot"))
            data = collections.defaultdict(list)
            end = time.time() + seconds
            while time.time() < end:
                p = parse(ser.readline().decode(errors="ignore"))
                if p:
                    data[p[0]].append(p[1])
            phases[phase] = data
            print("  collected", {k: len(v) for k, v in data.items()})
        ser.write(b"cal\n")
    return phases


def collect_log(path: str):
    phases = {"EMPTY": collections.defaultdict(list), "CAR": collections.defaultdict(list)}
    current = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip().upper()
            if s in phases:
                current = s
                continue
            p = parse(line)
            if p and current:
                phases[current][p[0]].append(p[1])
    return phases


def analyse(phases) -> int:
    rows, config_lines, problems = [], [], 0
    for spot in sorted(set(phases["EMPTY"]) | set(phases["CAR"])):
        empty = [v for v in phases["EMPTY"].get(spot, []) if v > 0]
        car = [v for v in phases["CAR"].get(spot, []) if v > 0]
        lost = len(phases["EMPTY"].get(spot, [])) + len(phases["CAR"].get(spot, [])) - len(empty) - len(car)
        if len(empty) < 5 or len(car) < 5:
            print("%s: not enough valid readings (empty %d, car %d)" % (spot, len(empty), len(car)))
            problems += 1
            continue
        e_med, c_med = statistics.median(empty), statistics.median(car)
        e_sd = statistics.pstdev(empty)
        c_sd = statistics.pstdev(car)
        gap = e_med - c_med
        occ_below = round(c_med + 0.4 * gap, 1)
        free_above = round(c_med + 0.6 * gap, 1)
        ok = gap > 2.0 and c_med + 3 * c_sd < occ_below and e_med - 3 * e_sd > free_above
        problems += not ok
        rows.append("| %s | %.1f | %.2f | %.1f | %.2f | %.1f | %.1f | %d | %s |" % (
            spot, e_med, e_sd, c_med, c_sd, occ_below, free_above, lost, "OK" if ok else "PROVJERITI montažu"))
        trig, echo = PINS.get(spot, (0, 0))
        config_lines.append('    {"%s", %2d, %2d, %.1ff, %.1ff},' % (spot, trig, echo, occ_below, free_above))

    print("\n| mjesto | prazno [cm] | σ | auto [cm] | σ | zauzeto ispod | slobodno iznad | izgubljeno | ocjena |")
    print("|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print("\n// include/config.h")
    print("static const SpotPins SPOTS[SPOT_COUNT] = {")
    print("\n".join(config_lines))
    print("};")
    if problems:
        print("\n%d spot(s) need attention: gap too small or too noisy (sensor angle, wall echo, loose mount)" % problems)
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port")
    src.add_argument("--log")
    ap.add_argument("--seconds", type=float, default=10.0, help="measuring time per phase")
    args = ap.parse_args(argv)
    phases = collect_serial(args.port, args.seconds) if args.port else collect_log(args.log)
    return analyse(phases)


if __name__ == "__main__":
    sys.exit(main())
