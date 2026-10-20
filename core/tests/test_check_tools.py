"""`pnpm check:tools` rule 2b, negative-tested (OF-BLD-019 §6.R, review finding 17).

Rule 2b holds every tool file other than `tools/writes.py` away from what
keeps a Proforma run or writes an audit line: those writes go through
writes.py, where rule 2 reads them. It caught two names, `proforma.run` and
`audit.append`; `proforma.run_flowsheet(...)`, `artifacts.compute(proforma.RUN,
…)` and `getattr(proforma, "run")` each kept a run past it.

The check runs as verify runs it, on a copy of the package with one file
planted under `tools/` per way of calling the store, and must name each
planted file and nothing else. Every planted file is a STAND-IN written here:
none is imported by the registry, and nothing in it runs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# One planted tool file per way around writes.py; each must be named.
PLANTED = {
    # The public sibling of proforma.run: it keeps a proforma.run artifact and writes no audit line.
    "plant_run_flowsheet.py": 'from .. import proforma as pf\n\n\ndef f():\n    return pf.run_flowsheet("ethanol_glucose_v0", [])\n',
    # The artifact store itself, asked for a run.
    "plant_compute.py": "from .. import artifacts, proforma\n\n\ndef f():\n    return artifacts.compute(proforma.RUN, [], records_by_id={})\n",
    # The same, the run tool's name spelled out and the store's function aliased.
    "plant_compute_alias.py": 'from ..artifacts import compute as keep\n\n\ndef f():\n    return keep("proforma.run", [])\n',
    # A store module handed to getattr.
    "plant_getattr.py": 'from .. import proforma\n\n\ndef f():\n    return getattr(proforma, "run")(None)\n',
    # A module imported by name at run time.
    "plant_importlib.py": 'import importlib\n\n\ndef f():\n    return importlib.import_module("openferment_core.proforma").run(None)\n',
    # The audit log, through an alias.
    "plant_audit.py": 'from ..audit import append as note\n\n\ndef f():\n    note(agent="model", who="m", module="proforma", action="run", state="open", target="t")\n',
    # A function outside tools/ that keeps a run, reached from a tool file:
    # what keeps a run is followed through every function that calls it.
    "plant_wrapper.py": "from .. import plant_keeper\n\n\ndef f(req):\n    return plant_keeper.keep(req)\n",
}
# The function the last planted tool file reaches, outside tools/.
KEEPER = "from . import proforma\n\n\ndef keep(req):\n    return proforma.run(req)\n"


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO / "core" / "openferment_core", root / "core" / "openferment_core",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (root / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "check-tools.py", root / "scripts" / "check-tools.py")
    (root / "docs").mkdir()
    shutil.copy(REPO / "docs" / "TOOLS.md", root / "docs" / "TOOLS.md")
    return root


def _check(root: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run([sys.executable, str(root / "scripts" / "check-tools.py")], cwd=root / "core", env=env,
                          capture_output=True, text=True, timeout=180)


def test_rule_2b_names_every_way_a_tool_file_keeps_a_run_or_writes_an_audit_line_past_writes_py(tmp_path):
    root = _copy(tmp_path)
    package = root / "core" / "openferment_core"
    for name, text in PLANTED.items():
        (package / "tools" / name).write_text(text, encoding="utf-8")
    (package / "plant_keeper.py").write_text(KEEPER, encoding="utf-8")
    out = _check(root)
    assert out.returncode == 1, out.stdout + out.stderr
    errors = [line.strip()[2:] for line in out.stdout.splitlines() if line.strip().startswith("- ")]
    for name in PLANTED:
        assert any(e.startswith(f"tools/{name} ") for e in errors), (name, out.stdout)
    # Nothing but the planted files is named: the copy itself passes every rule.
    assert all(any(e.startswith(f"tools/{name} ") for name in PLANTED) for e in errors), out.stdout
    assert any("plant_keeper.keep" in e for e in errors if e.startswith("tools/plant_wrapper.py ")), out.stdout


def test_the_copy_the_negative_test_plants_in_passes_as_the_tree_does(tmp_path):
    out = _check(_copy(tmp_path))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.startswith("✓ check:tools")
