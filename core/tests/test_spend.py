"""The day's spend, by role, and its settings (OF-BLD-014 §3.3, E.7)."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from openferment_core import db, projects, spend
from openferment_core.db import models as t
from openferment_core.db.engine import make_engine


def test_charges_add_up_by_role():
    spend.charge("answer", 0.25)
    spend.charge("index", 0.01)
    total = spend.charge("answer", 0.5)
    s = spend.state()
    assert s["byRole"] == {"answer": 0.75, "index": 0.01}
    assert total == s["totalUsd"] == 0.76 and s["calls"] == 3


def test_a_new_utc_day_starts_from_zero(monkeypatch):
    monkeypatch.setattr(spend, "today", lambda: "2026-10-14")
    spend.charge("answer", 3.0)
    monkeypatch.setattr(spend, "today", lambda: "2026-10-15")
    assert spend.total_today() == 0.0
    spend.charge("answer", 1.0)
    assert spend.state()["day"] == "2026-10-15" and spend.total_today() == 1.0


def test_the_cap_is_the_machines_across_every_project():
    spend.charge("answer", 0.3)
    with projects.using("another-project"):
        spend.charge("answer", 0.2)
        assert spend.total_today() == 0.5
    assert spend.total_today() == 0.5


def test_a_database_that_does_not_answer_closes_the_gate():
    # §3.R: reading unknown spend as "nothing spent" would reset the cap.
    down = make_engine("postgresql://nobody:nothing@127.0.0.1:9/none")
    previous_binding, previous_engine = db.bind(None), db.use_engine(down)
    try:
        with pytest.raises(spend.SpendUnknown, match="no model call is made"):
            spend.total_today()
        assert spend.would_pass(0.01)[0] is True
        with pytest.raises(spend.SpendUnknown):
            spend.reserve("answer", 0.01)
    finally:
        db.use_engine(previous_engine)
        db.bind(previous_binding)
        db.run(down.dispose())
    spend.charge("answer", 0.2)
    assert spend.total_today() == 0.2


def test_a_reservation_holds_against_the_cap_until_it_settles(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "1")
    held = spend.reserve("answer", 0.8)
    with pytest.raises(spend.CapReached):
        spend.reserve("answer", 0.3)
    assert spend.state()["reservedUsd"] == 0.8
    assert spend.settle(held, "answer", 0.25) == 0.25
    assert spend.state()["reservedUsd"] == 0.0
    spend.reserve("answer", 0.7)


def test_an_abandoned_reservation_holds_nothing(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "1")
    spend.reserve("answer", 0.9)

    async def expire() -> None:
        async with db.session() as s:
            await s.execute(update(t.spend).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))

    db.run(expire())
    assert spend.state()["reservedUsd"] == 0.0
    spend.reserve("answer", 0.9)


def test_a_reservation_settled_at_nothing_counts_no_call():
    held = spend.reserve("answer", 0.5)
    spend.settle(held, "answer", 0.0)
    assert spend.state()["calls"] == 0 and spend.total_today() == 0.0


def test_concurrent_charges_lose_nothing():
    threads = [threading.Thread(target=spend.charge, args=("answer", 0.01)) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert spend.total_today() == 0.2 and spend.state()["calls"] == 20


def test_the_budgets_default_to_d8_and_read_the_settings(monkeypatch):
    assert (spend.daily_budget(), spend.ask_budget()) == (25.0, 0.75)
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "5")
    monkeypatch.setenv("OPENFERMENT_ASK_BUDGET_USD", "0.2")
    assert (spend.daily_budget(), spend.ask_budget()) == (5.0, 0.2)


@pytest.mark.parametrize("raw", ["five", "-1"])
def test_a_budget_that_is_not_a_number_of_dollars_is_refused(monkeypatch, raw):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", raw)
    with pytest.raises(spend.BudgetSettingInvalid) as e:
        spend.daily_budget()
    assert "OPENFERMENT_DAILY_BUDGET_USD" in str(e.value)


def test_would_pass_compares_the_projection_with_what_is_left(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "1")
    spend.charge("answer", 0.9)
    assert spend.would_pass(0.1) == (False, 0.9, 1.0)
    assert spend.would_pass(0.11)[0] is True


def test_a_negative_charge_is_refused():
    with pytest.raises(ValueError):
        spend.charge("answer", -0.01)
