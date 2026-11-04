"""The mirror's entry point and engine object as the service discovers them, with no database."""
import subprocess
import sys
from importlib.metadata import entry_points, metadata, version

import pytest

from openferment_core.engine import EngineRefused

DISTRIBUTION = "openferment-engine-mirror"
KEPT_OUT = ("openferment_engine_mirror.worker", "biosteam", "thermosteam", "biorefineries", "pisces_sff", "cobra")


def test_the_mirror_registers_one_object_under_the_engine_group():
    (entry,) = [e for e in entry_points(group="openferment.engines") if e.name == "mirror"]
    assert entry.value == "openferment_engine_mirror.engine:ENGINE"
    assert entry.dist is not None and entry.dist.name == DISTRIBUTION
    engine = entry.load()
    assert (engine.name, engine.worker) == ("mirror", "openferment_engine_mirror.worker")
    assert tuple(engine.distributions) == (DISTRIBUTION,) and tuple(engine.heavy) == ()


def test_importing_the_entry_module_brings_in_neither_the_worker_nor_anything_heavy(tmp_path):
    code = ("import sys\n"
            "import openferment_engine_mirror.engine\n"
            f"kept_out = {KEPT_OUT!r}\n"
            "print(sorted(m for m in sys.modules if any(m == k or m.startswith(k + '.') for k in kept_out)))\n")
    done = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"


def test_the_engine_reads_its_version_from_installed_metadata():
    from openferment_engine_mirror.engine import ENGINE
    assert ENGINE.version() == {DISTRIBUTION: version(DISTRIBUTION)}


def test_the_engine_answers_its_thing_and_parameters_through_its_worker():
    from openferment_engine_mirror.engine import ENGINE
    (thing,) = ENGINE.things()
    assert thing.id == "reflect" and list(thing.configurations) == []
    assert (thing.precision.rtol, thing.precision.atol) == (0, 0)
    parameters = ENGINE.parameters("reflect", None)
    assert [p.key for p in parameters] == ["placeholder-a", "placeholder-b"]
    assert [(p.value, p.unit) for p in parameters] == [(1.0, "placeholder-unit"), (2.0, "another-placeholder-unit")]
    ref = f"{DISTRIBUTION}@{version(DISTRIBUTION)}"
    assert all(p.origin.kind == "library-default" and p.origin.ref == ref for p in parameters)


def test_a_thing_the_mirror_does_not_run_is_refused_through_the_engine():
    from openferment_engine_mirror.engine import ENGINE
    with pytest.raises(EngineRefused, match="nothing"):
        ENGINE.parameters("nothing", None)


def test_the_package_declares_no_licence_and_no_dependency_on_the_core():
    meta = metadata(DISTRIBUTION)
    assert not [field for field in ("License", "License-Expression", "License-File") if meta.get_all(field)]
    assert not [c for c in meta.get_all("Classifier") or [] if c.startswith("License")]
    assert not [r for r in meta.get_all("Requires-Dist") or [] if r.lower().startswith(("openferment-core", "openferment_core"))]
