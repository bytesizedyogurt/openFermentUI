"""H4: a second route to a library plant's numbers. Run as its own process with
the repository's venv Python; imports nothing of openFerment.

    /home/user/openFermentUI/core/.venv/bin/python direct_plant.py cornstover > out.json
    /home/user/openFermentUI/core/.venv/bin/python direct_plant.py corn > out.json
    /home/user/openFermentUI/core/.venv/bin/python direct_plant.py cellulosic > out.json   # cellulosic.Biorefinery()

Prints JSON: the TEA's numbers, the solved price, the UnitGroup totals, every stream's
F_mass/T/P and component flows, and every unit's installed and purchase cost.
"""
import io
import json
import sys
from contextlib import redirect_stdout
from importlib import import_module

import biosteam as bst

plant = sys.argv[1]
bst.process_tools.default()
with redirect_stdout(io.StringIO()):
    if plant == "cellulosic":
        from biorefineries import cellulosic
        br = cellulosic.Biorefinery()
        system, tea = br.system, br.system.TEA
        product = next(s for s in system.products if s.ID == "ethanol")
        feedstock = max([s for s in system.feeds if s.price > 0], key=lambda s: s.F_mass)
    else:
        m = import_module("biorefineries." + plant)
        if plant == "corn":
            m.units.SimultaneousSaccharificationFermentation._ins_size_is_fixed = False
        m.load()
        feedstock = getattr(m, {"corn": "corn", "cornstover": "cornstover"}[plant])
        product = m.ethanol
        tea = None
        for name in ("tea", f"{plant}_tea", f"{feedstock.ID}_tea", "ethanol_tea"):
            if isinstance(getattr(m, name, None), bst.TEA):
                tea = getattr(m, name)
                break
        system = tea.system

units = bst.UnitGroup("Biorefinery", tea.units)
out = {
    "plant": plant,
    "teaClass": type(tea).__name__,
    "IRR": tea.IRR, "sales": tea.sales, "material_cost": tea.material_cost, "utility_cost": tea.utility_cost,
    "installed_equipment_cost": tea.installed_equipment_cost, "purchase_cost": tea.purchase_cost,
    "TCI": tea.TCI, "FCI": tea.FCI, "FOC": tea.FOC, "VOC": tea.VOC, "AOC": tea.AOC, "NPV": tea.NPV,
    "operating_hours": tea.operating_hours, "labor_cost": getattr(tea, "labor_cost", None),
    "income_tax": tea.income_tax,
    "packagePrice": product.price, "product": product.ID, "productKgPerH": product.F_mass,
    "feedstock": feedstock.ID, "feedstockKgPerH": feedstock.F_mass, "feedstockPrice": feedstock.price,
    "productMarketValue": system.get_market_value(product), "feedstockMarketValue": system.get_market_value(feedstock),
    "heating": units.get_heating_duty(), "cooling": units.get_cooling_duty(),
    "electricityConsumption": units.get_electricity_consumption(),
    "electricityProduction": units.get_electricity_production(),
    "CE": bst.CE, "powerPrice": bst.PowerUtility.price,
    "streams": {s.ID: {"F_mass": s.F_mass, "T": s.T, "P": s.P,
                       "flows": {i: float(x) for i, x in zip(s.chemicals.IDs, s.mass) if x}}
                for s in system.streams if s.ID},
    "units": {u.ID: {"installed": u.installed_cost, "purchase": u.purchase_cost, "power": u.power_utility.rate}
              for u in system.units},
}
out["solvedPrice"] = tea.solve_price(product)
out["priceAfterSolve"] = product.price
print(json.dumps(out))
