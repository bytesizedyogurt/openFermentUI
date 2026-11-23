# H11-06: session-start appends the development address over an `export` or spaced database line

**Statement.** `scripts/session-start.sh` looks for core/.env's database with `grep -q '^OPENFERMENT_DATABASE_URL='`, so a core/.env that names its database as `export OPENFERMENT_DATABASE_URL=...` or `OPENFERMENT_DATABASE_URL = ...` (forms python-dotenv and `scripts/host/lib.sh`'s `env_setting` both read) gains the development address on a later line, and the service, which takes the file's last line for a name, then reads `openferment_dev`.

**Contract.**
- `scripts/session-start.sh:18-20`: "the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and core/.env names none, the development address (compose.yaml's) joins core/.env; then pnpm db:migrate".
- `scripts/host/lib.sh:97-100`: `env_setting` reads core/.env "in the forms of python-dotenv these settings take: an `export` before the name, blanks around `=`", and `core/tests/test_host.py:195-196` hold `export OPENFERMENT_PROJECT=ethanol` and `OPENFERMENT_PROJECT = ethanol` to python-dotenv's reading.
- `core/openferment_core/api.py:178`: the service loads core/.env with `load_dotenv(..., override=False)`, and `db/engine.py:49-59` reads `OPENFERMENT_DATABASE_URL` from what it loaded.

**Command** (from the repository root):

    bash bughunt/repro/H11-06/run.sh

It makes a fresh test database `bh_r_h11_06_named` and a scratch worktree at 2047f5a, writes the worktree's core/.env naming that database in three forms (the plain `NAME=url` as a control, `export NAME=url`, `NAME = url`), and for each: reads it as the service does (the worktree's own `db.engine.database_url()` after `load_dotenv`) and connects, reads it with the worktree's `env_setting`, runs the worktree's `scripts/session-start.sh` with the real `pg_isready` and stand-ins for `pnpm` and `uv` (so no install, sync or migration runs and nothing reaches `openferment_dev`), and reads it again. The database is dropped and the worktree removed after.

**Expected.** A core/.env that names a database in a form python-dotenv reads is left as it is by session-start, and the service reads that database after the session start as it did before.

**Observed.** The control is left alone. For the `export` form and the spaced form alike, the service's reading names `bh_r_h11_06_named` and connects to it before; session-start prints "OPENFERMENT_DATABASE_URL added to core/.env (the development address)" and appends `OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev`; after, the service's reading and `env_setting` both name `openferment_dev`. The same run's next step is `pnpm --silent db:migrate` (recorded by the stand-in), which on a real machine migrates the appended `openferment_dev`.

**Likely cause.** `scripts/session-start.sh:62`: `! grep -q '^OPENFERMENT_DATABASE_URL=' core/.env` matches the plain form alone. The pattern `env_setting` uses at `scripts/host/lib.sh:111` (`^[[:space:]]*(export[[:space:]]+)?NAME[[:space:]]*=`) reads the other forms. The workspace line at `scripts/session-start.sh:47` has the same shape.

Runs: `run1.log`, `run2.log`.
