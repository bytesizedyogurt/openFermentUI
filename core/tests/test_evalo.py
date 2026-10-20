"""Eval set O (OF-BLD-015 §7.6): the keys come from the stores by code, and
the score reads the trace and the footer. Offline, with a scripted loop."""
from __future__ import annotations

from openferment_core import evalo, module_stores, postdoc_agent, tools
from test_postdoc_agent import Script, plan
from test_tools import pool  # noqa: F401


def seeded(pool_):  # noqa: F811
    # The whole seed, archived programs shown, as eval set O was written over it.
    return module_stores.Stores(module_stores.seed_sources(lambda: pool_), include_archived=True)


def test_the_set_holds_ten_questions_and_their_keys_come_from_the_stores(pool):  # noqa: F811
    assert len(evalo.QUESTIONS) == 10
    keys = evalo.keys(seeded(pool))
    assert all(k["modules"] for k in keys), "every question names something a module holds"
    assert keys[0]["modules"] == ["dominion", "runbooks"]
    assert "geneos" in keys[2]["modules"] and "pureos" in keys[5]["modules"]


def test_a_question_scores_on_the_modules_read_and_the_footer(pool):  # noqa: F811
    ctx = tools.ToolContext(pool_factory=lambda: pool, stores_factory=lambda: seeded(pool))
    script = Script(
        [("dominion_read", {"ids": [], "words": "", "kind": "molecule", "state": "open", "limit": 5})],
        plan(),
    )
    out = postdoc_agent.ask(evalo.QUESTIONS[0], converse=script, ctx=ctx)
    s = evalo.score(out, ["dominion", "runbooks"])
    assert s["read"] == ["dominion"] and s["missedRead"] == ["runbooks"] and s["searched"] is False
    assert s["footer"] is True and s["missedNamed"] == []
    assert evalo.modules_read(out.trace) == {"dominion"}
