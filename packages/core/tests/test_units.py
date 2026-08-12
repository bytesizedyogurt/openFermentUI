"""Fixture replay for the unit engine.

`fixtures/units.json` was captured from `src/engine/units.ts` — every case in it
is a behaviour the TypeScript exhibits today, and this file replays all 4589 of
them against the Python port. It is the parity gate, so it is deliberately dumb:
no case is skipped, reinterpreted, or given a looser tolerance than 1e-12. A
difference big enough to need a wider tolerance is a difference big enough to
corrupt the Ledger.

One test function per fixture collection, parametrised so a failure names the
case rather than the collection.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from openferment_core.units import (
    Quantity,
    as_number,
    convert,
    explain_refusal,
    fmt,
    normalize_unit,
    parse_quantity,
    quantity_equals,
    round_to_precision,
    same_family,
    to_si,
    unit_family,
)

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "units.json"
_DATA: dict[str, Any] = json.loads(FIXTURES.read_text("utf-8"))

REL_TOL = 1e-12


def _cases(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = _DATA[name]
    return rows


def _ids(name: str) -> list[str]:
    """Stable per-row ids: the collection, the row index, and the row itself."""
    return [
        f"{name}#{i}:{json.dumps(row, ensure_ascii=False)}" for i, row in enumerate(_cases(name))
    ]


def _assert_close(actual: float, expected: float, case: dict[str, Any]) -> None:
    assert math.isclose(actual, expected, rel_tol=REL_TOL), f"{actual!r} != {expected!r} for {case}"


# ── normalizeUnit ──────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("normalizeUnit"), ids=_ids("normalizeUnit"))
def test_normalize_unit(case: dict[str, Any]) -> None:
    assert normalize_unit(case["in"]) == case["out"], case


# ── unitFamily ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("unitFamily"), ids=_ids("unitFamily"))
def test_unit_family(case: dict[str, Any]) -> None:
    assert unit_family(case["in"]) == case["out"], case


# ── sameFamily ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("sameFamily"), ids=_ids("sameFamily"))
def test_same_family(case: dict[str, Any]) -> None:
    assert same_family(case["a"], case["b"]) is case["out"], case


# ── convert ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("convert"), ids=_ids("convert"))
def test_convert(case: dict[str, Any]) -> None:
    _assert_close(convert(case["value"], case["from"], case["to"]), case["out"], case)


# ── convert, across families ───────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("convertCrossFamily"), ids=_ids("convertCrossFamily"))
def test_convert_cross_family(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as excinfo:
        convert(case["value"], case["from"], case["to"])
    # The message is product surface, not a debug string: it is compared whole.
    assert str(excinfo.value) == case["error"], case


# ── toSI ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("toSI"), ids=_ids("toSI"))
def test_to_si(case: dict[str, Any]) -> None:
    got = to_si(case["value"], case["unit"])
    assert got.unit == case["out"]["unit"], case
    _assert_close(got.value, case["out"]["value"], case)


# ── explainRefusal ─────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("explainRefusal"), ids=_ids("explainRefusal"))
def test_explain_refusal(case: dict[str, Any]) -> None:
    # The `because` strings are user-facing copy; compared byte for byte.
    assert explain_refusal(case["from"], case["to"]) == case["out"], case


# ── parseQuantity ──────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("parseQuantity"), ids=_ids("parseQuantity"))
def test_parse_quantity(case: dict[str, Any]) -> None:
    got = parse_quantity(case["in"])
    if case["out"] is None:
        assert got is None, case
        return
    assert got is not None, case
    assert got.unit == case["out"]["unit"], case
    _assert_close(got.value, case["out"]["value"], case)


# ── asNumber ───────────────────────────────────────────────────────────

# JSON cannot carry NaN or ±Infinity, so the capture wrote them as strings. Both
# readings of such a row — the literal string, or the non-finite float it stands
# for — must return None, so each is checked.
_NON_FINITE_SENTINELS = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}


@pytest.mark.parametrize("case", _cases("asNumber"), ids=_ids("asNumber"))
def test_as_number(case: dict[str, Any]) -> None:
    got = as_number(case["in"])
    if case["out"] is None:
        assert got is None, case
    else:
        assert got is not None, case
        _assert_close(got, case["out"], case)
    if isinstance(case["in"], str) and case["in"] in _NON_FINITE_SENTINELS:
        assert as_number(_NON_FINITE_SENTINELS[case["in"]]) is None, case


# ── fmt ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("fmt"), ids=_ids("fmt"))
def test_fmt(case: dict[str, Any]) -> None:
    assert fmt(case["value"], case["maxDecimals"]) == case["out"], case


# ── roundToPrecision ───────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("roundToPrecision"), ids=_ids("roundToPrecision"))
def test_round_to_precision(case: dict[str, Any]) -> None:
    _assert_close(round_to_precision(case["value"], case["increment"]), case["out"], case)


# ── quantityEquals ─────────────────────────────────────────────────────


@pytest.mark.parametrize("case", _cases("quantityEquals"), ids=_ids("quantityEquals"))
def test_quantity_equals(case: dict[str, Any]) -> None:
    a = Quantity(case["a"]["value"], case["a"]["unit"])
    b = Quantity(case["b"]["value"], case["b"]["unit"])
    # `tolerancePct: null` means "call it the way a caller who does not care
    # would" — i.e. take the default — not "pass None".
    got = (
        quantity_equals(a, b)
        if case["tolerancePct"] is None
        else quantity_equals(a, b, case["tolerancePct"])
    )
    assert got is case["out"], case


# ── hostile input ──────────────────────────────────────────────────────
#
# Not from the fixture. Phase 0 captured real units, so no fixture case could
# have caught this: in JavaScript, `t in U` and `ALIASES[t]` walk the PROTOTYPE
# CHAIN, and the mirror therefore accepted every `Object.prototype` member name
# as a unit — `normalizeUnit('toString')` returned 'toString',
# `sameFamily('toString', 'constructor')` returned True, `convert` across that
# pair returned NaN without throwing, and `toSI` crashed.
#
# A Python dict has no prototype, so this file has never had that behaviour.
# These tests exist so that the canon states the rule explicitly rather than
# relying on it falling out of the language, and so the two implementations are
# pinned together on inputs the fixture will never contain.

PROTOTYPE_KEYS = [
    "toString",
    "valueOf",
    "constructor",
    "hasOwnProperty",
    "__proto__",
    "isPrototypeOf",
    "propertyIsEnumerable",
    "toLocaleString",
]


@pytest.mark.parametrize("key", PROTOTYPE_KEYS)
def test_object_prototype_names_are_not_units(key: str) -> None:
    assert normalize_unit(key) is None
    assert unit_family(key) is None
    assert parse_quantity(f"1 {key}") is None


def test_two_non_units_do_not_share_a_family() -> None:
    """The failure this guards is agreement, not error.

    A unit engine that reports two non-units as dimensionally compatible has
    fabricated the one thing it exists to establish.
    """
    assert same_family("toString", "constructor") is False
    with pytest.raises(ValueError, match="Unknown unit: toString"):
        convert(1, "toString", "constructor")


# ── divergences found by differential testing against V8 ───────────────
#
# None of these are in fixtures/units.json. Phase 0 captured the engine's real
# inputs, which is the right thing for a pin to hold, but it means the fixture
# cannot see the places where an idiomatic Python translation quietly means
# something else. These were found by running both engines over several million
# generated inputs and comparing, and each is pinned here because the fixture
# will never catch a regression in it.
#
# Written with chr() rather than as literals: every codepoint involved is
# invisible, and an invisible character in a test is one an editor can silently
# eat.

#: U+FEFF. Whitespace to JavaScript's trim(), not to Python's str.strip().
BOM = chr(0xFEFF)
#: Whitespace to Python's str.strip(), not to JavaScript's trim().
PYTHON_ONLY_SPACE = [chr(0x85), chr(0x1C), chr(0x1D), chr(0x1E), chr(0x1F)]


def test_bom_prefixed_unit_resolves() -> None:
    """A UTF-8 BOM on the first cell of a CSV is an ordinary thing to receive.

    Left unhandled, the browser resolved this to the mass-concentration unit
    while the canonical engine -- the one an extraction pipeline calls --
    refused it.
    """
    assert normalize_unit(BOM + "g/L") == "g L⁻¹"
    assert normalize_unit("g" + BOM + "L⁻¹") == "g L⁻¹"
    assert unit_family(BOM + "g/L") == "massConc"
    assert same_family(BOM + "mg/L", BOM + "g/L") is True


def test_python_only_whitespace_is_not_whitespace() -> None:
    """The same disagreement in the other direction.

    U+0085 and U+001C-U+001F are whitespace to Python and not to JavaScript.
    Accepting them would have the canonical engine resolve a unit the browser
    rejects, which is the same defect mirrored.
    """
    for ch in PYTHON_ONLY_SPACE:
        assert normalize_unit(ch + "g/L") is None
        assert normalize_unit(ch) is None


def test_round_to_precision_survives_overflow() -> None:
    """value/increment can overflow to infinity; JS returns it, Python crashed.

    math.floor raises OverflowError on an infinity, so this was a crash where
    the mirror returned a value -- the worst kind of divergence in a pipeline.
    """
    assert round_to_precision(1e308, 0.001) == math.inf
    assert round_to_precision(-1e308, 0.001) == -math.inf
    assert round_to_precision(1e300, 1e-10) == math.inf


def test_round_to_precision_both_non_finite() -> None:
    """JS reaches Math.round(inf/inf) * inf, which is NaN.

    An early return on a non-finite value handed back the infinity instead.
    """
    for value in (math.inf, -math.inf):
        for increment in (math.inf, math.nan):
            assert math.isnan(round_to_precision(value, increment))


def test_negative_max_decimals_raises_rather_than_lying() -> None:
    """fmt(5.5, -1) returned "1" -- wrong by a factor of ten, silently.

    Quantizing by 10**+1 gives "10", and the trailing-zero strip then eats the
    zero. JS throws RangeError; a canonical engine must not answer instead.
    """
    for bad in (-1, 101):
        with pytest.raises(ValueError):
            fmt(5.5, bad)
    assert fmt(5.5, 0) == "6"
    # 100 is the upper bound and is accepted. (Asking for 100 decimals of an
    # inexact double gets the exact binary expansion, which is why this uses a
    # value that is exactly representable.)
    assert fmt(5.5, 100) == "5.5"


def test_precision_finer_than_to_fixed_can_express_raises() -> None:
    """increment < 1e-99 drives toFixed past its 100-digit limit, and JS throws."""
    assert round_to_precision(2.5, 1e-99) == 2.5
    with pytest.raises(ValueError):
        round_to_precision(2.5, 1e-100)


#: Arabic-Indic five, fullwidth one, Devanagari one. Unicode decimal digits that
#: Python's `\d` matches and JavaScript's does not.
NON_ASCII_DIGITS = [chr(0x665), chr(0xFF11), chr(0x967)]
#: Excluded by JS's `.`, not by Python's: CR, LINE SEPARATOR, PARAGRAPH SEPARATOR.
JS_DOT_EXCLUDED = [chr(0x0D), chr(0x2028), chr(0x2029)]


def test_a_number_is_not_assembled_from_two_scripts() -> None:
    """ "2" + Arabic-Indic five parsed as 25.0 — a value in no input.

    Python's `\\d` matches every Unicode decimal digit and float() accepts them,
    so the canonical engine invented a number the browser refuses. Fabricated
    data is the one thing this system may not produce.
    """
    for d in NON_ASCII_DIGITS:
        assert parse_quantity(d + " g/L") is None
        assert parse_quantity("2" + d + " g") is None
    assert parse_quantity("25 g") == Quantity(25.0, "g")


def test_python_only_whitespace_does_not_separate_value_from_unit() -> None:
    """The regex separator was still Python's `\\s` after `_js_trim` landed."""
    for ch in PYTHON_ONLY_SPACE:
        assert parse_quantity("2" + ch + "g/L") is None
    assert parse_quantity("2 g/L") == Quantity(2.0, "g L⁻¹")


def test_line_separators_inside_a_unit_do_not_parse() -> None:
    """A CR *inside* the unit — a CRLF-split CSV cell — parsed here, not in JS.

    A trailing one is trimmed by both, so only the interior case diverged.
    """
    for ch in JS_DOT_EXCLUDED:
        assert parse_quantity("1 g" + ch + "L⁻¹") is None
    assert parse_quantity("1 g L⁻¹") == Quantity(1.0, "g L⁻¹")


def test_grading_a_categorical_value_scores_it_wrong_rather_than_crashing() -> None:
    """`ExtractionRecord.value` is `float | str`, so this reaches real data.

    The TypeScript wraps the conversion in a bare catch precisely so this
    predicate never throws. `except ValueError` alone did not hold: a
    categorical value reaches the arithmetic as a str and raises TypeError.
    """
    assert quantity_equals(Quantity("CK2", "g"), Quantity(5.0, "g")) is False
    assert quantity_equals(Quantity("", "g"), Quantity(5.0, "g")) is False
    assert quantity_equals(Quantity(5.0, "g"), Quantity("CK2", "g")) is False


def test_as_number_returns_none_for_an_int_too_big_to_be_a_double() -> None:
    """json.loads of a large integer literal produces exactly this.

    math.isfinite raises OverflowError on it, so the one function whose whole
    contract is "None for anything that is not a finite number" was the one
    that raised.
    """
    assert as_number(10**400) is None
    assert as_number(-(10**400)) is None
    assert as_number(10) == 10
