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

Beside the scores a run keeps how the answer went (alpha 2.2 F.2a): the seconds
from the question to the loop's first step (the code's module sweep), to its
first step of another kind (the model's first: a tool it called, a restart or
the answer; a tool's step lands when the tool returns, so the first tool's own
time is in it) and to the answer, timed through the answer path's `on_step`;
why the loop stopped; its restarts (a model declined or was unavailable, and
the next model of the route was asked); and the validator's reasons for each
thing it dropped.

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
models sit side by side (`summary`). A run may ask some of a suite's questions
alone (`only`), under its tag: a follow-up among them is asked in the
conversation of the newest run of the question it follows under that tag, so a
table stopped part way is finished where it stopped. That conversation holds
what a full asking of the suite has the follow-up read before it; a follow-up
whose conversation there holds anything else (its own earlier asking among
them) is refused in words that name the questions to ask with it, so they are
asked together in a new conversation.

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
scores; a run may be judged again on another judge route (`judge`), and each
judgement is kept. A judgement names the models its route tried, in order, those
of them the safety classifier declined, and the route as it stood, so one Sonnet
gave after Opus declined says so. A judge none of whose route's models answers
(no key, the account's usage limit, the day's cap) stops the pass in words
(`JudgeUnavailable`) that name what the judge route spent on the call it stopped
at, and the run it was judging gains no judgement. Where no model of the plan
route answered the question either, a run's words say to ask it again with the
rest, in a new conversation.

THE SUMMARY (`summary`) sets each tag's newest runs side by side, each run
counted once for each judge model, by that model's newest judgement of it: the
code's scores, each judge's scores, refusals and cost, each judge route's
fallbacks and declines, how far the two judges' scores of the same answers lie
apart, the declines and the restarts counted by kind, the claims kept and
dropped with the drop reasons by kind, the tool calls, the median seconds, the
stops and the cost. `rows` gives one row for each tag's newest run of each
question.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Literal, get_args

from pydantic import BaseModel, Field

from .. import db, llm, projects
from ..db import models as t
from ..db import rows as _rows
from ..models import AnswerPlan, AskRequest, StopReason, TraceStep, Usage

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
    judged and what judging cost. A judge that declined leaves no score:
    `declined` says why, in words, and a mean leaves it out. `tried` names
    the models the judge route asked, in order, so a judgement Sonnet gave
    after Opus declined names both; `refused` names those of them the
    safety classifier declined; and `route` is the judge route as it stood
    when the answer was judged."""

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
    # The models asked, in order (llm.Result.tried, or the models a refusal
    # names); empty on a judgement kept before alpha 2.2 F.2a.
    tried: list[str] = Field(default_factory=list)
    # The judge route's chain when the answer was judged (llm.chain("judge")).
    route: list[str] = Field(default_factory=list)
    # The models of `tried` the safety classifier declined (llm.Result.refused,
    # or each model a refusal names); a model passed over for another reason
    # (a status such as 529, a model the key cannot reach) stands in `tried`
    # alone. Empty on a judgement kept before the F.2a review.
    refused: list[str] = Field(default_factory=list)


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
    # From the question asked to the loop's first step (the code's module
    # sweep), and to its first step of another kind: the model's first, a
    # tool it called, a restart or the answer. A tool's step lands when the
    # tool returns, so the first tool's own time is in the second. Timed
    # through the answer path's on_step; None on a run kept before alpha 2.2 F.2a.
    firstStepSeconds: float | None = None
    firstModelSeconds: float | None = None
    # Why the loop stopped (AnswerPlan.stopped); None on a run kept before F.2a.
    stopped: StopReason | None = None
    # The loop's restart steps, each in its words: a model declined or was
    # unavailable, and the question was asked again on the next.
    restarts: list[str] = Field(default_factory=list)
    # The validator's reason for each thing it dropped (AnswerPlan.rejectionReasons).
    dropReasons: list[str] = Field(default_factory=list)


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


# The engines question 13 expects named in the code: the three the core
# registers (core/pyproject.toml's entry points in the group
# `openferment.engines`). Seeded, its expectation names every engine the
# registry holds then (`engines_here`), the core's three among them, so an
# engine installed beside the core is expected too; the core names no other.
ENGINES_EXPECTED = ("biosteam", "kinetics", "train")
ENGINES_QUESTION = "eq-eth-13"


def _named(names: tuple[str, ...]) -> str:
    """Names in words: `a`, `a and b`, `a, b and c`."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _engines_expected(names: tuple[str, ...]) -> str:
    """What a good answer to question 13 does, naming `names`."""
    return (f"Names each engine registered here ({_named(names)}) from the engine reads: what each runs, what "
            "each takes (its parameters, each with its unit and the origin of its default, or that a run sets it) and "
            "what each gives (the outputs a run of it keeps), and which of the project's runs came from each, set out "
            "as one table with a row for each engine, its cells the ids, units and origins the reads returned, and each "
            "run named by its id and cited by the evidence id or the module row a read returned.")


def engines_here() -> tuple[str, ...]:
    """The engines question 13 expects when its suite is seeded: every name
    the registry holds (the group read in this process, as `engine_plants`
    lists it) and the core's three, in name order."""
    from ..tools.engine import registered_names

    return tuple(sorted({*ENGINES_EXPECTED, *registered_names()}))


def as_seeded(q: EvalQuestion) -> EvalQuestion:
    """A question as a seed keeps it: question 13's expectation names the
    engines here (`engines_here`); every other question as the code holds it."""
    if q.id != ENGINES_QUESTION:
        return q
    return q.model_copy(update={"expects": _engines_expected(engines_here())})


# The owner's twelve (alpha 2.1 execution prompt §5), asked of a project that
# holds the ethanol sources (docs/corpus/ethanol-sources.txt) and their
# extraction, and the two the alpha 2.2 prompt's §5 adds for the base's seams:
# the engine reads (13) and a measurement origin (14), in the prompt's words.
# Words only: what a good answer does. Question 4 asks of
# "that plant", the one question 3 asks of, so it is asked in question 3's
# conversation, as the owner's screen asked it in alpha 2.1 stage B.
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
         [["engine_report"]], ["evidence"], follows=3),
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
         _engines_expected(ENGINES_EXPECTED),
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
        return [EvalQuestion.model_validate(b) for b in await _rows.bodies(s, t.eval_questions, project_id)]


def questions(suite: str | None = None) -> list[EvalQuestion]:
    """The project's questions, oldest first; those of one suite when named."""
    return [q for q in db.run(_questions(projects.current())) if suite is None or q.suite == suite]


async def _seed(project_id: str, by: str, asked: list[EvalQuestion]) -> list[str]:
    made = []
    async with db.session() as s:
        for q in asked:
            if await _rows.body(s, t.eval_questions, project_id, q.id) is None:
                await _rows.put(s, t.eval_questions, project_id, q.id, q.model_copy(update={"by": by, "at": _now()})
                               .model_dump(mode="json"), by=by)
                made.append(q.id)
    return made


def seed(by: str = BY, suite: str = DEFAULT) -> list[str]:
    """A suite's questions kept in the project, those it lacks, each as a
    seed keeps it (`as_seeded`: question 13 names the engines registered
    here now); their ids."""
    if suite not in SUITES:
        raise ValueError(f"there is no suite {suite!r}: the suites are {', '.join(SUITES)}")
    return db.run(_seed(projects.current(), by, [as_seeded(q) for q in SUITES[suite]]))


async def _keep(project_id: str, run: EvalRun) -> None:
    async with db.session() as s:
        await _rows.put(s, t.eval_runs, project_id, run.id, run.model_dump(mode="json"), by=run.by,
                       question_id=run.questionId)


async def _runs(project_id: str) -> list[EvalRun]:
    async with db.session() as s:
        return [EvalRun.model_validate(b) for b in await _rows.bodies(s, t.eval_runs, project_id)]


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
# What a judgement may write, its thinking included: the plan's own turn
# ceiling (plan.MAX_TOKENS). Alpha 2.2 F.2c raised it from 16,000, where three
# of the haiku table's fourteen judgements on Opus at effort max ran out of
# room and five more came near it (ADR-008, Implementation 15). A judgement
# pays for what it writes.
JUDGE_TOKENS = 32000
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
    its scores, its faults and its verdict, labelled with that model, with
    the models the route tried, those of them that declined, and the route
    itself. The caller hands it the project's records and documents to read
    cited ids by (`evidence_pool`, which this package does not import). A
    route whose every model declines
    is a judgement with no score that says so. A route none of whose models
    answers (no key, the account's usage limit, the day's cap) raises
    llm.ModelUnavailable as the call raised it, and the caller keeps no
    judgement."""
    route = llm.chain("judge")
    try:
        got = (call or llm.call)(system=JUDGE_SYSTEM, user=json.dumps(case(q, plan, record, paper), ensure_ascii=False),
                                 schema=JUDGE_SCHEMA, max_tokens=JUDGE_TOKENS, family="judge", label=f"judge {q.id}: ")
    except llm.ModelRefused as e:
        return Judgement(model=", ".join(e.models) or "judge", declined=str(e), costUsd=e.usage.costUsd, at=_now(),
                         tried=list(e.models), refused=list(e.models), route=route)
    data = got.data or {}
    if not data:
        why = "it ran out of room" if got.truncated else "it was not a judgement"
        return Judgement(model=got.model, declined=f"The judge's answer did not arrive whole ({why}).",
                         costUsd=got.usage.costUsd, at=_now(), tried=list(got.tried), refused=list(got.refused),
                         route=route)
    return Judgement(model=got.model, answers=_unit(data.get("answers")), grounded=_unit(data.get("grounded")),
                     labelled=_unit(data.get("labelled")), coverage=_unit(data.get("coverage")),
                     errors=[str(e)[:400] for e in data.get("errors") or []][:20], note=str(data.get("note") or "")[:800],
                     costUsd=got.usage.costUsd, at=_now(), tried=list(got.tried), refused=list(got.refused),
                     route=route)


class Refused(ValueError):
    """A run or a judge pass asked of what the project cannot answer, in
    words; nothing was asked or judged."""


class JudgeUnavailable(RuntimeError):
    """A run or a judge pass stopped where no model on the judge route
    answered (no key, the account's usage limit, the day's cap), in words
    that say where it stopped and how to go on. The run it was judging keeps
    no judgement from it. `done` holds the runs kept or judged before the
    stop, in order: a run's own answer, kept unjudged, comes last among them.
    `spent` is what the judge route spent on the call it stopped at (a
    refusal billed before the next model met the stop), in USD; the day's
    spend table holds it."""

    def __init__(self, words: str, done: list[EvalRun], spent: float = 0.0):
        super().__init__(words)
        self.done = done
        self.spent = spent


def _spent(e: llm.ModelUnavailable) -> str:
    """What the judge route spent on the call it stopped at, in words, or
    nothing when it spent nothing."""
    cost = e.usage.costUsd
    return f" The judge route spent ${cost:.4f} on it first; the day's spend table holds that amount." if cost else ""


# The first words of the final step postdoc_agent.ask gives a plan no model
# of the plan route answered, and the words every refusal begins with
# (llm.ModelRefused). Such a plan with a refusal's words is a decline the
# table gave; one with other words came for want of a model (the key, the
# account's usage limit, the day's cap, the network).
NO_ANSWER = "No answer: "
REFUSAL = re.compile(r"^declined by the safety classifier\b")


def unanswered(plan: AnswerPlan) -> bool:
    """Whether a question went unanswered for want of a model: the plan
    holds no claim, the loop's final step says no answer came, and its
    decline is one `REFUSAL` leaves unmatched."""
    final = next((s for s in reversed(plan.trace) if s.kind == "final"), None)
    return (not plan.claims and final is not None and final.summary.startswith(NO_ANSWER)
            and not REFUSAL.match(plan.declined or ""))


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _listed(ids: list[str], suite: str) -> str:
    """A suite's question ids in words, or how to keep them when the project holds none."""
    return ", ".join(ids) if ids else f"none yet (pnpm eval seed --suite {suite} keeps them)"


# ── a run ──────────────────────────────────────────────────────────────


class _Timed:
    """When a question's steps came, in seconds from when it was asked: its
    first step, and its first of another kind than the code's module sweep
    (the model's first). Handed to the answer path as its `on_step`."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.first: float | None = None
        self.model: float | None = None

    def __call__(self, step: TraceStep) -> None:
        at = time.monotonic() - self.started
        if self.first is None:
            self.first = at
        if self.model is None and step.kind != "coverage":
            self.model = at

    def since(self) -> float:
        return time.monotonic() - self.started


def _seconds(x: float | None) -> float | None:
    """A time a run keeps, to the millisecond, as each of a run's times is kept."""
    return None if x is None else round(x, 3)


def _picked(suite: str, only: list[str] | None) -> list[EvalQuestion]:
    """The project's questions of a suite, in order: each one, or those
    `only` names. Raises Refused, in words, when it names none or one the
    suite lacks."""
    held = questions(suite)
    if only is None:
        return held
    ids = [q.id for q in held]
    if not only:
        raise Refused(f"no question is named; the suite {suite} holds {_listed(ids, suite)}")
    unknown = [x for x in only if x not in ids]
    if unknown:
        raise Refused(f"the suite {suite} in this project holds no question {', '.join(unknown)}; "
                      f"it holds {_listed(ids, suite)}")
    return [q for q in held if q.id in only]


def _ahead(q: EvalQuestion, held: list[EvalQuestion]) -> list[str]:
    """The questions a full asking of a suite (`held`, in order) asks in a
    follow-up's conversation before it, in order: the question it follows
    and each other question that follows that one ahead of it. Empty for a
    question that follows none."""
    if not q.follows:
        return []
    at = [x.id for x in held].index(q.id)
    return [x.id for x in held[:at] if q.follows in (x.id, x.follows)]


def _said(ids: list[str]) -> str:
    """Question ids in words, or that there are none."""
    return _named(tuple(ids)) if ids else "no answered question"


# A question a conversation holds that is none of the suite's, in words.
OTHER_QUESTION = "a question of no suite here"


def _chosen(suite: str, only: list[str] | None, tag: str) -> tuple[list[EvalQuestion], dict[str, str]]:
    """The questions a run asks (`_picked`), and for each follow-up whose
    question `only` leaves out, the conversation of that question's newest
    run under `tag`, which it is asked in. That conversation holds what a
    full asking of the suite has the follow-up read before it (`_ahead`),
    less the questions this run asks there first, so its answer reads what
    the table's own asking read. Raises Refused, in words, for a follow-up
    whose question has no such run, whose question no model of the plan
    route answered there (`unanswered`), or whose conversation there holds
    anything else (its own earlier asking among them), naming the questions
    to add so that they are asked together in a new conversation."""
    from . import conversations

    picked = _picked(suite, only)
    if only is None:
        return picked, {}
    held = questions(suite)
    id_of = {x.question.strip(): x.id for x in held}
    latest = {r.questionId: r for r in newest(suite, tag)}
    opened: dict[str, str] = {}
    for q in picked:
        if not q.follows or q.follows in only:
            continue
        ahead = _ahead(q, held)
        add = _named(tuple(x for x in ahead if x not in only) or (q.follows,))
        before = latest.get(q.follows)
        try:
            turns = conversations.get(before.conversationId).turns if before and before.conversationId else None
        except conversations.ConversationNotFound:
            turns = None
        if before is None or turns is None:
            raise Refused(f"{q.id} follows {q.follows}, and the tag {tag!r} holds no run of {q.follows} whose "
                          f"conversation it could be asked in: name {add} too, so they are asked together")
        turn = next((x for x in turns if x.id == before.turnId), None)
        if turn is not None and turn.plan is not None and unanswered(turn.plan):
            raise Refused(f"{q.id} follows {q.follows}, and no model of the plan route answered {q.follows} in its "
                          f"newest run under the tag {tag!r}: name {add} too, so they are asked again together in a new "
                          "conversation")
        holds = [id_of.get(p.question.strip(), OTHER_QUESTION) for p in conversations.history(before.conversationId)]
        if holds + [x.id for x in picked if x.id in ahead] != ahead:
            raise Refused(f"{q.id} follows {q.follows}, and a full asking of the suite asks it in one conversation "
                          f"after {_said(ahead)}; the conversation of {q.follows}'s newest run under the tag {tag!r} "
                          f"holds {_said(holds)}: name {add} too, so they are asked again together in a new "
                          "conversation")
        opened[q.id] = before.conversationId
    return picked, opened


def _run_stopped(kept: EvalRun, e: llm.ModelUnavailable, before: int, rest: list[str], *, suite: str, tag: str,
                 live: bool, again: list[str] | None = None) -> str:
    """Where a run stopped for want of a judge, and the commands that go on
    from there: the answer judged and the rest asked. Where no model of the
    plan route answered the question either, `again` names the questions to
    ask again, in order: the questions a full asking asks in its
    conversation before it, the question itself and the rest, so each
    follow-up among them reads a conversation of this asking alone."""
    under = f" under the tag {tag!r}" if tag else ""
    asking = f"pnpm eval run{' --live' if live else ''} --suite {suite} --tag {shlex.quote(tag)} --judge"
    words = f"The run{under} stopped at {kept.questionId}: no model on the judge route answered ({e}).{_spent(e)}"
    if again is not None:
        ahead = again[:again.index(kept.questionId)]
        go = "ask it again" + (" with the rest" if rest else "")
        if ahead:
            go += f"{',' if rest else ''} with {_said(ahead)} ahead of it in a new conversation, as a full asking has it"
        return (f"{words} No model of the plan route answered {kept.questionId} either: its run keeps the decline in "
                f"words and no judgement, and the run kept {_count(before, 'answer')} before it. To go on, {go}: "
                f"{asking} --only {','.join(again)}.")
    words += (f" Its answer is kept with no judgement; the run kept {_count(before, 'answer')} before it. To go on, "
              f"judge it with pnpm eval judge --suite {suite} --tag {shlex.quote(tag)} --only {kept.questionId}")
    if rest:
        words += f", and ask the rest with {asking} --only {','.join(rest)}"
    return words + "."


def run(answer: Callable[..., AnswerPlan], *, live: bool = False, by: str = BY, suite: str = DEFAULT,
        tag: str = "", judged: bool = False,
        judge_with: Callable[[EvalQuestion, AnswerPlan], Judgement] | None = None,
        only: list[str] | None = None,
        ) -> tuple[list[EvalRun], dict[str, StandIn]]:
    """Every question of one suite of the project asked through `answer` (an
    AskRequest, a stand-in model or None for the routing table's, and the
    `on_step` that times the answer's steps), scored and kept, in order,
    under `tag`; a question that follows another asked in its conversation.
    `only` names the questions to ask, the rest left as they stand: a
    follow-up whose question it leaves out is asked in the conversation of
    that question's newest run under `tag` (`_chosen`). With `judged`, each
    answer is judged as it is kept (a live run only: offline there is no
    judge model); a judge none of whose route's models answers stops the run
    in words (JudgeUnavailable), the answer it was to judge kept unjudged,
    and the words say to judge it and ask the rest; where no model of the
    plan route answered the question either (`unanswered`), they say to ask
    it again with the rest. Offline, a question with no stand-in script is
    passed over. The runs, and offline the stand-ins each question was asked
    of. Raises Refused, in words and before anything is asked, for questions
    the suite cannot ask as named."""
    if judged and not live and judge_with is None:
        raise Refused("an answer is judged by a model on the judge route, so an offline run is not judged")
    chosen, opened = _chosen(suite, only, tag)
    asked: dict[str, tuple[str, str]] = {}
    out: list[EvalRun] = []
    standins: dict[str, StandIn] = {}
    with contextlib.nullcontext() if live else _standin_routes():
        for i, q in enumerate(chosen):
            if not live and q.id not in SCRIPTS:
                continue
            if q.follows in asked:
                conversation = asked[q.follows][0]
            else:
                conversation = opened.get(q.id) or f"lc-eval-{uuid.uuid4().hex[:12]}"
            turn = f"turn-eval-{uuid.uuid4().hex[:12]}"
            converse = None
            if not live:
                converse = standins[q.id] = StandIn(*SCRIPTS[q.id]())
            clock = _Timed()
            plan = answer(AskRequest(question=q.question, conversationId=conversation, turnId=turn, by=by),
                          converse=converse, on_step=clock)
            seconds = clock.since()
            asked[q.id] = (plan.conversationId or conversation, plan.turnId or turn)
            kept = EvalRun(
                id=f"er-{uuid.uuid4().hex[:12]}", questionId=q.id, question=q.question,
                mode="live" if live else "offline", models=list(plan.usage.models) or ([STANDIN] if not live else []),
                conversationId=plan.conversationId, turnId=plan.turnId, scores=score(q, plan),
                droppedForNumbers=dropped_for_numbers(plan), claims=len(plan.claims), rejected=plan.rejected,
                declined=plan.declined, toolsCalled=[s.tool for s in plan.trace if s.kind == "tool" and s.tool],
                costUsd=plan.usage.costUsd, at=_now(), by=by, suite=suite, tag=tag, seconds=_seconds(seconds),
                firstStepSeconds=_seconds(clock.first), firstModelSeconds=_seconds(clock.model), stopped=plan.stopped,
                restarts=[s.summary for s in plan.trace if s.kind == "restart"],
                dropReasons=list(plan.rejectionReasons))
            if judged:
                try:
                    kept.judged.append((judge_with or judge)(q, plan))
                except llm.ModelUnavailable as e:
                    db.run(_keep(projects.current(), kept))
                    out.append(kept)
                    rest = [x.id for x in chosen[i + 1:] if live or x.id in SCRIPTS]
                    again = None
                    if unanswered(plan):
                        ahead = [x for x in _ahead(q, questions(suite)) if live or x in SCRIPTS]
                        again = [*ahead, q.id, *rest]
                    raise JudgeUnavailable(_run_stopped(kept, e, len(out) - 1, rest, suite=suite, tag=tag, live=live,
                                                        again=again), out, e.usage.costUsd) from e
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


def _pass_stopped(at: EvalRun, e: llm.ModelUnavailable, judged: int, left: list[EvalRun], suite: str) -> str:
    """Where a judge pass stopped, and the commands that judge what it left."""
    tags: dict[str, list[str]] = {}
    for r in left:
        tags.setdefault(r.tag, []).append(r.questionId)
    go_on = "; ".join(f"pnpm eval judge --suite {suite} --tag {shlex.quote(tag)} --only {','.join(ids)}"
                      for tag, ids in tags.items())
    return (f"The judge pass stopped at {at.questionId} of the tag {at.tag!r}: no model on the judge route answered "
            f"({e}).{_spent(e)} That run keeps the judgements it held; the pass judged {_count(judged, 'run')} before "
            f"it, each kept with its new judgement. To judge what is left: {go_on}.")


def judge_kept(suite: str = DEFAULT, tag: str | None = None,
               judge_with: Callable[[EvalQuestion, AnswerPlan], Judgement] | None = None,
               only: list[str] | None = None) -> list[EvalRun]:
    """The newest kept runs of a suite (one tag's when named, those of the
    questions `only` names when it names them) judged again by the judge
    route as it stands, each judgement added to those the run holds: a
    second judge reads the same answers the first did. A judge none of
    whose route's models answers stops the pass in words (JudgeUnavailable):
    the run it was judging keeps the judgements it held, and each run judged
    before it keeps its new one. Raises Refused, in words, for questions the
    suite lacks."""
    from . import conversations

    held = {q.id: q for q in _picked(suite, only)}
    todo = [r for r in newest(suite, tag) if r.questionId in held]
    done: list[EvalRun] = []
    for k, r in enumerate(todo):
        if not r.conversationId or not r.turnId:
            continue
        turn = next((t for t in conversations.get(r.conversationId).turns if t.id == r.turnId), None)
        if turn is None or turn.plan is None:
            continue
        try:
            got = (judge_with or judge)(held[r.questionId], turn.plan)
        except llm.ModelUnavailable as e:
            raise JudgeUnavailable(_pass_stopped(r, e, len(done), todo[k:], suite), done, e.usage.costUsd) from e
        r.judged.append(got)
        db.run(_keep(projects.current(), r))
        done.append(r)
    return done


SCORES = ("tools", "citations", "estimates", "bareNumbers")
JUDGED = ("answers", "grounded", "labelled", "coverage")
# Why the loop stops (AnswerPlan.stopped), in the order a summary counts them.
STOPS: tuple[str, ...] = get_args(StopReason)

# The kinds of thing the validator drops (validate.validate_plan and
# postdoc_agent.held_to_rule_one), each with words its reasons hold, so a
# table's drops are counted by kind: a reason's kind is the first whose words
# it holds, and a reason holding none of them is `other`.
DROP_KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a number in a claim's words", re.compile(r"contains a number")),
    ("a number in a gap or the decline", re.compile(r"dropped: it holds a number")),
    ("a typed value", re.compile(r"\bvalue \d+\b|its values are not a list")),
    ("a quote", re.compile(r"\bquote\b")),
    ("a row cited as evidence", re.compile(r"returned only as a row")),
    ("a citation no tool returned", re.compile(r"no tool returned|do not exist")),
    ("a claim citing nothing", re.compile(r"cites nothing")),
    ("an empty claim", re.compile(r"empty claim text|not a claim")),
)
OTHER_DROP = "other"


def drop_kind(reason: str) -> str:
    """The kind of thing one of the validator's reasons dropped (DROP_KINDS)."""
    return next((kind for kind, words in DROP_KINDS if words.search(reason)), OTHER_DROP)


# The kinds of restart the loop writes (postdoc_agent.ask: "<model> declined;
# asked again on <next>" after a refusal, "<model> was unavailable; asked
# again on <next>" after any other failure), each with the words that say it,
# so a table's restarts are counted by kind; a restart holding neither is `other`.
RESTART_KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("declined", re.compile(r" declined; asked again on ")),
    ("unavailable", re.compile(r" was unavailable; asked again on ")),
)
OTHER_RESTART = "other"


def restart_kind(words: str) -> str:
    """The kind of one of the loop's restart steps, by its words (RESTART_KINDS)."""
    return next((kind for kind, said in RESTART_KINDS if said.search(words)), OTHER_RESTART)


# How much of a judge's verdict a row gives (a judgement keeps up to 800 characters).
NOTE_CHARS = 200


def _mean(xs: list[float], places: int = 3) -> float | None:
    return round(sum(xs) / len(xs), places) if xs else None


def _median(xs: list[float], places: int = 3) -> float | None:
    return round(statistics.median(xs), places) if xs else None


def report(found: list[EvalRun]) -> dict[str, Any]:
    """The runs and the mean of each score over them."""
    mean = {n: _mean([getattr(r.scores, n) for r in found]) for n in SCORES}
    return {"runs": [r.model_dump(mode="json") for r in found], "mean": mean}


# ── the summary ────────────────────────────────────────────────────────


def _took_part(j: Judgement) -> list[str]:
    """The judge models a judgement names, in the order its route tried
    them. The last model a call tried gave the judgement, named by the id
    the API served (llm.call keeps the ids it asked by in `tried`); a
    refusal names each model it tried; a judgement kept before alpha 2.2
    F.2a names each model it was kept under."""
    if not j.tried:
        return [m.strip() for m in j.model.split(",") if m.strip()]
    if j.model == ", ".join(j.tried):
        return list(j.tried)
    return [*j.tried[:-1], j.model]


def _scored(j: Judgement, model: str) -> bool:
    """Whether `model` gave the judgement its scores."""
    return j.declined is None and j.model == model


def _charged(j: Judgement) -> str:
    """The judge model a judgement's cost is charged to: the model that gave
    it, or the first its route tried when each model it tried declined."""
    named = _took_part(j)
    return j.model if not named or j.model in named else named[0]


def _fell_back(j: Judgement) -> bool:
    """Whether a model after the first its route tried gave the judgement."""
    return len(j.tried) > 1 and j.model != ", ".join(j.tried)


def _by_judge(r: EvalRun) -> dict[str, Judgement]:
    """A run's newest judgement in which each judge model took part, by model."""
    latest: dict[str, Judgement] = {}
    for j in r.judged:
        for m in _took_part(j):
            latest[m] = j
    return latest


def _why_unscored(j: Judgement, model: str) -> str:
    """Why a judge model's newest judgement of a run holds no score of its own, in words."""
    if j.model != model and j.model in _took_part(j):
        how = "declined" if model in j.refused else "gave no answer (the command's log names why)"
        return f"{j.model} gave the judgement after {model} {how}" + (f": {j.declined}" if j.declined else "")
    return j.declined or "no score"


def _judges(found: list[EvalRun]) -> dict[str, dict[str, Any]]:
    """Each judge model's mean scores over the answers it scored, each run
    counted once by the model's newest judgement of it; the answers it
    scored; those it gave no score, for any reason (it declined, its route
    passed the answer on to a later model, or its answer did not arrive
    whole); those of them the safety classifier declined on it (`refused`);
    and what the judgements charged to it cost, every one kept."""
    of = [(r, _by_judge(r)) for r in found]
    out: dict[str, dict[str, Any]] = {}
    for m in sorted({m for _, by in of for m in by}):
        mine = [(r, by[m]) for r, by in of if m in by]
        scored = [j for _, j in mine if _scored(j, m)]
        out[m] = {**{n: _mean([v for j in scored if (v := getattr(j, n)) is not None]) for n in JUDGED},
                  "answersJudged": len(scored),
                  "declined": [r.questionId for r, j in mine if not _scored(j, m)],
                  "refused": [r.questionId for r, j in mine if m in j.refused],
                  "costUsd": round(sum(j.costUsd for r in found for j in r.judged if _charged(j) == m), 4)}
    return out


def _routes(found: list[EvalRun]) -> dict[str, dict[str, int]]:
    """Each judge route's newest judgement of each run, the route named by
    its models in order: how many, how many a later model of the route gave
    after the first passed the answer on, and how many hold no score. A
    judgement kept before alpha 2.2 F.2a names no route and is left out."""
    latest: dict[str, dict[str, Judgement]] = {}
    for r in found:
        for j in r.judged:
            if j.route:
                latest.setdefault(" then ".join(j.route), {})[r.id] = j
    return {route: {"judgements": len(js), "fellBack": sum(_fell_back(j) for j in js.values()),
                    "declined": sum(j.declined is not None for j in js.values())} for route, js in latest.items()}


def _disagree(found: list[EvalRun]) -> list[dict[str, Any]]:
    """For each two judge models, how far apart they scored the same answers:
    for each judge score, the mean absolute difference between the two
    models' newest judgements of each answer both scored (`pairs`); and the
    answers either took part in that lack a score from one of them
    (`unpaired`: declined, passed on, or not yet judged by it), which the
    means leave out."""
    of = [_by_judge(r) for r in found]
    models = sorted({m for by in of for m in by})
    out = []
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            pairs = [(by[a], by[b]) for by in of if a in by and b in by and _scored(by[a], a) and _scored(by[b], b)]
            either = sum(a in by or b in by for by in of)
            out.append({"judges": [a, b],
                        **{n: _mean([abs(x - y) for p, q in pairs
                                     if (x := getattr(p, n)) is not None and (y := getattr(q, n)) is not None])
                           for n in JUDGED},
                        "pairs": len(pairs), "unpaired": either - len(pairs)})
    return out


def _tag(found: list[EvalRun]) -> dict[str, Any]:
    """One tag's newest runs, summed up."""
    calls = [len(r.toolsCalled) for r in found]
    costs = [r.costUsd for r in found]
    judging = sum(j.costUsd for r in found for j in r.judged)
    kinds = [drop_kind(x) for r in found for x in r.dropReasons]
    restarted = [restart_kind(x) for r in found for x in r.restarts]
    return {
        "questions": len(found),
        "models": sorted({m for r in found for m in r.models}),
        "code": {n: _mean([getattr(r.scores, n) for r in found]) for n in SCORES},
        "judges": _judges(found),
        "judgeRoutes": _routes(found),
        "judgesDisagree": _disagree(found),
        "declined": [r.questionId for r in found if r.declined],
        "restarts": {r.questionId: list(r.restarts) for r in found if r.restarts},
        "restartCount": {**{kind: restarted.count(kind) for kind, _ in RESTART_KINDS},
                         **({OTHER_RESTART: n} if (n := restarted.count(OTHER_RESTART)) else {})},
        "claims": {"kept": sum(r.claims for r in found), "dropped": sum(r.rejected for r in found),
                   "droppedForNumbers": sum(r.droppedForNumbers for r in found),
                   "dropReasons": {k: n for k in (*(kind for kind, _ in DROP_KINDS), OTHER_DROP)
                                   if (n := kinds.count(k))}},
        "toolCalls": {"mean": _mean(calls), "median": _median(calls)},
        "seconds": {"firstStep": _median([r.firstStepSeconds for r in found if r.firstStepSeconds is not None]),
                    "firstModelStep": _median([r.firstModelSeconds for r in found if r.firstModelSeconds is not None]),
                    "answer": _median([r.seconds for r in found if r.seconds is not None])},
        "stops": {s: sum(r.stopped == s for r in found) for s in STOPS},
        "cost": {"perQuestion": {"mean": _mean(costs, 4), "median": _median(costs, 4)},
                 "answersUsd": round(sum(costs), 4), "judgesUsd": round(judging, 4),
                 "totalUsd": round(sum(costs) + judging, 4)},
    }


def summary(suite: str = DEFAULT) -> dict[str, Any]:
    """Each tag's newest runs of a suite side by side, each run counted once
    for each judge model by that model's newest judgement of it: the code's
    mean scores, each judge's with its refusals, each judge route's fallbacks
    and declines, the judges' disagreement, the declined plans and the
    restarts with their count by kind, the claims kept and dropped with the
    drop reasons by kind, the tool calls, the median seconds, the stops and
    the cost of the newest runs and their judgements; and the judges'
    disagreement pooled over every tag's answers."""
    found = newest(suite)
    by_tag: dict[str, list[EvalRun]] = {}
    for r in found:
        by_tag.setdefault(r.tag, []).append(r)
    return {"suite": suite, "tags": {tag: _tag(held) for tag, held in by_tag.items()},
            "judgesDisagree": _disagree(found)}


def rows(suite: str = DEFAULT) -> list[dict[str, Any]]:
    """One row for each tag's newest run of each question of a suite, in the
    tags' and the questions' order: its models, the code's scores, its tool
    calls, claims kept and dropped, stop, restarts, decline, seconds to the
    first step, to the model's first step and to the answer, and cost; and
    for each judge model, its four scores by its newest judgement of the run
    (each None, with the words why, where it gave none), its verdict cut to
    NOTE_CHARS, and what the judgements of the run charged to it cost."""
    out = []
    for r in newest(suite):
        judges: dict[str, dict[str, Any]] = {}
        for m, j in sorted(_by_judge(r).items()):
            mine = _scored(j, m)
            judges[m] = {**{n: getattr(j, n) if mine else None for n in JUDGED},
                         "declined": None if mine else _why_unscored(j, m),
                         "note": j.note[:NOTE_CHARS] if mine else "",
                         "costUsd": round(sum(x.costUsd for x in r.judged if _charged(x) == m), 4)}
        out.append({
            "tag": r.tag, "questionId": r.questionId, "models": list(r.models), "scores": r.scores.model_dump(),
            "toolCalls": len(r.toolsCalled), "claims": r.claims, "dropped": r.rejected,
            "droppedForNumbers": r.droppedForNumbers, "stopped": r.stopped, "restarts": list(r.restarts),
            "declined": r.declined, "seconds": r.seconds, "firstStepSeconds": r.firstStepSeconds,
            "firstModelSeconds": r.firstModelSeconds, "costUsd": r.costUsd, "judges": judges,
        })
    return out
