"""H5: fill project bh-a with one of everything a person or an assistant can make without a model, and make an
empty project bh-b. Writes what A holds to $H5_OUT/a_ids.json for the probes. Run against a service
bh_svc_start began over a fresh bh_h5_ database (see run_all.sh)."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j, show

A, B = "bh-a", "bh-b"
AT = "2026-11-10T07:00:00Z"
WHO = {"X-OpenFerment-Assistant": "bh-h5-agent/0.1"}
ids = {}


def ok(label, r, want=200):
    show(label, r, 160)
    if r.status_code != want:
        raise SystemExit(f"fill stopped at {label}: {r.status_code} {r.text[:400]}")
    return j(r)


for pid, by in ((A, "alice"), (B, "bob")):
    ok(f"project {pid}", call("POST", "/api/projects", json={"id": pid, "name": pid, "by": by}), 201)
POLICY = {"criticality": "routine", "recencyDays": 30, "supervisedRuns": 1}
for kind, entry in (("skill", {"id": "SK-A", "name": "Skill only A holds", "family": "placeholder", "mastery": ["criterion"], **POLICY}),
                    ("strain", {"id": "strain-a", "name": "Strain only A holds", "species": "Placeholder species A", "aliases": ["SECRET-ALIAS-A"]}),
                    ("product", {"id": "product-a", "name": "Product only A holds", "category": "industrial_enzyme"}),
                    ("lesson", {"id": "lesson-a", "name": "Lesson only A holds", "skills": ["SK-A"]})):
    ok(kind, call("POST", f"/api/catalogues/{kind}", A, json={"by": "alice", "entry": {"kind": kind, **entry}}))
version = {"version": "1.0", "baseBatch": {"value": 1, "unit": "placeholder-unit", "label": "batch"},
           "materials": [{"name": "Material A", "amount": 2.5, "unit": "placeholder-unit", "scaling": "fixed", "precision": 0.5}],
           "steps": [{"id": "s1", "text": "Add {{qty:Material A}}.", "skills": ["SK-A"]}], "estMinutes": {"active": 1, "total": 2}}
ok("protocol", call("POST", "/api/protocols", A, json={"by": "alice", "protocol": {
    "id": "PR-A", "title": "Protocol only A holds", "category": "sop", "bsl": 1, "organisms": ["Placeholder"],
    "purpose": "A's purpose", "currentVersion": "1.0", "versions": [version]}}))
ids["protocol"] = "PR-A"
ENTRY = {"id": "de-a1", "measureId": "m-a1", "stepId": "s-1", "at": AT, "value": 7.2, "unit": "g/L", "raw": "A's reading", "confirmed": True}
ok("deposition", call("PUT", "/api/state/depositions/dep-a", A, json={"by": "alice", "value": {
    "id": "dep-a", "runbookId": "rb-a", "protocolId": None, "operatorId": None, "startedAt": AT, "closedAt": None,
    "state": "running", "entries": [ENTRY], "observations": [], "reconciliation": None}}))
ok("train", call("PUT", "/api/state/trains/tr-a", A, json={"by": "alice", "value": {
    "train": {"id": "tr-a", "name": "Train only A holds", "program": "placeholder", "product": "product-a",
              "inlet": {"kind": "typed"}, "units": []}, "savedAt": AT, "by": "alice"}}))
ok("conversation", call("PUT", "/api/state/conversations/lc-a", A, json={"by": "alice", "value": {
    "id": "lc-a", "title": "A's private question", "startedAt": AT, "turns": [{"id": "turn-a", "question": "A's private question",
    "askedAt": AT, "steps": [], "plan": None, "error": None, "status": "answered"}]}}))
ok("fits", call("PUT", "/api/state/fits/sc-a", A, json={"by": "alice", "value": {"mu_max": "0123456789abcdef"}}))
ok("overrides", call("PUT", "/api/state/overrides/proforma:sc-a", A, json={"by": "alice", "value": [
    {"scope": "proforma:sc-a", "key": "price", "value": 1.2, "by": "alice", "at": AT}]}))
ids["state"] = {"depositions": "dep-a", "trains": "tr-a", "conversations": "lc-a", "fits": "sc-a",
                "overrides": "proforma:sc-a", "turn": "turn-a"}
ok("guild person", call("POST", "/api/guild/people", A, json={"id": "p-a", "name": "Person only A holds", "joinedAt": AT,
                                                               "addedAt": AT, "role": "lead"}))
ok("guild evidence", call("POST", "/api/guild/evidence", A, json={
    "id": "e-aaaa1", "personId": "p-a", "skillId": "SK-A", "kind": "knowledge", "at": AT,
    "source": {"kind": "lesson", "ref": "lesson-a"}, "raw": "A's evidence", "outcome": "pass"}))
check = ok("check request", call("POST", "/api/guild/checks/request", A, json={"personId": "p-a", "skillIds": ["SK-A"], "by": "p-a"}))
ids["checks"] = [check["id"]]
paste = ok("paste", call("POST", "/api/intake/paste", A, json={
    "title": "A secret paper", "by": "alice",
    "text": "Zymomonas xylofermentans SECRETWORDA produced ethanol at a titre of 41 g/L from xylose in fed-batch culture.\n\n"
            "The second section says the strain SECRETWORDA tolerated 8 percent ethanol."}))
ids["paste"] = paste
doc = paste["documentId"]
cand = ok("candidate", call("POST", "/api/tools/biorepo_write", A, headers=WHO, json={
    "action": "candidate", "target": doc, "note": "A's candidate", "fields": {
        "paperId": doc, "sectionId": "p0", "field": "ethanol_titre", "value": "41", "unit": "g/L",
        "quote": "produced ethanol at a titre of 41 g/L from xylose", "organism": "strain-a",
        "carbonSource": "xylose", "method": "fed-batch"}}))
ids["record"] = ids["candidate"] = cand["summary"]["candidateId"]
ok("decision", call("POST", "/api/biorepo/decisions", A, json={
    "status": "verified", "provenance": "verified", "recordId": ids["record"], "at": AT, "reviewer": "alice"}))
ids["person"], ids["evidence"] = "p-a", "e-aaaa1"


def pa(v, u):
    return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": "alice", "at": AT}}


inputs = [{"name": k, "quantity": pa(v, u)} for k, v, u in (
    ("mu_max", 0.3, "h⁻¹"), ("ks", 0.5, "g L⁻¹"), ("yxs", 0.1, "g g⁻¹"), ("alpha", 4.0, "g g⁻¹"), ("yps", 0.45, "g g⁻¹"),
    ("p_max", 100.0, "g L⁻¹"), ("x0", 1.0, "g L⁻¹"), ("s0", 50.0, "g L⁻¹"), ("p0", 0.0, "g L⁻¹"))]
ids["kinetics_inputs"] = inputs
ids["run"] = ok("kinetics run", call("POST", "/api/engines/kinetics/run", A, json={"thing": "batch_v1", "by": "alice", "inputs": inputs}))["run"]["id"]
two = [dict(i) for i in inputs]
two[0] = {"name": "mu_max", "quantity": pa(0.25, "h⁻¹")}
ids["run2"] = ok("kinetics run 2", call("POST", "/api/engines/kinetics/run", A, json={"thing": "batch_v1", "by": "alice", "inputs": two}))["run"]["id"]
ids["artifacts"] = [a["id"] for a in j(call("GET", "/api/biorepo/artifacts", A))]
ids["comparison"] = ok("comparison", call("POST", "/api/studies/comparisons", A, json={
    "title": "A's comparison", "runIds": [ids["run"], ids["run2"]], "by": "alice"}))["comparison"]["id"]
ids["runbook"] = ok("runbook", call("POST", "/api/studies/runbooks", A, json={
    "title": "A's runbook", "runId": ids["run"], "by": "alice", "predict": [{"label": "end titre", "output": "values.end.P"}]}))["id"]
ok("lock", call("POST", f"/api/studies/runbooks/{ids['runbook']}/lock", A, json={"by": "alice"}))
ids["flowsheet"] = ok("sff library", call("POST", "/api/flowsheets/library/SF_BST_01", A, json={"by": "alice"}))["id"]
ok("proposal", call("POST", "/api/tools/biorepo_write", A, headers=WHO, json={
    "action": "publish", "target": ids["record"], "fields": {}, "note": "A's publish proposal"}))
ids["proposals"] = [p["id"] for p in j(call("GET", "/api/proposals", A))]
ids["scenario"] = ok("study scenario", call("POST", "/api/studies/scenarios", A, json={
    "title": "A's scenario", "plant": "cornstover", "by": "alice", "values": []}))["id"]
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
print(json.dumps({k: v for k, v in ids.items() if k != "kinetics_inputs"}))
