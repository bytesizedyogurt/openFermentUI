"""Proforma on the service's side (OF-BLD-014 §8.1).

The worker that runs BioSTEAM is managed by engine/simulator.py; this module
re-exports its `call`, `start`, `status` and `worker`, the names the shelf's
runs, thermo.py, vessel.py and pureOS call it by (and tests stand in for).
"""
from __future__ import annotations

import math
import re
import shutil
from dataclasses import dataclass
from typing import Any

from . import binding as _binding
from .basis import SET_PARAM_ORIGINS, is_set
from .binding import exclusion as _exclusion
from .engine.simulator import (  # noqa: F401  (re-exported: the names callers and tests use)
    CALL_TIMEOUT_S,
    START_TIMEOUT_S,
    Status,
    call,
    start,
    status,
    warm_on_start,
    worker,
)
from .flowsheets import shelf as _shelf
from .workers import WorkerError


def simulator_status():
    """`status()` as its model (`SimulatorStatus`), as GET
    /api/proforma/status answers it."""
    from .models import SimulatorStatus

    return SimulatorStatus.model_validate(status())


def _installed(dist: str) -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(dist)
    except PackageNotFoundError:
        return "not installed"


def drawn_here() -> bool:
    """Whether this host draws a run's flowsheet diagram: Graphviz's `dot` on
    the path the service and its worker share (D8)."""
    return shutil.which("dot") is not None


# OF-BLD-019 §2.R: whether a run's diagram is drawn is part of its basis, so
# a host with Graphviz never inherits, as its own, a run made of the same
# inputs where Graphviz was absent: it computes and keeps its own.
DIAGRAM_DRAWN = "drawn by Graphviz"
DIAGRAM_NOT_DRAWN = "not drawn: Graphviz's dot was not on the path of the host that made this run"


def diagram_input():
    """The basis input that says whether the run's diagram is drawn, from
    this host (D8). A convention: it leaves the provenance as it is."""
    from .models import BasisInput, BasisSource

    return BasisInput(name="diagram", value=DIAGRAM_DRAWN if drawn_here() else DIAGRAM_NOT_DRAWN, unit="",
                      source=BasisSource(kind="convention", note=(
                          "D8: the flowsheet diagram is drawn with Graphviz when its dot is on the host's path; the "
                          "run is the same plant either way, and a host with Graphviz keeps a run of its own")))


def _draws(inputs) -> bool | None:
    """What a run's basis says of its diagram, for the worker; None for a
    run kept before the basis said (the worker then draws when dot is here)."""
    said = _named(inputs, "diagram")
    return None if said is None else str(said) == DIAGRAM_DRAWN


# ── Runs kept from the shelf's retired reference entries (alpha 2.2 D8) ──
#
# The shelf held two hand-written reference entries, cornstover_benchmark and
# corn_drygrind, which retired at alpha 2.2 C.6: the library shelf's
# cornstover and corn run the same packages' plants whole on their own
# defaults (engine/library.py), held to the package's own test, and the
# reference screen reads them. The two artifact tools the entries' runs were
# kept under stay registered, so an artifact a person kept replays: the
# Proforma worker recomputes each from its stored basis through the code
# that computed it (workers/kept_references.py), and a reference run's
# checks set what it measured beside the library plant's package test, the
# same test the entry named. A kept run's tables read as any run's
# (`tables_of`), and a train standing on one reads its streams, on the
# chemical set its entry named (`RETIRED`). Proforma's module rows list the
# kept runs, the reference page shows them, selling_price cites a kept run's
# price when the project keeps no run of the library plant on its package's
# own values (`retired_evidence`), and stream_table cites a kept reference
# run by it. No route or tool computes a new one.

# The benchmark (OF-BLD-014 §8.2): the corn stover plant's price per gallon.
BENCHMARK = "proforma_benchmark"
# A reference entry's run (OF-BLD-019 §2.2): the plant whole, with its tables.
REFERENCE = "proforma.reference"
# 2 (OF-BLD-019 §2.R): the basis says whether the diagram is drawn, and the
# plant builds with fresh chemical caches.
REFERENCE_VERSION = "reference run 2"
# The significant digits a reference run keeps, when its basis names none.
REFERENCE_DIGITS = 10


@dataclass(frozen=True)
class RetiredEntry:
    """What a retired reference entry named, kept for the runs a person kept
    from it: the library plant it built (the package test its kept runs are
    held to is that plant's, engine/library.regression, and its SFF file is
    the library run's to write), its title, the chemical set a train read
    from its kept run builds on (`program`, None where the entry named
    none), and the output a kept run's price is with the basis it is priced
    on."""

    plant: str
    title: str
    program: str | None
    priceOutput: str
    priceBasis: str


RETIRED = {
    "cornstover_benchmark": RetiredEntry(
        plant="cornstover", title="Corn stover to ethanol, the NREL 2011 design", program=None,
        priceOutput="mespUsdPerGal", priceBasis="USD per gallon of ethanol, at the package's own ethanol density"),
    "corn_drygrind": RetiredEntry(
        plant="corn", title="Dry-grind corn to ethanol, the conventional plant", program="yeast",
        priceOutput="ethanolPriceUsdPerKg",
        priceBasis=("USD per kg of the ethanol product stream as the package makes it (ethanol with its denaturant): "
                    "the package's own price, at which its TEA solves the internal rate of return")),
}
# The library plant each retired entry built, by the entry's id.
RETIRED_PLANTS = {entry: r.plant for entry, r in RETIRED.items()}
# The entry the benchmark was run from: the corn stover plant's.
BENCHMARK_ENTRY = "cornstover_benchmark"
BENCHMARK_LABEL = "Minimum ethanol selling price, the NREL 2011 corn stover design as biorefineries.cornstover builds it"
BENCHMARK_UNIT = "USD gal⁻¹"


def retired_entry_of(art) -> str | None:
    """The retired entry a kept run was made from: a reference run's
    flowsheet, or the corn stover entry for the benchmark; None for any
    other artifact."""
    if art.tool == BENCHMARK:
        return BENCHMARK_ENTRY
    if art.tool == REFERENCE:
        entry = str(_named(art.inputs, "flowsheet") or (art.output or {}).get("flowsheet") or "")
        return entry if entry in RETIRED else None
    return None


def kept_from_retired(plant: str | None = None) -> list:
    """The runs the project keeps from the retired reference entries, newest
    first: every reference run and benchmark, or those of the entries that
    built `plant`. A read: it runs nothing."""
    from . import artifacts

    kept = artifacts.of_tools(REFERENCE, BENCHMARK)
    return [a for a in kept if (entry := retired_entry_of(a)) is not None
            and (plant is None or RETIRED[entry].plant == plant)]


def retired_evidence(art):
    """A run kept from a retired reference entry as the one Evidence a claim
    cites it by, its id the artifact's: a benchmark's price per gallon, or a
    reference run's price on its package's own defaults in the output and
    basis its entry named. None for any other run, and for a run that holds
    no price."""
    from . import artifacts
    from .models import Evidence

    entry = retired_entry_of(art)
    if entry is None:
        return None
    o = art.output if isinstance(art.output, dict) else {}
    if art.tool == BENCHMARK:
        value, label, unit = o.get("mespUsdPerGal"), BENCHMARK_LABEL, BENCHMARK_UNIT
    else:
        r = RETIRED[entry]
        value, unit = o.get(r.priceOutput), r.priceBasis
        label = f"{r.title}: the price {o.get('package') or r.plant} gives on the package's own defaults"
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    return Evidence(id=art.id, label=label, value=float(value), unit=unit, provenance=art.provenance,
                    basis=artifacts.basis_of(art), figure=None)


def _run_benchmark(inputs, seed):
    return call("replay_benchmark", {})


def _register() -> None:
    from . import artifacts

    artifacts.register(BENCHMARK, f"biorefineries.cornstover@{_installed('biorefineries')}", _run_benchmark)


def _register_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(BENCHMARK, _register)


_register_lazy()


def _run_reference(inputs, seed):
    """A kept reference run, from its basis alone: the worker builds the
    plant its basis names and reads it; the package test's values are set
    beside what it read, as the run set them."""
    from .engine import library

    flowsheet = str(_named(inputs, "flowsheet"))
    digits = int(str(_named(inputs, "precision") or REFERENCE_DIGITS).split()[0])
    out = call("replay_reference", {"flowsheet": flowsheet, "digits": digits, "diagram": _draws(inputs)})
    plant = RETIRED_PLANTS.get(flowsheet)
    regression = library.regression(plant, None) if plant else None
    out["regression"] = regression.model_dump(mode="json") if regression else None
    out["checks"] = ([c.model_dump(mode="json") for c in library.checks(regression, out.get("measured") or {})]
                     if regression else [])
    return out


def _register_reference() -> None:
    from . import artifacts

    artifacts.register(REFERENCE, f"{REFERENCE_VERSION} · biosteam {_installed('biosteam')} · "
                                  f"biorefineries {_installed('biorefineries')}", _run_reference)


def _lazy_reference() -> None:
    from . import artifacts

    artifacts.register_lazy(REFERENCE, _register_reference)


_lazy_reference()


# ── Runs of a shelf flowsheet (§8.3) ─────────────────────────────────────────────
#
# Its inputs bind to records, or to an assumption a named person typed; the
# run is one artifact whose basis lists every record, assumption, model
# setting and convention it used. This module does the binding and the
# statistics; the worker runs BioSTEAM.

RUN = "proforma.run"
# The samples a run draws unless its request says otherwise, and the most it
# may ask for (OF-BLD-019 D7): settings, not measurements.
SAMPLES = 500
MAX_SAMPLES = 2000
GRID_POINTS = 5
HISTOGRAM_BINS = 20
QUANTILES = (5, 25, 50, 75, 95)
SINGLE = _binding.SINGLE


class ScenarioRefused(ValueError):
    """The scenario cannot run as asked, in words."""


# `_exclusion`, the aggregate gate, lives in binding.py (OF-BLD-020 §3.2), imported above.


def _settle(inp, bound: list, field_id: str) -> None:
    """An input bound to records: their median with their range and a
    triangular draw from three on, a pair drawn uniform, one held fixed and
    flagged (§8.3)."""
    from .models import BasisSource

    inp.binding = "records"
    inp.records, inp.recordIds = bound, [b.id for b in bound]
    inp.source = BasisSource(kind="record", note=f"{len(bound)} record{'s' if len(bound) != 1 else ''} of {field_id}")
    # The statistic lives in binding.py (OF-BLD-020 §3.2), which fermOS's
    # simulation binds through too.
    st = _binding.statistic([b.value for b in bound])
    inp.value, inp.low, inp.high, inp.sampling = st.value, st.low, st.high, st.sampling
    if st.flag:
        inp.flags.append(st.flag)


def _in_place_of(inp, bound: list) -> None:
    """Say how many bound records a person's value stands in place of
    (OF-BLD-020 D3), as a fermOS fit chosen in their place says it."""
    if bound:
        inp.flags.append(f"chosen in place of the {len(bound)} record{'s' if len(bound) != 1 else ''} it bound")


def _assume(inp, a) -> None:
    """An input bound to a named value: a person's assumption, its source
    naming the person (basis.assumption_source), or a model's estimate, its
    source naming the model (basis.estimate_source, ADR-006), either making
    the run `assumed`; or a deposition's reading, its source naming the
    reading and its depositor (basis.measurement_source), which makes a run
    resting on readings and records alone `measured`."""
    from .basis import assumption_source, estimate_source, measurement_source
    from .biorepo import reviewer_refusal

    if a.origin == "model-estimate":
        name = (a.by or "").strip()
        if not name or any(not ch.isprintable() for ch in name):
            raise ScenarioRefused(f"the estimate of {inp.key} names the model that made it, on one line")
    elif a.origin == "measurement":
        from .measurements import unnamed

        name = (a.by or "").strip()
        why = unnamed(name) if name and all(ch.isprintable() for ch in name) else "names nobody on one line"
        if why:
            raise ScenarioRefused(f"the measurement of {inp.key} names the person who deposited its reading: its "
                                  f"reading {why}")
    else:
        why = reviewer_refusal(a.by)
        if why:
            raise ScenarioRefused(f"the assumption for {inp.key} needs a person's name: {why}")
    if not all(math.isfinite(v) for v in (a.value, a.low, a.high)):
        # §2.R: an infinite value passed the range check and broke the artifact's JSON.
        raise ScenarioRefused(f"the assumption for {inp.key} must be a finite number, with a finite low and high")
    if not a.low <= a.value <= a.high:
        raise ScenarioRefused(f"the assumption for {inp.key} must lie within its own low and high")
    inp.binding = "assumption"
    inp.value, inp.low, inp.high = a.value, a.low, a.high
    inp.sampling = "fixed" if a.low == a.high else "uniform"
    inp.source = (estimate_source(a.by, a.at, a.note) if a.origin == "model-estimate"
                  else measurement_source(a.ref or "", a.by, a.at, a.note) if a.origin == "measurement"
                  else assumption_source(a.by, a.at, a.note))


# ── A person's values (OF-BLD-020 §2.2, D3; alpha 2.2 D2) ───────────────
#
# The parameter panel keeps a person's change to a scenario's input as an
# Override of scope `proforma:<scenario id>`, one of the project's rows. A
# run, a binding and a ceiling check carry it as a typed input
# (ProformaRunRequest.inputs; `?inputs=` on the two reads), which
# `overrides_of` converts at Proforma's door into that Override
# (basis.override_of, in the unit of the input or the Finance parameter it
# names). Each is laid on as the named value it is: it wins over the records
# and over a fermOS fit for its input, the input says how many records it
# stands in place of, and the basis names the person
# (basis.assumption_source) or the model (basis.estimate_source, ADR-006),
# so the run is `assumed`. A run that sets a value writes one line more
# (`values_read`), in the words the panel's overrides wrote before a run
# took typed inputs: an artifact's id hashes its basis, so a run a person
# makes through the panel keeps the artifact id it had (alpha 2.2 D6, the
# amendment at C.4).

# That line, its name, its value and its note word for word as the panel's
# overrides wrote it; the older `assumptions` field its note names retired
# at C.4.
ASSUMPTIONS_READ = "assumptions read from"
VALUES_READ = "overrides"
VALUES_READ_NOTE = ("where the named persons' values in this basis came from: the parameter panel's overrides, and any "
                    "the older assumptions field gave, which the service reads as overrides for one release; a basis "
                    "without this input read the older field alone")


def values_read(sets: bool) -> list:
    """The basis input a run writes when it sets a value, an input's or a
    composite's Finance value (`ASSUMPTIONS_READ`, a convention); none for a
    run that sets nothing. The parameter panel's resolve says what a run
    adds through this same function (OF-BLD-020 §2.R)."""
    from .models import BasisInput, BasisSource

    if not sets:
        return []
    return [BasisInput(name=ASSUMPTIONS_READ, value=VALUES_READ, unit="",
                       source=BasisSource(kind="convention", note=VALUES_READ_NOTE))]


def proforma_scope(scenario_id: str) -> str:
    """The parameter scope of a scenario (params.parse_scope's proforma form)."""
    return f"proforma:{scenario_id}"


def held_to_scope(scenario_id: str, overrides: list) -> None:
    """An override names the scope it changes: one sent for a run of
    `scenario_id` under another scenario's scope is refused in words, an
    input's and a composite's finance alike (OF-BLD-020 §6.R, main-28)."""
    stray = sorted({o.scope for o in overrides if o.scope != proforma_scope(scenario_id)})
    if stray:
        raise ScenarioRefused(f"an override names the scope it changes, and these were sent for "
                              f"{proforma_scope(scenario_id)}: {', '.join(stray)}")


def named_values(scenario_id: str | None, overrides: list | None = None) -> list:
    """A person's or a model's values for a scenario's inputs, as the binding
    lays them on: each Override of the scenario's scope as an
    `InputAssumption`, its origin the Override's. With no
    scenario id (GET /api/proforma/bind) every override names one proforma
    scope. Refused in words: an override of another scope, a value in words,
    and an input named twice."""
    from .models import InputAssumption

    over = list(overrides or [])
    scopes = sorted({o.scope for o in over})
    if scenario_id is not None:
        held_to_scope(scenario_id, over)
    elif len(scopes) > 1 or (scopes and not scopes[0].startswith("proforma:")):
        raise ScenarioRefused(f"the overrides of one binding name one scenario's scope, proforma:<scenario id>; "
                              f"these name {', '.join(scopes)}")
    from . import params

    out: dict[str, InputAssumption] = {}
    for o in over:
        if isinstance(o.value, bool) or not isinstance(o.value, (int, float)):
            raise ScenarioRefused(f"{o.key} takes a number, and its value was sent as {o.value!r}")
        if o.key in out:
            raise ScenarioRefused(f"{o.key} is set twice: a run sets each input once")
        when = params.unstamped(o)
        if when:  # §2.R, finding 5: the resolve refused it, and the run kept a basis naming no day
            raise ScenarioRefused(when)
        value = float(o.value)
        # One end typed, the other is the value (params.held, as the panel's
        # resolve reads it); neither, the value is held fixed at itself.
        low, high = params.held(value, o.low, o.high)
        out[o.key] = InputAssumption(key=o.key, value=value, low=value if low is None else low,
                                     high=value if high is None else high, by=o.by, at=o.at, note=o.note,
                                     origin=o.origin, ref=o.ref)
    return list(out.values())


def overrides_of(scenario_id: str, flowsheet: str, inputs: list | None) -> list:
    """The values a run request sets (ProformaRunRequest.inputs), each a
    typed quantity with its origin, as the Overrides of the scenario's scope
    `proforma:<scenario id>` its binding takes (basis.override_of), each in
    the unit of the parameter its name keys: an input of the flowsheet, or a
    parameter of the Finance group of a flowsheet built from a vessel and a
    train (params.flowsheet_specs, composite.finance_specs). Proforma's door,
    where every value set is converted once. A name the flowsheet takes no
    value for is refused in the words `_check_keys` says it in; a value in
    another unit than its parameter's, one carrying a basis and one that says
    no day are refused in basis.override_of's words (ScenarioRefused)."""
    from . import composite, params
    from .basis import InputRefused, override_of

    info = _shelf.info(flowsheet, allow_toy=True)
    specs = params.flowsheet_specs(info) + (composite.finance_specs() if info.builtFrom else [])
    units = params.units_of(specs)
    given = list(inputs or [])
    unknown = sorted({i.name for i in given if i.name not in units})
    if unknown:
        raise ScenarioRefused(f"{info.id} takes no input {', '.join(unknown)}")
    out = []
    for i in given:
        try:
            out.append(override_of(proforma_scope(scenario_id), i, units[i.name]))
        except InputRefused as e:
            raise ScenarioRefused(str(e)) from None
    return out


def inputs_of(flowsheet: str, overrides: list) -> list:
    """A scenario's Overrides (the rows the project keeps for its scope) as the
    inputs a run request carries, each in the unit of the parameter its key
    names: the inverse of `overrides_of`, the service's mirror of the
    browser's own (src/lib/params.ts `inputsOf`). A key the flowsheet takes no
    value for goes with no unit, as the browser sends it, and the run refuses
    it in words."""
    from . import composite, params
    from .models import EngineInput, Origin, Quantity

    info = _shelf.info(flowsheet, allow_toy=True)
    units = params.units_of(params.flowsheet_specs(info) + (composite.finance_specs() if info.builtFrom else []))
    return [EngineInput(name=o.key, quantity=Quantity(value=o.value, unit=units.get(o.key, ""), low=o.low, high=o.high,
                                                      origin=Origin(kind=o.origin, by=o.by, at=o.at, note=o.note,
                                                                    ref=o.ref)))
            for o in overrides]


def fits_beside(fits: dict[str, str] | None, typed: list) -> dict[str, str]:
    """The fermOS fits a person chose, less any input a person's value
    overrides: an override wins over a fit (D3), so the fit is not laid on
    there, and a fit's productivity then stands beside titre as the binding
    has it."""
    named = {a.key for a in typed}
    return {k: v for k, v in (fits or {}).items() if k not in named}


def _check_keys(info, typed: list) -> None:
    """Every input a person's value names is one the flowsheet takes a value
    for; a convention is stated in the basis and takes none."""
    takes = {i.key for i in info.inputs if i.kind != "convention"}
    stated = sorted({a.key for a in typed} & {i.key for i in info.inputs if i.kind == "convention"})
    if stated:
        raise ScenarioRefused(f"{', '.join(stated)} {'is a convention' if len(stated) == 1 else 'are conventions'} every "
                              f"run of {info.id} states in its basis, and takes no value")
    unknown = sorted({a.key for a in typed} - takes)
    if unknown:
        raise ScenarioRefused(f"{info.id} takes no input {', '.join(unknown)}")


def basis_inputs(inputs: list, flowsheet: str, samples: int = SAMPLES, scenario_id: str | None = None,
                 fitted: list | None = None, parts: Any = None, finance: list | None = None) -> list:
    """The run's basis: the flowsheet, the scenario it belongs to, what it
    borrows from a package, the samples, and every record, assumption and
    convention; an input a fermOS fit feeds names the fit's
    artifact (OF-BLD-019 §5.1), and `fitted` adds what else the fit gave
    (the batch time a productivity is the titre over). A composite run
    (OF-BLD-020 §6.1) adds its vessel design, its train run and its finance
    (`composite.basis_inputs`), and names the plant scale the vessel design
    gave as `plant_scale vessel`."""
    from .models import BasisInput, BasisSource

    info = _shelf.info(flowsheet, allow_toy=True)
    note = f"{info.title}: {info.description}"
    out = [BasisInput(name="flowsheet", value=flowsheet, unit="", source=BasisSource(kind="convention", note=note))]
    if scenario_id:
        # OF-BLD-019 §2.3 (e): the scenario a run belongs to, as words; pureOS
        # reads it ("a basis input named scenario wins"). A convention, so it
        # leaves the provenance as the records and assumptions make it.
        out.append(BasisInput(name="scenario", value=scenario_id, unit="", source=BasisSource(
            kind="convention", note="the scenario this run belongs to")))
    if flowsheet == ETHANOL:
        out += ethanol_basis()
    elif parts is not None:
        from . import composite

        out += composite.basis_inputs(parts, list(finance or []))
    if info.priceOutput:
        out.append(utility_input())
    out.append(diagram_input())
    out.append(BasisInput(name="samples", value=f"{samples} Latin hypercube", unit="", source=BasisSource(kind="convention")))
    for inp in inputs:
        if inp.binding == "records":
            out += [BasisInput(name=f"{inp.key} record", value=r.value, unit=inp.unit,
                               source=BasisSource(kind="record", id=r.id)) for r in inp.records]
        elif inp.binding == "assumption":
            out += assumption_inputs(inp)
        elif inp.binding == "artifact":
            # A fermOS fit or simulation a person chose; a composite's vessel
            # design for the plant scale it gives (OF-BLD-020 §6.1).
            what = "vessel" if parts is not None and inp.source is not None and inp.source.id == parts.vessel.id else "fit"
            for part, v in (("", inp.value), (" low", inp.low), (" high", inp.high)):
                out.append(BasisInput(name=f"{inp.key} {what}{part}", value=v, unit=inp.unit, source=inp.source))
    out += fitted or []
    return out


def assumption_inputs(inp) -> list:
    """The basis inputs a run writes for one input bound to a named person's
    value: the value, its low and its high, each with the person as its
    source. The parameter panel's resolve says what a run adds through this
    same function (OF-BLD-020 §2.R)."""
    from .models import BasisInput

    return [BasisInput(name=f"{inp.key}{part}", value=v, unit=inp.unit, source=inp.source)
            for part, v in (("", inp.value), (" low", inp.low), (" high", inp.high))]


def utility_input():
    """What a priced scenario run's utility lines and equipment costs rest
    on (OF-BLD-019 §2.R): BioSTEAM's own default utility prices and plant
    cost index, which the flowsheet sets at the start of every case and
    reads back, so no case prices on what an earlier plant left in the
    worker. BioSTEAM's defaults, not the corn plant's own settings."""
    from .models import BasisInput, BasisSource

    sim = f"biosteam@{_installed('biosteam')}"
    return BasisInput(
        name="utility prices and cost index",
        value="biosteam.process_tools.default_utilities() and default_CEPCI()", unit="",
        source=BasisSource(kind="model", id=sim, note=(
            "BioSTEAM's own default prices of electricity and of each heating and cooling agent, and its default plant "
            "cost index, set at the start of every case and read back after it, each value the case used "
            "(cepci, electricityPrice, and each agent's price and temperature)")))


def _specs(inputs: list) -> tuple[dict[str, dict], dict[str, float], dict[str, str]]:
    """Back from the basis to what the worker samples: per key a spec, the
    base case, and each input's source kind."""
    import statistics

    vals: dict[str, list[float]] = {}
    # The values the run set, by key: a person's, a model's or a reading,
    # and the source kind of each that is no person's.
    assumed: dict[str, dict[str, float]] = {}
    estimated: dict[str, str] = {}
    fitted: dict[str, dict[str, float]] = {}
    from . import composite

    for i in inputs:
        if i.name.startswith(composite.PREFIXES):
            # OF-BLD-020 §6.1: what a composite run carries of its vessel
            # design, its train run and its finance is built, not sampled.
            continue
        named = _FIT_NAME.fullmatch(i.name)
        if named is None:
            named = _VESSEL_NAME.fullmatch(i.name)
        if named and i.source.kind == "artifact":
            fitted.setdefault(named[1], {})[named[2] or "value"] = float(i.value)
        elif i.name.endswith(" record"):
            v = float(i.value)
            key = i.name.removesuffix(" record")
            vals.setdefault(key, []).append(v)
        elif is_set(i.source):
            key, _, part = i.name.partition(" ")
            assumed.setdefault(key, {})[part or "value"] = float(i.value)
            if i.source.kind != "assumption":
                estimated[key] = i.source.kind
    specs, base, kinds = {}, {}, {}
    for key, vs in vals.items():
        vs = sorted(vs)
        kinds[key] = "record"
        if len(vs) >= 3 and vs[0] != vs[-1]:
            specs[key] = {"kind": "triangular", "low": vs[0], "mode": statistics.median(vs), "high": vs[-1]}
            base[key] = statistics.median(vs)
        elif len(vs) == 2 and vs[0] != vs[-1]:
            specs[key], base[key] = {"kind": "uniform", "low": vs[0], "high": vs[1]}, (vs[0] + vs[1]) / 2
        else:
            specs[key], base[key] = {"kind": "fixed", "value": vs[0]}, vs[0]
    for key, a in assumed.items():
        kinds[key] = estimated.get(key, "assumption")
        base[key] = a["value"]
        specs[key] = ({"kind": "fixed", "value": a["value"]} if a["low"] == a["high"]
                      else {"kind": "uniform", "low": a["low"], "high": a["high"]})
    for key, f in fitted.items():
        # A fermOS fit's value: the forecast's median, drawn triangular over
        # its 5th and 95th percentile (OF-BLD-019 §5.1).
        kinds[key] = "artifact"
        base[key] = f["value"]
        if f["low"] == f["high"]:
            specs[key] = {"kind": "fixed", "value": f["value"]}
        elif f["low"] <= f["value"] <= f["high"]:
            specs[key] = {"kind": "triangular", "low": f["low"], "mode": f["value"], "high": f["high"]}
        else:
            specs[key] = {"kind": "uniform", "low": min(f["low"], f["high"]), "high": max(f["low"], f["high"])}
    return specs, base, kinds


def _ranks(x):
    """Average ranks, so tied values share one (§8.R: sample order broke ties)."""
    import numpy as np

    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    for v in np.unique(x):
        tied = x == v
        if tied.sum() > 1:
            r[tied] = r[tied].mean()
    return r


def _spearman(xr, yr) -> float | None:
    """Pearson over ranks; None when either side does not vary."""
    import numpy as np

    if np.ptp(xr) == 0 or np.ptp(yr) == 0:
        return None
    return float(np.corrcoef(xr, yr)[0, 1])


def _named(inputs, name: str):
    return next((i.value for i in inputs if i.name == name), None)


def _samples_of(inputs) -> int:
    """The sample count the basis states ('500 Latin hypercube')."""
    said = _named(inputs, "samples")
    try:
        return int(str(said).split()[0])
    except (IndexError, ValueError):
        return SAMPLES


def _run_scenario(inputs, seed):
    """One run of a flowsheet, from its basis alone: the worker's `run` op
    simulates the base case and reads its tables, walks the grid and draws
    the samples; this function turns the samples into the price's
    quantiles, histogram and Spearman sensitivity (averaged ranks, §8.R)."""
    import numpy as np

    flowsheet = str(_named(inputs, "flowsheet"))
    info = _shelf.info(flowsheet, allow_toy=True)
    price_key = info.priceOutput
    specs, base, kinds = _specs(inputs)
    axes = {}
    for k in info.gridInputs:
        s = specs[k]
        axes[k] = [s["value"]] if s["kind"] == "fixed" else [float(v) for v in np.linspace(s["low"], s["high"], GRID_POINTS)]
    from . import composite

    ask = {"flowsheet": flowsheet, "base": base, "specs": specs, "samples": _samples_of(inputs),
           "seed": int(seed or 0), "axes": axes or None, "diagram": _draws(inputs)}
    if flowsheet == composite.FLOWSHEET:
        # OF-BLD-020 §6.1: the vessel design's fermenter, the train run's
        # units and the finance a person set, from the basis alone.
        ask["structure"] = composite.structure_of(inputs)
    try:
        r = call("run", ask)
    except WorkerError as e:
        text = str(e)
        if text.startswith("Refused: "):
            raise ScenarioRefused(text.removeprefix("Refused: ")) from None
        raise
    base_out, base_infeasible = r["base"], r["baseInfeasible"]
    mc = r["montecarlo"]

    feasible = [s for s in mc["samples"] if s["outputs"] is not None]
    infeasible: dict[str, int] = {}
    for s in mc["samples"]:
        if s["infeasible"]:
            infeasible[s["infeasible"]["reason"]] = infeasible.get(s["infeasible"]["reason"], 0) + 1
    prices = np.array([s["outputs"][price_key] for s in feasible], dtype=float) if price_key else np.array([])
    quantiles, histogram, sensitivity = {}, [], []
    if len(prices):
        quantiles = {f"p{q}": float(np.percentile(prices, q)) for q in QUANTILES}
        counts, edges = np.histogram(prices, bins=HISTOGRAM_BINS)
        histogram = [{"low": float(edges[i]), "high": float(edges[i + 1]), "count": int(c)} for i, c in enumerate(counts)]
        pr = _ranks(prices)
        for key, spec in specs.items():
            if spec["kind"] == "fixed" or len(prices) < 3:
                continue
            xr = _ranks(np.array([s["inputs"][key] for s in feasible], dtype=float))
            rho = _spearman(xr, pr)
            if rho is None:
                continue
            sensitivity.append({"key": key, "rho": rho, "sourceKind": kinds[key]})
        sensitivity.sort(key=lambda r: -abs(r["rho"]))
    lines = ("capex", "media", "utilities", "labor", "downstream", "other")
    grid = None
    if r["grid"] is not None:
        cells = r["grid"]["cells"]
        grid = {
            "dims": [{"key": k, "values": v} for k, v in axes.items()],
            "msp": [c["outputs"][price_key] if c["outputs"] and price_key else None for c in cells],
            "costLines": {ln: [c["outputs"]["costLines"][ln] if c["outputs"] and "costLines" in c["outputs"] else None
                               for c in cells] for ln in lines},
            "infeasible": sum(1 for c in cells if c["outputs"] is None),
        }
    read_back = base_out.get("readBack") if base_out else (feasible[0]["outputs"].get("readBack") if feasible else None)
    t = r["tables"] or {}
    return {
        "flowsheet": flowsheet,
        "base": base,
        "basePrice": base_out.get(price_key) if base_out and price_key else None,
        "baseCostLines": base_out.get("costLines") if base_out else None,
        "baseInfeasible": base_infeasible,
        "readBack": read_back or {},
        "quantiles": quantiles,
        "histogram": histogram,
        "sensitivity": sensitivity,
        "samples": len(mc["samples"]),
        "feasible": len(feasible),
        "infeasible": infeasible,
        "grid": grid,
        # OF-BLD-019 §2.1 (D1): the base case's tables, as the worker read them.
        "tablesSource": t.get("tablesSource"),
        "tea": t.get("tea"),
        "streams": t.get("streams") or [],
        "units": t.get("units") or [],
        "utilities": t.get("utilities"),
        "diagram": t.get("diagram"),
        "diagramNote": t.get("diagramNote") if r["tables"] is not None else (
            "the base case could not run, so it has no tables" if base_infeasible else None),
        "unitOrder": t.get("unitOrder") or [],
        "tableUnits": t.get("tableUnits") or {},
    }


def plant_of(art) -> dict[str, Any]:
    """What the worker rebuilds a run's base case from, read from the run's
    basis alone, for its SFF file (ADR-003, engine/sff.py `export`): a shelf
    run's flowsheet with its base values and, for a composite, its structure.
    A run kept from a retired reference entry is refused in words naming the
    library plant whose run writes the same package's plant (alpha 2.2 D8)."""
    if art.tool in (REFERENCE, BENCHMARK):
        entry = str(_named(art.inputs, "flowsheet") or "cornstover_benchmark")
        plant = RETIRED_PLANTS.get(entry, "cornstover")
        raise ScenarioRefused(f"{art.tool} artifact {art.id} is a run kept from a reference entry that retired from "
                              f"Proforma's shelf at alpha 2.2: it replays as kept, and its SFF file is the library "
                              f"plant {plant}'s to write (run {plant} with POST /api/library/{plant}/run, which keeps "
                              "that run's file)")
    if art.tool == RUN:
        from . import composite

        flowsheet = str(_named(art.inputs, "flowsheet"))
        _, base, _ = _specs(art.inputs)
        plant: dict[str, Any] = {"flowsheet": flowsheet, "base": base}
        if flowsheet == composite.FLOWSHEET:
            plant["structure"] = composite.structure_of(art.inputs)
        return plant
    raise ScenarioRefused(f"{art.tool} is not a run of a flowsheet: a shelf run is exported as SFF")


# A run that carries its tables (OF-BLD-019 §2.1); a run stored before them
# was versioned by its flowsheet alone, and replays with that difference said.
# 2 (OF-BLD-019 §2.R): the basis names the utility prices and cost index and
# whether the diagram is drawn; the product's stream row carries the solved
# price; the plant builds as in a fresh worker.
RUN_VERSION = "shelf run 2"


def _register_run() -> None:
    from . import artifacts

    # The version names what the code computes, not one flowsheet: the
    # flowsheet is in each run's basis (OF-BLD-019 §2.1).
    artifacts.register(RUN, f"{RUN_VERSION} · biosteam {_installed('biosteam')} · biorefineries {_installed('biorefineries')}",
                       _run_scenario)


def _lazy_run() -> None:
    from . import artifacts

    artifacts.register_lazy(RUN, _register_run)


_lazy_run()


def _check_samples(n: int) -> None:
    if not 1 <= n <= MAX_SAMPLES:
        raise ScenarioRefused(f"a run draws between 1 and {MAX_SAMPLES} samples; {n} were asked for")


def _check_seed(seed: int) -> None:
    """The sampler takes a whole number from zero up (§2.R: a negative seed
    reached it after the base case and the grid had run)."""
    if seed < 0:
        raise ScenarioRefused(f"a run's seed is a whole number from 0 up; {seed} was given")


def _no_sample_held(art) -> str:
    """Why a run kept no price, in words: each reason its samples could not
    be held, counted, and the base case's own words; and the run it kept
    (§2.R: the 422 said only that there was no price, and the run it had
    stored was found nowhere)."""
    o = art.output
    n = o.get("samples") or 0
    reasons = "; ".join(f"{reason}: {count} of {n}" for reason, count in sorted((o.get("infeasible") or {}).items()))
    base = o.get("baseInfeasible")
    return ("this run has no sample the flowsheet could hold, so it has no price to cite"
            + (f" (the samples that could not run, by reason: {reasons})" if reasons else "")
            + (f"; the base case: {base}" if base else "")
            + f". The run is kept as artifact {art.id}.")


def keep_run(flowsheet: str, basis: list, *, by: str = "", seed: int = 0, records_by_id: Any = None,
             scenario_id: str | None = None, configuration: str | None = None):
    """A run's `proforma.run` artifact computed and kept as a run of the
    biosteam engine (engine/runs.compute_kept; alpha 2.2 D3, D6): one runs
    row, its thing the flowsheet, its configuration none (or, for a
    flowsheet built from a vessel and a train, the two it was built from,
    `parts_configuration`), the scenario's id on the row, created by `by`.
    Its SFF file is written at keep time by the Proforma worker from the
    run's base case (`write_file`) and kept as the record `run-<id>`, or the
    words for why it has none kept as `sffRefused`. A refusal the worker
    gives inside the computation is kept as a receipt and raised as
    ScenarioRefused with the receipt's id as `run_id`; the same request
    again is answered from its row, the computation one artifact whatever
    its cases (a grid, a sample)."""
    from .engine import runs

    return runs.compute_kept(runs.LIBRARY_ENGINE, flowsheet, configuration, tool=RUN, basis=basis,
                             refusal=ScenarioRefused, by=by, seed=seed, records_by_id=records_by_id,
                             scenario_id=scenario_id, write_sff=write_file)


def write_file(art, project_id: str, by: str):
    """A run's SFF file, written by the Proforma worker from the run's base
    case, rebuilt from its basis alone (`plant_of`, engine/sff.py `export`,
    through `call`), and kept as the record `run-<id>`. A run whose base case
    could not run has no plant to write: the worker is asked nothing, and
    the run keeps the words (sff.SFFRefused)."""
    from .engine import sff

    failed = art.output.get("baseInfeasible")
    if failed:
        raise sff.SFFRefused(f"the run's base case could not run ({failed}), so it has no plant to write as an SFF file")
    return sff.export(plant_of(art), project_id=project_id, run_artifact_id=art.id, by=by, call=call)


def computed(req, pool=None):
    """A scenario's run as `run` makes it, short of reading its price: bound,
    refused where an input waits for a source, and kept once per basis as one
    `proforma.run` artifact and its row (`keep_run`). Answers the artifact,
    the inputs as bound and the flowsheet's shelf entry. A run whose samples
    hold no price is kept like any other: the price is `run`'s to refuse."""
    from . import evidence_pool

    # OF-BLD-019 §2.3 (d): a scenario the project keeps by its id, or one a
    # page has not yet saved by the shelf flowsheet it names; anything else is
    # refused.
    flowsheet = flowsheet_of(req.scenarioId, req.flowsheet)
    info = _shelf.info(flowsheet)
    _check_samples(req.samples)
    _check_seed(req.seed)
    # Alpha 2.2 D2: the values set, each a typed quantity, converted at the
    # door into the Overrides of the scenario's scope.
    overrides = overrides_of(req.scenarioId, flowsheet, req.inputs)
    # OF-BLD-020 §6.1 (D11): a composite names its vessel design and its
    # train run, each held to the rules (composite.parts_of); the finance
    # group's overrides are its own, apart from the inputs'.
    parts, finance, rest = _composite(flowsheet, req.vessel, req.trainRun, overrides, scenario_id=req.scenarioId)
    # OF-BLD-020 §2.2 (D3): a person's values, each a named assumption that
    # wins over the records and any fit for its input.
    typed = named_values(req.scenarioId, rest)
    # A run that sets a value, an input's or a Finance value, says so in its
    # basis in the panel's words (`values_read`), so its artifact id is the
    # one the panel's overrides gave it.
    sets = bool(rest) or (finance is not None and any(v.overriddenBy for v in finance))
    _check_keys(info, typed)
    pool = pool or evidence_pool.load()
    inputs = bind_inputs(flowsheet, pool.records, req.host, typed)
    if parts is not None:
        from . import composite

        composite.vessel_scale(inputs, parts)
    # OF-BLD-019 §5.1 (D10): the fermOS fits a person chose, each computed
    # from its artifact; one that cannot feed its input is refused in words.
    # An input a person's value overrides takes no fit (D3).
    fitted = apply_fits(inputs, fits_beside(req.fits, typed), flowsheet)
    waiting = [i.key for i in inputs if i.binding == "waiting"]
    if waiting:
        raise ScenarioRefused("these inputs wait for a source, a record or a named person's assumption: " + ", ".join(waiting))
    art = keep_run(flowsheet, basis_inputs(inputs, flowsheet, req.samples, scenario_id=req.scenarioId, fitted=fitted,
                                           parts=parts, finance=finance) + values_read(sets),
                   by=req.by, seed=req.seed, records_by_id=pool.records_by_id, scenario_id=req.scenarioId,
                   configuration=parts_configuration(parts.vessel.id, parts.train.id) if parts is not None else None)
    return art, inputs, info


def run(req, pool=None):
    """Bind, refuse what waits for a source, and run once per basis, the run
    kept as one row of the biosteam engine (`computed`, `keep_run`). The run
    is one `proforma.run` artifact holding the price, the sensitivity and the
    base case's tables (D1); this reads them back from it, and refuses in
    words a run whose samples hold no price, the run kept."""
    from .models import ProformaGrid, ProformaRunResult

    art, inputs, info = computed(req, pool)
    o = art.output
    q = o["quantiles"]
    if not q:
        raise ScenarioRefused(_no_sample_held(art))
    ev = evidence_of(art)
    tables = tables_of(art)
    return ProformaRunResult(
        scenarioId=req.scenarioId, artifactId=art.id, provenance=art.provenance, inputs=inputs,
        basePrice=o["basePrice"], baseCostLines=o["baseCostLines"], baseInfeasible=o["baseInfeasible"],
        quantiles=q, histogram=o["histogram"], sensitivity=o["sensitivity"], samples=o["samples"],
        feasible=o["feasible"], infeasible=o["infeasible"], grid=ProformaGrid(**o["grid"]), readBack=o["readBack"],
        leavesOut=info.leavesOut, priceBasis=info.priceBasis or "", evidence=ev, **tables.model_dump())


def run_flowsheet(flowsheet: str, assumptions: list, *, samples: int = SAMPLES, seed: int = 0,
                  allow_toy: bool = False, scenario_id: str | None = None):
    """Run a flowsheet whose every input is a named person's assumption, and
    return its one `proforma.run` artifact, keeping no runs row: no route,
    tool or engine reaches it, and a test or a fixture makes a run's artifact
    with it (`run` keeps the row of every run a door asks for). The toy is
    refused unless the caller is a test or a fixture and says `allow_toy`; a
    flowsheet built from kept artifacts (OF-BLD-020 §6.1) runs as a scenario
    that names them."""
    from . import artifacts
    from .models import ScenarioInput

    try:
        info = _shelf.info(flowsheet, allow_toy=allow_toy)
    except _shelf.NotOnShelf as e:
        raise ScenarioRefused(str(e)) from None
    if info.builtFrom:
        raise ScenarioRefused(f"{flowsheet} is built from {' and '.join(info.builtFrom)} artifacts a scenario names: it "
                              "runs as that scenario (POST /api/proforma/run with vessel and trainRun)")
    _check_samples(samples)
    _check_seed(seed)
    given = {a.key: a for a in assumptions}
    unknown = sorted(set(given) - {i.key for i in info.inputs if i.kind != "convention"})
    if unknown:
        raise ScenarioRefused(f"{flowsheet} takes no input {', '.join(unknown)}")
    inputs = []
    for fi in info.inputs:
        if fi.kind == "convention":  # stated in the basis; it takes no value
            continue
        inp = ScenarioInput(key=fi.key, label=fi.name, unit=fi.unit, binding="waiting")
        if fi.key in given:
            _assume(inp, given[fi.key])
        inputs.append(inp)
    waiting = [i.key for i in inputs if i.binding == "waiting"]
    if waiting:
        raise ScenarioRefused("these inputs wait for a source, a record or a named person's assumption: " + ", ".join(waiting))
    return artifacts.compute(RUN, basis_inputs(inputs, flowsheet, samples, scenario_id=scenario_id),
                             records_by_id={}, seed=seed)


def tables_of(art):
    """The tables a `proforma.run` artifact holds, as every reader reads
    them (D1: Proforma, pureOS, fermOS, Postdoc, the MCP server); a library
    run and a `proforma.reference` artifact kept from a retired reference
    entry (§2.2) hold the same keys and read the same way. A run stored
    before §2.1 reads with empty tables and its flowsheet from its basis."""
    from .models import ProformaTables

    o = art.output
    fields = {k: o[k] for k in ProformaTables.model_fields if k in o and o[k] is not None}
    fields.setdefault("flowsheet", next((str(i.value) for i in art.inputs if i.name == "flowsheet"), None))
    return ProformaTables.model_validate(fields)


# The tools whose artifacts hold a run's tables (`tables_of`): a Proforma
# run, a library plant's run, and a run kept from a retired reference entry.
# The last two also hold the checks against their package's own test
# (`checks_of`).
TABLE_TOOLS = (RUN, "library.run", REFERENCE)


def checks_of(art):
    """A run's checks against its package's own test, as a library run and a
    run kept from a retired reference entry hold them (`output.checks`,
    engine/library.py `checks`): each of the test's values beside what the
    run computed. A run that holds none reads as an empty list."""
    from .models import RegressionCheck

    return [RegressionCheck.model_validate(c) for c in art.output.get("checks") or []]


def shelf() -> list:
    """The shelf (flowsheets/shelf.py), for `GET /api/proforma/shelf`; the
    toy is never on it."""
    return list(_shelf.SHELF.values())


def evidence_of(art):
    """A run as one Evidence: the median price with the 5th to 95th percentile."""
    from . import artifacts
    from .models import Evidence, Range

    q = art.output["quantiles"]
    if not q:
        raise ScenarioRefused("this run has no sample the flowsheet could hold, so it has no price to cite")
    # The scenario and flowsheet the run's basis names (OF-BLD-019 §2.3).
    flowsheet = str(_named(art.inputs, "flowsheet") or "")
    scenario_id = _named(art.inputs, "scenario") or flowsheet
    info = _shelf.info(flowsheet, allow_toy=True)
    return Evidence(
        id=art.id, label=f"Minimum selling price, {scenario_id} ({info.title})",
        value=q.get("p50", float("nan")), unit=info.priceBasis or "",
        interval=Range(low=q["p5"], high=q["p95"]) if q else None,
        provenance=art.provenance, basis=artifacts.basis_of(art), figure="distribution")


def latest_run(scenario_id: str):
    """The most recent stored run of a scenario, or None: a run whose basis
    names the scenario, or one stored before a basis named its scenario
    whose flowsheet is the kept scenario's (OF-BLD-019 §2.3)."""
    from . import artifacts

    own = {s["id"]: s.get("modelId") for s in held_scenarios()}.get(scenario_id)

    def belongs(a) -> bool:
        named = _named(a.inputs, "scenario")
        if named:
            return named == scenario_id
        return own is not None and str(_named(a.inputs, "flowsheet") or "") == own

    runs = [a for a in artifacts.all_artifacts() if a.tool == RUN and belongs(a)]
    return max(runs, key=lambda a: a.createdAt) if runs else None


# ── Glucose to ethanol, and every scenario the shelf can run (OF-BLD-019 §2.3) ──
#
# The flowsheet of our own binds by the shelf alone: each process input to
# the records of the fields its shelf entry names, in the evidence pool,
# through the aggregate gate and units.py. A scenario the project keeps
# names the shelf flowsheet it runs; one not yet saved (D6) names one in the
# request, and binds and runs the same way. Rule 1: no
# value here; the stand-ins live in the tests.

ETHANOL = "ethanol_glucose_v0"
# The carbon source a record must name to bind a process input of a
# flowsheet `bind_inputs` binds: the flowsheet's own feed. A record naming
# none is left out and counted, as one naming another feed is.
FEED_CARBON: dict[str, frozenset[str]] = {ETHANOL: frozenset({"glucose"}), _shelf.COMPOSITE: frozenset({"glucose"})}
# What a bound scenario says it makes, by flowsheet. A composite makes what
# its train traces (OF-BLD-020 §6.1): on the yeast chemical set, ethanol.
PRODUCTS = {ETHANOL: "ethanol", _shelf.COMPOSITE: "ethanol"}


def held_scenarios() -> list[dict]:
    """The BioSTEAM scenarios the project keeps (New scenario; the project's
    rows, project_state.py), each naming the shelf flowsheet it runs (its
    `modelId`): every scenario of the project, whichever browser made it."""
    from . import project_state

    return [r for r in project_state.kept("scenarios") if r.get("kind") == "biosteam"
            and r.get("modelId") in _shelf.SHELF]


def runnable(flowsheet: str):
    """The shelf entry of a flowsheet a scenario can run, or the refusal in
    words: the toy and an id the shelf does not hold are refused."""
    try:
        return _shelf.info(flowsheet)
    except _shelf.NotOnShelf as e:
        raise ScenarioRefused(str(e)) from None


def flowsheet_of(scenario_id: str, flowsheet: str | None = None) -> str:
    """The flowsheet a run runs: a kept scenario's own, by its id; else, for
    a scenario a page has not yet saved (ADR-014: its write waits in the
    browser's queue), the shelf flowsheet it names. Any other case is
    refused, in words."""
    if not (scenario_id or "").strip():
        raise ScenarioRefused("a run names the scenario it belongs to")
    held = {s["id"]: s for s in held_scenarios()}
    if scenario_id in held:
        own = held[scenario_id]["modelId"]
        if flowsheet and flowsheet != own:
            raise ScenarioRefused(f"{scenario_id} runs {own}, not {flowsheet}")
        return own
    if not flowsheet:
        raise ScenarioRefused(f"there is no kept scenario {scenario_id}; the BioSTEAM scenarios this project keeps are "
                              f"{', '.join(held) or 'none'}, and a scenario not yet saved names the flowsheet it runs")
    return runnable(flowsheet).id


def bind_inputs(flowsheet: str, records: list[dict], host: str | None = None, assumptions: list | None = None) -> list:
    """Every input of a shelf flowsheet that takes a value, bound by its shelf
    entry: a process input to the records of its fields (the first field
    with a bound record wins) in the evidence pool that pass the
    aggregate gate and name the flowsheet's feed as their carbon source, each
    converted by units.py into the input's unit; else it waits. A named
    person's assumption (an Override from the parameter panel, OF-BLD-020
    D3) wins over the records and says how many it stands in place of. A
    convention takes no value: the run's basis states it."""
    from . import units, validate
    from .models import BoundRecord, ScenarioInput

    info = _shelf.info(flowsheet, allow_toy=True)
    feed = FEED_CARBON.get(flowsheet, frozenset())
    given = {a.key: a for a in assumptions or []}
    out = []
    for fi in info.inputs:
        if fi.kind == "convention":
            continue
        inp = ScenarioInput(key=fi.key, label=fi.name, unit=fi.unit, binding="waiting")
        bound: list = []
        refused: str | None = None
        used = None
        for field_id in fi.fields:
            no_carbon = other_carbon = 0
            for r in records:
                if r.get("field") != field_id or _exclusion(r):
                    continue
                if host and r.get("strainId") != host:
                    continue
                carbon = r.get("carbonSource")
                if not carbon:
                    no_carbon += 1
                    continue
                if validate.carbon_source_id(carbon) not in feed:
                    other_carbon += 1
                    continue
                try:
                    v = units.convert(float(r["value"]), r.get("unit") or fi.unit, fi.unit)
                except (TypeError, ValueError) as e:
                    refused = f"record {r['id']}: {units.explain_refusal(r.get('unit') or '', fi.unit) or e}"
                    break
                bound.append(BoundRecord(id=r["id"], paperId=r["paperId"], value=v,
                                         organism=r.get("organismText") or r.get("strainId"), carbonSource=carbon,
                                         provenance=r.get("provenance") or "unverified"))
            inp.leftOutNoCarbon += no_carbon
            inp.leftOutOtherCarbon += other_carbon
            if refused or bound:
                used = field_id
                break
        if refused:
            inp.flags.append(f"the binding stopped: {refused}")
            if fi.key in given:
                _assume(inp, given[fi.key])
        elif fi.key in given:
            # OF-BLD-020 D3: a named person's value wins over the records.
            _in_place_of(inp, bound)
            _assume(inp, given[fi.key])
        elif bound:
            _settle(inp, bound, used)
        out.append(inp)
    return out


def ethanol_basis() -> list:
    """What the glucose-to-ethanol flowsheet takes from packages and states
    as conventions, for every run's basis (D3, D4): each package with its
    version, the theoretical yield the fermenter's conversion is a share of,
    the batch time's rule, and fuel grade. Values the run reads back are in
    its `readBack`; none is typed here."""
    from .models import BasisInput, BasisSource

    corn = f"biorefineries.corn@{_installed('biorefineries')}"
    ethanol = f"biorefineries.ethanol@{_installed('biorefineries')}"
    sim = f"biosteam@{_installed('biosteam')}"
    return [
        BasisInput(name="chemicals and finance", value=corn, unit="", source=BasisSource(
            kind="model", id=corn,
            note="the dry-grind corn ethanol plant's create_chemicals, and its create_tea: ConventionalEthanolTEA "
                 "with the package's default_tea_parameters")),
        BasisInput(name="purification train", value=ethanol, unit="", source=BasisSource(
            kind="model", id=ethanol,
            note="create_ethanol_purification_system as the package builds it: beer column with its heat "
                 "integration, rectifier, superheater, molecular sieves, product tanks")),
        BasisInput(name="fermenter", value=f"{sim} BatchBioreactor", unit="", source=BasisSource(
            kind="model", id=sim,
            note="BioSTEAM's batch bioreactor, sized and costed by BioSTEAM; its working volume fraction, cleaning "
                 "time and temperature are its own, its vessel limit BioSTEAM's anaerobic bioreactor's, all read back")),
        BasisInput(name="theoretical yield", value="Glucose -> 2 Ethanol + 2 CO2", unit="", source=BasisSource(
            kind="convention",
            note="the fermenter's conversion is the bound yield over this reaction's yield at thermosteam's "
                 "molecular weights; the run reads the theoretical yield back")),
        BasisInput(name="batch time", value="titre / productivity", unit="h", source=BasisSource(kind="convention")),
        BasisInput(name="ethanol purity", value="fuel grade", unit="", source=BasisSource(
            kind="convention",
            note="the ethanol the package's molecular sieves give, with no denaturant blended; the run reads the "
                 "purity back")),
    ]


def _hosts(records: list[dict], flowsheet: str) -> list[str]:
    info = _shelf.info(flowsheet, allow_toy=True)
    fields = {f for i in info.inputs for f in i.fields}
    return sorted({r.get("strainId") for r in records
                   if r.get("strainId") and r.get("field") in fields})


def bound(flowsheet: str, *, scenario_id: str = "", name: str = "", host: str | None = None,
          assumptions: list | None = None, pool=None, fits: dict[str, str] | None = None,
          vessel: str | None = None, train_run: str | None = None):
    """A flowsheet's inputs bound, in the shape GET /api/proforma/scenarios
    serves: a kept scenario's with its id and name, a flowsheet's alone with
    both empty (§2.3, c); with the fermOS fits a person chose laid on
    (OF-BLD-019 §5.1), and a person's named values over both (OF-BLD-020
    D3: an input a value overrides takes no fit). A composite (OF-BLD-020
    §6.1) binds with the vessel design and the train run it names, held to
    the rules, and the plant scale
    the vessel was designed at."""
    from . import evidence_pool
    from .models import ProformaScenarioInfo

    parts, _, _ = _composite(flowsheet, vessel, train_run, [])
    pool = pool or evidence_pool.load()
    info = _shelf.info(flowsheet, allow_toy=True)
    inputs = bind_inputs(flowsheet, pool.records, host, assumptions)
    if parts is not None:
        from . import composite

        composite.vessel_scale(inputs, parts)
    out = ProformaScenarioInfo(
        id=scenario_id, name=name, product=PRODUCTS.get(flowsheet, flowsheet), flowsheet=flowsheet, host=host,
        hosts=_hosts(pool.records, flowsheet), inputs=inputs, waiting=[], leavesOut=info.leavesOut,
        priceBasis=info.priceBasis or "")
    apply_fits(out.inputs, fits_beside(fits, assumptions or []), flowsheet)
    out.waiting = [i.key for i in out.inputs if i.binding == "waiting"]
    return out


def scenarios(host: str | None = None, pool=None) -> list:
    """GET /api/proforma/scenarios (§2.3, b): one bound scenario per BioSTEAM
    scenario the project keeps, every one the project's (alpha 2.2 D9), each
    bound with the vessel design and the train run it names where its
    flowsheet is built from them (custom_train_v1). A scenario its binding
    refuses (a part that cannot stand) and one on a flowsheet the shelf no
    longer holds (a retired entry's id, alpha 2.2 D8) are listed with the
    refusal in words and no inputs, so one scenario never stops the list."""
    from . import evidence_pool, project_state

    out = []
    for s in held_scenarios():
        pool = pool or evidence_pool.load()
        try:
            out.append(bound(s["modelId"], scenario_id=s["id"], name=s.get("name") or s["id"], host=host, pool=pool,
                             vessel=s.get("vessel") or None, train_run=s.get("trainRun") or None))
        except ScenarioRefused as e:
            out.append(_listed_refused(s, host, str(e)))
    listed = {s.id for s in out}
    for s in project_state.kept("scenarios"):
        if s.get("kind") == "biosteam" and s.get("modelId") not in _shelf.SHELF and s.get("id") not in listed:
            try:
                _shelf.info(str(s.get("modelId")))
            except _shelf.NotOnShelf as e:
                out.append(_listed_refused(s, host, str(e.args[0])))
    return out


def _listed_refused(s: dict, host: str | None, words: str):
    """A kept scenario as the list shows one its binding refuses: its id,
    name and flowsheet, no inputs, and the refusal in words."""
    from .models import ProformaScenarioInfo

    flowsheet = str(s.get("modelId"))
    info = _shelf.SHELF.get(flowsheet)
    return ProformaScenarioInfo(
        id=s["id"], name=s.get("name") or s["id"], product=PRODUCTS.get(flowsheet, flowsheet), flowsheet=flowsheet,
        host=host, inputs=[], leavesOut=info.leavesOut if info else [],
        priceBasis=(info.priceBasis or "") if info else "", refused=words)


def bind_flowsheet(flowsheet: str, host: str | None = None,
                   assumptions: list | None = None, pool=None, fits: dict[str, str] | None = None,
                   vessel: str | None = None, train_run: str | None = None):
    """GET /api/proforma/bind (§2.3, c): a shelf flowsheet's inputs bound as a
    scenario of that flowsheet not yet saved (ADR-014) shows them, id and
    name empty, with the fermOS fits a person chose (OF-BLD-019 §5.1). The
    toy, an id the shelf does not hold, and a fit that cannot feed the input
    it was chosen for are refused in words."""
    runnable(flowsheet)
    return bound(flowsheet, host=host, assumptions=assumptions, pool=pool, fits=fits, vessel=vessel,
                 train_run=train_run)


def _composite(flowsheet: str, vessel: str | None, train_run: str | None,
               overrides: list, *, scenario_id: str | None = None) -> tuple[Any, list | None, list]:
    """OF-BLD-020 §6.1 (D11): for a flowsheet built from kept artifacts, the
    two parts the request names (composite.parts_of, refused in words), the
    finance group with the person's values laid on, and the overrides left
    for the inputs; for any other, (None, None, the overrides), and a vessel
    or a train run named for it is refused. With a scenario id (a run), every
    override is held to its scope before the finance is split off, as the
    inputs' are (§6.R, main-28)."""
    from . import composite, params

    info = _shelf.info(flowsheet, allow_toy=True)
    if not info.builtFrom:
        named = [w for w, x in (("vessel", vessel), ("trainRun", train_run)) if x]
        if named:
            raise ScenarioRefused(f"{flowsheet} is not built from a vessel design or a train run: {' and '.join(named)} "
                                  f"belong to a scenario on {composite.FLOWSHEET}")
        return None, None, list(overrides)
    if scenario_id is not None:
        held_to_scope(scenario_id, list(overrides))
    parts = composite.parts_of(vessel, train_run)
    rest, mine = composite.split_overrides(overrides)
    try:
        finance = composite.finance_values(mine)
    except params.ParamRefused as e:
        raise ScenarioRefused(str(e)) from None
    return parts, finance, rest


# ── A scenario's flowsheet as a thing of the biosteam engine (alpha 2.2 D6) ──
#
# The biosteam engine (engine/biosteam.py) lists the shelf's flowsheets a
# scenario runs beside the library's plants, and runs each as Proforma runs a
# scenario of it, through the provider this module registers with it as it
# is imported (`_provide`). Its parameters are the inputs a scenario of it binds, as
# GET /api/proforma/bind binds one with no scenario: the records of the
# evidence pool, the stated conventions, and for a flowsheet built from a
# vessel and a train its Finance group at the package's own defaults and
# the plant scale its vessel design gives; an input nothing binds has no
# default and waits for a run's value. A run is the run of an unsaved
# scenario of it, named by the flowsheet's own id, so the same request is
# the same row. A flowsheet built from a kept vessel design and a kept train
# run (custom_train_v1) runs in a configuration naming the two, one for each
# pair the project's kept scenarios of it name whose parts stand, and is
# listed while the project keeps one: its parts are a scenario's to name.

# What the biosteam engine says a scenario's flowsheet is (EngineThing.kind).
THING_KIND = "scenario"
# A configuration of a flowsheet built from a vessel and a train: the two
# artifacts' ids, as a scenario of it names them (`parts_configuration`).
_PARTS = re.compile(r"vessel (\S+), train run (\S+)")


def runs_as_thing(flowsheet: str) -> bool:
    """Whether a flowsheet is one a scenario runs, and so a thing of the
    biosteam engine whatever the project keeps: on the shelf."""
    return flowsheet in _shelf.SHELF


def parts_configuration(vessel: str, train_run: str) -> str:
    """The configuration of a flowsheet built from a vessel and a train that
    names the vessel design and the train run a scenario of it is built from."""
    return f"vessel {vessel}, train run {train_run}"


def _kept_parts(flowsheet: str) -> list[str]:
    """The configurations of a flowsheet built from a vessel and a train: each
    pair of parts a scenario of it the project keeps names, once, in the
    order the project keeps them, whose parts stand (composite.parts_of: a
    pair that cannot stand is said on its scenario's page). Nothing while no
    project is named."""
    from . import composite, project_state, projects
    from .models import CONFIGURATION_MAX

    if projects.current_or_none() is None:
        return []
    out: list[str] = []
    for row in project_state.kept("scenarios"):
        if not isinstance(row, dict) or row.get("kind") != "biosteam" or row.get("modelId") != flowsheet:
            continue
        vessel, train_run = row.get("vessel"), row.get("trainRun")
        if not (isinstance(vessel, str) and vessel and isinstance(train_run, str) and train_run):
            continue
        name = parts_configuration(vessel, train_run)
        if name in out or len(name) > CONFIGURATION_MAX:
            continue
        try:
            composite.parts_of(vessel, train_run)
        except ScenarioRefused:
            continue
        out.append(name)
    return out


def thing_flowsheets() -> list[tuple[Any, list[str]]]:
    """The shelf's flowsheets a scenario runs (`runnable`: every one on the
    shelf, no toy), in the shelf's order, each with the configurations
    it runs in as a thing of the biosteam engine: none for a flowsheet built
    from nothing a scenario names; for one built from a kept vessel design
    and a kept train run, each pair of parts the project's scenarios of it
    name (`_kept_parts`), the flowsheet listed while there is one."""
    out = []
    for info in _shelf.SHELF.values():
        configurations = _kept_parts(info.id) if info.builtFrom else []
        if info.builtFrom and not configurations:
            continue
        out.append((info, configurations))
    return out


def _thing_parts(flowsheet: str, configuration: str | None) -> tuple[str | None, str | None]:
    """The vessel design and the train run a thing's configuration names, or
    the refusal in words: a flowsheet built from nothing a scenario names
    takes no configuration, and one built from a vessel and a train takes one
    of those its kept scenarios name."""
    info = runnable(flowsheet)
    cfg = (configuration or "").strip() or None
    if not info.builtFrom:
        if cfg is not None:
            raise ScenarioRefused(f"{flowsheet} takes no configuration, and {cfg!r} was named")
        return None, None
    held = _kept_parts(flowsheet)
    if cfg is None or cfg not in held:
        said = f"{cfg!r} is none of them" if cfg is not None else "none was named"
        raise ScenarioRefused(f"{flowsheet} runs in a configuration naming the vessel design and the train run a "
                              f"scenario of it the project keeps is built from: "
                              f"{'; '.join(held) or 'the project keeps no such scenario'}; {said}")
    vessel, train_run = _PARTS.fullmatch(cfg).groups()
    return vessel, train_run


def _engine_parameter(spec: Any, v: Any) -> Any:
    """One parameter of a scenario's flowsheet as the engine contract states
    it, from its value as the scenario's scope binds it with nothing set: the
    records that bound it (a `record` naming them), a fermOS fit, a kept
    simulation or the vessel design (an `artifact` naming it), the stated
    convention with its note, the package's own default (a `library-default`
    naming the package); else no default, which a run sets."""
    from .basis import origin_of
    from .models import EngineParameter, Origin

    origin = None
    if v is not None and v.value is not None and v.origin != "waiting":
        ref = v.source.id if v.source is not None and v.source.id else None
        if v.origin == "record":
            ids = ", ".join(v.recordIds) or ref
            origin = Origin(kind="record", ref=ids, note=v.detail) if ids else None
        elif v.origin in ("fit", "simulation", "artifact"):
            origin = Origin(kind="artifact", ref=ref, note=v.detail) if ref else None
        elif v.origin == "convention":
            note = (v.detail or spec.note or "").strip() or f"{spec.key}'s stated convention"
            origin = Origin(kind="convention", note=note)
        elif v.origin == "library-default":
            origin = Origin(kind="library-default", ref=ref, note=v.detail) if ref else None
        elif v.origin in SET_PARAM_ORIGINS and v.source is not None:
            origin = origin_of(v.source)
    return EngineParameter(**spec.model_dump(), value=v.value if origin is not None else None, origin=origin)


def thing_parameters(flowsheet: str, configuration: str | None) -> list:
    """What a run of a scenario's flowsheet takes, as the biosteam engine
    states it: each input, and a composite's Finance parameters, as a
    scenario of it binds them with nothing set (the `proforma:` scope of the
    flowsheet's own id, which binds as GET /api/proforma/bind binds a
    scenario not yet saved), each default with its origin
    (`_engine_parameter`). Reads the project's records and kept artifacts;
    starts no worker and keeps nothing."""
    from . import params
    from .models import ParamResolveRequest

    vessel, train_run = _thing_parts(flowsheet, configuration)
    try:
        scope = params.scope(proforma_scope(flowsheet),
                             ParamResolveRequest(flowsheet=flowsheet, vessel=vessel, trainRun=train_run))
    except (params.ParamRefused, params.ScopeUnknown) as e:
        raise ScenarioRefused(str(e).strip("'\"")) from None
    values = {v.key: v for v in scope.values}
    return [_engine_parameter(s, values.get(s.key)) for s in scope.specs]


def run_thing(flowsheet: str, configuration: str | None, inputs: list, by: str):
    """One run of a scenario's flowsheet as the biosteam engine runs it: the
    run of an unsaved scenario of the flowsheet, its id the flowsheet's own,
    bound as GET /api/proforma/bind binds one, with the values set (`inputs`,
    converted at Proforma's door) and the parts its configuration names,
    every other setting a scenario run's own default (its samples, its
    seed); kept as one row by `computed`, the artifact answered. A run whose
    samples hold no price is kept and answered as the run it is."""
    from .models import ProformaRunRequest

    vessel, train_run = _thing_parts(flowsheet, configuration)
    art, _, _ = computed(ProformaRunRequest(scenarioId=flowsheet, flowsheet=flowsheet, inputs=list(inputs), by=by,
                                            vessel=vessel, trainRun=train_run))
    return art


def thing_list() -> list:
    """The shelf's scenario flowsheets as the biosteam engine lists them,
    each in the configurations it runs in (`thing_flowsheets`), kind
    `scenario`. proforma.run registers no replay tolerance, so each replays
    identically: its precision is rtol 0, atol 0."""
    from .models import EnginePrecision, EngineThing

    exact = EnginePrecision(rtol=0.0, atol=0.0)
    return [EngineThing(id=info.id, title=info.title, kind=THING_KIND, configurations=configurations,
                        precision=exact) for info, configurations in thing_flowsheets()]


def _run_as_thing(flowsheet: str, configuration: str | None, inputs: list, by: str) -> str:
    """`run_thing` as the biosteam engine's provider answers it: the id of
    the run kept. A request its fields cannot hold (a `by` longer than a
    request takes) is refused in the request's words."""
    from pydantic import ValidationError

    try:
        return run_thing(flowsheet, configuration, inputs, by).id
    except ValidationError as e:
        said = e.errors()[0]["msg"] if e.errors() else str(e)
        raise ScenarioRefused(f"the biosteam engine cannot take this request: {said}") from None


def _provide() -> None:
    """The shelf's scenario flowsheets given to the biosteam engine as things
    of its own (engine/biosteam.py `provide`), as this module is imported:
    the engine package imports no Proforma module, and the service's app
    imports this one through its tools."""
    from .engine import biosteam

    biosteam.provide(biosteam.Provider(name="proforma", things=thing_list, holds=runs_as_thing,
                                       parameters=thing_parameters, run=_run_as_thing, refusal=ScenarioRefused))


_provide()


# ── A fermOS fit feeds the fermenter (OF-BLD-019 §5.1, D10) ─────────────
#
# A source, not a copy. A person picks a kept kinetic fit or forecast for a
# scenario's titre, yield and productivity (the request names the artifact
# per input; a model never picks it), and the service computes each value
# from it: titre from the forecast's final product, yield from product made
# over sugar used (Yp/s), and productivity as that titre over the batch
# time, the hour the forecast's median sugar runs out (fermos.forecast_for
# says how the forecast was had). Each value is the forecast's median with
# its 5th and 95th percentile, drawn triangular; the run's basis names the
# artifact as an `artifact` source, so its provenance enters through
# basis_provenance (a fit of a deposition rests on `measured` readings).
# A fit that cannot give an input is refused in words naming the parameter:
# μ or Xmax not identified, no Yp/s, no sugar series. A fit whose product
# series names another product than the scenario's is refused whole.
# `batch_simulation` does not exist in this tree; fermOS keeps
# `kinetic_fit` and `growth_forecast` (fermos.FEEDABLE).
#
# A SIMULATION FEEDS TOO (OF-BLD-020 §3.3, D1). A kept `fermos.simulation`
# gives the same three from its end state as it was kept: titre its final
# product at harvest, yield the product made over the sugar used to harvest,
# productivity that titre over the harvest hour, which is the batch time it
# gives; each a single value (a simulation draws no band), fixed. Its
# provenance is the artifact's own, basis_provenance over every source its
# parameters came from (a person's value makes it `assumed`), and it enters a
# run through the `artifact` source as a fit's does. A simulation is never a
# measurement, and its card says so. A chemostat runs continuously and gives
# a batch flowsheet nothing; a simulation of another product is refused
# whole, as a fit's product series is.

FIT_KEYS = ("titre", "yield", "productivity")

_FIT_NAME = re.compile(r"(\w+) fit(?: (low|high))?")
# OF-BLD-020 §6.1: an input a composite's vessel design binds (its plant
# scale), named `<key> vessel`, `… vessel low`, `… vessel high`, read back
# into what the worker samples as a fit's are.
_VESSEL_NAME = re.compile(r"(\w+) vessel(?: (low|high))?")
# The words a series' label or measure id uses for what each shelf
# flowsheet makes, to tell a fit of another product's series (PRODUCTS).
PRODUCT_WORDS: dict[str, tuple[str, ...]] = {
    "ethanol": ("ethanol", "etoh"),
}
# The concentration a titre is reckoned in, to make a productivity per hour.
_CONC, _PROD = "g L-1", "g L-1 h-1"


def _names(series, product: str) -> bool:
    if series is None:
        return False
    words = set(re.findall(r"[a-z0-9]+", f"{series.label} {series.measureId}".lower()))
    return any(w in words for w in PRODUCT_WORDS.get(product, (product,)))


def _converted(v: dict, frm: str, to: str) -> tuple[float, float, float]:
    from . import units

    return tuple(units.convert(float(v[k]), frm, to) for k in ("low", "median", "high"))  # type: ignore[return-value]


def fit_info(art, flowsheet: str):
    """What one kept fermOS artifact can feed a shelf flowsheet's titre,
    yield and productivity, each with how it is computed or why not."""
    from . import fermos, units
    from .models import FermosFitInfo, FitFeed

    info = runnable(flowsheet)
    declared = {i.key: i for i in info.inputs if i.key in FIT_KEYS}
    if not declared:
        raise ScenarioRefused(f"{flowsheet} takes no titre, yield or productivity, so no fermOS fit feeds it")
    product = PRODUCTS.get(flowsheet, flowsheet)
    out = FermosFitInfo(artifactId=art.id, tool=art.tool, provenance=art.provenance, createdAt=art.createdAt,
                        flowsheet=flowsheet, depositionId=fermos.deposition_of(art), fitArtifactId=fermos.fit_artifact_of(art))

    def refuse_all(why: str):
        out.refused = why
        out.feeds = [FitFeed(key=k, unit=i.unit, derivation="", refused=why) for k, i in declared.items()]
        return out

    if art.tool == fermos.SIMULATION:
        return _simulation_info(art, out, declared, product, flowsheet, refuse_all)
    try:
        fit_ = fermos.fit_of(art)
    except fermos.FitRefused as e:
        return refuse_all(str(e))
    roles = fermos.series_by_role(fit_)
    prod, sub = roles.get("product"), roles.get("substrate")
    out.productSeries = prod.label if prod else None
    out.substrateSeries = sub.label if sub else None
    others = [p for p in PRODUCT_WORDS if p != product and _names(prod, p)]
    if prod is not None and others and not _names(prod, product):
        return refuse_all(f"its product series, {prod.label}, is {others[0]}, not {product}, the product of {flowsheet}")
    if prod is not None and not _names(prod, product):
        out.flags.append(f"its product series, {prod.label}, names no product: it is read as {product} because a person chose it")
    try:
        fc, how = fermos.forecast_for(art)
    except fermos.FitRefused as e:
        return refuse_all(str(e))

    final = next((f for f in fc["finals"] if f["role"] == "product"), None)
    end = fc["times"][-1] if fc["times"] else None
    titre: tuple[float, float, float] | None = None
    titre_why = None
    if final is None:
        titre_why = "the fit has no product series, so it gives no final product"
    else:
        try:
            titre = _converted(final, final["unit"], _CONC)
        except units.UnitError:
            titre_why = f"the product series is in {final['unit']}, which is not a mass concentration"
    runs = fc.get("substrateRunsOutH")
    if sub is None:
        batch_why = "no sugar series: the fit has no substrate series, so it gives no batch time"
    elif runs is None:
        batch_why = (f"the forecast's median sugar does not run out within its {end:.4g} h, so it gives no batch time; "
                     "a forecast on fermOS → Forecast run until the sugar is spent does")
    elif runs <= 0:
        batch_why = "the forecast's median sugar is spent at its start, so it gives no batch time"
    else:
        batch_why = None
        out.batchTimeH = float(runs)
        out.batchTimeNote = FORECAST_BATCH_NOTE

    feeds = []
    for key, inp in declared.items():
        feed = FitFeed(key=key, unit=inp.unit, derivation="")
        try:
            if key == "titre":
                feed.derivation = f"the final product of {how}: its median, with the 5th and 95th percentile of its band for readings"
                if titre is None:
                    feed.refused = titre_why
                else:
                    feed.low, feed.value, feed.high = (units.convert(v, _CONC, inp.unit) for v in titre)
            elif key == "yield":
                feed.derivation = f"Yp/s, product made over sugar used, from {how}: its median, with the 5th and 95th percentile"
                y = fc.get("yieldInterval")
                if y is None:
                    one = units.normalize(prod.unit) if prod is not None else None
                    feed.refused = ("no Yp/s: the fit has no product series" if prod is None else
                                    "no Yp/s, and no sugar series: the fit has no substrate series" if sub is None else
                                    # A forecast kept before one unit spelled two ways was read as one (§5.R).
                                    f"no Yp/s in this forecast as kept: it was drawn before {prod.unit} and {sub.unit} "
                                    "were read as one unit; a forecast of the fit for another length gives it"
                                    if one is not None and one == units.normalize(sub.unit) else
                                    f"no Yp/s: the product series is in {prod.unit} and the sugar series in "
                                    f"{sub.unit}, which are not one mass concentration")
                elif units.family(prod.unit) != "massConc":
                    feed.refused = f"no Yp/s: the product and sugar series are in {prod.unit}, not a mass concentration"
                else:
                    # Product over sugar in one mass concentration: grams per gram.
                    feed.low, feed.value, feed.high = (units.convert(float(y[k]), "g g-1", inp.unit)
                                                       for k in ("low", "median", "high"))
            else:
                feed.derivation = (f"titre over batch time: the final product of {how} over the hour its median sugar "
                                   "runs out, the 5th and 95th percentile of the product over the same hour")
                if titre is None:
                    feed.refused = f"productivity is titre over batch time, and {titre_why}"
                elif batch_why:
                    feed.refused = f"productivity is titre over batch time, and {batch_why}"
                else:
                    feed.low, feed.value, feed.high = (units.convert(v / float(runs), _PROD, inp.unit) for v in titre)
        except units.UnitError as e:
            feed.low = feed.value = feed.high = None
            feed.refused = f"its value does not convert to {inp.unit}: {e}"
        feeds.append(feed)
    out.feeds = feeds
    return out


# How the batch time a productivity is the titre over was found, by the tool
# that kept it (§8.R): the run's `fit batch time` input, its refusal of a
# productivity fed apart from its titre, and the page all say these words.
FORECAST_BATCH_NOTE = ("the hour the forecast's median sugar runs out, found between its grid points; productivity is "
                       "the fit's titre over it, and titre is the same fit's")


def simulation_batch_note(aid: str, where: str) -> str:
    return (f"the harvest hour of simulation {aid} ({where}); productivity is the simulation's final titre over it, "
            "and titre is the same simulation's")


def _simulation_info(art, out, declared: dict, product: str, flowsheet: str, refuse_all):
    """What a kept simulation feeds (OF-BLD-020 §3.3): its end state as it
    was kept, read from the artifact and recomputed nowhere."""
    from . import fermos, kinetics, units
    from .models import FitFeed

    try:
        sim = fermos.result_of(art)
    except (KeyError, TypeError, ValueError) as e:
        return refuse_all(f"simulation {art.id} cannot be read as one: {e}")
    fam = kinetics.FAMILIES.get(sim.family)
    out.flags.append(f"a {sim.family} simulation, not a measurement: each value it gives was computed from the sources "
                     "its basis names, and its provenance follows them")
    if isinstance(fam, kinetics.ChemostatV1):
        return refuse_all(f"it simulates a chemostat ({sim.family}), which runs continuously and has no batch: "
                          f"{flowsheet} takes a batch's titre, yield and batch time")
    # OF-BLD-020 §3.R (finding 14): the titre a flowsheet takes is a product
    # in the broth (the family's P), which a family fermOS does not have
    # carries none, whatever product the simulation names.
    if fam is None or fam.product_state() != "P":
        return refuse_all(f"it simulates {sim.family}, a family that keeps no product in the broth: {flowsheet} "
                          f"takes the titre of {product} in the broth")
    if sim.product and sim.product != product:
        return refuse_all(f"it simulates {sim.product}, not {product}, the product of {flowsheet}")
    if not sim.product:
        out.flags.append(f"it names no product: it is read as {product} because a person chose it")
    out.productSeries = sim.product
    out.substrateSeries = sim.sugar
    harvest = (sim.sugarRunsOutH if sim.sugarRunsOutH is not None and sim.harvestH == sim.sugarRunsOutH
               else None)
    where = ("the hour its sugar runs out" if harvest is not None else "its run's end")
    if sim.harvestH and sim.harvestH > 0:
        out.batchTimeH = float(sim.harvestH)
        # §8.R (findings 0, 4, 10): a simulation has no forecast, no median
        # and no grid; its batch time is its harvest hour, said as such.
        out.batchTimeNote = simulation_batch_note(art.id, where)
    for flag in sim.flags:
        if "did not run out" in flag:
            out.flags.append(flag[:1].lower() + flag[1:].rstrip("."))
    G = kinetics.G_L
    got = {
        "titre": (sim.finalTitre, G, f"the final product of simulation {art.id} at harvest ({where})",
                  "the family keeps no product state" if sim.finalTitre is None else None),
        "yield": (sim.yieldAchieved, "g g⁻¹", f"product made over sugar used to harvest ({where}) in simulation {art.id}",
                  "no sugar was used before harvest" if sim.yieldAchieved is None else None),
        "productivity": (sim.productivity, f"{G} h⁻¹",
                         f"the final titre of simulation {art.id} over its harvest hour ({where}), the batch time it gives",
                         "it gives no titre or no harvest hour" if sim.productivity is None else None),
    }
    feeds = []
    for key, inp in declared.items():
        value, unit, derivation, why = got[key]
        feed = FitFeed(key=key, unit=inp.unit, derivation=derivation)
        if why:
            feed.refused = why
        else:
            try:
                feed.value = feed.low = feed.high = units.convert(float(value), unit, inp.unit)
            except units.UnitError as e:
                feed.refused = f"its value does not convert to {inp.unit}: {e}"
        feeds.append(feed)
    out.feeds = feeds
    return out


def fermos_fits(flowsheet: str) -> list:
    """GET /api/fermos/fits: every kinetic fit and forecast fermOS keeps,
    and every simulation (OF-BLD-020 §3.3), newest first, each with what it
    can feed `flowsheet` and why not. A read: it keeps nothing and starts no
    simulator."""
    from . import artifacts, fermos

    runnable(flowsheet)
    return [fit_info(a, flowsheet) for a in artifacts.all_artifacts() if a.tool in fermos.FEEDS_PROFORMA]


def apply_fits(inputs: list, fits: dict[str, str], flowsheet: str) -> list:
    """Bind each input a person chose a fermOS fit for to that artifact, in
    place, and return what else the basis takes from it (the batch time a
    productivity is the titre over). Refused in words: a key a fit cannot
    feed, an artifact not on file, and a fit that cannot give the input,
    naming the parameter."""
    from . import artifacts
    from .models import BasisInput, BasisSource

    if not fits:
        return []
    unknown = sorted(k for k in fits if k not in FIT_KEYS)
    if unknown:
        raise ScenarioRefused(f"a fermOS fit feeds {', '.join(FIT_KEYS)} alone; {', '.join(unknown)} take records "
                              "or a named person's assumption")
    by = {i.key: i for i in inputs}
    missing = sorted(k for k in fits if k not in by)
    if missing:
        raise ScenarioRefused(f"{flowsheet} takes no input {', '.join(missing)}")
    # A fit's productivity is its titre over the hour its sugar runs out, and
    # the fermenter's batch time is the bound titre over the bound
    # productivity: beside any other titre that batch time is not the fit's,
    # and the basis would name one the run did not use (§5.R). So it feeds
    # only beside titre from the same fit, and is refused in words naming
    # what titre is, never bound to the fit behind the person's back.
    paired = None
    if fits.get("productivity") and fits.get("titre") != fits["productivity"]:
        t = by["titre"] if "titre" in by else None
        n = len(t.records) if t else 0
        paired = (f"titre is from {fits['titre']}" if fits.get("titre") else
                  f"titre binds {n} record{'s' if n != 1 else ''}" if t and t.binding == "records" else
                  f"titre is a deposition's reading ({t.source.id if t.source else ''}), which wins over any fit"
                  if t and t.binding == "assumption" and _a_reading(t) else
                  "titre is a named person's assumption, which wins over any fit" if t and t.binding == "assumption" else
                  "titre waits for a source")
        # §2.R (finding 13): beside a titre a person typed, choosing the fit
        # for titre is not enough, since the person's value wins over it.
        remedy = ("reset titre to its source and choose {aid} for titre" if t and t.binding == "assumption"
                  and not fits.get("titre") else "choose {aid} for titre as well")
    infos: dict[str, Any] = {}
    extra: list = []
    for key in FIT_KEYS:
        aid = fits.get(key)
        if not aid:
            continue
        if aid not in infos:
            try:
                infos[aid] = fit_info(artifacts.get(aid), flowsheet)
            except artifacts.ArtifactNotFound:
                raise ScenarioRefused(f"there is no kept artifact {aid}: fermOS keeps a fit when it fits a deposited "
                                      "run, and a forecast when one is made from it") from None
            except artifacts.ArtifactDamaged as e:
                raise ScenarioRefused(str(e)) from None
        info = infos[aid]
        feed = next(f for f in info.feeds if f.key == key)
        if info.refused or feed.refused:
            raise ScenarioRefused(f"{info.tool} {aid} cannot feed {key}: {info.refused or feed.refused}")
        inp = by[key]
        had = len(inp.records)
        inp.binding = "artifact"
        inp.value, inp.low, inp.high = feed.value, feed.low, feed.high
        inp.sampling = "fixed" if feed.low == feed.high else "triangular"
        inp.source = BasisSource(kind="artifact", id=aid, note=feed.derivation)
        inp.records, inp.recordIds = [], []
        inp.leftOutNoCarbon = inp.leftOutOtherCarbon = 0
        inp.flags = ([f"chosen in place of the {had} record{'s' if had != 1 else ''} it bound"] if had else []) + list(info.flags)
        if key == "productivity" and paired:
            # §8.R (finding 10): worded by the tool that kept it, never a
            # forecast's words for a simulation.
            what = ("its final titre over its harvest hour" if info.tool == "fermos.simulation"
                    else "its titre over the hour its median sugar runs out")
            raise ScenarioRefused(
                f"productivity from {info.tool} {aid} is {what}, so it feeds "
                f"the fermenter only beside titre from {aid}: the fermenter's batch time is the titre over the "
                f"productivity, and here {paired}. To use it, {remedy.format(aid=aid)}, or stop using it for "
                "productivity")
        if key == "productivity" and info.batchTimeH is not None:
            extra.append(BasisInput(name="fit batch time", value=info.batchTimeH, unit="h", source=BasisSource(
                kind="artifact", id=aid, note=info.batchTimeNote or FORECAST_BATCH_NOTE)))
    return extra


# ── The geneOS ceiling check (OF-BLD-019 §5.2, D11) ─────────────────────
#
# A flag, never a bound. A scenario's fermenter yield, as the scenario binds
# it (its records' median and range, a person's assumption with its range,
# or a fermOS fit's Yp/s), is set beside the newest stored `geneos.ceiling`
# of each model on geneOS's shelf that is of the scenario's organism and has
# a route to its product, on the sugar its flowsheet's feed is. Both are put
# on the ceiling's own footing: grams of product per gram of sugar through
# units.py, and mol per mol at the conventions the ceiling's basis names
# (the artifact's own molPerMol over its gPerG). A yield, or its high end,
# above a ceiling is flagged in words asking a reviewer to check its basis;
# nothing is clamped, and no binding or run changes. Computed on read and
# kept nowhere, as GET /api/fermos/fits is; it starts no worker.
#
# The organism, from what the tree gives: the scenario's host filter when it
# has one; else, record by record, the strain a bound yield record names
# (its `strainId`, read through the strain catalogue), else the species its
# paper's words name, else none; the organism line counts each kind (§5.R:
# a few records of a catalogued strain never speak for the rest). A shelf
# model is the scenario's when its host is one of those strains ('strain')
# or of one of those species ('species': geneOS's yeast reconstructions,
# iMM904 and Yeast9, are of S288C), each said so on its row with the
# records it covers.

# The sugar each scenario flowsheet's feed is, as geneOS names its
# substrates: the glucose-to-ethanol flowsheet's is glucose (FEED_CARBON).
CEILING_SUGAR: dict[str, str] = {ETHANOL: "glucose", _shelf.COMPOSITE: "glucose"}
_G_PER_G = "g g-1"
CEILING_KEPT = "Computed on read and kept nowhere: the binding and the run keep the yield as bound."


def _input_named(art, name: str):
    return next((i for i in art.inputs if i.name == name), None)


def _ceiling_of(art, name: str) -> str | None:
    """What a ceiling's basis names: its model by the shelf id the model
    input's source carries, its product and substrate by their values."""
    i = _input_named(art, name)
    if i is None:
        return None
    return (str(i.source.id) if i.source.id else None) if name == "model" else str(i.value)


def stored_ceilings(model_id: str, product: str, sugar: str | None = None, stored: list | None = None) -> list:
    """The stored geneOS ceilings of one shelf model for one product, newest
    first (all_artifacts' order), on `sugar` alone when it is named: the
    lookup ceiling_check reads, and fermOS's simulation reads beside its
    Yp/s (OF-BLD-020 §3.1)."""
    from . import artifacts, geneos

    stored = [a for a in artifacts.all_artifacts() if a.tool == geneos.CEILING] if stored is None else stored
    mine = [a for a in stored if _ceiling_of(a, "model") == model_id and _ceiling_of(a, "product") == product
            and isinstance(a.output.get("gPerG"), (int, float))]
    return mine if sugar is None else [a for a in mine if _ceiling_of(a, "substrate") == sugar]


def host_models(product: str, strain: str) -> list[tuple[Any, str, str]]:
    """The geneOS shelf models with a route to `product` whose host is the
    strain ('strain') or of its species ('species'), each with the words
    that say so, as ceiling_check matches a scenario's organism, for one
    named strain (OF-BLD-020 §3.1)."""
    from . import geneos_models, module_stores

    labels, _ = _strain_labels()
    label = labels.get(strain, strain)
    species = module_stores.species_of(label)
    out: list[tuple[Any, str, str]] = []
    for m in geneos_models.SHELF.values():
        if product not in m.products or not m.host:
            continue
        host_label = labels.get(m.host) or m.name
        if m.host == strain:
            out.append((m, "strain", f"{m.id} is a reconstruction of {host_label}, the strain simulated"))
        elif species and module_stores.species_of(host_label) == species:
            out.append((m, "species", f"{m.id} is a reconstruction of {host_label}, and the strain simulated, {label}, "
                                      f"is of its species, {_species_words(species)}: another strain's network bounds "
                                      "it only as far as the two networks agree"))
    return out


def _strain_labels() -> tuple[dict[str, str], dict[str, str]]:
    """Each catalogued strain's label ('Saccharomyces cerevisiae S288C') and
    each chemical set's one species, from the module projection
    (module_stores reads the same): empty in alpha 2.0, unless a test hands
    one in."""
    from . import module_stores

    hosts = module_stores._projection()["geneos"]["hosts"]
    labels = {h["id"]: h["name"] for h in hosts if h.get("id") and h.get("name")}
    by_program: dict[str, set[str]] = {}
    for h in hosts:
        if h.get("program"):
            by_program.setdefault(h["program"], set()).add(module_stores.species_of(h.get("name") or "") or "")
    return labels, {p: next(iter(sp)) for p, sp in by_program.items() if len(sp) == 1 and "" not in sp}


def _species_words(species: str) -> str:
    return species[:1].upper() + species[1:]


def artifact_tool(aid: str | None) -> str | None:
    """The tool of a kept artifact, or None when it is not on file or
    cannot be read: what names a fermOS source as a fit, a forecast or a
    simulation (§8.R)."""
    from . import artifacts

    if not aid:
        return None
    try:
        return artifacts.get(aid).tool
    except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged):
        return None


def _a_reading(inp) -> bool:
    """Whether a scenario's input is bound to a deposition's reading: bound
    as a named value is (`_assume`), its source the reading
    (basis.measurement_source)."""
    from .basis import is_measurement

    return inp.source is not None and is_measurement(inp.source)


def _yield_words(inp, tool: str | None = None) -> str:
    if inp.binding == "records":
        n = len(inp.records)
        return (f"the median of {n} records, with the lowest and the highest" if n >= 3 else
                f"the middle of {n} records, with both" if n == 2 else "one record, held fixed")
    if inp.binding == "assumption" and _a_reading(inp):
        by = inp.source.by if inp.source else None
        return (f"a deposition's reading ({inp.source.id}), deposited by {by or 'nobody named'}, one value held "
                "fixed")
    if inp.binding == "assumption":
        by = inp.source.by if inp.source else None
        return f"a named person's assumption{f' ({by})' if by else ''}, with its low and its high"
    if inp.binding == "artifact":
        aid = inp.source.id if inp.source else None
        if tool == "fermos.simulation":
            # §8.R (findings 4, 11): a simulation's yield is what it
            # achieved, product made over sugar used, one value held fixed.
            return (f"a fermOS simulation's yield achieved{f' ({aid})' if aid else ''}: product made over sugar used to "
                    "harvest, one value held fixed")
        return f"a fermOS fit's Yp/s{f' ({aid})' if aid else ''}, its median with its 5th and 95th percentile"
    return "nothing yet: the yield waits for a record, a named person's assumption or a fermOS fit"


_CHECK_WHAT = {
    "records": "a reviewer should check the basis of each record above it (another sugar counted, the product "
               "measured otherwise, another organism)",
    "assumption": "a reviewer should check what the assumption rests on, and the basis of the yield it was taken from",
    "measurement": "a reviewer should check what the reading measured (the measure it was recorded against, its unit "
                   "and the sugar counted) and the bench's record of it",
    "artifact": "a reviewer should check the basis of the fit's readings (the product and sugar series, and their units)",
    "simulation": "a reviewer should check the sources of the simulation's parameters (its basis names each) and the "
                  "yields it was given",
}


def _row_words(flag: str, binding: str, value_above: bool) -> str:
    if flag == "no-yield":
        return "The scenario's yield waits for a source, so there is nothing to read against this ceiling."
    if flag == "within":
        return "The scenario's yield, its high end included, is at or under this ceiling."
    lead = ("The scenario's yield is above this ceiling" if value_above
            else "The scenario's yield is under this ceiling, but its high end is above it")
    return (f"{lead}. A yield above the most this network makes from this sugar rests on another basis, or is wrong, "
            f"so {_CHECK_WHAT.get(binding, _CHECK_WHAT['records'])}. It is flagged, not clamped: the binding and the "
            "run keep the yield as bound.")


def ceiling_check(scenario_id: str, flowsheet: str | None = None, host: str | None = None,
                  fits: dict[str, str] | None = None, pool=None, overrides: list | None = None):
    """GET /api/proforma/ceiling-check: a scenario's fermenter yield beside
    the newest stored geneOS ceiling of each shelf model of its organism, on
    its flowsheet's sugar (D11). The scenario is one the project keeps, by
    its id, or one not yet saved (ADR-014), by the flowsheet it names
    (flowsheet_of); its yield
    is bound as its page binds it, with the person's overrides and the
    fermOS fits chosen. Refused in words as the binding is. A read: it keeps
    nothing, starts no worker, and changes no binding or run."""
    from . import artifacts, evidence_pool, geneos, geneos_models, module_stores, units
    from .models import CeilingCheck, CeilingRow

    fid = flowsheet_of(scenario_id, flowsheet)
    info = runnable(fid)
    sugar = CEILING_SUGAR.get(fid)
    product = PRODUCTS.get(fid, fid)
    if sugar is None or product not in geneos_models.PRODUCTS:
        raise ScenarioRefused(f"{fid} names no product and sugar a geneOS ceiling is computed for")
    typed = named_values(scenario_id, overrides)
    _check_keys(info, typed)
    pool = pool or evidence_pool.load()
    # The yield as the scenario binds it, each record read as it is (D11).
    inputs = bind_inputs(fid, pool.records, host, typed)
    apply_fits(inputs, fits_beside(fits, typed), fid)
    inp = next((i for i in inputs if i.key == "yield"), None)
    if inp is None:
        raise ScenarioRefused(f"{fid} takes no yield, so no ceiling bounds it")

    def g(v):
        if v is None:
            return None
        try:
            return units.convert(float(v), inp.unit or _G_PER_G, _G_PER_G)
        except (TypeError, ValueError) as e:
            raise ScenarioRefused(f"the yield's unit, {inp.unit}, does not convert to {_G_PER_G}: "
                                  f"{units.explain_refusal(inp.unit or '', _G_PER_G) or e}") from None

    # The organism (the header above says how it is read). Each bound record
    # is read as of its strain's species, else the species its paper's words
    # name, else as of no organism; the line counts each kind, so a few
    # records of a catalogued strain never speak for the rest (§5.R).
    labels, _ = _strain_labels()
    tool = artifact_tool(inp.source.id if inp.source else None) if inp.binding == "artifact" else None
    by_id = getattr(pool, "records_by_id", None) or {r["id"]: r for r in pool.records}
    bound_rows = [by_id.get(r) or {} for r in (inp.recordIds if inp.binding == "records" else [])]
    n = len(bound_rows)
    of_record: dict[str, str | None] = {}  # each bound record's species, as read
    per_strain: dict[str, int] = {}
    named, by_text, unread = 0, 0, 0
    for r in [] if host else bound_rows:
        rid = str(r.get("id", ""))
        if r.get("strainId"):
            named += 1
            per_strain[str(r["strainId"])] = per_strain.get(str(r["strainId"]), 0) + 1
            of_record[rid] = module_stores.species_of(labels.get(str(r["strainId"]), ""))
        elif sp := module_stores.species_of(r.get("organismText") or ""):
            by_text += 1
            of_record[rid] = sp
        else:
            unread += 1
            of_record[rid] = None
    if host:
        strains = [host]
        whose = f"the host the scenario is narrowed to, {labels.get(host, host)}"
        same = "the host the scenario is narrowed to"
        species = {sp for s in strains if (sp := module_stores.species_of(labels.get(s, "")))}
    else:
        strains = sorted(per_strain)
        species = {sp for sp in of_record.values() if sp}
        parts = []
        if named:
            parts.append(f"{f'all {n}' if named == n else f'{named} of the {n}'} records its yield binds name "
                         + ", ".join(f"{labels.get(s, s)}" + (f" ({per_strain[s]})" if len(per_strain) > 1 else "")
                                     for s in strains))
        if by_text:
            parts.append(f"{by_text} name{'s' if by_text == 1 else ''} no catalogued strain and name"
                         f"{'s' if by_text == 1 else ''} the species in the paper's words")
        if unread:
            parts.append(f"{unread} name{'s' if unread == 1 else ''} no catalogued strain and "
                         f"name{'s' if unread == 1 else ''} no organism the tree can read")
        whose = "; ".join(parts)
        same = "a strain the records the yield binds name"
    species_list = sorted(species)
    if not whose:
        whose = "nothing the tree can read: no host is chosen, and the yield binds no record of a catalogued strain"
    organism = whose + (f" ({', '.join(_species_words(s) for s in species_list)})" if species_list else "")

    matched: list[tuple[Any, str, str]] = []
    for m in geneos_models.SHELF.values():
        if product not in m.products or not m.host:
            continue
        label = labels.get(m.host) or m.name
        if m.host in strains:
            count = f" ({per_strain[m.host]} of the {n} records the yield binds name it)" if m.host in per_strain else ""
            matched.append((m, "strain", f"{m.id} is a reconstruction of {label}, {same}{count}"))
            continue
        sp = module_stores.species_of(label)
        if sp and sp in species_list:
            cover = sum(1 for v in of_record.values() if v == sp)
            count = f" ({cover} of the {n} records the yield binds are read as of it)" if n and not host else ""
            matched.append((m, "species", f"{m.id} is a reconstruction of {label}, and the scenario's organism is of "
                                          f"its species, {_species_words(sp)}{count}: another strain's network bounds "
                                          "it only as far as the two networks agree"))

    stored = [a for a in artifacts.all_artifacts() if a.tool == geneos.CEILING]
    product_label = geneos_models.PRODUCTS[product]["label"]
    value, low, high = g(inp.value), g(inp.low), g(inp.high)
    top = high if high is not None else value
    rows: list[CeilingRow] = []
    other_sugars: set[str] = set()
    for m, how, words in matched:
        mine = stored_ceilings(m.id, product, None, stored)
        on = [a for a in mine if _ceiling_of(a, "substrate") == sugar]
        other_sugars |= {str(_ceiling_of(a, "substrate")) for a in mine if a not in on and _ceiling_of(a, "substrate")}
        if not on:
            continue
        newest = on[0]  # all_artifacts lists the newest first
        ceiling = float(newest.output["gPerG"])
        mol = newest.output.get("molPerMol")
        ratio = float(mol) / ceiling if isinstance(mol, (int, float)) and ceiling > 0 else None
        if value is None:
            flag, value_above = "no-yield", False
        else:
            value_above = value > ceiling
            flag = "above" if value_above or (top is not None and top > ceiling) else "within"
        above = [r.id for r in inp.records if (g(r.value) or 0.0) > ceiling] if inp.binding == "records" else []
        conventions = [f"{i.name}: {i.source.note}" for i in newest.inputs
                       if i.name in ("product", "substrate", "uptake") and i.source.note]
        rows.append(CeilingRow(
            modelId=m.id, modelName=m.name, modelBasis=str(_input_named(newest, "model").value), host=m.host,
            match=how, matchWords=words, product=product, substrate=sugar, artifactId=newest.id,
            provenance=newest.provenance, createdAt=newest.createdAt, older=len(on) - 1, ceilingGPerG=ceiling,
            ceilingMolPerMol=float(mol) if isinstance(mol, (int, float)) else None, conventions=conventions,
            yieldGPerG=value, yieldLowGPerG=low, yieldHighGPerG=high,
            yieldMolPerMol=value * ratio if value is not None and ratio is not None else None,
            flag=flag, words=_row_words(flag, "simulation" if tool == "fermos.simulation" else
                                        "measurement" if _a_reading(inp) else inp.binding,
                                        value_above), recordsAbove=above))

    models = [m.id for m, _, _ in matched]
    compute_at = f"/geneos/model?product={product}&substrate={sugar}" + (f"&model={models[0]}" if models else "")
    empty = None
    if not matched:
        empty = (f"No reaction network on geneOS's shelf is of this scenario's organism with a route to "
                 f"{product_label}, so no ceiling bounds this yield. geneOS → Model lists the shelf.")
    elif not rows:
        # A model whose shelf entry feeds it this sugar is sent to compute
        # its ceiling; one fed another sugar is not, since geneOS computes no
        # ceiling on a sugar a network does not take up (RehMBEL1391 takes up
        # no glucose), and what is on file for it is named (§5.R).
        fed = [m.id for m, _, _ in matched if m.feed == sugar]
        other = [m for m, _, _ in matched if m.feed != sugar]
        said = []
        if fed:
            said.append(f"No geneOS ceiling for {product_label} on {sugar} is on file for {', '.join(fed)}. One is "
                        f"computed in geneOS → Model: choose {product_label}, {sugar} and the model, and the ceiling is kept.")
        for m in other:
            kept = [a.id for a in stored if _ceiling_of(a, "model") == m.id and _ceiling_of(a, "product") == product
                    and _ceiling_of(a, "substrate") == m.feed]
            said.append(
                f"No geneOS ceiling for {product_label} on {sugar} is on file for {m.id}, and geneOS may never keep one: "
                f"it computes a ceiling only on a sugar the network takes up, and its shelf entry feeds it {m.feed}"
                + (f"; its ceiling on {m.feed} is on file ({', '.join(kept)}) and bounds no yield on {sugar}" if kept else "")
                + f". geneOS → Model on {m.id} and {sugar} says whether the network takes up {sugar}.")
        empty = " ".join(said)
    notes = [CEILING_KEPT]
    return CeilingCheck(
        scenarioId=scenario_id, flowsheet=fid, product=product, substrate=sugar,
        sugarWords=f"the flowsheet's feed is {sugar}",
        host=host, strains=strains, species=species_list, organismWords=organism, models=models,
        yieldBinding=inp.binding, yieldValue=inp.value, yieldLow=inp.low, yieldHigh=inp.high, yieldUnit=inp.unit,
        yieldSource=inp.source, yieldRecords=len(inp.records), yieldWords=_yield_words(inp, tool), yieldTool=tool,
        rows=rows,
        flagged=any(r.flag == "above" for r in rows), empty=empty, computeAt=compute_at,
        otherSugars=sorted(other_sugars), notes=notes)
