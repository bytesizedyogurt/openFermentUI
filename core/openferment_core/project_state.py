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

A row holds what the page sent, in the shape the page's generated types give
it (`src/api/types.gen.ts`), and each kind has its model in models.py (alpha
2.2 E.0b): a deposition, measured evidence, a runbook, a Proforma scenario,
a train the Builder saved, an override, a lock, a Live conversation. What is
checked here is what makes a row a row: a known kind, an id of the right
shape that the value repeats, a value that reads as its kind's model, a size
a page can send, and, once a runbook is locked, predictions and measures
that are the ones its lock froze (runbook_lock.py computes the digest the
page writes). The rules that act on the content run where they always ran.

`GET /api/state` answers a `ProjectState` (`state`): every row read as its
kind's model one at a time, so a row kept before its kind had a model, and
that does not read, is named in `refused` with why while the rest are
served. A row is served as kept: a field the page left out stays out, and a
deposition, measured evidence, a scenario and a saved train keep the fields
their models do not name.

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

A scope's overrides are one row a key, and two pages may hold one scope (a
Proforma scenario's panel open in two tabs). A page's write names the rows it
read beside the rows it sends (`base`), and the service lays the write on what
it keeps key by key (`_merged`): a key the page set or took back is changed,
a key the page left as it read it stays as the service keeps it, another
page's among them, and a key another page changed since this page read it,
which this page changed too, refuses the write in words, nothing kept (bug
hunt H7-04). A write that names no rows replaces the scope whole, as every
write did before.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import audit, db, projects
from .basis import EstimateRefused, refuse_estimates
from .db import models as t
from .db import rows
from .models import (
    Deposition,
    LiveConversation,
    MeasuredEvidence,
    Override,
    ProformaScenario,
    ProjectState,
    RefusedRow,
    Runbook,
    RunbookLock,
    TrainMade,
)
from .postdoc import conversations as _conversations
from .runbook_lock import frozen_as

# An id as the pages make them, and an override scope (`pureos:unit:tr-1:inlet`).
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:|-]{0,199}$")
MAX_BYTES = 2_000_000
# Who a row's maker is when the page sent no name: a browser with no person
# set in Settings (src/store.ts `decidedBy`). A reading kept under it names
# nobody, and no run takes it as a measurement (measurements.py).
UNNAMED = "this browser"
# The scopes whose overrides may keep a deposition's reading in its own value
# and unit (`Override.unit`): a Proforma scenario's, whose parameter panel
# offers readings (alpha 2.2 E.17). Every other scope keeps each value in its
# parameter's unit, as pureOS's Builder lays a train's overrides into the
# train it saves (src/lib/pureos.ts `trainSpecOf`).
OWN_UNIT_SCOPE = "proforma:"

# The stages a deposition moves through at the bench, in order (src/store.ts).
DEPOSITION_STATES = ("staged", "running", "closed")
# What a deposition, each of its readings and each of its observations keep
# from the write that first held them (`deposition_refusal`).
DEPOSITION_FIELDS = ("runbookId", "protocolId", "startedAt")
ENTRY_FIELDS = ("measureId", "stepId", "at", "value", "unit", "raw")
OBSERVATION_FIELDS = ("stepId", "at", "raw")


class StateRefused(ValueError):
    """A write that is not a row of its kind, in words."""


def _non_finite(value: Any, path: str = "") -> list[str]:
    """Where a number that is NaN, infinite or past a float's range stands
    in a row a page sends (each as a path into it, `value` for the row
    itself), anywhere in it."""
    from .models import float_holds

    if isinstance(value, float) and not math.isfinite(value):
        return [path or "value"]
    if isinstance(value, int) and not isinstance(value, bool) and not float_holds(value):
        return [path or "value"]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _non_finite(v, f"{path}.{k}" if path else str(k))]
    if isinstance(value, list):
        return [p for n, v in enumerate(value) for p in _non_finite(v, f"{path}[{n}]")]
    return []


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

# What each kind's row reads as (models.py), and the row in words. A write
# is held to its kind's model before it is kept, and a load reads each row
# by it (`state`). A lock and a scenario's fits are held whole by
# `_checked`'s own words; a Live conversation by Postdoc's (`merge`).
READERS: dict[str, tuple[TypeAdapter[Any], str]] = {
    "depositions": (TypeAdapter(Deposition), "a deposition"),
    "measuredEvidence": (TypeAdapter(MeasuredEvidence), "measured evidence"),
    "runbooks": (TypeAdapter(Runbook), "a runbook"),
    "fits": (TypeAdapter(dict[str, str]), "a scenario's fits"),
    "scenarios": (TypeAdapter(ProformaScenario), "a Proforma scenario"),
    "trains": (TypeAdapter(TrainMade), "a train the Builder saved"),
    LOCKS: (TypeAdapter(RunbookLock), "a lock"),
    OVERRIDES: (TypeAdapter(Override), "an override"),
    CONVERSATIONS: (TypeAdapter(LiveConversation), "a Live conversation"),
}
# How many of a row's validation errors its refusal names.
SAID = 3


def _where(loc: tuple[Any, ...]) -> str:
    """A field's place in a row, as `_non_finite` writes one
    (`entries[0].unit`); `the row` for the row itself."""
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "the row"


def _said(e: ValidationError) -> str:
    """Why a row does not read as its kind's model, in words: each field that
    does not read, where it stands and what it lacks, the first few."""
    errors = e.errors()
    said = [f"{_where(tuple(err.get('loc', ())))}: {str(err.get('msg', '')).removeprefix('Value error, ')}"
            for err in errors[:SAID]]
    return "; ".join(said) + (f"; and {len(errors) - SAID} more" if len(errors) > SAID else "")


def _reads_as(kind: str, value: Any, subject: str | None = None) -> None:
    """Refuse in words a row that does not read as its kind's model; nothing
    is kept."""
    reader, named = READERS[kind]
    try:
        reader.validate_python(value)
    except ValidationError as e:
        raise StateRefused(f"{subject or f'this {kind} row'} does not read as {named}: {_said(e)}; nothing was "
                           "kept") from None


def _checked(kind: str, item_id: str, value: Any) -> Any:
    if kind not in NAMES:
        raise StateRefused(f"{kind!r} is not something a project keeps; it keeps {', '.join(NAMES)}")
    if not ID.match(item_id):
        raise StateRefused(f"{item_id!r} is not an id: letters, digits and . _ : | -, at most 200")
    infinite = _non_finite(value)
    if infinite:
        # JSON carries finite numbers alone, and the database keeps JSON: a
        # page's NaN or Infinity is refused in words, nothing kept (alpha 2.2 D.0).
        raise StateRefused(f"this {kind} row holds a number that is NaN, infinite or past a float's range at "
                           f"{', '.join(infinite[:5])}; a row keeps finite numbers alone, so nothing was kept")
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
        twice = _named_twice(value)
        if twice:
            raise StateRefused(f"the overrides of {item_id} name {', '.join(twice)} more than once; a scope keeps one "
                               "override a key, so nothing was kept")
        for o in value:
            _reads_as(kind, o, f"the override of {o['key']} in {item_id}")
            if o.get("unit") is not None and not item_id.startswith(OWN_UNIT_SCOPE):
                raise StateRefused(f"the override of {o['key']} in {item_id} keeps a reading in its own unit "
                                   f"({o['unit']}), which a Proforma scenario's scope alone keeps "
                                   f"({OWN_UNIT_SCOPE}<scenario id>): this scope keeps each value in its parameter's "
                                   "unit, as a saved train keeps it; nothing was kept")
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
    if kind != CONVERSATIONS:
        # A Live conversation is held to its model where Postdoc lays it on (`merge`).
        _reads_as(kind, value)
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


async def _pairs(s: AsyncSession, project_id: str, kind: Kind) -> list[tuple[str, Any]]:
    """Each row of a kind the project keeps, as its id and its body, oldest first."""
    table = kind.table
    q = select(table.c.id, table.c.body).where(table.c.project_id == project_id, *kind.where())
    return [(r.id, r.body) for r in (await s.execute(q.order_by(table.c.created_at, table.c.id))).all()]


async def _rows_of(project_id: str) -> dict[str, Any]:
    """What the project keeps of its pages as its tables hold it: each kind's
    rows as (id, body), oldest first; the locks by runbook and the overrides
    by scope; each Live conversation whole, as Postdoc keeps it; and who
    deposited each deposition."""
    out: dict[str, Any] = {}
    async with db.session() as s:
        for name, kind in KINDS.items():
            out[name] = await _pairs(s, project_id, kind)
        out[LOCKS] = await _locks(s, project_id)
        out[OVERRIDES] = await _overrides(s, project_id)
    out[CONVERSATIONS] = [c.model_dump(mode="json") for c in await _conversations._listed(project_id)]
    # Who deposited each deposition (its row's maker, who first kept it): the
    # person a measurement resting on one of its readings names.
    out[MAKERS] = {str(body.get("id")): maker for body, maker in await _deposited(project_id, None)
                   if isinstance(body, dict) and body.get("id")}
    return out


async def _load(project_id: str) -> dict[str, Any]:
    held = await _rows_of(project_id)
    out = {**held, **{name: [body for _, body in held[name]] for name in KINDS}}
    # Fits and trains are keyed in the page by scenario and by train, the id
    # each row is kept under.
    out["fits"] = {rid: body.get("byInput") if isinstance(body, dict) else body for rid, body in held["fits"]}
    out["trains"] = dict(held["trains"])
    return out


def load() -> dict[str, Any]:
    """Everything the current project keeps of its pages, keyed as the page
    keeps it, and who deposited each deposition (`depositedBy`): each row's
    body as it was kept, what the service's own readers read."""
    return db.run(_load(projects.current()))


def state() -> ProjectState:
    """GET /api/state: everything the current project keeps of its pages,
    each row read as its kind's model (READERS) one at a time. A row that
    does not read, one kept before its kind had a model, is left out and
    named in `refused` with why, so one row never stops the rest from
    loading. A row read from what a page sent is served as kept (api.AS_KEPT);
    a Live conversation, read from the whole of what Postdoc keeps, is
    served whole."""
    held = db.run(_rows_of(projects.current()))
    refused: list[RefusedRow] = []

    def read(kind: str, row_id: str, body: Any, subject: str = "") -> Any:
        try:
            return READERS[kind][0].validate_python(body)
        except ValidationError as e:
            refused.append(RefusedRow(kind=kind, id=row_id, why=f"{subject}{_said(e)}"))
            return None

    def read_all(kind: str) -> list[tuple[str, Any]]:
        return [(rid, row) for rid, body in held[kind] if (row := read(kind, rid, body)) is not None]

    def override(scope: str, n: int, body: Any) -> Any:
        key = body.get("key") if isinstance(body, dict) else None
        return read(OVERRIDES, scope, body, f"the override of {key if isinstance(key, str) else f'entry {n}'}: ")

    overrides = {scope: kept_ones for scope, listed in held[OVERRIDES].items()
                 if (kept_ones := [o for n, body in enumerate(listed) if (o := override(scope, n, body)) is not None])}
    fits = {rid: f for rid, body in held["fits"]
            if (f := read("fits", rid, body.get("byInput") if isinstance(body, dict) else body)) is not None}
    return ProjectState(
        depositions=[row for _, row in read_all("depositions")],
        measuredEvidence=[row for _, row in read_all("measuredEvidence")],
        runbooks=[row for _, row in read_all("runbooks")],
        runbookLocks={rid: lock for rid, body in held[LOCKS].items() if (lock := read(LOCKS, rid, body)) is not None},
        overrides=overrides,
        fits=fits,
        scenarios=[row for _, row in read_all("scenarios")],
        trains=dict(read_all("trains")),
        conversations=[c for body in held[CONVERSATIONS]
                       if (c := read(CONVERSATIONS, str(body.get("id")), body)) is not None],
        depositedBy=held[MAKERS],
        refused=refused,
    )


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
    (`proforma:<scenario id>`), each as the parameter panel wrote it: a
    person's assumption or a model's estimate in its parameter's unit, or a
    deposition's reading a person chose there, in the reading's own value and
    unit and naming who chose it (`Override.unit`, `Override.chosenBy`)."""
    return db.run(_scope_overrides(projects.current(), scope))


def run_request(scenario: dict[str, Any], by: str = "") -> Any:
    """A run of a Proforma scenario the project keeps, as its page sends it,
    asked for by `by`: the flowsheet and the parts a composite is built
    from, the values a person set on its page (the overrides the project
    keeps for its scope, each sent as a typed input in its parameter's
    unit, a reading in its own value and unit, proforma.inputs_of), and the
    fermOS fits chosen for its inputs,
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


def _named_twice(listed: list[dict[str, Any]]) -> list[str]:
    """The keys a scope's list names more than once, in the order first named."""
    seen: set[str] = set()
    twice: list[str] = []
    for o in listed:
        if o["key"] in seen and o["key"] not in twice:
            twice.append(o["key"])
        seen.add(o["key"])
    return twice


def _read_base(item_id: str, base: Any) -> list[dict[str, Any]]:
    """The rows of a scope a page's write says it read, each naming the scope
    and its key once; refused in words when they do not. They are compared
    with what the service keeps, and never kept themselves."""
    if not isinstance(base, list) or not all(isinstance(o, dict) and o.get("scope") == item_id and
                                             isinstance(o.get("key"), str) and o["key"] for o in base):
        raise StateRefused(f"the overrides this page read of {item_id} are a list, each naming this scope and its "
                           "key; nothing was kept")
    if len(json.dumps(base)) > MAX_BYTES:
        raise StateRefused(f"the overrides this page read of {item_id} are over {MAX_BYTES // 1_000_000} MB; a page "
                           "sends less")
    twice = _named_twice(base)
    if twice:
        raise StateRefused(f"the overrides this page read of {item_id} name {', '.join(twice)} more than once; "
                           "nothing was kept")
    return base


def _as_read(o: dict[str, Any] | None) -> dict[str, Any] | None:
    """An override as a page reads it, to compare two: read as its model, a
    default filled and a null left out, so `3` and `3.0` are one number, as
    they are to the page. A row that does not read is one no page was served
    (`state`), and compares as no row."""
    if o is None:
        return None
    try:
        return READERS[OVERRIDES][0].validate_python(o).model_dump(mode="json", exclude_none=True)
    except ValidationError:
        return None


def _merged(item_id: str, kept: list[dict[str, Any]], base: list[dict[str, Any]],
            value: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A scope's overrides once a page's write is laid on what the service
    keeps (`kept`), key by key against the rows the page read (`base`): a key
    the page set or took back is changed where the service keeps it as the
    page read it, or already as the page sends it; a key the page left as it
    read it stays as kept. A key another page changed since, which this page
    changed too, refuses the write in words, nothing kept (bug hunt H7-04)."""
    held = {o["key"]: o for o in kept if isinstance(o, dict) and isinstance(o.get("key"), str)}
    read = {o["key"]: o for o in base}
    sent = {o["key"]: o for o in value}
    out = dict(held)
    clashes: list[str] = []
    for key in [*read, *(k for k in sent if k not in read)]:
        was, now = _as_read(read.get(key)), _as_read(sent.get(key))
        if was == now:
            continue
        there = _as_read(held.get(key))
        if there == was:
            if key in sent:
                out[key] = sent[key]
            else:
                out.pop(key, None)
        elif there != now:
            o = held.get(key)
            clashes.append(f"{key} was taken back" if there is None else
                           f"{key} was kept by {o.get('by') or 'another page'} at {o.get('at') or 'a later time'}")
    if clashes:
        raise StateRefused(f"the overrides of {item_id} changed since this page read them: {'; '.join(clashes)}; this "
                           "page changed the same, so nothing in this write was kept, and the scope as the service "
                           "keeps it is read again")
    return list(out.values())


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


def _override_maker(o: dict[str, Any], by: str) -> str:
    """Who an override row was made by: a deposition's reading by the person
    who chose it for the parameter (`chosenBy`; the write's person where the
    row names none), `by` staying its depositor; a person's value or a
    model's estimate by the person or the model it names."""
    if o.get("origin") == "measurement":
        return str(o.get("chosenBy") or by)
    return str(o.get("by") or by)


def _readings_chosen(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The rows of a scope's overrides that set a parameter to a deposition's
    reading the scope's rows before did not: a reading on a key that held
    none, another reading, or the same reading chosen by another person. A
    keep that moves a person's value beside a reading chooses nothing."""
    held = {o.get("key"): o for o in before}

    def same(o: dict[str, Any]) -> bool:
        was = held.get(o.get("key"))
        return (was is not None and was.get("origin") == "measurement"
                and (was.get("ref"), was.get("chosenBy")) == (o.get("ref"), o.get("chosenBy")))

    return [o for o in after if o.get("origin") == "measurement" and not same(o)]


async def _put(project_id: str, kind: str, item_id: str, value: Any, by: str,
               base: list[dict[str, Any]] | None = None) -> Any:
    """Keep one row; what was kept: a scope's overrides as the scope holds
    them once the write is laid on (`_merged`), any other row as it was sent."""
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
        chosen: list[dict[str, Any]] = []
        if kind == LOCKS:
            if existed:
                raise StateRefused(f"{item_id} is locked already; a lock is kept as it was made")
            await s.execute(insert(t.runbook_locks).values(
                project_id=project_id, runbook_id=item_id, lock_hash=value["lockHash"],
                locked_at=datetime.fromisoformat(value["lockedAt"].replace("Z", "+00:00")), created_by=by,
            ))
        elif kind == OVERRIDES:
            before = (await _overrides(s, project_id, item_id)).get(item_id, []) if existed else []
            # A write that names the rows it read is laid on what the scope keeps key by key; one that names none
            # replaces the scope whole.
            value = value if base is None else _merged(item_id, before, base, value)
            chosen = _readings_chosen(before, value)
            # Each key is written on its own: a row the write leaves as kept stays, with its maker and its time.
            held = {o.get("key"): o for o in before}
            keys = {o["key"] for o in value}
            for key in [k for k in held if k not in keys]:
                await s.execute(delete(t.overrides).where(t.overrides.c.project_id == project_id,
                                                          t.overrides.c.scope == item_id, t.overrides.c.key == key))
            for o in value:
                if held.get(o["key"]) == o:
                    continue
                await s.execute(delete(t.overrides).where(t.overrides.c.project_id == project_id,
                                                          t.overrides.c.scope == item_id, t.overrides.c.key == o["key"]))
                await s.execute(insert(t.overrides).values(project_id=project_id, scope=item_id, key=o["key"], body=o,
                                                           created_by=_override_maker(o, by)))
        else:
            k = KINDS[kind]
            body = {"id": item_id, "byInput": value} if kind == "fits" else value
            await rows.put(s, k.table, project_id, item_id, body, by=by, **k.columns(value))
        module = item_id.split(":", 1)[0] if kind == OVERRIDES and item_id.split(":", 1)[0] in ("proforma", "fermos", "pureos") \
            else (KINDS[kind].module if kind in KINDS else "runbooks")
        if not existed or kind == LOCKS:
            await audit.add(project_id, agent="person", who=by, module=module,
                            action="lock" if kind == LOCKS else f"keep_{kind}", state="locked" if kind == LOCKS else "kept",
                            target=item_id)
        # A parameter set to a deposition's reading, at the scope's first keep
        # or any later one: who chose which reading for which parameter
        # (alpha 2.2 E.debts; ADR-006's note of E.17).
        for o in chosen:
            await audit.add(project_id, agent="person", who=by, module=module, action="choose_reading", state="kept",
                            target=item_id, detail={"key": o["key"], "ref": o.get("ref"),
                                                    "chosenBy": _override_maker(o, by)})
        if closed:
            # A closed deposition changes little (a series' role, an
            # observation structured, its reconciliation), and each change
            # is audited.
            await audit.add(project_id, agent="person", who=by, module="runbooks", action="amend_depositions",
                            state="kept", target=item_id)
    return value


def put(kind: str, item_id: str, value: Any, by: str, base: Any = None) -> Any:
    """Keep one row, or refuse it in words; what was kept. A scope's
    overrides sent with the rows the page read of the scope (`base`) are laid
    on what the service keeps key by key, and what was kept is the scope as it
    then holds; every other row is kept whole."""
    checked = _checked(kind, item_id, value)
    if base is not None and kind != OVERRIDES:
        raise StateRefused(f"a write names the rows it read for a scope's overrides alone; a {kind} row is kept "
                           "whole, so nothing was kept")
    read = _read_base(item_id, base) if base is not None else None
    if kind == CONVERSATIONS:
        try:
            _conversations.merge(checked, by=by)
        except _conversations.ConversationRefused as e:
            raise StateRefused(str(e)) from None
        return checked
    kept = db.run(_put(projects.current(), kind, item_id, checked, (by or "").strip() or UNNAMED, read))
    # The scope answered as a load serves it: a row kept before its kind had a model, that does not read, stays kept
    # and unserved (`state`).
    return [o for o in kept if _as_read(o) is not None] if kind == OVERRIDES else kept


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
