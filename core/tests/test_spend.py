"""The day's spend, by role, and its settings (OF-BLD-014 §3.3, E.7)."""
from __future__ import annotations

import json
import threading

import pytest

from openferment_core import spend


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
    assert json.loads(spend.path().read_text())["day"] == "2026-10-15"


def test_the_file_is_the_one_the_setting_names(tmp_path, monkeypatch):
    target = tmp_path / "elsewhere" / "spend.json"
    monkeypatch.setenv("OPENFERMENT_SPEND_FILE", str(target))
    spend.charge("answer", 0.1)
    assert target.is_file()


def test_a_damaged_file_closes_the_gate_and_is_left_for_a_person():
    # §3.R: reading a damaged file as "nothing spent" reset the cap.
    spend.path().write_text("{not json", encoding="utf-8")
    with pytest.raises(spend.SpendFileDamaged, match="delete it"):
        spend.total_today()
    assert spend.would_pass(0.01)[0] is True
    spend.path().unlink()
    spend.charge("answer", 0.2)
    assert spend.total_today() == 0.2


def test_concurrent_charges_lose_nothing():
    threads = [threading.Thread(target=spend.charge, args=("answer", 0.01)) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
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
