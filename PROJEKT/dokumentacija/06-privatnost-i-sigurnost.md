# 6. Privatnost i sigurnost

Registarske oznake, slike vozila i vremena ulaska/izlaska mogu se povezati s osobama (osobni podaci prema
GDPR-u). Iako maketa ne obrađuje stvarne osobe, sustav je napravljen prema načelima zaštite podataka
(smjernice EDPB-a za povezana vozila – lokalna obrada; AZOP – svrha, zaštita, označavanje videonadzora).

| načelo | provedba u sustavu |
|---|---|
| minimizacija | slike se obrađuju u memoriji i ne spremaju; opcionalno samo izrez pločice (`privacy.save_crops`) |
| lokalna obrada | ALPR i odluke na edge računalu; u ThingsBoard idu samo rezultati (registracija, odluka) |
| ograničeno čuvanje | `parking-sessions purge --days 30`; izrezi pločica brišu se nakon `retention_days`; ThingsBoard TTL 30 dana (`SQL_TTL_TS_TS_KEY_VALUE_TTL`) |
| izmišljeni podaci | sve pločice generira `generate_plates.py`; stvarne registracije zabranjene u repozitoriju i izvještaju |
| ograničen pristup | baza samo na edge računalu; ThingsBoard s promijenjenom lozinkom; token gatewaya tajan; Mosquitto s lozinkom za demo |
| sljedivost | svaka ručna radnja zapisuje operatera, vrijeme i razlog (`events` tablica) |
| označavanje | na maketi natpis "Prostor pod videonadzorom" kao u stvarnoj garaži |

## Sigurnosne mjere (za demonstraciju)
- Mosquitto: `allow_anonymous false` + `password_file` (upute u `SOFTWARE/integracija/mosquitto.conf`)
- ESP32: lozinke samo u `secrets.h` (ne komita se)
- ThingsBoard: promijeniti `tenant@thingsboard.org` lozinku, tajni `TB_GATEWAY_TOKEN`
- Wi-Fi: zasebna mreža za maketu (WPA2)
- Fizička sigurnost rampe: ne zatvara se na vozilo, nakon 3 sigurnosna otvaranja ide u ERROR (ostaje gore)
