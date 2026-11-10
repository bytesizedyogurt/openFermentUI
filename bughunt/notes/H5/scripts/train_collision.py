"""H5: a model's kept train (trains, kind kept) and a person's saved train (kind made) share one key. Within
bh-a: the model lane starts a kept train through pureos_build; a person then PUTs a made train under its id."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import OUT, call, j

A = "bh-a"
ids = json.load(open(f"{OUT}/a_ids.json"))
who = {"X-OpenFerment-Assistant": "bh-h5-agent/0.1"}
r = j(call("POST", "/api/tools/pureos_build", A, headers=who, json={"action": "new", "product": "ethanol",
                                                                    "inletRef": ids["run"]}))
print("pureos_build new:", json.dumps(r)[:400])
tid = (r.get("summary") or {}).get("trainId")
kept = j(call("GET", "/api/pureos/trains-kept", A))
print("kept trains before:", [k.get("id") or k.get("train", {}).get("id") for k in kept] if isinstance(kept, list) else kept)
if tid:
    made = {"train": {"id": tid, "name": "A person's train under the model's id", "program": "placeholder",
                      "product": "x", "inlet": {"kind": "typed"}, "units": []},
            "savedAt": "2026-11-10T07:00:00Z", "by": "alice"}
    p = call("PUT", f"/api/state/trains/{tid}", A, json={"by": "alice", "value": made})
    print("PUT /api/state/trains:", p.status_code, p.text[:200])
    kept = j(call("GET", "/api/pureos/trains-kept", A))
    print("kept trains after:", [k.get("id") or k.get("train", {}).get("id") for k in kept] if isinstance(kept, list) else kept)
    print("state trains:", list(j(call("GET", "/api/state", A))["trains"]))
