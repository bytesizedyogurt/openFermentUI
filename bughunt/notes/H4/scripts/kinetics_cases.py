"""H4: fermOS families against closed forms, through POST /api/fermos/simulate and the
kinetics engine (POST /api/engines/kinetics/run). Each case is solvable by hand.

    cd /home/user/openFermentUI/core && bh_env .venv/bin/python \
        /home/user/openFermentUI/bughunt/notes/H4/scripts/kinetics_cases.py http://127.0.0.1:8840 h4p

Prints, for each case: the largest relative error of X, S, P (and V) over the series against
the closed form, the end state, the run-out hour against the hand value, the mass closure
(sugar consumed x yield against biomass plus product formed), and the engine's outputs with
their units beside the route's.
"""
import json
import math
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8840"
PROJECT = sys.argv[2] if len(sys.argv) > 2 else "h4p"
H = {"X-OpenFerment-Project": PROJECT}
U = {"mu_max": "h⁻¹", "ks": "g L⁻¹", "kd": "h⁻¹", "yxs": "g g⁻¹", "alpha": "g g⁻¹", "beta": "g g⁻¹ h⁻¹",
     "yps": "g g⁻¹", "maintenance": "g g⁻¹ h⁻¹", "p_max": "g L⁻¹", "n_inhibition": "", "yxo": "g g⁻¹",
     "mo": "g g⁻¹ h⁻¹", "x0": "g L⁻¹", "s0": "g L⁻¹", "p0": "g L⁻¹", "v0": "L", "t_end": "h",
     "feed_rate": "L h⁻¹", "mu_set": "h⁻¹", "feed_conc": "g L⁻¹", "feed_start_h": "h", "feed_end_h": "h",
     "dilution_rate": "h⁻¹", "feed_profile": "", "ki_substrate": "g L⁻¹"}
BIG = 1e12  # a Pmax no product reaches: (1 - P/Pmax) is 1 to twelve digits


def q(k, v):
    return {"value": v, "unit": U[k], "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}


def inputs(vals):
    return [{"name": k, "quantity": q(k, v)} for k, v in vals.items()]


client = httpx.Client(trust_env=False, timeout=300)
report = {}


def simulate(family, vals):
    r = client.post(f"{O}/api/fermos/simulate", json={"family": family, "by": "h4", "inputs": inputs(vals)}, headers=H)
    return r.status_code, r.json()


def engine(family, vals):
    r = client.post(f"{O}/api/engines/kinetics/run", json={"thing": family, "by": "h4", "inputs": inputs(vals)},
                    headers=H)
    return r.status_code, r.json()


def worst(series, key, exact):
    t = series["t"]
    errs = []
    for ti, yi in zip(t, series[key]):
        e = exact(ti)
        errs.append(abs(yi - e) / max(abs(e), 1e-9))
    k = max(range(len(errs)), key=lambda i: errs[i])
    return errs[k], t[k], series[key][k], exact(t[k])


def case(name, family, vals, exact, *, runout=None, closure=None):
    code, d = simulate(family, vals)
    print(f"\n== {name} ({family}) -> {code}")
    if code != 200:
        print("  refused:", d)
        report[name] = {"status": code, "detail": d}
        return None
    row = {"artifact": d["artifactId"], "units": d["units"], "end": d["end"], "harvestH": d["harvestH"],
           "sugarRunsOutH": d["sugarRunsOutH"], "finalTitre": d["finalTitre"], "yieldAchieved": d["yieldAchieved"],
           "productivity": d["productivity"], "massBalance": d["massBalance"]}
    s = d["series"]
    for key, f in exact.items():
        if key in s:
            e, t, got, want = worst(s, key, f)
            row[f"worst_{key}"] = e
            flag = "  <-- off" if e > 1e-4 else ""
            print(f"  {key}: worst relative error {e:.2e} at t={t:.4g} h (got {got:.10g}, closed form {want:.10g}){flag}")
    print(f"  end {d['end']}  units {d['units']}")
    print(f"  sugarRunsOutH {d['sugarRunsOutH']}  harvestH {d['harvestH']}  titre {d['finalTitre']}  "
          f"yield {d['yieldAchieved']}  productivity {d['productivity']}")
    if runout is not None:
        got = d["sugarRunsOutH"]
        rel = abs(got - runout) / runout if got is not None else None
        print(f"  run-out hour: service {got}, hand {runout:.10g}, rel {rel}")
        row["runout_hand"], row["runout_rel"] = runout, rel
    if closure is not None:
        c = closure(d)
        print(f"  closure (by hand from the end state): {c}")
        row["closure"] = c
    print(f"  massBalance {d['massBalance']['closure']:.2e} ok={d['massBalance']['ok']}")
    print(f"  our unit: {d['our'].get('unit') if isinstance(d.get('our'), dict) else None}; our keys {list(d['our'].keys()) if isinstance(d.get('our'), dict) else d.get('our')}")
    ecode, er = engine(family, vals)
    if ecode == 200:
        run = er.get("run") or er
        outs = {v["name"]: (v["quantity"]["value"], v["quantity"]["unit"]) for v in run["outputs"]["values"]}
        row["engine"] = {"id": run["id"], "outputs": outs}
        same = run["id"] == d["artifactId"]
        print(f"  engine run {run['id']} (same as the route's artifact: {same}); outputs:")
        for k, (v, u) in outs.items():
            print(f"    {k} = {v!r} [{u}]")
        for st, val in d["end"].items():
            if st == "t":
                continue
            ev = outs.get(f"end.{st}")
            if ev is None or abs(ev[0] - val) > 1e-12 * max(1, abs(val)):
                print(f"    <-- end.{st} differs: route {val} engine {ev}")
    else:
        print(f"  engine -> {ecode}: {json.dumps(er)[:400]}")
        row["engine"] = {"status": ecode, "detail": er}
    report[name] = row
    return d


# 1. No growth, a non-growth-associated product: X constant, P linear, S linear.
X0, S0, b, yps = 2.0, 20.0, 0.1, 0.5
case("zero growth, beta product", "batch_v1",
     {"mu_max": 0.0, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "beta": b, "yps": yps, "p_max": BIG,
      "x0": X0, "s0": S0, "p0": 0.0, "t_end": 40.0},
     {"X": lambda t: X0, "P": lambda t: b * X0 * t, "S": lambda t: S0 - b * X0 * t / yps},
     closure=lambda d: {"S used x Yp/s": (S0 - d["end"]["S"]) * yps, "P made": d["end"]["P"]})

# 2. Exponential growth on a Monod with Ks = 0, growth-associated product: closed form in X.
mu, yxs, al = 0.3, 0.5, 0.4
den = 1 / yxs + al / yps
tstar = math.log(1 + S0 / den / X0) / mu  # the hour S reaches zero
trun = math.log(1 + (1 - 1e-3) * S0 / den / X0) / mu  # the hour S reaches 1e-3 of its start
xexp = lambda t: X0 * math.exp(mu * min(t, tstar))
case("exponential growth, Ks 0, alpha product", "batch_v1",
     {"mu_max": mu, "ks": 0.0, "yxs": yxs, "alpha": al, "yps": yps, "p_max": BIG, "x0": X0, "s0": S0, "p0": 0.0},
     {"X": xexp, "P": lambda t: al * (xexp(t) - X0), "S": lambda t: max(S0 - (xexp(t) - X0) * den, 0.0)},
     runout=trun,
     closure=lambda d: {"S used": S0 - d["end"]["S"],
                        "(X-X0)/Yx/s + P/Yp/s": (d["end"]["X"] - X0) / yxs + d["end"]["P"] / yps})

# 3. Decay alone: X = X0 exp(-kd t); sugar and product untouched.
kd = 0.05
case("decay alone", "batch_v1",
     {"mu_max": 0.0, "ks": 1.0, "kd": kd, "yxs": 0.5, "alpha": 0.0, "yps": yps, "p_max": BIG,
      "x0": X0, "s0": S0, "p0": 1.0, "t_end": 30.0},
     {"X": lambda t: X0 * math.exp(-kd * t), "S": lambda t: S0, "P": lambda t: 1.0})

# 4. Maintenance alone: S = S0 - m X0 t.
m = 0.2
case("maintenance alone", "batch_v1",
     {"mu_max": 0.0, "ks": 1.0, "maintenance": m, "yxs": 0.5, "alpha": 0.0, "yps": yps, "p_max": BIG,
      "x0": X0, "s0": S0, "p0": 0.0, "t_end": 30.0},
     {"X": lambda t: X0, "S": lambda t: S0 - m * X0 * t, "P": lambda t: 0.0})

# 5. One substrate, constant yield, Monod: X + Yx/s S is conserved; at run-out X = X0 + Yx/s S0 (1 - 1e-3).
case("Monod, constant yield, no product", "batch_v1",
     {"mu_max": 0.4, "ks": 0.5, "yxs": yxs, "alpha": 0.0, "yps": yps, "p_max": BIG, "x0": 0.1, "s0": S0, "p0": 0.0},
     {},
     closure=lambda d: {"X end": d["end"]["X"], "X0 + Yx/s (S0 - S end)": 0.1 + yxs * (S0 - d["end"]["S"])})

# 6. Chemostat at steady state: S* = Ks D/(mu_max - D), X* = (Sf - S*)/(1/Yx/s + alpha/Yp/s), P* = alpha X*.
D, mm, ks, Sf = 0.1, 0.4, 1.0, 20.0
Ss = ks * D / (mm - D)
Xs = (Sf - Ss) / den
d6 = case("chemostat steady state", "chemostat_v1",
          {"mu_max": mm, "ks": ks, "yxs": yxs, "alpha": al, "yps": yps, "p_max": BIG, "dilution_rate": D,
           "feed_conc": Sf, "x0": Xs, "s0": Ss, "p0": al * Xs, "t_end": 50.0},
          {"X": lambda t: Xs, "S": lambda t: Ss, "P": lambda t: al * Xs})
if d6:
    print("  steadyState:", json.dumps(d6.get("steadyState"))[:800])
    print(f"  hand: S* {Ss:.10g} X* {Xs:.10g} P* {al * Xs:.10g}; washout D mu_max Sf/(Ks+Sf) = {mm * Sf / (ks + Sf):.10g}")
    report["chemostat steady state"]["steadyState"] = d6.get("steadyState")

# 7. Fed-batch, constant feed, no growth and no uptake: V = V0 + F t, every concentration diluted.
V0, F, Sfb = 1.0, 0.05, 100.0
case("fed-batch dilution alone", "fedbatch_v1",
     {"mu_max": 0.0, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "yps": yps, "p_max": BIG, "feed_profile": "constant",
      "feed_rate": F, "mu_set": 0.1, "feed_conc": Sfb, "x0": X0, "s0": S0, "p0": 3.0, "v0": V0, "t_end": 20.0},
     {"V": lambda t: V0 + F * t, "X": lambda t: X0 * V0 / (V0 + F * t),
      "S": lambda t: (S0 * V0 + F * Sfb * t) / (V0 + F * t), "P": lambda t: 3.0 * V0 / (V0 + F * t)})

# 8. Aerobic exponential growth: OUR = (mu/Yx/o + mo) X.
d8 = case("aerobic exponential growth (OUR)", "batch_v1",
          {"mu_max": mu, "ks": 0.0, "yxs": yxs, "alpha": 0.0, "yps": yps, "p_max": BIG, "x0": X0, "s0": S0,
           "p0": 0.0, "yxo": 1.0, "mo": 0.01, "t_end": 2.0},
          {"X": lambda t: X0 * math.exp(mu * t)})
if d8:
    our = d8["our"]
    print("  our keys:", list(our.keys()), "unit:", our.get("unit"), "peak:", our.get("peak"), our.get("peakH"))
    ts = our["t"]
    vals = our.get("our") or our.get("values") or our.get("rate")
    if vals:
        errs = [abs(v - (mu / 1.0 + 0.01) * X0 * math.exp(mu * t)) / ((mu + 0.01) * X0 * math.exp(mu * t))
                for t, v in zip(ts, vals)]
        print(f"  OUR worst relative error {max(errs):.2e}")
        report["aerobic exponential growth (OUR)"]["our_worst"] = max(errs)
json.dump(report, open("/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4/kinetics_cases.json", "w"),
          indent=1, default=str)
