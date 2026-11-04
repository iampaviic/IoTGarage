# Fizička maketa i elektronika napajanja

Zaduženi: Patrik (vlasnik, faze 1–2, do 6.12.2026.) i Lovro Gale (napajanje i ožičenje). Svaki član sam montira i
spaja svoj hardver na maketu.

Maketu treba izraditi ručno, ali sve što se može nacrtati, izračunati i isprintati unaprijed je ovdje.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [nacrt/](nacrt) | tlocrt 1:1 (`tlocrt.svg`), pregled, tablica dimenzija, položaji mjesta za ThingsBoard |
| [alati/tlocrt.py](alati/tlocrt.py) | generator tlocrta: drugo mjerilo ili broj mjesta jednom naredbom, A4 predložak za lijepljenje |
| [alati/kamera_kalkulator.py](alati/kamera_kalkulator.py) | zaklanja li rampa pločicu, koliko piksela dobiva OCR, je li kut prestrm, je li kamera u fokusu |
| [3d/](3d) | 7 parametarskih OpenSCAD dijelova i gotovi STL-ovi (rampe, nosači senzora, most kamere, držač pločice, ...) |
| [3d/sklop/](3d/sklop) | 3D sklop cijele makete sa senzorima, servima i kamerama; pogled iz kamere, STL i GLB u boji |
| [elektronika/wireviz/](elektronika/wireviz) | dijagrami ožičenja oba ESP32 čvora s oznakama kabela (SVG) |

Opisi i tablice su u [PROJEKT/maketa](../../PROJEKT/maketa):

| | sadržaj |
|---|---|
| [nacrt-makete.md](../../PROJEKT/maketa/nacrt-makete.md) | raspored, mjerilo autića, položaj kamere s provjerom geometrije, materijali, faze izrade |
| [shema-spajanja.md](../../PROJEKT/maketa/shema-spajanja.md) | tablice pinova (iste kao u firmwareu), djelitelj za ECHO, napajanje, masa |
| [proracun-napajanja.md](../../PROJEKT/maketa/proracun-napajanja.md) | proračun struje i odabir adaptera 5 V / 4 A |
| [oznake-kabela.md](../../PROJEKT/maketa/oznake-kabela.md) | sustav oznaka i boja kabela |
| [popis-komponenti.md](../../PROJEKT/maketa/popis-komponenti.md) | popis za kupnju, CSV verzija |
| [foto-dnevnik/](../../PROJEKT/maketa/foto-dnevnik) | pravila i tablica za fotografije faza izrade |

Pločice za autiće generira Sven: `python SOFTWARE/alpr/tools/generate_plates.py` → `plates_A4.pdf` (ispis na 100 %,
mat papir, ravnalom provjeri kontrolnu crtu od 50 mm).

## Brzi start

```bash
python alati/tlocrt.py --scale 24 --spots 6 --print-tiles     # tlocrt + A4 predložak
python alati/kamera_kalkulator.py --cam-behind 200 --cam-height 130
python elektronika/generiraj_sheme.py                          # nakon promjene pinova
openscad -o 3d/stl/rampa_sg90.stl 3d/rampa_sg90.scad           # nakon promjene mjera
python 3d/sklop/izvoz.py --slike                               # slike 3D sklopa nakon promjene dijela
```

## Zadaci

- ✅ električna shema u `elektronika/` (ažurirati prema stvarnom stanju)
- ✅ popis komponenti
- ✅ plan položaja senzora i kamera (`nacrt/tlocrt.svg`, `nacrt-makete.md` §2–3)
- ⬜ s timom odabrati mjerilo autića (preporuka 1:24) i materijal, naručiti komponente, provjeriti minimalni fokus kamere (rizik R-02)
- ⬜ izraditi bazu prema `nacrt/tlocrt.svg`, most iznad mjesta i kanale za kabele
- ⬜ isprintati i montirati 3D dijelove, senzore, rampe, IR senzore, most kamere i graničnike
- ⬜ razvod napajanja (sklopka, WAGO, kondenzatori), ožičenje po dijagramima i oznake kabela
- ⬜ prije spajanja ESP32 multimetrom provjeriti 5 V, masu i napon iza djelitelja (≤ 3,4 V)
- ⬜ fotografirati svaku fazu (`foto-dnevnik/`) i ažurirati shemu ako se nešto promijeni

Gotovo je kad se maketa uključi bez ručnog premještanja žica, svi senzori su stabilno montirani, a kamera ima
ponovljiv pogled na vozilo i registraciju.
