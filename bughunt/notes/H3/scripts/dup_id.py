"""H3: a deposition write that appends a second entry under an id an earlier entry holds is kept; the
second reading is named by no ref.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/dup_id.py http://127.0.0.1:8830
"""
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8830"
c = httpx.Client(base_url=O, trust_env=False, timeout=120)
H = {"X-OpenFerment-Project": "p1"}
T0 = "2026-11-09T10:00:00Z"


def e(eid, v, m="mz"):
    return {"id": eid, "measureId": m, "stepId": "readings", "at": T0, "value": v, "unit": "g/L", "raw": f"{v} g/L",
            "confirmed": True}


dep = {"id": "depD", "runbookId": "rbD", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": None,
       "state": "running", "observations": [], "reconciliation": None, "sampleTimes": {}, "entries": [e("d1", 10.0)]}
print("first", c.put("/api/state/depositions/depD", json={"by": "Ada Lovelace", "value": dep}, headers=H).status_code)
dep["entries"].append(e("d1", 99.0, m="other"))
r = c.put("/api/state/depositions/depD", json={"by": "Ada Lovelace", "value": dep}, headers=H)
print("a second entry under d1 (99 g/L, another measure):", r.status_code)
kept = next(d for d in c.get("/api/state", headers=H).json()["depositions"] if d["id"] == "depD")
print("entries kept:", [(x["id"], x["value"], x["measureId"]) for x in kept["entries"]])
r = c.get("/api/depositions/readings", params={"unit": "g/L"}, headers=H).json()
print("readings offered:", [(x["ref"], x["value"], x["measureId"]) for x in r if x["depositionId"] == "depD"])
