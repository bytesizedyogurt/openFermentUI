"""One read tool per module (OF-BLD-015 §7.2), through `tools.run`.

The module rows come from a small projection written here: fictional
runbooks, a host and a lesson, handed in as a catalogue no store holds yet
would be. The service's stores are stand-ins, so nothing here reads a key,
the network or this machine's data; the last test reads the project's own
rows (project_state.py).
"""
from __future__ import annotations

import json

import pytest

from openferment_core import module_stores, postdoc_agent, tools
from openferment_core.models import Checks, Guild, GuildPerson
from openferment_core.validate import SeenSet, validate_plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

STATES = {"open", "fenced", "approved", "locked", "proposed", "retired"}


# Fictional rows, chosen to be found by whole words and heads and by nothing else.
PROJECTION = {
    "runbooks": {
        "runbooks": [{"id": "rb-zeta", "title": "Zetase — pilot process", "kind": "research", "status": "needs_review",
                      "lockedAt": None, "productId": None, "strainId": None, "predictions": []},
                     {"id": "rb-omega", "title": "Omegase — bench trial", "kind": "research", "status": "ready",
                      "lockedAt": "2026-10-01T00:00:00Z", "productId": None, "strainId": None, "predictions": []}],
        "protocols": [],
    },
    "geneos": {"hosts": [{"id": "h-zeta", "name": "Zetamyces testii Z1", "badges": [], "bsl": 1},
                         {"id": "s-cerevisiae-cenpk113-7d", "name": "Saccharomyces cerevisiae CEN.PK113-7D",
                          "badges": [], "bsl": 1}],
               "pathways": []},
    "proforma": {"scenarios": []},
    "primer": {"lessons": [{"id": "l-ster", "title": "Sterilising and releasing a vessel",
                            "moduleTitle": "Why extraction comes first", "blurb": "", "skills": []}]},
}


def ctx_for(pool_, **over):  # noqa: F811
    """The service's sources over the fictional projection, with the test's
    stand-ins laid on."""
    def make():
        src = module_stores.fixture_sources(lambda: pool_)
        src.projection = lambda: json.loads(json.dumps(PROJECTION))
        for k, v in over.items():
            setattr(src, k, v)
        return module_stores.Stores(src)

    return tools.ToolContext(pool_factory=lambda: pool_, stores_factory=make)


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


def test_words_and_refs_both_find_a_row(pool):  # noqa: F811
    ctx = ctx_for(pool)
    assert read("runbooks", ctx, words="omegase bench").rows[0].id == "rb-omega"
    assert read("runbooks", ctx, ids=["runbooks/runbook/rb-omega"]).rows[0].state == "locked"
    assert read("geneos", ctx, words="zetamyces").rows[0].id == "h-zeta"


def test_a_number_a_wrong_kind_and_a_wrong_state_are_refused_in_words(pool):  # noqa: F811
    ctx = ctx_for(pool)
    assert "a number was typed" in tools.run("runbooks_read", {"ids": [], "words": "", "kind": "", "state": "",
                                                               "limit": 5, "ids_extra": 3}, ctx).error
    assert "not a kind" in read("pureos", ctx, kind="molecule").error
    assert "refused its input" in read("runbooks", ctx, state="free").error


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
    seen.add(read("runbooks", ctx, ids=["rb-omega"]))
    cited = {"id": "c1", "text": "The Omegase runbook is locked.", "recordIds": [], "support": "direct", "passages": [],
             "evidenceIds": [], "moduleRefs": ["runbooks/runbook/rb-omega"]}
    ghost = dict(cited, id="c2", moduleRefs=["runbooks/runbook/rb-zeta"])
    out = validate_plan([cited, ghost], seen, pool)
    assert [c.id for c in out.claims] == ["c1"] and out.claims[0].provenance == "unverified", "a runbook row carries no mark of its own"
    assert out.rejected == 1 and "no tool returned" in out.reasons[0]
    refused = SeenSet()
    refused.add(read("pureos", ctx, kind="molecule"))
    assert not refused.rows


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
    # Every tool after the seven goes out loose: the module pairs, and
    # OF-BLD-019's thermo_props (§4.2), run_flowsheet and stream_table (§6.1).
    assert {t["name"] for t in sent if not t["strict"]} == set(tools.WHITELIST[7:])
    assert {f"{m}_{w}" for m in module_stores.MODULES for w in ("read", "write")} <= set(tools.WHITELIST[7:])
    assert "refused its input" in tools.run("runbooks_read", {"ids": "rb-omega", "words": "", "kind": "", "state": "",
                                                              "limit": 5}).error


# ── tuned on the first live runs (2026-10-20) ─────────────────────────────


def test_a_word_finds_a_row_by_its_head(pool):  # noqa: F811
    """Haiku searched Primer for "depos" and found nothing where a person
    would have read "Depositing" as a match: a query word of four letters or
    more matches the head of a row's word, and the module's blurb counts."""
    ctx = ctx_for(pool)
    assert [r.id for r in read("primer", ctx, words="steril").rows] == ["l-ster"]  # "Sterilising and releasing a vessel"
    assert read("primer", ctx, words="ste").summary["count"] == 0  # three letters is too short a head
    assert read("primer", ctx, words="extract").summary["count"] >= 1  # the module's title, "Why extraction comes first"


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
    assert marks == {"00000000000000aa": "unverified", "00000000000000bb": "assumed", "00000000000000cc": "computed",
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

    fermos = module_stores.Stores(module_stores.Sources(**{**vars(module_stores.fixture_sources(no_pool)),
                                                           "artifacts": lambda: [forecast, undecided]}))
    assert {row.id: row.provenance for row in fermos.rows("fermos")} == {"00000000000000dd": "computed"}


# ── the program switch (OF-BLD-016 §2.3) ──────────────────────────────────


def test_the_switch_is_not_a_tool_input(pool):  # noqa: F811
    refused = tools.run("geneos_read", {"ids": [], "words": "", "kind": "", "state": "", "limit": 5,
                                        "includeArchived": True}, ctx_for(pool))
    assert refused.error and "includeArchived" in refused.error


# ── fermOS reads its simulations (OF-BLD-020 §3.4) ─────────────────────────


def _numbers_in(value):
    """Every int or float under a row's detail (a boolean is a flag, not one)."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return []
    if isinstance(value, (int, float)):
        return [value]
    items = value.values() if isinstance(value, dict) else value
    return [n for v in items for n in _numbers_in(v)]


def _kept_simulation(tmp_path, monkeypatch):
    """A batch_v1 simulation on a named person's STAND-IN values alone, kept
    in a throwaway store: test_fermos_bind's typed values, none a result."""
    from openferment_core import artifacts, fermos, intake
    from openferment_core.models import SimulationRequest
    from test_fermos_bind import TYPED, pool_of, typed

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    r = fermos.simulate(SimulationRequest(family="batch_v1", strain="s-cerevisiae-cenpk113-7d", product="ethanol",
                                          sugar="glucose", overrides=typed(ks=0.2, yxs=0.12, yps=0.45, mu_max=0.3,
                                                                           s0=50.0, **TYPED)), by_pool=pool_of())
    return artifacts.get(r.artifactId)


def test_fermos_reads_a_kept_simulation_as_its_own_kind_with_no_number_in_its_detail(pool, tmp_path, monkeypatch):  # noqa: F811
    art = _kept_simulation(tmp_path, monkeypatch)
    # The stored word says computed; the inputs say a person typed them, and the row says what they say now.
    doctored = art.model_copy(update={"provenance": "computed"})
    ctx = ctx_for(pool, artifacts=lambda: [doctored])
    r = read("fermos", ctx, kind="simulation")
    assert r.error is None
    [row] = r.rows
    assert row.ref == f"fermos/simulation/{art.id}" and row.kind == "simulation" and row.id == art.id
    assert row.label == "Batch (batch_v1) simulation of Saccharomyces cerevisiae CEN.PK113-7D"
    assert (row.state, row.status, row.provenance) == ("open", "computed", "assumed")
    assert row.detail["family"] == "batch_v1" and row.detail["strain"] == "s-cerevisiae-cenpk113-7d"
    assert set(row.detail["boundBy"]["assumption"]) >= {"mu_max", "ks", "x0"} and "convention" in row.detail["boundBy"]
    assert _numbers_in(row.detail) == [], "a simulation's numbers stay in its artifact"
    # A read by its id finds it; the artifact kind lists fits and forecasts and not it.
    assert [x.id for x in read("fermos", ctx, ids=[art.id]).rows] == [art.id]
    assert read("fermos", ctx, kind="artifact").rows == []
    assert "simulation" in tools.REGISTRY["fermos_read"].description


def test_a_simulation_read_as_a_row_is_cited_by_its_ref_and_one_cited_by_evidence_id_is_told_so(pool, tmp_path,
                                                                                                monkeypatch):  # noqa: F811
    art = _kept_simulation(tmp_path, monkeypatch)
    seen = SeenSet()
    seen.add(read("fermos", ctx_for(pool, artifacts=lambda: [art]), kind="simulation"))
    ref = f"fermos/simulation/{art.id}"
    assert seen.runs == {art.id: ref}, "SeenSet learns the simulation from its row"
    by_ref = {"id": "c1", "text": "The batch simulation ran until its sugar ran out.", "recordIds": [],
              "support": "direct", "passages": [], "evidenceIds": [], "moduleRefs": [ref]}
    by_id = dict(by_ref, id="c2", moduleRefs=[], evidenceIds=[art.id])
    ghost = dict(by_ref, id="c3", moduleRefs=["fermos/simulation/0123456789abcdef"])
    out = validate_plan([by_ref, by_id, ghost], seen, pool)
    assert [c.id for c in out.claims] == ["c1"] and out.claims[0].provenance == "assumed"
    assert out.rejected == 2
    assert out.reasons[0].startswith(f"c2: cites {art.id} by evidence id, which a read returned only as a row: cite {ref}")
    assert out.reasons[1].startswith("c3: cites what no tool returned in this run")


def test_a_loose_tool_keeps_its_maps_and_a_strict_one_stays_closed():
    """recordsByParam is keys to record ids (OF-BLD-020 §3.4): closing every
    object told the model it took nothing. A loose tool's map goes out with
    its value schema; a strict tool's objects stay closed, as the API needs."""
    from openferment_core import llm

    sent = {t["name"]: llm.tool_param(t["name"], t["description"], t["input_schema"], t["strict"])
            for t in postdoc_agent._tool_defs()}
    sim = sent["fermos_simulate"]["input_schema"]
    assert sim["additionalProperties"] is False
    assert sim["properties"]["recordsByParam"]["additionalProperties"] == {"items": {"type": "string"}, "type": "array"}
    assert sent["fermos_write"]["input_schema"]["properties"]["fields"]["additionalProperties"] == {"type": "string"}
    closed = llm.strict_schema(tools.REGISTRY["fermos_simulate"].info().inputSchema)
    assert closed["properties"]["recordsByParam"]["additionalProperties"] is False

    def maps(node):
        if isinstance(node, dict):
            return int(isinstance(node.get("additionalProperties"), dict)) + sum(maps(v) for v in node.values())
        return sum(maps(v) for v in node) if isinstance(node, list) else 0

    assert not any(maps(t["input_schema"]) for t in sent.values() if t["strict"])


def test_pureos_reads_a_train_a_model_built_as_kind_train(pool):  # noqa: F811
    """OF-BLD-020 §5.4: a train a model built is kept on the service and read
    as kind train, its ref `pureos/train/<train id>`, a detail of ids and words
    alone. The train is a STAND-IN written here."""
    from openferment_core.models import KeptTrain, TrainSpec

    spec = TrainSpec.model_validate({
        "id": "tr-0123456789ab", "name": "ethanol train, built by a model", "program": "yeast", "product": "ethanol",
        "inlet": {"kind": "run-stream", "ref": "0123456789abcdef", "streamId": "beer"},
        "units": [{"id": "C1", "type": "centrifugation", "records": {"split.Ethanol": ["r-X1-1"]}}]})
    k = KeptTrain(spec=spec, madeBy="claude-haiku-5-5", at="2026-10-21T00:00:00+00:00",
                  updatedAt="2026-10-21T00:00:00+00:00")
    r = read("pureos", ctx_for(pool, kept_trains=lambda: [k]), ids=[spec.id])
    [row] = r.rows
    assert (row.ref, row.kind, row.state, row.status, row.provenance) == (
        "pureos/train/tr-0123456789ab", "train", "open", "built by a model", None)
    assert row.detail["recordsNamed"] == {"C1": ["split.Ethanol"]} and row.detail["runs"] == []
    assert row.detail["madeBy"] == "claude-haiku-5-5" and _numbers_in(row.detail) == []
    seen = SeenSet()
    seen.add(r)
    assert row.ref in seen.rows and not seen.runs, "a train is data: its runs are the kept runs"


def test_the_module_reads_list_the_runbooks_and_scenarios_the_project_keeps(pool):  # noqa: F811
    """A runbook the project adopted, with its lock, and a scenario made with
    New scenario are the project's rows (project_state.py), and the module
    reads list them beside what a fixture hands in."""
    from openferment_core import project_state

    who = "Ada Moreno"
    project_state.put("runbooks", "rb-kept-1", {
        "id": "rb-kept-1", "kind": "research", "title": "Kappase — pilot run", "status": "draft", "stages": [],
        "note": "", "eta": None, "outputs": [], "productId": None, "progressPct": 0, "estCostUsd": None,
        "strainId": None, "measurementSchema": [], "lockedAt": None, "lockHash": None,
        "predictions": [{"id": "p1", "label": "Final titre", "value": 1, "unit": "g/L", "confidence": "low",
                         "basis": "a placeholder"}]}, who)
    project_state.put("scenarios", "sc-kept-1", {
        "id": "sc-kept-1", "modelId": "ethanol_glucose_v0", "flowsheetId": "ethanol_glucose_v0", "kind": "biosteam",
        "name": "Kept ethanol", "description": "", "product": "", "dims": [], "point": {}, "assumptions": [],
        "pinned": False}, who)

    def stores():
        return module_stores.Stores(module_stores.default_sources(lambda: pool))

    (rb,) = [r for r in stores().rows("runbooks") if r.id == "rb-kept-1"]
    assert (rb.label, rb.state, rb.detail["predictions"]) == ("Kappase — pilot run", "open", ["Final titre"])
    assert "Kappase" in rb.names
    project_state.put("runbookLocks", "rb-kept-1", {"lockedAt": "2026-10-31T00:00:00Z", "lockHash": "0123abcd"}, who)
    (rb,) = [r for r in stores().rows("runbooks") if r.id == "rb-kept-1"]
    assert rb.state == "locked" and rb.detail["lockedAt"] == "2026-10-31T00:00:00Z"
    (sc,) = [r for r in stores().rows("proforma") if r.kind == "scenario"]
    assert (sc.id, sc.label, sc.detail["modelId"]) == ("sc-kept-1", "Kept ethanol", "ethanol_glucose_v0")
    found = read("runbooks", tools.ToolContext(pool_factory=lambda: pool), words="kappase")
    assert found.error is None and [row.id for row in found.rows] == ["rb-kept-1"]
