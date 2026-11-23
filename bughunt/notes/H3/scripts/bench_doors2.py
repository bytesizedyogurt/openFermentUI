"""H3: every origin kind at the Proforma scope's resolve (POST /api/params/proforma:<id>/resolve, a door
that starts no worker), a reading from another project, and a corrected reading that stands again once
its correction's sample time moves.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/bench_doors2.py http://127.0.0.1:8830
Run after bench_doors.py (it reads dep1 in p1).
"""
from __future__ import annotations

import json
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8830"
c = httpx.Client(base_url=O, trust_env=False, timeout=120)
P1 = {"X-OpenFerment-Project": "p1"}
P2 = {"X-OpenFerment-Project": "p2"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"
SCOPE = "/api/params/proforma:sc-h3/resolve"


def show(tag, r, n=600):
    try:
        body = r.json()
    except Exception:
        body = r.text
    print(f"[{tag}] {r.status_code} {json.dumps(body, ensure_ascii=False)[:n]}")
    return body


def resolve(inputs, h=P1):
    return c.post(SCOPE, json={"flowsheet": "ethanol_glucose_v0", "inputs": inputs}, headers=h)


def titre(value, unit, origin):
    return {"name": "titre", "quantity": {"value": value, "unit": unit, "origin": origin}}


print("== every origin kind at the Proforma resolve ==")
kinds = {
    "person-assumption": {"kind": "person-assumption", "by": ADA, "at": T0},
    "model-estimate": {"kind": "model-estimate", "by": "claude-x", "at": T0},
    "measurement": {"kind": "measurement", "ref": "dep1/e6"},
    "record": {"kind": "record", "ref": "r1"},
    "artifact": {"kind": "artifact", "ref": "a1"},
    "library-default": {"kind": "library-default", "ref": "biorefineries"},
    "convention": {"kind": "convention", "note": "a setting"},
}
for k, o in kinds.items():
    v, u = (42.0, "g/L") if k == "measurement" else (42.0, "g L-1")
    b = show(f"resolve {k}", resolve([titre(v, u, o)]), 300)
    if isinstance(b, dict) and "values" in b:
        t = next(x for x in b["values"] if x["key"] == "titre")
        print(f"    titre -> {t['value']} origin {t['origin']} source {t['source']}")
        print(f"    basisInputs: {[ (bi['name'], bi['value'], bi['source']['kind']) for bi in b['basisInputs'] if bi['name'].startswith('titre')]}")

print("\n== a measurement sent with a different value or unit, a low/high, a depositor named ==")
show("value differs", resolve([titre(40.0, "g/L", kinds["measurement"])]), 300)
show("unit differs", resolve([titre(42.0, "g L-1", kinds["measurement"])]), 300)
show("with a high", resolve([{"name": "titre", "quantity": {"value": 42.0, "unit": "g/L", "high": 50, "origin": kinds["measurement"]}}]), 300)
show("another depositor", resolve([titre(42.0, "g/L", {**kinds["measurement"], "by": "Someone Else"})]), 300)
show("unconfirmed reading e2", resolve([titre(41.0, "g/L", {"kind": "measurement", "ref": "dep1/e2"})]), 300)
show("corrected reading e1", resolve([titre(40.0, "g/L", {"kind": "measurement", "ref": "dep1/e1"})]), 300)
show("a reading in K for a titre", resolve([titre(300.0, "K", {"kind": "measurement", "ref": "dep1/e3"})]), 300)

print("\n== another project's reading (p2 names p1's dep1/e6) ==")
show("p2 resolve", resolve([titre(42.0, "g/L", kinds["measurement"])], h=P2), 300)

print("\n== a series correction undone by moving a sample time ==")
def entry(eid, value, confirmed=True, corrected=None):
    e = {"id": eid, "measureId": "m1", "stepId": "readings", "at": T0, "value": value, "unit": "g/L",
         "raw": f"{value} g/L", "confirmed": confirmed}
    if corrected:
        e["correctedAt"] = corrected
    return e

dep = {"id": "dep9", "runbookId": "rb1", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": None,
       "state": "running", "observations": [], "reconciliation": None,
       "entries": [entry("s1", 4.0)], "sampleTimes": {"s1": 5.0}}
show("deposit s1 at 5 h (a mis-read 4 g/L)", c.put("/api/state/depositions/dep9", json={"by": ADA, "value": dep}, headers=P1), 120)
dep["entries"].append(entry("s2", 40.0, corrected="2026-11-09T11:00:00Z"))
dep["sampleTimes"] = {"s1": 5.0, "s2": 5.0}
show("correct s1 by s2 at the same 5 h", c.put("/api/state/depositions/dep9", json={"by": ADA, "value": dep}, headers=P1), 120)
show("resolve on s1 (corrected)", resolve([titre(4.0, "g/L", {"kind": "measurement", "ref": "dep9/s1"})]), 300)
dep["sampleTimes"] = {"s1": 5.0, "s2": 6.0}
show("move s2 to 6 h", c.put("/api/state/depositions/dep9", json={"by": ADA, "value": dep}, headers=P1), 120)
b = show("resolve on s1 again", resolve([titre(4.0, "g/L", {"kind": "measurement", "ref": "dep9/s1"})]), 300)
r = c.get("/api/depositions/readings", params={"unit": "g L-1"}, headers=P1).json()
print("readings offered for a titre now:", [(x["ref"], x["value"], x["hours"]) for x in r])
dep["sampleTimes"] = {"s2": 6.0}
show("take s1's sample time away", c.put("/api/state/depositions/dep9", json={"by": ADA, "value": dep}, headers=P1), 120)
