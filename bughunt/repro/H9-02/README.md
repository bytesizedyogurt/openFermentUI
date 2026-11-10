# H9-02: the spend gate never proposes

**Statement.** When the day's cap refuses an extraction asked through `intake_write` at the tool door (`POST /api/tools/intake_write`, the same `tools.run` path the MCP server and Postdoc's loop take), the call answers the error "intake_write could not extract ...: Today's model spend is ... daily cap ..." and keeps no proposal, so the spend gate's card and button never reach Home.

## Contract

- `core/openferment_core/tools/gates.py:13-15`: "The spend gate is the one a tool reaches at run time: an extraction is free until the budget refuses it, and then it is proposed for when the budget allows."
- `core/openferment_core/tools/gates.py:43-45`: `Gate("spend", "spend past the ask or the daily budget", (("intake", "extract"),), "extract it when the budget allows", None, True)`
- `core/openferment_core/tools/writes.py:27-28`: "The spend gate is reached at run time, when the budget refuses an extraction."
- `docs/TOOLS.md:856`: "| `spend` | spend past the ask or the daily budget | `intake extract` | extract it when the budget allows |"

## Command

```
bash bughunt/repro/H9-02/run.sh
```

The script makes the database `bh_r_h9_02_gate` fresh, starts a loopback stand-in for the model API on 127.0.0.1:9651 (it records every request and answers each with an error, so nothing leaves the machine and nothing is spent), and starts the service on 127.0.0.1:9650 with `OPENFERMENT_DAILY_BUDGET_USD=0.001`, a dummy key and `ANTHROPIC_BASE_URL` naming the stand-in. It makes a project, pastes one document, then calls `intake_write` `extract` on it twice: once with `?by=Alice Person`, once with `X-OpenFerment-Assistant: bughunt-client/0.1`. It reads `GET /api/proposals`, counts the requests the stand-in saw, and drops everything it made on exit.

## Expected

Each call answers `summary.state` "proposed", `gate` "spend", a `proposalId` and no error (`_propose`, `tools/writes.py:261-283`); `GET /api/proposals` lists the spend proposal, which Home shows with the button "extract it when the budget allows"; no model request is sent.

## Observed

Both calls answer `summary` {} with `auditIds` [] and the error "intake_write could not extract <doc>: Today's model spend is $0.00 of the $0.00 daily cap, and this call could pass it. Raise OPENFERMENT_DAILY_BUDGET_USD in core/.env, or wait for the next UTC day." `GET /api/proposals` answers []. The stand-in saw no request, so the cap refused the call before it was sent, the case the gate is for. Both runs (`run1.log`, `run2.log`) print `RESULT: DEFECT`.

## Likely cause

`core/openferment_core/llm.py:438` makes `BudgetExhausted` a subclass of `ModelUnavailable`. `extract.call_model` catches `llm.ModelUnavailable` at `core/openferment_core/extract.py:340` and raises `ExtractUnavailable` at `:342`, so the budget's refusal leaves `extract_paper` as an `ExtractUnavailable`. `_intake_extract`'s `except llm.BudgetExhausted` at `core/openferment_core/tools/writes.py:1171` is never reached, and the next clause answers the error at `:1178`. The two tests that hold the gate (`core/tests/test_writes.py:360`, `core/tests/test_proposals_review.py:73`) stub `extract_paper` to raise `BudgetExhausted` itself, so they pass over the wrapping in `call_model`.

A small fix: in `call_model`, re-raise `llm.BudgetExhausted` as it is ahead of the `ModelUnavailable` clause (or let `_intake_extract` look at the `ExtractUnavailable`'s `__cause__`), with a test that reaches the cap through `llm.call`.
