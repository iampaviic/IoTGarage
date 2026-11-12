# Baza parkirnih sesija, testiranje i dokumentacija

Zadužen: Lovro Gale, za bazu, testove i GitHub (repozitorij, CI, ploča zadataka). Pomaže Tomi sa senzorima i
Patriku s ožičenjem makete.

Vlasnik si podataka (parkirne sesije), testova i dokaza da sustav radi.

U [varijanti B](../../PROJEKT/sustav/varijanta-b.md) sesije vodi rule chain ThingsBoarda: aktivne su u atributu
`sessions` asseta Garage, a završene (trajanje, cijena) u njegovoj telemetriji. Pravilo naplate je isto, u
[`decide.tbel`](../thingsboard/rulechain/scripts/decide.tbel). Ovaj paket (SQLite) pripada varijanti A i ostaje
kao rezerva te kao referenca i testovi pravila naplate.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [parking_sessions/](parking_sessions) | Python paket `parking_sessions`: SQLite shema, API sesija, naplata, allow-lista, zapis događaja, brisanje starih podataka, CLI, generator testnih sesija |
| [tests/](tests/test_sessions.py) | testovi naplate na granicama, životnog ciklusa, dvostrukog ulaska, povijesti, statistike, privatnosti i CLI-ja |
| [model-podataka.md](../../PROJEKT/sustav/model-podataka.md) | ER dijagram, pravila baze, pravilo naplate, primjeri API-ja |
| [testni-plan.md](../../PROJEKT/testiranje/testni-plan.md) | testni slučajevi: ugovor, senzori, rampe, ALPR/OCR, baza, svi scenariji faze 4, ThingsBoard |
| [testni-zapisnik.md](../../PROJEKT/testiranje/testni-zapisnik.md) | zapisnik s već upisanim rezultatima automatskih testova i simulacije |
| [dokumentacija/](../../PROJEKT/dokumentacija) | kostur završne dokumentacije; korisničke upute i privatnost već su napisane |

## Baza u 30 sekundi

```bash
pip install -e .
parking-sessions --db test.db generate --days 14 --per-day 40   # izmišljene testne sesije
parking-sessions --db test.db stats --days 7
parking-sessions --db test.db list --limit 10
parking-sessions --db test.db allow add ZG1234AB --label "Testno vozilo 1"
parking-sessions --db test.db open ZG1234AB && parking-sessions --db test.db close ZG1234AB
parking-sessions --db test.db export sesije.csv                 # za Excel / izvještaj
parking-sessions --db test.db purge --days 30                   # privatnost
pytest tests
```

Pravilo naplate i demo profil: [model-podataka.md](../../PROJEKT/sustav/model-podataka.md#pravilo-naplate).

U varijanti A edge servis koristi bazu ovako: ulaz → `open_session`, mjesto zauzeto → `assign_spot`, izlaz →
`find_active` + `close_session`, a svaka odluka i ručna radnja → `log_event`.

## Zadaci

- ✅ baza, shema podataka i modul za parkirne sesije (varijanta A)
- ✅ varijanta B: sesije i naplata u rule chainu, scenarij `integracija/simulacija_b.py` provjerava ulaz, izlaz i cijenu
- ✅ testni plan · ✅ testni zapisnik pokrenut · ⬜ testovi na maketi
- ✅ kostur dokumentacije i 2 poglavlja · ⬜ ostala poglavlja
- ⬜ s timom dogovoriti pravilo naplate (za drugačije pravilo promijeni atribute asseta Garage ili `decide.tbel`,
  a dok postoji varijanta A i `PricingPolicy` s testovima)
- ⬜ provoditi testove iz [testnog plana](../../PROJEKT/testiranje/testni-plan.md) i upisivati ih u [zapisnik](../../PROJEKT/testiranje/testni-zapisnik.md): u simulaciji odmah, na maketi kad bude spremna
- ⬜ za svaku demonstracijsku registraciju pokazati ulaz, izlaz, trajanje i cijenu (tablica „Završene parkirne
  sesije“ na analitičkom dashboardu ili izvoz telemetrije asseta Garage u CSV)
- ⬜ prikupljati materijale svih članova i pisati dokumentaciju (`dokumentacija/`, izvoz pandocom)
- ⬜ provjeriti privatnost (TC-P01) prije predaje

Gotovo je kad za svaku demonstracijsku registraciju postoji zapis ulaska, izlaska, trajanja i cijene, a svi glavni
scenariji imaju upisan rezultat testa.
