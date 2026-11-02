"""A runbook lock's digest (runbook_lock.py), held to the browser's own.

`tests/fixtures/lock-digests.json` is written by `pnpm
export:lock-fixtures` from src/engine/lock.ts; `pnpm test:core` regenerates
it first, so the port is held to the browser's code as it stands. Each
case's digest is reproduced from the case as JSON carries it, the numbers
are written as JavaScript writes them, and a row is frozen under a digest
only while its predictions and measures are the ones it froze.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core.runbook_lock import canonical, frozen_as, js_number, lock_hash

FIXTURE = Path(__file__).parent / "fixtures" / "lock-digests.json"


def cases() -> list[dict]:
    if not FIXTURE.exists():
        pytest.fail(f"{FIXTURE} is missing; run `pnpm export:lock-fixtures` (pnpm test:core does)")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def test_every_digest_the_browser_wrote_is_reproduced():
    every = cases()
    assert len(every) >= 10
    wrong = [(c["name"], lock_hash(c["predictions"], c["schema"]), c["digest"]) for c in every
             if lock_hash(c["predictions"], c["schema"]) != c["digest"]]
    assert wrong == []


@pytest.mark.parametrize(("value", "written"), [
    (0, "0"), (-0.0, "0"), (1.0, "1"), (3, "3"), (-1.5, "-1.5"), (0.1, "0.1"), (0.30000000000000004, "0.30000000000000004"),
    (100, "100"), (1e20, "100000000000000000000"), (1e21, "1e+21"), (1.5e21, "1.5e+21"), (10 ** 21, "1e+21"),
    (2 ** 53, "9007199254740992"), (1e-6, "0.000001"), (1.5e-6, "0.0000015"), (1e-7, "1e-7"), (-1e-7, "-1e-7"),
    (1.23e-18, "1.23e-18"), (5e-324, "5e-324"), (1.7976931348623157e308, "1.7976931348623157e+308"),
    (123456789.123, "123456789.123"), (float("nan"), "null"), (float("inf"), "null"),
])
def test_a_number_is_written_as_javascript_writes_it(value, written):
    assert js_number(value) == written


def test_a_field_left_out_is_written_null_where_javascript_writes_undefined_so():
    point = {"id": "p1", "label": "Titre", "value": 1, "unit": "g/L", "confidence": "low"}
    assert canonical([point], [{"id": "m1", "label": "Titre", "unit": "g/L"}]) == \
        '{"p":[["p1","Titre",1,"g/L","low",null]],"m":[["m1","Titre","g/L",null,null]]}'


def test_an_absent_field_and_a_null_one_are_told_apart():
    point = {"id": "p1", "label": "Titre", "value": 1, "unit": "g/L", "confidence": "low", "basis": "a run"}
    assert canonical([point], []) == '{"p":[["p1","Titre",1,"g/L","low","a run"]],"m":[]}'
    assert canonical([{**point, "kind": None}], []) == '{"p":[["p1","Titre",1,"g/L","low","a run",null,null,null,null]],"m":[]}'
    assert lock_hash([point], []) != lock_hash([{**point, "kind": None}], [])


def test_a_row_is_frozen_under_its_digest_only_while_its_claims_stand():
    case = cases()[0]
    row = {"id": "rb-1", "status": "draft", "predictions": case["predictions"], "measurementSchema": case["schema"]}
    assert frozen_as(row, case["digest"])
    assert frozen_as({**row, "status": "running", "stages": [{"name": "Seed", "status": "done"}]}, case["digest"])
    moved = {**row, "predictions": [{**case["predictions"][0], "value": case["predictions"][0]["value"] + 1}]}
    assert not frozen_as(moved, case["digest"])
    assert not frozen_as({**row, "measurementSchema": []}, case["digest"])
    assert not frozen_as({**row, "predictions": [{"id": "p1"}]}, case["digest"])
    assert not frozen_as({**row, "predictions": [None]}, case["digest"])
    assert not frozen_as({**row, "predictions": "not a list of predictions"}, case["digest"])
