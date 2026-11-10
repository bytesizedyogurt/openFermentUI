"""H9-03 probes: the spend gate's two tests, with the budget refusal raised where the service raises it.

run.sh copies this file into a scratch worktree's core/tests and runs it there beside
test_writes.py::test_an_extraction_the_budget_refuses_becomes_a_spend_proposal and
test_proposals_review.py::test_a_spend_proposals_why_holds_no_number. Those two replace
extract.extract_paper with a function raising llm.BudgetExhausted. Here extract_paper is the real one:
the project holds a document, the day's cap is too small for one extraction, and llm.call's own
reservation (llm._reserve, spend.reserve) refuses the call. A stand-in client stands where the Anthropic
client would; it fails the probe if a request is ever about to be sent, so nothing leaves the machine.
Each probe writes what it saw as a JSON line to the file H9_03_OUT names.
"""
from __future__ import annotations

import json
import os

import pytest

from openferment_core import extract, llm, proposals
from openferment_core.validate import find_number
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)
from test_writes import ctx, store, write  # noqa: F401  (every store under tmp_path)

CAP_USD = "0.001"
PASSAGES = [{"id": "s1", "heading": "Results", "text": "Yeast ferments glucose to ethanol in the broth."}]


class _NoSend:
    """Where the Anthropic client stands: no request is ever sent through it."""

    class messages:  # noqa: N801
        @staticmethod
        def stream(**kw):
            raise AssertionError("H9-03 probe: a model request was about to be sent")


@pytest.fixture()
def tiny_cap(store, monkeypatch):  # noqa: F811
    store.held["X1"] = PASSAGES
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", CAP_USD)
    monkeypatch.setattr(llm, "_default_client", lambda: _NoSend())
    return store


def _note(probe: str, **what) -> None:
    out = os.environ.get("H9_03_OUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps({"probe": probe, **what}, default=str) + "\n")


def test_probe_extract_paper_raises_budget_exhausted_under_the_cap(tiny_cap):
    """What the two tests' stub raises, asked of the real function under a cap that refuses."""
    try:
        extract.extract_paper("X1")
    except Exception as e:  # noqa: BLE001  (what it raises is the observation)
        cause = e.__cause__
        _note("extract_paper", module=extract.__file__, raised=type(e).__name__,
              isBudgetExhausted=isinstance(e, llm.BudgetExhausted),
              cause=type(cause).__name__ if cause is not None else None, words=str(e)[:200])
        assert isinstance(e, llm.BudgetExhausted), (
            f"extract_paper raised {type(e).__name__} (from {type(cause).__name__ if cause else None}): {e}")
        return
    _note("extract_paper", module=extract.__file__, raised=None)
    pytest.fail("extract_paper returned under a cap too small for one call")


def test_probe_the_spend_gate_through_the_real_extract_path(pool, tiny_cap):  # noqa: F811
    """test_writes.py's spend-gate assertions, the budget refusal raised by llm.call's reservation."""
    r = write("intake", ctx(pool), "extract", target="X1")
    kept = proposals.open_ones()
    _note("intake_write", error=r.error, summary=r.summary, proposals=len(kept))
    assert r.summary.get("state") == "proposed" and r.summary.get("gate") == "spend", r.error
    [p] = kept
    assert p.server and "budget" in p.why and find_number(p.why) is None and find_number(p.title) is None
