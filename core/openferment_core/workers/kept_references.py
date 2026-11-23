"""The replay of runs kept from two retired shelf entries (alpha 2.2 D8).

Proforma's shelf held two hand-written reference entries, `cornstover_benchmark`
and `corn_drygrind`, which retired at alpha 2.2 C.6: the library shelf's
`cornstover` and `corn` run the same packages' plants (engine/library.py). The
artifact tools their runs were kept under, `proforma.reference` and
`proforma_benchmark`, stay registered, so an artifact a person kept replays
through the code that computed it, held here and reached by the Proforma
worker's two replay ops alone (docs/api/workers.md):

    replay_reference   a `proforma.reference` artifact: the plant its basis
                       names, built afresh inside the worker's
                       `package_defaults()`, its package's outputs, the
                       quantities its package test asserts, its defaults read
                       back and every table, as the entry's reference run read
                       them
    replay_benchmark   a `proforma_benchmark` artifact: the corn stover plant
                       built afresh and its price solved as the package solves it

`PLANTS` holds each entry's plant by the entry's id, each with `load()`,
`parts(built)`, `outputs(built)` and, for the dry-grind corn plant, its
`read_back(built)`. Nothing here is set by openFerment: every setting is the
package's, read back after the run. The one change to a package is the corn
plant's `_compat`, which its reference run's basis states as a convention
(biorefineries 2.35.1's SimultaneousSaccharificationFermentation passes two
inlets to `bst.BatchBioreactor`, which declares one fixed inlet in biosteam
2.54.0; the unit takes them, as biosteam's own NRELEthanolFermentation
declares, and no value of the package's changes).

Imported by the Proforma worker alone (E.6).
"""
from __future__ import annotations

from importlib.metadata import version
from typing import Any


class Cornstover:
    """`cornstover_benchmark`: the corn stover ethanol biorefinery the BioSTEAM
    authors built to the NREL design report, `biorefineries.cornstover`."""

    PACKAGE = "biorefineries.cornstover"
    REFERENCES = [
        "Humbird, D. et al. Process Design and Economics for Biochemical Conversion of Lignocellulosic Biomass to "
        "Ethanol: Dilute-Acid Pretreatment and Enzymatic Hydrolysis of Corn Stover. NREL/TP-5100-47764, 2011. "
        "doi:10.2172/1013269",
        "Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S. BioSTEAM: A Fast and Flexible Platform for the Design, "
        "Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty. ACS Sustainable Chem. Eng. 2020. "
        "doi:10.1021/acssuschemeng.9b07040",
    ]

    @staticmethod
    def settings(tea: Any) -> dict[str, Any]:
        years = tea.duration
        return {
            "rateOfReturn": float(tea.IRR),
            "operatingDays": float(tea.operating_days),
            "incomeTax": float(tea.income_tax),
            "startYear": int(years[0]),
            "endYear": int(years[1]),
        }

    @staticmethod
    def load() -> Any:
        from biorefineries import cornstover as cs

        return cs.Biorefinery("corn stover ethanol", load=False, save=False)

    @staticmethod
    def parts(br: Any) -> dict[str, Any]:
        """The system, the package's TEA, the ethanol at the price the package
        solved for it as it built the plant, and the corn stover feedstock."""
        return {"system": br.system, "tea": br.tea, "product": br.ethanol, "feedstock": br.cornstover,
                "price": None, "basis_flow": float(br.ethanol.F_mass), "basis": "kg of the ethanol product stream"}

    @staticmethod
    def outputs(br: Any) -> dict[str, Any]:
        from biorefineries import cornstover as cs

        per_kg = float(br.ethanol.price)
        return {
            "package": f"{Cornstover.PACKAGE}@{version('biorefineries')}",
            "mespUsdPerGal": per_kg * float(cs.ethanol_density_kggal),
            "mespUsdPerKg": per_kg,
            "ethanolDensityKgPerGal": float(cs.ethanol_density_kggal),
            "settings": Cornstover.settings(br.tea),
            "references": Cornstover.REFERENCES,
        }


class Corn:
    """`corn_drygrind`: the conventional dry-grind corn ethanol plant the
    BioSTEAM authors modelled after Kwiatkowski et al. 2006, `biorefineries.corn`."""

    PACKAGE = "biorefineries.corn"
    # The two the package's own README (biorefineries/corn/README.md) cites,
    # as it gives them, and the BioSTEAM paper.
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

    @staticmethod
    def _compat(corn: Any) -> None:
        """Let the package's SSF unit take the two inlets its own system gives
        it (the module docstring says why; the run's basis states it)."""
        corn.units.SimultaneousSaccharificationFermentation._ins_size_is_fixed = False

    @staticmethod
    def load() -> Any:
        """The package's plant, built afresh by `corn.load()` with every default
        its own; the worker calls this inside `package_defaults()`."""
        from biorefineries import corn

        Corn._compat(corn)
        corn.load(cache={})
        return corn

    @staticmethod
    def parts(corn: Any) -> dict[str, Any]:
        """The system, the package's TEA, the ethanol product and the corn
        feedstock, as the package's test names them; the price left as the
        package set it, and the per-unit lines on the ethanol stream's flow."""
        return {"system": corn.system, "tea": corn.tea, "product": corn.ethanol, "feedstock": corn.corn,
                "price": None, "basis_flow": float(corn.ethanol.F_mass),
                "basis": "kg of the ethanol product stream as the package makes it (ethanol with its denaturant)"}

    @staticmethod
    def outputs(corn: Any) -> dict[str, Any]:
        """The internal rate of return the plant's TEA solves at the package's
        ethanol price, and the flows that price is on."""
        return {
            "package": f"{Corn.PACKAGE}@{version('biorefineries')}",
            "ethanolPriceUsdPerKg": float(corn.ethanol.price),
            "IRR": float(corn.tea.IRR),
            "ethanolKgPerH": float(corn.ethanol.F_mass),
            "cornKgPerH": float(corn.corn.F_mass),
            "references": Corn.REFERENCES,
        }

    @staticmethod
    def read_back(corn: Any) -> dict[str, float | str]:
        """Every input the entry listed for this plant, read from the
        package's objects as the run left them (each the package's default)."""
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


# Each retired entry's plant, by the entry's id as its runs' basis names it.
PLANTS: dict[str, Any] = {"cornstover_benchmark": Cornstover, "corn_drygrind": Corn}


def plant(entry: str) -> Any:
    """The plant a retired entry's kept run replays, or KeyError in words."""
    if entry not in PLANTS:
        raise KeyError(f"{entry} is no retired reference entry whose kept runs replay here; they are "
                       f"{', '.join(PLANTS)}")
    return PLANTS[entry]


def benchmark() -> dict[str, Any]:
    """A kept benchmark's computation: the corn stover plant built afresh
    (`load=False`, `save=False`, so the package's own cache neither hands
    back a plant an earlier call built nor keeps this one), its price solved
    as the package solves it. The worker calls it inside `package_defaults()`."""
    from biorefineries import cornstover as cs

    br = cs.Biorefinery(load=False, save=False)
    tea = br.cornstover_tea
    per_kg = float(tea.solve_price(br.ethanol))
    years = tea.duration
    return {
        "package": f"{Cornstover.PACKAGE}@{version('biorefineries')}",
        "biosteam": version("biosteam"),
        "mespUsdPerGal": per_kg * float(cs.ethanol_density_kggal),
        "mespUsdPerKg": per_kg,
        "ethanolDensityKgPerGal": float(cs.ethanol_density_kggal),
        "settings": {
            "rateOfReturn": float(tea.IRR),
            "operatingDays": float(tea.operating_days),
            "incomeTax": float(tea.income_tax),
            "startYear": int(years[0]),
            "endYear": int(years[1]),
        },
        "references": Cornstover.REFERENCES,
    }
