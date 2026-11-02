"""The seam on the service's side: a vessel and a train become a flowsheet
Proforma prices (OF-BLD-020 §6.1, D11, D3, E.2‴, E.3‴; Appendix 2 §D).

`custom_train_v1` (flowsheets/shelf.py, flowsheets/custom_train_v1.py) is
built from two kept artifacts a scenario names, as the project's scenario
row keeps them and every request carries them (`vessel`, `trainRun`):

    the vessel design   a `fermos.vessel` artifact: its fermenter is rebuilt
                        in the Proforma worker as the same BioSTEAM class,
                        every design parameter as the design passed it
                        BioSTEAM, running the reaction it was built on
    the train run       a `pureos.train_run` artifact: its units follow the
                        fermenter on its beer, each the same catalogue type
                        with the values the run held; the train's own inlet
                        is not an input (the beer is its inlet)

This module never imports BioSTEAM (E.3‴): it reads the two artifacts, says
in words why a pair cannot stand, writes what the worker builds
(`structure`) and what the run's basis names, and declares the TEA's
financial parameters for the parameter panel.

    parts_of(vessel, train_run)   the two artifacts,
        read and held to the rules: both named, both on file, each of its
        own tool, neither damaged, the train built on the chemical set pureOS
        holds (`program`, the set's key), a vessel designed at a plant scale
        (one vessel's batch volume sizes no plant: §6.R, main-4/22), no unit
        id of the train that the fermenter or its feed mixer takes, and no
        unit of the train fed a side inlet (its flow is the run's own, not
        scaled to the plant: §6.R, main-25); refused in words
        (proforma.ScenarioRefused) otherwise
    fermenter_of(vessel_art)      what the worker rebuilds the fermenter from
    train_of(train_art)           the train's units, as the worker builds them
    vessel_scale(inputs, parts)   the plant scale the vessel was designed at
        binds `plant_scale` (an artifact source), unless a person typed one
    finance_specs() / finance_sources() / finance_values(overrides)
        the panel's group *Finance* in scope `proforma:<scenario id>`: every
        parameter `biorefineries.corn.tea.default_tea_parameters` names, its
        value the package's own (library default) until a person sets one,
        read from the installed file without importing it
        (shelf.package_tea_defaults)
    finance_refusal(values)       a schedule that does not sum to the whole,
        a life that ends before it starts, a year that is no whole number, a
        depreciation schedule longer than the life (BioSTEAM's own table:
        §6.R, main-29)
    basis_inputs(parts, finance)  what the run's basis names beyond a
        scenario run's: both artifacts (`artifact` sources, so their
        provenance follows into the run's), the fermenter's class, unit id,
        reaction and every design parameter (`fermenter.<key>`, source the
        vessel design), each train unit's type, class, outlets and values
        (`train.<unit>.<key>`, sources as the train run's basis holds them),
        and every finance parameter (`finance.<key>`, the library's default
        or a person's assumption)
    structure_of(inputs)          the worker's structure, from a run's basis
        alone (so a kept run replays): the fermenter, the train and the
        finance a person set

Rule 1: no process number here. The constants are words, prefixes and one
structural tolerance (`SCHEDULE_RTOL`), each with its reason.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, NamedTuple

from . import params
from .basis import ASSUMED_KINDS
from .flowsheets import shelf as _shelf
from .models import Artifact, BasisInput, BasisSource, Override, ParameterSpec, ParameterValue

FLOWSHEET = _shelf.COMPOSITE
VESSEL_TOOL, TRAIN_TOOL = _shelf.COMPOSITE_BUILT_FROM
FINANCE_GROUP = "Finance"
# The prefixes of what a composite run's basis names beyond a scenario run's
# inputs: a flowsheet input's key is one word (\w+), so a name with one of
# these is never read as an input to sample (proforma._specs).
FERMENTER, TRAIN, FINANCE = "fermenter.", "train.", "finance."
PREFIXES = (FERMENTER, TRAIN, FINANCE)
SEP = "."
# The feed mixer's unit id in flowsheets/custom_train_v1.py (MIXER).
MIXER_ID = "M1"
# The flowsheet inputs the vessel design binds.
VESSEL_BOUND = ("plant_scale",)
# A construction schedule's shares sum to the whole within the float's own
# rounding (a precision, not a process number).
SCHEDULE_RTOL = 1e-9
DURATION, SCHEDULE, DEPRECIATION = "duration", "construction_schedule", "depreciation"
DURATION_PARTS = ("start", "end")

_HOW_VESSEL = "fermOS → Vessel designs one for a kept simulation"
_HOW_TRAIN = "pureOS → New train builds and runs one"


def _refused(words: str) -> Exception:
    from .proforma import ScenarioRefused

    return ScenarioRefused(words)


# ── the parts ──────────────────────────────────────────────────────────


class Parts(NamedTuple):
    """The two artifacts a composite is built from, and the chemical set its train was built on."""

    vessel: Artifact
    train: Artifact
    program: str | None


def _artifact(aid: str, tool: str, what: str, how: str) -> Artifact:
    from . import artifacts

    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise _refused(f"there is no kept artifact {aid} here for {what}: {how}") from None
    except artifacts.ArtifactDamaged as e:
        raise _refused(f"{what}, {e}") from None
    if art.tool != tool:
        raise _refused(f"artifact {aid} is a {art.tool} artifact, not {what} ({tool})")
    return art


def parts_of(vessel: str | None, train_run: str | None) -> Parts:
    """The vessel design and the train run a composite scenario names, held
    to the rules (the module's docstring lists them), or the refusal."""
    from .pureos import train_spec

    missing = [w for w, x in (("vessel design (vessel)", vessel), ("train run (trainRun)", train_run)) if not x]
    if missing:
        raise _refused(f"{FLOWSHEET} is built from a kept vessel design (a {VESSEL_TOOL} artifact) and a kept train run "
                       f"(a {TRAIN_TOOL} artifact), named by the scenario; this names no {' and no '.join(missing)}. "
                       f"{_HOW_VESSEL}; {_HOW_TRAIN}")
    v = _artifact(str(vessel), VESSEL_TOOL, "the vessel design", _HOW_VESSEL)
    t = _artifact(str(train_run), TRAIN_TOOL, "the train run", _HOW_TRAIN)
    try:
        tp = train_spec.program_of_run(t)
    except FileNotFoundError:
        tp = None
    if tp not in train_spec.PROGRAM_CHEMICALS:
        said = (f"is built on the chemical set {tp}, which pureOS does not hold" if tp
                else "names no chemical set it was built on")
        raise _refused(f"train run {t.id} {said}: {FLOWSHEET} is built on "
                       f"{', '.join(train_spec.PROGRAM_CHEMICALS.values())}, so it takes a train run of that set alone")
    one = _batch_volume(v)
    if one is not None:
        raise _refused(one)
    unit_id = fermenter_of(v)["unitId"]
    tr = train_of(t)
    spec = tr["spec"]
    clash = sorted({u.id for u in spec.units} & {MIXER_ID, unit_id})
    if clash:
        raise _refused(f"train run {t.id} names a unit {', '.join(clash)}, which {FLOWSHEET}'s feed mixer ({MIXER_ID}) or "
                       f"fermenter (the vessel design's unit {unit_id}) takes: give that unit another id in pureOS and "
                       "run the train again")
    fed = _side_inlets(t, tr["units"])
    if fed is not None:
        raise _refused(fed)
    return Parts(vessel=v, train=t, program=tp)


def _batch_volume(v: Artifact) -> str | None:
    """Why a vessel designed for one vessel's batch volume cannot be a
    composite's fermenter, in words, or None (OF-BLD-020 §6.R, main-4/22).

    Its one vessel was sized for the batch volume fed over its cycle; the
    composite feeds the fermenter the plant's flow from the plant scale, so
    rebuilt as one vessel it would be one vessel of whatever size that flow
    asks, priced as a vessel nobody designed. The smaller, reversible choice
    of the two the review offered: refused here, before any worker runs, for
    the binding, the panel and the run alike."""
    bv = next((i for i in v.inputs if i.name == "batch_volume"), None)
    if bv is None:
        return None
    size = f", {float(bv.value):g} {bv.unit}" if isinstance(bv.value, (int, float)) and not isinstance(bv.value, bool) else ""
    return (f"vessel design {v.id} was designed for one vessel's batch volume (batch_volume){size}: {FLOWSHEET} prices a "
            "plant fed at its plant scale, and one vessel of a batch volume sizes no plant (rebuilt for the plant's flow "
            "it would be one vessel of whatever size that flow asks, not the vessel designed); design the vessel at a "
            "plant scale in fermOS → Vessel, and its plant scale binds this flowsheet's")


def _side_inlets(t: Artifact, units: list[dict[str, Any]]) -> str | None:
    """Why a train run whose units are fed a side inlet cannot be a
    composite's train, in words, or None (OF-BLD-020 §6.R, main-25).

    A side inlet's flow (a solvent, say) is a person's kg h⁻¹ for the train
    run's own inlet; the composite sets the beer from the plant scale, and
    the train module feeds a side inlet at its absolute flow, so the
    extraction priced would not be the one the run made. Whether to scale it
    by the beer over the run's inlet is a decision the document leaves open:
    refused here until it is made (the smaller, reversible choice)."""
    fed = []
    for u in units:
        ports = [f"{port}: " + ", ".join(f"{chem} {float(kg):g} kg h⁻¹" for chem, kg in flows.items() if kg)
                 for port, flows in (u.get("sides") or {}).items() if any(kg for kg in flows.values())]
        if ports:
            fed.append(f"unit {u['id']} a side inlet ({'; '.join(ports)})")
    if not fed:
        return None
    return (f"train run {t.id} feeds {' and '.join(fed)} at that run's own rate, a flow for the run's own inlet: "
            f"{FLOWSHEET} sets the beer from the plant scale, and a side inlet's flow is not scaled with it, so the "
            "extraction priced would not be the one the run made; price a train run whose units are fed no side inlet")


def fermenter_of(art: Artifact) -> dict[str, Any]:
    """What the worker rebuilds a kept vessel design's fermenter from, as
    plain JSON: its class and unit id, whether it is aerated, every design
    parameter the design passed BioSTEAM (a value whose source was the
    class's own default is left to the class, as vessel.worker_request left
    it), its vessel type, one vessel (a batch volume) or many, its reacting
    time, and the reaction it was built on (an aerated design's
    stoichiometry per glucose used and the scale its oxygen took; the NREL
    design's share of the glucose its cells took)."""
    from . import vessel

    o = art.output or {}
    given = {i.name: i for i in art.inputs}
    aerobic = bool(o.get("aerobic"))
    reaction = o.get("reaction") or {}
    oxygen = o.get("oxygen") or {}
    if aerobic and not reaction.get("stoichiometry"):
        raise _refused(f"vessel design {art.id} keeps no reaction stoichiometry to rebuild its fermenter from")
    design = given.get("vessel type")
    if not o.get("unitClass") or not o.get("unitId") or "tau" not in given:
        raise _refused(f"vessel design {art.id} keeps no unit class, unit id or reacting time to rebuild its fermenter "
                       "from")
    return {
        "vessel": art.id,
        "kind": vessel.AEROBIC if aerobic else vessel.ANAEROBIC,
        "unitClass": str(o["unitClass"]),
        "unitId": str(o["unitId"]),
        "design": str(design.value) if design is not None else None,
        "params": {k: vessel._bool(given[k].value) for k in vessel.DESIGN_KEYS
                   if k in given and given[k].source.kind != "model"},
        "one": "batch_volume" in given,
        "tau": float(given["tau"].value),
        "reaction": ({"stoichiometry": reaction.get("stoichiometry")} if aerobic
                     else {"growthShare": reaction.get("growthShare") or 0}),
        "oxygenScale": float(oxygen.get("scale") or 1) if aerobic else 1,
    }


def train_of(art: Artifact) -> dict[str, Any]:
    """A kept train run's units as the worker builds them, the chemical it
    traces and the train's product (pureos.train_spec.worker_units)."""
    from .pureos import train_spec

    try:
        got = train_spec.worker_units(art)
    except (KeyError, TypeError, ValueError) as e:
        raise _refused(f"train run {art.id} cannot be read as one: {e}") from None
    return {"run": art.id, "units": got["units"], "product": got["product"], "productId": got["train"].product,
            "spec": got["train"]}


def vessel_scale(inputs: list, parts: Parts) -> None:
    """Bind `plant_scale` to the plant scale the vessel was designed at, in
    place, unless a person's value already stands for it (D3: it wins). A
    design of one vessel's batch volume never reaches here: `parts_of`
    refuses it (OF-BLD-020 §6.R, main-4/22); a design that names no plant
    scale all the same leaves the input waiting for a named person, saying
    why."""
    given = {i.name: i for i in parts.vessel.inputs}
    for inp in inputs:
        if inp.key not in VESSEL_BOUND or inp.binding != "waiting":
            continue
        scale = given.get("plant_scale")
        if scale is None:
            inp.flags.append(f"vessel design {parts.vessel.id} was designed for no plant scale, so it gives this "
                             "flowsheet none: a named person's assumption sets it")
            continue
        low, high = given.get("plant_scale low"), given.get("plant_scale high")
        inp.binding = "artifact"
        inp.value = float(scale.value)
        inp.low = float(low.value) if low is not None else inp.value
        inp.high = float(high.value) if high is not None else inp.value
        inp.sampling = "fixed" if inp.low == inp.high else "uniform"
        who = f", typed by {scale.source.by}" if scale.source.by else ""
        inp.source = BasisSource(kind="artifact", id=parts.vessel.id, note=(
            f"the plant scale vessel design {parts.vessel.id} was designed at{who}"))


# ── the finance group (Appendix 2 §D) ──────────────────────────────────


class _Fin(NamedTuple):
    key: str
    label: str
    gloss: str
    dimension: str
    unit: str
    low: float | None
    high: float | None
    reason: str
    step: float | None = None


_SHARE = "a share: it lies between none and the whole"
_FEE = "a physical limit: no negative fee"
_YEAR = "a calendar year: it has no bound of its own"
FINANCE_DECLARED: tuple[_Fin, ...] = (
    _Fin("IRR", "Internal rate of return", "the return on the capital, a share a year, at which the TEA solves the "
         "product's price", "fraction", "", 0, None, "a convention of the panel: a positive return (BioSTEAM solves at "
         "any)"),
    _Fin("duration.start", "First year of the plant's life", "the year the venture starts, construction included",
         "year", "", None, None, _YEAR, 1),
    _Fin("duration.end", "Last year of the plant's life", "the year the venture ends", "year", "", None, None, _YEAR, 1),
    _Fin("depreciation", "Depreciation schedule", "how the capital is written off: a schedule and the years until "
         "the property is worth nothing, by BioSTEAM's own tables", "choice", "", None, None,
         "a choice of words: it has no bounds"),
    _Fin("income_tax", "Income tax", "the combined federal and state income tax, a share of taxable income",
         "fraction", "", 0, 1, _SHARE),
    _Fin("operating_days", "Operating days a year", "the days a year the plant runs", "time", "d yr⁻¹", 0, None,
         "a physical limit: no negative time"),
    _Fin("lang_factor", "Lang factor", "the fixed capital as a multiple of the purchased equipment's cost", "factor",
         "", 0, None, "a physical limit: no negative multiple of a cost"),
    _Fin("construction_schedule", "Capital spent in construction year", "the share of the fixed capital spent in "
         "this year of construction (one parameter a year, as the package's schedule counts them)", "fraction", "",
         0, 1, _SHARE),
    _Fin("WC_over_FCI", "Working capital", "the working capital as a share of the fixed capital", "fraction", "", 0,
         None, _FEE),
    _Fin("labor_cost", "Labour cost", "the plant's labour, a year", "costUSD", "USD yr⁻¹", 0, None,
         "a physical limit: no negative cost"),
    _Fin("fringe_benefits", "Fringe benefits", "the cost of fringe benefits, a share of the labour cost", "fraction",
         "", 0, None, _FEE),
    _Fin("property_tax", "Property tax", "a yearly fee, a share of the fixed capital", "fraction", "", 0, None, _FEE),
    _Fin("property_insurance", "Property insurance", "a yearly fee, a share of the fixed capital", "fraction", "", 0,
         None, _FEE),
    _Fin("supplies", "Supplies", "a yearly fee, a share of the labour cost", "fraction", "", 0, None, _FEE),
    _Fin("maintenance", "Maintenance", "a yearly fee, a share of the fixed capital", "fraction", "", 0, None, _FEE),
    _Fin("administration", "Administration", "a yearly fee, a share of the fixed capital", "fraction", "", 0, None,
         _FEE),
)
_BY_BASE = {d.key.partition(SEP)[0]: d for d in FINANCE_DECLARED}


def _source(key: str) -> BasisSource:
    from .proforma import _installed

    base, _, part = key.partition(SEP)
    which = f"['{base}']" + (f", its {part}" if base == DURATION else f", year {part}" if part else "")
    return BasisSource(kind="model", id=f"biorefineries@{_installed('biorefineries')}", note=(
        f"biorefineries.corn.tea's {_shelf.TEA_DEFAULTS_NAME}{which}, read from the installed package's own file "
        "(the TEA the flowsheet prices with, ConventionalEthanolTEA)"))


def _keys(defaults: dict[str, Any] | None) -> list[tuple[_Fin, str, Any]]:
    """Each panel key with its declaration and the package's value, in the
    declared order: a schedule a key a year, as the package's counts them."""
    out: list[tuple[_Fin, str, Any]] = []
    for d in FINANCE_DECLARED:
        base, _, part = d.key.partition(SEP)
        value = (defaults or {}).get(base)
        if base == DURATION:
            ends = value if isinstance(value, list) else [None, None]
            out.append((d, d.key, ends[DURATION_PARTS.index(part)] if len(ends) == len(DURATION_PARTS) else None))
        elif base == SCHEDULE:
            shares = value if isinstance(value, list) and value else [None]
            out += [(d, f"{base}{SEP}{n}", share) for n, share in enumerate(shares, 1)]
        else:
            out.append((d, d.key, value))
    return out


def _spec(d: _Fin, key: str, choices: list[str] | None) -> ParameterSpec:
    year = key.partition(SEP)[2] if key.startswith(SCHEDULE) else ""
    return ParameterSpec(
        key=key, label=f"{d.label} {year}".strip(), symbol="", gloss=d.gloss, dimension=d.dimension, unit=d.unit,
        min=d.low, max=d.high, step=d.step, group=FINANCE_GROUP, sourceRule=["assumption", "library-default"],
        boundsReason=d.reason, choices=choices,
        note=("The dry-grind corn plant's TEA, as custom_train_v1 prices with it: the package's own value until a "
              "person sets one, which is then their named assumption in the run's basis. A finance value is held at "
              "it across the run's samples: an interval stays in the basis and is not sampled."))


def finance_specs() -> list[ParameterSpec]:
    """The group *Finance*: every parameter the package's defaults name, in
    the declared order; the depreciation schedule a choice of the schedules
    BioSTEAM's TEA holds tables for (and the package's own, when it is not
    among them)."""
    defaults = _shelf.package_tea_defaults()
    schedules = list(_shelf.depreciation_schedules() or [])
    own = (defaults or {}).get(DEPRECIATION)
    if isinstance(own, str) and own not in schedules:
        schedules.append(own)
    return [_spec(d, key, schedules if d.key == DEPRECIATION else None) for d, key, _ in _keys(defaults)]


def finance_sources() -> dict[str, dict[str, ParameterValue | None]]:
    """Each finance key's candidate: the package's own value, a library
    default with the package named; or why there is none."""
    defaults = _shelf.package_tea_defaults()
    out: dict[str, dict[str, ParameterValue | None]] = {}
    for _d, key, value in _keys(defaults):
        if value is None:
            out[key] = {"waiting": ParameterValue(key=key, value=None, source=None, origin="waiting", detail=(
                f"the installed biorefineries holds no {_shelf.TEA_DEFAULTS_NAME} value for it here"))}
            continue
        src = _source(key)
        out[key] = {"library-default": ParameterValue(key=key, value=value, source=src, origin="library-default",
                                                      libraryDefault=value, detail=src.note)}
    return out


def finance_keys() -> set[str]:
    return {s.key for s in finance_specs()}


def split_overrides(overrides: Iterable[Override]) -> tuple[list[Override], list[Override]]:
    """A composite scope's overrides: the flowsheet inputs', and the finance
    group's."""
    keys = finance_keys()
    over = list(overrides or [])
    return [o for o in over if o.key not in keys], [o for o in over if o.key in keys]


def finance_refusal(values: Iterable[ParameterValue]) -> str | None:
    """Why the finance as it stands cannot price a plant, in words, or None:
    construction shares that do not sum to the whole, a life that ends before
    it starts, a year that is no whole number."""
    by = {v.key: v.value for v in values}
    said = []
    shares = [by[k] for k in sorted((k for k in by if k.startswith(f"{SCHEDULE}{SEP}")),
                                    key=lambda k: int(k.partition(SEP)[2]))]
    if shares and all(isinstance(x, (int, float)) for x in shares):
        total = math.fsum(float(x) for x in shares)
        if abs(total - 1) > SCHEDULE_RTOL:
            said.append(f"the construction schedule's shares sum to {total:.6g}: they are the shares of the fixed capital "
                        "spent each year of construction, and sum to the whole")
    start, end = by.get(f"{DURATION}{SEP}start"), by.get(f"{DURATION}{SEP}end")
    for what, y in (("first", start), ("last", end)):
        if isinstance(y, (int, float)) and not float(y).is_integer():
            said.append(f"the plant's {what} year, {y:g}, is no whole year")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and not end > start:
        said.append(f"the plant's life ends ({end:g}) before it starts ({start:g})")
    # OF-BLD-020 §6.R (main-29): BioSTEAM refuses a depreciation schedule
    # longer than the plant's life in every case of a run; its table's
    # length is read from its file (shelf.depreciation_lengths), never typed.
    schedule = by.get(DEPRECIATION)
    years = _shelf.depreciation_lengths().get(schedule) if isinstance(schedule, str) else None
    if years and isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start \
            and years > end - start:
        said.append(f"the depreciation schedule {schedule} writes the capital off over {years} years by BioSTEAM's own "
                    f"table, longer than the plant's life of {end - start:g} years ({start:g} to {end:g}): BioSTEAM "
                    "refuses a schedule longer than the life; choose a shorter schedule or a longer life")
    return "; ".join(said) or None


def finance_values(overrides: Iterable[Override] | None, by: str | None = None) -> list[ParameterValue]:
    """The finance group's values with a person's overrides laid on, each
    checked as the panel checks it; refused in words (ParamRefused) as the
    resolve refuses it, and for `finance_refusal`'s reasons."""
    values = params.resolve(finance_specs(), finance_sources(), overrides, by)
    why = finance_refusal(values)
    if why:
        raise params.ParamRefused(why)
    return values


def finance_basis(values: Iterable[ParameterValue]) -> list[BasisInput]:
    """The finance group in a run's basis, each key prefixed `finance.`: the
    package's own value as a `model` input, a person's as their assumption,
    with its low and high (held, not sampled)."""
    return [b.model_copy(update={"name": f"{FINANCE}{b.name}"}) for b in params.basis_inputs(finance_specs(), values)]


# ── the run's basis, and the worker's structure ─────────────────────────


def basis_inputs(parts: Parts, finance: list[ParameterValue]) -> list[BasisInput]:
    """What a composite run's basis names beyond a scenario run's (E.2‴):
    the two artifacts, the fermenter (its class, unit id, reaction, batch-time
    rule and every design parameter, as the vessel design holds it), the
    train (each unit's type, class, outlets, the flowsheet unit it reads and
    every value, with the sources the train run's basis holds), where the
    train's inlet went, the TEA and every finance parameter."""
    from . import vessel
    from .proforma import _installed

    v, t = parts.vessel, parts.train
    f = fermenter_of(v)
    tr = train_of(t)
    sim = f"biosteam@{_installed('biosteam')}"
    corn = f"biorefineries.corn@{_installed('biorefineries')}"
    spec = tr["spec"]
    out = [
        BasisInput(name="vessel", value=v.id, unit="", source=BasisSource(kind="artifact", id=v.id, note=(
            f"the vessel design the fermenter is rebuilt from: BioSTEAM's {f['unitClass']} with every design parameter "
            "as the design passed it BioSTEAM"))),
        BasisInput(name="train run", value=t.id, unit="", source=BasisSource(kind="artifact", id=t.id, note=(
            f"the train run whose units follow the fermenter on its beer, each with its values as the run held them "
            f"(train {spec.id}, {spec.name})"))),
        BasisInput(name="train inlet", value=f"{spec.inlet.kind}{f' {spec.inlet.ref}' if spec.inlet.ref else ''}", unit="",
                   source=BasisSource(kind="convention", note=(
                       "the train's own inlet, as its run had it, is not an input of this flowsheet: the fermenter's "
                       "beer is the train's inlet"))),
        BasisInput(name="chemicals and finance", value=corn, unit="", source=BasisSource(kind="model", id=corn, note=(
            "the dry-grind corn ethanol plant's create_chemicals, and its create_tea: ConventionalEthanolTEA with the "
            "package's default_tea_parameters, each finance parameter a person set laid on"))),
        BasisInput(name="fermenter", value=f"{sim} {f['unitClass']}", unit="", source=BasisSource(kind="model", id=sim, note=(
            f"BioSTEAM's {f['unitClass']}, rebuilt as the vessel design built it (flowsheets/vessel.make_unit), sized "
            "and costed by BioSTEAM"))),
        BasisInput(name="fermenter unit id", value=f["unitId"], unit="", source=BasisSource(kind="convention", note=(
            "the vessel design's own BioSTEAM unit id; the feed mixer is " + MIXER_ID))),
        BasisInput(name="fermenter reaction",
                   value=("the vessel design's reaction, per glucose used" if f["kind"] == vessel.AEROBIC else
                          "Glucose -> 2 Ethanol + 2 CO2 beside the vessel design's cells' reaction"), unit="",
                   source=BasisSource(kind="convention", note=(
                       ("the reaction the aerated design was built on (glucose and oxygen to cells, ethanol, carbon "
                        "dioxide and water), its oxygen scaled as the design scaled it; its conversion is the bound "
                        "yield over the ethanol it makes of a gram of glucose used")
                       if f["kind"] == vessel.AEROBIC else
                       ("glucose to two ethanol and two carbon dioxide at the bound yield over that reaction's "
                        "theoretical yield at thermosteam's molecular weights, beside Glucose -> Yeast + CO2 + H2O at "
                        "the share of the glucose the design's cells took")))),
        BasisInput(name="batch time", value="titre / productivity", unit="h", source=BasisSource(kind="convention", note=(
            "the fermenter's reacting time; the reacting time the vessel was designed for is fermenter.tau"))),
    ]
    named = {i.name: i for i in v.inputs}
    for key in ("tau", *vessel.DESIGN_KEYS, "plant_scale", "batch_volume"):
        for part in ("", " low", " high"):
            i = named.get(f"{key}{part}")
            if i is None:
                continue
            words = (f"{i.source.kind}{f' by {i.source.by}' if i.source.by else ''}"
                     f"{f' {i.source.id}' if i.source.id else ''}{f': {i.source.note}' if i.source.note else ''}")
            # `by` names the person a value the design took as their
            # assumption (OF-BLD-020 §6.R, main-11/23): the run's read-back
            # credits it to them, never to the package. The source stays the
            # design, so the run's provenance follows the artifact.
            out.append(BasisInput(name=f"{FERMENTER}{key}{part}", value=i.value, unit=i.unit, source=BasisSource(
                kind="artifact", id=v.id, note=f"as vessel design {v.id} holds it ({words})",
                by=i.source.by if i.source.kind in ASSUMED_KINDS else None)))
    if named.get("vessel type") is not None:
        vt = named["vessel type"]
        out.append(BasisInput(name=f"{FERMENTER}design", value=vt.value, unit="", source=BasisSource(
            kind="artifact", id=v.id, note=f"as vessel design {v.id} holds it ({vt.source.note or vt.source.kind})")))
    ids = {u["id"] for u in tr["units"]}
    for i in t.inputs:
        head = i.name.split(SEP, 1)[0].split(" ", 1)[0]
        if head in ids:
            out.append(i.model_copy(update={"name": f"{TRAIN}{i.name}"}))
    out.append(BasisInput(name=f"{TRAIN}product chemical", value=tr["product"], unit="", source=BasisSource(
        kind="convention", note=f"the chemical train run {t.id} traces, whose stream the flowsheet prices")))
    return out + finance_basis(finance)


def _named(inputs: Iterable[BasisInput], name: str) -> BasisInput | None:
    return next((i for i in inputs if i.name == name), None)


def structure_of(inputs: list[BasisInput]) -> dict[str, Any]:
    """The worker's structure, from a composite run's basis alone: the
    fermenter of the vessel design it names, the units of the train run it
    names, and the finance a person set (a package default is left to the
    package, as the worker reads it there); every finance key the basis
    names, for the read-back."""
    from . import artifacts

    vessel_id, train_id = _named(inputs, "vessel"), _named(inputs, "train run")
    if vessel_id is None or train_id is None:
        raise _refused(f"a {FLOWSHEET} run's basis names its vessel design and its train run")
    try:
        v, t = artifacts.get(str(vessel_id.value)), artifacts.get(str(train_id.value))
    except artifacts.ArtifactNotFound as e:
        raise _refused(f"there is no kept artifact {e.args[0]} here, which this run is built from") from None
    except artifacts.ArtifactDamaged as e:
        raise _refused(str(e)) from None
    finance = {i.name[len(FINANCE):]: i.value for i in inputs
               if i.name.startswith(FINANCE) and not i.name.endswith((" low", " high")) and i.source.kind != "model"}
    keys = [i.name[len(FINANCE):] for i in inputs if i.name.startswith(FINANCE) and not i.name.endswith((" low", " high"))]
    tr = train_of(t)
    return {"fermenter": fermenter_of(v), "train": {"run": tr["run"], "units": tr["units"], "product": tr["product"]},
            "finance": finance, "financeKeys": keys}
