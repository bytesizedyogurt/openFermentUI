"""H3-11: a model's estimate says in words what it rests on at two doors, and one door holds those words to
the number rule.

Run by run.sh with the repository's Python, keyless, over a fresh test database. One question goes through the
service's own answer path (`api._answer`, the body of POST /api/ask) to a stand-in model (no network, no key).
In that one ask the stand-in writes the same words, WORDS below, twice:

  round 1  the tool door: study_scenario on the sugarcane plant, one value whose quantity's note is WORDS
  round 2  engine_run on the scenario it kept (the worker is the tests' stand-in: no BioSTEAM)
  round 3  the claim door: a plan whose claim c1 states one estimate whose basis is WORDS, and a control claim c2
           whose basis is words with no number

The scenario row, the run's inputs and the run's artifact are read back from the project's stores.
"""
from __future__ import annotations

import json
import re
import sys

sys.path.insert(0, "/home/user/openFermentUI/core/tests")  # the tests' stand-in worker, read and never written

from openferment_core import api, artifacts, llm, projects  # noqa: E402
from openferment_core.engine import library, runs, simulator  # noqa: E402
from openferment_core.models import AskRequest, ProjectCreate, Usage  # noqa: E402
from openferment_core.studies import scenarios  # noqa: E402
from openferment_core.validate import find_number  # noqa: E402
from test_runs import StandIn as StandInWorker  # noqa: E402

PROJECT = "h3-11"
KEY = "stream.sugarcane.price"
WORDS = "about 30% above the 2011 design report"
PLAIN = "a delivered price above the package's"
TEXT = "The cane price the model estimates for the plant."


def claim(cid: str, basis: str) -> dict:
    value = {"label": "the cane's price", "evidenceId": "", "recordId": "",
             "estimate": {"value": 0.05, "unit": "USD/kg", "low": None, "high": None, "basis": basis}}
    return {"id": cid, "text": TEXT, "recordIds": [], "paperIds": [], "support": "unsupported", "passages": [],
            "evidenceIds": [], "moduleRefs": [], "values": [value]}


PLAN = {"claims": [claim("c1", WORDS), claim("c2", PLAIN)], "gaps": [], "declined": None}
SCENARIO = {"title": "A dearer cane", "plant": "sugarcane", "configuration": "", "note": "",
            "values": [{"key": KEY, "quantity": {"value": 0.05, "unit": "USD/kg", "note": WORDS}}]}


class StandInModel:
    """Stands in for llm.converse: two tool rounds, then the plan. No network."""

    def __init__(self):
        self.calls = 0
        self.models: list[str] = []

    def _turn(self, content, calls, data, stop):
        usage = Usage(inputTokens=1, outputTokens=1, costUsd=0.0, models=["h3-11-standin"])
        return llm.Turn(content=content, toolCalls=calls, data=data, stopReason=stop, usage=usage,
                        model="h3-11-standin")

    def __call__(self, **kw):
        self.calls += 1
        self.models.append(kw.get("model", ""))
        if self.calls == 1:
            call = llm.ToolCall(id="t1", name="study_scenario", input=SCENARIO)
            return self._turn([{"type": "tool_use", "id": "t1", "name": call.name, "input": call.input}],
                              [call], None, "tool_use")
        if self.calls == 2:
            said = json.dumps(kw.get("messages", []), default=str)
            sid = (re.findall(r'scenarioId\\?"\s*:\s*\\?"([^"\\]+)', said) or [""])[-1]
            args = {"plant": "", "configuration": "", "scenario": sid, "note": "the dearer cane"}
            call = llm.ToolCall(id="t2", name="engine_run", input=args)
            return self._turn([{"type": "tool_use", "id": "t2", "name": call.name, "input": call.input}],
                              [call], None, "tool_use")
        return self._turn([{"type": "text", "text": json.dumps(PLAN)}], [], PLAN, "end_turn")


def refuse(**kw):
    raise RuntimeError("h3-11: no model call is allowed in this reproduction")


llm.converse = refuse  # the stand-in is passed to the answer path; the real door refuses
simulator.call = StandInWorker()  # library_parameters, library_run and sff_export answered in process
library._PARAMETERS = {}

projects.create(ProjectCreate(id=PROJECT, name="H3-11 repro", by="bughunt"))
model = StandInModel()
tool_results: list[tuple[str, str | None]] = []
with projects.using(PROJECT):
    out = api._answer(AskRequest(question="What if the cane cost more?", by="bughunt"), converse=model)
    kept_scenarios = scenarios.listed()
    kept_runs = runs.listed()
    run_inputs = [(i.name, i.quantity.origin) for r in kept_runs for i in r.inputs if i.name == KEY]
    kept_artifacts = [artifacts.get(r.artifactId) for r in kept_runs if r.artifactId]

answering = model.models[0] if model.models else ""
print(f"stand-in model calls: {model.calls}; the answering route's model id: {answering!r}")
print(f"find_number on WORDS {WORDS!r}: {find_number(WORDS)!r}; on PLAIN {PLAIN!r}: {find_number(PLAIN)!r}")
print()
print("== the claim door (validate.claim_values, through the answer path) ==")
print(f"plan: {len(out.claims)} kept, {out.rejected} dropped")
for r in out.rejectionReasons:
    print(f"  dropped  {r}")
kept = {c.id: c for c in out.claims}
for c in out.claims:
    o = c.values[0].quantity.origin
    print(f"  kept     {c.id} ({c.provenance}) | origin {o.kind} by {o.by} note {o.note!r}")
print()
print("== the tool door (tools.run: numbers_in, stamped), the same ask ==")
for s in kept_scenarios:
    for v in s.values:
        o = v.quantity.origin
        print(f"  scenario {s.id} by {s.by} | {v.key} = {v.quantity.value} {v.quantity.unit} | origin {o.kind} "
              f"by {o.by} at {o.at} note {o.note!r}")
for r in kept_runs:
    print(f"  run {r.id} ({r.status}, {r.provenance}) by {r.by}")
for name, o in run_inputs:
    print(f"    input {name}: origin {o.kind} by {o.by} note {o.note!r}")
for a in kept_artifacts:
    for i in a.inputs:
        if i.name == KEY:
            print(f"  artifact {a.id} ({a.provenance}) | basis input {i.name} = {i.value} {i.unit} | source "
                  f"{i.source.kind} by {i.source.by} note {i.source.note!r}")

c1_dropped = "c1" not in kept and any(r.startswith("c1:") and "basis holds a number" in r for r in out.rejectionReasons)
c2_kept = "c2" in kept and kept["c2"].values[0].quantity.origin.note == PLAIN
scenario_note = [v.quantity.origin for s in kept_scenarios for v in s.values if v.key == KEY]
tool_kept = bool(scenario_note) and scenario_note[0].kind == "model-estimate" and scenario_note[0].note == WORDS
artifact_note = [i.source.note for a in kept_artifacts for i in a.inputs if i.name == KEY]
in_basis = bool(artifact_note) and artifact_note[0].endswith(f": {WORDS}")

print()
print("EXPECTED: one rule for what a model's estimate rests on, in words: WORDS (find_number finds a number in it) "
      "drops claim c1 at the claim door and is refused in words at the tool door, so no scenario, no run and no "
      "basis note carries it; c2 (no number) kept")
basis_said = repr(artifact_note[0]) if artifact_note else "none read"
tool_said = ("KEPT with the model-estimate note " + repr(scenario_note[0].note)) if tool_kept else "not kept with WORDS"
print(f"OBSERVED: claim door: c1 {'dropped (basis holds a number)' if c1_dropped else 'NOT dropped'}, c2 "
      f"{'kept' if c2_kept else 'NOT kept'}; tool door: the scenario {tool_said}; the run's artifact basis note "
      f"{basis_said}")
if not (c1_dropped and c2_kept):
    print("PYRESULT: NO-DEFECT (the claim door's controls did not behave as its rule says; see above)")
elif tool_kept and in_basis:
    print("PYRESULT: DEFECT")
elif tool_kept:
    print("PYRESULT: DEFECT (the scenario keeps WORDS; no run's basis was read)")
else:
    print("PYRESULT: NO-DEFECT")
sys.exit(0)
