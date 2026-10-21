# Skupovi slika

```
dataset/
  synthetic/<ime>/   generirano: python tools/make_synthetic_dataset.py (ne komita se, ponovljivo sa --seed)
  real/<ime>/        fotografije makete: python tools/capture_dataset.py (NE komita se - .gitignore)
     images/0001_093512.jpg
     labels.csv
```

`labels.csv`: `file, plate, x1, y1, x2, y2, x3, y3, x4, y4, lighting, angle, distance, note`
(kutovi: gore-lijevo, gore-desno, dolje-desno, dolje-lijevo u pikselima; prazan `plate` = slika bez pločice).

## Kako snimiti stvarni skup (cilj ≥ 100 slika)

| dimenzija | vrijednosti (upisati u `--lighting/--angle/--distance`) | po |
|---|---|---|
| registracija | barem 6 različitih pločica s lista | ≥ 10 slika svaka |
| osvjetljenje | `svijetlo`, `normalno`, `tamno` (ugašeno stropno svjetlo) | |
| kut | `0` (ravno), `15`, `30` (stupnjeva od osi kamere) | |
| udaljenost | `blizu` (na graničniku), `dalje` (+5 cm), `daleko` (+10 cm) | |
| bez pločice | prazna traka, ruka rampe, prazan autić | ~10 slika |

"Kontrolirani" skup za kriterij od 90 % = autić na graničniku, normalno/svijetlo, kut ≤ 15°.
Teži uvjeti se mjere odvojeno i opisuju u `ogranicenja.md`.

## Privatnost

Samo maketa i **izmišljene** pločice. Bez ljudi, bez stvarnih vozila, bez stvarnih registracija.
Stvarne fotografije ne idu u javni repozitorij (dijeliti preko zajedničkog diska), u izvještaj samo isječci.
