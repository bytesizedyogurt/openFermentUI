"""The trains a model built, kept on the service (OF-BLD-020 §5.4).

A person's trains live in their browser (D9: `trainsMade` in the Durable tier)
and travel whole with a run. A model builds a train across tool calls
(`pureos_build`: new, add a unit, bind a parameter to records, run), and an
outside assistant over MCP has no ask to hold its draft between calls, so the
service holds a model's train here: rows of the `trains` table of kind
`kept`, under the current project (ADR-001), one `KeptTrain` a row (the train
as data, `madeBy` the model id, `agent` the word `model`, `at` and
`updatedAt`, the effort and the ask).

ONE WRITE FUNCTION. `keep_train` is the only function that writes the store:
every change is a read-modify-write in one transaction under the store's
advisory lock (`db.lock`), which holds across the service's requests and
every other process on the database. The change itself is the caller's
function of the train as it stands under the lock (None for a new one), so
two changes made at once never lose one another. `tools/writes.py` is the
only tool file that calls it (`ALLOWED_WRITES`); `check:tools` rule 2b finds
it from the table it writes (`TABLE` below) and holds every other tool file
away from it.

Nothing here builds, checks or runs a train: `pureos.build` shapes the train
as data, `pureos.train_spec.run_train` runs it, and a run is a
`pureos.train_run` artifact found by the train's id. The service keeps no
person's value: a model's train carries none (its inputs are ids and words),
so a value nothing binds waits at the run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .. import db, projects
from ..db import models as t
from ..db import rows
from ..models import KeptTrain, KeptTrains, TrainSpec

# The store's table and the kind of its rows (the Builder's trains are rows
# of kind `made`). check:tools rule 2b names this table: every function here
# that writes it keeps a model's train.
TABLE = "trains"
KIND = "kept"


class KeptTrainRefused(ValueError):
    """A change to a kept train that cannot be made, in words."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _read(project_id: str) -> KeptTrains:
    async with db.session() as s:
        held = await rows.bodies(s, t.trains, project_id, t.trains.c.kind == KIND)
    return KeptTrains(trains=[KeptTrain.model_validate(b) for b in held])


def read() -> KeptTrains:
    """Every kept train of the current project, in the order they were made;
    none when a model has built none."""
    return db.run(_read(projects.current()))


def keep_train(train_id: str | None, change: Callable[[TrainSpec | None], TrainSpec], by: str, agent: str = "model",
               *, ask_id: str | None = None, effort: str | None = None) -> KeptTrain:
    """Make or change one kept train, the one write to the store.

    `train_id` None makes a new train: `change(None)` returns it, and its id
    must be new. Otherwise `change(spec)` gets the train as it stands under
    the lock and returns it changed, its id unchanged. `change` is a function
    of the train alone: it runs inside the store's transaction, on the
    database's own thread, where a call to another store is refused. `by` is
    the model's id; `agent` is `model`, always (a person's trains live in
    their browser). A refusal from `change` (any ValueError) leaves the store
    as it was. Returns the train as kept."""
    if agent != "model":
        raise KeptTrainRefused("a kept train is a model's: a person's trains live in their browser and travel with "
                               "a run")
    who = (by or "").strip()
    if not who:
        raise KeptTrainRefused("a kept train names the model that made it")
    return db.run(_keep(projects.current(), train_id, change, who, effort=effort or None, ask_id=ask_id or None))


async def _keep(project_id: str, train_id: str | None, change: Callable[[TrainSpec | None], TrainSpec], who: str, *,
                effort: str | None, ask_id: str | None) -> KeptTrain:
    async with db.session() as s:
        await db.lock(s, TABLE, project_id)
        store = KeptTrains(trains=[KeptTrain.model_validate(b)
                                   for b in await rows.bodies(s, t.trains, project_id, t.trains.c.kind == KIND)])
        at = _now()
        if train_id is None:
            spec = change(None)
            if any(k.spec.id == spec.id for k in store.trains):
                raise KeptTrainRefused(f"a kept train is already named {spec.id}")
            if await rows.body(s, t.trains, project_id, spec.id) is not None:
                raise KeptTrainRefused(f"a train is already named {spec.id} in this project")
            kept = KeptTrain(spec=spec, agent="model", madeBy=who, effort=effort, askId=ask_id, at=at, updatedAt=at)
        else:
            current = next((k for k in store.trains if k.spec.id == train_id), None)
            if current is None:
                raise KeptTrainRefused(f"there is no kept train {train_id} here; pureos_read lists the trains a model "
                                       "built (kind train)")
            spec = change(current.spec)
            if spec.id != train_id:
                raise KeptTrainRefused(f"a change keeps the train's id, {train_id}")
            kept = current.model_copy(update={"spec": spec, "updatedAt": at})
        await rows.put(s, t.trains, project_id, kept.spec.id, kept.model_dump(mode="json"), by=who, kind=KIND)
    return kept


def kept_train(train_id: str) -> KeptTrain | None:
    """One kept train by its id, or None."""
    return next((k for k in read().trains if k.spec.id == train_id), None)


def listed() -> list[KeptTrain]:
    """`GET /api/pureos/trains-kept`: every kept train, the most recently
    changed first. A read."""
    return sorted(read().trains, key=lambda k: (k.updatedAt, k.spec.id), reverse=True)
