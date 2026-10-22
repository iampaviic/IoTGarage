# Instalacija i pokretanje

Sve naredbe se pokreću iz mape `SOFTWARE` (osim ako piše drugačije). Detaljnije upute:
[korisničke upute](../PROJEKT/dokumentacija/03-korisnicke-upute.md),
[tehnička dokumentacija](../PROJEKT/dokumentacija/04-tehnicka-dokumentacija.md) i `README.md` u svakoj podmapi.

## 1. Preduvjeti

- Python ≥ 3.8, git
- Tesseract OCR i Mosquitto MQTT broker
  - Linux: `sudo apt install tesseract-ocr mosquitto`
  - Windows: instalacijski programi s [tesseract-ocr.github.io](https://tesseract-ocr.github.io/tessdoc/Installation.html)
    i [mosquitto.org](https://mosquitto.org/download/)
- Docker (za ThingsBoard, opcionalno za edge računalo)
- PlatformIO (VS Code ekstenzija ili `pip install platformio`) – firmware
- opcionalno: OpenSCAD (3D dijelovi), WireViz + Graphviz (sheme ožičenja)

## 2. Python okruženje i testovi (laptop)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                             # svi testovi, ~1 min
```

## 3. Cijeli sustav bez hardvera (simulacija)

```bash
python integracija/simulacija.py --broker
python integracija/simulacija.py --broker --interactive
```

Pokreće Mosquitto, simulatore senzora i rampi, ALPR sa sintetskom kamerom, kontrolu pristupa i bazu te odigra
demo scenarij.

## 4. ThingsBoard (laptop ili server s ≥ 4 GB RAM)

```bash
cd thingsboard
docker compose up -d                # prvo pokretanje traje par minuta
python provision/provision.py       # uređaji, alarmi, dashboardi
```

Web: <http://localhost:8080>, prijava `tenant@thingsboard.org` / `tenant` (**promijeniti lozinku!**).
Port 1884 = MQTT za most s edge računala. Simulacija s ThingsBoardom: `python integracija/simulacija.py --broker --tb`.

## 5. Firmware za ESP32 (čvor senzora i čvor rampi)

Za svaki čvor (`senzori/firmware` i `rampe/firmware`):

1. Kopirati `include/secrets.example.h` u `include/secrets.h` i upisati (`secrets.h` se ne komita):

   | vrijednost | značenje |
   |---|---|
   | `WIFI_SSID`, `WIFI_PASSWORD` | mreža makete |
   | `MQTT_HOST`, `MQTT_PORT` | IP edge računala, 1883 |
   | `MQTT_USER`, `MQTT_PASSWORD` | prazno = anonimno |
   | `NTP_SERVER` | izvor vremena |

2. `pio run -d senzori/firmware -t upload`
3. `pio device monitor -d senzori/firmware` (115200 baud)

Pinovi i pragovi: `include/config.h`; shema spajanja: [PROJEKT/maketa/shema-spajanja.md](../PROJEKT/maketa/shema-spajanja.md).

## 6. Edge računalo (Raspberry Pi ili Jetson Nano)

**a) Docker (preporuka):**

```bash
cd edge/deploy
docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml up -d --build
# bez kamere izostaviti docker-compose.camera.yml - sintetska kamera
```

**b) Nativno (Raspberry Pi OS / Ubuntu, Python ≥ 3.8):**

```bash
bash edge/deploy/install_native.sh
```

Skripta instalira Mosquitto i Tesseract, napravi `.venv` u ovoj mapi i kopira `edge/edge.example.yaml` u
`edge/edge.yaml`; zatim prema uputama koje ispiše uključiti systemd servise iz `edge/deploy/`.

**Konfiguracija:** `edge/edge.yaml` (kamera, pragovi pouzdanosti, naplata, privatnost; objašnjenja su u
`edge.example.yaml`). Varijable okruženja nadjačavaju `edge.yaml`; za Docker se postavljaju u
`docker-compose.edge.yml`, za nativnu instalaciju u `.service` datotekama:

| varijabla | značenje |
|---|---|
| `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_KEEPALIVE` | MQTT broker |
| `GARAGE_DB` | putanja SQLite baze sesija |
| `GARAGE_SPOTS` | broj parkirnih mjesta |
| `PRICING_PROFILE` | `real` ili `demo` (demo: 1 minuta = 1 sat) |
| `ALPR_SOURCE` | `camera`, `sim` (sintetske slike) ili `images` (mapa s fotografijama, `images_dir` u `edge.yaml`) |
| `TB_HOST`, `TB_MQTT_PORT`, `TB_GATEWAY_TOKEN` | ThingsBoard za most |
| `TB_BUFFER` | datoteka međuspremnika kad ThingsBoard nije dostupan |
| `TB_URL`, `TB_USER`, `TB_PASSWORD` | za `provision.py` i alate |

## 7. Maketa

```bash
python maketa/alati/tlocrt.py --scale 24 --spots 6 --print-tiles
python maketa/alati/kamera_kalkulator.py
python maketa/elektronika/generiraj_sheme.py   # treba wireviz
```

STL dijelovi za 3D ispis: `maketa/3d/stl/`. Popis komponenti i nacrt: [PROJEKT/maketa](../PROJEKT/maketa).
