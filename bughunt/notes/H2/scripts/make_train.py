"""Make a train from a kept library run, as scripts/prove.py `make_train` makes one through the Builder's routes.

    python3 -I make_train.py ORIGIN PROJECT RUN_ARTIFACT_ID PERSON > train.json

Every call goes through the service's routes (from-run, check, PUT /api/state/trains/<id>); it prints the train saved.
The words matched (`CANNOT_BUILD`, the waiting pattern) are copied from the tree's pureos modules at 2047f5a.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api import call  # noqa: E402

WAITING = re.compile(r"\bwaits (\(|for\b)")


def main(origin, project, reference, person):
    sys.path.insert(0, "/home/user/openFermentUI/core")
    from openferment_core.pureos.train_spec import CANNOT_BUILD  # words alone; this imports no simulator

    def api(method, path, body=None):
        status, out = call(origin, project, method, path, body)
        if status >= 400:
            raise SystemExit(f"{method} {path}: {status} {out}")
        return out

    read = api("POST", "/api/pureos/train/from-run", {"artifactId": reference})
    train = read["train"]
    ins = {u["id"]: u["ins"] for u in api("GET", f"/api/biorepo/artifacts/{reference}")["output"]["units"]}

    def from_unit(n):
        if n == 0:
            return train
        first = train["units"][n]
        return {**train, "name": f"{train['name']}, from {first['id']} on", "units": train["units"][n:],
                "inlet": {**train["inlet"], "streamId": ins[first["id"]][0]}}

    def check(tail):
        return api("POST", "/api/pureos/train/check", {"train": tail, "by": person})

    head = 0
    checked = check(train)
    while (not checked["ok"] and any(CANNOT_BUILD in w for w in checked["places"].get("inlet") or [])
           and head + 1 < len(train["units"])):
        head += 1
        checked = check(from_unit(head))
    tail = from_unit(head)
    waiting = [n for n, u in enumerate(tail["units"]) if checked["places"].get(u["id"])]
    kept = tail["units"][max(waiting) + 1:] if waiting else tail["units"]
    made = from_unit(len(train["units"]) - len(kept))
    again = check(made)
    print(json.dumps({"ok": again["ok"], "refusals": again.get("refusals")}), file=sys.stderr)
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    api("PUT", f"/api/state/trains/{made['id']}", {"by": person, "value": {"train": made, "savedAt": at, "by": person}})
    print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
