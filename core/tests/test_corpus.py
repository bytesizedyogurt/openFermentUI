"""Retrieval tests (OF-BLD-007 §10.3).

Written before any API call, because retrieval quality decides answer quality
and a bad retrieval is invisible downstream: the model gets thirty wrong
records, writes a confident answer citing them, every citation resolves, the
validator passes it, and the answer is still wrong. None of the later safety
rails catch that. This is the only place it can be caught.

Offline and free. No key, no network.
"""
from __future__ import annotations

import pytest

from openferment_core.corpus import load_corpus, tokenize


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_corpus_loads_and_indexes(corpus):
    assert len(corpus.papers) > 100
    assert len(corpus.records) > 100
    assert all(r["paperId"] in corpus.papers_by_id for r in corpus.records), (
        "every record must resolve to a paper — a record citing a paper that is "
        "not in the corpus would produce a claim the UI cannot render"
    )


def test_tokenize_keeps_short_discriminative_tokens():
    # 'cw15', 'od600' and 'ph' are two to five characters and are exactly the
    # terms that tell one record from another here. A minimum length would
    # throw them away.
    assert "cw15" in tokenize("Titre in cw15")
    assert "od600" in tokenize("OD600 at harvest")
    assert "ph" in tokenize("pH held at 6.8")


def test_tokenize_drops_stop_words():
    assert tokenize("What is the growth rate") == ["growth", "rate"]


def test_finds_the_right_record_for_a_covered_question(corpus):
    hits = corpus.search(
        "What specific growth rate does Chlorella vulgaris reach in mixotrophic culture?"
    )
    assert hits, "a question the corpus covers must return evidence"
    top = hits[0]
    assert top["field"] == "growth_rate_mu", (
        f"top hit is {top['id']} ({top['field']}), expected a growth-rate record"
    )


def test_out_of_corpus_question_returns_nothing(corpus):
    # The honest failure. Nothing in a fermentation corpus is about lattice QCD,
    # and returning a padded-out top-30 here is how a decline becomes an answer.
    assert corpus.search("quantum chromodynamics lattice gauge theory") == []


def test_a_lone_single_term_hit_is_not_evidence(corpus):
    """The 'achieved' bug.

    'What titre has been achieved for brazzein?' used to return one record — a
    casein kinase measurement — scoring purely on the word "achieved", which
    appears in exactly one document. The corpus holds no brazzein record and no
    titre field, so the only correct result is nothing at all. A single
    coincidental word match is not weak evidence; it is a coincidence, and a
    model handed it will cite it.
    """
    assert corpus.search("What titre has been achieved for brazzein?") == []


def test_coverage_rule_does_not_drop_a_genuine_two_term_hit(corpus):
    """The rule must not overshoot.

    The algal-casein question is the one the golden path asks. Its best hits
    match on two terms and must survive — a coverage rule that silences a real
    absence-of-evidence answer would be worse than the noise it removes.
    """
    hits = corpus.search("Has anyone expressed a casein in an alga?")
    assert hits, "a covered question must keep its evidence"
    assert len(hits[0]["matchedTerms"]) >= 2


def test_short_questions_are_exempt_from_the_coverage_rule(corpus):
    # Two content tokens legitimately match on one term. Applying the rule here
    # would make short questions unanswerable.
    hits = corpus.search("mixotrophic growth")
    assert hits


def test_respects_the_evidence_cap(corpus):
    # §6 caps evidence at 30 records. The cap is the contract with the token
    # budget, and it is enforced here rather than trusted to the caller.
    hits = corpus.search("protein expression yield", limit=5)
    assert len(hits) <= 5
    assert len(corpus.search("protein expression yield", limit=30)) <= 30


def test_hits_are_ranked_and_carry_their_reason(corpus):
    hits = corpus.search("phosphorylation of beta-casein")
    assert hits
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True), "hits must come back ranked"
    assert all("matchedTerms" in h for h in hits), (
        "every hit says which query terms it matched, so a bad retrieval can be "
        "diagnosed from the logs rather than guessed at"
    )


def test_every_hit_carries_what_a_claim_needs(corpus):
    """A retrieved record must be renderable by the UI without a second lookup."""
    for hit in corpus.search("expression level total soluble protein", limit=10):
        for field in ("id", "paperId", "field", "value", "unit", "quote", "provenance"):
            assert field in hit, f"{hit.get('id')} is missing {field}"
        assert hit["provenance"], "a record with no provenance cannot be ticked"


def test_empty_and_whitespace_questions_return_nothing(corpus):
    assert corpus.search("") == []
    assert corpus.search("   ") == []
    assert corpus.search("the and of") == [], "a question of only stop words has no terms"
