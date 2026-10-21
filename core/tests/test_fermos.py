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
    from types import SimpleNamespace

    from openferment_core import evidence_pool

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    # No record binds here: a simulation's parameters come from what each
    # test types (test_fermos_bind holds the binding from records).
    empty = SimpleNamespace(records=[], records_by_id={}, hidden={})
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: empty)
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


# ── OF-BLD-020 §3.1: a kinetics family fitted, and a simulation kept ───
#
# Every number below is a STAND-IN for a synthetic case, chosen here; none
# is a measurement or a result.

from openferment_core import artifacts, kinetics  # noqa: E402
from openferment_core.models import Override, SimulationRequest  # noqa: E402

BY = "openFerment test fixture"
BATCH = "batch_v1"
SCOPE = f"fermos:family:{BATCH}"
# What one batch_v1 fit can pin: its terms held as fermos.FIT_HELD holds them.
STANDIN_BATCH = dict(mu_max=0.40, ks=0.20, kd=0.0, yxs=0.15, alpha=2.0, beta=0.05, yps=0.45, maintenance=0.0,
                     p_max=None, n_inhibition=1.0, ki_substrate=None, yxo=None, mo=0.0)
STANDIN_BATCH_START = {"X": 0.2, "S": 50.0, "P": 0.0}
STANDIN_BATCH_TIMES = np.linspace(0.0, 12.0, 13)
# What a person types into the panel for a batch_v1 simulation.
STANDIN_TYPED = dict(mu_max=0.40, ks=0.20, yxs=0.15, alpha=2.0, yps=0.45, p_max=90.0, x0=0.2, s0=50.0, p0=0.0)
OUTPUT_KEYS = {"family", "title", "strain", "product", "sugar", "parameters", "start", "series", "units", "our", "end",
               "sugarRunsOutH", "harvestH", "finalTitre", "yieldAchieved", "productivity", "massBalance", "ceiling",
               "flags", "aerobic", "steadyState", "notes"}


def synthetic_batch(monkeypatch, roles=("biomass", "substrate", "product")):
    """A batch_v1 run made at a tight tolerance and read at thirteen hours."""
    with monkeypatch.context() as m:
        m.setattr(kinetics, "RTOL", 1e-12)
        m.setattr(kinetics, "ATOL", 1e-14)
        tr = kinetics.FAMILIES[BATCH].simulate(STANDIN_BATCH, STANDIN_BATCH_START, float(STANDIN_BATCH_TIMES[-1]))
    Y = tr.sample(STANDIN_BATCH_TIMES)
    state = {"biomass": "X", "substrate": "S", "product": "P"}
    return [series(role, STANDIN_BATCH_TIMES, Y[kinetics.IX[state[role]]]) for role in roles]


def typed(**values):
    return [Override(scope=SCOPE, key=k, value=v, by=BY, at="2026-10-21", note="a STAND-IN for a test")
            for k, v in values.items()]


def test_a_batch_v1_fit_recovers_its_parameters_and_is_kept_naming_its_model(store, monkeypatch):
    out = fermos.fit("dep-k", synthetic_batch(monkeypatch), family=BATCH)
    k = out.kinetic
    assert k.reason is None and k.model == BATCH
    got = {p.name: p for p in k.params}
    for name in ("mu_max", "ks", "yxs", "yps", "alpha", "beta"):
        assert got[name].value == pytest.approx(STANDIN_BATCH[name], rel=0.01), name
        assert got[name].identified, name
    assert got["ks"].unit == "g L⁻¹" and got["mu_max"].unit == "h⁻¹"
    art = artifacts.get(out.kineticArtifactId)
    assert art.tool == fermos.KINETIC and art.toolVersion == fermos.KINETIC_VERSION and art.output["model"] == BATCH
    held = {i.name: i for i in art.inputs if i.source.kind == "convention"}
    assert held["model"].value == BATCH and held["p_max"].value == "off" and held["kd"].value == 0
    assert art.provenance == "computed", "a fit takes only measurements and conventions (D1)"
    assert artifacts.replay(art.id).identical
    # A batch_v1 fit is simulated, not forecast.
    with pytest.raises(fermos.FitRefused, match="a forecast draws from a logistic_v0 fit"):
        fermos.forecast_run(fit_artifact=out.kineticArtifactId)


def test_a_product_and_substrate_only_batch_v1_fit_reports_mu_unidentified(store, monkeypatch):
    monkeypatch.setattr(kinetics, "FIT_MAX_NFEV", 20)
    out = fermos.fit("dep-ps", synthetic_batch(monkeypatch, ("substrate", "product")), family=BATCH)
    k = out.kinetic
    assert out.growth is None and out.growthArtifactId is None and k.model == BATCH and k.reason is None
    got = {p.name: p for p in k.params}
    # §3.R (findings 0, 8): the gauge X0 is the fit's, held and said so.
    assert got["mu_max"].identified is False and got["x0"].identified is False
    assert all(got[n].identified is False for n in fermos.SCALED_WITH_X)
    assert any("μmax is reported unidentified by rule" in n for n in k.notes)
    assert any("gauge" in n for n in k.notes)


def test_the_logistic_fit_is_unchanged_and_an_old_one_reads_as_logistic(store):
    out = fermos.fit("dep-l", batch(np.linspace(0, 30, 16)))
    assert out.kinetic.model == fermos.LOGISTIC and [p.name for p in out.kinetic.params] == list(TRUE)
    stored = artifacts.get(out.kineticArtifactId).output
    assert stored["model"] == fermos.LOGISTIC
    old = {k: v for k, v in stored.items() if k not in ("model", "notes")}
    assert fermos.KineticFit.model_validate(old).model == fermos.LOGISTIC
    with pytest.raises(fermos.FitRefused, match="'fedbatch_v1' is not one.*the feed"):
        fermos.fit("dep-l", batch(np.linspace(0, 30, 16)), family="fedbatch_v1")
    with pytest.raises(fermos.FitRefused, match="light_v1 is declared and not built"):
        fermos.fit("dep-l", batch(np.linspace(0, 30, 16)), family="light_v1")


def test_a_simulation_is_kept_with_every_parameter_and_override_named(store):
    r = fermos.simulate(SimulationRequest(family=BATCH, overrides=typed(**STANDIN_TYPED)))
    art = artifacts.get(r.artifactId)
    assert art.tool == fermos.SIMULATION and set(art.output) == OUTPUT_KEYS
    assert art.toolVersion == f"kinetics {BATCH} 1 · scipy {kinetics.versions()['scipy']}"
    # An override is a named person's assumption, so the simulation is demo.
    assert r.provenance == "demo" == art.provenance
    by_name = {i.name: i for i in art.inputs}
    for key in STANDIN_TYPED:
        assert by_name[key].source.kind == "assumption" and by_name[key].source.by == BY, key
    for key, word in (("kd", 0), ("beta", 0), ("ki_substrate", "off"), ("yxo", "anaerobic")):
        assert by_name[key].source.kind == "convention" and by_name[key].value == word, key
    assert by_name["solver"].value == "scipy solve_ivp, LSODA" and by_name["rtol"].value == kinetics.RTOL
    params_ = {p.key: p for p in r.parameters}
    assert params_["mu_max"].origin == "assumption" and params_["mu_max"].overriddenBy == BY
    assert params_["ki_substrate"].origin == "convention" and {p.key for p in r.start} == {"x0", "s0", "p0", "v0"}
    assert set(r.series) == {"t", "X", "S", "P"} and len(r.series["t"]) >= kinetics.POINTS
    assert r.units["X"] == "g L⁻¹" and r.our.unit == "g O2 L⁻¹ h⁻¹" and not r.aerobic and "anaerobic" in r.our.note
    assert r.sugarRunsOutH == r.harvestH == r.end["t"] and r.massBalance.ok and r.massBalance.closure < 1e-3
    assert r.finalTitre > 0 and 0 < r.yieldAchieved < STANDIN_TYPED["yps"]
    assert r.productivity == pytest.approx(r.finalTitre / r.harvestH)
    assert r.ceiling is None and r.flags == []
    # The same request again is the same artifact.
    assert fermos.simulate(SimulationRequest(family=BATCH, overrides=typed(**STANDIN_TYPED))).artifactId == r.artifactId
    assert artifacts.replay(r.artifactId).identical
    # OF-BLD-020 §6.2: the harvest is read from the kept series, its own hour a kept point.
    h = fermos.harvest(r.artifactId)
    assert h.hour == pytest.approx(r.harvestH) and h.exact and h.hourSource == fermos.HARVEST_HOUR
    assert {x.state: x.value for x in h.states}["P"] == pytest.approx(r.finalTitre)
    assert fermos.harvest(r.artifactId, 4.0).how == "an hour a person named"
    assert [s.artifactId for s in fermos.simulations()] == [r.artifactId]


def test_a_waiting_parameter_refuses_the_simulation_naming_it_and_its_field(store):
    with pytest.raises(fermos.SimulationRefused, match="batch_v1 cannot run yet") as e:
        fermos.simulate(SimulationRequest(family=BATCH, overrides=typed(**{k: v for k, v in STANDIN_TYPED.items()
                                                                           if k != "p_max"})))
    assert "p_max (maximum product concentration)" in str(e.value) and "ethanol_max_conc" in str(e.value)
    assert "mu_max" not in str(e.value)
    for req, words in (
        (SimulationRequest(family="light_v1"), "light_v1 is declared and not built"),
        (SimulationRequest(family="nowhere_v1"), "there is no model family 'nowhere_v1'"),
        (SimulationRequest(family=BATCH, fitArtifact="0123456789abcdef"), "there is no kept fit 0123456789abcdef"),
        (SimulationRequest(family=BATCH, startFrom="fit"), "names the fit"),
        (SimulationRequest(family=BATCH, durationPreset="fit-length"), "no fit is named"),
        (SimulationRequest(family=BATCH, startFrom="simulation:0123456789abcdef"), "no kept simulation"),
        (SimulationRequest(family=BATCH, startFrom="yesterday"), "starts from records, a fit"),
        (SimulationRequest(family=BATCH, overrides=typed(nothing=1.0)), "there is no parameter nothing"),
        (SimulationRequest(family=BATCH, overrides=[Override(scope="fermos:family:chemostat_v1", key="ks", value=1.0,
                                                             by=BY, at="2026-10-21")]), "an override names the scope"),
    ):
        with pytest.raises(fermos.SimulationRefused, match=words):
            fermos.simulate(req)
    assert not (store / "artifacts").exists() or not list((store / "artifacts").glob("*.json"))


def test_yps_is_set_beside_the_newest_stored_ceiling_and_flagged_above_it(store):
    from openferment_core import demo

    demo.standin_ceiling("Yeast9", "ethanol", "glucose", STANDIN_TYPED["yps"] * 0.9)
    req = SimulationRequest(family=BATCH, strain="s-cerevisiae-cenpk113-7d", product="ethanol", sugar="glucose",
                            overrides=typed(**STANDIN_TYPED))
    r = fermos.simulate(req)
    c = r.ceiling
    assert c is not None and c.strain == req.strain and c.flagged
    row = next(x for x in c.rows if x.modelId == "Yeast9")
    assert row.match == "species" and row.above and row.ypsGPerG == STANDIN_TYPED["yps"]
    assert row.ceilingGPerG == pytest.approx(STANDIN_TYPED["yps"] * 0.9)
    assert any("geneOS ceiling" in f for f in r.flags)
    # Read, never clamped: the parameter is the person's.
    assert next(p for p in r.parameters if p.key == "yps").value == STANDIN_TYPED["yps"]
    ceiling_inputs = [i for i in artifacts.get(r.artifactId).inputs if i.name.startswith("ceiling ")]
    assert {i.name for i in ceiling_inputs} == {"ceiling iMM904", "ceiling Yeast9"}
    assert {i.source.kind for i in ceiling_inputs} == {"artifact", "convention"}


def test_the_family_endpoints_and_the_simulation_endpoints(store):
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    listed = c.get("/api/fermos/families")
    assert listed.status_code == 200
    ids = [f["id"] for f in listed.json()]
    assert ids == ["batch_v1", "fedbatch_v1", "chemostat_v1", "light_v1"], "storage_v1 is archived with PHA"
    assert "storage_v1" in [f["id"] for f in c.get("/api/fermos/families?includeArchived=true").json()]
    one = c.get("/api/fermos/families/batch_v1").json()
    assert one["groups"][0] == "Growth" and "dX/dt = μ·X − kd·X" in one["equations"] and not one["socket"]
    assert c.get("/api/fermos/families/storage_v1").json()["program"] == "pha"
    missing = c.get("/api/fermos/families/nowhere_v1")
    assert missing.status_code == 404 and "there is no model family" in missing.json()["detail"]
    scope = c.get(f"/api/params/{SCOPE}")
    assert scope.status_code == 200 and scope.json()["kind"] == "fermos-family"
    assert "mu_max" in scope.json()["waiting"] and "kd" not in scope.json()["waiting"]
    body = {"family": BATCH, "overrides": [o.model_dump(mode="json") for o in typed(**STANDIN_TYPED)]}
    ok = c.post("/api/fermos/simulate", json=body)
    assert ok.status_code == 200 and ok.json()["provenance"] == "demo" and ok.json()["basis"]["tool"] == fermos.SIMULATION
    for bad, words in (({"family": BATCH}, "cannot run yet"), ({"family": "light_v1"}, "not built"),
                       ({**body, "overrides": body["overrides"][:1] + [{**body["overrides"][1], "value": "words"}]},
                        "takes a number")):
        r = c.post("/api/fermos/simulate", json=bad)
        assert r.status_code == 422 and words in r.json()["detail"], (bad, r.json())
    kept = c.get("/api/fermos/simulations").json()
    assert [k["artifactId"] for k in kept] == [ok.json()["artifactId"]] and kept[0]["provenance"] == "demo"
    assert c.post("/api/fermos/simulate", json=body, headers={"Origin": "https://evil.example"}).status_code == 403


# ── §3.R: a fit's gauge travels with it; a chemostat's steady state ────
#
# STAND-INs, chosen here: none is a measurement or a result.

CHEMO = "chemostat_v1"
# A person names a Pmax far above any titre these runs reach: the fit held
# Pmax off, and Pmax has no convention to fall back on.
STANDIN_PMAX_FAR = 1.0e6
STANDIN_CHEMOSTAT_TYPED = dict(mu_max=0.40, ks=0.20, yxs=0.15, alpha=2.0, yps=0.45, p_max=90.0, dilution_rate=0.1,
                               feed_conc=20.0, x0=0.5, s0=10.0, p0=0.0, t_end=400.0)
# The reviewer's Haldane case (test_kinetics' STANDIN_HALDANE): μ(Sf) − kd
# under D, μ's peak above it.
STANDIN_HALDANE_TYPED = dict(mu_max=0.5, ks=0.5, yxs=0.5, alpha=0.1, yps=0.45, p_max=90.0, ki_substrate=2.0,
                             dilution_rate=0.15, feed_conc=50.0, x0=20.0, s0=1.0, p0=0.0, t_end=400.0)
STANDIN_HALDANE_NEAR_WASHOUT = dict(x0=0.1, s0=50.0)


def typed_for(family, **values):
    return [Override(scope=f"fermos:family:{family}", key=k, value=v, by=BY, at="2026-10-21",
                     note="a STAND-IN for a test") for k, v in values.items()]


def test_a_gauged_fit_carries_its_x0_and_a_persons_x0_rescales_what_scales_with_it(store, monkeypatch):
    """§3.R findings 0 and 8: a batch_v1 fit of substrate and product alone
    held X0 at a gauge and kept no X0, so a simulation from it asked a person
    for X0 and integrated the gauge-scaled Yx/s, α and β with the person's:
    the sugar ran out at 11.88 h against the run's 7.92. The gauge is now the
    fit's X0 (identified false, said a gauge) and a convention in its basis;
    a simulation from the fit starts from it, and a person's X0 rescales
    Yx/s, α and β to its scale, named in each one's source. Finding 3: each
    flag says why its parameter is unidentified, never "the interval reaches
    zero" for a reason the interval contradicts."""
    readings = synthetic_batch(monkeypatch, ("substrate", "product"))
    out = fermos.fit("dep-gauge", readings, family=BATCH)
    fit_id = out.kineticArtifactId
    got = {p.name: p for p in out.kinetic.params}
    gauge = got["x0"]
    assert gauge.value == gauge.low == gauge.high == fermos.X0_GAUGE and gauge.identified is False
    assert gauge.unidentifiedBy == ["gauge"]
    assert all("gauge" in got[k].unidentifiedBy for k in fermos.SCALED_WITH_X)
    assert "rule" in got["mu_max"].unidentifiedBy and got["mu_max"].low > 0
    assert len(out.kinetic.covariance) == len(out.kinetic.params), "the covariance stays the params' own"
    held = {i.name: i for i in artifacts.get(fit_id).inputs if i.source.kind == "convention"}
    assert held["x0"].value == fermos.X0_GAUGE and "gauge" in held["x0"].source.note
    assert artifacts.replay(fit_id).identical

    truth = kinetics.FAMILIES[BATCH].simulate(STANDIN_BATCH, STANDIN_BATCH_START, None)

    def run(preset="until-sugar-runs-out", **over):
        return fermos.simulate(SimulationRequest(family=BATCH, fitArtifact=fit_id, startFrom="fit",
                                                 durationPreset=preset,
                                                 overrides=typed(p_max=STANDIN_PMAX_FAR, **over)))

    from_fit = run()
    x0 = {p.key: p for p in from_fit.start}["x0"]
    assert x0.origin == "fit" and x0.value == fermos.X0_GAUGE and "gauge" in x0.detail
    assert from_fit.sugarRunsOutH == pytest.approx(truth.runout_h, rel=0.01)
    person = run(x0=STANDIN_BATCH_START["X"])
    assert person.sugarRunsOutH == pytest.approx(truth.runout_h, rel=0.01), "the harvest hour was 50 % late"
    assert person.productivity == pytest.approx(from_fit.productivity, rel=1e-3)
    assert person.end["X"] == pytest.approx(float(truth.y_final[kinetics.IX["X"]]), rel=0.01)
    p = {v.key: v for v in person.parameters}
    c = STANDIN_BATCH_START["X"] / fermos.X0_GAUGE
    assert p["yxs"].value == pytest.approx(got["yxs"].value * c, rel=1e-12)
    for k in ("alpha", "beta"):
        assert p[k].value == pytest.approx(got[k].value / c, rel=1e-12), k
    for k in fermos.SCALED_WITH_X:
        assert p[k].origin == "fit" and "rescaled" in p[k].detail and "gauge" in p[k].detail, k
        assert p[k].source.id == fit_id
    # Finding 3: the flags say why, and never a reason the interval contradicts.
    flags = {f.split(" ", 1)[0]: f for f in person.flags if " is bound to fit " in f}
    assert "no biomass series" in flags["mu_max"] and "reaches zero" not in flags["mu_max"]
    assert "gauge" in flags["yxs"] and "reaches zero" not in flags["yxs"]
    assert "reaches zero" not in p["mu_max"].detail
    # The panel binds as the run does: a person's X0 in the resolve rescales the fit's Yx/s there too.
    from openferment_core import params
    from openferment_core.models import ParamResolveRequest

    panel = params.resolve_scope(SCOPE, ParamResolveRequest(fit=fit_id, startFrom="fit", overrides=typed(
        p_max=STANDIN_PMAX_FAR, x0=STANDIN_BATCH_START["X"])))
    shown = {v.key: v for v in panel.values}
    assert shown["yxs"].value == pytest.approx(p["yxs"].value, rel=1e-12) and "rescaled" in shown["yxs"].detail
    assert shown["x0"].origin == "assumption" and panel.waiting == []
    plain = {v.key: v for v in params.scope(SCOPE, ParamResolveRequest(fit=fit_id, startFrom="fit")).values}
    assert plain["x0"].origin == "fit" and plain["yxs"].value == pytest.approx(got["yxs"].value, rel=1e-12)
    # Finding 8: from the fit, with the fit's length, the run's own readings come back, whichever X0.
    last = {s.role: s.points[-1].value for s in readings}
    scatter = {q.role: q.scatter for q in out.kinetic.quality}
    for over in ({}, {"x0": STANDIN_BATCH_START["X"]}):
        r = run("fit-length", **over)
        for role, state in (("substrate", "S"), ("product", "P")):
            assert abs(r.end[state] - last[role]) <= 3 * scatter[role] + 1e-6, (over, role, r.end[state], last[role])


def test_a_chemostat_with_no_dilution_is_a_422_in_words(store):
    """§3.R finding 2: D = 0 answered 500 (NaN into brentq)."""
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    still = typed_for(CHEMO, **{**STANDIN_CHEMOSTAT_TYPED, "dilution_rate": 0.0})
    r = c.post("/api/fermos/simulate", json={"family": CHEMO, "overrides": [o.model_dump(mode="json") for o in still]})
    assert r.status_code == 422 and "dilution rate above zero" in r.json()["detail"], (r.status_code, r.text[:200])


def test_a_chemostats_steady_state_is_kept_with_its_values_and_a_haldane_culture_is_found(store):
    """§3.R findings 1 and 17: the steady state's X, S, P and D·P are the
    service's numbers, written into its words, and no note points at a
    productivity "above" that the card never shows; a Haldane μ that rises
    above D at low sugar holds a culture though μ(Sf) − kd is under D, and
    the result says washout is a second stable state and which one this run
    reached."""
    r = fermos.simulate(SimulationRequest(family=CHEMO, overrides=typed_for(CHEMO, **STANDIN_CHEMOSTAT_TYPED)))
    ss = r.steadyState
    assert ss is not None and ss.washout is False and ss.bistable is False and ss.reached == "culture"
    assert ss.productivity == pytest.approx(ss.dilutionRate * ss.P, rel=1e-12)
    for x in (ss.X, ss.S, ss.P, ss.productivity, ss.dilutionRate):
        assert f"{x:.4g}" in ss.words, (x, ss.words)
    assert not any("above" in n and "productivity" in n.lower() for n in r.notes), r.notes
    assert any("final titre over the run" in n for n in r.notes)
    h = fermos.simulate(SimulationRequest(family=CHEMO, overrides=typed_for(CHEMO, **STANDIN_HALDANE_TYPED)))
    hs = h.steadyState
    assert hs.washout is False and hs.bistable is True and hs.reached == "culture", hs
    assert hs.dWashout < hs.dilutionRate < hs.dWashoutMax and hs.X > 0 and hs.productivity > 0
    assert h.end["X"] == pytest.approx(hs.X, rel=1e-6) and "second stable state" in hs.words
    assert not any("wash out" in f for f in h.flags), h.flags
    w = fermos.simulate(SimulationRequest(family=CHEMO, overrides=typed_for(
        CHEMO, **{**STANDIN_HALDANE_TYPED, **STANDIN_HALDANE_NEAR_WASHOUT})))
    ws = w.steadyState
    assert ws.washout is False and ws.bistable is True and ws.reached == "washout" and w.end["X"] < 1e-6
    assert any("washed out" in f for f in w.flags), w.flags
    # Above μ's peak no culture holds: washout, and the words say μ − kd stays under D.
    gone = fermos.simulate(SimulationRequest(family=CHEMO, overrides=typed_for(
        CHEMO, **{**STANDIN_HALDANE_TYPED, "dilution_rate": 0.3})))
    assert gone.steadyState.washout is True and gone.steadyState.productivity is None
    assert any("wash out" in f for f in gone.flags)
