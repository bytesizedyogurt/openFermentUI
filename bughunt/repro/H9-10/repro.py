"""H9-10: a plan route of three models, the first two unavailable.

Run from core/ with the core's venv, OPENFERMENT_DATABASE_URL on a fresh test database and
OPENFERMENT_ROUTES naming the plan route claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5.
GET /api/health is read in process (FastAPI's TestClient, no lifespan); Postdoc's loop is asked
with a stand-in `converse` (the hook core/tests/test_postdoc_agent.py uses) that answers 529 on
the models in UNAVAILABLE and a plan of no claims on any other. No model is asked.
"""
from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from openferment_core import api, llm, postdoc_agent, projects, tools
from openferment_core.models import ProjectCreate, Usage

PROJECT = sys.argv[1]
projects.create(ProjectCreate(id=PROJECT, name=PROJECT, by="bughunt"))

health = TestClient(api.app).get("/api/health").json()


def ask(unavailable: set[str]) -> dict:
    asked: list[str] = []

    def converse(*, model, **_):
        asked.append(model)
        if model in unavailable:
            raise llm.ModelUnavailable(f"{model} answered 529: overloaded")
        plan = {"claims": [], "gaps": ["nothing in hand"], "declined": None}
        return llm.Turn(content=[{"type": "text", "text": json.dumps(plan)}], toolCalls=[], data=plan,
                        stopReason="end_turn", usage=Usage(models=[model]), model=model)

    with projects.using(PROJECT):
        plan = postdoc_agent.ask("What does the project hold?", converse=converse, ctx=tools.ToolContext())
    return {"unavailable": sorted(unavailable), "asked": asked, "declined": plan.declined,
            "steps": [s.summary for s in plan.trace]}


control = ask({"claude-opus-5-5"})
case = ask({"claude-opus-5-5", "claude-sonnet-5-5"})
print("SUMMARY " + json.dumps({"route": llm.chain("plan"), "health": {"model": health.get("model"),
      "fallbackModel": health.get("fallbackModel")}, "control": control, "case": case}))
