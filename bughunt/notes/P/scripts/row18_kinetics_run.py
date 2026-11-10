"""Rows 18, 19, 21 on the kinetics engine: a run of batch_v1 through POST /api/engines/kinetics/run with typed
inputs (each a person's assumption at a placeholder value, ks set to a deposited reading by its ref as a
measurement); the run is one runs row of engine kinetics; its inputs keep their origins; the reading is set in the
parameter's unit; a second project cannot read it.

usage: bh_py row18_kinetics_run.py ORIGIN PROJECT READING_REF
"""
import json
import sys

import httpx

ORIGIN, PROJECT, REF = sys.argv[1:4]
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": PROJECT})
AT = "2026-11-10T23:30:00Z"
params = c.get("/api/engines/kinetics/parameters", params={"thing": "batch_v1"}).json()
inputs = []
for p in params:
    if p.get("value") is not None or p.get("choices"):
        continue
    lo = p.get("min") or 0.0
    hi = p.get("max")
    v = (lo + hi) / 2 if hi is not None else (lo + 1.0 if lo else 0.5)
    q = {"value": v, "unit": p["unit"], "origin": {"kind": "person-assumption", "by": "Ada Moreno", "at": AT}}
    v = {"p_max": 100.0, "s0": 20.0, "p0": 0.0, "x0": 0.1}.get(p["key"], v)
    q["value"] = v
    if p["key"] == "ks":
        q = {"value": 1.5, "unit": "g/L", "origin": {"kind": "measurement", "by": "Ada Moreno", "at": "2026-11-10T00:00:00Z", "ref": REF}}
    inputs.append({"name": p["key"], "quantity": q})
print("inputs:", [(i["name"], i["quantity"]["value"], i["quantity"]["unit"], i["quantity"]["origin"]["kind"]) for i in inputs])
r = c.post("/api/engines/kinetics/run", json={"thing": "batch_v1", "inputs": inputs, "by": "Ada Moreno"})
print("run:", r.status_code, r.text[:600] if r.status_code != 200 else "")
if r.status_code != 200:
    sys.exit(1)
run = r.json()
rid = run.get("id") or run.get("runId") or (run.get("run") or {}).get("id")
print("run keys:", sorted(run)[:30], "id", rid)
got = c.get(f"/api/runs/{rid}").json()
print("row:", {k: got.get(k) for k in ("id", "engine", "thing", "configuration", "provenance", "createdBy")})
for i in got.get("inputs", []):
    if i.get("name") in ("ks", "mu_max"):
        print("input", json.dumps(i)[:400])
print("rests on:", json.dumps(got.get("restsOn") or got.get("rests_on"))[:400])
other = httpx.get(f"{ORIGIN}/api/runs/{rid}", headers={"X-OpenFerment-Project": "pb"}, trust_env=False)
print("pb reads it:", other.status_code)
