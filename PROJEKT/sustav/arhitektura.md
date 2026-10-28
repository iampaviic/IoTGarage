# Arhitektura sustava

> Vlasnik dokumenta: **osoba 1**. Svaka promjena koja utječe na više podsustava ide kroz ovaj dokument
> i [komunikacijski-ugovor.md](komunikacijski-ugovor.md) te se bilježi u [odluke.md](../upravljanje/odluke.md).

## 1. Minimalni sustav (cilj)

Vozilo dolazi do ulaza → kamera očitava registraciju → **edge računalo lokalno odlučuje** → rampa se otvara →
senzor mjesta mijenja stanje nakon parkiranja → sve je vidljivo u ThingsBoardu. Na izlazu se registracija
ponovno očitava, izračunava se trajanje i cijena te se zatvara parkirna sesija.

## 2. Blok-dijagram

```mermaid
flowchart LR
  subgraph Maketa
    S1[UZV senzor x6<br/>iznad mjesta] --> ESPS[ESP32<br/>čvor senzora]
    LED[LED<br/>po mjestu] --- ESPS
    IR[IR senzori<br/>na crti rampe] --> ESPR[ESP32<br/>čvor rampi]
    BTN[tipke za ručno<br/>otvaranje] --> ESPR
    ESPR --> SERVO[2x servo motor<br/>rampe + LED]
    CAM[USB kamera<br/>ulaz / izlaz]
  end

  subgraph Edge["Edge računalo"]
    MQ[(MQTT broker)]
    ALPR[ALPR servis<br/>detekcija + OCR]
    AC[Access control<br/>odluke, rampe]
    DB[(SQLite<br/>parkirne sesije)]
    BR[ThingsBoard<br/>bridge + buffer]
  end

  subgraph Oblak["Laptop / server"]
    TB[ThingsBoard CE<br/>dashboard, alarmi]
  end

  subgraph Mobitel
    APP[Mobilna aplikacija<br/>analitika garaže]
  end

  ESPS -- MQTT Wi-Fi --> MQ
  ESPR <-- MQTT Wi-Fi --> MQ
  CAM -- USB --> ALPR
  ALPR <--> MQ
  AC <--> MQ
  AC --- DB
  BR <--> MQ
  BR -- MQTT gateway API --> TB
  TB -- RPC gumbi --> BR
  TB -- REST API --> APP
```

**Ključna ideja:** ulazak i izlazak rade lokalno i bez ThingsBoarda. ThingsBoard je digitalni blizanac,
nadzor i analitika – nikada jedina komponenta potrebna za otvaranje rampe.

## 3. Komponente i vlasništvo

| komponenta | gdje radi | vlasnik | kod |
|---|---|---|---|
| čvor senzora (ESP32 + 6x UZV senzor + LED) | maketa | osoba 3 | `SOFTWARE/senzori/firmware` |
| čvor rampi (ESP32 + 2x servo motor + 2x IR senzor + LED + tipke) | maketa | osoba 4 | `SOFTWARE/rampe/firmware` |
| maketa, napajanje, ožičenje, nosači | maketa | osoba 2 | `SOFTWARE/maketa` |
| detekcija pločice (OpenCV) | edge | osoba 5 | `SOFTWARE/alpr/plate_detector` |
| OCR + validacija + ALPR servis + access control | edge | osoba 6 | `SOFTWARE/edge` |
| baza sesija, naplata, testovi, dokumentacija | edge | osoba 8 | `SOFTWARE/baza` |
| ThingsBoard, bridge, dashboardi, alarmi | laptop + edge | osoba 7 | `SOFTWARE/thingsboard` |
| ugovor (teme, JSON sheme), integracija, demo | svi | osoba 1 | `PROJEKT/upravljanje` |

## 4. Tok ulaska

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampe
  participant AC as Access control
  participant A as ALPR servis
  participant DB as SQLite
  participant TB as ThingsBoard (preko bridgea)
  V->>R: dolazi do crte rampe (IR senzor)
  R->>AC: gate/entrance/state {vehiclePresent:true}
  AC->>A: alpr/entrance/trigger {requestId}
  A->>A: do 3 slike: detekcija → OCR → glasanje
  A->>AC: alpr/entrance/event {plate, ocrConfidence}
  alt confidence ≥ 0.85, slobodno mjesto, nije već unutra
    AC->>DB: otvori sesiju
    AC->>R: gate/entrance/command {OPEN, requestId}
    R->>AC: gate/entrance/state {OPENING, requestId, success}
    AC-->>TB: access/decision GRANTED, session/event OPENED, summary
  else 0.60 – 0.85
    AC->>A: novi trigger (RETRY, do 3 pokušaja)
  else < 0.60 ili 3 neuspjela pokušaja
    AC-->>TB: access/decision MANUAL_REQUIRED → alarm, gumb "Ručno odobri ulaz"
  end
  V->>R: prolazi (IR slobodan) → rampa se sama zatvara nakon 2 s
```

## 5. Tok izlaska

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampe
  participant AC as Access control
  participant A as ALPR servis
  participant DB as SQLite
  V->>R: dolazi na izlaz
  R->>AC: gate/exit/state {vehiclePresent:true}
  AC->>A: alpr/exit/trigger
  A->>AC: alpr/exit/event {plate, ocrConfidence}
  AC->>DB: pronađi aktivnu sesiju → zatvori, trajanje, cijena
  AC->>R: gate/exit/command OPEN
  AC-->>AC: session/event SESSION_CLOSED {durationS, price}
  Note over AC: nema aktivne sesije → DENIED NO_ACTIVE_SESSION (ručna intervencija)
```

## 6. Raspored (deployment)

| uređaj | što pokreće | kako |
|---|---|---|
| edge računalo | MQTT broker, `edge_service all`, `tb_bridge` | Docker (`SOFTWARE/edge/deploy/docker-compose.edge.yml` + `docker-compose.camera.yml`) ili nativno (`install_native.sh`) |
| laptop (ili drugi uređaj s ≥ 4 GB RAM) | ThingsBoard CE | `SOFTWARE/thingsboard/docker-compose.yml` |
| 2x ESP32 | firmware senzora i rampi | PlatformIO |
| laptop bez hardvera (razvoj) | sve od gore + simulatori | `python SOFTWARE/integracija/simulacija.py --broker` |

Edge računalo može biti bilo koje Linux računalo s Dockerom ili Pythonom ≥ 3.8; odabir je zabilježen u
[odluke.md](../upravljanje/odluke.md) (D-004).

## 7. Što ako podsustav nije dostupan (degradirani rad)

| ispadne | posljedica | ponašanje sustava |
|---|---|---|
| ThingsBoard ili mreža prema njemu | nema dashboarda | ulaz/izlaz rade normalno; bridge sprema podatke u `tb-buffer.db` i šalje ih s izvornim vremenom kad se veza vrati (testirano) |
| MQTT broker / edge računalo | nema automatskih odluka | rampe i dalje rade lokalno: tipka za ručno otvaranje, automatsko zatvaranje, sigurnosno ponovno otvaranje |
| ALPR (kamera, OCR) | nema čitanja | 3 pokušaja → `MANUAL_REQUIRED` + alarm; operater odobrava gumbom na dashboardu ili CLI-jem; razlog se bilježi |
| ESP32 senzora | nema stanja mjesta | Last Will → mjesta postaju `UNKNOWN` (nikad "slobodno"), alarm "Uređaj nije dostupan" |
| jedan senzor | jedno mjesto nepoznato | firmware nakon 5 neuspjelih mjerenja javlja `UNKNOWN`/`TIMEOUT`; ne broji se kao slobodno |
| ESP32 rampi | rampa ne potvrđuje | access control ponovi naredbu jednom (isti `requestId`), zatim alarm `GATE_NO_ACK` |
| Wi-Fi | ESP32 offline | ESP32 se sam ponovno spaja (svakih 5 s); stanja se ponovno objavljuju nakon spajanja |

## 8. Vrijeme, privatnost, sigurnost

- Sva vremena u porukama i bazi: **UTC, ISO 8601** (`2026-10-19T08:31:12Z`); lokalno vrijeme samo u ThingsBoardu.
- Samo **izmišljene registracije** (generator: `SOFTWARE/alpr/tools/generate_plates.py`).
- Slike se ne spremaju; opcionalno samo izrezana pločica (`privacy.save_crops`) uz automatsko brisanje.
- Sesije i događaji brišu se nakon N dana (`parking-sessions purge --days 30`), ThingsBoard čuva telemetriju 30 dana.
- Za završnu demonstraciju: lozinka na MQTT brokeru, tajni token gatewaya, promijenjena lozinka ThingsBoarda.
