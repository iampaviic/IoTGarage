# Oznake kabela

Svaki kabel ima naljepnicu **na oba kraja** (mala naljepnica ili termoskupljajuća cijev s natpisom).
Iste oznake su u dijagramima `wireviz/*.svg` i u popisu `wireviz/*.bom.tsv`.

| oznaka | od → do | žile (boja) |
|---|---|---|
| `S-P01` … `S-P06` | razvod/ESP32 #1 → HC-SR04 na mjestu | crvena 5 V, žuta TRIG, zelena ECHO, crna GND |
| `S-P0x-DJ` | djelitelj → ESP32 #1 | zelena ECHO 3,3 V, crna GND |
| `S-LED` | ESP32 #1 / razvod → LED traka | crvena 5 V, bijela DIN, crna GND |
| `S-PWR` | razvod → ESP32 #1 VIN | crvena 5 V, crna GND |
| `R-UL-SERVO`, `R-IZ-SERVO` | ESP32 #2 / razvod → servo | narančasta signal, crvena 5 V, smeđa GND |
| `R-UL-IR`, `R-IZ-IR` | ESP32 #2 → FC-51 | crvena 3,3 V, crna GND, žuta OUT |
| `R-UL-SVJ`, `R-IZ-SVJ` | ESP32 #2 → LED rampe | crvena, zelena, crna GND |
| `R-UL-TIPKA`, `R-IZ-TIPKA` | ESP32 #2 → tipka | bijela GPIO, crna GND |
| `R-PWR` | razvod → ESP32 #2 VIN | crvena 5 V, crna GND |
| `R-ZUJ` | ESP32 #2 → zujalica | crvena, crna |
| `PWR-IN` | adapter → sklopka → razvod | |

Pravila boja: **crvena = +5 V, narančasta/žuta/bijela = signal, crna/smeđa = GND**. Nikad crna za +5 V.
