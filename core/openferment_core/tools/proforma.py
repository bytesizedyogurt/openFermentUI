"""Proforma's tools: `selling_price` (OF-BLD-014 §8.5), `run_flowsheet` and
`stream_table` (OF-BLD-019 §6.1).

`selling_price`: the price a person's run produced.

Ids in: a scenario id, any of the seed's BioSTEAM scenarios the program
switch shows (`proforma.seed_scenarios`: sc-yeast-1 with it off; sc-pha-1
too with it on, OF-BLD-019 §6.R). The most recent run artifact of that
scenario (`proforma.latest_run`) comes back as one `Evidence` with the hint
`distribution`: the median price and its 5th to 95th percentile, with the
run's provenance, which is `demo` while any input rests on an assumption;
what the flowsheet leaves out is read from the run's flowsheet on the shelf.
With no run on file, the tool refuses, names the inputs still waiting for a
source as the service binds them (`proforma.bound`), and says how a run is
made. It never runs a scenario and never makes an assumption: both are a
person's, in Proforma.

`proforma_benchmark` names the benchmark instead (§8.2): the NREL 2011 corn
stover ethanol design as `biorefineries.cornstover` builds it, with every
setting the package's own. Its stored run comes back as one `Evidence`, the
price per gallon; with none stored the tool refuses. It runs nothing here
either: a person runs the benchmark in Proforma → BioSTEAM.

`run_flowsheet` takes a scenario id and nothing else, and runs the scenario
as the service binds it: a free write through `proforma.run` (compute, no
model money), kept as one `proforma.run` artifact in the open lane and
audited with the model as its agent. It is at no gate. The service holds no
person's assumption, so an input no record binds waits, and the refusal is
`proforma.run`'s own words, the ones `POST /api/proforma/run` answers with a
422. The run itself is `tools/writes.py`'s `run_scenario`, which
`proforma_write`'s `run` action calls too, so `check:tools` reads the one
call to `proforma.run` there.

`stream_table` reads a kept run's stream table: a `proforma.run` artifact
(a scenario's run) or a `proforma.reference` artifact (a reference
biorefinery's, §2.2), through `proforma.tables_of`. The summary is the table
cut to the cap (the plant's feeds and products first), saying how many
streams it left out; the whole table rides in `ToolResult.data`, for the
endpoint and the MCP server. Both tools return the run as one `Evidence`
whose id is the artifact's, so a claim cites the run by it as it cites a
ceiling: the median price of a scenario's run, or the price a reference
biorefinery's package gives on its own defaults.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .. import programs, proforma
from ..models import Evidence, ToolResult
from . import MAX_SUMMARY_CHARS, Tool, ToolContext, register

NAME = "selling_price"
RUN_NAME = "run_flowsheet"
TABLE_NAME = "stream_table"


def _priced() -> list[str]:
    """The seed's BioSTEAM scenarios a description may name: none an
    archived program holds and no example (OF-BLD-016 §2.R, §3.3); none when
    the projection is missing."""
    return programs.offered("scenario", [s["id"] for s in proforma.seed_scenarios() if not s.get("example")])


# Named in the schema: an archived scenario never is; with the switch off
# `_run` refuses it.
_PRICED = _priced()


class SellingPriceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarioId: str = Field(description=(
        "A seed BioSTEAM scenario's id" + (f" ({', '.join(_PRICED)})" if _PRICED else "")
        + ", whose newest kept run it reads; or "
        + f"{proforma.BENCHMARK}, the NREL 2011 corn stover ethanol design as biorefineries.cornstover builds it."))


def _benchmark() -> ToolResult:
    art = proforma.stored_benchmark()
    if art is None:
        return ToolResult(error=f"{NAME} refused: the benchmark has not been run on this service. A person runs it in Proforma → BioSTEAM.")
    ev = proforma.benchmark_evidence(art)
    o = art.output
    return ToolResult(
        summary={
            "evidenceId": ev.id,
            "value": ev.value,
            "unit": ev.unit,
            "provenance": ev.provenance,
            "package": o.get("package"),
            "simulator": o.get("biosteam"),
            # The package's financial settings stay in the artifact; named here
            # in words, so a claim names them and cites the evidence.
            "settings": "the package's own: rate of return, income tax, operating days, and the start and end years, as stored with the artifact",
            "references": o.get("references"),
            "meaning": "the price at which the modelled corn stover ethanol plant breaks even, from the package's own settings; "
                       "a cellulosic design, not a batch fermentation of glucose",
        },
        evidence=[ev],
    )


def _not_held(sid: str, ctx: ToolContext) -> str:
    """An id that is no seed BioSTEAM scenario, refused in words: an authored
    cost surface keeps no run; anything else lives in the browser that made
    it, or nowhere. Names the ids it takes that the switch shows."""
    from .. import pureos
    from ..flowsheets import shelf

    authored = next((s for s in pureos.seed_scenarios() if s.get("id") == sid and s.get("kind") != "biosteam"), None)
    if authored is not None:
        return (f"{NAME} refused: {sid} is an authored cost surface, not a BioSTEAM scenario; no run of it is kept, and "
                "its numbers are the cost model's own")
    reference = shelf.SHELF.get(sid)
    if reference is not None and reference.reference:
        return (f"{NAME} refused: {sid} is a reference biorefinery, not a scenario: proforma_read lists its kept runs, "
                "and stream_table returns a run's evidence id, the price its package gives on its own defaults; the "
                f"corn stover benchmark's stored run is read here as {proforma.BENCHMARK}")
    held = [s["id"] for s in proforma.seed_scenarios()]
    shown = held if ctx.include_archived else programs.offered("scenario", held)
    return (f"{NAME} refused: {sid} is not a scenario this service holds. A scenario made with New scenario lives in "
            "the browser that made it, and its runs are read on its page in Proforma; the ids it takes are "
            f"{', '.join([*shown, proforma.BENCHMARK])}")


def _no_run(sid: str, seed: dict, ctx: ToolContext) -> str:
    """No run of a seed scenario on file: which inputs wait for a source as
    the service binds them now, and how a run is made. Nothing runs."""
    name = seed.get("name") or sid
    try:
        bound = proforma.bound(seed["modelId"], scenario_id=sid, name=name, pool=ctx.pool)
    except proforma.ScenarioRefused as e:
        return f"{NAME} refused: no run of {sid} is on file here, and its inputs could not be bound: {e}"
    waiting = [f"{i.key} ({i.label})" for i in bound.inputs if i.binding == "waiting"]
    if waiting:
        why = f"these inputs wait for a source, a record or a named person's assumption: {', '.join(waiting)}"
        how = (f"A run is made in Proforma, on the page of {name}: a named person's assumption is kept there for each "
               "input that waits, and the person runs it")
    else:
        why = "every input has a source as the service binds it, and nobody has run it"
        how = f"A person runs it in Proforma, on the page of {name}, or run_flowsheet runs it as the service binds it"
    return f"{NAME} refused: no run of {sid} is on file here; {why}. {how}. {NAME} reads the newest kept run and runs nothing"


def _run(inp: SellingPriceInput, ctx: ToolContext) -> ToolResult:
    from ..flowsheets import shelf

    sid = inp.scenarioId.strip()
    if sid == proforma.BENCHMARK:
        return _benchmark()
    if not sid:
        return ToolResult(error=f"{NAME} refused: name the scenario by its id (proforma_read lists them), or "
                                f"{proforma.BENCHMARK}")
    try:
        refused = programs.archived_refusal(NAME, [("scenario", sid)], ctx.include_archived)
    except FileNotFoundError:  # no projection here: nothing is known to be archived
        refused = None
    if refused:
        return ToolResult(error=refused)
    seed = {s["id"]: s for s in proforma.seed_scenarios()}.get(sid)
    if seed is None:
        return ToolResult(error=_not_held(sid, ctx))
    if seed.get("example") and not ctx.include_archived:
        # An example hides with the archive (OF-BLD-016 §3.3), as Proforma's scenario list hides it.
        return ToolResult(error=f"{NAME} refused: {sid} is an example, hidden with the archived programs. {programs.SWITCH}")
    art = proforma.latest_run(sid)
    if art is None:
        return ToolResult(error=_no_run(sid, seed, ctx))
    try:
        ev = proforma.evidence_of(art)
    except proforma.ScenarioRefused as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    # What the run ran, read from the run; the seed's flowsheet when the run
    # names none the shelf holds (a run is kept on its scenario's own).
    flowsheet = proforma.tables_of(art).flowsheet or seed["modelId"]
    try:
        info = shelf.info(flowsheet)
    except shelf.NotOnShelf:
        flowsheet, info = seed["modelId"], shelf.info(seed["modelId"])
    o = art.output
    assumed = sorted({i.name.split(" ")[0] for i in art.inputs if i.source.kind == "assumption"})
    return ToolResult(
        summary={
            "evidenceId": ev.id,
            "scenarioId": sid,
            "flowsheet": flowsheet,
            "median": ev.value,
            "interval": ev.interval.model_dump() if ev.interval else None,
            "unit": ev.unit,
            "provenance": ev.provenance,
            "feasible": o["feasible"],
            "samples": o["samples"],
            "infeasible": o["infeasible"],
            "assumedInputs": assumed,
            "leavesOut": info.leavesOut,
            "meaning": f"{info.title}: the minimum selling price across its inputs' ranges, from the newest run kept "
                       f"for {sid}",
        },
        evidence=[ev],
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "The minimum selling price the most recent kept run of a seed BioSTEAM scenario produced, as one evidence "
            "id to cite: the median with its 5th to 95th percentile, the infeasible share, which inputs rest on an "
            "assumption, and what the flowsheet leaves out. Refuses when no run is on file, naming the inputs still "
            "waiting for a source and how a run is made. With proforma_benchmark it returns the stored benchmark instead: the NREL 2011 "
            "corn stover ethanol design's minimum ethanol selling price as biorefineries.cornstover computes it. "
            "It cannot run a scenario or make an assumption."
        ),
        input_model=SellingPriceInput,
        run=_run,
    )
)


# ── run_flowsheet (OF-BLD-019 §6.1) ───────────────────────────────────────


def _biosteam_scenarios() -> list[str]:
    """The seed's BioSTEAM scenarios no archived program holds, for the
    description; none when the projection is missing."""
    from .. import pureos

    ids = [s["id"] for s in pureos.seed_scenarios() if s.get("kind") == "biosteam"]
    return programs.offered("scenario", ids)


# Named in the schema: an archived scenario never is (OF-BLD-016 §2.R).
_OFFERED = _biosteam_scenarios()


class RunFlowsheetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarioId: str = Field(description=(
        "The id of a BioSTEAM scenario the service holds" + (f" ({', '.join(_OFFERED)})" if _OFFERED else "")
        + "; proforma_read lists them. Nothing else: no value, no assumption, no setting."))


def _run_flowsheet(inp: RunFlowsheetInput, ctx: ToolContext) -> ToolResult:
    from .writes import run_scenario

    return run_scenario(RUN_NAME, inp.scenarioId, "", ctx)


RUN_TOOL = register(
    Tool(
        name=RUN_NAME,
        description=(
            "Run a BioSTEAM scenario's flowsheet as the service binds its inputs, and keep the run: one artifact "
            "holding the minimum selling price across the inputs' ranges, the cost breakdown, the sensitivity and "
            "the base case's stream, unit and utility tables. Returns one evidence id to cite (the run's artifact "
            "id), the median price with its 5th to 95th percentile, how each input is bound and the cost lines. "
            "Takes a scenario id and nothing else: you never type an assumption, a value or a setting. An input "
            "no record binds waits for a named person's assumption, typed in Proforma; the call then refuses and "
            "names the inputs that wait, and nothing runs. It spends no model money and is at no gate; the run "
            "is marked as yours in the audit log until a person promotes it. A run can take minutes."
        ),
        input_model=RunFlowsheetInput,
        run=_run_flowsheet,
        strict=False,
    )
)


# ── stream_table (OF-BLD-019 §6.1) ────────────────────────────────────────

# How many components a summary row names, largest first; the rest are counted.
TOP_COMPONENTS = 5
# Room the summary keeps under the cap for its own words.
HEADROOM = 400
EPS = 1e-9


class StreamTableInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifactId: str = Field(description=(
        "The artifact id of a kept Proforma run: a proforma.run artifact (a scenario's run, as run_flowsheet, "
        "selling_price or proforma_read return it) or a proforma.reference artifact (a reference biorefinery's "
        "run, as proforma_read lists it). Nothing else: no number, no stream, no setting."))


def _sig(v: Any) -> Any:
    """A flow, a temperature or a price to four significant digits, for the
    summary alone; `data` holds every number whole."""
    return float(f"{v:.4g}") if isinstance(v, float) else v


def run_evidence(art) -> Evidence | None:
    """A kept Proforma run as the one `Evidence` a claim cites it by, its id
    the artifact's: a scenario's run is its median price (`proforma.evidence_of`),
    a reference run the price its package gives on its own defaults. None
    when the run holds no price to cite."""
    from .. import artifacts
    from ..flowsheets import shelf

    if art.tool == proforma.RUN:
        try:
            return proforma.evidence_of(art)
        except proforma.ScenarioRefused:
            return None
    flowsheet = str(art.output.get("flowsheet") or next((i.value for i in art.inputs if i.name == "flowsheet"), ""))
    try:
        info = shelf.info(flowsheet)
    except shelf.NotOnShelf:
        return None
    value = art.output.get(info.priceOutput) if info.priceOutput else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return Evidence(id=art.id, label=f"{info.title}: the price {info.source} gives on the package's own defaults",
                    value=float(value), unit=info.priceBasis or "", provenance=art.provenance,
                    basis=artifacts.basis_of(art), figure=None)


def _row(s) -> dict[str, Any]:
    flows = sorted(((k, v) for k, v in s.massFlows.items() if v > EPS), key=lambda kv: -kv[1])
    row: dict[str, Any] = {"id": s.id, "from": s.source, "to": s.sink, "phase": s.phase, "T": _sig(s.T), "P": _sig(s.P),
                           "massFlow": _sig(s.massFlow), "components": {k: _sig(v) for k, v in flows[:TOP_COMPONENTS]}}
    if len(flows) > TOP_COMPONENTS:
        row["otherComponents"] = len(flows) - TOP_COMPONENTS
    if s.price is not None:
        row["price"] = _sig(s.price)
    return row


def _size(summary: dict[str, Any]) -> int:
    return len(json.dumps(summary, ensure_ascii=False, default=str))


def _stream_table(inp: StreamTableInput, ctx: ToolContext) -> ToolResult:
    from .. import artifacts, module_stores, pureos

    aid = inp.artifactId.strip()
    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        return ToolResult(error=f"{TABLE_NAME} refused: no kept artifact {aid!r}; proforma_read lists the runs on file")
    except artifacts.ArtifactDamaged as e:
        return ToolResult(error=f"{TABLE_NAME} could not read {aid}: {e}")
    if art.tool not in (proforma.RUN, proforma.REFERENCE):
        return ToolResult(error=f"{TABLE_NAME} refused: {aid} is a {art.tool} artifact, not a Proforma run; it reads the "
                                f"stream table of a {proforma.RUN} or {proforma.REFERENCE} artifact")
    # One rule for every reader of a run (OF-BLD-019 §6.R): hidden from
    # proforma_read, biorepo_read and pureOS's trains, refused here by id.
    refused = module_stores.hidden_run_refusal(TABLE_NAME, art, ctx.include_archived)
    if refused:
        return ToolResult(error=refused)
    scenario_id = pureos.scenario_of(art, pureos.seed_scenarios())[0] if art.tool == proforma.RUN else None
    t = proforma.tables_of(art)
    if not t.streams:
        return ToolResult(error=f"{TABLE_NAME} refused: run {aid} holds no stream table; a run kept before runs carried "
                                "their tables (or whose base case could not run) has none. Run the scenario again for one")
    # The plant's feeds and products first, then the streams between units,
    # each in the table's order: a cut never drops what enters or leaves.
    ordered = [s for s in t.streams if s.source is None or s.sink is None] + \
              [s for s in t.streams if s.source is not None and s.sink is not None]
    rows = [_row(s) for s in ordered]
    ev = run_evidence(art)
    units = {k: t.tableUnits[k] for k in ("T", "P", "massFlow", "price") if k in t.tableUnits}
    summary: dict[str, Any] = {
        "artifactId": art.id,
        "evidenceId": ev.id if ev else None,
        "tool": art.tool,
        "flowsheet": t.flowsheet,
        "scenarioId": scenario_id,
        "provenance": art.provenance,
        "tablesSource": t.tablesSource,
        "units": units,
        "streamCount": len(rows),
        "shown": len(rows),
        "leftOut": 0,
        "order": "the plant's feeds and products first, then the streams between units, each in the table's order; "
                 f"each stream's largest components by mass, at most {TOP_COMPONENTS}, the rest counted; numbers to "
                 "four significant digits",
        "streams": rows,
        "meaning": ("the base case's streams as BioSTEAM held them after the run, read from the kept artifact and never "
                    "simulated again; cite the run by its evidence id" if ev else
                    "the base case's streams as BioSTEAM held them after the run; this run holds no price, so it has "
                    "no evidence id to cite"),
    }
    budget = MAX_SUMMARY_CHARS - HEADROOM
    while _size(summary) > budget and summary["streams"]:
        summary["streams"] = summary["streams"][:-1]
        left = len(rows) - len(summary["streams"])
        summary["shown"], summary["leftOut"] = len(summary["streams"]), left
        summary["cut"] = (f"{left} of {len(rows)} streams left out to keep this summary under the "
                          f"{MAX_SUMMARY_CHARS} characters a model may read; the whole table rides in this result's "
                          "data, for the app and outside assistants, and in the artifact")
    data = {"artifactId": art.id, "tool": art.tool, "flowsheet": t.flowsheet, "tablesSource": t.tablesSource,
            "tableUnits": t.tableUnits, "streams": [s.model_dump(mode="json") for s in t.streams]}
    return ToolResult(summary=summary, evidence=[ev] if ev else [], data=data)


TABLE_TOOL = register(
    Tool(
        name=TABLE_NAME,
        description=(
            "Read the stream table a kept Proforma run holds: every stream of the base case with the unit it leaves "
            "and the unit it enters (none for a feed or a product), its phase, temperature, pressure, mass flow, "
            "price and largest components, as BioSTEAM held them after the run. Takes the run's artifact id and "
            "nothing else (a scenario's proforma.run artifact, or a reference biorefinery's proforma.reference "
            "artifact); you never type a number. The plant's feeds and products come first; a long table is cut to "
            "what a model may read and says how many streams it left out. Returns the run's evidence id to cite: a "
            "price, a cost or a recovery read from a run is cited by it. It runs nothing."
        ),
        input_model=StreamTableInput,
        run=_stream_table,
        strict=False,
    )
)
