"""H4: a custom_train_v1 run (POST /api/proforma/run) from a kept vessel design and a kept train run, then its cost
card's arithmetic: the lines' sum against tea.productPrice (the waterfall's closing row) and against the run's base price.
    cd core && bh_env .venv/bin/python composite_run.py http://127.0.0.1:8840 h4p <vessel id> <train run id> <tag>
"""
import json, sys, httpx
O, P, V, T, TAG = sys.argv[1:6]
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
def q(v, u): return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
vals = {"feed_glucose_conc": (20.0, "g L-1"), "titre": (2.85, "g L-1"), "yield": (0.143, "g g-1"),
        "productivity": (0.56, "g L-1 h-1"), "glucose_price": (0.4, "USD kg-1")}
body = {"scenarioId": f"h4-composite-{TAG}", "flowsheet": "custom_train_v1", "vessel": V, "trainRun": T, "by": "h4",
        "samples": 5, "inputs": [{"name": k, "quantity": q(*v)} for k, v in vals.items()]}
with httpx.Client(trust_env=False, timeout=900) as c:
    r = c.post(f"{O}/api/proforma/run", json=body, headers=H)
    print(r.status_code)
    d = r.json()
    json.dump(d, open(f"{W}/composite-{TAG}.json", "w"))
    if r.status_code != 200:
        print(json.dumps(d)[:2000]); sys.exit()
    tea = d["tea"]
    s = sum(l["perUnit"] for l in tea["lines"] if l["perUnit"] is not None)
    print("artifact", d["artifactId"], "basePrice", d["basePrice"], "tea.productPrice", tea["productPrice"],
          "basisFlow", tea["basisFlow"], "basis", tea["basis"])
    for l in tea["lines"]:
        print(f"  {l['key']:16s} {l['perUnit']:.6f}  {l['usdPerYear']:.6g} USD/yr")
    print("sum of lines", s, " closing row (tea.productPrice)", tea["productPrice"], " base price", d["basePrice"])
    prod = [x for x in d["streams"] if x["id"] == tea["product"]][0]
    print("product stream", prod["id"], prod["massFlow"], prod["massFlows"])
