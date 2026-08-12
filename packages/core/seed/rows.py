"""A model instance and a database row are the same thing, twice.

Everything here is driven by the columns `columns.py` derived, so there is no
list of field names anywhere in this module and no way for a new field to be
packed but not unpacked, or unpacked but not packed. The two directions are
tested against the real corpus: every seeded entity is turned into a row, turned
back, and compared to what went in (`tests/test_seed.py`).

Three things are worth knowing about the mapping.

**Values are taken from `model_dump(mode='json')`, not from the attributes.**
That is one call that already knows how to turn an enum into its value, a nested
model into a dict, a tuple into a list and a `float` into a JSON number — the
same serialisation the corpus JSON was written with. Reaching for the attributes
instead would mean re-deriving all of that here, differently, which is the
two-implementations failure in miniature.

**A NULL column is an ABSENT key, not a null value.** The corpus writes an
absent optional by leaving the key out (`src/data/source.ts` and the exporter
both do), and `extra='forbid'` plus the models' defaults mean an absent key is
exactly what the model wants back. So `from_row` drops nulls rather than passing
`None` in, and the round-trip test proves the two agree.

**A split-union field picks its arm by the value's type**, in the order the
annotation declares. `ExtractionRecord.value` is `float | str`, so 1.5 goes to
`value_num` and 'oligomannosidic N-glycans…' goes to `value_txt` — and a
categorical value that happens to read like a number stays in `value_txt`,
because the arm is chosen from the Python type the model produced, not by
looking at the characters.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .columns import Column, Logical, Table
from .dialect import Dialect

__all__ = [
    "delete_all_sql",
    "from_row",
    "insert_sql",
    "select_sql",
    "to_row",
    "upsert_sql",
    "writable_columns",
]

M = TypeVar("M", bound=BaseModel)


def _arm_matches(logical: Logical, value: Any) -> bool:
    if logical is Logical.TEXT:
        return isinstance(value, str)
    if logical is Logical.BOOLEAN:
        return isinstance(value, bool)
    if logical in (Logical.BIGINT, Logical.SMALLINT):
        return isinstance(value, int) and not isinstance(value, bool)
    if logical is Logical.DOUBLE:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def to_row(
    table: Table,
    instance: BaseModel,
    dialect: Dialect,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One model instance as `{column name: parameter}`.

    `extra` supplies the synthetic columns the model knows nothing about —
    `record_row_id` and `ordinal` on an audit event, `supersedes` on a
    correction. Identity columns and columns with a database default are left
    out entirely so the database fills them.
    """
    dumped = instance.model_dump(mode="json", by_alias=False)
    extra = extra or {}
    row: dict[str, Any] = {}

    for column in table.columns:
        if column.name in extra:
            row[column.name] = _pack(column, extra[column.name], dialect)
            continue
        if column.field is None:
            continue  # synthetic and not supplied: identity, or a DEFAULT
        value = dumped.get(column.field)
        group = _group_for(table, column)
        if group is not None:
            row[column.name] = (
                _pack(column, value, dialect) if _arm_matches(column.logical, value) else None
            )
            continue
        row[column.name] = _pack(column, value, dialect)

    return row


def _pack(column: Column, value: Any, dialect: Dialect) -> Any:
    if value is None:
        return None
    if column.logical is Logical.JSON:
        return dialect.pack_json(value)
    return value


def _group_for(table: Table, column: Column) -> str | None:
    for group in table.splits:
        if column.name in group.columns:
            return group.field
    return None


def from_row(
    table: Table,
    model: type[M],
    row: dict[str, Any],
    dialect: Dialect,
    *,
    extra: dict[str, Any] | None = None,
) -> M:
    """A row back into its model, via the model's own validation.

    Validated rather than constructed, so that a row which somehow violated the
    schema — a hand-written INSERT, a restored dump from an older schema — fails
    here rather than becoming a model instance the rest of the system trusts.
    """
    payload: dict[str, Any] = {}

    for column in table.columns:
        if column.field is None:
            continue
        value = row.get(column.name)
        if value is None:
            continue
        payload[column.field] = (
            dialect.unpack_json(value) if column.logical is Logical.JSON else value
        )

    if extra:
        payload.update(extra)
    return model.model_validate(payload)


# ── statements ─────────────────────────────────────────────────────────


def writable_columns(table: Table) -> tuple[Column, ...]:
    """Columns the loader supplies, in statement order.

    Identity and defaulted columns are the database's to fill, not the loader's
    to invent. Every statement built here and every parameter list built by the
    loader is ordered by this one function, so the two cannot drift apart.
    """
    return tuple(c for c in table.columns if not c.identity and c.sql_default is None)


def _placeholder(column: Column, dialect: Dialect) -> str:
    return dialect.json_param if column.logical is Logical.JSON else dialect.param


def insert_sql(table: Table, dialect: Dialect, *, returning: str | None = None) -> str:
    columns = writable_columns(table)
    names = ", ".join(dialect.quote(c.name) for c in columns)
    values = ", ".join(_placeholder(c, dialect) for c in columns)
    sql = f"INSERT INTO {dialect.quote(table.name)} ({names})\nVALUES ({values})"
    if returning is not None and dialect.supports_returning:
        sql += f"\nRETURNING {dialect.quote(returning)}"
    return sql


def upsert_sql(table: Table, dialect: Dialect) -> str:
    """Insert-or-replace, for the tables that are NOT append-only.

    Reference data — papers, the ontology, strains, protocols, scenarios, learn
    modules — is a projection of `data/corpus/*.json`, so re-running the loader
    against a database that already has it should converge rather than fail. The
    records table gets no such statement: overwriting a record in place is the
    thing this schema exists to make impossible.
    """
    if table.append_only:
        raise ValueError(f"{table.name} is append-only; there is no upsert for it")
    columns = writable_columns(table)
    keys = set(table.primary_key)
    updates = ", ".join(
        f"{dialect.quote(c.name)} = excluded.{dialect.quote(c.name)}"
        for c in columns
        if c.name not in keys
    )
    conflict = ", ".join(dialect.quote(k) for k in table.primary_key)
    return f"{insert_sql(table, dialect)}\nON CONFLICT ({conflict}) DO UPDATE SET {updates}"


def select_sql(
    table: Table,
    dialect: Dialect,
    *,
    source: str | None = None,
    order_by: str | None = None,
) -> tuple[str, tuple[Column, ...]]:
    """A SELECT naming its columns, and the columns it named.

    Explicit rather than `SELECT *`: the caller zips the returned tuple with
    these columns, and column order under `*` is the database's business.
    """
    columns = table.columns
    names = ", ".join(dialect.quote(c.name) for c in columns)
    sql = f"SELECT {names} FROM {dialect.quote(source or table.name)}"
    if order_by is not None:
        sql += f" ORDER BY {dialect.quote(order_by)}"
    return sql, columns


def delete_all_sql(table: Table, dialect: Dialect) -> str:
    """Only ever used against the tables that are not append-only."""
    if table.append_only:
        raise ValueError(f"{table.name} is append-only; rows are never deleted from it")
    return f"DELETE FROM {dialect.quote(table.name)}"
