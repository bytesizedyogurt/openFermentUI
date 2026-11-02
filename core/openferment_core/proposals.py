"""Proposals (OF-BLD-015 §7.4): what a model asked for at a gate, kept
until a person carries it out or dismisses it.

A write tool whose action a gate covers (`tools/gates.py`) writes nothing:
it calls `propose`, and the proposal is what comes back, with `state:
proposed`. Home shows every open proposal as a card with the one button a
person presses. `carry_out` runs the action on the server where the server
can (a check asked for in the person's name; an extraction once the budget
allows) and otherwise records that the person took it to the place the gate
names (the runbook to lock, the Guild page to sign on). Either way the
person's name goes on the proposal and a line goes to the audit log.

Each proposal is a row of the project's `proposals` table (ADR-001), written
under the project's proposals lock (`db.lock`) with its audit row in the same
transaction.

THE RULES (OF-BLD-016 §1.R). A proposal's words reach Home and the model's
next ask, so its title, why, note, target and field values hold no number
(`validate.find_number`, Rule 1), and its target is an id: a proposal that
breaks either is refused whole, never repaired. One ask makes one open
proposal of a kind (module, action, target); the second is refused. A Guild
proposal is listed (`listed`, `shown`) without its words, because who a
check names is never shown before it is run; the store keeps them. A server
gate is marked done only when its server action ran. The store's lock is
never held while an action runs: the proposal is marked running in this
process, the lock is let go, and it is taken again to record the end.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from . import audit, db, projects
from .db import models as t
from .db import rows
from .models import Proposal, Proposals
from .tools import gates
from .validate import find_number

# Proposals whose action is running in this process: the mark that lets
# carry_out let go of the store while the action runs (§1.R finding 13). It
# is set and read under the store's lock and cleared when the action ends. In
# memory, so a process that dies mid-run leaves the proposal open to be
# pressed again, never stuck.
_RUNNING: set[str] = set()


class ProposalRefused(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── the store ──────────────────────────────────────────────────────────


async def _all(s: AsyncSession, pid: str, state: str | None = None) -> list[Proposal]:
    where = [t.proposals.c.state == state] if state is not None else []
    return [Proposal.model_validate(b) for b in await rows.bodies(s, t.proposals, pid, *where)]


async def _one(s: AsyncSession, pid: str, proposal_id: str, *, for_update: bool = False) -> Proposal | None:
    found = await rows.body(s, t.proposals, pid, proposal_id, for_update=for_update)
    return Proposal.model_validate(found) if found is not None else None


async def _put(s: AsyncSession, pid: str, p: Proposal) -> None:
    await rows.put(s, t.proposals, pid, p.id, p.model_dump(mode="json"), by=p.by, state=p.state)


async def _read(pid: str, state: str | None = None) -> list[Proposal]:
    async with db.session() as s:
        return await _all(s, pid, state)


async def _get(pid: str, proposal_id: str) -> Proposal | None:
    async with db.session() as s:
        return await _one(s, pid, proposal_id)


def read() -> Proposals:
    """The project's proposals, in the order they were made."""
    return Proposals(proposals=db.run(_read(projects.current())))


def open_ones() -> list[Proposal]:
    return db.run(_read(projects.current(), "proposed"))


def get(proposal_id: str) -> Proposal | None:
    return db.run(_get(projects.current(), proposal_id))


def propose(
    *,
    module: str,
    action: str,
    gate: gates.Gate,
    title: str,
    why: str,
    by: str,
    target: str | None = None,
    fields: dict[str, str] | None = None,
    note: str = "",
    ask_id: str | None = None,
    effort: str | None = None,
) -> Proposal:
    _held_to_rule_one(title=title, why=why, note=note, target=target, fields=fields or {})
    made = Proposal(
        id=f"pr-{uuid.uuid4().hex[:12]}", at=_now(), module=module, action=action, gate=gate.id,  # type: ignore[arg-type]
        title=title, why=why, how=gate.how, route=gate.route, server=gate.server,
        target=target or None, fields=fields or {}, note=note, by=by, askId=ask_id or None,
    )
    return db.run(_keep(projects.current(), made, effort))


async def _keep(pid: str, made: Proposal, effort: str | None) -> Proposal:
    """The proposal and its audit row, written together, unless one of its
    kind already waits in this ask."""
    async with db.session() as s:
        await db.lock(s, "proposals", pid)
        # One open proposal of a kind per ask (§1.R finding 2): a restart, or
        # a second call worded otherwise, asks for what is already waiting.
        twin = next((p for p in await _all(s, pid, "proposed") if p.askId == made.askId
                     and (p.module, p.action, p.target) == (made.module, made.action, made.target)), None)
        if twin is not None:
            on = f" on {made.target}" if made.target else ""
            raise ProposalRefused(f"{made.module} {made.action}{on} is already proposed in this ask ({twin.id}) and "
                                  "waits for a person")
        await _put(s, pid, made)
        await audit.add(pid, agent="model", who=made.by, module=made.module, action=made.action, state="proposed",
                        target=made.target, ask_id=made.askId, effort=effort,
                        detail={"proposalId": made.id, "gate": made.gate})
    return made


def _held_to_rule_one(*, title: str, why: str, note: str, target: str | None, fields: dict[str, str]) -> None:
    """Rule 1 for a proposal's words, and its target an id. Refuses whole,
    naming what tripped; never repairs (§1.R findings 5 and 8)."""
    # The caller's own words first, so a refusal names what it wrote; the
    # title and why a tool builds from them come last.
    words = [("note", note), ("target", target or "")] + [(f"field {name}", value) for name, value in fields.items()]
    words += [("title", title), ("why", why)]
    for name, text in words:
        if (n := find_number(text or "")) is not None:
            raise ProposalRefused(f"the {name} holds a number ({n!r}); a proposal's words carry ids and words, and every "
                                  "number on screen comes from a source")
    if target and len(target.split()) != 1:
        raise ProposalRefused(f"the target {target!r} is not an id: name the one id or ref the action is on, or none")


def _person(person: str) -> str:
    name = (person or "").strip()
    if len(name) < 2 or name.lower() in gates.PLACEHOLDER_NAMES:
        raise ProposalRefused("a proposal is carried out or dismissed by a named person; set a reviewer name in Settings")
    return name


def _run(p: Proposal, person: str, acting: str | None = None) -> str:
    """The action, in the person's name, where the server can run it. Returns
    what happened, in words. Raises what the module's write function raises."""
    if (p.module, p.action) == ("guild", "propose_check"):
        from . import checks
        from .models import CheckRequest

        # Guild knows people by id, and the reviewer name is words: the check
        # is asked for by the Guild person the browser is acting as (§1.R
        # finding 11), whose authority checks.request decides.
        if not (acting or "").strip():
            raise ProposalRefused("a check is asked for by a person on Guild: choose who you are acting as on Guild, "
                                  "then press the button again")
        skills = [s.strip() for s in (p.fields.get("skillIds") or "").split(",") if s.strip()]
        made = checks.request(CheckRequest(personId=p.fields.get("personId", ""), skillIds=skills, by=acting.strip()))
        return f"check {made.id} asked for in {person}'s name, acting as {acting.strip()} on Guild, on {', '.join(made.skillIds)}"
    if (p.module, p.action) == ("intake", "extract"):
        from . import extract

        got = extract.extract_paper(p.target or "")
        return f"{p.target} extracted: {len(got.candidates)} candidates anchored, {got.rejected} rejected, ${got.usage.costUsd:.4f}"
    if (p.module, p.action) == ("home", "note"):
        # The notebook arrives with OF-BLD-017 §5.3; until then the note is
        # kept here, under the person's name, and the audit line says so.
        return f"note kept on this proposal under {person}'s name until the notebook lands (OF-BLD-017 §5.3)"
    if p.server:
        # A server gate the server has no action for runs nothing, so it is
        # never marked done (§1.R finding 12): it stays open to be dismissed.
        raise ProposalRefused(f"the service has no action for {p.module} {p.action}, so nothing was done; dismiss it")
    return f"handed to {person}: {p.how}"


def _open(p: Proposal | None, proposal_id: str) -> Proposal:
    if p is None:
        raise ProposalRefused(f"no proposal {proposal_id!r}")
    if p.state != "proposed":
        raise ProposalRefused(f"proposal {proposal_id} is already {p.state}")
    if p.id in _RUNNING:
        raise ProposalRefused(f"proposal {proposal_id} is being carried out")
    return p


def carry_out(proposal_id: str, person: str, acting: str | None = None) -> Proposal:
    """Run the action in the person's name, or record that it was handed to
    them. `acting` is the Guild person id the browser is acting as, which a
    check is asked for by. The store's locks are not held while the action
    runs (§1.R finding 13): it is marked running here, and the end is
    recorded under the locks taken again. Returns the proposal as `shown`."""
    name = _person(person)
    pid = projects.current()
    p = db.run(_start(pid, proposal_id))
    try:
        result = _run(p, name, acting)
        p = db.run(_end(pid, proposal_id, name, result))
    finally:
        _RUNNING.discard(proposal_id)
    return shown(p)


async def _start(pid: str, proposal_id: str) -> Proposal:
    """Mark the proposal running in this process, under the store's lock."""
    async with db.session() as s:
        await db.lock(s, "proposals", pid)
        p = _open(await _one(s, pid, proposal_id), proposal_id)
        _RUNNING.add(p.id)
    return p


async def _end(pid: str, proposal_id: str, name: str, result: str) -> Proposal:
    """The action ran: the proposal is done, in the person's name, and the
    audit row says so in the same transaction."""
    async with db.session() as s:
        await db.lock(s, "proposals", pid)
        p = await _one(s, pid, proposal_id, for_update=True)
        if p is None:
            raise ProposalRefused(f"proposal {proposal_id} left the store while it ran: {result}")
        p.state = "done"
        p.carriedOutBy = name
        p.carriedOutAt = _now()
        p.result = result
        await _put(s, pid, p)
        await audit.add(pid, agent="person", who=name, module=p.module, action=p.action, state="done", target=p.target,
                        detail={"proposalId": p.id, "gate": p.gate, "result": result})
    return p


def dismiss(proposal_id: str, person: str, reason: str) -> Proposal:
    name = _person(person)
    why = (reason or "").strip() or "dismissed on Home"
    return shown(db.run(_dismiss(projects.current(), proposal_id, name, why)))


async def _dismiss(pid: str, proposal_id: str, name: str, why: str) -> Proposal:
    async with db.session() as s:
        await db.lock(s, "proposals", pid)
        p = _open(await _one(s, pid, proposal_id, for_update=True), proposal_id)
        p.state = "dismissed"
        p.carriedOutBy = name
        p.carriedOutAt = _now()
        p.result = why
        await _put(s, pid, p)
        await audit.add(pid, agent="person", who=name, module=p.module, action=p.action, state="dismissed",
                        target=p.target, detail={"proposalId": p.id, "gate": p.gate, "reason": why})
    return p


def shown(p: Proposal) -> Proposal:
    """A proposal as a reader sees it (§1.R finding 9). A Guild proposal is
    about a person, and who a check names is never shown before it is run:
    its note, why and target are left out, and its title is the code's words
    alone (one made before §1.R ended in the target). Its fields keep their
    ids, as Guild's checks serve theirs, so the browser can hold shownTo and
    mayQueue (src/engine/checks.ts) over it. Every other proposal is as kept."""
    if p.module != "guild":
        return p
    return p.model_copy(update={"title": p.title.split(" — ")[0], "why": "", "note": "", "target": None})


def listed(state: str | None = None) -> list[Proposal]:
    """Every proposal, or those in one state, as `shown`: what
    GET /api/proposals serves."""
    return [shown(p) for p in db.run(_read(projects.current(), state))]


def as_rows(limit: int = 20) -> list[dict[str, Any]]:
    """Open proposals as `home_read` lists them."""
    return [shown(p).model_dump(mode="json") for p in open_ones()[:limit]]
