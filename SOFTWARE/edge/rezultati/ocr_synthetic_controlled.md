# Točnost OCR-a - controlled

- skup: `controlled` (150 slika s pločicom), motori: template, tesseract
- pragovi: prihvati >= 0.85, ponovi >= 0.60; datum 2026-10-21 09:58

| metrika | vrijednost |
|---|---|
| točno pročitano (bilo koja razina) | 91.3 % (137/150) |
| automatski prihvaćeno (ACCEPT) | 68.0 % |
| ponovno snimanje (RETRY) | 21.3 % |
| ručna intervencija (MANUAL) | 10.7 % |
| pločica nije pronađena | 0.0 % |
| **POGREŠNO prihvaćeno** (mora biti 0) | **0** |
| vrijeme detekcija + OCR (medijan) | 578 ms |

## Po uvjetima snimanja

| uvjeti | točno | ukupno |
|---|---|---|
| synthetic/controlled/- | 137 | 150 |

## Promašaji (pogrešno pročitano ili pločica nije pronađena)

| slika | stvarno | pročitano | confidence | razina |
|---|---|---|---|---|
| 0011.jpg | SB7256RK | AA7256RK | 0.19 | MANUAL |
| 0032.jpg | KA972EU | RM972EU | 0.16 | MANUAL |
| 0040.jpg | GS0296BL | OJ0296BL | 0.15 | MANUAL |
| 0041.jpg | PU034SD | VV034SD | 0.19 | MANUAL |
| 0042.jpg | RI410K | TA410K | 0.10 | MANUAL |
| 0043.jpg | DU764P | VM364P | 0.15 | MANUAL |
| 0060.jpg | KC182D | KC182O | 0.32 | MANUAL |
| 0062.jpg | KA4891AB | KL1891AE | 0.20 | MANUAL |
| 0095.jpg | ST2609T | SR2609T | 0.15 | MANUAL |
| 0105.jpg | GS218V | GS118V | 0.26 | MANUAL |
| 0120.jpg | GS484LK | DS484LK | 0.21 | MANUAL |
| 0126.jpg | RI0214AJ | RI0214A | 0.01 | MANUAL |
| 0142.jpg | KC395VA | AC395VA | 0.26 | MANUAL |
