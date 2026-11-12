"""Varijanta B end-to-end: simulated devices + the rule chain in a REAL ThingsBoard.

The scenario clears the parking sessions of the Garage asset, so it runs only when asked:
    docker compose -f thingsboard/docker-compose.yml up -d && python thingsboard/provision/provision.py
    TB_LIVE_TEST=1 pytest integracija/tests/test_varijanta_b.py -v
Variables as in integracija/simulacija_b.py (TB_URL, TB_HOST, TB_MQTT_PORT, tokens).
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

pytestmark = pytest.mark.skipif(os.environ.get("TB_LIVE_TEST") != "1",
                                 reason="needs a ThingsBoard prepared by provision.py; set TB_LIVE_TEST=1")


def test_demo_scenario_in_thingsboard():
    from simulacija_b import SystemB, scenario

    system = SystemB(verbose=True).start()
    try:
        scenario(system)
    finally:
        system.stop()


# ------------------------------------------------------------------ decide.tbel through ThingsBoard's script tester
SCRIPTS = os.path.join(HERE, "..", "..", "thingsboard", "rulechain", "scripts")


def _tb():
    from simulacija_b import TbRest

    return TbRest(os.environ.get("TB_URL", "http://localhost:8080"),
                  os.environ.get("TB_USER", "tenant@thingsboard.org"), os.environ.get("TB_PASSWORD", "tenant"))


@pytest.fixture(scope="module")
def decide():
    """Runs decide.tbel in ThingsBoard (same TBEL engine as the rule chain) and returns (msg, metadata)."""
    import json

    tb = _tb()
    with open(os.path.join(SCRIPTS, "decide.tbel"), encoding="utf-8") as f:
        script = f.read()

    def run(msg, **metadata):
        md = {"gate": "ENTRANCE", "direction": "ENTRY", "manual": "false", "ss_totalSpots": "6",
              "ss_sensorFree": "6", "ss_acceptThreshold": "0.85"}
        md.update({k: str(v) for k, v in metadata.items()})
        r = tb.post("/api/ruleChain/testScript", {"script": script, "scriptType": "update",
                                                  "argNames": ["msg", "metadata", "msgType"], "msg": json.dumps(msg),
                                                  "metadata": md, "msgType": "POST_TELEMETRY_REQUEST"},
                    scriptLang="TBEL")
        r.raise_for_status()
        assert not r.json().get("error"), r.json()["error"]
        out = json.loads(r.json()["output"])
        return out["msg"], out["metadata"]
    return run


def test_gate_never_opens_below_the_accept_threshold(decide):
    for direction in ("ENTRY", "EXIT"):
        for status in ("OK", "LOW_CONFIDENCE", "INVALID_FORMAT", "NO_PLATE", "CAMERA_ERROR", "TIMEOUT"):
            for conf in (0.0, 0.3, 0.6, 0.84, 0.849, 0.85, 0.95):
                for plate in ("ZG1234AB", None):
                    sessions = '{"ZG1234AB": {"sessionId": "S-1", "entryTime": "2026-10-19T08:00:00Z", ' \
                               '"entryTs": 1792396800000, "entryMode": "AUTO"}}' if direction == "EXIT" else "{}"
                    msg, md = decide({"status": status, "plate": plate, "ocrConfidence": conf},
                                     direction=direction, ss_sessions=sessions)
                    if md["openGate"] == "true":
                        assert conf >= 0.85 and plate and status in ("OK", "LOW_CONFIDENCE"), (direction, status, conf)


def test_allowlist_policy(decide):
    allow = '["ZG1234AB"]'
    msg, _ = decide({"status": "OK", "plate": "ST555CD", "ocrConfidence": 0.95}, ss_policy="allowlist",
                    ss_allowlist=allow)
    assert (msg["decision"], msg["decisionReason"]) == ("DENIED", "NOT_ON_ALLOWLIST")
    msg, _ = decide({"status": "OK", "plate": "ZG1234AB", "ocrConfidence": 0.95}, ss_policy="allowlist",
                    ss_allowlist=allow)
    assert msg["decision"] == "GRANTED"


def test_price_matches_the_python_pricing_rule(decide):
    """TBEL price == SOFTWARE/baza PricingPolicy at the boundaries (real and demo profile)."""
    import time

    from parking_sessions import PricingPolicy

    for policy, multiplier in ((PricingPolicy.real(), 1), (PricingPolicy.demo(), 60)):
        for duration in (60, 900, 901, 3600, 3601, 7200, 86400, 86401, 90000, 200000):
            entry = int(time.time() * 1000) - duration * 1000
            sessions = '{"ZG1234AB": {"sessionId": "S-1", "entryTime": "x", "entryTs": %d, "entryMode": "AUTO"}}' % entry
            msg, _ = decide({"status": "OK", "plate": "ZG1234AB", "ocrConfidence": 0.95}, direction="EXIT",
                            ss_sessions=sessions, ss_timeMultiplier=multiplier)
            expected = policy.price_cents(msg["durationS"]) / 100.0
            assert msg["sessionEvent"] == "SESSION_CLOSED" and msg["price"] == expected, (policy.name, duration, msg)
