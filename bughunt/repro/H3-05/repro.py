"""H3-05: a series correction is undone by a later write that moves a sample time.

Run by run.sh against a fresh keyless service: python -I repro.py ORIGIN. Project p1 must exist and hold
nothing else. The steps, each a request to the service:

  A. the candidate's path, a reading in a series
     1. runbook rb1 with one measure m1 (ethanol titre, g/L)
     2. deposition dep9, running: s1 4.0 g/L (a mis-read), confirmed, sample time 5 h
     3. the bench's correction (store amendEntry): s2 40.0 g/L, confirmed, correctedAt, raw "... -> corrected to
        40.0 g/L", the sample time carried across (5 h)
     4. the Proforma parameter resolve on dep9/s1, and the readings list for a titre
     5. a write that moves s2 to 6 h (dep9 is still open)
     6. the resolve on dep9/s1 again, and the readings list again
     7. a write that takes s1's sample time away, and the resolve on dep9/s1 once more
  B. the docstring's own write ("give an open deposition's readings their sample times")
     8. deposition dep10: s1 4.0 g/L with no time, corrected by s2 40.0 g/L with no time
     9. the resolve on dep10/s1 (refused), then a write that gives s2 alone its 5 h, then the resolve again

Prints the facts, then H305_VERDICT: DEFECT or NO-DEFECT (A decides; B is reported beside it).
"""
from __future__ import annotations

import copy
import json
import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=120)
P1 = {"X-OpenFerment-Project": "p1"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"
T1 = "2026-11-09T11:00:00Z"
SCOPE = "/api/params/proforma:sc-h305/resolve"


def short(r, n=200):
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        body = r.text
    return f"{r.status_code} {json.dumps(body, ensure_ascii=False)[:n]}"


def put(kind, rid, value):
    return c.put(f"/api/state/{kind}/{rid}", json={"by": ADA, "value": value}, headers=P1)


def resolve(ref, value):
    return c.post(SCOPE, headers=P1, json={"flowsheet": "ethanol_glucose_v0", "inputs": [
        {"name": "titre", "quantity": {"value": value, "unit": "g/L", "origin": {"kind": "measurement", "ref": ref}}}]})


def titre_of(r):
    """The titre the resolve set, as (value, origin, source kind, source id); None when refused."""
    if r.status_code != 200:
        return None
    t = next((x for x in r.json().get("values", []) if x.get("key") == "titre"), None)
    if t is None:
        return ("no titre row",)
    src = t.get("source") or {}
    return (t.get("value"), t.get("origin"), src.get("kind"), src.get("id"))


def offered(dep_id):
    rows = c.get("/api/depositions/readings", params={"unit": "g L-1"}, headers=P1).json()
    return [(x["ref"], x["value"], x["hours"]) for x in rows if x["depositionId"] == dep_id]


def entry(eid, value, raw=None, corrected=None):
    e = {"id": eid, "measureId": "m1", "stepId": "readings", "at": T0, "value": value, "unit": "g/L",
         "raw": raw or f"{value} g/L", "confirmed": True}
    if corrected:
        e["correctedAt"] = corrected
    return e


def deposition(dep_id, entries, times):
    return {"id": dep_id, "runbookId": "rb1", "protocolId": None, "operatorId": None, "startedAt": T0,
            "closedAt": None, "state": "running", "observations": [], "reconciliation": None,
            "entries": entries, "sampleTimes": times}


rb = {"id": "rb1", "kind": "research", "title": "Bench check", "status": "draft",
      "measurementSchema": [{"id": "m1", "label": "Ethanol titre", "unit": "g/L", "timepoint": "harvest"}]}
print(f"[1 runbook rb1, measure m1 ethanol titre g/L] {short(put('runbooks', 'rb1', rb), 60)}")

print("== A. a reading in a series ==")
s1 = entry("s1", 4.0)
s2 = entry("s2", 40.0, raw="4.0 g/L -> corrected to 40.0 g/L", corrected=T1)
d = deposition("dep9", [s1], {"s1": 5.0})
print(f"[2 deposit dep9: s1 4.0 g/L at 5 h, confirmed] {short(put('depositions', 'dep9', d), 60)}")
d = deposition("dep9", [s1, s2], {"s1": 5.0, "s2": 5.0})
print(f"[3 correct s1 by s2 40.0 g/L, the 5 h carried across] {short(put('depositions', 'dep9', d), 60)}")
r4 = resolve("dep9/s1", 4.0)
o4 = offered("dep9")
print(f"[4 resolve titre on dep9/s1] {short(r4)}")
print(f"   readings offered for a titre from dep9: {o4}")
d5 = copy.deepcopy(d)
d5["sampleTimes"] = {"s1": 5.0, "s2": 6.0}
w5 = put("depositions", "dep9", d5)
print(f"[5 move s2 to 6 h, dep9 still running] {short(w5, 60)}")
r6 = resolve("dep9/s1", 4.0)
o6 = offered("dep9")
print(f"[6 resolve titre on dep9/s1 again] {r6.status_code}; titre (value, origin, source kind, source id) = "
      f"{titre_of(r6)}" + ("" if r6.status_code == 200 else f" {short(r6)}"))
print(f"   readings offered for a titre from dep9: {o6}")
d7 = copy.deepcopy(d5)
d7["sampleTimes"] = {"s2": 6.0}
w7 = put("depositions", "dep9", d7)
r7 = resolve("dep9/s1", 4.0)
print(f"[7 take s1's sample time away] {short(w7, 60)}; resolve on dep9/s1 {r7.status_code} titre = {titre_of(r7)}")

print("== B. a correction with no time, then given a sample time ==")
t1, t2 = entry("s1", 4.0), entry("s2", 40.0, raw="4.0 g/L -> corrected to 40.0 g/L", corrected=T1)
put("depositions", "dep10", deposition("dep10", [t1], {}))
w8 = put("depositions", "dep10", deposition("dep10", [t1, t2], {}))
r8 = resolve("dep10/s1", 4.0)
print(f"[8 dep10: s1 4.0 g/L, corrected by s2 40.0 g/L, neither timed] {short(w8, 60)}; resolve on dep10/s1 "
      f"{short(r8)}")
w9 = put("depositions", "dep10", deposition("dep10", [t1, t2], {"s2": 5.0}))
r9 = resolve("dep10/s1", 4.0)
print(f"[9 give s2 alone its 5 h] {short(w9, 60)}; resolve on dep10/s1 {r9.status_code} titre = {titre_of(r9)}; "
      f"offered {offered('dep10')}")

held_first = r4.status_code == 422 and "corrected by dep9/s2" in r4.text and not any(x[0] == "dep9/s1" for x in o4)
undone = (w5.status_code == 200 and r6.status_code == 200 and (titre_of(r6) or (None,))[0] == 4.0
          and any(x[0] == "dep9/s1" for x in o6))
b_undone = r8.status_code == 422 and w9.status_code == 200 and r9.status_code == 200
print(f"H305_VERDICT: {'DEFECT' if held_first and undone else 'NO-DEFECT'} (A: refused while corrected "
      f"{held_first}, taken after the move {undone}; B: taken after a time is given {b_undone})")
