"""H3-10: a claim's estimate carries numbers in its unit, a field no rule reads.

Run by run.sh with the repository's Python, keyless, over a fresh test database. The service's own
answer path (`api._answer`, the body of POST /api/ask) asks one question of a stand-in model (no
network, no key): its plan states three claims, each with one estimate.

  c1  the number in words sits in the estimate's unit: 'USD/gal, about 40 cents above the 2011 design'
  c2  control: the same words moved into the estimate's basis (validate.claim_values reads a basis)
  c3  control: a plain unit 'USD/gal' and a basis in words with no number

Rule 6 of validate_plan and ADR-006's 6.2 note drop a claim whose label or basis holds a number; c2
shows that rule live. c1 carries the same number in words one field over. The kept turn is read back
from the conversation store.
"""
from __future__ import annotations

import json
import sys

from openferment_core import api, llm, projects, units
from openferment_core.models import AskRequest, ProjectCreate, Usage
from openferment_core.postdoc import conversations
from openferment_core.validate import find_number

PROJECT = "h3-10"
BAD_UNIT = "USD/gal, about 40 cents above the 2011 design"
TEXT = "The selling price the model estimates for the plant."


def value(unit: str, basis: str) -> dict:
    return {"label": "the selling price", "evidenceId": "", "recordId": "",
            "estimate": {"value": 2.1, "unit": unit, "low": None, "high": None, "basis": basis}}


def claim(cid: str, unit: str, basis: str) -> dict:
    return {"id": cid, "text": TEXT, "recordIds": [], "paperIds": [], "support": "unsupported", "passages": [],
            "evidenceIds": [], "moduleRefs": [], "values": [value(unit, basis)]}


PLAN = {"claims": [claim("c1", BAD_UNIT, "the design report's price structure"),
                   claim("c2", "USD/gal", "about 40 cents above the 2011 design"),
                   claim("c3", "USD/gal", "the design report's price structure")],
        "gaps": [], "declined": None}


class StandIn:
    """Stands in for llm.converse: one final plan, no tool call, no network."""

    def __init__(self):
        self.calls = 0

    def __call__(self, **kw):
        self.calls += 1
        usage = Usage(inputTokens=1, outputTokens=1, costUsd=0.0, models=["h3-10-standin"])
        return llm.Turn(content=[{"type": "text", "text": json.dumps(PLAN)}], toolCalls=[], data=PLAN,
                        stopReason="end_turn", usage=usage, model="h3-10-standin")


def refuse(**kw):
    raise RuntimeError("h3-10: no model call is allowed in this reproduction")


llm.converse = refuse  # belt and braces: the stand-in is passed, the real door refuses

projects.create(ProjectCreate(id=PROJECT, name="H3-10 repro", by="bughunt"))
standin = StandIn()
with projects.using(PROJECT):
    out = api._answer(AskRequest(question="What would the plant's selling price be?", by="bughunt"), converse=standin)
    kept_turns = conversations.get(out.conversationId).turns

print(f"stand-in calls: {standin.calls}; conversation {out.conversationId}, turn {out.turnId}")
print(f"plan: {len(out.claims)} kept, {out.rejected} dropped")
for r in out.rejectionReasons:
    print(f"  dropped  {r}")
kept = {c.id: c for c in out.claims}
for c in out.claims:
    q = c.values[0].quantity
    print(f"  kept     {c.id} ({c.provenance}) | value {q.value} unit {q.unit!r} origin {q.origin.kind} "
          f"by {q.origin.by} note {q.origin.note!r}")

(turn,) = kept_turns
stored = {c.id: c for c in (turn.plan.claims if turn.plan else [])}
s1 = stored.get("c1")
stored_unit = s1.values[0].quantity.unit if s1 else None
print(f"the conversation store's turn {turn.id} ({turn.status}) keeps c1: {'yes' if s1 else 'no'}; "
      f"its value's unit as kept: {stored_unit!r}")
print(f"the unit table reads c1's unit as: {units.normalize(BAD_UNIT)!r}; it reads 'USD/gal' as {units.normalize('USD/gal')!r}")
print(f"find_number on c1's unit finds: {find_number(BAD_UNIT)!r}; on c2's basis: {find_number('about 40 cents above the 2011 design')!r}")

c2_dropped = "c2" not in kept and any(r.startswith("c2:") and "basis holds a number" in r for r in out.rejectionReasons)
c3_kept = "c3" in kept
c1_kept = "c1" in kept and stored_unit == BAD_UNIT

print("EXPECTED: c1 dropped and counted like c2 (its estimate's unit holds a number in words, '40' and '2011', "
      "and the unit table reads no unit there); c3 kept; plan: 1 kept, 2 dropped")
print(f"OBSERVED: c1 {'KEPT' if 'c1' in kept else 'dropped'} with unit {stored_unit!r} in the conversation store; "
      f"c2 {'dropped (basis holds a number)' if c2_dropped else 'NOT dropped'}; c3 {'kept' if c3_kept else 'dropped'}; "
      f"plan: {len(out.claims)} kept, {out.rejected} dropped")
if not (c2_dropped and c3_kept):
    print("PYRESULT: NO-DEFECT (the controls did not behave as the rule says; see above)")
elif c1_kept:
    print("PYRESULT: DEFECT")
else:
    print("PYRESULT: NO-DEFECT")
sys.exit(0)
