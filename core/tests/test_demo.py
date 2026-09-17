"""The offline demo's fixtures go through the real code paths (OF-BLD-012 §8.1).

`pnpm demo:offline` runs the service in fixture mode against
tests/fixtures/demo/. These tests point the same modules at that directory
the way the demo script does — by path, not by replaying the script — and
check that the three fixtures still fit the code: the stand-in JATS splits,
the saved response anchors to it, the run scores, and the saved decisions
are ones biorepo.write would have stored. A demo that drifts from the code
would be the fake this project exists to avoid, and it would drift silently.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core import biorepo, extract, intake, witness
from openferment_core.models import BioRepo

DEMO = Path(__file__).parent / "fixtures" / "demo"


@pytest.fixture(autouse=True)
def _demo(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FIXTURE_DIR", DEMO / "jats")
    monkeypatch.setattr(extract, "FIXTURE_DIR", DEMO / "extract")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


def test_the_fixtures_say_what_they_are():
    # Each fixture carries a note on its own provenance. The stand-in JATS
    # says it is not the paper; a real one saved by `pnpm demo:fixtures`
    # says which paper and when. Either way the note is there.
    xml = (DEMO / "jats" / "PMC8471596.xml").read_text(encoding="utf-8")
    assert "THIS IS NOT THE PAPER" in xml or "Saved from Europe PMC" in xml
    response = json.loads((DEMO / "extract" / "B5.json").read_text(encoding="utf-8"))
    assert response["_note"].strip(), "the saved response says where it came from"
    repo = json.loads((DEMO / "biorepo.json").read_text(encoding="utf-8"))
    assert "never touches" in repo["_note"]


def test_the_loop_replays_from_the_fixtures():
    fetched = intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    assert fetched.status == "complete" and [s.id for s in fetched.sections][:2] == ["abstract", "s1"]

    result = extract.extract_paper("B5")
    # The ids are content-addressed; the fixture set is consistent when the
    # replayed candidates are exactly the ones the saved decisions name.
    saved = BioRepo.model_validate(json.loads((DEMO / "biorepo.json").read_text(encoding="utf-8")))
    assert [c.id for c in result.candidates] == [c.id for c in saved.records], result.rejectionDetails
    assert result.rejected == 0
    assert result.usage.costUsd == 0, "nothing was spent — no call was made"

    runs = witness.runs()
    assert [r.run for r in runs] == ["haiku-1"]
    assert {r.goldRecordId for r in runs[0].results} == {"r-B5-1", "r-B5-2", "r-B5-3"}


def test_the_saved_decisions_are_ones_the_write_function_stores():
    # Seed the scratch file the way the demo script does, then check that the
    # write function accepts exactly those decisions over these fixtures —
    # rewriting each one and comparing.
    saved = BioRepo.model_validate(json.loads((DEMO / "biorepo.json").read_text(encoding="utf-8")))
    assert set(saved.decisions) == {c.id for c in saved.records} | {"r-B5-3"}
    assert len(saved.records) == 2

    intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    extract.extract_paper("B5")
    for rid, d in saved.decisions.items():
        assert biorepo.write(d) == d, rid
    assert biorepo.read().decisions == saved.decisions
    assert [c.id for c in biorepo.read().records] == [c.id for c in saved.records]

    # A REJECTED candidate is the run's false positive, with its reason; the
    # one promoted to gold is not — the extractor got that row right.
    rejected = [rid for rid, d in saved.decisions.items() if d.status == "rejected"]
    assert rejected, "the fixture set needs a rejection to score as a false positive"
    fps = witness.runs()[0].falsePositives
    assert [fp.id for fp in fps] == rejected
    assert all(fp.note for fp in fps)


def test_the_fixture_set_covers_every_way_a_decision_can_land():
    """`pnpm test:export` reads this set to prove the merge reaches the
    corpus (OF-BLD-012.1 F4), so the set has to hold one of each."""
    saved = BioRepo.model_validate_json((DEMO / "biorepo.json").read_text(encoding="utf-8"))
    kinds = saved.decisions.values()
    assert any(d.corrected for d in kinds), "a correction, so the exported value is the reviewer's"
    assert any(d.provenance == "gold" or d.gold for d in kinds), "a gold promotion"
    assert any(d.status == "rejected" for d in kinds), "a rejection, which must stay out of the corpus"
    assert any(d.status == "verified" and not d.gold for d in kinds), "a plain accept"
