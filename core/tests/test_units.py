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
