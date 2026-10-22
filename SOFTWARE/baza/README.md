# Osoba 8 – baza, aplikacijska logika, testiranje i dokumentacija

**Zadužen:** Lovro Gale – baza, testovi i GitHub (repozitorij, CI, ploča zadataka); pomaže Tomi sa senzorima i Patriku s ožičenjem makete.

Ti si vlasnik **podataka** (parkirne sesije), **testova** i **dokaza da sustav radi**.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [sessions/](.) | Python paket `parking_sessions`: SQLite shema, API sesija, naplata, allow-lista, zapis događaja, brisanje starih podataka, CLI, generator testnih sesija |
| [sessions/tests/](tests/test_sessions.py) | 30 testova (naplata na granicama, životni ciklus, dvostruki ulazak, povijest, statistika, privatnost, CLI) |
| [model-podataka.md](../../PROJEKT/sustav/model-podataka.md) | ER dijagram, pravila baze, pravilo naplate, primjeri API-ja |
| [testni-plan.md](../../PROJEKT/testiranje/testni-plan.md) | ~60 testnih slučajeva: ugovor, senzori, rampe, ALPR/OCR, baza, **svi scenariji faze 4**, ThingsBoard |
| [testni-zapisnik.md](../../PROJEKT/testiranje/testni-zapisnik.md) | zapisnik – već upisani rezultati automatskih testova i simulacije (21. 10. 2026.) |
| [dokumentacija/](../../PROJEKT/dokumentacija) | kostur završne dokumentacije; **korisničke upute** i **privatnost** već napisane |

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

Naplata: prvih 15 min besplatno, zatim 1,50 € po započetom satu, najviše 15 € po danu
(`PRICING_PROFILE=demo` → 1 minuta = 1 sat za demonstraciju). Detalji: [model-podataka.md](../../PROJEKT/sustav/model-podataka.md).

Edge servis (osoba 6) koristi bazu ovako: ulaz → `open_session`, mjesto zauzeto → `assign_spot`,
izlaz → `find_active` + `close_session`, svaka odluka i ručna radnja → `log_event`.

## Tvoji zadaci

- [ ] dogovoriti s timom pravilo naplate (ako želite drugačije – promijeni `PricingPolicy` i testove)
- [ ] provoditi testove iz [testnog plana](../../PROJEKT/testiranje/testni-plan.md) i upisivati ih u [zapisnik](../../PROJEKT/testiranje/testni-zapisnik.md) – u simulaciji odmah, na maketi od 4. tjedna
- [ ] za svaku demonstracijsku registraciju pokazati ulaz, izlaz, trajanje i cijenu (`parking-sessions show`)
- [ ] prikupljati materijale svih članova i pisati dokumentaciju (`dokumentacija/`, izvoz pandocom)
- [ ] provjeriti privatnost (TC-P01) prije predaje

| isporučivo | status |
|---|---|
| baza i shema podataka | ✅ |
| modul za parkirne sesije | ✅ |
| testni plan | ✅ |
| testni zapisnik | ✅ pokrenut, ⬜ testovi na maketi |
| objedinjena dokumentacija | ✅ kostur + 2 poglavlja, ⬜ ostalo |

**Kriterij završetka:** za svaku demonstracijsku registraciju postoji zapis ulaska, izlaska, trajanja i cijene,
a svi glavni scenariji imaju evidentiran rezultat testa.
