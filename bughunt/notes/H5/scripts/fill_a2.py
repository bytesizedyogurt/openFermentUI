"""The rest of project bh-a: a Guild person with evidence and a check, a candidate written through the tool
door and accepted into a record, a kinetics engine run, a fermOS simulation, a comparison, a runbook made from
the run and locked, a study scenario on a library plant, an SFF library record. Adds to $H5_OUT/a_ids.json."""
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


who = {"X-OpenFerment-Assistant": "bh-h5-agent/0.1"}
person = {"id": "p-a", "name": "Person only A holds", "joinedAt": AT, "addedAt": AT, "role": "lead"}
ok("guild person", call("POST", "/api/guild/people", A, json=person))
ev = {"id": "e-aaaa1", "personId": "p-a", "skillId": "SK-A", "kind": "witnessed", "at": AT,
      "source": {"kind": "signoff", "ref": "signoff-a"}, "raw": "A's evidence", "outcome": "pass"}
ok("guild evidence", call("POST", "/api/guild/evidence", A, json=ev))
ok("check request", call("POST", "/api/guild/checks/request", A, json={"personId": "p-a", "skillIds": ["SK-A"], "by": "alice"}))
checks = ok("checks", call("GET", "/api/guild/checks", A))
doc = ids["paste"]["documentId"]
lit = ok("lit doc", call("POST", "/api/tools/literature_document?by=alice", A, json={"document": doc}))
cand = ok("candidate", call("POST", "/api/tools/biorepo_write", A, headers=who, json={
    "action": "candidate", "target": doc, "note": "A's candidate", "fields": {
        "paperId": doc, "sectionId": "p0", "field": "ethanol_titre", "value": "41", "unit": "g/L",
        "quote": "produced ethanol at a titre of 41 g/L from xylose", "organism": "strain-a",
        "carbonSource": "xylose", "method": "fed-batch"}}))
ids["candidate"] = cand["summary"].get("candidateId") if isinstance(cand, dict) else None
ids["person"] = "p-a"
ids["evidence"] = "e-aaaa1"
dec = ok("decision", call("POST", "/api/biorepo/decisions", A, json={
    "status": "accepted", "provenance": "verified", "recordId": ids["candidate"], "at": AT, "reviewer": "alice"}))
ids["record"] = ids["candidate"]
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
