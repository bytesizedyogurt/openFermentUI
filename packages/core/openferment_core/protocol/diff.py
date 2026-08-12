"""Structural diff of two protocol versions (OF-DES-001 §8.11).

A Ledger concern: what changed between two versions of a protocol has to be
computed server-side, from the canonical models, so that the answer a reviewer
sees is the answer the record carries.

This is the canonical implementation. `src/engine/diff.ts` is the mirror, and
`fixtures/diff.json` is the parity gate: one real pair (PR-TAP-01 1.0 → 1.1 —
the only protocol in the corpus with a second version) plus three synthetic
pairs that cover the step-`added` and step-`removed` branches the real corpus
never reaches. `tests/test_protocol.py` replays all four.

Two things in the TypeScript are load-bearing and easy to lose in a port; both
are called out where they happen:

* the `multiCheck` comparison goes through `JSON.stringify`, which a naive
  `json.dumps` does NOT reproduce, and
* the output is in neither version's order.
"""

from __future__ import annotations

from enum import StrEnum

from ..schema._base import OFModel
from ..schema.protocol import Material, ProtocolVersion, Step

__all__ = [
    "DiffKind",
    "MaterialDiff",
    "StepDiff",
    "VersionDiff",
    "diff_versions",
]


class DiffKind(StrEnum):
    """The four states an entry of a version diff can be in.

    A string union in the TypeScript (`'unchanged' | 'modified' | 'added' |
    'removed'`), declared in that order and reproduced in it, since it is the
    order a UI legend reads in.
    """

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


class StepDiff(OFModel):
    """One step's fate between two versions.

    `a` is the old step and `b` the new one. Both are optional and exactly which
    are present is decided by `kind`: `added` carries only `b`, `removed` only
    `a`, and `unchanged`/`modified` carry both. The TypeScript expresses this as
    one interface with two optional members rather than a discriminated union;
    it is ported the same way so that a serialised diff has the same shape on
    both sides of the wire.
    """

    kind: DiffKind
    a: Step | None = None
    b: Step | None = None


class MaterialDiff(OFModel):
    """One material's fate between two versions, keyed by NAME.

    Materials have no id in the schema, so the name is the identity. Renaming a
    material therefore reads as one `removed` and one `added` rather than a
    `modified`, which is the honest answer given the data available.
    """

    kind: DiffKind
    name: str
    a: Material | None = None
    b: Material | None = None


class VersionDiff(OFModel):
    """The whole comparison: steps, materials, and the newer version's changelog."""

    steps: list[StepDiff]
    materials: list[MaterialDiff]
    changelog: str | None = None


def _steps_differ(prev: Step, s: Step) -> bool:
    """Do these two same-id steps count as modified?

    ONLY `text`, `timer_sec` and `multi_check` are compared. A step whose `note`,
    `refs` or `timer_label` changed reads as `unchanged`, and the fixture pins
    that: PR-TAP-01 step p3 is `unchanged` between 1.0 and 1.1 while its `note`
    is rewritten and its `refs` move from M1 to M2. The diff is of the
    PROCEDURE, not of its annotation.
    """
    return (
        prev.text != s.text
        # JS `!==` on two `undefined`s is false, and Python `!=` on two `None`s
        # is likewise False — the "both absent" case is equal in both. The two
        # also agree on the awkward numeric pairs: `0 !== -0` is false in JS and
        # `0.0 != -0.0` is False here, while NaN is unequal to itself in both.
        or prev.timer_sec != s.timer_sec
        # THE COMPARISON THAT DECIDES EVERY STEP. The TypeScript is
        #     JSON.stringify(prev.multiCheck ?? null) !== JSON.stringify(s.multiCheck ?? null)
        # and the obvious translation — run both sides through `json.dumps` and
        # compare the strings — is not wrong here, but it is wrong-in-waiting,
        # and it is worth writing down why rather than leaving the next reader
        # to re-derive it.
        #
        # `json.dumps` differs from `JSON.stringify` in ways that would matter
        # if the two strings ever met: Python's default separators are `', '`
        # and `': '` where JSON.stringify uses `,` and `:`, `json.dumps` emits
        # `NaN`/`Infinity` where JSON.stringify emits `null`, and neither sorts
        # object keys, so two dicts built in different orders serialise
        # differently. None of that bites TODAY because both sides go through
        # the SAME serialiser and the field is a flat `list[str] | None`, where
        # the string comparison and the value comparison agree exactly — a
        # mutation replacing the line below with symmetric `json.dumps` calls
        # still passes the fixture, so the fixture does not pin this choice.
        # It is a design decision, not a captured one.
        #
        # What `JSON.stringify` is DOING on this type is a structural comparison
        # of a `string[] | null`, and Python's `!=` performs exactly that, with
        # no serialiser between the values and the answer:
        #
        #   * `?? null` collapses undefined and null to one thing, which is what
        #     `None` already is here;
        #   * two lists with equal elements in the same order compare equal, and
        #     order matters — `["a", "b"] != ["b", "a"]`, as `'["a","b"]'` and
        #     `'["b","a"]'` differ;
        #   * `[] != None` here, as `"[]" !== "null"` there — an empty checklist
        #     is not an absent one.
        #
        # The one pair where the two rules could part company is `[True]` vs
        # `[1]`: equal to Python, `"[true]"` vs `"[1]"` to JSON.stringify. The
        # field is `list[str] | None` and Pydantic validates it as such, so no
        # bool reaches this comparison — which is the other reason not to
        # serialise, since a serialiser would be papering over a type error
        # rather than reporting one.
        #
        # `tests/test_protocol.py::test_steps_differ_on` pins all of this. It
        # has to: every `modified` step in `fixtures/diff.json` differs on
        # `text` alone, so neither this clause nor the `timer_sec` one above is
        # exercised by a single captured case.
        or prev.multi_check != s.multi_check
    )


def diff_versions(a: ProtocolVersion, b: ProtocolVersion) -> VersionDiff:
    """Compare two versions of a protocol. `a` is the older, `b` the newer."""
    steps: list[StepDiff] = []
    # `new Map(xs.map(x => [k, x]))` keeps the LAST entry for a repeated key,
    # and so does a dict comprehension. Duplicate step ids collapse the same way
    # on both sides.
    a_steps = {s.id: s for s in a.steps}
    b_steps = {s.id: s for s in b.steps}
    # Walk b's order (the newer version), marking removed a-steps in place.
    for s in b.steps:
        prev = a_steps.get(s.id)
        if prev is None:
            steps.append(StepDiff(kind=DiffKind.ADDED, b=s))
        elif _steps_differ(prev, s):
            steps.append(StepDiff(kind=DiffKind.MODIFIED, a=prev, b=s))
        else:
            steps.append(StepDiff(kind=DiffKind.UNCHANGED, a=prev, b=s))
    # ORDER TRAP: despite the comment above, removed steps are NOT marked in
    # place. They are appended here, after the whole of b's order, so the result
    # is in neither a's order nor b's: a step deleted from the top of the
    # protocol comes out last. `fixtures/diff.json` pins it — the synthetic pair
    # yields [modified p2, added synthetic-inserted-step, unchanged p3, removed
    # p1] — and a port that interleaved removals at their old positions, which
    # is what a reviewer would probably rather see, would fail the gate.
    for s in a.steps:
        if s.id not in b_steps:
            steps.append(StepDiff(kind=DiffKind.REMOVED, a=s))

    materials: list[MaterialDiff] = []
    a_mats = {m.name: m for m in a.materials}
    b_mats = {m.name: m for m in b.materials}
    for m in b.materials:
        prev_m = a_mats.get(m.name)
        if prev_m is None:
            materials.append(MaterialDiff(kind=DiffKind.ADDED, name=m.name, b=m))
        # Only amount, unit and scaling. `precision`, `stock` and
        # `source_record_id` are not compared, so a material whose stock
        # concentration was corrected — which changes every stock volume the
        # protocol prints — reads as `unchanged`. Captured behaviour, ported as
        # written.
        elif prev_m.amount != m.amount or prev_m.unit != m.unit or prev_m.scaling != m.scaling:
            materials.append(MaterialDiff(kind=DiffKind.MODIFIED, name=m.name, a=prev_m, b=m))
        else:
            materials.append(MaterialDiff(kind=DiffKind.UNCHANGED, name=m.name, a=prev_m, b=m))
    # Same appended-after-the-loop ordering as the steps, and the real fixture
    # pair is what pins it: PR-TAP-01 swaps its trace element solution, and the
    # diff reads [... added "Revised trace element solution (Kropat 2011)" in
    # position 7 ...] followed by removed "Hutner trace element solution" last.
    for m in a.materials:
        if m.name not in b_mats:
            materials.append(MaterialDiff(kind=DiffKind.REMOVED, name=m.name, a=m))

    # b's changelog, not a's, and not a diff of the two: the changelog describes
    # the change INTO b, so it is already the answer to "what changed".
    return VersionDiff(steps=steps, materials=materials, changelog=b.changelog)
