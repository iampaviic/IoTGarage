# Dnevnik odluka

Kratki zapisi odluka koje utječu na više članova (format: kontekst → odluka → posljedice).
Odluke označene **[PRIJEDLOG]** pripremljene su unaprijed – potvrdite ih ili promijenite na prvom sastanku.

### D-001 Lokalni MQTT broker (Mosquitto) na edge računalu — zamijenjeno s D-012
- **Kontekst:** ThingsBoard ima vlastiti MQTT, ali s fiksnim temama i autentikacijom po uređaju; generička MQTT integracija postoji samo u PE/Cloud izdanju.
- **Odluka:** svi uređaji i servisi razgovaraju preko Mosquitta na edge računalu; prema ThingsBoardu ide samo bridge kao *gateway uređaj* (Gateway MQTT API, radi u CE).
- **Posljedice:** ulaz/izlaz rade bez ThingsBoarda; bridge mora imati međuspremnik (napravljeno: SQLite buffer).

### D-002 ID mjesta `P01` i u temi i u poruci
- **Kontekst:** prijedlog je imao `spot/01/telemetry` i `"spotId": "P01"` – dvije oznake za isto.
- **Odluka:** `garage/parking/spot/P01/telemetry`.
- **Posljedice:** ThingsBoard uređaj se zove `ParkingSpot-01` (u varijanti B tako ga imenuje sam ESP32 senzora).

### D-003 Ugovor kao JSON Schema + Python paket (varijanta A; za B vidi D-012)
- **Odluka:** teme i sheme su kod (`SOFTWARE/ugovor/garage_contract`), dokument ih opisuje. Svaki test, simulator i servis provjerava poruke.
- **Posljedice:** promjena ugovora = promjena sheme + primjera u jednom PR-u (CI).

### D-004 [PRIJEDLOG] Raspberry Pi kao edge računalo, Jetson Nano kao rezerva (u varijanti B samo za ALPR)
- **Kontekst:** imamo Raspberry Pi, Jetson Nano i jednu USB kameru. Jetson Nano (JetPack 4.x) ima Ubuntu 18.04 i Python 3.6; Pi ima noviji OS.
- **Odluka:** edge servis cilja Python ≥ 3.8 i radi na oba (CI testira 3.8); preporuka Pi (Docker ili nativno). Jetson kao rezerva ili za kasniji neuronski detektor (GPU).
- **Posljedice:** na Jetsonu koristiti Docker image ili `python3.8` iz apt-a.

### D-005 Dvije ESP32 pločice
- **Odluka:** jedan ESP32 za 6 senzora + LED traku, drugi za 2 rampe (servo, IR, LED, tipke). Pinovi su u `config.h` oba projekta i u shemi spajanja.

### D-006 HC-SR04 iznad mjesta, gleda prema dolje
- **Kontekst:** vodoravno postavljen ultrazvučni senzor u maloj maketi hvata jeke od zidova.
- **Odluka:** senzor na "mostu" ~11 cm iznad poda: prazno ≈ 14 cm, auto ≈ 6–7 cm. Prag s histerezom, medijan 5, potvrda 3x.

### D-007 Kamera: dvije kamere ili jedna premještana
- **Kontekst:** jedna kamera ne vidi obje prednje pločice, a ruka rampe može zakloniti pogled.
- **Odluka:** kamera na mostu iznad trake, 200 mm iza crte rampe, 130 mm visoko, ruka rampe na 50–58 mm (provjereno kalkulatorom). Za početak jedna kamera koja se premješta između dva fiksna nosača; druga kamera (~20 €) ako budžet dopušta.
- **Posljedice:** `edge.yaml` → `gates.*.camera`; vidi `PROJEKT/maketa/nacrt-makete.md`.

### D-008 Pločice: tiskane, 60 mm, poznati font
- **Odluka:** sve pločice generira `SOFTWARE/alpr/tools/generate_plates.py` (izmišljene, HR format, 60 × 12,7 mm). OCR ima dva motora: Tesseract (opći) i usporedbu s predlošcima istog fonta (vrlo pouzdan za naše pločice); rezultati glasaju.
- **Posljedice:** pločice tiskane drugim fontom smanjit će pouzdanost – ne mijenjati font bez ponovnog mjerenja.

### D-009 Pravila odluke i naplate
- Pragovi 0.85 / 0.60 i 3 pokušaja ([komunikacijski ugovor](../sustav/komunikacijski-ugovor.md#pravila-odlučivanja)).
  U varijanti B ponovne pokušaje radi ALPR servis (do 3 slike), a rule chain sve ispod 0.85 šalje operateru. Naplata i demo profil (1 minuta = 1 sat): [model-podataka.md](../sustav/model-podataka.md#pravilo-naplate).

### D-010 SQLite za sesije — zamijenjeno s D-012
- **Odluka:** SQLite datoteka na edge računalu (bez servera), WAL način; ThingsBoard dobiva samo događaje.

### D-011 Vrijeme
- UTC ISO 8601 svugdje; ESP32 bez NTP-a šalje `timestamp: null`, primatelj koristi vrijeme primitka. Za demo bez interneta: NTP poslužitelj (chrony) na edge računalu → `NTP_SERVER` u `secrets.h`.
- Varijanta B: ESP32 ne šalje vrijeme, telemetriju označava ThingsBoard vremenom primitka (u ms), pa NTP na ESP32
  nije potreban.

### D-012 Varijanta B: sve odluke i podaci u ThingsBoardu
- **Kontekst:** varijanta A (D-001, D-010) traži Mosquitto, access control, SQLite i bridge na edge računalu.
  Varijanta B je jednostavnija za postaviti i demonstrirati, a ThingsBoard je ionako dio sustava.
- **Odluka:** tim radi varijantu B ([varijanta-b.md](../sustav/varijanta-b.md)). Oba ESP32 i ALPR servis su
  *gateway* uređaji ThingsBoarda (`esp32-spots`, `esp32-gates`, `alpr-service`, MQTT s *access tokenom*); odluke,
  sesije (atribut `sessions` asseta Garage), naplatu i alarme vodi rule chain iz `SOFTWARE/thingsboard/rulechain`.
- **Posljedice:**
  - bez ThingsBoarda ili mreže automatski ulaz i izlaz ne rade; rampe se otvaraju tipkom, a zatvaraju same
    (prihvaćeno, NFR-01 promijenjen);
  - ugovor su teme ThingsBoardovog API-ja uređaja i ključevi u [komunikacijskom ugovoru](../sustav/komunikacijski-ugovor.md)
    (verzija 2.0), a ne `garage/...` teme;
  - `SOFTWARE/edge/edge_service` (access control), `SOFTWARE/baza`, `tb_bridge` i Mosquitto ostaju u repozitoriju kao
    varijanta A (rezerva) i ne razvijaju se dalje;
  - pravila odluke i naplate postoje dvaput (Python u A, TBEL u B); mijenjaju se zajedno dok A postoji;
  - novi rad (firmware, dashboardi, testovi, dokumentacija) radi se samo za B.
