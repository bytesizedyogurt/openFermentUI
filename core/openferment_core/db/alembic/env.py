"""Alembic's environment for the `openferment` schema (ADR-001).

Run through `python -m openferment_core.db migrate` (`pnpm db:migrate`), which
hands over the address in `config.attributes["url"]`. The version table lives
in the schema it versions, so Sci RAG Kit's history in `sci_rag` and ours
never meet, and autogenerate compares our schema alone.
"""
from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection

from openferment_core.db.engine import SCHEMA, make_engine
from openferment_core.db.models import metadata

config = context.config


def _configure(**kw) -> None:
    context.configure(
        target_metadata=metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=lambda name, type_, parent: type_ != "schema" or name == SCHEMA,
        compare_type=True,
        **kw,
    )


def _run(connection: Connection) -> None:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    engine = make_engine(config.attributes["url"], poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run)
            await connection.commit()
    finally:
        await engine.dispose()


if context.is_offline_mode():
    _configure(url=str(config.attributes["url"]), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_online())
