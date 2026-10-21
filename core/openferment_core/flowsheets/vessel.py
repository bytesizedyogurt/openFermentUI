"""fermOS's vessel, designed by BioSTEAM (OF-BLD-020 §4.1, D7, E.3‴).

Not a shelf flowsheet (it is not in `KNOWN`): one vessel, built afresh for
every design by the Proforma worker's `vessel_specs` and `vessel_design` ops,
which call `specs(kind)` and `design(spec)` here. BioSTEAM is imported in
this package and in workers/proforma_worker.py alone (test_workers).

    aerobic     `bst.AeratedBioreactor`: a stirred tank (BioSTEAM's 'Riet'
                kLa correlation) or a bubble column ('Dewes'), with its
                compressor, air cooler, agitator and recirculation loop
    anaerobic   `bst.NRELAnaerobicBatchBioreactor`, the NREL batch fermenter
                the ethanol flowsheet uses, with no gas inlet

THE OXYGEN DEMAND IS THE REACTION'S. The aerated class takes no oxygen
demand: the oxygen its `reactions` consume is its uptake, and it sizes the
air so that the oxygen it transfers, averaged over the cycle, meets that
uptake (`Q_O2_consumption` is a forced heat per oxygen consumed, not a
demand). So the growth reaction is built from what the simulation made —
glucose and oxygen to cells, ethanol, carbon dioxide and water, closed on
thermosteam's formulas — and its oxygen is scaled so that the uptake
BioSTEAM sizes for is the simulation's peak or its batch average, as the
request's `oxygenBasis` says (D7 asks for the peak). The scale is found by
designing once as balanced, reading the uptake per working volume the
reaction asks of the vessel (`get_OUR` over the vessels' working volume
while they react, whether or not BioSTEAM aerated it: the class sizes no air
at or below a floor its `_run` names, which a balanced reaction in a small
vessel can fall under), and designing again (a fresh unit each time); only a
scaled reaction still under that floor is designed with no air (OF-BLD-020
§4.R). With the scale above one the vessel's outlets carry that oxygen as
consumed; the broth the simulation ends with is its own end state, not this
unit's outlet.

THE HEAT. BioSTEAM's duty is its `_get_duty`: the enthalpy and heats of
formation out less in, or, when a person forces a heat per oxygen
(`Q_O2_consumption`), that heat times the oxygen the vessel consumed, which
is the scaled reaction's (`heat.method` says which). Beside it, D7's
cross-check after Cooney: the heat per oxygen of `biorefineries.cane` times
the oxygen the SIMULATION took up, the trapezoid integral of its uptake over
the batch to harvest, times each vessel's working volume and the vessels,
over the cycle (§4.R: never the reaction's own oxygen, which would agree with
BioSTEAM by construction).

THE OXYGEN BALANCE IS COMPUTED AFTER, against the simulated uptake over
time: OTR = kLa · ΔC, with kLa the class's own (`get_kLa`, by its
correlation) and ΔC the log-mean driving force the class sizes with, between
the sparged gas and the vent, each saturation from `aeration.C_O2_L` at the
vessel's temperature and the gas's oxygen partial pressure, the broth at
θ · C* (`theta_O2`). The hours the simulated uptake rises above it are named.

NOTHING HERE IS A PROCESS NUMBER. Every default is BioSTEAM's, read from its
signatures, class attributes or a probe instance (some live only in `_init`
bodies), or the corn plant's TEA's (its operating days, for a plant scale);
every value a design uses arrives in its spec. The heat cross-check per
oxygen consumed is the one `biorefineries.cane`'s aerated fermentations pass
BioSTEAM (their `Q_O2_consumption` default, which cites Benz), read from that
signature. The numbers in this file are structural: zero, one, and the
named iteration limits and tolerances below.

BioSTEAM ALSO NEEDS (measured by the spike, OF-BLD-020 §4.1's task):
- the feed at the vessel's own temperature, else the stirred-tank family's
  duty includes heating it;
- a fresh unit for every design: the NREL vessel never empties its vent, so
  re-simulating one unit doubles its carbon dioxide;
- `V_max` for the NREL vessel, which has no default: the ethanol flowsheet's,
  `bst.AnaerobicBioreactor.V_max_default`, read and named;
- on the stirred-tank family, `N` set on the object after construction with
  `V_max` cleared (the constructor re-applies `V_max_default`), and one
  vessel only with a loading time (else a division by zero);
- `kW_per_m3 = 0` for a bubble column, else it still costs an agitator.
"""
from __future__ import annotations

import inspect
import itertools
import math
from importlib import import_module
import re
import warnings
from importlib.metadata import version
from typing import Any

import biosteam as bst
import numpy as np
import thermosteam as tmo
from biosteam.units.design_tools import aeration
from thermosteam.units_of_measure import convert

from . import utility_settings

# Structural constants: how a design is solved, not what is designed.
# The feed's water is found by the secant method to this relative tolerance
# of its volume, within this many steps.
FEED_RTOL = 1e-12
FEED_STEPS = 50
# A simulated uptake above the vessel's transfer counts as short only past
# this relative margin, so a vessel sized exactly for the peak reports no
# zero-length interval at it.
SHORT_RTOL = 1e-9

AEROBIC, ANAEROBIC = "aerobic", "anaerobic"
STIRRED, BUBBLE = "Stirred tank", "Bubble column"
UNIT_ID = "R1"
# The yeast program's chemicals, as the ethanol flowsheet makes them, and the
# names this file reads in them.
CHEMICALS = "biorefineries.corn.create_chemicals"
GLUCOSE, ETHANOL, CELLS, WATER, O2, CO2 = "Glucose", "Ethanol", "Yeast", "Water", "O2", "CO2"

_SEQ = itertools.count()


class Refused(ValueError):
    """A design that cannot be made as asked, in words."""


# ── library defaults, read ─────────────────────────────────────────────


def _cls(kind: str) -> Any:
    if kind == AEROBIC:
        return bst.AeratedBioreactor
    if kind == ANAEROBIC:
        return bst.NRELAnaerobicBatchBioreactor
    raise Refused(f"a vessel is {AEROBIC} or {ANAEROBIC}; {kind!r} is neither")


def _signature(fn: Any) -> dict[str, Any]:
    out = {}
    for name, p in inspect.signature(fn).parameters.items():
        if name == "self" or p.kind in (p.VAR_KEYWORD, p.VAR_POSITIONAL):
            continue
        out[name] = None if p.default is p.empty else p.default
    return out


def _plain(v: Any) -> Any:
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return str(v)


def _methods_in(fn: Any) -> set[str]:
    """The kLa correlations a method of the class actually calls, read from
    its source: the class answers `get_kLa` for these alone and raises for
    every other registered one."""
    return set(re.findall(r"aeration\.(\w+)", inspect.getsource(fn)))


def operating_hours() -> tuple[float, str]:
    """The hours a year the corn plant's TEA operates, read from the package
    (its `default_tea_parameters`), in hours by thermosteam's units."""
    # By module path: once the corn plant has loaded in this worker, the
    # package's attribute `tea` is that plant's TEA object, not this module.
    tea = import_module("biorefineries.corn.tea")
    days = tea.default_tea_parameters["operating_days"]
    return float(convert(days, "day", "hr")), (
        f"biorefineries.corn's default_tea_parameters operating_days ({_plain(days):g} days a year), in hours: the TEA "
        "the ethanol flowsheet prices with")


def heat_per_oxygen() -> tuple[float, str]:
    """The heat released per oxygen consumed, kJ per kmol, that
    `biorefineries.cane`'s aerated fermentations force on BioSTEAM (their
    `Q_O2_consumption` default), read from the signature."""
    cane = import_module("biorefineries.cane.units")  # by module path, as above
    q = inspect.signature(cane.AeratedFermentation._init).parameters["Q_O2_consumption"].default
    return float(q), ("biorefineries.cane's AeratedFermentation passes BioSTEAM this forced duty per oxygen consumed "
                      "(its Q_O2_consumption default, kJ/kmol; its comment cites Benz, Bioreactor Design for Chemical "
                      "Engineers, Chem. Eng. Progress 2011): the rule that heat follows oxygen uptake (Cooney, Wang and "
                      "Mateles, Biotechnol. Bioeng. 1969), a convention set beside BioSTEAM's own duty as a cross-check")


def aeration_floor() -> tuple[float | None, str]:
    """The oxygen uptake, mol/s, at or below which `AeratedBioreactor` sizes
    no air, read from its `_run` (None when this BioSTEAM words it
    otherwise)."""
    m = re.search(r"if\s+OUR\s*<=\s*([0-9.eE+-]+)\s*:", inspect.getsource(bst.AeratedBioreactor._run))
    return (float(m.group(1)) if m else None), (
        "AeratedBioreactor._run sizes no air for an oxygen uptake at or below it (read from its code)")


def refusals(cls: Any) -> dict[str, dict[str, Any]]:
    """What the class's own setters refuse, read from their code: for N and
    V_max, the value a property's setter raises at or below. The NREL vessel
    refuses N and V_max at or below one; the aerated class's are plain
    attributes, and refuse nothing."""
    out: dict[str, dict[str, Any]] = {}
    for name in ("N", "V_max"):
        attr = inspect.getattr_static(cls, name, None)
        if not isinstance(attr, property) or attr.fset is None:
            continue
        m = re.search(rf"if\s+{name}\s*<=\s*([0-9.eE+-]+)\s*:\s*raise\s+ValueError", inspect.getsource(attr.fset))
        if m:
            out[name] = {"atOrBelow": float(m.group(1)),
                         "from": f"{cls.__name__}.{name}'s setter raises ValueError at or below it (read from its code)"}
    return out


def cost_index() -> tuple[float, int | None]:
    """BioSTEAM's plant cost index as set now, and the year its source
    comment says its default is of (None when the index is not that
    default)."""
    m = re.search(r"defaults to (?P<index>[0-9.]+) at (?P<year>\d{4})", inspect.getsource(bst))
    year = int(m.group("year")) if m and math.isclose(float(m.group("index")), float(bst.CE)) else None
    return float(bst.CE), year


def specs(kind: str) -> dict[str, Any]:
    """What the vessel class takes and its own defaults, read at import:
    the signatures (the aerated class forwards the stirred-tank family's),
    the class attributes and a probe instance (defaults set only inside
    `_init`), the choices the class runs, and where each default was read."""
    from ..workers.proforma_worker import package_defaults

    cls = _cls(kind)
    params: dict[str, dict[str, Any]] = {}
    sig = _signature(cls._init)
    if cls is bst.AeratedBioreactor:
        sig.update({k: v for k, v in _signature(bst.AbstractStirredTankReactor._init).items() if k not in sig})
    out: dict[str, Any] = {"kind": kind, "unitClass": cls.__name__}
    with package_defaults():
        _fresh_flowsheet()
        bst.settings.set_thermo(_chemicals())
        probe = _probe(cls)
        for name, default in sig.items():
            attr = f"{name}_default"
            plain_attr = next((k.__dict__[name] for k in cls.__mro__ if name in k.__dict__), None)
            if default is not None:
                value, where = default, f"{cls.__name__}._init's signature"
            elif getattr(cls, attr, None) is not None:
                value, where = getattr(cls, attr), f"{cls.__name__}.{attr}"
            elif plain_attr is not None and isinstance(plain_attr, (int, float, str)):
                value, where = plain_attr, f"{cls.__name__}.{name}"
            elif _plain(getattr(probe, name, None)) is not None and not callable(getattr(probe, name, None)):
                value, where = getattr(probe, name), f"a {cls.__name__} built with nothing set (its _init sets it)"
            else:
                value, where = None, f"{cls.__name__}._init's signature: None, which the class reads at run time"
            params[name] = {"default": _plain(value), "from": where}
        if cls is bst.NRELAnaerobicBatchBioreactor:
            params["V_max"] = {"default": _plain(bst.AnaerobicBioreactor.V_max_default), "from": (
                "bst.AnaerobicBioreactor.V_max_default: the NREL vessel has no default of its own, and the ethanol "
                "flowsheet passes BioSTEAM's anaerobic bioreactor's")}
        if cls is bst.AeratedBioreactor:
            registered = {key: fn.__name__ for key, fn in aeration.kLa_methods.items()}
            runs, solves = _methods_in(cls.get_kLa), _methods_in(cls.get_agitation_power)
            out["designs"] = {}
            for design in aeration.kLa_method_names:
                each = _probe(cls, design=design)  # what the class makes of each design when nothing else is set
                out["designs"][design] = {
                    "method": next(m for (d, m), fn in aeration.kLa_methods.items() if fn is each.kLa and d == design),
                    "optimize_power": bool(each.optimize_power),
                    "kW_per_m3": _plain(each.kW_per_m3),
                    "runs": [m for (d, m), fn in registered.items() if d == design and fn in runs],
                    "solvesPower": [m for (d, m), fn in registered.items() if d == design and fn in solves],
                    "registered": list(aeration.kLa_method_names[design]),
                }
            out["defaultDesign"] = BUBBLE if cls.kW_per_m3_default == 0 else STIRRED
            from biosteam.units.design_tools.pressure_vessel import allowed_vessel_types
            from biosteam.units.design_tools.specification_factors import pressure_vessel_material_factors

            out["choices"] = {
                "vessel_material": list(pressure_vessel_material_factors),
                "vessel_type": sorted(t for t in allowed_vessel_types if t),
                "heat_exchanger_configuration": _settable(probe, sorted(cls.heat_exchanger_configurations)),
            }
            q, why = heat_per_oxygen()
            out["heatPerO2"], out["heatPerO2From"] = q, why
            out["aerationFloorMolPerS"], out["aerationFloorFrom"] = aeration_floor()
        out["refuses"] = refusals(cls)
        hours, hours_from = operating_hours()
        ce, year = cost_index()
    out.update(parameters=params, biosteam=version("biosteam"), thermosteam=version("thermosteam"),
               biorefineries=version("biorefineries"), chemicals=CHEMICALS, operatingHours=hours,
               operatingHoursFrom=hours_from, costIndex=ce, costIndexYear=year)
    return out


def _settable(probe: Any, configurations: list[str]) -> list[str]:
    """The heat exchanger configurations the class takes: each set on a
    probe, and the ones its setter refuses ('not implemented') left out."""
    ok = []
    for c in configurations:
        try:
            probe.heat_exchanger_configuration = c
        except AttributeError:
            continue
        ok.append(c)
    return ok


def _chemicals() -> Any:
    from biorefineries import corn

    return corn.create_chemicals()


def _fresh_flowsheet() -> None:
    # One flowsheet per design, so nothing of an earlier one is found by ID;
    # package_defaults() puts the worker's own back afterwards.
    bst.main_flowsheet.set_flowsheet(bst.Flowsheet(f"fermos_vessel_{next(_SEQ)}"))


def _probe(cls: Any, **kwargs: Any) -> Any:
    """A unit built with nothing set but what `kwargs` name, to read the
    defaults its `_init` sets; never simulated."""
    feed = bst.Stream(None, Water=1, units="kg/hr")
    if cls is bst.AeratedBioreactor:
        return cls(None, ins=[feed, bst.Stream(None, phase="g")], outs=(None, None), **kwargs)
    return cls(None, ins=feed, outs=(None, None), V_max=bst.AnaerobicBioreactor.V_max_default, **kwargs)


# ── the design ─────────────────────────────────────────────────────────


def _T_default(cls: Any) -> float:
    T = getattr(cls, "T_default", None)
    if T is not None:
        return float(T)
    return float(inspect.signature(cls._init).parameters["T"].default)


def _feed(conc: dict[str, float], F_vol: float, T: float) -> Any:
    """A liquid stream with the given grams per litre of the mixture (by
    thermosteam's own volume of it), water making up the litre, scaled to
    F_vol (m³ per hour)."""
    s = bst.Stream("feed", T=T, units="kg/hr")
    for k, v in conc.items():
        if v:
            s.imass[k] = v  # kg in one cubic metre of the mixture: g per litre
    if s.F_vol >= 1:
        raise Refused("the start of the batch holds more than a litre of solids and solutes in a litre of broth, by "
                      "thermosteam's volumes")

    def gap(w: float) -> float:
        s.imass[WATER] = w
        return s.F_vol - 1

    # Secant from no water and from water filling the litre as if alone.
    w0, w1 = 0.0, float(tmo.Chemical(WATER).rho("l", T, s.P))
    f0, f1 = gap(w0), gap(w1)
    for _ in range(FEED_STEPS):
        if abs(f1) <= FEED_RTOL or f1 == f0:
            break
        w0, w1, f0 = w1, w1 - f1 * (w1 - w0) / (f1 - f0), f1
        f1 = gap(w1)
    if abs(f1) > FEED_RTOL:
        raise Refused("the feed's water did not settle on a litre of broth")
    s.imass[WATER] = w1
    s.scale(F_vol / s.F_vol)
    return s


def _reactions(chems: Any, kind: str, start: dict[str, float], made: dict[str, float], used: float) -> tuple[Any, dict]:
    """The reaction set from what the batch made per litre (cells and
    ethanol, g L⁻¹) and the glucose it used (g L⁻¹), on thermosteam's
    formulas and molecular weights.

    aerobic    one reaction, Glucose + O2 → Yeast + Ethanol + CO2 + H2O, the
               cells and ethanol per glucose held at what was made per glucose
               used, oxygen, carbon dioxide and water closed by the atomic
               balance, at the share of the fed glucose used
    anaerobic  two in parallel on the fed glucose: Glucose → 2 Ethanol + 2 CO2
               for the ethanol made, and Glucose → Yeast + CO2 + H2O (closed by
               the atomic balance, no oxygen) for the cells made; glucose the
               batch used beyond what these two take (maintenance, by-products
               the family does not model) stays in the broth, said so
    """
    MW = {i: float(chems[i].MW) for i in (GLUCOSE, ETHANOL, CELLS, O2)}
    fed = start.get(GLUCOSE, 0.0)
    if not fed > 0:
        raise Refused("the batch starts with no glucose, so there is nothing for the vessel's reaction to use")
    if not 0 < used <= fed:
        raise Refused("the glucose the batch used must be above none and at most what it started with")
    cells, ethanol = max(made.get(CELLS, 0.0), 0.0), max(made.get(ETHANOL, 0.0), 0.0)
    notes: list[str] = []
    if kind == AEROBIC:
        products = [CELLS] + ([ETHANOL] if ethanol > 0 else [])
        r = tmo.Rxn(f"{GLUCOSE} + {O2} -> {' + '.join(products)} + {CO2} + {WATER}", reactant=GLUCOSE, X=used / fed)
        r.istoichiometry[CELLS] = cells / used * MW[GLUCOSE] / MW[CELLS]
        if ethanol > 0:
            r.istoichiometry[ETHANOL] = ethanol / used * MW[GLUCOSE] / MW[ETHANOL]
        r.correct_atomic_balance([GLUCOSE, *products])
        st = r.istoichiometry
        if not st[O2] < 0:
            raise Refused("what this batch made from its glucose closes the atomic balance without consuming oxygen "
                          "(more reduced than the glucose it came from), so the aerated vessel has no oxygen uptake to "
                          "size its air for")
        if any(st[i] < 0 for i in (CO2, WATER)):
            raise Refused("what this batch made from its glucose cannot close the atomic balance with carbon dioxide "
                          "and water as products")
        info = {"equation": str(r), "stoichiometry": {i: float(st[i]) for i in (GLUCOSE, O2, CELLS, ETHANOL, CO2, WATER)},
                "glucoseUsedShare": used / fed,
                "impliedYxo": float(st[CELLS] * MW[CELLS] / (-st[O2] * MW[O2])) if cells > 0 else None}
        return r, {**info, "notes": notes}
    ferm = tmo.Rxn(f"{GLUCOSE} -> 2 {ETHANOL} + 2 {CO2}", reactant=GLUCOSE, X=0, check_atomic_balance=True)
    grow = tmo.Rxn(f"{GLUCOSE} -> {CELLS} + {CO2} + {WATER}", reactant=GLUCOSE, X=0, correct_atomic_balance=True)
    glucose_mol = fed / MW[GLUCOSE]
    x_f = ethanol / MW[ETHANOL] / ferm.istoichiometry[ETHANOL] / glucose_mol
    x_g = cells / MW[CELLS] / grow.istoichiometry[CELLS] / glucose_mol
    if x_f + x_g > used / fed * (1 + SHORT_RTOL):
        raise Refused("the ethanol and cells this batch made need more glucose, by the two reactions' stoichiometry, "
                      "than the batch used")
    ferm.X, grow.X = x_f, x_g
    left = used - (x_f + x_g) * fed
    if left > used * SHORT_RTOL:
        notes.append(f"the batch used {left:.4g} g L⁻¹ more glucose than ethanol and cell formation take by their "
                     "stoichiometry (maintenance and by-products the family does not model); in the vessel it stays in "
                     "the broth unconverted, as the ethanol flowsheet leaves it")
    theoretical = float(ferm.istoichiometry[ETHANOL] * MW[ETHANOL] / (-ferm.istoichiometry[GLUCOSE] * MW[GLUCOSE]))
    return tmo.ParallelReaction([ferm, grow]), {
        "equation": f"{ferm} ∥ {grow}", "fermentationShare": x_f, "growthShare": x_g,
        "theoreticalEthanolYield": theoretical, "notes": notes}


def _short(ts: list[float], ys: list[float], level: float) -> list[list[float]]:
    """[[start, end], …]: where ys rises above level, ends interpolated."""
    out, start = [], None

    def cross(i: int) -> float:
        t0, y0, t1, y1 = ts[i - 1], ys[i - 1], ts[i], ys[i]
        return t0 + (level - y0) * (t1 - t0) / (y1 - y0) if y1 != y0 else t0

    for i, y in enumerate(ys):
        above = y > level * (1 + SHORT_RTOL)
        if above and start is None:
            start = ts[i] if i == 0 else cross(i)
        elif not above and start is not None:
            out.append([start, cross(i)])
            start = None
    if start is not None:
        out.append([start, ts[-1]])
    return out


def _build(cls: Any, spec: dict[str, Any], chems: Any, rxn: Any, F_vol: float) -> Any:
    _fresh_flowsheet()
    bst.settings.set_thermo(chems)
    params = dict(spec.get("params") or {})
    T = params.get("T", _T_default(cls))
    feed = _feed(spec["start"], F_vol, T)
    N = params.pop("N", None)
    one = spec["scale"].get("batchVolume") is not None
    kwargs = {k: v for k, v in params.items()}
    if cls is bst.NRELAnaerobicBatchBioreactor:
        if N is not None:
            kwargs["N"] = N
        else:
            kwargs.setdefault("V_max", bst.AnaerobicBioreactor.V_max_default)
        R = cls(UNIT_ID, ins=feed, outs=("vent", "broth"), tau=spec["tau"], reactions=rxn, **kwargs)
    else:
        if spec.get("design") is not None:
            kwargs["design"] = spec["design"]
        if kwargs.get("design") == BUBBLE and "kW_per_m3" not in kwargs:
            kwargs["kW_per_m3"] = 0  # else a bubble column still costs an agitator
        R = cls(UNIT_ID, ins=[feed, bst.Stream("air", phase="g")], outs=("vent", "broth"), tau=spec["tau"],
                reactions=rxn, **kwargs)
        if N is not None or one:
            R.V_max = None  # the constructor re-applies V_max_default, and N cannot stand beside it
            R.N = 1 if one else N
    return R


def _scale(spec: dict[str, Any], cls: Any, params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """The broth fed per hour, m³, from the plant scale or the batch volume."""
    sc = spec["scale"]
    plant, batch = sc.get("plantScale"), sc.get("batchVolume")
    if plant is None and batch is None:
        raise Refused("a vessel design needs plant_scale (tonnes of product a year) or batch_volume (one vessel's "
                      "working volume, m³); neither was given")
    if plant is not None and batch is not None:
        raise Refused("give plant_scale or batch_volume, not both: one sets how much broth the vessels take")
    if plant is not None:
        titre = sc.get("productTitre") or 0.0
        if not titre > 0:
            raise Refused("this batch ends with no product, so a plant scale in tonnes of product cannot size it; give "
                          "a batch volume")
        hours, hours_from = operating_hours()
        product = float(convert(plant, "metric_ton", "kg")) / hours  # kg h⁻¹
        return product / titre, {"operatingHours": hours, "operatingHoursFrom": hours_from,
                                 "productKgPerH": product, "how": "the product a year over the corn TEA's operating "
                                 "hours, over the titre at harvest (kg m⁻³)"}
    if cls is bst.NRELAnaerobicBatchBioreactor:
        raise Refused("a batch volume names one vessel, and BioSTEAM's NREL batch bioreactor sizes two or more (it "
                      "refuses one); for an anaerobic design give a plant scale")
    if params.get("N") is not None:
        raise Refused("a batch volume names one vessel's working volume; leave N to it, or give a plant scale")
    loading = params.get("loading_time")
    if loading is None:
        raise Refused("one vessel of a batch volume needs a loading time: BioSTEAM sizes a single vessel's schedule "
                      "with it (without one it divides by zero)")
    tau_0 = params.get("tau_0", cls.tau_0_default)
    cycle = spec["tau"] + tau_0 + loading
    return batch / cycle, {"cycleH": cycle, "how": "one vessel: the batch volume over its cycle (tau + tau_0 + "
                                                   "loading_time)"}


def _uptake_sized(R: Any) -> float:
    """The oxygen uptake the vessel's reaction asks of it, per working volume
    while it reacts, mmol L⁻¹ h⁻¹ (its reaction's, over the cycle): what
    BioSTEAM sizes the air for, read whether or not it aerated (the vessel's
    size is the liquid's, designed either way; §4.R)."""
    d = R.design_results
    op = R.tau / d["Batch time"]
    V_work = d["Reactor volume"] * R.V_wf
    return float(R.get_OUR() * convert(1, "hr", "s") / (d["Number of reactors"] * V_work * op))


def _made(cls: Any, spec: dict[str, Any], chems: Any, rxn: Any, F_vol: float) -> tuple[Any, list[str]]:
    """Build the unit and simulate it, a class that refuses its construction
    (the NREL vessel's N or V_max at or below one, say) refused in BioSTEAM's
    own words like any failure of its design (OF-BLD-020 §4.R)."""
    try:
        R = _build(cls, spec, chems, rxn, F_vol)
    except Refused:
        raise
    except Exception as e:  # BioSTEAM's own words
        raise Refused(f"BioSTEAM could not build this vessel: {type(e).__name__}: {e}") from None
    return R, _simulate(R)


def _simulate(R: Any) -> list[str]:
    """Simulate, and return what BioSTEAM warns of the design it settled on.
    The air-flow solve costs every trial on its way, each with its own cost
    warning; the last of each kind (its words with the numbers set aside) is
    the one the final design gave, and the one kept. (Designing the unit
    again to read its warnings afresh is no way round: the NREL vessel adds
    its heat utility a second time, measured.)"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            R.simulate()
        except Refused:
            raise
        except Exception as e:  # BioSTEAM's own words
            raise Refused(f"BioSTEAM could not design this vessel: {type(e).__name__}: {e}") from None
    last: dict[str, str] = {}
    for w in caught:
        text = re.sub(r"\x1b\[[0-9;]*m", "", f"{w.category.__name__}: {w.message}")
        last[re.sub(r"[0-9][0-9.,e+-]*", "#", text)] = text
    return sorted(last.values())


def design(spec: dict[str, Any]) -> dict[str, Any]:
    """One vessel design: built inside `package_defaults()` on BioSTEAM's
    default utility prices and cost index, simulated, every table read."""
    from ..workers.proforma_worker import package_defaults

    kind = spec["kind"]
    cls = _cls(kind)
    with package_defaults():
        chems = _chemicals()
        bst.settings.set_thermo(chems)
        bst.process_tools.default_utilities()
        bst.process_tools.default_CEPCI()
        params = dict(spec.get("params") or {})
        F_vol, scale_info = _scale(spec, cls, params)
        rxn, rinfo = _reactions(chems, kind, spec["start"], spec["made"], spec["used"])
        R, said = _made(cls, spec, chems, rxn, F_vol)
        oxygen = None
        if kind == AEROBIC:
            balanced = _uptake_sized(R)
            consumed_kmol_h = _kmol_h(R.get_OUR())
            target = spec.get("ourTarget")
            factor = 1.0
            if target is not None and balanced > 0:
                # The class sizes for its reaction's uptake: scale the
                # reaction's oxygen to the simulation's, and design again,
                # whether or not the balanced reaction was aerated (§4.R).
                mmol_g = float(convert(1, "mol", "mmol")) / float(chems[O2].MW)
                factor = target * mmol_g / balanced
                rxn.istoichiometry[O2] *= factor
                R, said = _made(cls, spec, chems, rxn, F_vol)
            oxygen = _oxygen(R, spec, chems, balanced, factor, consumed_kmol_h)
        out = _read(R, cls, spec, chems)
        out.update(scale=scale_info, reaction=rinfo, oxygen=oxygen, warnings=said,
                   utilitySettings=utility_settings([R]), designNotes=_design_notes(R, cls, spec))
        out["heat"] = _heat(R, kind, out, oxygen)
    return out


def _kmol_h(mol_s: float) -> float:
    """mol s⁻¹ in kmol h⁻¹, by thermosteam's units."""
    return float(mol_s * convert(1, "hr", "s") * convert(1, "mol", "kmol"))


def _design_notes(R: Any, cls: Any, spec: dict[str, Any]) -> list[str]:
    """What the design does that its basis alone does not say: a batch
    volume's one vessel is not bounded by V_max (OF-BLD-020 §4.R)."""
    if spec["scale"].get("batchVolume") is None:
        return []
    V = float(R.design_results["Reactor volume"])
    vmax = getattr(cls, "V_max_default", None)
    over = vmax is not None and V > float(vmax)
    return [f"a batch volume designs one vessel of that working volume, so V_max does not apply: BioSTEAM's vessel "
            f"holds the batch volume over V_wf, {V:.4g} m³"
            + (f", larger than the {float(vmax):.4g} m³ its {cls.__name__} holds a vessel to by default "
               "(V_max_default)" if over else "")]


def _batch_oxygen(R: Any, ts: list[float], ys: list[float]) -> dict[str, float] | None:
    """The oxygen the simulation took up, per hour of the plant: the
    trapezoid integral of its uptake over the batch to harvest (mmol L⁻¹,
    which is mol m⁻³), times each vessel's working volume and the vessels,
    over the cycle (D7's Cooney basis, OF-BLD-020 §4.R). None without an
    interval of uptake (two hours or more)."""
    if len(ts) <= 1:
        return None
    area = float(np.trapezoid(ys, ts))
    d = R.design_results
    V_work, N, cycle = float(d["Reactor volume"]) * float(R.V_wf), float(d["Number of reactors"]), float(d["Batch time"])
    return {"area": area, "workingVolume": V_work, "vessels": N, "cycle": cycle,
            "kmolPerH": float(area * V_work * N / cycle * convert(1, "mol", "kmol"))}


def _oxygen(R: Any, spec: dict[str, Any], chems: Any, balanced: float | None, factor: float,
            consumed_kmol_h: float) -> dict[str, Any]:
    mmol_g = float(convert(1, "mol", "mmol")) / float(chems[O2].MW)
    our = spec.get("our") or {}
    ts = [float(t) for t in our.get("t") or []]
    ys = [float(v) * mmol_g for v in our.get("value") or []]
    floor, _ = aeration_floor()
    batch = _batch_oxygen(R, ts, ys)
    base = {"t": ts, "our": ys, "unit": "mmol L⁻¹ h⁻¹", "oxygenBasis": spec.get("oxygenBasis"),
            "balancedUptake": balanced, "scale": factor, "reactionO2KmolPerH": consumed_kmol_h,
            "targetUptake": spec["ourTarget"] * mmol_g if spec.get("ourTarget") is not None else None,
            "scaledO2KmolPerH": _kmol_h(R.get_OUR()),
            "simulatedO2KmolPerH": batch["kmolPerH"] if batch else None,
            "floorKmolPerH": _kmol_h(floor) if floor is not None else None}
    if R.air.isempty():
        return {**base, "aerated": False, "otr": 0.0, "kLa": None, "kLaUnit": "h⁻¹",
                "kLaNeededAtPeak": None, "method": None, "short": _short(ts, ys, 0.0) if ts else [],
                "sized": None, "cStar": None, "cL": None, "drivingForce": None}
    per_h = float(convert(1, "hr", "s"))
    kLa = float(R.get_kLa()) * per_h  # h⁻¹; sets superficial_gas_flow too
    gin, vent, rho, th = R.sparged_gas, R.vent, float(R.effluent_density), float(R.theta_O2)
    p_in = gin.get_property("P", "bar") * gin.imol[O2] / gin.F_mol
    p_out = vent.get_property("P", "bar") * vent.imol[O2] / vent.F_mol
    c_in, c_out = aeration.C_O2_L(R.T, p_in), aeration.C_O2_L(R.T, p_out)  # mol kg⁻¹
    lmdf = aeration.log_mean_driving_force(c_out, c_in, th * c_out, th * c_in)  # mol kg⁻¹
    to_mmol_L = float(convert(1, "mol", "mmol")) * rho / float(convert(1, "m3", "L"))  # mol kg⁻¹ → mmol L⁻¹
    otr = kLa * lmdf * to_mmol_L
    method = next((m for (d, m), fn in aeration.kLa_methods.items() if fn is R.kLa), getattr(R.kLa, "__name__", None))
    # The peak the simulation states (on its solver's steps), when it states
    # one above its display grid's (§4.R).
    stated = [spec["ourPeak"] * mmol_g] if spec.get("ourPeak") is not None else []
    peak = max(ys + stated) if ys or stated else None
    return {**base, "aerated": True, "otr": otr, "kLa": kLa, "kLaUnit": "h⁻¹",
            "kLaNeededAtPeak": peak / (lmdf * to_mmol_L) if peak is not None else None, "method": method,
            "short": _short(ts, ys, otr) if ts else [], "sized": _uptake_sized(R),
            "cStar": c_in * to_mmol_L, "cL": th * c_in * to_mmol_L, "drivingForce": lmdf * to_mmol_L}


def _row(label: str, value: Any, unit: str, frm: str) -> dict[str, Any]:
    return {"label": label, "value": _plain(value), "unit": unit, "readFrom": frm}


def _read(R: Any, cls: Any, spec: dict[str, Any], chems: Any) -> dict[str, Any]:
    d = R.design_results
    units = R._units
    N, V = d["Number of reactors"], d["Reactor volume"]
    cycle = d["Batch time"]
    rows = [
        _row("Vessels", N, "", "design_results 'Number of reactors'"),
        _row("Volume of each vessel", V, units.get("Reactor volume", "m3"), "design_results 'Reactor volume'"),
        _row("Working volume of each vessel", V * R.V_wf, units.get("Reactor volume", "m3"),
             "design_results 'Reactor volume' times the unit's V_wf"),
        _row("Working volume fraction", R.V_wf, "", "the unit's V_wf"),
        _row("Batch time (reacting)", R.tau, "hr", "the unit's tau"),
        _row("Cycle time", cycle, units.get("Batch time", "hr"), "design_results 'Batch time' (tau + tau_0 + loading)"),
        _row("Loading time", d.get("Loading time"), units.get("Loading time", "hr"), "design_results 'Loading time'"),
        _row("Cleaning and unloading time", R.tau_0, "hr", "the unit's tau_0"),
        _row("Dead time", cycle - R.tau, "hr", "design_results 'Batch time' less the unit's tau"),
    ]
    if cls is bst.AeratedBioreactor:
        rows += [
            _row("Length", R.get_design_result("Length", "m"), "m", "design_results 'Length', in m"),
            _row("Diameter", R.get_design_result("Diameter", "m"), "m", "design_results 'Diameter', in m"),
            _row("Vessel orientation", d.get("Vessel type"), "", "design_results 'Vessel type'"),
            _row("Vessel material", R.vessel_material, "", "the unit's vessel_material"),
            _row("Design", R.design, "", "the unit's design"),
            _row("Agitator power, each vessel", R.agitator.power_utility.rate if getattr(R, "agitator", None) else 0.0,
                 "kW", "the agitator auxiliary's power utility (none when kW_per_m3 is zero)"),
            _row("Agitation power per working volume", R.kW_per_m3, "kW/m3",
                 "the unit's kW_per_m3 after the run (solved when optimize_power is on)"),
            _row("Compressor power", R.compressor.power_utility.rate, "kW", "the compressor auxiliary's power utility"),
            _row("Compressor outlet pressure", R.compressor.P, "Pa", "the compressor auxiliary's P"),
            _row("Air cooler duty", R.air_cooler.heat_utilities[0].duty if R.air_cooler.heat_utilities else 0.0,
                 "kJ/hr", "the air cooler auxiliary's heat utility"),
            _row("Air fed", R.air.get_total_flow("m3/hr"), "m3/hr", "the air stream, at its own conditions"),
            _row("Air fed", R.air.F_mol, "kmol/hr", "the air stream"),
        ]
        if getattr(R, "recirculation_pump", None) is not None:
            rows.append(_row("Recirculation pump power, each vessel", R.recirculation_pump.power_utility.rate, "kW",
                             "the recirculation pump auxiliary's power utility"))
        if not R.air.isempty():
            op = R.tau / cycle
            V_work = V * R.V_wf
            per_min = R.sparged_gas.get_total_flow("m3/min") / N / op
            rows += [
                _row("kLa achieved", float(R.get_kLa()) * float(convert(1, "hr", "s")), "1/hr",
                     f"get_kLa(), by {next((m for (dd, m), fn in aeration.kLa_methods.items() if fn is R.kLa), '')}"),
                _row("Superficial gas velocity", R.superficial_gas_flow, "m/s", "the unit's superficial_gas_flow"),
                _row("Aeration, vvm", per_min / V_work, "1/min",
                     "the sparged gas per vessel while it reacts over its working volume, as BioSTEAM reckons the gas "
                     "velocity"),
            ]
        duty = R._get_duty()
        rows.append(_row("Reactor duty", duty, "kJ/hr", (
            "the unit's _get_duty(): the enthalpy and heats of formation out less in" if R.Q_O2_consumption is None else
            "the unit's _get_duty(): Q_O2_consumption times the oxygen in less the oxygen out")))
    else:
        duty = d["Reactor duty"]
        rows += [
            _row("Recirculation flow, each vessel", d.get("Recirculation flow rate"),
                 units.get("Recirculation flow rate", "m3/hr"), "design_results 'Recirculation flow rate'"),
            _row("Reactor duty", duty, units.get("Reactor duty", "kJ/hr"), "design_results 'Reactor duty'"),
        ]
    cooling = sum(float(h.duty) for h in R.heat_utilities if h.duty < 0)
    rows += [
        _row("Cooling duty, every heat utility", cooling, "kJ/hr", "the unit's heat utilities, auxiliaries included"),
        _row("Electricity, the whole unit", R.power_utility.rate, "kW", "the unit's power utility"),
        _row("Utility cost", R.utility_cost, "USD/hr", "the unit's utility_cost"),
    ]
    ce, year = cost_index()
    return {
        "unitClass": cls.__name__, "unitId": R.ID, "aerobic": cls is bst.AeratedBioreactor,
        "design": rows,
        "designResults": {k: _plain(v) for k, v in d.items()},
        "auxiliaries": {n: type(getattr(R, n)).__name__ for n in type(R).auxiliary_unit_names
                        if getattr(R, n, None) is not None},
        "used": {k: _plain(getattr(R, k)) for k in (
            "T", "P", "tau", "tau_0", "V_wf", "V_max", "N", "loading_time", "length_to_diameter", "kW_per_m3",
            "vessel_material", "vessel_type", "heat_exchanger_configuration", "dT_hx_loop", "jacket_annular_diameter",
            "theta_O2", "Q_O2_consumption", "optimize_power", "design", "cooler_pressure_drop",
            "compressor_isentropic_efficiency") if hasattr(R, k)},
        "coolingAgents": sorted({h.agent.ID for h in R.heat_utilities if h.agent is not None}),
        "cost": {
            "purchase": float(R.purchase_cost), "installed": float(R.installed_cost),
            "byItem": {k: {"purchase": float(v), "installed": float(R.installed_costs.get(k, 0.0))}
                       for k, v in R.purchase_costs.items()},
            "utility": float(R.utility_cost), "costIndex": ce, "costIndexYear": year,
            "note": ("BioSTEAM's own cost correlations for this class and its auxiliaries, at the plant cost index it "
                     "holds" + (f" (its default, of {year})" if year else "") + "; installed is purchase times BioSTEAM's "
                     "bare-module factors. The NREL vessel's correlations are scaled from their own base index to it."),
        },
        "versions": {"biosteam": version("biosteam"), "thermosteam": version("thermosteam"),
                     "biorefineries": version("biorefineries")},
        "chemicals": CHEMICALS,
        "dutyRead": float(duty),
    }


def _heat(R: Any, kind: str, out: dict[str, Any], oxygen: dict[str, Any] | None) -> dict[str, Any]:
    """BioSTEAM's duty and how it was found (`method`: the heats of formation,
    or a forced heat per oxygen times the oxygen the vessel consumed, which
    `consumedKmolPerH` is), beside D7's cross-check on the oxygen the
    simulation took up (OF-BLD-020 §4.R)."""
    if kind != AEROBIC or oxygen is None:
        return {"bst": out["dutyRead"], "method": "heats-of-formation", "consumedKmolPerH": None, "convention": None,
                "oxygenKmolPerH": None, "conventionNote": (
                    "the cross-check rests on oxygen consumed, and an anaerobic vessel consumes none: BioSTEAM's duty "
                    "stands alone")}
    # What _get_duty multiplies a forced heat per oxygen by: the oxygen in less the oxygen out.
    consumed = float(sum(i.imol[O2] for i in R.ins) - sum(i.imol[O2] for i in R.outs))
    method = "heats-of-formation" if R.Q_O2_consumption is None else "forced-per-oxygen"
    q, why = heat_per_oxygen()
    batch = _batch_oxygen(R, oxygen["t"], oxygen["our"])
    if batch is None:
        return {"bst": out["dutyRead"], "method": method, "consumedKmolPerH": consumed, "convention": None,
                "oxygenKmolPerH": None, "conventionNote": (
                    f"{why}; the simulation keeps no uptake over its hours, so there is no oxygen to apply it to")}
    return {"bst": out["dutyRead"], "method": method, "consumedKmolPerH": consumed,
            "convention": q * batch["kmolPerH"], "oxygenKmolPerH": batch["kmolPerH"], "conventionNote": (
                f"{why}; applied to the oxygen the simulation took up: the trapezoid integral of its uptake over the "
                f"batch to harvest, {batch['area']:.4g} mmol L⁻¹, times each vessel's working volume, "
                f"{batch['workingVolume']:.4g} m³, and the vessels, {batch['vessels']:.4g}, over the {batch['cycle']:.4g} h "
                f"cycle: {batch['kmolPerH']:.4g} kmol/hr")}
