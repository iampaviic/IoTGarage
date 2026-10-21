# Plan integracije

Integracija ide **korak po korak čim dvije komponente postoje**, ne na kraju. Svaki korak ima naredbu
i kriterij prolaza. Dok pravi hardver ne postoji, zamjenjuje ga simulator – pa se svaki korak može
napraviti već u 1. tjednu, a kasnije ponoviti s hardverom.

Prije svega: `pip install -r requirements-dev.txt`, Mosquitto pokrenut, u drugom terminalu stalno
otvoren monitor ugovora:

```bash
python -m garage_contract.monitor          # crveno = netko krši ugovor
```

| # | korak | sa simulatorom | s hardverom | kriterij prolaza |
|---|---|---|---|---|
| 1 | senzor → MQTT | `python osoba-3-senzori/simulator/spot_simulator.py` | flash `osoba-3-senzori/firmware`, `secrets.h` | 6 poruka `spot/P0x/telemetry`, sve zelene u monitoru; promjena stanja < 1 s |
| 2 | MQTT → ThingsBoard | `python -m tb_bridge` + `docker compose up` u `osoba-7-thingsboard` | isto | tlocrt na dashboardu mijenja boju unutar 3 s |
| 3 | edge → rampa | `python osoba-4-rampe/simulator/gate_simulator.py` + `python -m edge_service manual open --gate entrance` | flash `osoba-4-rampe/firmware` | rampa `OPENING → OPEN → CLOSING → CLOSED`, odgovor s istim `requestId` < 1 s |
| 4 | kamera → detekcija | `python osoba-5-alpr/tools/detect_image.py <slika>` | `capture_dataset.py` | pločica uokvirena, `*_crop.png` ravna i čitljiva |
| 5 | detekcija → OCR | `python -m edge_service read <slike>` | isto na fotografijama makete | točna registracija, confidence ≥ 0.85 |
| 6 | OCR → odluka | `simulacija.py` (ALPR_SOURCE=sim) | `edge_service all` + kamera | `access/decision GRANTED` za poznatu, `MANUAL_REQUIRED` za nečitljivu |
| 7 | odluka → rampa | `simulacija.py` | sve + ESP32 rampi | rampa se otvara samo nakon `GRANTED` |
| 8 | ulazak → sesija | `parking-sessions --db <db> list --active` | isto | sesija `ACTIVE` s vremenom ulaska |
| 9 | izlazak → zatvaranje sesije | `simulacija.py` (korak 5 demo scenarija) | isto | `SESSION_CLOSED` s trajanjem i cijenom |
| 10 | svi događaji → ThingsBoard | `simulacija.py --tb` | isto | odluke, sesije, alarmi vidljivi na oba dashboarda |

Cijeli lanac automatski (koristi se i u CI-u):

```bash
python osoba-1-voditelj/integracija/simulacija.py --broker        # demo scenarij, ispis odluka i cijene
pytest osoba-1-voditelj/integracija/tests -v                      # end-to-end testovi
```

## Tjedni integracijski sastanak (30–45 min)

1. Status po osobi (2 min svaki): što radi, što blokira – predložak u [sastanci/predlozak.md](sastanci/predlozak.md).
2. Demo: zadnji korak integracije uživo (simulator ili hardver).
3. Promjene ugovora / odluke → [odluke.md](odluke.md).
4. Rizici → [rizici.md](rizici.md).
5. Zadaci za sljedeći tjedan (GitHub Projects / [plan-rada.md](plan-rada.md)).

## Pravila rada u repozitoriju

- `main` je uvijek ispravan: CI (testovi, firmware build, 3D modeli) mora biti zelen.
- Svatko radi u svojoj grani `osobaN/kratki-opis` i otvara Pull Request; pregledava barem jedna osoba.
- Promjena tuđeg foldera samo uz dogovor s vlasnikom; promjena ugovora samo preko osobe 1.
- Ne komitati: `secrets.h`, `edge.yaml`, baze (`*.db`), fotografije stvarnih vozila.
