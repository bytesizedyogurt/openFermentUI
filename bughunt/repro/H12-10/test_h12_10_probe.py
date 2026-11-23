"""H12-10's probe, copied into the scratch worktree's core/tests and run there with the suite's own conftest.

It plants the row keep_run's docstring speaks of (engine/runs.py:435-446): a runs row held `done` with neither
its SFF record (`sff`) nor the words for why none was written (`sffRefused`), kept by a first asker with a
scenario and the first computation's diagnostics. Then a second asker keeps the same run (the same basis, so the
same id) with a scenario and diagnostics of its own. The contract: the row "is written whole again with its first
asker's `by`, `at` and scenario", and "a held row's own [diagnostics] stand when it has some". Each test prints
one PROBE line with what the row holds after the second keep, then asserts the contract.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import TEST_PROJECT
from openferment_core import artifacts, db
from openferment_core.engine import runs
from openferment_core.models import BasisInput, BasisSource, EngineRun, RunDiagnostic

TOOL = "test.h12-10"
FIRST_AT = "2026-11-01T00:00:00Z"


def _basis() -> list[BasisInput]:
    return [BasisInput(name="a-value", value=1.0, unit="placeholder-unit",
                       source=BasisSource(kind="convention", note="a placeholder"))]


@pytest.fixture
def planted(monkeypatch):
    """The held row with neither file nor words, as the first asker kept it."""
    monkeypatch.setitem(artifacts._REGISTRY, TOOL, artifacts.Registered(TOOL, "1", lambda i, seed: {"answer": 2.5}))
    engine = SimpleNamespace(name="placeholder-engine", version=lambda: {"placeholder-distribution": "0.0"})
    art = artifacts.compute(TOOL, _basis())
    row = EngineRun(id=art.id, engine="placeholder-engine", plant="a-thing", status="done", tool=TOOL,
                    toolVersion="1", inputs=runs._inputs(_basis()), provenance=art.provenance, artifactId=art.id,
                    by="First Person", at=FIRST_AT, scenarioId="first-scenario",
                    diagnostics=[RunDiagnostic(name="time taken", value=1.0, unit="placeholder-ms")])
    db.run(runs._put(TEST_PROJECT, row, "First Person"))
    held = runs.get(art.id)
    assert held.status == "done" and held.sff is None and held.sffRefused is None, "the planted row has neither"
    return engine, art


def _keep_again(engine, art):
    runs.keep_run(engine, "a-thing", None, tool=TOOL, version="1", basis=_basis(), by="Second Person", art=art,
                  sff_refused="the placeholder engine has no plant", scenario_id="second-scenario",
                  diagnostics=[{"name": "time taken", "value": 9.0, "unit": "placeholder-ms"}])
    return runs.get(art.id)


def test_a_held_row_with_neither_is_written_again_under_its_first_askers_by_at_and_scenario(planted):
    kept = _keep_again(*planted)
    print(f"\nPROBE by-at-scenario by={kept.by!r} at={kept.at!r} scenarioId={kept.scenarioId!r} "
          f"sffRefused={kept.sffRefused!r}", flush=True)
    assert kept.sffRefused == "the placeholder engine has no plant", "the row is written whole again"
    assert (kept.by, kept.at, kept.scenarioId) == ("First Person", FIRST_AT, "first-scenario")


def test_a_held_row_with_neither_keeps_its_own_diagnostics(planted):
    kept = _keep_again(*planted)
    said = [(d.name, d.value, d.unit) for d in kept.diagnostics]
    print(f"\nPROBE diagnostics {said!r} sffRefused={kept.sffRefused!r}", flush=True)
    assert kept.sffRefused == "the placeholder engine has no plant", "the row is written whole again"
    assert said == [("time taken", 1.0, "placeholder-ms")]
