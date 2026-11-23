"""H5-04 (with H2-04): a locked study runbook taken back through DELETE /api/state/runbooks/{id}, then made again.

    ORIGIN=http://127.0.0.1:PORT python -I locked_back.py

One project, one kinetics run on person assumptions (no model, no network), one study runbook of that run,
locked. Then: the lock's own DELETE (the refusal a lock gets), the runbook's DELETE, what the doors read
afterwards, the same runbook made again, and the audit. Prints EXPECTED, OBSERVED and RESULT lines.
"""
import os
import sys

import httpx

ORIGIN = os.environ["ORIGIN"]
P = "h504-a"
BY = "alice"
AT = "2026-11-10T07:00:00Z"
C = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": P})


def call(method, path, **kw):
    r = C.request(method, path, **kw)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


def need(label, got, want=200):
    s, body = got
    if s != want:
        print(f"setup stopped at {label}: {s} {str(body)[:300]}")
        print("RESULT: NO-DEFECT")
        sys.exit(0)
    return body


def pa(v, u):
    return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": BY, "at": AT}}


# Setup: a project, a kinetics run, a study runbook of it, locked.
s, _ = call("POST", "/api/projects", json={"id": P, "name": P, "by": BY})
print("project", s)
inputs = [{"name": k, "quantity": pa(v, u)} for k, v, u in (
    ("mu_max", 0.3, "h⁻¹"), ("ks", 0.5, "g L⁻¹"), ("yxs", 0.1, "g g⁻¹"), ("alpha", 4.0, "g g⁻¹"),
    ("yps", 0.45, "g g⁻¹"), ("p_max", 100.0, "g L⁻¹"), ("x0", 1.0, "g L⁻¹"), ("s0", 50.0, "g L⁻¹"),
    ("p0", 0.0, "g L⁻¹"))]
run = need("kinetics run", call("POST", "/api/engines/kinetics/run",
                                json={"thing": "batch_v1", "by": BY, "inputs": inputs}))["run"]
print("kinetics run", run["id"], run["status"])
ask = {"title": "H5-04 runbook", "runId": run["id"], "by": BY,
       "predict": [{"label": "end titre", "output": "values.end.P"}]}
book = need("make", call("POST", "/api/studies/runbooks", json=ask))
rid = book["id"]
print("make", rid, "lockedAt", book.get("lockedAt"))
locked = need("lock", call("POST", f"/api/studies/runbooks/{rid}/lock", json={"by": BY}))
frozen = (locked["lockedAt"], locked["lockHash"])
print("lock", frozen, "predictions", [(p["id"], p["value"], p["unit"]) for p in locked["predictions"]])

# The refusal a lock gets at the same door.
s_lock, b_lock = call("DELETE", f"/api/state/runbookLocks/{rid}", params={"by": BY})
print(f"DELETE /api/state/runbookLocks/{rid}: {s_lock} {str(b_lock)[:160]}")

# 1. The locked runbook taken back.
s_del, b_del = call("DELETE", f"/api/state/runbooks/{rid}", params={"by": BY})
print(f"DELETE /api/state/runbooks/{rid}: {s_del} {str(b_del)[:200]}")
s_get, b_get = call("GET", f"/api/studies/runbooks/{rid}")
print(f"  GET /api/studies/runbooks/{rid}: {s_get} {str(b_get)[:160]}")
s_ls, listed = call("GET", "/api/studies/runbooks")
in_list = [b["id"] for b in listed] if isinstance(listed, list) else listed
print("  GET /api/studies/runbooks lists:", in_list)
s_st, state = call("GET", "/api/state")
lock_left = state.get("runbookLocks", {}).get(rid) if isinstance(state, dict) else None
rows_left = [r for r in (state.get("runbooks") or {})] if isinstance(state, dict) else []
print("  GET /api/state runbooks:", rows_left, "| runbookLocks[rid]:", lock_left)
moved = {**locked, "predictions": [{**locked["predictions"][0], "value": locked["predictions"][0]["value"] * 2}]}
s_put, b_put = call("PUT", f"/api/state/runbooks/{rid}", json={"by": BY, "value": moved})
print(f"  PUT /api/state/runbooks/{rid} with a moved prediction (the lock left behind still guards a write): "
      f"{s_put} {str(b_put)[:160]}")

# 2. The same run and outputs asked again.
s_again, again = call("POST", "/api/studies/runbooks", json={**ask, "title": "H5-04 runbook, made again"})
again_lock = (again.get("lockedAt"), again.get("lockHash")) if isinstance(again, dict) else (None, None)
print(f"POST /api/studies/runbooks again: {s_again} id {again.get('id') if isinstance(again, dict) else again} "
      f"lockedAt {again_lock[0]} lockHash {again_lock[1]}")
s_get2, b_get2 = call("GET", f"/api/studies/runbooks/{rid}")
get2_lock = (b_get2.get("lockedAt"), b_get2.get("lockHash")) if isinstance(b_get2, dict) else (None, None)
print(f"  GET /api/studies/runbooks/{rid}: {s_get2} lockedAt {get2_lock[0]} lockHash {get2_lock[1]}")
s_ls2, listed2 = call("GET", "/api/studies/runbooks")
print("  GET /api/studies/runbooks lists:",
      [(b["id"], b.get("lockedAt"), b.get("lockHash")) for b in listed2] if isinstance(listed2, list) else listed2)
s_au, audit = call("GET", "/api/audit", params={"target": rid})
print("  audit:", [(a.get("action"), a.get("who"), a.get("state")) for a in audit] if isinstance(audit, list) else audit)

taken_back = s_del == 200 and s_get == 404 and lock_left is not None
answers_differ = s_again == 200 and again_lock == (None, None) and get2_lock == frozen
print()
print("EXPECTED: (1) DELETE /api/state/runbooks/<id> of a locked runbook refused in words (422), as "
      f"DELETE /api/state/runbookLocks/<id> is ({s_lock}), the runbook still served with its frozen predictions; "
      "(2) a make of the same run and outputs answering the runbook with its lock, as GET and the listing do")
print(f"OBSERVED: (1) DELETE {s_del} {b_del}; GET /api/studies/runbooks/{rid} {s_get}; the lock still kept in "
      f"runbookLocks: {lock_left}")
print(f"OBSERVED: (2) the make again answers lockedAt {again_lock[0]} lockHash {again_lock[1]}; "
      f"GET answers lockedAt {get2_lock[0]} lockHash {get2_lock[1]}")
print(f"part 1 (taken back, lock left behind): {'DEFECT' if taken_back else 'no defect'}; "
      f"part 2 (make answers unlocked, reads answer locked): {'DEFECT' if answers_differ else 'no defect'}")
print("RESULT: DEFECT" if taken_back else "RESULT: NO-DEFECT")
