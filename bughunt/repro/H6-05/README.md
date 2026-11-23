# H6-05 (with H10-04): ADR-001 and CLAUDE.md say JSONB; every content column is `json`

**Statement.** ADR-001's implementation note and CLAUDE.md's architecture line say each row keeps the
Pydantic model as a JSONB `body`, and the migrations make every content column of schema `openferment`
(34 of them, the 29 `body` columns among them) PostgreSQL `json`, the type
`core/openferment_core/db/models.py`'s own docstring says it chose.

H10-04 (`bughunt/notes/H10/candidates.json`) reports the same drift over the 29 `body` columns; this
one reproduction shows both.

## The contract it breaks

- `docs/decisions/ADR-001-postgresql.md:62`: "the rest of the row is `body`, the Pydantic model of
  `models.py` dumped as JSONB."
- `CLAUDE.md:66`: "a row keeps its lookup keys as columns and the Pydantic model as JSONB `body`
  (ADR-001)."
- `docs/PROGRESS.md:541` (the departures table, "the Pydantic model as JSONB") and
  `docs/PROGRESS.md:763` (stage 2.1's log line, "SQLAlchemy Core with a JSONB `body`") repeat the word.
- The tree says `json` and gives its reason: `core/openferment_core/db/models.py:7-9` "The content
  columns are `json`, which keeps the text as written: an object's keys keep their order (a
  simulation's series are drawn in it) and a negative zero stays one." `docs/PROGRESS.md:796-797`
  (stage 2.3's log line) says the same: "Content columns are `json` (key order is kept ...)".

## Command

```
bash bughunt/repro/H6-05/run.sh
```

The script makes a fresh database `bh_r_h6_05_types` and migrates it from empty to head (`0010`, both
schemas). It reads from `information_schema.columns` the type of every content column of schema
`openferment` (`body`, `record`, `selection`, `settings`, `input`, `result`), counts the `body` columns
and any `jsonb` column in the schema, and casts one literal to each type to show what each keeps. It
then reads ADR-001:62, CLAUDE.md:66, PROGRESS.md's lines, models.py's docstring and column
declarations, and the migrations' column types with `sed`, `awk` and `grep`. It starts no service and
makes no model call, and it drops the database when it ends.

## Expected

The content columns of a migrated database are of the type ADR-001:62 and CLAUDE.md:66 name, JSONB;
or the two documents say `json`, as models.py:6-9 and PROGRESS.md:796-797 do.

## Observed (both runs)

```
json: 34 columns (body,input,record,result,selection,settings)
body columns: 29, of type json: 29; columns of type jsonb anywhere in schema openferment: 0
'{"b":1,"a":-0}'::json  -> {"b":1,"a":-0}
'{"b":1,"a":-0}'::jsonb -> {"a": 0, "b": 1}
OBSERVED: 34 content columns of type json (29 of 29 body columns), 0 of type jsonb; 2 of the 2 documents say JSONB
RESULT: DEFECT
```

The cast shows why the code's choice holds for its reason: `json` keeps key order and `-0`, and
`jsonb` sorts the keys and writes `0`. The documents carry the word the code left behind.

## Likely cause

Commit `fa16892` (stage 2.3, "every store on its table") changed
`core/openferment_core/db/models.py:36` from `postgresql import JSONB` to `postgresql import JSON`
and added the docstring's reason at models.py:7-9; migration
`core/openferment_core/db/alembic/versions/0001_initial.py` (29 columns, for example line 42) and
`0006_eval.py:31` (one line for its two tables, `eval_questions` and `eval_runs`), `0007_catalogue.py:31`, `0009_engine_checks.py:32`, `0010_protocols.py:31` make
`postgresql.JSON` columns to match. ADR-001:62 and CLAUDE.md:66, written at stage 2.1 (`96fd138`)
while the column was still JSONB, kept the word. The fix is two words, in ADR-001:62 and CLAUDE.md:66,
and the two PROGRESS.md lines with them; `core/tests/test_guidance.py` holds CLAUDE.md's lines, so the
change to line 66 runs that test.

Severity S4 (drift in a record): the stores read and write whole bodies by key and query inside none,
so no number, label or row changes.
