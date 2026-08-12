"""Fixture replay for the metrics port.

`fixtures/metrics.json` was captured from `src/engine/metrics.ts`: three
`computeRunMetrics` cases over synthetic inputs. The fixture says why they are
synthetic, and the reason is invariant 2 — `RUN_OUTPUTS` in the app is empty
and stays empty until a real extractor has been run, so there is no real run to
capture. The inputs exist to exercise every branch: every outcome kind, a
seeded false positive, a result naming a gold record that no longer exists, and
an empty run.

This is the parity gate, so it is deliberately dumb: every case is compared
whole, by alias, against the captured output. Nothing is compared field by
field with a tolerance — the arithmetic is the same IEEE double arithmetic in
the same order, so it either agrees exactly or the port is wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from openferment_core.schema import ExtractionRecord, RunOutput

from openferment_assay import compute_run_metrics, prf

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "metrics.json"
_DATA: dict[str, Any] = json.loads(FIXTURES.read_text("utf-8"))

RECORDS = [ExtractionRecord.model_validate(r) for r in _DATA["inputs"]["syntheticGold"]]
RUNS = {r["run"]: RunOutput.model_validate(r) for r in _DATA["inputs"]["runs"]}
CASES: list[dict[str, Any]] = _DATA["computeRunMetrics"]


def _case(label: str) -> dict[str, Any]:
    return next(c for c in CASES if c["label"] == label)


def _metrics(label: str) -> dict[str, Any]:
    case = _case(label)
    result = compute_run_metrics(RUNS[case["extractorRun"]], RECORDS)
    dumped: dict[str, Any] = result.model_dump(by_alias=True, mode="json")
    return dumped


# ── computeRunMetrics ──────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c["label"] for c in CASES])
def test_compute_run_metrics(case: dict[str, Any]) -> None:
    result = compute_run_metrics(RUNS[case["extractorRun"]], RECORDS)
    assert result.model_dump(by_alias=True, mode="json") == case["out"]


def test_every_fixture_case_ran() -> None:
    """The fixture has three cases and all three are exercised. A parity gate
    that silently stops covering a case is worse than no gate."""
    assert len(CASES) == 3
    assert {c["extractorRun"] for c in CASES} == {"v0.4", "v0.4r", "v0.3"}


# ── the properties the fixture is pinning, stated in their own right ────


def test_per_field_is_ordered_by_gold_size_descending() -> None:
    """Rows sort by `nGold` descending with ties in first-seen order — not by
    score, so a field with no true positives keeps its place in the table."""
    out = _metrics("every outcome, plus a false positive")
    n_gold = [row["nGold"] for row in out["perField"]]
    assert n_gold == sorted(n_gold, reverse=True)
    assert [row["field"] for row in out["perField"]] == [
        "expression_pct_tsp",
        "fold_improvement",
        "medium_component_conc",
        "time_to_colony",
    ]


def test_fields_that_score_zero_are_reported() -> None:
    """The point of the screen this replaces. Two fields in the first case
    scored no true positives at all, and both are in the report with their
    counts and their top failure — not omitted, not folded into an average."""
    out = _metrics("every outcome, plus a false positive")
    zero = {row["field"]: row for row in out["perField"] if row["f1"] == 0}
    assert set(zero) == {"fold_improvement", "medium_component_conc"}
    assert zero["fold_improvement"]["fn"] == 2
    assert zero["fold_improvement"]["topFailure"] == "wrong span"
    assert zero["medium_component_conc"]["topFailure"] == "value mismatch"


def test_mismatch_charges_both_books() -> None:
    """A mismatch is one FP and one FN: a wrong record was produced AND the gold
    one was missed. `medium_component_conc` has exactly one `value_mismatch`
    against it and nothing else."""
    out = _metrics("every outcome, plus a false positive")
    row = next(r for r in out["perField"] if r["field"] == "medium_component_conc")
    assert (row["tp"], row["fp"], row["fn"]) == (0, 1, 1)


def test_miss_charges_only_a_false_negative() -> None:
    """`fold_improvement` takes one `span_error` (FP+FN) and one `miss` (FN
    only): two FN, one FP."""
    out = _metrics("every outcome, plus a false positive")
    row = next(r for r in out["perField"] if r["field"] == "fold_improvement")
    assert (row["tp"], row["fp"], row["fn"]) == (0, 1, 2)


def test_seeded_false_positive_adds_fp_to_its_field() -> None:
    """`expression_pct_tsp` has one match, one unit_error (FP+FN) and one seeded
    false positive (FP): tp 1, fp 2, fn 1."""
    out = _metrics("every outcome, plus a false positive")
    row = next(r for r in out["perField"] if r["field"] == "expression_pct_tsp")
    assert (row["tp"], row["fp"], row["fn"]) == (1, 2, 1)


def test_vanished_gold_record_is_dropped_not_counted_as_a_miss() -> None:
    """The `v0.4r` run names `record-that-was-deleted`, which no longer exists.
    It contributes nothing — no TP for the match it claims, and no FN either.
    Its two surviving results are the whole of the run's counts."""
    out = _metrics("a result naming a gold record that no longer exists")
    assert (out["micro"]["tp"], out["micro"]["fp"], out["micro"]["fn"]) == (1, 1, 1)
    assert [row["field"] for row in out["perField"]] == [
        "expression_pct_tsp",
        "medium_component_conc",
    ]


def test_gold_set_size_describes_the_gold_set_not_the_run() -> None:
    """`v0.4r` produced results for two records and `v0.3` for none, and both
    still report the full gold set: six records over four papers. A run cannot
    shrink the gold set by ignoring it."""
    for label in (
        "a result naming a gold record that no longer exists",
        "no results and no false positives",
    ):
        out = _metrics(label)
        assert out["goldSize"] == 6
        assert out["papersCovered"] == 4


def test_empty_run_reports_zeros_and_no_rows() -> None:
    out = _metrics("no results and no false positives")
    assert out["perField"] == []
    assert out["micro"] == {"precision": 0, "recall": 0, "f1": 0, "tp": 0, "fp": 0, "fn": 0}


def test_top_failure_is_the_em_dash_when_a_field_never_failed() -> None:
    out = _metrics("every outcome, plus a false positive")
    row = next(r for r in out["perField"] if r["field"] == "time_to_colony")
    assert row["topFailure"] == "—"
    assert (row["precision"], row["recall"], row["f1"]) == (1, 1, 1)


# ── prf ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ((0, 0, 0), (0.0, 0.0, 0.0)),
        ((0, 3, 0), (0.0, 0.0, 0.0)),  # predictions, none right → precision 0
        ((0, 0, 3), (0.0, 0.0, 0.0)),  # gold, none found → recall 0
        ((1, 1, 1), (0.5, 0.5, 0.5)),
        ((2, 0, 0), (1.0, 1.0, 1.0)),
    ],
)
def test_prf_zero_denominator_conventions(
    counts: tuple[int, int, int], expected: tuple[float, float, float]
) -> None:
    """An empty denominator is 0, never NaN and never an exception: the row
    stays in the table where a NaN would invite a caller to drop it."""
    assert tuple(prf(*counts)) == expected
