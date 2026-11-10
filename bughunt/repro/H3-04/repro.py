"""H3-04: measured evidence for a deposition the project does not hold is kept, and read as measured.

Run by run.sh against a fresh keyless service: python -I repro.py ORIGIN. Project p1 must exist and hold
nothing else. The steps: what the project holds at the bench (no deposition, no reading a run may take);
one measured-evidence row written naming deposition 'nope' and runbook 'nope', value 999 g/L, with the
page's own provenance 'measured' and confirmed true; the state read; the runbooks module read of that row
through the HTTP tool door; and, in process with no model and no network, the class validate_plan gives a
claim that cites the row the read returned. Prints the facts, then H304_VERDICT: DEFECT or NO-DEFECT.
"""
from __future__ import annotations

import json
import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
P1 = {"X-OpenFerment-Project": "p1"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"


def short(body):
    return json.dumps(body, ensure_ascii=False)[:260]


before = c.get("/api/state", headers=P1).json()
readings = c.get("/api/depositions/readings", headers=P1).json()
deps_before = [d.get("id") for d in before.get("depositions", [])]
rbs_before = [r.get("id") for r in before.get("runbooks", [])]
print(f"[1 what p1 holds at the bench] depositions {deps_before}; runbooks {rbs_before}; readings a run may take "
      f"{[r.get('ref') for r in readings] if isinstance(readings, list) else readings}")

me = {"id": "me2", "depositionId": "nope", "runbookId": "nope", "productId": None, "predictionId": "p1",
      "label": "Ethanol titre", "value": 999.0, "unit": "g/L", "provenance": "measured",
      "conditions": {"protocolId": None, "scale": 1, "strainId": None}, "deviations": [], "confirmed": True,
      "at": T0}
r = c.put("/api/state/measuredEvidence/me2", json={"by": ADA, "value": me}, headers=P1)
put_status = r.status_code
print(f"[2 PUT measuredEvidence me2, depositionId 'nope', 999 g/L, provenance measured, confirmed true] "
      f"{put_status} {short(r.json())}")

state = c.get("/api/state", headers=P1).json()
kept = {m["id"]: m for m in state.get("measuredEvidence", [])}.get("me2")
deps_after = [d.get("id") for d in state.get("depositions", [])]
print(f"[3 GET /api/state] measuredEvidence me2 "
      f"{(kept['value'], kept['unit'], kept['provenance'], kept['confirmed'], kept['depositionId']) if kept else None}; "
      f"depositions {deps_after}")

read = c.post("/api/tools/runbooks_read", params={"by": ADA},
              json={"ids": ["runbooks/measured-evidence/me2"], "words": "", "kind": "", "state": "", "limit": 5},
              headers=P1).json()
rows = read.get("rows") or []
row = next((x for x in rows if x.get("ref") == "runbooks/measured-evidence/me2"), {})
detail = row.get("detail") or {}
print(f"[4 POST /api/tools/runbooks_read runbooks/measured-evidence/me2] provenance {row.get('provenance')} value "
      f"{detail.get('value')} {detail.get('unit')} depositionId {detail.get('depositionId')} label "
      f"{row.get('label')!r}")
if not row:
    print("   (no row; the tool answered " + short(read) + ")")

claim_class = None
try:
    from openferment_core.models import ToolResult
    from openferment_core.validate import SeenSet, validate_plan

    class NoRecords:
        def record(self, _rid):
            return None

    seen = SeenSet()
    seen.add(ToolResult.model_validate(read))
    out = validate_plan([{"id": "c1", "text": "The bench measured the ethanol titre this run reached.",
                          "moduleRefs": ["runbooks/measured-evidence/me2"], "support": "direct"}],
                        seen, NoRecords(), model="none", at=T0)
    claim_class = out.claims[0].provenance if out.claims else None
    print(f"[5 validate_plan, a claim citing runbooks/measured-evidence/me2] kept {len(out.claims)}, rejected "
          f"{out.rejected}, claim provenance {claim_class} {out.reasons}")
except Exception as e:  # noqa: BLE001
    print(f"[5 validate_plan] could not run in process: {type(e).__name__}: {e}")

kept_ok = put_status == 200 and kept is not None and kept.get("depositionId") == "nope"
no_dep = "nope" not in deps_after
marked = row.get("provenance") == "measured" and detail.get("value") == 999.0
print("EXPECTED: the write of me2 is refused in words with a 422, since p1 holds no deposition 'nope' (and no "
      "runbook 'nope') for it to have been measured in; a measured-evidence row is held to a deposition, entry and "
      "reconciliation the project keeps, and its mark is computed from that deposition's confirmed readings by code")
print(f"OBSERVED: PUT answered {put_status}; GET /api/state keeps me2 at "
      f"{kept.get('value') if kept else None} g/L, provenance {kept.get('provenance') if kept else None}, "
      f"depositionId {kept.get('depositionId') if kept else None}, while p1 holds depositions {deps_after}; "
      f"runbooks_read marks the row {row.get('provenance')} at {detail.get('value')} {detail.get('unit')}; a claim "
      f"citing it is graded {claim_class}")
print("H304_VERDICT:", "DEFECT" if (kept_ok and no_dep and marked) else "NO-DEFECT",
      f"(kept={kept_ok} no_deposition_held={no_dep} read_as_measured={marked} claim_class={claim_class})")
