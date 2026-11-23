"""H1-04, a supporting probe (run.sh does not need it): the Proforma worker's own `evaluate`, one built
ethanol_glucose_v0, the run's six inputs evaluated twice in one process, and where the fermenter's
ethanol goes each time. Run from the repository root:

    source bughunt/lib/env.sh; bh_py ../bughunt/repro/H1-04/mass_balance.py 2>&1 | grep -v Warn

It reads nothing from the database and starts no service; keyless."""
from openferment_core.workers import proforma_worker as w

V = {"feed_glucose_conc": 100.0, "titre": 50.0, "yield": 0.4, "productivity": 1.0, "plant_scale": 1000.0,
     "glucose_price": 0.5}
module, b = w.built("ethanol_glucose_v0")
for case in (1, 2):
    out = w.evaluate("ethanol_glucose_v0", V)
    made = float(b.R1.outs[1].imass["Ethanol"]) + float(b.R1.outs[0].imass["Ethanol"])
    left = {s.ID: float(s.imass["Ethanol"]) for s in b.system.products}
    s9, s5 = (next(s for s in b.system.streams if s.ID == i) for i in ("s9", "s5"))
    beer = next(s for s in b.system.streams if s.ID == "distilled_beer")
    print(f"case {case}: price {out['pricePerKgEthanol']:.6f} USD/kg | ethanol out of the fermenter {made:.3f} kg/h, "
          f"leaving the plant {sum(left.values()):.3f} kg/h ({', '.join(f'{k} {v:.3f}' for k, v in left.items())}) | "
          f"the recycle s9 {float(s9.imass['Ethanol']):.3f}, the mixer's outlet s5 {float(s5.imass['Ethanol']):.3f} "
          f"(distilled_beer {float(beer.imass['Ethanol']):.3f}) | s5 P {s5.P:.1f} Pa")
