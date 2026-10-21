"""A run follows the parameter panel's overrides (OF-BLD-020 §2.2, D3), with
no simulator.

A person's change on Proforma's scenario page is an Override of scope
`proforma:<scenario id>`, kept in the browser that typed it and carried by
the run, the binding and the ceiling check. Each is laid on as the named
assumption it is: it wins over the records and over a fermOS fit for its
input, the basis names the person, and the run is `demo`. The older
`assumptions` field is read the same way for one release; a run that read
overrides says so in its basis, and a run that read none keeps the basis,
and the artifact id, it had before the panel.

Every record, override and assumption here is a FIXTURE written in the
test, on demo.py's yeast and PHA STAND-IN records; none is a measurement and
no price here is a result. The runs go through the real binding and
artifact code over demo.py's closed-form STAND-IN evaluator.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, basis, demo, intake, params, proforma
from openferment_core.models import InputAssumption, Override, ParamResolveRequest, ProformaRunRequest

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
OTHER = "A second test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
SCOPE = "proforma:sc-yeast-1"


@pytest.fixture()
def standin(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", demo._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records() + demo._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def over(key, value, low=None, high=None, *, scope=SCOPE, by=BY, note="a STAND-IN for a test") -> Override:
    return Override(scope=scope, key=key, value=value, low=low, high=high, by=by, at="2026-10-21", note=note)


def assume(key, value, low=None, high=None, by=BY) -> InputAssumption:
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=by, at="2026-10-21", note="a STAND-IN for a test")


ECONOMICS = [over("plant_scale", 100000.0), over("glucose_price", 0.4, 0.3, 0.5)]


def named(art):
    return {i.name: i for i in art.inputs}


def test_a_runs_overrides_are_bound_as_named_assumptions_and_the_basis_says_so(standin):
    r = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=ECONOMICS, samples=8), pool=standin)
    inputs = {i.key: i for i in r.inputs}
    assert inputs["glucose_price"].binding == "assumption" and inputs["glucose_price"].source.by == BY
    assert (inputs["glucose_price"].value, inputs["glucose_price"].low, inputs["glucose_price"].high) == (0.4, 0.3, 0.5)
    # A value with no range is held at itself, as the browser's assumption was.
    assert (inputs["plant_scale"].low, inputs["plant_scale"].high, inputs["plant_scale"].sampling) == (100000.0, 100000.0, "fixed")
    art = artifacts.get(r.artifactId)
    got = named(art)
    assert got["glucose_price"].source == basis.assumption_source(BY, "2026-10-21", "a STAND-IN for a test")
    assert [got[f"glucose_price {p}"].value for p in ("low", "high")] == [0.3, 0.5]
    assert got[proforma.ASSUMPTIONS_READ].value == "overrides" and got[proforma.ASSUMPTIONS_READ].source.kind == "convention"
    assert art.provenance == "demo" and r.provenance == "demo"


def test_an_override_replaces_the_records_for_its_input_and_reset_brings_them_back(standin):
    plain = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=ECONOMICS, samples=8), pool=standin)
    titre = {i.key: i for i in plain.inputs}["titre"]
    assert titre.binding == "records" and len(titre.records) == 3
    typed = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=[*ECONOMICS, over("titre", 50.0, by=OTHER)],
                                            samples=8), pool=standin)
    t = {i.key: i for i in typed.inputs}["titre"]
    assert t.binding == "assumption" and t.value == 50.0 and t.source.by == OTHER and t.records == []
    assert "chosen in place of the 3 records it bound" in t.flags
    got = named(artifacts.get(typed.artifactId))
    assert "titre record" not in got and got["titre"].value == 50.0 and got["titre"].source.by == OTHER
    assert typed.artifactId != plain.artifactId
    # Reset to source: the same run without the override binds the records again, the same artifact.
    again = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=ECONOMICS, samples=8), pool=standin)
    assert again.artifactId == plain.artifactId
    # The binding and the panel lay it on the same way.
    bound = {i.key: i for i in proforma.bound(ETHANOL, assumptions=proforma.named_values(None, [over("titre", 50.0)])[0],
                                              pool=standin).inputs}
    assert bound["titre"].binding == "assumption" and bound["titre"].value == 50.0
    resolved = {v.key: v for v in params.resolve_scope(SCOPE, ParamResolveRequest(overrides=[over("titre", 50.0)])).values}
    assert resolved["titre"].origin == "assumption" and resolved["titre"].value == 50.0


def test_an_override_wins_over_a_fermos_fit_for_its_input(standin, monkeypatch):
    called = []
    monkeypatch.setattr(proforma, "apply_fits", lambda inputs, fits, flowsheet: called.append(dict(fits)) or [])
    proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=[*ECONOMICS, over("titre", 50.0)],
                                    fits={"titre": "0123456789abcdef", "yield": "0123456789abcdef"}, samples=8), pool=standin)
    assert called == [{"yield": "0123456789abcdef"}], "the overridden input takes no fit"
    assert proforma.fits_beside({"titre": "a", "yield": "b"}, [assume("titre", 1.0)]) == {"yield": "b"}


def test_the_older_assumptions_field_still_works_for_one_release(standin):
    old = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]
    shim = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=old, samples=8), pool=standin)
    panel = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=ECONOMICS, samples=8), pool=standin)
    a, b = named(artifacts.get(shim.artifactId)), named(artifacts.get(panel.artifactId))
    # The same values, bound the same way: the one difference is the line saying overrides were read.
    assert proforma.ASSUMPTIONS_READ not in a and set(b) - set(a) == {proforma.ASSUMPTIONS_READ}
    assert all(a[k] == b[k] for k in a if k != proforma.ASSUMPTIONS_READ)
    assert shim.basePrice == panel.basePrice
    # Both fields at once are read together, and the basis says both.
    both = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=[ECONOMICS[0]], assumptions=[old[1]],
                                           samples=8), pool=standin)
    assert "assumptions, the older field" in str(named(artifacts.get(both.artifactId))[proforma.ASSUMPTIONS_READ].value)


def test_a_run_with_no_override_keeps_the_basis_and_the_artifact_id_it_had(standin):
    # Every run before the panel read the older field alone (or nothing). Its
    # basis is the one the binding and basis_inputs build, with nothing
    # added, so the artifact id a re-run finds is the one already kept.
    old = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]
    for req in (ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=old, samples=8),
                ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=old, samples=8)):
        r = proforma.run(req, pool=standin)
        inputs = proforma.bind_inputs(ETHANOL, standin.records, None, old)
        before = proforma.basis_inputs(inputs, None, ETHANOL, 8, scenario_id=req.scenarioId, fitted=[])
        art = artifacts.get(r.artifactId)
        assert [i.model_dump() for i in art.inputs] == [i.model_dump() for i in before]
        assert artifacts.compute(proforma.RUN, before, records_by_id=standin.records_by_id, seed=0).id == r.artifactId
        assert proforma.ASSUMPTIONS_READ not in named(art)
    pha = proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", samples=8, assumptions=[
        assume("recovery", 0.95, 0.9, 0.98), assume("sugarPrice", 0.4, 0.3, 0.5), assume("sugarFeed", 10000.0)]), pool=standin)
    assert proforma.ASSUMPTIONS_READ not in named(artifacts.get(pha.artifactId))


def test_overrides_that_cannot_stand_are_refused_in_words(standin, client):
    for extra, words in (
        ([over("titre", 50.0, scope="proforma:sc-pha-1")], "sent for proforma:sc-yeast-1: proforma:sc-pha-1"),
        ([over("titre", "a lot")], "the override of titre takes a number, not words"),
        ([over("titre", 50.0), over("titre", 60.0)], "two overrides of titre"),
        ([over("recovery", 0.9)], "ethanol_glucose_v0 takes no input recovery"),
        ([over("ethanol_purity", 1.0)], "ethanol_purity is a convention every run of ethanol_glucose_v0 states"),
        ([over("titre", 50.0, by="me")], "needs a person's name"),
        ([over("titre", 50.0, low=60.0)], "must lie within its own low and high"),
    ):
        with pytest.raises(proforma.ScenarioRefused, match=words.replace("(", r"\(")):
            proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=[*ECONOMICS, *extra], samples=4), pool=standin)
        r = client.post("/api/proforma/run", json={"scenarioId": "sc-yeast-1", "samples": 4,
                                                   "overrides": [o.model_dump() for o in (*ECONOMICS, *extra)]})
        assert r.status_code == 422 and words in r.json()["detail"], (extra, r.json())
    with pytest.raises(proforma.ScenarioRefused, match="named in both overrides and assumptions"):
        proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=ECONOMICS, assumptions=[assume("plant_scale", 1.0)],
                                        samples=4), pool=standin)
    assert not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]


def test_the_endpoints_carry_overrides(standin, client):
    import json

    body = {"scenarioId": "sc-yeast-1", "samples": 4, "overrides": [o.model_dump() for o in ECONOMICS]}
    r = client.post("/api/proforma/run", json=body)
    assert r.status_code == 200
    art = artifacts.get(r.json()["artifactId"])
    assert named(art)["plant_scale"].source.by == BY and named(art)[proforma.ASSUMPTIONS_READ].value == "overrides"
    # GET /api/proforma/bind lays a person's overrides over the records.
    q = json.dumps([over("titre", 50.0, scope=f"proforma:{MADE_HERE}").model_dump()])
    b = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "overrides": q})
    assert b.status_code == 200
    titre = next(i for i in b.json()["inputs"] if i["key"] == "titre")
    assert titre["binding"] == "assumption" and titre["value"] == 50.0 and titre["source"]["by"] == BY
    for raw, words in (("[1]", "overrides is a JSON list of overrides"),
                       (json.dumps([over("titre", 50.0, scope="fermos:family:batch_v1").model_dump()]), "proforma:<scenario id>"),
                       (json.dumps([over("recovery", 0.5).model_dump()]), "takes no input recovery")):
        bad = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "overrides": raw})
        assert bad.status_code == 422 and words in bad.json()["detail"], (raw, bad.json())
    # The ceiling check reads the yield a person's override sets, records or not.
    y = json.dumps([over("yield", 0.42).model_dump()])
    c = client.get("/api/proforma/ceiling-check", params={"scenarioId": "sc-yeast-1", "overrides": y})
    assert c.status_code == 200 and c.json()["yieldBinding"] == "assumption" and c.json()["yieldValue"] == 0.42
    # The older field is still read there for one release.
    a = json.dumps([assume("yield", 0.41).model_dump()])
    c = client.get("/api/proforma/ceiling-check", params={"scenarioId": "sc-yeast-1", "assumptions": a})
    assert c.status_code == 200 and c.json()["yieldValue"] == 0.41
    wrong = client.get("/api/proforma/ceiling-check", params={"scenarioId": "sc-yeast-1", "overrides": json.dumps(
        [over("yield", 0.42, scope="proforma:sc-pha-1").model_dump()])})
    assert wrong.status_code == 422 and "names the scope it changes" in wrong.json()["detail"]


def test_resolve_warns_outside_the_bounds_and_keeps_the_value(standin, client):
    # D4: a yield above the ontology's plausibility range is kept, never clamped, and said.
    o = over("yield", 0.7).model_dump()
    r = client.post(f"/api/params/{SCOPE}/resolve", json={"overrides": [o]})
    assert r.status_code == 200
    got = {v["key"]: v for v in r.json()["values"]}
    assert got["yield"]["value"] == 0.7 and got["yield"]["origin"] == "assumption" and got["yield"]["overriddenBy"] == BY
    assert r.json()["warnings"] == [got["yield"]["outOfBounds"]]
    assert "ethanol_yield_substrate" in got["yield"]["outOfBounds"] and "kept as given" in got["yield"]["outOfBounds"]
    # A run made with it binds the value as typed.
    run = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", overrides=[*ECONOMICS, over("yield", 0.45)], samples=4),
                       pool=standin)
    assert {i.key: i for i in run.inputs}["yield"].value == 0.45
