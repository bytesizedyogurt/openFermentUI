"""A project's protocols (alpha 2.2 E.12a; ADR-017): each protocol the lab
writes, kept whole, and read by Guild, Practice and the module reads.

A protocol is a row of the project's `protocols` table (migration 0010),
kept whole as `models.Protocol` with who kept it: its own fields, written
when it is made, and its versions. A person makes a protocol once under its
id (`POST /api/protocols`) and adds a version under a version of its own
(`POST /api/protocols/{id}/versions`), which becomes the current one. A
version is kept as it was kept: one already held is refused in words, and
nothing here takes a protocol or a version out, since taking a person's work
out of a live instance is the owner's call. Each keep is audited in the
keeper's name.

A step names the skills a person needs to do it, by their ids in the
project's skill catalogue (catalogues.py), and a keep holds every one of
them to that catalogue: a step naming a skill the catalogue does not hold is
refused in words naming the step and the skill.

A protocol is kept whole in one row, so a keep is held to MAX_BYTES as the
row it writes, refused in words past it, as a page's row is (project_state).
A row that does not read as a protocol, one kept in a shape an earlier model
allowed, is left out of every read and logged with why, so one row never
stops the rest from reading.

A protocol's numbers are what the protocol says, written for its base batch:
an amount, a stock's concentration, a timer, the minutes a run takes. A
material that rests on a record names it (`sourceRecordId`). No tool writes
a protocol; a person keeps every one.

The readers take them in the shapes they always read (`as_*`): Guild's
step skills and the current versions Practice quotes and a check's brief
reads (guild.projection), and the runbooks module's protocol rows
(module_stores).
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from . import audit, db, projects
from .db import models as t
from .db import rows
from .models import PLACEHOLDER, Material, Protocol, ProtocolVersion, Step


# The most a protocol may hold as its row keeps it, every version with it, as
# a page's row is held (project_state.MAX_BYTES).
MAX_BYTES = 2_000_000

log = logging.getLogger(__name__)


class ProtocolRefused(ValueError):
    """A protocol or a version the project will not keep, in words."""


class ProtocolNotFound(KeyError):
    pass


def _now() -> str:
    """A keep's time, ISO 8601 in UTC, written as the audit writes its rows'
    (`+00:00`)."""
    return datetime.now(timezone.utc).isoformat()


def _keeper(by: str | None) -> str:
    """The keeper's name as every door reads one (tools.caller_name), held
    to the rule a person's recorded name keeps (biorepo.reviewer_refusal)."""
    from .biorepo import reviewer_refusal
    from .tools import caller_name

    who = caller_name(by or "")
    if not who:
        raise ProtocolRefused("a protocol is kept in a person's name, and this keep names nobody")
    why = reviewer_refusal(who)
    if why:
        raise ProtocolRefused(f"a protocol is kept in a person's name: {why}")
    return who


def _skills_held(versions: list[ProtocolVersion]) -> None:
    """Every skill a step names is one the project's skill catalogue holds,
    or the keep is refused in words naming the step and the skill."""
    from . import catalogues

    held = {e.id for e in catalogues.listed("skill")}
    for v in versions:
        for st in v.steps:
            missing = [s for s in st.skills if s not in held]
            if missing:
                raise ProtocolRefused(
                    f"step {st.id} of version {v.version} needs {missing[0]}, which the project's skill catalogue "
                    "does not hold; a step names the skills it needs from that catalogue, so keep the skill there "
                    "first (/catalogues)")


def _read(body: dict[str, Any]) -> Protocol:
    return Protocol.model_validate(body)


def _readable(bodies: list[Any]) -> list[Protocol]:
    """Each row that reads as a protocol, read one at a time; a row that does
    not is left out and logged with its id and why."""
    out: list[Protocol] = []
    for body in bodies:
        try:
            out.append(_read(body))
        except ValidationError as e:
            held = body.get("id") if isinstance(body, dict) else None
            log.warning("the protocols' row %s does not read as a protocol and is left out: %s",
                        held if isinstance(held, str) else "with no id", first_error(e))
    return out


def _within(protocol: Protocol) -> None:
    """A protocol as its row keeps it is MAX_BYTES or less, or the keep is
    refused in words."""
    size = len(json.dumps(protocol.model_dump(mode="json")))
    if size > MAX_BYTES:
        raise ProtocolRefused(f"protocol {protocol.id} with every version it keeps comes to {size:,} bytes as its row "
                              f"keeps it, over the {MAX_BYTES:,} a protocol may hold, so nothing was kept")


# ── the store ──────────────────────────────────────────────────────────


async def _listed(project_id: str) -> list[Protocol]:
    async with db.session() as s:
        bodies = await rows.bodies(s, t.protocols, project_id)
    return sorted(_readable(bodies), key=lambda p: p.id)


def listed() -> list[Protocol]:
    """The open project's protocols, by id, each whole."""
    return db.run(_listed(projects.current()))


async def _one(project_id: str, protocol_id: str) -> Any:
    async with db.session() as s:
        return await rows.body(s, t.protocols, project_id, protocol_id)


def get(protocol_id: str) -> Protocol:
    """One of the open project's protocols, whole; ProtocolNotFound when it
    keeps none of that id, or keeps a row under it that no longer reads as a
    protocol, said in words."""
    body = db.run(_one(projects.current(), protocol_id))
    if body is None:
        raise ProtocolNotFound(f"the project keeps no protocol {protocol_id}")
    try:
        return _read(body)
    except ValidationError as e:
        raise ProtocolNotFound(f"the project keeps a row under {protocol_id} that no longer reads as a protocol "
                               f"({first_error(e)}), so every read leaves it out") from None


def _stamped(versions: list[ProtocolVersion], who: str, at: str) -> list[ProtocolVersion]:
    return [v.model_copy(update={"by": who, "at": at}) for v in versions]


async def _make(project_id: str, protocol: Protocol, who: str) -> Protocol:
    async with db.session() as s:
        # One keep at a time in the project's protocols: two makes of one id
        # never both land.
        await db.lock(s, "protocols", project_id)
        if await rows.body(s, t.protocols, project_id, protocol.id) is not None:
            raise ProtocolRefused(f"the project keeps a protocol {protocol.id} already; a protocol is made once, and a "
                                  f"new version of it is kept at /api/protocols/{protocol.id}/versions")
        await rows.put(s, t.protocols, project_id, protocol.id, protocol.model_dump(mode="json"), by=who)
        await audit.add(project_id, agent="person", who=who, module="runbooks", action="keep_protocol", state="kept",
                        target=protocol.id, detail={"versions": [v.version for v in protocol.versions]})
    return protocol


def make(protocol: Protocol, *, by: str) -> Protocol:
    """A protocol made in the open project in the name of `by`, with every
    version it holds, each stamped with its keeper and the time; refused in
    words when the project keeps a protocol under its id already, when a
    step names a skill the skill catalogue does not hold, and when the keep
    names nobody (ProtocolRefused)."""
    who = _keeper(by)
    _skills_held(protocol.versions)
    made = protocol.model_copy(update={"versions": _stamped(protocol.versions, who, _now())})
    _within(made)
    return db.run(_make(projects.current(), made, who))


async def _add(project_id: str, protocol_id: str, version: ProtocolVersion, who: str) -> Protocol:
    async with db.session() as s:
        await db.lock(s, "protocols", project_id)
        body = await rows.body(s, t.protocols, project_id, protocol_id, for_update=True)
        if body is None:
            raise ProtocolNotFound(f"the project keeps no protocol {protocol_id}")
        try:
            held = _read(body)
        except ValidationError as e:
            raise ProtocolRefused(f"the project keeps a row under {protocol_id} that no longer reads as a protocol "
                                  f"({first_error(e)}), so no version is added to it") from None
        if any(v.version == version.version for v in held.versions):
            raise ProtocolRefused(f"version {version.version} of {protocol_id} is kept as it was kept; a change is a "
                                  "new version, under a version of its own")
        grown = held.model_copy(update={"versions": [*held.versions, version], "currentVersion": version.version})
        try:
            grown = Protocol.model_validate(grown.model_dump(mode="json"))
        except ValidationError as e:
            raise ProtocolRefused(first_error(e)) from None
        _within(grown)
        await rows.put(s, t.protocols, project_id, protocol_id, grown.model_dump(mode="json"), by=who)
        await audit.add(project_id, agent="person", who=who, module="runbooks", action="keep_protocol_version",
                        state="kept", target=f"{protocol_id}/{version.version}", detail={"version": version.version})
    return grown


def add_version(protocol_id: str, version: ProtocolVersion, *, by: str) -> Protocol:
    """A new version of one of the open project's protocols, kept in the
    name of `by` and made its current version: the protocol whole, as it now
    stands. Refused in words when the protocol holds that version already,
    when a step names a skill the skill catalogue does not hold, and when
    the keep names nobody (ProtocolRefused); ProtocolNotFound when the
    project keeps no protocol under the id."""
    who = _keeper(by)
    _skills_held([version])
    stamped = version.model_copy(update={"by": who, "at": _now()})
    return db.run(_add(projects.current(), protocol_id, stamped, who))


def first_error(err: ValidationError) -> str:
    """A model's first error in words: where it stands, and why."""
    first = err.errors()[0]
    where = ".".join(str(p) for p in first.get("loc", ())) or "the protocol"
    return f"{where}: {str(first.get('msg')).removeprefix('Value error, ')}"


# ── a step as the bench reads it at the base batch ────────────────────


def round_to_precision(value: float, increment: float) -> float:
    """A value rounded to a precision increment, as the bench rounds an
    amount so it stays one it can measure (`roundToPrecision` in
    src/engine/units.ts): to the nearest increment, half up, written to the
    increment's decimals and one more."""
    steps = value / increment if increment > 0 else math.nan
    if not math.isfinite(steps):
        return value
    rounded = math.floor(steps + 0.5) * increment
    decimals = max(0, -math.floor(math.log10(increment)) + 1)
    return float(f"{rounded:.{decimals}f}")


def number(value: float) -> str:
    """A number as a person reads it: a whole number with no point, any other
    in the fewest digits that read back as it."""
    return str(int(value)) if float(value).is_integer() and abs(value) < 1e15 else repr(float(value))


def amount_at_base(m: Material) -> str:
    """A material's amount at the base batch, rounded to its precision, with its unit."""
    return f"{number(round_to_precision(m.amount, m.precision))} {m.unit}".strip()


def stock_at_base(m: Material) -> str:
    """The volume of a material's stock that holds its amount at the base
    batch, rounded to a tenth as the bench rounds it, with the stock's unit."""
    assert m.stock is not None
    return f"{number(round_to_precision(m.amount / m.stock.conc, 0.1))} {m.stock.unit}".strip()


def step_text(step: Step, version: ProtocolVersion) -> str:
    """A step's words at the version's base batch, each placeholder read as
    the bench reads it (`renderStepText` in src/engine/scale.ts at scale
    one): a material's amount, or the volume of its stock."""
    materials = {m.name: m for m in version.materials}

    def bound(match: Any) -> str:
        kind, name = match.group(1), match.group(2)
        m = materials[name]
        return stock_at_base(m) if kind == "stock" else amount_at_base(m)

    return PLACEHOLDER.sub(bound, step.text)


# ── the readers' shapes ────────────────────────────────────────────────


def held() -> list[Protocol]:
    """The open project's protocols, or none where no project is open."""
    try:
        return listed()
    except projects.ProjectRequired:
        return []


def current(p: Protocol) -> ProtocolVersion:
    return next(v for v in p.versions if v.version == p.currentVersion)


def as_steps(protocols: list[Protocol]) -> list[dict[str, Any]]:
    """Every step of every version with the skills it needs, as Guild reads
    them (guild.step_skills)."""
    return [{"protocolId": p.id, "version": v.version, "stepId": st.id, "skills": list(st.skills)}
            for p in protocols for v in p.versions for st in v.steps]


def as_quoted(protocols: list[Protocol]) -> list[dict[str, Any]]:
    """The current version of each protocol a step of which needs a skill, as
    Practice quotes it and a check's brief reads it: its steps in the words
    the bench shows at the base batch, and its materials."""
    out = []
    for p in protocols:
        v = current(p)
        if not any(st.skills for st in v.steps):
            continue
        out.append({
            "protocolId": p.id,
            "version": v.version,
            "title": p.title,
            "baseBatch": f"{number(v.baseBatch.value)} {v.baseBatch.unit} {v.baseBatch.label}".strip(),
            "steps": [{"stepId": st.id, "text": step_text(st, v), "note": st.note, "skills": list(st.skills)}
                      for st in v.steps],
            "materials": [{"name": m.name, "amount": m.amount, "unit": m.unit} for m in v.materials],
        })
    return out


def as_listed(protocols: list[Protocol]) -> list[dict[str, Any]]:
    """Each protocol as the runbooks module lists it (module_stores): its id,
    title, category, organisms and purpose, and its versions."""
    return [{"id": p.id, "title": p.title, "category": p.category, "organisms": list(p.organisms),
             "purpose": p.purpose, "currentVersion": p.currentVersion, "versions": [v.version for v in p.versions]}
            for p in protocols]
