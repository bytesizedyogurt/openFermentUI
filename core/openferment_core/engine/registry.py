"""The engines this service found (docs/api/engines.md, What the service does
with an engine; ADR-015).

Every object registered under the entry-point group `openferment.engines` is
loaded once, when the service starts (api.py) or at the first ask, and checked
for what the contract has it declare. One that fails to load, lacks a
declaration, or shares its name with another package's is kept with its error
in words, and the service runs on without it: two packages naming one engine
are both set aside, except that the core's own engine (the distribution
`openferment-core`) keeps its name and the other is set aside. The core
imports no engine by name: its own register through core/pyproject.toml like
any other package's.
"""
from __future__ import annotations

import importlib.metadata
import re
import threading
from dataclasses import dataclass
from typing import Any

from ..models import ENGINE_NAME, EngineInfo
from . import METHODS, Engine

GROUP = "openferment.engines"
# The distribution whose engines keep their names against another package's.
CORE_DISTRIBUTION = "openferment-core"


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
_LOCK = threading.Lock()


def _distribution(ep: Any) -> str | None:
    dist = getattr(ep, "dist", None)
    return getattr(dist, "name", None) if dist is not None else None


def entry_points() -> list[importlib.metadata.EntryPoint]:
    """The group's entry points, in name order (tests stand in here)."""
    return sorted(importlib.metadata.entry_points(group=GROUP), key=lambda e: (e.name, e.value))


def _why_not(name: str, entry: str, obj: Any) -> str | None:
    """Why the loaded object cannot serve as engine `name`, in words; None when it can."""
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


def _discover() -> tuple[dict[str, Found], list[Found]]:
    from . import runs

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
        ep = eps[0]
        try:
            obj = ep.load()
        except Exception as e:  # any failure to load is the engine's, said in words
            found[ep.name] = Found(ep.name, ep.value, None, f"{ep.value} could not be loaded: {type(e).__name__}: {e}")
            continue
        why = _why_not(ep.name, ep.value, obj)
        found[ep.name] = Found(ep.name, ep.value, None if why else obj, why)
        if why is None and hasattr(obj, "compute"):
            runs.register_engine_tool(obj)
    return found, aside


def found() -> dict[str, Found]:
    """Every engine registered here, loaded on the first ask."""
    global _FOUND, _ASIDE
    with _LOCK:
        if _FOUND is None:
            _FOUND, _ASIDE = _discover()
        return _FOUND


def set_aside() -> list[Found]:
    """The entry points that could not take their name, each with its words."""
    found()
    return list(_ASIDE)


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
    try:
        version, things, error = e.version(), e.things(), None
    except Exception as ex:  # a method that fails is said, and the engine still listed
        version, things, error = {}, [], f"{type(ex).__name__}: {ex}"
    return EngineInfo(name=name, entryPoint=f.entry, version=version, worker=e.worker, workerStatus=status_of(e),
                      heavy=list(e.heavy), things=things, conformance=verdict, error=error)


def infos() -> list[EngineInfo]:
    """Every engine, then every entry point set aside, each with its words."""
    return [info(n) for n in names()] + [EngineInfo(name=f.name, entryPoint=f.entry, error=f.error)
                                         for f in set_aside()]
