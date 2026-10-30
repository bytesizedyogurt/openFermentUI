"""The Phase 3 review's binding, forecast and tool findings, each held
(OF-BLD-020 §3.R, part B: findings 4, 7, 9, 11, 13, 15, 16 and 20; 21 is
test_check_tools' planted files). Findings 6, 10, 12, 14, 18 and 19 held the
program switch and the storage family, which alpha 2.0 removed (ADR-010).

A forecast's length a person typed is that person's assumption; a forecast
chosen as a fit gives what it holds; a fit of a family gives the terms it
held, so a simulation from it is the model that was fitted.

Every value a person "types" here is a STAND-IN chosen in the test, every
record is a STAND-IN written in the test, and every series is SYNTHETIC;
none is a measurement and no number here is a result.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, fermos, intake, kinetics, params, proforma, tools
from openferment_core.models import Override, ParamResolveRequest, SimulationRequest

BY = "openFerment test fixture"
OTHER = "Another test fixture"
BATCH = "batch_v1"
ETHANOL = proforma.ETHANOL
EMPTY = SimpleNamespace(records=[], records_by_id={})
# STAND-INs a person could type, chosen here, not values of anything.
BATCH_TYPED = dict(mu_max=0.4, ks=0.2, yxs=0.12, alpha=2.0, yps=0.45, p_max=90.0, x0=0.2, s0=50.0, p0=0.0)


def typed(family=BATCH, by=BY, **values):
    return [Override(scope=fermos.family_scope(family), key=k, value=v, by=by, at="2026-10-21",
                     note="a STAND-IN for a test") for k, v in values.items()]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(fermos, "_load_pool", lambda *a, **k: EMPTY)
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    return tmp_path


def _api():
    from openferment_core import api

    return TestClient(api.app)


def _batch(**over) -> str:
    return fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                             overrides=typed(**{**BATCH_TYPED, **over})), by_pool=EMPTY).artifactId


def _ctx(pool=EMPTY):
    c = tools.ToolContext(pool_factory=lambda: pool)
    c.ask_id, c.model = "ask-3r", "claude-haiku-5-5"
    return c


# ── a damaged kept simulation is a refusal in words (finding 9) ────────


def test_a_damaged_kept_simulation_is_refused_in_words_on_bind_and_simulate_never_a_500(store):
    from standins import plant_damaged

    sid = _batch()
    assert artifacts.get(sid).id == sid
    plant_damaged(sid)
    client = _api()
    ask = {"family": BATCH, "product": "ethanol", "sugar": "glucose", "startFrom": f"simulation:{sid}"}
    r = client.get("/api/fermos/bind", params=ask)
    assert r.status_code == 422 and sid in r.json()["detail"] and "cannot be read" in r.json()["detail"]
    r = client.post("/api/fermos/simulate", json=ask)
    assert r.status_code == 422 and sid in r.json()["detail"]
    r = client.get(f"/api/params/{fermos.family_scope(BATCH)}", params=ask)
    assert r.status_code in (409, 422) and sid in r.json()["detail"]


# ── a forecast's length is a person's, named (findings 7, 11) ───────────

TRUE = {"X0": 0.1, "mu": 0.35, "Xmax": 8.0, "P0": 0.05, "alpha": 0.4, "beta": 0.02, "S0": 60.0, "gamma": 4.5, "delta": 0.05}
T = np.linspace(0, 30, 16)


def _logistic_fit():
    from test_fermos_screen import _series

    rng = np.random.default_rng(3)
    x, i = fermos.logistic(np.asarray(T, float), TRUE["X0"], TRUE["mu"], TRUE["Xmax"])
    p = TRUE["P0"] + TRUE["alpha"] * (x - TRUE["X0"]) + TRUE["beta"] * i
    s = TRUE["S0"] - TRUE["gamma"] * (x - TRUE["X0"]) - TRUE["delta"] * i
    series = [_series("biomass", "Dry cell weight", x + rng.normal(0, 0.12, len(T))),
              _series("product", "Ethanol", p + rng.normal(0, 0.08, len(T))),
              _series("substrate", "Glucose", s + rng.normal(0, 0.6, len(T)))]
    return fermos.fit("dep-synthetic", series).kineticArtifactId


def test_a_forecast_length_a_person_typed_is_their_assumption_and_makes_the_forecast_demo(store):
    fit_id = _logistic_fit()
    scope = fermos.forecast_scope(fit_id)
    o = Override(scope=scope, key="t_end", value=12.0, by=BY, at="2026-10-21", note="a STAND-IN for a test")
    res = params.resolve_scope(scope, ParamResolveRequest(overrides=[o]))
    t_end = next(v for v in res.values if v.key == "t_end")
    assert t_end.origin == "assumption" and t_end.overriddenBy == BY
    # As FermOSForecast sends it: the length and who set it, no start changed.
    fc = fermos.forecast_run(fit_artifact=fit_id, duration_h=12.0, duration_by=BY)
    named = {i.name: i for i in artifacts.get(fc.artifactId).inputs}
    assert named["duration"].source.kind == "assumption" and named["duration"].source.by == BY
    assert fc.evidence.provenance == "demo"
    # The reviewer's call: the one who changed a start names the length when nobody else is named.
    fc = fermos.forecast_run(fit_artifact=fit_id, duration_h=12.0, changed_by=BY)
    assert artifacts.get(fc.artifactId).provenance == "demo"
    # Through the API, and on to Proforma: what the forecast feeds is demo too.
    r = _api().post("/api/fermos/forecast", json={"fitArtifactId": fit_id, "durationH": 12.0, "durationBy": BY})
    assert r.status_code == 200 and r.json()["evidence"]["provenance"] == "demo"
    info = proforma.fit_info(artifacts.get(r.json()["artifactId"]), ETHANOL)
    assert info.provenance == "demo"
    # A length nobody is named for stays the caller's convention, as asked.
    fc = fermos.forecast_run(fit_artifact=fit_id, duration_h=12.0)
    named = {i.name: i for i in artifacts.get(fc.artifactId).inputs}
    assert named["duration"].source.kind == "convention" and fc.evidence.provenance != "demo"


# ── a forecast chosen as the fit gives what it holds (finding 13) ───────


def test_a_forecast_chosen_as_the_fit_binds_its_own_start_values_and_length_with_the_person_named(store):
    fit_id = _logistic_fit()
    fc = fermos.forecast_run(fit_artifact=fit_id, start=fermos.StartValues(X0=0.5, S0=90.0), changed_by=BY,
                             duration_h=40.0)
    values, _ = fermos.bind_parameters(BATCH, None, "ethanol", "glucose", EMPTY, [], fc.artifactId, None,
                                       duration_preset=fermos.FIT_LENGTH)
    v = {x.key: x for x in values}
    assert v["x0"].value == pytest.approx(0.5) and v["s0"].value == pytest.approx(90.0)
    for key in ("x0", "s0", "t_end"):
        assert v[key].origin == "fit" and v[key].source.id == fc.artifactId and BY in v[key].source.note, key
    assert v["t_end"].value == pytest.approx(40.0)
    # What the forecast took unchanged from its fit is credited to the fit, naming the forecast.
    assert v["mu_max"].source.id == fit_id and fc.artifactId in v["mu_max"].source.note
    assert v["p0"].source.id == fit_id
    # Yp/s is the forecast's as kept, under the same start values.
    assert v["yps"].source.id == fc.artifactId


# ── a fit of the family is the model that was fitted (findings 4, 15) ──


def test_a_simulation_from_a_batch_fit_with_nothing_else_named_runs_the_fitted_model(store, monkeypatch):
    from test_fermos_bind import STANDIN_BATCH, TIMES, _batch_fit

    fit_id = _batch_fit(monkeypatch)
    # As fermOS → Forecast asks it: no product, no sugar, nothing typed.
    ask = {"family": BATCH, "product": None, "sugar": None, "fitArtifact": fit_id, "startFrom": "fit",
           "durationPreset": "fit-length"}
    b = fermos.bind(SimulationRequest(**ask))
    assert b.waiting == [], b.waiting
    held = {v.key: v for v in b.values}
    assert held["p_max"].origin == "fit" and held["p_max"].value == kinetics.OFF and held["p_max"].source.id == fit_id
    assert held["kd"].origin == "fit" and held["kd"].value == 0 and held["ki_substrate"].value == kinetics.OFF
    r = _api().post("/api/fermos/simulate", json=ask)
    assert r.status_code == 200, r.text
    out = r.json()
    with monkeypatch.context() as m:
        m.setattr(kinetics, "RTOL", 1e-12)
        m.setattr(kinetics, "ATOL", 1e-14)
        truth = kinetics.FAMILIES[BATCH].simulate(STANDIN_BATCH, {"X": 0.2, "S": 50.0, "P": 0.0}, float(TIMES[-1]))
    Y = truth.sample(TIMES)
    t = np.asarray(out["series"]["t"])
    for state in ("X", "S", "P"):
        got = np.interp(TIMES, t, np.asarray(out["series"][state]))
        want = Y[kinetics.IX[state]]
        assert np.allclose(got, want, rtol=0.02, atol=0.05), (state, got, want)


# ── a batch simulation feeds a flowsheet's titre (finding 14) ──────────


def test_a_batch_simulation_of_ethanol_feeds_the_flowsheets_titre(store):
    ok = proforma.fit_info(artifacts.get(_batch()), ETHANOL)
    assert ok.refused is None and all(f.value is not None for f in ok.feeds)


# ── what a choice leaves unread waits for nothing (finding 16) ─────────


@pytest.mark.parametrize("profile, unread, read", [("constant", "mu_set", "feed_rate"), ("exponential", "feed_rate", "mu_set")])
def test_a_fed_batch_parameter_its_profile_does_not_read_is_not_waiting_in_the_panel(store, profile, unread, read):
    scope = fermos.family_scope("fedbatch_v1")
    res = params.resolve_scope(scope, ParamResolveRequest(overrides=typed("fedbatch_v1", feed_profile=profile)))
    assert unread not in res.waiting and read in res.waiting
    v = next(x for x in res.values if x.key == unread)
    assert v.origin == "not-read" and v.value is None and "waits for nothing" in v.detail
    # What Simulate binds says the same.
    b = fermos.bind(SimulationRequest(family="fedbatch_v1", product="ethanol", sugar="glucose",
                                      overrides=typed("fedbatch_v1", feed_profile=profile)))
    assert unread not in b.waiting and read in b.waiting


# ── the tool's summary says no parameter's value (finding 20) ──────────


def test_fermos_simulates_flags_say_a_value_out_of_bounds_by_its_key_and_end_at_a_full_stop(store):
    from test_fermos_bind import STANDIN, pool_of, rec

    # A STAND-IN yield above the physical limit of Yx/s: a gram of substrate
    # makes at most a gram of cells.
    pool = pool_of(*STANDIN, rec("yxs-hi", "biomass_yield_substrate", 3.75, "g g-1"))
    start = fermos.simulate(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                              overrides=typed(x0=0.2, p0=0.0, alpha=2.0, p_max=90.0)),
                            by_pool=pool).artifactId
    r = tools.run("fermos_simulate", {"family": BATCH, "product": "ethanol", "sugar": "glucose",
                                      "recordsByParam": {"yxs": ["yxs-hi"]}, "startFrom": f"simulation:{start}"},
                  _ctx(pool))
    assert r.error is None, r.error
    flags = r.summary["flags"]
    assert any(f.startswith("yxs lies outside its bounds") for f in flags), flags
    assert all("3.75" not in f for f in flags) and all(f.endswith(".") for f in flags), flags
    # The artifact keeps the whole words, the value with them.
    assert any("3.75" in f for f in artifacts.get(r.summary["artifactId"]).output["flags"])
    assert "3.75" not in json.dumps(r.summary["flags"])
