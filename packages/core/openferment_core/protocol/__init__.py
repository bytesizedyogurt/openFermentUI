"""Protocol scaling math and version diff — the two engines that act on a protocol.

Both are Python because both leave the browser. Scaling drives physical lab
work: the numbers `scale_material` produces are the numbers somebody weighs out,
and the same figures feed BioSTEAM's material balances. The version diff is a
Ledger concern and has to run server-side, because what a reviewer is shown
about a change has to be what the record says about it.

`src/engine/scale.ts` and `src/engine/diff.ts` stay in the UI as mirrors of these
modules. They are not a second implementation to be kept in step by hand:
`fixtures/scale.json` and `fixtures/diff.json` were captured from them and are
replayed against this package by `tests/test_protocol.py`, so agreement is
enforced mechanically rather than remembered.

`round_to_precision` is imported from `openferment_core.units` and is not
reimplemented here — there is one of it in this repo.
"""

from __future__ import annotations

from .diff import DiffKind, MaterialDiff, StepDiff, VersionDiff, diff_versions
from .scale import (
    ScaledMaterial,
    StockVolume,
    batch_label,
    inoculum_volume,
    materials_checklist,
    render_step_text,
    scale_material,
    scale_materials,
)

__all__ = [
    "DiffKind",
    "MaterialDiff",
    "ScaledMaterial",
    "StepDiff",
    "StockVolume",
    "VersionDiff",
    "batch_label",
    "diff_versions",
    "inoculum_volume",
    "materials_checklist",
    "render_step_text",
    "scale_material",
    "scale_materials",
]
