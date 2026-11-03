"""The engine contract (alpha 2.2 stage B; docs/api/engines.md, ADR-015).

The registry loads every object of the entry-point group `openferment.engines`
and names what keeps one from use; `GET /api/engines` lists each; a run of a
contract engine is one `runs` row keyed by its basis, the same request twice
that one row, a value set kept with its origin, a bare number refused before
the worker is reached, a run the engine refuses kept as a receipt, a replay
held to the stated precision, its SFF refusal kept in words, its worker
started with no key and no database address; the four engine tools take the
engine; and the eight conformance checks hold for the contract's own sample
engine (engine/sample.py over workers/sample_worker.py, which computes
nothing), its verdict kept for `GET /api/engines` and `pnpm ready`.
"""
from __future__ import annotations

import json
import re
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openferment_core import api, artifacts, llm, ready, tools
from openferment_core.engine import conform, contract, registry, runs
from openferment_core.engine.sample import SAMPLE
from openferment_core.literature import KIT_SETTINGS
from openferment_core.models import EngineInput, EngineParameter, EngineThing, ParameterSpec, Quantity
from openferment_core.workers import withheld

SAMPLE_ENTRY = "openferment_core.engine.sample:SAMPLE"
ROOT = Path(__file__).resolve().parents[2]
BIOSTEAM_ENTRY = "openferment_core.engine.biosteam:ENGINE"


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
    return {"value": value, "unit": unit, "origin": {"kind": "person-assumption", "by": by, **origin}}


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
    assert run["tool"] == "engine.sample" and run["toolVersion"] == "sample · openferment-core 0.1.0"
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
    (given,) = [i for i in run["inputs"] if i["name"] == "value a-parameter"]
    # Written as a library run's override is: the day it was set, then its note.
    assert said(given["quantity"]["origin"]) == {"kind": "person-assumption", "by": "Ada Moreno", "at": runs._today(),
                                                 "note": f"typed on {runs._today()}: a placeholder"}
    assert [(v["name"], v["quantity"]["value"]) for v in run["outputs"]["values"]] == [("given a-parameter", 2.5),
                                                                                    ("count", 1.0)]


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
        value=4.0, unit="placeholder-unit", origin={"kind": "person-assumption", "by": "Ada Moreno"}))], "Ada Moreno")
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
    rows = {c.name: c for c in ready.check_engines()}
    assert rows["engine sample"].mark == "warn" and "never checked here" in rows["engine sample"].detail
    assert rows["engine broken"].mark == "warn" and "runs on without it" in rows["engine broken"].detail
    conform.keep(conform.verdict(SAMPLE, found, "conformance test"))
    held = conform.latest("sample")
    assert held.ok and held.version == "sample · openferment-core 0.1.0" and held.by == "conformance test"
    assert {c.name: c for c in ready.check_engines()}["engine sample"].mark == "ok"
    listed = {e["name"]: e for e in TestClient(api.app).get("/api/engines").json()}
    assert listed["sample"]["conformance"]["ok"] is True


def test_the_checks_run_with_the_values_they_are_given(engines):
    given = [EngineInput(name="a-parameter", quantity=Quantity(value=3.0, unit="placeholder-unit", origin={
        "kind": "person-assumption", "by": "conformance test", "note": "a placeholder"}))]
    found = {c.number: c for c in conform.checks(SAMPLE, by="conformance test", entry=SAMPLE_ENTRY, inputs=given)}
    assert all(c.ok for c in found.values()), [(n, c.said) for n, c in found.items() if not c.ok]
    assert "with 1 value set" in found[3].said and "its id the artifact id of its basis" in found[3].said
    assert "a model's run" in found[8].said and "its worker refused it too" in found[7].said


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
