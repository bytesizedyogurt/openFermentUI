"""H3-13: catalogue_write, in the model's lane, keeps a paper's measured values written in words.

  bh_py bughunt/repro/H3-13/repro.py http://127.0.0.1:<port>      (run.sh starts the service)

One project, two calls at the HTTP endpoint's assistant door (X-OpenFerment-Assistant), one read back.
No model is called and nothing leaves 127.0.0.1.
"""
import json
import sys

import httpx

from openferment_core.validate import find_number

O = sys.argv[1]
P = "h3-13"
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
r = c.post("/api/projects", json={"id": P, "name": "H3-13", "by": "bughunt"})
print("project made:", r.status_code)
H = {"X-OpenFerment-Project": P, "X-OpenFerment-Assistant": "hunt-agent/0.1"}

# Control: the same door refuses a JSON number (tools.numbers_in).
control = c.post("/api/tools/catalogue_write", headers=H, json={
    "kind": "strain", "id": "hunt-agent.0.1-control", "name": "Control strain", "summary": 45})
cb = control.json()
print("control, summary sent as the JSON number 45:", control.status_code, "error:", cb.get("error"))

# The candidate: a paper's measured values written in words in name, summary and note.
ENTRY = {"kind": "strain", "id": "hunt-agent.0.1-s1", "name": "Strain making 45 g/L",
         "species": "Saccharomyces cerevisiae", "summary": "reaches a titre of 45 g/L at 30 °C in 48 h",
         "note": "read from a paper: 0.45 g/g yield"}
w = c.post("/api/tools/catalogue_write", headers=H, json=ENTRY)
wb = w.json()
print("catalogue_write, the measured values in words:", w.status_code, "error:", wb.get("error"))
print("  the service's own number finder (validate.find_number) on each word field sent:")
stating = {}
for k in ("name", "summary", "note"):
    hit = find_number(ENTRY[k])
    stating[k] = hit
    print(f"    {k}: {ENTRY[k]!r} -> {hit!r}")

g = c.get(f"/api/catalogues/strain/{ENTRY['id']}", headers={"X-OpenFerment-Project": P})
kept = g.json() if g.status_code == 200 else {}
shown = {k: kept.get(k) for k in ("id", "name", "summary", "note", "by", "agent", "via", "source")}
print("GET /api/catalogues/strain/" + ENTRY["id"] + ":", g.status_code)
print("  kept:", json.dumps(shown, ensure_ascii=False))

control_refused = bool(cb.get("error")) and "summary" in cb["error"]
kept_words = (w.status_code == 200 and not wb.get("error") and g.status_code == 200
              and kept.get("agent") == "model"
              and all(kept.get(k) == ENTRY[k] for k in ("name", "summary", "note"))
              and all(stating.values()))
print()
print("EXPECTED: catalogue_write refused in words naming the field that states a number (name, summary, note "
      "each hold one validate.find_number finds), as the same door refuses summary sent as a JSON number, and "
      "nothing kept: 'Names and words only, never a measured value: a number a paper reports is a record'")
print(f"OBSERVED: control refused={control_refused}; the words write answered {w.status_code} with error "
      f"{wb.get('error')!r}, and the catalogue holds {ENTRY['id']} in the model's lane (agent={kept.get('agent')!r}, "
      f"via={kept.get('via')!r}, by={kept.get('by')!r}) with name {kept.get('name')!r}, summary "
      f"{kept.get('summary')!r} and note {kept.get('note')!r}")
print("RESULT: DEFECT" if (kept_words and control_refused) else "RESULT: NO-DEFECT")
