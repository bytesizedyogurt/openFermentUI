"""`pnpm ask:batch` (OF-BLD-014 §5.5), offline: test_postdoc_agent's scripted
stand-in answers, over test_tools' stand-in pool."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from openferment_core import postdoc_agent, tools
from test_postdoc_agent import SENTENCE, Script, claim, papers, passages_found, plan, records  # noqa: F401
from test_tools import pool  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ask_batch", ROOT / "scripts" / "ask-batch.py")
ask_batch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ask_batch)


def test_a_questions_file_is_read_one_question_a_line(tmp_path):
    f = tmp_path / "questions.txt"
    f.write_text("# a comment\nFirst question?\n\nSecond question?\n", encoding="utf-8")
    assert ask_batch.read_questions(f) == ["First question?", "Second question?"]


def test_each_question_is_asked_saved_and_counted(pool, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("OPENFERMENT_ASK_BUDGET_USD", "1")
    script = Script(
        [records()], [papers()], plan(claim(records=["r-X1-1"], quotes=[("X1:s1:0", SENTENCE)])),
        plan(claim(text="It held 5 grams.", records=["r-X1-1"])),
    )
    ctx = tools.ToolContext(pool_factory=lambda: pool)
    ticks = iter(range(100))
    printed: list[str] = []
    out = tmp_path / "out"
    rows = ask_batch.run(
        ["first question", "second question"], out,
        ask=lambda q, converse: postdoc_agent.ask(q, converse=converse, ctx=ctx),
        converse=script, clock=lambda: float(next(ticks)), echo=printed.append,
    )
    assert [(r["kept"], r["dropped"], r["toolCalls"], r["rounds"], r["stopped"]) for r in rows] == [
        (1, 0, 2, 3, "done"),
        (0, 1, 0, 1, "done"),
    ]
    assert rows[0]["keptWithRecordOrQuote"] == 1
    assert sorted(p.name for p in out.iterdir()) == ["01.json", "02.json", "summary.json"]
    assert json.loads((out / "01.json").read_text())["claims"][0]["recordIds"] == ["r-X1-1"]
    assert printed[0] == ask_batch.HEADER and printed[-1].startswith("total $")
    assert json.loads((out / "summary.json").read_text())["costUsd"] == round(sum(r["costUsd"] for r in rows), 6)


def test_no_key_asks_nothing(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ask_batch, "CORE", Path("/nonexistent"))
    assert ask_batch.main(["docs/build/questions-pha.txt"]) == 2
    assert "Nothing was asked" in capsys.readouterr().err
