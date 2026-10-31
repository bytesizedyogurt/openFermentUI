"""The coverage pass (OF-BLD-015 §7.1): before Postdoc's first turn, code
sweeps every module store for what the question names.

The module rows come from a small projection written here: a fictional
runbook, protocol and host (alpha 2.0 deleted the seed that modules.json was
projected from, ADR-010). The service's own stores are stand-ins, so nothing
here reads a key, the network or this machine's data.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import module_stores, postdoc_agent, tools
from openferment_core.models import Checks, Guild, PriorTurn
from test_postdoc_agent import Script, plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

# Fictional names, chosen to be found by whole words and by nothing else.
PROJECTION = {
    "runbooks": {
        "runbooks": [{"id": "rb-zeta", "title": "Zetase — pilot process", "kind": "research", "status": "needs_review",
                      "lockedAt": None, "productId": None, "strainId": None, "predictions": []},
                     {"id": "rb-omega", "title": "Omegase — bench trial", "kind": "research", "status": "ready",
                      "lockedAt": "2026-10-01T00:00:00Z", "productId": None, "strainId": None, "predictions": []}],
        "protocols": [{"id": "PR-ZETA-01", "title": "Zetase seed train", "category": "upstream", "purpose": "",
                       "organisms": [], "currentVersion": 1, "versions": [1]}],
    },
    "geneos": {"hosts": [{"id": "h-zeta", "name": "Zetamyces testii Z1", "badges": [], "bsl": 1}], "pathways": []},
    "proforma": {"scenarios": []},
    "primer": {"lessons": []},
}


def stores(pool_):  # noqa: F811
    sources = module_stores.Sources(projection=lambda: json.loads(json.dumps(PROJECTION)), pool=lambda: pool_,
                                    artifacts=list, guild=Guild, checks=Checks, intake=dict, shelf=list,
                                    strain_aliases=dict)
    return module_stores.Stores(sources)


def by_module(cmap):
    return {m.module: m for m in cmap.modules}


def test_a_runbook_and_a_host_are_found_where_they_live(pool):  # noqa: F811
    cmap = module_stores.coverage("What does the Zetase runbook predict on Zetamyces testii Z1?", stores(pool))
    m = by_module(cmap)
    assert any(h.ref == "runbooks/runbook/rb-zeta" for h in m["runbooks"].hits)
    assert any(h.ref == "geneos/host/h-zeta" for h in m["geneos"].hits)
    assert "Zetase" in cmap.entities or "zetase" in [e.lower() for e in cmap.entities]
    assert cmap.searched == len(module_stores.MODULES)


def test_what_is_locked_in_runbooks_is_every_locked_row_and_nothing_else(pool):  # noqa: F811
    cmap = module_stores.coverage("Which runbooks are locked?", stores(pool))
    rb = by_module(cmap)["runbooks"]
    assert rb.named and {h.ref for h in rb.hits} == {"runbooks/runbook/rb-omega"}


def test_a_module_that_cannot_be_read_says_so_and_the_rest_are_read(pool):  # noqa: F811
    s = stores(pool)
    s.sources.checks = lambda: (_ for _ in ()).throw(OSError("checks.json is unreadable"))
    cmap = module_stores.coverage("Zetase", s)
    assert "unreadable" in by_module(cmap)["guild"].error
    assert by_module(cmap)["runbooks"].count >= 1


def test_the_map_is_the_first_step_and_rides_in_round_one(pool):  # noqa: F811
    ctx = tools.ToolContext(pool_factory=lambda: pool, stores_factory=lambda: stores(pool))
    script = Script(plan())
    out = postdoc_agent.ask("What is in the Zetase runbook?", converse=script, ctx=ctx)
    first = out.trace[0]
    assert first.kind == "coverage" and first.ok and "searched ten, found in" in first.summary
    assert any(line.startswith("Runbooks · ") for line in first.input["modules"])
    content = script.calls[0]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "What is in the Zetase runbook?"}
    assert content[1]["text"].startswith("COVERAGE MAP") and "runbooks/runbook/rb-zeta" in content[1]["text"]
    assert out.coverage is not None and out.coverage.found >= 1
    # Nothing written, yet the decline never says the corpus is silent.
    assert out.declined and "corpus does not contain" not in out.declined and "Runbooks" in out.declined


def test_the_map_says_its_refs_are_for_reading_not_for_citing(pool):  # noqa: F811
    """OF-BLD-016 §1.2's live run: a model cited a ref from the map without
    reading its module, and the validator rightly dropped the claims. The map
    and the prompt say a ref is citable only once a read tool returns it."""
    text = module_stores.for_model(module_stores.coverage("Zetase", stores(pool)))
    assert "not citable" in text and "read tool returns" in text
    assert "not citable" in postdoc_agent.AGENT_SYSTEM


# OF-BLD-016 §1.R — a follow-up is swept with the questions it follows.
FOLLOW_UP = "Which of those are locked, and why?"


def _ask(pool_, question, history):  # noqa: F811
    script = Script(plan())
    ctx = tools.ToolContext(pool_factory=lambda: pool_, stores_factory=lambda: stores(pool_))
    return postdoc_agent.ask(question, converse=script, ctx=ctx, history=history), script


def test_a_follow_up_is_swept_with_the_questions_it_follows(pool):  # noqa: F811
    alone, _ = _ask(pool, FOLLOW_UP, [])
    assert alone.coverage.found == 0, "the follow-up's own words name nothing"
    earlier = PriorTurn(question="What does the Zetase runbook hold?", claims=["Runbooks hold a row for it."])
    out, script = _ask(pool, FOLLOW_UP, [earlier])
    assert out.coverage.found >= 1
    assert any(h.ref == "runbooks/runbook/rb-zeta" for h in by_module(out.coverage)["runbooks"].hits)
    assert out.trace[0].summary.startswith("Swept the modules for what the conversation names · searched ten, found in ")
    asked, cmap = script.calls[0]["messages"][-1]["content"]
    assert asked["text"].endswith(FOLLOW_UP), "the model answers the follow-up; only the sweep reads the earlier question"
    assert "runbooks/runbook/rb-zeta" in cmap["text"] and "this conversation names" in cmap["text"]
    assert out.declined and "corpus does not contain" not in out.declined


def test_a_follow_up_sweeps_the_earlier_questions_and_not_the_earlier_answers(pool):  # noqa: F811
    # An earlier answer is the model's words: it never steers the map.
    said = PriorTurn(question="Say more.", claims=["Zetase sits in Runbooks."], gaps=["Zetase has no deposition here."])
    out, _ = _ask(pool, "Which of those, and why?", [said])
    assert out.coverage.found == 0 and "corpus does not contain" in out.declined


def test_a_follow_up_sweeps_only_the_turns_it_reads(pool):  # noqa: F811
    named = PriorTurn(question="What does the Zetase runbook hold?")
    later = [PriorTurn(question="Say more.") for _ in range(postdoc_agent.MAX_HISTORY_TURNS)]
    out, script = _ask(pool, "Which of those, and why?", [named, *later])
    assert named.question not in json.dumps(script.calls[0]["messages"])
    assert out.coverage.found == 0
    out, _ = _ask(pool, "Which of those, and why?", [named, *later[1:]])
    assert out.coverage.found >= 1


def test_a_first_question_is_swept_by_itself(pool):  # noqa: F811
    q = "Is the Zetase runbook locked?"
    out, _ = _ask(pool, q, [])
    assert out.coverage == module_stores.coverage(q, stores(pool))
    assert out.trace[0].summary.startswith("Swept the modules for what the question names · ")


@pytest.mark.parametrize("status, locked, state", [("needs_review", None, "proposed"), ("ready", "2026-10-01", "locked")])
def test_a_runbook_state_is_computed_from_its_status_and_lock(status, locked, state):
    assert module_stores.runbook_state(status, locked) == state
