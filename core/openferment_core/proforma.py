"""Proforma on the service's side (OF-BLD-014 §8.1).

One `SimWorker` runs BioSTEAM in its own process. Its cold start takes about
forty seconds, so the worker starts on first use, or with the service when
`OPENFERMENT_WARM_PROFORMA=1`, and `status()` says where it is: `cold`,
`starting`, `ready` or `failed`, so the screen can say the simulator is
starting rather than look stuck.
"""
from __future__ import annotations

import os
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
        _STATE.update(status="failed", error=str(e))


def start(background: bool = True) -> dict[str, Any]:
    """Start the worker if it is cold or failed; return the status."""
    with _LOCK:
        if _STATE["status"] in ("cold", "failed"):
            _STATE.update(status="starting", error=None)
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
    """A request on the warm worker; the first one starts it and waits."""
    if _STATE["status"] != "ready":
        start(background=False)
    if _STATE["status"] != "ready":
        raise WorkerError(f"the Proforma simulator could not start: {_STATE['error']}")
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
REFERENCE_VERSION = "reference run 1"
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
    out = call("reference", {"flowsheet": flowsheet, "digits": digits})
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
        if key == "yield" and cap is not None:
            clipped = [b for b in bound if b.value > cap[0]]
            for b in clipped:
                b.value = cap[0]
            if clipped:
                inp.flags.append(f"{len(clipped)} above the highest glucose ceiling on the geneOS shelf, clipped to it")
        if bound:
            _settle(inp, bound, field_id)
        elif key in given:
            _assume(inp, given[key])
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


def _assume(inp, a) -> None:
    from .models import BasisSource
    from .threadp import reviewer_refusal

    why = reviewer_refusal(a.by)
    if why:
        raise ScenarioRefused(f"the assumption for {inp.key} needs a person's name: {why}")
    if not a.low <= a.value <= a.high:
        raise ScenarioRefused(f"the assumption for {inp.key} must lie within its own low and high")
    inp.binding = "assumption"
    inp.value, inp.low, inp.high = a.value, a.low, a.high
    inp.sampling = "fixed" if a.low == a.high else "uniform"
    inp.source = BasisSource(kind="assumption", by=a.by.strip(), note=f"typed on {a.at}" + (f": {a.note}" if a.note else ""))


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


def basis_inputs(inputs: list, cap: tuple[float, str] | None, flowsheet: str = FLOWSHEET,
                 samples: int = SAMPLES, scenario_id: str | None = None) -> list:
    """The run's basis: the flowsheet, the scenario it belongs to, what it
    borrows from a package, the samples, and every record, assumption, the
    cap and the conventions."""
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
    return out


def _specs(inputs: list) -> tuple[dict[str, dict], dict[str, float], dict[str, str]]:
    """Back from the basis to what the worker samples: per key a spec, the
    base case, and each input's source kind."""
    import statistics

    vals: dict[str, list[float]] = {}
    assumed: dict[str, dict[str, float]] = {}
    cap = next((float(i.value) for i in inputs if i.name == "yield cap"), None)
    for i in inputs:
        if i.name.endswith(" record"):
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
                     "seed": int(seed or 0), "axes": axes or None})
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
RUN_VERSION = "shelf run 1"


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
    # A run is a caller a person started by id: its records bind whatever the
    # program switch says (OF-BLD-016, "what keeps everything").
    pool = pool or evidence_pool.load(include_archived=True)
    if flowsheet == FLOWSHEET:
        cap = yield_cap()
        inputs = bind(pool.records, req.host, req.assumptions, cap)
    else:
        cap = None
        inputs = bind_inputs(flowsheet, pool.records, req.host, req.assumptions)
    waiting = [i.key for i in inputs if i.binding == "waiting"]
    if waiting:
        raise ScenarioRefused("these inputs wait for a source, a record or a named person's assumption: " + ", ".join(waiting))
    art = artifacts.compute(RUN, basis_inputs(inputs, cap, flowsheet, req.samples, scenario_id=req.scenarioId),
                            records_by_id=pool.records_by_id, seed=req.seed)
    o = art.output
    q = o["quantiles"]
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
    if not flowsheet:
        raise ScenarioRefused(f"there is no seed scenario {scenario_id}; the seed's BioSTEAM scenarios are "
                              f"{', '.join(seeds) or 'none'}, and a scenario made here names the flowsheet it runs")
    return runnable(flowsheet).id


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
    converted by units.py into the input's unit; with none, or with the
    binding stopped, a named person's assumption; else it waits. A
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
        elif bound:
            _settle(inp, bound, used)
        elif fi.key in given:
            _assume(inp, given[fi.key])
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
          assumptions: list | None = None, pool=None):
    """A flowsheet's inputs bound, in the shape GET /api/proforma/scenarios
    serves: a seed scenario's with its id and name, a flowsheet's alone with
    both empty (§2.3, c)."""
    from . import evidence_pool
    from .models import ProformaScenarioInfo

    pool = pool or evidence_pool.load(include_archived=True)
    if flowsheet == FLOWSHEET:
        return scenario(host, assumptions, pool).model_copy(update={"id": scenario_id, "name": name})
    info = _shelf.info(flowsheet, allow_toy=True)
    inputs = bind_inputs(flowsheet, pool.records, host, assumptions)
    return ProformaScenarioInfo(
        id=scenario_id, name=name, product=PRODUCTS.get(flowsheet, flowsheet), flowsheet=flowsheet, host=host,
        hosts=_hosts(pool.records, flowsheet), inputs=inputs, waiting=[i.key for i in inputs if i.binding == "waiting"],
        leavesOut=info.leavesOut, priceBasis=info.priceBasis or "")


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
                   assumptions: list | None = None, pool=None):
    """GET /api/proforma/bind (§2.3, c): a shelf flowsheet's inputs bound as a
    scenario a person made here shows them, id and name empty. The toy, an
    id the shelf does not hold, a reference biorefinery, and a flowsheet of
    a program the switch hides (as the shelf hides it) are refused in words."""
    from . import programs

    info = runnable(flowsheet)
    if _hidden(info.program, include_archived):
        held = programs.program_by_id(info.program)
        raise ScenarioRefused(
            f"{flowsheet} belongs to the archived program {held.name if held else info.program}; "
            "Settings → Programs → Show archived programs and examples binds it")
    return bound(flowsheet, host=host, assumptions=assumptions, pool=pool)
