# Detekcija pločica - controlled

- skup: `controlled`, slika: 165 (s pločicom 150, bez pločice 15)
- kriterij: IoU >= 0.50, min. confidence 0.50
- datum: 2026-10-21 09:56

| metrika | vrijednost |
|---|---|
| **uspješnost detekcije** | **100.0 %** (150 / 150) |
| lažno pozitivni (slike bez pločice) | 0 / 15 |
| srednji IoU točnih detekcija | 0.951 |
| vrijeme obrade (medijan / p95) | 35 ms / 49 ms |
| kriterij projekta (>= 90 %) | ZADOVOLJEN |

## Po uvjetima snimanja (osvjetljenje / kut / udaljenost)

| uvjeti | točno | ukupno | % |
|---|---|---|---|
| synthetic/controlled/- | 150 | 150 | 100 % |

## Neuspjesi

Slike s ucrtanom oznakom (zeleno) i detekcijom (crveno): `debug`

