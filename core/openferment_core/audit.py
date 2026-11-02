"""The audit log (OF-BLD-015 §7.3; execution prompt §7.3): every write a model
makes, and every proposal a person carries out or dismisses, one row each in
the `audit` table, under the project it was made in.

Rows are only ever added: a row that was written stays. A row says who did
it: `agent` is `model` or `person`; `who` is the model id or the person's
name; a model's row carries the effort and the ask it was part of. The
module, the action, the target and the state the write left behind are what
a review reads (§7.R).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select

from . import db, projects
from .db import models as t
from .models import AuditEntry

MAX_READ = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
) -> AuditEntry:
    """Add one row, in the transaction under way when there is one, so a write
    and its row commit together."""
    entry = AuditEntry(at=_now(), agent=agent, who=who, module=module, action=action, state=state, target=target,  # type: ignore[arg-type]
                       askId=ask_id or None, effort=effort, detail=detail or {})
    async with db.session() as s:
        await s.execute(
            insert(t.audit).values(
                project_id=project_id, agent=entry.agent, who=entry.who, module=entry.module,
                action=entry.action, state=entry.state, target=entry.target, body=entry.model_dump(mode="json"),
            )
        )
    return entry


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
) -> AuditEntry:
    """Add one row under the current project."""
    return db.run(add(projects.current(), agent=agent, who=who, module=module, action=action, state=state,
                      target=target, ask_id=ask_id, effort=effort, detail=detail))


async def _read(project_id: str, limit: int) -> list[AuditEntry]:
    async with db.session() as s:
        bodies = (
            await s.execute(
                select(t.audit.c.body).where(t.audit.c.project_id == project_id).order_by(t.audit.c.seq.desc()).limit(limit)
            )
        ).scalars().all()
    return [AuditEntry.model_validate(b) for b in reversed(bodies)]


def read(limit: int = MAX_READ) -> list[AuditEntry]:
    """The current project's newest `limit` rows, newest last."""
    return db.run(_read(projects.current(), max(0, limit)))
