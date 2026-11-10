# H13-03: `pnpm ready` leaves the explain, extract and judge routes unchecked

**Statement.** `pnpm ready`'s `model` row asks the Models API about the plan route's chain and its
`roles` row about the plan and index chains (`llm.ROLES` is `answer` and `index`), so an
`OPENFERMENT_ROUTES` that moves explain, extract or judge to models the key may not use reads `✓` on
both rows, and the live loop meets the refusal at its first extraction or judgement.

**Contract.**
- `docs/runbooks/live-host-install.md:162-163`: "reads, one row a check, whether the service can
  run: `✓` ready, `!` works with a gap worth knowing, `✗` the live loop fails here"; and
  `docs/runbooks/live-host-install.md:170-171`: "`model` and `roles`, the routes' models through the
  Models API".
- `CLAUDE.md:29`: "`pnpm ready` (or `pnpm ready --offline`) says in rows whether the service can
  run: the database, both schemas, pgvector, the embedder, the workers, each registered engine, the
  model routes and the key".
- `core/openferment_core/ready.py:488-489` (`check_roles`): "Each role's models, whether the Models
  API lists them for this key".

Narrower words stand beside these: `docs/api/postdoc.md:214`, `docs/runbooks/live-host-install.md:107`
and `docs/decisions/ADR-008-postdoc-memory-routing.md:443-445` say the model row names the plan
route's models and effort, and the roles row says when the index route holds no other model the key
lists. Read together, the documents give the rows' present reach in three places and promise the
model routes, every family among them, in two (the step 4 summary and CLAUDE.md).

**Command** (from the repository root): `bash bughunt/repro/H13-03/run.sh`

It makes a fresh migrated test database `bh_r_h13_03_ready` (the roles row reads today's spend),
runs `ready_routes.py` from `core/` keyless, and drops the database. The script calls
`ready.check_model(True, client_factory=...)` and `ready.check_roles(True, client_factory=...)`, as
`ready.run` calls them with a key held, their client a stand-in whose Models API and Messages API
answer 404 for `claude-haiku-4-5-20251001` and `claude-opus-4-8` (both priced in `llm.PRICES`) and
accept every other model. No socket leaves loopback and no service starts.

1. Control: `OPENFERMENT_ROUTES` moves plan to `claude-opus-4-8`. The rows read `✗ model` and
   `! roles`, each naming the model, so the stand-in and the rows catch an unlisted model they ask
   about.
2. The case: `OPENFERMENT_ROUTES` moves explain and extract to `claude-haiku-4-5-20251001` and judge
   to `claude-opus-4-8`, plan and index at their defaults. The routing table read back shows the
   moved routes; both rows are read again, and the models they asked about are listed.
3. One `llm.call` on extract and one on judge through the same stand-in, the live loop's calls.

**Expected.** The `model` or `roles` row names the moved routes' models and marks `!` or `✗` for
the two the key cannot use, as it does when the plan route moves.

**Observed** (both runs):
- `✓ model: the key is accepted; claude-opus-5-5 then claude-sonnet-5-5 on the plan route, effort high`
- `✓ roles: answer: claude-opus-5-5 → claude-sonnet-5-5; index: claude-haiku-5-5; every model listed for this key; ...`
- the rows asked the Models API about `claude-haiku-5-5`, `claude-opus-5-5` and `claude-sonnet-5-5`
  alone, and never about `claude-haiku-4-5-20251001` or `claude-opus-4-8`;
- `llm.call` on extract: `ModelUnavailable: claude-haiku-4-5-20251001 is not available to this key (404)`;
  on judge: `ModelUnavailable: claude-opus-4-8 is not available to this key (404)`.

**Likely cause.**
- `core/openferment_core/ready.py:433`: `check_model` walks `llm.chain()`, whose default family is
  plan (`core/openferment_core/llm.py:483`); the same function reads every route of the table at
  `ready.py:423`, for the providers that wait alone.
- `core/openferment_core/ready.py:499`: `check_roles` walks `llm.ROLES`, which is
  `("answer", "index")` (`core/openferment_core/llm.py:139`), and `ROLE_FAMILIES`
  (`core/openferment_core/llm.py:152`) reads answer as plan; explain, extract and judge stand in no
  role the row reads.

A fix walks `llm.routes()` (every family, `llm.FAMILIES`) in the roles row, or in the model row,
and names each unlisted model with the families it serves.
