# Entiteti, telemetrija i alarmi u ThingsBoardu

Sve stvara `provision/provision.py`; telemetriju šalje bridge (`bridge/tb_bridge/mapping.py`).

## Asset

| ime | tip | atributi (server) | relacije |
|---|---|---|---|
| Garage | Garage | `name`, `totalSpots`, `address`, `timezone` | `Contains` → svi uređaji (alarmi se propagiraju na asset) |

## Uređaji

| uređaj | profil | izvor (MQTT) | telemetrija | atributi (server) |
|---|---|---|---|---|
| ParkingSpot-01 … 06 | ParkingSpot | `garage/parking/spot/P0x/telemetry` | `state`, `stateCode` (0 slobodno, 1 zauzeto, −1 nepoznato), `occupied`, `distanceCm`, `sensorStatus` | `spotId`, `name`, `index`, `xPos`, `yPos` |
| EntranceGate, ExitGate | Gate | `garage/gate/<gate>/state`, alert `GATE_NO_ACK` | `state`, `stateCode` (0 CLOSED, 1 OPENING, 2 OPEN, 3 CLOSING, 4 ERROR), `vehiclePresent`, `lastRequestId`, `lastCommandSuccess`, `lastCommandReason`, `lastSource`, `ackTimeout` | `gate`, `name` |
| ALPR-Entrance, ALPR-Exit | ALPR | `garage/alpr/<gate>/event`, alert `ALPR_REPEATED_FAILURE` | `plate`, `status`, `ocrConfidence`, `detectionConfidence`, `accepted`, `processingMs`, `consecutiveFailures`, `alprFailing` | `gate`, `name` |
| Garage-Edge (gateway) | GarageEdge | `garage/summary`, `access/decision`, `session/event`, `system/alert` | `freeSpots`, `occupiedSpots`, `unknownSpots`, `totalSpots`, `occupancyPct`, `activeSessions`, `full`, `decision*`, `manualRequired`, `entry`, `exit`, `durationMin`, `price`, `session*`, `alert_<TIP>`, `lastAlert` | `name`, `totalSpots` |
| esp32-spots, esp32-gates, access-control, alpr-service, tb-bridge, … | Controller | `garage/system/heartbeat`, `garage/system/status/<id>` | `online`, `uptimeS`, `rssi`, `freeHeap`, `fwVersion`, `ip`, `deviceType` | – (stvara ih gateway automatski) |

Za analitiku: `entry`/`exit` = 1 po događaju → zbroj po satu = broj ulazaka/izlazaka; `durationMin` i `price`
šalju se pri zatvaranju sesije → prosjek / zbroj po danu.

## Pravila alarma (profili uređaja)

| profil | alarm | ozbiljnost | stvara se kad | gasi se kad |
|---|---|---|---|---|
| ParkingSpot | Senzor mjesta ne radi | MAJOR | `sensorStatus` ∉ {OK, SIMULATED} (TIMEOUT, OUT_OF_RANGE, OFFLINE) | `sensorStatus` ∈ {OK, SIMULATED} |
| Gate | Rampa ne potvrđuje naredbe | MAJOR | `ackTimeout = true` | `ackTimeout = false` (sljedeća uspješna potvrda) |
| Gate | Rampa u kvaru | CRITICAL | `stateCode = 4` (ERROR) | `stateCode ≠ 4` |
| ALPR | ALPR uzastopno ne uspijeva | MAJOR | `alprFailing = true` (3 neuspjela čitanja zaredom) | `alprFailing = false` |
| GarageEdge | Garaža puna | WARNING | `full = true` | `full = false` |
| GarageEdge | Potrebna ručna intervencija | WARNING | `manualRequired = true` | sljedeća odluka |
| Controller | Uređaj nije dostupan | MAJOR | `online = false` (MQTT Last Will) | `online = true` |

"Nema podataka sa senzora" pokriva se dvostruko: Last Will ESP32-a (`online=false` → sva njegova mjesta
`OFFLINE`) i firmware (`TIMEOUT` nakon 5 neuspjelih mjerenja).

## RPC (gumbi na dashboardu)

| uređaj | metoda | parametri | što se dogodi |
|---|---|---|---|
| EntranceGate / ExitGate | `open`, `close` | – | `garage/access/manual` OPEN_GATE/CLOSE_GATE (access control bilježi i šalje naredbu) |
| EntranceGate / ExitGate | `reset` | – | `RESET` naredba rampi (izlaz iz ERROR) |
| Garage-Edge | `approveEntry`, `approveExit` | `{"plate": "ZG1234AB"}` (opcionalno; inače zadnja očitana) | ručno odobrenje + sesija |
| Garage-Edge | `deny` | `{"gate": "ENTRANCE"}` | ručno odbijanje |
