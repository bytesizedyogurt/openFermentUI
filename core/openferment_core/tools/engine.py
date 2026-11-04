"""The library shelf and the project's engine runs, for Postdoc (alpha 2.0
stage 6; execution prompt §4.6, §9.1 step 6; ADR-004, ADR-006).

`engine_plants` lists what the shelf runs: the `biorefineries` plants with an
entry point and openFerment's own flowsheets, each with its configurations,
then the shelf's flowsheets a Proforma scenario runs (the biosteam engine's
things of kind `scenario`, alpha 2.2 D6); or, named, another engine's
things. Beside them it lists every engine registered here (`engines`), each
with its version, its worker's state, its last conformance verdict and the
ids of the project's runs it made, newest first, so one read says which
engines there are and which run came from each.
`engine_parameters` gives one plant's parameters as the package builds it
(the Proforma worker reads them): each key with its unit and the library's
default, the values a scenario sets are set against. `engine_run` runs a plant
at the library's defaults, or a study's scenario, as an engine run
(engine/runs.py) through `writes.run_engine`, which keeps it audited as its
caller's; `engine_report` reads a kept run back.

A RUN'S EVIDENCE. Each number its price block and its flowsheet's own outputs
hold, in its unit, and each line of its TEA breakdown, per unit of the price's
basis and per year, is one Evidence whose id is `<artifact id>:<block>.<key>`;
each output of a contract engine's run, of a kinetics run, of a train run
and of a Proforma scenario's run (its outputs.values) is one whose id is
`<artifact id>:values.<name>`. Each one's
basis is the run's artifact, its provenance the artifact's
(`assumed` when a value the run set is a person's assumption or a model's
estimate, `measured` when the values it set are deposited readings beside
records and defaults). `engine_report` also gives, by words, the parameters
the run read back from the plant (`<artifact id>:parameters.<key>`), each
with its origin: computed where the package set it, assumed where a person
or a model did, measured where a deposition's reading did. A claim cites
those ids, and a value a claim states is read from one by its id.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..basis import SET_ORIGINS
from ..models import CONFIGURATION_MAX, ComputedBasis, Evidence, RunReport, ToolResult
from . import Tool, ToolContext, register

MAX_ROWS = 40
# What each number of a run's price block is, in words (workers/library_plants.py's PRICE_UNITS).
PRICE_WORDS = {
    "solvedPrice": "the product's selling price solved at the TEA's rate of return",
    "packagePrice": "the product's price as the package sets it",
    "IRR": "the TEA's internal rate of return",
    "NPV": "the net present value at the package's prices",
    "TCI": "the total capital investment",
    "FCI": "the fixed capital investment",
    "installed_equipment_cost": "the installed equipment cost",
    "sales": "the yearly sales",
    "material_cost": "the yearly material cost",
    "utility_cost": "the yearly utility cost",
    "FOC": "the fixed operating cost",
    "VOC": "the variable operating cost",
    "feedstockKgPerH": "the feedstock's flow",
}


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def run_evidence(report: RunReport) -> list[Evidence]:
    """A kept run's numbers as evidence a claim may cite, each in its unit,
    on the run's artifact."""
    art, run = report.artifact, report.run
    if art is None:
        return []
    basis = ComputedBasis(tool=art.tool, toolVersion=art.toolVersion, inputs=art.inputs, artifactId=art.id,
                          at=art.createdAt, seed=art.seed)
    name = run.plant + (f" ({run.configuration})" if run.configuration else "")
    out: list[Evidence] = []
    price = art.output.get("price") or {}
    for key, unit in (price.get("units") or {}).items():
        if _number(price.get(key)):
            out.append(Evidence(id=f"{art.id}:price.{key}", label=f"{name}: {PRICE_WORDS.get(key, key)}",
                                value=price[key], unit=unit, provenance=art.provenance, basis=basis))
    units = art.output.get("outputUnits") or {}
    for key, value in (art.output.get("outputs") or {}).items():
        if _number(value) or isinstance(value, str):
            out.append(Evidence(id=f"{art.id}:outputs.{key}", label=f"{name}: {key}", value=value,
                                unit=units.get(key) or "", provenance=art.provenance, basis=basis))
    # A contract engine's outputs (docs/api/engines.md): each a name, a value and a unit.
    for v in art.output.get("values") or []:
        if isinstance(v, dict) and isinstance(v.get("name"), str) and (_number(v.get("value")) or isinstance(v.get("value"), str)):
            out.append(Evidence(id=f"{art.id}:values.{v['name']}", label=f"{name}: {v['name']}", value=v["value"],
                                unit=str(v.get("unit") or ""), provenance=art.provenance, basis=basis))
    # The kinetics engine's (fermos_engine.py), the train engine's (pureos/engine.py) and a Proforma scenario's
    # (proforma.py): each of the run's outputs.values, read from its artifact (engine/runs.py `values_of`).
    from ..engine import runs

    if art.tool in (runs.SIMULATION_TOOL, runs.FORECAST_TOOL, runs.VESSEL_TOOL, runs.TRAIN_TOOL, runs.PROFORMA_TOOL):
        for v in runs.values_of(art):
            q = v["quantity"]
            out.append(Evidence(id=f"{art.id}:values.{v['name']}", label=f"{name}: {v['name']}", value=q["value"],
                                unit=q["unit"], provenance=art.provenance, basis=basis))
    # The TEA's breakdown, line by line as the worker read it from BioSTEAM's TEA object.
    tea = art.output.get("tea") or {}
    per_unit = f"USD per {tea['basis']}" if tea.get("basis") else "USD per unit of the price's basis"
    annual = (art.output.get("tableUnits") or {}).get("annual") or "USD/yr"
    for line in tea.get("lines") or []:
        what = f"{name}: {line.get('label') or line.get('key')}, a line of the TEA's breakdown ({line.get('reads') or 'read from the TEA'})"
        if _number(line.get("perUnit")):
            out.append(Evidence(id=f"{art.id}:tea.{line['key']}", label=f"{what}, per unit of the price's basis",
                                value=line["perUnit"], unit=per_unit, provenance=art.provenance, basis=basis))
        if _number(line.get("usdPerYear")):
            out.append(Evidence(id=f"{art.id}:tea.{line['key']}.year", label=f"{what}, a year",
                                value=line["usdPerYear"], unit=annual, provenance=art.provenance, basis=basis))
    return out[:MAX_ROWS]


# What a parameter's origin is, in words, as a claim's label says it: each
# a ParamOrigin, the word a run's parameters (runs.parameters_of) give a
# value for where it came from.
ORIGIN_WORDS = {"library-default": "the package's own value", "assumption": "a person's assumption",
                "model-estimate": "a model's estimate", "measurement": "a deposition's reading",
                "record": "read from a record", "artifact": "read from an artifact"}
# The provenance a parameter's own evidence carries, by its ParamOrigin: a
# value a person or a model set is assumed, a deposition's reading measured,
# and the package's own value computed.
ORIGIN_PROVENANCE = {"assumption": "assumed", "model-estimate": "assumed", "measurement": "measured"}


def parameter_evidence(report: RunReport, words: str, limit: int) -> list[Evidence]:
    """The parameters a kept run read back from the plant whose key, label or
    group hold every one of `words`, as evidence on the run's artifact: computed
    where the package set the value, assumed where a person or a model did,
    measured where a deposition's reading did."""
    art, run = report.artifact, report.run
    held = report.parameters
    if hasattr(held, "model_dump"):
        held = held.model_dump(mode="json")
    if art is None or not isinstance(held, dict):
        return []
    basis = ComputedBasis(tool=art.tool, toolVersion=art.toolVersion, inputs=art.inputs, artifactId=art.id,
                          at=art.createdAt, seed=art.seed)
    name = run.plant + (f" ({run.configuration})" if run.configuration else "")
    specs = {sp.get("key"): sp for sp in held.get("specs") or [] if isinstance(sp, dict)}
    wanted = [w for w in words.lower().split() if w]
    out: list[Evidence] = []
    for v in held.get("values") or []:
        spec = specs.get(v.get("key")) or {}
        said = f"{v.get('key')} {spec.get('label', '')} {spec.get('group', '')}".lower()
        if (wanted and not all(w in said for w in wanted)) or not (_number(v.get("value")) or isinstance(v.get("value"), str)):
            continue
        origin = v.get("origin") or "library-default"
        source = (v.get("source") or {}).get("id")
        label = f"{name}: {spec.get('label') or v.get('key')}, {ORIGIN_WORDS.get(origin, origin)}" + (f" ({source})" if source else "")
        out.append(Evidence(id=f"{art.id}:parameters.{v.get('key')}", label=label, value=v["value"],
                            unit=spec.get("unit") or "", provenance=ORIGIN_PROVENANCE.get(origin, "computed"),
                            basis=basis))
        if len(out) >= limit:
            break
    return out


def run_result(report: RunReport, *, state: str = "open") -> ToolResult:
    """A kept run in a tool's words: the engine and the artifact tool that
    made it, what ran, on what values, and its numbers as evidence ids."""
    run = report.run
    if run.status == "refused":
        return ToolResult(summary={"runId": run.id, "engine": run.engine, "tool": run.tool, "plant": run.plant,
                                   "configuration": run.configuration, "status": "refused", "refused": run.refused,
                                   "scenarioId": run.scenarioId})
    evidence = run_evidence(report)
    own = [{"key": i.name, "value": i.quantity.value, "unit": i.quantity.unit, "origin": i.quantity.origin.kind,
            "by": i.quantity.origin.by, **({"reading": i.quantity.origin.ref} if i.quantity.origin.kind == "measurement"
                                           else {})}
           for i in run.inputs if i.quantity.origin is not None and i.quantity.origin.kind in SET_ORIGINS]
    return ToolResult(
        summary={
            "state": state,
            "runId": run.id,
            "artifactId": run.artifactId,
            "engine": run.engine,
            "tool": run.tool,
            "plant": run.plant,
            "configuration": run.configuration,
            "scenarioId": run.scenarioId,
            "provenance": run.provenance,
            "valuesSet": own,
            "evidence": [{"id": e.id, "label": e.label, "value": e.value, "unit": e.unit} for e in evidence],
            "sff": run.sff.model_dump(mode="json") if run.sff else None,
            "sffRefused": run.sffRefused,
            "packageTest": run.outputs.get("regression"),
            "by": run.by,
        },
        evidence=evidence,
    )


# ── engine_plants ───────────────────────────────────────────────────────


class EnginePlantsInput(BaseModel):
    engine: str = Field(default="biosteam", max_length=40, description=(
        "The engine whose things to list: biosteam, whose things are the library plants, openFerment's flowsheet "
        "and the shelf's scenario flowsheets, or any other the summary's `engines` names. Whichever is named, the "
        "summary lists every engine registered here with the ids of the project's runs each made."))
    words: str = Field(default="", max_length=200,
                       description="Words to narrow the shelf by: a product, a feedstock, a plant's name; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


# How many of an engine's runs the listing names by id, newest first; `runs` counts them all.
RUN_IDS = 20


def engines_listed() -> list[dict[str, Any]]:
    """Every engine registered here, in name order (GET /api/engines lists the
    same): its version, its worker and the worker's state, its last
    conformance verdict, and the project's runs it made (`runs`, how many;
    `runIds`, the newest RUN_IDS, newest first). An engine that cannot be
    used is listed with its words and its runs."""
    from ..engine import conform, registry, runs

    made = runs.made_by()
    out: list[dict[str, Any]] = []
    for name, found in sorted(registry.found().items()):
        ids = made.get(name, [])
        row: dict[str, Any] = {"name": name}
        if found.engine is None:
            row["error"] = found.error
        else:
            try:
                row["version"] = found.engine.version()
            except Exception as e:  # a version that cannot be read is said, and the engine still listed
                row["error"] = f"its version could not be read: {type(e).__name__}: {e}"
            row["worker"] = found.engine.worker
            row["workerStatus"] = registry.status_of(found.engine)
        verdict = conform.latest(name)
        row["conformance"] = (None if verdict is None else
                              {"ok": verdict.ok, "version": verdict.version, "by": verdict.by, "at": verdict.at})
        row["runs"] = len(ids)
        row["runIds"] = ids[:RUN_IDS]
        out.append(row)
    # The project's runs of an engine registered here no longer, listed under its name with those words.
    out += [{"name": name, "error": "no engine of this name is registered here now", "runs": len(ids),
             "runIds": ids[:RUN_IDS]} for name, ids in sorted(made.items()) if name not in registry.found()]
    return out


def _registered(tool: str, name: str) -> tuple[Any, ToolResult | None]:
    """The registered engine named, or the tool's refusal in words."""
    from ..engine import registry

    try:
        return registry.get(name.strip() or "biosteam"), None
    except (registry.EngineNotFound, registry.EngineUnavailable) as e:
        return None, ToolResult(error=f"{tool} refused: {str(e).strip(chr(39))}")


def _plants(inp: EnginePlantsInput, ctx: ToolContext) -> ToolResult:
    from ..engine import library

    engine, refused = _registered("engine_plants", inp.engine)
    if refused is not None:
        return refused
    words = [w for w in inp.words.lower().split() if w]
    if engine.name != "biosteam":
        from ..engine import EngineBroken

        try:
            things = engine.things()
        except EngineBroken as e:
            return ToolResult(error=f"engine_plants refused: the {engine.name} engine broke its contract: {e}")
        rows = [{"plant": th.id, "kind": th.kind, "title": th.title, "configurations": th.configurations,
                 "defaultConfiguration": th.defaultConfiguration} for th in things
                if not words or all(w in f"{th.id} {th.title} {th.kind or ''}".lower() for w in words)]
        return ToolResult(summary={"engine": engine.name, "matched": len(rows), "plants": rows[: inp.limit],
                                   "engines": engines_listed()})
    shelf = library.shelf()
    # Each plant as the engine runs it (engine/biosteam.py): the
    # configurations it built in here, and the one a run takes when none is
    # named, at every door.
    things = {th.id: th for th in engine.things()}
    rows = []
    for p in shelf.plants:
        th = things.get(p.id)
        if th is None:
            continue
        said = " ".join(x for x in (p.id, p.title or "", p.module, p.composedFrom or "", p.readme or "") if x).lower()
        if words and not all(w in said for w in words):
            continue
        rows.append({"plant": p.id, "kind": p.kind, "title": p.title, "configurations": th.configurations,
                     "defaultConfiguration": th.defaultConfiguration,
                     "requiresConfiguration": bool(th.configurations) and th.defaultConfiguration is None,
                     "composedFrom": p.composedFrom})
    # The things the engine's providers give it (alpha 2.2 D6): the shelf's
    # flowsheets a Proforma scenario runs, a run of one a scenario's run.
    held = {p.id for p in shelf.plants}
    rows += [{"plant": th.id, "kind": th.kind, "title": th.title, "configurations": th.configurations,
              "defaultConfiguration": th.defaultConfiguration} for th in things.values()
             if th.id not in held and (not words or all(w in f"{th.id} {th.title}".lower() for w in words))]
    return ToolResult(summary={"engine": "biosteam", "simulator": shelf.simulator, "package": shelf.package,
                               "matched": len(rows), "plants": rows[: inp.limit], "engines": engines_listed()})


# ── engine_parameters ───────────────────────────────────────────────────


class EngineParametersInput(BaseModel):
    engine: str = Field(default="biosteam", max_length=40, description=(
        "The engine to read (GET /api/engines names them): biosteam, whose things are the library plants, "
        "openFerment's flowsheet and the shelf's scenario flowsheets, or any other registered here."))
    plant: str = Field(max_length=80, description="A plant's id, as engine_plants gives it.")
    configuration: str = Field(default="", max_length=CONFIGURATION_MAX,
                               description="One of the plant's configurations; empty for its own.")
    words: str = Field(default="", max_length=200, description="Words to narrow the parameters by; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _parameters(inp: EngineParametersInput, ctx: ToolContext) -> ToolResult:
    from ..engine import biosteam, library, runs
    from ..engine import EngineBroken, EngineRefused

    engine, refused = _registered("engine_parameters", inp.engine)
    if refused is not None:
        return refused
    if engine.name != "biosteam" or biosteam.provided(inp.plant) is not None:
        # The thing and its configuration resolved as a run of it resolves
        # them (runs.thing_of), so the worker is asked in the configuration
        # a run would use.
        try:
            cfg, found_params = runs.parameters_with(engine, inp.plant, inp.configuration)
        except EngineRefused as e:
            return ToolResult(error=f"engine_parameters refused: {e}")
        except EngineBroken as e:
            return ToolResult(error=f"engine_parameters refused: the {engine.name} engine broke its contract: {e}")
        words = [w for w in inp.words.lower().split() if w]
        # A parameter with no default (default and origin null) is one a run sets, or the engine binds.
        rows = [{"key": p.key, "label": p.label, "unit": p.unit, "default": p.value,
                 "origin": p.origin.kind if p.origin is not None else None, "min": p.min, "max": p.max}
                for p in found_params if not words or all(w in f"{p.key} {p.label}".lower() for w in words)]
        return ToolResult(summary={"engine": engine.name, "plant": inp.plant.strip(), "configuration": cfg,
                                   "matched": len(rows), "parameters": rows[: inp.limit],
                                   "note": "A run sets a value in the parameter's own unit, as a typed quantity; "
                                           "a parameter whose default is null has none, and a run sets it or the "
                                           "engine binds it from what the project holds."})
    said = biosteam.unknown(inp.plant)
    if said:
        return ToolResult(error=f"engine_parameters refused: {said} (engine_plants lists them)")
    try:
        # Read in the configuration a run of the plant runs in: the one
        # named, else its default (engine/biosteam.py `default_configuration`).
        found = library.parameters(inp.plant.strip(), biosteam.default_configuration(inp.plant, inp.configuration))
    except (library.LibraryRefused, library.PlantNotFound) as e:
        return ToolResult(error=f"engine_parameters refused: {str(e).strip(chr(39))}")
    defaults = {v.key: v for v in found.values}
    words = [w for w in inp.words.lower().split() if w]
    rows = []
    for spec in found.specs:
        said = f"{spec.key} {spec.label} {spec.gloss} {spec.group}".lower()
        if words and not all(w in said for w in words):
            continue
        held = defaults.get(spec.key)
        rows.append({"key": spec.key, "label": spec.label, "unit": spec.unit, "group": spec.group,
                     "default": held.libraryDefault if held is not None else None, "min": spec.min, "max": spec.max})
    return ToolResult(summary={"plant": found.plant, "configuration": found.configuration, "scope": found.scope,
                               "matched": len(rows), "parameters": rows[: inp.limit],
                               "note": "A scenario sets a value in the parameter's own unit (study_scenario)."})


# ── engine_run ──────────────────────────────────────────────────────────


class EngineRunInput(BaseModel):
    engine: str = Field(default="biosteam", max_length=40, description=(
        "The engine to run (GET /api/engines names them): biosteam, whose things are the library plants, "
        "openFerment's flowsheet and the shelf's scenario flowsheets, or any other registered here, whose thing this "
        "tool runs at its own defaults."))
    plant: str = Field(default="", max_length=80,
                       description="A plant's id, run at the library's defaults; empty when a scenario is named.")
    configuration: str = Field(default="", max_length=CONFIGURATION_MAX,
                               description="One of the plant's configurations; empty for its own.")
    scenario: str = Field(default="", max_length=80,
                          description="A study scenario's id (study_scenario returns it), run on its plant with its values.")
    note: str = Field(default="", max_length=600, description="Why the run is asked for, in words.")


def _run(inp: EngineRunInput, ctx: ToolContext) -> ToolResult:
    from .writes import run_engine

    engine, refused = _registered("engine_run", inp.engine)
    if refused is not None:
        return refused
    return run_engine("engine_run", inp.plant, inp.configuration, inp.scenario, inp.note, ctx,
                      engine=None if engine.name == "biosteam" else engine)


# ── engine_report ───────────────────────────────────────────────────────


class EngineReportInput(BaseModel):
    engine: str = Field(default="biosteam", max_length=40, description=(
        "The engine that ran it, when you know it: a run of another engine is then refused. Left out, the run's own."))
    run: str = Field(max_length=80, description="A kept run's id, as engine_run or study_read gives it.")
    parameters: str = Field(default="", max_length=200, description=(
        "Words to read the parameters the run read back from the plant by (its feed, a unit, a price, a finance term): "
        "each one matched comes back as an evidence id with its value, its unit and its origin. Empty for none."))
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many parameters at most.")


def _report(inp: EngineReportInput, ctx: ToolContext) -> ToolResult:
    from ..engine import runs

    try:
        report = runs.report(inp.run.strip())
    except runs.RunNotFound as e:
        return ToolResult(error=f"engine_report refused: {str(e).strip(chr(39))}")
    # The engine is checked only when the caller names one: left out, its
    # default stands for the run's own (docs/TOOLS.md, engine_report).
    if "engine" in inp.model_fields_set and inp.engine.strip() and inp.engine.strip() != report.run.engine:
        return ToolResult(error=f"engine_report refused: run {report.run.id} was made by the {report.run.engine} "
                                f"engine, and {inp.engine.strip()!r} was named")
    result = run_result(report, state="open")
    if inp.parameters.strip() and result.error is None:
        # The parameters asked for, in the summary's room: the run's own numbers
        # stay citable, and engine_report with no words lists them.
        found = parameter_evidence(report, inp.parameters, inp.limit)
        keep = ("state", "runId", "artifactId", "engine", "tool", "plant", "configuration", "scenarioId", "provenance",
                "valuesSet")
        result.summary = {**{k: result.summary.get(k) for k in keep}, "matched": len(found),
                          "parameters": [{"id": e.id, "label": e.label.split(": ", 1)[-1], "value": e.value,
                                          "unit": e.unit} for e in found],
                          "note": "The run's price, its outputs and its TEA breakdown: engine_report with no parameters."}
        result.evidence = [*result.evidence, *found]
    return result


PLANTS_TOOL = register(Tool(
    name="engine_plants",
    description=(
        "List what the library shelf runs: the biorefineries plants with an entry point and openFerment's own "
        "flowsheets, each with its configurations, the configuration a run takes when none is named, and the "
        "package a flowsheet is composed from; or, with `engine`, that engine's things. Beside them, `engines` "
        "lists every engine registered here: its version, its worker and the worker's state, its last "
        "conformance verdict, and the ids of the project's runs it made, newest first (engine_report reads "
        "each). Narrow the things by words. Returns ids and words, nothing to cite."
    ),
    input_model=EnginePlantsInput, run=_plants, strict=False,
))

PARAMETERS_TOOL = register(Tool(
    name="engine_parameters",
    description=(
        "A plant's parameters as the package builds it: each key with its label, its unit, its group and the "
        "library's default, and the bounds it is held to. A scenario sets a parameter by its key in that unit. "
        "Narrow by words. The first call builds the plant in the simulator and may take half a minute."
    ),
    input_model=EngineParametersInput, run=_parameters, strict=False,
))

RUN_TOOL = register(Tool(
    name="engine_run",
    description=(
        "Run a plant from the library shelf at the library's defaults, or a study scenario (by its id) with the "
        "values it sets, as an engine run: kept in the project, marked as yours, with the SFF file it writes. "
        "Returns the run's id, its artifact id, its provenance (assumed when a value it set is an estimate or an "
        "assumption; measured when a value it set is a deposition's reading and none is either), the values it "
        "set with their origins (a reading with its ref), and each number its price and its flowsheet's "
        "outputs hold as an evidence id to cite. The same plant and values asked again answer from the run kept. "
        "A plant that refuses the values is kept as a receipt and refused in the plant's words."
    ),
    input_model=EngineRunInput, run=_run, strict=False, writes=True,
))

REPORT_TOOL = register(Tool(
    name="engine_report",
    description=(
        "Read a kept engine run by its id: what ran, the values it set with their origins, its provenance, and "
        "each number its price block, its flowsheet's outputs and its TEA breakdown hold as an evidence id to cite; "
        "with words in `parameters`, the parameters the run read back from the plant (its feed's composition, "
        "moisture and price, the chemicals' prices, the finance terms), each as an evidence id with its origin. "
        "For a refused run, the plant's own words."
    ),
    input_model=EngineReportInput, run=_report, strict=False,
))
