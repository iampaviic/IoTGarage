"""Offline checks of the varijanta B rule chain (no ThingsBoard needed).

The decisions themselves are tested against a real ThingsBoard by integracija/tests/test_varijanta_b.py.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULECHAIN = os.path.join(HERE, "..", "rulechain")
sys.path.insert(0, RULECHAIN)

import build_rule_chain  # noqa: E402


def test_committed_json_matches_the_scripts():
    """garaza.json must be regenerated (python build_rule_chain.py) after every script change."""
    with open(build_rule_chain.OUT, encoding="utf-8") as f:
        committed = json.load(f)
    assert committed == json.loads(json.dumps(build_rule_chain.build())), "run rulechain/build_rule_chain.py"


def test_connections_are_valid_and_every_script_is_used():
    chain = build_rule_chain.build()["metadata"]
    n = len(chain["nodes"])
    for c in chain["connections"]:
        assert 0 <= c["fromIndex"] < n and 0 <= c["toIndex"] < n
    used = {node["configuration"].get("tbelScript") for node in chain["nodes"]}
    for name in os.listdir(os.path.join(RULECHAIN, "scripts")):
        assert build_rule_chain.script(name[:-5]) in used, name + " is not used by any node"


def test_every_node_except_the_first_is_reachable():
    chain = build_rule_chain.build()["metadata"]
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop()
        for c in chain["connections"]:
            if c["fromIndex"] == i and c["toIndex"] not in seen:
                seen.add(c["toIndex"])
                todo.append(c["toIndex"])
    assert seen == set(range(len(chain["nodes"])))
