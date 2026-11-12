# IoT Garaža – upute za rad u repozitoriju

## Arhitektura: varijanta B

Projekt radi **varijantu B** (`PROJEKT/sustav/varijanta-b.md`, odluka D-012 u `PROJEKT/upravljanje/odluke.md`).
Sav novi rad (kod, testovi, dokumentacija, dijagrami) radi se za B:

- ESP32 senzora (`esp32-spots`), ESP32 rampi (`esp32-gates`) i ALPR servis (`alpr-service`) su gateway uređaji
  ThingsBoarda: MQTT s *access tokenom*, `v1/gateway/...` i `v1/devices/me/...`.
- Odluke, sesije, naplatu i alarme radi rule chain: `SOFTWARE/thingsboard/rulechain/scripts/*.tbel` →
  `python build_rule_chain.py` → `garaza.json` (generirano, komitati zajedno sa skriptama) → `provision.py`.
- Imena uređaja, ključevi i RPC metode: `PROJEKT/sustav/komunikacijski-ugovor.md`, `SOFTWARE/ugovor/garage_contract/tb.py`,
  `config.h` oba firmwarea. Promjena ugovora mijenja sve to u istom commitu.
- Varijanta A (Mosquitto, `edge_service` access control, `SOFTWARE/baza`, `tb_bridge`, `garage/...` teme,
  `PROJEKT/sustav/arhitektura.md`) je rezerva: ne proširivati, ne graditi novo na njoj; testovi moraju i dalje prolaziti.

## Provjera

Iz mape `SOFTWARE` (venv: `pip install -r requirements-dev.txt`):

- `pytest` – svi Python testovi (uključuje provjeru da je `garaza.json` u skladu sa skriptama)
- `pio test -e native -d senzori/firmware`, `pio run -e esp32dev -d senzori/firmware` (isto za `rampe/firmware`)
- rule chain, firmware protokol ili simulatori: `docker compose -f thingsboard/docker-compose.yml up -d`,
  `python thingsboard/provision/provision.py` (čeka da se ThingsBoard pokrene), zatim
  `TB_LIVE_TEST=1 pytest integracija/tests/test_varijanta_b.py` (isto radi CI job `varijanta-b`)
- Mermaid dijagrami u `.md` moraju se renderirati (GitLab ih prikazuje)

## Pravila

- Kod i komentari na engleskom, dokumentacija na hrvatskom, kratko.
- Firmware i Python simulator istog čvora šalju iste poruke (`senzori/simulator/spot_simulator_tb.py`,
  `rampe/simulator/gate_simulator_tb.py`); stroj stanja rampe ima C++ i Python blizanca s istim testovima.
- Registracije su izmišljene; ne komitati `secrets.h`, `edge.yaml`, `.env`, tokene za demonstraciju.
- Nova datoteka mora pripadati nekom pravilu u `.gitlab-tjedni/raspored.py`.
