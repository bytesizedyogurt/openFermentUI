"""The openFerment seed loader: `data/corpus/*.json` → Postgres.

`data/corpus/{papers,records,ontology,strains,protocols,scenarios,learn}.json`
is the corpus as the front end reads it (`src/data/source.ts`, "bundled"
backend). This package is the other end of the same seam: it validates those
seven files against the Pydantic models in `openferment_core.schema` and writes
them into a relational schema that is *derived from those same models*.

── THE SCHEMA IS GENERATED ────────────────────────────────────────────────
No `CREATE TABLE` is written by hand anywhere in this package. `columns.py`
walks `model_fields` and maps each annotation to a column; `registry.py` says
which collections exist and declares the five columns no model implies;
`ddl.py` renders. A field added to `ExtractionRecord` becomes a column the next
time the schema is emitted, and `tests/test_seed.py` fails if the checked-in
`schema.sql` has fallen behind the models — because a hand-maintained
`CREATE TABLE` that must agree with a Pydantic model is precisely the thing this
migration exists to remove (CLAUDE.md, "Do not hand-maintain a type in both").

Five columns are NOT derivable, and each says why in `registry.SYNTHETIC` and in
a `COMMENT ON COLUMN` in the emitted schema: `records.row_id` (a record id stops
being unique the moment a correction is appended), `records.supersedes`,
`records.inserted_at`, `audit_event.record_row_id` and `audit_event.ordinal` (a
JSON array is ordered; SQL rows are not).

── APPEND-ONLY IS ENFORCED BY THE DATABASE ────────────────────────────────
`records` and `audit_event` carry a `BEFORE UPDATE OR DELETE` trigger that
raises, and — because `TRUNCATE` fires no row trigger — a `BEFORE TRUNCATE`
statement trigger as well. `REVOKE UPDATE, DELETE, TRUNCATE … FROM PUBLIC` sits
behind that as defence in depth. Neither stops the table's owner from dropping
the trigger; nothing can, and a claim otherwise would be false.

A correction is a new row whose `supersedes` names the `row_id` it replaces —
backwards, because a forward `superseded_by` would have to be filled in by an
UPDATE. `records_current` is the view of rows nothing supersedes; `supersedes`
is UNIQUE so a correction chain cannot fork.

── `AuditEvent.from` ──────────────────────────────────────────────────────
`from` is a SQL reserved word and a Python keyword. The model spells it `from_`
with the alias `from`; `columns.sql_column_name` strips the escape (the rule is
"one trailing underscore, when what remains is a Python keyword", so a future
`class_` needs no new case) and every identifier this package emits is quoted,
so the column is `"from"` and its neighbour is `"to"`. Both are `JSONB`, because
the model types them `Any` to match the TypeScript's `unknown` — an audit entry
records what a value changed from, and that value may be a number, a string, or
an object.

── WHAT IS PROVEN, WITHOUT A SERVER ───────────────────────────────────────
There is no Postgres in this environment. The Postgres DDL is generated,
parsed (sqlglot) and linted; it is NOT executed, and this package does not claim
that it is. What IS executed is the same generated schema rendered for SQLite —
same tables, same columns, same nullability, same CHECK constraints, same
foreign key, same view, same append-only triggers — which is how the tests can
load the real corpus, read it back, and watch an UPDATE be refused. `dialect.py`
lists exactly where the two renderings differ.

Public surface:

    schema_sql(dialect)        the whole DDL as text
    read_corpus(dir)           the seven JSON files, validated
    load(cursor, corpus, …)    write them
    read_collection(cursor, …) read one back, in `source.ts` fetch shape
    append_correction(…)       correct a record by adding a row
"""

from __future__ import annotations

from .columns import Column, Logical, SplitGroup, Table
from .ddl import emit as schema_sql
from .ddl import statements as schema_statements
from .dialect import POSTGRES, SQLITE, Dialect
from .loader import (
    CorpusError,
    Cursor,
    LoadedCorpus,
    append_correction,
    load,
    read_collection,
    read_corpus,
    table_by_name,
)
from .registry import AUDIT, COLLECTIONS, SYNTHETIC, Collection, tables
from .rows import from_row, to_row

__all__ = [
    "AUDIT",
    "COLLECTIONS",
    "POSTGRES",
    "SQLITE",
    "SYNTHETIC",
    "Collection",
    "Column",
    "CorpusError",
    "Cursor",
    "Dialect",
    "LoadedCorpus",
    "Logical",
    "SplitGroup",
    "Table",
    "append_correction",
    "from_row",
    "load",
    "read_collection",
    "read_corpus",
    "schema_sql",
    "schema_statements",
    "table_by_name",
    "tables",
    "to_row",
]
