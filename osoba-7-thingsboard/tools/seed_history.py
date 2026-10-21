"""Fill ThingsBoard with FICTIONAL history so the analytics dashboard can be developed.

    python seed_history.py --days 7                 # 7 days of generated sessions + occupancy
    python seed_history.py --clear                  # delete ALL history of these keys (before the real demo!)

Uses the session generator of osoba 8 (parking_sessions.generator) and sends
the data as the Garage-Edge gateway device directly to ThingsBoard's MQTT API.
The final demonstration must show REAL data: run --clear first, then drive
the cars through the model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from garage_contract.mqtt import new_paho_client
from parking_sessions.generator import generate_sessions

KEYS = ["entry", "exit", "durationMin", "price", "sessionPlate", "sessionEvent", "sessionId", "sessionEntryTime",
        "occupiedSpots", "freeSpots", "unknownSpots", "occupancyPct", "activeSessions", "totalSpots", "full"]


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def build_points(days: int, spots: int):
    end = datetime.now(timezone.utc) - timedelta(minutes=5)
    sessions = [s for s in generate_sessions(days=days, per_day=max(10, spots * 5), end=end, seed=7,
                                             active_at_end=0, spot_count=spots) if s.status == "CLOSED"]
    points = []
    events = []
    for s in sessions:
        points.append((ms(s.entry_time), {"entry": 1, "sessionEvent": "SESSION_OPENED", "sessionPlate": s.plate,
                                         "sessionId": s.id}))
        points.append((ms(s.exit_time), {"exit": 1, "sessionEvent": "SESSION_CLOSED", "sessionPlate": s.plate,
                                        "sessionId": s.id, "durationMin": round(s.duration_s / 60.0, 1),
                                        "price": s.price, "sessionEntryTime": s.entry_time.strftime("%Y-%m-%dT%H:%M:%SZ")}))
        events += [(s.entry_time, +1), (s.exit_time, -1)]
    # occupancy timeline: number of cars inside (capped at the number of spots)
    inside = 0
    for t, delta in sorted(events):
        inside += delta
        occ = max(0, min(spots, inside))
        points.append((ms(t), {"occupiedSpots": occ, "freeSpots": spots - occ, "unknownSpots": 0,
                               "occupancyPct": round(100.0 * occ / spots, 1), "activeSessions": max(0, inside),
                               "totalSpots": spots, "full": occ >= spots}))
    points.sort(key=lambda p: p[0])
    return points, len(sessions)


def seed(host: str, port: int, token: str, days: int, spots: int) -> None:
    points, n = build_points(days, spots)
    c = new_paho_client("seed-history-%d" % int(time.time()))
    c.username_pw_set(token)
    c.connect(host, port, 30)
    c.loop_start()
    batch = []
    for ts, values in points:
        batch.append({"ts": ts, "values": values})
        if len(batch) == 100:
            c.publish("v1/devices/me/telemetry", json.dumps(batch), qos=1).wait_for_publish(10)
            batch = []
    if batch:
        c.publish("v1/devices/me/telemetry", json.dumps(batch), qos=1).wait_for_publish(10)
    c.loop_stop()
    c.disconnect()
    print("sent %d points (%d fictional sessions over %d days) to Garage-Edge" % (len(points), n, days))


def clear(url: str, user: str, password: str) -> None:
    tok = requests.post(url + "/api/auth/login", json={"username": user, "password": password}, timeout=20).json()
    h = {"X-Authorization": "Bearer " + tok["token"]}
    dev = requests.get(url + "/api/tenant/devices", params={"deviceName": "Garage-Edge"}, headers=h, timeout=20).json()
    r = requests.delete(url + "/api/plugins/telemetry/DEVICE/%s/timeseries/delete" % dev["id"]["id"], headers=h,
                        params={"keys": ",".join(KEYS), "deleteAllDataForKeys": "true"}, timeout=60)
    print("cleared history of Garage-Edge:", r.status_code)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--spots", type=int, default=int(os.environ.get("GARAGE_SPOTS", "6")))
    ap.add_argument("--tb-host", default=os.environ.get("TB_HOST", "localhost"))
    ap.add_argument("--tb-port", type=int, default=int(os.environ.get("TB_MQTT_PORT", "1884")))
    ap.add_argument("--token", default=os.environ.get("TB_GATEWAY_TOKEN", "garage-edge-gateway-token"))
    ap.add_argument("--clear", action="store_true", help="delete the history instead of adding to it")
    ap.add_argument("--url", default=os.environ.get("TB_URL", "http://localhost:8080"))
    ap.add_argument("--user", default=os.environ.get("TB_USER", "tenant@thingsboard.org"))
    ap.add_argument("--password", default=os.environ.get("TB_PASSWORD", "tenant"))
    args = ap.parse_args(argv)
    if args.clear:
        clear(args.url, args.user, args.password)
    else:
        seed(args.tb_host, args.tb_port, args.token, args.days, args.spots)
    return 0


if __name__ == "__main__":
    sys.exit(main())
