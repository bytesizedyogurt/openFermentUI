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

`core/data/proposals.json`, written through `atomic.write_text` under the
store's two locks, gitignored, on this machine alone.

THE RULES (OF-BLD-016 §1.R). A proposal's words reach Home and the model's
next ask, so its title, why, note, target and field values hold no number
(`validate.find_number`, Rule 1), and its target is an id: a proposal that
breaks either is refused whole, never repaired. One ask makes one open
proposal of a kind (module, action, target); the second is refused. A Guild
proposal is listed (`listed`, `shown`) without its words, because who a
check names is never shown before it is run; the store keeps them. A server
gate is marked done only when its server action ran. The store's locks are
never held while an action runs: the proposal is marked running in this
process, the locks are let go, and they are taken again to record the end.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from . import atomic, audit, intake
from .models import Proposal, Proposals
from .tools import gates
from .validate import find_number

PATH = intake.DATA_DIR / "proposals.json"
_LOCK = threading.Lock()
# Proposals whose action is running in this process, held under _LOCK: the
# mark that lets carry_out let go of the store while the action runs (§1.R
# finding 13). In memory, so a process that dies mid-run leaves the proposal
# open to be pressed again, never stuck.
_RUNNING: set[str] = set()


class ProposalRefused(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read() -> Proposals:
    if not PATH.exists():
        return Proposals()
    return Proposals.model_validate_json(PATH.read_text(encoding="utf-8"))


def _persist(store: Proposals) -> None:
    atomic.write_text(PATH, store.model_dump_json(indent=2) + "\n")


def open_ones() -> list[Proposal]:
    return [p for p in read().proposals if p.state == "proposed"]


def get(proposal_id: str) -> Proposal | None:
    return next((p for p in read().proposals if p.id == proposal_id), None)


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
    with _LOCK, atomic.held(PATH):
        store = read()
        # One open proposal of a kind per ask (§1.R finding 2): a restart, or
        # a second call worded otherwise, asks for what is already waiting.
        twin = next((p for p in store.proposals if p.state == "proposed" and p.askId == made.askId
                     and (p.module, p.action, p.target) == (made.module, made.action, made.target)), None)
        if twin is not None:
            on = f" on {made.target}" if made.target else ""
            raise ProposalRefused(f"{module} {action}{on} is already proposed in this ask ({twin.id}) and waits for a "
                                  "person")
        store.proposals.append(made)
        _persist(store)
    audit.append(agent="model", who=by, module=module, action=action, state="proposed", target=target,
                 ask_id=ask_id, effort=effort, detail={"proposalId": made.id, "gate": gate.id})
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


def _open(store: Proposals, proposal_id: str) -> Proposal:
    p = next((x for x in store.proposals if x.id == proposal_id), None)
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
    with _LOCK, atomic.held(PATH):
        p = _open(read(), proposal_id)
        _RUNNING.add(p.id)
    try:
        result = _run(p, name, acting)
        with _LOCK, atomic.held(PATH):
            store = read()
            p = next((x for x in store.proposals if x.id == proposal_id), None)
            if p is None:
                raise ProposalRefused(f"proposal {proposal_id} left the store while it ran: {result}")
            p.state = "done"
            p.carriedOutBy = name
            p.carriedOutAt = _now()
            p.result = result
            _persist(store)
    finally:
        with _LOCK:
            _RUNNING.discard(proposal_id)
    audit.append(agent="person", who=name, module=p.module, action=p.action, state="done", target=p.target,
                 detail={"proposalId": p.id, "gate": p.gate, "result": result})
    return shown(p)


def dismiss(proposal_id: str, person: str, reason: str) -> Proposal:
    name = _person(person)
    why = (reason or "").strip() or "dismissed on Home"
    with _LOCK, atomic.held(PATH):
        store = read()
        p = _open(store, proposal_id)
        p.state = "dismissed"
        p.carriedOutBy = name
        p.carriedOutAt = _now()
        p.result = why
        _persist(store)
    audit.append(agent="person", who=name, module=p.module, action=p.action, state="dismissed", target=p.target,
                 detail={"proposalId": p.id, "gate": p.gate, "reason": why})
    return shown(p)


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
    return [shown(p) for p in read().proposals if state is None or p.state == state]


def as_rows(limit: int = 20) -> list[dict[str, Any]]:
    """Open proposals as `home_read` lists them."""
    return [shown(p).model_dump(mode="json") for p in open_ones()[:limit]]
