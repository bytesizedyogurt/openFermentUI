"""H4-03: cornstover through POST /api/library/cornstover/run twice, once with nothing set and once with one
person's value equal to the library's own default (the feedstock price, read from GET .../parameters), and the
two runs' price blocks and cost cards set side by side. Prints EXPECTED, OBSERVED and RESULT lines.

    bh_env H403_ORIGIN=http://127.0.0.1:10300 H403_PROJECT=h403 H403_OUT=<dir> python -I check.py

The runs' basis states its precision ("10 significant digits"); docs/api/engines.md:615 gives a library thing's
precision as rtol 1e-9. The same plant at the same values gives one price to that precision.
"""
import json
import math
import os
import sys

import httpx

O, P, OUT = os.environ["H403_ORIGIN"], os.environ["H403_PROJECT"], os.environ["H403_OUT"]
H = {"X-OpenFerment-Project": P}
KEY = "stream.cornstover.price"
RTOL = 1e-9  # docs/api/engines.md:615, "ten significant digits (`rtol` 1e-9)"


def fail(words):
    print("EXPECTED: two cornstover runs to compare")
    print(f"OBSERVED: {words}")
    print("RESULT: NO-DEFECT")
    sys.exit(0)


def run(c, inputs, tag):
    r = c.post(f"{O}/api/library/cornstover/run", json={"by": "h403", "inputs": inputs}, headers=H)
    if r.status_code != 200:
        fail(f"the {tag} run answered {r.status_code}: {r.text[:400]}")
    d = r.json()
    json.dump(d, open(f"{OUT}/{tag}.json", "w"))
    return d


with httpx.Client(trust_env=False, timeout=1200) as c:
    r = c.get(f"{O}/api/library/cornstover/parameters", headers=H)
    if r.status_code != 200:
        fail(f"parameters answered {r.status_code}: {r.text[:300]}")
    lp = r.json()
    spec = next((s for s in lp["specs"] if s["key"] == KEY), None)
    val = next((v for v in lp["values"] if v["key"] == KEY), None)
    if spec is None or val is None:
        fail(f"cornstover has no parameter {KEY}")
    default, unit = val["value"], spec.get("unit")
    print(f"library default of {KEY}: {default!r} {unit} (origin {val['origin']}), "
          f"read from GET /api/library/cornstover/parameters")
    a = run(c, [], "nothing-set")
    q = {"value": default, "unit": unit, "origin": {"kind": "person-assumption", "by": "h403", "at": "2026-11-10"}}
    b = run(c, [{"name": KEY, "quantity": q}], "default-set")

oa, ob = a["artifact"]["output"], b["artifact"]["output"]
pa, pb = oa["price"], ob["price"]
ta, tb = oa.get("tea") or {}, ob.get("tea") or {}


def precision(d):
    for i in d["artifact"].get("inputs", []):
        if i.get("name") == "precision":
            return i.get("value")
    return None


def basis_value(d):
    for i in d["artifact"].get("inputs", []):
        if i.get("name") == KEY:
            return i.get("value")
    return None


def readback(o):
    for q in o.get("parameters", []):
        if q.get("key") == KEY:
            return q.get("value")
    return None


def line(t, key):
    return next((l["perUnit"] for l in t.get("lines", []) if l["key"] == key), None)


def stream(o, sid):
    return next((s for s in o.get("streams", []) if s["id"] == sid), {})


print(f"run A (nothing set): run {a['run']['id']}, artifact {a['artifact']['id']}, overrides {oa.get('overrides')}, "
      f"basis precision {precision(a)!r}")
print(f"run B ({KEY} = its default): run {b['run']['id']}, artifact {b['artifact']['id']}, "
      f"overrides {ob.get('overrides')}, basis precision {precision(b)!r}, {KEY} in the basis {basis_value(b)!r} "
      f"and read back {readback(ob)!r}")
print(f"{'':26s} {'A nothing set':>18s} {'B default set':>18s} {'B/A - 1':>10s}")


def row(name, x, y):
    rel = (y / x - 1) if isinstance(x, (int, float)) and isinstance(y, (int, float)) and x else float("nan")
    print(f"{name:26s} {x!s:>18s} {y!s:>18s} {rel:>10.2e}")


for k in ("solvedPrice", "packagePrice", "NPV", "IRR", "sales", "material_cost", "utility_cost", "TCI", "FCI", "VOC",
          "installed_equipment_cost", "feedstockKgPerH"):
    row(f"price.{k}", pa.get(k), pb.get(k))
row("tea.capitalRecovery", ta.get("capitalRecovery"), tb.get("capitalRecovery"))
row("tea line capitalRecovery", line(ta, "capitalRecovery"), line(tb, "capitalRecovery"))
prod = pa.get("product") or "ethanol"
row(f"stream {prod} massFlow", stream(oa, prod).get("massFlow"), stream(ob, prod).get("massFlow"))

sa, sb = pa.get("solvedPrice"), pb.get("solvedPrice")
if not isinstance(sa, (int, float)) or not isinstance(sb, (int, float)):
    fail(f"a solved price is missing: {sa!r}, {sb!r}")
rel = abs(sb / sa - 1)
bv = basis_value(b)
same_value = (bv is not None and float(bv) == float(default) and readback(ob) is not None
              and math.isclose(readback(ob), default, rel_tol=RTOL))
# The feed's price enters the material cost alone: what B's material cost may move by from the price it set.
hours = ta.get("operatingHours")
feed_gap = abs(float(bv) - float(default)) * pa["feedstockKgPerH"] * hours if bv is not None and hours else None
mat_gap = pb["material_cost"] - pa["material_cost"]
util_gap = pb["utility_cost"] - pa["utility_cost"]
print(f"EXPECTED: run B sets {KEY} to the library's own default ({default!r} {unit}), so it prices ethanol at run "
      f"A's {sa} USD/kg within the basis's ten significant digits (rtol {RTOL:g}), with A's NPV {pa.get('NPV')} USD")
print(f"OBSERVED: run B prices ethanol at {sb} USD/kg (relative difference {rel:.2e}, {rel / RTOL:.0f} times the "
      f"stated rtol) with NPV {pb.get('NPV')} USD; {KEY} in its basis {'equal to' if same_value else 'unlike'} the "
      f"default; capital recovery {tb.get('capitalRecovery')} against {ta.get('capitalRecovery')} USD/yr; material "
      f"cost moved {mat_gap:+.2f} USD/yr where the price set moves it {feed_gap!r} USD/yr, and the utility cost, "
      f"which no feed price enters, moved {util_gap:+.2f} USD/yr: the process itself was simulated again")
print("RESULT: DEFECT" if same_value and rel > RTOL else "RESULT: NO-DEFECT")
