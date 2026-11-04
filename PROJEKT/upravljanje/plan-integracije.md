# Plan integracije

Hardver se spaja dio po dio, jedan novi dio odjednom. Ono što još ne postoji zamjenjuje simulator ili laptop, pa se
svaki korak može isprobati i bez hardvera (stupac "bez hardvera"). Sljedeći korak počinje tek kad prethodni prođe
kriterij uspjeha. Rezultat upisuje Lovro u [testni zapisnik](../testiranje/testni-zapisnik.md): datum, tko,
prošlo ili palo, napomena.

Naredbe se pokreću iz mape `SOFTWARE` s aktiviranim `.venv` ([INSTALL.md](../../SOFTWARE/INSTALL.md)).

## Prije prvog koraka

- U jednom terminalu stalno radi monitor ugovora: `python -m garage_contract.monitor`. Crveno označi svaku poruku
  koja krši ugovor.
- Prije svakog spajanja na ESP32 isključi napajanje i dvaput provjeri žice prema
  [shemi spajanja](../maketa/shema-spajanja.md).
- Dok Raspberry Pi nije spreman, broker može biti laptop. ESP32 tada u `MQTT_HOST` ima adresu laptopa. Mosquitto po
  zadanom prima samo lokalne veze, pa napravi datoteku `lan.conf`:

  ```
  listener 1883
  allow_anonymous true
  ```

  i pokreni `mosquitto -c lan.conf -v`. Na Windowsu prvo zaustavi servis (`net stop mosquitto` u terminalu
  pokrenutom kao administrator) i u vatrozidu dopusti pristup na privatnoj mreži.

## Pregled

| korak | što | tko | rok | bez hardvera |
|---|---|---|---|---|
| H0 | napajanje bez elektronike | Patrik, Lovro | prije prvog spajanja | |
| H1 | jedan ultrazvučni senzor | Toma | KT2 | |
| H2 | senzori na MQTT-u | Toma | KT2 | `python senzori/simulator/spot_simulator.py` |
| H3 | svih 6 senzora, kalibracija i test 20× | Toma, Lovro, Patrik | KT5 | |
| H4 | senzori u ThingsBoardu | Anja | KT2 | simulator senzora + ThingsBoard + `python -m tb_bridge` |
| H5 | jedan servo | Luka | KT2 | |
| H6 | obje rampe: IR, LED, tipke, sigurnosni testovi | Luka, Patrik | KT5 | |
| H7 | rampe na MQTT-u | Luka | KT5 | `python rampe/simulator/gate_simulator.py` |
| H8 | kamera, detekcija i OCR | Sven, Lukas, Patrik | KT2 prva fotografija, KT5 ≥ 90 % | `python -m edge_service read <slike>` na sintetskim slikama |
| H9 | cijeli ulaz na edge računalu | Lukas, Luka | KT6 | `python integracija/simulacija.py --broker` |
| H10 | izlaz i ThingsBoard | svi | KT6 | `python integracija/simulacija.py --broker --tb` |
| H11 | testovi otpornosti i proba demonstracije | svi | KT7 | `pytest integracija/tests -v` (isto vrti CI) |

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

## H2. Senzori na MQTT-u

1. U `secrets.h` upiši Wi-Fi i `MQTT_HOST` (laptop s `lan.conf` ili Pi) pa ponovno učitaj firmware.
2. Serijski `status` mora javiti `WiFi=1 MQTT=1`.
3. U monitoru su poruke `garage/parking/spot/P01/telemetry` zelene.
4. Serijski `sim 3 1` simulira zauzeto P03, `sim off` vraća mjerenje.

Uspjeh: poruke svih 6 mjesta su zelene, promjena stanja stiže za manje od 1 s.

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
4. Test prihvaćanja preko MQTT-a:
   ```bash
   MQTT_HOST=192.168.1.10 python senzori/tools/provjera_20x.py --all --cycles 20 --out testni-zapis-senzori.md
   ```
   U Windows PowerShellu adresu brokera postavi prije naredbe: `$env:MQTT_HOST="192.168.1.10"`.

Uspjeh (TC-S02): 20/20 ciklusa i točno 40 promjena po mjestu. Svaka dodatna promjena je treperenje.

## H4. Senzori u ThingsBoardu

1. ThingsBoard radi na laptopu ([INSTALL.md §4](../../SOFTWARE/INSTALL.md#4-thingsboard-laptop-ili-server-s--4-gb-ram)).
2. Bridge na Piju pokreće Docker. Dok Pija nema, pokreni ga na laptopu: `python -m tb_bridge` (zadano je
   `MQTT_HOST=localhost`, `TB_HOST=localhost`, `TB_MQTT_PORT=1884`).
3. Stavi i makni autić na jednom mjestu i izmjeri vrijeme štopericom.

Uspjeh (TC-T01): tlocrt na dashboardu promijeni boju za manje od 3 s.

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

## H7. Rampe na MQTT-u

1. U `secrets.h` upiši Wi-Fi i `MQTT_HOST`, ponovno učitaj firmware. Monitor prikazuje zelene
   `garage/gate/entrance/state`.
2. Pošalji naredbu s laptopa, bez edge servisa:
   ```bash
   python -m garage_contract.monitor --pub garage/gate/entrance/command '{"requestId":"t1","command":"OPEN"}'
   ```
   Na Windowsu ovu naredbu pokreni u Git Bashu (dolazi s gitom), jer PowerShell iz nje miče navodnike. Kad edge
   servis radi, isto napravi `python -m edge_service manual open --gate entrance`.

Uspjeh: stanja `OPENING → OPEN → CLOSING → CLOSED` i potvrda s istim `requestId` za manje od 1 s.

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

## H9. Cijeli ulaz na edge računalu

1. Pi radi s kamerom ([INSTALL.md §6](../../SOFTWARE/INSTALL.md#6-edge-računalo-raspberry-pi-ili-jetson-nano)), a
   oba ESP32 koriste Pi kao broker.
2. Autić dođe na ulaz i stane na graničnik.
3. U monitoru redom: `gate/entrance/state` (vozilo prisutno), `alpr/entrance/event` (registracija i pouzdanost),
   `access/decision GRANTED`, `gate/entrance/command OPEN`. Rampa se otvara.
4. Sesija u bazi, na Piju u mapi `edge/deploy`:
   ```bash
   docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml exec edge parking-sessions --db /data/garage.db list --active
   ```

Uspjeh (TC-I01): od zaustavljanja do otvaranja prođe manje od 3 s, sesija je `ACTIVE` s vremenom ulaska, a rampa se
otvara samo nakon `GRANTED`.

## H10. Izlaz i ThingsBoard

1. Autić s P03 vozi na izlaz. Stiže `SESSION_CLOSED` s trajanjem i cijenom i rampa se otvara.
2. Na nadzornom dashboardu su odluke, sesije i alarmi, a na analitičkom ulazak i trajanje.
3. Gumbi: "Otvori ulaz" i "Ručno odobri ulaz". Za drugi prekrij pločicu: `MANUAL_REQUIRED` → gumb → `GRANTED`.

Uspjeh: cijeli [demo scenarij](../../PREZENTACIJA/demo-scenarij.md) (koraci 1–13) prolazi bez zastoja.

## H11. Testovi otpornosti i proba demonstracije

Na maketi, iz [testnog plana](../testiranje/testni-plan.md):

| test | kako | očekivano |
|---|---|---|
| TC-I08 ThingsBoard ne radi | na laptopu `docker compose stop thingsboard`, autić uđe, zatim `start` | ulaz radi; događaji se pojave s izvornim vremenom |
| TC-I09 restart ESP32 | tipka EN/RST na oba ESP32 | za manje od 30 s sve radi |
| TC-I10 restart Pija | `sudo reboot` | servisi se sami pokrenu, aktivne sesije ostaju |
| TC-I14 nema Wi-Fi-ja | ugasi router na 1 min | tipka na rampi radi; nakon povratka stanja su točna |
| TC-S04 senzor ne radi | odspoji ECHO jednog senzora | mjesto `UNKNOWN`, ne broji se kao slobodno, alarm |
| TC-I04 puna garaža | autić na svako mjesto, sedmi na ulaz | `DENIED GARAGE_FULL` |

Zatim dvije generalne probe po [demo scenariju](../../PREZENTACIJA/demo-scenarij.md) i snimanje rezervnog videa do
KT7 (17.1.2027.).
