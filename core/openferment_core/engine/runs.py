"""Engine runs (execution prompt §7.4; ADR-004, ADR-003, ADR-006).

An engine run is one run of a library plant or an openFerment flowsheet
(engine/library.py) in a project, kept as a row of the `runs` table:

    the plant and its configuration
    its inputs, each a `Quantity` with its origin (ADR-006): the package's own
                settings as `library-default`, a person's value as a
                `person-assumption`, a model's as a `model-estimate`, a
                convention the run states as a `convention`
    its computation: the `library.run` artifact (the basis, the output and
                its hash, replayable within the precision the basis states)
                and the provenance computed on it
    its outputs (the price, and a flowsheet's own) and the versions it ran on
    the SFF file it wrote (engine/sff.py `export`: a `run` record, validated,
                scored and tagged in the worker), or the words that say why
                none could be written
    its status: `done`, or `refused` with the plant's own words (a receipt:
                BioSTEAM's InfeasibleRegion naming its unit, a gate the values
                failed) and no artifact

A run's id is its computation's (the artifact id of its basis), so the same
run asked twice is one row, and a refused one is answered from its receipt.
A request the runner refuses before any plant is built (an unknown key, a
range, a scope the plant does not have) keeps nothing. The tables and the
read-back stay in the artifact; `report` reads the run, its artifact and its
SFF record together.

    GET  /api/runs                 the project's runs, newest first (?engine= one engine's)
    GET  /api/runs/{id}            one run's report: the run, its artifact, its SFF record,
                                   its parameters as the parameter panel reads them
    POST /api/library/{plant}/run  a library plant or a flowsheet run and kept (api.py)
    POST /api/engines/{name}/run   any registered engine's thing run and kept (api.py)

Every engine's run is a row of the same shape (docs/api/engines.md;
ADR-015). BioSTEAM's is computed by `run` above; an engine built on
`contract.WorkerEngine` computes in its own worker, and `run_engine` keys,
keeps, files and reports its run here, the same for every such engine.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import json
from collections.abc import Sequence

from .. import artifacts, db, events, projects
from ..basis import ASSUMED_KINDS, origin_of
from ..db import models as t
from ..db import rows
from ..models import (Artifact, BasisInput, BasisSource, EngineInput, EngineRun, Origin, Override, ParameterValue,
                      ParamScope, Quantity, ReplayTolerance, RunInput, RunReport, RunSFF)
from ..workers import WorkerCrashed, WorkerError, WorkerTimeout
from . import Engine, EngineRefused, contract, library, sff

# The words a version is read from in a run's basis: "biosteam 2.54.0" and
# "thermosteam 0.54.2" as values, "<module>@2.35.1" as the plant's source.
_NAMED = re.compile(r"^(\S+) (\S+)$")
PACKAGE = "biorefineries"


class RunNotFound(KeyError):
    pass


class RunRefused(library.LibraryRefused):
    """A plant's refusal of a run's values, kept as the receipt `run_id`."""

    def __init__(self, words: str, run_id: str):
        super().__init__(words)
        self.run_id = run_id


def _inputs(inputs: list[BasisInput]) -> list[RunInput]:
    return [RunInput(name=i.name, quantity=Quantity(value=i.value, unit=i.unit, origin=origin_of(i.source)))
            for i in inputs]


def _versions(inputs: list[BasisInput]) -> dict[str, str]:
    """The simulator, its property engine and the package, as the basis names them."""
    out = {}
    for i in inputs:
        if i.name in ("simulator", "thermodynamics") and isinstance(i.value, str) and _NAMED.match(i.value):
            name, v = _NAMED.match(i.value).groups()
            out[name] = v
        if i.name == "plant" and i.source.id and "@" in i.source.id:
            out[PACKAGE] = i.source.id.rsplit("@", 1)[1]
    return out


def _outputs(art: Artifact) -> dict[str, Any]:
    """What a run answers, small enough for a listing: the price, a
    flowsheet's own outputs, and how the package's test held it."""
    o = art.output
    out: dict[str, Any] = {"price": o.get("price")}
    if o.get("outputs") is not None:
        out["outputs"] = o["outputs"]
    held = o.get("checks") or []
    if held:
        out["regression"] = {"within": sum(bool(c.get("within")) for c in held), "of": len(held)}
    return out


def _named(inputs: list[BasisInput], name: str) -> Any:
    return next((i.value for i in inputs if i.name == name), None)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _put(project_id: str, run: EngineRun, by: str) -> None:
    columns = {"scenario_id": run.scenarioId} if run.scenarioId else {}
    async with db.session() as s:
        await rows.put(s, t.runs, project_id, run.id, run.model_dump(mode="json"), by=by,
                       flowsheet_id=run.sff.recordId if run.sff else None, status=run.status, engine=run.engine,
                       **columns)


async def _get(project_id: str, run_id: str) -> EngineRun | None:
    async with db.session() as s:
        body = await rows.body(s, t.runs, project_id, run_id)
    return EngineRun.model_validate(body) if body is not None else None


async def _listed(project_id: str, engine: str | None = None) -> list[EngineRun]:
    where = (t.runs.c.engine == engine,) if engine else ()
    async with db.session() as s:
        found = await rows.bodies(s, t.runs, project_id, *where, order=(t.runs.c.created_at.desc(), t.runs.c.id))
    return [EngineRun.model_validate(b) for b in found]


def get(run_id: str) -> EngineRun:
    found = db.run(_get(projects.current(), run_id))
    if found is None:
        raise RunNotFound(f"the project holds no run {run_id}")
    return found


def listed(engine: str | None = None) -> list[EngineRun]:
    """The project's runs, newest first; those of one engine when `engine` names it."""
    return db.run(_listed(projects.current(), engine))


def parameters_of(run: EngineRun, art: Artifact) -> ParamScope | None:
    """The run's parameters as the parameter panel reads them: each as its
    plant declares it (library._spec), its value the run's, a person's
    assumption or a model's estimate where the run set one and the library's
    own default elsewhere, read from the run's artifact alone."""
    read = art.output.get("parameters")
    if not isinstance(read, list):
        return None
    defaults = art.output.get("libraryDefaults") or {}
    plant = next((i for i in art.inputs if i.name == "plant"), None)
    own = BasisSource(kind="model", id=plant.source.id if plant else None,
                      note="read back from the plant as the package builds it")
    set_here = {i.name: i for i in art.inputs if i.source.kind in ASSUMED_KINDS}
    values = []
    for p in read:
        i = set_here.get(p["key"])
        if i is None:
            values.append(ParameterValue(key=p["key"], value=p["value"], source=own, origin="library-default",
                                         libraryDefault=defaults.get(p["key"], p["value"]), detail=p["note"]))
            continue
        values.append(ParameterValue(key=p["key"], value=i.value, source=i.source,
                                     origin="model-estimate" if i.source.kind == "model-estimate" else "assumption",
                                     overriddenBy=i.source.by, libraryDefault=defaults.get(p["key"]), detail=i.source.note))
    where = run.plant + (f" ({run.configuration})" if run.configuration else "")
    return ParamScope(scope=library.scope(run.plant, run.configuration), kind="library",
                      title=f"{where}: the values this run was bound with", specs=[library._spec(p) for p in read],
                      values=values, waiting=[], notes=[
                          "Each value is the run's own: a person's assumption or a model's estimate where the run set "
                          "one, the library's default elsewhere. A different value is a new scenario, and a new run."])


def _report(run: EngineRun, art: Artifact | None, flowsheet) -> RunReport:
    return RunReport(run=run, artifact=art, flowsheet=flowsheet,
                     parameters=parameters_of(run, art) if art is not None else None)


def report(run_id: str) -> RunReport:
    """One run with its artifact, its SFF record (the file itself is
    `GET /api/flowsheets/{id}/file`) and its parameters as the panel reads
    them."""
    run = get(run_id)
    art = artifacts.get(run.artifactId) if run.artifactId else None
    flowsheet = sff.get(run.sff.recordId, project_id=projects.current()) if run.sff else None
    return _report(run, art, flowsheet)


def run(plant_id: str, configuration: str | None = None, overrides: list[Override] | None = None, *,
        by: str = "", scenario_id: str | None = None) -> RunReport:
    """Run a library plant or an openFerment flowsheet, write its SFF file
    and keep the run; a run of the same basis kept already is answered from
    its row. A plant that refuses the values is kept as a receipt and
    refused (`RunRefused`, the plant's words and the receipt's id). A run a
    study's scenario asks for names it (`scenario_id`)."""
    who = (by or "").strip() or "this browser"
    inputs = library.run_inputs(plant_id, configuration, list(overrides or []))
    project_id = projects.current()
    version = artifacts.registered(library.LIBRARY_RUN).version_for(inputs)
    run_id = artifacts.artifact_id(library.LIBRARY_RUN, version, inputs)
    held = db.run(_get(project_id, run_id))
    if held is not None and held.status == "refused":
        raise RunRefused(held.refused or "the plant refused these values", held.id)
    if held is not None and (held.sff is not None or held.sffRefused is not None):
        return report(run_id)
    named = _named(inputs, "configuration")
    base = dict(id=run_id, plant=plant_id, configuration=str(named) if named is not None else None,
                tool=library.LIBRARY_RUN, toolVersion=version, inputs=_inputs(inputs), versions=_versions(inputs),
                by=who, at=_now(), scenarioId=scenario_id)
    job = {"id": run_id, "kind": "engine.run", "plant": plant_id, "configuration": base["configuration"],
           "scenarioId": scenario_id, "by": who}
    events.publish("job.queued", job, project=project_id)
    events.publish("job.running", job, project=project_id)
    try:
        art = artifacts.compute(library.LIBRARY_RUN, inputs)
    except library.LibraryRefused as e:
        db.run(_put(project_id, EngineRun(**base, status="refused", refused=str(e)), who))
        events.publish("job.failed", {**job, "status": "refused", "words": str(e)}, project=project_id)
        raise RunRefused(str(e), run_id) from None
    except Exception as e:
        events.publish("job.failed", {**job, "status": "failed", "words": f"{type(e).__name__}: {e}"}, project=project_id)
        raise
    flowsheet, refused = None, None
    try:
        flowsheet = sff.export(library.plant_of(art), project_id=project_id, run_artifact_id=art.id, by=who)
    except sff.SFFRefused as e:
        refused = str(e)
    except WorkerError as e:
        if not str(e).startswith("Refused: "):
            raise
        refused = str(e).removeprefix("Refused: ")
    kept = EngineRun(**base, status="done", provenance=art.provenance, artifactId=art.id, outputs=_outputs(art),
                     durationMs=art.durationMs, sffRefused=refused,
                     sff=RunSFF(recordId=flowsheet.id, valid=flowsheet.validation.valid,
                                score=flowsheet.completeness.score,
                                tags=sorted(k for k, v in flowsheet.tags.items() if v.earned)) if flowsheet else None)
    db.run(_put(project_id, kept, who))
    events.publish("job.done", {**job, "status": "done", "provenance": kept.provenance, "artifactId": kept.artifactId,
                                "sffRecordId": kept.sff.recordId if kept.sff else None}, project=project_id)
    return _report(kept, art, flowsheet)


# ── a contract engine's run (docs/api/engines.md; ADR-015) ──────────────


def engine_tool(engine: Engine) -> str:
    """The artifact tool an engine's runs are computed and replayed as."""
    return f"engine.{engine.name}"


def _precision_of(inputs: Sequence[BasisInput]) -> ReplayTolerance:
    """The precision a run's basis states (`precision.rtol`, `precision.atol`)."""
    rtol = _named(list(inputs), "precision.rtol")
    atol = _named(list(inputs), "precision.atol")
    return ReplayTolerance(rtol=float(rtol or 0.0), atol=float(atol or 0.0), why=(
        f"the precision the {_named(list(inputs), 'engine')} engine states for {_named(list(inputs), 'thing')}: "
        "every output within atol + rtol·|stored|"))


def _engine_values(inputs: Sequence[BasisInput]) -> list[dict[str, Any]]:
    """The values a run set, read back from its basis: what the worker's `run` op takes."""
    return [{"name": i.name.removeprefix("value "), "value": i.value, "unit": i.unit}
            for i in inputs if i.name.startswith("value ")]


def register_engine_tool(engine: Any) -> None:
    """Make an engine's runs computable and replayable as artifacts of the
    tool `engine.<name>`, from the basis alone."""

    def compute(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
        thing = str(_named(inputs, "thing"))
        configuration = _named(inputs, "configuration")
        configuration = str(configuration) if configuration is not None else None
        return {"engine": engine.name, "thing": thing, "configuration": configuration,
                "values": engine.compute(thing, configuration, _engine_values(inputs))}

    artifacts.register(engine_tool(engine), contract.version_string(engine), compute,
                       version_of=lambda inputs: contract.version_string(engine), tolerance_of=_precision_of)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _value_source(origin: Origin) -> BasisSource:
    """A value's source in the basis, as its origin names it: a person's
    assumption or a model's estimate, the day stamped as the library's are."""
    if origin.kind == "model-estimate":
        stamp = f"estimated on {origin.at}" if origin.at else None
        kind = "model-estimate"
    else:
        stamp = f"typed on {origin.at}" if origin.at else None
        kind = "assumption"
    note = ": ".join(x for x in (stamp, origin.note) if x) or None
    return BasisSource(kind=kind, by=(origin.by or "").strip(), note=note)


def _checked_values(engine: Any, thing: str, configuration: str | None,
                    inputs: Sequence[EngineInput]) -> list[BasisInput]:
    """The values a run sets, each checked against the thing's parameters:
    a key it declares, set once, in the parameter's unit and kind, inside
    its bounds. A value the parameters refuse keeps nothing."""
    params = {p.key: p for p in engine.parameters(thing, configuration)}
    out: list[BasisInput] = []
    seen: set[str] = set()
    for i in inputs:
        p = params.get(i.name)
        if p is None:
            raise EngineRefused(f"{thing} has no parameter {i.name!r}; its parameters are "
                                         f"{', '.join(sorted(params)) or 'none'}")
        if i.name in seen:
            raise EngineRefused(f"{i.name} is set twice")
        seen.add(i.name)
        q = i.quantity
        if q.unit != p.unit:
            raise EngineRefused(f"{i.name} is set in {q.unit!r}, and the parameter's unit is {p.unit!r}")
        numeric = isinstance(p.value, (int, float))
        if numeric != isinstance(q.value, (int, float)):
            raise EngineRefused(f"{i.name} takes {'a number' if numeric else 'words'}")
        if p.choices is not None and q.value not in p.choices:
            raise EngineRefused(f"{i.name} takes one of {', '.join(map(str, p.choices))}; "
                                         f"{q.value!r} is none of them")
        if numeric:
            v = float(q.value)
            if (p.min is not None and v < p.min) or (p.max is not None and v > p.max):
                raise EngineRefused(f"{i.name} = {q.value} {q.unit} lies outside its bounds "
                                             f"[{p.min}, {p.max}] {p.unit}")
        assert q.origin is not None  # EngineInput holds a person's or a model's
        out.append(BasisInput(name=f"value {i.name}", value=q.value, unit=q.unit, source=_value_source(q.origin)))
    return sorted(out, key=lambda b: b.name)


def run_engine(engine: Any, thing: str, configuration: str | None, inputs: Sequence[EngineInput] = (), *,
               by: str = "", scenario_id: str | None = None) -> RunReport:
    """One run of a contract engine (docs/api/engines.md), kept as one
    `runs` row of the shape every run has. Its id is the artifact id of its
    basis: the engine, the thing, the configuration, the precision the thing
    states and every value set, with its source. The same request twice is
    that one row; a run the engine refuses is kept as a receipt and answered
    from it. After the run the engine is asked once for its SFF file, kept
    as `run-<id>`, or its words kept as `sffRefused`."""
    who = (by or "").strip() or "this browser"
    thing_id = (thing or "").strip()
    things = {x.id: x for x in engine.things()}
    if thing_id not in things:
        raise EngineRefused(f"the {engine.name} engine runs no thing {thing_id!r}; it runs "
                                     f"{', '.join(sorted(things)) or 'nothing'}")
    found = things[thing_id]
    cfg = (configuration or "").strip() or found.defaultConfiguration
    if found.configurations and cfg not in found.configurations:
        raise EngineRefused(f"{thing_id} runs in {', '.join(found.configurations)}; "
                                     f"{cfg!r} is none of them")
    if not found.configurations and cfg is not None:
        raise EngineRefused(f"{thing_id} takes no configuration, and {cfg!r} was named")
    values = _checked_values(engine, thing_id, cfg, list(inputs))

    def convention(note: str) -> BasisSource:
        return BasisSource(kind="convention", note=note)

    basis = [BasisInput(name="engine", value=engine.name, unit="", source=convention("the engine that ran it")),
             BasisInput(name="thing", value=thing_id, unit="", source=convention(f"what the {engine.name} engine ran"))]
    if cfg is not None:
        basis.append(BasisInput(name="configuration", value=cfg, unit="", source=convention("the configuration it ran in")))
    basis += [BasisInput(name="precision.rtol", value=found.precision.rtol, unit="1",
                         source=convention("the relative precision the engine states for the thing")),
              BasisInput(name="precision.atol", value=found.precision.atol, unit="1",
                         source=convention("the absolute precision the engine states, in each output's unit")),
              *values]
    tool = engine_tool(engine)
    try:
        registered = artifacts.registered(tool)
    except artifacts.ToolNotRegistered:
        register_engine_tool(engine)
        registered = artifacts.registered(tool)
    version = registered.version_for(basis)
    run_id = artifacts.artifact_id(tool, version, basis)
    project_id = projects.current()
    held = db.run(_get(project_id, run_id))
    if held is not None and held.status == "refused":
        raise RunRefused(held.refused or f"the {engine.name} engine refused these values", held.id)
    if held is not None and (held.sff is not None or held.sffRefused is not None):
        return report(run_id)
    base = dict(id=run_id, engine=engine.name, plant=thing_id, configuration=cfg, tool=tool, toolVersion=version,
                inputs=_inputs(basis), versions=engine.version(), by=who, at=_now(), scenarioId=scenario_id)
    job = {"id": run_id, "kind": "engine.run", "engine": engine.name, "plant": thing_id, "configuration": cfg,
           "scenarioId": scenario_id, "by": who}
    events.publish("job.queued", job, project=project_id)
    events.publish("job.running", job, project=project_id)
    try:
        art = artifacts.compute(tool, basis)
    except EngineRefused as e:
        db.run(_put(project_id, EngineRun(**base, status="refused", refused=str(e)), who))
        events.publish("job.failed", {**job, "status": "refused", "words": str(e)}, project=project_id)
        raise RunRefused(str(e), run_id) from None
    except Exception as e:
        events.publish("job.failed", {**job, "status": "failed", "words": f"{type(e).__name__}: {e}"}, project=project_id)
        raise
    flowsheet, refused = None, None
    try:
        doc = engine.sff_document(thing_id, cfg, _engine_values(basis))
        flowsheet = sff.keep_run_file(json.dumps(doc).encode("utf-8"), project_id=project_id, run_artifact_id=art.id,
                                      source=f"written by the {engine.name} engine for run {art.id} of {thing_id}",
                                      title=found.title, by=who)
    except (EngineRefused, sff.SFFRefused) as e:
        refused = str(e)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        refused = f"the SFF file could not be written or checked: {e}"
    values_out = [{"name": o["name"], "quantity": Quantity(value=o["value"], unit=o["unit"],
                                                            origin=Origin(kind="artifact", ref=art.id)).model_dump(
                      mode="json", exclude_none=True)}
                  for o in art.output.get("values", [])]
    kept = EngineRun(**base, status="done", provenance=art.provenance, artifactId=art.id,
                     outputs={"values": values_out}, durationMs=art.durationMs, sffRefused=refused,
                     sff=RunSFF(recordId=flowsheet.id, valid=flowsheet.validation.valid,
                                score=flowsheet.completeness.score,
                                tags=sorted(k for k, v in flowsheet.tags.items() if v.earned)) if flowsheet else None)
    db.run(_put(project_id, kept, who))
    events.publish("job.done", {**job, "status": "done", "provenance": kept.provenance, "artifactId": kept.artifactId,
                                "sffRecordId": kept.sff.recordId if kept.sff else None}, project=project_id)
    return _report(kept, art, flowsheet)


def run_with(engine: Any, thing: str, configuration: str | None, inputs: Sequence[EngineInput] = (), *,
             by: str = "", scenario_id: str | None = None) -> RunReport:
    """One run of any registered engine, answered as its report: an engine
    built on WorkerEngine through `run_engine`, any other through its own
    `run`, which keeps its row."""
    if callable(getattr(engine, "compute", None)) and callable(getattr(engine, "sff_document", None)):
        return run_engine(engine, thing, configuration, inputs, by=by, scenario_id=scenario_id)
    kept = engine.run(thing, configuration, list(inputs), by)
    return report(kept.id)
