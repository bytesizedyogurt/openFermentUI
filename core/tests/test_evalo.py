"""Eval set O (OF-BLD-015 §7.6): the keys come from the stores by code, and
the score reads the trace. Offline, with a scripted loop."""
from __future__ import annotations

from openferment_core import evalo, module_stores, postdoc_agent, tools
from test_postdoc_agent import Script, plan
from test_tools import pool  # noqa: F401


def seeded(pool_):  # noqa: F811
    return module_stores.Stores(module_stores.seed_sources(lambda: pool_))


def test_the_set_holds_ten_questions_and_their_keys_come_from_the_stores(pool):  # noqa: F811
    assert len(evalo.QUESTIONS) == 10
    keys = evalo.keys(seeded(pool))
    assert all(k["modules"] for k in keys), "every question names something a module holds"
    assert keys[0]["modules"] == ["dominion", "runbooks"]
    assert "geneos" in keys[2]["modules"] and "pureos" in keys[5]["modules"]


def test_a_question_scores_on_the_modules_read(pool):  # noqa: F811
    ctx = tools.ToolContext(pool_factory=lambda: pool, stores_factory=lambda: seeded(pool))
    script = Script(
        [("dominion_read", {"ids": [], "words": "", "kind": "molecule", "state": "open", "limit": 5})],
        plan(),
    )
    out = postdoc_agent.ask(evalo.QUESTIONS[0], converse=script, ctx=ctx)
    s = evalo.score(out, ["dominion", "runbooks"])
    assert s["read"] == ["dominion"] and s["missedRead"] == ["runbooks"] and s["searched"] is False
    assert evalo.modules_read(out.trace) == {"dominion"}


def test_a_loop_that_reads_nothing_and_writes_nothing_scores_nothing(pool, tmp_path, monkeypatch):  # noqa: F811
    """The footer half's key and the plan's footer were the same
    `module_stores.coverage` call on the same question, so it held whatever
    the model did: a stand-in that called no tool and wrote nothing scored ten
    of ten on it (review of OF-BLD-016 §1.R). The set scores only what the
    loop could get wrong, so a loop that does nothing scores nothing, and the
    report names no footer score."""
    ctx = tools.ToolContext(pool_factory=lambda: pool, stores_factory=lambda: seeded(pool))
    key_for = evalo.key_for
    monkeypatch.setattr(evalo, "key_for", lambda q, stores=None: key_for(q, seeded(pool)))
    monkeypatch.setattr(evalo, "OUT", tmp_path / "eval-o.json")
    report = evalo.run(ask=lambda q: postdoc_agent.ask(q, converse=Script(plan()), ctx=ctx))
    assert all(r["key"] and not r["tools"] and not r["kept"] for r in report["questions"])
    assert report["searched"] == 0
    scores = {k: v for r in report["questions"] for k, v in r.items() if isinstance(v, bool)}
    assert scores == {"searched": False}, scores
    assert "footer" not in report and (tmp_path / "eval-o.json").exists()
