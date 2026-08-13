"""How the two databases spell what `columns.py` derived.

There is one schema. There are two renderers for it, and the split is the point:
which tables exist, which columns they have, what is nullable and what is
checked are decided once, from the models; a dialect only chooses words.

**Postgres is the product.** It is what `data/corpus/*.json` is loaded into and
what the "api" backend of `src/data/source.ts` would read back out.

**SQLite exists so the generator can be run rather than admired.** There is no
Postgres server in this environment, so a generated Postgres script can be
parsed and linted but not executed, and "the DDL is syntactically valid" is a
much weaker claim than "the DDL creates tables that accept the corpus and refuse
an UPDATE". Everything that is genuinely portable — the tables, the columns, the
nullability, the CHECK constraints, the foreign key, the supersession view, and
the append-only triggers — is executed against SQLite in the test suite, so that
the *logic* of the schema is proven even where its Postgres *spelling* is only
checked. The report at the end of this phase says exactly which is which; see
`tests/test_seed.py`.

Where the two genuinely differ, the difference is confined to this file:

    JSONB              vs  TEXT holding the same JSON bytes
    BIGINT … IDENTITY  vs  INTEGER PRIMARY KEY AUTOINCREMENT
    TIMESTAMPTZ/now()  vs  TEXT/CURRENT_TIMESTAMP
    a plpgsql trigger  vs  RAISE(ABORT) in a trigger body
    REVOKE …           vs  nothing; SQLite has no privileges

The last line is the honest one: the SQLite mirror cannot represent the
privilege half of the append-only defence, so the SQLite tests prove the trigger
half only.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from .columns import Column, Logical

__all__ = ["POSTGRES", "SQLITE", "Dialect"]

_APPEND_ONLY_MESSAGE = (
    "is append-only. A correction is a new row that supersedes an earlier one; "
    "UPDATE and DELETE are not how this table changes."
)


class Dialect:
    """Base renderer. Subclasses supply words, never structure."""

    name: str = "generic"
    types: ClassVar[dict[Logical, str]] = {}
    param: str = "?"
    json_param: str = "?"
    supports_returning: bool = False
    supports_truncate: bool = False
    #: `COMMENT ON` carries every `Field(description=...)` into the database
    #: catalogue. Invariant 5 in CLAUDE.md — the docstrings port with the types
    #: — and this is where they land once the type is a table.
    supports_comments: bool = False

    # ── identifiers and literals ───────────────────────────────────────

    def quote(self, ident: str) -> str:
        """Every identifier this package emits is quoted.

        `AuditEvent.from_` becomes the column `"from"`, and `from` is a reserved
        word in every SQL dialect there is. Quoting one identifier because it
        happens to be reserved means keeping a list of reserved words and being
        wrong about it later; quoting all of them is mechanical and cannot rot.
        It also keeps `"range"`, `"index"`, `"value"` and `"to"` out of the same
        argument.
        """
        return '"' + ident.replace('"', '""') + '"'

    def literal(self, value: str | int) -> str:
        if isinstance(value, int):
            return str(value)
        return "'" + value.replace("'", "''") + "'"

    # ── types ──────────────────────────────────────────────────────────

    def type_of(self, column: Column) -> str:
        return self.types[column.logical]

    def default_of(self, column: Column) -> str | None:
        if column.sql_default is None:
            return None
        if column.sql_default == "now":
            return self.now()
        raise ValueError(f"unknown default {column.sql_default!r}")

    def now(self) -> str:
        raise NotImplementedError

    def identity_clause(self, column: Column) -> str:
        """The whole column definition for an identity primary key.

        Rendered by the dialect rather than assembled by `ddl.py` because
        SQLite's is not a modifier on a type — `INTEGER PRIMARY KEY
        AUTOINCREMENT` is the entire declaration and the primary key cannot be
        stated separately.
        """
        raise NotImplementedError

    def json_array_length(self, expr: str) -> str:
        raise NotImplementedError

    # ── append-only ────────────────────────────────────────────────────

    def prologue(self) -> list[str]:
        """Statements that must precede the tables (Postgres: the trigger fn)."""
        return []

    def append_only_statements(self, table: str) -> list[str]:
        raise NotImplementedError

    def privilege_statements(self, table: str) -> list[str]:
        return []

    # ── values ─────────────────────────────────────────────────────────

    def pack_json(self, value: Any) -> str:
        """A JSON column's parameter, as text, for both dialects.

        `ensure_ascii=False` because the corpus is full of characters that
        matter — µ in µg, ⁻¹ in g L⁻¹, § in a curation reference — and escaping
        them would still round-trip but would make every stored document
        unreadable in a psql session.
        """
        return json.dumps(value, ensure_ascii=False, sort_keys=False)

    def unpack_json(self, value: Any) -> Any:
        """Undo `pack_json`, tolerating a driver that already parsed it.

        `psycopg` hands back a parsed object for a `jsonb` column; `sqlite3`
        hands back the text it was given.
        """
        if isinstance(value, str):
            return json.loads(value)
        return value


class _Postgres(Dialect):
    name = "postgres"
    types: ClassVar[dict[Logical, str]] = {
        Logical.TEXT: "TEXT",
        Logical.SMALLINT: "SMALLINT",
        Logical.BIGINT: "BIGINT",
        Logical.DOUBLE: "DOUBLE PRECISION",
        Logical.BOOLEAN: "BOOLEAN",
        Logical.JSON: "JSONB",
        Logical.TIMESTAMP: "TIMESTAMPTZ",
    }
    param = "%s"
    #: An explicit cast rather than trusting the driver to infer `jsonb` from a
    #: Python string. Both psycopg2 and psycopg3 usually get this right; "usually"
    #: is not a thing to find out about in production against a server this phase
    #: cannot test against.
    json_param = "CAST(%s AS JSONB)"
    supports_returning = True
    supports_truncate = True
    supports_comments = True

    def now(self) -> str:
        return "now()"

    def identity_clause(self, column: Column) -> str:
        return f"{self.quote(column.name)} BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

    def json_array_length(self, expr: str) -> str:
        return f"jsonb_array_length({expr})"

    def prologue(self) -> list[str]:
        return [
            "CREATE FUNCTION of_append_only() RETURNS trigger\n"
            "LANGUAGE plpgsql AS $of_append_only$\n"
            "BEGIN\n"
            "    RAISE EXCEPTION USING\n"
            "        ERRCODE = 'P0001',\n"
            f"        MESSAGE = format('openFerment: %I {_APPEND_ONLY_MESSAGE}', TG_TABLE_NAME),\n"
            "        HINT    = 'INSERT the corrected row with supersedes set to the "
            "row_id it replaces.';\n"
            "END;\n"
            "$of_append_only$"
        ]

    def append_only_statements(self, table: str) -> list[str]:
        t = self.quote(table)
        return [
            f"CREATE TRIGGER {self.quote(table + '_append_only')}\n"
            f"BEFORE UPDATE OR DELETE ON {t}\n"
            "FOR EACH ROW EXECUTE FUNCTION of_append_only()",
            # TRUNCATE fires no row-level trigger, so without this statement-level
            # one the table could be emptied in a single command.
            f"CREATE TRIGGER {self.quote(table + '_append_only_truncate')}\n"
            f"BEFORE TRUNCATE ON {t}\n"
            "FOR EACH STATEMENT EXECUTE FUNCTION of_append_only()",
        ]

    def privilege_statements(self, table: str) -> list[str]:
        # Defence in depth, not the defence. The trigger is what enforces the
        # rule.
        #
        # Do not read this as stopping a role from being GRANTED the ability to
        # try — REVOKE removes privileges currently held and places no
        # constraint on a future GRANT. On the empty database this script
        # builds it removes nothing at all, because PostgreSQL grants PUBLIC no
        # privileges on tables by default. It earns its place only on a
        # database where something has already granted them.
        #
        # Nor does it cover `records_current`: that view is auto-updatable, and
        # permission checks on the base table run as the view's owner, so a role
        # granted DELETE on the view is not subject to this revoke. The trigger
        # is what stops that too — which is the point of the first line.
        #
        # And nothing here stops the table's owner from dropping the trigger. No
        # database can: a schema cannot defend itself against its own owner.
        return [f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE {self.quote(table)} FROM PUBLIC"]


class _SQLite(Dialect):
    name = "sqlite"
    types: ClassVar[dict[Logical, str]] = {
        Logical.TEXT: "TEXT",
        Logical.SMALLINT: "INTEGER",
        Logical.BIGINT: "INTEGER",
        Logical.DOUBLE: "REAL",
        # SQLite has no boolean type; it stores 0/1 and Pydantic reads them back
        # as bools on the way into the model.
        Logical.BOOLEAN: "INTEGER",
        Logical.JSON: "TEXT",
        Logical.TIMESTAMP: "TEXT",
    }
    param = "?"
    json_param = "?"
    supports_returning = False
    supports_truncate = False

    def now(self) -> str:
        return "CURRENT_TIMESTAMP"

    def identity_clause(self, column: Column) -> str:
        return f"{self.quote(column.name)} INTEGER PRIMARY KEY AUTOINCREMENT"

    def json_array_length(self, expr: str) -> str:
        return f"json_array_length({expr})"

    def append_only_statements(self, table: str) -> list[str]:
        message = self.literal(f"openFerment: {table} {_APPEND_ONLY_MESSAGE}")
        out: list[str] = []
        for action in ("UPDATE", "DELETE"):
            name = self.quote(f"{table}_append_only_{action.lower()}")
            out.append(
                f"CREATE TRIGGER {name}\n"
                f"BEFORE {action} ON {self.quote(table)}\n"
                "BEGIN\n"
                f"    SELECT RAISE(ABORT, {message});\n"
                "END"
            )
        return out


POSTGRES: Dialect = _Postgres()
SQLITE: Dialect = _SQLite()
