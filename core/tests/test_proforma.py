"""Proforma on the service's side (OF-BLD-014 §8.2–§8.3), with no simulator."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, proforma


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_a_benchmark_not_yet_run_reads_as_none_and_starts_nothing(store):
    from openferment_core import api

    before = proforma.status()["status"]
    r = TestClient(api.app, base_url="http://127.0.0.1").get("/api/proforma/benchmark").json()
    assert r["artifact"] is None and r["simulator"]["status"] == before


def test_the_benchmark_cites_the_package_it_ran(store):
    inputs = proforma.benchmark_inputs()
    assert {i.source.kind for i in inputs} == {"model"}
    assert inputs[0].source.id.startswith("biorefineries.cornstover@")


# ── binding (§8.3) ─────────────────────────────────────────────────────
# Every record here is a FIXTURE written in the test; none is a measurement.

from types import SimpleNamespace  # noqa: E402

from openferment_core.models import InputAssumption, ProformaRunRequest  # noqa: E402


def rec(rid, field, value, unit, *, paper="P6", carbon="glucose", strain="c-necator-h16", **kw):
    return {"id": rid, "paperId": paper, "field": field, "value": value, "unit": unit, "carbonSource": carbon,
            "strainId": strain, "organismText": "Ralstonia eutropha", "provenance": "unverified", "status": "unverified",
            "primary": True, **kw}


def assume(key, value, low, high, by="Sean Creighton"):
    return InputAssumption(key=key, value=value, low=low, high=high, by=by, at="2026-10-15")


def by_key(inputs):
    return {i.key: i for i in inputs}


def test_three_records_give_their_median_and_range_and_sample_triangular():
    rs = [rec(f"t{i}", "pha_titre", v, "g/L") for i, v in enumerate([10.0, 40.0, 25.0])]
    t = by_key(proforma.bind(rs))["titre"]
    assert (t.value, t.low, t.high, t.sampling, t.binding) == (25.0, 10.0, 40.0, "triangular", "records")
    assert t.recordIds == ["t0", "t1", "t2"]


def test_two_records_are_a_pair_and_one_is_held_fixed_and_flagged():
    two = by_key(proforma.bind([rec("a", "pha_titre", 10.0, "g/L"), rec("b", "pha_titre", 20.0, "g/L")]))["titre"]
    assert (two.low, two.high, two.sampling) == (10.0, 20.0, "uniform")
    one = by_key(proforma.bind([rec("a", "pha_titre", 10.0, "g/L")]))["titre"]
    assert one.sampling == "fixed" and proforma.SINGLE in one.flags


def test_the_gate_and_the_carbon_source_decide_what_binds():
    rs = [
        rec("ok", "pha_titre", 10.0, "g/L", carbon="sunflower stalk hydrolysate"),
        rec("nocarbon", "pha_titre", 11.0, "g/L", carbon=None),
        rec("oil", "pha_titre", 12.0, "g/L", carbon="glycerol"),
        rec("estimate", "pha_titre", 13.0, "g/L", provenance="industry-estimate"),
        rec("computed", "pha_titre", 13.0, "g/L", provenance="computed"),
        rec("cites", "pha_titre", 14.0, "g/L", primary=False),
        rec("rejected", "pha_titre", 15.0, "g/L", status="rejected"),
        rec("caseins", "pha_titre", 16.0, "g/L", paper="B5"),
    ]
    t = by_key(proforma.bind(rs))["titre"]
    assert t.recordIds == ["ok"] and t.leftOutNoCarbon == 1 and t.leftOutOtherCarbon == 1


def test_content_in_percent_of_dry_mass_becomes_a_share():
    c = by_key(proforma.bind([rec("c", "pha_content_cdw", 60.0, "% CDW")]))["content"]
    assert c.value == pytest.approx(0.6)


def test_a_host_filter_narrows_the_binding():
    rs = [rec("h", "pha_titre", 10.0, "g/L"), rec("k", "pha_titre", 20.0, "g/L", strain="p-putida-kt2440")]
    assert by_key(proforma.bind(rs, host="p-putida-kt2440"))["titre"].recordIds == ["k"]


def test_a_yield_above_the_ceiling_is_clipped_and_said():
    rs = [rec("y1", "pha_yield_substrate", 0.3, "g g-1"), rec("y2", "pha_yield_substrate", 0.7, "g g-1")]
    y = by_key(proforma.bind(rs, cap=(0.48, "ceilingid")))["yield"]
    assert y.high == pytest.approx(0.48) and any("clipped" in f for f in y.flags)


def test_a_refused_conversion_stops_the_binding_with_the_engines_reason():
    y = by_key(proforma.bind([rec("bad", "pha_titre", 1.0, "% CDW")]))["titre"]
    assert y.binding == "waiting" and "binding stopped" in y.flags[0]


def test_an_assumption_needs_a_named_person_and_its_own_range():
    with pytest.raises(proforma.ScenarioRefused, match="placeholder"):
        proforma.bind([], assumptions=[assume("recovery", 0.9, 0.8, 0.95, by="me")])
    with pytest.raises(proforma.ScenarioRefused, match="within its own low and high"):
        proforma.bind([], assumptions=[assume("recovery", 0.99, 0.8, 0.95)])
    r = by_key(proforma.bind([], assumptions=[assume("recovery", 0.9, 0.8, 0.95)]))["recovery"]
    assert r.binding == "assumption" and r.source.by == "Sean Creighton" and r.sampling == "uniform"


def test_a_run_with_inputs_waiting_is_refused_listing_every_one(store):
    pool = SimpleNamespace(records=[rec("t", "pha_titre", 10.0, "g/L")], records_by_id={})
    with pytest.raises(proforma.ScenarioRefused) as e:
        proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=[assume("sugarFeed", 1000, 1000, 1000)]), pool=pool)
    for key in ("yield", "content", "productivity", "recovery", "sugarPrice"):
        assert key in str(e.value)
    assert "titre" not in str(e.value).split(":")[1] and "sugarFeed" not in str(e.value)


def test_the_basis_comes_back_as_the_same_sampling(store):
    rs = [rec(f"t{i}", "pha_titre", v, "g/L") for i, v in enumerate([10.0, 40.0, 25.0])]
    rs += [rec("y1", "pha_yield_substrate", 0.3, "g g-1"), rec("y2", "pha_yield_substrate", 0.7, "g g-1")]
    rs += [rec("c", "pha_content_cdw", 60.0, "% CDW")]
    inputs = proforma.bind(rs, assumptions=[assume("sugarPrice", 0.4, 0.3, 0.5)], cap=(0.48, "cap"))
    specs, base, kinds = proforma._specs(proforma.basis_inputs(inputs, (0.48, "cap")))
    assert specs["titre"] == {"kind": "triangular", "low": 10.0, "mode": 25.0, "high": 40.0}
    assert specs["yield"] == {"kind": "uniform", "low": 0.3, "high": 0.48}
    assert specs["content"] == {"kind": "fixed", "value": pytest.approx(0.6)}
    assert specs["sugarPrice"] == {"kind": "uniform", "low": 0.3, "high": 0.5} and base["sugarPrice"] == 0.4
    assert kinds == {"titre": "record", "yield": "record", "content": "record", "sugarPrice": "assumption"}


def test_the_scenario_endpoints(store, monkeypatch):
    from openferment_core import api, evidence_pool

    rs = [rec("t", "pha_titre", 10.0, "g/L"), rec("k", "pha_titre", 20.0, "g/L", strain="p-putida-kt2440")]
    monkeypatch.setattr(evidence_pool, "load", lambda: SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}))
    c = TestClient(api.app, base_url="http://127.0.0.1")
    [sc] = c.get("/api/proforma/scenarios").json()
    assert sc["id"] == "sc-pha-1" and sc["hosts"] == ["c-necator-h16", "p-putida-kt2440"]
    assert set(sc["waiting"]) == {"yield", "content", "productivity", "recovery", "sugarPrice", "sugarFeed"}
    assert c.get("/api/proforma/scenarios?host=p-putida-kt2440").json()[0]["inputs"][0]["recordIds"] == ["k"]
    r = c.post("/api/proforma/run", json={"scenarioId": "sc-pha-1"})
    assert r.status_code == 422 and "wait for a source" in r.json()["detail"]
    assert c.post("/api/proforma/run", json={"scenarioId": "sc-pha-1"}, headers={"Origin": "https://evil.example"}).status_code == 403
