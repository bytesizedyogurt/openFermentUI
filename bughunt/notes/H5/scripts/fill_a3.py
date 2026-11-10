"""Project bh-a, part three: the candidate accepted into a record, Guild evidence and a check, a kinetics
engine run, a comparison of it, a runbook made from it and locked, a study scenario, an SFF library record."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j, show

A = "bh-a"
AT = "2026-11-10T07:00:00Z"
ids = json.load(open(f"{OUT}/a_ids.json"))


def ok(label, r):
    show(label, r, 500)
    return j(r)


cands = ok("candidates", call("GET", "/api/biorepo/overlay", A))
cid = "mw1-" + ids["paste"]["documentId"] + "-0000"
if False:
    dec = ok("decision", call("POST", "/api/biorepo/decisions", A, json={
    "status": "verified", "provenance": "verified", "recordId": cid, "at": AT, "reviewer": "alice"}))
ids["record"] = cid
ev = {"id": "e-aaaa1", "personId": "p-a", "skillId": "SK-A", "kind": "knowledge", "at": AT,
      "source": {"kind": "lesson", "ref": "lesson-a"}, "raw": "A's evidence", "outcome": "pass"}
0 and ok("guild evidence", call("POST", "/api/guild/evidence", A, json=ev))
0 and ok("check request", call("POST", "/api/guild/checks/request", A, json={"personId": "p-a", "skillIds": ["SK-A"], "by": "p-a"}))
checks = ok("checks", call("GET", "/api/guild/checks", A))
ids["checks"] = [c["id"] for c in checks.get("checks", [])] if isinstance(checks, dict) else []


def pa(value, unit):
    return {"value": value, "unit": unit, "origin": {"kind": "person-assumption", "by": "alice", "at": AT}}


inputs = [{"name": k, "quantity": pa(v, u)} for k, v, u in (
    ("mu_max", 0.3, "h⁻¹"), ("ks", 0.5, "g L⁻¹"), ("yxs", 0.1, "g g⁻¹"), ("alpha", 4.0, "g g⁻¹"),
    ("yps", 0.45, "g g⁻¹"), ("p_max", 100.0, "g L⁻¹"), ("x0", 1.0, "g L⁻¹"), ("s0", 50.0, "g L⁻¹"),
    ("p0", 0.0, "g L⁻¹"))]
ids["kinetics_inputs"] = inputs
run = ok("kinetics run", call("POST", "/api/engines/kinetics/run", A, json={"thing": "batch_v1", "by": "alice",
                                                                            "inputs": inputs}))
rid = run.get("run", {}).get("id") if isinstance(run, dict) else None
ids["run"] = rid
art = run.get("run", {}).get("artifactId") if isinstance(run, dict) else None
print("run keys:", list(run.keys()) if isinstance(run, dict) else run, "run.run keys:",
      list(run.get("run", {}).keys()) if isinstance(run, dict) else "")
runs = ok("runs", call("GET", "/api/runs", A))
arts = ok("artifacts", call("GET", "/api/biorepo/artifacts", A))
ids["artifacts"] = [a["id"] for a in arts] if isinstance(arts, list) else []
if rid:
    comp = ok("comparison", call("POST", "/api/studies/comparisons", A, json={"title": "A's comparison", "runIds": [rid, rid],
                                                                          "by": "alice"}))
    ids["comparison"] = comp.get("id") if isinstance(comp, dict) else None
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
