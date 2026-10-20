"""The audit log (OF-BLD-015 §7.3): every write a model makes, and every
proposal a person carries out or dismisses, appended as one line.

`core/data/audit.jsonl`, one JSON object a line, appended under the same
two locks the other stores use (the service's threads, and another process
through the advisory file lock). It is never rewritten: a line that was
appended stays. It is gitignored and stays on the machine, like `spend.json`.

A line says who did it: `agent` is `model` or `person`; `who` is the model
id or the person's name; a model's line carries the effort and the ask it
was part of. The module, the action, the target and the state the write
left behind are what a review reads (§7.R).
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from . import atomic, intake
from .models import AuditEntry

PATH = intake.DATA_DIR / "audit.jsonl"
_LOCK = threading.Lock()
MAX_READ = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append(
    *,
    agent: str,
    who: str,
    module: str,
    action: str,
    state: str,
    target: str | None = None,
    ask_id: str | None = None,
    effort: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEntry:
    entry = AuditEntry(at=_now(), agent=agent, who=who, module=module, action=action, state=state, target=target,  # type: ignore[arg-type]
                       askId=ask_id or None, effort=effort, detail=detail or {})
    line = entry.model_dump_json() + "\n"
    with _LOCK, atomic.held(PATH):
        PATH.parent.mkdir(parents=True, exist_ok=True)
        with PATH.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
    return entry


def read(limit: int = MAX_READ) -> list[AuditEntry]:
    """The newest `limit` lines, newest last. A damaged line is skipped and
    counted nowhere: the log is evidence of what happened, never repaired."""
    if not PATH.exists():
        return []
    out: list[AuditEntry] = []
    with _LOCK, atomic.held(PATH):
        lines = PATH.read_text(encoding="utf-8").splitlines()
    for raw in lines[-max(0, limit):]:
        try:
            out.append(AuditEntry.model_validate(json.loads(raw)))
        except Exception:
            continue
    return out
