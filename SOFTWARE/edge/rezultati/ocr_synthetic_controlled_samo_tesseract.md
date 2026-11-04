# Točnost OCR-a - controlled

- skup: `controlled` (150 slika s pločicom), motori: tesseract
- pragovi: prihvati >= 0.85, ponovi >= 0.60; datum 2026-10-21 10:00

| metrika | vrijednost |
|---|---|
| točno pročitano (bilo koja razina) | 78.0 % (117/150) |
| automatski prihvaćeno (ACCEPT) | 27.3 % |
| ponovno snimanje (RETRY) | 40.0 % |
| ručna intervencija (MANUAL) | 32.7 % |
| pločica nije pronađena | 0.0 % |
| **POGREŠNO prihvaćeno** (mora biti 0) | **0** |
| vrijeme detekcija + OCR (medijan) | 384 ms |

## Po uvjetima snimanja

| uvjeti | točno | ukupno |
|---|---|---|
| synthetic/controlled/- | 117 | 150 |

## Promašaji (pogrešno pročitano ili pločica nije pronađena)

| slika | stvarno | pročitano | confidence | razina |
|---|---|---|---|---|
| 0004.jpg | ZD9262J | ZD926Z | 0.48 | MANUAL |
| 0012.jpg | PU838S | PU8385S | 0.51 | MANUAL |
| 0019.jpg | RI3914KJ | RI3914K | 0.68 | RETRY |
| 0021.jpg | PU3668IB | PU6681B | 0.67 | RETRY |
| 0029.jpg | ZD897J | - | 0.00 | MANUAL |
| 0031.jpg | BJ324F | - | 0.00 | MANUAL |
| 0036.jpg | VK1654J | VK165A | 0.79 | RETRY |
| 0041.jpg | PU034SD | PO345D | 0.15 | MANUAL |
| 0042.jpg | RI410K | - | 0.00 | MANUAL |
| 0043.jpg | DU764P | - | 0.00 | MANUAL |
| 0047.jpg | ZD465IO | ZD4651O | 0.81 | RETRY |
| 0051.jpg | GS397S | GS3975S | 0.52 | MANUAL |
| 0057.jpg | KA1239L | KA1239I | 0.33 | MANUAL |
| 0061.jpg | SB2323OP | SB2230P | 0.83 | RETRY |
| 0062.jpg | KA4891AB | - | 0.00 | MANUAL |
| 0071.jpg | KR6861J | KR686I | 0.51 | MANUAL |
| 0076.jpg | VK8477J | VK847T | 0.51 | MANUAL |
| 0087.jpg | GS181F | GS181A | 0.10 | MANUAL |
| 0089.jpg | KA161U | KA161O | 0.63 | RETRY |
| 0090.jpg | PU8997E | PU899T | 0.38 | MANUAL |
| 0094.jpg | KR046SJ | KR0465S | 0.20 | MANUAL |
| 0095.jpg | ST2609T | SV2609T | 0.56 | MANUAL |
| 0096.jpg | SB377ZJ | SB377Z | 0.83 | RETRY |
| 0099.jpg | SK654J | - | 0.00 | MANUAL |
| 0101.jpg | BJ1653A | BI653A | 0.69 | RETRY |
| 0122.jpg | VK0500JS | VK0500S | 0.39 | MANUAL |
| 0124.jpg | ZD874J | - | 0.00 | MANUAL |
| 0126.jpg | RI0214AJ | RI0214A | 0.05 | MANUAL |
| 0130.jpg | ZG390J | - | 0.00 | MANUAL |
| 0138.jpg | BJ8771M | BB771M | 0.62 | RETRY |
| 0140.jpg | VK607E | - | 0.00 | MANUAL |
| 0141.jpg | SB9813FS | SB9813S | 0.38 | MANUAL |
| 0146.jpg | OS9900J | OS990O | 0.60 | RETRY |
