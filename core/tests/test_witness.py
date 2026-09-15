"""match_run on a fixture (OF-BLD-012 §6.2, §6.3).

A hand-written seed and hand-written candidates, so every outcome in the
browser's vocabulary is produced by a case built to produce it and nothing
else: match, span_error, value_mismatch, unit_error, miss. Then the rules
around the score — a paper the extractor never ran over is not scored, a
candidate the seed has no record for is new and unscored — and the endpoint
that recomputes the run from the cache. Offline and free.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import biorepo, extract, intake, witness
from openferment_core.api import app
from openferment_core.models import Candidate, DroppedCandidate, ExtractRun, Overlay, Quantity, ReviewDecision
from openferment_core.units import to_si

# ── a seed nobody curated ──────────────────────────────────────────────

SEED = [
    {"id": "r-P1-1", "paperId": "P1", "field": "titer_secreted", "value": 4.2, "unit": "g L⁻¹"},
    {"id": "r-P1-2", "paperId": "P1", "field": "growth_rate_mu", "value": 0.12, "unit": "h⁻¹"},
    {"id": "r-P1-3", "paperId": "P1", "field": "time_to_colony", "value": 8.5, "unit": "d"},
    {"id": "r-P1-4", "paperId": "P1", "field": "expression_pct_tsp", "value": 0.2, "unit": "% TSP"},
    {"id": "r-P1-5", "paperId": "P1", "field": "kinase_identity", "value": "Fam20C", "unit": ""},
    {"id": "r-P2-1", "paperId": "P2", "field": "titer_secreted", "value": 1.0, "unit": "g L⁻¹"},
    {"id": "r-P3-1", "paperId": "P3", "field": "titer_secreted", "value": 9.0, "unit": "g L⁻¹"},
]


def cand(paper: str, field: str, value, unit: str, n: int = 1) -> Candidate:
    if isinstance(value, str):
        si = Quantity(value=value, unit="")
    else:
        sv, su = to_si(value, unit)
        si = Quantity(value=sv, unit=su)
    return Candidate(
        id=f"hk1-{paper}-{n}",
        paperId=paper,
        sectionId="s1",
        quote="a sentence the paper wrote",
        field=field,
        value=value,
        unit=unit,
        si=si,
        confidence=0.8,
    )


def dropped(paper: str, field: str, value, unit: str, rule: str = "quote") -> DroppedCandidate:
    return DroppedCandidate(paperId=paper, sectionId="s1", field=field, value=value, unit=unit, rule=rule)


CANDIDATES = [
    cand("P1", "titer_secreted", 4200, "mg/L", 1),  # match: 4200 mg/L is 4.2 g/L
    cand("P1", "growth_rate_mu", 0.20, "h⁻¹", 2),  # value_mismatch: same family, 67 % off
    cand("P1", "expression_pct_tsp", 2.0, "mg/L", 3),  # unit_error: a titre where a fraction belongs
    cand("P1", "kinase_identity", "CK2", "", 4),  # categorical value_mismatch
    cand("P1", "titer_intracellular", 1.1, "g/L", 5),  # new: no seed record for this field
    cand("P3", "titer_secreted", 9.0, "g/L", 1),  # on a paper that was not extracted
]
DROPPED = [
    dropped("P1", "time_to_colony", 8.5, "d"),  # value agreed, quote failed → span_error
    dropped("P1", "growth_rate_mu", 0.12, "h⁻¹", rule="range"),  # not a quote failure → ignored
]


def outcomes(run: ExtractRun) -> dict[str, str]:
    return {r.goldRecordId: r.outcome for r in run.results}


@pytest.fixture
def run() -> ExtractRun:
    return witness.match_run(CANDIDATES, SEED, papers={"P1", "P2"}, dropped=DROPPED)


# ── one case per outcome ───────────────────────────────────────────────


def test_a_candidate_within_two_percent_after_conversion_is_a_match(run):
    assert outcomes(run)["r-P1-1"] == "match"
    extracted = next(r.extracted for r in run.results if r.goldRecordId == "r-P1-1")
    # As the candidate wrote it; the helper here does not normalise units.
    assert extracted == Quantity(value=4200, unit="mg/L")


def test_same_family_no_agreement_is_a_value_mismatch(run):
    assert outcomes(run)["r-P1-2"] == "value_mismatch"


def test_a_different_family_is_a_unit_error(run):
    assert outcomes(run)["r-P1-3"] != "unit_error"  # that one is the span case below
    assert outcomes(run)["r-P1-4"] == "unit_error"


def test_a_refused_quote_whose_value_agreed_is_a_span_error(run):
    # Dropped from BioRepo, still counted here: the extractor produced it.
    assert outcomes(run)["r-P1-3"] == "span_error"
    extracted = next(r.extracted for r in run.results if r.goldRecordId == "r-P1-3")
    assert extracted == Quantity(value=8.5, unit="d")


def test_a_refusal_for_any_other_rule_is_not_a_span_error():
    only_range = [d for d in DROPPED if d.rule == "range"]
    run = witness.match_run([], SEED, papers={"P1"}, dropped=only_range)
    assert outcomes(run)["r-P1-2"] == "miss"


def test_nothing_for_the_field_is_a_miss(run):
    assert outcomes(run)["r-P2-1"] == "miss"
    assert next(r.extracted for r in run.results if r.goldRecordId == "r-P2-1") is None


def test_categorical_values_compare_case_insensitively():
    run = witness.match_run([cand("P1", "kinase_identity", "fam20c", "")], SEED, papers={"P1"})
    assert outcomes(run)["r-P1-5"] == "match"


def test_a_categorical_disagreement_is_a_value_mismatch(run):
    assert outcomes(run)["r-P1-5"] == "value_mismatch"


def test_match_beats_every_other_outcome():
    both = [cand("P1", "titer_secreted", 40, "g/L", 1), cand("P1", "titer_secreted", 4.2, "g/L", 2)]
    run = witness.match_run(both, SEED, papers={"P1"})
    assert outcomes(run)["r-P1-1"] == "match"


def test_the_tolerance_is_two_percent():
    assert outcomes(witness.match_run([cand("P1", "titer_secreted", 4.28, "g/L")], SEED, papers={"P1"}))["r-P1-1"] == "match"
    assert outcomes(witness.match_run([cand("P1", "titer_secreted", 4.30, "g/L")], SEED, papers={"P1"}))["r-P1-1"] == "value_mismatch"


# ── what is and is not scored ──────────────────────────────────────────


def test_only_extracted_papers_are_scored(run):
    # P3 has a perfect candidate and was never extracted: not a match, not a
    # miss — not scored.
    assert "r-P3-1" not in outcomes(run)
    assert set(outcomes(run)) == {"r-P1-1", "r-P1-2", "r-P1-3", "r-P1-4", "r-P1-5", "r-P2-1"}


def test_a_scored_paper_with_no_candidates_misses_everything():
    run = witness.match_run([], SEED, papers={"P2"})
    assert outcomes(run) == {"r-P2-1": "miss"}


def test_new_records_are_unscored_and_not_false_positives(run):
    assert run.falsePositives == []
    new = witness.new_records(CANDIDATES, SEED, papers={"P1", "P2"})
    assert [c.id for c in new] == ["hk1-P1-5"]
    assert all(c.status == "unverified" for c in new)


def test_false_positives_are_only_what_a_reviewer_rejected():
    def d(rid, status, reason=None):
        return ReviewDecision(status=status, provenance="unverified", reviewer="sean",
                              recordId=rid, at="2026-09-14T00:00:00Z", rejectReason=reason)
    decisions = {
        "hk1-P1-5": d("hk1-P1-5", "rejected", "not a titre — a loading control"),
        "hk1-P1-1": d("hk1-P1-1", "verified"),
    }
    fps = witness.false_positives(CANDIDATES, decisions)
    assert [fp.id for fp in fps] == ["hk1-P1-5"]
    assert fps[0].field == "titer_intracellular" and fps[0].note == "not a titre — a loading control"
    assert witness.false_positives(CANDIDATES, {}) == []


def test_an_accepted_candidate_appended_to_the_corpus_is_not_scored_against_itself(monkeypatch):
    # export-corpus appends accepted candidates with source='biorepo'. They
    # must be neither gold to match against nor cover a field so it stops
    # being new: the seed is what is scored.
    appended = {**SEED[0], "id": "hk1-P1-9", "field": "titer_intracellular", "value": 1.1,
                "unit": "g L⁻¹", "source": "biorepo"}
    corpus = type("C", (), {"records": SEED + [appended]})()
    monkeypatch.setattr(witness, "load_corpus", lambda: corpus)
    seed = witness.seed_records()
    assert [r["id"] for r in seed] == [r["id"] for r in SEED]
    run = witness.match_run(CANDIDATES, seed, papers={"P1"})
    assert "hk1-P1-9" not in outcomes(run)
    assert [c.id for c in witness.new_records(CANDIDATES, seed, papers={"P1"})] == ["hk1-P1-5"]


SIBLINGS = [
    {"id": "r-F4-1", "paperId": "F4", "field": "expression_pct_tsp", "value": 38, "unit": "% TSP"},
    {"id": "r-F4-2", "paperId": "F4", "field": "expression_pct_tsp", "value": 36, "unit": "% TSP"},
    {"id": "r-F4-3", "paperId": "F4", "field": "expression_pct_tsp", "value": 13, "unit": "% TSP"},
]


def test_one_candidate_scores_one_record():
    # Three curated figures for one field; the extractor found the first.
    # That is one match and two misses — not one match and two mismatches
    # "extracted 38" against records it never addressed.
    one = [cand("F4", "expression_pct_tsp", 38, "% TSP", 1)]
    assert outcomes(witness.match_run(one, SIBLINGS, papers={"F4"})) == {
        "r-F4-1": "match", "r-F4-2": "miss", "r-F4-3": "miss"}
    two = one + [cand("F4", "expression_pct_tsp", 36, "% TSP", 2)]
    assert outcomes(witness.match_run(two, SIBLINGS, papers={"F4"})) == {
        "r-F4-1": "match", "r-F4-2": "match", "r-F4-3": "miss"}
    # Matches are taken first, so a candidate is not spent on a mismatch with
    # an earlier record when it matches a later one.
    late = [cand("F4", "expression_pct_tsp", 13, "% TSP", 1)]
    assert outcomes(witness.match_run(late, SIBLINGS, papers={"F4"})) == {
        "r-F4-1": "miss", "r-F4-2": "miss", "r-F4-3": "match"}
    # Two curated records with the same value and one extraction: one match.
    twins = [dict(SIBLINGS[0]), {**SIBLINGS[0], "id": "r-F4-9"}]
    assert outcomes(witness.match_run(one, twins, papers={"F4"})) == {"r-F4-1": "match", "r-F4-9": "miss"}
    # A wrong candidate is spent on one sibling as a mismatch; the rest miss.
    wrong = [cand("F4", "expression_pct_tsp", 99, "% TSP", 1)]
    assert outcomes(witness.match_run(wrong, SIBLINGS, papers={"F4"})) == {
        "r-F4-1": "value_mismatch", "r-F4-2": "miss", "r-F4-3": "miss"}


def test_the_run_is_the_browsers_shape(run):
    assert run.run == "haiku-1"
    body = run.model_dump()
    assert set(body) == {"run", "results", "falsePositives"}
    assert set(body["results"][0]) == {"goldRecordId", "outcome", "extracted"}


# ── the endpoint, from the cache ───────────────────────────────────────

GOOD = {
    "candidates": [
        {
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
        },
        {  # quote not verbatim → dropped, and no seed value agrees → nothing
            "sectionId": "t1", "field": "time_to_colony", "value": 9, "unit": "d",
            "quote": "nine days, paraphrased", "isPrimary": True, "confidence": 0.8,
        },
    ]
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(extract, "FIXTURE_DIR", tmp_path / "no-saved-responses")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


@pytest.fixture
def client():
    return TestClient(app)


def test_runs_are_empty_until_something_is_extracted(client):
    assert client.get("/api/witness/runs").json() == []
    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    assert overlay.runs == [] and overlay.candidates == []


def test_runs_recompute_from_the_cache_against_the_seed(client, monkeypatch):
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: "structural")
    assert client.post("/api/intake/B5/fetch").json()["status"] == "complete"
    monkeypatch.setattr(extract, "call_model", lambda *_: (GOOD, extract.Usage()))
    assert client.post("/api/intake/B5/extract").status_code == 200

    runs = [ExtractRun.model_validate(r) for r in client.get("/api/witness/runs").json()]
    assert [r.run for r in runs] == ["haiku-1"]
    # B5's three seed records are time_to_colony; the extractor produced a
    # titre for it and a paraphrased colony time that anchoring refused with
    # a value the seed does not hold — so three misses, honestly.
    assert outcomes(runs[0]) == {"r-B5-1": "miss", "r-B5-2": "miss", "r-B5-3": "miss"}

    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    assert [r.run for r in overlay.runs] == ["haiku-1"]
    # The titre is new to B5 — the corpus growing — and it is in the overlay
    # for Guild, not in the score.
    assert [c.field for c in overlay.candidates] == ["titer_secreted"]
    assert overlay.candidates[0].id == "hk1-B5-a07dd73c"
    assert runs[0].falsePositives == []


def test_a_decision_stays_with_its_content_across_a_re_extraction(client, monkeypatch):
    # Ids are content-addressed. A reviewer rejects the titre; the paper is
    # re-extracted with --force and the extractor now says something else.
    # The rejection stays with the sentence it was about (kept as the file's
    # copy, no longer a false positive the extractor produces), and the new
    # candidate arrives undecided under its own id.
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: "structural")
    client.post("/api/intake/B5/fetch")
    monkeypatch.setattr(extract, "call_model", lambda *_: (GOOD, extract.Usage()))
    client.post("/api/intake/B5/extract")
    biorepo.write(ReviewDecision(status="rejected", provenance="unverified", reviewer="sean",
                                 recordId="hk1-B5-a07dd73c", at="2026-09-15T00:00:00Z",
                                 rejectReason="a placeholder row"))
    assert [fp.id for fp in witness.runs()[0].falsePositives] == ["hk1-B5-a07dd73c"]

    other = {"candidates": [{
        "sectionId": "t1", "field": "titer_secreted", "value": 9, "unit": "mg L-1",
        "quote": "Placeholder B | 9 | mg L-1", "isPrimary": True, "confidence": 0.7,
    }]}
    monkeypatch.setattr(extract, "call_model", lambda *_: (other, extract.Usage()))
    assert client.post("/api/intake/B5/extract?force=true").status_code == 200

    runs_, candidates, decisions = witness.overlay_bundle()
    assert [(c.id, c.value) for c in candidates] == [("hk1-B5-93a4e8a2", 9), ("hk1-B5-a07dd73c", 7)]
    assert "hk1-B5-a07dd73c" in decisions and "hk1-B5-93a4e8a2" not in decisions
    # The rejected 7 is still a false positive of the run: the file keeps it
    # and Witness measures what the extractor produced, then and now.
    assert [fp.id for fp in runs_[0].falsePositives] == ["hk1-B5-a07dd73c"]
    stored = biorepo.write(ReviewDecision(status="verified", provenance="unverified", reviewer="sean",
                                          recordId="hk1-B5-93a4e8a2", at="2026-09-15T01:00:00Z"))
    assert stored.status == "verified"
    assert sorted(c.value for c in biorepo.records()) == [7, 9]
