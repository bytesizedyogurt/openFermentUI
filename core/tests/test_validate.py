"""Validator tests (OF-BLD-007 §5, §10.5).

Written and passing BEFORE the first API call. The validator is the Rule 1
safety rail, and a safety rail you have not tested is a safety rail you are
hoping about. Every case here is a hand-written plan — good ones that must
survive intact, bad ones that must be dropped and counted — so the behaviour is
pinned against claims a human wrote rather than against whatever the model
happened to emit on the day.

Offline and free. No key, no network.
"""
from __future__ import annotations

import pytest

from openferment_core.models import weakest_provenance
from openferment_core.validate import decline_reason, find_number, validate_claims

# A tiny fixed corpus. Small on purpose: these tests are about the validator's
# rules, not about retrieval, and a fixture you can hold in your head is a
# fixture whose failures are readable.
RECORDS = {
    "r-A1-1": {"id": "r-A1-1", "paperId": "A1", "provenance": "curated"},
    "r-H4-3": {"id": "r-H4-3", "paperId": "H4", "provenance": "verified"},
    "r-O8-1": {"id": "r-O8-1", "paperId": "O8", "provenance": "industry-estimate"},
    "r-G1-1": {"id": "r-G1-1", "paperId": "G1", "provenance": "gold"},
}
PAPERS = {"A1": {"id": "A1"}, "H4": {"id": "H4"}, "O8": {"id": "O8"}, "G1": {"id": "G1"}}


def check(claims):
    return validate_claims(claims, RECORDS, PAPERS)


# ── the number detector ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "Titre reached 4.2 g/L",
        "about 4200 units",
        "roughly 1e6 cells",
        "a 12-fold improvement",
        "four point two grams per litre",
        "expression was twofold higher",
        "half of the total soluble protein",
        "an order of magnitude higher than the control",
        "the first of three runs",
        "yields around ½ the control",
        "reached 10% TSP",
    ],
)
def test_numbers_are_found_in_every_disguise(text):
    assert find_number(text) is not None, f"missed a number in {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "Titre in cw15 under mixotrophic conditions",
        "Secreted fraction for the strain in question",
        "Nobody has measured this in this host",
        "Often the tension between yield and purity decides the train",
        "Someone should reconsider this alone",
        "Phosphorylation state of bovine beta-casein as expressed in E. coli",
        "The wavelength used for the absorbance reading",
        # Identifiers carry digits without being quantities. A claim that cannot
        # name its strain is useless, and the first of these is the
        # specification's own worked example of a GOOD claim.
        "Titre in cw15 under mixotrophic conditions",
        "Expression in UVM4 relative to the parental line",
        "Optical density measured as OD600 at harvest",
        "Phosphorylation by CK2 in the E. coli system",
        "The CC-4350 background used throughout",
        "Elow47 before the UV mutagenesis step",
    ],
)
def test_ordinary_prose_is_not_flagged(text):
    """False positives are the failure mode that gets a validator switched off.

    'oneself', 'tension', 'often', 'alone' and 'wavelength' all contain a
    written numeral as a substring. A word-boundary rule that catches them
    would reject correct claims, and a rail that rejects correct output is a
    rail somebody disables.
    """
    assert find_number(text) is None, f"false positive on {text!r}"


# ── the four rejection rules ───────────────────────────────────────────


def test_a_good_claim_survives_intact():
    result = check(
        [
            {
                "id": "c1",
                "text": "Expression level in the cell-wall-deficient strain",
                "recordIds": ["r-A1-1"],
                "paperIds": ["A1"],
                "support": "direct",
            }
        ]
    )
    assert result.rejected == 0
    assert len(result.claims) == 1
    assert result.claims[0].text == "Expression level in the cell-wall-deficient strain"


def test_rule_one_a_claim_with_a_number_is_dropped():
    result = check(
        [
            {
                "id": "c1",
                "text": "Expression reached 0.2% TSP in the strain",
                "recordIds": ["r-A1-1"],
                "support": "direct",
            }
        ]
    )
    assert result.claims == []
    assert result.rejected == 1
    assert "contains a number" in result.reasons[0]


def test_the_rejected_claim_is_never_repaired():
    """The rule that matters most.

    A validator that strips the number and keeps the sentence produces prose
    the model never wrote, attached to citations chosen to support the prose it
    did write. Nothing that failed may come back in any form.
    """
    result = check(
        [
            {
                "id": "c1",
                "text": "Expression reached 0.2% TSP",
                "recordIds": ["r-A1-1"],
                "support": "direct",
            }
        ]
    )
    assert result.claims == [], "a rejected claim must not reappear repaired"
    assert not any("0.2" in c.text for c in result.claims)


def test_rule_two_an_unresolvable_record_id_is_dropped():
    result = check(
        [
            {
                "id": "c1",
                "text": "Secreted fraction in the host",
                "recordIds": ["r-DOES-NOT-EXIST"],
                "support": "direct",
            }
        ]
    )
    assert result.claims == []
    assert result.rejected == 1
    assert "do not exist" in result.reasons[0]


def test_a_claim_is_dropped_if_any_citation_is_a_ghost():
    # One real record does not rescue a hallucinated one. A partially-real
    # citation list is how a fabricated corroboration gets through.
    result = check(
        [
            {
                "id": "c1",
                "text": "Secreted fraction in the host",
                "recordIds": ["r-A1-1", "r-NOPE-9"],
                "support": "direct",
            }
        ]
    )
    assert result.claims == []
    assert result.rejected == 1


def test_rule_three_an_unresolvable_paper_id_is_dropped():
    result = check(
        [
            {
                "id": "c1",
                "text": "Secreted fraction in the host",
                "recordIds": ["r-A1-1"],
                "paperIds": ["ZZ9"],
                "support": "direct",
            }
        ]
    )
    assert result.claims == []
    assert "papers that do not exist" in result.reasons[0]


def test_rule_four_no_citation_and_not_admitting_it():
    result = check(
        [{"id": "c1", "text": "Secretion is generally poor in this host", "support": "direct"}]
    )
    assert result.claims == []
    assert "not 'unsupported'" in result.reasons[0]


def test_an_uncited_claim_that_admits_it_survives():
    """Naming an absence is a useful answer, but it has to be declared.

    "Nobody has measured this in this host" is exactly the answer §6 asks for.
    It is allowed through with no citations because it claims no measurement —
    what is not allowed is arriving at that state by omission.
    """
    result = check(
        [
            {
                "id": "c1",
                "text": "No study in the corpus measures this in a microalgal host",
                "recordIds": [],
                "support": "unsupported",
            }
        ]
    )
    assert len(result.claims) == 1
    assert result.claims[0].support == "unsupported"
    assert result.rejected == 0


def test_empty_claim_text_is_dropped():
    result = check([{"id": "c1", "text": "   ", "recordIds": ["r-A1-1"]}])
    assert result.claims == []
    assert result.rejected == 1


# ── provenance is computed, never model-chosen ─────────────────────────


def test_provenance_is_the_weakest_cited_record():
    result = check(
        [
            {
                "id": "c1",
                "text": "Market size for the product category",
                "recordIds": ["r-G1-1", "r-O8-1"],
                "support": "direct",
                "provenance": "gold",  # the model's own claim, to be ignored
            }
        ]
    )
    assert result.claims[0].provenance == "industry-estimate", (
        "a claim resting on one gold record and one industry estimate is an "
        "industry estimate, not gold"
    )


def test_the_models_provenance_field_is_discarded():
    result = check(
        [
            {
                "id": "c1",
                "text": "Expression level in the strain",
                "recordIds": ["r-A1-1"],  # curated
                "support": "direct",
                "provenance": "measured",  # a promotion the model is not allowed
            }
        ]
    )
    assert result.claims[0].provenance == "curated"


def test_weakest_provenance_ranks_measured_above_gold():
    assert weakest_provenance(["measured", "gold"]) == "gold"
    assert weakest_provenance(["measured"]) == "measured"
    assert weakest_provenance([]) == "unverified"


def test_an_unknown_provenance_class_is_treated_as_the_weakest():
    # An unrecognised provenance is not a reason for confidence.
    assert weakest_provenance(["gold", "something-new"]) == "demo"


def test_papers_are_derived_from_the_cited_records():
    """A claim can never point at a paper its evidence does not come from."""
    result = check(
        [
            {
                "id": "c1",
                "text": "Secreted fraction across both hosts",
                "recordIds": ["r-A1-1", "r-H4-3"],
                "paperIds": [],  # model named none
                "support": "direct",
            }
        ]
    )
    assert result.claims[0].paperIds == ["A1", "H4"]


# ── counting, and what happens when everything fails ───────────────────


def test_rejections_are_counted_and_reasoned():
    result = check(
        [
            {"id": "c1", "text": "Titre hit 4.2 g/L", "recordIds": ["r-A1-1"]},
            {"id": "c2", "text": "Fine claim", "recordIds": ["r-GHOST"]},
            {"id": "c3", "text": "Expression in the strain", "recordIds": ["r-A1-1"]},
        ]
    )
    assert len(result.claims) == 1
    assert result.rejected == 2
    assert len(result.reasons) == 2
    assert result.reasons[0].startswith("c1:")
    assert result.reasons[1].startswith("c2:")


def test_when_every_claim_is_rejected_the_plan_declines():
    result = check([{"id": "c1", "text": "Titre hit 4.2 g/L", "recordIds": ["r-A1-1"]}])
    reason = decline_reason(result, None)
    assert reason is not None
    assert "validation" in reason
    assert "fault in the answer, not in the corpus" in reason


def test_the_models_own_decline_wins():
    # It knows what it was missing and can say so specifically.
    result = check([])
    assert decline_reason(result, "No study measures this in a microalga.") == (
        "No study measures this in a microalga."
    )


def test_no_claims_and_no_rejections_declines_on_the_corpus():
    assert "corpus does not contain evidence" in decline_reason(check([]), None)


def test_a_valid_plan_does_not_decline():
    result = check(
        [{"id": "c1", "text": "Expression in the strain", "recordIds": ["r-A1-1"]}]
    )
    assert decline_reason(result, None) is None


# ── malformed model output must not crash the service ──────────────────


def test_missing_fields_are_handled_rather_than_raised():
    result = check([{}, {"text": "Expression in the strain"}, {"recordIds": ["r-A1-1"]}])
    assert result.rejected == 3
    assert result.claims == []


def test_a_claim_with_no_id_gets_a_positional_one():
    result = check([{"text": "Expression in the strain", "recordIds": ["r-A1-1"]}])
    assert result.claims[0].id == "c1"


def test_an_invalid_support_value_falls_back_rather_than_crashing():
    result = check(
        [{"id": "c1", "text": "Expression in the strain", "recordIds": ["r-A1-1"], "support": "vibes"}]
    )
    assert result.claims[0].support == "direct"
