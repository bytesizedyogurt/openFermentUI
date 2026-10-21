"""fermOS sizes the vessel a simulation needs, on BioSTEAM (OF-BLD-020 §4.1,
D7, E.2‴, E.3‴, Appendix 2 §C).

From a kept `fermos.simulation` (or, anaerobic only, a `kinetic_fit` or
`growth_forecast`, read through `proforma.fit_info` for titre, yield and
batch time), the Proforma worker designs one vessel with BioSTEAM's own
classes (`flowsheets/vessel.py`, ops `vessel_specs` and `vessel_design`):

    aerobic     AeratedBioreactor, a stirred tank ('Riet') or a bubble column
                ('Dewes'): vessels, volumes, schedule, agitator and compressor
                power, cooling, kLa achieved, gas velocity, air and vvm, costs
    anaerobic   NRELAnaerobicBatchBioreactor, the ethanol flowsheet's NREL
                batch fermenter: no gas inlet and no compressor

This module never imports BioSTEAM; it talks to it through the worker's JSON
contract (`proforma.call`, E.3‴).

EVERY PARAMETER IN HAND (Appendix 2 §C, D2). The scope
`fermos:vessel:<simulation or fit id>` serves each design parameter as a
`ParameterSpec` in groups Scale, Vessel, Schedule, Aeration, Agitation, Heat.
The declarations — label, symbol, gloss, unit, bounds and their reason,
source rule — are in this file (`DECLARED`); the values are the vessel
class's own defaults, read from BioSTEAM in the worker at import
(`vessel_specs`), with the class named, and the choices a choice offers are
the ones the class runs (a kLa correlation the class does not implement is
named in the note, never offered). `tau`, the reacting time, is the
simulation's harvest hour (or the fit's batch time) and the peak and
batch-average oxygen uptake are the simulation's, each source `simulation`
and overridable. `plant_scale` and `batch_volume` wait for a named person;
one of the two is needed. `check:seed` holds every declaration to a bounds
reason through `params.check()`, which reads them here with no worker; a sim
test holds the declarations to the class (every key one the class takes).

THE DEMAND. BioSTEAM's aerated class takes no oxygen demand: it sizes the
air for its reaction's uptake averaged over the cycle. The worker builds the
reaction from what the simulation made and scales its oxygen so the class
sizes for the simulation's peak uptake (`oxygen_basis` `peak`, D7's
convention) or its batch average; the oxygen balance is then computed
against the simulated uptake over time, and names the hours it is short.

THE ARTIFACT (E.2‴). `design(req)` keeps one `fermos.vessel` artifact
through `artifacts.compute`. Its basis: the simulation or fit (an `artifact`
input, so its provenance flows in), the vessel class and the chemicals and
the utility prices and cost index (`model`), the vessel type and the unit id
(`convention`), every design parameter with its source (`params.basis_inputs`:
an override an `assumption` by the person; a class default `model`; the
simulation's values `artifact`), and what a plant scale reads (the corn
TEA's operating hours). Its provenance is `basis_provenance`'s: `demo` with
any assumption, which a plant scale or batch volume always is.

    GET  /api/fermos/vessel/specs?simulation=&vesselType=   the ParamScope
    POST /api/fermos/vessel                                 VesselDesign
    GET  /api/fermos/vessels                                kept designs, newest first

OF-BLD-020 §4.2 ADDED. The vessel type is the panel's choice parameter
`design` (BioSTEAM's own name; Stirred tank or Bubble column): a person's
override of it is an assumption by them and chooses the vessel type as the
request's `vesselType` does, and the two must agree (`_chosen_type`). A
request may name a kLa correlation (`klaMethod`, fermos_vessel's), held to the
ones the class runs for the design and kept as a convention of that request
(`_kla_method`). A design carries its `Evidence` (id the artifact's), which
fermos_vessel returns and the screen reads the basis from. And the real
simulation is read as §3.1 keeps it: `end` is the run's last hour, so a run
that goes on past the hour its sugar runs out is read at `harvestH`
(`fermos.harvest`, from the series the artifact keeps: OF-BLD-020 §6.2), its
oxygen uptake up to that hour (`_past_harvest`).

OF-BLD-020 §4.R (the Phase 4 review). The peak uptake is the one the
simulation states (`our.peak`, on its solver's steps), not its display
grid's maximum. The reaction is scaled to the sized uptake at every scale,
and "no aeration" is said only of a scaled reaction still under BioSTEAM's
floor, in terms of the target uptake. The heat cross-check rests on the
oxygen the simulation took up, beside BioSTEAM's duty in the words of how it
was found (the heats of formation, or a person's heat per oxygen times the
oxygen the vessel consumed); a gap between the reaction's balanced oxygen
and the simulation's beyond `OXYGEN_AGREE_RTOL` is flagged with both
numbers. `N` is a whole number at or above the class's own minimum (the NREL
vessel refuses one, read from its code), and a V_max the class cannot use is
refused in words before the worker is asked (`_held`), as is a person's
V_max beside a batch volume, whose one vessel V_max does not bound: its
basis names no V_max. A kept design's parameters carry the library defaults
of the class and design built.
"""
from __future__ import annotations

import math
import threading
from typing import Any, Iterable

from . import params
from .models import (
    Artifact,
    BasisInput,
    BasisSource,
    Evidence,
    Override,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    VesselDesign,
    VesselRequest,
    VesselSummary,
)

TOOL = "fermos.vessel"
# The program whose chemicals the vessel is built on (its cells Yeast, its
# product ethanol), by its id in programs.ts (§8.R, finding 6).
YEAST_PROGRAM = "yeast"
# 2 since §4.R: the cross-check's oxygen, the scale at every size, the
# duty's words and the stated peak changed what a design computes.
VERSION_WORDS = "vessel 2"
SIMULATION = "fermos.simulation"
FIT_TOOLS = ("kinetic_fit", "growth_forecast")
# The families whose simulation is one batch on glucose making ethanol and
# cells, which the yeast program's chemicals hold; a fed-batch's feed and a
# chemostat's flow are not designed here yet.
DESIGNABLE = ("batch_v1",)
# A fit's titre, yield and batch time are read as the ethanol flowsheet reads
# them (proforma.fit_info).
FIT_FLOWSHEET = "ethanol_glucose_v0"
AEROBIC, ANAEROBIC = "aerobic", "anaerobic"
VESSEL_TYPES = {"stirred-tank": "Stirred tank", "bubble-column": "Bubble column"}
OXYGEN_BASES = ("peak", "batch-average")
# The unit strings a simulation's states and uptake come in (§3.1's shape).
CONC_UNITS = ("g L⁻¹", "g L-1", "g/L")
OUR_UNITS = ("g O2 L⁻¹ h⁻¹", "g O₂ L⁻¹ h⁻¹", "g O2 L-1 h-1", "g O₂ L-1 h-1", "g O2/L/h")
OUR_UNIT = "g O₂ L⁻¹ h⁻¹"
# The reaction's oxygen counts as unscaled within the float's own rounding.
UNSCALED = 1e-12
# A simulation's last hour counts as its harvest hour within the float's own
# rounding; past it, the run went on after the sugar ran out (§4.2).
HARVEST_EPS = 1e-9
# BioSTEAM's word for each vessel type, and the request's word for each.
TYPE_OF_DESIGN = {v: k for k, v in VESSEL_TYPES.items()}
# The heat cross-check's tolerance (§4.R, D7): the reaction's balanced
# oxygen and the oxygen the simulation took up agree within this share of
# the reaction's; beyond it a flag names both. A convention of this
# cross-check, named in every aerobic design's basis: a heat-per-oxygen rule
# is a rule of thumb, and a gap it could hide is not flagged.
OXYGEN_AGREE_RTOL = 0.1
TOLERANCE_INPUT = "oxygen agreement tolerance"


class VesselRefused(ValueError):
    """A design that cannot be made as asked, in words: a 422."""


class VesselNotFound(LookupError):
    """The simulation or fit named is not on file: a 404."""


def _installed(dist: str) -> str:
    from .proforma import _installed as installed

    return installed(dist)


def version() -> str:
    return f"{VERSION_WORDS} · biosteam {_installed('biosteam')} · thermosteam {_installed('thermosteam')}"


# ── what the simulation gives ──────────────────────────────────────────


def _by_key(values: Any) -> dict[str, Any]:
    """A list of ParameterValue-shaped dicts (or a plain dict) by key."""
    if isinstance(values, dict):
        return {k: (v.get("value") if isinstance(v, dict) else v) for k, v in values.items()}
    out = {}
    for v in values or []:
        if isinstance(v, dict) and "key" in v:
            out[v["key"]] = v.get("value")
    return out


def _number(x: Any, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise VesselRefused(f"the simulation holds no number for {what}")
    return float(x)


def simulation_inputs(art: Artifact) -> dict[str, Any]:
    """What a vessel design reads from one kept `fermos.simulation` artifact,
    in one place (§3.1's output shape: `family`, `start`, `series`, `our`,
    `end`, `harvestH`, `finalTitre`, `aerobic`): the start and end of the
    batch in g L⁻¹, the glucose used and the cells and ethanol made, the
    simulated oxygen uptake over time, the hour of harvest."""
    if art.tool != SIMULATION:
        raise VesselRefused(f"artifact {art.id} is a {art.tool} artifact, not a fermOS simulation ({SIMULATION})")
    o = art.output or {}
    family = str(o.get("family") or "")
    if family not in DESIGNABLE:
        raise VesselRefused(f"simulation {art.id} is of family {family or 'unnamed'}; a vessel is designed here for a "
                            f"batch on glucose ({', '.join(DESIGNABLE)}): a fed-batch's feed and a chemostat's flow "
                            "are not designed yet")
    product = (o.get("product") or next((i.value for i in art.inputs if i.name == "product"), None))
    if product not in (None, "", "ethanol"):
        raise VesselRefused(f"simulation {art.id} makes {product}; the vessel is built on the yeast program's "
                            "chemicals, whose product is ethanol")
    # §8.R (findings 6, 13): the vessel is built on the yeast program's
    # chemicals, so it says what it took the simulation's cells and product
    # to be, and refuses a strain of another organism.
    assumed: list[dict[str, str]] = []
    strain = (o.get("strain") or next((i.value for i in art.inputs if i.name == "strain"), None))
    organism = _organism_read(art.id, str(strain) if strain else None)
    if organism is not None:
        assumed.append({"name": "cells read as", "value": "Yeast", "note": organism})
    if not product:
        assumed.append({"name": "product read as", "value": "ethanol", "note": (
            f"simulation {art.id} names no product: its product state is read as ethanol, the product of the yeast "
            "program's chemicals the vessel is built on")})
    sugar = (o.get("sugar") or next((i.value for i in art.inputs if i.name == "sugar"), None))
    if sugar not in (None, "", "glucose"):
        raise VesselRefused(f"simulation {art.id} runs on {sugar}; the vessel's reaction is on glucose")
    state_units = o.get("units") or {}
    for state in ("X", "S", "P"):
        u = state_units.get(state)
        if u is not None and u not in CONC_UNITS:
            raise VesselRefused(f"simulation {art.id} keeps {state} in {u}; the vessel reads g L⁻¹")
    start = _by_key(o.get("start"))
    end = o.get("end") or {}
    x0, s0 = _number(start.get("x0"), "the cells at the start (x0)"), _number(start.get("s0"), "the glucose at the start (s0)")
    p0 = float(start.get("p0") or 0.0)
    harvest = _number(o.get("harvestH", end.get("t")), "the hour of harvest (harvestH)")
    our = o.get("our") or {}
    t, value = list(our.get("t") or []), list(our.get("value") or [])
    unit = our.get("unit")
    if unit is not None and unit not in OUR_UNITS:
        raise VesselRefused(f"simulation {art.id} keeps its oxygen uptake in {unit}; the vessel reads {OUR_UNIT}")
    if len(t) != len(value):
        raise VesselRefused(f"simulation {art.id}'s oxygen uptake has {len(value)} values at {len(t)} hours")
    end_t = end.get("t")
    notes: list[str] = []
    if _past_harvest(end_t, harvest):
        # §3.1's `end` is the run's last hour; a run set to go on past the
        # hour its sugar runs out is harvested at that hour (`harvestH`), so
        # the broth is read there, from the series the artifact keeps
        # (fermos.harvest, the read pureOS's inlet makes too: OF-BLD-020
        # §6.2, never integrated again), and the uptake is the batch's up to
        # it (OF-BLD-020 §4.2, reconciled with the real simulation).
        from . import fermos

        read = fermos.harvest(art)
        state = {x.state: x.value for x in read.states}
        X, S, P = (_number(state.get(k), f"{k} at harvest") for k in ("X", "S", "P"))
        keep = [i for i, h in enumerate(t) if float(h) <= harvest * (1 + HARVEST_EPS)]
        t, value = [t[i] for i in keep], [value[i] for i in keep]
        notes.append(f"the simulation runs on to {float(end_t):.4g} h; the vessel reads its broth at harvest, "
                     f"{harvest:.4g} h, the hour its sugar runs out, and its oxygen uptake up to that hour")
        if not read.exact:
            notes.append(f"its broth at harvest is {read.read}")
    else:
        X, S, P = (_number(end.get(k), f"{k} at harvest") for k in ("X", "S", "P"))
    # The peak the simulation states, read on its solver's own steps (§3.1),
    # kept when it falls at or before harvest (§4.R, finding 11).
    stated, stated_h = our.get("peak"), our.get("peakH")
    our_peak = None
    if isinstance(stated, (int, float)) and not isinstance(stated, bool) and math.isfinite(float(stated)) and stated > 0:
        if not (isinstance(stated_h, (int, float)) and _past_harvest(stated_h, harvest)):
            our_peak = {"value": float(stated), "h": float(stated_h) if isinstance(stated_h, (int, float)) else None}
    return {
        "id": art.id, "tool": art.tool, "family": family, "aerobic": bool(o.get("aerobic")),
        "start": {"x0": x0, "s0": s0, "p0": p0}, "end": {"X": X, "S": S, "P": P},
        "used": s0 - S, "made": {"cells": X - x0, "ethanol": P - p0},
        "harvestH": harvest, "finalTitre": float(o.get("finalTitre", P)),
        "our": {"t": [float(x) for x in t], "value": [float(x) for x in value]},
        "ourPeak": our_peak,
        "readNotes": notes + [a["note"] for a in assumed],
        "assumed": assumed,
    }


def _organism_read(aid: str, strain: str | None) -> str | None:
    """Words saying the simulation's cells are read as the yeast program's
    Yeast when that is an assumption (no strain named, or one whose species
    cannot be read here), None when its strain is of the program's species;
    a strain of another species is refused in words (§8.R, finding 6)."""
    from . import module_stores, proforma

    labels, species_of_program = proforma._strain_labels()
    yeast = species_of_program.get(YEAST_PROGRAM)
    if not strain:
        return (f"simulation {aid} names no strain: its cells are read as yeast (thermosteam's Yeast), the cells of the "
                "yeast program's chemicals the vessel is built on")
    label = labels.get(strain, strain)
    species = module_stores.species_of(label)
    if species and yeast and species != yeast:
        raise VesselRefused(f"simulation {aid} is of {label}, not of the yeast program's organism ({yeast}): the vessel "
                            "is built on the yeast program's chemicals, whose cells are thermosteam's Yeast, so it "
                            "designs no vessel for another organism's cells")
    if species and yeast:
        return None
    return (f"simulation {aid} is of {label}, whose species the service cannot read here: its cells are read as yeast "
            "(thermosteam's Yeast), the cells of the yeast program's chemicals the vessel is built on")


def _past_harvest(end_t: Any, harvest: float) -> bool:
    """Whether the run's last hour lies past its harvest hour, beyond the
    float's own rounding (`HARVEST_EPS`)."""
    if isinstance(end_t, bool) or not isinstance(end_t, (int, float)) or not math.isfinite(float(end_t)):
        return False
    return float(end_t) > harvest * (1 + HARVEST_EPS) + HARVEST_EPS


def fit_inputs(art: Artifact) -> dict[str, Any]:
    """What a vessel design reads from a kept kinetic fit or forecast, through
    `proforma.fit_info` (OF-BLD-019 §5.1): the titre, the yield and the batch
    time, as the ethanol flowsheet takes them. A fit gives no cells and no
    oxygen uptake, so its vessel is the anaerobic one; the glucose fed is
    what the titre over the yield used (all of it), and none is carried in."""
    from . import proforma

    if art.tool not in FIT_TOOLS:
        raise VesselRefused(f"artifact {art.id} is a {art.tool} artifact, not a kinetic fit or forecast")
    info = proforma.fit_info(art, FIT_FLOWSHEET)
    if info.refused:
        raise VesselRefused(f"fit {art.id} gives no vessel: {info.refused}")
    feeds = {f.key: f for f in info.feeds}
    for key in ("titre", "yield"):
        f = feeds.get(key)
        if f is None or f.refused or f.value is None:
            raise VesselRefused(f"fit {art.id} gives no {key}: {f.refused if f else 'it is not read'}")
    if info.batchTimeH is None:
        why = next((f.refused for f in info.feeds if f.key == "productivity" and f.refused), None)
        raise VesselRefused(f"fit {art.id} gives no batch time" + (f": {why}" if why else ""))
    titre, yld = float(feeds["titre"].value), float(feeds["yield"].value)
    if not (titre > 0 and yld > 0):
        raise VesselRefused(f"fit {art.id}'s titre and yield must both be above none")
    used = titre / yld
    return {
        "id": art.id, "tool": art.tool, "family": None, "aerobic": False,
        "start": {"x0": 0.0, "s0": used, "p0": 0.0}, "end": {"X": 0.0, "S": 0.0, "P": titre},
        "used": used, "made": {"cells": 0.0, "ethanol": titre}, "harvestH": float(info.batchTimeH),
        "finalTitre": titre, "our": {"t": [], "value": []},
        "fitNotes": [f"from {art.tool} {art.id}: the titre ({titre:.4g} g L⁻¹) and the yield ({yld:.4g} g g⁻¹) its "
                     "forecast gives, and the hour its median sugar runs out as the batch time; a fit gives no cells, "
                     "so none are in the broth, and the glucose fed is what the titre over the yield used", *info.flags],
    }


def _source_of(aid: str, include_archived: bool = True) -> tuple[Artifact, dict[str, Any]]:
    from . import artifacts

    try:
        art = artifacts.get(aid)
    except artifacts.ArtifactNotFound:
        raise VesselNotFound(f"no artifact {aid!r} is on file here: a vessel is designed for a fermOS simulation "
                             "(fermOS → Simulate keeps one) or, anaerobic, a kinetic fit or forecast") from None
    if not include_archived:
        from . import module_stores, programs

        try:
            program = module_stores.artifact_program(art)
            if programs.hides(program, False):
                raise VesselRefused(f"artifact {aid} belongs to the archived program {program}; turn on Show archived "
                                    "programs and examples in Settings → Programs to design for it")
        except FileNotFoundError:
            pass
    if art.tool == SIMULATION:
        return art, simulation_inputs(art)
    if art.tool in FIT_TOOLS:
        return art, fit_inputs(art)
    raise VesselRefused(f"artifact {aid} is a {art.tool} artifact; a vessel is designed for a fermOS simulation "
                        f"({SIMULATION}) or, anaerobic, a kinetic fit or forecast")


def oxygen_uptake(src: dict[str, Any]) -> tuple[float | None, float | None]:
    """The simulation's peak uptake and its average over the batch (the
    trapezoid integral over the hours it was kept, over their span), in
    the simulation's unit; None without a series. The peak is the one the
    simulation states on its solver's steps (`our.peak`) when it states one
    at or before harvest, else, or when its display grid holds a higher
    one, the grid's (§4.R, finding 11)."""
    t, y = src["our"]["t"], src["our"]["value"]
    if len(t) < 2:
        return None, None
    area = sum((t[i + 1] - t[i]) * (y[i] + y[i + 1]) / 2 for i in range(len(t) - 1))
    span = t[-1] - t[0]
    stated = (src.get("ourPeak") or {}).get("value")
    peak = max(y) if stated is None else max(stated, max(y))
    return peak, (area / span if span > 0 else None)


# ── the worker's answer, read once ─────────────────────────────────────

_SPECS: dict[str, dict[str, Any]] = {}
_SPECS_LOCK = threading.Lock()


def worker_specs(kind: str) -> dict[str, Any]:
    """The vessel class's parameters and defaults as BioSTEAM states them,
    from the worker's `vessel_specs`, kept for this process's life (they are
    the installed library's, which does not change under it)."""
    from . import proforma

    with _SPECS_LOCK:
        if kind not in _SPECS:
            _SPECS[kind] = proforma.call("vessel_specs", {"kind": kind})
        return _SPECS[kind]


# ── the declarations (Appendix 2 §C) ───────────────────────────────────

_POSITIVE = "a physical limit: {what} is above none"
_SHARE = "a physical limit: a share lies between none and the whole"
_WORDS = "a choice of words: it has no bounds"


class Decl:
    def __init__(self, key: str, label: str, symbol: str, gloss: str, dimension: str, unit: str, group: str,
                 rule: list[str], bounds: tuple[float | None, float | None, str], *, kinds: tuple[str, ...] = (AEROBIC, ANAEROBIC),
                 choice: bool = False, note: str | None = None, convention: Any = None, step: float | None = None) -> None:
        self.key, self.label, self.symbol, self.gloss = key, label, symbol, gloss
        self.dimension, self.unit, self.group, self.rule = dimension, unit, group, rule
        self.min, self.max, self.reason = bounds
        self.kinds, self.choice, self.note, self.convention, self.step = kinds, choice, note, convention, step


AER = (AEROBIC,)
DEFAULT = ["assumption", "library-default"]
DECLARED: tuple[Decl, ...] = (
    # Scale
    Decl("plant_scale", "Plant scale", "", "the product the plant makes in a year, which with the titre at harvest sets "
         "how much broth the vessels take", "mass", "t yr⁻¹", "Scale", ["assumption"],
         (0, None, _POSITIVE.format(what="a plant's yearly output")),
         note="One of plant_scale and batch_volume is needed. A plant scale runs the year on the corn plant's TEA "
              "operating hours, read from biorefineries.corn."),
    Decl("batch_volume", "Batch volume", "", "one vessel's working volume per batch: a design of one vessel, its broth "
         "fed over its cycle", "volume", "m³", "Scale", ["assumption"], (0, None, _POSITIVE.format(what="a volume")),
         kinds=AER, note="One of plant_scale and batch_volume is needed. One vessel needs a loading time: BioSTEAM "
                         "sizes a single vessel's schedule with it."),
    # Vessel
    Decl("design", "Vessel type", "", "whether the aerated vessel is a stirred tank, whose agitator BioSTEAM sizes and "
         "costs, or a bubble column, with none; it chooses the kLa correlation BioSTEAM computes with", "choice", "",
         "Vessel", ["assumption", "convention", "library-default"], (None, None, _WORDS), kinds=AER, choice=True,
         note="BioSTEAM's own name for it is design. A person's choice here is a named assumption; a request that "
              "names the vessel type (fermos_vessel's vesselType) is a convention of that request, and the two must "
              "agree. Changing it changes the kLa correlations offered and whether an agitator is costed."),
    Decl("V_max", "Largest vessel", "Vmax", "the largest single vessel BioSTEAM may use; it adds vessels rather than "
         "exceed it", "volume", "m³", "Vessel", DEFAULT, (0, None, _POSITIVE.format(what="a vessel's volume")),
         note="Give N or V_max, not both. The NREL vessel has no default of its own: BioSTEAM's anaerobic bioreactor's, "
              "as the ethanol flowsheet passes it. A batch volume designs one vessel, which V_max does not bound: its "
              "basis names no V_max, and a V_max typed beside one is refused."),
    Decl("N", "Number of vessels", "N", "how many vessels share the broth; unset, BioSTEAM finds it from the largest "
         "vessel", "count", "", "Vessel", DEFAULT,
         (1, None, "a physical limit: a design has at least one vessel, a whole number of them (a class that refuses "
                   "more, as the NREL vessel does, raises the bound in its own scope, with its own words)"), step=1,
         note="None by default: BioSTEAM finds the number from V_max. Give N or V_max, not both. A whole number; one "
              "aerated vessel at a plant scale needs a loading time."),
    Decl("V_wf", "Working volume fraction", "V_wf", "the share of each vessel the broth fills", "fraction", "",
         "Vessel", DEFAULT, (0, 1, _SHARE)),
    Decl("length_to_diameter", "Length to diameter", "L/D", "the vessel's height over its width", "ratio", "",
         "Vessel", DEFAULT, (0, None, _POSITIVE.format(what="a vessel's aspect ratio")), kinds=AER),
    Decl("vessel_material", "Vessel material", "", "what the pressure vessel is made of, which sets its cost factor",
         "choice", "", "Vessel", DEFAULT, (None, None, _WORDS), kinds=AER, choice=True),
    Decl("vessel_type", "Vessel orientation", "", "whether the pressure vessel stands vertical or lies horizontal "
         "(BioSTEAM's vessel_type; the stirred tank or bubble column is the vessel type chosen beside the panel)",
         "choice", "", "Vessel", DEFAULT, (None, None, _WORDS), kinds=AER, choice=True),
    # Schedule
    Decl("tau", "Reacting time", "τ", "the hours each batch reacts: the simulation's harvest hour", "time", "h",
         "Schedule", ["simulation", "artifact", "assumption"], (0, None, _POSITIVE.format(what="a batch's time"))),
    Decl("tau_0", "Cleaning and unloading time", "τ₀", "the hours between batches to empty and clean a vessel",
         "time", "h", "Schedule", DEFAULT, (0, None, "a physical limit: no negative time")),
    Decl("loading_time", "Loading time", "", "the hours to fill a vessel; unset, BioSTEAM takes each vessel to be "
         "filled all the time it is not reacting or being cleaned", "time", "h", "Schedule", DEFAULT,
         (0, None, "a physical limit: no negative time"),
         note="None by default: BioSTEAM assumes each vessel is constantly being filled."),
    # Aeration
    Decl("oxygen_basis", "Size the air for", "", "whether the air is sized for the simulation's peak oxygen uptake or "
         "its average over the batch", "choice", "", "Aeration", ["assumption", "convention"], (None, None, _WORDS),
         kinds=AER, choice=True, convention="peak",
         note="D7: the vessel must meet the culture's peak demand, so peak is the convention; batch-average is what "
              "BioSTEAM's class sizes for of itself, and the oxygen balance then shows where the peak falls short."),
    Decl("our_peak", "Peak oxygen uptake", "OURmax", "the highest oxygen uptake rate over the simulated batch",
         "oxygenUptake", "g O₂ L⁻¹ h⁻¹", "Aeration", ["simulation", "assumption"],
         (0, None, "a physical limit: no negative uptake"), kinds=AER),
    Decl("our_mean", "Average oxygen uptake", "OUR̄", "the oxygen the simulated batch takes up, over its hours",
         "oxygenUptake", "g O₂ L⁻¹ h⁻¹", "Aeration", ["simulation", "assumption"],
         (0, None, "a physical limit: no negative uptake"), kinds=AER),
    Decl("method", "kLa correlation", "kLa", "the correlation BioSTEAM computes the oxygen transfer coefficient with",
         "choice", "", "Aeration", ["assumption", "convention", "library-default"], (None, None, _WORDS), kinds=AER,
         choice=True),
    Decl("theta_O2", "Dissolved oxygen setpoint", "θ", "the dissolved oxygen held in the broth, as a share of "
         "saturation", "fraction", "", "Aeration", DEFAULT, (0, 1, _SHARE), kinds=AER),
    Decl("compressor_isentropic_efficiency", "Compressor efficiency", "η", "the air compressor's isentropic "
         "efficiency", "fraction", "", "Aeration", DEFAULT,
         (0, 1, "a physical limit: an efficiency lies between none and the ideal"), kinds=AER),
    # Agitation
    Decl("kW_per_m3", "Agitation power per volume", "P/V", "the agitator's power per working volume; solved, not set, "
         "while optimize_power is on", "powerPerVolume", "kW m⁻³", "Agitation", DEFAULT,
         (0, None, "a physical limit: no negative power"), kinds=AER),
    Decl("optimize_power", "Optimize power", "", "whether BioSTEAM solves the agitation and the air together for the "
         "least total power that meets the uptake", "choice", "", "Agitation", DEFAULT, (None, None, _WORDS),
         kinds=AER, choice=True),
    # Heat
    Decl("T", "Temperature", "T", "the broth's temperature", "temperature", "K", "Heat", DEFAULT,
         (0, None, "a physical limit: a temperature in kelvin is above none")),
    Decl("P", "Pressure", "P", "the vessel's operating pressure", "pressure", "Pa", "Heat", DEFAULT,
         (0, None, "a physical limit: an absolute pressure is above none")),
    Decl("heat_exchanger_configuration", "Heat exchanger", "", "how the vessel's heat is removed: a recirculation loop "
         "through an exchanger, or a jacket", "choice", "", "Heat", DEFAULT, (None, None, _WORDS), kinds=AER,
         choice=True),
    Decl("dT_hx_loop", "Loop temperature change", "ΔT", "the largest change in temperature across the recirculation "
         "loop's exchanger", "temperature", "K", "Heat", DEFAULT, (0, None, "a physical limit: no negative change"),
         kinds=AER),
    Decl("jacket_annular_diameter", "Jacket annular width", "", "the width of the jacket around the vessel, when "
         "jacketed", "length", "m", "Heat", DEFAULT, (0, None, _POSITIVE.format(what="a width")), kinds=AER),
    Decl("cooler_pressure_drop", "Air cooler pressure drop", "ΔP", "the pressure the air loses in its cooler",
         "pressure", "Pa", "Heat", DEFAULT, (0, None, "a physical limit: no negative drop"), kinds=AER),
    Decl("Q_O2_consumption", "Heat per oxygen consumed", "Q", "a forced heat per oxygen consumed; unset, BioSTEAM "
         "computes the duty from the heats of formation in and out", "molarEnergy", "kJ kmol⁻¹", "Heat", DEFAULT,
         (None, None, "no bound: a heat released is negative and BioSTEAM takes any value"), kinds=AER,
         note="None by default: the duty from the reaction's heats of formation. Not an oxygen demand: BioSTEAM "
              "sizes the air from the reaction's oxygen. Set, BioSTEAM's duty is it times the oxygen the vessel "
              "consumes, which is the reaction's scaled to the uptake the air is sized for; the heat line says so."),
)
# What each class takes that the panel does not offer, and why.
NOT_OFFERED = {
    "batch": "batch is held on: BioSTEAM's continuous mode divides the oxygen transfer by one hour where the batch "
             "time belongs (measured: a kLa off by the reacting time), and fermOS's simulations are batches",
    "adiabatic": "held off: the vessel's duty is what the design reads",
    "tau_phases": "BioSTEAM's own: the phases a residence time counts",
    "reactions": "built from what the simulation made",
    "kLa_kwargs": "BioSTEAM's correlation coefficients, its own",
    "Nmin": "stored by the NREL vessel and never used (measured: a large flow gave more vessels)",
    "Nmax": "stored by the NREL vessel and never used (measured: a large flow gave more vessels)",
}
GROUPS = ("Scale", "Vessel", "Schedule", "Aeration", "Agitation", "Heat")
# What the worker takes as a unit parameter; the vessel type travels as the
# design the request names, the rest are read before the worker runs.
DESIGN_KEYS = tuple(d.key for d in DECLARED if d.key not in (
    "plant_scale", "batch_volume", "tau", "oxygen_basis", "our_peak", "our_mean", "design"))


def _decls(kind: str) -> list[Decl]:
    return [d for d in DECLARED if kind in d.kinds]


def _spec(d: Decl, choices: list[str] | None = None, *, rule: list[str] | None = None, convention: Any = None,
          note: str | None = None, bounds: tuple[float | None, str] | None = None) -> ParameterSpec:
    low, reason = bounds if bounds is not None else (d.min, d.reason)
    return ParameterSpec(
        key=d.key, label=d.label, symbol=d.symbol, gloss=d.gloss, dimension=d.dimension, unit=d.unit,
        min=low, max=d.max, step=d.step, group=d.group, sourceRule=rule or d.rule, note=note or d.note,
        boundsReason=reason, choices=choices if d.choice else None,
        convention=convention if convention is not None else d.convention)


def _class_bounds(d: Decl, ws: dict[str, Any]) -> tuple[float | None, str] | None:
    """A lower bound the vessel class sets itself, read from its code by the
    worker (`refuses`: the value its setter raises at or below), with its
    reason (§4.R): N's least whole number above it, V_max's value itself
    (which the class refuses, said in the reason). None keeps the
    declaration's."""
    got = (ws.get("refuses") or {}).get(d.key)
    if got is None:
        return None
    x = float(got["atOrBelow"])
    if d.key == "N":
        return float(math.floor(x)) + 1, (f"a whole number of vessels: BioSTEAM's {ws['unitClass']} refuses N at or "
                                          f"below {x:g} ({got['from']})")
    return x, (f"BioSTEAM's {ws['unitClass']} refuses V_max at or below {x:g} {d.unit} ({got['from']}): a V_max "
               "above it")


def _held(kind: str, ws: dict[str, Any], overrides: Iterable[Override]) -> None:
    """What a person typed that the class cannot design, refused in words
    before the worker is asked (§4.R, findings 3, 4, 5, 8, 9): an N that is
    not a whole number or lies under the class's own minimum, a V_max at or
    under what the class refuses, one aerated vessel at a plant scale with
    no loading time, and a V_max beside a batch volume, which designs one
    vessel V_max does not bound."""
    typed = {o.key: o.value for o in overrides}
    num = {k: float(v) for k, v in typed.items()
           if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))}
    refuses = ws.get("refuses") or {}
    # §8.R (finding 14): the pairs a design refuses are refused here, where
    # the panel's resolve and the design both ask, never in the design alone.
    if "plant_scale" in num and "batch_volume" in num:
        raise VesselRefused("give plant_scale or batch_volume, not both: one sets how much broth the vessels take")
    if "N" in num and "V_max" in num:
        raise VesselRefused("give N or V_max, not both: BioSTEAM sizes by one of them")
    if "N" in num and "batch_volume" in num:
        raise VesselRefused("N does not apply to a batch volume: a batch volume names one vessel's working volume; leave "
                            "N to it, or give a plant scale")
    if "N" in num:
        n = num["N"]
        if not n.is_integer():
            raise VesselRefused(f"N is a number of vessels, a whole number; {n:g} is not: BioSTEAM would size and cost "
                                "that many vessels' worth (the aerated class) or round it up unsaid (the NREL vessel)")
        if "N" in refuses and n <= refuses["N"]["atOrBelow"]:
            x = refuses["N"]["atOrBelow"]
            raise VesselRefused(f"N {n:g}: BioSTEAM's {ws['unitClass']} refuses N at or below {x:g} ({refuses['N']['from']}); "
                                f"give {math.floor(x) + 1:g} or more, or leave N to it")
        if n < 1:
            raise VesselRefused(f"N {n:g}: a design has at least one vessel; give one or more, or leave N to BioSTEAM")
        if n == 1 and kind == AEROBIC and "loading_time" not in num and "batch_volume" not in num:
            raise VesselRefused("N 1: one aerated vessel at a plant scale needs a loading time: BioSTEAM sizes a single "
                                "vessel's schedule with it (without one it divides by zero); type one under Schedule")
    if "V_max" in num:
        v = num["V_max"]
        if "V_max" in refuses and v <= refuses["V_max"]["atOrBelow"]:
            x = refuses["V_max"]["atOrBelow"]
            raise VesselRefused(f"V_max {v:g} m³: BioSTEAM's {ws['unitClass']} refuses V_max at or below {x:g} m³ "
                                f"({refuses['V_max']['from']}); give a larger one, or leave V_max to it")
        if not v > 0:
            raise VesselRefused(f"V_max {v:g} m³: a vessel's volume is above none; give a larger one, or leave V_max to "
                                "BioSTEAM")
        if "batch_volume" in num:
            raise VesselRefused("V_max does not apply to a batch volume: a batch volume designs one vessel of that "
                                "working volume, which V_max does not bound; leave V_max to the class, or give a "
                                "plant scale")


def _static() -> Iterable[tuple[str, list[ParameterSpec]]]:
    """Every declaration, read with no worker (check:seed): each kind's specs
    as declared, a choice's offered words left to the worker."""
    for kind in (AEROBIC, ANAEROBIC):
        yield f"fermos vessel ({kind})", [_spec(d, [] if d.choice else None) for d in _decls(kind)]


# ── the scope ──────────────────────────────────────────────────────────


def _design_of(kind: str, vessel_type: str | None, ws: dict[str, Any]) -> str | None:
    if kind == ANAEROBIC:
        if vessel_type:
            raise VesselRefused("an anaerobic design is BioSTEAM's NREL batch fermenter; the vessel type chooses "
                                "between aerated designs (stirred tank or bubble column)")
        return None
    if vessel_type is None:
        return ws["defaultDesign"]
    if vessel_type not in VESSEL_TYPES:
        raise VesselRefused(f"a vessel type is {' or '.join(VESSEL_TYPES)}; {vessel_type!r} is neither")
    return VESSEL_TYPES[vessel_type]


def _model_source(ws: dict[str, Any], key: str, where: str) -> BasisSource:
    return BasisSource(kind="model", id=f"biosteam@{ws['biosteam']}",
                       note=f"{ws['unitClass']}'s own default for {key}, read from {where}")


def _choices(d: Decl, ws: dict[str, Any], design: str | None) -> list[str] | None:
    if not d.choice:
        return None
    if d.key == "oxygen_basis":
        return list(OXYGEN_BASES)
    if d.key == "design":
        return list(ws["designs"])
    if d.key == "method":
        return list(ws["designs"][design]["runs"])
    if d.key == "optimize_power":
        each = ws["designs"][design]
        return ["true", "false"] if each["method"] in each["solvesPower"] else ["false"]
    return list(ws["choices"][d.key])


def _method_note(ws: dict[str, Any], design: str) -> str:
    each = ws["designs"][design]
    idle = [m for m in each["registered"] if m not in each["runs"]]
    return (f"BioSTEAM {ws['biosteam']} runs {', '.join(each['runs'])} for a {design.lower()}"
            + (f"; it registers {', '.join(idle)} as well, which its {ws['unitClass']} does not implement on this "
               "BioSTEAM, so they are not offered" if idle else ""))


def _chosen_type(vessel_type: str | None, overrides: Iterable[Override]) -> tuple[str | None, str]:
    """The vessel type a design asks for, and who asked: a person's
    override of `design` in the panel ("override"), the request's
    `vesselType` ("request"), or neither ("default"). The two must agree."""
    chosen = next((o for o in overrides if o.key == "design"), None)
    if chosen is None:
        return vessel_type, ("request" if vessel_type else "default")
    word = TYPE_OF_DESIGN.get(chosen.value) if isinstance(chosen.value, str) else None
    if word is None:
        raise VesselRefused(f"design is one of {', '.join(VESSEL_TYPES.values())}; {chosen.value!r} is not")
    if vessel_type and vessel_type != word:
        raise VesselRefused(f"the vessel type asked for ({vessel_type}) and the one {chosen.by or 'a person'} chose in the "
                            f"panel ({chosen.value}) differ: send one, or the two alike")
    return word, "override"


def _kla_method(kind: str, design: str | None, ws: dict[str, Any], kla_method: str | None,
                overrides: Iterable[Override]) -> str | None:
    """The kLa correlation a request names (fermos_vessel's klaMethod), held
    to the ones BioSTEAM's class runs for the design; refused in words."""
    if not kla_method:
        return None
    if kind != AEROBIC or design is None:
        raise VesselRefused("an anaerobic vessel takes no air, so it has no kLa correlation to name")
    each = ws["designs"][design]
    if kla_method not in each["runs"]:
        idle = [m for m in each["registered"] if m not in each["runs"]]
        raise VesselRefused(f"BioSTEAM {ws['biosteam']} runs {', '.join(each['runs'])} for a {design.lower()}; "
                            f"{kla_method!r} is not one" + (f" ({', '.join(idle)} are registered and not implemented "
                                                            "by its class)" if idle else ""))
    typed = next((o for o in overrides if o.key == "method"), None)
    if typed is not None and typed.value != kla_method:
        raise VesselRefused(f"the kLa correlation asked for ({kla_method}) and the one {typed.by or 'a person'} chose "
                            f"in the panel ({typed.value}) differ: send one, or the two alike")
    return kla_method


def provided(aid: str, vessel_type: str | None, *, include_archived: bool = True, overrides: Iterable[Override] = (),
             kla_method: str | None = None) -> tuple[params.Provided, dict]:
    """The scope's specs and the candidates for each, and what was read.
    The vessel type is the request's `vesselType` or a person's override
    of `design` (they must agree); `kla_method` is a request's named kLa
    correlation, a convention of that request."""
    overrides = list(overrides)
    art, src = _source_of(aid, include_archived)
    kind = AEROBIC if src["aerobic"] else ANAEROBIC
    ws = worker_specs(kind)
    vessel_type, design_from = _chosen_type(vessel_type, overrides)
    design = _design_of(kind, vessel_type, ws)
    named_method = _kla_method(kind, design, ws, kla_method, overrides)
    _held(kind, ws, overrides)
    defaults = ws["parameters"]
    specs: list[ParameterSpec] = []
    sources: dict[str, dict[str, ParameterValue | None]] = {}
    peak, mean = oxygen_uptake(src)
    for d in _decls(kind):
        rule, convention, note = d.rule, None, d.note
        cands: dict[str, ParameterValue | None] = {}
        if d.key == "tau":
            entry = "simulation" if art.tool == SIMULATION else "artifact"
            what = "the simulation's harvest hour" if entry == "simulation" else "the fit's batch time: the hour its forecast's median sugar runs out"
            cands[entry] = ParameterValue(key=d.key, value=src["harvestH"], origin=entry, detail=what,
                                          source=BasisSource(kind="artifact", id=art.id, note=what))
        elif d.key in ("our_peak", "our_mean"):
            v = peak if d.key == "our_peak" else mean
            if v is not None:
                stated = src.get("ourPeak")
                at = f", at {stated['h']:.4g} h" if stated and stated.get("h") is not None else ""
                what = (("the peak oxygen uptake the simulation states, read on its solver's own steps (its our.peak"
                         f"{at}), which its display grid lies under" if stated and v == stated["value"] else
                         "the highest oxygen uptake on the simulation's time course (it states no peak of its own at or "
                         "before harvest above it)") if d.key == "our_peak" else
                        "the simulated oxygen uptake's average over the batch (the trapezoid integral over its span)")
                cands["simulation"] = ParameterValue(key=d.key, value=v, origin="simulation", detail=what,
                                                     source=BasisSource(kind="artifact", id=art.id, note=what))
        elif d.key == "design":
            got = defaults.get("design") or {}
            where = got.get("from") or f"{ws['unitClass']}'s own default design"
            cands["library-default"] = ParameterValue(key=d.key, value=ws["defaultDesign"], origin="library-default",
                                                      libraryDefault=ws["defaultDesign"],
                                                      source=_model_source(ws, d.key, where),
                                                      detail=f"{ws['unitClass']}'s default design, from {where}")
            if design_from == "request":
                what = "the vessel type the request chose (vesselType)"
                cands["convention"] = ParameterValue(key=d.key, value=design, origin="convention", detail=what,
                                                     source=BasisSource(kind="convention", note=what))
        elif d.key == "kW_per_m3" and design == "Bubble column":
            rule, convention = ["assumption", "convention"], 0.0
            note = ("A bubble column has no agitator: BioSTEAM costs one unless the power per volume is zero, so zero is "
                    "the convention for this design.")
        elif d.key in ("method", "optimize_power") and design is not None:
            each = ws["designs"][design]
            value = each[d.key] if d.key == "method" else ("true" if each["optimize_power"] else "false")
            where = f"a {ws['unitClass']} built as a {design.lower()} with nothing else set"
            cands["library-default"] = ParameterValue(key=d.key, value=value, origin="library-default",
                                                      libraryDefault=value, source=_model_source(ws, d.key, where),
                                                      detail=f"BioSTEAM's default for a {design.lower()}")
            if d.key == "method":
                note = _method_note(ws, design)
                if named_method:
                    what = "the kLa correlation the request named (klaMethod)"
                    cands["convention"] = ParameterValue(key=d.key, value=named_method, origin="convention",
                                                         detail=what, source=BasisSource(kind="convention", note=what))
        elif "library-default" in d.rule:
            got = defaults.get(d.key)
            if got is None:
                raise VesselRefused(f"BioSTEAM's {ws['unitClass']} names no parameter {d.key} on this install")
            v = got["default"]
            cands["library-default"] = ParameterValue(key=d.key, value=v, origin="library-default", libraryDefault=v,
                                                      source=_model_source(ws, d.key, got["from"]),
                                                      detail=f"{ws['unitClass']}'s default, from {got['from']}")
        specs.append(_spec(d, _choices(d, ws, design), rule=rule, convention=convention, note=note,
                           bounds=_class_bounds(d, ws)))
        sources[d.key] = cands
    words = "a simulation" if art.tool == SIMULATION else f"a {art.tool}"
    title = f"Vessel for {words} {art.id}: {ws['unitClass']}" + (f", {design.lower()}" if design else "")
    notes = [
        ("One of plant_scale and batch_volume is needed: a plant scale sizes the vessels for a year's product over the "
         "corn TEA's operating hours; a batch volume designs one vessel of that working volume (with a loading time)."
         if kind == AEROBIC else
         "A plant scale is needed: it sizes the vessels for a year's product over the corn TEA's operating hours. "
         "BioSTEAM's NREL batch fermenter sizes two vessels or more, so a batch volume of one vessel is not offered."),
        f"Each default is {ws['unitClass']}'s own in BioSTEAM {ws['biosteam']}, read from its code at import in the "
        "worker; a value a person types is a named assumption, and the design's basis names it.",
        "Not offered: " + "; ".join(f"{k}, {v}" for k, v in NOT_OFFERED.items() if k in defaults) + ".",
    ]
    if kind == AEROBIC:
        notes.append("The air flow, its vvm and the gas velocity are BioSTEAM's to solve, and are read after the design.")
    if art.tool != SIMULATION:
        notes += src.get("fitNotes", [])
    notes += src.get("readNotes", [])
    return params.Provided(title=title, specs=specs, sources=sources, notes=notes), {
        "artifact": art, "source": src, "kind": kind, "design": design, "worker": ws, "designFrom": design_from}


def _provider(ids: tuple[str, ...], req: ParamResolveRequest) -> params.Provided:
    (aid,) = ids
    try:
        got, _ = provided(aid, req.vesselType, overrides=req.overrides)
    except VesselNotFound as e:
        raise params.ScopeUnknown(str(e)) from None
    except VesselRefused as e:
        raise params.ParamRefused(str(e)) from None
    return got


params.register("fermos-vessel", _provider, _static)


def scope(aid: str, vessel_type: str | None = None):
    """GET /api/fermos/vessel/specs: the ParamScope for a design."""
    return params.scope(params.scope_name("fermos-vessel", aid), ParamResolveRequest(vesselType=vessel_type))


# ── the design ─────────────────────────────────────────────────────────


def _bool(v: Any) -> Any:
    return {"true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def basis_inputs(req: VesselRequest) -> tuple[list[BasisInput], list[ParameterSpec], list[ParameterValue], dict]:
    """The design's basis, its specs and resolved values, and what was read.
    Refused in words before anything runs: a scale missing or both given, N
    and V_max both given, an override that cannot stand."""
    from . import proforma

    named = [x for x in (req.simulation, req.fit) if x]
    if len(named) != 1:
        raise VesselRefused("a vessel is designed for one simulation or one fit: name exactly one")
    aid = named[0]
    got, read = provided(aid, req.vesselType, include_archived=req.includeArchived, overrides=req.overrides,
                         kla_method=req.klaMethod)
    art, kind = read["artifact"], read["kind"]
    if req.fit and art.tool == SIMULATION:
        raise VesselRefused(f"artifact {aid} is a simulation: name it as the simulation, not the fit")
    if req.simulation and art.tool != SIMULATION:
        raise VesselRefused(f"artifact {aid} is a {art.tool} artifact; name it as the fit, not the simulation")
    if req.fit and kind != ANAEROBIC:  # fit_inputs reads every fit as anaerobic; held here in words all the same
        raise VesselRefused("a fit gives no oxygen uptake, so it designs the anaerobic vessel only")
    scope_id = params.scope_name("fermos-vessel", aid)
    stray = sorted({o.scope for o in req.overrides if o.scope != scope_id})
    if stray:
        raise VesselRefused(f"an override names the scope it changes, and these were sent to {scope_id}: {', '.join(stray)}")
    try:
        values = params.resolve(got.specs, got.sources, req.overrides)
    except params.ParamRefused as e:
        raise VesselRefused(str(e)) from None
    by = {v.key: v for v in values}
    has = {k for k, v in by.items() if v.value is not None}
    if not ({"plant_scale", "batch_volume"} & has):
        raise VesselRefused("a vessel design needs plant_scale (tonnes of product a year) or batch_volume (one vessel's "
                            "working volume, m³), a named person's assumption; neither was given")
    # Both scales, and N beside V_max, are refused by `_held`, which
    # `provided` ran above for the design and runs for the panel alike.
    waiting = [v.key for v in values if v.origin == "waiting" and v.key not in ("plant_scale", "batch_volume")]
    if waiting:
        raise VesselRefused("these design parameters wait for a source: " + ", ".join(waiting))
    ws = read["worker"]
    lib = BasisSource(kind="model", id=f"biosteam@{ws['biosteam']}")
    inputs = [
        BasisInput(name="simulation" if art.tool == SIMULATION else "fit", value=art.id, unit="",
                   source=BasisSource(kind="artifact", id=art.id, note=f"the {art.tool} the vessel is designed for")),
        BasisInput(name="vessel class", value=ws["unitClass"], unit="", source=lib.model_copy(update={
            "note": f"BioSTEAM's {ws['unitClass']}, sized and costed by BioSTEAM"})),
        BasisInput(name="chemicals", value=ws["chemicals"], unit="", source=BasisSource(
            kind="model", id=f"biorefineries@{ws['biorefineries']}",
            note="the yeast program's chemicals, as the ethanol flowsheet makes them")),
        # What the vessel took the simulation's cells or product to be (§8.R).
        *(BasisInput(name=a["name"], value=a["value"], unit="", source=BasisSource(kind="convention", note=a["note"]))
          for a in read["source"].get("assumed", [])),
        proforma.utility_input(),
        BasisInput(name="unit id", value="R1", unit="", source=BasisSource(
            kind="convention", note="the BioSTEAM unit id the design is built under")),
    ]
    if read["design"] is not None:
        how = {"request": "the vessel type the request chose",
               "override": "the vessel type a person chose in the panel, named as design",
               "default": f"BioSTEAM's own default design for {ws['unitClass']}"}[read["designFrom"]]
        inputs.append(BasisInput(name="vessel type", value=read["design"], unit="", source=BasisSource(
            kind="convention", note=how)))
    if "plant_scale" in has:
        inputs.append(BasisInput(name="operating hours", value=ws["operatingHours"], unit="h yr⁻¹", source=BasisSource(
            kind="model", id=f"biorefineries@{ws['biorefineries']}", note=ws["operatingHoursFrom"])))
    if kind == AEROBIC:
        inputs.append(BasisInput(name="heat per oxygen consumed", value=ws["heatPerO2"], unit="kJ kmol⁻¹",
                                 source=BasisSource(kind="model", id=f"biorefineries@{ws['biorefineries']}",
                                                    note=ws["heatPerO2From"] + " (the cross-check, labelled a convention)")))
        inputs.append(BasisInput(name=TOLERANCE_INPUT, value=OXYGEN_AGREE_RTOL, unit="", source=BasisSource(
            kind="convention", note=("the share of the reaction's balanced oxygen within which the oxygen the simulation "
                                     "took up agrees with it; beyond it the design flags both (the heat cross-check's "
                                     "tolerance, a convention: a heat-per-oxygen rule is a rule of thumb)"))))
    drop = set()
    if "batch_volume" in has:
        # One vessel of the batch volume: V_max does not bound it, so the
        # basis names none (§4.R, finding 5); the design's flags say so.
        drop = {"V_max", "V_max low", "V_max high"}
    inputs += [i for i in params.basis_inputs(got.specs, values) if i.name not in drop]
    return inputs, got.specs, values, read


def _named(inputs: list[BasisInput], name: str) -> BasisInput | None:
    return next((i for i in inputs if i.name == name), None)


def worker_request(inputs: list[BasisInput]) -> tuple[dict[str, Any], Artifact, dict[str, Any], str]:
    """The worker's `vessel_design` request from a design's basis alone, with
    the artifact it names, what was read from it, and the kind of vessel."""
    from . import artifacts

    which = _named(inputs, "simulation") or _named(inputs, "fit")
    art = artifacts.get(str(which.value))
    src = simulation_inputs(art) if art.tool == SIMULATION else fit_inputs(art)
    kind = AEROBIC if src["aerobic"] else ANAEROBIC
    given = {i.name: i for i in inputs}
    worker_params = {k: _bool(given[k].value) for k in DESIGN_KEYS
                     if k in given and given[k].source.kind != "model"}
    design = _named(inputs, "vessel type")
    plant, batch = given.get("plant_scale"), given.get("batch_volume")
    spec: dict[str, Any] = {
        "kind": kind, "design": design.value if design is not None else None,
        "start": {"Glucose": src["start"]["s0"], "Yeast": src["start"]["x0"], "Ethanol": src["start"]["p0"]},
        "made": {"Yeast": src["made"]["cells"], "Ethanol": src["made"]["ethanol"]}, "used": src["used"],
        "tau": float(given["tau"].value),
        "scale": {"plantScale": float(plant.value) if plant else None, "batchVolume": float(batch.value) if batch else None,
                  "productTitre": src["finalTitre"]},
        "params": worker_params,
    }
    if kind == AEROBIC:
        oxygen_basis = str(given["oxygen_basis"].value) if "oxygen_basis" in given else OXYGEN_BASES[0]
        target = given.get("our_peak" if oxygen_basis == "peak" else "our_mean")
        if target is None or not float(target.value) > 0:
            raise VesselRefused("the simulation takes up no oxygen to size the air for, though it is aerobic")
        spec.update(our=src["our"], ourTarget=float(target.value), oxygenBasis=oxygen_basis,
                    ourPeak=(src.get("ourPeak") or {}).get("value"))
    return spec, art, src, kind


def _compute(inputs: list[BasisInput], seed: int | None) -> dict[str, Any]:
    """The design, from its basis alone: the simulation or fit it names, read
    from the store, and every parameter as the basis holds it. A value whose
    source is the class's own default is left to the class; every other one
    is passed. Pure, so a replay designs it again."""
    from . import proforma
    from .workers import WorkerError

    spec, art, src, kind = worker_request(inputs)
    oxygen_basis = spec.get("oxygenBasis")
    try:
        said = proforma.call("vessel_design", spec)
    except WorkerError as e:
        text = str(e)
        if text.startswith("Refused: "):
            raise VesselRefused(text.removeprefix("Refused: ")) from None
        raise
    flags = (list(said["reaction"].get("notes") or []) + list(src.get("fitNotes") or [])
             + list(src.get("readNotes") or []) + list(said.get("designNotes") or []))
    ox = said.get("oxygen")
    if ox is not None:
        if not ox["aerated"]:
            flags.append(_no_air_words(ox, oxygen_basis))
        if abs(ox["scale"] - 1) > UNSCALED and ox["aerated"]:
            flags.append(f"the reaction consumes {ox['scale']:.4g} times the oxygen its yields balance, so BioSTEAM sizes "
                         f"the air for the simulation's {oxygen_basis} uptake; the vessel's outlets carry that oxygen as "
                         "consumed, and the broth at harvest is the simulation's end state")
        if ox["short"]:
            spans = ", ".join(f"{a:.3g} to {b:.3g} h" for a, b in ox["short"])
            flags.append(f"the simulated oxygen uptake rises above what the vessel transfers from {spans}")
        tol = _named(inputs, TOLERANCE_INPUT)
        gap = _oxygen_gap(ox, float(tol.value) if tol is not None else None)
        if gap:
            flags.append(gap)
    flags += [f"BioSTEAM warned: {w}" for w in said.get("warnings") or []]
    heat = {**said["heat"], "unit": "kJ/hr", "dutyNote": _duty_words(said["heat"], ox, oxygen_basis, inputs, kind)}
    return {
        "parameters": [v.model_dump(mode="json") for v in _parameters(inputs, kind, art.id, art.tool)],
        "aerobic": kind == AEROBIC, "unitClass": said["unitClass"], "unitId": said["unitId"],
        "vesselType": next((k for k, v in VESSEL_TYPES.items() if v == spec["design"]), None),
        "source": art.id, "sourceTool": art.tool,
        "design": said["design"], "oxygen": ox,
        "oxygenNote": None if ox is not None else (
            "an anaerobic vessel takes no air: BioSTEAM's NREL batch fermenter has no gas inlet and no compressor, so "
            "there is no oxygen balance"),
        "heat": heat, "cost": said["cost"], "used": said["used"],
        "scale": said["scale"], "reaction": {k: v for k, v in said["reaction"].items() if k != "notes"},
        "designResults": said["designResults"], "auxiliaries": said["auxiliaries"],
        "coolingAgents": said["coolingAgents"], "utilitySettings": said["utilitySettings"],
        "flags": flags, "versions": said["versions"],
    }


def _no_air_words(ox: dict[str, Any], oxygen_basis: str | None) -> str:
    """Why a design has no air, in terms of the uptake it was sized for: the
    reaction scaled to the target is still at or under BioSTEAM's floor."""
    target, scaled, floor = ox.get("targetUptake"), ox.get("scaledO2KmolPerH"), ox.get("floorKmolPerH")
    if target is None or scaled is None:
        return ("BioSTEAM designed no aeration: the reaction's oxygen uptake is at or below the floor its "
                "AeratedBioreactor aerates from, so every hour the simulation takes up oxygen is short")
    return (f"BioSTEAM designed no aeration: scaled to the simulation's {oxygen_basis} uptake, {target:.4g} mmol L⁻¹ h⁻¹ "
            f"per working volume, the reaction consumes {scaled:.4g} kmol/hr of oxygen over the plant"
            + (f", at or below the floor of {floor:.4g} kmol/hr its AeratedBioreactor aerates from (read from its code)"
               if floor is not None else ", at or below the floor its AeratedBioreactor aerates from")
            + "; so every hour the simulation takes up oxygen is short: a larger batch or plant scale is aerated")


def _oxygen_gap(ox: dict[str, Any], tol: float | None) -> str | None:
    """The flag when the reaction's balanced oxygen and the oxygen the
    simulation took up differ by more than the stated tolerance (§4.R, D7),
    naming both."""
    rxn, sim = ox.get("reactionO2KmolPerH"), ox.get("simulatedO2KmolPerH")
    if tol is None or rxn is None or sim is None or not rxn > 0 or abs(sim - rxn) <= tol * rxn:
        return None
    return (f"the reaction's yields balance {rxn:.4g} kmol/hr of oxygen and the simulation took up {sim:.4g} kmol/hr "
            f"over the batch ({sim / rxn:.3g} times as much), apart by more than {tol:g} of the reaction's, the "
            "stated tolerance: BioSTEAM's duty rests on the reaction (its heats of formation, or a forced heat per "
            "oxygen times the oxygen the scaled reaction consumes), the cross-check on what the simulation took up")


def _duty_words(heat: dict[str, Any], ox: dict[str, Any] | None, oxygen_basis: str | None,
                inputs: list[BasisInput], kind: str) -> str:
    """BioSTEAM's duty in words: how it was found (findings 2, 7, 13)."""
    if heat.get("method") == "forced-per-oxygen":
        q = _named(inputs, "Q_O2_consumption")
        who = (f"typed by {q.source.by}" if q is not None and q.source.by else "set") if q is not None else "set"
        value = f", {float(q.value):.4g} kJ/kmol," if q is not None else ""
        consumed = heat.get("consumedKmolPerH")
        scale = (ox or {}).get("scale", 1.0)
        scaled = (f"; that oxygen is the reaction's scaled ×{scale:.4g} to size the air for the simulation's "
                  f"{oxygen_basis} uptake, so this duty is the heat at that uptake, not the batch's on average"
                  if abs(scale - 1) > UNSCALED else "")
        return (f"forced: Q_O2_consumption{value} {who}, times the oxygen the vessel consumed"
                + (f", {consumed:.4g} kmol/hr" if consumed is not None else "")
                + f" (AeratedBioreactor._get_duty with a heat per oxygen set){scaled}")
    if kind == AEROBIC:
        return ("from the reaction's enthalpy and heats of formation, out less in (AeratedBioreactor._get_duty, with no "
                "heat per oxygen forced)")
    return ("from the reaction's enthalpy and heats of formation, out less in (the NREL fermenter's design result "
            "'Reactor duty', its Hnet)")


def _register() -> None:
    from . import artifacts

    artifacts.register(TOOL, version(), _compute)


def _register_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(TOOL, _register)


_register_lazy()


def _parameters(inputs: list[BasisInput], kind: str, source_id: str, source_tool: str) -> list[ParameterValue]:
    """Every design parameter of this kind as the basis holds it, each with
    its source (an override an assumption by the person, a class default the
    library's, the simulation's values the artifact's), BioSTEAM's own
    default beside it, and a value outside its bounds flagged. A default
    BioSTEAM leaves as None (the class decides at run time) is in no basis,
    and reads here as that default."""
    origin = {"assumption": "assumption", "model": "library-default", "convention": "convention"}
    ws = worker_specs(kind)
    given = {i.name: i for i in inputs}
    design = _named(inputs, "vessel type")
    out = []
    for d in _decls(kind):
        lib = _library_default(ws, d.key, design.value if design is not None else None)
        i = given.get(d.key)
        if i is None:
            if d.key in ("plant_scale", "batch_volume"):
                continue
            if d.key == "V_max" and "batch_volume" in given:
                out.append(ParameterValue(key=d.key, value=None, source=None, origin="library-default",
                                          libraryDefault=lib, detail=(
                                              "not used: a batch volume designs one vessel of that working volume, "
                                              "and V_max does not apply to it")))
                continue
            got = ws["parameters"].get(d.key) or {}
            out.append(ParameterValue(key=d.key, value=None, source=_model_source(ws, d.key, got.get("from", "its code")),
                                      origin="library-default", libraryDefault=lib,
                                      detail=f"{ws['unitClass']}'s default is None: the class decides at run time"))
            continue
        o = origin.get(i.source.kind) or ("simulation" if i.source.id == source_id and source_tool == SIMULATION
                                          else "artifact")
        low, high = given.get(f"{d.key} low"), given.get(f"{d.key} high")
        v = ParameterValue(key=d.key, value=i.value, low=float(low.value) if low else None,
                           high=float(high.value) if high else None, source=i.source, origin=o,
                           overriddenBy=i.source.by if o == "assumption" else None,
                           libraryDefault=lib, detail=i.source.note)
        v.outOfBounds = params.bounds_check(_spec(d, [] if d.choice else None, bounds=_class_bounds(d, ws)), v.value,
                                            v.low, v.high)
        out.append(v)
    return out


def _library_default(ws: dict[str, Any], key: str, design: str | None) -> Any:
    """BioSTEAM's own default for a parameter of the class and design built,
    as the scope serves it (§4.R, finding 10): the design's for the kLa
    method, optimize_power and kW_per_m3, the class's default design for
    `design`, else the class's."""
    each = (ws.get("designs") or {}).get(design) if design else None
    if each is not None and key in ("method", "kW_per_m3"):
        return each[key]
    if each is not None and key == "optimize_power":
        return "true" if each["optimize_power"] else "false"
    if key == "design":
        return ws.get("defaultDesign")
    return (ws["parameters"].get(key) or {}).get("default")


def output_of(art: Artifact) -> VesselDesign:
    if art.tool != TOOL:
        raise VesselRefused(f"artifact {art.id} is a {art.tool} artifact, not a vessel design")
    o = art.output
    fields = {k: o[k] for k in VesselDesign.model_fields if k in o}
    return VesselDesign.model_validate({**fields, "artifactId": art.id, "provenance": art.provenance,
                                        "createdAt": art.createdAt, "evidence": evidence(art)})


def design(req: VesselRequest) -> VesselDesign:
    """Design the vessel, or return the design kept for the same basis."""
    from . import artifacts

    inputs, _, _, _ = basis_inputs(req)
    art = artifacts.compute(TOOL, inputs, records_by_id={})
    return output_of(art)


def summary(a: Artifact) -> VesselSummary:
    """One kept design in a line: what `GET /api/fermos/vessels` lists and
    `fermos_read`'s `vessel` rows carry. Read, never computed."""
    o = a.output or {}
    dr = o.get("designResults") or {}
    return VesselSummary(
        artifactId=a.id, provenance=a.provenance, createdAt=a.createdAt, source=str(o.get("source") or ""),
        sourceTool=str(o.get("sourceTool") or ""), unitClass=str(o.get("unitClass") or ""),
        vesselType=o.get("vesselType"), vessels=dr.get("Number of reactors"), volume=dr.get("Reactor volume"),
        installed=(o.get("cost") or {}).get("installed"))


def designs(include_archived: bool = False) -> list[VesselSummary]:
    """GET /api/fermos/vessels: every kept vessel design, newest first; a
    read, which starts no simulator. A design for an archived program's
    simulation (`module_stores.artifact_program`, which follows the
    simulation it rests on) is left out unless asked (§8.R, finding 3)."""
    from . import artifacts, module_stores, programs

    out = []
    for a in artifacts.all_artifacts():
        if a.tool != TOOL:
            continue
        if not include_archived:
            try:
                if programs.hides(module_stores.artifact_program(a), False):
                    continue
            except FileNotFoundError:
                pass
        out.append(summary(a))
    return out


# ── what a design cites (OF-BLD-020 §4.2, D13) ─────────────────────────


def evidence(art: Artifact) -> Evidence:
    """A kept design as one citable value: its id is the artifact's, its
    value the number of vessels BioSTEAM sized, its basis the design's."""
    from . import artifacts

    o = art.output or {}
    n = next((r.get("value") for r in o.get("design") or [] if r.get("label") == "Vessels"), None)
    kind = f", {o['vesselType'].replace('-', ' ')}" if o.get("vesselType") else ""
    return Evidence(
        id=art.id, label=f"Vessel design for {o.get('sourceTool')} {o.get('source')}: BioSTEAM's {o.get('unitClass')}"
                         f"{kind}, the number of vessels it sized (every other number is in the artifact)",
        value=float(n) if isinstance(n, (int, float)) and not isinstance(n, bool) else str(n), unit="vessels",
        provenance=art.provenance, basis=artifacts.basis_of(art), figure="oxygen-balance" if o.get("oxygen") else None)
