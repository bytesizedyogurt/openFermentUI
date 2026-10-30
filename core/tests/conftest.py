"""Shared test setup.

Every model call is charged to the day's spend (OF-BLD-014 §3.3). An offline
test's stand-in calls are charged inside the test's own rolled-back database
transaction, so no test ever moves this machine's real total, and no real
total can make an offline test refuse. A `live` test spends real money and is
charged to the machine's real database, the one core/.env names.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import threading
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _spend_kept_apart(request, monkeypatch):
    if request.node.get_closest_marker("live") is None:
        monkeypatch.delenv("OPENFERMENT_DAILY_BUDGET_USD", raising=False)
        yield
        return
    from dotenv import dotenv_values

    from openferment_core import db, spend

    address = os.environ.get(db.URL_SETTING) or dotenv_values(Path(__file__).parent.parent / ".env").get(db.URL_SETTING)
    if not address:
        yield
        return
    real = db.make_engine(address)
    monkeypatch.setattr(spend, "_ENGINE", real)
    yield
    db.run(real.dispose())


# Guild's skills, protocol step tags and lessons: the service ships with none
# (alpha 2.0 deleted the seed, ADR-010), so the tests read the frozen fixture
# alpha 1.0's export wrote. A test of the empty default sets PROJECTION back.
GUILD_PROJECTION = Path(__file__).parent / "fixtures" / "guild-projection.json"


@pytest.fixture(autouse=True)
def _guild_projection(monkeypatch):
    from openferment_core import guild

    monkeypatch.setattr(guild, "PROJECTION", GUILD_PROJECTION)
    guild._projection.cache_clear()
    yield
    guild._projection.cache_clear()


# The corpus the service ships is empty (alpha 2.0 deleted the seed, ADR-010).
# A test of a rule that acts on papers and records asks for this fixture and
# reads fixtures/test-corpus.json, a fictional corpus of placeholder papers.
TEST_CORPUS = Path(__file__).parent / "fixtures" / "test-corpus.json"


@pytest.fixture
def test_corpus(monkeypatch):
    from openferment_core import corpus

    monkeypatch.setattr(corpus, "DATA", TEST_CORPUS)
    corpus.load_corpus.cache_clear()
    yield corpus.load_corpus()
    corpus.load_corpus.cache_clear()


# ── PostgreSQL (alpha 2.0, ADR-001; execution prompt §8.1) ─────────────────
#
# One disposable database per test session, made on the server that
# OPENFERMENT_TEST_DATABASE_URL names (its database part is the prefix of the
# name made), migrated to head, and dropped when the session ends. Each test
# runs inside one transaction on one connection, rolled back when the test
# ends, so no test sees another's rows. Nothing connects until a test first
# touches the database: a test of a pure function needs no server.
TEST_DATABASE_SETTING = "OPENFERMENT_TEST_DATABASE_URL"
DEFAULT_TEST_DATABASE = "postgresql://openferment:openferment@127.0.0.1:5432/openferment_test"


class TestDatabase:
    """The session's database, made the first time a test needs it."""

    __test__ = False

    def __init__(self) -> None:
        from openferment_core.db import as_async

        self.server = as_async(os.environ.get(TEST_DATABASE_SETTING, "").strip() or DEFAULT_TEST_DATABASE)
        self.name = f"{self.server.database or 'openferment_test'}_{os.getpid()}_{secrets.token_hex(3)}"
        self.url = None
        self.engine = None
        self._lock = threading.Lock()

    def open(self):
        """Make, migrate and connect the database once; its engine."""
        from openferment_core.db import migrate
        from openferment_core.db.engine import make_engine

        with self._lock:
            if self.engine is None:
                try:
                    url = migrate.create(self.name, self.server)
                except Exception as e:
                    raise RuntimeError(
                        f"PostgreSQL did not answer at {self.server.render_as_string(hide_password=True)} "
                        f"({e.__class__.__name__}: {e}). Start it with `pnpm db:up`, or set {TEST_DATABASE_SETTING}."
                    ) from e
                self.url = url
                migrate.upgrade(url)
                self.engine = make_engine(url, pool_size=2, max_overflow=2)
            return self.engine

    async def engine_now(self):
        """`open`, from the database loop: the work runs on a thread of its
        own, because alembic runs its own event loop."""
        return await asyncio.to_thread(self.open)

    def close(self) -> None:
        from openferment_core import db
        from openferment_core.db import migrate

        if self.engine is not None:
            db.run(self.engine.dispose())
            migrate.drop(self.name, self.server)


@pytest.fixture(scope="session")
def test_database():
    held = TestDatabase()
    yield held
    held.close()


# Every test acts in one project, as every request names one (ADR-005): the
# test's own thread through `projects.using`, a thread it starts through
# OPENFERMENT_PROJECT, and every TestClient it makes through the header, the
# way the browser sends it. The project's row is written in the test's
# transaction when the database is first touched.
TEST_PROJECT = "test-project"


async def _test_project_row(connection) -> None:
    from sqlalchemy import insert

    from openferment_core.db import models as t

    await connection.execute(insert(t.projects).values(id=TEST_PROJECT, name="Test project", created_by="test"))


@pytest.fixture(autouse=True)
def _database(test_database, monkeypatch):
    """Every session of this test: a savepoint on one rolled-back transaction,
    in the test project."""
    from fastapi.testclient import TestClient

    from openferment_core import db, projects

    made = TestClient.__init__

    def naming_the_project(self, *args, headers=None, **kwargs):
        made(self, *args, headers={projects.HEADER: TEST_PROJECT, **(headers or {})}, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", naming_the_project)
    # A thread a test starts begins outside the test's context, like a
    # command's, and finds the project where a command does.
    monkeypatch.setenv(projects.ENV, TEST_PROJECT)
    binding = db.Binding(test_database.engine_now, prepare=_test_project_row)
    previous = db.bind(binding)
    with projects.using(TEST_PROJECT):
        yield binding
    db.bind(previous)
    if binding.connection is not None:
        db.run(binding.close())
