# R2-02: conform against a database the server does not hold

**Verdict: not reproduced.** Both runs print `RESULT: NO-DEFECT`. Each command does what its page says.

## Statement (the candidate's)

With `OPENFERMENT_DATABASE_URL` naming a database the PostgreSQL server does not hold, `conform biosteam`
makes its checks, prints the driver's error for the verdict it could not keep, says "every check holds" and
exits 0, while `migrations migrate` refuses the same address in words with exit 2.

## The contract

The candidate cites commit 6f85338 (D.0), "conform and migrations say a missing database in words (exit 2)",
and `docs/api/engines.md:805-807`. The pages written in that same commit say what "a missing database" means
for each command, and they hold conform to a server alone:

- `docs/api/engines.md:805-808`: "keeps its verdict in that address's database's `engine_checks`, with
  `--project` or without, once that database is migrated (`pnpm db:migrate`); a verdict it cannot keep is
  printed with the words why. With no address set, or a server that does not answer, it says so in words
  naming `OPENFERMENT_DATABASE_URL`, and exits 2."
- `docs/api/engines.md:113-115`: "The service needs `OPENFERMENT_DATABASE_URL` ... naming a migrated
  database, and `conform` the PostgreSQL server that address names, keeping its verdict once the named
  database is migrated".
- `docs/PROGRESS.md:1887-1889` (D0.7, the item the commit's phrase summarises for conform): "`conform` with
  no database (D0.7, A20): no `OPENFERMENT_DATABASE_URL`, or a server that does not answer, is said in words
  naming it and the address, its password hidden, and the command exits 2, with `--project` or without."
- `docs/PROGRESS.md:2060-2061` (R4, the item for migrations): "`python -m openferment_core.migrations` (R4)
  says in words, exit 2, a server that does not answer and a database its server does not hold, the latter
  with `pnpm db:reset <name>`."
- `core/openferment_core/engine/conform.py:38-40`: "Exits 1 when any check fails, and 2, in words naming
  OPENFERMENT_DATABASE_URL, when no address is set or its server does not answer".
- `core/openferment_core/migrations.py:16-18`: "a server that does not answer, and a database the server
  does not hold, which `reset NAME` (pnpm db:reset NAME) makes."

The pages give the database the server does not hold to migrations alone. For conform they give the case
its own sentence, "a verdict it cannot keep is printed with the words why", and an exit that follows the
checks.

## Command

    bash bughunt/repro/R2-02/run.sh

Run it from the repository root. It needs no key and calls no model. It makes `bh_r_r2_02_cfg` fresh with
`bh_db_fresh`, checks that `bh_r_r2_02_missing` is absent, and runs four commands from the main checkout's
own Python: `migrations migrate`, `conform biosteam` and `conform train --project p`, each with the
address naming `bh_r_r2_02_missing`, then `conform train --project p` on `bh_r_r2_02_cfg` as the control.
Before `conform.main` runs, the script sets conform's scratch prefix in the process (`conform.SCRATCH`), so
the checks' own database is named `bh_r_r2_02_cf_*`. Bytecode writing is turned off, and a private data
directory and a numba cache under `$BH_WORK/R2-02` take every other write, so the script edits nothing under
`core/`. It drops every `bh_r_r2_02_*` database when it ends.

## Expected (from the pages)

- `migrations migrate`: refused in words naming the missing database and `pnpm db:reset`, exit 2.
- `conform biosteam`: the eight checks run on a database of their own on the server. The verdict cannot be
  kept, and the reason is printed. The exit follows the checks: 0 when every check holds, 1 when one fails.
- `conform train --project p`: refused in words naming `OPENFERMENT_DATABASE_URL`, exit 2.

## Observed (run1.log and run2.log, the same in both)

- migrations: `refused: the server at 127.0.0.1:5432 holds no database bh_r_r2_02_missing (database
  "bh_r_r2_02_missing" does not exist): pnpm db:reset <name> makes a database of that name there and
  migrates it`, exit 2.
- conform biosteam: `! the verdict could not be kept for GET /api/engines: DBAPIError: ... database
  "bh_r_r2_02_missing" does not exist`, then `biosteam (...): every check holds` with eight ✓ rows, exit 0
  (57 s in run 1, 33 s in run 2). No `bh_r_r2_02_cf_*` database was left behind.
- conform train --project p: `✗ the PostgreSQL server OPENFERMENT_DATABASE_URL names
  (postgresql+asyncpg://openferment:***@127.0.0.1:5432/bh_r_r2_02_missing) could not read project 'p' from
  its database: DBAPIError: ... database "bh_r_r2_02_missing" does not exist ... Start it (pnpm db:up), ...
  or set OPENFERMENT_DATABASE_URL ... to a server with pgvector that answers`, exit 2.
- control: `✗ database 'bh_r_r2_02_cfg' holds no project 'p': name a project it holds`, exit 2.

## Cause, and what is left

The behaviour comes from `core/openferment_core/engine/conform.py:1120-1125`. A `keep(v)` that raises is
printed with its reason, and the command returns `0 if v.ok else 1`. That is the documented path from
`docs/api/engines.md:806-807`, and the two commands differ by design.

One wording point remains, outside the cited contract. With `--project`, a database the server lacks reaches
`_unanswered` (`conform.py:1013-1014`, words at `conform.py:756-769`), whose fixed advice ends "Start it
(pnpm db:up) ... to a server with pgvector that answers" when the server already answers. The same message
includes the server's own words naming the missing database, and the exit is 2 as the page requires. At most
this is S4 wording. Migrations' words for the same case name `pnpm db:reset <name>`.
