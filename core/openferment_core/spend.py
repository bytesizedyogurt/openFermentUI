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


def _empty(day: str) -> dict[str, Any]:
    return {"day": day, "byRole": {r: 0.0 for r in ROLES}, "calls": 0}


def _read(day: str) -> dict[str, Any]:
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return _empty(day)
    if not isinstance(data, dict) or data.get("day") != day:
        return _empty(day)
    by_role = data.get("byRole") if isinstance(data.get("byRole"), dict) else {}
    out = _empty(day)
    for role, usd in by_role.items():
        if isinstance(usd, (int, float)):
            out["byRole"][str(role)] = float(usd)
    out["calls"] = int(data.get("calls") or 0)
    return out


def state() -> dict[str, Any]:
    """Today's spend: `{"day", "byRole", "calls", "totalUsd"}`."""
    data = _read(today())
    data["totalUsd"] = round(sum(data["byRole"].values()), 6)
    return data


def total_today() -> float:
    return state()["totalUsd"]


def charge(role: str, usd: float) -> float:
    """Add `usd` to today's spend under `role`; return today's total."""
    if usd < 0:
        raise ValueError("a charge cannot be negative")
    p = path()
    with _LOCK, atomic.held(p):
        data = _read(today())
        data["byRole"][role] = round(data["byRole"].get(role, 0.0) + usd, 6)
        data["calls"] += 1
        atomic.write_text(p, json.dumps(data, indent=2, sort_keys=True) + "\n")
        return round(sum(data["byRole"].values()), 6)


def would_pass(projected_usd: float) -> tuple[bool, float, float]:
    """Whether a call that may cost `projected_usd` could take today past the
    cap. Returns (refuse, today's total, the cap)."""
    cap = daily_budget()
    spent = total_today()
    return spent + projected_usd > cap, spent, cap
