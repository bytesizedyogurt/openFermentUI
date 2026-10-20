"""The Proforma worker: BioSTEAM in a process of its own, kept warm
(OF-BLD-014 §8.1).

With flowsheets/, the only place in openferment_core that imports `biosteam`
(test_workers holds it to that). A cold import takes about forty seconds, so
the worker builds each flowsheet once and keeps it; every later request sets
its inputs on the built objects and re-simulates (Appendix 3, trap 3).

    ping        answered by `serve`
    benchmark   the published reference biorefinery (§8.2)
    evaluate    one case of a flowsheet: its inputs in, its outputs out
    grid        the outputs over a grid of up to three inputs
    montecarlo  Latin hypercube samples of the inputs, seeded
    run         one whole run (OF-BLD-019 §2.1): the base case, the tables
                read from BioSTEAM's objects right after it (TEA breakdown,
                streams, units, utility duties, the diagram), the grid and
                the samples; proforma.py keeps it as one artifact (D1)

The tables are read through BioSTEAM's own attributes and methods, never
recomputed: the TEA object's sales, material and utility cost, installed
equipment cost, FCI, TCI, FOC and IRR; each unit's costs, heat utilities and
power utility; the UnitGroup's duties in the units it states; and
`System.diagram` as SVG when Graphviz's `dot` is on the path (D8).
"""
from __future__ import annotations

import itertools
import math
import shutil
from importlib.metadata import version
from typing import Any

import biosteam as bst  # imported here so the cost is paid at start
import numpy as np
from scipy.stats import qmc

from .. import flowsheets
from ..flowsheets.shelf import TABLE_UNITS
from . import serve

_BUILT: dict[str, Any] = {}


class Refused(ValueError):
    """The request cannot be computed, in words."""


def built(name: str) -> tuple[Any, Any]:
    try:
        module = flowsheets.load(name)
    except KeyError as e:
        raise Refused(str(e)) from e
    if not hasattr(module, "build"):
        raise Refused(f"{name} is a reference biorefinery: it runs whole on its package's own defaults, "
                      "through its reference run, not case by case")
    if name not in _BUILT:
        _BUILT[name] = module.build()
    return module, _BUILT[name]


def evaluate(name: str, values: dict[str, float]) -> dict[str, float]:
    module, system = built(name)
    unknown = sorted(set(values) - set(module.INPUTS))
    if unknown:
        raise Refused(f"{name} has no input {', '.join(unknown)}; it takes {', '.join(module.INPUTS)}")
    try:
        return module.evaluate(system, values)
    except ValueError as e:  # an input outside what the flowsheet takes, in its words
        raise Refused(str(e)) from e


def grid(name: str, axes: dict[str, list[float]], base: dict[str, float]) -> dict[str, Any]:
    if not 1 <= len(axes) <= 3:
        raise Refused("a grid runs over one to three inputs")
    keys = list(axes)
    cells = []
    for combo in itertools.product(*(axes[k] for k in keys)):
        values = {**base, **dict(zip(keys, combo))}
        outputs, reason = _attempt(name, values)
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


def _attempt(name: str, values: dict[str, float]) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """One case. A case the flowsheet cannot hold is a result, named: its
    reason key (a flowsheet's `Infeasible.reason`, else `error`) and words."""
    try:
        return evaluate(name, values), None
    except Refused:
        raise
    except Exception as e:
        reason = getattr(e, "reason", None) or "error"
        return None, {"reason": str(reason), "detail": str(e) if reason != "error" else f"{type(e).__name__}: {e}"}


def montecarlo(name: str, specs: dict[str, dict[str, Any]], n: int, seed: int, base: dict[str, float]) -> dict[str, Any]:
    keys = list(specs)
    lhs = qmc.LatinHypercube(d=max(1, len(keys)), seed=seed).random(n)
    samples = []
    for row in lhs:
        values = {**base, **{k: _sample(specs[k], float(row[i])) for i, k in enumerate(keys)}}
        outputs, reason = _attempt(name, values)
        samples.append({"inputs": values, "outputs": outputs, "infeasible": reason})
    return {"n": n, "seed": seed, "samples": samples}


# ── the run's tables (OF-BLD-019 §2.1) ─────────────────────────────────

# The units of what the tables hold are BioSTEAM's, written into every run
# as `tableUnits` (flowsheets/shelf.py's TABLE_UNITS; demo.py's stand-in
# claims the same). D8's words when the diagram cannot be drawn here:
NO_GRAPHVIZ = ("Graphviz is not installed here; the diagram draws on a host that has it "
               "(brew install graphviz on the Mini). The units are listed in run order.")


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


def stream_table(system: Any) -> list[dict[str, Any]]:
    """Every stream of the system, in the order its units run: where it comes
    from and goes, its phase, temperature, pressure, total mass flow and the
    mass flow of each component that flows."""
    rows = []
    for s in system.streams:
        ids = s.chemicals.IDs
        flows = {i: float(m) for i, m in zip(ids, s.mass) if m}
        rows.append({
            "id": s.ID, "source": _id(s.source), "sink": _id(s.sink), "phase": str(s.phase),
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
            "ins": [s.ID for s in u.ins if s], "outs": [s.ID for s in u.outs if s],
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
        if v is None or (key in ("otherVariable", "coproductCredits") and v == 0.0):
            continue
        label, reads = LINE_WORDS[key]
        lines.append({"key": key, "label": label, "usdPerYear": v, "perUnit": v / per if per else None, "reads": reads})
    out["lines"] = lines
    return out


def diagram(system: Any) -> dict[str, Any]:
    """The flowsheet as SVG text when Graphviz's dot is here (D8); else
    None and the words why."""
    if not shutil.which("dot"):
        return {"diagram": None, "diagramNote": NO_GRAPHVIZ}
    try:
        svg = system.diagram(format="svg", display=False).pipe(format="svg").decode("utf-8")
    except Exception as e:  # Graphviz is here and could not draw it: say so, list the units
        return {"diagram": None, "diagramNote": f"Graphviz could not draw this flowsheet here ({type(e).__name__}); "
                                               "the units are listed in run order."}
    return {"diagram": svg, "diagramNote": None}


def tables(module: Any, b: Any) -> dict[str, Any]:
    """Every table of the base case, read from the objects it left."""
    parts = module.parts(b) if hasattr(module, "parts") else {"system": b}
    system = parts["system"]
    tea = parts.get("tea")
    units = tea.units if tea is not None else system.units
    return {
        "tablesSource": f"BioSTEAM {version('biosteam')}, thermosteam {version('thermosteam')}",
        "tea": tea_breakdown(parts),
        "streams": stream_table(system),
        "units": unit_table(system),
        "utilities": utility_duties(units, "the units the TEA costs" if tea is not None else "every unit of the system"),
        **diagram(system),
        "unitOrder": [u.ID for u in system.units],
        "tableUnits": TABLE_UNITS,
    }


def run(name: str, base: dict[str, float], specs: dict[str, dict[str, Any]], samples: int, seed: int,
        axes: dict[str, list[float]] | None = None) -> dict[str, Any]:
    """One whole run: the base case and its tables, read before any other
    case moves the objects; then the grid, when one is asked; then the
    samples, Latin hypercube and seeded, as `montecarlo`."""
    module, b = built(name)
    try:
        base_out, base_infeasible = evaluate(name, base), None
    except Refused:
        raise
    except Exception as e:  # the base case cannot be held: said as the service says a worker error
        base_out, base_infeasible = None, f"{type(e).__name__}: {e}"
    out_tables = tables(module, b) if base_out is not None else None
    out_grid = grid(name, axes, base) if axes else None
    mc = montecarlo(name, specs, samples, seed, base) if samples else {"n": 0, "seed": seed, "samples": []}
    return {"base": base_out, "baseInfeasible": base_infeasible, "tables": out_tables, "grid": out_grid, "montecarlo": mc}


def _op_run(args):
    return run(str(args["flowsheet"]), dict(args.get("base") or {}), dict(args.get("specs") or {}),
               int(args.get("samples", 0)), int(args.get("seed", 0)), args.get("axes") or None)


def _op_evaluate(args):
    return evaluate(str(args["flowsheet"]), dict(args.get("values") or {}))


def _op_grid(args):
    return grid(str(args["flowsheet"]), dict(args["axes"]), dict(args.get("base") or {}))


def _op_montecarlo(args):
    return montecarlo(str(args["flowsheet"]), dict(args["specs"]), int(args.get("n", 500)), int(args.get("seed", 0)),
                      dict(args.get("base") or {}))


def _op_benchmark(args):
    from openferment_core.flowsheets import cornstover_benchmark

    return cornstover_benchmark.run()


HANDLERS = {"evaluate": _op_evaluate, "grid": _op_grid, "montecarlo": _op_montecarlo, "benchmark": _op_benchmark,
            "run": _op_run}

if __name__ == "__main__":
    serve(HANDLERS, name="proforma")
