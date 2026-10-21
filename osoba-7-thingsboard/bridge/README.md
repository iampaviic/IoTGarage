# tb_bridge – Mosquitto → ThingsBoard

```bash
pip install -e osoba-7-thingsboard/bridge
MQTT_HOST=localhost TB_HOST=192.168.1.20 TB_MQTT_PORT=1884 TB_GATEWAY_TOKEN=... python -m tb_bridge
```

- sluša `garage/#` (bez `garage/sim/#`), pretvara poruke u telemetriju uređaja (`mapping.py`)
- svaki zapis prvo ide u SQLite red (`--buffer`, zadano `data/tb-buffer.db`) i briše se tek nakon potvrde
  ThingsBoarda (QoS 1) → ništa se ne gubi dok ThingsBoard ili mreža ne rade; vremena ostaju izvorna
- RPC s dashboarda → `garage/access/manual` (access control izvršava i bilježi)
