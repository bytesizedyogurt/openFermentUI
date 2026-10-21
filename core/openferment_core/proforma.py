"""Proforma on the service's side (OF-BLD-014 §8.1).

One `SimWorker` runs BioSTEAM in its own process. Its cold start takes about
forty seconds, so the worker starts on first use, or with the service when
`OPENFERMENT_WARM_PROFORMA=1`, and `status()` says where it is: `cold`,
`starting`, `ready` or `failed`, so the screen can say the simulator is
starting rather than look stuck.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import threading
from typing import Any, Literal

from .flowsheets import shelf as _shelf
from .workers import SimWorker, WorkerCrashed, WorkerError, WorkerTimeout

# A cold import plus a first build; a setting, not a measurement (B.3 measured
# the import at forty seconds).
START_TIMEOUT_S = 240.0
CALL_TIMEOUT_S = 600.0

Status = Literal["cold", "starting", "ready", "failed"]

_WORKER: SimWorker | None = None
_STATE: dict[str, Any] = {"status": "cold", "error": None}
_LOCK = threading.Lock()
# Set when a start in progress has settled, ready or failed (OF-BLD-019
# §7.R): a request arriving while another starts the worker waits on it.
_SETTLED = threading.Event()


def worker() -> SimWorker:
    global _WORKER
    with _LOCK:
        if _WORKER is None:
            _WORKER = SimWorker("openferment_core.workers.proforma_worker", timeout_s=CALL_TIMEOUT_S)
        return _WORKER


def status() -> dict[str, Any]:
    return dict(_STATE)


def _warm() -> None:
    try:
        worker().ping(timeout_s=START_TIMEOUT_S)
        _STATE.update(status="ready", error=None)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        _STATE.update(status="failed", error=str(e) or type(e).__name__)
    finally:
        _SETTLED.set()


def start(background: bool = True) -> dict[str, Any]:
    """Start the worker if it is cold or failed; return the status."""
    with _LOCK:
        if _STATE["status"] in ("cold", "failed"):
            _STATE.update(status="starting", error=None)
            _SETTLED.clear()
            go = True
        else:
            go = False
    if go:
        if background:
            threading.Thread(target=_warm, name="proforma-warm", daemon=True).start()
        else:
            _warm()
    return status()


def call(op: str, args: dict[str, Any]) -> Any:
    """A request on the warm worker; the first one starts it and waits, and
    one arriving while another starts it waits for that start, as long as
    a start may take (OF-BLD-019 §7.R), then says in words why it cannot
    run: the start's own error, or that the simulator is still starting."""
    if _STATE["status"] != "ready":
        start(background=False)
    if _STATE["status"] == "starting":
        _SETTLED.wait(timeout=START_TIMEOUT_S)
    if _STATE["status"] == "starting":
        raise WorkerError("the Proforma simulator is still starting; try again in a minute")
    if _STATE["status"] != "ready":
        raise WorkerError(f"the Proforma simulator could not start: {_STATE['error'] or 'it gave no reason'}")
    return worker().call(op, args)


def warm_on_start() -> bool:
    return os.environ.get("OPENFERMENT_WARM_PROFORMA", "").strip() == "1"


# ── The benchmark (§8.2) ────────────────────────────────────────────────

BENCHMARK = "proforma_benchmark"
BENCHMARK_PACKAGE = "biorefineries.cornstover"


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


def benchmark_inputs() -> list:
    from .models import BasisInput, BasisSource

    ref = f"{BENCHMARK_PACKAGE}@{_installed('biorefineries')}"
    return [
        BasisInput(name="model", value="biorefineries.cornstover.Biorefinery", unit="", source=BasisSource(
            kind="model", id=ref,
            note="the corn stover ethanol biorefinery built to NREL/TP-5100-47764, with every setting the package's own")),
        BasisInput(name="simulator", value=f"biosteam {_installed('biosteam')}", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{_installed('biosteam')}", note="the process simulator the package runs on")),
        BasisInput(name="gallon", value="ethanol_density_kggal", unit="kg gal-1", source=BasisSource(
            kind="model", id=ref, note="the package's own ethanol density per gallon converts its price per kilogram")),
    ]


def _run_benchmark(inputs, seed):
    return call("benchmark", {})


def _register() -> None:
    from . import artifacts

    artifacts.register(BENCHMARK, f"{BENCHMARK_PACKAGE}@{_installed('biorefineries')}", _run_benchmark)


def _register_lazy() -> None:
    from . import artifacts

    artifacts.register_lazy(BENCHMARK, _register)


_register_lazy()


def stored_benchmark():
    """The benchmark this installation ran, or None. A read: it runs nothing."""
    from . import artifacts

    reg = artifacts.registered(BENCHMARK)
    try:
        return artifacts.get(artifacts.artifact_id(reg.tool, reg.version, benchmark_inputs()))
    except artifacts.ArtifactNotFound:
        return None


def run_benchmark():
    from . import artifacts

    return artifacts.compute(BENCHMARK, benchmark_inputs())


def benchmark_evidence(art):
    """The benchmark run as one Evidence: the package's minimum ethanol
    selling price per gallon, as the stored artifact holds it."""
    from . import artifacts
    from .models import Evidence

    return Evidence(
        id=art.id,
        label="Minimum ethanol selling price, the NREL 2011 corn stover design as biorefineries.cornstover builds it",
        value=art.output["mespUsdPerGal"], unit="USD gal⁻¹",
        provenance=art.provenance, basis=artifacts.basis_of(art), figure=None)


# ── Reference biorefineries (OF-BLD-019 §2.2, D3) ───────────────────────
#
# A published biorefinery on the shelf (`reference: True`) runs whole on its
# package's own defaults in the worker's `reference` op and is kept as one
# `proforma.reference` artifact: the package's result, the quantities its
# own test asserts as this installation computed them (`measured`), its
# defaults read back (`readBack`), every table a `proforma.run` artifact
# holds (so `tables_of` reads it too), and the test's values beside them
# (`regression`, `checks`), parsed from the installed test file. Every input
# names the package, the simulator or a stated convention, so the run is
# `computed`, as the benchmark is. The benchmark's own endpoints and
# artifact (§8.2) are unchanged; the corn stover plant answers here too.

REFERENCE = "proforma.reference"
# 2 (OF-BLD-019 §2.R): the basis says whether the diagram is drawn, and the
# plant builds with fresh chemical caches.
REFERENCE_VERSION = "reference run 2"
# The significant digits a reference run keeps: BioSTEAM sums a set of units
# in an order that moves the last digits from one build to the next, so the
# run keeps fewer, and a replay compares the plant (a precision, stated in
# every basis).
REFERENCE_DIGITS = 10
# numpy.allclose's own absolute tolerance, which the package's test uses
# beside its rtol: a check holds when |measured − package| ≤ ATOL + rtol·|package|.
ALLCLOSE_ATOL = 1e-08


def _reference_info(flowsheet_id: str):
    try:
        info = _shelf.info(flowsheet_id)
    except _shelf.NotOnShelf as e:
        raise ScenarioRefused(str(e)) from None
    if not info.reference:
        refs = ", ".join(f.id for f in _shelf.SHELF.values() if f.reference)
        raise ScenarioRefused(f"{flowsheet_id} is not a reference biorefinery: it runs on its inputs as a scenario; "
                              f"the references are {refs}")
    return info


def reference_inputs(flowsheet_id: str) -> list:
    """The basis of a reference run: the package's plant, the simulator, the
    settings it builds under, each default the shelf lists (its value read
    back after the run), what the run changes about the package to run it,
    and the digits it keeps."""
    from .models import BasisInput, BasisSource

    info = _reference_info(flowsheet_id)
    pkg = f"{_shelf.REFERENCE_MODULES[flowsheet_id]}@{_installed('biorefineries')}"
    bst_v, tmo_v = _installed("biosteam"), _installed("thermosteam")
    out = [
        BasisInput(name="flowsheet", value=flowsheet_id, unit="", source=BasisSource(
            kind="model", id=pkg, note=f"{info.title}, every setting the package's own")),
        BasisInput(name="simulator", value=f"biosteam {bst_v}", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{bst_v}", note="the process simulator the package runs on")),
        BasisInput(name="thermodynamics", value=f"thermosteam {tmo_v}", unit="", source=BasisSource(
            kind="model", id=f"thermosteam@{tmo_v}", note="BioSTEAM's property engine")),
        BasisInput(name="settings", value="bst.process_tools.default()", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{bst_v}",
            note="BioSTEAM's default utilities and plant cost index before the plant builds, as the package's own "
                 "test builds it (default_settings, biorefineries/tests/test_biorefineries.py); the plant then sets "
                 "its own, and the worker puts back what it held before")),
    ]
    out += [BasisInput(name=i.key, value="the package's default", unit=i.unit,
                       source=BasisSource(kind="model", id=pkg, note=i.note)) for i in info.inputs]
    out += [BasisInput(name="compatibility", value=what, unit="", source=BasisSource(kind="convention", note=why))
            for what, why in _shelf.REFERENCE_COMPAT.get(flowsheet_id, [])]
    out.append(BasisInput(name="precision", value=f"{REFERENCE_DIGITS} significant digits", unit="", source=BasisSource(
        kind="convention", note="every number the run keeps is rounded so: BioSTEAM sums a set of units in an order "
                                "that moves the last digits from one build to the next, and a replay compares the plant")))
    out.append(diagram_input())
    return out


def regression_checks(regression, measured: dict) -> list:
    """Each of the package test's values beside what this installation
    computed, held as the test holds it (numpy.allclose with the test's rtol)."""
    from .models import RegressionCheck

    out = []
    for v in regression.values:
        m = measured.get(v.expression)
        m = float(m) if isinstance(m, (int, float)) else None
        within = m is not None and abs(m - v.package) <= ALLCLOSE_ATOL + v.rtol * abs(v.package)
        rel = abs(m - v.package) / abs(v.package) if m is not None and v.package != 0 else None
        out.append(RegressionCheck(expression=v.expression, label=v.label, unit=v.unit, measured=m, package=v.package,
                                   rtol=v.rtol, relDiff=rel, within=within))
    return out


def _run_reference(inputs, seed):
    """One reference run, from its basis alone: the worker builds the plant
    and reads it; the package test's values are set beside what it read."""
    flowsheet = str(_named(inputs, "flowsheet"))
    digits = int(str(_named(inputs, "precision") or REFERENCE_DIGITS).split()[0])
    out = call("reference", {"flowsheet": flowsheet, "digits": digits, "diagram": _draws(inputs)})
    regression = _shelf.package_regression(flowsheet)
    out["regression"] = regression.model_dump(mode="json") if regression else None
    out["checks"] = ([c.model_dump(mode="json") for c in regression_checks(regression, out.get("measured") or {})]
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


def _flowsheet_of(art) -> str | None:
    return next((str(i.value) for i in art.inputs if i.name == "flowsheet"), None)


def stored_reference(flowsheet_id: str):
    """The newest stored reference run of a reference flowsheet, or None. A
    read: it runs nothing and starts no simulator."""
    from . import artifacts

    _reference_info(flowsheet_id)
    return next((a for a in artifacts.all_artifacts() if a.tool == REFERENCE and _flowsheet_of(a) == flowsheet_id), None)


def run_reference(flowsheet_id: str):
    """Run a reference biorefinery (or return the stored run of the same
    basis) and keep it as one `proforma.reference` artifact."""
    from . import artifacts

    return artifacts.compute(REFERENCE, reference_inputs(flowsheet_id))


def reference(flowsheet_id: str, art=None):
    """What GET and POST /api/proforma/reference/{id} answer: the shelf's
    entry, the run (the newest stored, unless one is given), the package
    test's values and the simulator's status."""
    from .models import ProformaReference

    info = _reference_info(flowsheet_id)
    art = art if art is not None else stored_reference(flowsheet_id)
    return ProformaReference(flowsheet=info, artifact=art, regression=_shelf.package_regression(flowsheet_id),
                             simulator=status())


# ── The PHA scenario (§8.3) ─────────────────────────────────────────────
#
# Its inputs bind to records, or to an assumption a named person typed; the
# run is one artifact whose basis lists every record, assumption, model
# setting and convention it used. This module does the binding and the
# statistics; the worker runs BioSTEAM.

RUN = "proforma.run"
SCENARIO_ID = "sc-pha-1"
FLOWSHEET = "pha_sugar_v0"
# The samples a run draws unless its request says otherwise, and the most it
# may ask for (OF-BLD-019 D7): settings, not measurements.
SAMPLES = 500
MAX_SAMPLES = 2000
GRID_KEYS = ("titre", "yield", "sugarPrice")
GRID_POINTS = 5
HISTOGRAM_BINS = 20
QUANTILES = (5, 25, 50, 75, 95)
# The PHA draft's words live on the shelf (flowsheets/shelf.py), pure data
# the service reads without BioSTEAM.
PRICE_BASIS = _shelf.PHA_PRICE_BASIS
LEAVES_OUT = _shelf.PHA_LEAVES_OUT

# key: (label, unit, field, the field's canonical unit, scale into the flowsheet's unit)
BOUND = {
    "titre": ("PHA titre at harvest", "g L-1", "pha_titre", "g L⁻¹", 1.0),
    "yield": ("PHA yield on sugar", "g g-1", "pha_yield_substrate", "g g⁻¹", 1.0),
    "content": ("PHA share of dry cell mass", "g g-1", "pha_content_cdw", "% CDW", 0.01),
    "productivity": ("PHA volumetric productivity", "g L-1 h-1", "pha_productivity", "g L⁻¹ h⁻¹", 1.0),
}
ASSUMED = {
    "recovery": ("solids recovered at harvest", ""),
    "sugarPrice": ("price of fermentable sugar", "USD kg-1"),
    "sugarFeed": ("sugar fed", "kg h-1"),
}
KEYS = (*BOUND, *ASSUMED)
SUGARS = frozenset({"glucose", "xylose", "fructose", "mixed-sugars", "hydrolysate"})
SINGLE = "single source: held fixed in sampling"


class ScenarioRefused(ValueError):
    """The scenario cannot run as asked, in words."""


def _thread_p(paper_id: str) -> bool:
    import re

    return re.fullmatch(r"P\d+\w*", paper_id or "") is not None


def _exclusion(r: dict) -> str | None:
    """`aggregateExclusion` in Python, over a pool record."""
    if r.get("status") == "rejected":
        return "rejected"
    if r.get("provenance") == "industry-estimate":
        return "industry-estimate"
    if r.get("provenance") == "computed":
        return "computed"
    if r.get("primary") is False:
        return "not-primary"
    return None


def yield_cap() -> tuple[float, str] | None:
    """The highest glucose ceiling on the geneOS shelf, from its artifact."""
    from . import artifacts, geneos

    best: tuple[float, str] | None = None
    for a in artifacts.all_artifacts():
        if a.tool != geneos.CEILING or a.provenance == "demo":
            continue
        named = {i.name: i.value for i in a.inputs}
        if named.get("product") != "phb" or named.get("substrate") != "glucose":
            continue
        g = a.output.get("gPerG")
        if isinstance(g, (int, float)) and (best is None or g > best[0]):
            best = (float(g), a.id)
    return best


def bind(records: list[dict], host: str | None = None, assumptions: list | None = None,
         cap: tuple[float, str] | None = None) -> list:
    """Every input of the scenario, bound to records or an assumption."""
    from . import units, validate
    from .models import BoundRecord, ScenarioInput

    given = {a.key: a for a in assumptions or []}
    out = []
    for key, (label, unit, field_id, canonical, scale) in BOUND.items():
        inp = ScenarioInput(key=key, label=label, unit=unit, binding="waiting")
        bound: list[BoundRecord] = []
        refused: str | None = None
        for r in records:
            if r.get("field") != field_id or not _thread_p(r.get("paperId", "")) or _exclusion(r):
                continue
            if host and r.get("strainId") != host:
                continue
            carbon = r.get("carbonSource")
            if not carbon:
                inp.leftOutNoCarbon += 1
                continue
            if validate.carbon_source_id(carbon) not in SUGARS:
                inp.leftOutOtherCarbon += 1
                continue
            try:
                v = units.convert(float(r["value"]), r.get("unit") or canonical, canonical) * scale
            except (TypeError, ValueError) as e:
                refused = f"record {r['id']}: {units.explain_refusal(r.get('unit') or '', canonical) or e}"
                break
            bound.append(BoundRecord(id=r["id"], paperId=r["paperId"], value=v,
                                     organism=r.get("organismText") or r.get("strainId"), carbonSource=carbon,
                                     provenance=r.get("provenance") or "unverified"))
        if refused:
            # The records cannot be used; a person's assumption still can (§8.R).
            inp.flags.append(f"the binding stopped: {refused}")
            if key in given:
                _assume(inp, given[key])
            out.append(inp)
            continue
        if key in given:
            # OF-BLD-020 D3: a named person's value wins over the records,
            # and the input says how many it stands in place of.
            _in_place_of(inp, bound)
            _assume(inp, given[key])
            out.append(inp)
            continue
        if key == "yield" and cap is not None:
            clipped = [b for b in bound if b.value > cap[0]]
            for b in clipped:
                b.value = cap[0]
            if clipped:
                inp.flags.append(f"{len(clipped)} above the highest glucose ceiling on the geneOS shelf, clipped to it")
        if bound:
            _settle(inp, bound, field_id)
        out.append(inp)
    for key, (label, unit) in ASSUMED.items():
        inp = ScenarioInput(key=key, label=label, unit=unit, binding="waiting")
        if key in given:
            _assume(inp, given[key])
        out.append(inp)
    return out


def _settle(inp, bound: list, field_id: str) -> None:
    """An input bound to records: their median with their range and a
    triangular draw from three on, a pair drawn uniform, one held fixed and
    flagged (§8.3)."""
    import statistics

    from .models import BasisSource

    vals = sorted(b.value for b in bound)
    inp.binding = "records"
    inp.records, inp.recordIds = bound, [b.id for b in bound]
    inp.source = BasisSource(kind="record", note=f"{len(bound)} record{'s' if len(bound) != 1 else ''} of {field_id}")
    if len(vals) >= 3 and vals[0] != vals[-1]:
        inp.value, inp.low, inp.high, inp.sampling = statistics.median(vals), vals[0], vals[-1], "triangular"
    elif len(vals) == 2 and vals[0] != vals[1]:
        inp.value, inp.low, inp.high, inp.sampling = (vals[0] + vals[1]) / 2, vals[0], vals[1], "uniform"
    else:
        inp.value = inp.low = inp.high = vals[0]
        inp.sampling = "fixed"
        inp.flags.append(SINGLE if len(vals) == 1 else "every bound record gives the same value: held fixed in sampling")


def _in_place_of(inp, bound: list) -> None:
    """Say how many bound records a person's value stands in place of
    (OF-BLD-020 D3), as a fermOS fit chosen in their place says it."""
    if bound:
        inp.flags.append(f"chosen in place of the {len(bound)} record{'s' if len(bound) != 1 else ''} it bound")


def _assume(inp, a) -> None:
    from .basis import assumption_source
    from .threadp import reviewer_refusal

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
    inp.source = assumption_source(a.by, a.at, a.note)


def scenario(host: str | None = None, assumptions: list | None = None, pool=None):
    from . import evidence_pool
    from .models import ProformaScenarioInfo

    # A person opened this scenario by id, so its thread P records bind
    # whatever the program switch says; the screen decides whether an
    # archived scenario shows (OF-BLD-016 §2.3). A tool passes its own pool.
    pool = pool or evidence_pool.load(include_archived=True)
    inputs = bind(pool.records, host, assumptions, yield_cap())
    hosts = sorted({r.get("strainId") for r in pool.records
                    if r.get("strainId") and _thread_p(r.get("paperId", "")) and r.get("field") in {b[2] for b in BOUND.values()}})
    return ProformaScenarioInfo(
        id=SCENARIO_ID, name="PHA from cellulosic sugar — draft flowsheet", product="phb", flowsheet=FLOWSHEET,
        host=host, hosts=hosts, inputs=inputs, waiting=[i.key for i in inputs if i.binding == "waiting"],
        leavesOut=LEAVES_OUT, priceBasis=PRICE_BASIS)


# ── A person's overrides (OF-BLD-020 §2.2, D3) ─────────────────────────
#
# The parameter panel keeps a person's change to a scenario's input as an
# Override of scope `proforma:<scenario id>`, in the browser that typed it,
# and a run, a binding or a ceiling check carries it. Each is laid on as the
# named assumption it is: it wins over the records and over a fermOS fit
# for its input, the input says how many records it stands in place of, and
# the basis names the person (basis.assumption_source), so the run is
# `demo`. The older `assumptions` field is read the same way for one
# release. The basis says which field it read: a run that read overrides
# carries `assumptions read from`; one that read the older field alone
# carries nothing new, so its basis, and its artifact id, are what they were
# before the panel. The service keeps none.

ASSUMPTIONS_READ = "assumptions read from"
READ_WORDS = {
    (True, False): "overrides",
    (True, True): "overrides, and assumptions, the older field, read as overrides for one release",
}


def proforma_scope(scenario_id: str) -> str:
    """The parameter scope of a scenario (params.parse_scope's proforma form)."""
    return f"proforma:{scenario_id}"


def named_values(scenario_id: str | None, overrides: list | None = None,
                 assumptions: list | None = None) -> tuple[list, str | None]:
    """A person's values for a scenario's inputs, as the binding lays them on:
    each Override of the scenario's scope, and the older `assumptions` field,
    as `InputAssumption`s; and the words the basis says it read (None when
    it read no override: the older field alone, or nothing, is what every
    run before the panel read). With no scenario id (GET /api/proforma/bind) every
    override names one proforma scope. Refused in words: an override of
    another scope, a value in words, and an input named twice."""
    from .models import InputAssumption

    over = list(overrides or [])
    old = list(assumptions or [])
    scopes = sorted({o.scope for o in over})
    if scenario_id is not None:
        stray = [sc for sc in scopes if sc != proforma_scope(scenario_id)]
        if stray:
            raise ScenarioRefused(f"an override names the scope it changes, and these were sent for "
                                  f"{proforma_scope(scenario_id)}: {', '.join(stray)}")
    elif len(scopes) > 1 or (scopes and not scopes[0].startswith("proforma:")):
        raise ScenarioRefused(f"the overrides of one binding name one scenario's scope, proforma:<scenario id>; "
                              f"these name {', '.join(scopes)}")
    out: dict[str, InputAssumption] = {}
    for o in over:
        if isinstance(o.value, bool) or not isinstance(o.value, (int, float)):
            raise ScenarioRefused(f"the override of {o.key} takes a number, not words")
        if o.key in out:
            raise ScenarioRefused(f"two overrides of {o.key}: one person's value an input")
        value = float(o.value)
        out[o.key] = InputAssumption(key=o.key, value=value, low=value if o.low is None else o.low,
                                     high=value if o.high is None else o.high, by=o.by, at=o.at, note=o.note)
    from_overrides = set(out)
    for a in old:
        if a.key in from_overrides:
            raise ScenarioRefused(f"{a.key} is named in both overrides and assumptions, the older field: send it once, "
                                  "as an override")
        out[a.key] = a  # as before the panel, the last of the older field's values for a key stands
    words = READ_WORDS.get((bool(over), bool(old)))
    return list(out.values()), words


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


def assumptions_read(words: str | None) -> list:
    """The basis input that says a run's named values were read from the
    panel's overrides (OF-BLD-020 §2.2): none for a run that carries no
    override, so a run with none keeps the basis, and the artifact id, it
    had before the panel."""
    from .models import BasisInput, BasisSource

    if not words:
        return []
    return [BasisInput(name=ASSUMPTIONS_READ, value=words, unit="", source=BasisSource(
        kind="convention", note="where the named persons' values in this basis came from: the parameter panel's "
                                "overrides, and any the older assumptions field gave, which the service reads as overrides "
                                "for one release; a basis without this input read the older field alone"))]


def basis_inputs(inputs: list, cap: tuple[float, str] | None, flowsheet: str = FLOWSHEET,
                 samples: int = SAMPLES, scenario_id: str | None = None, fitted: list | None = None) -> list:
    """The run's basis: the flowsheet, the scenario it belongs to, what it
    borrows from a package, the samples, and every record, assumption, the
    cap and the conventions; an input a fermOS fit feeds names the fit's
    artifact (OF-BLD-019 §5.1), and `fitted` adds what else the fit gave
    (the batch time a productivity is the titre over)."""
    from .models import BasisInput, BasisSource

    info = _shelf.info(flowsheet, allow_toy=True)
    if flowsheet == FLOWSHEET:
        note = "draft v0: fermentation, harvest and drying only; " + "; ".join(LEAVES_OUT) + " left out"
    else:
        note = f"{info.title}: {info.description}"
    out = [BasisInput(name="flowsheet", value=flowsheet, unit="", source=BasisSource(kind="convention", note=note))]
    if scenario_id:
        # OF-BLD-019 §2.3 (e): the scenario a run belongs to, as words; pureOS
        # reads it ("a basis input named scenario wins"). A convention, so it
        # leaves the provenance as the records and assumptions make it.
        out.append(BasisInput(name="scenario", value=scenario_id, unit="", source=BasisSource(
            kind="convention", note="the scenario this run belongs to")))
    if flowsheet == FLOWSHEET:
        out.append(BasisInput(
            name="finance and properties", value=f"biorefineries.cornstover@{_installed('biorefineries')}", unit="",
            source=BasisSource(kind="model", id=f"biorefineries.cornstover@{_installed('biorefineries')}",
                               note="create_tea and create_chemicals; PHB borrows Lignin's volume and heat capacity")))
    elif flowsheet == ETHANOL:
        out += ethanol_basis()
    if info.priceOutput:
        out.append(utility_input())
    out.append(diagram_input())
    out.append(BasisInput(name="samples", value=f"{samples} Latin hypercube", unit="", source=BasisSource(kind="convention")))
    if cap is not None:
        out.append(BasisInput(name="yield cap", value=cap[0], unit="g g-1", source=BasisSource(kind="artifact", id=cap[1])))
    for inp in inputs:
        if inp.binding == "records":
            out += [BasisInput(name=f"{inp.key} record", value=r.value, unit=inp.unit,
                               source=BasisSource(kind="record", id=r.id)) for r in inp.records]
            if inp.key in BOUND and BOUND[inp.key][4] != 1.0:
                out.append(BasisInput(name=f"{inp.key} scale", value=BOUND[inp.key][4], unit="", source=BasisSource(
                    kind="convention", note=f"{BOUND[inp.key][3]} to a share")))
        elif inp.binding == "assumption":
            for part, v in (("", inp.value), (" low", inp.low), (" high", inp.high)):
                out.append(BasisInput(name=f"{inp.key}{part}", value=v, unit=inp.unit, source=inp.source))
        elif inp.binding == "artifact":
            for part, v in (("", inp.value), (" low", inp.low), (" high", inp.high)):
                out.append(BasisInput(name=f"{inp.key} fit{part}", value=v, unit=inp.unit, source=inp.source))
    out += fitted or []
    return out


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
    assumed: dict[str, dict[str, float]] = {}
    fitted: dict[str, dict[str, float]] = {}
    cap = next((float(i.value) for i in inputs if i.name == "yield cap"), None)
    for i in inputs:
        named = _FIT_NAME.fullmatch(i.name)
        if named and i.source.kind == "artifact":
            fitted.setdefault(named[1], {})[named[2] or "value"] = float(i.value)
        elif i.name.endswith(" record"):
            v = float(i.value)
            key = i.name.removesuffix(" record")
            vals.setdefault(key, []).append(min(v, cap) if key == "yield" and cap is not None else v)
        elif i.source.kind == "assumption":
            key, _, part = i.name.partition(" ")
            assumed.setdefault(key, {})[part or "value"] = float(i.value)
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
        kinds[key] = "assumption"
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

    flowsheet = str(_named(inputs, "flowsheet") or FLOWSHEET)
    info = _shelf.info(flowsheet, allow_toy=True)
    price_key = info.priceOutput
    specs, base, kinds = _specs(inputs)
    axes = {}
    for k in info.gridInputs:
        s = specs[k]
        axes[k] = [s["value"]] if s["kind"] == "fixed" else [float(v) for v in np.linspace(s["low"], s["high"], GRID_POINTS)]
    r = call("run", {"flowsheet": flowsheet, "base": base, "specs": specs, "samples": _samples_of(inputs),
                     "seed": int(seed or 0), "axes": axes or None, "diagram": _draws(inputs)})
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


def run(req, pool=None):
    """Bind, refuse what waits for a source, and run once per basis. The run
    is one `proforma.run` artifact holding the price, the sensitivity and the
    base case's tables (D1); this reads them back from it."""
    from . import artifacts, evidence_pool
    from .models import ProformaGrid, ProformaRunResult

    # OF-BLD-019 §2.3 (d): a seed scenario by its id, or a scenario a person
    # made here by the shelf flowsheet it names; anything else is refused.
    flowsheet = flowsheet_of(req.scenarioId, req.flowsheet)
    info = _shelf.info(flowsheet)
    _check_samples(req.samples)
    _check_seed(req.seed)
    # A run is a caller a person started by id: its records bind whatever the
    # program switch says (OF-BLD-016, "what keeps everything").
    # OF-BLD-020 §2.2 (D3): a person's overrides, and the older assumptions
    # field read the same way for one release, each a named assumption that
    # wins over the records and any fit for its input.
    typed, read = named_values(req.scenarioId, req.overrides, req.assumptions)
    _check_keys(info, typed)
    pool = pool or evidence_pool.load(include_archived=True)
    if flowsheet == FLOWSHEET:
        cap = yield_cap()
        inputs = bind(pool.records, req.host, typed, cap)
    else:
        cap = None
        inputs = bind_inputs(flowsheet, pool.records, req.host, typed)
    # OF-BLD-019 §5.1 (D10): the fermOS fits a person chose, each computed
    # from its artifact; one that cannot feed its input is refused in words.
    # An input a person's value overrides takes no fit (D3).
    fitted = apply_fits(inputs, fits_beside(req.fits, typed), flowsheet)
    waiting = [i.key for i in inputs if i.binding == "waiting"]
    if waiting:
        raise ScenarioRefused("these inputs wait for a source, a record or a named person's assumption: " + ", ".join(waiting))
    art = artifacts.compute(RUN, basis_inputs(inputs, cap, flowsheet, req.samples, scenario_id=req.scenarioId,
                                              fitted=fitted) + assumptions_read(read),
                            records_by_id=pool.records_by_id, seed=req.seed)
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
    return its one `proforma.run` artifact. The toy is refused unless the
    caller is a test or a fixture and says `allow_toy`; a reference
    biorefinery runs whole through its own reference run, not here."""
    from . import artifacts
    from .models import ScenarioInput

    try:
        info = _shelf.info(flowsheet, allow_toy=allow_toy)
    except _shelf.NotOnShelf as e:
        raise ScenarioRefused(str(e)) from None
    if info.reference:
        raise ScenarioRefused(f"{flowsheet} is a reference biorefinery: it runs whole on its package's own defaults")
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
    return artifacts.compute(RUN, basis_inputs(inputs, None, flowsheet, samples, scenario_id=scenario_id),
                             records_by_id={}, seed=seed)


def tables_of(art):
    """The tables a `proforma.run` artifact holds, as every reader reads
    them (D1: Proforma, pureOS, fermOS, Postdoc, the MCP server); a
    `proforma.reference` artifact (§2.2) holds the same keys and reads the
    same way. A run stored before §2.1 reads with empty tables and its
    flowsheet from its basis."""
    from .models import ProformaTables

    o = art.output
    fields = {k: o[k] for k in ProformaTables.model_fields if k in o and o[k] is not None}
    fields.setdefault("flowsheet", next((str(i.value) for i in art.inputs if i.name == "flowsheet"), None))
    return ProformaTables.model_validate(fields)


def shelf(include_archived: bool = False) -> list:
    """The shelf (flowsheets/shelf.py), for `GET /api/proforma/shelf`. A
    flowsheet of an archived program is left out unless the caller asks for
    archived programs (OF-BLD-016 §2.R); the toy is never on it."""
    from . import programs

    out = []
    for info in _shelf.SHELF.values():
        try:
            hidden = programs.hides(info.program, include_archived)
        except FileNotFoundError:  # no corpus exported here: nothing is known to be archived
            hidden = False
        if not hidden:
            out.append(info)
    return out


def evidence_of(art):
    """A run as one Evidence: the median price with the 5th to 95th percentile."""
    from . import artifacts
    from .models import Evidence, Range

    q = art.output["quantiles"]
    if not q:
        raise ScenarioRefused("this run has no sample the flowsheet could hold, so it has no price to cite")
    # The scenario and flowsheet the run's basis names (OF-BLD-019 §2.3); a
    # run stored before the basis named its scenario is sc-pha-1's.
    flowsheet = str(_named(art.inputs, "flowsheet") or FLOWSHEET)
    scenario_id = _named(art.inputs, "scenario") or SCENARIO_ID
    info = _shelf.info(flowsheet, allow_toy=True)
    return Evidence(
        id=art.id, label=f"Minimum selling price, {scenario_id} ({info.title})",
        value=q.get("p50", float("nan")), unit=info.priceBasis or PRICE_BASIS,
        interval=Range(low=q["p5"], high=q["p95"]) if q else None,
        provenance=art.provenance, basis=artifacts.basis_of(art), figure="distribution")


def latest_run(scenario_id: str = SCENARIO_ID):
    """The most recent stored run of a scenario, or None: a run whose basis
    names the scenario, or one stored before a basis named its scenario
    whose flowsheet is the seed scenario's (OF-BLD-019 §2.3)."""
    from . import artifacts

    seeded = {s["id"]: s.get("modelId") for s in seed_scenarios()}.get(scenario_id)

    def belongs(a) -> bool:
        named = _named(a.inputs, "scenario")
        if named:
            return named == scenario_id
        return seeded is not None and str(_named(a.inputs, "flowsheet") or FLOWSHEET) == seeded

    runs = [a for a in artifacts.all_artifacts() if a.tool == RUN and belongs(a)]
    return max(runs, key=lambda a: a.createdAt) if runs else None


# ── Glucose to ethanol, and every scenario the shelf can run (OF-BLD-019 §2.3) ──
#
# The yeast program's flowsheet of our own binds by the shelf alone: each
# process input to the records of the fields its shelf entry names, on its
# program's papers, through the aggregate gate and units.py, as `bind` does
# for thread P. The seed's BioSTEAM scenarios (src/data/scenarios.ts, read
# through modules.json) each name the shelf flowsheet they run; a scenario a
# person makes in the browser (D6) names one too, and binds and runs the
# same way. Rule 1: no value here; the stand-ins live in the tests.

ETHANOL = "ethanol_glucose_v0"
YEAST_SCENARIO_ID = "sc-yeast-1"
# The carbon source a record must name to bind a process input of a
# flowsheet `bind_inputs` binds: the flowsheet's own feed. A record naming
# none is left out and counted, as one naming another feed is.
FEED_CARBON: dict[str, frozenset[str]] = {ETHANOL: frozenset({"glucose"})}
# What a bound scenario says it makes, by flowsheet.
PRODUCTS = {FLOWSHEET: "phb", ETHANOL: "ethanol"}


def seed_scenarios() -> list[dict]:
    """The seed's BioSTEAM scenarios as `export:corpus` projects them into
    modules.json, each naming the non-reference shelf flowsheet it runs (its
    `modelId`). With no projection here, sc-pha-1 alone, the one scenario
    this module knew before the shelf."""
    from . import module_stores

    try:
        rows = list(module_stores._projection()["proforma"]["scenarios"])
    except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
        rows = [{"id": SCENARIO_ID, "name": "PHA from cellulosic sugar — draft flowsheet", "kind": "biosteam",
                 "modelId": FLOWSHEET, "program": "pha"}]
    return [r for r in rows if r.get("kind") == "biosteam" and r.get("modelId") in _shelf.SHELF
            and not _shelf.SHELF[r["modelId"]].reference]


def runnable(flowsheet: str):
    """The shelf entry of a flowsheet a scenario can run, or the refusal in
    words: the toy, an id the shelf does not hold, and a reference
    biorefinery (it runs whole on its package's own defaults) are refused."""
    try:
        info = _shelf.info(flowsheet)
    except _shelf.NotOnShelf as e:
        raise ScenarioRefused(str(e)) from None
    if info.reference:
        raise ScenarioRefused(f"{flowsheet} is a reference biorefinery: it runs whole on its package's own defaults, "
                              "not as a scenario's flowsheet")
    return info


def flowsheet_of(scenario_id: str, flowsheet: str | None = None) -> str:
    """The flowsheet a run runs: a seed scenario's own, by its id; else, for a
    scenario a person made here, the non-reference shelf flowsheet it names.
    Any other case is refused, in words."""
    if not (scenario_id or "").strip():
        raise ScenarioRefused("a run names the scenario it belongs to")
    seeds = {s["id"]: s for s in seed_scenarios()}
    if scenario_id in seeds:
        own = seeds[scenario_id]["modelId"]
        if flowsheet and flowsheet != own:
            raise ScenarioRefused(f"{scenario_id} runs {own}, not {flowsheet}")
        return own
    kind = _unrunnable_seed(scenario_id)
    if kind is not None:
        # §2.R: a seed scenario that runs no shelf flowsheet (the casein
        # examples are authored cost surfaces) is not a scenario made here;
        # a run under its id would file a flowsheet's train under it.
        what = ("an authored scenario of the seed, a cost surface written by hand" if kind == "authored"
                else f"a seed scenario of kind {kind} whose flowsheet is not on the shelf")
        raise ScenarioRefused(f"{scenario_id} is {what}: it runs no flowsheet here, and a scenario made here takes an "
                              "id of its own")
    if not flowsheet:
        raise ScenarioRefused(f"there is no seed scenario {scenario_id}; the seed's BioSTEAM scenarios are "
                              f"{', '.join(seeds) or 'none'}, and a scenario made here names the flowsheet it runs")
    return runnable(flowsheet).id


def _unrunnable_seed(scenario_id: str) -> str | None:
    """The kind of a seed scenario that runs no shelf flowsheet (an authored
    cost surface), by its id, from the projection modules.json holds; None
    when the seed holds no such scenario or there is no projection here."""
    from . import module_stores

    try:
        rows = list(module_stores._projection()["proforma"]["scenarios"])
    except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
        return None
    row = next((r for r in rows if r.get("id") == scenario_id), None)
    if row is None or (row.get("kind") == "biosteam" and row.get("modelId") in _shelf.SHELF):
        return None
    return str(row.get("kind") or "authored")


def _in_program(paper_id: str, program: str | None) -> bool:
    from . import programs

    try:
        return program is not None and programs.program_of_paper(paper_id or "") == program
    except FileNotFoundError:  # no corpus exported here: no paper is known to be the program's
        return False


def bind_inputs(flowsheet: str, records: list[dict], host: str | None = None, assumptions: list | None = None) -> list:
    """Every input of a shelf flowsheet that takes a value, bound by its shelf
    entry: a process input to the records of its fields (the first field
    with a bound record wins) on its program's papers that pass the
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
                if r.get("field") != field_id or not _in_program(r.get("paperId", ""), info.program) or _exclusion(r):
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
                   if r.get("strainId") and r.get("field") in fields and _in_program(r.get("paperId", ""), info.program)})


def bound(flowsheet: str, *, scenario_id: str = "", name: str = "", host: str | None = None,
          assumptions: list | None = None, pool=None, fits: dict[str, str] | None = None):
    """A flowsheet's inputs bound, in the shape GET /api/proforma/scenarios
    serves: a seed scenario's with its id and name, a flowsheet's alone with
    both empty (§2.3, c); with the fermOS fits a person chose laid on
    (OF-BLD-019 §5.1), and a person's named values over both (OF-BLD-020
    D3: an input a value overrides takes no fit)."""
    from . import evidence_pool
    from .models import ProformaScenarioInfo

    pool = pool or evidence_pool.load(include_archived=True)
    if flowsheet == FLOWSHEET:
        out = scenario(host, assumptions, pool).model_copy(update={"id": scenario_id, "name": name})
    else:
        info = _shelf.info(flowsheet, allow_toy=True)
        inputs = bind_inputs(flowsheet, pool.records, host, assumptions)
        out = ProformaScenarioInfo(
            id=scenario_id, name=name, product=PRODUCTS.get(flowsheet, flowsheet), flowsheet=flowsheet, host=host,
            hosts=_hosts(pool.records, flowsheet), inputs=inputs, waiting=[], leavesOut=info.leavesOut,
            priceBasis=info.priceBasis or "")
    apply_fits(out.inputs, fits_beside(fits, assumptions or []), flowsheet)
    out.waiting = [i.key for i in out.inputs if i.binding == "waiting"]
    return out


def _hidden(program: str | None, include_archived: bool) -> bool:
    from . import programs

    try:
        return programs.hides(program, include_archived)
    except FileNotFoundError:  # no corpus exported here: nothing is known to be archived
        return False


def scenarios(include_archived: bool = False, host: str | None = None, pool=None) -> list:
    """GET /api/proforma/scenarios (§2.3, b): one bound scenario per seed
    scenario of kind biosteam whose program the switch shows (an example
    hides with the archive). Each binds its own program's records whatever
    the switch says, as a scenario opened by id does."""
    from . import evidence_pool

    out = []
    for s in seed_scenarios():
        if _hidden(s.get("program"), include_archived) or (s.get("example") and not include_archived):
            continue
        pool = pool or evidence_pool.load(include_archived=True)
        out.append(bound(s["modelId"], scenario_id=s["id"], name=s.get("name") or s["id"], host=host, pool=pool))
    return out


def bind_flowsheet(flowsheet: str, *, include_archived: bool = False, host: str | None = None,
                   assumptions: list | None = None, pool=None, fits: dict[str, str] | None = None):
    """GET /api/proforma/bind (§2.3, c): a shelf flowsheet's inputs bound as a
    scenario a person made here shows them, id and name empty, with the
    fermOS fits a person chose (OF-BLD-019 §5.1). The toy, an id the shelf
    does not hold, a reference biorefinery, a flowsheet of a program the
    switch hides (as the shelf hides it), and a fit that cannot feed the
    input it was chosen for are refused in words."""
    from . import programs

    info = runnable(flowsheet)
    if _hidden(info.program, include_archived):
        held = programs.program_by_id(info.program)
        raise ScenarioRefused(
            f"{flowsheet} belongs to the archived program {held.name if held else info.program}; "
            "Settings → Programs → Show archived programs and examples binds it")
    return bound(flowsheet, host=host, assumptions=assumptions, pool=pool, fits=fits)


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

FIT_KEYS = ("titre", "yield", "productivity")
_FIT_NAME = re.compile(r"(\w+) fit(?: (low|high))?")
# The words a series' label or measure id uses for what each shelf
# flowsheet makes, to tell a fit of another product's series (PRODUCTS).
PRODUCT_WORDS: dict[str, tuple[str, ...]] = {
    "ethanol": ("ethanol", "etoh"),
    "phb": ("phb", "pha", "polyhydroxybutyrate", "polymer"),
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


def fermos_fits(flowsheet: str) -> list:
    """GET /api/fermos/fits: every kinetic fit and forecast fermOS keeps,
    newest first, each with what it can feed `flowsheet` and why not. A
    read: it keeps nothing and starts no simulator."""
    from . import artifacts, fermos

    runnable(flowsheet)
    return [fit_info(a, flowsheet) for a in artifacts.all_artifacts() if a.tool in fermos.FEEDABLE]


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
                  "titre is a named person's assumption" if t and t.binding == "assumption" else
                  "titre waits for a source")
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
            raise ScenarioRefused(
                f"productivity from {info.tool} {aid} is its titre over the hour its median sugar runs out, so it feeds "
                f"the fermenter only beside titre from {aid}: the fermenter's batch time is the titre over the "
                f"productivity, and here {paired}. To use it, choose {aid} for titre as well, or stop using it for "
                "productivity")
        if key == "productivity" and info.batchTimeH is not None:
            extra.append(BasisInput(name="fit batch time", value=info.batchTimeH, unit="h", source=BasisSource(
                kind="artifact", id=aid, note="the hour the forecast's median sugar runs out, found between its grid "
                                              "points; productivity is the fit's titre over it, and titre is the same fit's")))
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
# (its `strainId`), else the species its paper's words name, else the
# program's one species (every host the program catalogues is of it, as
# module_stores reads it), and the organism line counts each kind (§5.R: of
# sc-yeast-1's eighteen thread Q yield records on 20 October, three name
# CEN.PK113-7D and fifteen no catalogued strain). A shelf model is the
# scenario's when its host is one of those strains ('strain') or of one of
# those species ('species': geneOS's yeast reconstructions, iMM904 and
# Yeast9, are of S288C), each said so on its row with the records it covers.

# The sugar each scenario flowsheet's feed is, as geneOS names its
# substrates: the glucose-to-ethanol flowsheet's is glucose (FEED_CARBON);
# the PHA draft's is a fermentable sugar, and its yield cap reads the glucose
# ceiling (yield_cap), so its check reads glucose too. Its one matching
# model, RehMBEL1391, is fed fructose on the shelf and takes up no glucose,
# so that check finds no ceiling and says why, sending nobody to compute one
# geneOS would refuse (§5.R).
CEILING_SUGAR: dict[str, str] = {ETHANOL: "glucose", FLOWSHEET: "glucose"}
_G_PER_G = "g g-1"
CEILING_KEPT = "Computed on read and kept nowhere: the binding and the run keep the yield as bound."
PHA_CLIP_NOTE = ("The PHA draft's run clips record yields above the highest glucose ceiling on the shelf to it "
                 "(OF-BLD-014 §8.3); this check reads each record unclipped.")


def _input_named(art, name: str):
    return next((i for i in art.inputs if i.name == name), None)


def _ceiling_of(art, name: str) -> str | None:
    """What a ceiling's basis names: its model by the shelf id the model
    input's source carries, its product and substrate by their values."""
    i = _input_named(art, name)
    if i is None:
        return None
    return (str(i.source.id) if i.source.id else None) if name == "model" else str(i.value)


def _strain_labels() -> tuple[dict[str, str], dict[str, str]]:
    """Each catalogued strain's label ('Saccharomyces cerevisiae S288C') and
    each program's one species, when every host it catalogues is of that
    species, from the projection export:corpus writes (module_stores reads
    the same). Both empty with no projection here."""
    from . import module_stores

    try:
        hosts = module_stores._projection()["geneos"]["hosts"]
    except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
        return {}, {}
    labels = {h["id"]: h["name"] for h in hosts if h.get("id") and h.get("name")}
    by_program: dict[str, set[str]] = {}
    for h in hosts:
        if h.get("program"):
            by_program.setdefault(h["program"], set()).add(module_stores.species_of(h.get("name") or "") or "")
    return labels, {p: next(iter(sp)) for p, sp in by_program.items() if len(sp) == 1 and "" not in sp}


def _species_words(species: str) -> str:
    return species[:1].upper() + species[1:]


def _yield_words(inp) -> str:
    if inp.binding == "records":
        n = len(inp.records)
        return (f"the median of {n} records, with the lowest and the highest" if n >= 3 else
                f"the middle of {n} records, with both" if n == 2 else "one record, held fixed")
    if inp.binding == "assumption":
        by = inp.source.by if inp.source else None
        return f"a named person's assumption{f' ({by})' if by else ''}, with its low and its high"
    if inp.binding == "artifact":
        aid = inp.source.id if inp.source else None
        return f"a fermOS fit's Yp/s{f' ({aid})' if aid else ''}, its median with its 5th and 95th percentile"
    return "nothing yet: the yield waits for a record, a named person's assumption or a fermOS fit"


_CHECK_WHAT = {
    "records": "a reviewer should check the basis of each record above it (another sugar counted, the product "
               "measured otherwise, another organism)",
    "assumption": "a reviewer should check what the assumption rests on, and the basis of the yield it was taken from",
    "artifact": "a reviewer should check the basis of the fit's readings (the product and sugar series, and their units)",
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


def ceiling_check(scenario_id: str, flowsheet: str | None = None, *, include_archived: bool = False,
                  host: str | None = None, assumptions: list | None = None, fits: dict[str, str] | None = None,
                  pool=None, overrides: list | None = None):
    """GET /api/proforma/ceiling-check: a scenario's fermenter yield beside
    the newest stored geneOS ceiling of each shelf model of its organism, on
    its flowsheet's sugar (D11). The scenario is a seed's by its id, or one
    made here by the flowsheet it names (flowsheet_of); its yield is bound as
    its page binds it, with the person's overrides (and the older
    assumptions field, read the same way) and the fermOS fits chosen. Refused in words as the binding is; a scenario of a program the
    switch hides, as GET /api/proforma/bind refuses it. A read: it keeps
    nothing, starts no worker, and changes no binding or run."""
    from . import artifacts, evidence_pool, geneos, geneos_models, module_stores, programs, units
    from .models import CeilingCheck, CeilingRow

    fid = flowsheet_of(scenario_id, flowsheet)
    info = runnable(fid)
    if _hidden(info.program, include_archived):
        held = programs.program_by_id(info.program)
        raise ScenarioRefused(
            f"{fid} belongs to the archived program {held.name if held else info.program}; "
            "Settings → Programs → Show archived programs and examples reads it")
    sugar = CEILING_SUGAR.get(fid)
    product = PRODUCTS.get(fid, fid)
    if sugar is None or product not in geneos_models.PRODUCTS:
        raise ScenarioRefused(f"{fid} names no product and sugar a geneOS ceiling is computed for")
    typed, _ = named_values(scenario_id, overrides, assumptions)
    _check_keys(info, typed)
    pool = pool or evidence_pool.load(include_archived=True)
    # The yield as the scenario binds it: the PHA draft's records unclipped
    # (cap=None), so the check reads each record as it is (D11).
    inputs = bind(pool.records, host, typed, cap=None) if fid == FLOWSHEET else bind_inputs(
        fid, pool.records, host, typed)
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
    # name, else the program's one species; the line counts each kind, so a
    # few records of a catalogued strain never speak for the rest (§5.R).
    labels, program_species = _strain_labels()
    by_id = getattr(pool, "records_by_id", None) or {r["id"]: r for r in pool.records}
    bound_rows = [by_id.get(r) or {} for r in (inp.recordIds if inp.binding == "records" else [])]
    n = len(bound_rows)
    held = programs.program_by_id(info.program)
    program_name = held.name if held else info.program
    own_species = program_species.get(info.program or "")
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
            of_record[rid] = own_species
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
                         + (f"{'is' if unread == 1 else 'are'} read as the {program_name} program's species, "
                            f"{_species_words(own_species)}, the species of every host it catalogues" if own_species
                            else f"name{'s' if unread == 1 else ''} no organism the tree can read"))
        whose = "; ".join(parts)
        same = "a strain the records the yield binds name"
        if not n and own_species:
            species = {own_species}
            whose = (f"the {program_name} program, every host of which is {_species_words(own_species)}, as the "
                     "yield binds no record")
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
        mine = [a for a in stored if _ceiling_of(a, "model") == m.id and _ceiling_of(a, "product") == product
                and isinstance(a.output.get("gPerG"), (int, float))]
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
            flag=flag, words=_row_words(flag, inp.binding, value_above), recordsAbove=above))

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
    notes = [CEILING_KEPT] + ([PHA_CLIP_NOTE] if fid == FLOWSHEET and inp.binding == "records" else [])
    return CeilingCheck(
        scenarioId=scenario_id, flowsheet=fid, product=product, substrate=sugar,
        sugarWords=(f"the flowsheet's feed is {sugar}" if fid != FLOWSHEET else
                    f"the PHA draft's feed is a fermentable sugar; its yield cap reads the {sugar} ceiling, and so does this check"),
        host=host, strains=strains, species=species_list, organismWords=organism, models=models,
        yieldBinding=inp.binding, yieldValue=inp.value, yieldLow=inp.low, yieldHigh=inp.high, yieldUnit=inp.unit,
        yieldSource=inp.source, yieldRecords=len(inp.records), yieldWords=_yield_words(inp), rows=rows,
        flagged=any(r.flag == "above" for r in rows), empty=empty, computeAt=compute_at,
        otherSugars=sorted(other_sugars), notes=notes)
