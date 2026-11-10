"""H12-02's probes: for each of conformance checks 1, 3, 4, 5 and 8, an engine
or a service that breaks the check, and the check's own function failing it.

run.sh copies this file into a scratch worktree's core/tests/ and runs it
there. On the tree as it stands every probe passes: each check fails the
break it is shown. Under the mutation that makes that check hold whatever it
reads, its probe fails, which shows the mutation changes what the check
decides; the suite's own tests pass under the same mutation. Every value is a
placeholder in a placeholder unit, on the sample engine the suite uses.
"""
from __future__ import annotations

import time

from sqlalchemy import update

from openferment_core import db, projects, tools
from openferment_core.db import models as t
from openferment_core.engine import conform, runs, simulator
from openferment_core.engine.sample import SAMPLE
from test_engines import engines  # noqa: F401  (the registry of the sample)
from test_sff import StandInToolkit, small_doc

BY = "conformance test"


def _first():
    return SAMPLE.things()[0]


def test_probe_check_1_fails_a_door_that_reaches_the_worker_before_it_refuses(engines, monkeypatch):
    """A service whose tool door asks the engine to compute before it refuses
    the stray number: every answer is still a refusal and no run is kept,
    and the engine was reached."""
    real = tools.run

    def reaching(name, raw, ctx=None):
        if name == "engine_run":
            SAMPLE.compute("placeholder", None, [])
        return real(name, raw, ctx)

    monkeypatch.setattr(tools, "run", reaching)
    ok, said = conform._bare_number(SAMPLE, "placeholder", BY)
    assert "the engine was reached" in said and "0 run kept" in said, said
    assert not ok, f"check 1 held a door that reached the engine: {said}"


def test_probe_check_3_fails_a_run_that_no_row_keeps(engines, monkeypatch):
    """A service that answers a run and keeps no runs row for it: the same id
    twice, done, keyed by its basis, and zero rows."""

    async def keeps_nothing(project_id, run, by):
        return None

    monkeypatch.setattr(runs, "_put", keeps_nothing)
    ok, said, _ = conform._run_twice(SAMPLE, _first(), [], BY)
    assert "asked twice, is 0 rows" in said and "its id the artifact id of its basis" in said, said
    assert not ok, f"check 3 held a run no row keeps: {said}"


def test_probe_check_4_fails_an_output_that_moves_between_two_runs(engines, monkeypatch):
    """docs/api/engines.md, The worker: an output that moves between two runs
    of one request, a clock reading among them, makes the replay differ and
    fails conformance check 4."""
    real = SAMPLE.call

    def clocked(op, args, *, timeout_s=None):
        got = real(op, args, timeout_s=timeout_s)
        if op != "run":
            return got
        return {**got, "outputs": [*got["outputs"], {"name": "a clock reading",
                                                     "value": float(time.perf_counter_ns()), "unit": "placeholder-ns"}]}

    monkeypatch.setattr(SAMPLE, "call", clocked)
    ok, said, run = conform._run_twice(SAMPLE, _first(), [], BY)
    assert ok and run is not None, said
    (four, four_said), _ = conform._replayed(SAMPLE, run)
    assert "difference" in four_said and not four_said.startswith("identical"), four_said
    assert not four, f"check 4 held a replay that differs: {four_said}"


def test_probe_check_5_fails_a_run_whose_sff_file_does_not_validate(engines, monkeypatch):
    """An engine whose worker writes an SFF file the toolkit finds invalid:
    the file is kept with its findings and a score (engine/sff.py
    keep_run_file), and the run's record says it is not valid."""
    monkeypatch.setattr(simulator, "call", StandInToolkit())
    real = SAMPLE.call

    def writes_a_file(op, args, *, timeout_s=None):
        if op == "sff_export":
            return {"flowsheet": small_doc()}
        return real(op, args, timeout_s=timeout_s)

    monkeypatch.setattr(SAMPLE, "call", writes_a_file)
    ok, said, run = conform._run_twice(SAMPLE, _first(), [], BY)
    assert ok and run is not None and run.sff is not None, said
    assert run.sff.valid is False and run.sff.score is not None, run.sff
    _, (five, five_said) = conform._replayed(SAMPLE, run)
    assert "not valid" in five_said, five_said
    assert not five, f"check 5 held an SFF file that does not validate: {five_said}"


def test_probe_check_8_fails_a_row_whose_created_by_is_not_the_asker(engines):
    """A runs row whose created_by names someone other than the person who
    asked for the run, its body's by the asker's."""
    ok, said, run = conform._run_twice(SAMPLE, _first(), [], BY)
    assert ok and run is not None, said

    async def relabel() -> None:
        async with db.session() as s:
            await s.execute(update(t.runs).where(t.runs.c.project_id == projects.current(), t.runs.c.id == run.id)
                            .values(created_by="someone else"))

    db.run(relabel())
    assert conform._created_by(run.id) == "someone else" and run.by == BY
    every = SAMPLE.things()
    held, words = conform._asked_by(SAMPLE, every, every[0], [], run, BY, door=True)
    assert "created_by 'someone else'" in words, words
    assert not held, f"check 8 held a row whose created_by is not the asker: {words}"
