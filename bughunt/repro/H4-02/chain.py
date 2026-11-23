"""H4-02: the fewest service calls that make a custom_train_v1 run, then its cost card's numbers.

    chain.py run    (env H402_ORIGIN, H402_PROJECT, H402_OUT): a fermOS batch simulation, its vessel design, an
                    ethanol_glucose_v0 run read into a train and the train run, then the composite run
                    (POST /api/proforma/run, flowsheet custom_train_v1) from the vessel and the train run.
                    Writes <out>/composite.json and prints the run's id.
    chain.py judge  (env H402_OUT): reads composite.json and the page's card (<out>/screen.json) and prints the
                    EXPECTED, OBSERVED and RESULT lines.

Every value is a person-assumption typed here, dated 2026-11-10, as the hunt's scripts typed them
(bughunt/notes/H4/scripts/kinetics_cases.py case 2, vessel_one.py, scenario_run.py, composite_run.py).
"""
import json
import os
import sys

import httpx

OUT = os.environ["H402_OUT"]
AT = {"kind": "person-assumption", "by": "h402", "at": "2026-11-10"}


def q(v, u):
    return {"value": v, "unit": u, "origin": AT}


def ins(vals):
    return [{"name": k, "quantity": q(*v)} for k, v in vals.items()]


def post(c, path, body, H):
    r = c.post(path, json=body, headers=H)
    if r.status_code != 200:
        sys.exit(f"{path} answered {r.status_code}: {r.text[:600]}")
    return r.json()


def run():
    O, P = os.environ["H402_ORIGIN"], os.environ["H402_PROJECT"]
    H = {"X-OpenFerment-Project": P}
    with httpx.Client(base_url=O, trust_env=False, timeout=900) as c:
        # 1. A batch_v1 simulation (the hunt's case 2: exponential growth, Ks 0, a growth-associated product).
        sim = post(c, "/api/fermos/simulate", {"family": "batch_v1", "by": "h402", "inputs": ins({
            "mu_max": (0.3, "h⁻¹"), "ks": (0.0, "g L⁻¹"), "yxs": (0.5, "g g⁻¹"), "alpha": (0.4, "g g⁻¹"),
            "yps": (0.5, "g g⁻¹"), "p_max": (1e12, "g L⁻¹"), "x0": (2.0, "g L⁻¹"), "s0": (20.0, "g L⁻¹"),
            "p0": (0.0, "g L⁻¹")})}, H)
        print(f"simulation {sim['artifactId']}", file=sys.stderr)
        # 2. Its vessel at a plant scale.
        ves = post(c, "/api/fermos/vessel", {"simulation": sim["artifactId"], "by": "h402",
                                             "inputs": ins({"plant_scale": (1000.0, "t yr⁻¹")})}, H)
        print(f"vessel {ves['artifactId']}", file=sys.stderr)
        # 3. An ethanol_glucose_v0 run, read into a train, the train run.
        eg = post(c, "/api/engines/biosteam/run", {"thing": "ethanol_glucose_v0", "by": "h402", "inputs": ins({
            "feed_glucose_conc": (150.0, "g L-1"), "titre": (70.0, "g L-1"), "yield": (0.45, "g g-1"),
            "productivity": (2.0, "g L-1 h-1"), "plant_scale": (100000.0, "t yr-1"),
            "glucose_price": (0.4, "USD kg-1")})}, H)
        eg_id = (eg.get("run") or eg)["id"]
        print(f"ethanol_glucose_v0 run {eg_id}", file=sys.stderr)
        fr = post(c, "/api/pureos/train/from-run", {"artifactId": eg_id}, H)
        tr = post(c, "/api/pureos/train/run", {"train": fr["train"], "by": "h402"}, H)
        print(f"train run {tr['artifactId']} ({len(fr['train']['units'])} units)", file=sys.stderr)
        # 4. The composite: the vessel's fermenter and the train's units, priced.
        d = post(c, "/api/proforma/run", {
            "scenarioId": "h402-composite", "flowsheet": "custom_train_v1", "vessel": ves["artifactId"],
            "trainRun": tr["artifactId"], "by": "h402", "samples": 4, "inputs": ins({
                "feed_glucose_conc": (20.0, "g L-1"), "titre": (2.85, "g L-1"), "yield": (0.143, "g g-1"),
                "productivity": (0.56, "g L-1 h-1"), "glucose_price": (0.4, "USD kg-1")})}, H)
        # The run as the page reads it back (its tables), beside the run route's answer.
        tables = c.get(f"/api/biorepo/artifacts/{d['artifactId']}/tables", headers=H)
        d["_tables"] = tables.json() if tables.status_code == 200 else {"status": tables.status_code}
    json.dump(d, open(f"{OUT}/composite.json", "w"), indent=1)
    print(d["artifactId"])


def judge():
    d = json.load(open(f"{OUT}/composite.json"))
    tea = d["tea"]
    lines = [(l["key"], l["perUnit"]) for l in tea["lines"]]
    total = sum(v for _, v in lines if v is not None)
    base, pp, bf = d["basePrice"], tea["productPrice"], tea["basisFlow"]
    prod = next(s for s in d["streams"] if s["id"] == tea["product"])
    rebased = pp * prod["massFlow"] / bf
    tt = (d.get("_tables") or {}).get("tea") or {}
    print(f"run {d['artifactId']}: flowsheet custom_train_v1, basis '{tea['basis']}', basisFlow {bf:.6f} kg/h")
    print("lines (perUnit): " + ", ".join(f"{k} {v:.4f}" for k, v in lines) + f"; their sum {total:.10f}")
    print(f"basePrice {base:.10f}; tea.productPrice {pp:.10f}"
          + (f" (the tables route: {tt.get('productPrice'):.10f})" if tt.get("productPrice") is not None else ""))
    print(f"product stream {prod['id']}: {prod['massFlow']:.6f} kg/h holding {prod['massFlows']}")
    print(f"tea.productPrice x stream mass / basisFlow = {rebased:.10f}")
    sc = {}
    try:
        sc = json.load(open(f"{OUT}/screen.json"))["composite"]
    except Exception as e:  # noqa: BLE001 - the render is reported, then judged absent
        print(f"the page's card: not read ({e})")
    total_row = next((r for r in sc.get("rows", []) if r.startswith(("Price the lines", "Base-case price"))), None)
    print(f"page: closing row '{total_row}'; note '{sc.get('note')}'; base line '{sc.get('base')}'")

    def rel(a, b):
        return abs(a - b) / max(abs(a), abs(b), 1e-12)

    sum_is_base = rel(total, base) <= 1e-9
    pp_differs = rel(pp, base) > 1e-6
    same_price_rebased = rel(rebased, base) <= 1e-9
    row_at_pp = bool(total_row) and total_row.startswith("Price the lines are read at") and \
        abs(float(total_row.rsplit(" ", 1)[1]) - pp) < 5e-5
    note_false = bool(sc.get("note")) and "its lines sum to that price" in sc["note"] and f"{pp:.4f}" in sc["note"]
    print(f"checks: lines sum to basePrice {sum_is_base}; productPrice differs from basePrice {pp_differs}; "
          f"productPrice on the stream's basis is basePrice {same_price_rebased}; "
          f"closing row at productPrice {row_at_pp}; note says the lines sum to productPrice {note_false}")
    print(f"EXPECTED: the cost card's closing row is {total:.4f} USD per {tea['basis']} (the sum of its lines, the "
          "run's base-case price), labelled 'Base-case price', with no note of a second price "
          "(flowsheets/__init__.py:20-21: `price` per kg of the product stream, `basis_flow` the kg/hr the price is "
          "per; CostWaterfall.tsx:7-9: the lines sum to the last row by construction in the service)")
    print(f"OBSERVED: tea.productPrice {pp:.4f} is the TEA's price per kg of the {prod['id']} stream "
          f"({prod['massFlow']:.3f} kg/h) while basisFlow is the {bf:.3f} kg/h of product it contains; the lines "
          f"sum to {total:.4f} = basePrice; the page closes on '{total_row}' and its note says the lines sum to "
          f"{pp:.4f} and the TEA solved another price, {base:.4f}")
    defect = sum_is_base and pp_differs and same_price_rebased and row_at_pp and note_false
    print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")


if __name__ == "__main__":
    {"run": run, "judge": judge}[sys.argv[1]]()
