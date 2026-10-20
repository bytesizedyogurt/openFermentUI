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


def ctx_for(pool_, include_archived=True, **over):  # noqa: F811
    """The seed with archived programs shown, as the tools read it before
    the program switch (OF-BLD-016 §2.3), unless the test turns it off."""
    def make():
        src = module_stores.seed_sources(lambda: pool_)
        for k, v in over.items():
            setattr(src, k, v)
        return module_stores.Stores(src, include_archived=include_archived)

    return tools.ToolContext(pool_factory=lambda: pool_, stores_factory=make, include_archived=include_archived)


def read(module, ctx, ids=(), words="", kind="", state="", limit=20):
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
    assert "a number was typed" in tools.run("dominion_read", {"ids": [], "words": "", "kind": "", "state": "",
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


def _unions(node, path=""):
    """Parameters a strict schema leaves nullable or union-typed, as the API
    counts them: a type array or an anyOf."""
    found = []
    if isinstance(node, dict):
        if isinstance(node.get("type"), list) or "anyOf" in node:
            found.append(path)
        for key in ("properties", "$defs"):
            for name, child in (node.get(key) or {}).items():
                found += _unions(child, f"{path}.{name}")
        if "items" in node:
            found += _unions(node["items"], f"{path}[]")
    return found


def test_a_whole_request_stays_inside_the_sixteen_union_parameters_strict_tools_allow():
    from openferment_core import llm

    defs = [llm.strict_schema(t["input_schema"]) for t in postdoc_agent._tool_defs() if t["strict"]]
    count = sum(len(_unions(d)) for d in defs) + len(_unions(llm.strict_schema(postdoc_agent.PLAN_SCHEMA)))
    assert count <= 16, f"{count} union-typed parameters; the API refuses more than sixteen"
    assert not any(_unions(llm.strict_schema(tools.REGISTRY[f"{m}_read"].info().inputSchema))
                   for m in module_stores.MODULES)


def test_the_module_tools_go_out_loose_and_the_rest_strict():
    """Eighteen strict tools compiled to a grammar the API refused as too
    large (live, 2026-10-19); the seven earlier tools stay strict, and
    `tools.run` validates every input either way."""
    from openferment_core import llm

    sent = [llm.tool_param(t["name"], t["description"], t["input_schema"], t["strict"]) for t in postdoc_agent._tool_defs()]
    assert [t["name"] for t in sent if t["strict"]] == list(tools.WHITELIST[:7])
    # The module tools and thermosteam's read (OF-BLD-019 §4.2) go out loose.
    assert {t["name"] for t in sent if not t["strict"]} == {f"{m}_{w}" for m in module_stores.MODULES for w in ("read", "write")} | {"thermo_props"}
    assert "refused its input" in tools.run("dominion_read", {"ids": "hot-start-taq", "words": "", "kind": "", "state": "",
                                                              "limit": 5}).error


# ── tuned on the first live runs (2026-10-20) ─────────────────────────────


def test_a_word_finds_a_row_by_its_head(pool):  # noqa: F811
    """Haiku searched Primer for "depos" and found nothing where a person
    would have read "Depositing" as a match: a query word of four letters or
    more matches the head of a row's word, and the module's blurb counts."""
    ctx = ctx_for(pool)
    assert [r.id for r in read("primer", ctx, words="steril").rows] == ["l6-3"]  # "Sterilising and releasing a vessel"
    assert read("primer", ctx, words="ste").summary["count"] == 0  # three letters is too short a head
    assert read("primer", ctx, words="extract").summary["count"] >= 1  # "Why extraction", and the module's blurb


def test_an_artifact_row_carries_its_headline_values(pool):  # noqa: F811
    """A Proforma read said the benchmark row named its tool and date and
    nothing else (live, 2026-10-20). The top-level scalars of the output
    ride on the row, with the inputs' names, so a read says what was
    computed; a value is still cited through the tool that computes it."""
    from openferment_core.models import Artifact, BasisInput, BasisSource

    art = Artifact(id="0123456789abcdef", tool="proforma_benchmark", toolVersion="1", provenance="computed",
                   createdAt="2026-10-20T00:00:00Z", outputHash="x", durationMs=1,
                   inputs=[BasisInput(name="package", value="biorefineries.cornstover@2.35.1", unit="",
                                      source=BasisSource(kind="model", id="x"))],
                   output={"mespUsdPerGal": 1.9677, "package": "biorefineries.cornstover@2.35.1", "nested": {"a": 1},
                           "quantiles": [1, 2, 3]})
    r = read("proforma", ctx_for(pool, artifacts=lambda: [art]), kind="artifact")
    [row] = r.rows
    assert row.detail["output"] == {"mespUsdPerGal": 1.9677, "package": "biorefineries.cornstover@2.35.1"}
    assert row.detail["inputs"] == ["package=biorefineries.cornstover@2.35.1"]
    assert read("proforma", ctx_for(pool, artifacts=lambda: [art]), words="cornstover").summary["count"] == 1


def test_a_molecule_row_names_its_train_and_pathways(pool):  # noqa: F811
    """The seams to pureOS and geneOS: the unit operations and pathways a
    molecule declares are on its row, so a read of Dominion hands the next
    read its ids."""
    [row] = read("dominion", ctx_for(pool), ids=["taq-dna-polymerase"]).rows
    assert row.detail["processCode"] == "P9" and "heat-step" in row.detail["unitOperationIds"]
    assert read("dominion", ctx_for(pool), words="heat-step").summary["count"] >= 1


def test_an_artifact_row_is_worth_what_its_inputs_are_worth_now(pool):  # noqa: F811
    """An artifact computed while its record was verified is stored as
    `computed`. When the record is worth less now (a candidate no one has
    decided, or one a reviewer rejected, which leaves the pool), the row and
    a claim citing it say so: the mark is `basis_provenance` over the inputs
    as they stand, read at read time, as `artifacts.compute` does for a
    repeat, and never the stored file's word (review of OF-BLD-016 §1.R)."""
    from openferment_core.models import Artifact, BasisInput, BasisSource

    def art(aid, record_id):
        return Artifact(id=aid, tool="convert_units", toolVersion="1", provenance="computed",
                        createdAt="2026-10-20T00:00:00Z", outputHash="x", durationMs=1,
                        inputs=[BasisInput(name="record", value=record_id, unit="",
                                           source=BasisSource(kind="record", id=record_id))],
                        output={"value": 900.0, "unit": "mg L-1"})

    undecided = art("00000000000000aa", "cl1-X1-0000000a")  # anchored, decided by nobody: unverified
    rejected = art("00000000000000bb", "cl1-X1-0000000b")  # a reviewer rejected it: not in the pool
    curated = art("00000000000000cc", "r-X1-1")  # the seed's curated record
    forecast = Artifact(id="00000000000000dd", tool="growth_forecast", toolVersion="1", provenance="computed",
                        createdAt="2026-10-20T00:00:00Z", outputHash="x", durationMs=1,
                        inputs=[BasisInput(name="fit", value="00000000000000aa", unit="",
                                           source=BasisSource(kind="artifact", id="00000000000000aa"))],
                        output={"hours": 12.0})
    ctx = ctx_for(pool, artifacts=lambda: [undecided, rejected, curated, forecast])
    r = read("biorepo", ctx, kind="artifact")
    marks = {row.id: row.provenance for row in r.rows}
    assert marks == {"00000000000000aa": "unverified", "00000000000000bb": "demo", "00000000000000cc": "computed",
                     "00000000000000dd": "computed"}  # an artifact input is read as stored, as compute reads it
    seen = SeenSet()
    seen.add(r)
    cites = {"id": "c1", "text": "The conversion is kept as a computed value.", "recordIds": [], "support": "direct",
             "passages": [], "evidenceIds": [], "moduleRefs": ["biorepo/artifact/00000000000000aa"]}
    [c] = validate_plan([cites], seen, pool).claims
    assert c.provenance == "unverified"
    # A module that holds no record input never reads the pool.
    def no_pool():
        raise AssertionError("the pool was read for an artifact with no record input")

    fermos = module_stores.Stores(module_stores.Sources(**{**vars(module_stores.seed_sources(no_pool)),
                                                           "artifacts": lambda: [forecast, undecided]}))
    assert {row.id: row.provenance for row in fermos.rows("fermos")} == {"00000000000000dd": "computed"}


# ── the program switch (OF-BLD-016 §2.3) ──────────────────────────────────


def test_with_the_switch_off_a_read_leaves_archived_rows_out_and_says_so(pool):  # noqa: F811
    from openferment_core import programs

    off = ctx_for(pool, include_archived=False)
    asked = read("geneos", off, ids=["c-necator-h16"])
    assert asked.error is None and asked.rows == [] and asked.summary["count"] == 0
    assert "PHA" in asked.summary["hidden"] and "Settings → Programs" in asked.summary["hidden"]
    hosts = read("geneos", off, kind="host")
    assert hosts.rows and not [r.id for r in hosts.rows if programs.is_archived(programs.program_of("strain", r.id))]
    # A listing, or a read by words, says nothing of what is hidden.
    assert "hidden" not in hosts.summary
    assert "hidden" not in read("geneos", off, words="necator").summary
    # With the switch on, the row is read as before, and nothing is said hidden.
    on = read("geneos", ctx_for(pool), ids=["c-necator-h16"])
    assert [r.id for r in on.rows] == ["c-necator-h16"] and "hidden" not in on.summary


def test_with_the_switch_on_every_module_counts_what_it_did_before(pool):  # noqa: F811
    on, off = ctx_for(pool), ctx_for(pool, include_archived=False)
    for module in module_stores.MODULES:
        every = len(on.stores.all_rows(module))
        assert read(module, on, limit=1).summary["count"] == every, module
        hidden = off.stores.hidden(module)
        # Examples (§3.3) leave with the archive too, without being an
        # archived program's rows (OF-BLD-016 §4.R).
        hidden_ids = {r.id for r in hidden}
        examples = [r for r in on.stores.all_rows(module) if r.detail.get("example") and r.id not in hidden_ids]
        assert read(module, off, limit=1).summary["count"] == every - len(hidden) - len(examples), module
    assert read("dominion", off, limit=1).summary["count"] < read("dominion", on, limit=1).summary["count"]


def test_the_switch_is_not_a_tool_input(pool):  # noqa: F811
    refused = tools.run("geneos_read", {"ids": [], "words": "", "kind": "", "state": "", "limit": 5,
                                        "includeArchived": True}, ctx_for(pool, include_archived=False))
    assert refused.error and "includeArchived" in refused.error
