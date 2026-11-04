"""The provenance of a computed value (OF-BLD-014 §3.1, E.4)."""
from __future__ import annotations

from openferment_core.basis import basis_provenance
from openferment_core.models import (
    PROVENANCE_ORDER,
    BasisInput,
    BasisSource,
    ComputedBasis,
    Provenance,
)

RECORDS = {
    "r-gold": {"provenance": "gold"},
    "r-verified": {"provenance": "verified"},
    "r-unverified": {"provenance": "unverified"},
    "r-industry": {"provenance": "industry-estimate"},
}
ARTIFACTS = {
    "a-computed": {"provenance": "computed"},
    "a-unverified": {"provenance": "unverified"},
}


def _input(kind: str, id: str | None = None, **source) -> BasisInput:
    return BasisInput(name=f"in-{kind}-{id}", value="x", unit="", source=BasisSource(kind=kind, id=id, **source))


def _basis(*inputs: BasisInput) -> ComputedBasis:
    return ComputedBasis(tool="t", toolVersion="v", inputs=list(inputs), artifactId="a", at="2026-10-14T00:00:00Z")


def _p(*inputs: BasisInput) -> str:
    return basis_provenance(_basis(*inputs), RECORDS, ARTIFACTS)


def test_an_assumption_input_gives_assumed():
    assert _p(_input("record", "r-gold"), _input("assumption", note="a guess", by="Sean Creighton")) == "assumed"


def test_an_assumption_outweighs_every_other_input():
    assert _p(_input("deposition", "d-1"), _input("model", "m"), _input("assumption", by="Sean Creighton")) == "assumed"


def test_an_unverified_record_input_gives_unverified():
    assert _p(_input("record", "r-gold"), _input("record", "r-unverified")) == "unverified"


def test_strong_record_inputs_leave_the_value_computed():
    # A calculation on gold and verified records is still a calculation.
    assert _p(_input("record", "r-gold"), _input("record", "r-verified")) == "computed"


def test_an_industry_estimate_input_carries_through():
    assert _p(_input("record", "r-industry")) == "industry-estimate"


def test_a_deposition_input_gives_computed():
    assert _p(_input("deposition", "d-1")) == "computed"


def test_model_and_convention_inputs_change_nothing():
    assert _p(_input("model", "iJO1366"), _input("convention", note="uptake normalised to one")) == "computed"
    assert _p(_input("record", "r-unverified"), _input("model", "iJO1366")) == "unverified"


def test_no_inputs_is_computed():
    assert _p() == "computed"


def test_an_artifact_input_passes_its_own_provenance_through():
    assert _p(_input("artifact", "a-unverified")) == "unverified"
    assert _p(_input("artifact", "a-computed")) == "computed"


def test_an_artifact_object_is_read_like_a_dict():
    class A:
        provenance = "unverified"

    assert basis_provenance(_basis(_input("artifact", "x")), {}, {"x": A()}) == "unverified"


def test_a_source_that_cannot_be_found_is_the_weakest_there_is():
    assert _p(_input("record", "r-nowhere")) == "assumed"
    assert _p(_input("artifact", "a-nowhere")) == "assumed"


def test_computed_sits_after_every_experimental_class_and_before_unverified():
    i = PROVENANCE_ORDER.index("computed")
    assert PROVENANCE_ORDER[:i] == ["measured", "gold", "verified", "curated"]
    assert PROVENANCE_ORDER[i + 1] == "unverified"
    assert set(PROVENANCE_ORDER) == set(Provenance.__args__)


# ── the one converter: a typed quantity with its origin to an Override (alpha 2.2 D2) ──

import pytest  # noqa: E402

from openferment_core import artifacts, params  # noqa: E402
from openferment_core.basis import InputRefused, override_of  # noqa: E402
from openferment_core.models import EngineInput, Origin, Override, ParameterSpec, Quantity  # noqa: E402

# A placeholder parameter in a placeholder unit, and a value set on it with
# every field an Override holds.
SCOPE = "fermos:family:batch_v1"
UNIT = "placeholder-unit"
SPEC = ParameterSpec(key="a_parameter", label="A parameter", symbol="", gloss="a placeholder", dimension="",
                     unit=UNIT, min=0.0, group="placeholders", sourceRule=["assumption"],
                     boundsReason="a placeholder bound: nothing below none")
EVERY_FIELD = {
    "person-assumption": Override(scope=SCOPE, key="a_parameter", value=2.0, low=1.0, high=3.0, by="Ada Moreno",
                                  at="2026-10-21", note="a placeholder note", origin="person-assumption"),
    "model-estimate": Override(scope=SCOPE, key="a_parameter", value=2.0, low=1.0, high=3.0,
                               by="a-placeholder-model", at="2026-10-21T09:00:00Z", note="a placeholder note",
                               origin="model-estimate"),
}


def _sent(o: Override) -> EngineInput:
    """An Override as the browser sends it (src/lib/params.ts, `inputsOf`):
    its key, a quantity in its parameter's unit holding its value, low and
    high, and an origin holding its person or model, day and note."""
    return EngineInput.model_validate({"name": o.key, "quantity": {
        "value": o.value, "unit": UNIT, "low": o.low, "high": o.high,
        "origin": {"kind": o.origin, "by": o.by, "at": o.at, "note": o.note}}})


@pytest.mark.parametrize("origin", sorted(EVERY_FIELD))
def test_an_override_sent_as_its_input_comes_back_the_same_override_field_for_field(origin):
    o = EVERY_FIELD[origin]
    # Every field a person's or a model's value fills; `ref` names a measurement's reading alone.
    assert all(getattr(o, f) is not None for f in Override.model_fields if f != "ref"), "every field is set"
    assert o.ref is None
    back = override_of(SCOPE, _sent(o), UNIT)
    for field in Override.model_fields:
        assert getattr(back, field) == getattr(o, field), field
    assert back == o
    # So its run has the same artifact id: the basis a run writes for it is the same, input for input.
    basis = params.basis_inputs([SPEC], params.resolve([SPEC], {}, [o]))
    again = params.basis_inputs([SPEC], params.resolve([SPEC], {}, [back]))
    assert again == basis and artifacts.artifact_id("a.placeholder", "placeholder 1", again) == \
        artifacts.artifact_id("a.placeholder", "placeholder 1", basis)


def test_a_quantity_in_another_unit_or_with_a_basis_of_its_own_is_refused_in_words():
    sent = _sent(EVERY_FIELD["person-assumption"])
    with pytest.raises(InputRefused, match="a_parameter is set in 'placeholder-unit', and the parameter's unit is "
                                           "'another-unit'"):
        override_of(SCOPE, sent, "another-unit")
    reckoned = sent.model_copy(update={"quantity": sent.quantity.model_copy(update={"basis": "a placeholder basis"})})
    with pytest.raises(InputRefused, match="also carries the basis 'a placeholder basis'"):
        override_of(SCOPE, reckoned, UNIT)


@pytest.mark.parametrize("origin", [Origin(kind="record", ref="r-placeholder"),
                                    Origin(kind="artifact", ref="a-placeholder"),
                                    Origin(kind="library-default", ref="a-package@1"),
                                    Origin(kind="convention", note="a placeholder convention"), None])
def test_a_value_no_person_or_model_set_is_refused_in_words(origin):
    # EngineInput refuses these itself; the converter holds its own rule for
    # an input made past that check.
    made = EngineInput.model_construct(name="a_parameter", quantity=Quantity(value=2.0, unit=UNIT, origin=origin))
    with pytest.raises(InputRefused, match="a value a run sets is a person's assumption or a model's estimate"):
        override_of(SCOPE, made, UNIT)


def test_a_value_that_does_not_say_when_it_was_set_is_refused_in_words():
    undated = EngineInput.model_construct(name="a_parameter", quantity=Quantity(
        value=2.0, unit=UNIT, origin=Origin(kind="person-assumption", by="Ada Moreno")))
    with pytest.raises(InputRefused, match="says when it was set"):
        override_of(SCOPE, undated, UNIT)


def test_a_name_the_scope_has_no_parameter_for_is_refused_before_it_is_converted():
    sent = _sent(EVERY_FIELD["person-assumption"])
    with pytest.raises(params.ParamRefused, match="there is no parameter a_parameter here; the parameters are "
                                                  "another_parameter"):
        params.overrides_of(SCOPE, [sent], {"another_parameter": UNIT})
    assert params.overrides_of(SCOPE, [sent], params.units_of([SPEC])) == [EVERY_FIELD["person-assumption"]]


# ── the measurement origin: a deposition's reading a run sets (ADR-006, the note of 2026-11-03) ──

from openferment_core import project_state  # noqa: E402
from openferment_core.basis import is_measurement, measurement_source, origin_of  # noqa: E402

# A placeholder reading, as a person deposits one at the bench, and who deposited it.
DEPOSITOR = "Ada Moreno"
TAKEN = "2026-11-03T09:10:00Z"
READING = "dep-b1/de-1"


def _reading(**over) -> BasisInput:
    return BasisInput(name="in-measurement", value=2.0, unit=UNIT,
                      source=measurement_source(over.get("ref", READING), DEPOSITOR, TAKEN, over.get("note")))


ARTIFACTS["a-assumed"] = {"provenance": "assumed"}


def test_a_measurement_is_a_deposition_naming_its_reading_and_when_it_was_taken():
    src = measurement_source(READING, DEPOSITOR, TAKEN, "a placeholder note")
    assert (src.kind, src.id, src.by, src.note) == ("deposition", READING, DEPOSITOR,
                                                    f"measured on {TAKEN}: a placeholder note")
    assert is_measurement(src)
    o = origin_of(src)
    assert (o.kind, o.ref, o.by, o.at) == ("measurement", READING, DEPOSITOR, TAKEN)
    # A deposition naming a whole series (the readings a kinetic fit is made on) is the bench's record, as it was.
    series = BasisSource(kind="deposition", id="d-1", note="the readings as the browser sent them")
    assert not is_measurement(series) and origin_of(series).kind == "record"


def test_a_run_resting_on_a_measurement_records_and_defaults_alone_is_measured():
    assert _p(_reading()) == "measured"
    assert _p(_reading(), _input("model", "a-package@1"), _input("convention", note="a placeholder")) == "measured"
    # Records of any class stand beside a measurement (the prompt's §6.3: measurements and records alone).
    assert _p(_reading(), _input("record", "r-unverified"), _input("record", "r-gold")) == "measured"
    assert _p(_reading(), _input("artifact", "a-computed")) == "measured"


def test_a_measurement_beside_an_assumption_or_an_estimate_stays_assumed():
    assert _p(_reading(), _input("assumption", by=DEPOSITOR)) == "assumed"
    assert _p(_reading(), _input("model-estimate", by="a-placeholder-model")) == "assumed"
    # So does one beside an artifact that is assumed itself, or a source the caller cannot find.
    assert _p(_reading(), _input("artifact", "a-assumed")) == "assumed"
    assert _p(_reading(), _input("record", "r-nowhere")) == "assumed"


def test_the_packages_own_run_carries_neither_label():
    package = _input("model", "a-package@1")
    assert _p(package, _input("convention", note="the digits it keeps")) == "computed"
    assert _p() == "computed"


def _deposit(entries: list[dict], deposition_id: str = "dep-b1", **over) -> None:
    project_state.put("depositions", deposition_id, {
        "id": deposition_id, "runbookId": "rb-b1", "protocolId": "pr-b1", "operatorId": None, "state": "running",
        "startedAt": "2026-11-03T08:00:00Z", "closedAt": None, "entries": entries, "observations": [],
        "reconciliation": None, **over}, by=DEPOSITOR)


def _entry(entry_id: str = "de-1", value: float = 2.0, unit: str = UNIT, **over) -> dict:
    return {"id": entry_id, "measureId": "m-placeholder", "stepId": "s-1", "at": TAKEN, "value": value, "unit": unit,
            "raw": "a placeholder reading", "confirmed": True, **over}


def _measured(value: float = 2.0, unit: str = UNIT, **origin) -> EngineInput:
    return EngineInput.model_validate({"name": "a_parameter", "quantity": {
        "value": value, "unit": unit, "origin": {"kind": "measurement", "ref": READING, **origin}}})


def test_the_one_converter_looks_a_reading_up_and_makes_its_override_with_the_reading_as_its_source():
    _deposit([_entry()])
    o = override_of(SCOPE, _measured(note="a placeholder note"), UNIT)
    assert (o.origin, o.ref, o.by, o.at, o.value, o.note) == ("measurement", READING, DEPOSITOR, TAKEN, 2.0,
                                                              "a placeholder note")
    values = params.resolve([SPEC], {}, [o])
    assert (values[0].origin, values[0].overriddenBy) == ("measurement", DEPOSITOR)
    (made,) = params.basis_inputs([SPEC], values)
    assert made.source == measurement_source(READING, DEPOSITOR, TAKEN, "a placeholder note")
    assert basis_provenance(_basis(made), {}, {}) == "measured"


def test_the_one_converter_refuses_a_reading_the_project_does_not_hold_in_words():
    with pytest.raises(InputRefused, match="a_parameter: the project holds no deposition dep-b1"):
        override_of(SCOPE, _measured(), UNIT)
