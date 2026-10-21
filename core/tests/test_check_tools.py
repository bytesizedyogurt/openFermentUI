"""`pnpm check:tools` rule 2b and rule 6 (E.4‴), negative-tested (OF-BLD-019
§6.R, review finding 17; OF-BLD-020 §3.4).

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
    # OF-BLD-020 §3.4: a simulation, a vessel and a train are kept runs too.
    # fermos.simulate itself, past writes.run_simulation.
    "plant_simulate.py": "from .. import fermos\n\n\ndef f(req):\n    return fermos.simulate(req)\n",
    # The artifact store asked for a simulation by the module's own constant.
    "plant_compute_simulation.py": "from .. import artifacts, fermos\n\n\ndef f():\n    return artifacts.compute(fermos.SIMULATION, [])\n",
    # A vessel design, reached through the function that keeps one.
    "plant_vessel.py": "from .. import vessel\n\n\ndef f(req):\n    return vessel.design(req)\n",
    # A vessel and a train, the tool spelled out and the store's function aliased.
    "plant_compute_vessel.py": 'from ..artifacts import compute as keep\n\n\ndef f():\n    return keep("fermos.vessel", [])\n',
    "plant_compute_train.py": 'from .. import artifacts\n\n\ndef f():\n    return artifacts.compute("pureos.train_run", [])\n',
    # OF-BLD-020 §3.R (finding 21): a module from the interpreter's table, and
    # a module's names read as a dictionary, past every import.
    "plant_sysmodules.py": 'import sys\n\n\ndef f(req):\n    return sys.modules["openferment_core.fermos"].simulate(req)\n',
    "plant_vars.py": 'from .. import api\n\n\ndef f():\n    return vars(api)["artifacts"].compute("fermos.simulation", [])\n',
    "plant_globals.py": 'from .. import fermos\n\n\ndef f(req):\n    return globals()["fermos"].__dict__["simulate"](req)\n',
    # OF-BLD-020 §5.4: the store of the trains a model built, and a train's run.
    # The one write to the store, past writes.py's train functions.
    "plant_keep_train.py": 'from ..pureos.kept import keep_train\n\n\ndef f(spec):\n    return keep_train(None, lambda _: spec, "m")\n',
    # The same, the store module aliased.
    "plant_kept_alias.py": 'from ..pureos import kept as k\n\n\ndef f(spec):\n    return k.keep_train(None, lambda _: spec, "m")\n',
    # The store's private writer, which keep_train calls.
    "plant_kept_persist.py": "from ..pureos import kept\n\n\ndef f(store):\n    return kept._persist(store)\n",
    # A train's run, through the package's re-export.
    "plant_run_train.py": "from .. import pureos\n\n\ndef f(spec):\n    return pureos.run_train(spec)\n",
    # A function outside tools/ that keeps a model's train.
    "plant_train_wrapper.py": "from .. import plant_train_keeper\n\n\ndef f(spec):\n    return plant_train_keeper.keep(spec)\n",
    # A second writer of the same store, found by the file it names.
    "plant_store_wrapper.py": "from .. import plant_store\n\n\ndef f(text):\n    return plant_store.save(text)\n",
}
# The function the last planted tool file reaches, outside tools/.
KEEPER = "from . import proforma\n\n\ndef keep(req):\n    return proforma.run(req)\n"
# OF-BLD-020 §5.4: what the train wrappers reach, outside tools/.
TRAIN_KEEPER = 'from .pureos import kept\n\n\ndef keep(spec):\n    return kept.keep_train(None, lambda _: spec, "m")\n'
STORE = ('from . import atomic, intake\n\nFILE = "pureos-trains.json"\n\n\ndef save(text):\n'
         '    atomic.write_text(intake.DATA_DIR / FILE, text)\n')


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
    (package / "plant_train_keeper.py").write_text(TRAIN_KEEPER, encoding="utf-8")
    (package / "plant_store.py").write_text(STORE, encoding="utf-8")
    out = _check(root)
    assert out.returncode == 1, out.stdout + out.stderr
    errors = [line.strip()[2:] for line in out.stdout.splitlines() if line.strip().startswith("- ")]
    for name in PLANTED:
        assert any(e.startswith(f"tools/{name} ") for e in errors), (name, out.stdout)
    # Nothing but the planted files is named: the copy itself passes every rule.
    assert all(any(e.startswith(f"tools/{name} ") for name in PLANTED) for e in errors), out.stdout
    assert any("plant_keeper.keep" in e for e in errors if e.startswith("tools/plant_wrapper.py ")), out.stdout
    assert any("plant_train_keeper.keep" in e for e in errors if e.startswith("tools/plant_train_wrapper.py ")), out.stdout
    assert any("plant_store.save" in e for e in errors if e.startswith("tools/plant_store_wrapper.py ")), out.stdout
    assert any("pureos.kept._persist" in e for e in errors if e.startswith("tools/plant_kept_persist.py ")), out.stdout


def test_the_copy_the_negative_test_plants_in_passes_as_the_tree_does(tmp_path):
    out = _check(_copy(tmp_path))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.startswith("✓ check:tools")


# Rule 6 (E.4‴): a number field planted in fermos_simulate's input, at the
# top and nested; each must be named, and nothing else.
SIM_CLASS = 'class FermosSimulateInput(BaseModel):\n    model_config = ConfigDict(extra="forbid")\n'
PLANTED_FIELDS = ('    hours: float = Field(0.0, description="a STAND-IN numeric field, planted")\n'
                  '    byKey: dict[str, list[int]] = Field(default_factory=dict, description="a STAND-IN, planted")\n'
                  '    limit: dict[str, int] = Field(default_factory=dict, description="a count name, planted nested")\n')


def test_rule_6_names_a_numeric_field_in_a_fermos_tools_input_and_lets_the_top_level_counts_stand(tmp_path):
    root = _copy(tmp_path)
    source = root / "core" / "openferment_core" / "tools" / "fermos.py"
    text = source.read_text(encoding="utf-8")
    assert text.count(SIM_CLASS) == 1, "fermos_simulate's input class moved; plant the fields where it is"
    source.write_text(text.replace(SIM_CLASS, SIM_CLASS + PLANTED_FIELDS), encoding="utf-8")
    out = _check(root)
    assert out.returncode == 1, out.stdout + out.stderr
    errors = [line.strip()[2:] for line in out.stdout.splitlines() if line.strip().startswith("- ")]
    where = sorted(e.split(" at ", 1)[1].split(":", 1)[0] for e in errors)
    assert where == ["byKey.additionalProperties.items", "hours", "limit.additionalProperties"], out.stdout
    assert all(e.startswith("fermos_simulate's input schema holds a numeric field at ") and "(E.4‴)" in e
               for e in errors), out.stdout



# Rule 2 (OF-BLD-020 §5.4): writes.py names of the kept-train store its one
# write function and nothing else callable; a read planted there is named.
PLANTED_READ = "\n\ndef _planted_read():\n    from ..pureos import kept\n\n    return kept.read()\n"


def test_rule_2_names_writes_py_reaching_the_kept_train_store_past_its_write_function(tmp_path):
    root = _copy(tmp_path)
    source = root / "core" / "openferment_core" / "tools" / "writes.py"
    source.write_text(source.read_text(encoding="utf-8") + PLANTED_READ, encoding="utf-8")
    out = _check(root)
    assert out.returncode == 1, out.stdout + out.stderr
    errors = [line.strip()[2:] for line in out.stdout.splitlines() if line.strip().startswith("- ")]
    assert len(errors) == 1 and errors[0].startswith("tools/writes.py line ") and \
        "reaches pureos.kept.read (as kept.read), which is not one of the module write functions" in errors[0], out.stdout
