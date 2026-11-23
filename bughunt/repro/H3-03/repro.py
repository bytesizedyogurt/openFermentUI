"""H3-03: a released measured value is rewritten by a later write, unaudited, and served as measured.

Run by run.sh against a fresh keyless service: bh_py -I repro.py ORIGIN. Project p1 must exist.
The steps: a runbook, a closed and reconciled deposition (its reading 40 g/L), the measured evidence its
reconciliation released (40 g/L, by Ada Lovelace), then the same evidence id written again with 400 g/L by
another person. A rewrite of the deposition's own reading is tried first, as the contrast the service holds.
Prints the facts, then H303_VERDICT: DEFECT or H303_VERDICT: NO-DEFECT.
"""
from __future__ import annotations

import json
import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
P1 = {"X-OpenFerment-Project": "p1"}
ADA, OTHER = "Ada Lovelace", "Someone Else"
T0, T1 = "2026-11-09T10:00:00Z", "2026-11-09T12:00:00Z"


def put(kind, rid, value, by=ADA):
    r = c.put(f"/api/state/{kind}/{rid}", json={"by": by, "value": value}, headers=P1)
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        body = r.text
    return r.status_code, body


def short(body):
    return json.dumps(body, ensure_ascii=False)[:220]


runbook = {"id": "rb1", "kind": "research", "title": "Bench check", "status": "draft",
           "measurementSchema": [{"id": "m1", "label": "Ethanol titre", "unit": "g/L", "timepoint": "harvest"}]}
print("[1 runbook rb1]", put("runbooks", "rb1", runbook)[0])

e1 = {"id": "e1", "measureId": "m1", "stepId": "readings", "at": T0, "value": 40.0, "unit": "g/L",
      "raw": "40 g/L", "confirmed": True}
dep = {"id": "dep1", "runbookId": "rb1", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": T1,
       "state": "closed", "observations": [], "sampleTimes": {}, "entries": [e1],
       "reconciliation": {"at": T1, "outcome": "inconclusive", "note": "",
                          "deltas": [{"predictionId": "p1", "predicted": 45.0, "observed": 40.0, "unit": "g/L",
                                      "pctDelta": -11.1}]}}
print("[2 deposition dep1, closed and reconciled, reading e1 40 g/L]", put("depositions", "dep1", dep)[0])

st, body = put("depositions", "dep1", {**dep, "entries": [{**e1, "value": 400.0, "raw": "400 g/L"}]}, by=OTHER)
dep_held = st == 422
print(f"[3 contrast: rewrite dep1's reading e1 to 400 g/L by {OTHER}] {st} {short(body)}")

me = {"id": "me1", "depositionId": "dep1", "runbookId": "rb1", "productId": None, "predictionId": "p1",
      "label": "Ethanol titre", "value": 40.0, "unit": "g/L", "provenance": "measured",
      "conditions": {"protocolId": None, "scale": 1, "strainId": None}, "deviations": [], "confirmed": True, "at": T1}
st1, b1 = put("measuredEvidence", "me1", me)
print(f"[4 release measured evidence me1, 40 g/L, by {ADA}] {st1} value {b1.get('value', {}).get('value') if isinstance(b1, dict) else b1}")
st2, b2 = put("measuredEvidence", "me1", {**me, "value": 400.0}, by=OTHER)
print(f"[5 write me1 again, 400 g/L, by {OTHER}] {st2} {short(b2)}")

state = c.get("/api/state", headers=P1).json()
kept = {m["id"]: m for m in state.get("measuredEvidence", [])}.get("me1", {})
dep_kept = {d["id"]: d for d in state.get("depositions", [])}.get("dep1", {})
observed_in_rec = [d.get("observed") for d in (dep_kept.get("reconciliation") or {}).get("deltas", [])]
e1_kept = [e.get("value") for e in dep_kept.get("entries", []) if e.get("id") == "e1"]
print(f"[6 GET /api/state] me1 value {kept.get('value')} provenance {kept.get('provenance')} confirmed "
      f"{kept.get('confirmed')}; dep1 reading e1 {e1_kept}, its reconciliation observed {observed_in_rec}")

audit = c.get("/api/audit", params={"target": "me1"}, headers=P1).json()
rows = [(a.get("action"), a.get("who"), a.get("target")) for a in audit]
print(f"[7 GET /api/audit?target=me1] {len(rows)} row(s): {rows}")

read = c.post("/api/tools/runbooks_read", params={"by": ADA},
              json={"ids": ["runbooks/measured-evidence/me1"], "words": "", "kind": "", "state": "",
                    "limit": 5}, headers=P1).json()
mrows = read.get("rows") or (read.get("summary") or {}).get("rows") or []
mrow = next((r for r in mrows if str(r.get("ref", "")).endswith("measured-evidence/me1")
             or (r.get("kind") == "measured-evidence" and r.get("id") == "me1")), {})
print(f"[8 runbooks_read runbooks/measured-evidence/me1] provenance {mrow.get('provenance')} value "
      f"{(mrow.get('detail') or {}).get('value')} {(mrow.get('detail') or {}).get('unit')}")
if not mrow:
    print("   (no row; the tool answered " + short(read) + ")")

r = c.delete("/api/state/measuredEvidence/me1", params={"by": OTHER}, headers=P1)
print(f"[9 DELETE me1] {r.status_code} {short(r.json())}")

overwrote = st1 == 200 and st2 == 200 and kept.get("value") == 400.0
unaudited = not any(w == OTHER for _, w, _ in rows) and len(rows) <= 1
served = mrow.get("provenance") == "measured" and (mrow.get("detail") or {}).get("value") == 400.0
print("EXPECTED: the second write of me1 (40 to 400 g/L, by another person) is refused in words with a 422, as "
      "the deposition's own reading is at step 3, or at the least it leaves an audit row naming who changed it; "
      "the reads keep 40 g/L, the value the reconciliation observed")
print(f"OBSERVED: deposition rewrite {'refused 422' if dep_held else 'accepted'}; me1 rewrite answered {st2}; "
      f"GET /api/state keeps me1 at {kept.get('value')} g/L marked {kept.get('provenance')}; audit for me1 holds "
      f"{rows}; runbooks_read serves me1 as {mrow.get('provenance')} {(mrow.get('detail') or {}).get('value')} g/L; "
      f"dep1's reconciliation still says observed {observed_in_rec}")
print("H303_VERDICT:", "DEFECT" if (overwrote and unaudited) else "NO-DEFECT",
      f"(overwrote={overwrote} unaudited={unaudited} served_as_measured={served})")
