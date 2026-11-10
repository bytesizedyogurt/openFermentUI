"""H9: a plan route of three models, the first two unavailable. The routes say each model
is tried after the one before it is unavailable; Postdoc's loop is asked with a stand-in
`converse` that fails on the first two and answers on the third. No model is called.

    OPENFERMENT_DATABASE_URL=<bh_h9_spend> bh_py ../bughunt/notes/H9/scripts/plan_route_three.py
"""
from __future__ import annotations

import json
import os

os.environ["OPENFERMENT_ROUTES"] = json.dumps(
    {"plan": {"models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], "effort": "high"}})

from openferment_core import llm, postdoc_agent, projects, tools  # noqa: E402
from openferment_core.models import ProjectCreate, Usage  # noqa: E402

try:
    projects.create(ProjectCreate(id="route3", name="route3", by="bughunt"))
except Exception:
    pass
asked: list[str] = []


def converse(*, model, **_):
    asked.append(model)
    if model != "claude-haiku-5-5":
        raise llm.ModelUnavailable(f"{model} answered 529: overloaded")
    plan = {"claims": [], "gaps": ["nothing in hand"], "declined": None}
    return llm.Turn(content=[{"type": "text", "text": json.dumps(plan)}], toolCalls=[], data=plan,
                    stopReason="end_turn", usage=Usage(models=[model]), model=model)


with projects.using("route3"):
    plan = postdoc_agent.ask("What does the project hold?", converse=converse, ctx=tools.ToolContext())
print(json.dumps({"route": llm.chain("plan"), "asked": asked, "declined": plan.declined,
                  "steps": [s.summary for s in plan.trace]}, indent=1))
