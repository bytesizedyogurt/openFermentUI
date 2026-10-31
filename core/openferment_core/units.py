"""Units — the engine's tables and the record fields (OF-BLD-012 §5.3).

The four tables — the unit definitions, the alias map, the per-family SI
twin, and the refusals that carry a reason — live in `schema/units.json`, and
the record fields in `schema/fields.yaml` (alpha 2.0 moved both out of the
TypeScript seed's projection, ADR-010). `src/engine/units.ts` runs the same
tables in the browser until the client takes its conversions from the
service (stage 7); the fixture `scripts/export-unit-fixtures.ts` records from
it and `tests/test_units.py` asserts against pair by pair.

THE FUNCTIONS MIRROR THE TYPESCRIPT LINE FOR LINE, including the order of
operations in `convert` and the sequence of replacements in `_strip`. That is
not pedantry: the fixture test asserts exact equality on floats, and it can
only do that because both sides perform the same IEEE operations in the same
order. Change a step here, change it there, or the test says which one moved.

WHY THIS EXISTS. §2.4's anchoring rule 4 says a candidate's unit must
normalise, and normalise into the family of the field's canonical unit; rule 5
says the value, converted to that unit, must fall inside the field's range.
Both need a unit engine on the Python side that agrees with the browser about
what `mg·L⁻¹` means, or a candidate the service accepts could be one the screen
cannot display.

Raises rather than guesses. An unknown unit is `UnitError`, an incompatible
pair is `UnitError`, and a pair the engine refuses on principle (`% TSP` to
`g/L`) is `UnitError` carrying the recorded reason. Nothing here invents a
conversion factor.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA = Path(__file__).parent / "schema"
UNITS = SCHEMA / "units.json"
FIELDS = SCHEMA / "fields.yaml"


class UnitError(ValueError):
    """A conversion the engine will not do.

    `reason` is the recorded explanation when the pair is one of the refusals
    the browser also explains (OF-COR-001 §17 Rule 2), and None when the
    refusal is plain dimensional analysis.
    """

    def __init__(self, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason


# ── the tables ─────────────────────────────────────────────────────────


@lru_cache(maxsize=4)
def tables(path: str | None = None) -> dict[str, Any]:
    """The unit tables and the record fields.

    With no path, the schema files this package ships. A path names a JSON
    file holding `units` and `ontology` (a list of fields) in one, which is
    how a test hands the engine a table of its own.
    """
    if path:
        raw = json.loads(Path(path).read_text())
        if "units" not in raw or "ontology" not in raw:
            raise ValueError(f"{path} carries no `units` or `ontology` key")
        units, fields = raw["units"], raw["ontology"]
    else:
        import yaml

        units = json.loads(UNITS.read_text(encoding="utf-8"))
        fields = yaml.safe_load(FIELDS.read_text(encoding="utf-8"))["fields"]
    return {
        "table": units["table"],
        "aliases": units["aliases"],
        "si": units["si"],
        "refusals": units["refusals"],
        "ontology": {d["id"]: d for d in fields},
    }


# ── normalisation ──────────────────────────────────────────────────────

# The same replacements, in the same order, as `strip` in normalizeUnit().
# Middots become the space the table keys use; the minus sign papers print
# (U+2212) and the en dash become ASCII '-'; unicode superscripts become
# their ASCII spelling; runs of whitespace collapse; then lower-case.
_STRIP_STEPS = (
    ("·", " "),
    ("⋅", " "),
    ("\u2212", "-"),
    ("\u2013", "-"),
    ("⁻¹", "-1"),
    ("⁻²", "-2"),
    ("⁻³", "-3"),
    ("³", "3"),
    ("²", "2"),
)
_WS = re.compile(r"\s+")

# Grams per gram with each gram labelled by what it weighs: g EtOH/g glucose,
# gx/g, gDW gglucose⁻¹, g biomass [g glucose]⁻¹. The browser's
# LABELLED_MASS_RATIO in src/engine/units.ts, pattern for pattern; read
# against the stripped spelling, after every key has missed.
LABELLED_MASS_RATIO = (
    re.compile(r"^g(?:\s*[a-z]+)?\s*/\s*g(?:\s*[a-z]+)?$"),
    re.compile(r"^g(?:\s*[a-z]+)?(?:\s*\[\s*|\s+)g(?:\s*[a-z]+)?\s*\]?\s*-1$"),
)


def _strip(s: str) -> str:
    for a, b in _STRIP_STEPS:
        s = s.replace(a, b)
    return _WS.sub(" ", s).lower()


def normalize(raw: str) -> str | None:
    """The table key for a unit as somebody wrote it, or None.

    Five attempts, in the browser's order: the exact key; the alias as typed;
    the alias lower-cased; a superscript-blind, middot-blind, case-blind
    comparison against every key; and last, grams per gram with each gram
    labelled (LABELLED_MASS_RATIO). The order matters — 'mm' is a
    key (millimetres) and is found first, while 'mM' misses the key, misses
    the alias as typed, and reaches millimolar through the lower-cased alias.
    """
    t = raw.strip()
    table = tables()["table"]
    aliases = tables()["aliases"]
    if t in table:
        return t
    lower = t.lower()
    if aliases.get(t):
        return aliases[t]
    if aliases.get(lower):
        return aliases[lower]
    target = _strip(t)
    for key in table:
        if _strip(key) == target:
            return key
    if any(p.match(target.strip()) for p in LABELLED_MASS_RATIO):
        return "g g⁻¹"
    return None


def family(unit: str) -> str | None:
    n = normalize(unit)
    return None if n is None else tables()["table"][n]["family"]


def same_family(a: str, b: str) -> bool:
    fa = family(a)
    fb = family(b)
    return fa is not None and fa == fb


# ── conversion ─────────────────────────────────────────────────────────


def explain_refusal(from_unit: str, to_unit: str) -> str | None:
    """The recorded reason a conversion is refused, or None.

    None also when the units are unknown or in the same family — the browser
    returns null for both, and a reason for a conversion that would succeed
    would be a lie.
    """
    table = tables()["table"]
    f = table.get(normalize(from_unit) or "")
    t = table.get(normalize(to_unit) or "")
    if not f or not t or f["family"] == t["family"]:
        return None
    for r in tables()["refusals"]:
        if (r["a"] == f["family"] and r["b"] == t["family"]) or (
            r["b"] == f["family"] and r["a"] == t["family"]
        ):
            return r["because"]
    return None


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between two units of one family. Raises `UnitError` otherwise.

    `value * factor + offset` to the family base, then `(base - offset) /
    factor` out of it — the browser's expression, in the browser's order.
    """
    nf = normalize(from_unit)
    nt = normalize(to_unit)
    if nf is None:
        raise UnitError(f"Unknown unit: {from_unit}")
    if nt is None:
        raise UnitError(f"Unknown unit: {to_unit}")
    table = tables()["table"]
    uf = table[nf]
    ut = table[nt]
    if uf["family"] != ut["family"]:
        raise UnitError(
            f"Incompatible units: {from_unit} ({uf['family']}) vs {to_unit} ({ut['family']})",
            reason=explain_refusal(from_unit, to_unit),
        )
    base = value * uf["factor"] + uf.get("offset", 0)
    return (base - ut.get("offset", 0)) / ut["factor"]


def to_si(value: float, unit: str) -> tuple[float, str]:
    """The family's designated display twin. An unknown unit passes through."""
    n = normalize(unit)
    if n is None:
        return value, unit
    si = tables()["si"][tables()["table"][n]["family"]]
    return convert(value, n, si), si


def quantity_equals(
    a: tuple[float, str], b: tuple[float, str], tolerance_pct: float = 2
) -> bool:
    """Two quantities agree within a relative tolerance, after conversion.

    False across families; false when the conversion fails; zero against zero
    is an absolute test because a relative one would divide by nothing.
    """
    av_raw, au = a
    bv, bu = b
    if not same_family(au, bu):
        return False
    try:
        av = convert(av_raw, au, bu)
    except UnitError:
        return False
    if bv == 0:
        return abs(av) < 1e-12
    return abs(av - bv) / abs(bv) <= tolerance_pct / 100


# ── the ontology, for anchoring (§2.4 rules 4 and 5) ───────────────────


def field(field_id: str) -> dict[str, Any] | None:
    return tables()["ontology"].get(field_id)


def to_canonical(value: float, unit: str, field_id: str) -> float:
    """A value in the field's canonical unit, or `UnitError` saying why not.

    This is rule 4 of §2.4 as a function: the unit must normalise, and it must
    normalise into the family the field is denominated in. A `% TSP` offered
    for a titre field fails here with the recorded reason attached, which is
    what the rejection count will report.
    """
    f = field(field_id)
    if f is None:
        raise UnitError(f"Unknown field: {field_id}")
    if f["categorical"]:
        raise UnitError(f"{field_id} is categorical; it has no unit to convert to")
    return convert(value, unit, f["canonicalUnit"])
