"""`python -m openferment_core.literature.report` — the retrieval report
(ADR-002; execution prompt §8.2), and the lanes `literature_live.py` runs over
a project's own corpus (alpha 2.2 F.5; ADR-002, Implementation F).

    pnpm lit:report                       the kit's demo corpus, as below
    pnpm lit:report --project <id> ...    a project's lanes (literature_live.py)

THE DEMO. In a database of its own on the tests' server
(OPENFERMENT_TEST_DATABASE_URL, dropped after), a project holds the five demo
documents (core/tests/fixtures/kit-demo/, CC0, fictional), embedded by
FastEmbed. Each of the kit's seed questions for that corpus is asked of the
retriever inside the project's scope, in the configurations that ask no model
(vector and keyword together, as Search runs; each alone), and the kit scores
where the passage holding the answer's evidence ranks: hit at 5 and 10, mean
reciprocal rank, nDCG at 10, each with a bootstrap interval. It needs no key.

A PROJECT'S LANES (`lanes`). The ground truth is built by code from the
project's kept candidates (`truth`): a candidate whose quote stands verbatim
in the passage it cites, grouped by document, passage and field, one question
a group, its words the field's name and the organism and feed the group's
candidates name; its relevant passage is that chunk. No model writes or reads
a question. Then:

- retrieval: each question asked of the retriever in the project's scope in
  each configuration of `PROJECT_CONFIGS`, scored under the kit's rule (a
  passage of the question's document, or one holding a quote) and under the
  passage rule (the candidate's own chunk);
- the judge's relevance (`--judge`): the `judge` route grades the top ten
  passages of `interactive` and `full_deep` for each question, 0 to 2;
- answers (`--judge`): the kit's answer on the `explain` route through
  `interactive` and `full_deep`, each graded for grounding by the `judge`
  route (the kit's blind grounding pass).

`literature/` imports no `llm`: the command installs the model client
(`kit.install_model`) and hands in `tally`, a context in which every model
call is counted (`llm.tally`), and `stop`, read after each question, whose
words (no key, the account's usage limit, the day's cap) end the run there.
Each answer and each judgement is counted under its own tally, so it carries
the model that gave it.

`lanes` answers the run whole: every question, answer, rationale and grade.
The command writes that to a file under the service's data folder, outside
git, and `public` keeps the numbers alone (scores, counts, ids, models, USD,
seconds), which `write` sets beside the demo in
docs/reports/literature-retrieval.md and .json: the committed report quotes
no question, passage, answer, rationale or entity name.
"""
from __future__ import annotations

import contextlib
import dataclasses
import itertools
import json
import math
import os
import secrets
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sci_rag.answer.generator import format_sources
from sci_rag.db.models import Chunk, Document
from sci_rag.evals.judge import grade_grounding
from sci_rag.evals.report import corpus_fingerprint, retrieval_markdown, retrieval_payload
from sci_rag.evals.retrieval_eval import (
    DEFAULT_ABLATIONS,
    QuestionRetrievalRecord,
    RetrievalEvalResult,
    is_relevant,
    run_retrieval_eval,
)
from sci_rag.evals.seeds import SeedQuestion, load_seed_questions
from sci_rag.evals.stats import bootstrap_ci
from sci_rag.ingest.manifest import CorpusEntry
from sqlalchemy import insert, select

from .. import db, migrations, projects, units
from ..db import migrate
from ..db import models as t
from ..models import Candidate
from . import EMBEDDING_DIM, EMBEDDING_MODEL, kit

CORE = Path(__file__).parent.parent.parent
DEMO = CORE / "tests" / "fixtures" / "kit-demo"
OUT = CORE.parent / "docs" / "reports" / "literature-retrieval"
PROJECT = "retrieval-report"
# The kit's configurations that ask no model.
CONFIGS = ("interactive", "vector_only", "keyword_only")
#: The line in the report's Markdown after which the projects' parts stand.
PROJECTS_MARK = "<!-- The parts below are written by `pnpm lit:report --project <id> --render`. -->"

# ── the demo ───────────────────────────────────────────────────────────


def _entries() -> list[CorpusEntry]:
    rows = [json.loads(line) for line in (DEMO / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
    return [CorpusEntry(**{**row, "path": DEMO / row["path"], "source": kit.source(PROJECT, "upload")}) for row in rows]


async def _project() -> None:
    async with db.session() as s:
        await s.execute(insert(t.projects).values(id=PROJECT, name="Retrieval report", created_by="the report"))


def _run() -> tuple[str, dict]:
    db.run(_project())
    entries = _entries()
    kit.ingest(entries, project_id=PROJECT, selections=[{"collector": "upload"} for _ in entries], by="the report")
    questions = load_seed_questions(DEMO / "eval_seed_questions.jsonl")
    configs = [c for c in DEFAULT_ABLATIONS if c.name in CONFIGS]
    service = kit.service()

    async def evaluate():
        with projects.using(PROJECT):
            scope = await kit._narrowed(None)
            results = await run_retrieval_eval(service.retriever, questions, configs=configs, scope=scope)
        return results, await corpus_fingerprint(service.session_factory)

    results, fingerprint = db.run(evaluate())
    provenance = {"embedding": f"fastembed:{EMBEDDING_MODEL}@{EMBEDDING_DIM}", "models": "none asked",
                  "corpus": "Sci RAG Kit 0.5.0 demo corpus (data/demo at 26b3990)"}
    payload = retrieval_payload(results, fingerprint, questions=questions, provenance=provenance)
    when = datetime.now(UTC).strftime("%Y-%m-%d")
    head = [
        "<!-- Written by `pnpm lit:report` (core/openferment_core/literature/report.py); regenerate, do not edit. -->",
        "",
        "# Literature retrieval report",
        "",
        f"Sci RAG Kit's retrieval evaluation over its demo corpus, as openFerment runs the kit ({when}):",
        f"FastEmbed `{EMBEDDING_MODEL}` ({EMBEDDING_DIM} dimensions), the project's scope, and the",
        "configurations that ask no model. `interactive` is what BioRepo → Search runs. The kit's",
        "note below compares rows with `full_deep`, which asks a model and is not run here: read",
        "`interactive` as the baseline instead.",
        "",
    ]
    kit_text = retrieval_markdown(results, fingerprint, questions=questions).replace(
        "# Retrieval evaluation", "## The kit's retrieval evaluation", 1
    )
    return "\n".join(head) + "\n" + kit_text, payload


def main(argv: list[str]) -> int:
    server = os.environ.get("OPENFERMENT_TEST_DATABASE_URL", "").strip() or \
        "postgresql://openferment:openferment@127.0.0.1:5432/openferment_test"
    name = f"lit_report_{os.getpid()}_{secrets.token_hex(3)}"
    url = migrate.create(name, server)
    try:
        migrations.upgrade(url)
        db.use_engine(db.make_engine(url, pool_size=2, max_overflow=2))
        kit.use_database(url)
        markdown, payload = _run()
    finally:
        kit.use_database(None)
        engine = db.use_engine(None)
        if engine is not None:
            db.run(engine.dispose())
        migrate.drop(name, server)
    _, projects_part = read(OUT)
    _save(OUT, markdown, payload, projects_part)
    print(markdown)
    print(f"\nwritten to {OUT.with_suffix('.md').relative_to(CORE.parent)} and .json")
    return 0


# ── the committed report: the demo and each project's public numbers ───


def read(out: Path | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """The committed JSON's two parts (`OUT` unless another is named): the
    demo's payload, and each project's public numbers by id. A JSON written
    before the projects' parts existed is the kit's payload alone, and reads
    as the demo."""
    path = (out or OUT).with_suffix(".json")
    if not path.is_file():
        return None, {}
    held = json.loads(path.read_text(encoding="utf-8"))
    if held.get("kind") == "retrieval-report":
        return held.get("demo"), dict(held.get("projects") or {})
    return held, {}


def _demo_text(out: Path) -> str:
    path = out.with_suffix(".md")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return text.split(PROJECTS_MARK, 1)[0].rstrip() + "\n"


def _save(out: Path, demo_md: str, demo: dict[str, Any] | None, parts: dict[str, Any]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    markdown = demo_md.rstrip() + "\n"
    if parts:
        markdown += "\n" + PROJECTS_MARK + "\n\n" + "\n".join(render(parts[k]) for k in sorted(parts))
    out.with_suffix(".md").write_text(markdown.rstrip() + "\n", encoding="utf-8")
    whole = {"kind": "retrieval-report", "demo": demo, "projects": {k: parts[k] for k in sorted(parts)}}
    out.with_suffix(".json").write_text(json.dumps(whole, indent=2, default=str) + "\n", encoding="utf-8")


def write(part: dict[str, Any], out: Path | None = None) -> None:
    """Set a project's public numbers (`public`) in the committed report
    (`OUT` unless another is named), beside the demo and the other projects'
    parts, each as it stood."""
    out = out or OUT
    demo, parts = read(out)
    parts[part["project"]] = part
    _save(out, _demo_text(out), demo, parts)


# ── a project's ground truth, built from its kept candidates ──────────────

#: The configurations a project's retrieval lane runs, of the kit's own.
#: `no_retracted` carries a scope of its own and `with_citations` follows
#: citations the project may not hold, so neither stays inside a project.
PROJECT_CONFIGS = ("interactive", "vector_only", "keyword_only", "full_deep", "no_graph", "no_hyde")
#: The configurations the judge grades and the answers are given through,
#: with the profile each answer runs on.
JUDGED = {"interactive": "interactive", "full_deep": "deep"}
#: The passages a retrieval keeps, and the judge reads, a question.
TOP = 10
#: The longest passage the judge is shown, as the kit cuts a passage for its
#: graph build.
PASSAGE_CHARS = 4000
#: The tag every built question carries: its words and its evidence are a
#: model's extraction that no person has reviewed.
TAG = "from-candidates"
#: The words a project with no question to ask is refused in.
NO_QUESTIONS = ("Project {project} holds no kept candidate whose quote stands in the passage it cites, so no "
                "question can be built: extract its documents on Intake first (POST /api/intake/<document>/extract).")


@dataclass(frozen=True)
class Asked:
    """One question of a project's ground truth: the kit's `SeedQuestion`
    (the document's title as its reference, the group's quotes as its
    evidence), with the passage the group's candidates cite, its chunk, the
    field and the candidates' ids."""

    question: SeedQuestion
    document_id: str
    passage_id: str
    chunk_id: str
    field: str
    candidates: tuple[str, ...]


@dataclass
class Truth:
    """What a project's candidates gave: the questions, the candidates read,
    kept and left out (by reason), and the documents the project holds and
    those a question asks of."""

    asked: list[Asked] = field(default_factory=list)
    read: int = 0
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    documents: int = 0
    covered: int = 0
    groups: int = 0


def _spaced(text: str) -> str:
    return " ".join(text.split())


def _body(content: str) -> str:
    _, sep, rest = content.partition("\n\n")
    return rest if sep else content


def _index(passage_id: str) -> int:
    return int(passage_id[1:]) if passage_id[1:].isdigit() else -1


async def _corpus(project_id: str) -> tuple[dict[str, str], dict[tuple[str, str], tuple[str, str]]]:
    """The project's documents' titles, and each passage's chunk id and words
    by document and passage id."""
    documents = list((await kit.visible(project_id)).documents)
    if not documents:
        return {}, {}
    async with kit.service().session_factory() as session:
        titles = dict((await session.execute(
            select(Document.id, Document.title).where(Document.id.in_(documents)))).all())
        rows = (await session.execute(select(Chunk.id, Chunk.document_id, Chunk.chunk_index, Chunk.content)
                                      .where(Chunk.document_id.in_(documents)))).all()
    return titles, {(d, kit.passage_id(i)): (chunk_id, _body(content)) for chunk_id, d, i, content in rows}


async def _candidates(project_id: str) -> tuple[list[Candidate], int]:
    """The candidates the project keeps (each extraction's and each person's
    entries), and how many could not be read as a candidate."""
    async with db.session() as s:
        bodies = (await s.execute(select(t.candidates.c.body).where(t.candidates.c.project_id == project_id)
                                  .order_by(t.candidates.c.document_id, t.candidates.c.source))).scalars().all()
    found, unread = [], 0
    for body in bodies:
        for raw in (body or {}).get("candidates") or []:
            try:
                found.append(Candidate.model_validate(raw))
            except ValueError:
                unread += 1
    return found, unread


def _one(values: list[str | None]) -> str | None:
    held = {v.strip() for v in values if v and v.strip()}
    return held.pop() if len(held) == 1 and all(v and v.strip() for v in values) else None


def _words(field_name: str, organism: str | None, feed: str | None) -> str:
    asked = f"What {field_name[:1].lower()}{field_name[1:]} is reported"
    if organism:
        asked += f" for {organism}"
    if feed:
        asked += f" grown on {feed}"
    return asked + "?"


async def truth(project_id: str, *, limit: int | None = None) -> Truth:
    """The project's ground truth, built by code from its kept candidates. A
    candidate counts when its passage is one of the project's, its quote
    stands in that passage (whitespace aside) and its field is the
    ontology's. One question a group of them by document, passage and field;
    the groups are taken a document at a time in turn (documents by title,
    passages in order), so `limit` spreads the questions over the documents.
    Runs on the database loop."""
    titles, passages = await _corpus(project_id)
    candidates, unread = await _candidates(project_id)
    built = Truth(documents=len(titles), read=len(candidates) + unread)
    if unread:
        built.dropped["unreadable as a candidate"] = unread
    groups: dict[tuple[str, str, str], list[Candidate]] = {}
    for c in candidates:
        where = passages.get((c.paperId, c.sectionId))
        reason = None
        if where is None:
            reason = "its passage is not one the project holds"
        elif not c.quote.strip() or _spaced(c.quote) not in _spaced(where[1]):
            reason = "its quote does not stand in its passage"
        elif units.field(c.field) is None:
            reason = "its field is not the ontology's"
        if reason:
            built.dropped[reason] = built.dropped.get(reason, 0) + 1
            continue
        built.kept += 1
        groups.setdefault((c.paperId, c.sectionId, c.field), []).append(c)
    built.groups = len(groups)
    by_document: dict[str, list[tuple[str, str, str]]] = {}
    for key in sorted(groups, key=lambda k: (titles.get(k[0], ""), k[0], _index(k[1]), k[2])):
        by_document.setdefault(key[0], []).append(key)
    order = [key for turn in itertools.zip_longest(*by_document.values()) for key in turn if key]
    for n, key in enumerate(order[:limit] if limit else order, start=1):
        document_id, passage, field_id = key
        group = groups[key]
        name = str((units.field(field_id) or {}).get("name") or field_id)
        words = _words(name, _one([c.organismText or c.organism for c in group]), _one([c.carbonSource for c in group]))
        question = SeedQuestion(id=f"lq-{n:03d}", question=words, reference_titles=[titles[document_id]],
                                evidence_phrases=sorted({_spaced(c.quote) for c in group}), tags=[TAG])
        built.asked.append(Asked(question, document_id, passage, passages[(document_id, passage)][0], field_id,
                                 tuple(c.id for c in group)))
    built.covered = len({a.document_id for a in built.asked})
    return built


# ── what a lane spent ──────────────────────────────────────────────────

Tally = Callable[[], AbstractContextManager[list[Any]]]
Stop = Callable[[], str | None]


def as_spent(entry: Any) -> dict[str, Any]:
    """One counted call (`llm.Spent`) as the run keeps it."""
    usage = entry.usage
    return {"family": entry.family, "effort": entry.effort, "maxTokens": entry.max_tokens, "outcome": entry.outcome,
            "model": entry.model, "tried": list(entry.tried), "refused": list(entry.refused),
            "stopReason": entry.stop_reason, "fellBack": entry.fell_back, "failure": entry.failure,
            "inputTokens": usage.inputTokens, "outputTokens": usage.outputTokens, "usd": usage.costUsd}


def counted(spent: list[dict[str, Any]]) -> dict[str, Any]:
    """Calls, tokens and USD, the models that answered, and the calls refused,
    unavailable, fallen back and cut at their ceiling."""
    return {
        "calls": len(spent),
        "inputTokens": sum(s["inputTokens"] for s in spent),
        "outputTokens": sum(s["outputTokens"] for s in spent),
        "usd": round(sum(s["usd"] for s in spent), 6),
        "models": dict(sorted(Counter(s["model"] for s in spent if s["model"]).items())),
        "refused": sum(s["outcome"] == "refused" for s in spent),
        "unavailable": sum(s["outcome"] == "unavailable" for s in spent),
        "fellBack": sum(bool(s["fellBack"]) for s in spent),
        "truncated": sum(s["stopReason"] == "max_tokens" for s in spent),
    }


@contextlib.contextmanager
def _counted_into(tally: Tally, into: list[dict[str, Any]]) -> Iterator[None]:
    """A tally of its own around the calls made within, each kept in `into`."""
    with tally() as spent:
        try:
            yield
        finally:
            into.extend(as_spent(s) for s in spent)


def _ci(values: list[float]) -> dict[str, float] | None:
    return bootstrap_ci(values).as_dict() if values else None


# ── the retrieval lane ─────────────────────────────────────────────────


def _record(question_id: str, ranks: list[int], retrieved: int, degraded: list[str]) -> QuestionRetrievalRecord:
    first = ranks[0] if ranks else None
    return QuestionRetrievalRecord(question_id=question_id, first_relevant_rank=first,
                                   hit_at_5=first is not None and first <= 5, hit_at_10=first is not None and first <= 10,
                                   retrieved=retrieved, degraded_stages=degraded, relevant_ranks=ranks)


def _scored(result: RetrievalEvalResult) -> dict[str, Any]:
    return {"metrics": result.metrics_with_ci, "records": [dataclasses.asdict(r) for r in result.records]}


async def _retrieval(asked: list[Asked], configs: tuple[str, ...], scope: Any, shown: dict[tuple[str, str], list[str]],
                     *, tally: Tally, stop: Stop) -> tuple[dict[str, Any], str | None]:
    """Each question asked in each configuration, inside the project's scope,
    the top ten scored under both rules; the passages of the configurations
    the judge reads are kept in `shown` for it, by configuration and question."""
    retriever = kit.service().retriever
    lane: dict[str, Any] = {}
    for config in [c for name in configs for c in DEFAULT_ABLATIONS if c.name == name]:
        by_kit: list[QuestionRetrievalRecord] = []
        by_passage: list[QuestionRetrievalRecord] = []
        stages: dict[str, Counter[str]] = {"graph": Counter(), "hyde": Counter()}
        ranked: dict[str, list[dict[str, Any]]] = {}
        calls: list[dict[str, Any]] = []
        stopped = None
        began = time.monotonic()
        with _counted_into(tally, calls):
            for a in asked:
                result = await retriever.retrieve(a.question.question, limit=TOP, scope=scope, **config.kwargs)
                items = result.items[:TOP]
                by_kit.append(_record(a.question.id, [r for r, i in enumerate(items, 1) if is_relevant(i, a.question)],
                                      len(items), result.degraded_stages))
                by_passage.append(_record(a.question.id, [r for r, i in enumerate(items, 1) if i.id == a.chunk_id],
                                          len(items), result.degraded_stages))
                for trace in result.traces:
                    if trace.stage in stages:
                        stages[trace.stage][trace.status] += 1
                ranked[a.question.id] = [{"chunkId": i.id, "documentId": i.document_id, "layers": list(i.layers)}
                                         for i in items]
                if config.name in JUDGED:
                    shown[(config.name, a.question.id)] = [i.content for i in items]
                stopped = stop()
                if stopped:
                    break
        lane[config.name] = {
            "description": config.description, "kit": _scored(RetrievalEvalResult(config, by_kit)),
            "passage": _scored(RetrievalEvalResult(config, by_passage)),
            "stages": {k: dict(sorted(v.items())) for k, v in stages.items()}, "ranked": ranked, "spent": calls,
            "seconds": round(time.monotonic() - began, 1),
        }
        if stopped:
            return lane, stopped
    return lane, None


# ── the judge's relevance ──────────────────────────────────────────────

RELEVANCE = """You grade the passages a search returned for a question about {domain}.

For each numbered passage, give 2 when the passage states what the question asks, 1 when it bears on the question \
without stating it, and 0 when it does not bear on the question. Grade each passage from its own words alone.

Question: {question}

Passages:

{passages}

Respond with JSON only, one grade for every passage, in this form:
{{"grades": [{{"passage": 1, "relevance": 0}}], "rationale": "one sentence"}}"""


def relevance_prompt(domain: str, question: str, passages: list[str]) -> str:
    shown = "\n\n".join(f"[{i}] {text[:PASSAGE_CHARS]}" for i, text in enumerate(passages, start=1))
    return RELEVANCE.format(domain=domain, question=question, passages=shown)


def grades(payload: Any, n: int) -> list[int]:
    """The judge's grade of each of `n` passages, in order, each 0 to 2;
    ValueError in words for an answer that does not grade each one."""
    listed = payload.get("grades") if isinstance(payload, dict) else None
    if not isinstance(listed, list):
        raise ValueError("the judge's answer holds no list of grades")
    by: dict[int, int] = {}
    for g in listed:
        if isinstance(g, dict) and isinstance(g.get("passage"), int) and isinstance(g.get("relevance"), int | float):
            by[g["passage"]] = max(0, min(2, round(g["relevance"])))
    if set(by) != set(range(1, n + 1)):
        raise ValueError(f"the judge graded passages {sorted(by)} of {n}")
    return [by[i] for i in range(1, n + 1)]


def judged(graded: list[int]) -> dict[str, float]:
    """A question's measures under the judge's grades: the share of its
    passages graded 1 or 2, whether a passage graded 2 stands in the top five
    and the top ten, and nDCG at ten with graded gains over what was
    retrieved (relative, as the kit's nDCG is)."""
    dcg = sum((2 ** g - 1) / math.log2(r + 1) for r, g in enumerate(graded[:TOP], start=1))
    ideal = sum((2 ** g - 1) / math.log2(r + 1) for r, g in enumerate(sorted(graded, reverse=True)[:TOP], start=1))
    return {"precision_at_10": sum(g >= 1 for g in graded[:TOP]) / len(graded[:TOP]) if graded else 0.0,
            "hit_at_5": float(any(g == 2 for g in graded[:5])), "hit_at_10": float(any(g == 2 for g in graded[:TOP])),
            "ndcg_at_10": dcg / ideal if ideal else 0.0}


def _judge_summary(records: list[dict[str, Any]], began: float) -> dict[str, Any]:
    graded = [judged(r["grades"]) for r in records if r.get("grades")]
    out: dict[str, Any] = {"records": records, "asked": len(records), "graded": len(graded),
                           "failed": sum("error" in r for r in records), "seconds": round(time.monotonic() - began, 1)}
    for metric in ("precision_at_10", "hit_at_5", "hit_at_10", "ndcg_at_10"):
        out[metric] = _ci([g[metric] for g in graded])
    return out


async def _judge_retrieval(asked: list[Asked], shown: dict[tuple[str, str], list[str]], *, tally: Tally,
                           stop: Stop) -> tuple[dict[str, Any], str | None]:
    """The judge route's grade of the top ten of each judged configuration,
    one call a question and configuration, each under its own tally."""
    judge = kit.model("judge")
    domain = kit.service().domain.name
    lane: dict[str, Any] = {}
    for name in JUDGED:
        if not any(key[0] == name for key in shown):
            continue
        records: list[dict[str, Any]] = []
        began = time.monotonic()
        for a in asked:
            passages = shown.get((name, a.question.id)) or []
            record: dict[str, Any] = {"questionId": a.question.id, "passages": len(passages), "spent": []}
            records.append(record)
            if not passages:
                record["error"] = "no passage was retrieved"
                continue
            with _counted_into(tally, record["spent"]):
                try:
                    payload = await judge.generate_json(relevance_prompt(domain, a.question.question, passages),
                                                        max_tokens=1024)
                    record["grades"] = grades(payload, len(passages))
                    record["rationale"] = str(payload.get("rationale", "")).strip()
                except Exception as e:  # a refusal, an outage or an answer that grades nothing: counted
                    record["error"] = f"{type(e).__name__}: {e}"
            stopped = stop()
            if stopped:
                lane[name] = _judge_summary(records, began)
                return lane, stopped
        lane[name] = _judge_summary(records, began)
    return lane, None


# ── the answer lane ────────────────────────────────────────────────────


def _answer_summary(records: list[dict[str, Any]], began: float) -> dict[str, Any]:
    graded = [r["grounding"] for r in records if r.get("grounding")]
    answered = [r for r in records if "answer" in r]
    out: dict[str, Any] = {"records": records, "asked": len(records), "answered": len(answered), "graded": len(graded),
                           "failed": sum("error" in r for r in records),
                           "citedPassage": _ci([float(r["citedPassage"]) for r in answered]),
                           "seconds": round(time.monotonic() - began, 1)}
    for score in ("groundedness", "citation_accuracy", "completeness"):
        out[score] = _ci([float(g[score]) for g in graded])
    return out


async def _answers(asked: list[Asked], scope: Any, *, tally: Tally, stop: Stop) -> tuple[dict[str, Any], str | None]:
    """The kit's answer to each question through each judged configuration's
    profile, on the explain route, then the judge route's blind grounding pass
    over the answer and the sources the answer was written from, each under
    its own tally."""
    service = kit.service()
    judge = kit.model("judge")
    lane: dict[str, Any] = {}
    for name, profile in JUDGED.items():
        records: list[dict[str, Any]] = []
        began = time.monotonic()
        for a in asked:
            record: dict[str, Any] = {"questionId": a.question.id, "profile": profile, "answerSpent": [],
                                      "judgeSpent": []}
            records.append(record)
            result = None
            with _counted_into(tally, record["answerSpent"]):
                try:
                    result = await service.engine.answer(a.question.question, profile=profile, limit=8, scope=scope)
                except Exception as e:  # counted, never fatal
                    record["error"] = f"answer failed: {type(e).__name__}: {e}"
            if result is not None:
                used = result.prompt_retrieval or result.retrieval
                sources = format_sources(used) if used.items else "(no sources were retrieved)"
                record.update(answer=result.text, sources=sources, sourceCount=len(result.sources),
                              cited=len(result.cited_sources),
                              citedPassage=any(s.chunk_id == a.chunk_id for s in result.cited_sources))
                with _counted_into(tally, record["judgeSpent"]):
                    try:
                        grade = await grade_grounding(judge, service.domain, question=a.question.question,
                                                      answer_text=result.text, sources_block=sources)
                        record["grounding"] = dataclasses.asdict(grade)
                    except Exception as e:  # counted, never fatal
                        record["error"] = f"grounding judge failed: {type(e).__name__}: {e}"
            stopped = stop()
            if stopped:
                lane[name] = _answer_summary(records, began)
                return lane, stopped
        lane[name] = _answer_summary(records, began)
    return lane, None


# ── a project's run ────────────────────────────────────────────────────


class Refused(ValueError):
    """A run asked for something it cannot do, in words."""


def _truth(built: Truth) -> dict[str, Any]:
    return {
        "questions": [{"id": a.question.id, "question": a.question.question, "evidence": a.question.evidence_phrases,
                       "documentId": a.document_id, "passageId": a.passage_id, "chunkId": a.chunk_id,
                       "field": a.field, "candidates": list(a.candidates)} for a in built.asked],
        "read": built.read, "kept": built.kept, "dropped": dict(sorted(built.dropped.items())),
        "groups": built.groups, "documents": built.documents, "covered": built.covered,
    }


async def lanes(project_id: str, *, judge: bool = False, limit: int | None = None,
                configs: tuple[str, ...] = PROJECT_CONFIGS, tally: Tally, stop: Stop) -> dict[str, Any]:
    """A project's run, whole: its ground truth (`truth`), the retrieval lane
    over `configs`, and with `judge` the judge's relevance and the answer
    lane. Refused in words for a configuration that does not stay inside a
    project and for a project whose candidates build no question. Runs on the
    database loop."""
    outside = [c for c in configs if c not in PROJECT_CONFIGS]
    if outside:
        raise Refused(f"{', '.join(outside)}: a project's run takes {', '.join(PROJECT_CONFIGS)} alone, the kit's "
                      "configurations that stay inside the project's documents (`no_retracted` carries a scope of "
                      "its own, and `with_citations` follows citations outside the project)")
    built = await truth(project_id, limit=limit)
    if not built.asked:
        raise Refused(NO_QUESTIONS.format(project=project_id))
    with projects.using(project_id):
        scope = await kit._narrowed(None)
        run: dict[str, Any] = {"kind": "literature-lanes", "project": project_id, "at": datetime.now(UTC).isoformat(),
                               "configs": list(configs), "judge": judge,
                               "fingerprint": await kit.service().fingerprint(), "truth": _truth(built)}
        shown: dict[tuple[str, str], list[str]] = {}
        run["retrieval"], stopped = await _retrieval(built.asked, configs, scope, shown, tally=tally, stop=stop)
        if judge and not stopped:
            run["judgeRetrieval"], stopped = await _judge_retrieval(built.asked, shown, tally=tally, stop=stop)
        if judge and not stopped:
            run["answers"], stopped = await _answers(built.asked, scope, tally=tally, stop=stop)
        run["stopped"] = stopped
    return run


# ── the public numbers, and their Markdown ─────────────────────────────


def _all(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return [s for r in records for s in r.get(key, [])]


def public(run: dict[str, Any], *, routes: dict[str, Any], commit: str | None = None) -> dict[str, Any]:
    """The numbers of a run the committed report may hold: scores with their
    intervals, counts, question ids, model ids, USD and seconds. No question,
    passage, quote, answer, rationale or entity name."""
    fp, truth_ = run["fingerprint"], run["truth"]
    shape = fp.get("graph") or {}
    part: dict[str, Any] = {
        "project": run["project"], "at": run["at"], "commit": commit, "configs": run["configs"], "judged": run["judge"],
        "stopped": run.get("stopped"), "routes": routes,
        "corpus": {k: fp.get(k) for k in ("documents", "chunks", "tokens", "entities", "relationships", "communities",
                                          "embedding_versions", "latest_ingested_at")}
        | {"chunksRead": shape.get("chunks_read", 0), "entityTypes": shape.get("entity_types", {}),
           "relationTypes": shape.get("relation_types", {})},
        "truth": {"questions": len(truth_["questions"]), "read": truth_["read"], "kept": truth_["kept"],
                  "dropped": truth_["dropped"], "groups": truth_["groups"], "documents": truth_["documents"],
                  "covered": truth_["covered"],
                  "fields": dict(sorted(Counter(q["field"] for q in truth_["questions"]).items()))},
        "retrieval": {}, "judgeRetrieval": {}, "answers": {}, "cost": {},
    }
    for name, lane in (run.get("retrieval") or {}).items():
        part["retrieval"][name] = {
            "kit": lane["kit"]["metrics"], "passage": lane["passage"]["metrics"], "stages": lane["stages"],
            "spent": counted(lane["spent"]), "seconds": lane["seconds"],
            "missed": [r["question_id"] for r in lane["passage"]["records"] if not r["hit_at_10"]],
        }
    for name, lane in (run.get("judgeRetrieval") or {}).items():
        part["judgeRetrieval"][name] = {k: lane[k] for k in ("asked", "graded", "failed", "precision_at_10", "hit_at_5",
                                                             "hit_at_10", "ndcg_at_10", "seconds")} | {
            "spent": counted(_all(lane["records"], "spent"))}
    for name, lane in (run.get("answers") or {}).items():
        part["answers"][name] = {k: lane[k] for k in ("asked", "answered", "graded", "failed", "citedPassage",
                                                      "groundedness", "citation_accuracy", "completeness", "seconds")} | {
            "answerSpent": counted(_all(lane["records"], "answerSpent")),
            "judgeSpent": counted(_all(lane["records"], "judgeSpent"))}
    part["cost"] = {
        "retrieval": round(sum(v["spent"]["usd"] for v in part["retrieval"].values()), 6),
        "judgeRetrieval": round(sum(v["spent"]["usd"] for v in part["judgeRetrieval"].values()), 6),
        "answers": round(sum(v["answerSpent"]["usd"] + v["judgeSpent"]["usd"] for v in part["answers"].values()), 6),
    }
    part["cost"]["total"] = round(sum(part["cost"].values()), 6)
    return part


def _cell(ci: dict[str, float] | None) -> str:
    if not ci:
        return "–"
    return f"{ci['mean']:.2f} [{ci['lo']:.2f}, {ci['hi']:.2f}]"


def _named(counts: dict[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in counts.items()) or "none"


def render(part: dict[str, Any]) -> str:
    """A project's part of the report's Markdown, from its public numbers."""
    c, tr = part["corpus"], part["truth"]
    lines = [
        f"## The project `{part['project']}`", "",
        f"Run {part['at'][:19].replace('T', ' ')} UTC" + (f" at `{part['commit']}`" if part.get("commit") else "")
        + f", configurations {', '.join(f'`{x}`' for x in part['configs'])}"
        + (", with the judge" if part["judged"] else ", with no judge") + ". Written by "
        f"`pnpm lit:report --project {part['project']} --render` from the run's public numbers; the run whole (its "
        "questions, answers and rationales) stays in the service's data folder, outside git.", "",
    ]
    if part.get("stopped"):
        lines += [f"The run stopped before its end: {part['stopped']}", ""]
    lines += [
        "### The corpus", "",
        f"{c['documents']} documents, {c['chunks']} passages and {c['tokens']} kit tokens (the kit's estimate, four "
        f"characters a token where tiktoken is absent), embedded as {', '.join(c['embedding_versions']) or 'none'}. "
        f"The concept graph covers {c['chunksRead']} of the {c['chunks']} passages: {c['entities']} entities the "
        f"project's passages name and {c['relationships']} relationships they hold, {c['communities']} communities. "
        f"Entities by type: {_named(c['entityTypes'])}. Relationships by type: {_named(c['relationTypes'])}.", "",
        "### The ground truth", "",
        f"{tr['questions']} questions, built by code from {tr['kept']} of the {tr['read']} candidates the project "
        f"keeps, one a group of candidates by document, passage and field ({tr['groups']} groups), over "
        f"{tr['covered']} of its {tr['documents']} documents. A candidate counts when its quote stands in the passage "
        f"it cites; left out: {_named(tr['dropped'])}. Questions by field: {_named(tr['fields'])}. Each question is "
        f"tagged `{TAG}`: its words and its evidence come from a model's extraction that no person has reviewed, so "
        "every number below is provisional.", "",
        "### Retrieval", "",
        "The kit's rule counts a passage of the question's document, or one holding a quote of its candidates; the "
        "passage rule counts the candidates' own passage alone. Each cell is the mean with its 95% bootstrap "
        "interval.", "",
        "| Configuration | n | hit@5 kit | hit@10 kit | MRR kit | nDCG@10 kit | hit@5 passage | hit@10 passage | "
        "MRR passage | nDCG@10 passage |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in part["retrieval"].items():
        k, p = r["kit"], r["passage"]
        lines.append(f"| `{name}` | {k.get('n', 0)} | " + " | ".join(
            _cell(m.get(x)) for m in (k, p) for x in ("hit_at_5", "hit_at_10", "mrr", "ndcg_at_10")) + " |")
    lines += ["", "| Configuration | graph stage | HyDE stage | calls | USD | seconds |", "|---|---|---|---|---|---|"]
    for name, r in part["retrieval"].items():
        s = r["spent"]
        lines.append(f"| `{name}` | {_named(r['stages'].get('graph', {}))} | {_named(r['stages'].get('hyde', {}))} | "
                     f"{s['calls']} | {s['usd']:.4f} | {r['seconds']} |")
    lines += ["", "A layer earns its place when removing it moves a measure outside the overlap of the intervals: "
              "`full_deep` beside `no_graph` and `no_hyde`. Under a project's scope the graph seeds on exact names "
              "alone (ADR-002, Implementation F).", ""]
    for name, r in part["retrieval"].items():
        if r["missed"]:
            lines.append(f"- `{name}` missed at ten under the passage rule: {', '.join(r['missed'])}.")
    if any(r["missed"] for r in part["retrieval"].values()):
        lines.append("")
    if part["judgeRetrieval"]:
        lines += ["### The judge's relevance", "",
                  "The judge route grades each of the top ten passages 0 to 2 for its question.", "",
                  "| Configuration | graded | failed | precision@10 | hit@5 | hit@10 | nDCG@10 | judge models | USD |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for name, j in part["judgeRetrieval"].items():
            lines.append(f"| `{name}` | {j['graded']} of {j['asked']} | {j['failed']} | " + " | ".join(
                _cell(j.get(x)) for x in ("precision_at_10", "hit_at_5", "hit_at_10", "ndcg_at_10"))
                + f" | {_named(j['spent']['models'])} | {j['spent']['usd']:.4f} |")
        lines.append("")
    if part["answers"]:
        lines += ["### Answers", "",
                  "The kit's answer on the explain route, graded blind for grounding by the judge route over the "
                  "sources the answer was written from (0 to 2).", "",
                  "| Configuration | answered | graded | failed | cites the passage | groundedness | citation accuracy "
                  "| completeness | answer models | judge models | USD |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, a in part["answers"].items():
            usd = a["answerSpent"]["usd"] + a["judgeSpent"]["usd"]
            lines.append(f"| `{name}` | {a['answered']} of {a['asked']} | {a['graded']} | {a['failed']} | "
                         + " | ".join(_cell(a.get(x)) for x in ("citedPassage", "groundedness", "citation_accuracy",
                                                                 "completeness"))
                         + f" | {_named(a['answerSpent']['models'])} | {_named(a['judgeSpent']['models'])} | "
                           f"{usd:.4f} |")
        lines.append("")
    lines += ["### Routes", "", "| Family | effort | models |", "|---|---|---|"]
    for family, route in part["routes"].items():
        lines.append(f"| `{family}` | {route['effort']} | {', '.join(route['models'])} |")
    cost = part["cost"]
    lines += ["", "### Cost", "",
              f"Retrieval {cost['retrieval']:.4f} USD, the judge's relevance {cost['judgeRetrieval']:.4f} USD, "
              f"answers and their grading {cost['answers']:.4f} USD: {cost['total']:.4f} USD in all.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
