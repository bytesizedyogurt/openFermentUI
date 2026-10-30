"""Shared test setup.

Every model call is charged to the day's spend (OF-BLD-014 §3.3). An offline
test's stand-in calls are charged to a file of its own, so no test ever moves
this machine's real total in core/data/spend.json, and no real total can make
an offline test refuse. A `live` test spends real money and is charged to the
real file.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _spend_kept_apart(request, monkeypatch, tmp_path):
    if request.node.get_closest_marker("live") is None:
        monkeypatch.setenv("OPENFERMENT_SPEND_FILE", str(tmp_path / "spend.json"))
        monkeypatch.delenv("OPENFERMENT_DAILY_BUDGET_USD", raising=False)
    yield


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
