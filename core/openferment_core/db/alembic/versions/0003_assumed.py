"""`demo` renamed `assumed` in every stored row (ADR-006; execution prompt
§4.6, §13 item 5).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30

The provenance class alpha 1.0 called `demo` (a value resting on a named
person's assumption) is `assumed` from alpha 2.0 on: the same class under
its new name. Every row that names it is rewritten, so every reader reads
one vocabulary: each text column named `provenance`, and, in each JSON column
of the schema, the value of every key named `provenance`. Nothing else in a
row changes. An artifact whose output named the class has its output hash
computed again over the output as rewritten (in the canonical form
`artifacts.canonical` gives when this was written), so a replay compares like
with like. Artifact ids hash the inputs, which name no provenance, and a
runbook's lock hash covers its predictions' values and its measures, which
name none either; both stay as they are. The downgrade renames it back.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | Sequence[str] | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "openferment"
KEY = "provenance"


def _renamed(value: Any, old: str, new: str) -> Any:
    """`value` with every `provenance` key that holds `old` set to `new`."""
    if isinstance(value, dict):
        return {k: new if k == KEY and v == old else _renamed(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [_renamed(v, old, new) for v in value]
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _rename(old: str, new: str) -> None:
    bind = op.get_bind()
    found = bind.execute(sa.text(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = :schema AND (data_type IN ('json', 'jsonb') OR column_name = :key) "
        "ORDER BY table_name, ordinal_position"), {"schema": SCHEMA, "key": KEY}).all()
    tables: dict[str, list[tuple[str, str]]] = {}
    for table, column, kind in found:
        tables.setdefault(table, []).append((column, kind))
    for table, columns in tables.items():
        name = f'{SCHEMA}."{table}"'
        for column, kind in columns:
            if kind not in ("json", "jsonb"):
                bind.execute(sa.text(f'UPDATE {name} SET "{column}" = :new WHERE "{column}" = :old'),
                             {"old": old, "new": new})
        held = [c for c, kind in columns if kind in ("json", "jsonb")]
        if not held:
            continue
        # Only a row one of whose JSON columns holds the word is read.
        where = " OR ".join(f'CAST("{c}" AS text) LIKE CAST(:like AS text)' for c in held)
        listed = ", ".join(f'CAST("{c}" AS text) AS "{c}"' for c in held)
        rows = bind.execute(sa.text(f"SELECT CAST(ctid AS text) AS row_id, {listed} FROM {name} WHERE {where}"),
                            {"like": f'%"{old}"%'}).mappings().all()
        for row in rows:
            values = {}
            for c in held:
                if row[c] is None:
                    continue
                was = json.loads(row[c])
                now = _renamed(was, old, new)
                if now == was:
                    continue
                if table == "artifacts" and c == "body" and isinstance(now, dict) and now.get("output") != was.get("output"):
                    now["outputHash"] = hashlib.sha256(_canonical(now["output"]).encode("utf-8")).hexdigest()
                    values["output_hash"] = now["outputHash"]
                values[c] = now
            if not values:
                continue
            sets = ", ".join(
                f'"{c}" = CAST(CAST(:{c} AS text) AS {dict(columns)[c]})' if c in held else f'"{c}" = CAST(:{c} AS text)'
                for c in values)
            bind.execute(sa.text(f"UPDATE {name} SET {sets} WHERE ctid = CAST(CAST(:row_id AS text) AS tid)"),
                         {"row_id": row["row_id"],
                          **{c: (json.dumps(v, ensure_ascii=False) if c in held else v) for c, v in values.items()}})


def upgrade() -> None:
    _rename("demo", "assumed")


def downgrade() -> None:
    _rename("assumed", "demo")
