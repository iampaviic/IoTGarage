# Točnost OCR-a - hard

- skup: `hard` (150 slika s pločicom), motori: template, tesseract
- pragovi: prihvati >= 0.85, ponovi >= 0.60; datum 2026-10-21 09:59

| metrika | vrijednost |
|---|---|
| točno pročitano (bilo koja razina) | 78.7 % (118/150) |
| automatski prihvaćeno (ACCEPT) | 39.3 % |
| ponovno snimanje (RETRY) | 23.3 % |
| ručna intervencija (MANUAL) | 35.3 % |
| pločica nije pronađena | 2.0 % |
| **POGREŠNO prihvaćeno** (mora biti 0) | **0** |
| vrijeme detekcija + OCR (medijan) | 583 ms |

## Po uvjetima snimanja

| uvjeti | točno | ukupno |
|---|---|---|
| synthetic/hard/- | 118 | 147 |

## Promašaji (pogrešno pročitano ili pločica nije pronađena)

| slika | stvarno | pročitano | confidence | razina |
|---|---|---|---|---|
| 0001.jpg | KR8526L | KN8526I | 0.17 | MANUAL |
| 0012.jpg | KR2136F | - | 0.00 | NO_DETECTION |
| 0013.jpg | DU690RE | OU690RE | 0.38 | MANUAL |
| 0018.jpg | VK531G | - | 0.00 | MANUAL |
| 0019.jpg | SB9921M | SB9922N | 0.18 | MANUAL |
| 0020.jpg | VU622I | - | 0.00 | MANUAL |
| 0038.jpg | ZG049M | - | 0.00 | MANUAL |
| 0040.jpg | VK538RS | NT538BS | 0.05 | MANUAL |
| 0044.jpg | OS546DU | OS5460U | 0.16 | MANUAL |
| 0047.jpg | KA0367AJ | - | 0.00 | NO_DETECTION |
| 0053.jpg | BJ257NA | AV257NA | 0.17 | MANUAL |
| 0057.jpg | KC4512G | KC4522G | 0.51 | MANUAL |
| 0063.jpg | DU592BV | DU5928V | 0.38 | MANUAL |
| 0066.jpg | VU4896L | VU489R | 0.35 | MANUAL |
| 0078.jpg | DU438FF | OM438FF | 0.16 | MANUAL |
| 0080.jpg | KC080JU | KC080IU | 0.28 | MANUAL |
| 0082.jpg | RI0592J | RI0592I | 0.35 | MANUAL |
| 0084.jpg | PU981OV | PU9810V | 0.75 | RETRY |
| 0087.jpg | GS1712K | GS1312K | 0.41 | MANUAL |
| 0089.jpg | PU256S | VV256S | 0.13 | MANUAL |
| 0090.jpg | SB5929R | - | 0.00 | MANUAL |
| 0091.jpg | BJ1644P | BJ1644F | 0.20 | MANUAL |
| 0100.jpg | DU4690SS | - | 0.00 | NO_DETECTION |
| 0120.jpg | ST528U | - | 0.00 | MANUAL |
| 0128.jpg | RI552OZ | RI552CZ | 0.28 | MANUAL |
| 0136.jpg | SK704V | SK304V | 0.27 | MANUAL |
| 0138.jpg | ZG0757EZ | - | 0.00 | MANUAL |
| 0141.jpg | KA4948VM | IA948VM | 0.49 | MANUAL |
| 0145.jpg | DU404UA | DU4040A | 0.24 | MANUAL |
| 0146.jpg | GS014JH | - | 0.00 | MANUAL |
| 0147.jpg | PU1955JA | VV1955IA | 0.10 | MANUAL |
| 0150.jpg | OS0794K | - | 0.00 | MANUAL |
