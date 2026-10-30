"""The library plant runner (ADR-004; execution prompt §4.4, §8.4).

Every plant the installed `biorefineries` exposes is on the shelf, and so is
each of openFerment's own flowsheets composed from a package's factories
(kind `flowsheet`: `cellulosic_ethanol_v0`, run through the same adapter with
its configuration named in every basis). Discovery
(the Proforma worker's `library_discover`, workers/library_plants.py) reads
every subpackage without building it, then builds each plant in each
configuration the package names, and `library_shelf.json` holds what it
found. The shelf is regenerated, never edited:

    pnpm library:discover        python -m openferment_core.engine.library discover
    pnpm library:report          ... regression: docs/reports/library-regression.md and .json

and a `sim` test holds the committed file to what the installed package
exposes. A plant the pinned BioSTEAM cannot build stays on the shelf with
the package's own error.

A plant's parameters are read back from a fresh build (`parameters`): each a
`ParameterSpec` whose value is the library's default (origin
`library-default`), its bounds a convention with its reason. A run
(`run`) builds the plant afresh, sets a person's values (each an `Override`
of the plant's scope, a named assumption in the run's basis), simulates,
prices and reads it back, and is kept as one `library.run` artifact; a run
with no value of its own is held to the package's own test where the
package has one (`regression`, read from the installed test file by `ast`).
A run's SFF file is written by `plant_of` and engine/sff.py's `export`.

    GET  /api/library                                  the shelf
    GET  /api/library/{plant}/parameters?configuration=  its parameters, read back
    GET  /api/library/{plant}/regression?configuration=  the package test's values
    POST /api/library/{plant}/run                      one run, kept
"""
from __future__ import annotations

import json
import math
import sys
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from ..flowsheets import shelf as _shelf
from ..models import (
    BasisInput,
    BasisSource,
    LibraryParameters,
    LibraryPlant,
    LibraryShelf,
    Override,
    PackageRegression,
    ParameterSpec,
    ParameterValue,
    RegressionCheck,
)
from ..workers import WorkerError
from . import simulator

SHELF_FILE = Path(__file__).with_name("library_shelf.json")
TEST_FILE = "biorefineries/tests/test_biorefineries.py"
LIBRARY_RUN = "library.run"
LIBRARY_RUN_VERSION = "library run 1"
# The significant digits a run keeps (as a reference run keeps them): BioSTEAM
# sums a set of units in an order that moves the last digits from one build to
# the next, and a replay compares the plant. A precision, stated in every basis.
DIGITS = 10
# numpy.allclose's own absolute tolerance, which the package's test uses
# beside its rtol: a check holds when |measured − package| ≤ ATOL + rtol·|package|.
ALLCLOSE_ATOL = 1e-08


class LibraryRefused(ValueError):
    """The request cannot be computed, in words."""


class PlantNotFound(KeyError):
    pass


def _installed(dist: str) -> str:
    try:
        return version(dist)
    except PackageNotFoundError:
        return "not installed"


# ── the shelf ──────────────────────────────────────────────────────────


@cache
def shelf() -> LibraryShelf:
    """The shelf as discovery last wrote it."""
    return LibraryShelf.model_validate(json.loads(SHELF_FILE.read_text(encoding="utf-8")))


def plant(plant_id: str) -> LibraryPlant:
    for p in shelf().plants:
        if p.id == plant_id:
            return p
    raise PlantNotFound(f"the shelf has no {plant_id}; it has {', '.join(p.id for p in shelf().plants)}")


def _runnable(plant_id: str, configuration: str | None) -> LibraryPlant:
    """The plant, refused in words when it is not one a run can build: not
    a plant, a configuration it does not name, or none where it needs one."""
    p = plant(plant_id)
    if p.kind not in ("plant", "flowsheet"):
        said = {"subsystems": f"offers subsystem factories alone ({', '.join(p.factories)})",
                "none": "offers no plant", "unimportable": f"cannot be imported here: {p.error}"}[p.kind]
        raise LibraryRefused(f"{p.module} {said}")
    if configuration is None and p.requiresConfiguration:
        raise LibraryRefused(f"{p.module} is built in one of its configurations: {', '.join(p.configurations)}")
    if configuration is not None and configuration not in p.configurations:
        raise LibraryRefused(f"{p.module} names no configuration {configuration!r}"
                             + (f"; it names {', '.join(p.configurations)}" if p.configurations
                                else "; it is built in one configuration, its own"))
    return p


def scope(plant_id: str, configuration: str | None) -> str:
    """The parameter scope of a library plant (its configuration's)."""
    return f"library:{plant_id}" + (f":{configuration}" if configuration else "")


def discover(*, builds: bool = True) -> LibraryShelf:
    """Discovery, in the worker, and the build of each plant if asked."""
    found = simulator.call("library_discover", {"builds": builds})
    return LibraryShelf.model_validate(found)


def write_shelf(found: LibraryShelf) -> None:
    SHELF_FILE.write_text(json.dumps(found.model_dump(mode="json"), indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    shelf.cache_clear()


# ── the package's own test ─────────────────────────────────────────────


def package_test(plant_id: str, configuration: str | None) -> str | None:
    """The package test for a plant in a configuration, as the package's code
    generator names it (`test_<module><_configuration>`, a `*` spelled
    `_agile`), when the installed test file holds it."""
    tag = f"_{configuration}".replace("*", "_agile") if configuration else ""
    name = f"test_{plant_id}{tag}"
    return name if name in plant(plant_id).tests else None


def regression(plant_id: str, configuration: str | None) -> PackageRegression | None:
    """The values the package's own test for this plant asserts, read from
    the installed file; None when it has none."""
    name = package_test(plant_id, configuration)
    return _shelf.regression_of(TEST_FILE, name) if name else None


def checks(reg: PackageRegression, measured: dict[str, Any]) -> list[RegressionCheck]:
    """Each of the test's values beside what this installation computed, held
    as the test holds it (numpy.allclose with the test's rtol)."""
    out = []
    for v in reg.values:
        m = measured.get(v.expression)
        m = float(m) if isinstance(m, (int, float)) else None
        within = m is not None and abs(m - v.package) <= ALLCLOSE_ATOL + v.rtol * abs(v.package)
        rel = abs(m - v.package) / abs(v.package) if m is not None and v.package != 0 else None
        out.append(RegressionCheck(expression=v.expression, label=v.label, unit=v.unit, measured=m, package=v.package,
                                   rtol=v.rtol, relDiff=rel, within=within))
    return out


# ── parameters ─────────────────────────────────────────────────────────

SHARES = ("tea.income_tax", "tea.startup_FOCfrac", "tea.startup_VOCfrac", "tea.startup_salesfrac",
          "tea.finance_fraction", ".V_wf", ".efficiency", ".moisture_content", "_split")
DIMENSIONS = {"K": "temperature", "Pa": "pressure", "hr": "time", "yr": "time", "month": "time", "d/yr": "time",
              "kg/hr": "massFlow", "USD/kg": "price", "USD/kWh": "price", "USD/kmol": "price", "USD/kJ": "price",
              "m3": "volume", "kW/m3": "powerPerVolume", "kJ/hr": "duty", "kW": "power"}


def _bounds(key: str, unit: str, kind: str) -> tuple[float | None, float | None, str]:
    """A parameter's bounds, conventions each with its reason (D4)."""
    if kind == "text":
        return None, None, "read back in words, never set: BioSTEAM states no choices for it here"
    if unit == "K":
        return 0.0, None, "a temperature lies above absolute zero"
    if unit == "Pa":
        return 0.0, None, "an absolute pressure lies above a vacuum"
    if unit == "d/yr":
        return 0.0, 365.0, "a year holds 365 days"
    if unit in ("hr", "yr", "month"):
        return 0.0, None, "a time is not negative"
    if unit == "kg/hr":
        return 0.0, None, "a flow is not negative"
    if unit.startswith("USD/"):
        return None, None, "a price may lie below zero: a stream or utility the plant pays to send away is priced so"
    if any(key.endswith(s) or s in key for s in SHARES):
        return 0.0, 1.0, "a share lies between none and all"
    return None, None, "BioSTEAM states no bounds for this input, and none is set here"


def _spec(p: dict[str, Any]) -> ParameterSpec:
    low, high, why = _bounds(p["key"], p["unit"], p["kind"])
    return ParameterSpec(key=p["key"], label=p["label"], symbol="", gloss=p["note"],
                         dimension=DIMENSIONS.get(p["unit"], "words" if p["kind"] == "text" else "number"),
                         unit=p["unit"], min=low, max=high, group=p["group"], sourceRule=["library-default"],
                         note=p["note"], boundsReason=why)


def _value(p: dict[str, Any], source: BasisSource) -> ParameterValue:
    return ParameterValue(key=p["key"], value=p["value"], source=source, origin="library-default",
                          libraryDefault=p["value"], detail=p["note"])


_PARAMETERS: dict[tuple[str, str | None, str], LibraryParameters] = {}


def _refused(e: WorkerError) -> LibraryRefused:
    return LibraryRefused(str(e).removeprefix("Refused: "))


def parameters(plant_id: str, configuration: str | None = None) -> LibraryParameters:
    """A plant's parameters as the package builds it: read back from a fresh
    build in the worker, kept here for the installed versions."""
    entry = _runnable(plant_id, configuration)
    key = (plant_id, configuration, f"{_installed('biosteam')}/{_installed('biorefineries')}")
    if key not in _PARAMETERS:
        try:
            raw = simulator.call("library_parameters", {"plant": plant_id, "configuration": configuration})
        except WorkerError as e:
            if str(e).startswith("Refused: "):
                raise _refused(e) from None
            raise
        source = BasisSource(kind="model", id=f"{entry.module}@{_installed('biorefineries')}",
                             note="read back from the plant as the package builds it")
        _PARAMETERS[key] = LibraryParameters(
            plant=plant_id, configuration=configuration, scope=scope(plant_id, configuration), found=raw["found"],
            specs=[_spec(q) for q in raw["parameters"]], values=[_value(q, source) for q in raw["parameters"]],
            simulator=raw["simulator"], package=raw["package"])
    return _PARAMETERS[key]


# ── a run ──────────────────────────────────────────────────────────────


def _model(entry: LibraryPlant, note: str) -> BasisSource:
    """A plant's own source: the package's module, or for a composed
    flowsheet the package it is composed from, with the version installed."""
    return BasisSource(kind="model", id=f"{entry.composedFrom or entry.module}@{_installed('biorefineries')}", note=note)


def _override_input(o: Override, unit: str) -> BasisInput:
    if isinstance(o.value, bool) or not isinstance(o.value, (int, float)) or not math.isfinite(float(o.value)):
        raise LibraryRefused(f"the override of {o.key} takes a finite number")
    if (o.low is not None and o.low != o.value) or (o.high is not None and o.high != o.value):
        raise LibraryRefused(f"the override of {o.key} gives a range; a library run sets one value per parameter, "
                             "and a range is a study's to sample")
    if not o.by.strip():
        raise LibraryRefused(f"the override of {o.key} needs the name of the person who set it")
    note = f"typed on {o.at}" + (f": {o.note}" if o.note else "")
    return BasisInput(name=o.key, value=float(o.value), unit=unit,
                      source=BasisSource(kind="assumption", by=o.by.strip(), note=note))


def run_inputs(plant_id: str, configuration: str | None, overrides: list[Override]) -> list[BasisInput]:
    """A library run's basis: the plant and its configuration, the simulator,
    the settings it builds under, each change it needs to build here, each
    person's value, and the digits it keeps."""
    entry = _runnable(plant_id, configuration)
    if configuration is None and entry.kind == "flowsheet":
        configuration = entry.defaultConfiguration  # the basis names the configuration it ran
    want = scope(plant_id, configuration)
    # A composed flowsheet's default configuration is also its unnamed one:
    # the panel of `library:<flowsheet>` sets the plant a run of it builds.
    allowed = {want} | ({scope(plant_id, None)} if entry.kind == "flowsheet"
                        and configuration == entry.defaultConfiguration else set())
    stray = sorted({o.scope for o in overrides if o.scope not in allowed})
    if stray:
        raise LibraryRefused(f"an override names the scope it changes, and these were sent for {want}: {', '.join(stray)}")
    keys = [o.key for o in overrides]
    twice = sorted({k for k in keys if keys.count(k) > 1})
    if twice:
        raise LibraryRefused(f"two overrides of {', '.join(twice)}: one person's value a parameter")
    units = {s.key: s.unit for s in parameters(plant_id, configuration).specs} if overrides else {}
    unknown = sorted(k for k in keys if k not in units)
    if unknown:
        raise LibraryRefused(f"{entry.module} has no parameter {', '.join(unknown)}")
    bst_v, tmo_v = _installed("biosteam"), _installed("thermosteam")
    built_by = (f"openFerment's flowsheet {entry.module}, composed by its recipe ({entry.recipe}) from the package's "
                "factories, every number the package's" if entry.kind == "flowsheet" else
                f"{entry.title or entry.module}, built afresh through {entry.entry} with every setting the package's own")
    out = [BasisInput(name="plant", value=plant_id, unit="", source=_model(entry, built_by))]
    if configuration is not None:
        out.append(BasisInput(name="configuration", value=configuration, unit="", source=_model(
            entry, f"one of the configurations {entry.configurationsFrom} names"
                   + (" (the package's own composition)" if configuration == entry.defaultConfiguration else ""))))
    out += [
        BasisInput(name="simulator", value=f"biosteam {bst_v}", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{bst_v}", note="the process simulator the package runs on")),
        BasisInput(name="thermodynamics", value=f"thermosteam {tmo_v}", unit="", source=BasisSource(
            kind="model", id=f"thermosteam@{tmo_v}", note="BioSTEAM's property engine")),
        BasisInput(name="settings", value="bst.process_tools.default()", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{bst_v}",
            note="BioSTEAM's default utilities and plant cost index before the plant builds, as the package's own "
                 "test builds it; the plant then sets its own, and the worker puts back what it held before")),
    ]
    out += [BasisInput(name="compatibility", value=c.change, unit="", source=BasisSource(kind="convention", note=c.why))
            for c in entry.compat]
    out += [_override_input(o, units[o.key]) for o in overrides]
    out.append(BasisInput(name="precision", value=f"{DIGITS} significant digits", unit="", source=BasisSource(
        kind="convention", note="every number the run keeps is rounded so: BioSTEAM sums a set of units in an order "
                                "that moves the last digits from one build to the next, and a replay compares the plant")))
    return out


def _named(inputs: list[BasisInput], name: str) -> Any:
    return next((i.value for i in inputs if i.name == name), None)


def _overrides_of(inputs: list[BasisInput]) -> dict[str, float]:
    return {i.name: float(i.value) for i in inputs if i.source.kind == "assumption"}


def _run_library(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """One library run from its basis alone: the worker builds, sets, runs
    and reads the plant; a run with no value of its own is set beside the
    package's own test."""
    plant_id = str(_named(inputs, "plant"))
    configuration = _named(inputs, "configuration")
    configuration = str(configuration) if configuration is not None else None
    overrides = _overrides_of(inputs)
    digits = int(str(_named(inputs, "precision") or DIGITS).split()[0])
    try:
        out = simulator.call("library_run", {"plant": plant_id, "configuration": configuration,
                                             "overrides": overrides, "digits": digits})
    except WorkerError as e:
        if str(e).startswith("Refused: "):
            raise _refused(e) from None
        raise
    reg = regression(plant_id, configuration)
    if reg is not None and not overrides:
        out["regression"] = reg.model_dump(mode="json")
        out["checks"] = [c.model_dump(mode="json") for c in checks(reg, out.get("measured") or {})]
    else:
        out["regression"], out["checks"] = None, []
        out["regressionNote"] = ("the run sets values of its own, so the package's test does not hold it" if reg
                                 else "the package's test holds no values for this plant")
    return out


def _register() -> None:
    from .. import artifacts

    artifacts.register(LIBRARY_RUN, f"{LIBRARY_RUN_VERSION} · biosteam {_installed('biosteam')} · "
                                    f"biorefineries {_installed('biorefineries')}", _run_library)


def _register_lazy() -> None:
    from .. import artifacts

    artifacts.register_lazy(LIBRARY_RUN, _register)


_register_lazy()


def run(plant_id: str, configuration: str | None = None, overrides: list[Override] | None = None):
    """Run a library plant (or return the stored run of the same basis) and
    keep it as one `library.run` artifact."""
    from .. import artifacts

    return artifacts.compute(LIBRARY_RUN, run_inputs(plant_id, configuration, list(overrides or [])))


def plant_of(art) -> dict[str, Any]:
    """What the worker rebuilds a library run's plant from, for its SFF file
    (engine/sff.py `export`): the plant, its configuration and the person's values."""
    if art.tool != LIBRARY_RUN:
        raise LibraryRefused(f"{art.tool} is not a library run")
    configuration = _named(art.inputs, "configuration")
    return {"library": str(_named(art.inputs, "plant")), "flowsheet": f"library:{_named(art.inputs, 'plant')}",
            "configuration": str(configuration) if configuration is not None else None,
            "overrides": _overrides_of(art.inputs)}


# ── the command line ────────────────────────────────────────────────────

REPORT = Path(__file__).resolve().parents[3] / "docs" / "reports" / "library-regression"


def regression_report() -> tuple[str, dict[str, Any]]:
    """Every plant and configuration the package's test covers, run in the
    worker with the package's own settings and held to that test; the
    report as Markdown and as JSON. No run is kept."""
    rows = []
    for p in shelf().plants:
        if p.kind != "plant":
            continue
        for configuration in p.configurations or [None]:
            reg = regression(p.id, configuration)
            if reg is None:
                continue
            try:
                out = simulator.call("library_run", {"plant": p.id, "configuration": configuration, "overrides": {},
                                                     "digits": DIGITS})
            except WorkerError as e:
                rows.append({"plant": p.id, "configuration": configuration, "test": reg.test, "error": str(e)})
                continue
            held = checks(reg, out.get("measured") or {})
            rows.append({"plant": p.id, "configuration": configuration, "test": reg.test,
                         "within": sum(c.within for c in held), "of": len(held),
                         "outside": [{"expression": c.expression, "measured": c.measured, "package": c.package,
                                      "relDiff": c.relDiff, "rtol": c.rtol} for c in held if not c.within]})
    s = shelf()
    payload = {"package": s.package, "simulator": s.simulator, "thermosteam": s.thermosteam, "testFile": TEST_FILE,
               "rows": rows}
    lines = [
        "<!-- Written by `pnpm library:report` (core/openferment_core/engine/library.py); regenerate, do not edit. -->",
        "",
        "# Library plants against their package's own test",
        "",
        f"Every plant and configuration `{TEST_FILE}` covers, built afresh in the Proforma worker with the",
        f"package's own settings ({s.package}, {s.simulator}, {s.thermosteam}) and held to the test as the test",
        "holds it (`numpy.allclose` at its `rtol`). A value outside is listed with what this installation",
        "measured.",
        "",
        "| Plant | Configuration | Test | Within | Outside: measured against the test's value (relative difference) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['plant']} | {r['configuration'] or ''} | `{r['test']}` | not run | {r['error']} |")
            continue
        outside = "; ".join(
            f"`{o['expression']}` {o['measured']:.4g} against {o['package']:.4g} ({o['relDiff']:.1%})"
            if o["measured"] is not None and o["relDiff"] is not None else f"`{o['expression']}`"
            for o in r["outside"])
        lines.append(f"| {r['plant']} | {r['configuration'] or ''} | `{r['test']}` | {r['within']} of {r['of']} | "
                     f"{outside} |")
    return "\n".join(lines) + "\n", payload


def main(argv: list[str]) -> int:
    if argv == ["discover"]:
        simulator.start(background=False)
        found = discover(builds=True)
        write_shelf(found)
        plants = [p for p in found.plants if p.kind in ("plant", "flowsheet")]
        built = sum(1 for p in plants for b in p.builds if b.ok)
        tried = sum(len(p.builds) for p in plants)
        composed = sum(1 for p in plants if p.kind == "flowsheet")
        print(f"{SHELF_FILE.name}: {len(found.plants) - composed} subpackages of {found.package}, "
              f"{len(plants) - composed} plants, {composed} openFerment flowsheet(s); {built} of {tried} builds "
              f"succeed under {found.simulator}")
        for p in plants:
            for b in [b for b in p.builds if not b.ok]:
                print(f"  {p.id}{f' {b.configuration}' if b.configuration else ''}: {b.error}")
        return 0
    if argv == ["regression"]:
        simulator.start(background=False)
        markdown, payload = regression_report()
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.with_suffix(".md").write_text(markdown, encoding="utf-8")
        REPORT.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(markdown)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
