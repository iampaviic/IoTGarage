# Osoba 2 – fizička maketa i elektronika napajanja

**Zaduženi:** Patrik (vlasnik, tjedni 1–3) i Lovro Gale (napajanje i ožičenje). Svaki član sam montira i spaja svoj hardver na maketu.

Maketu moraš izraditi ti – ali sve što se može nacrtati, izračunati i isprintati unaprijed je ovdje.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [nacrt-makete.md](../../PROJEKT/maketa/nacrt-makete.md) | raspored, mjerilo autića, **položaj kamere** (s provjerom geometrije), materijali, faze izrade |
| [nacrt/](nacrt) | tlocrt **1:1** (`tlocrt.svg`), pregled, tablica dimenzija, položaji mjesta za ThingsBoard |
| [alati/tlocrt.py](alati/tlocrt.py) | generator tlocrta: drugo mjerilo/broj mjesta jednom naredbom, A4 predložak za lijepljenje |
| [alati/kamera_kalkulator.py](alati/kamera_kalkulator.py) | zaklanja li rampa pločicu, koliko piksela dobiva OCR, je li kut prestrm, je li kamera u fokusu |
| [3d/](3d) | 7 parametarskih OpenSCAD dijelova + gotovi STL-ovi (rampe, nosači senzora, most kamere, držač pločice, ...) |
| [elektronika/shema-spajanja.md](../../PROJEKT/maketa/shema-spajanja.md) | tablice pinova (iste kao u firmwareu), djelitelj za ECHO, napajanje, masa |
| [elektronika/wireviz/](elektronika/wireviz) | dijagrami ožičenja oba ESP32 čvora s oznakama kabela (SVG) |
| [elektronika/proracun-napajanja.md](../../PROJEKT/maketa/proracun-napajanja.md) | proračun struje → adapter 5 V / 4 A |
| [elektronika/oznake-kabela.md](../../PROJEKT/maketa/oznake-kabela.md) | sustav oznaka i boja kabela |
| [popis-komponenti.md](../../PROJEKT/maketa/popis-komponenti.md) | popis za kupnju s okvirnim cijenama (~230 €), CSV verzija |
| [foto-dnevnik/](../../PROJEKT/maketa/foto-dnevnik) | pravila i tablica za fotografije faza izrade |

Pločice za autiće generira osoba 5: `python SOFTWARE/alpr/tools/generate_plates.py` → `plates_A4.pdf`
(ispis na 100 %, mat papir, provjeri ravnalom kontrolnu crtu od 50 mm).

## Brzi start

```bash
python alati/tlocrt.py --scale 24 --spots 6 --print-tiles     # tlocrt + A4 predložak
python alati/kamera_kalkulator.py --cam-behind 200 --cam-height 130
python elektronika/generiraj_sheme.py                          # nakon promjene pinova
openscad -o 3d/stl/rampa_sg90.stl 3d/rampa_sg90.scad           # nakon promjene mjera
```

## Tvoji zadaci

1. **Tjedan 1:** s timom odabrati mjerilo autića (preporuka 1:24) i materijal; naručiti komponente po prioritetu;
   **provjeriti minimalni fokus kamere** (rizik R-02).
2. Izraditi bazu prema `nacrt/tlocrt.svg`, most iznad mjesta, kanale za kabele.
3. Isprintati i montirati 3D dijelove; montirati senzore, rampe, IR senzore, most kamere, graničnike.
4. Napraviti razvod napajanja (sklopka, WAGO, kondenzatori), ožičiti po dijagramima, **označiti kabele**.
5. Prije spajanja ESP32: multimetrom provjeriti 5 V, masu i napon iza djelitelja (≤ 3,4 V).
6. Fotografirati svaku fazu (`foto-dnevnik/`), ažurirati shemu ako nešto promijeniš.

## Isporučivo (iz plana) → gdje je

| isporučivo | status |
|---|---|
| završena fizička maketa | ⬜ izrada |
| električna shema | ✅ `elektronika/` (ažurirati prema stvarnom stanju) |
| popis komponenti | ✅ `popis-komponenti.md` |
| fotografije faza izrade | ⬜ `foto-dnevnik/` |
| plan položaja senzora i kamera | ✅ `nacrt/tlocrt.svg`, `nacrt-makete.md` §2–3 |

**Kriterij završetka:** maketa se uključi bez ručnog premještanja žica, svi senzori stabilno montirani,
kamera ima ponovljiv pogled na vozilo i registraciju.
