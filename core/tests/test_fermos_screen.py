"""What fermOS → Simulate and Forecast ask of the service (OF-BLD-020 §3.3).

A kept simulation feeds a Proforma scenario's titre, yield and batch time
(the §5.1 bridge, now over simulations), what waits is asked with the
person's overrides laid on (GET /api/fermos/bind?overrides=), and a
forecast's start values and length are a parameter scope
(`fermos:forecast:<kinetic fit id>`), so the Forecast tab types no number of
its own (E.1‴).

Every value a person "types" here is a STAND-IN chosen in the test, and
every series is SYNTHETIC; none is a measurement and no number here is a
result.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, fermos, intake, params, proforma
from openferment_core.models import FermosPoint, FermosSeries, Override, ParamResolveRequest, SimulationRequest

BY = "openFerment test fixture"
BATCH = "batch_v1"
SCOPE = f"fermos:family:{BATCH}"
ETHANOL = proforma.ETHANOL
# A batch a person could type whole: every parameter no record binds on an
# empty pool. STAND-INs chosen here, not values of anything.
TYPED = dict(mu_max=0.4, ks=0.2, yxs=0.12, alpha=2.0, yps=0.45, p_max=90.0, x0=0.2, s0=50.0, p0=0.0)


def typed(scope=SCOPE, **values):
    return [Override(scope=scope, key=k, value=v, by=BY, at="2026-10-21", note="a STAND-IN for a test")
            for k, v in values.items()]


EMPTY = SimpleNamespace(records=[], records_by_id={}, hidden={})


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(fermos, "_load_pool", lambda *a, **k: EMPTY)
    return tmp_path


def simulate(family=BATCH, product="ethanol", **over):
    values = {**TYPED, **over}
    return fermos.simulate(SimulationRequest(family=family, product=product, sugar="glucose",
                                             overrides=typed(scope=f"fermos:family:{family}", **values)),
                           by_pool=EMPTY)


# ── a simulation feeds a scenario (the §5.1 bridge, over simulations) ───


def test_a_kept_simulation_feeds_titre_yield_and_productivity_from_its_end_state(store):
    sim = simulate()
    assert sim.provenance == "demo", "every value a person typed makes the simulation demo"
    info = proforma.fit_info(artifacts.get(sim.artifactId), ETHANOL)
    assert info.tool == fermos.SIMULATION and info.refused is None and info.provenance == "demo"
    feeds = {f.key: f for f in info.feeds}
    assert feeds["titre"].value == pytest.approx(sim.finalTitre)
    assert feeds["yield"].value == pytest.approx(sim.yieldAchieved)
    assert feeds["productivity"].value == pytest.approx(sim.productivity)
    # One value each, fixed: a simulation draws no band.
    assert all(f.low == f.value == f.high for f in info.feeds)
    assert info.batchTimeH == pytest.approx(sim.harvestH) and sim.harvestH == sim.sugarRunsOutH
    assert any("not a measurement" in w for w in info.flags), "a simulation never passes for a measurement (D1)"
    assert "the hour its sugar runs out" in feeds["titre"].derivation
    # GET /api/fermos/fits lists it beside the fits and forecasts.
    assert [i.artifactId for i in proforma.fermos_fits(ETHANOL)] == [sim.artifactId]


def test_a_simulation_binds_a_scenarios_inputs_as_an_artifact_and_its_provenance_follows(store):
    sim = simulate()
    rs = [{"id": "q-t", "paperId": "Q7", "field": "ethanol_titre", "value": 40.0, "unit": "g L-1",
           "carbonSource": "glucose", "provenance": "unverified", "status": "unverified", "primary": True,
           "organismText": "Saccharomyces cerevisiae"}]
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}, hidden={})
    fits = {"titre": sim.artifactId, "yield": sim.artifactId, "productivity": sim.artifactId}
    bound = proforma.bind_flowsheet(ETHANOL, pool=pool, fits=fits)
    by = {i.key: i for i in bound.inputs}
    for key in fits:
        assert by[key].binding == "artifact" and by[key].source.id == sim.artifactId
        assert by[key].sampling == "fixed"
    assert "chosen in place of the 1 record it bound" in by["titre"].flags
    extra = proforma.apply_fits(proforma.bind_inputs(ETHANOL, rs, None, None), fits, ETHANOL)
    batch = next(b for b in extra if b.name == "fit batch time")
    assert batch.value == pytest.approx(sim.harvestH) and batch.source.id == sim.artifactId


def test_a_simulation_of_another_product_or_a_chemostat_feeds_nothing_and_says_why(store):
    other = simulate(product="phb")
    info = proforma.fit_info(artifacts.get(other.artifactId), ETHANOL)
    assert info.refused and "simulates phb, not ethanol" in info.refused
    assert all(f.refused == info.refused for f in info.feeds)
    nameless = simulate(product=None)
    info = proforma.fit_info(artifacts.get(nameless.artifactId), ETHANOL)
    assert info.refused is None
    assert any("names no product" in w for w in info.flags)
    chemo = fermos.simulate(SimulationRequest(family="chemostat_v1", product="ethanol", sugar="glucose", overrides=typed(
        scope="fermos:family:chemostat_v1", **TYPED, dilution_rate=0.1, feed_conc=50.0, t_end=100.0)), by_pool=EMPTY)
    info = proforma.fit_info(artifacts.get(chemo.artifactId), ETHANOL)
    assert info.refused and "chemostat" in info.refused and "no batch" in info.refused
    with pytest.raises(proforma.ScenarioRefused, match="cannot feed titre"):
        proforma.apply_fits(proforma.bind_inputs(ETHANOL, [], None, None), {"titre": chemo.artifactId}, ETHANOL)


# ── what waits, with the person's overrides laid on ─────────────────────


def test_bind_lays_the_persons_overrides_on_so_waiting_is_what_simulate_would_refuse(store):
    client = TestClient(_api())
    bare = client.get("/api/fermos/bind", params={"family": BATCH, "product": "ethanol", "sugar": "glucose"})
    assert bare.status_code == 200 and set(bare.json()["waiting"]) == set(TYPED)
    some = {k: v for k, v in TYPED.items() if k != "p_max"}
    r = client.get("/api/fermos/bind", params={
        "family": BATCH, "product": "ethanol", "sugar": "glucose",
        "overrides": json.dumps([o.model_dump() for o in typed(**some)])})
    assert r.status_code == 200 and r.json()["waiting"] == ["p_max"]
    mu = next(v for v in r.json()["values"] if v["key"] == "mu_max")
    assert mu["origin"] == "assumption" and mu["overriddenBy"] == BY
    # Another scope's override is refused in words, never laid on; a list
    # that is not one is the 422 Proforma's binding gives.
    stray = client.get("/api/fermos/bind", params={
        "family": BATCH, "overrides": json.dumps([o.model_dump() for o in typed(scope="proforma:sc-yeast-1", titre=1.0)])})
    assert stray.status_code == 422 and "proforma:sc-yeast-1" in stray.json()["detail"]
    assert client.get("/api/fermos/bind", params={"family": BATCH, "overrides": "{"}).status_code == 422


def _api():
    from openferment_core import api

    return api.app


# ── a forecast's start values and length are the panel's ───────────────

TRUE = {"X0": 0.1, "mu": 0.35, "Xmax": 8.0, "P0": 0.05, "alpha": 0.4, "beta": 0.02, "S0": 60.0, "gamma": 4.5, "delta": 0.05}
T = np.linspace(0, 30, 16)


def _series(role, label, values, unit="g L-1"):
    return FermosSeries(measureId=f"m-{role}", label=label, unit=unit, role=role,
                        points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                for i, (a, b) in enumerate(zip(T, values))])


def _logistic_fit(store, *, family=fermos.LOGISTIC):
    rng = np.random.default_rng(3)
    x, i = fermos.logistic(np.asarray(T, float), TRUE["X0"], TRUE["mu"], TRUE["Xmax"])
    p = TRUE["P0"] + TRUE["alpha"] * (x - TRUE["X0"]) + TRUE["beta"] * i
    s = TRUE["S0"] - TRUE["gamma"] * (x - TRUE["X0"]) - TRUE["delta"] * i
    series = [_series("biomass", "Dry cell weight", x + rng.normal(0, 0.12, len(T))),
              _series("product", "Ethanol", p + rng.normal(0, 0.08, len(T))),
              _series("substrate", "Glucose", s + rng.normal(0, 0.6, len(T)))]
    return fermos.fit("dep-synthetic", series, family=family)


def test_a_forecasts_start_values_and_length_are_a_scope_bound_to_the_fitted_run(store):
    fit = _logistic_fit(store)
    scope = fermos.forecast_scope(fit.kineticArtifactId)
    assert scope == f"fermos:forecast:{fit.kineticArtifactId}"
    got = params.scope(scope)
    assert got.kind == "fermos-forecast" and [s.key for s in got.specs] == ["x0", "s0", "p0", "t_end"]
    assert {s.group for s in got.specs} == {"Start values", "Run length"}
    assert all(s.sourceRule == ["fit", "assumption"] and s.boundsReason for s in got.specs)
    by = {v.key: v for v in got.values}
    for key, name in (("x0", "X0"), ("s0", "S0"), ("p0", "P0")):
        own = fermos.param(fit.kinetic, name)
        assert by[key].origin == "fit" and by[key].value == own.value and by[key].source.id == fit.kineticArtifactId
    assert by["t_end"].value == pytest.approx(30.0) and got.waiting == []
    # A person's value is an assumption by name, and nothing else moves.
    res = params.resolve_scope(scope, ParamResolveRequest(overrides=typed(scope=scope, s0=80.0)))
    s0 = next(v for v in res.values if v.key == "s0")
    assert s0.origin == "assumption" and s0.overriddenBy == BY and s0.value == 80.0
    assert next(v for v in res.values if v.key == "x0").origin == "fit"


def test_a_forecast_scope_takes_the_runs_own_units_and_refuses_what_is_not_a_logistic_fit(store):
    fit = _logistic_fit(store)
    od = fermos.fit("dep-od", [s.model_copy(update={"unit": "OD600"}) if s.role == "biomass" else s
                               for s in fit.kinetic.series])
    got = params.scope(fermos.forecast_scope(od.kineticArtifactId))
    units_ = {s.key: s.unit for s in got.specs}
    assert units_["x0"] == "OD600" and units_["s0"] == "g L-1" and units_["t_end"] == "h"
    client = TestClient(_api())
    assert client.get("/api/params/fermos:forecast:0000000000000000").status_code == 404
    batch = _logistic_fit(store, family=BATCH)
    r = client.get(f"/api/params/fermos:forecast:{batch.kineticArtifactId}")
    assert r.status_code == 422 and "fermos:family:batch_v1" in r.json()["detail"]
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
    r = client.get(f"/api/params/fermos:forecast:{fc.artifactId}")
    assert r.status_code == 422 and "a forecast is drawn from a kinetic fit" in r.json()["detail"]


def test_a_forecast_from_the_panels_values_names_the_person_as_it_did_before(store):
    # The Forecast tab sends the scope's overrides as the forecast's start
    # values and length (src/lib/fermos.ts forecastAsk); the service keeps
    # a changed start an assumption by name, and the length one too, by the
    # person who set it, else the one who changed a start (OF-BLD-020 §3.R,
    # findings 7 and 11; test_fermos_3r holds the length alone).
    fit = _logistic_fit(store)
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId,
                             start=fermos.StartValues(S0=80.0), changed_by=BY, duration_h=40.0)
    names = {i.name: i for i in artifacts.get(fc.artifactId).inputs}
    assert names["start S0"].source.kind == "assumption" and names["start S0"].source.by == BY
    assert names["duration"].value == 40.0 and fc.evidence.provenance == "demo"
    assert names["duration"].source.kind == "assumption" and names["duration"].source.by == BY
