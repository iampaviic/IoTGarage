# Instalacija i pokretanje

Sve naredbe se pokreću iz mape `SOFTWARE`, osim ako piše drugačije. Detaljnije upute su u
[korisničkim uputama](../PROJEKT/dokumentacija/03-korisnicke-upute.md),
[tehničkoj dokumentaciji](../PROJEKT/dokumentacija/04-tehnicka-dokumentacija.md) i `README.md` svake podmape.

## 1. Preduvjeti

| program | Windows | Linux (Ubuntu) |
|---|---|---|
| git | [git-scm.com](https://git-scm.com/download/win) | `sudo apt install git` |
| Python ≥ 3.8 (preporuka 3.11 ili 3.12) | [python.org](https://www.python.org/downloads/), u instalaciji označi "Add python.exe to PATH" | `sudo apt install python3 python3-venv` |
| Tesseract OCR | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), zatim `C:\Program Files\Tesseract-OCR` dodaj u PATH | `sudo apt install tesseract-ocr` |
| Mosquitto | [mosquitto.org](https://mosquitto.org/download/), zatim `C:\Program Files\mosquitto` dodaj u PATH | `sudo apt install mosquitto mosquitto-clients` |
| Docker (ThingsBoard, opcionalno edge) | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (traži WSL 2) | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/ubuntu/) |
| VS Code + PlatformIO (firmware) | [code.visualstudio.com](https://code.visualstudio.com), zatim *Extensions* → "PlatformIO IDE" | isto, ili `pip install platformio` |

Opcionalno: OpenSCAD (3D dijelovi), WireViz i Graphviz (sheme ožičenja).

PATH na Windowsu: *Start* → "environment variables" → *Path* → *New*. Zatim otvori novi terminal i provjeri
`git --version`, `python --version`, `tesseract --version` i `docker --version`.

## 2. Python okruženje i testovi (laptop)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                             # svi testovi, ~1 min
```

Ako Windows PowerShell odbije `activate`, jednom pokreni `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
U svakom novom terminalu ponovno uđi u mapu `SOFTWARE` i aktiviraj `.venv` (u promptu piše `(.venv)`).

## 3. Cijeli sustav bez hardvera (simulacija)

```bash
python integracija/simulacija.py --broker
python integracija/simulacija.py --broker --interactive    # sam upravljaš, upute se ispišu
python -m garage_contract.monitor                          # u drugom terminalu: sve MQTT poruke
```

Simulacija pokreće Mosquitto, simulatore senzora i rampi, ALPR sa sintetskom kamerom, kontrolu pristupa i bazu te
odigra demo scenarij: ulaz, parkiranje, nečitljivu pločicu s ručnim odobrenjem, izlaz bez sesije i izlaz s cijenom.
Na kraju ispiše cijenu i `poruke koje krše ugovor: 0`.

## 4. ThingsBoard (laptop ili server s ≥ 4 GB RAM)

```bash
cd thingsboard
docker compose up -d                # prvo pokretanje traje par minuta
python provision/provision.py       # uređaji, alarmi, dashboardi; smije se pokrenuti više puta
```

Web je na <http://localhost:8080>, prijava `tenant@thingsboard.org` / `tenant`. Prije demonstracije promijeni
lozinku (ikona profila → *Change password*) i od tada `provision.py` pokreći s `--password <nova>`. Port 1884 je
MQTT za most s edge računala. Simulacija s ThingsBoardom: `python integracija/simulacija.py --broker --tb`.

## 5. Firmware za ESP32 (čvor senzora i čvor rampi)

Za svaki čvor (`senzori/firmware` i `rampe/firmware`):

1. Kopiraj `include/secrets.example.h` u `include/secrets.h` i upiši vrijednosti (`secrets.h` se ne komita):

   | vrijednost | značenje |
   |---|---|
   | `WIFI_SSID`, `WIFI_PASSWORD` | mreža makete |
   | `MQTT_HOST`, `MQTT_PORT` | IP edge računala, 1883 |
   | `MQTT_USER`, `MQTT_PASSWORD` | prazno = anonimno |
   | `NTP_SERVER` | izvor vremena |

2. `pio run -d senzori/firmware -t upload` prevede firmware i učita ga na ESP32. PlatformIO sam preuzme biblioteke
   iz `platformio.ini`.
3. `pio device monitor -d senzori/firmware` otvori serijski monitor (115200 baud).

Unit testovi na računalu, bez pločice: `pio test -e native -d senzori/firmware`. Pinovi i pragovi su u
`include/config.h`, a shema spajanja u [PROJEKT/maketa/shema-spajanja.md](../PROJEKT/maketa/shema-spajanja.md).

## 6. Edge računalo (Raspberry Pi ili Jetson Nano)

a) Docker (preporuka):

```bash
cp edge/edge.example.yaml edge/edge.yaml          # prilagoditi (kamera, pragovi)
cd edge/deploy
cp .env.example .env                              # upisati TB_HOST = IP računala s ThingsBoardom
docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml up -d --build
# bez kamere izostaviti docker-compose.camera.yml - sintetska kamera
```

b) Nativno (Raspberry Pi OS / Ubuntu, Python ≥ 3.8):

```bash
bash edge/deploy/install_native.sh
```

Skripta instalira Mosquitto i Tesseract, napravi `.venv` u ovoj mapi i kopira `edge/edge.example.yaml` u
`edge/edge.yaml`. Zatim prema uputama koje ispiše uključi systemd servise iz `edge/deploy/`. Jetson Nano
(JetPack 4.x) ima Python 3.6, pa na njemu koristi Docker ili `sudo apt install python3.8 python3.8-venv` i
`PYTHON=python3.8 bash edge/deploy/install_native.sh`.

Konfiguracija je u `edge/edge.yaml` (kamera, pragovi pouzdanosti, naplata, privatnost; objašnjenja su u
`edge.example.yaml`). Varijable okruženja nadjačavaju `edge.yaml`. Za Docker se postavljaju u `edge/deploy/.env`
(predložak `.env.example`: `TB_HOST`, `TB_GATEWAY_TOKEN`, `EDGE_CONFIG`, `PRICING_PROFILE`), a za nativnu
instalaciju u `.service` datotekama:

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
python maketa/elektronika/generiraj_sheme.py      # treba wireviz
openscad -o maketa/3d/stl/rampa_sg90.stl maketa/3d/rampa_sg90.scad
```

Gotovi STL dijelovi za 3D ispis su u `maketa/3d/stl/`. Popis komponenti i nacrt su u [PROJEKT/maketa](../PROJEKT/maketa).
