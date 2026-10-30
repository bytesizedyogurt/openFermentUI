#!/usr/bin/env python
"""Ask a file of questions through Postdoc's loop (OF-BLD-014 §5.5).

    pnpm ask:batch questions.txt          # LIVE, needs the key

One question a line; blank lines and lines starting with `#` are skipped.
Each question runs through `postdoc_agent.ask`, exactly as `/api/ask` runs it,
and its plan is saved under `core/data/live/ask-batch-<time>/` (gitignored,
and kept on this machine). One row a question is printed: claims kept,
claims dropped by rule, tool calls, rounds (the tool-choosing turns of the
conversation that answered, the last one included), seconds, cost, why it
stopped.
The last line is the total cost.

A question the loop declines is a row like any other. The exit code is 1
when no model answered any question (the key, the network, the budget), and
2 when there is no key to try.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CORE = Path(__file__).resolve().parent.parent / "core"
ROOT = CORE.parent
sys.path.insert(0, str(CORE))

from openferment_core import atomic, intake, llm, postdoc_agent, tools  # noqa: E402
from openferment_core.models import AnswerPlan  # noqa: E402


def _path(raw: str) -> Path:
    """A path typed at the repository root, though pnpm runs this from core/."""
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def read_questions(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


HEADER = f"{'#':>2}  {'kept':>4}  {'dropped':>7}  {'tools':>5}  {'rounds':>6}  {'seconds':>7}  {'cost':>8}  stopped"


def row(n: int, plan: AnswerPlan, rounds: int, seconds: float) -> str:
    tools = sum(1 for t in plan.trace if t.kind == "tool")
    stopped = plan.stopped if not plan.declined or plan.claims else f"{plan.stopped}, declined"
    return f"{n:>2}  {len(plan.claims):>4}  {plan.rejected:>7}  {tools:>5}  {rounds:>6}  {seconds:>7.1f}  ${plan.usage.costUsd:>7.4f}  {stopped}"


def run(
    questions: list[str],
    out: Path,
    *,
    ask: Callable[..., AnswerPlan] = postdoc_agent.ask,
    converse: Callable[..., Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    echo: Callable[[str], None] = print,
) -> list[dict[str, Any]]:
    """Ask each question; save each plan and a summary; return the rows."""
    out.mkdir(parents=True, exist_ok=True)
    base = converse or llm.converse
    echo(HEADER)
    rows = []
    for n, question in enumerate(questions, start=1):
        turns = 0

        def counted(**kw):
            # A fresh conversation (a restart) holds the question alone.
            nonlocal turns
            if len(kw["messages"]) == 1:
                turns = 0
            if kw.get("tool_choice") == "auto":
                turns += 1
            return base(**kw)

        started = clock()
        plan = ask(question, converse=counted)
        seconds = clock() - started
        atomic.write_text(out / f"{n:02d}.json", plan.model_dump_json(indent=2))
        echo(row(n, plan, turns, seconds))
        rows.append({
            "n": n, "question": question, "kept": len(plan.claims), "dropped": plan.rejected,
            "toolCalls": sum(1 for t in plan.trace if t.kind == "tool"), "rounds": turns,
            "seconds": round(seconds, 2), "costUsd": plan.usage.costUsd, "stopped": plan.stopped,
            "declined": plan.declined, "models": plan.usage.models,
            "keptWithRecordOrQuote": sum(1 for c in plan.claims if c.recordIds or c.passages),
        })
    total = sum(r["costUsd"] for r in rows)
    atomic.write_text(out / "summary.json", json.dumps({"rows": rows, "costUsd": round(total, 6)}, indent=2))
    echo(f"total ${total:.4f} · plans in {out}")
    return rows


def pool_or_none():
    """The evidence pool, or None when there is no corpus to build it from."""
    try:
        return tools.ToolContext().pool
    except FileNotFoundError:
        return None


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("file", help="questions, one a line")
    args = parser.parse_args(argv)
    load_dotenv(CORE / ".env", override=False)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ask:batch needs the key in core/.env (core/.env.example names it). Nothing was asked.", file=sys.stderr)
        return 2
    pool = pool_or_none()
    if pool is None:
        print("ask:batch could not read the corpus; the service's log names why. Nothing was asked.", file=sys.stderr)
        return 2
    questions = read_questions(_path(args.file))
    ctx = tools.ToolContext(pool_factory=lambda: pool)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = run(questions, intake.DATA_DIR / "live" / f"ask-batch-{stamp}",
               ask=lambda q, converse: postdoc_agent.ask(q, converse=converse, ctx=ctx))
    answered = [r for r in rows if r["models"]]
    return 0 if answered else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
