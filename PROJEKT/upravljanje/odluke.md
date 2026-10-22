# Dnevnik odluka

Kratki zapisi odluka koje utječu na više članova (format: kontekst → odluka → posljedice).
Odluke označene **[PRIJEDLOG]** pripremljene su unaprijed – potvrdite ih ili promijenite na prvom sastanku.

### D-001 Lokalni MQTT broker (Mosquitto) na edge računalu
- **Kontekst:** ThingsBoard ima vlastiti MQTT, ali s fiksnim temama i autentikacijom po uređaju; generička MQTT integracija postoji samo u PE/Cloud izdanju.
- **Odluka:** svi uređaji i servisi razgovaraju preko Mosquitta na edge računalu; prema ThingsBoardu ide samo bridge kao *gateway uređaj* (Gateway MQTT API, radi u CE).
- **Posljedice:** ulaz/izlaz rade bez ThingsBoarda; bridge mora imati međuspremnik (napravljeno: SQLite buffer).

### D-002 ID mjesta `P01` i u temi i u poruci
- **Kontekst:** prijedlog je imao `spot/01/telemetry` i `"spotId": "P01"` – dvije oznake za isto.
- **Odluka:** `garage/parking/spot/P01/telemetry`.
- **Posljedice:** ThingsBoard uređaj se zove `ParkingSpot-01` (mapira bridge).

### D-003 Ugovor kao JSON Schema + Python paket
- **Odluka:** teme i sheme su kod (`contract/garage_contract`), dokument ih opisuje. Svaki test, simulator i servis provjerava poruke.
- **Posljedice:** promjena ugovora = promjena sheme + primjera u jednom PR-u (CI).

### D-004 [PRIJEDLOG] Raspberry Pi kao edge računalo, Jetson Nano kao rezerva
- **Kontekst:** imamo Raspberry Pi, Jetson Nano i jednu USB kameru. Jetson Nano (JetPack 4.x) ima Ubuntu 18.04 i Python 3.6; Pi ima noviji OS.
- **Odluka:** edge servis cilja Python ≥ 3.8 i radi na oba (CI testira 3.8); preporuka Pi (Docker ili nativno). Jetson kao rezerva ili za kasniji neuronski detektor (GPU).
- **Posljedice:** na Jetsonu koristiti Docker image ili `python3.8` iz apt-a.

### D-005 Dvije ESP32 pločice
- **Odluka:** jedan ESP32 za 6 senzora + LED traku, drugi za 2 rampe (servo, IR, LED, tipke). Pinovi su u `config.h` oba projekta i u shemi spajanja osobe 2.

### D-006 HC-SR04 iznad mjesta, gleda prema dolje
- **Kontekst:** vodoravno postavljen ultrazvučni senzor u maloj maketi hvata jeke od zidova.
- **Odluka:** senzor na "mostu" ~11 cm iznad poda: prazno ≈ 14 cm, auto ≈ 6–7 cm. Prag s histerezom, medijan 5, potvrda 3x.

### D-007 Kamera: varijanta A (dvije kamere) ili B (jedna premještana)
- **Kontekst:** jedna kamera ne vidi obje prednje pločice, a ruka rampe može zakloniti pogled.
- **Odluka:** kamera na mostu iznad trake, 200 mm iza crte rampe, 130 mm visoko, ruka rampe na 50–58 mm (provjereno kalkulatorom). Za početak jedna kamera koja se premješta između dva fiksna nosača; druga kamera (~20 €) ako budžet dopušta.
- **Posljedice:** `edge.yaml` → `gates.*.camera`; vidi `PROJEKT/maketa/nacrt-makete.md`.

### D-008 Pločice: tiskane, 60 mm, poznati font
- **Odluka:** sve pločice generira `SOFTWARE/alpr/tools/generate_plates.py` (izmišljene, HR format, 60 × 12,7 mm). OCR ima dva motora: Tesseract (opći) i usporedbu s predlošcima istog fonta (vrlo pouzdan za naše pločice); rezultati glasaju.
- **Posljedice:** pločice tiskane drugim fontom smanjit će pouzdanost – ne mijenjati font bez ponovnog mjerenja.

### D-009 Pravila odluke i naplate
- Pragovi 0.85 / 0.60, 3 pokušaja. Naplata: prvih 15 min besplatno, 1,50 € po započetom satu, najviše 15 € po danu. Demo profil: 1 minuta = 1 sat (da se u demonstraciji vidi cijena).

### D-010 SQLite za sesije
- **Odluka:** SQLite datoteka na edge računalu (bez servera), WAL način; ThingsBoard dobiva samo događaje.

### D-011 Vrijeme
- UTC ISO 8601 svugdje; ESP32 bez NTP-a šalje `timestamp: null`, primatelj koristi vrijeme primitka. Za demo bez interneta: NTP poslužitelj (chrony) na edge računalu → `NTP_SERVER` u `secrets.h`.
