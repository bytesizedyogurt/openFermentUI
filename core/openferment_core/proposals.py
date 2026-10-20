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
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from . import atomic, audit, intake
from .models import Proposal, Proposals
from .tools import gates

PATH = intake.DATA_DIR / "proposals.json"
_LOCK = threading.Lock()


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
    made = Proposal(
        id=f"pr-{uuid.uuid4().hex[:12]}", at=_now(), module=module, action=action, gate=gate.id,  # type: ignore[arg-type]
        title=title, why=why, how=gate.how, route=gate.route, server=gate.server,
        target=target, fields=fields or {}, note=note, by=by, askId=ask_id or None,
    )
    with _LOCK, atomic.held(PATH):
        store = read()
        store.proposals.append(made)
        _persist(store)
    audit.append(agent="model", who=by, module=module, action=action, state="proposed", target=target,
                 ask_id=ask_id, effort=effort, detail={"proposalId": made.id, "gate": gate.id})
    return made


def _person(person: str) -> str:
    name = (person or "").strip()
    if len(name) < 2 or name.lower() in gates.PLACEHOLDER_NAMES:
        raise ProposalRefused("a proposal is carried out or dismissed by a named person; set a reviewer name in Settings")
    return name


def _run(p: Proposal, person: str) -> str:
    """The action, in the person's name, where the server can run it. Returns
    what happened, in words. Raises what the module's write function raises."""
    if (p.module, p.action) == ("guild", "propose_check"):
        from . import checks
        from .models import CheckRequest

        skills = [s.strip() for s in (p.fields.get("skillIds") or "").split(",") if s.strip()]
        made = checks.request(CheckRequest(personId=p.fields.get("personId", ""), skillIds=skills, by=person))
        return f"check {made.id} asked for in {person}'s name on {', '.join(made.skillIds)}"
    if (p.module, p.action) == ("intake", "extract"):
        from . import extract

        got = extract.extract_paper(p.target or "")
        return f"{p.target} extracted: {len(got.candidates)} candidates anchored, {got.rejected} rejected, ${got.usage.costUsd:.4f}"
    if (p.module, p.action) == ("home", "note"):
        # The notebook arrives with OF-BLD-017 §5.3; until then the note is
        # kept here, under the person's name, and the audit line says so.
        return f"note kept on this proposal under {person}'s name until the notebook lands (OF-BLD-017 §5.3)"
    return f"handed to {person}: {p.how}"


def carry_out(proposal_id: str, person: str) -> Proposal:
    name = _person(person)
    with _LOCK, atomic.held(PATH):
        store = read()
        p = next((x for x in store.proposals if x.id == proposal_id), None)
        if p is None:
            raise ProposalRefused(f"no proposal {proposal_id!r}")
        if p.state != "proposed":
            raise ProposalRefused(f"proposal {proposal_id} is already {p.state}")
        result = _run(p, name)
        p.state = "done"
        p.carriedOutBy = name
        p.carriedOutAt = _now()
        p.result = result
        _persist(store)
    audit.append(agent="person", who=name, module=p.module, action=p.action, state="done", target=p.target,
                 detail={"proposalId": p.id, "gate": p.gate, "result": result})
    return p


def dismiss(proposal_id: str, person: str, reason: str) -> Proposal:
    name = _person(person)
    why = (reason or "").strip() or "dismissed on Home"
    with _LOCK, atomic.held(PATH):
        store = read()
        p = next((x for x in store.proposals if x.id == proposal_id), None)
        if p is None:
            raise ProposalRefused(f"no proposal {proposal_id!r}")
        if p.state != "proposed":
            raise ProposalRefused(f"proposal {proposal_id} is already {p.state}")
        p.state = "dismissed"
        p.carriedOutBy = name
        p.carriedOutAt = _now()
        p.result = why
        _persist(store)
    audit.append(agent="person", who=name, module=p.module, action=p.action, state="dismissed", target=p.target,
                 detail={"proposalId": p.id, "gate": p.gate, "reason": why})
    return p


def as_rows(limit: int = 20) -> list[dict[str, Any]]:
    """Open proposals as `home_read` lists them."""
    return [p.model_dump(mode="json") for p in open_ones()[:limit]]
