"""gen.py MODELS_A1 OUT_DIR: two alpha 1.0 data directories written by alpha 1.0's own models
(`git show alpha-1.0:core/openferment_core/models.py`, which imports pydantic alone), in the shapes
alpha 1.0's core/data/ held its guild ledger (guild.json) and its artifacts (artifacts/<id>.json).

  OUT_DIR/one   guild.json naming two people (p-ada, p-ben); artifacts/<id>.json, one artifact
  OUT_DIR/dup   guild.json naming p-ben twice under one id, the second entry renamed "Ben Ortiz (again)",
                three entries in all; artifacts/<id>.json and "artifacts/<id> copy.json", the same bytes,
                as a file manager's duplicate names a copy
The people and the artifact are placeholders; no science is typed here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("models_a1", sys.argv[1])
m = importlib.util.module_from_spec(spec)
sys.modules["models_a1"] = m
spec.loader.exec_module(m)
for name in dir(m):
    obj = getattr(m, name)
    if isinstance(obj, type) and hasattr(obj, "model_rebuild"):
        try:
            obj.model_rebuild()
        except Exception:  # noqa: BLE001
            pass
out = Path(sys.argv[2])
shutil.rmtree(out, ignore_errors=True)

lead = m.GuildPerson(id="p-ada", name="Ada Moreno", role="lead", joinedAt="2026-10-01", addedAt="2026-10-01T00:00:00Z")
tech = m.GuildPerson(id="p-ben", name="Ben Ortiz", role="member", joinedAt="2026-10-02", addedAt="2026-10-02T00:00:00Z",
                     addedBy="p-ada")
guild = m.Guild(people=[lead, tech], evidence=[],
                policy=m.GuildPolicy(checksPerQuarter=2, updatedBy="p-ada", updatedAt="2026-10-01T00:00:00Z"))
held = {"note": "a placeholder"}
art = m.Artifact(id="00000000000000aa", tool="proforma.run", toolVersion="1", provenance="demo",
                 inputs=[m.BasisInput(name="price", value=0.5, unit="USD/kg",
                                      source=m.BasisSource(kind="assumption", by="Ada Moreno", note="typed"))],
                 output=held, createdAt="2026-10-07T00:00:00Z", durationMs=1,
                 outputHash=hashlib.sha256(json.dumps(held, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16])

for case in ("one", "dup"):
    (out / case / "artifacts").mkdir(parents=True)
    (out / case / "artifacts" / f"{art.id}.json").write_text(art.model_dump_json(indent=2))
    (out / case / "guild.json").write_text(guild.model_dump_json(indent=2))
g = json.loads(guild.model_dump_json())
g["people"].append({**g["people"][1], "name": "Ben Ortiz (again)"})
(out / "dup" / "guild.json").write_text(json.dumps(g, indent=2))
shutil.copyfile(out / "dup" / "artifacts" / f"{art.id}.json", out / "dup" / "artifacts" / f"{art.id} copy.json")
for case in ("one", "dup"):
    gj = json.loads((out / case / "guild.json").read_text())
    files = sorted(p.name for p in (out / case / "artifacts").glob("*.json"))
    print(f"{case}: guild.json people {[(p['id'], p['name']) for p in gj['people']]}; artifacts/ {files}")
