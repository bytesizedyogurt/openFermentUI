"""Protocol scaling math (OF-DES-001 §8.11).

Quantities scale by declared class, rounded to each material's precision spec so
recipes stay pipettable.

This is the canonical implementation. `src/engine/scale.ts` is the mirror, and
`fixtures/scale.json` is the parity gate between them: 392 `scaleMaterial`
cases, 40 `scaleMaterials` cases and 8 `inoculumVolume` cases, replayed by
`tests/test_protocol.py`.

Three functions here — `render_step_text`, `batch_label`, `materials_checklist`
— are NOT in that fixture. `scripts/capture-fixtures.ts` captures only the three
listed above, so the strings these three produce are pinned by literals in the
test file instead, captured from the TypeScript rather than transcribed by hand.
Extending the capture script is the right home for them and is outside this
module's remit; until that happens the literals are the gate.

Because the fixture was captured from V8, this port reproduces JavaScript's
semantics rather than Python's wherever the two disagree, as `units.py` does,
and the places where that matters are marked `JS:` below. There are fewer of
them here than in `units.py`, for a reason worth stating: the arithmetic needs
no special handling at all — IEEE-754 doubles multiply the same in both
languages — because every rounding decision in this module is delegated to
`units.round_to_precision`, which already carries the `Math.round` and
`toFixed` semantics. It is imported, never reimplemented. What is left is the
string building, which is where the remaining `JS:` notes are.

One deliberate divergence, flagged at the point where it bites: a stock
concentration of zero raises `ZeroDivisionError` here where the TypeScript emits
an infinite stock volume. See `scale_material`.
"""

from __future__ import annotations

import re
from typing import Any, Final

from ..schema._base import OFModel
from ..schema.protocol import Material, ProtocolVersion, ScalingClass, Step
from ..units import fmt, round_to_precision

__all__ = [
    "ScaledMaterial",
    "StockVolume",
    "batch_label",
    "inoculum_volume",
    "materials_checklist",
    "render_step_text",
    "scale_material",
    "scale_materials",
]

#: Precision increment the stock volume is snapped to, in the stock's own unit.
#: Hard-coded in the TypeScript rather than taken from the material's own
#: `precision`, and deliberately so: `precision` describes weighing out the neat
#: material (0.001 g for a trace salt), whereas a stock volume is pipetted, and
#: 0.1 is the finest graduation anyone should be asked to hit by eye.
_STOCK_VOLUME_PRECISION: Final = 0.1

#: Precision increment for the seed volume `inoculum_volume` returns, in mL.
#: The same 0.1 as above and for the same pipetting reason, but a separate
#: constant because it is a separate decision — the TypeScript hard-codes the
#: two independently, and moving one should not move the other.
_SEED_VOLUME_PRECISION_ML: Final = 0.1


class StockVolume(OFModel):
    """Volume of stock solution to dispense, and the unit it is measured in.

    Inline in the TypeScript (`stockVolume?: { value: number; unit: string }`);
    named here because Pydantic has no anonymous model.
    """

    value: float
    unit: str


class ScaledMaterial(Material):
    """A `Material` with its scaled amount attached.

    `ScaledMaterial extends Material` in the TypeScript and the implementation
    spreads the source material into the result, so every `Material` field is
    carried through unchanged. Subclassing reproduces that, including the field
    ORDER a serialisation will emit: the inherited fields first, then the three
    added here — which is the order `fixtures/scale.json` was written in.
    """

    scaled_amount: float
    scales: bool
    stock_volume: StockVolume | None = None


def scale_material(m: Material, scale: float) -> ScaledMaterial:
    """Scale one material, rounded to its own precision increment."""
    # JS: `m.scaling !== 'fixed'` on a string union; `ScalingClass` is a
    # StrEnum, so the comparison is spelled against the member rather than the
    # literal and means the same thing.
    #
    # Any class other than `fixed` scales, and they all scale by the SAME
    # multiplier: `per_unit_biomass` is not treated differently here or anywhere
    # else in the TypeScript, so a lysis buffer declared per unit biomass is
    # multiplied by the BATCH VOLUME factor, which is only the same number while
    # cell density is held constant. PR-DISRUPT-01 is the one version that uses
    # the class, and 40 of the fixture's cases pin exactly this behaviour.
    # Ported as written — the class is a declaration the engine records and does
    # not yet act on.
    scales = m.scaling != ScalingClass.FIXED
    raw = m.amount * scale if scales else m.amount
    # `precision` is a rounding INCREMENT, not a count of decimal places: 0.05
    # means "to the nearest 0.05 g". `round_to_precision` is imported from
    # `..units`, which is where this repo's single implementation of it lives —
    # a second one here is precisely the failure this migration exists to
    # prevent.
    scaled_amount = round_to_precision(raw, m.precision)
    data: dict[str, Any] = {**m.model_dump(), "scaled_amount": scaled_amount, "scales": scales}
    if m.stock is not None:
        # amount (mass or volume of pure component) via stock concentration.
        # stock.conc in unit-per-mL of stock (e.g. g/mL → mL of stock needed).
        #
        # Note `raw`, not `scaled_amount`: the stock volume is computed from the
        # UNROUNDED amount and then rounded once, so it is not the volume that
        # delivers the rounded figure on the checklist line beside it. The
        # TypeScript does this and the fixture pins the results, so it is ported
        # as written.
        #
        # DELIBERATE DIVERGENCE, the only one in this module. A `conc` of zero
        # raises ZeroDivisionError here; JS yields Infinity, which survives
        # `round_to_precision` and reaches the bench as `stockVolume.value:
        # Infinity` — rendered by `fmt` as "—" and serialised by JSON.stringify
        # as `null`. Nothing in the corpus carries a zero concentration and the
        # fixture pins no such case, so this contradicts nothing that was
        # captured; reproducing it would mean printing an infinite volume onto a
        # protocol sheet, which is the fabrication invariant 2 forbids.
        vol = raw / m.stock.conc
        data["stock_volume"] = {
            "value": round_to_precision(vol, _STOCK_VOLUME_PRECISION),
            "unit": m.stock.unit,
        }
    return ScaledMaterial.model_validate(data)


def scale_materials(version: ProtocolVersion, scale: float) -> list[ScaledMaterial]:
    """Every material in a version, scaled, in the version's own order."""
    return [scale_material(m, scale) for m in version.materials]


# The JS original is
#   /\{\{(qty|stock):([^}]+)\}\}/g
# and translates character for character. The three things worth stating:
#
# JS: the `/g` flag. JavaScript needs it to replace every occurrence; Python's
#     `re.sub` replaces every occurrence unless told otherwise, so the ABSENCE
#     of a `count=` argument here is what `/g` is doing there. This is the
#     mirror image of the trap in `units.fmt`, where a JS regex WITHOUT `/g`
#     had to be given an explicit `count=1`.
#
# JS: `[^}]+` is a negated class, so it spans newlines in both languages —
#     unlike `.`, which excludes a different set of characters in each and which
#     `units.py` had to write out longhand. It also requires at least one
#     character, which is why `{{qty:}}` is left alone rather than looked up as
#     the empty material name.
#
# JS: the callback. `String.replace` expands `$&`/`$1` patterns only when the
#     replacement is a STRING, and Python's `re.sub` expands `\1` patterns only
#     when the replacement is a STRING. Both leave the return value of a
#     replacement FUNCTION verbatim, so the two agree today — and both would
#     start corrupting material names, which are free text, the moment either
#     side is rewritten as a string replacement.
_PLACEHOLDER: Final = re.compile(r"\{\{(qty|stock):([^}]+)\}\}")


def render_step_text(step: Step, version: ProtocolVersion, scale: float) -> str:
    """Render a step's text at scale.

    Replaces `{{qty:materialName}}` with the scaled amount + unit, and
    `{{stock:materialName}}` with the stock volume.
    """

    def replace(match: re.Match[str]) -> str:
        # JS: the callback is destructured `(_, kind, name)` — the whole match
        # first, then the capture groups — so these are groups 1 and 2 of the
        # Match, not 0 and 1.
        kind, name = match.group(1), match.group(2)
        # JS: `Array.prototype.find` returns the FIRST match, and `next(...)`
        # over a generator does the same. Two materials with the
        # same name resolve to the earlier one; nothing in the corpus has
        # duplicate names within a version, but nothing enforces it either.
        mat = next((m for m in version.materials if m.name == name), None)
        if mat is None:
            # User-facing copy, pinned character for character — including the
            # mathematical angle brackets U+27E8 and U+27E9, which are NOT the
            # ASCII `<` `>` and not the CJK 〈 〉.
            return f"⟨unknown material: {name}⟩"
        scaled = scale_material(mat, scale)
        if kind == "stock" and scaled.stock_volume is not None:
            return f"{fmt(scaled.stock_volume.value)} {scaled.stock_volume.unit}"
        # Note the fallthrough: a `{{stock:…}}` placeholder naming a material
        # with no stock renders the neat AMOUNT instead, silently. JS: the TS
        # condition is `kind === 'stock' && scaled.stockVolume`, a TRUTHINESS
        # test on the optional object; `is not None` is the same test here
        # because the only falsy value the field can hold is its absence. It is a real trap for a protocol author — the sheet then says
        # "add 4.84 g" where it meant to say "add 50 mL of stock" — but it is
        # the captured behaviour, so it is ported rather than fixed.
        return f"{fmt(scaled.scaled_amount)} {mat.unit}"

    return _PLACEHOLDER.sub(replace, step.text)


def batch_label(version: ProtocolVersion, scale: float) -> str:
    """Total batch label at scale, e.g. "5 L batch"."""
    # Not rounded to any precision: the batch size is a headline, not something
    # anybody weighs out, so it goes through `fmt`'s display rounding only.
    v = version.base_batch.value * scale
    return f"{fmt(v)} {version.base_batch.unit} {version.base_batch.label}"


def materials_checklist(version: ProtocolVersion, scale: float, title: str) -> str:
    """Plain-text checklist of materials at scale (Copy as checklist).

    The five header lines are the export's honesty preamble: they say that the
    protocol content is real, that the amounts on the sheet were computed rather
    than measured at this scale, and that the cited figures are curator
    transcriptions. They are product copy and are reproduced byte for byte, em
    dashes included.
    """
    lines = [
        f"# {title} — materials at {batch_label(version, scale)}",
        "# openFerment export — corpus OF-COR-001 v1.0",
        "# Protocol content is real: drawn from the catalogued literature and standard bench practice.",
        "# Amounts here are computed by scaling the base batch, not measured at this scale.",
        "# Cited figures are curator transcriptions, not yet checked against the source PDFs.",
        "",
    ]
    for m in scale_materials(version, scale):
        fixed_note = "" if m.scales else " (fixed — does not scale)"
        stock_note = ""
        # The TypeScript tests `m.stockVolume` alone and then reaches for
        # `m.stock!`; the second test here is that non-null assertion written
        # out, and it is sound for the same reason — `scale_material` sets the
        # two together or neither.
        if m.stock_volume is not None and m.stock is not None:
            # The TS writes the stock's denominator as
            #   `m.stock!.unit === 'mL' ? 'mL' : m.stock!.unit`
            # whose two branches are the same string. It is an identity, so it
            # is collapsed here rather than transcribed; the µL stocks in the
            # corpus prove the "else" arm is reached and that it changes
            # nothing.
            stock_note = (
                f" — use {fmt(m.stock_volume.value)} {m.stock_volume.unit} of stock"
                f" ({fmt(m.stock.conc)} {m.unit}/{m.stock.unit})"
            )
        lines.append(f"[ ] {m.name}: {fmt(m.scaled_amount)} {m.unit}{fixed_note}{stock_note}")
    # JS: `Array.prototype.join('\n')` puts no separator after the last
    # element, and neither does `str.join`, so the checklist ends without a
    # trailing newline in both.
    return "\n".join(lines)


def inoculum_volume(
    target_od: float,
    culture_volume_ml: float,
    seed_od: float,
) -> float | None:
    """Inoculation-density helper: volume of seed at measured OD to hit target OD."""
    if seed_od <= target_od or seed_od <= 0:
        return None
    # The TypeScript's own note, ported verbatim because it records what the
    # author believed the formula was:
    #
    #   V_seed = V_final * targetOD / (seedOD - targetOD) approximated for small V:
    #   exact: V_seed * seedOD = targetOD * (V_final); assume V_final includes seed.
    #
    # The code below is the SECOND of those two, not the first, and the guard
    # above belongs to the first — `seed_od <= target_od` is what stops the
    # `(seedOD - targetOD)` denominator going to zero or negative, and the
    # implemented formula has no such denominator. Ported as written, guard
    # included: the guard is conservative rather than wrong (a seed no denser
    # than the target cannot inoculate to it), and the eight fixture cases pin
    # both the formula and the two refusals.
    v = (target_od * culture_volume_ml) / seed_od
    return round_to_precision(v, _SEED_VOLUME_PRECISION_ML)
