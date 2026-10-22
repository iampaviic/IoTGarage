"""WBS slika za plan projekta: python wbs.py (treba matplotlib) -> wbs.png."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, INK2, MUTED, LINE = "#0b0b0b", "#52514e", "#8a8984", "#9a9994"
BLUE, FILL, SURF = "#2a78d6", "#eaf2fc", "#ffffff"

packages = [
    ("1 Upravljanje projektom", "Patrik", ["Plan, arhitektura, zahtjevi", "Komunikacijski ugovor (MQTT)",
                                             "Tjedni sastanci, rizici, odluke", "Objedinjavanje dokumentacije"]),
    ("2 Fizička maketa", "Patrik + Lovro", ["Nacrt i nabava komponenti", "Baza, mjesta, mostovi",
                                             "3D ispis i montaža", "Napajanje i ožičenje"]),
    ("3 Senzori mjesta", "Toma + Lovro", ["Firmware ESP32", "Filtriranje i pragovi",
                                          "MQTT, ponovno spajanje, heartbeat", "Test 20× po mjestu"]),
    ("4 Rampe i kontrola pristupa", "Luka", ["Servo i stroj stanja, aktuatori", "Sigurnost (IR) i ručno upravljanje",
                                             "MQTT naredbe i potvrde", "Pravila odluke o pristupu"]),
    ("5 ALPR – detekcija", "Sven", ["Kamera i pločice", "Detekcija i perspektiva", "Skup fotografija",
                                    "Mjerenje točnosti"]),
    ("6 OCR i edge servis", "Lukas", ["OCR i normalizacija", "ALPR servis (kamera → OCR)",
                                      "Postavljanje na edge računalo", "Tablica točnosti OCR-a"]),
    ("7 ThingsBoard", "Anja + Leo", ["Instalacija, entiteti, most (bridge)", "Nadzorni dashboard",
                                     "Alarmi i obavijesti", "Analitički dashboard i API (Leo)"]),
    ("8 Baza, testovi, GitHub", "Lovro", ["Parkirne sesije i naplata", "Testni plan i zapisnik",
                                          "Repozitorij, CI, ploča zadataka", "Korisničke upute"]),
    ("9 Integracija i završetak", "Patrik + svi", ["Integracija (10 koraka)", "Stabilizacija i testovi",
                                                     "Rezervni video", "Prezentacija i demonstracija"]),
    ("10 Mobilna aplikacija", "Leo", ["Tehnologija i dizajn ekrana", "Dohvat podataka (ThingsBoard REST API)",
                                      "Ekrani analitike (MVP)", "Testiranje i demo"]),
]

plt.rcParams.update({"font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(11, 7.12), dpi=200)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 110)
ax.set_ylim(-7.2, 64)
ax.axis("off")
fig.patch.set_facecolor(SURF)

BW, BH = 32.5, 12.4
lefts = [4, 40, 76]
tops = [50, 35.8, 21.6, 7.4]
bus_y = 53.5

# root
ax.add_patch(FancyBboxPatch((38, 57), 34, 6, boxstyle="round,pad=0,rounding_size=1", fc=BLUE, ec=BLUE, lw=1.2))
ax.text(55, 61.2, "IoT Garaža", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
ax.text(55, 58.7, "Pametna parkirna garaža s ALPR-om", ha="center", va="center", color="white", fontsize=9)
ax.plot([55, 55], [57, bus_y], color=LINE, lw=1.2, solid_capstyle="butt")
ax.plot([lefts[0] - 2, lefts[2] - 2], [bus_y, bus_y], color=LINE, lw=1.2)

for k, (title, owner, items) in enumerate(packages):
    col, row = k % 3, k // 3
    x, top = lefts[col], tops[row]
    trunk = x - 2
    ymid = top - BH / 2
    last_row = max(r for r in range(4) if 3 * r + col < len(packages))
    if row == last_row:
        ax.plot([trunk, trunk], [bus_y, ymid], color=LINE, lw=1.2)
    ax.plot([trunk, x], [ymid, ymid], color=LINE, lw=1.2)
    ax.add_patch(FancyBboxPatch((x, top - BH), BW, BH, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=FILL, ec=BLUE, lw=1.0))
    ax.text(x + 1.2, top - 1.5, title, ha="left", va="top", fontsize=10, fontweight="bold", color=INK)
    ax.text(x + BW - 1.0, top - 1.65, owner, ha="right", va="top", fontsize=7.5, color=MUTED)
    n = int(title.split()[0])
    for j, it in enumerate(items):
        ax.text(x + 1.2, top - 4.1 - j * 1.95, "%d.%d  %s" % (n, j + 1, it), ha="left", va="top",
                fontsize=8.5, color=INK2)

fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wbs.png"), facecolor=SURF)
print("ok")
