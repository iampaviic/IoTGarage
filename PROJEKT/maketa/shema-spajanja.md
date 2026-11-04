# Shema spajanja

Dijagrami ožičenja (generirani iz istih pinova kao firmware): **[čvor senzora](../../SOFTWARE/maketa/elektronika/wireviz/cvor-senzora.svg)**,
**[čvor rampi](../../SOFTWARE/maketa/elektronika/wireviz/cvor-rampi.svg)**, popisi kabela `wireviz/*.bom.tsv`. Ponovno generiranje:
`python SOFTWARE/maketa/elektronika/generiraj_sheme.py` (treba `pip install wireviz` i Graphviz).

> Pinovi su definirani u `SOFTWARE/senzori/firmware/include/config.h` i `SOFTWARE/rampe/firmware/include/config.h`.
> Mijenjaju se **prvo tamo**, zatim u `generiraj_sheme.py` i ovoj tablici.

## Čvor senzora (ESP32 #1, `esp32-spots`)

| mjesto | TRIG | ECHO (preko djelitelja!) | kabel |
|---|---|---|---|
| P01 | GPIO23 | GPIO36 (VP) | S-P01 |
| P02 | GPIO22 | GPIO39 (VN) | S-P02 |
| P03 | GPIO21 | GPIO34 | S-P03 |
| P04 | GPIO19 | GPIO35 | S-P04 |
| P05 | GPIO18 | GPIO32 | S-P05 |
| P06 | GPIO5 | GPIO33 | S-P06 |
| LED traka WS2812B (DIN) | GPIO25 (preko 330 Ω) | – | S-LED |

GPIO 34–39 su samo ulazi i nemaju pull-up – idealni za ECHO.

### Djelitelj napona za ECHO (OBAVEZNO)

HC-SR04 radi na 5 V i ECHO izlaz daje **5 V**; ESP32 ulazi podnose najviše **3,3 V**.

```
HC-SR04 ECHO ──[ 1 kΩ ]──┬── ESP32 GPIO (ECHO)
                          │
                       [ 2 kΩ ]
                          │
GND ──────────────────────┴── GND
```
5 V × 2/(1+2) = 3,33 V. Dva otpornika od 1 kΩ u seriji = 2 kΩ. Prije spajanja ESP32 izmjeri
multimetrom napon na izlazu djelitelja dok senzor mjeri (≤ 3,4 V).

## Čvor rampi (ESP32 #2, `esp32-gates`)

| funkcija | ulaz | izlaz | kabel |
|---|---|---|---|
| servo (signal) | GPIO13 | GPIO14 | R-UL-SERVO / R-IZ-SERVO |
| IR senzor FC-51 (OUT, LOW = vozilo) | GPIO34 | GPIO35 | R-UL-IR / R-IZ-IR |
| crvena LED (220 Ω) | GPIO25 | GPIO27 | R-UL-SVJ / R-IZ-SVJ |
| zelena LED (220 Ω) | GPIO26 | GPIO33 | R-UL-SVJ / R-IZ-SVJ |
| tipka ručnog otvaranja (prema GND) | GPIO18 | GPIO19 | R-UL-TIPKA / R-IZ-TIPKA |
| zujalica (opcionalno) | GPIO23 | | R-ZUJ |

- **Servo se napaja s 5 V iz adaptera, ne s ESP32!** Signal (3,3 V) radi bez pretvarača.
- **FC-51 napajati s 3,3 V** (pin 3V3 ESP32) – tada je i njegov izlaz 3,3 V. Na 5 V bi izlaz bio 5 V (opasno za GPIO 34/35).
- Tipka između GPIO i GND, firmware uključuje interni pull-up.

## Napajanje i masa

```
adapter 5 V / 4 A ── sklopka ──┬── WAGO +5V ── HC-SR04 x6, servo x2, LED traka (+1000 µF), ESP32 #1 VIN, ESP32 #2 VIN
                               └── WAGO GND ── SVE mase (zajednička masa je obavezna!)
Raspberry Pi: vlastiti USB-C adapter; USB kamera na Pi.
```
- Kondenzator 1000 µF uz servo napajanje i uz LED traku (pazi na polaritet).
- Dok je ESP32 spojen USB-om na laptop i 5 V adapter je uključen: većina DevKit pločica ima diodu na USB 5 V
  pa je to sigurno – ipak, za programiranje je najsigurnije isključiti adapter.
- Proračun struje: [proracun-napajanja.md](proracun-napajanja.md). Oznake kabela: [oznake-kabela.md](oznake-kabela.md).
