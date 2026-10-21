# 3. Korisničke upute

Za **operatera** garaže (osoba koja prati dashboard) i za **tehničara** koji sustav pokreće.

## 3.1 Pokretanje sustava

1. Uključi maketu sklopkom (5 V adapter) – LED na mjestima zasvijetle, rampe se zatvore.
2. Uključi edge računalo (Raspberry Pi). Servisi (Mosquitto, edge servis, ThingsBoard bridge) se pokreću sami
   (Docker `restart: unless-stopped` ili systemd). Provjera: `docker compose -f docker-compose.edge.yml ps`.
3. Na laptopu pokreni ThingsBoard (`docker compose up -d` u `osoba-7-thingsboard`) i otvori
   `http://localhost:8080` → *Dashboards* → **Garaža – nadzor**.
4. Nakon ~30 s: sva mjesta imaju boju (zeleno/crveno), rampe "zatvorena", broj slobodnih mjesta je točan.

## 3.2 Dashboard "Garaža – nadzor"

| dio | značenje |
|---|---|
| tlocrt | zeleno = slobodno, crveno = zauzeto, **sivo = nepoznato** (senzor ne radi – ne broji se kao slobodno) |
| ULAZ / IZLAZ | stanje rampe, je li vozilo na crti rampe, zadnja očitana registracija i pouzdanost |
| plavi kvadrat | broj slobodnih mjesta |
| Odluke pristupa | svaka odluka: smjer, registracija, odluka (zeleno odobreno, crveno odbijeno, žuto ponovno snimanje, ljubičasto ručno), razlog, pouzdanost |
| Alarmi | aktivni i ugašeni alarmi; potvrdi (*acknowledge*) kad ih riješiš |
| gumbi | Otvori ulaz / Otvori izlaz / Ručno odobri ulaz / Ručno odobri izlaz / Odbij vozilo na ulazu |

## 3.3 Što učiniti kada...

| situacija | na dashboardu | što učiniti |
|---|---|---|
| pločica se ne može pročitati | odluka `MANUAL_REQUIRED`, alarm "Potrebna ručna intervencija", rampa zatvorena | provjeri vozilo (kamerom/vizualno) → **Ručno odobri ulaz** (otvara sesiju s zadnjom očitanom registracijom) ili **Odbij** |
| garaža je puna | `DENIED GARAGE_FULL`, alarm "Garaža puna" | vozilo se vraća; ili pričekaj izlazak |
| vozilo već "unutra" | `DENIED ALREADY_INSIDE` | provjeri je li prethodni izlaz propušten; tehničar može zatvoriti staru sesiju (`parking-sessions close <REG>`) |
| izlaz bez sesije | `DENIED NO_ACTIVE_SESSION` | provjeri registraciju; **Ručno odobri izlaz** (bilježi se "izlaz bez sesije") |
| rampa ne odgovara | alarm "Rampa ne potvrđuje naredbe" | provjeri napajanje/Wi-Fi ESP32 rampi; tipka na rampi radi i bez mreže |
| rampa u kvaru (ERROR) | alarm "Rampa u kvaru", LED trepće | ukloni prepreku, drži tipku rampe 3 s (reset) |
| senzor mjesta ne radi | mjesto sivo, alarm "Senzor mjesta ne radi" | provjeri kabel senzora (oznaka `S-P0x`) |
| ThingsBoard ne radi | dashboard se ne osvježava | **garaža i dalje radi**; podaci će se pojaviti kad se ThingsBoard vrati |

Svaka ručna radnja zapisuje se u bazu s vremenom, operaterom i napomenom (`parking-sessions events`).

## 3.4 Naredbe za tehničara

```bash
parking-sessions --db data/garage.db list --active          # tko je trenutno u garaži
parking-sessions --db data/garage.db list --plate ZG1234AB  # povijest vozila
parking-sessions --db data/garage.db show <ID sesije>       # detalji, trenutna cijena
parking-sessions --db data/garage.db stats --days 7         # statistika, ulasci po satu
parking-sessions --db data/garage.db events --limit 20      # zapis odluka i ručnih radnji
python -m edge_service manual approve-entry --plate ZG1234AB --note "razlog"
python -m garage_contract.monitor                           # sve MQTT poruke uživo
```

## 3.5 Gašenje
Ugasi edge računalo (`sudo shutdown now`), zatim maketu sklopkom. Aktivne sesije ostaju u bazi.
