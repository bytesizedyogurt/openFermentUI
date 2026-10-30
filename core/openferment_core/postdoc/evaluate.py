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
each question as a turn); `openferment_core.evaluation` is the command:

    python -m openferment_core.evaluation seed           the default questions into the project
    python -m openferment_core.evaluation run [--live]   ask, score and keep; the report as JSON
"""
from __future__ import annotations

import contextlib
import json
import os
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
    # Whether a good answer states a labelled estimate.
    estimate: bool = False
    # The question this one follows, asked first in the same conversation.
    follows: str | None = None
    by: str = BY
    at: str = ""


class EvalScores(BaseModel):
    tools: float
    citations: float
    estimates: float
    bareNumbers: float


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── the store ──────────────────────────────────────────────────────────


async def _questions(project_id: str) -> list[EvalQuestion]:
    async with db.session() as s:
        return [EvalQuestion.model_validate(b) for b in await rows.bodies(s, t.eval_questions, project_id)]


def questions() -> list[EvalQuestion]:
    """The project's questions, oldest first."""
    return db.run(_questions(projects.current()))


async def _seed(project_id: str, by: str) -> list[str]:
    made = []
    async with db.session() as s:
        for q in DEFAULT_QUESTIONS:
            if await rows.body(s, t.eval_questions, project_id, q.id) is None:
                await rows.put(s, t.eval_questions, project_id, q.id, q.model_copy(update={"by": by, "at": _now()})
                               .model_dump(mode="json"), by=by)
                made.append(q.id)
    return made


def seed(by: str = BY) -> list[str]:
    """The default questions kept in the project, those it lacks; their ids."""
    return db.run(_seed(projects.current(), by))


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
        estimates=1.0 if labelled and bool(estimated) == q.estimate else 0.0,
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


# ── a run ──────────────────────────────────────────────────────────────


def run(answer: Callable[..., AnswerPlan], *, live: bool = False,
        by: str = BY) -> tuple[list[EvalRun], dict[str, StandIn]]:
    """Every question of the project asked through `answer` (an AskRequest
    and a stand-in model, or None for the routing table's), scored and kept,
    in order; a question that follows another asked in its conversation.
    Offline, a question with no stand-in script is passed over. The runs, and
    offline the stand-ins each question was asked of."""
    asked: dict[str, tuple[str, str]] = {}
    out: list[EvalRun] = []
    standins: dict[str, StandIn] = {}
    with contextlib.nullcontext() if live else _standin_routes():
        for q in questions():
            if not live and q.id not in SCRIPTS:
                continue
            conversation = asked[q.follows][0] if q.follows in asked else f"lc-eval-{uuid.uuid4().hex[:12]}"
            turn = f"turn-eval-{uuid.uuid4().hex[:12]}"
            converse = None
            if not live:
                converse = standins[q.id] = StandIn(*SCRIPTS[q.id]())
            plan = answer(AskRequest(question=q.question, conversationId=conversation, turnId=turn, by=by),
                          converse=converse)
            asked[q.id] = (plan.conversationId or conversation, plan.turnId or turn)
            kept = EvalRun(
                id=f"er-{uuid.uuid4().hex[:12]}", questionId=q.id, question=q.question,
                mode="live" if live else "offline", models=list(plan.usage.models) or ([STANDIN] if not live else []),
                conversationId=plan.conversationId, turnId=plan.turnId, scores=score(q, plan),
                droppedForNumbers=dropped_for_numbers(plan), claims=len(plan.claims), rejected=plan.rejected,
                declined=plan.declined, toolsCalled=[s.tool for s in plan.trace if s.kind == "tool" and s.tool],
                costUsd=plan.usage.costUsd, at=_now(), by=by)
            db.run(_keep(projects.current(), kept))
            out.append(kept)
    return out, standins


def report(found: list[EvalRun]) -> dict[str, Any]:
    """The runs and the mean of each score over them."""
    names = ("tools", "citations", "estimates", "bareNumbers")
    mean = {n: round(sum(getattr(r.scores, n) for r in found) / len(found), 3) if found else None for n in names}
    return {"runs": [r.model_dump(mode="json") for r in found], "mean": mean}
