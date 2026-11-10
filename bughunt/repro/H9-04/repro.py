"""H9-04: claims whose words state a quantity, through Postdoc's own loop.

A fresh project holds one pasted document. A scripted stand-in for the model
(the converse hook test_postdoc_agent.py uses; no request leaves the machine)
calls search_passages once, reads the document's sentence, and answers a plan:
each claim quotes that sentence word for word, and each one's words state a
quantity. postdoc_agent.ask holds the plan to validate.validate_plan, the
decision the service keeps; this prints which claims and gaps it kept.

    OPENFERMENT_DATABASE_URL=... python repro.py PROJECT
"""
from __future__ import annotations

import json
import sys

from sci_rag.embed import LocalHashEmbedder

from openferment_core import intake, llm, postdoc_agent, practice, projects, tools
from openferment_core.literature import EMBEDDING_DIM, kit
from openferment_core.models import ProjectCreate, Usage
from openferment_core.postdoc.plan import SYSTEM as PLAN_SYSTEM

PROJECT = sys.argv[1]
SENTENCE = "Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions."

# The words the candidate names, each in a claim of its own (the defect), three the validator
# drops (the controls: "twofold", "tenfold", "pH 7"), and two its step-label rule keeps by design.
DEFECT = {
    "d1": "Ethanol titre roughly doubled under anaerobic conditions",
    "d2": "The yield halved on xylose",
    "d3": "The titre quadrupled in the evolved strain",
    "d4": "Table IV lists the yields of the strains",
    "d5": "A x10 rise in productivity followed the change",
    "d6": "The strain grew best at pH7 in the cited batch",
    "d7": "The titre fell at pH-4 in the cited batch",
}
# Kept by design, shown for reference: validate.py's step-label carve-out (STEP_WORDS) keeps
# "phase 3", so "phase III" being kept agrees with the validator's own rule.
BY_DESIGN = {
    "s1": "The phase 3 fermentation reached its titre",
    "s2": "The phase III fermentation reached its titre",
}
CONTROL = {
    "k1": "Ethanol titre rose twofold under anaerobic conditions",
    "k2": "A tenfold rise in productivity followed the change",
    "k3": "The strain grew best at pH 7 in the cited batch",
}
GAPS = ["Whether the titre doubled at pH7 is measured nowhere in the project",
        "Whether the titre rose twofold is measured nowhere in the project"]

kit.use_embedder(LocalHashEmbedder(EMBEDDING_DIM))  # the tests' offline embedder: no model file
projects.create(ProjectCreate(id=PROJECT, name="H9-04 repro", by="Bughunt Person"))
with projects.using(PROJECT):
    got = intake.paste("Anaerobic yeast notes", SENTENCE, project_id=PROJECT, by="Bughunt Person")
    print(json.dumps({"pasted": got.model_dump(mode="json").get("documentId") or str(got)[:120]}))


class Script:
    """llm.converse's stand-in: one turn of tool calls, then the plan."""

    def __init__(self, *turns):
        self.turns = list(turns)

    def __call__(self, **kw):
        turn = self.turns.pop(0) if self.turns else {"claims": [], "gaps": [], "declined": None}
        usage = Usage(inputTokens=10, outputTokens=5, costUsd=0.0, models=[kw["model"]])
        if isinstance(turn, dict):
            return llm.Turn(content=[{"type": "text", "text": json.dumps(turn)}], toolCalls=[], data=turn,
                            stopReason="end_turn", usage=usage, model=kw["model"])
        calls = [llm.ToolCall(id=f"tu-{i}", name=n, input=inp) for i, (n, inp) in enumerate(turn)]
        content = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
        return llm.Turn(content=content, toolCalls=calls, data=None, stopReason="tool_use", usage=usage,
                        model=kw["model"])


class PlanWriter:
    """Writes the plan after the search, citing the passage id the search returned."""

    def __init__(self):
        self.script = Script([("search_passages", {"query": "yeast ethanol anaerobic", "k": 3})])
        self.passage_id = None

    def __call__(self, **kw):
        if self.script.turns:
            return self.script(**kw)
        for m in kw["messages"]:
            for part in (m.get("content") if isinstance(m.get("content"), list) else []):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    body = part.get("content")
                    text = body if isinstance(body, str) else json.dumps(body)
                    for found in json.loads(text).get("passages", []) if text.strip().startswith("{") else []:
                        if SENTENCE in (found.get("text") or ""):
                            self.passage_id = found["passageId"]
        claims = [{"id": cid, "text": text, "recordIds": [], "paperIds": [], "support": "direct",
                   "passages": [{"passageId": self.passage_id, "quote": SENTENCE}], "evidenceIds": [],
                   "moduleRefs": [], "values": []}
                  for cid, text in {**DEFECT, **CONTROL, **BY_DESIGN}.items()]
        self.script.turns.append({"claims": claims, "gaps": GAPS, "declined": None})
        return self.script(**kw)


writer = PlanWriter()
with projects.using(PROJECT):
    out = postdoc_agent.ask("How does yeast make ethanol without oxygen?", converse=writer,
                            ctx=tools.ToolContext(project=PROJECT))

print(json.dumps({"passageCited": writer.passage_id, "declined": out.declined, "kept": len(out.claims),
                  "rejected": out.rejected}))
kept = {c.id for c in out.claims}
first = next((c for c in out.claims if c.id == "d1"), None)
if first is not None:
    print(json.dumps({"keptClaimShownAs": {"id": first.id, "text": first.text, "support": first.support,
                                           "provenance": first.provenance, "paperIds": first.paperIds,
                                           "quote": first.passages[0].quote if first.passages else None,
                                           "values": [v.model_dump(mode="json") for v in first.values]}}))
reasons = {r.split(":", 1)[0]: r for r in out.rejectionReasons}
for cid, text in {**DEFECT, **CONTROL, **BY_DESIGN}.items():
    print(json.dumps({"claim": cid, "text": text, "kept": cid in kept, "reason": reasons.get(cid)}))
for g in GAPS:
    print(json.dumps({"gap": g, "kept": g in out.gaps}))
# The same words held to the practice drafts' check (practice.check_text: find_number, then PRACTICE_QUANTITY).
for cid, text in DEFECT.items():
    try:
        practice.check_text("prompt", text, 0)
        refused = False
    except practice.PracticeRefused:
        refused = True
    print(json.dumps({"practice": cid, "refused": refused}))
print(json.dumps({"planPromptListsDoubledAsBad": "Ethanol titre roughly doubled under anaerobic conditions" in PLAN_SYSTEM,
                  "agentRule9NamesPhAndTableNumber": "a pH" in postdoc_agent.AGENT_SYSTEM
                  and "a table or figure" in postdoc_agent.AGENT_SYSTEM}))
summary = {"defectKept": sum(cid in kept for cid in DEFECT), "defectTotal": len(DEFECT),
           "byDesignKept": sum(cid in kept for cid in BY_DESIGN),
           "controlDropped": sum(cid not in kept for cid in CONTROL), "controlTotal": len(CONTROL),
           "gapDoubledKept": GAPS[0] in out.gaps, "gapTwofoldDropped": GAPS[1] not in out.gaps,
           "passageCited": writer.passage_id is not None}
print("SUMMARY " + json.dumps(summary))
