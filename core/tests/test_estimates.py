"""A model's estimate (ADR-006; execution prompt §4.6; acceptance A6).

A number a model supplies enters as a `Quantity` whose origin names the
model, and an `Override` whose origin is `model-estimate`. It reaches a run:
the run's basis names the model, and the run is `assumed`, as it is on a
person's assumption. It never reaches a record: each record store (BioRepo's
decisions, the candidates, a project's depositions and measurements) refuses
one planted in what it is asked to keep, writes nothing, and says why. An
assumed value is never averaged into evidence.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, basis, binding, biorepo, extract, project_state
from openferment_core.engine import library
from openferment_core.models import (
    BasisInput,
    BasisSource,
    Candidate,
    ComputedBasis,
    ExtractResponse,
    Origin,
    Override,
    Quantity,
    ReviewDecision,
    Usage,
)

MODEL = "claude-opus-5-5"
AT = "2026-10-30T12:00:00Z"
ESTIMATE = Origin(kind="model-estimate", by=MODEL, at=AT, note="a typical titre for this host")


def client() -> TestClient:
    return TestClient(api.app, base_url="http://127.0.0.1")


def estimated(value: float, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit, origin=ESTIMATE)


def test_a_quantity_names_its_origin_and_a_bare_one_is_written_as_before():
    assert Quantity(value=1.5, unit="g L-1").model_dump(mode="json") == {"value": 1.5, "unit": "g L-1"}
    held = estimated(1.5, "g L-1").model_dump(mode="json")
    assert held["origin"]["kind"] == "model-estimate" and held["origin"]["by"] == MODEL
    assert Quantity.model_validate(held) == estimated(1.5, "g L-1")
    with pytest.raises(ValueError, match="names the model that estimated it"):
        Origin(kind="model-estimate", at=AT)
    with pytest.raises(ValueError, match="names the person who typed it"):
        Origin(kind="person-assumption", by="  ")
    with pytest.raises(ValueError, match="names what it was read from"):
        Origin(kind="record")


def test_an_estimate_in_a_basis_makes_the_value_assumed_and_names_the_model():
    source = basis.estimate_source(MODEL, AT, "a typical titre")
    assert source.kind == "model-estimate" and source.by == MODEL and source.note == f"estimated on {AT}: a typical titre"
    b = ComputedBasis(tool="t", toolVersion="1", artifactId="a", at=AT, inputs=[
        BasisInput(name="titre", value=1.5, unit="g L-1", source=source)])
    assert basis.basis_provenance(b, {}, {}) == "assumed"
    origin = basis.origin_of(source)
    assert (origin.kind, origin.by, origin.at) == ("model-estimate", MODEL, AT)


def test_an_override_is_a_persons_assumption_unless_it_says_it_is_a_models_estimate():
    person = Override(scope="s", key="k", value=1.0, by="Ada Moreno", at="2026-10-30")
    model = person.model_copy(update={"by": MODEL, "at": AT, "origin": "model-estimate"})
    assert person.origin == "person-assumption" and basis.override_source(person).kind == "assumption"
    assert basis.override_source(model).kind == "model-estimate" and basis.override_source(model).by == MODEL
    assert [basis.origin_of(basis.override_source(o)).kind for o in (person, model)] == [
        "person-assumption", "model-estimate"]


def test_an_estimate_reaches_a_library_run_and_the_run_is_assumed(monkeypatch):
    """The run's basis names the model as the source of its value; the
    value goes to the worker as a person's would."""
    shelf = library.shelf()
    entry = next(p for p in shelf.plants if p.kind == "flowsheet")
    spec = library.ParameterSpec(key="stream.cornstover.price", label="price", symbol="", gloss="g", dimension="number",
                                 unit="USD/kg", group="Streams", sourceRule=["library-default"], boundsReason="r")
    monkeypatch.setattr(library, "parameters", lambda plant, configuration=None: library.LibraryParameters(
        plant=plant, configuration=configuration, scope=library.scope(plant, configuration), found={},
        specs=[spec], values=[], simulator="biosteam", package="biorefineries"))
    o = Override(scope=library.scope(entry.id, None), key=spec.key, value=0.08, by=MODEL, at=AT, origin="model-estimate")
    inputs = library.run_inputs(entry.id, None, [o])
    price = next(i for i in inputs if i.name == spec.key)
    assert price.source.kind == "model-estimate" and price.source.by == MODEL
    assert library._overrides_of(inputs) == {spec.key: 0.08}
    b = ComputedBasis(tool=library.LIBRARY_RUN, toolVersion=library.LIBRARY_RUN_VERSION, artifactId="a", at=AT,
                      inputs=inputs)
    assert basis.basis_provenance(b, {}, {}) == "assumed"
    with pytest.raises(library.LibraryRefused, match="model that estimated it"):
        library.run_inputs(entry.id, None, [o.model_copy(update={"by": " "})])


def test_a_parameter_panel_takes_an_estimate_naming_its_model_and_says_so():
    from openferment_core import params

    spec = params.ParameterSpec(key="mu_max", label="μmax", symbol="μ", gloss="g", dimension="rate", unit="h⁻¹",
                                group="Growth", sourceRule=["fit", "assumption"], boundsReason="r", min=0.0)
    o = Override(scope="fermos:family:monod", key="mu_max", value=0.3, by=MODEL, at=AT, origin="model-estimate")
    kept = params.checked([spec], [o])["mu_max"]
    value = params._from_override(spec, kept)
    assert value.origin == "model-estimate" and value.source.kind == "model-estimate"
    assert value.overriddenBy == MODEL and value.detail.startswith(f"estimated by {MODEL}")
    with pytest.raises(params.ParamRefused, match="names the model that made it"):
        params.checked([spec], [o.model_copy(update={"by": ""})])


@pytest.mark.parametrize("field", ["corrected", "gold"])
def test_biorepo_refuses_a_decision_carrying_a_models_estimate(field):
    d = ReviewDecision(status="verified", provenance="verified", reviewer="Ada Moreno", recordId="cl1-T7-0a1b2c3d",
                       at=AT, **{field: estimated(3.0, "mg L-1")})
    for dry_run in (True, False):
        with pytest.raises(biorepo.WriteRefused) as caught:
            biorepo.write(d, dry_run=dry_run)
        assert caught.value.rule == "estimate" and f"{field}.origin" in caught.value.why
    assert biorepo.read().decisions == {}


def test_biorepo_refuses_a_decision_that_calls_itself_assumed():
    d = ReviewDecision(status="verified", provenance="assumed", reviewer="Ada Moreno", recordId="cl1-T7-0a1b2c3d", at=AT)
    with pytest.raises(biorepo.WriteRefused, match="estimate"):
        biorepo.write(d)


def test_the_decisions_route_refuses_an_estimate_with_its_rule():
    d = ReviewDecision(status="verified", provenance="verified", reviewer="Ada Moreno", recordId="cl1-T7-0a1b2c3d",
                       at=AT, corrected=estimated(3.0, "mg L-1"))
    r = client().post("/api/biorepo/decisions", json=d.model_dump(mode="json"))
    assert r.status_code == 422 and r.json()["detail"].startswith("estimate:")


def test_the_candidates_store_refuses_a_candidate_carrying_a_models_estimate():
    c = Candidate(id="cl1-T7-0a1b2c3d", paperId="T7", sectionId="s1", quote="titre 3 mg L-1", field="titer_secreted",
                  value=3, unit="mg L-1", si=Quantity(value=0.003, unit="g L-1", origin=ESTIMATE))
    result = ExtractResponse(paperId="T7", extractedAt=AT, candidates=[c], audit=[], usage=Usage(), calls=0)
    with pytest.raises(basis.EstimateRefused, match="candidates store"):
        extract._persist(result)
    assert extract.cached("T7") is None


@pytest.mark.parametrize("kind", ["depositions", "measuredEvidence"])
def test_a_projects_bench_records_refuse_a_models_estimate(kind):
    value = {"id": "dep-1", "runbookId": "rb-1", "entries": [
        {"step": "s1", "quantity": estimated(7.2, "g L-1").model_dump(mode="json")}]}
    with pytest.raises(project_state.StateRefused, match="never a record"):
        project_state.put(kind, "dep-1", value, "Ada Moreno")
    assert project_state.load()[kind] == []
    r = client().put(f"/api/state/{kind}/dep-1", json={"value": value, "by": "Ada Moreno"})
    assert r.status_code == 422 and "never a record" in r.json()["detail"]


def test_a_scenarios_overrides_take_an_estimate():
    """An estimate may reach a scenario: a project keeps an override whose
    origin is a model's estimate, as it keeps a person's."""
    scope = "proforma:sc-1"
    o = Override(scope=scope, key="price", value=1.2, by=MODEL, at=AT, origin="model-estimate").model_dump(mode="json")
    project_state.put("overrides", scope, [o], "Ada Moreno")
    assert project_state.load()["overrides"] == {scope: [o]}


def test_an_assumed_value_is_never_averaged_into_evidence():
    assert binding.exclusion({"provenance": "assumed", "status": "verified"}) == "assumed"
    assert binding.exclusion({"provenance": "verified", "status": "verified"}) is None
    assert basis.estimate_in({"provenance": "verified", "value": 1.0}) is None
    assert basis.estimate_in([{"source": BasisSource(kind="model-estimate", by=MODEL).model_dump()}]) == "[0].source"
