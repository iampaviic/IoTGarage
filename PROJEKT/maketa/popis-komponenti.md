# Popis komponenti

CSV za tablični kalkulator: [popis-komponenti.csv](popis-komponenti.csv).

| kategorija | komponenta | kom | za što | napomena |
|---|---|---|---|---|
| elektronika | ESP32 DevKit V1 (ESP32-WROOM-32, 30 pinova) | 2 | cvor senzora + cvor rampi | provjeri da USB kabel prenosi podatke |
| elektronika | HC-SR04 ultrazvucni senzor | 6 | zauzetost mjesta | 5 V napajanje, ECHO preko djelitelja |
| elektronika | SG90 mikro servo | 2 | rampe | metalni zupcanici (MG90S) izdrzljiviji |
| elektronika | FC-51 IR senzor prepreke | 2 | vozilo na crti rampe | napajati s 3.3 V |
| elektronika | WS2812B LED (traka 60/m, 1 m ili 6 modula) | 1 | indikator po mjestu | 1 podatkovni pin |
| elektronika | LED 5 mm crvena + zelena | 4 | svjetla rampi | s otpornikom 220 Ohm |
| elektronika | tipkalo 6x6 mm | 2 | rucno otvaranje rampe | drzi 3 s = RESET |
| elektronika | aktivna zujalica 3.3 V | 1 | zvuk pri zatvaranju | opcionalno |
| elektronika | otpornik 1 kOhm | 6 | djelitelj ECHO |  |
| elektronika | otpornik 2 kOhm (ili 2x 1 kOhm) | 6 | djelitelj ECHO |  |
| elektronika | otpornik 220 Ohm | 4 | LED rampi |  |
| elektronika | otpornik 330 Ohm | 1 | podatkovna linija WS2812 |  |
| elektronika | elektrolitski kondenzator 1000 uF / 10 V | 2 | LED traka, servo | uz napajanje |
| napajanje | adapter 5 V / 4 A (bacva 5,5/2,1) | 1 | servo, senzori, LED, ESP32 |  |
| napajanje | zenska DC uticnica s vijcima | 1 |  |  |
| napajanje | sklopka (rocker) | 1 | jedna sklopka za cijelu maketu |  |
| napajanje | WAGO 221 spojnice (komplet) | 1 | razvod 5 V / GND |  |
| napajanje | USB kabel micro-USB (podatkovni) | 2 | programiranje ESP32 |  |
| spajanje | Dupont zice M-F, F-F, M-M (po 40) | 1 |  |  |
| spajanje | 4-zilni kabel (telefonski / ravni) 5 m | 1 | HC-SR04 |  |
| spajanje | protoboard / perfboard 7x9 cm | 2 | djelitelji, razvod |  |
| spajanje | termoskupljajuca cijev, vezice, naljepnice za kabele | 1 | oznake kabela |  |
| edge | Raspberry Pi 4 (imamo) + napajanje USB-C 5 V/3 A + microSD 32 GB | 1 | edge racunalo | Jetson Nano kao rezerva |
| edge | USB kamera 720p/1080p (imamo 1) | 1 | ALPR | druga kamera = varijanta A |
| mreza | putni Wi-Fi router (npr. TP-Link) | 1 | vlastita mreza makete | opcionalno, rizik R-07 |
| maketa | pjenasti PVC (Forex) 5 mm, ~1000 x 700 mm | 1 | baza, zidovi |  |
| maketa | letvice / PVC trake 10 x 10 mm | 4 | mostovi za senzore i kameru | ili 3D ispis |
| maketa | PLA filament | 0.3 | nosaci, rampe, mostovi (cijena po kg) |  |
| maketa | vijci M3 + matice (komplet) | 1 |  |  |
| maketa | autic 1:24 | 3 | vozila za demo |  |
| maketa | mat foto papir A4 / laminiranje | 5 | pločice | sjajni papir reflektira |
| maketa | bijela izolirka 5 mm | 1 | oznake mjesta |  |
