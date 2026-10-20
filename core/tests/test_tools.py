"""One tool registry and the first two tools (OF-BLD-014 §3.4, E.6).

The pool is a fixture: a tiny corpus.json written here, and candidates made
here, labelled as stand-ins. Unit conversion runs on the real unit tables.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, evidence_pool, intake, tools
from openferment_core.corpus import load_corpus
from openferment_core.models import Candidate, Quantity, ReviewDecision

STAND_IN = "STAND-IN for test_tools: invented records, not a paper's values."

CORPUS = {
    "_fixture": STAND_IN,
    "papers": [
        {"id": "X1", "title": "Polyhydroxybutyrate from xylose hydrolysate", "year": 2020, "textSource": "full-text", "sections": [{"id": "s1", "heading": "Results"}]},
        {"id": "X2", "title": "Casein expression in algae", "year": 2019, "textSource": "curation-note", "sections": [{"id": "s1", "heading": "Results"}]},
    ],
    "records": [
        {"id": "r-X1-1", "paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "fieldLabel": "Secreted titer", "value": 2.5, "unit": "g L-1", "quote": "polyhydroxybutyrate titre on xylose hydrolysate", "provenance": "curated", "status": "unverified", "primary": True, "strainId": "c-necator-h16", "conditions": None, "source": "seed"},
        {"id": "r-X2-1", "paperId": "X2", "sectionId": "s1", "field": "expression_pct_tsp", "fieldLabel": "Expression level (% TSP)", "value": 0.2, "unit": "% TSP", "quote": "casein expression level in algae", "provenance": "curated", "status": "unverified", "primary": True, "strainId": "cw15", "conditions": None, "source": "seed"},
        {"id": "r-X2-2", "paperId": "X2", "sectionId": "s1", "field": "expression_pct_tsp", "fieldLabel": "Expression level (% TSP)", "value": 0.3, "unit": "% TSP", "quote": "casein expression rejected reading", "provenance": "curated", "status": "rejected", "primary": True, "strainId": "cw15", "conditions": None, "source": "seed"},
    ],
}


def _candidate(cid: str, *, field="titer_secreted", value=900.0, unit="mg L-1", organism="c-necator-h16", organism_text="Cupriavidus necator H16", carbon="xylose"):
    return Candidate(
        id=cid, paperId="X1", sectionId="s1", quote="polyhydroxybutyrate on xylose from the extractor",
        field=field, value=value, unit=unit, si=Quantity(value=value, unit=unit),
        organism=organism, organismText=organism_text, carbonSource=carbon,
    )


@pytest.fixture()
def pool(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(CORPUS), encoding="utf-8")
    corpus = load_corpus(str(path))
    rejected = ReviewDecision(status="rejected", provenance="unverified", recordId="cl1-X1-0000000b", at="2026-10-15T00:00:00Z", reviewer="Sean Creighton", rejectReason="wrong field")
    return evidence_pool.build(
        corpus,
        [_candidate("cl1-X1-0000000a"), _candidate("cl1-X1-0000000b"), _candidate("cl1-X1-0000000c", organism="a soil bacterium", organism_text=None, carbon=None)],
        {"cl1-X1-0000000b": rejected},
        [{"id": "titer_secreted", "name": "Secreted titer"}],
    )


def ctx(pool):
    return tools.ToolContext(pool_factory=lambda: pool)


def _search(pool, **kw):
    raw = {"query": "", "field": "", "organism": "", "limit": 10} | kw
    return tools.run("search_records", raw, ctx(pool))


# ── the pool ───────────────────────────────────────────────────────────


def test_the_pool_holds_seed_records_and_unrejected_candidates_as_unverified(pool):
    ids = set(pool.records_by_id)
    assert ids == {"r-X1-1", "r-X2-1", "cl1-X1-0000000a", "cl1-X1-0000000c"}
    cand = pool.record("cl1-X1-0000000a")
    assert (cand["provenance"], cand["status"], cand["source"]) == ("unverified", "unverified", "candidate")
    assert cand["fieldLabel"] == "Secreted titer"


def test_a_resolved_organism_is_a_strain_and_an_unresolved_one_stays_words(pool):
    assert pool.record("cl1-X1-0000000a")["strainId"] == "c-necator-h16"
    words = pool.record("cl1-X1-0000000c")
    assert words["strainId"] is None and words["organismText"] == "a soil bacterium"


# ── search_records ─────────────────────────────────────────────────────


def test_search_records_orders_by_relevance(pool):
    # "titre" stands in one record's quote alone, so that record leads.
    r = _search(pool, query="titre extractor")
    assert r.error is None
    assert r.recordIds[0] == "r-X1-1"
    assert "r-X2-1" not in r.recordIds
    assert r.summary["count"] == len(r.recordIds) == len(r.summary["records"])


def test_search_records_filters_by_field_and_by_strain(pool):
    assert set(_search(pool, field="expression_pct_tsp").recordIds) == {"r-X2-1"}
    assert set(_search(pool, organism="c-necator-h16").recordIds) == {"r-X1-1", "cl1-X1-0000000a"}
    assert _search(pool, query="titre", organism="cw15").recordIds == []


def test_search_records_never_returns_a_rejected_record(pool):
    everything = _search(pool).recordIds + _search(pool, query="casein expression rejected reading").recordIds
    assert "r-X2-2" not in everything and "cl1-X1-0000000b" not in everything


def test_search_records_returns_the_trimmed_shape_with_the_carbon_source(pool):
    rec = next(x for x in _search(pool, organism="c-necator-h16").summary["records"] if x["recordId"] == "cl1-X1-0000000a")
    assert rec["carbonSource"] == "xylose" and rec["provenance"] == "unverified" and rec["strain"] == "c-necator-h16"
    assert "score" not in rec and "matchedTerms" not in rec


def test_search_records_returns_at_most_ten(pool):
    r = tools.run("search_records", {"query": "", "field": "", "organism": "", "limit": 50}, ctx(pool))
    assert len(r.recordIds) <= evidence_pool.MAX_LIMIT


# ── convert_units ──────────────────────────────────────────────────────


def test_convert_units_converts_within_a_family_and_keeps_an_artifact(pool, tmp_path):
    r = tools.run("convert_units", {"recordId": "r-X1-1", "toUnit": "mg L-1"}, ctx(pool))
    assert r.error is None
    (ev,) = r.evidence
    assert ev.value == pytest.approx(2500.0) and ev.unit == "mg L-1"
    assert ev.provenance == "computed", "a curated input does not weaken a computed value below computed"
    assert [i.source.kind for i in ev.basis.inputs] == ["record", "convention"]
    assert ev.basis.inputs[0].source.id == "r-X1-1"
    assert (tmp_path / "artifacts" / f"{ev.basis.artifactId}.json").is_file()
    assert artifacts.replay(ev.basis.artifactId).identical


def test_convert_units_from_an_unverified_record_is_unverified(pool):
    r = tools.run("convert_units", {"recordId": "cl1-X1-0000000a", "toUnit": "g L-1"}, ctx(pool))
    assert r.error is None and r.evidence[0].provenance == "unverified"
    assert r.evidence[0].value == pytest.approx(0.9)


def test_convert_units_refuses_tsp_to_a_concentration_with_the_engines_reason(pool):
    from openferment_core import units

    r = tools.run("convert_units", {"recordId": "r-X2-1", "toUnit": "g L-1"}, ctx(pool))
    assert r.evidence == [] and r.error is not None
    assert units.explain_refusal("% TSP", "g L-1") in r.error


def test_convert_units_refuses_a_record_it_cannot_see(pool):
    r = tools.run("convert_units", {"recordId": "r-X2-2", "toUnit": "% TSP"}, ctx(pool))
    assert r.error and "no record" in r.error


# ── the registry ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        {"query": "PHB", "field": "", "organism": "", "limit": 3, "above": 0.4},
        {"recordId": "r-X1-1", "toUnit": "g L-1", "factor": 1000},
        {"query": "PHB", "field": "", "organism": "", "limit": 3, "nested": {"k": 2}},
        {"query": "PHB", "field": "", "organism": "", "limit": 3, "list": ["a", 7]},
    ],
)
def test_a_number_typed_into_a_tool_input_is_refused(pool, raw):
    name = "convert_units" if "recordId" in raw else "search_records"
    r = tools.run(name, raw, ctx(pool))
    assert r.error and "a number was typed" in r.error
    assert r.evidence == [] and r.recordIds == []


def test_k_and_limit_may_be_numbers_and_only_at_the_top():
    assert tools.numbers_in({"limit": 3, "k": 5, "query": "x"}) == []
    assert tools.numbers_in({"limit": 2.5}) == ["limit"]
    assert tools.numbers_in({"limit": True}) == [], "a boolean is not a number here"
    assert tools.numbers_in({"a": {"limit": 3}}) == ["a.limit"]


def test_an_unknown_tool_or_a_wrong_input_is_a_result_with_an_error(pool):
    assert "no tool named" in tools.run("nonesuch", {}, ctx(pool)).error
    assert "refused its input" in tools.run("search_records", {"query": "x"}, ctx(pool)).error
    assert "refused its input" in tools.run("convert_units", {"recordId": "r-X1-1", "toUnit": "g L-1", "extra": "x"}, ctx(pool)).error


def test_a_summary_over_the_limit_is_replaced_by_an_error(monkeypatch, pool):
    from openferment_core.models import ToolResult

    big = tools.Tool("search_records", "d", tools.records.SearchRecordsInput, lambda i, c: ToolResult(summary={"x": "y" * 10_000}))
    monkeypatch.setitem(tools.REGISTRY, "search_records", big)
    r = _search(pool)
    assert r.summary == {} and "over the 9000" in r.error


MODULES = ("dominion", "runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild", "primer", "intake", "home")
READS = [f"{m}_read" for m in MODULES] + [f"{m}_write" for m in MODULES]
# The one literal list of the registry's names the tests hold it to; every
# other test derives its count from tools.WHITELIST (OF-BLD-019 §6.1).
NAMES = (["search_records", "convert_units", "search_passages", "yield_ceiling", "growth_forecast", "selling_price",
          "draft_runbook"] + READS + ["thermo_props", "run_flowsheet", "stream_table"])


def test_only_the_whitelisted_names_may_register():
    with pytest.raises(ValueError):
        tools.register(tools.Tool("run_shell", "d", tools.records.SearchRecordsInput, lambda i, c: None))
    assert [t.name for t in tools.infos()] == NAMES == list(tools.WHITELIST)


# ── the endpoints ──────────────────────────────────────────────────────


@pytest.fixture()
def client(pool, monkeypatch):
    from openferment_core import api

    monkeypatch.setattr(tools.ToolContext, "pool", property(lambda self: pool))
    return TestClient(api.app, base_url="http://127.0.0.1")


def test_get_tools_lists_names_descriptions_and_schemas(client):
    body = client.get("/api/tools").json()
    assert [t["name"] for t in body] == NAMES
    assert body[0]["inputSchema"]["properties"]["query"]["type"] == "string"
    assert all(len(t["description"]) > 80 for t in body)


def test_post_runs_a_tool_and_refuses_numbers_like_the_loop(client):
    ok = client.post("/api/tools/search_records", json={"query": "", "field": "", "organism": "c-necator-h16", "limit": 5})
    assert ok.status_code == 200 and set(ok.json()["recordIds"]) == {"r-X1-1", "cl1-X1-0000000a"}
    refused = client.post("/api/tools/convert_units", json={"recordId": "r-X1-1", "toUnit": "g L-1", "value": 3})
    assert refused.status_code == 200 and "a number was typed" in refused.json()["error"]
    assert client.post("/api/tools/nonesuch", json={}).status_code == 404


def test_the_request_guard_covers_the_tool_endpoint(client):
    r = client.post("/api/tools/search_records", json={"query": "", "field": "", "organism": "", "limit": 1}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


# ── selling_price (§8.5) ───────────────────────────────────────────────


def test_selling_price_refuses_with_no_run_and_names_what_waits(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from openferment_core import intake

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    # sc-pha-1 is PHA's, an archived program: the switch is on here, and
    # test_programs holds the refusal with it off (OF-BLD-016 §2.R).
    ctx = tools.ToolContext(pool_factory=lambda: SimpleNamespace(records=[], records_by_id={}), include_archived=True)
    r = tools.run("selling_price", {"scenarioId": "sc-pha-1"}, ctx)
    assert r.error and "no run of sc-pha-1 exists" in r.error and "price of fermentable sugar" in r.error
    assert "no BioSTEAM scenario" in tools.run("selling_price", {"scenarioId": "sc-s1"}, ctx).error


def test_selling_price_cites_the_latest_run_a_person_produced(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from openferment_core import demo, intake, proforma
    from openferment_core.models import InputAssumption, ProformaRunRequest

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", demo._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    a = [InputAssumption(key=k, value=v, low=v, high=v, by="Sean Creighton", at="2026-10-15")
         for k, v in (("recovery", 0.95), ("sugarPrice", 0.4), ("sugarFeed", 1000.0))]
    run = proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=a), pool=pool)
    r = tools.run("selling_price", {"scenarioId": "sc-pha-1"}, tools.ToolContext(pool_factory=lambda: pool, include_archived=True))
    assert r.error is None and r.evidence[0].id == run.artifactId and r.evidence[0].figure == "distribution"
    assert r.summary["provenance"] == "demo" and r.summary["assumedInputs"] == ["recovery", "sugarFeed", "sugarPrice"]
    assert r.evidence[0].interval.low <= r.evidence[0].value <= r.evidence[0].interval.high


def test_selling_price_cites_the_stored_benchmark_and_runs_nothing(monkeypatch, tmp_path):
    from openferment_core import intake, proforma

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    ctx = tools.ToolContext()
    r = tools.run("selling_price", {"scenarioId": "proforma_benchmark"}, ctx)
    assert r.error and "has not been run on this service" in r.error
    # A STAND-IN benchmark output, so the stored artifact exists without BioSTEAM.
    monkeypatch.setattr(proforma, "call", lambda op, args: {
        "package": "biorefineries.cornstover@stand-in", "biosteam": "stand-in", "mespUsdPerGal": 2.5,
        "mespUsdPerKg": 0.8, "ethanolDensityKgPerGal": 3.0, "settings": {}, "references": []})
    art = proforma.run_benchmark()
    monkeypatch.setattr(proforma, "call", lambda op, args: pytest.fail("the tool ran the benchmark"))
    r = tools.run("selling_price", {"scenarioId": "proforma_benchmark"}, ctx)
    assert r.error is None and r.evidence[0].id == art.id
    assert r.evidence[0].value == 2.5 and r.evidence[0].unit == "USD gal⁻¹"
    assert r.summary["provenance"] == r.evidence[0].provenance


# Live test, 2026-10-16: told "an empty string for any field", the model sent
# the two characters "" and every such search came back empty. The filters
# are nullable now, null means unused, and the literal "" means the same.
@pytest.mark.parametrize("unused", [None, '""', "", "''"])
def test_an_unused_filter_is_null_and_the_literal_quotes_mean_the_same(pool, unused):
    r = _search(pool, field=unused, organism=unused)
    assert r.error is None
    assert set(r.recordIds) == set(_search(pool, field=None, organism=None).recordIds)
    assert r.recordIds, "an unused filter filters nothing"
    assert r.summary["field"] is None and r.summary["organism"] is None


def test_the_schema_offers_null_for_an_unused_filter():
    schema = tools.REGISTRY["search_records"].input_model.model_json_schema()
    for name in ("field", "organism"):
        prop = schema["properties"][name]
        assert {"type": "null"} in prop.get("anyOf", []), prop
        assert "null" in prop["description"] and "empty string" not in prop["description"]


# ── run_flowsheet and stream_table (OF-BLD-019 §6.1) ───────────────────


@pytest.fixture()
def proforma_store(tmp_path, monkeypatch):
    """A throwaway store, the audit log and the proposals in it, and demo.py's
    STAND-IN evaluator answering for the BioSTEAM worker over STAND-IN records,
    as the offline Proforma tests run."""
    from types import SimpleNamespace

    from openferment_core import audit, demo, proforma, proposals

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(audit, "PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", tmp_path / "proposals.json")
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    monkeypatch.setattr(proforma, "call", demo._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}, path=tmp_path)


def _pcx(pool_, archived=True):
    c = tools.ToolContext(pool_factory=lambda: pool_, include_archived=archived)
    c.ask_id, c.model = "ask-61", "claude-haiku-5-5"
    return c


def _a_person_kept_assumptions(monkeypatch):
    """STAND-IN for a service that holds a named person's assumptions. This
    service holds none (they live in the browser's Durable tier), so a real
    call binds records alone and the PHA draft's three assumptions wait."""
    from openferment_core import proforma
    from openferment_core.models import InputAssumption

    kept = [InputAssumption(key=k, value=v, low=v, high=v, by="Sean Creighton", at="2026-10-15", note=STAND_IN)
            for k, v in (("recovery", 0.95), ("sugarPrice", 0.4), ("sugarFeed", 1000.0))]
    real = proforma.bind
    monkeypatch.setattr(proforma, "bind", lambda records, host=None, assumptions=None, cap=None:
                        real(records, host, assumptions or kept, cap))


def test_run_flowsheet_runs_a_scenario_as_bound_keeps_one_run_and_marks_it_as_the_models(proforma_store, monkeypatch):
    from openferment_core import audit, proposals

    _a_person_kept_assumptions(monkeypatch)
    r = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store))
    assert r.error is None, r.error
    s = r.summary
    (ev,) = r.evidence
    assert s["state"] == "open" and s["scenarioId"] == "sc-pha-1" and s["flowsheet"] == "pha_sugar_v0"
    assert ev.id == s["artifactId"] == s["evidenceId"] and ev.figure == "distribution"
    art = artifacts.get(ev.id)
    assert art.tool == "proforma.run" and s["provenance"] == art.provenance == "demo"  # an assumption remains
    assert s["costLines"] and {i["binding"] for i in s["inputs"]} == {"records", "assumption"}
    assert len(json.dumps(s, ensure_ascii=False)) <= tools.MAX_SUMMARY_CHARS
    [line] = audit.read()
    assert (line.agent, line.who, line.module, line.action, line.state, line.target, line.askId, line.effort) == (
        "model", "claude-haiku-5-5", "proforma", "run", "open", "sc-pha-1", "ask-61", "medium")
    assert line.detail["tool"] == "run_flowsheet" and line.detail["artifactId"] == ev.id
    # At no gate: nothing was proposed.
    assert proposals.read().proposals == []
    # proforma_write's run is the same run, marked with its own name.
    w = tools.run("proforma_write", {"action": "run", "target": "sc-pha-1", "fields": {}, "note": "again"}, _pcx(proforma_store))
    assert w.error is None and w.evidence[0].id == ev.id
    assert audit.read()[-1].detail["tool"] == "proforma_write" and audit.read()[-1].detail["note"] == "again"


def test_run_flowsheet_with_an_input_waiting_returns_the_422s_words_and_keeps_nothing(proforma_store):
    from openferment_core import audit

    r = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store))
    assert r.error and r.error.startswith("run_flowsheet refused: these inputs wait for a source")
    assert "recovery, sugarPrice, sugarFeed" in r.error and "a model never supplies one" in r.error
    assert r.evidence == [] and audit.read() == [] and artifacts.all_artifacts() == []
    w = tools.run("proforma_write", {"action": "run", "target": "sc-pha-1", "fields": {}, "note": ""}, _pcx(proforma_store))
    assert w.error == r.error.replace("run_flowsheet", "proforma_write", 1)


def test_run_flowsheet_refuses_a_scenario_it_does_not_hold_in_words(proforma_store, monkeypatch):
    from openferment_core import audit, pureos

    seed = [{"id": "sc-pha-1", "kind": "biosteam", "modelId": "pha_sugar_v0", "program": "pha"},
            {"id": "sc-s1", "kind": "authored", "modelId": "S1", "program": "casein"}]
    monkeypatch.setattr(pureos, "seed_scenarios", lambda: seed)
    c = _pcx(proforma_store)
    made_here = tools.run("run_flowsheet", {"scenarioId": "sc-mg2k1-1"}, c).error
    assert "is not a scenario this service holds" in made_here and "the browser that made it" in made_here
    assert "sc-pha-1" in made_here
    assert "authored cost surface" in tools.run("run_flowsheet", {"scenarioId": "sc-s1"}, c).error
    assert "name the scenario" in tools.run("run_flowsheet", {"scenarioId": " "}, c).error
    # With no projection to read, proforma.run's own words refuse it.
    monkeypatch.setattr(pureos, "seed_scenarios", lambda: [])
    # (§2.3's flowsheet_of writes them: a seed id runs its own flowsheet, and
    # an id the seed lacks names no flowsheet to run.)
    assert "there is no seed scenario sc-nonesuch" in tools.run("run_flowsheet", {"scenarioId": "sc-nonesuch"}, c).error
    # An empty target is refused too: proforma_write no longer runs sc-pha-1 unnamed.
    assert "name the scenario" in tools.run("proforma_write", {"action": "run", "target": "", "fields": {}, "note": ""}, c).error
    assert audit.read() == []


def test_run_flowsheet_refuses_an_archived_scenario_with_the_switch_off(proforma_store):
    off = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store, archived=False))
    assert off.error and "archived (hidden)" in off.error and "Settings → Programs" in off.error


@pytest.mark.parametrize("name, raw", [
    ("run_flowsheet", {"scenarioId": "sc-pha-1", "samples": 500}),
    ("run_flowsheet", {"scenarioId": "sc-pha-1", "sugarPrice": 0.4}),
    ("stream_table", {"artifactId": 7}),
])
def test_a_number_in_a_proforma_tools_input_is_refused(proforma_store, name, raw):
    r = tools.run(name, raw, _pcx(proforma_store))
    assert r.error and "a number was typed" in r.error and artifacts.all_artifacts() == []


def test_run_flowsheet_takes_no_assumption_even_in_words(proforma_store):
    r = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1", "assumptions": "sugar at forty cents"}, _pcx(proforma_store))
    assert r.error and "refused its input" in r.error
    assert "never type an assumption" in tools.REGISTRY["run_flowsheet"].description
    assert "never type a number" in tools.REGISTRY["stream_table"].description
    assert not tools.REGISTRY["run_flowsheet"].strict and not tools.REGISTRY["stream_table"].strict


def test_stream_table_reads_a_kept_run_with_its_rows_and_the_whole_table_in_data(proforma_store, monkeypatch):
    _a_person_kept_assumptions(monkeypatch)
    run = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store))
    aid = run.summary["artifactId"]
    r = tools.run("stream_table", {"artifactId": aid}, _pcx(proforma_store))
    assert r.error is None, r.error
    s = r.summary
    assert s["tool"] == "proforma.run" and s["evidenceId"] == aid and s["scenarioId"] == "sc-pha-1"
    assert r.evidence[0].id == aid and r.evidence[0] == run.evidence[0], "one artifact, one evidence, whichever tool read it"
    assert s["streamCount"] == s["shown"] == len(s["streams"]) and s["leftOut"] == 0 and "cut" not in s
    # Feeds and products first, then the streams between units.
    edges = [row["from"] is None or row["to"] is None for row in s["streams"]]
    assert edges == sorted(edges, reverse=True) and edges[0]
    sugar = next(row for row in s["streams"] if row["id"] == "sugar")
    assert sugar["to"] == "R1" and sugar["from"] is None and "Glucose" in sugar["components"] and "price" in sugar
    # data holds the table whole, every number as the run kept it.
    from openferment_core import proforma

    whole = proforma.tables_of(artifacts.get(aid))
    assert r.data["streams"] == [x.model_dump(mode="json") for x in whole.streams]
    assert r.data["tableUnits"] == whole.tableUnits and r.data["artifactId"] == aid


def test_stream_table_cuts_a_long_table_to_the_cap_and_says_how_many_it_left_out(proforma_store, monkeypatch):
    from openferment_core import proforma
    from openferment_core.models import StreamRow

    _a_person_kept_assumptions(monkeypatch)
    aid = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store)).summary["artifactId"]
    # A STAND-IN table far past the cap: a feed, a product, and many streams between units.
    flows = {f"STAND-IN chemical {n}": float(n + 1) for n in range(12)}
    rows = [StreamRow(id="feed", source=None, sink="U0", phase="l", T=298.15, P=101325.0, massFlow=78.0, massFlows=flows),
            *[StreamRow(id=f"s{n}", source=f"U{n}", sink=f"U{n + 1}", phase="l", T=300.0 + n, P=101325.0,
                        massFlow=78.0, massFlows=flows) for n in range(200)],
            StreamRow(id="product", source="U200", sink=None, phase="l", T=350.0, P=101325.0, massFlow=78.0,
                      massFlows=flows, price=1.5)]
    real = proforma.tables_of
    monkeypatch.setattr(proforma, "tables_of", lambda art: real(art).model_copy(update={"streams": rows}))
    r = tools.run("stream_table", {"artifactId": aid}, _pcx(proforma_store))
    assert r.error is None, r.error
    s = r.summary
    assert len(json.dumps(s, ensure_ascii=False, default=str)) <= tools.MAX_SUMMARY_CHARS
    assert s["streamCount"] == len(rows) and s["shown"] + s["leftOut"] == len(rows) and 0 < s["shown"] < len(rows)
    assert s["cut"].startswith(f"{s['leftOut']} of {len(rows)} streams left out")
    assert [row["id"] for row in s["streams"][:2]] == ["feed", "product"], "a cut never drops what enters or leaves"
    assert len(s["streams"][0]["components"]) == 5 and s["streams"][0]["otherComponents"] == 7
    assert len(r.data["streams"]) == len(rows) and r.data["streams"][5]["massFlows"] == flows
    assert r.evidence and r.evidence[0].id == aid


def test_stream_table_reads_a_reference_run_and_cites_the_price_its_package_gives(proforma_store):
    from openferment_core import proforma
    from openferment_core.flowsheets import shelf

    art = proforma.run_reference("corn_drygrind")
    r = tools.run("stream_table", {"artifactId": art.id}, _pcx(proforma_store))
    assert r.error is None, r.error
    (ev,) = r.evidence
    corn = shelf.SHELF["corn_drygrind"]
    assert ev.id == art.id == r.summary["evidenceId"] and ev.value == art.output[corn.priceOutput]
    assert ev.unit == corn.priceBasis and ev.provenance == art.provenance and ev.basis.tool == "proforma.reference"
    assert r.summary["tool"] == "proforma.reference" and r.summary["scenarioId"] is None
    assert len(r.data["streams"]) == r.summary["streamCount"] == len(proforma.tables_of(art).streams)
    # Proforma's rows list the reference run beside the scenarios' (ARTIFACT_MODULE).
    read = tools.run("proforma_read", {"ids": [], "words": "", "kind": "artifact", "state": "", "limit": 20},
                     _pcx(proforma_store))
    assert read.error is None and f"proforma/artifact/{art.id}" in [row.ref for row in read.rows]


def test_stream_table_refuses_what_is_not_a_proforma_run_in_words(pool, proforma_store):
    from openferment_core import proforma

    conv = tools.run("convert_units", {"recordId": "r-X1-1", "toUnit": "mg L-1"}, ctx(pool))
    assert conv.error is None
    kept = conv.evidence[0].basis.artifactId
    other = tools.run("stream_table", {"artifactId": kept}, _pcx(proforma_store))
    assert other.error == (f"stream_table refused: {kept} is a convert_units artifact, not a Proforma run; "
                           f"it reads the stream table of a {proforma.RUN} or {proforma.REFERENCE} artifact")
    assert "no kept artifact" in tools.run("stream_table", {"artifactId": "0123456789abcdef"}, _pcx(proforma_store)).error
    assert "no kept artifact" in tools.run("stream_table", {"artifactId": "../corpus"}, _pcx(proforma_store)).error
    assert other.evidence == [] and other.data is None


def test_stream_table_refuses_an_archived_run_with_the_switch_off(proforma_store, monkeypatch):
    _a_person_kept_assumptions(monkeypatch)
    aid = tools.run("run_flowsheet", {"scenarioId": "sc-pha-1"}, _pcx(proforma_store)).summary["artifactId"]
    off = tools.run("stream_table", {"artifactId": aid}, _pcx(proforma_store, archived=False))
    assert off.error and "PHA, archived (hidden)" in off.error and "Settings → Programs" in off.error
    assert off.evidence == [] and off.data is None
