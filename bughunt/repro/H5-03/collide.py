"""H5-03: a PUT /api/state write under another kind's id replaces that row.

Against a keyless service over a fresh database (run.sh starts both): one project; a study scenario made
through POST /api/studies/scenarios (kind `engine`) and a model's kept train made through the pureos_build
tool in the model's lane (kind `kept`); then a person's PUT /api/state/scenarios/<the study's id> and PUT
/api/state/trains/<the kept train's id>. Prints what the project holds before and after each write, the
rows' `kind` column as the database keeps it, and the verdict."""
import os
import subprocess
import sys

import httpx

ORIGIN = os.environ["ORIGIN"]
DB_URL = os.environ["DB_URL"]
P = "bh-r-h5-03"
AT = "2026-11-10T07:00:00Z"
C = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": P})
MODEL = {"X-OpenFerment-Assistant": "bh-h5-03-agent/0.1"}


def need(r, label, want=200):
    print(f"  {label}: {r.status_code} {r.text[:220]}")
    if r.status_code != want:
        print(f"OBSERVED: the setup stopped at {label}")
        print("RESULT: NO-DEFECT")
        sys.exit(0)
    return r.json()


def kind_of(table, row_id):
    out = subprocess.run(["psql", DB_URL, "-qAtXc",
                          f"select kind || ', made by ' || created_by from {table} where project_id = '{P}' and id = '{row_id}'"],
                         capture_output=True, text=True)
    return out.stdout.strip() or "(no row)"


print("setup")
need(httpx.post(f"{ORIGIN}/api/projects", json={"id": P, "name": P, "by": "alice"}, trust_env=False),
     "POST /api/projects", 201)
sc = need(C.post("/api/studies/scenarios", json={"title": "Alice's study scenario", "plant": "cornstover",
                                                  "by": "alice", "values": []}), "POST /api/studies/scenarios")["id"]


def pa(v, u):
    return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": "alice", "at": AT}}


inputs = [{"name": k, "quantity": pa(v, u)} for k, v, u in (
    ("mu_max", 0.3, "h⁻¹"), ("ks", 0.5, "g L⁻¹"), ("yxs", 0.1, "g g⁻¹"), ("alpha", 4.0, "g g⁻¹"), ("yps", 0.45, "g g⁻¹"),
    ("p_max", 100.0, "g L⁻¹"), ("x0", 1.0, "g L⁻¹"), ("s0", 50.0, "g L⁻¹"), ("p0", 0.0, "g L⁻¹"))]
run = need(C.post("/api/engines/kinetics/run", json={"thing": "batch_v1", "by": "alice", "inputs": inputs}),
           "POST /api/engines/kinetics/run")["run"]["id"]
built = need(C.post("/api/tools/pureos_build", headers=MODEL, json={"action": "new", "product": "ethanol",
                                                                   "inletRef": run}), "POST /api/tools/pureos_build new")
tr = (built.get("summary") or {}).get("trainId")
if not tr:
    print("OBSERVED: pureos_build named no train id")
    print("RESULT: NO-DEFECT")
    sys.exit(0)

defects = []

print(f"\n1. study scenario {sc}")
before = C.get(f"/api/studies/scenarios/{sc}")
print(f"  before: GET /api/studies/scenarios/{sc} {before.status_code}; title {before.json().get('title')!r}, "
      f"plant {before.json().get('plant')!r}; listed {[s['id'] for s in C.get('/api/studies/scenarios').json()]}; "
      f"row {(row_before := kind_of('scenarios', sc))}")
row = {"id": sc, "modelId": "ethanol_glucose_v0", "flowsheetId": "ethanol_glucose_v0", "kind": "biosteam",
       "name": "Bob's Proforma scenario", "description": "", "product": "", "pinned": False, "lastRunId": None,
       "createdAt": AT}
put = C.put(f"/api/state/scenarios/{sc}", json={"by": "bob", "value": row})
print(f"  PUT /api/state/scenarios/{sc} as bob: {put.status_code} {put.text[:160]}")
after = C.get(f"/api/studies/scenarios/{sc}")
listed = [s["id"] for s in C.get("/api/studies/scenarios").json()]
row_after = kind_of("scenarios", sc)
print(f"  after: GET /api/studies/scenarios/{sc} {after.status_code} {after.text[:120]}; listed {listed}; "
      f"row {row_after}")
gone = C.delete(f"/api/state/scenarios/{sc}", params={"by": "bob"})
print(f"  DELETE /api/state/scenarios/{sc} as bob: {gone.status_code}; row {kind_of('scenarios', sc)}")
if put.status_code == 200 and after.status_code == 404 and sc not in listed:
    defects.append(f"PUT /api/state/scenarios/{sc} answered 200 and the study scenario is gone "
                   f"(GET {after.status_code}, the list {listed}, the row {row_before!r} now {row_after!r})")

print(f"\n2. kept train {tr}")
kept = [k["spec"]["id"] for k in C.get("/api/pureos/trains-kept").json()]
tr_before = kind_of("trains", tr)
print(f"  before: GET /api/pureos/trains-kept {kept}; row {tr_before}")
made = {"train": {"id": tr, "name": "Bob's train", "program": "placeholder", "product": "x",
                  "inlet": {"kind": "typed"}, "units": []}, "savedAt": AT, "by": "bob"}
put = C.put(f"/api/state/trains/{tr}", json={"by": "bob", "value": made})
print(f"  PUT /api/state/trains/{tr} as bob: {put.status_code} {put.text[:160]}")
kept_after = [k["spec"]["id"] for k in C.get("/api/pureos/trains-kept").json()]
tr_after = kind_of("trains", tr)
print(f"  after: GET /api/pureos/trains-kept {kept_after}; row {tr_after}")
if put.status_code == 200 and tr in kept and tr not in kept_after:
    defects.append(f"PUT /api/state/trains/{tr} answered 200 and the model's kept train is gone "
                   f"(trains-kept {kept} then {kept_after}, the row {tr_before!r} now {tr_after!r})")

audit = C.get("/api/audit", params={"limit": 50}).json()
print("\n  audit rows on the two ids:",
      [(a["action"], a.get("who"), a["target"]) for a in audit if a.get("target") in (sc, tr)])

print("\nEXPECTED: each PUT refused in words (a 422) naming the row another kind keeps under that id; the study "
      "scenario and the model's kept train read back as they were made")
if defects:
    print("OBSERVED: " + "; ".join(defects))
    print("RESULT: DEFECT")
else:
    print("OBSERVED: each write was refused or left the other kind's row as it was")
    print("RESULT: NO-DEFECT")
