# Arhitektura sustava

> Vlasnik dokumenta: **osoba 1**. Svaka promjena koja utječe na više podsustava ide kroz ovaj dokument
> i [komunikacijski-ugovor.md](komunikacijski-ugovor.md) te se bilježi u [odluke.md](../upravljanje/odluke.md).

## 1. Minimalni sustav (cilj)

Vozilo dolazi do ulaza → kamera očitava registraciju → **edge računalo lokalno odlučuje** → rampa se otvara →
senzor mjesta mijenja stanje nakon parkiranja → sve je vidljivo u ThingsBoardu. Na izlazu se registracija
ponovno očitava, izračunava se trajanje i cijena te se zatvara parkirna sesija.

## 2. Blok-dijagram

Ovo je **varijanta A** – odluke se donose lokalno na edge računalu i sustav radi i bez ThingsBoarda.
Jednostavnija **varijanta B**, u kojoj sve odluke i podatke preuzima ThingsBoard, opisana je u
[poglavlju 9](#9-varijanta-b-sustav-oslonjen-na-thingsboard).

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

## 9. Varijanta B: sustav oslonjen na ThingsBoard

Ako sustav ne mora raditi bez ThingsBoarda, edge računalo se svodi na ALPR, a lokalni MQTT broker i SQLite baza
nisu potrebni – njihov posao preuzima ThingsBoard (provjereno u dokumentaciji ThingsBoarda):

- **MQTT broker** – ThingsBoard ima ugrađeni MQTT transport (*„ThingsBoard server nodes acts as an MQTT broker“*,
  port 1883, prijava *access tokenom* uređaja). Uređaj šalje telemetriju na `v1/devices/me/telemetry`, atribute na
  `v1/devices/me/attributes`, a naredbe prima na `v1/devices/me/rpc/request/+`
  ([MQTT Device API](https://thingsboard.io/docs/reference/mqtt-api/)).
- **Baza** – telemetrija i atributi spremaju se u bazu ThingsBoarda (PostgreSQL); parkirne sesije postaju atributi i
  telemetrija asseta „Garaža“ ([telemetrija](https://thingsboard.io/docs/user-guide/telemetry/),
  [atributi](https://thingsboard.io/docs/user-guide/attributes/)).
- **Logika** (odluke o ulasku/izlasku, naplata, alarmi) – *rule chain* od standardnih čvorova: *script* (TBEL ili
  JavaScript), *script filter*, *originator attributes* / *related entity data*, *change originator*,
  [*rpc call request*](https://thingsboard.io/docs/user-guide/rule-engine-2-0/nodes/action/rpc-call-request/),
  *save timeseries*, *save attributes*, *create alarm*. Naredbe uređajima idu kao server-side
  [RPC](https://thingsboard.io/docs/user-guide/rpc/); dvosmjerni RPC vraća odgovor uređaja u rule chain.
- **Ograničenje:** ugrađeni MQTT nije opći broker – uređaj šalje samo svoje podatke i prima samo svoje RPC naredbe.
  Uređaji ne razgovaraju izravno; sve ide preko rule chaina.
- **Edge računalo** ostaje samo za kameru i ALPR (ThingsBoard ne obrađuje slike). ALPR servis može raditi i na
  istom laptopu kao ThingsBoard.

### 9.1 Blok-dijagram (varijanta B)

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

  subgraph Edge["Edge računalo (ili laptop s ThingsBoardom)"]
    ALPR[ALPR servis<br/>detekcija + OCR]
  end

  subgraph Oblak["Laptop / server – ThingsBoard CE"]
    MQ[MQTT transport<br/>ugrađeni broker]
    RE[Rule engine<br/>odluke, naplata, alarmi]
    TDB[(Baza ThingsBoarda<br/>sesije, telemetrija)]
    DASH[Dashboardi<br/>+ gumbi za ručno]
    API[REST API]
  end

  subgraph Mobitel
    APP[Mobilna aplikacija<br/>analitika garaže]
  end

  ESPS -- MQTT telemetrija --> MQ
  ESPR <-- MQTT telemetrija i RPC --> MQ
  CAM -- USB --> ALPR
  ALPR <-- MQTT RPC --> MQ
  MQ <--> RE
  RE --- TDB
  DASH --- TDB
  DASH -- RPC gumbi --> RE
  API --- TDB
  API --> APP
```

**Ključna ideja:** sve odluke donosi ThingsBoard. Bez ThingsBoarda ili mreže ulaz i izlaz **ne rade automatski** –
rampe se mogu otvoriti samo tipkom na maketi (firmware i dalje sam zatvara rampu i ne spušta je na vozilo).

### 9.2 Tok ulaska (varijanta B)

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampe
  participant TB as ThingsBoard (rule chain)
  participant A as ALPR servis
  participant DB as Baza ThingsBoarda
  V->>R: dolazi do crte rampe (IR senzor)
  R->>TB: telemetrija {gate: entrance, vehiclePresent: true}
  TB->>A: RPC readPlate {gate: entrance} (dvosmjerni)
  A->>A: do 3 slike: detekcija → OCR → glasanje
  A-->>TB: odgovor RPC-a {plate, ocrConfidence}
  TB->>DB: dohvati slobodna mjesta i aktivne sesije (atributi asseta „Garaža“)
  alt confidence ≥ 0.85, slobodno mjesto, nije već unutra
    TB->>DB: otvori sesiju (atribut activeSessions), telemetrija accessDecision GRANTED
    TB->>R: RPC open {gate: entrance}
    R-->>TB: odgovor RPC-a {state: OPENING}
  else confidence < 0.85 ili nema slobodnog mjesta
    TB->>DB: alarm MANUAL_REQUIRED / GARAGE_FULL
    Note over TB: operater odobrava gumbom na dashboardu → RPC open
  end
  V->>R: prolazi (IR slobodan) → rampa se sama zatvara nakon 2 s
```

### 9.3 Tok izlaska (varijanta B)

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampe
  participant TB as ThingsBoard (rule chain)
  participant A as ALPR servis
  participant DB as Baza ThingsBoarda
  V->>R: dolazi na izlaz
  R->>TB: telemetrija {gate: exit, vehiclePresent: true}
  TB->>A: RPC readPlate {gate: exit}
  A-->>TB: odgovor RPC-a {plate, ocrConfidence}
  TB->>DB: pronađi aktivnu sesiju za registraciju
  alt sesija postoji
    TB->>TB: skripta: trajanje i cijena (15 min besplatno, 1,50 € po započetom satu, najviše 15 € dnevno)
    TB->>DB: telemetrija session {plate, durationS, price}, ukloni iz activeSessions
    TB->>R: RPC open {gate: exit}
  else nema aktivne sesije
    TB->>DB: alarm NO_ACTIVE_SESSION (ručna intervencija)
  end
```

U varijanti B ponovni pokušaji čitanja (pouzdanost 0,60 – 0,85) ostaju unutar ALPR servisa: on uzme do 3 slike i
vrati jedan rezultat, a rule chain sve ispod 0,85 šalje na ručno odobrenje. Tako je rule chain jednostavniji.

### 9.4 Usporedba varijanti

| | A – lokalno odlučivanje (edge) | B – ThingsBoard |
|---|---|---|
| MQTT broker | na edge računalu | ugrađeni MQTT transport ThingsBoarda |
| parkirne sesije | SQLite na edge računalu | baza ThingsBoarda (atributi i telemetrija asseta „Garaža“) |
| odluke i naplata | Python servis (`SOFTWARE/edge`), pokriven testovima | rule chain (TBEL skripte), uređuje se u web sučelju |
| edge računalo | broker, ALPR, kontrola pristupa, baza, bridge | samo ALPR (kamera) |
| bez ThingsBoarda ili mreže | ulaz i izlaz rade, podaci se šalju naknadno | automatski ulaz i izlaz ne rade, rampe samo tipkom |
| MQTT teme | vlastiti ugovor (`garage/...`, JSON sheme) | API uređaja ThingsBoarda (`v1/devices/me/...`) |
| testiranje | unit i e2e testovi u repozitoriju | ručno u ThingsBoardu; rule chain se izvozi kao JSON u repozitorij |
| vrijeme odziva | lokalno | ovisi o mreži do servera |

### 9.5 Što bi se promijenilo ako tim odabere varijantu B

- **Firmware** oba ESP32: MQTT host je ThingsBoard, korisničko ime je *access token* uređaja, teme
  `v1/devices/me/telemetry` i `v1/devices/me/rpc/request/+` umjesto `garage/...`; čvor senzora šalje i broj
  slobodnih mjesta.
- **ALPR servis** postaje uređaj u ThingsBoardu koji odgovara na RPC `readPlate`.
- **Kontrola pristupa** (`SOFTWARE/edge/edge_service`), **baza** (`SOFTWARE/baza`) i **bridge** (`tb_bridge`) se ne
  koriste; njihova pravila (pragovi, naplata, allow-lista) prelaze u rule chain, koji se izvozi u
  `SOFTWARE/thingsboard/`.
- Odluku o varijanti zabilježiti u [odluke.md](../upravljanje/odluke.md).
