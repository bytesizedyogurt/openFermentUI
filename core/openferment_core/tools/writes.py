"""One write tool per module, the pair of its read tool (OF-BLD-015 §7.3).

`dominion_write`, `runbooks_write`, `geneos_write`, `fermos_write`,
`pureos_write`, `proforma_write`, `biorepo_write`, `guild_write`,
`primer_write`, `intake_write`, `home_write`.

THE RULE. A write tool never touches a store. Each action calls the
module's own write function, where the module's rules already live:
`geneos.ceiling` and its kin, `fermos.forecast_run`, `proforma.run`,
`extract.add_candidate` (anchoring, §2.4), `intake.fetch_paper`,
`extract.extract_paper`, and `checks.request` in a person's name. A module
with no write function on the service refuses in words with the reason
(Dominion, pureOS and Primer are curated seed; protocols and depositions
are written in the browser), and that refusal is a result Postdoc reports
in `gaps`. `check:tools` greps this file for a store write and fails on one.

THE MARK. Every write that goes through carries `agent: model`, the model
id, the effort and the ask id into the audit log (`audit.py`), and what it
made lands in the open lane: an artifact with its basis, a candidate
`unverified`, a fetched paper. A person or a run promotes it.

THE GATES. An action in `gates.GATES` writes nothing: it becomes a proposal
with `state: proposed`, and Home shows it with one button (§7.4). The spend
gate is reached at run time, when the budget refuses an extraction.

Inputs carry ids and words, as every tool's do: `action`, `target` (an id or
ref), `fields` (names to words, what the action needs), `note` (the model's
own words on why). A number anywhere is refused by the registry before this
file runs.
"""
from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from .. import llm, module_stores
from ..models import ToolResult
from . import Tool, ToolContext, register
from . import gates

# ── what each module can be asked to do ───────────────────────────────────

# action → (what it does, the fields it takes). An action in gates.GATES is
# listed too: the model sees it, and the registry turns it into a proposal.
ACTIONS: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    "dominion": {
        "publish": ("publish a clearance finding to the commons (gated)", ("productId", "jurisdictionId")),
    },
    "runbooks": {
        "draft": ("draft a runbook: use the draft_runbook tool, which writes the numbers from the evidence", ()),
        "lock": ("lock a runbook's predictions before a run (gated)", ()),
        "deposit": ("start a deposition of a protocol on the bench (gated)", ("protocolId",)),
        "run": ("send a runbook's protocol to the bench (gated)", ("protocolId",)),
        "publish": ("publish a runbook and its ledger to the commons (gated)", ()),
        "revise_protocol": ("draft a protocol revision", ("protocolId", "change")),
    },
    "geneos": {
        "ceiling": ("compute and keep the yield ceiling of a model on a sugar", ("modelId", "product", "substrate")),
        "frontier": ("compute and keep the growth–product frontier of a model on a sugar", ("modelId", "product", "substrate")),
        "mix": ("compute and keep the ceiling across a mix of two sugars", ("modelId", "product", "substrate", "substrateB")),
    },
    "fermos": {
        "forecast": ("forecast a run from a kept kinetic fit and keep it", ("fitArtifactId",)),
        "fit": ("fit a deposited run's series", ("depositionId",)),
    },
    "pureos": {},
    "proforma": {
        "run": ("run the BioSTEAM scenario named in target on the bound inputs and keep the run", ()),
        "bind": ("bind an assumption to a scenario input", ("key", "value", "basis")),
    },
    "biorepo": {
        "candidate": ("create an extraction candidate anchored to a sentence of a fetched paper",
                      ("paperId", "sectionId", "field", "value", "unit", "quote", "organism", "carbonSource", "method")),
        "decide": ("accept, reject or correct a record", ("recordId",)),
        "publish": ("publish records to the commons (gated)", ()),
    },
    "guild": {
        "propose_check": ("propose a competence check on a person's skills (gated: a person asks for it)", ("personId", "skillIds")),
        "record_check": ("mark a check's outcome (refused: an assessor runs a check at the bench)", ("checkId",)),
        "evidence": ("record evidence on the ledger (gated: a person signs it)", ("personId", "skillId", "kind")),
        "person": ("add or change a person on the ledger (gated)", ("personId", "name")),
        "policy": ("change the lead's Guild policy (gated)", ("criticality", "mode")),
    },
    "primer": {
        "lesson": ("write or change a lesson", ("lessonId",)),
    },
    "intake": {
        "fetch": ("fetch the full text of the paper named in target from Europe PMC and prepare it", ()),
        "extract": ("extract candidates from the fetched paper named in target (spends on the model)", ()),
        "add": ("add a new source to the corpus", ("doi",)),
    },
    "home": {
        "note": ("propose a notebook note a person accepts under their name (gated)", ()),
    },
}

NO_WRITE = {
    "dominion": "Dominion's molecules and clearance findings are curated seed (src/data/products.ts, "
                "src/data/clearanceFindings.ts); the service has no write function for them, and a finding is written by a "
                "person in a commit",
    "pureos": "pureOS's unit operations are curated vocabulary (src/data/vocabulary.ts); the service has no write function "
              "for them",
    "primer": "Primer's lessons are curated seed (src/data/learn.ts); the service has no write function for them",
}
NO_WRITE_ACTION = {
    ("runbooks", "revise_protocol"): "protocols are curated seed (src/data/protocols.ts) and revised in the browser's "
                                     "editor by a person; the service has no write function for them",
    ("runbooks", "draft"): "use the draft_runbook tool: it takes the evidence ids and record ids this run returned and "
                           "writes every number from them",
    ("fermos", "fit"): "a deposition's series lives in the browser, which sends it to POST /api/fermos/fit; the service "
                       "holds no deposition to fit",
    ("proforma", "bind"): "an assumption is a named person's and is kept in the browser's Durable tier; the service has no "
                          "store for one, and a model's number would be one from its weights",
    ("biorepo", "decide"): "a review decision is a person's (biorepo.write refuses any other reviewer); say in gaps what "
                           "you would decide and why",
    ("intake", "add"): "a source enters the corpus through a person's approval (pnpm thread:propose, thread:apply); "
                       "the service has no write function for a new paper",
    ("primer", "lesson"): "Primer's lessons are curated seed (src/data/learn.ts); the service has no write function for them",
    ("guild", "record_check"): "a check is run by an assessor at the bench (/guild/checks/:id/run), one criterion at a "
                               "time, and its entries are written in their name; a model may propose a check and never "
                               "record one",
}


class ModuleWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(description="One of the actions in the tool's description.")
    target: str = Field(description="The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string.")
    fields: dict[str, str] = Field(description="What the action needs, by the names in the tool's description, as words and ids; "
                                               "a value copied from a quote is a string. Empty when the action takes none.")
    note: str = Field(description="Why, in your own words; kept on the audit line and the proposal.")


def _who(ctx: ToolContext | None = None) -> tuple[str, str]:
    """The model this write is marked with: the one answering the run when a
    loop owns it (§7.R finding 7), else the chain's first name."""
    model = getattr(ctx, "model", "") or llm.chain("answer")[0]
    return model, llm.effort()


def _audit(ctx: ToolContext, module: str, action: str, state: str, target: str | None, detail: dict[str, Any]) -> None:
    from .. import audit

    model, effort = _who(ctx)
    audit.append(agent="model", who=model, module=module, action=action, state=state, target=target,
                 ask_id=getattr(ctx, "ask_id", None), effort=effort, detail=detail)


def _propose(ctx: ToolContext, module: str, action: str, gate: gates.Gate, inp: ModuleWriteInput, title: str, why: str) -> ToolResult:
    from .. import proposals

    model, effort = _who(ctx)
    try:
        # The store holds a proposal's words to Rule 1 and refuses an open
        # twin in the same ask (OF-BLD-016 §1.R findings 2, 5 and 8).
        made = proposals.propose(module=module, action=action, gate=gate, title=title, why=why, by=model,
                                 target=inp.target or None, fields=inp.fields, note=inp.note,
                                 ask_id=getattr(ctx, "ask_id", None), effort=effort)
    except proposals.ProposalRefused as e:
        return ToolResult(error=f"{module}_write refused {action}: {e}. Nothing was proposed. Say so in gaps.")
    return ToolResult(summary={
        "state": "proposed",
        "proposalId": made.id,
        "gate": gate.id,
        "gateCovers": gate.covers,
        "how": gate.how,
        "meaning": "nothing was written: this action waits for a person, who sees it as a card on Home with one button. "
                   "Say so in gaps.",
    })


def _need(inp: ModuleWriteInput, *names: str) -> str | None:
    missing = [n for n in names if not (inp.fields.get(n) or "").strip()]
    return f"fields {', '.join(missing)} are needed" if missing else None


# ── the actions that write ────────────────────────────────────────────────


def _geneos(action: str, inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    from .. import geneos
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    need = _need(inp, "modelId", "product", "substrate") or (action == "mix" and _need(inp, "substrateB")) or None
    if need:
        return ToolResult(error=f"geneos_write refused: {need}")
    f = inp.fields
    try:
        if action == "ceiling":
            r = geneos.ceiling(f["modelId"], f["product"], f["substrate"])
        elif action == "frontier":
            r = geneos.frontier(f["modelId"], f["product"], f["substrate"])
        else:
            r = geneos.mix(f["modelId"], f["product"], f["substrate"], f["substrateB"])
    except geneos.GeneosUnavailable as e:
        return ToolResult(error=f"geneos_write refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"geneos_write could not compute it: {e}")
    if r.finding:
        # A finding stores nothing (§7.R finding 3): the audit line says so.
        _audit(ctx, "geneos", action, "finding", f["modelId"], {"finding": r.finding, "note": inp.note})
        return ToolResult(summary={"state": "finding", "model": f["modelId"], "finding": r.finding,
                                   "meaning": "nothing was kept: the model cannot take this feed up, which is the answer"})
    ev = r.evidence
    assert ev is not None
    _audit(ctx, "geneos", action, "open", f["modelId"], {"artifactId": r.artifactId, "evidenceId": ev.id, "note": inp.note})
    return ToolResult(
        summary={"state": "open", "artifactId": r.artifactId, "evidenceId": ev.id, "what": ev.label, "provenance": ev.provenance,
                 "meaning": "kept as an artifact in the open lane, marked as the model's in the audit log; cite the evidence id"},
        evidence=[ev],
    )


def _fermos_forecast(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    from .. import artifacts, fermos

    need = _need(inp, "fitArtifactId")
    if need:
        return ToolResult(error=f"fermos_write refused: {need}")
    try:
        r = fermos.forecast_run(fit_artifact=inp.fields["fitArtifactId"])
    except (fermos.FitRefused, artifacts.ArtifactNotFound, artifacts.ArtifactDamaged) as e:
        return ToolResult(error=f"fermos_write refused: {e}")
    _audit(ctx, "fermos", "forecast", "open", inp.fields["fitArtifactId"], {"artifactId": r.artifactId, "evidenceId": r.evidence.id,
                                                                            "note": inp.note})
    return ToolResult(summary={"state": "open", "artifactId": r.artifactId, "evidenceId": r.evidence.id,
                               "provenance": r.evidence.provenance,
                               "meaning": "kept as an artifact in the open lane, marked as the model's; cite the evidence id"},
                      evidence=[r.evidence])


def _proforma_run(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    from .. import proforma
    from ..models import ProformaRunRequest
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    scenario = inp.target or proforma.SCENARIO_ID
    try:
        r = proforma.run(ProformaRunRequest(scenarioId=scenario), pool=ctx.pool)
    except proforma.ScenarioRefused as e:
        return ToolResult(error=f"proforma_write refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"proforma_write could not run the scenario: {e}")
    aid = getattr(r, "artifactId", None)
    ev = getattr(r, "evidence", None)
    _audit(ctx, "proforma", "run", "open", scenario, {"artifactId": aid, "note": inp.note})
    return ToolResult(summary={"state": "open", "scenario": scenario, "artifactId": aid,
                               "evidenceId": getattr(ev, "id", None),
                               "meaning": "the run is kept as an artifact in the open lane, marked as the model's"},
                      evidence=[ev] if ev is not None else [])


def _biorepo_candidate(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    from .. import extract

    need = _need(inp, "paperId", "sectionId", "field", "value", "unit", "quote")
    if need:
        return ToolResult(error=f"biorepo_write refused: {need}")
    # Only the fields the action lists reach anchoring, and the two flags it
    # reads, as the word true or false: every field is a string, and
    # bool('false') is True (OF-BLD-016 §1.R finding 7). Anything else is
    # refused, never passed on and never guessed at.
    listed = ACTIONS["biorepo"]["candidate"][1]
    flags = ("negativeResult", "isPrimary")
    unknown = [k for k in inp.fields if k not in listed and k not in flags]
    if unknown:
        return ToolResult(error=f"biorepo_write refused: {', '.join(unknown)} {'is' if len(unknown) == 1 else 'are'} not a "
                                f"field of a candidate; the fields are {', '.join(listed + flags)}")
    raw: dict[str, Any] = {k: v for k, v in inp.fields.items() if k in listed and k != "paperId"}
    for flag in flags:
        if flag in inp.fields:
            word = inp.fields[flag].strip().lower()
            if word not in ("true", "false"):
                return ToolResult(error=f"biorepo_write refused: {flag} is the word true or false, or left out")
            raw[flag] = word == "true"
    model, _ = _who(ctx)
    try:
        made, rule, detail = extract.add_candidate(inp.fields["paperId"], raw, who=model)
    except extract.ExtractUnavailable as e:
        return ToolResult(error=f"biorepo_write refused: {e}")
    if made is None:
        return ToolResult(error=f"biorepo_write refused on rule {rule}: {detail}")
    row = module_stores.Row("biorepo", "candidate", made.id, made.field, "proposed", "unverified", provenance="unverified",
                            detail={"paperId": made.paperId, "field": made.field, "by": model})
    _audit(ctx, "biorepo", "candidate", "proposed", made.id, {"paperId": made.paperId, "field": made.field, "note": inp.note})
    return ToolResult(
        summary={"state": "proposed", "ref": row.ref, "candidateId": made.id, "field": made.field, "provenance": "unverified",
                 "meaning": "an unverified candidate in the review queue, anchored to the sentence, marked as the model's; "
                            "a person accepts or rejects it on Guild; cite its ref in moduleRefs"},
        rows=[row.model()],
    )


def _intake_fetch(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    from .. import intake

    paper = ctx.pool.corpus.paper(inp.target)
    if paper is None:
        return ToolResult(error=f"intake_write refused: {inp.target!r} is not a paper in the corpus")
    try:
        r = intake.fetch_paper(paper)
    except (intake.NetworkRefused, intake.Transient) as e:
        return ToolResult(error=f"intake_write could not fetch {inp.target}: {e}")
    _audit(ctx, "intake", "fetch", module_stores.intake_state(r.status), inp.target, {"status": r.status, "note": inp.note})
    return ToolResult(summary={"state": module_stores.intake_state(r.status), "paperId": inp.target, "status": r.status,
                               "sections": len(r.sections), "reason": getattr(r, "reason", None),
                               "meaning": "the paper's full text is prepared on the service, marked as the model's fetch"})


def _intake_extract(inp: ModuleWriteInput, ctx: ToolContext, gate: gates.Gate) -> ToolResult:
    from .. import extract

    if ctx.pool.corpus.paper(inp.target) is None:
        return ToolResult(error=f"intake_write refused: {inp.target!r} is not a paper in the corpus")
    try:
        r = extract.extract_paper(inp.target)
    except llm.BudgetExhausted as e:
        # The why is the code's words: the budget's message carries its
        # figures, and a proposal's words hold no number (§1.R finding 5).
        return _propose(ctx, "intake", "extract", gate, inp, f"Extract {inp.target} when the budget allows",
                        "the model budget refused the extraction when it was asked for; it runs when a person presses "
                        "the button and the budget allows")
    except (extract.ExtractUnavailable, extract.ExtractTruncated, llm.ModelRefused, llm.ModelUnavailable) as e:
        return ToolResult(error=f"intake_write could not extract {inp.target}: {e}")
    _audit(ctx, "intake", "extract", "proposed", inp.target, {"candidates": len(r.candidates), "rejected": r.rejected,
                                                              "costUsd": r.usage.costUsd, "note": inp.note})
    return ToolResult(summary={"state": "proposed", "paperId": inp.target, "candidates": len(r.candidates), "rejected": r.rejected,
                               "costUsd": r.usage.costUsd,
                               "meaning": "candidates anchored and queued for review, unverified, marked as the model's run"},
                      usage=r.usage)


# ── the runner ────────────────────────────────────────────────────────────


def _runner(module: str) -> Callable[[ModuleWriteInput, ToolContext], ToolResult]:
    name = f"{module}_write"
    actions = ACTIONS[module]

    def run(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
        action = inp.action.strip()
        if action not in actions:
            seed = f" {NO_WRITE[module]}." if module in NO_WRITE else ""
            listed = f"the actions are {', '.join(actions)}" if actions else "it has no action"
            return ToolResult(error=f"{name} refused: {action!r} is not an action; {listed}.{seed} Say so in gaps.")
        # A gate is checked first: an action at one is a proposal whatever
        # the module can or cannot write itself.
        gate = gates.gated(module, action)
        if module in NO_WRITE and gate is None:
            return ToolResult(error=f"{name} refused: {NO_WRITE[module]}. Say so in gaps.")
        if (module, action) in NO_WRITE_ACTION:
            return ToolResult(error=f"{name} refused {action}: {NO_WRITE_ACTION[(module, action)]}. Say so in gaps.")
        if gate is not None and gate.id != "spend":
            # The title is the code's words and the target's id (§1.R finding
            # 8); a Guild proposal's names nobody, because who a check names
            # is never shown before it is run (finding 9).
            what, _ = actions[action]
            words = what.split(" (")[0]
            title = f"{module_stores.LABEL[module]}: {words}" + (f" — {inp.target}" if inp.target and module != "guild" else "")
            return _propose(ctx, module, action, gate, inp, title, inp.note or words)
        if module == "geneos":
            return _geneos(action, inp, ctx)
        if module == "fermos":
            return _fermos_forecast(inp, ctx)
        if module == "proforma":
            return _proforma_run(inp, ctx)
        if module == "biorepo":
            return _biorepo_candidate(inp, ctx)
        if module == "intake" and action == "fetch":
            return _intake_fetch(inp, ctx)
        if module == "intake" and action == "extract":
            assert gate is not None
            return _intake_extract(inp, ctx, gate)
        return ToolResult(error=f"{name} refused: {action} has no write function yet. Say so in gaps.")

    return run


def _description(module: str) -> str:
    label = module_stores.LABEL[module]
    lines = []
    if module in NO_WRITE and not ACTIONS[module]:
        return (f"Write to {label}: nothing can be written here by a model. {NO_WRITE[module]}. Every call is refused in "
                "words; report the refusal in gaps and name the person who could make the change.")
    for action, (what, fields) in ACTIONS[module].items():
        g = gates.gated(module, action)
        tail = (f" [gated: {g.covers}; becomes a proposal a person carries out on Home]" if g and g.id != "spend"
                else " [at the budget, gated: becomes a spend proposal a person carries out on Home]" if g else "")
        lines.append(f"{action}: {what}" + (f" (fields: {', '.join(fields)})" if fields else "") + tail)
    seed = f" {NO_WRITE[module]}: every other call is refused in words." if module in NO_WRITE else ""
    return (f"Write to {label}, through the module's own write function. Actions — " + "; ".join(lines) + f".{seed} "
            "Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane "
            "marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.")


TOOLS = {
    module: register(Tool(name=f"{module}_write", description=_description(module), input_model=ModuleWriteInput,
                          run=_runner(module), strict=False))
    for module in module_stores.MODULES
}
