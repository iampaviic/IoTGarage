# Popis komponenti

Okvirne cijene (EUR, 2026, domaće trgovine / AliExpress) – provjerite prije narudžbe. CSV za tablični kalkulator: [popis-komponenti.csv](popis-komponenti.csv).

| kategorija | komponenta | kom | rezerva | ~€/kom | ~€ ukupno | za što | napomena |
|---|---|---|---|---|---|---|---|
| elektronika | ESP32 DevKit V1 (ESP32-WROOM-32, 30 pinova) | 2 | 1 | 8.00 | 24.00 | cvor senzora + cvor rampi | provjeri da USB kabel prenosi podatke |
| elektronika | HC-SR04 ultrazvucni senzor | 6 | 1 | 2.00 | 14.00 | zauzetost mjesta | 5 V napajanje, ECHO preko djelitelja |
| elektronika | SG90 mikro servo | 2 | 1 | 3.00 | 9.00 | rampe | metalni zupcanici (MG90S) izdrzljiviji |
| elektronika | FC-51 IR senzor prepreke | 2 | 1 | 1.50 | 4.50 | vozilo na crti rampe | napajati s 3.3 V |
| elektronika | WS2812B LED (traka 60/m, 1 m ili 6 modula) | 1 | 0 | 6.00 | 6.00 | indikator po mjestu | 1 podatkovni pin |
| elektronika | LED 5 mm crvena + zelena | 4 | 2 | 0.10 | 0.60 | svjetla rampi | s otpornikom 220 Ohm |
| elektronika | tipkalo 6x6 mm | 2 | 2 | 0.20 | 0.80 | rucno otvaranje rampe | drzi 3 s = RESET |
| elektronika | aktivna zujalica 3.3 V | 1 | 0 | 1.00 | 1.00 | zvuk pri zatvaranju | opcionalno |
| elektronika | otpornik 1 kOhm | 6 | 4 | 0.05 | 0.50 | djelitelj ECHO |  |
| elektronika | otpornik 2 kOhm (ili 2x 1 kOhm) | 6 | 4 | 0.05 | 0.50 | djelitelj ECHO |  |
| elektronika | otpornik 220 Ohm | 4 | 4 | 0.05 | 0.40 | LED rampi |  |
| elektronika | otpornik 330 Ohm | 1 | 1 | 0.05 | 0.10 | podatkovna linija WS2812 |  |
| elektronika | elektrolitski kondenzator 1000 uF / 10 V | 2 | 1 | 0.50 | 1.50 | LED traka, servo | uz napajanje |
| napajanje | adapter 5 V / 4 A (bacva 5,5/2,1) | 1 | 0 | 10.00 | 10.00 | servo, senzori, LED, ESP32 |  |
| napajanje | zenska DC uticnica s vijcima | 1 | 0 | 1.00 | 1.00 |  |  |
| napajanje | sklopka (rocker) | 1 | 0 | 1.00 | 1.00 | jedna sklopka za cijelu maketu |  |
| napajanje | WAGO 221 spojnice (komplet) | 1 | 0 | 5.00 | 5.00 | razvod 5 V / GND |  |
| napajanje | USB kabel micro-USB (podatkovni) | 2 | 1 | 2.00 | 6.00 | programiranje ESP32 |  |
| spajanje | Dupont zice M-F, F-F, M-M (po 40) | 1 | 0 | 5.00 | 5.00 |  |  |
| spajanje | 4-zilni kabel (telefonski / ravni) 5 m | 1 | 0 | 5.00 | 5.00 | HC-SR04 |  |
| spajanje | protoboard / perfboard 7x9 cm | 2 | 1 | 1.50 | 4.50 | djelitelji, razvod |  |
| spajanje | termoskupljajuca cijev, vezice, naljepnice za kabele | 1 | 0 | 6.00 | 6.00 | oznake kabela |  |
| edge | Raspberry Pi 4 (imamo) + napajanje USB-C 5 V/3 A + microSD 32 GB | 1 | 0 | 12.00 | 0.00 | edge racunalo | Jetson Nano kao rezerva |
| edge | USB kamera 720p/1080p (imamo 1) | 1 | 1 | 20.00 | 20.00 | ALPR | druga kamera = varijanta A |
| mreza | putni Wi-Fi router (npr. TP-Link) | 1 | 0 | 25.00 | 25.00 | vlastita mreza makete | opcionalno, rizik R-07 |
| maketa | pjenasti PVC (Forex) 5 mm, ~1000 x 700 mm | 1 | 0 | 20.00 | 20.00 | baza, zidovi |  |
| maketa | letvice / PVC trake 10 x 10 mm | 4 | 0 | 1.50 | 6.00 | mostovi za senzore i kameru | ili 3D ispis |
| maketa | PLA filament | 0.3 | 0 | 20.00 | 6.00 | nosaci, rampe, mostovi (cijena po kg) |  |
| maketa | vijci M3 + matice (komplet) | 1 | 0 | 5.00 | 5.00 |  |  |
| maketa | autic 1:24 | 3 | 0 | 12.00 | 36.00 | vozila za demo |  |
| maketa | mat foto papir A4 / laminiranje | 5 | 0 | 0.50 | 2.50 | pločice | sjajni papir reflektira |
| maketa | bijela izolirka 5 mm | 1 | 0 | 2.00 | 2.00 | oznake mjesta |  |

**Okvirno ukupno: 229 €** (bez stvari koje već imamo; s rezervnim dijelovima).

Već imamo: Raspberry Pi, Jetson Nano, jednu USB kameru.

Lista za kupnju po prioritetu: (1) ESP32, HC-SR04, SG90, FC-51, otpornici, napajanje – potrebno u 1. tjednu za dokaz izvedivosti; (2) materijal makete, filament, autići; (3) druga kamera, router, LED traka.
