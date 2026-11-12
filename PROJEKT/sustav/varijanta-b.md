# Varijanta B: sustav oslonjen na ThingsBoard

**Odabrana arhitektura** ([odluka D-012](../upravljanje/odluke.md)). Sav novi rad se radi za varijantu B.
[Varijanta A](arhitektura.md) (lokalno odlučivanje na edge računalu) ostaje u repozitoriju kao rezerva.

Uređaji se spajaju izravno na ThingsBoard, a odluke, parkirne sesije, naplatu i alarme vodi *rule chain*.
Lokalni MQTT broker, SQLite baza, access control na edge računalu i bridge nisu potrebni. Izvan ThingsBoarda
ostaje samo ALPR, jer ThingsBoard ne obrađuje slike.

- MQTT: ugrađeni MQTT transport ThingsBoarda (port 1883, korisničko ime je *access token* uređaja). Svaki čvor je
  *gateway* uređaj ([Gateway MQTT API](https://thingsboard.io/docs/reference/gateway-mqtt-api/), radi u CE) i
  jednom vezom šalje podatke za svoje uređaje.
- Baza: telemetrija, atributi i alarmi u bazi ThingsBoarda (PostgreSQL). Parkirne sesije su atribut `sessions`
  asseta „Garage“, a odluke i završene sesije njegova telemetrija.
- Logika: rule chain [`SOFTWARE/thingsboard/rulechain`](../../SOFTWARE/thingsboard/rulechain) (TBEL skripte +
  generator). Naredbe uređajima su server-side [RPC](https://thingsboard.io/docs/user-guide/rpc/).
- Ugrađeni MQTT nije opći broker: uređaji ne razgovaraju izravno, sve ide preko rule chaina.

Sve je isprobano na ThingsBoard CE 4.2.1 sa simuliranim uređajima (`integracija/simulacija_b.py`, testovi u
[§ Testiranje](#testiranje)); na hardveru još nije.

## Blok-dijagram

```mermaid
flowchart LR
  subgraph Maketa
    S1[UZV senzori x6] --> ESPS[ESP32 senzora<br/>gateway esp32-spots]
    LED[LED po mjestu] --- ESPS
    IR[IR senzori] --> ESPR[ESP32 rampi<br/>gateway esp32-gates]
    BTN[tipke za otvaranje] --> ESPR
    SERVO[2x servo + LED] --- ESPR
    CAM[USB kamere]
  end

  subgraph Laptop["Laptop (ili Raspberry Pi za ALPR)"]
    ALPR["ALPR servis: detekcija + OCR<br/>gateway alpr-service"]
  end

  subgraph TB["ThingsBoard CE"]
    MQ[MQTT transport :1883]
    RE[Rule chain]
    TDB[(Baza)]
    DASH[Dashboardi]
    API[REST API]
  end

  subgraph Mobitel
    APP[Mobilna aplikacija]
  end

  ESPS -- telemetrija, RPC sim --> MQ
  ESPR <-- telemetrija, RPC --> MQ
  CAM -- USB --> ALPR
  ALPR <-- RPC readPlate --> MQ
  MQ <--> RE
  RE --- TDB
  DASH --- TDB
  DASH -- RPC approve / deny --> RE
  API --- TDB
  API --> APP
```

| blok | uloga | ThingsBoard | tko | kod |
|---|---|---|---|---|
| ESP32 senzora + 6× HC-SR04 + LED | mjeri zauzetost, šalje stanja mjesta i broj slobodnih | gateway `esp32-spots` → `ParkingSpot-01…06` | Toma | `SOFTWARE/senzori` |
| ESP32 rampi + servo, IR, tipke | izvršava naredbe, javlja dolazak vozila, sam zatvara rampu i ne spušta je na vozilo | gateway `esp32-gates` → `EntranceGate`, `ExitGate` | Luka | `SOFTWARE/rampe` |
| ALPR servis + USB kamere | na RPC `readPlate` vraća registraciju i pouzdanost | gateway `alpr-service` → `ALPR-Entrance`, `ALPR-Exit` | Sven, Lukas | `SOFTWARE/alpr`, `SOFTWARE/edge` (`tb_alpr.py`) |
| rule chain | odluke o ulasku i izlasku, sesije, naplata, alarmi, RPC naredbe rampama | root rule chain „Garaža (varijanta B)“ | Anja, Luka (pravila), Lovro (sesije, naplata) | `SOFTWARE/thingsboard/rulechain` |
| asset „Garage“ | postavke (pragovi, naplata, politika), sesije, sažetak, odluke | asset `Garage` | Anja | `SOFTWARE/thingsboard/provision` |
| dashboardi | nadzor, alarmi, ručno odobravanje, analitika | 2 dashboarda | Anja, Leo | `SOFTWARE/thingsboard/dashboards` |
| mobilna aplikacija | čita analitiku preko REST API-ja | – | Leo | `SOFTWARE/mobilna-aplikacija` |

Sve odluke donosi ThingsBoard. Bez ThingsBoarda ili mreže ulaz i izlaz ne rade automatski, a rampe se mogu
otvoriti samo tipkom na maketi. Firmware i dalje sam zatvara rampu i ne spušta je na vozilo.

## Čvor senzora mjesta (ESP32)

Firmware: [`SOFTWARE/senzori/firmware`](../../SOFTWARE/senzori/firmware), simulator istog ponašanja:
[`spot_simulator_tb.py`](../../SOFTWARE/senzori/simulator/spot_simulator_tb.py).

| smjer | tema | sadržaj | kada |
|---|---|---|---|
| ESP32 → TB | `v1/gateway/connect` | `{"device": "ParkingSpot-03", "type": "ParkingSpot"}` | nakon svakog spajanja, za svako mjesto |
| ESP32 → TB | `v1/gateway/telemetry` | `{"ParkingSpot-03": [{"state": "OCCUPIED", "stateCode": 1, "occupied": true, "distanceCm": 6.4, "sensorStatus": "OK"}]}` | promjena, svakih 30 s, nakon spajanja |
| ESP32 → TB | `v1/devices/me/telemetry` | `{"freeSpots": 5, "occupiedSpots": 1, "unknownSpots": 0, "totalSpots": 6}` (+ `uptimeS`, `rssi`, `freeHeap` svakih 30 s) | uz svaku promjenu, svakih 30 s |
| ESP32 → TB | `v1/devices/me/attributes` | `{"fwVersion", "ip", "deviceType", "spotCount"}` | nakon spajanja |
| TB → ESP32 | `v1/devices/me/rpc/request/+` | `sim {"spot": "P03", "occupied": true\|false\|null}`, `simOff`, `status` | simulacija, provjera |

Vrijeme poruka postavlja ThingsBoard (vrijeme primitka), pa ESP32 ne treba NTP. `state` je `FREE | OCCUPIED |
UNKNOWN`, `stateCode` 0 / 1 / −1, a `sensorStatus` `OK | TIMEOUT | OUT_OF_RANGE | SIMULATED` (`OFFLINE`
postavlja rule chain kad čvor nestane). Za `UNKNOWN` nema ključeva `occupied` i `distanceCm`.

### Pokretanje i spajanje

```mermaid
sequenceDiagram
  participant E as ESP32 senzora
  participant W as Wi-Fi ruter
  participant TB as ThingsBoard (MQTT)
  participant RC as Rule chain
  participant G as Asset Garage
  E->>E: setup: pinovi, filtri (UNKNOWN), LED plavo
  E->>W: WiFi.begin (ponovno svakih 5 s)
  W-->>E: IP adresa
  E->>TB: CONNECT clientId esp32-spots,<br/>user = access token, keepalive 30 s
  TB-->>E: CONNACK
  TB->>RC: Connect Event (esp32-spots)
  RC->>RC: online = true,<br/>ugasi alarm „Uređaj nije dostupan“
  loop P01 … P06
    E->>TB: v1/gateway/connect {device: ParkingSpot-0x, type: ParkingSpot}
  end
  E->>TB: SUBSCRIBE v1/devices/me/rpc/request/+
  E->>TB: v1/devices/me/attributes {fwVersion, ip, deviceType, spotCount}
  loop P01 … P06
    E->>TB: v1/gateway/telemetry {ParkingSpot-0x: [stanje]}
  end
  E->>TB: v1/devices/me/telemetry {brojevi mjesta, uptimeS, rssi, freeHeap}
  TB->>RC: Post telemetry (esp32-spots)
  RC->>G: atributi sensorFree, sensorOccupied
  RC->>G: sažetak (freeSpots, availableSpots, full …)
```

Dok se filtar ne napuni (prvih ≈ 2 s), mjesta su `UNKNOWN` i ne broje se kao slobodna.

### Parkiranje: mjerenje i promjena stanja

```mermaid
sequenceDiagram
  participant S as HC-SR04 P03
  participant E as ESP32 senzora
  participant L as LED P03
  participant TB as ThingsBoard
  participant RC as Rule chain
  participant G as Asset Garage
  participant D as Dashboard
  loop svakih 60 ms sljedeći senzor (isti senzor svakih 360 ms)
    E->>S: TRIG 10 µs
    S-->>E: ECHO → udaljenost u cm
    E->>E: filtar: valjano 2–60 cm, medijan 5,<br/>histereza 10 / 12 cm, potvrda 3×
  end
  Note over S,E: autić parkira, 14 cm → 6,5 cm
  E->>E: OCCUPIED potvrđen (≈ 2 s nakon parkiranja)
  E->>L: crveno
  E->>TB: v1/gateway/telemetry {ParkingSpot-03: [{state: OCCUPIED,<br/>stateCode: 1, occupied: true, distanceCm: 6.4, sensorStatus: OK}]}
  E->>TB: v1/devices/me/telemetry {freeSpots: 5, occupiedSpots: 1,<br/>unknownSpots: 0, totalSpots: 6}
  TB->>RC: Post telemetry (ParkingSpot-03)
  RC->>RC: pravila alarma profila ParkingSpot, spremi telemetriju
  TB->>RC: Post telemetry (esp32-spots)
  RC->>G: sensorFree = 5, sensorOccupied = 1
  RC->>G: sažetak: freeSpots, occupancyPct, activeSessions,<br/>availableSpots = min(slobodna, ukupno − sesije), full
  alt availableSpots = 0
    RC->>G: alarm „Garaža puna“
  else ima mjesta
    RC->>G: ugasi alarm „Garaža puna“
  end
  G-->>D: tlocrt i broj slobodnih mjesta (< 3 s)
```

Odlazak s mjesta je isti tok: 6,5 cm → 14 cm, `FREE`, zeleno. Vrijednost između pragova (10–12 cm) ne mijenja
stanje (histereza), pa mjesto ne treperi.

### Periodično javljanje

```mermaid
sequenceDiagram
  participant E as ESP32 senzora
  participant TB as ThingsBoard
  participant RC as Rule chain
  loop svakih 30 s
    E->>TB: v1/gateway/telemetry za svih 6 mjesta
    E->>TB: v1/devices/me/telemetry {brojevi, uptimeS, rssi, freeHeap}
    TB->>RC: Post telemetry → spremi, sažetak
  end
  Note over E,TB: keepalive 30 s: bez poruka ESP32 šalje PINGREQ.<br/>ThingsBoard zatvara vezu nakon 45 s tišine,<br/>a uređaj bez aktivnosti 90 s (inactivityTimeout) postaje neaktivan.
```

### Kvar senzora

```mermaid
sequenceDiagram
  participant S as HC-SR04 P05
  participant E as ESP32 senzora
  participant L as LED P05
  participant TB as ThingsBoard
  participant RC as Rule chain
  participant G as Asset Garage
  Note over S: ECHO odspojen ili senzor ne vidi pod
  loop 5 mjerenja zaredom
    E->>S: TRIG
    S-->>E: nema jeke (6 ms) ili izvan 2–60 cm
  end
  E->>E: UNKNOWN, sensorStatus TIMEOUT / OUT_OF_RANGE
  E->>L: plavo
  E->>TB: v1/gateway/telemetry {ParkingSpot-05: [{state: UNKNOWN,<br/>stateCode: -1, sensorStatus: TIMEOUT}]}
  E->>TB: v1/devices/me/telemetry {freeSpots: 4, unknownSpots: 1, …}
  TB->>RC: Post telemetry
  RC->>RC: profil ParkingSpot: sensorStatus nije OK ni SIMULATED<br/>→ alarm „Senzor mjesta ne radi“ (MAJOR)
  RC->>G: nepoznato mjesto se ne broji kao slobodno
  Note over S,E: senzor ponovno daje valjana mjerenja
  E->>TB: {state: FREE, sensorStatus: OK}
  RC->>RC: alarm se gasi
```

### Gubitak veze i oporavak

```mermaid
sequenceDiagram
  participant E as ESP32 senzora
  participant L as LED traka
  participant TB as ThingsBoard
  participant RC as Rule chain
  participant G as Asset Garage
  Note over E,TB: Wi-Fi ili ThingsBoard ne radi, ili ESP32 ostane bez struje
  par ESP32 radi dalje lokalno
    E->>E: mjerenje i filtar rade dalje
    E->>L: LED pokazuju stvarno stanje
    E->>E: svakih 5 s pokušaj Wi-Fi / MQTT
  and ThingsBoard primijeti prekid
    TB->>TB: TCP veza zatvorena ili 45 s bez poruka
    TB->>RC: Disconnect Event (esp32-spots i ParkingSpot-01 … 06)
    RC->>RC: esp32-spots: online = false,<br/>alarm „Uređaj nije dostupan“
    RC->>RC: ParkingSpot-0x: state UNKNOWN, sensorStatus OFFLINE
    RC->>G: sensorFree = 0 → nema slobodnih mjesta (ulaz DENIED GARAGE_FULL)
  end
  Note over E,TB: veza se vrati
  E->>TB: CONNECT (access token)
  TB->>RC: Connect Event → online = true, alarm se gasi
  E->>TB: gateway/connect, stanja svih mjesta, brojevi
  RC->>G: točna stanja i sažetak
```

Prekid se vidi u ThingsBoardu za najviše ≈ 45 s (odmah ako se TCP veza uredno zatvori). Isprobano u simulaciji
(korak 8 scenarija).

### Simulacija i kalibracija

```mermaid
sequenceDiagram
  participant O as Operater / simulacija
  participant TB as ThingsBoard
  participant E as ESP32 senzora
  participant PC as Laptop (USB, 115200)
  O->>TB: RPC sim {spot: P03, occupied: true} na esp32-spots
  TB->>E: v1/devices/me/rpc/request/5
  E->>E: P03 = OCCUPIED, sensorStatus SIMULATED
  E->>TB: telemetrija P03 + brojevi
  E-->>TB: v1/devices/me/rpc/response/5 {success: true}
  TB-->>O: odgovor
  O->>TB: RPC simOff → natrag na stvarne senzore
  PC->>E: serijski: status, cal, sim 3 1, sim off
  E-->>PC: stanja ili CAL,P03,6.4 (za tools/kalibracija.py)
```

`occupied: null` simulira pokvaren senzor (`TIMEOUT`), pa se može isprobati i alarm.

## Tok ulaska

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampi (EntranceGate)
  participant RC as Rule chain
  participant A as ALPR servis (ALPR-Entrance)
  participant G as Asset Garage
  participant O as Operater (dashboard)
  V->>R: dolazi do zatvorene rampe (IR)
  R->>RC: telemetrija {vehicleArrived: true, state: CLOSED}
  RC->>A: RPC readPlate {gate: ENTRANCE}
  A->>A: do 3 slike: detekcija, OCR, glasanje
  A-->>RC: {status, plate, ocrConfidence}
  RC->>G: čita sessions, sensorFree, totalSpots, pravila
  alt pouzdanost ≥ 0,85, ima mjesta, nije već unutra
    RC->>G: sesija u sessions, GRANTED, entry = 1
    RC->>R: RPC open
    R-->>RC: {success: true, state: OPENING}
  else pouzdanost < 0,85, nema pločice ili ALPR ne odgovori u 15 s
    RC->>G: MANUAL_REQUIRED, alarm „Potrebna ručna intervencija“
    O->>RC: RPC approve na EntranceGate {plate} (gumb „Ručno odobri ulaz“)
    RC->>G: sesija (MANUAL), GRANTED MANUAL_APPROVAL, alarm se gasi
    RC->>R: RPC open, odgovor rampe ide dashboardu
  else garaža puna ili vozilo već unutra
    RC->>G: DENIED GARAGE_FULL ili ALREADY_INSIDE
  end
  V->>R: prolazi (IR slobodan)
  R->>R: zatvara rampu nakon 2 s
```

- Ručno odobravanje: gumb šalje rampi RPC `approve`. Rule chain ga presretne, uzme registraciju iz parametra,
  iz polja „Registracija za ručno odobrenje“ (atribut `manualPlate`) ili zadnju očitanu, otvori sesiju i tek onda
  rampi pošalje `open`. Bez sesije bi isto vozilo na izlazu dobilo `NO_ACTIVE_SESSION`. Gumb „Odbij“ (RPC `deny`)
  bilježi `DENIED MANUAL_DENIAL`, a rampa kratko zapišti.
- Ponovni pokušaji čitanja (pouzdanost 0,60–0,85) ostaju unutar ALPR servisa, koji uzme do 3 slike i vrati jedan
  rezultat. Rule chain sve ispod 0,85 šalje operateru, pa se rampa nikad ne otvori sama ispod praga.
- Rampa mora potvrditi naredbu u 5 s, inače alarm „Rampa ne potvrđuje naredbe“.

## Tok izlaska

```mermaid
sequenceDiagram
  participant V as Vozilo
  participant R as ESP32 rampi (ExitGate)
  participant RC as Rule chain
  participant A as ALPR servis (ALPR-Exit)
  participant G as Asset Garage
  participant O as Operater (dashboard)
  V->>R: dolazi na izlaz (IR)
  R->>RC: telemetrija {vehicleArrived: true, state: CLOSED}
  RC->>A: RPC readPlate {gate: EXIT}
  A-->>RC: {status, plate, ocrConfidence}
  RC->>G: traži sesiju u sessions
  alt pouzdanost ≥ 0,85 i sesija postoji
    RC->>RC: trajanje i cijena
    RC->>G: briše sesiju, SESSION_CLOSED,<br/>exit = 1, durationMin, price
    RC->>R: RPC open
    R-->>RC: {success: true, state: OPENING}
  else pouzdanost < 0,85 ili nema sesije
    RC->>G: MANUAL_REQUIRED ili DENIED NO_ACTIVE_SESSION, alarm
    O->>RC: RPC approve na ExitGate {plate}
    RC->>G: zatvori sesiju ako postoji
    RC->>R: RPC open
  end
  V->>R: prolazi (IR slobodan)
  R->>R: zatvara rampu nakon 2 s
```

Cijena se računa istim [pravilom naplate](model-podataka.md#pravilo-naplate) kao `SOFTWARE/baza`; postavke su
atributi asseta „Garage“ (`freeMinutes`, `pricePerHourCents`, `dailyCapCents`, `timeMultiplier`; demo:
`provision.py --demo-pricing`). S `exitFuzzyMatch = true` izlaz prihvaća jedan pogrešno pročitan znak ako
odgovara točno jedna sesija.

## Rule chain

Izvor su TBEL skripte u [`rulechain/scripts`](../../SOFTWARE/thingsboard/rulechain/scripts) i generator
[`build_rule_chain.py`](../../SOFTWARE/thingsboard/rulechain/build_rule_chain.py), koji piše `garaza.json`.
`provision.py` ga uveze i postavi kao *root* rule chain. Promjene u web sučelju se gube pri sljedećem
`provision.py`, pa ih treba prenijeti u skripte.

Redoslijed: profili uređaja šalju poruke u red `SequentialByOriginator` (poruke jednog uređaja jedna za drugom), a
nakon „Na asset Garage“ *checkpoint* ih vrati u isti red s assetom kao pošiljateljem. Tako se brojevi mjesta, sesije
i sažetak mijenjaju jedan po jedan, i kad ulaz i izlaz odlučuju u istom trenutku. U zadanom redu `Main` poruke se
obrađuju paralelno, pa bi stariji broj slobodnih mjesta mogao prepisati noviji (uočeno u testu).

| poruka | što rule chain napravi |
|---|---|
| bilo koja telemetrija ili atribut uređaja | pravila alarma profila, spremanje |
| `esp32-spots`: `freeSpots`, `occupiedSpots` | atributi `sensorFree`, `sensorOccupied` asseta Garage → sažetak, alarm „Garaža puna“ |
| rampa: `vehicleArrived: true` | RPC `readPlate` ALPR uređaju te rampe (15 s) → odluka (`decide.tbel`) → sesija, telemetrija odluke, RPC `open` rampi, alarm „Potrebna ručna intervencija“ |
| RPC `approve` / `deny` s dashboarda na rampu | ista odluka kao ručna radnja; rampa odgovara dashboardu |
| RPC `open`, `close`, `reset` s dashboarda | ravno rampi |
| Connect / Disconnect / Inactivity Event | `online`, alarm „Uređaj nije dostupan“; mjesta `UNKNOWN` / `OFFLINE`; bez čvora senzora nema slobodnih mjesta |
| rampa ne odgovori na naredbu u 5 s | `ackTimeout`, alarm „Rampa ne potvrđuje naredbe“ |

Entiteti, ključevi telemetrije, atributi asseta i alarmi: [entiteti-i-alarmi.md](entiteti-i-alarmi.md).
Teme i poruke svih uređaja: [komunikacijski ugovor](komunikacijski-ugovor.md).

## Raspored (deployment)

| uređaj | što pokreće | kako |
|---|---|---|
| laptop (≥ 4 GB RAM) | ThingsBoard CE, rule chain, dashboardi | `SOFTWARE/thingsboard/docker-compose.yml` + `provision/provision.py` |
| laptop ili Raspberry Pi uz kameru | ALPR servis | `python -m edge_service --config edge.yaml tb-alpr` |
| 2× ESP32 | firmware senzora i rampi | PlatformIO, `secrets.h`: Wi-Fi, IP laptopa, *access token* |
| laptop bez hardvera (razvoj) | ThingsBoard + simulirani uređaji | `python integracija/simulacija_b.py` |

## Degradirani rad

| ispadne | ponašanje |
|---|---|
| ThingsBoard ili mreža | nema automatskih odluka: rampe se otvaraju samo tipkom, same se zatvaraju i ne spuštaju se na vozilo; LED mjesta rade; nakon povratka čvorovi pošalju sva stanja |
| ALPR (kamera, OCR) | RPC `readPlate` ne odgovori u 15 s → `MANUAL_REQUIRED` + alarm; operater odobrava na dashboardu |
| ESP32 senzora | Disconnect → mjesta `UNKNOWN` / `OFFLINE` (nikad „slobodno“), alarm „Uređaj nije dostupan“ |
| jedan senzor | nakon 5 neuspjelih mjerenja `UNKNOWN` / `TIMEOUT`, alarm „Senzor mjesta ne radi“ |
| ESP32 rampi | RPC `open` bez odgovora u 5 s → alarm „Rampa ne potvrđuje naredbe“ |
| Wi-Fi | ESP32 se sam ponovno spaja (svakih 5 s) i ponovno pošalje sva stanja |

## Testiranje

| što | kako | gdje |
|---|---|---|
| rule chain sa simuliranim uređajima: ulaz, ručno odobrenje, već unutra, izlaz s cijenom, nepoznato vozilo, puna garaža, gubitak čvora senzora; `decide.tbel`: nikad otvaranje ispod praga, allow-lista, cijena = Python pravilo | `python integracija/simulacija_b.py` ili `TB_LIVE_TEST=1 pytest integracija/tests/test_varijanta_b.py` | CI (ThingsBoard u Dockeru); lokalno treba ThingsBoard + `provision.py` |
| isto s pravim ALPR-om i OCR-om na sintetskim slikama | `python integracija/simulacija_b.py --alpr sim` | treba Tesseract |
| `garaza.json` odgovara skriptama, svi čvorovi su povezani | `pytest thingsboard/tests` | CI |
| ALPR kao uređaj ThingsBoarda | `pytest edge/tests/test_tb_alpr.py` | CI |
| firmware oba ESP32 | `pio test -e native`, `pio run` | CI |

## Usporedba s varijantom A

| | A – lokalno odlučivanje (edge) | B – ThingsBoard (odabrano) |
|---|---|---|
| MQTT broker | Mosquitto na edge računalu | ugrađeni MQTT transport ThingsBoarda |
| parkirne sesije | SQLite na edge računalu | atribut `sessions` asseta Garage |
| odluke i naplata | Python servis (`SOFTWARE/edge`) | rule chain (TBEL skripte u repozitoriju) |
| edge računalo | broker, ALPR, kontrola pristupa, baza, bridge | samo ALPR (može i na laptopu) |
| bez ThingsBoarda ili mreže | ulaz i izlaz rade, podaci se šalju naknadno | automatski ulaz i izlaz ne rade, rampe samo tipkom |
| MQTT teme | vlastiti ugovor (`garage/...`, JSON sheme) | API uređaja ThingsBoarda (`v1/gateway/...`, `v1/devices/me/...`) |
| testiranje | unit i e2e testovi bez ThingsBoarda | unit testovi + scenarij na pravom ThingsBoardu |
| vrijeme odziva | lokalno | ovisi o mreži do laptopa |

## Što je napravljeno za prijelaz i što još treba

| | stanje |
|---|---|
| firmware senzora i rampi na ThingsBoard API-ju (gateway, RPC, `vehicleArrived`) | ✅ preveden, unit testovi · ⬜ na hardveru |
| ALPR kao uređaj ThingsBoarda (`edge_service tb-alpr`) | ✅ isprobano sa sintetskim slikama · ⬜ s kamerom |
| rule chain, provisioning (gateway uređaji, tokeni, postavke asseta), dashboardi | ✅ isprobano na ThingsBoard CE 4.2.1 |
| simulatori i scenarij za B | ✅ |
| access control (`SOFTWARE/edge/edge_service`), baza (`SOFTWARE/baza`), bridge (`tb_bridge`), Mosquitto | ostaju kao varijanta A (rezerva), ne koriste se |
| ⬜ tajni *access tokeni* i lozinka tenanta za demonstraciju | Anja |
| ⬜ cijeli [plan integracije](../upravljanje/plan-integracije.md) s hardverom | svi |
