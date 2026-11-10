"""H9-08, in process: the daily cap and the ask cap read from settings of nan and inf.

    OPENFERMENT_DATABASE_URL=<bh_r_h9_08_*> bh_py ../bughunt/repro/H9-08/caps.py

Prints one line a case; the last line is `DEFECTS n`. No model is called: the ask runs Postdoc's
own loop with a stand-in `converse` that records each call and answers nothing.
"""
from __future__ import annotations

import os

from sqlalchemy import delete

from openferment_core import db, llm, postdoc_agent, projects, ready, spend, tools
from openferment_core.db import models as t
from openferment_core.models import ProjectCreate, Usage

defects = 0


def clear() -> None:
    async def go():
        async with db.session() as s:
            await s.execute(delete(t.spend))
    db.run(go())


print("## A. OPENFERMENT_DAILY_BUDGET_USD: the call gate (llm._reserve, a 1000 USD worst case) and ready's spend row")
REQUEST = {"system": "x", "messages": [{"role": "user", "content": "y"}]}
for raw in ("-1", "1.00", "nan", "inf"):
    clear()
    os.environ[spend.DAILY_SETTING] = raw
    try:
        cap = spend.daily_budget()
        read = f"cap read as {cap!r}"
    except spend.BudgetSettingInvalid as e:
        read = f"refused in words: {e}"
        cap = None
    worst = llm.worst_case_usd("claude-opus-5-5", REQUEST, 50_000_000)  # 50M output tokens at 20 USD a million
    try:
        rid = llm._reserve("claude-opus-5-5", REQUEST, 50_000_000, Usage(), "answer")
        gate = f"a {worst:.2f} USD call HELD (reservation {rid})"
    except (llm.BudgetExhausted, spend.BudgetSettingInvalid) as e:
        gate = f"a {worst:.2f} USD call refused ({type(e).__name__}): {str(e)[:100]}"
    held = spend.state()["reservedUsd"]
    row = ready.check_spend()
    print(f"{spend.DAILY_SETTING}={raw}: {read}")
    print(f"    gate: {gate}; reservedUsd now {held}")
    print(f"    ready: [{row.mark}] spend {row.detail}")
    if raw in ("nan", "inf") and (cap is not None or row.mark != "fail" or held > 0):
        defects += 1
        print(f"    DEFECT: {raw} is taken as a number of dollars")
clear()
os.environ.pop(spend.DAILY_SETTING, None)

print("## B. OPENFERMENT_ASK_BUDGET_USD: Postdoc's loop (postdoc_agent.ask), a stand-in model that records each call")
try:
    projects.create(ProjectCreate(id="caps", name="caps", by="bughunt"))
except Exception:
    pass
for raw in ("-1", "nan", "inf"):
    os.environ[spend.ASK_SETTING] = raw
    calls: list[int] = []

    def converse(**kw):  # never asked to answer: every case ends before or at the first turn's room
        calls.append(kw.get("max_tokens"))
        raise llm.ModelUnavailable("stand-in", Usage())

    with projects.using("caps"):
        try:
            plan = postdoc_agent.ask("Which scenarios does the project keep?", converse=converse, ctx=tools.ToolContext())
            said = f"a plan, declined={plan.declined!r}"
            ok = plan.declined is not None
        except Exception as e:
            said = f"RAISED {type(e).__name__}: {e}"
            ok = False
    print(f"{spend.ASK_SETTING}={raw}: {said}; stand-in model calls {len(calls)}")
    if raw in ("nan", "inf") and not ok:
        defects += 1
        print(f"    DEFECT: the ask raised where the loop promises a plan with declined set")
os.environ.pop(spend.ASK_SETTING, None)
print(f"DEFECTS {defects}")
