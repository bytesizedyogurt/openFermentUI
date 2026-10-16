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


def test_an_assumption_input_gives_demo():
    assert _p(_input("record", "r-gold"), _input("assumption", note="a guess", by="Sean Creighton")) == "demo"


def test_an_assumption_outweighs_every_other_input():
    assert _p(_input("deposition", "d-1"), _input("model", "m"), _input("assumption", by="Sean Creighton")) == "demo"


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
    assert _p(_input("record", "r-nowhere")) == "demo"
    assert _p(_input("artifact", "a-nowhere")) == "demo"


def test_computed_sits_after_every_experimental_class_and_before_unverified():
    i = PROVENANCE_ORDER.index("computed")
    assert PROVENANCE_ORDER[:i] == ["measured", "gold", "verified", "curated"]
    assert PROVENANCE_ORDER[i + 1] == "unverified"
    assert set(PROVENANCE_ORDER) == set(Provenance.__args__)
