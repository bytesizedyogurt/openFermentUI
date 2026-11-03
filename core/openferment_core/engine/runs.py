"""Engine runs (execution prompt §7.4; ADR-004, ADR-003, ADR-006, ADR-015).

An engine run is one computation of one engine in a project, kept as a row
of the `runs` table in the shape every engine's run has (docs/api/runs.md):

    what ran    the engine, its thing (a library plant or an openFerment
                flowsheet for BioSTEAM, engine/library.py) and the
                configuration it ran in
    its inputs  each a `Quantity` with its origin (ADR-006): the package's own
                settings as `library-default`, a person's value as a
                `person-assumption`, a model's as a `model-estimate`, a
                convention the run states as a `convention`
    its computation  the artifact of its basis (the basis, the output and
                its hash, replayable within the precision the basis states)
                and the provenance computed on it
    its outputs `values`, each output a typed quantity in the unit its
                artifact states, its origin the run's artifact (`values_of`);
                a library run keeps its price, a flowsheet's own outputs and
                how the package's test held it beside them
    its versions  the simulator, its property engine and the package, as
                its basis names them, or the engine's own `version()`
    its SFF file  (engine/sff.py: a `run` record, validated, scored and
                tagged in the worker), or the words that say why none could
                be written
    its status  `done`, or `refused` with the engine's own words (a receipt:
                BioSTEAM's InfeasibleRegion naming its unit, a gate the values
                failed) and no artifact

A run's id is its computation's (the artifact id of its basis), so the same
run asked twice is one row, and a refused one is answered from its receipt.
A request refused before anything computes (an unknown key, a range, a scope
the plant does not have) keeps nothing. `keep_run` keeps the row of any
engine's computation: BioSTEAM's library run (`run`), the run of every
engine built on `contract.WorkerEngine` (`run_engine`) and the kinetics
engine's computations in the service's own process (`compute_kept`,
fermos_engine.py) are kept through it. The tables and the read-back stay in
the artifact; `report` reads the run, its artifact and its SFF record
together.

    GET  /api/runs                 the project's runs, newest first (?engine= one engine's)
    GET  /api/runs/{id}            one run's report: the run, its artifact, its SFF record,
                                   its parameters as the parameter panel reads them
    POST /api/library/{plant}/run  a library plant or a flowsheet run and kept (api.py)
    POST /api/engines/{name}/run   any registered engine's thing run and kept (api.py)

BioSTEAM's run is computed by `run`; an engine built on
`contract.WorkerEngine` computes in its own worker, and `run_engine` keys,
files and reports its run here, the same for every such engine
(docs/api/engines.md).
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from typing import Any

import json
from collections.abc import Mapping, Sequence

from .. import artifacts, db, events, projects
from ..basis import ASSUMED_KINDS, assumption_source, estimate_source, origin_of
from ..db import models as t
from ..db import rows
from ..models import (Artifact, BasisInput, BasisSource, EngineInput, EngineParameter, EngineRun, EngineThing, Origin,
                      Override, ParameterValue, ParamScope, Quantity, ReplayTolerance, RunInput, RunReport, RunSFF,
                      SFFFlowsheet)
from ..params import bounds_check
from ..workers import WorkerError
from . import Engine, EngineBroken, EngineRefused, contract, library, sff

# The words a version is read from in a run's basis: "biosteam 2.54.0" and
# "thermosteam 0.54.2" as values, "<module>@2.35.1" as the plant's source.
_NAMED = re.compile(r"^(\S+) (\S+)$")
PACKAGE = "biorefineries"
# The engine a library run is kept under, as BioSTEAM registers (engine/biosteam.py).
LIBRARY_ENGINE = "biosteam"
# The stem of a contract engine's artifact tool (`engine_tool`): `engine.<name>`.
CONTRACT_TOOL = "engine."
# The kinetics engine's artifact tools (fermos_engine.py), each read here by
# its name: the engine package imports no fermOS module (test_boundaries.py).
SIMULATION_TOOL = "fermos.simulation"
FORECAST_TOOL = "growth_forecast"
VESSEL_TOOL = "fermos.vessel"


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


def _versions(inputs: Sequence[BasisInput], engine: Any = None) -> dict[str, str]:
    """The distributions a run ran on: the simulator, its property engine
    and the package, as its basis names them; for a basis that names no
    simulator, the engine's own `version()` (`_engine_versions`)."""
    out = {}
    for i in inputs:
        if i.name in ("simulator", "thermodynamics") and isinstance(i.value, str) and _NAMED.match(i.value):
            name, v = _NAMED.match(i.value).groups()
            out[name] = v
        if i.name == "plant" and i.source.id and "@" in i.source.id:
            out[PACKAGE] = i.source.id.rsplit("@", 1)[1]
    if any(i.name == "simulator" for i in inputs):
        return out
    return _engine_versions(engine)


def _engine_versions(engine: Any) -> dict[str, str]:
    """An engine's `version()`: the engine's own when the engine is given,
    the registered engine's when it is named (engine/registry.py); empty for
    a name no usable engine registers here."""
    if engine is None:
        return {}
    if isinstance(engine, str):
        from . import registry

        try:
            engine = registry.get(engine)
        except (registry.EngineNotFound, registry.EngineUnavailable):
            return {}
    return dict(engine.version())


def _engine_name(engine: Any) -> str:
    """The name a run is kept under: the engine's own for an engine given
    whole; a name given is BioSTEAM's (`LIBRARY_ENGINE`, whose library run
    `run` computes here) or one the registry holds (engine/registry.py),
    usable or set aside. Any other name is refused in words (ValueError), so
    every row is filed under an engine `GET /api/engines` lists."""
    if not isinstance(engine, str):
        return engine.name
    name = engine.strip()
    if name == LIBRARY_ENGINE:
        return name
    from . import registry

    if name not in registry.found():
        raise ValueError(f"no engine named {name!r} is registered here, so no run is kept under it; the engines are "
                         f"{', '.join(registry.names()) or 'none'}")
    return name


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def values_of(art: Artifact) -> list[dict[str, Any]]:
    """A run's outputs as typed quantities, read from its artifact alone:
    each `{name, quantity}`, the quantity in the unit the artifact states
    for it and its origin the artifact (`{"kind": "artifact", "ref": <its
    id>}`). A library run's are each number of its price block in the unit
    `price.units` names (`price.<key>`) and each of its flowsheet's own
    outputs that `outputUnits` names a unit for (`outputs.<key>`), in the
    artifact's order; a contract engine's run's are its worker's outputs,
    each by its own name, in the worker's order. The kinetics engine's are
    a simulation's end state in the units it states for each state
    (`end.<state>`, `end.t` in hours) and its harvest hour and the hour its
    sugar runs out, where it runs out (`harvestH`, `sugarRunsOutH`); a
    forecast's finals, each its median with its 5th and 95th percentiles as
    the quantity's low and high (`finals.<role>`); and a vessel design's
    rows in BioSTEAM's units (`design.<label>`, the unit beside a label two
    rows share). Any other tool's artifact answers an empty list."""
    origin = Origin(kind="artifact", ref=art.id)

    def typed(name: str, value: Any, unit: str, low: Any = None, high: Any = None) -> dict[str, Any]:
        return {"name": name, "quantity": Quantity(
            value=value, unit=unit, low=low if _number(low) else None, high=high if _number(high) else None,
            origin=origin).model_dump(mode="json", exclude_none=True)}

    o = art.output
    if art.tool == library.LIBRARY_RUN:
        price = o.get("price") or {}
        out = [typed(f"price.{k}", price[k], u) for k, u in (price.get("units") or {}).items()
               if isinstance(u, str) and _number(price.get(k))]
        units = o.get("outputUnits") or {}
        out += [typed(f"outputs.{k}", v, units[k]) for k, v in (o.get("outputs") or {}).items()
                if isinstance(units.get(k), str) and (_number(v) or isinstance(v, str))]
        return out
    if art.tool.startswith(CONTRACT_TOOL):
        return [typed(v["name"], v["value"], v["unit"]) for v in o.get("values") or []]
    if art.tool == SIMULATION_TOOL:
        units = o.get("units") or {}
        out = [typed(f"end.{k}", v, units[k]) for k, v in (o.get("end") or {}).items()
               if isinstance(units.get(k), str) and _number(v)]
        if isinstance(units.get("t"), str):
            out += [typed(k, o[k], units["t"]) for k in ("harvestH", "sugarRunsOutH") if _number(o.get(k))]
        return out
    if art.tool == FORECAST_TOOL:
        return [typed(f"finals.{f['role']}", f["median"], f["unit"], f.get("low"), f.get("high"))
                for f in o.get("finals") or [] if isinstance(f, dict) and isinstance(f.get("role"), str)
                and isinstance(f.get("unit"), str) and _number(f.get("median"))]
    if art.tool == VESSEL_TOOL:
        rows = [r for r in o.get("design") or [] if isinstance(r, dict) and isinstance(r.get("label"), str)
                and isinstance(r.get("unit"), str) and (_number(r.get("value")) or isinstance(r.get("value"), str))]
        shared = {lb for lb in (r["label"] for r in rows) if sum(r["label"] == lb for r in rows) > 1}
        return [typed(f"design.{r['label']}" + (f" ({r['unit']})" if r["label"] in shared and r["unit"] else ""),
                      r["value"], r["unit"]) for r in rows]
    return []


def _outputs(art: Artifact) -> dict[str, Any]:
    """What a run answers, small enough for a listing: `values`, its outputs
    as typed quantities (`values_of`), and for a library run its price, a
    flowsheet's own outputs and how the package's test held it as well."""
    values = values_of(art)
    if art.tool != library.LIBRARY_RUN:
        return {"values": values}
    o = art.output
    out: dict[str, Any] = {"price": o.get("price")}
    if o.get("outputs") is not None:
        out["outputs"] = o["outputs"]
    held = o.get("checks") or []
    if held:
        out["regression"] = {"within": sum(bool(c.get("within")) for c in held), "of": len(held)}
    out["values"] = values
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
    own default elsewhere, read from the run's artifact alone. A library
    run's alone: a run of any other tool answers None."""
    if art.tool != library.LIBRARY_RUN:
        return None
    read = art.output.get("parameters")
    if not isinstance(read, list):
        return None
    defaults = art.output.get("libraryDefaults") or {}
    plant = next((i for i in art.inputs if i.name == "plant"), None)
    own = BasisSource(kind="model", id=plant.source.id if plant else None,
                      note="read back from the plant as the package builds it")
    set_here = {i.name: i for i in art.inputs if i.source.kind in ASSUMED_KINDS}
    specs = [library._spec(p) for p in read]
    values = []
    for p, spec in zip(read, specs):
        i = set_here.get(p["key"])
        if i is None:
            values.append(ParameterValue(key=p["key"], value=p["value"], source=own, origin="library-default",
                                         libraryDefault=defaults.get(p["key"], p["value"]), detail=p["note"]))
            continue
        # A value the run set outside the plant's bounds is kept as set, and flagged (D4).
        values.append(ParameterValue(key=p["key"], value=i.value, source=i.source,
                                     origin="model-estimate" if i.source.kind == "model-estimate" else "assumption",
                                     overriddenBy=i.source.by, libraryDefault=defaults.get(p["key"]), detail=i.source.note,
                                     outOfBounds=bounds_check(spec, i.value)))
    where = run.plant + (f" ({run.configuration})" if run.configuration else "")
    return ParamScope(scope=library.scope(run.plant, run.configuration), kind="library",
                      title=f"{where}: the values this run was bound with", specs=specs,
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


def _job(run_id: str, engine: str, thing: str, configuration: str | None, scenario_id: str | None,
         by: str) -> dict[str, Any]:
    """What the event stream says of a run's job (`job.*`, docs/api/postdoc.md)."""
    return {"id": run_id, "kind": "engine.run", "engine": engine, "plant": thing, "configuration": configuration,
            "scenarioId": scenario_id, "by": by}


def _failed(job: dict[str, Any], e: BaseException, project_id: str) -> None:
    """The job said failed on the event stream, in the error's type and words; no row is kept."""
    events.publish("job.failed", {**job, "status": "failed", "words": f"{type(e).__name__}: {e}"}, project=project_id)


def keep_run(engine: Any, thing: str, configuration: str | None, *, tool: str, version: str,
             basis: Sequence[BasisInput], by: str = "", art: Artifact | None = None, refused: str | None = None,
             flowsheet: SFFFlowsheet | None = None, sff_refused: str | None = None,
             scenario_id: str | None = None, seed: int | None = None,
             versions: Mapping[str, str] | None = None) -> RunReport:
    """Keep one run of any engine's computation as its `runs` row, in the
    shape every run has (docs/api/runs.md, Keeping a run), say so on the
    project's event stream, and answer the run's report.

    `engine` is the engine that ran it, as the engine itself or by its
    registered name (`_engine_name`: a name no engine registered here has
    is refused). `tool`, `version`, `basis` and `seed` are its
    computation's, and the run's id is the artifact id of that basis.
    A computation that ran gives `art`, the artifact it kept: the row is
    `done`, its outputs read from the artifact (`values_of`), its SFF file
    the record `flowsheet` or the words `sff_refused` for why none was
    written (one of the two), and `job.done` says it. An engine that
    refused the values inside its computation gives `refused`, its words:
    the row is a receipt the same request is answered from, it keeps no SFF
    file, and `job.failed` says it. Exactly one of `art` and `refused` is
    given, and an `art` is the computation of this basis; a call outside
    these rules is refused (ValueError) and keeps nothing.

    The same run kept twice is one row, answered as it was first kept: a
    held row that is done with its file or its words, or a held receipt, is
    answered from the store, and nothing is written or said. A held row
    with neither is written whole again with its first asker's `by`, `at`
    and scenario. The row's versions are `versions` when the keeper gives
    them (the distributions that thing's computation ran on), else the
    distributions its basis names, or the engine's own `version()` for a
    basis that names no simulator. `by` is who asked, `this browser` when
    the request names no one; `scenario_id` the study scenario that asked
    for it."""
    if (art is None) == (refused is None):
        raise ValueError("a run is kept with the artifact its computation kept, or with the words its engine "
                         "refused it in: one of the two")
    basis = list(basis)
    run_id = artifacts.artifact_id(tool, version, basis, seed)
    if art is not None and (art.id, art.tool, art.toolVersion) != (run_id, tool, version):
        raise ValueError(f"artifact {art.id} ({art.tool}, {art.toolVersion}) is no computation of run {run_id}'s "
                         f"basis ({tool}, {version})")
    if art is not None and (flowsheet is None) == (sff_refused is None):
        raise ValueError("a run that computed is kept with its SFF record, or with the words for why its engine "
                         "wrote none: one of the two")
    if art is None and (flowsheet is not None or sff_refused is not None):
        raise ValueError("a receipt keeps no SFF file: the engine refused the values, and nothing was computed "
                         "to write one for")
    name = _engine_name(engine)
    project_id = projects.current()
    held = db.run(_get(project_id, run_id))
    if held is not None and (held.status == "refused" or held.sff is not None or held.sffRefused is not None):
        return report(run_id)
    who = (by or "").strip() or "this browser"
    first, when, asked = (held.by, held.at, held.scenarioId) if held is not None else (who, _now(), scenario_id)
    base = dict(id=run_id, engine=name, plant=thing, configuration=configuration, tool=tool, toolVersion=version,
                inputs=_inputs(basis), versions=dict(versions) if versions is not None else _versions(basis, engine),
                by=first, at=when, scenarioId=asked)
    job = _job(run_id, name, thing, configuration, scenario_id, who)
    if art is None:
        receipt = EngineRun(**base, status="refused", refused=refused)
        db.run(_put(project_id, receipt, first))
        events.publish("job.failed", {**job, "status": "refused", "words": refused}, project=project_id)
        return _report(receipt, None, None)
    kept = EngineRun(**base, status="done", provenance=art.provenance, artifactId=art.id, outputs=_outputs(art),
                     durationMs=art.durationMs, sffRefused=sff_refused,
                     sff=RunSFF(recordId=flowsheet.id, valid=flowsheet.validation.valid,
                                score=flowsheet.completeness.score,
                                tags=sorted(k for k, v in flowsheet.tags.items() if v.earned)) if flowsheet else None)
    db.run(_put(project_id, kept, first))
    events.publish("job.done", {**job, "status": "done", "provenance": kept.provenance, "artifactId": kept.artifactId,
                                "sffRecordId": kept.sff.recordId if kept.sff else None}, project=project_id)
    return _report(kept, art, flowsheet)


def compute_kept(engine: Any, thing: str, configuration: str | None, *, tool: str, basis: Sequence[BasisInput],
                 refusal: type[Exception], sff_refused: str, by: str = "", seed: int | None = None,
                 records_by_id: Mapping[str, Any] | None = None, scenario_id: str | None = None,
                 versions: Mapping[str, str] | None = None) -> Artifact:
    """An engine's computation in the service's own process (the kinetics
    engine's, fermos_engine.py), computed through `artifacts.compute` and kept
    as its run (`keep_run`), the artifact answered; a library run's path
    (`run`) for an engine that computes here.

    The run's id is the artifact id of `tool`, its version for `basis`, the
    basis and `seed`. A receipt the project holds for that id is answered
    without computing: `refusal` raised in the receipt's words. A row held
    done answers the stored artifact, its provenance brought up to date by
    `artifacts.compute` (a record it rests on reviewed or demoted since), and
    the row's provenance follows the artifact's; nothing else is written,
    and nothing is said. Otherwise the job is said queued and running and the
    computation runs: a `refusal` it raises is the engine's refusal of these
    values, kept as a receipt and raised again; any other error says the job
    failed and is raised, with no row kept. A refusal raised here carries the
    receipt's id as `run_id`. The computation is kept with `sff_refused`, the
    engine's words for why it writes no SFF file, and with `versions` (the
    distributions this thing ran on; `keep_run`). `by` is who asked;
    `records_by_id` the provenance of the basis's record inputs, as
    `artifacts.compute` takes it."""
    basis = list(basis)
    version = artifacts.registered(tool).version_for(basis)
    run_id = artifacts.artifact_id(tool, version, basis, seed)
    project_id = projects.current()
    held = db.run(_get(project_id, run_id))
    if held is not None and held.status == "refused":
        e = refusal(held.refused or f"the {_engine_name(engine)} engine refused these values")
        e.run_id = held.id  # type: ignore[attr-defined]
        raise e
    if held is not None and (held.sff is not None or held.sffRefused is not None):
        art = artifacts.compute(tool, basis, records_by_id=records_by_id, seed=seed)
        if held.status == "done" and art.provenance != held.provenance:
            db.run(_put(project_id, held.model_copy(update={"provenance": art.provenance}), held.by))
        return art
    who = (by or "").strip() or "this browser"
    job = _job(run_id, _engine_name(engine), thing, configuration, scenario_id, who)
    events.publish("job.queued", job, project=project_id)
    events.publish("job.running", job, project=project_id)
    try:
        art = artifacts.compute(tool, basis, records_by_id=records_by_id, seed=seed)
    except refusal as e:
        receipt = keep_run(engine, thing, configuration, tool=tool, version=version, basis=basis, by=who,
                           refused=str(e), scenario_id=scenario_id, seed=seed, versions=versions).run
        e.run_id = receipt.id  # type: ignore[attr-defined]
        raise
    except Exception as e:
        _failed(job, e, project_id)
        raise
    keep_run(engine, thing, configuration, tool=tool, version=version, basis=basis, by=who, art=art,
             sff_refused=sff_refused, scenario_id=scenario_id, seed=seed, versions=versions)
    return art


def run(plant_id: str, configuration: str | None = None, overrides: list[Override] | None = None, *,
        by: str = "", scenario_id: str | None = None) -> RunReport:
    """Run a library plant or an openFerment flowsheet, write its SFF file
    and keep the run (`keep_run`); a run of the same basis kept already is
    answered from its row. A plant that refuses the values is kept as a
    receipt and refused (`RunRefused`, the plant's words and the receipt's
    id). A run a study's scenario asks for names it (`scenario_id`)."""
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
    cfg = str(named) if named is not None else None
    job = _job(run_id, LIBRARY_ENGINE, plant_id, cfg, scenario_id, who)
    events.publish("job.queued", job, project=project_id)
    events.publish("job.running", job, project=project_id)
    try:
        art = artifacts.compute(library.LIBRARY_RUN, inputs)
    except library.LibraryRefused as e:
        receipt = keep_run(LIBRARY_ENGINE, plant_id, cfg, tool=library.LIBRARY_RUN, version=version, basis=inputs,
                           by=who, refused=str(e), scenario_id=scenario_id).run
        raise RunRefused(str(e), receipt.id) from None
    except Exception as e:
        _failed(job, e, project_id)
        raise
    flowsheet, refused = None, None
    try:
        flowsheet = sff.export(library.plant_of(art), project_id=project_id, run_artifact_id=art.id, by=who)
    except sff.SFFRefused as e:
        refused = str(e)
    except Exception as e:
        # The worker's words for the file are kept with the run; any other
        # failure is said on the event stream and raised, with no row kept.
        if isinstance(e, WorkerError) and str(e).startswith("Refused: "):
            refused = str(e).removeprefix("Refused: ")
        else:
            _failed(job, e, project_id)
            raise
    return keep_run(LIBRARY_ENGINE, plant_id, cfg, tool=library.LIBRARY_RUN, version=version, basis=inputs, by=who,
                    art=art, flowsheet=flowsheet, sff_refused=refused, scenario_id=scenario_id)


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


def _value_source(name: str, origin: Origin) -> BasisSource:
    """A value's source in the basis, as its origin names it: a person's
    assumption or a model's estimate, written as a library run's override is
    (basis.override_source), with the day its origin says it was set. The
    service stamps no day of its own, so the same request is the same run on
    any day."""
    at = (origin.at or "").strip()
    if not at:
        raise EngineRefused(f"{name}: a value a run sets says when it was set (quantity.origin.at)")
    if origin.kind == "model-estimate":
        return estimate_source(origin.by or "", at, origin.note)
    return assumption_source(origin.by or "", at, origin.note)


# How many of a thing's keys a refusal of an unknown key names, nearest first.
NEAREST_KEYS = 3


def _unknown_key(thing: str, key: str, params: dict[str, EngineParameter]) -> str:
    """A key the thing does not declare, in words: how many parameters the
    thing has and the few keys nearest to the one asked for."""
    if not params:
        return f"{thing} has no parameter {key!r}; it takes no parameters"
    near = difflib.get_close_matches(key, sorted(params), n=NEAREST_KEYS, cutoff=0.0)
    n = len(params)
    return (f"{thing} has no parameter {key!r}; of its {n} parameter{'s' if n != 1 else ''}, the nearest "
            f"{'is' if len(near) == 1 else 'are'} {', '.join(near)}")


def takes_number(p: EngineParameter) -> bool:
    """Whether a run sets the parameter as a number, read from its
    declaration: a parameter with choices takes one of them, in words; one
    whose default is words in no unit takes words; every other one takes a
    number, a parameter with no default and one whose default is a
    convention's words in a unit among them (the kinetics engine's term left
    off, as `ki_substrate` is, until a run sets a number in g L⁻¹)."""
    if p.choices is not None:
        return False
    return not (isinstance(p.value, str) and not p.unit)


def check_inputs(thing: str, parameters: Sequence[EngineParameter], inputs: Sequence[EngineInput], *,
                 bounds: bool) -> None:
    """The values a run sets, each checked against the thing's parameters
    before anything runs: a key the thing declares, set once, in the
    parameter's unit, a number for a number and one of its choices for words
    (`takes_number`), and, with `bounds`, inside its bounds. `run_engine`
    checks a contract engine's values with their bounds; BioSTEAM's engine
    and the kinetics engine check theirs with `bounds` False: the library
    flags a value outside a plant's bounds on the run's parameters, kept as
    set (`parameters_of`), and fermOS flags one on its artifact. A value
    refused raises EngineRefused in words, and nothing is kept. A key the
    thing lacks is named with the few keys nearest to it, the same for every
    engine."""
    params = {p.key: p for p in parameters}
    seen: set[str] = set()
    for i in inputs:
        p = params.get(i.name)
        if p is None:
            raise EngineRefused(_unknown_key(thing, i.name, params))
        if i.name in seen:
            raise EngineRefused(f"{i.name} is set twice")
        seen.add(i.name)
        q = i.quantity
        if q.unit != p.unit:
            raise EngineRefused(f"{i.name} is set in {q.unit!r}, and the parameter's unit is {p.unit!r}")
        numeric = takes_number(p)
        if numeric != isinstance(q.value, (int, float)):
            raise EngineRefused(f"{i.name} takes {'a number' if numeric else 'words'}")
        if p.choices is not None and q.value not in p.choices:
            raise EngineRefused(f"{i.name} takes one of {', '.join(map(str, p.choices))}; {q.value!r} is none of them")
        if bounds and numeric:
            v = float(q.value)
            if (p.min is not None and v < p.min) or (p.max is not None and v > p.max):
                raise EngineRefused(f"{i.name} = {q.value} {q.unit} lies outside its bounds [{p.min}, {p.max}] {p.unit}")


def _checked_values(engine: Any, thing: str, configuration: str | None,
                    inputs: Sequence[EngineInput]) -> list[BasisInput]:
    """The values a run sets, checked against the thing's parameters with
    their bounds (`check_inputs`), each as its basis input with its source.
    A contract engine's run sets one value per parameter, its value and unit
    with its origin: a quantity that also carries `low`, `high` or `basis` is
    refused in words, since its worker receives the value and unit alone."""
    for i in inputs:
        carried = [k for k in ("low", "high", "basis") if getattr(i.quantity, k) is not None]
        if carried:
            raise EngineRefused(f"{i.name}: a run of the {engine.name} engine sets one value in the parameter's "
                                f"unit, with its origin; this quantity also carries {' and '.join(carried)}")
    parameters = engine.parameters(thing, configuration)
    check_inputs(thing, parameters, inputs, bounds=True)
    waiting = sorted(p.key for p in parameters if p.value is None and p.key not in {i.name for i in inputs})
    if waiting:
        n = len(waiting)
        raise EngineRefused(f"{thing} cannot run yet: {n} parameter{'s wait' if n != 1 else ' waits'} for the run to "
                            f"set {'them' if n != 1 else 'it'}, having no default: {', '.join(waiting)}")
    out: list[BasisInput] = []
    for i in inputs:
        q = i.quantity
        assert q.origin is not None  # EngineInput holds a person's or a model's
        out.append(BasisInput(name=f"value {i.name}", value=q.value, unit=q.unit, source=_value_source(i.name, q.origin)))
    return sorted(out, key=lambda b: b.name)


def is_contract(engine: Any) -> bool:
    """Whether the engine is built on WorkerEngine: the service keys, keeps
    and files its runs (`run_engine`) over its worker's ops."""
    return callable(getattr(engine, "compute", None)) and callable(getattr(engine, "sff_document", None))


def thing_of(engine: Any, thing: str, configuration: str | None) -> tuple[EngineThing, str | None]:
    """The thing a request names and the configuration it runs in, one rule
    at every door of a contract engine (its run, its parameters, its tools):
    a request naming no configuration runs in the thing's default; a thing
    with configurations and no default is run with one named; a configuration
    the thing does not name, or any configuration for a thing that takes
    none, is refused in words."""
    thing_id = (thing or "").strip()
    things = {x.id: x for x in engine.things()}
    if thing_id not in things:
        raise EngineRefused(f"the {engine.name} engine runs no thing {thing_id!r}; it runs "
                            f"{', '.join(sorted(things)) or 'nothing'}")
    found = things[thing_id]
    cfg = (configuration or "").strip() or found.defaultConfiguration
    if found.configurations and cfg is None:
        raise EngineRefused(f"{thing_id} is run in one of its configurations, named in the request: "
                            f"{', '.join(found.configurations)}")
    if found.configurations and cfg not in found.configurations:
        raise EngineRefused(f"{thing_id} runs in {', '.join(found.configurations)}; {cfg!r} is none of them")
    if not found.configurations and cfg is not None:
        raise EngineRefused(f"{thing_id} takes no configuration, and {cfg!r} was named")
    return found, cfg


def parameters_with(engine: Any, thing: str, configuration: str | None) -> tuple[str | None, list[EngineParameter]]:
    """A thing's parameters as a run of it reads them, with the configuration
    they are read in. A contract engine's thing and configuration are
    resolved by `thing_of` first, so its worker's `parameters` op receives
    the configuration a run would use; any other engine answers its own
    `parameters` for the configuration named."""
    if is_contract(engine):
        found, cfg = thing_of(engine, thing, configuration)
        return cfg, engine.parameters(found.id, cfg)
    cfg = (configuration or "").strip() or None
    return cfg, engine.parameters((thing or "").strip(), cfg)


def run_engine(engine: Any, thing: str, configuration: str | None, inputs: Sequence[EngineInput] = (), *,
               by: str = "", scenario_id: str | None = None) -> RunReport:
    """One run of a contract engine (docs/api/engines.md), kept as one
    `runs` row of the shape every run has (`keep_run`). Its id is the
    artifact id of its basis: the engine, the thing, the configuration, the
    precision the thing states and every value set, with its source. The
    same request twice is that one row, answered as it was first kept (its
    `by` the first asker's); a run the engine refuses is kept as a receipt
    and answered from it. Every ask, a repeat included, first checks its
    values against the worker's `parameters` op, so a row or a receipt is
    answered while the worker answers. After the run the engine is asked
    once for its SFF file, kept as `run-<id>`, or its words kept as
    `sffRefused`. A worker that fails, or answers outside the protocol
    (EngineBroken), keeps no row: its job is said failed on the event stream
    and the error raised. A failure of the SFF step leaves the run's
    artifact kept, and the next ask answers the computation from it and asks
    for the file again."""
    who = (by or "").strip() or "this browser"
    found, cfg = thing_of(engine, thing, configuration)
    thing_id = found.id
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
    job = _job(run_id, engine.name, thing_id, cfg, scenario_id, who)
    events.publish("job.queued", job, project=project_id)
    events.publish("job.running", job, project=project_id)
    try:
        art = artifacts.compute(tool, basis)
    except EngineRefused as e:
        receipt = keep_run(engine, thing_id, cfg, tool=tool, version=version, basis=basis, by=who, refused=str(e),
                           scenario_id=scenario_id).run
        raise RunRefused(str(e), receipt.id) from None
    except Exception as e:
        _failed(job, e, project_id)
        raise
    flowsheet, refused = None, None
    try:
        doc = engine.sff_document(thing_id, cfg, _engine_values(basis))
        flowsheet = sff.keep_run_file(json.dumps(doc).encode("utf-8"), project_id=project_id, run_artifact_id=art.id,
                                      source=f"written by the {engine.name} engine for run {art.id} of {thing_id}",
                                      title=found.title, by=who)
    except (EngineRefused, sff.SFFRefused) as e:
        refused = str(e)
    except Exception as e:
        # The Proforma worker refused the file in words; any other failure (a
        # worker that crashed or timed out, an engine that broke the protocol)
        # is said on the event stream and raised, as a library run's is, with
        # no row kept, and the next ask tries again.
        if isinstance(e, WorkerError) and str(e).startswith("Refused: "):
            refused = str(e).removeprefix("Refused: ")
        else:
            _failed(job, e, project_id)
            raise
    return keep_run(engine, thing_id, cfg, tool=tool, version=version, basis=basis, by=who, art=art,
                    flowsheet=flowsheet, sff_refused=refused, scenario_id=scenario_id)


def run_with(engine: Any, thing: str, configuration: str | None, inputs: Sequence[EngineInput] = (), *,
             by: str = "", scenario_id: str | None = None) -> RunReport:
    """One run of any registered engine, answered as its report: an engine
    built on WorkerEngine through `run_engine`, any other through its own
    `run`, which keeps its row; an engine whose `run` kept none is broken
    (EngineBroken)."""
    if is_contract(engine):
        return run_engine(engine, thing, configuration, inputs, by=by, scenario_id=scenario_id)
    kept = engine.run(thing, configuration, list(inputs), by)
    try:
        return report(str(getattr(kept, "id", "") or ""))
    except RunNotFound:
        raise EngineBroken(f"the {engine.name} engine kept no row for its run") from None
