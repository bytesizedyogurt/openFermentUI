"""H4: compare a service library run (POST /api/library/{plant}/run answer) with the direct route
(direct_plant.py), field by field.

    python3 compare_plant.py direct-cornstover.json svc-cornstover.json [tables.json]

Prints each number, both routes, and the relative difference; flags anything past 1e-9
(the run keeps ten significant digits).
"""
import json
import sys

d = json.load(open(sys.argv[1]))
s = json.load(open(sys.argv[2]))
tables = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
out = s["artifact"]["output"]
price = out["price"]
vals = {v["name"]: v["quantity"] for v in s["run"]["outputs"]["values"]}
bad = []


def cmp(label, mine, theirs, rtol=1e-9, atol=1e-8):
    if mine is None or theirs is None:
        print(f"  {label:45s} direct={mine!r} service={theirs!r}  MISSING")
        bad.append(label)
        return
    rel = abs(mine - theirs) / abs(mine) if mine else abs(theirs)
    flag = "" if abs(mine - theirs) <= atol + rtol * abs(mine) else "  <-- DIFFERS"
    if flag:
        bad.append(label)
    print(f"  {label:45s} direct={mine:<22.12g} service={theirs:<22.12g} rel={rel:.2e}{flag}")


print("price block (artifact output.price and run outputs.values):")
for k in ("IRR", "sales", "material_cost", "utility_cost", "installed_equipment_cost", "TCI", "FCI", "FOC", "VOC"):
    cmp(f"price.{k}", d[k], price.get(k))
    cmp(f"values price.{k}", d[k], (vals.get(f"price.{k}") or {}).get("value"))
cmp("price.NPV (atol 1 USD)", d["NPV"], price.get("NPV"), atol=1.0)
cmp("price.packagePrice", d["packagePrice"], price.get("packagePrice"))
cmp("price.solvedPrice", d["solvedPrice"], price.get("solvedPrice"))
cmp("price.feedstockKgPerH", d["feedstockKgPerH"], price.get("feedstockKgPerH"))
print("  units:", price.get("units"))
print("package-test quantities (output.measured):")
m = out.get("measured") or {}
for k, dk in (("units.get_heating_duty()", "heating"), ("units.get_cooling_duty()", "cooling"),
              ("units.get_electricity_consumption()", "electricityConsumption"),
              ("units.get_electricity_production()", "electricityProduction"),
              ("feedstock.price", "feedstockPrice"), ("product.price", "packagePrice")):
    cmp(k, d[dk], m.get(k))
print("utilities table (output.utilities):")
u = out.get("utilities") or {}
for k, dk in (("heating", "heating"), ("cooling", "cooling"), ("electricityConsumption", "electricityConsumption"),
              ("electricityProduction", "electricityProduction")):
    cmp(f"utilities.{k}", d[dk], u.get(k))
print("  units:", {k: v for k, v in u.items() if k.endswith("Unit")})
tea = out.get("tea") or {}
print("TEA breakdown (output.tea):")
for k, dk in (("sales", "sales"), ("materialCost", "material_cost"), ("utilityCost", "utility_cost"),
              ("installedEquipmentCost", "installed_equipment_cost"), ("purchaseCost", "purchase_cost"),
              ("FCI", "FCI"), ("TCI", "TCI"), ("FOC", "FOC"), ("operatingHours", "operating_hours"),
              ("feedstockCost", "feedstockMarketValue"), ("productPrice", "packagePrice"),
              ("basisFlow", "productKgPerH"), ("laborCost", "labor_cost"), ("incomeTax", "income_tax")):
    cmp(f"tea.{k}", d[dk], tea.get(k))
cmp("tea.capitalRecovery = sales - AOC", d["sales"] - d["AOC"], tea.get("capitalRecovery"))
cmp("tea.coproductCredits = sales - revenue", d["sales"] - d["productMarketValue"], tea.get("coproductCredits"))
lines = tea.get("lines") or []
tot = sum(l["perUnit"] for l in lines if l["perUnit"] is not None)
cmp("sum of waterfall perUnit vs productPrice", d["packagePrice"], tot, rtol=1e-6)
for l in lines:
    print(f"    line {l['key']:18s} {l['usdPerYear']:>18.6g} USD/yr  {l['perUnit']!r:>22} per unit")
print("streams (output.streams):")
st = {r["id"]: r for r in out.get("streams") or []}
nd = 0
for sid, ds in d["streams"].items():
    r = st.get(sid)
    if r is None:
        print(f"  stream {sid} missing from the service table")
        bad.append(sid)
        continue
    for k, dk in (("massFlow", "F_mass"), ("T", "T"), ("P", "P")):
        mine, theirs = ds[dk], r[k]
        if abs(mine - theirs) > 1e-8 + 1e-9 * abs(mine):
            nd += 1
            print(f"  stream {sid}.{k}: direct {mine!r} service {theirs!r}")
    for c, f in ds["flows"].items():
        g = r["massFlows"].get(c)
        if g is None or abs(f - g) > 1e-8 + 1e-9 * abs(f):
            nd += 1
            if nd < 40:
                print(f"  stream {sid}.{c}: direct {f!r} service {g!r}")
print(f"  {len(d['streams'])} streams compared, {nd} values differ past ten digits")
print("units (output.units):")
ut = {r["id"]: r for r in out.get("units") or []}
nu = 0
for uid, du in d["units"].items():
    r = ut.get(uid)
    if r is None:
        print(f"  unit {uid} missing")
        continue
    for k, dk in (("installedCost", "installed"), ("purchaseCost", "purchase")):
        if abs(du[dk] - r[k]) > 1e-8 + 1e-9 * abs(du[dk]):
            nu += 1
            print(f"  unit {uid}.{k}: direct {du[dk]!r} service {r[k]!r}")
print(f"  {len(d['units'])} units compared, {nu} costs differ")
s_inst = sum(r["installedCost"] for r in out.get("units") or [])
print(f"  sum of unit installedCost over the system table: {s_inst:.10g}; tea installed_equipment_cost {d['installed_equipment_cost']:.10g}")
print("checks (output.checks):")
for c in out.get("checks") or []:
    print(f"  {c['expression']:40s} within={c['within']} measured={c['measured']} package={c['package']} rel={c['relDiff']}")
print("DIFFER:", bad)
