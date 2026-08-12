"""Render the derived tables as SQL.

`statements(dialect)` is the API; `emit(dialect)` is the same thing as a file.
Nothing here decides what a table contains — `registry.tables()` did that from
the Pydantic models — so the whole of this module is punctuation, plus the four
things that are not columns:

* the append-only triggers, delegated to the dialect;
* `<table>_current`, the view that reads an append-only table as its latest
  rows, generated for any table that has a `supersedes` column;
* `REVOKE`, so a role cannot be granted a privilege the trigger will refuse;
* `COMMENT ON`, which carries every `Field(description=...)` and every synthetic
  column's stated reason into the database catalogue. A column whose reason for
  existing lives only in a Python file is a column someone will "clean up".

No `DROP`, no `IF NOT EXISTS`, no `ALTER`: this script builds the schema once,
into an empty database. Changing a schema that already holds rows is a migration
and this phase does not write migrations — it would have to guess what the old
schema was.
"""

from __future__ import annotations

from .columns import Column, SplitGroup, Table
from .dialect import Dialect
from .registry import tables

__all__ = ["emit", "statements", "table_statements"]

_WRAP = 96


def _check_in(dialect: Dialect, column: Column) -> str:
    assert column.allowed is not None
    values = ", ".join(dialect.literal(v) for v in column.allowed)
    return f"CHECK ({dialect.quote(column.name)} IN ({values}))"


def _column_sql(dialect: Dialect, column: Column) -> str:
    if column.identity:
        return dialect.identity_clause(column)

    head = f"{dialect.quote(column.name)} {dialect.type_of(column)}"
    if not column.nullable:
        head += " NOT NULL"
    default = dialect.default_of(column)
    if default is not None:
        head += f" DEFAULT {default}"
    if column.references is not None:
        target, target_column = column.references
        head += f" REFERENCES {dialect.quote(target)} ({dialect.quote(target_column)})"

    tail: list[str] = []
    if column.allowed is not None:
        tail.append(_check_in(dialect, column))
    if column.json_arity is not None:
        length = dialect.json_array_length(dialect.quote(column.name))
        tail.append(f"CHECK ({length} = {column.json_arity})")

    if not tail:
        return head
    one_line = head + " " + " ".join(tail)
    if len(one_line) + 4 <= _WRAP:
        return one_line
    return head + "".join("\n        " + t for t in tail)


def _split_check(dialect: Dialect, table: Table, group: SplitGroup) -> str:
    """ "Exactly one arm holds the value" — or "at most one", when optional.

    Written as a sum of CASE expressions rather than the two-column `IS NULL <>
    IS NULL` trick, because the trick only works for exactly two arms and this
    rule is derived from the annotation, which is free to grow a third.
    """
    terms = " + ".join(
        f"(CASE WHEN {dialect.quote(name)} IS NULL THEN 0 ELSE 1 END)" for name in group.columns
    )
    comparison = "= 1" if group.required else "<= 1"
    name = dialect.quote(f"{table.name}_{group.field}_one_arm")
    return f"CONSTRAINT {name} CHECK (({terms}) {comparison})"


def table_statements(dialect: Dialect, table: Table) -> list[str]:
    body: list[str] = [_column_sql(dialect, c) for c in table.columns]

    if table.primary_key:
        cols = ", ".join(dialect.quote(c) for c in table.primary_key)
        body.append(f"CONSTRAINT {dialect.quote(table.name + '_pk')} PRIMARY KEY ({cols})")
    for unique in table.unique:
        cols = ", ".join(dialect.quote(c) for c in unique)
        suffix = "_".join(unique)
        body.append(f"CONSTRAINT {dialect.quote(f'{table.name}_{suffix}_key')} UNIQUE ({cols})")
    for group in table.splits:
        body.append(_split_check(dialect, table, group))

    inner = ",\n    ".join(body)
    out = [f"CREATE TABLE {dialect.quote(table.name)} (\n    {inner}\n)"]

    for index in table.indexes:
        cols = ", ".join(dialect.quote(c) for c in index)
        suffix = "_".join(index)
        out.append(
            f"CREATE INDEX {dialect.quote(f'{table.name}_{suffix}_idx')} "
            f"ON {dialect.quote(table.name)} ({cols})"
        )

    if table.append_only:
        out.extend(dialect.append_only_statements(table.name))
        out.extend(dialect.privilege_statements(table.name))

    out.extend(_view_statements(dialect, table))
    out.extend(_comment_statements(dialect, table))
    return out


def _view_statements(dialect: Dialect, table: Table) -> list[str]:
    """`<table>_current`: the rows nothing else supersedes.

    Emitted for any table carrying a `supersedes` column, which is how an
    append-only table expresses a correction. Reading `records` directly gives
    every version ever written, which is the point of keeping them; reading
    `records_current` gives the corpus as it now stands.
    """
    if not any(c.name == "supersedes" for c in table.columns):
        return []
    name = dialect.quote(f"{table.name}_current")
    t = dialect.quote(table.name)
    return [
        f"CREATE VIEW {name} AS\n"
        f'SELECT "r".* FROM {t} AS "r"\n'
        f'WHERE NOT EXISTS (SELECT 1 FROM {t} AS "s" WHERE "s"."supersedes" = "r"."row_id")'
    ]


def _comment_statements(dialect: Dialect, table: Table) -> list[str]:
    if not dialect.supports_comments:
        return []
    out: list[str] = []
    if table.doc:
        out.append(f"COMMENT ON TABLE {dialect.quote(table.name)} IS {dialect.literal(table.doc)}")
    for column in table.columns:
        text = _column_comment(table, column)
        if text is None:
            continue
        target = f"{dialect.quote(table.name)}.{dialect.quote(column.name)}"
        out.append(f"COMMENT ON COLUMN {target} IS {dialect.literal(text)}")
    return out


def _column_comment(table: Table, column: Column) -> str | None:
    if column.why is not None:
        return column.why
    if column.field is None or table.model is None:
        return None
    info = table.model.model_fields.get(column.field)
    description = None if info is None else info.description
    arm = _arm_note(table, column)
    if description is None:
        return arm
    return description if arm is None else f"{description} [{arm}]"


def _arm_note(table: Table, column: Column) -> str | None:
    for group in table.splits:
        if column.name in group.columns:
            return f"the {column.logical.value} arm of `{group.field}`"
    return None


def statements(dialect: Dialect) -> list[str]:
    """Every statement of the seed schema, in the order it must be executed."""
    out: list[str] = list(dialect.prologue())
    for table in tables():
        out.extend(table_statements(dialect, table))
    return out


def emit(dialect: Dialect) -> str:
    """The schema as a file, with the header that says not to edit it."""
    header = "\n".join(
        (
            "-- openFerment seed schema — GENERATED, do not edit.",
            "--",
            "-- Derived from the Pydantic models in",
            "-- packages/core/openferment_core/schema/. A field added to a model becomes a",
            "-- column here the next time this is emitted; a column edited here is a column",
            "-- that disagrees with the model, which is the failure this migration exists to",
            '-- remove (CLAUDE.md, "Do not hand-maintain a type in both").',
            "--",
            f"-- Regenerate:  python3 packages/core/seed/cli.py emit --dialect {dialect.name}",
            f"-- Dialect:     {dialect.name}",
            "",
        )
    )
    return header + "\n" + "".join(f"{s};\n\n" for s in statements(dialect)).rstrip() + "\n"
