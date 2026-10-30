"""What a project keeps of its pages (project_state.py): each kind on its
table under the project, loaded whole, written one row at a time, refused in
words when it is not a row of its kind, and taken back only where a person
may take it back."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, audit, project_state, projects
from openferment_core.models import ProjectCreate


def client() -> TestClient:
    return TestClient(api.app, base_url="http://127.0.0.1")


DEPOSITION = {"id": "dep-1", "runbookId": "rb-1", "entries": [{"step": "s1", "value": 7.2}]}
TRAIN = {"train": {"id": "tr-1", "units": []}, "savedAt": "2026-10-30T07:00:00Z", "by": "Ada Moreno"}
LIVE = {"id": "lc-1", "turns": [{"question": "What limits the titre?", "status": "done"}]}


def test_a_new_project_keeps_nothing_and_says_so_by_kind():
    kept = project_state.load()
    assert kept == {"depositions": [], "measuredEvidence": [], "runbooks": [], "fits": {}, "scenarios": [],
                    "trains": {}, "conversations": [], "runbookLocks": {}, "overrides": {}}


def test_each_kind_comes_back_as_the_page_keeps_it():
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    project_state.put("trains", "tr-1", TRAIN, "Ada Moreno")
    project_state.put("conversations", "lc-1", LIVE, "Ada Moreno")
    project_state.put("fits", "sc-1", {"mu_max": "0123456789abcdef"}, "Ada Moreno")
    project_state.put("runbookLocks", "rb-1", {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}, "Ada Moreno")
    project_state.put("overrides", "proforma:sc-1", [{"scope": "proforma:sc-1", "key": "price", "value": 1.2, "by": "Ada Moreno"}], "Ada Moreno")
    kept = project_state.load()
    assert kept["depositions"] == [DEPOSITION]
    assert kept["trains"] == {"tr-1": TRAIN}
    assert kept["conversations"] == [LIVE]
    assert kept["fits"] == {"sc-1": {"mu_max": "0123456789abcdef"}}
    assert kept["runbookLocks"] == {"rb-1": {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}}
    assert kept["overrides"] == {"proforma:sc-1": [{"scope": "proforma:sc-1", "key": "price", "value": 1.2, "by": "Ada Moreno"}]}


def test_a_row_written_again_is_the_same_row_moved_and_audited_once():
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    moved = {**DEPOSITION, "entries": [*DEPOSITION["entries"], {"step": "s2", "value": 7.4}]}
    project_state.put("depositions", "dep-1", moved, "Ada Moreno")
    assert project_state.load()["depositions"] == [moved]
    assert [(a.action, a.target) for a in audit.read()] == [("keep_depositions", "dep-1")]


def test_the_overrides_of_a_scope_are_replaced_whole():
    scope = "fermos:family:monod"
    project_state.put("overrides", scope, [{"scope": scope, "key": "mu_max", "value": 0.3}, {"scope": scope, "key": "Ks", "value": 0.1}], "Ada Moreno")
    project_state.put("overrides", scope, [{"scope": scope, "key": "Ks", "value": 0.2}], "Ada Moreno")
    assert project_state.load()["overrides"] == {scope: [{"scope": scope, "key": "Ks", "value": 0.2}]}


def test_a_projects_rows_are_its_own():
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    other = projects.create(ProjectCreate(name="Other", by="Ada Moreno"))
    with projects.using(other.id):
        assert project_state.load()["depositions"] == []


@pytest.mark.parametrize(
    ("kind", "item_id", "value", "words"),
    [
        ("secrets", "x", {}, "not something a project keeps"),
        ("depositions", "has space", {"id": "has space"}, "is not an id"),
        ("depositions", "dep-1", {"id": "dep-2"}, "says it is 'dep-2'"),
        ("depositions", "dep-1", ["not", "an", "object"], "is an object"),
        ("trains", "tr-1", {"train": {"id": "tr-9"}}, "says it is 'tr-9'"),
        ("fits", "sc-1", {"mu_max": 3}, "map each input to an artifact id"),
        ("runbookLocks", "rb-1", {"lockedAt": "yesterday", "lockHash": "abc"}, "is not a time"),
        ("runbookLocks", "rb-1", {"lockHash": "abc"}, "names when it was made"),
        ("overrides", "proforma:sc-1", [{"scope": "proforma:sc-2", "key": "price"}], "naming this scope"),
        ("depositions", "dep-1", {"id": "dep-1", "blob": "x" * 2_000_001}, "over 2 MB"),
    ],
)
def test_what_is_not_a_row_of_its_kind_is_refused_in_words(kind, item_id, value, words):
    with pytest.raises(project_state.StateRefused, match=words):
        project_state.put(kind, item_id, value, "Ada Moreno")
    assert all(not v for v in project_state.load().values())


def test_a_lock_is_kept_as_made_and_a_deposition_is_never_taken_back():
    lock = {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}
    project_state.put("runbookLocks", "rb-1", lock, "Ada Moreno")
    with pytest.raises(project_state.StateRefused, match="locked already"):
        project_state.put("runbookLocks", "rb-1", {**lock, "lockHash": "other"}, "Ada Moreno")
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    for kind, item_id in (("runbookLocks", "rb-1"), ("depositions", "dep-1"), ("measuredEvidence", "me-1")):
        with pytest.raises(project_state.StateRefused, match="never taken back"):
            project_state.remove(kind, item_id, "Ada Moreno")
    assert project_state.load()["runbookLocks"] == {"rb-1": lock}


def test_what_a_person_may_take_back_goes_and_the_taking_is_audited():
    project_state.put("trains", "tr-1", TRAIN, "Ada Moreno")
    project_state.remove("trains", "tr-1", "Ada Moreno")
    project_state.remove("trains", "tr-1", "Ada Moreno")  # nothing held: nothing done
    assert project_state.load()["trains"] == {}
    assert [(a.action, a.who) for a in audit.read()] == [("keep_trains", "Ada Moreno"), ("remove_trains", "Ada Moreno")]


def test_the_routes_load_write_refuse_and_take_back():
    c = client()
    r = c.put("/api/state/trains/tr-1", json={"by": "Ada Moreno", "value": TRAIN})
    assert r.status_code == 200 and r.json()["value"] == TRAIN
    assert c.get("/api/state").json()["trains"] == {"tr-1": TRAIN}
    r = c.put("/api/state/trains/tr-2", json={"by": "Ada Moreno", "value": TRAIN})
    assert r.status_code == 422 and "says it is 'tr-1'" in r.json()["detail"]
    assert c.delete("/api/state/trains/tr-1?by=Ada%20Moreno").json()["removed"] is True
    assert c.get("/api/state").json()["trains"] == {}
    # The project is the request's: none named, none kept.
    assert c.get("/api/state", headers={projects.HEADER: ""}).status_code == 422
