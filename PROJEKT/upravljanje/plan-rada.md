# Plan rada po tjednima (backlog)

Oznake: ✅ već pripremljeno u repozitoriju (provjeriti i preuzeti), ⬜ posao za člana tima.
Ovaj popis se lako prenese u GitHub Projects (jedna kartica po retku, oznaka = osoba, milestone = faza).

## Vremenski okvir

Projekt traje od **19.10.2026.** do roka za predaju **29.1.2027.** (15 tjedana, T1–T15).

| faza | tjedni | datumi |
|---|---|---|
| 1 – definicija i dokaz izvedivosti | T1–T2 | 19.10. – 1.11.2026. |
| 2 – samostalni podsustavi | T3–T7 | 2.11. – 6.12.2026. |
| 3 – integracija | T8–T9 | 7.12. – 20.12.2026. |
| blagdanska stanka (rezerva) | T10–T11 | 21.12.2026. – 3.1.2027. |
| 4 – stabilizacija i testiranje | T12–T13 | 4.1. – 17.1.2027. |
| 5 – dokumentacija, prezentacija i predaja | T14–T15 | 18.1. – 29.1.2027. |

Kontrolne točke (dogovor tima, plan projekta v1.3):

| | kontrolna točka | planirano | ostvareno |
|---|---|---|---|
| KT1 | arhitektura, plan i repozitorij | 28.10.2026. | 27.10.2026. ✅ |
| KT2 | dokaz izvedivosti (1 senzor, 1 servo, ThingsBoard, ALPR na stvarnoj fotografiji), nacrt makete | 10.11.2026. | |
| KT3 | baza makete izrađena | 23.11.2026. | |
| KT4 | podsustavi rade na hardveru (senzori 20/20, sigurnosni testovi rampi, detekcija ≥ 90 %) | 23.12.2026. | |
| KT5 | integracija s hardverom završena; MVP mobilne aplikacije | 11.1.2027. | |
| KT6 | svi testni scenariji prolaze, demo video snimljen | 17.1.2027. | |
| KT7 | završna dokumentacija i prezentacija; projekt predan na GitLab | 29.1.2027. | |

## Faza 1 – definicija i dokaz izvedivosti (T1–T2, 19.10. – 1.11.2026.)

| osoba | zadatak |
|---|---|
| 1 | ✅ arhitektura, ugovor, zahtjevi, rizici, odluke, plan integracije, demo scenarij · ⬜ potvrditi odluke D-004 i D-007 s timom · ⬜ otvoriti GitHub Projects ploču iz ovog popisa · ⬜ dogovoriti termin tjednog sastanka |
| 2 | ✅ tlocrt, kalkulator kamere, 3D dijelovi, sheme spajanja, popis komponenti · ⬜ odabrati mjerilo autića i materijal · ⬜ naručiti/prikupiti komponente · ⬜ **provjeriti minimalni fokus kamere** |
| 3 | ✅ firmware, filtar s testovima, simulator, alati za kalibraciju i test 20x · ⬜ spojiti JEDAN HC-SR04 (s djeliteljem!) i vidjeti `CAL` mjerenja |
| 4 | ✅ firmware, stanje rampe s testovima, simulator · ⬜ pomaknuti jedan SG90 s ESP32 (`open e` u serijskom monitoru) |
| 5 | ✅ detektor, generator pločica, sintetski skup, evaluacija · ⬜ isprintati pločice · ⬜ prve 10 fotografija makete/autića `capture_dataset.py` |
| 6 | ✅ OCR, edge servis, odluke, testovi · ⬜ `python -m edge_service read` na prvim fotografijama |
| 7 | ✅ docker-compose, provisioning, bridge, dva dashboarda, alarmi · ⬜ pokrenuti ThingsBoard na laptopu, `provision.py`, promijeniti lozinku |
| 8 | ✅ baza sesija, naplata, CLI, generator, testovi, testni plan, kostur dokumentacije · ⬜ pročitati testni plan, dogovoriti pravilo naplate s timom |

## Faza 2 – samostalni podsustavi (T3–T7, 2.11. – 6.12.2026.)

| osoba | zadatak |
|---|---|
| 2 | ⬜ izrada baze i mjesta prema `nacrt/tlocrt.svg` · ⬜ most za senzore iznad mjesta · ⬜ 3D ispis nosača i rampi · ⬜ ožičenje prema `elektronika/wireviz/*.svg`, oznake kabela · ⬜ foto-dnevnik |
| 3 | ⬜ svih 6 senzora na maketi · ⬜ `kalibracija.py` → pragovi u `config.h` i `tablica-pragova.md` · ⬜ MQTT s pravim brokerom · ⬜ LED traka |
| 4 | ⬜ montaža obje rampe, kalibracija kutova (`closedAngle/openAngle`) · ⬜ IR senzori na crti rampe · ⬜ sigurnosni testovi (`sigurnosni-testovi.md`) |
| 5 | ⬜ skup ≥ 100 stvarnih fotografija (različite pločice, svjetlo, kut, udaljenost) · ⬜ `label_tool.py` · ⬜ `evaluate_detection.py` ≥ 90 % · ⬜ `ogranicenja.md` |
| 6 | ⬜ `evaluate_ocr.py` na stvarnom skupu, 0 pogrešno prihvaćenih · ⬜ podesiti težine/pragove ako treba · ⬜ edge na Raspberry Pi (Docker ili nativno) |
| 7 | ⬜ dashboardi s pravim podacima, prilagodba izgleda · ⬜ obavijesti na alarm (Notification center) · ⬜ izvoz dashboarda u repo |
| 8 | ⬜ provesti testove TC-B*, TC-I* u simulaciji i zapisati u `testni-zapisnik.md` · ⬜ prikupljati materijale za dokumentaciju |

## Faza 3 – integracija (T8–T9, 7.12. – 20.12.2026.)

⬜ Koraci 1–10 iz [plan-integracije.md](plan-integracije.md) **s hardverom**, po redu; svaki prolaz zapisuje osoba 8.

## Blagdanska stanka (T10–T11, 21.12.2026. – 3.1.2027.)

Rezerva za zaostatke iz faza 2 i 3; nema planiranih zadataka.

## Faza 4 – stabilizacija i testiranje (T12–T13, 4.1. – 17.1.2027.)

⬜ Svi scenariji iz testnog plana (prazna/puna garaža, nepoznata/nečitljiva pločica, prekid Wi-Fi, prekid
ThingsBoarda, restart ESP32 i edge računala, vozilo predugo ispod rampe, ulazak bez izlaska, izlazak bez sesije)
· ⬜ rezervni video · ⬜ zamrzavanje značajki (samo popravci).

## Faza 5 – dokumentacija, prezentacija i predaja (T14–T15, 18.1. – 29.1.2027.)

⬜ dokumentacija iz `PROJEKT/dokumentacija` · ⬜ slajdovi (arhitektura, rezultati ALPR i senzora,
dashboard, sesija iz baze, ograničenja) · ⬜ generalna proba demo scenarija ×2 · ⬜ arhiviranje na GitLabu
prema [uputama nastavnika](../../OSTALO/upute-nastavnika-gitlab.md), najkasnije **29.1.2027.**
