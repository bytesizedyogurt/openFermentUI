# H9-10: Postdoc's loop asks at most two models of the plan route

**Statement.** With the plan route set to `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`
(`OPENFERMENT_ROUTES`, or `OPENFERMENT_MODEL` with a two-model `OPENFERMENT_FALLBACK_MODEL`) and the
first two unavailable, a Postdoc question declines after sonnet and haiku is never asked, while
`GET /api/health` names `claude-sonnet-5-5, claude-haiku-5-5` as the route's fallbacks.

**Contract.**
- `docs/api/postdoc.md:193-195`: "`llm.ROUTES` ... gives each family its default route: the models
  tried in order, each after the one before it declines or is unavailable"; the table at line 199
  names the `plan` family's calls as "Postdoc's loop".
- `docs/api/postdoc.md:207-208`: "`OPENFERMENT_FALLBACK_MODEL` (several models, comma-separated, tried
  in order) over the models of `plan`, `explain` and `extract`".
- `core/openferment_core/llm.py:12-14`: "OPENFERMENT_MODEL with OPENFERMENT_FALLBACK_MODEL (a
  comma-separated list, tried in order) is the chain of the answering families, plan, explain and extract".
- `core/openferment_core/api.py:474` and `:485-486` (`GET /api/health`): "The models are the plan
  route's, the one Postdoc's loop answers on" and `fallbackModel` is "The models the route moves to, in
  order, when its first declines or is unavailable".

**Command.** `bash bughunt/repro/H9-10/run.sh` from the repository root. It makes a fresh database
`bh_r_h9_10_loop`, reads `GET /api/health` in process, and asks `postdoc_agent.ask` twice with a
stand-in `converse` (the hook `core/tests/test_postdoc_agent.py` uses): a control with opus alone
unavailable, then the case with opus and sonnet unavailable. The model API's address is a closed
loopback port; no model is asked and nothing is spent. It drops the database when done.

**Expected.** The loop asks opus, then sonnet, then haiku, and haiku's plan is the answer, its trace
ending "Answered: ...", as the control's does when sonnet answers.

**Observed (both runs).** `GET /api/health` gives `fallbackModel` `'claude-sonnet-5-5, claude-haiku-5-5'`;
the loop asked `['claude-opus-5-5', 'claude-sonnet-5-5']`, declined with "claude-sonnet-5-5 answered
529: overloaded", and its last trace step reads "No answer: claude-sonnet-5-5 answered 529:
overloaded". The control (opus alone unavailable) restarts on sonnet and answers, so the stand-in and
the restart path work as the test suite's do.

**Likely cause.** `core/openferment_core/postdoc_agent.py:714` `for i, model in enumerate(models[:2]):`
and `:728` `if isinstance(e, llm.BudgetExhausted) or i + 1 >= min(len(models), 2): break` cap the loop
at one restart; the module docstring at `postdoc_agent.py:28` says the loop "restarts the question once
on the next model in the answer chain", which the public routing contract and the health route do not
carry. `llm.call` (`llm.py:859`, `for i, named in enumerate(models):`) walks every model of a route, the
`explain` and `extract` families' calls among them. The default routes hold two models each, so the
defect shows only on a configured plan route of three or more.

Severity S3 (an edge case with a workaround: keep the plan route to two models, the wanted fallback
second). Kind: Inconsistency. Fix size: small (walk `models` whole, or say the cap in
`docs/api/postdoc.md`, `llm.py` and the health field's words).
