# Plan rada po tjednima (backlog)

Oznake: ✅ već pripremljeno u repozitoriju (provjeriti i preuzeti), ⬜ posao za člana tima.
Ovaj popis se lako prenese u GitHub Projects (jedna kartica po retku, oznaka = osoba, milestone = faza).

## Faza 1 – definicija i dokaz izvedivosti (tjedan 1)

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

## Faza 2 – samostalni podsustavi (tjedni 2–3)

| osoba | zadatak |
|---|---|
| 2 | ⬜ izrada baze i mjesta prema `nacrt/tlocrt.svg` · ⬜ most za senzore iznad mjesta · ⬜ 3D ispis nosača i rampi · ⬜ ožičenje prema `elektronika/wireviz/*.svg`, oznake kabela · ⬜ foto-dnevnik |
| 3 | ⬜ svih 6 senzora na maketi · ⬜ `kalibracija.py` → pragovi u `config.h` i `tablica-pragova.md` · ⬜ MQTT s pravim brokerom · ⬜ LED traka |
| 4 | ⬜ montaža obje rampe, kalibracija kutova (`closedAngle/openAngle`) · ⬜ IR senzori na crti rampe · ⬜ sigurnosni testovi (`sigurnosni-testovi.md`) |
| 5 | ⬜ skup ≥ 100 stvarnih fotografija (različite pločice, svjetlo, kut, udaljenost) · ⬜ `label_tool.py` · ⬜ `evaluate_detection.py` ≥ 90 % · ⬜ `ogranicenja.md` |
| 6 | ⬜ `evaluate_ocr.py` na stvarnom skupu, 0 pogrešno prihvaćenih · ⬜ podesiti težine/pragove ako treba · ⬜ edge na Raspberry Pi (Docker ili nativno) |
| 7 | ⬜ dashboardi s pravim podacima, prilagodba izgleda · ⬜ obavijesti na alarm (Notification center) · ⬜ izvoz dashboarda u repo |
| 8 | ⬜ provesti testove TC-B*, TC-I* u simulaciji i zapisati u `testni-zapisnik.md` · ⬜ prikupljati materijale za dokumentaciju |

## Faza 3 – integracija (tjedan 4)

⬜ Koraci 1–10 iz [plan-integracije.md](plan-integracije.md) **s hardverom**, po redu; svaki prolaz zapisuje osoba 8.

## Faza 4 – stabilizacija i testiranje (tjedan 5)

⬜ Svi scenariji iz testnog plana (prazna/puna garaža, nepoznata/nečitljiva pločica, prekid Wi-Fi, prekid
ThingsBoarda, restart ESP32 i edge računala, vozilo predugo ispod rampe, ulazak bez izlaska, izlazak bez sesije)
· ⬜ rezervni video · ⬜ zamrzavanje značajki (samo popravci).

## Faza 5 – prezentacija i dokumentacija (tjedan 6)

⬜ dokumentacija iz `osoba-8-baza-testovi/dokumentacija` · ⬜ slajdovi (arhitektura, rezultati ALPR i senzora,
dashboard, sesija iz baze, ograničenja) · ⬜ generalna proba demo scenarija ×2.
