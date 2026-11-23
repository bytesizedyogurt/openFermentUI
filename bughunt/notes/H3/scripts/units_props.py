"""H3: property tests over units.py and schema/units.json.

Run from a worktree with hypothesis installed:
  cd <wt>/core && .venv/bin/python -m pytest <this file> -q -p no:randomly -p no:cacheprovider
It imports openferment_core from the interpreter's path (the worktree's own copy of 2047f5a).
"""
from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from openferment_core import units

T = units.tables()
TABLE = T["table"]
FAMILIES: dict[str, list[str]] = {}
for key, row in TABLE.items():
    FAMILIES.setdefault(row["family"], []).append(key)
PAIRS = [(f, a, b) for f, keys in FAMILIES.items() for a in keys for b in keys]
TRIPLES = [(f, a, b, c) for f, keys in FAMILIES.items() for a in keys for b in keys for c in keys]
CROSS = [(a, b) for a in TABLE for b in TABLE if TABLE[a]["family"] != TABLE[b]["family"]]

finite = st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False)
REL = 1e-12


def close(a: float, b: float, rel: float = REL, abs_: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(pair=st.sampled_from(PAIRS), x=finite)
def test_round_trip(pair, x):
    _, a, b = pair
    y = units.convert(units.convert(x, a, b), b, a)
    assert close(y, x), (a, b, x, y)


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(tr=st.sampled_from(TRIPLES), x=finite)
def test_compose(tr, x):
    _, a, b, c = tr
    two = units.convert(units.convert(x, a, b), b, c)
    one = units.convert(x, a, c)
    assert close(two, one, rel=1e-9), (a, b, c, x, two, one)


@settings(max_examples=300)
@given(key=st.sampled_from(list(TABLE)), x=finite)
def test_self_is_identity_exactly(key, x):
    assert units.convert(x, key, key) == x, (key, x, units.convert(x, key, key))


@settings(max_examples=200)
@given(pair=st.sampled_from(CROSS), x=finite)
def test_cross_family_refused(pair, x):
    a, b = pair
    with pytest.raises(units.UnitError):
        units.convert(x, a, b)


@given(junk=st.text(min_size=1, max_size=8).filter(lambda s: units.normalize(s) is None))
@settings(max_examples=200)
def test_unknown_refused(junk):
    with pytest.raises(units.UnitError):
        units.convert(1.0, junk, "g")


@pytest.mark.parametrize("x", [0.0, -0.0, -5.0, 1e308, -1e308, 5e-324, float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("a,b", [("kg", "mg"), ("µg", "kg"), ("K", "°C"), ("°F", "K"), ("t d⁻¹", "g h⁻¹")])
def test_edges_report(x, a, b):
    """Records what convert answers at the edges (no assertion beyond: it never answers a finite
    number for a non-finite input, and never a non-finite number for a finite one without saying so)."""
    y = units.convert(x, a, b)
    print(f"EDGE convert({x!r}, {a!r}, {b!r}) = {y!r}")
    if math.isfinite(x):
        assert math.isfinite(y), f"a finite {x} {a} becomes {y} {b} with no refusal"
