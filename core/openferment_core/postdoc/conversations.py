"""Postdoc's conversations, kept under the project (execution prompt §4.8; ADR-008).

A conversation is a row of `conversations` (its title, when it began, who began it); each
of its turns a row of `turns`, in order (`seq`), holding the question, the loop's steps as
they completed, the validated plan or the failure in words, its status, who asked, and the
artifacts its tool calls produced; each tool call a row of `tool_calls` under its turn, with
what it was asked, what it answered the model, and what it offered to cite.

A follow-up reads its history from here (`history`): each answered turn's question and its
plan's words, as the browser sent them before (models.py `PriorTurn`), so a reload, another
device or another caller asks in the same conversation. A turn is kept `running` when it
begins and finished when the loop ends; one this process is not answering reads
`interrupted`, as the service that was answering it stopped.

The page writes its Live conversations through project_state as it always did; those writes
land here (`merge`): a conversation it begins is kept, and a turn it holds that the service
does not (asked while the service was away, in a browser before alpha 2.0) is kept as the
page wrote it. A turn the service holds stays as the service kept it, unless it is `running`
and nobody here is answering it (`_open`): the page may write the turn it is asking before
the ask arrives, so the service takes over a page's running turn when it begins it, and a
page's record of how a turn ended stands for one the service never received or stopped
answering.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit, db, projects
from ..db import models as t
from ..db import rows
from ..models import AnswerPlan, LiveConversation, LiveTurn, PriorTurn, ToolCallRecord, ToolResult, TraceStep, TurnError

# An id as a page makes one (project_state.ID).
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:|-]{0,199}$")
TITLE = 120
# The turns this process is answering now: one that is `running` and not here was cut short.
_answering: set[tuple[str, str]] = set()
_lock = threading.Lock()


class ConversationRefused(ValueError):
    """A conversation or a turn that cannot be kept, in words."""


class ConversationNotFound(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(value: str | None, prefix: str) -> str:
    if value is None or not value.strip():
        return f"{prefix}-{uuid.uuid4().hex[:12]}"
    if not ID.match(value):
        raise ConversationRefused(f"{value!r} is not an id: letters, digits and . _ : | -, at most 200")
    return value


def _artifacts(evidence: list[Any]) -> list[str]:
    out: list[str] = []
    for e in evidence:
        aid = getattr(getattr(e, "basis", None), "artifactId", None)
        if aid and aid not in out:
            out.append(aid)
    return out


def _open(project_id: str, turn_id: str, status: str) -> bool:
    """A turn kept `running` that nobody here is answering: the page wrote it before its ask
    arrived, or the service that was answering it stopped. Whoever comes next may finish it."""
    with _lock:
        return status == "running" and (project_id, turn_id) not in _answering


# ── reads ──────────────────────────────────────────────────────────────


def _turn(body: dict[str, Any], project_id: str) -> LiveTurn:
    turn = LiveTurn.model_validate(body)
    with _lock:
        cut = turn.status == "running" and (project_id, turn.id) not in _answering
    return turn.model_copy(update={"status": "interrupted"}) if cut else turn


async def _conversation(s: AsyncSession, project_id: str, cid: str) -> LiveConversation | None:
    head = await rows.body(s, t.conversations, project_id, cid)
    if head is None:
        return None
    found = (await s.execute(select(t.turns.c.body).where(t.turns.c.project_id == project_id,
                                                         t.turns.c.conversation_id == cid).order_by(t.turns.c.seq))).scalars()
    return LiveConversation(id=cid, title=head.get("title", ""), startedAt=head.get("startedAt", ""),
                            turns=[_turn(b, project_id) for b in found])


async def _listed(project_id: str) -> list[LiveConversation]:
    async with db.session() as s:
        ids = (await s.execute(select(t.conversations.c.id).where(t.conversations.c.project_id == project_id)
                               .order_by(t.conversations.c.created_at, t.conversations.c.id))).scalars().all()
        return [c for cid in ids if (c := await _conversation(s, project_id, cid)) is not None]


def listed() -> list[LiveConversation]:
    """The project's conversations, oldest first, each with its turns."""
    return db.run(_listed(projects.current()))


async def _get(project_id: str, cid: str) -> LiveConversation | None:
    async with db.session() as s:
        return await _conversation(s, project_id, cid)


def get(cid: str) -> LiveConversation:
    found = db.run(_get(projects.current(), cid))
    if found is None:
        raise ConversationNotFound(f"the project holds no conversation {cid}")
    return found


def history(cid: str | None) -> list[PriorTurn]:
    """A follow-up's history: each answered turn's question and its plan's words, oldest
    first; none for a conversation the project does not hold yet."""
    if not cid:
        return []
    found = db.run(_get(projects.current(), cid))
    if found is None:
        return []
    return [PriorTurn(question=x.question, claims=[c.text for c in x.plan.claims], gaps=list(x.plan.gaps),
                      declined=x.plan.declined) for x in found.turns if x.status == "answered" and x.plan is not None]


async def _calls(project_id: str, turn_id: str) -> list[ToolCallRecord]:
    async with db.session() as s:
        found = (await s.execute(select(t.tool_calls).where(t.tool_calls.c.project_id == project_id,
                                                            t.tool_calls.c.turn_id == turn_id).order_by(t.tool_calls.c.seq))).all()
    return [ToolCallRecord(seq=r.seq, turnId=turn_id, tool=r.tool, input=r.input, by=r.created_by,
                           at=r.created_at.isoformat().replace("+00:00", "Z"), **(r.result or {})) for r in found]


def calls(cid: str, turn_id: str) -> list[ToolCallRecord]:
    """The tool calls one turn made, in order."""
    held = get(cid)
    if all(x.id != turn_id for x in held.turns):
        raise ConversationNotFound(f"conversation {cid} holds no turn {turn_id}")
    return db.run(_calls(projects.current(), turn_id))


# ── writes ─────────────────────────────────────────────────────────────


async def _started(s: AsyncSession, project_id: str, cid: str, title: str, started: str, by: str) -> None:
    """The conversation kept when it is new, and its beginning audited, once."""
    if await rows.body(s, t.conversations, project_id, cid) is not None:
        return
    await rows.put(s, t.conversations, project_id, cid, {"id": cid, "title": title[:TITLE], "startedAt": started, "by": by},
                   by=by, title=title[:TITLE])
    await audit.add(project_id, agent="person", who=by, module="home", action="keep_conversations", state="kept", target=cid)


async def _begin(project_id: str, cid: str, tid: str, question: str, by: str) -> int:
    async with db.session() as s:
        await db.lock(s, "conversation", project_id, cid)
        await _started(s, project_id, cid, question, _now(), by)
        held = (await s.execute(select(t.turns.c.conversation_id, t.turns.c.seq, t.turns.c.status).where(
            t.turns.c.project_id == project_id, t.turns.c.id == tid))).first()
        # This process marked the turn as being answered before it got here, so `_open` would not
        # see it: a held turn is the page's own `running` one, which the service takes over.
        if held is not None and not (held.conversation_id == cid and held.status == "running"):
            raise ConversationRefused(f"the project holds a turn {tid} already; a turn is asked once")
        # The page may have written the turn it is asking first, `running`: the service takes it over.
        seq = held.seq if held is not None else (await s.execute(select(func.coalesce(func.max(t.turns.c.seq), 0)).where(
            t.turns.c.project_id == project_id, t.turns.c.conversation_id == cid))).scalar() + 1
        turn = LiveTurn(id=tid, question=question, askedAt=_now(), status="running", by=by)
        await rows.put(s, t.turns, project_id, tid, turn.model_dump(mode="json"), by=by, conversation_id=cid, seq=seq,
                       status="running")
        return seq


def begin(question: str, *, conversation_id: str | None = None, turn_id: str | None = None, by: str = "") -> tuple[str, str, int]:
    """A turn kept `running` in its conversation, the conversation begun when it is new
    (titled by its first question): the conversation's id, the turn's and its place."""
    cid, tid = _id(conversation_id, "lc"), _id(turn_id, "turn")
    who = (by or "").strip() or "this browser"
    pid = projects.current()
    # Marked as answered here before it is kept, so no page's write takes it over meanwhile.
    with _lock:
        if (pid, tid) in _answering:
            raise ConversationRefused(f"turn {tid} is being answered already; a turn is asked once")
        _answering.add((pid, tid))
    try:
        seq = db.run(_begin(pid, cid, tid, question, who))
    except BaseException:
        with _lock:
            _answering.discard((pid, tid))
        raise
    return cid, tid, seq


async def _call(project_id: str, turn_id: str, tool: str, args: dict[str, Any], result: dict[str, Any], by: str) -> None:
    async with db.session() as s:
        await s.execute(t.tool_calls.insert().values(project_id=project_id, turn_id=turn_id, tool=tool, input=args,
                                                     result=result, created_by=by))


def called(turn_id: str, tool: str, args: dict[str, Any], result: ToolResult, *, by: str) -> list[str]:
    """One tool call of a turn kept with what it answered the model and what it offered to
    cite; the artifacts it produced or read."""
    artifacts = _artifacts(result.evidence)
    kept = {"summary": result.summary, "error": result.error, "evidenceIds": [e.id for e in result.evidence],
            "recordIds": list(result.recordIds), "passageIds": [p.id for p in result.passages], "artifactIds": artifacts}
    # As JSON reads it: a summary may hold a value JSON has no word for, which it says as text.
    db.run(_call(projects.current(), turn_id, tool, json.loads(json.dumps(args, default=str)),
                 json.loads(json.dumps(kept, default=str)), by))
    return artifacts


async def _finish(project_id: str, turn_id: str, change: dict[str, Any]) -> None:
    async with db.session() as s:
        body = await rows.body(s, t.turns, project_id, turn_id, for_update=True)
        if body is None:
            raise ConversationNotFound(f"the project holds no turn {turn_id}")
        merged = {**body, **change}
        await s.execute(update(t.turns).where(t.turns.c.project_id == project_id, t.turns.c.id == turn_id)
                        .values(body=merged, status=merged["status"], updated_at=func.clock_timestamp()))


def finish(turn_id: str, *, plan: AnswerPlan | None, steps: list[TraceStep], artifacts: list[str] | None = None,
           error: TurnError | None = None, stopped: bool = False) -> str:
    """A turn kept as it ended: `answered` with its plan (a declined plan is an answer),
    `stopped` when nobody was waiting, `failed` with the words why."""
    status = "failed" if error is not None else "stopped" if stopped else "answered"
    found = list(artifacts or [])
    for aid in _artifacts(plan.evidence if plan is not None else []):
        if aid not in found:
            found.append(aid)
    pid = projects.current()
    try:
        db.run(_finish(pid, turn_id, {"status": status, "steps": [x.model_dump(mode="json") for x in steps],
                                      "plan": plan.model_dump(mode="json") if plan is not None else None,
                                      "error": error.model_dump(mode="json") if error is not None else None,
                                      "artifactIds": found}))
    finally:
        with _lock:
            _answering.discard((pid, turn_id))
    return status


async def _merge(project_id: str, page: LiveConversation, by: str) -> None:
    async with db.session() as s:
        await db.lock(s, "conversation", project_id, page.id)
        await _started(s, project_id, page.id, page.title, page.startedAt, by)
        seq = (await s.execute(select(func.coalesce(func.max(t.turns.c.seq), 0)).where(
            t.turns.c.project_id == project_id, t.turns.c.conversation_id == page.id))).scalar()
        for turn in page.turns:
            held = (await s.execute(select(t.turns.c.conversation_id, t.turns.c.seq, t.turns.c.status).where(
                t.turns.c.project_id == project_id, t.turns.c.id == turn.id))).first()
            if held is not None and held.conversation_id != page.id:
                raise ConversationRefused(f"turn {turn.id} belongs to conversation {held.conversation_id}, not {page.id}")
            if held is not None and not _open(project_id, turn.id, held.status):
                continue  # as the service kept it
            if held is None:
                seq += 1
            await rows.put(s, t.turns, project_id, turn.id, turn.model_dump(mode="json"), by=by,
                           conversation_id=page.id, seq=held.seq if held is not None else seq, status=turn.status)


def merge(page: dict[str, Any], *, by: str) -> None:
    """A Live conversation as the page holds it, laid onto what the service keeps: the
    conversation begun when it is new, each turn the service does not hold kept as the page
    wrote it, each it holds left as the service kept it."""
    try:
        conversation = LiveConversation.model_validate(page)
    except ValueError as e:
        raise ConversationRefused(f"a conversation row is a Live conversation: {str(e).splitlines()[0]}") from None
    for turn in conversation.turns:
        if not ID.match(turn.id):
            raise ConversationRefused(f"{turn.id!r} is not an id: letters, digits and . _ : | -, at most 200")
    db.run(_merge(projects.current(), conversation, (by or "").strip() or "this browser"))


def error_of(message: str, remedy: str = "The service log names what went wrong.") -> TurnError:
    return TurnError(message=message, remedy=remedy)
