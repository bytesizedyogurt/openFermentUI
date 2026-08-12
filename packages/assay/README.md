# openferment-assay

Gold-set scoring for openFerment extractor runs, in Python: per-field
precision, recall and F1 for one run, reported per `FieldId`, **including the
fields that score badly**.

That last clause is the package. The screen this replaces computed its own
numbers in the browser, and a per-field report that quietly omits its worst
fields reads as a better extractor than the one that was run. Every field the
run touched gets a row here — zeros and all — sorted by gold-set size rather
than by score, so a field with no true positives cannot fall off the bottom of
the table.

Scoring is Python because Inspect AI is Python. See `CLAUDE.md` at the
repository root for the routing table.

## What is where

| | |
|---|---|
| `openferment_assay/metrics.py` | The counting rules. A pure function. No Inspect import anywhere in its chain. |
| `openferment_assay/scorer.py` | The Inspect AI wrapper: one scorer, two metrics. Adapter only — it carries no counting rule of its own. |
| `tests/test_metrics.py` | Fixture parity against `fixtures/metrics.json`, captured from `src/engine/metrics.ts`. |
| `tests/test_metrics_without_inspect.py` | A child interpreter with `inspect_ai` blocked, proving the split above is real. |
| `tests/test_scorer.py` | The wrapper, and a real `eval()` run under Inspect. |

## The counting rules

A gold record counts **TP** when the run's outcome is `match`. A mismatch —
`value_mismatch`, `unit_error`, `span_error` — counts **both FP and FN**,
because the run produced a wrong record *and* missed the gold one; charging it
only one of the two would let a confidently wrong extractor outscore a silent
one. A `miss` counts **FN only**. A seeded false positive — a value no gold
record claims — adds **FP** to its field. A result naming a gold record that no
longer exists is **dropped**, not counted as a miss: a record deleted
mid-session is missing from the gold set, not missed by the extractor.

`gold_size`, `papers_covered` and each row's `n_gold` describe the gold set, not
the run. A run that answered one of six records still reports a gold set of six.

## Public API

```python
from openferment_assay import compute_run_metrics  # no Inspect needed
from openferment_assay.scorer import extraction_outcome  # needs Inspect
```

- `compute_run_metrics(run: RunOutput, records: Sequence[ExtractionRecord]) -> RunMetrics`
  — the port of `computeRunMetrics`, keeping its name so the two grep as one
  thing.
- `compute_metrics(run, gold, outcomes, spurious) -> RunMetrics` — the counter
  itself, over the three minimal things the rules need. Both the `RunOutput`
  adapter above and the Inspect metrics below go through this one function.
- `prf(tp, fp, fn) -> PRF` — precision, recall, F1, with the zero-denominator
  conventions the TypeScript pinned.
- `extraction_outcome(classify=None) -> Scorer` — scores one gold record as one
  of the five `RunOutcomeKind` values.
- `per_field_prf()`, `micro_prf()` — the metrics, attached to that scorer.
- `run_metrics_from_scores(scores, run="inspect") -> RunMetrics` — the same
  numbers as the metrics, as a model rather than a flat mapping, so the labels
  Inspect cannot carry (`top_failure`) are still reachable.

## Parity

`fixtures/metrics.json` holds three `computeRunMetrics` cases captured from the
TypeScript. `tests/test_metrics.py` replays all three and compares each result
whole, exactly — same IEEE arithmetic in the same order, so it either agrees to
the last bit or the port is wrong. `tests/test_scorer.py` feeds the same cases
through the Inspect adapter and expects the same output, which is what says the
two paths are one counter rather than two that happen to agree today.

The fixture's inputs are synthetic, and say so. `RUN_OUTPUTS` in the app is
empty and stays empty until a real extractor has been run, so there is no real
run to capture and nothing in this package invents one.

## Running it

`inspect-ai` is an optional extra. The counting rules and their parity gate run
without it.

```
cd packages/assay
python3 -m pytest -q          # 35 tests
python3 -m ruff check .
python3 -m mypy --strict openferment_assay tests
```

Neither this package nor `packages/core` is installed in the repo's CI path;
both resolve out of the tree via `pythonpath` / `mypy_path` in `pyproject.toml`,
the same way `pnpm check:schema` runs `packages/core`.
