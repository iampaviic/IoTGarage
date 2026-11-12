# 6. Privatnost i sigurnost

Registarske oznake, slike vozila i vremena ulaska/izlaska mogu se povezati s osobama (osobni podaci prema
GDPR-u). Iako maketa ne obrađuje stvarne osobe, sustav je napravljen prema načelima zaštite podataka
(smjernice EDPB-a za povezana vozila – obrada slika uz kameru; AZOP – svrha, zaštita, označavanje videonadzora).

| načelo | provedba u sustavu |
|---|---|
| minimizacija | slike se obrađuju u memoriji i ne spremaju; opcionalno samo izrez pločice (`privacy.save_crops`) |
| lokalna obrada slika | ALPR na računalu uz kameru; u ThingsBoard idu samo rezultati (registracija, pouzdanost), nikad slike |
| ograničeno čuvanje | ThingsBoard TTL 30 dana za telemetriju (`SQL_TTL_TS_TS_KEY_VALUE_TTL`); aktivne sesije samo dok je vozilo unutra; izrezi pločica brišu se nakon `retention_days` |
| izmišljeni podaci | sve pločice generira `generate_plates.py`; stvarne registracije zabranjene u repozitoriju i izvještaju |
| ograničen pristup | ThingsBoard s promijenjenom lozinkom; tajni *access tokeni* uređaja (`esp32-spots`, `esp32-gates`, `alpr-service`); bez tokena se nitko ne može spojiti |
| sljedivost | svaka odluka i ručna radnja je telemetrija asseta Garage (`decisionManual`), a ThingsBoard bilježi korisnika u *Audit logs* |
| označavanje | na maketi natpis "Prostor pod videonadzorom" kao u stvarnoj garaži |

## Sigurnosne mjere (za demonstraciju)
- ESP32: Wi-Fi lozinka i *access token* samo u `secrets.h` (ne komita se)
- ThingsBoard: promijeniti `tenant@thingsboard.org` lozinku, tajni tokeni (`TB_TOKEN_SPOTS`, `TB_TOKEN_GATES`,
  `TB_TOKEN_ALPR` pri `provision.py`)
- Wi-Fi: zasebna mreža za maketu (WPA2)
- Fizička sigurnost rampe: ne zatvara se na vozilo, nakon 3 sigurnosna otvaranja ide u ERROR (ostaje gore)
