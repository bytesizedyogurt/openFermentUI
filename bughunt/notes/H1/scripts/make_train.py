"""A train made in a project as a person makes one in pureOS's Builder, following scripts/prove.py's
make_train: a cornstover library run, read into a train (POST /api/pureos/train/from-run), its head units
taken out while the check refuses its inlet, the waiting units taken out, checked, saved (PUT
/api/state/trains/<id>). Prints the train's id. usage: make_train.py ORIGIN PROJECT"""
import sys, time
import httpx
from openferment_core.pureos.engine import WAITING
from openferment_core.pureos.train_spec import CANNOT_BUILD

O, P = sys.argv[1], sys.argv[2]
PERSON = "H1 hunter"
c = httpx.Client(trust_env=False, timeout=900, headers={"X-OpenFerment-Project": P})


def api(m, path, body=None):
    r = c.request(m, O + path, json=body)
    r.raise_for_status()
    return r.json()


ref = api("POST", "/api/engines/biosteam/run", {"thing": "cornstover", "by": PERSON})["run"]["artifactId"]
read = api("POST", "/api/pureos/train/from-run", {"artifactId": ref})
train = read["train"]
ins = {u["id"]: u["ins"] for u in api("GET", f"/api/biorepo/artifacts/{ref}")["output"]["units"]}


def from_unit(n):
    if n == 0:
        return train
    first = train["units"][n]
    return {**train, "name": f"{train['name']}, from {first['id']} on", "units": train["units"][n:],
            "inlet": {**train["inlet"], "streamId": ins[first["id"]][0]}}


def check(tail):
    return api("POST", "/api/pureos/train/check", {"train": tail, "by": PERSON})


head, checked = 0, check(train)
while (not checked["ok"] and any(CANNOT_BUILD in w for w in checked["places"].get("inlet") or [])
       and head + 1 < len(train["units"])):
    head += 1
    checked = check(from_unit(head))
tail = from_unit(head)
waiting = [n for n, u in enumerate(tail["units"]) if checked["places"].get(u["id"])]
kept = tail["units"][max(waiting) + 1:] if waiting else tail["units"]
made = from_unit(len(train["units"]) - len(kept))
again = check(made)
print("check ok:", again["ok"], again.get("refusals"), file=sys.stderr)
at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
api("PUT", f"/api/state/trains/{made['id']}", {"by": PERSON, "value": {"train": made, "savedAt": at, "by": PERSON}})
print(made["id"])
