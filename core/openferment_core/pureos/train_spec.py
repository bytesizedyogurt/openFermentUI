"""pureOS's train: data, checked, resolved, run, and kept (OF-BLD-020 §5.2;
D9, D10, E.2‴, E.3‴).

A TRAIN IS DATA (D9). `TrainSpec` (models.py, mirrored in types.ts) is an id,
a name, a program, a product, an inlet, and units in order: each a catalogue
type (pureos/catalogue.py), the values a person typed for it (Override-shaped,
D3), record ids named for a parameter, where each outlet goes (`onward`,
`waste`, or `recycle:<an earlier unit>`; an outlet not named takes the
catalogue's default), and optionally a shelf flowsheet's own unit to read its
values from (`readFrom`). The browser keeps a train whole and sends it with a
run; the service keeps the runs.

    validate(spec)           every refusal at once, in words; runs nothing
    inlet_stream(spec, overrides=None, by=None, include_archived=True)
                             the inlet as data (D10): a kept simulation's broth
                             at harvest (cells, product and sugar in g L⁻¹ by
                             the simulation's own units, read as the program's
                             chemicals, the water the balance the worker reads
                             from the mixture's density), a kept run's stream
                             (its kg/hr, temperature, pressure and phase), or a
                             composition typed under a person's name; with its
                             values, their sources and its basis inputs
    run_train(spec, overrides=None, by=None, include_archived=False)
                             resolve every parameter of every unit with its
                             source, refuse what waits in words, and keep one
                             `pureos.train_run` artifact; the Proforma worker
                             builds and runs the train (op `train_run`,
                             flowsheets/train.py), and nothing here imports
                             BioSTEAM (E.3‴)
    train_runs(include_archived)  every kept train run, newest first
    program_of_run(art)      a train run's program: the train's, its inlet's
                             and what its records name, an archived one winning

THE INLET'S OWN PANEL is the pseudo-unit `inlet`, scope
`pureos:unit:<train id>:inlet`: `broth_flow` (m³ h⁻¹: a `fermos.vessel` design
of the simulation the train names gives it, its working volume times its
vessels over its cycle time, read from the design; else a person's; it waits
otherwise, and the run refuses naming it), `harvest_hour` (the simulation's
own harvest hour, else a person's, said so), `T` and `P` (a run's stream's
own; else a person's, else thermosteam's Stream default), and for a typed
inlet `conc.<chemical>` (g L⁻¹, each a person's assumption).

WHERE A UNIT'S VALUE COMES FROM, IN ORDER: a person's override (the train's
typed value, or the run request's override of the same key); a shelf
flowsheet's own unit the train reads (`readFrom`: the value the built unit
holds, a `model` source naming the package's version, first in the rule);
records of the parameter's ontology field (catalogue.py's source rules) on the
train's program's papers through the aggregate gate (binding.py), each named,
the per-component key of the product's chemical alone, a step's recovery and
purity only where the record's words name the step, a percentage turned into
a share (a named step, `PER_CENT`), and a split to an outlet the product does
not go on by turned into one less the recovery (said so); the record ids
named for a key bind it and no other record does; then the class's own
default, read from its code in the worker. A per-component key nobody set is
left to the class, which reads a split that does not name a component as none
of it to outlet 0 (BioSTEAM's own reading, said in the run's notes).

THE RUN'S ARTIFACT (E.2‴). Its basis names the train as data, the program,
the product and the chemical traced, the chemical set, the BioSTEAM,
thermosteam and biorefineries versions, the utility prices and cost index,
whether the diagram is drawn, the inlet with every source, and for every unit
its type, its BioSTEAM class and its unit id, where each outlet goes, the
flowsheet unit it reads, and every parameter with its source (an override an
`assumption` naming the person; a class default a `model` input naming
BioSTEAM's version; a record a `record` input; the inlet's simulation, run or
vessel an `artifact`). Its provenance is `basis_provenance`'s. Its output
holds the tables as `proforma.tables_of` reads them (so `pureos.train_of`
reads a train run as it reads a Proforma run), the product and its stream, the
purity of every stream, each unit's costs or *no cost model*, the inlet as
built, every parameter as the basis holds it, notes and flags. A train runs
each value as given: an interval stays in the basis and is not sampled.

Rule 1: no process number here. The constants below are a structural word
list, a unit's definition (`PER_CENT`) and a reading convention
(`IMPURITIES`), each with its reason.
"""
from __future__ import annotations

import json
import re
import threading
from typing import Any, Iterable, NamedTuple

from .. import params
from ..models import (
    Artifact,
    BasisInput,
    BasisSource,
    Override,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    StreamImpurity,
    StreamPurity,
    TrainInletRead,
    TrainParam,
    TrainPurity,
    TrainRun,
    TrainSpec,
    TrainSummary,
    TrainUnitCost,
    TrainUnitParameters,
    TrainUnitSpec,
    TrainValidation,
)
from . import catalogue

TRAIN_RUN = "pureos.train_run"
VERSION_WORDS = "train run 1"
# The pseudo-unit whose scope holds the inlet's own parameters.
INLET = "inlet"
ONWARD, WASTE, RECYCLE = "onward", "waste", "recycle:"
# A unit's id is its BioSTEAM unit id: a letter, then letters, digits and
# underscores (BioSTEAM's ids take no dash or dot).
UNIT_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
SIMULATION = "fermos.simulation"
VESSEL = "fermos.vessel"
# The artifacts whose stream table a run-stream inlet reads.
STREAM_TOOLS = ("proforma.run", "proforma.reference", TRAIN_RUN)
# The chemical set a program's trains build on, in words: the worker builds
# every train on it (flowsheets/ethanol_glucose_v0.create_chemicals), and a
# program with none here has no train yet.
PROGRAM_CHEMICALS = {"yeast": "the yeast program's chemicals, as the ethanol flowsheet builds on them "
                              "(biorefineries.corn.create_chemicals)"}
# What a simulation's cells and sugar are read as in that set: names.
CELLS = {"yeast": "Yeast"}
SUGAR_CHEMICALS = {"glucose": "Glucose"}
# A percent is a share times a hundred: the unit's own definition, the one
# step a percentage record takes to a share spec (no unit of units.py holds
# a bare share).
PER_CENT = 100.0
PERCENT_UNITS = ("%", "% of total protein")
PERCENT_FIELDS = ("step_recovery", "product_purity", "cake_moisture", "disruption_protein_yield")
# Fields that say nothing of which step they were measured on: a record binds
# a unit only where its words name the unit's step.
STEP_FIELDS = ("step_recovery", "product_purity")
# A per-component key bound by a record of these fields is the product's.
PRODUCT_KEYED = ("split", "partition_coefficient", "sieving_coefficient")
# How many of a stream's largest other components a purity row names: a
# reading convention, not a process number.
IMPURITIES = 3
# A class's own default is left to the class: the sources catalogue.py names
# it by.
CLASS_DEFAULT_IDS = ("biosteam@", "openferment.pureos.inhouse")
INLET_GROUP = "Inlet"
SIDE_GROUP = "Side stream"

_ABS_T = "a physical limit: a temperature in kelvin is above none"
_ABS_P = "a physical limit: an absolute pressure is above none"


class TrainRefused(ValueError):
    """A train that cannot run, in words (a 422)."""


class TrainNotOnFile(LookupError):
    """An artifact a train names that is not kept here (a 422 in words)."""


def scope_of(train_id: str, unit_id: str) -> str:
    return params.scope_name("pureos-unit", train_id, unit_id)


# ── what the worker reads, once a process ──────────────────────────────

_SPECS: dict[str, Any] = {}
_UNITS: dict[tuple[str, str, str], dict[str, Any]] = {}
_LOCK = threading.Lock()


def train_specs() -> dict[str, Any]:
    """The worker's `train_specs`: the yeast program's chemical IDs, the
    Stream defaults, the library versions; kept for the process's life."""
    from .. import proforma

    with _LOCK:
        if "specs" not in _SPECS:
            _SPECS["specs"] = proforma.call("train_specs", {})
        return _SPECS["specs"]


def flowsheet_unit(flowsheet: str, unit: str, type_id: str) -> dict[str, Any]:
    """What a shelf flowsheet's own unit holds, by catalogue key (the worker's
    `flowsheet_unit_values`), kept for the process's life: a unit's design
    values are the package's and do not move under it."""
    from .. import proforma
    from ..workers import WorkerError

    key = (flowsheet, unit, type_id)
    with _LOCK:
        if key not in _UNITS:
            try:
                said = proforma.call("flowsheet_unit_values", {"flowsheet": flowsheet,
                                                               "units": [{"unit": unit, "type": type_id}]})
            except WorkerError as e:
                text = str(e)
                if text.startswith("Refused: "):
                    raise TrainRefused(text.removeprefix("Refused: ")) from None
                raise
            _UNITS[key] = {**said["units"][unit], "versions": said["versions"]}
        return _UNITS[key]


# ── a train as data: validate ──────────────────────────────────────────


def _out_ports(e: catalogue.Entry) -> list[catalogue.Port]:
    return [p for p in e.ports if p.side == "out"]


def _side_ports(e: catalogue.Entry) -> list[catalogue.Port]:
    return [p for p in e.ports if p.side == "in" and p.source == "side"]


def _upstream(e: catalogue.Entry) -> catalogue.Port | None:
    return next((p for p in e.ports if p.side == "in" and p.source == "upstream"), None)


def routes(unit: TrainUnitSpec, e: catalogue.Entry | None = None) -> dict[str, str]:
    """Where each outlet of a unit goes: as the train routes it, else the
    catalogue's default (its onward port on, every other to waste)."""
    e = e or catalogue.entry(unit.type)
    return {p.name: unit.outlets.get(p.name) or (ONWARD if p.onward else WASTE) for p in _out_ports(e)}


def _key_words(e: catalogue.Entry, key: str) -> str | None:
    """None when a parameter key is one of a unit's; else why not, in words
    (empty when the list of its parameters says it all)."""
    per = catalogue.template_keys(e)
    plain = {p.key for p in e.params if not p.per}
    if key in plain:
        return None
    base, sep, item = key.partition(catalogue.SEP)
    if sep and item:
        if per.get(base) == "component":
            return None
        if per.get(base) == "effect":
            return None if item.isdigit() and int(item) >= 1 else f"{key}: an effect is numbered from one"
        if base in {p.name for p in _side_ports(e)}:
            return None
    if base in per:
        return (f"{key} is set per {per[base]}, as {base}{catalogue.SEP}<{per[base]}>: the template itself takes no "
                "value")
    return ""


def validate(spec: TrainSpec) -> list[str]:
    """Every reason the train cannot be built, at once, in words; empty when
    it can (its values still resolve at the run). Runs nothing."""
    from ..flowsheets import shelf

    said: list[str] = []
    for word, value in (("train", spec.id), ("program", spec.program), ("product", spec.product)):
        if not re.fullmatch(params._ID, value or ""):
            said.append(f"a {word} is named by its id (letters, digits, dots, dashes, underscores); {value!r} is not one")
    if not (spec.name or "").strip():
        said.append("a train has a name")
    inlet = spec.inlet
    if inlet.kind in ("simulation", "run-stream") and not inlet.ref:
        said.append(f"a {inlet.kind} inlet names its artifact (ref)")
    if inlet.kind == "typed" and inlet.ref:
        said.append("a typed inlet names no artifact: its composition is typed")
    if inlet.kind == "run-stream" and not inlet.streamId:
        said.append("a run's stream as the inlet names the stream (streamId)")
    if inlet.kind != "run-stream" and inlet.streamId:
        said.append("a stream id belongs to a run-stream inlet")
    if inlet.vessel and inlet.kind != "simulation":
        said.append("a vessel gives the broth flow of a simulation's harvest alone")
    for ref, what in ((inlet.ref, "ref"), (inlet.vessel, "vessel")):
        if ref and not re.fullmatch(r"[0-9a-f]{16}", ref):
            said.append(f"the inlet's {what} is an artifact id (16 hex); {ref!r} is not one")
    allowed = {"simulation": ("broth_flow", "harvest_hour", "T", "P"), "run-stream": (), "typed": ("broth_flow", "T", "P")}
    for key in inlet.params:
        if key in allowed[inlet.kind] or (inlet.kind == "typed" and key.startswith(f"conc{catalogue.SEP}")
                                          and len(key) > len("conc.")):
            continue
        said.append(f"the inlet ({inlet.kind}) has no parameter {key!r}; its parameters are "
                    + (", ".join(allowed[inlet.kind]) + (", conc.<chemical>" if inlet.kind == "typed" else "")
                       if allowed[inlet.kind] else "none a person sets: a run's stream carries its own"))
    if not spec.units:
        said.append("a train holds at least one unit")
    order = [u.id for u in spec.units]
    seen: set[str] = set()
    for n, u in enumerate(spec.units):
        if u.id in seen:
            said.append(f"two units are named {u.id}: a unit's id is its own")
        seen.add(u.id)
        if not UNIT_ID.fullmatch(u.id or ""):
            said.append(f"unit id {u.id!r} is not one BioSTEAM takes: a letter, then letters, digits or underscores")
        if u.id == INLET:
            said.append(f"{INLET} names the train's inlet, not a unit")
        try:
            e = catalogue.entry(u.type)
        except catalogue.CatalogueUnknown as ex:
            said.append(f"unit {u.id}: {ex}")
            continue
        outs = {p.name for p in _out_ports(e)}
        for name, route in u.outlets.items():
            if name not in outs:
                said.append(f"unit {u.id} ({e.id}) has no outlet {name!r}; its outlets are {', '.join(sorted(outs))}")
                continue
            if route in (ONWARD, WASTE):
                continue
            if not route.startswith(RECYCLE):
                said.append(f"unit {u.id}'s outlet {name} goes onward, to waste or to recycle:<an earlier unit>; "
                            f"{route!r} is none of them")
                continue
            target = route[len(RECYCLE):]
            if target not in order[:n]:
                where = ("itself" if target == u.id else "a unit after it" if target in order
                         else "no unit of this train")
                said.append(f"unit {u.id}'s outlet {name} recycles to {target}, {where}: a recycle goes back to an "
                            "earlier unit (D9), and a forward one is refused")
                continue
            te = _entry_of(spec, target)
            if te is not None:
                up = _upstream(te)
                if up is None or not up.many:
                    said.append(f"unit {u.id}'s outlet {name} recycles to {target} ({te.id}), whose inlet takes one "
                                "stream: route it to a unit whose inlet takes several (a mixer, a column, a "
                                "centrifuge, a filter)")
        onward = [name for name, route in routes(u, e).items() if route == ONWARD]
        if len(onward) > 1:
            said.append(f"unit {u.id} ({e.id}) sends {len(onward)} outlets on ({', '.join(onward)}): a unit of a train "
                        "sends one on")
        elif not onward:
            said.append(f"unit {u.id} ({e.id}) sends no outlet on: each unit of a train sends one on, and the last "
                        "one's is the product stream")
        rules = {p.key: p.rule for p in e.params}
        for key in [*u.params, *u.records]:
            why = _key_words(e, key)
            if why is None:
                continue
            said.append(f"unit {u.id} ({e.id}) has no parameter {key!r}; its parameters are "
                        f"{', '.join(p.key + (catalogue.SEP + '<' + p.per + '>' if p.per else '') for p in e.params)}"
                        + (f" and the side inlets' {', '.join(p.name + '.<chemical>' for p in _side_ports(e))}"
                           if _side_ports(e) else "") + (f" ({why})" if why else ""))
        for key, ids in u.records.items():
            base = key.partition(catalogue.SEP)[0]
            if not any(r.startswith("record:") for r in rules.get(base, ())):
                said.append(f"unit {u.id}: {key} binds from no record field, so no record can be named for it")
            if not ids or any(not isinstance(i, str) or not i.strip() for i in ids):
                said.append(f"unit {u.id}: the records named for {key} are record ids")
        if u.readFrom is not None:
            try:
                info = shelf.info(u.readFrom.flowsheet)
            except shelf.NotOnShelf as ex:
                said.append(f"unit {u.id} reads from {u.readFrom.flowsheet!r}: {ex}")
            else:
                if info.reference:
                    said.append(f"unit {u.id} reads from {info.id}, a reference biorefinery: it runs whole, and a "
                                "train reads the units of a flowsheet the worker builds case by case")
            if not UNIT_ID.fullmatch(u.readFrom.unit or ""):
                said.append(f"unit {u.id} reads from unit {u.readFrom.unit!r}, which is no BioSTEAM unit id")
    return said


def _entry_of(spec: TrainSpec, unit_id: str) -> catalogue.Entry | None:
    """The catalogue entry of a unit of the train, or None."""
    u = next((x for x in spec.units if x.id == unit_id), None)
    try:
        return catalogue.entry(u.type) if u is not None else None
    except catalogue.CatalogueUnknown:
        return None


def validation(spec: TrainSpec) -> TrainValidation:
    said = validate(spec)
    return TrainValidation(ok=not said, refusals=said)


# ── the inlet (D10) ────────────────────────────────────────────────────


def _artifact(aid: str, what: str) -> Artifact:
    from .. import artifacts

    try:
        return artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise TrainRefused(f"there is no kept artifact {aid} here, which the train names as its {what}") from None


def _shown(art: Artifact, what: str, include_archived: bool) -> None:
    """An archived program's artifact as an inlet, refused with the switch
    off, as fermOS refuses an archived kept simulation as a start."""
    from .. import module_stores, programs

    try:
        program = module_stores.artifact_program(art)
        if not programs.hides(program, include_archived):
            return
        p = programs.program_by_id(program)
    except FileNotFoundError:
        return
    raise TrainRefused(f"{what} {art.id} belongs to {p.name if p else program}, archived (hidden). {programs.SWITCH}")


def _spec(key: str, label: str, gloss: str, dimension: str, unit: str, rule: list[str],
          bounds: tuple[float | None, float | None, str], group: str = INLET_GROUP, symbol: str = "",
          note: str | None = None) -> ParameterSpec:
    low, high, reason = bounds
    return ParameterSpec(key=key, label=label, symbol=symbol, gloss=gloss, dimension=dimension, unit=unit, min=low,
                         max=high, group=group, sourceRule=rule, note=note, boundsReason=reason)


def _flow_spec(rule: list[str], note: str) -> ParameterSpec:
    return _spec("broth_flow", "Broth flow", "the volume of broth the train takes an hour", "flow", "m³ h⁻¹", rule,
                 (0, None, "a physical limit: a flow is above none"), symbol="Q", note=note)


def _tp_specs(rule: list[str]) -> list[ParameterSpec]:
    return [_spec("T", "Temperature", "the inlet's temperature", "temperature", "K", rule, (0, None, _ABS_T), symbol="T"),
            _spec("P", "Pressure", "the inlet's pressure", "pressure", "Pa", rule, (0, None, _ABS_P), symbol="P")]


def _stream_default(key: str) -> ParameterValue:
    ws = train_specs()
    v = ws[key]
    return ParameterValue(key=key, value=v, origin="library-default", libraryDefault=v, source=BasisSource(
        kind="model", id=f"thermosteam@{ws['versions']['thermosteam']}",
        note=f"the {key} thermosteam gives a Stream nobody set it on, read from {ws['from']}"),
        detail=f"thermosteam's Stream default, read from its code ({ws['from']})")


class _InletRead(NamedTuple):
    """What the inlet's scope reads before any person's value: its specs and
    candidates, the artifact, and how its states map to chemicals."""

    provided: params.Provided
    art: Artifact | None
    chemical_of_state: dict[str, str]
    conventions: list[BasisInput]
    notes: list[str]


def _vessel_flow(spec: TrainSpec, sim: Artifact) -> ParameterValue:
    """The broth flow a vessel design of the simulation gives: its working
    volume times its vessels over its cycle time, read from the design."""
    v = _artifact(spec.inlet.vessel or "", "vessel")
    if v.tool != VESSEL:
        raise TrainRefused(f"artifact {v.id} is a {v.tool} artifact, not a vessel design ({VESSEL})")
    o = v.output or {}
    if str(o.get("source") or "") != sim.id:
        raise TrainRefused(f"vessel {v.id} was designed for {o.get('sourceTool') or 'an artifact'} {o.get('source')}, "
                           f"not for simulation {sim.id}, the train's inlet")
    rows = {r.get("label"): r for r in o.get("design") or []}
    want = {"Working volume of each vessel": ("m3", "m³"), "Vessels": ("",), "Cycle time": ("hr", "h")}
    got = {}
    for label, units_ok in want.items():
        r = rows.get(label)
        if r is None or not isinstance(r.get("value"), (int, float)) or isinstance(r.get("value"), bool):
            raise TrainRefused(f"vessel {v.id} holds no {label.lower()}, which the broth flow is read from")
        if (r.get("unit") or "") not in units_ok:
            raise TrainRefused(f"vessel {v.id} keeps its {label.lower()} in {r.get('unit')}, which the broth flow does "
                               f"not read ({' or '.join(u or 'no unit' for u in units_ok)})")
        got[label] = float(r["value"])
    if not got["Cycle time"] > 0:
        raise TrainRefused(f"vessel {v.id}'s cycle time is not above none: no broth flow is read from it")
    q = got["Working volume of each vessel"] * got["Vessels"] / got["Cycle time"]
    return ParameterValue(key="broth_flow", value=q, origin="artifact", source=BasisSource(
        kind="artifact", id=v.id, note=(f"vessel design {v.id}: the working volume of each of its {got['Vessels']:g} "
                                        f"vessels, {got['Working volume of each vessel']:.6g} m³, times the vessels, over "
                                        f"its cycle time, {got['Cycle time']:.6g} h, as the design reads them")),
        detail=f"read from vessel design {v.id}: working volume × vessels ÷ cycle time")


def _inlet_read(spec: TrainSpec, include_archived: bool = True) -> _InletRead:
    from .. import thermo

    inlet = spec.inlet
    conventions: list[BasisInput] = []
    notes: list[str] = []
    if inlet.kind == "simulation":
        from .. import kinetics, vessel

        art = _artifact(inlet.ref or "", "inlet")
        if art.tool != SIMULATION:
            raise TrainRefused(f"artifact {art.id} is a {art.tool} artifact, not a fermOS simulation ({SIMULATION}): a "
                               "simulation inlet is a kept simulation's harvest")
        _shown(art, "simulation", include_archived)
        o = art.output or {}
        family = kinetics.FAMILIES.get(str(o.get("family") or ""))
        if family is None or family.product_state() != "P":
            raise TrainRefused(f"simulation {art.id} is of family {o.get('family')}, whose product is no "
                               "concentration P in the broth: its harvest is not a train's inlet here")
        state_units = o.get("units") or {}
        for state in ("X", "S", "P"):
            u = state_units.get(state)
            if u is not None and u not in vessel.CONC_UNITS:
                raise TrainRefused(f"simulation {art.id} keeps {state} in {u}; the inlet reads g L⁻¹")
        cells = CELLS.get(spec.program)
        try:
            organism = vessel._organism_read(art.id, str(o["strain"]) if o.get("strain") else None)
        except vessel.VesselRefused as e:
            raise TrainRefused(str(e).replace("the vessel is built", "the train is built").replace(
                "designs no vessel", "takes no inlet")) from None
        if organism is not None:
            conventions.append(BasisInput(name="cells read as", value=cells or "", unit="", source=BasisSource(
                kind="convention", note=organism.replace("the vessel is built on", "the train is built on"))))
        product = o.get("product")
        if product and product != spec.product:
            raise TrainRefused(f"simulation {art.id} makes {product}; the train's product is {spec.product}")
        chem = thermo.CHEMICALS.get(spec.product, "")
        if not product:
            conventions.append(BasisInput(name="product read as", value=spec.product, unit="", source=BasisSource(
                kind="convention", note=(f"simulation {art.id} names no product: its product state P is read as the "
                                         f"train's product, {spec.product}"))))
        sugar = str(o.get("sugar") or "")
        sugar_chem = SUGAR_CHEMICALS.get(sugar)
        if sugar_chem is None:
            raise TrainRefused(f"simulation {art.id} runs on {sugar or 'no sugar it names'}; the inlet reads "
                               f"{', '.join(SUGAR_CHEMICALS)} as the program's chemicals name them")
        mapping = {"X": cells or "", "P": chem, "S": sugar_chem}
        harvest = o.get("harvestH")
        sources: dict[str, dict[str, ParameterValue | None]] = {"harvest_hour": {}, "broth_flow": {},
                                                                "T": {"library-default": _stream_default("T")},
                                                                "P": {"library-default": _stream_default("P")}}
        if isinstance(harvest, (int, float)) and not isinstance(harvest, bool):
            sources["harvest_hour"]["simulation"] = ParameterValue(
                key="harvest_hour", value=float(harvest), origin="simulation", source=BasisSource(
                    kind="artifact", id=art.id, note=f"the hour simulation {art.id} is harvested, as it keeps it"),
                detail=f"simulation {art.id}'s own harvest hour")
        if inlet.vessel:
            sources["broth_flow"]["artifact"] = _vessel_flow(spec, art)
        else:
            sources["broth_flow"]["waiting"] = ParameterValue(key="broth_flow", value=None, origin="waiting", source=None,
                                                              detail=(f"name a vessel design of simulation {art.id} "
                                                                      "(its working volume × vessels ÷ cycle time), or "
                                                                      "type the broth flow under your name"))
        specs = [_flow_spec(["artifact", "assumption"], "From a vessel design of the simulation the train names, "
                            "read from the design, never typed; else a person's."),
                 _spec("harvest_hour", "Harvest hour", "the hour of the simulation the broth is taken at", "time", "h",
                       ["simulation", "assumption"], (0, None, "a physical limit: an hour of the run is not negative"),
                       note="The simulation's own harvest hour; a person may name another hour of the run, said so."),
                 *_tp_specs(["assumption", "library-default"])]
        notes.append(f"The broth at harvest of simulation {art.id}: X as {mapping['X']}, P as {mapping['P']}, S as "
                     f"{mapping['S']}, in g L⁻¹ over the broth flow; {catalogue.SOLVENT} is the balance, read from the "
                     "mixture's density in the worker.")
        return _InletRead(params.Provided(title=f"Inlet of train {spec.name}: the harvest of simulation {art.id}",
                                          specs=specs, sources=sources, notes=notes), art, mapping, conventions, notes)
    if inlet.kind == "run-stream":
        from .. import proforma

        art = _artifact(inlet.ref or "", "inlet")
        if art.tool not in STREAM_TOOLS:
            raise TrainRefused(f"artifact {art.id} is a {art.tool} artifact; a run's stream is read from a "
                               f"{', '.join(STREAM_TOOLS)} artifact")
        _shown(art, "run", include_archived)
        row = next((s for s in proforma.tables_of(art).streams if s.id == inlet.streamId), None)
        if row is None:
            raise TrainRefused(f"run {art.id}'s stream table holds no stream {inlet.streamId}")
        if len(row.phase) != 1:
            raise TrainRefused(f"stream {row.id} of run {art.id} is in phases {row.phase!r}; its table keeps no split "
                               "by phase, so it is not an inlet here")
        src = BasisSource(kind="artifact", id=art.id, note=f"stream {row.id} of run {art.id}, as its stream table holds it")
        sources = {k: {"artifact": ParameterValue(key=k, value=float(getattr(row, k)), origin="artifact", source=src,
                                                  detail=f"stream {row.id} of run {art.id}")} for k in ("T", "P")}
        specs = _tp_specs(["artifact"])
        notes.append(f"Stream {row.id} of run {art.id}: its kg/hr by chemical, temperature, pressure and phase, as its "
                     "stream table holds them.")
        return _InletRead(params.Provided(title=f"Inlet of train {spec.name}: stream {row.id} of run {art.id}",
                                          specs=specs, sources=sources, notes=notes), art, {}, conventions, notes)
    ws = train_specs()
    chems = [c for c in ws["chemicals"] if c != catalogue.SOLVENT]
    specs = [_flow_spec(["assumption"], "A person's."), *(
        _spec(f"conc{catalogue.SEP}{c}", f"{c} concentration", f"the {c} in each litre of the inlet", "massConc",
              "g L⁻¹", ["assumption"], (0, None, "a physical limit: no negative concentration")) for c in chems),
        *_tp_specs(["assumption", "library-default"])]
    sources = {"T": {"library-default": _stream_default("T")}, "P": {"library-default": _stream_default("P")}}
    notes.append(f"A composition typed under a person's name: each concentration in g L⁻¹ over the broth flow; "
                 f"{catalogue.SOLVENT} is the balance, read from the mixture's density in the worker. A component left "
                 "untyped is absent.")
    def absent(values: list[ParameterValue]) -> dict[str, str]:
        return {v.key: "absent from the inlet: a component nobody typed is not in it" for v in values
                if v.key.startswith(f"conc{catalogue.SEP}")}

    return _InletRead(params.Provided(title=f"Inlet of train {spec.name}: typed", specs=specs, sources=sources,
                                      notes=notes, unread=absent), None, {}, conventions, notes)


def _as_overrides(scope: str, typed: dict[str, TrainParam], extra: Iterable[Override] = ()) -> list[Override]:
    """A place's typed values as Overrides of its scope, with the request's
    overrides of the same scope laid over them key by key."""
    out = {k: Override(scope=scope, key=k, **v.model_dump()) for k, v in typed.items()}
    for o in extra:
        if o.scope == scope:
            out[o.key] = o
    return list(out.values())


class Inlet(NamedTuple):
    """The inlet as data: what it was (`read`), the request the worker builds
    the stream from (`worker`), its basis inputs, its specs and values, and
    the chemicals the train carries from it."""

    read: TrainInletRead
    worker: dict[str, Any]
    basis: list[BasisInput]
    specs: list[ParameterSpec]
    values: list[ParameterValue]
    chemicals: list[str]


def _waiting_words(where: str, values: list[ParameterValue]) -> list[str]:
    return [f"{where}: {v.key} waits ({v.detail})" for v in values if v.origin == "waiting"]


def inlet_stream(spec: TrainSpec, overrides: Iterable[Override] | None = None, by: str | None = None,
                 include_archived: bool = True) -> Inlet:
    """The inlet as data (D10), its values resolved with the train's typed
    ones and the request's overrides of `pureos:unit:<train>:inlet`, every
    source named; refused in words while a value waits."""
    from .. import fermos, kinetics

    scope = scope_of(spec.id, INLET)
    got = _inlet_read(spec, include_archived)
    try:
        values = params.resolve(got.provided.specs, got.provided.sources,
                                _as_overrides(scope, spec.inlet.params, overrides or ()), by)
    except params.ParamRefused as e:
        raise TrainRefused(f"the inlet: {e}") from None
    waiting = _waiting_words("the inlet", [v for v in values if not v.key.startswith(f"conc{catalogue.SEP}")])
    if waiting:
        raise TrainRefused("; ".join(waiting))
    v = {x.key: x for x in values}
    basis = [BasisInput(name="inlet kind", value=spec.inlet.kind, unit="", source=BasisSource(kind="convention", note={
        "simulation": "the inlet is a kept fermOS simulation's broth at harvest (D10)",
        "run-stream": "the inlet is a stream of a kept run, as its stream table holds it",
        "typed": "the inlet is a composition typed under a person's name"}[spec.inlet.kind]))]
    art = got.art
    if art is not None:
        basis.append(BasisInput(name="inlet", value=art.id, unit="", source=BasisSource(
            kind="artifact", id=art.id, note=f"the {art.tool} the inlet is read from")))
    if spec.inlet.streamId:
        basis.append(BasisInput(name="inlet stream", value=spec.inlet.streamId, unit="", source=BasisSource(
            kind="convention", note="the stream of that run the train takes")))
    if spec.inlet.vessel:
        basis.append(BasisInput(name="vessel", value=spec.inlet.vessel, unit="", source=BasisSource(
            kind="artifact", id=spec.inlet.vessel, note="the vessel design whose working volume, vessels and cycle time "
                                                         "give the broth flow")))
    basis += [b.model_copy(update={"name": f"{INLET}{catalogue.SEP}{b.name}"})
              for b in params.basis_inputs(got.provided.specs, values)]
    basis += got.conventions
    notes = list(got.notes)
    concentrations: dict[str, float] | None = None
    flows: dict[str, float] = {}
    phase = "l"
    absent = None
    harvest_hour = None
    if spec.inlet.kind == "simulation":
        harvest_hour = float(v["harvest_hour"].value)  # type: ignore[arg-type]
        try:
            h = fermos.harvest(art, harvest_hour)
        except (kinetics.FamilyRefused, ValueError) as e:
            raise TrainRefused(f"the inlet: {e}") from None
        absent = h.get("absent")
        concentrations = {}
        for state, chem in got.chemical_of_state.items():
            c = float(h["state"][state])
            concentrations[chem] = concentrations.get(chem, 0.0) + c
            basis.append(BasisInput(name=f"{INLET}{catalogue.SEP}conc{catalogue.SEP}{chem}", value=c, unit="g L⁻¹",
                                    source=BasisSource(kind="artifact", id=art.id, note=(
                                        f"{state} of simulation {art.id} at {harvest_hour:.6g} h, in g L⁻¹ as the "
                                        f"simulation keeps it, read as {chem}"))))
        if v["harvest_hour"].origin == "assumption":
            notes.append(f"The broth is taken at {harvest_hour:.6g} h, an hour {v['harvest_hour'].overriddenBy} named, "
                         f"not the simulation's own harvest hour.")
        basis.append(BasisInput(name="inlet absent", value=str(absent or ""), unit="", source=BasisSource(
            kind="convention", note="what the simulation's family does not model is absent from the inlet (D10)")))
    elif spec.inlet.kind == "typed":
        concentrations = {k.split(catalogue.SEP, 1)[-1]: float(x.value) for k, x in v.items()  # type: ignore[arg-type]
                          if k.startswith(f"conc{catalogue.SEP}") and x.value is not None and float(x.value) > 0}
        if not concentrations:
            raise TrainRefused("the inlet: a typed inlet names at least one component's concentration above none, under "
                               "a person's name (conc.<chemical>)")
    else:
        from .. import proforma

        row = next(s for s in proforma.tables_of(art).streams if s.id == spec.inlet.streamId)
        flows = {c: float(m) for c, m in row.massFlows.items() if m > 0}
        phase = row.phase
        for c, m in flows.items():
            basis.append(BasisInput(name=f"{INLET}{catalogue.SEP}flow{catalogue.SEP}{c}", value=m, unit="kg/hr",
                                    source=BasisSource(kind="artifact", id=art.id, note=(
                                        f"{c} in stream {row.id} of run {art.id}, as its stream table holds it"))))
    basis.append(BasisInput(name="inlet phase", value=phase, unit="", source=BasisSource(
        kind="convention", note="the inlet's phase: a broth is a liquid" if spec.inlet.kind != "run-stream"
        else f"the phase stream {spec.inlet.streamId} of run {art.id} is in")))
    if concentrations is not None:
        basis.append(BasisInput(name="inlet balance", value=catalogue.SOLVENT, unit="", source=BasisSource(
            kind="convention", note=(f"{catalogue.SOLVENT} is the balance: the {catalogue.SOLVENT} that brings the "
                                     "mixture's volume, as thermosteam computes it at the inlet's temperature and "
                                     "pressure, to the broth flow"))))
    chemicals = sorted({*(concentrations or {}), *flows, *((catalogue.SOLVENT,) if concentrations is not None else ())})
    worker = {"flows": flows or None, "concentrations": concentrations,
              "brothFlow": float(v["broth_flow"].value) if "broth_flow" in v else None,  # type: ignore[arg-type]
              "balance": catalogue.SOLVENT if concentrations is not None else None,
              "T": float(v["T"].value), "P": float(v["P"].value), "phase": phase}  # type: ignore[arg-type]
    read = TrainInletRead(kind=spec.inlet.kind, ref=art.id if art else None, refTool=art.tool if art else None,
                          streamId=spec.inlet.streamId, vessel=spec.inlet.vessel, chemicals=chemicals,
                          concentrations=concentrations, flows=flows, brothFlow=worker["brothFlow"],
                          harvestHour=harvest_hour, T=worker["T"], P=worker["P"], phase=phase, absent=absent,
                          notes=notes)
    return Inlet(read, worker, basis, got.provided.specs, values, chemicals)


def chemicals_of(spec: TrainSpec, overrides: Iterable[Override] = (), include_archived: bool = True) -> list[str]:
    """The chemicals a train carries from its inlet, which its units'
    per-component keys expand over; read without resolving the inlet's
    values (a typed inlet's are the components its values name)."""
    inlet = spec.inlet
    if inlet.kind == "typed":
        named = {o.key: o.value for o in _as_overrides(scope_of(spec.id, INLET), inlet.params, overrides)}
        typed = {k.split(catalogue.SEP, 1)[-1] for k, x in named.items()
                 if k.startswith(f"conc{catalogue.SEP}") and isinstance(x, (int, float)) and x > 0}
        return sorted({*typed, catalogue.SOLVENT})
    got = _inlet_read(spec, include_archived)
    if inlet.kind == "simulation":
        return sorted({*got.chemical_of_state.values(), catalogue.SOLVENT} - {""})
    from .. import proforma

    row = next(s for s in proforma.tables_of(got.art).streams if s.id == inlet.streamId)
    return sorted(c for c, m in row.massFlows.items() if m > 0)


def static_specs() -> Iterable[tuple[str, list[ParameterSpec]]]:
    """Every spec a train adds to the catalogue's, read with no worker, for
    `params --check` (check:seed holds each to a written bounds reason, D4):
    the inlet's, by kind, a typed concentration and a side inlet's flow each
    one template (expanded per chemical when a train is resolved)."""
    conc = _spec("conc", "Concentration", "a component's mass in each litre of the inlet", "massConc", "g L⁻¹",
                 ["assumption"], (0, None, "a physical limit: no negative concentration"),
                 note="Per component: a key conc.<chemical> for each chemical of the program's set but water, the balance.")
    yield "pureos train inlet (simulation)", [
        _flow_spec(["artifact", "assumption"], "From a vessel design of the simulation the train names; else a person's."),
        _spec("harvest_hour", "Harvest hour", "the hour of the simulation the broth is taken at", "time", "h",
              ["simulation", "assumption"], (0, None, "a physical limit: an hour of the run is not negative")),
        *_tp_specs(["assumption", "library-default"])]
    yield "pureos train inlet (run-stream)", _tp_specs(["artifact"])
    yield "pureos train inlet (typed)", [_flow_spec(["assumption"], "A person's."), conc,
                                         *_tp_specs(["assumption", "library-default"])]
    for e in catalogue.UNIT_TYPES:
        for p in _side_ports(e):
            yield f"pureos unit {e.id} side inlet {p.name}", [
                _spec(p.name, f"{p.name.capitalize()} flow", f"a component's flow in the {p.name} inlet ({p.what})",
                      "massFlow", "kg h⁻¹", ["assumption"], (0, None, "a physical limit: no negative flow"),
                      group=SIDE_GROUP, note=f"Per component: a key {p.name}.<chemical> for each chemical of the "
                                             "program's set.")]


# ── a unit's parameters ────────────────────────────────────────────────


def _side_specs(e: catalogue.Entry, chemicals: Iterable[str]) -> list[ParameterSpec]:
    """A side inlet the train supplies (a solvent): its kg/hr per chemical of
    the program's set, each a person's."""
    out = []
    for p in _side_ports(e):
        for c in chemicals:
            out.append(_spec(f"{p.name}{catalogue.SEP}{c}", f"{p.name.capitalize()} {c}",
                             f"the {c} the {p.name} inlet carries an hour ({p.what})", "massFlow", "kg h⁻¹",
                             ["assumption"], (0, None, "a physical limit: no negative flow"), group=SIDE_GROUP))
    return out


def _number(o: Override | None) -> float | None:
    if o is None or isinstance(o.value, bool) or not isinstance(o.value, (int, float)):
        return None
    return float(o.value)


def _step_words(e: catalogue.Entry) -> list[str]:
    from .. import module_stores

    words = {e.id.replace("-", " "), e.name.lower(), e.cls.lower(), *(m.replace("-", " ") for m in e.maps)}
    try:
        for op in module_stores._projection()["pureos"]["unitOperations"]:
            if op.get("id") in (e.id, *e.maps) and op.get("label"):
                words.add(str(op["label"]).lower())
    except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
        pass
    return sorted(w for w in words if w)


def _names_step(r: dict[str, Any], words: list[str]) -> bool:
    text = " ".join(str(r.get(k) or "") for k in ("quote", "method", "conditions")).lower()
    return any(w in text for w in words)


class _Kept(NamedTuple):
    record: dict[str, Any]
    value: float


def _record_value(r: dict[str, Any], field: str) -> tuple[float | None, str | None]:
    """A record's value in the spec's terms: a percentage over `PER_CENT` (a
    share), a ratio as given; or why it is not read."""
    from .. import units

    try:
        x = float(r["value"])
    except (KeyError, TypeError, ValueError):
        return None, "a value that is not a number"
    unit = str(r.get("unit") or "").strip()
    if field in PERCENT_FIELDS:
        if unit not in PERCENT_UNITS and units.normalize(unit) != "%":
            return None, f"in {unit or 'no unit'}, not a percentage"
        return x / PER_CENT, None
    if unit and units.normalize(unit) not in (None, ""):
        return None, f"in {unit}, where a ratio has no unit"
    return x, None


def _records_for(field: str, e: catalogue.Entry, spec: TrainSpec, pool: Any, named: list[str] | None
                 ) -> tuple[list[_Kept], dict[str, int], list[str]]:
    """The records of one field that bind a unit of the train, each in the
    spec's terms; those left out, counted by why; and the refusals of named
    records that cannot bind."""
    from .. import binding

    kept: list[_Kept] = []
    out: dict[str, int] = {}
    refused: list[str] = []
    words = _step_words(e) if field in STEP_FIELDS else []
    pool_records = pool.records if pool is not None else []
    if named is not None:
        by_id = {r["id"]: r for r in pool_records}
        candidates = []
        for rid in named:
            r = by_id.get(rid)
            if r is None:
                refused.append(f"record {rid} is not in the evidence pool here")
            elif r.get("field") != field:
                refused.append(f"record {rid} is of {r.get('field')}, not {field}")
            else:
                candidates.append(r)
    else:
        candidates = [r for r in pool_records if r.get("field") == field]

    def leave(why: str, r: dict[str, Any]) -> None:
        if named is not None:
            refused.append(f"record {r['id']}: {why}")
        out[why] = out.get(why, 0) + 1

    for r in candidates:
        if not binding.in_program(str(r.get("paperId") or ""), spec.program):
            leave(f"not on the {spec.program} program's papers", r)
            continue
        gate = binding.exclusion(r)
        if gate:
            leave(f"kept out by the aggregate gate ({gate})", r)
            continue
        if words and not _names_step(r, words):
            leave(f"naming another step or none (its words name none of: {', '.join(words)})", r)
            continue
        x, why = _record_value(r, field)
        if x is None:
            leave(str(why), r)
            continue
        kept.append(_Kept(r, x))
    return kept, out, refused


class UnitScope(NamedTuple):
    """One unit of a train, resolved: its catalogue entry, the scope's specs
    and candidates, its overrides, and the refusals of records named for it."""

    unit: TrainUnitSpec
    entry: catalogue.Entry
    provided: params.Provided
    overrides: list[Override]
    refused: list[str]
    read_from: dict[str, Any] | None


def unit_scope(spec: TrainSpec, unit: TrainUnitSpec, chemicals: list[str], pool: Any,
               overrides: Iterable[Override] = (), product_chemical: str | None = None) -> UnitScope:
    """A train's unit as its panel and its run see it: the catalogue's
    specs, expanded over the train's chemicals (and per effect), with the
    side inlets' flows; each value's candidates (the class's default, a
    flowsheet unit's value the train reads, the records that bind, named or
    found); and the overrides (the train's typed values with the request's
    over them)."""
    from .. import binding

    e = catalogue.entry(unit.type)
    scope = scope_of(spec.id, unit.id)
    given = _as_overrides(scope, unit.params, overrides)
    by_key = {o.key: o for o in given}
    effects = _number(by_key.get("effects"))
    got = catalogue.provided(e.id)
    expanded = catalogue.expand(e.id, got.specs, chemicals,
                                effects=int(effects) if effects is not None and effects >= 1 and effects.is_integer()
                                else None)
    ws = train_specs()
    specs = expanded + _side_specs(e, ws["chemicals"])
    per = catalogue.template_keys(e)
    sources: dict[str, dict[str, ParameterValue | None]] = {}
    for s in specs:
        base = s.key.partition(catalogue.SEP)[0] if s.key not in got.sources else s.key
        cands = dict(got.sources.get(base) or {})
        sources[s.key] = {k: (c.model_copy(update={"key": s.key}) if c is not None else None) for k, c in cands.items()}
    read_from = None
    notes = list(got.notes)
    if unit.readFrom is not None:
        rf = unit.readFrom
        read_from = flowsheet_unit(rf.flowsheet, rf.unit, e.id)
        ver = read_from["versions"]
        src = BasisSource(kind="model", id=f"biorefineries@{ver['biorefineries']}", note=(
            f"unit {rf.unit} of {rf.flowsheet} as the worker builds it (its package biorefineries {ver['biorefineries']}"
            f", BioSTEAM {ver['biosteam']}): {read_from['unitClass']}'s own value, read from the built unit"))
        keyed = {s.key: i for i, s in enumerate(specs)}
        for k, x in read_from["values"].items():
            if k not in keyed:
                continue
            i = keyed[k]
            s = specs[i]
            specs[i] = s.model_copy(update={"sourceRule": ["library-default", *[r for r in s.sourceRule
                                                                                  if r != "library-default"]]})
            sources[k]["library-default"] = ParameterValue(key=k, value=x, origin="library-default", libraryDefault=x,
                                                           source=src, detail=f"read from unit {rf.unit} of {rf.flowsheet}")
        notes.append(f"Reads unit {rf.unit} of {rf.flowsheet}: each value its built unit holds comes first, as the "
                     "package's own; " + ("; ".join(f"{k}: {w}" for k, w in sorted(read_from["unread"].items()))
                                          or "every parameter was read") + ".")
    refused: list[str] = []
    pool_note = None
    outlet0 = _out_ports(e)[0].name
    onward = next((n for n, r in routes(unit, e).items() if r == ONWARD), None)
    passes = _number(by_key.get("passes"))
    for s in specs:
        base, _, item = s.key.partition(catalogue.SEP)
        fields = [r.split(":", 1)[1] for r in s.sourceRule if r.startswith("record:")]
        if not fields:
            continue
        field = fields[0]
        if base in per and per[base] == "component" and base in PRODUCT_KEYED and item != product_chemical:
            sources[s.key]["waiting"] = ParameterValue(key=s.key, value=None, origin="waiting", source=None, detail=(
                f"a record of {field} binds the product's {base} alone ({product_chemical or 'no chemical is named for the product'})"))
            continue
        if pool is None:
            pool_note = "No evidence pool here (no corpus exported), so no record binds."
            continue
        named = unit.records.get(s.key)
        kept, out, bad = _records_for(field, e, spec, pool, named)
        refused += [f"unit {unit.id}, {s.key}: {w}" for w in bad]
        left = "; left out: " + ", ".join(f"{n} {why}" for why, n in out.items()) if out else ""
        if s.key == "release":
            if kept and passes != 1:
                sources[s.key]["waiting"] = ParameterValue(key=s.key, value=None, origin="waiting", source=None, detail=(
                    f"a record of {field} states the release of its step as run, which is one pass's only when the "
                    f"unit runs one pass; this one runs {passes if passes is not None else 'an untyped number of'} "
                    f"passes, so a person sets the release per pass{left}"))
                continue
        if not kept:
            sources[s.key]["waiting"] = ParameterValue(key=s.key, value=None, origin="waiting", source=None, detail=(
                f"no record of {field} on the {spec.program} program's papers binds{left}"))
            continue
        values = [k.value for k in kept]
        how = "each a percentage over a hundred, a share" if field in PERCENT_FIELDS else "each as the record gives it"
        if base == "split" and field == "step_recovery" and onward is not None and onward != outlet0:
            values = [1 - x for x in values]
            how += (f", then one less it: the split is to outlet {outlet0}, and the product goes on by {onward}, so "
                    "what the step recovers is what the split does not send to outlet 0")
        st = binding.statistic(values)
        n = len(kept)
        span = f"{st.low:.4g}" if st.low == st.high else f"{st.low:.4g}–{st.high:.4g}"
        whose = "named for it" if named is not None else f"on the {spec.program} program's papers"
        detail = f"{n} record{'' if n == 1 else 's'} of {field} {whose} ({how}): {span}" + (
            f", the median {st.value:.4g}" if st.sampling == "triangular" else
            f", the middle {st.value:.4g}" if st.sampling == "uniform" else "") + left
        sources[s.key][f"record:{field}"] = ParameterValue(
            key=s.key, value=st.value, low=st.low, high=st.high, origin="record", recordIds=[k.record["id"] for k in kept],
            source=BasisSource(kind="record", note=f"{n} record{'' if n == 1 else 's'} of {field}"), detail=detail)
    if pool_note:
        notes.append(pool_note)
    title = (f"Unit {unit.id} of train {spec.name}: {e.name} (" + (f"BioSTEAM's {e.biosteam}" if e.biosteam
                                                                   else f"in-house {e.inhouse}") + ")")

    def refuses(values: list[ParameterValue]) -> str | None:
        waiting = [v for v in values if v.origin == "waiting" and _required(e, v.key)]
        if waiting:
            return None
        said = catalogue.unmet(e.id, {v.key: v.value for v in values})
        return "; ".join(said) if said else None

    sides = {p.name for p in _side_ports(e)}

    def unread(values: list[ParameterValue]) -> dict[str, str]:
        """A side inlet's flow nobody typed is absent from it; a
        per-component key nobody set, once its template has a value, is left
        to the class."""
        given_ = {v.key: v.value for v in values}
        out = {}
        for v in values:
            base = v.key.partition(catalogue.SEP)[0]
            if base in sides:
                out[v.key] = f"absent from the {base} inlet: a component nobody typed is not in it"
            elif base == "split" and any(k.startswith(f"split{catalogue.SEP}") and x is not None
                                         for k, x in given_.items()):
                out[v.key] = ("set by no record or person: BioSTEAM reads a component a split does not name as none "
                              f"of it to outlet {outlet0}")
        return out

    return UnitScope(unit, e, params.Provided(title=title, specs=specs, sources=sources, notes=notes, refuses=refuses,
                                              unread=unread), given, refused, read_from)


def _required(e: catalogue.Entry, key: str) -> bool:
    """Whether a waiting key holds a run back: a plain parameter does; a
    per-component or per-effect key, or a side inlet's flow, is left to the
    class (its needs, `catalogue.unmet`, say what it must have)."""
    base = key.partition(catalogue.SEP)[0]
    return base not in catalogue.template_keys(e) and base not in {p.name for p in _side_ports(e)}


def _pool() -> Any:
    from .. import evidence_pool

    try:
        return evidence_pool.load(include_archived=True)
    except FileNotFoundError:
        return None


def _product_chemical(product: str) -> str | None:
    from .. import thermo

    return thermo.CHEMICALS.get(product)


def provided(ids: tuple[str, ...], req: ParamResolveRequest) -> params.Provided:
    """The `pureos-unit` scope of a unit of the train the request sends, or
    of its inlet (catalogue.py's provider calls this when a train is sent)."""
    spec = req.train
    assert spec is not None
    train_id, unit_id = ids
    if spec.id != train_id:
        raise params.ParamRefused(f"this scope names train {train_id}; the train sent is {spec.id}")
    try:
        if unit_id == INLET:
            # A scope names its train by id, so its inlet reads whatever the
            # program switch says, as a Proforma scope's records bind
            # (OF-BLD-016); the run honours the switch.
            return _inlet_read(spec, True).provided
        unit = next((u for u in spec.units if u.id == unit_id), None)
        if unit is None:
            raise params.ScopeUnknown(f"train {spec.id} has no unit {unit_id}; its units are "
                                      f"{', '.join(u.id for u in spec.units) or 'none'} and its inlet")
        if req.unitType and req.unitType != unit.type:
            raise params.ParamRefused(f"unit {unit_id} of train {spec.id} is a {unit.type}, not a {req.unitType}")
        try:
            catalogue.entry(unit.type)
        except catalogue.CatalogueUnknown as e:
            raise params.ParamRefused(str(e)) from None
        chems = chemicals_of(spec, req.overrides, include_archived=True)
        # The request's overrides decide what expands with them (an
        # evaporator's effects) and what a record binds beside (passes); the
        # resolve lays them on.
        got = unit_scope(spec, unit, chems, _pool(), req.overrides, _product_chemical(spec.product))
        if got.refused:
            raise params.ParamRefused("; ".join(got.refused))
        return got.provided
    except (TrainRefused, TrainNotOnFile) as e:
        raise params.ParamRefused(str(e)) from None


# ── the run ────────────────────────────────────────────────────────────


def _installed(dist: str) -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(dist)
    except PackageNotFoundError:
        return "not installed"


def _version() -> str:
    return (f"{VERSION_WORDS} · biosteam {_installed('biosteam')} · thermosteam {_installed('thermosteam')} · "
            f"biorefineries {_installed('biorefineries')}")


def run_train(spec: TrainSpec, overrides: Iterable[Override] | None = None, by: str | None = None,
              include_archived: bool = False) -> TrainRun:
    """Resolve every value of the train with its source, refuse in words what
    cannot run (the validation's refusals, a value that waits naming what
    would bind it, a unit's needs, every one at once), and keep one
    `pureos.train_run` artifact, or return the one kept for the same basis."""
    from .. import artifacts, programs, proforma

    said = validate(spec)
    if said:
        raise TrainRefused("; ".join(said))
    overrides = list(overrides or [])
    scopes = {scope_of(spec.id, INLET), *(scope_of(spec.id, u.id) for u in spec.units)}
    stray = sorted({o.scope for o in overrides if o.scope not in scopes})
    if stray:
        raise TrainRefused(f"an override names the scope it changes, and these are no unit's of train {spec.id}: "
                           f"{', '.join(stray)}")
    try:
        if programs.hides(spec.program, include_archived):
            p = programs.program_by_id(spec.program)
            raise TrainRefused(f"train {spec.id} belongs to {p.name if p else spec.program}, archived (hidden). "
                               f"{programs.SWITCH}")
    except FileNotFoundError:
        pass
    if spec.program not in PROGRAM_CHEMICALS:
        raise TrainRefused(f"pureOS builds a train on {', '.join(PROGRAM_CHEMICALS.values())}; program {spec.program} "
                           "has no chemical set here, so its train does not run yet")
    chem = _product_chemical(spec.product)
    if chem is None:
        from .. import thermo

        try:
            thermo.chemical_of(spec.product)
        except Exception as e:  # VolatilityMissing, ThermoRefused: in their words
            raise TrainRefused(f"{e}. A train traces its product by the library's own name for it") from None
    ws = train_specs()
    inlet = inlet_stream(spec, overrides, by, include_archived)
    unknown = sorted(set(inlet.chemicals) - set(ws["chemicals"]))
    if unknown:
        raise TrainRefused(f"the inlet carries {', '.join(unknown)}, which {PROGRAM_CHEMICALS[spec.program]} do not "
                           "hold: the train cannot build its stream")
    pool = _pool()
    refusals: list[str] = []
    resolved: list[tuple[UnitScope, list[ParameterValue]]] = []
    for unit in spec.units:
        got = unit_scope(spec, unit, inlet.chemicals, pool, overrides, chem)
        refusals += got.refused
        try:
            values = params.resolve(got.provided.specs, got.provided.sources, got.overrides, by)
        except params.ParamRefused as e:
            refusals.append(f"unit {unit.id}: {e}")
            continue
        refusals += _waiting_words(f"unit {unit.id} ({got.entry.id})", [v for v in values if _required(got.entry, v.key)])
        refusals += [f"unit {unit.id}: {w}" for w in catalogue.unmet(got.entry.id, {v.key: v.value for v in values})]
        try:
            catalogue.kwargs_of(got.entry.id, {v.key: v.value for v in values})
        except ValueError as e:
            refusals.append(f"unit {unit.id}: {e}")
        resolved.append((got, values))
    if refusals:
        raise TrainRefused("; ".join(refusals))
    sim = f"biosteam@{ws['versions']['biosteam']}"
    lib = f"biorefineries@{ws['versions']['biorefineries']}"
    basis: list[BasisInput] = [
        BasisInput(name="train", value=json.dumps(spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
                   unit="", source=BasisSource(kind="convention", note=(
                       "the train as data (D9), as the request sent it: its inlet, its units in order, where each "
                       "outlet goes, and every value a person typed, each also named below with its source"))),
        BasisInput(name="program", value=spec.program, unit="", source=BasisSource(kind="convention",
                                                                                   note="the train's program")),
        BasisInput(name="product", value=spec.product, unit="", source=BasisSource(kind="convention",
                                                                                   note="the train's product")),
        BasisInput(name="product chemical", value=chem or "", unit="", source=BasisSource(kind="convention", note=(
            f"thermosteam's own name for {spec.product}, as thermo.CHEMICALS names it: the chemical the train traces"))),
        BasisInput(name="chemicals", value=PROGRAM_CHEMICALS[spec.program], unit="", source=BasisSource(
            kind="model", id=lib, note="the chemical set every unit of the train is built on")),
        *(BasisInput(name=dist, value=v, unit="", source=BasisSource(kind="model", id=f"{dist}@{v}", note=(
            f"the {dist} version the worker ran"))) for dist, v in sorted(ws["versions"].items())),
        proforma.utility_input(),
        proforma.diagram_input(),
        *inlet.basis,
    ]
    for got, values in resolved:
        u, e = got.unit, got.entry
        cls_src = (BasisSource(kind="model", id=sim, note=f"BioSTEAM's {e.biosteam}, built as unit {u.id}")
                   if e.biosteam else BasisSource(kind="model", id="openferment.pureos.inhouse",
                                                  note=f"the in-house {e.inhouse} (pureos/inhouse.py), built as unit {u.id}"))
        basis.append(BasisInput(name=f"{u.id} type", value=e.id, unit="", source=BasisSource(kind="convention",
                                                                                            note=f"{e.name}: {e.line}")))
        basis.append(BasisInput(name=f"{u.id} class", value=e.cls, unit="", source=cls_src))
        for name, route in routes(u, e).items():
            basis.append(BasisInput(name=f"{u.id} outlet {name}", value=route, unit="", source=BasisSource(
                kind="convention", note=f"where outlet {name} goes, as the train routes it (D9)")))
        if u.readFrom is not None:
            basis.append(BasisInput(name=f"{u.id} reads", value=f"{u.readFrom.flowsheet} {u.readFrom.unit}", unit="",
                                    source=BasisSource(kind="model", id=lib, note=(
                                        f"the shelf flowsheet's own unit whose values unit {u.id} takes first"))))
        basis += [b.model_copy(update={"name": f"{u.id}{catalogue.SEP}{b.name}"})
                  for b in params.basis_inputs(got.provided.specs, values)]
    art = artifacts.compute(TRAIN_RUN, basis, records_by_id=pool.records_by_id if pool is not None else {})
    return run_of(art)


# ── the artifact ───────────────────────────────────────────────────────


def _named(inputs: list[BasisInput], name: str) -> BasisInput | None:
    return next((i for i in inputs if i.name == name), None)


def _class_default(src: BasisSource) -> bool:
    return src.kind == "model" and any((src.id or "").startswith(x) for x in CLASS_DEFAULT_IDS)


def _prefixed(inputs: list[BasisInput], prefix: str) -> dict[str, BasisInput]:
    return {i.name[len(prefix):]: i for i in inputs if i.name.startswith(prefix)}


_SUFFIXES = (" low", " high", " record")


def _values(given: dict[str, BasisInput], spec_of: Any) -> list[ParameterValue]:
    """A place's values as its basis holds them, each with its source."""
    out = []
    for key, i in given.items():
        if key.endswith(_SUFFIXES):
            continue
        records = [str(x.value) for k, x in given.items() if k == f"{key} record"]
        low, high = given.get(f"{key} low"), given.get(f"{key} high")
        kind = i.source.kind
        origin = ("record" if records else "assumption" if kind == "assumption" else
                  "library-default" if kind == "model" else "convention" if kind == "convention" else "artifact")
        v = ParameterValue(key=key, value=i.value, low=float(low.value) if low else None,
                           high=float(high.value) if high else None, source=i.source, origin=origin,  # type: ignore[arg-type]
                           overriddenBy=i.source.by if kind == "assumption" else None, recordIds=records,
                           detail=i.source.note)
        s = spec_of(key)
        if s is not None:
            v.outOfBounds = params.bounds_check(s, v.value, v.low, v.high)
        out.append(v)
    return out


def _spec_of(e: catalogue.Entry) -> Any:
    specs = {s.key: s for s in catalogue.static_specs(e)}

    def of(key: str) -> ParameterSpec | None:
        base, sep, _ = key.partition(catalogue.SEP)
        if key in specs:
            return specs[key]
        if sep and base in specs:
            return specs[base]
        if sep and base in {p.name for p in _side_ports(e)}:
            return _spec(key, key, "", "massFlow", "kg h⁻¹", ["assumption"], (0, None, "a physical limit: no negative flow"))
        return None
    return of


def _inlet_spec_of(key: str) -> ParameterSpec | None:
    """An inlet value's spec, for its bounds: each is a physical limit at
    none."""
    base = key.partition(catalogue.SEP)[0]
    if key in ("broth_flow", "harvest_hour", "T", "P") or base in ("conc", "flow"):
        return _spec(key, key, "", "", "", ["assumption"], (0, None, "a physical limit: none of it is negative"))
    return None


def purity_of(streams: list[dict[str, Any]], product: str, product_stream: str | None) -> TrainPurity:
    """Every stream's product share by mass and its largest other components,
    read from the stream table."""
    rows = []
    for s in streams:
        total = float(s.get("massFlow") or 0.0)
        flows = {k: float(v) for k, v in (s.get("massFlows") or {}).items() if v > 0}
        if total <= 0:
            rows.append(StreamPurity(stream=s["id"], massFlow=total))
            continue
        others = sorted(((k, v) for k, v in flows.items() if k != product), key=lambda kv: -kv[1])[:IMPURITIES]
        rows.append(StreamPurity(stream=s["id"], massFlow=total, productFraction=flows.get(product, 0.0) / total,
                                 impurities=[StreamImpurity(chemical=k, massFraction=v / total) for k, v in others]))
    main = next((r for r in rows if r.stream == product_stream), None)
    return TrainPurity(product=product, productStream=product_stream,
                       productFraction=main.productFraction if main else None, streams=rows,
                       impuritiesShown=IMPURITIES, note=(
                           f"{product}'s share of each stream's mass, and the {IMPURITIES} largest other components by "
                           "mass, read from the stream table; a stream carrying nothing has no share"))


def _run_train(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """The run, from its basis alone: the train as data, every value as the
    basis holds it, the inlet; the worker builds and runs it, and this reads
    what it gives. A value whose source is the class's own default is left
    to the class; every other one is passed."""
    from .. import proforma
    from ..workers import WorkerError

    spec = TrainSpec.model_validate_json(str(_named(inputs, "train").value))  # type: ignore[union-attr]
    chem = str(_named(inputs, "product chemical").value)  # type: ignore[union-attr]
    given = _prefixed(inputs, f"{INLET}{catalogue.SEP}")
    conc = {k.split(catalogue.SEP, 1)[-1]: float(i.value) for k, i in given.items()  # type: ignore[arg-type]
            if k.startswith(f"conc{catalogue.SEP}") and not k.endswith(_SUFFIXES)}
    flows = {k.split(catalogue.SEP, 1)[-1]: float(i.value) for k, i in given.items()  # type: ignore[arg-type]
             if k.startswith(f"flow{catalogue.SEP}")}
    balance = _named(inputs, "inlet balance")
    inlet = {"flows": flows or None, "concentrations": conc if balance is not None else None,
             "brothFlow": float(given["broth_flow"].value) if "broth_flow" in given else None,  # type: ignore[arg-type]
             "balance": str(balance.value) if balance is not None else None,
             "T": float(given["T"].value), "P": float(given["P"].value),  # type: ignore[arg-type]
             "phase": str(_named(inputs, "inlet phase").value)}  # type: ignore[union-attr]
    units = []
    parameters: list[TrainUnitParameters] = []
    notes: list[str] = []
    flags: list[str] = []
    chems = sorted({*conc, *flows, *((str(balance.value),) if balance is not None else ())})
    for u in spec.units:
        e = catalogue.entry(u.type)
        mine = _prefixed(inputs, f"{u.id}{catalogue.SEP}")
        sides = {p.name for p in _side_ports(e)}
        values: dict[str, Any] = {}
        side_flows: dict[str, dict[str, float]] = {}
        for key, i in mine.items():
            if key.endswith(_SUFFIXES) or _class_default(i.source):
                continue
            base, _, item = key.partition(catalogue.SEP)
            if base in sides and item:
                side_flows.setdefault(base, {})[item] = float(i.value)  # type: ignore[arg-type]
            else:
                values[key] = i.value
        units.append({"id": u.id, "type": e.id, "values": values, "outlets": routes(u, e), "sides": side_flows})
        vals = _values(mine, _spec_of(e))
        parameters.append(TrainUnitParameters(unit=u.id, type=e.id, unitClass=e.cls, values=vals))
        flags += [f"unit {u.id}: {v.outOfBounds}" for v in vals if v.outOfBounds]
        per = [p.key for p in e.params if p.per == "component" and p.key in ("split",)]
        for t in per:
            unset = [c for c in chems if f"{t}{catalogue.SEP}{c}" not in mine]
            if unset:
                notes.append(f"Unit {u.id}: no record or person set {', '.join(f'{t}.{c}' for c in unset)}; BioSTEAM "
                             f"reads a split that does not name a component as none of it to outlet "
                             f"{_out_ports(e)[0].name}.")
        if e.biosteam == "DrumDryer":
            notes.append(f"Unit {u.id} is BioSTEAM's DrumDryer, which burns its fuel without taking the oxygen from its "
                         "gas: its outlets carry that oxygen's mass beyond its inlets (pureOS §5.1). No product is "
                         "counted in it, and the difference is the class's, not a broken balance.")
    request = {"system": "pureos_" + re.sub(r"[^A-Za-z0-9_]", "_", spec.id), "product": chem, "inlet": inlet,
               "units": units, "diagram": proforma._draws(inputs)}
    try:
        said = proforma.call("train_run", request)
    except WorkerError as e:
        text = str(e)
        if text.startswith("Refused: "):
            raise TrainRefused(text.removeprefix("Refused: ")) from None
        raise
    costs = []
    by_unit = {c["unit"]: c for c in said["costs"]}
    for u in spec.units:
        e = catalogue.entry(u.type)
        c = by_unit.get(u.id) or {}
        if not e.cost_model:
            costs.append(TrainUnitCost(unit=u.id, type=e.id, unitClass=e.cls, costModel=False, note=(
                "no cost model: " + next((n for n in e.notes if n.startswith("No cost model")), "the in-house unit "
                                         "carries no correlation with a source, so BioSTEAM's Unit costs it at nothing"))))
            continue
        costs.append(TrainUnitCost(unit=u.id, type=e.id, unitClass=c.get("unitClass") or e.cls, costModel=True,
                                   purchaseCost=c.get("purchaseCost"), installedCost=c.get("installedCost"),
                                   items=c.get("items") or {},
                                   note=next((n for n in e.notes if "costs a" in n and "at nothing" in n), None)))
    built = said["inlet"]
    absent = _named(inputs, "inlet absent")
    ref = _named(inputs, "inlet")
    ref_tool = None
    if ref is not None:
        from .. import artifacts

        try:
            ref_tool = artifacts.get(str(ref.value)).tool
        except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged):
            ref_tool = None
    inlet_notes = [str(i.source.note) for i in inputs if i.name in ("inlet kind", "cells read as", "product read as")
                   and i.source.note]
    hour = given.get("harvest_hour")
    if hour is not None and hour.source.kind == "assumption":
        inlet_notes.append(f"the broth is taken at {float(hour.value):.6g} h, an hour {hour.source.by} named, not the "
                           "simulation's own harvest hour")
    read = TrainInletRead(
        kind=spec.inlet.kind, ref=spec.inlet.ref, refTool=ref_tool, streamId=spec.inlet.streamId, vessel=spec.inlet.vessel,
        chemicals=chems, concentrations=conc if balance is not None else None, flows=built["flows"],
        water=built.get("water"), waterNote=built.get("waterNote"), brothFlow=inlet["brothFlow"],
        harvestHour=float(given["harvest_hour"].value) if "harvest_hour" in given else None,  # type: ignore[arg-type]
        T=built["T"], P=built["P"], phase=built["phase"], absent=str(absent.value) if absent and absent.value else None,
        notes=inlet_notes)
    flags += [f"the inlet: {v.outOfBounds}" for v in _values(given, _inlet_spec_of) if v.outOfBounds]
    return {
        "train": spec.model_dump(mode="json"), "flowsheet": None,
        "tablesSource": said["tablesSource"], "streams": said["streams"], "units": said["units"],
        "utilities": said["utilities"], "diagram": said.get("diagram"), "diagramNote": said.get("diagramNote"),
        "unitOrder": said["unitOrder"], "tableUnits": said["tableUnits"],
        "product": chem, "productId": spec.product, "productStream": said["productStream"],
        "purity": purity_of(said["streams"], chem, said["productStream"]).model_dump(mode="json"),
        "costs": [c.model_dump(mode="json") for c in costs], "inlet": read.model_dump(mode="json"),
        "parameters": [p.model_dump(mode="json") for p in parameters], "outlets": said["outlets"],
        "utilitySettings": said.get("utilitySettings") or {}, "versions": said.get("versions") or {},
        "notes": notes, "flags": flags,
    }


def _register() -> None:
    from .. import artifacts

    artifacts.register(TRAIN_RUN, _version(), _run_train)


def _register_lazy() -> None:
    from .. import artifacts

    artifacts.register_lazy(TRAIN_RUN, _register)


_register_lazy()


def run_of(art: Artifact) -> TrainRun:
    """A kept train run, read: the train as pureos.train_of reads it, and
    the artifact's own purity, costs, inlet, parameters, notes and flags."""
    from .. import artifacts
    from . import train_of

    if art.tool != TRAIN_RUN:
        raise TrainRefused(f"artifact {art.id} is a {art.tool} artifact, not a train run ({TRAIN_RUN})")
    o = art.output
    return TrainRun(artifactId=art.id, provenance=art.provenance, createdAt=art.createdAt,  # type: ignore[arg-type]
                    spec=TrainSpec.model_validate(o["train"]), train=train_of(art), purity=TrainPurity(**o["purity"]),
                    costs=[TrainUnitCost(**c) for c in o["costs"]], inlet=TrainInletRead(**o["inlet"]),
                    parameters=[TrainUnitParameters(**p) for p in o["parameters"]], notes=o.get("notes") or [],
                    flags=o.get("flags") or [], basis=artifacts.basis_of(art))


# ── what is on file ────────────────────────────────────────────────────


def program_of_run(art: Artifact, record_lookup: Any = None) -> str | None:
    """A train run's program: the program its train names, what its basis
    names (its records), and its inlet's (the simulation's or run's), an
    archived program winning, so a run built on an archived program's broth
    hides with it."""
    from .. import artifacts, module_stores, programs

    found: list[str | None] = [next((str(i.value) for i in art.inputs if i.name == "program"), None)]
    try:
        found.append(programs.program_of_artifact(art, record_lookup))
    except FileNotFoundError:
        pass
    ref = next((i for i in art.inputs if i.name == "inlet" and i.source.kind == "artifact" and i.source.id), None)
    if ref is not None and ref.source.id != art.id:
        try:
            found.append(module_stores.artifact_program(artifacts.get(str(ref.source.id)), record_lookup))
        except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged, FileNotFoundError):
            pass
    kept = [p for p in found if p]
    try:
        archived = next((p for p in kept if programs.is_archived(p)), None)
    except FileNotFoundError:
        archived = None
    return archived or (kept[0] if kept else None)


def train_runs(include_archived: bool = False, *, arts: Iterable[Artifact] | None = None) -> list[TrainSummary]:
    """GET /api/pureos/train-runs: every kept train run, newest first; one of
    an archived program left out unless asked. A read: no worker starts."""
    from .. import artifacts, programs
    from . import _Marks, summary, train_of

    kept = list(artifacts.all_artifacts() if arts is None else arts)
    mark = _Marks(kept)
    out = []
    for a in kept:
        if a.tool != TRAIN_RUN:
            continue
        try:
            tr = train_of(a, provenance=mark(a))
        except (KeyError, TypeError, ValueError):
            continue
        try:
            if programs.hides(tr.program, include_archived):
                continue
        except FileNotFoundError:
            pass
        out.append(summary(tr))
    return sorted(out, key=lambda s: (s.createdAt, s.artifactId), reverse=True)


