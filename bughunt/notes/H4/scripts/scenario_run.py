"""H4: one run of the ethanol_glucose_v0 scenario flowsheet through POST /api/engines/biosteam/run,
then its tables (GET /api/biorepo/artifacts/{id}/tables); writes both to the scratch directory.
    cd core && bh_env .venv/bin/python scenario_run.py http://127.0.0.1:8840 h4p
"""
import json, sys, httpx
O, P = sys.argv[1], sys.argv[2]
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
def q(v, u): return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
vals = {"feed_glucose_conc": (150.0, "g L-1"), "titre": (70.0, "g L-1"), "yield": (0.45, "g g-1"),
        "productivity": (2.0, "g L-1 h-1"), "plant_scale": (100000.0, "t yr-1"), "glucose_price": (0.4, "USD kg-1")}
body = {"thing": "ethanol_glucose_v0", "by": "h4", "inputs": [{"name": k, "quantity": q(*v)} for k, v in vals.items()]}
with httpx.Client(trust_env=False, timeout=900) as c:
    r = c.post(f"{O}/api/engines/biosteam/run", json=body, headers=H)
    print(r.status_code)
    d = r.json()
    json.dump(d, open(f"{W}/svc-egv0.json", "w"))
    run = d.get("run") or d
    print(run.get("status"), run.get("refused"), run.get("id"))
    t = c.get(f"{O}/api/biorepo/artifacts/{run['id']}/tables", headers=H)
    print(t.status_code)
    json.dump(t.json(), open(f"{W}/svc-egv0-tables.json", "w"))
    a = c.get(f"{O}/api/runs/{run['id']}", headers=H)
    json.dump(a.json(), open(f"{W}/svc-egv0-report.json", "w"))
