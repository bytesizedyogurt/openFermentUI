"""The mirror's worker driven as the service drives it: SimWorker, one JSON request a line, no database."""
import io
import json
import math
from importlib.metadata import version

import pytest

from openferment_core.workers import SimWorker, WorkerError, serve
from openferment_engine_mirror.worker import HANDLERS, Refused

MODULE = "openferment_engine_mirror.worker"
DISTRIBUTION = "openferment-engine-mirror"
DEFAULTS = [{"name": "placeholder-a", "value": 1.0, "unit": "placeholder-unit"},
            {"name": "placeholder-b", "value": 2.0, "unit": "another-placeholder-unit"}]


def asked(*values, thing="reflect", configuration=None):
    return {"thing": thing, "configuration": configuration, "inputs": list(values)}


def counted(n):
    return {"name": "values set", "value": n, "unit": ""}


def in_shape(entries):
    """The protocol's shape for outputs and diagnostics (docs/api/workers.md, `run`)."""
    names = [e["name"] for e in entries]
    assert len(set(names)) == len(names)
    for e in entries:
        assert set(e) == {"name", "value", "unit"}
        assert isinstance(e["name"], str) and e["name"].strip() and len(e["name"]) <= 200
        assert isinstance(e["unit"], str)
        value = e["value"]
        assert isinstance(value, str) or (
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value))


@pytest.fixture
def worker():
    w = SimWorker(MODULE, withhold_secrets=True)
    yield w
    w.close()


def test_ping_answers_the_mirror_by_name(worker):
    answer = worker.call("ping", {})
    assert answer["worker"] == "mirror" and isinstance(answer["pid"], int)


def test_the_one_thing_takes_no_configuration_and_states_an_exact_precision(worker):
    (thing,) = worker.call("things", {})["things"]
    assert thing["id"] == "reflect" and thing["title"] and thing["kind"] == "placeholder"
    assert thing["configurations"] == [] and thing["defaultConfiguration"] is None
    assert thing["precision"] == {"rtol": 0, "atol": 0}


def test_every_parameter_has_a_placeholder_default_whose_origin_names_the_installed_package(worker):
    parameters = worker.call("parameters", {"thing": "reflect", "configuration": None})["parameters"]
    ref = f"{DISTRIBUTION}@{version(DISTRIBUTION)}"
    keys = [p["key"] for p in parameters]
    assert keys == sorted(keys)
    for p in parameters:
        assert p["origin"] == {"kind": "library-default", "ref": ref}
        assert p["unit"].endswith("placeholder-unit") and p["label"] and p["boundsReason"]
        assert "min" not in p and "max" not in p
    assert [{"name": p["key"], "value": p["value"], "unit": p["unit"]} for p in parameters] == DEFAULTS


def test_a_run_on_the_defaults_returns_each_default_and_counts_no_value_set(worker):
    answer = worker.call("run", asked())
    assert answer["outputs"] == DEFAULTS + [counted(0)]
    (took,) = answer["diagnostics"]
    assert took["name"] == "time taken" and took["unit"] == "ms" and took["value"] >= 0
    in_shape(answer["outputs"])
    in_shape(answer["diagnostics"])


def test_a_run_returns_each_value_it_sets_in_its_unit_and_key_order_and_counts_them(worker):
    a = {"name": "placeholder-a", "value": 3.0, "unit": "placeholder-unit"}
    b = {"name": "placeholder-b", "value": -4.5, "unit": "another-placeholder-unit"}
    assert worker.call("run", asked(a))["outputs"] == [a, DEFAULTS[1], counted(1)]
    assert worker.call("run", asked(b))["outputs"] == [DEFAULTS[0], b, counted(1)]
    answer = worker.call("run", asked(a, b))
    assert answer["outputs"] == [a, b, counted(2)]
    in_shape(answer["outputs"])


def test_the_same_request_answers_the_same_outputs_in_the_same_order_in_any_process(worker):
    request = asked({"name": "placeholder-b", "value": 5.0, "unit": "another-placeholder-unit"})
    first, again = worker.call("run", request), worker.call("run", request)
    fresh = SimWorker(MODULE, withhold_secrets=True)
    try:
        anew = fresh.call("run", request)
    finally:
        fresh.close()
    assert json.dumps(first["outputs"]) == json.dumps(again["outputs"]) == json.dumps(anew["outputs"])
    assert [d["name"] for d in first["diagnostics"] + again["diagnostics"] + anew["diagnostics"]] == ["time taken"] * 3


def test_the_mirror_has_no_plant_and_refuses_its_sff_file_in_words(worker):
    with pytest.raises(WorkerError, match=r"^Refused: the mirror engine has no plant, so it writes no SFF file"):
        worker.call("sff_export", asked(*DEFAULTS))


@pytest.mark.parametrize("op", ["parameters", "run", "sff_export"])
def test_every_op_that_names_a_thing_refuses_one_the_mirror_does_not_run(worker, op):
    args = {"thing": "nothing", "configuration": None} if op == "parameters" else asked(thing="nothing")
    with pytest.raises(WorkerError, match=r"^Refused: the mirror engine runs no thing 'nothing'; it runs 'reflect'"):
        worker.call(op, args)


def test_the_thing_conformance_offers_is_refused_in_words_with_no_traceback(worker):
    with pytest.raises(WorkerError, match=r"^Refused: the mirror engine runs no thing 'conform-no-such-thing'") as refused:
        worker.call("run", asked(thing="conform-no-such-thing"))
    assert "Traceback" not in str(refused.value)


@pytest.mark.parametrize("change, words", [
    ({"configuration": "one way"}, "the mirror's thing 'reflect' takes no configuration, and the request names 'one way'"),
    ({"inputs": [{"name": "placeholder-c", "value": 1.0, "unit": "placeholder-unit"}]},
     "the mirror's thing 'reflect' takes no parameter 'placeholder-c'; it takes placeholder-a, placeholder-b"),
    ({"inputs": [DEFAULTS[0], DEFAULTS[0]]}, "the run sets 'placeholder-a' twice"),
    ({"inputs": [{**DEFAULTS[0], "unit": "another-placeholder-unit"}]},
     "'placeholder-a' is set in 'another-placeholder-unit', and the mirror takes it in 'placeholder-unit'"),
    ({"inputs": [{**DEFAULTS[0], "value": "words"}]}, "'placeholder-a' takes a finite number, and the run set 'words'"),
    ({"inputs": [{**DEFAULTS[0], "value": True}]}, "'placeholder-a' takes a finite number, and the run set True"),
    ({"inputs": [{"name": "placeholder-a", "value": 1.0}]}, "each value a run sets is a name, a value and a unit"),
    ({"inputs": {"placeholder-a": 1.0}}, "a run's inputs are a list of values"),
])
def test_a_request_outside_the_parameters_is_refused_in_words(worker, change, words):
    with pytest.raises(WorkerError) as refused:
        worker.call("run", {**asked(), **change})
    assert str(refused.value).startswith(f"Refused: {words}")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 10 ** 400])
def test_a_number_that_is_not_finite_is_refused_at_the_handler(value):
    with pytest.raises(Refused, match=r"^'placeholder-a' takes a finite number"):
        HANDLERS["run"](asked({**DEFAULTS[0], "value": value}))


def test_serve_answers_one_line_a_request_skipping_a_blank_line():
    lines = [json.dumps({"id": 1, "op": "ping", "args": {}}),
             json.dumps({"id": 2, "op": "run", "args": asked()}),
             "",
             json.dumps({"id": 3, "op": "sff_export", "args": asked()})]
    stdout = io.StringIO()
    serve(HANDLERS, name="mirror", stdin=io.StringIO("\n".join(lines) + "\n"), stdout=stdout)
    answers = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [(a["id"], a["ok"]) for a in answers] == [(1, True), (2, True), (3, False)]
    assert answers[0]["result"]["worker"] == "mirror"
    assert answers[1]["result"]["outputs"] == DEFAULTS + [counted(0)]
    assert answers[2]["error"].startswith("Refused: the mirror engine has no plant")
