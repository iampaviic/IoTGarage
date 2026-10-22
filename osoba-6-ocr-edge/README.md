# Osoba 6 – OCR, obrada registracije i edge servis

**Zaduženi:** Lukas Davorija (OCR, ALPR servis, edge računalo) i Luka Oslić (pravila odluke i access control – `edge_service/decisions.py`, `edge_service/access_control.py`). Zamjena za ALPR: Sven Matić.

Ti čitaš i validiraš registraciju te **donosiš lokalnu odluku** o ulasku/izlasku. Tvoj servis je "mozak" edge računala.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [plate_ocr/preprocess.py](plate_ocr/preprocess.py) | priprema izreza: makne plavu EU traku, **izbriše grb** (inače se čita kao H/B/3/I), makne rub, polaritet, skaliranje |
| [plate_ocr/engines.py](plate_ocr/engines.py) | dva OCR motora: **Tesseract** (opći) i **predlošci** (usporedba sa znakovima istog fonta kojim tiskamo pločice) |
| [plate_ocr/normalize.py](plate_ocr/normalize.py) | normalizacija po formatu HR registracije: O↔0, I↔1, B↔8, S↔5, Z↔2, G↔6 ovisno o poziciji, uklanjanje smeća (grb, rub), popis oznaka gradova |
| [plate_ocr/reader.py](plate_ocr/reader.py) | glasanje svih motora × varijanti → registracija + pouzdanost + razina (`ACCEPT/RETRY/MANUAL`) |
| [edge_service/decisions.py](edge_service/decisions.py) | čista pravila odluke (pragovi 0.85/0.60, 3 pokušaja) – **testirano da se ispod praga nikad ne otvara** |
| [edge_service/access_control.py](edge_service/access_control.py) | access control: stanja mjesta i rampi, ALPR okidači, ponovni pokušaji, sesije, naredbe rampi s potvrdom i ponavljanjem, alarmi, ručne radnje |
| [edge_service/alpr_service.py](edge_service/alpr_service.py) | ALPR servis: kamera / sintetska kamera / mapa slika → detekcija (osoba 5) → OCR → `alpr/<gate>/event` |
| [edge_service/__main__.py](edge_service/__main__.py) | naredbe: `all`, `access`, `alpr`, `read` (offline), `manual` (operater) |
| [edge.example.yaml](edge.example.yaml) | konfiguracija s objašnjenjima |
| [deploy/](deploy) | Docker image + compose za Raspberry Pi/Jetson, nativna instalacija, systemd servisi |
| [tools/evaluate_ocr.py](tools/evaluate_ocr.py) | tablica točnosti OCR-a (+ broj **pogrešno prihvaćenih**, mora biti 0) |
| [rezultati/](rezultati) | izvještaji na sintetskim skupovima |
| [tests/](tests) | 51 test: normalizacija, OCR, pravila odluke, 16 scenarija access controla (svaka poruka provjerena prema ugovoru) |

## Kako se računa pouzdanost

Svaki motor čita svaku varijantu slike (predlošci: 4 varijante, Tesseract: 3) → svako čitanje se
normalizira prema formatu `GG 1234-AB`. Čitanja glasaju: težina motora × kvaliteta čitanja
(pouzdanost motora × 0,9^broj ispravaka). **Pouzdanost = glasovi pobjednika / ukupna težina svih čitanja** –
čitanje koje ne uspije broji se protiv pobjednika. Zato se registracija prihvaća samo kad se (gotovo) svi slažu.

| motor | sam (sintetski kontrolirani skup) | |
|---|---|---|
| samo Tesseract | 78 % točno, 27 % prihvaćeno, 0 pogrešno prihvaćenih | Tesseraktova vlastita pouzdanost nije pouzdana (i pogrešna čitanja imaju 80–90) |
| samo predlošci | 91 % točno, 88 % prihvaćeno, 0 pogrešno prihvaćenih | radi samo za naš font |
| **oba (zadano)** | 91 % točno, 68 % prihvaćeno iz **prve** slike, **0 pogrešno prihvaćenih** | najsigurnije; ostatak rješavaju 3 slike po okidaču + 3 pokušaja |

U simulaciji cijelog sustava (sintetska kamera kao fiksna kamera) svako vozilo prođe automatski.
**Na stvarnim fotografijama izmjeri ponovno** (`evaluate_ocr.py`) i po potrebi promijeni težine u `OcrConfig`.

## Pravila odluke

| pouzdanost | ulaz | izlaz |
|---|---|---|
| ≥ 0.85 | `GRANTED` ako ima slobodnih mjesta, vozilo nije već unutra (i na allow-listi ako je `policy: allowlist`) | `GRANTED` ako postoji aktivna sesija → zatvori sesiju, cijena |
| 0.60 – 0.85 | `RETRY` (nova slika, najviše 3 pokušaja) | isto |
| < 0.60 | `MANUAL_REQUIRED` – rampa ostaje zatvorena | isto |

Slobodna mjesta = `min(senzorom slobodna, ukupno − aktivne sesije)`; `UNKNOWN` mjesto nije slobodno.
Rampa mora potvrditi naredbu u 3 s → jedno ponavljanje s istim `requestId` → alarm `GATE_NO_ACK`.

## Brzi start (laptop)

```bash
pip install -r ../requirements-dev.txt          # iz korijena repozitorija; + sudo apt install tesseract-ocr
python -m edge_service read ../osoba-5-alpr/dataset/synthetic/controlled/images/00*.jpg   # offline čitanje
python tools/evaluate_ocr.py ../osoba-5-alpr/dataset/synthetic/controlled                 # tablica točnosti
cp edge.example.yaml edge.yaml                  # prilagodi kameru, pragove
python -m edge_service --config edge.yaml all   # treba Mosquitto; ALPR_SOURCE=sim za rad bez kamere
pytest tests
```

Ručne radnje operatera (isto rade gumbi na ThingsBoard dashboardu; svaka se bilježi u bazu):

```bash
python -m edge_service manual approve-entry --plate ZG1234AB --note "pločica prljava"
python -m edge_service manual approve-exit --plate ZG1234AB
python -m edge_service manual deny --gate entrance
python -m edge_service manual open --gate exit
```

## Edge računalo (Raspberry Pi / Jetson Nano)

**Docker (preporuka, radi jednako na oba):**
```bash
cd osoba-6-ocr-edge/deploy
docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml up -d --build   # mosquitto + edge + tb-bridge, USB kamera
docker compose -f docker-compose.edge.yml up -d --build                                # bez kamere (sintetske slike), npr. na laptopu
```
**Nativno (Raspberry Pi OS / Ubuntu, Python ≥ 3.8):** `bash osoba-6-ocr-edge/deploy/install_native.sh`, zatim systemd
servisi iz `deploy/`. **Jetson Nano** (JetPack 4.x ima Python 3.6): koristi Docker ili `sudo apt install python3.8 python3.8-venv`
i `PYTHON=python3.8 bash install_native.sh` (koristi sistemski OpenCV ako postoji).

## Privatnost

- slike se ne spremaju; `privacy.save_crops: true` sprema samo izrez pločice, briše se nakon `retention_days`
- baza: `parking-sessions purge --days 30`; samo izmišljene registracije

## Tvoji zadaci

- [ ] pokrenuti `read` i `evaluate_ocr.py` na prvim stvarnim fotografijama (tjedan 1–2)
- [ ] skup stvarnih slika (s osobom 5) → tablica točnosti OCR-a, **0 pogrešno prihvaćenih**
- [ ] po potrebi podesiti težine/pragove/varijante (`OcrConfig`) i ponoviti mjerenje
- [ ] postaviti edge na Raspberry Pi (Docker ili nativno), kamera u `edge.yaml`
- [ ] dogovoriti s timom `policy: open` ili `allowlist` (`parking-sessions allow add ZG1234AB --label "Testno vozilo 1"`)
- [ ] integracijski koraci 5–9 iz plana integracije s pravim hardverom

| isporučivo | status |
|---|---|
| OCR modul | ✅ `plate_ocr` |
| lokalni edge servis | ✅ `edge_service` |
| baza dopuštenih registracija | ✅ tablica `allowed_plates` (osoba 8) + CLI |
| algoritam otvaranja i zatvaranja sesije | ✅ `access_control.py` + testovi |
| tablica točnosti OCR-a | ✅ sintetski, ⬜ stvarni |
