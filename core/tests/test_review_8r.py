"""The final review of OF-BLD-020's night one, fixed (§8.R).

A simulation fed to Proforma is called a simulation wherever it feeds it
(findings 0, 4, 5, 10, 11); a kept vessel design replays on a service just
started (1); the vessel says what it took a simulation's cells and product
to be, and refuses another organism (6, 13); Simulate and the panel refuse
what the run refuses, before it runs, by the run's own function (12, 14).

Every value a person "types" here is a STAND-IN chosen in the test and
every artifact a STAND-IN in its tool's shape; none is a measurement and no
number here is a result.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from openferment_core import artifacts, evidence_pool, fermos, intake, params, proforma, vessel
from openferment_core.models import (
    Artifact,
    BasisInput,
    BasisSource,
    Override,
    ParamResolveRequest,
    SimulationRequest,
)

BY = "openFerment test fixture"
AT = "2026-10-21"
STANDIN = "STAND-IN for this test"
BATCH = "batch_v1"
ETHANOL = proforma.ETHANOL
TYPED = dict(mu_max=0.4, ks=0.2, yxs=0.12, alpha=2.0, yps=0.45, p_max=90.0, x0=0.2, s0=50.0, p0=0.0)
EMPTY = SimpleNamespace(records=[], records_by_id={}, hidden={})
YEAST_STRAIN = "strain-yeast-test"
OTHER_STRAIN = "strain-ab12"
# A strain catalogue written for these tests (the service ships none, alpha
# 2.0 ADR-010): a yeast strain, and a strain of another, fictional species.
STRAIN_LABELS = {YEAST_STRAIN: "Saccharomyces cerevisiae TEST-1", OTHER_STRAIN: "Testus organismus AB12"}


def typed(scope=f"fermos:family:{BATCH}", **values):
    return [Override(scope=scope, key=k, value=v, by=BY, at=AT, note="a STAND-IN for a test") for k, v in values.items()]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(fermos, "_load_pool", lambda *a, **k: EMPTY)
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: EMPTY)
    return tmp_path


def simulate(product="ethanol", **over):
    return fermos.simulate(SimulationRequest(family=BATCH, product=product, sugar="glucose",
                                             overrides=typed(**{**TYPED, **over})), by_pool=EMPTY)


# ── findings 0, 4, 5, 10, 11: a simulation is called a simulation ───────


def test_a_simulation_fed_to_proforma_is_never_called_a_fit_or_a_forecast(store):
    # A run harvested at its end, its sugar not run out (D10: a time the person sets).
    sim = simulate(t_end=3.0)
    assert sim.sugarRunsOutH is None and sim.harvestH == pytest.approx(3.0)
    info = proforma.fit_info(artifacts.get(sim.artifactId), ETHANOL)
    assert info.batchTimeNote and sim.artifactId in info.batchTimeNote and "its run's end" in info.batchTimeNote
    assert "forecast" not in info.batchTimeNote and "median" not in info.batchTimeNote
    all3 = {"titre": sim.artifactId, "yield": sim.artifactId, "productivity": sim.artifactId}
    extra = proforma.apply_fits(proforma.bind_inputs(ETHANOL, [], None, None), all3, ETHANOL)
    batch = next(b for b in extra if b.name == "fit batch time")
    assert batch.source.note == info.batchTimeNote
    # The productivity refusal says what the simulation's productivity is.
    with pytest.raises(proforma.ScenarioRefused) as e:
        proforma.apply_fits(proforma.bind_inputs(ETHANOL, [], None, None), {"productivity": sim.artifactId}, ETHANOL)
    assert "median sugar" not in str(e.value) and "harvest hour" in str(e.value)
    # The panel serves each as a simulation, identified null (D2), never "fitted":
    # a scenario made here, on the ethanol flowsheet.
    scope = params.scope("proforma:sc-made-here", ParamResolveRequest(fits=all3, flowsheet=ETHANOL))
    for v in scope.values:
        if v.key in all3:
            assert v.origin == "simulation" and v.identified is None, v
    # The ceiling check names the simulation's achieved yield, not a fit's band.
    check = proforma.ceiling_check("sc-made-here", flowsheet=ETHANOL, pool=EMPTY, fits={"yield": sim.artifactId})
    assert check.yieldTool == fermos.SIMULATION
    assert "simulation" in check.yieldWords and "percentile" not in check.yieldWords and "Yp/s" not in check.yieldWords


def test_a_fit_and_a_forecast_keep_their_own_words(store):
    """A forecast's batch time stays the forecast's (the words moved, they
    did not change): FORECAST_BATCH_NOTE is what a forecast says."""
    assert "forecast's median sugar" in proforma.FORECAST_BATCH_NOTE
    assert "harvest hour of simulation abc" in proforma.simulation_batch_note("abc", "its run's end")


# ── finding 1: a vessel design replays on a service just started ───────


def test_the_vessel_tool_is_registered_when_the_service_starts():
    code = ("import sys\nfrom openferment_core import api, artifacts\n"
            "assert 'openferment_core.vessel' not in sys.modules, 'the service imports vessel at start'\n"
            "artifacts.registered('fermos.vessel')\nprint('registered')\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(Path(__file__).resolve().parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().endswith("registered")


# ── the stand-in simulations a vessel reads ─────────────────────────────


def _keep(aid: str, tool: str, output: dict, inputs: list[BasisInput]) -> Artifact:
    art = Artifact(id=aid, tool=tool, toolVersion=STANDIN, inputs=inputs, output=output,
                   outputHash=artifacts.output_hash(output), provenance="assumed", createdAt="2026-10-21T00:00:00Z",
                   durationMs=0, seed=None)
    from standins import plant_artifact

    return plant_artifact(art)


def _standin_sim(aid: str, strain: str | None, product: str | None = "ethanol") -> Artifact:
    from test_vessel import standin_simulation

    out = {**standin_simulation(False), "product": product, "strain": strain}
    inputs = [BasisInput(name="stand-in", value=STANDIN, unit="", source=BasisSource(kind="assumption", by=BY, note=STANDIN))]
    if strain:
        inputs.append(BasisInput(name="strain", value=strain, unit="", source=BasisSource(kind="convention", note=STANDIN)))
    return _keep(aid, vessel.SIMULATION, out, inputs)


# ── findings 6 and 13: the vessel says what it assumed ──────────────────


def test_the_vessel_refuses_another_organism_and_says_what_it_read_a_nameless_product_as(store, monkeypatch):
    monkeypatch.setattr(proforma, "_strain_labels", lambda: (STRAIN_LABELS, {"yeast": "saccharomyces cerevisiae"}))
    with pytest.raises(vessel.VesselRefused, match="not of the yeast program's organism"):
        vessel.simulation_inputs(_standin_sim("c0c0c0c0c0c0c0c1", OTHER_STRAIN))
    read = vessel.simulation_inputs(_standin_sim("c0c0c0c0c0c0c0c2", YEAST_STRAIN, product=None))
    assert [a["name"] for a in read["assumed"]] == ["product read as"]
    assert any("names no product" in n and "ethanol" in n for n in read["readNotes"])
    nameless = vessel.simulation_inputs(_standin_sim("c0c0c0c0c0c0c0c3", None))
    assert [a["name"] for a in nameless["assumed"]] == ["cells read as"]
    assert any("names no strain" in n for n in nameless["readNotes"])
    assert vessel.simulation_inputs(_standin_sim("c0c0c0c0c0c0c0c4", YEAST_STRAIN))["assumed"] == []


def test_a_design_names_what_it_read_a_nameless_product_as_in_its_basis(store, monkeypatch):
    from test_vessel import StandInWorker

    monkeypatch.setattr(proforma, "call", StandInWorker())
    monkeypatch.setattr(vessel, "_SPECS", {})
    sim = _standin_sim("c0c0c0c0c0c0c0c5", YEAST_STRAIN, product=None)
    from openferment_core.models import VesselRequest

    got = vessel.design(VesselRequest(simulation=sim.id, overrides=[
        Override(scope=f"fermos:vessel:{sim.id}", key="plant_scale", value=50000.0, by=BY, at=AT)]))
    basis = {i.name: i for i in artifacts.get(got.artifactId).inputs}
    assert basis["product read as"].value == "ethanol" and basis["product read as"].source.kind == "convention"
    assert any("names no product" in f for f in got.flags)


# ── findings 12 and 14: the panel and Simulate refuse what the run refuses ──


def _logistic_fit_with_negative_p0() -> str:
    """A logistic_v0 fit whose product starts a little below zero, as an
    unbounded least-squares fit lands a near-zero start on noisy readings:
    SYNTHETIC series, every number a STAND-IN."""
    import numpy as np

    from openferment_core.models import FermosPoint, FermosSeries

    def series(role, t, v):
        return FermosSeries(measureId=f"m-{role}", label=role, unit="g L-1", role=role,
                            points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                    for i, (a, b) in enumerate(zip(t, v))])

    t = np.linspace(0, 30, 16)
    x, i = fermos.logistic(t, 0.1, 0.35, 8.0)
    out = fermos.fit("dep-8r", [series("biomass", t, x), series("product", t, -0.0079 + 0.4 * (x - 0.1) + 0.02 * i),
                                series("substrate", t, 60.0 - 4.5 * (x - 0.1) - 0.05 * i)])
    return out.kineticArtifactId


def test_a_start_value_below_zero_holds_simulate_and_names_its_key_and_source(store):
    fit_id = _logistic_fit_with_negative_p0()
    req = SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", startFrom="fit", fitArtifact=fit_id,
                            overrides=typed(**{k: v for k, v in TYPED.items() if k not in ("x0", "s0", "p0")}))
    bound = fermos.bind(req, pool=EMPTY)
    assert bound.waiting == [] and bound.refused, bound
    assert "p0" in bound.refused and fit_id in bound.refused and "cannot be negative" in bound.refused
    with pytest.raises(fermos.SimulationRefused) as e:
        fermos.simulate(req, by_pool=EMPTY)
    assert str(e.value) == bound.refused


def test_the_family_panel_refuses_what_the_run_refuses(store):
    scope = f"fermos:family:{BATCH}"
    for key, value, words in (("yxs", 0.0, "yxs must be above zero"), ("mu_max", -1.0, "mu_max cannot be negative"),
                              ("x0", -1.0, "x0 is -1"), ("t_end", 0.0, "run length")):
        with pytest.raises(params.ParamRefused, match=words):
            params.resolve_scope(scope, ParamResolveRequest(product="ethanol", sugar="glucose",
                                                            overrides=typed(**{**TYPED, key: value})))
        got = fermos.bind(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose",
                                            overrides=typed(**{**TYPED, key: value})), pool=EMPTY)
        assert got.waiting == [] and got.refused and words in got.refused, (key, got.refused)
    ok = params.resolve_scope(scope, ParamResolveRequest(product="ethanol", sugar="glucose", overrides=typed(**TYPED)))
    assert ok.waiting == []
    assert fermos.bind(SimulationRequest(family=BATCH, product="ethanol", sugar="glucose", overrides=typed(**TYPED)),
                       pool=EMPTY).refused is None


def test_the_vessel_panel_refuses_n_beside_v_max_and_both_scales(store, monkeypatch):
    from test_vessel import ANAEROBIC_ID, StandInWorker, keep, standin_simulation

    monkeypatch.setattr(proforma, "call", StandInWorker())
    monkeypatch.setattr(vessel, "_SPECS", {})
    keep(ANAEROBIC_ID, standin_simulation(False))
    scope = f"fermos:vessel:{ANAEROBIC_ID}"

    def o(key, value):
        return Override(scope=scope, key=key, value=value, by=BY, at=AT)

    with pytest.raises(params.ParamRefused, match="give N or V_max, not both"):
        params.resolve_scope(scope, ParamResolveRequest(overrides=[o("plant_scale", 1000.0), o("N", 3.0),
                                                                   o("V_max", 500.0)]))
    with pytest.raises(params.ParamRefused, match="give plant_scale or batch_volume, not both"):
        params.resolve_scope(scope, ParamResolveRequest(overrides=[o("plant_scale", 1000.0), o("batch_volume", 50.0)]))
