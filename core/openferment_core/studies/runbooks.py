"""Runbooks from a study (execution prompt §9.1 step 5; OF-BLD-006 §3).

A runbook commits, before a fermenter is touched, to what a run predicts and
what the bench will measure. A study makes one from an engine run: each
output the request names (`outputs.<key>` of a flowsheet's outputs, or
`price.<key>` of the price block) becomes a point prediction whose value
and unit are the run's, whose basis names the run (its id, its plant and
configuration, its provenance) and whose artifact is the run's, at
confidence `low`: a model's answer on its basis, which the bench has not
tested. Each prediction gets a measure the bench records at harvest. The
runbook is a row of `runbooks` in the shape the runbook page keeps
(`src/data/types.ts` `Runbook`), so it lists and opens there beside a
person's.

Locking freezes it. The service writes the digest the browser's own code
writes (runbook_lock.py, a port of src/engine/lock.ts) and the moment, into
`runbook_locks` and into the runbook, through project_state.py, which
audits the lock and from then on refuses a row whose predictions or
measures are not the ones frozen. A locked runbook is never edited; a
change is a new runbook.

A row is read and written as it is kept: a prediction's field the row
leaves out stays out, because the digest reads an absent field and a null
one differently (`exclude_unset`).

    POST /api/studies/runbooks              {title, runId, predict: [{output, label}], by}
    GET  /api/studies/runbooks              the runbooks studies made, newest first
    GET  /api/studies/runbooks/{id}         any runbook of the project
    POST /api/studies/runbooks/{id}/lock    {by}
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from .. import project_state
from ..engine import runs
from ..models import Measure, Prediction, Runbook, RunbookCreate
from ..runbook_lock import lock_hash

PREFIX = "rb-study-"
BY = "this browser"


class RunbookRefused(ValueError):
    """A runbook that cannot be made or locked, in words."""


class RunbookNotFound(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _row(book: Runbook) -> dict[str, Any]:
    return book.model_dump(mode="json", exclude_unset=True)


def _laid(row: dict[str, Any], locks: dict[str, dict[str, str]]) -> dict[str, Any]:
    """A runbook's row as kept, a lock the row does not carry laid on (as
    the page lays it on when the project loads)."""
    lock = locks.get(row.get("id"))
    return {**row, **lock} if lock and not row.get("lockedAt") else row


def _held(rid: str) -> dict[str, Any] | None:
    state = project_state.load()
    row = next((r for r in state["runbooks"] if r.get("id") == rid), None)
    return None if row is None else _laid(row, state["runbookLocks"])


def _value(output: dict[str, Any], key: str) -> tuple[Any, str | None]:
    """A run's `outputs.<key>` or `price.<key>`, with its unit."""
    block, _, name = key.partition(".")
    if block == "outputs":
        return (output.get("outputs") or {}).get(name), (output.get("outputUnits") or {}).get(name)
    if block == "price":
        price = output.get("price") or {}
        return price.get(name), (price.get("units") or {}).get(name)
    return None, None


def runbook_id(run_id: str, outputs: list[str]) -> str:
    """`rb-study-` and twelve hex of the run and the outputs it predicts:
    the same run predicting the same outputs is one runbook."""
    text = json.dumps({"run": run_id, "outputs": outputs}, separators=(",", ":"))
    return PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def make(asked: RunbookCreate) -> Runbook:
    """A runbook whose predictions are an engine run's outputs, kept among
    the project's runbooks. The same run and outputs asked again are the
    runbook kept already, as it stands: a person may have revised a draft's
    predictions, and a locked one is frozen."""
    try:
        report = runs.report(asked.runId)
    except runs.RunNotFound as e:
        raise RunbookRefused(str(e).strip("'\"")) from None
    run, art = report.run, report.artifact
    if run.status != "done" or art is None:
        raise RunbookRefused(f"run {run.id} was refused by its plant ({run.refused}), so it predicts nothing")
    keys = [p.output for p in asked.predict]
    if len(set(keys)) != len(keys):
        raise RunbookRefused("a runbook predicts each output once")
    rid = runbook_id(run.id, keys)
    if _held(rid) is not None:
        return get(rid)
    where = run.plant + (f" ({run.configuration})" if run.configuration else "")
    predictions, measures = [], []
    for n, item in enumerate(asked.predict, start=1):
        value, unit = _value(art.output, item.output)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or unit is None:
            raise RunbookRefused(f"run {run.id} answers no number with a unit for {item.output}; it answers "
                                 "outputs.<key> of a flowsheet's outputs and price.<key> of its price")
        predictions.append(Prediction(
            id=f"p{n}", label=item.label, value=float(value), unit=unit, confidence="low", artifactId=art.id,
            basis=f"engine run {run.id} of {where}, {run.provenance}: its {item.output}"))
        measures.append(Measure(id=f"m{n}", label=item.label, unit=unit, timepoint="harvest", predictionId=f"p{n}"))
    book = Runbook(
        id=rid, kind="research", title=asked.title.strip(), status="draft", stages=[],
        note=(f"Made from engine run {run.id} of {where} ({run.provenance}): each prediction is the run's value "
              "in the run's unit, written by the service. The bench measures each at harvest."),
        eta=None, outputs=[], productId=None, progressPct=0, estCostUsd=None, strainId=None,
        predictions=predictions, measurementSchema=measures, lockedAt=None, lockHash=None)
    project_state.put("runbooks", rid, _row(book), (asked.by or "").strip() or BY)
    return book


def _valid(rid: str, row: dict[str, Any]) -> Runbook:
    try:
        return Runbook.model_validate(row)
    except ValidationError as e:
        problem = e.errors()[0]
        raise RunbookRefused(f"{rid} is not kept in the runbook page's shape ({'.'.join(map(str, problem['loc']))}: "
                             f"{problem['msg']})") from None


def _read(rid: str) -> tuple[dict[str, Any], Runbook]:
    row = _held(rid)
    if row is None:
        raise RunbookNotFound(f"the project holds no runbook {rid}")
    return row, _valid(rid, row)


def get(rid: str) -> Runbook:
    """A runbook of the project, a study's or a person's."""
    return _read(rid)[1]


def listed() -> list[Runbook]:
    """The runbooks studies made, newest first."""
    state = project_state.load()
    return [_valid(r["id"], _laid(r, state["runbookLocks"]))
            for r in reversed(state["runbooks"]) if str(r.get("id", "")).startswith(PREFIX)]


def lock(rid: str, *, by: str = "") -> Runbook:
    """The runbook's predictions and measures frozen under the digest the
    browser writes, with the moment: the lock first, which a second lock
    is refused against, then the row that carries it. Refused when the
    runbook is locked already or predicts nothing."""
    row, book = _read(rid)
    if book.lockedAt:
        raise RunbookRefused(f"{rid} is locked already; a lock is kept as it was made, and a change is a new runbook")
    if not book.predictions:
        raise RunbookRefused(f"{rid} predicts nothing, so it has made no claim to lock")
    # Over the row as kept, which the page hashes when it reads the lock.
    frozen = {"lockedAt": _now(), "lockHash": lock_hash(row["predictions"], row["measurementSchema"])}
    who = (by or "").strip() or BY
    try:
        project_state.put("runbookLocks", rid, frozen, who)
    except project_state.StateRefused as e:
        raise RunbookRefused(str(e)) from None
    project_state.put("runbooks", rid, {**row, **frozen}, who)
    return get(rid)
