# Proračun napajanja (5 V)

| potrošač | kom | tipično [mA] | vršno [mA] | ukupno vršno [mA] | napomena |
|---|---|---|---|---|---|
| ESP32 DevKit (Wi-Fi) | 2 | 80 | 300 | 600 | vrhovi pri slanju |
| HC-SR04 | 6 | 2 | 15 | 90 | mjeri jedan po jedan |
| SG90 servo | 2 | 10 | 700 (blokiran) | 1400 | u pokretu ~200 mA |
| WS2812B LED (svjetlina 40/255, jedna boja) | 6 | 5 | 60 (bijelo, puna svjetlina) | 360 | firmware ograničava svjetlinu |
| FC-51 IR (s 3,3 V regulatora ESP32) | 2 | 20 | 20 | 40 | |
| LED rampi + zujalica | – | 20 | 70 | 70 | |
| **ukupno** | | **~0,5 A** | | **~2,6 A** | najgori slučaj (oba servo blokirana) |

**Odabir: adapter 5 V / 4 A** → rezerva ~50 % i za najgori slučaj. Raspberry Pi ima zaseban adapter
(5 V / 3 A USB-C), jer pad napona pri pokretanju serva ne smije resetirati edge računalo.

Presjek vodiča: glavni razvod 5 V/GND ≥ 0,5 mm² (ili dvije Dupont žice paralelno); do senzora tanki 4-žilni kabel je dovoljan.
