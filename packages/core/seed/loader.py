"""Read `data/corpus/*.json`, validate it, and write it to the database.

Two rules shape this module, both inherited from
`packages/core/scripts/validate_fixtures.py`, which is the same job one step
earlier in the pipeline.

**Validate everything before writing anything.** A load that inserts eighty
papers and then discovers the eighty-first does not parse has left the database
in a state nobody asked for. `read_corpus` parses all seven collections and
reports every failure it found, with the entity id and the field, before any
statement is executed.

**Where a real corpus instance fails to parse, the MODEL is wrong.** The corpus
is real literature, unevenly keyed on purpose. This loader never coerces, never
fills in a missing value and never drops a field it does not recognise; it fails
and says which entity and which field, so the model can be fixed deliberately.

The read path (`read_collection`) exists so the round trip can be tested and so
an API backend has something to serve: it returns exactly the JSON array
`src/data/source.ts` fetches from `{VITE_CORPUS_API_BASE}/{name}.json` —
camelCase keys, absent optionals absent. What it does NOT do is sort, or
recompute `si`: the adapter applies both on read, deliberately and for both
backends, so doing it here as well would be a second implementation of a
derivation that already has one home.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from .columns import Table
from .dialect import Dialect
from .registry import AUDIT, COLLECTIONS, tables
from .rows import from_row, insert_sql, select_sql, to_row, upsert_sql, writable_columns

__all__ = [
    "CorpusError",
    "Cursor",
    "LoadedCorpus",
    "append_correction",
    "load",
    "read_collection",
    "read_corpus",
    "table_by_name",
]


class Cursor(Protocol):
    """The slice of DB-API 2.0 this loader uses.

    Deliberately three methods wide. `psycopg`'s cursor and `sqlite3`'s cursor
    are both this, and nothing here depends on anything that is not in the spec
    — the one driver-specific thing, `lastrowid`, is reached for with `getattr`
    and only on a dialect that has no `RETURNING`.
    """

    def execute(self, sql: str, parameters: Sequence[Any] = ..., /) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


class CorpusError(Exception):
    """One or more corpus entities did not parse. Carries every failure."""

    def __init__(self, failures: Sequence[str]) -> None:
        self.failures = list(failures)
        head = f"{len(self.failures)} corpus entit{'y' if len(self.failures) == 1 else 'ies'}"
        super().__init__(f"{head} failed to validate:\n  - " + "\n  - ".join(self.failures))


@dataclass(frozen=True)
class LoadedCorpus:
    """Every collection, parsed. Keyed by the file stem, which is also the key
    `src/data/source.ts` fetches under."""

    items: dict[str, list[BaseModel]]

    def counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.items.items()}


def table_by_name(name: str) -> Table:
    for table in tables():
        if table.name == name:
            return table
    raise KeyError(f"no table named {name!r}")


def _identify(raw: object, index: int) -> str:
    if isinstance(raw, dict):
        for key in ("id", "modelId", "model_id", "name", "title"):
            if key in raw:
                return str(raw[key])
    return f"[{index}]"


def read_corpus(corpus_dir: Path) -> LoadedCorpus:
    """Parse all seven files. Raises `CorpusError` listing every failure.

    A missing file is an error and an empty one is not: `data/corpus/*.json` is
    generated, and a collection that is legitimately empty (`learn.json` before
    the modules are written) is a fact about the corpus, while a file that is
    not there means the export did not run.
    """
    failures: list[str] = []
    items: dict[str, list[BaseModel]] = {}

    for collection in COLLECTIONS:
        path = corpus_dir / f"{collection.name}.json"
        if not path.exists():
            failures.append(f"{collection.name}: {path} does not exist")
            items[collection.name] = []
            continue
        raw = json.loads(path.read_text("utf-8"))
        if not isinstance(raw, list):
            failures.append(f"{collection.name}: {path} is not a JSON array")
            items[collection.name] = []
            continue

        parsed: list[BaseModel] = []
        for index, entry in enumerate(raw):
            identity = _identify(entry, index)
            try:
                parsed.append(collection.model.model_validate(entry))
            except ValidationError as error:
                for detail in error.errors():
                    location = ".".join(str(part) for part in detail["loc"])
                    failures.append(
                        f"{collection.name}/{identity}: {location} — {detail['msg']} "
                        f"(got {detail.get('input')!r})"
                    )
        items[collection.name] = parsed

    if failures:
        raise CorpusError(failures)
    return LoadedCorpus(items=items)


def _execute(cursor: Cursor, sql: str, table: Table, row: dict[str, Any]) -> None:
    """Run one statement, ordering the parameters exactly as it names them."""
    cursor.execute(sql, [row.get(c.name) for c in writable_columns(table)])


def _insert_returning_row_id(cursor: Cursor, sql: str, params: list[Any], dialect: Dialect) -> int:
    cursor.execute(sql, params)
    if dialect.supports_returning:
        fetched = cursor.fetchone()
        return int(fetched[0])
    row_id = getattr(cursor, "lastrowid", None)
    if row_id is None:
        raise RuntimeError(
            f"{dialect.name} has neither RETURNING nor lastrowid; the audit events of a "
            f"record cannot be attached without the row_id of the row they belong to."
        )
    return int(row_id)


def _record_count(cursor: Cursor, dialect: Dialect) -> int:
    cursor.execute(f"SELECT count(*) FROM {dialect.quote(AUDIT.parent)}", [])
    fetched = cursor.fetchone()
    return int(fetched[0])


def load(
    cursor: Cursor,
    corpus: LoadedCorpus,
    dialect: Dialect,
    *,
    append: bool = False,
) -> dict[str, int]:
    """Write a parsed corpus. Returns rows written per table.

    Reference tables upsert on their primary key, so a reload converges. The
    records table cannot: it is append-only, and loading the same corpus twice
    would append a second copy of every record with nothing marking it as a
    correction of the first. So a non-empty records table is refused unless
    `append=True` says that is what was meant.
    """
    if not append:
        existing = _record_count(cursor, dialect)
        if existing:
            raise RuntimeError(
                f"{AUDIT.parent} already holds {existing} row(s). It is append-only, so a "
                f"second load would add a duplicate of every record rather than replace it. "
                f"Load into an empty database, or pass append=True if a second batch is "
                f"genuinely what is wanted."
            )

    written: dict[str, int] = {AUDIT.table: 0}

    for collection in COLLECTIONS:
        table = table_by_name(collection.table)
        entries = corpus.items.get(collection.name, [])

        if not table.append_only:
            statement = upsert_sql(table, dialect)
            for entry in entries:
                _execute(cursor, statement, table, to_row(table, entry, dialect))
            written[table.name] = len(entries)
            continue

        written[table.name] = 0
        for entry in entries:
            written[AUDIT.table] += _insert_record(cursor, entry, dialect)
            written[table.name] += 1

    return written


def _insert_record(
    cursor: Cursor,
    record: BaseModel,
    dialect: Dialect,
    *,
    supersedes: int | None = None,
) -> int:
    """Insert one record and its audit trail. Returns the audit rows written."""
    records = table_by_name(AUDIT.parent)
    audit = table_by_name(AUDIT.table)

    extra: dict[str, Any] = {} if supersedes is None else {"supersedes": supersedes}
    row = to_row(records, record, dialect, extra=extra)
    row_id = _insert_returning_row_id(
        cursor,
        insert_sql(records, dialect, returning="row_id"),
        [row.get(c.name) for c in writable_columns(records)],
        dialect,
    )

    statement = insert_sql(audit, dialect)
    events = getattr(record, AUDIT.field)
    for ordinal, event in enumerate(events):
        event_row = to_row(
            audit, event, dialect, extra={"record_row_id": row_id, "ordinal": ordinal}
        )
        _execute(cursor, statement, audit, event_row)
    return len(events)


def append_correction(
    cursor: Cursor,
    record: BaseModel,
    dialect: Dialect,
    *,
    supersedes: int,
) -> int:
    """Correct a record the only way this schema allows: by adding a row.

    `supersedes` is the `row_id` of the row being replaced. Nothing about that
    older row changes — it stays exactly as it was written, which is the point
    of an append-only store — and `records_current` stops returning it because
    a newer row now points at it.
    """
    _insert_record(cursor, record, dialect, supersedes=supersedes)
    cursor.execute(f"SELECT max({dialect.quote('row_id')}) FROM {dialect.quote(AUDIT.parent)}", [])
    fetched = cursor.fetchone()
    return int(fetched[0])


def read_collection(cursor: Cursor, dialect: Dialect, name: str) -> list[dict[str, Any]]:
    """One collection back out, in the shape `src/data/source.ts` fetches.

    Records come from `records_current`, not from `records`: the superseded
    versions are kept for the audit trail, not to be served twice.
    """
    collection = next((c for c in COLLECTIONS if c.name == name), None)
    if collection is None:
        raise KeyError(f"no collection named {name!r}")
    table = table_by_name(collection.table)

    source = f"{table.name}_current" if table.append_only else None
    order = "row_id" if table.append_only else None
    sql, columns = select_sql(table, dialect, source=source, order_by=order)
    cursor.execute(sql, [])
    fetched = list(cursor.fetchall())
    rows = [dict(zip((c.name for c in columns), values, strict=True)) for values in fetched]

    audit_by_row = _audit_by_row(cursor, dialect) if table.append_only else {}

    out: list[dict[str, Any]] = []
    for row in rows:
        extra: dict[str, Any] = {}
        if table.append_only:
            extra[AUDIT.field] = audit_by_row.get(int(row["row_id"]), [])
        instance = from_row(table, collection.model, row, dialect, extra=extra)
        out.append(instance.model_dump(mode="json", by_alias=True, exclude_none=True))
    return out


def _audit_by_row(cursor: Cursor, dialect: Dialect) -> dict[int, list[dict[str, Any]]]:
    """Every audit trail, grouped by record row and in `ordinal` order.

    Ordered explicitly. A `SELECT` without an `ORDER BY` returns rows in
    whatever order the plan produced, and the order of a record's audit events
    is data — the same argument `src/data/source.ts` makes about entry order.
    """
    audit = table_by_name(AUDIT.table)
    names = ", ".join(dialect.quote(c.name) for c in audit.columns)
    cursor.execute(
        f"SELECT {names} FROM {dialect.quote(audit.name)} "
        f"ORDER BY {dialect.quote('record_row_id')}, {dialect.quote('ordinal')}",
        [],
    )
    out: dict[int, list[dict[str, Any]]] = {}
    for values in cursor.fetchall():
        row = dict(zip((c.name for c in audit.columns), values, strict=True))
        event = from_row(audit, AUDIT.model, row, dialect)
        out.setdefault(int(row["record_row_id"]), []).append(
            event.model_dump(mode="json", by_alias=True, exclude_none=True)
        )
    return out
