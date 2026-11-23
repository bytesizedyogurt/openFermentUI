"""A pytest plugin for H12-02: which tests reach each of conform's check
functions. Loaded with `-p h12_02_reached` (this directory on PYTHONPATH); it
writes {"conform": <the file imported>, "reached": {function: [node ids]}} to
the path H12_02_REACHED names when the session ends. It changes nothing the
tests see beyond one wrapper frame around each function."""
from __future__ import annotations

import json
import os

import pytest

NAMES = ("_bare_number", "_origins", "_run_twice", "_replayed", "_asked_by")
_current: list[str | None] = [None]
_reached: dict[str, list[str]] = {n: [] for n in NAMES}
_file: list[str] = [""]


def pytest_collection_finish(session):
    from openferment_core.engine import conform

    _file[0] = conform.__file__
    for n in NAMES:
        real = getattr(conform, n)

        def wrapped(*a, _real=real, _n=n, **k):
            node = _current[0]
            if node and node not in _reached[_n]:
                _reached[_n].append(node)
            return _real(*a, **k)

        setattr(conform, n, wrapped)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _current[0] = item.nodeid
    yield
    _current[0] = None


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("H12_02_REACHED")
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"conform": _file[0], "reached": _reached}, f, indent=1)
