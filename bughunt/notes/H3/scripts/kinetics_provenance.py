"""H3: a contract engine's run (kinetics, no worker) on every mix of origins, and the provenance each
reader answers: the run's report, GET /api/runs/{id}, and the runs list.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/kinetics_provenance.py http://127.0.0.1:8830
"""
from __future__ import annotations

import json
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8830"
c = httpx.Client(base_url=O, trust_env=False, timeout=300)
P1 = {"X-OpenFerment-Project": "p1"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"

READ = {  # key: (value, unit as deposited, parameter unit)
    "mu_max": (0.0125, "min⁻¹", "h⁻¹"), "ks": (0.5, "g/L", "g L⁻¹"), "yxs": (0.1, "g/g", "g g⁻¹"),
    "alpha": (2.0, "g/g", "g g⁻¹"), "yps": (0.45, "g/g", "g g⁻¹"), "p_max": (90.0, "g/L", "g L⁻¹"),
    "x0": (0.1, "g/L", "g L⁻¹"), "s0": (100.0, "g/L", "g L⁻¹"), "p0": (0.0, "g/L", "g L⁻¹"),
}
entries = [{"id": f"k{n}", "measureId": f"mk_{k}", "stepId": "readings", "at": T0, "value": v, "unit": u,
            "raw": f"{v} {u}", "confirmed": True} for n, (k, (v, u, _)) in enumerate(READ.items())]
dep = {"id": "depK", "runbookId": "rbK", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": None,
       "state": "running", "observations": [], "reconciliation": None, "sampleTimes": {}, "entries": entries}
r = c.put("/api/state/depositions/depK", json={"by": ADA, "value": dep}, headers=P1)
print("deposit", r.status_code)
ref = {k: f"depK/k{n}" for n, k in enumerate(READ)}


def reading(k):
    v, u, _ = READ[k]
    return {"name": k, "quantity": {"value": v, "unit": u, "origin": {"kind": "measurement", "ref": ref[k]}}}


def person(k, by=ADA):
    v, u, pu = READ[k]
    from_unit = {"min⁻¹": 60.0}.get(u, 1.0)
    return {"name": k, "quantity": {"value": v * from_unit, "unit": pu,
                                    "origin": {"kind": "person-assumption", "by": by, "at": T0}}}


def estimate(k):
    v, u, pu = READ[k]
    from_unit = {"min⁻¹": 60.0}.get(u, 1.0)
    return {"name": k, "quantity": {"value": v * from_unit, "unit": pu,
                                    "origin": {"kind": "model-estimate", "by": "claude-x", "at": T0}}}


def run(tag, inputs):
    r = c.post("/api/engines/kinetics/run", json={"thing": "batch_v1", "inputs": inputs, "by": ADA}, headers=P1)
    b = r.json()
    if r.status_code != 200:
        print(f"[{tag}] {r.status_code} {json.dumps(b)[:400]}")
        return None
    run_ = b.get("run") or {}
    rid = run_.get("id")
    got = c.get(f"/api/runs/{rid}", headers=P1).json()["run"]
    kinds = sorted({i["quantity"].get("origin", {}).get("kind") for i in got.get("inputs", [])})
    mu = next((i for i in got.get("inputs", []) if i["name"].endswith("mu_max")), None)
    print(f"[{tag}] report {run_.get('provenance')} | GET /api/runs {got.get('provenance')} | origins {kinds}")
    if mu:
        print(f"      mu_max input: {mu['quantity']}")
    return rid


all_read = [reading(k) for k in READ]
run("every value a reading", all_read)
run("readings and one estimate", [*all_read[:-1], estimate("p0")])
run("readings and one person's value", [*all_read[:-1], person("p0")])
run("every value a person's", [person(k) for k in READ])
run("every value a model's", [estimate(k) for k in READ])
listed = c.get("/api/runs", headers=P1).json()
print("runs list:", [(x.get("id"), x.get("engine"), x.get("provenance")) for x in (listed if isinstance(listed, list) else listed.get("runs", []))][:8])
