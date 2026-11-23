"""gen.py MODELS_A1 OUT_DIR: one alpha 1.0 data directory holding biorepo.json alone.

The file is written by alpha 1.0's own models (`git show alpha-1.0:core/openferment_core/models.py`,
which imports pydantic alone): one candidate and one verified decision with a gold value, as
gen_alpha1.py's `full` case writes it. Then the decision's gold value is given an origin of kind
`model-estimate`, as bughunt/notes/H6/scripts/gen_alpha1.py's `estimate` case does. The record is a
placeholder. Prints the decision as written, and what alpha 1.0's own ReviewDecision reads of its
gold value, one JSON object a line.
"""
from __future__ import annotations

import importlib.util
import json
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
out.mkdir(parents=True, exist_ok=True)
Q = m.Quantity
C1 = m.Candidate(id="cl1-P1-0001", paperId="P1", sectionId="s1", quote="Placeholder A | 3 | mg L-1",
                 field="titer_secreted", value=3, unit="mg L-1", si=Q(value=0.003, unit="g L-1"))
D1 = m.ReviewDecision(status="verified", provenance="curated", reviewer="Ada Moreno", recordId=C1.id,
                      at="2026-10-20T00:00:00Z", gold=Q(value=3, unit="mg L-1"))
repo = json.loads(m.BioRepo(decisions={C1.id: D1}, records=[C1]).model_dump_json())
repo["decisions"][C1.id]["gold"]["origin"] = {"kind": "model-estimate", "by": "claude-x", "at": "2026-10-20T00:00:00Z"}
(out / "biorepo.json").write_text(json.dumps(repo, indent=2))
print(json.dumps(repo["decisions"][C1.id]))
print(json.dumps({"alpha1_reads_gold_as": m.ReviewDecision.model_validate(repo["decisions"][C1.id]).gold.model_dump()}))
