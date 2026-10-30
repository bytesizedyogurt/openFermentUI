"""The library plant runner (ADR-004; execution prompt §8.4), offline.

The shelf is the committed discovery (engine/library_shelf.json); the
package's own test is read from the installed file by `ast` (nothing is
imported); the worker is a STAND-IN that answers `library_parameters` and
`library_run` in the worker's shape. Discovery, builds and runs in the real
worker are the `sim` tests in test_library_sim.py.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core.api import app
from openferment_core.engine import library, sff, simulator
from openferment_core.models import Artifact, LibraryShelf, Override
from openferment_core.workers import WorkerError

# The plants the execution prompt (§4.4) names, and the two it names that
# the installed package offers as subsystem factories alone.
NAMED_PLANTS = {"cornstover", "corn", "sugarcane", "lipidcane", "oilcane", "cane", "cellulosic", "lactic", "LAOs",
                "fattyalcohols", "gas_fermentation", "milk"}
NAMED_SUBSYSTEMS = {"ethanol", "biodiesel"}


def over(key: str, value, scope: str = "library:sugarcane", **kw) -> Override:
    return Override(scope=scope, key=key, value=value, by=kw.pop("by", "A. Reader"), at="2026-10-30", **kw)


# ── the shelf ──────────────────────────────────────────────────────────


def test_the_shelf_holds_every_subpackage_discovery_found_and_says_what_each_is():
    s = library.shelf()
    kinds = {p.id: p.kind for p in s.plants}
    assert NAMED_PLANTS <= {i for i, k in kinds.items() if k == "plant"}
    assert NAMED_SUBSYSTEMS <= {i for i, k in kinds.items() if k == "subsystems"}
    assert s.package == "biorefineries 2.35.1" and s.simulator == "biosteam 2.54.0"
    assert LibraryShelf.model_validate(json.loads(library.SHELF_FILE.read_text(encoding="utf-8"))) == s


def test_each_plant_says_whether_each_configuration_built_and_why_not():
    s = {p.id: p for p in library.shelf().plants}
    assert [b.configuration for b in s["oilcane"].builds] == s["oilcane"].configurations and len(s["oilcane"].builds) == 13
    assert all(b.ok and b.priced and b.units for b in s["oilcane"].builds)
    [laos] = s["LAOs"].builds
    assert not laos.ok and "could not be built under biosteam 2.54.0" in laos.error
    for p in s.values():
        if p.kind == "plant":
            assert p.builds, p.id


def test_a_plant_names_its_configurations_where_the_package_does():
    oilcane, cane = library.plant("oilcane"), library.plant("cane")
    assert oilcane.requiresConfiguration and "S1" in oilcane.configurations and "O1*" in oilcane.configurations
    assert oilcane.configurationsFrom == "biorefineries/tests/test_biorefineries.py, configurations"
    assert cane.configurationsFrom == "biorefineries.cane.evaluation.configuration_names"
    assert library.plant("cellulosic").scenario[0].name == "feedstock"


def test_the_change_corn_needs_to_build_here_is_on_the_shelf_with_its_reason():
    [c] = library.plant("corn").compat
    assert "two inlets" in c.change and "biosteam 2.54.0" in c.why


# ── the package's own test ─────────────────────────────────────────────


def test_a_plants_test_is_named_as_the_packages_code_generator_names_it():
    assert library.package_test("sugarcane", None) == "test_sugarcane"
    assert library.package_test("oilcane", "S1*") == "test_oilcane_S1_agile"
    assert library.package_test("cane", "S1") is None, "cane's configurations have no test of their own"


def test_the_regression_is_read_from_the_installed_test_file():
    reg = library.regression("sugarcane", None)
    assert reg is not None and reg.test == "test_sugarcane" and reg.file == library.TEST_FILE
    assert [v.expression for v in reg.values][:3] == ["tea.IRR", "feedstock.price", "product.price"]
    assert all(v.rtol == 0.05 for v in reg.values) and len(reg.values) == 11
    assert library.regression("cellulosic", None) is None


def test_a_check_holds_as_numpy_allclose_holds_it():
    reg = library.regression("sugarcane", None)
    measured = {v.expression: v.package * 1.04 for v in reg.values}
    assert all(c.within for c in library.checks(reg, measured))
    measured["tea.sales"] = reg.values[3].package * 1.2
    [bad] = [c for c in library.checks(reg, measured) if not c.within]
    assert bad.expression == "tea.sales" and bad.relDiff == pytest.approx(0.2)


# ── what a run can build ────────────────────────────────────────────────


@pytest.mark.parametrize("plant, configuration, said", [
    ("ethanol", None, "subsystem factories alone"),
    ("oilcane", None, "built in one of its configurations"),
    ("oilcane", "Z9", "names no configuration 'Z9'"),
    ("sugarcane", "S1", "built in one configuration, its own"),
])
def test_a_run_the_shelf_cannot_build_is_refused_in_words(plant, configuration, said):
    with pytest.raises(library.LibraryRefused, match=said):
        library.run_inputs(plant, configuration, [])


def test_a_plant_not_on_the_shelf_is_not_found():
    with pytest.raises(library.PlantNotFound):
        library.run_inputs("nosuchplant", None, [])


def test_bounds_are_conventions_each_with_its_reason():
    assert library._bounds("unit.R301.T", "K", "number")[:2] == (0.0, None)
    assert library._bounds("tea.operating_days", "d/yr", "number")[:2] == (0.0, 365.0)
    assert library._bounds("tea.income_tax", "", "number")[:2] == (0.0, 1.0)
    low, high, why = library._bounds("stream.sugarcane.price", "USD/kg", "number")
    assert (low, high) == (None, None) and "below zero" in why
    assert all(library._bounds(k, u, kind)[2] for k, u, kind in
               [("unit.X.thing", "", "number"), ("unit.X.material", "", "text")])


# ── with the worker stood in ────────────────────────────────────────────

SUGARCANE_PARAMETERS = [
    {"key": "stream.sugarcane.F_mass", "label": "sugarcane: flow", "group": "feedstock", "unit": "kg/hr",
     "value": 333334.2, "note": "the main feedstock's mass flow, as the package builds it", "kind": "number"},
    {"key": "stream.sugarcane.price", "label": "sugarcane: price", "group": "prices", "unit": "USD/kg",
     "value": 0.03455, "note": "the feedstock's price as the package sets it", "kind": "number"},
    {"key": "unit.T202.vessel_type", "label": "T202: vessel_type", "group": "unit T202", "unit": "",
     "value": "Field erected", "note": "StorageTank.vessel_type, in words; read back, not set", "kind": "text"},
]


class StandInWorker:
    """A STAND-IN for the Proforma worker's library ops: the worker's shapes,
    the sugarcane plant's first parameters, and every op it was asked."""

    def __init__(self, refuse: str | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.refuse = refuse

    def __call__(self, op: str, args: dict):
        self.calls.append((op, args))
        if self.refuse:
            raise WorkerError(f"Refused: {self.refuse}")
        if op == "library_parameters":
            return {"plant": args["plant"], "configuration": args["configuration"], "parameters": SUGARCANE_PARAMETERS,
                    "found": {"product": "the package test's name for it, sugarcane.ethanol"},
                    "simulator": "biosteam 2.54.0", "package": "biorefineries 2.35.1"}
        if op == "library_run":
            reg = library.regression("sugarcane", None)
            return {"plant": args["plant"], "configuration": args["configuration"], "price": {"priced": True},
                    "measured": {v.expression: v.package for v in reg.values}, "parameters": SUGARCANE_PARAMETERS,
                    "overrides": args["overrides"]}
        raise AssertionError(f"the stand-in has no op {op}")


@pytest.fixture
def worker(monkeypatch):
    stand_in = StandInWorker()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def test_parameters_are_read_back_as_library_defaults_and_kept_for_the_installed_versions(worker):
    got = library.parameters("sugarcane")
    assert got.scope == "library:sugarcane" and [s.key for s in got.specs] == [p["key"] for p in SUGARCANE_PARAMETERS]
    assert all(v.origin == "library-default" and v.libraryDefault == v.value for v in got.values)
    assert all(s.sourceRule == ["library-default"] and s.boundsReason for s in got.specs)
    flow = next(s for s in got.specs if s.key == "stream.sugarcane.F_mass")
    assert (flow.min, flow.dimension) == (0.0, "massFlow")
    assert got.values[0].source.kind == "model" and got.values[0].source.id == "biorefineries.sugarcane@2.35.1"
    library.parameters("sugarcane")
    assert [op for op, _ in worker.calls] == ["library_parameters"], "read once for the installed versions"


def test_a_runs_basis_names_the_plant_the_settings_each_change_and_each_persons_value(worker):
    inputs = library.run_inputs("sugarcane", None, [over("stream.sugarcane.price", 0.05, note="a quote")])
    named = {i.name: i for i in inputs}
    assert named["plant"].value == "sugarcane" and named["plant"].source.kind == "model"
    assert named["simulator"].value == "biosteam 2.54.0" and named["precision"].value == "10 significant digits"
    price = named["stream.sugarcane.price"]
    assert (price.value, price.unit, price.source.kind, price.source.by) == (0.05, "USD/kg", "assumption", "A. Reader")
    assert price.source.note == "typed on 2026-10-30: a quote"
    corn = {i.name: i for i in library.run_inputs("corn", None, [])}
    assert corn["compatibility"].source.kind == "convention" and "two inlets" in corn["compatibility"].value


@pytest.mark.parametrize("overrides, said", [
    ([over("stream.sugarcane.price", 0.05, scope="library:corn")], "names the scope it changes"),
    ([over("stream.sugarcane.price", 0.05), over("stream.sugarcane.price", 0.06)], "two overrides"),
    ([over("stream.sugarcane.price", 0.05, low=0.04, high=0.06)], "a range is a study's"),
    ([over("stream.sugarcane.price", "cheap")], "finite number"),
    ([over("unit.T999.T", 300.0)], "has no parameter unit.T999.T"),
])
def test_a_persons_values_are_refused_in_words_where_a_run_cannot_take_them(worker, overrides, said):
    with pytest.raises(library.LibraryRefused, match=said):
        library.run_inputs("sugarcane", None, overrides)


def test_a_run_with_no_value_of_its_own_is_held_to_the_packages_test(worker):
    out = library._run_library(library.run_inputs("sugarcane", None, []), None)
    assert out["regression"]["test"] == "test_sugarcane" and len(out["checks"]) == 11
    assert all(c["within"] for c in out["checks"])
    [(op, args)] = [c for c in worker.calls if c[0] == "library_run"]
    assert args == {"plant": "sugarcane", "configuration": None, "overrides": {}, "digits": 10}


def test_a_run_with_a_persons_value_is_not_held_to_the_packages_test(worker):
    out = library._run_library(library.run_inputs("sugarcane", None, [over("stream.sugarcane.price", 0.05)]), None)
    assert out["regression"] is None and out["checks"] == [] and "values of its own" in out["regressionNote"]
    [(_, args)] = [c for c in worker.calls if c[0] == "library_run"]
    assert args["overrides"] == {"stream.sugarcane.price": 0.05}


def test_the_workers_refusal_is_said_in_its_words(monkeypatch):
    monkeypatch.setattr(simulator, "call", StandInWorker(refuse="biorefineries.LAOs could not be built under biosteam"))
    with pytest.raises(library.LibraryRefused, match="^biorefineries.LAOs could not be built"):
        library._run_library(library.run_inputs("LAOs", None, []), None)


def test_a_library_run_is_exported_from_its_basis_alone(worker):
    inputs = library.run_inputs("sugarcane", None, [over("stream.sugarcane.price", 0.05)])
    art = Artifact(id="0123456789abcdef", tool=library.LIBRARY_RUN, toolVersion="v", inputs=inputs, output={},
                   outputHash="h", provenance="assumed", createdAt="2026-10-30T00:00:00Z", durationMs=0)
    assert library.plant_of(art) == {"library": "sugarcane", "flowsheet": "library:sugarcane", "configuration": None,
                                     "overrides": {"stream.sugarcane.price": 0.05}}
    with pytest.raises(library.LibraryRefused):
        library.plant_of(art.model_copy(update={"tool": "proforma.run"}))


def test_a_run_is_kept_and_assumed_when_it_rests_on_a_persons_value(worker):
    art = library.run("sugarcane", None, [over("stream.sugarcane.price", 0.05)])
    assert art.tool == library.LIBRARY_RUN and art.provenance == "assumed"
    plain = library.run("sugarcane")
    assert plain.provenance == "computed" and plain.id != art.id
    assert library.run("sugarcane").id == plain.id and len([c for c in worker.calls if c[0] == "library_run"]) == 2


# ── the routes ─────────────────────────────────────────────────────────


def test_the_routes_serve_the_shelf_the_regression_and_refuse_what_cannot_run(worker, monkeypatch):
    def unwritten(*a, **k):
        raise sff.SFFRefused("the stand-in writes no SFF file")

    monkeypatch.setattr(sff, "export", unwritten)  # test_runs.py runs the export with a stand-in toolkit
    client = TestClient(app)
    assert {p["id"] for p in client.get("/api/library").json()["plants"]} >= NAMED_PLANTS
    assert client.get("/api/library/sugarcane/regression").json()["test"] == "test_sugarcane"
    assert client.get("/api/library/cellulosic/regression").json() is None
    assert client.get("/api/library/nosuch/parameters").status_code == 404
    refused = client.post("/api/library/ethanol/run", json={})
    assert refused.status_code == 422 and "subsystem factories" in refused.json()["detail"]
    params = client.get("/api/library/sugarcane/parameters").json()
    assert params["values"][0]["origin"] == "library-default"
    ran = client.post("/api/library/sugarcane/run", json={"overrides": [over("stream.sugarcane.price", 0.05).model_dump()]})
    assert ran.status_code == 200 and ran.json()["artifact"]["tool"] == "library.run"
    assert ran.json()["run"]["provenance"] == "assumed" and ran.json()["run"]["sffRefused"] == "the stand-in writes no SFF file"


# ── openFerment's composed flowsheet, on the same shelf ─────────────────


def test_the_composed_flowsheet_is_on_the_shelf_with_its_configurations_and_recipe():
    entry = library.plant("cellulosic_ethanol_v0")
    assert (entry.kind, entry.composedFrom, entry.defaultConfiguration) == (
        "flowsheet", "biorefineries.cellulosic", "dilute acid, IB")
    assert entry.recipe == "openferment_core/flowsheets/recipes/cellulosic_ethanol_v0"
    assert len(entry.configurations) == 8 and entry.configurations[0] == "dilute acid, IB"
    built = {b.configuration: b.ok for b in entry.builds}
    assert built["dilute acid, IB"] and built["hot water, SCF"] and not built["AFEX, IB"] and not built["alkaline, SCF"]


def test_a_flowsheet_run_names_the_configuration_it_ran_and_what_it_is_composed_from(worker):
    named = {i.name: i for i in library.run_inputs("cellulosic_ethanol_v0", None, [])}
    assert named["configuration"].value == "dilute acid, IB"
    assert "(the package's own composition)" in named["configuration"].source.note
    assert named["plant"].source.id == "biorefineries.cellulosic@2.35.1"
    assert "composed by its recipe" in named["plant"].source.note


def test_the_flowsheets_unnamed_scope_sets_its_default_configuration_alone(worker, monkeypatch):
    monkeypatch.setattr(library, "parameters", lambda plant, configuration=None: SimpleParameters())
    unnamed = over("feed.moisture", 0.25, scope="library:cellulosic_ethanol_v0")
    inputs = library.run_inputs("cellulosic_ethanol_v0", None, [unnamed])
    assert {i.name for i in inputs if i.source.kind == "assumption"} == {"feed.moisture"}
    with pytest.raises(library.LibraryRefused, match="names the scope it changes"):
        library.run_inputs("cellulosic_ethanol_v0", "hot water, IB", [unnamed])


class SimpleParameters:
    """What `parameters` answers for the scope test: one spec, the moisture."""

    specs = [type("Spec", (), {"key": "feed.moisture", "unit": ""})()]
