"""Project bh-a, part five: a proposal (a gated write through the tool door), a fermOS simulation through its
route, measured evidence, and a study scenario on a library plant (starts the BioSTEAM worker)."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j, show

A = "bh-a"
AT = "2026-11-10T07:00:00Z"
ids = json.load(open(f"{OUT}/a_ids.json"))


def ok(label, r, n=500):
    show(label, r, n)
    return j(r)


who = {"X-OpenFerment-Assistant": "bh-h5-agent/0.1"}
p = ok("proposal", call("POST", "/api/tools/biorepo_write", A, headers=who, json={
    "action": "publish", "target": ids["record"], "fields": {}, "note": "A's publish proposal"}))
props = ok("proposals", call("GET", "/api/proposals", A))
ids["proposals"] = [x["id"] for x in props] if isinstance(props, list) else []
me = {"id": "me-a", "runbookId": "rb-a", "depositionId": "dep-a", "at": AT, "by": "alice"}
ok("measuredEvidence", call("PUT", "/api/state/measuredEvidence/me-a", A, json={"by": "alice", "value": me}))
sc = ok("study scenario", call("POST", "/api/studies/scenarios", A, json={
    "title": "A's scenario", "plant": "cornstover", "by": "alice", "values": []}))
ids["scenario"] = sc.get("id") if isinstance(sc, dict) else None
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
