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
        "id": "t1",
        "heading": "Table 1 Titres by condition",
        "text": "Condition | Titre | Unit\nFed-batch | 4200 | mg L-1\nShake flask | 150 | mg L-1",
    },
]

ONTOLOGY = tables()["ontology"]


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
    return anchor_candidate(raw, SECTIONS, paper_id="X1", candidate_id="hk1-X1-1")


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
    _, rule, detail = anchor(good(sectionId="t1", value="7-10", unit="mg/L", quote="Fed-batch | 4200 | mg L-1"))
    assert rule == "value" and "single number" in detail
    _, rule, _ = anchor(good(value="four point two"))
    assert rule == "value"


def test_a_power_of_ten_in_the_quote_is_read_as_a_number():
    # A titre written as 4.2 × 10³ mg L⁻¹ is 4.2 g/L; it must not be read as 4.2, 10 and 3.
    sections = SECTIONS + [
        {"id": "s8", "heading": "Titre", "text": "The titre reached 4.2 × 10³ mg L⁻¹ by day 4."}
    ]
    raw = good(sectionId="s8", value=4200, unit="mg/L", quote="reached 4.2 × 10³ mg L⁻¹")
    c, rule, detail = anchor_candidate(raw, sections, paper_id="X1", candidate_id="hk1-X1-1")
    assert rule is None, detail
    assert c.si.value == 4.2
    raw = good(sectionId="s8", value=4.2, unit="mg/L", quote="reached 4.2 × 10³ mg L⁻¹")
    _, rule, _ = anchor_candidate(raw, sections, paper_id="X1", candidate_id="hk1-X1-1")
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
    assert c.id == "hk1-X1-1" and c.paperId == "X1" and c.sectionId == "s3"
    assert c.value == 4.2 and c.unit == "g L⁻¹"
    assert c.si.unit == "kg m⁻³" and c.si.value == 4.2
    assert c.status == "unverified" and c.provenance == "unverified"
    assert c.extractorRun == "haiku-1"
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


def test_a_categorical_candidate_anchors_case_insensitively():
    cat = next(k for k, d in ONTOLOGY.items() if d["categorical"] and "kinase" in k)
    c, rule, detail = anchor(
        good(field=cat, value="fam20c", unit="", quote="The kinase responsible was Fam20C.")
    )
    assert rule is None, detail
    assert c.value == "fam20c" and c.unit == "" and c.si.unit == ""


def test_undetermined_is_a_valid_method():
    # Any numeric field that requires a method, with a sentence written for it
    # in its own canonical unit at the middle of its range.
    needs, spec = next((k, d) for k, d in ONTOLOGY.items() if d["requiresMethod"] and not d["categorical"])
    low, high = spec["range"]
    value = (low + high) / 2
    sentence = f"The measured value was {value:g} {spec['canonicalUnit']} by the stated method."
    sections = SECTIONS + [{"id": "s9", "heading": "Extra", "text": sentence}]
    raw = good(sectionId="s9", field=needs, value=value, unit=spec["canonicalUnit"],
               method="undetermined", quote=sentence)
    c, rule, detail = anchor_candidate(raw, sections, paper_id="X1", candidate_id="hk1-X1-1")
    assert rule is None, detail
    assert c.method == "undetermined"
    # And without the method, the same candidate is refused on rule 6.
    raw.pop("method")
    _, rule, _ = anchor_candidate(raw, sections, paper_id="X1", candidate_id="hk1-X1-1")
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


def test_rule_3_categorical_value_must_be_in_the_quote():
    cat = next(k for k, d in ONTOLOGY.items() if d["categorical"] and "kinase" in k)
    _, rule, _ = anchor(good(field=cat, value="CK2", unit="", quote="The kinase responsible was Fam20C."))
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


def test_rule_5_value_must_be_in_range_in_canonical_units():
    # expression_pct_tsp tops out at 40. The quote states 4200 and the
    # candidate's unit does not convert into the quote's, so rule 3 compares
    # the bare number and passes it — and rule 5 is what refuses it.
    _, rule, detail = anchor(
        good(
            sectionId="t1",
            field="expression_pct_tsp",
            value=4200,
            unit="% TSP",
            quote="Fed-batch | 4200 | mg L-1",
            method="undetermined",
        )
    )
    assert rule == "range", detail


def test_a_candidate_whose_unit_disagrees_with_the_quotes_refuses_on_the_value():
    # The row says 4200 mg L-1. A candidate calling that 4200 g/L is claiming
    # a number the sentence does not state, and rule 3 now sees it.
    _, rule, detail = anchor(
        good(sectionId="t1", value=4200, unit="g/L", quote="Fed-batch | 4200 | mg L-1")
    )
    assert rule == "value", detail


def test_rule_6_a_method_is_required_where_the_ontology_says_so():
    needs = next(k for k, d in ONTOLOGY.items() if d["requiresMethod"] and d["categorical"])
    _, rule, detail = anchor(
        good(field=needs, value="fam20c", unit="", quote="The kinase responsible was Fam20C.")
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
    assert len(ids) == 2 and all(re.fullmatch(r"hk1-X1-[0-9a-f]{8}", i) for i in ids) and ids[0] != ids[1]
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
            sectionId="s4",
            field="phosphorylation_degree",
            value=0,
            unit="% of native sites",
            quote="The recombinant protein was not phosphorylated",
            method="undetermined",
            negativeResult=True,
        )
    )
    assert rule is None, detail
    assert c.valueBasis == "negation"


def test_a_negative_result_needs_a_marker_in_the_quote():
    _, rule, detail = anchor(
        good(
            sectionId="s4",
            field="phosphorylation_degree",
            value=0,
            unit="% of native sites",
            quote="All eight phosphoserine sites were substituted with aspartate",
            negativeResult=True,
        )
    )
    assert rule == "value", detail


def test_a_negative_result_flag_does_not_license_a_number():
    # negativeResult is about zero. A non-zero value is held to the ordinary rule.
    _, rule, detail = anchor(
        good(
            sectionId="s4",
            field="phosphorylation_degree",
            value=40,
            unit="% of native sites",
            quote="The recombinant protein was not phosphorylated",
            negativeResult=True,
        )
    )
    assert rule == "value", detail


def test_a_number_the_paper_wrote_in_words_anchors():
    c, rule, detail = anchor(
        good(
            sectionId="s4",
            field="phosphate_count",
            value=8,
            unit="mol mol-1",
            quote="All eight phosphoserine sites were substituted with aspartate",
            method="undetermined",
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
    # r-E2-1: a diameter of 140 nm read off "radius ~70 nm". Doubling is
    # arithmetic the sentence did not do, and no flag licenses it.
    _, rule, detail = anchor(
        good(
            sectionId="s4",
            field="micelle_diameter",
            value=140,
            unit="nm",
            quote="The particle was approximately spherical, radius ~70 nm",
        )
    )
    assert rule == "value", detail


def test_a_value_read_from_a_comparison_still_refuses():
    # r-H4-4: "the same degree of phosphorylation as" is not the number 100.
    _, rule, detail = anchor(
        good(
            sectionId="s4",
            field="phosphorylation_degree",
            value=100,
            unit="% of native sites",
            quote="It carried the same degree of phosphorylation as the animal-derived protein",
        )
    )
    assert rule == "value", detail
