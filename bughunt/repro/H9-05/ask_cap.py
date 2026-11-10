"""H9-05: the ask cap (OPENFERMENT_ASK_BUDGET_USD) through Postdoc's own loop.

postdoc_agent.ask runs with a stand-in `converse` in place of the model. Each
round calls one cheap tool (study_read), and the answer after a stop is an empty
plan. Each turn is charged what a model writing its whole room would cost: its
request read as input at four characters a token, and every output token the
turn's max_tokens allows. That charge sits at or under the code's own worst case
for the turn (llm.worst_case_usd, which reads input at two characters a token),
so a loop that keeps its promise ends at or under the budget.

Offline: every socket to a host other than loopback is refused in this process,
and no model client is built (the stand-in answers every turn).

usage (from core/, OPENFERMENT_DATABASE_URL naming a fresh bh_* database):
    .venv/bin/python ../bughunt/repro/H9-05/ask_cap.py
"""
from __future__ import annotations

import json
import os
import socket
import sys

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_connect, _connect_ex = socket.socket.connect, socket.socket.connect_ex


def _local(address) -> bool:
    return isinstance(address, (str, bytes)) or (isinstance(address, tuple) and str(address[0]) in _LOOPBACK)


def _guarded(real):
    def connect(self, address):
        if not _local(address):
            raise ConnectionRefusedError(f"H9-05 repro: the network is refused ({address!r})")
        return real(self, address)
    return connect


socket.socket.connect = _guarded(_connect)  # type: ignore[method-assign]
socket.socket.connect_ex = _guarded(_connect_ex)  # type: ignore[method-assign]

from openferment_core import llm, postdoc_agent, projects, tools  # noqa: E402
from openferment_core.models import ProjectCreate, Usage  # noqa: E402

PROJECT = "h905"
projects.create(ProjectCreate(id=PROJECT, name=PROJECT, by="H9-05 repro"))

# No model client may be built: the loop's turns all go to the stand-in.
def _no_client(*a, **k):  # pragma: no cover - a call here is the repro's own failure
    raise RuntimeError("H9-05 repro: a model client was asked for")


for name in ("_default_client", "converse"):
    if hasattr(llm, name):
        setattr(llm, name, _no_client)

MODEL = llm.chain("plan")[0]
_, MODEL_ID = llm.spec(MODEL)


def stand_in(log: list[dict]):
    def converse(*, system, messages, tools: list, schema, max_tokens, model, tool_choice="auto", **_):
        request = {"system": system, "messages": messages, "tools": tools}
        chars = len(json.dumps(request, default=str, ensure_ascii=False))
        inp, out = chars // 4, max_tokens
        cost = llm.cost_usd(MODEL_ID, inp, out)
        worst = llm.worst_case_usd(MODEL_ID, request, max_tokens)
        log.append({"tool_choice": tool_choice, "max_tokens": max_tokens, "costUsd": cost, "worstUsd": worst})
        used = Usage(inputTokens=inp, outputTokens=out, costUsd=cost, models=[MODEL_ID])
        if tool_choice == "none":
            plan = {"claims": [], "gaps": [], "declined": None}
            return llm.Turn(content=[{"type": "text", "text": json.dumps(plan)}], toolCalls=[], data=plan,
                            stopReason="end_turn", usage=used, model=MODEL_ID)
        n = len(log)
        call = {"words": f"round {n}"}
        return llm.Turn(content=[{"type": "tool_use", "id": f"tu{n}", "name": "study_read", "input": call}],
                        toolCalls=[llm.ToolCall(id=f"tu{n}", name="study_read", input=call)],
                        data=None, stopReason="tool_use", usage=used, model=MODEL_ID)
    return converse


defects = 0
print(f"model {MODEL_ID}; prices {llm.prices_for(MODEL_ID, 1000)} USD per million in/out; "
      f"MIN_TOKENS {postdoc_agent.MIN_TOKENS}; plan route {llm.routes()['plan']}", flush=True)
for budget in sys.argv[1:] or ["0", "0.75", "2.00"]:
    os.environ["OPENFERMENT_ASK_BUDGET_USD"] = budget
    log: list[dict] = []
    with projects.using(PROJECT):
        plan = postdoc_agent.ask("Which scenarios does the project keep?", converse=stand_in(log),
                                 ctx=tools.ToolContext())
    spent = plan.usage.costUsd
    within_worst = all(x["costUsd"] <= x["worstUsd"] for x in log)
    rounds = [x for x in log if x["tool_choice"] == "auto"]
    rounds_usd = round(sum(x["costUsd"] for x in rounds), 6)
    rounds_worst = round(sum(x["worstUsd"] for x in rounds), 6)
    past = spent > float(budget)
    defects += past
    print(json.dumps({
        "askBudgetUsd": budget, "modelTurns": len(log), "spentUsd": round(spent, 4), "pastTheBudget": past,
        "stopped": plan.stopped, "everyTurnAtOrUnderItsWorstCase": within_worst,
        "roundsWorstCaseUsd": round(rounds_worst, 4), "roundsChargedUsd": round(rounds_usd, 4),
        "turns": [{"tool_choice": x["tool_choice"], "max_tokens": x["max_tokens"],
                   "costUsd": round(x["costUsd"], 4), "worstUsd": round(x["worstUsd"], 4)} for x in log],
    }), flush=True)
print(f"SUMMARY {defects} budget(s) spent past", flush=True)
