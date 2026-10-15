"""Four more lanes (OF-BLD-014 §4.2). Offline: a stand-in model answers the
helper calls, and HashEmbedder stands in for the vectors. The passages are
STAND-IN text built here, not a paper's words."""
from __future__ import annotations

import json

import numpy as np
import pytest

from openferment_core import embed, expand, intake, llm, passages, rerank, retrieve
from openferment_core.models import FetchedSection, FetchResult, Usage


# ── fusion ─────────────────────────────────────────────────────────────


def test_reciprocal_rank_fusion_by_hand():
    fused = retrieve.rrf({"a": ["x", "y", "z"], "b": ["y", "w"]})
    scores = {pid: s for pid, s, _ in fused}
    assert scores["y"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["x"] == pytest.approx(1 / 61)
    assert scores["z"] == pytest.approx(1 / 63)
    assert scores["w"] == pytest.approx(1 / 62)
    assert [pid for pid, _, _ in fused] == ["y", "x", "w", "z"]
    assert dict((pid, r) for pid, _, r in fused)["y"] == {"a": 2, "b": 1}


def test_a_tie_keeps_first_seen_order():
    fused = retrieve.rrf({"a": ["p"], "b": ["q"]})
    assert [pid for pid, _, _ in fused] == ["p", "q"]


# ── the stand-in embedder ──────────────────────────────────────────────


def test_hash_embedder_is_deterministic_and_unit_length():
    e = embed.HashEmbedder(64)
    a = e.embed(["xylose fed PHB", "casein micelle"])
    b = embed.HashEmbedder(64).embed(["xylose fed PHB", "casein micelle"])
    assert np.array_equal(a, b)
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)
    assert a[0] @ a[0] > a[0] @ a[1]


# ── an index to search ─────────────────────────────────────────────────

TEXTS = {
    "X1": ["Polyhydroxybutyrate accumulated when the cells were fed xylose hydrolysate.", "The reactor ran at constant temperature."],
    "X2": ["Poly-3-hydroxybutyrate granules filled the cytoplasm of Cupriavidus necator.", "Agitation was kept constant."],
    "X3": ["Casein micelles formed in the presence of calcium.", "Phosphorylation was measured by mass spectrometry."],
    "X4": ["Glucose was the only carbon source in the control.", "Optical density was read daily."],
}


@pytest.fixture()
def index(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(passages, "_papers_meta", lambda: {})
    monkeypatch.setattr(passages, "_LOADED", None)
    monkeypatch.setattr(retrieve, "_EMBEDDERS", {})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stand-in")
    (tmp_path / "fulltext").mkdir()
    for pid, sentences in TEXTS.items():
        r = FetchResult(
            paperId=pid, pmcid=None, status="complete", fetchedAt="2026-10-15T00:00:00Z",
            sections=[FetchedSection(id=f"s{n}", heading="Results", text=t) for n, t in enumerate(sentences, start=1)],
        )
        (tmp_path / "fulltext" / f"{pid}.json").write_text(r.model_dump_json(), encoding="utf-8")
    passages.build()
    return tmp_path


def stand_in(data: dict, calls: list | None = None, usd: float = 0.001):
    def ask(**kw):
        if calls is not None:
            calls.append(kw)
        return llm.Result(data=data, model="claude-haiku-5-5", usage=Usage(costUsd=usd, models=["claude-haiku-5-5"]))

    return ask


# ── bm25+expand ────────────────────────────────────────────────────────


def test_other_phrasings_widen_recall(index):
    question = "PHB from xylose"
    plain = {h.passage.paperId for h in retrieve.search(question, k=8, lane="bm25")}
    assert "X2" not in plain, "the keyword lane alone misses the paper that says poly-3-hydroxybutyrate"
    calls: list = []
    ask = stand_in({"phrasings": ["poly-3-hydroxybutyrate granules", "polyhydroxybutyrate xylose"]}, calls)
    detail = retrieve.search_detail(question, k=8, lane="bm25+expand", ask=ask)
    found = {h.passage.paperId for h in detail.hits}
    assert {"X1", "X2"} <= found
    assert detail.phrasings == ["poly-3-hydroxybutyrate granules", "polyhydroxybutyrate xylose"]
    assert calls[0]["role"] == "index"
    assert detail.usage.costUsd == 0.001


def test_phrasings_are_cached_on_disk_and_paid_for_once(index):
    calls: list = []
    ask = stand_in({"phrasings": ["one", "two", "three", "four"]}, calls)
    first, spent = expand.phrasings("a question", ask=ask)
    again, spent_again = expand.phrasings("a question", ask=ask)
    assert first == again == ["one", "two", "three"] and len(calls) == 1
    assert spent.costUsd == 0.001 and spent_again.costUsd == 0.0
    assert list((index / "index" / "cache" / "expand").glob("*.json"))


# ── the grading reader ────────────────────────────────────────────────


def test_a_made_up_sentence_from_the_reader_is_caught_and_counted(index):
    pid_true = "X1:s1:0"
    pid_false = "X2:s2:0"
    ask = stand_in(
        {
            "grades": [
                {"passageId": pid_true, "grade": 3, "sentence": "Polyhydroxybutyrate accumulated when the cells were fed xylose hydrolysate."},
                {"passageId": pid_false, "grade": 3, "sentence": "Agitation was kept constant at a record rate."},
            ]
        }
    )
    detail = retrieve.search_detail("xylose constant", k=8, lane="bm25+rerank", ask=ask)
    by = {h.passage.id: h for h in detail.hits}
    assert pid_false in by, "the reader was shown the passage it misquoted"
    assert detail.unverifiedSentences == 1
    assert by[pid_true].grade == 3 and by[pid_true].sentence.startswith("Polyhydroxybutyrate accumulated")
    assert by[pid_false].grade == 0 and by[pid_false].sentence is None
    assert detail.hits[0].passage.id == pid_true, "order is grade first"


def test_the_reader_ignores_passages_it_was_not_shown():
    p = passages.Passage(id="A:s1:0", paperId="A", sectionId="s1", heading="h", kind="prose", text="A real sentence.", start=0, end=16)
    g = rerank.check([{"passageId": "B:s1:0", "grade": 3, "sentence": "x"}, {"passageId": "A:s1:0", "grade": 2, "sentence": "  A real   sentence. "}], {p.id: p})
    assert g.grades == {"A:s1:0": 2} and g.unverified == 0, "spacing is normalised; the words are not"
    altered = rerank.check([{"passageId": "A:s1:0", "grade": 2, "sentence": "a REAL sentence."}], {p.id: p})
    assert altered.grades == {"A:s1:0": 0} and altered.unverified == 1


# ── hybrid ─────────────────────────────────────────────────────────────


def test_hybrid_fuses_keyword_and_vector_rankings(index):
    embed.build_dense(embed.HashEmbedder(64))
    meta = json.loads((index / "index" / "dense.json").read_text())
    assert meta["model"] == "hash-64" and meta["count"] == 8
    hits = retrieve.search("casein calcium micelles", k=3, lane="hybrid")
    assert hits[0].passage.paperId == "X3"
    assert set(hits[0].lanes) == {"bm25", "dense"}


def test_vectors_from_an_older_index_are_not_used(index):
    embed.build_dense(embed.HashEmbedder(64))
    (index / "fulltext" / "X4.json").unlink()
    passages.build()
    why = retrieve.why_unavailable("hybrid")
    assert why and "older index" in why


# ── an unavailable lane says why ───────────────────────────────────────


def test_an_unavailable_lane_says_why(index, monkeypatch):
    assert "pnpm index:build --dense" in retrieve.why_unavailable("hybrid")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert "needs the key" in retrieve.why_unavailable("bm25+rerank")
    with pytest.raises(retrieve.LaneUnavailable, match="needs the key"):
        retrieve.search("x", lane="bm25+expand")
    assert retrieve.why_unavailable("bm25") is None
    assert "there is no lane" in retrieve.why_unavailable("magic")


def test_an_embedder_that_cannot_load_makes_the_lane_say_so(index, monkeypatch):
    embed.build_dense(embed.HashEmbedder(64))
    meta = index / "index" / "dense.json"
    m = json.loads(meta.read_text())
    m["model"] = "no-such/model"
    meta.write_text(json.dumps(m))

    class Broken:
        def __init__(self, model):
            raise embed.EmbedderUnavailable("the model no-such/model could not be loaded; it comes from huggingface.co")

    monkeypatch.setattr(embed, "FastEmbedder", Broken)
    assert "huggingface.co" in retrieve.why_unavailable("hybrid")


def test_the_default_lane_comes_from_config(index):
    assert retrieve.search_detail("casein", k=2).lane == "bm25"
    (index / "index" / "config.json").write_text(json.dumps({"lane": "bm25+expand"}))
    with pytest.raises(retrieve.LaneUnavailable):
        # The chosen lane runs when none is named, and asks before it spends.
        import os

        os.environ.pop("ANTHROPIC_API_KEY", None)
        retrieve.search("casein")


def test_status_lists_every_lane(index):
    s = passages.status()
    assert [l.name for l in s.lanes] == list(retrieve.LANES)
    assert s.lanes[0].available and not s.lanes[2].available


# ── the endpoint (§4.4) ────────────────────────────────────────────────


def test_post_search_returns_hits_and_refuses_a_lane_that_cannot_run(index, monkeypatch):
    from fastapi.testclient import TestClient

    from openferment_core import api

    client = TestClient(api.app, base_url="http://127.0.0.1")
    ok = client.post("/api/rag/search", json={"question": "casein calcium micelles", "k": 3})
    assert ok.status_code == 200
    body = ok.json()
    assert body["lane"] == "bm25" and body["hits"][0]["passage"]["paperId"] == "X3"
    assert body["hits"][0]["lanes"] == {"bm25": 1} and body["costUsd"] == 0.0
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    refused = client.post("/api/rag/search", json={"question": "casein", "k": 3, "lane": "bm25+rerank"})
    assert refused.status_code == 409 and "needs the key" in refused.json()["detail"]
    guarded = client.post("/api/rag/search", json={"question": "casein"}, headers={"Origin": "https://evil.example"})
    assert guarded.status_code == 403
