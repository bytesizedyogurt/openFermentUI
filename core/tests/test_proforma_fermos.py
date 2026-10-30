"""A fermOS fit feeds a scenario's titre, yield and batch time (OF-BLD-019
§5.1, D10), with no simulator.

Every series here is SYNTHETIC, built in the test from parameters chosen here
(test_fermos's generating batch), and every record and assumption is a
FIXTURE; none is a measurement and no value here is a result. The fits and
forecasts go through the real fermOS code into a scratch artifact store; the
runs go through the real binding and artifact code over demo.py's closed-form
STAND-IN evaluator.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, basis, fermos, intake, proforma
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.models import (
    ComputedBasis,
    FermosPoint,
    FermosSeries,
    InputAssumption,
    ProformaRunRequest,
)

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
# The generating batch, chosen here (test_fermos's), not measured.
TRUE = {"X0": 0.1, "mu": 0.35, "Xmax": 8.0, "P0": 0.05, "alpha": 0.4, "beta": 0.02, "S0": 60.0, "gamma": 4.5, "delta": 0.05}
T = np.linspace(0, 30, 16)
SD = (0.12, 0.08, 0.6)
# How long a person asks a forecast to run so that its sugar is spent: a
# setting of this test.
LONG_H = 200.0


def series(role, label, t, v, unit="g L-1"):
    return FermosSeries(measureId=f"m-{label.lower()}", label=label, unit=unit, role=role,
                        points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                for i, (a, b) in enumerate(zip(t, v))])


def batch(product="Ethanol", substrate="Glucose", seed=3, with_sugar=True):
    rng = np.random.default_rng(seed)
    x, i = fermos.logistic(np.asarray(T, float), TRUE["X0"], TRUE["mu"], TRUE["Xmax"])
    p = TRUE["P0"] + TRUE["alpha"] * (x - TRUE["X0"]) + TRUE["beta"] * i
    s = TRUE["S0"] - TRUE["gamma"] * (x - TRUE["X0"]) - TRUE["delta"] * i
    out = [series("biomass", "Dry cell weight", T, x + rng.normal(0, SD[0], len(T))),
           series("product", product, T, p + rng.normal(0, SD[1], len(T)))]
    if with_sugar:
        out.append(series("substrate", substrate, T, s + rng.normal(0, SD[2], len(T))))
    return out


def assume(key, value, low=None, high=None):
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=BY, at="2026-10-20", note="a STAND-IN for a test")


ASSUMED = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def standin(monkeypatch, store):
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = standins._standin_records() + standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def kept_fit(dep="dep-ethanol", **kw):
    fit = fermos.fit(dep, batch(**kw))
    assert fit.kineticArtifactId, fit.kinetic.reason
    return fit


def feeds_of(info):
    return {f.key: f for f in info.feeds}


# ── what a fit can feed ────────────────────────────────────────────────


def test_a_forecast_run_until_the_sugar_is_spent_feeds_all_three_from_its_own_numbers(store):
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    assert fc.substrateRunsOutH is not None
    info = proforma.fit_info(artifacts.get(fc.artifactId), ETHANOL)
    f = feeds_of(info)
    assert info.refused is None and all(x.refused is None for x in info.feeds)
    # The batch time is the hour the median sugar runs out, found between the
    # last of the forecast's points with sugar left and the first without
    # (§5.R), and every number is the forecast's own, drawn again to that
    # hour with its fit and seed: titre its final product, yield its Yp/s,
    # productivity the titre over that hour.
    assert fc.times[-2] < info.batchTimeH <= fc.substrateRunsOutH
    again = fermos.forecast(fermos.fit_of(artifacts.get(fc.artifactId)), None, info.batchTimeH, fc.seed)
    final = next(x for x in again["finals"] if x["role"] == "product")
    assert (f["titre"].low, f["titre"].value, f["titre"].high) == pytest.approx((final["low"], final["median"], final["high"]))
    y = again["yieldInterval"]
    assert (f["yield"].low, f["yield"].value, f["yield"].high) == pytest.approx((y["low"], y["median"], y["high"]))
    assert f["productivity"].value == pytest.approx(final["median"] / info.batchTimeH)
    assert f["productivity"].low == pytest.approx(final["low"] / info.batchTimeH)
    assert "drawn again to the hour its median sugar runs out" in f["titre"].derivation
    assert info.depositionId == "dep-ethanol" and info.fitArtifactId == fit.kineticArtifactId
    assert info.productSeries == "Ethanol" and info.substrateSeries == "Glucose" and info.flags == []


def test_what_a_fit_feeds_does_not_move_with_the_length_its_forecast_was_asked_to_run(store):
    """OF-BLD-019 §5.R, finding 0: a forecast lays its points over the whole
    length asked, so the first point where its median sugar is spent can lie
    far past the hour it runs out. The hour is found between grid points and
    the forecast drawn again to it, so a forecast of one fit asked for 200 h
    and one asked for 3000 h feed the same titre, yield, productivity and
    batch time, within 1 %."""
    fit = kept_fit()
    infos = []
    for hours in (LONG_H, 3000.0):
        fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=hours)
        assert fc.substrateRunsOutH is not None
        infos.append(proforma.fit_info(artifacts.get(fc.artifactId), ETHANOL))
    short, long_ = infos
    assert long_.batchTimeH == pytest.approx(short.batchTimeH, rel=0.01)
    a, b = feeds_of(short), feeds_of(long_)
    for k in proforma.FIT_KEYS:
        assert a[k].refused is None and b[k].refused is None, (a[k].refused, b[k].refused)
        for part in ("low", "value", "high"):
            assert getattr(b[k], part) == pytest.approx(getattr(a[k], part), rel=0.01), (k, part)


def test_a_fit_forecast_under_its_own_length_gives_titre_and_yield_and_says_why_no_batch_time(store):
    fit = kept_fit()
    info = proforma.fit_info(artifacts.get(fit.kineticArtifactId), ETHANOL)
    f = feeds_of(info)
    assert f["titre"].refused is None and f["yield"].refused is None
    assert "does not run out within" in f["productivity"].refused and "fermOS → Forecast" in f["productivity"].refused
    # The forecast it reads is the one growth_forecast keeps, drawn the same way.
    kept = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
    assert f["titre"].value == pytest.approx(next(x for x in kept.finals if x.role == "product").median)


def test_the_list_holds_every_fit_and_forecast_and_nothing_else(store):
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    listed = proforma.fermos_fits(ETHANOL)
    assert sorted(i.artifactId for i in listed) == sorted([fit.kineticArtifactId, fc.artifactId])
    assert {i.tool for i in listed} == {"kinetic_fit", "growth_forecast"}
    assert all(i.provenance == "computed" for i in listed)
    with pytest.raises(proforma.ScenarioRefused, match="reference biorefinery"):
        proforma.fermos_fits("corn_drygrind")


# ── the binding, the run and its basis ─────────────────────────────────


def test_a_chosen_fit_binds_titre_yield_and_productivity_and_the_run_names_it(standin):
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    fits = {k: fc.artifactId for k in proforma.FIT_KEYS}
    info = proforma.bind_flowsheet(ETHANOL, pool=standin, fits=fits)
    by = {i.key: i for i in info.inputs}
    for k in proforma.FIT_KEYS:
        assert by[k].binding == "artifact" and by[k].source.kind == "artifact" and by[k].source.id == fc.artifactId
        assert by[k].records == [] and by[k].sampling == "triangular" and by[k].source.note
    assert "productivity" not in info.waiting and by["titre"].flags == ["chosen in place of the 3 records it bound"]

    run = proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=ASSUMED, fits=fits), pool=standin)
    art = artifacts.get(run.artifactId)
    named = {i.name: i for i in art.inputs}
    for k in proforma.FIT_KEYS:
        for part in ("", " low", " high"):
            i = named[f"{k} fit{part}"]
            assert i.source.kind == "artifact" and i.source.id == fc.artifactId
    assert named["titre fit"].value == pytest.approx(by["titre"].value)
    batch = proforma.fit_info(artifacts.get(fc.artifactId), ETHANOL).batchTimeH
    assert named["fit batch time"].value == pytest.approx(batch) and named["fit batch time"].unit == "h"
    assert not any(i.name.startswith("titre record") for i in art.inputs)
    assert {s.key: s.sourceKind for s in run.sensitivity}.get("titre") == "artifact"
    # The fit's provenance enters through basis_provenance: alone, the fit's
    # inputs make the value computed (the fit rests on a deposition's
    # measured readings); the assumptions make the whole run standins.
    fit_inputs = [i for i in art.inputs if i.source.kind == "artifact"]
    alone = ComputedBasis(tool="t", toolVersion="v", inputs=fit_inputs, artifactId="x", at="now")
    assert basis.basis_provenance(alone, {}, {fc.artifactId: artifacts.get(fc.artifactId)}) == "computed"
    assert run.provenance == "demo"
    # A forecast a person changed is an assumption, so a run fed by it is demo by its own inputs.
    changed = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H,
                                  start=fermos.StartValues(S0=55.0), changed_by="Sean Creighton")
    assert proforma.fit_info(artifacts.get(changed.artifactId), ETHANOL).provenance == "demo"


def test_a_fits_productivity_feeds_the_fermenter_only_beside_its_own_titre(standin):
    """OF-BLD-019 §5.R, finding 1: productivity from a fit is its titre over
    the hour its sugar runs out, and the fermenter's batch time is the bound
    titre over the bound productivity. Beside a titre from records, a
    person's assumption or another fit, that batch time is not the fit's,
    and the basis would name one the run did not use; so it is refused in
    words naming titre, and nothing is kept."""
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    before = len(artifacts.all_artifacts())
    for fits, said in (({"productivity": fc.artifactId, "yield": fc.artifactId}, "titre binds 3 records"),
                       ({"titre": fit.kineticArtifactId, "yield": fit.kineticArtifactId, "productivity": fc.artifactId},
                        f"titre is from {fit.kineticArtifactId}")):
        with pytest.raises(proforma.ScenarioRefused) as refused:
            proforma.bind_flowsheet(ETHANOL, pool=standin, fits=fits)
        words = str(refused.value)
        assert f"productivity from growth_forecast {fc.artifactId}" in words and said in words, words
        assert f"choose {fc.artifactId} for titre as well, or stop using it for productivity" in words, words
        with pytest.raises(proforma.ScenarioRefused, match="only beside titre from"):
            proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=ASSUMED, fits=fits), pool=standin)
    # No stand-in record is of S288C, so there titre takes a person's assumption.
    with pytest.raises(proforma.ScenarioRefused, match="titre is a named person's assumption"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, host="s-cerevisiae-s288c", fits={"productivity": fc.artifactId},
                                assumptions=[assume("titre", 60.0, 50.0, 70.0)])
    assert len(artifacts.all_artifacts()) == before
    # Beside its own titre the run goes, and its basis names the fit's batch time.
    ok = proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": fc.artifactId, "productivity": fc.artifactId})
    assert {i.key: i.binding for i in ok.inputs}["productivity"] == "artifact"


def test_a_fit_on_the_pha_draft_binds_through_the_same_rule(standin):
    fit = kept_fit(dep="dep-pha", product="PHB", substrate="Glucose")
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    info = proforma.bind_flowsheet(proforma.FLOWSHEET, include_archived=True, pool=standin, fits={"titre": fc.artifactId})
    by = {i.key: i for i in info.inputs}
    assert by["titre"].binding == "artifact" and by["yield"].binding == "records"


# ── refusals, in words naming the parameter ────────────────────────────


def _unidentify(aid: str, name: str) -> None:
    """A STAND-IN: the kept fit as a run that did not identify `name` would
    leave it, its interval reaching zero (as test_fermos does to a fit)."""
    art = artifacts.get(aid)
    params = [dict(p, low=-1.0, identified=False) if p["name"] == name else p for p in art.output["params"]]
    changed = art.model_copy(update={"output": {**art.output, "params": params}})
    (intake.DATA_DIR / "artifacts" / f"{aid}.json").write_text(changed.model_dump_json(indent=2) + "\n", encoding="utf-8")


def test_an_unidentified_mu_refuses_naming_mu(standin):
    fit = kept_fit()
    _unidentify(fit.kineticArtifactId, "mu")
    info = proforma.fit_info(artifacts.get(fit.kineticArtifactId), ETHANOL)
    assert info.refused and "μ (mu) is not identified" in info.refused and "exponentially" in info.refused
    assert all(f.refused == info.refused for f in info.feeds)
    with pytest.raises(proforma.ScenarioRefused, match=r"cannot feed titre: μ \(mu\) is not identified"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": fit.kineticArtifactId})
    with pytest.raises(proforma.ScenarioRefused, match=r"μ \(mu\) is not identified"):
        proforma.run(ProformaRunRequest(scenarioId="sc-yeast-1", assumptions=ASSUMED,
                                        fits={"yield": fit.kineticArtifactId}), pool=standin)


def test_an_unidentified_xmax_refuses_naming_xmax(standin):
    fit = kept_fit()
    _unidentify(fit.kineticArtifactId, "Xmax")
    with pytest.raises(proforma.ScenarioRefused, match="Xmax .*is not identified.*levels off"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"yield": fit.kineticArtifactId})


def test_a_fit_with_no_sugar_series_refuses_the_batch_time_and_the_yield(standin):
    fit = kept_fit(with_sugar=False)
    f = feeds_of(proforma.fit_info(artifacts.get(fit.kineticArtifactId), ETHANOL))
    assert f["titre"].refused is None
    assert "no Yp/s" in f["yield"].refused and "no sugar series" in f["yield"].refused
    assert "no sugar series" in f["productivity"].refused and "batch time" in f["productivity"].refused
    with pytest.raises(proforma.ScenarioRefused, match="cannot feed productivity: productivity is titre over batch time, and no sugar series"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"productivity": fit.kineticArtifactId})
    # The titre it can give, it gives.
    ok = proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": fit.kineticArtifactId})
    assert {i.key: i.binding for i in ok.inputs}["titre"] == "artifact"


def test_one_unit_spelled_two_ways_is_one_unit_and_gives_the_yield(store):
    """OF-BLD-019 §5.R, finding 3: product in 'g L-1' and sugar in 'g/L' are
    one mass concentration (units.normalize), so the fit gives the same Yp/s
    as one whose series spell it alike; a refusal says what is true."""
    alike = feeds_of(proforma.fit_info(artifacts.get(kept_fit(dep="dep-alike").kineticArtifactId), ETHANOL))
    spelled = batch()
    spelled[2] = spelled[2].model_copy(update={"unit": "g/L"})
    fit = fermos.fit("dep-spelled", spelled)
    mixed = feeds_of(proforma.fit_info(artifacts.get(fit.kineticArtifactId), ETHANOL))
    assert mixed["yield"].refused is None, mixed["yield"].refused
    assert (mixed["yield"].low, mixed["yield"].value, mixed["yield"].high) == pytest.approx(
        (alike["yield"].low, alike["yield"].value, alike["yield"].high))
    # A forecast kept before the two spellings were read as one, with no Yp/s
    # (a STAND-IN: its file rewritten so), says so, never that they differ.
    kept = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=30.0)
    art = artifacts.get(kept.artifactId)
    old = art.model_copy(update={"output": {**art.output, "yieldInterval": None}})
    (intake.DATA_DIR / "artifacts" / f"{art.id}.json").write_text(old.model_dump_json(indent=2) + "\n", encoding="utf-8")
    said = feeds_of(proforma.fit_info(artifacts.get(art.id), ETHANOL))["yield"].refused
    assert "drawn before g L-1 and g/L were read as one unit" in said, said
    # Two mass units that are not one are refused, saying which.
    other = batch()
    other[2] = other[2].model_copy(update={"unit": "mg/L"})
    refused = feeds_of(proforma.fit_info(artifacts.get(fermos.fit("dep-mg", other).kineticArtifactId), ETHANOL))["yield"].refused
    assert "g L-1" in refused and "mg/L" in refused, refused


def test_a_fit_of_another_products_series_is_refused_whole(standin):
    fit = kept_fit(product="Polymer (PHB)")
    info = proforma.fit_info(artifacts.get(fit.kineticArtifactId), ETHANOL)
    assert info.refused and "is phb, not ethanol" in info.refused
    with pytest.raises(proforma.ScenarioRefused, match="not ethanol"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": fit.kineticArtifactId})
    # A product series that names nothing is read as the scenario's, and says so.
    plain = kept_fit(dep="dep-plain", product="Product A")
    assert proforma.fit_info(artifacts.get(plain.kineticArtifactId), ETHANOL).flags == [
        "its product series, Product A, names no product: it is read as ethanol because a person chose it"]


def test_a_damaged_fit_file_refuses_what_rests_on_it_and_the_rest_still_lists(client):
    """OF-BLD-019 §5.R, finding 2: a forecast whose kinetic fit's file is
    damaged on disk is refused in words naming the damage; every other fit
    still lists, and the endpoint answers."""
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    other = kept_fit(dep="dep-other", seed=5)
    path = artifacts.folder() / f"{fit.kineticArtifactId}.json"
    path.write_text(path.read_text(encoding="utf-8")[:200], encoding="utf-8")  # cut short, as a partial write
    listed = {i.artifactId: i for i in proforma.fermos_fits(ETHANOL)}
    assert set(listed) == {fc.artifactId, other.kineticArtifactId}
    assert listed[fc.artifactId].refused and "is damaged on disk" in listed[fc.artifactId].refused
    assert listed[fc.artifactId].depositionId is None and listed[fc.artifactId].fitArtifactId == fit.kineticArtifactId
    assert listed[other.kineticArtifactId].refused is None
    r = client.get("/api/fermos/fits", params={"flowsheet": ETHANOL})
    assert r.status_code == 200 and len(r.json()) == 2
    b = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "fits": json.dumps({"titre": fc.artifactId})})
    assert b.status_code == 422 and "damaged on disk" in b.json()["detail"]


def test_the_rest_is_refused_in_words(standin):
    fit = kept_fit()
    with pytest.raises(proforma.ScenarioRefused, match="feeds titre, yield, productivity alone; plant_scale"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"plant_scale": fit.kineticArtifactId})
    with pytest.raises(proforma.ScenarioRefused, match="no kept artifact 0123456789abcdef"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": "0123456789abcdef"})
    with pytest.raises(proforma.ScenarioRefused, match="growth_fit, not a kinetic fit or a forecast"):
        proforma.bind_flowsheet(ETHANOL, pool=standin, fits={"titre": fermos.fit("dep-g", batch()).growthArtifactId})


# ── the endpoints ──────────────────────────────────────────────────────


def test_the_fits_endpoint_and_the_bind_endpoint_with_fits(client):
    fit = kept_fit()
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=LONG_H)
    r = client.get("/api/fermos/fits", params={"flowsheet": ETHANOL})
    assert r.status_code == 200 and {x["artifactId"] for x in r.json()} == {fit.kineticArtifactId, fc.artifactId}
    assert client.get("/api/fermos/fits", params={"flowsheet": "toy"}).status_code == 422
    assert client.get("/api/fermos/fits").status_code == 422  # the flowsheet is named

    fits = {k: fc.artifactId for k in proforma.FIT_KEYS}
    b = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "fits": json.dumps(fits)})
    assert b.status_code == 200
    by = {i["key"]: i for i in b.json()["inputs"]}
    assert all(by[k]["binding"] == "artifact" and by[k]["source"]["id"] == fc.artifactId for k in proforma.FIT_KEYS)
    assert "productivity" not in b.json()["waiting"]
    bad = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "fits": "[1]"})
    assert bad.status_code == 422 and "JSON object" in bad.json()["detail"]
    refused = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "fits": json.dumps({"productivity": fit.kineticArtifactId})})
    assert refused.status_code == 422 and "does not run out" in refused.json()["detail"]

    ran = client.post("/api/proforma/run", json={"scenarioId": "sc-yeast-1", "fits": fits,
                                                  "assumptions": [a.model_dump() for a in ASSUMED]})
    assert ran.status_code == 200 and {i["key"]: i["binding"] for i in ran.json()["inputs"]}["yield"] == "artifact"
