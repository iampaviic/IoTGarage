SOFTWARE - izvorni programski kod
=================================

Instalacija i pokretanje: INSTALL.TXT. Svaka podmapa ima README.md s
detaljnim uputama za taj dio sustava (tko je zaduzen, kako se koristi,
sto jos treba napraviti). Kod je na engleskom, upute na hrvatskom.

ugovor/              Python paket garage_contract: MQTT teme, 15 JSON shema
                     poruka, validacija, MQTT klijent, monitor poruka.
                     Komunikacijski ugovor kao kod - koriste ga svi dijelovi.
integracija/         simulacija cijelog sustava na jednom racunalu
                     (simulacija.py, scenarij.py), konfiguracija Mosquitta,
                     end-to-end testovi
senzori/             cvor senzora mjesta: firmware za ESP32 + 6x HC-SR04
                     (C++, PlatformIO projekt u firmware/), Python simulator,
                     alati za kalibraciju i test 20x
rampe/               cvor rampi: firmware za ESP32 + 2x servo, IR senzori,
                     tipke (C++, PlatformIO projekt u firmware/), Python
                     simulator i blizanac stroja stanja s testovima
alpr/                Python paket plate_detector: detekcija registarske
                     plocice (OpenCV), generator izmisljenih plocica za ispis,
                     sintetski skup slika, alati za snimanje, oznacavanje i
                     mjerenje tocnosti (rezultati/)
edge/                Python paket garage-edge: OCR (plate_ocr), ALPR servis i
                     lokalna kontrola pristupa (edge_service), konfiguracija
                     edge.example.yaml, deploy/ (Docker, nativna instalacija,
                     systemd servisi za Raspberry Pi / Jetson Nano)
thingsboard/         ThingsBoard CE (docker-compose.yml), provisioning uredjaja
                     i alarma (provision/), most MQTT -> ThingsBoard s
                     medjuspremnikom (bridge/), dva dashboarda (dashboards/)
baza/                Python paket parking_sessions: SQLite baza parkirnih
                     sesija, naplata, allow-lista, CLI parking-sessions
maketa/              izvorne datoteke makete: 3D dijelovi (OpenSCAD .scad +
                     gotovi .stl u 3d/), generator tlocrta i kalkulator
                     kamere (alati/), tlocrt (nacrt/), dijagrami ozicenja
                     (WireViz, elektronika/)
mobilna-aplikacija/  mobilna aplikacija za analitiku garaze (u izradi)
izvrsne-verzije/     izvrsne verzije (firmware .bin, Docker slika, APK) -
                     dodaju se na kraju projekta, vidi README.TXT u mapi

requirements-dev.txt sve Python ovisnosti za razvoj i testove
pytest.ini           popis testova; "pytest" iz ove mape pokrece sve

Prevodjenje
-----------
Python: nije potrebno (pip install, vidi INSTALL.TXT).
Firmware: PlatformIO, uobicajene naredbe:
    pio run -d senzori/firmware                 prevodjenje
    pio run -d senzori/firmware -t upload       prevodjenje + upload na ESP32
    pio test -e native -d senzori/firmware      unit testovi na racunalu
(isto za rampe/firmware). Ovisnosti (PubSubClient, ArduinoJson, ...)
PlatformIO preuzima sam prema platformio.ini.
3D dijelovi: openscad -o dio.stl dio.scad (gotovi STL-ovi su u maketa/3d/stl/).
