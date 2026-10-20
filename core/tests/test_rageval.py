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
    # The reply for a passage not asked is ignored; each passage asked is
    # kept or discarded once (§4.R).
    assert meta["discarded"] == {"five words in a row from the passage": 1}
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


def test_a_lane_whose_model_refuses_is_scored_unavailable_with_the_reason(index, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stand-in")

    def refused(**kw):
        raise llm.ModelUnavailable("The Anthropic API refused the request as malformed: not scoped to a workspace")

    monkeypatch.setattr(rageval, "build_sets", lambda: (
        {"K": [rageval.Question("K1", "K", "secreted titre xylose", ["X1:s1:0"])], "S": [], "F": []},
        [],
    ))
    report = rageval.evaluate(ask=refused, lanes=["bm25", "bm25+expand"])
    expand = next(l for l in report.lanes if l.lane == "bm25+expand")
    assert not expand.available and "not scoped to a workspace" in expand.why and expand.sets == {}
    assert report.chosenLane == "bm25"


def test_one_refused_helper_call_leaves_the_question_unscored_and_the_lane_scored(index, monkeypatch):
    # Live test, 2026-10-16: the safety classifier declined one helper call
    # and the whole lane was discarded after it had paid for the rest. A
    # refusal now costs its question alone, and the lane says how many.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stand-in")

    def ask(**kw):
        text = json.dumps(kw.get("messages") or kw.get("user") or kw)
        if "refuse me" in text:
            raise llm.ModelRefused("bio", ["claude-haiku-5-5"], llm.Usage(costUsd=0.001, models=["claude-haiku-5-5"]))
        return llm.Result(data={"phrasings": ["secreted titre"]}, model="claude-haiku-5-5",
                          usage=llm.Usage(costUsd=0.001, models=["claude-haiku-5-5"]))

    monkeypatch.setattr(rageval, "build_sets", lambda: (
        {"K": [rageval.Question("K1", "K", "secreted titre xylose", ["X1:s1:0"]),
               rageval.Question("K2", "K", "refuse me titre", ["X1:s1:0"])], "S": [], "F": []},
        [],
    ))
    report = rageval.evaluate(ask=ask, lanes=["bm25", "bm25+expand"])
    expand = next(l for l in report.lanes if l.lane == "bm25+expand")
    assert expand.available and expand.why is None
    assert expand.refused == 1
    assert expand.sets["K"].questions == 1
    assert expand.score is not None


def test_a_refused_key_still_makes_the_lane_unavailable(index, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stand-in")

    def unavailable(**kw):
        raise llm.ModelUnavailable("today's budget is spent")

    monkeypatch.setattr(rageval, "build_sets", lambda: (
        {"K": [rageval.Question("K1", "K", "secreted titre xylose", ["X1:s1:0"])], "S": [], "F": []},
        [],
    ))
    report = rageval.evaluate(ask=unavailable, lanes=["bm25+expand"])
    assert not report.lanes[0].available and report.lanes[0].refused == 0


# ── one thread (OF-BLD-016 §4.1) ───────────────────────────────────────
# The scorecard rerun on thread Q alone: its questions drawn from thread Q's
# papers, while every search still runs over the whole index. STAND-IN text.

THREAD_TEXTS = {
    "Q1": ["The yeast culture converted the glucose feed into ethanol over the course of the batch, and the broth "
           "was sampled at each stage so that sugar and product could be followed together across the whole run of "
           "the fermentation in the stirred vessel."],
    "Q2": ["Biomass formation slowed once the alcohol accumulated in the medium, which the authors attribute to "
           "inhibition of growth by the product itself; the effect was followed by optical density in every flask "
           "and compared between the two strains they grew."],
    "P1": ["The bacterium stored the polyester inside its cells when nitrogen ran short, and granules were seen "
           "under the microscope by the end of the cultivation on the pretreated straw hydrolysate that the group "
           "prepared in its own pilot unit beforehand."],
    "B5": ["The alga secreted the reporter protein into the medium when grown on acetate in the light, and the "
           "protein was recovered from the supernatant after the cells were removed by gentle centrifugation at the "
           "end of each culture in the shaken flasks."],
}


@pytest.fixture()
def thread_index(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(passages, "_papers_meta", lambda: {})
    monkeypatch.setattr(passages, "_LOADED", None)
    (tmp_path / "fulltext").mkdir()
    for pid, sentences in THREAD_TEXTS.items():
        r = FetchResult(paperId=pid, pmcid=None, status="complete", fetchedAt="2026-10-20T00:00:00Z",
                        sections=[FetchedSection(id=f"s{n}", heading="Results", text=t) for n, t in enumerate(sentences, start=1)])
        (tmp_path / "fulltext" / f"{pid}.json").write_text(r.model_dump_json(), encoding="utf-8")
    passages.build()
    return tmp_path


def test_a_paper_is_on_a_thread_when_its_id_is_the_letter_then_a_number():
    assert rageval.on_thread("Q1", "Q") and rageval.on_thread("Q22", "Q") and rageval.on_thread("H4", "H")
    for pid in ("P1", "QX1", "Q", "Q1a", "AQ1", ""):
        assert not rageval.on_thread(pid, "Q"), pid
    assert rageval.on_thread("P3", None), "no thread: every paper, as before"


def _asking(asked: list[str]):
    def ask(**kw):
        ids = [line[1:].split("]")[0] for line in kw["user"].splitlines() if line.startswith("[")]
        asked.extend(ids)
        return llm.Result(data={"questions": [{"passageId": i, "question": "Which feed suits this organism best?"} for i in ids]},
                          model="claude-haiku-5-5", usage=Usage(costUsd=0.0001))
    return ask


def test_written_questions_on_a_thread_sample_only_its_passages(thread_index):
    asked: list[str] = []
    meta = rageval.write_questions(10, ask=_asking(asked), thread="Q")
    assert asked and {a.split(":")[0] for a in asked} == {"Q1", "Q2"}
    assert meta["thread"] == "Q" and meta["asked"] == len(asked) == 2
    qs, saved = rageval.read_s("Q")
    assert {q.relevant[0].split(":")[0] for q in qs} == {"Q1", "Q2"} and saved["thread"] == "Q"


def test_written_questions_on_a_thread_leave_the_set_for_every_paper_alone(thread_index):
    asked: list[str] = []
    every = rageval.write_questions(10, ask=_asking(asked))
    assert {a.split(":")[0] for a in asked} == set(THREAD_TEXTS), "no thread: every paper, as before"
    assert "thread" not in every
    before = (thread_index / "rageval" / "questions.jsonl").read_text(encoding="utf-8")
    rageval.write_questions(10, ask=_asking([]), thread="Q")
    assert (thread_index / "rageval" / "questions.jsonl").read_text(encoding="utf-8") == before
    qs, _ = rageval.read_s()
    assert len(qs) == every["kept"] == 4
    assert len(rageval.read_s("Q")[0]) == 2


def test_a_thread_with_no_passage_writes_nothing(thread_index):
    with pytest.raises(ValueError, match="thread Z"):
        rageval.write_questions(10, ask=_asking([]), thread="Z")
    assert not (thread_index / "rageval" / "questions-Z.jsonl").exists()


THREAD_ITEMS = [
    {"id": "cl1-Q1-aaaaaaaa", "paperId": "Q1", "field": "ethanol_titre", "quote": "converted the glucose feed into ethanol",
     "strainId": "s-cerevisiae-s288c", "carbonSource": "glucose", "source": "candidate"},
    {"id": "r-Q2-test", "paperId": "Q2", "field": "ethanol_inhibition_ki", "quote": "inhibition of growth by the product itself",
     "strainId": "s-cerevisiae-s288c", "source": "seed"},
    {"id": "cl1-P1-bbbbbbbb", "paperId": "P1", "field": "pha_content", "quote": "stored the polyester inside its cells",
     "strainId": "c-necator-h16", "source": "candidate"},
    {"id": "r-B5-test", "paperId": "B5", "field": "titer_secreted", "quote": "secreted the reporter protein into the medium",
     "strainId": "cw15", "source": "seed"},
]


@pytest.fixture()
def thread_pool(thread_index, monkeypatch):
    from types import SimpleNamespace

    from openferment_core import corpus, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda **kw: SimpleNamespace(records=THREAD_ITEMS))
    monkeypatch.setattr(corpus, "load_corpus", lambda: SimpleNamespace(records_by_id={i["id"]: i for i in THREAD_ITEMS if i["source"] == "seed"}))
    monkeypatch.setattr(rageval, "_corpus_extras", lambda: ({"ethanol_titre": "Ethanol titre (g L-1)", "ethanol_inhibition_ki": "Ethanol inhibition constant (g L-1)",
                                                             "pha_content": "PHA content (%)", "titer_secreted": "Secreted titer (g L-1)"}, {}))
    return thread_index


def test_k_on_a_thread_holds_only_that_threads_items(thread_pool):
    sets, infos = rageval.build_sets(thread="Q")
    assert sorted(i for q in sets["K"] for i in q.source["items"]) == ["cl1-Q1-aaaaaaaa", "r-Q2-test"]
    assert all(r.split(":")[0] in {"Q1", "Q2"} for q in sets["K"] for r in q.relevant)
    k = next(i for i in infos if i.name == "K")
    assert k.questions == 2 and "thread Q" in k.note and "1 records and 1 anchored candidates" in k.note
    # The authored flows cite no thread Q record: F is empty, and says so.
    f = next(i for i in infos if i.name == "F")
    assert sets["F"] == [] and f.questions == 0 and "thread Q" in f.note
    # No thread: every item, as before.
    every, every_infos = rageval.build_sets()
    assert len(every["K"]) == 4 and "thread" not in next(i for i in every_infos if i.name == "K").note


def test_eval_on_a_thread_reads_that_threads_written_questions(thread_pool):
    rageval.write_questions(10, ask=_asking([]))
    rageval.write_questions(10, ask=_asking([]), thread="Q")
    on_q, infos = rageval.build_sets(thread="Q")
    assert len(on_q["S"]) == 2 and all(q.relevant[0].split(":")[0] in {"Q1", "Q2"} for q in on_q["S"])
    s = next(i for i in infos if i.name == "S")
    assert "thread Q" in s.note and "2 kept of 2 asked" in s.note
    assert len(rageval.build_sets()[0]["S"]) == 4


def test_the_report_carries_its_thread_and_retrieval_searches_every_paper(thread_index, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    seen: dict = {}

    def sets(thread=None):
        seen["thread"] = thread
        return {"K": [rageval.Question("K1", "K", "alcohol inhibits growth of the yeast", ["Q2:s1:0"])], "S": [], "F": []}, []

    monkeypatch.setattr(rageval, "build_sets", sets)
    report = rageval.evaluate(lanes=["bm25"], thread="Q")
    assert seen["thread"] == "Q" and report.thread == "Q"
    assert report.papersIndexed == 4, "the index searched is the whole one"
    rageval.save(report)
    assert rageval.read_report().thread == "Q"
    config = json.loads((thread_index / "index" / "config.json").read_text())
    assert config["thread"] == "Q" and config["lane"] == report.chosenLane
    # Without one, nothing names a thread.
    plain = rageval.evaluate(lanes=["bm25"])
    assert plain.thread is None
    rageval.save(plain)
    assert "thread" not in json.loads((thread_index / "index" / "config.json").read_text())


def test_the_command_line_takes_a_thread(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    calls: list = []
    monkeypatch.setattr(rageval, "write_questions", lambda n, thread=None: calls.append(("questions", n, thread)) or {"kept": 0, "asked": 0, "discarded": {}, "costUsd": 0.0})
    monkeypatch.setattr(rageval, "evaluate", lambda thread=None: calls.append(("eval", thread)) or "report")
    monkeypatch.setattr(rageval, "save", lambda report: None)
    monkeypatch.setattr(rageval, "_print", lambda report: None)
    assert rageval.main(["questions", "--n", "100", "--thread", "Q"]) == 0
    # pnpm may pass its own "--" through.
    assert rageval.main(["eval", "--", "--thread", "Q"]) == 0
    assert rageval.main(["questions"]) == 0 and rageval.main(["eval"]) == 0
    assert calls == [("questions", 100, "Q"), ("eval", "Q"), ("questions", 200, None), ("eval", None)]
    assert rageval.main(["eval", "--thread", "q1"]) == 2 and rageval.main(["eval", "--thread"]) == 2
    assert len(calls) == 4


def test_the_report_says_which_lane_search_runs_on_when_a_person_holds_it_apart(index, monkeypatch):
    """OF-BLD-016 §4.1: the rule may choose a lane a person has not adopted
    (tonight: bm25+rerank, a model call of about twenty seconds a search,
    held off for the meeting). Witness must say which lane search runs on,
    from config.json, beside the rule's choice, never one for the other."""
    from fastapi.testclient import TestClient

    from openferment_core import api

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(rageval, "build_sets", lambda: (
        {"K": [rageval.Question("K1", "K", "secreted titre xylose", ["X1:s1:0"])], "S": [], "F": []},
        [],
    ))
    rageval.save(rageval.evaluate())
    config = index / "index" / "config.json"
    held = json.loads(config.read_text())
    held["lane"] = "hybrid"
    config.write_text(json.dumps(held))
    body = TestClient(api.app, base_url="http://127.0.0.1").get("/api/rag/report").json()
    assert body["chosenLane"] == "bm25" and body["laneInUse"] == "hybrid"
