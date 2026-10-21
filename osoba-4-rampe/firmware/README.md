# Firmware čvora rampi (ESP32)

| datoteka | sadržaj |
|---|---|
| `platformio.ini` | `esp32dev` (Arduino) i `native` (unit testovi na PC-u) |
| `include/config.h` | pinovi obje rampe, kutovi serva, vremena (automatsko zatvaranje, debounce) |
| `include/secrets.example.h` | predložak za Wi-Fi/MQTT (kopiraj u `secrets.h`) |
| `lib/GateLogic/` | stroj stanja rampe (bez Arduina, testabilan) |
| `src/main.cpp` | servo (glatko pomicanje), IR, tipke (kratko/dugo), LED, zujalica, MQTT, serijske naredbe |
| `test/test_gate/` | Unity testovi stroja stanja |

```bash
pio run -t upload && pio device monitor
pio test -e native
```
Biblioteke: PubSubClient, ArduinoJson 7, ESP32Servo (PlatformIO ih preuzima sam).
