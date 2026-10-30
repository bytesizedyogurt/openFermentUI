"""Stand-ins for tests: invented records and a closed-form evaluator.

TEST INFRASTRUCTURE, moved out of `openferment_core/demo.py` when alpha 2.0
deleted the demo fixtures (stage 1, ADR-010). Every value here was typed for a
test of the binding, override, ceiling and run-contract rules; none is a
measurement, a parameter of any organism, or a result. Stage 4 replaces these
with fixtures read from the `biorefineries` library plants (ADR-004); until
then the tests that need a binding pool and a fast evaluator import this file.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from typing import Any

CORE = Path(__file__).resolve().parent.parent


AT = "2026-09-15T09:00:00Z"


_SHAPE = {"x0": 0.12, "mu": 0.3, "xmax": 9.0, "p0": 0.05, "alpha": 0.35, "beta": 0.015, "s0": 60.0, "gamma": 4.2, "delta": 0.04}


def fermos_sample_series() -> list[dict[str, Any]]:
    import math

    def at(t: float) -> tuple[float, float, float]:
        c = _SHAPE
        denom = c["x0"] + (c["xmax"] - c["x0"]) * math.exp(-c["mu"] * t)
        x = c["x0"] * c["xmax"] / denom
        integral = c["xmax"] * t + (c["xmax"] / c["mu"]) * math.log(denom / c["xmax"])
        return x, c["p0"] + c["alpha"] * (x - c["x0"]) + c["beta"] * integral, c["s0"] - c["gamma"] * (x - c["x0"]) - c["delta"] * integral

    def jitter(i: int, scale: float) -> float:
        u = math.sin(i * 12.9898 + 78.233) * 43758.5453
        return (u - math.floor(u) - 0.5) * 2 * scale

    hours = [i * 2.5 for i in range(14)]
    out = []
    for k, (role, label, scale) in enumerate((("biomass", "Dry cell weight (sample)", 0.15), ("product", "Polymer (sample)", 0.08),
                                             ("substrate", "Sugar (sample)", 0.6))):
        out.append({"measureId": f"sample-{role}", "label": label, "unit": "g L-1", "role": role, "points": [
            {"t": t, "value": round(max(0.0, at(t)[k] + jitter(i + 31 * (k + 1), scale)), 3), "entryId": f"sample-{role}-{i}", "confirmed": True}
            for i, t in enumerate(hours)]})
    return out


# OF-BLD-019 §5.1: a fermOS fit feeds the fermenter. The sample time course
# above (INVENTED) relabelled as a STAND-IN ethanol run on a deposition no
# browser holds, fitted and forecast through the real code in a scratch
# store; the forecast runs STANDIN_FORECAST_H hours, a setting of this
# fixture, so that its median sugar is spent. GET /api/fermos/fits for every
# flowsheet with nothing on file and with the two on file (each answered or
# refused in the service's words), and the yeast flowsheet bound with the
# forecast for every input it feeds (GET /api/proforma/bind?fits=). The two
# artifacts join artifacts.json so their links open.
BRIDGE_DEPOSITION = "dep-standin-ethanol"
STANDIN_FORECAST_H = 120.0
BRIDGE_LABELS = {"biomass": "Dry cell weight (STAND-IN)", "product": "Ethanol (STAND-IN)",
                 "substrate": "Glucose (STAND-IN)"}


def _bridge_fits() -> tuple[str, str]:
    """The bridge's STAND-IN fit and its forecast, kept in the current store
    (artifacts.folder()) through the real code: their ids, the fit's first."""
    from openferment_core import fermos
    from openferment_core.models import FermosSeries

    series = [FermosSeries.model_validate({**x, "measureId": f"standin-{x['role']}", "label": BRIDGE_LABELS[x["role"]]})
              for x in fermos_sample_series()]
    fit = fermos.fit(BRIDGE_DEPOSITION, series)
    fc = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, duration_h=STANDIN_FORECAST_H)
    return fit.kineticArtifactId, fc.artifactId


# §8.4: Proforma's BioSTEAM scenario for the smoke double. The binding and
# the run go through the real code (proforma.bind, proforma.run, the artifact
# store in a scratch folder); the records are STAND-INs on a paper id no
# corpus holds, and BioSTEAM is replaced by a closed-form STAND-IN evaluator,
# so test:core needs no simulator. Not a price of anything.
PROFORMA_STANDIN = "STAND-IN for the browser tests: invented records and a closed-form evaluator in place of BioSTEAM"


def _standin_records() -> list[dict[str, Any]]:
    rows = [("pha_titre", "g L-1", (20.0, 45.0, 70.0)), ("pha_yield_substrate", "g g-1", (0.22, 0.3, 0.36)),
            ("pha_content_cdw", "% CDW", (65.0, 80.0)), ("pha_productivity", "g L-1 h-1", (0.6, 1.4, 2.0))]
    out = []
    for field, unit, values in rows:
        for n, v in enumerate(values):
            out.append({"id": f"standin-{field}-{n}", "paperId": "P999", "field": field, "value": v, "unit": unit,
                        "carbonSource": "glucose", "strainId": "c-necator-h16", "organismText": "STAND-IN organism",
                        "provenance": "unverified", "status": "unverified", "primary": True})
    return out


def _standin_call(op: str, args: dict[str, Any]) -> Any:
    import itertools

    from scipy.stats import qmc

    # OF-BLD-019 §2.3: the glucose-to-ethanol flowsheet has a closed form of
    # its own; every other call is the PHA draft's, as before.
    flowsheet = args.get("flowsheet") or "pha_sugar_v0"
    # OF-BLD-020 §6.1: a vessel and a train, priced, answers as the ethanol
    # flowsheet's closed form does, under its own output names (the stand-in
    # reads no structure: it builds nothing).
    composite = flowsheet == "custom_train_v1"
    ethanol = flowsheet == "ethanol_glucose_v0" or composite

    def evaluate(v: dict[str, float]) -> dict[str, Any]:
        if composite:
            out = _standin_ethanol_evaluate(v)
            return {"pricePerKgProduct": out["pricePerKgEthanol"], "productKgPerH": out["ethanolKgPerH"],
                    "costLines": out["costLines"], "readBack": out["readBack"]}
        if ethanol:
            return _standin_ethanol_evaluate(v)
        if v["yield"] / v["content"] > 0.5:
            raise ValueError("carbon")
        lines = {"media": v["sugarPrice"] / v["yield"] / v["recovery"], "utilities": 0.3 / v["productivity"],
                 "labor": 0.1, "downstream": 2.0 / v["titre"], "other": 0.12, "capex": 4.0 / v["titre"] + 0.05}
        return {"pricePerKgPha": sum(lines.values()), "phaKgPerH": v["sugarFeed"] * v["yield"] * v["recovery"],
                "costLines": lines, "readBack": {"standIn": 1.0}}

    def attempt(v):
        try:
            return evaluate(v), None
        except ValueError as e:
            return None, {"reason": str(e), "detail": PROFORMA_STANDIN}

    def sample(spec, u):
        if spec["kind"] == "fixed":
            return spec["value"]
        lo, hi = spec["low"], spec["high"]
        if spec["kind"] == "uniform" or hi == lo:
            return lo + u * (hi - lo)
        c = (spec["mode"] - lo) / (hi - lo)
        return lo + (hi - lo) * ((u * c) ** 0.5 if u < c else 1 - ((1 - u) * (1 - c)) ** 0.5)

    if op == "evaluate":
        return evaluate(args["values"])
    if op == "reference":
        return _standin_reference(str(args["flowsheet"]))
    if op == "run":
        # OF-BLD-019 §2.1: the worker's whole run, composed of the three
        # below, with tables a closed form makes and labels as the stand-in.
        try:
            base_out, base_infeasible = evaluate(args["base"]), None
        except ValueError as e:
            base_out, base_infeasible = None, f"ValueError: {e}"
        grid = (_standin_call("grid", {"flowsheet": flowsheet, "axes": args["axes"], "base": args["base"]})
                if args.get("axes") else None)
        mc = _standin_call("montecarlo", {"flowsheet": flowsheet, "specs": args["specs"], "n": args["samples"],
                                          "seed": args["seed"], "base": args["base"]})
        tables = _standin_ethanol_tables if ethanol else _standin_tables
        shaped = ({**base_out, "ethanolKgPerH": base_out["productKgPerH"]} if composite and base_out else base_out)
        return {"base": base_out, "baseInfeasible": base_infeasible,
                "tables": tables(args["base"], shaped) if base_out else None, "grid": grid, "montecarlo": mc}
    if op == "grid":
        keys = list(args["axes"])
        cells = []
        for combo in itertools.product(*(args["axes"][k] for k in keys)):
            o, r = attempt({**args["base"], **dict(zip(keys, combo))})
            cells.append({"at": dict(zip(keys, combo)), "outputs": o, "infeasible": r})
        return {"axes": args["axes"], "base": args["base"], "cells": cells}
    keys = list(args["specs"])
    samples = []
    for row in qmc.LatinHypercube(d=len(keys), seed=args["seed"]).random(args["n"]):
        v = {**args["base"], **{k: sample(args["specs"][k], float(row[i])) for i, k in enumerate(keys)}}
        o, r = attempt(v)
        samples.append({"inputs": v, "outputs": o, "infeasible": r})
    return {"n": args["n"], "seed": args["seed"], "samples": samples}


# The tables of a run (OF-BLD-019 §2.1) in the shape the worker writes, from
# a closed form over the stand-in's inputs and cost lines: three units, six
# streams, a TEA breakdown whose lines sum to the stand-in price. Every
# number is invented and the tables say so in `tablesSource`.
STANDIN_HOURS = 8000.0


def _standin_tables(v: dict[str, float], out: dict[str, Any]) -> dict[str, Any]:
    from openferment_core.flowsheets.shelf import TABLE_UNITS

    sugar, pha = v["sugarFeed"], v["sugarFeed"] * v["yield"]
    water = pha / v["titre"] * 1000.0
    cells = pha * (1 - v["content"]) / v["content"]
    product = (pha + cells) * v["recovery"]
    broth = sugar + water

    def stream(sid, source, sink, flows, price=None):
        return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price}

    streams = [
        stream("sugar", None, "R1", {"Glucose": sugar}, v["sugarPrice"]),
        stream("process_water", None, "R1", {"Water": water}),
        stream("broth", "R1", "C1", {"Water": water, "Glucose": sugar - pha - cells, "PHB": pha, "Cells": cells}),
        stream("spent_medium", "C1", None, {"Water": water, "Glucose": sugar - pha - cells, "PHB": pha * (1 - v["recovery"]),
                                            "Cells": cells * (1 - v["recovery"])}),
        stream("wet_solids", "C1", "D1", {"PHB": pha * v["recovery"], "Cells": cells * v["recovery"]}),
        stream("product", "D1", None, {"PHB": pha * v["recovery"], "Cells": cells * v["recovery"]}),
    ]
    lines_in = out["costLines"]
    per = pha * v["recovery"] * STANDIN_HOURS
    capital = lines_in["capex"] * per
    units = []
    for n, (uid, share, heat, cool, kw) in enumerate((("R1", 0.7, None, 9.0e6, 400.0), ("C1", 0.2, None, None, 90.0),
                                                       ("D1", 0.1, 4.0e6, None, 170.0))):
        installed = capital * 3.0 * share
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid], "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    annual = {"feedstock": lines_in["media"] * per, "otherMaterials": 0.0,
              "utilities": (lines_in["utilities"] + lines_in["downstream"]) * per,
              "fixedOperating": (lines_in["labor"] + lines_in["other"]) * per, "capitalRecovery": capital}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery"}
    sales = sum(annual.values())
    installed_total = sum(u["installedCost"] for u in units)
    tea = {
        "teaClass": "StandIn", "product": "product", "feedstock": "sugar",
        "productPrice": sales / (product * STANDIN_HOURS), "basisFlow": pha * v["recovery"],
        "basis": "kg of PHA contained in dried cell mass", "operatingHours": STANDIN_HOURS, "sales": sales,
        "materialCost": annual["feedstock"], "feedstockCost": annual["feedstock"], "otherMaterialCost": 0.0,
        "utilityCost": annual["utilities"], "purchaseCost": installed_total / 2.0, "installedEquipmentCost": installed_total,
        "FCI": installed_total, "TCI": installed_total, "FOC": annual["fixedOperating"], "laborCost": lines_in["labor"] * per,
        "capitalRecovery": capital, "coproductCredits": 0.0, "IRR": None, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / per, "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    heating = sum(u["heatingDuty"] or 0.0 for u in units) / 1e6
    cooling = sum(u["coolingDuty"] or 0.0 for u in units) / 1e6
    power = sum(u["power"] or 0.0 for u in units) / 1e3
    return {
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": heating, "heatingUnit": "GJ/hr", "cooling": cooling,
                      "coolingUnit": "GJ/hr", "electricityConsumption": power, "electricityConsumptionUnit": "MW",
                      "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


# A reference biorefinery's run (OF-BLD-019 §2.2) in the shape the worker's
# `reference` op writes, from a closed form: three units, five streams, a
# TEA whose lines sum to the stand-in price, the package test's quantities
# read from those, and every default the shelf lists. Every number is
# invented and the run says so in `simulator` and `tablesSource`; the
# package test's values beside it are the installed file's, as a real run's.
def _standin_reference(flowsheet: str) -> dict[str, Any]:
    from openferment_core.flowsheets import shelf as _shelf
    from openferment_core.flowsheets.shelf import TABLE_UNITS

    info = _shelf.info(flowsheet)
    hours, feed, product, price, feed_price = 8000.0, 40000.0, 12000.0, 0.5, 0.15
    lines_in = {"feedstock": feed * feed_price, "otherMaterials": 600.0, "utilities": 900.0,
                "fixedOperating": 500.0, "capitalRecovery": 700.0}
    credit = sum(lines_in.values()) - product * price  # what the co-product must bring for the lines to sum
    annual = {k: v * hours for k, v in lines_in.items()} | {"coproductCredits": -credit * hours}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery",
             "coproductCredits": "Co-product credits"}

    def stream(sid, source, sink, flows, price_=None):
        return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price_}

    streams = [
        stream("feed", None, "R1", {"Starch": feed}, feed_price),
        stream("beer", "R1", "D1", {"Ethanol": product, "Water": 3 * product}),
        stream("product", "D1", "M1", {"Ethanol": product}, price),
        stream("stillage", "D1", None, {"Water": 3 * product}),
        stream("coproduct", "R1", None, {"Solids": feed - product}, credit / (feed - product)),
    ]
    units = []
    for n, (uid, heat, cool, kw) in enumerate((("R1", None, 5.0e6, 300.0), ("D1", 9.0e6, 8.0e6, 120.0),
                                               ("M1", None, None, 40.0))):
        installed = lines_in["capitalRecovery"] * hours * (3 - n)
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid],
                      "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    installed_total = sum(u["installedCost"] for u in units)
    # The TEA prices installation on the purchase costs as a whole, with a
    # STAND-IN Lang factor, as the corn plant's TEA does with its own: so the
    # TEA's installed equipment cost is not the sum of the units' (OF-BLD-019
    # §3.R, finding 19), and a page that summed the units would show another
    # number than the TEA's.
    lang = 3.0
    tea_installed = installed_total / 2.0 * lang
    sales = product * price * hours + credit * hours
    heating = sum(u["heatingDuty"] or 0.0 for u in units) / 1e6
    cooling = sum(u["coolingDuty"] or 0.0 for u in units) / 1e6
    power = sum(u["power"] or 0.0 for u in units) / 1e3
    tea = {
        "teaClass": "StandIn", "product": "product", "feedstock": "feed", "productPrice": price, "basisFlow": product,
        "basis": "kg of the STAND-IN product", "operatingHours": hours, "sales": sales,
        "materialCost": annual["feedstock"] + annual["otherMaterials"], "feedstockCost": annual["feedstock"],
        "otherMaterialCost": annual["otherMaterials"], "utilityCost": annual["utilities"],
        "purchaseCost": installed_total / 2.0, "installedEquipmentCost": tea_installed, "FCI": tea_installed,
        "TCI": tea_installed, "FOC": annual["fixedOperating"], "laborCost": annual["fixedOperating"] / 2.0,
        "capitalRecovery": annual["capitalRecovery"], "coproductCredits": credit * hours, "IRR": 0.1, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / (product * hours), "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    measured = {
        "tea.IRR": tea["IRR"], "feedstock.price": feed_price, "product.price": price, "tea.sales": sales,
        "tea.material_cost": tea["materialCost"], "tea.installed_equipment_cost": tea_installed,
        "tea.utility_cost": tea["utilityCost"], "units.get_heating_duty()": heating, "units.get_cooling_duty()": cooling,
        "units.get_electricity_consumption()": power, "units.get_electricity_production()": 0.0,
    }
    if flowsheet == "corn_drygrind":
        outputs = {"ethanolPriceUsdPerKg": price, "IRR": tea["IRR"], "ethanolKgPerH": product, "cornKgPerH": feed}
    else:
        outputs = {"mespUsdPerGal": price * 3.0, "mespUsdPerKg": price, "ethanolDensityKgPerGal": 3.0,
                   "settings": {"rateOfReturn": 0.1, "operatingDays": hours / 24.0, "incomeTax": 0.35,
                                "startYear": 2007, "endYear": 2037}}
    read_back = {i.key: ("STAND-IN" if i.dimension == "schedule" else lang if i.key == "langFactor" else 1.0) for i in info.inputs}
    return {
        "flowsheet": flowsheet, "simulator": PROFORMA_STANDIN, "package": f"STAND-IN for {flowsheet}",
        **outputs, "references": [PROFORMA_STANDIN], "measured": measured, "readBack": read_back,
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": heating, "heatingUnit": "GJ/hr", "cooling": cooling,
                      "coolingUnit": "GJ/hr", "electricityConsumption": power, "electricityConsumptionUnit": "MW",
                      "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


# OF-BLD-019 §2.3: the yeast flowsheet's STAND-INs. Records on a thread Q
# paper id no corpus holds, and a closed-form evaluator whose theoretical
# yield is its own STAND-IN, not the flowsheet's (which the worker computes
# from the reaction and thermosteam's molecular weights). Not a price of
# anything.
STANDIN_THEORETICAL = 0.511
YEAST_STANDIN_ASSUMED = (("plant_scale", 100000.0, 100000.0, 100000.0), ("glucose_price", 0.4, 0.3, 0.5))


def _standin_yeast_records() -> list[dict[str, Any]]:
    rows = [("medium_component_conc", "g L-1", (20.0, 60.0, 100.0)), ("ethanol_titre", "g L-1", (40.0, 60.0, 90.0)),
            ("ethanol_yield_substrate", "g g-1", (0.4, 0.45, 0.48)), ("ethanol_productivity", "g L-1 h-1", (1.0, 1.8, 2.5))]
    out = []
    for field, unit, values in rows:
        for n, v in enumerate(values):
            out.append({"id": f"standin-{field}-{n}", "paperId": "Q999", "field": field, "value": v, "unit": unit,
                        "carbonSource": "glucose", "strainId": "s-cerevisiae-cenpk113-7d",
                        "organismText": "STAND-IN organism", "provenance": "unverified", "status": "unverified",
                        "primary": True})
    return out


def _standin_ethanol_evaluate(v: dict[str, float]) -> dict[str, Any]:
    if v["yield"] > STANDIN_THEORETICAL:
        raise ValueError("yield")
    lines = {"media": v["glucose_price"] / v["yield"], "utilities": 0.6 / v["feed_glucose_conc"], "labor": 0.02,
             "downstream": 2.0 / v["feed_glucose_conc"], "other": 0.03,
             "capex": 0.05 + 0.002 * v["titre"] / v["productivity"]}
    return {"pricePerKgEthanol": sum(lines.values()), "ethanolKgPerH": v["plant_scale"] * 1000.0 / STANDIN_HOURS,
            "costLines": lines, "readBack": {"standIn": 1.0}}


def _standin_ethanol_tables(v: dict[str, float], out: dict[str, Any]) -> dict[str, Any]:
    """The tables of a run in the shape the worker writes, from a closed form
    over the yeast stand-in's inputs and cost lines: four units, seven
    streams, a TEA breakdown whose lines sum to the stand-in price. Every
    number is invented, and `tablesSource` says so."""
    from openferment_core.flowsheets.shelf import TABLE_UNITS

    ethanol = out["ethanolKgPerH"]
    glucose = ethanol / v["yield"]
    co2 = ethanol  # STAND-IN: as much carbon dioxide as ethanol, by mass
    left = glucose - ethanol - co2
    water = glucose / v["feed_glucose_conc"] * 1000.0

    def stream(sid, source, sink, flows, price=None, phase="l"):
        return {"id": sid, "source": source, "sink": sink, "phase": phase, "T": 298.15, "P": 101325.0,
                "massFlow": sum(flows.values()), "massFlows": flows, "price": price}

    streams = [
        stream("glucose", None, "R1", {"Glucose": glucose}, v["glucose_price"]),
        stream("process_water", None, "R1", {"Water": water}),
        stream("vent", "R1", None, {"CO2": co2}, phase="g"),
        stream("beer", "R1", "D302", {"Water": water, "Ethanol": ethanol, "Glucose": left}),
        stream("stillage", "D302", None, {"Water": water, "Glucose": left}),
        stream("distillate", "D302", "U301", {"Ethanol": ethanol}),
        stream("ethanol", "U301", None, {"Ethanol": ethanol}),
    ]
    lines_in = out["costLines"]
    per = ethanol * STANDIN_HOURS
    capital = lines_in["capex"] * per
    units = []
    for n, (uid, share, heat, cool, kw) in enumerate((("R1", 0.5, None, 9.0e6, 300.0), ("D302", 0.3, 6.0e7, 4.0e7, 60.0),
                                                       ("U301", 0.2, 1.0e7, None, 20.0))):
        installed = capital * 3.0 * share
        units.append({"id": uid, "unitClass": "StandIn", "line": "STAND-IN unit", "order": n,
                      "ins": [s["id"] for s in streams if s["sink"] == uid], "outs": [s["id"] for s in streams if s["source"] == uid],
                      "installedCost": installed, "purchaseCost": installed / 2.0,
                      "heatingDuty": heat, "coolingDuty": cool, "power": kw})
    annual = {"feedstock": lines_in["media"] * per, "otherMaterials": 0.0,
              "utilities": (lines_in["utilities"] + lines_in["downstream"]) * per,
              "fixedOperating": (lines_in["labor"] + lines_in["other"]) * per, "capitalRecovery": capital}
    words = {"feedstock": "Main feedstock", "otherMaterials": "Other materials", "utilities": "Utilities",
             "fixedOperating": "Fixed operating, labour included", "capitalRecovery": "Capital recovery"}
    sales = sum(annual.values())
    installed_total = sum(u["installedCost"] for u in units)
    tea = {
        "teaClass": "StandIn", "product": "ethanol", "feedstock": "glucose",
        "productPrice": sales / per, "basisFlow": ethanol, "basis": "kg of fuel-grade ethanol, as the product leaves its tank",
        "operatingHours": STANDIN_HOURS, "sales": sales,
        "materialCost": annual["feedstock"], "feedstockCost": annual["feedstock"], "otherMaterialCost": 0.0,
        "utilityCost": annual["utilities"], "purchaseCost": installed_total / 2.0, "installedEquipmentCost": installed_total,
        "FCI": installed_total, "TCI": installed_total, "FOC": annual["fixedOperating"], "laborCost": lines_in["labor"] * per,
        "capitalRecovery": capital, "coproductCredits": 0.0, "IRR": None, "incomeTax": None,
        "lines": [{"key": k, "label": words[k], "usdPerYear": a, "perUnit": a / per, "reads": PROFORMA_STANDIN}
                  for k, a in annual.items()],
    }
    return {
        "tablesSource": PROFORMA_STANDIN, "tea": tea, "streams": streams, "units": units,
        "utilities": {"group": "STAND-IN units", "heating": sum(u["heatingDuty"] or 0.0 for u in units) / 1e6,
                      "heatingUnit": "GJ/hr", "cooling": sum(u["coolingDuty"] or 0.0 for u in units) / 1e6,
                      "coolingUnit": "GJ/hr", "electricityConsumption": sum(u["power"] or 0.0 for u in units) / 1e3,
                      "electricityConsumptionUnit": "MW", "electricityProduction": 0.0, "electricityProductionUnit": "MW"},
        "diagram": None,
        "diagramNote": "STAND-IN: no flowsheet was simulated, so there is no diagram; the units are listed in order.",
        "unitOrder": [u["id"] for u in units], "tableUnits": TABLE_UNITS,
    }


STANDIN_CEILING_NOTE = ("STAND-IN ceiling for tests and the browser double: not computed by {model} or any model; "
                        "a value set between the stand-in yields so the flag shows")


def standin_ceiling(model_id: str, product: str, substrate: str, g_per_g: float, *, at: str = AT,
                    version: str = "STAND-IN ceiling 1"):
    """Keep one STAND-IN `geneos.ceiling` artifact in the current store
    (artifacts.folder()), in the shape the geneOS worker writes, for the
    shelf model `model_id`; return it. Its basis is geneos's own but for the
    model input, an assumption that says what it is."""
    from openferment_core import artifacts, atomic, geneos, geneos_models
    from openferment_core.basis import basis_provenance
    from openferment_core.models import Artifact, BasisInput, BasisSource, ComputedBasis

    inputs = [BasisInput(name="model", value=f"STAND-IN for {model_id}", unit="", source=BasisSource(
        kind="assumption", id=model_id, by="openFerment test fixture", note=STANDIN_CEILING_NOTE.format(model=model_id)))]
    inputs += [i for i in geneos._inputs(model_id, product, [substrate]) if i.name != "model"]
    mol = g_per_g * geneos_models.SUBSTRATES[substrate]["molarMass"] / geneos_models.PRODUCTS[product]["molarMass"]
    output = {"modelId": model_id, "product": product, "substrate": substrate,
              "exchange": geneos_models.exchange_id(model_id, substrate), "uptake": geneos_models.UPTAKE,
              "flux": mol * geneos_models.UPTAKE, "molPerMol": mol, "gPerG": g_per_g, "solver": "STAND-IN",
              "status": "optimal"}
    aid = artifacts.artifact_id(geneos.CEILING, version, inputs)
    basis = ComputedBasis(tool=geneos.CEILING, toolVersion=version, inputs=inputs, artifactId=aid, at=at)
    art = Artifact(id=aid, tool=geneos.CEILING, toolVersion=version, inputs=inputs, output=output,
                   outputHash=artifacts.output_hash(output), provenance=basis_provenance(basis, {}, {}), createdAt=at,
                   durationMs=0)
    artifacts.folder().mkdir(parents=True, exist_ok=True)
    atomic.write_text(artifacts.folder() / f"{aid}.json", art.model_dump_json(indent=2) + "\n")
    return art


VESSEL_FIXTURE_RTOL = 1e-6


# §8.1: the fixtures that need BioSTEAM, which are the toy flowsheet's: one
# evaluation, a small grid and a seeded sample, made by the real Proforma
# worker. `pnpm test:sim` regenerates them and fails when they drift;
# write `sim_fixtures()` over the file to refresh it (the note keeps its old words: they are part of the file).
SIM_FIXTURES = CORE / "tests" / "fixtures" / "sim" / "toy.json"
SIM_NOTE = "TEST FIXTURE: the toy flowsheet (a mixer and a splitter) through the real BioSTEAM worker; made by `python -m openferment_core.demo --sim`."


def sim_fixtures() -> dict[str, Any]:
    from openferment_core import proforma

    evaluate = proforma.call("evaluate", {"flowsheet": "toy", "values": {}})
    grid = proforma.call("grid", {"flowsheet": "toy", "axes": {"split": [0.2, 0.6], "ethanol": [40.0, 50.0]}, "base": {}})
    sample = proforma.call("montecarlo", {"flowsheet": "toy", "specs": {
        "split": {"kind": "uniform", "low": 0.1, "high": 0.9},
        "ethanol": {"kind": "triangular", "low": 40.0, "mode": 50.0, "high": 70.0}}, "n": 8, "seed": 3, "base": {}})
    return {"_fixture": SIM_NOTE, "evaluate": evaluate, "grid": grid, "montecarlo": sample}
