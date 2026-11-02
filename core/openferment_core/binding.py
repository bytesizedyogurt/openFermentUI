"""What Proforma and fermOS bind a value from records with (OF-BLD-020 §3.2).

Moved here from proforma.py, unchanged, so fermOS's simulation binds through
the same gate and the same statistic as Proforma's inputs do (D6). proforma.py
imports each under the name it had there, so its bindings, its runs' bases
and their artifact ids are what they were (test_fermos_bind holds them).

    exclusion(record)          the aggregate gate: why a record is kept out of
                               any aggregate (rejected, an industry estimate, a
                               computed value, an assumed one, a value the
                               paper cites from another), or None;
                               `aggregateExclusion` in Python
    statistic(values)          what a set of bound values gives: their median
                               with their range from three distinct values on,
                               a pair's middle with both ends, one value held
                               fixed, and the words that say so

Rule 1: no value here. A record's value is the paper's; these functions
choose which records count and summarise them, and say how.
"""
from __future__ import annotations

import statistics as _statistics
from typing import NamedTuple

# What the statistic says when it holds a value fixed (§8.3 of OF-BLD-014).
SINGLE = "single source: held fixed in sampling"
SAME = "every bound record gives the same value: held fixed in sampling"


def exclusion(r: dict) -> str | None:
    """`aggregateExclusion` in Python, over a pool record."""
    if r.get("status") == "rejected":
        return "rejected"
    if r.get("provenance") == "industry-estimate":
        return "industry-estimate"
    if r.get("provenance") == "computed":
        return "computed"
    # A model's estimate or a person's assumption is never evidence (ADR-006).
    if r.get("provenance") == "assumed":
        return "assumed"
    if r.get("primary") is False:
        return "not-primary"
    return None


class Statistic(NamedTuple):
    """A bound value, its range, how a run samples it, and the flag it
    carries (None when it carries none)."""

    value: float
    low: float
    high: float
    sampling: str
    flag: str | None


def statistic(values: list[float]) -> Statistic:
    """The median of the values with their range and a triangular draw from
    three distinct values on; a distinct pair's middle with both ends, drawn
    uniform; one value, or values all alike, held fixed and flagged
    (OF-BLD-014 §8.3). Refused for no values."""
    vals = sorted(values)
    if not vals:
        raise ValueError("no value to summarise")
    if len(vals) >= 3 and vals[0] != vals[-1]:
        return Statistic(_statistics.median(vals), vals[0], vals[-1], "triangular", None)
    if len(vals) == 2 and vals[0] != vals[1]:
        return Statistic((vals[0] + vals[1]) / 2, vals[0], vals[1], "uniform", None)
    return Statistic(vals[0], vals[0], vals[0], "fixed", SINGLE if len(vals) == 1 else SAME)
