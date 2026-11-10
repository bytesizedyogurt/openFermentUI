"""Make a study runbook from a run, lock it, then try to move what the lock froze through every door that writes a
runbook row. Prints what each door answered and what the runbook reads as afterwards.

    python3 -I lock_probe.py ORIGIN PROJECT RUN_ID OUTPUT [OUTPUT...]
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api import call  # noqa: E402

sys.path.insert(0, "/home/user/openFermentUI/core")
from openferment_core.runbook_lock import lock_hash  # noqa: E402  the digest alone; no service, no database


def main(origin, project, run_id, *outputs):
    def api(method, path, body=None):
        s, out = call(origin, project, method, path, body)
        return s, out

    s, book = api("POST", "/api/studies/runbooks", {"title": "H2 lock probe", "runId": run_id, "by": "Hunter H2",
                                                   "predict": [{"output": o, "label": o} for o in outputs]})
    print("make", s, book.get("id") if isinstance(book, dict) else book)
    if s != 200:
        return
    rid = book["id"]
    s, locked = api("POST", f"/api/studies/runbooks/{rid}/lock", {"by": "Hunter H2"})
    print("lock", s, locked.get("lockedAt"), locked.get("lockHash"))
    frozen = (locked["lockedAt"], locked["lockHash"])
    print("digest recomputed here == served:", lock_hash(locked["predictions"], locked["measurementSchema"]) == locked["lockHash"])

    # 1. A prediction's value moved through the state door.
    moved = copy.deepcopy(locked)
    moved["predictions"][0]["value"] = moved["predictions"][0]["value"] * 2
    s, out = api("PUT", f"/api/state/runbooks/{rid}", {"by": "Hunter H2", "value": moved})
    print("PUT a moved prediction", s, str(out)[:200])

    # 2. The same predictions, with the lock's moment and digest rewritten on the row.
    forged = copy.deepcopy(locked)
    forged["lockedAt"] = "2020-01-01T00:00:00Z"
    forged["lockHash"] = "0000000000000000"
    s, out = api("PUT", f"/api/state/runbooks/{rid}", {"by": "Hunter H2", "value": forged})
    print("PUT the lock's moment and digest rewritten", s, str(out)[:200])
    s, now = api("GET", f"/api/studies/runbooks/{rid}")
    print("  GET after:", s, now.get("lockedAt"), now.get("lockHash"), "| lock froze", frozen)

    # 3. The row with the lock taken off it.
    bare = copy.deepcopy(locked)
    bare["lockedAt"] = None
    bare["lockHash"] = None
    s, out = api("PUT", f"/api/state/runbooks/{rid}", {"by": "Hunter H2", "value": bare})
    print("PUT the lock taken off the row", s, str(out)[:200])
    s, now = api("GET", f"/api/studies/runbooks/{rid}")
    print("  GET after:", s, now.get("lockedAt"), now.get("lockHash"))

    # 4. The locked runbook taken back through the state door, then asked for again.
    s, out = api("DELETE", f"/api/state/runbooks/{rid}?by=Hunter%20H2")
    print("DELETE the locked runbook", s, str(out)[:200])
    s, now = api("GET", f"/api/studies/runbooks/{rid}")
    print("  GET after:", s, str(now)[:200])
    s, again = api("POST", "/api/studies/runbooks", {"title": "H2 lock probe, again", "runId": run_id, "by": "Hunter H2",
                                                    "predict": [{"output": o, "label": o} for o in outputs]})
    print("  make again", s, again.get("lockedAt") if isinstance(again, dict) else again,
          again.get("lockHash") if isinstance(again, dict) else "")
    s, listed = api("GET", "/api/studies/runbooks")
    print("  listed:", [(b["id"], b.get("lockedAt")) for b in listed] if isinstance(listed, list) else listed)
    s, audit = api("GET", f"/api/audit?target={rid}")
    print("  audit:", [(a.get("action"), a.get("who"), a.get("state")) for a in audit] if isinstance(audit, list) else audit)


if __name__ == "__main__":
    main(*sys.argv[1:])
