"""The day's spend on models, by role, and the daily cap (OF-BLD-014 §3.3, E.7).

`llm.py` charges every response here, and asks before every call whether the
call could pass `OPENFERMENT_DAILY_BUDGET_USD`. The day is the UTC day; a new
day starts from zero. The file is `core/data/spend.json`, gitignored and
never pushed (E.10), written through `atomic.write_text` under a lock held
across processes, because the nightly job is a second one.

The cap is a setting in `core/.env` (D8). Its default is the figure D8
accepted; it is a software budget, a convention in E.1's sense, and no
result depends on it.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import atomic, intake

DAILY_SETTING = "OPENFERMENT_DAILY_BUDGET_USD"
ASK_SETTING = "OPENFERMENT_ASK_BUDGET_USD"
# D8's figures, accepted by Sean (OF-BLD-014 Part D).
DEFAULT_DAILY_USD = 25.0
DEFAULT_ASK_USD = 0.75
ROLES = ("answer", "index")

_LOCK = threading.Lock()


class BudgetSettingInvalid(ValueError):
    pass


def path() -> Path:
    """Read at call time. `OPENFERMENT_SPEND_FILE` moves it (the offline tests
    do, so they never touch this machine's real total)."""
    raw = os.environ.get("OPENFERMENT_SPEND_FILE", "").strip()
    return Path(raw) if raw else intake.DATA_DIR / "spend.json"


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


class SpendFileDamaged(RuntimeError):
    """The day's spend cannot be read. The gate closes rather than starting
    the day from zero, and the file is left for a person to look at (§3.R)."""


class CapReached(RuntimeError):
    def __init__(self, spent: float, reserved: float, cap: float):
        super().__init__(f"today ${spent:.2f} spent and ${reserved:.2f} reserved of the ${cap:.2f} cap")
        self.spent, self.reserved, self.cap = spent, reserved, cap


def _empty(day: str) -> dict[str, Any]:
    return {"day": day, "byRole": {r: 0.0 for r in ROLES}, "calls": 0, "reservations": {}}


def _read(day: str) -> dict[str, Any]:
    p = path()
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _empty(day)
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get("byRole", {}), dict):
            raise ValueError("not a spend record")
    except ValueError as e:
        raise SpendFileDamaged(
            f"{p} cannot be read ({e}), so today's spend is unknown and no model call is made. "
            "Look at it, then delete it to start the day from zero."
        ) from None
    if data.get("day") != day:
        return _empty(day)
    out = _empty(day)
    for role, usd in data.get("byRole", {}).items():
        if isinstance(usd, (int, float)):
            out["byRole"][str(role)] = float(usd)
    out["calls"] = int(data.get("calls") or 0)
    now = datetime.now(timezone.utc).timestamp()
    for rid, r in (data.get("reservations") or {}).items():
        if isinstance(r, dict) and isinstance(r.get("usd"), (int, float)) and now - float(r.get("t", 0)) < RESERVATION_TTL_S:
            out["reservations"][str(rid)] = {"usd": float(r["usd"]), "t": float(r["t"])}
    return out


def _write(data: dict[str, Any]) -> None:
    atomic.write_text(path(), json.dumps(data, indent=2, sort_keys=True) + "\n")


def _totals(data: dict[str, Any]) -> tuple[float, float]:
    return (
        round(sum(data["byRole"].values()), 6),
        round(sum(r["usd"] for r in data["reservations"].values()), 6),
    )


def state() -> dict[str, Any]:
    """Today's spend: `{"day", "byRole", "calls", "reservations",
    "totalUsd", "reservedUsd"}`. Raises SpendFileDamaged."""
    data = _read(today())
    data["totalUsd"], data["reservedUsd"] = _totals(data)
    return data


def total_today() -> float:
    return state()["totalUsd"]


def reserve(role: str, projected_usd: float) -> str:
    """Hold `projected_usd` against today's cap, or raise CapReached. Check
    and hold are one step under the lock, so two calls at once cannot each
    see room that only one of them has (§3.R)."""
    p = path()
    with _LOCK, atomic.held(p):
        data = _read(today())
        spent, reserved = _totals(data)
        cap = daily_budget()
        if spent + reserved + projected_usd > cap:
            raise CapReached(spent, reserved, cap)
        rid = uuid.uuid4().hex[:12]
        data["reservations"][rid] = {"usd": round(projected_usd, 6), "t": datetime.now(timezone.utc).timestamp(), "role": role}
        _write(data)
        return rid


def settle(rid: str | None, role: str, usd: float) -> float:
    """Release a reservation and charge what the call cost; today's total."""
    if usd < 0:
        raise ValueError("a charge cannot be negative")
    p = path()
    with _LOCK, atomic.held(p):
        data = _read(today())
        if rid is not None:
            data["reservations"].pop(rid, None)
        if usd > 0 or rid is None:
            data["byRole"][role] = round(data["byRole"].get(role, 0.0) + usd, 6)
            data["calls"] += 1
        _write(data)
        return _totals(data)[0]


def charge(role: str, usd: float) -> float:
    """Add `usd` to today's spend under `role`; return today's total."""
    return settle(None, role, usd)


def would_pass(projected_usd: float) -> tuple[bool, float, float]:
    """Whether a call that may cost `projected_usd` could take today past the
    cap, counting what is reserved. A damaged file always would."""
    cap = daily_budget()
    try:
        s = state()
    except SpendFileDamaged:
        return True, 0.0, cap
    return s["totalUsd"] + s["reservedUsd"] + projected_usd > cap, s["totalUsd"], cap
