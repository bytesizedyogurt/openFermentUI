"""The Inspect AI wrapper around `openferment_assay.metrics`.

Everything in here is adapter. It carries no counting rule of its own: both
metrics project Inspect's `SampleScore` list into the `GoldItem` /
`OutcomeItem` / spurious-field triple that `compute_metrics` takes, and hand it
over. A rule that lived in both places would have to be kept in step by hand,
which is the failure this package exists to prevent — so if a number here looks
wrong, `metrics.py` is where it is wrong.

**Why the split is load bearing.** `metrics.py` never imports Inspect, so the
counting rules — and the fixture parity gate over them — run in an environment
where `inspect-ai` was never installed. This module is the only thing that
needs it. That is also why `openferment_assay/__init__.py` does not re-export
anything from here.

**How a sample carries its gold record.** Each sample IS one gold record. The
scorer needs three things from `sample.metadata`, and raises rather than guess
when they are missing:

    field       the FieldId the record is reported under
    paper_id    the paper it came from — this is what `papersCovered` counts
    gold_record_id  optional; the sample id is used when it is absent

`Sample.target` is the gold answer as text (`"10 µg mL⁻¹"`), parsed with the
canonical unit engine in `openferment_core.units`. No unit arithmetic is
written here either.

**What the metric emits, and what it cannot.** Inspect's `Value` admits a flat
mapping only — `Mapping[str, str | int | float | bool | None]`, no nesting — so
a per-field table is emitted as `"<field>/<statistic>"` keys. Every field the
run touched gets its full set of keys, including the fields that scored zero.
Suppressing them would make the eval log read better than the run it describes,
which is the exact failure the per-field report exists to catch.

Every entry of that mapping is coerced with `float()` when Inspect builds the
eval log (`inspect_ai/_eval/task/results.py`), so a metric can carry numbers
only — `top_failure` would raise there. The label is not lost: it is on
`RunMetrics.top_failure`, from `run_metrics_from_scores` or from the pure
`compute_metrics`, where a string can be held as a string. A caller that wants
the whole table asks for the model, not for the metric.

**Both metrics are declared `scores="unreduced"`.** The score value here is a
word — 'match', 'unit_error' — and Inspect's epoch reducers average score
values through `value_to_float`, where a word it does not recognise becomes
0.0. Left on the default, every outcome reaches the metric as the same number
and the report is silently all zeros. Nothing is lost by opting out: these
metrics aggregate the raw outcomes themselves, which is the entire job, so
there is nothing for a reducer to do first.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from inspect_ai.scorer import Metric, SampleScore, Score, Scorer, Target, Value, metric, scorer
from inspect_ai.solver import TaskState
from openferment_core.schema import FieldId, RunOutcomeKind
from openferment_core.units import Quantity, convert, normalize_unit, parse_quantity

from .metrics import GoldItem, OutcomeItem, RunMetrics, compute_metrics

__all__ = [
    "FIELD_KEY",
    "GOLD_ID_KEY",
    "PAPER_KEY",
    "SPURIOUS_KEY",
    "OutcomeClassifier",
    "classify_outcome",
    "extraction_outcome",
    "micro_prf",
    "per_field_prf",
    "run_metrics_from_scores",
]

FIELD_KEY = "field"
PAPER_KEY = "paper_id"
GOLD_ID_KEY = "gold_record_id"
SPURIOUS_KEY = "spurious_fields"
"""Score metadata key: fields of the spurious extractions produced for this
sample — values no gold record claims. Each one adds an FP to its field."""


# ── outcome classification ──────────────────────────────────────────────

OutcomeClassifier = Callable[[Quantity | None, Quantity | None], RunOutcomeKind]
"""`(extracted, gold) -> outcome`. Injected so a pipeline that carries span
provenance can classify `span_error`, which this module cannot — see
`classify_outcome`."""


def classify_outcome(extracted: Quantity | None, gold: Quantity | None) -> RunOutcomeKind:
    """Classify one extraction against its gold answer.

    The rules, in the order they are tried, and why:

    1. Nothing extracted → `miss`. The run stayed silent; there is no wrong
       record to charge it for.
    2. Equal once converted into the gold's unit → `match`. A value in a
       different but convertible unit is the same measurement written another
       way — that is what `ExtractionRecord.si` exists to say — so it is not
       held against the extractor.
    3. Same number, different unit → `unit_error`. This is the normalization
       failure the label names: the number was read correctly off the page and
       the unit was not.
    4. Anything else, including output that does not parse as a quantity →
       `value_mismatch`. Unparseable output is a wrong record, not a missing
       one; it costs both an FP and an FN, which is the correct charge for
       having produced something wrong.

    `span_error` is never returned. Whether the supporting quote came from the
    right span is not decidable from a value and a unit, and guessing it would
    put a failure kind in the report that nothing measured. A pipeline that
    does carry spans passes its own classifier to `extraction_outcome`; the
    counting rules in `metrics.py` handle all five kinds either way.
    """
    if extracted is None:
        return RunOutcomeKind.MISS
    if gold is None:
        # No gold answer to compare against. Not this function's call to make —
        # a sample with no target should not have reached a scorer.
        raise ValueError("classify_outcome: no gold quantity to score against")
    try:
        if convert(extracted.value, extracted.unit, gold.unit) == gold.value:
            return RunOutcomeKind.MATCH
    except ValueError:
        # Unknown unit, or two families the engine refuses to bridge. Refusal is
        # an answer: it is not a match, and the rules below still apply.
        pass
    if extracted.value == gold.value and _unit_key(extracted.unit) != _unit_key(gold.unit):
        return RunOutcomeKind.UNIT_ERROR
    return RunOutcomeKind.VALUE_MISMATCH


def _unit_key(unit: str) -> str:
    """Canonical form of a unit string for equality, falling back to the raw
    text when the engine does not know the unit. An unknown unit is compared as
    written rather than silently treated as equal to everything else."""
    return normalize_unit(unit) or unit


def _parse_extracted(completion: str) -> Quantity | None:
    """Read one extraction out of a model completion.

    Accepts either a JSON object with `value` and `unit` — what a structured
    extractor emits — or free text the unit engine can parse (`"10 µg mL⁻¹"`).
    An empty completion, JSON `null`, or a JSON object whose `value` is null is
    the extractor saying it found nothing, and becomes a `miss`. Output that is
    present but unreadable is NOT a miss — the extractor produced something, and
    something wrong is what `value_mismatch` charges for — so it comes back as a
    quantity of NaN, which equals nothing and falls to that rule.
    """
    text = completion.strip()
    if not text:
        return None
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        return parse_quantity(text) or Quantity(math.nan, "")
    if payload is None:
        return None
    if isinstance(payload, dict):
        if payload.get("value") is None:
            return None
        try:
            return Quantity(float(payload["value"]), str(payload.get("unit", "")))
        except (TypeError, ValueError):
            return Quantity(math.nan, str(payload.get("unit", "")))
    if isinstance(payload, int | float):
        return Quantity(float(payload), "")
    return parse_quantity(str(payload)) or Quantity(math.nan, "")


def _spurious_fields(completion: str) -> list[FieldId]:
    """Fields of any extra extractions the completion declares under
    `spurious` — a structured extractor reporting values it emitted that the
    sample's gold record does not claim. Absent from free-text output, which
    can only answer the one record it was asked for."""
    text = completion.strip()
    if not text.startswith("{"):
        return []
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    raw = payload.get("spurious") or []
    if not isinstance(raw, list):
        return []
    return [FieldId(str(f)) for f in raw]


# ── the scorer ──────────────────────────────────────────────────────────


def _meta(state: TaskState) -> dict[str, Any]:
    meta: dict[str, Any] = dict(state.metadata or {})
    return meta


def _require(meta: dict[str, Any], key: str, sample_id: object) -> str:
    value = meta.get(key)
    if value is None or value == "":
        raise ValueError(
            f"sample {sample_id!r}: metadata[{key!r}] is required — "
            "every sample in this task is one gold record, and the per-field "
            "report cannot be assembled without it"
        )
    return str(value)


# ── metrics ─────────────────────────────────────────────────────────────


def run_metrics_from_scores(scores: list[SampleScore], run: str = "inspect") -> RunMetrics:
    """Project Inspect's scores onto `compute_metrics`. The only adapter.

    One sample is one gold record, so every score contributes a `GoldItem` —
    including a score marked unscored (Inspect's NaN sentinel). That mirrors the
    TypeScript, where a gold record with no result still counts toward
    `goldSize`, `papersCovered` and the field's `nGold`, and only its absent
    outcome goes uncounted. An unscored sample contributes no outcome: a sample
    the scorer could not score is not evidence that the extractor missed it, and
    recording it as a miss would invent a failure that was never observed.

    Under `eval()` that branch is never reached, because Inspect filters
    unscored samples out before calling a metric. It is here for the direct
    callers — `inspect_ai.score`, a notebook, this package's own tests — who see
    the unfiltered list, and so that the rule is written down rather than
    inherited from someone else's filter.

    Over more than one epoch the same gold record is scored more than once. Each
    attempt is counted as an attempt, so TP/FP/FN accumulate across epochs, but
    the record is still one record and enters the gold set once: `n_gold`,
    `gold_size` and `papers_covered` describe the gold set, never the number of
    times it was asked.
    """
    gold: list[GoldItem] = []
    outcomes: list[OutcomeItem] = []
    spurious: list[FieldId] = []
    seen: set[str] = set()
    for index, sample in enumerate(scores):
        meta: dict[str, Any] = {**(sample.sample_metadata or {}), **(sample.score.metadata or {})}
        sample_id = sample.sample_id if sample.sample_id is not None else index
        gold_id = str(meta.get(GOLD_ID_KEY) or sample_id)
        if gold_id not in seen:
            seen.add(gold_id)
            gold.append(
                GoldItem(
                    id=gold_id,
                    field=FieldId(_require(meta, FIELD_KEY, sample_id)),
                    paper_id=_require(meta, PAPER_KEY, sample_id),
                )
            )
        value = sample.score.value
        if isinstance(value, float) and math.isnan(value):
            continue  # Inspect's unscored sentinel — no outcome was observed
        outcomes.append(OutcomeItem(gold_record_id=gold_id, outcome=RunOutcomeKind(str(value))))
        spurious.extend(FieldId(str(f)) for f in meta.get(SPURIOUS_KEY, ()))
    return compute_metrics(run=run, gold=gold, outcomes=outcomes, spurious=spurious)


@metric(scores="unreduced")
def per_field_prf() -> Metric:
    """Per-field precision, recall and F1 — every field, in `nGold` order.

    Emitted flat, as `"<field>/<statistic>"`, because Inspect's `Value` admits
    no nested mapping. Each field carries its TP/FP/FN alongside the three
    scores: a row reading 0/0/0 for P/R/F1 says nothing about whether the field
    was attempted and got everything wrong or was never attempted at all, and
    those call for different work.

    The counts are what make the zero rows readable, and the zero rows are the
    reason this metric reports per field at all — the fields that score badly
    are the only ones that say where to go next.
    """

    def metric_fn(scores: list[SampleScore]) -> Value:
        result = run_metrics_from_scores(scores)
        out: dict[str, str | int | float | bool | None] = {}
        for row in result.per_field:
            out[f"{row.field}/n_gold"] = row.n_gold
            out[f"{row.field}/tp"] = row.tp
            out[f"{row.field}/fp"] = row.fp
            out[f"{row.field}/fn"] = row.fn
            out[f"{row.field}/precision"] = row.precision
            out[f"{row.field}/recall"] = row.recall
            out[f"{row.field}/f1"] = row.f1
        return out

    return metric_fn


@metric(scores="unreduced")
def micro_prf() -> Metric:
    """Run-level micro average, with the raw TP/FP/FN it came from.

    The counts ship with the scores on purpose: micro P/R/F1 alone cannot tell a
    run that answered everything badly from one that answered almost nothing.
    """

    def metric_fn(scores: list[SampleScore]) -> Value:
        result = run_metrics_from_scores(scores)
        return {
            "precision": result.micro.precision,
            "recall": result.micro.recall,
            "f1": result.micro.f1,
            "tp": result.micro.tp,
            "fp": result.micro.fp,
            "fn": result.micro.fn,
            "gold_size": result.gold_size,
            "papers_covered": result.papers_covered,
        }

    return metric_fn


@scorer(metrics=[per_field_prf(), micro_prf()])
def extraction_outcome(classify: OutcomeClassifier | None = None) -> Scorer:
    """Score one gold record: `match`, `value_mismatch`, `unit_error`,
    `span_error` or `miss`.

    The score's value is the outcome name — the same vocabulary as
    `RunOutcomeKind` in the schema, so the eval log and the store say the same
    words about the same run. Aggregation into P/R/F1 is the metrics' job;
    nothing is averaged here.

    Args:
        classify: outcome classifier. Defaults to `classify_outcome`, which
            reads a value and a unit and therefore never returns `span_error`.
            A pipeline that carries span provenance supplies its own.
    """
    classifier = classify or classify_outcome

    async def score(state: TaskState, target: Target) -> Score:
        meta = _meta(state)
        sample_id = state.sample_id
        field = FieldId(_require(meta, FIELD_KEY, sample_id))
        paper_id = _require(meta, PAPER_KEY, sample_id)
        completion = state.output.completion if state.output is not None else ""
        extracted = _parse_extracted(completion)
        gold = parse_quantity(target.text)
        outcome = classifier(extracted, gold)
        return Score(
            value=outcome.value,
            answer=completion,
            explanation=(
                f"{field}: extracted {extracted!r} against gold {gold!r} → {outcome.value}"
            ),
            metadata={
                FIELD_KEY: str(field),
                PAPER_KEY: paper_id,
                GOLD_ID_KEY: str(meta.get(GOLD_ID_KEY) or sample_id),
                SPURIOUS_KEY: [str(f) for f in _spurious_fields(completion)],
            },
        )

    return score
