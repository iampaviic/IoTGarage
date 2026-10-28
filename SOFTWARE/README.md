# SOFTWARE – izvorni programski kod

<!-- gitlab:od-tjedna=9 -->
Instalacija i pokretanje: [INSTALL.md](INSTALL.md).
<!-- /gitlab -->

Svaka podmapa ima `README.md` s detaljnim uputama za taj dio sustava (tko je zadužen, kako se koristi, što još
treba napraviti). Kod je na engleskom, upute na hrvatskom.

| mapa | sadržaj |
|---|---|
| [ugovor/](ugovor) | Python paket `garage_contract`: MQTT teme, 15 JSON shema poruka, validacija, MQTT klijent, monitor poruka – komunikacijski ugovor kao kod, koriste ga svi dijelovi |
| [integracija/](integracija) | simulacija cijelog sustava na jednom računalu (`simulacija.py`, `scenarij.py`), konfiguracija Mosquitta, end-to-end testovi |
| [senzori/](senzori) | čvor senzora mjesta: firmware za ESP32 + 6× HC-SR04 (C++, PlatformIO projekt u `firmware/`), Python simulator, alati za kalibraciju i test 20× |
| [rampe/](rampe) | čvor rampi: firmware za ESP32 + 2× servo, IR senzori, tipke (C++, PlatformIO projekt u `firmware/`), Python simulator i blizanac stroja stanja s testovima |
| [alpr/](alpr) | Python paket `plate_detector`: detekcija registarske pločice (OpenCV), generator izmišljenih pločica za ispis, sintetski skup slika, alati za snimanje, označavanje i mjerenje točnosti (`rezultati/`) |
| [edge/](edge) | Python paket `garage-edge`: OCR (`plate_ocr`), ALPR servis i lokalna kontrola pristupa (`edge_service`), konfiguracija `edge.example.yaml`, `deploy/` (Docker, nativna instalacija, systemd servisi za Raspberry Pi / Jetson Nano) |
| [thingsboard/](thingsboard) | ThingsBoard CE (`docker-compose.yml`), provisioning uređaja i alarma (`provision/`), most MQTT → ThingsBoard s međuspremnikom (`bridge/`), dva dashboarda (`dashboards/`) |
| [baza/](baza) | Python paket `parking_sessions`: SQLite baza parkirnih sesija, naplata, allow-lista, CLI `parking-sessions` |
| [maketa/](maketa) | izvorne datoteke makete: 3D dijelovi (OpenSCAD `.scad` + gotovi `.stl` u `3d/`), generator tlocrta i kalkulator kamere (`alati/`), tlocrt (`nacrt/`), dijagrami ožičenja (WireViz, `elektronika/`) |
| [mobilna-aplikacija/](mobilna-aplikacija) | mobilna aplikacija za analitiku garaže (u izradi) |
| [izvrsne-verzije/](izvrsne-verzije) | izvršne verzije (firmware `.bin`, Docker slika, APK) – dodaju se na kraju projekta |
| `requirements-dev.txt` | sve Python ovisnosti za razvoj i testove |
| `pytest.ini` | popis testova; `pytest` iz ove mape pokreće sve |

## Prevođenje

- **Python:** nije potrebno – pakete instalira `pip install -r requirements-dev.txt`.
<!-- gitlab:od-tjedna=3 -->
- **Firmware:** PlatformIO, uobičajene naredbe (isto za `rampe/firmware`); ovisnosti (PubSubClient, ArduinoJson, …)
  PlatformIO preuzima sam prema `platformio.ini`:

  ```bash
  pio run -d senzori/firmware                 # prevođenje
  pio run -d senzori/firmware -t upload       # prevođenje + upload na ESP32
  pio test -e native -d senzori/firmware      # unit testovi na računalu
  ```

- **3D dijelovi:** `openscad -o dio.stl dio.scad` (gotovi STL-ovi su u `maketa/3d/stl/`).
<!-- /gitlab -->
