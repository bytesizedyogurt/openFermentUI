"""The counting rules must run where Inspect does not.

`inspect-ai` is an optional dependency of this package and the split between
`metrics.py` and `scorer.py` only means something if it is enforced. This test
enforces it: a child interpreter with `inspect_ai` blocked at the import system
imports `openferment_assay`, computes a fixture case, and must get the captured
answer. It fails if anything in the metrics chain ever grows an Inspect import
— including an eager re-export from `__init__.py`, which is the easy way to
break this by accident.

The block is a `sys.meta_path` finder rather than an uninstall, so the test
tells the truth in this environment (where Inspect IS installed) and in one
where it is not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ASSAY = Path(__file__).resolve().parents[1]
CORE = ASSAY.parent / "core"
FIXTURES = ASSAY.parents[1] / "fixtures" / "metrics.json"

CHILD = """
import json, sys


class BlockInspect:
    def find_spec(self, name, path=None, target=None):
        if name == "inspect_ai" or name.startswith("inspect_ai."):
            raise ImportError("inspect_ai is not installed in this environment")
        return None


sys.meta_path.insert(0, BlockInspect())

import openferment_assay
from openferment_core.schema import ExtractionRecord, RunOutput

data = json.loads(open(sys.argv[1], encoding="utf-8").read())
records = [ExtractionRecord.model_validate(r) for r in data["inputs"]["syntheticGold"]]
case = data["computeRunMetrics"][0]
run = next(r for r in data["inputs"]["runs"] if r["run"] == case["extractorRun"])
out = openferment_assay.compute_run_metrics(RunOutput.model_validate(run), records)
assert "inspect_ai" not in sys.modules, "something imported inspect_ai"
print(json.dumps(out.model_dump(by_alias=True, mode="json")))
"""


def test_metrics_run_without_inspect_ai() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", CHILD, str(FIXTURES)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": f"{ASSAY}:{CORE}", "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    expected = json.loads(FIXTURES.read_text("utf-8"))["computeRunMetrics"][0]["out"]
    assert json.loads(proc.stdout) == expected


def test_the_blocker_actually_blocks() -> None:
    """A negative control. If the import block quietly stopped working, the test
    above would keep passing while proving nothing."""
    proc = subprocess.run(
        [sys.executable, "-c", CHILD.replace("import openferment_assay", "import inspect_ai")],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": f"{ASSAY}:{CORE}", "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert proc.returncode != 0
    assert "inspect_ai is not installed in this environment" in proc.stderr
