"""One read tool per module (OF-BLD-015 §7.2), through `tools.run`.

The seeded modules come from the real `modules.json`; the service's stores
are stand-ins, so nothing here reads a key, the network or this machine's
data.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import module_stores, postdoc_agent, tools
from openferment_core.models import Checks, Guild, GuildPerson
from openferment_core.validate import SeenSet, validate_plan
from test_postdoc_agent import Script, claim, plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

STATES = {"open", "fenced", "approved", "locked", "proposed", "retired"}


def ctx_for(pool_, **over):  # noqa: F811
    def make():
        src = module_stores.seed_sources(lambda: pool_)
        for k, v in over.items():
            setattr(src, k, v)
        return module_stores.Stores(src)

    return tools.ToolContext(pool_factory=lambda: pool_, stores_factory=make)


def read(module, ctx, ids=(), words="", kind=None, state=None, limit=20):
    return tools.run(f"{module}_read", {"ids": list(ids), "words": words, "kind": kind, "state": state, "limit": limit}, ctx)


def test_every_module_has_a_read_tool_in_the_whitelist():
    names = {t.name for t in tools.infos()}
    assert {f"{m}_read" for m in module_stores.MODULES} <= names
    assert all(n in tools.WHITELIST for n in names)


@pytest.mark.parametrize("module", module_stores.MODULES)
def test_each_read_returns_typed_rows_inside_the_summary_cap(pool, module):  # noqa: F811
    r = read(module, ctx_for(pool))
    assert r.error is None, r.error
    assert all(row.state in STATES and row.ref == f"{module}/{row.kind}/{row.id}" for row in r.rows)
    assert len(json.dumps(r.summary, default=str)) <= tools.MAX_SUMMARY_CHARS
    assert r.summary["returned"] == len(r.rows) and sum(r.summary["states"].values()) == r.summary["count"]
    assert ("partial" in r.summary) == (module in module_stores.PARTIAL)


def test_dominion_reads_open_and_fenced_with_their_marks(pool):  # noqa: F811
    ctx = ctx_for(pool)
    opened = read("dominion", ctx, kind="molecule", state="open")
    fenced = read("dominion", ctx, kind="molecule", state="fenced")
    seeded = module_stores._projection()["dominion"]["molecules"]
    assert opened.summary["count"] + fenced.summary["count"] == len(seeded)
    assert all(row.provenance == "demo" and row.status in ("clear-expired", "clear-none") for row in opened.rows)
    taq = read("dominion", ctx, ids=["hot-start-taq"]).rows
    assert [(r.id, r.state, r.status) for r in taq] == [("hot-start-taq", "fenced", "watch-variant")]


def test_words_and_refs_both_find_a_row(pool):  # noqa: F811
    ctx = ctx_for(pool)
    assert read("runbooks", ctx, words="brazzein pilot").rows[0].id == "rb-brazzein"
    assert read("runbooks", ctx, ids=["runbooks/runbook/rb-brazzein"]).rows[0].state == "locked"
    assert read("geneos", ctx, words="necator").rows[0].id == "c-necator-h16"


def test_a_number_a_wrong_kind_and_a_wrong_state_are_refused_in_words(pool):  # noqa: F811
    ctx = ctx_for(pool)
    assert "a number was typed" in tools.run("dominion_read", {"ids": [], "words": "", "kind": None, "state": None,
                                                               "limit": 5, "ids_extra": 3}, ctx).error
    assert "not a kind" in read("pureos", ctx, kind="molecule").error
    assert "refused its input" in read("dominion", ctx, state="free").error


def test_guild_is_reduced_to_what_the_ledger_shows(pool):  # noqa: F811
    person = GuildPerson(id="p-ada", name="Ada Lovelace", role="lead", title="Head of the bench",
                         joinedAt="2026-01-01", addedAt="2026-01-01T00:00:00Z", addedBy="p-lead")
    r = read("guild", ctx_for(pool, guild=lambda: Guild(people=[person]), checks=Checks))
    [row] = r.rows
    assert (row.label, row.state, row.detail) == ("Ada Lovelace", "open", {"role": "lead"})
    assert "Head of the bench" not in json.dumps(r.summary)


def test_a_module_that_cannot_be_read_is_refused_in_words(pool):  # noqa: F811
    def broken():
        raise OSError("guild.json is unreadable")

    assert "could not read the module" in read("guild", ctx_for(pool, guild=broken)).error


def test_a_claim_may_cite_a_row_its_run_returned_and_no_other(pool):  # noqa: F811
    ctx = ctx_for(pool)
    seen = SeenSet()
    seen.add(read("dominion", ctx, ids=["hot-start-taq"]))
    cited = {"id": "c1", "text": "Hot-start Taq is fenced.", "recordIds": [], "support": "direct", "passages": [],
             "evidenceIds": [], "moduleRefs": ["dominion/molecule/hot-start-taq"]}
    ghost = dict(cited, id="c2", moduleRefs=["dominion/molecule/brazzein"])
    out = validate_plan([cited, ghost], seen, pool)
    assert [c.id for c in out.claims] == ["c1"] and out.claims[0].provenance == "demo"
    assert out.rejected == 1 and "no tool returned" in out.reasons[0]
    refused = SeenSet()
    refused.add(read("pureos", ctx, kind="molecule"))
    assert not refused.rows


def test_what_is_open_in_dominion_is_answered_from_dominion_read(pool):  # noqa: F811
    ctx = ctx_for(pool)
    question = "What is open in Dominion?"
    script = Script(
        [("dominion_read", {"ids": [], "words": "", "kind": "molecule", "state": "open", "limit": 5})],
        plan(dict(claim(text="Pfu polymerase is open to make: its foundational patents ran out."),
                  moduleRefs=["dominion/molecule/pfu-polymerase"])),
    )
    out = postdoc_agent.ask(question, converse=script, ctx=ctx)
    assert [s.kind for s in out.trace] == ["coverage", "tool", "final"]
    assert out.trace[1].summary.startswith("Read Dominion for molecule · open · ")
    [c] = out.claims
    assert c.moduleRefs == ["dominion/molecule/pfu-polymerase"] and c.provenance == "demo"
    assert [r.ref for r in out.rows] == ["dominion/molecule/pfu-polymerase"] and out.rows[0].state == "open"
    assert module_stores.footer(out.coverage).startswith("searched eleven, found in")
    assert next(m for m in out.coverage.modules if m.module == "dominion").count > 0
    # The tool the model was offered is the registry's, by the API's name rule.
    assert "dominion_read" in [t["name"] for t in script.calls[0]["tools"]]
