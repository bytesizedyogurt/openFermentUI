"""Alembic's environment for Sci RAG Kit's schema, `sci_rag` (ADR-001, ADR-002).

The six migrations in versions/ are the kit's own, from its pinned commit and
under its licence (LICENSE-sci-rag-kit): its wheel leaves them out. This file
is openFerment's. It runs them with the kit's tables in their own schema and
the version table beside them, so the kit's history and ours
(db/alembic/) never meet. `openferment_core.migrations` runs it after ours,
with the address in `config.attributes["url"]`.

The vector extension is made in `public` first, where the search path finds
it for the kit's column type and index. Making an extension needs the rights
the database's owner or a superuser holds; a database made from a template
that already has it (the development and test databases) needs nothing.
"""
from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection

from openferment_core.db.engine import make_engine
from openferment_core.literature import kit

config = context.config


def _run(connection: Connection) -> None:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public"))
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{kit.SCHEMA}"'))
    context.configure(
        connection=connection,
        target_metadata=kit.kit_models.Base.metadata,
        version_table_schema=kit.SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    engine = make_engine(config.attributes["url"], search_path=kit.SEARCH_PATH, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run)
            await connection.commit()
    finally:
        await engine.dispose()


asyncio.run(_online())
