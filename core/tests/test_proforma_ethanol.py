"""Glucose to ethanol, and the scenario run contract (OF-BLD-019 §2.3), with
no simulator.

Every record and assumption here is a FIXTURE written in the test, the
records on placeholder paper ids; none is a measurement and no price here is
a result. The runs go through the real binding and artifact code over the
closed-form STAND-IN evaluator (standins.py). The flowsheet itself runs in
`test_proforma.py` (marked `sim`) and `test_proforma_slow.py`.

The seed's scenarios went with the seed (alpha 2.0, ADR-010), so the service
holds none by its id; the rules a held scenario's run keeps are tested on one
a fixture holds (`held`).
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, basis, intake, proforma, units
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.flowsheets import shelf
from openferment_core.models import BasisInput, BasisSource, ComputedBasis, InputAssumption, ProformaRunRequest

CORE = Path(__file__).resolve().parent.parent
MODULE = CORE / "openferment_core" / "flowsheets" / "ethanol_glucose_v0.py"
ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
HELD = "sc-held-1"  # a scenario the service holds by its id, as the `held` fixture holds it


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def standin(monkeypatch, store):
    """The STAND-IN evaluator in place of the worker, over the stand-in
    records of both flowsheets, as the double's fixtures are made."""
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def held(monkeypatch):
    """One scenario the service holds by its id, on the ethanol flowsheet."""
    row = {"id": HELD, "name": "A held test scenario", "kind": "biosteam", "modelId": ETHANOL}
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [row])
    return row


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def rec(rid, field, value, unit, *, paper="T1", carbon="glucose", strain=None, **kw):
    return {"id": rid, "paperId": paper, "field": field, "value": value, "unit": unit, "carbonSource": carbon,
            "strainId": strain, "organismText": "Saccharomyces cerevisiae", "provenance": "unverified",
            "status": "unverified", "primary": True, **kw}


def assume(key, value, low=None, high=None, by=BY):
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=by, at="2026-10-20", note="a STAND-IN for a test")


def by_key(inputs):
    return {i.key: i for i in inputs}


def _assigned(name: str):
    """A module-level literal of the flowsheet file, read without importing
    BioSTEAM."""
    for node in ast.parse(MODULE.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{MODULE.name} assigns no {name}")


ASSUMED = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]


# ── the flowsheet and its shelf entry (D4) ─────────────────────────────


def test_the_flowsheet_file_holds_no_number():
    # Rule 1 and D4: every process value arrives bound; the file's only
    # numbers are nothing and one (a denaturant at zero, a starting sales of
    # zero, a conversion that every case overwrites).
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    numbers = {n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    assert numbers <= {0, 1}, f"{MODULE.name} holds the numbers {sorted(numbers)}"
    assert all(default is None for _label, _unit, default in _assigned("INPUTS").values())


def test_the_shelf_entry_is_the_flowsheets_inputs():
    e = shelf.SHELF[ETHANOL]
    assert not e.reference and e.program == "yeast" and e.source == "this repository"
    module = _assigned("INPUTS")
    valued = [i for i in e.inputs if i.kind != "convention"]
    assert [i.key for i in valued] == list(module)
    for i in valued:
        assert (i.name, i.unit) == module[i.key][:2]
    by = {i.key: i for i in e.inputs}
    assert by["feed_glucose_conc"].fields == ["medium_component_conc"] and by["titre"].fields == ["ethanol_titre"]
    assert by["yield"].fields == ["ethanol_yield_substrate"] and by["productivity"].fields == ["ethanol_productivity"]
    assert [by[k].kind for k in ("plant_scale", "glucose_price")] == ["economic", "economic"]
    assert by["plant_scale"].fields == by["glucose_price"].fields == []
    assert by["ethanol_purity"].kind == "convention" and by["ethanol_purity"].fields == []
    ontology = units.tables()["ontology"]
    assert all(f in ontology for i in e.inputs for f in i.fields), "a field the records do not carry"
    assert e.leavesOut == _assigned("LEAVES_OUT") == shelf.ETHANOL_LEAVES_OUT
    assert e.priceOutput == "pricePerKgEthanol" and e.priceBasis == shelf.ETHANOL_PRICE_BASIS
    assert e.gridInputs == ["titre", "yield", "glucose_price"] and set(e.gridInputs) <= set(module)


# ── the binding ────────────────────────────────────────────────────────


def test_records_that_name_glucose_bind_and_the_rest_are_counted():
    rs = [
        rec("f1", "medium_component_conc", 20.0, "g/L"), rec("f2", "medium_component_conc", 100.0, "g/L"),
        rec("f3", "medium_component_conc", 60.0, "g/L"),
        rec("nocarbon", "medium_component_conc", 30.0, "g/L", carbon=None),
        rec("sucrose", "medium_component_conc", 30.0, "g/L", carbon="sucrose"),
        rec("estimate", "medium_component_conc", 30.0, "g/L", provenance="industry-estimate"),
        rec("computed", "medium_component_conc", 30.0, "g/L", provenance="computed"),
        rec("rejected", "medium_component_conc", 30.0, "g/L", status="rejected"),
        rec("cites", "medium_component_conc", 30.0, "g/L", primary=False),
        rec("t", "ethanol_titre", 90.0, "g/L"),
        rec("p", "ethanol_productivity", 2000.0, "mg L⁻¹ h⁻¹"),
    ]
    b = by_key(proforma.bind_inputs(ETHANOL, rs))
    assert list(b) == ["feed_glucose_conc", "titre", "yield", "productivity", "plant_scale", "glucose_price"]
    feed = b["feed_glucose_conc"]
    assert feed.recordIds == ["f1", "f2", "f3"] and (feed.value, feed.low, feed.high, feed.sampling) == (60.0, 20.0, 100.0, "triangular")
    assert feed.leftOutNoCarbon == 1 and feed.leftOutOtherCarbon == 1
    assert feed.source.kind == "record" and "medium_component_conc" in feed.source.note
    assert b["titre"].sampling == "fixed" and proforma.SINGLE in b["titre"].flags
    assert b["productivity"].value == pytest.approx(2.0)  # mg to g, by units.py
    assert b["yield"].binding == b["plant_scale"].binding == b["glucose_price"].binding == "waiting"


def test_a_refused_conversion_stops_the_binding_and_an_assumption_fills_it():
    bad = [rec("v", "ethanol_titre", 12.0, "% CDW")]
    t = by_key(proforma.bind_inputs(ETHANOL, bad))["titre"]
    assert t.binding == "waiting" and "binding stopped" in t.flags[0]
    t = by_key(proforma.bind_inputs(ETHANOL, bad, assumptions=[assume("titre", 80.0, 60.0, 100.0)]))["titre"]
    assert t.binding == "assumption" and t.source.by == BY and any("binding stopped" in f for f in t.flags)


def test_an_assumption_needs_a_named_person_and_a_host_narrows_the_binding():
    with pytest.raises(proforma.ScenarioRefused, match="placeholder"):
        proforma.bind_inputs(ETHANOL, [], assumptions=[assume("glucose_price", 0.4, by="me")])
    rs = [rec("cen", "ethanol_titre", 90.0, "g/L", strain="s-cerevisiae-cenpk113-7d"), rec("other", "ethanol_titre", 50.0, "g/L")]
    assert by_key(proforma.bind_inputs(ETHANOL, rs, host="s-cerevisiae-cenpk113-7d"))["titre"].recordIds == ["cen"]
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    assert proforma.bound(ETHANOL, pool=pool).hosts == ["s-cerevisiae-cenpk113-7d"]


# ── (b) the scenarios the project keeps ──────────────────────────────────


def test_the_scenarios_endpoint_serves_the_scenarios_the_project_keeps(client, monkeypatch):
    assert client.get("/api/proforma/scenarios").json() == [], "the test project keeps no scenario"
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [{"id": HELD, "name": "A held test scenario", "kind": "biosteam",
                                                             "modelId": ETHANOL}])
    [held] = client.get("/api/proforma/scenarios").json()
    assert held["id"] == HELD and held["flowsheet"] == ETHANOL and held["name"] and held["product"] == "ethanol"
    assert held["waiting"] == ["plant_scale", "glucose_price"] and held["priceBasis"] == shelf.ETHANOL_PRICE_BASIS
    nobody = client.get("/api/proforma/scenarios?host=nobody").json()[0]
    assert nobody["waiting"] == ["feed_glucose_conc", "titre", "yield", "productivity", "plant_scale", "glucose_price"]


# ── (c) a flowsheet bound, as a scenario made here shows it ────────────


def test_the_bind_endpoint_binds_a_flowsheet_and_refuses_in_words(client, held):
    r = client.get(f"/api/proforma/bind?flowsheet={ETHANOL}")
    assert r.status_code == 200
    b = r.json()
    assert b["id"] == "" and b["name"] == "" and b["flowsheet"] == ETHANOL and b["waiting"] == ["plant_scale", "glucose_price"]
    assert set(b) == set(client.get("/api/proforma/scenarios").json()[0])  # the same shape as (b)
    for fid, words in (("cornstover_benchmark", "reference biorefinery"), ("toy", "STAND-IN for tests"),
                       ("nowhere", "there is no flowsheet nowhere")):
        r = client.get(f"/api/proforma/bind?flowsheet={fid}")
        assert r.status_code == 422 and words in r.json()["detail"]
    narrowed = client.get(f"/api/proforma/bind?flowsheet={ETHANOL}&host=nobody").json()
    assert "titre" in narrowed["waiting"]


# ── (d) a run: a seed scenario by its id, a made one by its flowsheet ──


def test_a_scenario_made_here_runs_its_flowsheet_bound_as_bind_binds_it(standin, held):
    r = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED, samples=20),
                     pool=standin)
    assert r.scenarioId == MADE_HERE and r.flowsheet == ETHANOL and r.provenance == "assumed" and r.samples == 20
    assert [i.binding for i in r.inputs] == [i.binding for i in proforma.bind_inputs(ETHANOL, standin.records, None, ASSUMED)]
    assert r.priceBasis == shelf.ETHANOL_PRICE_BASIS and r.leavesOut == shelf.ETHANOL_LEAVES_OUT
    assert r.tea is not None and sum(line.perUnit for line in r.tea.lines) == pytest.approx(r.basePrice, rel=1e-12)
    assert len(r.grid.msp) == 125 and r.evidence.unit == shelf.ETHANOL_PRICE_BASIS and MADE_HERE in r.evidence.label
    kept = proforma.run(ProformaRunRequest(scenarioId=HELD, assumptions=ASSUMED, samples=20), pool=standin)
    assert kept.artifactId != r.artifactId and kept.quantiles == r.quantiles  # the same case, two scenarios' runs


def test_every_other_run_is_refused_in_words(standin, client, held):
    cases = [
        ({"scenarioId": MADE_HERE}, f"there is no held scenario {MADE_HERE}"),
        ({"scenarioId": MADE_HERE, "flowsheet": "cornstover_benchmark"}, "reference biorefinery"),
        ({"scenarioId": MADE_HERE, "flowsheet": "toy"}, "STAND-IN for tests"),
        ({"scenarioId": MADE_HERE, "flowsheet": "nowhere"}, "there is no flowsheet nowhere"),
        ({"scenarioId": HELD, "flowsheet": shelf.COMPOSITE}, f"{HELD} runs ethanol_glucose_v0, not {shelf.COMPOSITE}"),
        ({"scenarioId": " ", "flowsheet": ETHANOL}, "names the scenario it belongs to"),
        ({"scenarioId": HELD}, "wait for a source, a record or a named person's assumption: plant_scale, glucose_price"),
        ({"scenarioId": MADE_HERE, "flowsheet": ETHANOL}, "plant_scale, glucose_price"),
    ]
    for body, words in cases:
        with pytest.raises(proforma.ScenarioRefused, match=words.replace("(", r"\(")):
            proforma.run(ProformaRunRequest(**body), pool=standin)
        r = client.post("/api/proforma/run", json=body)
        assert r.status_code == 422 and words in r.json()["detail"], (body, r.json())
    # A held scenario may name its own flowsheet.
    ok = client.post("/api/proforma/run", json={"scenarioId": HELD, "flowsheet": ETHANOL, "samples": 8,
                                                "assumptions": [a.model_dump() for a in ASSUMED]})
    assert ok.status_code == 200 and ok.json()["scenarioId"] == HELD


# ── (e) the basis names the scenario, and leaves the provenance be ─────


def test_every_run_names_its_scenario_in_the_basis_as_a_convention(standin, held):
    for sid, req in ((HELD, {"assumptions": ASSUMED}),
                     (MADE_HERE, {"flowsheet": ETHANOL, "assumptions": ASSUMED})):
        art = artifacts.get(proforma.run(ProformaRunRequest(scenarioId=sid, samples=8, **req), pool=standin).artifactId)
        named = [i for i in art.inputs if i.name == "scenario"]
        assert len(named) == 1 and named[0].value == sid and named[0].source.kind == "convention"


def test_the_scenario_input_leaves_the_provenance_as_it_was():
    record = BasisInput(name="titre record", value=1.0, unit="g L-1", source=BasisSource(kind="record", id="r1"))
    scenario = proforma.basis_inputs([], ETHANOL, 8, scenario_id=MADE_HERE)
    [named] = [i for i in scenario if i.name == "scenario"]
    for prov in ("verified", "unverified", "gold"):
        def of(inputs):
            b = ComputedBasis(tool=proforma.RUN, toolVersion="test", inputs=inputs, artifactId="0" * 16, at="2026-10-20")
            return basis.basis_provenance(b, {"r1": {"provenance": prov}}, {})
        assert of([record, named]) == of([record])
    assert "scenario" not in [i.name for i in proforma.basis_inputs([], ETHANOL, 8)]


def test_the_basis_names_the_packages_and_the_conventions():
    named = {i.name: i for i in proforma.basis_inputs([], ETHANOL, 8)}
    assert named["chemicals and finance"].source.kind == "model" and named["chemicals and finance"].source.id.startswith("biorefineries.corn@")
    assert named["purification train"].source.id.startswith("biorefineries.ethanol@")
    assert named["fermenter"].source.id.startswith("biosteam@")
    for conv in ("theoretical yield", "batch time", "ethanol purity"):
        assert named[conv].source.kind == "convention" and isinstance(named[conv].value, str)
    assert named["ethanol purity"].value == "fuel grade"


def test_the_latest_run_and_its_evidence_follow_the_scenario(standin, held):
    kept = proforma.run(ProformaRunRequest(scenarioId=HELD, assumptions=ASSUMED, samples=8), pool=standin)
    assert proforma.latest_run("sc-nowhere") is None and proforma.latest_run(MADE_HERE) is None
    assert proforma.latest_run(HELD).id == kept.artifactId
    ev = proforma.evidence_of(artifacts.get(kept.artifactId))
    assert HELD in ev.label and ev.unit == shelf.ETHANOL_PRICE_BASIS


# ── the Phase 2 review (OF-BLD-019 §2.R), offline ──────────────────────
# Each test below was written before its fix and seen to fail for the
# reason the review gave; the worker's own (sim and slow) are in
# test_proforma.py and test_proforma_slow.py.


def test_every_run_names_the_utility_prices_and_cost_index_it_priced_on():
    # §2.R, review 1: the run's utilities and every equipment cost rest on
    # BioSTEAM's utility prices and plant cost index; the basis names them,
    # BioSTEAM's own defaults set for every case, and the run reads them back.
    for flowsheet in (ETHANOL, shelf.COMPOSITE):
        named = {i.name: i for i in proforma.basis_inputs([], flowsheet, 8)}
        u = named["utility prices and cost index"]
        assert u.source.kind == "model" and u.source.id.startswith("biosteam@"), flowsheet
        assert "default_utilities" in str(u.value) and "default_CEPCI" in str(u.value)
        assert "read back" in (u.source.note or "")


def test_a_run_with_no_sample_the_flowsheet_holds_says_why_and_names_its_run(standin, client):
    # §2.R, review 3: every case asks a yield above the theoretical, so no
    # sample runs; the 422 says why and names the run it kept, which was
    # stored before the refusal and was found nowhere on the screen.
    above = standins.STANDIN_THEORETICAL * 1.2
    every = [assume("feed_glucose_conc", 100.0), assume("titre", 45.0), assume("yield", above),
             assume("productivity", 2.0), *ASSUMED]
    host = "nobody"  # no record binds: every input is a named person's assumption
    with pytest.raises(proforma.ScenarioRefused) as e:
        proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, host=host, assumptions=every, samples=4),
                     pool=standin)
    said = str(e.value)
    [kept] = [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]
    assert "no sample the flowsheet could hold" in said and kept.id in said
    assert "yield: 4 of 4" in said and "the base case" in said and "yield" in kept.output["baseInfeasible"]
    r = client.post("/api/proforma/run", json={"scenarioId": MADE_HERE, "flowsheet": ETHANOL, "host": host, "samples": 4,
                                               "assumptions": [a.model_dump() for a in every]})
    assert r.status_code == 422 and kept.id in r.json()["detail"] and "yield: 4 of 4" in r.json()["detail"]


def test_a_number_that_is_not_finite_and_a_negative_seed_are_refused_in_words(standin, client):
    # §2.R, review 5: both were a 500 (the infinite assumption reached the
    # artifact's canonical JSON; the negative seed reached the sampler).
    for field in ("value", "low", "high"):
        a = {"key": "plant_scale", "value": 100000.0, "low": 100000.0, "high": 100000.0, "by": BY, "at": "2026-10-20"}
        a[field] = "INF"
        body = (f'{{"scenarioId": "{MADE_HERE}", "flowsheet": "{ETHANOL}", "samples": 4, "assumptions": ['
                + ", ".join(__import__("json").dumps(x) for x in (a, ASSUMED[1].model_dump()))
                + "]}").replace('"INF"', "Infinity")
        r = client.post("/api/proforma/run", content=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 422 and "plant_scale" in r.json()["detail"] and "finite" in r.json()["detail"], (field, r.text)
    called = []
    real = proforma.call
    proforma.call = lambda op, args: called.append(op) or real(op, args)
    try:
        r = client.post("/api/proforma/run", json={"scenarioId": MADE_HERE, "flowsheet": ETHANOL, "seed": -1, "samples": 4,
                                                   "assumptions": [a.model_dump() for a in ASSUMED]})
    finally:
        proforma.call = real
    assert r.status_code == 422 and "seed" in r.json()["detail"] and called == []
    assert not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]


def test_a_host_with_graphviz_draws_its_own_run_of_a_basis_run_without_it(monkeypatch, standin):
    # §2.R, review 7 and 11: whether the run's diagram is drawn is part of its
    # basis, so a run made where Graphviz's dot was absent is not the run a
    # host with dot makes of the same inputs: that host draws its own.
    monkeypatch.setattr(proforma, "drawn_here", lambda: False)
    without = proforma.run_reference("corn_drygrind")
    named = {i.name: i for i in without.inputs}
    assert named["diagram"].source.kind == "convention" and "not drawn" in str(named["diagram"].value)
    monkeypatch.setattr(proforma, "drawn_here", lambda: True)
    drawn = proforma.run_reference("corn_drygrind")
    assert drawn.id != without.id and {i.name: i for i in drawn.inputs}["diagram"].value == "drawn by Graphviz"
    assert without.provenance == drawn.provenance == "computed"
    run_without = {i.name: i for i in proforma.basis_inputs([], ETHANOL, 8)}["diagram"]
    assert run_without.value == "drawn by Graphviz"  # drawn_here is patched to True above
