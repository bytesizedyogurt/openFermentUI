"""The one store (ADR-001; execution prompt §8.1): the engine and its loop,
the sessions, the advisory lock, the migrations and the database commands."""
from __future__ import annotations

import asyncio
import threading

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import insert, select, update

from openferment_core import db
from openferment_core.db import migrate
from openferment_core.db.engine import make_engine
from openferment_core.db import models as t
from openferment_core.db.__main__ import main as db_command


async def _project_ids() -> list[str]:
    async with db.session() as s:
        return list((await s.execute(select(t.projects.c.id))).scalars())


async def _add_project(pid: str) -> None:
    async with db.session() as s:
        await s.execute(insert(t.projects).values(id=pid, name=pid, created_by="test"))


def test_a_database_migrated_to_head_differs_from_the_table_models_in_nothing(test_database):
    engine = test_database.open()

    def compare(connection):
        context = MigrationContext.configure(
            connection,
            opts={
                "include_schemas": True,
                "version_table_schema": db.SCHEMA,
                "include_name": lambda name, type_, parent: type_ != "schema" or name == db.SCHEMA,
                "compare_type": True,
            },
        )
        return compare_metadata(context, t.metadata)

    async def diff():
        async with engine.connect() as c:
            return await c.run_sync(compare)

    assert db.run(diff()) == []


def test_the_session_database_is_at_the_newest_revision(test_database):
    test_database.open()
    assert migrate.head() == "0001"
    assert migrate.revision(test_database.url) == migrate.head()


def test_rollback_1_a_row_a_test_writes_is_there_for_the_rest_of_that_test():
    db.run(_add_project("written-in-test-one"))
    assert "written-in-test-one" in db.run(_project_ids())


def test_rollback_2_and_gone_when_the_next_test_starts():
    assert "written-in-test-one" not in db.run(_project_ids())


def test_a_session_opened_inside_another_joins_its_transaction():
    async def nested() -> bool:
        async with db.session() as outer, db.session() as inner:
            return outer is inner

    assert db.run(nested())


def test_a_block_that_raises_leaves_nothing_behind():
    async def refused() -> None:
        async with db.session() as s:
            await s.execute(insert(t.projects).values(id="never-kept", name="never kept", created_by="test"))
            raise ValueError("refused after the write")

    with pytest.raises(ValueError, match="refused after the write"):
        db.run(refused())
    assert "never-kept" not in db.run(_project_ids())


def test_run_refuses_on_the_database_thread_rather_than_wait_on_itself():
    async def inner() -> str:
        async def one() -> int:
            return 1

        with pytest.raises(RuntimeError, match="database thread"):
            db.run(one())
        return "refused"

    assert db.run(inner()) == "refused"


def test_arun_answers_an_async_caller():
    async def caller() -> list[str]:
        return await db.arun(_project_ids())

    assert isinstance(asyncio.run(caller()), list)


def test_the_advisory_lock_lets_one_writer_at_a_time_across_connections(test_database):
    """Eight writers read a counter, wait, and write it plus one, each on its
    own connection of a real (committed) database. Under the lock none of the
    eight increments is lost."""
    test_database.open()
    name = f"{test_database.name}_lock"
    url = migrate.create(name, test_database.server)
    engine = make_engine(url, pool_size=8, max_overflow=0)
    previous_engine = db.use_engine(engine)
    previous_binding = db.bind(None)
    try:
        migrate.upgrade(url)

        async def seed() -> None:
            async with db.session() as s:
                await s.execute(insert(t.projects).values(id="lock", name="lock", created_by="test", settings={"n": 0}))

        async def bump() -> None:
            async with db.session() as s:
                await db.lock(s, "test", "counter")
                held = (await s.execute(select(t.projects.c.settings).where(t.projects.c.id == "lock"))).scalar_one()
                await asyncio.sleep(0.02)
                await s.execute(update(t.projects).where(t.projects.c.id == "lock").values(settings={"n": held["n"] + 1}))

        async def count() -> int:
            async with db.session() as s:
                return (await s.execute(select(t.projects.c.settings).where(t.projects.c.id == "lock"))).scalar_one()["n"]

        db.run(seed())
        writers = [threading.Thread(target=lambda: db.run(bump())) for _ in range(8)]
        for w in writers:
            w.start()
        for w in writers:
            w.join()
        assert db.run(count()) == 8
    finally:
        db.bind(previous_binding)
        db.use_engine(previous_engine)
        db.run(engine.dispose())
        migrate.drop(name, test_database.server)


@pytest.mark.parametrize("name", ["openferment", "Openferment", "x; drop table", "", "has-dash"])
def test_reset_refuses_the_production_database_and_any_name_it_would_not_make(name):
    # Refused before any connection is tried: the address answers nothing.
    with pytest.raises(migrate.ResetRefused):
        migrate.reset(name, "postgresql://nobody:nothing@127.0.0.1:9/none")


def test_the_command_says_why_it_refuses(capsys, monkeypatch):
    monkeypatch.setenv(db.URL_SETTING, "postgresql://nobody:nothing@127.0.0.1:9/none")
    assert db_command(["reset", "openferment"]) == 2
    assert "production database" in capsys.readouterr().err


def test_the_command_names_the_setting_when_no_address_is_set(capsys, monkeypatch):
    monkeypatch.setattr("openferment_core.db.__main__.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv(db.URL_SETTING, raising=False)
    assert db_command(["migrate"]) == 2
    assert db.URL_SETTING in capsys.readouterr().err


def test_a_plain_postgresql_address_is_given_the_asyncpg_dialect():
    assert db.as_async("postgresql://a:b@127.0.0.1:5432/x").drivername == "postgresql+asyncpg"
    assert db.as_async("postgresql+psycopg://a:b@127.0.0.1/x").drivername == "postgresql+asyncpg"
    with pytest.raises(db.DatabaseUnavailable):
        db.as_async("sqlite:///x.db")
