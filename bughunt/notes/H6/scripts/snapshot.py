"""snapshot.py ORIGIN PROJECT OUT.json: every read route a project answers, list and detail, as JSON.

Run against alpha 2.1's service before the upgrade and against the head's after it; compare.py sets the
two side by side. Each answer is kept with its status; a detail route is asked for every id its list names.
A read changes nothing.
"""
from __future__ import annotations

import json
import sys
from typing import Any

import httpx

origin, project, out = sys.argv[1], sys.argv[2], sys.argv[3]
c = httpx.Client(base_url=origin, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": project})
got: dict[str, Any] = {}


def get(path: str, **params: Any) -> Any:
    key = path + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")
    r = c.get(path, params=params or None)
    try:
        body = r.json()
    except ValueError:
        body = r.text[:500]
    got[key] = {"status": r.status_code, "body": body}
    return body if r.status_code == 200 else None


def ids(body: Any, *keys: str) -> list[str]:
    if isinstance(body, dict):
        for k in ("runs", "artifacts", "items", "flowsheets", "entries"):
            if isinstance(body.get(k), list):
                body = body[k]
                break
    out_: list[str] = []
    for x in body or []:
        if isinstance(x, dict):
            for k in keys:
                if isinstance(x.get(k), str):
                    out_.append(x[k])
                    break
    return out_


get("/api/health")
get("/api/projects")
get(f"/api/projects/{project}")
get("/api/state")
for rid in ids(get("/api/runs"), "id"):
    get(f"/api/runs/{rid}")
arts = get("/api/biorepo/artifacts")
for aid in ids(arts, "id"):
    get(f"/api/biorepo/artifacts/{aid}")
    get(f"/api/biorepo/artifacts/{aid}/tables")
    get(f"/api/biorepo/artifacts/{aid}/checks")
get("/api/biorepo/overlay")
for kind in ("strain", "product", "skill", "lesson"):
    for eid in ids(get(f"/api/catalogues/{kind}"), "id"):
        get(f"/api/catalogues/{kind}/{eid}")
for cid in ids(get("/api/conversations"), "id"):
    conv = get(f"/api/conversations/{cid}")
    for tid in ids((conv or {}).get("turns"), "id"):
        get(f"/api/conversations/{cid}/turns/{tid}/calls")
for fid in ids(get("/api/flowsheets"), "id"):
    get(f"/api/flowsheets/{fid}")
    get(f"/api/flowsheets/{fid}/file")
get("/api/flowsheets/library")
get("/api/literature/documents")
get("/api/literature/stats")
for sid in ids(get("/api/studies/scenarios"), "id"):
    get(f"/api/studies/scenarios/{sid}")
for cid in ids(get("/api/studies/comparisons"), "id"):
    get(f"/api/studies/comparisons/{cid}")
for bid in ids(get("/api/studies/runbooks"), "id"):
    get(f"/api/studies/runbooks/{bid}")
for path in ("/api/guild", "/api/guild/checks", "/api/practice", "/api/proposals", "/api/audit",
             "/api/fermos/simulations", "/api/fermos/vessels", "/api/fermos/families", "/api/pureos/train-runs",
             "/api/pureos/trains-kept", "/api/pureos/trains", "/api/witness/runs", "/api/proforma/scenarios",
             "/api/proforma/shelf", "/api/proforma/status", "/api/library", "/api/geneos/models",
             "/api/depositions/readings", "/api/engines", "/api/protocols", "/api/tools",
             "/api/proforma/benchmark", "/api/proforma/reference/corn_drygrind",
             "/api/proforma/reference/cornstover_benchmark"):
    get(path)
st = got["/api/state"]["body"] if got["/api/state"]["status"] == 200 else {}
for s in (st or {}).get("scenarios", []):
    get("/api/proforma/runs", scenarioId=s["id"])
for path in ("/api/fermos/fits",):
    get(path, flowsheet="ethanol_glucose_v0")
json.dump(got, open(out, "w"), indent=1, default=str)
bad = {k: v["status"] for k, v in got.items() if v["status"] != 200}
print(f"{len(got)} reads, {len(bad)} not 200")
for k, v in bad.items():
    print("  ", v, k, str(got[k]["body"])[:200])
