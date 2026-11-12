# Komunikacijski ugovor (verzija 2.0, varijanta B)

Varijanta B ([D-012](../upravljanje/odluke.md)): svi uređaji razgovaraju samo s ThingsBoardom, preko njegovog
MQTT API-ja za uređaje. Ugovor su teme tog API-ja, imena uređaja, ključevi telemetrije, RPC metode i atributi asseta
„Garage“. Imena i ključevi su u kodu na jednom mjestu: [`garage_contract/tb.py`](../../SOFTWARE/ugovor/garage_contract/tb.py)
(Python), `config.h` oba firmwarea i [rule chain](../../SOFTWARE/thingsboard/rulechain). Tokovi poruka su u
[varijanta-b.md](varijanta-b.md).

## Opća pravila

| pravilo | vrijednost |
|---|---|
| protokol | MQTT 3.1.1 prema ThingsBoardu, port 1883; korisničko ime = *access token* gateway uređaja, lozinka prazna |
| uređaji | svaki čvor je *gateway* i jednom vezom govori za svoje uređaje ([Gateway MQTT API](https://thingsboard.io/docs/reference/gateway-mqtt-api/)) |
| format | JSON, UTF-8, ključevi `camelCase`; ključ s vrijednošću `null` se ne šalje |
| QoS | 1 |
| vrijeme | ESP32 ne šalje vrijeme: ThingsBoard sprema vrijeme primitka (ms od 1970., UTC). Python uređaji smiju poslati `ts` |
| identifikatori | mjesta `P01`–`P06` → uređaji `ParkingSpot-01`…`06`; rampe `ENTRANCE` / `EXIT` → `EntranceGate` / `ExitGate`; kamere `ALPR-Entrance` / `ALPR-Exit` |
| registracije | normalizirane: velika slova, bez razmaka i crtica (`ZG1234AB`) |
| naredbe | server-side RPC; odgovor ide na isti `id`; rampa mora odgovoriti u 5 s, ALPR u 15 s |
| online | ThingsBoard sam vidi spajanje i prekid veze (Connect / Disconnect Event); keepalive 30 s, `inactivityTimeout` 90 s |
| heartbeat | svaki gateway svakih 30 s: `uptimeS` (ESP32 i `rssi`, `freeHeap`) |

## Uređaji i teme

| čvor (gateway, token) | uređaji (profil) | šalje | prima (RPC) |
|---|---|---|---|
| ESP32 senzora `esp32-spots` | `ParkingSpot-01…06` (ParkingSpot) | stanje mjesta; vlastito: `freeSpots`, `occupiedSpots`, `unknownSpots`, `totalSpots` | `sim`, `simOff`, `status` |
| ESP32 rampi `esp32-gates` | `EntranceGate`, `ExitGate` (Gate) | stanje rampe, `vehicleArrived` | `open`, `close`, `reset`, `deny` |
| ALPR servis `alpr-service` | `ALPR-Entrance`, `ALPR-Exit` (ALPR) | rezultat čitanja | `readPlate`; `simVehicle` (samo simulacija) |

| tema | smjer | sadržaj |
|---|---|---|
| `v1/gateway/connect` | čvor → TB | `{"device": "ParkingSpot-03", "type": "ParkingSpot"}` nakon svakog spajanja |
| `v1/gateway/telemetry` | čvor → TB | `{"ParkingSpot-03": [{...}]}` ili `{"ParkingSpot-03": [{"ts": 1792398600000, "values": {...}}]}` |
| `v1/gateway/rpc` | TB → čvor | `{"device": "EntranceGate", "data": {"id": 7, "method": "open", "params": {...}}}` |
| `v1/gateway/rpc` | čvor → TB | `{"device": "EntranceGate", "id": 7, "data": {"success": true, "state": "OPENING", "reason": null}}` |
| `v1/devices/me/telemetry` | čvor → TB | telemetrija samog gatewaya (heartbeat, brojevi mjesta) |
| `v1/devices/me/attributes` | čvor → TB | `fwVersion`, `ip`, `deviceType` nakon spajanja |
| `v1/devices/me/rpc/request/{id}` | TB → čvor | RPC samom gatewayu (`sim`, `simVehicle`); odgovor na `v1/devices/me/rpc/response/{id}` |

## Telemetrija uređaja

| uređaj | ključevi | kada |
|---|---|---|
| `ParkingSpot-0x` | `state` (`FREE \| OCCUPIED \| UNKNOWN`), `stateCode` (0 / 1 / −1), `occupied`, `distanceCm`, `sensorStatus` (`OK \| TIMEOUT \| OUT_OF_RANGE \| SIMULATED`; `OFFLINE` postavlja rule chain) | promjena, svakih 30 s, nakon spajanja |
| `EntranceGate`, `ExitGate` | `state` (`CLOSED \| OPENING \| OPEN \| CLOSING \| ERROR`), `stateCode` (0–4), `vehiclePresent`, `lastSource`, `lastCommandSuccess`, `lastCommandReason`; `vehicleArrived: true` kad vozilo dođe do zatvorene rampe | svaka promjena, svakih 30 s |
| `ALPR-Entrance`, `ALPR-Exit` | `plate` (`-` ako je nema), `status` (`OK \| LOW_CONFIDENCE \| INVALID_FORMAT \| NO_PLATE \| CAMERA_ERROR`), `ocrConfidence`, `detectionConfidence`, `accepted`, `processingMs`, `consecutiveFailures`, `alprFailing` | svako čitanje |

## RPC

| uređaj | metoda | parametri | odgovor |
|---|---|---|---|
| `ALPR-Entrance` / `ALPR-Exit` | `readPlate` | `{"gate": "ENTRANCE"}` | `{"status", "plate", "rawText", "ocrConfidence", "detectionConfidence", "accepted", "processingMs", "gate"}` |
| `EntranceGate` / `ExitGate` | `open`, `close`, `reset` | `{"reason", "plate"}` (neobavezno) | `{"success", "state", "reason"}`; `reason`: `VEHICLE_PRESENT`, `ERROR_STATE`, `INVALID_COMMAND`, `DUPLICATE` |
| `EntranceGate` / `ExitGate` | `deny` | – | rampa kratko zapišti i ostane zatvorena |
| `EntranceGate` / `ExitGate` | `approve`, `deny` (s dashboarda) | `{"plate": "ZG1234AB"}` (neobavezno) | presreće ih rule chain: ručna odluka, zatim `open` / `deny` rampi |
| `esp32-spots` | `sim` / `simOff` / `status` | `{"spot": "P03", "occupied": true \| false \| null}` | `{"success": true}` |
| `alpr-service` | `simVehicle` | `{"gate", "plate", "quality": "good \| poor \| unreadable"}` | samo uz `ALPR_SOURCE=sim` |

## Asset „Garage“ (rule chain)

| server atribut | značenje | piše |
|---|---|---|
| `totalSpots`, `policy` (`open` \| `allowlist`), `allowlist` (JSON lista), `acceptThreshold` (0.85), `exitFuzzyMatch` | pravila odluke | `provision.py` (samo ako nedostaju), operater |
| `freeMinutes` (15), `pricePerHourCents` (150), `dailyCapCents` (1500), `timeMultiplier` (1; demo 60) | naplata | `provision.py`, operater |
| `sessions` | aktivne sesije: `{"ZG1234AB": {"sessionId", "entryTime", "entryTs", "entryMode", "entryConfidence"}}` | rule chain |
| `sensorFree`, `sensorOccupied` | zadnji brojevi čvora senzora | rule chain |
| `lastPlateEntrance`, `lastPlateExit`, `manualPlate` | zadnje očitane registracije, registracija koju upiše operater | rule chain, dashboard |

| telemetrija asseta | ključevi |
|---|---|
| sažetak | `totalSpots`, `freeSpots`, `occupiedSpots`, `unknownSpots`, `occupancyPct`, `activeSessions`, `availableSpots`, `full` |
| odluka | `decision` (`GRANTED \| DENIED \| MANUAL_REQUIRED`), `decisionReason`, `decisionPlate`, `decisionDirection` (`ENTRY \| EXIT`), `decisionConfidence`, `decisionManual`, `manualRequired` |
| sesija | `sessionEvent` (`SESSION_OPENED \| SESSION_CLOSED`), `sessionId`, `sessionPlate`, `entry` / `exit` (= 1), `sessionEntryTime`, `durationS`, `durationMin`, `price` (EUR) |

## Pravila odlučivanja

| ocrConfidence | odluka |
|---|---|
| ≥ 0.85 | automatska odluka (`GRANTED` ili `DENIED` s razlogom) |
| < 0.85 (ALPR je već probao do 3 slike) | `MANUAL_REQUIRED` – nikad automatsko otvaranje |

Razlozi: `AUTHORIZED`, `MANUAL_APPROVAL`, `MANUAL_DENIAL`, `GARAGE_FULL`, `ALREADY_INSIDE`, `NOT_ON_ALLOWLIST` (samo uz
`policy: allowlist`), `NO_ACTIVE_SESSION` (izlaz), `LOW_CONFIDENCE`, `NO_PLATE`, `INVALID_FORMAT`, `TIMEOUT`,
`CAMERA_ERROR`. Slobodna mjesta za novo vozilo = `min(FREE mjesta, ukupno − aktivne sesije)`; `UNKNOWN` se ne broji.

## Kako se ugovor mijenja

1. Prijedlog (issue ili poruka Patriku) s razlogom.
2. Patrik u **jednom** PR-u mijenja ovaj dokument, `garage_contract/tb.py`, firmware ili simulatore i rule chain;
   CI provjerava firmware, `garaza.json` i ALPR, a scenarij (`integracija/simulacija_b.py`) cijeli tok.
3. Unos u [odluke.md](../upravljanje/odluke.md), obavijest na tjednom sastanku.

## Varijanta A (rezerva): MQTT teme preko Mosquitta (verzija 1.0)

Ne koristi se u varijanti B; ostaje dok postoji kod varijante A. Strojno provjerljiva verzija su JSON sheme u
[`SOFTWARE/ugovor/garage_contract/schemas/`](../../SOFTWARE/ugovor/garage_contract/schemas) i primjeri u
[`SOFTWARE/ugovor/examples/`](../../SOFTWARE/ugovor/examples).

### Opća pravila

| pravilo | vrijednost |
|---|---|
| protokol | MQTT 3.1.1, broker Mosquitto na edge računalu, port 1883 |
| format | JSON objekt, UTF-8, ključevi `camelCase` |
| QoS | 1 za sve poruke |
| retained | samo **stanja**: mjesta, rampe, sažetak, online status. **Naredbe i događaji nikad.** |
| vrijeme | `timestamp` u UTC ISO 8601 sa `Z` (`2026-10-19T08:31:12Z`). ESP32 bez NTP-a šalje `null`, primatelj tada koristi vrijeme primitka |
| identifikatori | mjesta `P01`–`P06` (u temi i u poruci), rampe `entrance`/`exit` u temi, `ENTRANCE`/`EXIT` u poruci |
| registracije | uvijek normalizirane: velika slova, bez razmaka i crtica (`ZG1234AB`) |
| naredbe | svaka ima `requestId`; odgovor nosi isti `requestId`; ponovljeni `requestId` se ne izvršava dvaput |
| online status | Last Will na `garage/system/status/<deviceId>` = `{"deviceId": "...", "online": false}` (retained) |
| heartbeat | svaki uređaj/servis svakih 30 s na `garage/system/heartbeat` |

### Teme

| tema | smjer | retained | shema | opis |
|---|---|---|---|---|
| `garage/parking/spot/{P01}/telemetry` | ESP32 senzora → svi | da | `spot_telemetry` | stanje mjesta: na promjenu, svakih 30 s, nakon spajanja |
| `garage/gate/{entrance\|exit}/command` | access control → ESP32 rampi | ne | `gate_command` | `OPEN`, `CLOSE`, `RESET` |
| `garage/gate/{entrance\|exit}/state` | ESP32 rampi → svi | da | `gate_state` | stanje, prisutnost vozila, potvrda naredbe (`requestId`, `success`) |
| `garage/alpr/{gate}/trigger` | access control → ALPR | ne | `alpr_trigger` | "očitaj registraciju" (`VEHICLE_DETECTED`, `RETRY`, `MANUAL`) |
| `garage/alpr/{gate}/event` | ALPR → access control | ne | `alpr_event` | rezultat čitanja s pouzdanošću |
| `garage/access/decision` | access control → svi | ne | `access_decision` | `GRANTED`, `DENIED`, `RETRY`, `MANUAL_REQUIRED` + razlog |
| `garage/access/manual` | dashboard/CLI → access control | ne | `access_manual` | ručna radnja operatera (uvijek se bilježi) |
| `garage/session/event` | access control → svi | ne | `session_event` | `SESSION_OPENED` / `SESSION_CLOSED` (trajanje, cijena) |
| `garage/summary` | access control → svi | da | `garage_summary` | broj slobodnih/zauzetih/nepoznatih mjesta, popunjenost |
| `garage/system/heartbeat` | svi → svi | ne | `heartbeat` | živ sam, uptime, RSSI, verzija |
| `garage/system/status/{deviceId}` | svi (LWT) → svi | da | `device_status` | online / offline |
| `garage/system/alert` | edge → svi | ne | `system_alert` | podigni/ugasi upozorenje (`GATE_NO_ACK`, `ALPR_REPEATED_FAILURE`, ...) |
| `garage/sim/spot/{P01}` | samo simulacija | ne | `sim_spot` | prisili stanje mjesta (simulator i firmware senzora) |
| `garage/sim/gate/{gate}/presence` | samo simulacija | ne | `sim_gate_presence` | simulirano vozilo na crti rampe |
| `garage/sim/vehicle/{gate}` | samo simulacija | da | `sim_vehicle` | koja pločica je ispred simulirane kamere |

### Primjeri

#### Stanje parkirnog mjesta
```json
{"spotId": "P01", "state": "OCCUPIED", "occupied": true, "distanceCm": 6.4, "sensorStatus": "OK",
 "deviceId": "esp32-spots", "uptimeMs": 512345, "timestamp": "2026-10-19T08:30:00Z"}
```
`state` je `FREE | OCCUPIED | UNKNOWN`; za `UNKNOWN` je `occupied: null`. `sensorStatus`: `OK`, `TIMEOUT`,
`OUT_OF_RANGE`, `UNSTABLE`, `SIMULATED`, `OFFLINE` (zadnje postavlja edge kad uređaj nestane).

#### ALPR događaj
```json
{"requestId": "trg-entrance-7f3a9c", "cameraId": "entrance-camera", "direction": "ENTRY", "status": "OK",
 "plate": "ZG1234AB", "rawText": "ZG 1234-AB", "detectionConfidence": 0.94, "ocrConfidence": 0.89,
 "accepted": true, "processingMs": 412, "consecutiveFailures": 0, "timestamp": "2026-10-19T08:31:12Z"}
```

#### Naredba rampi i odgovor
```json
{"requestId": "req-1024", "command": "OPEN", "reason": "AUTHORIZED_ENTRY", "plate": "ZG1234AB",
 "timestamp": "2026-10-19T08:31:13Z"}
```
```json
{"gate": "ENTRANCE", "state": "OPENING", "vehiclePresent": true, "requestId": "req-1024", "success": true,
 "reason": null, "source": "MQTT", "deviceId": "esp32-gates", "timestamp": "2026-10-19T08:31:14Z"}
```
Neuspjeh: `success: false` + `reason` (`VEHICLE_PRESENT`, `ERROR_STATE`, `INVALID_COMMAND`); ponovljeni
zahtjev: `success: true, reason: "DUPLICATE"`. Rampa mora odgovoriti u **3 s**, inače edge ponavlja naredbu
jednom (isti `requestId`) pa podiže alarm `GATE_NO_ACK`.

#### Odluka i sesija
```json
{"decisionId": "dec-51c2e0", "direction": "ENTRY", "plate": "ZG1234AB", "confidence": 0.89,
 "decision": "GRANTED", "reason": "AUTHORIZED", "gateRequestId": "req-1024",
 "sessionId": "S-20261019-083112-4F2A", "freeSpots": 4, "manual": false, "operator": null,
 "timestamp": "2026-10-19T08:31:13Z"}
```
```json
{"eventType": "SESSION_CLOSED", "sessionId": "S-20261019-083112-4F2A", "plate": "ZG1234AB",
 "entryTime": "2026-10-19T08:31:13Z", "exitTime": "2026-10-19T09:48:40Z", "durationS": 4647,
 "price": 3.0, "currency": "EUR", "entryMode": "AUTO", "exitMode": "AUTO",
 "entryConfidence": 0.89, "exitConfidence": 0.92, "timestamp": "2026-10-19T09:48:40Z"}
```

Svi ostali primjeri: [`SOFTWARE/ugovor/examples/`](../../SOFTWARE/ugovor/examples).

### Pravila odlučivanja (A)

| ocrConfidence | odluka |
|---|---|
| ≥ 0.85 | automatska odluka (`GRANTED` ili `DENIED` s razlogom) |
| 0.60 – 0.85 | `RETRY` – nova slika, najviše 3 pokušaja, zatim `MANUAL_REQUIRED` |
| < 0.60 | `MANUAL_REQUIRED` – nikad automatsko otvaranje |

Razlozi odbijanja: `GARAGE_FULL`, `ALREADY_INSIDE`, `NOT_ON_ALLOWLIST` (samo ako je `policy: allowlist`),
`NO_ACTIVE_SESSION` (izlaz). Slobodna mjesta = `min(FREE mjesta, ukupno − aktivne sesije)`; `UNKNOWN` se ne broji.

### Alati

```bash
python -m garage_contract.monitor                       # sve poruke, zeleno = po ugovoru, crveno = krši ugovor
python -m garage_contract.monitor --filter 'garage/gate/#'
python -m garage_contract.monitor --pub garage/gate/entrance/command '{"requestId":"t1","command":"OPEN","reason":"TEST"}'
```

### Kako se ugovor A mijenja

1. Prijedlog (issue ili poruka Patriku) s razlogom.
2. Patrik mijenja shemu + primjer + ovaj dokument u **jednom** PR-u; CI provjerava sve primjere.
3. Unos u [odluke.md](../upravljanje/odluke.md), obavijest na tjednom sastanku.
4. Nekompatibilna promjena = nova verzija (`CONTRACT_VERSION` u `garage_contract/__init__.py`).
