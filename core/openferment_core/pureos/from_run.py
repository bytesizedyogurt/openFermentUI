"""A run's train, read into the Builder (OF-BLD-020 §5.3, D9).

    from_run(artifact_id, train_id=None) -> TrainFromRun

A kept run (a `proforma.run`, a `proforma.reference` or a `pureos.train_run`)
holds its stream and unit tables (`proforma.tables_of`). This reads them into
a `TrainSpec` the Builder opens, as data, and never computes a quantity:

    which units   every unit the product passes through: on the product's path
                  (pureOS's own reading of the path, by pass: `pureos._leads_on`)
                  with the product entering it in the run's stream table, in
                  run order, whose BioSTEAM class (or in-house class) is a
                  catalogue type's, the catalogue's id taking it; a unit off the
                  path, one the product does not enter (upstream of the broth,
                  the fermenter that forms it, a side line such as a blend's
                  other component), one whose class no type holds, or one whose
                  outlets the type's ports do not match one for one, is named in
                  `unmapped` with why, in words
    the inlet     the run's own stream entering the first unit taken (its first
                  inlet, BioSTEAM's feed), a `run-stream` inlet on that run
    the outlets   each outlet routed as the run routed it, followed through the
                  units the train leaves out: on to the next unit taken (or, for
                  the last, to the product stream), back to an earlier one (a
                  recycle, when that unit's inlet takes several streams), else to
                  waste; when two outlets lead on, the one carrying the more
                  product goes on and the run's numbers say so (the product's
                  kg/hr as its stream table holds them, compared, never made)
    the values    a run of a shelf flowsheet the worker builds case by case
                  (`proforma.run` on a non-reference entry) gives each unit taken
                  `readFrom` that flowsheet's own unit of the same id: its values
                  are the package's, read in the worker as `model` inputs naming
                  its version when the train runs (§5.2); a run of a flowsheet
                  built from parts (`custom_train_v1`, its shelf entry's
                  `builtFrom`) is not read so, since the worker reads no unit of
                  it: each unit of the train run its basis names takes that
                  train's own flowsheet unit and named records, and the notes
                  name what a person typed there (§5.R part a, findings 3, 14
                  and 24); any other run's units stay at their classes'
                  defaults, and what waits, waits
    the product   the chemical the run traced (pureOS's reading of the run) and
                  the product id `thermo.CHEMICALS` names for it; a run whose
                  product no id names here, or that names no product, is refused
                  in words, as is one naming no chemical set, or with no unit
                  to take

The train's structure is held to `validate` and its refusals are returned
beside it, for a person to settle in the Builder. Nothing is kept: the
Builder keeps the train when a person saves it.

Rule 1: no number in this file. Every value a unit takes is the package's,
read in the worker, a class's default, a record's or a person's.
"""
from __future__ import annotations

from typing import Any

from ..models import (
    Artifact,
    TrainFromRun,
    TrainInlet,
    TrainSpec,
    TrainUnitReadFrom,
    TrainUnitSpec,
    TrainUnmapped,
)
from . import catalogue
from .train_spec import ONWARD, RECYCLE, UNIT_ID, WASTE, TrainRefused, validate

# The runs whose tables a train is read from.
RUN = "proforma.run"
REFERENCE = "proforma.reference"
TRAIN_RUN = "pureos.train_run"
RUN_TOOLS = (RUN, REFERENCE, TRAIN_RUN)


class RunNotOnFile(LookupError):
    """No kept artifact by that id (a 404)."""


def _by_class() -> dict[str, catalogue.Entry]:
    """Each catalogue type by the class it builds: BioSTEAM's name, or the
    in-house class's."""
    return {e.cls: e for e in catalogue.UNIT_TYPES}


def _product_id(chemical: str) -> str | None:
    from .. import thermo

    return next((pid for pid, chem in thermo.CHEMICALS.items() if chem == chemical), None)


def _read(art: Artifact) -> tuple[Any, str | None, str | None, str | None, str | None, str]:
    """(the tables, the product stream, the chemical traced, the product id,
    the program, what the run is called) for a kept run."""
    from .. import proforma
    from . import _train_product, product_of, program_of, program_of_run, scenario_of, held_scenarios

    t = proforma.tables_of(art)
    o = art.output if isinstance(art.output, dict) else {}
    if art.tool == TRAIN_RUN:
        stream_id, chem, _ = _train_product(art, t)
        pid = str(o.get("productId") or "") or (_product_id(chem) if chem else None)
        program = program_of_run(art)
        spec = o.get("train") or {}
        label = str(spec.get('name') or spec.get('id') or art.id)
    else:
        stream_id, chem, how = product_of(t)
        if not chem:
            raise TrainRefused(f"run {art.id} names no product to trace ({how}), so no train is read from it")
        pid = _product_id(chem)
        scenarios = held_scenarios() if art.tool == RUN else []
        sid, sname = scenario_of(art, scenarios) if art.tool == RUN else (None, None)
        program = program_of(art, sid, scenarios)
        label = sname or t.flowsheet or art.id
    if not chem or not stream_id:
        raise TrainRefused(f"run {art.id} names no product stream, so no train is read from it")
    if not pid:
        from .. import thermo

        raise TrainRefused(f"run {art.id} traces {chem}, which no product a train traces here is "
                           f"({', '.join(f'{k}: {v}' for k, v in thermo.CHEMICALS.items())})")
    if not program:
        raise TrainRefused(f"run {art.id} belongs to no program, and a train is one program's")
    return t, stream_id, chem, pid, program, label


def _reads_from(art: Artifact, flowsheet: str | None) -> str | None:
    """The shelf flowsheet whose own units a train read from this run takes
    its values from: a run of one the worker builds case by case. A
    reference runs whole, and the worker reads no unit of a flowsheet built
    from parts (§5.R part a)."""
    from ..flowsheets import shelf

    if art.tool != RUN or not flowsheet:
        return None
    try:
        info = shelf.info(flowsheet)
    except shelf.NotOnShelf:
        return None
    return None if info.reference or info.builtFrom else info.id


def _parts_train(art: Artifact, flowsheet: str | None) -> tuple[str | None, TrainSpec | None, str | None]:
    """For a run of a flowsheet built from parts: the train run its basis
    names, that run's train as data, and why it is not read when it is not."""
    from .. import artifacts
    from ..flowsheets import shelf

    if art.tool != RUN or not flowsheet:
        return None, None, None
    try:
        if not shelf.info(flowsheet).builtFrom:
            return None, None, None
    except shelf.NotOnShelf:
        return None, None, None
    named = next((i for i in art.inputs if i.name == "train run" and i.source.kind == "artifact"), None)
    if named is None:
        return None, None, f"run {art.id}'s basis names no train run"
    rid = str(named.source.id or named.value)
    try:
        tr = artifacts.get(rid)
        return rid, TrainSpec.model_validate((tr.output or {})["train"]), None
    except artifacts.ArtifactNotFound:
        return rid, None, f"train run {rid}, which run {art.id} names, is not on file here"
    except (artifacts.ArtifactDamaged, KeyError, TypeError, ValueError):
        return rid, None, f"train run {rid}, which run {art.id} names, cannot be read"


def from_run(artifact_id: str, train_id: str | None = None) -> TrainFromRun:
    """POST /api/pureos/train/from-run: the run's units, each by its class,
    into a train (module docstring); nothing is kept."""
    from .. import artifacts
    from . import EPS, _leads_on, passes

    try:
        art = artifacts.get(artifact_id)
    except artifacts.ArtifactNotFound:
        raise RunNotOnFile(f"there is no kept artifact {artifact_id} here: a train is read from a kept run (a Proforma "
                           "run, a reference run or a pureOS train run)") from None
    if art.tool not in RUN_TOOLS:
        raise TrainRefused(f"artifact {art.id} is a {art.tool} artifact; a train is read from a run ("
                           f"{', '.join(RUN_TOOLS)})")
    t, stream_id, chem, pid, program, label = _read(art)
    streams = {s.id: s for s in t.streams}
    leads = _leads_on(stream_id, t.streams, t.units)
    by_class = _by_class()
    unmapped: list[TrainUnmapped] = []
    taken: list[tuple[Any, catalogue.Entry]] = []

    def carries(sid: str) -> float:
        row = streams.get(sid)
        return float(row.massFlows.get(chem or "", 0.0)) if row is not None else 0.0

    for u in sorted(t.units, key=lambda x: x.order):
        if not any(o in leads for _, outs in passes(u) for o in outs):
            unmapped.append(TrainUnmapped(unitId=u.id, unitClass=u.unitClass, why=(
                f"off the product's path: no outlet of {u.id} leads to {stream_id}, and a train is the line the "
                "product takes")))
            continue
        # A train is what the product passes through: a unit the run's stream
        # table shows no product entering is upstream of the broth, or forms
        # the product (a fermenter), or carries a side line (a blend's other
        # component) into the path, and the train starts where the product
        # enters (pureOS's own reading, as train_of says "formed here").
        if not any(carries(s) > EPS for s in u.ins):
            unmapped.append(TrainUnmapped(unitId=u.id, unitClass=u.unitClass, why=(
                f"no {chem} enters {u.id} in the run: it is upstream of the broth, forms the product, or brings "
                "another stream to the path, and a train is what the product passes through")))
            continue
        e = by_class.get(u.unitClass)
        if e is None:
            unmapped.append(TrainUnmapped(unitId=u.id, unitClass=u.unitClass, why=(
                f"{u.unitClass} is no unit type of pureOS's catalogue, so the train passes on what enters it without "
                "it")))
            continue
        ports = [p for p in e.ports if p.side == "out"]
        if len(ports) != len(u.outs):
            unmapped.append(TrainUnmapped(unitId=u.id, unitClass=u.unitClass, why=(
                f"{u.id} has {len(u.outs)} outlet{'' if len(u.outs) == 1 else 's'} in the run, and the catalogue's "
                f"{e.id} has {len(ports)}: its outlets cannot be routed one for one")))
            continue
        taken.append((u, e))
    if not taken:
        raise TrainRefused(f"no unit of run {art.id} that its product passes through is a unit type of pureOS's catalogue, "
                           "so no train is read from it: "
                           + "; ".join(f"{m.unitId} ({m.unitClass}): {m.why}" for m in unmapped))
    ids = [u.id for u, _ in taken]
    units = {u.id: u for u in t.units}
    notes: list[str] = []

    def reaches(sid: str) -> tuple[set[str], bool]:
        """The units taken that a stream reaches first, through units the
        train leaves out (by pass), and whether it reaches the product
        stream."""
        found: set[str] = set()
        product = False
        stack, seen = [sid], {sid}
        while stack:
            s = stack.pop()
            product = product or s == stream_id
            row = streams.get(s)
            sink = row.sink if row is not None else None
            if not sink:
                continue
            if sink in ids:
                found.add(sink)
                continue
            u = units.get(sink)
            if u is None:
                continue
            nexts = next((outs for ins, outs in passes(u) if s in ins), list(u.outs))
            for n in nexts:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        return found, product

    def own_id(uid: str, n: int) -> str:
        return uid if UNIT_ID.fullmatch(uid) and uid != "inlet" else f"U{n + 1}"

    names = {uid: own_id(uid, n) for n, uid in enumerate(ids)}
    reads = _reads_from(art, t.flowsheet)
    # §5.R (part a): a composite's train units are its train run's own.
    parts_id, parts, parts_why = _parts_train(art, t.flowsheet)
    own = {x.id: x for x in parts.units} if parts is not None else {}
    carried: list[str] = []
    typed: list[str] = []
    spec_units: list[TrainUnitSpec] = []
    for k, (u, e) in enumerate(taken):
        nxt = ids[k + 1] if k + 1 < len(ids) else None
        ports = [p for p in e.ports if p.side == "out"]
        routes: dict[str, str] = {}
        onward: list[tuple[str, str]] = []
        for p, sid in zip(ports, u.outs):
            found, product = reaches(sid)
            if (nxt is not None and nxt in found) or (nxt is None and product):
                onward.append((p.name, sid))
                routes[p.name] = ONWARD
                continue
            back = [x for x in ids[:k] if x in found]
            if back:
                target = back[-1]
                te = next(entry for tu, entry in taken if tu.id == target)
                up = next((q for q in te.ports if q.side == "in" and q.source == "upstream"), None)
                if up is not None and up.many:
                    routes[p.name] = f"{RECYCLE}{names[target]}"
                    continue
                notes.append(f"Unit {names[u.id]}'s outlet {p.name} ({sid}) runs back to {names[target]} in the run, whose "
                             f"inlet takes one stream in the catalogue's {te.id}: it goes to waste in the train.")
            routes[p.name] = WASTE
        if len(onward) > 1:
            keep = max(onward, key=lambda x: carries(x[1]))
            for name, sid in onward:
                if name != keep[0]:
                    routes[name] = WASTE
            notes.append(f"Unit {names[u.id]}: outlets {', '.join(n for n, _ in onward)} all lead on in the run; "
                         f"{keep[0]} ({keep[1]}) carries the more {chem} by the run's stream table and goes on, and "
                         "the others go to waste in the train.")
        elif not onward:
            on_path = [(p.name, sid) for p, sid in zip(ports, u.outs) if sid in leads]
            if on_path:
                keep = max(on_path, key=lambda x: carries(x[1]))
                routes[keep[0]] = ONWARD
                notes.append(f"Unit {names[u.id]}: no outlet reaches "
                             f"{'the next unit taken, ' + names[nxt] if nxt else 'the product stream'} directly in the "
                             f"run; {keep[0]} ({keep[1]}), on the product's path, goes on.")
        between = []
        if nxt is not None:
            order = {x.id: x.order for x in t.units}
            between = [x for x in sorted(t.units, key=lambda y: y.order)
                       if order[u.id] < x.order < order[nxt] and x.id not in ids
                       and any(o in leads for _, outs in passes(x) for o in outs)]
        if between:
            notes.append(f"Unit {names[u.id]}'s onward outlet goes straight to {names[nxt]} in the train; between them "
                         "the run passes it through " + ", ".join(f"{x.id} ({x.unitClass})" for x in between)
                         + ", which the train leaves out.")
        theirs = own.get(u.id)
        if theirs is not None and theirs.type == e.id:
            carried.append(names[u.id])
            typed += [f"{names[u.id]}.{key} ({tp.by})" for key, tp in theirs.params.items()]
            spec_units.append(TrainUnitSpec(id=names[u.id], type=e.id, outlets=routes, records=dict(theirs.records),
                                            readFrom=theirs.readFrom))
            continue
        spec_units.append(TrainUnitSpec(
            id=names[u.id], type=e.id, outlets=routes,
            readFrom=TrainUnitReadFrom(flowsheet=reads, unit=u.id) if reads else None))
    first = taken[0][0]
    if not first.ins:
        raise TrainRefused(f"unit {first.id}, the first of run {art.id}'s train, has no inlet in its unit table")
    inlet_id = first.ins[0]
    if len(first.ins) > 1:
        notes.append(f"The inlet is {inlet_id}, the first inlet of {first.id} in the run; "
                     f"{', '.join(first.ins[1:])} also entered it there, which the train leaves out.")
    else:
        notes.append(f"The inlet is {inlet_id}, the stream entering {first.id} in the run, as its stream table holds it.")
    renamed = [f"{uid} as {names[uid]}" for uid in ids if names[uid] != uid]
    if renamed:
        notes.append(f"A unit id BioSTEAM would not take is renamed: {', '.join(renamed)}.")
    if parts_id is not None or parts_why is not None:
        notes.append(f"Run {art.id} is of {t.flowsheet}, built from a vessel design and a train run: the worker reads no "
                     "unit of it, so no unit here reads from it. " + (
                         f"{', '.join(carried) or 'No unit taken'} {'takes' if len(carried) == 1 else 'take'} the "
                         f"flowsheet unit and the records, where any, that train run {parts_id} named for "
                         f"{'it' if len(carried) == 1 else 'them'}"
                         + (f"; what a person typed there is theirs and not carried: {', '.join(typed)}" if typed else "")
                         + "; every other value starts at its class's own default."
                         if parts is not None else f"Its train is not read ({parts_why}): each unit starts at its "
                                                   "class's own defaults."))
    else:
        notes.append(f"Each unit reads its values from {reads}'s own unit of the same id, as the package builds it: a "
                     "model input naming the package's version when the train runs." if reads else
                     "Each unit starts at its class's own defaults: a value its class requires and gives none for waits "
                     "for a record or a person in the Builder.")
    spec = TrainSpec(
        id=train_id or f"from-{art.id}", name=f"The train of {label}", program=program, product=pid,
        inlet=TrainInlet(kind="run-stream", ref=art.id, streamId=inlet_id), units=spec_units)
    return TrainFromRun(train=spec, unmapped=unmapped, notes=notes, refusals=validate(spec))
