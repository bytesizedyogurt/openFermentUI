"""BioRepo keeps what was computed, and can replay it (OF-BLD-014 §3.2, E.5).

The store is the `artifacts` table, one row per artifact and project
(ADR-001); each test's rows are rolled back when it ends.
"""
from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, projects
from openferment_core.models import BasisInput, BasisSource, ProjectCreate
from standins import plant_damaged

CALLS: list[int] = []


def _count(inputs, seed):
    CALLS.append(1)
    return {"label": "count", "value": len(inputs), "unit": "inputs", "names": [i.name for i in inputs]}


@pytest.fixture(autouse=True)
def _store():
    saved = dict(artifacts._REGISTRY)
    artifacts.register("t_count", "v1", _count)
    CALLS.clear()
    yield
    artifacts._REGISTRY.clear()
    artifacts._REGISTRY.update(saved)


def _in(name: str, kind: str = "convention", id: str | None = None) -> BasisInput:
    return BasisInput(name=name, value=name, unit="", source=BasisSource(kind=kind, id=id, note="a convention"))


def _kept() -> list[str]:
    """The ids the current project's store holds."""
    return sorted(a.id for a in artifacts.all_artifacts())


def test_same_inputs_give_the_same_id_and_one_row():
    a = artifacts.compute("t_count", [_in("x"), _in("y")])
    b = artifacts.compute("t_count", [_in("x"), _in("y")])
    assert a.id == b.id and len(a.id) == 16
    assert _kept() == [a.id] and artifacts.count() == 1
    assert len(CALLS) == 1, "the second call returned the stored artifact and computed nothing"
    assert b == a


def test_a_changed_input_gives_a_new_id():
    a = artifacts.compute("t_count", [_in("x")])
    b = artifacts.compute("t_count", [_in("z")])
    assert a.id != b.id
    assert len(_kept()) == 2


def test_a_changed_version_or_seed_gives_a_new_id():
    base = artifacts.artifact_id("t", "v1", [_in("x")])
    assert artifacts.artifact_id("t", "v2", [_in("x")]) != base
    assert artifacts.artifact_id("t", "v1", [_in("x")], seed=7) != base
    assert artifacts.artifact_id("t", "v1", [_in("x")], seed=None) == base


def test_the_artifact_carries_its_provenance_from_its_inputs():
    a = artifacts.compute("t_count", [_in("r", "record", "r-1")], records_by_id={"r-1": {"provenance": "unverified"}})
    assert a.provenance == "unverified"
    b = artifacts.compute("t_count", [_in("m", "model", "iJO1366")])
    assert b.provenance == "computed"
    c = artifacts.compute("t_count", [_in("a", "artifact", b.id)])
    assert c.provenance == "computed"
    d = artifacts.compute("t_count", [_in("guess", "assumption")])
    assert d.provenance == "demo"


def test_keep_false_writes_nothing():
    a = artifacts.compute("t_count", [_in("x")], keep=False)
    assert a.id and _kept() == []


def test_replay_of_an_unchanged_tool_says_identical():
    a = artifacts.compute("t_count", [_in("x"), _in("y")])
    r = artifacts.replay(a.id)
    assert r.identical and r.differences == [] and r.storedHash == r.replayedHash == a.outputHash


def test_replay_after_the_function_changes_says_what_differs():
    a = artifacts.compute("t_count", [_in("x"), _in("y")])
    stored = artifacts.get(a.id)

    def changed(inputs, seed):
        return {"label": "count", "value": len(inputs) + 1, "unit": "inputs", "names": [i.name for i in inputs]}

    artifacts.register("t_count", "v1", changed)
    r = artifacts.replay(a.id)
    assert not r.identical
    assert [(d.path, d.stored, d.replayed) for d in r.differences] == [("value", 2, 3)]
    # A replay never rewrites what was stored.
    assert artifacts.get(a.id) == stored


def test_replay_names_a_changed_version():
    a = artifacts.compute("t_count", [_in("x")])
    artifacts.register("t_count", "v2", lambda inputs, seed: {"value": "other"})
    r = artifacts.replay(a.id)
    assert not r.identical
    assert r.differences[0].path == "toolVersion"
    assert (r.differences[0].stored, r.differences[0].replayed) == ("v1", "v2")


def test_replay_of_an_unregistered_tool_is_refused():
    a = artifacts.compute("t_count", [_in("x")])
    artifacts._REGISTRY.pop("t_count")
    with pytest.raises(artifacts.ToolNotRegistered):
        artifacts.replay(a.id)


def test_a_concurrent_double_write_leaves_one_valid_row():
    """Eight threads compute the same thing at once; the first to keep it
    wins and every one returns its row. (Each thread finds the test project
    through OPENFERMENT_PROJECT, as a command does.)"""
    barrier = threading.Barrier(8)
    results = []

    def slow(inputs, seed):
        return {"value": len(inputs)}

    artifacts.register("t_slow", "v1", slow)

    def go():
        barrier.wait()
        results.append(artifacts.compute("t_slow", [_in("x")]))

    threads = [threading.Thread(target=go) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({r.id for r in results}) == 1
    assert _kept() == [results[0].id]
    assert artifacts.get(results[0].id) == results[0]
    assert len({r.createdAt for r in results}) == 1, "every caller got the one stored artifact"


def test_an_id_that_is_not_hex_names_no_artifact():
    for bad in ("../../x", "ABCDEF0123456789", "0123", "0123456789abcdef.json"):
        with pytest.raises(artifacts.ArtifactNotFound):
            artifacts.get(bad)


def test_a_tool_must_return_json():
    artifacts.register("t_bad", "v1", lambda inputs, seed: {"value": float("nan")})
    with pytest.raises(ValueError):
        artifacts.compute("t_bad", [_in("x")])


def test_all_artifacts_skips_a_damaged_row_and_lists_newest_first():
    a = artifacts.compute("t_count", [_in("x")])
    plant_damaged("0" * 16)
    assert [x.id for x in artifacts.all_artifacts()] == [a.id]


def test_a_damaged_row_is_refused_in_words_naming_it():
    plant_damaged("0" * 16)
    with pytest.raises(artifacts.ArtifactDamaged, match=f"artifact {'0' * 16} is damaged on disk"):
        artifacts.get("0" * 16)


def test_an_artifact_is_kept_in_its_project_and_read_in_no_other():
    other = projects.create(ProjectCreate(name="Other project", by="Ada Moreno"))
    with projects.using(other.id):
        theirs = artifacts.compute("t_count", [_in("x")])
        assert [a.id for a in artifacts.all_artifacts()] == [theirs.id]
    assert _kept() == []
    with pytest.raises(artifacts.ArtifactNotFound):
        artifacts.get(theirs.id)
    # The same computation here is the same id, kept again in this project.
    mine = artifacts.compute("t_count", [_in("x")])
    assert mine.id == theirs.id and _kept() == [mine.id] and artifacts.count() == 2


# ── the endpoints ─────────────────────────────────────────────────────


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_the_endpoints_list_read_and_replay(client):
    a = artifacts.compute("t_count", [_in("x")])
    assert [x["id"] for x in client.get("/api/biorepo/artifacts").json()] == [a.id]
    assert client.get(f"/api/biorepo/artifacts/{a.id}").json()["outputHash"] == a.outputHash
    r = client.post(f"/api/biorepo/artifacts/{a.id}/replay")
    assert r.status_code == 200 and r.json()["identical"] is True


def test_the_endpoints_answer_404_and_409(client):
    assert client.get("/api/biorepo/artifacts/0123456789abcdef").status_code == 404
    assert client.post("/api/biorepo/artifacts/0123456789abcdef/replay").status_code == 404
    a = artifacts.compute("t_count", [_in("x")])
    artifacts._REGISTRY.pop("t_count")
    assert client.post(f"/api/biorepo/artifacts/{a.id}/replay").status_code == 409


def test_replay_is_a_change_the_request_guard_covers(client):
    a = artifacts.compute("t_count", [_in("x")])
    r = client.post(f"/api/biorepo/artifacts/{a.id}/replay", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
