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
    assert artifacts.get(ev.basis.artifactId).id == ev.basis.artifactId
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


MODULES = ("runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild", "primer", "intake", "home")
READS = [f"{m}_read" for m in MODULES] + [f"{m}_write" for m in MODULES]
# The one literal list of the registry's names the tests hold it to; every
# other test derives its count from tools.WHITELIST (OF-BLD-019 §6.1).
NAMES = (["search_records", "convert_units", "search_passages", "yield_ceiling", "growth_forecast", "selling_price",
          "draft_runbook"] + READS + ["thermo_props", "run_flowsheet", "stream_table", "fermos_simulate",
                                       "fermos_vessel", "pureos_build", "pureos_propose"])


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


# A seed scenario written for these tests (the seed's went with it, alpha 2.0
# ADR-010): a BioSTEAM scenario on the glucose-to-ethanol flowsheet.
TEST_SEED = [{"id": "sc-test-ethanol", "kind": "biosteam", "modelId": "ethanol_glucose_v0", "name": "Test ethanol scenario"}]


@pytest.fixture()
def test_seed(monkeypatch):
    from openferment_core import proforma

    monkeypatch.setattr(proforma, "seed_scenarios", lambda: TEST_SEED)
    return TEST_SEED[0]["id"]


def _yeast_pool(drop=()):
    """demo.py's STAND-IN yeast records (thread Q paper ids), less the fields
    a test drops."""
    from types import SimpleNamespace

    import standins
    rs = [r for r in standins._standin_yeast_records() if r["field"] not in drop]
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


def _yeast_assumed():
    from openferment_core.models import InputAssumption

    return [InputAssumption(key="plant_scale", value=100000.0, low=100000.0, high=100000.0, by="Sean Creighton",
                            at="2026-10-20", note=STAND_IN),
            InputAssumption(key="glucose_price", value=0.4, low=0.3, high=0.5, by="Sean Creighton", at="2026-10-20",
                            note=STAND_IN)]


def test_selling_price_cites_the_newest_run_of_a_seed_scenario(proforma_store, monkeypatch, test_seed):
    """OF-BLD-019 §6.R (review findings 2 and 15): selling_price reads the
    newest kept run of the scenario it is asked about."""
    from openferment_core import proforma
    from openferment_core.flowsheets import shelf
    from openferment_core.models import ProformaRunRequest

    pool = _yeast_pool()
    stamps = iter(["2026-10-20T10:00:00Z", "2026-10-20T11:00:00Z"])
    monkeypatch.setattr(artifacts, "_now", lambda: next(stamps))
    older = proforma.run(ProformaRunRequest(scenarioId=test_seed, assumptions=_yeast_assumed(), samples=8), pool=pool)
    newer = proforma.run(ProformaRunRequest(scenarioId=test_seed, assumptions=_yeast_assumed(), samples=12), pool=pool)
    assert older.artifactId != newer.artifactId
    monkeypatch.setattr(proforma, "call", lambda op, args: pytest.fail("selling_price ran something"))
    r = tools.run("selling_price", {"scenarioId": test_seed}, _pcx(pool))
    assert r.error is None, r.error
    (ev,) = r.evidence
    assert ev.id == newer.artifactId == r.summary["evidenceId"] and ev.figure == "distribution"
    assert ev.unit == shelf.ETHANOL_PRICE_BASIS and ev.provenance == "demo" == r.summary["provenance"]
    assert r.summary["scenarioId"] == test_seed and r.summary["flowsheet"] == "ethanol_glucose_v0"
    assert r.summary["leavesOut"] == shelf.ETHANOL_LEAVES_OUT
    assert r.summary["assumedInputs"] == ["glucose_price", "plant_scale"]


def test_selling_price_with_no_run_of_a_seed_scenario_names_what_waits_and_how_a_run_is_made(proforma_store, test_seed):
    from openferment_core import audit

    r = tools.run("selling_price", {"scenarioId": test_seed}, _pcx(_yeast_pool(drop=("ethanol_productivity",))))
    assert r.error and "no BioSTEAM scenario" not in r.error and f"no run of {test_seed} is on file" in r.error
    assert "productivity" in r.error and "plant_scale" in r.error and "glucose_price" in r.error
    assert "feed_glucose_conc" not in r.error and "titre " not in r.error  # bound to records, they wait for nothing
    assert "Proforma" in r.error and "named person's assumption" in r.error and "runs nothing" in r.error
    assert r.evidence == [] and artifacts.all_artifacts() == [] and audit.read() == []
    # Every process input bound, and still no run on file: said so.
    every = tools.run("selling_price", {"scenarioId": test_seed}, _pcx(_yeast_pool()))
    assert "plant_scale" in every.error and "productivity" not in every.error


def test_selling_price_refuses_what_is_no_seed_biosteam_scenario_in_words(proforma_store, test_seed):
    c = _pcx(_yeast_pool())
    made_here = tools.run("selling_price", {"scenarioId": "sc-mg2k1-1"}, c).error
    assert "is not a scenario this service holds" in made_here and test_seed in made_here
    assert "name the scenario" in tools.run("selling_price", {"scenarioId": " "}, c).error
    # A reference biorefinery's run is read where it is kept, and the words say where.
    corn = tools.run("selling_price", {"scenarioId": "corn_drygrind"}, c).error
    assert "is a reference biorefinery, not a scenario" in corn and "stream_table" in corn


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

    from openferment_core import proforma

    import standins

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}, path=tmp_path)


def _pcx(pool_):
    c = tools.ToolContext(pool_factory=lambda: pool_)
    c.ask_id, c.model = "ask-61", "claude-haiku-5-5"
    return c


def test_run_flowsheet_with_an_input_waiting_returns_the_422s_words_and_keeps_nothing(proforma_store, test_seed):
    from openferment_core import audit

    r = tools.run("run_flowsheet", {"scenarioId": test_seed}, _pcx(_yeast_pool()))
    assert r.error and r.error.startswith("run_flowsheet refused: these inputs wait for a source")
    assert "plant_scale" in r.error and "glucose_price" in r.error and "a model never supplies one" in r.error
    assert r.evidence == [] and audit.read() == [] and artifacts.all_artifacts() == []
    w = tools.run("proforma_write", {"action": "run", "target": test_seed, "fields": {}, "note": ""}, _pcx(_yeast_pool()))
    assert w.error == r.error.replace("run_flowsheet", "proforma_write", 1)


def test_run_flowsheet_refuses_a_scenario_it_does_not_hold_in_words(proforma_store, monkeypatch):
    from openferment_core import audit, pureos

    seed = TEST_SEED
    monkeypatch.setattr(pureos, "seed_scenarios", lambda: seed)
    c = _pcx(proforma_store)
    made_here = tools.run("run_flowsheet", {"scenarioId": "sc-mg2k1-1"}, c).error
    assert "is not a scenario this service holds" in made_here and "the browser that made it" in made_here
    assert "sc-test-ethanol" in made_here
    assert "name the scenario" in tools.run("run_flowsheet", {"scenarioId": " "}, c).error
    # With no projection to read, proforma.run's own words refuse it.
    monkeypatch.setattr(pureos, "seed_scenarios", lambda: [])
    # (§2.3's flowsheet_of writes them: a seed id runs its own flowsheet, and
    # an id the seed lacks names no flowsheet to run.)
    assert "there is no seed scenario sc-nonesuch" in tools.run("run_flowsheet", {"scenarioId": "sc-nonesuch"}, c).error
    # An empty target is refused too: proforma_write runs no scenario unnamed.
    assert "name the scenario" in tools.run("proforma_write", {"action": "run", "target": "", "fields": {}, "note": ""}, c).error
    assert audit.read() == []


@pytest.mark.parametrize("name, raw", [
    ("run_flowsheet", {"scenarioId": "sc-test-ethanol", "samples": 500}),
    ("run_flowsheet", {"scenarioId": "sc-test-ethanol", "glucose_price": 0.4}),
    ("stream_table", {"artifactId": 7}),
])
def test_a_number_in_a_proforma_tools_input_is_refused(proforma_store, name, raw):
    r = tools.run(name, raw, _pcx(proforma_store))
    assert r.error and "a number was typed" in r.error and artifacts.all_artifacts() == []


def test_run_flowsheet_takes_no_assumption_even_in_words(proforma_store):
    r = tools.run("run_flowsheet", {"scenarioId": "sc-test-ethanol", "assumptions": "glucose at forty cents"}, _pcx(proforma_store))
    assert r.error and "refused its input" in r.error
    assert "never type an assumption" in tools.REGISTRY["run_flowsheet"].description
    assert "never type a number" in tools.REGISTRY["stream_table"].description
    assert not tools.REGISTRY["run_flowsheet"].strict and not tools.REGISTRY["stream_table"].strict


def test_stream_table_cuts_a_long_table_to_the_cap_and_says_how_many_it_left_out(proforma_store, monkeypatch):
    from openferment_core import proforma
    from openferment_core.models import StreamRow

    aid = proforma.run_reference("corn_drygrind").id
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


# ── fermos_simulate (OF-BLD-020 §3.4, D13) ─────────────────────────────


@pytest.fixture()
def fermos_store(tmp_path, monkeypatch):
    """A throwaway store with the audit log and the proposals in it, and
    test_fermos_bind's STAND-IN batch_v1 pool (records written in the test
    on thread Q paper ids, none a paper's value)."""
    from test_fermos_bind import STANDIN, pool_of, rec

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    return pool_of(*STANDIN, rec("pm1", "ethanol_max_conc", 90.0), rec("al1", "ethanol_lp_alpha", 2.0, "g g-1"),
                   rec("mu-rej", "growth_rate_mu", 0.9, "h-1", status="rejected"),
                   rec("mu-cites", "growth_rate_mu", 0.9, "h-1", primary=False),
                   rec("mu-odd", "growth_rate_mu", 0.3, "g/L"))


def _kept_start(pool_):
    """A kept simulation a named person's STAND-IN values made, whose start
    values a model's simulation takes (`startFrom: simulation:<id>`): the
    service holds no person's assumption, and x0 and p0 bind from no record."""
    from openferment_core import fermos
    from openferment_core.models import SimulationRequest
    from test_fermos_bind import typed

    return fermos.simulate(SimulationRequest(family="batch_v1", product="ethanol", sugar="glucose",
                                             overrides=typed(x0=0.2, p0=0.0)), by_pool=pool_).artifactId


def _sim(start, **over):
    return {"family": "batch_v1", "strain": "", "product": "ethanol", "sugar": "glucose",
            "recordsByParam": {"mu_max": ["mu1", "mu3"]}, "fitArtifact": "", "startFrom": f"simulation:{start}",
            "durationPreset": "until-sugar-runs-out", **over}


def test_fermos_simulate_runs_a_family_from_record_ids_keeps_one_simulation_and_marks_it_as_the_models(fermos_store):
    from openferment_core import audit, fermos, proposals

    start = _kept_start(fermos_store)
    r = tools.run("fermos_simulate", _sim(start), _pcx(fermos_store))
    assert r.error is None, r.error
    s = r.summary
    (ev,) = r.evidence
    assert s["state"] == "open" and s["family"] == "batch_v1" and ev.id == s["artifactId"] == s["evidenceId"]
    art = artifacts.get(ev.id)
    assert art.tool == fermos.SIMULATION and ev.basis.tool == fermos.SIMULATION and ev.basis.artifactId == ev.id
    assert ev.provenance == s["provenance"] == art.provenance == "demo", "its start rests on a person's values"
    assert ev.value == pytest.approx(art.output["finalTitre"]) and ev.unit == art.output["units"]["P"]
    assert len(json.dumps(s, ensure_ascii=False)) <= tools.MAX_SUMMARY_CHARS
    # What bound each parameter, in words and counts; its value is in the artifact.
    lines = {x["key"]: x for x in s["parameters"] + s["start"]}
    assert lines["mu_max"] == {"key": "mu_max", "origin": "record", "records": 2,
                               "boundBy": "2 records of growth_rate_mu, named for it"}
    assert lines["yps"]["boundBy"] == "2 records of ethanol_yield_substrate, found by the rule for the strain and sugar"
    assert lines["x0"]["boundBy"] == f"a kept simulation, {start}" and lines["kd"]["boundBy"] == "a stated convention"
    assert lines["ki_substrate"]["boundBy"] == "a stated convention: off"
    assert {x["key"] for x in s["parameters"] + s["start"]} == {v.key for v in fermos.result_of(art).parameters} | {
        v.key for v in fermos.result_of(art).start}
    # The records named bind exactly that parameter, and the basis says they were named.
    named = {i.name: i for i in art.inputs}
    assert [i.value for i in art.inputs if i.name == "mu_max record"] == ["mu1", "mu3"]
    assert named["mu_max origin"].value == fermos.NAMED and named["records of"].value.startswith("every strain")
    [line] = audit.read()
    assert (line.agent, line.who, line.module, line.action, line.state, line.target, line.askId, line.effort) == (
        "model", "claude-haiku-5-5", "fermos", "simulate", "open", "batch_v1", "ask-61", "medium")
    assert line.detail["tool"] == "fermos_simulate" and line.detail["artifactId"] == ev.id
    # At no gate: nothing was proposed.
    assert proposals.read().proposals == []
    # fermos_write's simulate is the same run, marked with its own name.
    w = tools.run("fermos_write", {"action": "simulate", "target": "batch_v1", "note": "again",
                                   "fields": {"product": "ethanol", "sugar": "glucose", "records.mu_max": "mu1, mu3",
                                              "startFrom": f"simulation:{start}"}}, _pcx(fermos_store))
    assert w.error is None and w.evidence[0].id == ev.id
    assert audit.read()[-1].detail["tool"] == "fermos_write" and audit.read()[-1].detail["note"] == "again"


def test_fermos_simulate_with_a_parameter_waiting_returns_the_refusals_words_and_keeps_nothing(fermos_store):
    from openferment_core import audit

    r = tools.run("fermos_simulate", {"family": "batch_v1", "product": "ethanol", "sugar": "glucose"},
                  _pcx(fermos_store))
    assert r.error and r.error.startswith("fermos_simulate refused: batch_v1 cannot run yet")
    assert "x0 (cells at the start)" in r.error and "p0 (product at the start)" in r.error
    assert "a model never supplies one" in r.error and "recordsByParam" in r.error
    assert r.evidence == [] and audit.read() == [] and artifacts.all_artifacts() == []
    w = tools.run("fermos_write", {"action": "simulate", "target": "batch_v1", "note": "",
                                   "fields": {"product": "ethanol", "sugar": "glucose"}}, _pcx(fermos_store))
    assert w.error == r.error.replace("fermos_simulate", "fermos_write", 1)


@pytest.mark.parametrize("named, words", [
    ({"mu_max": ["nowhere-1"]}, "record nowhere-1, named for mu_max, is not in the evidence pool"),
    ({"mu_max": ["ks1"]}, "record ks1 is a record of monod_ks, and mu_max (maximum specific growth rate) binds from "
                          "growth_rate_mu"),
    ({"mu_max": ["mu-rej"]}, "record mu-rej, named for mu_max, is kept out by the aggregate gate: rejected"),
    ({"mu_max": ["mu-cites"]}, "record mu-cites, named for mu_max, is kept out by the aggregate gate: not-primary"),
    ({"mu_max": ["mu-odd"]}, "record mu-odd, named for mu_max, is in 'g/L', which units.py does not convert into h⁻¹"),
    ({"mu_max": []}, "recordsByParam names no record for mu_max"),
    ({"mu_max": ["mu1", "mu1"]}, "record mu1 is named twice for mu_max"),
    ({"mu_max": ["../corpus"]}, "a record is named by its id"),
    ({"x0": ["s01"]}, "x0 (cells at the start) binds from no record field here"),
    ({"growth": ["mu1"]}, "recordsByParam names growth, which is no parameter of batch_v1"),
])
def test_fermos_simulate_refuses_a_named_record_that_cannot_bind_in_words(fermos_store, named, words):
    from openferment_core import audit

    start = _kept_start(fermos_store)
    before = {a.id for a in artifacts.all_artifacts()}
    r = tools.run("fermos_simulate", _sim(start, recordsByParam=named), _pcx(fermos_store))
    assert r.error and r.error.startswith("fermos_simulate refused: ") and words in r.error, r.error
    assert r.evidence == [] and audit.read() == [] and {a.id for a in artifacts.all_artifacts()} == before


def test_a_number_in_fermos_simulates_input_is_refused_and_its_schema_holds_none(fermos_store):
    start = _kept_start(fermos_store)
    for raw in (_sim(start, recordsByParam={"mu_max": [0.4]}), _sim(start, mu_max=0.4), _sim(start, family=1)):
        r = tools.run("fermos_simulate", raw, _pcx(fermos_store))
        assert r.error and "a number was typed" in r.error and r.evidence == []
    assert "refused its input" in tools.run("fermos_simulate", _sim(start, overrides=[]), _pcx(fermos_store)).error
    schema = json.dumps(tools.REGISTRY["fermos_simulate"].info().inputSchema)
    assert '"number"' not in schema and '"integer"' not in schema
    assert tools.REGISTRY["fermos_simulate"].strict is False


def test_fermos_write_simulate_refuses_a_field_it_does_not_take(fermos_store):
    r = tools.run("fermos_write", {"action": "simulate", "target": "batch_v1", "note": "",
                                   "fields": {"product": "ethanol", "mu_max": "fast"}}, _pcx(fermos_store))
    assert r.error and "mu_max is not a field of it" in r.error and "records.<parameter key>" in r.error
    preset = tools.run("fermos_write", {"action": "simulate", "target": "batch_v1", "note": "",
                                        "fields": {"durationPreset": "forever"}}, _pcx(fermos_store))
    assert preset.error and "until-sugar-runs-out or fit-length" in preset.error
    assert "simulate:" in tools.REGISTRY["fermos_write"].description
