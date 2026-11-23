# H9-08: budget settings of nan or inf are taken as numbers of dollars

**Statement.** `spend._setting` accepts `OPENFERMENT_DAILY_BUDGET_USD` and `OPENFERMENT_ASK_BUDGET_USD`
of `nan` or `inf`: a daily cap of nan or inf holds a 1000 USD call and ready marks its spend row sound
(`$0.00 of the $nan daily cap`), and an ask budget of nan or inf makes Postdoc's loop raise
(ValueError, OverflowError), so `POST /api/ask` answers HTTP 500 and the turn is kept `failed`.

## Contract

- `core/openferment_core/spend.py:57`: a setting is refused when it is one "which is not a number of dollars"
  (`BudgetSettingInvalid`); `spend.py:58-59` refuses a negative one, "a budget cannot be negative".
- `core/openferment_core/llm.py:37-39`: "ONE DAILY CAP. ... a call whose worst case could take the UTC day past
  `OPENFERMENT_DAILY_BUDGET_USD` is refused before it is sent (`BudgetExhausted`)."
- `CLAUDE.md:48` (R): "Every model call goes through `core/openferment_core/llm.py` ... under the day's cap
  `OPENFERMENT_DAILY_BUDGET_USD`".
- `core/openferment_core/api.py:554`: "Every failure below returns a plan with `declined` set rather than an HTTP
  error"; `core/openferment_core/postdoc_agent.py:679`: "Every failure is a plan with `declined` set."

## Command

    bash bughunt/repro/H9-08/run.sh        (from the repository root)

Keyless and spending nothing: `ANTHROPIC_API_KEY` is empty and `ANTHROPIC_BASE_URL` names 127.0.0.1:9159, where
nothing listens. Every defect shown happens before a model call. It makes three fresh databases
(`bh_r_h9_08_caps`, `_askneg`, `_askinf`), runs `caps.py` in process, starts two services (9150 with an ask
budget of -1, 9151 with inf), asks each one question, and drops and stops everything at the end.

## Expected

A daily cap or an ask budget of `nan` or `inf` is refused as `BudgetSettingInvalid` in words, as `-1` is:
no call held against it, ready's spend row `fail`, the ask a 200 plan with `declined` set.

## Observed (both runs)

- Daily cap `-1`: refused in words at the gate and on ready's row. Cap `1.00`: a 1000 USD call refused
  (`BudgetExhausted`).
- Daily cap `nan`: read as `nan`; a 1000 USD call HELD (`reservedUsd` 1000.000128); ready `[ok] spend $0.00 of the
  $nan daily cap`. Cap `inf`: the same, `$inf`.
- Ask budget `-1`: a plan with `declined` set. Ask budget `nan`: `ValueError: cannot convert float NaN to integer`;
  `inf`: `OverflowError: cannot convert float infinity to integer`; zero model calls in each.
- Through the service: `-1` answers HTTP 200 with `declined` set; `inf` answers HTTP 500 `Internal Server Error`,
  the turn kept `status='failed'`, `error='Postdoc failed while answering: OverflowError.'`.

## Likely cause

- `core/openferment_core/spend.py:50-60` (`_setting`): `float(raw)` parses `nan`, `inf` and `1e999`, and the one
  check after it is `value < 0` (line 58), which is false for both nan and inf. No `math.isfinite` test.
- `core/openferment_core/spend.py:162`: `spent + reserved + projected_usd > cap` is never true for a nan cap, nor
  for an infinite one, so every reservation is held.
- `core/openferment_core/ready.py:405`: `"warn" if spent >= cap else "ok"` marks a nan cap `ok`.
- `core/openferment_core/postdoc_agent.py:540`: `int(left / per_token)` with `left` infinite or nan raises; the
  loop's handlers (lines 719-723) catch `Cancelled`, model refusals and outages alone, and `api._answer`
  (api.py:540-543) keeps the turn failed and re-raises, a 500.
