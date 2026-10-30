"""biorepo.write — one write function, four refusals (OF-BLD-012 §2.3, §7.1–7.2).

Every rule that keeps a bad decision out of the project's decisions has a
test that presents that decision and reads the refusal's rule. Then the paths a
good decision takes: a candidate a reviewer accepted or rejected is copied
beside the decision, a rejection reaches Witness as a false positive, an
accepted record survives a checkout that never ran the extractor, and a
rejected record stops being retrieved. Offline: the papers and records are
the fictional test corpus (fixtures/test-corpus.json), the structural JATS
fixture stands in for T5's text, and the model call is stubbed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from openferment_core import biorepo, db, extract, intake, projects, witness
from openferment_core.db import models as t
from openferment_core.api import app
from openferment_core.corpus import load_corpus
from openferment_core.models import (
    BioRepo,
    FetchedSection,
    FetchResult,
    Overlay,
    Quantity,
    ReviewDecision,
)

REPO_ROOT = Path(__file__).parent.parent.parent
STRUCTURAL = "structural"

# The extractor found a titre in T5's table — a field the corpus has no T5
# record for, so it is a new candidate.
NEW_TITRE = {
    "candidates": [
        {
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
        }
    ]
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path, test_corpus):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "FIXTURE_DIR", tmp_path / "no-saved-responses")


def decision_rows() -> list[dict]:
    """The project's decision rows, in the order made."""

    async def read() -> list[dict]:
        async with db.session() as s:
            q = select(t.decisions.c.body).where(t.decisions.c.project_id == projects.current())
            return list((await s.execute(q.order_by(t.decisions.c.seq))).scalars())

    return db.run(read())


def nothing_decided() -> bool:
    return decision_rows() == []


def drop_candidates() -> None:
    """Every candidate row of the project goes, as a later extraction run
    replaces them."""

    async def drop() -> None:
        async with db.session() as s:
            await s.execute(delete(t.candidates).where(t.candidates.c.project_id == projects.current()))

    db.run(drop())


def fetch_t5():
    return intake.fetch_paper({"id": "T5", "pmcid": STRUCTURAL})


def extract_t5(monkeypatch):
    fetch_t5()
    monkeypatch.setattr(extract, "call_model", lambda *_: (NEW_TITRE, extract.Usage()))
    return extract.extract_paper("T5")


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


def fetch_saying(paper_id: str, record_id: str, sentence: str) -> None:
    """A fetched paper whose section says this, under the section id the
    record cites — written where a real fetch would leave it, so `cached`
    reads it the way it reads any other. Used where the test is about the
    anchoring rules and not about the fetch."""
    rec = load_corpus().record(record_id)
    assert rec is not None, record_id
    result = FetchResult(
        paperId=paper_id,
        status="complete",
        fetchedAt="2026-09-15T00:00:00Z",
        sections=[FetchedSection(id=rec["sectionId"], heading="Results", text=sentence)],
    )
    intake.FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)
    (intake.FULLTEXT_DIR / f"{paper_id}.json").write_text(
        result.model_dump_json(), encoding="utf-8"
    )


def identified(paper_id: str) -> bool:
    p = load_corpus().paper(paper_id) or {}
    return bool(p.get("pmcid") or p.get("doi") or p.get("pmid"))


def unfetched_seed_record() -> str:
    """A record on an identified paper nobody has fetched in this test."""
    return next(r["id"] for r in load_corpus().records if r["paperId"] != "T5" and identified(r["paperId"]))


def unidentified_seed_record() -> str:
    """A record on a paper with no PMCID, DOI or PMID."""
    return next(r["id"] for r in load_corpus().records if not identified(r["paperId"]))


# ── the file ───────────────────────────────────────────────────────────


def test_a_project_nobody_has_decided_in_is_an_empty_repository():
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
    assert nothing_decided(), "a refusal writes nothing"


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
    fetch_t5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "verified", quote="a sentence the paper never wrote"))
    assert caught.value.rule == "quote" and "rule 'quote'" in str(caught.value)


def test_gold_needs_a_quote_that_anchors_its_own_will_not_do_here():
    # T5's curated quote is about colonies; the structural fixture standing
    # in for its text says nothing of the kind. Gold means "this sentence in
    # this paper says this number", so without one, it is refused.
    fetch_t5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "verified", provenance="gold", gold=Quantity(value=8.5, unit="d")))
    assert caught.value.rule == "quote"


def test_refuses_any_decision_on_a_paper_with_no_identifier():
    # check:biorepo fails the build on such a decision (§7.4); the write
    # function says so first, for a rejection as much as a promotion.
    rid = unidentified_seed_record()
    for status in ("rejected", "verified"):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(decision(rid, status, rejectReason="x"))
        assert caught.value.rule == "paper"
    assert nothing_decided()


def test_refuses_a_typed_value_whose_unit_does_not_convert():
    # §2.4 rule 4 for what a reviewer typed: a unit that does not normalise,
    # or one of another family than the field's, is refused. Status does not
    # matter.
    fetch_t5()
    for status in ("verified", "unverified"):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(decision("r-T5-1", status, corrected=Quantity(value=8.5, unit="furlongs")))
        assert caught.value.rule == "unit", status
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "verified", corrected=Quantity(value=8.5, unit="g/L")))
    assert caught.value.rule == "unit"
    # In a unit of the field AND in the record's sentence (§6.9: a typed
    # number anchors like any other), it is stored — with the correction.
    rec = load_corpus().record("r-T5-1")
    fetch_saying("T5", "r-T5-1", f"In our hands, {rec['quote']}.")
    stored = biorepo.write(decision("r-T5-1", "verified", corrected=Quantity(value=7, unit="d")))
    assert stored.corrected == Quantity(value=7, unit="d")


def test_both_typed_values_are_unit_checked_not_just_the_first():
    # A decision may carry a gold value AND a correction. Rule 4 applies to
    # each: a correction in the field's unit does not launder a gold in
    # another, and the other way round. The message names which one failed.
    fetch_t5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "verified", provenance="gold",
                               gold=Quantity(value=9, unit="furlongs"), corrected=Quantity(value=9, unit="d")))
    assert caught.value.rule == "unit" and "gold" in caught.value.why
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "verified", provenance="gold",
                               gold=Quantity(value=9, unit="d"), corrected=Quantity(value=9, unit="furlongs")))
    assert caught.value.rule == "unit" and "corrected" in caught.value.why
    assert nothing_decided()


def test_refuses_gold_that_is_not_verified():
    fetch_t5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-1", "unverified", provenance="gold", gold=Quantity(value=8.5, unit="d")))
    assert caught.value.rule == "status"


# ── what a good decision does ──────────────────────────────────────────


def test_accept_without_a_quote_proceeds_on_a_fetched_paper():
    fetch_t5()
    stored = biorepo.write(decision("r-T5-1", "verified"))
    assert stored.quote is None and stored.status == "verified"
    assert biorepo.read().decisions["r-T5-1"] == stored
    assert biorepo.read().records == [], "a seed record is not copied; the seed has it"


def test_gold_on_a_candidate_anchors_on_its_quote_and_keeps_both(monkeypatch):
    extract_t5(monkeypatch)
    stored = biorepo.write(
        decision("cl1-T5-276fbb61", "verified", provenance="gold", gold=Quantity(value=7, unit="mg L⁻¹"))
    )
    # The candidate's own quote and section were copied onto the decision,
    # so `check:biorepo`'s "every gold decision has a quote" holds by
    # construction.
    assert stored.quote == "Placeholder A | 7 | mg L-1" and stored.sectionId == "t1"
    repo = biorepo.read()
    assert [c.id for c in repo.records] == ["cl1-T5-276fbb61"]
    assert repo.records[0].status == "unverified", "the copy is the candidate; the decision is the authority"


def test_a_rejected_candidate_is_a_false_positive_in_the_run(monkeypatch):
    extract_t5(monkeypatch)
    biorepo.write(decision("cl1-T5-276fbb61", "rejected", rejectReason="a placeholder row, not a measurement"))
    runs = witness.runs()
    assert [fp.id for fp in runs[0].falsePositives] == ["cl1-T5-276fbb61"]
    fp = runs[0].falsePositives[0]
    assert fp.field == "titer_secreted" and fp.extracted == Quantity(value=7, unit="mg L⁻¹")
    assert fp.note == "a placeholder row, not a measurement"
    # Still in the overlay's candidates, with its decision beside it, so the
    # browser can show what was decided rather than a hole.
    overlay = Overlay.model_validate(TestClient(app).get("/api/biorepo/overlay").json())
    assert [c.id for c in overlay.candidates] == ["cl1-T5-276fbb61"]
    assert overlay.records["cl1-T5-276fbb61"].status == "rejected"


def test_a_decided_candidate_outlives_its_extraction(monkeypatch):
    extract_t5(monkeypatch)
    biorepo.write(decision("cl1-T5-276fbb61", "verified"))
    drop_candidates()
    # No run — the extraction is gone — but the record is still a record,
    # kept with its decision, and a later decision about it still resolves.
    assert witness.runs() == []
    assert [c.id for c in witness.new_candidates()] == ["cl1-T5-276fbb61"]
    again = biorepo.write(decision("cl1-T5-276fbb61", "rejected", rejectReason="on reflection, a placeholder"))
    assert again.status == "rejected" and len(biorepo.read().records) == 1


def test_a_decision_is_kept_as_sent_one_row_each_signed_by_its_reviewer():
    fetch_t5()
    biorepo.write(decision("r-T5-1", "verified"))
    [row] = decision_rows()
    assert row["recordId"] == "r-T5-1" and list(biorepo.decisions()) == ["r-T5-1"]
    assert "quote" not in row, "None is left out, not written as null"

    async def signed() -> list[str]:
        async with db.session() as s:
            return list((await s.execute(select(t.decisions.c.created_by))).scalars())

    assert db.run(signed()) == ["sean"]


def test_every_decision_and_every_undo_stays_a_row_and_the_newest_holds():
    fetch_t5()
    biorepo.write(decision("r-T5-1", "verified"))
    biorepo.write(decision("r-T5-1", "rejected", rejectReason="on reflection"))
    biorepo.write(decision("r-T5-1", "unverified", provenance="unverified"))
    assert [r["status"] for r in decision_rows()] == ["verified", "rejected", "unverified"]
    assert "r-T5-1" not in biorepo.decisions()

    async def count() -> int:
        async with db.session() as s:
            return (await s.execute(select(func.count()).select_from(t.decisions))).scalar_one()

    assert db.run(count()) == 3


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
    raw = json.loads(Path(__file__).with_name("fixtures").joinpath("test-corpus.json").read_text())
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


# ── the structure the curators recorded (OF-BLD-012.1 F1.3) ────────────
#
# `write` builds the raw dict anchoring reads. Until F1.3 it passed the
# value, the unit and the quote and nothing else, so a promotion on a record
# whose source states a range met a midpoint that is not in the sentence.


def test_gold_on_a_record_whose_source_states_a_range_anchors_on_that_range():
    # r-T5-1: the curators recorded 7-10 days and wrote the midpoint down.
    rec = load_corpus().record("r-T5-1")
    assert rec["range"] == {"low": 7, "high": 10} and rec["value"] == 8.5
    fetch_saying("T5", "r-T5-1", f"In our hands, {rec['quote']}.")
    stored = biorepo.write(
        decision("r-T5-1", "verified", provenance="gold", gold=Quantity(value=8.5, unit="d"))
    )
    assert stored.status == "verified"
    assert biorepo.decisions()["r-T5-1"].quote == rec["quote"]


def test_gold_on_a_record_the_paper_wrote_in_another_unit_anchors():
    # r-T2-1: curated 0.015 g/L; the paper wrote "a maximum of 15 mg/L".
    rec = load_corpus().record("r-T2-1")
    assert rec["value"] == 0.015 and rec.get("range") is None
    fetch_saying("T2", "r-T2-1", f"Secretion improved, {rec['quote']}.")
    stored = biorepo.write(
        decision("r-T2-1", "verified", provenance="gold", gold=Quantity(value=0.015, unit="g L\u207b\u00b9"))
    )
    assert stored.status == "verified"


def test_gold_on_a_recorded_absence_reads_its_zero_from_the_sentence():
    # r-T3-3: value 0, negativeResult, and a quote with no digit anywhere in
    # it — the negation rule is the only thing that can anchor it.
    rec = load_corpus().record("r-T3-3")
    assert rec["value"] == 0 and rec["negativeResult"] is True
    assert not any(ch.isdigit() for ch in rec["quote"])
    fetch_saying("T3", "r-T3-3", f"Even after prolonged incubation, {rec['quote']}.")
    stored = biorepo.write(decision("r-T3-3", "verified", provenance="gold"))
    assert stored.status == "verified"


def test_gold_on_a_value_derived_from_the_quote_still_refuses_with_a_reason():
    # r-T4-1: a rate of 0.24 h-1 read off "0.12 h-1". Doubling is
    # arithmetic the sentence did not do, and no recorded structure licenses
    # it — the reviewer is told to edit the value or record the derivation.
    rec = load_corpus().record("r-T4-1")
    fetch_saying("T4", "r-T4-1", f"The particle was {rec['quote']}.")
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T4-1", "verified", provenance="gold"))
    assert caught.value.rule == "quote"
    assert "derived from the quote" in caught.value.why


# ── the check the browser asks before the keystroke (F1.5) ─────────────


def test_a_dry_run_answers_the_same_and_writes_nothing():
    fetch_t5()
    good = decision("r-T5-3", "verified")
    assert biorepo.write(good, dry_run=True).status == "verified"
    assert nothing_decided(), "a dry run is a question, not a decision"
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision(unfetched_seed_record(), "verified"), dry_run=True)
    assert caught.value.rule == "fulltext"
    assert nothing_decided()
    # And the real write still stores it.
    biorepo.write(good)
    assert "r-T5-3" in biorepo.decisions()


def test_the_check_endpoint_answers_ok_or_the_rule(client):
    fetch_t5()
    ok = client.post("/api/biorepo/check", json=decision("r-T5-3", "verified").model_dump()).json()
    assert ok == {"ok": True, "rule": None, "why": None}
    bad = client.post(
        "/api/biorepo/check",
        json=decision(unfetched_seed_record(), "verified").model_dump(),
    )
    assert bad.status_code == 200, "a refusal is an answer, not an error"
    assert bad.json()["ok"] is False and bad.json()["rule"] == "fulltext"
    assert "full text" in bad.json()["why"]
    assert biorepo.decisions() == {}, "asking must never write"


# ── a decision is signed by a person (OF-BLD-012.1 F2) ─────────────────


@pytest.mark.parametrize("name", ["you", "me", "Reviewer", "USER", "test", "x", " "])
def test_refuses_a_reviewer_who_is_not_a_person(name):
    # README: "a verified record is one a named reviewer promoted against a
    # quote in the paper's own text". A corpus signed 'you' is signed by
    # nobody, and the decisions are the record of who decided what.
    fetch_t5()
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("r-T5-3", "verified", reviewer=name))
    assert caught.value.rule == "reviewer"
    assert nothing_decided()


def test_a_named_reviewer_is_stored():
    fetch_t5()
    stored = biorepo.write(decision("r-T5-3", "verified", reviewer="Sean Creighton"))
    assert stored.reviewer == "Sean Creighton"
    assert biorepo.decisions()["r-T5-3"].reviewer == "Sean Creighton"


# ── §6.9 — a typed number is held to the sentence like any other ────────


def test_a_correction_with_no_quote_anchors_on_the_records_own_sentence():
    # A decision that carried a corrected value and no quote skipped
    # anchoring altogether, so a reviewer-typed number reached biorepo.json
    # — and corpus.json, through the export's merge — without appearing in
    # any sentence the paper wrote. The record's own sentence is the one it
    # has to sit in, whatever the decision's status.
    rec = load_corpus().record("r-T5-1")
    fetch_saying("T5", "r-T5-1", f"In our hands, {rec['quote']}.")
    assert "9.9" not in rec["quote"]
    for status in ("verified", "unverified"):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(decision("r-T5-1", status, corrected=Quantity(value=9.9, unit="d")))
        assert caught.value.rule == "quote", status
    # An endpoint of the range the sentence states is in the sentence.
    stored = biorepo.write(decision("r-T5-1", "verified", corrected=Quantity(value=7, unit="d")))
    assert stored.corrected == Quantity(value=7, unit="d")
    assert stored.quote == rec["quote"], "the sentence the correction stands on is stored with it"


def test_a_correction_on_an_unfetched_paper_is_refused_for_want_of_words():
    rid = next(
        r["id"] for r in load_corpus().records
        if r["paperId"] != "T5" and identified(r["paperId"]) and isinstance(r["value"], (int, float))
    )
    rec = load_corpus().record(rid)
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision(rid, "unverified", corrected=Quantity(value=rec["value"], unit=rec["unit"])))
    assert caught.value.rule == "fulltext"


def test_an_undecided_decision_withdraws_the_one_it_replaces(monkeypatch):
    # An undo posts the record as it was before the decision: status
    # 'unverified', nothing typed. That is a withdrawal, not a decision to
    # keep — the file stored it as one, and the candidate copy beside it, so
    # Witness counted an undone rejection as decided on every checkout.
    extract_t5(monkeypatch)
    biorepo.write(decision("cl1-T5-276fbb61", "rejected", rejectReason="a placeholder row"))
    assert "cl1-T5-276fbb61" in biorepo.decisions() and len(biorepo.records()) == 1
    echoed = biorepo.write(decision("cl1-T5-276fbb61", "unverified", provenance="unverified"))
    assert echoed.status == "unverified"
    assert "cl1-T5-276fbb61" not in biorepo.decisions()
    assert biorepo.records() == [], "the copy goes with the decision it sat beside"
    # Withdrawing what was never decided is nothing, not an error; and
    # dry_run answers without adding a row.
    before = decision_rows()
    biorepo.write(decision("cl1-T5-276fbb61", "unverified", provenance="unverified"))
    biorepo.write(decision("cl1-T5-276fbb61", "unverified", provenance="unverified"), dry_run=True)
    assert decision_rows() == before


def test_resolving_a_candidate_reads_its_own_papers_row_and_no_other(monkeypatch):
    # The id names the paper — 'cl1-T5-276fbb61' — so there is one row to
    # read. `_resolve` once read and validated every paper's candidates on
    # every call, and Guild asks /check twice per card.
    extract_t5(monkeypatch)
    monkeypatch.setattr(extract, "all_cached", lambda: pytest.fail("scanned the whole cache"))
    stored = biorepo.write(decision("cl1-T5-276fbb61", "rejected", rejectReason="a placeholder row"))
    assert stored.recordId == "cl1-T5-276fbb61"
    # A seed record never touches the extractor's cache at all.
    fetch_saying("T5", "r-T5-3", "Selection used paromomycin.")
    assert biorepo.write(decision("r-T5-3", "verified")).status == "verified"


def test_a_candidate_id_names_a_paper_id_and_nothing_else(monkeypatch):
    # The paper segment of a candidate id picks the paper whose candidates
    # are read. Read as `.+` it would have let 'cl1-../../x-deadbeef' ask for
    # a paper id no paper can have.
    fetch_t5()
    opened: list[str] = []
    real = extract.cached

    def watching(paper_id):
        opened.append(paper_id)
        return real(paper_id)

    monkeypatch.setattr(extract, "cached", watching)
    with pytest.raises(biorepo.WriteRefused) as caught:
        biorepo.write(decision("cl1-../../x-deadbeef", "rejected", rejectReason="no"))
    assert caught.value.rule == "record"
    assert opened == [], "no paper's candidates were even asked for"
