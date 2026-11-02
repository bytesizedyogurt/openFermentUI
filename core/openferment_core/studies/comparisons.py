"""Comparisons (execution prompt §7.4, §9.1 step 5).

Two or more engine runs set side by side: every output the runs answer
(the price block BioSTEAM's TEA gives, and a flowsheet's own outputs), each
in its unit, with each run's value and its relative change from the first
run's; and every value any of the runs set for itself, with each run's value
and its origin: a person's assumption, a model's estimate, or the library's
own default where a run set none.

A comparison is computed as one `study.comparison` artifact whose inputs
are the runs' artifacts, so its provenance is the weakest of theirs
(`assumed` when any run rests on an assumption or an estimate) and it
replays from them. It is kept as a row of `comparisons` under that
artifact's id, with its title: the same runs in the same order are one
comparison. A run its plant refused has no artifact and is not compared.

    GET  /api/studies/comparisons
    POST /api/studies/comparisons        {title, runIds, by}
    GET  /api/studies/comparisons/{id}   the comparison and its artifact
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .. import artifacts, db, projects
from ..basis import ASSUMED_KINDS, origin_of
from ..db import models as t
from ..db import rows
from ..engine import runs
from ..models import (
    Artifact,
    BasisInput,
    BasisSource,
    ComparisonCreate,
    ComparisonReport,
    StudyComparison,
)

COMPARISON = "study.comparison"
VERSION = "study comparison 1"
# The price block's entries that are a run's numbers (the rest name things).
SKIP = {"priced", "teaClass", "product", "feedstock", "units", "why", "solvedPriceRefused"}


class ComparisonRefused(ValueError):
    """A comparison that cannot be made, in words."""


class ComparisonNotFound(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _change(value: Any, first: Any) -> float | None:
    if not isinstance(value, (int, float)) or not isinstance(first, (int, float)) or isinstance(value, bool) or not first:
        return None
    return (value - first) / abs(first)


def _rows(arts: list[Artifact]) -> list[dict[str, Any]]:
    """Each output any run answers, in the order the first run gives them."""
    keys: list[tuple[str, str]] = []
    for a in arts:
        price, outputs = a.output.get("price") or {}, a.output.get("outputs") or {}
        keys += [("price", k) for k in price if k not in SKIP and ("price", k) not in keys]
        keys += [("outputs", k) for k in outputs if ("outputs", k) not in keys]
    out = []
    for block, key in keys:
        values = [(a.output.get(block) or {}).get(key) for a in arts]
        units = [((a.output.get("price") or {}).get("units") or {}).get(key) if block == "price"
                 else (a.output.get("outputUnits") or {}).get(key) for a in arts]
        unit = next((u for u in units if u is not None), None)
        out.append({"key": f"{block}.{key}", "unit": unit, "values": values,
                    "change": [_change(v, values[0]) for v in values]})
    return out


def _set_values(arts: list[Artifact]) -> list[dict[str, Any]]:
    """Each value any run set for itself, with each run's value and origin;
    a run that set none has the library's own default, named so."""
    keys: list[str] = []
    for a in arts:
        keys += [i.name for i in a.inputs if i.source.kind in ASSUMED_KINDS and i.name not in keys]
    out = []
    for key in keys:
        cells = []
        for a in arts:
            own = next((i for i in a.inputs if i.name == key and i.source.kind in ASSUMED_KINDS), None)
            if own is not None:
                origin = origin_of(own.source)
                cells.append({"value": own.value, "unit": own.unit, "origin": origin.kind, "by": origin.by})
                continue
            plant = next((i for i in a.inputs if i.name == "plant"), None)
            default = (a.output.get("libraryDefaults") or {}).get(key)
            unit = next((p.get("unit") for p in a.output.get("parameters") or [] if p.get("key") == key), None)
            cells.append({"value": default, "unit": unit, "origin": "library-default",
                          "by": plant.source.id if plant is not None else None})
        out.append({"key": key, "values": cells})
    return out


def _compare(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """A comparison from its basis alone: the runs' artifacts, read from
    the project's store, set side by side."""
    arts = [artifacts.get(str(i.value)) for i in inputs if i.source.kind == "artifact"]
    return {
        "runs": [{"artifactId": a.id, "plant": next((i.value for i in a.inputs if i.name == "plant"), None),
                  "configuration": next((i.value for i in a.inputs if i.name == "configuration"), None),
                  "provenance": a.provenance} for a in arts],
        "rows": _rows(arts),
        "values": _set_values(arts),
    }


def _register() -> None:
    artifacts.register(COMPARISON, VERSION, _compare)


artifacts.register_lazy(COMPARISON, _register)


async def _put(project_id: str, comparison: StudyComparison, by: str) -> None:
    async with db.session() as s:
        await rows.put(s, t.comparisons, project_id, comparison.id, comparison.model_dump(mode="json"), by=by)


async def _get(project_id: str, cid: str) -> StudyComparison | None:
    async with db.session() as s:
        body = await rows.body(s, t.comparisons, project_id, cid)
    return StudyComparison.model_validate(body) if body is not None else None


async def _listed(project_id: str) -> list[StudyComparison]:
    async with db.session() as s:
        found = await rows.bodies(s, t.comparisons, project_id,
                                  order=(t.comparisons.c.created_at.desc(), t.comparisons.c.id))
    return [StudyComparison.model_validate(b) for b in found]


def make(asked: ComparisonCreate) -> ComparisonReport:
    """The runs compared, computed as one artifact and kept with the title."""
    ids = list(asked.runIds)
    if len(ids) < 2 or len(set(ids)) != len(ids):
        raise ComparisonRefused("a comparison sets two or more different runs side by side")
    inputs = []
    for n, rid in enumerate(ids, start=1):
        try:
            run = runs.get(rid)
        except runs.RunNotFound as e:
            raise ComparisonRefused(str(e).strip("'\"")) from None
        if run.status != "done" or run.artifactId is None:
            raise ComparisonRefused(f"run {rid} was refused by its plant ({run.refused}), so it has nothing to compare")
        inputs.append(BasisInput(name=f"run {n}", value=run.artifactId, unit="", source=BasisSource(
            kind="artifact", id=run.artifactId, note=f"engine run of {run.plant}"
            + (f" ({run.configuration})" if run.configuration else ""))))
    art = artifacts.compute(COMPARISON, inputs)
    who = (asked.by or "").strip() or "this browser"
    project_id = projects.current()
    held = db.run(_get(project_id, art.id))
    comparison = StudyComparison(id=art.id, title=asked.title.strip(), runIds=ids, artifactId=art.id,
                                 provenance=art.provenance, by=held.by if held else who,
                                 at=held.at if held else _now())
    db.run(_put(project_id, comparison, who))
    return ComparisonReport(comparison=comparison, artifact=art)


def get(cid: str) -> ComparisonReport:
    found = db.run(_get(projects.current(), cid))
    if found is None:
        raise ComparisonNotFound(f"the project holds no comparison {cid}")
    return ComparisonReport(comparison=found, artifact=artifacts.get(found.artifactId))


def listed() -> list[StudyComparison]:
    """The project's comparisons, newest first."""
    return db.run(_listed(projects.current()))
