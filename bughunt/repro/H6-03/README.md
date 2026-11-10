# H6-03: db:import-alpha1 answers a traceback with no `refused:` line

**Statement.** `pnpm db:import-alpha1` prints a Python traceback and exits 1, with no line beginning
`refused:`, in three cases: an alpha 1.0 data directory holds two extraction files of one paper, the
configured server holds no database of the configured name, or the server does not answer. `pnpm
db:migrate` names the last two in words (`refused:`, exit 2).

**Contract.**
- `docs/runbooks/live-host-install.md:218-219`: "A line beginning `refused:` says why, and the import
  has written nothing."
- `core/openferment_core/import_alpha1.py:13-15` (module docstring): "Every file is read and checked
  before anything is written, and everything is written in one transaction: an import lands whole or
  not at all."
- `core/openferment_core/migrations.py:16-18` (the sibling command's docstring): "A command that cannot
  run says why in words and exits 2: no address set, the production database named, a server that does
  not answer, and a database the server does not hold".

**Command.** `bash bughunt/repro/H6-03/run.sh` from the repository root. It adds a worktree of 2047f5a
(on the repository's venv; the worktree holds no `core/.env`), writes two data directories with alpha
1.0's own models (`gen.py`: `candidates/P1.json`, and the same directory with a byte copy named `P1
copy.json`, as a file manager names a duplicate), makes the fresh database `bh_r_h6_03_dup`, and runs
`python -m openferment_core.import_alpha1` (the module `package.json`'s `db:import-alpha1` runs) on
1. the duplicate directory into `bh_r_h6_03_dup`, then the single-file directory as a control;
2. the address of `bh_r_h6_03_absent`, a name the server holds no database under;
3. an address on 127.0.0.1:9729, where nothing listens.
For 2 and 3 it runs `python -m openferment_core.migrations migrate` (`pnpm db:migrate`) on the same
address. It drops both databases and removes the worktree when done.

**Expected.** Each of the three answers one line beginning `refused:` in words and exits 2, writing
nothing: the duplicate named by its second file and its paper, the database and the server named as
`pnpm db:migrate` names them.

**Observed** (run1.log, run2.log, the same both times).
- Two files of one paper: exit 1, no `refused:` line, three chained tracebacks ending in
  `asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint
  "pk_candidates"`, `Key (project_id, document_id, source)=(repro-h6-03-dup, P1, model) already
  exists`, raised from `import_alpha1.py` line 211 in `_write`. The database holds 0 projects and 0
  candidate rows after it (the transaction rolls back). The control, the same directory without the
  copy, carries in with exit 0.
- No database: exit 1, no `refused:` line, three tracebacks ending in `InvalidCatalogNameError:
  database "bh_r_h6_03_absent" does not exist`. `pnpm db:migrate` on the same address: exit 2,
  `refused: the server at 127.0.0.1:5432 holds no database bh_r_h6_03_absent (...): pnpm db:reset
  <name> makes a database of that name there and migrates it`.
- No server: exit 1, no `refused:` line, one traceback ending in `ConnectionRefusedError: [Errno 111]
  Connect call failed ('127.0.0.1', 9729)`. `pnpm db:migrate` on the same address: exit 2, `refused:
  the database bh_r_h6_03_x on 127.0.0.1:9729 could not be reached: ConnectionRefusedError: ...`.

**Likely cause.**
- `core/openferment_core/import_alpha1.py:242`: `main` catches `ImportRefused`, `ProjectRefused` and
  `db.DatabaseUnavailable` alone, so a `DBAPIError` or an `OSError` from `db.run` leaves as a
  traceback. `migrations.py:135` catches `(DBAPIError, OSError)` and words them with `_unreadable`
  (`migrations.py:95`), which the import never calls.
- `core/openferment_core/import_alpha1.py:151`: `read()` reads every `candidates/*.json` and checks each
  file alone; nothing checks that two files name one `paperId`, so the second insert at line 211 meets
  the `candidates` table's key (project, document, source) inside the write.

**Reach.** Nothing is written in any case. The runbook's own line runs `pnpm db:migrate &&
pnpm db:import-alpha1`, so the two database cases show when the import runs by itself (the runbook's
second form, `--data ~/openferment-alpha-1.0-data`, at line 231-232) or the server goes away between
the two. Removing the duplicate file, or making the database, lets the import through: S3.
