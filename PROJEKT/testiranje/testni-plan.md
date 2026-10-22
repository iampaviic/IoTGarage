# Testni plan

Svaki test ima ID (koriste ga [zahtjevi](../sustav/zahtjevi.md) i [testni zapisnik](testni-zapisnik.md)).
**Tip:** A = automatski (pytest / alat), R = ručno na maketi, S = u simulaciji (`simulacija.py`), H = na hardveru.
Automatski testovi: `pytest` iz mape `SOFTWARE` (CI ih vrti na svakom PR-u).

## Ugovor i privatnost

| ID | test | tip | koraci / automatski test | očekivano |
|---|---|---|---|---|
| TC-C01 | sve poruke poštuju ugovor | A, H | `integracija/tests/test_e2e.py::test_all_messages_follow_the_contract`; na maketi monitor tijekom cijelog demo scenarija | 0 crvenih poruka |
| TC-C02 | primjer svake poruke odgovara shemi | A | `contract/tests/test_contract.py` | prolaz |
| TC-P01 | privatnost | R | provjeri: samo generirane pločice, `save_crops: false` ili retencija, `purge` radi, TTL u ThingsBoardu | sve ispunjeno |

## Senzori mjesta (osoba 3)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-S01 | jedan senzor prepoznaje vozilo | H | serijski `cal`, stavi/makni autić | jasna razlika > 4 cm |
| TC-S02 | 20× postavi/makni po mjestu | H | `tools/provjera_20x.py --all --cycles 20` | 20/20, točno 40 promjena po mjestu |
| TC-S03 | filtar (medijan, histereza, potvrda) | A | `firmware/test` (`pio test -e native`) | 8/8 |
| TC-S04 | neispravan senzor → UNKNOWN | A, H | odspoji ECHO jednog senzora | ≤ 1 s `UNKNOWN/TIMEOUT`, mjesto se ne broji kao slobodno, alarm |
| TC-S05 | ponovno spajanje Wi-Fi/MQTT | H | ugasi router 30 s pa upali | ESP32 se vrati sam, ponovno objavi sva stanja |
| TC-S06 | Last Will | H | isključi napajanje ESP32 | `online:false` u ≤ 45 s, mjesta `OFFLINE`, alarm "Uređaj nije dostupan" |

## Rampe (osoba 4) – detalji u [sigurnosnim testovima](sigurnosni-testovi-rampi.md)

| ID | test | tip | očekivano |
|---|---|---|---|
| TC-R00 | stroj stanja (C++ i Python) | A | `pio test -e native` 7/7, `pytest rampe/simulator` 6/6 |
| TC-R01 – TC-R13 | otvaranje, zatvaranje, auto-zatvaranje, ne zatvara na vozilo, sigurnosno otvaranje, tipka, ERROR/reset, dvostruka naredba, nevaljana naredba, ispad MQTT-a, ispad edgea, restart, struja | H | vidi dokument osobe 4 |

## ALPR i OCR (osobe 5, 6)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-A01 | kamera snima vozilo | H | `capture_dataset.py` | pločica oštra i u kadru na graničniku |
| TC-A02 | detekcija ≥ 90 % | A, H | `evaluate_detection.py dataset/real/<skup>` | ≥ 90 % na kontroliranom skupu |
| TC-A03 | vrijeme obrade | A | izvještaj detekcije + OCR | detekcija < 200 ms, ukupno < 2 s na edge računalu |
| TC-O01 | tablica točnosti OCR-a | A, H | `evaluate_ocr.py dataset/real/<skup>` | ≥ 90 % točno pročitano (bilo koja razina) |
| TC-O02 | nema pogrešno prihvaćenih | A, H | isto | **0** pogrešno prihvaćenih |
| TC-O03 | nikad otvaranje ispod praga | A | `SOFTWARE/edge/tests/test_decisions.py::test_never_opens_below_accept_threshold` | prolaz (sve kombinacije) |
| TC-O04 | normalizacija (O/0, I/1, grb, ...) | A | `tests/test_ocr.py` | prolaz |

## Baza i sesije (osoba 8)

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
| TC-I01 | **dopuštena registracija** – cijeli ulaz → parkiranje → izlaz | A, S, H | `test_e2e.py::test_entry_park_exit_creates_complete_session`; na maketi demo koraci 1–13 | `GRANTED`, sesija s mjestom, trajanjem i cijenom; vrijeme zaustavljanje → otvaranje < 3 s |
| TC-I02 | **nepoznata registracija** (policy `allowlist`) | A, H | `test_access_control.py::test_allowlist_policy` | `DENIED NOT_ON_ALLOWLIST`, rampa zatvorena |
| TC-I03 | nesigurno očitanje → ponovno → ručno | A, S | `test_low_confidence_retries_then_needs_operator` | 3 pokušaja, `MANUAL_REQUIRED`, ručno odobrenje bilježi operatera |
| TC-I04 | **potpuno puna garaža** | A, H | `test_full_garage_is_denied`; na maketi napuni sva mjesta | `DENIED GARAGE_FULL`, alarm "Garaža puna" |
| TC-I05 | **izlazak bez aktivne sesije** | A, S, H | `test_exit_without_session_is_denied`, e2e | `DENIED NO_ACTIVE_SESSION` |
| TC-I06 | **prazna garaža** | H | sva mjesta prazna, restart sustava | sažetak: sva slobodna, dashboard zelen |
| TC-I07 | neispravan senzor se ne broji | A, S | `test_unknown_spots_are_not_free`, e2e `test_broken_sensor_is_not_counted_as_free` | `unknownSpots` ≥ 1, slobodna = samo `FREE` |
| TC-I08 | **prekid ThingsBoarda** | R, H | `docker compose stop thingsboard`, vozilo uđe, `start` | ulaz radi; događaji se pojave s izvornim vremenom |
| TC-I09 | **restart ESP32** | H | reset oba ESP32 | < 30 s sve radi, stanja ponovno objavljena |
| TC-I10 | **restart edge računala** | H | `sudo reboot` | servisi se sami pokrenu (Docker `restart`/systemd), aktivne sesije ostaju |
| TC-I11 | simulacijski način | A | `simulacija.py --broker`, e2e testovi | 0 kršenja ugovora |
| TC-I12 | **vozilo predugo ispod rampe** | H | autić ostavi ispod otvorene rampe 60 s | rampa ostaje gore; nakon odlaska se zatvori |
| TC-I13 | **ulazak bez odgovarajućeg izlaska** (isto vozilo ponovno na ulazu) | A, H | `test_vehicle_cannot_enter_twice` (access control) | `DENIED ALREADY_INSIDE` (operater može razriješiti) |
| TC-I14 | **prekid Wi-Fi-ja** | H | ugasi Wi-Fi 1 min | rampe lokalno rade (tipka); nakon povratka stanja točna |
| TC-I15 | **loše osvjetljenje** | H | ugasi stropno svjetlo, 10 dolazaka | izmjeriti udio `ACCEPT/RETRY/MANUAL`, 0 pogrešnih |
| TC-I16 | **nečitljiva pločica** | A, S, H | e2e `test_unreadable_plate_needs_operator_and_gate_stays_closed`; na maketi prekrij pločicu | `MANUAL_REQUIRED`, rampa zatvorena, alarm |
| TC-I17 | rampa ne potvrđuje | A, S | `test_gate_without_ack_is_resent_then_alarm`; `gate_simulator.py --no-ack exit` | 1 ponavljanje (isti `requestId`), alarm `GATE_NO_ACK` |

## ThingsBoard (osoba 7)

| ID | test | tip | koraci | očekivano |
|---|---|---|---|---|
| TC-T01 | promjena mjesta na dashboardu | S, H | promijeni stanje, štoperica | < 3 s |
| TC-T02 | analitika | S | `seed_history.py`, zatim `--clear` | grafovi popunjeni / prazni |
| TC-T03 | alarmi | S, H | izazovi svaki alarm iz `entiteti-i-alarmi.md` | alarm se stvori i ugasi |
| TC-T04 | gumbi (RPC) | S, H | "Otvori ulaz", "Ručno odobri ulaz" | rampa se otvara, odluka `MANUAL_APPROVAL` u tablici |
| TC-T05 | obavijest | H | izazovi alarm | obavijest u zvoncu (+ e-mail ako je postavljen) |
| TC-T06 | restart ne briše ništa | R | `docker compose restart` / `down` + `up` | uređaji, dashboardi i povijest postoje |
| TC-T07 | međuspremnik bridgea | A, R | `tests/test_bridge.py`; ugasi TB, generiraj događaje, upali | međuspremnik se isprazni, podaci s izvornim vremenom |
