"""biorepo.write — one write function, four refusals (OF-BLD-012 §2.3, §7.1–7.2).

Every rule that keeps a bad decision out of the committed file has a test
that presents that decision and reads the refusal's rule. Then the paths a
good decision takes: a candidate a reviewer accepted or rejected is copied
beside the decision, a rejection reaches Witness as a false positive, an
accepted record survives a checkout that never ran the extractor, and a
rejected record stops being retrieved. Offline: the structural JATS fixture
stands in for B5's text, the model call is stubbed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import biorepo, extract, intake, witness
from openferment_core.api import app
from openferment_core.corpus import load_corpus
from openferment_core.models import BioRepo, Overlay, Quantity, ReviewDecision

REPO_ROOT = Path(__file__).parent.parent.parent
STRUCTURAL = "structural"

# The extractor found a titre in B5's table — a field the seed has no B5
# record for, so it is a new candidate, hk1-B5-a07dd73c.
NEW_TITRE = {
    "candidates": [
        {
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
        }
    ]
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(extract, "FIXTURE_DIR", tmp_path / "no-saved-responses")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


def fetch_b5():
    return intake.fetch_paper({"id": "B5", "pmcid": STRUCTURAL})


def extract_b5(monkeypatch):
    fetch_b5()
    monkeypatch.setattr(extract, "call_model", lambda *_: (NEW_TITRE, extract.Usage()))
    return extract.extract_paper("B5")


def decision(record_id: str, status: str = "verified", **overrides) -> ReviewDecision:
    base = dict(
        status=status,
        provenance="curated",
        reviewer="sean",
        recordId=record_id,
        at="2026-09-14T12:00:00Z",
    )
    base.update(overrides)
    return ReviewDecision(**base)


def identified(paper_id: str) -> bool:
    p = load_corpus().paper(paper_id) or {}
    return bool(p.get("pmcid") or p.get("doi") or p.get("pmid"))


def unfetched_seed_record() -> str:
    """A seed record on an identified paper nobody has fetched in this test."""
    return next(r["id"] for r in load_corpus().records if r["paperId"] != "B5" and identified(r["paperId"]))


def unidentified_seed_record() -> str:
    """A seed record on a paper with no PMCID, DOI or PMID — 73 of the 132."""
    return next(r["id"] for r in load_corpus().records if not identified(r["paperId"]))


# ── the file ───────────────────────────────────────────────────────────


def test_a_missing_file_is_an_empty_repository():
    assert biorepo.read() == BioRepo()
    assert biorepo.decisions() == {} and biorepo.records() == []


def test_the_committed_file_is_the_model_and_starts_empty():
    raw = json.loads((REPO_ROOT / "core" / "data" / "biorepo.json").read_text(encoding="utf-8"))
    assert list(raw) == ["version", "decisions", "records"]
    assert BioRepo.model_validate(raw).version == 1


# ── the four refusals ──────────────────────────────────────────────────


def test_refuses_a_record_that_resolves_to_nothing():
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-NOPE-1", "rejected"))
    assert caught.value.rule == "record"
    assert not biorepo.PATH.exists(), "a refusal writes nothing"


@pytest.mark.parametrize("reviewer", [None, "", "   "])
def test_refuses_an_empty_reviewer(reviewer):
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision(unfetched_seed_record(), "rejected", reviewer=reviewer))
    assert caught.value.rule == "reviewer"


def test_refuses_a_promotion_on_a_paper_with_no_full_text():
    rid = unfetched_seed_record()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision(rid, "verified"))
    assert caught.value.rule == "fulltext"
    # A rejection needs no text: it is not claiming the paper said anything.
    stored = biorepo.write(decision(rid, "rejected", rejectReason="duplicate of another record"))
    assert stored.status == "rejected" and biorepo.decisions()[rid] == stored


def test_refuses_a_promotion_whose_quote_fails_anchoring():
    fetch_b5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "verified", quote="a sentence the paper never wrote"))
    assert caught.value.rule == "quote" and "rule 'quote'" in str(caught.value)


def test_gold_needs_a_quote_that_anchors_its_own_will_not_do_here():
    # B5's curated quote is about colonies; the structural fixture standing
    # in for its text says nothing of the kind. Gold means "this sentence in
    # this paper says this number", so without one, it is refused.
    fetch_b5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "verified", provenance="gold", gold=Quantity(value=8.5, unit="d")))
    assert caught.value.rule == "quote"


def test_refuses_any_decision_on_a_paper_with_no_identifier():
    # check:biorepo fails the build on such a decision (§7.4); the write
    # function says so first, for a rejection as much as a promotion.
    rid = unidentified_seed_record()
    for status in ("rejected", "verified"):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(decision(rid, status, rejectReason="x"))
        assert caught.value.rule == "paper"
    assert not biorepo.PATH.exists()


def test_refuses_a_typed_value_outside_the_fields_range():
    # §2.4 rule 5 for what a reviewer typed: 8500 days to a colony is not a
    # colony time, whatever the reviewer meant; and a unit that does not
    # normalise is refused the same way. Status does not matter.
    fetch_b5()
    for status in ("verified", "unverified"):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(decision("r-B5-1", status, corrected=Quantity(value=8500, unit="d")))
        assert caught.value.rule == "range", status
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "verified", corrected=Quantity(value=8.5, unit="furlongs")))
    assert caught.value.rule == "range"
    # In range, it is stored — with the correction.
    stored = biorepo.write(decision("r-B5-1", "verified", corrected=Quantity(value=9, unit="d")))
    assert stored.corrected == Quantity(value=9, unit="d")


def test_both_typed_values_are_range_checked_not_just_the_first():
    # A decision may carry a gold value AND a correction. Rule 5 applies to
    # each: an in-range correction does not launder an out-of-range gold, and
    # the other way round. The message names which one failed.
    fetch_b5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "verified", provenance="gold",
                               gold=Quantity(value=8500, unit="d"), corrected=Quantity(value=9, unit="d")))
    assert caught.value.rule == "range" and "gold" in caught.value.why
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "verified", provenance="gold",
                               gold=Quantity(value=9, unit="d"), corrected=Quantity(value=8500, unit="d")))
    assert caught.value.rule == "range" and "corrected" in caught.value.why
    assert not biorepo.PATH.exists()


def test_refuses_gold_that_is_not_verified():
    fetch_b5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-B5-1", "unverified", provenance="gold", gold=Quantity(value=8.5, unit="d")))
    assert caught.value.rule == "status"


# ── what a good decision does ──────────────────────────────────────────


def test_accept_without_a_quote_proceeds_on_a_fetched_paper():
    fetch_b5()
    stored = biorepo.write(decision("r-B5-1", "verified"))
    assert stored.quote is None and stored.status == "verified"
    assert biorepo.read().decisions["r-B5-1"] == stored
    assert biorepo.read().records == [], "a seed record is not copied; the seed has it"


def test_gold_on_a_candidate_anchors_on_its_quote_and_keeps_both(monkeypatch):
    extract_b5(monkeypatch)
    stored = biorepo.write(
        decision("hk1-B5-a07dd73c", "verified", provenance="gold", gold=Quantity(value=7, unit="mg L⁻¹"))
    )
    # The candidate's own quote and section were copied onto the decision,
    # so `check:biorepo`'s "every gold decision has a quote" holds by
    # construction.
    assert stored.quote == "Placeholder A | 7 | mg L-1" and stored.sectionId == "t1"
    repo = biorepo.read()
    assert [c.id for c in repo.records] == ["hk1-B5-a07dd73c"]
    assert repo.records[0].status == "unverified", "the copy is the candidate; the decision is the authority"


def test_a_rejected_candidate_is_a_false_positive_in_the_run(monkeypatch):
    extract_b5(monkeypatch)
    biorepo.write(decision("hk1-B5-a07dd73c", "rejected", rejectReason="a placeholder row, not a measurement"))
    runs = witness.runs()
    assert [fp.id for fp in runs[0].falsePositives] == ["hk1-B5-a07dd73c"]
    fp = runs[0].falsePositives[0]
    assert fp.field == "titer_secreted" and fp.extracted == Quantity(value=7, unit="mg L⁻¹")
    assert fp.note == "a placeholder row, not a measurement"
    # Still in the overlay's candidates, with its decision beside it, so the
    # browser can show what was decided rather than a hole.
    overlay = Overlay.model_validate(TestClient(app).get("/api/biorepo/overlay").json())
    assert [c.id for c in overlay.candidates] == ["hk1-B5-a07dd73c"]
    assert overlay.records["hk1-B5-a07dd73c"].status == "rejected"


def test_a_decided_candidate_outlives_the_cache(monkeypatch):
    extract_b5(monkeypatch)
    biorepo.write(decision("hk1-B5-a07dd73c", "verified"))
    for path in extract.CANDIDATES_DIR.glob("*.json"):
        path.unlink()
    # No run — nothing was extracted in this checkout — but the record is
    # still a record, and a later decision about it still resolves.
    assert witness.runs() == []
    assert [c.id for c in witness.new_candidates()] == ["hk1-B5-a07dd73c"]
    again = biorepo.write(decision("hk1-B5-a07dd73c", "rejected", rejectReason="on reflection, a placeholder"))
    assert again.status == "rejected" and len(biorepo.read().records) == 1


def test_the_file_is_written_the_way_the_guard_reads_it():
    fetch_b5()
    biorepo.write(decision("r-B5-1", "verified"))
    raw = json.loads(biorepo.PATH.read_text(encoding="utf-8"))
    assert raw["version"] == 1 and list(raw["decisions"]) == ["r-B5-1"]
    assert raw["decisions"]["r-B5-1"]["recordId"] == "r-B5-1"
    assert "quote" not in raw["decisions"]["r-B5-1"], "None is left out, not written as null"


# ── the endpoint ───────────────────────────────────────────────────────


@pytest.fixture
def client():
    return TestClient(app)


def test_decisions_endpoint_stores_or_refuses_with_the_rule(client):
    rid = unfetched_seed_record()
    ok = client.post("/api/biorepo/decisions", json=decision(rid, "rejected", rejectReason="x").model_dump())
    assert ok.status_code == 200 and ok.json()["recordId"] == rid

    bad = client.post("/api/biorepo/decisions", json=decision("r-NOPE-1", "rejected").model_dump())
    assert bad.status_code == 422 and bad.json()["detail"].startswith("record:")

    empty = client.post("/api/biorepo/decisions", json=decision(rid, "rejected", reviewer="").model_dump())
    assert empty.status_code == 422 and empty.json()["detail"].startswith("reviewer:")


# ── retrieval honours a rejection (§7.4) ───────────────────────────────


def test_a_rejected_record_is_resolvable_but_never_retrieved(tmp_path):
    corpus = load_corpus()
    raw = json.loads(Path(extract.intake.DATA_DIR.parent / "openferment_core" / "data" / "corpus.json").read_text())
    # A record asked for in its own words is the top hit — until it is rejected.
    target = raw["records"][0]
    query = target["quote"]
    assert [h["id"] for h in corpus.search(query)][0] == target["id"]
    target["status"] = "rejected"
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(raw))
    edited = load_corpus(str(path))
    assert edited.record(target["id"]) is not None, "still resolvable — a decision may name it"
    assert target["id"] not in [h["id"] for h in edited.search(query)]
