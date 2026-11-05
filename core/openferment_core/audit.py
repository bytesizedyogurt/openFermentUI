"""The audit log (OF-BLD-015 §7.3; execution prompt §7.3): every write a model
makes, and every proposal a person carries out or dismisses, one row each in
the `audit` table, under the project it was made in.

Rows are only ever added: a row that was written stays. A row says who did
it: `agent` is `model` or `person`; `who` is the model id or the person's
name; a model's row carries the effort and the ask it was part of. The
module, the action, the target and the state the write left behind are what
a review reads (§7.R).

A row's id is its place in the table (`seq`), written as a string of digits
(alpha 2.2 E.16): `add` answers the row under it, `read` serves every row
under it, and a tool call names the rows it wrote by it (`tools.run`, the
result's `auditIds`), collected by `written`. `read` takes the newest rows of
the project, narrowed by the action, the target and who, each matched as the
row names it.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select

from . import db, projects
from .db import models as t
from .models import AuditEntry, AuditRow

MAX_READ = 500

# The ids of the rows added while `written` is open, in the order they were
# added. A coroutine sent to the database loop (db.run) runs in a copy of its
# sender's context, so a row added there joins the list the sender opened.
_WRITTEN: ContextVar[list[str] | None] = ContextVar("openferment_audit_written", default=None)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def written() -> Iterator[list[str]]:
    """The ids of the rows added while the block runs, oldest first, wherever
    they are added: by `append`, or by `add` inside a store's own transaction
    (a proposal and its row). A block opened inside another hands its ids on
    to the outer one when it closes."""
    outer = _WRITTEN.get()
    ids: list[str] = []
    token = _WRITTEN.set(ids)
    try:
        yield ids
    finally:
        _WRITTEN.reset(token)
        if outer is not None:
            outer.extend(ids)


async def add(
    project_id: str,
    *,
    agent: str,
    who: str,
    module: str,
    action: str,
    state: str,
    target: str | None = None,
    ask_id: str | None = None,
    effort: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditRow:
    """Add one row, in the transaction under way when there is one, so a write
    and its row commit together; the row under its id."""
    entry = AuditEntry(at=_now(), agent=agent, who=who, module=module, action=action, state=state, target=target,  # type: ignore[arg-type]
                       askId=ask_id or None, effort=effort, detail=detail or {})
    async with db.session() as s:
        seq = (await s.execute(
            insert(t.audit).values(
                project_id=project_id, agent=entry.agent, who=entry.who, module=entry.module,
                action=entry.action, state=entry.state, target=entry.target, body=entry.model_dump(mode="json"),
            ).returning(t.audit.c.seq)
        )).scalar_one()
    row = AuditRow.model_validate({**entry.model_dump(), "id": str(seq)})
    collecting = _WRITTEN.get()
    if collecting is not None:
        collecting.append(row.id)
    return row


def append(
    *,
    agent: str,
    who: str,
    module: str,
    action: str,
    state: str,
    target: str | None = None,
    ask_id: str | None = None,
    effort: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditRow:
    """Add one row under the current project."""
    return db.run(add(projects.current(), agent=agent, who=who, module=module, action=action, state=state,
                      target=target, ask_id=ask_id, effort=effort, detail=detail))


async def _read(project_id: str, limit: int, action: str | None, target: str | None,
                who: str | None) -> list[AuditRow]:
    query = select(t.audit.c.seq, t.audit.c.body).where(t.audit.c.project_id == project_id)
    for column, value in ((t.audit.c.action, action), (t.audit.c.target, target), (t.audit.c.who, who)):
        if value:
            query = query.where(column == value)
    async with db.session() as s:
        found = (await s.execute(query.order_by(t.audit.c.seq.desc()).limit(limit))).all()
    return [AuditRow.model_validate({**body, "id": str(seq)}) for seq, body in reversed(found)]


async def _standing(project_id: str, ids: list[int]) -> set[int]:
    async with db.session() as s:
        found = (await s.execute(select(t.audit.c.seq).where(t.audit.c.project_id == project_id,
                                                              t.audit.c.seq.in_(ids)))).scalars()
        return set(found)


def standing(ids: list[str], project_id: str | None = None) -> list[str]:
    """The ids among `ids` whose rows the project's table holds (the project
    named, else the current one), in the order given: a row added in a
    transaction that was rolled back is gone, and its id is left out."""
    numbers = [int(i) for i in ids if i.isdigit()]
    if not numbers:
        return []
    held = db.run(_standing(project_id or projects.current(), numbers))
    return [i for i in ids if i.isdigit() and int(i) in held]


def read(limit: int = MAX_READ, *, action: str | None = None, target: str | None = None,
         who: str | None = None) -> list[AuditRow]:
    """The current project's newest `limit` rows, newest last; given an
    action, a target or who, the newest `limit` rows that name each given one
    exactly."""
    return db.run(_read(projects.current(), max(0, limit), action, target, who))
