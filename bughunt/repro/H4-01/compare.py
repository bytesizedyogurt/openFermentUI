"""H4-01: cornstover and cellulosic_ethanol_v0, each run once through POST /api/library/{plant}/run with no
value set, and their cost cards set side by side. Prints EXPECTED, OBSERVED and RESULT lines.

    bh_env H401_ORIGIN=http://127.0.0.1:10220 H401_PROJECT=h401 H401_OUT=<dir> python -I compare.py run
    (then screen.mjs, which writes <dir>/screen.json)
    bh_env H401_OUT=<dir> python -I compare.py judge

The cost card (src/components/figures/CostWaterfall.tsx) draws `tea.lines` as its rows and `tea.productPrice` as
its closing row (`waterfallTotal`); the run's base-case price is `price.solvedPrice`. Everything compared here is
what the card is drawn from.
"""
import json
import math
import os
import sys

import httpx

OUT = os.environ["H401_OUT"]
REL = 1e-9  # two floats of one computation agree to this; a cost line moved by a price gap differs by far more


def same(a, b, rel=REL):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def run(c, plant):
    O, P = os.environ["H401_ORIGIN"], os.environ["H401_PROJECT"]
    r = c.post(f"{O}/api/library/{plant}/run", json={"by": "h401"}, headers={"X-OpenFerment-Project": P})
    if r.status_code != 200:
        print(f"{plant} run answered {r.status_code}: {r.text[:400]}")
        sys.exit(1)
    d = r.json()
    json.dump(d, open(f"{OUT}/{plant}.json", "w"))
    return d


if sys.argv[1] == "run":  # the two runs, no value set; their run ids for the screen
    with httpx.Client(trust_env=False, timeout=1200) as c:
        ids = [f"{plant}={run(c, plant)['run']['id']}" for plant in ("cornstover", "cellulosic_ethanol_v0")]
    print(" ".join(ids))
    sys.exit(0)

cs, cv = (json.load(open(f"{OUT}/{plant}.json")) for plant in ("cornstover", "cellulosic_ethanol_v0"))

oc, ov = cs["artifact"]["output"], cv["artifact"]["output"]
print(f"runs: cornstover {cs['run']['id']}, cellulosic_ethanol_v0 {cv['run']['id']}; "
      f"overrides set: {oc.get('overrides')!r} and {ov.get('overrides')!r}; inputs sent: none")

# 1. The two plants are one plant: every stream's flows, every unit's costs and duties, the TEA's capital.
def streams(o):
    return {s["id"]: s for s in o["streams"]}


def units(o):
    return {u["id"]: u for u in o["units"]}


sc, sv, uc, uv = streams(oc), streams(ov), units(oc), units(ov)
stream_diff = [i for i in sc if i not in sv or not same(sc[i]["massFlow"], sv[i]["massFlow"])
               or any(not same(sc[i]["massFlows"].get(k), sv[i]["massFlows"].get(k)) for k in sc[i]["massFlows"])]
stream_diff += [i for i in sv if i not in sc]
unit_keys = ("installedCost", "purchaseCost", "heatingDuty", "coolingDuty", "power")
unit_diff = [i for i in uc if i not in uv or any(not same(uc[i].get(k), uv[i].get(k)) for k in unit_keys)]
unit_diff += [i for i in uv if i not in uc]
pc, pv = oc["price"], ov["price"]
tc, tv = oc["tea"], ov["tea"]
cap_keys = ("FCI", "TCI", "FOC", "installedEquipmentCost", "materialCost", "utilityCost", "operatingHours", "basisFlow")
cap_diff = [k for k in cap_keys if not same(tc.get(k), tv.get(k))]
irr_same = same(pc.get("IRR"), pv.get("IRR"))
solved_same = same(pc["solvedPrice"], pv["solvedPrice"])
print(f"streams: {len(sc)} and {len(sv)}, differing in flow: {len(stream_diff)} {stream_diff[:5]}")
print(f"units: {len(uc)} and {len(uv)}, differing in cost or duty: {len(unit_diff)} {unit_diff[:5]}")
print(f"TEA totals differing ({', '.join(cap_keys)}): {cap_diff}; IRR {pc.get('IRR')} and {pv.get('IRR')}")
print(f"solvedPrice (the base-case price): cornstover {pc['solvedPrice']}, cellulosic_ethanol_v0 {pv['solvedPrice']}")
print(f"packagePrice (the product's set price): cornstover {pc['packagePrice']}, cellulosic_ethanol_v0 {pv['packagePrice']}")
eth_c, eth_v = sc.get(tc["product"], {}), sv.get(tv["product"], {})
print(f"stream table, the {tc['product']} row's price: cornstover {eth_c.get('price')}, "
      f"cellulosic_ethanol_v0 {eth_v.get('price')}")
one_plant = not stream_diff and not unit_diff and not cap_diff and irr_same and solved_same

# 2. The cards: each line per kg, the closing row, and what capital recovery would be at the solved price.
lc = {l["key"]: l for l in tc["lines"]}
lv = {l["key"]: l for l in tv["lines"]}
print(f"\n{'cost card line (USD per kg ethanol)':38s} {'cornstover':>12s} {'cellulosic_ethanol_v0':>22s}")
for k in list(dict.fromkeys(list(lc) + list(lv))):
    a, b = lc.get(k, {}).get("perUnit"), lv.get(k, {}).get("perUnit")
    label = (lc.get(k) or lv.get(k))["label"]
    print(f"  {label:36s} {a if a is None else round(a, 6):>12} {b if b is None else round(b, 6):>22}")
print(f"  {'closing row (tea.productPrice)':36s} {round(tc['productPrice'], 6):>12} {round(tv['productPrice'], 6):>22}")
print(f"  {'base-case price (price.solvedPrice)':36s} {round(pc['solvedPrice'], 6):>12} {round(pv['solvedPrice'], 6):>22}")
sum_c = sum(l["perUnit"] for l in tc["lines"])
sum_v = sum(l["perUnit"] for l in tv["lines"])
print(f"  {'sum of the lines':36s} {round(sum_c, 6):>12} {round(sum_v, 6):>22}")

other_moved = [k for k in lc if k != "capitalRecovery" and (k not in lv or not same(lc[k]["perUnit"], lv[k]["perUnit"]))]
cr_c, cr_v = lc["capitalRecovery"]["perUnit"], lv["capitalRecovery"]["perUnit"]
cr_at_solved_v = pv["solvedPrice"] - (sum_v - cr_v)  # capital recovery the card would show read at its solved price
gap_v = tv["productPrice"] - pv["solvedPrice"]
print(f"\ncellulosic_ethanol_v0: closing row less base-case price = {gap_v:.6f} USD/kg; its capital recovery less "
      f"cornstover's = {cr_v - cr_c:.6f} USD/kg; lines other than capital recovery that differ: {other_moved}")
print(f"cellulosic_ethanol_v0's capital recovery read at its own solved price would be {cr_at_solved_v:.6f} USD/kg "
      f"(cornstover's card: {cr_c:.6f})")

# 3. The screen: the Capital recovery row and the closing row each card draws (screen.mjs, the built app).
try:
    screen = json.load(open(f"{OUT}/screen.json"))
except (OSError, ValueError):
    screen = None
shown = {}
if screen:
    for label in ("cornstover", "cellulosic_ethanol_v0"):
        rows = screen.get(label, {}).get("rows", [])
        cr = next((r for r in rows if r.startswith("Capital recovery")), None)
        print(f"[screen {label}] base case: {screen.get(label, {}).get('base')}")
        print(f"[screen {label}] rows: {' || '.join(rows)}")
        print(f"[screen {label}] price note: {screen.get(label, {}).get('note')}")
        shown[label] = cr
else:
    print("[screen] no screen reading (Chromium did not run); the verdict rests on the run's own tables")
print(f"[screen] Capital recovery row as drawn: cornstover {shown.get('cornstover')!r}, "
      f"cellulosic_ethanol_v0 {shown.get('cellulosic_ethanol_v0')!r}")

defect_b = one_plant and not other_moved and not same(cr_c, cr_v, 1e-6) and not same(tv["productPrice"], pv["solvedPrice"], 1e-6)
takes_whole_gap = math.isclose(cr_v - cr_c, gap_v, rel_tol=1e-6, abs_tol=1e-9)
print(f"\nthe capital recovery line takes the whole gap: {takes_whole_gap}")
print(f"EXPECTED: cellulosic_ethanol_v0 at its default (dilute acid, IB), with no value set, is the package's own cellulosic "
      f"plant unit for unit (its recipe's words), so its cost card is cornstover's card: lines that close on the solved price "
      f"{pv['solvedPrice']:.6f} USD/kg, capital recovery {cr_c:.6f} USD/kg, as the recipe's own load() prices the ethanol "
      f"at the TEA's IRR as the package's Biorefinery does")
print(f"OBSERVED: equal plants ({len(sc)} streams and {len(uc)} units equal, the same solved price and capital); "
      f"cornstover's card closes on {tc['productPrice']:.6f} with capital recovery {cr_c:.6f} USD/kg, "
      f"cellulosic_ethanol_v0's closes on {tv['productPrice']:.6f} (its set price) with capital recovery {cr_v:.6f} USD/kg, "
      f"the line {cr_v - cr_c:.6f} USD/kg larger, the whole gap between its closing row and its base-case price")
print("RESULT: DEFECT" if defect_b else "RESULT: NO-DEFECT")
