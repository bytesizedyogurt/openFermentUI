"""Boundary requests at POST /api/engines/{kinetics,train,biosteam}/run and the parameters route.
usage: core_doors.py ORIGIN PROJECT TRAIN_ID INPUTS_FILE"""
import json, sys
import httpx

O, P, TRAIN, INPUTS = sys.argv[1:5]
c = httpx.Client(trust_env=False, timeout=900, headers={"X-OpenFerment-Project": P})
placeholders = json.load(open(INPUTS))


def case(label, method, path, body=None, params=None):
    before = len(c.get(f"{O}/api/runs").json())
    r = c.request(method, O + path, json=body, params=params)
    gained = len(c.get(f"{O}/api/runs").json()) - before
    print(f"{label:<60} {r.status_code}  +{gained} rows  {r.text[:260]}")
    return r


K = "/api/engines/kinetics/run"
case("kinetics batch_v1, no values", "POST", K, {"thing": "batch_v1", "by": "H1"})
case("kinetics batch_v1, a configuration", "POST", K, {"thing": "batch_v1", "configuration": "x", "by": "H1"})
case("kinetics forecast, none kept", "POST", K, {"thing": "forecast", "by": "H1"})
case("kinetics vessel, a configuration no artifact", "POST", K, {"thing": "vessel", "configuration": "0123456789abcdef", "by": "H1"})
first = placeholders[0]
twice = placeholders + [first]
case("kinetics batch_v1, a key set twice", "POST", K, {"thing": "batch_v1", "inputs": twice, "by": "H1"})
far = [dict(p) for p in placeholders]
far[0] = {**far[0], "quantity": {**far[0]["quantity"], "value": 1e6}}
case("kinetics batch_v1, mu_max 1e6 (past its bounds)", "POST", K, {"thing": "batch_v1", "inputs": far, "by": "H1"})
ranged = [dict(p) for p in placeholders]
ranged[0] = {**ranged[0], "quantity": {**ranged[0]["quantity"], "low": 0.5, "high": 1.5}}
r = case("kinetics batch_v1, a range on mu_max", "POST", K, {"thing": "batch_v1", "inputs": ranged, "by": "H1"})
if r.status_code == 200:
    print("   basis names:", [i["name"] for i in r.json()["artifact"]["inputs"] if i["name"].startswith("mu_max")])
case("kinetics parameters batch_v1", "GET", "/api/engines/kinetics/parameters", params={"thing": "batch_v1"})
T = "/api/engines/train/run"
case("train unknown thing", "POST", T, {"thing": "nothing", "by": "H1"})
case("train configuration", "POST", T, {"thing": TRAIN, "configuration": "x", "by": "H1"})
case("train a name of neither form", "POST", T, {"thing": TRAIN, "by": "H1", "inputs": [{"name": "nodot", "quantity": {
    "value": 1.0, "unit": "", "origin": {"kind": "person-assumption", "by": "H1", "at": "2026-11-10"}}}]})
case("train parameters", "GET", "/api/engines/train/parameters", params={"thing": TRAIN})
case("biosteam unknown thing", "POST", "/api/engines/biosteam/run", {"thing": "nothing", "by": "H1"})
case("biosteam cornstover with a configuration", "POST", "/api/engines/biosteam/run", {"thing": "cornstover", "configuration": "x", "by": "H1"})
case("biosteam cane no configuration (default S1)", "GET", "/api/engines/biosteam/parameters", params={"thing": "cane"})
case("biosteam subsystem ethanol", "POST", "/api/engines/biosteam/run", {"thing": "ethanol", "by": "H1"})
case("biosteam scenario flowsheet, nothing set", "POST", "/api/engines/biosteam/run", {"thing": "ethanol_glucose_v0", "by": "H1"})
