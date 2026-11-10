"""H9: the daily cap at its boundary (spend.py), on a test database of its own.

    OPENFERMENT_DATABASE_URL=<bh_h9_spend> bh_py ../bughunt/notes/H9/scripts/spend_boundaries.py

Each case starts from an empty spend table. Prints one JSON line a case.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import date, timedelta

from sqlalchemy import delete

from openferment_core import db, spend
from openferment_core.db import models as t


def clear() -> None:
    async def go():
        async with db.session() as s:
            await s.execute(delete(t.spend))
    db.run(go())


def case(name: str, **said) -> None:
    print(json.dumps({"case": name, **said}), flush=True)


def attempt(usd: float) -> str:
    try:
        return spend.reserve("answer", usd)
    except spend.CapReached as e:
        return f"refused: {e}"


os.environ[spend.DAILY_SETTING] = "1.00"

clear()
case("exactly at the cap, nothing spent", reserve_1_00=attempt(1.00)[:9])
clear()
case("a cent under", reserve_0_99=attempt(0.99)[:9])
clear()
case("a cent over", reserve_1_01=attempt(1.01))
clear()
rid = attempt(0.60)
spend.settle(rid, "answer", 0.60)
case("spent 0.60, then 0.40 (to the cap) and 0.41 (a cent past)", at_cap=attempt(0.40)[:9], past=attempt(0.01))

# concurrent: twenty reservations of 0.10 against a cap of 1.00 at once.
clear()
results: list[str] = []
lock = threading.Lock()


def one() -> None:
    r = attempt(0.10)
    with lock:
        results.append(r)


threads = [threading.Thread(target=one) for _ in range(20)]
[th.start() for th in threads]
[th.join() for th in threads]
held = sum(1 for r in results if not r.startswith("refused"))
case("twenty concurrent reservations of 0.10, cap 1.00", held=held, refused=20 - held,
     reservedUsd=spend.state()["reservedUsd"])

# the UTC day boundary: a reservation held on day D settles after midnight.
clear()
real_today = spend.today
d0 = date.fromisoformat(real_today())
spend.today = lambda: d0.isoformat()  # type: ignore[assignment]
late = attempt(0.90)  # 23:59 on D: the call's worst case held against D
spend.today = lambda: (d0 + timedelta(days=1)).isoformat()  # type: ignore[assignment]
early = attempt(0.90)  # 00:00 on D+1: D's hold is not counted against D+1
spend.settle(late, "answer", 0.90)  # the late call ends after midnight and is charged to D+1
spend.settle(early, "answer", 0.90)
after = spend.state()
case("a call reserved before midnight and settled after it", second_reservation=early[:9],
     dayAfterSpentUsd=after["totalUsd"], cap=spend.daily_budget(), pastTheCap=after["totalUsd"] > spend.daily_budget())
spend.today = real_today  # type: ignore[assignment]

# a cap that is no number of dollars
for raw in ("nan", "NaN", "inf", "1e999", "-0"):
    clear()
    os.environ[spend.DAILY_SETTING] = raw
    try:
        cap = spend.daily_budget()
        got = attempt(1000.0)
        case(f"{spend.DAILY_SETTING}={raw}", cap=str(cap), reserve_1000=got[:40])
    except spend.BudgetSettingInvalid as e:
        case(f"{spend.DAILY_SETTING}={raw}", refused=str(e))
clear()
