"""What a run's computation reports about itself (alpha 2.2 D0.1;
docs/api/workers.md, `run`; docs/api/engines.md, The worker).

A contract engine's worker may answer `diagnostics` beside its outputs: the
time its computation took, the iterations it made, each a name, a finite
number or words, and a unit. The service keeps them on the run's row, beside
`durationMs`, and nowhere in the run's artifact, so the run's id, its output
hash, its replay and every reader of `outputs.values` (comparisons, runbooks,
evidence) stand as they stood: the pins hold. The same request asked again is
the kept row with its first computation's diagnostics. A diagnostics answer
outside that shape breaks the contract, and conformance check 3 holds the
shape. Every value here is a placeholder in a placeholder unit.
"""
from __future__ import annotations

import re
import sys

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, artifacts, llm, tools
from openferment_core.engine import EngineBroken, conform, contract, registry, runs
from openferment_core.engine.sample import SAMPLE
from openferment_core.models import EngineRun, RunDiagnostic
from test_engine_pins import PINS
from test_engines import (SAMPLE_ENTRY, _forget, _points, _write_package, engines,  # noqa: F401  (the registry)
                          given)

# What the stand-in worker reports beside the sample's outputs: a count of its
# computations (which moves on every one, as a clock reading would) and words.
TIME = "time taken"
WORDS = "a placeholder note"


def reporting(monkeypatch, engine=SAMPLE) -> list[dict]:
    """The engine's worker as it is, its `run` op answering diagnostics beside
    its outputs: the count of run ops asked so far, in a placeholder unit, and
    words. Answers the list of the run ops asked."""
    real = engine.call
    asked: list[dict] = []

    def call(op, args, *, timeout_s=None):
        got = real(op, args, timeout_s=timeout_s)
        if op != "run":
            return got
        asked.append(args)
        return {**got, "diagnostics": [{"name": TIME, "value": float(len(asked)), "unit": "placeholder-ms"},
                                       {"name": WORDS, "value": "one way", "unit": ""}]}

    monkeypatch.setattr(engine, "call", call)
    return asked


def test_a_run_keeps_its_diagnostics_beside_its_outputs_and_its_artifact_and_pin_stand_as_before(engines, monkeypatch):
    asked = reporting(monkeypatch)
    run = SAMPLE.run("placeholder", None, [given("a-parameter", 2.5, note="a placeholder")], "Ada Moreno")
    assert [(d.name, d.value, d.unit) for d in run.diagnostics] == [(TIME, 1.0, "placeholder-ms"),
                                                                     (WORDS, "one way", "")]
    art = artifacts.get(run.artifactId)
    # The artifact is the computation alone: the pin's id and output hash, bit for bit.
    assert (art.id, art.outputHash) == PINS["engine.sample"] and "diagnostics" not in art.output
    assert [v["name"] for v in run.outputs["values"]] == ["given a-parameter", "count"]
    # A replay asks the run op again, whose diagnostics move, and compares the outputs alone.
    replayed = SAMPLE.replay(run)
    assert replayed.identical and replayed.differences == [] and len(asked) == 2
    # The same request again is the kept row, its first computation's diagnostics, the run op left alone.
    again = SAMPLE.run("placeholder", None, [given("a-parameter", 2.5, note="a placeholder")], "Grace Hopper")
    assert again == run and len(asked) == 2
    served = TestClient(api.app).get(f"/api/runs/{run.id}").json()["run"]
    assert served["diagnostics"] == [{"name": TIME, "value": 1.0, "unit": "placeholder-ms"},
                                     {"name": WORDS, "value": "one way", "unit": ""}]
    assert served["durationMs"] == art.durationMs


def test_a_run_whose_engine_reports_none_keeps_an_empty_list_and_an_older_row_reads_so():
    held = EngineRun.model_validate({"id": "0123456789abcdef", "plant": "placeholder", "status": "done",
                                     "tool": "engine.sample", "toolVersion": "v", "inputs": [], "by": "a person",
                                     "at": "2026-11-04T00:00:00Z"})
    assert held.diagnostics == []


def test_engine_report_names_the_diagnostics_as_words_and_cites_the_outputs_alone(engines, monkeypatch):
    plain_worker = SAMPLE.call
    reporting(monkeypatch)
    ctx = tools.ToolContext(model=llm.DEFAULT_PRIMARY)
    ran = tools.run("engine_run", {"engine": "sample", "plant": "placeholder"}, ctx)
    assert ran.error is None, ran.error
    read = tools.run("engine_report", {"engine": "sample", "run": ran.summary["runId"]}, ctx)
    assert read.error is None, read.error
    said = read.summary["diagnostics"]
    assert said["count"] == 2 and said["shown"] == [{"name": TIME, "value": 1.0, "unit": "placeholder-ms"},
                                                    {"name": WORDS, "value": "one way", "unit": ""}]
    assert "a replay compares the outputs alone" in said["note"]
    # Evidence is the outputs': no diagnostic is an evidence id.
    assert [e.id for e in read.evidence] == [f"{ran.summary['artifactId']}:values.count"]
    narrowed = tools.run("engine_report", {"engine": "sample", "run": ran.summary["runId"], "parameters": "placeholder"},
                         ctx)
    assert narrowed.summary["diagnostics"] == said, "the parameters read keeps the diagnostics' words"
    # A run whose engine reports none names none.
    monkeypatch.setattr(SAMPLE, "call", plain_worker)
    other = tools.run("engine_run", {"engine": "sample", "plant": "placeholder-configured"}, ctx)
    assert other.error is None, other.error
    plain = tools.run("engine_report", {"engine": "sample", "run": other.summary["runId"]}, ctx)
    assert plain.error is None and "diagnostics" not in plain.summary


def test_a_summary_names_as_many_diagnostics_as_its_room_holds_and_counts_them_all():
    from openferment_core.tools import engine as engine_tools

    many = [RunDiagnostic(name=f"placeholder {n:02d} " + "x" * 150, value=float(n), unit="placeholder-unit")
            for n in range(50)]
    run = EngineRun(id="0123456789abcdef", plant="placeholder", status="done", tool="engine.sample", toolVersion="v",
                    inputs=[], by="a person", at="2026-11-04T00:00:00Z", diagnostics=many)
    said = engine_tools.diagnostics_said(run)
    assert said["count"] == 50 and 0 < len(said["shown"]) < 50
    import json

    assert len(json.dumps(said["shown"])) <= engine_tools.DIAGNOSTICS_BUDGET + 2


@pytest.mark.parametrize(("diagnostics", "says"), [
    ({"name": TIME}, "diagnostics that are no list"),
    ([{"name": TIME, "value": True, "unit": "1"}], "a diagnostic that is no name, value and unit"),
    ([{"name": TIME, "value": 1.0}], "a diagnostic that is no name, value and unit"),
    ([{"name": TIME, "value": float("nan"), "unit": "1"}], "a diagnostic whose number is NaN or infinite"),
    ([{"name": TIME, "value": float("inf"), "unit": "1"}], "a diagnostic whose number is NaN or infinite"),
    ([{"name": " ", "value": 1.0, "unit": "1"}], "a diagnostic whose name is blank or longer than 200 characters"),
    ([{"name": "n" * 201, "value": 1.0, "unit": "1"}], "a diagnostic whose name is blank or longer than 200"),
    ([{"name": TIME, "value": 1.0, "unit": "1"}, {"name": TIME, "value": 2.0, "unit": "1"}],
     "two diagnostics named 'time taken'"),
    ([{"name": f"d{n}", "value": 1.0, "unit": "1"} for n in range(51)], "51 diagnostics, more than the 50 a run keeps"),
    # A JSON integer past a float's range, which Python reads whole (alpha 2.2 D.0 review).
    ([{"name": TIME, "value": 10**400, "unit": "1"}], "a diagnostic whose number lies past a float's range"),
])
def test_diagnostics_outside_their_shape_break_the_contract_and_keep_nothing(engines, monkeypatch, diagnostics, says):
    real = SAMPLE.call

    def call(op, args, *, timeout_s=None):
        got = real(op, args, timeout_s=timeout_s)
        return {**got, "diagnostics": diagnostics} if op == "run" else got

    monkeypatch.setattr(SAMPLE, "call", call)
    with pytest.raises(EngineBroken, match=re.escape(says)):
        SAMPLE.compute("placeholder", None, [])
    route = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder"})
    assert route.status_code == 503 and says in route.json()["detail"]
    assert runs.listed("sample") == [], "a break keeps no row, so the next ask computes afresh"


def test_an_output_past_a_floats_range_breaks_the_contract_before_anything_is_kept(engines, monkeypatch):
    """Alpha 2.2 D.0 review: an output's integer past a float's range is a
    break in words (EngineBroken, a 503), before the artifact is kept, so the
    next ask computes afresh."""
    real = SAMPLE.call

    def call(op, args, *, timeout_s=None):
        got = real(op, args, timeout_s=timeout_s)
        return {**got, "outputs": [{"name": "count", "value": 10**400, "unit": "1"}]} if op == "run" else got

    monkeypatch.setattr(SAMPLE, "call", call)
    route = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder"})
    assert route.status_code == 503 and "an output whose number lies past a float's range" in route.json()["detail"]
    assert runs.listed("sample") == [] and artifacts.all_artifacts() == []


def test_a_diagnostics_value_is_a_finite_number_or_words_in_words():
    for value, says in ((True, "a diagnostic's value is a finite number or words; a boolean is refused"),
                        (float("nan"), "a diagnostic's number is finite"),
                        (10**400, "a diagnostic's number is finite, inside a float's range")):
        with pytest.raises(ValueError, match=re.escape(says)):
            RunDiagnostic(name=TIME, value=value, unit="1")
    assert RunDiagnostic(name=TIME, value=2**1023, unit="1").value == float(2**1023), "the largest power a float holds"


def test_check_3_holds_a_runs_diagnostics_in_their_shape(engines, monkeypatch):
    reporting(monkeypatch)
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY)}
    assert all(c.ok for c in found.values()), [(n, c.said) for n, c in found.items() if not c.ok]
    assert (f"it reports 2 diagnostics beside its outputs ({TIME}, {WORDS}), each a name, a value and a unit, kept on "
            "its row and nowhere in its artifact; asked again, the first computation's") in found[3].said
    assert found[4].ok and "identical" in found[4].said, "the replay leaves the diagnostics uncompared"
    assert "diagnostics in their shape" in conform.CHECKS[3]


def test_check_3_fails_a_run_whose_row_answers_other_diagnostics_when_asked_again(engines, monkeypatch):
    reporting(monkeypatch)
    real = runs.run_with
    asked = []

    def moved(*a, **k):
        report = real(*a, **k)
        asked.append(report)
        if len(asked) == 2:
            changed = [d.model_copy(update={"value": "another"}) for d in report.run.diagnostics]
            return report.model_copy(update={"run": report.run.model_copy(update={"diagnostics": changed})})
        return report

    monkeypatch.setattr(runs, "run_with", moved)
    ok, said, _ = conform._run_twice(SAMPLE, SAMPLE.things()[0], [], "conformance test")
    assert not ok and "asked again, other diagnostics" in said


def test_a_diagnosed_block_hands_the_run_op_its_list_and_none_outside_it():
    assert contract._DIAGNOSED.get() is None
    with contract.diagnosed() as held:
        assert contract._DIAGNOSED.get() is held and held == []
    assert contract._DIAGNOSED.get() is None


# ── an engine of its own, through the worker protocol ──────────────────

WORKER = '''\
"""A placeholder engine's worker whose run reports the time it took."""
import time

from openferment_core.workers import serve

THINGS = [{"id": "a-thing", "title": "A placeholder thing", "configurations": [],
           "precision": {"rtol": 0, "atol": 0}}]


class Refused(Exception):
    pass


def _thing(args):
    if args.get("thing") != "a-thing":
        raise Refused(f"the reporting engine runs no thing {args.get('thing')!r}")


def things(args):
    return {"things": THINGS}


def parameters(args):
    _thing(args)
    return {"parameters": [{"key": "a-parameter", "label": "A placeholder", "unit": "placeholder-unit", "value": 1.0,
                            "origin": {"kind": "convention", "note": "a placeholder setting"},
                            "boundsReason": "a placeholder with no bounds"}]}


def run(args):
    started = time.perf_counter()
    _thing(args)
    outputs = [{"name": f"given {v['name']}", "value": v["value"], "unit": v["unit"]} for v in args["inputs"]]
    outputs.append({"name": "count", "value": len(args["inputs"]), "unit": "1"})
    took = (time.perf_counter() - started) * 1000.0
    return {"outputs": outputs, "diagnostics": [{"name": "time taken", "value": took, "unit": "ms"}]}


def sff_export(args):
    _thing(args)
    raise Refused("the reporting engine has no plant, so it writes no SFF file")


if __name__ == "__main__":
    serve({"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}, name="reporting")
'''
ENGINE = ('from openferment_core.engine import WorkerEngine\n'
          'ENGINE = WorkerEngine(name="reporting", worker="a_reporting_engine.worker",'
          ' distributions=("openferment-core",))\n')


@pytest.fixture
def reporting_engine(monkeypatch, tmp_path):
    """An engine of its own in a package of its own, its worker a process of
    its own speaking the protocol, registered through the group."""
    _write_package(tmp_path, {"a_reporting_engine/__init__.py": "", "a_reporting_engine/worker.py": WORKER,
                              "a_reporting_engine/engine.py": ENGINE})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("reporting", "a_reporting_engine.engine:ENGINE")))
    registry.reset()
    yield registry.get("reporting")
    engine = registry.found()["reporting"].engine
    if engine is not None and engine._sim is not None:
        engine._sim.close()
    registry.reset()
    _forget("a_reporting_engine")


def test_a_worker_of_its_own_reports_the_time_its_run_took_and_its_replay_holds(reporting_engine):
    client = TestClient(api.app)
    first = client.post("/api/engines/reporting/run", json={"thing": "a-thing", "by": "Ada Moreno"})
    assert first.status_code == 200, first.text
    run = first.json()["run"]
    ((name, value, unit),) = [(d["name"], d["value"], d["unit"]) for d in run["diagnostics"]]
    assert (name, unit) == ("time taken", "ms") and isinstance(value, float) and value >= 0
    art = artifacts.get(run["artifactId"])
    assert "diagnostics" not in art.output and [v["name"] for v in run["outputs"]["values"]] == ["count"]
    replayed = client.post(f"/api/biorepo/artifacts/{run['artifactId']}/replay").json()
    assert replayed["identical"] is True, "the time its replay took is left uncompared"
    assert client.post("/api/engines/reporting/run", json={"thing": "a-thing", "by": "Grace Hopper"}).json()["run"] == run


def test_the_eight_checks_hold_on_an_engine_that_reports_the_time_its_run_took(reporting_engine):
    found = {c.number: c for c in conform.checks(reporting_engine, by="conformance test",
                                                  entry="a_reporting_engine.engine:ENGINE")}
    assert all(c.ok for c in found.values()), [(n, c.said) for n, c in found.items() if not c.ok]
    assert "it reports 1 diagnostic beside its outputs (time taken)" in found[3].said
    assert found[4].said.startswith("identical"), found[4].said
    assert "a_reporting_engine" in sys.modules
