"""What the nightly job checks after intake (OF-BLD-014 §10.2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from openferment_core import artifacts, intake, nightly_checks
from openferment_core.models import BasisInput, BasisSource

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(nightly_checks, "load_registrars", lambda: None)
    return tmp_path


def _keep(tool, version, value):
    state = {"value": value}
    artifacts.register(tool, version, lambda inputs, seed: {"v": state["value"]})
    art = artifacts.compute(tool, [BasisInput(name="x", value="a", unit="", source=BasisSource(kind="convention"))])
    return art, state


def test_an_identical_replay_passes_and_a_different_one_is_a_problem(store):
    art, state = _keep("nightly_probe", "1", 1.0)
    assert nightly_checks.replay_newest() == []
    state["value"] = 2.0
    problems = nightly_checks.replay_newest()
    assert len(problems) == 1 and art.id in problems[0] and "replays differently" in problems[0]


def test_an_artifact_an_earlier_version_made_is_stale_and_no_problem(store, capsys):
    art, _ = _keep("nightly_probe_v", "1", 1.0)
    artifacts.register("nightly_probe_v", "2", lambda inputs, seed: {"v": 9.0})
    assert nightly_checks.replay_newest() == []
    assert f"artifact {art.id} (nightly_probe_v): stale, made by 1; the tool is now 2" in capsys.readouterr().out


def test_a_tool_this_process_does_not_know_is_a_problem(store):
    art, _ = _keep("nightly_probe_gone", "1", 1.0)
    artifacts._REGISTRY.pop("nightly_probe_gone")
    problems = nightly_checks.replay_newest()
    assert len(problems) == 1 and art.id in problems[0] and "could not be replayed" in problems[0]


def test_the_nightly_job_checks_after_extraction():
    sh = (REPO / "scripts" / "host" / "nightly.sh").read_text()
    intake_at = sh.index("openferment_core.extract --all")
    assert sh.index("openferment_core.nightly_checks") > intake_at, "the checks run after extraction"
