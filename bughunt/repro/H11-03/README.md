# H11-03: install.sh takes a shell's OPENFERMENT_DATABASE_URL as core/.env's

**Statement.** Run from a shell that exports `OPENFERMENT_DATABASE_URL`, over the core/.env of the runbook's step 1
(no database line), `scripts/host/install.sh` writes no database line into core/.env, and the server's LaunchDaemon
starts the service with `PATH`, `HOME` and `PYTHONUNBUFFERED` alone, so the installed service reaches no database
(`GET /api/projects` 503) while install.sh's health wait and `pnpm ready`'s data and service rows all pass.

**Contract.**
- `scripts/host/lib.sh:122-124`: "a database named `openferment`, and its address in core/.env. Makes what is
  missing and says what it made."
- `docs/runbooks/live-host-install.md:137-139`: "when no database is named in `core/.env`, checks for pgvector,
  makes the database `openferment` and names it there".
- `scripts/host/install.sh:8-10`: "makes the database `openferment` on Homebrew's PostgreSQL and names it in
  core/.env when none is named there".
- `core/openferment_core/db/engine.py:56`: "on the live host scripts/host/install.sh writes it".

**Command.** From the repository root: `bash bughunt/repro/H11-03/run.sh`

It runs install.sh unchanged in a detached worktree of 2047f5a, over stand-ins for macOS and Homebrew. The stand-in
`launchctl bootstrap` starts the server job as launchd does: the installed plist's `ProgramArguments` in its
`WorkingDirectory`, with its `EnvironmentVariables` as the whole environment (plus `ANTHROPIC_BASE_URL` on a closed
loopback port as a keyless guard). The service is the worktree's code on the repository's interpreter, on
127.0.0.1:9370, reading the worktree's core/.env. The shell exports the address of a fresh, migrated test database
(`bh_r_h11_03_live`), so `pnpm ready`'s rows, run from that shell as `run_ready` runs them, see a sound database.
A control calls `ensure_database` over the same file with nothing exported.

**Expected.** With no database line in core/.env, install.sh names a database there (the live address, or the
value the shell exports), so the service the LaunchDaemon starts reads its database from core/.env and
`GET /api/projects` answers 200.

**Observed** (both runs).
- Control, nothing exported: "Database openferment is ready, and its address is in core/.env."; core/.env then
  names `postgresql://owner@127.0.0.1:5432/openferment`.
- Exported: install.sh exits 0 and says "OPENFERMENT_DATABASE_URL names the database."; its `wait_for_health`
  prints `{"ok":true,...}`; core/.env's database, as python-dotenv reads it, is `None`; the server job's
  `EnvironmentVariables` are `HOME,PATH,PYTHONUNBUFFERED`.
- `pnpm ready`'s rows from the install shell: `ok data: 0 projects, 0 review decisions, at revision 0010`,
  `ok service: answers on 127.0.0.1:9370`.
- The job's service: `GET /api/health` 200; `GET /api/projects` 503 "OPENFERMENT_DATABASE_URL is not set. Put it in
  core/.env: ... on the live host scripts/host/install.sh writes it".
- Also: with the example's development address exported over the same file, the refusal tells the person to
  "Delete that line from core/.env and run this again", and core/.env holds no such line (0 database lines).

**Likely cause.**
- `scripts/host/lib.sh:147-153`: `named="$(env_setting OPENFERMENT_DATABASE_URL)"`, then on any non-empty value
  `echo "OPENFERMENT_DATABASE_URL names the database."; return`, before anything is written to core/.env.
- `scripts/host/lib.sh:106-110`: `env_setting` answers from the environment first (`${!name}`) and reads the file
  only when the environment has no value, as its own comment (lib.sh:94-105) says; ensure_database's question is
  whether core/.env names a database, and the environment answers it.
- `scripts/host/launchd.py:71`: the jobs' environment is `PATH`, `HOME` and `PYTHONUNBUFFERED`, so the service
  reads its database from core/.env alone (`core/openferment_core/api.py:178`, `load_dotenv(..., override=False)`).

Confidence: high. Severity S3: the install path breaks only when the shell exports the setting; unsetting it, or
writing the line in core/.env by hand, works around it.
