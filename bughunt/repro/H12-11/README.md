# H12-11: ready's literature row and the kit's revision go untested

**Statement.** Dropping `at != head` from `ready.check_literature` (mutation M65) leaves `test_ready.py`, `test_db.py` and `test_import_alpha1.py` green, and on a database whose `sci_rag` schema stands at 0005 of 0006 the mutated row then reads `ok` and names revision 0006. The data row's twin mutation (M64) is caught by `test_data_reports_a_database_behind_the_newest_schema`.

**Contract.**
- `core/openferment_core/ready.py:160-161`, the row's own docstring: "Sci RAG Kit's side of the database, as its own `sci-rag doctor` sees it: the vector extension, the kit's schema at its newest revision, a vector column of FastEmbed's dimension, ..."
- `CLAUDE.md:29`: "`pnpm ready` (or `pnpm ready --offline`) says in rows whether the service can run: the database, both schemas, pgvector, ..."

**Command.** From the repository root: `bash bughunt/repro/H12-11/run.sh`

The script works in a scratch worktree of 2047f5a under `$BH_WORK/H12-11/`, keyless, with no service and no model call. It:
1. greps `core/tests/` for callers of `check_literature` (one: `test_ready.py:399`, over the session database at head);
2. makes a fresh database `bh_r_h12_11_kit` with `bh_db_fresh`, takes `sci_rag` back to 0005 with alembic's downgrade, and asks `check_literature` on the tree as it stands, then with M65 applied;
3. runs the three test files with M65 applied (test databases `bh_r_h12_11_t_*`);
4. runs `test_ready.py` with M64 applied, as the control.

It drops every database it made and removes the worktree at the end.

**Expected.** A test holds the literature row to the kit's revision, as `test_data_reports_a_database_behind_the_newest_schema` holds the data row: with M65 applied, at least one of the three files fails.

**Observed (both runs).**
- As the tree stands, on `sci_rag` at 0005: `fail | Sci RAG Kit's schema is at revision 0005 of 0006. Run: pnpm db:migrate`.
- With M65, on the same database: `ok | pgvector 0.6.0, revision 0006, 0 documents, 0 chunks`. The row reads green and names the head revision for a schema one revision short.
- With M65: `95 passed`. The one caller, `test_the_literature_row_reads_the_kits_schema` (`core/tests/test_ready.py:398`), runs over a database migrated to head, where both versions of the row agree.
- Control M64: `1 failed, 64 passed`, with `test_data_reports_a_database_behind_the_newest_schema` failing.

`RESULT: DEFECT` in `run1.log` and `run2.log`.

**Likely cause.** `core/openferment_core/ready.py:206` (`if at != head or width is None:`) is the one line that compares the kit's revision with its head. `core/tests/test_ready.py:433-441` builds a bare database for the data row alone, and no test makes a kit schema behind its head, so the `at != head` half of line 206 has no test. The `width is None` half covers a schema with no `chunks` table. Revision 0006 adds `document_citations` alone, so a 0005 schema keeps the vector column and passes that half. A fix is one test: migrate a database, downgrade `sci_rag` one revision, and assert the literature row fails with `pnpm db:migrate` in its words.

**Severity.** S4 (a hollow test): the row behaves as documented today, and the test suite would let a break of its revision check through unseen.
