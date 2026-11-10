"""H4: cornstover through POST /api/library/cornstover/run with one person's value equal to the library default
(the feedstock price, 0.05158816935126135 USD/kg); its solved price beside the run that sets nothing.
    cd core && bh_env .venv/bin/python cornstover_feeddefault.py http://127.0.0.1:8840 h4p
"""
import json, sys, httpx
O, P = sys.argv[1], sys.argv[2]
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
q = {"value": 0.05158816935126135, "unit": "USD/kg", "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
with httpx.Client(trust_env=False, timeout=900) as c:
    r = c.post(f"{O}/api/library/cornstover/run", json={"by": "h4", "inputs": [{"name": "stream.cornstover.price", "quantity": q}]}, headers=H)
    print(r.status_code)
    d = r.json()
    json.dump(d, open(f"{W}/svc-cornstover-feeddefault.json", "w"))
    o = d["artifact"]["output"]
    pr, tea = o["price"], o["tea"]
    print("id", d["run"]["id"], "packagePrice", pr["packagePrice"], "solvedPrice", pr["solvedPrice"], "NPV", pr["NPV"])
    print("tea.productPrice", tea["productPrice"], "capitalRecovery USD/yr", tea["capitalRecovery"])
    for l in tea["lines"]:
        print(f"  {l['key']:16s} {l['perUnit']:.6f} USD/kg  {l['usdPerYear']:.6g} USD/yr")
    print("sum of lines", sum(l["perUnit"] for l in tea["lines"]))
