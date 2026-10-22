# Detekcija pločica - hard

- skup: `hard`, slika: 165 (s pločicom 150, bez pločice 15)
- kriterij: IoU >= 0.50, min. confidence 0.50
- datum: 2026-10-21 09:56

| metrika | vrijednost |
|---|---|
| **uspješnost detekcije** | **95.3 %** (143 / 150) |
| lažno pozitivni (slike bez pločice) | 0 / 15 |
| srednji IoU točnih detekcija | 0.926 |
| vrijeme obrade (medijan / p95) | 37 ms / 54 ms |
| kriterij projekta (>= 90 %) | ZADOVOLJEN |

## Po uvjetima snimanja (osvjetljenje / kut / udaljenost)

| uvjeti | točno | ukupno | % |
|---|---|---|---|
| synthetic/hard/- | 143 | 150 | 95 % |

## Neuspjesi

Slike s ucrtanom oznakom (zeleno) i detekcijom (crveno): `debug`

- `0012.jpg` KR2136F - missed (conf 0.21)
- `0018.jpg` VK531G - wrong place (IoU 0.00) (conf 0.68)
- `0047.jpg` KA0367AJ - missed (conf 0.00)
- `0090.jpg` SB5929R - wrong place (IoU 0.00) (conf 0.67)
- `0100.jpg` DU4690SS - missed (conf 0.43)
- `0138.jpg` ZG0757EZ - wrong place (IoU 0.00) (conf 0.57)
- `0150.jpg` OS0794K - wrong place (IoU 0.00) (conf 0.62)
