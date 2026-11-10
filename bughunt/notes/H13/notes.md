# H13: documents and commands

Commit 2047f5a, a detached worktree of my own (removed at the end), its own `core/.venv` and
`node_modules`. Keyless throughout (`bh_env`); every database `bh_h13_*`, dropped; ports 8930-8933.
Logs of the main runs are in `logs/`, scripts in `scripts/`.

## Generated files

`pnpm gen:api`, `gen:tools`, `gen:components` and the three fixture exports test:core runs
(`export:unit-fixtures`, `export:competence-fixtures`, `export:lock-fixtures`) were run in the clean
worktree: `git status` empty afterwards, so `docs/api/openapi.json`, `src/api/types.gen.ts`,
`docs/TOOLS.md` and `COMPONENTS.md` are what the tree writes (the fixtures are gitignored). The
`--check` stages and `check:tools`/`check:licences` held again with the mirror engine installed.
`pnpm lit:report` (the demo, offline) reproduces the demo's numbers and drops 37 hand-written
lines of `docs/reports/literature-retrieval.md` (H13-02).

## Verify's stages, run one by one in the worktree

check:secrets, gen:api --check, gen:components --check, gen:tools --check, check:plan, check:tools,
check:licences, check:guild, check:state, check:figures, typecheck, test:reconcile, build (18 s,
`dist/` identical to the tree's): all pass. Not run: test:core/test:sim/test:lit whole (the hunt's
resource rule), smoke (kernel-chosen port and an `openferment_smoke_*` database). Targeted pytest:
test_guidance, test_host, test_ready, test_prove_examples, test_licences, test_openapi,
test_check_tools: 172 passed.

## Command ledger (CLAUDE.md, README.md, docs/BASE.md, the live-host runbook)

ran-ok: pnpm install --frozen-lockfile; uv sync --frozen --all-extras (Python 3.13.17); db:migrate
(bh db); db:reset bh_h13_reset; db:reset openferment (refused before any connection, pointed at a dead
port); migrations revision; ready --offline; ready (fixtures, port 8930); ready --probe (keyless:
skip); ready --bogus (usage); gen:*; build; prove --steps 3,8 (40 s) and prove --keep --steps 2 (both
through scripts/prove_bh.py, which moves the port to 8931/8933 and the database name to bh_h13_proof_*
in memory); eval seed, seed --suite ethanol (14), run, run --only --tag, summary [--rows];
eval run --judge (refused: needs --live, exit 2); eval judge (stops exit 1 keyless, as postdoc.md
says); lit:graph --project --dry-run; lit:graph without --by (usage, exit 2); lit:report --project
(refuses an empty project in words); lit:report (demo); geneos:fetch over the cached model files;
conform mirror / kinetics --inputs / biosteam (through scripts/conform_bh.py, scratch database
bh_h13_conform_*): every check holds; write_placeholder_inputs; db:import-alpha1 (committed file, and
--data with a stand-in that is refused in words); engines-local.sh; the runbook's .env sed, chmod and
grep; bash -n on every shell script; the record-reader command; the mirror install, pytest and conform
lines; uv run keeps an editable engine installed.
ran-fails: README "Run it" on a keyless clone (H13-01); the mirror README's line 10 read from the
directory line 9 names (H13-05).
dry-run: pnpm db:up (docker; 5432 is the hunt's server; compose.yaml read); prototype:up (ports 8000
and 4173; its parts run: session-start's database step, the service with no database); session-start
whole (its database step run as the script holds it); pnpm dev (port 5173; vite.config.ts read);
install.sh, deploy.sh, nightly.sh, brew, pmset, launchctl, tailscale (macOS, sudo); backup_database
(read; its pg_dump custom-format dump and the runbook's pg_restore shape run on a bh_ copy);
git push of the tags (the two commits exist locally).
not-run: verify whole, test:core/sim/lit/slow/live whole (resource rule), smoke (port and database
name), full prove steps 4-7, 9, 10 (CPU share; the baseline ran them), conform train --project (needs a
saved train; prove step 10 makes one), pnpm ready's network rows and every live-model command.

## The two example READMEs, as a stranger

Mirror: the install line, the test line and the conform line all work from the directories they
need; the page puts the reader in the package's directory for line 9 and then says `cd core` (fails
there), and names no database setup or service start (H13-05). Its run appears in `GET /api/runs`,
`GET /api/engines` lists it, `pnpm ready` reads its verdict; the run id recomputes from engines.md's
recipe. Record-reader: `uv run examples/agents/record-reader/record_reader.py --project ... --service
...` exits 0 against my service and against prove --keep's (`--project proof`); the audit row names
`example-agent/0.1`, door http. TOOLS.md's MCP recipes (scripts/mcp_doors.py): nameless client marked
`an assistant over MCP` on both doors, source words per door, four bad origins refused in words, no
project refused in words, audit filters by action/target/who.

## What held

Every backticked path in the scoped pages resolves (scripts/check_paths.py); every route they name is
an operation (scripts/check_routes.py), and all 133 carry `x-openferment-scope`; every `pnpm` script
and `python -m` module named exists; BASE.md's and CLAUDE.md's versions equal core/uv.lock, and so does
every Python row of THIRD_PARTY.md; llm.ROUTES, the plan ceilings, KIT_ROOM, JUDGE_TOKENS and the
budgets equal CLAUDE.md and postdoc.md; verify's sixteen stages equal ADR-011 Implementation 8;
workers.md's op headings equal the worker HANDLERS tables; the launchd labels equal scripts/host.

## Findings

H13-01 S2 keyless Run it has no database; H13-02 S3 lit:report erases the report's hand-written part;
H13-03 S3 ready's model rows check plan and index alone; H13-04 S4 eval's tracebacks for a missing
project; H13-05 S4 the example READMEs' stuck points; H13-06 S4 verify.yml names smoke.mjs.
