# Plan integracije

Hardver se spaja dio po dio, jedan novi dio odjednom. Ono što još ne postoji zamjenjuje simulator ili laptop, pa se
svaki korak može isprobati i bez hardvera (stupac "bez hardvera"). Sljedeći korak počinje tek kad prethodni prođe
kriterij uspjeha. Rezultat upisuje Lovro u [testni zapisnik](../testiranje/testni-zapisnik.md): datum, tko,
prošlo ili palo, napomena.

Naredbe se pokreću iz mape `SOFTWARE` s aktiviranim `.venv` ([INSTALL.md](../../SOFTWARE/INSTALL.md)). Plan je za
[varijantu B](../sustav/varijanta-b.md): ESP32 i ALPR spajaju se izravno na ThingsBoard na laptopu.

## Prije prvog koraka

- ThingsBoard radi na laptopu i pripremljen je s `provision.py`
  ([INSTALL.md §3](../../SOFTWARE/INSTALL.md#3-thingsboard-laptop-ili-server-s--4-gb-ram)); `provision.py` ispiše
  *access tokene* za `secrets.h`. ESP32 u `TB_HOST` ima IP laptopa. Na Windowsu u vatrozidu dopusti Dockeru pristup
  na privatnoj mreži (port 1883).
- Poruke se prate u ThingsBoardu: *Entities → Devices → uređaj → Latest telemetry*, a tok kroz rule chain uključivanjem
  *Debug* na čvoru (*Rule chains → Garaža (varijanta B) → čvor → Debug*, zatim kartica *Events*).
- Prije svakog spajanja na ESP32 isključi napajanje i dvaput provjeri žice prema
  [shemi spajanja](../maketa/shema-spajanja.md).

## Pregled

| korak | što | tko | rok | bez hardvera |
|---|---|---|---|---|
| H0 | napajanje bez elektronike | Patrik, Lovro | prije prvog spajanja | |
| H1 | jedan ultrazvučni senzor | Toma | KT2 | |
| H2 | senzori u ThingsBoardu (MQTT, token) | Toma | KT2 | `python senzori/simulator/spot_simulator_tb.py` |
| H3 | svih 6 senzora, kalibracija i test 20× | Toma, Lovro, Patrik | KT5 | |
| H4 | senzori na dashboardu, gubitak veze | Anja, Toma | KT2 | simulator senzora (`k` = prekid veze) + ThingsBoard |
| H5 | jedan servo | Luka | KT2 | |
| H6 | obje rampe: IR, LED, tipke, sigurnosni testovi | Luka, Patrik | KT5 | |
| H7 | rampe u ThingsBoardu (RPC) | Luka | KT5 | `python rampe/simulator/gate_simulator_tb.py` |
| H8 | kamera, detekcija i OCR | Sven, Lukas, Patrik | KT2 prva fotografija, KT5 ≥ 90 % | `python -m edge_service read <slike>` na sintetskim slikama |
| H9 | cijeli ulaz kroz rule chain | Lukas, Luka, Anja | KT6 | `python integracija/simulacija_b.py --alpr sim` |
| H10 | izlaz, ručno odobrenje i dashboardi | svi | KT6 | `python integracija/simulacija_b.py` |
| H11 | testovi otpornosti i proba demonstracije | svi | KT7 | `TB_LIVE_TEST=1 pytest integracija/tests/test_varijanta_b.py -v` |

## H0. Napajanje bez elektronike

Treba: adapter 5 V / 4 A, sklopka, WAGO spojnice, kondenzatori 1000 µF, multimetar.

1. Spoji adapter → sklopka → WAGO +5 V i WAGO GND ([shema](../maketa/shema-spajanja.md#napajanje-i-masa)).
2. Kondenzator 1000 µF stavi uz napajanje serva i uz LED traku. Duža nožica (+) ide na +5 V.
3. Uključi i izmjeri napon između +5 V i GND.

Uspjeh: 4,9–5,2 V. Raspberry Pi ima svoj USB-C adapter i ne spaja se na ovaj razvod.

## H1. Jedan ultrazvučni senzor

Treba: ESP32 senzora, jedan HC-SR04, otpornici 1 kΩ i 2 kΩ (ili 2 × 1 kΩ), protoboard.

1. Djelitelj za ECHO je obavezan, jer 5 V na ulazu uništi ESP32: ECHO → 1 kΩ → točka → 2 kΩ → GND. Točka ide na
   GPIO36 (mjesto P01).
2. Prije spajanja na ESP32 ulaz djelitelja spoji na +5 V i izmjeri izlaz. Mora biti 3,2–3,4 V.
3. HC-SR04: VCC na +5 V, GND na GND, TRIG na GPIO23. GND ESP32 spoji na zajednički GND.
4. Učitaj firmware ([INSTALL.md §5](../../SOFTWARE/INSTALL.md#5-firmware-za-esp32-čvor-senzora-i-čvor-rampi)) i u
   serijskom monitoru upiši `cal`. Stižu redci `CAL,P01,14.2`. Ostala mjesta javljaju grešku jer senzora još nema.
5. Stavi autić ispod senzora pa ga makni.

Uspjeh (TC-S01): prazno ~14 cm, s autićem ~6–7 cm, razlika veća od 4 cm.

## H2. Senzori u ThingsBoardu

1. U `secrets.h` upiši Wi-Fi, `TB_HOST` (IP laptopa) i `TB_TOKEN` uređaja `esp32-spots` pa ponovno učitaj firmware.
2. Serijski monitor javlja `ThingsBoard: connected`, a `status` `WiFi=1 ThingsBoard=1`. `rc=4` ili `rc=5` znači
   pogrešan token.
3. U ThingsBoardu `esp32-spots` je *Active*, a `ParkingSpot-01` … `06` imaju svježu telemetriju (`state`,
   `sensorStatus`); `esp32-spots` ima `freeSpots`, `occupiedSpots`, `unknownSpots`.
4. Serijski `sim 3 1` simulira zauzeto P03, `sim off` vraća mjerenje. Isto radi RPC `sim` na `esp32-spots`.

Uspjeh: svih 6 mjesta ima telemetriju, promjena stanja je u ThingsBoardu za manje od 1 s.

## H3. Svih 6 senzora, kalibracija i test 20×

1. Na most makete (113 mm iznad poda) montiraj 6 nosača sa senzorima, svaki s djeliteljem, i LED traku.
2. Kalibracija, s ESP32 spojenim USB-om na laptop:
   ```bash
   python senzori/tools/kalibracija.py --port COM5          # Linux: /dev/ttyUSB0; port piše u PlatformIO
   ```
   Prati upute (sva mjesta prazna, zatim autić redom na svako mjesto). Alat ispiše redke za `SPOTS[]` u
   `senzori/firmware/include/config.h` i tablicu za [tablica-pragova.md](../testiranje/tablica-pragova.md).
   "PROVJERITI montažu" znači da senzor nije okomit ili vidi zid.
3. Upiši pragove u `config.h` i ponovno učitaj firmware.
4. Test prihvaćanja, s ESP32 spojenim USB-om (alat čita promjene koje firmware ispisuje i šalje ThingsBoardu):
   ```bash
   python senzori/tools/provjera_20x.py --port COM5 --all --cycles 20 --out testni-zapis-senzori.md
   ```

Uspjeh (TC-S02): 20/20 ciklusa i točno 40 promjena po mjestu. Svaka dodatna promjena je treperenje.

## H4. Senzori na dashboardu, gubitak veze

1. Otvori nadzorni dashboard „Garaža - nadzor“.
2. Stavi i makni autić na jednom mjestu i izmjeri vrijeme štopericom.
3. Isključi napajanje ESP32 senzora. Unutar ≈ 45 s mjesta postanu siva (`UNKNOWN` / `OFFLINE`), broj slobodnih je 0,
   a u tablici alarma je „Uređaj nije dostupan“. Uključi ga natrag: stanja se vrate, alarm se ugasi.

Uspjeh (TC-T01, TC-I07): tlocrt promijeni boju za manje od 3 s; nestanak čvora nikad ne prikaže mjesta kao slobodna.

## H5. Jedan servo

Treba: ESP32 rampi, jedan SG90, kondenzator 1000 µF.

1. Servo se napaja s +5 V adaptera, nikad s ESP32. Smeđa žica je GND, crvena +5 V, narančasta (signal) ide na
   GPIO13. GND adaptera i GND ESP32 moraju biti spojeni.
2. Učitaj firmware rampi, u serijskom monitoru upiši `open e` pa `close e`.
3. Namjesti ruku na stup: zatvorena stoji ravno preko trake, otvorena je okrenuta uz otok. Ako kut ne odgovara,
   promijeni `closedAngle` i `openAngle` u `rampe/firmware/include/config.h` i ponovno učitaj firmware.

Uspjeh: ruka se glatko otvara i zatvara, a ESP32 se pritom ne resetira.

## H6. Obje rampe: IR, LED, tipke, sigurnosni testovi

1. Drugi servo ide na GPIO14, IR senzori FC-51 na GPIO34 i GPIO35. FC-51 se napaja s 3,3 V (pin 3V3 ESP32), ne s 5 V.
   LED-ice idu preko 220 Ω, tipke između GPIO i GND
   ([pinovi](../maketa/shema-spajanja.md#čvor-rampi-esp32-2-esp32-gates)).
2. IR postavi na crtu rampe s druge strane trake, na visini branika. Serijski `status` smije javiti `present=1`
   samo kad je autić na crti, a ruka rampe ga ne smije aktivirati. Osjetljivost se podešava potenciometrom na FC-51.
3. Tipka: kratki pritisak otvara rampu, držanje 3 s radi RESET.
4. Provedi [sigurnosne testove rampi](../testiranje/sigurnosni-testovi-rampi.md).

Uspjeh: svi sigurnosni testovi prolaze i upisani su u zapisnik.

## H7. Rampe u ThingsBoardu

1. U `secrets.h` upiši Wi-Fi, `TB_HOST` i `TB_TOKEN` uređaja `esp32-gates`, ponovno učitaj firmware. U ThingsBoardu
   `EntranceGate` i `ExitGate` imaju telemetriju `state`, `vehiclePresent`.
2. Na dashboardu pritisni „Otvori ulaz“ (RPC `open`). Gumb dobije odgovor rampe.
3. Autić na crtu ulazne rampe: `EntranceGate` dobije `vehicleArrived = true`. Dok ALPR ne radi, rule chain nakon 15 s
   javi `MANUAL_REQUIRED` (alarm „Potrebna ručna intervencija“), a „Ručno odobri ulaz“ otvori rampu.

Uspjeh: stanja `OPENING → OPEN → CLOSING → CLOSED` u ThingsBoardu, odgovor na RPC za manje od 1 s.

## H8. Kamera, detekcija i OCR

Prvo na laptopu, gdje se vidi slika, a tek onda na Piju.

1. Isprintaj pločice: `python alpr/tools/generate_plates.py --out tablice`. PDF ispiši na 100 % na mat papiru i
   ravnalom provjeri kontrolnu crtu od 50 mm. Pločice zalijepi u držače na autićima.
2. Fokus (rizik R-02): snimi pločicu s 20, 25 i 30 cm. Jeftine kamere s fiksnim fokusom su mutne ispod ~30 cm.
   Ako je slika mutna, povećaj udaljenost ili uzmi kameru s autofokusom.
3. Snimanje treba OpenCV s prozorima (jednom):
   ```bash
   pip uninstall -y opencv-python-headless && pip install -e "alpr[gui]"
   python alpr/tools/capture_dataset.py --out alpr/dataset/real/v1 --plate ZG1234AB --lighting svijetlo --angle 0 --distance blizu
   ```
   RAZMAK sprema sliku, `q` izlazi. Snimi prvih 10 slika s kamerom na stvarnom položaju.
4. Detekcija i čitanje:
   ```bash
   python alpr/tools/detect_image.py alpr/dataset/real/v1/<slika>.jpg --out alpr/rezultati/probe
   python -m edge_service read alpr/dataset/real/v1/*.jpg
   ```
5. Za KT5 Sven i Lukas snime ≥ 100 slika i izmjere ih (`label_tool.py`, `evaluate_detection.py`,
   `edge/tools/evaluate_ocr.py`).

Uspjeh: pločica je uokvirena, izrez ravan i čitljiv, registracija točna s pouzdanošću ≥ 0,85. Za KT5 detekcija
≥ 90 % i 0 pogrešno prihvaćenih čitanja.

## H9. Cijeli ulaz kroz rule chain

1. ALPR servis radi uz kameru, na laptopu ili Piju
   ([INSTALL.md §6](../../SOFTWARE/INSTALL.md#6-alpr-servis-laptop-raspberry-pi-ili-jetson-nano-uz-kameru)), a
   `alpr-service` je u ThingsBoardu *Active*.
2. Autić dođe na ulaz i stane na graničnik.
3. U ThingsBoardu redom: `EntranceGate` `vehicleArrived`, `ALPR-Entrance` `plate` i `ocrConfidence`, na assetu
   Garage `decision = GRANTED` i `sessionEvent = SESSION_OPENED`, zatim `EntranceGate` `OPENING`. Rampa se otvara.
4. Sesija je u atributu `sessions` asseta Garage (*Entities → Assets → Garage → Attributes*), a na dashboardu
   „Vozila u garaži“ poraste za 1.

Uspjeh (TC-I01): od zaustavljanja do otvaranja prođe manje od 3 s, sesija ima vrijeme ulaska, a rampa se otvara samo
nakon `GRANTED`.

## H10. Izlaz i ThingsBoard

1. Autić s P03 vozi na izlaz. Stiže `SESSION_CLOSED` s trajanjem i cijenom i rampa se otvara.
2. Na nadzornom dashboardu su odluke, sesije i alarmi, a na analitičkom ulazak i trajanje.
3. Gumbi: "Otvori ulaz" i "Ručno odobri ulaz". Za drugi prekrij pločicu: `MANUAL_REQUIRED` → upiši registraciju u
   „Registracija za ručno odobrenje“ → gumb → `GRANTED MANUAL_APPROVAL`.

Uspjeh: cijeli [demo scenarij](../../PREZENTACIJA/demo-scenarij.md) (koraci 1–13) prolazi bez zastoja.

## H11. Testovi otpornosti i proba demonstracije

Na maketi, iz [testnog plana](../testiranje/testni-plan.md):

| test | kako | očekivano |
|---|---|---|
| TC-I08 ThingsBoard ne radi | na laptopu `docker compose stop thingsboard`, autić na ulaz, tipka, zatim `start` | rampa se otvara samo tipkom i sama zatvara; nakon `start` uređaji se sami spoje, stanja i sesije su točni |
| TC-I09 restart ESP32 | tipka EN/RST na oba ESP32 | za manje od 30 s sve radi |
| TC-I10 restart ALPR računala | `sudo reboot` (ili ponovno pokreni `tb-alpr`) | servis se sam pokrene i spoji; aktivne sesije ostaju (u ThingsBoardu) |
| TC-I14 nema Wi-Fi-ja | ugasi router na 1 min | tipka na rampi radi; nakon povratka stanja su točna |
| TC-S04 senzor ne radi | odspoji ECHO jednog senzora | mjesto `UNKNOWN`, ne broji se kao slobodno, alarm |
| TC-I04 puna garaža | autić na svako mjesto, sedmi na ulaz | `DENIED GARAGE_FULL` |

Zatim dvije generalne probe po [demo scenariju](../../PREZENTACIJA/demo-scenarij.md) i snimanje rezervnog videa do
KT7 (17.1.2027.).
