"""Project bh-a, part four: a second kinetics run, a comparison of the two, a runbook from the first and its
lock, an SFF library record, a study scenario on a library plant, a fermOS fit choice. Adds to a_ids.json."""
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


if False:
    inputs2 = [dict(i) for i in ids["kinetics_inputs"]]
    inputs2[0] = {"name": "mu_max", "quantity": {**inputs2[0]["quantity"], "value": 0.25}}
    run2 = ok("kinetics run 2", call("POST", "/api/engines/kinetics/run", A, json={"thing": "batch_v1", "by": "alice",
                                                                                   "inputs": inputs2}), 200)
    ids["run2"] = run2["run"]["id"]
    comp = ok("comparison", call("POST", "/api/studies/comparisons", A, json={
        "title": "A's comparison", "runIds": [ids["run"], ids["run2"]], "by": "alice"}), 300)
    ids["comparison"] = comp.get("id") or comp.get("comparison", {}).get("id")
    print("comparison keys", list(comp.keys()))
    outs = run2["run"]["outputs"]
    print("outputs", json.dumps(outs)[:600])
rb = ok("runbook", call("POST", "/api/studies/runbooks", A, json={
    "title": "A's runbook", "runId": ids["run"], "by": "alice",
    "predict": [{"label": "end titre", "output": "end.P"}]}), 300)
ids["runbook"] = rb.get("id")
lock = ok("lock", call("POST", f"/api/studies/runbooks/{ids['runbook']}/lock", A, json={"by": "alice"}), 300)
sff = ok("sff library", call("POST", "/api/flowsheets/library/SF_BST_01", A, json={"by": "alice"}), 300)
ids["flowsheet"] = sff.get("id") if isinstance(sff, dict) else None
json.dump(ids, open(f"{OUT}/a_ids.json", "w"), indent=1)
