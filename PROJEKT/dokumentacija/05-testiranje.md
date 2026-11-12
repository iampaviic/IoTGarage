# 5. Testiranje

## 5.1 Pristup
- automatski testovi na svakom PR-u (GitHub Actions): Python (Python 3.8 i 3.12), firmware build + unit testovi, 3D modeli
- simulacija cijelog sustava bez hardvera s pravim ThingsBoardom (`simulacija_b.py`, `test_varijanta_b.py`)
- testovi na maketi prema testnom planu (`testni-plan.md`), rezultati u `testni-zapisnik.md`

## 5.2 Rezultati
| područje | metrika | rezultat (sintetski / simulacija) | rezultat (maketa) |
|---|---|---|---|
| senzori | 20× po mjestu bez treperenja | filtar: 8/8 unit testova | |
| detekcija pločice | uspješnost (IoU ≥ 0,5) | 100 % kontrolirano, 95,3 % teško | |
| OCR | točno / pogrešno prihvaćeno | 91,3 % / 0 | |
| odluke | nikad otvaranje ispod praga | prolaz (sve kombinacije, `decide.tbel` u ThingsBoardu) | |
| sustav | scenariji faze 4 | vidi zapisnik | |
| ThingsBoard | kašnjenje, restart, gubitak veze uređaja | scenarij B (8 koraka) prolazi; restart provjeren | |

## 5.3 Uočeni problemi i rješenja
_(popuniti tijekom testiranja)_
