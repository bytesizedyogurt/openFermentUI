"""The benchmark (OF-BLD-014 §8.2): a published biorefinery, run end to end.

`biorefineries.cornstover` is the corn stover ethanol biorefinery the BioSTEAM
authors built to the NREL design report (Humbird et al. 2011,
NREL/TP-5100-47764) and published with BioSTEAM (Cortes-Peña et al. 2020,
ACS Sustainable Chem. Eng., doi:10.1021/acssuschemeng.9b07040). Running it
with the package's own defaults and arriving at the minimum ethanol selling
price measured for this version (B.3: 1.968 USD per gallon) shows this
installation simulates and prices a flowsheet as its authors do. Nothing here
is set by openFerment: every setting is the package's, read back after the run.
"""
from __future__ import annotations

from importlib.metadata import version
from typing import Any

PACKAGE = "biorefineries.cornstover"
REFERENCES = [
    "Humbird, D. et al. Process Design and Economics for Biochemical Conversion of Lignocellulosic Biomass to "
    "Ethanol: Dilute-Acid Pretreatment and Enzymatic Hydrolysis of Corn Stover. NREL/TP-5100-47764, 2011. "
    "doi:10.2172/1013269",
    "Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S. BioSTEAM: A Fast and Flexible Platform for the Design, "
    "Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty. ACS Sustainable Chem. Eng. 2020. "
    "doi:10.1021/acssuschemeng.9b07040",
]


def _settings(tea: Any) -> dict[str, Any]:
    years = tea.duration
    return {
        "rateOfReturn": float(tea.IRR),
        "operatingDays": float(tea.operating_days),
        "incomeTax": float(tea.income_tax),
        "startYear": int(years[0]),
        "endYear": int(years[1]),
    }


# ── its reference run (OF-BLD-019 §2.2) ─────────────────────────────────
# The same plant through GET/POST /api/proforma/reference/cornstover_benchmark,
# as one `proforma.reference` artifact with every table. `run()` above stays
# the benchmark's, unchanged; the reference run builds its own plant afresh,
# as `cornstover.load()` names it, inside the worker's `package_defaults()`,
# and leaves the benchmark's cached plant as it was.


def load() -> Any:
    from biorefineries import cornstover as cs

    return cs.Biorefinery("corn stover ethanol", load=False, save=False)


def parts(br: Any) -> dict[str, Any]:
    """The system, the package's TEA, the ethanol at the price the package
    solved for it as it built the plant, and the corn stover feedstock."""
    return {"system": br.system, "tea": br.tea, "product": br.ethanol, "feedstock": br.cornstover,
            "price": None, "basis_flow": float(br.ethanol.F_mass), "basis": "kg of the ethanol product stream"}


def outputs(br: Any) -> dict[str, Any]:
    from biorefineries import cornstover as cs

    per_kg = float(br.ethanol.price)
    return {
        "package": f"{PACKAGE}@{version('biorefineries')}",
        "mespUsdPerGal": per_kg * float(cs.ethanol_density_kggal),
        "mespUsdPerKg": per_kg,
        "ethanolDensityKgPerGal": float(cs.ethanol_density_kggal),
        "settings": _settings(br.tea),
        "references": REFERENCES,
    }


def run() -> dict[str, Any]:
    from biorefineries import cornstover as cs

    br = cs.Biorefinery()
    tea = br.cornstover_tea
    per_kg = float(tea.solve_price(br.ethanol))
    years = tea.duration
    return {
        "package": f"{PACKAGE}@{version('biorefineries')}",
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
        "references": REFERENCES,
    }
