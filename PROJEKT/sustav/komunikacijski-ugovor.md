# Komunikacijski ugovor (verzija 1.0)

> **Strojno provjerljiva verzija** ovog dokumenta su JSON sheme u
> [`contract/garage_contract/schemas/`](../../SOFTWARE/ugovor/garage_contract/schemas) i primjeri u
> [`contract/examples/`](../../SOFTWARE/ugovor/examples). Python servisi ih uvoze iz paketa `garage_contract`,
> testovi (i CI) provjeravaju svaku poruku. Ako se dokument i sheme razlikuju, **vrijede sheme**.

## Opća pravila

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

## Teme

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

## Primjeri

### Stanje parkirnog mjesta
```json
{"spotId": "P01", "state": "OCCUPIED", "occupied": true, "distanceCm": 6.4, "sensorStatus": "OK",
 "deviceId": "esp32-spots", "uptimeMs": 512345, "timestamp": "2026-10-19T08:30:00Z"}
```
`state` je `FREE | OCCUPIED | UNKNOWN`; za `UNKNOWN` je `occupied: null`. `sensorStatus`: `OK`, `TIMEOUT`,
`OUT_OF_RANGE`, `UNSTABLE`, `SIMULATED`, `OFFLINE` (zadnje postavlja edge kad uređaj nestane).

### ALPR događaj
```json
{"requestId": "trg-entrance-7f3a9c", "cameraId": "entrance-camera", "direction": "ENTRY", "status": "OK",
 "plate": "ZG1234AB", "rawText": "ZG 1234-AB", "detectionConfidence": 0.94, "ocrConfidence": 0.89,
 "accepted": true, "processingMs": 412, "consecutiveFailures": 0, "timestamp": "2026-10-19T08:31:12Z"}
```

### Naredba rampi i odgovor
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

### Odluka i sesija
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

Svi ostali primjeri: [`contract/examples/`](../../SOFTWARE/ugovor/examples).

## Pravila odlučivanja (access control, osoba 6)

| ocrConfidence | odluka |
|---|---|
| ≥ 0.85 | automatska odluka (`GRANTED` ili `DENIED` s razlogom) |
| 0.60 – 0.85 | `RETRY` – nova slika, najviše 3 pokušaja, zatim `MANUAL_REQUIRED` |
| < 0.60 | `MANUAL_REQUIRED` – nikad automatsko otvaranje |

Razlozi odbijanja: `GARAGE_FULL`, `ALREADY_INSIDE`, `NOT_ON_ALLOWLIST` (samo ako je `policy: allowlist`),
`NO_ACTIVE_SESSION` (izlaz). Slobodna mjesta = `min(FREE mjesta, ukupno − aktivne sesije)`; `UNKNOWN` se ne broji.

## Alati

```bash
python -m garage_contract.monitor                       # sve poruke, zeleno = po ugovoru, crveno = krši ugovor
python -m garage_contract.monitor --filter 'garage/gate/#'
python -m garage_contract.monitor --pub garage/gate/entrance/command '{"requestId":"t1","command":"OPEN","reason":"TEST"}'
```

## Kako se ugovor mijenja

1. Prijedlog (issue ili poruka osobi 1) s razlogom.
2. Osoba 1 mijenja shemu + primjer + ovaj dokument u **jednom** PR-u; CI provjerava sve primjere.
3. Unos u [odluke.md](../upravljanje/odluke.md), obavijest na tjednom sastanku.
4. Nekompatibilna promjena = nova verzija (`CONTRACT_VERSION` u `garage_contract/__init__.py`).
