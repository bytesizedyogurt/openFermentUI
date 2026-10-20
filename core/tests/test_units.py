"""The unit engine agrees with the browser (OF-BLD-012 §5.3).

`core/tests/fixtures/units.json` is not written by hand. `scripts/
export-unit-fixtures.ts` runs the TypeScript engine over a fixed set of inputs
and records what it answered; `pnpm test:core` regenerates it before pytest
runs, so the fixture never lags the engine. Every case below asserts that the
Python mirror answers the same — including exact float equality on
conversions, which holds because both sides perform the same IEEE operations
in the same order.

When a case here fails, the TypeScript side is right by definition and the
Python side has drifted. That is the arrangement, and it is the reason the
fixture is generated rather than typed.

Offline and free. No key, no network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core.units import (
    UnitError,
    convert,
    explain_refusal,
    family,
    field,
    in_range,
    normalize,
    quantity_equals,
    tables,
    to_canonical,
    to_si,
)
from openferment_core.validate import anchor_candidate, find_number

FIXTURE = Path(__file__).parent / "fixtures" / "units.json"


def _fixture() -> dict:
    if not FIXTURE.exists():
        raise FileNotFoundError(
            f"{FIXTURE} not found. It is generated from the TypeScript engine — run "
            "`pnpm export:unit-fixtures` from the repository root, or `pnpm test:core`, "
            "which does."
        )
    return json.loads(FIXTURE.read_text())


FX = _fixture()


def _id(case: dict) -> str:
    for key in ("raw", "from", "unit"):
        if key in case:
            return repr(case[key]) + (f"→{case['to']!r}" if "to" in case else "")
    return repr(case.get("a"))


# ── the pairs ──────────────────────────────────────────────────────────


def test_the_fixture_is_the_size_the_spec_asked_for():
    pairs = sum(len(FX[k]) for k in ("normalize", "conversions", "si", "refusals", "equals"))
    assert pairs >= 20, f"{pairs} pairs — §5.3 asks for twenty"


@pytest.mark.parametrize("case", FX["normalize"], ids=_id)
def test_normalize_matches_the_browser(case):
    assert normalize(case["raw"]) == case["unit"]
    assert family(case["raw"]) == case["family"]


@pytest.mark.parametrize("case", FX["conversions"], ids=_id)
def test_convert_matches_the_browser_exactly(case):
    if case["error"] is not None:
        with pytest.raises(UnitError):
            convert(case["value"], case["from"], case["to"])
    else:
        # Exact, not approximate. Same operations in the same order on the
        # same doubles give the same bits; a tolerance here would hide the
        # day somebody reorders them.
        assert convert(case["value"], case["from"], case["to"]) == case["result"]


@pytest.mark.parametrize("case", FX["si"], ids=_id)
def test_to_si_matches_the_browser(case):
    value, unit = to_si(case["value"], case["unit"])
    assert unit == case["si"]["unit"]
    assert value == case["si"]["value"]


@pytest.mark.parametrize("case", FX["refusals"], ids=_id)
def test_refusals_carry_the_same_reason(case):
    assert explain_refusal(case["from"], case["to"]) == case["because"]


@pytest.mark.parametrize("case", FX["equals"], ids=_id)
def test_quantity_equals_matches_the_browser(case):
    a = (case["a"]["value"], case["a"]["unit"])
    b = (case["b"]["value"], case["b"]["unit"])
    assert quantity_equals(a, b, case["tolerancePct"]) is case["result"]


# ── the refusal is an error with its reason attached ──────────────────


def test_a_refused_conversion_raises_with_the_recorded_reason():
    with pytest.raises(UnitError) as caught:
        convert(10, "% TSP", "g/L")
    assert caught.value.reason is not None
    assert "total soluble protein" in caught.value.reason


def test_a_plain_dimension_error_raises_with_no_reason():
    with pytest.raises(UnitError) as caught:
        convert(10, "g/L", "h⁻¹")
    assert caught.value.reason is None


def test_an_unknown_unit_is_an_error_not_a_guess():
    assert normalize("furlongs") is None
    with pytest.raises(UnitError):
        convert(1, "furlongs", "g/L")


# ── the ontology crossed with it ───────────────────────────────────────


def test_every_ontology_field_has_a_canonical_unit_the_engine_knows():
    for field_id, d in tables()["ontology"].items():
        assert normalize(d["canonicalUnit"]) is not None, (
            f"{field_id}: canonical unit {d['canonicalUnit']!r} does not normalise — "
            "no candidate for this field could ever pass §2.4 rule 4"
        )
        low, high = d["range"]
        if d["categorical"]:
            # A string has no range. The ontology writes [0, 0] and an empty
            # unit for these, and rule 5 never runs on them.
            assert d["canonicalUnit"] == "", f"{field_id}: categorical, yet carries a unit"
            continue
        assert low < high, f"{field_id}: range {d['range']} is not ascending"


def test_to_canonical_converts_into_the_field_unit():
    assert field("titer_secreted")["canonicalUnit"] == "g L⁻¹"
    assert to_canonical(2500, "mg/L", "titer_secreted") == 2.5
    assert to_canonical(2.5, "g·L⁻¹", "titer_secreted") == 2.5


def test_to_canonical_refuses_across_families_with_the_reason():
    # §2.4 rule 4, and OF-COR-001 §17 Rule 2: a share of TSP is not a titre.
    with pytest.raises(UnitError) as caught:
        to_canonical(10, "% TSP", "titer_secreted")
    assert caught.value.reason is not None


def test_to_canonical_refuses_a_categorical_field():
    categorical = [k for k, d in tables()["ontology"].items() if d["categorical"]]
    assert categorical, "the ontology has categorical fields (kinase_identity, glycan_species)"
    with pytest.raises(UnitError):
        to_canonical(1, "", categorical[0])


def test_to_canonical_refuses_an_unknown_field():
    with pytest.raises(UnitError):
        to_canonical(1, "g/L", "no_such_field")


def test_in_range_is_inclusive_at_both_ends():
    low, high = field("titer_secreted")["range"]
    assert in_range(low, "titer_secreted")
    assert in_range(high, "titer_secreted")
    assert not in_range(high * 10, "titer_secreted")
    assert not in_range(low / 10, "titer_secreted")


# ── the polymer family (OF-BLD-014 §2.1) ───────────────────────────────


def test_a_share_of_dry_cells_refuses_a_titre_with_the_biomass_density_reason():
    # The row crosses the boundary in corpus.json; units.explain_refusal reads
    # it from there, and to_canonical carries it as the error's reason.
    reason = explain_refusal("% CDW", "g/L")
    assert reason is not None and "biomass density of that culture" in reason
    assert explain_refusal("mg/L", "wt%") == reason
    with pytest.raises(UnitError) as caught:
        to_canonical(40, "% CDW", "pha_titre")
    assert caught.value.reason == reason


def test_the_polymer_aliases_normalise_into_their_own_families():
    for spelling in ("% CDW", "%CDW", "% cdw", "wt%", "% (w/w)"):
        assert normalize(spelling) == "% CDW" and family(spelling) == "percentCdw", spelling
    for spelling in ("kDa", "kda", "kg/mol"):
        assert normalize(spelling) == "kDa" and family(spelling) == "molarMass", spelling
    assert family("Da") == family("g mol⁻¹") == "molarMass"
    # Its own family, not `percent`: a share of dry cells is not % DW of a medium.
    assert not quantity_equals((40, "% CDW"), (40, "%"))


def test_the_ontology_carries_the_five_polymer_fields_and_their_two_refusals():
    ontology = tables()["ontology"]
    polymer = {k: d for k, d in ontology.items() if d["family"] == "polymer"}
    assert set(polymer) == {
        "pha_content_cdw", "pha_titre", "pha_yield_substrate", "pha_productivity", "pha_mw",
    }
    assert polymer["pha_content_cdw"]["canonicalUnit"] == "% CDW"
    assert polymer["pha_mw"]["canonicalUnit"] == "kDa"
    assert {k for k, d in polymer.items() if d["requiresMethod"]} == {"pha_content_cdw", "pha_mw"}
    refused = {k: [r["field"] for r in d["refuseConversionTo"]] for k, d in polymer.items() if d["refuseConversionTo"]}
    assert refused == {"pha_content_cdw": ["pha_titre"], "pha_titre": ["pha_content_cdw"]}
    # Both entries' reasons are the engine's own reason, for the reader of the file.
    for d in (polymer["pha_content_cdw"], polymer["pha_titre"]):
        assert "biomass density of that culture" in d["refuseConversionTo"][0]["because"]


def test_a_bacterial_growth_rate_is_inside_the_widened_range():
    # A rate a bacterium reaches, and the old algal ceiling refused: in range
    # now, while a value an order of magnitude past it still is not.
    assert in_range(to_canonical(0.41, "h⁻¹", "growth_rate_mu"), "growth_rate_mu")
    assert in_range(to_canonical(24, "d⁻¹", "growth_rate_mu"), "growth_rate_mu")
    assert not in_range(to_canonical(30, "h⁻¹", "growth_rate_mu"), "growth_rate_mu")


# ── the kinetics family (thread Q) ─────────────────────────────────────

KINETICS = {
    "monod_ks": "g L⁻¹",
    "biomass_yield_substrate": "g g⁻¹",
    "ethanol_yield_substrate": "g g⁻¹",
    "ethanol_titre": "g L⁻¹",
    "ethanol_productivity": "g L⁻¹ h⁻¹",
    "ethanol_inhibition_ki": "g L⁻¹",
    "ethanol_max_conc": "g L⁻¹",
    "substrate_inhibition_ki": "g L⁻¹",
    "ethanol_lp_alpha": "g g⁻¹",
    "ethanol_lp_beta": "g g⁻¹ h⁻¹",
    "ethanol_mesp": "USD gal⁻¹",
}


def test_the_ontology_carries_the_eleven_kinetics_fields_in_units_the_engine_knows():
    ontology = tables()["ontology"]
    kinetics = {k: d for k, d in ontology.items() if d["family"] == "kinetics"}
    assert {k: d["canonicalUnit"] for k, d in kinetics.items()} == KINETICS
    for field_id, unit in KINETICS.items():
        assert normalize(unit) == unit, f"{field_id}: {unit!r} is not a key of the table"
        assert to_canonical(1, unit, field_id) == 1, field_id
    # Only the price needs its method: the costing basis the analysis names.
    assert {k for k, d in kinetics.items() if d["requiresMethod"]} == {"ethanol_mesp"}
    [refusal] = kinetics["ethanol_mesp"]["refuseConversionTo"]
    assert refusal["field"] == "minimum_selling_price" and "density of the product" in refusal["because"]


def test_the_kinetic_fields_take_the_spellings_papers_write():
    for spelling, field_id in (
        ("g/L", "monod_ks"),
        ("g L-1", "ethanol_titre"),
        ("g L−1", "ethanol_max_conc"),
        ("g/g", "biomass_yield_substrate"),
        ("g g-1", "ethanol_yield_substrate"),
        ("g/L/h", "ethanol_productivity"),
        ("g L-1 h-1", "ethanol_productivity"),
        ("g/g/h", "ethanol_lp_beta"),
        ("g g−1 h−1", "ethanol_lp_beta"),
        ("$/gal", "ethanol_mesp"),
    ):
        assert to_canonical(2, spelling, field_id) == 2, (spelling, field_id)


def test_a_price_per_gallon_normalises_and_refuses_a_price_per_kilogram_with_the_density_reason():
    for spelling in ("$/gal", "USD/gal", "$ gal-1", "$ gal−1", "US$/gal", "$/gallon", "USD per gallon", "USD gal-1"):
        assert normalize(spelling) == "USD gal⁻¹" and family(spelling) == "costUSDVolume", spelling
    for spelling in ("$/kg", "USD/kg"):
        assert normalize(spelling) == "USD kg⁻¹" and family(spelling) == "costUSD", spelling
    reason = explain_refusal("USD gal⁻¹", "USD kg⁻¹")
    assert reason is not None and "density of the product" in reason
    assert explain_refusal("$/kg", "$/gal") == reason, "symmetric, through the aliases"
    with pytest.raises(UnitError) as caught:
        convert(2.5, "$/gal", "USD kg⁻¹")
    assert caught.value.reason == reason
    with pytest.raises(UnitError) as caught:
        to_canonical(2.5, "$/gal", "minimum_selling_price")
    assert caught.value.reason == reason
    # Nor is it a euro price, and there the refusal is plain dimensional analysis.
    assert explain_refusal("USD gal⁻¹", "EUR kg⁻¹") is None


# A paper nobody wrote: one sentence per kinetic quantity, each value placed
# outside its field's guard, and one inside it. Test values, stated as such.
KINETICS_SECTION = [
    {
        "id": "s1",
        "text": (
            "In the imaginary run the ethanol yield reached 0.92 g g-1 on glucose. "
            "The imaginary analysis put the minimum ethanol selling price at $75/gal. "
            "The fitted Ks of the imaginary strain was 150 g/L. "
            "The fitted beta was 12 g g-1 h-1. "
            "In the control run the ethanol yield was 0.45 g g-1 on glucose."
        ),
    }
]


@pytest.mark.parametrize(
    "field_id, value, unit, quote, method",
    [
        ("ethanol_yield_substrate", 0.92, "g g-1", "the ethanol yield reached 0.92 g g-1 on glucose", None),
        ("ethanol_mesp", 75, "$/gal", "the minimum ethanol selling price at $75/gal", "undetermined"),
        ("monod_ks", 150, "g/L", "The fitted Ks of the imaginary strain was 150 g/L", None),
        ("ethanol_lp_beta", 12, "g g-1 h-1", "The fitted beta was 12 g g-1 h-1", None),
    ],
)
def test_a_value_outside_a_kinetic_fields_range_is_refused_at_anchoring(field_id, value, unit, quote, method):
    raw = {
        "sectionId": "s1", "field": field_id, "value": value, "unit": unit, "quote": quote,
        "isPrimary": True, "confidence": 0.9,
    }
    if method:
        raw["method"] = method
    candidate, rule, detail = anchor_candidate(raw, KINETICS_SECTION, paper_id="Q1")
    assert candidate is None and rule == "range", f"{rule}: {detail}"
    assert field_id in detail


def test_a_value_inside_the_range_anchors_on_the_same_sentence_shape():
    raw = {
        "sectionId": "s1", "field": "ethanol_yield_substrate", "value": 0.45, "unit": "g g-1",
        "quote": "the ethanol yield was 0.45 g g-1 on glucose",
        "organism": "Saccharomyces cerevisiae CEN.PK113-7D", "isPrimary": True, "confidence": 0.9,
    }
    candidate, rule, detail = anchor_candidate(raw, KINETICS_SECTION, paper_id="Q1")
    assert candidate is not None, f"{rule}: {detail}"
    assert candidate.value == 0.45 and candidate.unit == "g g⁻¹"
    assert candidate.organism == "s-cerevisiae-cenpk113-7d"


# Definitions reach the extraction model verbatim (extract.ontology_for_prompt),
# so a numeral in one is a number set in front of a model asked to find
# numbers. Read by Rule 1's own detector for its digit form, a numeral outside
# an identifier token: CK2 and cw15 are names. Its word numbers are not held
# here, because "half" in a half-saturation constant and "first" in a
# first-order rate are what those fields mean. Two definitions predate the
# rule and state the native state and the numbering convention they are about;
# every other field, and every field added after them, holds none.
DEFINITIONS_WITH_NUMERALS = {"phosphate_count", "phospho_site_position"}


def _numeral(text: str) -> str | None:
    found = find_number(text)
    # find_number looks for numerals first, so a word it returns means none.
    return found if found is not None and any(ch.isnumeric() for ch in found) else None


def test_no_definition_the_extractor_reads_carries_a_numeral():
    for field_id, d in tables()["ontology"].items():
        found = _numeral(d["name"]) or _numeral(d["definition"])
        if field_id in DEFINITIONS_WITH_NUMERALS:
            assert found, f"{field_id} no longer carries a numeral; take it off the exception list"
            continue
        assert found is None, f"{field_id}: its name or definition carries {found!r}"


# Thread Q's papers write a yield's grams with what they weigh. Grams per gram
# whatever the labels; a kilogram, a milligram, a rate or a volume stays apart.
@pytest.mark.parametrize("raw", [
    "g EtOH/g Glucose", "g ethanol [g glucose]−1", "g biomass [g glucose]−1",
    "gDW gglucose−1", "gx/g", "gx g−1", "gE gG –1",
])
def test_a_labelled_gram_per_gram_is_grams_per_gram(raw):
    assert normalize(raw) == "g g⁻¹"


@pytest.mark.parametrize("raw, expected", [
    ("g kg-1", None), ("gx/l", None), ("g gX-1 h-1", None),
    ("mg g-1", "mg g⁻¹"), ("g.L−1", "g L⁻¹"), ("g L-1h-1", "g L⁻¹ h⁻¹"), ("g/L hr", "g L⁻¹ h⁻¹"),
])
def test_what_a_labelled_ratio_must_not_swallow(raw, expected):
    assert normalize(raw) == expected

