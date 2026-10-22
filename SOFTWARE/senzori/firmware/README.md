# Firmware čvora senzora (ESP32)

| datoteka | sadržaj |
|---|---|
| `platformio.ini` | `esp32dev` (Arduino) i `native` (unit testovi na PC-u) |
| `include/config.h` | pinovi, pragovi po mjestu, vremena, LED traka |
| `include/secrets.example.h` | predložak za Wi-Fi/MQTT (kopiraj u `secrets.h`, ne komitaj) |
| `lib/OccupancyFilter/` | filtar zauzetosti (bez Arduina, testabilan) |
| `src/main.cpp` | mjerenje, MQTT, reconnect, Last Will, heartbeat, NTP, LED, serijske naredbe, simulacija |
| `test/test_filter/` | Unity testovi filtra |

```bash
pio run                 # prevođenje
pio run -t upload       # upload na ESP32
pio device monitor      # serijski monitor (115200)
pio test -e native      # testovi filtra na PC-u
```
Biblioteke (PubSubClient, ArduinoJson 7, Adafruit NeoPixel) PlatformIO preuzima sam.
Arduino IDE: otvori `src/main.cpp` kao sketch, kopiraj `lib/OccupancyFilter/*` i `include/*` u mapu sketcha
i instaliraj iste biblioteke iz Library Managera.
