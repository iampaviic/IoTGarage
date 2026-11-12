# SOFTWARE – izvorni programski kod

<!-- gitlab:od-tjedna=9 -->
Instalacija i pokretanje: [INSTALL.md](INSTALL.md).
<!-- /gitlab -->

Svaka podmapa ima `README.md` s uputama za taj dio sustava: tko je zadužen, kako se koristi i što još treba
napraviti. Kod je na engleskom, upute na hrvatskom.

| mapa | sadržaj |
|---|---|
| [ugovor/](ugovor) | Python paket `garage_contract`: `tb.py` – imena uređaja i gateway klijent za ThingsBoard (varijanta B); MQTT teme, 15 JSON shema, validacija i monitor varijante A |
| [integracija/](integracija) | simulacija cijelog sustava: `simulacija_b.py` (varijanta B, s ThingsBoardom, scenarij s provjerom svakog koraka); `simulacija.py`, `scenarij.py`, Mosquitto (varijanta A); end-to-end testovi |
| [senzori/](senzori) | čvor senzora mjesta: firmware za ESP32 + 6× HC-SR04 (C++, PlatformIO projekt u `firmware/`, gateway `esp32-spots` u ThingsBoardu), simulator, alati za kalibraciju i test 20× |
| [rampe/](rampe) | čvor rampi: firmware za ESP32 + 2× servo, IR senzori, tipke (C++, PlatformIO projekt u `firmware/`, gateway `esp32-gates`), simulator i blizanac stroja stanja s testovima |
| [alpr/](alpr) | Python paket `plate_detector`: detekcija registarske pločice (OpenCV), generator izmišljenih pločica za ispis, sintetski skup slika, alati za snimanje, označavanje i mjerenje točnosti (`rezultati/`) |
| [edge/](edge) | Python paket `garage-edge`: OCR (`plate_ocr`), ALPR servis kao uređaj ThingsBoarda (`edge_service tb-alpr`), konfiguracija `edge.example.yaml`, `deploy/` (Docker, nativna instalacija, systemd); lokalna kontrola pristupa varijante A |
| [thingsboard/](thingsboard) | ThingsBoard CE (`docker-compose.yml`), rule chain s odlukama, sesijama i naplatom (`rulechain/`), provisioning (`provision/`), dva dashboarda (`dashboards/`); most za varijantu A (`bridge/`) |
| [baza/](baza) | varijanta A (rezerva): Python paket `parking_sessions`, SQLite baza parkirnih sesija, naplata, allow-lista, CLI |
| [maketa/](maketa) | izvorne datoteke makete: 3D dijelovi (OpenSCAD `.scad` + gotovi `.stl` u `3d/`), generator tlocrta i kalkulator kamere (`alati/`), tlocrt (`nacrt/`), dijagrami ožičenja (WireViz, `elektronika/`) |
| [mobilna-aplikacija/](mobilna-aplikacija) | mobilna aplikacija za analitiku garaže (u izradi) |
| [izvrsne-verzije/](izvrsne-verzije) | izvršne verzije (firmware `.bin`, Docker slika, APK), dodaju se na kraju projekta |
| `requirements-dev.txt` | sve Python ovisnosti za razvoj i testove |
| `pytest.ini` | popis testova; `pytest` iz ove mape pokreće sve |

## Prevođenje

Python paketi se ne prevode, nego se instaliraju s `pip install -r requirements-dev.txt`. Firmware se prevodi
PlatformIO-om (`pio run`), a 3D dijelovi OpenSCAD-om. Naredbe su u [INSTALL.md](INSTALL.md).
