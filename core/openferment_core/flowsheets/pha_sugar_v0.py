"""A draft PHA flowsheet, version 0 (OF-BLD-014 §8.3; Appendix 3).

Fermentable sugar and ammonia → an aerated batch fermenter → a solids
centrifuge → a drum dryer → dried, PHA-rich cell mass. The price is per
kilogram of PHA contained in that dried cell mass.

WHAT IT LEAVES OUT: feedstock pretreatment and hydrolysis, polymer extraction
and purification, wastewater treatment, co-products (`LEAVES_OUT`).

Every input is set by the caller; this module holds no value for any of them.
Everything else is the reference biorefinery's (`biorefineries.cornstover`)
or BioSTEAM's own, and is read back after each run and listed (`read_back`),
so the screen can name its source. Appendix 3's five traps are handled where
they bite and marked "trap n".
"""
from __future__ import annotations

from typing import Any

import biosteam as bst
import thermosteam as tmo

NAME = "pha_sugar_v0"

INPUTS = {
    "titre": ("PHA titre at harvest", "g L-1", None),
    "yield": ("PHA yield on sugar", "g g-1", None),
    "content": ("PHA share of dry cell mass", "g g-1", None),
    "productivity": ("PHA volumetric productivity", "g L-1 h-1", None),
    "recovery": ("solids recovered at harvest", "", None),
    "sugarPrice": ("price of fermentable sugar", "USD kg-1", None),
    "sugarFeed": ("sugar fed", "kg h-1", None),
}

LEAVES_OUT = [
    "feedstock pretreatment and hydrolysis",
    "polymer extraction and purification",
    "wastewater treatment",
    "co-products",
]

CELLS = "Z_mobilis"  # the package's generic cell mass, CH1.8O0.5N0.2
POLYMER = "Glucose + 1.5 O2 -> PHB + 2 CO2 + 3 H2O"
RESPIRATION = "Glucose + 6 O2 -> 6 CO2 + 6 H2O"
BALANCE_TOL = 1e-6

# The words for an infeasible case. `oxygen` is BioSTEAM's own: read in
# AeratedBioreactor._run (biosteam 2.54.0), which raises "even an infinite
# flow rate of gas is not enough" when fifty times the oxygen uptake in air
# cannot meet transfer at the dissolved-oxygen target (§8.3, confirmed).
REASONS = {
    "carbon": "this yield and content leave no sugar for respiration",
    "oxygen": "this case asks for more oxygen than the aerated tank transfers",
    "balance": "the fermenter's mass balance did not close",
}


class Infeasible(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{REASONS[reason]}{f': {detail}' if detail else ''}")
        self.reason = reason


class Built:
    """The system, built once. Each case sets its inputs on these objects and
    re-simulates (trap 3: a ParallelReaction copies conversions when built)."""

    def __init__(self) -> None:
        from biorefineries import cornstover as cs

        self.cs = cs
        # A fresh flowsheet each build: units and streams of an earlier build
        # under the same name would otherwise be found by ID and reused.
        bst.main_flowsheet.set_flowsheet(bst.Flowsheet(NAME))
        chems = tmo.Chemicals(list(cs.create_chemicals()))  # trap 2: DrumDryer needs CH4, which this package has
        phb = tmo.Chemical.blank("PHB", formula="C4H6O2", phase="s")
        phb.copy_models_from(chems.Lignin, ["V", "Cn"])
        phb.default()
        chems.append(phb)
        chems.compile()
        self.chemicals = chems
        bst.settings.set_thermo(chems)
        self.thermo = bst.settings.thermo
        self.mw = {k: getattr(chems, k).MW for k in ("Glucose", "PHB", CELLS, "NH3")}

        # Trap 1: the polymer reaction has many balanced forms, so it is written
        # out and checked; the cell-mass one has one, and thermosteam solves it.
        to_phb = bst.Rxn(POLYMER, reactant="Glucose", X=0.1, check_atomic_balance=True)
        to_cells = bst.Rxn(f"Glucose + NH3 -> {CELLS} + CO2 + H2O", reactant="Glucose", X=0.1, correct_atomic_balance=True)
        burn = bst.Rxn(RESPIRATION, reactant="Glucose", X=0.1, check_atomic_balance=True)
        st = {c.ID: v for c, v in zip(to_cells.chemicals, to_cells.stoichiometry) if abs(v) > 1e-12}
        self.cells_reaction = {k: float(v) for k, v in st.items()}
        self.cells_per_glc = st[CELLS] / -st["Glucose"]
        self.nh3_per_glc = st["NH3"] / st["Glucose"]

        # The sugar and the water that dilutes it to the titre are two streams,
        # so the sugar's price is charged on sugar alone (Appendix 3's probe
        # priced the diluted feed; §8.3 found it).
        self.feed = bst.Stream("sugar", Glucose=1.0, units="kg/hr")
        self.water = bst.Stream("process_water", Water=1.0, units="kg/hr")
        self.ammonia = bst.Stream("ammonia", NH3=1.0, units="kg/hr", price=cs.price["Ammonia"])
        self.M1 = bst.Mixer("M1", ins=[self.feed, self.water, self.ammonia])
        self.R1 = bst.AeratedBioreactor(
            "R1", ins=[self.M1 - 0, bst.Stream("air", phase="g")], outs=["vent", "broth"],
            reactions=bst.ParallelReaction([to_phb, to_cells, burn]), tau=10.0, batch=True)
        self.C1 = bst.SolidsCentrifuge("C1", ins=self.R1 - 1, outs=["wet_solids", "spent_medium"],
                                       split={"PHB": 0.9, CELLS: 0.9}, solids=["PHB", CELLS])
        self.D1 = bst.DrumDryer("D1", ins=[self.C1 - 0, "dryer_air", "natural_gas"],
                                outs=["product", "dryer_vent", "emissions"], split={"PHB": 0.0, CELLS: 0.0})
        self.flowsheet = bst.main_flowsheet.get_flowsheet()
        self.system = bst.System.from_units("pha_sys", units=[self.M1, self.R1, self.C1, self.D1])
        self.tea = None

    def gap(self) -> float:
        flow_in = sum(s.F_mass for s in self.R1.ins)
        return abs(flow_in - sum(s.F_mass for s in self.R1.outs)) / flow_in


def build() -> Built:
    return Built()


def conversions(b: Built, v: dict[str, float]) -> tuple[float, float, float]:
    """The share of sugar each reaction takes: yield sets the polymer's,
    content the cell mass's, and the remainder is respired."""
    sugar = v["sugarFeed"]
    phb = sugar * v["yield"]
    cells = phb * (1 - v["content"]) / v["content"]
    n_glc = sugar / b.mw["Glucose"]
    x_phb = (phb / b.mw["PHB"]) / n_glc
    x_cells = (cells / b.mw[CELLS]) / b.cells_per_glc / n_glc
    return x_phb, x_cells, 1.0 - x_phb - x_cells


def _check(v: dict[str, float]) -> None:
    missing = [k for k in INPUTS if k not in v]
    if missing:
        raise ValueError(f"{NAME} needs {', '.join(missing)}")
    for k in ("yield", "content", "recovery"):
        if not 0 < v[k] <= 1:
            raise ValueError(f"{INPUTS[k][0]} must lie above 0 and at most 1")
    for k in ("titre", "productivity", "sugarFeed", "sugarPrice"):
        if not v[k] > 0:
            raise ValueError(f"{INPUTS[k][0]} must be above 0")


def simulate(b: Built, values: dict[str, float]) -> None:
    v = {k: float(values[k]) for k in values}
    _check(v)
    bst.main_flowsheet.set_flowsheet(b.flowsheet)
    bst.settings.set_thermo(b.thermo)
    x_phb, x_cells, x_burn = conversions(b, v)
    if x_burn < 0:
        raise Infeasible("carbon")
    b.R1.reactions.X[:] = [x_phb, x_cells, x_burn]  # trap 3
    sugar = v["sugarFeed"]
    n_glc = sugar / b.mw["Glucose"]
    b.feed.imass["Glucose"] = sugar
    b.water.imass["Water"] = sugar * v["yield"] / v["titre"] * 1000.0
    b.feed.price = v["sugarPrice"]
    b.ammonia.imass["NH3"] = x_cells * n_glc * b.nh3_per_glc * b.mw["NH3"]
    b.R1.tau = v["titre"] / v["productivity"]
    b.C1.isplit["PHB"] = v["recovery"]
    b.C1.isplit[CELLS] = v["recovery"]
    try:
        b.system.simulate()
    except RuntimeError as e:
        if "infinite flow rate of gas" in str(e):
            raise Infeasible("oxygen") from e
        raise Infeasible("balance", f"{type(e).__name__}: {e}") from e
    except Exception as e:  # trap 4: a broken fermenter surfaces downstream
        raise Infeasible("balance", f"{type(e).__name__}: {e}") from e
    if b.gap() > BALANCE_TOL:
        raise Infeasible("balance")


def read_back(b: Built) -> dict[str, float]:
    """Every setting the inputs table leaves out, read from the objects."""
    tea = b.tea
    return {
        "cakeMoisture": float(b.C1.moisture_content),
        "dryerMoisture": float(b.D1.moisture_content),
        "vesselLimitM3": float(b.R1.V_max),
        "oxygenTarget": float(b.R1.theta_O2),
        "temperatureK": float(b.R1.T),
        "rateOfReturn": float(tea.IRR),
        "operatingDays": float(tea.operating_days),
        "startYear": float(tea.duration[0]),
        "endYear": float(tea.duration[1]),
        "incomeTax": float(tea.income_tax),
        "ammoniaPriceUsdPerKg": float(b.ammonia.price),
        "packageGlucosePriceUsdPerKg": float(b.cs.price["Glucose"]) if "Glucose" in b.cs.price else float("nan"),
    }


def evaluate(b: Built, values: dict[str, float]) -> dict[str, Any]:
    simulate(b, values)
    if b.tea is None:
        b.tea = b.cs.create_tea(b.system)  # the benchmark's own finance model
    tea = b.tea
    product = b.D1.outs[0]
    pha = float(product.imass["PHB"])
    # TEA.solve_sales starts its secant from the last case's answer, so the
    # price would depend on what ran before. Start every case from zero, so
    # a case gives one price whatever came first and an artifact replays.
    tea._sales = 0.0
    price = float(tea.solve_price(product)) * float(product.F_mass) / pha
    hours = float(tea.operating_hours)
    per_kg = 1.0 / (pha * hours)
    media = (b.feed.cost + b.ammonia.cost) * hours * per_kg
    ferm_utilities = (b.R1.utility_cost or 0.0) + (b.M1.utility_cost or 0.0)
    down_utilities = (b.C1.utility_cost or 0.0) + (b.D1.utility_cost or 0.0) + sum(
        s.cost for s in b.D1.ins if s.price)
    utilities = ferm_utilities * hours * per_kg
    downstream = down_utilities * hours * per_kg
    labor = float(tea.labor_cost) * per_kg
    other = (float(tea.FOC) - float(tea.labor_cost)) * per_kg
    lines = {"media": media, "utilities": utilities, "labor": labor, "downstream": downstream, "other": other}
    # Capital is what remains of the price after the operating lines: the
    # return on and of the plant, and the tax on it. So the lines sum to the
    # price by construction.
    lines["capex"] = price - sum(lines.values())
    return {
        "pricePerKgPha": price,
        "phaKgPerH": pha,
        "costLines": lines,
        "readBack": read_back(b),
        "conversions": dict(zip(("polymer", "cells", "respiration"), conversions(b, {k: float(values[k]) for k in values}))),
    }
