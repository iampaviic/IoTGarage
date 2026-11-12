# OCR, obrada registracije i ALPR servis

Zaduženi: Lukas Davorija (OCR, ALPR servis) i Luka Oslić (pravila odluke). Zamjena za ALPR: Sven Matić.

U [varijanti B](../../PROJEKT/sustav/varijanta-b.md) ovaj servis samo čita registraciju: on je uređaj `alpr-service`
u ThingsBoardu i na RPC `readPlate` vrati registraciju i pouzdanost. O ulasku i izlasku odlučuje rule chain
ThingsBoarda. Lokalna kontrola pristupa (`access_control.py`, `decisions.py`, naredbe `all`, `access`, `manual`)
pripada varijanti A i ostaje kao rezerva.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [plate_ocr/preprocess.py](plate_ocr/preprocess.py) | priprema izreza: makne plavu EU traku, izbriše grb (inače se čita kao H/B/3/I), makne rub, polaritet, skaliranje |
| [plate_ocr/engines.py](plate_ocr/engines.py) | dva OCR motora: Tesseract (opći) i predlošci (usporedba sa znakovima istog fonta kojim tiskamo pločice) |
| [plate_ocr/normalize.py](plate_ocr/normalize.py) | normalizacija po formatu HR registracije: O↔0, I↔1, B↔8, S↔5, Z↔2, G↔6 ovisno o poziciji, uklanjanje smeća (grb, rub), popis oznaka gradova |
| [plate_ocr/reader.py](plate_ocr/reader.py) | glasanje svih motora × varijanti → registracija + pouzdanost + razina (`ACCEPT/RETRY/MANUAL`) |
| [edge_service/tb_alpr.py](edge_service/tb_alpr.py) | **varijanta B**: ALPR kao gateway `alpr-service` u ThingsBoardu, RPC `readPlate` → do 3 slike → odgovor + telemetrija `ALPR-Entrance` / `ALPR-Exit` |
| [edge_service/alpr_service.py](edge_service/alpr_service.py) | čitanje: kamera / sintetska kamera / mapa slika → detekcija (`plate_detector`) → OCR → najbolji rezultat |
| [edge_service/__main__.py](edge_service/__main__.py) | naredbe: `tb-alpr` (B), `read` (offline); `all`, `access`, `alpr`, `manual` (A) |
| [edge_service/decisions.py](edge_service/decisions.py), [access_control.py](edge_service/access_control.py) | varijanta A: pravila odluke i lokalna kontrola pristupa (u B ih zamjenjuje rule chain) |
| [edge.example.yaml](edge.example.yaml) | konfiguracija s objašnjenjima (sekcija `thingsboard`: host, port, token) |
| [deploy/](deploy) | Docker (`docker-compose.alpr.yml` za B), nativna instalacija, systemd (`garage-alpr.service`) |
| [tools/evaluate_ocr.py](tools/evaluate_ocr.py) | tablica točnosti OCR-a s brojem pogrešno prihvaćenih čitanja (mora biti 0) |
| [rezultati/](rezultati) | izvještaji na sintetskim skupovima |
| [tests/](tests) | normalizacija, OCR, ALPR kao uređaj ThingsBoarda (`test_tb_alpr.py`); pravila odluke i access control (A) |

## Kako se računa pouzdanost

Svaki motor čita više varijanti slike, a čitanja glasaju s težinom motora i kvalitete čitanja. Pouzdanost je udio
glasova pobjednika u ukupnoj težini svih čitanja, pa se registracija prihvaća samo kad se gotovo sva čitanja slažu.
Usporedba motora je u [rezultati/](rezultati). Na stvarnim fotografijama izmjeri ponovno (`evaluate_ocr.py`) i po
potrebi promijeni težine u `OcrConfig`.

Pragovi i pravila odluke su u [komunikacijskom ugovoru](../../PROJEKT/sustav/komunikacijski-ugovor.md#pravila-odlučivanja).

## Brzi start (laptop)

```bash
python -m edge_service read ../alpr/dataset/synthetic/controlled/images/00*.jpg   # offline čitanje
python tools/evaluate_ocr.py ../alpr/dataset/synthetic/controlled                 # tablica točnosti
cp edge.example.yaml edge.yaml                      # kamera, pragovi, sekcija thingsboard (host, token)
python -m edge_service --config edge.yaml tb-alpr   # treba ThingsBoard; ALPR_SOURCE=sim za rad bez kamere
pytest tests
```

Ručne radnje operatera su gumbi na nadzornom dashboardu („Ručno odobri ulaz“, „Odbij“, „Otvori izlaz“).

Postavljanje uz kameru (laptop, Raspberry Pi ili Jetson Nano, Docker ili nativno):
[INSTALL.md §6](../INSTALL.md#6-alpr-servis-laptop-raspberry-pi-ili-jetson-nano-uz-kameru).

## Zadaci

- ✅ OCR modul `plate_ocr` i ALPR servis
- ✅ prijelaz na varijantu B: ALPR kao uređaj ThingsBoarda (`tb-alpr`), isproban s ThingsBoardom na sintetskim slikama
- ✅ (varijanta A) lokalni access control, sesije i allow-lista s testovima
- ✅ tablica točnosti OCR-a na sintetskom skupu · ⬜ na stvarnom skupu
- ⬜ `read` i `evaluate_ocr.py` na prvim stvarnim fotografijama
- ⬜ sa Svenom skup stvarnih slika i tablica točnosti, 0 pogrešno prihvaćenih
- ⬜ po potrebi podesiti težine, pragove i varijante (`OcrConfig`) i ponoviti mjerenje
- ⬜ ALPR uz kameru (laptop ili Raspberry Pi), kamera i token `alpr-service` u `edge.yaml`
- ⬜ izmjeriti vrijeme od `vehicleArrived` do odgovora `readPlate` (cilj: rampa otvorena za < 3 s)
- ⬜ s timom dogovoriti `policy: open` ili `allowlist` (atributi `policy` i `allowlist` asseta Garage)
- ⬜ koraci H8–H10 iz [plana integracije](../../PROJEKT/upravljanje/plan-integracije.md) s pravim hardverom
