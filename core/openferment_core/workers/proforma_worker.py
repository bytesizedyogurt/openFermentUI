"""The Proforma worker: BioSTEAM in a process of its own, kept warm
(OF-BLD-014 §8.1).

With flowsheets/, the only place in openferment_core that imports `biosteam`
(test_workers holds it to that). A cold import takes about forty seconds, so
the worker builds each flowsheet once and keeps it; every later request sets
its inputs on the built objects and re-simulates (Appendix 3, trap 3).

    ping        answered by `serve`
    benchmark   the published reference biorefinery (§8.2), built afresh
                inside `package_defaults()` (OF-BLD-019 §2.R)
    evaluate    one case of a flowsheet: its inputs in, its outputs out
    grid        the outputs over a grid of up to three inputs
    montecarlo  Latin hypercube samples of the inputs, seeded
    run         one whole run (OF-BLD-019 §2.1): the base case, the tables
                read from BioSTEAM's objects right after it (TEA breakdown,
                streams, units, utility duties, the diagram), the grid and
                the samples; proforma.py keeps it as one artifact (D1). A
                flowsheet built from a structure (OF-BLD-020 §6.1,
                `custom_train_v1`: a vessel design's fermenter, a train run's
                units and the TEA's finance) takes it as `structure`, and the
                worker keeps a built plant per structure (STRUCTURES_KEPT)
    reference   a published reference biorefinery run whole on its
                package's defaults (OF-BLD-019 §2.2): built afresh inside
                `package_defaults()`, as the package's own test builds it;
                its outputs, the quantities that test asserts, its defaults
                read back and every table; numbers rounded to the digits
                the basis states, so a replay compares the plant and not
                the order BioSTEAM sums a set of units in
    thermo_props  thermosteam's answer for one mixture (OF-BLD-019 §4.2, D9):
                a Stream on the library's own chemicals at T and P, and its
                density, heat capacity, viscosity, bubble and dew points;
                thermo.py keeps it as one artifact
    volatility  a chemical's volatility beside a partner (OF-BLD-020 §7.1,
                D12): each one's normal boiling point as the library holds
                it, and whether the library's own vapour-liquid equilibrium
                gives the pair a minimum-boiling azeotrope at its default
                pressure, by the preset's search; thermo.py keeps it as one
                `volatility` artifact
    vessel_specs  what fermOS's vessel class takes and its own defaults,
                read from BioSTEAM at import (OF-BLD-020 §4.1, E.3‴):
                `flowsheets/vessel.py`'s `specs`
    vessel_design one vessel designed for a simulation (OF-BLD-020 §4.1, D7):
                `AeratedBioreactor` or `NRELAnaerobicBatchBioreactor`, built
                afresh inside `package_defaults()`, its design, costs and the
                oxygen balance read; vessel.py keeps it as one artifact
    catalogue_specs  what one of pureOS's unit types takes and its class's
                own defaults, choices and refusals, read from its code at
                import on the yeast program's chemicals (OF-BLD-020 §5.1):
                `pureos/catalogue.py`'s `read_class`, handed the class
                (BioSTEAM's, or the in-house one) and the chemical IDs
    catalogue_unit_check  one unit of a type built alone on given inlets
                and values (catalogue keys), simulated, and read: its streams,
                design, costs and the attributes it holds (`build_unit`,
                `unit_report`); the catalogue's sim test runs every type so
    train_specs   what a train builds on (OF-BLD-020 §5.2): the yeast
                program's chemical IDs and thermosteam's Stream defaults
    flowsheet_unit_values  a shelf flowsheet's own units read by catalogue
                key, as its package builds them (a train's `readFrom`)
    train_run   one pureOS train built from its plain spec
                (`flowsheets/train.py`), simulated whole with its recycles,
                and read: stream, unit and utility tables, the diagram or
                the unit list, each unit's costs, the inlet as built

NO WORKER STOPS IN A DEBUGGER. BioSTEAM 2.54.0's AeratedBioreactor answers a
failure of its bubble-column correlation with a bare `breakpoint()`, which
would open pdb on this process's JSON channel and hang it. `SimWorker` starts
every worker with PYTHONBREAKPOINT=0, and this module also sets
`sys.breakpointhook` to raise in words, so the request fails and the worker
answers the next one.

THE WARM WORKER KEEPS NO PLANT'S SETTINGS (OF-BLD-019 §2.R). BioSTEAM keeps
process-wide state a plant can change: the utility prices and the plant cost
index, the stream and unit tickets that name what a package leaves unnamed,
and the chemicals thermosteam's `chemical_cache` keeps per package, whose
Chemical objects are shared by name between packages (the corn plant locks
ammonia to liquid in the object the corn stover plant uses). Every plant
therefore builds inside `package_defaults()`, as it would in a worker that
had built nothing before, and the worker puts back what it held afterwards;
a scenario flowsheet sets BioSTEAM's default utility prices and cost index
for every case it runs, and says so in its read-back.

The tables are read through BioSTEAM's own attributes and methods, never
recomputed: the TEA object's sales, material and utility cost, installed
equipment cost, FCI, TCI, FOC and IRR; each unit's costs, heat utilities and
power utility; the UnitGroup's duties in the units it states; and
`System.diagram` as SVG when Graphviz's `dot` is on the path (D8).

THERMOSTEAM ANSWERS, NEVER GUESSES (D9). A chemical is looked up in the
library by its name; one the library lacks, or cannot build, refuses the
whole question in words naming it. A property the library cannot compute for
this mixture is left out with the library's own reason, never filled. The
units are the library's (`stream_units_of_measure`), and a temperature or
pressure nobody gave is the library's own Stream default, said so.
"""
from __future__ import annotations

import functools
import inspect
import itertools
import math
import shutil
import sys
import types
from contextlib import contextmanager
from importlib.metadata import version
from typing import Any, Iterator

import biosteam as bst  # imported here so the cost is paid at start
import numpy as np
import thermosteam as tmo  # BioSTEAM's property engine, loaded with it
from scipy.stats import qmc
from thermosteam.utils import chemical_cache

from .. import flowsheets
from ..flowsheets.shelf import TABLE_UNITS
from . import serve
from .dot_names import stable_names

_BUILT: dict[str, Any] = {}


def _no_debugger(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("BioSTEAM reached breakpoint() inside its own code (in 2.54.0, AeratedBioreactor's bubble-column "
                       "correlation, when it cannot read the broth's viscosity or the gas's density); the worker does not "
                       "stop in a debugger, so this request fails")


sys.breakpointhook = _no_debugger


class Refused(ValueError):
    """The request cannot be computed, in words."""


# How many plants built from a structure (OF-BLD-020 §6.1: custom_train_v1,
# one per vessel design, train run and finance) the worker keeps warm; the
# oldest is let go past it. A setting, not a measurement.
STRUCTURES_KEPT = 4


def _structure_key(name: str, structure: dict[str, Any]) -> str:
    import hashlib
    import json

    text = json.dumps(structure, sort_keys=True, separators=(",", ":"), default=str)
    return f"{name}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def built(name: str, structure: dict[str, Any] | None = None) -> tuple[Any, Any]:
    try:
        module = flowsheets.load(name)
    except KeyError as e:
        raise Refused(str(e)) from e
    if not hasattr(module, "build"):
        raise Refused(f"{name} is a reference biorefinery: it runs whole on its package's own defaults, "
                      "through its reference run, not case by case")
    takes = bool(getattr(module, "STRUCTURED", False))
    if takes and structure is None:
        raise Refused(f"{name} is built from a vessel design and a train run, which this request does not name")
    if not takes and structure is not None:
        raise Refused(f"{name} is built once, whole, and takes no structure")
    key = name if structure is None else _structure_key(name, structure)
    if key not in _BUILT:
        # Built as it would be in a worker that had built nothing before
        # (OF-BLD-019 §2.R): BioSTEAM's tickets start at one, so the streams a
        # package leaves unnamed take the same ids whichever plant this worker
        # built first; and every chemical comes from fresh caches, so nothing
        # this plant changes reaches a plant built later, nor the other way.
        with package_defaults():
            _BUILT[key] = module.build(structure, unit_class) if takes else module.build()
        made = [k for k in _BUILT if ":" in k]
        for old in made[:-STRUCTURES_KEPT]:
            del _BUILT[old]
    return module, _BUILT[key]


def evaluate(name: str, values: dict[str, float], structure: dict[str, Any] | None = None) -> dict[str, float]:
    module, system = built(name, structure)
    unknown = sorted(set(values) - set(module.INPUTS))
    if unknown:
        raise Refused(f"{name} has no input {', '.join(unknown)}; it takes {', '.join(module.INPUTS)}")
    try:
        return module.evaluate(system, values)
    except ValueError as e:  # an input outside what the flowsheet takes, in its words
        raise Refused(str(e)) from e


def grid(name: str, axes: dict[str, list[float]], base: dict[str, float],
         structure: dict[str, Any] | None = None) -> dict[str, Any]:
    if not 1 <= len(axes) <= 3:
        raise Refused("a grid runs over one to three inputs")
    keys = list(axes)
    cells = []
    for combo in itertools.product(*(axes[k] for k in keys)):
        values = {**base, **dict(zip(keys, combo))}
        outputs, reason = _attempt(name, values, structure)
        cells.append({"at": dict(zip(keys, combo)), "outputs": outputs, "infeasible": reason})
    return {"axes": axes, "base": base, "cells": cells}


def _sample(spec: dict[str, Any], u: float) -> float:
    kind = spec["kind"]
    if kind == "fixed":
        return float(spec["value"])
    lo, hi = float(spec["low"]), float(spec["high"])
    if kind == "uniform":
        return lo + u * (hi - lo)
    if kind == "triangular":
        mode = float(spec["mode"])
        if hi == lo:
            return lo
        c = (mode - lo) / (hi - lo)
        return lo + (hi - lo) * (np.sqrt(u * c) if u < c else 1 - np.sqrt((1 - u) * (1 - c)))
    raise Refused(f"there is no distribution {kind}")


def _attempt(name: str, values: dict[str, float],
             structure: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """One case. A case the flowsheet cannot hold is a result, named: its
    reason key (a flowsheet's `Infeasible.reason`, else `error`) and words."""
    try:
        return evaluate(name, values, structure), None
    except Refused:
        raise
    except Exception as e:
        reason = getattr(e, "reason", None) or "error"
        return None, {"reason": str(reason), "detail": str(e) if reason != "error" else f"{type(e).__name__}: {e}"}


def montecarlo(name: str, specs: dict[str, dict[str, Any]], n: int, seed: int, base: dict[str, float],
               structure: dict[str, Any] | None = None) -> dict[str, Any]:
    keys = list(specs)
    lhs = qmc.LatinHypercube(d=max(1, len(keys)), seed=seed).random(n)
    samples = []
    for row in lhs:
        values = {**base, **{k: _sample(specs[k], float(row[i])) for i, k in enumerate(keys)}}
        outputs, reason = _attempt(name, values, structure)
        samples.append({"inputs": values, "outputs": outputs, "infeasible": reason})
    return {"n": n, "seed": seed, "samples": samples}


# ── the run's tables (OF-BLD-019 §2.1) ─────────────────────────────────

# The units of what the tables hold are BioSTEAM's, written into every run
# as `tableUnits` (flowsheets/shelf.py's TABLE_UNITS; demo.py's stand-in
# claims the same). D8's words when the diagram cannot be drawn here:
NO_GRAPHVIZ = ("Graphviz was not on the host that made this run, so it has no diagram; a host that has it "
               "(brew install graphviz on the Mini) draws its own run of the same inputs. The units are listed in run order.")
# A run whose basis asks for the diagram, replayed where dot is not found.
DOT_MISSING = ("This run's basis asks for the diagram Graphviz draws, and Graphviz's dot is not on this host's path; "
               "the units are listed in run order.")


def _num(x: Any) -> float | None:
    """A finite float, or None: an artifact holds no NaN or infinity."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _id(stream_or_unit: Any) -> str | None:
    """The ID of a unit or stream, or None where there is none (a feed has
    no source unit, a product no sink)."""
    if not stream_or_unit:
        return None
    return getattr(stream_or_unit, "ID", None) or None


def _sid(s: Any) -> str:
    """A stream's ID, or, for a stream BioSTEAM left unnamed (a package may
    leave one; the corn plant's water centre has four), where it sits in
    BioSTEAM's own notation: 'U1-2' for outlet 2 of U1, '0-U1' for inlet 0."""
    if s.ID:
        return s.ID
    if s.source:
        return f"{s.source.ID}-{next((i for i, o in enumerate(s.source.outs) if o is s), 'out')}"
    if s.sink:
        return f"{next((i for i, o in enumerate(s.sink.ins) if o is s), 'in')}-{s.sink.ID}"
    return "unnamed"


def stream_table(system: Any) -> list[dict[str, Any]]:
    """Every stream of the system, in the order its units run: where it comes
    from and goes, its phase, temperature, pressure, total mass flow and the
    mass flow of each component that flows."""
    rows = []
    for s in system.streams:
        ids = s.chemicals.IDs
        flows = {i: float(m) for i, m in zip(ids, s.mass) if m}
        rows.append({
            "id": _sid(s), "source": _id(s.source), "sink": _id(s.sink), "phase": str(s.phase),
            "T": float(s.T), "P": float(s.P), "massFlow": float(s.F_mass), "massFlows": flows,
            "price": _num(s.price) if s.price else None,
        })
    return rows


def _duties(heat_utilities: Any) -> tuple[float | None, float | None]:
    """Heating and cooling duty, split as BioSTEAM's System splits them: a
    utility whose flow and duty share a sign heats, the rest cool."""
    hus = list(heat_utilities or [])
    if not hus:
        return None, None
    heating = sum(float(h.duty) for h in hus if h.flow * h.duty > 0)
    cooling = -sum(float(h.duty) for h in hus if h.flow * h.duty < 0)
    return heating, cooling


def unit_table(system: Any) -> list[dict[str, Any]]:
    """Every unit operation in run order, with its BioSTEAM class, its costs,
    and its duties and power where it has them."""
    rows = []
    for n, u in enumerate(system.units):
        heating, cooling = _duties(u.heat_utilities)
        power = _num(u.power_utility.rate)
        rows.append({
            "id": u.ID, "unitClass": type(u).__name__, "line": getattr(u, "line", None) or None, "order": n,
            "ins": [_sid(s) for s in u.ins if s], "outs": [_sid(s) for s in u.outs if s],
            "installedCost": float(u.installed_cost), "purchaseCost": float(u.purchase_cost),
            "heatingDuty": heating, "coolingDuty": cooling, "power": power or None,
        })
    return rows


def utility_duties(units: Any, group: str) -> dict[str, Any]:
    """BioSTEAM's UnitGroup over the plant's units, each total with the unit
    the UnitGroup module states for it."""
    from biosteam.process_tools import unit_group as ug

    g = bst.UnitGroup(group, list(units))
    return {
        "group": group,
        "heating": float(g.get_heating_duty()), "heatingUnit": ug.DUTY_UNITS,
        "cooling": float(g.get_cooling_duty()), "coolingUnit": ug.DUTY_UNITS,
        "electricityConsumption": float(g.get_electricity_consumption()), "electricityConsumptionUnit": ug.ELEC_UNITS,
        "electricityProduction": float(g.get_electricity_production()), "electricityProductionUnit": ug.ELEC_UNITS,
    }


# A relative size below which a difference of two TEA totals is the float's
# own rounding, not a cost (a precision, not a process number).
NOISE = 1e-12

LINE_WORDS = {
    "feedstock": ("Main feedstock", "the system's market value of the feedstock stream (System.get_market_value)"),
    "otherMaterials": ("Other materials", "TEA.material_cost less the main feedstock"),
    "utilities": ("Utilities", "TEA.utility_cost"),
    "otherVariable": ("Other variable costs", "TEA.VOC less material and utility cost"),
    "fixedOperating": ("Fixed operating, labour included", "TEA.FOC"),
    "capitalRecovery": ("Capital recovery", "TEA.sales less TEA.AOC: the return on and of the capital, and its tax"),
    "coproductCredits": ("Co-product credits", "TEA.sales less the main product's market value, as a credit"),
}


def tea_breakdown(parts: dict[str, Any]) -> dict[str, Any] | None:
    """The TEA object's own numbers for the base case. When the flowsheet
    solved a price, the product carries it while the numbers are read, and
    gets back what it had after."""
    tea, product = parts.get("tea"), parts.get("product")
    if tea is None or product is None:
        return None
    feedstock, price = parts.get("feedstock"), parts.get("price")
    system = tea.system
    before = product.price
    try:
        if price is not None:
            product.price = price
        hours = float(tea.operating_hours)
        sales, material, utility = float(tea.sales), float(tea.material_cost), float(tea.utility_cost)
        foc, voc, aoc = float(tea.FOC), float(tea.VOC), float(tea.AOC)
        revenue = float(system.get_market_value(product))
        feed_cost = float(system.get_market_value(feedstock)) if feedstock is not None else None
        out = {
            "teaClass": type(tea).__name__, "product": product.ID, "feedstock": _id(feedstock),
            "productPrice": _num(product.price), "basisFlow": _num(parts.get("basis_flow", product.F_mass)),
            "basis": parts.get("basis") or f"kg of the {product.ID} stream",
            "operatingHours": hours, "sales": sales, "materialCost": material, "feedstockCost": feed_cost,
            "otherMaterialCost": material - (feed_cost or 0.0), "utilityCost": utility,
            "purchaseCost": float(tea.purchase_cost), "installedEquipmentCost": float(tea.installed_equipment_cost),
            "FCI": float(tea.FCI), "TCI": float(tea.TCI), "FOC": foc,
            "laborCost": _num(getattr(tea, "labor_cost", None)),
            "capitalRecovery": sales - aoc, "coproductCredits": sales - revenue,
            "IRR": _num(getattr(tea, "IRR", None)), "incomeTax": _num(getattr(tea, "income_tax", None)),
        }
    finally:
        product.price = before
    annual = {
        "feedstock": feed_cost, "otherMaterials": out["otherMaterialCost"], "utilities": utility,
        "otherVariable": voc - material - utility, "fixedOperating": foc, "capitalRecovery": out["capitalRecovery"],
        "coproductCredits": -out["coproductCredits"],
    }
    per = (out["basisFlow"] or 0.0) * hours
    lines = []
    for key, v in annual.items():
        # Other variable cost and co-product credit are lines only when they
        # are something: a difference of two TEA totals that agree to the
        # float's own noise (the corn plant's VOC less material and utility
        # cost is ±1e-9 USD/yr on 6e7, and its sign changes build to build)
        # is no line.
        if v is None or (key in ("otherVariable", "coproductCredits") and abs(v) <= NOISE * max(abs(voc), abs(sales), 1.0)):
            continue
        label, reads = LINE_WORDS[key]
        lines.append({"key": key, "label": label, "usdPerYear": v, "perUnit": v / per if per else None, "reads": reads})
    out["lines"] = lines
    return out


def diagram(system: Any, draw: bool | None = None) -> dict[str, Any]:
    """The flowsheet as SVG text when the run's basis asks for it (`draw`,
    the `diagram` input the service sets from whether this host has
    Graphviz's dot; None, a caller that names nothing, draws when dot is
    here) (D8); else None and the words why."""
    here = shutil.which("dot") is not None
    if draw is None:
        draw = here
    if not draw:
        return {"diagram": None, "diagramNote": NO_GRAPHVIZ}
    if not here:
        return {"diagram": None, "diagramNote": DOT_MISSING}
    try:
        # BioSTEAM names each node by its object's address; renamed by their
        # order in the digraph, two builds of one plant draw one SVG, so a
        # drawn run replays (OF-BLD-019 §7.R, workers/dot_names.py).
        graph = system.diagram(format="svg", display=False)
        graph.body[:] = stable_names(list(graph.body))
        svg = graph.pipe(format="svg").decode("utf-8")
    except Exception as e:  # Graphviz is here and could not draw it: say so, list the units
        return {"diagram": None, "diagramNote": f"Graphviz could not draw this flowsheet on the host that made this run "
                                               f"({type(e).__name__}); the units are listed in run order."}
    return {"diagram": svg, "diagramNote": None}


def tables(module: Any, b: Any, draw: bool | None = None) -> dict[str, Any]:
    """Every table of the base case, read from the objects it left. Where
    the flowsheet solved a price, the product carries it while every table
    is read, its stream row included, and gets back what it had after
    (OF-BLD-019 §2.R: the row once showed the package's list price beside
    the price the run solved)."""
    parts = module.parts(b) if hasattr(module, "parts") else {"system": b}
    system = parts["system"]
    tea, product, price = parts.get("tea"), parts.get("product"), parts.get("price")
    units = tea.units if tea is not None else system.units
    before = product.price if product is not None else None
    try:
        if product is not None and price is not None:
            product.price = price
        return {
            "tablesSource": f"BioSTEAM {version('biosteam')}, thermosteam {version('thermosteam')}",
            "tea": tea_breakdown(parts),
            "streams": stream_table(system),
            "units": unit_table(system),
            "utilities": utility_duties(units, "the units the TEA costs" if tea is not None else "every unit of the system"),
            **diagram(system, draw),
            "unitOrder": [u.ID for u in system.units],
            "tableUnits": TABLE_UNITS,
        }
    finally:
        if product is not None:
            product.price = before


def run(name: str, base: dict[str, float], specs: dict[str, dict[str, Any]], samples: int, seed: int,
        axes: dict[str, list[float]] | None = None, draw: bool | None = None,
        structure: dict[str, Any] | None = None) -> dict[str, Any]:
    """One whole run: the base case and its tables, read before any other
    case moves the objects; then the grid, when one is asked; then the
    samples, Latin hypercube and seeded, as `montecarlo`. A flowsheet built
    from a structure (OF-BLD-020 §6.1, custom_train_v1) takes it here, and
    every case of the run is of the one plant it builds."""
    module, b = built(name, structure)
    try:
        base_out, base_infeasible = evaluate(name, base, structure), None
    except Refused:
        raise
    except Exception as e:  # the base case cannot be held: said as the service says a worker error
        base_out, base_infeasible = None, f"{type(e).__name__}: {e}"
    out_tables = tables(module, b, draw) if base_out is not None else None
    out_grid = grid(name, axes, base, structure) if axes else None
    mc = (montecarlo(name, specs, samples, seed, base, structure) if samples
          else {"n": 0, "seed": seed, "samples": []})
    return {"base": base_out, "baseInfeasible": base_infeasible, "tables": out_tables, "grid": out_grid, "montecarlo": mc}


# ── a reference biorefinery's run (OF-BLD-019 §2.2) ────────────────────


# The code every function thermosteam's `chemical_cache` decorator makes
# runs: how such a function is told from any other.
_CACHED_CHEMICALS = chemical_cache(lambda: None).__code__


def _cached_chemicals() -> dict[int, Any]:
    """Every function a loaded `biorefineries` module made with thermosteam's
    `chemical_cache` (each package's `create_chemicals` and kin), by id.
    Each keeps, through `functools.cache`, the chemicals it made the first
    time it ran, and makes each one by name with thermosteam's chemical cache
    on, so a Chemical object is shared by every package that made it: a
    package that changes one changes it for the others (biorefineries.corn
    locks NH3 to liquid in the object biorefineries.cornstover uses)."""
    out: dict[int, Any] = {}
    for name, module in list(sys.modules.items()):
        if not (name == "biorefineries" or name.startswith("biorefineries.")):
            continue
        for v in list(getattr(module, "__dict__", {}).values()):
            if type(v) is types.FunctionType and v.__code__ is _CACHED_CHEMICALS:
                out[id(v)] = v
    return out


def _cache_of(fn: Any) -> Any:
    """The cell that holds a `chemical_cache` function's functools cache."""
    return fn.__closure__[fn.__code__.co_freevars.index("g")]


def _fresh_cache(fn: Any) -> None:
    """Give a `chemical_cache` function an empty cache of its own, so the
    next call makes its chemicals anew, as in a fresh worker."""
    plain = fn.__closure__[fn.__code__.co_freevars.index("f")].cell_contents
    _cache_of(fn).cell_contents = functools.cache(plain)


@contextmanager
def package_defaults() -> Iterator[None]:
    """A plant builds, and a reference biorefinery is read, as in a worker
    that had built nothing before: BioSTEAM's defaults first, as the
    package's own test runs it (`default_settings` in
    biorefineries/tests/test_biorefineries.py calls
    `bst.process_tools.default()`, which also clears the tickets and
    thermosteam's chemical cache), and every package's chemicals made anew
    from empty caches (OF-BLD-019 §2.R). Afterwards what the worker held
    before is put back, not the defaults, because the worker keeps other
    plants warm whose costs read these globals (a PowerUtility's cost reads
    the class's price when it is asked); a chemicals cache first filled
    inside is emptied, so nothing a plant made here is shared with the next."""
    cached = _cached_chemicals()
    saved = {
        "cachedChemicals": {k: _cache_of(fn).cell_contents for k, fn in cached.items()},
        "CE": bst.CE,
        "power": bst.PowerUtility.price,
        "powerFactors": dict(bst.PowerUtility.characterization_factors),
        "heating": bst.HeatUtility.heating_agents,
        "cooling": bst.HeatUtility.cooling_agents,
        "tickets": {c: dict(c.ticket_numbers) for c in (bst.Stream, bst.Unit, bst.System)},
        "chemicals": dict(bst.Chemical.chemical_cache),
        "flowsheet": bst.main_flowsheet.get_flowsheet(),
        "thermo": getattr(bst.settings, "_thermo", None),
    }
    for fn in cached.values():
        _fresh_cache(fn)
    bst.process_tools.default()
    try:
        yield
    finally:
        for k, fn in _cached_chemicals().items():
            if k in saved["cachedChemicals"]:
                _cache_of(fn).cell_contents = saved["cachedChemicals"][k]
            else:  # a module first imported inside: its cache holds this plant's chemicals
                _fresh_cache(fn)
        bst.CE = saved["CE"]
        bst.PowerUtility.price = saved["power"]
        bst.PowerUtility.characterization_factors.clear()
        bst.PowerUtility.characterization_factors.update(saved["powerFactors"])
        bst.HeatUtility.heating_agents = saved["heating"]
        bst.HeatUtility.cooling_agents = saved["cooling"]
        for cls, tickets in saved["tickets"].items():
            cls.ticket_numbers.clear()
            cls.ticket_numbers.update(tickets)
        bst.Chemical.chemical_cache.clear()
        bst.Chemical.chemical_cache.update(saved["chemicals"])
        bst.main_flowsheet.set_flowsheet(saved["flowsheet"])
        if saved["thermo"] is not None:
            bst.settings.set_thermo(saved["thermo"])


def package_test_quantities(parts: dict[str, Any]) -> dict[str, float]:
    """The quantities the package's test template asserts, computed as it
    computes them (`UnitGroup('Biorefinery', tea.units)`), keyed by the
    expression it writes (flowsheets/shelf.py, TEST_QUANTITIES)."""
    tea, feedstock, product = parts["tea"], parts["feedstock"], parts["product"]
    units = bst.UnitGroup("Biorefinery", tea.units)
    return {
        "tea.IRR": float(tea.IRR),
        "feedstock.price": float(feedstock.price),
        "product.price": float(product.price),
        "tea.sales": float(tea.sales),
        "tea.material_cost": float(tea.material_cost),
        "tea.installed_equipment_cost": float(tea.installed_equipment_cost),
        "tea.utility_cost": float(tea.utility_cost),
        "units.get_heating_duty()": float(units.get_heating_duty()),
        "units.get_cooling_duty()": float(units.get_cooling_duty()),
        "units.get_electricity_consumption()": float(units.get_electricity_consumption()),
        "units.get_electricity_production()": float(units.get_electricity_production()),
    }


def rounded(value: Any, digits: int) -> Any:
    """Every float in a JSON-ready value to `digits` significant digits."""
    if isinstance(value, float):
        return float(f"{value:.{digits}g}") if math.isfinite(value) else value
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v, digits) for v in value]
    return value


def reference(name: str, digits: int, draw: bool | None = None) -> dict[str, Any]:
    """A reference biorefinery, run whole: built afresh inside
    `package_defaults()`, then everything read before the settings go back."""
    try:
        module = flowsheets.load(name)
    except KeyError as e:
        raise Refused(str(e)) from e
    if not hasattr(module, "load"):
        raise Refused(f"{name} is not a reference biorefinery: it is run case by case, on its inputs")
    if not 1 <= digits <= 17:
        raise Refused("a reference run keeps between 1 and 17 significant digits")
    with package_defaults():
        b = module.load()
        parts = module.parts(b)
        out = {
            "flowsheet": name,
            "simulator": f"biosteam {version('biosteam')}",
            **module.outputs(b),
            "measured": package_test_quantities(parts),
            "readBack": module.read_back(b) if hasattr(module, "read_back") else {},
            **tables(module, b, draw),
        }
    return rounded(out, digits)


def _op_reference(args):
    return reference(str(args["flowsheet"]), int(args.get("digits", 17)), args.get("diagram"))


# ── thermosteam answers property questions (OF-BLD-019 §4.2, D9) ───────

# The properties asked of every mixture: (output key, the Stream attribute,
# the key of its unit in thermosteam's stream_units_of_measure).
PROPERTIES = (("density", "rho"), ("Cp", "Cp"), ("viscosity", "mu"))
# Numerical settings of the two solves, not quantities of any process: how
# finely the azeotrope's bracket is scanned, how many halvings refine it, and
# when the titre's fixed point has settled.
AZEOTROPE_SCAN = 100
AZEOTROPE_HALVINGS = 60
TITRE_TOLERANCE = 1e-12
TITRE_ITERATIONS = 100

_THERMOS: dict[tuple[str, ...], Any] = {}


def stream_defaults() -> tuple[float, float, str]:
    """The temperature, pressure and phase thermosteam gives a Stream nobody
    set them on, read from the library's own signature."""
    params = inspect.signature(tmo.Stream.__init__).parameters
    return float(params["T"].default), float(params["P"].default), str(params["phase"].default)


def library_units() -> dict[str, str]:
    from thermosteam.units_of_measure import stream_units_of_measure as su

    out = {key: str(su[attr]) for key, attr in PROPERTIES}
    out.update(T=str(su["T"]), P=str(su["P"]), bubblePoint=str(su["T"]), dewPoint=str(su["T"]),
               massFractions="kg/kg", vapourAtBubble="mol/mol")
    return out


def thermo_of(names: list[str]) -> Any:
    """One property package for these chemicals, each looked up in the
    library by name; kept, since a lookup costs a database read. A chemical
    the library lacks or cannot build refuses the question, naming it."""
    key = tuple(sorted(set(names)))
    if key in _THERMOS:
        return _THERMOS[key]
    chemicals, lacking, broken = [], [], []
    for name in key:
        try:
            chemicals.append(tmo.Chemical(name))
        except LookupError:
            lacking.append(name)
        except Exception as e:  # in the database, and the library cannot build it
            broken.append(f"{name} ({type(e).__name__}: {e})")
    said = []
    if lacking:
        said.append(f"thermosteam's chemical library has no chemical named {', '.join(lacking)}")
    if broken:
        said.append(f"thermosteam could not build {', '.join(broken)} from its library")
    if said:
        raise Refused("; ".join(said) + ". It answers for the library's own chemicals and guesses no other.")
    try:
        th = tmo.Thermo(chemicals)
    except Exception as e:
        raise Refused(f"thermosteam could not make one property package of {', '.join(key)}: {type(e).__name__}: {e}") from e
    _THERMOS[key] = th
    return th


def _mixture(th: Any, flows: dict[str, float], T: float, P: float, phase: str, by: str = "mass") -> Any:
    s = tmo.Stream(None, thermo=th, phase=phase, T=T, P=P)  # None: kept out of BioSTEAM's registry
    target = s.imass if by == "mass" else s.imol
    for name, v in flows.items():
        target[name] = float(v)
    return s


def _finite(what: str, fn: Any, notes: list[str]) -> float | None:
    try:
        v = float(fn())
    except Exception as e:
        notes.append(f"{what}: thermosteam could not compute it for this mixture ({type(e).__name__}: {e})")
        return None
    if not math.isfinite(v):
        notes.append(f"{what}: thermosteam gave no finite value for this mixture")
        return None
    return v


def _titre(th: Any, solute: str, solvent: str, kg_m3: float, T: float, P: float, phase: str) -> tuple[float, dict]:
    """The solute's mass fraction at which its mass per volume of the mixture,
    at the mixture's own density as thermosteam computes it, is the titre: a
    fixed point w = c / rho(w), from the pure solvent's density."""
    w = 0.0
    for n in range(1, TITRE_ITERATIONS + 1):
        rho = float(_mixture(th, {solvent: 1.0 - w, solute: w}, T, P, phase).rho)
        nxt = kg_m3 / rho
        if not 0.0 <= nxt < 1.0:
            raise Refused(f"a titre of {kg_m3:g} kg/m^3 is not below the density thermosteam gives the mixture "
                          f"({rho:g} kg/m^3), so no {solvent}–{solute} mixture holds it")
        if abs(nxt - w) <= TITRE_TOLERANCE:
            return nxt, {"kind": "titre", "solute": solute, "solvent": solvent, "kgPerM3": kg_m3, "iterations": n,
                         "how": "the mass fraction at which the solute per volume of the mixture, at the mixture's "
                                "own density as thermosteam computes it, equals the titre (a fixed point)"}
        w = nxt
    raise Refused(f"the mass fraction for a titre of {kg_m3:g} kg/m^3 did not settle in {TITRE_ITERATIONS} steps")


def _azeotrope_grid() -> list[float]:
    """The light chemical's mole fractions the azeotrope search scans: the
    grid between the two pure chemicals, both pure ends left out."""
    return [i / AZEOTROPE_SCAN for i in range(1, AZEOTROPE_SCAN)]


def _minimum_boiling(th: Any, light: str, heavy: str, T: float, P: float) -> float | None:
    """The light chemical's mole fraction in the liquid whose first bubble, by
    thermosteam's own vapour-liquid equilibrium at P, has the liquid's own
    composition, where y(x) - x for the light chemical turns from positive to
    not (a minimum-boiling azeotrope): scanned on `_azeotrope_grid`, then
    halved. None when it never turns on the grid (OF-BLD-020 §7.1 generalised
    the ethanol–water preset's search to any two chemicals)."""

    def gap(x: float) -> float:
        b = _mixture(th, {light: x, heavy: 1.0 - x}, T, P, "l", by="mol").bubble_point_at_P(P)
        return float(dict(zip(b.IDs, b.y))[light]) - x

    xs = _azeotrope_grid()
    gaps = [gap(x) for x in xs]
    bracket = next(((xs[i], xs[i + 1]) for i in range(len(xs) - 1) if gaps[i] > 0 >= gaps[i + 1]), None)
    if bracket is None:
        return None
    lo, hi = bracket
    for _ in range(AZEOTROPE_HALVINGS):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def _azeotrope(th: Any, light: str, heavy: str, T: float, P: float) -> tuple[float, dict]:
    """The liquid whose first bubble, by thermosteam's own vapour-liquid
    equilibrium at P, has the liquid's own composition: where y(x) - x for the
    light chemical turns from positive to not, scanned and then halved."""
    x = _minimum_boiling(th, light, heavy, T, P)
    if x is None:
        raise Refused(f"thermosteam's own vapour-liquid equilibrium gives {light} and {heavy} no azeotrope at {P:g} Pa")
    return x, {"kind": "azeotrope", "light": light, "heavy": heavy, "moleFraction": x, "P": P,
               "how": "the liquid whose first bubble, by thermosteam's own vapour-liquid equilibrium at this pressure, "
                      "has the liquid's own composition: y - x of the lighter chemical scanned for its change of sign, "
                      "then halved"}


def thermo_props(components: dict[str, float], T: float | None = None, P: float | None = None,
                 phase: str | None = None, solve: dict[str, Any] | None = None) -> dict[str, Any]:
    """D9: a Stream on the library's chemicals at T and P, and what the
    library says of it. `components` are mass flows or fractions (only their
    ratios matter); `solve` asks for the composition of a titre or an
    azeotrope instead. A T, P or phase not given is the library's default."""
    T0, P0, phase0 = stream_defaults()
    T_from = "given" if T is not None else "thermosteam's Stream default"
    P_from = "given" if P is not None else "thermosteam's Stream default"
    T, P, phase = float(T if T is not None else T0), float(P if P is not None else P0), str(phase or phase0)
    if phase not in ("l", "g", "s"):
        raise Refused(f"a mixture in phases {phase!r} keeps no split by phase here; thermosteam is asked about one phase, "
                      "l, g or s, and not asked to guess the split")
    names = [n for n, v in components.items() if v and float(v) > 0]
    if solve and solve.get("kind") == "titre":
        names = [solve["solvent"], solve["solute"]]
    elif solve and solve.get("kind") == "azeotrope":
        names = [solve["heavy"], solve["light"]]
    elif solve:
        raise Refused(f"there is no solve {solve.get('kind')!r}")
    if not names:
        raise Refused("the mixture carries nothing: every flow is zero")
    th = thermo_of(names)
    solved = None
    if solve and solve["kind"] == "titre":
        w, solved = _titre(th, solve["solute"], solve["solvent"], float(solve["kgPerM3"]), T, P, phase)
        flows = {solve["solvent"]: 1.0 - w, solve["solute"]: w}
        s = _mixture(th, flows, T, P, phase)
    elif solve and solve["kind"] == "azeotrope":
        x, solved = _azeotrope(th, solve["light"], solve["heavy"], T, P)
        s = _mixture(th, {solve["light"]: x, solve["heavy"]: 1.0 - x}, T, P, phase, by="mol")
    else:
        s = _mixture(th, {n: float(components[n]) for n in names}, T, P, phase)
    total = float(s.F_mass)
    fractions = {i: float(m) / total for i, m in zip(s.chemicals.IDs, s.mass) if m}
    notes: list[str] = []
    out: dict[str, Any] = {key: _finite(key, lambda a=attr: getattr(s, a), notes) for key, attr in PROPERTIES}
    try:
        b = s.bubble_point_at_P(P)
        out["bubblePoint"] = _finite("bubblePoint", lambda: b.T, notes)
        out["vapourAtBubble"] = {i: float(y) for i, y in zip(b.IDs, b.y)}
    except Exception as e:
        notes.append(f"bubblePoint: thermosteam could not compute it for this mixture ({type(e).__name__}: {e})")
        out["bubblePoint"], out["vapourAtBubble"] = None, None
    out["dewPoint"] = _finite("dewPoint", lambda: s.dew_point_at_P(P).T, notes)
    return {
        "library": f"thermosteam {version('thermosteam')}", "T": T, "P": P, "phase": phase,
        "TSource": T_from, "PSource": P_from, "massFractions": fractions, **out,
        "units": library_units(), "solved": solved, "notes": notes,
    }


def _op_thermo_props(args):
    return thermo_props(dict(args.get("components") or {}), args.get("T"), args.get("P"), args.get("phase"),
                        args.get("solve") or None)


# ── a product's volatility (OF-BLD-020 §7.1, D12) ──────────────────────

VOLATILITY_HOW = ("each chemical's normal boiling point is the library's own Tb; the azeotrope is the liquid whose first "
                  "bubble, by the library's own vapour-liquid equilibrium at this pressure, has the liquid's own "
                  "composition, where y - x of the lower-boiling chemical turns from positive to not (a minimum-boiling "
                  "azeotrope), scanned on the grid `searched` names and then halved")


def _boiling_point(th: Any, name: str, notes: list[str]) -> float | None:
    tb = getattr(th.chemicals[name], "Tb", None)
    if tb is None or not math.isfinite(float(tb)):
        notes.append(f"Tb of {name}: thermosteam's library holds no normal boiling point for it")
        return None
    return float(tb)


def volatility(chemical: str, partner: str, P: float | None = None) -> dict[str, Any]:
    """D12's volatility, in thermosteam's words: each chemical's normal
    boiling point as the library holds it (`Chemical.Tb`), which of the two
    boils lower, and whether the library's own vapour-liquid equilibrium gives
    the pair a minimum-boiling azeotrope at P (the library's Stream default
    when not given): `_minimum_boiling` on the lower-boiling chemical, the
    search the `ethanol-water-azeotrope` preset runs. One found is the
    composition and the temperature the library gives; none found is said
    with the grid searched; a search the library cannot carry out is left
    unanswered with its reason, never guessed."""
    T0, P0, _ = stream_defaults()
    P_from = "given" if P is not None else "thermosteam's Stream default"
    P = float(P if P is not None else P0)
    if not chemical or not partner or chemical == partner:
        raise Refused("a volatility names a chemical and a partner: two different chemicals of the library")
    th = thermo_of([chemical, partner])
    notes: list[str] = []
    tb = {n: _boiling_point(th, n, notes) for n in (chemical, partner)}
    su = library_units()
    out: dict[str, Any] = {
        "library": f"thermosteam {version('thermosteam')}", "chemical": chemical, "partner": partner, "P": P,
        "PSource": P_from, "boilingPoint": tb[chemical], "partnerBoilingPoint": tb[partner], "lighter": None,
        "azeotrope": None, "azeotropeMoleFraction": None, "azeotropeMassFraction": None, "azeotropeT": None,
        "searched": None, "how": VOLATILITY_HOW, "notes": notes,
        "units": {"boilingPoint": su["T"], "partnerBoilingPoint": su["T"], "azeotropeT": su["T"], "P": su["P"],
                  "azeotropeMoleFraction": "mol/mol", "azeotropeMassFraction": "kg/kg", "searched": "mol/mol"},
    }
    if tb[chemical] is None or tb[partner] is None:
        notes.append("azeotrope: not searched, since without both normal boiling points which chemical boils lower "
                     "is not known")
        return out
    light, heavy = sorted((chemical, partner), key=lambda n: tb[n])
    xs = _azeotrope_grid()
    out.update(lighter=light, searched={"of": light, "from": xs[0], "to": xs[-1], "points": len(xs),
                                        "halvings": AZEOTROPE_HALVINGS})
    try:
        x = _minimum_boiling(th, light, heavy, T0, P)
    except Exception as e:  # the library could not give a bubble point the search reads
        notes.append(f"azeotrope: thermosteam could not compute the bubble points the search reads for {light} and "
                     f"{heavy} ({type(e).__name__}: {e})")
        return out
    if x is None:
        out["azeotrope"] = False
        notes.append(f"azeotrope: none found. The library's own vapour-liquid equilibrium at {P:g} Pa never turns "
                     f"{light}'s vapour mole fraction from above its liquid's to not, on {len(xs)} {light} mole "
                     f"fractions from {xs[0]:g} to {xs[-1]:g}")
        return out
    s = _mixture(th, {light: x, heavy: 1.0 - x}, T0, P, "l", by="mol")
    mass = dict(zip(s.chemicals.IDs, (float(m) for m in s.mass)))
    out.update(azeotrope=True, azeotropeMoleFraction=x if light == chemical else 1.0 - x,
               azeotropeMassFraction=mass[chemical] / float(s.F_mass),
               azeotropeT=_finite("azeotropeT", lambda: s.bubble_point_at_P(P).T, notes))
    return out


def _op_volatility(args):
    return volatility(str(args.get("chemical") or ""), str(args.get("partner") or ""), args.get("P"))


def _op_run(args):
    return run(str(args["flowsheet"]), dict(args.get("base") or {}), dict(args.get("specs") or {}),
               int(args.get("samples", 0)), int(args.get("seed", 0)), args.get("axes") or None, args.get("diagram"),
               args.get("structure"))


def _op_evaluate(args):
    return evaluate(str(args["flowsheet"]), dict(args.get("values") or {}), args.get("structure"))


def _op_grid(args):
    return grid(str(args["flowsheet"]), dict(args["axes"]), dict(args.get("base") or {}))


def _op_montecarlo(args):
    return montecarlo(str(args["flowsheet"]), dict(args["specs"]), int(args.get("n", 500)), int(args.get("seed", 0)),
                      dict(args.get("base") or {}))


def _op_benchmark(args):
    """The benchmark (§8.2), built afresh inside `package_defaults()`: the
    corn stover plant sets its own utility prices and cost index as it
    builds, and these go back with everything else afterwards, so no later
    case prices on them (OF-BLD-019 §2.R)."""
    from openferment_core.flowsheets import cornstover_benchmark

    with package_defaults():
        return cornstover_benchmark.run()


def _op_vessel_specs(args):
    from ..flowsheets import vessel

    return vessel.specs(str(args.get("kind") or ""))


def _op_vessel_design(args):
    from ..flowsheets import vessel

    return vessel.design(dict(args))


# ── pureOS's unit catalogue (OF-BLD-020 §5.1) ──────────────────────────


def unit_class(type_id: str) -> tuple[Any, Any]:
    """A catalogue entry and its class: BioSTEAM's by name, or the in-house
    one, which only this worker imports (E.3‴)."""
    from ..pureos import catalogue, inhouse

    e = catalogue.entry(type_id)
    if e.inhouse:
        return e, getattr(inhouse, e.inhouse)
    return e, getattr(bst, e.biosteam)


def yeast_chemicals() -> Any:
    """The yeast program's chemicals, as the ethanol flowsheet builds on them."""
    from ..flowsheets.ethanol_glucose_v0 import create_chemicals

    return create_chemicals()


def _op_catalogue_specs(args):
    from ..pureos import catalogue

    e, cls = unit_class(str(args.get("type") or ""))
    with package_defaults():
        chems = yeast_chemicals()
        bst.settings.set_thermo(chems)
        return catalogue.read_class(e.id, cls, list(chems.IDs))


def _inlet(chems: Any, spec: dict[str, Any], n: int) -> Any:
    """A stand-in or a train's inlet as the request gives it: kg/hr by
    chemical, its phase (or, multi-phase, kg/hr by phase and chemical), and
    its temperature and pressure where given; an empty dict is an empty
    inlet the unit may fill."""
    flows = dict(spec.get("flows") or {})
    by_phase = dict(spec.get("byPhase") or {})
    kw = {k: float(spec[k]) for k in ("T", "P") if spec.get(k) is not None}
    if by_phase:
        s = tmo.MultiStream(f"in{n}", thermo=chems, phases=tuple(sorted(by_phase)), **kw)
        for phase, got in by_phase.items():
            for chem, kg in got.items():
                s.imass[phase, chem] = float(kg)
        return s
    s = bst.Stream(f"in{n}", thermo=chems, phase=str(spec.get("phase") or "l"), units="kg/hr", **kw)
    for chem, kg in flows.items():
        s.imass[chem] = float(kg)
    return s


def _op_catalogue_unit_check(args):
    """One unit of a type built alone on the request's inlets and values,
    inside `package_defaults()` on BioSTEAM's default utility prices and cost
    index, simulated, and read. A failure is BioSTEAM's own words."""
    from ..pureos import catalogue

    e, cls = unit_class(str(args.get("type") or ""))
    values = dict(args.get("values") or {})
    keys = list(args.get("hold") or [])
    with package_defaults():
        chems = yeast_chemicals()
        bst.settings.set_thermo(chems)
        bst.process_tools.default_utilities()
        bst.process_tools.default_CEPCI()
        bst.main_flowsheet.set_flowsheet(bst.Flowsheet(f"pureos_check_{e.id.replace('-', '_')}"))
        ins = [_inlet(chems, spec, n) for n, spec in enumerate(args.get("ins") or [])]
        n_out = len([p for p in e.ports if p.side == "out"])
        outs = [f"out{n}" for n in range(n_out)]
        unit = catalogue.build_unit(e.id, cls, "U1", ins, outs, values)
        unit.simulate()
        return catalogue.unit_report(unit, keys)


# ── pureOS's train (OF-BLD-020 §5.2, D9, D10) ─────────────────────────


def _versions() -> dict[str, str]:
    return {"biosteam": version("biosteam"), "thermosteam": version("thermosteam"),
            "biorefineries": version("biorefineries")}


def _op_train_specs(args):
    """What a train builds on, read here: the yeast program's chemical IDs,
    and the temperature, pressure and phase thermosteam gives a Stream nobody
    set them on (an inlet's library default)."""
    T, P, phase = stream_defaults()
    with package_defaults():
        chems = yeast_chemicals()
        ids = list(chems.IDs)
    return {"chemicals": ids, "T": T, "P": P, "phase": phase,
            "from": "thermosteam's Stream signature (its T, P and phase defaults)", "versions": _versions()}


def _op_flowsheet_unit_values(args):
    """The values of a shelf flowsheet's own units by catalogue key, as its
    package builds them (§5.2, `TrainUnitReadFrom`): the flowsheet built once
    and kept, each unit found by its ID and held to the catalogue type's
    class, and read (`flowsheets/train.read_unit`). Read, never simulated: a
    unit's design values are set when it is built."""
    from ..flowsheets import train as train_fs

    name = str(args.get("flowsheet") or "")
    if getattr(flowsheets.load(name) if name in flowsheets.KNOWN else None, "STRUCTURED", False):
        raise Refused(f"{name} is built from a vessel design and a train run: its units are the fermenter and that "
                      "train's own, read from the train run")
    _, b = built(name)
    system = b.system if hasattr(b, "system") else b
    by_id = {u.ID: u for u in system.units}
    out = {}
    for want in args.get("units") or []:
        uid, type_id = str(want.get("unit") or ""), str(want.get("type") or "")
        e, cls = unit_class(type_id)
        unit = by_id.get(uid)
        if unit is None:
            raise Refused(f"{name} has no unit {uid}; its units are {', '.join(by_id)}")
        if type(unit) is not cls and not isinstance(unit, cls):
            raise Refused(f"unit {uid} of {name} is a {type(unit).__name__}, not the {cls.__name__} of the catalogue's "
                          f"{e.id}: a train's unit reads a flowsheet's unit of its own class")
        values, unread = train_fs.read_unit(e.id, unit)
        out[uid] = {"unitClass": type(unit).__name__, "values": values, "unread": unread}
    return {"flowsheet": name, "units": out, "versions": _versions()}


def _op_train_run(args):
    """One train built and run (OF-BLD-020 §5.2): inside `package_defaults()`
    on the yeast program's chemicals, BioSTEAM's default utility prices and
    cost index set as every scenario flowsheet sets them, a fresh flowsheet;
    the train built by `flowsheets/train.Built` and simulated whole; then its
    tables read with this worker's own readers (no TEA: a train is not priced
    here) and each unit's costs. A train that cannot be built or run is the
    module's refusal, in words naming the unit and BioSTEAM's error."""
    from ..flowsheets import train as train_fs

    with package_defaults():
        chems = yeast_chemicals()
        bst.settings.set_thermo(chems)
        bst.process_tools.default_utilities()
        bst.process_tools.default_CEPCI()
        bst.main_flowsheet.set_flowsheet(bst.Flowsheet(str(args["system"])))
        b = train_fs.Built(dict(args), unit_class, chems)
        b.simulate()
        system = b.system
        return {
            "tablesSource": f"BioSTEAM {version('biosteam')}, thermosteam {version('thermosteam')}",
            "streams": stream_table(system),
            "units": unit_table(system),
            "utilities": utility_duties(system.units, "every unit of the train"),
            **diagram(system, args.get("diagram")),
            "unitOrder": [u.ID for u in system.units],
            "tableUnits": TABLE_UNITS,
            "inlet": b.inlet_built,
            "productStream": b.product.ID,
            "outlets": b.outlet_ids(),
            "costs": b.costs(),
            "utilitySettings": flowsheets.utility_settings(system.units),
            "versions": _versions(),
        }


HANDLERS = {"evaluate": _op_evaluate, "grid": _op_grid, "montecarlo": _op_montecarlo, "benchmark": _op_benchmark,
            "run": _op_run, "reference": _op_reference, "thermo_props": _op_thermo_props,
            "vessel_specs": _op_vessel_specs, "vessel_design": _op_vessel_design,
            "catalogue_specs": _op_catalogue_specs, "catalogue_unit_check": _op_catalogue_unit_check}

HANDLERS["volatility"] = _op_volatility  # OF-BLD-020 §7.1
HANDLERS.update(train_specs=_op_train_specs, flowsheet_unit_values=_op_flowsheet_unit_values,
                train_run=_op_train_run)  # OF-BLD-020 §5.2

if __name__ == "__main__":
    serve(HANDLERS, name="proforma")
