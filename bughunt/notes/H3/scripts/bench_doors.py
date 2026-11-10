"""H3: the bench's readings at the service's doors (ADR-006 C.5 and E.17; ADR-016; measurements.py;
project_state.deposition_refusal).

  source bughunt/lib/env.sh; O=$(bh_svc_start bh_h3_a 8830); bh_project $O p1; bh_project $O p2
  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/bench_doors.py http://127.0.0.1:8830

Writes rows in projects p1 and p2 of the test database behind ORIGIN; reads every door it can reach
without a worker (the readings list, the Proforma scope's resolve, the state rows, the module read tool).
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


def show(tag, r):
    try:
        body = r.json()
    except Exception:
        body = r.text
    s = json.dumps(body, ensure_ascii=False)
    print(f"[{tag}] {r.status_code} {s[:700]}")
    return body


def put(kind, rid, value, by=ADA, h=P1):
    return c.put(f"/api/state/{kind}/{rid}", json={"by": by, "value": value}, headers=h)


T0 = "2026-11-09T10:00:00Z"
runbook = {"id": "rb1", "kind": "experiment", "title": "Bench check", "status": "draft",
           "measurementSchema": [{"id": "m1", "label": "Ethanol titre", "unit": "g/L", "timepoint": "harvest"},
                                 {"id": "m2", "label": "Broth temperature", "unit": "°C", "timepoint": "harvest"}]}
show("runbook", put("runbooks", "rb1", runbook))


def entry(eid, value, unit, confirmed=True, measure="m1", at=T0, raw=None):
    return {"id": eid, "measureId": measure, "stepId": "readings", "at": at, "value": value, "unit": unit,
            "raw": raw or f"{value} {unit}", "confirmed": confirmed}


dep = {"id": "dep1", "runbookId": "rb1", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": None,
       "state": "running", "observations": [], "reconciliation": None, "sampleTimes": {},
       "entries": [entry("e1", 40.0, "g/L"),                      # stands, confirmed
                   entry("e2", 41.0, "g/L", confirmed=False, measure="m2"),     # unconfirmed
                   entry("e3", 300.0, "K", measure="m2"),          # a temperature in kelvin
                   entry("e4", 0.04, "Mg/L"),                      # megagrams per litre written as Mg
                   entry("e5", 12.0, "%")]}                        # a unit no titre converts from
show("deposit dep1", put("depositions", "dep1", dep))

print("\n== the readings list, by the parameter's unit ==")
for u in ["g L-1", "g/L", "°C", "K", "kg m-3", "", None]:
    q = {} if u is None else {"unit": u}
    body = show(f"readings unit={u!r}", c.get("/api/depositions/readings", params=q, headers=P1))

print("\n== another project's reading ==")
show("readings in p2", c.get("/api/depositions/readings", headers=P2))

print("\n== a correction, then a sample time moved while the deposition is open ==")
dep2 = json.loads(json.dumps(dep))
dep2["entries"].append({**entry("e6", 42.0, "g/L"), "correctedAt": "2026-11-09T11:00:00Z"})
show("correct e1 by e6", put("depositions", "dep1", dep2))
show("readings after correction", c.get("/api/depositions/readings", params={"unit": "g L-1"}, headers=P1))
dep3 = json.loads(json.dumps(dep2))
dep3["sampleTimes"] = {"e6": 5.0}
show("give e6 a sample time after it corrected e1", put("depositions", "dep1", dep3))
body = show("readings after the sample time", c.get("/api/depositions/readings", params={"unit": "g L-1"}, headers=P1))
print("standing refs:", [r["ref"] for r in body] if isinstance(body, list) else body)
dep4 = json.loads(json.dumps(dep3))
dep4["sampleTimes"] = {"e6": 7.5}
show("move e6's sample time again", put("depositions", "dep1", dep4))

print("\n== measured evidence: overwrite a released value, write one for no deposition ==")
me = {"id": "me1", "depositionId": "dep1", "runbookId": "rb1", "productId": None, "predictionId": "p1",
      "label": "Ethanol titre", "value": 40.0, "unit": "g/L", "provenance": "measured",
      "conditions": {"protocolId": None, "scale": 1, "strainId": None}, "deviations": [], "confirmed": True,
      "at": T0}
show("release me1", put("measuredEvidence", "me1", me))
show("overwrite me1 value 400", put("measuredEvidence", "me1", {**me, "value": 400.0}, by="Someone Else"))
show("measured evidence for a deposition the project lacks",
     put("measuredEvidence", "me2", {**me, "id": "me2", "depositionId": "nope", "value": 999.0}))
st = c.get("/api/state", headers=P1).json()
print("measuredEvidence kept:", [(m["id"], m["value"], m["provenance"], m["confirmed"], m["depositionId"])
                                 for m in st["measuredEvidence"]])
show("delete me1", c.delete("/api/state/measuredEvidence/me1", params={"by": ADA}, headers=P1))

print("\n== the module read (runbooks) through the HTTP tool door ==")
r = c.post("/api/tools/runbooks_read", params={"by": ADA}, json={}, headers=P1)
body = show("runbooks_read", r)
for row in (body.get("summary") or {}).get("rows") or []:
    print("   row", row.get("kind"), row.get("id"), row.get("provenance"), (row.get("detail") or {}).get("value"))

print("\n== an estimate offered to each bench record ==")
est = {"kind": "model-estimate", "by": "claude-x", "at": T0}
dep5 = json.loads(json.dumps(dep4))
dep5["entries"].append({**entry("e7", 43.0, "g/L"), "origin": est})
show("deposition entry with an estimate origin", put("depositions", "dep1", dep5))
show("measured evidence saying assumed", put("measuredEvidence", "me3", {**me, "id": "me3", "provenance": "assumed"}))
show("measured evidence with an estimate in deviations",
     put("measuredEvidence", "me4", {**me, "id": "me4", "deviations": [], "basis": {"kind": "model-estimate"}}))
