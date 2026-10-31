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
and the outlets are named, and product that enters a unit on the path and
leaves by no outlet is lost there too. Both masses, in and out, are kept
beside it.

BY PASS, NOT BY UNIT (§4.R). Which streams lead on is worked out stream by
stream: a stream leads on when the outlets its sink unit sends it to do. A
unit joins every inlet to every outlet, except one whose passes BioSTEAM
keeps apart (`SEPARATE_PASSES`): a process heat exchanger heats the beer on
one side and cools the column's bottoms on the other, and the bottoms never
join the beer. Such a unit is credited only on the passes that lead on, so
the column loses its bottoms and the exchanger passes on all the beer.

THE PRODUCT is the component the run's price is per: of the stream the
run's TEA prices, the one component whose flow is the TEA's basis flow,
when exactly one is; else that stream's largest component. A run with no
TEA (the toy) names no product: its train lists units and masses and no
recovery, and says why.

WHICH SCENARIO a run belongs to: a basis input named `scenario`, when the
run carries one; else the one held scenario (the module projection's, none
since alpha 2.0 deleted the seed's) whose `modelId` is the run's flowsheet.
A run no scenario claims is a train known by its artifact id.

THE PACKAGE (OF-BLD-020 §5.1). This module was pureos.py; it became the
package so the train's pieces live beside it. `pureos.catalogue` is the unit
catalogue (data, served without BioSTEAM; the functions that read a class's
defaults import BioSTEAM inside themselves and run in the Proforma worker),
and `pureos.inhouse` holds the three `bst.Unit` subclasses BioSTEAM lacks,
imported by the worker alone. This module imports the in-house units never,
and the catalogue only through `pureos.train_spec` (data: no BioSTEAM).

A TRAIN RUN IS READ AS A RUN IS (OF-BLD-020 §5.2). `pureos.train_spec` holds the
train as data (`validate`, `inlet_stream`, `run_train`, re-exported here):
one `pureos.train_run` artifact keeps the tables as `proforma.tables_of`
reads them, so `train_of` reads a train run as it reads a Proforma run, by
pass; a train run has no TEA, so its product is the chemical the run traced
(the artifact's own `product`) and its product stream the last unit's onward
outlet (`productStream`). `trains()` and `train()` list and open train runs
beside Proforma's: a train run is known by its train's id (its newest run
read), or by its artifact id.

A TRAIN PROPOSED BY RULES (OF-BLD-020 §7.2, D12). `pureos.proposer` reads a
product's class and the properties its class's rule splits on (thermosteam's
volatility, ProtParam on its sequence, where the products catalogue holds one)
and proposes a `TrainSpec` with every parameter at its library default or
waiting, each unit with its reason; `propose` is re-exported here.
"""
from __future__ import annotations

from typing import Any, Iterable

from ..models import Artifact, ProformaTables, StreamRow, Train, TrainSummary, TrainUnit

RUN = "proforma.run"
# A pureOS train run (OF-BLD-020 §5.2), read as a run is.
TRAIN_RUN = "pureos.train_run"
TABLE_RUNS = (RUN, TRAIN_RUN)
# kg/hr: a flow at or below this carries nothing.
EPS = 1e-9
# A share of the product entering a unit below which what does not leave it
# is the float's rounding, not product lost (a precision, not a process number).
ROUNDING = 1e-9
# BioSTEAM unit classes whose passes stay apart: inlet i leaves by outlet i
# and by no other. `HXprocess._run` copies ins[0] to outs[0] and ins[1] to
# outs[1] and exchanges heat between them (biosteam/units/heat_exchange.py,
# BioSTEAM 2.54.0). No other class in BioSTEAM's units package is shown by
# its source to keep its passes apart, so every other unit is one pass.
SEPARATE_PASSES = frozenset({"HXprocess"})


class TrainNotFound(LookupError):
    """No run on file answers to the key; the message says how one gets there."""


# ── what the run names ───────────────────────────────────────────────────


def _flowsheet(art: Artifact) -> str | None:
    named = art.output.get("flowsheet") if isinstance(art.output, dict) else None
    return str(named) if named else next((str(i.value) for i in art.inputs if i.name == "flowsheet"), None)


def held_scenarios() -> list[dict[str, Any]]:
    """The scenarios the service holds, from the module projection; none
    since the seed went (alpha 2.0, ADR-010), and then only a run's own
    `scenario` input names its scenario."""
    from .. import module_stores

    return list(module_stores._projection()["proforma"]["scenarios"])


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


def program_of(art: Artifact, scenario_id: str | None, scenarios: Iterable[dict[str, Any]]) -> str | None:
    """A train's chemical set: its scenario's, else its flowsheet's on the shelf."""
    from ..flowsheets import shelf as _shelf

    found: list[str | None] = [next((s.get("program") for s in scenarios if s["id"] == scenario_id), None)]
    try:
        found.append(_shelf.info(_flowsheet(art) or "", allow_toy=True).program)
    except _shelf.NotOnShelf:
        pass
    kept = [p for p in found if p]
    return kept[0] if kept else None


def _kept_tables(art: Artifact) -> bool:
    """Whether the run was kept with its tables' keys (OF-BLD-019 §2.1 on),
    even empty ones; a run kept before them holds none of the keys."""
    o = art.output if isinstance(art.output, dict) else {}
    return any(k in o for k in ("tea", "streams", "units"))


def _base_infeasible(art: Artifact) -> str | None:
    o = art.output if isinstance(art.output, dict) else {}
    why = o.get("baseInfeasible")
    return str(why) if why else None


def product_of(t: ProformaTables, *, no_tea: str | None = None) -> tuple[str | None, str | None, str]:
    """(the product stream, the component traced, how it was read in words).
    `no_tea` says why a run holds no TEA when the reason is not that its
    flowsheet prices nothing (a base case that could not run, a run kept
    before the tables)."""
    if t.tea is None:
        return None, None, no_tea or "this run has no TEA, so it names no product and no recovery is read"
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


def passes(u: Any) -> list[tuple[list[str], list[str]]]:
    """A unit's passes, each (inlets, outlets): one per inlet for a class
    whose passes stay apart, when its row lists as many outlets as inlets;
    else one pass joining every inlet to every outlet."""
    if u.unitClass in SEPARATE_PASSES and len(u.ins) == len(u.outs):
        return [([i], [o]) for i, o in zip(u.ins, u.outs)]
    return [(list(u.ins), list(u.outs))]


def _leads_on(product_stream: str | None, streams: list[StreamRow], units: list[Any]) -> set[str]:
    """Every stream that leads to the product stream: the product stream,
    and each stream whose sink unit passes it into one that does (by pass)."""
    if not product_stream or not any(s.id == product_stream for s in streams):
        return set()
    by_unit = {u.id: u for u in units}
    sends: dict[str, list[str]] = {}
    for s in streams:
        if not s.sink:
            continue
        u = by_unit.get(s.sink)
        if u is None:  # a sink with no row in the unit table: one pass, from its streams
            sends[s.id] = [x.id for x in streams if x.source == s.sink]
        else:
            sends[s.id] = next((outs for ins, outs in passes(u) if s.id in ins), list(u.outs))
    on = {product_stream}
    grew = True
    while grew:
        grew = False
        for sid, nexts in sends.items():
            if sid not in on and any(n in on for n in nexts):
                on.add(sid)
                grew = True
    return on


def _train_product(art: Artifact, t: ProformaTables) -> tuple[str | None, str | None, str]:
    """A train run's product and its stream, from the artifact's own words:
    the chemical the run traced and the last unit's onward outlet."""
    o = art.output if isinstance(art.output, dict) else {}
    stream, product, pid = o.get("productStream"), o.get("product"), o.get("productId")
    if not stream or not product:
        return stream, product, "this train run names no product stream, so no recovery is read"
    if not any(s.id == stream for s in t.streams):
        return stream, product, f"the train run names {stream} as its product stream, and its table holds no such stream"
    return stream, product, (f"{product} in {stream}: the library's chemical for the train's product, {pid}, traced to "
                             "the last unit's onward outlet")


def train_of(art: Artifact, *, scenarios: Iterable[dict[str, Any]] | None = None, provenance: str | None = None,
             runs: int = 1) -> Train:
    """One run's train, read from its stream and unit tables alone: a
    Proforma run's, or a pureOS train run's (OF-BLD-020 §5.2)."""
    from .. import proforma

    if art.tool not in TABLE_RUNS:
        raise TrainNotFound(f"artifact {art.id} is a {art.tool} artifact, not a Proforma run or a train run; a train is "
                            "read from a run")
    t = proforma.tables_of(art)
    train_id = train_name = None
    if art.tool == TRAIN_RUN:
        from . import train_spec as _train

        scenarios = []
        sid = sname = None
        infeasible = None
        stream_id, product, how = _train_product(art, t)
        spec = (art.output or {}).get("train") or {}
        train_id, train_name = spec.get("id"), spec.get("name")
        program = _train.program_of_run(art)
    else:
        scenarios = list(held_scenarios() if scenarios is None else scenarios)
        sid, sname = scenario_of(art, scenarios)
        infeasible = _base_infeasible(art)
        no_tea = (f"the base case could not run ({infeasible}), so the run kept no tables, names no product and reads "
                  "no recovery" if infeasible else
                  None if _kept_tables(art) else
                  "this run was kept before runs carried their tables (OF-BLD-019 §2.1), so it names no product here "
                  "and reads no recovery")
        stream_id, product, how = product_of(t, no_tea=no_tea)
        program = program_of(art, sid, scenarios)
    by_id = {s.id: s for s in t.streams}

    def m(sid_: str) -> float:
        s = by_id.get(sid_)
        return float(s.massFlows.get(product, 0.0)) if (s is not None and product) else 0.0

    def total(ids: list[str]) -> float:
        return float(sum(by_id[i].massFlow for i in ids if i in by_id))

    leads = _leads_on(stream_id, t.streams, t.units) if product else set()

    units: list[TrainUnit] = []
    for u in sorted(t.units, key=lambda x: x.order):
        on_path = [(ins, outs) for ins, outs in passes(u) if any(o in leads for o in outs)]
        row: dict[str, Any] = {"id": u.id, "unitClass": u.unitClass, "line": u.line, "order": u.order, "ins": u.ins,
                               "outs": u.outs, "onPath": bool(on_path), "massIn": total(u.ins), "massOut": total(u.outs)}
        if product and not on_path:
            row.update(productIn=sum(m(i) for i in u.ins), productOut=sum(m(o) for o in u.outs),
                       note=f"off the product's path: no outlet of {u.id} leads to {stream_id}")
        elif product:
            # Only the passes on the path are credited: another pass's product
            # was counted where it left the path, or never was on it.
            ins = [i for p_ins, _ in on_path for i in p_ins]
            outs = [o for _, p_outs in on_path for o in p_outs]
            p_in, p_out = sum(m(i) for i in ins), sum(m(o) for o in outs)
            on = sum(m(o) for o in outs if o in leads)
            kept = p_in - p_out if p_in - p_out > ROUNDING * p_in else 0.0  # entered, and left by no outlet
            row.update(productIn=p_in, productOut=p_out, productOnward=on, productLost=(p_out - on) + kept,
                       lostTo=[o for o in outs if o not in leads and m(o) > EPS])
            notes = []
            apart = [(p_ins, p_outs) for p_ins, p_outs in passes(u) if (p_ins, p_outs) not in on_path]
            if apart:
                notes.append("only the pass " + "; ".join(f"{', '.join(a)} → {', '.join(b)}" for a, b in on_path) +
                             " is on the product's path; the pass " +
                             "; ".join(f"{', '.join(a)} → {', '.join(b)}" for a, b in apart) +
                             f" is kept apart by {u.unitClass} and is not counted here")
            if p_in <= EPS:
                notes.append(f"no {product} enters {u.id}: the product is formed here" if p_out > EPS
                             else f"no {product} enters or leaves {u.id}")
            else:
                row["recovery"] = on / p_in
                if on > p_in * (1 + 1e-9):
                    notes.append(f"more {product} leaves {u.id} on its way than enters it: the unit forms product")
                if kept:
                    notes.append(f"some of the {product} entering {u.id} leaves it by no outlet, and is counted lost here")
            if notes:
                row["note"] = "; ".join(notes)
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
    if infeasible:
        note = (f"the base case could not run ({infeasible}), so the run kept no tables and no train is read; change "
                "the inputs it cannot hold in Proforma and run it again")
    elif not t.units:
        note = ("this run was kept before runs carried their tables (OF-BLD-019 §2.1); run the scenario again in "
                "Proforma and its train reads here" if not _kept_tables(art) else "this run kept no unit table")
    elif product and not any(u.onPath for u in units):
        note = f"no unit's outlet leads to {stream_id}, so no recovery is read"
    return Train(
        scenarioId=sid, scenarioName=sname, artifactId=art.id, flowsheet=t.flowsheet, createdAt=art.createdAt,
        provenance=provenance or art.provenance,  # type: ignore[arg-type]
        program=program, tablesSource=t.tablesSource,
        productStream=stream_id, product=product, productBasis=how, productOut=out, productLost=lost,
        overallRecovery=overall, units=units, streams=t.streams, tableUnits=t.tableUnits, runs=runs, note=note,
        tool=art.tool, trainId=train_id, trainName=train_name)


class _Marks:
    """What each run is worth now (§4.R): `basis_provenance` over its inputs
    as they stand, the pool's records and the store's artifacts, as
    `module_stores` works out the mark pureos_read gives the same train. The
    pool is loaded once, and only for a run that binds a record."""

    def __init__(self, kept: list[Artifact], records_by_id: Any = None):
        self.kept = {a.id: a for a in kept}
        self.records_by_id = records_by_id

    def __call__(self, art: Artifact) -> str:
        from ..artifacts import basis_of
        from ..basis import basis_provenance

        kinds = {i.source.kind for i in art.inputs}
        if "record" in kinds and self.records_by_id is None:
            from .. import evidence_pool

            self.records_by_id = evidence_pool.load().records_by_id
        records = self.records_by_id if "record" in kinds else {}
        return basis_provenance(basis_of(art), records or {}, self.kept if "artifact" in kinds else {})


def _runs(arts: Iterable[Artifact], scenarios: list[dict[str, Any]]) -> dict[str, list[Artifact]]:
    """The runs on file by the key a train is known by: a Proforma run's
    scenario, else its own id; a train run's train id (OF-BLD-020 §5.2), else
    its own id; newest first."""
    out: dict[str, list[Artifact]] = {}
    for a in arts:
        if a.tool == RUN:
            sid, _ = scenario_of(a, scenarios)
        elif a.tool == TRAIN_RUN:
            spec = (a.output or {}).get("train") if isinstance(a.output, dict) else None
            sid = spec.get("id") if isinstance(spec, dict) else None
        else:
            continue
        out.setdefault(sid or a.id, []).append(a)
    for runs in out.values():
        runs.sort(key=lambda a: a.createdAt, reverse=True)
    return out


def trains(*, arts: Iterable[Artifact] | None = None,
           scenarios: Iterable[dict[str, Any]] | None = None, records_by_id: Any = None) -> list[Train]:
    """The newest run of every scenario with a run on file (and every run no
    scenario claims), newest first. Each train's provenance is its run's
    worth now, as pureos_read gives it."""
    from .. import artifacts

    scenarios = list(held_scenarios() if scenarios is None else scenarios)
    kept = list(artifacts.all_artifacts() if arts is None else arts)
    mark = _Marks(kept, records_by_id)
    out = []
    for runs in _runs(kept, scenarios).values():
        tr = train_of(runs[0], scenarios=scenarios, provenance=mark(runs[0]), runs=len(runs))
        out.append(tr)
    return sorted(out, key=lambda tr: tr.createdAt, reverse=True)


def summary(tr: Train) -> TrainSummary:
    return TrainSummary(scenarioId=tr.scenarioId, scenarioName=tr.scenarioName, artifactId=tr.artifactId,
                        flowsheet=tr.flowsheet, createdAt=tr.createdAt, provenance=tr.provenance, program=tr.program,
                        product=tr.product, unitCount=len(tr.units), overallRecovery=tr.overallRecovery, runs=tr.runs,
                        note=tr.note, tool=tr.tool, trainId=tr.trainId, trainName=tr.trainName)


def train(key: str, *, arts: Iterable[Artifact] | None = None, scenarios: Iterable[dict[str, Any]] | None = None,
          records_by_id: Any = None) -> Train:
    """The train a scenario id or a run's artifact id names: the newest run
    of that scenario, or that run. Its provenance is the run's worth now, as
    pureos_read gives it."""
    from .. import artifacts

    scenarios = list(held_scenarios() if scenarios is None else scenarios)
    kept = list(artifacts.all_artifacts() if arts is None else arts)
    mark = _Marks(kept, records_by_id)
    runs = _runs(kept, scenarios)
    if key in runs:
        a = runs[key][0]
        return train_of(a, scenarios=scenarios, provenance=mark(a), runs=len(runs[key]))
    for group in runs.values():
        for a in group:
            if a.id == key:
                return train_of(a, scenarios=scenarios, provenance=mark(a), runs=1)
    other = next((a for a in kept if a.id == key), None)
    if other is not None:
        raise TrainNotFound(f"artifact {key} is a {other.tool} artifact, not a Proforma run or a train run; a train is "
                            "read from a run")
    raise TrainNotFound(f"no Proforma run of {key} is on file here: run the scenario in Proforma, and pureOS reads its "
                        "train from that run; a train built in pureOS is read by its id once it has run")


# OF-BLD-020 §5.2: the train as data, re-exported (pureos.train_spec imports this
# package's readers inside its functions, so the import order is safe).
from .train_spec import (  # noqa: E402, F401 (re-exported: pureos.run_train and kin)
    TrainRefused,
    check_train,
    inlet_stream,
    program_of_run,
    run_of,
    run_train,
    train_runs,
    validate,
    validation,
)

# OF-BLD-020 §7.2: a train proposed by written rules, re-exported as
# pureos.propose (the module is `proposer`, so the function shadows no module).
from .proposer import ProposeRefused, ProposeUnknown, propose  # noqa: E402, F401
# OF-BLD-020 §5.3: a run's units read into a train for the Builder.
from .from_run import RunNotOnFile, from_run  # noqa: E402, F401
