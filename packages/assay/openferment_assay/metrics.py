"""Validation metrics (OF-DES-001 §8.8): P/R/F1 against the gold set.

Ported from `src/engine/metrics.ts`. This module is the canonical
implementation; the TypeScript screen that computed its own numbers is what
this replaces. Nothing here imports Inspect — see `openferment_assay.scorer`
for the wrapper, and the module docstring there for why the split is load
bearing.

**The report names every field, including the ones that score badly.** That is
the whole point of the screen this comes from. A per-field table that quietly
drops the fields with no true positives reads as a better extractor than the
one that was actually run, and the fields with the worst F1 are the only ones
that tell you where to work next. `compute_metrics` therefore emits a row for
every field the run touched — including rows that are all zeros — and sorts by
gold-set size rather than by score, so a bad field cannot fall off the bottom.

**The counting rules, and why each one is what it is.** A gold record counts TP
when the run's outcome is 'match'. A mismatch outcome — `value_mismatch`,
`unit_error`, `span_error` — counts BOTH FP and FN, because the run produced a
wrong record AND missed the gold one; charging it only one of the two would let
a confidently wrong extractor score better than a silent one. 'miss' counts FN
only: nothing wrong was emitted. Seeded false positives — values the extractor
produced that no gold record claims — add FP. A result naming a gold record
that no longer exists is dropped from the metrics rather than counted as a
miss, because a record deleted mid-session is missing from the gold set, not
missed by the extractor.

**Two entry points, one set of rules.** `compute_metrics` counts; it takes the
three minimal things the rules actually need (gold identity, per-record
outcome, spurious fields). `compute_run_metrics` is the adapter for a
`RunOutput` from the store and is the exact counterpart of `computeRunMetrics`
in the TypeScript — same name, so the two grep as one thing. The Inspect metric
in `scorer.py` is a second adapter onto the same counter. Neither adapter
re-implements a rule; that duplication is the failure this package exists to
prevent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NamedTuple

from openferment_core.schema import ExtractionRecord, FieldId, RunOutcomeKind, RunOutput
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

__all__ = [
    "FAILURE_LABEL",
    "NO_FAILURE",
    "FieldMetrics",
    "GoldItem",
    "MicroMetrics",
    "OutcomeItem",
    "RunMetrics",
    "compute_metrics",
    "compute_run_metrics",
    "prf",
]


class AssayModel(BaseModel):
    """Base for the report shapes in this module.

    Deliberately not `openferment_core.schema.OFModel`: that is the base for
    openFerment *entities* and carries entity policy (`extra='forbid'`,
    validation on assignment, the no-normalising string rules). These are a
    computed report, not an entity. What they do share is the house wire
    convention — snake_case in Python, camelCase on the wire — because
    `fixtures/metrics.json` was captured from the TypeScript and the parity gate
    compares against those camelCase keys directly.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PRF(NamedTuple):
    precision: float
    recall: float
    f1: float


def prf(tp: int, fp: int, fn: int) -> PRF:
    """Precision, recall and F1, with the TypeScript's zero-denominator rules.

    An empty denominator yields 0, not NaN and not an exception: a field with no
    predictions has precision 0, a field with no gold has recall 0, and a field
    with neither has F1 0. Zero is the honest reading here — nothing was right —
    and it keeps the row in the table where a NaN would invite a caller to drop
    it. The arithmetic is written in the same order as `metrics.ts` so the two
    produce bit-identical doubles.
    """
    precision = 0.0 if tp + fp == 0 else tp / (tp + fp)
    recall = 0.0 if tp + fn == 0 else tp / (tp + fn)
    f1 = 0.0 if precision + recall == 0 else (2 * precision * recall) / (precision + recall)
    return PRF(precision, recall, f1)


FAILURE_LABEL: dict[str, str] = {
    "value_mismatch": "value mismatch",
    "unit_error": "unit normalization",
    "span_error": "wrong span",
    "miss": "missed entirely",
}
"""Human labels for the failure kinds, from `metrics.ts`.

'spurious' is deliberately absent. The TypeScript falls back to the raw key
(`FAILURE_LABEL[k] ?? k`), so a field whose worst failure is a seeded false
positive reports the bare word 'spurious'. That fallback is reproduced rather
than tidied up: adding a label here would change what the screen prints.
"""

NO_FAILURE = "—"
"""What `topFailure` reads when a field recorded no failures at all (em dash)."""


@dataclass(frozen=True, slots=True)
class GoldItem:
    """One gold-set record, reduced to what the counting rules need.

    `id` is what a run result points at, `field` is what the row is reported
    under, and `paper_id` feeds `papersCovered`. Nothing else about a record
    affects a metric.
    """

    id: str
    field: FieldId
    paper_id: str


@dataclass(frozen=True, slots=True)
class OutcomeItem:
    """How one gold record fared, reduced to what the counting rules need."""

    gold_record_id: str
    outcome: RunOutcomeKind


@dataclass
class _Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    failures: dict[str, int] = field(default_factory=dict)


class FieldMetrics(AssayModel):
    """One row of the per-field table — one `FieldId`, however badly it scored."""

    field: FieldId
    n_gold: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    top_failure: str


class MicroMetrics(AssayModel):
    """Run-level micro average. Inline in the TypeScript; named here because
    Pydantic has no anonymous model."""

    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


class RunMetrics(AssayModel):
    """Everything one extractor run scored.

    `gold_size` and `papers_covered` describe the GOLD SET, not the run: they
    are counted over every gold record handed in, including records the run
    never produced a result for. A run that answered one of six records must not
    be able to report a gold set of one.
    """

    run: str
    micro: MicroMetrics
    per_field: list[FieldMetrics]
    gold_size: int
    papers_covered: int


def compute_metrics(
    run: str,
    gold: Sequence[GoldItem],
    outcomes: Sequence[OutcomeItem],
    spurious: Sequence[FieldId] = (),
) -> RunMetrics:
    """Count one run into per-field and micro P/R/F1. The rules live here only.

    `spurious` is the field of each false positive the run produced — a value no
    gold record claims. Only its field matters to the arithmetic.

    Ordering is part of the contract, not a presentation detail, and is checked
    against the fixture:

    - Rows are sorted by `n_gold` DESCENDING, and ties keep first-seen order.
      `Array.prototype.sort` has been stable since ES2019 and Python's `sorted`
      is stable, so `key=-n_gold` over an insertion-ordered dict reproduces the
      TypeScript exactly. Sorting by gold-set size rather than by score is what
      keeps a zero-F1 field in the middle of the table instead of at the bottom
      where it reads as an afterthought.
    - `top_failure` is the failure kind with the strictly greatest count, so a
      tie keeps the kind seen first. The running maximum starts at 0 and every
      recorded count is at least 1, so any failure at all beats the
      `NO_FAILURE` default.
    """
    by_id = {g.id: g for g in gold}
    per_field_counts: dict[FieldId, _Counts] = {}

    def ensure(f: FieldId) -> _Counts:
        return per_field_counts.setdefault(f, _Counts())

    for res in outcomes:
        rec = by_id.get(res.gold_record_id)
        if rec is None:
            continue  # gold record removed during session — drop from metrics
        c = ensure(rec.field)
        if res.outcome == RunOutcomeKind.MATCH:
            c.tp += 1
        elif res.outcome == RunOutcomeKind.MISS:
            c.fn += 1
            c.failures["miss"] = c.failures.get("miss", 0) + 1
        else:
            # A wrong record AND a missed gold one: both books are charged.
            c.fp += 1
            c.fn += 1
            c.failures[res.outcome.value] = c.failures.get(res.outcome.value, 0) + 1
    for field_id in spurious:
        c = ensure(field_id)
        c.fp += 1
        c.failures["spurious"] = c.failures.get("spurious", 0) + 1

    gold_by_field: dict[FieldId, int] = {}
    for g in gold:
        gold_by_field[g.field] = gold_by_field.get(g.field, 0) + 1

    rows: list[FieldMetrics] = []
    tp = fp = fn = 0
    for field_id, c in per_field_counts.items():
        tp += c.tp
        fp += c.fp
        fn += c.fn
        top_failure = NO_FAILURE
        top_count = 0
        for kind, count in c.failures.items():
            if count > top_count:
                top_count = count
                top_failure = FAILURE_LABEL.get(kind, kind)
        scores = prf(c.tp, c.fp, c.fn)
        rows.append(
            FieldMetrics(
                field=field_id,
                n_gold=gold_by_field.get(field_id, 0),
                tp=c.tp,
                fp=c.fp,
                fn=c.fn,
                precision=scores.precision,
                recall=scores.recall,
                f1=scores.f1,
                top_failure=top_failure,
            )
        )
    rows.sort(key=lambda row: -row.n_gold)

    micro = prf(tp, fp, fn)
    return RunMetrics(
        run=run,
        micro=MicroMetrics(
            precision=micro.precision,
            recall=micro.recall,
            f1=micro.f1,
            tp=tp,
            fp=fp,
            fn=fn,
        ),
        per_field=rows,
        gold_size=len(gold),
        papers_covered=len({g.paper_id for g in gold}),
    )


def compute_run_metrics(run: RunOutput, records: Sequence[ExtractionRecord]) -> RunMetrics:
    """Compute metrics for one extractor run — the port of `computeRunMetrics`.

    Named for its TypeScript counterpart rather than snake_cased away from it,
    the same call the schema port made for `isAggregatable`: the two are one
    thing and should grep as one thing.

    A record is in the gold set when it carries a `gold` value. The TypeScript
    tests `records.filter(r => r.gold)` — an object, always truthy when present
    — so `is not None` is the same test, including for a gold answer of 0.
    """
    gold_records = [r for r in records if r.gold is not None]
    return compute_metrics(
        run=str(run.run),
        gold=[GoldItem(id=r.id, field=r.field, paper_id=r.paper_id) for r in gold_records],
        outcomes=[
            OutcomeItem(gold_record_id=res.gold_record_id, outcome=res.outcome)
            for res in run.results
        ],
        spurious=[fp.field for fp in run.false_positives],
    )
