"""The one PostgreSQL engine (ADR-001; execution prompt §4.1, §8.1).

SQLAlchemy 2 async over asyncpg, the driver Sci RAG Kit uses, so the service
and the kit share one driver and one instance. The address is
OPENFERMENT_DATABASE_URL (core/.env); a plain `postgresql://` address is given
the asyncpg dialect here.

The store functions keep their synchronous names and signatures (§8.1), and
everything that calls them is synchronous: the routes FastAPI runs in its
threadpool, the tool registry, Postdoc's loop, the MCP server, the commands and
the tests. They reach the async engine through `run`, which hands a coroutine
to one event loop this module owns, on a thread of its own, and waits for the
answer. Every pooled connection is made and used on that loop, which is what
asyncpg requires of a connection. An async caller awaits `arun` instead and
leaves its own loop free while the database works.
"""
from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

T = TypeVar("T")

URL_SETTING = "OPENFERMENT_DATABASE_URL"
#: Our tables live in this schema; Sci RAG Kit's live in `sci_rag` (ADR-001).
SCHEMA = "openferment"
#: The database a host serves from. `db:reset` refuses it by name.
PRODUCTION_NAME = "openferment"


class DatabaseUnavailable(RuntimeError):
    """No database address is set, or the database does not answer."""


def as_async(url: URL | str) -> URL:
    """`url` with the asyncpg dialect, whichever PostgreSQL dialect it named."""
    parsed = make_url(url) if isinstance(url, str) else url
    if parsed.get_backend_name() != "postgresql":
        raise DatabaseUnavailable(f"{parsed.render_as_string(hide_password=True)} is not a PostgreSQL address")
    return parsed.set(drivername="postgresql+asyncpg")


def database_url() -> URL:
    """The configured address, read at call time so a test can move it."""
    raw = os.environ.get(URL_SETTING, "").strip()
    if not raw:
        raise DatabaseUnavailable(
            f"{URL_SETTING} is not set. Put it in core/.env: "
            "postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev for `pnpm db:up`, "
            "then run `pnpm db:migrate`."
        )
    return as_async(raw)


# ── The loop every connection lives on ────────────────────────────────────


class _Loop:
    """One event loop on one daemon thread, started on first use."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None

    def get(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self.loop is None or self.loop.is_closed() or not (self.thread and self.thread.is_alive()):
                loop = asyncio.new_event_loop()
                started = threading.Event()

                def serve() -> None:
                    asyncio.set_event_loop(loop)
                    loop.call_soon(started.set)
                    loop.run_forever()

                thread = threading.Thread(target=serve, name="openferment-db", daemon=True)
                thread.start()
                started.wait()
                self.loop, self.thread = loop, thread
            return self.loop


_LOOP = _Loop()


def on_database_thread() -> bool:
    return threading.current_thread() is _LOOP.thread


def run(coro: Coroutine[Any, Any, T]) -> T:
    """Run `coro` on the database loop and return its result, from any
    synchronous caller. A store's coroutine calls another store's coroutine
    directly; calling `run` from the database thread would wait on itself, so
    it refuses instead."""
    if on_database_thread():
        coro.close()
        raise RuntimeError("db.run was called on the database thread: await the coroutine there instead")
    return asyncio.run_coroutine_threadsafe(coro, _LOOP.get()).result()


async def arun(coro: Coroutine[Any, Any, T]) -> T:
    """`run` for an async caller: its own loop stays free while it waits."""
    return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, _LOOP.get()))


# ── The engine ────────────────────────────────────────────────────────────


def make_engine(url: URL | str, **kw: Any) -> AsyncEngine:
    """An engine for `url` whose connections put `public` alone on the search
    path. Our tables are always named with their schema; the pinned path keeps
    reflection honest, because a role named `openferment` would otherwise find
    its own schema first (`"$user"`) and reflection would call it the default."""
    return create_async_engine(as_async(url), connect_args={"server_settings": {"search_path": "public"}}, **kw)


_ENGINE: AsyncEngine | None = None
_ENGINE_LOCK = threading.Lock()


def engine() -> AsyncEngine:
    """The service's engine, made on first use from `database_url()`."""
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = make_engine(database_url(), pool_pre_ping=True, pool_size=5, max_overflow=5)
        return _ENGINE


def use_engine(replacement: AsyncEngine | None) -> AsyncEngine | None:
    """Swap the engine (the tests' database, a command's own address) and
    return the one it replaced, which the caller disposes of or restores."""
    global _ENGINE
    with _ENGINE_LOCK:
        previous, _ENGINE = _ENGINE, replacement
        return previous


async def _dispose(e: AsyncEngine) -> None:
    await e.dispose()


def dispose() -> None:
    """Close the pool, so a forked or exiting process leaves no connection."""
    e = use_engine(None)
    if e is not None:
        run(_dispose(e))
