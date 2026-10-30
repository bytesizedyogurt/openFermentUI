"""Migrations, and whole databases made and removed (execution prompt §8.1).

`upgrade` brings a database to the newest `openferment` schema through our
alembic history (`pnpm db:migrate`). `create`, `drop` and `reset` make and
remove whole databases on the same server, for the tests, the smoke and a
developer's fresh start (`pnpm db:reset NAME`). `reset` and `drop` refuse the
production database by its name, `PRODUCTION_NAME`, whatever address they
were given.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import pool, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError

from .engine import PRODUCTION_NAME, SCHEMA, as_async, database_url, make_engine

HERE = Path(__file__).parent
# A database name this module will create or drop: lower case, digits and
# underscores, so it never needs quoting rules beyond the double quotes.
NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class ResetRefused(ValueError):
    """Asked to drop a database that must not be dropped, or a bad name."""


def config(url: URL | str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(HERE / "alembic"))
    cfg.attributes["url"] = as_async(url)
    return cfg


def upgrade(url: URL | str | None = None, revision: str = "head") -> None:
    """Migrate the database at `url` (the configured one by default)."""
    command.upgrade(config(url or database_url()), revision)


def head() -> str:
    """The newest revision in our history."""
    from alembic.script import ScriptDirectory

    found = ScriptDirectory.from_config(config(URL.create("postgresql"))).get_current_head()
    if found is None:
        raise RuntimeError("the alembic history holds no revision")
    return found


async def _scalar(url: URL, sql: str) -> object:
    engine = make_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as c:
            return (await c.execute(text(sql))).scalar()
    finally:
        await engine.dispose()


def revision(url: URL | str | None = None) -> str | None:
    """The revision the database is at, or None before its first migration."""
    target = as_async(url or database_url())
    try:
        return asyncio.run(_scalar(target, f'SELECT version_num FROM "{SCHEMA}".alembic_version')) or None  # type: ignore[return-value]
    except ProgrammingError:
        return None


async def _autocommit(url: URL, sql: str) -> None:
    engine = make_engine(url, poolclass=pool.NullPool, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as c:
            await c.execute(text(sql))
    finally:
        await engine.dispose()


def _checked(name: str) -> str:
    if not NAME.match(name):
        raise ResetRefused(f"{name!r} is not a database name this command makes: lower case, digits and underscores")
    if name == PRODUCTION_NAME:
        raise ResetRefused(f"{name!r} is the production database; this command never drops or recreates it")
    return name


def create(name: str, url: URL | str | None = None) -> URL:
    """Make an empty database `name` on the server at `url`; its address."""
    base = as_async(url or database_url())
    asyncio.run(_autocommit(base.set(database="postgres"), f'CREATE DATABASE "{_checked(name)}"'))
    return base.set(database=name)


def drop(name: str, url: URL | str | None = None) -> None:
    """Remove database `name`, closing its connections first."""
    base = as_async(url or database_url())
    asyncio.run(_autocommit(base.set(database="postgres"), f'DROP DATABASE IF EXISTS "{_checked(name)}" WITH (FORCE)'))


def reset(name: str, url: URL | str | None = None) -> URL:
    """Drop `name`, make it again and migrate it; its address."""
    drop(name, url)
    target = create(name, url)
    upgrade(target)
    return target
