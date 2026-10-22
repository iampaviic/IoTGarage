# IoT Garaža

- **Projekt:** IoT Garaža, ak. god. 2026/27
- **Puni naziv projekta:** Pametna parkirna garaža s automatskim prepoznavanjem registarskih oznaka (ALPR),
  lokalnim (edge) upravljanjem ulaskom i izlaskom te digitalnim blizancem u platformi ThingsBoard
- **Datum prezentacije:** _upisati_

Pametna garaža na maketi: kamera čita registraciju, **edge računalo lokalno odlučuje** o ulasku, rampa se
otvara, senzori prate zauzetost mjesta, parkirna sesija se naplaćuje pri izlasku, a sve se prikazuje u
ThingsBoardu i mobilnoj aplikaciji.

## Sadržaj repozitorija

Struktura slijedi [upute nastavnika](OSTALO/upute-nastavnika-gitlab.md); svaka mapa ima `README.md` s opisom.

| mapa | sadržaj |
|---|---|
| [PROJEKT](PROJEKT) | [prijedlog i plan projekta](PROJEKT/plan-projekta) (DOCX + PDF), [završna dokumentacija](PROJEKT/dokumentacija), [arhitektura i MQTT ugovor](PROJEKT/sustav), [plan rada, rizici, odluke](PROJEKT/upravljanje), [nacrt makete](PROJEKT/maketa), [testiranje](PROJEKT/testiranje) |
| [SOFTWARE](SOFTWARE) | sav kod – firmware, edge servis, baza, ThingsBoard, simulacija, 3D dijelovi; [instalacija](SOFTWARE/INSTALL.md) |
| [PREZENTACIJA](PREZENTACIJA) | [demo scenarij](PREZENTACIJA/demo-scenarij.md), završna prezentacija |
| [OSTALO](OSTALO) | [literatura i poveznice](OSTALO/literatura.md), upute nastavnika |

![dashboard](PROJEKT/slike/dashboard-nadzor.jpg)

## Tim

Svaki dio sustava ima svoju mapu s **README-om: tko je zadužen, što je već napravljeno, kako se koristi i što još treba napraviti**.

| | uloga | tko | mapa | pripremljeno |
|---|---|---|---|---|
| 1 | voditelj, arhitektura, integracija | Patrik | [PROJEKT/upravljanje](PROJEKT/upravljanje) | arhitektura, **komunikacijski ugovor kao kod** (JSON sheme + Python paket), zahtjevi, rizici, odluke, plan rada, demo scenarij, **simulacija cijelog sustava** + e2e testovi |
| 2 | maketa, napajanje, ožičenje | Patrik, Lovro Gale | [SOFTWARE/maketa](SOFTWARE/maketa) | tlocrt 1:1, kalkulator položaja kamere, 7 parametarskih 3D dijelova (STL), dijagrami ožičenja, popis komponenti, proračun napajanja |
| 3 | senzori mjesta, firmware | Toma Burgund (+ Lovro Gale) | [SOFTWARE/senzori](SOFTWARE/senzori) | ESP32 firmware (6× HC-SR04, filtar, MQTT, reconnect, LWT), unit testovi, simulator, alati za kalibraciju i test 20× |
| 4 | rampe, aktuatori, lokalna kontrola pristupa | Luka Oslić | [SOFTWARE/rampe](SOFTWARE/rampe) | ESP32 firmware (2 rampe, stroj stanja, sigurnost, tipke), unit testovi, simulator, sigurnosni testovi |
| 5 | ALPR – detekcija pločice | Sven Matić | [SOFTWARE/alpr](SOFTWARE/alpr) | OpenCV detektor, ispravak perspektive, **pločice za ispis**, sintetski skup, alati za snimanje/označavanje/mjerenje |
| 6 | OCR, edge servis | Lukas Davorija (+ Luka Oslić za access control) | [SOFTWARE/edge](SOFTWARE/edge) | dvostruki OCR s glasanjem, HR format, ALPR servis, **access control** (odluke, sesije, rampe, alarmi), Docker za Raspberry Pi/Jetson |
| 7 | ThingsBoard | Anja, Leo Hreljanović (analitika) | [SOFTWARE/thingsboard](SOFTWARE/thingsboard) | docker-compose, provisioning jednom naredbom, bridge s međuspremnikom, **2 dashboarda**, 7 pravila alarma, RPC gumbi |
| 8 | baza, testovi, GitHub | Lovro Gale | [SOFTWARE/baza](SOFTWARE/baza) | SQLite sesije + naplata + CLI, testni plan (~60 slučajeva), testni zapisnik, kostur dokumentacije, korisničke upute |

Leo Hreljanović uz to izrađuje **[mobilnu aplikaciju za analitiku garaže](SOFTWARE/mobilna-aplikacija)** (zauzetost, ulasci po satu, prosječno trajanje, povijest sesija), koja podatke čita iz ThingsBoarda preko REST API-ja.

**Što je provjereno:** 145 automatskih testova prolazi; cijeli sustav radi u simulaciji (0 poruka koje krše
ugovor); oba firmwarea se prevode za ESP32; ThingsBoard dashboardi, alarmi, RPC, međuspremnik pri ispadu i
restart provjereni na ThingsBoard CE 4.2.1. **Što još nije:** ništa nije isprobano na stvarnom hardveru, a
ALPR je mjeren samo na sintetskim slikama – to je posao za tim (vidi [plan rada](PROJEKT/upravljanje/plan-rada.md)).

## Arhitektura ukratko

```mermaid
flowchart LR
  S[ESP32 senzora<br/>6x HC-SR04] -- MQTT --> M[(Mosquitto)]
  R[ESP32 rampi<br/>2x servo, IR] <-- MQTT --> M
  C[USB kamera] --> A[ALPR + OCR]
  A <--> M
  AC[Access control<br/>+ SQLite sesije] <--> M
  M <--> B[Bridge + buffer] -- gateway API --> TB[ThingsBoard]
  subgraph Edge računalo
    M
    A
    AC
    B
  end
```

Detalji: [arhitektura](PROJEKT/sustav/arhitektura.md) · [MQTT teme i poruke](PROJEKT/sustav/komunikacijski-ugovor.md) ·
[odluke](PROJEKT/upravljanje/odluke.md) · [demo scenarij](PREZENTACIJA/demo-scenarij.md)

## Brzi start – cijeli sustav bez hardvera (5 minuta)

Treba: Python ≥ 3.8, [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html) i
[Mosquitto](https://mosquitto.org/download/) (Linux: `sudo apt install tesseract-ocr mosquitto`).

```bash
git clone <repo> && cd IoTGarage/SOFTWARE              # sve naredbe se pokreću iz mape SOFTWARE
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python integracija/simulacija.py --broker     # odigra demo: ulaz, parkiranje, nečitljiva pločica, izlaz s cijenom
pytest                                        # svi testovi
```

S ThingsBoardom (Docker):

```bash
cd thingsboard && docker compose up -d && python provision/provision.py && cd ..
python integracija/simulacija.py --broker --tb --interactive
# http://localhost:8080  (tenant@thingsboard.org / tenant) -> Dashboards -> "Garaža - nadzor"
```

Korisni alati:

```bash
python -m garage_contract.monitor                                  # sve MQTT poruke, crveno = krši ugovor
python -m edge_service read slika.jpg                              # pročitaj registraciju sa slike
python alpr/tools/generate_plates.py --out tablice                 # pločice za ispis
parking-sessions --db data/garage.db list --active                 # tko je u garaži
```

Firmware, edge računalo i sve varijable konfiguracije: [SOFTWARE/INSTALL.md](SOFTWARE/INSTALL.md).

## Struktura i pravila

- Python paketi se instaliraju iz svojih mapa (`SOFTWARE/requirements-dev.txt`), firmware je PlatformIO.
- Sva vremena: **UTC ISO 8601**. Sve registracije: **izmišljene**.
- Promjena MQTT poruka samo kroz voditelja (sheme u `SOFTWARE/ugovor`) – CI provjerava sve primjere.
- Svatko radi u svojoj grani i otvara Pull Request; **CI** (`.github/workflows/ci.yml`) mora biti zelen:
  Python testovi (3.8 i 3.12) + e2e simulacija, prevođenje i unit testovi oba firmwarea, renderiranje 3D dijelova.
- Ne komitati: `secrets.h`, `edge.yaml`, baze `*.db`, stvarne fotografije.
