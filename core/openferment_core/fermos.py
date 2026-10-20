"""fermOS fits what a run measured (OF-BLD-014 §7.2).

The browser sends a deposition's series, the way Practice sends runs; the
service fits them and keeps the fit as an artifact, and nothing else. No
parameter from a paper enters fermOS (D6): the browser sends a deposition's
own readings. Depositions live in the browser's Durable tier, which the
service cannot see, so it takes the readings as sent and says so in each
fit's basis (§7.R).

GROWTH FIT. For a biomass series of four or more readings: least squares of
ln X on t over every contiguous window of four or more readings. Among the
windows whose slope has a 95 % interval above zero, the one with the highest
R². It works in the measure's own unit, so optical density fits as well as
dry weight.

KINETIC FIT. Logistic growth, Luedeking–Piret production and the substrate
balance, integrated in closed form, so no integrator is needed:

    X(t) = X0·Xmax / (X0 + (Xmax − X0)·e^(−μt))
    I(t) = ∫X = Xmax·t + (Xmax/μ)·ln[(X0 + (Xmax − X0)·e^(−μt)) / Xmax]
    P(t) = P0 + α·(X(t) − X0) + β·I(t)
    S(t) = S0 − γ·(X(t) − X0) − δ·I(t)

(the forms above are the specification's, rearranged so e^(μt) never
overflows). Fit X0, μ, Xmax to biomass; with that curve fixed, solve the
product and substrate coefficients by bounded linear least squares; then
refine everything together in two passes, rates bounded at zero, the first
scaling each series' residuals by its range and the second by its own
scatter from the first. The covariance comes from the Jacobian and the
residual variance, the intervals from Student's t.

THE NOISE ASSUMPTION. Each series scatters by a constant amount. Where an
assay scatters in proportion to its reading, the intervals at the high end
come out too narrow; the screen says so beside every interval.

WHAT THE MODEL IS. It holds no nutrient: Xmax stands for whatever stopped
growth in that run, so a fit describes that medium.
"""
from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
from scipy.optimize import least_squares, lsq_linear
from scipy.stats import t as student_t

from . import artifacts
from .models import (
    Band,
    BasisInput,
    BasisSource,
    Evidence,
    FermosFitResponse,
    ForecastResult,
    Interval,
    StartValues,
    FermosSeries,
    FitParam,
    GrowthFit,
    KineticFit,
    SeriesFitQuality,
)

GROWTH, KINETIC = "growth_fit", "kinetic_fit"
VERSION = "fermos-1"

# Conventions (E.1): the shortest window a growth rate is read over, the
# fewest readings a kinetic fit takes, and the interval's coverage.
MIN_WINDOW = 4
MIN_KINETIC = 5
CONFIDENCE = 0.95

NOTES = [
    "Each series is taken to scatter by a constant amount. Where an assay scatters in proportion to its reading, "
    "the intervals at the high end of a curve come out too narrow.",
    "The model holds no nutrient: Xmax stands for whatever stopped growth in this run, so the fit describes this "
    "run's medium.",
]


class FitRefused(ValueError):
    """The request cannot be fitted, in words."""


# ── the growth fit ─────────────────────────────────────────────────────


def _ols(t: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """Slope, intercept, slope's standard error, R²."""
    n = len(t)
    tm, ym = t.mean(), y.mean()
    sxx = float(((t - tm) ** 2).sum())
    slope = float(((t - tm) * (y - ym)).sum() / sxx)
    icpt = float(ym - slope * tm)
    res = y - (icpt + slope * t)
    ssr = float((res**2).sum())
    sst = float(((y - ym) ** 2).sum())
    se = math.sqrt(ssr / (n - 2) / sxx) if n > 2 else math.inf
    r2 = 1 - ssr / sst if sst > 0 else 0.0
    return slope, icpt, se, r2


def growth_fit(series: FermosSeries) -> GrowthFit:
    pts = [p for p in series.points]
    base = GrowthFit(measureId=series.measureId, unit=series.unit, points=len(pts))
    if len(pts) < MIN_WINDOW:
        return base.model_copy(update={"reason": f"a growth rate needs {MIN_WINDOW} or more readings; this series has {len(pts)}"})
    if any(p.value <= 0 for p in pts):
        return base.model_copy(update={"reason": "a reading at or below zero has no logarithm; the growth rate is read from ln of biomass"})
    t = np.array([p.t for p in pts], float)
    y = np.log(np.array([p.value for p in pts], float))
    best: tuple[float, float, float, float, int, int] | None = None
    for i in range(len(pts)):
        for j in range(i + MIN_WINDOW, len(pts) + 1):
            tw, yw = t[i:j], y[i:j]
            if np.ptp(tw) == 0:
                continue
            slope, _, se, r2 = _ols(tw, yw)
            low = slope - student_t.ppf(0.5 + CONFIDENCE / 2, len(tw) - 2) * se
            if low <= 0:
                continue
            if best is None or r2 > best[3] + 1e-12:
                best = (slope, low, slope + (slope - low), r2, i, j)
    if best is None:
        return base.model_copy(update={"reason": "no window of four or more readings has a growth rate whose 95 % interval lies above zero"})
    slope, low, high, r2, i, j = best
    return base.model_copy(update={
        "mu": FitParam(name="mu", value=slope, low=low, high=high, unit="h-1", identified=low > 0),
        "doublingTimeH": math.log(2) / slope, "r2": r2, "window": [float(t[i]), float(t[j - 1])],
        "points": j - i,
    })


# ── the kinetic fit ────────────────────────────────────────────────────


def logistic(t: np.ndarray, x0: float, mu: float, xmax: float) -> tuple[np.ndarray, np.ndarray]:
    """X(t) and its integral from zero, in forms that do not overflow."""
    e = np.exp(-mu * t)
    denom = x0 + (xmax - x0) * e
    x = x0 * xmax / denom
    integral = xmax * t + (xmax / mu) * np.log(denom / xmax)
    return x, integral


def _role(series: list[FermosSeries], role: str) -> FermosSeries | None:
    found = [s for s in series if s.role == role and len(s.points) >= 2]
    return found[0] if found else None


def _arrays(s: FermosSeries) -> tuple[np.ndarray, np.ndarray]:
    return np.array([p.t for p in s.points], float), np.array([p.value for p in s.points], float)


def kinetic_fit(series: list[FermosSeries], growth: GrowthFit | None = None) -> KineticFit:
    bio = _role(series, "biomass")
    if bio is None or len(bio.points) < MIN_KINETIC:
        n = len(bio.points) if bio else 0
        return KineticFit(reason=f"a kinetic fit needs a biomass series of {MIN_KINETIC} or more readings; this run has {n}")
    prod = _role(series, "product")
    subs = _role(series, "substrate")
    prod = prod if prod and len(prod.points) >= MIN_KINETIC else None
    subs = subs if subs and len(subs.points) >= 3 else None
    tb, xb = _arrays(bio)
    if xb.max() <= 0:
        return KineticFit(reason="every biomass reading is at or below zero")

    # 1. The biomass curve alone.
    x0_0 = max(float(xb[0]), float(xb.max()) * 1e-3, 1e-9)
    mu_0 = growth.mu.value if growth and growth.mu else max(math.log(max(xb.max(), x0_0 * 1.01) / x0_0) / max(np.ptp(tb), 1e-9), 1e-3)
    xmax_0 = float(xb.max()) * 1.05
    r = least_squares(lambda q: logistic(tb, *q)[0] - xb, [x0_0, mu_0, xmax_0],
                      bounds=([1e-12, 1e-9, 1e-12], [np.inf, np.inf, np.inf]))
    x0, mu, xmax = (float(v) for v in r.x)

    # 2. The coefficients, by bounded linear least squares on that curve.
    names = ["X0", "mu", "Xmax"]
    q0 = [x0, mu, xmax]
    lo = [1e-12, 1e-9, 1e-12]
    for s, (n0, a, b), sign in ((prod, ("P0", "alpha", "beta"), 1.0), (subs, ("S0", "gamma", "delta"), -1.0)):
        if s is None:
            continue
        ts, ys = _arrays(s)
        xs, ints = logistic(ts, x0, mu, xmax)
        design = np.column_stack([np.ones_like(ts), sign * (xs - x0), sign * ints])
        sol = lsq_linear(design, ys, bounds=([-np.inf, 0, 0], [np.inf, np.inf, np.inf]))
        names += [n0, a, b]
        q0 += [float(v) for v in sol.x]
        lo += [-np.inf, 0.0, 0.0]

    present = [("biomass", bio)] + [(k, v) for k, v in (("product", prod), ("substrate", subs)) if v is not None]

    def predict(q: np.ndarray, role: str, ts: np.ndarray) -> np.ndarray:
        x, i = logistic(ts, q[0], q[1], q[2])
        if role == "biomass":
            return x
        k = names.index("P0" if role == "product" else "S0")
        sign = 1.0 if role == "product" else -1.0
        return q[k] + sign * (q[k + 1] * (x - q[0]) + q[k + 2] * i)

    def residuals(q: np.ndarray, scales: list[float]) -> np.ndarray:
        out = []
        for (role, s), sc in zip(present, scales):
            ts, ys = _arrays(s)
            out.append((predict(q, role, ts) - ys) / sc)
        return np.concatenate(out)

    # 3. Everything together: scaled by range, then by each series' scatter.
    ranges = [max(float(np.ptp(_arrays(s)[1])), 1e-12) for _, s in present]
    bounds = (lo, [np.inf] * len(lo))
    q0a = np.clip(np.array(q0), np.array(lo) + 0, None)
    first = least_squares(residuals, q0a, args=(ranges,), bounds=bounds, x_scale="jac")
    scatters = []
    for role, s in present:
        ts, ys = _arrays(s)
        rr = predict(first.x, role, ts) - ys
        scatters.append(max(math.sqrt(float((rr**2).sum()) / len(rr)), 1e-12 * max(ranges)))
    second = least_squares(residuals, first.x, args=(scatters,), bounds=bounds, x_scale="jac")
    q = second.x

    n_obs = sum(len(s.points) for _, s in present)
    dof = n_obs - len(q)
    if dof <= 0:
        return KineticFit(reason=f"{n_obs} readings cannot pin down {len(q)} parameters")
    w = second.fun
    s2 = float((w**2).sum()) / dof
    jac = second.jac
    try:
        cov = np.linalg.pinv(jac.T @ jac) * s2
    except np.linalg.LinAlgError:
        return KineticFit(reason="the fit's parameters cannot be told apart on this run")
    tcrit = float(student_t.ppf(0.5 + CONFIDENCE / 2, dof))

    xu = bio.unit
    pu = prod.unit if prod else ""
    su = subs.unit if subs else ""
    units = {"X0": xu, "mu": "h-1", "Xmax": xu, "P0": pu, "alpha": f"{pu} per {xu}", "beta": f"{pu} per {xu} per h",
             "S0": su, "gamma": f"{su} per {xu}", "delta": f"{su} per {xu} per h"}
    params = []
    for k, name in enumerate(names):
        se = math.sqrt(max(float(cov[k, k]), 0.0))
        v = float(q[k])
        low, high = v - tcrit * se, v + tcrit * se
        p = FitParam(name=name, value=v, low=low, high=high, unit=units[name])
        if name in ("mu", "Xmax"):
            p.identified = low > 0
        if name in ("alpha", "beta", "gamma", "delta"):
            p.indistinguishableFromZero = low <= 0 <= high or v == 0
        params.append(p)

    quality = []
    for role, s in present:
        ts, ys = _arrays(s)
        rr = ys - predict(q, role, ts)
        sst = float(((ys - ys.mean()) ** 2).sum())
        quality.append(SeriesFitQuality(
            measureId=s.measureId, role=role, r2=1 - float((rr**2).sum()) / sst if sst > 0 else 0.0,
            scatter=math.sqrt(float((rr**2).sum()) / max(len(rr) - 1, 1)), residuals=[float(v) for v in rr],
        ))
    return KineticFit(params=params, quality=quality, covariance=[[float(v) for v in row] for row in cov],
                      series=[s for _, s in present])


# ── artifacts (E.5) ────────────────────────────────────────────────────


def _inputs(deposition_id: str, series: list[FermosSeries]) -> list[BasisInput]:
    """One input per series, its readings as JSON, source the deposition."""
    return [
        BasisInput(
            name=f"{s.role or 'unassigned'} series: {s.label}",
            value=json.dumps(s.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            unit=s.unit,
            source=BasisSource(kind="deposition", id=deposition_id,
                               note="the readings as the browser sent them; the service cannot see the deposition itself"),
        )
        for s in series
    ]


def _series_of(inputs: list[BasisInput]) -> list[FermosSeries]:
    return [FermosSeries.model_validate_json(str(i.value)) for i in inputs]


def _run_growth(inputs, seed):
    bio = _role(_series_of(inputs), "biomass")
    if bio is None:
        raise FitRefused("no series is marked biomass")
    return growth_fit(bio).model_dump(mode="json")


def _run_kinetic(inputs, seed):
    series = _series_of(inputs)
    bio = _role(series, "biomass")
    return kinetic_fit(series, growth_fit(bio) if bio else None).model_dump(mode="json")


artifacts.register(GROWTH, VERSION, _run_growth)
artifacts.register(KINETIC, VERSION, _run_kinetic)


def fit(deposition_id: str, series: list[FermosSeries], *, sample: bool = False) -> FermosFitResponse:
    """Both fits for one run. A sample run is computed inline and kept nowhere."""
    series = [s.model_copy(update={"points": sorted(s.points, key=lambda p: p.t)}) for s in series]
    bio = _role(series, "biomass")
    if bio is None:
        raise FitRefused("mark one series as biomass: the fits read the growth rate from it")
    readings = [p for s in series for p in s.points]
    share = sum(1 for p in readings if p.confirmed) / len(readings) if readings else 0.0
    inputs = _inputs(deposition_id, [s for s in series if s.role])
    keep = not sample
    g_art = artifacts.compute(GROWTH, inputs, keep=keep)
    k_art = artifacts.compute(KINETIC, inputs, keep=keep)
    growth = GrowthFit.model_validate(g_art.output)
    kinetic = KineticFit.model_validate(k_art.output)
    return FermosFitResponse(
        depositionId=deposition_id, growth=growth, kinetic=kinetic,
        growthArtifactId=None if sample else g_art.id, kineticArtifactId=None if sample else k_art.id,
        confirmedShare=share, sample=sample, notes=list(NOTES),
    )


def param(fit_: KineticFit, name: str) -> FitParam | None:
    return next((p for p in fit_.params if p.name == name), None)


def series_by_role(fit_: KineticFit) -> dict[str, Any]:
    return {s.role: s for s in fit_.series if s.role}


# ── the forecast (§7.3) ────────────────────────────────────────────────

FORECAST = "growth_forecast"
DRAWS = 200
GRID = 100
SEED = 0

FORECAST_NOTES = [
    "One run pins down that run. Variation from run to run is absent from this band until several runs are fitted together.",
    NOTES[0],
]

WHAT_IDENTIFIES = {
    "mu": "a run with four or more readings while biomass grows exponentially",
    "Xmax": "a run that continues until biomass levels off",
}


def unidentified(fit_: KineticFit) -> str | None:
    """The first of μ and Xmax this fit does not identify, by name, or None."""
    names = [p.name for p in fit_.params]
    for name in ("mu", "Xmax"):
        p = param(fit_, name)
        # Decided here from the numbers, never from a posted flag (§7.R): the
        # interval's low end, and the covariance's own normal bound.
        k = names.index(name) if p else -1
        var = fit_.covariance[k][k] if p and k < len(fit_.covariance) and k < len(fit_.covariance[k]) else math.inf
        pinned = p is not None and p.low > 0 and p.value - 1.96 * math.sqrt(max(var, 0.0)) > 0
        if not pinned:
            return name
    return None


def check_forecastable(fit_: KineticFit) -> None:
    if fit_.reason or not fit_.params:
        raise FitRefused(f"there is no kinetic fit to forecast from: {fit_.reason or 'no parameters'}")
    name = unidentified(fit_)
    if name:
        raise FitRefused(f"{name} is not identified by this run (its interval reaches zero); "
                         f"what would identify it is {WHAT_IDENTIFIES[name]}")


def forecast(fit_: KineticFit, start: StartValues | None = None, duration_h: float | None = None,
             seed: int = SEED) -> dict[str, Any]:
    """The band for readings over `duration_h`, from `DRAWS` parameter sets
    drawn from the fit's covariance. Pure: everything it needs is passed."""
    check_forecastable(fit_)
    start = start or StartValues()
    names = [p.name for p in fit_.params]
    mean = np.array([p.value for p in fit_.params])
    cov = np.array(fit_.covariance)
    rng = np.random.default_rng(seed)
    roles = series_by_role(fit_)
    last = max(pt.t for s in fit_.series for pt in s.points)
    duration = float(duration_h if duration_h is not None else last)
    times = np.linspace(0.0, duration, GRID)
    rate_ix = [names.index(n) for n in ("alpha", "beta", "gamma", "delta") if n in names]

    draws: list[np.ndarray] = []
    tries = 0
    while len(draws) < DRAWS:
        tries += 1
        if tries > DRAWS * 50:
            raise FitRefused("the fit's covariance gives almost no valid parameter set; the run cannot support a forecast")
        q = rng.multivariate_normal(mean, cov, method="svd")
        for k, key in (("X0", "X0"), ("P0", "P0"), ("S0", "S0")):
            v = getattr(start, key)
            if v is not None and k in names:
                q[names.index(k)] = v
        if q[0] <= 0 or q[1] <= 0 or q[2] <= 0 or any(q[i] < 0 for i in rate_ix):
            continue
        draws.append(q)

    scatter = {qq.role: qq.scatter for qq in fit_.quality}
    curves: dict[str, np.ndarray] = {}
    clean: dict[str, np.ndarray] = {}
    for role in ("biomass", "product", "substrate"):
        if role not in roles:
            continue
        rows, bare = [], []
        for q in draws:
            x, integ = logistic(times, q[0], q[1], q[2])
            if role == "biomass":
                y = x
            else:
                k = names.index("P0" if role == "product" else "S0")
                sign = 1.0 if role == "product" else -1.0
                y = q[k] + sign * (q[k + 1] * (x - q[0]) + q[k + 2] * integ)
            bare.append(y)
            # A band for readings: each draw carries the series' own scatter.
            rows.append(y + rng.normal(0.0, scatter.get(role, 0.0), len(times)))
        curves[role] = np.array(rows)
        clean[role] = np.array(bare)

    runs_out = None
    end = len(times)
    if "substrate" in curves:
        med = np.median(curves["substrate"], axis=0)
        below = np.nonzero(med <= 0)[0]
        if below.size:
            end = int(below[0]) + 1
            runs_out = float(times[below[0]])
    times = times[:end]
    bands, finals = [], []
    for role, c in curves.items():
        c = c[:, :end]
        lo, md, hi = (np.percentile(c, q, axis=0) for q in (5, 50, 95))
        unit = roles[role].unit
        bands.append({"role": role, "unit": unit, "low": lo.tolist(), "median": md.tolist(), "high": hi.tolist()})
        finals.append({"role": role, "unit": unit, "low": float(lo[-1]), "median": float(md[-1]), "high": float(hi[-1])})

    yield_iv = None
    if "product" in curves and "substrate" in curves and roles["product"].unit == roles["substrate"].unit and "g" in roles["product"].unit:
        # The process, not the readings: yield is taken from the draws before
        # any reading scatter is added (§7.R).
        p, sub = clean["product"][:, :end], clean["substrate"][:, :end]
        made = p[:, -1] - p[:, 0]
        used = sub[:, 0] - sub[:, -1]
        ok = used > 0
        if ok.any():
            y = made[ok] / used[ok]
            u = roles["product"].unit
            yield_iv = {"role": "yield", "unit": f"{u} per {u}", "low": float(np.percentile(y, 5)),
                        "median": float(np.percentile(y, 50)), "high": float(np.percentile(y, 95))}
    return {"times": times.tolist(), "bands": bands, "finals": finals, "yieldInterval": yield_iv,
            "substrateRunsOutH": runs_out, "draws": DRAWS, "seed": seed}


def _forecast_inputs(fit_artifact: str | None, fit_inline: KineticFit | None, start: StartValues,
                     changed_by: str | None, duration_h: float | None, deposition_id: str | None) -> list[BasisInput]:
    inputs: list[BasisInput] = []
    if fit_artifact:
        inputs.append(BasisInput(name="kinetic fit", value=fit_artifact, unit="", source=BasisSource(kind="artifact", id=fit_artifact)))
    else:
        assert fit_inline is not None
        inputs.append(BasisInput(
            name="kinetic fit", value=fit_inline.model_dump_json(), unit="",
            source=BasisSource(kind="assumption", by="openFerment sample", note="the sample run's fit, an invented time course")))
    for key in ("X0", "P0", "S0"):
        v = getattr(start, key)
        if v is None:
            continue
        if not (changed_by or "").strip():
            raise FitRefused(f"a changed starting value ({key}) is an assumption, and needs the name of the person who set it")
        inputs.append(BasisInput(name=f"start {key}", value=float(v), unit="",
                                 source=BasisSource(kind="assumption", by=changed_by.strip(), note=f"{key} set on screen")))
    if duration_h is not None:
        inputs.append(BasisInput(name="duration", value=float(duration_h), unit="h",
                                 source=BasisSource(kind="convention", note="how long the forecast runs, as asked")))
    return inputs


def _fit_from(inputs: list[BasisInput]) -> KineticFit:
    i = next(x for x in inputs if x.name == "kinetic fit")
    if i.source.kind == "artifact":
        return KineticFit.model_validate(artifacts.get(str(i.value)).output)
    return KineticFit.model_validate_json(str(i.value))


def _run_forecast(inputs, seed):
    start = StartValues(**{x.name.split(" ")[1]: float(x.value) for x in inputs if x.name.startswith("start ")})
    dur = next((float(x.value) for x in inputs if x.name == "duration"), None)
    return forecast(_fit_from(inputs), start, dur, SEED if seed is None else seed)


artifacts.register(FORECAST, VERSION, _run_forecast)


def forecast_run(*, fit_artifact: str | None = None, fit_inline: KineticFit | None = None,
                 start: StartValues | None = None, changed_by: str | None = None,
                 duration_h: float | None = None, sample: bool = False) -> ForecastResult:
    start = start or StartValues()
    if not fit_artifact and fit_inline is None:
        raise FitRefused("name a kept kinetic fit, or send the sample run's fit inline")
    if fit_artifact:
        try:
            art = artifacts.get(fit_artifact)
        except FileNotFoundError as e:
            raise FitRefused(f"there is no kept fit {fit_artifact}") from e
        if art.tool != KINETIC:
            raise FitRefused(f"{fit_artifact} is a {art.tool}, not a kinetic fit")
    # A starting value equal to the run's own is no change, and a start for a
    # series the run lacks is refused (§7.R).
    source = KineticFit.model_validate(artifacts.get(fit_artifact).output) if fit_artifact else fit_inline
    kept = {}
    for key, role in (("X0", "biomass"), ("P0", "product"), ("S0", "substrate")):
        v = getattr(start, key)
        if v is None:
            continue
        own = param(source, key)
        if own is None:
            raise FitRefused(f"the fit has no {role} series, so a starting {key} has nothing to start")
        if not math.isclose(v, own.value, rel_tol=1e-9, abs_tol=1e-12):
            kept[key] = v
    start = StartValues(**kept)
    inputs = _forecast_inputs(fit_artifact, fit_inline, start, changed_by, duration_h, None)
    check_forecastable(_fit_from(inputs))
    art = artifacts.compute(FORECAST, inputs, seed=SEED, keep=not sample)
    out = art.output
    lead = next((f for f in out["finals"] if f["role"] == "product"), out["finals"][0])
    ev = Evidence(
        id=f"ev-{art.id}", label=f"forecast final {lead['role']}, {len(out['times'])} points to {out['times'][-1]:.4g} h",
        value=lead["median"], unit=lead["unit"],
        interval={"low": lead["low"], "high": lead["high"]},
        provenance=art.provenance, basis=artifacts.basis_of(art), figure="trajectory",
    )
    return ForecastResult(**out, artifactId=None if sample else art.id, evidence=ev, sample=sample, notes=list(FORECAST_NOTES))


# ── what a fit feeds a flowsheet (OF-BLD-019 §5.1, D10) ────────────────
#
# A person sends a kept fit, or a kept forecast, to a Proforma scenario; the
# binding (proforma.fit_info) reads what it gives from the forecast: titre
# from the final product, yield from product made over sugar used (Yp/s),
# and the batch time from the hour the median sugar runs out. A forecast is
# read as it was kept; a kinetic fit is forecast here under the fitted run's
# own starting values and length, seeded, exactly as `growth_forecast`
# forecasts it, and that forecast is kept nowhere: the fit is the source the
# scenario names. `batch_simulation` does not exist in this tree.

FEEDABLE = (KINETIC, FORECAST)
# How a refusal names a parameter.
SYMBOL = {"mu": "μ", "Xmax": "Xmax"}


def fit_of(art: Any) -> KineticFit:
    """The kinetic fit a kept fermOS artifact rests on: a kinetic fit's own
    output, or the fit a forecast's basis names. Refused in words when the
    artifact is neither, or its fit is not on file."""
    if art.tool == KINETIC:
        return KineticFit.model_validate(art.output)
    if art.tool == FORECAST:
        try:
            return _fit_from(art.inputs)
        except (StopIteration, artifacts.ArtifactNotFound) as e:
            raise FitRefused(f"the kinetic fit forecast {art.id} rests on is not on file") from e
    raise FitRefused(f"{art.id} is a {art.tool}, not a kinetic fit or a forecast fermOS keeps")


def fit_artifact_of(art: Any) -> str | None:
    """The kept kinetic fit an artifact is or rests on, by id."""
    if art.tool == KINETIC:
        return art.id
    i = next((x for x in art.inputs if x.name == "kinetic fit" and x.source.kind == "artifact"), None)
    return i.source.id if i else None


def deposition_of(art: Any) -> str | None:
    """The run a fit was made on: its readings' deposition, through the fit a forecast rests on."""
    found = next((x.source.id for x in art.inputs if x.source.kind == "deposition"), None)
    if found or art.tool != FORECAST:
        return found
    fid = fit_artifact_of(art)
    try:
        return next((x.source.id for x in artifacts.get(fid).inputs if x.source.kind == "deposition"), None) if fid else None
    except artifacts.ArtifactNotFound:
        return None


def forecast_for(art: Any) -> tuple[dict[str, Any], str]:
    """The forecast an artifact feeds a flowsheet from, and how it was had, in
    words. A kinetic fit whose μ or Xmax is not identified is refused naming
    the parameter and what run would identify it."""
    fit_ = fit_of(art)
    if fit_.reason or not fit_.params:
        raise FitRefused(f"it holds no kinetic fit: {fit_.reason or 'no parameters'}")
    name = unidentified(fit_)
    if name:
        raise FitRefused(f"{SYMBOL[name]} ({name}) is not identified by the run it was fitted to (its interval "
                         f"reaches zero); what would identify it is {WHAT_IDENTIFIES[name]}")
    if art.tool == FORECAST:
        return dict(art.output), f"forecast {art.id}, as kept"
    return forecast(fit_, StartValues(), None, SEED), (
        f"the forecast of fit {art.id} under its run's own starting values and length, seed {SEED}, "
        f"{DRAWS} draws, kept nowhere")

