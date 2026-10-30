"""Rows kept whole by id (ADR-001, Implementation).

Most stores keep a project's entities as rows of a `_scoped` table: the key
`(project_id, id)`, a few lookup columns, and the Pydantic model as `body`.
These are the reads and writes they share, so every store writes a row the
same way: an upsert that keeps `created_by` and `created_at` from the first
write and moves `updated_at` (where the table has it) on every later one.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Table, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement


async def bodies(
    s: AsyncSession, table: Table, project_id: str, *where: ColumnElement[bool], order: Iterable[Any] = ()
) -> list[dict[str, Any]]:
    """The bodies of a project's rows, oldest first unless `order` says otherwise."""
    q = select(table.c.body).where(table.c.project_id == project_id, *where)
    q = q.order_by(*(order or (table.c.created_at, table.c.id)))
    return list((await s.execute(q)).scalars())


async def body(s: AsyncSession, table: Table, project_id: str, row_id: str, *, for_update: bool = False) -> dict[str, Any] | None:
    """One row's body, or None. `for_update` holds the row until the transaction ends."""
    q = select(table.c.body).where(table.c.project_id == project_id, table.c.id == row_id)
    if for_update:
        q = q.with_for_update()
    return (await s.execute(q)).scalar_one_or_none()


async def put(
    s: AsyncSession,
    table: Table,
    project_id: str,
    row_id: str,
    value: Mapping[str, Any],
    *,
    by: str,
    **columns: Any,
) -> None:
    """Write one row whole: its body and lookup `columns`. A row that exists
    keeps who made it and when; `updated_at`, where the table has it, moves."""
    values = {"project_id": project_id, "id": row_id, "body": dict(value), "created_by": by, **columns}
    stmt = insert(table).values(**values)
    changes: dict[str, Any] = {"body": stmt.excluded.body, **{k: stmt.excluded[k] for k in columns}}
    if "updated_at" in table.c:
        changes["updated_at"] = func.clock_timestamp()
    await s.execute(stmt.on_conflict_do_update(index_elements=[table.c.project_id, table.c.id], set_=changes))


async def drop(s: AsyncSession, table: Table, project_id: str, row_id: str) -> None:
    """Remove one row. Only for what a person's own undo takes back; a record
    of what was decided or done is never removed."""
    await s.execute(delete(table).where(table.c.project_id == project_id, table.c.id == row_id))
