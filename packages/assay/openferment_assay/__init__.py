"""openferment-assay — gold-set scoring for openFerment extractor runs.

Per-field precision, recall and F1 for one extractor run, reported per
`FieldId` and including the fields that score badly, plus the Inspect AI
scorer that produces those numbers from an eval.

This module re-exports the metric computation ONLY. `openferment_assay.scorer`
is imported explicitly, by path, because importing it pulls in `inspect_ai`,
and the counting rules must stay usable — and testable — where Inspect is not
installed. Nothing in the chain below this line imports Inspect.

    from openferment_assay import compute_run_metrics       # no Inspect needed
    from openferment_assay.scorer import extraction_outcome  # needs Inspect

See `CLAUDE.md` at the repository root for the routing table that puts this
package in Python.
"""

from __future__ import annotations

from .metrics import (
    FAILURE_LABEL,
    NO_FAILURE,
    FieldMetrics,
    GoldItem,
    MicroMetrics,
    OutcomeItem,
    RunMetrics,
    compute_metrics,
    compute_run_metrics,
    prf,
)

__version__ = "0.1.0"

__all__ = [
    "FAILURE_LABEL",
    "NO_FAILURE",
    "FieldMetrics",
    "GoldItem",
    "MicroMetrics",
    "OutcomeItem",
    "RunMetrics",
    "__version__",
    "compute_metrics",
    "compute_run_metrics",
    "prf",
]
