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


# ── The PHA scenario (§8.3) ─────────────────────────────────────────────
#
# Its inputs bind to records, or to an assumption a named person typed; the
# run is one artifact whose basis lists every record, assumption, model
# setting and convention it used. This module does the binding and the
# statistics; the worker runs BioSTEAM.

RUN = "proforma.run"
SCENARIO_ID = "sc-pha-1"
FLOWSHEET = "pha_sugar_v0"
SAMPLES = 500
GRID_KEYS = ("titre", "yield", "sugarPrice")
GRID_POINTS = 5
HISTOGRAM_BINS = 20
QUANTILES = (5, 25, 50, 75, 95)
PRICE_BASIS = "USD per kg of PHA contained in dried cell mass"
LEAVES_OUT = [
    "feedstock pretreatment and hydrolysis",
    "polymer extraction and purification",
    "wastewater treatment",
    "co-products",
]

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
    import statistics

    from . import units, validate
    from .models import BasisSource, BoundRecord, ScenarioInput

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
        elif key in given:
            _assume(inp, given[key])
        out.append(inp)
    for key, (label, unit) in ASSUMED.items():
        inp = ScenarioInput(key=key, label=label, unit=unit, binding="waiting")
        if key in given:
            _assume(inp, given[key])
        out.append(inp)
    return out


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

    pool = pool or evidence_pool.load()
    inputs = bind(pool.records, host, assumptions, yield_cap())
    hosts = sorted({r.get("strainId") for r in pool.records
                    if r.get("strainId") and _thread_p(r.get("paperId", "")) and r.get("field") in {b[2] for b in BOUND.values()}})
    return ProformaScenarioInfo(
        id=SCENARIO_ID, name="PHA from cellulosic sugar — draft flowsheet", product="phb", flowsheet=FLOWSHEET,
        host=host, hosts=hosts, inputs=inputs, waiting=[i.key for i in inputs if i.binding == "waiting"],
        leavesOut=LEAVES_OUT, priceBasis=PRICE_BASIS)


def basis_inputs(inputs: list, cap: tuple[float, str] | None) -> list:
    """The run's basis: every record, assumption, the cap and the conventions."""
    from .models import BasisInput, BasisSource

    out = [
        BasisInput(name="flowsheet", value=FLOWSHEET, unit="", source=BasisSource(
            kind="convention", note="draft v0: fermentation, harvest and drying only; " + "; ".join(LEAVES_OUT) + " left out")),
        BasisInput(name="finance and properties", value=f"biorefineries.cornstover@{_installed('biorefineries')}", unit="",
                   source=BasisSource(kind="model", id=f"biorefineries.cornstover@{_installed('biorefineries')}",
                                      note="create_tea and create_chemicals; PHB borrows Lignin's volume and heat capacity")),
        BasisInput(name="samples", value=f"{SAMPLES} Latin hypercube", unit="", source=BasisSource(kind="convention")),
    ]
    if cap is not None:
        out.append(BasisInput(name="yield cap", value=cap[0], unit="g g-1", source=BasisSource(kind="artifact", id=cap[1])))
    for inp in inputs:
        if inp.binding == "records":
            out += [BasisInput(name=f"{inp.key} record", value=r.value, unit=inp.unit,
                               source=BasisSource(kind="record", id=r.id)) for r in inp.records]
            if BOUND[inp.key][4] != 1.0:
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


def _run_scenario(inputs, seed):
    import numpy as np

    specs, base, kinds = _specs(inputs)
    try:
        base_out = call("evaluate", {"flowsheet": FLOWSHEET, "values": base})
        base_infeasible = None
    except WorkerError as e:
        base_out, base_infeasible = None, str(e)
    axes = {}
    for k in GRID_KEYS:
        s = specs[k]
        axes[k] = [s["value"]] if s["kind"] == "fixed" else [float(v) for v in np.linspace(s["low"], s["high"], GRID_POINTS)]
    grid = call("grid", {"flowsheet": FLOWSHEET, "axes": axes, "base": base})
    mc = call("montecarlo", {"flowsheet": FLOWSHEET, "specs": specs, "n": SAMPLES, "seed": int(seed or 0), "base": base})

    feasible = [s for s in mc["samples"] if s["outputs"] is not None]
    infeasible: dict[str, int] = {}
    for s in mc["samples"]:
        if s["infeasible"]:
            infeasible[s["infeasible"]["reason"]] = infeasible.get(s["infeasible"]["reason"], 0) + 1
    prices = np.array([s["outputs"]["pricePerKgPha"] for s in feasible], dtype=float)
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
    cells = grid["cells"]
    return {
        "base": base,
        "basePrice": base_out["pricePerKgPha"] if base_out else None,
        "baseCostLines": base_out["costLines"] if base_out else None,
        "baseInfeasible": base_infeasible,
        "readBack": base_out["readBack"] if base_out else (feasible[0]["outputs"]["readBack"] if feasible else {}),
        "quantiles": quantiles,
        "histogram": histogram,
        "sensitivity": sensitivity,
        "samples": len(mc["samples"]),
        "feasible": len(feasible),
        "infeasible": infeasible,
        "grid": {
            "dims": [{"key": k, "values": v} for k, v in axes.items()],
            "msp": [c["outputs"]["pricePerKgPha"] if c["outputs"] else None for c in cells],
            "costLines": {ln: [c["outputs"]["costLines"][ln] if c["outputs"] else None for c in cells] for ln in lines},
            "infeasible": sum(1 for c in cells if c["outputs"] is None),
        },
    }


def _register_run() -> None:
    from . import artifacts

    artifacts.register(RUN, f"{FLOWSHEET} · biosteam {_installed('biosteam')} · biorefineries {_installed('biorefineries')}",
                       _run_scenario)


def _lazy_run() -> None:
    from . import artifacts

    artifacts.register_lazy(RUN, _register_run)


_lazy_run()


def run(req, pool=None):
    """Bind, refuse what waits for a source, and run once per basis."""
    from . import artifacts, evidence_pool
    from .models import ProformaGrid, ProformaRunResult

    if req.scenarioId != SCENARIO_ID:
        raise ScenarioRefused(f"there is no scenario {req.scenarioId}; the BioSTEAM scenario is {SCENARIO_ID}")
    pool = pool or evidence_pool.load()
    cap = yield_cap()
    inputs = bind(pool.records, req.host, req.assumptions, cap)
    waiting = [i.key for i in inputs if i.binding == "waiting"]
    if waiting:
        raise ScenarioRefused("these inputs wait for a source, a record or a named person's assumption: " + ", ".join(waiting))
    art = artifacts.compute(RUN, basis_inputs(inputs, cap), records_by_id=pool.records_by_id, seed=req.seed)
    o = art.output
    q = o["quantiles"]
    ev = evidence_of(art)
    return ProformaRunResult(
        scenarioId=SCENARIO_ID, artifactId=art.id, provenance=art.provenance, inputs=inputs,
        basePrice=o["basePrice"], baseCostLines=o["baseCostLines"], baseInfeasible=o["baseInfeasible"],
        quantiles=q, histogram=o["histogram"], sensitivity=o["sensitivity"], samples=o["samples"],
        feasible=o["feasible"], infeasible=o["infeasible"], grid=ProformaGrid(**o["grid"]), readBack=o["readBack"],
        leavesOut=LEAVES_OUT, priceBasis=PRICE_BASIS, evidence=ev)


def evidence_of(art):
    """A run as one Evidence: the median price with the 5th to 95th percentile."""
    from . import artifacts
    from .models import Evidence, Range

    q = art.output["quantiles"]
    if not q:
        raise ScenarioRefused("this run has no sample the flowsheet could hold, so it has no price to cite")
    return Evidence(
        id=art.id, label=f"Minimum selling price, {SCENARIO_ID} (BioSTEAM draft flowsheet v0)",
        value=q.get("p50", float("nan")), unit=PRICE_BASIS,
        interval=Range(low=q["p5"], high=q["p95"]) if q else None,
        provenance=art.provenance, basis=artifacts.basis_of(art), figure="distribution")


def latest_run(scenario_id: str = SCENARIO_ID):
    """The most recent stored run of a scenario, or None."""
    from . import artifacts

    runs = [a for a in artifacts.all_artifacts() if a.tool == RUN]
    return max(runs, key=lambda a: a.createdAt) if runs else None
