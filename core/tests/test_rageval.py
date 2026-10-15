"""Every lane scored on the same questions (OF-BLD-014 §4.3). Metrics are held
to answers worked by hand; the corpus is STAND-IN text built here."""
from __future__ import annotations

import json
import math

import pytest

from openferment_core import intake, llm, passages, rageval, retrieve
from openferment_core.models import FetchedSection, FetchResult, RagLaneReport, RagMetrics, RagReport, Usage


# ── metrics, by hand ───────────────────────────────────────────────────

RANKED = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]


def test_recall_by_hand():
    assert rageval.recall_at(RANKED, ["b", "k"], 5) == 0.5
    assert rageval.recall_at(RANKED, ["b", "k"], 20) == 1.0
    assert rageval.recall_at(RANKED, ["z"], 10) == 0.0


def test_mrr_by_hand():
    assert rageval.mrr_at(RANKED, ["c", "e"]) == pytest.approx(1 / 3)
    assert rageval.mrr_at(RANKED, ["k"]) == 0.0, "rank 11 is outside MRR@10"


def test_ndcg_by_hand():
    # Relevant at ranks 2 and 4, two relevant in all:
    # DCG = 1/log2(3) + 1/log2(5); IDCG = 1/log2(2) + 1/log2(3).
    want = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert rageval.ndcg_at(RANKED, ["b", "d"]) == pytest.approx(want)
    assert rageval.ndcg_at(["x", "b"], ["b"]) == pytest.approx(1 / math.log2(3))
    assert rageval.ndcg_at(RANKED, ["a"]) == 1.0


def test_score_set_means_over_questions():
    m = rageval.score_set([(["a", "b"], ["a"], 0.1, 0.0), (["a", "b"], ["b"], 0.3, 0.002)])
    assert m.questions == 2 and m.recall5 == 1.0 and m.mrr10 == pytest.approx(0.75)
    assert m.medianSeconds == pytest.approx(0.2) and m.costPerQuestion == 0.001


# ── the rule ───────────────────────────────────────────────────────────


def _m(ndcg: float) -> RagMetrics:
    return RagMetrics(questions=10, recall5=0, recall10=0, recall20=0, mrr10=0, ndcg10=ndcg, medianSeconds=0, costPerQuestion=0)


def _lane(name: str, k: float | None, s: float | None = None, available: bool = True) -> RagLaneReport:
    sets = {}
    if k is not None:
        sets["K"] = _m(k)
    if s is not None:
        sets["S"] = _m(s)
    lane = RagLaneReport(lane=name, available=available, paid=name in retrieve.PAID, sets=sets)
    lane.score = rageval.lane_score(lane) if available else None
    return lane


def _report(*lanes: RagLaneReport) -> RagReport:
    return RagReport(date="d", manifestHash="h", papersIndexed=1, passages=1, sets=[], lanes=list(lanes), chosenLane="bm25", rule=rageval.RULE, totalCostUsd=0)


def test_a_tie_goes_to_the_free_lane():
    assert rageval.choose_lane(_report(_lane("bm25", 0.5, 0.5), _lane("bm25+rerank", 0.5, 0.5))) == "bm25"
    assert rageval.choose_lane(_report(_lane("bm25", 0.5, 0.5), _lane("hybrid", 0.5, 0.5))) == "bm25"


def test_a_paid_lane_needs_the_margin_to_win():
    assert rageval.choose_lane(_report(_lane("bm25", 0.50, 0.50), _lane("bm25+rerank", 0.51, 0.52))) == "bm25"
    assert rageval.choose_lane(_report(_lane("bm25", 0.50, 0.50), _lane("bm25+rerank", 0.52, 0.52))) == "bm25+rerank"
    # The margin is over the best FREE lane, hybrid here.
    assert rageval.choose_lane(_report(_lane("bm25", 0.4, 0.4), _lane("hybrid", 0.6, 0.6), _lane("hybrid+rerank", 0.61, 0.61))) == "hybrid"
    assert rageval.choose_lane(_report(_lane("bm25", 0.4, 0.4), _lane("hybrid", 0.6, 0.6), _lane("hybrid+rerank", 0.63, 0.63))) == "hybrid+rerank"


def test_an_unavailable_lane_is_skipped():
    assert rageval.choose_lane(_report(_lane("bm25", 0.3), _lane("hybrid", 0.9, available=False))) == "bm25"


def test_the_score_is_the_mean_of_k_and_s_present():
    assert _lane("bm25", 0.2, 0.6).score == pytest.approx(0.4)
    assert _lane("bm25", 0.2).score == pytest.approx(0.2), "S absent: K alone"


# ── K and F on a fixture corpus ────────────────────────────────────────

TEXTS = {
    "X1": ["The secreted titre reached its peak after the fourth day of xylose feeding.", "Agitation was kept constant throughout."],
    "X2": ["Cells of cw15 secreted the reporter into the medium on acetate.", "The reactor ran at constant temperature."],
}


@pytest.fixture()
def index(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(passages, "_papers_meta", lambda: {})
    monkeypatch.setattr(passages, "_LOADED", None)
    (tmp_path / "fulltext").mkdir()
    for pid, sentences in TEXTS.items():
        r = FetchResult(paperId=pid, pmcid=None, status="complete", fetchedAt="2026-10-15T00:00:00Z",
                        sections=[FetchedSection(id=f"s{n}", heading="Results", text=t) for n, t in enumerate(sentences, start=1)])
        (tmp_path / "fulltext" / f"{pid}.json").write_text(r.model_dump_json(), encoding="utf-8")
    passages.build()
    return tmp_path


ITEMS = [
    {"id": "r-X1-1", "paperId": "X1", "field": "titer_secreted", "quote": "The secreted titre reached its peak", "strainId": "c-necator-h16", "source": "seed"},
    {"id": "cl1-X1-aaaaaaaa", "paperId": "X1", "field": "titer_secreted", "quote": "after the fourth day of xylose feeding", "strainId": "c-necator-h16", "carbonSource": "xylose", "source": "candidate"},
    {"id": "r-X2-1", "paperId": "X2", "field": "titer_secreted", "quote": "Cells of cw15 secreted the reporter", "strainId": "cw15", "source": "seed"},
    {"id": "r-X2-2", "paperId": "X2", "field": "titer_secreted", "quote": "written from a curator's notes, not in the paper", "strainId": "cw15", "source": "seed"},
]


def test_k_holds_only_anchored_items_grouped_by_field_and_organism(index):
    cuts = passages.read_index()
    qs, counts = rageval.build_k(ITEMS, cuts, {"titer_secreted": "Secreted titer (g L-1)"}, {"c-necator-h16": "cupriavidus necator h16"})
    assert counts == {"records": 2, "candidates": 1}, "the curator's-notes quote anchors nowhere"
    texts = sorted(q.text for q in qs)
    assert texts == ["Secreted titer of cupriavidus necator h16 grown on xylose", "Secreted titer of cw15"]
    nec = next(q for q in qs if "necator" in q.text)
    assert nec.relevant == ["X1:s1:0"] and sorted(nec.source["items"]) == ["cl1-X1-aaaaaaaa", "r-X1-1"]


def test_f_covers_only_flows_whose_records_anchor(index):
    cuts = passages.read_index()
    flows = [
        {"id": "F1", "question": "titres?", "recordIds": ["r-X1-1"]},
        {"id": "F2", "question": "notes?", "recordIds": ["r-X2-2"]},
        {"id": "F12", "question": "papers only", "recordIds": []},
    ]
    qs, total = rageval.build_f(flows, {i["id"]: i for i in ITEMS}, cuts)
    assert total == 2 and [q.id for q in qs] == ["F-F1"] and qs[0].relevant == ["X1:s1:0"]


# ── S ──────────────────────────────────────────────────────────────────


def test_a_written_question_that_copies_its_passage_is_discarded():
    passage = "The secreted titre reached its peak after the fourth day of xylose feeding at 37 degrees."
    assert rageval.copies_passage("When did the secreted titre reached its peak?", passage) == "five words in a row from the passage"
    assert rageval.copies_passage("Does the culture work best at 37 degrees?", passage) == "a number from the passage"
    assert rageval.copies_passage("How long does production take on a pentose feed?", passage) is None


def test_the_sample_spreads_across_papers_and_kinds_and_is_seeded():
    def cut(pid, sid, kind, n):
        text = "x " * 150
        return passages.Cut(passages.Passage(id=f"{pid}:{sid}:{n}", paperId=pid, sectionId=sid, heading="h", kind=kind, text=text, start=0, end=len(text)), "c")

    cuts = [cut(p, "s1", "prose", n) for p in "ABC" for n in range(5)] + [cut(p, "t1", "table", 0) for p in "ABC"]
    first = [c.passage.id for c in rageval.sample(cuts, 6)]
    assert first == [c.passage.id for c in rageval.sample(cuts, 6)]
    assert {i.split(":")[0] for i in first} == {"A", "B", "C"}
    assert sum(":t1:" in i for i in first) == 3, "each paper gives its table before a second prose passage"


def test_write_questions_keeps_and_discards_and_counts(index, monkeypatch):
    def ask(**kw):
        ids = [line[1:].split("]")[0] for line in kw["user"].splitlines() if line.startswith("[")]
        assert kw["role"] == "index"
        return llm.Result(
            data={"questions": [
                {"passageId": ids[0], "question": "How long does production take on a pentose feed?"},
                {"passageId": ids[1], "question": "Agitation was kept constant throughout?"},
                {"passageId": "not-shown", "question": "anything"},
            ]},
            model="claude-haiku-5-5", usage=Usage(costUsd=0.0003),
        )

    # The fixture's passages are under the sampler's minimum length: take them in order.
    monkeypatch.setattr(rageval, "sample", lambda cuts, n, seed=rageval.SEED: [c for c in cuts if c.passage.paperId == "X1"][:n])
    meta = rageval.write_questions(2, ask=ask)
    qs, saved = rageval.read_s()
    assert meta["asked"] == 2 and meta["kept"] == 1 and saved["kept"] == 1
    assert meta["discarded"] == {"five words in a row from the passage": 1, "no usable question": 1}
    assert qs[0].relevant == ["X1:s1:0"] and qs[0].set == "S"
    assert meta["costUsd"] == 0.0003


# ── the run, end to end, free lanes ────────────────────────────────────


def test_eval_scores_bm25_writes_the_report_and_the_choice(index, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(rageval, "build_sets", lambda: (
        {"K": [rageval.Question("K1", "K", "secreted titre xylose", ["X1:s1:0"])], "S": [], "F": []},
        [],
    ))
    report = rageval.evaluate()
    bm25 = next(l for l in report.lanes if l.lane == "bm25")
    assert bm25.available and bm25.sets["K"].recall5 == 1.0
    assert not next(l for l in report.lanes if l.lane == "bm25+rerank").available
    rageval.save(report)
    assert rageval.read_report().chosenLane == "bm25"
    assert json.loads((index / "index" / "config.json").read_text())["lane"] == "bm25"


def test_the_report_endpoint_says_how_to_make_one(index):
    from fastapi.testclient import TestClient

    from openferment_core import api

    client = TestClient(api.app, base_url="http://127.0.0.1")
    r = client.get("/api/rag/report")
    assert r.status_code == 404 and "pnpm rag:eval" in r.json()["detail"]
