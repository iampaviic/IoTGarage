# 1. Uvod

## 1.1 Zadatak
_(prepisati zadatak kolegija)_

## 1.2 Cilj i opseg
Vozilo dolazi do ulaza, kamera očitava registraciju, sustav **lokalno** (na edge računalu) odlučuje smije li
vozilo ući, rampa se otvara, slobodno mjesto mijenja stanje nakon parkiranja, a sva se stanja i događaji
prikazuju u ThingsBoardu. Pri izlasku se registracija ponovno očitava, izračunava trajanje i bilježi završetak
parkirne sesije.

Maketa: 6 parkirnih mjesta (mjerilo 1:24), ulazna i izlazna rampa, USB kamera, 2× ESP32, Raspberry Pi kao
edge računalo, ThingsBoard CE.

Izvan opsega: stvarna naplata, mobilna aplikacija, rad s pravim vozilima.

## 1.3 Tim i uloge
| osoba | uloga |
|---|---|
| 1 | voditelj projekta, arhitektura, integracija |
| 2 | fizička maketa, napajanje, ožičenje |
| 3 | senzori parkirnih mjesta, firmware |
| 4 | rampe, aktuatori, lokalna kontrola |
| 5 | ALPR – detekcija pločice |
| 6 | OCR, edge servis, odluke |
| 7 | ThingsBoard, dashboardi, alarmi |
| 8 | baza, testiranje, dokumentacija |
