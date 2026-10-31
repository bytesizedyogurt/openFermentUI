"""A study's scenarios (execution prompt §9.1 step 5; ADR-006).

A scenario names a plant on the library shelf (a `biorefineries` plant or
an openFerment flowsheet), its configuration, and the values it sets: each a
parameter's key and a quantity in the parameter's own unit, whose origin is
a named person's assumption or a model's estimate (the model's id in `by`).
Every other parameter keeps the library's own default. A scenario is checked
against the plant's parameters when it is made, so a key the plant does not
read back, a unit it does not use or a value of the wrong kind is refused
before anything runs.

Running a scenario is an engine run (engine/runs.py): each value becomes an
`Override` of the plant's scope with its origin, the run's basis names each
value's author, and a run resting on any of them is `assumed`. The scenario
keeps the ids of its runs, oldest first.

A scenario is a row of `scenarios` with kind `engine`; its id is `ssc-` and
the first twelve hex of the sha256 of its plant, configuration and values,
so the same values on the same plant are one scenario.

    GET  /api/studies/scenarios
    POST /api/studies/scenarios            {title, plant, configuration?, values, note?, by}
    GET  /api/studies/scenarios/{id}
    POST /api/studies/scenarios/{id}/run   {by}
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .. import db, projects
from ..db import models as t
from ..db import rows
from ..engine import library, runs
from ..models import Override, RunReport, ScenarioCreate, StudyScenario

KIND = "engine"
PREFIX = "ssc-"


class ScenarioRefused(ValueError):
    """A scenario that cannot be made or run, in words."""


class ScenarioNotFound(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def scenario_id(plant: str, configuration: str | None, values: list) -> str:
    """`ssc-` and the first twelve hex of the sha256 of the plant, the
    configuration and the values as JSON with sorted keys."""
    payload = {"plant": plant, "configuration": configuration,
               "values": sorted((v.model_dump(mode="json") for v in values), key=lambda v: v["key"])}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _checked(asked: ScenarioCreate) -> None:
    """The plant, the configuration and each value against what the plant
    reads back: its key, its unit and its kind."""
    try:
        params = library.parameters(asked.plant, asked.configuration)
    except library.PlantNotFound as e:
        raise ScenarioRefused(str(e).strip("'\"")) from None
    except library.LibraryRefused as e:
        raise ScenarioRefused(str(e)) from None
    specs = {s.key: s for s in params.specs}
    keys = [v.key for v in asked.values]
    twice = sorted({k for k in keys if keys.count(k) > 1})
    if twice:
        raise ScenarioRefused(f"a scenario sets each parameter once; {', '.join(twice)} twice")
    for v in asked.values:
        spec = specs.get(v.key)
        if spec is None:
            raise ScenarioRefused(f"{asked.plant} reads back no parameter {v.key}")
        if spec.dimension == "words":
            raise ScenarioRefused(f"{v.key} is read back in words and never set")
        if v.quantity.unit != spec.unit:
            raise ScenarioRefused(f"{v.key} is in {spec.unit or 'no unit'}; the scenario gives {v.quantity.unit or 'none'}")


async def _put(project_id: str, scenario: StudyScenario, by: str) -> None:
    async with db.session() as s:
        await rows.put(s, t.scenarios, project_id, scenario.id, scenario.model_dump(mode="json"), by=by,
                       kind=KIND, pinned=False)


async def _get(project_id: str, sid: str) -> StudyScenario | None:
    async with db.session() as s:
        body = await rows.body(s, t.scenarios, project_id, sid)
    if body is None or body.get("kind") != KIND:
        return None
    return StudyScenario.model_validate(body)


async def _listed(project_id: str) -> list[StudyScenario]:
    async with db.session() as s:
        found = await rows.bodies(s, t.scenarios, project_id, t.scenarios.c.kind == KIND,
                                  order=(t.scenarios.c.created_at.desc(), t.scenarios.c.id))
    return [StudyScenario.model_validate(b) for b in found]


def make(asked: ScenarioCreate) -> StudyScenario:
    """A scenario checked against its plant and kept; the same plant,
    configuration and values kept already are that scenario, its title and
    note brought up to date."""
    _checked(asked)
    who = (asked.by or "").strip() or "this browser"
    sid = scenario_id(asked.plant, asked.configuration, asked.values)
    project_id = projects.current()
    held = db.run(_get(project_id, sid))
    scenario = StudyScenario(id=sid, title=asked.title.strip(), plant=asked.plant, configuration=asked.configuration,
                             values=asked.values, note=asked.note, runIds=held.runIds if held else [],
                             by=held.by if held else who, at=held.at if held else _now())
    db.run(_put(project_id, scenario, who))
    return scenario


def get(sid: str) -> StudyScenario:
    found = db.run(_get(projects.current(), sid))
    if found is None:
        raise ScenarioNotFound(f"the project holds no scenario {sid}")
    return found


def listed() -> list[StudyScenario]:
    """The project's study scenarios, newest first."""
    return db.run(_listed(projects.current()))


def overrides(scenario: StudyScenario) -> list[Override]:
    """The scenario's values as Overrides of its plant's scope, each with its
    origin, its author, the moment it was set and what it rests on."""
    scope = library.scope(scenario.plant, scenario.configuration)
    return [Override(scope=scope, key=v.key, value=float(v.quantity.value), by=v.quantity.origin.by,
                     at=v.quantity.origin.at, note=v.quantity.origin.note, origin=v.quantity.origin.kind)
            for v in scenario.values]


def run(sid: str, *, by: str = "") -> RunReport:
    """The scenario run as an engine run, and the run's id kept with it. A
    plant's refusal is the run's receipt (engine/runs.py) and refused here
    in the plant's words."""
    scenario = get(sid)
    who = (by or "").strip() or "this browser"
    try:
        report = runs.run(scenario.plant, scenario.configuration, overrides(scenario), by=who, scenario_id=scenario.id)
    except runs.RunRefused as e:
        _kept(scenario, e.run_id, who)
        raise
    _kept(scenario, report.run.id, who)
    return report


def _kept(scenario: StudyScenario, run_id: str, by: str) -> None:
    if run_id not in scenario.runIds:
        db.run(_put(projects.current(), scenario.model_copy(update={"runIds": [*scenario.runIds, run_id]}), by))
