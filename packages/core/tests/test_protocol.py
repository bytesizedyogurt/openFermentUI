"""Fixture replay for the protocol engines.

`fixtures/scale.json` and `fixtures/diff.json` were captured from
`src/engine/scale.ts` and `src/engine/diff.ts` by `scripts/capture-fixtures.ts`.
Every case in them is a behaviour the TypeScript exhibits today, and this file
replays all 444 of them against the Python port: 392 `scaleMaterial`, 40
`scaleMaterials`, 8 `inoculumVolume`, 1 real `diffVersions` pair and 3 synthetic
ones. It is the parity gate, so it is deliberately dumb — no case is skipped,
reinterpreted, or given a looser tolerance than 1e-12. Every case passes at that
tolerance; none needed widening.

INPUTS are not read back out of the outputs. `scale.json` echoes each source
material inside its result (`ScaledMaterial` spreads `Material`), so a lazy
replay could feed the expectation to itself and pass without computing
anything. Instead the inputs are re-parsed from `fixtures/schema-instances.json`
— the same `PROTOCOLS` the capture script iterated — walked in the capture
script's own nested order, and zipped positionally against the fixture rows with
the identifying keys asserted at every step. A drift in either file breaks
collection rather than passing quietly.

TWO GAPS IN THE FIXTURE ARE FILLED HERE, and both are places where the capture
is thinner than it looks.

The first is inside `diff_versions`: every `modified` step in `diff.json`
differs on `text` alone, so the `timer_sec` and `multi_check` clauses of the
comparison are pinned by nothing — deleting either leaves all 444 captured cases
green. `test_steps_differ_on` covers them.

The second is that three functions are not in the fixture at all.
`capture-fixtures.ts` records `scaleMaterial`, `scaleMaterials` and
`inoculumVolume` and nothing else, so `render_step_text`, `batch_label` and
`materials_checklist` — every user-visible string the scaling engine produces —
have no captured gate either.

Both sets of expectations were CAPTURED from the TypeScript rather than
transcribed from reading it: `src/engine/scale.ts` and `src/engine/diff.ts` were
imported under `tsx` and called over the same corpus and the same four scales
the fixture sweep uses. The synthetic step texts and single-step versions
exercise the branches the corpus never reaches. The right home for all of it is
`capture-fixtures.ts`, which is outside this package; until it gets there, these
literals are the gate.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Final

import pytest
from pydantic import BaseModel

from openferment_core.protocol import (
    StepDiff,
    batch_label,
    diff_versions,
    inoculum_volume,
    materials_checklist,
    render_step_text,
    scale_material,
    scale_materials,
)
from openferment_core.schema.protocol import Material, Protocol, ProtocolVersion, Step

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
_SCALE: dict[str, Any] = json.loads((FIXTURES / "scale.json").read_text("utf-8"))
_DIFF: dict[str, Any] = json.loads((FIXTURES / "diff.json").read_text("utf-8"))
_INSTANCES: dict[str, Any] = json.loads((FIXTURES / "schema-instances.json").read_text("utf-8"))

REL_TOL = 1e-12

#: The scales the capture script swept, read from the fixture rather than
#: restated, so the two cannot drift apart.
SCALES: Final[list[float]] = [float(s) for s in _SCALE["meta"]["scales"]]

#: The corpus the capture script iterated, re-parsed through the canonical models.
PROTOCOLS: Final[list[Protocol]] = [Protocol.model_validate(p) for p in _INSTANCES["protocols"]]


def _dump(model: BaseModel) -> Any:
    """Serialise a result the way `JSON.stringify` serialised the TypeScript one.

    `by_alias` because the fixture is camelCase; `exclude_none` because
    JSON.stringify drops `undefined` members rather than emitting null, and every
    optional in these shapes is `undefined`-when-absent on the TypeScript side;
    `mode="json"` so a `StrEnum` comes out as its string.
    """
    return model.model_dump(by_alias=True, exclude_none=True, mode="json")


def _assert_matches(actual: Any, expected: Any, case: str, path: str = "out") -> None:
    """Compare a dumped result against a fixture value, numbers by `isclose`.

    Structure is compared exactly — a key the port emits and the fixture does
    not is a failure, in both directions — and only leaf numbers are given the
    1e-12 tolerance. Booleans are checked before numbers because `bool` is a
    subclass of `int` in Python and `math.isclose(True, 1)` is true, which would
    let `scales: true` match `scales: 1`.
    """
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{case} {path}: {actual!r} is not an object"
        assert sorted(actual) == sorted(expected), (
            f"{case} {path}: keys {sorted(actual)} != {sorted(expected)}"
        )
        for key in expected:
            _assert_matches(actual[key], expected[key], case, f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{case} {path}: {actual!r} is not an array"
        assert len(actual) == len(expected), (
            f"{case} {path}: length {len(actual)} != {len(expected)}"
        )
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _assert_matches(a, e, case, f"{path}[{i}]")
    elif isinstance(expected, bool) or isinstance(actual, bool):
        assert actual is expected, f"{case} {path}: {actual!r} != {expected!r}"
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        assert math.isclose(actual, expected, rel_tol=REL_TOL), (
            f"{case} {path}: {actual!r} != {expected!r}"
        )
    else:
        assert actual == expected, f"{case} {path}: {actual!r} != {expected!r}"


# ══ scaleMaterial ══════════════════════════════════════════════════════


def _scale_material_cases() -> list[tuple[str, Material, float, dict[str, Any]]]:
    """Re-walk `PROTOCOLS × versions × materials × SCALES`, the capture's own order."""
    rows: list[dict[str, Any]] = _SCALE["scaleMaterial"]
    cases: list[tuple[str, Material, float, dict[str, Any]]] = []
    i = 0
    for p in PROTOCOLS:
        for v in p.versions:
            for m in v.materials:
                for scale in SCALES:
                    row = rows[i]
                    i += 1
                    ident = f"{p.id}/{v.version}/{m.name}@{scale}"
                    assert (row["protocol"], row["version"], row["material"]) == (
                        p.id,
                        v.version,
                        m.name,
                    ), f"fixture row {i - 1} is not {ident}"
                    assert row["scale"] == scale, f"fixture row {i - 1} is not {ident}"
                    cases.append((ident, m, scale, row["out"]))
    assert i == len(rows), f"walked {i} materials, fixture has {len(rows)} rows"
    return cases


_SCALE_MATERIAL = _scale_material_cases()


@pytest.mark.parametrize(
    ("ident", "material", "scale", "expected"),
    _SCALE_MATERIAL,
    ids=[c[0] for c in _SCALE_MATERIAL],
)
def test_scale_material(
    ident: str, material: Material, scale: float, expected: dict[str, Any]
) -> None:
    _assert_matches(_dump(scale_material(material, scale)), expected, ident)


# ══ scaleMaterials ═════════════════════════════════════════════════════


def _scale_materials_cases() -> list[tuple[str, ProtocolVersion, float, list[Any]]]:
    rows: list[dict[str, Any]] = _SCALE["scaleMaterials"]
    cases: list[tuple[str, ProtocolVersion, float, list[Any]]] = []
    i = 0
    for p in PROTOCOLS:
        for v in p.versions:
            for scale in SCALES:
                row = rows[i]
                i += 1
                ident = f"{p.id}/{v.version}@{scale}"
                assert (row["protocol"], row["version"], row["scale"]) == (
                    p.id,
                    v.version,
                    scale,
                ), f"fixture row {i - 1} is not {ident}"
                cases.append((ident, v, scale, row["out"]))
    assert i == len(rows), f"walked {i} versions, fixture has {len(rows)} rows"
    return cases


_SCALE_MATERIALS = _scale_materials_cases()


@pytest.mark.parametrize(
    ("ident", "version", "scale", "expected"),
    _SCALE_MATERIALS,
    ids=[c[0] for c in _SCALE_MATERIALS],
)
def test_scale_materials(
    ident: str, version: ProtocolVersion, scale: float, expected: list[Any]
) -> None:
    _assert_matches([_dump(m) for m in scale_materials(version, scale)], expected, ident)


def test_scale_materials_keeps_the_versions_own_order() -> None:
    """`map` preserves order; a dict-keyed rewrite would not, and nothing else would notice."""
    version = PROTOCOLS[0].versions[0]
    assert [m.name for m in scale_materials(version, 2)] == [m.name for m in version.materials]


# ══ inoculumVolume ═════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "case",
    _SCALE["inoculumVolume"],
    ids=[
        f"target={c['targetOD']},V={c['cultureVolumeML']},seed={c['seedOD']}"
        for c in _SCALE["inoculumVolume"]
    ],
)
def test_inoculum_volume(case: dict[str, Any]) -> None:
    got = inoculum_volume(case["targetOD"], case["cultureVolumeML"], case["seedOD"])
    if case["out"] is None:
        # A refusal, not a zero: a seed no denser than the target cannot
        # inoculate to it, and the engine says so rather than guessing.
        assert got is None, case
        return
    assert got is not None, case
    assert math.isclose(got, case["out"], rel_tol=REL_TOL), case


# ══ diffVersions, the real pair ════════════════════════════════════════


def _diff_cases() -> list[tuple[str, ProtocolVersion, ProtocolVersion, dict[str, Any]]]:
    """Consecutive version pairs, per protocol — `p.versions.slice(1)` in the capture."""
    rows: list[dict[str, Any]] = _DIFF["diffVersions"]
    cases: list[tuple[str, ProtocolVersion, ProtocolVersion, dict[str, Any]]] = []
    i = 0
    for p in PROTOCOLS:
        for prev, cur in zip(p.versions, p.versions[1:], strict=False):
            row = rows[i]
            i += 1
            ident = f"{p.id} {prev.version}->{cur.version}"
            assert (row["protocol"], row["from"], row["to"]) == (
                p.id,
                prev.version,
                cur.version,
            ), f"fixture row {i - 1} is not {ident}"
            cases.append((ident, prev, cur, row["out"]))
    assert i == len(rows), f"walked {i} pairs, fixture has {len(rows)} rows"
    return cases


_DIFF_REAL = _diff_cases()


@pytest.mark.parametrize(
    ("ident", "a", "b", "expected"), _DIFF_REAL, ids=[c[0] for c in _DIFF_REAL]
)
def test_diff_versions_real(
    ident: str, a: ProtocolVersion, b: ProtocolVersion, expected: dict[str, Any]
) -> None:
    _assert_matches(_dump(diff_versions(a, b)), expected, ident)


# ══ diffVersions, the synthetic pairs ══════════════════════════════════
#
# `syntheticInputs` carries the two versions but not which way round each case
# ran them; `capture-fixtures.ts` names the three calls, and this maps its
# labels back onto the inputs. An unrecognised label fails rather than silently
# skipping a case.

_SYN_FROM: Final = ProtocolVersion.model_validate(_DIFF["syntheticInputs"]["from"])
_SYN_TO: Final = ProtocolVersion.model_validate(_DIFF["syntheticInputs"]["to"])

_SYNTHETIC_DIRECTIONS: Final[dict[str, tuple[ProtocolVersion, ProtocolVersion]]] = {
    "added, removed, modified and reordered steps": (_SYN_FROM, _SYN_TO),
    "reverse direction": (_SYN_TO, _SYN_FROM),
    "a version against itself": (_SYN_FROM, _SYN_FROM),
}


@pytest.mark.parametrize(
    "case",
    _DIFF["diffVersionsSynthetic"],
    ids=[c["label"] for c in _DIFF["diffVersionsSynthetic"]],
)
def test_diff_versions_synthetic(case: dict[str, Any]) -> None:
    assert case["label"] in _SYNTHETIC_DIRECTIONS, f"unmapped synthetic case: {case['label']}"
    a, b = _SYNTHETIC_DIRECTIONS[case["label"]]
    _assert_matches(_dump(diff_versions(a, b)), case["out"], case["label"])


def test_diff_appends_removals_after_the_newer_versions_order() -> None:
    """The output is in neither version's order — pinned here as well as by the fixture.

    `p1` is dropped between `synthetic-a` and `synthetic-b`, and comes out LAST
    rather than first, because removals are appended after the walk of b. This
    is the single most reversible-looking line in `diff.ts` and the one a port
    is most likely to "tidy".
    """
    out = diff_versions(_SYN_FROM, _SYN_TO)

    def step_id(d: StepDiff) -> str:
        # `b` for an added step, `a` for a removed one; both carry the same id
        # where both are present. Every StepDiff has at least one of the two.
        s = d.b if d.b is not None else d.a
        assert s is not None, d
        return s.id

    assert [(d.kind.value, step_id(d)) for d in out.steps] == [
        ("modified", "p2"),
        ("added", "synthetic-inserted-step"),
        ("unchanged", "p3"),
        ("removed", "p1"),
    ]


def test_diff_ignores_note_and_refs() -> None:
    """A step whose annotation changed is `unchanged`; only the procedure is diffed.

    PR-TAP-01 step p3 rewrites its `note` and moves its `refs` from M1 to M2
    between 1.0 and 1.1, and the fixture calls it unchanged. Stated separately
    because it is a design decision rather than an accident, and a port that
    compared whole steps would fail this before it failed anything else.
    """
    a, b = PROTOCOLS[0].versions[0], PROTOCOLS[0].versions[1]
    p3 = next(d for d in diff_versions(a, b).steps if d.a is not None and d.a.id == "p3")
    assert p3.kind.value == "unchanged"
    assert p3.a is not None and p3.b is not None
    assert (p3.a.note, p3.a.refs) != (p3.b.note, p3.b.refs)


# ══ the step comparison the fixture never exercises ════════════════════
#
# Every `modified` step in `fixtures/diff.json` differs on `text` alone, so the
# `timer_sec` and `multi_check` clauses of the comparison are pinned by no
# captured case at all — dropping either one leaves the whole fixture green.
# These rows fill that hole. They were CAPTURED from `src/engine/diff.ts` under
# `tsx`, one synthetic single-step version against another, not transcribed from
# reading it; `a` and `b` are the two step objects as JSON.

_STEPS_DIFFER_ON: Final[list[tuple[str, str, str, str]]] = [
    (
        "multiCheck equal",
        '{"id": "s1", "text": "Same text.", "multiCheck": ["a", "b"]}',
        '{"id": "s1", "text": "Same text.", "multiCheck": ["a", "b"]}',
        "unchanged",
    ),
    (
        "multiCheck reordered",
        '{"id": "s1", "text": "Same text.", "multiCheck": ["a", "b"]}',
        '{"id": "s1", "text": "Same text.", "multiCheck": ["b", "a"]}',
        "modified",
    ),
    (
        "multiCheck extended",
        '{"id": "s1", "text": "Same text.", "multiCheck": ["a"]}',
        '{"id": "s1", "text": "Same text.", "multiCheck": ["a", "b"]}',
        "modified",
    ),
    (
        "multiCheck empty vs absent",
        '{"id": "s1", "text": "Same text.", "multiCheck": []}',
        '{"id": "s1", "text": "Same text."}',
        "modified",
    ),
    (
        "multiCheck absent vs absent",
        '{"id": "s1", "text": "Same text."}',
        '{"id": "s1", "text": "Same text."}',
        "unchanged",
    ),
    (
        "multiCheck empty vs empty",
        '{"id": "s1", "text": "Same text.", "multiCheck": []}',
        '{"id": "s1", "text": "Same text.", "multiCheck": []}',
        "unchanged",
    ),
    (
        "timerSec equal",
        '{"id": "s1", "text": "Same text.", "timerSec": 60}',
        '{"id": "s1", "text": "Same text.", "timerSec": 60}',
        "unchanged",
    ),
    (
        "timerSec changed",
        '{"id": "s1", "text": "Same text.", "timerSec": 60}',
        '{"id": "s1", "text": "Same text.", "timerSec": 90}',
        "modified",
    ),
    (
        "timerSec absent vs set",
        '{"id": "s1", "text": "Same text."}',
        '{"id": "s1", "text": "Same text.", "timerSec": 60}',
        "modified",
    ),
    (
        "timerSec set vs absent",
        '{"id": "s1", "text": "Same text.", "timerSec": 60}',
        '{"id": "s1", "text": "Same text."}',
        "modified",
    ),
    (
        "timerLabel changed",
        '{"id": "s1", "text": "Same text.", "timerSec": 60, "timerLabel": "Stir"}',
        '{"id": "s1", "text": "Same text.", "timerSec": 60, "timerLabel": "Mix"}',
        "unchanged",
    ),
    (
        "note changed",
        '{"id": "s1", "text": "Same text.", "note": "one"}',
        '{"id": "s1", "text": "Same text.", "note": "two"}',
        "unchanged",
    ),
    (
        "refs changed",
        '{"id": "s1", "text": "Same text.", "refs": ["M1"]}',
        '{"id": "s1", "text": "Same text.", "refs": ["M2"]}',
        "unchanged",
    ),
]


@pytest.mark.parametrize(
    ("label", "a_json", "b_json", "expected"),
    _STEPS_DIFFER_ON,
    ids=[c[0] for c in _STEPS_DIFFER_ON],
)
def test_steps_differ_on(label: str, a_json: str, b_json: str, expected: str) -> None:
    a = _SYN_FROM.model_copy(update={"steps": [Step.model_validate(json.loads(a_json))]})
    b = _SYN_FROM.model_copy(update={"steps": [Step.model_validate(json.loads(b_json))]})
    diff = diff_versions(a, b)
    assert [d.kind.value for d in diff.steps] == [expected], label


# ══ the three functions the fixture does not cover ═════════════════════
#
# Captured from `src/engine/scale.ts` under `tsx`, over the same corpus and the
# same four scales the fixture sweep uses. See the module docstring.


def _version(protocol_id: str, version: str) -> ProtocolVersion:
    p = next(p for p in PROTOCOLS if p.id == protocol_id)
    return next(v for v in p.versions if v.version == version)


def _title(protocol_id: str) -> str:
    return next(p for p in PROTOCOLS if p.id == protocol_id).title


_BATCH_LABEL: Final[dict[tuple[str, str, float], str]] = {
    ("PR-TAP-01", "1.0", 0.5): "0.5 L batch",
    ("PR-TAP-01", "1.0", 1.0): "1 L batch",
    ("PR-TAP-01", "1.0", 2.0): "2 L batch",
    ("PR-TAP-01", "1.0", 10.0): "10 L batch",
    ("PR-TRANS-01", "1.0", 2.0): "16 reactions electroporation set",
    ("PR-CIP-01", "1.0", 0.5): "0.5 vessel per cycle",
    ("PR-DISRUPT-01", "1.0", 10.0): "100 L culture",
    ("PR-SEED-01", "1.0", 0.5): "200 mL production seed",
}


@pytest.mark.parametrize(
    ("key", "expected"), _BATCH_LABEL.items(), ids=[str(k) for k in _BATCH_LABEL]
)
def test_batch_label(key: tuple[str, str, float], expected: str) -> None:
    protocol_id, version, scale = key
    assert batch_label(_version(protocol_id, version), scale) == expected


_RENDER_STEP_TEXT: Final[dict[tuple[str, str, str, float], str]] = {
    (
        "PR-TAP-01",
        "1.0",
        "p4",
        10.0,
    ): "Add 250 mL of salt stock S. That single addition delivers the whole salt charge: 3.8 g ammonium chloride, 1 g magnesium sulfate heptahydrate and 0.5 g calcium chloride dihydrate.",
    (
        "PR-TAP-01",
        "1.0",
        "p5",
        0.5,
    ): "Add 5 mL of phosphate stock P, delivering 0.81 g of phosphate salts. Add it slowly and directly into the vortex, with the calcium already dispersed. A local excess of phosphate against undiluted calcium precipitates calcium phosphate as a haze that never clears.",
    (
        "PR-PHOS-01",
        "1.0",
        "f2",
        2.0,
    ): "Dephosphorylate the treated aliquots: add 8 µL of calf intestinal alkaline phosphatase (80 units across the panel) and incubate at 37 °C for 2 h. Run the mock alongside on the same block.",
    (
        "PR-DISRUPT-01",
        "1.0",
        "d1",
        10.0,
    ): "Record the feed before touching it. Measure the culture’s dry cell weight under PR-OD-01 and write it on the batch sheet: OF-COR-001 gives no harvest density for cw15, so every yield below is expressed against your measured figure rather than an assumed one.",
}


@pytest.mark.parametrize(
    ("key", "expected"), _RENDER_STEP_TEXT.items(), ids=[str(k) for k in _RENDER_STEP_TEXT]
)
def test_render_step_text(key: tuple[str, str, str, float], expected: str) -> None:
    protocol_id, version_id, step_id, scale = key
    version = _version(protocol_id, version_id)
    step = next(s for s in version.steps if s.id == step_id)
    assert render_step_text(step, version, scale) == expected


# Synthetic step texts, covering the placeholder branches the corpus does not:
# an unknown material, a `stock:` placeholder on a material with no stock (which
# silently renders the neat amount), a repeated placeholder, a kind outside
# `qty|stock`, an empty material name, a stray brace, and replacement-pattern
# characters that neither language may expand.
_RENDER_EDGE: Final[dict[tuple[str, float], str]] = {
    ("{{qty:No Such Material}}", 2.0): "⟨unknown material: No Such Material⟩",
    ("{{stock:Tris base}}", 2.0): "4.84 g",
    ("{{stock:Ammonium chloride}}", 2.0): "50 mL",
    ("{{qty:Tris base}} and {{qty:Tris base}}", 2.0): "4.84 g and 4.84 g",
    ("no placeholders at all", 2.0): "no placeholders at all",
    ("{{other:Tris base}}", 2.0): "{{other:Tris base}}",
    ("{{qty:}}", 2.0): "{{qty:}}",
    ("{{qty:Tris base}}}", 2.0): "4.84 g}",
    ("$& {{qty:Tris base}} $1 \\n", 2.0): "$& 4.84 g $1 \\n",
}


@pytest.mark.parametrize(
    ("key", "expected"), _RENDER_EDGE.items(), ids=[repr(k) for k in _RENDER_EDGE]
)
def test_render_step_text_edge_cases(key: tuple[str, float], expected: str) -> None:
    text, scale = key
    version = _version("PR-TAP-01", "1.0")
    assert render_step_text(Step(id="edge", text=text), version, scale) == expected


_MATERIALS_CHECKLIST: Final[dict[tuple[str, str, float], tuple[str, ...]]] = {
    ("PR-TAP-01", "1.0", 2.0): (
        "# TAP medium preparation (1 L base) — materials at 2 L batch",
        "# openFerment export — corpus OF-COR-001 v1.0",
        "# Protocol content is real: drawn from the catalogued literature and standard bench practice.",
        "# Amounts here are computed by scaling the base batch, not measured at this scale.",
        "# Cited figures are curator transcriptions, not yet checked against the source PDFs.",
        "",
        "[ ] Tris base: 4.84 g",
        "[ ] Glacial acetic acid: 2 mL",
        "[ ] Ammonium chloride: 0.76 g — use 50 mL of stock (0.015 g/mL)",
        "[ ] Magnesium sulfate heptahydrate: 0.2 g — use 50 mL of stock (0.004 g/mL)",
        "[ ] Calcium chloride dihydrate: 0.1 g — use 50 mL of stock (0.002 g/mL)",
        "[ ] Potassium phosphate salts (K₂HPO₄ + KH₂PO₄): 3.22 g — use 20 mL of stock (0.161 g/mL)",
        "[ ] Hutner trace element solution: 2 mL",
        "[ ] Deionised water (make-up): 1800 mL",
        "[ ] pH 7.00 calibration buffer sachet: 1 sachet (fixed — does not scale)",
        "[ ] pH 4.01 calibration buffer sachet: 1 sachet (fixed — does not scale)",
        "[ ] Autoclave indicator tape: 1 strip (fixed — does not scale)",
    ),
    ("PR-PHOS-01", "1.0", 0.5): (
        "# Phos-tag phosphorylation analysis of recombinant β-casein — materials at 5 lanes per gel pair",
        "# openFerment export — corpus OF-COR-001 v1.0",
        "# Protocol content is real: drawn from the catalogued literature and standard bench practice.",
        "# Amounts here are computed by scaling the base batch, not measured at this scale.",
        "# Cited figures are curator transcriptions, not yet checked against the source PDFs.",
        "",
        "[ ] Purified recombinant β-casein sample: 50 µg",
        "[ ] Native bovine β-casein reference standard: 25 µg",
        "[ ] Phos-tag acrylamide: 25 µL",
        "[ ] Manganese(II) chloride, 10 mM: 250 µL",
        "[ ] Alkaline phosphatase, calf intestinal: 20 units — use 2 µL of stock (10 units/µL)",
        "[ ] Acrylamide/bis solution, 30 % 37.5:1: 10 mL",
        "[ ] Urea, molecular biology grade: 12.5 g",
        "[ ] EDTA soak solution, 10 mM: 100 mL",
        "[ ] Coomassie R-250 staining solution: 50 mL",
        "[ ] Ethyl Stains-All reagent: 25 mL (fixed — does not scale)",
        "[ ] Protein ladder, 10–250 kDa: 100 µL (fixed — does not scale)",
    ),
    ("PR-DISRUPT-01", "1.0", 10.0): (
        "# Harvest and mild PEF disruption of cw15 — materials at 100 L culture",
        "# openFerment export — corpus OF-COR-001 v1.0",
        "# Protocol content is real: drawn from the catalogued literature and standard bench practice.",
        "# Amounts here are computed by scaling the base batch, not measured at this scale.",
        "# Cited figures are curator transcriptions, not yet checked against the source PDFs.",
        "",
        "[ ] Low-conductivity resuspension buffer, 1 mM potassium phosphate pH 7.0: 10,000 mL",
        "[ ] Protease inhibitor tablets, EDTA-free: 50 tablets",
        "[ ] 500 mL centrifuge bottles with sealing caps: 60 bottles",
        "[ ] Membrane-impermeant nucleic acid stain: 5 mL",
        "[ ] Bradford assay reactions: 320 reactions",
        "[ ] Bovine serum albumin standard, 2 mg mL⁻¹: 2 mL (fixed — does not scale)",
        "[ ] 0.4 mm yttria-stabilised zirconia beads: 0.2 L (fixed — does not scale)",
        "[ ] Chamber coolant, 30 % v/v propylene glycol: 4 L (fixed — does not scale)",
        "[ ] Conductivity standard, 1413 µS cm⁻¹: 50 mL (fixed — does not scale)",
    ),
}


@pytest.mark.parametrize(
    ("key", "expected"), _MATERIALS_CHECKLIST.items(), ids=[str(k) for k in _MATERIALS_CHECKLIST]
)
def test_materials_checklist(key: tuple[str, str, float], expected: tuple[str, ...]) -> None:
    protocol_id, version, scale = key
    got = materials_checklist(_version(protocol_id, version), scale, _title(protocol_id))
    # Compared line by line so a failure names the line rather than dumping two
    # forty-line blobs side by side.
    assert got.split("\n") == list(expected)
