# Entiteti, telemetrija i alarmi u ThingsBoardu

Varijanta B ([varijanta-b.md](varijanta-b.md)). Sve stvara `provision/provision.py`: profile, uređaje, gateway
uređaje s *access tokenima*, asset „Garage“ s postavkama i root rule chain. Telemetriju šalju sami uređaji, a
odluke, sesije i sažetak piše rule chain. Ključevi i RPC metode: [komunikacijski ugovor](komunikacijski-ugovor.md).

## Asset

| ime | tip | atributi (server) | relacije |
|---|---|---|---|
| Garage | Garage | `name`, `totalSpots`, `address`, `timezone`; postavke rule chaina (`policy`, `allowlist`, `acceptThreshold`, `exitFuzzyMatch`, `freeMinutes`, `pricePerHourCents`, `dailyCapCents`, `timeMultiplier`); `sessions`, `sensorFree`, `sensorOccupied`, `lastPlateEntrance`, `lastPlateExit`, `manualPlate` | `Contains` → svi uređaji (alarmi se propagiraju na asset) |

Telemetrija asseta (piše rule chain): sažetak (`freeSpots`, `occupiedSpots`, `unknownSpots`, `totalSpots`,
`occupancyPct`, `activeSessions`, `availableSpots`, `full`), odluke (`decision*`, `manualRequired`) i sesije
(`sessionEvent`, `sessionId`, `sessionPlate`, `entry`, `exit`, `sessionEntryTime`, `durationS`, `durationMin`,
`price`).

Za analitiku: `entry`/`exit` = 1 po događaju → zbroj po satu = broj ulazaka/izlazaka; `durationMin` i `price`
šalju se pri zatvaranju sesije → prosjek / zbroj po danu.

## Uređaji

| uređaj | profil | tko šalje | telemetrija | atributi (server) |
|---|---|---|---|---|
| ParkingSpot-01 … 06 | ParkingSpot | `esp32-spots` | `state`, `stateCode` (0 slobodno, 1 zauzeto, −1 nepoznato), `occupied`, `distanceCm`, `sensorStatus` | `spotId`, `name`, `index`, `xPos`, `yPos` |
| EntranceGate, ExitGate | Gate | `esp32-gates` | `state`, `stateCode` (0 CLOSED, 1 OPENING, 2 OPEN, 3 CLOSING, 4 ERROR), `vehiclePresent`, `vehicleArrived`, `lastSource`, `lastCommandSuccess`, `lastCommandReason`; `ackTimeout` (rule chain) | `gate`, `name` |
| ALPR-Entrance, ALPR-Exit | ALPR | `alpr-service` | `plate`, `status`, `ocrConfidence`, `detectionConfidence`, `accepted`, `processingMs`, `consecutiveFailures`, `alprFailing` | `gate`, `name` |
| esp32-spots, esp32-gates, alpr-service | Controller (gateway) | sami | `uptimeS`, `rssi`, `freeHeap`; `esp32-spots` i `freeSpots`, `occupiedSpots`, `unknownSpots`, `totalSpots`; `online` (rule chain) | `name`, `inactivityTimeout` (90 000 ms); klijentski: `fwVersion`, `ip`, `deviceType` |

*Access tokeni* gatewaya su zadano `esp32-spots-token`, `esp32-gates-token` i `alpr-service-token`. Za demonstraciju
postavi tajne tokene (`TB_TOKEN_SPOTS`, `TB_TOKEN_GATES`, `TB_TOKEN_ALPR` pri pokretanju `provision.py`) i iste upiši u
`secrets.h` oba ESP32 i u `edge.yaml`.

## Alarmi

| alarm | entitet | ozbiljnost | stvara se kad | gasi se kad | tko |
|---|---|---|---|---|---|
| Senzor mjesta ne radi | ParkingSpot | MAJOR | `sensorStatus` ∉ {OK, SIMULATED} (TIMEOUT, OUT_OF_RANGE, OFFLINE) | `sensorStatus` ∈ {OK, SIMULATED} | profil ParkingSpot |
| Rampa u kvaru | Gate | CRITICAL | `stateCode = 4` (ERROR) | `stateCode ≠ 4` | profil Gate |
| ALPR uzastopno ne uspijeva | ALPR | MAJOR | `alprFailing = true` (3 neuspjela čitanja zaredom) | `alprFailing = false` | profil ALPR |
| Rampa ne potvrđuje naredbe | Gate | MAJOR | RPC rampi bez odgovora u 5 s | sljedeća potvrda | rule chain |
| Uređaj nije dostupan | gateway | MAJOR | Disconnect / Inactivity Event | Connect / Activity Event | rule chain |
| Garaža puna | Garage | WARNING | `availableSpots = 0` | ima mjesta | rule chain |
| Potrebna ručna intervencija | Garage | WARNING | `MANUAL_REQUIRED` ili `NO_ACTIVE_SESSION` | sljedeća odluka | rule chain |

Kad `esp32-spots` izgubi vezu, rule chain njegova mjesta postavi na `UNKNOWN` / `OFFLINE` (nikad „slobodno“) i
`sensorFree = 0`.

## RPC (gumbi na dashboardu)

| uređaj | metoda | parametri | što se dogodi |
|---|---|---|---|
| EntranceGate / ExitGate | `open`, `close`, `reset` | – | naredba ravno rampi (`reset` izlazi iz ERROR) |
| EntranceGate / ExitGate | `approve` | `{"plate": "ZG1234AB"}` (neobavezno; inače `manualPlate` ili zadnja očitana) | rule chain: ručno odobrenje + sesija, zatim `open` |
| EntranceGate | `deny` | – | rule chain: `DENIED MANUAL_DENIAL`, rampa kratko zapišti |

Polje „Registracija za ručno odobrenje“ na nadzornom dashboardu piše atribut `manualPlate` asseta Garage.
