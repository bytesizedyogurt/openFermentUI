"""A project's retrieval lanes (literature/report.py; ADR-002, Implementation F):
the ground truth built by code from the project's kept candidates, retrieval
under two rules inside the project's scope, the judge's relevance and the
answers graded for grounding, each call counted under its own tally, and a
committed report that holds numbers alone.

Offline: the kit embeds with its local embedder (conftest), and every model is
a stand-in installed as the kit's client, by role. Every text a test writes is
a placeholder carrying a tag of its own, since the kit's rows are committed in
the session's database.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import math
import uuid
from types import SimpleNamespace

import pytest
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import LLMClient
from sqlalchemy import insert

from openferment_core import db
from openferment_core.db import models as t
from openferment_core.literature import kit, report
from openferment_core.models import Candidate, ExtractResponse, Quantity, Usage

HERE = "test-project"
THERE = "other-project"
FIELD = "titer_secreted"
OTHER_FIELD = "titer_intracellular"


@pytest.fixture(autouse=True)
def _kit(kit_database):
    yield
    kit.install_model(None)


@pytest.fixture
def two_projects():
    async def add() -> None:
        async with db.session() as s:
            await s.execute(insert(t.projects).values(id=THERE, name=THERE, created_by="test"))

    db.run(add())


def _tag() -> str:
    return uuid.uuid4().hex[:10]


def _store(tmp_path, project_id: str, tag: str, *sections: str) -> kit.Stored:
    title = f"Placeholder study {tag}"
    text = f"# {title}\n\n" + "".join(f"## Part {i}\n\n{words}\n\n" for i, words in enumerate(sections))
    path = tmp_path / f"{uuid.uuid4().hex}.md"
    path.write_text(text, encoding="utf-8")
    entry = CorpusEntry(path=path, title=title, source=kit.source(project_id, "paste"), license_class="public")
    [stored] = kit.ingest([entry], project_id=project_id, selections=[{"collector": "paste"}], by="test")
    return stored


def _passage(document_id: str, words: str, project_id: str = HERE) -> str:
    return next(p["id"] for p in kit.passages(document_id, project_id=project_id).sections if words in p["text"])


def _candidate(document_id: str, passage_id: str, quote: str, field: str = FIELD, **kw) -> Candidate:
    return Candidate(id=f"c-{uuid.uuid4().hex[:8]}", paperId=document_id, sectionId=passage_id, quote=quote,
                     field=field, value=1.0, unit="g L⁻¹", si=Quantity(value=1.0, unit="g L⁻¹"), **kw)


def _keep(project_id: str, document_id: str, candidates: list[Candidate]) -> None:
    body = ExtractResponse(paperId=document_id, extractedAt="2026-11-08T00:00:00Z", candidates=candidates)

    async def put() -> None:
        async with db.session() as s:
            await s.execute(insert(t.candidates).values(project_id=project_id, document_id=document_id, source="model",
                                                        body=body.model_dump(mode="json"), created_by="test"))

    db.run(put())


def _truth(project_id: str, **kw) -> report.Truth:
    return db.run(report.truth(project_id, **kw))


# ── stand-ins: the tally, and the models by the kit's role ─────────────

_OPEN: contextvars.ContextVar[tuple[list, ...]] = contextvars.ContextVar("standin_tallies", default=())


@contextlib.contextmanager
def tally():
    """A stand-in for `llm.tally`: every stand-in call made within one is
    counted in it, as llm.call counts a model's."""
    spent: list = []
    token = _OPEN.set((*_OPEN.get(), spent))
    try:
        yield spent
    finally:
        _OPEN.reset(token)


def never() -> str | None:
    return None


class Model(LLMClient):
    """A stand-in for one route's model: it answers each kind of prompt the
    lanes send, and counts itself in every tally open around it."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                       max_tokens: int = 2048, json_mode: bool = False) -> str:
        self.prompts.append(prompt)
        for kept in _OPEN.get():
            kept.append(SimpleNamespace(family=self.name, effort="low", max_tokens=max_tokens, outcome="answered",
                                        model=self.name, tried=(self.name,), refused=(), stop_reason="end_turn",
                                        fell_back=False, failure=None,
                                        usage=Usage(inputTokens=10, outputTokens=5, costUsd=0.001)))
        if "You grade the passages a search returned" in prompt:
            n = prompt.split("Passages:", 1)[1].count("\n[")
            return json.dumps({"grades": [{"passage": i, "relevance": 2 if i == 1 else 0} for i in range(1, n + 1)],
                               "rationale": f"rationale-{self.name}"})
        if "groundedness" in prompt:
            return json.dumps({"groundedness": 2, "citation_accuracy": 1, "completeness": 2,
                               "rationale": f"rationale-{self.name}"})
        if json_mode:
            return json.dumps({"entities": [], "relationships": []})
        return f"answer-text-{self.name} [1]"

    def stream(self, prompt: str, **kw):
        async def once():
            yield await self.generate(prompt, **kw)

        return once()


@pytest.fixture
def models():
    held = {role: Model(f"{role}-standin") for role in ("answer", "extraction", "judge")}
    kit.install_model(lambda role: held[role])
    return held


@pytest.fixture
def corpus(tmp_path, two_projects):
    """Two documents of this project and one of the other's, the other's
    holding this project's words too, with candidates kept for each."""
    tag = _tag()
    n = SimpleNamespace(tag=tag, said=f"the placeholder reading {tag} stood at its mark",
                        also=f"the placeholder count {tag} was taken", far=f"the far reading {tag} was noted",
                        organism=f"organism-{tag}", feed=f"feed-{tag}")
    n.one = _store(tmp_path, HERE, tag + "a", f"In this run {n.said}.", f"Later {n.also}.")
    n.two = _store(tmp_path, HERE, tag + "b", f"Elsewhere {n.far}.")
    n.theirs = _store(tmp_path, THERE, tag + "t", f"In that run {n.said}.")
    p_said, p_also = _passage(n.one.document_id, n.said), _passage(n.one.document_id, n.also)
    p_far = _passage(n.two.document_id, n.far)
    _keep(HERE, n.one.document_id, [
        _candidate(n.one.document_id, p_said, n.said, organismText=n.organism, carbonSource=n.feed),
        _candidate(n.one.document_id, p_said, n.said.replace("stood", "  stood"), organismText=n.organism,
                   carbonSource=n.feed),
        _candidate(n.one.document_id, p_also, n.also, field=OTHER_FIELD),
        _candidate(n.one.document_id, p_also, f"words {tag} the passage lacks"),
        _candidate(n.one.document_id, "p999", n.also),
        _candidate(n.one.document_id, p_also, n.also, field="no_such_field"),
    ])
    _keep(HERE, n.two.document_id, [_candidate(n.two.document_id, p_far, n.far)])
    _keep(THERE, n.theirs.document_id, [_candidate(n.theirs.document_id, _passage(n.theirs.document_id, n.said, THERE),
                                                   n.said)])
    n.p_said, n.p_also, n.p_far = p_said, p_also, p_far
    return n


# ── the ground truth ───────────────────────────────────────────────────


def test_a_projects_questions_are_built_by_code_from_its_kept_candidates(corpus):
    n = corpus
    built = _truth(HERE)
    assert (built.read, built.kept, built.groups, built.documents, built.covered) == (7, 4, 3, 2, 2)
    assert built.dropped == {"its field is not the ontology's": 1, "its passage is not one the project holds": 1,
                             "its quote does not stand in its passage": 1}
    by_passage = {(a.document_id, a.passage_id): a for a in built.asked}
    said = by_passage[(n.one.document_id, n.p_said)]
    assert said.question.question == f"What secreted titer is reported for {n.organism} grown on {n.feed}?"
    assert said.question.evidence_phrases == [n.said], "two candidates of one passage and field: one question"
    assert said.question.reference_titles == [f"Placeholder study {n.tag}a"] and said.question.tags == [report.TAG]
    assert len(said.candidates) == 2 and said.field == FIELD
    chunks = {c.chunk_index: c.id for c in kit.document(n.one.document_id, project_id=HERE)[1]}
    assert said.chunk_id == chunks[int(n.p_said[1:])], "its relevant passage is the candidates' chunk"
    assert by_passage[(n.one.document_id, n.p_also)].question.question == "What intracellular titer is reported?"
    # The documents in turn: the first two questions ask of both documents.
    assert [a.question.id for a in built.asked] == ["lq-001", "lq-002", "lq-003"]
    assert {a.document_id for a in built.asked[:2]} == {n.one.document_id, n.two.document_id}
    assert {a.document_id for a in _truth(HERE, limit=2).asked} == {n.one.document_id, n.two.document_id}


def test_neither_project_builds_a_question_from_the_others_candidates(corpus):
    n = corpus
    theirs = _truth(THERE)
    assert [a.document_id for a in theirs.asked] == [n.theirs.document_id] and theirs.read == 1
    assert n.theirs.document_id not in {a.document_id for a in _truth(HERE).asked}


def test_a_project_with_no_kept_candidate_is_refused_in_words(tmp_path, two_projects):
    _store(tmp_path, THERE, _tag(), "Placeholder words alone.")
    with pytest.raises(report.Refused, match="holds no kept candidate"):
        db.run(report.lanes(THERE, tally=tally, stop=never))


@pytest.mark.parametrize("config", ["no_retracted", "with_citations", "no_such_config"])
def test_a_configuration_that_reads_outside_the_project_is_refused_by_name(corpus, config):
    with pytest.raises(report.Refused, match=config):
        db.run(report.lanes(HERE, configs=("interactive", config), tally=tally, stop=never))


# ── retrieval ──────────────────────────────────────────────────────────


def test_retrieval_scores_both_rules_inside_the_projects_scope(corpus):
    n = corpus
    run = db.run(report.lanes(HERE, configs=("interactive", "keyword_only"), tally=tally, stop=never))
    assert run["stopped"] is None and set(run["retrieval"]) == {"interactive", "keyword_only"}
    mine = {n.one.document_id, n.two.document_id}
    for lane in run["retrieval"].values():
        assert {i["documentId"] for ranked in lane["ranked"].values() for i in ranked} <= mine, "the other's never"
        assert lane["kit"]["metrics"]["n"] == lane["passage"]["metrics"]["n"] == 3
        assert lane["spent"] == [], "these configurations ask no model"
    asked = {q["id"]: q for q in run["truth"]["questions"]}
    records = {r["question_id"]: r for r in run["retrieval"]["keyword_only"]["passage"]["records"]}
    for qid, q in asked.items():
        ranked = run["retrieval"]["keyword_only"]["ranked"][qid]
        hit = [r for r, i in enumerate(ranked, 1) if i["chunkId"] == q["chunkId"]]
        assert records[qid]["relevant_ranks"] == hit, "the passage rule counts the candidates' own chunk alone"
    kit_rule = {r["question_id"]: r for r in run["retrieval"]["keyword_only"]["kit"]["records"]}
    assert all(len(kit_rule[q]["relevant_ranks"]) >= len(records[q]["relevant_ranks"]) for q in asked)


def test_the_configurations_that_ask_a_model_run_on_the_installed_one_and_count_their_stages(corpus, models):
    n = corpus
    run = db.run(report.lanes(HERE, configs=("full_deep", "no_hyde"), tally=tally, stop=never))
    deep, no_hyde = run["retrieval"]["full_deep"], run["retrieval"]["no_hyde"]
    mine = {n.one.document_id, n.two.document_id}
    for lane in (deep, no_hyde):
        assert {i["documentId"] for ranked in lane["ranked"].values() for i in ranked} <= mine, "the other's never"
    assert sum(deep["stages"]["hyde"].values()) == 3 and sum(deep["stages"]["graph"].values()) == 3
    assert no_hyde["stages"]["hyde"].get("success", 0) == 0
    assert deep["spent"] and {s["model"] for s in deep["spent"]} == {"extraction-standin"}
    assert models["extraction"].prompts and not models["judge"].prompts and not models["answer"].prompts


def test_a_run_stops_in_words_where_its_stop_says(corpus):
    words = "No model answered: the day's cap holds (a placeholder)."
    calls = iter([None, words])
    run = db.run(report.lanes(HERE, configs=("interactive", "keyword_only"), judge=True, tally=tally,
                              stop=lambda: next(calls, words)))
    assert run["stopped"] == words and list(run["retrieval"]) == ["interactive"]
    assert len(run["retrieval"]["interactive"]["ranked"]) == 2, "the question it stopped after is kept"
    assert "judgeRetrieval" not in run and "answers" not in run


# ── the judge ──────────────────────────────────────────────────────────


def test_the_judge_grades_the_top_ten_and_the_answers_each_under_its_own_tally(corpus, models):
    run = db.run(report.lanes(HERE, configs=("interactive", "full_deep", "vector_only"), judge=True, tally=tally,
                              stop=never))
    assert set(run["judgeRetrieval"]) == set(run["answers"]) == {"interactive", "full_deep"}
    for name, lane in run["judgeRetrieval"].items():
        assert lane["graded"] == lane["asked"] == 3 and lane["failed"] == 0
        for r in lane["records"]:
            assert r["grades"][0] == 2 and len(r["grades"]) == r["passages"] == len(run["retrieval"][name]["ranked"][
                r["questionId"]])
            assert [s["model"] for s in r["spent"]] == ["judge-standin"], "one call, its own tally"
        assert lane["hit_at_5"]["mean"] == 1.0
    for name, lane in run["answers"].items():
        assert lane["answered"] == lane["graded"] == 3
        for r in lane["records"]:
            assert r["answer"] == "answer-text-answer-standin [1]" and r["sources"].startswith("[1] ")
            assert r["grounding"]["groundedness"] == 2 and r["grounding"]["rationale"] == "rationale-judge-standin"
            assert {s["model"] for s in r["judgeSpent"]} == {"judge-standin"}
            assert "answer-standin" in {s["model"] for s in r["answerSpent"]}
            assert "judge-standin" not in {s["model"] for s in r["answerSpent"]}
    relevance = [p for p in models["judge"].prompts if "You grade the passages" in p]
    assert len(relevance) == 6 and all("[1] " in p for p in relevance)


def test_a_judges_answer_that_does_not_grade_every_passage_is_refused():
    assert report.grades({"grades": [{"passage": 2, "relevance": 1}, {"passage": 1, "relevance": 5}]}, 2) == [2, 1]
    for payload in ({"grades": [{"passage": 1, "relevance": 1}]}, {"verdict": "fine"}, ["no"]):
        with pytest.raises(ValueError):
            report.grades(payload, 2)
    assert report.judged([2, 0, 1]) == pytest.approx({"precision_at_10": 2 / 3, "hit_at_5": 1.0, "hit_at_10": 1.0,
                                                      "ndcg_at_10": 3.5 / (3 + 1 / math.log2(3))})
    assert report.judged([0, 0, 2])["hit_at_5"] == 1.0 and report.judged([1, 1])["hit_at_10"] == 0.0
    assert report.judged([2, 1])["ndcg_at_10"] == 1.0 > report.judged([1, 2])["ndcg_at_10"]


# ── the committed report ───────────────────────────────────────────────


ROUTES = {"index": {"models": ["index-standin"], "effort": "low"}, "judge": {"models": ["judge-standin"], "effort": "max"}}


def test_the_committed_report_quotes_no_question_passage_answer_or_rationale(corpus, models, tmp_path):
    n = corpus
    run = db.run(report.lanes(HERE, configs=("interactive", "full_deep"), judge=True, tally=tally, stop=never))
    part = report.public(run, routes=ROUTES, commit="abc1234")
    out = tmp_path / "reports" / "literature-retrieval"
    report.write(part, out=out)
    md, js = out.with_suffix(".md").read_text(), out.with_suffix(".json").read_text()
    for words in (n.said, n.also, n.far, n.organism, n.feed, n.tag, "answer-text", "rationale-", "Placeholder study"):
        assert words not in md and words not in js, words
    assert f"`{HERE}`" in md and "abc1234" in md and "judge-standin" in md and "from-candidates" in md
    assert part["truth"]["questions"] == 3 and part["cost"]["total"] > 0
    assert json.loads(js)["projects"][HERE]["answers"]["full_deep"]["graded"] == 3


def test_writing_a_part_keeps_the_demo_and_reads_an_old_shaped_json_as_the_demo(tmp_path):
    out = tmp_path / "literature-retrieval"
    demo = {"kind": "retrieval", "configs": {"interactive": {"hit_at_5": 1.0}}}
    out.with_suffix(".json").write_text(json.dumps(demo))
    out.with_suffix(".md").write_text("# Literature retrieval report\n\nThe demo's words.\n")
    part = {"project": "p-one", "at": "2026-11-08T00:00:00+00:00", "commit": None, "configs": ["interactive"],
            "judged": False, "stopped": None, "routes": {},
            "corpus": {"documents": 1, "chunks": 2, "tokens": 3, "entities": 0, "relationships": 0, "communities": 0,
                       "embedding_versions": [], "latest_ingested_at": None, "chunksRead": 0, "entityTypes": {},
                       "relationTypes": {}},
            "truth": {"questions": 1, "read": 1, "kept": 1, "dropped": {}, "groups": 1, "documents": 1, "covered": 1,
                      "fields": {FIELD: 1}},
            "retrieval": {}, "judgeRetrieval": {}, "answers": {},
            "cost": {"retrieval": 0.0, "judgeRetrieval": 0.0, "answers": 0.0, "total": 0.0}}
    report.write(part, out=out)
    report.write({**part, "project": "p-two"}, out=out)
    held = json.loads(out.with_suffix(".json").read_text())
    assert held["kind"] == "retrieval-report" and held["demo"] == demo and list(held["projects"]) == ["p-one", "p-two"]
    md = out.with_suffix(".md").read_text()
    assert md.startswith("# Literature retrieval report\n\nThe demo's words.\n") and md.count(report.PROJECTS_MARK) == 1
    assert md.index("`p-one`") < md.index("`p-two`")
    assert report.read(out) == (demo, held["projects"])
    # The demo's run keeps the projects' parts: _save with new demo words and payload.
    report._save(out, "# Literature retrieval report\n\nNew demo words.\n", {"kind": "retrieval"}, held["projects"])
    again = out.with_suffix(".md").read_text()
    assert again.startswith("# Literature retrieval report\n\nNew demo words.\n") and "`p-two`" in again
