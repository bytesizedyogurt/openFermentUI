"""Engine runs in the real worker (engine/runs.py; execution prompt §7.4,
§9.1 step 5; ADR-004, ADR-006; the stage 4 gate).

Marked `sim`. openFerment's cellulosic ethanol flowsheet run with the
library's own defaults is kept with every input a `library-default` or a
stated convention and the SFF file it wrote, valid, scored and carrying its
recipe; one with a person's assumption and a model's estimate runs and is
`assumed`, its basis naming the person and the model; a run replays within
the precision its basis states, a scenario flowsheet's at a small plant
identically, every fixed sample priced as its base case; AFEX's infeasible
region is kept as a receipt naming its unit.
"""
from __future__ import annotations

import pytest

from openferment_core import artifacts, llm, proforma
from openferment_core.engine import library, registry, runs
from openferment_core.models import InputAssumption, Override
from openferment_core.workers import SimWorker
from standins import assumed_inputs

pytestmark = pytest.mark.sim

FLOWSHEET = "cellulosic_ethanol_v0"
# A scenario flowsheet the biosteam engine runs beside the library's plants (alpha 2.2 D6).
SCENARIO = "ethanol_glucose_v0"
# The model the service calls first: the one whose estimates these are.
MODEL = llm.DEFAULT_PRIMARY


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()


def test_the_flowsheet_on_library_defaults_is_kept_with_its_sff_file(warm):
    rep = runs.run(FLOWSHEET, by="Ada Moreno")
    run = rep.run
    assert run.status == "done" and run.configuration == "dilute acid, IB" and run.provenance != "assumed"
    assert {i.quantity.origin.kind for i in run.inputs} <= {"library-default", "convention"}
    assert run.versions["biosteam"] == "2.54.0" and run.versions["biorefineries"] == "2.35.1"
    assert run.outputs["outputs"]["mespUsdPerKg"] == rep.artifact.output["outputs"]["mespUsdPerKg"] > 0
    # D3: its outputs.values, each a quantity in the unit the artifact states, its origin the artifact.
    values = {v["name"]: v["quantity"] for v in run.outputs["values"]}
    art = rep.artifact.output
    assert values["outputs.mespUsdPerKg"] == {"value": art["outputs"]["mespUsdPerKg"],
                                              "unit": art["outputUnits"]["mespUsdPerKg"],
                                              "origin": {"kind": "artifact", "ref": run.artifactId}}
    assert values["price.solvedPrice"]["value"] == art["price"]["solvedPrice"]
    assert values["price.solvedPrice"]["unit"] == art["price"]["units"]["solvedPrice"]
    assert run.sff.valid and run.sff.score > 0.5 and rep.flowsheet.completeness.recipe["digests_valid"]
    assert runs.listed()[0] == run and runs.report(run.id).run == run


def test_a_scenario_with_a_persons_assumption_and_a_models_estimate_runs_and_is_assumed(warm):
    """§9.1 step 5: one person-assumption and one model-estimate."""
    scope = library.scope(FLOWSHEET, None)
    values = [Override(scope=scope, key="stream.cornstover.price", value=0.08, by="Ada Moreno", at="2026-10-30"),
              Override(scope=scope, key="unit.R303.tau_cofermentation", value=48.0, by=MODEL, at="2026-10-30T12:00:00Z",
                       origin="model-estimate", note="a co-fermentation of two days, as such plants are often run")]
    rep = runs.run(FLOWSHEET, None, values, by="Ada Moreno")
    assert rep.run.status == "done" and rep.run.provenance == rep.artifact.provenance == "assumed"
    origins = {i.name: i.quantity.origin for i in rep.run.inputs}
    assert (origins["stream.cornstover.price"].kind, origins["stream.cornstover.price"].by) == (
        "person-assumption", "Ada Moreno")
    assert (origins["unit.R303.tau_cofermentation"].kind, origins["unit.R303.tau_cofermentation"].by) == (
        "model-estimate", MODEL)
    base = runs.run(FLOWSHEET, by="Ada Moreno").run.outputs["outputs"]["mespUsdPerKg"]
    assert rep.run.outputs["outputs"]["mespUsdPerKg"] != base and rep.run.sff.valid


def test_a_run_replays_within_the_precision_its_basis_states(warm, monkeypatch):
    run = runs.run(FLOWSHEET, by="Ada Moreno").run
    replayed = artifacts.replay(run.artifactId)
    assert replayed.withinTolerance, replayed.differences[:5]
    assert replayed.tolerance.rtol == pytest.approx(1e-9)

    # H1-04: a scenario flowsheet's run at a plant of 1000 t/yr, where the sieves' whole recycle (about one kmol an
    # hour) sits inside BioSTEAM's default recycle tolerance. Every input is test_proforma's STAND-IN at that scale,
    # held fixed, so every sample and the grid's one cell take the base case's inputs. The run and its replay go to
    # a worker started for them alone: the run's base case is the first case of the plant that worker builds, as
    # after a service starts, and every sample, and the replay, a later case on the plant it holds.
    from test_proforma import ETHANOL_STANDIN

    biosteam = registry.get("biosteam")
    (thing,) = [t for t in biosteam.things() if t.id == SCENARIO]
    assert (thing.precision.rtol, thing.precision.atol) == (0.0, 0.0)
    small = {**ETHANOL_STANDIN, "plant_scale": 1000.0}
    inputs = assumed_inputs([InputAssumption(key=k, value=v, low=v, high=v, by="Ada Moreno", at="2026-10-30",
                                             note="a STAND-IN for a test") for k, v in small.items()], SCENARIO)
    own = SimWorker("openferment_core.workers.proforma_worker", timeout_s=proforma.CALL_TIMEOUT_S)
    monkeypatch.setattr(proforma, "call", own.call)
    try:
        scenario = biosteam.run(SCENARIO, None, inputs, "Ada Moreno")
        o = artifacts.get(scenario.artifactId).output
        assert o["feasible"] == o["samples"] > 0 and o["baseInfeasible"] is None
        # Each sample and the grid's cell price as the base case does.
        assert set(o["quantiles"].values()) == {o["basePrice"]}, (o["basePrice"], o["quantiles"])
        assert set(o["grid"]["msp"]) == {o["basePrice"]}, (o["basePrice"], o["grid"]["msp"])
        # Its replay on the plant the worker now holds is identical, as rtol 0, atol 0 asks.
        again = artifacts.replay(scenario.artifactId)
        assert again.identical and again.withinTolerance, again.differences[:5]
    finally:
        own.close()


def test_an_infeasible_configuration_is_kept_as_a_receipt_naming_its_unit(warm):
    with pytest.raises(library.LibraryRefused, match="InfeasibleRegion"):
        runs.run(FLOWSHEET, "AFEX, IB", by="Ada Moreno")
    receipt = next(r for r in runs.listed() if r.configuration == "AFEX, IB")
    assert receipt.status == "refused" and "M207" in receipt.refused and receipt.artifactId is None
