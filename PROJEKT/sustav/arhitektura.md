# Arhitektura sustava

Vlasnik dokumenta je Patrik. Promjena koja utječe na više podsustava ide kroz ovaj dokument i
[komunikacijski-ugovor.md](komunikacijski-ugovor.md) te se bilježi u [odluke.md](../upravljanje/odluke.md).

## 1. Minimalni sustav (cilj)

Vozilo dolazi do ulaza → kamera očitava registraciju → edge računalo lokalno odlučuje → rampa se otvara →
senzor mjesta mijenja stanje nakon parkiranja → sve je vidljivo u ThingsBoardu. Na izlazu se registracija
ponovno očitava, izračunava se trajanje i cijena te se zatvara parkirna sesija.

## 2. Blok-dijagram

Ovo je varijanta A: odluke se donose lokalno na edge računalu i sustav radi i bez ThingsBoarda. Jednostavnija
varijanta B, u kojoj sve odluke i podatke preuzima ThingsBoard, opisana je u [varijanta-b.md](varijanta-b.md).

```mermaid
flowchart LR
  subgraph Maketa
    S1[UZV senzori x6] --> ESPS[ESP32 senzora]
    LED[LED po mjestu] --- ESPS
    IR[IR senzori] --> ESPR[ESP32 rampi]
    BTN[tipke za otvaranje] --> ESPR
    SERVO[2x servo + LED] --- ESPR
    CAM[USB kamere]
  end

  subgraph Edge["Edge računalo"]
    MQ[(MQTT broker)]
    ALPR["ALPR: detekcija + OCR"]
    AC[Access control]
    DB[(SQLite)]
    BR[ThingsBoard bridge]
  end

  subgraph Oblak["Laptop / server"]
    TB[ThingsBoard CE + dashboard]
  end

  subgraph Mobitel
    APP[Mobilna aplikacija]
  end

  ESPS -- MQTT --> MQ
  ESPR <-- MQTT --> MQ
  CAM -- USB --> ALPR
  ALPR <--> MQ
  AC <--> MQ
  AC --- DB
  BR <--> MQ
  BR -- gateway API --> TB
  TB -- RPC gumbi --> BR
  TB -- REST API --> APP
```

| blok | uloga | tko | kod |
|---|---|---|---|
| UZV senzori, ESP32 senzora, LED | šest senzora iznad mjesta; ESP32 preko Wi-Fi-ja i MQTT-a javlja stanje mjesta, LED ga pokazuje | Toma | `SOFTWARE/senzori` |
| IR senzori, tipke, ESP32 rampi, servo + LED | IR na crti rampe javlja vozilo, tipke ručno otvaraju rampu, dva servo motora pokreću rampe | Luka | `SOFTWARE/rampe` |
| USB kamere, ALPR | detekcija pločice (Sven) i OCR (Lukas) na edge računalu, za ulaz i izlaz | Sven, Lukas | `SOFTWARE/alpr`, `SOFTWARE/edge` |
| Access control, SQLite | odluke o ulasku i izlasku, naredbe rampama, parkirne sesije i naplata | Lukas, Luka (pravila), Lovro (baza) | `SOFTWARE/edge`, `SOFTWARE/baza` |
| ThingsBoard bridge | šalje podatke ThingsBoardu (MQTT gateway API) i čuva ih dok veza ne radi | Anja | `SOFTWARE/thingsboard` |
| ThingsBoard CE | dashboard, alarmi, gumbi za ručno odobravanje (RPC natrag preko bridgea) | Anja, Leo (analitika) | `SOFTWARE/thingsboard` |
| Mobilna aplikacija | čita analitiku iz ThingsBoarda preko REST API-ja | Leo | `SOFTWARE/mobilna-aplikacija` |

Maketu, napajanje, ožičenje i nosače rade Patrik i Lovro (`SOFTWARE/maketa`). Ugovor, integraciju i demonstraciju
vodi Patrik.

Ulazak i izlazak rade lokalno i bez ThingsBoarda. ThingsBoard je digitalni blizanac, nadzor i analitika i nikad
nije jedina komponenta potrebna za otvaranje rampe.

## 3. Tok ulaska

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
  alt confidence ≥ 0.85, ima mjesta, nije već unutra
    AC->>DB: otvori sesiju
    AC->>R: gate/entrance/command {OPEN, requestId}
    R->>AC: gate/entrance/state {OPENING, requestId, success}
    AC-->>TB: access/decision GRANTED,<br/>session/event OPENED, summary
  else 0.60 – 0.85
    AC->>A: novi trigger (RETRY, do 3 pokušaja)
  else < 0.60 ili 3 neuspjela pokušaja
    AC-->>TB: access/decision MANUAL_REQUIRED<br/>→ alarm, gumb „Ručno odobri ulaz“
  end
  V->>R: prolazi (IR slobodan) →<br/>rampa se sama zatvara nakon 2 s
```

## 4. Tok izlaska

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
  AC->>DB: pronađi aktivnu sesiju →<br/>zatvori, trajanje, cijena
  AC->>R: gate/exit/command OPEN
  AC-->>AC: session/event SESSION_CLOSED<br/>{durationS, price}
  Note over AC: nema aktivne sesije →<br/>DENIED NO_ACTIVE_SESSION<br/>(ručna intervencija)
```

## 5. Raspored (deployment)

| uređaj | što pokreće | kako |
|---|---|---|
| edge računalo | MQTT broker, `edge_service all`, `tb_bridge` | Docker (`SOFTWARE/edge/deploy/docker-compose.edge.yml` + `docker-compose.camera.yml`) ili nativno (`install_native.sh`) |
| laptop (ili drugi uređaj s ≥ 4 GB RAM) | ThingsBoard CE | `SOFTWARE/thingsboard/docker-compose.yml` |
| 2x ESP32 | firmware senzora i rampi | PlatformIO |
| laptop bez hardvera (razvoj) | sve od gore + simulatori | `python SOFTWARE/integracija/simulacija.py --broker` |

Edge računalo može biti bilo koje Linux računalo s Dockerom ili Pythonom ≥ 3.8; odabir je zabilježen u
[odluke.md](../upravljanje/odluke.md) (D-004).

## 6. Što ako podsustav nije dostupan (degradirani rad)

| ispadne | posljedica | ponašanje sustava |
|---|---|---|
| ThingsBoard ili mreža prema njemu | nema dashboarda | ulaz/izlaz rade normalno; bridge sprema podatke u `tb-buffer.db` i šalje ih s izvornim vremenom kad se veza vrati (testirano) |
| MQTT broker / edge računalo | nema automatskih odluka | rampe i dalje rade lokalno: tipka za ručno otvaranje, automatsko zatvaranje, sigurnosno ponovno otvaranje |
| ALPR (kamera, OCR) | nema čitanja | 3 pokušaja → `MANUAL_REQUIRED` + alarm; operater odobrava gumbom na dashboardu ili CLI-jem; razlog se bilježi |
| ESP32 senzora | nema stanja mjesta | Last Will → mjesta postaju `UNKNOWN` (nikad "slobodno"), alarm "Uređaj nije dostupan" |
| jedan senzor | jedno mjesto nepoznato | firmware nakon 5 neuspjelih mjerenja javlja `UNKNOWN`/`TIMEOUT`; ne broji se kao slobodno |
| ESP32 rampi | rampa ne potvrđuje | access control ponovi naredbu jednom (isti `requestId`), zatim alarm `GATE_NO_ACK` |
| Wi-Fi | ESP32 offline | ESP32 se sam ponovno spaja (svakih 5 s); stanja se ponovno objavljuju nakon spajanja |

Vrijeme u porukama je UTC ([komunikacijski ugovor](komunikacijski-ugovor.md)); privatnost i sigurnost su opisane u
[06-privatnost-i-sigurnost.md](../dokumentacija/06-privatnost-i-sigurnost.md).
