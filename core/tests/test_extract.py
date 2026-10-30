"""Extraction, offline (OF-BLD-012 §6.1, §6.3).

The model call is stubbed — `call_model` is replaced with a function that
returns a hand-written tool input — so every rule around the call is pinned
without spending a token: what the prompt and tool contain, how a passage is
cut, what happens to the candidates the stub returns, what is persisted, and
what the endpoint answers when there is nothing to anchor to.

A document's passages come from Sci RAG Kit (`extract.passages`); here they
are the structural fixture's sections, served as a held document's passages
(`HELD`), so each rule is pinned against text a human can read. Extraction
over a document the kit itself stores is tested in test_literature_kit.py.

The live test that actually calls the model is test_extract_live.py, marked live.
"""
from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from sqlalchemy import select

from openferment_core import db, extract, projects
from openferment_core.api import app
from openferment_core.db import models as t
from openferment_core.models import ExtractResponse, Usage
from openferment_core.units import tables

from conftest import structural_passages

# The documents this test's project holds: id → passages (conftest's held_documents).
HELD: dict[str, list[dict]] = {}



def kept_row(paper_id: str) -> dict:
    """The extractor's row for a paper, as stored."""

    async def read() -> dict:
        async with db.session() as s:
            q = select(t.candidates.c.body).where(
                t.candidates.c.project_id == projects.current(),
                t.candidates.c.document_id == paper_id,
                t.candidates.c.source == extract.MODEL,
            )
            return (await s.execute(q)).scalar_one()

    return db.run(read())

@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path, test_corpus, held_documents):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(extract, "FIXTURE_DIR", tmp_path / "no-saved-responses")
    global HELD
    HELD = held_documents


def fetch_structural_as(paper_id: str) -> None:
    """The structural document, held as this paper's passages."""
    HELD[paper_id] = structural_passages()


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
    assert [c.id for c in r.candidates] == ["cl1-X1-31a6caf5", "cl1-X1-18c2cdd5"], "content-addressed, stable across runs"
    assert r.candidates[0].value == 7 and r.candidates[0].unit == "mg L⁻¹"
    assert r.candidates[1].organism == "imaginary yeast"
    assert all(c.status == "unverified" and c.provenance == "unverified" for c in r.candidates)
    assert all(c.extractorRun == "claude-1" for c in r.candidates)
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
    assert r.audit and r.audit[0].who == "claude-1" and r.audit[0].action == "extracted"

    # The call saw the whole paper and the pinned tool.
    assert len(call.calls) == 1
    sent = call.calls[0]
    assert sent["paper_id"] == "X1"
    assert "[t1 · Table 1 Placeholder rows, kept as rows.]" in sent["user_text"]
    assert any("titer_secreted" in v["properties"]["field"]["enum"] for v in item_variants(sent["tool"]))

    # Persisted, and the kept run is honoured.
    stored = kept_row("X1")
    assert stored["run"] == "claude-1" and len(stored["candidates"]) == 2 and len(stored["dropped"]) == 4
    again = extract.extract_paper("X1")
    assert again.extractedAt == r.extractedAt and len(call.calls) == 1
    forced = extract.extract_paper("X1", force=True)
    assert len(call.calls) == 2 and forced.extractedAt >= r.extractedAt
    assert ExtractResponse.model_validate(stored)


def test_a_paper_with_no_full_text_is_refused_before_any_call(monkeypatch):
    call = stub_call({"candidates": []})
    monkeypatch.setattr(extract, "call_model", call)
    with pytest.raises(extract.NothingToAnchor) as caught:
        extract.extract_paper("NOPE")
    assert "holds no document NOPE" in str(caught.value)
    assert call.calls == []


def test_a_document_with_no_text_is_not_extractable(monkeypatch):
    HELD["X2"] = []
    with pytest.raises(extract.NothingToAnchor):
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
    fetch_structural_as("T5")
    monkeypatch.setattr(extract, "call_model", stub_call({"candidates": [], "truncated": True}))
    r = client.post("/api/intake/T5/extract")
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


def test_extract_endpoint_refuses_a_document_the_project_does_not_hold(client):
    r = client.post("/api/intake/T5/extract")
    assert r.status_code == 422
    assert "holds no document T5" in r.json()["detail"]


def test_extract_endpoint_returns_the_anchored_candidates(client, monkeypatch):
    fetch_structural_as("T5")
    monkeypatch.setattr(extract, "call_model", stub_call(GOOD_AND_BAD))
    r = client.post("/api/intake/T5/extract")
    assert r.status_code == 200, r.text
    body = ExtractResponse.model_validate(r.json())
    assert body.paperId == "T5" and len(body.candidates) == 2 and body.rejected == 4
    assert body.candidates[0].id == "cl1-T5-276fbb61"


def test_extract_endpoint_says_when_there_is_no_key(client, monkeypatch):
    fetch_structural_as("T5")
    # Fixture mode with no saved response behaves like the no-key case: 503
    # with the reason, never a candidate list invented to fill the gap.
    r = client.post("/api/intake/T5/extract")
    assert r.status_code == 503
    assert "saved response" in r.json()["detail"]


# ── what the curators can say, the extractor can say too (F1.4) ────────


def test_the_tool_lets_the_model_state_a_range_and_an_absence():
    tool = extract.build_tool(["s1"], ["titer_secreted"])
    props = item_variants(tool)[-1]["properties"]
    assert props["range"]["properties"]["low"]["type"] == "number"
    assert props["range"]["properties"]["high"]["type"] == "number"
    assert props["negativeResult"]["type"] == "boolean"
    # Optional: most sentences state neither.
    required = tool["input_schema"]["properties"]["candidates"]["items"]["required"]
    assert "range" not in required and "negativeResult" not in required


def test_the_system_prompt_says_what_a_range_and_an_absence_are_for():
    assert "range" in extract.SYSTEM and "midpoint" in extract.SYSTEM
    assert "negativeResult" in extract.SYSTEM


def fetch_sections(paper_id: str, sections: list[tuple[str, str]]) -> None:
    """A fetched paper whose sections say these things, written where a real
    fetch would leave it."""
    from openferment_core.models import FetchedSection

    HELD[paper_id] = [FetchedSection(id=i, heading="Results", text=t).model_dump() for i, t in sections]


def fetch_saying(paper_id: str, section_id: str, text: str) -> None:
    """A fetched paper whose one section says this, written where a real
    fetch would leave it."""
    from openferment_core.models import FetchedSection

    HELD[paper_id] = [FetchedSection(id=section_id, heading="Results", text=text).model_dump()]


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
    fetch_saying("R2", "s1", "No secreted product was detected in the medium.")
    emitted = {
        "candidates": [
            {
                "sectionId": "s1", "field": "titer_secreted", "value": 0,
                "unit": "g/L",
                "quote": "No secreted product was detected in the medium",
                "negativeResult": True,
                "isPrimary": True, "confidence": 0.9,
            }
        ]
    }
    monkeypatch.setattr(extract, "call_model", lambda *_: (emitted, extract.Usage()))
    result = extract.extract_paper("R2")
    assert result.rejected == 0, result.rejectionDetails
    [c] = result.candidates
    assert c.value == 0 and c.valueBasis == "negation" and c.negativeResult is True


# ── a long paper does not lose its candidates (OF-BLD-012.1 F8) ────────
#
# A review with many tables can emit more than the token limit of candidates.
# The old handling logged a warning and returned nothing, and Witness then
# scored that paper as if the extractor had found nothing in it.

FOUR = [(f"s{n}", f"The titre reached {n}.0 g L-1 in run {n}.") for n in (1, 2, 3, 4)]


def one_per_section(section_ids: list[str]) -> dict:
    return {
        "candidates": [
            {
                "sectionId": sid, "field": "titer_secreted", "value": float(sid[1:]),
                "unit": "g L-1", "quote": f"The titre reached {sid[1:]}.0 g L-1 in run {sid[1:]}",
                "isPrimary": True, "confidence": 0.9,
            }
            for sid in section_ids
        ]
    }


def item_variants(tool: dict) -> list[dict]:
    """The candidate schema, as the list of its one variant."""
    return [tool["input_schema"]["properties"]["candidates"]["items"]]


def sections_asked(tool: dict) -> list[str]:
    return item_variants(tool)[0]["properties"]["sectionId"]["enum"]


def truncated(usage_in: int = 100) -> tuple[dict, extract.Usage]:
    u = extract.Usage(inputTokens=usage_in, outputTokens=extract.MAX_TOKENS, costUsd=0.01)
    return {"candidates": [], "truncated": True, "usage": u.model_dump()}, u


def test_the_token_limit_is_high_enough_for_a_paper_full_of_tables():
    assert extract.MAX_TOKENS >= 16_000


def test_a_paper_that_truncates_whole_is_split_and_nothing_is_lost(monkeypatch):
    fetch_sections("S1", FOUR)
    asked: list[list[str]] = []

    def fake(paper_id, user_text, tool):
        ids = sections_asked(tool)
        asked.append(ids)
        if len(ids) == 4:
            return truncated()
        return one_per_section(ids), extract.Usage(inputTokens=10, outputTokens=20, costUsd=0.002)

    monkeypatch.setattr(extract, "call_model", fake)
    result = extract.extract_paper("S1")
    assert result.calls == 3, asked
    assert asked == [["s1", "s2", "s3", "s4"], ["s1", "s2"], ["s3", "s4"]]
    assert sorted(c.sectionId for c in result.candidates) == ["s1", "s2", "s3", "s4"]
    assert result.truncatedSections == []
    # Every call is paid for, including the one that produced nothing.
    assert result.usage.costUsd == pytest.approx(0.01 + 0.002 + 0.002)


def test_a_half_that_still_truncates_splits_once_more_then_reports_it(monkeypatch):
    fetch_sections("S2", FOUR)
    asked: list[list[str]] = []

    def fake(paper_id, user_text, tool):
        ids = sections_asked(tool)
        asked.append(ids)
        # Everything on the left keeps truncating; the right half answers.
        if ids[0] == "s1":
            return truncated()
        return one_per_section(ids), extract.Usage(costUsd=0.002)

    monkeypatch.setattr(extract, "call_model", fake)
    result = extract.extract_paper("S2")
    # whole → [s1 s2] → [s1] → [s2]; and [s3 s4] answered whole.
    assert sorted(c.sectionId for c in result.candidates) == ["s2", "s3", "s4"]
    assert result.truncatedSections == ["s1"], asked
    assert result.calls == len(asked)


def test_a_paper_that_truncates_all_the_way_down_is_still_refused(monkeypatch):
    # Nothing was extracted, so nothing is cached and the endpoint says 502:
    # an empty extraction written to disk would be scored as every record
    # missed and could never be re-run without --force.
    fetch_sections("S3", FOUR)
    monkeypatch.setattr(extract, "call_model", lambda *_: truncated())
    with pytest.raises(extract.ExtractTruncated):
        extract.extract_paper("S3")
    assert extract.cached("S3") is None


def test_a_paper_that_does_not_truncate_is_one_call(monkeypatch):
    fetch_sections("S4", FOUR)
    monkeypatch.setattr(
        extract, "call_model",
        lambda p, u, t: (one_per_section(sections_asked(t)), extract.Usage(costUsd=0.002)),
    )
    result = extract.extract_paper("S4")
    assert result.calls == 1 and result.truncatedSections == []
    assert len(result.candidates) == 4


def test_the_prompt_is_built_once_per_call(monkeypatch):
    # `extract_paper` built the whole prompt — the ontology and every section
    # serialised — once for its notes and then again for the call. Twice the
    # work on every paper, and three or four times on one that splits.
    fetch_structural_as("X1")
    monkeypatch.setattr(extract, "call_model", stub_call(GOOD_AND_BAD))
    real = extract.build_prompt
    calls: list[int] = []

    def counting(sections):
        calls.append(len(sections))
        return real(sections)

    monkeypatch.setattr(extract, "build_prompt", counting)
    extract.extract_paper("X1")
    assert calls == [len(HELD["X1"])], calls


# ── a polymer, a bacterium's growth rate, and what the cells were fed ──
# (OF-BLD-014 §2.1). The section is a fixture about an imaginary run; its
# numbers are test values, not results.

CULTURE_SECTION = (
    "On glucose the imaginary strain reached an ethanol titre of 62 g/L at harvest. "
    "Its specific growth rate was 0.41 h-1 in the batch phase."
)


def _culture_candidates(**over) -> dict:
    base = [
        {  # a titre
            "sectionId": "s1", "field": "ethanol_titre", "value": 62, "unit": "g/L",
            "quote": "the imaginary strain reached an ethanol titre of 62 g/L at harvest",
            "isPrimary": True, "confidence": 0.9,
            "organism": "imaginary strain", "carbonSource": over.get("titre_carbon", "glucose"),
        },
        {  # a growth rate
            "sectionId": "s1", "field": "growth_rate_mu", "value": 0.41, "unit": "h-1",
            "quote": "Its specific growth rate was 0.41 h-1 in the batch phase",
            "isPrimary": True, "confidence": 0.9,
            "carbonSource": over.get("rate_carbon", "glucose"),
        },
    ]
    return {"candidates": base}


def test_a_carbon_source_that_sits_in_the_section_is_kept(monkeypatch):
    fetch_saying("P3", "s1", CULTURE_SECTION)
    monkeypatch.setattr(extract, "call_model", lambda *_: (_culture_candidates(), extract.Usage()))
    result = extract.extract_paper("P3")
    assert [c.carbonSource for c in result.candidates] == ["glucose", "glucose"]
    assert result.fieldDrops == {"carbonSource": 0}
    # Persisted as it was answered.
    stored = kept_row("P3")
    assert stored["candidates"][0]["carbonSource"] == "glucose"


def test_a_carbon_source_absent_from_the_section_is_dropped_and_its_candidate_kept(monkeypatch):
    fetch_saying("P4", "s1", CULTURE_SECTION)
    raw = _culture_candidates(titre_carbon="xylose")
    monkeypatch.setattr(extract, "call_model", lambda *_: (raw, extract.Usage()))
    result = extract.extract_paper("P4")
    assert result.rejected == 0, "a dropped field is not a rejected candidate"
    assert len(result.candidates) == 2
    titre = next(c for c in result.candidates if c.field == "ethanol_titre")
    rate = next(c for c in result.candidates if c.field == "growth_rate_mu")
    assert titre.carbonSource is None, "xylose is not in the section; the field goes"
    assert rate.carbonSource == "glucose", "the other candidate's is untouched"
    assert result.fieldDrops == {"carbonSource": 1}
    assert all(v == 0 for v in result.rejectionReasons.values())


def test_the_tool_asks_for_the_carbon_source_in_the_papers_words():
    tool = extract.build_tool(["s1"], ["ethanol_titre"])
    items = item_variants(tool)[0]
    prop = items["properties"]["carbonSource"]
    assert prop["type"] == "string"
    assert "words the paper uses" in prop["description"] and "names none" in prop["description"]
    assert "carbonSource" not in items["required"], "a paper may name none"
