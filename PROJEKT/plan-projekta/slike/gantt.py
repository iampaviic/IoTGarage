"""Gantogram za plan projekta: python gantt.py (treba matplotlib) -> gantt.png."""
import os
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
import matplotlib.dates as mdates


def D(s):
    """'dd.mm' -> date; October-December are 2026, January 2027."""
    day, month = int(s.split(".")[0]), int(s.split(".")[1])
    return dt.date(2026 if month >= 10 else 2027, month, day)


def END(s):
    return D(s) + dt.timedelta(days=1)


INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BAR, SURF, BAND = "#2a78d6", "#fcfcfb", "#f1f0ec"
EXAM_FILL, EXAM_LINE, EXAM_INK = "#fbeeec", "#d9958d", "#b0453b"

groups = [
    ("1 Upravljanje projektom – Patrik", [
        ("Plan, arhitektura, MQTT ugovor", "19.10", "1.11"),
        ("Tjedni sastanci, praćenje rizika i odluka", "19.10", "29.1"),
        ("Objedinjavanje dokumentacije", "7.12", "29.1")]),
    ("2 Fizička maketa – Patrik, Lovro", [
        ("Nacrt, nabava komponenti, fokus kamere", "19.10", "8.11"),
        ("Baza, mjesta, 3D ispis, montaža", "2.11", "29.11"),
        ("Napajanje i ožičenje", "7.12", "20.12")]),
    ("3 Senzori mjesta – Toma, Lovro", [
        ("Jedan senzor s djeliteljem, mjerenja", "2.11", "10.11"),
        ("6 senzora na mostu, LED traka, MQTT", "11.11", "22.11"),
        ("Kalibracija pragova, test 20× po mjestu", "7.12", "18.12")]),
    ("4 Rampe i kontrola pristupa – Luka", [
        ("Jedan servo s ESP32, firmware", "2.11", "10.11"),
        ("Montaža obje rampe: kutovi, IR, LED, tipke", "11.11", "22.11"),
        ("Pravila pristupa i naredbe preko MQTT-a", "7.12", "13.12"),
        ("Sigurnosni testovi rampi", "7.12", "18.12")]),
    ("5 ALPR – detekcija – Sven", [
        ("Ispis pločica, fokus kamere, prve fotografije", "2.11", "10.11"),
        ("Skup ≥ 100 fotografija, označavanje", "11.11", "22.11"),
        ("Mjerenje detekcije (≥ 90 %), ograničenja", "7.12", "18.12")]),
    ("6 OCR i edge servis – Lukas", [
        ("OCR na prvim stvarnim fotografijama", "9.11", "15.11"),
        ("Edge servis na Raspberry Pi s kamerom", "16.11", "22.11"),
        ("Tablica točnosti OCR-a, podešavanje", "7.12", "18.12")]),
    ("7 ThingsBoard – Anja, Leo", [
        ("Instalacija, entiteti, bridge", "2.11", "15.11"),
        ("Nadzorni dashboard, alarmi, obavijesti", "7.12", "20.12"),
        ("Analitički dashboard i API za aplikaciju (Leo)", "7.12", "20.12")]),
    ("8 Baza, testovi, GitHub – Lovro", [
        ("Model sesija i pravilo naplate", "2.11", "8.11"),
        ("Testni plan, izvođenje i zapisnik testova", "9.11", "17.1"),
        ("Korisničke upute", "4.1", "24.1")]),
    ("9 Integracija i završetak – svi", [
        ("Integracija s hardverom (koraci 1–10)", "7.12", "20.12"),
        ("Stabilizacija, testni scenariji, rezervni video", "4.1", "17.1"),
        ("Prezentacija, generalna proba, predaja", "18.1", "29.1")]),
    ("10 Mobilna aplikacija – Leo", [
        ("Tehnologija, dizajn, dohvat podataka", "9.11", "6.12"),
        ("Ekrani analitike – MVP", "7.12", "20.12"),
        ("Testiranje i dorada", "4.1", "17.1")]),
]
milestones = [("KT1", "28.10"), ("KT2", "10.11"), ("KT3", "20.11"), ("KT4", "23.11"), ("KT5", "23.12"),
              ("KT6", "11.1"), ("KT7", "17.1"), ("KT8", "29.1")]
phases = [("Faza 1", "19.10", "1.11"), ("Faza 2", "2.11", "6.12"), ("Faza 3", "7.12", "20.12"),
          ("Blagdani", "21.12", "3.1"), ("Faza 4", "4.1", "17.1"), ("Faza 5", "18.1", "29.1")]
HOLIDAY = ("21.12", "3.1")
EXAMS = ("23.11", "4.12")          # međuispiti: na projektu se ne radi, trake se prekidaju
START = D("19.10")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
rows = []
for g, tasks in groups:
    rows.append(("group", g, None, None))
    for t in tasks:
        rows.append(("task",) + t)

n = len(rows)
fig, ax = plt.subplots(figsize=(11, 10.2), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
x0, x1 = D("19.10"), END("29.1")

# phase bands (holiday break hatched)
for k, (name, a, b) in enumerate(phases):
    if (a, b) == HOLIDAY:
        ax.add_patch(Rectangle((mdates.date2num(D(a)), -2.1), (END(b) - D(a)).days, n + 4.1, fc=SURF,
                               ec="#c9c8c2", hatch="////", lw=0, zorder=0))
    elif k % 2 == 0:
        ax.axvspan(D(a), END(b), color=BAND, zorder=0, lw=0)
    if D(a) < D(EXAMS[0]) < END(b):   # label in the part of the phase before the exams
        b = "%d.%d" % ((D(EXAMS[0]) - dt.timedelta(days=1)).day, D(EXAMS[0]).month)
    ax.text(D(a) + (END(b) - D(a)) / 2, -1.55, name, ha="center", va="center", color=INK2, fontsize=8.5,
            fontweight="bold")

# exam period: no work on the project, bars are interrupted
ex0, ex1 = D(EXAMS[0]), END(EXAMS[1])
ax.add_patch(Rectangle((mdates.date2num(ex0), -2.1), (ex1 - ex0).days, 1.5, fc=EXAM_FILL, lw=0, zorder=0.5))
ax.add_patch(Rectangle((mdates.date2num(ex0), -0.6), (ex1 - ex0).days, n + 2.6, fc=EXAM_FILL, ec=EXAM_LINE,
                       hatch="\\\\", lw=0, zorder=0.5))
ax.text(ex0 + (ex1 - ex0) / 2, -1.55, "Međuispiti", ha="center", va="center", color=EXAM_INK, fontsize=8.5,
        fontweight="bold")


def work_segments(s, e):
    """[start, end) pieces of a task outside the exam period; a leftover of 1-2 days (the weekend
    after the exams) is not drawn."""
    return [(a, b) for a, b in ((s, min(e, ex0)), (max(s, ex1), e)) if (b - a).days >= 3]

for i, (kind, label, a, b) in enumerate(rows):
    if kind == "group":
        ax.text(-0.005, i, label, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontweight="bold", color=INK, fontsize=9)
        continue
    ax.text(-0.005, i, label, transform=ax.get_yaxis_transform(), ha="right", va="center", color=INK2, fontsize=8.5)
    for s, e in work_segments(D(a), END(b)):
        ax.add_patch(FancyBboxPatch((mdates.date2num(s) + 0.25, i - 0.28), (e - s).days - 0.5, 0.56,
                                    boxstyle="round,pad=0,rounding_size=0.5", fc=BAR, ec="none", zorder=3,
                                    mutation_aspect=0.04))

# milestones; a label too close to the previous one goes one line lower
prev_x, low = None, False
for name, d in milestones:
    x = mdates.date2num(END(d))
    low = (not low) if prev_x is not None and x - prev_x < 5 else False
    prev_x = x
    ax.vlines(x, -0.6, n - 0.4, color=MUTED, lw=0.8, ls=(0, (2, 2)), zorder=1)
    ax.scatter([x], [n + 0.1], marker="D", s=46, color=INK, zorder=4, edgecolors=SURF, linewidths=1.5)
    ax.text(x, n + (1.55 if low else 0.85), name, ha="center", va="center", fontsize=8, color=INK)

ax.set_xlim(mdates.date2num(x0) - 0.5, mdates.date2num(x1) + 1.5)
ax.set_ylim(n + 2.0, -2.1)
ax.set_yticks([])
weeks = [START + dt.timedelta(days=7 * k) for k in range(15)]
ax.set_xticks([mdates.date2num(w) for w in weeks])
ax.set_xticklabels([f"{w.day}.{w.month}." if k % 2 == 0 else "" for k, w in enumerate(weeks)],
                   color=INK2, fontsize=8)
ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(axis="x", length=0, pad=4)
for k, w in enumerate(weeks):  # week labels on top
    ax.text(mdates.date2num(w) + 3.5, -1.0, f"T{k + 1}", ha="center", va="center", color=MUTED, fontsize=7)
ax.set_xlabel("Početak tjedna (ponedjeljak), 2026./2027.", color=INK2, fontsize=8.5)
legend = [Line2D([], [], marker="D", ls="none", color=INK, markersize=6, label="kontrolna točka"),
          Patch(fc=SURF, ec="#c9c8c2", hatch="////", lw=0, label="blagdanska stanka (rezerva)"),
          Patch(fc=EXAM_FILL, ec=EXAM_LINE, hatch="\\\\", lw=0, label="međuispiti – ne radi se na projektu")]
fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.66, 0.004), ncol=3, frameon=False,
           fontsize=8.5, labelcolor=INK2, handlelength=1.6, columnspacing=2.0)
fig.subplots_adjust(left=0.33, right=0.985, top=0.987, bottom=0.08)
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gantt.png"), facecolor=SURF)
print("ok")
