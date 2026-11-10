# H9-07: `pnpm ready --offline` says Ready with a routing table that cannot route

**Statement.** Under `--offline` (and `--no-network`) `ready` skips the model and roles rows whole, so an
`OPENFERMENT_ROUTES` table that cannot route (no JSON, an unknown family, an unknown provider, an effort outside the
enum, an empty model list) leaves the report at "Ready." with exit 0, though the table is read with no network and no
key and `llm.routes()` raises `RoutesInvalid` on it.

**Contract.**

- `CLAUDE.md:29`: "`pnpm ready` (or `pnpm ready --offline`) says in rows whether the service can run: the database,
  both schemas, pgvector, the embedder, the workers, each registered engine, the model routes and the key".
- `docs/decisions/ADR-008-postdoc-memory-routing.md:81-83`: "`OPENFERMENT_ROUTES` (a JSON object of family to
  `{"models", "effort"}`) lays a route over a family, refused in words when it cannot route (`RoutesInvalid`, and
  `pnpm ready` fails on it)".

**Command.** `bash bughunt/repro/H9-07/run.sh` from the repository root. It makes a fresh database
(`bh_r_h9_07_ready`) and a private copy of the fetched data, runs
`python -m openferment_core.ready --offline --no-workers` (what `pnpm ready --offline` runs, without the workers' cold
start) once for a valid table and once for each of five tables that cannot route, then asks `llm.routes()` and
`ready.check_model(have_key=False)` about the same tables in one process with no network. Keyless: no key in the
environment, `ANTHROPIC_BASE_URL` on a loopback port nothing listens on, no service started. It drops the database and
the data copy on the way out.

**Expected.** For each table that cannot route, a failing (✗) model row in the `RoutesInvalid` words, and exit 1.

**Observed (both runs).** For all five tables, `llm.routes()` raises `RoutesInvalid` (for example
"OPENFERMENT_ROUTES.plan.models is a list of model specs") and `check_model(False)` answers
"✗ ... so no call can be routed" with no network, while `ready --offline` prints `· model --no-network`,
`· roles --no-network`, `Ready.` and exits 0, the same report the valid table gives.

**Likely cause** (high confidence).

- `core/openferment_core/ready.py:641` sets `no_network = no_network or offline`, and
  `core/openferment_core/ready.py:658-661` puts `check_model` and `check_roles` under that switch whole, so the
  routes check never runs offline.
- The routes check (`llm.routes()` and its `RoutesInvalid`) lives only inside `check_model`, at
  `core/openferment_core/ready.py:416-422`, ahead of the key and the network; it needs neither.
- `core/tests/test_ready.py:158-161` holds the check in `check_model` alone, and
  `core/tests/test_ready.py:475-484` pins the offline skip of the model row with the default table, so no test runs
  an offline report over a table that cannot route.

Plain `pnpm ready` (no flag) reaches `check_model`, so ADR-008's words hold for it; CLAUDE.md:29 names the
`--offline` form, and the defect sits in that form and in `--no-network`. `scripts/prove.py:609` runs `ready --offline` as proof step 1,
so the proof's "ready green" passes over the same tables.

Severity S3: a host with a broken `OPENFERMENT_ROUTES` reads "Ready." from the offline report, and the plain
`pnpm ready` shows the failing row.
