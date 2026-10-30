"""Engine runs in the real worker (engine/runs.py; execution prompt §7.4,
§9.1 step 5; ADR-004, ADR-006; the stage 4 gate).

Marked `sim`. openFerment's cellulosic ethanol flowsheet run with the
library's own defaults is kept with every input a `library-default` or a
stated convention and the SFF file it wrote, valid, scored and carrying its
recipe; one with a person's assumption and a model's estimate runs and is
`assumed`, its basis naming the person and the model; a run replays within
the precision its basis states; AFEX's infeasible region is kept as a
receipt naming its unit.
"""
from __future__ import annotations

import pytest

from openferment_core import artifacts, proforma
from openferment_core.engine import library, runs
from openferment_core.models import Override

pytestmark = pytest.mark.sim

FLOWSHEET = "cellulosic_ethanol_v0"
MODEL = "claude-opus-5-5"


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


def test_a_run_replays_within_the_precision_its_basis_states(warm):
    run = runs.run(FLOWSHEET, by="Ada Moreno").run
    replayed = artifacts.replay(run.artifactId)
    assert replayed.withinTolerance, replayed.differences[:5]
    assert replayed.tolerance.rtol == pytest.approx(1e-9)


def test_an_infeasible_configuration_is_kept_as_a_receipt_naming_its_unit(warm):
    with pytest.raises(library.LibraryRefused, match="InfeasibleRegion"):
        runs.run(FLOWSHEET, "AFEX, IB", by="Ada Moreno")
    receipt = next(r for r in runs.listed() if r.configuration == "AFEX, IB")
    assert receipt.status == "refused" and "M207" in receipt.refused and receipt.artifactId is None
