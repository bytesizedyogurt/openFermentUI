"""The coverage pass (OF-BLD-015 §7.1): before Postdoc's first turn, code
sweeps every module store for what the question names.

The seeded modules come from the real `modules.json` (`pnpm test:core`
exports it first); the service's own stores are stand-ins, so nothing here
reads a key, the network or this machine's data.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import module_stores, postdoc_agent, tools
from openferment_core.models import PriorTurn
from test_postdoc_agent import Script, plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

PROJECTION = json.loads(module_stores.PROJECTION.read_text())


def stores(pool_):  # noqa: F811
    return module_stores.Stores(module_stores.seed_sources(lambda: pool_))


def by_module(cmap):
    return {m.module: m for m in cmap.modules}


def test_a_molecule_a_runbook_and_a_strain_are_found_where_they_live(pool):  # noqa: F811
    q = "Is brazzein open in Dominion, what did the Brazzein runbook lock, and can Komagataella phaffii GS115 make it?"
    cmap = module_stores.coverage(q, stores(pool))
    m = by_module(cmap)
    assert cmap.searched == 11 and [x.module for x in cmap.modules] == list(module_stores.MODULES)
    brazzein = next(x for x in PROJECTION["dominion"]["molecules"] if x["id"] == "brazzein")
    hit = next(h for h in m["dominion"].hits if h.id == "brazzein")
    assert hit.ref == "dominion/molecule/brazzein"
    assert hit.state == module_stores.clearance_state(brazzein["clearanceState"])
    assert m["dominion"].named
    rb = next(h for h in m["runbooks"].hits if h.id == "rb-brazzein")
    assert rb.state == "locked"  # the seed locked it on 2026-07-02
    assert [h.id for h in m["geneos"].hits] == ["gs115"]
    assert cmap.found == 3 and module_stores.footer(cmap) == "searched eleven, found in three"
    assert cmap.entities == ["brazzein", "komagataella phaffii"]


def test_what_is_open_in_dominion_is_every_open_molecule_and_nothing_else(pool):  # noqa: F811
    cmap = module_stores.coverage("What is open in Dominion and which runbooks touch it?", stores(pool))
    d = by_module(cmap)["dominion"]
    open_ids = [x["id"] for x in PROJECTION["dominion"]["molecules"] if x["clearanceState"] in ("clear-expired", "clear-none")]
    open_ids += [f"{x['productId']}.{x['jurisdictionId']}" for x in PROJECTION["dominion"]["findings"]
                 if x["state"] in ("clear-expired", "clear-none")]
    assert d.count == len(open_ids) and d.count > 0
    assert all(h.state == "open" for h in d.hits) and len(d.hits) == module_stores.COVERAGE_HITS
    # "open" was asked of Dominion; the runbooks are listed whatever their state.
    rb = by_module(cmap)["runbooks"]
    assert rb.named and rb.count == len(PROJECTION["runbooks"]["runbooks"]) + len(PROJECTION["runbooks"]["protocols"])
    assert {h.state for h in rb.hits} - {"open"}


@pytest.mark.parametrize("state, expected", [("clear-expired", "open"), ("clear-none", "open"), ("watch-variant", "fenced"),
                                             ("watch-process", "fenced"), ("blocked", "fenced"), ("unknown", "fenced")])
def test_a_clearance_state_reads_as_open_or_fenced(state, expected):
    assert module_stores.clearance_state(state) == expected


def test_a_paper_id_is_not_mistaken_for_a_strain_designation(pool):  # noqa: F811
    cmap = module_stores.coverage("What did C. necator H16 make?", stores(pool))
    assert by_module(cmap)["intake"].count == 0


def test_a_module_that_cannot_be_read_says_so_and_the_rest_are_read(pool):  # noqa: F811
    s = stores(pool)
    s.sources.checks = lambda: (_ for _ in ()).throw(OSError("checks.json is unreadable"))
    cmap = module_stores.coverage("brazzein", s)
    assert "unreadable" in by_module(cmap)["guild"].error
    assert by_module(cmap)["dominion"].count >= 1


def test_the_map_is_the_first_step_and_rides_in_round_one(pool):  # noqa: F811
    ctx = tools.ToolContext(pool_factory=lambda: pool, stores_factory=lambda: stores(pool))
    script = Script(plan())
    out = postdoc_agent.ask("What is open in Dominion?", converse=script, ctx=ctx)
    first = out.trace[0]
    assert first.kind == "coverage" and first.ok and "searched eleven, found in" in first.summary
    assert any(line.startswith("Dominion · ") for line in first.input["modules"])
    content = script.calls[0]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "What is open in Dominion?"}
    assert content[1]["text"].startswith("COVERAGE MAP") and "dominion/molecule/" in content[1]["text"]
    assert out.coverage is not None and out.coverage.found >= 1
    # Nothing written, yet the decline never says the corpus is silent.
    assert out.declined and "corpus does not contain" not in out.declined and "Dominion" in out.declined


def test_the_map_says_its_refs_are_for_reading_not_for_citing(pool):  # noqa: F811
    """OF-BLD-016 §1.2's live run: Haiku cited `geneos/model/Yeast9` from the map
    without reading geneOS, and the validator rightly dropped both ceiling
    claims. The map and the prompt say a ref is citable only once a read tool
    returns it in this conversation."""
    text = module_stores.for_model(module_stores.coverage("brazzein", stores(pool)))
    assert "not citable" in text and "read tool returns" in text
    assert "not citable" in postdoc_agent.AGENT_SYSTEM


# OF-BLD-016 §1.R — a follow-up is swept with the questions it follows.
FOLLOW_UP = "Which of those are fenced, and why?"


def _ask(pool_, question, history):  # noqa: F811
    script = Script(plan())
    ctx = tools.ToolContext(pool_factory=lambda: pool_, stores_factory=lambda: stores(pool_))
    return postdoc_agent.ask(question, converse=script, ctx=ctx, history=history), script


def test_a_follow_up_is_swept_with_the_questions_it_follows(pool):  # noqa: F811
    """"Which of those are fenced, and why?" names nothing by itself; the
    question it follows named brazzein in Dominion. The map, the trace, the
    footer and the decline follow the conversation, never calling absent what
    Dominion shows (OF-BLD-015 §7.1)."""
    alone, _ = _ask(pool, FOLLOW_UP, [])
    assert alone.coverage.found == 0, "the follow-up's own words name nothing"
    earlier = PriorTurn(question="What is open in Dominion on brazzein?", claims=["Dominion holds a clearance row for it."])
    out, script = _ask(pool, FOLLOW_UP, [earlier])
    assert "brazzein" in out.coverage.entities and out.coverage.found >= 1
    assert any(h.ref == "dominion/molecule/brazzein" for h in by_module(out.coverage)["dominion"].hits)
    assert out.trace[0].summary.startswith("Swept the modules for what the conversation names · searched eleven, found in ")
    asked, cmap = script.calls[0]["messages"][-1]["content"]
    assert asked["text"].endswith(FOLLOW_UP), "the model answers the follow-up; only the sweep reads the earlier question"
    assert "dominion/molecule/brazzein" in cmap["text"]
    assert "Names found in the conversation: brazzein" in cmap["text"] and "this conversation names" in cmap["text"]
    assert out.declined and "corpus does not contain" not in out.declined and "Dominion" in out.declined


def test_a_follow_up_sweeps_the_earlier_questions_and_not_the_earlier_answers(pool):  # noqa: F811
    # An earlier answer is the model's words: it never steers the map.
    said = PriorTurn(question="Say more.", claims=["Brazzein sits in Dominion."], gaps=["Brazzein has no runbook here."])
    out, _ = _ask(pool, FOLLOW_UP, [said])
    assert out.coverage.found == 0 and "corpus does not contain" in out.declined


def test_a_follow_up_sweeps_only_the_turns_it_reads(pool):  # noqa: F811
    named = PriorTurn(question="What is open in Dominion on brazzein?")
    later = [PriorTurn(question="Say more.") for _ in range(postdoc_agent.MAX_HISTORY_TURNS)]
    out, script = _ask(pool, FOLLOW_UP, [named, *later])
    assert named.question not in json.dumps(script.calls[0]["messages"])
    assert out.coverage.found == 0
    out, _ = _ask(pool, FOLLOW_UP, [named, *later[1:]])
    assert out.coverage.found >= 1


def test_a_first_question_is_swept_by_itself(pool):  # noqa: F811
    q = "Is brazzein open in Dominion?"
    out, _ = _ask(pool, q, [])
    assert out.coverage == module_stores.coverage(q, stores(pool))
    assert out.trace[0].summary.startswith("Swept the modules for what the question names · ")
    assert module_stores.for_model(out.coverage).count("Names found in the question: brazzein") == 1
