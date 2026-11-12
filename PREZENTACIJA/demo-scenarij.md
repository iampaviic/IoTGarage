# Scenarij završne demonstracije

Trajanje ~10 min + pitanja. Uloge: **voditelj** (priča), **operater** (dashboard), **vozač** (pomiče autiće),
**tehničar** (ThingsBoard s detaljima uređaja i assetom Garage, spreman za plan B).

## Kontrolna lista (dan prije i 30 min prije)

- [ ] maketa uključena, sve LED trake zelene, rampe zatvorene
- [ ] ThingsBoard radi, rule chain „Garaža (varijanta B)“ je *root*; `esp32-spots`, `esp32-gates` i `alpr-service` su *Active*
- [ ] ALPR servis radi (`python -m edge_service --config edge/edge.yaml tb-alpr` ili Docker na Piju)
- [ ] ThingsBoard otvoren: dashboard "Garaža – nadzor" (puni zaslon) + "Garaža – analitika" u drugoj kartici
- [ ] fiktivna povijest obrisana: `python SOFTWARE/thingsboard/tools/seed_history.py --clear` (prikazujemo **stvarne** podatke)
- [ ] sesije od proba obrisane: atribut `sessions` asseta Garage = `{}`
- [ ] demo naplata: atribut `timeMultiplier` asseta Garage = 60 (`provision.py --demo-pricing`; 1 min = 1 h → vidi se cijena)
- [ ] 3 autića s pločicama (npr. `ZG1234AB`, `ST555B`, i jedan s prljavom/prekrivenom pločicom)
- [ ] u drugoj kartici *Entities → Assets → Garage* (atributi `sessions`, telemetrija odluka)
- [ ] rezervni video (`demo.mp4`) na laptopu i USB-u; rezervni ESP32, kabel, punjač
- [ ] plan B: `python SOFTWARE/integracija/simulacija_b.py --interactive` (simulirani uređaji na istom ThingsBoardu)

## Glavni scenarij

| # | radnja | što se vidi | tko |
|---|---|---|---|
| 1 | pokaži dashboard | sva mjesta zelena, "6 slobodnih mjesta" (ili koliko ih je) | operater |
| 2 | autić `ZG1234AB` dolazi do ulaza, staje na graničnik | IR senzor → `vehicleArrived`; rule chain traži ALPR, kamera snima | vozač |
| 3 | ALPR | na tlocrtu kod ULAZA: `ZG 1234-AB`, pouzdanost ~95 % | operater |
| 4 | odluka | tablica odluka: `ENTRY ZG1234AB GRANTED AUTHORIZED` | voditelj objašnjava odluku u rule chainu ThingsBoarda |
| 5 | rampa se otvara | servo, zelena LED, dashboard "otvorena" | – |
| 6 | autić prolazi, rampa se zatvara sama | IR slobodan → 2 s → zatvaranje | vozač |
| 7 | parkiranje na P03 | P03 crveno, broj slobodnih −1, LED na mjestu crvena | vozač |
| 8 | pokaži sesiju | asset Garage, atribut `sessions`: `ZG1234AB` s vremenom ulaska; "Vozila u garaži" = 1 | tehničar |
| 9 | analitika | graf zauzetosti skočio, "ulasci po satu" +1 | operater |
| 10 | (nakon ~2 min) autić napušta P03 i dolazi na izlaz | P03 zeleno | vozač |
| 11 | ALPR na izlazu, pronađena sesija | tablica: `EXIT ZG1234AB GRANTED` | – |
| 12 | trajanje i cijena | analitika / tablica sesija: npr. 2,3 min → **3,00 €** (demo naplata) | voditelj objašnjava pravilo naplate |
| 13 | rampa se otvara, autić izlazi, sesija zatvorena | tablica „Završene parkirne sesije“ na analitici; `sessions` više nema `ZG1234AB` | tehničar |

## Kontrolirana greška (odabrati jednu ili dvije)

**A – nečitljiva pločica:** autić s prekrivenom pločicom → ALPR uzme do 3 slike → `MANUAL_REQUIRED`,
alarm "Potrebna ručna intervencija", rampa **ostaje zatvorena**. Operater upiše registraciju u "Registracija za
ručno odobrenje" i klikne "Ručno odobri ulaz" → `GRANTED (MANUAL_APPROVAL)`, sesija s `entryMode = MANUAL`.

**B – ThingsBoard ne radi:** `docker compose stop thingsboard` → automatski ulaz ne radi, ali vozač otvori rampu
tipkom, a rampa se sama zatvori i ne spušta se na autić (sigurnost je u firmwareu). `docker compose start
thingsboard` → uređaji se sami spoje i stanja mjesta su točna. Voditelj objašnjava cijenu varijante B (D-012).

**C – izlaz bez sesije:** autić koji nije ušao dođe na izlaz → `DENIED NO_ACTIVE_SESSION`.

**D – senzor ne radi:** odspoji jedan HC-SR04 → mjesto sivo `UNKNOWN`, ne broji se kao slobodno, alarm. Ili isključi
ESP32 senzora → sva mjesta `OFFLINE`, alarm "Uređaj nije dostupan", broj slobodnih 0.

## Rezervni video

Snimiti cijeli glavni scenarij + grešku A u fazi 4, do KT7 (17.1.2027.) (mobitel na stativu + snimka zaslona dashboarda),
montirati jedno do drugog. Trajanje ≤ 4 min.

## Šest kriterija uspjeha (pokazati eksplicitno)

1. Maketa radi pouzdano → koraci 1–13 bez zastoja
2. Senzori ispravno prikazuju zauzetost → koraci 7, 10 + testni zapis 20x (Toma)
3. ALPR čita testne registracije → korak 3 + tablica točnosti (Sven, Lukas)
4. Rampe reagiraju na odluke i ostaju sigurne bez mreže → koraci 5, 11 + greška B
5. ThingsBoard prikazuje stvarno stanje i povijest → koraci 1, 9, 12
6. Potpuna parkirna sesija → koraci 8, 12, 13
