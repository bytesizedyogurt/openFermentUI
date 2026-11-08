"""A run follows the parameter panel's overrides (OF-BLD-020 §2.2, D3), with
no simulator.

A person's change on Proforma's scenario page is an Override of scope
`proforma:<scenario id>`, kept in the browser that typed it and carried by
the run, the binding and the ceiling check, each as a typed input in its
parameter's unit, converted back into the Override at Proforma's door
(alpha 2.2 D2). Each is laid on as the named assumption it is: it wins over
the records and over a fermOS fit for its input, the basis names the person,
and the run is `assumed`. A run that sets a value writes the line the
panel's overrides wrote (`assumptions read from`), word for word, so a run a
person makes through the panel keeps the artifact id its overrides gave it
before the run took typed inputs (alpha 2.2 D6, the amendment at C.4). The
older `assumptions` field retired at C.4: a request that sends it is refused
as any unknown field is.

Every record, override and assumption here is a FIXTURE written in the
test, on the STAND-IN records of standins.py; none is a measurement and no
price here is a result. The runs go through the real binding and artifact
code over the closed-form STAND-IN evaluator. The scenario is one a fixture
holds by its id (`held`): the seed's went with the seed (alpha 2.0, ADR-010).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openferment_core import artifacts, basis, intake, params, proforma
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.models import InputAssumption, Override, ProformaRunRequest
from standins import as_input, assumed_inputs, proforma_inputs, resolve_json, resolve_request, scope_units

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
OTHER = "A second test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
HELD = "sc-held-1"  # a scenario the service holds by its id, as the `held` fixture holds it
SCOPE = f"proforma:{HELD}"


@pytest.fixture(autouse=True)
def held(monkeypatch):
    """One scenario the service holds by its id, on the ethanol flowsheet."""
    row = {"id": HELD, "name": "A held test scenario", "kind": "biosteam", "modelId": ETHANOL}
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [row])
    return row


@pytest.fixture()
def standin(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def over(key, value, low=None, high=None, *, scope=SCOPE, by=BY, note="a STAND-IN for a test") -> Override:
    return Override(scope=scope, key=key, value=value, low=low, high=high, by=by, at="2026-10-21", note=note)


def assume(key, value, low=None, high=None, by=BY) -> InputAssumption:
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=by, at="2026-10-21", note="a STAND-IN for a test")


ECONOMICS = [over("plant_scale", 100000.0), over("glucose_price", 0.4, 0.3, 0.5)]


def asked(overrides=(), **fields) -> ProformaRunRequest:
    """A run request as the browser sends one (src/lib/proforma.ts `runBody`):
    the scope's overrides as typed inputs, each in its input's unit."""
    return ProformaRunRequest(**{"scenarioId": HELD, **fields}, inputs=proforma_inputs(overrides))


def sent(overrides) -> list[dict]:
    """The scope's overrides as the run route's JSON `inputs`."""
    return [i.model_dump(mode="json", exclude_none=True) for i in proforma_inputs(overrides)]


def named(art):
    return {i.name: i for i in art.inputs}


def test_a_runs_overrides_are_bound_as_named_assumptions_and_named_in_the_basis(standin):
    r = proforma.run(asked(ECONOMICS, samples=8), pool=standin)
    inputs = {i.key: i for i in r.inputs}
    assert inputs["glucose_price"].binding == "assumption" and inputs["glucose_price"].source.by == BY
    assert (inputs["glucose_price"].value, inputs["glucose_price"].low, inputs["glucose_price"].high) == (0.4, 0.3, 0.5)
    # A value with no range is held at itself, as the browser's assumption was.
    assert (inputs["plant_scale"].low, inputs["plant_scale"].high, inputs["plant_scale"].sampling) == (100000.0, 100000.0, "fixed")
    art = artifacts.get(r.artifactId)
    got = named(art)
    assert got["glucose_price"].source == basis.assumption_source(BY, "2026-10-21", "a STAND-IN for a test")
    assert [got[f"glucose_price {p}"].value for p in ("low", "high")] == [0.3, 0.5]
    # The run says it set values in the words the panel's overrides wrote, a convention.
    read = got[proforma.ASSUMPTIONS_READ]
    assert (read.value, read.unit, read.source.kind) == ("overrides", "", "convention")
    assert read.source.note == proforma.VALUES_READ_NOTE
    assert art.provenance == "assumed" and r.provenance == "assumed"


def test_an_override_replaces_the_records_for_its_input_and_reset_brings_them_back(standin):
    plain = proforma.run(asked(ECONOMICS, samples=8), pool=standin)
    titre = {i.key: i for i in plain.inputs}["titre"]
    assert titre.binding == "records" and len(titre.records) == 3
    typed = proforma.run(asked([*ECONOMICS, over("titre", 50.0, by=OTHER)], samples=8), pool=standin)
    t = {i.key: i for i in typed.inputs}["titre"]
    assert t.binding == "assumption" and t.value == 50.0 and t.source.by == OTHER and t.records == []
    assert "chosen in place of the 3 records it bound" in t.flags
    got = named(artifacts.get(typed.artifactId))
    assert "titre record" not in got and got["titre"].value == 50.0 and got["titre"].source.by == OTHER
    assert typed.artifactId != plain.artifactId
    # Reset to source: the same run without the override binds the records again, the same artifact.
    again = proforma.run(asked(ECONOMICS, samples=8), pool=standin)
    assert again.artifactId == plain.artifactId
    # The binding and the panel lay it on the same way.
    bound = {i.key: i for i in proforma.bound(ETHANOL, assumptions=proforma.named_values(None, [over("titre", 50.0)]),
                                              pool=standin).inputs}
    assert bound["titre"].binding == "assumption" and bound["titre"].value == 50.0
    resolved = {v.key: v for v in params.resolve_scope(SCOPE, resolve_request(SCOPE, overrides=[over("titre", 50.0)])).values}
    assert resolved["titre"].origin == "assumption" and resolved["titre"].value == 50.0


def test_an_override_wins_over_a_fermos_fit_for_its_input(standin, monkeypatch):
    called = []
    monkeypatch.setattr(proforma, "apply_fits", lambda inputs, fits, flowsheet: called.append(dict(fits)) or [])
    proforma.run(asked([*ECONOMICS, over("titre", 50.0)],
                       fits={"titre": "0123456789abcdef", "yield": "0123456789abcdef"}, samples=8), pool=standin)
    assert called == [{"yield": "0123456789abcdef"}], "the overridden input takes no fit"
    assert proforma.fits_beside({"titre": "a", "yield": "b"}, [assume("titre", 1.0)]) == {"yield": "b"}


@pytest.mark.parametrize("field", ["assumptions", "overrides"])
def test_the_older_fields_are_refused_as_any_unknown_field_is(standin, client, field):
    """The older `assumptions` field retired after its one release, as the
    panel's `overrides` did when a run took typed inputs (alpha 2.2 D2): a
    request that sends either is refused as a request with any field it does
    not name is, and nothing runs."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProformaRunRequest(scenarioId=HELD, **{field: []})
    r = client.post("/api/proforma/run", json={"scenarioId": HELD, "samples": 4, field: []})
    assert r.status_code == 422, r.json()
    assert [(e["type"], e["loc"]) for e in r.json()["detail"]] == [("extra_forbidden", ["body", field])]
    assert not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]


# The line the panel's overrides wrote at b6a85d0 (proforma.py's
# `assumptions_read` there), written out here word for word: a run that sets
# a value writes it.
def panel_line():
    """The basis input a run that read the panel's overrides wrote at b6a85d0."""
    from openferment_core.models import BasisInput, BasisSource

    return BasisInput(name="assumptions read from", value="overrides", unit="", source=BasisSource(
        kind="convention", note="where the named persons' values in this basis came from: the parameter panel's "
                                "overrides, and any the older assumptions field gave, which the service reads as "
                                "overrides for one release; a basis without this input read the older field alone"))


# Each run's artifact id through the panel's overrides at b6a85d0, measured
# there on these stand-ins, eight samples, no host drawing the diagram.
PANEL_IDS = {"held": "52e1bc2d2c215e81", "held with titre": "b1931d595489ef2e", "made here": "66845418720c7794"}


def test_a_panel_run_sent_as_inputs_keeps_the_artifact_id_its_overrides_gave(standin, monkeypatch):
    """Alpha 2.2 D6, the amendment at C.4: a run a person makes through the
    panel keeps the artifact id it had. The values sent as inputs convert to
    the very basis the panel's overrides wrote, each source's kind, person,
    note and day as before, and the line saying overrides were read; the
    Override form of each request, laid on and based as the run lays it on,
    gives the same id, the one b6a85d0 kept."""
    monkeypatch.setattr(proforma, "drawn_here", lambda: False)
    mh = f"proforma:{MADE_HERE}"
    cases = {
        "held": (HELD, None, ECONOMICS),
        "held with titre": (HELD, None, [*ECONOMICS, over("titre", 50.0, by=OTHER)]),
        "made here": (MADE_HERE, ETHANOL, [over("plant_scale", 100000.0, scope=mh),
                                           over("glucose_price", 0.4, 0.3, 0.5, scope=mh)]),
    }
    for name, (sid, flowsheet, typed) in cases.items():
        r = proforma.run(ProformaRunRequest(scenarioId=sid, flowsheet=flowsheet, inputs=proforma_inputs(typed),
                                            samples=8), pool=standin)
        bound = proforma.bind_inputs(ETHANOL, standin.records, None, proforma.named_values(sid, typed))
        panel = proforma.basis_inputs(bound, ETHANOL, 8, scenario_id=sid, fitted=[]) + [panel_line()]
        art = artifacts.get(r.artifactId)
        assert [i.model_dump() for i in art.inputs] == [i.model_dump() for i in panel], name
        assert artifacts.compute(proforma.RUN, panel, records_by_id=standin.records_by_id, seed=0).id == r.artifactId
        assert r.artifactId == PANEL_IDS[name], name
        # Each value's source as the panel's overrides wrote it: the person, the day and the note.
        assert named(art)["glucose_price"].source == basis.assumption_source(BY, "2026-10-21", "a STAND-IN for a test")
    # A run that sets no value writes no line: its basis is the binding's alone.
    assert proforma.values_read(False) == [] and proforma.values_read(True) == [panel_line()]


def test_a_models_estimate_bases_as_an_estimate_naming_the_model(standin, client):
    """ADR-006, recorded at C.4 (alpha 2.2 D6's amendment): a value a model
    sets is its estimate, and the basis names it so: its source is
    `model-estimate` with the model's id as `by`, its note the day it was
    estimated, and the run's sensitivity reads it as an estimate. Until C.4
    the binding based it as a person's assumption naming the model. The run
    is `assumed`. A model's id that runs over two lines is refused at
    Proforma's door in words, a blank one by the request's own origin, and
    nothing runs."""
    model = "placeholder-model-id"
    estimate = over("glucose_price", 0.4, 0.3, 0.5, by=model).model_copy(update={"origin": "model-estimate"})
    r = proforma.run(asked([ECONOMICS[0], estimate], samples=8), pool=standin)
    got = named(artifacts.get(r.artifactId))
    for name in ("glucose_price", "glucose_price low", "glucose_price high"):
        assert got[name].source == basis.estimate_source(model, "2026-10-21", "a STAND-IN for a test"), name
        assert got[name].source.kind == "model-estimate" and got[name].source.by == model
    assert got["plant_scale"].source.kind == "assumption"
    price = {i.key: i for i in r.inputs}["glucose_price"]
    assert price.binding == "assumption" and price.source.kind == "model-estimate" and price.source.by == model
    assert {s.key: s.sourceKind for s in r.sensitivity}["glucose_price"] == "model-estimate"
    assert r.provenance == "assumed" and artifacts.get(r.artifactId).provenance == "assumed"
    before = len([a for a in artifacts.all_artifacts() if a.tool == proforma.RUN])
    two_lines = estimate.model_copy(update={"by": "a-model\nsecond line"})
    words = "the estimate of glucose_price names the model that made it, on one line"
    with pytest.raises(proforma.ScenarioRefused, match=words):
        proforma.run(asked([ECONOMICS[0], two_lines], samples=4), pool=standin)
    answer = client.post("/api/proforma/run", json={"scenarioId": HELD, "samples": 4,
                                                    "inputs": sent([ECONOMICS[0], two_lines])})
    assert answer.status_code == 422 and answer.json()["detail"] == words, answer.json()
    blank = sent([ECONOMICS[0], estimate])
    blank[1]["quantity"]["origin"]["by"] = "   "
    answer = client.post("/api/proforma/run", json={"scenarioId": HELD, "samples": 4, "inputs": blank})
    assert answer.status_code == 422 and "a model-estimate names the model that estimated it (by)" in str(
        answer.json()["detail"]), answer.json()
    assert len([a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]) == before


def test_overrides_that_cannot_stand_are_refused_in_words(standin, client):
    for extra, words in (
        ([over("titre", "a lot")], "titre takes a number, and its value was sent as 'a lot'"),
        ([over("titre", 50.0), over("titre", 60.0)], "titre is set twice: a run sets each input once"),
        ([over("recovery", 0.9)], "ethanol_glucose_v0 takes no input recovery"),
        ([over("ethanol_purity", 1.0)], "ethanol_purity is a convention every run of ethanol_glucose_v0 states"),
        ([over("titre", 50.0, by="me")], "needs a person's name"),
        ([over("titre", 50.0, low=60.0)], "must lie within its own low and high"),
    ):
        with pytest.raises(proforma.ScenarioRefused, match=words.replace("(", r"\(")):
            proforma.run(asked([*ECONOMICS, *extra], samples=4), pool=standin)
        r = client.post("/api/proforma/run", json={"scenarioId": HELD, "samples": 4, "inputs": sent([*ECONOMICS, *extra])})
        assert r.status_code == 422 and words in r.json()["detail"], (extra, r.json())
    # A value typed in another unit than its input's is refused at the door, in the converter's words.
    wrong = proforma_inputs([over("titre", 50.0)])[0]
    wrong = wrong.model_copy(update={"quantity": wrong.quantity.model_copy(update={"unit": "placeholder-unit"})})
    with pytest.raises(proforma.ScenarioRefused, match="titre is set in 'placeholder-unit', and the parameter's unit is"):
        proforma.run(ProformaRunRequest(scenarioId=HELD, inputs=[*proforma_inputs(ECONOMICS), wrong], samples=4),
                     pool=standin)
    assert not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]


def test_the_endpoints_carry_inputs(standin, client):
    """Every door of Proforma takes a person's values as typed inputs (the
    plan's D6 amendment at C.4): the run's body, and `?inputs=` on the
    binding and the ceiling check, each converted at Proforma's door; the
    two reads refuse their retired fields in words naming `?inputs=`."""
    import json

    body = {"scenarioId": HELD, "samples": 4, "inputs": sent(ECONOMICS)}
    r = client.post("/api/proforma/run", json=body)
    assert r.status_code == 200
    art = artifacts.get(r.json()["artifactId"])
    assert named(art)["plant_scale"].source.by == BY and named(art)["plant_scale"].unit == "t yr-1"
    # GET /api/proforma/bind lays a person's values over the records, on the flowsheet's own scope.
    q = json.dumps(sent([over("titre", 50.0, scope=f"proforma:{ETHANOL}")]))
    b = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "inputs": q})
    assert b.status_code == 200, b.json()
    titre = next(i for i in b.json()["inputs"] if i["key"] == "titre")
    assert titre["binding"] == "assumption" and titre["value"] == 50.0 and titre["source"]["by"] == BY
    wrong_unit = sent([over("titre", 50.0)])
    wrong_unit[0]["quantity"]["unit"] = "placeholder-unit"
    for raw, words in (("[1]", "inputs is a JSON list of values"),
                       (json.dumps(wrong_unit), "titre is set in 'placeholder-unit', and the parameter's unit is"),
                       (json.dumps([{**sent([over("titre", 50.0)])[0], "name": "recovery"}]), "takes no input recovery")):
        bad = client.get("/api/proforma/bind", params={"flowsheet": ETHANOL, "inputs": raw})
        assert bad.status_code == 422 and words in bad.json()["detail"], (raw, bad.json())
    # The ceiling check reads the yield a person's value sets, records or not.
    y = json.dumps(sent([over("yield", 0.42)]))
    c = client.get("/api/proforma/ceiling-check", params={"scenarioId": HELD, "inputs": y})
    assert c.status_code == 200 and c.json()["yieldBinding"] == "assumption" and c.json()["yieldValue"] == 0.42
    # The retired fields are refused in words naming the field each read takes, and nothing is read.
    retired = json.dumps([over("yield", 0.42).model_dump()])
    for path, query in (("/api/proforma/ceiling-check", {"scenarioId": HELD, "overrides": retired}),
                        ("/api/proforma/ceiling-check", {"scenarioId": HELD, "assumptions": retired}),
                        ("/api/proforma/bind", {"flowsheet": ETHANOL, "overrides": retired})):
        gone = client.get(path, params=query)
        name = next(k for k in query if k in ("overrides", "assumptions"))
        assert gone.status_code == 422 and gone.json()["detail"].startswith(
            f"{name} is retired: this read takes the values a person sets as ?inputs="), (path, gone.json())


def test_resolve_warns_outside_the_bounds_and_keeps_the_value(standin, client):
    # D4: a yield outside its bounds (a physical limit: no negative yield) is
    # kept, never clamped, and said.
    r = client.post(f"/api/params/{SCOPE}/resolve", json={"inputs": resolve_json(SCOPE, [over("yield", -0.1)])})
    assert r.status_code == 200
    got = {v["key"]: v for v in r.json()["values"]}
    assert got["yield"]["value"] == -0.1 and got["yield"]["origin"] == "assumption" and got["yield"]["overriddenBy"] == BY
    assert r.json()["warnings"] == [got["yield"]["outOfBounds"]]
    assert "no negative" in got["yield"]["outOfBounds"] and "kept as given" in got["yield"]["outOfBounds"]
    # A run made with a value inside them binds the value as typed.
    run = proforma.run(asked([*ECONOMICS, over("yield", 0.45)], samples=4), pool=standin)
    assert {i.key: i for i in run.inputs}["yield"].value == 0.45


# ── OF-BLD-020 §2.R: the panel binds as the run binds ──────────────────


def test_the_panel_binds_as_the_run_binds_and_both_refuse_in_the_same_words(standin, client):
    """§2.R findings 0, 9 and 13: a forecast chosen for titre, yield and
    productivity, then titre typed by a person. The resolve used to bind
    without the person's values, so its refusal said titre binds records;
    it binds with them now, as the run does, and both refuse in the same
    words, which say the titre is the person's and the remedy that applies."""
    _, fc = standins._bridge_fits()
    every = {k: fc for k in proforma.FIT_KEYS}
    typed = [*ECONOMICS, over("titre", 50.0)]
    with pytest.raises(params.ParamRefused) as panel:
        params.resolve_scope(SCOPE, resolve_request(SCOPE, fits=every, overrides=typed))
    words = str(panel.value)
    assert "titre is a named person's assumption" in words and "titre binds" not in words, words
    assert "reset titre to its source" in words, words
    # What the page sends (the fits of the inputs no override names) and what the panel sends are refused alike.
    for fits in (every, {"yield": fc, "productivity": fc}):
        with pytest.raises(proforma.ScenarioRefused) as run:
            proforma.run(asked(typed, fits=fits, samples=4), pool=standin)
        assert str(run.value) == words
    r = client.post(f"/api/params/{SCOPE}/resolve", json={"fits": every, "inputs": resolve_json(SCOPE, typed)})
    assert r.status_code == 422 and r.json()["detail"] == words
    # Reset titre: the resolve binds every input to the forecast, as the run would.
    ok = params.resolve_scope(SCOPE, resolve_request(SCOPE, fits=every, overrides=ECONOMICS))
    assert {v.key: v.origin for v in ok.values if v.key in proforma.FIT_KEYS} == dict.fromkeys(proforma.FIT_KEYS, "fit")


def test_resolve_states_the_interval_and_the_basis_inputs_the_run_takes(standin, client):
    """§2.R findings 1, 14, 3 and 19: one end of an interval typed and the
    other left empty is the value itself, the same in the resolve and the
    run; and the basis inputs the resolve says the overrides add are the
    ones the run's basis takes for the same overrides, from one function."""
    typed = [over("titre", 50.0, low=40.0), over("plant_scale", 100000.0), over("glucose_price", 0.4, 0.3, 0.5)]
    r = params.resolve_scope(SCOPE, resolve_request(SCOPE, overrides=typed))
    got = {v.key: v for v in r.values}
    held = {a.key: a for a in proforma.named_values(HELD, typed)}
    assert (got["titre"].low, got["titre"].high) == (held["titre"].low, held["titre"].high) == (40.0, 50.0)
    # With neither end it is held at itself: no interval on the panel, both ends the value in the run.
    assert (got["plant_scale"].low, got["plant_scale"].high) == (None, None)
    assert (held["plant_scale"].low, held["plant_scale"].high) == (100000.0, 100000.0)
    up = params.resolve_scope(SCOPE, resolve_request(SCOPE, overrides=[over("titre", 50.0, high=70.0)]))
    assert next((v.low, v.high) for v in up.values if v.key == "titre") == (50.0, 70.0)
    run = proforma.run(asked(typed, samples=4), pool=standin)
    added = [i for i in artifacts.get(run.artifactId).inputs
             if i.source.kind == "assumption" or i.name == proforma.ASSUMPTIONS_READ]
    assert [i.model_dump() for i in r.basisInputs] == [i.model_dump() for i in added]
    assert [i.name for i in r.basisInputs][:3] == ["titre", "titre low", "titre high"]
    body = client.post(f"/api/params/{SCOPE}/resolve", json={"inputs": resolve_json(SCOPE, typed)}).json()
    assert [i["name"] for i in body["basisInputs"]] == [i.name for i in added]


def test_an_override_of_a_convention_is_refused_by_the_resolve_as_by_the_run(standin, client):
    """§2.R findings 2 and 18: the resolve accepted a person's value for a
    convention every run states, which every run refuses."""
    o = over("ethanol_purity", 0.5)
    with pytest.raises(params.ParamRefused, match="ethanol_purity is a convention, fuel grade") as refused:
        params.resolve_scope(SCOPE, resolve_request(SCOPE, overrides=[o]))
    assert "takes no person's value" in str(refused.value)
    r = client.post(f"/api/params/{SCOPE}/resolve", json={"inputs": resolve_json(SCOPE, [o])})
    assert r.status_code == 422 and "ethanol_purity is a convention" in r.json()["detail"]
    with pytest.raises(proforma.ScenarioRefused, match="ethanol_purity is a convention"):
        proforma.run(asked([*ECONOMICS, o], samples=4), pool=standin)


def test_a_persons_value_wins_over_the_records_and_moves_the_artifact_id(standin):
    """§2.R finding 4: a person's value of an input that binds records wins
    over them (D3), so the binding, the basis and the id change."""
    old = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]
    plain = proforma.run(ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs(old), samples=8), pool=standin)
    typed = proforma.run(ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs([*old, assume("titre", 50.0)]),
                                            samples=8), pool=standin)
    t = {i.key: i for i in typed.inputs}["titre"]
    assert t.binding == "assumption" and t.value == 50.0 and "chosen in place of the 3 records it bound" in t.flags
    assert typed.artifactId != plain.artifactId
    got = named(artifacts.get(typed.artifactId))
    assert "titre record" not in got and got["titre"].source.by == BY


def test_a_run_refuses_an_override_that_does_not_say_when_it_was_typed(standin, client):
    """§2.R finding 5: the resolve refused an override with no `at`, the run
    kept one, and its basis named no day. Since alpha 2.2 (D2) the run and
    the resolve take each value as a typed input, which is refused as it is
    read when it says no day."""
    unit = scope_units(SCOPE)["glucose_price"]
    for at in ("", "   "):
        blank = over("glucose_price", 0.4).model_copy(update={"at": at})
        with pytest.raises(ValidationError, match="glucose_price: a value a run sets says when it was set"):
            as_input(blank, unit)
        body = {"name": "glucose_price", "quantity": {"value": 0.4, "unit": unit,
                                                      "origin": {"kind": "person-assumption", "by": BY, "at": at}}}
        for route, sent_ in ((f"/api/params/{SCOPE}/resolve", {"inputs": [body]}),
                             ("/api/proforma/run", {"scenarioId": HELD, "samples": 4, "inputs": [body]})):
            r = client.post(route, json=sent_)
            assert r.status_code == 422 and "says when it was set" in str(r.json()["detail"]), route
    assert not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]
