# H9-05: the ask cap does not hold

**Statement.** Each round's ceiling (`postdoc_agent._turn_tokens`) is sized to spend every dollar the question's budget has left after the conversation is read, so the `MIN_TOKENS` answer the loop holds back is paid for past `OPENFERMENT_ASK_BUDGET_USD`: on Opus at the default 0.75 USD a question whose turns write their whole room spends 0.91 USD, at 2.00 USD it spends 2.16 USD, and at 0 USD it still asks for tools and makes two model calls costing 0.52 USD.

## Contract

- `docs/decisions/ADR-008-postdoc-memory-routing.md:99-102` (6.3): "The ask budget keeps back the final turn's worst case before another round is asked (`postdoc_agent._final_turn_usd`: the conversation so far read as input, and every output token the turn allows): the loop stops asking for tools when what it spent and what the answer could cost reach the question's budget, so the answer is paid for within it."
- `core/openferment_core/postdoc_agent.py:544-546`, `_out_of_budget`: "The cost it may run to keeps back what the final turn could cost (`final_usd`), so the answer is always paid for within the question's budget."
- `docs/decisions/ADR-008-postdoc-memory-routing.md:150-151` (Implementation 9): "The ask's cost cap (`OPENFERMENT_ASK_BUDGET_USD`) bounds what one question spends, and its reservation for the final turn stands as 6.3 built it."

## Command

```
bash bughunt/repro/H9-05/run.sh
```

From the repository root. It makes a fresh test database `bh_r_h9_05_ask` (migrated to head) and runs `ask_cap.py` with the repository's Python, keyless, with the default routing table (`OPENFERMENT_ROUTES` empty: `plan` on `claude-opus-5-5` at effort high). The script makes a project, then asks one question through `postdoc_agent.ask` at the ask budgets 0, 0.75 and 2.00 USD. A stand-in `converse` answers each turn: a round calls `study_read`, and the answer after the stop is an empty plan. Each turn is charged its request read as input at four characters a token, plus every output token its `max_tokens` allows; the script checks that each charge sits at or under the code's own worst case for that turn (`llm.worst_case_usd`, two characters a token). Every socket to a host beyond loopback is refused inside the process, and no model client is built. No service runs. The database is dropped on exit, and the script checks that no file under `core/`, `src/`, `scripts/` or `examples/` was written.

## Expected

At every budget the question's total cost stays at or under `OPENFERMENT_ASK_BUDGET_USD`, since every turn costs at most the worst case the loop reasons with. At a zero budget, what was spent and what the answer could cost already reach the budget before round one, so the loop asks for no tools and makes at most the one answer turn.

## Observed (both runs)

| ask budget | turns (tool_choice, max_tokens, USD) | total | stopped |
|---|---|---|---|
| 0 | (auto, 8000, 0.2614), (none, 8000, 0.2619) | 0.5233 USD | cost |
| 0.75 | (auto, 27360, 0.6486), (none, 8000, 0.2619) | 0.9105 USD | cost |
| 2.00 | (auto, 32000, 0.7414), (auto, 32000, 0.7418), (auto, 15622, 0.4146), (none, 8000, 0.2627) | 2.1605 USD | cost |

Every turn's charge is at or under its worst case. At 0.75 USD, round one's worst case is 0.7500 USD, the whole budget: `_turn_tokens` gave it 27,360 tokens, all the budget left after its request is read, and the answer turn's 0.26 USD lands on top. Each budget ends past its cap, each stopped `cost`.

## Likely cause

- `core/openferment_core/postdoc_agent.py:537-540`: `left = budget_usd - run.spent.costUsd - read` gives a round every dollar left and keeps nothing back for `_final_turn_usd`, so a round that writes its whole room spends the reservation the answer needs.
- `core/openferment_core/postdoc_agent.py:597-607`: `_out_of_budget` is asked only after the round has spent, and the answer turn then runs at `MIN_TOKENS` whatever is left (`_turn_tokens` floors at `MIN_TOKENS`, :540).
- `core/openferment_core/postdoc_agent.py:577-584`: round one runs at `MIN_TOKENS` with `tool_choice="auto"` and no budget check before it, so a zero budget still asks for tools and then pays for an answer.
- Implementation 9 (`ADR-008-postdoc-memory-routing.md:156-159`) records the sizing that breaks 6.3's promise: "A turn now writes as much as the question's budget has left to pay for … and the loop holds back a `MIN_TOKENS` answer before it asks another round."

The suite cannot see it: `core/tests/test_postdoc_agent.py:174` stubs `_final_turn_usd` and charges its stand-in turns a fraction of a cent, and `test_postdoc_agent.py:194` asserts the uncapped sizing (a ceiling near 20,000 tokens at a budget equal to that turn's whole worst case).

Bound: the overshoot is at most one answer turn, its conversation read as input plus `MIN_TOKENS` of output (about 0.26 to 0.36 USD on Opus here). The day's cap (`spend.reserve`, `core/openferment_core/spend.py:174`) still holds each real call's worst case before it is sent, and a person can lower the ask budget to keep a question under a figure.
