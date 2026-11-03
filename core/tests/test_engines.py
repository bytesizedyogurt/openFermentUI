"""The engine contract (alpha 2.2 stage B; docs/api/engines.md, ADR-015).

The registry loads every object of the entry-point group `openferment.engines`
and names what keeps one from use, whatever the object raises, an entry module
asking the registry as it is imported, or one bringing its worker or a heavy
module into the service; `GET /api/engines` lists each, a cold worker given a
short wait and a worker's things kept after its first answer; a run of a
contract engine is one `runs` row keyed by its basis, the same request twice
that one row, a value set kept with its origin and its own day, a bare number
refused before the worker is reached, a run the engine refuses kept as a
receipt, a worker answering outside the protocol broken with nothing kept, a
replay held to the stated precision, its SFF refusal kept in words, its worker
started with no key and no database address; BioSTEAM checks a value's unit
before the plant is built; the four engine tools take the engine, and a write
at the HTTP door names its caller; and the eight conformance checks hold for
the contract's own sample engine (engine/sample.py over
workers/sample_worker.py, which computes nothing), its verdict kept for `GET
/api/engines` and `pnpm ready`. After the review of B.6: one configuration
rule and one configuration length at every door, a value with a range or a
basis refused, every module the service keeps out held out whatever order the
engines load in, a replay naming a moved version, and the things checked in
the order named. Stage C (D4): a parameter with no default, said so and
waited for; the kinetics engine registered by the core's own entry point,
listed with no worker, each of its things run as one row at every door, a
parameter that waits refused with nothing kept, a refusal inside the
integration kept as a receipt, and the eight checks holding on it with the
placeholders conformance builds, in the test's database and on a scratch one.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from importlib.metadata import EntryPoint
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import TEST_PROJECT
from openferment_core import api, artifacts, events, llm, ready, tools
from openferment_core.engine import EngineBroken, EngineRefused, conform, contract, library, registry, runs, simulator
from openferment_core.engine.sample import SAMPLE
from openferment_core.literature import KIT_SETTINGS
from openferment_core.models import (CONFIGURATION_MAX, EngineInput, EngineParameter, EngineRun, EngineThing,
                                     ParameterSpec, Quantity)
from openferment_core.workers import WorkerCrashed, WorkerTimeout, withheld

SAMPLE_ENTRY = "openferment_core.engine.sample:SAMPLE"
ROOT = Path(__file__).resolve().parents[2]
BIOSTEAM_ENTRY = "openferment_core.engine.biosteam:ENGINE"
# The day a person set a value, as the request says it: a placeholder day.
DAY = "2026-10-30"
SAMPLE_VERSION = "engine run 1 · sample · openferment-core 0.1.0"


def _points(*pairs: tuple[str, str]) -> list[EntryPoint]:
    return [EntryPoint(name=n, value=v, group=registry.GROUP) for n, v in pairs]


@pytest.fixture
def engines(monkeypatch):
    """A registry of BioSTEAM, the sample, and three that cannot be used."""
    points = _points(("biosteam", BIOSTEAM_ENTRY), ("sample", SAMPLE_ENTRY),
                     ("broken", "openferment_core.engine.no_such_module:ENGINE"),
                     ("misnamed", SAMPLE_ENTRY), ("Not-An-Engine", SAMPLE_ENTRY))
    monkeypatch.setattr(registry, "entry_points", lambda: points)
    registry.reset()
    yield
    registry.reset()


def said(origin: dict) -> dict:
    """An origin as it reads, the fields it leaves unset dropped."""
    return {k: v for k, v in origin.items() if v is not None}


def person(value, unit="placeholder-unit", by="Ada Moreno", **origin):
    return {"value": value, "unit": unit, "origin": {"kind": "person-assumption", "by": by, "at": DAY, **origin}}


def given(name, value, unit="placeholder-unit", **origin) -> EngineInput:
    return EngineInput.model_validate({"name": name, "quantity": person(value, unit, **origin)})


def test_the_registry_loads_each_engine_of_the_group_and_says_what_keeps_one_from_use(engines):
    found = registry.found()
    assert found["sample"].engine is SAMPLE and found["biosteam"].engine is not None
    assert "could not be loaded: ModuleNotFoundError" in found["broken"].error
    assert "names itself 'sample' where its entry point names 'misnamed'" in found["misnamed"].error
    assert "no engine name" in found["Not-An-Engine"].error
    with pytest.raises(registry.EngineUnavailable, match="cannot be used"):
        registry.get("broken")
    with pytest.raises(registry.EngineNotFound, match="the engines are"):
        registry.get("nosuch")


class _Heavy:
    """An engine that names heavy modules and no worker to keep them in."""

    name, worker, heavy = "heavy", None, ("a_heavy_module",)

    def __getattr__(self, method):
        if method in contract.METHODS:
            return lambda *a, **k: None
        raise AttributeError(method)


HEAVY = _Heavy()


class _Point:
    """An entry point as a distribution installs it: its name, its value and its distribution's."""

    def __init__(self, name, value, distribution):
        self.name, self.value, self.group = name, value, registry.GROUP
        self.dist = type("Dist", (), {"name": distribution})()

    def load(self):
        return EntryPoint(self.name, self.value, self.group).load()


def test_the_cores_own_engine_keeps_its_name_and_another_package_claiming_it_is_set_aside(monkeypatch):
    points = [_Point("sample", SAMPLE_ENTRY, "openferment-core"),
              _Point("sample", "a_strangers_package.engine:ENGINE", "a-strangers-package")]
    monkeypatch.setattr(registry, "entry_points", lambda: points)
    registry.reset()
    try:
        assert registry.get("sample") is SAMPLE
        (aside,) = registry.set_aside()
        assert aside.entry == "a_strangers_package.engine:ENGINE" and "the core's own engine is named" in aside.error
        listed = [(i.name, i.entryPoint, i.error is None) for i in registry.infos()]
        assert ("sample", SAMPLE_ENTRY, True) in listed and ("sample", aside.entry, False) in listed
    finally:
        registry.reset()


def test_two_packages_claiming_one_name_are_both_set_aside(monkeypatch):
    points = [_Point("twin", SAMPLE_ENTRY, "one-package"), _Point("twin", SAMPLE_ENTRY, "another-package")]
    monkeypatch.setattr(registry, "entry_points", lambda: points)
    registry.reset()
    try:
        with pytest.raises(registry.EngineUnavailable, match="2 packages register an engine named 'twin'"):
            registry.get("twin")
    finally:
        registry.reset()


def test_the_contract_pages_imports_run_and_its_examples_validate():
    page = (ROOT / "docs" / "api" / "engines.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```(\w+)\n(.*?)```", page, flags=re.S)
    imports = [line for lang, body in blocks if lang == "python" for line in body.splitlines()
               if line.startswith(("from openferment_core", "import openferment_core"))]
    assert imports
    for line in imports:
        exec(line, {})  # noqa: S102  (the page's own import lines, as a stranger runs them)
    shapes = {"EngineThing": EngineThing, "EngineParameter": EngineParameter, "EngineInput": EngineInput}
    checked = 0
    for heading, body in re.findall(r"### `(\w+)`\n\n((?:```json\n.*?```\s*)+)", page, flags=re.S):
        for example in re.findall(r"```json\n(.*?)```", body, flags=re.S):
            shapes[heading].model_validate(json.loads(example))
            checked += 1
    assert checked >= 4


def test_importing_the_engine_package_imports_none_of_its_modules():
    import subprocess
    import sys

    probe = ("import sys, openferment_core.engine as e; from openferment_core.engine import Engine, EngineRefused; "
             "print(sorted(m for m in sys.modules if m.startswith('openferment_core.engine.')))")
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, cwd=ROOT / "core")
    assert done.returncode == 0 and done.stdout.strip() == "[]", done.stderr[-400:]


def test_a_run_replays_on_a_service_that_has_just_started(engines, monkeypatch):
    made = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder"}).json()["run"]
    # A service just started knows no engine tool until it reads the registry.
    monkeypatch.delitem(artifacts._REGISTRY, "engine.sample")
    registry.reset()
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("sample", SAMPLE_ENTRY)))
    replayed = TestClient(api.app).post(f"/api/biorepo/artifacts/{made['artifactId']}/replay")
    assert replayed.status_code == 200 and replayed.json()["identical"]


def test_an_engine_that_computes_with_heavy_modules_names_the_worker_they_live_in(monkeypatch):
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("heavy", "tests.test_engines:HEAVY")))
    registry.reset()
    try:
        assert "declares no worker to keep them in" in registry.found()["heavy"].error
    finally:
        registry.reset()


def test_a_parameter_is_a_parameter_spec_with_its_default_and_where_it_comes_from():
    p = EngineParameter(key="a-parameter", label="A placeholder", unit="placeholder-unit", value=1.0,
                        origin={"kind": "library-default", "ref": "a-package@0.1.0"}, boundsReason="none stated")
    assert isinstance(p, ParameterSpec) and p.sourceRule == ["library-default"] and p.group == "parameters"
    for bad, says in [
        ({"origin": {"kind": "person-assumption", "by": "Ada Moreno"}}, "never person-assumption"),
        ({"origin": {"kind": "convention"}}, "says what it is"),
        ({"value": "sideways", "choices": ["one", "another"]}, "none of its choices"),
        ({"boundsReason": " "}, "written reason"),
    ]:
        with pytest.raises(ValidationError, match=says):
            EngineParameter(**{**p.model_dump(exclude={"sourceRule"}), **bad})


def test_the_service_registers_biosteam_through_its_own_entry_point():
    registry.reset()
    try:
        assert registry.found()["biosteam"].entry == BIOSTEAM_ENTRY
        assert "sample" not in registry.names()
    finally:
        registry.reset()


def test_get_api_engines_lists_each_with_its_things_worker_and_error(engines):
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
    sample = listed["sample"]
    assert sample["entryPoint"] == SAMPLE_ENTRY and sample["worker"] == SAMPLE.worker and sample["error"] is None
    assert [t["id"] for t in sample["things"]] == ["placeholder", "placeholder-configured", "refuses"]
    assert sample["version"] == {"openferment-core": "0.1.0"} and sample["conformance"] is None
    assert listed["broken"]["error"].startswith("openferment_core.engine.no_such_module:ENGINE could not be loaded")
    assert listed["biosteam"]["worker"] == "openferment_core.workers.proforma_worker"
    assert "biosteam" in listed["biosteam"]["heavy"]
    params = TestClient(api.app).get("/api/engines/sample/parameters", params={"thing": "placeholder"}).json()
    assert [(p["key"], p["origin"]["kind"]) for p in params] == [("a-parameter", "library-default"),
                                                                 ("a-setting", "convention")]
    assert TestClient(api.app).get("/api/engines/nosuch/parameters", params={"thing": "x"}).status_code == 404
    assert TestClient(api.app).get("/api/engines/broken/parameters", params={"thing": "x"}).status_code == 503


def test_a_run_is_one_row_keyed_by_its_basis_and_the_same_request_twice_is_that_row(engines):
    client = TestClient(api.app)
    first = client.post("/api/engines/sample/run", json={"thing": "placeholder", "by": "Ada Moreno"})
    assert first.status_code == 200, first.text
    run = first.json()["run"]
    assert (run["engine"], run["plant"], run["status"], run["provenance"]) == ("sample", "placeholder", "done", "computed")
    assert run["tool"] == "engine.sample" and run["toolVersion"] == SAMPLE_VERSION
    assert run["outputs"]["values"] == [{"name": "count", "quantity": {
        "value": 0.0, "unit": "1", "origin": {"kind": "artifact", "ref": run["artifactId"]}}}]
    assert run["sff"] is None and run["sffRefused"] == "the sample engine has no plant, so it writes no SFF file"
    assert {i["name"] for i in run["inputs"]} == {"engine", "thing", "precision.rtol", "precision.atol"}
    again = client.post("/api/engines/sample/run", json={"thing": "placeholder", "by": "Ada Moreno"}).json()["run"]
    assert again["id"] == run["id"] and len(runs.listed("sample")) == 1
    other = client.post("/api/engines/sample/run", json={"thing": "placeholder-configured"}).json()["run"]
    assert other["configuration"] == "one way" and other["id"] != run["id"] and other["by"] == "this browser"


def test_a_value_set_is_kept_with_its_origin_and_makes_the_run_assumed(engines):
    asked = {"thing": "placeholder", "by": "Ada Moreno",
             "inputs": [{"name": "a-parameter", "quantity": person(2.5, note="a placeholder")}]}
    run = TestClient(api.app).post("/api/engines/sample/run", json=asked).json()["run"]
    assert run["provenance"] == "assumed"
    (value,) = [i for i in run["inputs"] if i["name"] == "value a-parameter"]
    # Written as a library run's override is: the day its origin says it was set, then its note.
    assert said(value["quantity"]["origin"]) == {"kind": "person-assumption", "by": "Ada Moreno", "at": DAY,
                                                 "note": f"typed on {DAY}: a placeholder"}
    assert [(v["name"], v["quantity"]["value"]) for v in run["outputs"]["values"]] == [("given a-parameter", 2.5),
                                                                                    ("count", 1.0)]


def test_a_value_says_the_day_it_was_set_and_the_service_stamps_no_day_of_its_own(engines, monkeypatch):
    client = TestClient(api.app)
    undated = {"name": "a-parameter", "quantity": {"value": 2.5, "unit": "placeholder-unit",
                                                    "origin": {"kind": "person-assumption", "by": "Ada Moreno"}}}
    answer = client.post("/api/engines/sample/run", json={"thing": "placeholder", "inputs": [undated]})
    assert answer.status_code == 422 and "says when it was set (quantity.origin.at)" in answer.text
    assert runs.listed("sample") == []
    with pytest.raises(ValidationError, match="says when it was set"):
        EngineInput.model_validate(undated)
    asked = {"thing": "placeholder", "inputs": [{"name": "a-parameter", "quantity": person(2.5)}]}
    first = client.post("/api/engines/sample/run", json=asked).json()["run"]
    # Asked again on another day, the request is the one it was: its basis holds the value's own day alone.
    monkeypatch.setattr(runs, "_now", lambda: "2027-01-02T00:00:00Z")
    again = client.post("/api/engines/sample/run", json=asked).json()["run"]
    assert again["id"] == first["id"] and len(runs.listed("sample")) == 1
    with pytest.raises(EngineRefused, match="says when it was set"):
        runs._value_source("a-parameter", given("a-parameter", 2.5).quantity.origin.model_copy(update={"at": " "}))


@pytest.mark.parametrize(("body", "says"), [
    ({"thing": "placeholder", "n": 3}, "Extra inputs are not permitted"),
    ({"thing": "placeholder", "inputs": [{"name": "a-parameter", "quantity": person(2.5) | {"n": 3}}]},
     "n is none of them"),
    ({"thing": "placeholder", "inputs": [{"name": "a-parameter", "quantity": {
        "value": 2.5, "unit": "placeholder-unit", "origin": {"kind": "person-assumption", "by": "Ada Moreno", "n": 3}}}]},
     "origin.n is none of them"),
    ({"thing": "placeholder", "inputs": [{"name": "a-parameter", "quantity": person(True)}]}, "never true or false"),
])
def test_a_request_holds_its_own_fields_and_numbers_alone(engines, body, says):
    answer = TestClient(api.app).post("/api/engines/sample/run", json=body)
    assert answer.status_code == 422 and says in answer.text
    assert runs.listed("sample") == []


def test_a_bare_number_is_refused_before_the_worker_is_reached(engines, monkeypatch):
    reached: list[str] = []
    monkeypatch.setattr(SAMPLE, "compute", lambda *a, **k: reached.append("compute"))
    client = TestClient(api.app)
    bare = client.post("/api/engines/sample/run", json={"thing": "placeholder", "inputs": [{"name": "a-parameter",
                                                                                            "quantity": 2.5}]})
    unsigned = client.post("/api/engines/sample/run", json={"thing": "placeholder", "inputs": [
        {"name": "a-parameter", "quantity": {"value": 2.5, "unit": "placeholder-unit"}}]})
    assert bare.status_code == 422 and unsigned.status_code == 422 and "person's assumption" in unsigned.text
    tool = tools.run("engine_run", {"engine": "sample", "plant": "placeholder", "configuration": 7},
                     tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert tool.error and reached == [] and runs.listed("sample") == []


@pytest.mark.parametrize(("inputs", "says"), [
    ([{"name": "nosuch", "quantity": person(1.0)}], "has no parameter 'nosuch'"),
    ([{"name": "a-parameter", "quantity": person(1.0, unit="another-unit")}], "the parameter's unit is"),
    ([{"name": "a-parameter", "quantity": person(11.0)}], "outside its bounds"),
    ([{"name": "a-setting", "quantity": person(3.0, unit="")}], "takes words"),
    ([{"name": "a-setting", "quantity": person("sideways", unit="")}], "takes one of plain, another"),
    ([{"name": "a-parameter", "quantity": person(1.0)}, {"name": "a-parameter", "quantity": person(2.0)}], "set twice"),
])
def test_values_the_parameters_refuse_keep_nothing(engines, inputs, says):
    answer = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder", "inputs": inputs})
    assert answer.status_code == 422 and says in answer.json()["detail"]
    assert runs.listed("sample") == []


def test_a_thing_or_configuration_the_engine_lacks_is_refused_in_words(engines):
    client = TestClient(api.app)
    nosuch = client.post("/api/engines/sample/run", json={"thing": "nosuch"})
    assert nosuch.status_code == 422 and "runs no thing 'nosuch'" in nosuch.json()["detail"]
    wrong = client.post("/api/engines/sample/run", json={"thing": "placeholder-configured", "configuration": "sideways"})
    assert wrong.status_code == 422 and "is none of them" in wrong.json()["detail"]
    none = client.post("/api/engines/sample/run", json={"thing": "placeholder", "configuration": "one way"})
    assert none.status_code == 422 and "takes no configuration" in none.json()["detail"]
    assert client.post("/api/engines/nosuch/run", json={"thing": "x"}).status_code == 404


def test_a_run_the_engine_refuses_is_kept_as_a_receipt_and_answered_from_it(engines, monkeypatch):
    client = TestClient(api.app)
    refused = client.post("/api/engines/sample/run", json={"thing": "refuses", "by": "Ada Moreno"})
    assert refused.status_code == 422 and refused.json()["detail"] == "the sample engine refuses every run of this thing, in these words"
    (receipt,) = runs.listed("sample")
    assert receipt.status == "refused" and receipt.refused == refused.json()["detail"] and receipt.artifactId is None
    monkeypatch.setattr(SAMPLE, "compute", lambda *a, **k: pytest.fail("a receipt is answered without the worker"))
    assert client.post("/api/engines/sample/run", json={"thing": "refuses"}).status_code == 422


def test_a_replay_holds_the_run_to_the_precision_the_thing_states(engines):
    run = SAMPLE.run("placeholder", None, [EngineInput(name="a-parameter", quantity=Quantity(
        value=4.0, unit="placeholder-unit", origin={"kind": "person-assumption", "by": "Ada Moreno", "at": DAY}))],
                     "Ada Moreno")
    replayed = SAMPLE.replay(run)
    assert replayed.identical and replayed.withinTolerance
    assert (replayed.tolerance.rtol, replayed.tolerance.atol) == (0.0, 0.0)
    assert "the precision the sample engine states for placeholder" in replayed.tolerance.why
    assert artifacts.get(run.artifactId).tool == "engine.sample"
    assert SAMPLE.export_sff(run) == run.sffRefused


def test_runs_of_one_engine_are_listed_by_engine(engines):
    client = TestClient(api.app)
    made = client.post("/api/engines/sample/run", json={"thing": "placeholder"}).json()["run"]
    assert [r["id"] for r in client.get("/api/runs", params={"engine": "sample"}).json()] == [made["id"]]
    assert client.get("/api/runs", params={"engine": "biosteam"}).json() == []


def test_a_contract_engines_run_is_kept_by_keep_run_with_its_engines_versions_and_its_job(engines):
    """D3: run_engine keeps its row through keep_run, the one keeper: the
    row's versions are the engine's own (its basis names no simulator), and
    its job is said queued, running and done naming the engine. keep_run
    given the engine's registered name answers that row as first kept, and
    keeps a computation of another basis with the registered engine's
    versions."""
    start = events.newest()
    run = SAMPLE.run("placeholder", None, [given("a-parameter", 2.5)], "Ada Moreno")
    assert run.versions == SAMPLE.version() == {"openferment-core": "0.1.0"}
    sent = [e for e in events.recent(TEST_PROJECT, start) if e.type.startswith("job.")]
    assert [e.type for e in sent] == ["job.queued", "job.running", "job.done"]
    assert {e.data["engine"] for e in sent} == {"sample"} and sent[-1].data["artifactId"] == run.artifactId
    art = artifacts.get(run.artifactId)
    start = events.newest()
    again = runs.keep_run("sample", run.plant, run.configuration, tool=art.tool, version=art.toolVersion,
                          basis=art.inputs, by="Grace Hopper", art=art, sff_refused=run.sffRefused).run
    assert again == run and events.recent(TEST_PROJECT, start) == []
    basis = [i.model_copy(update={"value": 3.5}) if i.name == "value a-parameter" else i for i in art.inputs]
    other = artifacts.compute(art.tool, basis)
    kept = runs.keep_run("sample", run.plant, run.configuration, tool=art.tool, version=art.toolVersion, basis=basis,
                         by="Ada Moreno", art=other, sff_refused=run.sffRefused).run
    assert (kept.id, kept.engine, kept.versions) == (other.id, "sample", SAMPLE.version()) and kept.id != run.id
    assert runs.values_of(art) == run.outputs["values"] and runs.parameters_of(run, art) is None


def test_an_engines_worker_receives_no_key_and_no_database_address(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "OPENFERMENT_API_KEY", "OPENFERMENT_DATABASE_URL", "SCI_RAG_DATABASE_URL",
                 "OPENFERMENT_RAG_KEY", "A_SERVICE_TOKEN"):
        monkeypatch.setenv(name, "a-value-the-worker-must-not-see")
    engine = contract.WorkerEngine(name="sample", worker=SAMPLE.worker)
    seen = engine.call("environment", {})["names"]
    # The four kit settings are the package's own constants, written by the
    # worker's import of openferment_core after it starts (literature/__init__.py).
    received = [n for n in seen if n not in KIT_SETTINGS]
    assert not [n for n in received if withheld(n)] and "PATH" in received
    assert "OPENFERMENT_DATABASE_URL" not in seen and "A_SERVICE_TOKEN" not in seen
    assert withheld("OPENFERMENT_LOCAL_API_KEY") and withheld("anthropic_base_url") and not withheld("OPENFERMENT_PROJECT")


def test_the_engine_tools_take_the_engine(engines):
    ctx = tools.ToolContext(model=llm.DEFAULT_PRIMARY)
    plants = tools.run("engine_plants", {"engine": "sample"}, ctx)
    assert plants.error is None and [p["plant"] for p in plants.summary["plants"]] == ["placeholder",
                                                                                       "placeholder-configured", "refuses"]
    params = tools.run("engine_parameters", {"engine": "sample", "plant": "placeholder"}, ctx)
    assert [p["origin"] for p in params.summary["parameters"]] == ["library-default", "convention"]
    ran = tools.run("engine_run", {"engine": "sample", "plant": "placeholder", "note": "the contract's test"}, ctx)
    assert ran.error is None and ran.summary["provenance"] == "computed" and ran.summary["by"] == llm.DEFAULT_PRIMARY
    assert [e.id for e in ran.evidence] == [f"{ran.summary['artifactId']}:values.count"]
    report = tools.run("engine_report", {"run": ran.summary["runId"]}, ctx)
    assert report.error is None and report.summary["runId"] == ran.summary["runId"], "left out, the run's own"
    wrong = tools.run("engine_report", {"run": ran.summary["runId"], "engine": "biosteam"}, ctx)
    assert "was made by the sample engine" in wrong.error
    assert "the engines are" in tools.run("engine_plants", {"engine": "nosuch"}, ctx).error
    scenario = tools.run("engine_run", {"engine": "sample", "scenario": "sc-1"}, ctx)
    assert "a study scenario runs on BioSTEAM" in scenario.error


def test_the_eight_checks_hold_for_the_sample_and_the_verdict_is_kept_for_the_screens_and_ready(engines):
    found = conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY)
    assert [c.number for c in found] == list(range(1, 9))
    assert all(c.ok for c in found), [(c.number, c.said) for c in found if not c.ok]
    assert conform.CHECKS[7] == "a request the engine refuses is kept as a receipt in its words, with no traceback"
    # Check 7: the worker offered a thing it does not run refuses it; the receipt answers the second ask.
    assert "kept as receipt" in found[6].said
    assert "answered from the receipt with the worker's run op never asked" in found[6].said
    # Check 8: a model's run through the tool door, on another thing in its default configuration.
    assert "a model's run of placeholder-configured (one way) through the engine_run tool" in found[7].said
    assert "created_by 'conformance-model'" in found[7].said
    rows = {c.name: c for c in ready.check_engines()}
    assert rows["engine sample"].mark == "warn" and "never checked here" in rows["engine sample"].detail
    assert rows["engine broken"].mark == "warn" and "runs on without it" in rows["engine broken"].detail
    conform.keep(conform.verdict(SAMPLE, found, "conformance test"))
    held = conform.latest("sample")
    assert held.ok and held.version == SAMPLE_VERSION and held.by == "conformance test"
    assert {c.name: c for c in ready.check_engines()}["engine sample"].mark == "ok"
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
    assert listed["sample"]["conformance"]["ok"] is True


def test_the_checks_run_with_the_values_they_are_given(engines):
    values = [EngineInput(name="a-parameter", quantity=Quantity(value=3.0, unit="placeholder-unit", origin={
        "kind": "person-assumption", "by": "conformance test", "at": DAY, "note": "a placeholder"}))]
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY, inputs=values)}
    assert all(c.ok for c in found.values()), [(n, c.said) for n, c in found.items() if not c.ok]
    assert "with 1 value set" in found[3].said and "its id the artifact id of its basis" in found[3].said
    # With values set, the model's run is the same values as its estimates, dated the day the check runs.
    assert "a model's run (" in found[8].said and "1 value its estimate" in found[8].said
    estimates = [i for r in runs.listed("sample") if r.by == conform.MODEL for i in r.inputs
                 if i.name == "value a-parameter"]
    assert estimates and all(i.quantity.origin.kind == "model-estimate" and i.quantity.origin.at == conform._today()
                             for i in estimates)


def test_the_command_takes_things_and_inputs_and_refuses_anything_else(tmp_path):
    assert conform._options(["--thing", "a", "--thing", "b", "--inputs", "x.json"]) == (["a", "b"], "x.json")
    with pytest.raises(conform.ConformRefused, match="no option here"):
        conform._options(["--things", "a"])
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps([{"name": "a-parameter", "quantity": person(2.0)}]))
    assert [i.name for i in conform._read_inputs(str(path))] == ["a-parameter"]
    path.write_text(json.dumps({"name": "a-parameter"}))
    with pytest.raises(conform.ConformRefused, match="no JSON list"):
        conform._read_inputs(str(path))


def test_a_check_that_fails_says_which_and_why(engines, monkeypatch):
    real = SAMPLE.parameters

    def no_origin(thing, configuration):
        got = real(thing, configuration)
        got[0].origin.ref = " "
        return got

    monkeypatch.setattr(SAMPLE, "parameters", no_origin)
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY)}
    assert not found[2].ok and "lack an origin" in found[2].said
    assert not conform.verdict(SAMPLE, list(found.values()), "t").ok


# ── one checker of the values a run sets (BioSTEAM's door and a contract engine's) ──


def test_one_checker_holds_a_contract_engines_bounds_and_leaves_a_plants_to_the_library():
    p = EngineParameter(key="a-parameter", label="A placeholder", unit="placeholder-unit", value=1.0, min=0, max=10,
                        origin={"kind": "library-default", "ref": "a-package@0.1.0"}, boundsReason="placeholder bounds")
    far = [given("a-parameter", 11.0)]
    with pytest.raises(EngineRefused, match="outside its bounds"):
        runs.check_inputs("a-thing", [p], far, bounds=True)
    runs.check_inputs("a-thing", [p], far, bounds=False)
    for wrong, says in [([given("a-parameter", 1.0, unit="another-unit")], "the parameter's unit is 'placeholder-unit'"),
                        ([given("nosuch", 1.0)], "has no parameter 'nosuch'; of its 1 parameter, the nearest is "
                                                 "a-parameter"),
                        ([given("a-parameter", "words", unit="placeholder-unit")], "takes a number"),
                        ([given("a-parameter", 1.0), given("a-parameter", 2.0)], "set twice")]:
        with pytest.raises(EngineRefused, match=says):
            runs.check_inputs("a-thing", [p], wrong, bounds=False)


@pytest.fixture
def plant_worker(monkeypatch):
    """test_runs' stand-in for the Proforma worker: the library ops (the sugarcane plant's shapes) and the SFF ops."""
    from test_runs import StandIn

    stand_in = StandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def test_biosteam_checks_the_unit_a_value_is_typed_in_before_the_plant_is_built(engines, plant_worker):
    biosteam = registry.get("biosteam")
    typed = given("stream.sugarcane.price", 2.0, unit="placeholder-unit")
    with pytest.raises(EngineRefused, match="set in 'placeholder-unit', and the parameter's unit is 'USD/kg'"):
        biosteam.run("sugarcane", None, [typed], "Ada Moreno")
    answer = TestClient(api.app).post("/api/engines/biosteam/run", json={
        "thing": "sugarcane", "inputs": [typed.model_dump(mode="json", exclude_none=True)], "by": "Ada Moreno"})
    assert answer.status_code == 422 and "the parameter's unit is 'USD/kg'" in answer.json()["detail"]
    assert "library_run" not in plant_worker.calls and runs.listed() == [], "a value refused keeps nothing"


def test_biosteam_keeps_a_value_outside_a_plants_bounds_and_flags_it_on_the_runs_parameters(plant_worker):
    biosteam = registry.get("biosteam")
    run = biosteam.run("sugarcane", None, [given("stream.sugarcane.F_mass", -1.0, unit="kg/hr", note="a placeholder")],
                       "Ada Moreno")
    assert run.status == "done" and run.provenance == "assumed"
    (flow,) = [i for i in run.inputs if i.name == "stream.sugarcane.F_mass"]
    assert (flow.quantity.value, flow.quantity.origin.at) == (-1.0, DAY), "the value as set, on its own day"
    values = {v.key: v for v in runs.report(run.id).parameters.values}
    assert values["stream.sugarcane.F_mass"].value == -1.0
    assert "lies outside its bounds" in values["stream.sugarcane.F_mass"].outOfBounds
    assert values["stream.sugarcane.price"].outOfBounds is None


def test_a_library_run_whose_file_step_fails_says_its_job_failed_and_keeps_no_row(plant_worker, monkeypatch):
    from openferment_core.engine import sff

    def crashed(*a, **k):
        raise WorkerCrashed("the Proforma worker ended while answering 'sff_export'")

    monkeypatch.setattr(sff, "export", crashed)
    start = events.newest()
    with pytest.raises(WorkerCrashed):
        runs.run("sugarcane", by="Ada Moreno")
    *_, failed = events.recent(TEST_PROJECT, start)
    assert (failed.type, failed.data["status"]) == ("job.failed", "failed") and "WorkerCrashed" in failed.data["words"]
    assert runs.listed() == []


# ── discovery that no engine can stop ──────────────────────────────────


class _NameRaises:
    """An engine whose `name` raises when the registry reads it."""

    worker, heavy = None, ()

    @property
    def name(self):
        raise RuntimeError("a declaration that fails when it is read")


NAME_RAISES = _NameRaises()


def test_an_engine_whose_declaration_raises_is_listed_with_its_words_and_the_rest_load(monkeypatch):
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("raises", "tests.test_engines:NAME_RAISES"),
                                                                  ("sample", SAMPLE_ENTRY)))
    registry.reset()
    try:
        found = registry.found()
        assert found["raises"].engine is None
        assert found["raises"].error == ("tests.test_engines:NAME_RAISES could not be checked: RuntimeError: a "
                                         "declaration that fails when it is read")
        assert found["sample"].engine is SAMPLE
    finally:
        registry.reset()


def test_an_entry_module_that_exits_as_it_is_imported_is_listed_and_the_rest_load(monkeypatch, tmp_path):
    (tmp_path / "an_exiting_engine.py").write_text("raise SystemExit(3)\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("exits", "an_exiting_engine:ENGINE"),
                                                                  ("sample", SAMPLE_ENTRY)))
    registry.reset()
    try:
        found = registry.found()
        assert found["exits"].error == "an_exiting_engine:ENGINE could not be loaded: SystemExit: 3"
        assert found["sample"].engine is SAMPLE
        listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
        assert listed["exits"]["error"] == found["exits"].error and listed["sample"]["error"] is None
    finally:
        registry.reset()
        sys.modules.pop("an_exiting_engine", None)


def test_an_entry_module_that_asks_the_registry_as_it_is_imported_is_answered_with_nothing(tmp_path):
    """In a process of its own, so a registry that deadlocked would fail the test by its timeout."""
    (tmp_path / "a_curious_engine.py").write_text(
        "from openferment_core.engine import registry\n"
        "SEEN = (registry.found(), registry.names(), registry.set_aside())\n"
        "from openferment_core.engine.sample import SAMPLE as ENGINE\n")
    probe = ("import json, sys\n"
             f"sys.path.insert(0, {str(tmp_path)!r})\n"
             "from importlib.metadata import EntryPoint\n"
             "from openferment_core.engine import registry\n"
             "registry.entry_points = lambda: [EntryPoint(name='sample', value='a_curious_engine:ENGINE', "
             "group=registry.GROUP)]\n"
             "found = registry.found()\n"
             "import a_curious_engine\n"
             "print(json.dumps({'seen': a_curious_engine.SEEN, 'error': found['sample'].error, "
             "'loaded': found['sample'].engine is a_curious_engine.ENGINE, 'again': registry.names()}))\n")
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, cwd=ROOT / "core", timeout=120)
    assert done.returncode == 0, done.stderr[-600:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {"seen": [{}, [], []], "error": None, "loaded": True,
                                                                "again": ["sample"]}


def test_the_service_starts_when_the_group_itself_cannot_be_read(monkeypatch, caplog):
    def unreadable():
        raise OSError("the distributions' metadata could not be read")

    monkeypatch.setattr(registry, "entry_points", unreadable)
    registry.reset()
    try:
        with caplog.at_level("WARNING", logger="openferment.api"):
            api._discover_engines()
        assert ("the engines of openferment.engines could not be read at startup: OSError: the distributions' "
                "metadata could not be read") in caplog.text
    finally:
        registry.reset()


def test_an_entry_module_that_imports_its_worker_or_a_heavy_module_is_set_aside(monkeypatch, tmp_path):
    pkg = tmp_path / "a_heavy_engine"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "worker.py").write_text("")
    (tmp_path / "a_fake_heavy_module.py").write_text("WEIGHT = 'a placeholder'\n")
    (pkg / "engine.py").write_text(
        "import a_fake_heavy_module  # noqa: F401\n"
        "from openferment_core.engine.contract import WorkerEngine\n"
        "ENGINE = WorkerEngine(name='weighty', worker='a_heavy_engine.worker', heavy=('a_fake_heavy_module',))\n")
    (pkg / "eager.py").write_text(
        "from . import worker  # noqa: F401\n"
        "from openferment_core.engine.contract import WorkerEngine\n"
        "ENGINE = WorkerEngine(name='eager', worker='a_heavy_engine.worker')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(
        ("weighty", "a_heavy_engine.engine:ENGINE"), ("eager", "a_heavy_engine.eager:ENGINE"), ("sample", SAMPLE_ENTRY)))
    registry.reset()
    try:
        found = registry.found()
        assert found["weighty"].engine is None and found["weighty"].error == (
            "importing a_heavy_engine.engine:ENGINE imported a_fake_heavy_module, which belong in its worker")
        assert found["eager"].engine is None and found["eager"].error == (
            "importing a_heavy_engine.eager:ENGINE imported a_heavy_engine.worker, which belong in its worker")
        assert found["sample"].engine is SAMPLE
        assert "engine.weighty" not in artifacts._REGISTRY and "engine.eager" not in artifacts._REGISTRY
    finally:
        registry.reset()
        for m in [m for m in sys.modules if m == "a_fake_heavy_module" or m.split(".")[0] == "a_heavy_engine"]:
            del sys.modules[m]


# ── a worker that answers outside the protocol ─────────────────────────


@pytest.mark.parametrize(("answer", "says"), [
    ({}, "answered no 'outputs'"),
    ({"outputs": {"name": "count"}}, "answered outputs that are no list"),
    ({"outputs": [{"name": "count", "value": True, "unit": "1"}]}, "an output that is no name, value and unit"),
    ({"outputs": [{"name": "count", "value": 1.0}]}, "an output that is no name, value and unit"),
    ({"outputs": [{"name": "count", "value": 1.0, "unit": "1"}, {"name": "count", "value": 2.0, "unit": "1"}]},
     "two outputs named 'count'"),
    ({"outputs": [{"name": " ", "value": 1.0, "unit": "1"}]}, "blank or longer than 200 characters"),
    ({"outputs": [{"name": "n" * 201, "value": 1.0, "unit": "1"}]}, "blank or longer than 200 characters"),
    ({"outputs": [{"name": "count", "value": float("nan"), "unit": "1"}]}, "an output whose number is NaN or infinite"),
    ({"outputs": [{"name": "count", "value": float("inf"), "unit": "1"}]}, "an output whose number is NaN or infinite"),
    ({"outputs": [{"name": "count", "value": float("-inf"), "unit": "1"}]}, "an output whose number is NaN or infinite"),
])
def test_a_worker_that_answers_outside_the_protocol_is_broken_and_keeps_nothing(engines, monkeypatch, answer, says):
    real = SAMPLE.call
    monkeypatch.setattr(SAMPLE, "call", lambda op, args, *, timeout_s=None: answer if op == "run"
                        else real(op, args, timeout_s=timeout_s))
    with pytest.raises(EngineBroken, match=re.escape(says)) as broken:
        SAMPLE.compute("placeholder", None, [])
    assert not isinstance(broken.value, EngineRefused)
    client = TestClient(api.app)
    start = events.newest()
    route = client.post("/api/engines/sample/run", json={"thing": "placeholder"})
    assert route.status_code == 503 and says in route.json()["detail"]
    *_, failed = events.recent(TEST_PROJECT, start)
    assert (failed.type, failed.data["status"]) == ("job.failed", "failed") and "EngineBroken" in failed.data["words"]
    tool = tools.run("engine_run", {"engine": "sample", "plant": "placeholder"}, tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert "the sample engine broke its contract, and no run was kept" in tool.error and says in tool.error
    assert runs.listed("sample") == [], "no receipt: the next ask computes afresh"
    monkeypatch.setattr(SAMPLE, "call", real)
    mended = client.post("/api/engines/sample/run", json={"thing": "placeholder"})
    assert mended.status_code == 200 and mended.json()["run"]["status"] == "done"


def test_a_worker_whose_things_or_file_answer_outside_the_protocol_is_broken(engines, monkeypatch):
    engine = contract.WorkerEngine(name="sample", worker=SAMPLE.worker)
    answers = {"things": {"things": [{"id": "placeholder"}]}, "parameters": {"parameters": "none"},
               "sff_export": {"flowsheet": ["not", "an", "object"]}}
    monkeypatch.setattr(engine, "call", lambda op, args, *, timeout_s=None: answers[op])
    with pytest.raises(EngineBroken, match="answered things outside their shape"):
        engine.things()
    with pytest.raises(EngineBroken, match="answered parameters that are no list"):
        engine.parameters("placeholder", None)
    with pytest.raises(EngineBroken, match="a flowsheet that is no JSON object"):
        engine.sff_document("placeholder", None, [])


def test_a_worker_that_fails_writing_the_file_says_the_job_failed_and_keeps_no_row(engines, monkeypatch):
    def crashed(*a, **k):
        raise WorkerCrashed("the sample worker ended while answering 'sff_export'")

    monkeypatch.setattr(SAMPLE, "sff_document", crashed)
    start = events.newest()
    answer = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder"})
    assert answer.status_code == 503 and "ended while answering 'sff_export'" in answer.json()["detail"]
    sent = events.recent(TEST_PROJECT, start)
    assert [e.type for e in sent][:2] == ["job.queued", "job.running"] and sent[-1].type == "job.failed"
    assert "WorkerCrashed" in sent[-1].data["words"] and runs.listed("sample") == []


class _Forgetful:
    """A hand-written engine whose own run keeps no row."""

    name, worker, heavy = "forgetful", None, ()

    def version(self):
        return {"openferment-core": "0.1.0"}

    def things(self):
        return [EngineThing(id="placeholder", title="A placeholder thing", precision={"rtol": 0, "atol": 0})]

    def parameters(self, thing, configuration):
        return []

    def run(self, thing, configuration, inputs, by):
        return EngineRun(id="0123456789abcdef", engine=self.name, plant=thing, status="done", tool="engine.forgetful",
                         toolVersion="v", inputs=[], by=by, at=f"{DAY}T00:00:00Z")

    def replay(self, run):
        raise EngineRefused("nothing to replay")

    def export_sff(self, run):
        return "it has no plant"


FORGETFUL = _Forgetful()


def test_an_engine_whose_own_run_keeps_no_row_is_broken(monkeypatch):
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("forgetful", "tests.test_engines:FORGETFUL")))
    registry.reset()
    try:
        with pytest.raises(EngineBroken, match="the forgetful engine kept no row for its run"):
            runs.run_with(FORGETFUL, "placeholder", None, [], by="Ada Moreno")
        answer = TestClient(api.app).post("/api/engines/forgetful/run", json={"thing": "placeholder"})
        assert answer.status_code == 503 and answer.json()["detail"] == "the forgetful engine kept no row for its run"
    finally:
        registry.reset()


# ── the listing never waits long on a worker ───────────────────────────


class _Sim:
    """A stand-in SimWorker: every op it is asked and the timeout it was given."""

    def __init__(self, module, *, timeout_s, withhold_secrets):
        self.module, self.alive, self.asked = module, True, []

    def call(self, op, args, *, timeout_s=None):
        self.asked.append((op, timeout_s))
        return {"things": [{"id": "placeholder", "title": "A placeholder thing", "precision": {"rtol": 0, "atol": 0}}]}


def test_a_worker_engines_things_are_asked_once_and_a_cold_worker_is_given_a_short_wait(monkeypatch):
    monkeypatch.setattr(contract, "SimWorker", _Sim)
    engine = contract.WorkerEngine(name="sample", worker=SAMPLE.worker, distributions=("openferment-core",))
    monkeypatch.setattr(registry, "found", lambda: {"sample": registry.Found("sample", SAMPLE_ENTRY, engine)})
    monkeypatch.setattr(conform, "latest", lambda name: None)
    first, again = registry.info("sample"), registry.info("sample")
    assert [t.id for t in first.things] == [t.id for t in again.things] == ["placeholder"] and first.error is None
    assert registry.LISTING_TIMEOUT_S == 30.0 and engine._sim.asked == [("things", 30.0)]
    assert [t.id for t in engine.things()] == ["placeholder"] and engine._sim.asked == [("things", 30.0)], (
        "kept for the life of the process")


def test_a_listing_whose_worker_times_out_lists_the_engine_with_the_words(monkeypatch):
    engine = contract.WorkerEngine(name="sample", worker=SAMPLE.worker, distributions=("openferment-core",))

    def silent(op, args, *, timeout_s=None):
        raise WorkerTimeout(f"{engine.worker} gave no answer to {op!r} in {timeout_s:g} s; it was stopped and the next "
                            "call starts it again")

    monkeypatch.setattr(engine, "call", silent)
    monkeypatch.setattr(registry, "found", lambda: {"sample": registry.Found("sample", SAMPLE_ENTRY, engine)})
    monkeypatch.setattr(conform, "latest", lambda name: None)
    listed = registry.info("sample")
    assert listed.things == [] and listed.version == {"openferment-core": "0.1.0"}
    assert listed.error.startswith("its things could not be listed: WorkerTimeout:") and "in 30 s" in listed.error
    assert engine._things is None, "a failure is kept nowhere, so the next listing asks again"


# ── conformance: a refusal kept as a receipt, a configuration named, the model's door ──


def test_check_7_fails_a_worker_that_computes_a_thing_it_does_not_run(engines, monkeypatch):
    real = SAMPLE.call

    def lenient(op, args, *, timeout_s=None):
        if op == "run" and args.get("thing") == conform.NO_SUCH_THING:
            return {"outputs": [{"name": "count", "value": 0, "unit": "1"}]}
        return real(op, args, timeout_s=timeout_s)

    monkeypatch.setattr(SAMPLE, "call", lenient)
    own = set(vars(SAMPLE))
    ok, words = conform._refused_unknown(SAMPLE, "conformance test")
    assert not ok and "computed 'conform-no-such-thing'" in words
    assert set(vars(SAMPLE)) == own and conform.NO_SUCH_THING not in [t.id for t in SAMPLE.things()], "the spies are gone"


def test_check_7_fails_when_the_same_request_reaches_the_worker_again(engines, monkeypatch):
    """A service that keyed the request anew each time would ask the worker twice: the receipt answers nothing."""
    fresh = iter(f"{n:016x}" for n in range(1, 99))
    monkeypatch.setattr(artifacts, "artifact_id", lambda *a, **k: next(fresh))
    ok, words = conform._refused_unknown(SAMPLE, "conformance test")
    assert not ok and "kept as receipt" in words and "with the worker's run op asked 1 more time" in words


def test_check_7_holds_an_engine_without_compute_to_a_refusal_in_words_that_keeps_nothing(engines):
    ok, words = conform._refused_unknown(registry.get("biosteam"), "conformance test")
    assert ok and "the shelf has no conform-no-such-thing" in words and "0 run kept" in words


def test_a_thing_that_must_name_a_configuration_is_checked_in_its_first_and_refused_with_none(engines, monkeypatch):
    real = SAMPLE.things

    def undefaulted(*a, **k):
        return [t.model_copy(update={"defaultConfiguration": None}) if t.id == "placeholder-configured" else t
                for t in real(*a, **k)]

    monkeypatch.setattr(SAMPLE, "things", undefaulted)
    none = TestClient(api.app).post("/api/engines/sample/run", json={"thing": "placeholder-configured"})
    assert none.status_code == 422
    assert none.json()["detail"] == ("placeholder-configured is run in one of its configurations, named in the request: "
                                     "one way, another way")
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY,
                                                 things=["placeholder-configured"])}
    assert all(c.ok for c in found.values()), [(n, c.said) for n, c in found.items() if not c.ok]
    ran = {(r.by, r.configuration) for r in runs.listed("sample")}
    assert ("conformance test", "one way") in ran and (conform.MODEL, "another way") in ran
    assert "a model's run of placeholder-configured (another way) through the engine_run tool" in found[8].said


def test_a_write_tool_at_the_http_door_names_who_calls_it(engines):
    client = TestClient(api.app)
    nobody = client.post("/api/tools/engine_run", json={"engine": "sample", "plant": "placeholder"})
    assert nobody.status_code == 422 and "this call names nobody" in nobody.json()["detail"]
    assert runs.listed("sample") == []
    named = client.post("/api/tools/engine_run", params={"by": "Ada Moreno"}, json={"engine": "sample", "plant": "placeholder"})
    assert named.status_code == 200 and named.json()["error"] is None
    run_id = named.json()["summary"]["runId"]
    assert conform._created_by(run_id) == "Ada Moreno" and runs.get(run_id).by == "Ada Moreno"
    read = client.post("/api/tools/engine_plants", json={"engine": "sample"})
    assert read.status_code == 200 and read.json()["error"] is None, "a read that names nobody runs as it did"


def test_every_contract_runs_tool_version_carries_the_contracts_stem():
    assert contract.version_string(SAMPLE) == SAMPLE_VERSION
    assert SAMPLE_VERSION.startswith(contract.CONTRACT_RUN + " · ")


def test_the_engine_routes_declare_what_they_answer_in_words():
    doc = api.app.openapi()
    for path, method in (("/api/engines/{name}/parameters", "get"), ("/api/engines/{name}/run", "post")):
        responses = doc["paths"][path][method]["responses"]
        assert {"200", "404", "422", "503"} <= set(responses), (path, sorted(responses))
        assert all(responses[c]["description"].strip() for c in ("404", "422", "503"))
        assert responses["503"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/Refusal"}
    assert doc["components"]["schemas"]["Refusal"]["properties"]["detail"]["type"] == "string"
    written = json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))
    assert written["paths"]["/api/engines/{name}/run"]["post"]["responses"].keys() >= {"404", "422", "503"}


# ── the review of B.6: one rule at every door, every module kept out ────


def _asked(monkeypatch, engine=SAMPLE):
    """The worker ops the engine asks, each with its args, the worker answering as it does."""
    real, calls = engine.call, []

    def spy(op, args, *, timeout_s=None):
        calls.append((op, dict(args)))
        return real(op, args, timeout_s=timeout_s)

    monkeypatch.setattr(engine, "call", spy)
    return calls


def test_the_parameters_door_resolves_the_configuration_as_a_run_does(engines, monkeypatch):
    calls = _asked(monkeypatch)
    client = TestClient(api.app)
    params = client.get("/api/engines/sample/parameters", params={"thing": "placeholder-configured"})
    assert params.status_code == 200 and [p["key"] for p in params.json()] == ["a-parameter", "a-setting"]
    assert ("parameters", {"thing": "placeholder-configured", "configuration": "one way"}) in calls, calls
    for asked, says in [({"thing": "placeholder-configured", "configuration": "sideways"}, "is none of them"),
                        ({"thing": "placeholder", "configuration": "one way"}, "takes no configuration"),
                        ({"thing": "nosuch"}, "runs no thing 'nosuch'")]:
        answer = client.get("/api/engines/sample/parameters", params=asked)
        assert answer.status_code == 422 and says in answer.json()["detail"], (asked, answer.text)
    assert [c for c in calls if c[0] == "parameters"] == [
        ("parameters", {"thing": "placeholder-configured", "configuration": "one way"})], "a refusal asks no worker"
    ctx = tools.ToolContext(model=llm.DEFAULT_PRIMARY)
    read = tools.run("engine_parameters", {"engine": "sample", "plant": "placeholder-configured"}, ctx)
    assert read.error is None and read.summary["configuration"] == "one way"
    wrong = tools.run("engine_parameters", {"engine": "sample", "plant": "placeholder", "configuration": "one way"}, ctx)
    assert "takes no configuration" in wrong.error


def test_a_thing_with_no_default_configuration_is_read_with_one_named(engines, monkeypatch):
    real = SAMPLE.things
    monkeypatch.setattr(SAMPLE, "things", lambda *a, **k: [
        t.model_copy(update={"defaultConfiguration": None}) if t.id == "placeholder-configured" else t
        for t in real(*a, **k)])
    answer = TestClient(api.app).get("/api/engines/sample/parameters", params={"thing": "placeholder-configured"})
    assert answer.status_code == 422 and "is run in one of its configurations, named in the request" in answer.text


LONG = "a placeholder configuration whose name runs past forty characters"


def test_a_configuration_name_the_thing_allows_passes_every_door(engines, monkeypatch):
    assert 40 < len(LONG) <= CONFIGURATION_MAX
    real = SAMPLE.things
    monkeypatch.setattr(SAMPLE, "things", lambda *a, **k: [
        t.model_copy(update={"configurations": ["one way", LONG]}) if t.id == "placeholder-configured" else t
        for t in real(*a, **k)])
    ctx = tools.ToolContext(model=llm.DEFAULT_PRIMARY)
    route = TestClient(api.app).post("/api/engines/sample/run",
                                     json={"thing": "placeholder-configured", "configuration": LONG})
    assert route.status_code == 200 and route.json()["run"]["configuration"] == LONG
    params = tools.run("engine_parameters", {"engine": "sample", "plant": "placeholder-configured",
                                             "configuration": LONG}, ctx)
    assert params.error is None and params.summary["configuration"] == LONG
    ran = tools.run("engine_run", {"engine": "sample", "plant": "placeholder-configured", "configuration": LONG}, ctx)
    assert ran.error is None and ran.summary["configuration"] == LONG and ran.summary["runId"] == route.json()["run"]["id"]
    too_long = "c" * (CONFIGURATION_MAX + 1)
    with pytest.raises(ValidationError, match=f"at most {CONFIGURATION_MAX} characters"):
        EngineThing(id="a-thing", title="A thing", configurations=[too_long], precision={"rtol": 0, "atol": 0})
    refused = tools.run("engine_run", {"engine": "sample", "plant": "placeholder-configured", "configuration": too_long},
                        ctx)
    assert f"at most {CONFIGURATION_MAX} characters" in refused.error


@pytest.mark.parametrize(("extra", "says"), [
    ({"low": 1.0, "high": 3.0}, "also carries low and high"),
    ({"basis": "a placeholder basis"}, "also carries basis"),
])
def test_a_contract_engines_value_carries_its_value_and_unit_alone(engines, monkeypatch, extra, says):
    calls = _asked(monkeypatch)
    answer = TestClient(api.app).post("/api/engines/sample/run", json={
        "thing": "placeholder", "inputs": [{"name": "a-parameter", "quantity": person(2.5) | extra}]})
    assert answer.status_code == 422 and says in answer.json()["detail"]
    assert runs.listed("sample") == [] and not [c for c in calls if c[0] in ("parameters", "run")]


def test_biosteam_refuses_a_value_that_carries_a_basis_before_the_plant_is_built(engines, plant_worker):
    biosteam = registry.get("biosteam")
    typed = EngineInput.model_validate({"name": "stream.sugarcane.price", "quantity": person(
        2.0, unit="USD/kg") | {"basis": "a placeholder basis"}})
    with pytest.raises(EngineRefused, match="also carries the basis 'a placeholder basis'"):
        biosteam.run("sugarcane", None, [typed], "Ada Moreno")
    assert not [c for c in plant_worker.calls if c in ("library_parameters", "library_run")] and runs.listed() == []


def test_a_key_biosteam_lacks_is_named_with_the_few_nearest(engines, plant_worker):
    biosteam = registry.get("biosteam")
    with pytest.raises(EngineRefused) as refused:
        biosteam.run("sugarcane", None, [given("stream.sugarcane.prise", 2.0, unit="USD/kg")], "Ada Moreno")
    said = str(refused.value)
    count = len(biosteam.parameters("sugarcane", None))
    assert said.startswith(f"sugarcane has no parameter 'stream.sugarcane.prise'; of its {count} parameters, the nearest")
    assert "stream.sugarcane.price" in said and said.count(",") <= runs.NEAREST_KEYS


def test_a_replay_names_the_version_a_run_was_kept_at_when_the_engine_moved(engines, monkeypatch):
    run = SAMPLE.run("placeholder", None, [], "Ada Moreno")
    monkeypatch.setattr(SAMPLE, "version", lambda: {"openferment-core": "0.1.1"})
    replayed = TestClient(api.app).post(f"/api/biorepo/artifacts/{run.artifactId}/replay").json()
    assert replayed["identical"] and replayed["withinTolerance"]
    assert replayed["differences"] == [{"path": "toolVersion", "stored": SAMPLE_VERSION,
                                        "replayed": "engine run 1 · sample · openferment-core 0.1.1"}]


def test_conformance_checks_the_things_in_the_order_named_and_refuses_one_it_lacks(engines):
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test",
                                                 things=["placeholder-configured", "placeholder"])}
    assert " of placeholder-configured" in found[3].said and found[3].ok, found[3].said
    assert "a model's run of placeholder through the engine_run tool" in found[8].said, found[8].said
    with pytest.raises(conform.ConformRefused, match="the sample engine runs no 'nosuch'; it runs placeholder"):
        conform.checks(SAMPLE, by="conformance test", things=["placeholder", "nosuch"])


def test_check_7_fails_when_its_first_ask_never_reaches_the_worker(engines):
    """The same request asked in one project a second time is answered from the
    receipt the first check kept: its first ask reaches no worker, and the
    check says so."""
    ok, words = conform._refused_unknown(SAMPLE, "conformance test")
    assert ok, words
    ok, words = conform._refused_unknown(SAMPLE, "conformance test")
    assert not ok and "the first ask reached its worker's run op 0 times" in words


def test_an_entry_point_name_past_forty_characters_is_said_so(monkeypatch):
    name = "an-engine-whose-name-runs-past-forty-characters"
    monkeypatch.setattr(registry, "entry_points", lambda: _points((name, SAMPLE_ENTRY)))
    registry.reset()
    try:
        assert registry.found()[name].error == (f"the entry point's name {name!r} is longer than an engine name's 40 "
                                                "characters")
    finally:
        registry.reset()


class _OwnThings(contract.WorkerEngine):
    """A WorkerEngine whose things are its own, by the Engine protocol's signature."""

    def things(self):
        return [EngineThing(id="placeholder", title="A placeholder thing", precision={"rtol": 0, "atol": 0})]


def test_the_listing_reads_a_subclass_that_defines_its_own_things(monkeypatch):
    engine = _OwnThings(name="sample", worker=SAMPLE.worker, distributions=("openferment-core",))
    monkeypatch.setattr(registry, "found", lambda: {"sample": registry.Found("sample", SAMPLE_ENTRY, engine)})
    monkeypatch.setattr(conform, "latest", lambda name: None)
    listed = registry.info("sample")
    assert listed.error is None and [t.id for t in listed.things] == ["placeholder"]


def _write_package(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def _forget(*tops: str) -> None:
    for m in [m for m in sys.modules if m.split(".")[0] in tops]:
        del sys.modules[m]


def test_a_dotted_heavy_name_covers_its_module_at_discovery_and_in_check_6(monkeypatch, tmp_path):
    _write_package(tmp_path, {
        "a_dotted_heavy/__init__.py": "",
        "a_dotted_heavy/core.py": "WEIGHT = 'a placeholder'\n",
        "a_dotted_engine/__init__.py": "",
        "a_dotted_engine/worker.py": "",
        "a_dotted_engine/engine.py": (
            "import a_dotted_heavy.core  # noqa: F401\n"
            "from openferment_core.engine.contract import WorkerEngine\n"
            "ENGINE = WorkerEngine(name='dotted', worker='a_dotted_engine.worker', heavy=('a_dotted_heavy.core',))\n")})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("dotted", "a_dotted_engine.engine:ENGINE")))
    registry.reset()
    try:
        assert registry.found()["dotted"].error == (
            "importing a_dotted_engine.engine:ENGINE imported a_dotted_heavy.core, which belong in its worker")
        assert "a_dotted_heavy.core" not in sys.modules, "taken out, so the next engine is measured afresh"
        engine = contract.WorkerEngine(name="dotted", worker="a_dotted_engine.worker", heavy=("a_dotted_heavy.core",))
        ok, words = conform._imports_alone("a_dotted_engine.engine", engine)
        assert not ok and words == "importing a_dotted_engine.engine imported a_dotted_heavy.core"
    finally:
        registry.reset()
        _forget("a_dotted_heavy", "a_dotted_engine")


def test_two_engines_that_import_one_heavy_module_are_both_set_aside(monkeypatch, tmp_path):
    engine = ("import a_shared_heavy  # noqa: F401\n"
              "from openferment_core.engine.contract import WorkerEngine\n"
              "ENGINE = WorkerEngine(name='{name}', worker='{name}_pkg.worker', heavy=('a_shared_heavy',))\n")
    _write_package(tmp_path, {"a_shared_heavy.py": "WEIGHT = 'a placeholder'\n",
                              **{f"{n}_pkg/{f}": t for n in ("one", "two") for f, t in (
                                  ("__init__.py", ""), ("worker.py", ""), ("engine.py", engine.format(name=n)))}})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("one", "one_pkg.engine:ENGINE"),
                                                                  ("two", "two_pkg.engine:ENGINE")))
    registry.reset()
    try:
        found = registry.found()
        for n in ("one", "two"):
            assert found[n].engine is None and found[n].error == (
                f"importing {n}_pkg.engine:ENGINE imported a_shared_heavy, which belong in its worker")
        assert "a_shared_heavy" not in sys.modules
    finally:
        registry.reset()
        _forget("a_shared_heavy", "one_pkg", "two_pkg")


def test_an_engine_that_declares_nothing_heavy_still_keeps_the_worker_libraries_out(monkeypatch, tmp_path):
    """workers.WORKER_LIBRARIES stay out of the service's process for every
    engine; a stand-in `pisces_sff` (the vendored toolkit, importable in its
    worker alone) is the one imported here."""
    from openferment_core.workers import WORKER_LIBRARIES

    assert "pisces_sff" in WORKER_LIBRARIES and "pisces_sff" not in sys.modules
    _write_package(tmp_path, {
        "pisces_sff/__init__.py": "WEIGHT = 'a stand-in'\n",
        "an_undeclaring_engine/__init__.py": "",
        "an_undeclaring_engine/worker.py": "",
        "an_undeclaring_engine/engine.py": (
            "import pisces_sff  # noqa: F401\n"
            "from openferment_core.engine.contract import WorkerEngine\n"
            "ENGINE = WorkerEngine(name='undeclaring', worker='an_undeclaring_engine.worker', heavy=())\n")})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(registry, "entry_points", lambda: _points(
        ("undeclaring", "an_undeclaring_engine.engine:ENGINE"), ("sample", SAMPLE_ENTRY)))
    registry.reset()
    try:
        found = registry.found()
        assert found["undeclaring"].error == (
            "importing an_undeclaring_engine.engine:ENGINE imported pisces_sff, which belong in its worker")
        assert found["sample"].engine is SAMPLE and "pisces_sff" not in sys.modules
        engine = contract.WorkerEngine(name="undeclaring", worker="an_undeclaring_engine.worker", heavy=())
        ok, words = conform._imports_alone("an_undeclaring_engine.engine", engine)
        assert not ok and words == "importing an_undeclaring_engine.engine imported pisces_sff"
    finally:
        registry.reset()
        _forget("pisces_sff", "an_undeclaring_engine")


def test_a_thread_an_entry_module_starts_and_waits_on_is_answered_and_discovery_ends(tmp_path):
    """In a process of its own, so a registry that kept the thread waiting would fail the test by its timeout."""
    (tmp_path / "a_threaded_engine.py").write_text(
        "import threading\n"
        "from openferment_core.engine import registry\n"
        "SEEN = []\n"
        "t = threading.Thread(target=lambda: SEEN.append(registry.names()))\n"
        "t.start()\n"
        "t.join(60)\n"
        "WAITED = t.is_alive()\n"
        "from openferment_core.engine.sample import SAMPLE as ENGINE\n")
    probe = ("import json, sys, time\n"
             f"sys.path.insert(0, {str(tmp_path)!r})\n"
             "from importlib.metadata import EntryPoint\n"
             "from openferment_core.engine import registry\n"
             "registry.DISCOVERY_WAIT_S = 0.5\n"
             "registry.entry_points = lambda: [EntryPoint(name='sample', value='a_threaded_engine:ENGINE', "
             "group=registry.GROUP)]\n"
             "started = time.monotonic()\n"
             "found = registry.found()\n"
             "took = time.monotonic() - started\n"
             "import a_threaded_engine as m\n"
             "print(json.dumps({'seen': m.SEEN, 'waited': m.WAITED, 'loaded': found['sample'].error is None, "
             "'quick': took < 30}))\n")
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, cwd=ROOT / "core", timeout=120)
    assert done.returncode == 0, done.stderr[-600:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {"seen": [[]], "waited": False, "loaded": True,
                                                                "quick": True}


def test_the_routes_declare_the_refusals_they_answer_and_a_quantity_is_typed_both_ways(engines):
    doc = api.app.openapi()
    paths, schemas = doc["paths"], doc["components"]["schemas"]
    refusal = {"$ref": "#/components/schemas/Refusal"}
    report = paths["/api/runs/{run_id}"]["get"]["responses"]
    replay = paths["/api/biorepo/artifacts/{artifact_id}/replay"]["post"]["responses"]
    tool = paths["/api/tools/{name}"]["post"]["responses"]
    assert report["404"]["content"]["application/json"]["schema"] == refusal
    assert {"404", "409"} <= set(replay) and replay["409"]["content"]["application/json"]["schema"] == refusal
    assert tool["404"]["content"]["application/json"]["schema"] == refusal
    assert refusal in tool["422"]["content"]["application/json"]["schema"]["anyOf"]
    # A run's input quantity reads with its own fields, as it is written.
    assert "Quantity-Output" not in schemas
    assert set(schemas["Quantity"]["properties"]) == {"value", "unit", "basis", "low", "high", "origin"}
    client = TestClient(api.app)
    assert client.get("/api/runs/0000000000000000").status_code == 404
    assert client.post("/api/biorepo/artifacts/0000000000000000/replay").status_code == 404
    assert client.post("/api/tools/nosuch", json={}).status_code == 404


# ── a parameter with no default (alpha 2.2 D4; docs/api/engines.md) ─────


def test_a_parameter_with_no_default_has_value_and_origin_null_and_says_a_run_sets_it():
    p = EngineParameter(key="a-parameter", label="A placeholder", unit="placeholder-unit", value=None, origin=None,
                        boundsReason="none stated")
    assert p.sourceRule == ["assumption"], "a parameter with no default is one a run's value sets"
    for bad, says in [({"value": 1.0}, "a default carries its origin"),
                      ({"origin": {"kind": "library-default", "ref": "a-package@0.1.0"}}, "a default carries its origin")]:
        with pytest.raises(ValidationError, match=says):
            EngineParameter(**{**p.model_dump(exclude={"sourceRule"}), **bad})
    words = EngineParameter(key="a-setting", label="A placeholder", unit="", value=None, origin=None,
                            choices=["one", "another"], boundsReason="a setting chosen from its words")
    assert words.value is None and words.choices == ["one", "another"]


def test_a_value_is_a_number_or_words_as_its_parameter_is_declared():
    def declared(**fields):
        base = {"key": "a-parameter", "label": "A placeholder", "unit": "placeholder-unit", "boundsReason": "none"}
        if fields.get("value") is not None:
            base["origin"] = {"kind": "convention", "note": "a placeholder setting"}
        return EngineParameter(**{"value": None, "origin": None, **base, **fields})

    assert runs.takes_number(declared(value=1.5)) and runs.takes_number(declared())
    # A convention's words in a unit (a term left off) take a number; words in no unit take words.
    assert runs.takes_number(declared(value="off"))
    assert not runs.takes_number(declared(value="words", unit=""))
    assert not runs.takes_number(declared(choices=["one", "another"], unit=""))
    runs.check_inputs("a-thing", [declared(value="off")], [given("a-parameter", 2.0)], bounds=False)
    with pytest.raises(EngineRefused, match="takes a number"):
        runs.check_inputs("a-thing", [declared()], [given("a-parameter", "words")], bounds=False)


def test_a_contract_engines_parameter_with_no_default_waits_for_the_run_to_set_it(engines, monkeypatch):
    real = SAMPLE.parameters

    def no_default(thing, configuration):
        return [p.model_copy(update={"value": None, "origin": None, "sourceRule": ["assumption"]})
                if p.key == "a-parameter" else p for p in real(thing, configuration)]

    monkeypatch.setattr(SAMPLE, "parameters", no_default)
    computed = []
    monkeypatch.setattr(SAMPLE, "compute", lambda *a, **k: computed.append(a) or [])
    client = TestClient(api.app)
    waits = client.post("/api/engines/sample/run", json={"thing": "placeholder", "by": "Ada Moreno"})
    assert waits.status_code == 422, waits.text
    assert "placeholder cannot run yet: 1 parameter waits for the run to set it, having no default: a-parameter" in \
        waits.json()["detail"]
    assert runs.listed("sample") == [] and computed == [], "a run that leaves it unset keeps nothing and reaches no worker"
    set_here = client.post("/api/engines/sample/run", json={
        "thing": "placeholder", "by": "Ada Moreno", "inputs": [{"name": "a-parameter", "quantity": person(2.5)}]})
    assert set_here.status_code == 200 and len(computed) == 1
    # Check 2 holds a parameter with no default that a run sets, and names one that says nothing of who sets it.
    held, said = conform._origins(SAMPLE, [t for t in SAMPLE.things() if t.id == "placeholder"])
    assert held and "1 a run sets" in said
    monkeypatch.setattr(SAMPLE, "parameters", lambda thing, configuration: [
        p.model_copy(update={"sourceRule": ["library-default"]}) for p in no_default(thing, configuration)])
    held, said = conform._origins(SAMPLE, [t for t in SAMPLE.things() if t.id == "placeholder"])
    assert not held and "placeholder:a-parameter" in said


# ── the kinetics engine (alpha 2.2 D4; fermos_engine.py, ADR-015) ───────
#
# Every value a kinetics run sets here is test_fermos' and test_vessel's own
# STAND-IN, typed as those tests type it, or conformance's placeholder.

from openferment_core import evidence_pool, fermos, fermos_engine, intake, kinetics, proforma, vessel  # noqa: E402
from openferment_core.models import VesselRequest  # noqa: E402
from standins import as_inputs  # noqa: E402

KINETICS_ENTRY = "openferment_core.fermos_engine:ENGINE"
KINETICS = fermos_engine.ENGINE
FAMILIES = ["batch_v1", "fedbatch_v1", "chemostat_v1"]


@pytest.fixture
def kinetics_engines(monkeypatch, tmp_path):
    """A registry of BioSTEAM and the kinetics engine, as core/pyproject.toml
    registers them, over a project whose evidence pool holds no record (as
    test_fermos' `store` holds it): each value is the one the test types."""
    from types import SimpleNamespace

    monkeypatch.setattr(registry, "entry_points", lambda: _points(("biosteam", BIOSTEAM_ENTRY),
                                                                  ("kinetics", KINETICS_ENTRY)))
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: SimpleNamespace(records=[], records_by_id={}))
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    registry.reset()
    yield KINETICS
    registry.reset()


def _typed(family="batch_v1"):
    """test_fermos' STAND-IN values for a family, as the inputs a request sends."""
    from test_fermos import STANDIN_CHEMOSTAT_TYPED, STANDIN_TYPED, inputs_for

    return inputs_for(family, **(STANDIN_CHEMOSTAT_TYPED if family == "chemostat_v1" else STANDIN_TYPED))


def _sent(inputs) -> list[dict]:
    return [i.model_dump(mode="json", exclude_none=True) for i in inputs]


def test_the_service_registers_kinetics_through_its_own_entry_point():
    registry.reset()
    try:
        found = registry.found()["kinetics"]
        assert (found.entry, found.engine, found.error) == (KINETICS_ENTRY, KINETICS, None)
        assert (KINETICS.worker, KINETICS.heavy) == (None, ())
        rows = {r.name.removeprefix("engine "): r for r in ready.check_engines()}
        # pnpm ready names the worker a vessel design runs in, and a conform command that can pass: its file of values.
        said = rows["kinetics"].detail
        assert "no worker: it computes in the service's process; a vessel design runs in the Proforma worker" in said
        assert ("python -m openferment_core.engine.conform kinetics --inputs <file>, the file "
                "openferment_core.fermos_engine.write_placeholder_inputs(<file>, by=<your name>) writes") in said
        assert ready.conform_command("biosteam") == "python -m openferment_core.engine.conform biosteam"
    finally:
        registry.reset()


def test_get_api_engines_lists_kinetics_with_the_families_that_simulate_and_no_worker(kinetics_engines):
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
    k = listed["kinetics"]
    assert (k["entryPoint"], k["error"], k["worker"], k["workerStatus"], k["heavy"]) == (
        KINETICS_ENTRY, None, None, "none", [])
    assert k["version"] == {**kinetics.versions(), "biosteam": library._installed("biosteam"),
                            "thermosteam": library._installed("thermosteam")}
    # light_v1 is a socket, and the contract has no kinetics socket; a project holding no fit and no
    # simulation lists no forecast and no vessel.
    assert [(t["id"], t["configurations"], t["defaultConfiguration"], t["precision"]) for t in k["things"]] == [
        (f, [], None, {"rtol": 0.0, "atol": 0.0}) for f in FAMILIES]


def test_a_familys_parameters_keep_each_convention_and_leave_the_rest_to_the_run(kinetics_engines):
    got = {p["key"]: p for p in TestClient(api.app).get("/api/engines/kinetics/parameters",
                                                        params={"thing": "batch_v1"}).json()}
    specs = {s.key: s for s in kinetics.family("batch_v1").specs()}
    assert list(got) == list(specs)
    for key, spec in specs.items():
        p = got[key]
        if spec.convention is not None and "convention" in spec.sourceRule:
            assert (p["value"], p["origin"]["kind"]) == (spec.convention, "convention") and p["origin"]["note"], key
        else:
            assert p["value"] is None and p["origin"] is None and "assumption" in p["sourceRule"], key
    assert got["mu_max"]["unit"] == specs["mu_max"].unit and got["ki_substrate"]["value"] == "off"
    read = tools.run("engine_parameters", {"engine": "kinetics", "plant": "batch_v1", "words": "mu_max"},
                     tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert read.error is None and read.summary["parameters"][0]["origin"] is None


def test_a_run_of_a_family_is_one_row_at_every_door_and_the_same_request_twice_is_that_row(kinetics_engines):
    client = TestClient(api.app)
    asked = {"thing": "batch_v1", "by": "Ada Moreno", "inputs": _sent(_typed())}
    first = client.post("/api/engines/kinetics/run", json=asked)
    assert first.status_code == 200, first.text
    run = first.json()["run"]
    assert (run["engine"], run["plant"], run["configuration"], run["tool"], run["status"], run["provenance"],
            run["by"]) == ("kinetics", "batch_v1", None, fermos.SIMULATION, "done", "assumed", "Ada Moreno")
    assert run["sffRefused"] == fermos_engine.SFF_WORDS["family"] and run["sff"] is None
    # A family's simulation runs on numpy and scipy alone: its row names those, and BioSTEAM stays the vessel's.
    assert run["versions"] == kinetics.versions()
    names = [v["name"] for v in run["outputs"]["values"]]
    assert names == ["end.X", "end.S", "end.P", "end.t", "harvestH", "sugarRunsOutH"]
    assert all(v["quantity"]["origin"] == {"kind": "artifact", "ref": run["artifactId"]} for v in run["outputs"]["values"])
    assert client.post("/api/engines/kinetics/run", json=asked).json()["run"] == run
    # fermOS's own route and its tool make the same run: one row, its first asker kept.
    simulated = client.post("/api/fermos/simulate", json={"family": "batch_v1", "inputs": _sent(_typed()),
                                                          "by": "Grace Hopper"})
    assert simulated.status_code == 200 and simulated.json()["artifactId"] == run["artifactId"]
    assert [(r.id, r.by) for r in runs.listed("kinetics")] == [(run["id"], "Ada Moreno")]
    report = client.get(f"/api/runs/{run['id']}").json()
    assert report["artifact"]["tool"] == fermos.SIMULATION and report["parameters"] is None
    # The engine tools read it as any engine's run: each output an evidence id on its artifact.
    read = tools.run("engine_report", {"run": run["id"]}, tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert read.error is None and [e.id for e in read.evidence] == [f"{run['artifactId']}:values.{n}" for n in names]
    replayed = KINETICS.replay(runs.get(run["id"]))
    assert replayed.identical and KINETICS.export_sff(runs.get(run["id"])) == fermos_engine.SFF_WORDS["family"]


def test_a_kinetics_run_that_leaves_a_parameter_waiting_is_refused_in_words_and_keeps_nothing(kinetics_engines):
    client = TestClient(api.app)
    waits = client.post("/api/engines/kinetics/run", json={"thing": "batch_v1", "by": "Ada Moreno"})
    assert waits.status_code == 422 and "batch_v1 cannot run yet" in waits.json()["detail"], waits.text
    (mu,) = [i for i in _sent(_typed()) if i["name"] == "mu_max"]
    for inputs, says in [([mu | {"quantity": mu["quantity"] | {"unit": "placeholder-unit"}}],
                          "mu_max is set in 'placeholder-unit', and the parameter's unit is 'h⁻¹'"),
                         ([mu | {"name": "mu_maks"}], "batch_v1 has no parameter 'mu_maks'; of its 18 parameters"),
                         ([mu, mu], "mu_max is set twice")]:
        answer = client.post("/api/engines/kinetics/run", json={"thing": "batch_v1", "inputs": inputs})
        assert answer.status_code == 422 and says in answer.json()["detail"], (says, answer.text)
    assert "the kinetics engine runs no thing 'light_v1'" in client.post(
        "/api/engines/kinetics/run", json={"thing": "light_v1"}).json()["detail"]
    assert runs.listed("kinetics") == [] and artifacts.all_artifacts() == []


def test_a_refusal_inside_the_integration_is_kept_as_a_receipt_and_answered_from_it(kinetics_engines, monkeypatch):
    integrated = []

    def refuses(inputs):
        integrated.append(len(inputs))
        raise fermos.SimulationRefused("the integration stopped, in the placeholder's words")

    monkeypatch.setattr(fermos, "_trajectory", refuses)
    with pytest.raises(runs.RunRefused, match="in the placeholder's words") as refused:
        KINETICS.run("batch_v1", None, _typed(), "Ada Moreno")
    receipt = runs.get(refused.value.run_id)
    assert (receipt.engine, receipt.status, receipt.artifactId, receipt.by) == ("kinetics", "refused", None, "Ada Moreno")
    assert receipt.refused == "the integration stopped, in the placeholder's words" and receipt.sffRefused is None
    again = TestClient(api.app).post("/api/fermos/simulate", json={"family": "batch_v1", "inputs": _sent(_typed())})
    assert again.status_code == 422 and "in the placeholder's words" in again.json()["detail"]
    assert len(integrated) == 1, "the same request is answered from its receipt, integrating nothing"
    assert runs.listed("kinetics") == [receipt]


def test_a_forecast_and_a_vessel_are_things_while_the_project_holds_what_they_take(kinetics_engines):
    from test_fermos import SD, T, batch

    fit = fermos.fit("dep-f", batch(T, np.random.default_rng(4), SD))
    things = {t.id: t for t in KINETICS.things()}
    assert things["forecast"].configurations == [fit.kineticArtifactId] and things["forecast"].defaultConfiguration is None
    # A logistic fit designs the anaerobic vessel, so it is a configuration of the vessel too.
    assert things["vessel"].configurations == [fit.kineticArtifactId]
    params_ = {p.key: p for p in KINETICS.parameters("forecast", fit.kineticArtifactId)}
    assert set(params_) == {"x0", "s0", "p0", "t_end"} and all(p.value is None for p in params_.values())
    with pytest.raises(EngineRefused, match="forecast is run in one of its configurations, named in the request"):
        KINETICS.run("forecast", None, [], "Ada Moreno")
    run = KINETICS.run("forecast", fit.kineticArtifactId, [], "Ada Moreno")
    assert (run.plant, run.configuration, run.tool, run.status, run.provenance, run.by) == (
        "forecast", fit.kineticArtifactId, fermos.FORECAST, "done", "computed", "Ada Moreno")
    finals = {v["name"]: v["quantity"] for v in run.outputs["values"]}
    assert list(finals) == ["finals.biomass", "finals.product", "finals.substrate"]
    assert all(q["low"] <= q["value"] <= q["high"] for q in finals.values())
    kept = TestClient(api.app).post("/api/fermos/forecast", json={"fitArtifactId": fit.kineticArtifactId,
                                                                  "by": "Grace Hopper"}).json()
    assert kept["artifactId"] == run.artifactId and [r.id for r in runs.listed("kinetics")] == [run.id]
    assert KINETICS.replay(run).identical and run.versions == kinetics.versions()
    # GET /api/engines lists them in the request's project, read afresh: the fit, and the forecast made of it.
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}["kinetics"]
    served = {t["id"]: t["configurations"] for t in listed["things"]}
    assert served["forecast"] == [fit.kineticArtifactId]
    assert set(served["vessel"]) == {fit.kineticArtifactId, run.artifactId}


def test_a_run_reads_only_the_artifact_its_configuration_names(kinetics_engines, monkeypatch):
    """A family is fermOS's own, and a forecast's configuration is the one
    fit it names: a run of either reads no listing of the project's
    artifacts. A configuration the thing cannot take is refused in the
    listing's words, naming what the project holds."""
    from test_fermos import SD, T, batch

    fit = fermos.fit("dep-f", batch(T, np.random.default_rng(4), SD))

    def listed():
        raise AssertionError("a run read the project's listing")

    monkeypatch.setattr(fermos_engine, "_kept", listed)
    ran = KINETICS.run("forecast", fit.kineticArtifactId, [], "Ada Moreno")
    assert (ran.plant, ran.configuration, ran.status) == ("forecast", fit.kineticArtifactId, "done")
    assert [p.key for p in KINETICS.parameters("batch_v1", None)] == [s.key for s in kinetics.family("batch_v1").specs()]
    with pytest.raises(EngineRefused, match="batch_v1 takes no configuration, and 'a-placeholder' was named"):
        KINETICS.run("batch_v1", "a-placeholder", [], "Ada Moreno")
    monkeypatch.setattr(fermos_engine, "_kept", lambda: ([fit.kineticArtifactId], [fit.kineticArtifactId]))
    with pytest.raises(EngineRefused, match=f"forecast runs in {fit.kineticArtifactId}; '0000000000000000' is none"):
        KINETICS.run("forecast", "0000000000000000", [], "Ada Moreno")


def test_a_vessel_design_is_a_run_of_its_simulation_and_the_same_request_twice_is_that_row(kinetics_engines,
                                                                                         monkeypatch):
    from test_vessel import AEROBIC_ID, StandInWorker, keep, override, standin_simulation

    keep(AEROBIC_ID, standin_simulation(True))
    monkeypatch.setattr(proforma, "call", StandInWorker())
    monkeypatch.setattr(vessel, "_SPECS", {})
    things = {t.id: t for t in KINETICS.things()}
    assert things["vessel"].configurations == [AEROBIC_ID] and "forecast" not in things
    params_ = {p.key: p for p in KINETICS.parameters("vessel", AEROBIC_ID)}
    assert params_["plant_scale"].value is None and params_["plant_scale"].origin is None
    assert (params_["oxygen_basis"].value, params_["oxygen_basis"].origin.kind) == ("peak", "convention")
    assert (params_["V_wf"].origin.kind, params_["V_wf"].origin.ref) == ("library-default", "biosteam@0.0-standin")
    assert params_["tau"].value is None, "the simulation's harvest hour, bound when the design runs"
    with pytest.raises(EngineRefused, match="needs plant_scale"):
        KINETICS.run("vessel", AEROBIC_ID, [], "Ada Moreno")
    assert runs.listed("kinetics") == []
    scale = as_inputs([override(AEROBIC_ID, "plant_scale", 1000.0)], vessel.UNITS)
    run = KINETICS.run("vessel", AEROBIC_ID, scale, "Ada Moreno")
    assert (run.plant, run.configuration, run.tool, run.status, run.provenance) == (
        "vessel", AEROBIC_ID, vessel.TOOL, "done", "assumed")
    assert run.outputs["values"] == [{"name": "design.Vessels", "quantity": {
        "value": 2.0, "unit": "", "origin": {"kind": "artifact", "ref": run.artifactId}}}]
    again = vessel.design(VesselRequest(simulation=AEROBIC_ID, inputs=scale, by="Grace Hopper"))
    assert again.artifactId == run.artifactId and [(r.id, r.by) for r in runs.listed("kinetics")] == [
        (run.id, "Ada Moreno")]
    # A design's row names what the design ran on: its tool version's BioSTEAM and its chemicals' package.
    named = dict(part.split(" ", 1) for part in vessel.version().split(" · ")[1:])
    chemicals = next(i for i in artifacts.get(run.artifactId).inputs if i.name == "chemicals")
    assert run.versions == {**named, "biorefineries": chemicals.source.id.split("@", 1)[1]}
    assert set(run.versions) == {"biosteam", "thermosteam", "biorefineries"}


def test_a_vessels_refusals_name_the_keys_its_own_scope_lists(kinetics_engines, monkeypatch):
    """An anaerobic design's scope lists its own keys: a key it lacks, an
    aerobic design's batch volume among them, is refused naming those, and
    a design with no scale asks for the plant scale alone."""
    from test_vessel import ANAEROBIC_ID, StandInWorker, keep, override, standin_simulation

    keep(ANAEROBIC_ID, standin_simulation(False))
    monkeypatch.setattr(proforma, "call", StandInWorker())
    monkeypatch.setattr(vessel, "_SPECS", {})
    listed = [p.key for p in KINETICS.parameters("vessel", ANAEROBIC_ID)]
    assert "batch_volume" not in listed
    for key in ("plant_scal", "batch_volume"):
        stray = as_inputs([override(ANAEROBIC_ID, key, 1000.0)], vessel.UNITS)
        with pytest.raises(EngineRefused, match=f"there is no parameter {key} here; the parameters are "
                                                f"{', '.join(listed)}$"):
            KINETICS.run("vessel", ANAEROBIC_ID, stray, "Ada Moreno")
    with pytest.raises(EngineRefused) as none:
        KINETICS.run("vessel", ANAEROBIC_ID, [], "Ada Moreno")
    assert str(none.value) == ("a vessel design needs plant_scale (tonnes of product a year), a named person's "
                               "assumption; none was given")
    assert runs.listed("kinetics") == []


def test_a_worker_a_kinetics_thing_calls_that_cannot_answer_is_a_503_naming_it(kinetics_engines, monkeypatch):
    from openferment_core.workers import WorkerCrashed
    from test_vessel import AEROBIC_ID, keep, standin_simulation

    keep(AEROBIC_ID, standin_simulation(True))

    def crashed(op, payload):
        raise WorkerCrashed(f"openferment_core.workers.proforma_worker ended while answering {op!r}", "")

    monkeypatch.setattr(proforma, "call", crashed)
    monkeypatch.setattr(vessel, "_SPECS", {})
    r = TestClient(api.app).get("/api/engines/kinetics/parameters", params={"thing": "vessel",
                                                                          "configuration": AEROBIC_ID})
    assert r.status_code == 503, r.text
    assert r.json()["detail"] == ("the kinetics engine computes in the service's process, and the worker its "
                                  "computation called could not answer: openferment_core.workers.proforma_worker "
                                  "ended while answering 'vessel_specs'")
    assert runs.listed("kinetics") == []


def test_conformance_holds_all_eight_on_kinetics_with_the_placeholders_it_is_given(kinetics_engines, tmp_path):
    path = fermos_engine.write_placeholder_inputs(tmp_path / "inputs.json", by="conformance test")
    values = conform._read_inputs(str(path))
    assert {i.name: i.quantity.value for i in values} == {"mu_max": 1.0, "ks": 1.0, "yxs": 1.0, "alpha": 1.0,
                                                          "yps": 1.0, "p_max": 1.0, "x0": 1.0, "s0": 1.0, "p0": 0.0}
    assert {(i.quantity.origin.kind, i.quantity.origin.by, i.quantity.origin.at) for i in values} == {
        ("person-assumption", "conformance test", conform._today())}
    found = conform.checks(KINETICS, by="conformance test", entry=KINETICS_ENTRY, inputs=values)
    assert [c.number for c in found] == list(range(1, 9))
    assert all(c.ok for c in found), [(c.number, c.said) for c in found if not c.ok]
    unset = sum(1 for f in FAMILIES for s in kinetics.family(f).specs()
                if s.convention is None or "convention" not in s.sourceRule)
    assert f"{unset} a run sets" in found[1].said and "with 9 values set" in found[2].said
    # Check 6: an engine with no worker holds the worker libraries out of the service's process.
    assert "imported none of biorefineries, biosteam, cobra, pisces_sff, thermosteam" in found[5].said
    # Every family's placeholders compute.
    for family in FAMILIES[1:]:
        ran = KINETICS.run(family, None, fermos_engine.placeholder_inputs(family, by="conformance test"),
                           "conformance test")
        assert ran.status == "done", (family, ran.refused)


def test_the_conform_command_holds_all_eight_on_kinetics_on_a_scratch_database(kinetics_engines, test_database,
                                                                              monkeypatch, tmp_path, capsys):
    path = fermos_engine.write_placeholder_inputs(tmp_path / "inputs.json", by="conformance test")
    monkeypatch.setenv("OPENFERMENT_DATABASE_URL", test_database.server.render_as_string(hide_password=False))
    assert conform.main(["kinetics", "--inputs", str(path)]) == 0, capsys.readouterr().out
    printed = capsys.readouterr().out
    assert printed.count("✓") == 8 and "every check holds" in printed
    held = conform.latest("kinetics")
    assert held.ok and held.version == contract.version_string(KINETICS)
