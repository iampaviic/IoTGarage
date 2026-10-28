# Popis rizika

Vjerojatnost (V) i utjecaj (U): 1 = nizak, 3 = visok. Prioritet = V × U. Pregled na svakom tjednom sastanku.

| ID | rizik | V | U | P | mjera | vlasnik | status |
|---|---|---|---|---|---|---|---|
| R-01 | OCR nepouzdan na stvarnim fotografijama makete (odsjaj, mutno, kut) | 2 | 3 | 6 | kontrolirano osvjetljenje, mat papir, graničnik kotača, kalkulator kamere; dvostruki OCR (predlošci + Tesseract); rano mjerenje na stvarnim slikama (tj. 1–2) | 5, 6 | otvoren |
| R-02 | Kamera ne može izoštriti na maloj udaljenosti | 2 | 3 | 6 | provjeriti minimalni fokus kamere u 1. tjednu; udaljenost ≥ 20 cm; po potrebi kamera s autofokusom | 2, 5 | otvoren |
| R-03 | Ruka rampe zaklanja pločicu | 2 | 2 | 4 | geometrija iz `kamera_kalkulator.py`; ruka na 50–58 mm | 2, 4 | otvoren |
| R-04 | HC-SR04 jeke u maloj maketi / nestabilna mjerenja | 2 | 2 | 4 | senzor iznad mjesta, kalibracija (`kalibracija.py`), filtar; rezerva: IR ili ToF senzor | 3 | otvoren |
| R-05 | 5 V ECHO uništi ESP32 ulaz | 2 | 3 | 6 | djelitelj 1k/2k na svakom ECHO; provjera multimetrom prije spajanja | 2, 3 | otvoren |
| R-06 | Servo resetira ESP32 (pad napona) | 2 | 2 | 4 | servo iz zasebnog 5 V napajanja, zajednička masa, 470–1000 µF kondenzator | 2, 4 | otvoren |
| R-07 | Wi-Fi na fakultetu (portal, izolacija klijenata) blokira ESP32 | 3 | 3 | 9 | vlastiti router / hotspot za maketu; Raspberry Pi kao pristupna točka | 1, 2 | otvoren |
| R-08 | ThingsBoard pretežak za Raspberry Pi | 2 | 2 | 4 | ThingsBoard na laptopu; edge samo Mosquitto + servisi | 7 | riješen (D-001, arhitektura) |
| R-09 | Jetson Nano: star Python 3.6 | 3 | 1 | 3 | Raspberry Pi kao edge ili Docker; CI testira Python 3.8 | 6 | riješen (D-004) |
| R-10 | Integracija ostavljena za kraj | 2 | 3 | 6 | simulatori od 1. dana, tjedni integracijski korak, e2e test u CI-u | 1 | u tijeku |
| R-11 | Član tima nedostupan / kasni | 2 | 2 | 4 | svaki podsustav ima simulator i README; parovi za zamjenu (3↔4, 5↔6, 7↔8) | 1 | otvoren |
| R-12 | Kvar na dan demonstracije | 2 | 3 | 6 | rezervni video, rezervni ESP32 i kabeli, `simulacija.py` kao plan B, kontrolna lista | 1 | otvoren |
| R-13 | Stvarne registracije u repozitoriju / izvještaju | 1 | 3 | 3 | samo generirane pločice, `.gitignore` za `dataset/real`, pregled PR-ova | 5, 8 | otvoren |
| R-14 | NTP nije dostupan bez interneta → vrijeme ESP32 nepoznato | 2 | 1 | 2 | ESP32 šalje `null`, edge koristi vrijeme primitka; chrony na edge računalu | 3, 4 | riješen (D-011) |
| R-15 | Mobilna aplikacija odvlači vrijeme od glavnog sustava ili ne bude gotova | 2 | 1 | 2 | aplikacija samo čita ThingsBoard (REST API), garaža ne ovisi o njoj; MVP do KT5, nakon KT6 samo popravci; analitički dashboard kao rezerva | 7 (Leo) | otvoren |
| R-16 | Blagdani, kolokviji i ispiti (prosinac – siječanj) smanjuju vrijeme za rad | 3 | 2 | 6 | integracija s hardverom radi se prije blagdana i zaključuje do KT5 (11.1.); blagdanska stanka je rezerva; u siječnju samo testiranje i dokumentacija; termini nedostupnosti u planu projekta | 1 | otvoren |
