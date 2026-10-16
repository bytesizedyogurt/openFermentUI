"""The offline demo's fixtures go through the real code paths (OF-BLD-012 §8.1).

`pnpm demo:offline` runs the service in fixture mode against
tests/fixtures/demo/. These tests point the same modules at that directory
the way the demo script does — by path, not by replaying the script — and
check that the three fixtures still fit the code: the saved JATS splits,
the saved response anchors to it, the run scores, and the saved decisions
are ones biorepo.write would have stored. A demo that drifts from the code
would be the fake this project exists to avoid, and it would drift silently.

The set has two shapes (OF-BLD-014 §1.5). Over the hand-written stand-in,
three decisions demonstrate the review. Over a real model response, the one
decision is the accept of the curated r-B5-3, and the real candidates stay
undecided. Either way the replayed candidates are what the saved response
anchors, and the rejections are as many as the saved response's. The set
`pnpm test:export` reads, tests/fixtures/export/, is the stand-in decided all
four ways whatever the demo set holds.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core import biorepo, demo, extract, intake, witness
from openferment_core.models import BioRepo
from openferment_core.validate import anchor_all

DEMO = Path(__file__).parent / "fixtures" / "demo"
EXPORT = Path(__file__).parent / "fixtures" / "export"
REAL = demo.response_is_real(DEMO)


@pytest.fixture(autouse=True)
def _demo(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FIXTURE_DIR", DEMO / "jats")
    monkeypatch.setattr(extract, "FIXTURE_DIR", DEMO / "extract")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


def saved_set(root: Path = DEMO) -> BioRepo:
    return BioRepo.model_validate(json.loads((root / "biorepo.json").read_text(encoding="utf-8")))


def anchored_from_the_saved_response(fixtures: Path = DEMO):
    """What the saved response anchors against the saved text, asked of
    anchoring directly: the yardstick the replay is held to."""
    fetched = intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"}, force=True)
    sections = [s.model_dump() for s in fetched.sections]
    raws = json.loads((fixtures / "extract" / "B5.json").read_text(encoding="utf-8"))["raw"]["candidates"]
    return anchor_all(raws, sections, paper_id="B5")


def test_the_fixtures_say_what_they_are():
    # Each fixture carries a note on its own provenance. The stand-in JATS
    # says it is not the paper; a real one saved by `pnpm demo:fixtures`
    # says which paper and when. Either way the note is there.
    xml = (DEMO / "jats" / "PMC8471596.xml").read_text(encoding="utf-8")
    assert "THIS IS NOT THE PAPER" in xml or "Saved from Europe PMC" in xml
    response = json.loads((DEMO / "extract" / "B5.json").read_text(encoding="utf-8"))
    assert response["_note"].strip(), "the saved response says where it came from"
    assert ("HAND-WRITTEN" in response["_note"]) is not REAL, "the note and the usage agree on what it is"
    for root in (DEMO, EXPORT):
        repo = json.loads((root / "biorepo.json").read_text(encoding="utf-8"))
        assert "never touches" in repo["_note"]


def test_the_loop_replays_from_the_fixtures():
    fetched = intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    assert fetched.status == "complete" and fetched.sections[0].id == "abstract"

    result = extract.extract_paper("B5")
    expected = anchored_from_the_saved_response()
    # The ids are content-addressed: the replay is consistent when it yields
    # exactly what the saved response anchors, and rejects as many.
    assert [c.id for c in result.candidates] == [c.id for c in expected.accepted], result.rejectionDetails
    assert result.rejected == expected.rejected
    saved_usage = json.loads((DEMO / "extract" / "B5.json").read_text(encoding="utf-8")).get("usage") or {}
    assert result.usage.costUsd == saved_usage.get("costUsd", 0), "the replay reports the saved call; it makes none"

    runs = witness.runs()
    assert [r.run for r in runs] == ["claude-1"]
    assert {r.goldRecordId for r in runs[0].results} == {"r-B5-1", "r-B5-2", "r-B5-3"}
    if REAL:
        # §1.R — held to what anchoring gave when the response was saved, and
        # never to nothing: a demo with no candidate decides nothing.
        at_save = json.loads((DEMO / "extract" / "B5.json").read_text(encoding="utf-8"))[demo.ANCHORED_AT_SAVE]
        assert [c.id for c in result.candidates] == at_save["candidates"] and result.rejected == at_save["rejected"]
        assert result.candidates, "a real response that anchors nothing demonstrates nothing"
    else:
        assert result.rejected == 0, "every hand-written candidate anchors"
        assert [c.id for c in result.candidates] == [c.id for c in saved_set().records]


def test_the_saved_decisions_are_ones_the_write_function_stores():
    # Seed the scratch file the way the demo script does, then check that the
    # write function accepts exactly those decisions over these fixtures —
    # rewriting each one and comparing.
    saved = saved_set()
    intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    result = extract.extract_paper("B5")
    for rid, d in saved.decisions.items():
        assert biorepo.write(d) == d, rid
    assert biorepo.read().decisions == saved.decisions
    assert [c.id for c in biorepo.read().records] == [c.id for c in saved.records]

    if REAL:
        # §1.5 — a real response records no decision nobody made.
        assert set(saved.decisions) == {"r-B5-3"} and saved.records == []
        assert saved.decisions["r-B5-3"].status == "verified"
        undecided = {c.id for c in result.candidates} - set(saved.decisions)
        assert undecided == {c.id for c in result.candidates}, "every real candidate waits for a person"
        assert witness.runs()[0].falsePositives == []
        return

    assert set(saved.decisions) == {c.id for c in saved.records} | {"r-B5-3"}
    assert len(saved.records) == 2
    # A REJECTED candidate is the run's false positive, with its reason; the
    # one promoted to gold is not — the extractor got that row right.
    rejected = [rid for rid, d in saved.decisions.items() if d.status == "rejected"]
    assert rejected, "the fixture set needs a rejection to score as a false positive"
    fps = witness.runs()[0].falsePositives
    assert [fp.id for fp in fps] == rejected
    assert all(fp.note for fp in fps)


def test_the_export_set_covers_every_way_a_decision_can_land():
    """`pnpm test:export` reads this set to prove the merge reaches the
    corpus (OF-BLD-012.1 F4), so the set has to hold one of each."""
    kinds = saved_set(EXPORT).decisions.values()
    assert any(d.corrected for d in kinds), "a correction, so the exported value is the reviewer's"
    assert any(d.provenance == "gold" or d.gold for d in kinds), "a gold promotion"
    assert any(d.status == "rejected" for d in kinds), "a rejection, which must stay out of the corpus"
    assert any(d.status == "verified" and not d.gold for d in kinds), "a plain accept"


# ── the sets are what the code makes (E.2) ─────────────────────────────


def test_the_committed_sets_are_what_demo_fixtures_writes(tmp_path):
    demo.rebuild_decisions(DEMO, out=tmp_path / "demo.json")
    demo.rebuild_export_set(out=tmp_path / "export.json")
    assert (tmp_path / "demo.json").read_text(encoding="utf-8") == (DEMO / "biorepo.json").read_text(encoding="utf-8")
    assert (tmp_path / "export.json").read_text(encoding="utf-8") == (EXPORT / "biorepo.json").read_text(encoding="utf-8")


def test_the_prototype_fixtures_are_what_demo_prototype_writes(tmp_path, monkeypatch):
    """OF-BLD-014 E.2: the smoke double serves these files, so they must be
    what the code produces today. The fixtures name the model chain they were
    written under, `llm.py`'s defaults; a session whose environment names other
    models (one model as primary and fallback, say) regenerates at those
    defaults, so the comparison is of the code and never of the environment."""
    for name in ("OPENFERMENT_MODEL", "OPENFERMENT_FALLBACK_MODEL", "OPENFERMENT_INDEX_MODEL", "OPENFERMENT_EFFORT"):
        monkeypatch.delenv(name, raising=False)
    written = demo.rebuild_prototype(out=tmp_path)
    assert written
    for path in written:
        committed = demo.PROTOTYPE / path.name
        assert committed.is_file(), f"{committed} is missing: run python -m openferment_core.demo --prototype"
        assert path.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8"), (
            f"{path.name} no longer matches the code: run python -m openferment_core.demo --prototype"
        )
    committed = sorted(p.name for p in demo.PROTOTYPE.glob("*.json*"))
    assert committed == sorted(p.name for p in written), "a fixture the command no longer writes is still committed"


def test_the_figure_sample_is_what_demo_prototype_writes(tmp_path):
    """OF-BLD-014 §6.1: the gallery's sample, said to be one in its first field."""
    written = demo.rebuild_figure_samples(tmp_path / "figureSamples.json")
    assert written.read_text(encoding="utf-8") == demo.FIGURE_SAMPLES.read_text(encoding="utf-8"), (
        "figureSamples.json no longer matches the code: run python -m openferment_core.demo --prototype"
    )
    assert next(iter(json.loads(written.read_text()))) == "_sample"


def test_the_fermos_sample_is_what_demo_prototype_writes(tmp_path):
    """OF-BLD-014 §7.4: the browser's sample run, said to be one in its first field."""
    written = demo.rebuild_fermos_sample(tmp_path / "fermosSample.json")
    assert written.read_text(encoding="utf-8") == demo.FERMOS_SAMPLE.read_text(encoding="utf-8")
    assert next(iter(json.loads(written.read_text()))) == "_sample"


def test_building_a_set_leaves_the_modules_where_they_were(tmp_path):
    where = (intake.FULLTEXT_DIR, extract.CANDIDATES_DIR, biorepo.PATH, intake.FIXTURE_DIR)
    demo.rebuild_export_set(out=tmp_path / "export.json")
    assert (intake.FULLTEXT_DIR, extract.CANDIDATES_DIR, biorepo.PATH, intake.FIXTURE_DIR) == where


# ── a real response, before one exists (OF-BLD-014 §1.5) ───────────────


@pytest.fixture
def real_shaped(tmp_path):
    """A fixture root shaped like what `pnpm demo:fixtures --real` saves.
    TEST STAND-IN: the structural document as the text, and a response whose
    usage names a model, so demo.py treats it as real. Two of its candidates
    anchor and one quotes a sentence the text does not hold."""
    root = tmp_path / "real"
    (root / "jats").mkdir(parents=True)
    (root / "jats" / "PMC8471596.xml").write_text(
        (Path(__file__).parent / "fixtures" / "jats" / "structural.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "extract").mkdir()
    raws = [*demo.SMOKE_RAWS, {
        "sectionId": "t1", "field": "titer_secreted", "value": 9, "unit": "mg L-1",
        "quote": "A sentence this document never wrote: 9 mg L-1", "isPrimary": True, "confidence": 0.5,
    }]
    (root / "extract" / "B5.json").write_text(json.dumps({
        "_note": "Test stand-in for a saved real response (test_demo.py).",
        "raw": {"candidates": raws},
        "usage": {"inputTokens": 1, "outputTokens": 1, "costUsd": 0.0, "models": ["claude-opus-5-5"]},
        # What anchoring gave at save time, written out here as the expectation.
        "anchoredAtSave": {"candidates": ["cl1-B5-a07dd73c", "cl1-B5-95f64ef4"], "rejected": 1},
    }), encoding="utf-8")
    return root


def test_a_real_response_gets_one_accept_and_its_candidates_wait(real_shaped, tmp_path, monkeypatch):
    assert demo.response_is_real(real_shaped)
    ids = demo.rebuild_decisions(real_shaped, out=tmp_path / "biorepo.json")
    built = BioRepo.model_validate_json((tmp_path / "biorepo.json").read_text(encoding="utf-8"))
    assert ids == ["r-B5-3"] and built.records == []
    assert built.decisions["r-B5-3"].status == "verified" and built.decisions["r-B5-3"].provenance == "curated"
    assert "never touches" in json.loads((tmp_path / "biorepo.json").read_text(encoding="utf-8"))["_note"]

    # The replay over it: what the response anchors, and its one rejection.
    monkeypatch.setattr(intake, "FIXTURE_DIR", real_shaped / "jats")
    monkeypatch.setattr(extract, "FIXTURE_DIR", real_shaped / "extract")
    intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    result = extract.extract_paper("B5")
    expected = anchored_from_the_saved_response(real_shaped)
    assert [c.id for c in result.candidates] == [c.id for c in expected.accepted] and len(result.candidates) == 2
    assert result.rejected == expected.rejected == 1
    at_save = json.loads((real_shaped / "extract" / "B5.json").read_text(encoding="utf-8"))[demo.ANCHORED_AT_SAVE]
    assert [c.id for c in result.candidates] == at_save["candidates"] and result.rejected == at_save["rejected"]


def test_a_real_response_that_anchors_nothing_is_refused(real_shaped, tmp_path):
    path = real_shaped / "extract" / "B5.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    for raw in saved["raw"]["candidates"]:
        raw["quote"] = "A sentence this document never wrote: " + str(raw["value"])
    path.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(SystemExit, match="anchors no candidate"):
        demo.rebuild_decisions(real_shaped, out=tmp_path / "biorepo.json")
    assert not (tmp_path / "biorepo.json").exists()


def test_saving_records_what_anchoring_gave(real_shaped, monkeypatch):
    path = real_shaped / "extract" / "B5.json"
    before = json.loads(path.read_text(encoding="utf-8"))
    before.pop(demo.ANCHORED_AT_SAVE)
    path.write_text(json.dumps(before), encoding="utf-8")
    monkeypatch.setattr(intake, "FIXTURE_DIR", real_shaped / "jats")
    monkeypatch.setattr(extract, "FIXTURE_DIR", real_shaped / "extract")
    intake.fetch_paper({"id": "B5", "pmcid": "PMC8471596"})
    result = extract.extract_paper("B5")
    demo.record_anchoring(path, result)
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after[demo.ANCHORED_AT_SAVE] == {"candidates": [c.id for c in result.candidates], "rejected": 1}
    assert after["raw"] == before["raw"] and after["usage"] == before["usage"]
