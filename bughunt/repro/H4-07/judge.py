"""H4-07 judge: reads one ethanol_glucose_v0 run (the route's JSON answer), the shelf the service serves, the
parameter panel's specs for the same flowsheet and the source lines that set the batch time, then prints EXPECTED,
OBSERVED and RESULT. Usage: judge.py RUN_JSON SHELF_JSON PARAMS_JSON REPO_ROOT

The candidate says the titre input ("ethanol titre at harvest") sets only the batch time, the beer's ethanol follows
from the feed's glucose and the yield, and a titre above feed x yield is priced with no word. The judge measures that
behaviour, then reads the input's own declared description (the shelf's note, which the panel shows as the input's
gloss). DEFECT when the behaviour holds and the description the service serves for the input leaves it unsaid;
NO-DEFECT when the served description says the beer's ethanol follows from the feed and the yield and the run reads
it back, since the run then does what its input says it does."""
import json
import math
import sys
from pathlib import Path

run_file, shelf_file, params_file, root = (Path(a) for a in sys.argv[1:5])


def src_line(rel: str, needle: str) -> str:
    lines = (root / rel).read_text().splitlines()
    return next((f"{rel}:{i}: {ln.strip()}" for i, ln in enumerate(lines, 1) if needle in ln), f"{rel}: '{needle}' not found")


try:
    d = json.loads(run_file.read_text())
    run, o = d["run"], d["artifact"]["output"]
    rb = o["readBack"]
    typed = {i["name"]: i["quantity"]["value"] for i in run["inputs"]}
    feed, titre, yld, prod = (float(typed[k]) for k in ("feed_glucose_conc", "titre", "yield", "productivity"))
    beer, batch, price = float(rb["beerEthanolGPerL"]), float(rb["batchTimeH"]), o.get("basePrice")
except Exception as e:  # noqa: BLE001
    print("EXPECTED: an ethanol_glucose_v0 run with its inputs and its read-back")
    print(f"OBSERVED: the run's answer could not be read ({type(e).__name__}: {e}); head: {run_file.read_text()[:300]!r}")
    print("RESULT: NO-DEFECT")
    sys.exit(0)

shelf = json.loads(shelf_file.read_text())
entry = next((f for f in shelf if f.get("id") == "ethanol_glucose_v0"), {})
inp = next((i for i in entry.get("inputs", []) if i.get("key") == "titre"), {})
note = inp.get("note") or ""
try:
    params = json.loads(params_file.read_text())
    spec = next((s for s in params.get("specs", []) if s.get("key") == "titre"), {})
    gloss = spec.get("gloss") or ""
except Exception:  # noqa: BLE001
    gloss = ""

print(f"run {run['id']} ({run.get('status')}): typed feed_glucose_conc {feed:g} g L-1, titre {titre:g} g L-1, "
      f"yield {yld:g} g g-1, productivity {prod:g} g L-1 h-1")
print(f"read back: beerEthanolGPerL {beer:.4f}, batchTimeH {batch:g}, fermenterConversion "
      f"{float(rb['fermenterConversion']):.4f}; basePrice {price} USD/kg; baseInfeasible {o.get('baseInfeasible')}")
print(f"feed x yield = {feed * yld:g} g L-1 (the titre typed is {titre - feed * yld:+g} above it); titre / productivity "
      f"= {titre / prod:g} h; beer / batch time = {beer / batch:.4f} g L-1 h-1 (productivity typed {prod:g})")
print("source: " + src_line("core/openferment_core/flowsheets/ethanol_glucose_v0.py", '"titre": ("ethanol titre at harvest"'))
print("source: " + src_line("core/openferment_core/flowsheets/ethanol_glucose_v0.py", 'b.R1.tau = v["titre"] / v["productivity"]'))
print("source: " + src_line("core/openferment_core/flowsheets/shelf.py", "with the productivity, sets the batch time; the beer's own"))
print(f"served shelf note for the titre input (GET /api/proforma/shelf): {inp.get('name')!r}: {note!r}")
print(f"served panel gloss for the titre input (GET /api/params/proforma:...?flowsheet=ethanol_glucose_v0): {gloss!r}")

behaviour = (run.get("status") == "done" and abs(beer - titre) / titre > 0.01 and math.isclose(batch, titre / prod)
             and titre > feed * yld and price is not None and math.isfinite(float(price)))
said = "the beer's own ethanol follows from the feed's glucose and the yield" in note and "reads it back" in note
shown = "the beer's own ethanol follows from the feed's glucose and the yield" in gloss
read_back = "beerEthanolGPerL" in rb and "batchTimeH" in rb

print("EXPECTED: (candidate) beer at the titre the run names, or a refusal in words when feed x yield cannot make it;"
      " (the input's served description) the titre sets the batch time with the productivity, the beer's ethanol"
      " follows from the feed's glucose and the yield, and the run reads the beer back")
print(f"OBSERVED: beer {beer:.2f} g L-1 under a titre of {titre:g}, batch time {batch:g} h = titre / productivity, priced"
      f" at {float(price):.4f} USD/kg with no refusal (behaviour as the candidate says: {behaviour}); the served shelf"
      f" note says so (beer follows from feed and yield, read back: {said}); the panel shows it as the input's gloss"
      f" ({shown}); the run reads back beer and batch time ({read_back})")
if behaviour and not (said and read_back):
    print("RESULT: DEFECT")
else:
    print("verdict: the run does what the titre input's declared note says it does (batch time from titre and"
          " productivity; beer from feed and yield, read back), so the candidate's contract is the input's label alone")
    print("RESULT: NO-DEFECT")
