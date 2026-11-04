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
LIVE = {"id": "lc-1", "title": "What limits the titre?", "startedAt": "2026-10-30T07:00:00Z",
        "turns": [{"id": "t-1", "question": "What limits the titre?", "askedAt": "2026-10-30T07:00:00Z", "steps": [],
                   "plan": None, "error": None, "status": "answered"}]}
# As Postdoc keeps it (postdoc/conversations.py): the page's turn, with who asked and what it produced.
KEPT = {**LIVE, "turns": [{**LIVE["turns"][0], "by": None, "artifactIds": []}]}


def test_a_new_project_keeps_nothing_and_says_so_by_kind():
    kept = project_state.load()
    assert kept == {"depositions": [], "measuredEvidence": [], "runbooks": [], "fits": {}, "scenarios": [],
                    "trains": {}, "conversations": [], "runbookLocks": {}, "overrides": {}, "depositedBy": {}}


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
    assert kept["conversations"] == [KEPT]
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
        ("conversations", "lc-1", {"id": "lc-1", "turns": "every word"}, "is a Live conversation"),
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
    for kind, item_id in (("runbookLocks", "rb-1"), ("depositions", "dep-1"), ("measuredEvidence", "me-1"),
                          ("conversations", "lc-1")):
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


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "1" + "0" * 400])
def test_a_row_holding_a_number_json_cannot_carry_is_refused_in_words(number):
    """Alpha 2.2 D.0: a page's row holding NaN, an infinity or a number past
    a float's range (each of which Python reads from a JSON body) is a 422 in
    words naming where it stands, and nothing is kept."""
    body = '{"by": "Ada Moreno", "value": {"id": "s-nan", "values": [{"key": "a-placeholder", "value": %s}]}}' % number
    r = client().put("/api/state/scenarios/s-nan", content=body, headers={"content-type": "application/json"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == ("this scenarios row holds a number that is NaN, infinite or past a float's range at "
                                  "values[0].value; a row keeps finite numbers alone, so nothing was kept")
    assert project_state.load()["scenarios"] == [] and audit.read() == []


# ── a deposition is the bench's record: appended, never rewritten ──────

# A deposition as the bench keeps it (src/store.ts), with placeholder readings: one read back, one waiting.
BENCH = {"id": "dep-b", "runbookId": "rb-1", "protocolId": None, "operatorId": None, "state": "running",
         "startedAt": "2026-11-03T08:00:00Z", "closedAt": None, "reconciliation": None, "sampleTimes": {},
         "observations": [{"id": "ob-1", "stepId": "s-1", "at": "2026-11-03T08:05:00Z", "raw": "a placeholder note",
                           "structured": None}],
         "entries": [{"id": "de-1", "measureId": "m-1", "stepId": "s-1", "at": "2026-11-03T08:10:00Z", "value": 3.0,
                      "unit": "placeholder-unit", "raw": "a placeholder reading", "confirmed": True},
                     {"id": "de-2", "measureId": "m-1", "stepId": "s-1", "at": "2026-11-03T08:20:00Z", "value": 4.0,
                      "unit": "placeholder-unit", "raw": "another placeholder reading", "confirmed": False}]}


def _entries(body: dict, n: int, **change) -> list[dict]:
    """`body`'s readings with reading `n` changed."""
    return [{**e, **change} if i == n else e for i, e in enumerate(body["entries"])]


def _closed(body: dict = BENCH) -> dict:
    return {**body, "state": "closed", "closedAt": "2026-11-03T09:00:00Z"}


def test_the_benchs_own_writes_to_a_deposition_are_kept():
    """Every write the bench makes (src/store.ts: capture, read back, correct, attach a series, give a sample
    time, structure an observation, name a series' role, close, reconcile) stands over the row before it."""
    put = lambda body: project_state.put("depositions", "dep-b", body, "Ada Moreno")  # noqa: E731
    put({**BENCH, "state": "staged", "entries": [], "observations": []})
    put(BENCH)
    confirmed = {**BENCH, "entries": _entries(BENCH, 1, confirmed=True)}
    put(confirmed)
    # A correction is a new reading on the same measure, keeping the time the reading was taken.
    corrected = {**confirmed, "entries": [*confirmed["entries"], {
        **confirmed["entries"][1], "id": "de-3", "value": 4.5, "raw": "another placeholder reading -> corrected",
        "correctedAt": "2026-11-03T08:30:00Z"}]}
    put(corrected)
    series = {**corrected, "sampleTimes": {"de-3": 1}, "entries": [*corrected["entries"], {
        "id": "de-4", "measureId": "m-1", "stepId": "attached", "at": "2026-11-03T08:40:00Z", "value": 5.0,
        "unit": "placeholder-unit", "raw": "2, m-1, 5, placeholder-unit", "confirmed": False}]}
    put({**series, "sampleTimes": {"de-3": 1, "de-4": 2}})
    structured = {**series, "sampleTimes": {"de-3": 1, "de-4": 2}, "observations": [
        {**series["observations"][0], "structured": "a placeholder structure"}], "seriesRoles": {"m-1": "product"}}
    put(structured)
    closed = _closed(structured)
    put(closed)
    # Once closed: a series' role, an observation's structure and the reconciliation, each audited.
    put({**closed, "seriesRoles": {"m-1": "biomass"}})
    put({**closed, "seriesRoles": {"m-1": "biomass"}, "reconciliation": {"at": "2026-11-03T09:10:00Z",
                                                                         "outcome": "inconclusive", "deltas": [],
                                                                         "note": ""}})
    kept = project_state.load()["depositions"]
    assert [e["id"] for e in kept[0]["entries"]] == ["de-1", "de-2", "de-3", "de-4"]
    assert kept[0]["reconciliation"]["outcome"] == "inconclusive"
    assert [(a.action, a.target) for a in audit.read()] == [
        ("keep_depositions", "dep-b"), ("amend_depositions", "dep-b"), ("amend_depositions", "dep-b")]


@pytest.mark.parametrize(("change", "words"), [
    (lambda b: {**b, "entries": b["entries"][1:]}, "keeps every reading it was given, and this write leaves out de-1"),
    (lambda b: {**b, "entries": []}, "leaves out de-1, de-2"),
    (lambda b: {**b, "entries": b["entries"][::-1]}, "keeps its readings in the order they were taken"),
    (lambda b: {**b, "entries": _entries(b, 0, value=4.0)},
     "reading de-1 keeps the value it was taken with \\(3.0\\), and this write sets 4.0"),
    (lambda b: {**b, "entries": _entries(b, 0, unit="another-unit")}, "reading de-1 keeps the unit"),
    (lambda b: {**b, "entries": _entries(b, 0, at="2026-11-03T11:30:00Z")}, "reading de-1 keeps the at"),
    (lambda b: {**b, "entries": _entries(b, 0, measureId="m-2")}, "reading de-1 keeps the measureId"),
    (lambda b: {**b, "entries": _entries(b, 0, raw="other words")}, "reading de-1 keeps the raw"),
    (lambda b: {**b, "entries": _entries(b, 0, confirmed=False)},
     "reading de-1 was read back and confirmed, and a confirmation stays"),
    (lambda b: {**b, "observations": []}, "keeps every observation it was given, and this write leaves out ob-1"),
    (lambda b: {**b, "observations": [{**b["observations"][0], "raw": "other words"}]}, "observation ob-1 keeps the raw"),
    (lambda b: {**b, "state": "staged"}, "dep-b is running, and a deposition moves from staged to running to closed"),
    (lambda b: {**b, "runbookId": "rb-2"}, "dep-b keeps the runbookId it was made with"),
])
def test_a_write_that_rewrites_a_kept_deposition_is_refused_in_words(change, words):
    project_state.put("depositions", "dep-b", BENCH, "Ada Moreno")
    with pytest.raises(project_state.StateRefused, match=words):
        project_state.put("depositions", "dep-b", change(BENCH), "Grace Hopper")
    assert project_state.load()["depositions"] == [BENCH]


@pytest.mark.parametrize(("change", "words"), [
    (lambda b: {**b, "state": "running", "closedAt": None}, "dep-b is closed, and a deposition moves from staged"),
    (lambda b: {**b, "closedAt": "2026-11-03T12:00:00Z"}, "was closed at 2026-11-03T09:00:00Z, and a close stays"),
    (lambda b: {**b, "entries": [*b["entries"], {**b["entries"][0], "id": "de-9"}]},
     "dep-b is closed, and closing stops new readings and observations"),
    (lambda b: {**b, "observations": [*b["observations"], {**b["observations"][0], "id": "ob-9"}]},
     "closing stops new readings and observations"),
    (lambda b: {**b, "sampleTimes": {"de-1": 1}}, "dep-b is closed, and its readings keep the sample times"),
    (lambda b: {**b, "operatorId": "p-1"}, "dep-b is closed, and it keeps the operator it closed with"),
    (lambda b: {**b, "entries": _entries(b, 1, value=9.0)}, "reading de-2 keeps the value"),
])
def test_a_closed_deposition_takes_no_new_reading_and_keeps_what_it_closed_with(change, words):
    project_state.put("depositions", "dep-b", BENCH, "Ada Moreno")
    project_state.put("depositions", "dep-b", _closed(), "Ada Moreno")
    with pytest.raises(project_state.StateRefused, match=words):
        project_state.put("depositions", "dep-b", change(_closed()), "Grace Hopper")
    assert project_state.load()["depositions"] == [_closed()]


def test_a_reconciliation_stays_as_it_was_made():
    reconciled = {**_closed(), "reconciliation": {"at": "2026-11-03T09:10:00Z", "outcome": "confirmed", "deltas": [],
                                                  "note": ""}}
    project_state.put("depositions", "dep-b", reconciled, "Ada Moreno")
    with pytest.raises(project_state.StateRefused, match="dep-b was reconciled, and a reconciliation stays"):
        project_state.put("depositions", "dep-b", {**reconciled, "reconciliation": {
            **reconciled["reconciliation"], "outcome": "refuted"}}, "Ada Moreno")


def test_the_route_refuses_a_closed_depositions_rewrite_by_another_person_and_its_readings_stand():
    c = client()
    assert c.put("/api/state/depositions/dep-b", json={"by": "Ada Moreno", "value": _closed()}).status_code == 200
    rewritten = {**_closed(), "entries": _entries(_closed(), 1, confirmed=True, value=4.5)}
    r = c.put("/api/state/depositions/dep-b", json={"by": "Grace Hopper", "value": rewritten})
    assert r.status_code == 422 and "reading de-2 keeps the value it was taken with" in r.json()["detail"]
    emptied = c.put("/api/state/depositions/dep-b", json={"by": "Grace Hopper", "value": {**_closed(), "entries": []}})
    assert emptied.status_code == 422 and "leaves out de-1, de-2" in emptied.json()["detail"]
    held = c.get("/api/state").json()
    assert held["depositions"] == [_closed()] and held["depositedBy"] == {"dep-b": "Ada Moreno"}
