"""Generate wiring (harness) diagrams of both ESP32 nodes with WireViz.

    pip install wireviz        (needs Graphviz: apt install graphviz / https://graphviz.org/download/)
    python generiraj_sheme.py  -> wireviz/cvor-senzora.{yml,svg,png,bom.tsv}, wireviz/cvor-rampi.{...}

The pin numbers are the same as in the firmware (osoba-3-senzori/firmware/include/config.h
and osoba-4-rampe/firmware/include/config.h). Change them THERE first, then here.
Every cable gets a label (S-P01, R-UL-SERVO ...) - print the labels and stick them on both ends.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wireviz")

SPOTS = [("P01", 23, 36), ("P02", 22, 39), ("P03", 21, 34), ("P04", 19, 35), ("P05", 18, 32), ("P06", 5, 33)]
GATES = [  # name, label, servo, ir, red, green, button
    ("UL", "ulaz", 13, 34, 25, 26, 18),
    ("IZ", "izlaz", 14, 35, 27, 33, 19),
]
LED_STRIP_PIN = 25
BUZZER_PIN = 23


def q(s: str) -> str:
    return '"%s"' % s


def sensor_node() -> str:
    pins = ["5V", "GND", "3V3"] + ["GPIO%d" % t for _, t, _ in SPOTS] + ["GPIO%d" % e for _, _, e in SPOTS] + \
           ["GPIO%d" % LED_STRIP_PIN]
    y = ["connectors:",
         "  ESP32-S:",
         "    type: ESP32 DevKit V1 (cvor senzora)",
         "    pinlabels: [%s]" % ", ".join(pins),
         "  NAPAJANJE:",
         "    type: 5 V / 4 A adapter (zajednicko)",
         "    pinlabels: [+5V, GND]"]
    for spot, trig, echo in SPOTS:
        y += ["  %s:" % spot,
              "    type: HC-SR04",
              "    pinlabels: [VCC, TRIG, ECHO, GND]",
              "  DJ-%s:" % spot,
              "    type: djelitelj 1k/2k",
              "    notes: ECHO 5 V u 3.3 V",
              "    pinlabels: [ULAZ 5V, IZLAZ 3V3, GND]"]
    y += ["  LED-TRAKA:", "    type: WS2812B x %d (330 Ohm u DATA, 1000 uF na 5V)" % len(SPOTS),
          "    pinlabels: [+5V, DIN, GND]"]
    y += ["cables:"]
    for spot, _, _ in SPOTS:
        y += ["  S-%s:" % spot, "    wirecount: 4", "    colors: [RD, YE, GN, BK]", "    length: 0.6",
              "    notes: oznaka S-%s na oba kraja" % spot,
              "  S-%s-DJ:" % spot, "    wirecount: 2", "    colors: [GN, BK]", "    length: 0.05", "    category: bundle"]
    y += ["  S-LED:", "    wirecount: 3", "    colors: [RD, WH, BK]", "    length: 0.6",
          "  S-PWR:", "    wirecount: 2", "    colors: [RD, BK]", "    length: 0.3"]
    y += ["connections:"]
    for spot, trig, echo in SPOTS:
        y += ["  -", "    - NAPAJANJE: [1, 2]", "    - S-%s: [1, 4]" % spot, "    - %s: [VCC, GND]" % spot,
              "  -", "    - ESP32-S: [GPIO%d]" % trig, "    - S-%s: [2]" % spot, "    - %s: [TRIG]" % spot,
              "  -", "    - %s: [ECHO]" % spot, "    - S-%s: [3]" % spot, "    - DJ-%s: [ULAZ 5V]" % spot,
              "  -", "    - DJ-%s: [IZLAZ 3V3, GND]" % spot, "    - S-%s-DJ: [1, 2]" % spot,
              "    - ESP32-S: [GPIO%d, GND]" % echo]
    y += ["  -", "    - NAPAJANJE: [1, 2]", "    - S-PWR: [1, 2]", "    - ESP32-S: [5V, GND]",
          "  -", "    - NAPAJANJE: [1, 2]", "    - S-LED: [1, 3]", "    - LED-TRAKA: [+5V, GND]",
          "  -", "    - ESP32-S: [GPIO%d]" % LED_STRIP_PIN, "    - S-LED: [2]", "    - LED-TRAKA: [DIN]",
          ]
    return "\n".join(y) + "\n"


def gate_node() -> str:
    pins = ["5V", "GND", "3V3"]
    for _, _, servo, ir, red, green, btn in GATES:
        pins += ["GPIO%d" % p for p in (servo, ir, red, green, btn)]
    pins += ["GPIO%d" % BUZZER_PIN]
    y = ["connectors:",
         "  ESP32-R:",
         "    type: ESP32 DevKit V1 (cvor rampi)",
         "    pinlabels: [%s]" % ", ".join(pins),
         "  NAPAJANJE:",
         "    type: 5 V / 4 A adapter (zajednicko)",
         "    pinlabels: [+5V, GND]"]
    for name, label, *_ in GATES:
        y += ["  SERVO-%s:" % name, "    type: SG90 (%s)" % label, "    pinlabels: [PWM, +5V, GND]",
              "  IR-%s:" % name, "    type: FC-51 (%s) - napajati s 3.3 V!" % label, "    pinlabels: [VCC, GND, OUT]",
              "  SVJ-%s:" % name, "    type: LED crvena+zelena s 220 Ohm (%s)" % label,
              "    pinlabels: [CRVENA, ZELENA, GND]",
              "  TIPKA-%s:" % name, "    type: tipkalo rucno otvaranje (%s)" % label, "    pinlabels: [A, B]"]
    y += ["  ZUJALICA:", "    type: aktivna zujalica 3.3 V (opcionalno)", "    pinlabels: [+, '-']"]
    y += ["cables:"]
    for name, *_ in GATES:
        y += ["  R-%s-SERVO:" % name, "    wirecount: 3", "    colors: [OG, RD, BN]", "    length: 0.4",
              "  R-%s-IR:" % name, "    wirecount: 3", "    colors: [RD, BK, YE]", "    length: 0.4",
              "  R-%s-SVJ:" % name, "    wirecount: 3", "    colors: [RD, GN, BK]", "    length: 0.4",
              "  R-%s-TIPKA:" % name, "    wirecount: 2", "    colors: [WH, BK]", "    length: 0.4"]
    y += ["  R-PWR:", "    wirecount: 2", "    colors: [RD, BK]", "    length: 0.3",
          "  R-ZUJ:", "    wirecount: 2", "    colors: [RD, BK]", "    length: 0.2"]
    y += ["connections:"]
    for name, _, servo, ir, red, green, btn in GATES:
        y += ["  -", "    - ESP32-R: [GPIO%d]" % servo, "    - R-%s-SERVO: [1]" % name, "    - SERVO-%s: [PWM]" % name,
              "  -", "    - NAPAJANJE: [1, 2]", "    - R-%s-SERVO: [2, 3]" % name, "    - SERVO-%s: [+5V, GND]" % name,
              "  -", "    - ESP32-R: [3V3, GND, GPIO%d]" % ir, "    - R-%s-IR: [1, 2, 3]" % name,
              "    - IR-%s: [VCC, GND, OUT]" % name,
              "  -", "    - ESP32-R: [GPIO%d, GPIO%d, GND]" % (red, green), "    - R-%s-SVJ: [1, 2, 3]" % name,
              "    - SVJ-%s: [CRVENA, ZELENA, GND]" % name,
              "  -", "    - ESP32-R: [GPIO%d, GND]" % btn, "    - R-%s-TIPKA: [1, 2]" % name,
              "    - TIPKA-%s: [A, B]" % name]
    y += ["  -", "    - NAPAJANJE: [1, 2]", "    - R-PWR: [1, 2]", "    - ESP32-R: [5V, GND]",
          "  -", "    - ESP32-R: [GPIO%d, GND]" % BUZZER_PIN, "    - R-ZUJ: [1, 2]", "    - ZUJALICA: [+, '-']"]
    return "\n".join(y) + "\n"


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for name, text in (("cvor-senzora", sensor_node()), ("cvor-rampi", gate_node())):
        path = os.path.join(OUT, name + ".yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        exe = shutil.which("wireviz") or os.path.join(os.path.dirname(sys.executable), "wireviz")
        r = subprocess.run([exe, path, "-f", "spt"], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            return 1
        print("generated", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
