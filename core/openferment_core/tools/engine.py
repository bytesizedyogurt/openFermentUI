"""The library shelf and the project's engine runs, for Postdoc (alpha 2.0
stage 6; execution prompt §4.6, §9.1 step 6; ADR-004, ADR-006).

`engine_plants` lists what the shelf runs: the `biorefineries` plants with an
entry point and openFerment's own flowsheets, each with its configurations.
`engine_parameters` gives one plant's parameters as the package builds it
(the Proforma worker reads them): each key with its unit and the library's
default, the values a scenario sets are set against. `engine_run` runs a plant
at the library's defaults, or a study's scenario, as an engine run
(engine/runs.py) through `writes.run_engine`, which keeps it audited as its
caller's; `engine_report` reads a kept run back.

A RUN'S EVIDENCE. Each number its price block and its flowsheet's own outputs
hold, in its unit, is one Evidence whose id is `<artifact id>:<block>.<key>`
and whose basis is the run's artifact, its provenance the artifact's
(`assumed` when a value the run set is a person's assumption or a model's
estimate). A claim cites those ids, and a value a claim states is read from
one by its id.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..models import ComputedBasis, Evidence, RunReport, ToolResult
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
    return out[:MAX_ROWS]


def run_result(report: RunReport, *, state: str = "open") -> ToolResult:
    """A kept run in a tool's words: what ran, on what values, and its numbers as evidence ids."""
    run = report.run
    if run.status == "refused":
        return ToolResult(summary={"runId": run.id, "plant": run.plant, "configuration": run.configuration,
                                   "status": "refused", "refused": run.refused, "scenarioId": run.scenarioId})
    evidence = run_evidence(report)
    own = [{"key": i.name, "value": i.quantity.value, "unit": i.quantity.unit, "origin": i.quantity.origin.kind,
            "by": i.quantity.origin.by}
           for i in run.inputs if i.quantity.origin is not None
           and i.quantity.origin.kind in ("person-assumption", "model-estimate")]
    return ToolResult(
        summary={
            "state": state,
            "runId": run.id,
            "artifactId": run.artifactId,
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
    words: str = Field(default="", max_length=200,
                       description="Words to narrow the shelf by: a product, a feedstock, a plant's name; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _plants(inp: EnginePlantsInput, ctx: ToolContext) -> ToolResult:
    from ..engine import library

    shelf = library.shelf()
    words = [w for w in inp.words.lower().split() if w]
    rows = []
    for p in shelf.plants:
        if p.kind not in ("plant", "flowsheet") or p.error:
            continue
        said = " ".join(x for x in (p.id, p.title or "", p.module, p.composedFrom or "", p.readme or "") if x).lower()
        if words and not all(w in said for w in words):
            continue
        rows.append({"plant": p.id, "kind": p.kind, "title": p.title, "configurations": p.configurations,
                     "defaultConfiguration": p.defaultConfiguration, "requiresConfiguration": p.requiresConfiguration,
                     "composedFrom": p.composedFrom})
    return ToolResult(summary={"simulator": shelf.simulator, "package": shelf.package, "matched": len(rows),
                               "plants": rows[: inp.limit]})


# ── engine_parameters ───────────────────────────────────────────────────


class EngineParametersInput(BaseModel):
    plant: str = Field(max_length=80, description="A plant's id, as engine_plants gives it.")
    configuration: str = Field(default="", max_length=40, description="One of the plant's configurations; empty for its own.")
    words: str = Field(default="", max_length=200, description="Words to narrow the parameters by; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _parameters(inp: EngineParametersInput, ctx: ToolContext) -> ToolResult:
    from ..engine import library

    try:
        found = library.parameters(inp.plant.strip(), inp.configuration.strip() or None)
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
    plant: str = Field(default="", max_length=80,
                       description="A plant's id, run at the library's defaults; empty when a scenario is named.")
    configuration: str = Field(default="", max_length=40, description="One of the plant's configurations; empty for its own.")
    scenario: str = Field(default="", max_length=80,
                          description="A study scenario's id (study_scenario returns it), run on its plant with its values.")
    note: str = Field(default="", max_length=600, description="Why the run is asked for, in words.")


def _run(inp: EngineRunInput, ctx: ToolContext) -> ToolResult:
    from .writes import run_engine

    return run_engine("engine_run", inp.plant, inp.configuration, inp.scenario, inp.note, ctx)


# ── engine_report ───────────────────────────────────────────────────────


class EngineReportInput(BaseModel):
    run: str = Field(max_length=80, description="A kept run's id, as engine_run or study_read gives it.")


def _report(inp: EngineReportInput, ctx: ToolContext) -> ToolResult:
    from ..engine import runs

    try:
        report = runs.report(inp.run.strip())
    except runs.RunNotFound as e:
        return ToolResult(error=f"engine_report refused: {str(e).strip(chr(39))}")
    return run_result(report, state="open")


PLANTS_TOOL = register(Tool(
    name="engine_plants",
    description=(
        "List what the library shelf runs: the biorefineries plants with an entry point and openFerment's own "
        "flowsheets, each with its configurations, the configuration a run takes when none is named, and the "
        "package a flowsheet is composed from. Narrow by words. Returns ids and words, nothing to cite."
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
        "assumption), the values it set with their origins, and each number its price and its flowsheet's "
        "outputs hold as an evidence id to cite. The same plant and values asked again answer from the run kept. "
        "A plant that refuses the values is kept as a receipt and refused in the plant's words."
    ),
    input_model=EngineRunInput, run=_run, strict=False, writes=True,
))

REPORT_TOOL = register(Tool(
    name="engine_report",
    description=(
        "Read a kept engine run by its id: what ran, the values it set with their origins, its provenance, and "
        "each number its price and its flowsheet's outputs hold as an evidence id to cite; for a refused run, "
        "the plant's own words."
    ),
    input_model=EngineReportInput, run=_report, strict=False,
))
