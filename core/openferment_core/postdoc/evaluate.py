"""Postdoc's evaluation set (execution prompt §10 stage 6.4; ADR-006, ADR-008).

A project keeps its questions as rows of `eval_questions`, each with what a good
answer does: the tools it reaches for (any one tool of each group), what its
claims cite, and whether it states a labelled estimate. A run asks each question
through Postdoc's loop, kept as a turn of a conversation like any question (a
question that follows another is asked in that one's conversation, so it reads
its history from the service), and keeps a row of `eval_runs` scored by code:

    tools        the share of the tool groups the trace reached
    citations    the share of the claims kept that cite what the question expects
    estimates    1 when the answer states a labelled estimate exactly where the
                 question asks for one, every claim stating one `assumed`
    bareNumbers  1 when no claim was dropped for a number in its text; the count
                 dropped is kept beside it

OFFLINE the loop answers with a stand-in (`StandIn`): each default question's own
script of tool calls and a plan written from what the tools returned, the
stand-in named `STANDIN` wherever a model is named. It exercises the tools, the
validator, the conversation store and the scores without a key; its second
question drops a claim with a bare number on purpose, so the count is seen to
work. LIVE (`--live`) the routing table's `plan` models answer every question.
A run asks through the answer path it is handed (`api._answer`, which keeps
each question as a turn); `openferment_core.evaluation` is the command.

TWO SUITES. `default` holds the proof's two questions over the sugarcane plant;
`ethanol` holds the owner's twelve real questions over a project of ethanol
sources (alpha 2.1 stage B and C; docs/reports/live-questions-2026-11.md) and
the two alpha 2.2 adds for the base's seams (its prompt's §5): the engines
registered, what each takes and gives and which of the project's runs came from
each (13), and a deposition's reading set as a scenario's value and run (14),
each question with what a good answer does in words (`expects`). A run asks one
suite, under a `tag` that names the route table it ran on, so runs on different
models sit side by side (`summary`).

THE JUDGE (alpha 2.1 stage C). Beside the code's scores, a model on the `judge`
route reads each answer as Postdoc gave it: the question, what a good answer
does, every claim with what it cites (the evidence's values, each record's
quote, each passage's words), the gaps, and the tools called. It scores four
things from 0 to 1 and names the faults it finds:

    answers      how far the answer does what the question asks
    grounded     the share of claims that what they cite bears out
    labelled     every value's origin said, every estimate labelled
    coverage     how much of what a good answer covers this one covers

A judgement is the judge model's, kept with that model's id beside the code's
scores and never in their place; a run may be judged again on another judge
route (`judge`), and each judgement is kept.
"""
from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Literal

from pydantic import BaseModel, Field

from .. import db, llm, projects
from ..db import models as t
from ..db import rows
from ..models import AnswerPlan, AskRequest, Usage

BY = "openFerment evaluation"
# The stand-in's name, wherever a model is named: an estimate it types, an audit line.
STANDIN = "openferment-standin"
# The plant the default questions ask about, and the parameter the second one changes.
PLANT = "sugarcane"
CANE_PRICE = "stream.sugarcane.price"
CiteKind = Literal["evidence", "record", "passage", "row"]


class EvalQuestion(BaseModel):
    id: str
    question: str
    # Groups of tools: the trace reaching any one tool of a group counts for it.
    tools: list[list[str]] = Field(default_factory=list)
    # What a claim of a good answer cites.
    cites: list[CiteKind] = Field(default_factory=list)
    # Whether a good answer states a labelled estimate: True where it must,
    # False where it must not, None where it may (labelled, if it does).
    estimate: bool | None = False
    # The question this one follows, asked first in the same conversation.
    follows: str | None = None
    # What a good answer does, in words: what the judge holds it to.
    expects: str = ""
    # The suite it belongs to (DEFAULT or ETHANOL).
    suite: str = "default"
    by: str = BY
    at: str = ""


class EvalScores(BaseModel):
    tools: float
    citations: float
    estimates: float
    bareNumbers: float


class Judgement(BaseModel):
    """What the judge model made of one answer: its four scores, each 0 to
    1, the faults it named and its verdict, labelled with the model that
    judged and what judging cost. A judge that declined, or could not be
    reached, leaves no score: `declined` says why, in words, and a mean
    leaves it out."""

    model: str
    answers: float | None = None
    grounded: float | None = None
    labelled: float | None = None
    coverage: float | None = None
    errors: list[str] = Field(default_factory=list)
    note: str = ""
    declined: str | None = None
    costUsd: float = 0.0
    at: str = ""


class EvalRun(BaseModel):
    id: str
    questionId: str
    question: str
    mode: Literal["offline", "live"]
    models: list[str]
    conversationId: str | None = None
    turnId: str | None = None
    scores: EvalScores
    droppedForNumbers: int
    claims: int
    rejected: int
    declined: str | None = None
    toolsCalled: list[str]
    costUsd: float
    at: str
    by: str
    suite: str = "default"
    # The route table the run was asked on, as the person running it named it.
    tag: str = ""
    # From the question asked to the answer kept.
    seconds: float | None = None
    judged: list[Judgement] = Field(default_factory=list)


DEFAULT_QUESTIONS = (
    EvalQuestion(id="eq-price", question=(
        "What selling price does the library's sugarcane plant solve for its ethanol at the package's own values?"),
        tools=[["engine_run", "engine_report"]], cites=["evidence"]),
    EvalQuestion(id="eq-dearer", question=(
        "And on a dearer cane? Propose a scenario with your own estimate of the cane's price, run it, and say what "
        "it does to the selling price."),
        tools=[["engine_parameters"], ["study_scenario"], ["engine_run"]], cites=["evidence"], estimate=True,
        follows="eq-price"),
)

DEFAULT = "default"
ETHANOL = "ethanol"


def _eth(n: int, question: str, expects: str, tools: list[list[str]], cites: list[CiteKind],
         estimate: bool | None = None, follows: int | None = None) -> EvalQuestion:
    return EvalQuestion(id=f"eq-eth-{n:02d}", question=question, expects=expects, tools=tools, cites=cites,
                        estimate=estimate, follows=f"eq-eth-{follows:02d}" if follows else None, suite=ETHANOL)


# The engines question 13 expects named: the three the core registers
# (core/pyproject.toml's entry points in the group `openferment.engines`).
# Stage D adds the stranger's engine once it is installed.
ENGINES_EXPECTED = ("biosteam", "kinetics", "train")


def _named(names: tuple[str, ...]) -> str:
    """Names in words: `a`, `a and b`, `a, b and c`."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


# The owner's twelve (alpha 2.1 execution prompt §5), asked of a project that
# holds the ethanol sources (docs/corpus/ethanol-sources.txt) and their
# extraction, and the two the alpha 2.2 prompt's §5 adds for the base's seams:
# the engine reads (13) and a measurement origin (14), in the prompt's words.
# Words only: what a good answer does, never what it finds.
ETHANOL_QUESTIONS = (
    _eth(1, "Which of the project's documents report an ethanol titre, and under what conditions does each report it?",
         "Names each document that reports an ethanol titre and the conditions it reports it under, each claim citing "
         "the passage or record it rests on.",
         [["search_passages", "search_records", "literature_document"]], ["passage", "record"]),
    _eth(2, "What strains of Saccharomyces cerevisiae appear in the project's documents, and which documents describe "
            "each?",
         "Names the strains of S. cerevisiae the documents describe and which documents describe each, each claim "
         "citing a passage or a record.",
         [["search_passages", "literature_document", "search_records"]], ["passage", "record"]),
    _eth(3, "What does the reference cellulosic ethanol plant in the library assume about its feedstock, and where do "
            "those numbers come from?",
         "States the reference cellulosic plant's feedstock assumptions (its composition, moisture, flow and price) as "
         "typed values read back from a run, and names where each comes from: the package's own value, or a source "
         "the documents give.",
         [["engine_run", "engine_report"]], ["evidence"]),
    _eth(4, "What drives the selling price in that plant: show the cost lines and say which inputs the package sets "
            "and which a person could change.",
         "Shows the cost lines behind the selling price, each cited to the run's artifact, and says which inputs the "
         "package sets and which a person could change in a scenario.",
         [["engine_report"]], ["evidence"]),
    _eth(5, "What if the organism fermented glucose alone? Propose a scenario, run it, and say what changed and what "
            "the change rests on.",
         "Proposes a glucose-only scenario, runs it, compares it with the package's own run, and says what changed and "
         "what the change rests on, each estimate labelled as the model's.",
         [["study_scenario"], ["engine_run"], ["study_compare"]], ["evidence"], estimate=True),
    _eth(6, "Compare dilute-acid and hot-water pretreatment in the composed flowsheet, with the package's own "
            "defaults.",
         "Runs the composed flowsheet with dilute-acid and with hot-water pretreatment on the package's defaults, "
         "compares the two, and flags what limits the comparison.",
         [["engine_run"], ["study_compare"]], ["evidence"]),
    _eth(7, "What is uncertain in the comparison, and what evidence would settle it?",
         "Says what is uncertain in the comparison and what evidence would settle it, with no number of its own.",
         [["study_read", "study_compare", "engine_report", "engine_parameters"]], ["evidence", "passage"],
         estimate=False, follows=6),
    _eth(8, "Draft a runbook for the scenario in question 5 with its predictions read from the run.",
         "Drafts a runbook through the runbook tool for the glucose-only scenario's run, its predictions read from "
         "that run.",
         [["draft_runbook"]], ["evidence"], follows=5),
    _eth(9, "Which records in this project are verified, and which candidates wait for review?",
         "Says which records are verified and which candidates wait for review, from the module reads, naming "
         "documents by their titles.",
         [["biorepo_read", "search_records"]], ["row", "record"], estimate=False),
    _eth(10, "Which documents in the project were refused or partly ingested, and why?",
         "Says which documents were refused or partly ingested and why, from Intake's state, in words.",
         [["intake_read", "literature_sources"]], ["row"], estimate=False),
    _eth(11, "Import this SFF file and tell me what plant it describes: the toolkit reference file SF_BST_15.",
         "Imports the toolkit's reference file SF_BST_15 and says what plant it describes from its graph, each claim "
         "cited to the record's evidence.",
         [["flowsheet_import", "flowsheet_read"]], ["evidence"], estimate=False),
    _eth(12, "What is the theoretical ceiling for ethanol on glucose according to the genome-scale models on the shelf, "
             "and how do the project's records compare?",
         "Gives the ethanol ceiling on glucose from the genome-scale models on the shelf as geneOS artifacts and "
         "compares the project's recorded yields with it, or says in words that a model file is absent.",
         [["yield_ceiling", "geneos_read"]], ["evidence", "record"]),
    _eth(13, "Which engines are registered here, what does each take and give, and which of this project's runs came "
             "from each?",
         f"Names each engine registered here ({_named(ENGINES_EXPECTED)}) from the engine reads: what each runs, what "
         "each takes (its parameters, each with its unit and the origin of its default, or that a run sets it) and "
         "what each gives (the outputs a run of it keeps), and which of the project's runs came from each, set out "
         "as one table with a row for each engine, its cells the ids, units and origins the reads returned, and each "
         "run named by its id and cited by the evidence id or the module row a read returned.",
         [["engine_plants"], ["engine_parameters"],
          ["engine_report", "study_read", "proforma_read", "fermos_read", "pureos_read"]],
         ["evidence", "row"], estimate=False),
    _eth(14, "Take the ethanol yield measured in this project's most recent deposition, set it as the glucose-only "
             "scenario's yield, run it, and say what changed and what the value rests on.",
         "Reads the ethanol yield the project's most recent deposition holds from the bench's readings (runbooks_read, "
         "kind reading), sets it as the yield of the glucose-only scenario this conversation proposed, the value and "
         "unit as the reading gives them with the origin measurement naming the reading's id, runs the scenario, sets "
         "the run beside the glucose-only scenario's own run in a comparison, and says what changed, citing the "
         "comparison, and what the value rests on: the deposition, the person who deposited it and when it was "
         "taken, and the run's provenance, measured, or assumed with the reason (the estimate or the assumption "
         "among the run's values). Where the project's depositions hold no ethanol yield, says so in words and runs "
         "nothing.",
         [["runbooks_read"], ["study_scenario"], ["engine_run"], ["study_compare"]], ["evidence", "row"],
         follows=5),
)
SUITES: dict[str, tuple[EvalQuestion, ...]] = {DEFAULT: DEFAULT_QUESTIONS, ETHANOL: ETHANOL_QUESTIONS}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── the store ──────────────────────────────────────────────────────────


async def _questions(project_id: str) -> list[EvalQuestion]:
    async with db.session() as s:
        return [EvalQuestion.model_validate(b) for b in await rows.bodies(s, t.eval_questions, project_id)]


def questions(suite: str | None = None) -> list[EvalQuestion]:
    """The project's questions, oldest first; those of one suite when named."""
    return [q for q in db.run(_questions(projects.current())) if suite is None or q.suite == suite]


async def _seed(project_id: str, by: str, suite: str) -> list[str]:
    made = []
    async with db.session() as s:
        for q in SUITES[suite]:
            if await rows.body(s, t.eval_questions, project_id, q.id) is None:
                await rows.put(s, t.eval_questions, project_id, q.id, q.model_copy(update={"by": by, "at": _now()})
                               .model_dump(mode="json"), by=by)
                made.append(q.id)
    return made


def seed(by: str = BY, suite: str = DEFAULT) -> list[str]:
    """A suite's questions kept in the project, those it lacks; their ids."""
    if suite not in SUITES:
        raise ValueError(f"there is no suite {suite!r}: the suites are {', '.join(SUITES)}")
    return db.run(_seed(projects.current(), by, suite))


async def _keep(project_id: str, run: EvalRun) -> None:
    async with db.session() as s:
        await rows.put(s, t.eval_runs, project_id, run.id, run.model_dump(mode="json"), by=run.by,
                       question_id=run.questionId)


async def _runs(project_id: str) -> list[EvalRun]:
    async with db.session() as s:
        return [EvalRun.model_validate(b) for b in await rows.bodies(s, t.eval_runs, project_id)]


def runs() -> list[EvalRun]:
    """The project's scored runs, oldest first."""
    return db.run(_runs(projects.current()))


# ── the scores ─────────────────────────────────────────────────────────


def _cites(claim: Any) -> set[str]:
    kinds = set()
    if claim.evidenceIds:
        kinds.add("evidence")
    if claim.recordIds:
        kinds.add("record")
    if claim.passages:
        kinds.add("passage")
    if claim.moduleRefs:
        kinds.add("row")
    return kinds


def dropped_for_numbers(plan: AnswerPlan) -> int:
    return sum("contains a number" in reason for reason in plan.rejectionReasons)


def score(q: EvalQuestion, plan: AnswerPlan) -> EvalScores:
    """A plan held to what its question expects, by code."""
    called = {s.tool for s in plan.trace if s.kind == "tool" and s.ok}
    tools = sum(any(name in called for name in group) for group in q.tools) / len(q.tools) if q.tools else 1.0
    kept = plan.claims
    want = set(q.cites)
    cited = [bool(_cites(c) & want) if want else bool(_cites(c)) for c in kept]
    estimated = [c for c in kept if any(v.quantity.origin is not None and v.quantity.origin.kind == "model-estimate"
                                        for v in c.values)]
    labelled = all(c.provenance == "assumed" for c in estimated)
    return EvalScores(
        tools=round(tools, 3),
        citations=round(sum(cited) / len(cited), 3) if cited else 0.0,
        estimates=1.0 if labelled and (q.estimate is None or bool(estimated) == q.estimate) else 0.0,
        bareNumbers=0.0 if dropped_for_numbers(plan) else 1.0,
    )


# ── the offline stand-in ───────────────────────────────────────────────


class StandIn:
    """A stand-in for the model on one question: each call takes the next
    entry of its script, a list of tool calls (name, input) or the final
    plan, either of which may be a function of the conversation so far.
    Every conversation it was handed is kept."""

    def __init__(self, *turns: Any):
        self.turns = list(turns)
        self.seen: list[list[dict[str, Any]]] = []

    def __call__(self, **kw: Any) -> llm.Turn:
        messages = json.loads(json.dumps(kw["messages"], default=str))
        self.seen.append(messages)
        entry = self.turns.pop(0) if self.turns else {"claims": [], "gaps": [], "declined": None}
        if callable(entry):
            entry = entry(messages)
        usage = Usage(models=[kw["model"]])
        if isinstance(entry, dict):
            return llm.Turn(content=[{"type": "text", "text": json.dumps(entry)}], toolCalls=[], data=entry,
                            stopReason="end_turn", usage=usage, model=kw["model"])
        calls = [llm.ToolCall(id=f"tu-{len(self.seen)}-{i}", name=name, input=inp) for i, (name, inp) in enumerate(entry)]
        return llm.Turn(content=[{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls],
                        toolCalls=calls, data=None, stopReason="tool_use", usage=usage, model=kw["model"])


def returned(messages: list[dict[str, Any]], key: str) -> Any:
    """The newest tool result's `key`, as the stand-in read it."""
    for m in reversed(messages):
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            for block in reversed(m["content"]):
                if block.get("type") == "tool_result" and not block.get("is_error"):
                    found = json.loads(block["content"]).get(key)
                    if found is not None:
                        return found
    raise LookupError(f"no tool returned {key!r} to the stand-in")


def _claim(cid: str, text: str, *, evidence: list[str] = (), values: list[dict] = (), support: str = "direct") -> dict:
    return {"id": cid, "text": text, "recordIds": [], "paperIds": [], "support": support, "passages": [],
            "evidenceIds": list(evidence), "moduleRefs": [], "values": list(values)}


def _read(label: str, evidence_id: str) -> dict:
    return {"label": label, "evidenceId": evidence_id, "recordId": "", "estimate": None}


def _price_script() -> list[Any]:
    def answer(m: list[dict[str, Any]]) -> dict:
        price = f"{returned(m, 'artifactId')}:price.solvedPrice"
        return {"claims": [_claim("c1", "The library's sugarcane plant solves a selling price for its ethanol at the "
                                        "package's own values.", values=[_read("the selling price the run solves", price)])],
                "gaps": [], "declined": None}

    return [[("engine_run", {"plant": PLANT, "configuration": "", "scenario": "", "note": "the package's own values"})],
            answer]


def _dearer_script() -> list[Any]:
    def scenario(m: list[dict[str, Any]]) -> list:
        spec = next(p for p in returned(m, "parameters") if p["key"] == CANE_PRICE)
        value = round(1.5 * float(spec["default"]), 6)
        return [("study_scenario", {"title": "A dearer cane", "plant": PLANT, "configuration": "", "note": "",
                                    "values": [{"key": CANE_PRICE, "quantity": {
                                        "value": value, "unit": spec["unit"],
                                        "note": "half again the package's own price for the cane"}}]})]

    def answer(m: list[dict[str, Any]]) -> dict:
        price = f"{returned(m, 'artifactId')}:price.solvedPrice"
        (cane,) = returned(m, "valuesSet")
        estimate = {"label": "the cane's price the scenario sets", "evidenceId": "", "recordId": "",
                    "estimate": {"value": cane["value"], "unit": cane["unit"], "low": None, "high": None,
                                 "basis": "the package's own price for the cane, raised for a dearer harvest"}}
        return {"claims": [
            _claim("c1", "On the dearer cane the plant solves the ethanol's selling price again, resting on the "
                         "stand-in's estimate of the cane's price.", support="inferred",
                   values=[_read("the selling price the run solves", price), estimate]),
            _claim("c2", "The selling price passes 1 dollar a kilogram.", evidence=[price]),
        ], "gaps": [], "declined": None}

    return [[("engine_parameters", {"plant": PLANT, "configuration": "", "words": "price", "limit": 40})], scenario,
            lambda m: [("engine_run", {"plant": "", "configuration": "", "scenario": returned(m, "scenarioId"),
                                       "note": "the dearer cane"})],
            answer]


SCRIPTS: dict[str, Callable[[], list[Any]]] = {"eq-price": _price_script, "eq-dearer": _dearer_script}


@contextlib.contextmanager
def _standin_routes() -> Iterator[None]:
    """The `plan` route names the stand-in, so every estimate it types and
    every write it makes is marked as the stand-in's."""
    held = os.environ.get(llm.ROUTES_SETTING)
    table = json.loads(held) if held else {}
    os.environ[llm.ROUTES_SETTING] = json.dumps({**table, "plan": {"models": [STANDIN]}})
    try:
        yield
    finally:
        if held is None:
            os.environ.pop(llm.ROUTES_SETTING, None)
        else:
            os.environ[llm.ROUTES_SETTING] = held


# ── the judge ──────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You grade one answer of Postdoc, a research assistant in \
openFerment, a platform for bioprocess engineering work, against the question \
it was asked and what a good answer to it does.

Postdoc may only claim what its tools returned. Each claim cites what it rests \
on: evidence ids (values a computation produced, given here with their labels \
and values), record ids (values extracted from the project's documents, given \
here with the verbatim quote each stands in), passages (verbatim quotes of the \
project's documents, given with their surrounding text) or module rows. A \
claim's words hold no number; the numbers it states stand in its typed values, \
each with its origin: read from evidence or a record, or the model's own \
estimate, which a good answer labels as one, and a claim stating one is marked \
`assumed`.

Grade only from what is in front of you: the question, what a good answer \
does, the claims with what each cites, the gaps the answer names, what the \
validator dropped, and the tools it called. Use what you know only to spot a \
claim its citations do not bear out, or a value given a meaning its source \
does not have (a label that does not fit the number, a unit that does not fit \
the quantity); never to add facts or to reward an answer for what is not cited.

Score each from 0 to 1:
- answers: how far the answer does what the question asks.
- grounded: the share of its claims whose words and values what they cite \
bears out.
- labelled: every value's origin said and every estimate labelled as the \
model's, its claim marked assumed; 1 when the answer states no value it \
cannot source.
- coverage: how much of what a good answer covers this one covers, reading \
its gaps as honest limits.

Name each fault as an error: the claim's id and what is wrong with it. End \
with a verdict of one or two sentences."""

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers": {"type": "number", "description": "0 to 1: how far the answer does what the question asks."},
        "grounded": {"type": "number", "description": "0 to 1: the share of claims what they cite bears out."},
        "labelled": {"type": "number", "description": "0 to 1: every value's origin said, every estimate labelled."},
        "coverage": {"type": "number", "description": "0 to 1: how much of what a good answer covers this one covers."},
        "errors": {"type": "array", "items": {"type": "string"},
                   "description": "Each fault: the claim's id and what is wrong with it."},
        "note": {"type": "string", "description": "The verdict, in one or two sentences."},
    },
    "required": ["answers", "grounded", "labelled", "coverage", "errors", "note"],
    "additionalProperties": False,
}
# What a judgement may write, its thinking included.
JUDGE_TOKENS = 16000
# How much of a cited passage's surrounding text the judge reads.
PASSAGE_CHARS = 1500


def case(q: EvalQuestion, plan: AnswerPlan, record: Callable[[str], dict[str, Any] | None],
         paper: Callable[[str], dict[str, Any] | None] = lambda _: None) -> dict[str, Any]:
    """An answer as the judge reads it: the question, what a good answer
    does, and every claim with what it cites, each cited thing given as the
    answer had it."""
    evidence = {e.id: e for e in plan.evidence}
    passages = {p.id: p for p in plan.passages}
    titles: dict[str, str] = {}

    def title(paper_id: str) -> None:
        if paper_id and paper_id not in titles:
            found = paper(paper_id)
            titles[paper_id] = str((found or {}).get("title") or paper_id)

    claims = []
    for c in plan.claims:
        records = []
        for rid in c.recordIds:
            r = record(rid)
            if r is not None:
                title(str(r.get("paperId") or ""))
                records.append({"id": rid, "document": r.get("paperId"), "field": r.get("fieldLabel") or r.get("field"),
                                "value": r.get("value"), "unit": r.get("unit"), "quote": r.get("quote")})
        quoted = []
        for ref in c.passages:
            held = passages.get(ref.passageId)
            if held is not None:
                title(held.paperId)
            quoted.append({"id": ref.passageId, "document": held.paperId if held else None, "quote": ref.quote,
                           "context": held.text[:PASSAGE_CHARS] if held else None})
        claims.append({
            "id": c.id, "text": c.text, "support": c.support, "provenance": c.provenance,
            "values": [{"label": v.label, "value": v.quantity.value, "unit": v.quantity.unit,
                        "origin": v.quantity.origin.kind if v.quantity.origin else None, "source": v.source}
                       for v in c.values],
            "evidence": [{"id": i, "label": evidence[i].label, "value": evidence[i].value, "unit": evidence[i].unit}
                         for i in c.evidenceIds if i in evidence],
            "records": records, "passages": quoted, "rows": list(c.moduleRefs),
        })
    return {
        "question": q.question, "aGoodAnswer": q.expects or "(not stated)", "claims": claims,
        "documents": titles, "gaps": list(plan.gaps), "declined": plan.declined,
        "droppedByTheValidator": list(plan.rejectionReasons), "stopped": plan.stopped,
        "toolsCalled": [f"{s.tool}{'' if s.ok else ' (refused)'}" for s in plan.trace if s.kind == "tool" and s.tool],
    }


def _unit(x: Any) -> float:
    try:
        return round(min(1.0, max(0.0, float(x))), 3)
    except (TypeError, ValueError):
        return 0.0


def judge(q: EvalQuestion, plan: AnswerPlan, *, record: Callable[[str], dict[str, Any] | None],
          paper: Callable[[str], dict[str, Any] | None], call: Callable[..., llm.Result] | None = None) -> Judgement:
    """One answer judged by the first model on the `judge` route that will:
    its scores, its faults and its verdict, labelled with that model. The
    caller hands it the project's records and documents to read cited ids
    by (`evidence_pool`, which this package does not import). A route whose
    every model declines, or none answers, is a judgement with no score
    that says so."""
    try:
        got = (call or llm.call)(system=JUDGE_SYSTEM, user=json.dumps(case(q, plan, record, paper), ensure_ascii=False),
                                 schema=JUDGE_SCHEMA, max_tokens=JUDGE_TOKENS, family="judge", label=f"judge {q.id}: ")
    except llm.ModelRefused as e:
        return Judgement(model=", ".join(e.models) or "judge", declined=str(e), costUsd=e.usage.costUsd, at=_now())
    except llm.ModelUnavailable as e:
        return Judgement(model=", ".join(llm.chain("judge")), declined=str(e), costUsd=e.usage.costUsd, at=_now())
    data = got.data or {}
    if not data:
        why = "it ran out of room" if got.truncated else "it was not a judgement"
        return Judgement(model=got.model, declined=f"The judge's answer did not arrive whole ({why}).",
                         costUsd=got.usage.costUsd, at=_now())
    return Judgement(model=got.model, answers=_unit(data.get("answers")), grounded=_unit(data.get("grounded")),
                     labelled=_unit(data.get("labelled")), coverage=_unit(data.get("coverage")),
                     errors=[str(e)[:400] for e in data.get("errors") or []][:20], note=str(data.get("note") or "")[:800],
                     costUsd=got.usage.costUsd, at=_now())


# ── a run ──────────────────────────────────────────────────────────────


def run(answer: Callable[..., AnswerPlan], *, live: bool = False, by: str = BY, suite: str = DEFAULT,
        tag: str = "", judged: bool = False,
        judge_with: Callable[[EvalQuestion, AnswerPlan], Judgement] | None = None,
        ) -> tuple[list[EvalRun], dict[str, StandIn]]:
    """Every question of one suite of the project asked through `answer` (an
    AskRequest and a stand-in model, or None for the routing table's), scored
    and kept, in order, under `tag`; a question that follows another asked in
    its conversation. With `judged`, each answer is judged as it is kept (a
    live run only: offline there is no judge model). Offline, a question with
    no stand-in script is passed over. The runs, and offline the stand-ins
    each question was asked of."""
    if judged and not live and judge_with is None:
        raise ValueError("an answer is judged by a model on the judge route, so an offline run is not judged")
    asked: dict[str, tuple[str, str]] = {}
    out: list[EvalRun] = []
    standins: dict[str, StandIn] = {}
    with contextlib.nullcontext() if live else _standin_routes():
        for q in questions(suite):
            if not live and q.id not in SCRIPTS:
                continue
            conversation = asked[q.follows][0] if q.follows in asked else f"lc-eval-{uuid.uuid4().hex[:12]}"
            turn = f"turn-eval-{uuid.uuid4().hex[:12]}"
            converse = None
            if not live:
                converse = standins[q.id] = StandIn(*SCRIPTS[q.id]())
            started = time.monotonic()
            plan = answer(AskRequest(question=q.question, conversationId=conversation, turnId=turn, by=by),
                          converse=converse)
            seconds = round(time.monotonic() - started, 1)
            asked[q.id] = (plan.conversationId or conversation, plan.turnId or turn)
            kept = EvalRun(
                id=f"er-{uuid.uuid4().hex[:12]}", questionId=q.id, question=q.question,
                mode="live" if live else "offline", models=list(plan.usage.models) or ([STANDIN] if not live else []),
                conversationId=plan.conversationId, turnId=plan.turnId, scores=score(q, plan),
                droppedForNumbers=dropped_for_numbers(plan), claims=len(plan.claims), rejected=plan.rejected,
                declined=plan.declined, toolsCalled=[s.tool for s in plan.trace if s.kind == "tool" and s.tool],
                costUsd=plan.usage.costUsd, at=_now(), by=by, suite=suite, tag=tag, seconds=seconds)
            if judged:
                kept.judged.append((judge_with or judge)(q, plan))
            db.run(_keep(projects.current(), kept))
            out.append(kept)
    return out, standins


def newest(suite: str = DEFAULT, tag: str | None = None) -> list[EvalRun]:
    """The newest kept run of each question of a suite, per tag (one tag
    when named), in the questions' order."""
    order = {q.id: i for i, q in enumerate(questions(suite))}
    latest: dict[tuple[str, str], EvalRun] = {}
    for r in runs():
        if r.suite == suite and r.questionId in order and (tag is None or r.tag == tag):
            latest[(r.tag, r.questionId)] = r
    return sorted(latest.values(), key=lambda r: (r.tag, order[r.questionId]))


def judge_kept(suite: str = DEFAULT, tag: str | None = None,
               judge_with: Callable[[EvalQuestion, AnswerPlan], Judgement] | None = None) -> list[EvalRun]:
    """The newest kept runs of a suite (one tag's when named) judged again by
    the judge route as it stands, each judgement added to those the run holds:
    a second judge reads the same answers the first did."""
    from . import conversations

    held = {q.id: q for q in questions(suite)}
    done = []
    for r in newest(suite, tag):
        if not r.conversationId or not r.turnId:
            continue
        turn = next((t for t in conversations.get(r.conversationId).turns if t.id == r.turnId), None)
        if turn is None or turn.plan is None:
            continue
        r.judged.append((judge_with or judge)(held[r.questionId], turn.plan))
        db.run(_keep(projects.current(), r))
        done.append(r)
    return done


SCORES = ("tools", "citations", "estimates", "bareNumbers")
JUDGED = ("answers", "grounded", "labelled", "coverage")


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def report(found: list[EvalRun]) -> dict[str, Any]:
    """The runs and the mean of each score over them."""
    mean = {n: _mean([getattr(r.scores, n) for r in found]) for n in SCORES}
    return {"runs": [r.model_dump(mode="json") for r in found], "mean": mean}


def summary(suite: str = DEFAULT) -> dict[str, Any]:
    """Each tag's newest runs of a suite side by side: the code's mean
    scores, each judge model's mean scores (labelled with that model), what
    the answers cost and took, and the answers declined."""
    by_tag: dict[str, list[EvalRun]] = {}
    for r in newest(suite):
        by_tag.setdefault(r.tag, []).append(r)
    out: dict[str, Any] = {}
    for tag, found in by_tag.items():
        judges: dict[str, list[Judgement]] = {}
        for r in found:
            for j in r.judged:
                judges.setdefault(j.model, []).append(j)
        out[tag] = {
            "questions": len(found),
            "models": sorted({m for r in found for m in r.models}),
            "code": {n: _mean([getattr(r.scores, n) for r in found]) for n in SCORES},
            "judges": {m: {**{n: _mean([getattr(j, n) for j in js if getattr(j, n) is not None]) for n in JUDGED},
                           "answers judged": sum(j.declined is None for j in js),
                           "declined": [r.questionId for r in found for j in r.judged if j.model == m and j.declined],
                           "costUsd": round(sum(j.costUsd for j in js), 4)} for m, js in judges.items()},
            "costUsd": round(sum(r.costUsd for r in found), 4),
            "seconds": _mean([r.seconds for r in found if r.seconds is not None]),
            "declined": [r.questionId for r in found if r.declined],
            "droppedForNumbers": sum(r.droppedForNumbers for r in found),
        }
    return out
