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
