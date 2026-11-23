"""H9-09: a call held at 23:59:30 UTC settles at 00:00:40 into the next day, which never counted its hold.

    OPENFERMENT_DATABASE_URL=<bh_r_h9_09_...> bh_py ../bughunt/repro/H9-09/across_midnight.py

The spend module's own clock (`spend.datetime`) is set to the instant each step happens at; the
reservations and settlements are the very calls llm.py makes (`spend.reserve`, then `spend.settle`
with the reservation's id), on a fresh test database. No model is called.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import select

from openferment_core import db, spend
from openferment_core.db import models as t

os.environ[spend.DAILY_SETTING] = "1.00"
REAL_DATETIME = spend.datetime
NOW = [REAL_DATETIME(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)]


class Clock(REAL_DATETIME):
    @classmethod
    def now(cls, tz=None):  # the instant the step happens at, UTC
        return NOW[0] if tz is None else NOW[0].astimezone(tz)


spend.datetime = Clock  # type: ignore[misc]


def at(iso: str) -> None:
    NOW[0] = REAL_DATETIME.fromisoformat(iso)


def attempt(usd: float) -> str:
    try:
        return spend.reserve("answer", usd)
    except spend.CapReached as e:
        return f"refused ({e})"


def day_spent(day: str) -> float:
    async def go():
        async with db.session() as s:
            rows = (await s.execute(select(t.spend).where(t.spend.c.day == date.fromisoformat(day)))).all()
        return round(sum(float(r.usd) for r in rows if r.state in spend.SPENT), 6)
    return db.run(go())


def say(**kw) -> None:
    print(json.dumps(kw), flush=True)


cap = spend.daily_budget()

# Control: the same two calls within one UTC day. The second is refused while the first is in flight.
at("2026-11-08T12:00:00+00:00")
first = attempt(0.90)
second = attempt(0.90)
spend.settle(first, "answer", 0.90)
say(step="control, one day (2026-11-08)", first=first, second=second, daySpentUsd=day_spent("2026-11-08"), cap=cap)

# Across midnight: call A is held at 23:59:30 on 2026-11-10, B is asked at 00:00:10 on 2026-11-11 while
# A is still in flight, A answers at 00:00:40, B at 00:01:10. Each call's worst case is 0.90.
at("2026-11-10T23:59:30+00:00")
a = attempt(0.90)
say(step="23:59:30 A reserves 0.90", a=a, state=spend.state())
at("2026-11-11T00:00:10+00:00")
seen = spend.state()
say(step="00:00:10 the new day's state as B's check reads it", reservedUsd=seen["reservedUsd"], totalUsd=seen["totalUsd"])
b = attempt(0.90)
say(step="00:00:10 B reserves 0.90 while A is in flight", b=b)
at("2026-11-11T00:00:40+00:00")
after_a = spend.settle(a, "answer", 0.90)
say(step="00:00:40 A settles 0.90", newDayTotalUsd=after_a)
at("2026-11-11T00:01:10+00:00")
if not b.startswith("refused"):
    spend.settle(b, "answer", 0.90)
end = spend.state()
d0, d1 = day_spent("2026-11-10"), day_spent("2026-11-11")
say(step="00:01:10 B settles 0.90", day0SpentUsd=d0, day1SpentUsd=d1, day1Calls=end["calls"], cap=cap)

print(f"OBSERVED: control: within one day the second 0.90 reservation was {'refused' if second.startswith('refused') else 'held'}")
print(f"OBSERVED: at 00:00:10 the new day's check read reservedUsd={seen['reservedUsd']} while A's 0.90 was in flight")
print(f"OBSERVED: B's 0.90 reservation on 2026-11-11 was {'refused' if b.startswith('refused') else 'held'}")
print(f"OBSERVED: 2026-11-10 spent {d0:.2f} USD; 2026-11-11 spent {d1:.2f} USD in {end['calls']} calls against the {cap:.2f} USD cap")
print(f"VERDICT: {'DEFECT' if d1 > cap or d0 > cap else 'NO-DEFECT'}")
