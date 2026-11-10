"""spend.py's daily cap under OPENFERMENT_DAILY_BUDGET_USD=nan (and inf, and 25 for contrast): a reservation of
a million dollars is asked; the cap should refuse it (CapReached) or the setting should be refused as no number
of dollars (BudgetSettingInvalid). Run with OPENFERMENT_DATABASE_URL naming a migrated bh_h12_* database."""
import os

from openferment_core import projects, spend

for setting in ("25", "nan", "NaN", "inf"):
    os.environ[spend.DAILY_SETTING] = setting
    try:
        with projects.using(None):
            rid = spend.reserve("plan", 1e6)
        print(f"{setting!r}: budget read as {spend.daily_budget()!r}; a reservation of $1e6 was HELD ({rid}); "
              f"today's reserved total ${spend.state()['reservedUsd']:.0f}")
        spend.settle(rid, "plan", 0.0)
    except spend.CapReached as e:
        print(f"{setting!r}: refused by the cap: {e}")
    except spend.BudgetSettingInvalid as e:
        print(f"{setting!r}: the setting is refused: {e}")
