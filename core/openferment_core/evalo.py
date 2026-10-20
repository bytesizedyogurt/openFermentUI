"""Eval set O (OF-BLD-015 §7.6): ten cross-module questions, each scored on
whether Postdoc searched the right modules.

    python -m openferment_core.evalo keys     # the answer keys, from the stores, no model
    python -m openferment_core.evalo run      # the ten questions live; writes core/data/live/eval-o.json

THE KEY IS DRAWN BY CODE. For each question, the modules that must be
searched are the ones `module_stores.coverage` finds something in, which is
the same code the loop runs before its first turn: a module the question
names, or one holding a row the question names. No answer key is written by
hand or by a model.

THE SCORE. `searched`: every key module was read by its read tool (or
`search_records`/`search_passages` for BioRepo) in the trace. A question
scores one point for it; the set's score is the mean over ten. The report
keeps the tools called, the claims kept and dropped, the cost and the model,
so a later run on another model is compared on the same keys.

THE FOOTER IS NOT SCORED. §7.6 asks whether the footer names the key
modules, but the key is `coverage(question)` and the footer is the map the
loop's sweep drew with the same call before its first turn, so it held by
construction: a stand-in that called no tool and wrote nothing scored ten of
ten on it (review of OF-BLD-016 §1.R). A score the model cannot miss
measures nothing; that the plan carries its sweep is `test_coverage`'s to
hold.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import intake, module_stores

QUESTIONS = [
    "What is open in Dominion and which runbooks touch it?",
    "Is brazzein open to make, what did its runbook lock, and which host does it run on?",
    "Which hosts in geneOS could make PHB, and what yield ceiling has been computed for Cupriavidus necator H16 on glucose?",
    "What PHB titres have been reported on xylose hydrolysate, and which of those papers has Intake fetched with full text?",
    "What does the Proforma scenario for PHA from cellulosic sugar still wait for, and what does the benchmark run give?",
    "Which downstream unit operations does Taq DNA polymerase need, and what does pureOS say about the centrifugation step?",
    "What is waiting for a person on Home right now, and which Primer lesson teaches measuring dry cell weight?",
    "Which protocols in Runbooks are tagged for Komagataella phaffii GS115, and which molecules in Dominion default to that host?",
    "Which Guild checks are open, and which Primer lessons count toward the skills they name?",
    "Which Intake sources failed to fetch, and does BioRepo hold any record from them?",
]
OUT = intake.DATA_DIR / "live" / "eval-o.json"
# BioRepo is searched through the corpus tools as well as its read tool.
BIOREPO_TOOLS = {"biorepo_read", "search_records", "search_passages", "convert_units"}


def key_for(question: str, stores: module_stores.Stores | None = None) -> list[str]:
    cmap = module_stores.coverage(question, stores)
    return [m.module for m in cmap.modules if m.count]


def keys(stores: module_stores.Stores | None = None) -> list[dict[str, Any]]:
    return [{"question": q, "modules": key_for(q, stores)} for q in QUESTIONS]


def modules_read(trace: list[Any]) -> set[str]:
    out: set[str] = set()
    for s in trace:
        if s.kind != "tool" or not s.ok:
            continue
        if s.tool in BIOREPO_TOOLS:
            out.add("biorepo")
        elif s.tool and s.tool.endswith("_read"):
            out.add(s.tool[: -len("_read")])
    return out


def score(plan: Any, key: list[str]) -> dict[str, Any]:
    read = modules_read(plan.trace)
    missed_read = [m for m in key if m not in read]
    return {"searched": not missed_read, "read": sorted(read), "missedRead": missed_read}


def run(ask=None) -> dict[str, Any]:
    from . import postdoc_agent

    ask = ask or postdoc_agent.ask
    rows = []
    for q in QUESTIONS:
        key = key_for(q)
        t = time.monotonic()
        plan = ask(q)
        s = score(plan, key)
        rows.append({
            "question": q, "key": key, **s,
            "tools": [x.tool for x in plan.trace if x.kind == "tool"],
            "kept": len(plan.claims), "dropped": plan.rejected, "reasons": plan.rejectionReasons,
            "declined": plan.declined, "costUsd": plan.usage.costUsd, "models": plan.usage.models,
            "seconds": round(time.monotonic() - t, 1),
        })
        print(f"{'✓' if s['searched'] else '✗'} {q[:70]}  key={key} read={s['read']} ${plan.usage.costUsd:.4f}")
    report = {
        "set": "O",
        "at": datetime.now(timezone.utc).isoformat(),
        "n": len(rows),
        "searched": sum(r["searched"] for r in rows) / len(rows),
        "costUsd": round(sum(r["costUsd"] for r in rows), 4),
        "models": sorted({m for r in rows for m in r["models"]}),
        "questions": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nset O: searched {report['searched']:.0%}, ${report['costUsd']} on {', '.join(report['models'])} → {OUT}")
    return report


def main(argv: list[str]) -> int:
    if argv[:1] == ["keys"]:
        for k in keys():
            print(f"{k['modules']}  {k['question']}")
        return 0
    if argv[:1] == ["run"]:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).parent.parent / ".env", override=False)
        run()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
