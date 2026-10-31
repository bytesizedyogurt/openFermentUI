"""The evidence pool (OF-BLD-014 §3.4; OF-BLD-007 §10.3): what Postdoc may cite.

Retrieval decides answer quality, and a bad retrieval is invisible downstream:
the model gets the wrong records, writes a confident answer citing them, every
citation resolves, the validator passes it, and the answer is still wrong.
These rules are where that can be caught. Then the pool's records themselves:
a candidate nobody decided is `unverified`, one a reviewer decided stands as
the decision left it, and a rejected one is never there.

Offline and free. The papers and candidates are fictional placeholders about
imaginary strains, written so a rule has something to act on; nothing here is
a measurement.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from openferment_core import biorepo, evidence_pool, extract, module_stores
from openferment_core.evidence_pool import tokenize
from openferment_core.literature import kit
from openferment_core.models import Candidate, ExtractResponse, Quantity, ReviewDecision, Usage
from openferment_core.units import to_si

AT = "2026-10-30T12:00:00Z"
NOTE = [{"id": "s1", "heading": "Curation note"}]
PAPERS = [
    {"id": "T5", "title": "A placeholder paper on colonies of imaginary strains", "year": 2026, "sections": NOTE},
    {"id": "T2", "title": "A placeholder paper on a secreted product", "year": 2026, "sections": NOTE},
    {"id": "T3", "title": "A placeholder paper on an absence", "year": 2026, "sections": NOTE},
    {"id": "T4", "title": "A placeholder paper on growth", "year": 2026, "sections": NOTE},
]


def cand(cid: str, paper: str, field: str, value, unit: str, quote: str, **extra) -> Candidate:
    sv, su = to_si(value, unit)
    return Candidate(id=cid, paperId=paper, sectionId="s1", quote=quote, field=field, value=value, unit=unit,
                     si=Quantity(value=sv, unit=su), confidence=0.8, **extra)


CANDIDATES = [
    cand("cl1-T5-00000001", "T5", "time_to_colony", 8.5, "d", "colonies appear on selection in 7–10 days for strain ab12"),
    cand("cl1-T5-00000002", "T5", "time_to_colony", 8.5, "d", "7–10 days for strain ab12 and strain ef5"),
    cand("cl1-T5-00000003", "T5", "time_to_colony", 17.5, "d", "versus 15–20 days for strain cd34"),
    cand("cl1-T2-00000001", "T2", "titer_secreted", 0.015, "g L⁻¹", "reaching a maximum of 15 mg/L"),
    cand("cl1-T3-00000003", "T3", "secreted_fraction", 0, "% of total expressed",
         "the knockout strain hardly secreted any product at all and kept it in the cells", negativeResult=True),
    cand("cl1-T4-00000001", "T4", "growth_rate_mu", 0.24, "h⁻¹", "a specific growth rate of 0.12 h-1 in the first phase"),
]


def decision(record_id: str, status: str, **extra) -> ReviewDecision:
    return ReviewDecision(**{"status": status, "provenance": "unverified", "reviewer": "A. Reader", "recordId": record_id,
                             "at": AT, **extra})


@pytest.fixture
def pool():
    return evidence_pool.build(CANDIDATES, {}, papers=PAPERS)


# ── the words ──────────────────────────────────────────────────────────


def test_tokenize_keeps_short_discriminative_tokens():
    # 'cw15', 'od600' and 'ph' are two to five characters and are exactly the
    # terms that tell one record from another. A minimum length would throw
    # them away.
    assert "cw15" in tokenize("Titre in cw15")
    assert "od600" in tokenize("OD600 at harvest")
    assert "ph" in tokenize("pH held at 6.8")


def test_tokenize_drops_stop_words():
    assert tokenize("What is the growth rate") == ["growth", "rate"]


# ── search ─────────────────────────────────────────────────────────────


def test_a_pool_of_nothing_finds_nothing():
    empty = evidence_pool.build([], {})
    assert empty.records == [] and empty.search("specific growth rate in the first phase") == []


def test_every_record_resolves_to_a_paper(pool):
    # A record citing a paper the pool cannot name would make a claim the UI
    # cannot render.
    assert pool.records and all(pool.paper(r["paperId"]) for r in pool.records)


def test_finds_the_right_record_for_a_covered_question(pool):
    hits = pool.search("What specific growth rate does strain gh67k reach in the first phase?")
    assert hits, "a question the pool covers must return evidence"
    assert hits[0]["field"] == "growth_rate_mu", f"top hit is {hits[0]['id']} ({hits[0]['field']})"


def test_a_question_the_pool_does_not_cover_finds_nothing(pool):
    # The honest failure: returning padded-out hits here is how a decline
    # becomes an answer.
    assert pool.search("quantum chromodynamics lattice gauge theory") == []


def test_a_lone_single_term_hit_is_not_evidence(pool):
    # The pool holds nothing about brazzein; one record shares the word
    # "knockout" with the question, and a single coincidental word match is a
    # coincidence the model would cite.
    assert pool.search("What brazzein output was reported for the knockout?") == []


def test_the_coverage_rule_keeps_a_genuine_two_term_hit(pool):
    hits = pool.search("Has anyone measured colonies on selection?")
    assert hits, "a covered question must keep its evidence"
    assert len(hits[0]["matchedTerms"]) >= 2


def test_short_questions_are_exempt_from_the_coverage_rule(pool):
    # Two content tokens legitimately match on one term.
    assert pool.search("knockout strain")


def test_search_holds_the_cap(pool):
    assert len(pool.search("strain colonies days selection", limit=2)) <= 2
    assert len(pool.search("strain colonies days selection", limit=30)) <= evidence_pool.MAX_LIMIT


def test_hits_are_ranked_and_carry_their_reason(pool):
    hits = pool.search("secreted product of the knockout strain")
    assert hits
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True), "hits must come back ranked"
    assert all("matchedTerms" in h for h in hits), "every hit says which query terms it matched"


def test_every_hit_carries_what_a_claim_needs(pool):
    for hit in pool.search("colonies on selection in days"):
        for name in ("id", "paperId", "field", "value", "unit", "quote", "provenance"):
            assert name in hit, f"{hit.get('id')} is missing {name}"


def test_a_question_with_no_words_lists_the_records_in_pool_order(pool):
    listed = [r["id"] for r in pool.search("")]
    assert listed == [c.id for c in CANDIDATES]
    assert [r["id"] for r in pool.search("the and of")] == listed, "stop words alone are no words"
    assert [r["id"] for r in pool.search("", field="titer_secreted")] == ["cl1-T2-00000001"]


# ── the records, as the decisions leave them ───────────────────────────


def test_an_undecided_candidate_is_unverified(pool):
    rec = pool.record("cl1-T2-00000001")
    assert (rec["provenance"], rec["status"], rec["source"]) == ("unverified", "unverified", "candidate")
    assert module_stores.record_state(rec["provenance"], rec["status"]) == "proposed"


def test_an_accepted_candidate_stands_as_the_decision_left_it():
    # The reviewer accepted it, with the paper's own number as a correction
    # and the sentence re-anchored; the label the browser sent is not what
    # the record carries, the decision's kind is (ADR-006).
    accepted = decision("cl1-T4-00000001", "verified", provenance="unverified",
                        corrected=Quantity(value=0.12, unit="h⁻¹"), quote="a specific growth rate of 0.12 h-1",
                        sectionId="s1")
    pool = evidence_pool.build(CANDIDATES, {"cl1-T4-00000001": accepted})
    rec = pool.record("cl1-T4-00000001")
    assert (rec["status"], rec["provenance"]) == ("verified", "verified")
    assert (rec["value"], rec["unit"], rec["quote"]) == (0.12, "h⁻¹", "a specific growth rate of 0.12 h-1")
    assert module_stores.record_state(rec["provenance"], rec["status"]) == "approved", "not awaiting review"


def test_a_gold_decision_makes_a_gold_record_and_a_rejection_none():
    gold = decision("cl1-T5-00000001", "verified", provenance="gold", gold=Quantity(value=8.5, unit="d"))
    rejected = decision("cl1-T5-00000002", "rejected", rejectReason="a duplicate of another sentence")
    pool = evidence_pool.build(CANDIDATES, {"cl1-T5-00000001": gold, "cl1-T5-00000002": rejected})
    assert pool.record("cl1-T5-00000001")["provenance"] == "gold"
    assert pool.record("cl1-T5-00000002") is None
    assert "cl1-T5-00000002" not in [r["id"] for r in pool.search("days for strain ab12 and strain ef5")]


def test_a_decision_is_the_provenance_its_kind_gives():
    assert biorepo.provenance_of(decision("x", "verified", provenance="curated")) == "verified"
    assert biorepo.provenance_of(decision("x", "verified", provenance="measured")) == "verified", "no person sets it"
    assert biorepo.provenance_of(decision("x", "verified", gold=Quantity(value=1, unit="d"))) == "gold"
    assert biorepo.provenance_of(decision("x", "rejected", rejectReason="no")) == "unverified"
    assert biorepo.provenance_of(decision("x", "unverified", corrected=Quantity(value=1, unit="d"))) == "unverified"


def test_the_project_pool_reads_its_candidates_its_decisions_and_its_documents_titles(monkeypatch):
    # The extractor's row for T4, a decision on one of its candidates, and a
    # copy kept with a decision whose extraction is gone (T9's row was
    # replaced), all read from the project's tables.
    extract._persist(ExtractResponse(paperId="T4", extractedAt=AT, candidates=[CANDIDATES[-1]], audit=[],
                                     usage=Usage(), calls=0))
    gone = cand("cl1-T9-00000001", "T9", "final_biomass_density", 3, "g L⁻¹", "the biomass reached 3 g/L")
    monkeypatch.setattr(kit, "documents", lambda project_id: [
        (SimpleNamespace(id="T4", title="A placeholder paper on growth", publication_year=2026), {})])
    accepted = decision("cl1-T4-00000001", "verified")
    from openferment_core import db, projects

    db.run(biorepo._keep(projects.current(), accepted, CANDIDATES[-1], undo=False))
    db.run(biorepo._keep(projects.current(), decision("cl1-T9-00000001", "verified"), gone, undo=False))
    pool = evidence_pool.load()
    assert sorted(pool.records_by_id) == ["cl1-T4-00000001", "cl1-T9-00000001"]
    assert pool.record("cl1-T4-00000001")["provenance"] == "verified"
    assert pool.record("cl1-T9-00000001")["status"] == "verified", "a decided record outlives its extraction"
    assert pool.paper("T4")["title"] == "A placeholder paper on growth" and pool.paper("T9") is None
