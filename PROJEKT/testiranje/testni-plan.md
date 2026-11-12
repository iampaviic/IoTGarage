# Testni plan

Svaki test ima ID (koriste ga [zahtjevi](../sustav/zahtjevi.md) i [testni zapisnik](testni-zapisnik.md)).
**Tip:** A = automatski (pytest / alat), R = ručno na maketi, S = u simulaciji s ThingsBoardom (`simulacija_b.py`),
H = na hardveru. Automatski testovi: `pytest` iz mape `SOFTWARE` (CI ih vrti na svakom PR-u); scenarij varijante B
s pravim ThingsBoardom: `TB_LIVE_TEST=1 pytest integracija/tests/test_varijanta_b.py` (`test_b` dolje). Testovi
označeni (A) provjeravaju kod varijante A, koji ostaje kao rezerva.

## Ugovor i privatnost

| ID | test | tip | koraci / automatski test | očekivano |
|---|---|---|---|---|
| TC-C01 | sve poruke poštuju ugovor | A, S, H | `test_b` (svaki korak provjeren u ThingsBoardu); na maketi telemetrija svih uređaja tijekom demo scenarija | scenarij prolazi; u ThingsBoardu nema nepoznatih ključeva |
| TC-C02 | rule chain odgovara skriptama, primjeri poruka (A) | A | `thingsboard/tests/test_rule_chain.py`; `ugovor/tests/test_contract.py` (A) | prolaz |
| TC-P01 | privatnost | R | provjeri: samo generirane pločice, `save_crops: false` ili retencija, `purge` radi, TTL u ThingsBoardu | sve ispunjeno |

## Senzori mjesta (Toma)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-S01 | jedan senzor prepoznaje vozilo | H | serijski `cal`, stavi/makni autić | jasna razlika > 4 cm |
| TC-S02 | 20× postavi/makni po mjestu | H | `tools/provjera_20x.py --port COM5 --all --cycles 20` | 20/20, točno 40 promjena po mjestu |
| TC-S03 | filtar (medijan, histereza, potvrda) | A | `firmware/test` (`pio test -e native`) | 8/8 |
| TC-S04 | neispravan senzor → UNKNOWN | A, H | odspoji ECHO jednog senzora | ≤ 1 s `UNKNOWN/TIMEOUT`, mjesto se ne broji kao slobodno, alarm |
| TC-S05 | ponovno spajanje Wi-Fi / ThingsBoard | H | ugasi router 30 s pa upali | ESP32 se vrati sam, ponovno objavi sva stanja |
| TC-S06 | nestanak čvora | S, H | `test_b` korak 8; isključi napajanje ESP32 | `online = false` u ≤ 45 s, mjesta `UNKNOWN` / `OFFLINE`, alarm "Uređaj nije dostupan" |

## Rampe (Luka)

| ID | test | tip | očekivano |
|---|---|---|---|
| TC-R00 | stroj stanja (C++ i Python) | A | `pio test -e native` 7/7, `pytest rampe/simulator` 6/6 |
| TC-R01 – TC-R13 | otvaranje, zatvaranje, auto-zatvaranje, ne zatvara na vozilo, sigurnosno otvaranje, tipka, ERROR/reset, dvostruka naredba, nevaljana naredba, ispad ThingsBoarda ili mreže, restart, struja | H | [sigurnosni testovi rampi](sigurnosni-testovi-rampi.md) |

## ALPR i OCR (Sven, Lukas)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-A01 | kamera snima vozilo | H | `capture_dataset.py` | pločica oštra i u kadru na graničniku |
| TC-A02 | detekcija ≥ 90 % | A, H | `evaluate_detection.py dataset/real/<skup>` | ≥ 90 % na kontroliranom skupu |
| TC-A03 | vrijeme obrade | A, H | izvještaj detekcije + OCR; `processingMs` uređaja `ALPR-Entrance` | detekcija < 200 ms, ukupno < 2 s na računalu s ALPR-om |
| TC-O01 | tablica točnosti OCR-a | A, H | `evaluate_ocr.py dataset/real/<skup>` | ≥ 90 % točno pročitano (bilo koja razina) |
| TC-O02 | nema pogrešno prihvaćenih | A, H | isto | **0** pogrešno prihvaćenih |
| TC-O03 | nikad otvaranje ispod praga | A | `test_varijanta_b.py::test_gate_never_opens_below_the_accept_threshold` (`decide.tbel` u ThingsBoardu); (A) `edge/tests/test_decisions.py` | prolaz (sve kombinacije) |
| TC-O04 | normalizacija (O/0, I/1, grb, ...) | A | `tests/test_ocr.py` | prolaz |

## Baza i sesije (Lovro)

U varijanti B sesije vodi rule chain: TC-B01 i TC-B04 pokriva `test_b` (koraci 1, 4, 5), a TC-B02
`test_varijanta_b.py::test_price_matches_the_python_pricing_rule` (TBEL cijena = Python pravilo na svim granicama).
Testovi ispod provjeravaju paket `parking_sessions` (A), koji je i referenca pravila naplate.

| ID | test | tip | automatski test | očekivano |
|---|---|---|---|---|
| TC-B01 | otvori → zatvori sesiju, trajanje, cijena | A | `test_full_session_lifecycle` | 77 min → 3,00 € |
| TC-B02 | granični slučajevi naplate | A | `test_real_pricing` (0, 15:00, 15:01, 60:00, 60:01, 24 h, 25 h) | prema pravilu |
| TC-B03 | povijest i statistika | A | `test_history_and_stats` | ispravni brojevi |
| TC-B04 | isto vozilo ne može ući dvaput | A | `test_vehicle_cannot_enter_twice` | `ActiveSessionExists` |
| TC-B05 | zatvaranje dvaput / nepostojeće | A | `test_close_twice_fails`, `test_close_unknown_session` | greška, bez promjene |
| TC-B06 | brisanje starih podataka | A | `test_purge_keeps_active_sessions` | aktivne ostaju |
| TC-B07 | baza preživi restart | A | `test_file_database_persists` | sesija postoji nakon ponovnog otvaranja |
| TC-B08 | generator testnih sesija | A | `test_generator_is_deterministic_and_consistent` | ponovljiv, ispravne cijene |

## Sustav (scenariji iz faze 4)

| ID | scenarij (plan, faza 4) | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-I01 | **dopuštena registracija** – cijeli ulaz → parkiranje → izlaz | A, S, H | `test_b` koraci 1, 2, 5; na maketi demo koraci 1–13 | `GRANTED`, sesija s trajanjem i cijenom; vrijeme zaustavljanje → otvaranje < 3 s |
| TC-I02 | **nepoznata registracija** (`policy: allowlist` na assetu Garage) | S, H | postavi `policy = allowlist`, `allowlist = ["ZG1234AB"]`, dovezi drugu pločicu | `DENIED NOT_ON_ALLOWLIST`, rampa zatvorena |
| TC-I03 | nesigurno očitanje → ručno | A, S | `test_b` korak 3; ALPR sam uzme do 3 slike | `MANUAL_REQUIRED`, rampa zatvorena, ručno odobrenje `MANUAL_APPROVAL` |
| TC-I04 | **potpuno puna garaža** | A, S, H | `test_b` korak 7; na maketi napuni sva mjesta | `DENIED GARAGE_FULL`, alarm "Garaža puna" |
| TC-I05 | **izlazak bez aktivne sesije** | A, S, H | `test_b` korak 6 | `DENIED NO_ACTIVE_SESSION`, alarm "Potrebna ručna intervencija" |
| TC-I06 | **prazna garaža** | H | sva mjesta prazna, restart sustava | sažetak: sva slobodna, dashboard zelen |
| TC-I07 | neispravan senzor ili čvor se ne broji | A, S | `test_b` korak 8 (čvor izgubi vezu); simulator `3x` (kvar senzora) | mjesta `UNKNOWN`, slobodna = samo `FREE`; alarm |
| TC-I08 | **prekid ThingsBoarda** | R, H | `docker compose stop thingsboard`, vozilo na ulaz, tipka, `start` | rampa radi tipkom i sama se zatvara; nakon `start` uređaji se sami spoje, sesije i stanja točni |
| TC-I09 | **restart ESP32** | H | reset oba ESP32 | < 30 s sve radi, stanja ponovno objavljena |
| TC-I10 | **restart ALPR računala** | H | `sudo reboot` ili ponovno pokretanje `tb-alpr` | servis se sam spoji; aktivne sesije ostaju (u ThingsBoardu) |
| TC-I11 | simulacijski način | A, S | `simulacija_b.py` (i `--alpr sim`), simulatori `*_tb.py` | scenarij prolazi |
| TC-I12 | **vozilo predugo ispod rampe** | H | autić ostavi ispod otvorene rampe 60 s | rampa ostaje gore; nakon odlaska se zatvori |
| TC-I13 | **ulazak bez odgovarajućeg izlaska** (isto vozilo ponovno na ulazu) | A, S, H | `test_b` korak 4 | `DENIED ALREADY_INSIDE` (operater može razriješiti) |
| TC-I14 | **prekid Wi-Fi-ja** | H | ugasi Wi-Fi 1 min | rampe lokalno rade (tipka); nakon povratka stanja točna |
| TC-I15 | **loše osvjetljenje** | H | ugasi stropno svjetlo, 10 dolazaka | izmjeriti udio `ACCEPT/RETRY/MANUAL`, 0 pogrešnih |
| TC-I16 | **nečitljiva pločica** | A, S, H | `test_b` korak 3 (`--alpr sim`: prava nečitljiva slika); na maketi prekrij pločicu | `MANUAL_REQUIRED`, rampa zatvorena, alarm |
| TC-I17 | rampa ne potvrđuje | S | `gate_simulator_tb.py --no-ack exit`, vozilo na izlazu s aktivnom sesijom | nakon 5 s alarm „Rampa ne potvrđuje naredbe“ |

## ThingsBoard (Anja)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-T01 | promjena mjesta na dashboardu | S, H | promijeni stanje, štoperica | < 3 s |
| TC-T02 | analitika | S | `seed_history.py`, zatim `--clear` | grafovi popunjeni / prazni |
| TC-T03 | alarmi | S, H | izazovi svaki alarm iz `entiteti-i-alarmi.md` | alarm se stvori i ugasi |
| TC-T04 | gumbi (RPC) | A, S, H | "Otvori ulaz", "Ručno odobri ulaz" (s upisanom registracijom), "Odbij"; `test_b` koraci 3 i 6 | rampa se otvara, odluka `MANUAL_APPROVAL` / `MANUAL_DENIAL` u tablici |
| TC-T05 | obavijest | H | izazovi alarm | obavijest u zvoncu (+ e-mail ako je postavljen) |
| TC-T06 | restart ne briše ništa | R | `docker compose restart` / `down` + `up` | uređaji, dashboardi i povijest postoje |
| TC-T07 | (A) međuspremnik bridgea | A | `tests/test_bridge.py` | prolaz |
