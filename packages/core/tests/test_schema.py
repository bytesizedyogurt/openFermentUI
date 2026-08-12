"""Tests for the canonical schema.

These are not exhaustive coverage of Pydantic — they check the handful of things
this schema promises that a reader would otherwise have to take on trust, and the
places where a port most easily goes wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openferment_core import schema as S

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "schema-instances.json"


@pytest.fixture(scope="module")
def seeded() -> dict[str, list[dict[str, object]]]:
    return json.loads(FIXTURES.read_text("utf-8"))


# ── the corpus parses ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("key", "model"),
    [
        ("papers", S.Paper),
        ("records", S.ExtractionRecord),
        ("strains", S.Strain),
        ("protocols", S.Protocol),
        ("ontology", S.ParameterDef),
        ("scenarios", S.Scenario),
        ("learnModules", S.LearnModule),
    ],
)
def test_every_seeded_instance_parses(seeded, key, model) -> None:  # type: ignore[no-untyped-def]
    """Where a real corpus instance fails, the model is wrong, not the data."""
    for raw in seeded[key]:
        model.model_validate(raw)


# ── invariant 3: isAggregatable is the single gate ─────────────────────


def _record(**over: object) -> S.ExtractionRecord:
    base: dict[str, object] = {
        "id": "r-test-1",
        "paperId": "H4",
        "sectionId": "s1",
        "quote": "a quoted span",
        "field": "titer_secreted",
        "value": 1.0,
        "unit": "g L⁻¹",
        "si": {"value": 1.0, "unit": "kg m⁻³"},
        "confidence": 0.9,
        "status": "unverified",
        "provenance": "curated",
        "audit": [],
        "isPrimary": True,
        "evidenceClass": "literature",
    }
    base.update(over)
    return S.ExtractionRecord.model_validate(base)


def test_aggregatable_by_default() -> None:
    assert _record().isAggregatable() is True
    assert _record().aggregateExclusion() is None


def test_rejected_record_is_excluded() -> None:
    r = _record(status="rejected")
    assert r.isAggregatable() is False
    assert r.aggregateExclusion() == "rejected"


def test_industry_estimate_never_enters_an_aggregate() -> None:
    """OF-COR-001 §16 O8. Useful for framing, useless as evidence."""
    r = _record(provenance="industry-estimate")
    assert r.isAggregatable() is False
    assert r.aggregateExclusion() == "industry-estimate"


def test_citation_of_a_citation_is_excluded() -> None:
    """A paper reciting someone else's number is not an independent measurement."""
    r = _record(isPrimary=False)
    assert r.isAggregatable() is False
    assert r.aggregateExclusion() == "not-primary"


def test_exclusion_order_matches_the_typescript() -> None:
    """Rejected wins over industry-estimate wins over not-primary.

    The reason string is displayed, so which one a multiply-excluded record
    reports is a visible behaviour and not an implementation detail.
    """
    r = _record(status="rejected", provenance="industry-estimate", isPrimary=False)
    assert r.aggregateExclusion() == "rejected"


def test_validate_assignment_re_runs_the_gate() -> None:
    """Editing provenance after construction must change aggregatability."""
    r = _record()
    assert r.isAggregatable() is True
    r.provenance = S.Provenance.INDUSTRY_ESTIMATE
    assert r.isAggregatable() is False


# ── invariant 1: enum values match the TypeScript exactly ──────────────


def test_hyphenated_and_spaced_enum_values_survive() -> None:
    """The values with punctuation in them are the ones a port loses."""
    assert S.Provenance.INDUSTRY_ESTIMATE.value == "industry-estimate"
    assert S.AnalysisMethod.UREA_PAGE_PHOSPHATASE.value == "urea-PAGE + phosphatase"
    assert S.AnalysisMethod.LC_ESI_MS.value == "LC-ESI-MS"
    assert S.AnalysisMethod.SDS_PAGE_MOBILITY.value == "SDS-PAGE mobility"
    assert S.AnalysisMethod.ETHYL_STAINS_ALL.value == "Ethyl Stains-All"
    assert S.AnalysisMethod.PROCESS_MODEL.value == "process model"
    assert S.ScalingClass.PER_BATCH_VOLUME.value == "per_batch_volume"
    assert S.SourceType.INDUSTRY_REPORT.value == "industry-report"


def test_undetermined_is_a_first_class_analysis_method() -> None:
    """Absence of measurement is not measurement of absence (OF-COR-001 §17)."""
    assert S.AnalysisMethod.UNDETERMINED.value == "undetermined"
    assert _record(method="undetermined").method is S.AnalysisMethod.UNDETERMINED


def test_ingest_status_enumerates_every_stage() -> None:
    """The TypeScript writes these as a template literal over IngestStage.

    JSON Schema cannot express that, so they are written out — and if IngestStage
    grows a member, this test is what notices that IngestStatus did not.
    """
    for stage in S.IngestStage:
        assert f"stage:{stage.value}" in {s.value for s in S.IngestStatus}


# ── invariant 4: sentinels stay ────────────────────────────────────────


def test_year_zero_is_accepted() -> None:
    """`year: 0` means unknown. A model that rejected it would force a guess."""
    paper = S.Paper.model_validate(
        {
            "id": "X1",
            "title": "Unknown year",
            "authors": [],
            "year": 0,
            "venue": "",
            "organisms": [],
            "topics": [],
            "abstract": "",
            "sections": [],
            "ingest": "catalogued",
            "thread": "A",
            "sourceType": "journal-article",
            "textSource": "curation-note",
            "openAccess": False,
            "tranche": 2,
        }
    )
    assert paper.year == 0


# ── strictness ─────────────────────────────────────────────────────────


def test_unknown_field_is_rejected() -> None:
    """extra='forbid' is what makes validating the corpus mean anything."""
    with pytest.raises(ValidationError):
        _record(somethingNobodyDeclared=1)


def test_unknown_enum_member_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _record(provenance="probably-fine")


# ── discriminated unions ───────────────────────────────────────────────


def test_assumption_basis_discriminates() -> None:
    a = S.ScenarioAssumption.model_validate(
        {
            "label": "Secreted titer",
            "value": 1.0,
            "unit": "g L⁻¹",
            "provenance": "curated",
            "basis": {"kind": "record", "recordId": "r-K1-1"},
            "note": "",
        }
    )
    assert isinstance(a.basis, S.BasisRecord)
    assert a.basis.record_id == "r-K1-1"

    b = S.ScenarioAssumption.model_validate(
        {
            "label": "Capital charge",
            "value": 0.12,
            "unit": "",
            "provenance": "demo",
            "basis": {"kind": "model", "justification": "financial convention"},
            "note": "",
        }
    )
    assert isinstance(b.basis, S.BasisModel)


def test_unsourced_basis_is_expressible_because_it_is_a_defect_class() -> None:
    """The schema must be able to say "this number has nothing behind it".

    A schema that could not express the defect could not report it either.
    """
    a = S.ScenarioAssumption.model_validate(
        {
            "label": "Media share of COGS",
            "value": 42.0,
            "unit": "%",
            "provenance": "industry-estimate",
            "basis": {"kind": "unsourced"},
            "note": "",
        }
    )
    assert isinstance(a.basis, S.BasisUnsourced)


# ── round trip ─────────────────────────────────────────────────────────


def test_round_trip_uses_camel_case_on_the_wire(seeded) -> None:  # type: ignore[no-untyped-def]
    raw = seeded["records"][0]
    parsed = S.ExtractionRecord.model_validate(raw)
    emitted = parsed.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert "isPrimary" in emitted
    assert "is_primary" not in emitted
    assert emitted["id"] == raw["id"]
