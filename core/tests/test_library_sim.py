"""The library plant runner in the real worker (ADR-004; the stage 4 gate).

Marked `sim`: the Proforma worker loads BioSTEAM. What the installed package
exposes is what the committed shelf says; library plants run and are held to
their package's own test as it holds on these versions (the corn stover plant
misses two of its eleven values, measured); an agile configuration runs and
says why it has no TEA breakdown; a person's value changes the solved price
and makes the run assumed; a run replays within its precision after another
plant ran between (A→B→A); a library run's SFF file validates and scores; a plant the
pinned BioSTEAM cannot build is refused with the package's own error.
"""
from __future__ import annotations

import pytest

from openferment_core import artifacts, proforma
from openferment_core.engine import library, sff
from openferment_core.models import Override

pytestmark = pytest.mark.sim

PROJECT = "test-project"


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()


def _read(shelf) -> list[dict]:
    return [p.model_dump(mode="json", exclude={"builds"}) for p in shelf.plants]


def test_the_committed_shelf_is_what_the_installed_package_exposes(warm):
    fresh = library.discover(builds=False)
    committed = library.shelf()
    assert (fresh.package, fresh.simulator, fresh.thermosteam) == (committed.package, committed.simulator,
                                                                    committed.thermosteam)
    assert _read(fresh) == _read(committed), "regenerate the shelf: pnpm library:discover"


# MEASURED 2026-10-30 (biosteam 2.54.0, biorefineries 2.35.1): what each
# plant's own package test holds here. The corn stover plant, the NREL
# cellulosic ethanol design, misses two of its eleven values, as its
# reference run has since 2026-10-20 (test_proforma_slow pins the same two);
# every miss is said in the run's checks, never hidden.
HOLDS = {
    ("corn", None): set(),
    ("sugarcane", None): set(),
    ("lipidcane", None): set(),
    ("cornstover", None): {"tea.installed_equipment_cost", "units.get_electricity_consumption()"},
    ("oilcane", "O2"): {"tea.utility_cost", "units.get_electricity_production()"},
}


@pytest.mark.parametrize("plant, configuration", sorted(HOLDS, key=str))
def test_a_library_plant_runs_and_its_packages_own_test_is_held_beside_it(warm, plant, configuration):
    art = library.run(plant, configuration)
    o = art.output
    assert art.provenance == "computed" and o["price"]["priced"] and o["price"]["solvedPrice"] > 0
    assert o["regression"]["test"] == library.package_test(plant, configuration) and len(o["checks"]) == 11
    outside = {c["expression"] for c in o["checks"] if not c["within"]}
    assert outside == HOLDS[(plant, configuration)], [c for c in o["checks"] if not c["within"]]
    assert o["streams"] and o["units"] and o["parameters"] and o["found"]["product"].startswith("the package test's")
    assert {"plant", "simulator", "settings", "precision"} <= {i.name for i in art.inputs}


def test_an_agile_configuration_runs_with_its_tables_and_says_why_it_has_no_tea_breakdown(warm):
    o = library.run("oilcane", "S2*").output
    assert all(c["within"] for c in o["checks"]) and o["streams"]
    assert o["tea"] is None and o["teaNote"].startswith("the TEA's breakdown could not be read from BioSTEAM")


def test_a_persons_value_changes_the_solved_price_and_makes_the_run_assumed(warm):
    base = library.run("sugarcane").output["price"]["solvedPrice"]
    o = Override(scope="library:sugarcane", key="stream.sugarcane.price", value=0.05, by="openFerment test",
                 at="2026-10-30", note="a higher cane price")
    art = library.run("sugarcane", None, [o])
    assert art.provenance == "assumed" and art.output["regression"] is None
    assert art.output["price"]["solvedPrice"] > base
    [p] = [p for p in art.output["parameters"] if p["key"] == "stream.sugarcane.price"]
    assert p["value"] == 0.05 and art.output["libraryDefaults"]["stream.sugarcane.price"] == pytest.approx(0.03455)


def test_a_run_replays_within_its_precision_after_another_plant_ran_between(warm):
    # Every build is fresh: a later one sets the package's own settings
    # again, so what differs is the solver's last digits, an NPV at the
    # solved price lying within the package test's atol of zero.
    a = library.run("cornstover")
    library.run("oilcane", "O1")
    replayed = artifacts.replay(a.id)
    assert replayed.withinTolerance, replayed.differences[:5]
    assert a.output["libraryDefaults"]["utility.CEPCI"] == pytest.approx(525.4), "the package's own cost index"


def test_the_flowsheet_replays_identical_after_a_plant_that_prices_its_own_process_water(warm):
    # Sugarcane's process settings price process water at 0.000254 USD/kg, and
    # BioSTEAM's default() leaves that for the next plant: the worker starts each
    # build from the stream prices BioSTEAM imports with (proforma_worker
    # DEFAULT_STREAM_PRICES), so the composed flowsheet pays its own price again.
    a = library.run("cellulosic_ethanol_v0")
    library.run("sugarcane")
    replayed = artifacts.replay(a.id)
    assert replayed.identical, replayed.differences[:5]


def test_the_parameters_read_back_are_the_library_defaults_a_run_starts_from(warm):
    got = library.parameters("cornstover")
    keys = {s.key for s in got.specs}
    assert {"stream.cornstover.F_mass", "stream.cornstover.price", "tea.IRR", "utility.CEPCI"} <= keys
    assert any(k.startswith("unit.") for k in keys)
    assert all(v.origin == "library-default" for v in got.values)
    ran = {p["key"]: p["value"] for p in library.run("cornstover").output["parameters"]}
    assert all(ran[v.key] == pytest.approx(v.value, rel=1e-9) for v in got.values if isinstance(v.value, float))


def test_a_library_runs_sff_file_validates_and_scores(warm):
    o = Override(scope="library:sugarcane", key="stream.sugarcane.price", value=0.05, by="openFerment test",
                 at="2026-10-30")
    art = library.run("sugarcane", None, [o])
    record = sff.export(library.plant_of(art), project_id=PROJECT, run_artifact_id=art.id, by="openFerment test")
    assert record.validation.valid, record.validation.findings
    assert 0.5 < record.completeness.score < 1 and record.origin == "run"
    [feed] = [f for f in record.graph.feeds if f.id == "sugarcane"]
    assert feed.price == pytest.approx(0.05), "the file is the plant the run set"


def test_a_plant_the_pinned_biosteam_cannot_build_is_refused_with_the_packages_error(warm):
    [laos] = library.plant("LAOs").builds
    with pytest.raises(library.LibraryRefused) as e:
        library.run("LAOs")
    assert str(e.value) == laos.error
