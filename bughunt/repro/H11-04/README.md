# H11-04: the night's dump reads the database `openferment` whatever database core/.env names

**Statement.** `scripts/host/nightly.sh` exports `OPENFERMENT_DATABASE_URL` from `core/.env` to the
night's extraction, checks, proposals and briefs, and `backup_database` then runs
`pg_dump -h 127.0.0.1 … openferment` with a database name fixed in the call, so a Mini whose
`core/.env` names another database (an address `ensure_database` accepts) keeps nightly dumps of a
different database, exit 0, or fails its dump every night when no `openferment` is on the server.

**Contract.**
- `scripts/host/nightly.sh:30`: "The database as the night finds it, before the night's work writes to it";
  the night's work is given the address `nightly.sh:24-26` exports from `core/.env`
  (`nightly.sh:21`: "The database and the project the night's extraction writes into").
- `scripts/host/lib.sh:151-153`: `ensure_database` takes any address besides the example's and says
  "OPENFERMENT_DATABASE_URL names the database." (`docs/runbooks/live-host-install.md:138` makes
  `openferment` only "when no database is named in `core/.env`").
- `docs/runbooks/live-host-install.md:240`: "The night's dump holds the whole database."
- The candidate also cites `docs/runbooks/live-host-install.md:260` "dumps the database `openferment`":
  that sentence agrees with the code, and the alpha 2.2 prompt's §3 (quoted at `lib.sh:168`) names
  `pg_dump openferment`. The break is between the dump and the address the rest of the host reads.

**Command.** From the repository root: `bash bughunt/repro/H11-04/run.sh`

It adds a scratch worktree at 2047f5a and runs its `scripts/host/nightly.sh` as launchd starts it
(`env -i`, PATH and HOME alone, `/bin/bash`). A stand-in `brew` names a keg whose `pg_dump` records its
arguments and runs the real `/usr/bin/pg_dump` on the test server; the test server holds `bh_*`
databases alone, so the plain name `openferment` reads as `bh_r_h11_04_openferment` (a leftover with its
own project `leftover-only`), or as a missing database in night C. The worktree's
`core/.venv/bin/python` is a stand-in that records each `-m openferment_core.*` call with the
`OPENFERMENT_DATABASE_URL` it was given. Step 2 makes `bh_r_h11_04_live` with the project `night-live`
through the API (service on 127.0.0.1:9670). Night 0 is the control (`core/.env` names `…/openferment`);
night A names `…/bh_r_h11_04_live` with a database `openferment` present; night C names it with none.
Step 7 hands the same stand-in `pg_dump` the address `core/.env` names, to show it dumps `night-live`.
Everything (service, databases, worktree, data copies) is removed at exit.

**Expected.** Each night `pg_dump` reads the database the four python steps are given, the one
`core/.env`'s `OPENFERMENT_DATABASE_URL` names: night A's dump holds `night-live`.

**Observed (run1.log, run2.log, the same both times).**
- `ensure_database` over night A's `core/.env`: "OPENFERMENT_DATABASE_URL names the database.", exit 0.
- Night 0: the work given `…/openferment`, `pg_dump … openferment`, exit 0: the control agrees.
- Night A: the four python steps given `DB=postgresql://openferment@127.0.0.1:5432/bh_r_h11_04_live`;
  `pg_dump -h 127.0.0.1 --format=custom --file=…/openferment-2026-11-10.dump.part openferment`; exit 0;
  the kept dump holds 0 lines naming `night-live` and 2 naming `leftover-only`.
- Night C: the same work and the same `pg_dump` call; "pg_dump openferment failed, and the kept dumps
  stay as they were"; nightly exit 1; no dump kept.
- Step 7: the stand-in given `--dbname=…/bh_r_h11_04_live` dumps 2 lines naming `night-live`.
- `RESULT: DEFECT` in both runs.

**Likely cause.** `scripts/host/lib.sh:188`:
`"$tool" -h 127.0.0.1 --format=custom --file="$file.part" openferment` fixes the host and the database
name, and `backup_database` (`lib.sh:177-205`) never reads `OPENFERMENT_DATABASE_URL` (the run counts 0
lines there naming it or `env_setting`). A URL with another port, role or database name reaches the
service and the night's work and never reaches the dump. The test
`core/tests/test_host.py:319-327` asserts the fixed call `pg_dump -h 127.0.0.1 --format=custom
--file=… openferment`, so it holds the mismatch in place.

**Severity.** S3: the default install (`ensure_database` writes `…/openferment`) dumps the right
database; a `core/.env` naming another database is an edge case, with the workaround of naming the
live database `openferment` or dumping it by hand.
