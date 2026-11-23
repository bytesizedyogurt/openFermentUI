"""H5: two kinds of row share a table under one key (project_id, id): a study scenario (kind engine) and a
Proforma scenario (kind proforma) in `scenarios`; a study runbook and a page's runbook in `runbooks`, a locked
one among them. Within project bh-a: a Proforma scenario PUT under a study scenario's id, and a DELETE of a
locked study runbook through /api/state. Prints what A holds before and after."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j

A = "bh-a"
ids = json.load(open(f"{OUT}/a_ids.json"))
sc, rb = ids["scenario"], ids["runbook"]
print("1. study scenario before:", call("GET", f"/api/studies/scenarios/{sc}", A).text[:200])
row = {"id": sc, "modelId": "ethanol_glucose_v0", "flowsheetId": "ethanol_glucose_v0", "kind": "biosteam",
       "name": "A Proforma scenario under the study's id", "description": "", "product": "", "pinned": False,
       "lastRunId": None, "createdAt": "2026-11-10T07:00:00Z"}
r = call("PUT", f"/api/state/scenarios/{sc}", A, json={"by": "alice", "value": row})
print("   PUT /api/state/scenarios:", r.status_code, r.text[:160])
print("   study scenario after:", call("GET", f"/api/studies/scenarios/{sc}", A).status_code,
      call("GET", f"/api/studies/scenarios/{sc}", A).text[:200])
print("   study scenarios listed:", [s["id"] for s in j(call("GET", "/api/studies/scenarios", A))])
d = call("DELETE", f"/api/state/scenarios/{sc}", A, params={"by": "alice"})
print("   DELETE /api/state/scenarios:", d.status_code, d.text[:160])
print("   study scenario after the undo:", call("GET", f"/api/studies/scenarios/{sc}", A).status_code)

print("2. study runbook before:", call("GET", f"/api/studies/runbooks/{rb}", A).status_code,
      "locked:", rb in j(call("GET", "/api/state", A))["runbookLocks"])
d = call("DELETE", f"/api/state/runbooks/{rb}", A, params={"by": "alice"})
print("   DELETE /api/state/runbooks:", d.status_code, d.text[:200])
st = j(call("GET", "/api/state", A))
print("   study runbook after:", call("GET", f"/api/studies/runbooks/{rb}", A).status_code,
      call("GET", f"/api/studies/runbooks/{rb}", A).text[:150])
print("   lock still kept:", rb in st["runbookLocks"], st["runbookLocks"].get(rb))
print("   audit:", [(a["action"], a["target"]) for a in j(call("GET", "/api/audit", A, params={"target": rb}))])
