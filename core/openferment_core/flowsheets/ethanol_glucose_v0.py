"""Glucose to ethanol, version 0: a flowsheet of our own (OF-BLD-019 §2.3;
D3, D4).

    glucose ──────┐
                  ├─ M1 ── R1 batch fermenter ── beer ── the ethanol purification
    process water ┘          │                          train of the BioSTEAM
                             └─ vent (CO2)               reference designs
                                                         ├─ fuel-grade ethanol
                                                         ├─ stillage
                                                         └─ the rectifier's water

The fermenter is a `bst.BatchBioreactor` (BioSTEAM's NREL batch bioreactor,
sized and costed by BioSTEAM) running one reaction, glucose to two ethanol
and two carbon dioxide, at the bound yield as a share of the theoretical
yield. The theoretical yield is computed here from that reaction's
stoichiometry and thermosteam's molecular weights; it is a convention the
run's basis names and the run reads back, never a number in this file. The
batch time is the titre over the productivity. The purification train is
`biorefineries.ethanol.create_ethanol_purification_system` exactly as the
package builds it (beer column with its heat integration, rectifier,
superheater, molecular sieves, product tanks), with no denaturant blended:
the product is the ethanol the package's sieves give, fuel grade, a
convention the basis names. Chemicals and finance are the dry-grind corn
ethanol plant's (`biorefineries.corn.create_chemicals`, `corn.create_tea`
with its `default_tea_parameters`), cited with the package's version in the
basis; equipment and thermodynamics are BioSTEAM's own.

WHAT IT LEAVES OUT (`LEAVES_OUT`): where the glucose comes from; cell mass
and by-products (the glucose the yield does not turn into ethanol leaves in
the beer unconverted, and goes out with the stillage); the scrubber that
recovers ethanol from the fermenter's gas; stillage handling and co-products;
wastewater treatment and the boiler.

Every input is set by the caller; this module holds no value for any of
them (Rule 1, D4). Everything else is the package's or BioSTEAM's own, read
back after each case (`read_back`) so the screen can name its source.
"""
from __future__ import annotations

from typing import Any

import biosteam as bst
import thermosteam as tmo

NAME = "ethanol_glucose_v0"

INPUTS = {
    "feed_glucose_conc": ("glucose in the fermenter's feed", "g L-1", None),
    "titre": ("ethanol titre at harvest", "g L-1", None),
    "yield": ("ethanol yield on glucose", "g g-1", None),
    "productivity": ("ethanol volumetric productivity", "g L-1 h-1", None),
    "plant_scale": ("ethanol fermented in a year", "t yr-1", None),
    "glucose_price": ("price of glucose", "USD kg-1", None),
}

LEAVES_OUT = [
    "where the glucose comes from: it arrives as clean glucose, priced as such",
    "cell mass and by-products: the glucose the yield does not turn into ethanol leaves unconverted in the stillage",
    "the scrubber that recovers ethanol from the fermenter's gas",
    "stillage handling and co-products",
    "wastewater treatment and the boiler",
]

FERMENTATION = "Glucose -> 2 Ethanol + 2 CO2"

# The words for a case the flowsheet cannot hold.
REASONS = {
    "yield": "this yield is above the theoretical yield of ethanol on glucose",
    "concentration": "the feed cannot hold this much glucose in a litre",
    "convergence": "the flowsheet did not converge on this case",
}


class Infeasible(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{REASONS[reason]}{f': {detail}' if detail else ''}")
        self.reason = reason


class Fermenter(bst.BatchBioreactor):
    """BioSTEAM's batch bioreactor running one reaction, glucose to ethanol
    and carbon dioxide, at the conversion each case sets. Size, vessel count,
    cost, duty and the working volume fraction are BioSTEAM's: this class
    adds the reaction and nothing else. The gas leaves through the vent as
    the corn plant's fermenter vents it."""

    line = "Fermentation"

    def _init(self, **kwargs: Any) -> None:
        super()._init(**kwargs)
        # The conversion is set by every case before it runs (`simulate`).
        self.reaction = tmo.Rxn(FERMENTATION, reactant="Glucose", X=1.0, check_atomic_balance=True)

    def _run(self) -> None:
        vent, effluent = self.outs
        effluent.mix_from(self.ins)
        self.reaction(effluent)
        vent.empty()
        vent.receive_vent(effluent)


class Built:
    """The system and its TEA, built once. Each case sets its inputs on these
    objects and re-simulates (Appendix 3, trap 3)."""

    def __init__(self) -> None:
        from biorefineries import corn
        from biorefineries.ethanol import create_ethanol_purification_system

        self.corn = corn
        # A fresh flowsheet each build, so nothing of an earlier build under
        # the same name is found by ID and reused.
        bst.main_flowsheet.set_flowsheet(bst.Flowsheet(NAME))
        self.chemicals = corn.create_chemicals()
        bst.settings.set_thermo(self.chemicals)
        self.thermo = bst.settings.thermo

        self.glucose = bst.Stream("glucose", Glucose=1.0, units="kg/hr")
        self.water = bst.Stream("process_water", Water=1.0, units="kg/hr")
        self.M1 = bst.Mixer("M1", ins=[self.glucose, self.water], outs="glucose_solution")
        self.R1 = Fermenter("R1", ins=self.M1 - 0, outs=("vent", "beer"),
                            V_max=bst.AnaerobicBioreactor.V_max_default)
        rxn = self.R1.reaction
        st = rxn.istoichiometry
        # The theoretical yield, g ethanol per g glucose, from the reaction as
        # written and thermosteam's molecular weights.
        self.theoretical = float(st["Ethanol"] * self.chemicals.Ethanol.MW
                                 / (-st["Glucose"] * self.chemicals.Glucose.MW))
        self.denaturant = bst.Stream("denaturant", units="kg/hr")
        self.purification = create_ethanol_purification_system(
            ins=[self.R1 - 1, self.denaturant], outs=["ethanol", "stillage", "recycle_process_water"])
        self.product = self.purification.outs[0]
        self.blender = self.flowsheet_unit("M304")
        # No denaturant is blended: the product is the ethanol the sieves give
        # (the convention `ethanol_purity`, fuel grade, named in the basis).
        self.blender.denaturant_fraction = 0
        self.flowsheet = bst.main_flowsheet.get_flowsheet()
        self.system = bst.System.from_units(f"{NAME}_sys", units=[self.M1, self.R1, *self.purification.units])
        # The dry-grind corn plant's own finance model, its parameters as the
        # package sets them.
        self.tea = corn.create_tea(self.system)
        self.price: float | None = None

    def flowsheet_unit(self, unit_id: str) -> Any:
        return next(u for u in self.purification.units if u.ID == unit_id)


def build() -> Built:
    return Built()


def _check(v: dict[str, float]) -> None:
    missing = [k for k in INPUTS if k not in v]
    if missing:
        raise ValueError(f"{NAME} needs {', '.join(missing)}")
    for k in INPUTS:
        if not v[k] > 0:
            raise ValueError(f"{INPUTS[k][0]} must be above 0")


def _dilute(b: Built, glucose: float, conc: float) -> float:
    """The process water that brings the glucose to `conc` (g per litre of the
    glucose solution, as the mixer gives it, by thermosteam's volume of the
    mixture), found by a bracketing root search."""
    from scipy.optimize import brentq

    solution = b.M1.outs[0]

    def gap(water: float) -> float:
        b.water.imass["Water"] = water
        b.M1.run()
        return glucose / solution.F_vol - conc  # kg m-3 is g L-1

    # Water alone at the glucose's volume of solution: more than enough, since
    # the glucose takes up room of its own.
    rho = b.chemicals.Water.rho("l", b.water.T, b.water.P)
    high = glucose / conc * rho
    if gap(0) <= 0:
        raise Infeasible("concentration")
    return float(brentq(gap, 0, high))


def simulate(b: Built, values: dict[str, float]) -> None:
    v = {k: float(values[k]) for k in values}
    _check(v)
    bst.main_flowsheet.set_flowsheet(b.flowsheet)
    bst.settings.set_thermo(b.thermo)
    conversion = v["yield"] / b.theoretical
    if conversion > 1:
        raise Infeasible("yield")
    b.R1.reaction.X = conversion
    hours = float(b.tea.operating_hours)
    ethanol = float(tmo.units_of_measure.convert(v["plant_scale"], "metric_ton", "kg")) / hours
    glucose = ethanol / v["yield"]
    b.glucose.imass["Glucose"] = glucose
    b.glucose.price = v["glucose_price"]
    b.water.imass["Water"] = _dilute(b, glucose, v["feed_glucose_conc"])
    b.R1.tau = v["titre"] / v["productivity"]
    # The recycle (the sieves' regenerate back to the rectifier) converges
    # from where the last case left it, so the answer would depend on what
    # ran before. Empty it, so a case gives one answer whatever came first
    # (measured: carried over, the same case moved its price in the fourth
    # digit; emptied, what remains is BioSTEAM's own last-digit noise).
    b.system.empty_recycles()
    try:
        b.system.simulate()
    except Exception as e:
        raise Infeasible("convergence", f"{type(e).__name__}: {e}") from e


def read_back(b: Built) -> dict[str, float]:
    """Every setting the inputs leave to the package or to BioSTEAM, and what
    the case gave, read from the objects."""
    tea, R1, beer, product = b.tea, b.R1, b.R1.outs[1], b.product
    design = R1.design_results
    return {
        "theoreticalYieldGPerG": b.theoretical,
        "fermenterConversion": float(R1.reaction.X),
        "batchTimeH": float(R1.tau),
        "beerEthanolGPerL": float(beer.imass["Ethanol"] / beer.F_vol),
        "glucoseFedKgPerH": float(b.glucose.imass["Glucose"]),
        "waterFedKgPerH": float(b.water.imass["Water"]),
        "productEthanolMassFraction": float(product.imass["Ethanol"] / product.F_mass),
        "denaturantFraction": float(b.blender.denaturant_fraction),
        "reactors": float(design["Number of reactors"]),
        "reactorVolumeM3": float(design["Reactor volume"]),
        "vesselLimitM3": float(R1.V_max),
        "workingVolumeFraction": float(R1.V_wf),
        "cleaningTimeH": float(R1.tau_0),
        "temperatureK": float(R1.T),
        "operatingHours": float(tea.operating_hours),
        "rateOfReturn": float(tea.IRR),
        "operatingDays": float(tea.operating_days),
        "startYear": float(tea.duration[0]),
        "endYear": float(tea.duration[1]),
        "incomeTax": float(tea.income_tax),
        "langFactor": float(tea.lang_factor),
    }


def evaluate(b: Built, values: dict[str, float]) -> dict[str, Any]:
    simulate(b, values)
    tea, product = b.tea, b.product
    # TEA.solve_sales starts its secant from the last case's answer; start
    # every case from zero, so a case gives one price whatever ran before
    # and an artifact replays (as pha_sugar_v0 does).
    tea._sales = 0
    b.price = float(tea.solve_price(product))
    price = b.price
    hours = float(tea.operating_hours)
    per_kg = 1 / (float(product.F_mass) * hours)
    fermentation = [b.M1, b.R1]
    media = sum(s.cost for s in (b.glucose, b.water, b.denaturant) if s.price) * hours * per_kg
    utilities = sum(u.utility_cost or 0 for u in fermentation) * hours * per_kg
    downstream = sum(u.utility_cost or 0 for u in b.purification.units) * hours * per_kg
    labor = float(tea.labor_cost) * per_kg
    other = (float(tea.FOC) - float(tea.labor_cost)) * per_kg
    lines = {"media": media, "utilities": utilities, "labor": labor, "downstream": downstream, "other": other}
    # Capital is what remains of the price after the operating lines: the
    # return on and of the plant and the tax on it, so the lines sum to the
    # price by construction.
    lines["capex"] = price - sum(lines.values())
    return {
        "pricePerKgEthanol": price,
        "ethanolKgPerH": float(product.imass["Ethanol"]),
        "costLines": lines,
        "readBack": read_back(b),
    }


def parts(b: Built) -> dict[str, Any]:
    """What the worker reads the run's tables from after the base case
    (OF-BLD-019 §2.1): the system, the corn plant's TEA, the ethanol product,
    the glucose as the main feedstock, the price the TEA solved for the
    product, and the product's own flow as the flow the price is per."""
    return {"system": b.system, "tea": b.tea, "product": b.product, "feedstock": b.glucose, "price": b.price,
            "basis_flow": float(b.product.F_mass), "basis": "kg of fuel-grade ethanol, as the product leaves its tank"}
