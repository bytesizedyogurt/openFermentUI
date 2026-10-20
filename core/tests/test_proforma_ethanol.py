"""Glucose to ethanol, and the scenario run contract (OF-BLD-019 §2.3), with
no simulator.

Every record and assumption here is a FIXTURE written in the test, the
records on thread Q paper ids; none is a measurement and no price here is a
result. The runs go through the real binding and artifact code over demo.py's
closed-form STAND-IN evaluator. The flowsheet itself runs in
`test_proforma.py` (marked `sim`) and `test_proforma_slow.py`.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, basis, demo, intake, proforma, units
from openferment_core.flowsheets import shelf
from openferment_core.models import BasisInput, BasisSource, ComputedBasis, InputAssumption, ProformaRunRequest

CORE = Path(__file__).resolve().parent.parent
MODULE = CORE / "openferment_core" / "flowsheets" / "ethanol_glucose_v0.py"
ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def standin(monkeypatch, store):
    """The STAND-IN evaluator in place of the worker, over the stand-in
    records of both flowsheets, as the double's fixtures are made."""
    monkeypatch.setattr(proforma, "call", demo._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records() + demo._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def rec(rid, field, value, unit, *, paper="Q7", carbon="glucose", strain=None, **kw):
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


def test_the_seed_ships_one_yeast_scenario_on_the_flowsheet():
    seeds = {s["id"]: s for s in proforma.seed_scenarios()}
    assert seeds["sc-yeast-1"]["modelId"] == ETHANOL and seeds["sc-yeast-1"]["program"] == "yeast"
    assert not seeds["sc-yeast-1"].get("example")
    for s in seeds.values():
        assert s["modelId"] in shelf.SHELF and not shelf.SHELF[s["modelId"]].reference


# ── the binding ────────────────────────────────────────────────────────


def test_thread_q_records_that_name_glucose_bind_and_the_rest_are_counted():
    rs = [
        rec("f1", "medium_component_conc", 20.0, "g/L"), rec("f2", "medium_component_conc", 100.0, "g/L"),
        rec("f3", "medium_component_conc", 60.0, "g/L"),
        rec("nocarbon", "medium_component_conc", 30.0, "g/L", carbon=None),
        rec("sucrose", "medium_component_conc", 30.0, "g/L", carbon="sucrose"),
        rec("pha", "medium_component_conc", 30.0, "g/L", paper="P6"),
        rec("casein", "medium_component_conc", 30.0, "g/L", paper="B5"),
        rec("estimate", "medium_component_conc", 30.0, "g/L", provenance="industry-estimate"),
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


# ── (b) the seed's scenarios, by the switch ────────────────────────────


def test_the_scenarios_endpoint_serves_the_seed_by_the_switch(client):
    off = client.get("/api/proforma/scenarios").json()
    assert [s["id"] for s in off] == ["sc-yeast-1"] == [s["id"] for s in client.get("/api/proforma/scenarios?includeArchived=false").json()]
    yeast = off[0]
    assert yeast["flowsheet"] == ETHANOL and yeast["name"] and yeast["product"] == "ethanol"
    assert yeast["waiting"] == ["plant_scale", "glucose_price"] and yeast["priceBasis"] == shelf.ETHANOL_PRICE_BASIS
    on = client.get("/api/proforma/scenarios?includeArchived=true").json()
    assert {s["id"]: s["flowsheet"] for s in on} == {"sc-pha-1": "pha_sugar_v0", "sc-yeast-1": ETHANOL}
    nobody = client.get("/api/proforma/scenarios?includeArchived=false&host=nobody").json()[0]
    assert nobody["waiting"] == ["feed_glucose_conc", "titre", "yield", "productivity", "plant_scale", "glucose_price"]


# ── (c) a flowsheet bound, as a scenario made here shows it ────────────


def test_the_bind_endpoint_binds_a_flowsheet_and_refuses_in_words(client):
    r = client.get(f"/api/proforma/bind?flowsheet={ETHANOL}&includeArchived=false")
    assert r.status_code == 200
    b = r.json()
    assert b["id"] == "" and b["name"] == "" and b["flowsheet"] == ETHANOL and b["waiting"] == ["plant_scale", "glucose_price"]
    assert set(b) == set(client.get("/api/proforma/scenarios").json()[0])  # the same shape as (b)
    for fid, words in (("cornstover_benchmark", "reference biorefinery"), ("toy", "STAND-IN for tests"),
                       ("nowhere", "there is no flowsheet nowhere")):
        r = client.get(f"/api/proforma/bind?flowsheet={fid}")
        assert r.status_code == 422 and words in r.json()["detail"]
    off = client.get("/api/proforma/bind?flowsheet=pha_sugar_v0")
    assert off.status_code == 422 and "archived program PHA" in off.json()["detail"] and "Settings → Programs" in off.json()["detail"]
    on = client.get("/api/proforma/bind?flowsheet=pha_sugar_v0&includeArchived=true").json()
    assert on["id"] == "" and on["flowsheet"] == "pha_sugar_v0" and set(on["waiting"]) == {"recovery", "sugarPrice", "sugarFeed"}
    narrowed = client.get(f"/api/proforma/bind?flowsheet={ETHANOL}&host=nobody").json()
    assert "titre" in narrowed["waiting"]


# ── (d) a run: a seed scenario by its id, a made one by its flowsheet ──


def test_a_scenario_made_here_runs_its_flowsheet_bound_as_bind_binds_it(standin):
    r = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED, samples=20),
                     pool=standin)
    assert r.scenarioId == MADE_HERE and r.flowsheet == ETHANOL and r.provenance == "demo" and r.samples == 20
    assert [i.binding for i in r.inputs] == [i.binding for i in proforma.bind_inputs(ETHANOL, standin.records, None, ASSUMED)]
    assert r.priceBasis == shelf.ETHANOL_PRICE_BASIS and r.leavesOut == shelf.ETHANOL_LEAVES_OUT
    assert r.tea is not None and sum(line.perUnit for line in r.tea.lines) == pytest.approx(r.basePrice, rel=1e-12)
    assert len(r.grid.msp) == 125 and r.evidence.unit == shelf.ETHANOL_PRICE_BASIS and MADE_HERE in r.evidence.label
    seeded = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=ASSUMED, samples=20), pool=standin)
    assert seeded.artifactId != r.artifactId and seeded.quantiles == r.quantiles  # the same case, two scenarios' runs


def test_every_other_run_is_refused_in_words(standin, client):
    cases = [
        ({"scenarioId": MADE_HERE}, f"there is no seed scenario {MADE_HERE}"),
        ({"scenarioId": MADE_HERE, "flowsheet": "cornstover_benchmark"}, "reference biorefinery"),
        ({"scenarioId": MADE_HERE, "flowsheet": "toy"}, "STAND-IN for tests"),
        ({"scenarioId": MADE_HERE, "flowsheet": "nowhere"}, "there is no flowsheet nowhere"),
        ({"scenarioId": "sc-yeast-1", "flowsheet": "pha_sugar_v0"}, "sc-yeast-1 runs ethanol_glucose_v0, not pha_sugar_v0"),
        ({"scenarioId": " ", "flowsheet": ETHANOL}, "names the scenario it belongs to"),
        ({"scenarioId": "sc-yeast-1"}, "wait for a source, a record or a named person's assumption: plant_scale, glucose_price"),
        ({"scenarioId": MADE_HERE, "flowsheet": ETHANOL}, "plant_scale, glucose_price"),
    ]
    for body, words in cases:
        with pytest.raises(proforma.ScenarioRefused, match=words.replace("(", r"\(")):
            proforma.run(ProformaRunRequest(**body), pool=standin)
        r = client.post("/api/proforma/run", json=body)
        assert r.status_code == 422 and words in r.json()["detail"], (body, r.json())
    # A seed scenario may name its own flowsheet.
    ok = client.post("/api/proforma/run", json={"scenarioId": "sc-yeast-1", "flowsheet": ETHANOL, "samples": 8,
                                                "assumptions": [a.model_dump() for a in ASSUMED]})
    assert ok.status_code == 200 and ok.json()["scenarioId"] == "sc-yeast-1"


# ── (e) the basis names the scenario, and leaves the provenance be ─────


def test_every_run_names_its_scenario_in_the_basis_as_a_convention(standin):
    for sid, req in (("sc-yeast-1", {"assumptions": ASSUMED}),
                     (MADE_HERE, {"flowsheet": ETHANOL, "assumptions": ASSUMED})):
        art = artifacts.get(proforma.run(ProformaRunRequest(scenarioId=sid, samples=8, **req), pool=standin).artifactId)
        named = [i for i in art.inputs if i.name == "scenario"]
        assert len(named) == 1 and named[0].value == sid and named[0].source.kind == "convention"
    pha = [InputAssumption(key=k, value=v, low=v, high=v, by=BY, at="2026-10-20")
           for k, v in (("recovery", 0.95), ("sugarPrice", 0.4), ("sugarFeed", 10000.0))]
    art = artifacts.get(proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=pha, samples=8), pool=standin).artifactId)
    assert [i.value for i in art.inputs if i.name == "scenario"] == ["sc-pha-1"]


def test_the_scenario_input_leaves_the_provenance_as_it_was():
    record = BasisInput(name="titre record", value=1.0, unit="g L-1", source=BasisSource(kind="record", id="r1"))
    scenario = proforma.basis_inputs([], None, ETHANOL, 8, scenario_id="sc-yeast-1")
    [named] = [i for i in scenario if i.name == "scenario"]
    for prov in ("verified", "unverified", "gold"):
        def of(inputs):
            b = ComputedBasis(tool=proforma.RUN, toolVersion="test", inputs=inputs, artifactId="0" * 16, at="2026-10-20")
            return basis.basis_provenance(b, {"r1": {"provenance": prov}}, {})
        assert of([record, named]) == of([record])
    assert "scenario" not in [i.name for i in proforma.basis_inputs([], None, ETHANOL, 8)]


def test_the_basis_names_the_packages_and_the_conventions():
    named = {i.name: i for i in proforma.basis_inputs([], None, ETHANOL, 8)}
    assert named["chemicals and finance"].source.kind == "model" and named["chemicals and finance"].source.id.startswith("biorefineries.corn@")
    assert named["purification train"].source.id.startswith("biorefineries.ethanol@")
    assert named["fermenter"].source.id.startswith("biosteam@")
    for conv in ("theoretical yield", "batch time", "ethanol purity"):
        assert named[conv].source.kind == "convention" and isinstance(named[conv].value, str)
    assert named["ethanol purity"].value == "fuel grade"


def test_the_latest_run_and_its_evidence_follow_the_scenario(standin):
    yeast = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=ASSUMED, samples=8), pool=standin)
    assert proforma.latest_run("sc-pha-1") is None and proforma.latest_run(MADE_HERE) is None
    assert proforma.latest_run("sc-yeast-1").id == yeast.artifactId
    ev = proforma.evidence_of(artifacts.get(yeast.artifactId))
    assert "sc-yeast-1" in ev.label and ev.unit == shelf.ETHANOL_PRICE_BASIS
