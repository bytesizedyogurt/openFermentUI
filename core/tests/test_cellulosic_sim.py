"""openFerment's cellulosic ethanol flowsheet in the real worker (ADR-004;
execution prompt §8.4; the stage 4 gate).

Marked `sim`. The package's own composition (dilute acid, IB) is the
package's plant, to the ten digits a run keeps; every configuration on the
shelf builds or is refused as the shelf says (AFEX's BioSTEAM InfeasibleRegion
a receipt naming its unit); SCF runs its saccharification and co-fermentation
in two batch reactors; the gates refuse a dry composition whose shares do not
sum to one and a reactant converted more than wholly; a person's composition
changes the price and makes the run assumed; a warm plant set B and back to A
returns A's answer (A→B→A); the run's SFF file validates with the recipe
embedded and its digests valid.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import proforma
from openferment_core.engine import library, sff
from openferment_core.models import Override

pytestmark = pytest.mark.sim

FLOWSHEET = "cellulosic_ethanol_v0"
PROJECT = "test-project"


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()


def over(key: str, value: float, configuration: str | None = None) -> Override:
    return Override(scope=library.scope(FLOWSHEET, configuration), key=key, value=value, by="openFerment test",
                    at="2026-10-30")


def test_the_packages_own_composition_is_the_packages_plant(warm):
    ours = library.run(FLOWSHEET).output
    package = library.run("cellulosic").output
    assert ours["configuration"] == "dilute acid, IB"
    assert ours["price"]["solvedPrice"] == pytest.approx(package["price"]["solvedPrice"], rel=1e-9)
    assert ours["outputs"]["mespUsdPerKg"] == pytest.approx(ours["price"]["solvedPrice"], rel=1e-9)
    assert len(ours["units"]) == len(package["units"])
    assert ours["readBack"]["organisms"] == [{"name": "Zymomonas mobilis", "label": "ethanologen"}]


def test_every_configuration_builds_or_is_refused_as_the_shelf_says(warm):
    entry = library.plant(FLOWSHEET)
    assert entry.kind == "flowsheet" and entry.composedFrom == "biorefineries.cellulosic"
    builds = {b.configuration: b for b in entry.builds}
    assert set(builds) == set(entry.configurations) and len(builds) == 8
    assert all(builds[f"{p}, {f}"].ok for p in ("dilute acid", "hot water") for f in ("IB", "SCF"))
    afex = builds["AFEX, IB"]
    assert not afex.ok and "InfeasibleRegion" in afex.error and "M207" in afex.error and "\x1b" not in afex.error
    with pytest.raises(library.LibraryRefused, match="InfeasibleRegion"):
        library.run(FLOWSHEET, "AFEX, IB")
    with pytest.raises(library.LibraryRefused, match="names no configuration"):
        library.run(FLOWSHEET, "dilute acid, SSCF")


def test_scf_saccharifies_and_cofements_in_two_batch_reactors(warm):
    back = library.run(FLOWSHEET, "dilute acid, SCF").output["readBack"]
    batch = [u for u in back["units"] if u["mode"] == "batch"]
    assert [u["class"] for u in batch] == ["Saccharification", "CoFermentation"]
    assert all(u["tau"] > 0 and u["reactionSets"] for u in batch)
    assert back["versions"]["biosteam"] == "2.54.0" and back["tea"]["IRR"] > 0


def test_the_gates_refuse_what_a_plant_cannot_hold_before_it_runs(warm):
    params = {s.key: v.value for s, v in zip(library.parameters(FLOWSHEET).specs, library.parameters(FLOWSHEET).values)}
    glucan = params["feed.dry.Glucan"]
    with pytest.raises(library.LibraryRefused, match="sum to 1.05; they sum to one"):
        library.run(FLOWSHEET, None, [over("feed.dry.Glucan", glucan + 0.05)])
    glucose = params["rxn.R201.reactions.0"]
    with pytest.raises(library.LibraryRefused, match="conversions of Glucan sum to"):
        library.run(FLOWSHEET, None, [over("rxn.R201.reactions.0", glucose + 0.95)])
    with pytest.raises(library.LibraryRefused, match="moisture"):
        library.run(FLOWSHEET, None, [over("feed.moisture", 1.0)])


def test_a_persons_composition_changes_the_price_and_makes_the_run_assumed(warm):
    params = {v.key: v.value for v in library.parameters(FLOWSHEET).values}
    base = library.run(FLOWSHEET).output["outputs"]["mespUsdPerKg"]
    shift = [over("feed.dry.Glucan", params["feed.dry.Glucan"] + 0.02),
             over("feed.dry.Xylan", params["feed.dry.Xylan"] - 0.02)]
    art = library.run(FLOWSHEET, None, shift)
    assert art.provenance == "demo" and art.output["outputs"]["mespUsdPerKg"] != base
    assert {i.name for i in art.inputs if i.source.kind == "assumption"} == {"feed.dry.Glucan", "feed.dry.Xylan"}


def test_a_warm_plant_set_b_and_back_to_a_returns_as_answer(warm):
    a, b, a_again = proforma.call("library_cases", {
        "plant": FLOWSHEET, "configuration": None, "digits": 17,
        "cases": [{}, {"stream.cornstover.price": 0.08, "unit.R303.tau_cofermentation": 48.0}, {}]})
    assert b["outputs"]["mespUsdPerKg"] != a["outputs"]["mespUsdPerKg"]
    assert a_again["outputs"] == a["outputs"] and a_again["price"] == a["price"], "A→B→A"


def test_the_runs_sff_file_validates_with_its_recipe_embedded(warm):
    art = library.run(FLOWSHEET)
    record = sff.export(library.plant_of(art), project_id=PROJECT, run_artifact_id=art.id, by="openFerment test")
    assert record.validation.valid, [f for f in record.validation.findings if f.status == "fail"]
    assert record.completeness.recipe["present"] and record.completeness.recipe["digests_valid"]
    held = json.loads(sff.document(record.id, project_id=PROJECT))
    rep = held["metadata"]["reproducibility"]
    assert rep["load_script"]["filename"] == "load.py" and rep["environment"]["filename"] == "environment.yaml"
    assert rep["simulator_package"]["name"] == "biosteam" and rep["flowsheet_model_package"]["name"] == "biorefineries"
    assert held["metadata"]["microorganisms"] == [{"name": "Zymomonas mobilis", "label": "ethanologen"}]
    assert held["metadata"]["process_title"].endswith(": dilute acid, IB")
