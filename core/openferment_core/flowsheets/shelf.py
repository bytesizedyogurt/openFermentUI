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
    brothStream   (OF-BLD-020 §6.2) the stream a scenario flowsheet names as
               its fermenter's broth, by the id its own file gives the
               fermenter's outlet (test_seam holds each to its file); a
               train's inlet from a scenario takes it from the newest run.
               A reference names none: its package names its streams.
    package_regression(id)
               a reference biorefinery's own test values (OF-BLD-019 §2.2),
               parsed from the installed package's test file (`ast`, no
               import), with the package, the file and the test named
"""
from __future__ import annotations

import ast
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path

from ..models import FlowsheetInfo, FlowsheetInput, PackageRegression, RegressionValue


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
    packageTest="biorefineries/tests/test_biorefineries.py::test_cornstover",
)

# The dry-grind corn plant's inputs (OF-BLD-019 §2.2): every one is the
# package's own default, listed so a person sees what the plant rests on.
# None holds a value here; the worker reads each back from the package's
# objects after the run (flowsheets/corn_drygrind.py, `read_back`).
_PKG_DEFAULT = "the package's own default, read back after the run"


def _default(key: str, name: str, dimension: str, unit: str, where: str) -> FlowsheetInput:
    return FlowsheetInput(key=key, name=name, dimension=dimension, unit=unit, kind="convention",
                          note=f"{_PKG_DEFAULT}: {where}")


_CORN = FlowsheetInfo(
    id="corn_drygrind",
    title="Dry-grind corn to ethanol, the conventional plant",
    description=(
        "The conventional dry-grind corn ethanol plant the BioSTEAM authors built after Kwiatkowski et al. 2006 "
        "(Industrial Crops and Products): milling and slurry, jet cooking and liquefaction, "
        "saccharification, simultaneous saccharification and fermentation by yeast, the ethanol purification train "
        "of biorefineries.ethanol (beer column, rectifier, molecular sieves), and DDGS and crude corn oil recovered "
        "from the stillage. Run whole on the package's own defaults: the yeast program's reference biorefinery, "
        "with the package's own regression values beside what this installation computes."
    ),
    source=f"{_pkg('biorefineries')}, corn",
    program="yeast",
    reference=True,
    inputs=[
        _default("cornFeed", "corn fed", "massFlow", "kg h-1", "BiorefinerySettings.feedstock_hourly_mass_flow"),
        _default("cornPrice", "price of corn", "costUSD", "USD kg-1", "default_stream_prices['Corn']"),
        _default("ethanolPrice", "price of ethanol", "costUSD", "USD kg-1",
                 "default_stream_prices['Ethanol'], the price at which the package's TEA solves the internal rate of return"),
        _default("ddgsPrice", "price of DDGS (distillers' dried grains with solubles)", "costUSD", "USD kg-1",
                 "default_stream_prices['DDGS']"),
        _default("crudeOilPrice", "price of crude corn oil", "costUSD", "USD kg-1", "default_stream_prices['Crude oil']"),
        _default("enzymePrice", "price of the amylase enzymes", "costUSD", "USD kg-1", "default_stream_prices['Enzyme']"),
        _default("yeastPrice", "price of yeast", "costUSD", "USD kg-1", "default_stream_prices['Yeast']"),
        _default("electricityPrice", "price of electricity", "costUSD", "USD kWh-1",
                 "default_load_utility_settings(power_price=…)"),
        _default("ssfYield", "glucose to ethanol in the fermenter, as a share of the theoretical", "fraction", "",
                 "SimultaneousSaccharificationFermentation(yield_=…)"),
        _default("ssfTime", "fermentation batch time", "time", "h", "SimultaneousSaccharificationFermentation(tau=…)"),
        _default("ssfTemperature", "fermenter temperature", "temp", "K", "SimultaneousSaccharificationFermentation(T=…)"),
        _default("ssfWorkingVolume", "fermenter working volume, as a share of the vessel", "fraction", "",
                 "SimultaneousSaccharificationFermentation(V_wf=…)"),
        _default("solidsContent", "corn in the slurry", "fraction", "g g-1",
                 "default_process_parameters['slurry_solids_content']"),
        _default("yeastLoading", "yeast loaded on the mash", "fraction", "g g-1",
                 "default_process_parameters['yeast_loading']"),
        _default("operatingDays", "operating days a year", "time", "d", "default_tea_parameters['operating_days']"),
        _default("incomeTax", "income tax", "fraction", "", "default_tea_parameters['income_tax']"),
        _default("langFactor", "Lang factor, installed over purchased equipment cost", "factor", "",
                 "default_tea_parameters['lang_factor']"),
        _default("laborCost", "labour cost", "costUSD", "USD yr-1", "default_tea_parameters['labor_cost']"),
        _default("startYear", "first year of the plant's life", "year", "", "default_tea_parameters['duration']"),
        _default("endYear", "last year of the plant's life", "year", "", "default_tea_parameters['duration']"),
        _default("depreciation", "depreciation schedule", "schedule", "", "default_tea_parameters['depreciation']"),
        _default("cepci", "plant cost index (CEPCI)", "index", "", "BiorefinerySettings(CEPCI=…)"),
    ],
    outputs=["ethanolPriceUsdPerKg", "IRR", "ethanolKgPerH", "cornKgPerH", "measured", "checks", "readBack", "references"],
    priceOutput="ethanolPriceUsdPerKg",
    priceBasis=("USD per kg of the ethanol product stream as the package makes it (ethanol with its denaturant): "
                "the package's own price, at which its TEA solves the internal rate of return"),
    packageTest="biorefineries/tests/test_biorefineries.py::test_corn",
)

# OF-BLD-019 §2.3: glucose to ethanol, ours. What it leaves out is
# flowsheets/ethanol_glucose_v0.LEAVES_OUT, repeated here as data so the
# service reads it without BioSTEAM (test_proforma_ethanol holds the two equal).
ETHANOL_LEAVES_OUT = [
    "where the glucose comes from: it arrives as clean glucose, priced as such",
    "cell mass and by-products: the glucose the yield does not turn into ethanol leaves unconverted in the stillage",
    "the scrubber that recovers ethanol from the fermenter's gas",
    "stillage handling and co-products",
    "wastewater treatment and the boiler",
]
ETHANOL_PRICE_BASIS = "USD per kg of fuel-grade ethanol, as the product leaves its tank"

_ETHANOL = FlowsheetInfo(
    id="ethanol_glucose_v0",
    title="Glucose to ethanol, draft v0",
    description=(
        "A glucose solution into a batch fermenter, then the ethanol purification train of the BioSTEAM "
        "reference designs (beer column, rectifier, molecular sieves), giving fuel-grade ethanol. The fermenter "
        "turns glucose into ethanol at the bound yield as a share of the theoretical yield, for a batch time of "
        "titre over productivity. Chemicals and finance are the dry-grind corn ethanol plant's; equipment and "
        "thermodynamics are BioSTEAM's own; no number is the flowsheet's."
    ),
    source="this repository",
    program="yeast",
    reference=False,
    inputs=[
        FlowsheetInput(key="feed_glucose_conc", name="glucose in the fermenter's feed", dimension="massConc",
                       unit="g L-1", fields=["medium_component_conc"], kind="process",
                       note="records of a medium component whose carbon source is glucose; sets the water that "
                            "dilutes the glucose, by thermosteam's volume of the solution"),
        FlowsheetInput(key="titre", name="ethanol titre at harvest", dimension="massConc", unit="g L-1",
                       fields=["ethanol_titre"], kind="process",
                       note="with the productivity, sets the batch time; the beer's own ethanol follows from "
                            "the feed's glucose and the yield, and the run reads it back"),
        FlowsheetInput(key="yield", name="ethanol yield on glucose", dimension="yield", unit="g g-1",
                       fields=["ethanol_yield_substrate"], kind="process",
                       note="the fermenter's conversion is this yield over the theoretical yield of the reaction; "
                            "a case above the theoretical yield cannot run, and says so"),
        FlowsheetInput(key="productivity", name="ethanol volumetric productivity", dimension="volProd",
                       unit="g L-1 h-1", fields=["ethanol_productivity"], kind="process",
                       note="the batch time is the titre divided by it"),
        FlowsheetInput(key="plant_scale", name="ethanol fermented in a year", dimension="massFlow", unit="t yr-1",
                       kind="economic",
                       note="a named person's assumption; with the yield it sets the glucose fed, so the plant's size"),
        FlowsheetInput(key="glucose_price", name="price of glucose", dimension="costUSD", unit="USD kg-1",
                       kind="economic", note="a named person's assumption; the glucose alone is priced, not its water"),
        FlowsheetInput(key="ethanol_purity", name="ethanol purity", dimension="fraction", unit="",
                       kind="convention",
                       note="fuel grade: the ethanol the package's molecular sieves give, with no denaturant "
                            "blended; a convention every run's basis names, and the run reads the purity back"),
    ],
    outputs=["pricePerKgEthanol", "ethanolKgPerH", "costLines", "readBack"],
    priceOutput="pricePerKgEthanol",
    priceBasis=ETHANOL_PRICE_BASIS,
    leavesOut=ETHANOL_LEAVES_OUT,
    gridInputs=["titre", "yield", "glucose_price"],
    brothStream="beer",
)

# OF-BLD-020 §6.1 (D11): a vessel and a train, priced. Its scenarios are made
# in the browser alone (no seed scenario names it: check:seed holds a seed's
# modelId to BIOSTEAM_FLOWSHEETS, which leaves it out), each naming the kept
# vessel design and train run it is built from (`builtFrom`). Its program is
# its train's; a train runs only on a program with a chemical set
# (pureos/train_spec.PROGRAM_CHEMICALS, the yeast program's alone tonight), so
# the entry is the yeast program's and a train of another program is refused
# in words (test_custom_train holds the two equal).
COMPOSITE = "custom_train_v1"
COMPOSITE_BUILT_FROM = ["fermos.vessel", "pureos.train_run"]
COMPOSITE_PRICE_BASIS = ("USD per kg of the product the train traces (ethanol, for the yeast program), contained in "
                         "the train's product stream as it leaves the train's last unit")
COMPOSITE_LEAVES_OUT = [
    "where the glucose comes from: it arrives as clean glucose, priced as such",
    "every outlet the train does not send on leaves the plant unpriced: no co-product credit and no waste treatment",
    "by-products the vessel's reaction does not make, and the scrubber that would recover product from the fermenter's gas",
    "wastewater treatment and the boiler",
]

_CUSTOM_TRAIN = FlowsheetInfo(
    id=COMPOSITE,
    title="A vessel and a train, priced",
    description=(
        "A glucose solution into the fermenter fermOS designed (a kept fermos.vessel design: BioSTEAM's "
        "AeratedBioreactor or NREL batch fermenter, rebuilt as the same class with every design parameter as the "
        "design holds it, running the reaction the design was built on), its beer through the units of a train pureOS "
        "ran (a kept pureos.train_run: each unit the same catalogue type, class and values as that run held them), "
        "priced with the dry-grind corn ethanol plant's TEA (biorefineries.corn.create_tea, ConventionalEthanolTEA), "
        "its financial parameters in the panel's Finance group as the package's defaults until a person sets one. "
        "A scenario on it names the vessel design and the train run. The train's own inlet is not an input: the "
        "fermenter's beer is its inlet. Only the yeast program has a chemical set, so a vessel or a train of another "
        "program is refused."
    ),
    source="this repository",
    program="yeast",
    reference=False,
    builtFrom=COMPOSITE_BUILT_FROM,
    inputs=[
        FlowsheetInput(key="feed_glucose_conc", name="glucose in the fermenter's feed", dimension="massConc",
                       unit="g L-1", fields=["medium_component_conc"], kind="process",
                       note="records of a medium component whose carbon source is glucose; sets the water that "
                            "dilutes the glucose, by thermosteam's volume of the solution"),
        FlowsheetInput(key="titre", name="ethanol titre at harvest", dimension="massConc", unit="g L-1",
                       fields=["ethanol_titre"], kind="process",
                       note="with the productivity, sets the fermenter's batch time; the reacting time the vessel was "
                            "designed for is named beside it in the run's basis"),
        FlowsheetInput(key="yield", name="ethanol yield on glucose", dimension="yield", unit="g g-1",
                       fields=["ethanol_yield_substrate"], kind="process",
                       note="sets the conversion of the vessel's reaction: the yield over the ethanol that reaction "
                            "makes of a gram of glucose; a case above it cannot run, and says so"),
        FlowsheetInput(key="productivity", name="ethanol volumetric productivity", dimension="volProd",
                       unit="g L-1 h-1", fields=["ethanol_productivity"], kind="process",
                       note="the batch time is the titre divided by it"),
        FlowsheetInput(key="plant_scale", name="ethanol fermented in a year", dimension="massFlow", unit="t yr-1",
                       kind="economic",
                       note="the vessel's scale: the plant scale its design names (the vessel design is its source); "
                            "a design of one vessel's batch volume names none, and then it is a named person's "
                            "assumption. With the yield it sets the glucose fed, so the plant's size"),
        FlowsheetInput(key="glucose_price", name="price of glucose", dimension="costUSD", unit="USD kg-1",
                       kind="economic", note="a named person's assumption; the glucose alone is priced, not its water"),
    ],
    outputs=["pricePerKgProduct", "productKgPerH", "costLines", "readBack"],
    priceOutput="pricePerKgProduct",
    priceBasis=COMPOSITE_PRICE_BASIS,
    leavesOut=COMPOSITE_LEAVES_OUT,
    gridInputs=["titre", "yield", "glucose_price"],
    brothStream="beer",
)

SHELF: dict[str, FlowsheetInfo] = {f.id: f for f in (_CORNSTOVER, _CORN, _ETHANOL, _CUSTOM_TRAIN)}

# The package module each reference biorefinery runs (OF-BLD-019 §2.2).
REFERENCE_MODULES = {"cornstover_benchmark": "biorefineries.cornstover", "corn_drygrind": "biorefineries.corn"}

# What a reference run changes about its package for this installation to
# run it, as (what, why); the basis of every run carries each as a
# `convention` input. No value of the package's is changed.
REFERENCE_COMPAT = {
    "corn_drygrind": [(
        "SimultaneousSaccharificationFermentation._ins_size_is_fixed = False",
        "biorefineries.corn's SimultaneousSaccharificationFermentation passes its two inlets (the mash and the "
        "yeast) to bst.BatchBioreactor, which declares one fixed inlet in biosteam 2.54.0, so corn.load() stops with "
        "'at most 1 streams expected; 2 given'. The flowsheet lets the unit take them, as biosteam's own "
        "NRELEthanolFermentation declares; the unit's _run already mixes every inlet. No number of the package's "
        "is changed, and the package's own test values hold within its tolerance.",
    )],
}

# The quantities the package's test template asserts
# (biorefineries/tests/test_biorefineries.py, generate_code), by the
# expression it writes, in words and in the units BioSTEAM states them:
# the TEA's annual amounts in USD/yr, its capital in USD, prices in USD/kg,
# the UnitGroup's duties and electricity in its DUTY_UNITS and ELEC_UNITS
# (a sim test holds these two to biosteam's own).
TEST_QUANTITIES = {
    "tea.IRR": ("internal rate of return", ""),
    "feedstock.price": ("feedstock price", "USD/kg"),
    "product.price": ("product price", "USD/kg"),
    "tea.sales": ("sales", "USD/yr"),
    "tea.material_cost": ("material cost", "USD/yr"),
    "tea.installed_equipment_cost": ("installed equipment cost", "USD"),
    "tea.utility_cost": ("utility cost", "USD/yr"),
    "units.get_heating_duty()": ("heating duty", "GJ/hr"),
    "units.get_cooling_duty()": ("cooling duty", "GJ/hr"),
    "units.get_electricity_consumption()": ("electricity consumption", "MW"),
    "units.get_electricity_production()": ("electricity production", "MW"),
}


def _installed_file(relative: str) -> Path | None:
    """A file of the installed biorefineries distribution, found through its
    metadata (nothing is imported), or None when it is not installed here."""
    try:
        path = Path(str(distribution("biorefineries").locate_file(relative)))
    except PackageNotFoundError:
        return None
    return path if path.is_file() else None


@lru_cache(maxsize=None)
def package_regression(flowsheet_id: str) -> PackageRegression | None:
    """The values a reference biorefinery's own package test asserts, read
    from the installed test file: each `assert np.allclose(<expression>,
    <value>, rtol=<tolerance>)` of the named test, in the order the test
    writes them. None for a flowsheet with no package test, or when the
    package or the test is not found here. Nothing is retyped: the file is
    the authority, and the regression names it."""
    entry = SHELF.get(flowsheet_id)
    if entry is None or not entry.packageTest:
        return None
    file, _, test = entry.packageTest.partition("::")
    return regression_of(file, test)


def regression_of(file: str, test: str) -> PackageRegression | None:
    """The values one test of the installed biorefineries asserts (`file`
    relative to the distribution, `test` a function in it), read as
    `package_regression` reads them; None when the file or the test is not
    found here. The library plant runner (engine/library.py) names a plant's
    test this way."""
    path = _installed_file(file)
    if path is None:
        return None
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == test), None)
    if fn is None:
        return None
    values = []
    for stmt in fn.body:
        call = stmt.test if isinstance(stmt, ast.Assert) else None
        if not (isinstance(call, ast.Call) and ast.unparse(call.func) == "np.allclose" and len(call.args) >= 2):
            continue
        expression = ast.unparse(call.args[0])
        rtol = next((k.value for k in call.keywords if k.arg == "rtol"), None)
        label, unit = TEST_QUANTITIES.get(expression, (expression, ""))
        values.append(RegressionValue(
            expression=expression, label=label, unit=unit, package=float(ast.literal_eval(call.args[1])),
            # numpy.allclose's own default when the test names none
            rtol=float(ast.literal_eval(rtol)) if rtol is not None else 1e-05))
    return PackageRegression(package=_pkg("biorefineries"), file=file, test=test, values=values)

# The dry-grind corn plant's TEA parameters (OF-BLD-020 §6.1, Appendix 2 §D),
# read from the installed package's own file without importing it, as the
# package test is (`package_regression`): `custom_train_v1` prices with
# `biorefineries.corn.create_tea`, and the parameter panel serves each of
# these as the library's default until a person sets one. The worker builds
# that TEA from the package's dict itself, and a sim test holds the two
# equal. BioSTEAM's depreciation schedules are read the same way, from its
# TEA class's `depreciation_schedules`.
TEA_DEFAULTS_FILE = "biorefineries/corn/tea.py"
TEA_DEFAULTS_NAME = "default_tea_parameters"
TEA_CLASS_FILE = "biosteam/_tea.py"


def _dist_file(dist: str, relative: str) -> Path | None:
    try:
        path = Path(str(distribution(dist).locate_file(relative)))
    except PackageNotFoundError:
        return None
    return path if path.is_file() else None


@lru_cache(maxsize=None)
def package_tea_defaults() -> dict[str, object] | None:
    """`biorefineries.corn.tea.default_tea_parameters` as the installed file
    writes it (`dict(IRR=…, duration=(…), …)`), each value read with
    `ast.literal_eval`; tuples become lists. None when the package or the
    name is not found here."""
    path = _dist_file("biorefineries", TEA_DEFAULTS_FILE)
    if path is None:
        return None
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == TEA_DEFAULTS_NAME
                                                     for t in node.targets)):
            continue
        call = node.value
        if isinstance(call, ast.Call) and ast.unparse(call.func) == "dict" and not call.args:
            out: dict[str, object] = {}
            for k in call.keywords:
                v = ast.literal_eval(k.value)
                out[str(k.arg)] = list(v) if isinstance(v, tuple) else v
            return out
        if isinstance(call, ast.Dict):
            return {str(ast.literal_eval(k)): (lambda v: list(v) if isinstance(v, tuple) else v)(ast.literal_eval(v))
                    for k, v in zip(call.keys, call.values) if k is not None}
    return None


@lru_cache(maxsize=None)
def depreciation_schedules() -> list[str] | None:
    """The depreciation schedules BioSTEAM's TEA holds tables for, as its
    `depreciation` takes them by name ('MACRS7'), read from the installed
    class's `depreciation_schedules` keys. None when not found here."""
    table = _depreciation_table()
    return None if table is None else [name for name, _ in table]


@lru_cache(maxsize=None)
def depreciation_lengths() -> dict[str, int]:
    """How many years each schedule BioSTEAM's TEA holds a table for writes
    the capital off over: the length of its table's array, read from the
    installed class's `depreciation_schedules` without importing it (a
    MACRS schedule's table runs a year past its name, by the half-year
    convention). BioSTEAM refuses a schedule longer than the plant's life
    (its `_fill_depreciation_array`), so the panel says so before a run
    (OF-BLD-020 §6.R, main-29). Empty when not found here; a table this
    reader cannot count is left out."""
    return {name: n for name, n in (_depreciation_table() or []) if n is not None}


def _depreciation_table() -> list[tuple[str, int | None]] | None:
    """Each schedule of BioSTEAM's TEA table by name, with its array's
    length when the file writes it as `np.array([...])`; None when the class
    or its table is not found here."""
    path = _dist_file("biosteam", TEA_CLASS_FILE)
    if path is None:
        return None
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TEA"), None)
    if cls is None:
        return None
    for node in cls.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign)
                                                                       and len(node.targets) == 1 else None)
        if isinstance(target, ast.Name) and target.id == "depreciation_schedules" and isinstance(node.value, ast.Dict):
            out: list[tuple[str, int | None]] = []
            for k, v in zip(node.value.keys, node.value.values):
                key = ast.literal_eval(k) if k is not None else None
                if isinstance(key, tuple) and all(isinstance(x, (str, int)) for x in key):
                    arr = v.args[0] if isinstance(v, ast.Call) and len(v.args) == 1 else None
                    out.append(("".join(str(x) for x in key), len(arr.elts) if isinstance(arr, ast.List) else None))
            return out
    return None


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
