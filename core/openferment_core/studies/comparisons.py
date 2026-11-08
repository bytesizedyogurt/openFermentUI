"""Comparisons (execution prompt §7.4, §9.1 step 5).

Two or more engine runs set side by side: every output the runs answer,
each in its unit, with each run's value and its relative change from the
first run's; and every value any of the runs set for itself, with each run's
value and its origin: a person's assumption, a model's estimate, a
deposition's reading (basis.is_set), or the library's own default where a
library run set none. A library run's outputs
are its price block (BioSTEAM's TEA) and a flowsheet's own outputs, read as
they have always been read; a run of any other engine's, a Proforma
scenario's run among them, are its outputs.values (engine/runs.py
`values_of`), so runs of any engine compare. A value named as a library run
names its own (`price.<key>`, `outputs.<key>`: a Proforma run's solved
price, `price.solvedPrice`) shares that output's row, so a library run's
price and a Proforma run's meet on one row with its change.

A comparison is computed as one `study.comparison` artifact whose inputs
are the runs' artifacts, so its provenance is the weakest of theirs
(`assumed` when any run rests on an assumption or an estimate) and it
replays from them. Its version says what it read (`_version_of`): `study
comparison 1` for library runs alone, read as they have always been read,
and `study comparison 2` for one that holds a run of another engine (D3),
whose outputs.values it reads and whose value cells name a default only
where a library run's plant declares one. A comparison kept at version 1
over such a run replays at version 2 and says so. It is kept as a row of
`comparisons` under that artifact's id, with its title: the same runs in
the same order are one comparison. A run its plant refused has no artifact
and is not compared.

    GET  /api/studies/comparisons
    POST /api/studies/comparisons        {title, runIds, by}
    GET  /api/studies/comparisons/{id}   the comparison and its artifact
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from .. import artifacts, db, projects
from ..basis import is_set, origin_of
from ..db import models as t
from ..db import rows
from ..engine import library, runs
from ..models import (
    Artifact,
    BasisInput,
    BasisSource,
    ComparisonCreate,
    ComparisonReport,
    StudyComparison,
)

COMPARISON = "study.comparison"
# Library runs alone; and a comparison that holds a run of another engine (D3).
VERSION = "study comparison 1"
VERSION_ENGINES = "study comparison 2"
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


def _block(a: Artifact, name: str) -> dict[str, Any]:
    """A library run's block of its output (`price`, `outputs`,
    `outputUnits`); empty for a run of any other engine."""
    return (a.output.get(name) or {}) if a.tool == library.LIBRARY_RUN else {}


def _typed(a: Artifact) -> dict[str, dict[str, Any]]:
    """The outputs.values of a run of any engine beside BioSTEAM's, each
    quantity by its output's name; a library run's numbers are its blocks."""
    return {} if a.tool == library.LIBRARY_RUN else {v["name"]: v["quantity"] for v in runs.values_of(a)}


# The blocks a library run's outputs.values name its numbers by
# (engine/runs.py `values_of`): another run's value of such a name shares the
# library run's row.
SHARED = ("price", "outputs")


def _row_of(name: str) -> tuple[str, str]:
    """The row a run's typed value stands in: a library block's row for a
    name a library run's outputs.values gives (`price.<key>`,
    `outputs.<key>`), else `values.<name>`."""
    block, _, key = name.partition(".")
    return (block, key) if block in SHARED and key else ("values", name)


def _typed_in(a: Artifact, block: str, key: str) -> dict[str, Any] | None:
    """A run's typed value standing in the row (block, key), or None."""
    return _typed(a).get(key if block == "values" else f"{block}.{key}")


def _rows(arts: list[Artifact]) -> list[dict[str, Any]]:
    """Each output any run answers, in the order the first run gives them:
    a library run's `price.<key>` and `outputs.<key>`, and any other run's
    `values.<name>`, a value named as a library run names its own sharing
    that row (`_row_of`)."""
    keys: list[tuple[str, str]] = []
    for a in arts:
        price, outputs = _block(a, "price"), _block(a, "outputs")
        keys += [("price", k) for k in price if k not in SKIP and ("price", k) not in keys]
        keys += [("outputs", k) for k in outputs if ("outputs", k) not in keys]
        keys += [_row_of(k) for k in _typed(a) if _row_of(k) not in keys]
    out = []
    for block, key in keys:
        if block == "values":
            held = [_typed(a).get(key) for a in arts]
            values = [q["value"] if q is not None else None for q in held]
            units = [q["unit"] if q is not None else None for q in held]
        else:
            # A library run's block, or another run's value of the same name.
            held = [None if a.tool == library.LIBRARY_RUN else _typed_in(a, block, key) for a in arts]
            values = [q["value"] if q is not None else _block(a, block).get(key) for a, q in zip(arts, held)]
            units = [q["unit"] if q is not None else
                     (_block(a, "price").get("units") or {}).get(key) if block == "price"
                     else _block(a, "outputUnits").get(key) for a, q in zip(arts, held)]
        unit = next((u for u in units if u is not None), None)
        out.append({"key": f"{block}.{key}", "unit": unit, "values": values,
                    "change": [_change(v, values[0]) for v in values]})
    return out


def _declares(a: Artifact, key: str) -> bool:
    """Whether a run's plant declares the value `key`: a library run whose
    parameters, as its artifact read them back, name it."""
    return a.tool == library.LIBRARY_RUN and any(p.get("key") == key for p in a.output.get("parameters") or [])


# A run's cell for a value it holds none of (`study comparison 2`).
NO_VALUE = {"value": None, "unit": None, "origin": None, "by": None}


def _set_values(arts: list[Artifact]) -> list[dict[str, Any]]:
    """Each value any run set for itself, with each run's value and origin,
    a deposition's reading with its ref. A library run that set none has the
    library's own default, named so. A
    comparison that holds a run of another engine (`study comparison 2`)
    gives that default where the library run's plant declares the value
    (`_declares`); every other run's cell there is NO_VALUE, its value,
    unit, origin and `by` null, since its artifact holds no default of that
    name."""
    engines = _holds_other_engines(arts)
    keys: list[str] = []
    for a in arts:
        keys += [i.name for i in a.inputs if is_set(i.source) and i.name not in keys]
    out = []
    for key in keys:
        cells = []
        for a in arts:
            own = next((i for i in a.inputs if i.name == key and is_set(i.source)), None)
            if own is not None:
                origin = origin_of(own.source)
                cell = {"value": own.value, "unit": own.unit, "origin": origin.kind, "by": origin.by}
                # A reading names itself, so the cell traces to its deposition without the runs.
                cells.append({**cell, "ref": origin.ref} if origin.kind == "measurement" else cell)
                continue
            if engines and not _declares(a, key):
                cells.append(dict(NO_VALUE))
                continue
            plant = next((i for i in a.inputs if i.name == "plant"), None)
            default = (a.output.get("libraryDefaults") or {}).get(key)
            unit = next((p.get("unit") for p in a.output.get("parameters") or [] if p.get("key") == key), None)
            cells.append({"value": default, "unit": unit, "origin": "library-default",
                          "by": plant.source.id if plant is not None else None})
        out.append({"key": key, "values": cells})
    return out


def _ran(a: Artifact) -> Any:
    """What a run ran, as its basis names it: a library run's `plant`, a
    contract engine's run's `thing`, a Proforma scenario's run's
    `flowsheet`."""
    named = {i.name: i.value for i in a.inputs}
    return named.get("plant", named.get("thing", named.get("flowsheet")))


def _compared(inputs: Sequence[BasisInput]) -> list[Artifact]:
    """The runs' artifacts a comparison's basis names, read from the project's store, in order."""
    return [artifacts.get(str(i.value)) for i in inputs if i.source.kind == "artifact"]


def _holds_other_engines(arts: list[Artifact]) -> bool:
    """Whether any compared run is a run of an engine beside BioSTEAM's library."""
    return any(a.tool != library.LIBRARY_RUN for a in arts)


def _version_of(inputs: Sequence[BasisInput]) -> str:
    """What a comparison computes, by the runs it compares: VERSION for
    library runs alone, VERSION_ENGINES when it holds a run of another
    engine."""
    return VERSION_ENGINES if _holds_other_engines(_compared(inputs)) else VERSION


def _compare(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """A comparison from its basis alone: the runs' artifacts, read from
    the project's store, set side by side."""
    arts = _compared(inputs)
    return {
        "runs": [{"artifactId": a.id, "plant": _ran(a),
                  "configuration": next((i.value for i in a.inputs if i.name == "configuration"), None),
                  "provenance": a.provenance} for a in arts],
        "rows": _rows(arts),
        "values": _set_values(arts),
    }


def _register() -> None:
    artifacts.register(COMPARISON, VERSION, _compare, version_of=_version_of)


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
