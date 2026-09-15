"""Extraction, offline (OF-BLD-012 §6.1, §6.3).

The model call is stubbed — `call_model` is replaced with a function that
returns a hand-written tool input — so every rule around the call is pinned
without spending a token: what the prompt and tool contain, how a section is
cut, what happens to the candidates the stub returns, what is persisted, and
what the endpoint answers when there is nothing to anchor to.

The live test that actually calls Haiku is test_extract_live.py, marked live.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import biorepo, extract, intake
from openferment_core.api import app
from openferment_core.models import ExtractResponse, Usage
from openferment_core.units import tables

STRUCTURAL_PMCID = "structural"


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(extract, "FIXTURE_DIR", tmp_path / "no-saved-responses")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


def fetch_structural_as(paper_id: str):
    """Cache the structural document as this paper's full text."""
    return intake.fetch_paper({"id": paper_id, "pmcid": STRUCTURAL_PMCID})


# The response a well-behaved model would give for the structural document:
# two good candidates, and four that break one rule each.
GOOD_AND_BAD = {
    "candidates": [
        {  # good — the table row
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.8,
        },
        {  # good — prose, with an organism
            "sectionId": "t1", "field": "titer_secreted", "value": 9, "unit": "mg L-1",
            "quote": "Placeholder B | 9 | mg L-1", "isPrimary": True, "confidence": 0.7,
            "organism": "imaginary yeast",
        },
        {  # quote not verbatim
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A: 7 mg/L", "isPrimary": True, "confidence": 0.9,
        },
        {  # value not in quote
            "sectionId": "t1", "field": "titer_secreted", "value": 70, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.9,
        },
        {  # unit family wrong for the field
            "sectionId": "t1", "field": "titer_secreted", "value": 7, "unit": "% TSP",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.9,
        },
        {  # section the paper does not have
            "sectionId": "s42", "field": "titer_secreted", "value": 7, "unit": "mg L-1",
            "quote": "Placeholder A | 7 | mg L-1", "isPrimary": True, "confidence": 0.9,
        },
    ]
}


def stub_call(raw, usage=None):
    def _call(paper_id, user_text, tool):
        _call.calls.append({"paper_id": paper_id, "user_text": user_text, "tool": tool})
        return raw, usage or Usage(inputTokens=1000, outputTokens=200, costUsd=0.002)
    _call.calls = []
    return _call


# ── the tool and the prompt ────────────────────────────────────────────


def test_the_tool_pins_sections_and_fields_to_enums():
    tool = extract.build_tool(["abstract", "s1", "t1"], ["titer_secreted", "kinase_identity"])
    item = tool["input_schema"]["properties"]["candidates"]["items"]
    assert item["properties"]["sectionId"]["enum"] == ["abstract", "s1", "t1"]
    assert item["properties"]["field"]["enum"] == ["titer_secreted", "kinase_identity"]
    assert set(item["required"]) >= {"sectionId", "field", "value", "unit", "quote", "isPrimary", "confidence"}
    assert tool["name"] == "emit_candidates"


def test_the_prompt_carries_the_ontology_without_ranges_or_notes():
    for f in extract.ontology_for_prompt():
        assert set(f) == {"id", "name", "definition", "canonicalUnit", "categorical", "requiresMethod"}
    assert len(extract.ontology_for_prompt()) == len(tables()["ontology"])


def test_the_prompt_labels_every_section_and_says_when_it_cut_one():
    long_text = ("A sentence that goes on. " * 800).strip()  # ~20k chars
    sections = [
        {"id": "abstract", "heading": "Abstract", "text": "Short."},
        {"id": "s1", "heading": "Results › Growth", "text": long_text},
    ]
    text, notes = extract.build_prompt(sections)
    assert "[abstract · Abstract]\nShort." in text
    assert "[s1 · Results › Growth]\n" in text
    assert len(notes) == 1 and "s1" in notes[0] and "truncated" in notes[0]
    body = text.split("[s1 · Results › Growth]\n")[1]
    assert len(body) <= extract.SECTION_CHAR_LIMIT
    assert body.endswith("."), "cut at a sentence boundary"


# ── extraction over a fetched paper ────────────────────────────────────


def test_extract_anchors_persists_and_counts_rejections(monkeypatch):
    fetch_structural_as("X1")
    call = stub_call(GOOD_AND_BAD)
    monkeypatch.setattr(extract, "call_model", call)

    r = extract.extract_paper("X1")
    assert [c.id for c in r.candidates] == ["hk1-X1-31a6caf5", "hk1-X1-18c2cdd5"], "content-addressed, stable across runs"
    assert r.candidates[0].value == 7 and r.candidates[0].unit == "mg L⁻¹"
    assert r.candidates[1].organism == "imaginary yeast"
    assert all(c.status == "unverified" and c.provenance == "unverified" for c in r.candidates)
    assert all(c.extractorRun == "haiku-1" for c in r.candidates)
    assert r.rejected == 4
    assert r.rejectionReasons["quote"] == 1
    assert r.rejectionReasons["value"] == 1
    assert r.rejectionReasons["unit"] == 1
    assert r.rejectionReasons["section"] == 1
    assert len(r.rejectionDetails) == 4
    # §6.2 — what was refused travels with the response, for match_run's
    # span_error, and never as a candidate.
    assert [d.rule for d in r.dropped] == ["quote", "value", "unit", "section"]
    assert all(d.paperId == "X1" and d.field == "titer_secreted" for d in r.dropped)
    assert r.dropped[0].value == 7 and r.dropped[0].unit == "mg L-1"
    assert r.usage.costUsd == 0.002 and r.usage.inputTokens == 1000
    assert r.audit and r.audit[0].who == "haiku-1" and r.audit[0].action == "extracted"

    # The call saw the whole paper and the pinned tool.
    assert len(call.calls) == 1
    sent = call.calls[0]
    assert sent["paper_id"] == "X1"
    assert "[t1 · Table 1 Placeholder rows, kept as rows.]" in sent["user_text"]
    assert "titer_secreted" in sent["tool"]["input_schema"]["properties"]["candidates"]["items"]["properties"]["field"]["enum"]

    # Persisted, and the cache is honoured.
    path = extract.CANDIDATES_DIR / "X1.json"
    assert path.exists()
    stored = json.loads(path.read_text())
    assert stored["run"] == "haiku-1" and len(stored["candidates"]) == 2 and len(stored["dropped"]) == 4
    again = extract.extract_paper("X1")
    assert again.extractedAt == r.extractedAt and len(call.calls) == 1
    forced = extract.extract_paper("X1", force=True)
    assert len(call.calls) == 2 and forced.extractedAt >= r.extractedAt
    assert ExtractResponse.model_validate(stored)


def test_a_paper_with_no_full_text_is_refused_before_any_call(monkeypatch):
    call = stub_call({"candidates": []})
    monkeypatch.setattr(extract, "call_model", call)
    with pytest.raises(extract.ExtractUnavailable) as caught:
        extract.extract_paper("NOPE")
    assert "no cached full text" in str(caught.value)
    assert call.calls == []


def test_a_failed_fetch_is_not_extractable(monkeypatch):
    intake.fetch_paper({"id": "X2", "pmcid": "PMC0000000"})  # no fixture → failed:fetch
    with pytest.raises(extract.ExtractUnavailable):
        extract.extract_paper("X2")


def test_a_truncated_response_is_refused_and_not_cached(monkeypatch):
    # Cached as an empty extraction it would score as every record missed and
    # could never be re-run without --force; so it is neither.
    fetch_structural_as("X1")
    monkeypatch.setattr(extract, "call_model", stub_call({"candidates": [], "truncated": True}))
    with pytest.raises(extract.ExtractTruncated) as caught:
        extract.extract_paper("X1")
    assert "nothing cached" in str(caught.value)
    assert extract.cached("X1") is None
    # The next attempt is a real call, not a cache hit.
    call = stub_call(GOOD_AND_BAD)
    monkeypatch.setattr(extract, "call_model", call)
    assert len(extract.extract_paper("X1").candidates) == 2 and len(call.calls) == 1


def test_extract_endpoint_answers_502_on_a_truncated_response(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: STRUCTURAL_PMCID)
    client.post("/api/intake/B5/fetch")
    monkeypatch.setattr(extract, "call_model", stub_call({"candidates": [], "truncated": True}))
    r = client.post("/api/intake/B5/extract")
    assert r.status_code == 502 and "token limit" in r.json()["detail"]


def test_fixture_mode_refuses_the_api_without_a_saved_response(monkeypatch):
    fetch_structural_as("X1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(extract.ExtractUnavailable) as caught:
        extract.extract_paper("X1")
    assert "no saved response" in str(caught.value)


# ── the endpoint ───────────────────────────────────────────────────────


@pytest.fixture
def client():
    return TestClient(app)


def test_extract_endpoint_refuses_without_full_text(client):
    r = client.post("/api/intake/B5/extract")
    assert r.status_code == 422
    assert "no cached full text" in r.json()["detail"]
    assert client.post("/api/intake/NOPE/extract").status_code == 404


def test_extract_endpoint_returns_the_anchored_candidates(client, monkeypatch):
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: STRUCTURAL_PMCID)
    assert client.post("/api/intake/B5/fetch").json()["status"] == "complete"
    monkeypatch.setattr(extract, "call_model", stub_call(GOOD_AND_BAD))
    r = client.post("/api/intake/B5/extract")
    assert r.status_code == 200, r.text
    body = ExtractResponse.model_validate(r.json())
    assert body.paperId == "B5" and len(body.candidates) == 2 and body.rejected == 4
    assert body.candidates[0].id == "hk1-B5-a07dd73c"


def test_extract_endpoint_says_when_there_is_no_key(client, monkeypatch):
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: STRUCTURAL_PMCID)
    client.post("/api/intake/B5/fetch")
    # Fixture mode with no saved response behaves like the no-key case: 503
    # with the reason, never a candidate list invented to fill the gap.
    r = client.post("/api/intake/B5/extract")
    assert r.status_code == 503
    assert "saved response" in r.json()["detail"]


# ── what the curators can say, the extractor can say too (F1.4) ────────


def test_the_tool_lets_the_model_state_a_range_and_an_absence():
    tool = extract.build_tool(["s1"], ["titer_secreted"])
    props = tool["input_schema"]["properties"]["candidates"]["items"]["properties"]
    assert props["range"]["properties"]["low"]["type"] == "number"
    assert props["range"]["properties"]["high"]["type"] == "number"
    assert props["negativeResult"]["type"] == "boolean"
    # Optional: most sentences state neither.
    required = tool["input_schema"]["properties"]["candidates"]["items"]["required"]
    assert "range" not in required and "negativeResult" not in required


def test_the_system_prompt_says_what_a_range_and_an_absence_are_for():
    assert "range" in extract.SYSTEM and "midpoint" in extract.SYSTEM
    assert "negativeResult" in extract.SYSTEM


def fetch_saying(paper_id: str, section_id: str, text: str) -> None:
    """A fetched paper whose one section says this, written where a real
    fetch would leave it."""
    from openferment_core.models import FetchedSection, FetchResult

    result = FetchResult(
        paperId=paper_id,
        status="complete",
        fetchedAt="2026-09-15T00:00:00Z",
        sections=[FetchedSection(id=section_id, heading="Results", text=text)],
    )
    intake.FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)
    (intake.FULLTEXT_DIR / f"{paper_id}.json").write_text(result.model_dump_json(), encoding="utf-8")


def test_a_range_the_model_states_reaches_the_anchored_candidate(monkeypatch):
    # The sentence states 7-10 days; the model emits the range and the
    # midpoint, as the prompt asks. The candidate keeps both.
    fetch_saying("R1", "s1", "Colonies appeared in 7-10 days on selection.")
    emitted = {
        "candidates": [
            {
                "sectionId": "s1", "field": "time_to_colony", "value": 8.5, "unit": "d",
                "quote": "Colonies appeared in 7-10 days on selection",
                "range": {"low": 7, "high": 10},
                "isPrimary": True, "confidence": 0.9,
            }
        ]
    }
    monkeypatch.setattr(extract, "call_model", lambda *_: (emitted, extract.Usage()))
    result = extract.extract_paper("R1")
    assert result.rejected == 0, result.rejectionDetails
    [c] = result.candidates
    assert c.value == 8.5 and c.valueBasis == "range-midpoint"
    assert c.range is not None and (c.range.low, c.range.high) == (7.0, 10.0)


def test_an_absence_the_model_states_reaches_the_anchored_candidate(monkeypatch):
    fetch_saying("R2", "s1", "The recombinant protein was not phosphorylated.")
    emitted = {
        "candidates": [
            {
                "sectionId": "s1", "field": "phosphorylation_degree", "value": 0,
                "unit": "% of native sites",
                "quote": "The recombinant protein was not phosphorylated",
                "negativeResult": True, "method": "undetermined",
                "isPrimary": True, "confidence": 0.9,
            }
        ]
    }
    monkeypatch.setattr(extract, "call_model", lambda *_: (emitted, extract.Usage()))
    result = extract.extract_paper("R2")
    assert result.rejected == 0, result.rejectionDetails
    [c] = result.candidates
    assert c.value == 0 and c.valueBasis == "negation" and c.negativeResult is True
