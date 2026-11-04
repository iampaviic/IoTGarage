# OCR, obrada registracije i edge servis

Zaduženi: Lukas Davorija (OCR, ALPR servis, edge računalo) i Luka Oslić (pravila odluke i access control,
`edge_service/decisions.py` i `edge_service/access_control.py`). Zamjena za ALPR: Sven Matić.

Ovaj servis čita i provjerava registraciju te lokalno odlučuje o ulasku i izlasku. On je "mozak" edge računala.

## Što je već napravljeno

| | sadržaj |
|---|---|
| [plate_ocr/preprocess.py](plate_ocr/preprocess.py) | priprema izreza: makne plavu EU traku, izbriše grb (inače se čita kao H/B/3/I), makne rub, polaritet, skaliranje |
| [plate_ocr/engines.py](plate_ocr/engines.py) | dva OCR motora: Tesseract (opći) i predlošci (usporedba sa znakovima istog fonta kojim tiskamo pločice) |
| [plate_ocr/normalize.py](plate_ocr/normalize.py) | normalizacija po formatu HR registracije: O↔0, I↔1, B↔8, S↔5, Z↔2, G↔6 ovisno o poziciji, uklanjanje smeća (grb, rub), popis oznaka gradova |
| [plate_ocr/reader.py](plate_ocr/reader.py) | glasanje svih motora × varijanti → registracija + pouzdanost + razina (`ACCEPT/RETRY/MANUAL`) |
| [edge_service/decisions.py](edge_service/decisions.py) | čista pravila odluke; testirano je da se ispod praga rampa nikad ne otvara |
| [edge_service/access_control.py](edge_service/access_control.py) | access control: stanja mjesta i rampi, ALPR okidači, ponovni pokušaji, sesije, naredbe rampi s potvrdom i ponavljanjem, alarmi, ručne radnje |
| [edge_service/alpr_service.py](edge_service/alpr_service.py) | ALPR servis: kamera / sintetska kamera / mapa slika → detekcija (`plate_detector`) → OCR → `alpr/<gate>/event` |
| [edge_service/__main__.py](edge_service/__main__.py) | naredbe: `all`, `access`, `alpr`, `read` (offline), `manual` (operater) |
| [edge.example.yaml](edge.example.yaml) | konfiguracija s objašnjenjima |
| [deploy/](deploy) | Docker image i compose za Raspberry Pi/Jetson, nativna instalacija, systemd servisi |
| [tools/evaluate_ocr.py](tools/evaluate_ocr.py) | tablica točnosti OCR-a s brojem pogrešno prihvaćenih čitanja (mora biti 0) |
| [rezultati/](rezultati) | izvještaji na sintetskim skupovima |
| [tests/](tests) | normalizacija, OCR, pravila odluke i scenariji access controla; svaka poruka se provjerava prema ugovoru |

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
cp edge.example.yaml edge.yaml                  # prilagodi kameru, pragove
python -m edge_service --config edge.yaml all   # treba Mosquitto; ALPR_SOURCE=sim za rad bez kamere
pytest tests
```

Ručne radnje operatera (isto rade gumbi na ThingsBoard dashboardu, a svaka se bilježi u bazu):

```bash
python -m edge_service manual approve-entry --plate ZG1234AB --note "pločica prljava"
python -m edge_service manual approve-exit --plate ZG1234AB
python -m edge_service manual deny --gate entrance
python -m edge_service manual open --gate exit
```

Postavljanje na Raspberry Pi ili Jetson Nano (Docker ili nativno): [INSTALL.md §6](../INSTALL.md#6-edge-računalo-raspberry-pi-ili-jetson-nano).

## Zadaci

- ✅ OCR modul `plate_ocr` i lokalni edge servis `edge_service`
- ✅ baza dopuštenih registracija (tablica `allowed_plates` u [SOFTWARE/baza](../baza)) i CLI
- ✅ algoritam otvaranja i zatvaranja sesije (`access_control.py`) s testovima
- ✅ tablica točnosti OCR-a na sintetskom skupu · ⬜ na stvarnom skupu
- ⬜ `read` i `evaluate_ocr.py` na prvim stvarnim fotografijama
- ⬜ sa Svenom skup stvarnih slika i tablica točnosti, 0 pogrešno prihvaćenih
- ⬜ po potrebi podesiti težine, pragove i varijante (`OcrConfig`) i ponoviti mjerenje
- ⬜ edge na Raspberry Pi (Docker ili nativno), kamera u `edge.yaml`
- ⬜ s timom dogovoriti `policy: open` ili `allowlist` (`parking-sessions allow add ZG1234AB --label "Testno vozilo 1"`)
- ⬜ koraci H8–H10 iz [plana integracije](../../PROJEKT/upravljanje/plan-integracije.md) s pravim hardverom
