# H13-04: `pnpm eval` answers a missing or unknown project with tracebacks or an empty summary

**Statement.** Asked with no `OPENFERMENT_PROJECT`, `pnpm eval seed` and `pnpm eval summary` end in a
Python traceback (`ProjectRequired`, exit 1); asked with a project the database lacks, `eval seed`
ends in three chained tracebacks (`ForeignKeyViolationError`, with the SQL insert and its parameters,
exit 1) and `eval summary` prints an empty summary with exit 0, the same bytes a held project with no
runs prints; `pnpm lit:graph`, `conform` and the MCP server meet the same unknown project with words
that name it, and the two commands exit 2.

**Contract.**
- `core/openferment_core/projects/__init__.py:10-11`: "A command or the MCP server names it once, in
  OPENFERMENT_PROJECT. A store call that names none is refused in words."
- The other doors for the same case, each refusing in words:
  - `core/openferment_core/literature_live.py:226`: "The store holds no project {args.project!r}."
    (exit 2, `pnpm lit:graph`);
  - `core/openferment_core/engine/conform.py:1016`: "database ... holds no project {project_id!r}:
    name a project it holds" (exit 2 at `conform.py:1094-1096`);
  - `core/openferment_core/mcp_server.py:339`: "... holds no project named {self.project!r}. Start
    this server with --project naming a project it holds ...".
- `core/openferment_core/evaluation.py:25`: "It acts in the project OPENFERMENT_PROJECT names", and
  `evaluation.py:38-39`: "A command asked of questions the suite cannot ask as named exits 2 in words,
  having asked nothing." These two lines are the command's own register for a refusal; line 38-39
  speaks of questions, so the project case rests on the projects module's words and the three doors
  above.

**Command** (from the repository root): `bash bughunt/repro/H13-04/run.sh`

It makes a fresh migrated test database `bh_r_h13_04_eval`, keeps one project `h13-held` in it
through `projects.create`, and adds a detached worktree of `2047f5a` under the scratchpad's
`bh/work/H13-04/run/`. The worktree holds no `core/.env`, so the command's own `__main__` loader
(`evaluation._settings`) reads nothing of the checkout's settings. Each command runs from the
worktree's `core/` with the checkout's Python, keyless: `pnpm eval` is
`cd core && uv run --all-extras python -m openferment_core.evaluation`, and the script runs that
module directly. No service, no network, no model call. The cases:

1. `eval seed`, `OPENFERMENT_PROJECT` unset.
2. `eval seed`, `OPENFERMENT_PROJECT=nope`, and the rows kept for `nope` counted after.
3. `eval summary`, `OPENFERMENT_PROJECT=nope`; and `eval summary` with it unset.
4. Control: `eval seed` and `eval summary` in `h13-held`, the project the database holds.
5. The other doors: `literature_live graph --project nope --dry-run` (`pnpm lit:graph`) and
   `engine.conform train --project nope`.

The database and the worktree are removed at the end.

**Expected.** Each `eval` case exits 2 with words naming the missing or unknown project and keeps
nothing, as `lit:graph` and `conform` answer the same project.

**Observed** (both runs, `run1.log` and `run2.log`, `RESULT: DEFECT`):
- `eval seed`, no project: exit 1, one traceback (17 lines) ending
  `openferment_core.projects.ProjectRequired: This names no project. ... a command sets OPENFERMENT_PROJECT.`
- `eval seed`, `nope`: exit 1, three chained tracebacks (180 lines) ending
  `sqlalchemy.exc.IntegrityError: (...ForeignKeyViolationError) insert or update on table "eval_questions" violates foreign key constraint "fk_eval_questions_project_id"`,
  with `[SQL: INSERT INTO openferment.eval_questions ...]` and `[parameters: ('nope', 'eq-price', ...)]`;
  0 rows kept for `nope` (the foreign key held the database clean).
- `eval summary`, `nope`: exit 0, nothing on stderr, stdout
  `{"suite": "default", "tags": {}, "judgesDisagree": []}`.
- `eval summary`, no project: exit 1, a `ProjectRequired` traceback.
- Control, `h13-held`: `eval seed` exit 0 `{"seeded": ["eq-price", "eq-dearer"]}`; `eval summary`
  exit 0 `{"suite": "default", "tags": {}, "judgesDisagree": []}`, byte for byte the answer for `nope`.
- `lit:graph --project nope --dry-run`: exit 2, `The store holds no project 'nope'.`
- `conform train --project nope`: exit 2,
  `✗ database 'bh_r_h13_04_eval' holds no project 'nope': name a project it holds`.

A mistyped project name thus reads as a project with no runs on `eval summary`, and as a database
fault on `eval seed`.

**Likely cause** (confidence high).
- `core/openferment_core/evaluation.py:106-114`: `main` calls `evaluate.seed` and `evaluate.summary`
  with no check that the project is named and held, and catches no `projects.ProjectRequired`; the
  `run` and `judge` branches (`evaluation.py:115-150`) catch `evaluate.Refused` and
  `JudgeUnavailable` alone.
- `core/openferment_core/postdoc/evaluate.py:383-389` (`seed`) reads `projects.current()` and inserts
  straight away, so an unknown project reaches the foreign key; `evaluate.py:1221-1235` (`summary`)
  reads `newest(suite)`, which finds no rows for an unknown project and answers an empty summary.

A fix in `evaluation.main` reads `projects.current_or_none()` and `projects.get(...)` before any
branch, as `literature_live.main` does at `literature_live.py:225-227`, and answers a missing or
unknown project in words with exit 2.
