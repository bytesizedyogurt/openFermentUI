"""The papers' own words, cut into passages and indexed (OF-BLD-014 §4.1).

The JATS fixtures in the tree are short placeholders, so the long section and
the long table here are built in code. STAND-IN text, not a paper's words.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, passages
from openferment_core.models import FetchedSection, FetchResult


def _prose(n: int = 40) -> str:
    out = []
    for i in range(n):
        out.append(
            f"Sentence number {i} describes the stand-in culture of E. coli strain K{i} in words "
            f"that run long enough to matter for the cutter, as reported by Smith et al. in the stand-in."
        )
    return " ".join(out)


def _table(rows: int = 60) -> str:
    header = "Entry | Strain | Carbon source | Titre column"
    lines = [header] + [f"row {i} | strain S{i} | xylose and glucose mixture {i} | value v{i}" for i in range(rows)]
    return "\n".join(lines + ["Footnote: v stands for a stand-in value."])


def _reassemble(text: str, spans: list[tuple[int, int]]) -> str:
    out = ""
    covered = 0
    for s, e in spans:
        assert s <= covered, "no gap between passages"
        out += text[max(s, covered) : e]
        covered = max(covered, e)
    return out


def test_prose_passages_reassemble_their_section_once_overlaps_are_removed():
    text = _prose()
    spans = passages.prose_chunks(text)
    assert len(spans) > 3
    assert _reassemble(text, spans) == text
    for s, e in spans:
        assert e - s <= passages.CHUNK_MAX


def test_each_prose_passage_after_the_first_repeats_the_last_sentence_before_it():
    text = _prose()
    spans = passages.prose_chunks(text)
    sentences = passages.sentence_spans(text)
    starts = {s for s, _ in sentences}
    for (s0, e0), (s1, _) in zip(spans, spans[1:]):
        assert s1 < e0, "one sentence of overlap"
        assert s1 in starts, "a passage starts at a sentence"


def test_a_repeated_sentence_never_stands_alone():
    # Sentences sized so that the overlap plus the next sentence pass the
    # target: the passage after the repeat still moves on.
    text = " ".join(f"Sentence {i} " + "word " * 120 + "end." for i in range(6))
    spans = passages.prose_chunks(text, target=900, limit=1400)
    for s, e in spans:
        assert len(passages.sentence_spans(text[s:e])) >= 1
    for (_, e0), (s1, e1) in zip(spans, spans[1:]):
        assert e1 > e0, "every passage reaches past the one before"


def test_abbreviations_do_not_end_a_sentence():
    text = "Growth of E. coli was slow. Cells of P. putida grew, as Smith et al. Reported earlier. Fig. 2 shows it."
    sentences = [text[s:e].strip() for s, e in passages.sentence_spans(text)]
    assert sentences[0] == "Growth of E. coli was slow."
    assert sentences[1].startswith("Cells of P. putida grew")


def test_every_table_chunk_starts_with_heading_and_first_row_and_keeps_rows_whole():
    text = _table()
    section = {"id": "t2", "heading": "Table 2 Stand-in yields", "text": text}
    cuts = passages.cut_section("X1", section, "A stand-in paper (2020)")
    assert len(cuts) > 2
    header = text.split("\n")[0]
    rows = set(text.split("\n"))
    for c in cuts:
        lines = c.passage.text.split("\n")
        assert lines[0] == "Table 2 Stand-in yields" and lines[1] == header
        assert all(line in rows for line in lines[1:]), "a row is never cut"
        assert c.passage.kind == "table"


def test_a_figure_is_one_passage_and_a_long_abstract_two():
    fig = passages.cut_section("X1", {"id": "f1", "heading": "Figure 1", "text": _prose(30)}, "ctx")
    assert len(fig) == 1 and fig[0].passage.kind == "figure"
    abstract = passages.cut_section("X1", {"id": "abstract", "heading": "Abstract", "text": _prose(20)}, "ctx")
    assert len(abstract) == 2
    short = passages.cut_section("X1", {"id": "abstract", "heading": "Abstract", "text": "One short abstract."}, "ctx")
    assert len(short) == 1


def test_the_context_is_kept_apart_from_the_papers_words():
    cuts = passages.cut_paper("X1", [{"id": "s1", "heading": "Results", "text": "A sentence the paper wrote."}], "A title", 2020)
    assert cuts[0].context == "A title (2020) — Results"
    assert cuts[0].passage.text == "A sentence the paper wrote."
    assert cuts[0].passage.id == "X1:s1:0"


# ── the index on disk ──────────────────────────────────────────────────


@pytest.fixture()
def fetched(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(passages, "_papers_meta", lambda: {"X1": {"title": "Stand-in one", "year": 2020}})
    (tmp_path / "fulltext").mkdir()

    def write(pid: str, sections: list[dict], status: str = "complete"):
        r = FetchResult(paperId=pid, pmcid=None, status=status, fetchedAt="2026-10-15T00:00:00Z", sections=[FetchedSection(**s) for s in sections])
        (tmp_path / "fulltext" / f"{pid}.json").write_text(r.model_dump_json(), encoding="utf-8")

    return write


def test_ids_are_stable_across_rebuilds_and_an_unchanged_paper_is_skipped(fetched):
    fetched("X1", [{"id": "s1", "heading": "Results", "text": _prose()}, {"id": "t1", "heading": "Table 1", "text": _table()}])
    fetched("X2", [{"id": "s1", "heading": "Methods", "text": _prose(10)}])
    first = passages.build()
    ids = [c.passage.id for c in passages.read_index()]
    assert sorted(first["rebuilt"]) == ["X1", "X2"] and first["passages"] == len(ids)
    second = passages.build()
    assert second["rebuilt"] == [] and sorted(second["kept"]) == ["X1", "X2"]
    assert [c.passage.id for c in passages.read_index()] == ids
    fetched("X2", [{"id": "s1", "heading": "Methods", "text": _prose(12)}])
    third = passages.build()
    assert third["rebuilt"] == ["X2"] and third["kept"] == ["X1"]
    assert passages.build(everything=True)["rebuilt"] == ["X1", "X2"]


def test_a_curation_note_or_a_failed_fetch_is_never_indexed(fetched):
    fetched("X1", [{"id": "s1", "heading": "Results", "text": "The paper's own sentence."}])
    fetched("X3", [], status="failed:fetch")
    did = passages.build()
    assert did["papers"] == 1 and {c.passage.paperId for c in passages.read_index()} == {"X1"}


def test_a_paper_whose_text_is_gone_is_dropped(fetched, tmp_path):
    fetched("X1", [{"id": "s1", "heading": "R", "text": "One."}])
    fetched("X2", [{"id": "s1", "heading": "R", "text": "Two."}])
    passages.build()
    (tmp_path / "fulltext" / "X2.json").unlink()
    assert passages.build()["dropped"] == ["X2"]


def test_a_new_chunker_cuts_every_paper_again(fetched, monkeypatch):
    fetched("X1", [{"id": "s1", "heading": "R", "text": "One."}])
    passages.build()
    monkeypatch.setattr(passages, "CHUNKER_VERSION", "passages-test")
    assert passages.build()["rebuilt"] == ["X1"]


# ── the bm25 lane ──────────────────────────────────────────────────────


def _index(*texts: str) -> passages.Bm25Index:
    cuts = [
        passages.Cut(
            passages.Passage(id=f"X:s{n}:0", paperId="X", sectionId=f"s{n}", heading="h", kind="prose", text=t, start=0, end=len(t)),
            "context",
        )
        for n, t in enumerate(texts)
    ]
    return passages.Bm25Index(cuts)


def test_bm25_ranks_by_keyword_and_drops_zero_scores():
    idx = _index("xylose feeding raised the PHB content", "glucose only", "an unrelated methods note", "casein micelles")
    hits = idx.search("PHB xylose", k=8)
    assert hits[0].passage.id == "X:s0:0"
    assert all(h.score > 0 for h in hits) and "X:s3:0" not in [h.passage.id for h in hits]


def test_bm25_refuses_a_long_question_whose_best_hit_matches_one_term():
    idx = _index("xylose feeding raised the PHB content", "glucose only", "an unrelated methods note", "casein micelles")
    assert idx.search("casein phosphorylation kinase", k=8) == []
    assert idx.search("casein", k=8)[0].passage.id == "X:s3:0", "a short question may match on one term"


# ── the endpoint ───────────────────────────────────────────────────────


def test_rag_status_reports_the_index_and_the_lane(fetched, tmp_path):
    from openferment_core import api

    client = TestClient(api.app, base_url="http://127.0.0.1")
    empty = client.get("/api/rag/status").json()
    assert empty["papersIndexed"] == 0 and empty["lanes"][0] == {"name": "bm25", "available": False, "why": "no index yet: run pnpm index:build"}
    fetched("X1", [{"id": "s1", "heading": "R", "text": _prose(10)}])
    passages.build()
    body = client.get("/api/rag/status").json()
    assert body["papersIndexed"] == 1 and body["passages"] >= 1 and body["chosenLane"] == "bm25"
    (tmp_path / "index" / "config.json").write_text(json.dumps({"lane": "hybrid"}), encoding="utf-8")
    assert client.get("/api/rag/status").json()["chosenLane"] == "hybrid"
