"""Proforma's tools: `selling_price` (OF-BLD-014 §8.5), `run_flowsheet` and
`stream_table` (OF-BLD-019 §6.1).

`selling_price`: the price a person's run produced.

Ids in: a scenario id, any BioSTEAM scenario the project keeps
(`proforma.held_scenarios`, the ones made with New scenario). The most recent
run artifact of that
scenario (`proforma.latest_run`) comes back as one `Evidence` with the hint
`distribution`: the median price and its 5th to 95th percentile, with the
run's provenance, which is `assumed` while any input rests on an assumption;
what the flowsheet leaves out is read from the run's flowsheet on the shelf.
With no run on file, the tool refuses, names the inputs still waiting for a
source as the service binds them (`proforma.bound`), and says how a run is
made. It never runs a scenario and never makes an assumption: both are a
person's, in Proforma.

A plant of the library shelf, by its id, names its newest run on its
package's own values the project keeps (alpha 2.2 D8): the reference plants
`cornstover` (the NREL 2011 corn stover design, the benchmark the shelf's
retired entry ran) and `corn` (the dry-grind corn plant), or any plant
`engine_plants` lists. The product's selling price solved at the TEA's rate
of return comes back as one `Evidence`, the id `engine_report` gives the same
number (`<artifact id>:price.solvedPrice`), with how many of the package
test's values the run holds; with no such run kept the tool refuses, says
how one is made and names any run the project kept from a retired entry of
that plant. An id of a retired reference entry (`proforma_benchmark`,
`cornstover_benchmark`, `corn_drygrind`) answers as its library plant, and
the summary says so; when the project keeps no run of that plant on its
package's own values, it answers from the newest run the project kept from
the entry (the benchmark, or a reference run), its price as the entry named
it (`proforma.retired_evidence`), and the summary says the run was kept from
a retired entry. It runs nothing here either.

`run_flowsheet` takes a scenario id and nothing else, and runs the scenario
as its page runs it (`project_state.run_request`: the overrides a person set on
the page and the fermOS fits chosen for its inputs, read from the project's
rows): a free write through `proforma.run` (compute, no model money), kept as
one `proforma.run` artifact in the open lane and audited with the model as
its agent. It is at no gate. An input that neither a record nor a person's
override binds waits, and the refusal is `proforma.run`'s own words, the ones
`POST /api/proforma/run` answers with a 422. The run itself is `tools/writes.py`'s `run_scenario`, which
`proforma_write`'s `run` action calls too, so `check:tools` reads the one
call to `proforma.run` there.

`stream_table` reads a kept run's stream table: a `proforma.run` artifact
(a scenario's run), a `library.run` artifact (a library plant's run, alpha
2.2 D8) or a `proforma.reference` artifact kept from a retired reference
entry, through `proforma.tables_of`. The summary is the table
cut to the cap (the plant's feeds and products first), saying how many
streams it left out; the whole table rides in `ToolResult.data`, for the
endpoint and the MCP server. A scenario's run comes back as one `Evidence`
whose id is the artifact's, the median price, so a claim cites the run by it
as it cites a ceiling, and a reference run kept from a retired entry the same
way, the price its package gives on its own defaults; a library run's numbers
are cited by the ids `engine_report` names.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .. import proforma, project_state
from ..basis import ASSUMED_KINDS, SET_ORIGINS, is_measurement
from ..models import Evidence, ToolResult
from . import MAX_SUMMARY_CHARS, Tool, ToolContext, register

NAME = "selling_price"
RUN_NAME = "run_flowsheet"
TABLE_NAME = "stream_table"
# The runs whose stream table stream_table reads: a library plant's run among
# them (alpha 2.2 D8), whose tables the Proforma worker reads as a run's, and
# a run kept from a retired reference entry, read as kept.
TABLE_TOOLS = proforma.TABLE_TOOLS
LIBRARY_RUN = "library.run"
# The library plant an id of a retired reference entry names (alpha 2.2 D8).
RETIRED_IDS = {proforma.BENCHMARK: "cornstover", **proforma.RETIRED_PLANTS}


class SellingPriceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarioId: str = Field(description=(
        "The id of a BioSTEAM scenario the project keeps (proforma_read lists them), whose newest kept run it reads; "
        "or a plant of the library shelf by its id (engine_plants lists them: cornstover is the NREL 2011 corn stover "
        "design, corn the dry-grind corn plant), whose newest run on its package's own values it reads."))


def _sets_values(run) -> bool:
    """Whether a kept engine run set a value of its own: a person's
    assumption, a model's estimate or a deposition's reading."""
    return any(i.quantity.origin is not None and i.quantity.origin.kind in SET_ORIGINS for i in run.inputs)


def _library_price(plant: str, asked: str) -> ToolResult:
    """The newest run of a library plant on its package's own values the
    project keeps, its solved price as one Evidence (the id engine_report
    gives it); a refusal in words when none is kept or it holds no price."""
    from ..engine import library, runs
    from .engine import run_evidence as engine_evidence

    kept = [r for r in runs.listed(runs.LIBRARY_ENGINE)
            if r.tool == LIBRARY_RUN and r.plant == plant and r.status == "done" and r.artifactId
            and not _sets_values(r)]
    if not kept:
        retired = proforma.kept_from_retired(plant)
        if asked != plant and retired:
            return _retired_price(retired[0], plant, asked)
        held = ""
        if retired:
            entry = proforma.retired_entry_of(retired[0])
            held = (f" The project keeps {retired[0].tool} artifact {retired[0].id}, a run kept from the retired entry "
                    f"{entry}; {NAME} reads its price by the id "
                    f"{proforma.BENCHMARK if retired[0].tool == proforma.BENCHMARK else entry}.")
        return ToolResult(error=(
            f"{NAME} refused: no run of the library plant {plant} on its package's own values is kept in this "
            f"project. engine_run runs it (plant {plant}), and a person runs it in Proforma, on its reference card or "
            f"in Studies; {NAME} reads the newest kept run and runs nothing.{held}"))
    run = kept[0]  # listed newest first
    report = runs.report(run.id)
    found = {e.id.rsplit(":", 1)[-1]: e for e in engine_evidence(report)}
    ev = found.get("price.solvedPrice") or found.get("price.packagePrice")
    if ev is None:
        return ToolResult(error=(f"{NAME} refused: run {run.id} of the library plant {plant} holds no price: its plant "
                                 "carries no TEA here, or its TEA solved none (engine_report reads its numbers)"))
    o = report.artifact.output if report.artifact else {}
    price = o.get("price") or {}
    checks = [c for c in o.get("checks") or [] if isinstance(c, dict)]
    summary: dict[str, Any] = {
        "evidenceId": ev.id,
        "runId": run.id,
        "plant": plant,
        "configuration": run.configuration,
        "title": library.plant(plant).title,
        "value": ev.value,
        "unit": ev.unit,
        "product": price.get("product"),
        "provenance": ev.provenance,
        "packageTest": (f"{sum(1 for c in checks if c.get('within'))} of {len(checks)} values of the package's own "
                        "test within its tolerance on this run" if checks else
                        o.get("regressionNote") or "the package's test holds no values for this plant"),
        "meaning": (f"{ev.label}, on the package's own values, from the newest run of {plant} kept in this project; "
                    "engine_report reads the run's other numbers (its TEA breakdown, its outputs) as evidence ids"),
    }
    if asked != plant:
        summary["retired"] = (f"{asked} retired with the shelf's hand-written reference entries (alpha 2.2): it is the "
                              f"library plant {plant}, read here by that id")
    return ToolResult(summary=summary, evidence=[ev])


def _retired_price(art, plant: str, asked: str) -> ToolResult:
    """The price of the newest run the project kept from a retired reference
    entry of `plant`, as one Evidence whose id is the artifact's; a refusal
    in words when it holds none."""
    ev = proforma.retired_evidence(art)
    entry = proforma.retired_entry_of(art)
    if ev is None:
        return ToolResult(error=(f"{NAME} refused: {art.tool} artifact {art.id}, the newest run kept from the retired "
                                 f"entry {entry}, holds no price; the library plant {plant}'s run gives one (engine_run "
                                 f"runs it, plant {plant})"))
    o = art.output if isinstance(art.output, dict) else {}
    return ToolResult(
        summary={
            "evidenceId": ev.id,
            "artifactId": art.id,
            "tool": art.tool,
            "entry": entry,
            "plant": plant,
            "title": proforma.RETIRED[entry].title if entry else None,
            "value": ev.value,
            "unit": ev.unit,
            "provenance": ev.provenance,
            "package": o.get("package"),
            "simulator": o.get("biosteam"),
            "settings": "the package's own, as stored with the artifact",
            "references": o.get("references"),
            "keptAt": art.createdAt,
            "retired": (f"{asked} retired with the shelf's hand-written reference entries (alpha 2.2); this run was kept "
                        f"from the entry {entry} before it retired, and the project keeps no run of the library plant "
                        f"{plant} on its package's own values (engine_run runs one, plant {plant})"),
            "meaning": f"{ev.label}, from the newest run kept in this project from the retired entry {entry}",
        },
        evidence=[ev],
    )


def _not_held(sid: str, ctx: ToolContext) -> str:
    """An id that is no BioSTEAM scenario the project keeps and no plant of
    the library shelf, refused in words naming the ids it takes."""
    shown = [s["id"] for s in proforma.held_scenarios()]
    return (f"{NAME} refused: {sid} is no BioSTEAM scenario this project keeps and no plant of the library shelf; "
            f"the scenarios it takes are {', '.join(shown) or 'none yet'}, and a library plant by its id "
            "(engine_plants lists them)")


def _no_run(sid: str, row: dict, ctx: ToolContext) -> str:
    """No run of the scenario on file: which inputs wait for a source as its
    page binds them now (with the overrides a person set there and the fits
    chosen for it), and how a run is made. Nothing runs."""
    name = row.get("name") or sid
    try:
        req = project_state.run_request(row)
        flowsheet = req.flowsheet or row["modelId"]
        typed = proforma.named_values(sid, proforma.overrides_of(sid, flowsheet, req.inputs))
        bound = proforma.bound(flowsheet, scenario_id=sid, name=name, pool=ctx.pool,
                               assumptions=typed, fits=req.fits, vessel=req.vessel, train_run=req.trainRun)
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
    from ..engine import library
    from ..flowsheets import shelf

    sid = inp.scenarioId.strip()
    if not sid:
        return ToolResult(error=f"{NAME} refused: name the scenario by its id (proforma_read lists them), or a plant "
                                "of the library shelf by its id (engine_plants lists them)")
    row = {s["id"]: s for s in proforma.held_scenarios()}.get(sid)
    if row is None:
        plant = RETIRED_IDS.get(sid, sid)
        if any(p.id == plant for p in library.shelf().plants):
            return _library_price(plant, sid)
        return ToolResult(error=_not_held(sid, ctx))
    art = proforma.latest_run(sid)
    if art is None:
        return ToolResult(error=_no_run(sid, row, ctx))
    try:
        ev = proforma.evidence_of(art)
    except proforma.ScenarioRefused as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    # What the run ran, read from the run; the scenario's flowsheet when the
    # run names none the shelf holds (a run is kept on its scenario's own).
    flowsheet = proforma.tables_of(art).flowsheet or row["modelId"]
    try:
        info = shelf.info(flowsheet)
    except shelf.NotOnShelf:
        flowsheet, info = row["modelId"], shelf.info(row["modelId"])
    o = art.output
    assumed = sorted({i.name.split(" ")[0] for i in art.inputs if i.source.kind in ASSUMED_KINDS})
    # The inputs a deposition's reading set (basis.is_measurement, beside the assumed ones).
    measured = sorted({i.name.split(" ")[0] for i in art.inputs if is_measurement(i.source)})
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
            "measuredInputs": measured,
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
            "The minimum selling price the most recent kept run of one of the project's BioSTEAM scenarios produced, as one evidence "
            "id to cite: the median with its 5th to 95th percentile, the infeasible share, which inputs rest on an "
            "assumption and which on a deposition's reading, and what the flowsheet leaves out. Refuses when no run is on file, naming the inputs still "
            "waiting for a source and how a run is made. With a plant of the library shelf by its id (cornstover, the NREL 2011 "
            "corn stover design; corn, the dry-grind corn plant; any plant engine_plants lists) it reads that plant's newest kept "
            "run on its package's own values: the selling price its TEA solves, as the evidence id engine_report gives it, and "
            "how many of the package test's values the run holds. An id of a retired reference entry (proforma_benchmark, "
            "cornstover_benchmark, corn_drygrind) reads its library plant, or, when the project keeps no such run, the "
            "newest run the project kept from that entry, its price as the entry named it. "
            "It cannot run a scenario or make an assumption."
        ),
        input_model=SellingPriceInput,
        run=_run,
    )
)


# ── run_flowsheet (OF-BLD-019 §6.1) ───────────────────────────────────────


class RunFlowsheetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarioId: str = Field(description=(
        "The id of a BioSTEAM scenario the project keeps; proforma_read lists them. Nothing else: no value, no "
        "assumption, no setting."))


def _run_flowsheet(inp: RunFlowsheetInput, ctx: ToolContext) -> ToolResult:
    from .writes import run_scenario

    return run_scenario(RUN_NAME, inp.scenarioId, "", ctx)


RUN_TOOL = register(
    Tool(
        name=RUN_NAME,
        description=(
            "Run one of the project's BioSTEAM scenarios as its page runs it, and keep the run: one artifact "
            "holding the minimum selling price across the inputs' ranges, the cost breakdown, the sensitivity and "
            "the base case's stream, unit and utility tables. Returns one evidence id to cite (the run's artifact "
            "id), the median price with its 5th to 95th percentile, how each input is bound and the cost lines. "
            "Takes a scenario id and nothing else: you never type an assumption, a value or a setting. The run "
            "reads the assumptions a named person set on the scenario's page and the fermOS fits chosen for it; an "
            "input that neither a record nor such an assumption binds waits, and the call then refuses and "
            "names the inputs that wait, and nothing runs. It spends no model money and is at no gate; the run "
            "is marked as yours in the audit log until a person promotes it. A run can take minutes."
        ),
        input_model=RunFlowsheetInput,
        run=_run_flowsheet,
        strict=False,
        writes=True,
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
        "The artifact id of a kept run: a proforma.run artifact (a scenario's run, as run_flowsheet, "
        "selling_price or proforma_read return it), a library.run artifact (a library plant's run, as engine_run, "
        "engine_report and proforma_read name it), or a proforma.reference artifact kept from a retired reference "
        "entry. Nothing else: no number, no stream, no setting."))


def _sig(v: Any) -> Any:
    """A flow, a temperature or a price to four significant digits, for the
    summary alone; `data` holds every number whole."""
    return float(f"{v:.4g}") if isinstance(v, float) else v


def run_evidence(art) -> Evidence | None:
    """A kept run as the one `Evidence` a claim cites it by, its id the
    artifact's: a scenario's run its median price (`proforma.evidence_of`),
    a reference run kept from a retired entry the price its package gives on
    its own defaults, as the entry named it (`proforma.retired_evidence`).
    None for a run that holds no price to cite, and for a library run, whose
    numbers are cited by the ids engine_report names."""
    if art.tool == proforma.REFERENCE:
        return proforma.retired_evidence(art)
    if art.tool != proforma.RUN:
        return None
    try:
        return proforma.evidence_of(art)
    except proforma.ScenarioRefused:
        return None


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
    from .. import artifacts, pureos

    aid = inp.artifactId.strip()
    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        return ToolResult(error=f"{TABLE_NAME} refused: no kept artifact {aid!r}; proforma_read lists the runs on file, "
                                "the runs kept from the retired reference entries among them, and biorepo_read lists "
                                "every kept artifact")
    except artifacts.ArtifactDamaged as e:
        return ToolResult(error=f"{TABLE_NAME} could not read {aid}: {e}")
    if art.tool not in TABLE_TOOLS:
        return ToolResult(error=f"{TABLE_NAME} refused: {aid} is a {art.tool} artifact, and {TABLE_NAME} reads the "
                                f"stream table of a {proforma.RUN} or {LIBRARY_RUN} artifact, or of a "
                                f"{proforma.REFERENCE} artifact kept from a retired reference entry")
    scenario_id = pureos.scenario_of(art, pureos.held_scenarios())[0] if art.tool == proforma.RUN else None
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
                    "the base case's streams as BioSTEAM held them after the run, read from the kept artifact and never "
                    "simulated again; a library plant's run is cited by the evidence id engine_report names for each "
                    "of its outputs" if art.tool == LIBRARY_RUN else
                    "the base case's streams as BioSTEAM held them in a run kept from a reference entry that retired "
                    "from Proforma's shelf at alpha 2.2, read as kept; this run holds no price, and the library "
                    "plant's run of the same package (engine_run, then engine_report) gives the evidence ids to cite"
                    if art.tool == proforma.REFERENCE
                    else "the base case's streams as BioSTEAM held them after the run; this run holds no price, so it "
                         "has no evidence id to cite"),
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
            "nothing else (a scenario's proforma.run artifact or a library plant's library.run artifact, the corn "
            "stover and dry-grind corn reference plants' among them, or a proforma.reference artifact kept from a "
            "retired reference entry); you never type a number. The plant's feeds and products come first; a long "
            "table is cut to what a model may read and says how many streams it left out. A scenario's run and a "
            "kept reference run return their evidence id to cite, the run's price; a library plant's numbers are "
            "cited by the evidence ids engine_report names for its outputs. It runs nothing."
        ),
        input_model=StreamTableInput,
        run=_stream_table,
        strict=False,
    )
)
