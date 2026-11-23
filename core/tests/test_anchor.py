"""Anchoring — the mirror of Rule 1 (OF-BLD-012 §2.4, §10.5).

Written and passing BEFORE the first extraction call, for the same reason the
claim validator was: this is the rail that keeps a number the model invented
out of BioRepo, and a rail you have not tested is a rail you are hoping about.
Every case is a hand-written candidate against a hand-written paper — good
ones that must anchor unchanged, and at least one bad one per rule that must
be refused with that rule's code.

The ontology and unit tables are the real ones, read from corpus.json the way
the service reads them. Offline and free.
"""
from __future__ import annotations

import re

import pytest

from openferment_core import units
from openferment_core.units import tables
from openferment_core.validate import (
    ANCHOR_RULES,
    MAX_QUOTE_CHARS,
    anchor_all,
    anchor_candidate,
    normalize_text,
    parse_numbers,
    parse_quantities,
)

# A paper nobody wrote. Two prose sections and one table, with the spellings a
# real fetch produces: 'L-1' for L⁻¹, an en dash in a range, a soft hyphen
# left behind by a PDF, and a categorical mention.
SECTIONS = [
    {
        "id": "abstract",
        "heading": "Abstract",
        "text": "An imaginary protein was secreted by an imaginary yeast.",
    },
    {
        "id": "s3",
        "heading": "Results › Expression",
        "text": (
            "The secreted titre reached 4.20 g L-1 after 72 h in the fed-batch run, "
            "compared with 0.15 g L-1 in shake flasks. Intracellular product amounted to "
            "12% of total soluble protein. The specific growth rate was 0.12 h-1. "
            "Phosphorylation at Ser15 was confirmed by LC-ESI-MS. The kinase responsible "
            "was Fam20C. Colonies appeared in 7–10 days. A soft­hyphenated word."
        ),
    },
    {
        "id": "s4",
        "heading": "Results \u203a Structure the curators recorded",
        "text": (
            "Secretion in the flask line ran 12-15 mg L-1 across the series. "
            "Across the survey, yields ran 0.6 mg L-1 to 1 g L-1 in five yeast studies. "
            "The recombinant protein was not phosphorylated. "
            "All eight phosphoserine sites were substituted with aspartate. "
            "Secretion improved roughly three-fold over the parent strain. "
            "The analogue sold at about USD 12 thousand/kg in 2025. "
            "The particle was approximately spherical, radius ~70 nm. "
            "It carried the same degree of phosphorylation as the animal-derived protein."
        ),
    },
    {
        "id": "s5",
        "heading": "Results \u203a What the medium held",
        "text": (
            "No secreted product was detected in the medium of the parent strain. "
            "On the solid medium, colonies appeared after eight days. "
            "It secreted the same share of its protein as the parent strain."
        ),
    },
    {
        "id": "t1",
        "heading": "Table 1 Titres by condition",
        "text": "Condition | Titre | Unit\nFed-batch | 4200 | mg L-1\nShake flask | 150 | mg L-1",
    },
]

ONTOLOGY = tables()["ontology"]

# A categorical field that requires a method, for the rules a categorical
# value keeps. The record fields hold none at present (alpha 2.0 removed the
# families that had them, ADR-010), so a test hands the engine one of its own.
TEST_CATEGORICAL = {
    "id": "test_enzyme_identity",
    "family": "expression",
    "name": "Enzyme identity (test field)",
    "definition": "A named enzyme, as the paper states it. Written for these tests.",
    "canonicalUnit": "",
    "categorical": True,
    "requiresMethod": True,
    "refuseConversionTo": [],
}


@pytest.fixture
def categorical(monkeypatch):
    real = units.tables()
    monkeypatch.setattr(units, "tables", lambda path=None: {**real, "ontology": {**real["ontology"], TEST_CATEGORICAL["id"]: TEST_CATEGORICAL}})
    return TEST_CATEGORICAL["id"]


def good(**overrides):
    base = {
        "sectionId": "s3",
        "field": "titer_secreted",
        "value": 4.2,
        "unit": "g/L",
        "quote": "The secreted titre reached 4.20 g L-1 after 72 h in the fed-batch run",
        "confidence": 0.9,
        "isPrimary": True,
    }
    base.update(overrides)
    return base


def anchor(raw):
    return anchor_candidate(raw, SECTIONS, paper_id="X1", candidate_id="cl1-X1-1")


# ── normalisation and number parsing ───────────────────────────────────


def test_normalisation_folds_dashes_superscripts_soft_hyphens_and_whitespace():
    assert normalize_text("4.2 g L⁻¹   over 7–10 d") == "4.2 g L-1 over 7-10 d"
    assert normalize_text("soft­hyphen") == "softhyphen"
    assert normalize_text("−17 °C") == "-17 °C"


def test_a_superscript_on_a_number_is_a_power_of_ten_not_a_digit():
    # '10⁶' is a million, not a hundred and six; 'L⁻¹' is still a unit exponent.
    assert normalize_text("2 × 10⁶ cells mL⁻¹") == "2 × 10^6 cells mL-1"
    assert normalize_text("10⁻⁶ M") == "10^-6 M"
    assert normalize_text("m² and CO₂") == "m2 and CO₂"


@pytest.mark.parametrize(
    ("text", "numbers"),
    [
        ("2 × 10^6 cells mL-1", [2e6]),
        ("2 x 10^6 cells", [2e6]),
        ("2.5·10^-3 M", [2.5e-3]),
        ("about 10^6 cells and 12 h", [1e6, 12.0]),
        ("1e6 cells", [1e6]),
    ],
)
def test_scientific_notation_is_one_number(text, numbers):
    assert parse_numbers(text) == numbers


@pytest.mark.parametrize("written", ["4200", "4,200", "4200 mg L-1", " 4,200 "])
def test_a_value_written_as_a_string_is_read_like_a_quote(written):
    c, rule, detail = anchor(
        good(sectionId="t1", value=written, unit="mg/L", quote="Fed-batch | 4200 | mg L-1")
    )
    assert rule is None, detail
    assert c.value == 4200 and c.si.value == 4.2


def test_a_string_value_must_hold_exactly_one_number():
    # A range written as the value is read as that range, and a quote that
    # does not state it refuses it (the tests on values copied whole, below).
    _, rule, detail = anchor(good(sectionId="t1", value="7-10", unit="mg/L", quote="Fed-batch | 4200 | mg L-1"))
    assert rule == "value" and "the recorded range 7-10" in detail, detail
    _, rule, _ = anchor(good(value="four point two"))
    assert rule == "value"


def test_a_power_of_ten_in_the_quote_is_read_as_a_number():
    # A titre written as 4.2 × 10³ mg L⁻¹ is 4.2 g/L; it must not be read as 4.2, 10 and 3.
    sections = SECTIONS + [
        {"id": "s8", "heading": "Titre", "text": "The titre reached 4.2 × 10³ mg L⁻¹ by day 4."}
    ]
    raw = good(sectionId="s8", value=4200, unit="mg/L", quote="reached 4.2 × 10³ mg L⁻¹")
    c, rule, detail = anchor_candidate(raw, sections, paper_id="X1", candidate_id="cl1-X1-1")
    assert rule is None, detail
    assert c.si.value == 4.2
    raw = good(sectionId="s8", value=4.2, unit="mg/L", quote="reached 4.2 × 10³ mg L⁻¹")
    _, rule, _ = anchor_candidate(raw, sections, paper_id="X1", candidate_id="cl1-X1-1")
    assert rule == "value", "4.2 is the mantissa, not a number the sentence states"


@pytest.mark.parametrize(
    ("text", "numbers"),
    [
        ("reached 4.20 g L-1 after 72 h", [4.20, 72.0]),
        ("Fed-batch | 4,200 | mg L-1", [4200.0]),
        ("about 1e6 cells and 12%", [1e6, 12.0]),
        ("in 7-10 days", [7.0, 10.0]),  # the -10 is ten, not minus ten
        ("held at -17 C", [-17.0]),
        ("no numbers here", []),
    ],
)
def test_numbers_are_parsed_as_a_paper_writes_them(text, numbers):
    assert parse_numbers(text) == numbers


# ── the good candidate anchors unchanged ───────────────────────────────


def test_a_good_numeric_candidate_anchors_with_si_and_fixed_provenance():
    c, rule, detail = anchor(good())
    assert rule is None, detail
    assert c is not None
    assert c.id == "cl1-X1-1" and c.paperId == "X1" and c.sectionId == "s3"
    assert c.value == 4.2 and c.unit == "g L⁻¹"
    assert c.si.unit == "kg m⁻³" and c.si.value == 4.2
    assert c.status == "unverified" and c.provenance == "unverified"
    assert c.extractorRun == "claude-1"
    assert c.confidence == 0.9 and c.isPrimary is True


def test_the_model_cannot_set_status_or_provenance():
    c, rule, _ = anchor(good(status="verified", provenance="gold"))
    assert rule is None
    assert c.status == "unverified" and c.provenance == "unverified"


def test_a_table_row_is_a_quote():
    c, rule, detail = anchor(
        good(sectionId="t1", value=4200, unit="mg/L", quote="Fed-batch | 4200 | mg L-1")
    )
    assert rule is None, detail
    assert c.si.value == 4.2  # 4200 mg/L is 4.2 kg m⁻³


def test_a_quote_written_with_unicode_matches_ascii_text():
    # The model copied the quote with a real superscript and a non-breaking
    # space; the fetched text has 'L-1' and a plain space. Same sentence.
    c, rule, detail = anchor(good(quote="reached 4.20 g L⁻¹ after 72 h"))
    assert rule is None, detail


def test_a_soft_hyphen_in_the_text_does_not_break_a_quote():
    c, rule, detail = anchor(
        good(field="titer_secreted", value=4.2, unit="g/L",
             quote="A softhyphenated word")
    )
    # The quote is in the text — but the value is not in the quote, so it
    # fails on rule 3, which proves rule 2 passed.
    assert rule == "value", detail


def test_a_categorical_candidate_anchors_case_insensitively(categorical):
    c, rule, detail = anchor(
        good(field=categorical, value="fam20c", unit="", method="undetermined", quote="The kinase responsible was Fam20C.")
    )
    assert rule is None, detail
    assert c.value == "fam20c" and c.unit == "" and c.si.unit == ""


def test_undetermined_is_a_valid_method():
    # Any numeric field that requires a method, with a sentence written for it
    # in its own canonical unit.
    needs, spec = next((k, d) for k, d in ONTOLOGY.items() if d["requiresMethod"] and not d["categorical"])
    value = 7
    sentence = f"The measured value was {value:g} {spec['canonicalUnit']} by the stated method."
    sections = SECTIONS + [{"id": "s9", "heading": "Extra", "text": sentence}]
    raw = good(sectionId="s9", field=needs, value=value, unit=spec["canonicalUnit"],
               method="undetermined", quote=sentence)
    c, rule, detail = anchor_candidate(raw, sections, paper_id="X1", candidate_id="cl1-X1-1")
    assert rule is None, detail
    assert c.method == "undetermined"
    # And without the method, the same candidate is refused on rule 6.
    raw.pop("method")
    _, rule, _ = anchor_candidate(raw, sections, paper_id="X1", candidate_id="cl1-X1-1")
    assert rule == "method"


# ── one refusal per rule ───────────────────────────────────────────────


def test_rule_0_unknown_field():
    _, rule, _ = anchor(good(field="no_such_field"))
    assert rule == "field"


def test_rule_1_section_must_be_fetched():
    _, rule, detail = anchor(good(sectionId="s99"))
    assert rule == "section" and "s99" in detail


def test_rule_2_quote_must_be_verbatim():
    _, rule, _ = anchor(good(quote="The secreted titre reached 4.2 g/L"))  # paraphrased
    assert rule == "quote"


def test_rule_2_quote_must_be_short():
    long = "x" * (MAX_QUOTE_CHARS + 1)
    _, rule, detail = anchor(good(quote=long))
    assert rule == "quote" and str(MAX_QUOTE_CHARS) in detail


def test_rule_3_value_must_be_in_the_quote_within_half_a_percent():
    # 4.2 against 4.20 is fine (above); 4.2 against 42 is not.
    _, rule, detail = anchor(good(value=42))
    assert rule == "value", detail
    # 4.2 against 4.19 is inside 0.5 %; 4.2 against 4.1 is outside.
    assert anchor(good(value=4.19))[1] is None
    assert anchor(good(value=4.1))[1] == "value"


def test_rule_3_categorical_value_must_be_in_the_quote(categorical):
    _, rule, _ = anchor(good(field=categorical, value="CK2", unit="", method="undetermined", quote="The kinase responsible was Fam20C."))
    assert rule == "value"


def test_rule_4_unit_must_normalise():
    _, rule, detail = anchor(good(unit="furlongs"))
    assert rule == "unit" and "furlongs" in detail


def test_rule_4_unit_must_be_in_the_fields_family_with_the_reason():
    _, rule, detail = anchor(
        good(unit="% TSP", value=12, quote="Intracellular product amounted to 12% of total soluble protein")
    )
    assert rule == "unit"
    assert "total soluble protein" in detail  # the recorded refusal reason



def test_a_candidate_whose_unit_disagrees_with_the_quotes_refuses_on_the_value():
    # The row says 4200 mg L-1. A candidate calling that 4200 g/L is claiming
    # a number the sentence does not state, and rule 3 now sees it.
    _, rule, detail = anchor(
        good(sectionId="t1", value=4200, unit="g/L", quote="Fed-batch | 4200 | mg L-1")
    )
    assert rule == "value", detail


def test_rule_6_a_method_is_required_where_the_ontology_says_so(categorical):
    _, rule, detail = anchor(
        good(field=categorical, value="fam20c", unit="", quote="The kinase responsible was Fam20C.")
    )
    assert rule == "method", detail


# ── the batch counts per rule and numbers survivors in order ───────────


def test_anchor_all_counts_rejections_per_rule():
    result = anchor_all(
        [
            good(),
            good(sectionId="s99"),
            good(value=42),
            good(unit="furlongs"),
            good(sectionId="t1", value=4200, unit="mg/L", quote="Fed-batch | 4200 | mg L-1"),
            good(quote="not in the paper at all"),
        ],
        SECTIONS,
        paper_id="X1",
    )
    ids = [c.id for c in result.accepted]
    assert len(ids) == 2 and all(re.fullmatch(r"cl1-X1-[0-9a-f]{8}", i) for i in ids) and ids[0] != ids[1]
    # Stable: the same content gets the same id on a second run, however the
    # unit was spelled; a duplicate collapses.
    again = anchor_all([good(), good(unit="g L⁻¹"), good()], SECTIONS, paper_id="X1")
    assert [c.id for c in again.accepted] == [ids[0]] and again.rejected == 0
    assert again.duplicates == 2
    assert result.rejected == 4
    assert result.reasons["section"] == 1
    assert result.reasons["value"] == 1
    assert result.reasons["unit"] == 1
    assert result.reasons["quote"] == 1
    assert set(result.reasons) == set(ANCHOR_RULES)
    assert len(result.details) == 4


def test_a_duplicate_keeps_the_more_confident_emission():
    # The same sentence, field and number emitted twice is one candidate;
    # the copy kept is the one the model was surer of, whichever came first,
    # and the collapse is counted rather than silently absorbed.
    low_first = anchor_all([good(confidence=0.4), good(confidence=0.9)], SECTIONS, paper_id="X1")
    high_first = anchor_all([good(confidence=0.9), good(confidence=0.4)], SECTIONS, paper_id="X1")
    assert [c.confidence for c in low_first.accepted] == [0.9]
    assert [c.confidence for c in high_first.accepted] == [0.9]
    assert low_first.duplicates == high_first.duplicates == 1
    assert low_first.accepted[0].id == high_first.accepted[0].id


# ── §2.4 rule 3, as OF-BLD-012.1 F1.2 rewrites it ──────────────────────
#
# The curators recorded that "7-10 days" is a range and that "not
# phosphorylated" is an absence. Until F1.2 the exporter dropped that
# structure and the rule met a midpoint it could not find in the sentence.
# These cases are the structure, read back.


def test_the_quote_is_parsed_into_quantities_not_bare_numbers():
    q = parse_quantities("The secreted titre reached 4.20 g L-1 after 72 h")
    assert [(x.value, x.unit) for x in q] == [(4.2, "g L\u207b\u00b9"), (72.0, "h")]
    # A number with nothing that normalises after it is a bare quantity.
    assert [(x.value, x.unit) for x in parse_quantities("released 45-50%")] == [
        (45.0, None),
        (50.0, "%"),
    ]


def test_word_numbers_and_scale_words_are_quantities():
    assert [x.value for x in parse_quantities("all eight phosphoserine sites")] == [8.0]
    assert [x.value for x in parse_quantities("roughly three-fold")] == [3.0]
    assert [x.value for x in parse_quantities("about USD 1 million/kg")] == [1e6]
    assert [x.value for x in parse_quantities("roughly three times larger")] == [3.0]
    # An ordinal is not a cardinal: 'the second impeller' is not the number two.
    assert [x.value for x in parse_quantities("the second impeller")] == []


def test_a_recorded_range_anchors_on_its_midpoint():
    c, rule, detail = anchor(
        good(
            field="time_to_colony",
            value=8.5,
            unit="d",
            quote="Colonies appeared in 7\u201310 days",
            range={"low": 7, "high": 10},
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "range-midpoint"


@pytest.mark.parametrize(
    "value,basis", [(7, "range-low"), (10, "range-high"), (8.5, "range-midpoint")]
)
def test_a_recorded_range_anchors_on_either_endpoint_too(value, basis):
    c, rule, detail = anchor(
        good(
            field="time_to_colony",
            value=value,
            unit="d",
            quote="Colonies appeared in 7\u201310 days",
            range={"low": 7, "high": 10},
        )
    )
    assert rule is None, detail
    assert c.valueBasis == basis


def test_a_range_is_converted_from_the_units_the_quote_writes():
    # The curators recorded 0.012-0.015 g/L; the paper wrote 12-15 mg/L.
    c, rule, detail = anchor(
        good(
            sectionId="s4",
            value=0.0135,
            unit="g/L",
            quote="Secretion in the flask line ran 12-15 mg L-1 across the series",
            range={"low": 0.012, "high": 0.015},
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "range-midpoint"


def test_a_range_written_as_a_to_b_with_a_unit_on_each_end():
    # 0.6 mg/L to 1 g/L is the range 0.6-1000 mg/L; the midpoint is 500.3.
    c, rule, detail = anchor(
        good(
            sectionId="s4",
            value=500.3,
            unit="mg/L",
            quote="yields ran 0.6 mg L-1 to 1 g L-1 in five yeast studies",
            range={"low": 0.6, "high": 1000},
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "range-midpoint"


# A value a model copies whole from a paper (alpha 2.1, stage B: the live
# extraction refused every "0.15 ± 0.01 (A)" and "2–3" a fallback model sent).
SPREAD = [{"id": "r1", "heading": "Results", "text": "The secreted titre was 0.15 ± 0.01 g L-1 in strain A. "
           "Colonies appeared in 7–10 days."}]


def _copied(**overrides):
    return anchor_candidate(good(sectionId="r1", **overrides), SPREAD, paper_id="X2", candidate_id="cl1-X2-1")


def test_a_mean_written_with_its_spread_anchors_on_the_mean():
    c, rule, detail = _copied(value="0.15 ± 0.01 (A)", unit="g/L", quote="The secreted titre was 0.15 ± 0.01 g L-1 in strain A")
    assert rule is None, detail
    assert (c.value, c.valueBasis, c.range) == (0.15, "exact", None)


def test_a_mean_with_its_spread_still_stands_in_the_quote():
    _, rule, detail = _copied(value="0.16 ± 0.01", unit="g/L", quote="The secreted titre was 0.15 ± 0.01 g L-1 in strain A")
    assert rule == "value", detail


def test_a_range_copied_whole_is_the_records_range_and_its_low_end():
    c, rule, detail = _copied(field="time_to_colony", value="7–10", unit="d", quote="Colonies appeared in 7–10 days")
    assert rule is None, detail
    assert (c.value, c.valueBasis, (c.range.low, c.range.high)) == (7, "range-low", (7, 10))


def test_a_value_holding_several_numbers_otherwise_is_refused():
    _, rule, detail = _copied(field="time_to_colony", value="7, 8 and 10", unit="d", quote="Colonies appeared in 7–10 days")
    assert rule == "value" and "not a single number" in detail, detail


def test_a_range_the_quote_does_not_state_refuses():
    _, rule, detail = anchor(
        good(
            field="time_to_colony",
            value=8.5,
            unit="d",
            quote="Colonies appeared in 7\u201310 days",
            range={"low": 2, "high": 5},
        )
    )
    assert rule == "value", detail


def test_a_negative_result_reads_zero_from_the_sentence_that_states_the_absence():
    c, rule, detail = anchor(
        good(
            sectionId="s5",
            field="titer_secreted",
            value=0,
            unit="g/L",
            quote="No secreted product was detected in the medium of the parent strain",
            negativeResult=True,
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "negation"


def test_a_negative_result_needs_a_marker_in_the_quote():
    _, rule, detail = anchor(
        good(
            sectionId="s4",
            field="titer_secreted",
            value=0,
            unit="g/L",
            quote="Secretion improved roughly three-fold over the parent strain",
            negativeResult=True,
        )
    )
    assert rule == "value", detail


def test_a_negative_result_flag_does_not_license_a_number():
    # negativeResult is about zero. A non-zero value is held to the ordinary rule.
    _, rule, detail = anchor(
        good(
            sectionId="s5",
            field="titer_secreted",
            value=40,
            unit="g/L",
            quote="No secreted product was detected in the medium of the parent strain",
            negativeResult=True,
        )
    )
    assert rule == "value", detail


def test_a_number_the_paper_wrote_in_words_anchors():
    c, rule, detail = anchor(
        good(
            sectionId="s5",
            field="time_to_colony",
            value=8,
            unit="d",
            quote="On the solid medium, colonies appeared after eight days",
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "exact"


def test_a_fold_written_in_words_anchors():
    c, rule, detail = anchor(
        good(
            sectionId="s4",
            field="fold_improvement",
            value=3,
            unit="\u00d7",
            quote="Secretion improved roughly three-fold over the parent strain",
        )
    )
    assert rule is None, detail


def test_a_scale_word_multiplies_the_number_beside_it():
    c, rule, detail = anchor(
        good(
            sectionId="s4",
            field="minimum_selling_price",
            value=12000,
            unit="USD kg-1",
            quote="The analogue sold at about USD 12 thousand/kg in 2025",
            method="undetermined",
        )
    )
    assert rule is None, detail


def test_a_unit_the_quote_spells_differently_anchors_as_converted():
    # The table says 4200 mg L-1; the candidate says 4.2 g/L. One measurement.
    c, rule, detail = anchor(
        good(sectionId="t1", value=4.2, unit="g/L", quote="Fed-batch | 4200 | mg L-1")
    )
    assert rule is None, detail
    assert c.valueBasis == "converted"


def test_a_value_derived_from_the_quotes_numbers_still_refuses():
    # A rate of 0.24 h-1 read off "0.12 h-1": doubling is arithmetic the
    # sentence did not do, and no flag licenses it.
    _, rule, detail = anchor(
        good(
            sectionId="s3",
            field="growth_rate_mu",
            value=0.24,
            unit="h-1",
            quote="The specific growth rate was 0.12 h-1",
        )
    )
    assert rule == "value", detail


def test_a_value_read_from_a_comparison_still_refuses():
    # "the same share of its protein as" is a comparison, and no number 100.
    _, rule, detail = anchor(
        good(
            sectionId="s5",
            field="secreted_fraction",
            value=100,
            unit="% of total expressed",
            quote="It secreted the same share of its protein as the parent strain",
        )
    )
    assert rule == "value", detail


# ── §6.9 — what a review of rule 3 found ────────────────────────────────
#
# Two ways a sentence that states no number was read as stating one.


def test_a_cardinal_in_a_partitive_or_a_compound_is_not_a_quantity():
    # "one of the highest titres" states no titre of 1, and "a two-step
    # purification" states no 2. Read as numbers, they let a candidate
    # valued 1 or 2 anchor on ordinary prose as basis 'exact'.
    from openferment_core.validate import value_basis

    assert value_basis(1.0, "one of the highest titres reported for this host", "g L-1") is None
    assert value_basis(2.0, "a two-step purification gave pure protein", "") is None
    assert value_basis(1.0, "one of the two strains grew", "") is None
    # What the closed list is FOR still reads as it did:
    assert value_basis(3.0, "Secretion improved roughly three-fold", "×") == "exact"
    assert value_basis(3.0, "roughly three times larger than normal", "×") == "exact"
    assert value_basis(8.0, "All eight phosphoserine sites were substituted", "mol mol-1") == "exact"


def test_a_negation_marker_is_a_word_not_a_substring():
    # 'none' is not in 'nonetheless' and 'absent' is not in 'absentee'; a
    # marker matched as a substring let a zero anchor on a sentence that
    # reports no absence at all.
    from openferment_core.validate import value_basis

    assert value_basis(0.0, "nonetheless, the yield rose to 4.2 g/L", "g L-1", negative_result=True) is None
    assert value_basis(0.0, "the absentee samples were discarded", "", negative_result=True) is None
    assert value_basis(0.0, "phosphoserine was not detected in any fraction", "", negative_result=True) == "negation"
    assert value_basis(0.0, "there was no detectable kinase activity", "", negative_result=True) == "negation"
    assert value_basis(0.0, "the sites were absent from the mature protein", "", negative_result=True) == "negation"


# ── a quote whose unit does not convert into the candidate's (H3-01) ───
#
# Rule 3 reads the number in the unit the sentence wrote and converts it into
# the candidate's. Where the unit engine refuses the conversion (a price per
# gallon into one per kilogram, a percentage by volume into a mass
# concentration), the sentence states no number in the candidate's unit, and
# the candidate is refused on the value. biorepo.write re-anchors every value
# a decision places through the same rule, so a candidate kept before rule 3
# read the unit cannot become a gold or a corrected record either. Test
# sentences, stated as such.

PER_GALLON = "The minimum ethanol selling price was $2.15/gal in the base case."
BY_VOLUME = "The final ethanol concentration was 45% (v/v) after fermentation."
UNCONVERTED = [
    ("minimum_selling_price", 2.15, "USD/kg", PER_GALLON, "USD gal⁻¹"),
    ("minimum_selling_price", 2.15, "USD/kg", "The minimum ethanol selling price was 2.15 USD/gal in the base case.",
     "USD gal⁻¹"),
    ("ethanol_titre", 45, "g/L", BY_VOLUME, "%"),
    ("ethanol_titre", 5, "g/L", "Ethanol reached 5 mol/L in the broth.", "mol L⁻¹"),
    ("ethanol_yield_substrate", 0.45, "g/g", "The specific growth rate was 0.45 h-1 on glucose.", "h⁻¹"),
    ("specific_oxygen_uptake", 2, "mmol/g/h", "The specific oxygen uptake rate was 2 mg/g/h in the run.",
     "mg g⁻¹ h⁻¹"),
    ("minimum_selling_price", 1.2, "USD/kg", "The minimum selling price was 1.2 EUR kg-1 for the product.",
     "EUR kg⁻¹"),
]


def _on_its_sentence(field, value, unit, sentence):
    sections = [{"id": "s1", "heading": "Results", "text": f"Results. {sentence} Further text."}]
    raw = {"sectionId": "s1", "field": field, "value": value, "unit": unit, "quote": sentence,
           "method": "undetermined"}
    return anchor_candidate(raw, sections, paper_id="U1")


def test_a_currency_written_before_the_number_joins_the_unit_after_it():
    assert [(q.value, q.unit) for q in parse_quantities(PER_GALLON)] == [(2.15, "USD gal⁻¹")]
    assert [(q.value, q.unit) for q in parse_quantities("sold at about USD 12 thousand/kg")] == [
        (12000.0, "USD kg⁻¹")
    ]
    # A currency with no unit after it stays a bare number.
    assert [(q.value, q.unit) for q in parse_quantities("it cost $2.15 in all")] == [(2.15, None)]


@pytest.mark.parametrize("field,value,unit,sentence,said", UNCONVERTED)
def test_a_quote_whose_unit_does_not_convert_into_the_candidates_refuses_on_the_value(
    field, value, unit, sentence, said
):
    candidate, rule, detail = _on_its_sentence(field, value, unit, sentence)
    assert candidate is None and rule == "value", (rule, detail)
    assert f"the quote states {value:g} {said}" in detail and "does not convert into" in detail


def test_a_quote_whose_unit_converts_still_anchors_and_says_converted():
    c, rule, detail = _on_its_sentence(
        "ethanol_titre", 0.045, "g/L", "The final ethanol concentration was 45 mg/L after fermentation."
    )
    assert rule is None, detail
    assert c.valueBasis == "converted"
    c, rule, detail = _on_its_sentence("minimum_selling_price", 12000, "USD/kg", "sold at about USD 12 thousand/kg")
    assert rule is None, detail
    assert c.valueBasis == "exact", "the sentence wrote the candidate's own unit, and nothing was converted"


def test_biorepo_write_refuses_to_promote_a_value_whose_quote_unit_does_not_convert(held_documents):
    from openferment_core import biorepo, db, extract, projects
    from openferment_core.literature import kit
    from openferment_core.models import Candidate, ExtractResponse, Quantity, ReviewDecision, Usage
    from openferment_core.units import to_si

    held_documents["U1"] = [
        {"id": "s1", "heading": "Results", "text": f"Results. {PER_GALLON} Further text."},
        {"id": "s2", "heading": "Results", "text": f"Results. {BY_VOLUME} Further text."},
    ]
    db.run(kit._link(projects.current(), "U1", {}, "test"))
    # The two candidates as anchoring kept them while rule 3 compared such a
    # number bare: a price per kilogram on a price per gallon, and a mass
    # concentration on a percentage by volume.
    kept = []
    for cid, section, field, value, unit, quote in (
        ("cl1-U1-00000001", "s1", "minimum_selling_price", 2.15, "USD kg⁻¹", PER_GALLON),
        ("cl1-U1-00000002", "s2", "ethanol_titre", 45.0, "g L⁻¹", BY_VOLUME),
    ):
        sv, su = to_si(value, unit)
        kept.append(Candidate(id=cid, paperId="U1", sectionId=section, field=field, value=value, unit=unit,
                              quote=quote, si=Quantity(value=sv, unit=su), confidence=0.8, valueBasis="converted",
                              method="undetermined"))
    extract._persist(ExtractResponse(paperId="U1", extractedAt="2026-11-10T12:00:00Z", candidates=kept, audit=[],
                                     usage=Usage(), calls=0))

    def decided(record_id, **kw):
        return ReviewDecision(status="verified", provenance="curated", reviewer="A test reviewer",
                              recordId=record_id, at="2026-11-10T12:00:00Z", **kw)

    # A decision that places a number re-anchors it on the record's quote: a
    # gold value or a correction (an accept with neither places none, §7.3).
    with pytest.raises(biorepo.WriteRefused) as price:
        biorepo.write(decided("cl1-U1-00000001", gold=Quantity(value=2.15, unit="USD/kg")))
    assert price.value.rule == "quote"
    assert "rule 'value'" in price.value.why and "USD gal⁻¹ does not convert" in price.value.why
    with pytest.raises(biorepo.WriteRefused) as corrected:
        biorepo.write(decided("cl1-U1-00000001", corrected=Quantity(value=2.15, unit="USD/kg")))
    assert corrected.value.rule == "quote" and "rule 'value'" in corrected.value.why
    with pytest.raises(biorepo.WriteRefused) as gold:
        biorepo.write(decided("cl1-U1-00000002", gold=Quantity(value=45, unit="g/L")))
    assert gold.value.rule == "quote"
    assert "rule 'value'" in gold.value.why and "% does not convert" in gold.value.why
    assert biorepo.decisions() == {}, "neither decision was kept"


# ── a unit the sentence writes past what the unit table reads ──────────
#
# The quantity parser reads the longest run of tokens the unit table knows,
# and for 'g ethanol per litre' that is 'g' alone: the label word and what
# follows it are the rest of the unit. Such a number compares bare, as rule 3
# compared every number before F1.2, and anchors as 'exact'; the refusals
# above, whose units the parser reads whole, stay refused. Test sentences,
# stated as such.

LABELLED = [
    ("ethanol_titre", 45, "g/L", "Ethanol reached 45 g ethanol per litre in the broth."),
    ("final_biomass_density", 12, "g/L", "Biomass reached 12 g DCW/L by the end of the run."),
    ("ethanol_titre", 45, "g L-1", "The titre reached 45 g EtOH L-1 at 48 h."),
    ("medium_component_conc", 100, "g/L", "The feed held 100 g glucose/L at the start."),
    ("ethanol_productivity", 1.2, "g/L/h", "Productivity was 1.2 g ethanol/L/h over the run."),
    ("titer_secreted", 150, "mg/L", "The supernatant held 150 mg protein/L after 72 h."),
    ("ethanol_yield_substrate", 0.45, "g/g", "The yield was 0.45 g ethanol per g glucose consumed."),
    ("expression_pct_tsp", 12, "% TSP", "The reporter made up 12% of total soluble protein."),
    # A denominator in brackets, a middle dot, a share named in words (round
    # 2's check of H3-01): each runs on past the 'g' or '%' the table reads.
    ("ethanol_yield_substrate", 0.45, "g/g", "The ethanol yield was 0.45 g ethanol (g glucose)-1 on the hydrolysate."),
    ("ethanol_yield_substrate", 0.45, "g/g", "The ethanol yield was 0.45 g ethanol (g glucose)\u22121 on the hydrolysate."),
    ("biomass_yield_substrate", 0.5, "g/g", "Biomass yield was 0.5 g cells (g glucose)-1 in the batch."),
    ("final_biomass_density", 5, "g/L", "The culture reached 5 g (DCW)/L by the end of the run."),
    ("ethanol_titre", 80, "g/L", "Growth stopped near 80 g ethanol\u00b7L-1 in the broth."),
    ("expression_pct_tsp", 12, "% TSP", "The reporter made up 12% total soluble protein in the leaves."),
]


@pytest.mark.parametrize("field,value,unit,sentence", LABELLED)
def test_a_quote_whose_unit_carries_a_label_anchors_its_candidate_as_exact(field, value, unit, sentence):
    c, rule, detail = _on_its_sentence(field, value, unit, sentence)
    assert rule is None, detail
    assert c.valueBasis == "exact", "a unit read in part is compared bare, and nothing is converted from it"


def test_the_parser_says_when_the_sentences_unit_runs_on_past_what_it_read():
    for _, value, _, sentence in LABELLED:
        [q] = [q for q in parse_quantities(sentence) if q.value == value]
        assert q.unit is not None and q.unitWhole is False, sentence
    for _, value, _, sentence, _ in UNCONVERTED:
        [q] = [q for q in parse_quantities(sentence) if q.value == value]
        assert q.unitWhole, sentence
    assert [q.unitWhole for q in parse_quantities("The secreted titre reached 4.20 g L-1 after 72 h")] == [True, True]


def test_a_share_named_in_words_states_nothing_in_a_unit_that_is_no_percentage():
    # A percentage read in part compares bare into a percentage alone: the
    # sentence states 12% of something, and no 12 g/L.
    for sentence in ("The reporter made up 12% total soluble protein in the leaves.",
                     "The reporter made up 12% of total soluble protein."):
        c, rule, detail = _on_its_sentence("ethanol_titre", 12, "g/L", sentence)
        assert c is None and rule == "value", detail
    # A bracket closed with nothing after it qualifies the unit and ends it.
    assert [q.unitWhole for q in parse_quantities("Ethanol was 45% (v/v) in the broth.")] == [True]


def test_a_number_whose_unit_runs_on_is_never_converted():
    # 150 mg protein/L read as 150 mg would convert into no concentration;
    # compared bare, it states 150 and no 0.15.
    c, rule, detail = _on_its_sentence("titer_secreted", 0.15, "g/L", "The supernatant held 150 mg protein/L after 72 h.")
    assert c is None and rule == "value", detail


def test_biorepo_write_reanchors_a_plain_accept_on_a_candidate_kept_as_converted(held_documents):
    # A candidate kept while rule 3 compared a number in another unit bare
    # carries valueBasis 'converted'. A plain accept places the record's own
    # number, so its value is anchored on its quote again, and one that no
    # longer anchors is refused; one that still does is kept as sent.
    from openferment_core import biorepo, db, extract, projects
    from openferment_core.literature import kit
    from openferment_core.models import Candidate, ExtractResponse, Quantity, ReviewDecision, Usage
    from openferment_core.units import to_si

    labelled = "Ethanol reached 45 g ethanol per litre in the broth."
    in_mg = "The final ethanol concentration was 45 mg/L after fermentation."
    held_documents["U2"] = [
        {"id": f"s{n}", "heading": "Results", "text": f"Results. {sentence} Further text."}
        for n, sentence in enumerate((PER_GALLON, BY_VOLUME, labelled, in_mg), start=1)
    ]
    db.run(kit._link(projects.current(), "U2", {}, "test"))
    kept = []
    for cid, section, field, value, unit, quote in (
        ("cl1-U2-00000001", "s1", "minimum_selling_price", 2.15, "USD kg⁻¹", PER_GALLON),
        ("cl1-U2-00000002", "s2", "ethanol_titre", 45.0, "g L⁻¹", BY_VOLUME),
        ("cl1-U2-00000003", "s3", "ethanol_titre", 45.0, "g L⁻¹", labelled),
        ("cl1-U2-00000004", "s4", "ethanol_titre", 0.045, "g L⁻¹", in_mg),
    ):
        sv, su = to_si(value, unit)
        kept.append(Candidate(id=cid, paperId="U2", sectionId=section, field=field, value=value, unit=unit,
                              quote=quote, si=Quantity(value=sv, unit=su), confidence=0.8, valueBasis="converted",
                              method="undetermined"))
    extract._persist(ExtractResponse(paperId="U2", extractedAt="2026-11-10T12:00:00Z", candidates=kept, audit=[],
                                     usage=Usage(), calls=0))

    def accepted(record_id):
        return ReviewDecision(status="verified", provenance="curated", reviewer="A test reviewer",
                              recordId=record_id, at="2026-11-10T12:00:00Z")

    for record_id, unit in (("cl1-U2-00000001", "USD gal⁻¹"), ("cl1-U2-00000002", "%")):
        for dry_run in (True, False):
            with pytest.raises(biorepo.WriteRefused) as refused:
                biorepo.write(accepted(record_id), dry_run=dry_run)
            assert refused.value.rule == "quote", dry_run
            assert "rule 'value'" in refused.value.why and f"{unit} does not convert" in refused.value.why
    # The labelled unit compares bare and the milligrams convert: both stand.
    for record_id in ("cl1-U2-00000003", "cl1-U2-00000004"):
        stored = biorepo.write(accepted(record_id))
        assert stored.status == "verified" and stored.quote is None, "the decision is kept as sent"
    assert sorted(biorepo.decisions()) == ["cl1-U2-00000003", "cl1-U2-00000004"]


def test_biorepo_write_reanchors_a_plain_accept_on_a_candidate_kept_as_exact(held_documents):
    # '$2.15/gal' parsed with no unit before round 1, so 2.15 USD kg⁻¹ was
    # kept as 'exact' on it (bughunt/repro/H3-01/README.md). A plain accept
    # anchors every record with a quote on it again, whatever its basis, and
    # this one is refused; a record that still anchors is kept as sent.
    from openferment_core import biorepo, db, extract, projects
    from openferment_core.literature import kit
    from openferment_core.models import Candidate, ExtractResponse, Quantity, ReviewDecision, Usage
    from openferment_core.units import to_si

    plain = "The final ethanol concentration was 45 g/L after fermentation."
    held_documents["U3"] = [
        {"id": f"s{n}", "heading": "Results", "text": f"Results. {sentence} Further text."}
        for n, sentence in enumerate((PER_GALLON, plain), start=1)
    ]
    db.run(kit._link(projects.current(), "U3", {}, "test"))
    kept = []
    for cid, section, field, value, unit, quote in (
        ("cl1-U3-00000001", "s1", "minimum_selling_price", 2.15, "USD kg⁻¹", PER_GALLON),
        ("cl1-U3-00000002", "s2", "ethanol_titre", 45.0, "g L⁻¹", plain),
    ):
        sv, su = to_si(value, unit)
        kept.append(Candidate(id=cid, paperId="U3", sectionId=section, field=field, value=value, unit=unit,
                              quote=quote, si=Quantity(value=sv, unit=su), confidence=0.8, valueBasis="exact",
                              method="undetermined"))
    extract._persist(ExtractResponse(paperId="U3", extractedAt="2026-11-10T12:00:00Z", candidates=kept, audit=[],
                                     usage=Usage(), calls=0))

    def accepted(record_id):
        return ReviewDecision(status="verified", provenance="curated", reviewer="A test reviewer",
                              recordId=record_id, at="2026-11-10T12:00:00Z")

    for dry_run in (True, False):
        with pytest.raises(biorepo.WriteRefused) as refused:
            biorepo.write(accepted("cl1-U3-00000001"), dry_run=dry_run)
        assert refused.value.rule == "quote", dry_run
        assert "rule 'value'" in refused.value.why and "USD gal⁻¹ does not convert" in refused.value.why
    stored = biorepo.write(accepted("cl1-U3-00000002"))
    assert stored.status == "verified" and stored.quote is None, "the decision is kept as sent"
    assert sorted(biorepo.decisions()) == ["cl1-U3-00000002"]


def test_a_gram_per_gallon_is_refused_on_the_unit():
    # H3-08: 0.45 g/gal anchored as a verified yield of 0.45 g g⁻¹; it does not
    # normalise now, and anchoring refuses it on rule 'unit' as it refuses g/furlong.
    c, rule, detail = _on_its_sentence("ethanol_yield_substrate", 0.45, "g/gal",
                                       "The broth held 0.45 g/gal of residual ethanol at harvest.")
    assert c is None and rule == "unit", detail
