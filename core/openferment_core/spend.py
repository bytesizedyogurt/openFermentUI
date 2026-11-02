"""The day's spend on models, by role, and the daily cap (OF-BLD-014 §3.3, E.7).

`llm.py` charges every response here, and asks before every call whether the
call could pass `OPENFERMENT_DAILY_BUDGET_USD`. The day is the UTC day; a new
day starts from zero. The day's spend is rows of the `spend` table (ADR-001):
a reservation is a row until its call settles, and what a call cost is a row
that stays. The cap is the machine's, across every project and process (the
nightly job is a second process), so the check and the hold run under one
advisory lock on the day.

The cap is a setting in `core/.env` (D8). Its default is the figure D8
accepted; it is a software budget, a convention in E.1's sense, and no
result depends on it.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from . import db, projects
from .db import models as t

DAILY_SETTING = "OPENFERMENT_DAILY_BUDGET_USD"
ASK_SETTING = "OPENFERMENT_ASK_BUDGET_USD"
# D8's figures, accepted by Sean (OF-BLD-014 Part D).
DEFAULT_DAILY_USD = 25.0
DEFAULT_ASK_USD = 0.75
ROLES = ("answer", "index")
# What a call cost; a reservation becomes `settled`, a charge with no
# reservation is `charged`.
SPENT = ("settled", "charged")

# Where the spend is kept when it is not the session under way: a live test
# charges the machine's real total here (core/tests/conftest.py), while every
# other test's spend is rolled back with the test.
_ENGINE: AsyncEngine | None = None


class BudgetSettingInvalid(ValueError):
    pass


def _setting(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise BudgetSettingInvalid(f"{name} in core/.env is {raw!r}, which is not a number of dollars") from None
    if value < 0:
        raise BudgetSettingInvalid(f"{name} in core/.env is {raw}, and a budget cannot be negative")
    return value


def daily_budget() -> float:
    return _setting(DAILY_SETTING, DEFAULT_DAILY_USD)


def ask_budget() -> float:
    """The cap on one question (D8). Postdoc's loop reads it from §5.2 on."""
    return _setting(ASK_SETTING, DEFAULT_ASK_USD)


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# How long a reservation holds before it is treated as abandoned (a process
# that died between reserving and settling). Longer than any call this
# service makes; a convention in E.1's sense.
RESERVATION_TTL_S = 1800


class SpendUnknown(RuntimeError):
    """The day's spend cannot be read: the database did not answer. The gate
    closes rather than starting the day from zero (§3.R)."""


class CapReached(RuntimeError):
    def __init__(self, spent: float, reserved: float, cap: float):
        super().__init__(f"today ${spent:.2f} spent and ${reserved:.2f} reserved of the ${cap:.2f} cap")
        self.spent, self.reserved, self.cap = spent, reserved, cap


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    if _ENGINE is None:
        async with db.session() as s:
            yield s
        return
    async with AsyncSession(_ENGINE, expire_on_commit=False) as s, s.begin():
        yield s


def _run(coro: Any) -> Any:
    """`db.run`, with a database that does not answer said as SpendUnknown."""
    try:
        return db.run(coro)
    except (CapReached, ValueError):
        raise
    except Exception as e:  # the database is down, unset or refusing: the gate closes
        raise SpendUnknown(
            f"today's spend cannot be read ({type(e).__name__}: {e}), so no model call is made. "
            f"Start PostgreSQL or check {db.URL_SETTING} in core/.env."
        ) from e


async def _day_state(s: AsyncSession, day: date) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    rows = (await s.execute(select(t.spend).where(t.spend.c.day == day).order_by(t.spend.c.seq))).all()
    out: dict[str, Any] = {"day": day.isoformat(), "byRole": {r: 0.0 for r in ROLES}, "calls": 0, "reservations": {}}
    for r in rows:
        if r.state in SPENT:
            out["byRole"][r.role] = round(out["byRole"].get(r.role, 0.0) + float(r.usd), 6)
            out["calls"] += 1
        elif r.state == "reserved" and r.expires_at is not None and r.expires_at > now:
            out["reservations"][r.reservation] = {"usd": float(r.usd), "t": r.created_at.timestamp()}
    return out


def _totals(data: dict[str, Any]) -> tuple[float, float]:
    return (
        round(sum(data["byRole"].values()), 6),
        round(sum(r["usd"] for r in data["reservations"].values()), 6),
    )


async def _state() -> dict[str, Any]:
    async with _session() as s:
        return await _day_state(s, date.fromisoformat(today()))


def state() -> dict[str, Any]:
    """Today's spend: `{"day", "byRole", "calls", "reservations",
    "totalUsd", "reservedUsd"}`. Raises SpendUnknown."""
    data = _run(_state())
    data["totalUsd"], data["reservedUsd"] = _totals(data)
    return data


def total_today() -> float:
    return state()["totalUsd"]


async def _reserve(role: str, projected_usd: float, project_id: str | None) -> str:
    day = date.fromisoformat(today())
    async with _session() as s:
        await db.lock(s, "spend", day.isoformat())
        now = datetime.now(timezone.utc)
        # An abandoned reservation holds nothing; its row goes.
        await s.execute(delete(t.spend).where(t.spend.c.state == "reserved", t.spend.c.expires_at <= now))
        spent, reserved = _totals(await _day_state(s, day))
        cap = daily_budget()
        if spent + reserved + projected_usd > cap:
            raise CapReached(spent, reserved, cap)
        rid = uuid.uuid4().hex[:12]
        await s.execute(
            insert(t.spend).values(
                day=day, role=role, usd=round(projected_usd, 6), state="reserved", reservation=rid,
                project_id=project_id, expires_at=now + timedelta(seconds=RESERVATION_TTL_S),
            )
        )
        return rid


def reserve(role: str, projected_usd: float) -> str:
    """Hold `projected_usd` against today's cap, or raise CapReached. Check
    and hold are one step under the day's lock, so two calls at once cannot
    each see room that only one of them has (§3.R)."""
    return _run(_reserve(role, projected_usd, projects.current_or_none()))


async def _settle(rid: str | None, role: str, usd: float, project_id: str | None) -> float:
    day = date.fromisoformat(today())
    async with _session() as s:
        await db.lock(s, "spend", day.isoformat())
        if rid is not None:
            await s.execute(delete(t.spend).where(t.spend.c.reservation == rid, t.spend.c.state == "reserved"))
        if usd > 0 or rid is None:
            await s.execute(
                insert(t.spend).values(day=day, role=role, usd=round(usd, 6), state="settled" if rid else "charged",
                                       project_id=project_id)
            )
        return _totals(await _day_state(s, day))[0]


def settle(rid: str | None, role: str, usd: float) -> float:
    """Release a reservation and charge what the call cost; today's total."""
    if usd < 0:
        raise ValueError("a charge cannot be negative")
    return _run(_settle(rid, role, usd, projects.current_or_none()))


def charge(role: str, usd: float) -> float:
    """Add `usd` to today's spend under `role`; return today's total."""
    return settle(None, role, usd)


def would_pass(projected_usd: float) -> tuple[bool, float, float]:
    """Whether a call that may cost `projected_usd` could take today past the
    cap, counting what is reserved. Unknown spend always would."""
    cap = daily_budget()
    try:
        s = state()
    except SpendUnknown:
        return True, 0.0, cap
    return s["totalUsd"] + s["reservedUsd"] + projected_usd > cap, s["totalUsd"], cap
