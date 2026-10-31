"""FastAPI app — openferment-core's first surface (OF-BLD-007 §4).

The seam is Python rather than a Node proxy on purpose. An API key cannot live
in the browser, so a server is required either way; and every tool Postdoc will
eventually orchestrate — COBRApy, BioSTEAM, the sequence stack — is Python.
A throwaway JS proxy would mean building this boundary twice.

Run it from `core/`:

    uv run uvicorn openferment_core.api:app --reload

After a `pnpm build` the same process serves the app itself at / (§B.4 at the
bottom of this file), so http://127.0.0.1:8000 is the whole of openFerment.

The browser never sees a key and never renders model prose. It renders a plan.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy.exc import InterfaceError, OperationalError

from . import artifacts, biorepo, checks, db, extract, fermos, geneos, guard, guild, intake, postdoc_agent, practice, projects, tools, witness
from .literature import kit
from .workers import WorkerCrashed, WorkerError, WorkerTimeout
from .models import (
    AuditEntry,
    Proposal,
    ProposalAction,
    AnswerPlan,
    Artifact,
    AskRequest,
    LiveConversation,
    ToolCallRecord,
    Check,
    CheckDismiss,
    CheckRecord,
    CheckRequest,
    Checks,
    CheckSchedule,
    DecisionCheck,
    ExtractResponse,
    ExtractRun,
    FermosFitRequest,
    FermosFitResponse,
    CollectOutcome,
    CollectRequest,
    ForecastRequest,
    ParamResolveRequest,
    ProformaRunRequest,
    ProposeRequest,
    SimulationRequest,
    ThermoPropsRequest,
    TrainFromRunRequest,
    TrainRunRequest,
    TrainSpec,
    VesselDesign,
    VesselRequest,
    ForecastResult,
    GeneosModelInfo,
    GeneosResult,
    Guild,
    GuildEvidence,
    GuildPerson,
    GuildPolicy,
    GuildWithdrawal,
    LiteratureDocument,
    SearchHit,
    SearchResponse,
    Overlay,
    PasteRequest,
    LiteratureQuestion,
    Practice,
    PracticeDraftRequest,
    PracticeScenario,
    PracticeSession,
    PracticeTurnRequest,
    Project,
    ProjectCreate,
    LibraryParameters,
    LibraryRunRequest,
    RunReport,
    EngineRun,
    ScenarioCreate,
    StudyRequest,
    StudyScenario,
    ComparisonCreate,
    ComparisonReport,
    Runbook,
    RunbookCreate,
    StudyComparison,
    LibraryShelf,
    PackageRegression,
    ReplayResult,
    ReviewDecision,
    SFFExportRequest,
    SFFFlowsheet,
    SFFLibraryEntry,
    SFFLibraryImport,
    ToolInfo,
    ToolResult,
)
from . import llm
from .engine import library as _library  # noqa: F401  (registers the library.run tool for compute and replay)
from .engine import runs as _runs
from .studies import comparisons as _comparisons  # noqa: F401  (registers study.comparison for compute and replay)
from .studies import exports as _exports
from .studies import runbooks as _runbooks
from .studies import scenarios as _scenarios
from .postdoc import conversations as _conversations
from . import events as event_stream

# core/.env, which is gitignored. Loaded here rather than by the shell so that
# `uv run uvicorn ...` works with no ceremony; `override=False` means a real
# environment variable still wins, which is what CI would set.
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("openferment.api")

app = FastAPI(title="openferment-core", version="0.1.0")


# What acts in no project: health, and the projects themselves. A page that
# remembers a project the database no longer holds can still ask these.
UNSCOPED = ("/api/health", "/api/projects")


def _scoped_openapi() -> dict[str, Any]:
    """The OpenAPI document (docs/api/openapi.json, `pnpm gen:api`) with every
    route's project scope written on it (ADR-005; acceptance A5): a route that
    acts in a project says so (`x-openferment-scope: project`) and takes the
    project's id in the X-OpenFerment-Project header, or `?project=` where a
    header cannot be sent (an EventSource); the routes that act in none say
    `none`."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    for path, item in schema.get("paths", {}).items():
        scoped = not path.startswith(UNSCOPED)
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            operation["x-openferment-scope"] = "project" if scoped else "none"
            if scoped:
                operation.setdefault("parameters", []).append({
                    "name": projects.HEADER, "in": "header", "required": False, "schema": {"type": "string"},
                    "description": f"The project the request acts in; ?{projects.QUERY}= in its place."})
    app.openapi_schema = schema
    return schema


app.openapi = _scoped_openapi  # type: ignore[method-assign]


# Starlette runs the middleware added last first, so this one, added before
# the guard below, runs after it: a refused request never reaches the database.
@app.middleware("http")
async def act_in_the_named_project(request: Request, call_next):
    """Every /api and /rag request acts in the project it names (ADR-005), in
    the `X-OpenFerment-Project` header or `?project=`. A request that names one
    the database does not hold stops here with a 404; one that names none goes
    on in no project, and a store call it makes is refused with a 422."""
    if not request.url.path.startswith(("/api/", "/rag/")):
        return await call_next(request)
    named = request.headers.get(projects.HEADER) or request.query_params.get(projects.QUERY)
    if named is None or request.url.path.startswith(UNSCOPED):
        with projects.using(None):
            return await call_next(request)
    named = named.strip()
    if not projects.valid_id(named):
        return JSONResponse(status_code=422, content={"detail": f"{named!r} is not a project id"})
    try:
        known = await db.arun(projects.held(named))
    except Exception as e:  # the database is down or unset: say so, never 500
        return JSONResponse(status_code=503, content={"detail": _database_down(e)})
    if not known:
        return JSONResponse(status_code=404, content={"detail": f"no project named {named!r}"})
    with projects.using(named):
        return await call_next(request)


def _database_down(e: Exception) -> str:
    if isinstance(e, db.DatabaseUnavailable):
        return str(e)
    return (
        f"The database did not answer ({e.__class__.__name__}). Start PostgreSQL (`pnpm db:up`) "
        f"or check {db.URL_SETTING} in core/.env."
    )


@app.exception_handler(projects.ProjectRequired)
async def _no_project(request: Request, e: projects.ProjectRequired) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(e)})


@app.exception_handler(db.DatabaseUnavailable)
async def _no_database(request: Request, e: db.DatabaseUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(e)})


@app.exception_handler(OperationalError)
@app.exception_handler(InterfaceError)
@app.exception_handler(ConnectionRefusedError)
async def _database_unreachable(request: Request, e: Exception) -> JSONResponse:
    log.warning("the database did not answer %s %s: %s", request.method, request.url.path, e)
    return JSONResponse(status_code=503, content={"detail": _database_down(e)})


@app.middleware("http")
async def refuse_changes_from_elsewhere(request: Request, call_next):
    """A changing request from another site, or under a hostile name, stops
    here with a 403 that says why (guard.py, OF-BLD-012 §B.6)."""
    why = guard.refusal(request.method, request.headers)
    if why is not None:
        log.warning("refused %s %s: %s", request.method, request.url.path, why)
        return JSONResponse(status_code=403, content={"detail": why})
    return await call_next(request)

@app.get("/api/health")
def health() -> dict:
    """Liveness, and what the service can actually do right now.

    `hasKey` lets the UI tell "the service is down" from "the service is up but
    has no key" — two different problems with two different fixes, and a single
    "unavailable" would send somebody to restart a process that is running fine.
    """
    return {
        "ok": True,
        "service": "openferment-core",
        "model": llm.primary(),
        # The model a call falls back to when the primary declines or is
        # unavailable (llm.py).
        "fallbackModel": llm.fallback(),
        "hasKey": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


def _ask_agent(question: str, on_step=None, cancelled=None, history=None, on_call=None, on_result=None,
               converse=None) -> AnswerPlan:
    """The bounded loop (OF-BLD-014 §5.2) over the evidence pool as it stands,
    with the conversation's earlier turns when the question is a follow-up.
    `converse` stands in for the model (the evaluation's offline stand-in);
    None asks the routing table's models."""
    return postdoc_agent.ask(question, ctx=tools.ToolContext(), on_step=on_step, cancelled=cancelled, history=history,
                             on_call=on_call, on_result=on_result, converse=converse)


def _answer(request: AskRequest, *, on_step=None, cancelled=None, on_turn=None, converse=None) -> AnswerPlan:
    """One question through the loop, kept as a turn of its conversation
    (postdoc/conversations.py): a follow-up's history read from what the
    service keeps, each tool call kept under the turn with what it answered,
    and the turn, each step, each call and the plan said on the project's
    event stream (events.py) as they happen."""
    question = request.question.strip()
    try:
        cid, tid, seq = _conversations.begin(question, conversation_id=request.conversationId, turn_id=request.turnId,
                                             by=request.by)
    except _conversations.ConversationRefused as e:
        return AnswerPlan(question=question, declined=str(e))
    who = request.by.strip() or "this browser"
    ids = {"conversationId": cid, "turnId": tid}
    if on_turn is not None:
        on_turn({**ids, "seq": seq})
    event_stream.publish("turn.started", {**ids, "seq": seq, "question": question, "by": who})
    history = _conversations.history(cid) if request.conversationId else list(request.history)
    artifacts: list[str] = []

    def step(s) -> None:
        event_stream.publish("turn.delta", {**ids, "step": s.model_dump(mode="json")})
        if on_step is not None:
            on_step(s)

    def call(name: str, args: dict) -> None:
        event_stream.publish("tool.call", {**ids, "tool": name, "input": args})

    def result(name: str, args: dict, res: ToolResult) -> None:
        kept = _conversations.called(tid, name, args, res, by=who)
        artifacts.extend(a for a in kept if a not in artifacts)
        event_stream.publish("tool.result", {**ids, "tool": name, "ok": res.error is None, "error": res.error,
                                             "hits": len(res.recordIds) + len(res.passages) + len(res.evidence) + len(res.rows),
                                             "evidenceIds": [e.id for e in res.evidence], "artifactIds": kept})

    try:
        plan = _ask_agent(question, on_step=step, cancelled=cancelled, history=history, on_call=call, on_result=result,
                          converse=converse)
    except Exception as e:
        _conversations.finish(tid, plan=None, steps=[], artifacts=artifacts, error=_conversations.error_of(
            f"Postdoc failed while answering: {type(e).__name__}."))
        raise
    plan = plan.model_copy(update=ids)
    _conversations.finish(tid, plan=plan, steps=plan.trace, artifacts=artifacts, stopped=bool(cancelled and cancelled()))
    event_stream.publish("turn.decline" if plan.declined else "turn.plan", {**ids, "plan": plan.model_dump(mode="json")})
    return plan


@app.post("/api/ask", response_model=AnswerPlan)
def ask(request: AskRequest) -> AnswerPlan:
    """One question in, one AnswerPlan out: the bounded loop of tools
    (OF-BLD-014 §5.2), kept as a turn of its conversation.

    Every failure below returns a plan with `declined` set rather than an HTTP
    error, because a declined plan is a thing the UI already knows how to
    render honestly and a 500 is a thing it can only apologise for. The one
    exception is the service being unreachable, which the browser detects
    itself — there is no response to put a reason in.
    """
    if not request.question.strip():
        return AnswerPlan(question="", declined="Ask a question and Postdoc will answer it.")
    return _answer(request)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/ask/stream")
def ask_stream(request: AskRequest) -> StreamingResponse:
    """The loop's steps as they complete (OF-BLD-014 §5.3), as server-sent
    events: `turn` (the conversation and the turn the service keeps the
    question as), each `step` (a TraceStep), then `plan` (the validated
    AnswerPlan), or `error` when the service itself failed. A declined plan
    is a `plan`. The same turn is said on the project's event stream
    (`GET /api/events`)."""
    return StreamingResponse(_stream_events(request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _stream_events(request: AskRequest):
    """The events of one question, as text. When the reader goes, the
    generator is closed, and the loop stops before its next model turn
    (§5.R) rather than spending on an answer nobody will read."""
    inbox: queue.Queue = queue.Queue()
    gone = threading.Event()

    def work() -> None:
        try:
            if not request.question.strip():
                plan = ask(request)
            else:
                plan = _answer(request, on_step=lambda s: inbox.put(("step", s.model_dump(mode="json"))),
                               cancelled=gone.is_set, on_turn=lambda turn: inbox.put(("turn", turn)))
            inbox.put(("plan", plan.model_dump(mode="json")))
        except Exception as e:  # the stream must end in words, never hang
            log.exception("ask stream failed")
            inbox.put(("error", {"message": f"Postdoc failed while answering: {type(e).__name__}. The service log names what went wrong."}))
        finally:
            inbox.put(None)

    # The loop runs on a thread of its own, in this request's project.
    threading.Thread(target=contextvars.copy_context().run, args=(work,), name="ask-stream", daemon=True).start()
    try:
        while (item := inbox.get()) is not None:
            yield _sse(*item)
    finally:
        gone.set()


# ── conversations and the event stream (execution prompt §4.8, §7.3) ──


@app.get("/api/conversations", response_model=list[LiveConversation])
def conversations_listed() -> list[LiveConversation]:
    """The project's Postdoc conversations, oldest first, each with its turns."""
    return _conversations.listed()


@app.get("/api/conversations/{conversation_id}", response_model=LiveConversation)
def conversation(conversation_id: str) -> LiveConversation:
    try:
        return _conversations.get(conversation_id)
    except _conversations.ConversationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


@app.get("/api/conversations/{conversation_id}/turns/{turn_id}/calls", response_model=list[ToolCallRecord])
def conversation_calls(conversation_id: str, turn_id: str) -> list[ToolCallRecord]:
    """The tool calls one turn made, in order, each with what it answered the
    model and what it offered to cite."""
    try:
        return _conversations.calls(conversation_id, turn_id)
    except _conversations.ConversationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


@app.get("/api/events")
def project_events(request: Request, after: int | None = None) -> StreamingResponse:
    """The project's events as they happen (events.py): jobs, tool calls,
    artifacts kept and Postdoc's turns, as server-sent events. `Last-Event-ID`
    (an EventSource's reconnection) or `?after=` resumes after the event a
    page saw last; a page that names none is sent what happens from now."""
    header = request.headers.get("last-event-id")
    try:
        resume = int(header) if header else after
    except ValueError:
        resume = after
    return StreamingResponse(event_stream.stream(projects.current(), resume), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── geneOS (OF-BLD-014 §6.3) ───────────────────────────────────────────


class CeilingRequest(BaseModel):
    modelId: str
    product: str = "ethanol"
    substrate: str


class MixRequest(BaseModel):
    modelId: str
    product: str = "ethanol"
    a: str
    b: str


def _geneos(fn, *args) -> GeneosResult:
    """A model that cannot load here, or a request the worker refuses, is a
    409 in words; a finding is a 200 that says so."""
    try:
        return fn(*args)
    except geneos.GeneosUnavailable as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=409, detail=f"the geneOS worker could not compute it: {e}") from e


@app.get("/api/geneos/models", response_model=list[GeneosModelInfo])
def geneos_models() -> list[GeneosModelInfo]:
    return geneos.models()


@app.post("/api/geneos/ceiling", response_model=GeneosResult)
def geneos_ceiling(req: CeilingRequest) -> GeneosResult:
    return _geneos(geneos.ceiling, req.modelId, req.product, req.substrate)


@app.post("/api/geneos/frontier", response_model=GeneosResult)
def geneos_frontier(req: CeilingRequest) -> GeneosResult:
    return _geneos(geneos.frontier, req.modelId, req.product, req.substrate)


@app.post("/api/geneos/mix", response_model=GeneosResult)
def geneos_mix(req: MixRequest) -> GeneosResult:
    return _geneos(geneos.mix, req.modelId, req.product, req.a, req.b)


# ── fermOS (OF-BLD-014 §7.2) ───────────────────────────────────────────


@app.post("/api/fermos/fit", response_model=FermosFitResponse)
def fermos_fit(req: FermosFitRequest) -> FermosFitResponse:
    """Fit a run's series. The browser sends them; the service keeps the
    fits as artifacts (a sample run's are kept nowhere) and nothing else."""
    try:
        return fermos.fit(req.depositionId, req.series, sample=req.sample, family=req.family)
    except fermos.FitRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/fermos/forecast", response_model=ForecastResult)
def fermos_forecast(req: ForecastRequest) -> ForecastResult:
    """A band for the next run from a fit (§7.3). A refusal says which
    parameter the run did not identify, and what run would."""
    try:
        return fermos.forecast_run(fit_artifact=req.fitArtifactId, fit_inline=req.fit if req.sample else None,
                                   start=req.start, changed_by=req.changedBy, duration_h=req.durationH, sample=req.sample,
                                   duration_by=req.durationBy)
    except fermos.FitRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# ── fermOS simulates (OF-BLD-020 §3.1) ─────────────────────────────────


@app.get("/api/fermos/families")
def fermos_families() -> list[dict]:  # noqa: N803 (the wire name)
    """The model families (`FamilyInfo`): each with its equations, states,
    parameters (ParameterSpecs) and the panel's groups."""
    return [f.model_dump(mode="json") for f in fermos.families()]


@app.get("/api/fermos/families/{family_id}")
def fermos_family(family_id: str) -> dict:
    """One model family by id; 404 in words for none."""
    from . import kinetics

    try:
        return fermos.family_info(family_id).model_dump(mode="json")
    except kinetics.FamilyRefused as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/fermos/simulate")
def fermos_simulate(req: SimulationRequest) -> dict:
    """Simulate a model family (`SimulationResult`) and keep it as one
    `fermos.simulation` artifact. Each parameter resolves with its source: a
    person's override (an assumption by name, so the result is `assumed`), else
    the family's stated convention. 422 in words for a parameter that waits
    (named with what would bind it), the light socket, a bad override, or a
    run that cannot end."""
    try:
        return fermos.simulate(req).model_dump(mode="json")
    except fermos.SimulationRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/fermos/bind")
def fermos_bind(family: str, strain: str | None = None, product: str | None = None, sugar: str | None = None,
                fit: str | None = None, startFrom: str = "records",  # noqa: N803 (the wire name)
                durationPreset: str = "until-sugar-runs-out",  # noqa: N803
                overrides: str | None = None) -> dict:
    """A family's parameters bound for a strain, product and sugar
    (`FermosBinding`, OF-BLD-020 §3.2, D6): each from the fit a person chose
    (`?fit=`), the records of the evidence pool through the aggregate gate, a kept simulation (`?startFrom=simulation:<id>`), or the
    spec's convention, with its source; what waits, each named with the field
    that would bind it; and notes saying what bound from where. `?overrides=`
    (a JSON list of the person's overrides of `fermos:family:<family>`, as
    the simulation would carry them; OF-BLD-020 §3.3) lays them on, so
    `waiting` is what Simulate would refuse for. Starts no integration and
    keeps nothing. 404 for a family no one declared; 422 in words for a fit
    or simulation not on file, a fit of another family, a sugar or id that is
    not one, or an override of another scope."""
    from . import kinetics

    if family not in kinetics.FAMILIES:
        raise HTTPException(status_code=404, detail=f"there is no model family {family!r}: the families are "
                                                    f"{', '.join(kinetics.FAMILIES)}")
    if durationPreset not in ("until-sugar-runs-out", "fit-length"):
        raise HTTPException(status_code=422, detail=f"a run-length preset is until-sugar-runs-out or fit-length; "
                                                    f"{durationPreset!r} is neither")
    req = SimulationRequest(family=family, strain=strain, product=product, sugar=sugar, fitArtifact=fit,
                            startFrom=startFrom, durationPreset=durationPreset,
                            overrides=_overrides_param(overrides))
    try:
        return fermos.bind(req).model_dump(mode="json")
    except fermos.SimulationRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/fermos/simulations")
def fermos_simulations() -> list[dict]:  # noqa: N803 (the wire name)
    """The kept simulations, newest first (`SimulationSummary`). A read: it
    runs nothing."""
    return [s.model_dump(mode="json") for s in fermos.simulations()]


@app.get("/api/fermos/harvest")
def fermos_harvest(simulation: str, hour: float | None = None) -> dict:  # noqa: N803 (the wire name)
    """A kept simulation's broth at an hour (`FermosHarvest`, OF-BLD-020
    §6.2, D10): its own harvest hour, or `?hour=`, a person's (the hour the
    Builder's inlet scope holds under their name; a model never sends one),
    read from the series the artifact keeps, each state with its unit, the
    hour's source and how it was read. A read: nothing is integrated again
    and nothing is kept. 404 for a simulation not on file, 409 for one
    damaged on disk, 422 in words for an hour outside the simulated span, a
    simulation that keeps no product in the broth, and another artifact."""
    from . import artifacts

    try:
        art = artifacts.get(simulation)
    except artifacts.ArtifactNotFound:
        raise HTTPException(status_code=404, detail=f"there is no kept simulation {simulation} here: fermOS → "
                                                    "Simulate keeps one") from None
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    try:
        return fermos.harvest(art, hour).model_dump(mode="json")
    except fermos.SimulationRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/fermos/fits")
def fermos_fits(flowsheet: str) -> list[dict]:  # noqa: N803 (the wire name)
    """The kinetic fits, forecasts and simulations fermOS keeps (a
    simulation since OF-BLD-020 §3.3), newest first, each with what it can
    feed a shelf flowsheet's titre, yield and productivity and why not
    (OF-BLD-019 §5.1, D10). A person picks one on the scenario page;
    a read: it keeps nothing. A flowsheet a scenario cannot run is a 422."""
    from . import proforma

    try:
        return [f.model_dump(mode="json") for f in proforma.fermos_fits(flowsheet)]
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _fits_param(raw: str | None) -> dict[str, str]:
    """`?fits=` on GET /api/proforma/bind: a JSON object of input key to
    artifact id, as ProformaRunRequest.fits carries it."""
    if not raw:
        return {}
    try:
        fits = json.loads(raw)
    except (ValueError, RecursionError):
        # OF-BLD-019 §7.R: JSON nested past Python's recursion limit is
        # malformed like any other, refused in words, never a bare 500.
        fits = None
    if not isinstance(fits, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in fits.items()):
        raise HTTPException(status_code=422, detail="fits is a JSON object of input key to the id of a kept fermOS fit")
    return fits


def _train_param(raw: str | None) -> TrainSpec | None:
    """`?train=` on GET /api/params/{scope} (OF-BLD-020 §5.2): the whole
    TrainSpec as JSON, as the resolve's `train` carries it; refused in words
    when it is not one."""
    from pydantic import ValidationError

    if not raw:
        return None
    try:
        return TrainSpec.model_validate_json(raw)
    except (ValidationError, ValueError, RecursionError) as e:
        first = str(e).splitlines()[0] if str(e) else type(e).__name__
        raise HTTPException(status_code=422, detail=f"train is a pureOS train as JSON (a TrainSpec): {first}") from None


def _assumptions_param(raw: str | None) -> list:
    """`?assumptions=` on GET /api/proforma/ceiling-check: a JSON list of
    named persons' assumptions, as ProformaRunRequest.assumptions carries
    them."""
    from pydantic import TypeAdapter, ValidationError

    from .models import InputAssumption

    if not raw:
        return []
    try:
        return TypeAdapter(list[InputAssumption]).validate_json(raw)
    except (ValidationError, RecursionError):
        raise HTTPException(status_code=422, detail="assumptions is a JSON list of assumptions, each with key, value, "
                                                    "low, high, by and at, as a run takes them") from None


def _overrides_param(raw: str | None) -> list:
    """`?overrides=` on GET /api/proforma/bind and the ceiling check: a JSON
    list of a person's overrides from the parameter panel (OF-BLD-020 D3),
    as ProformaRunRequest.overrides carries them."""
    from pydantic import TypeAdapter, ValidationError

    from .models import Override

    if not raw:
        return []
    try:
        return TypeAdapter(list[Override]).validate_json(raw)
    except (ValidationError, RecursionError):
        raise HTTPException(status_code=422, detail="overrides is a JSON list of overrides, each with scope, key, value, "
                                                    "by and at, as a run takes them") from None


@app.get("/api/proforma/status")
def proforma_status() -> dict:
    """Where the BioSTEAM worker is (§8.1): cold, starting, ready or failed."""
    from . import proforma

    return proforma.status()


@app.get("/api/proforma/shelf")
def proforma_shelf() -> list[dict]:  # noqa: N803 (the wire name)
    """The shelf of flowsheets (OF-BLD-019 §2.1, D2): pure data, read with no
    simulator."""
    from . import proforma

    return [f.model_dump(mode="json") for f in proforma.shelf()]


@app.get("/api/proforma/benchmark")
def proforma_benchmark() -> dict:
    """The benchmark this installation reproduced (§8.2), or none yet. A read:
    it starts nothing. POST runs it."""
    from . import proforma

    art = proforma.stored_benchmark()
    return {"artifact": art.model_dump(mode="json") if art else None, "simulator": proforma.status()}


@app.post("/api/proforma/benchmark")
def proforma_benchmark_run() -> dict:
    """Run the published corn stover biorefinery and keep its price (§8.2)."""
    from . import proforma
    from .workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        art = proforma.run_benchmark()
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not run the benchmark: {e}") from e
    return {"artifact": art.model_dump(mode="json"), "simulator": proforma.status()}


@app.get("/api/proforma/reference/{flowsheet_id}")
def proforma_reference(flowsheet_id: str) -> dict:
    """A reference biorefinery on the shelf (OF-BLD-019 §2.2): its entry, the
    newest stored run or none, its package test's values, the simulator's
    status. A read: it starts nothing. 404 for an id that is not a
    reference biorefinery on the shelf."""
    from . import proforma

    try:
        return proforma.reference(flowsheet_id).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/proforma/reference/{flowsheet_id}")
def proforma_reference_run(flowsheet_id: str) -> dict:
    """Run a reference biorefinery whole on its package's defaults and keep
    it as one `proforma.reference` artifact (a basis already run returns its
    stored artifact)."""
    from . import proforma
    from .workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        art = proforma.run_reference(flowsheet_id)
        return proforma.reference(flowsheet_id, art).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not run {flowsheet_id}: {e}") from e


# ── SFF flowsheet records (alpha 2.0, ADR-003; engine/sff.py) ────────────


def _sff_refused(e: Exception, status: int = 422) -> HTTPException:
    return HTTPException(status_code=status, detail=str(e))


@app.get("/api/flowsheets", response_model=list[SFFFlowsheet])
def flowsheets_listed() -> list[SFFFlowsheet]:
    """The project's SFF records, newest first, without their graphs."""
    from .engine import sff

    return sff.listed(project_id=projects.current())


@app.get("/api/flowsheets/library", response_model=list[SFFLibraryEntry])
def flowsheets_library() -> list[SFFLibraryEntry]:
    """The toolkit's reference flowsheets at the pinned commit, and which this
    machine has fetched. A read: it fetches nothing and starts no worker."""
    from .engine import sff

    return sff.library()


@app.post("/api/flowsheets/library/{file_id}", response_model=SFFFlowsheet)
def flowsheets_library_import(file_id: str, request: SFFLibraryImport) -> SFFFlowsheet:
    """One reference flowsheet fetched from the pinned commit (or found here),
    its hash checked, checked by the toolkit in the worker, drawn and kept in
    the project with origin `library`."""
    from .engine import sff

    try:
        return sff.import_library(file_id, project_id=projects.current(), by=request.by)
    except sff.FlowsheetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e
    except sff.SFFRefused as e:
        raise _sff_refused(e) from e
    except sff.LibraryUnavailable as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not check {file_id}: {e}") from e


@app.post("/api/flowsheets/import", response_model=SFFFlowsheet)
def flowsheets_import(file: UploadFile = File(...), by: str = Form(..., min_length=1, max_length=200)) -> SFFFlowsheet:
    """An SFF file a person uploads: read, checked by the toolkit in the
    worker (a file that fails validation is kept with its findings), drawn
    and kept. 413 past the size an import takes; 422 for a file that is not
    an SFF flowsheet."""
    from .engine import sff

    data = file.file.read(sff.MAX_FILE + 1)
    if len(data) > sff.MAX_FILE:
        raise HTTPException(status_code=413, detail=f"{file.filename} is larger than {sff.MAX_FILE // (1024 * 1024)} MB")
    try:
        return sff.import_sff(data, file.filename or "", project_id=projects.current(), by=by)
    except sff.SFFRefused as e:
        raise _sff_refused(e) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not check the file: {e}") from e


@app.post("/api/flowsheets/export", response_model=SFFFlowsheet)
def flowsheets_export(request: SFFExportRequest) -> SFFFlowsheet:
    """A kept run's base case written as an SFF file by the toolkit in the
    worker, checked, drawn and kept with origin `run`. 404 for a run the
    project does not hold; 422 for an artifact that is not a run."""
    from . import proforma
    from .engine import sff

    try:
        art = artifacts.get(request.artifactId)
    except artifacts.ArtifactNotFound as e:
        raise HTTPException(status_code=404, detail=f"the project holds no run {request.artifactId}") from e
    try:
        plant = _library.plant_of(art) if art.tool == _library.LIBRARY_RUN else proforma.plant_of(art)
        return sff.export(plant, project_id=projects.current(), run_artifact_id=art.id, by=request.by)
    except (proforma.ScenarioRefused, sff.SFFRefused, _library.LibraryRefused) as e:
        raise _sff_refused(e) from e
    except WorkerError as e:
        raise HTTPException(status_code=409, detail=f"the run's base case could not be exported: {e}") from e
    except (WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not export the run: {e}") from e


@app.get("/api/flowsheets/{record_id}", response_model=SFFFlowsheet)
def flowsheets_record(record_id: str) -> SFFFlowsheet:
    """One SFF record, its graph included."""
    from .engine import sff

    try:
        return sff.get(record_id, project_id=projects.current())
    except sff.FlowsheetNotFound as e:
        raise HTTPException(status_code=404, detail=f"the project holds no flowsheet {record_id}") from e


@app.get("/api/flowsheets/{record_id}/file")
def flowsheets_file(record_id: str):
    """The SFF file as it is held, byte for byte as it came."""
    from fastapi.responses import Response

    from .engine import sff

    try:
        text = sff.document(record_id, project_id=projects.current())
    except sff.FlowsheetNotFound as e:
        raise HTTPException(status_code=404, detail=f"the project holds no flowsheet {record_id}") from e
    return Response(content=text.encode("utf-8"), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{record_id}.sff.json"'})


# ── Library plants (alpha 2.0, ADR-004; engine/library.py) ──────────────


@app.get("/api/library", response_model=LibraryShelf)
def library_shelf() -> LibraryShelf:
    """Every subpackage of the installed biorefineries as discovery read it:
    each plant's entry point, configurations, package tests, the changes it
    needs to build here, and whether each configuration built. A read: it
    starts no simulator."""
    return _library.shelf()


def _library_plant(plant: str) -> None:
    try:
        _library.plant(plant)
    except _library.PlantNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


@app.get("/api/library/{plant}/parameters", response_model=LibraryParameters)
def library_parameters(plant: str, configuration: str | None = None) -> LibraryParameters:
    """A plant's parameters as the package builds it, each read back from a
    fresh build in the worker with origin `library-default`."""
    _library_plant(plant)
    try:
        return _library.parameters(plant, configuration)
    except _library.LibraryRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not build {plant}: {e}") from e


@app.get("/api/library/{plant}/regression", response_model=PackageRegression | None)
def library_regression(plant: str, configuration: str | None = None) -> PackageRegression | None:
    """The values the package's own test for this plant asserts, read from
    the installed file; null when it has none. A read."""
    _library_plant(plant)
    return _library.regression(plant, configuration)


@app.post("/api/library/{plant}/run", response_model=RunReport)
def library_run(plant: str, request: LibraryRunRequest) -> RunReport:
    """One engine run of a library plant or an openFerment flowsheet, built
    afresh with the values set for it, priced, read back and written as an
    SFF file, kept in the project's runs (engine/runs.py): the run, its
    `library.run` artifact and its SFF record. A basis already run answers
    from its row; values the plant refuses are kept as a receipt and
    answered 422 in the plant's words."""
    _library_plant(plant)
    try:
        return _runs.run(plant, request.configuration, request.overrides, by=request.by)
    except _library.LibraryRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not run {plant}: {e}") from e


@app.get("/api/runs")
def runs_list() -> list[EngineRun]:
    """The project's engine runs, newest first."""
    return _runs.listed()


@app.get("/api/runs/{run_id}")
def runs_report(run_id: str) -> RunReport:
    """One engine run with its artifact and its SFF record."""
    try:
        return _runs.report(run_id)
    except _runs.RunNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


# ── studies (stage 5; studies/) ─────────────────────────────────────────


@app.get("/api/studies/scenarios")
def study_scenarios() -> list[StudyScenario]:
    """The project's study scenarios, newest first."""
    return _scenarios.listed()


@app.post("/api/studies/scenarios")
def study_scenario_make(asked: ScenarioCreate) -> StudyScenario:
    """A scenario on a library plant or an openFerment flowsheet, checked
    against the plant's parameters and kept; each value a person's
    assumption or a model's estimate (ADR-006)."""
    try:
        return _scenarios.make(asked)
    except _scenarios.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not read {asked.plant}: {e}") from e


@app.get("/api/studies/scenarios/{scenario_id}")
def study_scenario(scenario_id: str) -> StudyScenario:
    try:
        return _scenarios.get(scenario_id)
    except _scenarios.ScenarioNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


@app.post("/api/studies/scenarios/{scenario_id}/run")
def study_scenario_run(scenario_id: str, asked: StudyRequest) -> RunReport:
    """The scenario run as an engine run (its report); values the plant
    refuses are kept as a receipt with the scenario and answered 422."""
    try:
        return _scenarios.run(scenario_id, by=asked.by)
    except _scenarios.ScenarioNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e
    except _library.LibraryRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not run {scenario_id}: {e}") from e


@app.get("/api/studies/comparisons")
def study_comparisons() -> list[StudyComparison]:
    """The project's comparisons, newest first."""
    return _comparisons.listed()


@app.post("/api/studies/comparisons")
def study_comparison_make(asked: ComparisonCreate) -> ComparisonReport:
    """Two or more engine runs set side by side, computed as one
    `study.comparison` artifact and kept with the title."""
    try:
        return _comparisons.make(asked)
    except _comparisons.ComparisonRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/studies/comparisons/{comparison_id}")
def study_comparison(comparison_id: str) -> ComparisonReport:
    try:
        return _comparisons.get(comparison_id)
    except _comparisons.ComparisonNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e


# A runbook is answered as it is kept (`exclude_unset`): the lock's digest
# reads a prediction's absent field and a null one differently.


@app.get("/api/studies/runbooks", response_model=list[Runbook], response_model_exclude_unset=True)
def study_runbooks() -> list[Runbook]:
    """The runbooks studies made, newest first."""
    try:
        return _runbooks.listed()
    except _runbooks.RunbookRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/studies/runbooks", response_model=Runbook, response_model_exclude_unset=True)
def study_runbook_make(asked: RunbookCreate) -> Runbook:
    """A runbook whose predictions are outputs of an engine run, in the
    run's units, with the measures the bench records at harvest; kept
    among the project's runbooks as a draft."""
    try:
        return _runbooks.make(asked)
    except _runbooks.RunbookRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/studies/runbooks/{runbook_id}", response_model=Runbook, response_model_exclude_unset=True)
def study_runbook(runbook_id: str) -> Runbook:
    try:
        return _runbooks.get(runbook_id)
    except _runbooks.RunbookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e
    except _runbooks.RunbookRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/studies/runbooks/{runbook_id}/lock", response_model=Runbook, response_model_exclude_unset=True)
def study_runbook_lock(runbook_id: str, asked: StudyRequest) -> Runbook:
    """The runbook's predictions and measures frozen under the digest the
    browser writes (src/engine/lock.ts), with the moment."""
    try:
        return _runbooks.lock(runbook_id, by=asked.by)
    except _runbooks.RunbookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\"")) from e
    except _runbooks.RunbookRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/studies/export", response_class=Response)
def study_export(by: str = "") -> Response:
    """The project's studies as one zip that opens without the service:
    study.json, study.md, each run's SFF file, versions.json and a manifest
    of each file's sha256 (studies/exports.py)."""
    try:
        data = _exports.package(by=by)
    except _exports.ExportRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{_exports.filename()}"'})


@app.get("/api/proforma/scenarios")
def proforma_scenarios(host: str | None = None) -> list[dict]:  # noqa: N803 (the wire name)
    """The project's BioSTEAM scenarios with their inputs bound to records
    (§8.3; OF-BLD-019 §2.3). A read: it starts no simulator."""
    from . import proforma

    return [s.model_dump(mode="json") for s in proforma.scenarios(host=host)]


@app.get("/api/proforma/bind")
def proforma_bind(flowsheet: str, host: str | None = None,  # noqa: N803
                  fits: str | None = None, overrides: str | None = None, vessel: str | None = None,
                  trainRun: str | None = None) -> dict:  # noqa: N803 (the wire name)
    """A shelf flowsheet's inputs bound, as a scenario not yet saved to the
    project shows them (OF-BLD-019 §2.3, D6), id and name empty; `?fits=`
    lays on the fermOS fits a person chose (§5.1), a JSON object of input
    key to artifact id, and `?overrides=` a person's overrides of one
    scenario's scope over both (OF-BLD-020 D3), a JSON list. A flowsheet
    built from kept artifacts (`custom_train_v1`, OF-BLD-020 §6.1) names its
    vessel design and its train run (`?vessel=`, `?trainRun=`). A reference
    biorefinery, the toy, an unknown id, a fit that cannot feed its input,
    an override that cannot stand, or a composite's part that cannot
    (missing, another tool's, damaged, of another chemical set) is a 422 in
    words. A read:
    it starts no simulator."""
    from . import composite, proforma

    chosen = _fits_param(fits)
    typed = _overrides_param(overrides)
    try:
        # A composite's Finance group is its own (the run lays it on, the
        # panel resolves it); every other flowsheet takes no finance key, and
        # one sent is refused as the run refuses it (OF-BLD-020 §6.R, main-30).
        built = bool(proforma.runnable(flowsheet).builtFrom)
        inputs, _finance = composite.split_overrides(typed) if built else (typed, [])
        values, _ = proforma.named_values(None, inputs)
        if values:
            proforma._check_keys(proforma.runnable(flowsheet), values)
        return proforma.bind_flowsheet(flowsheet, host=host,
                                       assumptions=values, fits=chosen, vessel=vessel,
                                       train_run=trainRun).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/proforma/ceiling-check")
def proforma_ceiling_check(scenarioId: str, flowsheet: str | None = None, host: str | None = None,  # noqa: N803
                           fits: str | None = None,  # noqa: N803
                           assumptions: str | None = None, overrides: str | None = None) -> dict:
    """A scenario's fermenter yield read against the newest stored geneOS
    ceiling of each shelf model of its organism, on its flowsheet's sugar
    (OF-BLD-019 §5.2, D11): `CeilingCheck`. A scenario the project keeps by
    its id, one not yet saved by the flowsheet it names; `?fits=` and
    `?overrides=` (JSON; OF-BLD-020 D3) bind its yield as its page binds it,
    and `?assumptions=`, the older field, is read as overrides for one
    release. A yield above a ceiling is flagged, never clamped. A read: it
    keeps nothing, starts no worker and changes no binding or run. Refused
    in words (422) as the binding is."""
    from . import proforma

    chosen = _fits_param(fits)
    typed = _assumptions_param(assumptions)
    over = _overrides_param(overrides)
    try:
        return proforma.ceiling_check(scenarioId, flowsheet, host=host,
                                      assumptions=typed, fits=chosen, overrides=over).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/proforma/run")
def proforma_run(req: ProformaRunRequest) -> dict:
    """Run a scenario the project keeps by its id, or one not yet saved by
    the shelf flowsheet it names (OF-BLD-019 §2.3, d): 422 in words for any
    other case, and listing every input waiting for a source."""
    from . import proforma
    from .workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        return proforma.run(req).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator could not run the scenario: {e}") from e


@app.get("/api/proforma/runs")
def proforma_runs(scenarioId: str = "") -> dict:  # noqa: N803 (the wire name)
    """A scenario's newest run on this service (OF-BLD-019 §3.R): the newest
    stored `proforma.run` whose basis names the scenario (`latest_run`, the
    one pureOS and selling_price read), or none. A read: it runs nothing and
    starts no simulator. The scenario is named by id, and a link opens what
    it names."""
    from . import proforma

    sid = scenarioId.strip()
    if not sid:
        raise HTTPException(status_code=422, detail="a read of a scenario's runs names the scenario it belongs to")
    art = proforma.latest_run(sid)
    return {"scenarioId": sid, "artifact": art.model_dump(mode="json") if art else None}


# ── one parameter panel (OF-BLD-020 §2.1, D2–D4) ────────────────────────


@app.get("/api/params/{scope:path}")
def params_scope(scope: str, flowsheet: str | None = None, host: str | None = None, fits: str | None = None,
                 vesselType: str | None = None, strain: str | None = None, product: str | None = None,  # noqa: N803
                 sugar: str | None = None, fit: str | None = None, startFrom: str | None = None,  # noqa: N803
                 durationPreset: str | None = None,  # noqa: N803 (the wire name)
                 unitType: str | None = None, train: str | None = None,  # noqa: N803 (the wire name)
                 vessel: str | None = None, trainRun: str | None = None) -> dict:  # noqa: N803 (the wire name)
    """A scope's parameters (`ParamScope`): every spec with its bounds and
    their reason, and its value as the service binds it now, with its
    source. `proforma:<scenario id>` is a scenario the project keeps, or
    with `?flowsheet=` one not yet saved; `?host=` and `?fits=` (JSON)
    bind as `/api/proforma/bind` does. Binding only: it starts no worker,
    integrates nothing and keeps nothing. `fermos:vessel:<id>` (with
    `?vesselType=`) reads its class's defaults through the Proforma worker,
    which a read starts when it is cold (OF-BLD-020 §4.1). `fermos:family:<id>`
    binds as GET /api/fermos/bind does, from `?strain=`, `?product=`,
    `?sugar=`, `?fit=`, `?startFrom=` and `?durationPreset=` (OF-BLD-020
    §3.2). `pureos:unit:<train>:<unit>` takes
    the unit's catalogue type as `?unitType=` and reads its class's defaults
    through the Proforma worker as the vessel's do (§5.1); with no type it is
    a 404 in words. With `?train=` (the whole TrainSpec, JSON, §5.2) the unit is
    the train's own, its per-component keys expanded over the train's
    chemicals and its records bound from the evidence pool by each parameter's field, and
    `pureos:unit:<train>:inlet` is the train's inlet. A `proforma:` scope on
    `custom_train_v1` names its vessel design and train run (`?vessel=`,
    `?trainRun=`; OF-BLD-020 §6.1) and serves the group Finance, read from
    the installed package with no worker. 404 for a scope no provider here
    knows; 422 in words for a malformed one or a refused binding; 409 for an
    artifact the scope names that is damaged on disk, as the vessel's own route
    answers it (§2.R, finding 17); 503 when the worker cannot answer."""
    from . import artifacts, params

    if vesselType not in (None, "stirred-tank", "bubble-column"):
        raise HTTPException(status_code=422, detail=f"a vessel type is stirred-tank or bubble-column; {vesselType!r} is neither")
    if durationPreset not in (None, "until-sugar-runs-out", "fit-length"):
        raise HTTPException(status_code=422, detail=f"a run-length preset is until-sugar-runs-out or fit-length; "
                                                    f"{durationPreset!r} is neither")
    req = ParamResolveRequest(flowsheet=flowsheet, host=host, fits=_fits_param(fits), vesselType=vesselType,
                              strain=strain, product=product, sugar=sugar, fit=fit, startFrom=startFrom,
                              durationPreset=durationPreset, unitType=unitType,
                              train=_train_param(train), vessel=vessel, trainRun=trainRun)
    try:
        return params.scope(scope, req).model_dump(mode="json")
    except params.ScopeUnknown as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except params.ParamRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not answer: {e}") from e


@app.post("/api/params/{scope:path}/resolve")
def params_resolve(scope: str, req: ParamResolveRequest) -> dict:
    """A person's overrides laid on a scope's values (`ParamResolveResult`):
    each override an `assumption` by the person it names, the basis inputs
    the overrides would add to a run, and every value outside its bounds in
    words (kept, never clamped). The basis inputs are the ones a run of the
    scope writes for those overrides (§2.R). Runs nothing and keeps nothing:
    the service keeps no override (D3). 404, 422, 409 and 503 as the GET
    answers them; a `fermos:vessel:` scope may start the worker as the GET
    may."""
    from . import artifacts, params

    try:
        return params.resolve_scope(scope, req).model_dump(mode="json")
    except params.ScopeUnknown as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except params.ParamRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not answer: {e}") from e


# ── fermOS sizes the vessel on BioSTEAM (OF-BLD-020 §4.1, D7) ──────────


@app.get("/api/fermos/vessel/specs")
def fermos_vessel_specs(simulation: str | None = None, fit: str | None = None,
                        vesselType: str | None = None) -> dict:  # noqa: N803 (the wire name)
    """The vessel scope `fermos:vessel:<simulation or fit id>` (a
    `ParamScope`): every design parameter of Appendix 2 §C with its bounds
    and their reason, and its value with its source: BioSTEAM's own default
    for the class, read in the worker (which this starts when it is cold), the
    simulation's harvest hour and oxygen uptake, or waiting for a named person
    (plant scale or batch volume). 404 for an artifact not on file; 422 in
    words for one no vessel is designed for; 503 when the worker cannot
    answer."""
    from . import artifacts, vessel

    named = [x for x in (simulation, fit) if x]
    if len(named) != 1:
        raise HTTPException(status_code=422, detail="name one simulation (?simulation=) or one fit (?fit=)")
    if vesselType not in (None, "stirred-tank", "bubble-column"):
        raise HTTPException(status_code=422, detail=f"a vessel type is stirred-tank or bubble-column; {vesselType!r} is neither")
    from . import params

    try:
        return vessel.scope(named[0], vesselType).model_dump(mode="json")
    except params.ScopeUnknown as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except params.ParamRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not answer: {e}") from e


@app.post("/api/fermos/vessel", response_model=VesselDesign)
def fermos_vessel(req: VesselRequest) -> VesselDesign:
    """Design the vessel a simulation (or, anaerobic only, a fit) needs, in
    the Proforma worker on BioSTEAM: one `fermos.vessel` artifact, computed
    or returned as kept for the same basis. 422 in words for a design that
    cannot be made as asked (no plant scale and no batch volume, a fit asked
    for an aerobic design, an artifact not on file, an override that cannot
    stand, BioSTEAM's own refusal); 409 for a file damaged on disk; 503 when
    the worker cannot answer."""
    from . import artifacts, vessel

    try:
        return vessel.design(req)
    except (vessel.VesselRefused, vessel.VesselNotFound) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not answer: {e}") from e


@app.get("/api/fermos/vessels")
def fermos_vessels() -> list[dict]:
    """Every kept vessel design, newest first (`VesselSummary`): a read,
    which starts no simulator."""
    from . import vessel

    return [v.model_dump(mode="json") for v in vessel.designs()]


# ── thermosteam answers property questions (OF-BLD-019 §4.2, D9) ───────


def _thermo_answer(fn, req: ThermoPropsRequest):
    from . import artifacts, evidence_pool, thermo

    try:
        # A person names the run or the record by id. Only a record needs the
        # pool.
        kind, _ = thermo.question(req)
        return fn(req, pool=evidence_pool.load() if kind == thermo.BEER else None)
    except thermo.ThermoNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except thermo.ThermoRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except artifacts.ArtifactDamaged as e:  # the run's file or the answer's (§4.R): in words, as artifacts_read says it
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.post("/api/thermo/props", response_model=Artifact)
def thermo_props(req: ThermoPropsRequest) -> Artifact:
    """thermosteam's density, heat capacity, viscosity and bubble and dew
    points for a run's stream, or a preset: one `thermo_props` artifact,
    computed in the Proforma worker or returned as stored. 404 for a run,
    stream or record not on file; 409 for a run or an answer whose file is
    damaged on disk; 422 for a question that cannot be asked, a chemical the
    library lacks among them, in words; 503 when the worker cannot answer."""
    from . import thermo
    from .workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        return _thermo_answer(thermo.props, req)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where thermosteam runs, could not answer: {e}") from e


@app.get("/api/thermo/props")
def thermo_props_stored(artifactId: str | None = None, streamId: str | None = None,  # noqa: N803 (the wire names)
                        preset: str | None = None, recordId: str | None = None) -> dict:
    """The answer stored for the same question, as `{"artifact": …}`, or
    `{"artifact": null}` when it has not been asked here: a read, which
    starts no simulator. The same 404, 409 and 422 as the POST."""
    from . import thermo

    art = _thermo_answer(thermo.stored, ThermoPropsRequest(artifactId=artifactId, streamId=streamId, preset=preset,
                                                           recordId=recordId))
    return {"artifact": art.model_dump(mode="json") if art else None}


# ── a product's properties (OF-BLD-020 §7.1, D12) ──────────────────────
#
# What pureOS's proposer reads: ProtParam on a product entry's own sequence
# (protparam.py) and its volatility by thermosteam (thermo.py). A request names
# the product by id and nothing else. Imported here so each tool is registered
# when the service starts, and a kept answer replays on a service just started.

from . import protparam as _protparam  # noqa: E402,F401
from .models import ProductPropertyRequest  # noqa: E402


def _protparam_answer(fn, product: str):
    from . import artifacts, protparam

    try:
        return fn(product)
    except protparam.ProtParamMissing as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except protparam.ProtParamRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.post("/api/protparam", response_model=Artifact)
def protparam_compute(req: ProductPropertyRequest) -> Artifact:
    """Biopython's ProtParam on a product entry's own sequence: its molecular
    weight, isoelectric point, extinction coefficients and GRAVY, one
    `protparam` artifact computed here or returned as stored. 404 for a
    product with no sequence (the words say the entry carries none) or no
    such product; 422 for a sequence ProtParam cannot read, in words naming
    each letter and its positions; 409 for an answer damaged on disk."""
    from . import protparam

    return _protparam_answer(protparam.of_product, req.product)


@app.get("/api/protparam")
def protparam_stored(product: str = "") -> dict:
    """The answer stored for the product's sequence, as `{"artifact": …}`, or
    `{"artifact": null}` when it has not been computed here: a read, which
    computes nothing. The same 404, 409 and 422 as the POST."""
    from . import protparam

    art = _protparam_answer(protparam.stored, product)
    return {"artifact": art.model_dump(mode="json") if art else None}


def _volatility_answer(fn, product: str):
    from . import artifacts, thermo

    try:
        return fn(product)
    except thermo.ThermoNotFound as e:  # VolatilityMissing: the product names no chemical of the library
        raise HTTPException(status_code=404, detail=str(e)) from None
    except thermo.ThermoRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.post("/api/thermo/volatility", response_model=Artifact)
def thermo_volatility(req: ProductPropertyRequest) -> Artifact:
    """A product's volatility by thermosteam: its chemical's and water's
    normal boiling points, and whether the library's own vapour-liquid
    equilibrium gives the pair a minimum-boiling azeotrope, one `volatility`
    artifact computed in the Proforma worker or returned as stored. 404 for a
    product that names no chemical of the library here; 422 for a chemical
    the library lacks, in words naming it; 409 for an answer damaged on disk;
    503 when the worker cannot answer."""
    from . import thermo
    from .workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        return _volatility_answer(thermo.volatility, req.product)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where thermosteam runs, could not answer: {e}") from e


@app.get("/api/thermo/volatility")
def thermo_volatility_stored(product: str = "") -> dict:
    """The volatility stored for the product, as `{"artifact": …}`, or
    `{"artifact": null}`: a read, which starts no simulator. The same 404,
    409 and 422 as the POST."""
    from . import thermo

    art = _volatility_answer(thermo.stored_volatility, product)
    return {"artifact": art.model_dump(mode="json") if art else None}


def _warm_proforma() -> None:
    from . import proforma

    if proforma.warm_on_start():
        proforma.start(background=True)


_warm_proforma()


# ── Intake (OF-BLD-012 §5.2) ────────────────────────────────────────────


@app.post("/api/intake/{paper_id}/extract", response_model=ExtractResponse)
def intake_extract(paper_id: str, force: bool = False) -> ExtractResponse:
    """One structured model response over a document's passages in the kit
    (§6.1, §6.3; ADR-002). `paper_id` is the kit's document id.

    422 when the project holds no such document — there is nothing to anchor
    to. 503 when there is no key or the API cannot be reached; the detail says
    which.
    """
    try:
        result = extract.extract_paper(paper_id, force=force)
    except extract.NothingToAnchor as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except extract.ExtractTruncated as e:
        # Not cached, so the next attempt is a real one; 502 because the
        # upstream answered and the answer was unusable.
        raise HTTPException(status_code=502, detail=str(e)) from e
    except extract.ExtractUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    log.info(
        "extract: %s → %d anchored, %d rejected, $%.4f",
        paper_id, len(result.candidates), result.rejected, result.usage.costUsd,
    )
    return result


# ── the literature layer: collection into Sci RAG Kit (ADR-002) ─────────

# The kit generates through llm.py: its answers, HyDE's passages and a
# document's graph are model calls like any other, under the day's cap.
kit.install_model(llm.kit_client)

#: The largest file Intake takes, in bytes.
MAX_UPLOAD = 50 * 1024 * 1024


def _collected(outcome: CollectOutcome) -> CollectOutcome:
    log.info(
        "intake: %s %s → %s%s", outcome.collector, outcome.identifier, outcome.status,
        f" ({outcome.reason})" if outcome.reason else "",
    )
    return outcome


@app.post("/api/intake/collect", response_model=CollectOutcome)
def intake_collect(request: CollectRequest) -> CollectOutcome:
    """A paper, a report or a strain entry by its identifier, fetched by the
    collector that serves it, stored in the kit and linked to the project.

    Not collected is HTTP 200 with `status: failed` and the reason: the
    Intake board renders it, and a 5xx would render as nothing."""
    return _collected(intake.collect(request.identifier, project_id=projects.current(), by=request.by,
                                     reason=request.reason))


@app.post("/api/intake/upload", response_model=CollectOutcome)
def intake_upload(
    file: UploadFile = File(...),
    by: str = Form(..., min_length=1, max_length=200),
    title: str = Form("", max_length=500),
    licenceClass: str = Form("unknown", max_length=40),
    licence: str = Form("", max_length=2000),
    reason: str = Form("", max_length=2000),
) -> CollectOutcome:
    """A file a person uploads (PDF, JATS XML, Markdown, HTML or text),
    stored in the kit and linked to the project. 413 past MAX_UPLOAD."""
    project_id = projects.current()
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail=f"{file.filename} is larger than {MAX_UPLOAD // (1024 * 1024)} MB")
    return _collected(intake.upload(file.filename or "", data, project_id=project_id, by=by, title=title,
                                    licence_class=licenceClass, licence=licence, reason=reason))


@app.post("/api/intake/paste", response_model=CollectOutcome)
def intake_paste(request: PasteRequest) -> CollectOutcome:
    """Text a person pastes, under its title, stored in the kit and linked to the project."""
    return _collected(intake.paste(request.title, request.text, project_id=projects.current(), by=request.by,
                                   url=request.url, licence_class=request.licenceClass, licence=request.licence,
                                   reason=request.reason))


@app.get("/api/literature/documents", response_model=list[LiteratureDocument])
def literature_documents() -> list[LiteratureDocument]:
    """Every document the project holds, newest first, with the selection
    that brought each in."""
    return [
        LiteratureDocument(
            documentId=d.id, title=d.title, authors=list(d.authors or []), year=d.publication_year, doi=d.doi,
            journal=d.journal, citation=d.formatted_citation, source=d.source, sourceRef=d.source_ref,
            licenceClass=d.license_class, chunks=d.chunk_count, collector=(link["selection"] or {}).get("collector"),
            selection=link["selection"] or {}, linkedBy=link["created_by"], linkedAt=link["created_at"].isoformat(),
        )
        for d, link in kit.documents(projects.current())
    ]


@app.get("/api/literature/stats")
def literature_stats() -> dict[str, Any]:
    """The project's documents and chunks in the kit, by source, licence class
    and embedding version; the concept graph's size is the instance's."""
    return kit.stats(projects.current())


@app.get("/api/literature/search", response_model=SearchResponse)
def literature_search(q: str, topK: int = 10, profile: str = "interactive") -> SearchResponse:
    """The passages of the project's documents that best answer `q`, best
    first, each with its document, passage id and citation. 'interactive'
    (vector and keyword) asks no model; 'deep' adds the graph and HyDE."""
    if not q.strip():
        raise HTTPException(status_code=422, detail="a search needs words")
    if profile not in ("interactive", "deep"):
        raise HTTPException(status_code=422, detail="profile is interactive or deep")
    hits, result = kit.search(q, project_id=projects.current(), top_k=max(1, min(topK, 50)), profile=profile)
    return SearchResponse(
        query=q, profile=result.profile, degradedStages=result.degraded_stages,
        hits=[SearchHit(
            documentId=h.document_id, passageId=h.passage_id, title=h.title, text=h.text, sectionPath=h.section_path,
            citation=h.citation, licenceClass=h.licence_class, year=h.year, score=h.score, layers=list(h.layers),
            isTable=h.is_table,
        ) for h in hits],
    )


@app.post("/api/literature/answer")
def literature_answer(request: LiteratureQuestion) -> StreamingResponse:
    """A cited answer over the project's documents, as server-sent events:
    `delta` (text), `citations` (every source with its passage id and whether
    the answer cited it), `done`, or `error`. One model call through llm.py,
    under the day's cap; with no key the stream says so in an `error`."""
    project_id = projects.current()

    def events():
        for event in kit.answer(request.question, project_id=project_id, top_k=request.topK):
            kind = event.pop("type")
            yield _sse(kind, event)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class _KitREST:
    """The kit's REST app at /rag (ADR-002), built on its first request and
    again whenever the kit is pointed at another database, so it always
    serves the engine the kit holds now."""

    def __init__(self) -> None:
        self._built: tuple[int, Any] | None = None

    async def __call__(self, scope, receive, send) -> None:
        generation = kit.generation()
        if self._built is None or self._built[0] != generation:
            self._built = (generation, kit.rest_app())
        await self._built[1](scope, receive, send)


app.mount("/rag", _KitREST(), name="rag")


# ── the overlay (OF-BLD-012 §2.1) ───────────────────────────────────────


@app.get("/api/biorepo/overlay", response_model=Overlay)
def biorepo_overlay() -> Overlay:
    """What the service knows of the project's literature.

    Papers are the documents the project holds in the kit, with their
    passages (ADR-002); the run and the new candidates are recomputed from
    the project's candidates against the values its reviewers typed (§6.2,
    `witness.reviewed_records`); the decisions come from the project's
    decision rows (§7.2). The store applies whatever is here in one action at
    load, and nothing here changes a record's status — that path goes
    through `biorepo.write` alone.
    """
    runs, candidates, decisions = witness.overlay_bundle()
    # Always the FULL lists, never None (OF-BLD-012.1 F3): an empty list here
    # means the extractor has produced nothing, and the store drops what it
    # was holding. None is reserved for a caller that supplies neither, and
    # nothing in this service is such a caller.
    return Overlay(papers=intake.overlay_papers(projects.current()), records=decisions, candidates=candidates, runs=runs)


@app.post("/api/biorepo/decisions", response_model=ReviewDecision)
def biorepo_decisions(decision: ReviewDecision) -> ReviewDecision:
    """The one way a decision reaches the project's decisions (§2.3, §7.2): through
    `biorepo.write`, which stores it or refuses it with the rule that failed.
    422 carries the rule and the reason; nothing is repaired on the way."""
    try:
        return biorepo.write(decision)
    except biorepo.WriteRefused as e:
        log.warning("biorepo refused %s — %s", decision.recordId, e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/biorepo/check", response_model=DecisionCheck)
def biorepo_check(decision: ReviewDecision) -> DecisionCheck:
    """Would `biorepo.write` keep this decision? (OF-BLD-012.1 F1.5)

    Every rule of §2.3 runs; nothing is written. A refusal is an ANSWER, not
    an error, so it comes back 200 with the rule and the reason — the browser
    is asking a question, and a 422 here would read as a failed decision in
    the console of a reviewer who has not decided anything yet.
    """
    try:
        biorepo.write(decision, dry_run=True)
        return DecisionCheck(ok=True)
    except biorepo.WriteRefused as e:
        return DecisionCheck(ok=False, rule=e.rule, why=e.why)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── Guild (OF-BLD-013 §1.2) ──────────────────────────────────────────────
#
# The competence ledger. Reads are open like every read here; each write goes
# through one function in guild.py, which stores it or refuses it with the
# rule that failed. 422 carries the rule and the reason, the same shape
# /api/biorepo/decisions uses, and /api/guild/check answers 200 either way.


def _refused(e: guild.GuildRefused, what: str) -> HTTPException:
    log.warning("guild refused %s — %s", what, e)
    return HTTPException(status_code=422, detail=str(e))


@app.get("/api/guild", response_model=Guild)
def guild_ledger() -> Guild:
    """The whole ledger: people and every entry, withdrawn ones included.
    The browser applies it at load the way it applies the overlay, and
    computes every level from it."""
    return guild.read()


@app.post("/api/guild/people", response_model=GuildPerson)
def guild_people(person: GuildPerson) -> GuildPerson:
    try:
        return guild.write_person(person)
    except guild.GuildRefused as e:
        raise _refused(e, person.id) from e


@app.post("/api/guild/evidence", response_model=GuildEvidence)
def guild_evidence(entry: GuildEvidence) -> GuildEvidence:
    try:
        return guild.write_evidence(entry)
    except guild.GuildRefused as e:
        raise _refused(e, entry.id) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/guild/check", response_model=DecisionCheck)
def guild_check(entry: GuildEvidence) -> DecisionCheck:
    """Would `guild.write_evidence` keep this entry? Every rule runs and
    nothing is written. A refusal is an answer, so it comes back 200."""
    try:
        guild.write_evidence(entry, dry_run=True)
        return DecisionCheck(ok=True)
    except guild.GuildRefused as e:
        return DecisionCheck(ok=False, rule=e.rule, why=e.why)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/guild/policy", response_model=GuildPolicy)
def guild_policy(policy: GuildPolicy) -> GuildPolicy:
    try:
        return guild.write_policy(policy)
    except guild.GuildRefused as e:
        raise _refused(e, "policy") from e


@app.post("/api/guild/withdraw", response_model=GuildEvidence)
def guild_withdraw(request: GuildWithdrawal) -> GuildEvidence:
    try:
        return guild.withdraw(request)
    except guild.GuildRefused as e:
        raise _refused(e, request.evidenceId) from e


# ── Checks (OF-BLD-013 §5.2) ────────────────────────────────────────────
#
# Proposed by fixed rules, asked for, scheduled, dismissed and run, each
# through one function in checks.py; a run writes witnessed entries through
# guild.write_evidence. 422 carries the rule and the reason.


class CheckProposeRequest(BaseModel):
    by: str


def _check_refused(e: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(e))


@app.get("/api/guild/checks", response_model=Checks)
def checks_read() -> Checks:
    return checks.read()


@app.post("/api/guild/checks/propose", response_model=list[Check])
def checks_propose(request: CheckProposeRequest) -> list[Check]:
    try:
        return checks.propose(request.by)
    except checks.CheckRefused as e:
        raise _check_refused(e) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/guild/checks/request", response_model=Check)
def checks_request(request: CheckRequest) -> Check:
    try:
        return checks.request(request)
    except checks.CheckRefused as e:
        raise _check_refused(e) from e


@app.post("/api/guild/checks/{check_id}/schedule", response_model=Check)
def checks_schedule(check_id: str, request: CheckSchedule) -> Check:
    try:
        return checks.schedule(check_id, request)
    except checks.CheckRefused as e:
        raise _check_refused(e) from e


@app.post("/api/guild/checks/{check_id}/dismiss", response_model=Check)
def checks_dismiss(check_id: str, request: CheckDismiss) -> Check:
    try:
        return checks.dismiss(check_id, request)
    except checks.CheckRefused as e:
        raise _check_refused(e) from e


@app.post("/api/guild/checks/{check_id}/record", response_model=Check)
def checks_record(check_id: str, request: CheckRecord) -> Check:
    try:
        return checks.record(check_id, request)
    except (checks.CheckRefused, guild.GuildRefused) as e:
        raise _check_refused(e) from e


class BriefRequest(BaseModel):
    by: str


@app.post("/api/guild/checks/{check_id}/brief", response_model=Check)
def checks_brief(check_id: str, request: BriefRequest) -> Check:
    """One model call: what the assessor should watch, kept on the check."""
    try:
        return checks.brief(check_id, request.by)
    except checks.CheckRefused as e:
        raise _check_refused(e) from e
    except checks.BriefUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── Practice (OF-BLD-013 §4) ────────────────────────────────────────────
#
# Scenarios drafted by the model and checked by practice.py, which copies
# every value from the source a draft cites and refuses a draft that states a
# number of its own. 422 carries the rule and the reason, as Guild's do; 503
# means no key, no network, or every model declined.


@app.get("/api/practice", response_model=Practice)
def practice_read() -> Practice:
    return practice.read()


@app.post("/api/practice/draft", response_model=PracticeScenario)
def practice_draft(request: PracticeDraftRequest) -> PracticeScenario:  # noqa: N803 (the wire name)
    """A scenario for one skill."""
    try:
        return practice.draft(request)
    except practice.PracticeRefused as e:
        log.warning("practice refused a draft for %s — %s: %s ($%.4f spent)", request.skillId, e.rule, e.detail, e.usage.costUsd)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except practice.PracticeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/practice/turn", response_model=PracticeSession)
def practice_turn(request: PracticeTurnRequest) -> PracticeSession:
    """The trainee's answer and the tutor's reply, kept together or not at all.
    The session that closes for a person on the ledger puts practice on it."""
    try:
        return practice.turn(request)
    except practice.PracticeRefused as e:
        log.warning("practice refused a turn on %s — %s: %s ($%.4f spent)", request.scenarioId, e.rule, e.detail, e.usage.costUsd)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except practice.PracticeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


class PracticeRecordRequest(BaseModel):
    sessionId: str


@app.post("/api/practice/record", response_model=PracticeSession)
def practice_record(request: PracticeRecordRequest) -> PracticeSession:
    """Ask the ledger again for a closed session it has no entry for."""
    try:
        return practice.record(request.sessionId)
    except practice.PracticeRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# ── Witness (OF-BLD-012 §6.3) ────────────────────────────────────────────


@app.get("/api/witness/runs", response_model=list[ExtractRun])
def witness_runs() -> list[ExtractRun]:
    """RunOutput[] recomputed from the project's candidates against the values
    its reviewers typed. Empty until something has been extracted."""
    return witness.runs()


# ── Artifacts (OF-BLD-014 §3.2, E.5) ─────────────────────────────────────


@app.get("/api/biorepo/artifacts", response_model=list[Artifact])
def artifacts_list() -> list[Artifact]:  # noqa: N803 (the wire name)
    """Every value this service computed and kept, newest first."""
    return artifacts.all_artifacts()


@app.get("/api/biorepo/artifacts/{artifact_id}", response_model=Artifact)
def artifacts_read(artifact_id: str) -> Artifact:
    try:
        return artifacts.get(artifact_id)
    except artifacts.ArtifactNotFound:
        raise HTTPException(status_code=404, detail=f"no artifact {artifact_id!r}") from None
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.post("/api/biorepo/artifacts/{artifact_id}/replay", response_model=ReplayResult)
def artifacts_replay(artifact_id: str) -> ReplayResult:
    """Recompute and compare. 404 for an unknown id; 409 when the tool that
    made it is not registered in this service, which cannot replay it."""
    try:
        return artifacts.replay(artifact_id)
    except artifacts.ArtifactNotFound:
        raise HTTPException(status_code=404, detail=f"no artifact {artifact_id!r}") from None
    except (artifacts.ToolNotRegistered, artifacts.ArtifactDamaged) as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


# ── pureOS reads the train (OF-BLD-019 §4.1, D1) ────────────────────────


@app.get("/api/pureos/trains")
def pureos_trains() -> list[dict]:  # noqa: N803 (the wire name)
    """The trains on file: the newest Proforma run of each scenario, read
    unit by unit from its stream table, with its overall recovery. A read: it
    starts no simulator."""
    from . import pureos

    return [pureos.summary(t).model_dump(mode="json")
            for t in pureos.trains()]


@app.get("/api/pureos/train-runs")
def pureos_train_runs() -> list[dict]:  # noqa: N803 (the wire name)
    """Every kept pureOS train run (`TrainSummary`), newest first (OF-BLD-020
    §5.2). A read: it starts no simulator."""
    from . import pureos

    return [s.model_dump(mode="json") for s in pureos.train_runs()]


@app.get("/api/pureos/trains-kept")
def pureos_trains_kept() -> list[dict]:  # noqa: N803 (the wire name)
    """The trains a model built with `pureos_build` or `pureos_write`
    (`KeptTrain`: the train as data, `madeBy` the model, `at` and
    `updatedAt`), the most recently changed first (OF-BLD-020 §5.4). A
    person's trains are the project's rows (`GET /api/state`). A read: it
    writes nothing and starts no simulator."""
    from .pureos import kept

    return [k.model_dump(mode="json") for k in kept.listed()]


@app.post("/api/pureos/train/validate")
def pureos_train_validate(train: TrainSpec) -> dict:
    """Every refusal of a train at once, in words (`TrainValidation`): a type
    not in the catalogue, an outlet its type does not have, a recycle that is
    not to an earlier unit, a key its unit does not declare, no unit, two
    outlets on, a duplicate id. Runs nothing (OF-BLD-020 §5.2, D9)."""
    from . import pureos

    return pureos.validation(train).model_dump(mode="json")


@app.post("/api/pureos/train/check")
def pureos_train_check(req: TrainRunRequest) -> dict:
    """Everything a run of the train would refuse, at once, in the run's
    words, each by the place it belongs to (`TrainValidation`: a unit's id,
    `inlet`, or `train`): the validation's refusals, a value that waits naming
    what would bind it, a unit's needs (OF-BLD-020 §5.3). Runs no train and
    keeps nothing; it reads what the scopes read (the program's chemicals,
    each class's defaults), which a cold worker starts for. 409 for an
    artifact the train names that is damaged on disk; 503 when the worker
    cannot answer."""
    from . import artifacts, pureos

    try:
        return pureos.check_train(req.train, req.overrides, req.by).model_dump(mode="json")
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not read "
                                                    f"the train's units: {e}") from e


@app.post("/api/pureos/train/from-run")
def pureos_train_from_run(req: TrainFromRunRequest) -> dict:
    """A kept run's units read into a train (`TrainFromRun`, OF-BLD-020
    §5.3): every unit on the product's path whose class is a catalogue
    type, in run order, its outlets routed as the run routed them, its values
    read from the package's own unit when the run is of a shelf flowsheet;
    the units it does not take and why; the train's structural refusals.
    Keeps nothing and starts no simulator. 404 for an artifact not on file;
    422 in words for one that is no run or that no train is read from; 409
    for one damaged on disk."""
    from . import artifacts, pureos

    try:
        return pureos.from_run(req.artifactId, req.trainId).model_dump(mode="json")
    except pureos.RunNotOnFile as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except pureos.TrainRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@app.post("/api/pureos/train/run")
def pureos_train_run(req: TrainRunRequest) -> dict:
    """Run a train (`TrainRun`): every value resolved with its source, the
    train built and run in the Proforma worker, one `pureos.train_run`
    artifact kept (or the one kept for the same basis returned). 422 in words
    for every refusal (the validation's, a value that waits naming what would
    bind it, a unit's needs, a unit that does not converge, with BioSTEAM's
    words); 409 for an artifact the train names that is damaged on disk; 503
    when the worker cannot answer (OF-BLD-020 §5.2)."""
    from . import artifacts, pureos

    try:
        return pureos.run_train(req.train, req.overrides, req.by).model_dump(mode="json")
    except pureos.TrainRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not run the "
                                                    f"train: {e}") from e


@app.get("/api/pureos/train/{key}")
def pureos_train(key: str) -> dict:
    """One train: the newest run of the scenario `key` names, the newest run
    of the pureOS train it names (OF-BLD-020 §5.2), or the run whose artifact
    id it is. 404 says how a run gets there; a deep link opens what it
    names."""
    from . import pureos

    try:
        return pureos.train(key).model_dump(mode="json")
    except pureos.TrainNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


# ── pureOS proposes a train (OF-BLD-020 §7.2, D12) ──────────────────────

@app.post("/api/pureos/propose")
def pureos_propose(req: ProposeRequest) -> dict:
    """A train proposed by written rules (`TrainProposal`): the product's
    class and the properties its rule splits on (thermosteam's volatility,
    ProtParam on the catalogue entry's sequence, where the product is a
    protein), each unit at its library defaults or waiting, with one reason
    naming the rule, the property and its artifact; or none, naming what is
    missing. Keeps nothing but the property artifacts it reads. 404 for a
    product neither the products catalogue nor thermo.CHEMICALS holds; 422 in
    words for a refusal (an unknown host, an inlet that is not one, a sequence
    ProtParam cannot read, a chemical the library lacks); 409 for a property
    answer damaged on disk; 503 when the worker cannot answer a volatility
    question."""
    from . import artifacts, pureos

    try:
        return pureos.propose(req.product, req.host, req.inletRef).model_dump(mode="json")
    except pureos.ProposeUnknown as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except pureos.ProposeRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except artifacts.ArtifactDamaged as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where thermosteam runs, could not answer "
                                                    f"the volatility question: {e}") from e


# ── pureOS's unit catalogue (OF-BLD-020 §5.1, D8) ──────────────────────


@app.get("/api/pureos/catalogue")
def pureos_catalogue() -> list[dict]:
    """Every unit type a train can hold (`UnitType`), in stage order: its
    BioSTEAM or in-house class, what each inlet and outlet is, whether
    BioSTEAM costs it, what it needs set, what it does not offer and why.
    From the catalogue's data alone: it starts no simulator."""
    from .pureos import catalogue

    return [u.model_dump(mode="json") for u in catalogue.listing()]


@app.get("/api/pureos/catalogue/{type_id}/specs")
def pureos_catalogue_specs(type_id: str) -> dict:
    """One unit type's parameters (`UnitSpecs`): every ParameterSpec with the
    choices and bounds its class gives, each default as the class gives it,
    read from its code in the Proforma worker (which this starts when it is
    cold, once per process and type), how each reaches the class, and what it
    does not offer. 404 for an id not in the catalogue; 503 in words when the
    worker cannot answer."""
    from .pureos import catalogue

    try:
        return catalogue.specs_of(type_id).model_dump(mode="json")
    except catalogue.CatalogueUnknown as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        raise HTTPException(status_code=503, detail=f"the Proforma simulator, where BioSTEAM runs, could not read "
                                                    f"{type_id}'s class: {e}") from e


# ── Tools (OF-BLD-014 §3.4, E.6) ─────────────────────────────────────────


@app.get("/api/tools", response_model=list[ToolInfo])
def tools_list() -> list[ToolInfo]:
    """Each tool's name, description and input schema."""
    return tools.infos()


# ── Proposals and the audit log (OF-BLD-015 §7.3, §7.4) ────────────────


@app.get("/api/proposals", response_model=list[Proposal])
def proposals_list(state: str | None = None) -> list[Proposal]:
    """Every proposal, or those in one state; Home shows the `proposed`."""
    from . import proposals

    # As a reader sees them: a Guild proposal without its words, since who a
    # check names is never shown before it is run (OF-BLD-016 §1.R).
    return proposals.listed(state)


@app.post("/api/proposals/{proposal_id}/carry-out", response_model=Proposal)
def proposals_carry_out(proposal_id: str, action: ProposalAction) -> Proposal:
    """A person presses the button: the server runs the action in their name
    where it can, and records that they took it otherwise."""
    from . import checks, extract, proposals

    try:
        return proposals.carry_out(proposal_id, action.person, action.actingId)
    except proposals.ProposalRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except checks.CheckRefused as e:
        raise HTTPException(status_code=422, detail=f"{e}") from e
    except (extract.ExtractUnavailable, extract.ExtractTruncated, llm.ModelUnavailable, llm.ModelRefused) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/proposals/{proposal_id}/dismiss", response_model=Proposal)
def proposals_dismiss(proposal_id: str, action: ProposalAction) -> Proposal:
    from . import proposals

    try:
        return proposals.dismiss(proposal_id, action.person, action.reason)
    except proposals.ProposalRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# ── Projects (alpha 2.0, ADR-005) ─────────────────────────────────────────


@app.get("/api/projects", response_model=list[Project])
def projects_list() -> list[Project]:
    """Every project, oldest first. Needs no project of its own."""
    return projects.listed()


@app.post("/api/projects", response_model=Project, status_code=201)
def projects_create(asked: ProjectCreate) -> Project:
    """Make a project; its id is made from the name unless one is given. A
    taken id is a 409 that says so."""
    try:
        return projects.create(asked)
    except projects.ProjectRefused as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@app.get("/api/projects/{project_id}", response_model=Project)
def projects_get(project_id: str) -> Project:
    found = projects.get(project_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"no project named {project_id!r}")
    return found


# ── What a project keeps of its pages (stage 2, project_state.py) ──────


class StateWrite(BaseModel):
    """PUT /api/state/{kind}/{id}: the row as the page keeps it, and who."""

    by: str = ""
    value: Any


@app.get("/api/state")
def state_load() -> dict[str, Any]:
    """Everything the project keeps of its pages, keyed as the page keeps it."""
    from . import project_state

    return project_state.load()


@app.put("/api/state/{kind}/{item_id}")
def state_put(kind: str, item_id: str, write: StateWrite) -> dict[str, Any]:
    from . import project_state

    try:
        return {"kind": kind, "id": item_id, "value": project_state.put(kind, item_id, write.value, write.by)}
    except project_state.StateRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.delete("/api/state/{kind}/{item_id}")
def state_remove(kind: str, item_id: str, by: str = "") -> dict[str, Any]:
    from . import project_state

    try:
        project_state.remove(kind, item_id, by)
    except project_state.StateRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"kind": kind, "id": item_id, "removed": True}


@app.get("/api/audit", response_model=list[AuditEntry])
def audit_read(limit: int = 200) -> list[AuditEntry]:
    """The newest rows of the project's audit log, newest last."""
    from . import audit

    return audit.read(max(1, min(limit, audit.MAX_READ)))


@app.post("/api/tools/{name}", response_model=ToolResult)
def tools_run(name: str, body: dict[str, Any], by: str = "") -> ToolResult:  # noqa: N803 (the wire name)
    """Run one tool through the registry, the same path Postdoc's loop and
    the MCP server take, in the request's project. A refusal is a result
    with `error` set; an unknown tool is a 404. The body is the tool's
    input; `?by=` names the person calling, who is the author of any
    quantity the input types (ADR-006) and of any study write it makes."""
    if name not in tools.REGISTRY:
        raise HTTPException(status_code=404, detail=f"no tool named {name!r}")
    return tools.run(name, body, tools.ToolContext(person=by.strip()[:200]))


# ── The built app (OF-BLD-012 §B.4) ──────────────────────────────────────

# One process, one port. When `pnpm build` has produced dist/, the service
# serves it at / beside /api, so the whole app is one address: the browser's
# relative /api calls land on this same process, and the Mac Mini daemon
# (scripts/host/) runs nothing else. With no dist/ (a fresh clone, the test
# suite, `pnpm dev` before a first build) nothing is mounted and the service
# answers /api alone, exactly as before.
#
# Mounted LAST, and that is load-bearing: Starlette tries routes in order and
# a mount at "/" matches every path, so each /api route above answers first.
# StaticFiles resolves every request and refuses one that leaves the
# directory, the same confinement scripts/lib/serve-dist.mjs gives the test
# servers (OF-BLD-012.1 §6.9). OPENFERMENT_DIST_DIR overrides the location; a
# relative value is taken from the repository root, like the data overrides.
DIST_DIR = intake._env_path("OPENFERMENT_DIST_DIR", Path(__file__).parent.parent.parent / "dist")


IMMUTABLE = "public, max-age=31536000, immutable"


class AppFiles(StaticFiles):
    """dist/, with caching that survives a deploy. A build names its scripts
    and styles by content hash under assets/ and deletes the old ones, so a
    browser holding last week's index.html would ask for files that are gone
    and show a blank page. The page and anything else outside assets/ is
    revalidated on every load; what is under assets/ never changes under its
    name and is kept for a year."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = IMMUTABLE if path.startswith("assets/") else "no-cache"
        return response


def mount_app(target: FastAPI, dist: Path) -> bool:
    """Serve `dist` at / on `target` when it holds a build. True if mounted."""
    if not (dist / "index.html").is_file():
        return False
    target.mount("/", AppFiles(directory=dist, html=True), name="app")
    return True


if mount_app(app, DIST_DIR):
    log.info("serving the built app from %s at /", DIST_DIR)
