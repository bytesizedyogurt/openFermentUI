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
page can send, and, once a runbook is locked, predictions and measures that
are the ones its lock froze (runbook_lock.py computes the digest the page
writes). The rules that act on the content run where they always ran.

What a person made, locked, measured or asked stays: a deposition, a
measurement, a lock and a conversation are never taken back through here.
Making, locking and taking back are audited; the many saves of one deposition
while it runs at the bench are the same row moving and are not, and every
write a closed deposition accepts is.

A deposition is the bench's record, and a run may rest on one of its
readings (measurements.py), so a write to a kept deposition is held to what
the bench does (`deposition_refusal`): readings and observations are
appended, each kept as it was taken (a correction is a new reading, the
bench's `amendEntry`), a read-back moves `confirmed` from false to true, the
state moves from staged to running to closed, and a reconciliation stays as
it was made. Closing stops new readings, new observations and new sample
times. Every other change is refused in words.

A Live conversation is Postdoc's own record (postdoc/conversations.py),
which a page's write is laid onto.
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
from .basis import EstimateRefused, refuse_estimates
from .db import models as t
from .db import rows
from .postdoc import conversations as _conversations
from .runbook_lock import frozen_as

# An id as the pages make them, and an override scope (`pureos:unit:tr-1:inlet`).
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:|-]{0,199}$")
MAX_BYTES = 2_000_000
# Who a row's maker is when the page sent no name: a browser with no person
# set in Settings (src/store.ts `decidedBy`). A reading kept under it names
# nobody, and no run takes it as a measurement (measurements.py).
UNNAMED = "this browser"

# The stages a deposition moves through at the bench, in order (src/store.ts).
DEPOSITION_STATES = ("staged", "running", "closed")
# What a deposition, each of its readings and each of its observations keep
# from the write that first held them (`deposition_refusal`).
DEPOSITION_FIELDS = ("runbookId", "protocolId", "startedAt")
ENTRY_FIELDS = ("measureId", "stepId", "at", "value", "unit", "raw")
OBSERVATION_FIELDS = ("stepId", "at", "raw")


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


KINDS: dict[str, Kind] = {
    k.name: k
    for k in (
        Kind("depositions", t.depositions, "runbooks", removable=False,
             columns=lambda v: {"runbook_id": v.get("runbookId")}),
        Kind("measuredEvidence", t.measured_evidence, "runbooks", removable=False),
        Kind("runbooks", t.runbooks, "runbooks"),
        Kind("fits", t.fits, "proforma"),
        Kind("scenarios", t.scenarios, "proforma", columns=lambda v: {"pinned": bool(v.get("pinned")), "kind": "proforma"},
             where=lambda: [t.scenarios.c.kind == "proforma"]),
        Kind("trains", t.trains, "pureos", columns=lambda v: {"kind": "made"},
             where=lambda: [t.trains.c.kind == "made"]),
    )
}
# A deposition and a measurement are records of the bench: no model's
# estimate enters them (ADR-006).
RECORD_KINDS = ("depositions", "measuredEvidence")
# Three kinds keep their own tables' shapes: a lock is (runbook, hash, when),
# the overrides of one scope are one row per key, and a Live conversation is
# Postdoc's own, kept as a conversation and its turns (postdoc/conversations.py):
# a page's write is laid onto what the service keeps, and a load reads it back
# whole.
LOCKS, OVERRIDES, CONVERSATIONS = "runbookLocks", "overrides", "conversations"
NAMES = (*KINDS, LOCKS, OVERRIDES, CONVERSATIONS)
# What a load carries beside the rows: who deposited each deposition, by id.
# The service writes it from the rows' makers; no page sends it.
MAKERS = "depositedBy"


def _checked(kind: str, item_id: str, value: Any) -> Any:
    if kind not in NAMES:
        raise StateRefused(f"{kind!r} is not something a project keeps; it keeps {', '.join(NAMES)}")
    if not ID.match(item_id):
        raise StateRefused(f"{item_id!r} is not an id: letters, digits and . _ : | -, at most 200")
    if len(json.dumps(value)) > MAX_BYTES:
        raise StateRefused(f"this {kind} row is over {MAX_BYTES // 1_000_000} MB; a page sends less")
    if kind in RECORD_KINDS:
        try:
            refuse_estimates(value, f"a project's {kind}")
        except EstimateRefused as e:
            raise StateRefused(str(e)) from None
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


def _listed(body: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [x for x in body.get(key) or [] if isinstance(x, dict)]


def _appended(item_id: str, what: str, before: list[dict[str, Any]], after: list[dict[str, Any]],
              fields: tuple[str, ...]) -> str | None:
    """Why `after` is no append to `before`, a deposition's readings or its
    observations: each kept one stays, in the order it was taken, with the
    fields it was taken with; None when every one does."""
    held = [x.get("id") for x in before]
    sent = [x.get("id") for x in after]
    missing = [str(i) for i in held if i not in sent]
    if missing:
        return (f"{item_id} keeps every {what} it was given, and this write leaves out {', '.join(missing)}; a "
                f"{what} is corrected by a new one")
    if sent[: len(held)] != held:
        return f"{item_id} keeps its {what}s in the order they were taken, and this write moves them"
    for old, new in zip(before, after):
        for f in fields:
            if old.get(f) != new.get(f):
                return (f"{item_id}: {what} {old.get('id')} keeps the {f} it was taken with ({old.get(f)!r}), and this "
                        f"write sets {new.get(f)!r}; a correction is a new {what}")
    return None


def deposition_refusal(item_id: str, before: dict[str, Any], after: dict[str, Any]) -> str | None:
    """Why a write of deposition `item_id` cannot stand over the row the
    project keeps (`before`), in words; None when it can. The write may add
    readings and observations while the deposition is open, confirm a
    reading a person read back, give an open deposition's readings their
    sample times, move its state forward, structure an observation, name
    each series' role, and reconcile it once. Everything else of the record
    stays as it was kept (the module's docstring)."""
    states = DEPOSITION_STATES
    was, now = before.get("state"), after.get("state")
    if was in states and (now not in states or states.index(now) < states.index(was)):
        return (f"{item_id} is {was}, and a deposition moves from staged to running to closed; this write makes it "
                f"{now!r}")
    for f in DEPOSITION_FIELDS:
        if f in before and before.get(f) != after.get(f):
            return f"{item_id} keeps the {f} it was made with ({before.get(f)!r}), and this write sets {after.get(f)!r}"
    if before.get("closedAt") is not None and before.get("closedAt") != after.get("closedAt"):
        return f"{item_id} was closed at {before.get('closedAt')}, and a close stays as it was made"
    old_entries, new_entries = _listed(before, "entries"), _listed(after, "entries")
    why = (_appended(item_id, "reading", old_entries, new_entries, ENTRY_FIELDS)
           or _appended(item_id, "observation", _listed(before, "observations"), _listed(after, "observations"),
                        OBSERVATION_FIELDS))
    if why:
        return why
    for old, new in zip(old_entries, new_entries):
        if old.get("confirmed") is True and new.get("confirmed") is not True:
            return f"{item_id}: reading {old.get('id')} was read back and confirmed, and a confirmation stays"
    if before.get("reconciliation") is not None and before.get("reconciliation") != after.get("reconciliation"):
        return f"{item_id} was reconciled, and a reconciliation stays as it was made"
    if was == "closed":
        if len(new_entries) > len(old_entries) or len(_listed(after, "observations")) > len(_listed(before, "observations")):
            return (f"{item_id} is closed, and closing stops new readings and observations; a new reading belongs in "
                    "a new deposition")
        if (before.get("sampleTimes") or {}) != (after.get("sampleTimes") or {}):
            return f"{item_id} is closed, and its readings keep the sample times they had when it closed"
        if before.get("operatorId") != after.get("operatorId"):
            return f"{item_id} is closed, and it keeps the operator it closed with"
    return None


# ── reads ──────────────────────────────────────────────────────────────


async def _locks(s: AsyncSession, project_id: str) -> dict[str, dict[str, str]]:
    locks = (await s.execute(
        select(t.runbook_locks).where(t.runbook_locks.c.project_id == project_id).order_by(t.runbook_locks.c.created_at)
    )).all()
    return {r.runbook_id: {"lockedAt": r.locked_at.isoformat().replace("+00:00", "Z"), "lockHash": r.lock_hash}
            for r in locks}


async def _overrides(s: AsyncSession, project_id: str, scope: str | None = None) -> dict[str, list[dict[str, Any]]]:
    q = select(t.overrides).where(t.overrides.c.project_id == project_id)
    if scope is not None:
        q = q.where(t.overrides.c.scope == scope)
    out: dict[str, list[dict[str, Any]]] = {}
    for r in (await s.execute(q.order_by(t.overrides.c.created_at, t.overrides.c.key))).all():
        out.setdefault(r.scope, []).append(r.body)
    return out


async def _load(project_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    async with db.session() as s:
        for name, kind in KINDS.items():
            out[name] = await rows.bodies(s, kind.table, project_id, *kind.where())
        out[LOCKS] = await _locks(s, project_id)
        out[OVERRIDES] = await _overrides(s, project_id)
    out[CONVERSATIONS] = [c.model_dump(mode="json") for c in await _conversations._listed(project_id)]
    # Fits and trains are keyed in the page by scenario and by train.
    out["fits"] = {f["id"]: f["byInput"] for f in out["fits"]}
    out["trains"] = {tr["train"]["id"]: tr for tr in out["trains"]}
    # Who deposited each deposition (its row's maker, who first kept it): the
    # person a measurement resting on one of its readings names.
    out[MAKERS] = {str(body.get("id")): maker for body, maker in await _deposited(project_id, None)
                   if isinstance(body, dict) and body.get("id")}
    return out


def load() -> dict[str, Any]:
    """Everything the current project keeps of its pages, keyed as the page
    keeps it, and who deposited each deposition (`depositedBy`)."""
    return db.run(_load(projects.current()))


async def _kept(project_id: str, kind: str) -> list[Any]:
    k = KINDS[kind]
    async with db.session() as s:
        out = await rows.bodies(s, k.table, project_id, *k.where())
        if kind == "runbooks":
            frozen = await _locks(s, project_id)
            out = [{**b, **frozen.get(b.get("id"), {})} for b in out]
    return out


def kept(kind: str) -> list[Any]:
    """The rows of one kind the current project keeps, oldest first, as its
    pages keep them; a runbook with its lock when it has one. What the
    service's own readers see of a project's work: Proforma's scenarios, the
    fits chosen for them, and the module reads."""
    if kind not in KINDS:
        raise StateRefused(f"{kind!r} is not a kind of row the project keeps; the kinds are {', '.join(KINDS)}")
    return db.run(_kept(projects.current(), kind))


async def _deposited(project_id: str, deposition_id: str | None) -> list[tuple[dict[str, Any], str]]:
    q = select(t.depositions.c.body, t.depositions.c.created_by).where(t.depositions.c.project_id == project_id)
    if deposition_id is not None:
        q = q.where(t.depositions.c.id == deposition_id)
    async with db.session() as s:
        found = (await s.execute(q.order_by(t.depositions.c.created_at, t.depositions.c.id))).all()
    return [(r.body, r.created_by) for r in found]


def deposited(deposition_id: str | None = None) -> list[tuple[dict[str, Any], str]]:
    """The depositions the current project keeps, oldest first, each as its
    page keeps it beside the person who deposited it (the row's maker, who
    first kept it); with `deposition_id`, that one alone, or none. What a
    measurement is looked up in (measurements.py)."""
    return db.run(_deposited(projects.current(), deposition_id))


async def _scope_overrides(project_id: str, scope: str) -> list[dict[str, Any]]:
    async with db.session() as s:
        return (await _overrides(s, project_id, scope)).get(scope, [])


def overrides_of(scope: str) -> list[dict[str, Any]]:
    """The overrides the current project keeps for one scope
    (`proforma:<scenario id>`), each a person's assumption or a model's
    estimate as the parameter panel wrote it."""
    return db.run(_scope_overrides(projects.current(), scope))


def run_request(scenario: dict[str, Any], by: str = "") -> Any:
    """A run of a Proforma scenario the project keeps, as its page sends it,
    asked for by `by`: the flowsheet and the parts a composite is built
    from, the values a person set on its page (the overrides the project
    keeps for its scope, each sent as the typed input its parameter's unit
    names, proforma.inputs_of), and the fermOS fits chosen for its inputs,
    each read from the project's rows. No value is typed here. A kept
    override that cannot be sent as an input (one that says no day, or
    names no one) is refused in words (proforma.ScenarioRefused)."""
    from pydantic import ValidationError

    from . import proforma
    from .models import Override, ProformaRunRequest

    sid = scenario["id"]
    overrides = [Override.model_validate(o) for o in overrides_of(f"proforma:{sid}")]
    try:
        inputs = proforma.inputs_of(scenario["modelId"], overrides)
    except ValidationError as e:
        said = "; ".join(str(err.get("msg", "")).removeprefix("Value error, ") for err in e.errors())
        raise proforma.ScenarioRefused(f"a value kept for {sid} cannot be sent with its run: {said}") from None
    fits = next((dict(f.get("byInput") or {}) for f in kept("fits") if f.get("id") == sid), {})
    return ProformaRunRequest(scenarioId=sid, flowsheet=scenario["modelId"], inputs=inputs, fits=fits,
                              vessel=scenario.get("vessel"), trainRun=scenario.get("trainRun"), by=by)


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


async def _frozen(s: AsyncSession, project_id: str, runbook_id: str) -> str | None:
    """The digest a runbook's lock froze, or None while it is unlocked."""
    q = select(t.runbook_locks.c.lock_hash).where(t.runbook_locks.c.project_id == project_id,
                                                  t.runbook_locks.c.runbook_id == runbook_id)
    return (await s.execute(q.limit(1))).scalar()


async def _stored(s: AsyncSession, project_id: str, deposition_id: str) -> dict[str, Any] | None:
    """The deposition the project keeps under `deposition_id`, or None."""
    q = select(t.depositions.c.body).where(t.depositions.c.project_id == project_id, t.depositions.c.id == deposition_id)
    body = (await s.execute(q.limit(1))).scalar()
    return body if isinstance(body, dict) else None


async def _put(project_id: str, kind: str, item_id: str, value: Any, by: str) -> None:
    async with db.session() as s:
        # A runbook and its lock are written one at a time, so a row cannot
        # slip in between a lock and the content it froze; a deposition's
        # writes are held against the row they follow the same way.
        await db.lock(s, "state", project_id, "runbooks" if kind == LOCKS else kind, item_id)
        existed = await _held(s, kind, project_id, item_id)
        if kind == "runbooks":
            frozen = await _frozen(s, project_id, item_id)
            if frozen is not None and not frozen_as(value, frozen):
                raise StateRefused(f"{item_id} is locked: its predictions and measures are kept as they were frozen "
                                   f"under {frozen}, and a change is a new runbook")
        closed = False
        if kind == "depositions" and existed:
            before = await _stored(s, project_id, item_id)
            if before is not None:
                why = deposition_refusal(item_id, before, value)
                if why:
                    raise StateRefused(why)
                closed = before.get("state") == "closed"
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
        elif closed:
            # A closed deposition changes little (a series' role, an
            # observation structured, its reconciliation), and each change
            # is audited.
            await audit.add(project_id, agent="person", who=by, module="runbooks", action="amend_depositions",
                            state="kept", target=item_id)


def put(kind: str, item_id: str, value: Any, by: str) -> Any:
    """Keep one row whole, or refuse it in words; what was kept."""
    checked = _checked(kind, item_id, value)
    if kind == CONVERSATIONS:
        try:
            _conversations.merge(checked, by=by)
        except _conversations.ConversationRefused as e:
            raise StateRefused(str(e)) from None
        return checked
    db.run(_put(projects.current(), kind, item_id, checked, (by or "").strip() or UNNAMED))
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
    if kind in (LOCKS, CONVERSATIONS) or (kind in KINDS and not KINDS[kind].removable):
        raise StateRefused(f"a {kind[:-1] if kind.endswith('s') else kind} is kept as it was made, and never taken back")
    if not ID.match(item_id):
        raise StateRefused(f"{item_id!r} is not an id")
    db.run(_remove(projects.current(), kind, item_id, (by or "").strip() or UNNAMED))
