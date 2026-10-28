# Mobilna aplikacija – analitika garaže

**Zadužen:** Leo Hreljanović. Zamjena za ThingsBoard dio: Anja.

Aplikacija prikazuje analitiku garaže – zauzetost, ulaske po satu, prosječno trajanje parkiranja i povijest
sesija. Podatke **samo čita** iz ThingsBoarda preko REST API-ja; garaža nikad ne ovisi o njoj (vidi rizik R-15
u [planu projekta](../../PROJEKT/plan-projekta)).

## Kako dohvatiti podatke

- ThingsBoard pokreni prema [thingsboard/README.md](../thingsboard/README.md); podaci bez hardvera:
  `python integracija/simulacija.py --broker --tb` (iz mape `SOFTWARE`).
- Za aplikaciju napravi korisnika **samo za čitanje** (customer user), ne koristi tenant račun.
- Prijava: `POST /api/auth/login` → JWT token; telemetrija: `GET /api/plugins/telemetry/{entityType}/{entityId}/values/timeseries?keys=...`
  ([REST API](https://thingsboard.io/docs/reference/rest-api/)).
- Koji uređaji i telemetrijski ključevi postoje: [entiteti-i-alarmi.md](../../PROJEKT/sustav/entiteti-i-alarmi.md);
  što prikazuje analitički dashboard: [thingsboard/dashboards](../thingsboard/dashboards).

## Tvoji zadaci

- [ ] odabrati tehnologiju (npr. Flutter ili React Native) i ovdje opisati kako se projekt otvara i pokreće
- [ ] dizajn ekrana i dohvat podataka (9.11. – 6.12.2026.)
- [ ] prva verzija s ključnim brojkama do KT5 (20. 12. 2026.), nakon KT6 (17. 1. 2027.) samo popravci
- [ ] izvrsna verzija (APK) u [izvrsne-verzije](../izvrsne-verzije) na kraju projekta
