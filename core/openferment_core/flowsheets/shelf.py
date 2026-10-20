"""Proforma's shelf of flowsheets (OF-BLD-019 §2.1, D2).

Pure data: what each flowsheet is, where it comes from, which program it
belongs to, the inputs it takes and the outputs it reports. The service
serves it at `GET /api/proforma/shelf` and must never import BioSTEAM to do
so, so this module imports nothing heavier than the models (test_proforma
holds it to that). src/data/types.ts mirrors `FlowsheetInfo` through PAIRS.

A scenario names a flowsheet by id and nothing else about its structure.
No input here carries a value: records bind the process inputs, a named
person's assumption sets the rest, and a reference biorefinery runs whole
on its package's own defaults (Rule 1; E.1).

    SHELF      the flowsheets a person can choose, by id
    TEST_ONLY  the toy, a STAND-IN for tests: never on the shelf, never
               served, and refused wherever the shelf is asked unless the
               caller says `allow_toy` (as geneOS's toy network is)
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ..models import FlowsheetInfo, FlowsheetInput


def _pkg(dist: str) -> str:
    """A package and its installed version, or that it is not installed."""
    try:
        return f"{dist} {version(dist)}"
    except PackageNotFoundError:
        return f"{dist} (not installed here)"


# The units of what a run's tables hold, as BioSTEAM states them (Stream.T,
# Stream.P, Stream.F_mass, a unit's purchase and installed cost, a
# HeatUtility's duty, a PowerUtility's rate, the TEA's annual amounts). The
# worker writes them into every run artifact as `tableUnits`.
TABLE_UNITS = {"T": "K", "P": "Pa", "massFlow": "kg/hr", "price": "USD/kg", "cost": "USD", "duty": "kJ/hr",
               "power": "kW", "annual": "USD/yr", "perUnit": "USD per unit of the price's basis"}

# What the PHA draft leaves out; proforma.LEAVES_OUT is this list.
PHA_LEAVES_OUT = [
    "feedstock pretreatment and hydrolysis",
    "polymer extraction and purification",
    "wastewater treatment",
    "co-products",
]
PHA_PRICE_BASIS = "USD per kg of PHA contained in dried cell mass"

_CORNSTOVER = FlowsheetInfo(
    id="cornstover_benchmark",
    title="Corn stover to ethanol, the NREL 2011 design",
    description=(
        "The corn stover ethanol biorefinery the BioSTEAM authors built to the NREL design report "
        "(Humbird et al. 2011, NREL/TP-5100-47764): pretreatment, enzymatic hydrolysis, co-fermentation, "
        "distillation, wastewater treatment and a boiler, run whole on the package's own defaults. "
        "The benchmark: it shows this installation simulates and prices a published biorefinery as its authors do."
    ),
    source=f"{_pkg('biorefineries')}, cornstover",
    program=None,
    reference=True,
    inputs=[],
    outputs=["mespUsdPerGal", "mespUsdPerKg", "ethanolDensityKgPerGal", "settings", "references"],
    priceOutput="mespUsdPerGal",
    priceBasis="USD per gallon of ethanol, at the package's own ethanol density",
)

_PHA = FlowsheetInfo(
    id="pha_sugar_v0",
    title="PHA from fermentable sugar, draft v0",
    description=(
        "Fermentable sugar and ammonia into an aerated batch fermenter, a solids centrifuge and a drum dryer, "
        "giving dried, PHA-rich cell mass. Chemicals and finance are the corn stover reference biorefinery's; "
        "equipment and thermodynamics are BioSTEAM's own."
    ),
    source="this repository",
    program="pha",
    reference=False,
    inputs=[
        FlowsheetInput(key="titre", name="PHA titre at harvest", dimension="massConc", unit="g L-1",
                       fields=["pha_titre"], kind="process",
                       note="sets the water that dilutes the sugar to the harvest broth"),
        FlowsheetInput(key="yield", name="PHA yield on sugar", dimension="yield", unit="g g-1",
                       fields=["pha_yield_substrate"], kind="process",
                       note="sets the polymer reaction's share of the sugar; clipped to the geneOS ceiling when one is stored"),
        FlowsheetInput(key="content", name="PHA share of dry cell mass", dimension="fraction", unit="g g-1",
                       fields=["pha_content_cdw"], kind="process",
                       note="sets the cell-mass reaction's share; records in percent of dry mass become a share"),
        FlowsheetInput(key="productivity", name="PHA volumetric productivity", dimension="volProd", unit="g L-1 h-1",
                       fields=["pha_productivity"], kind="process",
                       note="the batch time is the titre divided by it"),
        FlowsheetInput(key="recovery", name="solids recovered at harvest", dimension="fraction", unit="",
                       kind="process", note="a named person's assumption: the centrifuge's split of polymer and cells"),
        FlowsheetInput(key="sugarPrice", name="price of fermentable sugar", dimension="costUSD", unit="USD kg-1",
                       kind="economic", note="a named person's assumption; the sugar alone is priced, not its dilution water"),
        FlowsheetInput(key="sugarFeed", name="sugar fed", dimension="massFlow", unit="kg h-1",
                       kind="process", note="a named person's assumption; it sets the plant's size"),
    ],
    outputs=["pricePerKgPha", "phaKgPerH", "costLines", "readBack", "conversions"],
    priceOutput="pricePerKgPha",
    priceBasis=PHA_PRICE_BASIS,
    leavesOut=PHA_LEAVES_OUT,
    gridInputs=["titre", "yield", "sugarPrice"],
)

SHELF: dict[str, FlowsheetInfo] = {f.id: f for f in (_CORNSTOVER, _PHA)}

TEST_ONLY: dict[str, FlowsheetInfo] = {
    "toy": FlowsheetInfo(
        id="toy",
        title="Toy flowsheet (STAND-IN for tests)",
        description="A mixer feeding a splitter, whose mass balance is worked by hand in flowsheets/toy.py. Not a process.",
        source="this repository",
        program=None,
        reference=False,
        inputs=[
            FlowsheetInput(key="water", name="water fed", dimension="massFlow", unit="kg h-1", kind="process",
                           note="a STAND-IN input for tests"),
            FlowsheetInput(key="ethanol", name="ethanol fed", dimension="massFlow", unit="kg h-1", kind="process",
                           note="a STAND-IN input for tests"),
            FlowsheetInput(key="split", name="share to the top", dimension="fraction", unit="", kind="process",
                           note="a STAND-IN input for tests"),
        ],
        outputs=["topEthanol", "topWater", "bottomTotal"],
    ),
}


class NotOnShelf(KeyError):
    """A flowsheet id the shelf does not hold, in words."""

    def __str__(self) -> str:  # KeyError quotes its message; say it plainly
        return str(self.args[0]) if self.args else ""


def info(flowsheet_id: str, *, allow_toy: bool = False) -> FlowsheetInfo:
    """The shelf's entry for a flowsheet. The toy is refused unless the
    caller is a test or a fixture and says so."""
    if flowsheet_id in SHELF:
        return SHELF[flowsheet_id]
    if flowsheet_id in TEST_ONLY:
        if allow_toy:
            return TEST_ONLY[flowsheet_id]
        raise NotOnShelf(f"{flowsheet_id} is a STAND-IN for tests and is not on the shelf; "
                         f"the shelf holds {', '.join(SHELF)}")
    raise NotOnShelf(f"there is no flowsheet {flowsheet_id} on the shelf; it holds {', '.join(SHELF)}")
