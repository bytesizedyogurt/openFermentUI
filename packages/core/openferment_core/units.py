"""Purpose-built unit engine for the openFerment ontology (OF-DES-001 §7.5).

Linear families use factor-to-base; temperature is affine.

This is the canonical implementation. `src/engine/units.ts` is the mirror, and
`fixtures/units.json` is the parity gate between them — every observable this
module produces (values, families, refusal copy, *and the exact text of the two
exception messages*) is pinned there.

Because the fixture was captured from the TypeScript, this port reproduces
JavaScript's semantics rather than Python's wherever the two disagree. Those
places are marked `JS:` in the comments below; none of them are accidents, and
"tidying" one of them silently breaks the cross-language gate. The four that
bite hardest:

* `Math.round` rounds halves toward +∞; Python's `round` rounds halves to even.
* `Number.prototype.toFixed`/`toExponential` round the *exact binary value* with
  ties away from zero; Python's `format` rounds ties to even.
* `String.replace(regex)` without the `/g` flag replaces once; Python's
  `str.replace` and `re.sub` replace every occurrence unless told otherwise.
* A regex `$` in JavaScript (no `/m`) means end-of-string; in Python it also
  matches just before a trailing newline.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from types import MappingProxyType
from typing import Final, NamedTuple

__all__ = [
    "REFUSAL_PAIRS",
    "SI_UNIT_BY_FAMILY",
    "UNIT_ALIASES",
    "UNIT_TABLE",
    "Quantity",
    "Refusal",
    "UnitDef",
    "as_number",
    "convert",
    "explain_refusal",
    "fmt",
    "normalize_unit",
    "parse_quantity",
    "quantity_equals",
    "round_to_precision",
    "same_family",
    "to_si",
    "unit_family",
]


@dataclass(frozen=True, slots=True)
class UnitDef:
    """One canonical unit.

    `factor` multiplies to the family base; `offset` makes the mapping affine
    (temperature): base = value * factor + offset.

    Field order differs from the TypeScript interface by necessity: TS declares
    `offset?` third and `label` fourth, but an optional field has to come last
    in Python. `label` is the canonical display form, which is *not* always the
    table key — `g 100mL⁻¹` displays as `g 100 mL⁻¹`, and `colonies µg⁻¹`
    displays as `colonies µg⁻¹ DNA`.
    """

    family: str
    factor: float
    label: str
    offset: float | None = None


class Quantity(NamedTuple):
    """A value with its unit — the `{ value, unit }` object the TS returns."""

    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class Refusal:
    """One row of `REFUSAL_PAIRS`: two families, and why the engine won't bridge them."""

    a: str
    b: str
    because: str


# Family base units: rate=h⁻¹, time=h, massConc=g L⁻¹, mass=g, volume=L,
# percent=%, yield=g g⁻¹, volProd=g L⁻¹ h⁻¹, specProd=mg g⁻¹ h⁻¹,
# odDcw=g L⁻¹ OD⁻¹, temp=°C, light=µmol m⁻² s⁻¹, ph=(none), molar=mol L⁻¹
#
# JS: insertion order is load-bearing. `normalizeUnit`'s last resort scans
# `Object.keys(U)` and returns the FIRST key whose superscript-stripped form
# matches, so this dict is transcribed in the TypeScript's exact order. (No two
# keys currently strip to the same string, so the scan is unambiguous today —
# but that is a property of the data, not a guarantee, and reordering the table
# is exactly how it would stop being true.)
#
# Every non-terminating factor stays written as the division the TypeScript
# wrote (1/24, 1/60, 1/3600, 5/9, -160/9, 1/3.6). A hand-transcribed decimal
# would be a different double and would drift from the fixture.
_U: Final[dict[str, UnitDef]] = {
    "h⁻¹": UnitDef("rate", 1, "h⁻¹"),
    "d⁻¹": UnitDef("rate", 1 / 24, "d⁻¹"),
    "min⁻¹": UnitDef("rate", 60, "min⁻¹"),
    "h": UnitDef("time", 1, "h"),
    "min": UnitDef("time", 1 / 60, "min"),
    "d": UnitDef("time", 24, "d"),
    "s": UnitDef("time", 1 / 3600, "s"),
    "g L⁻¹": UnitDef("massConc", 1, "g L⁻¹"),
    "mg L⁻¹": UnitDef("massConc", 0.001, "mg L⁻¹"),
    "µg L⁻¹": UnitDef("massConc", 0.000001, "µg L⁻¹"),
    "kg m⁻³": UnitDef("massConc", 1, "kg m⁻³"),
    "mg mL⁻¹": UnitDef("massConc", 1, "mg mL⁻¹"),
    "µg mL⁻¹": UnitDef("massConc", 0.001, "µg mL⁻¹"),
    "mg dL⁻¹": UnitDef("massConc", 0.01, "mg dL⁻¹"),
    "g 100mL⁻¹": UnitDef("massConc", 10, "g 100 mL⁻¹"),
    "g": UnitDef("mass", 1, "g"),
    "mg": UnitDef("mass", 0.001, "mg"),
    "µg": UnitDef("mass", 0.000001, "µg"),
    "kg": UnitDef("mass", 1000, "kg"),
    "L": UnitDef("volume", 1, "L"),
    "mL": UnitDef("volume", 0.001, "mL"),
    "µL": UnitDef("volume", 0.000001, "µL"),
    "m³": UnitDef("volume", 1000, "m³"),
    "%": UnitDef("percent", 1, "%"),
    "% DW": UnitDef("percent", 1, "% DW"),
    "% v/v": UnitDef("percent", 1, "% v/v"),
    "% w/v": UnitDef("percent", 1, "% w/v"),
    "g g⁻¹": UnitDef("yield", 1, "g g⁻¹"),
    "mg g⁻¹": UnitDef("yield", 0.001, "mg g⁻¹"),
    "g L⁻¹ h⁻¹": UnitDef("volProd", 1, "g L⁻¹ h⁻¹"),
    "mg L⁻¹ h⁻¹": UnitDef("volProd", 0.001, "mg L⁻¹ h⁻¹"),
    "g L⁻¹ d⁻¹": UnitDef("volProd", 1 / 24, "g L⁻¹ d⁻¹"),
    "mg g⁻¹ h⁻¹": UnitDef("specProd", 1, "mg g⁻¹ h⁻¹"),
    "g g⁻¹ h⁻¹": UnitDef("specProd", 1000, "g g⁻¹ h⁻¹"),
    "mg g⁻¹ d⁻¹": UnitDef("specProd", 1 / 24, "mg g⁻¹ d⁻¹"),
    "g L⁻¹ OD⁻¹": UnitDef("odDcw", 1, "g L⁻¹ OD⁻¹"),
    "°C": UnitDef("temp", 1, "°C", offset=0),
    "K": UnitDef("temp", 1, "K", offset=-273.15),
    "°F": UnitDef("temp", 5 / 9, "°F", offset=-160 / 9),
    "µmol m⁻² s⁻¹": UnitDef("light", 1, "µmol m⁻² s⁻¹"),
    "µE m⁻² s⁻¹": UnitDef("light", 1, "µE m⁻² s⁻¹"),
    "": UnitDef("ph", 1, ""),
    "mol L⁻¹": UnitDef("molar", 1, "mol L⁻¹"),
    "mmol L⁻¹": UnitDef("molar", 0.001, "mmol L⁻¹"),
    "µmol L⁻¹": UnitDef("molar", 0.000001, "µmol L⁻¹"),
    "vvm": UnitDef("vvm", 1, "vvm"),
    "rpm": UnitDef("rpm", 1, "rpm"),
    "µm": UnitDef("length", 0.000001, "µm"),
    "cm": UnitDef("length", 0.01, "cm"),
    "m": UnitDef("length", 1, "m"),
    "nm": UnitDef("length", 1e-9, "nm"),
    "mm": UnitDef("length", 0.001, "mm"),
    # ── OF-COR-001 §17 ontology v1 ──────────────────────────────────────
    # Expression share. Deliberately its OWN family, not `percent`: a share of
    # total soluble protein is not interconvertible with a concentration, and
    # keeping it separate makes the engine refuse by construction (Rule 2).
    "% TSP": UnitDef("proteinShare", 1, "% TSP"),
    "% TCP": UnitDef("proteinShare", 1, "% TCP"),
    "% of native sites": UnitDef("percent", 1, "% of native sites"),
    "% sedimentable": UnitDef("percent", 1, "% sedimentable"),
    "% of total expressed": UnitDef("percent", 1, "% of total expressed"),
    "% of total protein": UnitDef("percent", 1, "% of total protein"),
    "mol mol⁻¹": UnitDef("stoichiometry", 1, "mol mol⁻¹"),
    "×": UnitDef("fold", 1, "×"),
    "colonies µg⁻¹": UnitDef("transformationEff", 1, "colonies µg⁻¹ DNA"),
    "residue": UnitDef("position", 1, "residue"),
    "kWh kg⁻¹": UnitDef("energyPerMass", 1, "kWh kg⁻¹"),
    "MJ kg⁻¹": UnitDef("energyPerMass", 1 / 3.6, "MJ kg⁻¹"),
    # Currency is per-family on purpose. Converting EUR/kg to USD/kg needs an
    # exchange rate with a date, which a unit engine has no business inventing —
    # and OF-COR-001 §16 carries costs in both (Acién 69 €/kg, GFI $4–6/kg).
    "USD kg⁻¹": UnitDef("costUSD", 1, "USD kg⁻¹"),
    "EUR kg⁻¹": UnitDef("costEUR", 1, "EUR kg⁻¹"),
}

# Conversions the engine refuses *with an explanation* rather than a bare
# dimension error (OF-COR-001 §17 Rule 2). Dimensional analysis already blocks
# these; the point of this table is that the UI can say why, turning the unit
# engine from a convenience into an epistemic guardrail.
#
# The `because` strings are user-facing product copy and are pinned byte for
# byte by the fixture, em dashes (—) included. Do not reword or reflow them.
_REFUSALS: Final[tuple[Refusal, ...]] = (
    Refusal(
        a="proteinShare",
        b="massConc",
        because="A share of total soluble protein and a concentration are not interconvertible without the cell density and the total-protein fraction of the biomass. Record those two values and the conversion becomes possible; guessing them would fabricate a titer.",
    ),
    Refusal(
        a="proteinShare",
        b="percent",
        because="Both are percentages but of different denominators — % of total soluble protein is not % of dry weight or % of native phosphorylation sites. Comparing them directly is a category error.",
    ),
    Refusal(
        a="costUSD",
        b="costEUR",
        because="Currency conversion needs an exchange rate with a date attached. The engine will not invent one — record the rate and the date as an explicit assumption.",
    ),
)

# The SI/canonical display unit chosen per family for the "SI twin".
_SI_UNIT: Final[dict[str, str]] = {
    "proteinShare": "% TSP",
    "stoichiometry": "mol mol⁻¹",
    "fold": "×",
    "transformationEff": "colonies µg⁻¹",
    "position": "residue",
    "energyPerMass": "kWh kg⁻¹",
    "costUSD": "USD kg⁻¹",
    "costEUR": "EUR kg⁻¹",
    "rate": "h⁻¹",
    "time": "h",
    "massConc": "kg m⁻³",
    "mass": "g",
    "volume": "L",
    "percent": "%",
    "yield": "g g⁻¹",
    "volProd": "g L⁻¹ h⁻¹",
    "specProd": "mg g⁻¹ h⁻¹",
    "odDcw": "g L⁻¹ OD⁻¹",
    "temp": "°C",
    "light": "µmol m⁻² s⁻¹",
    "ph": "",
    "molar": "mol L⁻¹",
    "vvm": "vvm",
    "rpm": "rpm",
    "length": "m",
}

# Alias normalization: accept human/ASCII notations.
#
# Case is the whole point of several of these, and they only work because
# `normalize_unit` tries the canonical table first, then the alias table
# case-sensitively, then case-insensitively:
#   "m"  hits _U   → metre        "M"  falls to _ALIASES["m"]  → mol L⁻¹
#   "mm" hits _U   → millimetre   "mM" falls to _ALIASES["mm"] → mmol L⁻¹
#   "µm" hits _U   → micrometre   "µM" falls to _ALIASES["µm"] → µmol L⁻¹
# The "m"/"mm"/"µm" entries here are therefore only ever reachable through the
# lowercased lookup. "um" has no canonical-table entry, so it resolves to
# µmol L⁻¹ — not micrometre.
_ALIASES: Final[dict[str, str]] = {
    "1/h": "h⁻¹",
    "h-1": "h⁻¹",
    "/h": "h⁻¹",
    "per hour": "h⁻¹",
    "1/d": "d⁻¹",
    "d-1": "d⁻¹",
    "/d": "d⁻¹",
    "/day": "d⁻¹",
    "per day": "d⁻¹",
    "g/l": "g L⁻¹",
    "g/L": "g L⁻¹",
    "mg/l": "mg L⁻¹",
    "mg/L": "mg L⁻¹",
    "ug/l": "µg L⁻¹",
    "µg/L": "µg L⁻¹",
    "kg/m3": "kg m⁻³",
    "kg/m³": "kg m⁻³",
    "mg/ml": "mg mL⁻¹",
    "mg/mL": "mg mL⁻¹",
    "ug/ml": "µg mL⁻¹",
    "µg/mL": "µg mL⁻¹",
    "mg/dl": "mg dL⁻¹",
    "mg/dL": "mg dL⁻¹",
    "g/100ml": "g 100mL⁻¹",
    "g/100 mL": "g 100mL⁻¹",
    "g/g": "g g⁻¹",
    "mg/g": "mg g⁻¹",
    "g/l/h": "g L⁻¹ h⁻¹",
    "g/L/h": "g L⁻¹ h⁻¹",
    "mg/l/h": "mg L⁻¹ h⁻¹",
    "mg/L/h": "mg L⁻¹ h⁻¹",
    "g/l/d": "g L⁻¹ d⁻¹",
    "g/L/d": "g L⁻¹ d⁻¹",
    "mg/g/h": "mg g⁻¹ h⁻¹",
    "g/g/h": "g g⁻¹ h⁻¹",
    "mg/g/d": "mg g⁻¹ d⁻¹",
    "g/l/od": "g L⁻¹ OD⁻¹",
    "g/L/OD": "g L⁻¹ OD⁻¹",
    "c": "°C",
    "°c": "°C",
    "degc": "°C",
    "deg c": "°C",
    "f": "°F",
    "°f": "°F",
    "k": "K",
    "umol/m2/s": "µmol m⁻² s⁻¹",
    "µmol/m²/s": "µmol m⁻² s⁻¹",
    "ue/m2/s": "µE m⁻² s⁻¹",
    "%dw": "% DW",
    "% dw": "% DW",
    "%v/v": "% v/v",
    "% vv": "% v/v",
    "%w/v": "% w/v",
    "m": "mol L⁻¹",
    "mm": "mmol L⁻¹",
    "um": "µmol L⁻¹",
    "µm": "µmol L⁻¹",
    "mol/l": "mol L⁻¹",
    "mmol/l": "mmol L⁻¹",
    "ml": "mL",
    "ul": "µL",
    "µl": "µL",
    "l": "L",
    "m3": "m³",
}

# The unit and alias tables, exported read-only so a fixture capture can be
# exhaustive rather than transcribed.
#
# Phase 0 of the Python migration pins this engine's behaviour as
# language-neutral JSON, and a hand-written list of "the units I remembered"
# would pin the wrong thing — the one alias nobody typed into the fixture is
# exactly the one that would silently diverge. Exporting the tables costs
# nothing at runtime and makes the capture provably complete.
UNIT_TABLE: Final[Mapping[str, UnitDef]] = MappingProxyType(_U)
UNIT_ALIASES: Final[Mapping[str, str]] = MappingProxyType(_ALIASES)
SI_UNIT_BY_FAMILY: Final[Mapping[str, str]] = MappingProxyType(_SI_UNIT)
#: Cross-family pairs the engine refuses with an explanation rather than a bare error.
REFUSAL_PAIRS: Final[tuple[Refusal, ...]] = _REFUSALS


# ── JavaScript number semantics ────────────────────────────────────────
# Three helpers that exist only because the fixture was captured from V8.


def _js_math_round(x: float) -> float:
    """`Math.round`: nearest integer, ties toward +∞.

    JS: `Math.round(2.5) === 3` and `Math.round(-2.5) === -2`. Python's builtin
    `round` is banker's rounding — `round(2.5) == 2` — so it cannot be used.
    """
    # The obvious spelling, floor(x + 0.5), is wrong: `x + 0.5` can itself round
    # UP to an integer in binary. The classic case is 0.49999999999999994, where
    # V8 returns 0 but floor(x + 0.5) gives 1. Comparing the fractional part
    # instead keeps the arithmetic exact — `x - floor(x)` is exact for every
    # finite double — and states the spec rule directly: nearest, ties up.
    # JS: Math.round(±∞) is ±∞ and Math.round(NaN) is NaN. math.floor raises
    # OverflowError on an infinity and ValueError on a NaN, so a non-finite
    # quotient — which round_to_precision reaches whenever value/increment
    # overflows — would crash here rather than propagate.
    if not math.isfinite(x):
        return x
    f = math.floor(x)
    return f + 1 if x - f >= 0.5 else f


def _js_to_fixed(x: float, digits: int) -> str:
    """`Number.prototype.toFixed(digits)`.

    JS rounds the EXACT binary value of the double and breaks ties AWAY FROM
    ZERO (the spec negates first, then picks the larger integer on a tie).
    Python's `format(x, ".Nf")` rounds ties to even, so the two disagree on
    exactly-representable ties: `(2.5).toFixed(0)` is "3" where
    `format(2.5, ".0f")` is "2", and `(0.125).toFixed(2)` is "0.13" where
    `format(0.125, ".2f")` is "0.12".

    `Decimal(float)` is exact, so quantizing it with ROUND_HALF_UP on the
    absolute value reproduces the spec exactly — including the cases where JS
    looks like it rounds "wrong", e.g. `(1.005).toFixed(2) === "1.00"`, because
    the stored double is 1.00499999999999989....
    """
    # JS throws RangeError outside [0, 100], and — unlike toExponential — it
    # does so BEFORE looking at the value, so (NaN).toFixed(-1) throws while
    # (NaN).toFixed(0) is "NaN". Verified against V8, not assumed.
    #
    # Without this check a negative `digits` does not fail, it LIES: quantizing
    # by 10**+1 gives "10" for 5.5, and fmt's trailing-zero strip then eats the
    # zero, so fmt(5.5, -1) returns "1" — wrong by a factor of ten, silently.
    if digits < 0 or digits > 100:
        raise ValueError(f"toFixed() digits argument must be between 0 and 100, got {digits}")
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "-Infinity" if x < 0 else "Infinity"
    # JS: `x < 0` is false for -0, so -0 formats without a sign, but -0.4
    # formats as "-0" — the sign is taken before rounding, never after.
    sign = "-" if x < 0 else ""
    ax = abs(x)
    # JS: at 1e21 and above toFixed gives up and returns ToString(x). Python's
    # repr agrees with JS's shortest-round-trip form at these magnitudes.
    if ax >= 1e21:
        return sign + repr(ax)
    with localcontext() as ctx:
        # Room for 21 integer digits plus toFixed's 100-digit maximum.
        ctx.prec = 400
        d = Decimal(ax).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return sign + format(d, "f")


def _js_to_exponential(x: float, digits: int) -> str:
    """`Number.prototype.toExponential(digits)`.

    Same exact-binary, ties-away-from-zero rule as `_js_to_fixed`, plus an
    UNPADDED exponent: JS gives "1.23e+5" where `format(x, ".2e")` gives
    "1.23e+05". `fmt` re-parses the exponent as a number so the padding does not
    survive, but the mantissa substring is used verbatim — so it has to be
    rounded the JS way.
    """
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "-Infinity" if x < 0 else "Infinity"
    # The range check is here rather than first because toExponential orders it
    # the other way round from toFixed: (NaN).toExponential(-1) is "NaN" but
    # (1.5).toExponential(-1) throws. Confirmed against V8.
    if digits < 0 or digits > 100:
        raise ValueError(f"toExponential() argument must be between 0 and 100, got {digits}")
    sign = "-" if x < 0 else ""
    ax = abs(x)
    if ax == 0:
        exp = 0
        ds = "0" * (digits + 1)
    else:
        with localcontext() as ctx:
            ctx.prec = 400
            d = Decimal(ax)
            # `adjusted()` reads the exact binary expansion, so for 1e-6 (stored
            # as 9.99999999999999954...e-7) it reports -7, not -6. The carry
            # branch below puts that right, and also covers real carries such as
            # (999999.5).toExponential(2) === "1.00e+6".
            exp = d.adjusted()
            q = d.quantize(Decimal(1).scaleb(exp - digits), rounding=ROUND_HALF_UP)
        ds = "".join(str(t) for t in q.as_tuple().digits)
        if len(ds) > digits + 1:
            exp += 1
            ds = ds[: digits + 1]
    mantissa = ds[0] + ("." + ds[1:] if digits > 0 else "")
    return f"{sign}{mantissa}e{'+' if exp >= 0 else '-'}{abs(exp)}"


# ── the engine ─────────────────────────────────────────────────────────


#: Largest int that survives conversion to a double. Beyond it math.isfinite
#: raises rather than returning False.
_MAX_FLOAT_INT: Final = 2**1024


def as_number(v: float | str) -> float | None:
    """Narrow a record value to a number, or None if it is categorical.

    Call sites that convert or compute MUST go through this rather than casting
    — a categorical value silently coerced to NaN would poison a median.

    JS tests `typeof v === 'number'`, under which `true` is a boolean and not a
    number. Python's `bool` is a subclass of `int`, so `isinstance(True, int)`
    is True and a naive check would hand back 1 for a flag that was never a
    measurement. Booleans are therefore rejected explicitly, matching JS. (The
    fixture pins no boolean row — it pins numbers, the non-finite sentinels, and
    strings — so this is a deliberate choice, not a captured behaviour.)
    """
    if isinstance(v, bool):
        return None
    # An int outside double range — which `json.loads` produces from a large
    # integer literal — makes `math.isfinite` raise OverflowError. The one
    # function whose entire contract is "None for anything that is not a finite
    # number" must not be the one that raises; JS has no such value at all
    # (it would already be Infinity, hence null).
    if isinstance(v, int) and not -_MAX_FLOAT_INT <= v <= _MAX_FLOAT_INT:
        return None
    # JS: `isFinite` is false for NaN and for both infinities.
    if isinstance(v, (int, float)) and math.isfinite(v):
        return v
    return None


def explain_refusal(from_unit: str, to_unit: str) -> str | None:
    """If a refusal is a known trap, explain it; otherwise return None.

    Takes two UNIT STRINGS, not a record: a refusal explains what the
    CONVERSION needs, not what one particular record happens to be missing.
    """
    # JS: `U[normalizeUnit(x) ?? '']` — the null-coalescing fallback is the
    # empty string, which is a REAL key in the unit table (the pH family). An
    # unknown unit therefore lands on `ph` rather than on undefined. It changes
    # nothing today because no refusal pair names `ph`, so unknown units still
    # return None; it is transcribed rather than "fixed" so that adding a `ph`
    # refusal later fails the fixture loudly instead of quietly diverging.
    nf = normalize_unit(from_unit)
    nt = normalize_unit(to_unit)
    f = _U.get(nf if nf is not None else "")
    t = _U.get(nt if nt is not None else "")
    if f is None or t is None or f.family == t.family:
        return None
    for r in _REFUSALS:
        if (r.a == f.family and r.b == t.family) or (r.b == f.family and r.a == t.family):
            return r.because
    return None


# JavaScript's whitespace set, which is NOT Python's.
#
# `String.prototype.trim` and the regex `\s` both use WhiteSpace + LineTerminator:
# the ASCII controls, space, NBSP, every Unicode Zs, U+2028, U+2029 — and
# U+FEFF, the byte-order mark. Python's `str.strip()` and `\s` instead follow
# `str.isspace()`, which EXCLUDES U+FEFF and INCLUDES U+001C–U+001F and U+0085.
#
# So the two disagree in both directions on six codepoints. The one that matters
# is U+FEFF: a UTF-8 BOM on the first cell of a CSV is an ordinary thing to
# receive, and it would mean the browser resolved "\ufeffg/L" to g L⁻¹ while the
# canonical engine — the one an extraction pipeline calls — refused it. The
# separator controls going the other way are noise, but they are noise the two
# implementations disagreed about.
#
# Spelled out rather than derived, because the point is to be JS's set and not
# whatever the running Python happens to think a space is.
_JS_WS = (
    "\t\n\v\f\r \u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000\ufeff"
)
_JS_WS_RUN = re.compile(f"[{re.escape(_JS_WS)}]+")


def _js_trim(s: str) -> str:
    """`String.prototype.trim` — see `_JS_WS`. Not `str.strip()`."""
    return s.strip(_JS_WS)


def _strip(s: str) -> str:
    """Superscript-insensitive, case-insensitive, whitespace-collapsed key form.

    JS: every `.replace()` here carries the `/g` flag, so all occurrences go —
    which is what Python's `str.replace`/`re.sub` do by default. Order matters:
    `⁻¹ ⁻² ⁻³` are consumed before the bare `³ ²` rules, so `kg m⁻³` becomes
    `kg m-3` and not `kg m⁻3`. There is deliberately no rule for a bare `¹`.
    """
    s = (
        s.replace("⁻¹", "-1")
        .replace("⁻²", "-2")
        .replace("⁻³", "-3")
        .replace("³", "3")
        .replace("²", "2")
    )
    # Collapses runs of whitespace but does not trim — same as the TS. The
    # character class is JS's `\s`, not Python's; see `_JS_WS`.
    return _JS_WS_RUN.sub(" ", s).lower()


def normalize_unit(raw: str) -> str | None:
    """Resolve any accepted spelling to a canonical key of `UNIT_TABLE`.

    The lookup ORDER is load-bearing and case sensitivity is the whole point:

        exact key in the unit table
        → alias table, exact
        → alias table, lowercased
        → superscript-stripped scan of the unit-table keys

    That order is what makes "m" a metre while "M" is mol L⁻¹, "mm" a
    millimetre while "mM" is mmol L⁻¹, and "µm" a micrometre while "µM" is
    µmol L⁻¹. Reordering these four steps, or lowercasing earlier, turns a
    micromolar into a micrometre without any error being raised.
    """
    # `_js_trim`, not `str.strip()` — the two strip different characters, and
    # the difference is in the INPUT rather than in the table, so "no unit
    # contains one" does not make it safe. See `_JS_WS`.
    t = _js_trim(raw)
    # NOT ported, deliberately: in JS `t in U` walks the prototype chain, so
    # `normalizeUnit('toString')` returns "toString", `unitFamily` of it is
    # `undefined` (not null, in defiance of the signature), `sameFamily` calls
    # two such non-units the SAME family, `convert` between them returns NaN
    # without throwing, `parseQuantity('1 constructor')` yields a record with
    # unit "constructor", and `toSI(1, 'toString')` throws a TypeError. A Python
    # dict has no prototype, so this file is correct by construction — and a
    # fabricated unit is exactly what must not be reproduced for the sake of
    # parity. The fixture pins no such case, so nothing here contradicts it.
    if t in _U:
        return t
    lower = t.lower()
    # JS: `if (ALIASES[t])` is a TRUTHINESS test, not a presence test — an alias
    # mapping to "" would be skipped. Python's falsy empty string matches that.
    if _ALIASES.get(t):
        return _ALIASES[t]
    if _ALIASES.get(lower):
        return _ALIASES[lower]
    # Try unicode-superscript-insensitive match.
    target = _strip(t)
    # JS: `for (const key of Object.keys(U))` returns the FIRST match in
    # insertion order; `_U` is transcribed in the TypeScript's order to match.
    for key in _U:
        if _strip(key) == target:
            return key
    return None


def unit_family(unit: str) -> str | None:
    n = normalize_unit(unit)
    return None if n is None else _U[n].family


def same_family(a: str, b: str) -> bool:
    fa = unit_family(a)
    fb = unit_family(b)
    return fa is not None and fa == fb


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value between two units of the same family. Raises on mismatch.

    The two messages are pinned character for character by the fixture:
        Unknown unit: {raw}
        Incompatible units: {from} ({from_family}) vs {to} ({to_family})
    Note that the incompatible-units message quotes the CALLER'S strings, not
    the normalised ones — a user who typed "g/l" is told about "g/l".

    (`from` and `to` in the TypeScript signature; `from` is a keyword here.)
    """
    nf = normalize_unit(from_unit)
    nt = normalize_unit(to_unit)
    if nf is None:
        raise ValueError(f"Unknown unit: {from_unit}")
    if nt is None:
        raise ValueError(f"Unknown unit: {to_unit}")
    uf = _U[nf]
    ut = _U[nt]
    if uf.family != ut.family:
        raise ValueError(
            f"Incompatible units: {from_unit} ({uf.family}) vs {to_unit} ({ut.family})"
        )
    # JS: `uf.offset ?? 0` — null-coalescing, so an explicit `offset: 0` (°C)
    # is kept and only a missing offset defaults.
    base = value * uf.factor + (uf.offset if uf.offset is not None else 0)
    return (base - (ut.offset if ut.offset is not None else 0)) / ut.factor


def to_si(value: float, unit: str) -> Quantity:
    """SI-normalized twin per §7.5 (family's designated SI display unit).

    An unknown unit is returned UNCHANGED — value and unit both. This does not
    raise and does not return None: the SI twin is a display convenience, and a
    record whose unit the engine does not recognise still has to render.
    """
    n = normalize_unit(unit)
    if n is None:
        return Quantity(value, unit)
    si = _SI_UNIT[_U[n].family]
    return Quantity(convert(value, n, si), si)


# The JS original is
#   /^(-?\d+(?:[.,]\d+)?(?:[eE]-?\d+)?)\s*(.*)$/
# and three pieces of it mean something different in Python. All three are
# written out rather than translated character for character, because each one
# makes the canonical engine ACCEPT text the browser rejects — and the engine's
# job is to refuse what it cannot justify.
#
#  `\d`   JS matches ASCII 0-9. Python matches every Unicode decimal digit, and
#         `float()` then accepts them, so "٥ g/L" parsed as 5.0 and — worse —
#         "2٥ g" parsed as 25.0, a number assembled from two different scripts
#         that appears nowhere in the input. That is fabricated data, which is
#         the one thing this system may not do (invariant 2).
#
#  `\s`   JS's whitespace set, not Python's; see `_JS_WS`. Python's `\s` matches
#         U+0085 and U+001C-U+001F, so "2<U+0085>g/L" parsed here and not there.
#
#  `.`    JS's dot excludes \n \r U+2028 U+2029; Python's excludes only \n. A CR
#         *inside* a unit — a CRLF-split CSV cell — parsed here and not there.
#
# `\Z` rather than `$`: Python's `$` also matches just before a trailing newline,
# which would let "1 g\n" parse. Note also that the exponent accepts only a
# MINUS sign, so "1e+3 g" is not a quantity in either implementation.
_JS_DOT = "[^\n\r\u2028\u2029]"
_QUANTITY_RE: Final = re.compile(
    r"^(-?[0-9]+(?:[.,][0-9]+)?(?:[eE]-?[0-9]+)?)"
    rf"[{re.escape(_JS_WS)}]*({_JS_DOT}*)\Z"
)


def parse_quantity(text: str) -> Quantity | None:
    """Parse free text like "2 g/L", "0.15 h⁻¹", "200 mg/dL", "25 °C"."""
    m = _QUANTITY_RE.match(_js_trim(text))
    if not m:
        return None
    # JS: `"str".replace(",", ".")` with a string needle replaces only the FIRST
    # comma; Python's `str.replace` replaces all of them. The regex admits at
    # most one comma so the two agree here — `count=1` keeps it that way if the
    # number grammar ever grows a thousands separator.
    value = float(m.group(1).replace(",", ".", 1))
    if not math.isfinite(value):
        return None
    raw_unit = _js_trim(m.group(2))
    if raw_unit == "":
        return Quantity(value, "")
    unit = normalize_unit(raw_unit)
    if unit is None:
        return None
    return Quantity(value, unit)


_SUPERSCRIPT: Final[dict[str, str]] = {
    "-": "⁻",
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
}


def _superscript(n: int) -> str:
    """Real superscript digits, matching the unit strings the corpus already uses."""
    return "".join(_SUPERSCRIPT.get(c, c) for c in str(n))


def fmt(value: float | str, max_decimals: int = 3) -> str:
    """Format a number for display: sensible significant digits, no trailing noise.

    Categorical records (kinase_identity, glycan_species) carry a string, and
    the right rendering for those is the string itself — so this passes them
    through rather than producing NaN.
    """
    if isinstance(value, str):
        return value
    if not math.isfinite(value):
        return "—"
    if value == 0:  # JS: `value === 0` is true for -0 as well.
        return "0"
    abs_value = abs(value)

    # Scientific notation only where a plain number stops being readable. An MSP
    # of 20437 USD/kg read as "2.04×10⁴" is worse than "20,437" — the reader has
    # to decode it before they can judge it. Above a million, the reverse.
    if abs_value >= 1e6 or abs_value < 0.001:
        mantissa, exp = _js_to_exponential(value, 2).split("e")
        # JS: `Number(exp)` on "+8"/"-6"; the mantissa string is used verbatim.
        return f"{mantissa}×10{_superscript(int(exp))}"

    decimals = max_decimals
    if abs_value >= 100:
        decimals = min(1, max_decimals)
    elif abs_value >= 10:
        decimals = min(2, max_decimals)
    # JS: `/\.?0+$/` has NO `/g` flag, so `String.replace` strips ONE match —
    # hence `count=1`. The rule is blunter than it looks and the fixture pins
    # the consequences: fmt(100, 0) is "1" and fmt(0.0012, 0) is "", because
    # "100" and "0" lose their trailing zeros with no decimal point in sight.
    s = re.sub(r"\.?0+\Z", "", _js_to_fixed(value, decimals), count=1)

    # Group the integer part once numbers get long enough to miscount at a glance.
    if abs_value >= 10000:
        int_part, _, frac = s.partition(".")
        # JS: this regex DOES carry `/g`, so every group separator is inserted.
        grouped = re.sub(r"\B(?=(\d{3})+(?!\d))", ",", int_part)
        return f"{grouped}.{frac}" if frac else grouped
    return s


def _js_decimals_for(increment: float) -> int:
    """JS: `Math.max(0, -Math.floor(Math.log10(increment)) + 1)`.

    Only the non-finite cases need help, and both collapse to 0.
    `Math.log10(∞)` is ∞ and `Math.floor(∞)` is ∞, so `-∞ + 1` is `-∞` and
    `Math.max` clamps to 0; `Math.log10(NaN)` is NaN and `Math.max(0, NaN)` is
    NaN, which `toFixed`'s ToIntegerOrInfinity then coerces to 0. Python's
    `math.floor` raises on both instead of propagating them.
    """
    if not math.isfinite(increment):
        return 0
    return max(0, -math.floor(math.log10(increment)) + 1)


def round_to_precision(value: float, increment: float) -> float:
    """Round to a precision increment (e.g. 0.1 g) for pipettable recipes."""
    if increment <= 0:
        return value
    # Deliberately no short-circuit on a non-finite value. JS has none either,
    # and the arithmetic below reaches the right answer on its own now that
    # _js_math_round passes infinities through: for value=±∞ and increment=∞ the
    # quotient is NaN and JS returns NaN, whereas returning `value` early would
    # hand back ±∞. The two disagreed on exactly those four combinations.
    rounded = _js_math_round(value / increment) * increment
    decimals = _js_decimals_for(increment)
    # JS: parseFloat(rounded.toFixed(decimals)) — the round-trip through a fixed
    # string is what clears the binary dust (25 * 0.1 → 2.5000000000000004 → 2.5).
    return float(_js_to_fixed(rounded, decimals))


def quantity_equals(a: Quantity, b: Quantity, tolerance_pct: float = 2) -> bool:
    """Are two quantities equivalent within a tolerance (for checkpoint grading)?"""
    if not same_family(a.unit, b.unit):
        return False
    try:
        av = convert(a.value, a.unit, b.unit)
        if b.value == 0:
            return abs(av) < 1e-12
        return abs(av - b.value) / abs(b.value) <= tolerance_pct / 100
    except (TypeError, ValueError):
        # The TS wraps this in a bare `catch` precisely so the predicate never
        # throws, and the narrower `except ValueError` did not hold: a
        # categorical record value ("CK2", a glycan species) reaches the
        # arithmetic as a str and raises TypeError, so grading a checkpoint
        # against one crashed the caller instead of scoring it wrong. Records
        # really do carry categorical values — `ExtractionRecord.value` is
        # `float | str` — so this is reachable from real data.
        #
        # DELIBERATE DIFFERENCE, the only one in this module. JS coerces a
        # NUMERIC string, so quantityEquals({value: "5"}, {value: 5}) is `true`
        # there and False here. Both signatures say `float`, so neither is
        # reachable without lying to the type checker, and importing JS's
        # implicit string-to-number coercion into the canonical engine to match
        # would be porting the accident rather than the behaviour.
        return False
