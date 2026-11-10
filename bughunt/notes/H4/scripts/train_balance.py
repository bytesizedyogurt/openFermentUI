"""H4: conservation of mass across every unit of a train run's stream table, and the train's own
reading of it (recovery, productOut, productLost, overallRecovery, purity), recomputed from the table.

    python3 train_balance.py train-run.json [run-report.json]

train-run.json is POST /api/pureos/train/run's answer; run-report.json, if given, is
GET /api/runs/{id} for the same run (its outputs.values are compared with the table).
"""
import json
import sys
from collections import defaultdict

d = json.load(open(sys.argv[1]))
t = d["train"]
streams = {s["id"]: s for s in t["streams"]}
print("table units:", t["tableUnits"])
bad = 0
# 1. Every stream's total against the sum of its components.
for s in t["streams"]:
    tot = sum(s["massFlows"].values())
    if abs(tot - s["massFlow"]) > 1e-9 * max(1, s["massFlow"]):
        bad += 1
        print(f"  stream {s['id']}: massFlow {s['massFlow']} but components sum {tot}")
# 2. Each unit: inlets equal outlets, component by component (no reaction in a separation train).
for u in t["units"]:
    ins = defaultdict(float)
    outs = defaultdict(float)
    for sid in u["ins"]:
        for c, f in streams[sid]["massFlows"].items():
            ins[c] += f
    for sid in u["outs"]:
        for c, f in streams[sid]["massFlows"].items():
            outs[c] += f
    worst = max((abs(ins[c] - outs[c]) / max(ins[c], outs[c], 1e-12), c) for c in set(ins) | set(outs))
    tin, tout = sum(ins.values()), sum(outs.values())
    flag = "  <-- does not close" if worst[0] > 1e-6 else ""
    if flag:
        bad += 1
    print(f"  {u['id']:6s} {u['unitClass']:22s} in {tin:14.6f} out {tout:14.6f} kg/hr; worst component {worst[1]} "
          f"rel {worst[0]:.2e}; unit says massIn {u['massIn']:.6f} massOut {u['massOut']:.6f}{flag}")
    # The unit's own reading of the product.
    p = t["product"]
    pin = ins.get(p, 0.0)
    pout = outs.get(p, 0.0)
    if abs(pin - u["productIn"]) > 1e-9 * max(1, pin):
        print(f"     productIn {u['productIn']} against the table's {pin}")
    if u["productIn"] and u["recovery"] is not None:
        r = u["productOnward"] / u["productIn"]
        if abs(r - u["recovery"]) > 1e-12:
            print(f"     recovery {u['recovery']} against productOnward/productIn {r}")
    if abs(u["productIn"] - u["productOnward"] - u["productLost"]) > 1e-6 * max(1, u["productIn"]):
        print(f"     productIn - productOnward = {u['productIn'] - u['productOnward']} against productLost {u['productLost']} "
              f"(lostTo {u['lostTo']})")
cum = 1.0
for u in t["units"]:
    if u["recovery"] is not None:
        cum *= u["recovery"]
    if u["cumulative"] is not None and abs(cum - u["cumulative"]) > 1e-12:
        print(f"  {u['id']}: cumulative {u['cumulative']} against the product of recoveries {cum}")
first = t["units"][0]
print(f"overallRecovery {t['overallRecovery']} ; productOut/productIn(first unit) "
      f"{t['productOut'] / first['productIn']}; product of recoveries {cum}")
print(f"productOut {t['productOut']} ; {t['productStream']} carries "
      f"{streams[t['productStream']]['massFlows'].get(t['product'])}")
print(f"productLost {t['productLost']} ; first productIn - productOut {first['productIn'] - t['productOut']}")
pur = d["purity"]
ps = streams[t["productStream"]]
print(f"purity.productFraction {pur['productFraction']} ; table {ps['massFlows'].get(t['product'], 0) / ps['massFlow']}")
for s in pur["streams"]:
    tab = streams[s["stream"]]
    f = tab["massFlows"].get(t["product"], 0) / tab["massFlow"] if tab["massFlow"] else None
    if f is not None and abs(f - s["productFraction"]) > 1e-12:
        print(f"  purity of {s['stream']} {s['productFraction']} against table {f}")
    imp = sum(i["massFraction"] for i in s["impurities"]) + s["productFraction"]
    if abs(imp - 1) > 1e-9:
        print(f"  purity of {s['stream']}: product share and impurities sum to {imp}")
if len(sys.argv) > 2:
    rep = json.load(open(sys.argv[2]))
    vals = {v["name"]: v["quantity"] for v in rep["run"]["outputs"]["values"]}
    print("run outputs:")
    for k, q in vals.items():
        if k.startswith("massFlow."):
            sid = k.split(".", 1)[1]
            ok = abs(q["value"] - streams[sid]["massFlow"]) <= 1e-9 * max(1, q["value"])
            if not ok:
                print(f"  {k} {q} against table {streams[sid]['massFlow']}")
        elif k.startswith("purity."):
            sid = k.split(".", 1)[1]
            f = streams[sid]["massFlows"].get(t["product"], 0) / streams[sid]["massFlow"]
            if abs(q["value"] - f) > 1e-12:
                print(f"  {k} {q['value']} against table {f}")
        else:
            print(f"  {k} = {q['value']} [{q['unit']}]")
    units = {q["unit"] for k, q in vals.items() if k.startswith("massFlow.")} | {vals["productOut"]["unit"]} if "productOut" in vals else set()
    print("  units used for massFlow.* and productOut:", units)
print("streams that do not balance or units that do not close:", bad)
