# H9-03: the spend gate's tests stub an exception the real extraction never raises

**Statement.** `test_writes.py::test_an_extraction_the_budget_refuses_becomes_a_spend_proposal` and
`test_proposals_review.py::test_a_spend_proposals_why_holds_no_number` replace `extract.extract_paper` with a
function that raises `llm.BudgetExhausted`. The real `extract_paper` wraps that exception in `ExtractUnavailable`,
so both tests pass while a budget refusal on the real path keeps no spend proposal (H9-02).

Kind: hollow test. Severity: S3. The tests are the gap. The broken gate they miss is H9-02 (S2).

## The contract

- `core/tests/test_writes.py:360`: the test's own name, "an extraction the budget refuses becomes a spend
  proposal".
- `core/openferment_core/tools/gates.py:13-15`: "The spend gate is the one a tool reaches at run time: an
  extraction is free until the budget refuses it, and then it is proposed for when the budget allows."
- `core/openferment_core/tools/writes.py:27-28`: "The spend gate is reached at run time, when the budget refuses an
  extraction."
- `docs/TOOLS.md:856`: gate `spend`, "spend past the ask or the daily budget", covers `intake extract`, "extract it
  when the budget allows".

A test that holds this contract has to fail when the budget refuses an extraction and no proposal is kept.

## The command

```
bash bughunt/repro/H9-03/run.sh
```

This needs no key, no service and no network. `run.sh` makes a scratch worktree of 2047f5a and a fresh
configured database `bh_r_h9_03_cfg`. Each pytest session makes and drops its own `bh_r_h9_03_t_*` test database.
The script copies `test_zz_h9_03_probe.py` into the worktree's `core/tests`. Each pytest session runs four tests:

- T1 and T2: the suite's two spend-gate tests, unchanged.
- P1: the real `extract_paper` on a held document, with `OPENFERMENT_DAILY_BUDGET_USD=0.001`. `llm.call`'s own
  reservation (`llm._reserve` → `spend.reserve`) refuses the call. P1 asks whether the function raises
  `llm.BudgetExhausted`, the exception T1's and T2's stub raises. A stand-in client sits where the Anthropic
  client would and fails the probe if any request is about to be sent.
- P2: T1's assertions run through `intake_write extract` under the same cap. It expects `state: proposed`,
  `gate: spend` and one kept proposal whose why holds no number.

The script runs these four tests twice:

1. On the tree as it is.
2. On a control tree: the same tree with one change. Two lines in `extract.call_model` let `llm.BudgetExhausted`
   through, as the stub assumes.

Then it removes the worktree and drops every `bh_r_h9_03_*` database. `run1.log` and `run2.log` hold two runs,
each from fresh databases.

## Expected

T1 and T2 fail on a tree whose real extraction path keeps no spend proposal when the daily cap refuses. They
should pass only where a budget refusal through `extract_paper` becomes a proposal, which is what P2 checks.

## Observed (both runs)

| tree | T1 | T2 | P1 | P2 |
|---|---|---|---|---|
| 2047f5a as it is | passed | passed | failed | failed |
| control (BudgetExhausted let through) | passed | passed | passed | passed |

- On 2047f5a, P1 shows `extract_paper` raises `ExtractUnavailable` (`__cause__` BudgetExhausted) with the words
  "Today's model spend is $0.00 of the $0.00 daily cap, and this call could pass it. ...".
- On 2047f5a, P2 shows `intake_write extract` answers error "intake_write could not extract X1: Today's model
  spend is ..." with summary `{}` and 0 proposals kept.
- On the control tree, P2 answers `state: proposed`, `gate: spend`, with 1 proposal kept.
- T1 and T2 pass on both trees, so their result is the same whether or not the gate works on the real path.

`RESULT: DEFECT` in both runs.

## Likely cause

- `core/tests/test_writes.py:363-366` and `core/tests/test_proposals_review.py:74-77` monkeypatch
  `extract.extract_paper` with `broke`, which raises `llm.BudgetExhausted` itself.
- In the real function, `core/openferment_core/extract.py:340-342` (`call_model`) catches `llm.ModelUnavailable`
  and raises `ExtractUnavailable`. `llm.BudgetExhausted` is a subclass of it (`core/openferment_core/llm.py:438`,
  `class BudgetExhausted(ModelUnavailable)`), so the stubbed exception never leaves `extract_paper`.
- That makes `except llm.BudgetExhausted` at `core/openferment_core/tools/writes.py:1171` unreachable from the
  real path.

The fix is small: drive the refusal from where it arises (a tiny `OPENFERMENT_DAILY_BUDGET_USD` with a client
that never sends, as P1 and P2 do, or a stub on `llm.call`), and fix H9-02 so the tests pass again.
