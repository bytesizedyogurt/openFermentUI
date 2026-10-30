"""The trains a model built, kept on the service (OF-BLD-020 §5.4).

A person's trains live in their browser (D9: `trainsMade` in the Durable tier)
and travel whole with a run. A model builds a train across tool calls
(`pureos_build`: new, add a unit, bind a parameter to records, run), and an
outside assistant over MCP has no ask to hold its draft between calls, so the
service holds a model's train here: `core/data/pureos-trains.json`, one
`KeptTrain` a train (the train as data, `madeBy` the model id, `agent` the
word `model`, `at` and `updatedAt`, the effort and the ask), gitignored and on
this machine alone, like the proposals and the audit log; it is not on the
data branch.

ONE WRITE FUNCTION. `keep_train` is the only function that writes the file:
every change is a read-modify-write under the store's two locks (a thread
lock for the service's requests, a file lock for another process), written
through `atomic.write_text`. The change itself is the caller's function of
the train as it stands under the lock (None for a new one), so two changes
made at once never lose one another. `tools/writes.py` is the only tool file
that calls it (`ALLOWED_WRITES`); `check:tools` rule 2b finds it from the
file name below and holds every other tool file away from it.

Nothing here builds, checks or runs a train: `pureos.build` shapes the train
as data, `pureos.train_spec.run_train` runs it, and a run is a
`pureos.train_run` artifact found by the train's id. The service keeps no
person's value: a model's train carries none (its inputs are ids and words),
so a value nothing binds waits at the run.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .. import atomic, intake
from ..models import KeptTrain, KeptTrains, TrainSpec

# The store's file, under the service's data directory. check:tools rule 2b
# names this file: every function here that writes it keeps a model's train.
FILE = "pureos-trains.json"
# The file's indentation, as the proposals' (a layout, not a process number).
JSON_INDENT = 2
_LOCK = threading.Lock()


class KeptTrainRefused(ValueError):
    """A change to a kept train that cannot be made, in words."""


def path() -> Path:
    """Where the store lives: read at call time, so a data directory set
    after import (a test's, `OPENFERMENT_DATA_DIR`) is the one used."""
    return intake.DATA_DIR / FILE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read() -> KeptTrains:
    """Every kept train as the file holds it; none when there is no file."""
    p = path()
    if not p.exists():
        return KeptTrains()
    return KeptTrains.model_validate_json(p.read_text(encoding="utf-8"))


def _persist(store: KeptTrains) -> None:
    atomic.write_text(path(), store.model_dump_json(indent=JSON_INDENT) + "\n")


def keep_train(train_id: str | None, change: Callable[[TrainSpec | None], TrainSpec], by: str, agent: str = "model",
               *, ask_id: str | None = None, effort: str | None = None) -> KeptTrain:
    """Make or change one kept train, the one write to the store.

    `train_id` None makes a new train: `change(None)` returns it, and its id
    must be new. Otherwise `change(spec)` gets the train as it stands under
    the lock and returns it changed, its id unchanged. `by` is the model's
    id; `agent` is `model`, always (a person's trains live in their
    browser). A refusal from `change` (any ValueError) leaves the store as it
    was. Returns the train as kept."""
    if agent != "model":
        raise KeptTrainRefused("a kept train is a model's: a person's trains live in their browser and travel with "
                               "a run")
    who = (by or "").strip()
    if not who:
        raise KeptTrainRefused("a kept train names the model that made it")
    p = path()
    with _LOCK, atomic.held(p):
        store = read()
        at = _now()
        if train_id is None:
            spec = change(None)
            if any(k.spec.id == spec.id for k in store.trains):
                raise KeptTrainRefused(f"a kept train is already named {spec.id}")
            kept = KeptTrain(spec=spec, agent="model", madeBy=who, effort=effort or None, askId=ask_id or None, at=at,
                             updatedAt=at)
            store.trains.append(kept)
        else:
            n = next((i for i, k in enumerate(store.trains) if k.spec.id == train_id), None)
            if n is None:
                raise KeptTrainRefused(f"there is no kept train {train_id} here; pureos_read lists the trains a model "
                                       "built (kind train)")
            spec = change(store.trains[n].spec)
            if spec.id != train_id:
                raise KeptTrainRefused(f"a change keeps the train's id, {train_id}")
            kept = store.trains[n].model_copy(update={"spec": spec, "updatedAt": at})
            store.trains[n] = kept
        _persist(store)
    return kept


def kept_train(train_id: str) -> KeptTrain | None:
    """One kept train by its id, or None."""
    return next((k for k in read().trains if k.spec.id == train_id), None)


def listed() -> list[KeptTrain]:
    """`GET /api/pureos/trains-kept`: every kept train, the most recently
    changed first. A read."""
    return sorted(read().trains, key=lambda k: (k.updatedAt, k.spec.id), reverse=True)
