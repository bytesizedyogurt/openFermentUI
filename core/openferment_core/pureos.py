"""pureOS reads the train a flowsheet ran (OF-BLD-019 §4.1, D1).

Proforma's run is one `proforma.run` artifact holding the base case's stream
and unit tables (`proforma.tables_of`). pureOS reads that same artifact unit
by unit: which streams enter and leave each unit, how much of the product
each carries, and what share of the product entering a unit leaves it on
its way to the product stream. Nothing is typed and nothing is recomputed:
every number here is arithmetic over the stream table the worker wrote.

WHY NOT OUTLETS OVER INLETS. A unit that reacts nothing conserves mass, so
the product in all its outlets equals the product in all its inlets: that
ratio is one for every separator and says nothing about recovery. A unit's
recovery here is the product leaving by the outlets that lead on toward the
product stream (directly, through later units, or round a recycle) over the
product entering it; what leaves by its other outlets is lost at that unit,
and the outlets are named. Both masses, in and out, are kept beside it.

THE PRODUCT is the component the run's price is per: of the stream the
run's TEA prices, the one component whose flow is the TEA's basis flow,
when exactly one is; else that stream's largest component. A run with no
TEA (the toy) names no product: its train lists units and masses and no
recovery, and says why.

WHICH SCENARIO a run belongs to: a basis input named `scenario`, when the
run carries one; else the one seed scenario (modules.json, written by
`pnpm export:corpus`) whose `modelId` is the run's flowsheet. A run no
scenario claims is a train known by its artifact id.
"""
from __future__ import annotations

from typing import Any, Iterable

from .models import Artifact, ProformaTables, StreamRow, Train, TrainSummary, TrainUnit

RUN = "proforma.run"
# kg/hr: a flow at or below this carries nothing.
EPS = 1e-9


class TrainNotFound(LookupError):
    """No run on file answers to the key; the message says how one gets there."""


# ── what the run names ───────────────────────────────────────────────────


def _flowsheet(art: Artifact) -> str | None:
    named = art.output.get("flowsheet") if isinstance(art.output, dict) else None
    return str(named) if named else next((str(i.value) for i in art.inputs if i.name == "flowsheet"), None)


def seed_scenarios() -> list[dict[str, Any]]:
    """The seed's scenarios as `export:corpus` projects them; none when the
    projection is missing, and then only a run's own `scenario` input names
    its scenario."""
    from . import module_stores

    try:
        return list(module_stores._projection()["proforma"]["scenarios"])
    except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
        return []


def scenario_of(art: Artifact, scenarios: Iterable[dict[str, Any]]) -> tuple[str | None, str | None]:
    """The scenario a run belongs to and its name, or (None, None)."""
    by_id = {s["id"]: s for s in scenarios}
    named = next((str(i.value) for i in art.inputs if i.name == "scenario" and isinstance(i.value, str)), None)
    if named:
        return named, (by_id.get(named) or {}).get("name")
    flowsheet = _flowsheet(art)
    claims = [s for s in by_id.values() if s.get("kind") == "biosteam" and s.get("modelId") == flowsheet]
    if len(claims) == 1:
        return claims[0]["id"], claims[0].get("name")
    return None, None


def program_of(art: Artifact, scenario_id: str | None, scenarios: Iterable[dict[str, Any]],
               record_lookup: Any = None) -> str | None:
    """A train's program: its scenario's, its flowsheet's on the shelf, and
    what its basis names (`programs.program_of_artifact`); an archived one
    among them wins, as it does for an artifact."""
    from . import programs
    from .flowsheets import shelf as _shelf

    found: list[str | None] = [next((s.get("program") for s in scenarios if s["id"] == scenario_id), None)]
    try:
        found.append(_shelf.info(_flowsheet(art) or "", allow_toy=True).program)
    except _shelf.NotOnShelf:
        pass
    try:
        found.append(programs.program_of_artifact(art, record_lookup))
    except FileNotFoundError:  # no corpus exported here: the basis names nothing known
        pass
    except Exception:  # a lookup that cannot load leaves the ids in the basis to speak
        try:
            found.append(programs.program_of_artifact(art))
        except FileNotFoundError:
            pass
    kept = [p for p in found if p]
    try:
        archived = next((p for p in kept if programs.is_archived(p)), None)
    except FileNotFoundError:
        archived = None
    return archived or (kept[0] if kept else None)


def product_of(t: ProformaTables) -> tuple[str | None, str | None, str]:
    """(the product stream, the component traced, how it was read in words)."""
    if t.tea is None:
        return None, None, "this run has no TEA, so it names no product and no recovery is read"
    stream = next((s for s in t.streams if s.id == t.tea.product), None)
    if stream is None:
        return t.tea.product, None, f"the run prices {t.tea.product}, and its stream table holds no such stream"
    flows = {k: v for k, v in stream.massFlows.items() if v > EPS}
    if not flows:
        return stream.id, None, f"the run prices {stream.id}, which carries nothing in its base case"
    basis = t.tea.basisFlow
    if basis is not None:
        match = [k for k, v in flows.items() if abs(v - basis) <= 1e-6 * max(abs(basis), 1.0)]
        if len(match) == 1:
            return stream.id, match[0], (f"{match[0]} in {stream.id}: the component the run's price is per "
                                         f"({t.tea.basis or 'its basis flow'})")
    biggest = max(flows, key=lambda k: flows[k])
    return stream.id, biggest, f"{biggest}, the largest component of {stream.id}, the stream the run prices"


# ── the train ────────────────────────────────────────────────────────────


def _reach(product_stream: str | None, streams: list[StreamRow]) -> set[str]:
    """Every unit with an outlet that leads to the product stream."""
    source = next((s.source for s in streams if s.id == product_stream), None)
    if not source:
        return set()
    reach = {source}
    grew = True
    while grew:
        grew = False
        for s in streams:
            if s.source and s.sink in reach and s.source not in reach:
                reach.add(s.source)
                grew = True
    return reach


def train_of(art: Artifact, *, scenarios: Iterable[dict[str, Any]] | None = None, provenance: str | None = None,
             runs: int = 1, record_lookup: Any = None) -> Train:
    """One run's train, read from its stream and unit tables alone."""
    from . import proforma

    if art.tool != RUN:
        raise TrainNotFound(f"artifact {art.id} is a {art.tool} artifact, not a Proforma run; a train is read from a run")
    scenarios = list(seed_scenarios() if scenarios is None else scenarios)
    t = proforma.tables_of(art)
    sid, sname = scenario_of(art, scenarios)
    stream_id, product, how = product_of(t)
    by_id = {s.id: s for s in t.streams}

    def m(sid_: str) -> float:
        s = by_id.get(sid_)
        return float(s.massFlows.get(product, 0.0)) if (s is not None and product) else 0.0

    def total(ids: list[str]) -> float:
        return float(sum(by_id[i].massFlow for i in ids if i in by_id))

    reach = _reach(stream_id, t.streams) if product else set()

    def onward(sid_: str) -> bool:
        s = by_id.get(sid_)
        return sid_ == stream_id or (s is not None and s.sink in reach)

    units: list[TrainUnit] = []
    for u in sorted(t.units, key=lambda x: x.order):
        row: dict[str, Any] = {"id": u.id, "unitClass": u.unitClass, "line": u.line, "order": u.order, "ins": u.ins,
                               "outs": u.outs, "onPath": u.id in reach, "massIn": total(u.ins), "massOut": total(u.outs)}
        if product:
            p_in, p_out = sum(m(i) for i in u.ins), sum(m(o) for o in u.outs)
            row.update(productIn=p_in, productOut=p_out)
            if u.id not in reach:
                row["note"] = f"off the product's path: no outlet of {u.id} leads to {stream_id}"
            else:
                on = sum(m(o) for o in u.outs if onward(o))
                row.update(productOnward=on, productLost=p_out - on,
                           lostTo=[o for o in u.outs if not onward(o) and m(o) > EPS])
                if p_in <= EPS:
                    row["note"] = (f"no {product} enters {u.id}: the product is formed here" if p_out > EPS
                                   else f"no {product} enters or leaves {u.id}")
                else:
                    row["recovery"] = on / p_in
                    if on > p_in * (1 + 1e-9):
                        row["note"] = f"more {product} leaves {u.id} on its way than enters it: the unit forms product"
        units.append(TrainUnit(**row))

    out = m(stream_id) if (product and stream_id) else None
    lost = sum(u.productLost or 0.0 for u in units if u.onPath) if product else None
    delivered = (out or 0.0) + (lost or 0.0)
    overall = None
    if product and delivered > EPS:
        overall = (out or 0.0) / delivered
        gone = 0.0
        for n, u in enumerate(units):
            if u.onPath:
                gone += u.productLost or 0.0
                units[n] = u.model_copy(update={"cumulative": 1.0 - gone / delivered})
    note = None
    if not t.units:
        note = ("this run was kept before runs carried their tables (OF-BLD-019 §2.1); run the scenario again in "
                "Proforma and its train reads here")
    elif product and not reach:
        note = f"no unit's outlet leads to {stream_id}, so no recovery is read"
    return Train(
        scenarioId=sid, scenarioName=sname, artifactId=art.id, flowsheet=t.flowsheet, createdAt=art.createdAt,
        provenance=provenance or art.provenance,  # type: ignore[arg-type]
        program=program_of(art, sid, scenarios, record_lookup), tablesSource=t.tablesSource,
        productStream=stream_id, product=product, productBasis=how, productOut=out, productLost=lost,
        overallRecovery=overall, units=units, streams=t.streams, tableUnits=t.tableUnits, runs=runs, note=note)


def _runs(arts: Iterable[Artifact], scenarios: list[dict[str, Any]]) -> dict[str, list[Artifact]]:
    """The runs on file by the key a train is known by: its scenario, else
    its own id; newest first."""
    out: dict[str, list[Artifact]] = {}
    for a in arts:
        if a.tool != RUN:
            continue
        sid, _ = scenario_of(a, scenarios)
        out.setdefault(sid or a.id, []).append(a)
    for runs in out.values():
        runs.sort(key=lambda a: a.createdAt, reverse=True)
    return out


def trains(include_archived: bool = False, *, arts: Iterable[Artifact] | None = None,
           scenarios: Iterable[dict[str, Any]] | None = None, record_lookup: Any = None) -> list[Train]:
    """The newest run of every scenario with a run on file (and every run no
    scenario claims), newest first. A train of an archived program is left
    out unless the caller asks for archived programs (OF-BLD-016 §2.R)."""
    from . import artifacts, programs

    scenarios = list(seed_scenarios() if scenarios is None else scenarios)
    kept = list(artifacts.all_artifacts() if arts is None else arts)
    out = []
    for runs in _runs(kept, scenarios).values():
        tr = train_of(runs[0], scenarios=scenarios, runs=len(runs), record_lookup=record_lookup)
        try:
            hidden = programs.hides(tr.program, include_archived)
        except FileNotFoundError:
            hidden = False
        if not hidden:
            out.append(tr)
    return sorted(out, key=lambda tr: tr.createdAt, reverse=True)


def summary(tr: Train) -> TrainSummary:
    return TrainSummary(scenarioId=tr.scenarioId, scenarioName=tr.scenarioName, artifactId=tr.artifactId,
                        flowsheet=tr.flowsheet, createdAt=tr.createdAt, provenance=tr.provenance, program=tr.program,
                        product=tr.product, unitCount=len(tr.units), overallRecovery=tr.overallRecovery, runs=tr.runs,
                        note=tr.note)


def train(key: str, *, arts: Iterable[Artifact] | None = None, scenarios: Iterable[dict[str, Any]] | None = None,
          record_lookup: Any = None) -> Train:
    """The train a scenario id or a run's artifact id names: the newest run
    of that scenario, or that run. A deep link opens whatever program it
    belongs to, as every page opened by id does; the page says the program."""
    from . import artifacts

    scenarios = list(seed_scenarios() if scenarios is None else scenarios)
    kept = list(artifacts.all_artifacts() if arts is None else arts)
    runs = _runs(kept, scenarios)
    if key in runs:
        return train_of(runs[key][0], scenarios=scenarios, runs=len(runs[key]), record_lookup=record_lookup)
    for group in runs.values():
        for a in group:
            if a.id == key:
                return train_of(a, scenarios=scenarios, runs=1, record_lookup=record_lookup)
    other = next((a for a in kept if a.id == key), None)
    if other is not None:
        raise TrainNotFound(f"artifact {key} is a {other.tool} artifact, not a Proforma run; a train is read from a run")
    raise TrainNotFound(f"no Proforma run of {key} is on file here: run the scenario in Proforma, and pureOS reads its "
                        "train from that run")
