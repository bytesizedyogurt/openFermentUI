"""H9: the ask cap (OPENFERMENT_ASK_BUDGET_USD) at its boundary, through Postdoc's own
loop (postdoc_agent.ask) with a stand-in `converse` that charges each turn what a model
writing its whole room would cost: its request read as input at four characters a token,
and every output token the turn allows. No model is called.

    OPENFERMENT_DATABASE_URL=<bh_h9_spend> bh_py ../bughunt/notes/H9/scripts/ask_budget.py
"""
from __future__ import annotations

import json
import os

from openferment_core import llm, postdoc_agent, projects, tools
from openferment_core.models import ProjectCreate, Usage

MODEL = "claude-opus-5-5"
try:
    projects.create(ProjectCreate(id="askcap", name="askcap", by="bughunt"))
except Exception:
    pass


def stand_in(log: list[dict]):
    def converse(*, system, messages, tools: list, schema, max_tokens, model, tool_choice="auto", **_):
        chars = len(json.dumps({"system": system, "messages": messages, "tools": tools}, default=str))
        inp, out = chars // 4, max_tokens
        cost = llm.cost_usd(MODEL, inp, out)
        log.append({"tool_choice": tool_choice, "max_tokens": max_tokens, "costUsd": cost})
        used = Usage(inputTokens=inp, outputTokens=out, costUsd=cost, models=[MODEL])
        if tool_choice == "none":
            plan = {"claims": [], "gaps": [], "declined": None}
            return llm.Turn(content=[{"type": "text", "text": json.dumps(plan)}], toolCalls=[], data=plan,
                            stopReason="end_turn", usage=used, model=MODEL)
        n = len(log)
        block = {"type": "tool_use", "id": f"tu{n}", "name": "study_read", "input": {"words": f"round {n}"}}
        return llm.Turn(content=[block], toolCalls=[llm.ToolCall(id=f"tu{n}", name="study_read",
                                                                 input={"words": f"round {n}"})],
                        data=None, stopReason="tool_use", usage=used, model=MODEL)
    return converse


for budget in ("0", "0.75", "2.00", "inf", "nan"):
    os.environ["OPENFERMENT_ASK_BUDGET_USD"] = budget
    log: list[dict] = []
    with projects.using("askcap"):
        try:
            plan = postdoc_agent.ask("Which scenarios does the project keep?", converse=stand_in(log),
                                     ctx=tools.ToolContext())
            spent = plan.usage.costUsd
            said = {"stopped": plan.stopped, "declined": plan.declined}
        except Exception as e:  # what the loop raises, in its own words
            spent = sum(x["costUsd"] for x in log)
            said = {"raised": f"{type(e).__name__}: {e}"}
    print(json.dumps({"askBudgetUsd": budget, "modelTurns": len(log), "spentUsd": round(spent, 4),
                      "pastTheBudget": (budget not in ("inf", "nan") and spent > float(budget)),
                      "turns": [(x["tool_choice"], x["max_tokens"], x["costUsd"]) for x in log], **said}), flush=True)
