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
(Dominion and Primer are curated seed, as pureOS's vocabulary and unit
catalogue are; protocols and depositions are written in the browser), and
that refusal is a result Postdoc reports
in `gaps`. `check:tools` greps this file for a store write and fails on one.

THE MARK. Every write that goes through carries `agent: model`, the model
id, the effort and the ask id into the audit log (`audit.py`), and what it
made lands in the open lane: an artifact with its basis, a candidate
`unverified`, a fetched paper. A person or a run promotes it.

THE GATES. An action in `gates.GATES` writes nothing: it becomes a proposal
with `state: proposed`, and Home shows it with one button (§7.4). The spend
gate is reached at run time, when the budget refuses an extraction. A
flowsheet run is at no gate: it spends no model money and keeps one artifact
in the open lane, as a ceiling does.

ONE RUN, TWO NAMES (OF-BLD-019 §6.1). `proforma_write`'s `run` and the
registry's `run_flowsheet` (tools/proforma.py) both run a scenario through
`run_scenario` below, so the one call to `proforma.run` stays in this file,
where `check:tools` reads it, and both are refused, run and audited alike.
So with a simulation (OF-BLD-020 §3.4): `fermos_write`'s `simulate` and the
registry's `fermos_simulate` (tools/fermos.py) both run `run_simulation`
below, the one call to `fermos.simulate`, free (compute, no model money) and
at no gate, audited with the model as agent. So with a vessel (OF-BLD-020
§4.2): `fermos_write`'s `design_vessel` and the registry's `fermos_vessel`
(tools/fermos.py) both design through `design_vessel` below, the one call to
`vessel.design`. So with a train (OF-BLD-020 §5.4): `pureos_write`'s
`new_train`, `add_unit`, `remove_unit`, `set_from_record` and `run_train` and
the registry's `pureos_build` (tools/pureos.py) share one function an action
below, so the calls to `pureos.kept.keep_train` (the one write to the store of
the trains a model built) and to `pureos.train_spec.run_train` stay in this
file; each is free, at no gate, and audited with the model as agent.

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
        "simulate": ("simulate the model family named in target (batch_v1 and the rest) and keep the simulation, as "
                     "fermos_simulate does: each parameter binds from a fit, the records, a kept simulation or a stated "
                     "convention, and the call refuses naming each parameter nothing binds; records.<parameter key> "
                     "names the record ids, comma-separated, that bind that parameter",
                     ("strain", "product", "sugar", "fitArtifact", "startFrom", "durationPreset", "records.<key>")),
        "design_vessel": ("design on BioSTEAM the vessel a kept simulation (or, anaerobic, a kept kinetic fit) needs and "
                          "keep it, as fermos_vessel does; refused in words while its plant scale waits for a person",
                          ("simulationArtifact", "fitArtifact", "vesselType", "klaMethod")),
    },
    # OF-BLD-020 §5.4 — a train a model builds, kept on the service, as
    # pureos_build builds it (the same function an action).
    "pureos": {
        "new_train": ("start a train for a product (its id) from the inlet a kept artifact gives (inletRef: a kept "
                      "simulation's artifact id, a kept vessel design's, or a kept run's stream as "
                      "<artifact id>/<stream id>), kept on the service as the model's, as pureos_build's new does",
                      ("product", "inletRef")),
        "add_unit": ("add a unit of a catalogue type to the train named in target, after the unit named (inlet for the "
                     "first place; empty for the end)", ("unitType", "afterUnitId")),
        "remove_unit": ("take a unit out of the train named in target", ("unitId",)),
        "set_from_record": ("bind a unit's parameter to exactly the records named for it (records.<parameter key>, "
                            "their ids separated by commas or spaces), each held to the parameter's field, the "
                            "aggregate gate and its unit; refused naming a record that cannot bind and why",
                            ("unitId", "records.<key>")),
        "run_train": ("run the train named in target in the Proforma worker as the service binds it and keep the run; "
                      "refused naming each value that waits for a person's", ()),
    },
    "proforma": {
        "run": ("run the BioSTEAM scenario named in target as the service binds it and keep the run, as run_flowsheet "
                "does; refused naming the inputs that wait for a person's assumption", ()),
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
    "primer": "Primer's lessons are curated seed (src/data/learn.ts); the service has no write function for them",
}
# What a module that writes some things keeps as seed beside them, said when an
# action is not one of its own (OF-BLD-020 §5.4: pureOS keeps a model's train,
# and its vocabulary and catalogue stay curated).
SEED_NOTE = {
    "pureos": "pureOS's unit operations and its unit catalogue are curated (src/data/vocabulary.ts, "
              "core/openferment_core/pureos/catalogue.py); the service has no write function for them",
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


VESSEL_WAITS = ("A named person types the plant scale (or one vessel's batch volume) in fermOS → Vessel, under their "
                "reviewer name; a model never supplies one. Say in gaps that the design waits for it.")


def design_vessel(tool: str, simulation: str, fit: str, vessel_type: str, kla_method: str, note: str,
                  ctx: ToolContext) -> ToolResult:
    """Design the vessel a kept simulation (or, anaerobic, a kept fit) needs
    on BioSTEAM, keep it as one `fermos.vessel` artifact, and mark it as the
    model's (OF-BLD-020 §4.2, D13). `fermos_vessel` and `fermos_write`'s
    `design_vessel` both run here, so the one call to `vessel.design` stays
    in this file. Ids and words in: the artifact, the vessel type, the kLa
    correlation by BioSTEAM's name. The service holds no person's plant scale
    or batch volume (they are typed in the panel, in a browser), so none is
    passed, and the design is refused in vessel.design's own words until a
    person's design is asked for on the screen."""
    from .. import artifacts, vessel
    from ..models import VesselRequest
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    sim, fitted = (simulation or "").strip(), (fit or "").strip()
    if bool(sim) == bool(fitted):
        return ToolResult(error=f"{tool} refused: name one kept simulation (simulationArtifact) or one kept kinetic fit "
                                "(fitArtifact) by its artifact id, not both; fermos_read lists them")
    kind = (vessel_type or "").strip() or None
    if kind is not None and kind not in vessel.VESSEL_TYPES:
        return ToolResult(error=f"{tool} refused: a vessel type is {' or '.join(vessel.VESSEL_TYPES)}; {kind!r} is neither")
    try:
        d = vessel.design(VesselRequest(simulation=sim or None, fit=fitted or None, vesselType=kind,
                                        klaMethod=(kla_method or "").strip() or None,
                                        includeArchived=ctx.include_archived))
    except vessel.VesselRefused as e:
        waits = f" {VESSEL_WAITS}" if "plant_scale" in str(e) else ""
        return ToolResult(error=f"{tool} refused: {e}.{waits}")
    except (vessel.VesselNotFound, artifacts.ArtifactDamaged) as e:
        return ToolResult(error=f"{tool} refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{tool} could not design the vessel: {e}")
    ev = d.evidence
    _audit(ctx, "fermos", "design_vessel", "open", sim or fitted, {"artifactId": d.artifactId, "evidenceId": ev.id,
                                                                   "tool": tool, "note": note})
    return ToolResult(summary={"state": "open", **_vessel_summary(d), "evidenceId": ev.id,
                               "meaning": "the vessel is designed on BioSTEAM and kept as one artifact in the open lane, "
                                          "marked as the model's in the audit log; cite its numbers by the evidence id, "
                                          "which is its artifact id; never state them yourself"},
                      evidence=[ev])


# The design table's rows a summary carries, by the label the worker reads
# them under; the whole table is in the artifact (get_artifact).
VESSEL_ROWS = ("Vessels", "Volume of each vessel", "Working volume of each vessel", "Batch time (reacting)",
               "Cycle time", "Dead time", "Agitator power, each vessel", "Compressor power", "kLa achieved",
               "Superficial gas velocity", "Aeration, vvm", "Reactor duty", "Cooling duty, every heat utility",
               "Electricity, the whole unit")


def _vessel_summary(d: Any) -> dict[str, Any]:
    """What a model reads of a design, copied from it: the rows a reader
    asks for first, the oxygen balance in brief, heat, cost with its index,
    who assumed what, and the flags. Nothing is computed here."""
    ox = d.oxygen
    return {
        "artifactId": d.artifactId, "provenance": d.provenance, "source": d.source, "sourceTool": d.sourceTool,
        "unitClass": d.unitClass, "vesselType": d.vesselType, "aerobic": d.aerobic,
        "design": [{"label": r.label, "value": r.value, "unit": r.unit} for r in d.design if r.label in VESSEL_ROWS],
        "oxygen": None if ox is None else {
            "method": ox.method, "kLa": ox.kLa, "kLaNeededAtPeak": ox.kLaNeededAtPeak, "kLaUnit": ox.kLaUnit,
            "otr": ox.otr, "unit": ox.unit, "short": ox.short, "oxygenBasis": ox.oxygenBasis, "aerated": ox.aerated},
        "oxygenNote": d.oxygenNote,
        # How BioSTEAM found its duty and what the cross-check rests on, in the service's words (§4.R).
        "heat": {"bst": d.heat.bst, "method": d.heat.method, "dutyNote": d.heat.dutyNote,
                 "convention": d.heat.convention, "conventionNote": d.heat.conventionNote, "unit": d.heat.unit},
        "cost": {"purchase": d.cost.purchase, "installed": d.cost.installed, "unit": "USD",
                 "costIndex": d.cost.costIndex, "costIndexYear": d.cost.costIndexYear},
        "assumedBy": sorted({p.overriddenBy for p in d.parameters if p.overriddenBy}),
        "flags": d.flags,
    }


def _fermos(action: str, inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    if action == "simulate":
        return _fermos_simulate(inp, ctx)
    if action == "design_vessel":
        f = inp.fields
        return design_vessel("fermos_write", f.get("simulationArtifact", ""), f.get("fitArtifact", ""),
                             f.get("vesselType", ""), f.get("klaMethod", ""), inp.note, ctx)
    return _fermos_forecast(inp, ctx)


RUN_WAITS = ("A named person types each waiting input in Proforma, on the scenario's page, under their reviewer "
             "name; a model never supplies one. Say in gaps which inputs wait.")


def run_scenario(tool: str, scenario_id: str, note: str, ctx: ToolContext) -> ToolResult:
    """Run one BioSTEAM scenario as the service binds it, keep the run and
    mark it as the model's (OF-BLD-019 §6.1). The service holds no person's
    assumption (they live in the browser's Durable tier), so none is passed:
    an input with no record waits, and the refusal is proforma.run's own
    words (what `POST /api/proforma/run` answers with a 422)."""
    from .. import programs, proforma, pureos
    from ..models import ProformaRunRequest
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    sid = (scenario_id or "").strip()
    if not sid:
        return ToolResult(error=f"{tool} refused: name the scenario to run by its id (proforma_read lists them)")
    try:
        refused = programs.archived_refusal(tool, [("scenario", sid)], ctx.include_archived)
    except FileNotFoundError:  # no projection here: nothing is known to be archived
        refused = None
    if refused:
        return ToolResult(error=refused)
    seed = {s["id"]: s for s in pureos.seed_scenarios()}
    if seed and sid not in seed:
        held = ", ".join(sorted(k for k, s in seed.items() if s.get("kind") == "biosteam"))
        return ToolResult(error=f"{tool} refused: {sid} is not a scenario this service holds. A scenario made with New "
                                f"scenario lives in the browser that made it, and a person runs it on its page in "
                                f"Proforma; the service's BioSTEAM scenarios are {held or 'none'}")
    if seed and seed[sid].get("kind") != "biosteam":
        return ToolResult(error=f"{tool} refused: {sid} is an authored cost surface, not a BioSTEAM flowsheet; "
                                "nothing runs it")
    try:
        r = proforma.run(ProformaRunRequest(scenarioId=sid), pool=ctx.pool)
    except proforma.ScenarioRefused as e:
        waits = f" {RUN_WAITS}" if "wait for a source" in str(e) else ""
        return ToolResult(error=f"{tool} refused: {e}.{waits}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{tool} could not run the scenario: {e}")
    ev = r.evidence
    _audit(ctx, "proforma", "run", "open", sid, {"artifactId": r.artifactId, "evidenceId": ev.id, "tool": tool,
                                                  "note": note})
    tea = r.tea
    return ToolResult(
        summary={
            "state": "open",
            "scenarioId": sid,
            "flowsheet": r.flowsheet,
            "artifactId": r.artifactId,
            "evidenceId": ev.id,
            "provenance": r.provenance,
            "median": ev.value,
            "interval": ev.interval.model_dump() if ev.interval else None,
            "basePrice": r.basePrice,
            "unit": r.priceBasis,
            "samples": r.samples,
            "feasible": r.feasible,
            "infeasible": r.infeasible,
            "inputs": [{"key": i.key, "label": i.label, "binding": i.binding, "records": len(i.recordIds),
                        "source": i.source.kind if i.source else None} for i in r.inputs],
            "costLines": [{"key": ln.key, "label": ln.label, "perUnit": ln.perUnit} for ln in tea.lines] if tea else [],
            "streams": len(r.streams),
            "units": len(r.units),
            "leavesOut": r.leavesOut,
            "meaning": "the scenario ran as the service binds it and is kept as one run artifact in the open lane, "
                       "marked as the model's in the audit log; cite its price, a cost line or a recovery by the "
                       "evidence id; stream_table reads its streams and pureos_read its train",
        },
        evidence=[ev],
    )


def _proforma_run(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    return run_scenario("proforma_write", inp.target, inp.note, ctx)


# ── a simulation (OF-BLD-020 §3.4) ────────────────────────────────────────

SIM_WAITS = ("A named person types each waiting parameter in fermOS → Simulate under their reviewer name; a model "
             "never supplies one. Where a waiting parameter names a record field, records of that field can be named "
             "for it in recordsByParam. Say in gaps which parameters wait.")
# How each origin is said, in words: what bound the parameter, never its value.
BOUND_BY = {"fit": "a fit", "record": "records", "simulation": "a kept simulation", "assumption": "a named person",
            "convention": "a stated convention", "library-default": "the library's own default", "artifact": "an artifact"}
MAX_FLAG_CHARS = 300


def _bound_by(v: Any, named: set[str], fields_of: dict[str, str]) -> dict[str, Any]:
    """What bound one parameter, in words and counts: the records by how many
    and of which field, and whether they were named for it; a fit or a kept
    simulation by its artifact id; a convention by its word when it is one.
    Never a number of the parameter's, which the artifact holds."""
    line: dict[str, Any] = {"key": v.key, "origin": v.origin}
    src = v.source
    if v.origin == "record":
        n = len(v.recordIds)
        fields = sorted({fields_of[r] for r in v.recordIds if r in fields_of})
        line["records"] = n
        line["boundBy"] = (f"{n} record{'' if n == 1 else 's'}" + (f" of {' and '.join(fields)}" if fields else "")
                           + (", named for it" if v.key in named else ", found by the rule for the strain and sugar"))
    elif v.origin in ("fit", "simulation", "artifact"):
        line["boundBy"] = f"{BOUND_BY[v.origin]}, {src.id}" if src and src.id else BOUND_BY[v.origin]
        if v.origin == "fit" and v.identified is False:
            line["identified"] = False
    elif v.origin == "assumption":
        line["boundBy"] = f"{BOUND_BY['assumption']}, {v.overriddenBy}"
    elif v.origin == "waiting":
        line["boundBy"] = "nothing: this setting of the family does not read it"
    else:
        line["boundBy"] = BOUND_BY.get(v.origin, v.origin) + (f": {v.value}" if isinstance(v.value, str) else "")
    return line


def _simulation_evidence(r: Any) -> Any:
    """A kept simulation as the one `Evidence` a claim cites it by: its id is
    the artifact's, its value the product's titre at harvest as the artifact
    holds it, its provenance and basis the artifact's."""
    from .. import kinetics
    from ..models import Evidence

    state = kinetics.FAMILIES[r.family].product_state() if r.family in kinetics.FAMILIES else None
    who = r.strain or "every strain of the program's organism"
    on = f" on {r.sugar}" if r.sugar else ""
    made = r.product or "product"
    value: float | str = r.finalTitre if r.finalTitre is not None else "no product state"
    return Evidence(id=r.artifactId, label=f"{r.title} simulation ({r.family}) of {who}{on}: the {made} titre at harvest",
                    value=value, unit=(r.units.get(state, "") if state else ""), provenance=r.provenance,
                    basis=r.basis, figure="trajectory")


def _summary_flags(r: Any) -> list[str]:
    """The simulation's flags as the summary says them (OF-BLD-020 §3.R,
    finding 20): a value outside its bounds by its key alone, never the
    value or its ends, which the artifact holds with the bounds and their
    reason; any other flag whole, or cut at a sentence or clause under
    MAX_FLAG_CHARS and said to be cut; each ending at a full stop."""
    outside = {v.outOfBounds: v.key for v in [*r.parameters, *r.start] if v.outOfBounds}
    out = []
    for f in r.flags:
        if f in outside:
            f = (f"{outside[f]} lies outside its bounds; it is kept as given, and the artifact holds the value, its "
                 "bounds and their reason")
        elif len(f) > MAX_FLAG_CHARS:
            head = f[:MAX_FLAG_CHARS]
            at = max(head.rfind(". "), head.rfind("; "))
            head = head[:at] if at > 0 else head[:head.rfind(" ")]
            f = head.rstrip(" ,;:.") + " (cut here; the artifact holds the whole flag)"
        f = f.rstrip()
        out.append(f if f.endswith(".") else f"{f}.")
    return out


def _sig(x: Any) -> Any:
    """A number of the end state to four significant digits, for the summary
    alone; the artifact holds every number whole."""
    return float(f"{x:.4g}") if isinstance(x, float) else x


def run_simulation(tool: str, req: Any, note: str, ctx: ToolContext) -> ToolResult:
    """Simulate one model family as the service binds it, keep it and mark it
    as the model's (OF-BLD-020 §3.4). The request carries ids and words: a
    family, a strain, a product, a sugar, the records named for a parameter,
    a fit, a start and a run-length preset; the service holds no person's
    assumption (they live in the browser's Durable tier), so none is passed:
    a parameter nothing binds waits, and the refusal is fermos.simulate's own
    words (what `POST /api/fermos/simulate` answers with a 422)."""
    from .. import fermos, kinetics, programs

    family = (req.family or "").strip()
    if not family:
        return ToolResult(error=f"{tool} refused: name the model family to simulate by its id ({', '.join(kinetics.FAMILIES)})")
    fam = kinetics.FAMILIES.get(family)
    if fam is not None and not ctx.include_archived:
        try:
            hidden = programs.hides(fam.program, False)
        except FileNotFoundError:  # no projection here: nothing is known to be archived
            hidden = False
        if hidden:
            p = programs.program_by_id(fam.program)
            return ToolResult(error=f"{tool} refused: {family} belongs to {p.name if p else fam.program}, archived "
                                    f"(hidden). {programs.SWITCH}")
    try:
        refused = programs.archived_refusal(tool, [("strain", req.strain or ""), ("product", req.product or "")],
                                            ctx.include_archived)
    except FileNotFoundError:
        refused = None
    if refused:
        return ToolResult(error=refused)
    req = req.model_copy(update={"family": family, "includeArchived": ctx.include_archived, "overrides": []})
    try:
        r = fermos.simulate(req, by_pool=ctx.pool)
    except fermos.SimulationRefused as e:
        waits = f" {SIM_WAITS}" if "cannot run yet" in str(e) else ""
        return ToolResult(error=f"{tool} refused: {str(e).rstrip('.')}.{waits}")
    ev = _simulation_evidence(r)
    _audit(ctx, "fermos", "simulate", "open", family, {"artifactId": r.artifactId, "evidenceId": ev.id, "tool": tool,
                                                       "strain": r.strain, "product": r.product, "sugar": r.sugar,
                                                       "note": note})
    ceiling = r.ceiling
    # Which keys the request named records for, as the basis says (`<key>
    # origin`), and each bound record's field, from the pool it was bound on.
    named = {i.name.rsplit(" ", 1)[0] for i in r.basis.inputs
             if i.name.endswith(f" {fermos.ORIGIN}") and i.value == fermos.NAMED}
    by_id = getattr(ctx.pool, "records_by_id", None) or {}
    fields_of = {rid: str(by_id[rid].get("field") or "") for v in [*r.parameters, *r.start] for rid in v.recordIds
                 if rid in by_id}
    return ToolResult(
        summary={
            "state": "open",
            "artifactId": r.artifactId,
            "evidenceId": ev.id,
            "family": r.family,
            "title": r.title,
            "strain": r.strain,
            "product": r.product,
            "sugar": r.sugar,
            "provenance": r.provenance,
            "parameters": [_bound_by(v, named, fields_of) for v in r.parameters],
            "start": [_bound_by(v, named, fields_of) for v in r.start],
            "end": {"finalTitre": _sig(r.finalTitre), "yieldAchieved": _sig(r.yieldAchieved),
                    "productivity": _sig(r.productivity), "harvestH": _sig(r.harvestH),
                    "sugarRunsOutH": _sig(r.sugarRunsOutH), "aerobic": r.aerobic, "units": r.units,
                    "read": "from the artifact, to four significant digits; cite the evidence id, never the number"},
            "ceiling": ({"rows": [{"modelId": c.modelId, "above": c.above, "words": c.words} for c in ceiling.rows],
                         "flagged": ceiling.flagged, "empty": ceiling.empty} if ceiling else None),
            "massBalanceCloses": r.massBalance.ok,
            "flags": _summary_flags(r),
            "meaning": "the family ran as the service binds it and is kept as one simulation artifact in the open lane, "
                       "marked as the model's in the audit log; each parameter says what bound it, and its value is in "
                       "the artifact. Its numbers are read from the artifact, never stated: cite the simulation by the "
                       "evidence id, which is its artifact id; fermos_read reads it again as kind simulation",
        },
        evidence=[ev],
    )


def _fermos_simulate(inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    """`fermos_write`'s `simulate`: the family in `target`, the rest in
    `fields` as words, a parameter's records as `records.<key>`, their ids
    separated by commas or spaces; any other field is refused, never passed
    on and never guessed at."""
    from ..models import SimulationRequest

    words = ("strain", "product", "sugar", "fitArtifact", "startFrom", "durationPreset")
    unknown = [k for k in inp.fields if k not in words and not (k.startswith("records.") and k[len("records."):])]
    if unknown:
        return ToolResult(error=f"fermos_write refused simulate: {', '.join(unknown)} "
                                f"{'is' if len(unknown) == 1 else 'are'} not a field of it; the fields are "
                                f"{', '.join(words)} and records.<parameter key>")
    f = {k: (v or "").strip() for k, v in inp.fields.items()}
    preset = f.get("durationPreset") or "until-sugar-runs-out"
    if preset not in ("until-sugar-runs-out", "fit-length"):
        return ToolResult(error=f"fermos_write refused simulate: durationPreset is until-sugar-runs-out or fit-length; "
                                f"{preset!r} is neither")
    named = {k[len("records."):]: [x for x in v.replace(",", " ").split() if x] for k, v in f.items()
             if k.startswith("records.")}
    req = SimulationRequest(family=inp.target, strain=f.get("strain") or None, product=f.get("product") or None,
                            sugar=f.get("sugar") or None, fitArtifact=f.get("fitArtifact") or None,
                            startFrom=f.get("startFrom") or "records", durationPreset=preset, recordsByParam=named)
    return run_simulation("fermos_write", req, inp.note, ctx)


# ── a train a model builds (OF-BLD-020 §5.4, D9, D13) ─────────────────────
#
# pureos_build and pureos_write's train actions are one function an action
# here. A model's train is kept on the service by pureos.kept.keep_train, the
# store's one write, under its locks; the change is pureos.build's, worked out
# from the train as it stands. A run is pureos.train_spec.run_train, with no
# person's value (the service holds none), so a value nothing binds waits and
# the call returns the refusal's words.

TRAIN_WAITS = ("A named person types each waiting value in pureOS → Builder under their reviewer name; a model never "
               "supplies one. Where a waiting parameter binds from a record field, set_from_record names records for "
               "it. Say in gaps which values wait.")
KEPT_MEANING = ("the train is kept on the service as the model's, marked so in the audit log; it holds ids and words, "
                "every value binds at the run from the records, the class's own default or a named person; toRun says "
                "in words what still stops it running")


def _kept_result(tool: str, action: str, k: Any, note: str, ctx: ToolContext, said: dict[str, Any] | None = None
                 ) -> ToolResult:
    from ..pureos import build

    _audit(ctx, "pureos", action, "open", k.spec.id, {"tool": tool, "note": note, **(said or {})})
    return ToolResult(summary={"state": "open", **build.described(k), **(said or {}), "meaning": KEPT_MEANING})


def _train_refused(tool: str, e: Exception) -> ToolResult:
    return ToolResult(error=f"{tool} refused: {str(e).rstrip('.')}.")


def new_train(tool: str, product: str, inlet_ref: str, note: str, ctx: ToolContext) -> ToolResult:
    """A new train, no unit yet, for a product from the inlet a kept
    artifact gives; kept as the model's (pureos_build new, pureos_write
    new_train)."""
    from ..pureos import build, kept

    try:
        spec, said = build.new_spec(product, inlet_ref, ctx.include_archived)
    except build.BuildRefused as e:
        return _train_refused(tool, e)
    model, effort = _who(ctx)
    try:
        k = kept.keep_train(None, lambda _: spec, model, ask_id=getattr(ctx, "ask_id", None) or None, effort=effort)
    except kept.KeptTrainRefused as e:
        return _train_refused(tool, e)
    return _kept_result(tool, "new_train", k, note, ctx, {"read": said})


def add_unit(tool: str, train_id: str, unit_type: str, after: str, note: str, ctx: ToolContext) -> ToolResult:
    """A unit of a catalogue type added to a kept train, after the unit
    named (pureos_build add_unit, pureos_write add_unit)."""
    from ..pureos import build, kept

    made: list[str] = []

    def change(cur: Any) -> Any:
        spec, uid = build.with_unit(cur, unit_type, after)
        made.append(uid)
        return spec

    model, effort = _who(ctx)
    try:
        build.kept_or_refuse(train_id)
        k = kept.keep_train(train_id.strip(), change, model, ask_id=getattr(ctx, "ask_id", None) or None, effort=effort)
    except (build.BuildRefused, kept.KeptTrainRefused) as e:
        return _train_refused(tool, e)
    return _kept_result(tool, "add_unit", k, note, ctx, {"added": made[-1]})


def remove_unit(tool: str, train_id: str, unit_id: str, note: str, ctx: ToolContext) -> ToolResult:
    """A unit taken out of a kept train (pureos_build remove_unit,
    pureos_write remove_unit)."""
    from ..pureos import build, kept

    model, effort = _who(ctx)
    try:
        build.kept_or_refuse(train_id)
        k = kept.keep_train(train_id.strip(), lambda cur: build.without_unit(cur, unit_id), model,
                            ask_id=getattr(ctx, "ask_id", None) or None, effort=effort)
    except (build.BuildRefused, kept.KeptTrainRefused) as e:
        return _train_refused(tool, e)
    return _kept_result(tool, "remove_unit", k, note, ctx, {"removed": unit_id.strip()})


def set_from_record(tool: str, train_id: str, unit_id: str, records_by_param: dict[str, list[str]], note: str,
                    ctx: ToolContext) -> ToolResult:
    """A unit's parameters bound to exactly the records named for each, held
    to the run's own check (pureos_build set_from_record, pureos_write
    set_from_record). The check reads the class's parameters in the Proforma
    worker, so it runs with the store let go; the train is kept only if it
    did not change meanwhile."""
    from ..pureos import build, kept
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        base = build.kept_or_refuse(train_id).spec
        spec, bound = build.with_records(base, unit_id, records_by_param, ctx.pool, ctx.include_archived)
    except build.BuildRefused as e:
        return _train_refused(tool, e)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{tool} could not read unit {unit_id}'s parameters from the Proforma simulator, where "
                                f"BioSTEAM runs: {e}")

    def change(cur: Any) -> Any:
        if cur != base:
            raise build.BuildRefused(f"train {base.id} changed while its records were checked; ask again")
        return spec

    model, effort = _who(ctx)
    try:
        k = kept.keep_train(base.id, change, model, ask_id=getattr(ctx, "ask_id", None) or None, effort=effort)
    except (build.BuildRefused, kept.KeptTrainRefused) as e:
        return _train_refused(tool, e)
    return _kept_result(tool, "set_from_record", k, note, ctx, {"unit": unit_id.strip(), "bound": bound})


def run_train(tool: str, train_id: str, note: str, ctx: ToolContext) -> ToolResult:
    """Run a kept train in the Proforma worker as the service binds it and
    keep the run as one `pureos.train_run` artifact (pureos_build run,
    pureos_write run_train). The service holds no person's value, so none is
    passed: a value nothing binds waits, and the refusal is run_train's own
    words (what `POST /api/pureos/train/run` answers with a 422). Returns the
    run as one Evidence whose id is the artifact's, a summary a model reads,
    and the whole run in `data`, which no model reads."""
    from .. import artifacts
    from ..pureos import build, train_spec
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        k = build.kept_or_refuse(train_id)
    except build.BuildRefused as e:
        return _train_refused(tool, e)
    try:
        r = train_spec.run_train(k.spec, None, None, ctx.include_archived)
    except train_spec.TrainRefused as e:
        waits = f" {TRAIN_WAITS}" if " waits" in str(e) else ""
        return ToolResult(error=f"{tool} refused: {str(e).rstrip('.')}.{waits}")
    except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged) as e:
        return ToolResult(error=f"{tool} refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{tool} could not run the train: {e}")
    ev = build.run_evidence(r)
    _audit(ctx, "pureos", "run_train", "open", k.spec.id, {"artifactId": r.artifactId, "evidenceId": ev.id, "tool": tool,
                                                            "note": note})
    return ToolResult(
        summary={"state": "open", **build.run_summary(r), "evidenceId": ev.id,
                 "meaning": "the train ran as the service binds it in the Proforma worker, where BioSTEAM builds it, and "
                            "the run is kept as one artifact in the open lane, marked as the model's in the audit log; "
                            "its numbers are read from the artifact, never stated: cite a recovery or a purity by the "
                            "evidence id, which is its artifact id; pureos_read reads it again as kind train-run"},
        evidence=[ev], data=r.model_dump(mode="json"))


def _proposal(got: Any) -> tuple[Any, list[Any]]:
    """The train and its reasons from what OF-BLD-020 §7.2's proposer
    returns: a pair, or one object carrying `train` (or `spec`) and
    `reasons`."""
    from ..models import TrainSpec

    if isinstance(got, tuple) and len(got) == 2:
        spec, reasons = got
    else:
        spec = getattr(got, "train", None) or getattr(got, "spec", None)
        reasons = getattr(got, "reasons", None) or []
    if spec is None:
        raise ValueError("the proposer returned no train")
    return TrainSpec.model_validate(spec.model_dump() if hasattr(spec, "model_dump") else spec), list(reasons or [])


def propose_train(tool: str, product: str, host: str, inlet_ref: str, note: str, ctx: ToolContext) -> ToolResult:
    """A train proposed by OF-BLD-020 §7.2's rules (`pureos.propose`) for a
    product made in a host, kept as the model's under an id of its own
    (pureos_build propose). A proposal that proposes nothing is refused in
    the words naming each missing property; the proposer's own refusals
    (an unknown product or host, an archived program with the switch off, a
    bad inlet) come back in its words."""
    from .. import artifacts
    from ..pureos import build, kept
    from ..pureos import propose as proposer
    from ..pureos.proposer import ProposeRefused, ProposeUnknown
    from ..workers import WorkerCrashed, WorkerError, WorkerTimeout

    try:
        got = proposer((product or "").strip(), (host or "").strip(), (inlet_ref or "").strip() or None,
                       include_archived=ctx.include_archived)
    except (ProposeUnknown, ProposeRefused, artifacts.ArtifactDamaged) as e:
        return _train_refused(tool, e)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{tool} could not ask thermosteam for the properties the proposer reads: {e}")
    if getattr(got, "train", None) is None:
        missing = "; ".join(f"{m.property}: {m.why}" for m in getattr(got, "missing", []) or []) or "no rule applies"
        return ToolResult(error=f"{tool} refused propose: the rules propose no train for {product} made in {host}, "
                                f"because {missing}. Nothing was kept. Say so in gaps.")
    try:
        spec, reasons = _proposal(got)
    except (ValueError, LookupError) as e:
        return _train_refused(tool, e)
    spec = spec.model_copy(update={"id": build.new_id()})
    model, effort = _who(ctx)
    try:
        k = kept.keep_train(None, lambda _: spec, model, ask_id=getattr(ctx, "ask_id", None) or None, effort=effort)
    except kept.KeptTrainRefused as e:
        return _train_refused(tool, e)
    words = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in reasons]
    return _kept_result(tool, "propose_train", k, note, ctx, {"reasons": words})


def _pureos(action: str, inp: ModuleWriteInput, ctx: ToolContext) -> ToolResult:
    """`pureos_write`'s train actions: the train in `target` (empty for
    new_train), the rest in `fields` as words; a parameter's records as
    `records.<key>`, their ids separated by commas or spaces. A field the
    action does not take is refused, never passed on and never guessed at."""
    f = {k: (v or "").strip() for k, v in inp.fields.items()}
    takes = [n for n in ACTIONS["pureos"][action][1] if n != "records.<key>"]
    unknown = [k for k in f if k not in takes and not (action == "set_from_record" and k.startswith("records.")
                                                       and k[len("records."):])]
    if unknown:
        listed = ", ".join(ACTIONS["pureos"][action][1]) or "none"
        return ToolResult(error=f"pureos_write refused {action}: {', '.join(unknown)} "
                                f"{'is' if len(unknown) == 1 else 'are'} not a field of it; its fields are {listed}")
    name, target = "pureos_write", inp.target.strip()
    if action == "new_train":
        return new_train(name, f.get("product", ""), f.get("inletRef", ""), inp.note, ctx)
    if action == "add_unit":
        return add_unit(name, target, f.get("unitType", ""), f.get("afterUnitId", ""), inp.note, ctx)
    if action == "remove_unit":
        return remove_unit(name, target, f.get("unitId", ""), inp.note, ctx)
    if action == "set_from_record":
        named = {k[len("records."):]: [x for x in v.replace(",", " ").split() if x] for k, v in f.items()
                 if k.startswith("records.")}
        return set_from_record(name, target, f.get("unitId", ""), named, inp.note, ctx)
    return run_train(name, target, inp.note, ctx)


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
            seed = f" {NO_WRITE[module]}." if module in NO_WRITE else f" {SEED_NOTE[module]}." if module in SEED_NOTE else ""
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
            return _fermos(action, inp, ctx)
        if module == "pureos":
            return _pureos(action, inp, ctx)
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
    seed = (f" {NO_WRITE[module]}: every other call is refused in words." if module in NO_WRITE else
            f" {SEED_NOTE[module]}: every other call is refused in words." if module in SEED_NOTE else "")
    return (f"Write to {label}, through the module's own write function. Actions — " + "; ".join(lines) + f".{seed} "
            "Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane "
            "marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.")


TOOLS = {
    module: register(Tool(name=f"{module}_write", description=_description(module), input_model=ModuleWriteInput,
                          run=_runner(module), strict=False))
    for module in module_stores.MODULES
}
