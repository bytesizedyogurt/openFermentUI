"""Fill project bh-a with one of everything a person can make without a model, and write what was made
to $H5_OUT/a_ids.json for the cross-project probes. Run with bh_py against a service bh_svc_start began."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j, show

A = "bh-a"
AT = "2026-11-10T07:00:00Z"
ids = {}


def ok(label, r):
    show(label, r, 300)
    return j(r)


POLICY = {"criticality": "routine", "recencyDays": 30, "supervisedRuns": 1}
ok("skill", call("POST", "/api/catalogues/skill", A, json={"by": "alice", "entry": {
    "kind": "skill", "id": "SK-A", "name": "Skill only A holds", "family": "placeholder", "mastery": ["criterion"], **POLICY}}))
ok("strain", call("POST", "/api/catalogues/strain", A, json={"by": "alice", "entry": {
    "kind": "strain", "id": "strain-a", "name": "Strain only A holds", "species": "Placeholder species A",
    "aliases": ["SECRET-ALIAS-A"]}}))
ok("product", call("POST", "/api/catalogues/product", A, json={"by": "alice", "entry": {
    "kind": "product", "id": "product-a", "name": "Product only A holds", "category": "industrial_enzyme"}}))
ok("lesson", call("POST", "/api/catalogues/lesson", A, json={"by": "alice", "entry": {
    "kind": "lesson", "id": "lesson-a", "name": "Lesson only A holds", "skills": ["SK-A"]}}))
ids["catalogue"] = {"skill": "SK-A", "strain": "strain-a", "product": "product-a", "lesson": "lesson-a"}

version = {"version": "1.0", "baseBatch": {"value": 1, "unit": "placeholder-unit", "label": "batch"},
           "materials": [{"name": "Material A", "amount": 2.5, "unit": "placeholder-unit", "scaling": "fixed",
                          "precision": 0.5}],
           "steps": [{"id": "s1", "text": "Add {{qty:Material A}}.", "skills": ["SK-A"]}],
           "estMinutes": {"active": 1, "total": 2}}
proto = {"id": "PR-A", "title": "Protocol only A holds", "category": "sop", "bsl": 1, "organisms": ["Placeholder"],
         "purpose": "A's purpose", "currentVersion": "1.0", "versions": [version]}
ok("protocol", call("POST", "/api/protocols", A, json={"protocol": proto, "by": "alice"}))
ids["protocol"] = "PR-A"

ENTRY = {"id": "de-a1", "measureId": "m-a1", "stepId": "s-1", "at": AT, "value": 7.2, "unit": "g/L",
         "raw": "A's reading", "confirmed": True}
DEP = {"id": "dep-a", "runbookId": "rb-a", "protocolId": None, "operatorId": None, "startedAt": AT,
       "closedAt": None, "state": "running", "entries": [ENTRY], "observations": [], "reconciliation": None}
ok("deposition", call("PUT", "/api/state/depositions/dep-a", A, json={"by": "alice", "value": DEP}))
TRAIN = {"train": {"id": "tr-a", "name": "Train only A holds", "program": "placeholder", "product": "product-a",
                   "inlet": {"kind": "typed"}, "units": []}, "savedAt": AT, "by": "alice"}
ok("train", call("PUT", "/api/state/trains/tr-a", A, json={"by": "alice", "value": TRAIN}))
LIVE = {"id": "lc-a", "title": "A's private question", "startedAt": AT,
        "turns": [{"id": "turn-a", "question": "A's private question", "askedAt": AT, "steps": [],
                   "plan": None, "error": None, "status": "answered"}]}
ok("conversation", call("PUT", "/api/state/conversations/lc-a", A, json={"by": "alice", "value": LIVE}))
ok("fits", call("PUT", "/api/state/fits/sc-a", A, json={"by": "alice", "value": {"mu_max": "0123456789abcdef"}}))
price = {"scope": "proforma:sc-a", "key": "price", "value": 1.2, "by": "alice", "at": AT}
ok("overrides", call("PUT", "/api/state/overrides/proforma:sc-a", A, json={"by": "alice", "value": [price]}))
ids["state"] = {"depositions": "dep-a", "trains": "tr-a", "conversations": "lc-a", "fits": "sc-a",
                "overrides": "proforma:sc-a", "turn": "turn-a"}

person = {"id": "per-a", "name": "Person only A holds", "joinedAt": AT, "addedAt": AT, "role": "tech"}
ok("guild person", call("POST", "/api/guild/people", A, json=person))
ids["person"] = "per-a"

paste = ok("paste", call("POST", "/api/intake/paste", A, json={
    "title": "A secret paper", "by": "alice",
    "text": "Zymomonas xylofermentans SECRETWORDA produced ethanol at a titre of 41 g/L from xylose in "
            "fed-batch culture.\n\nThe second section says the strain SECRETWORDA tolerated 8 percent ethanol."}))
ids["paste"] = paste
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
print(json.dumps(ids, indent=1))
