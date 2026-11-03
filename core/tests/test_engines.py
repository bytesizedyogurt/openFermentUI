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
Stage C (D5): the train engine registered by the core's own entry point, its
things the project's trains read afresh, its parameters each with the origin
its resolution names, a run one row at every door, a value that waits keeping
nothing and the worker's refusal a receipt, the eight checks holding on each
train of a copy of a project (`--project`), and the command without one
refused in words naming it. Stage C.3b (D5's amendment): the checks read a
project and check a copy of it on a database of their own, so the project
holds the same rows, byte for byte, after them, beside the verdict, and a
person's earlier run of a train changes nothing; a draft and a train that
waits are listed as such and left out, numbered, a project with no train that
can run is refused in words saying the ways on, and the command runs with the
configured address naming the production database, every engine held off a
database of that name, its verdict the one row written; the verdict kept
gives counts and names no project, train or run; the copy holds every row a
train's resolution reads; the checks' database is dropped when SIGTERM ends
the command and when a rollback cannot close; and `pnpm ready` says why a
failed engine fails and why no command checks an engine that names nothing
its things rest on.
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
    # A thing the project holds rests a default on its records, an artifact or a person's typed value, each named.
    for origin, rule in (({"kind": "record", "ref": "a-record"}, ["record:a-field"]),
                         ({"kind": "artifact", "ref": "0" * 16}, ["artifact"]),
                         ({"kind": "person-assumption", "by": "Ada Moreno", "at": DAY}, ["assumption"])):
        held = EngineParameter(**{**p.model_dump(exclude={"sourceRule"}), "origin": origin,
                                  **({"sourceRule": rule} if origin["kind"] == "record" else {})})
        assert held.sourceRule == rule and conform._names_its_ground(held.origin)
    for bad, says in [
        ({"origin": {"kind": "model-estimate", "by": "a-model"}}, "names the origin model-estimate"),
        ({"origin": {"kind": "record", "ref": "a-record"}}, "names the field it binds from"),
        ({"origin": {"kind": "record"}, "sourceRule": ["record:a-field"]}, "names what it was read from"),
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


def test_the_command_takes_things_inputs_and_a_project_and_refuses_anything_else(tmp_path):
    assert conform._options(["--thing", "a", "--thing", "b", "--inputs", "x.json"]) == (["a", "b"], "x.json", None)
    assert conform._options(["--project", "a-project"]) == ([], None, "a-project")
    with pytest.raises(conform.ConformRefused, match="unknown option --things: the options are --thing <id>"):
        conform._options(["--things", "a"])
    # An option with no value says what it takes, whether it ends the line or another option follows it.
    for argv, says in ((["--project"], "--project needs a project's id"), (["--thing", "--project", "p"],
                                                                         "--thing needs a thing's id"),
                       (["--inputs"], "--inputs needs a file")):
        with pytest.raises(conform.ConformRefused) as refused:
            conform._options(argv)
        assert conform._words(refused.value) == says
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
    assert ok and "the biosteam engine runs no thing 'conform-no-such-thing'" in words and "0 run kept" in words


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
    assert held and "1 with none, taking a run's value" in said
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
    assert f"{unset} with none, each taking a run's value" in found[1].said and "with 9 values set" in found[2].said
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


# ── the train engine (alpha 2.2 D5; pureos/engine.py, ADR-015) ──────────
#
# Every train here is test_train's STAND-IN (`spec_of`), run on its
# TrainWorker with no record pool, as test_train runs it; a record a value
# binds from is test_pureos_build_tool's STAND-IN.

from openferment_core import db  # noqa: E402
from openferment_core.pureos import engine as train_engine  # noqa: E402
from openferment_core.pureos import kept as kept_trains  # noqa: E402
from openferment_core.pureos import train_spec  # noqa: E402
from test_train import AT as TRAIN_AT  # noqa: E402
from test_train import BY as TRAIN_BY  # noqa: E402
from test_train import VERSIONS as TRAIN_VERSIONS  # noqa: E402
from test_train import TrainWorker, spec_of, typed  # noqa: E402

TRAIN_ENTRY = "openferment_core.pureos.engine:ENGINE"
TRAIN = train_engine.ENGINE
# The project's evidence pool as pureOS reads it, before `train_engines` hands in none.
PROJECT_POOL = train_spec._pool


@pytest.fixture
def train_engines(monkeypatch, tmp_path):
    """A registry of BioSTEAM and the train engine, as core/pyproject.toml
    registers them, over test_train's stand-in worker and no record pool."""
    from openferment_core.pureos import catalogue

    monkeypatch.setattr(registry, "entry_points", lambda: _points(("biosteam", BIOSTEAM_ENTRY),
                                                                  ("train", TRAIN_ENTRY)))
    w = TrainWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_UNITS", {})
    monkeypatch.setattr(train_spec, "_pool", lambda: None)
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    registry.reset()
    yield w
    registry.reset()


def _saved(spec, by="Ada Moreno"):
    """A train saved as pureOS's Builder saves it: the project's row (PUT /api/state/trains/<id>)."""
    r = TestClient(api.app).put(f"/api/state/trains/{spec.id}", json={"by": by, "value": {
        "train": spec.model_dump(mode="json"), "savedAt": f"{DAY}T00:00:00Z", "by": by}})
    assert r.status_code == 200, r.text


def test_the_service_registers_train_through_its_own_entry_point():
    registry.reset()
    try:
        found = registry.found()["train"]
        assert (found.entry, found.engine, found.error) == (TRAIN_ENTRY, TRAIN, None)
        biosteam = registry.get("biosteam")
        assert (TRAIN.worker, TRAIN.heavy) == (biosteam.worker, biosteam.heavy)
        assert TRAIN.version() == {**biosteam.version(), "train run": train_spec.VERSION_WORDS.rsplit(" ", 1)[1]}
        assert ready.conform_command("train") == ("python -m openferment_core.engine.conform train --project <id>, "
                                                  "naming a project of this database that holds one of its things "
                                                  f"({TRAIN.things_are}); the checks run on a copy of it")
        assert ready.things_are("biosteam") is None and ready.conform_command("biosteam") == (
            "python -m openferment_core.engine.conform biosteam")
    finally:
        registry.reset()


def test_the_conform_command_reads_the_production_database_and_writes_there_its_verdict_alone(train_engines,
                                                                                                test_database,
                                                                                                monkeypatch, capsys):
    """The live host's database is the production one (`openferment`). With
    the configured address naming the production database, `pnpm ready`
    names the command as it names it on any database; the command reads the
    project and checks a copy of it on a database of its own, and the one row
    it writes where it read is its verdict. Every session here reaches the
    test's own database through its binding, and every engine the command
    makes is held off a database named `openferment`, so a path that made an
    engine of its own from the configured address fails here before it
    reaches a server's real database of that name."""
    import importlib

    # The module that makes every engine (db.make_engine), which `openferment_core.db.engine` names as a function.
    db_engine = importlib.import_module("openferment_core.db.engine")
    made, reached = db_engine.create_async_engine, []

    def held_off(url, *args, **kwargs):
        if getattr(url, "database", None) == db.PRODUCTION_NAME:
            reached.append(url.render_as_string(hide_password=True))
            raise AssertionError(f"an engine was made for the production database: {reached[-1]}")
        return made(url, *args, **kwargs)

    _saved(spec_of())
    server = test_database.server.render_as_string(hide_password=False)
    monkeypatch.setattr(db_engine, "create_async_engine", held_off)
    monkeypatch.setenv("OPENFERMENT_DATABASE_URL", server.rsplit("/", 1)[0] + "/" + db.PRODUCTION_NAME)
    rows = {c.name: c for c in ready.check_engines()}
    assert rows["engine train"].mark == "warn" and rows["engine train"].detail.endswith(
        f"never checked here: {ready.conform_command('train')}")
    before = _every_row()
    assert conform.main(["train", "--project", TEST_PROJECT]) == 0, capsys.readouterr().out
    printed = capsys.readouterr().out
    assert printed.count("✓") == 8 and "every check holds" in printed
    after = _every_row()
    assert _changed(before, after) == ["openferment.engine_checks"]
    assert len(after["openferment.engine_checks"]) == 1 and conform.latest("train").ok
    rows = {c.name: c for c in ready.check_engines()}
    assert rows["engine train"].mark == "ok" and "every conformance check held" in rows["engine train"].detail
    assert reached == []


def test_get_api_engines_lists_train_with_the_projects_trains_read_afresh(train_engines):
    client = TestClient(api.app)
    listed = {e["name"]: e for e in client.get("/api/engines").json()}
    t = listed["train"]
    assert (t["entryPoint"], t["error"], t["worker"], t["things"], t["thingsAre"]) == (
        TRAIN_ENTRY, None, "openferment_core.workers.proforma_worker", [], TRAIN.things_are)
    assert listed["biosteam"]["thingsAre"] is None
    _saved(spec_of())
    kept_trains.keep_train(None, lambda _: spec_of(id="k-1", name="A model's train"), "a-model")
    t = {e["name"]: e for e in client.get("/api/engines").json()}["train"]
    # A train run keeps every digit BioSTEAM gives, so it replays exactly.
    exact = {"rtol": 0.0, "atol": 0.0}
    assert [(x["id"], x["title"], x["kind"], x["configurations"], x["defaultConfiguration"], x["precision"])
            for x in t["things"]] == [
        ("t1", "A test train", "made", [], None, exact),
        ("k-1", "A model's train, built by a-model", "kept", [], None, exact)]


def test_a_trains_parameters_are_each_places_values_with_the_origins_their_resolution_names(train_engines,
                                                                                         monkeypatch):
    from test_pureos_build_tool import stand_in_pool

    monkeypatch.setattr(train_spec, "_pool", stand_in_pool)
    _saved(spec_of())
    got = {p.key: p for p in TRAIN.parameters("t1", None)}
    keys = list(got)
    assert keys[0].startswith("inlet.") and keys.index("C1.split.Yeast") < keys.index("F1.V")
    typed = got["inlet.broth_flow"]
    assert (typed.value, typed.origin.kind, typed.origin.by, typed.origin.at) == (1.0, "person-assumption",
                                                                                    TRAIN_BY, TRAIN_AT)
    assert (got["inlet.T"].origin.kind, got["inlet.T"].origin.ref) == ("library-default", "thermosteam@0.0-standin")
    assert got["F1.vessel_material"].origin.kind == "library-default"
    # The records that bound a value name it; a value nothing gives has none, and a run sets it.
    bound = got["C1.split.Ethanol"]
    assert bound.origin.kind == "record" and bound.origin.ref == "r-st-1, r-st-2"
    assert got["C1.moisture_content"].origin.kind == "record" and got["C1.moisture_content"].origin.ref == "r-cm-1"
    # A value the train fills itself when a run leaves it unset says so in its note, with the resolution's reason:
    # a component the typed inlet does not carry, a value the class decides at run time.
    absent, decided = got["inlet.conc.Octane"], got["F1.T"]
    assert (absent.value, absent.origin, decided.value, decided.origin) == (None, None, None, None)
    assert absent.note.endswith(f"{train_engine.FILLS_ITSELF} (absent from the inlet: a component nobody typed is not "
                                "in it).")
    assert f"{train_engine.FILLS_ITSELF} (" in decided.note and "the class decides at run time" in decided.note
    assert not [p.key for p in got.values() if p.value is not None and train_engine.FILLS_ITSELF in (p.note or "")]
    held, said = conform._origins(TRAIN, TRAIN.things())
    assert held, said
    served = TestClient(api.app).get("/api/engines/train/parameters", params={"thing": "t1"}).json()
    assert [p["key"] for p in served] == keys
    with pytest.raises(EngineRefused, match="t1 takes no configuration, and 'a-placeholder' was named"):
        TRAIN.parameters("t1", "a-placeholder")


def test_a_trains_run_is_one_row_at_every_door_and_the_same_request_twice_is_that_row(train_engines):
    _saved(spec_of())
    client = TestClient(api.app)
    first = client.post("/api/engines/train/run", json={"thing": "t1", "by": "Ada Moreno"})
    assert first.status_code == 200, first.text
    run = first.json()["run"]
    assert (run["engine"], run["plant"], run["configuration"], run["tool"], run["status"], run["provenance"],
            run["by"]) == ("train", "t1", None, train_spec.TRAIN_RUN, "done", "assumed", "Ada Moreno")
    assert run["versions"] == TRAIN_VERSIONS and run["sff"]["recordId"] == f"run-{run['id']}"
    assert client.post("/api/engines/train/run", json={"thing": "t1", "by": "Grace Hopper"}).json()["run"] == run
    # pureOS's own route and its tool make the same run: one row, its first asker kept.
    again = client.post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json"), "by": "Grace Hopper"})
    assert again.status_code == 200 and again.json()["artifactId"] == run["artifactId"]
    assert [(r.id, r.by) for r in runs.listed("train")] == [(run["id"], "Ada Moreno")]
    # A value set at the engine's door is converted at pureOS's: another basis, another row.
    asked = {"thing": "t1", "by": "Ada Moreno", "inputs": [{"name": "F1.V", "quantity": person(0.2, unit="")}]}
    changed = client.post("/api/engines/train/run", json=asked)
    assert changed.status_code == 200, changed.text
    set_here = next(i["quantity"] for i in changed.json()["run"]["inputs"] if i["name"] == "F1.V")
    assert (set_here["value"], set_here["origin"]["by"], set_here["origin"]["at"]) == (0.2, "Ada Moreno", DAY)
    assert len(runs.listed("train")) == 2
    # The engine tools read it as any engine's run.
    read = tools.run("engine_report", {"engine": "train", "run": run["id"]}, tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert read.error is None and f"{run['artifactId']}:values.overallRecovery" in [e.id for e in read.evidence]
    held = runs.get(run["id"])
    assert TRAIN.replay(held).identical and TRAIN.export_sff(held).id == f"run-{run['id']}"


def test_a_train_that_waits_is_refused_with_nothing_kept_and_the_workers_refusal_is_a_receipt(train_engines,
                                                                                              monkeypatch):
    _saved(spec_of(units=[{"id": "D1", "type": "distillation"}]))
    _saved(spec_of(id="t2", name="Another test train"))
    client = TestClient(api.app)
    waits = client.post("/api/engines/train/run", json={"thing": "t1", "by": "Ada Moreno"})
    assert waits.status_code == 422 and "unit D1 (distillation): light_key waits" in waits.json()["detail"]
    stray = client.post("/api/engines/train/run", json={"thing": "t2", "inputs": [
        {"name": "F1.Vee", "quantity": person(0.2, unit="")}]})
    assert stray.status_code == 422 and "unit F1 (flash) has no parameter 'Vee'; its parameters are" in (
        stray.json()["detail"])
    # The engine's door refuses as pureOS's does: every refusal at once, a bad input beside a value that waits.
    both = client.post("/api/engines/train/run", json={"thing": "t1", "inputs": [
        {"name": "D1.Vee", "quantity": person(0.2, unit="")}]}).json()["detail"]
    assert both.startswith("unit D1 (distillation) has no parameter 'Vee'") and "D1 (distillation): light_key waits" in both
    assert "the train engine runs no thing 'nosuch'; it runs t1, t2" in client.post(
        "/api/engines/train/run", json={"thing": "nosuch"}).json()["detail"]
    assert runs.listed("train") == []
    refusing = TrainWorker(fail="Refused: unit F1 (flash, Flash) did not converge: BioSTEAM said: STAND-IN")
    monkeypatch.setattr(proforma, "call", refusing)
    refused = client.post("/api/engines/train/run", json={"thing": "t2", "by": "Ada Moreno"})
    assert refused.status_code == 422 and "did not converge" in refused.json()["detail"]
    (receipt,) = runs.listed("train")
    assert (receipt.status, receipt.artifactId, receipt.plant, receipt.by) == ("refused", None, "t2", "Ada Moreno")
    asked = len([c for c in refusing.calls if c[0] == "train_run"])
    assert client.post("/api/engines/train/run", json={"thing": "t2"}).status_code == 422
    assert len([c for c in refusing.calls if c[0] == "train_run"]) == asked, "answered from the receipt"


def test_conformance_holds_all_eight_on_train_in_the_project_that_holds_its_train(train_engines):
    _saved(spec_of())
    found = conform.checks(TRAIN, by="conformance test", entry=TRAIN_ENTRY)
    assert [c.number for c in found] == list(range(1, 9))
    assert all(c.ok for c in found), [(c.number, c.said) for c in found if not c.ok]
    assert "record run-" in found[4].said and "valid, score 0.5" in found[4].said
    assert "imported none of the worker openferment_core.workers.proforma_worker" in found[5].said
    assert "the train engine runs no thing 'conform-no-such-thing'" in found[6].said
    # The model's run sets the first parameter a run may set, at its own default, as its estimate.
    assert "a model's run (" in found[7].said and "1 value its estimate" in found[7].said
    assert [r.by for r in runs.listed("train")] == [conform.MODEL, "conformance test"]


def test_the_conform_command_checks_train_in_a_named_project_and_refuses_without_one(train_engines, test_database,
                                                                                    monkeypatch, capsys):
    _saved(spec_of())
    server = test_database.server.render_as_string(hide_password=False)
    monkeypatch.setenv("OPENFERMENT_DATABASE_URL", server)
    assert conform.main(["train"]) == 2
    said = capsys.readouterr().out
    assert f"the train engine's things are {TRAIN.things_are}. A database made for the checks holds none" in said
    assert "--project <id>" in said
    assert conform.main(["train", "--project", TEST_PROJECT]) == 0, capsys.readouterr().out
    printed = capsys.readouterr().out
    assert printed.count("✓") == 8 and "every check holds" in printed
    held = conform.latest("train")
    assert held.ok and held.version == contract.version_string(TRAIN)
    assert conform.main(["train", "--project", "no-such-project"]) == 2
    assert "holds no project 'no-such-project'" in capsys.readouterr().out
    # An engine that declares no things_are is checked on a database of its own, with no --project.
    assert conform.main(["biosteam", "--project", TEST_PROJECT]) == 2
    assert ("the biosteam engine declares no things_are, so its things are checked in a project made for the checks "
            "on a database of their own: python -m openferment_core.engine.conform biosteam, with no --project"
            in capsys.readouterr().out)


def test_both_doors_refuse_a_trains_bad_inputs_together_by_place_in_one_set_of_words(train_engines):
    """The engine's run route and pureOS's own route take a train's values
    through one door (train_spec.converted): every bad name at once, each by
    its place, in the same words, and nothing kept."""
    _saved(spec_of())
    client = TestClient(api.app)
    bad = [{"name": n, "quantity": person(0.2, unit="")} for n in ("Z9.V", "V", "F1.nonesuch")]
    engine = client.post("/api/engines/train/run", json={"thing": "t1", "by": "Ada Moreno", "inputs": bad})
    own = client.post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json"), "by": "Ada Moreno",
                                                     "inputs": bad})
    assert engine.status_code == own.status_code == 422
    said = own.json()["detail"]
    assert engine.json()["detail"] == said
    assert "Z9.V names 'Z9', which is no unit of train t1 and not its inlet" in said
    assert "V: a value a train's run sets is named <unit id>.<key> or inlet.<key>" in said
    assert "unit F1 (flash) has no parameter 'nonesuch'" in said
    assert runs.listed("train") == []


def _conform_here(test_database, monkeypatch) -> None:
    """The configured database for the checks' command: the test server, its
    rows the test's own (the session's binding)."""
    monkeypatch.setenv("OPENFERMENT_DATABASE_URL", test_database.server.render_as_string(hide_password=False))


def _every_row() -> dict[str, list[str]]:
    """Every row of every table of the openferment and sci_rag schemas, each
    as PostgreSQL writes the row out as text, by table: what "the same rows,
    byte for byte" is held to."""
    from sqlalchemy import text

    async def read() -> dict[str, list[str]]:
        async with db.session() as s:
            names = (await s.execute(text(
                "SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_schema IN "
                "('openferment', 'sci_rag') AND table_type = 'BASE TABLE' ORDER BY 1"))).scalars().all()
            out = {}
            for name in names:
                schema, table = name.split(".", 1)
                out[name] = sorted((await s.execute(text(f'SELECT x::text FROM "{schema}"."{table}" x'))).scalars())
        return out

    return db.run(read())


def _changed(before: dict[str, list[str]], after: dict[str, list[str]]) -> list[str]:
    """The tables whose rows differ between two reads of `_every_row`."""
    return sorted(n for n in {*before, *after} if before.get(n) != after.get(n))


CHECKS_BY = "conformance check of train"
# test_train's STAND-IN flash, alone: a train of it stands on a stream that carries no cells.
FLASH = [{"id": "F1", "type": "flash", "params": {"P": typed(101325.0), "V": typed(0.1)},
          "outlets": {"vapour": "waste", "liquid": "onward"}}]


def test_conform_in_a_project_checks_each_train_in_a_copy_and_a_persons_earlier_run_changes_nothing(
        train_engines, test_database, monkeypatch):
    """The checks read the project and run on a copy of it in a database of
    their own: each train the project holds is checked, all eight hold, and
    the project holds the same rows, byte for byte, after them, beside the
    verdict. A person of the project ran a train before the checks: its run
    made afresh in the copy is the person's run's id, created by the checks,
    and the person's row is as it was. The verdict kept gives counts and
    names no project, train or run. With a value set (`--inputs`), the train
    that lacks the value's place is left out, refused, and the train it fits
    is checked with it."""
    _saved(spec_of())
    _saved(spec_of(id="t2", name="Another test train", units=FLASH))
    client = TestClient(api.app)
    mine = client.post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json"),
                                                      "by": "A. Stranger"}).json()["artifactId"]
    _conform_here(test_database, monkeypatch)
    before = _every_row()
    v = conform.in_project("train", TEST_PROJECT, by=CHECKS_BY)
    assert v.ok, [(c.number, c.said) for c in v.checks if not c.ok]
    assert "parameters of 2 things (t1, t2)" in v.checks[1].said
    three = v.checks[2].said
    assert three.startswith(f"t1: run {mine} of t1, asked twice, is 1 row; engine train, status done") and (
        "; t2: run " in three)
    assert f"made in a copy of project {TEST_PROJECT} on a database of the checks' own" in three
    assert "copied, and the verdict alone written to the database they were read from" in three
    assert "left out" not in three
    # A train replays with no tolerance, and its words say identical once.
    assert v.checks[3].said == "t1: identical; 0 differences; t2: identical; 0 differences"
    eight = v.checks[7].said
    assert eight.startswith(f"t1: the checks' run: created_by {CHECKS_BY!r}") and (
        f"; t2: the checks' run: created_by {CHECKS_BY!r}" in eight)
    assert eight.count("1 value its estimate") == 2
    assert _changed(before, _every_row()) == ["openferment.engine_checks"]
    assert [(r.id, r.by) for r in runs.listed("train")] == [(mine, "A. Stranger")]
    # The verdict kept is the machine's row: its words give counts and name no project, train or run.
    kept = conform.latest("train")
    assert kept == conform._counted(v, 2, 0) and [(c.number, c.ok) for c in kept.checks] == [
        (c.number, c.ok) for c in v.checks]
    words = json.dumps(kept.model_dump(mode="json"))
    assert not [w for w in (TEST_PROJECT, "t1", "t2", mine) if w in words], words
    assert kept.checks[2].said == ("held on each of the 2 things of a project, checked in a copy of it; the command's "
                                   "own table gives the words")
    assert kept.checks[0].said.startswith("held for the engine") and "over the parameters of the 2 things" in (
        kept.checks[1].said)
    # The values --inputs names are set on every train checked: one that lacks a value's place is left out, refused.
    unit = {p.key: p.unit for p in TRAIN.parameters("t1", None)}["C1.split.Yeast"]
    asked = [EngineInput(name="C1.split.Yeast", quantity=Quantity(value=0.9, unit=unit, origin={
        "kind": "person-assumption", "by": "Ada Moreno", "at": DAY}))]
    narrowed = conform.in_project("train", TEST_PROJECT, by=CHECKS_BY, inputs=asked)
    assert narrowed.ok, [(c.number, c.said) for c in narrowed.checks if not c.ok]
    three = narrowed.checks[2].said
    assert " of t1 with 1 value set, asked twice, is 1 row" in three and "of t2" not in three
    assert (f"; left out, 1 thing, each with its words: (1) t2, {train_engine.REFUSED}: C1.split.Yeast names 'C1', "
            "which is no unit of train t2 and not its inlet") in three
    assert conform.latest("train") == conform._counted(narrowed, 1, 1)
    assert conform.latest("train").checks[2].said.startswith("held on the 1 thing of a project, checked in a copy of "
                                                             "it, 1 more left out")


def test_conform_in_a_project_lists_a_draft_and_a_train_that_waits_as_such_and_leaves_them_out(
        train_engines, test_database, monkeypatch):
    """A saved draft with no unit and a train whose values wait for what no
    source gives are listed in check 3's words, each as what it is with its
    own words, and left out; every check holds on the train that runs. A
    thing named is checked as named, and a train that waits then fails check
    3 in its words. The project holds the same rows after either."""
    _saved(spec_of(id="a0", name="A train that waits", units=[{"id": "D1", "type": "distillation"}]))
    _saved(spec_of(id="b0", name="A draft", units=[]))
    _saved(spec_of())
    _conform_here(test_database, monkeypatch)
    before = _every_row()
    v = conform.in_project("train", TEST_PROJECT, by=CHECKS_BY)
    assert v.ok, [(c.number, c.said) for c in v.checks if not c.ok]
    three = v.checks[2].said
    assert three.startswith("run ") and " of t1, asked twice, is 1 row" in three
    # The copy's words come first, then each thing left out, numbered, with its words.
    copied = three.index("copied, and the verdict alone written to the database they were read from")
    listed = three.index(f"; left out, 2 things, each with its words: (1) a0, {train_engine.WAITS}: unit D1 "
                         "(distillation): light_key waits")
    assert copied < listed and three.endswith(f"; (2) b0, {train_engine.DRAFT}: a train holds at least one unit")
    assert "(t1)" in v.checks[1].said and "a0" not in v.checks[1].said
    named = conform.in_project("train", TEST_PROJECT, by=CHECKS_BY, things=["a0"])
    assert not named.ok and "light_key waits" in named.checks[2].said and "left out" not in named.checks[2].said
    assert _changed(before, _every_row()) == ["openferment.engine_checks"]
    assert runs.listed("train") == []


def test_conform_in_a_project_that_holds_no_train_that_can_run_is_refused_in_words(train_engines, test_database,
                                                                                    monkeypatch):
    _saved(spec_of(id="b0", name="A draft", units=[]))
    _conform_here(test_database, monkeypatch)
    before = _every_row()
    with pytest.raises(conform.ConformRefused, match=re.escape(
            "the project holds no thing of the train engine that can run as it stands; left out, 1 thing, each with "
            f"its words: (1) b0, {train_engine.DRAFT}: a train holds at least one unit. Make one that runs; set the "
            "values a waiting thing needs with --inputs <file>; or name one with --thing <id> to check it as it "
            "stands")):
        conform.in_project("train", TEST_PROJECT, by=CHECKS_BY)
    assert _changed(before, _every_row()) == [] and conform.latest("train") is None


def test_conform_in_a_project_that_holds_none_of_the_engines_things_says_what_they_are(train_engines, test_database,
                                                                                       monkeypatch, capsys):
    _conform_here(test_database, monkeypatch)
    before = _every_row()
    assert conform.main(["train", "--project", TEST_PROJECT]) == 2
    assert capsys.readouterr().out.strip() == (f"✗ the project holds none of the train engine's things, which are "
                                               f"{TRAIN.things_are}: make one there, then run the checks again")
    assert _changed(before, _every_row()) == [] and conform.latest("train") is None


def test_a_trains_rest_on_what_its_inlet_reads_the_pool_and_the_strains_and_unready_says_what_it_is(train_engines):
    """What the copy takes of a project, as the train engine names it: every
    train; each artifact a train's inlet reads, by id, with its run's row (a
    simulation and its vessel design, a run, a scenario's newest run); the
    scenarios an inlet names; the evidence pool whole; the strains. And what
    each train the checks leave out is, in its words."""
    from test_builder import RUN_ID, _keep

    _keep()  # test_builder's STAND-IN run of scenario sc-k3x9q-1, its basis naming the scenario
    simulation, design = "a0a0a0a0a0a0a0a1", "a0a0a0a0a0a0a0a5"
    _saved(spec_of(id="s1", name="On a simulation", inlet={"kind": "simulation", "ref": simulation, "vessel": design}))
    _saved(spec_of(id="r1", name="On a run", inlet={"kind": "run-stream", "ref": RUN_ID, "streamId": "s1"},
                   units=FLASH))
    _saved(spec_of(id="c1", name="On a scenario", inlet={"kind": "run-stream", "ref": "sc-k3x9q-1"}, units=FLASH))
    _saved(spec_of(id="b0", name="A draft", units=[]))
    _saved(spec_of(id="a0", name="A train that waits", units=[{"id": "D1", "type": "distillation"}]))
    ids = sorted({simulation, design, RUN_ID})
    assert TRAIN.rests_on() == {"trains": None, "artifacts": {"id": ids}, "runs": {"id": ids},
                                "scenarios": {"id": ["sc-k3x9q-1"]}, "candidates": None, "decisions": None,
                                "catalogue": {"kind": ["strain"]}}
    said = {th.id: TRAIN.unready(th.id, []) for th in TRAIN.things()}
    assert said["r1"] is None and said["c1"] is None
    assert said["b0"] == f"{train_engine.DRAFT}: a train holds at least one unit"
    assert said["a0"].startswith(f"{train_engine.WAITS}: unit D1 (distillation): light_key waits (")
    assert said["s1"].startswith(f"{train_engine.REFUSED}: there is no kept artifact {simulation} here")
    assert runs.listed("train") == [] and not [c for c in train_engines.calls if c[0] == "train_run"]


def test_the_copy_holds_every_row_a_trains_resolution_reads_and_resolves_each_train_as_the_project_does(
        train_engines, test_database, monkeypatch):
    """A project whose trains rest on every kind of row a train's resolution
    reads: records bound from the evidence pool (an extraction, a reviewer's
    rejection of one of its candidates that moves what binds), a simulation
    naming a strain of the catalogue, a person's earlier run of a train that
    another train stands on, and a scenario whose newest run belongs to it
    through the scenario's own row. Every table the resolution reads in the
    project is one the copy takes, and the copy resolves each train as the
    project does: its parameters, and the artifact a run of it computes (its
    id, its output and its provenance). A copy that leaves out a table, or
    the rows of one that a train reads, fails here. Every check then holds on
    each train, the train a second one stands on among them."""
    from sqlalchemy import event

    from openferment_core import biorepo, catalogues, extract, project_state, projects
    from openferment_core.models import ExtractResponse, Usage
    from standins import plant_artifact
    from test_builder import _keep
    from test_catalogues import STRAIN
    from test_evidence_pool import cand, decision
    from test_vessel import keep, standin_simulation

    monkeypatch.setattr(train_spec, "_pool", PROJECT_POOL)
    # test_train's STAND-IN step records, as an extraction the project keeps; a reviewer accepted the first and
    # rejected the second, so the first alone binds the centrifuge's split.
    found = [cand("cl1-Q1-00000001", "Q1", "step_recovery", 90.0, "%", "after centrifugation the broth kept"),
             cand("cl1-Q1-00000002", "Q1", "step_recovery", 80.0, "%", "after centrifugation the broth kept"),
             cand("cl1-Q1-00000003", "Q1", "step_recovery", 50.0, "%", "after the chromatography column")]
    extract._persist(ExtractResponse(paperId="Q1", extractedAt=f"{DAY}T00:00:00Z", candidates=found, audit=[],
                                     usage=Usage(), calls=0))
    db.run(biorepo._keep(projects.current(), decision("cl1-Q1-00000001", "verified"), found[0], undo=False))
    db.run(biorepo._keep(projects.current(), decision("cl1-Q1-00000002", "rejected", rejectReason="a STAND-IN"),
                         found[1], undo=False))
    catalogues.keep(STRAIN, by="Ada Moreno")
    simulation = "a0a0a0a0a0a0a0a2"
    keep(simulation, {**standin_simulation(False), "strain": STRAIN.id})
    # test_builder's STAND-IN runs of the scenario's flowsheet: one whose basis names the scenario, and a newer one
    # kept before a basis named its scenario, which belongs to it through the scenario's row.
    _keep()
    newest = _keep("bbbbbbbbbbbbbbb3", scenario=None)
    plant_artifact(newest.model_copy(update={"createdAt": "2026-10-22T10:00:00Z"}))
    project_state.put("scenarios", "sc-k3x9q-1", {"id": "sc-k3x9q-1", "kind": "biosteam", "modelId": "ethanol_glucose_v0",
                                                  "name": "A test scenario"}, by="Ada Moreno")
    _saved(spec_of())
    mine = TestClient(api.app).post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json"),
                                                                   "by": "A. Stranger"}).json()["artifactId"]
    _saved(spec_of(id="s1", name="On a simulation", inlet={"kind": "simulation", "ref": simulation,
                                                           "params": {"broth_flow": typed(1.0)}}))
    _saved(spec_of(id="r1", name="On a person's run", inlet={"kind": "run-stream", "ref": mine, "streamId": "C1_liquid"}))
    _saved(spec_of(id="c1", name="On a scenario", inlet={"kind": "run-stream", "ref": "sc-k3x9q-1"}, units=FLASH))

    def resolved() -> dict[str, object]:
        out = {}
        for th in TRAIN.things():
            assert TRAIN.unready(th.id, []) is None, th.id
            got = train_spec._prepared(TRAIN._train(th.id, None), [], None)
            art = artifacts.compute(train_spec.TRAIN_RUN, got.basis, records_by_id=got.pool.records_by_id, keep=False)
            out[th.id] = ([p.model_dump(mode="json") for p in TRAIN.parameters(th.id, None)],
                          (art.id, art.outputHash, art.provenance))
        return out

    read: list[str] = []

    def heard(conn, cursor, statement, *_):
        read.extend(re.findall(r"(?:FROM|JOIN)\s+openferment\.(\w+)", statement))

    event.listen(test_database.engine.sync_engine, "before_cursor_execute", heard)
    try:
        here = resolved()
    finally:
        event.remove(test_database.engine.sync_engine, "before_cursor_execute", heard)
    assert here["t1"][1][0] == mine
    bound = next(p for p in here["t1"][0] if p["key"] == "C1.split.Ethanol")
    assert (bound["origin"]["kind"], bound["origin"]["ref"]) == ("record", "cl1-Q1-00000001")
    assert any(i.value == newest.id for i in train_spec._prepared(TRAIN._train("c1", None), [], None).basis
               if i.name == "inlet")
    # The pool reads its documents' titles for its search alone, which no train's value or words read.
    assert set(read) - {"documents_link"} <= set(TRAIN.rests_on()) | {"projects"}, sorted(set(read))
    assert {"trains", "artifacts", "candidates", "decisions", "catalogue", "scenarios"} <= set(read)
    _conform_here(test_database, monkeypatch)
    with conform.copy_of(TRAIN, TEST_PROJECT) as copied:
        there = resolved()
    assert there == here
    assert copied == {"projects": 1, "trains": 4, "artifacts": 3, "runs": 0, "scenarios": 1, "candidates": 1,
                      "decisions": 2, "catalogue": 1}
    before = _every_row()
    v = conform.in_project("train", TEST_PROJECT, by=CHECKS_BY)
    assert v.ok, [(c.number, c.said) for c in v.checks if not c.ok]
    assert v.checks[2].said.startswith(f"t1: run {mine} of t1, asked twice, is 1 row")
    assert all(f"{t}: run " in v.checks[2].said for t in ("s1", "r1", "c1"))
    assert _changed(before, _every_row()) == ["openferment.engine_checks"]


def test_ready_names_the_checks_that_failed_and_the_command_that_says_why(train_engines):
    """A failed verdict's row reads to its end as one sentence: the checks
    that failed, when, and the command to run to see why."""
    from openferment_core.models import EngineCheck

    found = [EngineCheck(number=n, check=conform.CHECKS[n], ok=n not in (3, 8), said="placeholder words")
             for n in range(1, 9)]
    failed = conform.verdict(TRAIN, found, "conformance test")
    conform.keep(failed)
    row = {c.name: c for c in ready.check_engines()}["engine train"]
    assert row.mark == "warn" and row.detail.endswith(
        f"checks 3, 8 failed at {failed.at}; to see why, run {ready.conform_command('train')}")
    assert row.detail.endswith("; the checks run on a copy of it") and "says why" not in row.detail


class _Unrested:
    """An engine whose things are a project's own (`things_are`) and that
    names nothing they rest on: it loads and runs, and no command checks it."""

    name, worker, heavy = "unrested", None, ()
    things_are = "a project's placeholders"

    def version(self):
        return {"openferment-core": "0.1.0"}

    def things(self):
        return []

    def parameters(self, thing, configuration):
        return []

    def run(self, thing, configuration, inputs, by):
        raise EngineRefused("the unrested engine runs nothing")

    def replay(self, run):
        raise EngineRefused("nothing to replay")

    def export_sff(self, run):
        return "it has no plant"


UNRESTED = _Unrested()


def test_an_engine_whose_things_rest_on_nothing_named_loads_and_ready_says_why_no_command_checks_it(monkeypatch,
                                                                                                     capsys):
    monkeypatch.setattr(registry, "entry_points", lambda: _points(("unrested", "tests.test_engines:UNRESTED")))
    registry.reset()
    try:
        assert registry.found()["unrested"].error is None
        said = conform.unrested(UNRESTED)
        assert said.startswith(f"the unrested engine's things are {UNRESTED.things_are}, and it declares no "
                               "rests_on() naming the rows they rest on")
        assert conform.unrested(TRAIN) is None and conform.unrested(SAMPLE) is None
        row = {c.name: c for c in ready.check_engines()}["engine unrested"]
        assert row.mark == "warn" and row.detail.endswith(said) and "python -m" not in row.detail
        # The command refuses it in the same words, with --project and without.
        for argv in (["unrested"], ["unrested", "--project", TEST_PROJECT]):
            assert conform.main(argv) == 2
            assert capsys.readouterr().out.strip() == f"✗ {said}"
    finally:
        registry.reset()


def test_a_table_an_engine_names_is_one_of_a_projects_rows_and_any_other_is_refused_in_whole_words():
    assert conform._table("trains") is not None
    for name in ("no_such_table", "engine_checks"):
        with pytest.raises(conform.ConformRefused) as refused:
            conform._table(name)
        assert conform._words(refused.value) == (f"the name {name!r} is no table of a project's rows in the "
                                                 "openferment schema")


def test_words_too_long_for_a_check_are_cut_at_a_word_with_an_ellipsis():
    said = "a train carries no TEA, and the schema the toolkit ships requires every file's year"
    assert conform._cut(said, 200) == said
    cut = conform._cut(said, 40)
    assert cut == "a train carries no TEA, and the schema…" and len(cut) <= 41
    assert conform._cut("a" * 50, 40) == "a" * 40 + "…"


def _on_server(test_database, name: str) -> bool:
    """Whether the test server holds database `name`."""
    import asyncio

    from openferment_core.db import migrate

    found = asyncio.run(migrate._scalar(test_database.server.set(database="postgres"),
                                        f"SELECT count(*) FROM pg_database WHERE datname = '{name}'"))
    return bool(found)


class _Interrupted(BaseException):
    """What an interrupt raises as it ends a block, standing in for Ctrl-C's KeyboardInterrupt."""


def test_a_copy_whose_rollback_cannot_close_lets_what_ended_it_through_and_drops_its_database(train_engines,
                                                                                            test_database,
                                                                                            monkeypatch):
    """A connection still busy with a query an interrupt cut short refuses its
    rollback (asyncpg: another operation is in progress). The interrupt is
    what the caller meets, the pool is disposed of, and the checks' database
    is dropped."""
    from openferment_core.db import migrate

    _saved(spec_of())
    _conform_here(test_database, monkeypatch)
    made: list[str] = []
    create = migrate.create
    monkeypatch.setattr(migrate, "create", lambda name, url=None: made.append(name) or create(name, url))

    class Busy(db.Binding):
        async def close(self):
            await super().close()
            raise RuntimeError("cannot perform operation: another operation is in progress (a STAND-IN)")

    monkeypatch.setattr(db, "Binding", Busy)
    with pytest.raises(_Interrupted):
        with conform.copy_of(TRAIN, TEST_PROJECT):
            assert [th.id for th in TRAIN.things()] == ["t1"] and _on_server(test_database, made[0])
            raise _Interrupted
    assert len(made) == 1 and not _on_server(test_database, made[0])
    assert [th.id for th in TRAIN.things()] == ["t1"], "the sessions bind as they did before the copy"


def test_sighup_and_sigterm_end_the_block_while_the_checks_database_stands_and_their_handlers_return_after():
    import signal as signals

    before = {s: signals.getsignal(s) for s in conform.ENDING}
    assert {signals.SIGTERM, signals.SIGHUP} <= set(conform.ENDING)
    with conform._signals_end_the_block():
        for s in conform.ENDING:
            handler = signals.getsignal(s)
            assert handler is not before[s] and callable(handler)
            with pytest.raises(SystemExit) as ended:
                handler(s, None)
            assert ended.value.code == 128 + s
    assert {s: signals.getsignal(s) for s in conform.ENDING} == before


# A process that makes the checks' own database, says its name and waits to be ended.
SCRATCH_THEN_WAIT = """
import time
from openferment_core.engine import conform
with conform._scratch("signal-test") as url:
    print(url.database, flush=True)
    time.sleep(120)
"""


def test_sigterm_ends_the_command_with_its_code_and_drops_the_checks_database(test_database):
    import os
    import signal as signals

    from openferment_core.db import migrate

    env = {**os.environ, "OPENFERMENT_DATABASE_URL": test_database.server.render_as_string(hide_password=False)}
    ran = subprocess.Popen([sys.executable, "-c", SCRATCH_THEN_WAIT], cwd=ROOT / "core", env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    name, left = "", False
    try:
        name = ran.stdout.readline().strip()
        assert name.startswith("openferment_conform_signal_test_"), ran.stderr.read()
        assert _on_server(test_database, name)
        ran.send_signal(signals.SIGTERM)
        assert ran.wait(timeout=60) == 128 + signals.SIGTERM, ran.stderr.read()
    finally:
        if ran.poll() is None:
            ran.kill()
            ran.wait()
        # A database the process left is the test's to drop, so a failing run leaves none behind.
        left = bool(name) and _on_server(test_database, name)
        if left:
            migrate.drop(name, test_database.server)
    assert not left, f"{name} was left on the server"


# ── biosteam's scenario flowsheets (alpha 2.2 stage C, D6) ─────────────

from types import SimpleNamespace  # noqa: E402

import standins  # noqa: E402
from openferment_core.models import InputAssumption  # noqa: E402
from standins import assumed_inputs  # noqa: E402

SCENARIO_FLOWSHEET = "ethanol_glucose_v0"
# test_proforma_runs' typed values: the plant scale and the glucose price, the two inputs no record binds.
SCENARIO_ASSUMED = [InputAssumption(key="plant_scale", value=100000.0, low=100000.0, high=100000.0, by="Ada Moreno",
                                    at=DAY, note="a STAND-IN for a test"),
                    InputAssumption(key="glucose_price", value=0.4, low=0.3, high=0.5, by="Ada Moreno", at=DAY,
                                    note="a STAND-IN for a test")]


@pytest.fixture
def scenario_worker(monkeypatch, tmp_path):
    """The closed-form STAND-IN evaluator in place of the Proforma worker, over the stand-in records, as
    test_proforma_runs' `standin` holds them; the engines' registry with BioSTEAM in it."""
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)
    return pool


def test_biosteam_lists_the_shelfs_scenario_flowsheets_beside_its_library_plants(engines, scenario_worker):
    from openferment_core.flowsheets import shelf

    biosteam = registry.get("biosteam")
    things = {t.id: t for t in biosteam.things()}
    library_ids = [p.id for p in library.shelf().plants if p.id in things]
    assert list(things)[: len(library_ids)] == library_ids, "the library's own things first, as the shelf lists them"
    flowsheet = things[SCENARIO_FLOWSHEET]
    assert (flowsheet.kind, flowsheet.title, flowsheet.configurations, flowsheet.defaultConfiguration) == (
        "scenario", shelf.SHELF[SCENARIO_FLOWSHEET].title, [], None)
    assert (flowsheet.precision.rtol, flowsheet.precision.atol) == (0.0, 0.0), "a Proforma run replays identically"
    # A reference biorefinery is no scenario's flowsheet, and the composite waits for a scenario that names its parts.
    assert not {f for f, info in shelf.SHELF.items() if info.reference} & set(things)
    assert shelf.COMPOSITE not in things
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
    assert SCENARIO_FLOWSHEET in [t["id"] for t in listed["biosteam"]["things"]]


def test_a_scenario_flowsheets_parameters_are_what_a_scenario_of_it_binds(engines, scenario_worker):
    biosteam = registry.get("biosteam")
    params = {p.key: p for p in biosteam.parameters(SCENARIO_FLOWSHEET, None)}
    bound = {i.key: i for i in proforma.bind_flowsheet(SCENARIO_FLOWSHEET, pool=scenario_worker).inputs}
    assert set(params) == {i.key for i in shelf_inputs(SCENARIO_FLOWSHEET)}
    for key, i in bound.items():
        p = params[key]
        if i.binding == "records":
            assert (p.value, p.origin.kind, p.origin.ref) == (i.value, "record", ", ".join(i.recordIds)), key
        else:
            assert (p.value, p.origin) == (None, None) and "assumption" in p.sourceRule, key
    assert params["ethanol_purity"].origin.kind == "convention" and params["ethanol_purity"].origin.note
    # The engine's route reads the same, and a configuration the flowsheet takes none of is refused in words.
    client = TestClient(api.app)
    served = client.get("/api/engines/biosteam/parameters", params={"thing": SCENARIO_FLOWSHEET}).json()
    assert [p["key"] for p in served] == list(params)
    refused = client.get("/api/engines/biosteam/parameters", params={"thing": SCENARIO_FLOWSHEET, "configuration": "x"})
    assert refused.status_code == 422 and "takes no configuration" in refused.json()["detail"]
    held, said = conform._origins(biosteam, [t for t in biosteam.things() if t.id == SCENARIO_FLOWSHEET])
    assert held, said


def shelf_inputs(flowsheet):
    from openferment_core.flowsheets import shelf

    return shelf.SHELF[flowsheet].inputs


def test_a_scenario_flowsheets_run_through_the_engine_is_one_proforma_row_with_its_file(engines, scenario_worker):
    client = TestClient(api.app)
    inputs = [i.model_dump(mode="json", exclude_none=True) for i in assumed_inputs(SCENARIO_ASSUMED)]
    waits = client.post("/api/engines/biosteam/run", json={"thing": SCENARIO_FLOWSHEET, "by": "Ada Moreno"})
    assert waits.status_code == 422 and "wait for a source" in waits.json()["detail"] and runs.listed() == []
    first = client.post("/api/engines/biosteam/run", json={"thing": SCENARIO_FLOWSHEET, "inputs": inputs,
                                                           "by": "Ada Moreno"})
    assert first.status_code == 200, first.json()
    run = first.json()["run"]
    assert (run["engine"], run["tool"], run["plant"], run["configuration"], run["scenarioId"], run["by"]) == (
        "biosteam", proforma.RUN, SCENARIO_FLOWSHEET, None, SCENARIO_FLOWSHEET, "Ada Moreno")
    assert run["status"] == "done" and run["provenance"] == "assumed" and run["sff"]["recordId"] == f"run-{run['id']}"
    assert {v["name"] for v in run["outputs"]["values"]} >= {"price.solvedPrice", "quantiles.p50"}
    # The same request again, at the engine or at Proforma's own route as an unsaved scenario named by the
    # flowsheet's id, is the one row.
    again = client.post("/api/engines/biosteam/run", json={"thing": SCENARIO_FLOWSHEET, "inputs": inputs,
                                                           "by": "Grace Hopper"}).json()["run"]
    routed = client.post("/api/proforma/run", json={"scenarioId": SCENARIO_FLOWSHEET, "flowsheet": SCENARIO_FLOWSHEET,
                                                    "inputs": inputs, "by": "Grace Hopper"})
    assert again == run and routed.status_code == 200 and routed.json()["artifactId"] == run["id"]
    assert [r.id for r in runs.listed("biosteam")] == [run["id"]]
    # A value its input cannot take is refused before anything runs, and keeps nothing.
    wrong = [{**inputs[0], "quantity": {**inputs[0]["quantity"], "unit": "placeholder-unit"}}, inputs[1]]
    refused = client.post("/api/engines/biosteam/run", json={"thing": SCENARIO_FLOWSHEET, "inputs": wrong})
    assert refused.status_code == 422 and "plant_scale is set in 'placeholder-unit'" in refused.json()["detail"]
    assert len(runs.listed("biosteam")) == 1


def test_conformance_holds_on_a_scenario_flowsheet(engines, scenario_worker):
    """The eight checks on one of biosteam's scenario flowsheets, its values set as `--inputs` sets them, on the
    stand-in evaluator (test_engines_sim.py makes them on the real worker, beside a library plant)."""
    biosteam = registry.get("biosteam")
    found = conform.checks(biosteam, by="conformance test", things=[SCENARIO_FLOWSHEET], entry=BIOSTEAM_ENTRY,
                           inputs=assumed_inputs(SCENARIO_ASSUMED))
    assert [c.number for c in found] == list(range(1, 9))
    assert all(c.ok for c in found), [(c.number, c.said) for c in found if not c.ok]
    model = next(c for c in found if c.number == 8).said
    assert "conformance-model" in model and "its estimate" in model, model


def test_the_two_library_doors_are_one_path(engines, plant_worker):
    """POST /api/library/{plant}/run takes typed inputs and runs through the
    biosteam engine's own path (engine/biosteam.py `run_plant`): a value's
    unit is checked before the plant is built at both doors, in one set of
    words, and a plant that takes configurations, asked with none, runs in
    its default at both, and at the tools' door, as one row."""
    biosteam = registry.get("biosteam")
    client = TestClient(api.app)
    typed = given("stream.sugarcane.price", 2.0, unit="placeholder-unit").model_dump(mode="json", exclude_none=True)
    doors = [client.post("/api/library/sugarcane/run", json={"inputs": [typed], "by": "Ada Moreno"}),
             client.post("/api/engines/biosteam/run", json={"thing": "sugarcane", "inputs": [typed], "by": "Ada Moreno"})]
    assert [d.status_code for d in doors] == [422, 422]
    assert doors[0].json()["detail"] == doors[1].json()["detail"] and "the parameter's unit is 'USD/kg'" in doors[0].text
    assert "library_run" not in plant_worker.calls and runs.listed() == [], "a value refused keeps nothing"
    (cane,) = [t for t in biosteam.things() if t.id == "cane"]
    assert cane.configurations and cane.defaultConfiguration == cane.configurations[0]
    routed = client.post("/api/library/cane/run", json={"by": "Ada Moreno"})
    assert routed.status_code == 200, routed.json()
    run = routed.json()["run"]
    assert run["configuration"] == cane.defaultConfiguration
    engine = client.post("/api/engines/biosteam/run", json={"thing": "cane", "by": "Ada Moreno"}).json()["run"]
    tool = tools.run("engine_run", {"plant": "cane"}, tools.ToolContext(person="Ada Moreno"))
    assert engine["id"] == run["id"] == tool.summary["runId"] and biosteam.run("cane", None, [], "Ada Moreno").id == run["id"]
    assert [r.id for r in runs.listed("biosteam")] == [run["id"]]


# The things the biosteam engine lists of kind `scenario`, in a process of its own: before and after Proforma is
# imported, with the engine imported first or second, and once conformance reads the engine as the service holds it.
PROVIDED = """
import json, sys
order = sys.argv[1]
listed = []
def scenario_things(engine):
    return [t.id for t in engine.things() if t.kind == "scenario"]
if order == "engine first":
    from openferment_core.engine import biosteam
    listed.append(scenario_things(biosteam.ENGINE))
    from openferment_core import proforma
elif order == "proforma first":
    from openferment_core import proforma
    from openferment_core.engine import biosteam
else:
    from openferment_core.engine import biosteam, conform
    listed.append(scenario_things(biosteam.ENGINE))
    conform.as_served()
listed.append(scenario_things(biosteam.ENGINE))
print(json.dumps({"listed": listed, "providers": list(biosteam._PROVIDERS)}))
"""


@pytest.mark.parametrize("order", ["engine first", "proforma first", "as served"])
def test_the_engine_package_reaches_proforma_through_the_provider_proforma_registers(order):
    """The plan's D6 amendment at C.4: engine/ imports no module above it, so
    Proforma gives the biosteam engine its scenario flowsheets through the
    provider it registers as it is imported (engine/biosteam.py `provide`),
    whichever of the two is imported first; the engine alone lists none, and
    conformance reads the engine as the service's app holds it, Proforma
    imported (conform.as_served)."""
    done = subprocess.run([sys.executable, "-c", PROVIDED, order], cwd=ROOT / "core", capture_output=True, text=True,
                          timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    got = json.loads(done.stdout.strip().splitlines()[-1])
    assert got["providers"] == ["proforma"] and "ethanol_glucose_v0" in got["listed"][-1]
    if order != "proforma first":
        assert got["listed"][0] == [], "the engine alone lists no scenario flowsheet"


def test_a_plant_that_takes_configurations_is_read_in_its_default_at_every_parameters_door(engines, plant_worker):
    """The plan's D6 amendment at C.4: a plant that takes configurations,
    asked with none, is read in its default at every door that reads its
    parameters, as every door runs it: the engine's route, the library's
    route, the engine_parameters tool, and engine_plants' row says so."""
    biosteam = registry.get("biosteam")
    (cane,) = [t for t in biosteam.things() if t.id == "cane"]
    default = cane.defaultConfiguration
    assert default is not None and cane.configurations
    client = TestClient(api.app)
    served = client.get("/api/engines/biosteam/parameters", params={"thing": "cane"})
    assert served.status_code == 200, served.json()
    named = client.get("/api/engines/biosteam/parameters", params={"thing": "cane", "configuration": default}).json()
    assert served.json() == named
    library_door = client.get("/api/library/cane/parameters")
    assert library_door.status_code == 200 and library_door.json()["configuration"] == default
    tool = tools.run("engine_parameters", {"plant": "cane"}, tools.ToolContext(person="Ada Moreno"))
    assert tool.error is None and tool.summary["configuration"] == default, tool.error
    asked_for = {args.get("configuration") for op, args in plant_worker.library.calls if op == "library_parameters"}
    assert asked_for == {default}
    rows = {r["plant"]: r for r in tools.run("engine_plants", {"words": "cane"}, tools.ToolContext()).summary["plants"]}
    assert (rows["cane"]["defaultConfiguration"], rows["cane"]["requiresConfiguration"]) == (default, False)
    assert rows["cane"]["configurations"] == cane.configurations


def test_an_unknown_thing_at_biosteams_door_is_refused_naming_the_engines_own_things(engines, scenario_worker):
    """A thing neither on the library's shelf nor provided is refused in
    words naming what the engine runs, the shelf's scenario flowsheets among
    them, at the run route, the parameters route, the tools and check 7, and
    keeps nothing; a subsystem the shelf holds is the library's to refuse."""
    biosteam = registry.get("biosteam")
    ids = [t.id for t in biosteam.things()]
    words = f"the biosteam engine runs no thing 'ethanol_glucose'; it runs {', '.join(ids)}"
    client = TestClient(api.app)
    ran = client.post("/api/engines/biosteam/run", json={"thing": "ethanol_glucose", "by": "Ada Moreno"})
    read = client.get("/api/engines/biosteam/parameters", params={"thing": "ethanol_glucose"})
    assert [(r.status_code, r.json()["detail"]) for r in (ran, read)] == [(422, words), (422, words)]
    assert SCENARIO_FLOWSHEET in words and "tea" not in ids
    tool = tools.run("engine_parameters", {"plant": "ethanol_glucose"}, tools.ToolContext(person="Ada Moreno"))
    assert tool.error == f"engine_parameters refused: {words} (engine_plants lists them)"
    tool = tools.run("engine_run", {"plant": "ethanol_glucose"}, tools.ToolContext(person="Ada Moreno"))
    assert tool.error == f"engine_run refused: {words}"
    ok, said = conform._refused_unknown(biosteam, "conformance test")
    assert ok and f"the biosteam engine runs no thing '{conform.NO_SUCH_THING}'" in said and "0 run kept" in said
    assert runs.listed() == []


def test_a_scenario_flowsheets_refusal_keeps_its_words_whole_at_each_door(engines, scenario_worker):
    """A refusal the scenario flowsheet's values meet at Proforma's door is
    said whole at the engine's door, its closing quote kept, as Proforma's
    own route says it."""
    inputs = [i.model_dump(mode="json", exclude_none=True) for i in assumed_inputs(SCENARIO_ASSUMED)]
    wrong = [{**inputs[0], "quantity": {**inputs[0]["quantity"], "unit": "placeholder-unit"}}, inputs[1]]
    words = "plant_scale is set in 'placeholder-unit', and the parameter's unit is 't yr-1'"
    client = TestClient(api.app)
    engine = client.post("/api/engines/biosteam/run", json={"thing": SCENARIO_FLOWSHEET, "inputs": wrong})
    routed = client.post("/api/proforma/run", json={"scenarioId": SCENARIO_FLOWSHEET, "flowsheet": SCENARIO_FLOWSHEET,
                                                    "inputs": wrong})
    assert [(r.status_code, r.json()["detail"]) for r in (engine, routed)] == [(422, words), (422, words)]
    with pytest.raises(EngineRefused) as refused:
        registry.get("biosteam").run(SCENARIO_FLOWSHEET, None, [EngineInput.model_validate(w) for w in wrong], "A. N.")
    assert str(refused.value) == words and runs.listed() == []


def test_a_scenario_flowsheet_whose_values_wait_is_refused_before_conformance_runs(engines, scenario_worker, capsys):
    """A scenario flowsheet whose inputs wait for values (its parameters give
    them no default) cannot run as it stands: biosteam's `unready` says so,
    and the checks' command refuses it in words before anything is made, so
    no failing verdict stands in for biosteam's; with its values set it is
    ready, and a library plant always is."""
    biosteam = registry.get("biosteam")
    said = biosteam.unready(SCENARIO_FLOWSHEET, [])
    assert said == f"{SCENARIO_FLOWSHEET} waits for 2 values its parameters give no default, which a run sets: " \
                   "glucose_price, plant_scale"
    assert biosteam.unready(SCENARIO_FLOWSHEET, assumed_inputs(SCENARIO_ASSUMED)) is None
    assert biosteam.unready("cane", []) is None
    kept = conform.latest("biosteam")
    assert conform._inside("biosteam", "conformance test", ["--thing", SCENARIO_FLOWSHEET]) == 2
    err = capsys.readouterr().err
    assert f"{SCENARIO_FLOWSHEET} cannot be checked as it stands: {said}; set its values with --inputs <file>" in err
    assert runs.listed() == [] and conform.latest("biosteam") == kept


def test_check_3_says_a_run_that_answers_no_output(engines, scenario_worker):
    """A scenario flowsheet's run whose every case asks a yield above the
    stand-in's theoretical is kept done with no price (test_proforma_ethanol's
    case): the engine's route answers 200 with that row, its outputs.values
    empty, and check 3 says the run answers no output."""
    biosteam = registry.get("biosteam")
    above = standins.STANDIN_THEORETICAL * 1.2
    values = [InputAssumption(key=k, value=v, low=v, high=v, by="Ada Moreno", at=DAY, note="a STAND-IN for a test")
              for k, v in (("feed_glucose_conc", 100.0), ("titre", 45.0), ("yield", above), ("productivity", 2.0))]
    inputs = assumed_inputs([*values, *SCENARIO_ASSUMED])
    answer = TestClient(api.app).post("/api/engines/biosteam/run", json={
        "thing": SCENARIO_FLOWSHEET, "by": "Ada Moreno",
        "inputs": [i.model_dump(mode="json", exclude_none=True) for i in inputs]})
    assert answer.status_code == 200, answer.json()
    assert answer.json()["run"]["status"] == "done" and answer.json()["run"]["outputs"]["values"] == []
    (thing,) = [t for t in biosteam.things() if t.id == SCENARIO_FLOWSHEET]
    ok, said, run = conform._run_twice(biosteam, thing, inputs, "conformance test")
    assert ok and run is not None and said.endswith("; it answers no output: its outputs.values are empty"), said
