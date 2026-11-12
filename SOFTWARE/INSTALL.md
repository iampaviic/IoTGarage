# Instalacija i pokretanje

Upute su za odabranu [varijantu B](../PROJEKT/sustav/varijanta-b.md): ThingsBoard na laptopu, oba ESP32 i ALPR
servis spojeni izravno na njega. Varijanta A (rezerva) je na kraju, u [§ 8](#8-varijanta-a-rezerva).
Sve naredbe se pokreću iz mape `SOFTWARE`, osim ako piše drugačije. Detaljnije upute su u
[korisničkim uputama](../PROJEKT/dokumentacija/03-korisnicke-upute.md),
[tehničkoj dokumentaciji](../PROJEKT/dokumentacija/04-tehnicka-dokumentacija.md) i `README.md` svake podmape.

## 1. Preduvjeti

| program | Windows | Linux (Ubuntu) |
|---|---|---|
| git | [git-scm.com](https://git-scm.com/download/win) | `sudo apt install git` |
| Python ≥ 3.8 (preporuka 3.11 ili 3.12) | [python.org](https://www.python.org/downloads/), u instalaciji označi "Add python.exe to PATH" | `sudo apt install python3 python3-venv` |
| Tesseract OCR | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), zatim `C:\Program Files\Tesseract-OCR` dodaj u PATH | `sudo apt install tesseract-ocr` |
| Docker (ThingsBoard, opcionalno ALPR) | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (traži WSL 2) | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/ubuntu/) |
| VS Code + PlatformIO (firmware) | [code.visualstudio.com](https://code.visualstudio.com), zatim *Extensions* → "PlatformIO IDE" | isto, ili `pip install platformio` |

Opcionalno: OpenSCAD (3D dijelovi), WireViz i Graphviz (sheme ožičenja), Mosquitto (samo varijanta A).

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

## 3. ThingsBoard (laptop ili server s ≥ 4 GB RAM)

```bash
docker compose -f thingsboard/docker-compose.yml up -d    # prvo pokretanje traje par minuta
python thingsboard/provision/provision.py --demo-pricing   # sve za varijantu B; smije se pokrenuti više puta
```

`provision.py` pričeka da se ThingsBoard pokrene (do 5 min, `--wait`) i napravi profile s alarmima, uređaje, gateway uređaje `esp32-spots`, `esp32-gates` i `alpr-service` s
*access tokenima* (ispiše ih), asset „Garage“ s postavkama naplate i pravila, root rule chain i dashboarde.
Ponovno pokretanje ne briše sesije ni promijenjene postavke. `--demo-pricing`: 1 minuta se naplaćuje kao 1 sat.

Web je na <http://localhost:8080>, prijava `tenant@thingsboard.org` / `tenant`. MQTT za uređaje je port 1883
(ako na istom računalu radi Mosquitto, u `docker-compose.yml` stavi `1884:1883`). Prije demonstracije:

- promijeni lozinku (ikona profila → *Change password*) i od tada `provision.py` pokreći s `--password <nova>`;
- postavi tajne tokene: `TB_TOKEN_SPOTS=… TB_TOKEN_GATES=… TB_TOKEN_ALPR=… python thingsboard/provision/provision.py`
  i iste upiši u `secrets.h` oba ESP32 i u `edge/edge.yaml` (tokeni se ne komitaju).

Postavke odluke i naplate su server atributi asseta *Garage* (*Entities → Assets → Garage → Attributes*): `policy`,
`allowlist`, `acceptThreshold`, `freeMinutes`, `pricePerHourCents`, `dailyCapCents`, `timeMultiplier`.

## 4. Cijeli sustav bez hardvera (simulacija)

Uz pokrenuti ThingsBoard (§ 3):

```bash
python integracija/simulacija_b.py                 # demo scenarij, svaki korak se provjeri u ThingsBoardu
python integracija/simulacija_b.py --alpr sim      # isto s pravim ALPR-om i OCR-om na sintetskim slikama
python integracija/simulacija_b.py --interactive   # samo simulirani uređaji; upravljaš s dashboarda
```

Scenarij: ulaz, parkiranje, nečitljiva pločica s ručnim odobrenjem, vozilo već unutra, izlaz s cijenom, nepoznato
vozilo, puna garaža i gubitak veze čvora senzora. **Briše parkirne sesije**, pa ga ne pokreći na ThingsBoardu za
demonstraciju. Pojedini simulatori: `senzori/simulator/spot_simulator_tb.py`, `rampe/simulator/gate_simulator_tb.py`
(varijable `TB_HOST`, `TB_MQTT_PORT`, `TB_TOKEN_SPOTS`, `TB_TOKEN_GATES`).

## 5. Firmware za ESP32 (čvor senzora i čvor rampi)

Za svaki čvor (`senzori/firmware` i `rampe/firmware`):

1. Kopiraj `include/secrets.example.h` u `include/secrets.h` i upiši vrijednosti (`secrets.h` se ne komita):

   | vrijednost | značenje |
   |---|---|
   | `WIFI_SSID`, `WIFI_PASSWORD` | mreža makete |
   | `TB_HOST`, `TB_PORT` | IP laptopa s ThingsBoardom, 1883 |
   | `TB_TOKEN` | *access token* uređaja `esp32-spots` odnosno `esp32-gates` (ispiše ga `provision.py`) |

2. `pio run -d senzori/firmware -t upload` prevede firmware i učita ga na ESP32. PlatformIO sam preuzme biblioteke
   iz `platformio.ini`.
3. `pio device monitor -d senzori/firmware` otvori serijski monitor (115200 baud).

Unit testovi na računalu, bez pločice: `pio test -e native -d senzori/firmware`. Pinovi i pragovi su u
`include/config.h`, a shema spajanja u [PROJEKT/maketa/shema-spajanja.md](../PROJEKT/maketa/shema-spajanja.md).
U serijskom monitoru `ThingsBoard: connected` znači da je token dobar; `rc=4` ili `rc=5` znači pogrešan token.

## 6. ALPR servis (laptop, Raspberry Pi ili Jetson Nano uz kameru)

ALPR je uređaj `alpr-service` u ThingsBoardu i odgovara na RPC `readPlate`. Može raditi na istom laptopu kao
ThingsBoard.

```bash
cp edge/edge.example.yaml edge/edge.yaml      # kamera i sekcija thingsboard: host, port, token alpr-service
python -m edge_service --config edge/edge.yaml tb-alpr
ALPR_SOURCE=sim python -m edge_service --config edge/edge.yaml tb-alpr    # bez kamere: sintetske slike
```

Docker (Raspberry Pi / Jetson):

```bash
cd edge/deploy
cp .env.example .env                          # TB_HOST, TB_TOKEN_ALPR, EDGE_CONFIG
docker compose -f docker-compose.alpr.yml -f docker-compose.alpr-camera.yml up -d --build
# bez kamere izostaviti docker-compose.alpr-camera.yml - sintetska kamera
```

Nativno (Raspberry Pi OS / Ubuntu, Python ≥ 3.8): `bash edge/deploy/install_native.sh`, zatim systemd servis
`edge/deploy/garage-alpr.service` prema uputama koje skripta ispiše. Jetson Nano (JetPack 4.x) ima Python 3.6, pa na
njemu koristi Docker ili `PYTHON=python3.8 bash edge/deploy/install_native.sh`.

| varijabla | značenje |
|---|---|
| `TB_HOST`, `TB_MQTT_PORT`, `TB_TOKEN_ALPR` | ThingsBoard i token za ALPR (nadjačavaju `edge.yaml`) |
| `ALPR_SOURCE` | `camera`, `sim` (sintetske slike) ili `images` (mapa s fotografijama, `images_dir` u `edge.yaml`) |
| `TB_URL`, `TB_USER`, `TB_PASSWORD` | REST API za `provision.py`, `simulacija_b.py` i alate |

## 7. Maketa

```bash
python maketa/alati/tlocrt.py --scale 24 --spots 6 --print-tiles
python maketa/alati/kamera_kalkulator.py
python maketa/elektronika/generiraj_sheme.py      # treba wireviz
openscad -o maketa/3d/stl/rampa_sg90.stl maketa/3d/rampa_sg90.scad
```

Gotovi STL dijelovi za 3D ispis su u `maketa/3d/stl/`. Popis komponenti i nacrt su u [PROJEKT/maketa](../PROJEKT/maketa).

## 8. Varijanta A (rezerva)

Lokalni Mosquitto, access control i SQLite na edge računalu, bridge prema ThingsBoardu
([arhitektura.md](../PROJEKT/sustav/arhitektura.md)). Ne koristi se, ali kod i testovi su ispravni:

```bash
python integracija/simulacija.py --broker       # treba Mosquitto
python thingsboard/provision/provision.py --varijanta a   # Garage-Edge gateway za tb_bridge, bez rule chaina
cd edge/deploy && docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml up -d --build
```

Firmware za varijantu A je u git povijesti (prije odluke D-012); nadzorni dashboardi u repozitoriju su za B.
