"""A project's event stream (execution prompt §7.3 item 2): `GET /api/events?project=`.

Every worker job, tool call, artifact and Postdoc turn says what happened as it happens,
so a page renders a card for it then rather than after:

    job.queued, job.running, job.done, job.failed   an engine run, by its run id
    tool.call, tool.result                          a tool a Postdoc turn called, with the turn
    artifact.kept                                   an artifact kept, by its id and its tool
    turn.started, turn.delta, turn.plan, turn.decline
                                                    a Postdoc turn: begun, each step of its loop
                                                    as it completes, and its validated plan
                                                    (`turn.decline` when the plan declines)

An event is `{id, type, at, project, data}`: `id` counts up in this process, so a page that
reconnects with `Last-Event-ID` is sent what it missed from the newest events this process
holds, and a page that names no event is sent what happens from when it opens the stream (it
opens the stream, then reads the record). The stream is how a page sees work happen; the record of it is the tables (runs,
artifacts, turns, tool_calls), which a page reads on load. Events stay in this process and
in memory: nothing reads them back after a restart. A page that falls BEHIND by more unread
events than this process will hold for it is closed; it reconnects from the last event it
read, as an EventSource does.
"""
from __future__ import annotations

import asyncio
import collections
import itertools
import json
import queue
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterator

from pydantic import BaseModel

from . import projects

TYPES = ("job.queued", "job.running", "job.done", "job.failed", "tool.call", "tool.result", "artifact.kept",
         "turn.started", "turn.delta", "turn.plan", "turn.decline")
# The newest events kept for a page that reconnects, across every project.
KEPT = 2000
# A page that reads nothing for this long is sent a comment, so a proxy keeps the stream open.
HEARTBEAT_S = 15.0
# How many unread events one page may fall behind before it is closed (it reconnects and resumes).
BEHIND = 1000
# How often a stream looks for an event: an event reaches its page within this.
POLL_S = 0.05


class Event(BaseModel):
    id: int
    type: str
    at: str
    project: str
    data: dict[str, Any]


_lock = threading.Lock()
_ids = itertools.count(1)
_kept: collections.deque[Event] = collections.deque(maxlen=KEPT)
# Each reading page's inbox; None in an inbox closes its stream.
_readers: dict[int, tuple[str, queue.Queue]] = {}
_reader_ids = itertools.count(1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish(type_: str, data: dict[str, Any], *, project: str | None = None) -> Event | None:
    """Say one thing that happened in a project (the current one when none is named); None
    when no project is open, as in a command that acts in none."""
    if type_ not in TYPES:
        raise ValueError(f"{type_!r} is not an event type: {', '.join(TYPES)}")
    pid = project or projects.current_or_none()
    if pid is None:
        return None
    with _lock:
        event = Event(id=next(_ids), type=type_, at=_now(), project=pid, data=data)
        _kept.append(event)
        for rid, (owner, inbox) in list(_readers.items()):
            if owner != pid:
                continue
            if inbox.qsize() < BEHIND:
                inbox.put_nowait(event)
            else:
                inbox.put_nowait(None)
                del _readers[rid]
    return event


def newest() -> int:
    """The id of the newest event this process holds, in any project; 0 when it holds none."""
    with _lock:
        return _kept[-1].id if _kept else 0


def recent(project: str, after: int = 0) -> list[Event]:
    """The kept events of a project after `after`, oldest first."""
    with _lock:
        return [e for e in _kept if e.project == project and e.id > after]


@contextmanager
def reader(project: str) -> Iterator[queue.Queue]:
    """An inbox of the project's events from now on, until the block ends."""
    inbox: queue.Queue = queue.Queue()
    with _lock:
        rid = next(_reader_ids)
        _readers[rid] = (project, inbox)
    try:
        yield inbox
    finally:
        with _lock:
            _readers.pop(rid, None)


def sse(event: Event) -> str:
    return f"id: {event.id}\nevent: {event.type}\ndata: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"


async def stream(project: str, after: int | None = None, *, heartbeat_s: float | None = None,
                 until: Any = None) -> AsyncIterator[str]:
    """The project's events as server-sent events: first those kept since `after` (none when
    `after` is None), then each as it happens, a comment when nothing has for `heartbeat_s`
    (HEARTBEAT_S). It waits on the event loop and holds no thread, so every page may keep one
    open. It ends when the page has fallen BEHIND, and when `until` (a callable, for a test)
    returns true. An event said while the stream opens is sent once."""
    beat = heartbeat_s or HEARTBEAT_S
    last = newest() if after is None else after
    with reader(project) as inbox:
        for e in recent(project, last):
            last = e.id
            yield sse(e)
        quiet = time.monotonic()
        while not (until and until()):
            try:
                e = inbox.get_nowait()
            except queue.Empty:
                if time.monotonic() - quiet >= beat:
                    quiet = time.monotonic()
                    yield ": keepalive\n\n"
                else:
                    await asyncio.sleep(min(POLL_S, beat))
                continue
            if e is None:
                return
            quiet = time.monotonic()
            if e.id > last:
                last = e.id
                yield sse(e)
