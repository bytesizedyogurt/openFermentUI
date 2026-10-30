"""Projects (ADR-005; execution prompt §4.5).

A project scopes documents, records, flowsheets, runs, artifacts, runbooks,
depositions, conversations and Guild entries: every table carries
`project_id`, and every store call acts within the project `current()` names.

A request names its project in the `X-OpenFerment-Project` header or, where a
header cannot be sent (an event stream), in `?project=`; the service sets it
for the request (api.py) and refuses one that names a project it does not
hold. A command or the MCP server names it once, in OPENFERMENT_PROJECT. A
store call that names none is refused in words. Who may open a project is a
stub until accounts exist (§13 question 9): `project_members` has its table
and nothing reads it yet.

`projects` imports `db` and `models` and nothing else of the service (§7.2).
"""
from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select

from .. import db
from ..db import models as t
from ..models import PROJECT_ID, AuditEntry, Project, ProjectCreate

HEADER = "X-OpenFerment-Project"
QUERY = "project"
ENV = "OPENFERMENT_PROJECT"
_ID = re.compile(PROJECT_ID)


class ProjectRequired(LookupError):
    """A store call that names no project."""


class ProjectRefused(ValueError):
    """A project that cannot be made as asked."""


_UNSET: Any = object()
_CURRENT: ContextVar[Any] = ContextVar("openferment_project", default=_UNSET)


def current() -> str:
    """The project this request or command acts in."""
    value = _CURRENT.get()
    if value is _UNSET:
        value = os.environ.get(ENV, "").strip() or None
    if not value:
        raise ProjectRequired(
            f"This names no project. A request sends the {HEADER} header (or ?{QUERY}= on an event "
            f"stream); a command sets {ENV}."
        )
    return str(value)


@contextmanager
def using(project_id: str | None) -> Iterator[None]:
    """Act in `project_id` inside the block. None names none: a store call
    inside is refused rather than falling back to OPENFERMENT_PROJECT."""
    token = _CURRENT.set(project_id)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def valid_id(value: str) -> bool:
    return bool(_ID.match(value))


def slug(name: str) -> str:
    """The id a name makes: `Corn stover ethanol` gives `corn-stover-ethanol`."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    made = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:63].strip("-")
    return made or "project"


def _project(row: Any) -> Project:
    return Project(
        id=row.id,
        name=row.name,
        description=row.description,
        createdBy=row.created_by,
        createdAt=row.created_at.isoformat(),
    )


async def held(project_id: str) -> bool:
    """Whether the database holds `project_id`."""
    async with db.session() as s:
        return (await s.execute(select(t.projects.c.id).where(t.projects.c.id == project_id))).first() is not None


async def _get(project_id: str) -> Project | None:
    async with db.session() as s:
        row = (await s.execute(select(t.projects).where(t.projects.c.id == project_id))).first()
    return _project(row) if row else None


async def _listed() -> list[Project]:
    async with db.session() as s:
        rows = (await s.execute(select(t.projects).order_by(t.projects.c.created_at, t.projects.c.id))).all()
    return [_project(r) for r in rows]


async def _create(asked: ProjectCreate) -> Project:
    name, by = asked.name.strip(), asked.by.strip()
    if not name or not by:
        raise ProjectRefused("a project needs a name, and the name of the person making it")
    async with db.session() as s:
        await db.lock(s, "projects")
        if asked.id is not None:
            pid = asked.id
            if (await s.execute(select(t.projects.c.id).where(t.projects.c.id == pid))).first():
                raise ProjectRefused(f"a project named {pid!r} already exists")
        else:
            base = slug(name)
            taken = set((await s.execute(select(t.projects.c.id).where(t.projects.c.id.startswith(base)))).scalars())
            pid, n = base, 2
            while pid in taken:
                suffix = f"-{n}"
                pid, n = base[: 63 - len(suffix)] + suffix, n + 1
        await s.execute(
            insert(t.projects).values(id=pid, name=name, description=asked.description.strip(), created_by=by)
        )
        entry = AuditEntry(
            at=datetime.now(timezone.utc).isoformat(), agent="person", who=by, module="home",
            action="create_project", state="created", target=pid,
        )
        await s.execute(
            insert(t.audit).values(
                project_id=pid, agent=entry.agent, who=entry.who, module=entry.module, action=entry.action,
                state=entry.state, target=entry.target, body=entry.model_dump(mode="json"),
            )
        )
        row = (await s.execute(select(t.projects).where(t.projects.c.id == pid))).one()
    return _project(row)


def get(project_id: str) -> Project | None:
    return db.run(_get(project_id))


def listed() -> list[Project]:
    """Every project, oldest first."""
    return db.run(_listed())


def create(asked: ProjectCreate) -> Project:
    """Make a project, audited as its maker's; refused when the id is taken."""
    return db.run(_create(asked))
