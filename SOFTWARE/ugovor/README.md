# garage_contract – komunikacijski ugovor kao Python paket

```bash
pip install -e SOFTWARE/ugovor
```

| modul | sadržaj |
|---|---|
| `topics.py` | sve MQTT teme i pomoćne funkcije (`topics.gate_command("entrance")`) |
| `schemas/*.schema.json` | JSON Schema (draft-07) za svaku poruku – izvor istine |
| `validation.py` | `validate("spot_telemetry", payload)`, `message_type_for_topic(topic)` |
| `mqtt.py` | `MqttConnection`: paho 1.x i 2.x, automatsko ponovno spajanje, Last Will, heartbeat, JSON |
| `timeutil.py` | UTC ISO 8601 (`utc_now_iso()`, `parse_iso()`), radi i na Pythonu 3.8 |
| `config.py` | `MqttSettings.from_env()` (`MQTT_HOST`, `MQTT_PORT`, ...), `GarageConfig` (broj mjesta) |
| `monitor.py` | `python -m garage_contract.monitor` – prikazuje sve poruke i označava kršenja ugovora |

Primjeri svih poruka su u [examples/](examples); `pytest tests` provjerava da svaki primjer odgovara shemi.
Ne-Python strane (ESP32 firmware) koriste iste nazive polja – sheme su čitljive i ljudima.
