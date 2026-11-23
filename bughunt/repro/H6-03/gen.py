"""gen.py MODELS_A1 OUT_DIR: two alpha 1.0 data directories written by alpha 1.0's own models
(`git show alpha-1.0:core/openferment_core/models.py`, which imports pydantic alone), in the shape
alpha 1.0's core/data/ held its extractions: candidates/<paperId>.json, one ExtractResponse a paper.

  OUT_DIR/one    candidates/P1.json alone
  OUT_DIR/dup    candidates/P1.json and "candidates/P1 copy.json", the same bytes, as a file manager's
                 duplicate names a copy
The candidate is a placeholder; no science is typed here.
"""
from __future__ import annotations

import importlib.util
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
c = m.Candidate(id="cl1-P1-0001", paperId="P1", sectionId="s1", quote="Placeholder A | 3 | mg L-1",
                field="titer_secreted", value=3, unit="mg L-1", si=m.Quantity(value=0.003, unit="g L-1"))
ext = m.ExtractResponse(paperId="P1", extractedAt="2026-10-02T00:00:00Z", candidates=[c])
for case in ("one", "dup"):
    (out / case / "candidates").mkdir(parents=True)
    (out / case / "candidates" / "P1.json").write_text(ext.model_dump_json(indent=2))
shutil.copyfile(out / "dup" / "candidates" / "P1.json", out / "dup" / "candidates" / "P1 copy.json")
print("written:", ", ".join(str(p.relative_to(out)) for p in sorted(out.rglob("*.json"))))
