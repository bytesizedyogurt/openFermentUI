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

    GET  /api/runs                 the project's runs, newest first
    GET  /api/runs/{id}            one run's report: the run, its artifact, its SFF record,
                                   its parameters as the parameter panel reads them
    POST /api/library/{plant}/run  a library plant or a flowsheet run and kept (api.py)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .. import artifacts, db, projects
from ..basis import ASSUMED_KINDS, origin_of
from ..db import models as t
from ..db import rows
from ..models import (Artifact, BasisInput, BasisSource, EngineRun, Override, ParameterValue, ParamScope, Quantity, RunInput,
                      RunReport, RunSFF)
from ..workers import WorkerError
from . import library, sff

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
                       flowsheet_id=run.sff.recordId if run.sff else None, status=run.status, **columns)


async def _get(project_id: str, run_id: str) -> EngineRun | None:
    async with db.session() as s:
        body = await rows.body(s, t.runs, project_id, run_id)
    return EngineRun.model_validate(body) if body is not None else None


async def _listed(project_id: str) -> list[EngineRun]:
    async with db.session() as s:
        found = await rows.bodies(s, t.runs, project_id, order=(t.runs.c.created_at.desc(), t.runs.c.id))
    return [EngineRun.model_validate(b) for b in found]


def get(run_id: str) -> EngineRun:
    found = db.run(_get(projects.current(), run_id))
    if found is None:
        raise RunNotFound(f"the project holds no run {run_id}")
    return found


def listed() -> list[EngineRun]:
    """The project's runs, newest first."""
    return db.run(_listed(projects.current()))


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
    try:
        art = artifacts.compute(library.LIBRARY_RUN, inputs)
    except library.LibraryRefused as e:
        db.run(_put(project_id, EngineRun(**base, status="refused", refused=str(e)), who))
        raise RunRefused(str(e), run_id) from None
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
    return _report(kept, art, flowsheet)
