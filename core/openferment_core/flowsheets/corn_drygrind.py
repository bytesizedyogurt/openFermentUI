"""The dry-grind corn ethanol plant (OF-BLD-019 §2.2): a published reference
biorefinery, run whole on its package's own defaults.

`biorefineries.corn` is the conventional dry-grind corn ethanol plant the
BioSTEAM authors modelled after Kwiatkowski et al. 2006 (milling, jet
cooking, liquefaction, saccharification, simultaneous saccharification and
fermentation by yeast, `biorefineries.ethanol`'s purification train, DDGS
and crude corn oil from the stillage). It is a yeast ethanol process end to
end, and the yeast program's reference biorefinery. The package's own test
(`biorefineries/tests/test_biorefineries.py::test_corn`) holds eleven of its
numbers; `test_proforma_slow` holds this installation to them, read from that
file (flowsheets/shelf.py, `package_regression`).

Nothing here is set by openFerment. `load()` is what the package's test does
under its `default_settings` decorator: BioSTEAM's defaults first (the
worker's `package_defaults`, which also puts back afterwards whatever the
worker held before), then `corn.load()`. The plant is built afresh each run
(`cache={}`), so a run never reads a plant an earlier run left. Every
setting the shelf lists is read back from the package's objects after the
run (`read_back`).

ONE CHANGE TO THE PACKAGE, and why (shelf.REFERENCE_COMPAT, in every run's
basis): biorefineries 2.35.1's `SimultaneousSaccharificationFermentation`
passes two inlets to `bst.BatchBioreactor`, which declares one fixed inlet in
biosteam 2.54.0, so `corn.load()` stops before it builds. `_compat` lets the
unit take its inlets, as biosteam's own `NRELEthanolFermentation` declares;
no value of the package's changes, and its test values hold.

Imported by the Proforma worker alone (E.6).
"""
from __future__ import annotations

from importlib.metadata import version
from typing import Any

PACKAGE = "biorefineries.corn"
# The two the package's own README (biorefineries/corn/README.md) cites, as
# it gives them, and the BioSTEAM paper the benchmark cites.
REFERENCES = [
    "Kwiatkowski, J. R.; McAloon, A. J.; Taylor, F.; Johnston, D. B. Modeling the process and costs of fuel ethanol "
    "production by the corn dry-grind process. Industrial Crops and Products 2006, 23, 288–296. "
    "https://www.sciencedirect.com/science/article/pii/S0926669005000944",
    "Kurambhatti, C.; Kumar, D.; Singh, V. Impact of Fractionation Process on the Technical and Economic Viability "
    "of Corn Dry Grind Ethanol Process. Processes 2019, 7, 578. https://www.mdpi.com/2227-9717/7/9/578",
    "Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S. BioSTEAM: A Fast and Flexible Platform for the Design, "
    "Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty. ACS Sustainable Chem. Eng. 2020. "
    "doi:10.1021/acssuschemeng.9b07040",
]


def _compat(corn: Any) -> None:
    """Let the package's SSF unit take the two inlets its own system gives it
    (the module docstring says why; shelf.REFERENCE_COMPAT says it in every
    basis)."""
    corn.units.SimultaneousSaccharificationFermentation._ins_size_is_fixed = False


def load() -> Any:
    """The package's plant, built afresh by `corn.load()` with every default
    its own; the worker calls this inside `package_defaults()`."""
    from biorefineries import corn

    _compat(corn)
    corn.load(cache={})
    return corn


def parts(corn: Any) -> dict[str, Any]:
    """What the worker reads the run's tables from (OF-BLD-019 §2.1): the
    system, the package's TEA, the ethanol product and the corn feedstock,
    as the package's test names them. The price is the package's own, left
    as the package set it (`price` None), and the per-unit lines divide by
    the ethanol stream's flow."""
    return {"system": corn.system, "tea": corn.tea, "product": corn.ethanol, "feedstock": corn.corn,
            "price": None, "basis_flow": float(corn.ethanol.F_mass),
            "basis": "kg of the ethanol product stream as the package makes it (ethanol with its denaturant)"}


def outputs(corn: Any) -> dict[str, Any]:
    """The plant's own result: the internal rate of return its TEA solves at
    the package's ethanol price, and the flows that price is on."""
    return {
        "package": f"{PACKAGE}@{version('biorefineries')}",
        "ethanolPriceUsdPerKg": float(corn.ethanol.price),
        "IRR": float(corn.tea.IRR),
        "ethanolKgPerH": float(corn.ethanol.F_mass),
        "cornKgPerH": float(corn.corn.F_mass),
        "references": REFERENCES,
    }


def read_back(corn: Any) -> dict[str, float | str]:
    """Every input the shelf lists for this plant, read from the package's
    objects as the run left them (each the package's default)."""
    import biosteam as bst

    tea, ssf = corn.tea, corn.V405
    process = corn.biorefinery.biorefinery_settings.process_parameters
    return {
        "cornFeed": float(corn.corn.F_mass),
        "cornPrice": float(corn.corn.price),
        "ethanolPrice": float(corn.ethanol.price),
        "ddgsPrice": float(corn.DDGS.price),
        "crudeOilPrice": float(corn.crude_oil.price),
        "enzymePrice": float(corn.alpha_amylase.price),
        "yeastPrice": float(corn.yeast.price),
        "electricityPrice": float(bst.PowerUtility.price),
        "ssfYield": float(ssf.reaction.X),
        "ssfTime": float(ssf.tau),
        "ssfTemperature": float(ssf.T),
        "ssfWorkingVolume": float(ssf.V_wf),
        "solidsContent": float(process["slurry_solids_content"]),
        "yeastLoading": float(process["yeast_loading"]),
        "operatingDays": float(tea.operating_days),
        "incomeTax": float(tea.income_tax),
        "langFactor": float(tea.lang_factor),
        "laborCost": float(tea.labor_cost),
        "startYear": float(tea.duration[0]),
        "endYear": float(tea.duration[1]),
        "depreciation": str(tea.depreciation),
        "cepci": float(bst.CE),
    }
