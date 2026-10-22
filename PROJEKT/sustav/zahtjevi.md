# Funkcionalni i nefunkcionalni zahtjevi

Prioritet (MoSCoW): **M** = mora, **S** = trebalo bi, **C** = moglo bi. Stupac "provjera" upućuje na test
iz [testnog plana](../testiranje/testni-plan.md) (osoba 8). Status ažurira osoba 1 na tjednom sastanku.

## Funkcionalni

| ID | zahtjev | prioritet | vlasnik | provjera | status |
|---|---|---|---|---|---|
| FR-01 | Sustav prepoznaje zauzetost svakog od 4–6 parkirnih mjesta | M | 3 | TC-S01, TC-S02 | softver gotov, čeka hardver |
| FR-02 | Stanje mjesta prikazuje se na dashboardu unutar nekoliko sekundi | M | 3, 7 | TC-T01 | provjereno u simulaciji |
| FR-03 | Neispravan senzor označava mjesto kao `UNKNOWN`, nikad kao slobodno | M | 3, 6 | TC-S04, TC-I07 | gotovo (testovi) |
| FR-04 | Kamera snima vozilo na ulazu i izlazu | M | 2, 5 | TC-A01 | čeka hardver |
| FR-05 | Sustav pronalazi pločicu i izrezuje je s ispravljenom perspektivom | M | 5 | TC-A02 | gotovo (sintetski 100 %) |
| FR-06 | Sustav čita registraciju i vraća pouzdanost | M | 6 | TC-O01 | gotovo (sintetski) |
| FR-07 | Rampa se nikad ne otvara automatski ispod praga pouzdanosti (0.85) | M | 6 | TC-O03 | gotovo (test po svim kombinacijama) |
| FR-08 | Edge lokalno odlučuje o ulasku: valjana registracija + slobodno mjesto + nije već unutra | M | 6 | TC-I01 | gotovo |
| FR-09 | Nesigurno očitanje → nova slika (do 3x) → ručno odobrenje | M | 6 | TC-I03 | gotovo |
| FR-10 | Ulazna i izlazna rampa otvaraju/zatvaraju se na naredbu i potvrđuju izvršenje | M | 4 | TC-R01 | firmware gotov |
| FR-11 | Rampa se automatski zatvara i ne zatvara dok je vozilo ispod nje | M | 4 | TC-R03, TC-R04 | firmware + testovi gotovi |
| FR-12 | Ručno otvaranje rampe (fizička tipka i dashboard) | M | 4, 7 | TC-R06, TC-T04 | gotovo |
| FR-13 | Ulazak otvara parkirnu sesiju, izlazak je zatvara s trajanjem i cijenom | M | 8 | TC-B01 | gotovo |
| FR-14 | Izlazak bez aktivne sesije se odbija i traži intervenciju | M | 6, 8 | TC-I05 | gotovo |
| FR-15 | Dashboard: tlocrt, slobodna mjesta, rampe, zadnja registracija | M | 7 | TC-T01 | gotovo |
| FR-16 | Analitički dashboard: zauzetost, ulasci po satu, prosječno trajanje, popunjenost | M | 7 | TC-T02 | gotovo |
| FR-17 | Alarmi: nema podataka senzora, ALPR ne uspijeva, rampa ne potvrđuje, garaža puna | M | 7 | TC-T03 | gotovo |
| FR-18 | Povijest sesija dostupna (baza + dashboard) | M | 8, 7 | TC-B03 | gotovo |
| FR-19 | Popis dopuštenih registracija (allow-list) kao opcija | S | 6, 8 | TC-I06 | gotovo |
| FR-20 | Obavijest (web/e-mail) na alarm | C | 7 | TC-T05 | upute u README osobe 7 |
| FR-21 | Druga kamera / neuronski detektor pločica | C | 5 | – | nije planirano za prvu verziju |

## Nefunkcionalni

| ID | zahtjev | mjera | provjera |
|---|---|---|---|
| NFR-01 | Rad bez ThingsBoarda | ulaz/izlaz rade, podaci se šalju naknadno | TC-I08 |
| NFR-02 | Vrijeme od zaustavljanja vozila do otvaranja rampe | < 3 s u kontroliranim uvjetima | TC-I01 (mjeriti) |
| NFR-03 | Točnost detekcije pločice na vlastitom skupu slika | ≥ 90 % | TC-A02 |
| NFR-04 | Senzor mjesta | 20/20 ispravnih ciklusa po mjestu, bez treperenja | TC-S02 |
| NFR-05 | Restart ThingsBoarda ne briše konfiguraciju ni povijest | provjereno | TC-T06 |
| NFR-06 | Restart ESP32 / edge računala: sustav se oporavi sam | < 30 s | TC-I09, TC-I10 |
| NFR-07 | Vrijeme u UTC ISO 8601 u svim porukama i bazi | 100 % poruka (monitor) | TC-C01 |
| NFR-08 | Privatnost: samo izmišljene registracije, nema spremanja punih slika, brisanje nakon 30 dana | provjera konfiguracije | TC-P01 |
| NFR-09 | Svaki podsustav ima simulacijski način | simulatori + `ALPR_SOURCE=sim` | TC-I11 |
| NFR-10 | Svaka poruka poštuje komunikacijski ugovor | 0 grešaka u monitoru tijekom demo scenarija | TC-C01 |
