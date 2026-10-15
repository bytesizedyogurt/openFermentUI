"""fermOS fits what a run measured (OF-BLD-014 §7.2).

The browser sends a deposition's series, the way Practice sends runs; the
service fits them and keeps the fit as an artifact, and nothing else. No
parameter from a paper enters fermOS (D6): every number here was measured on
the run being fitted.

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
    BasisInput,
    BasisSource,
    FermosFitResponse,
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
            source=BasisSource(kind="deposition", id=deposition_id),
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
