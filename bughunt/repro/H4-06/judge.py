"""H4-06 judge: reads one cellulosic_ethanol_v0 library run (the route's JSON answer) and the two source lines
that name its ethanol outputs, then prints EXPECTED, OBSERVED and RESULT. Usage: judge.py RUN_JSON REPO_ROOT"""
import json
import re
import sys
from pathlib import Path

run_file, root = Path(sys.argv[1]), Path(sys.argv[2])
try:
    d = json.loads(run_file.read_text())
    o = d["artifact"]["output"]
    outs, units = o["outputs"], o.get("outputUnits") or {}
    eth = next(s for s in o["streams"] if s["id"] == "ethanol")
except Exception as e:  # noqa: BLE001
    print("EXPECTED: a cellulosic_ethanol_v0 run with outputs and an ethanol stream")
    print(f"OBSERVED: the run's answer could not be read ({type(e).__name__}: {e}); head: {run_file.read_text()[:300]!r}")
    print("RESULT: NO-DEFECT")
    sys.exit(0)

flows = eth["massFlows"]
ethanol_alone = float(flows["Ethanol"])
stream_total = float(eth["massFlow"])
dry = float(outs["dryFeedKgPerH"])
said_h, said_kg = float(outs["ethanolKgPerH"]), float(outs["ethanolKgPerKgDryFeed"])
others = {k: round(float(v), 2) for k, v in flows.items() if k != "Ethanol" and abs(float(v)) > 1e-9}

words = (root / "src/screens/ProformaComparison.tsx").read_text()
label_h = re.search(r"'outputs\.ethanolKgPerH': '([^']*)'", words)
label_kg = re.search(r"'outputs\.ethanolKgPerKgDryFeed': '([^']*)'", words)
glucose = (root / "core/openferment_core/flowsheets/ethanol_glucose_v0.py").read_text()
glucose_line = next((f"ethanol_glucose_v0.py:{i}: {ln.strip()}" for i, ln in enumerate(glucose.splitlines(), 1)
                     if '"ethanolKgPerH":' in ln and "float(" in ln), "")
cev0 = (root / "core/openferment_core/flowsheets/cellulosic_ethanol_v0.py").read_text()
cev0_lines = [f"cellulosic_ethanol_v0.py:{i}: {ln.strip()}" for i, ln in enumerate(cev0.splitlines(), 1)
              if ('"ethanolKgPerH":' in ln or '"ethanolKgPerKgDryFeed":' in ln) and "float(" in ln]

print(f"run {d['artifact']['id']}: plant {d.get('run', {}).get('plant', 'cellulosic_ethanol_v0')}, "
      f"configuration {o.get('configuration') or d.get('run', {}).get('configuration')}")
print(f"ethanol stream: massFlow {stream_total:.4f} kg/hr; Ethanol {ethanol_alone:.4f}; the rest {others}")
print(f"outputs: ethanolKgPerH {said_h:.4f} {units.get('ethanolKgPerH')}, dryFeedKgPerH {dry:.4f}, "
      f"ethanolKgPerKgDryFeed {said_kg:.6f} {units.get('ethanolKgPerKgDryFeed')}")
print(f"Comparison screen words: outputs.ethanolKgPerH -> {label_h and label_h.group(1)!r}; "
      f"outputs.ethanolKgPerKgDryFeed -> {label_kg and label_kg.group(1)!r}")
for ln in cev0_lines:
    print(ln)
print(f"the same key elsewhere, {glucose_line}")

print(f"EXPECTED: 'Ethanol made per hour' reads the ethanol in the product, {ethanol_alone:.1f} kg/hr, and "
      f"'Ethanol per kg of dry feed' {ethanol_alone / dry:.4f} kg/kg, as ethanol_glucose_v0's ethanolKgPerH reads "
      f"product.imass['Ethanol']; or the two outputs named for the denatured product stream they measure")
print(f"OBSERVED: ethanolKgPerH {said_h:.1f} kg/hr is the whole product stream ({stream_total:.1f}: Ethanol "
      f"{ethanol_alone:.1f} plus {others}), {100 * (said_h / ethanol_alone - 1):.2f} % above the ethanol; "
      f"ethanolKgPerKgDryFeed {said_kg:.4f} against {ethanol_alone / dry:.4f} kg/kg of ethanol, "
      f"{100 * (said_kg * dry / ethanol_alone - 1):.2f} % high; the screen names both 'Ethanol'")

defect = (abs(said_h - stream_total) <= 1e-6 * stream_total
          and said_h > ethanol_alone * 1.001
          and label_h is not None and label_h.group(1).lower().startswith("ethanol")
          and label_kg is not None and label_kg.group(1).lower().startswith("ethanol")
          and 'imass["Ethanol"]' in glucose_line)
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
