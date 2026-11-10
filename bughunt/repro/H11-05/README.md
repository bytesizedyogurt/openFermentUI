# H11-05: session-start.sh glues its settings onto a core/.env last line that has no newline

**Statement.** `scripts/session-start.sh` appends `OPENFERMENT_DATABASE_URL` (and, when the session names
one, `OPENFERMENT_WORKSPACE_ID`) to `core/.env` with `printf '...\n' >>` and no leading newline, so over a
`core/.env` whose last line has no newline at its end the setting joins that line: a key line saved that way
reads as the key with the setting stuck to its end, and the setting itself reads as unset.

**Contract.**
- `scripts/session-start.sh:18-20`: "4. the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and
  core/.env names none, the development address (compose.yaml's) joins core/.env". After the run, core/.env
  still names none to every reader (python-dotenv, the service's `load_dotenv`).
- `scripts/session-start.sh:44-46`: the workspace id "joins core/.env when the file lacks it, so a service
  started from the file sends it too". After the run the service reads no workspace id.
- `scripts/session-start.sh:6`: "Idempotent: run it at the start of every session, on a fresh clone or a
  warm one." A second run over the glued file appends the database line again.
- The tree's own standard for the same append: `scripts/host/lib.sh:162-163`, "On a line of its own, whether
  or not the file's last line ends in one." with `printf '\nOPENFERMENT_DATABASE_URL=...\n'`, held by
  `core/tests/test_host.py:243-257` over `"# a placeholder\nANTHROPIC_API_KEY=sk-ant-..."` ("no newline at
  the end"), asserting the key line stays `ANTHROPIC_API_KEY=sk-ant-...`. The one test line naming
  `session-start.sh` (`core/tests/test_host.py:452`) checks the order of its sync and engines steps alone.

**Command.** From the repository root: `bash bughunt/repro/H11-05/run.sh`

It adds a detached worktree of 2047f5a under `$BH_WORK/H11-05/wt` and runs that worktree's
`scripts/session-start.sh` over the worktree's own `core/.env` (the repository's own `core/.env` is never read
or written). Stand-ins answer for `pnpm` and `uv` (each records its call and exits 0); `pg_isready` is the real
`/usr/bin/pg_isready`, finding the test server on 127.0.0.1, where the run makes the fresh database
`bh_r_h11_05_pg` to confirm it answers. The key line holds the example's placeholder text `sk-ant-...` alone.
Each case's file is printed with `cat -A`, then read by python-dotenv's `dotenv_values` and by the service's
loader in the worktree's code (`load_dotenv(..., override=False)` as `core/openferment_core/api.py:178` calls
it, then `db.engine.database_url()` and the key read of `core/openferment_core/llm.py:716`). Cases: A, the key
line ends in a newline (control); B, no newline at its end; B2, session-start run again over B's file; C, as B
with `OPENFERMENT_WORKSPACE_ID=wrkspc_h11_placeholder` in the session. The worktree, the stand-ins and the
database are removed at exit. Keyless; nothing reaches the network.

**Expected.** In every case the added setting lands on a line of its own: the key reads as `sk-ant-...`, the
database as `postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev`, and in case C the workspace
as `wrkspc_h11_placeholder`.

**Observed (run1.log and run2.log, identical).**
- Case A (control): `core/.env` ends `ANTHROPIC_API_KEY=sk-ant-...$` then
  `OPENFERMENT_DATABASE_URL=postgresql://...openferment_dev$`; the key reads `'sk-ant-...'` and
  `database_url()` answers `postgresql+asyncpg://openferment:***@127.0.0.1:5432/openferment_dev`.
- Case B: session-start says "OPENFERMENT_DATABASE_URL added to core/.env (the development address)", exit 0,
  and the file's last line is
  `ANTHROPIC_API_KEY=sk-ant-...OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev$`.
  `dotenv_values` and the service's loader both read the key as
  `'sk-ant-...OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev'`
  and the database as unset; `database_url()` raises `DatabaseUnavailable: OPENFERMENT_DATABASE_URL is not set`.
- Case B2: the second run appends the database line again, now on a line of its own; the database then reads
  as the development address, and the key stays glued.
- Case C: the workspace line glues onto the key line
  (`ANTHROPIC_API_KEY=sk-ant-...OPENFERMENT_WORKSPACE_ID=wrkspc_h11_placeholder$`); the workspace reads as
  unset and the key carries its text; the database line that follows lands on its own line.
- `RESULT: DEFECT` both times.

**Likely cause.** `scripts/session-start.sh:48`
(`printf 'OPENFERMENT_WORKSPACE_ID=%s\n' ... >> core/.env`) and `scripts/session-start.sh:63`
(`printf 'OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev\n' >> core/.env`)
append with no leading newline; `scripts/host/lib.sh:163` shows the form that holds (`printf '\n...\n'`).
The guards at `session-start.sh:47` and `:62` (`grep -q '^NAME='`) then miss the glued setting, so a second
run appends the database line again.

**Severity.** S3. The condition is an edge case: session-start writes its own key line with a newline
(`session-start.sh:33`), and `core/.env.example` ends in one, so it takes a hand-saved file whose last line
lacks its newline. The run says nothing is wrong (exit 0, "added to core/.env"), and the key the service
sends then carries the appended text; `pnpm ready` (step 5) names the missing database, and the workaround is
to put the key line and the setting on lines of their own by hand.
