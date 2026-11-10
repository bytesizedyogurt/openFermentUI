"""H3-15: a deposition write that appends a second entry under an id an earlier entry holds is kept.

Run by run.sh against a fresh keyless service: python -I repro.py ORIGIN. Project p1 must exist and hold
nothing else. The steps: deposition depD written with one confirmed reading d1 (10 g/L, measure mz); the
same deposition written again with a second entry also under id d1 (99 g/L, measure other); the state
read back; the readings a run may take listed in g/L. Two further lines show the same hole on one measure
(depE: d1 at 10 g/L, then d1 again at 12 g/L on mz) and on a first write (depF made with two entries under
d1). Prints the facts, then H315_VERDICT: DEFECT or NO-DEFECT (decided by depD alone).
"""
from __future__ import annotations

import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
P1 = {"X-OpenFerment-Project": "p1"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"


def entry(eid: str, v: float, m: str = "mz") -> dict:
    return {"id": eid, "measureId": m, "stepId": "readings", "at": T0, "value": v, "unit": "g/L",
            "raw": f"{v} g/L", "confirmed": True}


def deposition(did: str, entries: list[dict]) -> dict:
    return {"id": did, "runbookId": "rbD", "protocolId": None, "operatorId": None, "startedAt": T0,
            "closedAt": None, "state": "running", "observations": [], "reconciliation": None,
            "sampleTimes": {}, "entries": entries}


def put(dep: dict) -> httpx.Response:
    return c.put(f"/api/state/depositions/{dep['id']}", json={"by": ADA, "value": dep}, headers=P1)


def kept(did: str) -> list[tuple]:
    deps = c.get("/api/state", headers=P1).json().get("depositions") or []
    d = next((x for x in deps if x.get("id") == did), {})
    return [(x.get("id"), x.get("value"), x.get("measureId")) for x in d.get("entries") or []]


def offered(did: str) -> list[tuple]:
    r = c.get("/api/depositions/readings", params={"unit": "g/L"}, headers=P1).json()
    return [(x["ref"], x["value"], x["measureId"]) for x in r if x.get("depositionId") == did]


# depD: the candidate's steps.
dep = deposition("depD", [entry("d1", 10.0)])
r1 = put(dep)
print(f"depD first write, one reading d1 (10 g/L on mz): {r1.status_code}")
dep["entries"].append(entry("d1", 99.0, m="other"))
r2 = put(dep)
said = r2.text[:240] if r2.status_code != 200 else ""
print(f"depD second write appends another entry under d1 (99 g/L on other): {r2.status_code} {said}".rstrip())
k = kept("depD")
print(f"depD entries kept: {k}")
print(f"depD readings offered in g/L: {offered('depD')}")

# depE: the same id twice on one measure.
depe = deposition("depE", [entry("d1", 10.0)])
put(depe)
depe["entries"].append(entry("d1", 12.0))
re_ = put(depe)
print(f"also, depE: d1 at 10 g/L, then d1 again at 12 g/L on mz: {re_.status_code}; kept {kept('depE')}; "
      f"readings offered {offered('depE')}")

# depF: a first write that holds two entries under one id.
rf = put(deposition("depF", [entry("d1", 10.0), entry("d1", 20.0, m="other")]))
print(f"also, depF made in one write with two entries under d1: {rf.status_code}; kept {kept('depF')}")

dups = [x for x in k if x[0] == "d1"]
defect = r1.status_code == 200 and r2.status_code == 200 and len(dups) == 2
print(f"H315_VERDICT: {'DEFECT' if defect else 'NO-DEFECT'} (second write {r2.status_code}, entries under d1 kept: "
      f"{len(dups)})")
