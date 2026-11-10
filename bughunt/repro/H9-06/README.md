# H9-06: a routing table that cannot route makes POST /api/ask and the extraction route answer 500

**Statement.** With `OPENFERMENT_ROUTES` set to a table `llm.routes()` refuses (here
`{"plan": {"models": []}}`), `POST /api/ask` and `POST /api/intake/{id}/extract` each answer
`500 Internal Server Error`, and the `RoutesInvalid` words reach the service log alone.

**Contract.**

- `core/openferment_core/api.py:554-556`, the docstring of `POST /api/ask`: "Every failure below
  returns a plan with `declined` set rather than an HTTP error, because a declined plan is a thing
  the UI already knows how to render honestly and a 500 is a thing it can only apologise for. The
  one exception is the service being unreachable".
- `docs/decisions/ADR-008-postdoc-memory-routing.md:81-83` (6.3): "`OPENFERMENT_ROUTES` (a JSON
  object of family to `{"models", "effort"}`) lays a route over a family, refused in words when it
  cannot route (`RoutesInvalid`, and `pnpm ready` fails on it)".
- `core/openferment_core/llm.py:259`, `routes()`: "Raises RoutesInvalid in words."

**Command** (from the repository root):

    bash bughunt/repro/H9-06/run.sh

Two services of the head on fresh databases: port 10040 with the table `{"plan": {"models": []}}`,
port 10041 with no table as the control. Both are keyless, and `ANTHROPIC_BASE_URL` names
127.0.0.1:10049, where nothing listens, so no model request leaves the machine and nothing is spent.
The script asks one question on each, pastes one short document on 10040 and asks for its
extraction, reads the service log, then stops both services and drops both databases.

**Expected.** `POST /api/ask` answers 200 with a plan whose `declined` holds the `RoutesInvalid`
words (`OPENFERMENT_ROUTES.plan.models is a list of model specs`), as the control's keyless ask
answers 200 with `declined` set ("ANTHROPIC_API_KEY is not set ..."). The extraction route refuses
in words, a 503 with its detail as it answers for no key.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

- `POST /api/ask` on 10040: `[500] Internal Server Error`.
- `POST /api/intake/<doc>/extract` on 10040: `[500] Internal Server Error`.
- control `POST /api/ask` on 10041: `[200]`, `declined`: "ANTHROPIC_API_KEY is not set. Put it in
  core/.env (gitignored) and restart the service."
- the log on 10040 holds two unhandled exceptions, each ending in
  `openferment_core.llm.RoutesInvalid: OPENFERMENT_ROUTES.plan.models is a list of model specs`,
  raised through `postdoc_agent.py:709` and `extract.py:328`.
- `GET /api/health` answers 200 under the same table, so nothing at start-up says the table is bad.

**Likely cause.**

- `core/openferment_core/postdoc_agent.py:709-710`: `llm.chain("plan")` and `llm.routes()` run
  outside the `try` that turns `ModelRefused` and `ModelUnavailable` into a declined plan (its
  neighbour `spend.ask_budget()` at :701-704 turns `BudgetSettingInvalid` into one). The
  `RoutesInvalid` they raise reaches `api.py:_answer` (:537-543), which keeps the turn failed and
  re-raises, and FastAPI answers 500.
- `core/openferment_core/extract.py:328`: `call_model` calls `llm.call`, whose first act
  (`llm.py:804`, `route = routes()[family]`) raises `RoutesInvalid`, a `ValueError` that neither
  `call_model`'s handlers nor `api.py:intake_extract` (:2017-2034) map to a status in words.

**Severity.** S3: a misconfigured setting on the host, with a workaround. `pnpm ready`, run with the
network, fails its `model` row in the `RoutesInvalid` words (`ready.py:419-421`), and fixing
`OPENFERMENT_ROUTES` restores both routes. `pnpm ready --offline` skips that row and says "Ready."
under the same table (`bughunt/notes/H9/evidence/routes/empty-models/ready.txt`), so the offline
check leaves the fault unsaid.
