"""Gantogram za plan projekta: python gantt.py (treba matplotlib) -> gantt.png."""
import os
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.dates as mdates

D = lambda s: dt.date(2026, int(s.split(".")[1]), int(s.split(".")[0]))
END = lambda s: D(s) + dt.timedelta(days=1)

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BAR, BAR_DONE, SURF = "#2a78d6", "#9cc1ee", "#fcfcfb"

groups = [
    ("1 Upravljanje projektom – Patrik", [
        ("Plan, arhitektura, MQTT ugovor", "19.10", "25.10"),
        ("Tjedni sastanci, praćenje rizika i odluka", "19.10", "29.11"),
        ("Objedinjavanje dokumentacije", "9.11", "29.11")]),
    ("2 Fizička maketa – Patrik, Lovro", [
        ("Nacrt, nabava komponenti, fokus kamere", "19.10", "1.11"),
        ("Baza, mjesta, mostovi, 3D ispis, montaža", "26.10", "8.11"),
        ("Napajanje i ožičenje", "2.11", "8.11")]),
    ("3 Senzori mjesta – Toma, Lovro", [
        ("Firmware, kalibracija, MQTT, test 20×", "19.10", "8.11")]),
    ("4 Rampe i kontrola pristupa – Luka", [
        ("Firmware, montaža, sigurnosni testovi, pravila", "19.10", "8.11")]),
    ("5 ALPR – detekcija – Sven", [
        ("Kamera, pločice, ≥ 100 fotografija, mjerenje", "19.10", "8.11")]),
    ("6 OCR i edge servis – Lukas", [
        ("OCR na stvarnim slikama, edge na Raspberry Pi", "26.10", "8.11")]),
    ("7 ThingsBoard – Anja, Leo", [
        ("Instalacija, entiteti, bridge", "19.10", "1.11"),
        ("Nadzorni dashboard, alarmi, obavijesti", "26.10", "8.11"),
        ("Analitički dashboard i API za aplikaciju (Leo)", "26.10", "8.11")]),
    ("8 Baza, testovi, GitHub – Lovro", [
        ("Model sesija i pravilo naplate", "19.10", "1.11"),
        ("Testni plan, izvođenje i zapisnik testova", "26.10", "22.11"),
        ("Korisničke upute", "9.11", "29.11")]),
    ("9 Integracija i završetak – svi", [
        ("Integracija s hardverom (koraci 1–10)", "9.11", "15.11"),
        ("Stabilizacija, testni scenariji, rezervni video", "16.11", "22.11"),
        ("Prezentacija, generalna proba, demo", "23.11", "29.11")]),
    ("10 Mobilna aplikacija – Leo", [
        ("Tehnologija, dizajn, dohvat podataka", "26.10", "8.11"),
        ("Ekrani analitike – MVP", "9.11", "15.11"),
        ("Testiranje i dorada", "16.11", "22.11")]),
]
milestones = [("KT1", "21.10"), ("KT2", "25.10"), ("KT3", "1.11"), ("KT4", "8.11"),
              ("KT5", "15.11"), ("KT6", "22.11"), ("KT7", "29.11")]
phases = [("Faza 1", "19.10", "25.10"), ("Faza 2", "26.10", "8.11"), ("Faza 3", "9.11", "15.11"),
          ("Faza 4", "16.11", "22.11"), ("Faza 5", "23.11", "29.11")]
TODAY = D("21.10")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
rows = []
for g, tasks in groups:
    rows.append(("group", g, None, None))
    for t in tasks:
        rows.append(("task",) + t)

n = len(rows)
fig, ax = plt.subplots(figsize=(11, 8.6), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
x0, x1 = D("19.10"), END("29.11")

# phase bands
for k, (name, a, b) in enumerate(phases):
    if k % 2 == 0:
        ax.axvspan(D(a), END(b), color="#f1f0ec", zorder=0, lw=0)
    ax.text(D(a) + (END(b) - D(a)) / 2, -1.55, name, ha="center", va="center", color=INK2, fontsize=8.5,
            fontweight="bold")

for i, (kind, label, a, b) in enumerate(rows):
    y = i
    if kind == "group":
        ax.text(-0.005, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontweight="bold", color=INK, fontsize=9)
        continue
    ax.text(-0.005, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center", color=INK2, fontsize=8.5)
    s, e = D(a), END(b)
    width = (e - s).days - 0.25
    sx = mdates.date2num(s) + 0.12
    # part before today is shown lighter (already elapsed time)
    ax.add_patch(FancyBboxPatch((sx, y - 0.28), width, 0.56, boxstyle="round,pad=0,rounding_size=0.25",
                                fc=BAR, ec="none", zorder=3, mutation_aspect=0.08))

# milestones
ytop = n + 0.3
for name, d in milestones:
    x = mdates.date2num(END(d)) - 0.0
    ax.vlines(x, -0.6, n - 0.4, color=MUTED, lw=0.8, ls=(0, (2, 2)), zorder=1)
    ax.scatter([x], [n + 0.1], marker="D", s=46, color=INK, zorder=4, edgecolors=SURF, linewidths=1.5)
    ax.text(x, n + 0.85, name, ha="center", va="center", fontsize=8, color=INK)

ax.set_xlim(mdates.date2num(x0) - 0.3, mdates.date2num(x1) + 0.8)
ax.set_ylim(n + 1.3, -2.1)
ax.set_yticks([])
weeks = [D("19.10") + dt.timedelta(days=7 * k) for k in range(7)]
ax.set_xticks([mdates.date2num(w) for w in weeks])
ax.set_xticklabels([f"{w.day}.{w.month}." for w in weeks], color=INK2, fontsize=8.5)
for k in range(6):
    mid = mdates.date2num(weeks[k]) + 3.5
    ax.text(mid, n + 0.85, "", ha="center")
ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(axis="x", length=0, pad=4)
# week labels on top
for k in range(6):
    mid = mdates.date2num(weeks[k]) + 3.5
    ax.text(mid, -1.05, f"T{k + 1}", ha="center", va="center", color=MUTED, fontsize=8)
ax.set_xlabel("Tjedan (početak tjedna, ponedjeljak) – 2026.  ◆ kontrolna točka", color=INK2, fontsize=8.5)
fig.subplots_adjust(left=0.33, right=0.975, top=0.985, bottom=0.07)
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gantt.png"), facecolor=SURF)
print("ok")
