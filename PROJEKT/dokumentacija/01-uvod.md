# 1. Uvod

## 1.1 Zadatak
_(prepisati zadatak kolegija)_

## 1.2 Cilj i opseg
Vozilo dolazi do ulaza, kamera očitava registraciju, sustav **lokalno** (na edge računalu) odlučuje smije li
vozilo ući, rampa se otvara, slobodno mjesto mijenja stanje nakon parkiranja, a sva se stanja i događaji
prikazuju u ThingsBoardu. Pri izlasku se registracija ponovno očitava, izračunava trajanje i bilježi završetak
parkirne sesije.

Maketa: 6 parkirnih mjesta (mjerilo 1:24), ulazna i izlazna rampa, USB kamera, 2× ESP32, Raspberry Pi kao
edge računalo, ThingsBoard CE. Mobilna aplikacija prikazuje analitiku garaže i podatke čita iz ThingsBoarda.

Izvan opsega: stvarna naplata, rad s pravim vozilima.

## 1.3 Tim i uloge
| tko | uloga |
|---|---|
| Patrik | voditelj projekta, arhitektura, integracija, maketa |
| Lovro Gale | baza, testiranje, dokumentacija, napajanje i ožičenje |
| Toma Burgund | senzori parkirnih mjesta, firmware |
| Luka Oslić | rampe, aktuatori, lokalna kontrola pristupa |
| Sven Matić | ALPR: detekcija pločice |
| Lukas Davorija | OCR, edge servis, odluke |
| Anja | ThingsBoard, dashboardi, alarmi |
| Leo Hreljanović | mobilna aplikacija, analitički dashboard |
