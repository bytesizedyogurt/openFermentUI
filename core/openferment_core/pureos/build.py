"""What a model's build does to a train, as data (OF-BLD-020 §5.4; D9, D13).

`pureos_build` and `pureos_write` (tools/writes.py) build a train a step at a
time from ids and words: a product and the artifact its inlet is read from,
then catalogue unit types in order, then the record ids that bind a unit's
parameter, then a run. Every function here takes a train and returns it
changed, or refuses in words (`BuildRefused`); none keeps anything. The change
is kept by `pureos.kept.keep_train`, under its locks, through tools/writes.py,
and a run is `pureos.train_spec.run_train`'s, through the same file.

THE INLET a model names (`inletRef`):
    a kept `fermos.simulation`'s artifact id   its broth at harvest (D10); its
                                               broth flow then waits for a
                                               person's value
    a kept `fermos.vessel`'s artifact id       the harvest of the simulation it
                                               was designed for, the broth
                                               flow read from the design
    `<artifact id>/<stream id>`                a stream of a kept run
                                               (`proforma.run`,
                                               `proforma.reference`,
                                               `pureos.train_run`)

THE PROGRAM a model's train belongs to is its inlet's (the program the inlet
artifact belongs to, `module_stores.artifact_program`), else the one active
program when exactly one is, said so; the product is the one the request
names, else the simulation's.

A UNIT a model adds takes the catalogue's default routing (its onward port
on, every other outlet to waste) and an id of the type's first letter and the
smallest count that is free (`C1`, `D1`, `D2`), BioSTEAM's form for a unit
id. A model types no value: a parameter binds from the records named for it,
the records the rule finds, or the class's own default, else it waits and the
run refuses naming it (a person types it in pureOS → Builder).

WHAT A MODEL READS of a kept train or a run is written here by code, copied
from it: the run's numbers to four significant digits from the artifact, what
bound each parameter in counts and never its value, the artifact id to cite.

Rule 1: no process number here. The constants below are an id's length and
the significant digits a summary prints, each named with its reason.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from ..models import Artifact, Evidence, KeptTrain, TrainInlet, TrainRun, TrainSpec, TrainUnitSpec
from . import catalogue, train_spec

# A kept train's id: `tr-` and this many hex digits of a random UUID (a
# name's length, not a process number).
ID_PREFIX = "tr-"
ID_HEX = 12
# A run's stream in `inletRef`: `<artifact id>/<stream id>`.
STREAM_SEP = "/"
ARTIFACT_ID = re.compile(r"[0-9a-f]{16}")
# The significant digits a summary prints a run's numbers to; the artifact
# holds every number whole (a reading convention, as writes._sig's).
SUMMARY_DIGITS = 4
# A summary's flags and notes, each cut under this many characters at a
# sentence or clause (a reading convention, as writes.MAX_FLAG_CHARS).
MAX_LINE_CHARS = 300


class BuildRefused(ValueError):
    """A step of a model's build that cannot be taken, in words."""


def new_id() -> str:
    return f"{ID_PREFIX}{uuid.uuid4().hex[:ID_HEX]}"


# ── the inlet and the train ────────────────────────────────────────────


def _artifact(aid: str, what: str) -> Artifact:
    from .. import artifacts

    try:
        return artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise BuildRefused(f"there is no kept artifact {aid} here, which {what} names") from None
    except artifacts.ArtifactDamaged as e:
        raise BuildRefused(f"artifact {aid}, which {what} names, cannot be read: {e}") from None


def _hidden(art: Artifact, include_archived: bool) -> None:
    """An archived program's artifact as an inlet, refused with the switch
    off, as the run refuses it (train_spec._shown)."""
    from .. import module_stores, programs

    try:
        program = module_stores.artifact_program(art)
        if not programs.hides(program, include_archived):
            return
        p = programs.program_by_id(program)
    except FileNotFoundError:
        return
    raise BuildRefused(f"artifact {art.id} belongs to {p.name if p else program}, archived (hidden). {programs.SWITCH}")


def inlet_of(inlet_ref: str, include_archived: bool = False) -> tuple[TrainInlet, Artifact, Artifact | None]:
    """The inlet `inletRef` names, the artifact it names, and the kept
    simulation the broth comes from (None for a run's stream)."""
    ref = (inlet_ref or "").strip()
    aid, sep, stream = ref.partition(STREAM_SEP)
    if not aid:
        raise BuildRefused("name the inlet by the artifact it is read from: a kept simulation's artifact id (its harvest), "
                           "a kept vessel design's (the harvest of its simulation, its broth flow read from the design), "
                           f"or a kept run's stream as <artifact id>{STREAM_SEP}<stream id>")
    if not ARTIFACT_ID.fullmatch(aid):
        raise BuildRefused(f"{aid!r} is not an artifact id (sixteen hex digits); fermos_read lists the simulations and "
                           "vessel designs, proforma_read and pureos_read the runs")
    art = _artifact(aid, "inletRef")
    _hidden(art, include_archived)
    if art.tool == train_spec.SIMULATION:
        if sep:
            raise BuildRefused(f"{aid} is a kept simulation, whose harvest is the inlet: it names no stream")
        return TrainInlet(kind="simulation", ref=aid), art, art
    if art.tool == train_spec.VESSEL:
        if sep:
            raise BuildRefused(f"{aid} is a kept vessel design, whose simulation's harvest is the inlet: it names no "
                               "stream")
        o = art.output if isinstance(art.output, dict) else {}
        source, tool = str(o.get("source") or ""), str(o.get("sourceTool") or "")
        if tool != train_spec.SIMULATION or not source:
            raise BuildRefused(f"vessel design {aid} was designed for {tool or 'an artifact'} {source or ''}".rstrip()
                               + ", not a kept simulation: a train's inlet is a simulation's harvest, a vessel design's "
                               "simulation, or a stream of a kept run")
        sim = _artifact(source, f"vessel design {aid}")
        _hidden(sim, include_archived)
        return TrainInlet(kind="simulation", ref=source, vessel=aid), art, sim
    if art.tool in train_spec.STREAM_TOOLS:
        from .. import proforma

        if not stream:
            raise BuildRefused(f"{aid} is a kept run ({art.tool}): name its stream as {aid}{STREAM_SEP}<stream id>; "
                               "stream_table lists a Proforma run's streams, and pureos_read names a train run's product "
                               "stream")
        ids = [s.id for s in proforma.tables_of(art).streams]
        if stream not in ids:
            raise BuildRefused(f"run {aid}'s stream table holds no stream {stream!r}; stream_table lists its streams")
        return TrainInlet(kind="run-stream", ref=aid, streamId=stream), art, None
    raise BuildRefused(f"artifact {aid} is a {art.tool} artifact; a train's inlet is a kept simulation's harvest "
                       f"({train_spec.SIMULATION}), a vessel design's simulation ({train_spec.VESSEL}), or a stream of a "
                       f"kept run ({', '.join(train_spec.STREAM_TOOLS)})")


def _program(art: Artifact) -> tuple[str, str]:
    """The train's program and how it was read, in words."""
    from .. import module_stores, programs

    try:
        program = module_stores.artifact_program(art)
    except FileNotFoundError:
        program = None
    if program:
        return program, f"the program {art.tool} {art.id} belongs to"
    try:
        active = programs.active_programs()
    except FileNotFoundError:
        active = []
    if len(active) == 1:
        return active[0].id, (f"the one active program, {active[0].name}: {art.tool} {art.id} names no program of "
                              "its own")
    raise BuildRefused(f"{art.tool} {art.id} names no program, and there is no one active program to take: a train "
                       "belongs to a program, whose chemicals it is built on")


def new_spec(product: str, inlet_ref: str, include_archived: bool = False) -> tuple[TrainSpec, list[str]]:
    """A new train with no unit yet: its id, a name of words, its program,
    its product and its inlet; and what was read, in words."""
    from .. import params, thermo

    inlet, art, sim = inlet_of(inlet_ref, include_archived)
    said: list[str] = []
    made = str((sim.output or {}).get("product") or "") if sim is not None else ""
    pid = (product or "").strip() or made
    if not pid:
        raise BuildRefused("name the product the train recovers by its id (ethanol): the inlet names none")
    if not re.fullmatch(params._ID, pid):
        raise BuildRefused(f"a product is named by its id; {pid!r} is not one")
    if made and made != pid:
        raise BuildRefused(f"simulation {sim.id} makes {made}; a train recovering {pid} takes another inlet")  # type: ignore[union-attr]
    if not (product or "").strip():
        said.append(f"the product is the simulation's own, {pid}")
    if pid not in thermo.CHEMICALS:
        named = ", ".join(f"{p} ({c})" for p, c in sorted(thermo.CHEMICALS.items()))
        raise BuildRefused(f"a train traces its product by the library's own name for it, and thermo's CHEMICALS names "
                           f"{named}; {pid} is none of them")
    program, how = _program(art)
    said.append(f"the program is {program}: {how}")
    if program not in train_spec.PROGRAM_CHEMICALS:
        raise BuildRefused(f"pureOS builds a train on {', '.join(train_spec.PROGRAM_CHEMICALS.values())}; program "
                           f"{program} has no chemical set here, so its train does not run yet")
    spec = TrainSpec(id=new_id(), name=f"{pid} train, built by a model", program=program, product=pid, inlet=inlet,
                     units=[])
    return spec, said


def _unit(spec: TrainSpec, unit_id: str) -> tuple[int, TrainUnitSpec]:
    n = next((i for i, u in enumerate(spec.units) if u.id == unit_id), None)
    if n is None:
        held = ", ".join(u.id for u in spec.units) or "none yet"
        raise BuildRefused(f"train {spec.id} has no unit {unit_id!r}; its units are {held}")
    return n, spec.units[n]


def _unit_id(spec: TrainSpec, e: catalogue.Entry) -> str:
    """The type's first letter and the smallest count no unit of the train
    holds: BioSTEAM's form for a unit id."""
    taken = {u.id for u in spec.units}
    letter = e.id[0].upper()
    n = 1
    while f"{letter}{n}" in taken:
        n += 1
    return f"{letter}{n}"


def with_unit(spec: TrainSpec, unit_type: str, after: str = "") -> tuple[TrainSpec, str]:
    """The train with a unit of a catalogue type added after the unit named
    (the inlet, or the end when none is named), and the new unit's id."""
    try:
        e = catalogue.entry((unit_type or "").strip())
    except catalogue.CatalogueUnknown as ex:
        raise BuildRefused(f"{ex}; GET /api/pureos/catalogue names what each does") from None
    where = (after or "").strip()
    if not where:
        at = len(spec.units)
    elif where == train_spec.INLET:
        at = 0
    else:
        at = _unit(spec, where)[0] + 1
    uid = _unit_id(spec, e)
    units = [*spec.units[:at], TrainUnitSpec(id=uid, type=e.id), *spec.units[at:]]
    return spec.model_copy(update={"units": units}), uid


def without_unit(spec: TrainSpec, unit_id: str) -> TrainSpec:
    """The train with the unit named taken out; refused while another unit
    recycles to it."""
    n, unit = _unit(spec, (unit_id or "").strip())
    back = [f"{u.id}'s outlet {name}" for u in spec.units for name, route in u.outlets.items()
            if route == f"{train_spec.RECYCLE}{unit.id}"]
    if back:
        raise BuildRefused(f"{', '.join(back)} recycles to {unit.id}: route it elsewhere first")
    return spec.model_copy(update={"units": [*spec.units[:n], *spec.units[n + 1:]]})


def with_records(spec: TrainSpec, unit_id: str, records_by_param: dict[str, list[str]], pool: Any,
                 include_archived: bool = False) -> tuple[TrainSpec, dict[str, dict[str, Any]]]:
    """The train with a unit's parameters bound to exactly the records named
    for each (D13): each must be in the evidence pool the switch shows, a
    record of the field the parameter's source rule names, on the train's
    program's papers, kept by the aggregate gate, naming the unit's step where
    its field says nothing of one, and in a unit the parameter reads; else the
    call is refused naming the record and why. The check is the run's own:
    the unit's scope (`train_spec.unit_scope`), which reads the class's
    parameters in the Proforma worker. Returns, by key, the field and how many
    records bind it; never a value."""
    from .. import params, thermo

    n, unit = _unit(spec, (unit_id or "").strip())
    if not records_by_param:
        raise BuildRefused(f"name at least one parameter of unit {unit.id} and the record ids that bind it "
                           "(recordsByParam)")
    named: dict[str, list[str]] = {}
    for key, ids in records_by_param.items():
        k = (key or "").strip()
        clean = [str(i).strip() for i in ids or []]
        if not clean or any(not i for i in clean):
            raise BuildRefused(f"recordsByParam names no record for {k or 'a key'}: name the record ids that bind it")
        bad = [i for i in clean if not re.fullmatch(params._ID, i)]
        if bad:
            raise BuildRefused(f"a record is named by its id; {', '.join(repr(b) for b in bad)} is not one")
        twice = sorted({i for i in clean if clean.count(i) > 1})
        if twice:
            raise BuildRefused(f"record {', '.join(twice)} is named twice for {k}")
        named[k] = clean
    changed = unit.model_copy(update={"records": {**unit.records, **named}})
    candidate = spec.model_copy(update={"units": [*spec.units[:n], changed, *spec.units[n + 1:]]})
    before = set(train_spec.validate(spec))
    new = [r for r in train_spec.validate(candidate) if r not in before]
    if new:
        raise BuildRefused("; ".join(new))
    try:
        chemicals = train_spec.chemicals_of(candidate, (), include_archived)
        got = train_spec.unit_scope(candidate, changed, chemicals, pool, (), thermo.CHEMICALS.get(spec.product))
    except train_spec.TrainRefused as e:
        raise BuildRefused(f"the train's inlet cannot be read, so no record can be checked against unit {unit.id}: "
                           f"{e}") from None
    refused = list(got.refused)
    keys = {s.key for s in got.provided.specs}
    bound: dict[str, dict[str, Any]] = {}
    for key in named:
        if key not in keys:
            refused.append(f"unit {unit.id}, {key}: not a parameter of unit {unit.id} on this train's chemicals "
                           f"({', '.join(chemicals)})")
            continue
        sources = got.provided.sources.get(key) or {}
        hit = next(((k, v) for k, v in sources.items() if k.startswith("record:") and v is not None), None)
        if hit is None:
            waiting = sources.get("waiting")
            if not any(r.startswith(f"unit {unit.id}, {key}:") for r in refused):
                refused.append(f"unit {unit.id}, {key}: " + (waiting.detail if waiting is not None and waiting.detail
                                                              else "no record named binds it"))
            continue
        bound[key] = {"field": hit[0].split(":", 1)[1], "records": len(hit[1].recordIds)}
    if refused:
        raise BuildRefused("; ".join(refused))
    return candidate, bound


# ── what a model reads ─────────────────────────────────────────────────


def kept_or_refuse(train_id: str) -> KeptTrain:
    """A kept train by its id, or a refusal naming where they are listed."""
    from . import kept

    tid = (train_id or "").strip()
    if not tid:
        raise BuildRefused("name the train by its id (trainId), as new returned it; pureos_read lists the trains a model "
                           "built (kind train)")
    k = kept.kept_train(tid)
    if k is None:
        raise BuildRefused(f"there is no kept train {tid} here; pureos_read lists the trains a model built (kind train)")
    return k


def _sig(x: Any) -> Any:
    return float(f"{x:.{SUMMARY_DIGITS}g}") if isinstance(x, float) else x


def _cut(line: str) -> str:
    """A flag or note whole, or cut at a sentence or clause under
    MAX_LINE_CHARS and said to be cut; the artifact keeps every word."""
    if len(line) <= MAX_LINE_CHARS:
        return line
    head = line[:MAX_LINE_CHARS]
    at = max(head.rfind(". "), head.rfind("; "))
    head = head[:at] if at > 0 else head[:head.rfind(" ")]
    return head.rstrip(" ,;:.") + " (cut here; the artifact holds the whole line)"


def described(k: KeptTrain) -> dict[str, Any]:
    """A kept train as a model reads it: ids and words, what is named for
    each unit, and what still stops it running, in the validation's words."""
    s = k.spec
    units = []
    for u in s.units:
        e = catalogue.entry(u.type)
        units.append({"id": u.id, "type": e.id, "name": e.name, "stage": e.stage, "class": e.cls,
                      "outlets": train_spec.routes(u, e),
                      "recordsNamed": {key: len(ids) for key, ids in u.records.items()}})
    return {
        "trainId": s.id, "name": s.name, "program": s.program, "product": s.product,
        "inlet": {"kind": s.inlet.kind, "ref": s.inlet.ref, "streamId": s.inlet.streamId, "vessel": s.inlet.vessel},
        "units": units, "madeBy": k.madeBy, "at": k.at, "updatedAt": k.updatedAt,
        "toRun": train_spec.validate(s),
    }


def run_evidence(r: TrainRun) -> Evidence:
    """A train run as the one `Evidence` a claim cites it by: its id is the
    artifact's, its value the overall recovery of the product to the product
    stream as the artifact reads it, its provenance and basis the artifact's."""
    tr = r.train
    value: float | str = tr.overallRecovery if tr.overallRecovery is not None else "no recovery read"
    return Evidence(id=r.artifactId, label=(f"Run of train {r.spec.name} ({r.spec.id}): the share of the "
                                            f"{tr.product or r.spec.product} entering the train that leaves by its "
                                            f"product stream, {tr.productStream or 'none named'}"),
                    value=value, unit="", provenance=r.provenance, basis=r.basis, figure="recovery")


def run_summary(r: TrainRun) -> dict[str, Any]:
    """What a model reads of a run, copied from the artifact: each unit, what
    bound each of its parameters in counts (never a value), each unit's
    recovery and the overall to four significant digits, the product's share
    of the product stream, and the flags and notes, cut. The whole run rides
    in the result's data, which no model reads."""
    tr = r.train
    by_unit = {u.id: u for u in tr.units}
    costs = {c.unit: c.costModel for c in r.costs}
    # How many records bind each key, counted from the basis's own
    # `<unit>.<key> record` inputs, one a record.
    named: dict[str, dict[str, int]] = {}
    for i in r.basis.inputs:
        if i.name.endswith(" record") and catalogue.SEP in i.name:
            unit, _, key = i.name[: -len(" record")].partition(catalogue.SEP)
            named.setdefault(unit, {})[key] = named.get(unit, {}).get(key, 0) + 1
    units = []
    for p in r.parameters:
        origins: dict[str, int] = {}
        for v in p.values:
            origins[v.origin] = origins.get(v.origin, 0) + 1
        records = named.get(p.unit, {})
        u = by_unit.get(p.unit)
        units.append({"id": p.unit, "type": p.type, "class": p.unitClass, "boundBy": origins,
                      "recordsBinding": records, "onPath": u.onPath if u else None,
                      "recovery": _sig(u.recovery) if u and u.recovery is not None else None,
                      "lostTo": u.lostTo if u else [], "costModel": costs.get(p.unit)})
    return {
        "trainId": r.spec.id, "name": r.spec.name, "artifactId": r.artifactId, "provenance": r.provenance,
        "product": tr.product, "productStream": tr.productStream,
        "overallRecovery": _sig(tr.overallRecovery) if tr.overallRecovery is not None else None,
        "productShareOfProductStream": _sig(r.purity.productFraction) if r.purity.productFraction is not None else None,
        "inlet": {"kind": r.inlet.kind, "ref": r.inlet.ref, "streamId": r.inlet.streamId, "vessel": r.inlet.vessel},
        "units": units,
        "flags": [_cut(f) for f in r.flags], "notes": [_cut(n) for n in r.notes],
        "read": (f"from the artifact, to {SUMMARY_DIGITS} significant digits; what bound each parameter is counted by "
                 "origin, and its value is in the artifact; cite the run by its evidence id, never the number"),
    }
