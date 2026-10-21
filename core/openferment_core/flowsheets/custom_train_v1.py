"""A vessel and a train, priced: the seam (OF-BLD-020 §6.1, D11, E.2‴, E.3‴).

    glucose ──────┐                                           the train pureOS ran,
                  ├─ M1 ── the fermenter fermOS designed ── beer ── unit by unit ── product
    process water ┘          │ (air, when it is aerated)            └─ every other outlet
                             └─ vent

Not built once and kept by its name, as the other scenario flowsheets are:
its structure is data, the Proforma worker hands it in (`build(structure,
unit_class)`, through the `run` op's `structure`), and the worker keeps a
built plant per structure. The structure is the service's
(core/openferment_core/composite.py), read from two kept artifacts:

    fermenter   a `fermos.vessel` design: its BioSTEAM class
                (`AeratedBioreactor` or `NRELAnaerobicBatchBioreactor`), its
                unit id, every design parameter the design passed BioSTEAM
                (a value whose source was the class's own default is left to
                the class, as the design left it), its vessel type, one vessel
                or many, its reacting time, and the reaction it was built on;
                rebuilt by `flowsheets/vessel.make_unit`, the function the
                design itself is built with
    train       a `pureos.train_run`: each unit's catalogue type, values,
                outlets and side flows as that run held them, built by
                `flowsheets/train.Built` on the fermenter's beer (the train's
                own inlet is not an input here: the beer is its inlet)
    finance     the values a person set in the panel's Finance group, by key;
                every other parameter of the dry-grind corn plant's TEA is the
                package's own `default_tea_parameters`, read here from the
                package and handed to `biorefineries.corn.create_tea`

THE REACTION IS THE VESSEL'S, AT THE BOUND YIELD. A case sets the
conversion so the ethanol made per gram of glucose fed is the scenario's
bound yield: an aerated vessel's one reaction (glucose and oxygen to cells,
ethanol, carbon dioxide and water, per glucose used, its oxygen scaled as the
design scaled it) at the yield over the ethanol it makes of a gram of glucose
used; the NREL vessel's two in parallel, glucose to two ethanol and two
carbon dioxide at the yield over that reaction's theoretical yield (thermosteam's
molecular weights), beside the cells' reaction at the share of the glucose the
design gave it. A yield the reaction cannot reach is a case the flowsheet
cannot hold, said so. The batch time is the titre over the productivity, as
the ethanol flowsheet's is; the reacting time the vessel was designed for is
read back beside it.

Every case sets BioSTEAM's default utility prices and plant cost index, as
the other scenario flowsheets do, empties the train's recycles and the NREL
vessel's vent (which that class never empties of itself), and starts the
TEA's price solve from nothing, so a case gives one answer whatever ran
before. BIOSTEAM IS IMPORTED AT THE TOP OF THIS FILE: it runs in the worker
alone (test_workers holds flowsheets/ to that).

Rule 1: no number in this file but zero and one (an AST test holds it).
Every value is the service's, named in the run's basis, or the package's or
BioSTEAM's own, read back after each case.
"""
from __future__ import annotations

import itertools
from importlib import import_module
from typing import Any, Callable

import biosteam as bst
import thermosteam as tmo

from . import utility_settings
from . import vessel as _vessel
from .ethanol_glucose_v0 import FERMENTATION, _dilute, create_chemicals
from .train import Built as _TrainBuilt

NAME = "custom_train_v1"
# A structure is handed in with every build: the worker keeps one built
# plant per structure.
STRUCTURED = True

INPUTS = {
    "feed_glucose_conc": ("glucose in the fermenter's feed", "g L-1", None),
    "titre": ("ethanol titre at harvest", "g L-1", None),
    "yield": ("ethanol yield on glucose", "g g-1", None),
    "productivity": ("ethanol volumetric productivity", "g L-1 h-1", None),
    "plant_scale": ("ethanol fermented in a year", "t yr-1", None),
    "glucose_price": ("price of glucose", "USD kg-1", None),
}

AEROBIC, ANAEROBIC = "aerobic", "anaerobic"
GLUCOSE, ETHANOL, CELLS, O2, CO2, WATER = "Glucose", "Ethanol", "Yeast", "O2", "CO2", "Water"
# The cells' reaction of the NREL vessel, as the vessel design builds it
# (closed on thermosteam's formulas, no oxygen).
GROWTH = f"{GLUCOSE} -> {CELLS} + {CO2} + {WATER}"
MIXER = "M1"
# The keys of the TEA parameters that hold a pair or a schedule, by part.
DURATION, SCHEDULE = "duration", "construction_schedule"
DURATION_PARTS = ("start", "end")
SEP = "."

# The words for a case the flowsheet cannot hold.
REASONS = {
    "yield": "this yield is above what the vessel's reaction makes of the glucose",
    "concentration": "the feed cannot hold this much glucose in a litre",
    "convergence": "the flowsheet did not converge on this case",
    "product": "the train's product stream carries none of the product it traces",
}

_SEQ = itertools.count()


class Infeasible(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{REASONS[reason]}{f': {detail}' if detail else ''}")
        self.reason = reason


class Refused(ValueError):
    """A structure that cannot be built, in words (the worker's error names
    the class, so the service reads it as a refusal)."""


# ── the TEA's parameters ───────────────────────────────────────────────


def package_tea_defaults() -> dict[str, Any]:
    """`biorefineries.corn.tea.default_tea_parameters`, read from the package
    by module path (once the corn plant has loaded in this worker, the
    package's attribute `tea` is that plant's TEA object, not this module)."""
    return dict(import_module("biorefineries.corn.tea").default_tea_parameters)


def tea_parameters(finance: dict[str, Any]) -> dict[str, Any]:
    """The package's defaults with a person's values laid on by panel key: a
    plain key replaces its value; `duration.start` and `duration.end` one end
    of the plant's life; `construction_schedule.<n>` the share of year n."""
    out = package_tea_defaults()
    for key, value in finance.items():
        base, _, part = key.partition(SEP)
        if base not in out:
            raise Refused(f"the corn plant's TEA takes no parameter {base}; it takes {', '.join(out)}")
        if base == DURATION and part in DURATION_PARTS:
            ends = list(out[base])
            ends[DURATION_PARTS.index(part)] = value
            out[base] = tuple(ends)
        elif base == SCHEDULE and part.isdigit():
            shares = list(out[base])
            at = int(part) - 1
            if not 0 <= at < len(shares):
                raise Refused(f"the construction schedule has {len(shares)} years; there is no year {part}")
            shares[at] = value
            out[base] = tuple(shares)
        elif part:
            raise Refused(f"{key} is no parameter of the corn plant's TEA")
        else:
            out[base] = value
    return out


def tea_values(tea: Any, keys: list[str]) -> dict[str, float]:
    """Each panel key's value as the TEA object holds it after a case, a
    number (a word, the depreciation schedule, is in the basis alone)."""
    out: dict[str, float] = {}
    for key in keys:
        base, _, part = key.partition(SEP)
        # The class's own attribute, or its private one where the class keeps
        # it under a leading underscore (BioSTEAM's construction schedule).
        held = next((getattr(tea, a) for a in (base, f"_{base}") if hasattr(tea, a)), None)
        if held is None:
            continue
        if base == DURATION and part in DURATION_PARTS:
            held = list(held)[DURATION_PARTS.index(part)]
        elif base == SCHEDULE and part.isdigit():
            held = list(held)[int(part) - 1]
        if isinstance(held, (int, float)) and not isinstance(held, bool):
            out[f"finance{SEP}{key}"] = float(held)
    return out


# ── the fermenter's reaction ───────────────────────────────────────────


class _Reaction:
    """The vessel's reaction, and how a yield sets its conversion."""

    def __init__(self, chems: Any, fermenter: dict[str, Any]) -> None:
        MW = {i: float(chems[i].MW) for i in (GLUCOSE, ETHANOL)}
        r = fermenter["reaction"]
        self.kind = fermenter["kind"]
        if self.kind == AEROBIC:
            st = {k: float(v) for k, v in (r.get("stoichiometry") or {}).items()}
            if not st.get(ETHANOL, 0) > 0:
                raise Refused(f"vessel design {fermenter['vessel']}'s reaction makes no ethanol, so no yield of "
                              "ethanol on glucose feeds it: its simulation made none")
            products = [i for i in (CELLS, ETHANOL, CO2, WATER) if st.get(i, 0) > 0]
            self.rxn = tmo.Rxn(f"{GLUCOSE} + {O2} -> {' + '.join(products)}", reactant=GLUCOSE, X=0)
            for chem, coefficient in st.items():
                self.rxn.istoichiometry[chem] = coefficient
            # The oxygen as the design scaled it to size the air for the
            # simulation's uptake (flowsheets/vessel.design).
            self.rxn.istoichiometry[O2] *= float(fermenter["oxygenScale"])
            self.per_glucose = st[ETHANOL] * MW[ETHANOL] / (-st[GLUCOSE] * MW[GLUCOSE])
            self.growth_share = None
        else:
            self.ferm = tmo.Rxn(FERMENTATION, reactant=GLUCOSE, X=0, check_atomic_balance=True)
            self.grow = tmo.Rxn(GROWTH, reactant=GLUCOSE, X=0, correct_atomic_balance=True)
            self.growth_share = float(r.get("growthShare") or 0)
            self.grow.X = self.growth_share
            st = self.ferm.istoichiometry
            self.per_glucose = float(st[ETHANOL] * MW[ETHANOL] / (-st[GLUCOSE] * MW[GLUCOSE]))
            self.rxn = tmo.ParallelReaction([self.ferm, self.grow])

    def set_yield(self, yield_: float) -> float:
        """Set the conversion that makes `yield_` g of ethanol per g of
        glucose fed, and return it."""
        x = yield_ / self.per_glucose
        if self.kind == AEROBIC:
            if x > 1:
                raise Infeasible("yield", f"the vessel's reaction makes {self.per_glucose:.6g} g of ethanol of a gram "
                                          "of glucose it uses")
            self.rxn.X = x
        else:
            if x + self.growth_share > 1:
                raise Infeasible("yield", f"the theoretical yield is {self.per_glucose:.6g} g g⁻¹, and the vessel's "
                                          f"cells take {self.growth_share:.6g} of the glucose")
            # A parallel reaction holds its own copy of each conversion: the
            # fermentation is its first.
            self.rxn.X[0] = x
        return x

    @property
    def conversion(self) -> float:
        return float(self.rxn.X if self.kind == AEROBIC else self.rxn.X[0])


# ── the plant ──────────────────────────────────────────────────────────


class Built:
    """The fermenter, the train and their TEA, built once per structure; each
    case sets its inputs on these objects and re-simulates."""

    def __init__(self, structure: dict[str, Any], unit_class: Callable[[str], tuple[Any, Any]]) -> None:
        from biorefineries import corn

        f, t = structure["fermenter"], structure["train"]
        self.structure = structure
        bst.main_flowsheet.set_flowsheet(bst.Flowsheet(f"{NAME}_{next(_SEQ)}"))
        self.chemicals = create_chemicals()
        bst.settings.set_thermo(self.chemicals)
        self.thermo = bst.settings.thermo
        cls = getattr(bst, f["unitClass"], None)
        if cls not in (bst.AeratedBioreactor, bst.NRELAnaerobicBatchBioreactor):
            raise Refused(f"a vessel design's fermenter is BioSTEAM's AeratedBioreactor or NRELAnaerobicBatchBioreactor; "
                          f"{f['unitClass']} is neither")
        clash = sorted({u["id"] for u in t["units"]} & {MIXER, f["unitId"]})
        if clash:
            raise Refused(f"the train names a unit {', '.join(clash)}, which this flowsheet's feed mixer or fermenter "
                          "takes; give that unit of the train another id in pureOS")

        self.glucose = bst.Stream("glucose", Glucose=1, units="kg/hr")
        self.water = bst.Stream("process_water", Water=1, units="kg/hr")
        self.M1 = bst.Mixer(MIXER, ins=[self.glucose, self.water], outs="glucose_solution")
        self.reaction = _Reaction(self.chemicals, f)
        self.R1 = _vessel.make_unit(cls, f["unitId"], self.M1 - 0, float(f["tau"]), self.reaction.rxn,
                                    dict(f["params"]), f.get("design"), bool(f["one"]), outs=("vent", "beer"))
        self.vessel_tau = float(f["tau"])
        self.beer = self.R1.outs[1]
        try:
            self.train = _TrainBuilt({"units": t["units"]}, unit_class, self.chemicals, upstream=self.beer)
        except Exception as e:  # the train module's refusal, or BioSTEAM's words
            raise Refused(str(e)) from None
        self.product = self.train.product
        self.product_chemical = str(t["product"])
        self.flowsheet = bst.main_flowsheet.get_flowsheet()
        self.system = bst.System.from_units(f"{NAME}_sys", units=[self.M1, self.R1, *self.train.units])
        self.tea = corn.create_tea(self.system, **tea_parameters(dict(structure.get("finance") or {})))
        self.finance_keys = list(structure.get("financeKeys") or [])
        self.price: float | None = None


def build(structure: dict[str, Any], unit_class: Callable[[str], tuple[Any, Any]]) -> Built:
    return Built(structure, unit_class)


def _check(v: dict[str, float]) -> None:
    missing = [k for k in INPUTS if k not in v]
    if missing:
        raise ValueError(f"{NAME} needs {', '.join(missing)}")
    for k in INPUTS:
        if not v[k] > 0:
            raise ValueError(f"{INPUTS[k][0]} must be above 0")


def simulate(b: Built, values: dict[str, float]) -> None:
    v = {k: float(values[k]) for k in values}
    _check(v)
    bst.main_flowsheet.set_flowsheet(b.flowsheet)
    bst.settings.set_thermo(b.thermo)
    # BioSTEAM's own utility prices and plant cost index for every case, as
    # the other scenario flowsheets set them (read back with the case).
    bst.process_tools.default_utilities()
    bst.process_tools.default_CEPCI()
    b.reaction.set_yield(v["yield"])
    hours = float(b.tea.operating_hours)
    ethanol = float(tmo.units_of_measure.convert(v["plant_scale"], "metric_ton", "kg")) / hours
    glucose = ethanol / v["yield"]
    b.glucose.imass[GLUCOSE] = glucose
    b.glucose.price = v["glucose_price"]
    b.water.imass[WATER] = _dilute(b, glucose, v["feed_glucose_conc"])
    b.R1.tau = v["titre"] / v["productivity"]
    # The NREL vessel never empties its vent (it mixes the vent into its
    # equilibrium), and the train's recycles converge from where the last
    # case left them: both emptied, so a case gives one answer whatever ran
    # before.
    b.R1.outs[0].empty()
    b.system.empty_recycles()
    try:
        b.system.simulate()
    except Exception as e:
        raise Infeasible("convergence", f"{type(e).__name__}: {e}") from e


def read_back(b: Built) -> dict[str, float]:
    """What the case gave and every setting the inputs leave to the vessel
    design, the train run, the package or BioSTEAM, read from the objects."""
    R1, beer, product, chem = b.R1, b.beer, b.product, b.product_chemical
    design = R1.design_results
    out = {
        "fermenterConversion": b.reaction.conversion,
        ("theoreticalYieldGPerG" if b.reaction.kind == ANAEROBIC else "reactionYieldGPerG"): float(b.reaction.per_glucose),
        "batchTimeH": float(R1.tau),
        "vesselTauH": b.vessel_tau,
        "beerProductGPerL": float(beer.imass[chem] / beer.F_vol),
        "glucoseFedKgPerH": float(b.glucose.imass[GLUCOSE]),
        "waterFedKgPerH": float(b.water.imass[WATER]),
        "productMassFraction": float(product.imass[chem] / product.F_mass) if product.F_mass else 0.0,
        "reactors": float(design["Number of reactors"]),
        "reactorVolumeM3": float(design["Reactor volume"]),
        "workingVolumeFraction": float(R1.V_wf),
        "cleaningTimeH": float(R1.tau_0),
        "temperatureK": float(R1.T),
        "operatingHours": float(b.tea.operating_hours),
        **tea_values(b.tea, b.finance_keys),
        **utility_settings(b.system.units),
    }
    if b.reaction.growth_share is not None:
        out["growthShare"] = b.reaction.growth_share
    return out


def evaluate(b: Built, values: dict[str, float]) -> dict[str, Any]:
    simulate(b, values)
    tea, product = b.tea, b.product
    # TEA.solve_sales starts its secant from the last case's answer; start
    # every case from zero, as the other scenario flowsheets do.
    contained = float(product.imass[b.product_chemical])
    if not contained > 0:
        raise Infeasible("product", f"{product.ID} carries no {b.product_chemical}")
    tea._sales = 0
    b.price = float(tea.solve_price(product))
    # The price per kg of the product the train traces, contained in its
    # product stream (as the PHA flowsheet prices per kg of PHA contained):
    # the stream's price times its mass over the product's.
    price = b.price * float(product.F_mass) / contained
    hours = float(tea.operating_hours)
    per_kg = 1 / (contained * hours)
    media = sum(s.cost for s in (b.glucose, b.water) if s.price) * hours * per_kg
    utilities = sum(u.utility_cost or 0 for u in (b.M1, b.R1)) * hours * per_kg
    downstream = sum(u.utility_cost or 0 for u in b.train.units) * hours * per_kg
    labor = float(tea.labor_cost) * per_kg
    other = (float(tea.FOC) - float(tea.labor_cost)) * per_kg
    lines = {"media": media, "utilities": utilities, "labor": labor, "downstream": downstream, "other": other}
    # Capital is what remains of the price after the operating lines, so the
    # lines sum to the price by construction (as the ethanol flowsheet's do).
    lines["capex"] = price - sum(lines.values())
    return {
        "pricePerKgProduct": price,
        "productKgPerH": contained,
        "costLines": lines,
        "readBack": read_back(b),
    }


def parts(b: Built) -> dict[str, Any]:
    """What the worker reads the run's tables from after the base case: the
    whole system (fermenter and train), the corn plant's TEA, the train's
    product stream, the glucose as the main feedstock, the price the TEA
    solved for that stream, and the product it contains as the flow the
    price is per (so pureOS traces that product through the run)."""
    return {"system": b.system, "tea": b.tea, "product": b.product, "feedstock": b.glucose, "price": b.price,
            "basis_flow": float(b.product.imass[b.product_chemical]),
            "basis": f"kg of {b.product_chemical} contained in the train's product stream"}
