"""What a project keeps of its pages (project_state.py): each kind on its
table under the project, loaded whole, written one row at a time, refused in
words when it is not a row of its kind, and taken back only where a person
may take it back. Each kind reads as its model (alpha 2.2 E.0b): a write that
does not read is refused in words, `GET /api/state` serves each row as the
page sent it, and a row kept before its kind had a model, that does not read,
is named in `refused` while the rest load."""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from openferment_core import api, audit, db, project_state, projects
from openferment_core.db import models as t
from openferment_core.db import rows
from openferment_core.models import LiveConversation, ProjectCreate, ProjectState
from openferment_core.postdoc import conversations
from openferment_core.runbook_lock import frozen_as, js_number, lock_hash

from test_runbook_lock import cases


def client() -> TestClient:
    return TestClient(api.app, base_url="http://127.0.0.1")


AT = "2026-10-30T07:00:00Z"
# A deposition as the bench keeps one (src/store.ts `openDeposition`, `captureDeposition`), its reading a placeholder.
ENTRY = {"id": "de-1", "measureId": "m-1", "stepId": "s-1", "at": AT, "value": 7.2, "unit": "placeholder-unit",
         "raw": "a placeholder reading", "confirmed": False}
DEPOSITION = {"id": "dep-1", "runbookId": "rb-1", "protocolId": None, "operatorId": None, "startedAt": AT,
              "closedAt": None, "state": "running", "entries": [ENTRY], "observations": [], "reconciliation": None}
# A train as the Builder saves one (src/store.ts `saveTrain`): the train as data, placeholders throughout.
TRAIN = {"train": {"id": "tr-1", "name": "A placeholder train", "program": "placeholder",
                   "product": "a-placeholder-product", "inlet": {"kind": "typed"}, "units": []},
         "savedAt": AT, "by": "Ada Moreno"}
LIVE = {"id": "lc-1", "title": "What limits the titre?", "startedAt": "2026-10-30T07:00:00Z",
        "turns": [{"id": "t-1", "question": "What limits the titre?", "askedAt": "2026-10-30T07:00:00Z", "steps": [],
                   "plan": None, "error": None, "status": "answered"}]}
# As Postdoc keeps it (postdoc/conversations.py): the page's turn, with who asked and what it produced.
KEPT = {**LIVE, "turns": [{**LIVE["turns"][0], "by": None, "artifactIds": []}]}
EMPTY = {"depositions": [], "measuredEvidence": [], "runbooks": [], "runbookLocks": {}, "overrides": {}, "fits": {},
         "scenarios": [], "trains": {}, "conversations": [], "depositedBy": {}, "refused": []}


def test_a_new_project_keeps_nothing_and_says_so_by_kind():
    kept = project_state.load()
    assert kept == {"depositions": [], "measuredEvidence": [], "runbooks": [], "fits": {}, "scenarios": [],
                    "trains": {}, "conversations": [], "runbookLocks": {}, "overrides": {}, "depositedBy": {}}
    assert client().get("/api/state").json() == EMPTY == project_state.state().model_dump(mode="json")


def test_each_kind_comes_back_as_the_page_keeps_it():
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    project_state.put("trains", "tr-1", TRAIN, "Ada Moreno")
    project_state.put("conversations", "lc-1", LIVE, "Ada Moreno")
    project_state.put("fits", "sc-1", {"mu_max": "0123456789abcdef"}, "Ada Moreno")
    project_state.put("runbookLocks", "rb-1", {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}, "Ada Moreno")
    price = {"scope": "proforma:sc-1", "key": "price", "value": 1.2, "by": "Ada Moreno", "at": AT}
    project_state.put("overrides", "proforma:sc-1", [price], "Ada Moreno")
    kept = project_state.load()
    assert kept["depositions"] == [DEPOSITION]
    assert kept["trains"] == {"tr-1": TRAIN}
    assert kept["conversations"] == [KEPT]
    assert kept["fits"] == {"sc-1": {"mu_max": "0123456789abcdef"}}
    assert kept["runbookLocks"] == {"rb-1": {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}}
    assert kept["overrides"] == {"proforma:sc-1": [price]}
    assert client().get("/api/state").json() == {**kept, "refused": []}


def test_a_row_written_again_is_the_same_row_moved_and_audited_once():
    project_state.put("depositions", "dep-1", DEPOSITION, "Ada Moreno")
    moved = {**DEPOSITION, "entries": [*DEPOSITION["entries"], {**ENTRY, "id": "de-2", "stepId": "s-2", "value": 7.4}]}
    project_state.put("depositions", "dep-1", moved, "Ada Moreno")
    assert project_state.load()["depositions"] == [moved]
    assert [(a.action, a.target) for a in audit.read()] == [("keep_depositions", "dep-1")]


def test_the_overrides_of_a_scope_are_replaced_whole():
    scope = "fermos:family:monod"
    named = {"by": "Ada Moreno", "at": AT}
    project_state.put("overrides", scope, [{"scope": scope, "key": "mu_max", "value": 0.3, **named},
                                           {"scope": scope, "key": "Ks", "value": 0.1, **named}], "Ada Moreno")
    project_state.put("overrides", scope, [{"scope": scope, "key": "Ks", "value": 0.2, **named}], "Ada Moreno")
    assert project_state.load()["overrides"] == {scope: [{"scope": scope, "key": "Ks", "value": 0.2, **named}]}


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
        # A reading in its own unit stands on a Proforma scenario's scope alone: a saved train keeps each value in
        # its parameter's unit (src/lib/pureos.ts `trainSpecOf`), and fermOS's panels offer no reading.
        *[("overrides", scope, [{"scope": scope, "key": "a_placeholder_key", "value": 2.0, "by": "Ada Moreno",
                                 "at": AT, "origin": "measurement", "ref": "dep-1/de-1", "unit": "placeholder-unit"}],
           "which a Proforma scenario's scope alone keeps")
          for scope in ("pureos:unit:tr-1:u-1", "fermos:family:monod")],
        ("overrides", "proforma:sc-1", [{"scope": "proforma:sc-1", "key": "price", "value": 0.4, "by": "Ada Moreno",
                                         "at": AT, "chosenBy": "Ada Moreno"}], "names who chose it"),
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


# ── each kind read as its model (alpha 2.2 E.0b) ───────────────────────

# Every kind of row as a page writes it (src/store.ts), placeholders throughout: fields a row may leave out written
# in some and left out in others, nulls where the page writes null, and a field the kind's model does not name, kept
# by an earlier page.
RUNBOOK = {"id": "rb-1", "kind": "research", "title": "A placeholder runbook", "status": "draft", "stages": [],
           "note": "", "eta": None, "outputs": [], "productId": None, "progressPct": 0, "estCostUsd": None,
           "strainId": None,
           "predictions": [{"id": "p-1", "label": "A placeholder prediction", "value": 3, "unit": "placeholder-unit",
                            "confidence": "low", "basis": "a placeholder"},
                           {"id": "p-2", "label": "Another placeholder prediction", "value": 2.5,
                            "unit": "placeholder-unit", "confidence": "medium", "basis": "a placeholder",
                            "kind": "interval", "interval": {"low": 2, "high": 3}, "artifactId": None}],
           "measurementSchema": [{"id": "m-1", "label": "A placeholder measure", "unit": "placeholder-unit",
                                  "timepoint": "harvest", "predictionId": "p-1"},
                                 {"id": "m-2", "label": "Another placeholder measure", "unit": "placeholder-unit",
                                  "timepoint": "harvest"}],
           "lockedAt": None, "lockHash": None}
CLOSED = {"id": "dep-2", "runbookId": "rb-1", "protocolId": "pr-1", "operatorId": "p-1", "startedAt": AT,
          "closedAt": "2026-10-30T09:00:00Z", "state": "closed",
          "entries": [ENTRY, {**ENTRY, "id": "de-2", "value": 7.5, "raw": "a placeholder reading -> corrected",
                              "confirmed": True, "correctedAt": "2026-10-30T08:00:00Z"}],
          "observations": [{"id": "ob-1", "stepId": "s-1", "at": AT, "raw": "a placeholder note",
                            "structured": "a placeholder structure"}],
          "reconciliation": {"at": "2026-10-30T09:10:00Z", "outcome": "inconclusive", "deltas": [
              {"predictionId": "p-1", "predicted": 3, "observed": 7.5, "unit": "placeholder-unit", "pctDelta": 150}],
                             "note": ""},
          "sampleTimes": {"de-1": 1, "de-2": 1.5}, "seriesRoles": {"m-1": "product"},
          "legacy": "a field an earlier page wrote"}
MEASURED = {"id": "me-1", "depositionId": "dep-2", "runbookId": "rb-1", "productId": None, "predictionId": "p-1",
            "label": "A placeholder prediction", "value": 7.5, "unit": "placeholder-unit", "provenance": "measured",
            "conditions": {"protocolId": "pr-1", "scale": 1, "strainId": None}, "deviations": ["a placeholder deviation"],
            "confirmed": True, "at": "2026-10-30T09:10:00Z"}
SCENARIO = {"id": "sc-1", "modelId": "a-placeholder-flowsheet", "flowsheetId": "a-placeholder-flowsheet",
            "kind": "biosteam", "name": "A placeholder scenario", "description": "", "product": "", "dims": [],
            "point": {}, "assumptions": [], "pinned": False, "lastRunId": None, "createdAt": AT}
COMPOSITE = {"id": "sc-2", "modelId": "a-placeholder-flowsheet", "kind": "biosteam", "name": "A placeholder composite",
             "description": "", "product": "", "pinned": True, "vessel": "0123456789abcdef",
             "trainRun": "fedcba9876543210"}
BUILT = {"train": {"id": "tr-2", "name": "A placeholder train", "program": "placeholder",
                   "product": "a-placeholder-product",
                   "inlet": {"kind": "typed", "ref": None,
                             "params": {"a_placeholder_key": {"value": 1, "by": "Ada Moreno", "at": AT}}},
                   "units": [{"id": "U1", "type": "a_placeholder_type", "params": {}, "outlets": {}, "records": {},
                              "readFrom": None}]},
         "savedAt": AT, "by": "Ada Moreno"}
PANEL = [{"scope": "proforma:sc-1", "key": "a_placeholder_key", "value": 1.5, "low": None, "high": None,
          "by": "Ada Moreno", "at": AT, "note": None},
         {"scope": "proforma:sc-1", "key": "another_placeholder_key", "value": 2, "low": 1, "high": 3,
          "by": "Ada Moreno", "at": AT, "note": "a placeholder", "origin": "measurement", "ref": "dep-2/de-2"},
         # A reading as Proforma's parameter panel keeps one (alpha 2.2 E.17): its own value and unit, one value.
         {"scope": "proforma:sc-1", "key": "a_third_placeholder_key", "value": 7.5, "unit": "placeholder-unit",
          "low": None, "high": None, "by": "Ada Moreno", "at": AT, "note": None, "origin": "measurement",
          "ref": "dep-2/de-1"}]
PAGE_ROWS = [("depositions", "dep-1", DEPOSITION), ("depositions", "dep-2", CLOSED),
             ("measuredEvidence", "me-1", MEASURED), ("runbooks", "rb-1", RUNBOOK), ("scenarios", "sc-1", SCENARIO),
             ("scenarios", "sc-2", COMPOSITE), ("trains", "tr-1", TRAIN), ("trains", "tr-2", BUILT),
             ("overrides", "proforma:sc-1", PANEL), ("fits", "sc-1", {"mu_max": "0123456789abcdef"}),
             ("runbookLocks", "rb-1", {"lockedAt": AT, "lockHash": "abc"})]


def as_the_page_writes(value: Any) -> str:
    """A row's JSON as the page writes it (JSON.stringify), keys sorted: a
    number as JavaScript writes one (`runbook_lock.js_number`), so `3` and
    `3.0` are one number, as they are to the page."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return js_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(as_the_page_writes(v) for v in value) + "]"
    return "{" + ",".join(f"{json.dumps(k, ensure_ascii=False)}:{as_the_page_writes(value[k])}"
                          for k in sorted(value)) + "}"


def served_row(served: dict[str, Any], kind: str, item_id: str) -> Any:
    held = served[kind]
    return held.get(item_id) if isinstance(held, dict) else next((r for r in held if r["id"] == item_id), None)


def test_each_kind_comes_back_through_the_route_byte_for_byte_as_the_page_wrote_it():
    """Every field a page sent stands where it was, a field it left out stays
    out, a null stays null, and a field the model does not name is kept: the
    row the page reads back is the one it wrote, as the page writes JSON."""
    c = client()
    for kind, item_id, row in PAGE_ROWS:
        r = c.put(f"/api/state/{kind}/{item_id}", json={"by": "Ada Moreno", "value": row})
        assert r.status_code == 200, (kind, r.text)
        assert r.json() == {"kind": kind, "id": item_id, "value": row}
    served = c.get("/api/state").json()
    assert served["refused"] == [] and ProjectState.model_validate(served)
    for kind, item_id, row in PAGE_ROWS:
        assert as_the_page_writes(served_row(served, kind, item_id)) == as_the_page_writes(row), (kind, item_id)
    assert "correctedAt" not in served_row(served, "depositions", "dep-2")["entries"][0]
    assert "kind" not in served_row(served, "runbooks", "rb-1")["predictions"][0]
    assert "predictionId" not in served_row(served, "runbooks", "rb-1")["measurementSchema"][1]
    assert {"vessel", "trainRun"}.isdisjoint(served_row(served, "scenarios", "sc-1"))
    assert served_row(served, "depositions", "dep-2")["legacy"] == "a field an earlier page wrote"
    assert served["depositedBy"] == {"dep-1": "Ada Moreno", "dep-2": "Ada Moreno"}


def kept_before_its_model(kind: str, item_id: str, body: Any) -> None:
    """A row as an earlier page wrote it, kept in its table as it stood: no
    row was read as its kind's model before alpha 2.2 E.0b."""
    async def keep() -> None:
        async with db.session() as s:
            if kind == project_state.OVERRIDES:
                for o in body:
                    await s.execute(insert(t.overrides).values(project_id=projects.current(), scope=item_id,
                                                               key=o["key"], body=o, created_by="Ada Moreno"))
                return
            k = project_state.KINDS[kind]
            value = {"id": item_id, "byInput": body} if kind == "fits" else body
            await rows.put(s, k.table, projects.current(), item_id, value, by="Ada Moreno", **k.columns(body))

    db.run(keep())


def test_a_row_kept_before_its_kind_had_a_model_that_does_not_read_is_named_and_the_rest_load():
    for kind, item_id, row in PAGE_ROWS:
        project_state.put(kind, item_id, row, "Ada Moreno")
    kept_before_its_model("depositions", "dep-old", {"id": "dep-old", "runbookId": "rb-1",
                                                     "entries": [{"step": "s1", "value": 7.2}]})
    kept_before_its_model("scenarios", "sc-old", {"id": "sc-old", "kind": "authored", "name": "An older placeholder"})
    kept_before_its_model("trains", "tr-old", {"train": {"id": "tr-old", "units": []}, "savedAt": AT, "by": "Ada Moreno"})
    kept_before_its_model("overrides", "fermos:family:a-placeholder", [
        {"scope": "fermos:family:a-placeholder", "key": "a_placeholder_key", "value": 0.3},
        {"scope": "fermos:family:a-placeholder", "key": "another_placeholder_key", "value": 0.1, "by": "Ada Moreno",
         "at": AT}])
    kept_before_its_model("fits", "sc-old", {"a_placeholder_key": 3})
    r = client().get("/api/state")
    assert r.status_code == 200, r.text
    served = r.json()
    why = {(x["kind"], x["id"]): x["why"] for x in served["refused"]}
    assert why == {
        ("depositions", "dep-old"): "protocolId: Field required; operatorId: Field required; startedAt: Field required; "
                                    "and 11 more",
        ("scenarios", "sc-old"): "modelId: Field required; kind: Input should be 'biosteam'; description: Field "
                                 "required; and 2 more",
        ("trains", "tr-old"): "train.name: Field required; train.program: Field required; train.product: Field "
                              "required; and 1 more",
        ("overrides", "fermos:family:a-placeholder"): "the override of a_placeholder_key: by: Field required; at: Field "
                                                      "required",
        ("fits", "sc-old"): "a_placeholder_key: Input should be a valid string",
    }
    # Every other row loads beside them, the other override of the scope among them.
    for kind, item_id, row in PAGE_ROWS:
        assert as_the_page_writes(served_row(served, kind, item_id)) == as_the_page_writes(row), (kind, item_id)
    assert [o["key"] for o in served["overrides"]["fermos:family:a-placeholder"]] == ["another_placeholder_key"]
    assert "dep-old" not in {d["id"] for d in served["depositions"]} and "sc-old" not in served["fits"]
    # The service's own readers read each body as it was kept.
    assert "dep-old" in {d["id"] for d in project_state.load()["depositions"]}


def test_a_runbooks_lock_digest_reads_the_same_through_the_state():
    """lock.ts's digests (`pnpm export:lock-fixtures`) over each case's
    predictions and measures, a field left out and a null among them, are the
    digests of the rows GET /api/state serves; a page sending a locked row
    back as it read it is held to its lock."""
    c = client()
    for n, case in enumerate(cases()):
        rid = f"rb-case-{n}"
        row = {**RUNBOOK, "id": rid, "predictions": case["predictions"], "measurementSchema": case["schema"]}
        assert c.put(f"/api/state/runbooks/{rid}", json={"by": "Ada Moreno", "value": row}).status_code == 200
        lock = {"lockedAt": AT, "lockHash": case["digest"]}
        assert c.put(f"/api/state/runbookLocks/{rid}", json={"by": "Ada Moreno", "value": lock}).status_code == 200
    served = c.get("/api/state").json()
    held = {r["id"]: r for r in served["runbooks"]}
    for n, case in enumerate(cases()):
        got = held[f"rb-case-{n}"]
        assert lock_hash(got["predictions"], got["measurementSchema"]) == case["digest"], case["name"]
        assert frozen_as(got, served["runbookLocks"][got["id"]]["lockHash"]), case["name"]
        again = c.put(f"/api/state/runbooks/{got['id']}", json={"by": "Ada Moreno", "value": got})
        assert again.status_code == 200, (case["name"], again.text)


@pytest.mark.parametrize(("kind", "item_id", "value", "words"), [
    ("depositions", "dep-1", {**DEPOSITION, "state": "paused"},
     "this depositions row does not read as a deposition: state: Input should be 'staged', 'running' or 'closed'; "
     "nothing was kept"),
    ("depositions", "dep-1", {**DEPOSITION, "entries": [{"id": "de-1", "value": 7.2}]},
     "does not read as a deposition: entries[0].measureId: Field required"),
    ("measuredEvidence", "me-1", {k: v for k, v in MEASURED.items() if k != "conditions"},
     "this measuredEvidence row does not read as measured evidence: conditions: Field required"),
    ("runbooks", "rb-2", {**RUNBOOK, "id": "rb-2", "status": "shelved"}, "does not read as a runbook: status: "),
    ("scenarios", "sc-1", {"id": "sc-1", "kind": "biosteam", "name": "n"},
     "this scenarios row does not read as a Proforma scenario: modelId: Field required"),
    ("trains", "tr-1", {"train": {"id": "tr-1", "units": []}, "savedAt": AT, "by": "Ada Moreno"},
     "this trains row does not read as a train the Builder saved: train.name: Field required"),
    ("overrides", "proforma:sc-1", [{**PANEL[0], "value": True}],
     "the override of a_placeholder_key in proforma:sc-1 does not read as an override: value: an override's value, "
     "low and high are numbers or words, never true or false; nothing was kept"),
    ("overrides", "proforma:sc-1", [{k: v for k, v in PANEL[1].items() if k != "ref"}],
     "names its reading as <deposition id>/<entry id> (ref)"),
    ("overrides", "proforma:sc-1", [{**PANEL[0], "unit": "placeholder-unit"}],
     "the override of a_placeholder_key in proforma:sc-1 does not read as an override: the row: the override of "
     "a_placeholder_key keeps a unit of its own for a deposition's reading alone, and a person's assumption is in "
     "its parameter's unit; nothing was kept"),
])
def test_a_row_that_does_not_read_as_its_kind_is_refused_in_words_and_nothing_is_kept(kind, item_id, value, words):
    with pytest.raises(project_state.StateRefused) as refused:
        project_state.put(kind, item_id, value, "Ada Moreno")
    assert words in str(refused.value)
    r = client().put(f"/api/state/{kind}/{item_id}", json={"by": "Ada Moreno", "value": value})
    assert r.status_code == 422 and words in r.json()["detail"]
    assert project_state.state().model_dump(mode="json") == EMPTY and audit.read() == []


def test_a_live_conversation_is_served_whole_an_older_turn_among_them():
    """A conversation is Postdoc's own record, read from the whole of what it
    keeps: every field of each turn is in the answer, one a turn kept before
    the field existed among them (served as its model's default)."""
    project_state.put("conversations", "lc-1", LIVE, "Ada Moreno")
    older = {k: v for k, v in KEPT["turns"][0].items() if k not in ("by", "artifactIds")}

    async def keep_older() -> None:
        async with db.session() as s:
            await rows.put(s, t.turns, projects.current(), "t-1", older, by="Ada Moreno", conversation_id="lc-1",
                           seq=1, status="answered")

    db.run(keep_older())
    served = client().get("/api/state").json()["conversations"]
    assert served == [c.model_dump(mode="json") for c in conversations.listed()] == [KEPT]
    assert list(served[0]) == list(LiveConversation.model_fields)
