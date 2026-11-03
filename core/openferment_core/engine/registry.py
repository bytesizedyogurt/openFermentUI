"""The engines this service found (docs/api/engines.md, What the service does
with an engine; ADR-015).

Every object registered under the entry-point group `openferment.engines` is
loaded once, when the service starts (api.py) or at the first ask, and checked
for what the contract has it declare. One that fails to load (whatever it
raises, SystemExit included; a KeyboardInterrupt alone goes on), lacks a
declaration, raises while it is checked, brings into the service's process
its worker module, a heavy module it declares or a library of
`workers.WORKER_LIBRARIES`, or shares its name with another package's is kept
with its error in words, and the service runs on without it: two packages
naming one engine are both set aside, except that the core's own engine (the
distribution `openferment-core`) keeps its name and the other is set aside.
The heavy modules counted are those an entry module's import brings in that
the service had not imported already; an engine set aside for them has them
taken out of `sys.modules`, so the next entry point's import is measured
afresh. Conformance check 6, in a process of its own, holds every declared
module out. An entry module that asks the registry while it is being
imported, from its own thread or one it starts, is answered as though no
engine were found yet. Discovery runs during startup with no time limit of
its own, so an entry module's import returns promptly. The core imports no
engine by name: its own register through core/pyproject.toml like any other
package's.
"""
from __future__ import annotations

import importlib.metadata
import re
import sys
import threading
from dataclasses import dataclass
from typing import Any

from ..models import ENGINE_NAME, ENGINE_NAME_MAX, EngineInfo
from ..workers import WORKER_LIBRARIES, covers
from . import METHODS, Engine

GROUP = "openferment.engines"
# The distribution whose engines keep their names against another package's.
CORE_DISTRIBUTION = "openferment-core"
# How long `GET /api/engines` waits on a cold worker's first `things`; once
# answered, a WorkerEngine keeps its things for the life of the process.
LISTING_TIMEOUT_S = 30.0
# How long a call from another thread waits for discovery in progress before
# it is answered with nothing: a thread an entry module starts and waits on
# gets its answer, and discovery goes on.
DISCOVERY_WAIT_S = 10.0


class EngineNotFound(LookupError):
    """No engine of that name is registered here."""


class EngineUnavailable(RuntimeError):
    """The engine is registered and cannot be used: it failed to load or to declare what it must."""


@dataclass
class Found:
    name: str
    # The entry point's value, `package.module:ENGINE`.
    entry: str
    engine: Any | None
    error: str | None = None


_FOUND: dict[str, Found] | None = None
# Entry points set aside because the core's own engine holds their name.
_ASIDE: list[Found] = []
# Reentrant, with `_DISCOVERING` set while the group loads: an entry module
# that asks the registry as it is imported is answered at once, with nothing.
_LOCK = threading.RLock()
_DISCOVERING = False


def _distribution(ep: Any) -> str | None:
    dist = getattr(ep, "dist", None)
    return getattr(dist, "name", None) if dist is not None else None


def entry_points() -> list[importlib.metadata.EntryPoint]:
    """The group's entry points, in name order (tests stand in here)."""
    return sorted(importlib.metadata.entry_points(group=GROUP), key=lambda e: (e.name, e.value))


def _why_not(name: str, entry: str, obj: Any) -> str | None:
    """Why the loaded object cannot serve as engine `name`, in words; None when it can."""
    if len(name) > ENGINE_NAME_MAX:
        return f"the entry point's name {name!r} is longer than an engine name's {ENGINE_NAME_MAX} characters"
    if not re.match(ENGINE_NAME, name):
        return (f"the entry point's name {name!r} is no engine name: lowercase letters, digits and -, starting "
                "with a letter")
    own = getattr(obj, "name", None)
    if own != name:
        return f"the object at {entry} names itself {own!r} where its entry point names {name!r}"
    worker = getattr(obj, "worker", None)
    if worker is not None and not (isinstance(worker, str) and worker.strip()):
        return f"the object at {entry} declares a worker that is no dotted module name"
    heavy = getattr(obj, "heavy", None)
    if not isinstance(heavy, (tuple, list)) or not all(isinstance(h, str) for h in heavy):
        return f"the object at {entry} declares no heavy modules (a tuple of names, () for none)"
    if worker is None and heavy:
        return (f"the object at {entry} computes with {', '.join(heavy)} and declares no worker to keep them in, "
                "out of the service's process")
    missing = [m for m in METHODS if not callable(getattr(obj, m, None))]
    if missing:
        return f"the object at {entry} lacks {', '.join(missing)}"
    return None


def _words(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"


def kept_out(obj: Any) -> tuple[str, set[str]]:
    """What the service's process keeps out for an engine: its worker module
    (and every module below it), and the heavy modules, each with every module
    below it, that it declares beside `workers.WORKER_LIBRARIES`."""
    return obj.worker or "", set(obj.heavy) | set(WORKER_LIBRARIES)


def in_worker(module: str, worker: str, heavy: set[str]) -> bool:
    """Whether `module` belongs in the worker's process (`kept_out`)."""
    return bool(worker and covers(worker, module)) or any(covers(h, module) for h in heavy)


def _imported_in_service(obj: Any, new: set[str]) -> list[str]:
    """The modules loading the entry point brought into this process that
    belong in the engine's worker (`kept_out`), sorted."""
    worker, heavy = kept_out(obj)
    return sorted(m for m in new if in_worker(m, worker, heavy))


def _load(ep: Any) -> Found:
    """One entry point loaded and checked. Whatever it raises is kept as its
    words (a KeyboardInterrupt alone goes on), so no engine stops the service.
    An engine set aside for the heavy modules its import brought in has them
    taken out of `sys.modules`, so another engine importing them is measured
    afresh."""
    from . import runs

    before = set(sys.modules)
    try:
        obj = ep.load()
    except KeyboardInterrupt:
        raise
    except BaseException as e:  # any failure to load is the engine's, said in words
        return Found(ep.name, ep.value, None, f"{ep.value} could not be loaded: {_words(e)}")
    try:
        why = _why_not(ep.name, ep.value, obj)
        if why is None:
            wrong = _imported_in_service(obj, set(sys.modules) - before)
            if wrong:
                why = f"importing {ep.value} imported {', '.join(wrong[:8])}, which belong in its worker"
                for m in wrong:
                    sys.modules.pop(m, None)
        if why is None and callable(getattr(obj, "compute", None)):
            runs.register_engine_tool(obj)
    except KeyboardInterrupt:
        raise
    except BaseException as e:  # a declaration or a version that raises, said in words
        return Found(ep.name, ep.value, None, f"{ep.value} could not be checked: {_words(e)}")
    return Found(ep.name, ep.value, None if why else obj, why)


def _discover() -> tuple[dict[str, Found], list[Found]]:
    named: dict[str, list[Any]] = {}
    for ep in entry_points():
        named.setdefault(ep.name, []).append(ep)
    found: dict[str, Found] = {}
    aside: list[Found] = []
    for name, eps in named.items():
        if len(eps) > 1:
            core = [ep for ep in eps if _distribution(ep) == CORE_DISTRIBUTION]
            if len(core) != 1:
                found[name] = Found(name, eps[0].value, None, f"{len(eps)} packages register an engine named "
                                    f"{name!r} ({' and '.join(ep.value for ep in eps)}), so none is used")
                continue
            aside += [Found(name, ep.value, None, f"the core's own engine is named {name!r} ({core[0].value}), so "
                                                  f"{ep.value} is set aside") for ep in eps if ep is not core[0]]
            eps = core
        found[eps[0].name] = _load(eps[0])
    return found, aside


def found() -> dict[str, Found]:
    """Every engine registered here, loaded on the first ask. While the group
    loads, an entry module that asks as it is imported is answered with
    nothing at once, and another thread is answered when discovery ends, or
    with nothing after DISCOVERY_WAIT_S (a thread an entry module starts and
    waits on)."""
    global _FOUND, _ASIDE, _DISCOVERING
    if not _LOCK.acquire(timeout=DISCOVERY_WAIT_S):
        return {}
    try:
        if _DISCOVERING:
            return {}
        if _FOUND is None:
            _DISCOVERING = True
            try:
                _FOUND, _ASIDE = _discover()
            finally:
                _DISCOVERING = False
        return _FOUND
    finally:
        _LOCK.release()


def set_aside() -> list[Found]:
    """The entry points that could not take their name, each with its words;
    nothing while the group loads, as `found` answers."""
    if not _LOCK.acquire(timeout=DISCOVERY_WAIT_S):
        return []
    try:
        if _DISCOVERING:
            return []
        found()
        return list(_ASIDE)
    finally:
        _LOCK.release()


def reset() -> None:
    """Forget what was found, so the next ask reads the group again."""
    global _FOUND, _ASIDE
    with _LOCK:
        _FOUND, _ASIDE = None, []


def names() -> list[str]:
    return sorted(found())


def get(name: str) -> Engine:
    """The engine registered as `name`, ready to use."""
    f = found().get((name or "").strip())
    if f is None:
        raise EngineNotFound(f"no engine named {name!r} is registered here; the engines are "
                             f"{', '.join(names()) or 'none'}")
    if f.engine is None:
        raise EngineUnavailable(f"the engine {f.name} cannot be used: {f.error}")
    return f.engine


def status_of(engine: Any) -> str:
    """The engine's worker: `ready`, `cold`, `starting`, `failed`, or `none` for an engine with no worker."""
    if getattr(engine, "worker", None) is None:
        return "none"
    status = getattr(engine, "status", None)
    if callable(status):
        status = status()
    return str(status or "cold")


def info(name: str) -> EngineInfo:
    """One engine as `GET /api/engines` lists it: what it declares, what it
    runs, its worker and its last conformance verdict, or the error that
    keeps it from use."""
    from . import conform

    f = found()[name]
    verdict = conform.latest(name)
    if f.engine is None:
        return EngineInfo(name=name, entryPoint=f.entry, conformance=verdict, error=f.error)
    e = f.engine
    errors: list[str] = []
    try:
        version = e.version()
    except Exception as ex:  # a method that fails is said, and the engine still listed
        version = {}
        errors.append(f"its version could not be read: {_words(ex)}")
    try:
        things = _listed_things(e)
    except Exception as ex:  # a worker that fails or keeps the listing waiting is said
        things = []
        errors.append(f"its things could not be listed: {_words(ex)}")
    things_are = getattr(e, "things_are", None)
    return EngineInfo(name=name, entryPoint=f.entry, version=version, worker=e.worker, workerStatus=status_of(e),
                      heavy=list(e.heavy), things=things, thingsAre=str(things_are) if things_are else None,
                      conformance=verdict, error="; ".join(errors) or None)


def _listed_things(engine: Any) -> list[Any]:
    """An engine's things as the listing reads them: a WorkerEngine's from
    what it keeps, its cold worker given `LISTING_TIMEOUT_S` to answer first;
    any other engine's, a subclass's own `things()` among them, from
    `things()` as the Engine protocol has it."""
    from .contract import WorkerEngine

    own = type(engine).things is WorkerEngine.things and "things" not in getattr(engine, "__dict__", {})
    if isinstance(engine, WorkerEngine) and own:
        return engine.things(timeout_s=LISTING_TIMEOUT_S)
    return engine.things()


def infos() -> list[EngineInfo]:
    """Every engine, then every entry point set aside, each with its words."""
    return [info(n) for n in names()] + [EngineInfo(name=f.name, entryPoint=f.entry, error=f.error)
                                         for f in set_aside()]
