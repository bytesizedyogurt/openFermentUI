"""fermOS's fits (OF-BLD-014 §7.2). Every series here is SYNTHETIC, built in
the test from parameters chosen here; none is a measurement."""
from __future__ import annotations

import numpy as np
import pytest

from openferment_core import fermos, intake
from openferment_core.models import FermosPoint, FermosSeries

# The generating batch: chosen here, not measured.
TRUE = {"X0": 0.1, "mu": 0.35, "Xmax": 8.0, "P0": 0.05, "alpha": 0.4, "beta": 0.02, "S0": 60.0, "gamma": 4.5, "delta": 0.05}


def series(role, t, v, unit="g L-1"):
    return FermosSeries(measureId=f"m-{role}", label=role, unit=unit, role=role,
                        points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                for i, (a, b) in enumerate(zip(t, v))])


def batch(t, rng=None, sd=(0.0, 0.0, 0.0)):
    x, i = fermos.logistic(np.asarray(t, float), TRUE["X0"], TRUE["mu"], TRUE["Xmax"])
    p = TRUE["P0"] + TRUE["alpha"] * (x - TRUE["X0"]) + TRUE["beta"] * i
    s = TRUE["S0"] - TRUE["gamma"] * (x - TRUE["X0"]) - TRUE["delta"] * i
    if rng is not None:
        x = x + rng.normal(0, sd[0], len(t))
        p = p + rng.normal(0, sd[1], len(t))
        s = s + rng.normal(0, sd[2], len(t))
    return [series("biomass", t, x), series("product", t, p), series("substrate", t, s)]


# ── the growth fit ─────────────────────────────────────────────────────


def test_an_exponential_series_returns_its_growth_rate_within_one_percent():
    t = np.arange(0, 10, 1.0)
    g = fermos.growth_fit(series("biomass", t, 0.05 * np.exp(0.42 * t), "OD600"))
    assert g.mu.value == pytest.approx(0.42, rel=0.01) and g.mu.identified
    assert g.doublingTimeH == pytest.approx(np.log(2) / 0.42, rel=0.01) and g.unit == "OD600"


def test_a_flat_series_returns_no_fit_and_a_reason():
    g = fermos.growth_fit(series("biomass", np.arange(8.0), np.full(8, 1.5)))
    assert g.mu is None and "above zero" in g.reason


def test_a_series_with_a_lag_picks_the_exponential_window():
    t = np.arange(0, 14, 1.0)
    lag = 5.0
    x = np.where(t < lag, 0.1, 0.1 * np.exp(0.5 * (t - lag)))
    g = fermos.growth_fit(series("biomass", t, x))
    assert g.window[0] >= lag and g.mu.value == pytest.approx(0.5, rel=0.01)


def test_too_few_readings_is_said_in_words():
    g = fermos.growth_fit(series("biomass", [0, 1, 2], [0.1, 0.2, 0.4]))
    assert g.mu is None and "4 or more" in g.reason


# ── the kinetic fit ────────────────────────────────────────────────────


def test_a_noiseless_batch_returns_its_generating_parameters_within_a_tenth_of_a_percent():
    k = fermos.kinetic_fit(batch(np.linspace(0, 30, 16)))
    assert k.reason is None
    got = {p.name: p.value for p in k.params}
    for name, v in TRUE.items():
        assert got[name] == pytest.approx(v, rel=1e-3), name
    assert all(q.r2 > 0.999999 for q in k.quality)


def test_a_run_cut_off_before_biomass_levels_off_reports_a_wider_xmax_interval():
    widths_full, widths_cut = [], []
    for seed in range(9):
        rng = np.random.default_rng(seed)
        full = fermos.kinetic_fit(batch(np.linspace(0, 30, 16), rng, (0.12, 0.08, 0.6)))
        rng = np.random.default_rng(seed)
        cut = fermos.kinetic_fit(batch(np.linspace(0, 14, 16), rng, (0.12, 0.08, 0.6)))
        xf = fermos.param(full, "Xmax")
        xc = fermos.param(cut, "Xmax")
        widths_full.append(xf.high - xf.low)
        widths_cut.append(xc.high - xc.low)
        assert fermos.param(full, "mu").identified and xf.identified
    assert np.median(widths_cut) > 2 * np.median(widths_full)


def test_a_coefficient_the_run_cannot_tell_from_zero_is_marked():
    # A run that made no product: alpha and beta are zero, and the noisy
    # product series cannot tell them from it.
    rng = np.random.default_rng(3)
    t = np.linspace(0, 30, 16)
    runs = batch(t, rng, (0.05, 0.0, 0.5))
    runs[1] = series("product", t, 0.05 + rng.normal(0, 0.05, len(t)))
    k = fermos.kinetic_fit(runs)
    assert fermos.param(k, "alpha").indistinguishableFromZero and fermos.param(k, "beta").indistinguishableFromZero
    assert fermos.param(k, "gamma").indistinguishableFromZero is False, "the sugar was eaten"


def test_a_kinetic_fit_needs_five_biomass_readings():
    k = fermos.kinetic_fit([series("biomass", [0, 1, 2, 3], [0.1, 0.2, 0.4, 0.8])])
    assert not k.params and "5 or more" in k.reason


def test_units_are_built_from_the_measures_own():
    runs = batch(np.linspace(0, 30, 12))
    runs[0] = runs[0].model_copy(update={"unit": "OD600"})
    k = fermos.kinetic_fit(runs)
    units = {p.name: p.unit for p in k.params}
    assert units["Xmax"] == "OD600" and units["alpha"] == "g L-1 per OD600" and units["delta"] == "g L-1 per OD600 per h"


# ── the endpoint and the artifact ──────────────────────────────────────


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_a_fit_is_kept_with_the_deposition_as_its_source(store):
    from openferment_core import artifacts

    out = fermos.fit("dep-1", batch(np.linspace(0, 30, 10)))
    art = artifacts.get(out.kineticArtifactId)
    assert {i.source.kind for i in art.inputs} == {"deposition"} and {i.source.id for i in art.inputs} == {"dep-1"}
    assert art.provenance == "computed" and out.confirmedShare == 1.0
    assert artifacts.replay(out.kineticArtifactId).identical


def test_a_sample_run_is_kept_nowhere(store):
    out = fermos.fit("sample", batch(np.linspace(0, 30, 10)), sample=True)
    assert out.kineticArtifactId is None and out.sample
    assert not (store / "artifacts").exists() or not list((store / "artifacts").glob("*.json"))


def test_the_endpoint(store):
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    body = {"depositionId": "dep-2", "series": [s.model_dump(mode="json") for s in batch(np.linspace(0, 30, 10))]}
    r = c.post("/api/fermos/fit", json=body).json()
    assert r["growth"]["mu"]["identified"] and len(r["kinetic"]["params"]) == 9 and len(r["notes"]) == 2
    nobio = {"depositionId": "dep-3", "series": [body["series"][1]]}
    refused = c.post("/api/fermos/fit", json=nobio)
    assert refused.status_code == 422 and "biomass" in refused.json()["detail"]
    assert c.post("/api/fermos/fit", json=body, headers={"Origin": "https://evil.example"}).status_code == 403


# ── the forecast (§7.3) ────────────────────────────────────────────────

T = np.linspace(0, 30, 16)
SD = (0.15, 0.1, 0.8)


def test_a_fresh_reading_falls_inside_the_band_in_most_runs():
    # Forty seeded copies of one run with constant scatter: for each, fit,
    # forecast its own conditions, and draw a fresh reading at the final time.
    inside = {"biomass": 0, "product": 0, "substrate": 0}
    x, i = fermos.logistic(np.array([T[-1]]), TRUE["X0"], TRUE["mu"], TRUE["Xmax"])
    truth = {
        "biomass": float(x[0]),
        "product": float(TRUE["P0"] + TRUE["alpha"] * (x[0] - TRUE["X0"]) + TRUE["beta"] * i[0]),
        "substrate": float(TRUE["S0"] - TRUE["gamma"] * (x[0] - TRUE["X0"]) - TRUE["delta"] * i[0]),
    }
    for seed in range(40):
        rng = np.random.default_rng(1000 + seed)
        k = fermos.kinetic_fit(batch(T, rng, SD))
        out = fermos.forecast(k, seed=seed)
        fresh = {r: truth[r] + rng.normal(0, s) for r, s in zip(("biomass", "product", "substrate"), SD)}
        for f in out["finals"]:
            inside[f["role"]] += f["low"] <= fresh[f["role"]] <= f["high"]
    assert all(v >= 28 for v in inside.values()), inside


def test_the_same_seed_gives_the_same_band():
    k = fermos.kinetic_fit(batch(T, np.random.default_rng(5), SD))
    assert fermos.forecast(k, seed=7) == fermos.forecast(k, seed=7)
    assert fermos.forecast(k, seed=7) != fermos.forecast(k, seed=8)


def test_an_unidentified_xmax_is_refused_with_what_would_identify_it():
    k = fermos.kinetic_fit(batch(T))
    xmax = fermos.param(k, "Xmax")
    xmax.identified, xmax.low = False, -1.0
    with pytest.raises(fermos.FitRefused, match="Xmax is not identified.*continues until biomass levels off"):
        fermos.forecast(k)


def test_a_forecast_that_exhausts_its_substrate_ends_at_that_hour():
    k = fermos.kinetic_fit(batch(T, np.random.default_rng(2), SD))
    out = fermos.forecast(k, duration_h=200)
    assert out["substrateRunsOutH"] is not None and out["times"][-1] == pytest.approx(out["substrateRunsOutH"])
    sub = next(b for b in out["bands"] if b["role"] == "substrate")
    assert sub["median"][-1] <= 0 < sub["median"][-2]


def test_a_kept_forecast_is_computed_and_a_changed_start_makes_it_demo(store):
    fit = fermos.fit("dep-f", batch(T, np.random.default_rng(4), SD))
    kept = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
    assert kept.evidence.provenance == "computed" and kept.evidence.figure == "trajectory" and kept.artifactId
    assert kept.yieldInterval is not None and kept.yieldInterval.low < kept.yieldInterval.median < kept.yieldInterval.high
    with pytest.raises(fermos.FitRefused, match="needs the name"):
        fermos.forecast_run(fit_artifact=fit.kineticArtifactId, start=fermos.StartValues(S0=60.0))
    changed = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, start=fermos.StartValues(S0=60.0), changed_by="Sean Creighton")
    assert changed.evidence.provenance == "demo"


def test_the_sample_forecast_is_inline_and_kept_nowhere(store):
    k = fermos.kinetic_fit(batch(T, np.random.default_rng(6), SD))
    out = fermos.forecast_run(fit_inline=k, sample=True)
    assert out.artifactId is None and out.sample and out.evidence.provenance == "demo"
    assert not (store / "artifacts").exists() or not list((store / "artifacts").glob("*.json"))


def test_the_forecast_endpoint_and_the_tool(store):
    from fastapi.testclient import TestClient

    from openferment_core import api, tools

    fit = fermos.fit("dep-g", batch(T, np.random.default_rng(8), SD))
    c = TestClient(api.app, base_url="http://127.0.0.1")
    r = c.post("/api/fermos/forecast", json={"fitArtifactId": fit.kineticArtifactId})
    assert r.status_code == 200 and len(r.json()["bands"]) == 3 and len(r.json()["notes"]) == 2
    growth_id = fit.growthArtifactId
    wrong = c.post("/api/fermos/forecast", json={"fitArtifactId": growth_id})
    assert wrong.status_code == 422 and "not a kinetic fit" in wrong.json()["detail"]
    t = tools.run("growth_forecast", {"fitArtifactId": fit.kineticArtifactId})
    assert t.error is None and t.evidence[0].figure == "trajectory" and t.summary["evidenceId"] == t.evidence[0].id
