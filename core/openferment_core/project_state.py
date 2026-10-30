"""What a project keeps of the work done in its pages (execution prompt §5.5,
stage 2; ADR-001, ADR-005).

Depositions, measured evidence, runbooks adopted from a draft and every
runbook's lock, the parameter panel's overrides, the fits chosen for a
scenario's inputs, the scenarios made in Proforma, the trains built in
pureOS's Builder, and Postdoc's Live conversations. Until stage 2 each was the
browser's own, in IndexedDB, so two devices disagreed about one project. Each
is now rows of its table under the project; a page loads them all from
`GET /api/state` and writes one at a time, and the browser keeps only the
writes the service has not yet acknowledged.

A row holds what the page sent, in the shape the page's types give it
(`src/data/types.ts`; stage 7 generates those types from Pydantic models).
What is checked here is what makes a row a row: a known kind, an id of the
right shape that the value repeats, a value of the kind's shape, a size a
page can send. The rules that act on the content run where they always ran.

What a person made, locked or measured stays: a deposition, a measurement
and a lock are never taken back through here. Making, locking and taking back
are audited; the many saves of one deposition while it runs at the bench are
the same row moving and are not.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import audit, db, projects
from .db import models as t
from .db import rows

# An id as the pages make them, and an override scope (`pureos:unit:tr-1:inlet`).
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:|-]{0,199}$")
MAX_BYTES = 2_000_000


class StateRefused(ValueError):
    """A write that is not a row of its kind, in words."""


@dataclass(frozen=True)
class Kind:
    name: str
    table: Any
    module: str
    # Whether a person may take a row back (a deposition, a measurement and a lock stay).
    removable: bool = True
    # Lookup columns from the value.
    columns: Callable[[dict[str, Any]], dict[str, Any]] = field(default=lambda value: {})
    # The rows of the table this kind reads, beyond the project.
    where: Callable[[], list[Any]] = field(default=lambda: [])


def _title(value: dict[str, Any]) -> dict[str, Any]:
    turns = value.get("turns") or []
    first = turns[0] if turns and isinstance(turns[0], dict) else {}
    return {"title": str(first.get("question") or "")[:200]}


KINDS: dict[str, Kind] = {
    k.name: k
    for k in (
        Kind("depositions", t.depositions, "runbooks", removable=False,
             columns=lambda v: {"runbook_id": v.get("runbookId")}),
        Kind("measuredEvidence", t.measured_evidence, "runbooks", removable=False),
        Kind("runbooks", t.runbooks, "runbooks"),
        Kind("fits", t.fits, "proforma"),
        Kind("scenarios", t.scenarios, "proforma", columns=lambda v: {"pinned": bool(v.get("pinned"))}),
        Kind("trains", t.trains, "pureos", columns=lambda v: {"kind": "made"},
             where=lambda: [t.trains.c.kind == "made"]),
        Kind("conversations", t.conversations, "home", columns=_title),
    )
}
# Two kinds keep their own tables' shapes: a lock is (runbook, hash, when),
# and the overrides of one scope are one row per key.
LOCKS, OVERRIDES = "runbookLocks", "overrides"
NAMES = (*KINDS, LOCKS, OVERRIDES)


def _checked(kind: str, item_id: str, value: Any) -> Any:
    if kind not in NAMES:
        raise StateRefused(f"{kind!r} is not something a project keeps; it keeps {', '.join(NAMES)}")
    if not ID.match(item_id):
        raise StateRefused(f"{item_id!r} is not an id: letters, digits and . _ : | -, at most 200")
    if len(json.dumps(value)) > MAX_BYTES:
        raise StateRefused(f"this {kind} row is over {MAX_BYTES // 1_000_000} MB; a page sends less")
    if kind == OVERRIDES:
        if not isinstance(value, list) or not all(isinstance(o, dict) and o.get("scope") == item_id and
                                                  isinstance(o.get("key"), str) and o["key"] for o in value):
            raise StateRefused(f"the overrides of {item_id} are a list, each naming this scope and its key")
        return value
    if kind == LOCKS:
        if not isinstance(value, dict) or not all(isinstance(value.get(k), str) and value[k] for k in ("lockedAt", "lockHash")):
            raise StateRefused("a lock names when it was made (lockedAt) and the hash it holds (lockHash)")
        try:
            datetime.fromisoformat(value["lockedAt"].replace("Z", "+00:00"))
        except ValueError:
            raise StateRefused(f"lockedAt {value['lockedAt']!r} is not a time") from None
        return value
    if not isinstance(value, dict):
        raise StateRefused(f"a {kind} row is an object")
    if kind == "fits":
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise StateRefused("a scenario's fits map each input to an artifact id")
        return value
    named = value.get("train", {}).get("id") if kind == "trains" and isinstance(value.get("train"), dict) else value.get("id")
    if named != item_id:
        raise StateRefused(f"the {kind} row says it is {named!r}, and was sent as {item_id!r}")
    return value


# ── reads ──────────────────────────────────────────────────────────────


async def _load(project_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    async with db.session() as s:
        for name, kind in KINDS.items():
            out[name] = await rows.bodies(s, kind.table, project_id, *kind.where())
        locks = (await s.execute(
            select(t.runbook_locks).where(t.runbook_locks.c.project_id == project_id).order_by(t.runbook_locks.c.created_at)
        )).all()
        out[LOCKS] = {r.runbook_id: {"lockedAt": r.locked_at.isoformat().replace("+00:00", "Z"), "lockHash": r.lock_hash}
                      for r in locks}
        overrides: dict[str, list[dict[str, Any]]] = {}
        for r in (await s.execute(
            select(t.overrides).where(t.overrides.c.project_id == project_id).order_by(t.overrides.c.created_at, t.overrides.c.key)
        )).all():
            overrides.setdefault(r.scope, []).append(r.body)
        out[OVERRIDES] = overrides
    # Fits and trains are keyed in the page by scenario and by train.
    out["fits"] = {f["id"]: f["byInput"] for f in out["fits"]}
    out["trains"] = {tr["train"]["id"]: tr for tr in out["trains"]}
    return out


def load() -> dict[str, Any]:
    """Everything the current project keeps of its pages, keyed as the page keeps it."""
    return db.run(_load(projects.current()))


# ── writes ─────────────────────────────────────────────────────────────


async def _held(s: AsyncSession, kind: str, project_id: str, item_id: str) -> bool:
    if kind == LOCKS:
        q = select(t.runbook_locks.c.runbook_id).where(t.runbook_locks.c.project_id == project_id,
                                                       t.runbook_locks.c.runbook_id == item_id)
    elif kind == OVERRIDES:
        q = select(t.overrides.c.key).where(t.overrides.c.project_id == project_id, t.overrides.c.scope == item_id)
    else:
        table = KINDS[kind].table
        q = select(table.c.id).where(table.c.project_id == project_id, table.c.id == item_id, *KINDS[kind].where())
    return (await s.execute(q.limit(1))).first() is not None


async def _put(project_id: str, kind: str, item_id: str, value: Any, by: str) -> None:
    async with db.session() as s:
        await db.lock(s, "state", project_id, kind, item_id)
        existed = await _held(s, kind, project_id, item_id)
        if kind == LOCKS:
            if existed:
                raise StateRefused(f"{item_id} is locked already; a lock is kept as it was made")
            await s.execute(insert(t.runbook_locks).values(
                project_id=project_id, runbook_id=item_id, lock_hash=value["lockHash"],
                locked_at=datetime.fromisoformat(value["lockedAt"].replace("Z", "+00:00")), created_by=by,
            ))
        elif kind == OVERRIDES:
            await s.execute(delete(t.overrides).where(t.overrides.c.project_id == project_id, t.overrides.c.scope == item_id))
            for o in value:
                await s.execute(insert(t.overrides).values(project_id=project_id, scope=item_id, key=o["key"], body=o,
                                                           created_by=str(o.get("by") or by)))
        else:
            k = KINDS[kind]
            body = {"id": item_id, "byInput": value} if kind == "fits" else value
            await rows.put(s, k.table, project_id, item_id, body, by=by, **k.columns(value))
        if not existed or kind == LOCKS:
            module = item_id.split(":", 1)[0] if kind == OVERRIDES and item_id.split(":", 1)[0] in ("proforma", "fermos", "pureos") \
                else (KINDS[kind].module if kind in KINDS else "runbooks")
            await audit.add(project_id, agent="person", who=by, module=module,
                            action="lock" if kind == LOCKS else f"keep_{kind}", state="locked" if kind == LOCKS else "kept",
                            target=item_id)


def put(kind: str, item_id: str, value: Any, by: str) -> Any:
    """Keep one row whole, or refuse it in words; what was kept."""
    checked = _checked(kind, item_id, value)
    db.run(_put(projects.current(), kind, item_id, checked, (by or "").strip() or "this browser"))
    return checked


async def _remove(project_id: str, kind: str, item_id: str, by: str) -> None:
    async with db.session() as s:
        await db.lock(s, "state", project_id, kind, item_id)
        if not await _held(s, kind, project_id, item_id):
            return
        if kind == OVERRIDES:
            await s.execute(delete(t.overrides).where(t.overrides.c.project_id == project_id, t.overrides.c.scope == item_id))
            module = item_id.split(":", 1)[0]
        else:
            await rows.drop(s, KINDS[kind].table, project_id, item_id)
            module = KINDS[kind].module
        await audit.add(project_id, agent="person", who=by,
                        module=module if module in ("proforma", "fermos", "pureos", "runbooks", "home") else "home",
                        action=f"remove_{kind}", state="removed", target=item_id)


def remove(kind: str, item_id: str, by: str) -> None:
    """Take one row back, a person's own undo. A deposition, a measurement
    and a lock stay; taking back what is not held is nothing."""
    if kind not in NAMES:
        raise StateRefused(f"{kind!r} is not something a project keeps; it keeps {', '.join(NAMES)}")
    if kind == LOCKS or (kind in KINDS and not KINDS[kind].removable):
        raise StateRefused(f"a {kind[:-1] if kind.endswith('s') else kind} is kept as it was made, and never taken back")
    if not ID.match(item_id):
        raise StateRefused(f"{item_id!r} is not an id")
    db.run(_remove(projects.current(), kind, item_id, (by or "").strip() or "this browser"))
