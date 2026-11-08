"""A number that is NaN or infinite in a run's values, refused in words at
every door before anything computes (alpha 2.2 D0.6; docs/api/engines.md,
EngineInput).

Python reads `NaN`, `Infinity`, `-Infinity` and a number past a float's
range (`1e999`) from a JSON body. Every door that takes a run's values reads
them as `EngineInput`s or a scenario's `ScenarioValue`s, which refuse such a
number as they are read: a 422 in FastAPI's list of field errors, the input
it echoes written in words, where a refusal echoing one answered 500 and a
run on one answered 500 at its id. A caller that builds its values in code
meets the same words at the one checker (`runs.check_inputs`) and the one
converter (`basis.override_of`); the tool door says so in its own words, and
`conform --inputs` refuses such a file. Every value here is a placeholder.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, llm, tools
from openferment_core.basis import InputRefused, override_of
from openferment_core.engine import EngineRefused, conform, runs
from openferment_core.engine.sample import SAMPLE
from openferment_core.models import EngineInput, EngineParameter, Quantity
from openferment_core.studies import scenarios
from test_engines import DAY, engines  # noqa: F401  (the registry of the sample)
from test_train import spec_of

ORIGIN = f'{{"kind": "person-assumption", "by": "Ada Moreno", "at": "{DAY}"}}'


def value(number: str, field: str = "value") -> str:
    """One value a run sets, as JSON text, `number` written as it stands (NaN, Infinity, 1e999)."""
    held = {"value": "1.0", "low": None, "high": None}
    held[field] = number
    ends = "".join(f', "{k}": {v}' for k, v in (("low", held["low"]), ("high", held["high"])) if v is not None)
    return (f'{{"name": "a-parameter", "quantity": {{"value": {held["value"]}, "unit": "placeholder-unit"{ends}, '
            f'"origin": {ORIGIN}}}}}')


def strict(text: str):
    """JSON as the standard reads it: NaN and Infinity are no JSON."""
    def refuse(token: str):
        raise AssertionError(f"the answer holds {token}, which JSON carries no way to write")

    return json.loads(text, parse_constant=refuse)


# The doors a run's values come in by, each a body with one value set, `{v}`.
DOORS = [
    ("/api/engines/sample/run", '{{"thing": "placeholder", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/engines/kinetics/run", '{{"thing": "batch_v1", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/library/cornstover/run", '{{"inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/proforma/run", '{{"scenarioId": "a-scenario", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/fermos/simulate", '{{"family": "batch_v1", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/fermos/forecast", '{{"fitArtifactId": "0123456789abcdef", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/fermos/vessel", '{{"simulation": "0123456789abcdef", "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/params/proforma:a-scenario/resolve", '{{"inputs": [{v}]}}'),
    ("/api/pureos/train/run", '{{"train": ' + json.dumps(spec_of().model_dump(mode="json")).replace("{", "{{")
     .replace("}", "}}") + ', "inputs": [{v}], "by": "Ada Moreno"}}'),
    ("/api/pureos/train/check", '{{"train": ' + json.dumps(spec_of().model_dump(mode="json")).replace("{", "{{")
     .replace("}", "}}") + ', "inputs": [{v}], "by": "Ada Moreno"}}'),
]
NUMBERS = [("NaN", "value", "its value is NaN"), ("Infinity", "value", "its value is infinite"),
           ("-Infinity", "value", "its value is infinite"), ("1e999", "value", "its value is infinite"),
           ("Infinity", "high", "its high is infinite"), ("NaN", "low", "its low is NaN")]


@pytest.mark.parametrize(("path", "body"), DOORS, ids=[d[0] for d in DOORS])
@pytest.mark.parametrize(("number", "field", "says"), NUMBERS, ids=[f"{n}-{f}" for n, f, _ in NUMBERS])
def test_every_door_refuses_a_number_that_is_nan_or_infinite_in_words_before_anything_runs(
        engines, monkeypatch, path, body, number, field, says):
    monkeypatch.setattr(SAMPLE, "call", lambda *a, **k: pytest.fail("the sample's worker was reached"))
    answer = TestClient(api.app).post(path, content=body.format(v=value(number, field)),
                                      headers={"content-type": "application/json"})
    assert answer.status_code == 422, answer.text
    detail = strict(answer.text)["detail"]
    words = json.dumps(detail)
    assert says in words and "a number a run sets is finite" in words, words
    assert runs.listed() == [], "nothing ran, and nothing is kept"


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e999"])
def test_a_scenario_refuses_a_value_that_is_nan_or_infinite_in_words(number):
    body = ('{"title": "A placeholder scenario", "plant": "cornstover", "values": [{"key": "a-parameter", '
            f'"quantity": {{"value": {number}, "unit": "placeholder-unit", "origin": {ORIGIN}}}}}]}}')
    answer = TestClient(api.app).post("/api/studies/scenarios", content=body,
                                      headers={"content-type": "application/json"})
    assert answer.status_code == 422, answer.text
    assert "a scenario's value is a finite number" in json.dumps(strict(answer.text)["detail"])
    assert scenarios.listed() == []


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e999"])
def test_the_bind_reads_query_refuses_one_in_words(number):
    answer = TestClient(api.app).get("/api/proforma/bind", params={
        "flowsheet": "ethanol_glucose_v0", "inputs": f"[{value(number)}]"})
    assert answer.status_code == 422, answer.text
    detail = strict(answer.text)["detail"]
    assert "inputs is a JSON list of values" in detail and "a number a run sets is finite" in detail, detail


def test_the_tool_door_refuses_one_in_its_own_words(engines):
    raw = json.loads('{"title": "A placeholder scenario", "plant": "cornstover", "values": [{"key": "a-parameter", '
                     '"quantity": {"value": NaN, "unit": "placeholder-unit"}}]}')
    said = tools.run("study_scenario", raw, tools.ToolContext(model=llm.DEFAULT_PRIMARY))
    assert said.error == ("study_scenario refused: values[0].quantity.value holds a number that is NaN or infinite, "
                          "and a number a tool takes is finite; nothing ran")
    assert scenarios.listed() == []


def test_a_caller_in_code_meets_the_same_words_at_the_checker_and_the_converter():
    built = EngineInput.model_construct(name="a-parameter", quantity=Quantity.model_construct(
        value=float("nan"), unit="placeholder-unit", basis=None, low=None, high=None, origin=None))
    p = EngineParameter(key="a-parameter", label="A placeholder", unit="placeholder-unit", value=1.0,
                        origin={"kind": "convention", "note": "a placeholder setting"}, boundsReason="none stated")
    with pytest.raises(EngineRefused, match="a-parameter: its value is NaN, and a number a run sets is finite"):
        runs.check_inputs("placeholder", [p], [built], bounds=True)
    with pytest.raises(InputRefused, match="a-parameter: its value is NaN, and a number a run sets is finite"):
        override_of("proforma:a-scenario", built, "placeholder-unit")
    with pytest.raises(ValueError, match="its value is infinite, and a number a run sets is finite"):
        EngineInput(name="a-parameter", quantity=Quantity(value=float("inf"), unit="placeholder-unit", origin={
            "kind": "person-assumption", "by": "Ada Moreno", "at": DAY}))


def test_conform_refuses_a_file_of_inputs_holding_one(tmp_path, capsys):
    path = tmp_path / "inputs.json"
    path.write_text(f"[{value('NaN')}]", encoding="utf-8")
    with pytest.raises(ValueError, match="its value is NaN, and a number a run sets is finite"):
        conform._read_inputs(str(path))
    assert conform.main(["sample", "--inputs", str(path)]) == 2
    assert "its value is NaN" in capsys.readouterr().out
