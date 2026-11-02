"""Sessions: one transaction per top-level store call (execution prompt §8.1).

`session()` opens a session and its transaction on the database loop. A store
function that runs inside another's transaction joins it, so a review decision
and its audit row commit together or not at all. Row locks and the
transaction-scoped advisory lock `lock` take the place of the file stores'
`_WRITE_LOCK`, their file locks and their atomic writes.

The tests bind every session to one connection inside an outer transaction
(`Binding`) that is rolled back after each test: each session is a savepoint
on it, and the sessions take turns on the one connection.
"""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from .engine import engine

_HELD: ContextVar[AsyncSession | None] = ContextVar("openferment_db_session", default=None)


class Binding:
    """One connection inside one transaction that is never committed. It is
    opened when a session first asks for it, so a test that never touches
    the database never connects; `prepare` runs once on it when it opens."""

    def __init__(
        self,
        engine: AsyncEngine | Callable[[], Awaitable[AsyncEngine]],
        prepare: Callable[[AsyncConnection], Awaitable[None]] | None = None,
    ) -> None:
        # An engine, or a coroutine function that makes one when it is first
        # needed (the tests make their database then).
        self.engine = engine
        self.prepare = prepare
        self.connection: AsyncConnection | None = None
        self.turn = asyncio.Lock()

    async def connect(self) -> AsyncConnection:
        if self.connection is None:
            if not isinstance(self.engine, AsyncEngine):
                self.engine = await self.engine()
            connection = await self.engine.connect()
            await connection.begin()
            self.connection = connection
            if self.prepare is not None:
                await self.prepare(connection)
        return self.connection

    async def close(self) -> None:
        """Roll everything back and give the connection up."""
        if self.connection is not None:
            connection, self.connection = self.connection, None
            await connection.rollback()
            await connection.close()


_BINDING: Binding | None = None


def bind(binding: Binding | None) -> Binding | None:
    """Make every new session a savepoint of `binding` (None undoes it); the
    binding it replaced."""
    global _BINDING
    previous, _BINDING = _BINDING, binding
    return previous


@asynccontextmanager
async def _hold(s: AsyncSession) -> AsyncIterator[AsyncSession]:
    async with s.begin():
        token = _HELD.set(s)
        try:
            yield s
        finally:
            _HELD.reset(token)


@asynccontextmanager
async def session() -> AsyncIterator[AsyncSession]:
    """The session of the transaction under way, or a new one that commits
    when the block ends and rolls back if it raises."""
    held = _HELD.get()
    if held is not None:
        yield held
        return
    binding = _BINDING
    if binding is None:
        async with AsyncSession(engine(), expire_on_commit=False) as s, _hold(s) as held:
            yield held
        return
    async with binding.turn:
        connection = await binding.connect()
        async with (
            AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as s,
            _hold(s) as held,
        ):
            yield held


async def lock(s: AsyncSession, *key: str) -> None:
    """Hold an advisory lock on `key` (a store and a project, say) until the
    transaction ends: the read-check-write of a store's rules runs one at a
    time for that key, across every process on the database."""
    digest = hashlib.sha256("\x1f".join(key).encode("utf-8")).digest()
    await s.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": int.from_bytes(digest[:8], "big", signed=True)})
