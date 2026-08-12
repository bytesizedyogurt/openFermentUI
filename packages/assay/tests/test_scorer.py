"""Tests for the Inspect AI wrapper.

Three things are checked, in increasing distance from the fixture:

1. `classify_outcome` — the only judgement the wrapper makes.
2. `run_metrics_from_scores` reproduces the captured `computeRunMetrics` output
   EXACTLY when it is fed Inspect scores carrying the fixture's outcomes. This
   is the load-bearing one: it is what says the Inspect path and the store path
   are the same counter and not two counters that happen to agree today.
3. A real `eval()` under Inspect, with a replay solver in place of a model, so
   the claim "this runs as an Inspect scorer" is a thing that was executed
   rather than a thing that was written.

The inputs are the fixture's synthetic gold records, for the reason the fixture
gives: `RUN_OUTPUTS` in the app is empty and stays empty until a real extractor
has been run. The replayed extractions in the eval test are synthetic too, and
chosen to produce one of each outcome — no number here is a claim about any
extractor's performance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("inspect_ai", reason="inspect-ai is the optional `inspect` extra")

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import SampleScore, Score
from inspect_ai.solver import Generate, Solver, TaskState, solver
from openferment_core.schema import RunOutcomeKind
from openferment_core.units import Quantity

from openferment_assay.scorer import (
    classify_outcome,
    extraction_outcome,
    run_metrics_from_scores,
)

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "metrics.json"
_DATA: dict[str, Any] = json.loads(FIXTURES.read_text("utf-8"))
GOLD: list[dict[str, Any]] = _DATA["inputs"]["syntheticGold"]


# ── classify_outcome ───────────────────────────────────────────────────


def test_no_extraction_is_a_miss() -> None:
    assert classify_outcome(None, Quantity(0.2, "% TSP")) is RunOutcomeKind.MISS


def test_same_value_and_unit_is_a_match() -> None:
    assert classify_outcome(Quantity(0.2, "% TSP"), Quantity(0.2, "% TSP")) is RunOutcomeKind.MATCH


def test_convertible_unit_is_a_match_not_a_unit_error() -> None:
    """204 h and 8.5 d are the same measurement written two ways. Charging the
    extractor for the second spelling would penalise it for the thing
    `ExtractionRecord.si` exists to normalise."""
    assert classify_outcome(Quantity(204.0, "h"), Quantity(8.5, "d")) is RunOutcomeKind.MATCH


def test_right_number_wrong_unit_is_a_unit_error() -> None:
    assert classify_outcome(Quantity(8.5, "h"), Quantity(8.5, "d")) is RunOutcomeKind.UNIT_ERROR


def test_wrong_number_is_a_value_mismatch() -> None:
    assert (
        classify_outcome(Quantity(25.0, "µg mL⁻¹"), Quantity(10.0, "µg mL⁻¹"))
        is RunOutcomeKind.VALUE_MISMATCH
    )


def test_unknown_unit_is_compared_as_written() -> None:
    """The engine refuses to bridge what it does not know, and refusal is an
    answer: an unrecognised unit does not quietly become equal to everything."""
    assert (
        classify_outcome(Quantity(8.6, "widgets"), Quantity(8.6, "×")) is RunOutcomeKind.UNIT_ERROR
    )


def test_span_error_is_never_guessed() -> None:
    """The default classifier sees a value and a unit. It cannot know whether
    the quote came from the right span, so it never reports that it did."""
    outcomes = {
        classify_outcome(extracted, Quantity(1.0, "d"))
        for extracted in (None, Quantity(1.0, "d"), Quantity(1.0, "h"), Quantity(2.0, "d"))
    }
    assert RunOutcomeKind.SPAN_ERROR not in outcomes


# ── the Inspect adapter against the captured output ────────────────────


def _sample_scores() -> list[SampleScore]:
    """The fixture's `v0.4` run, expressed as Inspect scores.

    One sample per gold record, carrying the outcome the fixture recorded. The
    run's single seeded false positive is attached to the first sample — only
    its field reaches the arithmetic, which is the same thing the store path
    passes.
    """
    run = next(r for r in _DATA["inputs"]["runs"] if r["run"] == "v0.4")
    outcome_by_id = {r["goldRecordId"]: r["outcome"] for r in run["results"]}
    spurious = [fp["field"] for fp in run["falsePositives"]]
    scores: list[SampleScore] = []
    for index, record in enumerate(GOLD):
        scores.append(
            SampleScore(
                score=Score(
                    value=outcome_by_id[record["id"]],
                    metadata={"spurious_fields": spurious if index == 0 else []},
                ),
                sample_id=record["id"],
                sample_metadata={"field": record["field"], "paper_id": record["paperId"]},
            )
        )
    return scores


def test_inspect_scores_reproduce_the_captured_metrics_exactly() -> None:
    result = run_metrics_from_scores(_sample_scores(), run="v0.4")
    expected = next(c for c in _DATA["computeRunMetrics"] if c["extractorRun"] == "v0.4")["out"]
    assert result.model_dump(by_alias=True, mode="json") == expected


def test_unscored_samples_count_as_gold_but_not_as_a_miss() -> None:
    """Inspect's NaN sentinel means the scorer could not score the sample. The
    record stays in the gold set — it exists — but no outcome is invented for
    it, so nothing is charged to the extractor."""
    scores = _sample_scores()
    scores[1] = SampleScore(
        score=Score.unscored(),
        sample_id=scores[1].sample_id,
        sample_metadata=scores[1].sample_metadata,
    )
    result = run_metrics_from_scores(scores, run="v0.4")
    assert result.gold_size == 6
    assert result.papers_covered == 4
    assert [row.field for row in result.per_field if row.field == "medium_component_conc"] == []


def test_missing_field_metadata_raises_rather_than_guessing() -> None:
    bad = [
        SampleScore(
            score=Score(value="match"),
            sample_id="synthetic-gold-1",
            sample_metadata={"paper_id": "A1"},
        )
    ]
    with pytest.raises(ValueError, match="metadata\\['field'\\] is required"):
        run_metrics_from_scores(bad)


# ── a real eval under Inspect ──────────────────────────────────────────

REPLAY = {
    # value, unit and gold agree
    "synthetic-gold-1": '{"value": 0.2, "unit": "% TSP"}',
    # right shape, wrong number
    "synthetic-gold-2": '{"value": 25, "unit": "µg mL⁻¹"}',
    # correct, and the extractor also emitted a value no gold record claims
    "synthetic-gold-3": '{"value": 0, "unit": "% TSP", "spurious": ["expression_pct_tsp"]}',
    # nothing extracted
    "synthetic-gold-4": "",
    # wrong number
    "synthetic-gold-5": '{"value": 12, "unit": "×"}',
    # right number, unit never normalised
    "synthetic-gold-6": '{"value": 8.5, "unit": "h"}',
}


@solver
def replay_extractions() -> Solver:
    """Stands in for the extractor under test. The scorer is what is being
    exercised here, so the sample carries its own canned output and no model is
    called — `mockllm` satisfies `eval()`'s need for a model and is never
    asked for anything."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.output = ModelOutput.from_content(
            model="replay", content=str(state.metadata.get("replay", ""))
        )
        return state

    return solve


def _task() -> Task:
    samples = [
        Sample(
            id=record["id"],
            input=record["quote"],
            target=f"{record['gold']['value']} {record['gold']['unit']}",
            metadata={
                "field": record["field"],
                "paper_id": record["paperId"],
                "replay": REPLAY[record["id"]],
            },
        )
        for record in GOLD
    ]
    return Task(dataset=samples, solver=replay_extractions(), scorer=extraction_outcome())


@pytest.fixture(scope="module")
def eval_log(tmp_path_factory: pytest.TempPathFactory) -> EvalLog:
    logs = eval(
        _task(),
        model="mockllm/model",
        log_dir=str(tmp_path_factory.mktemp("logs")),
        display="none",
    )
    assert logs[0].status == "success", logs[0].error
    return logs[0]


def _metrics(log: EvalLog) -> dict[str, float]:
    assert log.results is not None
    return {name: m.value for name, m in log.results.scores[0].metrics.items()}


def test_eval_scores_every_sample(eval_log: EvalLog) -> None:
    assert eval_log.results is not None
    assert eval_log.results.completed_samples == len(GOLD)


def test_eval_classifies_each_outcome(eval_log: EvalLog) -> None:
    assert eval_log.samples is not None
    outcomes = {
        str(sample.id): str(next(iter(sample.scores.values())).value)
        for sample in eval_log.samples
        if sample.scores
    }
    assert outcomes == {
        "synthetic-gold-1": "match",
        "synthetic-gold-2": "value_mismatch",
        "synthetic-gold-3": "match",
        "synthetic-gold-4": "miss",
        "synthetic-gold-5": "value_mismatch",
        "synthetic-gold-6": "unit_error",
    }


def test_eval_reports_every_field_including_the_worst(eval_log: EvalLog) -> None:
    """The clause this package exists for. Two fields scored zero on every
    statistic and both are in the log with their counts — `fold_improvement`
    missed one record and got the other wrong, `time_to_colony` never
    normalised its unit — next to the field that did well."""
    metrics = _metrics(eval_log)
    for field in (
        "expression_pct_tsp",
        "fold_improvement",
        "medium_component_conc",
        "time_to_colony",
    ):
        assert f"{field}/f1" in metrics, f"{field} fell out of the report"

    assert metrics["expression_pct_tsp/tp"] == 2
    assert metrics["expression_pct_tsp/fp"] == 1  # the spurious extraction
    assert metrics["expression_pct_tsp/f1"] == 0.8

    assert metrics["fold_improvement/f1"] == 0
    assert metrics["fold_improvement/n_gold"] == 2
    assert metrics["fold_improvement/fn"] == 2

    assert metrics["time_to_colony/f1"] == 0
    assert metrics["time_to_colony/fp"] == 1
    assert metrics["medium_component_conc/f1"] == 0


def test_eval_reports_the_micro_average_with_its_counts(eval_log: EvalLog) -> None:
    metrics = _metrics(eval_log)
    assert (metrics["tp"], metrics["fp"], metrics["fn"]) == (2, 4, 4)
    assert metrics["gold_size"] == 6
    assert metrics["papers_covered"] == 4


def test_eval_per_field_rows_are_ordered_by_gold_size(eval_log: EvalLog) -> None:
    """Insertion order survives into the log, so the report reads in the same
    order the pure function produced: by gold-set size, not by score."""
    assert eval_log.results is not None
    order = [
        name.split("/")[0]
        for name in eval_log.results.scores[0].metrics
        if name.endswith("/n_gold")
    ]
    assert order == [
        "expression_pct_tsp",
        "fold_improvement",
        "medium_component_conc",
        "time_to_colony",
    ]
