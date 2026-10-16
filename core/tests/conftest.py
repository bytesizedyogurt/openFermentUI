"""Shared test setup.

Every model call is charged to the day's spend (OF-BLD-014 §3.3). An offline
test's stand-in calls are charged to a file of its own, so no test ever moves
this machine's real total in core/data/spend.json, and no real total can make
an offline test refuse. A `live` test spends real money and is charged to the
real file.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _spend_kept_apart(request, monkeypatch, tmp_path):
    if request.node.get_closest_marker("live") is None:
        monkeypatch.setenv("OPENFERMENT_SPEND_FILE", str(tmp_path / "spend.json"))
        monkeypatch.delenv("OPENFERMENT_DAILY_BUDGET_USD", raising=False)
    yield
