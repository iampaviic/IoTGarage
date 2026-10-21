"""Contract monitor: print every garage/# message and check it against the schema.

    python -m garage_contract.monitor                 # watch everything
    python -m garage_contract.monitor --filter 'garage/gate/#'
    python -m garage_contract.monitor --pub garage/gate/entrance/command \
        '{"requestId":"t1","command":"OPEN","reason":"TEST"}'

The most useful tool during integration: if a message is red, the sender
violates the contract (or the contract must be changed by osoba 1).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from garage_contract.config import MqttSettings
from garage_contract.mqtt import MqttConnection
from garage_contract.validation import errors_for, message_type_for_topic

GREEN = "\033[32m"
RED = "\033[31m"
GREY = "\033[90m"
RESET = "\033[0m"


def _print(topic: str, payload, color: bool) -> None:
    def c(code: str, text: str) -> str:
        return code + text + RESET if color else text

    stamp = time.strftime("%H:%M:%S")
    message_type = message_type_for_topic(topic)
    body = json.dumps(payload, ensure_ascii=False)
    if message_type is None:
        print("%s %s %s %s" % (stamp, c(GREY, "?  "), topic, body))
        return
    errors = errors_for(message_type, payload)
    mark = c(GREEN, "OK ") if not errors else c(RED, "ERR")
    print("%s %s %s %s" % (stamp, mark, topic, body))
    for e in errors:
        print("            " + c(RED, "-> " + e))
    sys.stdout.flush()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", help="MQTT host (default $MQTT_HOST or localhost)")
    ap.add_argument("--port", type=int, help="MQTT port (default $MQTT_PORT or 1883)")
    ap.add_argument("--filter", default="garage/#", help="topic filter to watch")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--pub", nargs=2, metavar=("TOPIC", "JSON"), help="publish one message and exit")
    ap.add_argument("--retain", action="store_true", help="with --pub: retained message")
    args = ap.parse_args(argv)

    settings = MqttSettings.from_env()
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port

    conn = MqttConnection("garage-monitor-%d" % int(time.time() * 1000 % 100000), settings)
    if args.pub:
        topic, raw = args.pub
        payload = json.loads(raw)
        _print(topic, payload, not args.no_color)
        if not conn.start():
            print("broker not reachable", file=sys.stderr)
            return 1
        conn.publish_json(topic, payload, retain=args.retain)
        time.sleep(0.3)
        conn.stop()
        return 0

    conn.subscribe(args.filter, lambda t, p: _print(t, p, not args.no_color))
    conn.start()
    print("watching %s on %s:%s (Ctrl+C to stop)" % (args.filter, settings.host, settings.port))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    conn.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
