# 3. Korisničke upute

Za **operatera** garaže (osoba koja prati dashboard) i za **tehničara** koji sustav pokreće.

## 3.1 Pokretanje sustava

1. Uključi maketu sklopkom (5 V adapter) – LED na mjestima zasvijetle, rampe se zatvore.
2. Na laptopu pokreni ThingsBoard (`docker compose up -d` u `SOFTWARE/thingsboard`) i otvori
   `http://localhost:8080` → *Dashboards* → **Garaža – nadzor**.
3. Pokreni ALPR servis (`python -m edge_service --config edge/edge.yaml tb-alpr` u mapi `SOFTWARE`); na Raspberry
   Piju se pokreće sam (Docker `restart: unless-stopped` ili systemd).
4. Nakon ~30 s: sva mjesta imaju boju (zeleno/crveno), rampe "zatvorena", broj slobodnih mjesta je točan.

## 3.2 Dashboard "Garaža – nadzor"

| dio | značenje |
|---|---|
| tlocrt | zeleno = slobodno, crveno = zauzeto, **sivo = nepoznato** (senzor ne radi – ne broji se kao slobodno) |
| ULAZ / IZLAZ | stanje rampe, je li vozilo na crti rampe, zadnja očitana registracija i pouzdanost |
| plavi kvadrat | broj slobodnih mjesta |
| Odluke pristupa | svaka odluka: smjer, registracija, odluka (zeleno odobreno, crveno odbijeno, ljubičasto ručno), razlog, pouzdanost |
| Alarmi | aktivni i ugašeni alarmi; potvrdi (*acknowledge*) kad ih riješiš |
| gumbi | Otvori ulaz / Otvori izlaz / Ručno odobri ulaz / Ručno odobri izlaz / Odbij vozilo na ulazu |
| Registracija za ručno odobrenje | upiši registraciju prije „Ručno odobri“ ako je kamera nije pročitala ili ju je krivo pročitala |

## 3.3 Što učiniti kada...

| situacija | na dashboardu | što učiniti |
|---|---|---|
| pločica se ne može pročitati | odluka `MANUAL_REQUIRED`, alarm "Potrebna ručna intervencija", rampa zatvorena | provjeri vozilo (kamerom/vizualno), po potrebi upiši registraciju → **Ručno odobri ulaz** (otvara sesiju s upisanom ili zadnjom očitanom registracijom) ili **Odbij** |
| garaža je puna | `DENIED GARAGE_FULL`, alarm "Garaža puna" | vozilo se vraća; ili pričekaj izlazak |
| vozilo već "unutra" | `DENIED ALREADY_INSIDE` | provjeri je li prethodni izlaz propušten; tehničar može obrisati staru sesiju iz atributa `sessions` asseta Garage |
| izlaz bez sesije | `DENIED NO_ACTIVE_SESSION` | provjeri registraciju; **Ručno odobri izlaz** (bilježi se "izlaz bez sesije") |
| rampa ne odgovara | alarm "Rampa ne potvrđuje naredbe" | provjeri napajanje/Wi-Fi ESP32 rampi; tipka na rampi radi i bez mreže |
| rampa u kvaru (ERROR) | alarm "Rampa u kvaru", LED trepće | ukloni prepreku, drži tipku rampe 3 s (reset) |
| senzor mjesta ne radi | mjesto sivo, alarm "Senzor mjesta ne radi" | provjeri kabel senzora (oznaka `S-P0x`) |
| ThingsBoard ne radi | dashboard se ne osvježava, rampe se ne otvaraju same | rampe otvaraj tipkom na maketi (same se zatvaraju); ponovno pokreni ThingsBoard (`docker compose up -d`), uređaji se sami spoje |

Svaka odluka i ručna radnja zapisuje se kao telemetrija asseta Garage (tablica „Odluke pristupa“, stupac „Ručno“).

## 3.4 Naredbe za tehničara

- tko je trenutno u garaži: *Entities → Assets → Garage → Attributes*, atribut `sessions`;
- povijest sesija i odluka: *Latest telemetry* asseta Garage ili analitički dashboard (tablica „Završene parkirne sesije“);
- postavke (naplata, `policy`, `allowlist`): server atributi asseta Garage;
- stanje uređaja: *Entities → Devices* (`esp32-spots`, `esp32-gates`, `alpr-service` moraju biti *Active*);
- ponovno postavljanje svega: `python thingsboard/provision/provision.py` (ne briše sesije).

## 3.5 Gašenje
Zaustavi ALPR servis (Ctrl+C; na Piju `sudo shutdown now`), zatim maketu sklopkom i na kraju ThingsBoard
(`docker compose stop`). Aktivne sesije ostaju u ThingsBoardu.
