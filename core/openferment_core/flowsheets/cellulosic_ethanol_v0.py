"""Cellulosic ethanol, version 0: openFerment's first flowsheet of its own,
composed from the `biorefineries.cellulosic` factories (ADR-004; execution
prompt §4.4, §8.4).

The plant is built by its recipe (`recipes/cellulosic_ethanol_v0/load.py`,
the SFF toolkit's model-directory shape): the package's own composition with
the pretreatment and the fermentation kind chosen. It runs through the
library plant runner (workers/library_plants.py) as any library plant does:
built afresh, its parameters read back, a person's values set, simulated,
priced, read back again, exported to SFF with its recipe embedded.

    configuration  "<pretreatment>, <fermentation>": dilute acid (the
                   package's), hot water, AFEX or alkaline; IB or SCF. The
                   package's own composition is "dilute acid, IB"

NO NUMBER IS TYPED HERE. Every value is the package's, read back from the
built plant (`parameters`): the feed's flow, price, moisture and dry
composition, each component a share of the dry mass; the solids loading
each mixer of the package holds; every conversion of every reaction set the
package's cellulosic process units carry (pretreatment, saccharification,
seed train, co-fermentation and its losses), named by its reaction; each such
unit's residence times. The organism is the one the package's reactions grow
(`organisms`: the cell mass its seed train and co-fermentation make).

THE GATES. A person's values are checked before the plant runs (`finalize`):
the dry composition's shares sum to one, the moisture is a share below one,
and no reactant of a reaction set converts more than all of it (the
conversions of one reactant sum to at most one). A case BioSTEAM finds
infeasible (`InfeasibleRegion`) is refused with BioSTEAM's words, a receipt
naming the unit, never a number. A warm plant returns to the same answer when
it is set back (A→B→A; `settle` empties the recycles and the TEA's sales
guess before each case).

Imported by the Proforma worker alone (BioSTEAM is imported here).
"""
from __future__ import annotations

import importlib.util
from importlib.metadata import version
from pathlib import Path
from typing import Any

import biosteam as bst
import numpy as np
import thermosteam as tmo

from ..workers.library_plants import Param, Plant, Refused, writable

NAME = "cellulosic_ethanol_v0"
RECIPE_DIR = Path(__file__).with_name("recipes") / NAME
TITLE = "Corn stover to ethanol, composed from biorefineries.cellulosic"
COMPOSED_FROM = "biorefineries.cellulosic"
# A share's sum is held to one within this: people type rounded shares. A
# precision of the check, not a quantity of the process.
SHARE_SUM_TOLERANCE = 1e-6
# A reactant converts at most all of itself; BioSTEAM's own check allows its
# float's rounding.
CONVERSION_SUM_TOLERANCE = 1e-12


def recipe() -> Any:
    """The recipe's `load.py`, loaded by its path as the SFF toolkit loads it."""
    spec = importlib.util.spec_from_file_location(f"sff_model_{NAME}", RECIPE_DIR / "load.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RECIPE = recipe()
CONFIGURATIONS = [f"{p}, {f}" for p in _RECIPE.PRETREATMENTS for f in _RECIPE.FERMENTATIONS]
DEFAULT_CONFIGURATION = ", ".join(_RECIPE.PACKAGE_DEFAULT)


def _kinds(configuration: str | None) -> tuple[str, str]:
    configuration = configuration or DEFAULT_CONFIGURATION
    if configuration not in CONFIGURATIONS:
        raise Refused(f"{NAME} has no configuration {configuration!r}; it has {', '.join(CONFIGURATIONS)}")
    pretreatment, fermentation = configuration.split(", ")
    return pretreatment, fermentation


def _package_units() -> tuple[type, ...]:
    """The package's cellulosic process unit classes: the units whose
    reactions, residence times and loadings a person may set here. The
    facilities' (wastewater, boiler) stay the package's."""
    from biorefineries.cellulosic import units

    return tuple(v for v in vars(units).values() if isinstance(v, type) and issubclass(v, bst.Unit)
                 and v.__module__ == units.__name__)


def build(configuration: str | None) -> Plant:
    """The plant built and simulated through the recipe: called inside the
    worker's `package_defaults()`."""
    pretreatment, fermentation = _kinds(configuration)
    try:
        system, tea = _RECIPE.create_system(pretreatment, fermentation)
        system.simulate()
    except bst.exceptions.InfeasibleRegion as e:
        raise Refused(f"{NAME} {configuration or DEFAULT_CONFIGURATION} is infeasible here (BioSTEAM's InfeasibleRegion): "
                      f"{e}") from e
    except Exception as e:
        raise Refused(f"{NAME} {configuration or DEFAULT_CONFIGURATION} could not be built under biosteam "
                      f"{version('biosteam')}: {type(e).__name__}: {e}") from e
    feedstock = next(s for s in system.feeds if s.ID == "cornstover")
    product = next(s for s in system.products if s.ID == "ethanol")
    import sys

    module = sys.modules[__name__]
    return Plant(NAME, configuration or DEFAULT_CONFIGURATION, module, None, system, tea, feedstock, product,
                 {"system": "the recipe's composition of the package's factories",
                  "tea": "biorefineries.tea.create_cellulosic_ethanol_tea, over the units the package's Biorefinery counts "
                         "outside the battery limits",
                  "feedstock": "the package's cornstover stream", "product": "the package's ethanol stream"},
                 flowsheet=module)


# ── parameters ─────────────────────────────────────────────────────────


def reaction_sets(system: Any) -> list[tuple[Any, str, Any]]:
    """Every parallel reaction set the package's process units carry, as
    (unit, attribute, set): a set that is a view of a larger one is left out,
    so each conversion is offered once."""
    classes = _package_units()
    found: list[tuple[Any, str, Any]] = []
    for unit in system.units:
        if not isinstance(unit, classes):
            continue
        sets = [(name, v) for name, v in vars(unit).items() if isinstance(v, tmo.reaction.ParallelReaction)]
        for name, rxn in sorted(sets, key=lambda nv: -nv[1].X.size):
            if any(np.shares_memory(rxn.X, kept.X) for u, _, kept in found if u is unit):
                continue
            found.append((unit, name, rxn))
    return found


def _equation(rxn: Any, i: int) -> str:
    """A reaction of a set, as thermosteam writes its stoichiometry."""
    from thermosteam.reaction._reaction import get_stoichiometric_string

    return get_stoichiometric_string(rxn._stoichiometry[i], rxn._phases, rxn.chemicals)


def _composition(p: Plant) -> tuple[float, dict[str, float]]:
    fs = p.feedstock
    water = float(fs.imass["Water"])
    dry = float(fs.F_mass) - water
    shares = {c.ID: float(fs.imass[c.ID]) / dry for c in fs.chemicals if c.ID != "Water" and fs.imass[c.ID] > 0}
    return water / float(fs.F_mass), shares


def parameters(p: Plant) -> list[Param]:
    """What a person may set on the composed plant beyond what every library
    plant reads back: the feed's moisture and dry composition, the solids
    loadings, the conversions and the residence times."""
    pending = p.pending
    out: list[Param] = []
    moisture, shares = _composition(p)

    def hold(key: str):
        return lambda v: pending.__setitem__(key, v)

    out.append(Param("feed.moisture", "Feed moisture, a share of its mass", "feedstock", "", moisture, hold("feed.moisture"),
                     "water in the package's cornstover stream, as a share of its mass", "number"))
    out += [Param(f"feed.dry.{c}", f"{c}, a share of the dry feed", "feedstock", "", share, hold(f"feed.dry.{c}"),
                  f"{c} in the package's cornstover stream, as a share of its dry mass", "number")
            for c, share in shares.items()]
    for unit in p.system.units:
        for attr in ("solids_loading", "insoluble_solids_loading"):
            v = getattr(unit, attr, None)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(Param(f"unit.{unit.ID}.{attr}", f"{unit.ID}: {attr.replace('_', ' ')}", f"unit {unit.ID}", "",
                                 float(v), lambda x, u=unit, a=attr: setattr(u, a, x),
                                 f"{type(unit).__name__}.{attr}, as the package's factory sets it", "number"))
    classes = _package_units()
    for unit in p.system.units:
        if not isinstance(unit, classes):
            continue
        for name in _residence_times(unit):
            v = getattr(unit, name)
            settable = writable(unit, name)
            out.append(Param(f"unit.{unit.ID}.{name}", f"{unit.ID}: residence time {name}", f"unit {unit.ID}", "hr",
                             float(v), (lambda x, u=unit, a=name: setattr(u, a, x)) if settable else None,
                             f"{type(unit).__name__}.{name}, " + ("as the package sets it" if settable else
                                                                  "computed by the unit: read back, not set"),
                             "number"))
    for unit, attr, rxn in reaction_sets(p.system):
        for i in range(rxn.X.size):
            out.append(Param(f"rxn.{unit.ID}.{attr}.{i}", f"{unit.ID} {attr}: {_equation(rxn, i)}", f"unit {unit.ID}", "",
                             float(rxn.X[i]), lambda x, r=rxn, j=i: r.X.__setitem__(j, x),
                             f"the conversion of {rxn.reactants[i]} in {type(unit).__name__}.{attr}, as the package sets it",
                             "number"))
    return out


def _residence_times(unit: Any) -> list[str]:
    """A unit's residence times: every number it answers to a name that
    begins `tau`, its own or its class's (the package's IB reactor holds
    `tau_saccharification` and `tau_cofermentation` on its class)."""
    out = []
    for name in sorted(n for n in dir(unit) if n.startswith("tau")):
        try:
            v = getattr(unit, name)
        except Exception:  # noqa: BLE001 — a name the unit cannot answer is not one of its times
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(name)
    return out


def finalize(p: Plant) -> None:
    """A person's values checked and laid on together: the feed's
    composition from its shares and moisture, and each reaction set's
    conversions, one reactant at a time. Refused in words when a share sum
    or a conversion sum cannot hold."""
    pending = p.pending
    if pending:
        moisture, shares = _composition(p)
        moisture = pending.get("feed.moisture", moisture)
        shares = {c: pending.get(f"feed.dry.{c}", s) for c, s in shares.items()}
        if not 0 <= moisture < 1:
            raise Refused(f"the feed's moisture is a share of its mass, at least none and below all; {moisture} is not")
        if any(s < 0 for s in shares.values()):
            raise Refused("a component's share of the dry feed is not negative")
        total = sum(shares.values())
        if abs(total - 1) > SHARE_SUM_TOLERANCE:
            raise Refused(f"the dry feed's shares sum to {total:.9g}; they sum to one")
        fs = p.feedstock
        F = float(fs.F_mass)
        fs.empty()
        for c, s in shares.items():
            fs.imass[c] = F * (1 - moisture) * s
        fs.imass["Water"] = F * moisture
        pending.clear()
    for unit, attr, rxn in reaction_sets(p.system):
        sums: dict[str, float] = {}
        for i, reactant in enumerate(rxn.reactants):
            if rxn.X[i] < 0:
                raise Refused(f"{unit.ID} {attr}: the conversion of {reactant} by {_equation(rxn, i)} is not negative")
            sums[reactant] = sums.get(reactant, 0.0) + float(rxn.X[i])
        over = {r: s for r, s in sums.items() if s > 1 + CONVERSION_SUM_TOLERANCE}
        if over:
            r, s = next(iter(over.items()))
            raise Refused(f"{unit.ID} {attr}: the conversions of {r} sum to {s:.9g}; a reactant converts at most all of "
                          "itself")


def settle(p: Plant) -> None:
    """Before a case runs on a warm plant: the recycles emptied and the TEA's
    guess of its sales cleared, so the case's answer does not lean on the
    last one's (A→B→A)."""
    p.system.empty_recycles()
    if p.tea is not None:
        p.tea._sales = 0


# ── what a run reads back ──────────────────────────────────────────────


def organisms() -> list[dict[str, str]]:
    """The organism the plant ferments with, as the recipe declares it
    (`extended_metadata.yaml`, `microorganisms`): a BioSTEAM system names no
    host, so it is declared beside the recipe, as the SFF toolkit's own
    recipes declare theirs. The package's seed train and co-fermentation
    reactions grow its cell mass (`Z_mobilis`), and the read-back lists them."""
    return [dict(m) for m in authored().get("microorganisms") or []]


def authored() -> dict[str, Any]:
    """What the recipe declares for the SFF file's metadata, as the toolkit's
    runner reads it: title, designers, the source's DOI, the organism."""
    import yaml

    return yaml.safe_load((RECIPE_DIR / "extended_metadata.yaml").read_text(encoding="utf-8")) or {}


def read_back(p: Plant) -> dict[str, Any]:
    """Every process unit's mode (batch or continuous), temperature,
    residence times, vessel count and conversions; the utility prices and
    the plant cost index the case used; the versions."""
    from . import utility_settings

    units = []
    classes = _package_units()
    sets: dict[str, list] = {}
    for unit, attr, rxn in reaction_sets(p.system):
        sets.setdefault(unit.ID, []).append({"set": attr, "reactions": [
            {"equation": _equation(rxn, i), "reactant": rxn.reactants[i], "X": float(rxn.X[i])}
            for i in range(rxn.X.size)]})
    for unit in p.system.units:
        if not isinstance(unit, classes):
            continue
        row: dict[str, Any] = {"id": unit.ID, "class": type(unit).__name__,
                               "mode": "batch" if isinstance(unit, bst.BatchBioreactor) else "continuous"}
        for attr in ("T", *_residence_times(unit), "N", "V"):
            v = getattr(unit, attr, None)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                row[attr] = float(v)
        design_n = unit.design_results.get("Number of reactors") if hasattr(unit, "design_results") else None
        if isinstance(design_n, (int, float)):
            row["vessels"] = float(design_n)
        row["reactionSets"] = sets.get(unit.ID, [])
        units.append(row)
    tea = p.tea
    return {
        "configuration": p.configuration,
        "units": units,
        "organisms": organisms(),
        "tea": {"class": type(tea).__name__, "IRR": float(tea.IRR), "duration": list(tea.duration),
                "depreciation": str(tea.depreciation), "income_tax": float(tea.income_tax),
                "operating_days": float(tea.operating_days)} if tea is not None else None,
        "utilities": utility_settings(p.system.units),
        "versions": {d: version(d) for d in ("biosteam", "thermosteam", "biorefineries")},
    }


def outputs(p: Plant) -> dict[str, Any]:
    """The minimum ethanol selling price, per kilogram and per gallon (the
    package's own density per gallon), and what the plant makes of its feed."""
    from biorefineries.cellulosic import biorefinery as package

    ethanol, feed = p.product, p.feedstock
    price = float(p.tea.solve_price(ethanol)) if p.tea is not None else None
    dry = float(feed.F_mass) - float(feed.imass["Water"])
    return {
        "mespUsdPerKg": price,
        "mespUsdPerGal": price * float(package.ethanol_density_kggal) if price is not None else None,
        "ethanolKgPerH": float(ethanol.F_mass),
        "dryFeedKgPerH": dry,
        "ethanolKgPerKgDryFeed": float(ethanol.F_mass) / dry if dry else None,
        "ethanolDensityKgPerGal": float(package.ethanol_density_kggal),
    }
