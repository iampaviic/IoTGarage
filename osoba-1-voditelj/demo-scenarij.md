# Scenarij završne demonstracije

Trajanje ~10 min + pitanja. Uloge: **voditelj** (priča), **operater** (dashboard), **vozač** (pomiče autiće),
**tehničar** (terminal s monitorom, spreman za plan B).

## Kontrolna lista (dan prije i 30 min prije)

- [ ] maketa uključena, sve LED trake zelene, rampe zatvorene
- [ ] edge računalo: `docker compose ... ps` – mosquitto, edge, tb-bridge `running`
- [ ] ThingsBoard otvoren: dashboard "Garaža – nadzor" (puni zaslon) + "Garaža – analitika" u drugoj kartici
- [ ] fiktivna povijest obrisana: `python osoba-7-thingsboard/tools/seed_history.py --clear` (prikazujemo **stvarne** podatke)
- [ ] `PRICING_PROFILE=demo` (1 min = 1 h → vidi se cijena)
- [ ] 3 autića s pločicama (npr. `ZG1234AB`, `ST555B`, i jedan s prljavom/prekrivenom pločicom)
- [ ] monitor ugovora otvoren u terminalu: `python -m garage_contract.monitor`
- [ ] rezervni video (`demo.mp4`) na laptopu i USB-u; rezervni ESP32, kabel, punjač
- [ ] plan B: `python osoba-1-voditelj/integracija/simulacija.py --tb --interactive`

## Glavni scenarij

| # | radnja | što se vidi | tko |
|---|---|---|---|
| 1 | pokaži dashboard | sva mjesta zelena, "6 slobodnih mjesta" (ili koliko ih je) | operater |
| 2 | autić `ZG1234AB` dolazi do ulaza, staje na graničnik | IR senzor → `vehiclePresent`; kamera snima | vozač |
| 3 | ALPR | na tlocrtu kod ULAZA: `ZG 1234-AB`, pouzdanost ~95 % | operater |
| 4 | odluka | tablica odluka: `ENTRY ZG1234AB GRANTED AUTHORIZED` | voditelj objašnjava lokalnu odluku na edgeu |
| 5 | rampa se otvara | servo, zelena LED, dashboard "otvorena" | – |
| 6 | autić prolazi, rampa se zatvara sama | IR slobodan → 2 s → zatvaranje | vozač |
| 7 | parkiranje na P03 | P03 crveno, broj slobodnih −1, LED na mjestu crvena | vozač |
| 8 | pokaži sesiju u bazi | `parking-sessions --db data/garage.db list --active` | tehničar |
| 9 | analitika | graf zauzetosti skočio, "ulasci po satu" +1 | operater |
| 10 | (nakon ~2 min) autić napušta P03 i dolazi na izlaz | P03 zeleno | vozač |
| 11 | ALPR na izlazu, pronađena sesija | tablica: `EXIT ZG1234AB GRANTED` | – |
| 12 | trajanje i cijena | analitika / tablica sesija: npr. 2,3 min → **3,00 €** (demo naplata) | voditelj objašnjava pravilo naplate |
| 13 | rampa se otvara, autić izlazi, sesija `CLOSED` | `parking-sessions ... show <id>` | tehničar |

## Kontrolirana greška (odabrati jednu ili dvije)

**A – nečitljiva pločica:** autić s prekrivenom pločicom → 3 pokušaja (`RETRY`) → `MANUAL_REQUIRED`,
alarm "Potrebna ručna intervencija", rampa **ostaje zatvorena**. Operater klikne "Ručno odobri ulaz" →
`GRANTED (MANUAL_APPROVAL)`, u bazi `entry_mode = MANUAL` + zapis tko i zašto (`parking-sessions events`).

**B – ThingsBoard ne radi:** `docker compose stop thingsboard` → autić ulazi, rampa se otvara normalno
(odluka je lokalna!). `docker compose start thingsboard` → nakon ~1 min događaji se pojave na dashboardu
s točnim vremenom (bridge ih je čuvao).

**C – izlaz bez sesije:** autić koji nije ušao dođe na izlaz → `DENIED NO_ACTIVE_SESSION`.

**D – senzor ne radi:** odspoji jedan HC-SR04 → mjesto sivo `UNKNOWN`, ne broji se kao slobodno, alarm.

## Rezervni video

Snimiti cijeli glavni scenarij + grešku A u tjednu 5 (mobitel na stativu + snimka zaslona dashboarda),
montirati jedno do drugog. Trajanje ≤ 4 min.

## Šest kriterija uspjeha (pokazati eksplicitno)

1. Maketa radi pouzdano → koraci 1–13 bez zastoja
2. Senzori ispravno prikazuju zauzetost → koraci 7, 10 + testni zapis 20x (osoba 3)
3. ALPR čita testne registracije → korak 3 + tablica točnosti (osobe 5, 6)
4. Rampe reagiraju na lokalne odluke → koraci 5, 11 + greška B
5. ThingsBoard prikazuje stvarno stanje i povijest → koraci 1, 9, 12
6. Potpuna parkirna sesija → koraci 8, 12, 13
