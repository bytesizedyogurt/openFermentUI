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

import json
import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import artifacts, biorepo, checks, extract, fermos, geneos, guard, guild, intake, passages, postdoc_agent, practice, programs, rageval, retrieve, tools, witness
from .corpus import load_corpus
from .workers import WorkerCrashed, WorkerError, WorkerTimeout
from .models import (
    AuditEntry,
    Proposal,
    ProposalAction,
    AnswerPlan,
    Artifact,
    AskRequest,
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
    FetchResult,
    ForecastRequest,
    ParamResolveRequest,
    ProformaRunRequest,
    SimulationRequest,
    ThermoPropsRequest,
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
    IntakeStatus,
    Overlay,
    Practice,
    PracticeDraftRequest,
    PracticeScenario,
    PracticeSession,
    PracticeTurnRequest,
    RagReport,
    RagSearchRequest,
    RagSearchResponse,
    RagStatus,
    ReplayResult,
    ReviewDecision,
    ToolInfo,
    ToolResult,
    Usage,
)
from . import llm, spend
from .postdoc import PostdocUnavailable, ask_model
from .validate import decline_reason, validate_claims

# core/.env, which is gitignored. Loaded here rather than by the shell so that
# `uv run uvicorn ...` works with no ceremony; `override=False` means a real
# environment variable still wins, which is what CI would set.
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("openferment.api")

app = FastAPI(title="openferment-core", version="0.1.0")


@app.middleware("http")
async def refuse_changes_from_elsewhere(request: Request, call_next):
    """A changing request from another site, or under a hostile name, stops
    here with a 403 that says why (guard.py, OF-BLD-012 §B.6)."""
    why = guard.refusal(request.method, request.headers)
    if why is not None:
        log.warning("refused %s %s: %s", request.method, request.url.path, why)
        return JSONResponse(status_code=403, content={"detail": why})
    return await call_next(request)

# §6 caps evidence at 30 records. The cap is the contract with the token budget.
MAX_EVIDENCE = 30


@app.get("/api/health")
def health() -> dict:
    """Liveness, and what the service can actually do right now.

    `hasKey` lets the UI tell "the service is down" from "the service is up but
    has no key" — two different problems with two different fixes, and a single
    "unavailable" would send somebody to restart a process that is running fine.
    """
    try:
        corpus = load_corpus()
        records = len(corpus.records)
        corpus_error = None
    except FileNotFoundError as e:
        records = 0
        corpus_error = str(e)
    return {
        "ok": corpus_error is None,
        "service": "openferment-core",
        "model": llm.primary(),
        # The model a call falls back to when the primary declines or is
        # unavailable (llm.py).
        "fallbackModel": llm.fallback(),
        "hasKey": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "records": records,
        "corpusError": corpus_error,
    }


CORPUS_MISSING = (
    "The corpus has not been generated. Run `pnpm export:corpus` from "
    "the repository root and restart the service."
)


def _ask_agent(question: str, on_step=None, cancelled=None, history=None, include_archived: bool = False) -> AnswerPlan:
    """The bounded loop (OF-BLD-014 §5.2) over the evidence pool as it stands,
    with the conversation's earlier turns when the question is a follow-up.
    The browser's program switch rides in the tools' context (OF-BLD-016
    §2.3): off, archived programs are left out of everything the loop reads."""
    ctx = tools.ToolContext(include_archived=include_archived)
    try:
        ctx.pool  # loaded now, so a missing corpus declines in words
    except FileNotFoundError as e:
        log.error("corpus missing: %s", e)
        return AnswerPlan(question=question, declined=CORPUS_MISSING)
    return postdoc_agent.ask(question, ctx=ctx, on_step=on_step, cancelled=cancelled, history=history)


@app.post("/api/ask", response_model=AnswerPlan)
def ask(request: AskRequest) -> AnswerPlan:
    """One question in, one AnswerPlan out. `mode: 'agent'` (the default) runs
    the bounded loop of tools (OF-BLD-014 §5.2); `mode: 'single'` is one
    retrieval and one call.

    Every failure below returns a plan with `declined` set rather than an HTTP
    error, because a declined plan is a thing the UI already knows how to
    render honestly and a 500 is a thing it can only apologise for. The one
    exception is the service being unreachable, which the browser detects
    itself — there is no response to put a reason in.
    """
    question = request.question.strip()
    if not question:
        return AnswerPlan(question="", declined="Ask a question and Postdoc will answer it.")
    if request.mode == "agent":
        return _ask_agent(question, history=request.history, include_archived=request.includeArchived)

    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        log.error("corpus missing: %s", e)
        return AnswerPlan(question=question, declined=CORPUS_MISSING)

    limit = max(1, min(request.maxEvidence, MAX_EVIDENCE))
    # The switch holds here too (OF-BLD-016 §2.3): an archived program's
    # records are neither given to the model nor accepted from it.
    records = [r for r in corpus.search(question, limit=MAX_EVIDENCE if not request.includeArchived else limit)
               if not programs.hides(programs.program_of_record(r), request.includeArchived)][:limit]
    log.info(
        "ask: %r → %d records%s",
        question[:80],
        len(records),
        f" (top: {records[0]['id']} on {records[0]['matchedTerms']})" if records else "",
    )

    try:
        raw, usage = ask_model(question, records, corpus)
    except PostdocUnavailable as e:
        log.error("postdoc unavailable: %s", e)
        return AnswerPlan(question=question, declined=str(e), usage=e.usage)

    result = validate_claims(
        raw.get("claims") or [],
        {rid: r for rid, r in corpus.records_by_id.items()
         if not programs.hides(programs.program_of_record(r), request.includeArchived)},
        corpus.papers_by_id,
    )

    # §5 — log the rejection rate. A rate that climbs is the signal that the
    # prompt has drifted, and it is the only signal there is.
    if result.rejected:
        log.warning(
            "validator dropped %d/%d claims: %s",
            result.rejected,
            result.rejected + len(result.claims),
            "; ".join(result.reasons),
        )

    # Gaps and the decline are model prose, held to Rule 1 as the loop holds
    # them: one with a number is dropped and named (OF-BLD-016 §1.R).
    gaps, said = postdoc_agent.held_to_rule_one(raw.get("gaps"), raw.get("declined"), result.reasons)

    return AnswerPlan(
        question=question,
        claims=result.claims,
        gaps=gaps,
        declined=decline_reason(result, said),
        usage=usage,
        rejected=result.rejected,
        rejectionReasons=result.reasons,
    )


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/ask/stream")
def ask_stream(request: AskRequest) -> StreamingResponse:
    """The loop's steps as they complete (OF-BLD-014 §5.3), as server-sent
    events: `step` (a TraceStep), then `plan` (the validated AnswerPlan), or
    `error` when the service itself failed. A declined plan is a `plan`. In
    `single` mode there are no steps, and the plan is the only event."""
    return StreamingResponse(_stream_events(request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _stream_events(request: AskRequest):
    """The events of one question, as text. When the reader goes, the
    generator is closed, and the loop stops before its next model turn
    (§5.R) rather than spending on an answer nobody will read."""
    events: queue.Queue = queue.Queue()
    gone = threading.Event()

    def work() -> None:
        try:
            question = request.question.strip()
            if request.mode == "single" or not question:
                plan = ask(request)
            else:
                plan = _ask_agent(question, on_step=lambda s: events.put(("step", s.model_dump(mode="json"))),
                                  cancelled=gone.is_set, history=request.history,
                                  include_archived=request.includeArchived)
            events.put(("plan", plan.model_dump(mode="json")))
        except Exception as e:  # the stream must end in words, never hang
            log.exception("ask stream failed")
            events.put(("error", {"message": f"Postdoc failed while answering: {type(e).__name__}. The service log names what went wrong."}))
        finally:
            events.put(None)

    threading.Thread(target=work, name="ask-stream", daemon=True).start()
    try:
        while (item := events.get()) is not None:
            yield _sse(*item)
    finally:
        gone.set()


# ── geneOS (OF-BLD-014 §6.3) ───────────────────────────────────────────


class CeilingRequest(BaseModel):
    modelId: str
    product: str = "phb"
    substrate: str


class MixRequest(BaseModel):
    modelId: str
    product: str = "phb"
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
def fermos_families(includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The model families (`FamilyInfo`): each with its equations, states,
    parameters (ParameterSpecs) and the panel's groups. A family of an
    archived program (storage_v1, PHA's) is left out unless asked."""
    return [f.model_dump(mode="json") for f in fermos.families(includeArchived)]


@app.get("/api/fermos/families/{family_id}")
def fermos_family(family_id: str) -> dict:
    """One model family by id, archived or not; 404 in words for none."""
    from . import kinetics

    try:
        return fermos.family_info(family_id).model_dump(mode="json")
    except kinetics.FamilyRefused as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/fermos/simulate")
def fermos_simulate(req: SimulationRequest) -> dict:
    """Simulate a model family (`SimulationResult`) and keep it as one
    `fermos.simulation` artifact. Each parameter resolves with its source: a
    person's override (an assumption by name, so the result is `demo`), else
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
                durationPreset: str = "until-sugar-runs-out", includeArchived: bool = False,  # noqa: N803
                overrides: str | None = None) -> dict:
    """A family's parameters bound for a strain, product and sugar
    (`FermosBinding`, OF-BLD-020 §3.2, D6): each from the fit a person chose
    (`?fit=`), the records of the evidence pool the switch shows through the
    aggregate gate, a kept simulation (`?startFrom=simulation:<id>`), or the
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
                            startFrom=startFrom, durationPreset=durationPreset, includeArchived=includeArchived,
                            overrides=_overrides_param(overrides))
    try:
        return fermos.bind(req).model_dump(mode="json")
    except fermos.SimulationRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/fermos/simulations")
def fermos_simulations(includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The kept simulations, newest first (`SimulationSummary`); one of an
    archived program is left out unless asked. A read: it runs nothing."""
    return [s.model_dump(mode="json") for s in fermos.simulations(includeArchived)]


@app.get("/api/fermos/fits")
def fermos_fits(flowsheet: str, includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The kinetic fits, forecasts and simulations fermOS keeps (a
    simulation since OF-BLD-020 §3.3), newest first, each with what it can
    feed a shelf flowsheet's titre, yield and productivity and why not
    (OF-BLD-019 §5.1, D10); one of an archived program left out unless
    `?includeArchived=true` (§3.R). A person picks one on the scenario page;
    a read: it keeps nothing. A flowsheet a scenario cannot run is a 422."""
    from . import proforma

    try:
        return [f.model_dump(mode="json") for f in proforma.fermos_fits(flowsheet, includeArchived)]
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
def proforma_shelf(includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The shelf of flowsheets (OF-BLD-019 §2.1, D2): pure data, read with no
    simulator. A flowsheet of an archived program is left out unless
    `?includeArchived=true` asks for it, as the artifact list does."""
    from . import proforma

    return [f.model_dump(mode="json") for f in proforma.shelf(include_archived=includeArchived)]


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


@app.get("/api/proforma/scenarios")
def proforma_scenarios(host: str | None = None, includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The seed's BioSTEAM scenarios with their inputs bound to records
    (§8.3; OF-BLD-019 §2.3): one per scenario whose program the switch
    shows, so sc-yeast-1 with it off and sc-pha-1 too with it on. A read: it
    starts no simulator."""
    from . import proforma

    return [s.model_dump(mode="json") for s in proforma.scenarios(include_archived=includeArchived, host=host)]


@app.get("/api/proforma/bind")
def proforma_bind(flowsheet: str, host: str | None = None, includeArchived: bool = False,  # noqa: N803
                  fits: str | None = None, overrides: str | None = None) -> dict:
    """A shelf flowsheet's inputs bound, as a scenario a person made in the
    browser shows them (OF-BLD-019 §2.3, D6), id and name empty; `?fits=`
    lays on the fermOS fits a person chose (§5.1), a JSON object of input
    key to artifact id, and `?overrides=` a person's overrides of one
    scenario's scope over both (OF-BLD-020 D3), a JSON list. A reference
    biorefinery, the toy, an unknown id, a flowsheet of a program the switch
    hides, a fit that cannot feed its input, or an override that cannot
    stand is a 422 in words. A read: it starts no simulator."""
    from . import proforma

    chosen = _fits_param(fits)
    typed = _overrides_param(overrides)
    try:
        values, _ = proforma.named_values(None, typed)
        if values:
            proforma._check_keys(proforma.runnable(flowsheet), values)
        return proforma.bind_flowsheet(flowsheet, include_archived=includeArchived, host=host,
                                       assumptions=values, fits=chosen).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/api/proforma/ceiling-check")
def proforma_ceiling_check(scenarioId: str, flowsheet: str | None = None, host: str | None = None,  # noqa: N803
                           includeArchived: bool = False, fits: str | None = None,  # noqa: N803
                           assumptions: str | None = None, overrides: str | None = None) -> dict:
    """A scenario's fermenter yield read against the newest stored geneOS
    ceiling of each shelf model of its organism, on its flowsheet's sugar
    (OF-BLD-019 §5.2, D11): `CeilingCheck`. A seed scenario by its id, one
    made in the browser by the flowsheet it names; `?fits=` and
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
        return proforma.ceiling_check(scenarioId, flowsheet, include_archived=includeArchived, host=host,
                                      assumptions=typed, fits=chosen, overrides=over).model_dump(mode="json")
    except proforma.ScenarioRefused as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/proforma/run")
def proforma_run(req: ProformaRunRequest) -> dict:
    """Run a seed scenario by its id, or a scenario made in the browser by
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
    starts no simulator. The scenario is named by id, so no program filter
    applies (a link opens what it names)."""
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
                 durationPreset: str | None = None, includeArchived: bool = False) -> dict:  # noqa: N803 (the wire name)
    """A scope's parameters (`ParamScope`): every spec with its bounds and
    their reason, and its value as the service binds it now, with its
    source. `proforma:<scenario id>` is a seed scenario, or with
    `?flowsheet=` a scenario made in a browser; `?host=` and `?fits=` (JSON)
    bind as `/api/proforma/bind` does. Binding only: it starts no worker,
    integrates nothing and keeps nothing. `fermos:vessel:<id>` (with
    `?vesselType=`) reads its class's defaults through the Proforma worker,
    which a read starts when it is cold (OF-BLD-020 §4.1). `fermos:family:<id>`
    binds as GET /api/fermos/bind does, from `?strain=`, `?product=`,
    `?sugar=`, `?fit=`, `?startFrom=`, `?durationPreset=` and
    `?includeArchived=` (OF-BLD-020 §3.2). 404 for a scope no provider here
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
                              durationPreset=durationPreset, includeArchived=includeArchived)
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
def fermos_vessels(includeArchived: bool = False) -> list[dict]:
    """Every kept vessel design, newest first (`VesselSummary`): a read,
    which starts no simulator. One for an archived program's simulation is
    left out unless asked (OF-BLD-020 §8.R, finding 3)."""
    from . import vessel

    return [v.model_dump(mode="json") for v in vessel.designs(includeArchived)]


# ── thermosteam answers property questions (OF-BLD-019 §4.2, D9) ───────


def _thermo_answer(fn, req: ThermoPropsRequest):
    from . import artifacts, evidence_pool, thermo

    try:
        # A person names the run or the record by id, so archived programs'
        # records resolve too; the page says which program a run is of. Only
        # a record needs the pool.
        kind, _ = thermo.question(req)
        return fn(req, pool=evidence_pool.load(include_archived=True) if kind == thermo.BEER else None)
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


def _warm_proforma() -> None:
    from . import proforma

    if proforma.warm_on_start():
        proforma.start(background=True)


_warm_proforma()


# ── Intake (OF-BLD-012 §5.2) ────────────────────────────────────────────


@app.post("/api/intake/{paper_id}/fetch", response_model=FetchResult)
def intake_fetch(paper_id: str, force: bool = False) -> FetchResult:
    """Fetch one paper's full text from Europe PMC, or from OSTI or the
    Saccharomyces Genome Database when its `sourceUrl` names one, split it,
    cache it.

    A fetch that fails returns HTTP 200 with `status: failed:fetch` or
    `failed:parse` and a reason — the ingest board renders both, and a 5xx
    would render as nothing. The only errors here are a paper the corpus has
    never heard of, and a corpus that has not been generated.
    """
    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    paper = corpus.paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"{paper_id} is not in the corpus")
    result = intake.fetch_paper(paper, force=force)
    log.info("intake: %s → %s%s", paper_id, result.status, f" ({result.reason})" if result.reason else "")
    return result


@app.get("/api/intake/status")
def intake_status() -> dict[str, IntakeStatus]:
    """Every paper with a cached fetch, success or failure, summarised."""
    return intake.all_statuses()


@app.post("/api/intake/{paper_id}/extract", response_model=ExtractResponse)
def intake_extract(paper_id: str, force: bool = False) -> ExtractResponse:
    """One structured model response over the paper's cached full text (§6.1, §6.3).

    422 when the paper has no cached full text — there is nothing to anchor
    to, and an extraction over a curation note would be an extraction over
    the curator. 503 when there is no key or the API cannot be reached; the
    detail says which.
    """
    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if corpus.paper(paper_id) is None:
        raise HTTPException(status_code=404, detail=f"{paper_id} is not in the corpus")
    fetched = intake.cached(paper_id)
    if fetched is None or fetched.status != "complete":
        raise HTTPException(
            status_code=422,
            detail=f"{paper_id} has no cached full text. POST /api/intake/{paper_id}/fetch first.",
        )
    try:
        result = extract.extract_paper(paper_id, force=force)
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


# ── the overlay (OF-BLD-012 §2.1) ───────────────────────────────────────


@app.get("/api/biorepo/overlay", response_model=Overlay)
def biorepo_overlay() -> Overlay:
    """What the service knows that the seed does not.

    Papers from fulltext/ (§5); the run and the new candidates recomputed
    from candidates/ against the seed (§6.2); the reviewers' decisions from
    biorepo.json (§7.2). The store applies whatever is here in one action at
    load, and nothing here changes a record's status — that path goes
    through `biorepo.write` alone. A missing corpus.json costs the run, not
    the overlay.
    """
    runs, candidates, decisions = witness.overlay_bundle()
    # Always the FULL lists, never None (OF-BLD-012.1 F3): an empty list here
    # means the extractor has produced nothing, and the store drops what it
    # was holding. None is reserved for a caller that supplies neither, and
    # nothing in this service is such a caller.
    return Overlay(papers=intake.overlay_papers(), records=decisions, candidates=candidates, runs=runs)


@app.post("/api/biorepo/decisions", response_model=ReviewDecision)
def biorepo_decisions(decision: ReviewDecision) -> ReviewDecision:
    """The one way a decision reaches biorepo.json (§2.3, §7.2): through
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


class ProposeRequest(BaseModel):
    by: str


def _check_refused(e: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(e))


@app.get("/api/guild/checks", response_model=Checks)
def checks_read() -> Checks:
    return checks.read()


@app.post("/api/guild/checks/propose", response_model=list[Check])
def checks_propose(request: ProposeRequest) -> list[Check]:
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
def practice_draft(request: PracticeDraftRequest, includeArchived: bool = False) -> PracticeScenario:  # noqa: N803 (the wire name)
    """A scenario for one skill. An archived program's protocols are no source
    unless `?includeArchived=true` asks for them (OF-BLD-016 §2.R)."""
    try:
        return practice.draft(request, include_archived=includeArchived)
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
    """RunOutput[] recomputed from every candidates/*.json against the seed.
    Empty until something has been extracted. 503 when the corpus has not
    been generated, because there is nothing to score against."""
    try:
        return witness.runs()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── Artifacts (OF-BLD-014 §3.2, E.5) ─────────────────────────────────────


@app.get("/api/biorepo/artifacts", response_model=list[Artifact])
def artifacts_list(includeArchived: bool = False) -> list[Artifact]:  # noqa: N803 (the wire name)
    """Every value this service computed and kept, newest first. A value
    computed from an archived program's records, models, products or strains
    is left out unless `?includeArchived=true` asks for it (OF-BLD-016 §2.R),
    as the evidence pool leaves it out of Postdoc; a Proforma run by its
    scenario and flowsheet too, as every reader decides it (OF-BLD-019 §6.R)."""
    from . import module_stores

    kept = artifacts.all_artifacts()
    if includeArchived:
        return kept
    try:
        lookup = load_corpus().record
    except FileNotFoundError:
        lookup = None
    return [a for a in kept if not programs.hides(module_stores.artifact_program(a, lookup))]


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


def _record_lookup():
    try:
        return load_corpus().record
    except FileNotFoundError:
        return None


@app.get("/api/pureos/trains")
def pureos_trains(includeArchived: bool = False) -> list[dict]:  # noqa: N803 (the wire name)
    """The trains on file: the newest Proforma run of each scenario, read
    unit by unit from its stream table, with its overall recovery. A train of
    an archived program is left out unless `?includeArchived=true` asks for it.
    A read: it starts no simulator."""
    from . import pureos

    return [pureos.summary(t).model_dump(mode="json")
            for t in pureos.trains(include_archived=includeArchived, record_lookup=_record_lookup())]


@app.get("/api/pureos/train/{key}")
def pureos_train(key: str) -> dict:
    """One train: the newest run of the scenario `key` names, or the run whose
    artifact id it is. 404 says how a run gets there; a deep link opens
    whatever program it belongs to, and the page names it."""
    from . import pureos

    try:
        return pureos.train(key, record_lookup=_record_lookup()).model_dump(mode="json")
    except pureos.TrainNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


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


@app.get("/api/audit", response_model=list[AuditEntry])
def audit_read(limit: int = 200) -> list[AuditEntry]:
    """The newest lines of the audit log, newest last."""
    from . import audit

    return audit.read(max(1, min(limit, audit.MAX_READ)))


@app.post("/api/tools/{name}", response_model=ToolResult)
def tools_run(name: str, body: dict[str, Any], includeArchived: bool = False) -> ToolResult:  # noqa: N803 (the wire name)
    """Run one tool through the registry, the same path Postdoc's loop and
    the MCP server take. A refusal is a result with `error` set; an unknown
    tool is a 404. The program switch is a query parameter,
    `?includeArchived=true`, and rides in the tool's context: the body is the
    tool's input, and no input carries it (OF-BLD-016 §2.3)."""
    if name not in tools.REGISTRY:
        raise HTTPException(status_code=404, detail=f"no tool named {name!r}")
    return tools.run(name, body, tools.ToolContext(include_archived=includeArchived))


# ── Passage retrieval (OF-BLD-014 Phase 4) ───────────────────────────────


@app.get("/api/rag/status", response_model=RagStatus)
def rag_status() -> RagStatus:
    """Papers indexed, passages, the lanes and whether each can run, and the
    lane searches use when none is named."""
    return passages.status()


@app.post("/api/rag/search", response_model=RagSearchResponse)
def rag_search(request: RagSearchRequest) -> RagSearchResponse:
    """Passages for a question, on the lane named or the chosen one. A lane
    that cannot run here is a 409 that says why; a paid lane's helper calls
    are held to the daily cap like every model call."""
    try:
        detail = retrieve.search_detail(request.question, k=max(1, min(request.k, 20)), lane=request.lane,
                                        include_archived=request.includeArchived)
    except retrieve.LaneUnavailable as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except (llm.ModelUnavailable, llm.ModelRefused, spend.BudgetSettingInvalid) as e:
        # A key refused, a budget spent or set wrong, a request declined:
        # the service is up and says why (§4.R).
        raise HTTPException(status_code=503, detail=str(e)) from None
    return RagSearchResponse(
        lane=detail.lane,
        hits=detail.hits,
        phrasings=detail.phrasings,
        unverifiedSentences=detail.unverifiedSentences,
        costUsd=detail.usage.costUsd,
        note=detail.note,
    )


@app.get("/api/rag/report", response_model=RagReport)
def rag_report() -> RagReport:
    """The last scorecard of every lane; 404 until `pnpm rag:eval` has run."""
    report = rageval.read_report()
    if report is None:
        raise HTTPException(status_code=404, detail="no retrieval scorecard yet: run pnpm rag:eval")
    # The rule's choice and the lane in use can differ: a person may hold the
    # lane apart (OF-BLD-016 §4.1), and the screen names both.
    return report.model_copy(update={"laneInUse": passages.chosen_lane()})


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
