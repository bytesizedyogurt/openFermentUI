"""fermOS fits what a run measured (OF-BLD-014 §7.2), and simulates a run
from its sources (OF-BLD-020 §3.1).

THE RULE, AS OF-BLD-020 D1 AMENDS IT. A *fit* takes only a deposition's
measured series: the browser sends a deposition's own readings, the way
Practice sends runs, and the service fits them and keeps the fit as an
artifact. Depositions live in the browser's Durable tier, which the service
cannot see, so it takes the readings as sent and says so in each fit's basis
(§7.R). A *simulation* (kinetics.py's model families) may take its
parameters from records through the aggregate gate, a fit or forecast, a
kept simulation, a named person's assumption or a stated convention, each
named in its basis, and its provenance is basis_provenance over them
(BINDING below, OF-BLD-020 §3.2).

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
growth in that run, so a fit describes that medium. It is `logistic_v0`
(LOGISTIC), a fit family only: a kinetic fit names its model, and one kept
before OF-BLD-020 names none and reads as logistic_v0.

A FAMILY FIT. `fit(..., family="batch_v1")` fits kinetics.py's batch family
to the same series on least_squares (Family.fit), starting from the logistic
fit's own first estimates read off the readings (_batch_start says why not
its final curve), with the terms one batch's readings cannot pin held as
conventions named in the basis (no death, no maintenance, Ki and Pmax off,
anaerobic). It keeps a `kinetic_fit` whose `model` is the family; with no
biomass series μmax is reported unidentified (OF-BLD-018 D4).

THE GAUGE (OF-BLD-020 §3.R, findings 0 and 8). With no biomass series the
scale of the cells is free: X0, Yx/s, α and β are known only together. The
fit holds X0 at a gauge, X0_GAUGE, named as a convention in its basis, and
keeps it among its parameters (identified false, said a gauge), so a
simulation started from the fit starts from it and reproduces the run. A
person who gives the run's own X0 in its place gets Yx/s multiplied and α
and β divided by X0 over the gauge, each one's source saying so: the sugar
and product are the fit's, the cells the person's scale. Each parameter the
fit reports unidentified carries why (FitParam.unidentifiedBy), and every
reader says that reason, never one the interval beside it contradicts.

BINDING (OF-BLD-020 §3.2, D6). `bind_parameters` gives each spec its value
by its `sourceRule`, in order: the parameter of the fit a person chose (a
`kinetic_fit` of the same family, or a `logistic_v0` fit or its forecast for
what it carries: μ, α, β, the start values, and Yp/s through its forecast as
`proforma.fit_info` reads it), with its interval and whether its run
identified it; the records of each `record:<field>` entry in the evidence
pool, through Proforma's aggregate gate and its statistic (binding.py, moved
there from proforma.py) and units.py into the spec's unit, held to the strain
chosen (its aliases) or to every strain, and to the sugar
(kinetics.CARBON_RULE says which fields are held otherwise,
kinetics.STRAIN_FREE which no strain sets, and kinetics.PRODUCT_OWN which are
one product's own); a kept simulation's value when the request starts from
one; then a named person's override, which wins over all of them
(params.resolve); then the spec's stated convention. A parameter with none
waits, and a run refuses naming it and the field that would bind it. Every
record that is left out is counted and said: another strain or none, no
carbon source or another one, a unit units.py cannot convert.

NAMED RECORDS (OF-BLD-020 §3.4, D13). A request may bind a parameter to
exactly the records it names (`recordsByParam`, spec key to record ids):
what Postdoc's `fermos_simulate` sends, ids and never values. Each must be
in the evidence pool, a record of a field the spec binds from, through the
aggregate gate, and convert into the spec's unit; one
that is not refuses the request, naming it and why. They bind ahead of a fit
or a kept simulation (a person's override still wins), their value is the
same statistic, the basis names each as a `record` input, and `<key> origin`
says they were named (`NAMED`); `records of` speaks only of the records the
rule found.

SIMULATION. `simulate(SimulationRequest)` binds a family's specs
(bind_parameters), refuses in words naming every parameter that waits and
what would bind it, integrates (kinetics.py), and keeps one
`fermos.simulation` artifact (`SIMULATION`): the parameters and start values
with their sources, the time course by state, OUR(t), the end state, the
hour the sugar runs out, the harvest, the mass balance, Yp/s beside the
newest stored geneOS ceiling of the strain's host models (read, never
clamped), and its flags. `harvest(artifact, hour)` reads one's broth at an
hour from the series it keeps (OF-BLD-020 §6.2, D10): never integrated
again, nothing kept; pureOS's simulation inlet reads through it.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import numpy as np
from scipy.optimize import least_squares, lsq_linear
from scipy.stats import t as student_t

from . import artifacts, binding, kinetics, params, units
from .models import (
    Band,
    BasisInput,
    BasisSource,
    Evidence,
    FamilyInfo,
    FermosBinding,
    FermosFitResponse,
    FermosHarvest,
    FermosPoint,
    ForecastResult,
    Interval,
    MassBalance,
    Override,
    OxygenUptake,
    ParameterSpec,
    ParameterValue,
    ParamResolveRequest,
    SimulationCeiling,
    SimulationCeilingRow,
    SimulationRequest,
    SimulationResult,
    SimulationSummary,
    StartValues,
    SteadyState,
    FermosSeries,
    FitParam,
    GrowthFit,
    HarvestState,
    KineticFit,
    SeriesFitQuality,
)

GROWTH, KINETIC = "growth_fit", "kinetic_fit"
VERSION = "fermos-1"
# A kinetic fit names its model since OF-BLD-020 §3.1, so its output changed
# shape: one kept under fermos-1 is stale, and reads as logistic_v0.
KINETIC_VERSION = "fermos-2"
# The closed-form logistic fit below: a fit family only, not in
# kinetics.FAMILIES.
LOGISTIC = "logistic_v0"

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
    return [FermosSeries.model_validate_json(str(i.value)) for i in inputs if i.source.kind == "deposition"]


def _model_of(inputs: list[BasisInput]) -> str:
    """The model a kinetic fit's basis names; none is logistic_v0."""
    return next((str(i.value) for i in inputs if i.name == "model"), LOGISTIC)


def _run_growth(inputs, seed):
    bio = _role(_series_of(inputs), "biomass")
    if bio is None:
        raise FitRefused("no series is marked biomass")
    return growth_fit(bio).model_dump(mode="json")


def _run_kinetic(inputs, seed):
    series = _series_of(inputs)
    model = _model_of(inputs)
    if model != LOGISTIC:
        return family_fit(model, series, _held_of(inputs)).model_dump(mode="json")
    bio = _role(series, "biomass")
    return kinetic_fit(series, growth_fit(bio) if bio else None).model_dump(mode="json")


artifacts.register(GROWTH, VERSION, _run_growth)
artifacts.register(KINETIC, KINETIC_VERSION, _run_kinetic)


# ── a kinetics family fitted to a run (OF-BLD-020 §3.1) ────────────────

G_L = kinetics.G_L
# The fit families: the logistic, and the kinetics families a deposition's
# series can carry. A fed-batch and a chemostat run need what a deposition
# does not record (the feed, the dilution).
FIT_FAMILIES = (LOGISTIC, "batch_v1")
STATE_OF_ROLE = {"biomass": "X", "substrate": "S", "product": "P"}
# What one batch's readings cannot pin, held in a family fit, each a
# convention its basis names: (key, value, why). A word is the term off.
FIT_HELD = (
    ("kd", 0, "held at zero: one batch's readings do not tell a death rate from slower growth"),
    ("maintenance", 0, "held at zero: one batch's readings do not tell maintenance from a lower yield"),
    ("ki_substrate", kinetics.OFF, "held off: one batch's readings do not tell substrate inhibition from a lower μmax"),
    ("p_max", kinetics.OFF, "held off: a fit takes only measurements (D1), and a batch that never nears Pmax "
                            "does not pin it, so product inhibition is left out"),
    ("n_inhibition", 1, "1 by convention (Appendix 2 §A); with Pmax off it changes nothing"),
    ("yxo", kinetics.ANAEROBIC, "no oxygen series is fitted"),
    ("mo", 0, "no oxygen series is fitted"),
)
# With no biomass series these scale with X0 (X → cX, Yx/s → cYx/s,
# α → α/c, β → β/c leaves S and P unchanged when kd and m are held at zero).
SCALED_WITH_X = ("yxs", "alpha", "beta")
# What a simulation started from a family fit takes from it as the fit held
# it (OF-BLD-020 §3.R, finding 4): every held term that shapes X, S or P, so
# the simulation is the model that was fitted (with Pmax off, nothing waits
# for one). Yx/o and mO shape only the oxygen uptake, which no fit reads.
HELD_INTO_SIMULATION = ("kd", "maintenance", "ki_substrate", "p_max", "n_inhibition")
# The gauge X0 is held at when a run has no biomass series (a convention the
# fit's basis names): one gram per litre, so a gauged Yx/s, α and β read as
# per gram of cells per litre of the gauge. Any value would do; this one
# keeps them at the scale of a culture's own.
X0_GAUGE = 1.0
X0_GAUGE_NOTE = ("the gauge X0 is held at: the run has no biomass series, so the scale of the cells is free and X0, "
                 "Yx/s, α and β are known only together; one gram per litre, not a reading (OF-BLD-020 §3.R)")
FIT_GAUGE_NOTE = ("No biomass series: the scale of the cells is free, so X0, Yx/s, α and β are known only together; "
                  "X0 is held at one gram per litre, a gauge, not a reading.")
# Why a family fit reports a parameter unidentified, in the order a reader
# names them: the gauge (family_fit's), then kinetics.Family.fit's own.
UNIDENTIFIED_WORDS = {
    "gauge": "the run has no biomass series, so it scales with X0, which the fit held at a gauge",
    **kinetics.UNIDENTIFIED,
}
X0_GAUGE_WORDS = "the run has no biomass series, so X0 is a gauge the fit held, not a reading"
# How a binding says a fitted value was not identified; the simulation's
# flag reads the reason back after it, from the value's own source.
NOT_IDENTIFIED = "its run did not identify it: "


def unidentified_words(p: FitParam) -> str:
    """Why a fit reports `p` unidentified, in words: the reasons the fit
    kept (FitParam.unidentifiedBy); for a fit that kept none (a logistic
    fit, or one kept before reasons were), its interval reaching zero when it
    does, else that the fit gave no reason. Never a reason the interval
    contradicts (OF-BLD-020 §3.R, finding 3)."""
    if p.unidentifiedBy:
        return "; ".join(X0_GAUGE_WORDS if r == "gauge" and p.name == "x0" else UNIDENTIFIED_WORDS[r]
                         for r in p.unidentifiedBy)
    if p.low <= 0:
        return UNIDENTIFIED_WORDS["interval"]
    return "the fit kept no reason (it was kept before fits did)"


def _gauged(series: list[FermosSeries]) -> bool:
    """A family fit's X is free of scale: no biomass series of two readings."""
    return not any(s.role == "biomass" and len(s.points) >= 2 for s in series)


def _held_inputs(family: str, gauged: bool = False) -> list[BasisInput]:
    specs = {s.key: s for s in kinetics.family(family).specs()}
    out = [BasisInput(name="model", value=family, unit="",
                      source=BasisSource(kind="convention", note=f"the model family fitted: {kinetics.family(family).title} "
                                                                 f"({family}, kinetics.py)"))]
    for key, value, why in FIT_HELD:
        out.append(BasisInput(name=key, value=value, unit=specs[key].unit if key in specs else "",
                              source=BasisSource(kind="convention", note=why)))
    if gauged:
        out.append(BasisInput(name="x0", value=X0_GAUGE, unit=specs["x0"].unit,
                              source=BasisSource(kind="convention", note=X0_GAUGE_NOTE)))
    return out


def _held_of(inputs: list[BasisInput]) -> dict[str, Any]:
    keys = {k for k, _, _ in FIT_HELD} | {"x0"}
    return {i.name: (None if isinstance(i.value, str) else float(i.value)) for i in inputs
            if i.name in keys and i.source.kind == "convention"}


def _in_g_per_l(s: FermosSeries) -> FermosSeries:
    """The series in g L⁻¹, through units.py, or the refusal in words."""
    try:
        points = [p.model_copy(update={"value": units.convert(float(p.value), s.unit, G_L)}) for p in s.points]
    except (TypeError, ValueError):
        raise FitRefused(f"a kinetics family integrates in {G_L}; the {s.role} series is in {s.unit}, which does not "
                         f"convert (fit it as {LOGISTIC}, which reads any unit)") from None
    return s.model_copy(update={"unit": G_L, "points": points})


def _window_rate(t: np.ndarray, y: np.ndarray) -> float | None:
    """growth_fit's rate on an arbitrary positive series, or None."""
    ok = y > 0
    if ok.sum() < MIN_WINDOW:
        return None
    pts = [FermosPoint(t=float(a), value=float(b), entryId=str(k)) for k, (a, b) in enumerate(zip(t[ok], y[ok]))]
    g = growth_fit(FermosSeries(measureId="", label="", unit="", role="biomass", points=pts))
    return g.mu.value if g.mu else None


def _trapz(t: np.ndarray, y: np.ndarray) -> np.ndarray:
    out = np.zeros_like(y)
    out[1:] = np.cumsum((y[1:] + y[:-1]) / 2 * np.diff(t))
    return out


def _batch_start(data: dict[str, tuple[np.ndarray, np.ndarray]],
                 gauge: float = X0_GAUGE) -> tuple[dict[str, float], list[str]]:
    """Where a batch_v1 fit starts: the logistic fit's own first estimates,
    read off the readings (kinetic_fit's steps 1 and 2), never its final
    curve, which starts a Monod fit far off (on test_fermos' stand-in the
    logistic's X0 came out 0.017 against 0.2, its μ 0.93 against 0.40).
    X0, S0 and P0 are the first readings (D6); μmax the growth window's rate
    (growth_fit); α and β by bounded linear least squares of P − P0 on X − X0
    and ∫X; 1/Yx/s and 1/Yp/s the same of S0 − S on X − X0 and P − P0. Ks
    has no estimator and starts at half the starting sugar. An estimate of
    zero has no logarithm, and starts at RUN_OUT_SHARE of the most it could
    be.

    With no biomass series X0 is the gauge (X0_GAUGE, or the one the fit's
    basis names); μmax is the
    rate at which the sugar's consumption grows; X is read as growing by
    e^(μmax·t) to the hour of the lowest sugar reading, in step with the sugar
    used; half the sugar used is read as going to growth and half to the
    product, and β starts as above."""
    notes: list[str] = []
    tS, S = data["S"]
    tP, P = data["P"]
    s0, p0 = float(S[0]), float(P[0])
    used = max(s0 - float(S.min()), kinetics.ATOL)
    made = max(float(P.max()) - p0, kinetics.ATOL)
    span = float(max(tS.max(), tP.max()))
    start: dict[str, float] = {"ks": s0 / 2, "s0": s0, "p0": p0}
    if "X" not in data:
        x0 = gauge
        notes.append(FIT_GAUGE_NOTE)
        mu = _window_rate(tS, s0 - S) or 1 / span
        t_low = float(tS[int(np.argmin(S))])
        x_made = x0 * math.expm1(mu * t_low)
        tX = np.union1d(tS, tP)
        X = x0 + x_made * (s0 - np.interp(tX, tS, S)) / used
        ix = _trapz(tX, X)
        start.update(x0=x0, mu_max=mu, yps=2 * made / used, yxs=2 * x_made / used, alpha=made / x_made,
                     beta=kinetics.RUN_OUT_SHARE * made / max(float(ix[-1]), kinetics.ATOL))
        return start, notes
    tX, X = data["X"]
    x0 = float(X[0])
    mu = _window_rate(tX, X) or 1 / span
    ix = _trapz(tX, X)
    x_at_p, i_at_p = np.interp(tP, tX, X) - x0, np.interp(tP, tX, ix)
    ab = lsq_linear(np.column_stack([x_at_p, i_at_p]), P - p0, bounds=([0, 0], [np.inf, np.inf])).x
    x_at_s = np.interp(tS, tX, X) - x0
    p_at_s = np.interp(tS, tP, P) - p0
    inv = lsq_linear(np.column_stack([x_at_s, p_at_s]), s0 - S, bounds=([0, 0], [np.inf, np.inf])).x
    x_made = max(float(x_at_p.max()), kinetics.ATOL)
    start.update(x0=x0, mu_max=float(mu),
                 alpha=float(ab[0]) if ab[0] > 0 else kinetics.RUN_OUT_SHARE * made / x_made,
                 beta=float(ab[1]) if ab[1] > 0 else kinetics.RUN_OUT_SHARE * made / max(float(i_at_p.max()), kinetics.ATOL),
                 yxs=1 / float(inv[0]) if inv[0] > 0 else x_made / used,
                 yps=1 / float(inv[1]) if inv[1] > 0 else made / used)
    return start, notes


def family_fit(family: str, series: list[FermosSeries], held: dict[str, Any]) -> KineticFit:
    """A kinetics family fitted to a run's series (Family.fit): a KineticFit
    whose `model` is the family, its parameters named as the family's specs
    and in their units. A run it cannot fit is a KineticFit with a reason."""
    fam = kinetics.family(family)
    specs = {s.key: s for s in fam.specs()}
    present = [s for s in series if s.role in STATE_OF_ROLE and len(s.points) >= 2]
    roles = {s.role for s in present}
    if not {"product", "substrate"} <= roles:
        return KineticFit(model=family, reason=f"{family} fits product and substrate together; this run has "
                                               f"{', '.join(sorted(roles)) or 'neither'}")
    try:
        converted = [_in_g_per_l(s) for s in present]
    except FitRefused as e:
        return KineticFit(model=family, reason=str(e))
    data = {STATE_OF_ROLE[s.role]: _arrays(s) for s in converted}
    gauged = "X" not in data
    gauge = held.get("x0") if gauged and isinstance(held.get("x0"), float) else X0_GAUGE
    start, notes = _batch_start(data, gauge)
    keys = ["mu_max", "ks", "yxs", "yps", "alpha", "beta", "x0", "s0", "p0"]
    fixed: dict[str, Any] = {k: v for k, v in held.items() if k in specs}
    fixed["v0"] = None
    if gauged:
        # The scale of X is free: hold X0 at the gauge, so the optimizer has
        # no null direction to wander along, and report what scales with it
        # as unidentified, whatever the numbers say.
        keys.remove("x0")
        fixed["x0"] = start["x0"]
    try:
        r = fam.fit(data, {k: start[k] for k in keys}, fixed, unbounded=SCALED_WITH_X if gauged else ())
    except kinetics.FamilyRefused as e:
        return KineticFit(model=family, reason=str(e))
    why = {k: list(v) for k, v in r.why.items()}
    if gauged:
        for k in SCALED_WITH_X:
            r.identified[k] = False
            why[k] = ["gauge", *(x for x in why.get(k, []) if x != "gauge")]
        notes.append("Yx/s, α and β scale with the gauge X0, so they are reported unidentified, whatever their "
                     "intervals say.")
    fparams = []
    for k in r.keys:
        fp = FitParam(name=k, value=r.values[k], low=r.low[k], high=r.high[k], unit=specs[k].unit,
                      identified=r.identified[k], unidentifiedBy=why.get(k) or None)
        if k in ("alpha", "beta"):
            fp.indistinguishableFromZero = r.low[k] <= 0 <= r.high[k] or r.values[k] == 0
        fparams.append(fp)
    covariance = r.covariance
    if gauged:
        # The gauge is the fit's X0, held: a parameter with no spread, so its
        # row and column of the covariance are zero and the covariance stays
        # the params' own, in their order.
        fparams.append(FitParam(name="x0", value=gauge, low=gauge, high=gauge, unit=specs["x0"].unit,
                                identified=False, unidentifiedBy=["gauge"]))
        covariance = [[*row, 0.0] for row in r.covariance] + [[0.0] * (len(r.covariance) + 1)]
    quality = [SeriesFitQuality(measureId=s.measureId, role=s.role, r2=r.quality[STATE_OF_ROLE[s.role]]["r2"],
                                scatter=r.quality[STATE_OF_ROLE[s.role]]["scatter"],
                                residuals=r.quality[STATE_OF_ROLE[s.role]]["residuals"])
               for s in present if STATE_OF_ROLE[s.role] in r.quality]
    return KineticFit(params=fparams, quality=quality, covariance=covariance, series=present, model=family,
                      notes=notes + r.notes)


def fit(deposition_id: str, series: list[FermosSeries], *, sample: bool = False,
        family: str = LOGISTIC) -> FermosFitResponse:
    """Both fits for one run: the growth rate, and the kinetic fit of
    `family` (logistic_v0, or batch_v1). A sample run is computed inline and
    kept nowhere."""
    if family not in FIT_FAMILIES:
        known = kinetics.FAMILIES.get(family)
        if known is not None and known.socket:
            raise FitRefused(known.refusal())
        raise FitRefused(f"a run's series fit {' or '.join(FIT_FAMILIES)}; {family!r} is not one"
                         + (": a fed-batch and a chemostat run need what a deposition does not record "
                            "(the feed, the dilution)" if known is not None else ""))
    series = [s.model_copy(update={"points": sorted(s.points, key=lambda p: p.t)}) for s in series]
    bio = _role(series, "biomass")
    if bio is None and family == LOGISTIC:
        raise FitRefused("mark one series as biomass: the fits read the growth rate from it")
    readings = [p for s in series for p in s.points]
    share = sum(1 for p in readings if p.confirmed) / len(readings) if readings else 0.0
    inputs = _inputs(deposition_id, [s for s in series if s.role])
    keep = not sample
    g_art = artifacts.compute(GROWTH, inputs, keep=keep) if bio is not None else None
    held = [] if family == LOGISTIC else _held_inputs(family, gauged=_gauged([s for s in series if s.role]))
    k_art = artifacts.compute(KINETIC, inputs + held, keep=keep)
    growth = GrowthFit.model_validate(g_art.output) if g_art is not None else None
    kinetic = KineticFit.model_validate(k_art.output)
    return FermosFitResponse(
        depositionId=deposition_id, growth=growth, kinetic=kinetic,
        growthArtifactId=None if sample or g_art is None else g_art.id, kineticArtifactId=None if sample else k_art.id,
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


def _logistic_only(fit_: KineticFit) -> None:
    if fit_.model != LOGISTIC:
        raise FitRefused(f"a forecast draws from a {LOGISTIC} fit; this one fits {fit_.model}, which is simulated, "
                         "not forecast, from its parameters")


def check_forecastable(fit_: KineticFit) -> None:
    _logistic_only(fit_)
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
    # One mass concentration, however it is spelled ('g L-1', 'g/L'): the
    # units engine's normal form decides (§5.R), never the raw strings.
    if ("product" in curves and "substrate" in curves and "g" in roles["product"].unit
            and units.normalize(roles["product"].unit) is not None
            and units.normalize(roles["product"].unit) == units.normalize(roles["substrate"].unit)):
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
                     changed_by: str | None, duration_h: float | None, deposition_id: str | None,
                     duration_by: str | None = None) -> list[BasisInput]:
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
        # A length a person typed is that person's assumption, named, and
        # makes the forecast assumed (OF-BLD-020 §3.R, findings 7 and 11; D3,
        # E.2‴): the person who set it (`duration_by`), else the one who
        # changed a start value. A length nobody is named for is the caller's
        # convention, as asked (a test, a stand-in, a fixed check).
        who = (duration_by or changed_by or "").strip()
        source = (BasisSource(kind="assumption", by=who, note="how long the forecast runs, set on screen") if who
                  else BasisSource(kind="convention", note="how long the forecast runs, as asked"))
        inputs.append(BasisInput(name="duration", value=float(duration_h), unit="h", source=source))
    return inputs


def _fit_from(inputs: list[BasisInput]) -> KineticFit:
    i = next(x for x in inputs if x.name == "kinetic fit")
    if i.source.kind == "artifact":
        return KineticFit.model_validate(artifacts.get(str(i.value)).output)
    return KineticFit.model_validate_json(str(i.value))


def _start_of(inputs) -> StartValues:
    """The starting values a forecast's basis names (none: the run's own)."""
    return StartValues(**{x.name.split(" ")[1]: float(x.value) for x in inputs if x.name.startswith("start ")})


def _run_forecast(inputs, seed):
    dur = next((float(x.value) for x in inputs if x.name == "duration"), None)
    return forecast(_fit_from(inputs), _start_of(inputs), dur, SEED if seed is None else seed)


artifacts.register(FORECAST, VERSION, _run_forecast)


def forecast_run(*, fit_artifact: str | None = None, fit_inline: KineticFit | None = None,
                 start: StartValues | None = None, changed_by: str | None = None,
                 duration_h: float | None = None, sample: bool = False,
                 duration_by: str | None = None) -> ForecastResult:
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
    inputs = _forecast_inputs(fit_artifact, fit_inline, start, changed_by, duration_h, None, duration_by)
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
        except artifacts.ArtifactDamaged as e:
            # One damaged file refuses what rests on it, in words; it never
            # takes the other fits down with it (§5.R).
            raise FitRefused(f"the kinetic fit forecast {art.id} rests on cannot be read: {e}") from e
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
    except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged):
        return None


# The run-out hour (OF-BLD-019 §5.R). A forecast lays its GRID points over
# the whole length asked and stops at the first point where its median sugar
# is spent, which can lie a whole step past the hour the sugar runs out: a
# forecast asked for 3000 h steps by about 30 h. Past that hour the curves
# keep making product from sugar pushed below zero, so the titre, the yield
# and the batch time a fit feeds would move with the length a person typed.
# The hour is found instead by linear interpolation of the median sugar
# between the last point with sugar left and the first without, on a grid
# drawn again to the bracket's end until one step is at most RUN_OUT_STEP of
# the hour (a grid to the bracket's end steps by about 1 % of it); then the
# forecast is drawn again to that hour, with the same fit, starting values
# and seed, and kept nowhere. The draws do not depend on the length, so each
# redraw is the same DRAWS parameter sets. On test_proforma_fermos' stand-in
# fit, forecasts asked to run from about one run-out to three hundred feed
# batch times within 1 % of each other (STATE.md, §5.R).
RUN_OUT_STEP = 0.02
RUN_OUT_PASSES = 8


def _bracket(fc: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """The last grid hour with median sugar left and the first without, and
    the median sugar at each; None when the sugar does not run out after the
    start."""
    times = fc.get("times") or []
    band = next((b for b in fc.get("bands") or [] if b["role"] == "substrate"), None)
    runs = fc.get("substrateRunsOutH")
    if band is None or runs is None or len(times) < 2 or runs <= times[0]:
        return None
    t1, t2 = float(times[-2]), float(times[-1])
    s1, s2 = float(band["median"][-2]), float(band["median"][-1])
    if not (s1 > 0 >= s2):
        return None
    return t1, t2, s1, s2


def to_run_out(fit_: KineticFit, fc: dict[str, Any], start: StartValues | None = None,
               seed: int = SEED) -> dict[str, Any] | None:
    """`fc` drawn again to the hour its median sugar runs out, found between
    grid points (RUN_OUT_STEP above), its `substrateRunsOutH` that hour (the
    last point it reaches); None when its sugar does not run out after the
    start. Pure, and kept nowhere."""
    found = _bracket(fc)
    if found is None:
        return None
    for _ in range(RUN_OUT_PASSES):
        t1, t2, s1, s2 = found
        hour = t1 + (t2 - t1) * s1 / (s1 - s2)
        if t2 - t1 <= RUN_OUT_STEP * hour:
            break
        finer = _bracket(forecast(fit_, start, t2, seed))
        if finer is None:
            break
        found = finer
    again = forecast(fit_, start, hour, seed)
    again["substrateRunsOutH"] = float(again["times"][-1])
    return again


def forecast_for(art: Any) -> tuple[dict[str, Any], str]:
    """The forecast an artifact feeds a flowsheet from, and how it was had, in
    words. A kinetic fit whose μ or Xmax is not identified is refused naming
    the parameter and what run would identify it. A forecast whose median
    sugar runs out is drawn again to that hour (to_run_out), so what it feeds
    does not depend on the length it was asked to run."""
    fit_ = fit_of(art)
    _logistic_only(fit_)
    if fit_.reason or not fit_.params:
        raise FitRefused(f"it holds no kinetic fit: {fit_.reason or 'no parameters'}")
    name = unidentified(fit_)
    if name:
        raise FitRefused(f"{SYMBOL[name]} ({name}) is not identified by the run it was fitted to (its interval "
                         f"reaches zero); what would identify it is {WHAT_IDENTIFIES[name]}")
    if art.tool == FORECAST:
        fc, how = dict(art.output), f"forecast {art.id}"
        start, seed = _start_of(art.inputs), int(art.output.get("seed", SEED))
    else:
        fc, how = forecast(fit_, StartValues(), None, SEED), (
            f"the forecast of fit {art.id} under its run's own starting values and length, seed {SEED}, "
            f"{DRAWS} draws")
        start, seed = StartValues(), SEED
    again = to_run_out(fit_, fc, start, seed)
    if again is None:
        return fc, f"{how}, as kept" if art.tool == FORECAST else f"{how}, kept nowhere"
    return again, (f"{how}, drawn again to the hour its median sugar runs out, found between its grid points "
                   f"(the same fit, starting values and seed; kept nowhere)")



# ── simulation (OF-BLD-020 §3.1, D1, D5, E.2‴) ─────────────────────────

SIMULATION = "fermos.simulation"
# 2 since OF-BLD-020 §6.R (seam-0): a simulation keeps its own harvest hour
# among the hours of its series, so a batch run past the hour its sugar runs
# out reads its broth there; a run kept under 1 names its own output still.
SIMULATION_RUN = 2
SIMULATION_STEM = f"kinetics {SIMULATION_RUN} · scipy {kinetics.versions()['scipy']}"
OUR_UNIT = "g O2 L⁻¹ h⁻¹"
ANAEROBIC_NOTE = ("Yx/o is absent, so the culture is taken as anaerobic: it takes up no oxygen and its OUR is zero, "
                  "said so (D5).")
START_GROUP = "Start values"
SimulationRefused = kinetics.FamilyRefused
# What a Proforma scenario may take its titre, yield and productivity from
# (proforma.fit_info, GET /api/fermos/fits): a fit, a forecast, and a kept
# simulation (OF-BLD-020 §3.3). A simulation binds no other simulation's
# parameters through FEEDABLE: it starts from one (`simulation:<id>`).
FEEDS_PROFORMA = (*FEEDABLE, SIMULATION)


def _named(inputs: list[BasisInput], name: str) -> BasisInput | None:
    return next((i for i in inputs if i.name == name), None)


def _simulation_version(inputs) -> str:
    fid = _named(list(inputs), "family")
    return f"kinetics {fid.value if fid else '?'} {SIMULATION_RUN} · scipy {kinetics.versions()['scipy']}"


def family_scope(family_id: str) -> str:
    return params.scope_name("fermos-family", family_id)


def family_info(family_id: str) -> FamilyInfo:
    fam = kinetics.family(family_id)
    return FamilyInfo(id=fam.id, title=fam.title, what=fam.what, equations=fam.equations, states=list(fam.states),
                      stateUnits=fam.state_units, socket=fam.socket, specs=fam.specs(), groups=fam.groups())


def families() -> list[FamilyInfo]:
    """Every model family; GET /api/fermos/families/{id} serves one."""
    return [family_info(f) for f in kinetics.FAMILIES]


def family_provided(ids: tuple[str, ...], req: ParamResolveRequest) -> params.Provided:
    """The `fermos-family` scope (`fermos:family:<id>`): the family's specs,
    bound as a simulation binds them (bind_parameters) from the request's
    strain, product, sugar, fit, kept simulation and run-length preset over
    the evidence pool; a person's overrides lie on
    them (params.resolve), and a person's X0 rescales a gauged fit's Yx/s,
    α and β here as in the run (§3.R), so the panel shows what runs."""
    (fid,) = ids
    fam = kinetics.FAMILIES.get(fid)
    if fam is None:
        raise params.ScopeUnknown(f"there is no model family {fid}: the families are {', '.join(kinetics.FAMILIES)}")
    sim = SimulationRequest(family=fid, strain=req.strain, product=req.product, sugar=req.sugar,
                            fitArtifact=req.fit, startFrom=req.startFrom or "records",
                            durationPreset=req.durationPreset or UNTIL_RUN_OUT_PRESET,
                            overrides=list(req.overrides))
    try:
        _check_request(sim)
        got = _bound(fam, sim, _load_pool())
    except SimulationRefused as e:
        raise params.ParamRefused(str(e)) from None
    return params.Provided(title=f"{fam.title} ({fam.id})", specs=got.specs, sources=got.sources, notes=got.notes,
                           unread=lambda values: _unread_words(fam, got.specs, values),
                           refuses=lambda values: run_refusal(fam, got.specs, values))


def _unread_words(fam: kinetics.Family, specs: list[ParameterSpec], values: list[ParameterValue]) -> dict[str, str]:
    """The keys the family's other values leave unread (`fam.irrelevant`, as
    `_waiting` skips them), each with why: its spec's note (§3.R, finding 16)."""
    spec_of = {s.key: s for s in specs}
    p: dict[str, Any] = {}
    for v in values:
        x = v.value
        p[v.key] = (x if spec_of[v.key].choices else None) if isinstance(x, str) else x
    return {k: (f"Not read with the other values as they stand, so it waits for nothing: "
                f"{spec_of[k].note or 'this setting of the family does not read it'}")
            for k in fam.irrelevant(p) if k in spec_of}


def _family_static():
    for fid, fam in kinetics.FAMILIES.items():
        yield f"fermos family {fid}", fam.specs()


# ── a forecast's start values and length, in the panel (§3.3, E.1‴) ─────
#
# A forecast of a logistic_v0 fit starts from the fitted run's own X0, S0 and
# P0 and runs the run's own length unless a person names others. Those are
# the scope `fermos:forecast:<kinetic fit artifact id>`: the batch family's
# own declarations of the start values and run length (kinetics.py), in the
# units of the fit's series (a forecast's start values are the run's
# readings' units), each bound to the fit and overridable by a named person,
# so FermOS*.tsx renders no number box of its own. A batch_v1 fit is
# simulated from, not forecast: its start values and run length are its
# family's scope (`fermos:family:batch_v1`), started from the fit.

FORECAST_KEYS = (("x0", "X0", "biomass"), ("s0", "S0", "substrate"), ("p0", "P0", "product"))
FORECAST_SCOPE_NOTES = [
    "A forecast starts from the fitted run's own values and runs its own length unless a person names others here: "
    "a changed start value or length is that person's assumption, named in the forecast's basis, and the forecast it "
    "makes is assumed.",
    "A low and a high typed here are not read: a forecast starts from one value, and its band comes from the fit.",
]


def forecast_scope(fit_id: str) -> str:
    return params.scope_name("fermos-forecast", fit_id)


def _forecast_specs(unit_of: dict[str, str]) -> list[ParameterSpec]:
    """The start values the fit has, in its series' units, and the run
    length: batch_v1's own declarations, bound to the fit or a person."""
    base = {s.key: s for s in kinetics.family("batch_v1").specs()}
    out = []
    for key, _, role in FORECAST_KEYS:
        if key not in unit_of:
            continue
        b, u = base[key], unit_of[key]
        out.append(b.model_copy(update={
            "unit": u, "dimension": units.family(u) or "a reading", "sourceRule": ["fit", "assumption"],
            "gloss": f"{b.gloss}, in the unit of the run's {role} series",
            "note": f"The fitted run's own {b.symbol} unless a person names another (a forecast's start value).",
            "convention": None}))
    t = base["t_end"]
    out.append(t.model_copy(update={
        "label": "forecast length", "gloss": "how long the forecast runs", "sourceRule": ["fit", "assumption"],
        "note": "The length of the run the fit was made on, its last reading, unless a person names another.",
        "convention": None}))
    return out


def _forecast_static():
    yield "fermos forecast of a logistic_v0 fit", _forecast_specs({k: G_L for k, _, _ in FORECAST_KEYS})


def forecast_provided(ids: tuple[str, ...], req: ParamResolveRequest) -> params.Provided:
    """The `fermos-forecast` scope (`fermos:forecast:<kinetic fit id>`):
    a logistic_v0 fit's start values and run length, each bound to the
    fitted run's own, a person's overrides laid on them (params.resolve).
    A fit not on file is a 404; a fit of a family, a forecast or another
    artifact, or a fit that holds no parameters, a 422 in words."""
    (fit_id,) = ids
    try:
        art = artifacts.get(fit_id)
    except artifacts.ArtifactNotFound:
        raise params.ScopeUnknown(f"there is no kept kinetic fit {fit_id}: fermOS keeps a fit when it fits a "
                                  "deposited run") from None
    except artifacts.ArtifactDamaged as e:
        raise params.ParamRefused(f"fit {fit_id} cannot be read: {e}") from None
    if art.tool != KINETIC:
        raise params.ParamRefused(f"{fit_id} is a {art.tool}; a forecast is drawn from a kinetic fit")
    fit_ = KineticFit.model_validate(art.output)
    if fit_.model != LOGISTIC:
        raise params.ParamRefused(f"fit {fit_id} fits {fit_.model}, which is simulated from its parameters, not "
                                  f"forecast: its start values and run length are {family_scope(fit_.model)}'s, "
                                  "started from the fit")
    if fit_.reason or not fit_.params:
        raise params.ParamRefused(f"fit {fit_id} holds no kinetic fit: {fit_.reason or 'no parameters'}")
    roles = series_by_role(fit_)
    unit_of = {key: roles[role].unit for key, name, role in FORECAST_KEYS if role in roles and param(fit_, name)}
    sources: dict[str, dict[str, ParameterValue | None]] = {}
    for key, name, _ in FORECAST_KEYS:
        if key not in unit_of:
            continue
        p = param(fit_, name)
        note = f"{name} of {LOGISTIC} kinetic fit {fit_id}: the fitted run's own, with its 95 % interval"
        sources[key] = {"fit": ParameterValue(key=key, value=p.value, low=p.low, high=p.high, identified=_identified(p),
                                              origin="fit", source=BasisSource(kind="artifact", id=fit_id, note=note),
                                              detail=note)}
    hours = [pt.t for sr in fit_.series for pt in sr.points]
    if hours and max(hours) > 0:
        note = f"the length of the run kinetic fit {fit_id} was made on: its last reading"
        sources["t_end"] = {"fit": ParameterValue(key="t_end", value=float(max(hours)), origin="fit",
                                                  source=BasisSource(kind="artifact", id=fit_id, note=note),
                                                  detail=note)}
    dep = deposition_of(art)
    title = f"Forecast of kinetic fit {fit_id}" + (f", fitted to deposition {dep}" if dep else "")
    return params.Provided(title=title, specs=_forecast_specs(unit_of), sources=sources, notes=list(FORECAST_SCOPE_NOTES))


def _check_request(req: SimulationRequest) -> None:
    """A request that cannot stand, refused in words, never ignored: a start
    that is not records, a fit or simulation:<artifact id>; a start from a
    fit, or a fit's run length, with no fit named; an id that is not one; a
    sugar the carbon-source vocabulary does not hold."""
    start = req.startFrom or "records"
    if start not in ("records", "fit") and not start.startswith(SIM_PREFIX):
        raise SimulationRefused(f"a simulation starts from records, a fit or simulation:<artifact id>; "
                                f"{start!r} is none of them")
    if start == "fit" and not req.fitArtifact:
        raise SimulationRefused("a simulation that starts from a fit names the fit: choose one (fitArtifact)")
    if req.durationPreset == FIT_LENGTH and not req.fitArtifact:
        raise SimulationRefused("the fit-length preset runs as long as the run a fit was made on, and no fit is named: "
                                "choose one (fitArtifact)")
    kept = start[len(SIM_PREFIX):] if start.startswith(SIM_PREFIX) else None
    for word, value in (("strain", req.strain), ("product", req.product), ("sugar", req.sugar),
                        ("fit", req.fitArtifact), ("kept simulation", kept)):
        if value is not None and not re.fullmatch(params._ID, value):
            raise SimulationRefused(f"a {word} is named by its id (letters, digits, dots, dashes, underscores); "
                                    f"{value!r} is not one")
    sugars = _sugars()
    if req.sugar and sugars and req.sugar not in sugars:
        raise SimulationRefused(f"a sugar is named by its carbon-source id, one of {', '.join(sorted(sugars))}; "
                                f"{req.sugar!r} is not one")


def _numbers(fam: kinetics.Family, specs: list[ParameterSpec],
             values: list[ParameterValue]) -> tuple[dict[str, Any], dict[str, Any], float | None]:
    """The parameters as kinetics reads them (a convention in words is the
    term off: None), the start values by state, and the run length; or the
    refusal naming every parameter that waits and what would bind it."""
    by_key = {v.key: v for v in values}
    spec_of = {s.key: s for s in specs}
    p: dict[str, Any] = {}
    for key, v in by_key.items():
        x = v.value
        if isinstance(x, str):
            p[key] = x if spec_of[key].choices else None
        elif x is None:
            p[key] = None
        else:
            p[key] = float(x)
    skip = fam.irrelevant(p)
    waiting = [by_key[s.key] for s in specs if by_key[s.key].origin == "waiting" and s.key not in skip]
    if waiting:
        lines = "; ".join(f"{v.key} ({spec_of[v.key].label}) {v.detail}" for v in waiting)
        raise SimulationRefused(f"{fam.id} cannot run yet: {len(waiting)} parameter"
                                f"{'s wait' if len(waiting) != 1 else ' waits'}. {lines}")
    y0 = {state: p.pop(key) for key, state in kinetics.START_STATE.items() if key in p}
    t_end = p.pop("t_end", None)
    return p, y0, t_end


def _source_words(v: ParameterValue) -> str:
    """Where a value came from, in a few words, for a refusal naming it."""
    src = v.source
    if v.overriddenBy:
        return f"typed by {v.overriddenBy}"
    if v.origin == "fit" and src is not None and src.id:
        return f"from fit {src.id}"
    if v.origin == "simulation" and src is not None and src.id:
        return f"from simulation {src.id}"
    if v.origin == "record":
        return f"from {len(v.recordIds)} record{'s' if len(v.recordIds) != 1 else ''}"
    return f"its {v.origin}"


def run_refusal(fam: kinetics.Family, specs: list[ParameterSpec], values: list[ParameterValue]) -> str | None:
    """What a simulation of these values would be refused for though
    nothing waits (OF-BLD-020 §8.R, findings 12 and 14), in the words the run
    refuses with, or None when it would go ahead. One function for the run
    (`simulate`), the panel's resolve (a 422) and `bind` (its `refused`, so
    Simulate holds its button): a start value below zero names its key, its
    value and where it came from (a logistic fit's P0 lands below zero on
    noisy readings), and every other check is the family's own
    (`_prepared`, `y0_of`, `check`), run before anything integrates. A value
    that waits is said by `waiting`, not here."""
    try:
        p, y0, t_end = _numbers(fam, specs, values)
    except SimulationRefused:
        return None
    by_key = {v.key: v for v in values}
    unit_of = {s.key: s.unit for s in specs}
    for key, state in kinetics.START_STATE.items():
        x = y0.get(state)
        if key in by_key and isinstance(x, (int, float)) and not isinstance(x, bool) and x < 0:
            v = by_key[key]
            unit = f" {unit_of.get(key)}" if unit_of.get(key) else ""
            return (f"{key} is {x:g}{unit}, {_source_words(v)}: a start value cannot be negative; type {key} under your "
                    "name in the panel, or choose another source")
    try:
        prepared = fam._prepared(p)
        fam.y0_of(y0, prepared)
        fam.check(prepared, t_end)
    except kinetics.FamilyRefused as e:
        return str(e)
    return None


def _ceiling_inputs(req: SimulationRequest) -> tuple[list[BasisInput], list[str]]:
    """The newest stored geneOS ceiling of each host model of the strain, on
    the sugar, named in the basis (an artifact input, compared beside the
    result, never a bound), or a convention input saying none is on file."""
    from . import geneos_models, proforma

    if not (req.strain and req.product and req.sugar):
        return [], ["No strain, product and sugar were all named, so no geneOS ceiling is read beside this simulation."]
    if req.product not in geneos_models.PRODUCTS:
        return [], [f"geneOS computes no ceiling for {req.product}, so none is read beside this simulation."]
    out = []
    for m, how, words in proforma.host_models(req.product, req.strain):
        on = proforma.stored_ceilings(m.id, req.product, req.sugar)
        if on:
            out.append(BasisInput(name=f"ceiling {m.id}", value=on[0].id, unit="g g⁻¹",
                                  source=BasisSource(kind="artifact", id=on[0].id,
                                                     note=f"{how}: {words}; set beside Yp/s, never a bound")))
        else:
            out.append(BasisInput(name=f"ceiling {m.id}", value="none on file", unit="",
                                  source=BasisSource(kind="convention", note=f"{how}: {words}; no geneOS ceiling on "
                                                                              f"{req.sugar} is on file for it")))
    return out, []


def _solver_inputs() -> list[BasisInput]:
    s = kinetics.SETTINGS
    return [
        BasisInput(name="solver", value="scipy solve_ivp, LSODA", unit="",
                   source=BasisSource(kind="convention", note=f"the integrator (scipy {kinetics.versions()['scipy']})")),
        BasisInput(name="rtol", value=kinetics.RTOL, unit="", source=BasisSource(kind="convention", note=s["RTOL"])),
        BasisInput(name="atol", value=kinetics.ATOL, unit=G_L, source=BasisSource(kind="convention", note=s["ATOL"])),
        BasisInput(name="run-out share", value=kinetics.RUN_OUT_SHARE, unit="",
                   source=BasisSource(kind="convention", note=s["RUN_OUT_SHARE"])),
        BasisInput(name="mass balance closure", value=kinetics.BALANCE_TOL, unit="",
                   source=BasisSource(kind="convention", note=s["BALANCE_TOL"])),
        BasisInput(name="points", value=kinetics.POINTS, unit="", source=BasisSource(kind="convention", note=s["POINTS"])),
    ]


# ── binding: a fit, the records, a kept simulation, a person (§3.2, D6) ─

SIM_PREFIX = "simulation:"
UNTIL_RUN_OUT_PRESET = "until-sugar-runs-out"
FIT_LENGTH = "fit-length"
# What a logistic_v0 fit carries into a family's parameters, by spec key: its
# μ read as μmax (a logistic's rate is the growth rate with nothing yet
# limiting), its Luedeking–Piret coefficients, and its start values. Its Xmax
# has no parameter: in a family growth stops where the sugar, Pmax or the
# second nutrient stops it. Yp/s comes through its forecast (fit_info).
FROM_LOGISTIC = {"mu_max": "mu", "alpha": "alpha", "beta": "beta", "x0": "X0", "s0": "S0", "p0": "P0"}
# A value bound to a fit or a kept simulation names that artifact as its
# source; the basis says which it was, and whether the fit's run identified
# it, in one `<key> origin` input beside it, so a simulation reads its
# parameters back from its own basis and nothing else.
ORIGIN = "origin"
ORIGIN_WORDS = {"fit": True, "fit, not identified": False, "fit, identification not judged": None}
ORIGIN_NOTE = ("where the value came from, as the binding chose it (OF-BLD-020 D6): a fit a person chose, and whether "
               "the run it was fitted to identified it (its interval excludes zero), or a kept simulation")
RECORDS_OF = "records of"
# The `<key> origin` word beside a value bound to the records a request named
# for it (recordsByParam, OF-BLD-020 §3.4): those records alone bind it, and
# `records of` says nothing of them.
NAMED = "records named"
NAMED_NOTE = ("where the value came from (OF-BLD-020 §3.4): the records the request named for it by id, each in the "
              "evidence pool, of a field it binds from, through the aggregate gate and units.py; no strain, sugar or "
              "program filter chose them")


def _load_pool() -> Any:
    """The evidence pool, or an empty one when none can be read here
    (nothing is known, so nothing binds)."""
    from types import SimpleNamespace

    from . import evidence_pool

    try:
        return evidence_pool.load()
    except FileNotFoundError:
        return SimpleNamespace(records=[], records_by_id={})


def _sugars() -> set[str]:
    from . import validate

    try:
        return set(validate.vocabulary()["carbon"].values())
    except (FileNotFoundError, ValueError):
        return set()


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _g(x: float) -> str:
    return f"{x:.4g}"


class _Context:
    """Who and what a binding is for: the strain chosen or none, the sugar,
    the product, and the words that say each. Every record the evidence pool
    holds may bind."""

    def __init__(self, fam: kinetics.Family, req: SimulationRequest) -> None:
        from . import module_stores, proforma

        self.labels, _ = proforma._strain_labels()
        self.strain, self.sugar, self.product = req.strain, req.sugar, req.product
        hosts: list[str] = []
        try:
            hosts = [h["id"] for h in module_stores._projection()["geneos"]["hosts"] if h.get("id")]
        except (module_stores.ProjectionMissing, KeyError, TypeError, ValueError):
            pass
        if self.strain and hosts and self.strain not in hosts:
            raise SimulationRefused(f"there is no catalogued strain {self.strain}: a strain is named by its id in "
                                    f"geneOS's hosts, such as {', '.join(sorted(hosts)[:4])}")
        # Every record the pool holds may bind; projects scope the pool from
        # alpha 2.0 stage 2 on (ADR-005).
        self.pool_words = "every paper the evidence pool holds"
        self.strain_label = self.labels.get(self.strain or "", self.strain or "")
        self.organism_words = f"every strain on {self.pool_words}"

    def of_strain(self, r: dict[str, Any]) -> bool:
        from . import validate

        if r.get("strainId") == self.strain:
            return True
        try:
            return bool(r.get("organismText")) and validate.strain_id(str(r["organismText"])) == self.strain
        except (FileNotFoundError, ValueError):
            return False


class _Bound:
    """One field's records as a binding takes them: the kept ones with their
    value in the spec's unit, and every one left out, counted by why."""

    def __init__(self) -> None:
        self.kept: list[tuple[dict[str, Any], float]] = []
        self.out: dict[str, int] = {}
        self.unconverted: list[str] = []

    def leave(self, why: str) -> None:
        self.out[why] = self.out.get(why, 0) + 1

    def words(self) -> str:
        parts = [f"{n} {why}" for why, n in self.out.items()]
        if self.unconverted:
            parts.append(f"{len(self.unconverted)} in a unit units.py does not convert ("
                         + "; ".join(self.unconverted[:3]) + ("; …" if len(self.unconverted) > 3 else "") + ")")
        return ("left out: " + ", ".join(parts)) if parts else ""


def _field_records(field: str, unit: str, ctx: _Context, pool: Any) -> _Bound:
    """The records of one field that bind, in `unit`, and the rest counted."""
    from . import validate

    rule = kinetics.CARBON_RULE.get(field, "sugar")
    by_strain = bool(ctx.strain) and field not in kinetics.STRAIN_FREE
    out = _Bound()
    for r in pool.records:
        if r.get("field") != field:
            continue
        if binding.exclusion(r):
            out.leave("kept out by the aggregate gate")
            continue
        if by_strain and not ctx.of_strain(r):
            out.leave("of another strain or of none")
            continue
        if rule != "any":
            carbon = r.get("carbonSource")
            if not carbon:
                if rule == "sugar":
                    out.leave("naming no carbon source")
                    continue
            else:
                try:
                    named = validate.carbon_source_id(str(carbon))
                except (FileNotFoundError, ValueError):
                    named = None
                if named != ctx.sugar:
                    out.leave("naming another carbon source")
                    continue
        try:
            v = units.convert(float(r["value"]), r.get("unit") or unit, unit)
        except (TypeError, ValueError, KeyError) as e:
            why = units.explain_refusal(str(r.get("unit") or ""), unit) or str(e)
            out.unconverted.append(f"{r.get('id')}: {r.get('unit')}, {why}")
            continue
        out.kept.append((r, v))
    return out


def _record_candidate(spec: ParameterSpec, entry: str, ctx: _Context, pool: Any) -> tuple[ParameterValue | None, str]:
    """What one `record:<field>` entry binds for a spec, or why it binds
    nothing, in words."""
    field = entry.split(":", 1)[1]
    own = kinetics.PRODUCT_OWN.get(field)
    if own and own != ctx.product:
        swap = kinetics.PRODUCT_FIELDS.get(ctx.product or "", {}).get(field)
        if not swap:
            return None, (f"{field} is {own}'s own field, and " + (f"the product is {ctx.product}" if ctx.product
                                                                    else "no product is named"))
        field = swap
    rule = kinetics.CARBON_RULE.get(field, "sugar")
    if rule != "any" and not ctx.sugar:
        return None, f"a record of {field} binds on the sugar it names, and no sugar is named"
    got = _field_records(field, spec.unit, ctx, pool)
    on = {"sugar": f" on {ctx.sugar}", "sugar or none": f" on {ctx.sugar} or naming no carbon source",
          "any": ""}[rule]
    whose = (f", for {ctx.strain_label}" if ctx.strain and field not in kinetics.STRAIN_FREE else "")
    left = got.words()
    if not got.kept:
        return None, f"no record of {field}{on}{whose} binds" + (f" ({left})" if left else "")
    st = binding.statistic([v for _, v in got.kept])
    n = len(got.kept)
    unit = f" {spec.unit}" if spec.unit else ""
    span = f"{_g(st.low)}{unit}" if st.low == st.high else f"{_g(st.low)}–{_g(st.high)}{unit}"
    stat = {"triangular": f", the median {_g(st.value)}", "uniform": f", the middle {_g(st.value)}"}.get(st.sampling, "")
    detail = f"{_plural(n, 'record')} of {field}{on}{whose}: {span}{stat}" + (f"; {left}" if left else "")
    if st.flag and n > 1:
        detail += "; every one gives the same value"
    return ParameterValue(key=spec.key, value=st.value, low=st.low, high=st.high,
                          source=BasisSource(kind="record", note=f"{_plural(n, 'record')} of {field}"),
                          origin="record", recordIds=[str(r["id"]) for r, _ in got.kept], detail=detail), ""


def _record_fields(spec: ParameterSpec, ctx: _Context) -> tuple[list[str], list[str]]:
    """The record fields a spec binds from for this product (a field one
    product owns gives way to the product's own, kinetics.PRODUCT_FIELDS),
    and why each field that cannot bind here does not, in words."""
    fields, why = [], []
    for entry in spec.sourceRule:
        if not entry.startswith("record:"):
            continue
        field = entry.split(":", 1)[1]
        own = kinetics.PRODUCT_OWN.get(field)
        if own and own != ctx.product:
            swap = kinetics.PRODUCT_FIELDS.get(ctx.product or "", {}).get(field)
            if not swap:
                why.append(f"{field} is {own}'s own field, and "
                           + (f"the product is {ctx.product}" if ctx.product else "no product is named"))
                continue
            field = swap
        if field not in fields:
            fields.append(field)
    return fields, why


def _named_records(spec: ParameterSpec, ids: list[str], ctx: _Context, pool: Any) -> ParameterValue:
    """A parameter bound to exactly the records a request named for it
    (`recordsByParam`, OF-BLD-020 §3.4, D13): each must be in the evidence
    pool, be a record of a field the spec binds from, pass
    the aggregate gate and convert into the spec's unit; any one that does
    not refuses the request, naming the record and why. Their value is
    Proforma's statistic over them, as the records the rule finds bind; no
    strain or sugar filter is applied, since the records were chosen by id,
    and the detail says they were named."""
    if not ids:
        raise SimulationRefused(f"recordsByParam names no record for {spec.key}: name the records that bind it, or "
                                "leave it out and the records the rule finds bind it")
    fields, why = _record_fields(spec, ctx)
    if not fields:
        said = "; ".join(why) if why else f"its sources are {', '.join(spec.sourceRule) or 'none'}"
        raise SimulationRefused(f"{spec.key} ({spec.label}) binds from no record field here, so no record can be named "
                                f"for it: {said}")
    by_id = getattr(pool, "records_by_id", None) or {str(r.get("id")): r for r in getattr(pool, "records", [])}
    seen: set[str] = set()
    kept: list[tuple[str, float, str]] = []
    for rid in ids:
        if not isinstance(rid, str) or not re.fullmatch(params._ID, rid):
            raise SimulationRefused(f"a record is named by its id (letters, digits, dots, dashes, underscores); "
                                    f"{rid!r}, named for {spec.key}, is not one")
        if rid in seen:
            raise SimulationRefused(f"record {rid} is named twice for {spec.key}: name each record once")
        seen.add(rid)
        r = by_id.get(rid)
        if r is None:
            raise SimulationRefused(f"record {rid}, named for {spec.key}, is not in the evidence pool: "
                                    "search_records finds the records that are")
        field = str(r.get("field") or "")
        if field not in fields:
            raise SimulationRefused(f"record {rid} is a record of {field or 'no field'}, and {spec.key} ({spec.label}) "
                                    f"binds from {' or '.join(fields)}")
        gate = binding.exclusion(r)
        if gate:
            raise SimulationRefused(f"record {rid}, named for {spec.key}, is kept out by the aggregate gate: {gate}")
        try:
            v = units.convert(float(r["value"]), r.get("unit") or spec.unit, spec.unit)
        except (TypeError, ValueError, KeyError) as e:
            said = units.explain_refusal(str(r.get("unit") or ""), spec.unit) or str(e)
            raise SimulationRefused(f"record {rid}, named for {spec.key}, is in {r.get('unit')!r}, which units.py does "
                                    f"not convert into {spec.unit or 'a number'}: {said}") from None
        kept.append((rid, v, field))
    st = binding.statistic([v for _, v, _ in kept])
    n = len(kept)
    named_fields = sorted({f for _, _, f in kept})
    unit = f" {spec.unit}" if spec.unit else ""
    span = f"{_g(st.low)}{unit}" if st.low == st.high else f"{_g(st.low)}–{_g(st.high)}{unit}"
    stat = {"triangular": f", the median {_g(st.value)}", "uniform": f", the middle {_g(st.value)}"}.get(st.sampling, "")
    what = f"{_plural(n, 'record')} of {' and '.join(named_fields)}, named for it"
    detail = f"{what}: {span}{stat}"
    if st.flag and n > 1:
        detail += "; every one gives the same value"
    return ParameterValue(key=spec.key, value=st.value, low=st.low, high=st.high,
                          source=BasisSource(kind="record", note=what), origin="record",
                          recordIds=[rid for rid, _, _ in kept], detail=detail)


def _identified(p: FitParam) -> bool | None:
    """Whether the run a fit was made on identified a parameter: its own
    word, else its interval excluding zero for a coefficient, else unjudged."""
    if p.identified is not None:
        return p.identified
    if p.indistinguishableFromZero is not None:
        return not p.indistinguishableFromZero
    return None


def _fit_art(fit_id: str) -> Any:
    try:
        art = artifacts.get(fit_id)
    except artifacts.ArtifactNotFound:
        raise SimulationRefused(f"there is no kept fit {fit_id}: fermOS keeps a fit when it fits a deposited run, and "
                                "a forecast when one is made from it") from None
    except artifacts.ArtifactDamaged as e:
        raise SimulationRefused(f"fit {fit_id} cannot be read: {e}") from None
    if art.tool not in FEEDABLE:
        raise SimulationRefused(f"{fit_id} is a {art.tool}, not a kinetic fit or a forecast fermOS keeps")
    return art


def _fit_candidates(fit_id: str, fam: kinetics.Family, specs: dict[str, ParameterSpec], ctx: _Context,
                    preset: str,
                    x0: float | None = None) -> tuple[dict[str, ParameterValue], list[str]]:
    """What a chosen fit gives each parameter it carries, in the spec's unit,
    with its interval and whether its run identified it, and why not (the
    reason the fit kept); and what it could not give, in words. A fit of
    another family is refused.

    A forecast chosen as the fit (OF-BLD-020 §3.R, finding 13) gives what it
    holds: the start values and length it was drawn under, each credited to
    it with the person its basis names, and its Yp/s as kept; the rates it
    took unchanged from the kinetic fit it rests on are credited to that fit.
    A fit of the family's own model gives the terms it held as conventions
    (HELD_INTO_SIMULATION) as it held them (finding 4), so a simulation
    started from it is the model that was fitted. A fit of a run with no
    biomass series gives its gauge as X0; `x0`, a person's X0 in its place,
    rescales Yx/s, α and β from the gauge to that scale, each one's source
    saying so (findings 0 and 8)."""
    from . import proforma

    art = _fit_art(fit_id)
    try:
        fit_ = fit_of(art)
    except FitRefused as e:
        raise SimulationRefused(str(e)) from None
    if fit_.reason or not fit_.params:
        raise SimulationRefused(f"fit {fit_id} holds no kinetic fit: {fit_.reason or 'no parameters'}")
    model = fit_.model
    if model == fam.id:
        names = {k: k for k in specs}
    elif model == LOGISTIC:
        names = {k: n for k, n in FROM_LOGISTIC.items() if k in specs}
    else:
        raise SimulationRefused(f"fit {fit_id} is of {model}; a {fam.id} simulation takes a fit of its own family or "
                                f"a {LOGISTIC} fit")
    dep = deposition_of(art)
    what = f"{model} {art.tool} {fit_id}" + (f", fitted to deposition {dep}" if dep else "")
    # A forecast holds its start values and length; its rates are its fit's.
    under = fit_artifact_of(art) if art.tool == FORECAST else None
    rates = (f"{model} {KINETIC} {under}, which forecast {fit_id} rests on"
             + (f", fitted to deposition {dep}" if dep else "")) if under else what
    started = {x.name.split(" ", 1)[1]: x for x in art.inputs if x.name.startswith("start ")} if under else {}
    roles = series_by_role(fit_)
    notes: list[str] = []
    out: dict[str, ParameterValue] = {}

    def factor(key: str, unit: str) -> float:
        """The number one of the fit's units is in the spec's unit."""
        if model == LOGISTIC and key in ("alpha", "beta"):
            pu, xu = (roles.get(r).unit if roles.get(r) else "" for r in ("product", "biomass"))
            return units.convert(1.0, pu, G_L) / units.convert(1.0, xu, G_L)
        return units.convert(1.0, unit, specs[key].unit)

    for key, name in names.items():
        p = param(fit_, name)
        if p is None:
            continue
        try:
            k = factor(key, p.unit)
        except (TypeError, ValueError):
            notes.append(f"Fit {fit_id} gives {specs[key].symbol or key} in {p.unit}, which does not convert into "
                         f"{specs[key].unit or 'a number'}, so it does not bind {key}.")
            continue
        symbol = specs[key].symbol or key
        if name in started:
            # The value the forecast was drawn from, a person's assumption in
            # its basis: credited to the forecast, with the person named.
            x = started[name]
            who = f", set by {x.source.by}" if x.source.by else ""
            note = f"{symbol} forecast {fit_id} started from{who} (an assumption in its basis)"
            out[key] = ParameterValue(key=key, value=float(x.value) * k, low=float(x.value) * k, high=float(x.value) * k,
                                      identified=None, origin="fit", source=BasisSource(kind="artifact", id=fit_id,
                                                                                        note=note), detail=note)
            continue
        identified = _identified(p)
        said = "" if identified is not False else f"; {NOT_IDENTIFIED}{unidentified_words(p)}"
        out[key] = ParameterValue(
            key=key, value=p.value * k, low=p.low * k, high=p.high * k, identified=identified, origin="fit",
            source=BasisSource(kind="artifact", id=under or fit_id,
                               note=f"{symbol} of {rates}, with its 95 % interval{said}"),
            detail=f"{symbol} of {rates}{said}")
    gauge = None
    if model == fam.id and "x0" in specs and "biomass" not in roles:
        gp = param(fit_, "x0")
        gauge = gp.value if gp is not None else X0_GAUGE
        if gp is None:
            # A fit kept before it carried its gauge: family_fit held X0 at
            # X0_GAUGE, the only gauge it has held.
            note = (f"X0 of {what}, held at the gauge family_fit holds, {_g(gauge)} {G_L} (the fit was kept before "
                    f"it carried it); {NOT_IDENTIFIED}{X0_GAUGE_WORDS}")
            out["x0"] = ParameterValue(key="x0", value=gauge, low=gauge, high=gauge, identified=False, origin="fit",
                                       source=BasisSource(kind="artifact", id=fit_id, note=note), detail=note)
    if gauge and x0 is not None and x0 != gauge:
        c = x0 / gauge
        for key in SCALED_WITH_X:
            v = out.get(key)
            if v is None:
                continue
            k = c if key == "yxs" else 1 / c
            how = (f"rescaled from the fit's gauge X0 of {_g(gauge)} {G_L} to the X0 a person gave, {_g(x0)} {G_L} "
                   f"(× {_g(k)})")
            out[key] = v.model_copy(update={
                "value": v.value * k, "low": v.low * k if v.low is not None else None,
                "high": v.high * k if v.high is not None else None, "detail": f"{v.detail}; {how}",
                "source": v.source.model_copy(update={"note": f"{v.source.note}; {how}"})})
        notes.append(f"Fit {fit_id} has no biomass series, so it held X0 at a gauge of {_g(gauge)} {G_L}; a person "
                     f"gave X0 as {_g(x0)} {G_L}, so Yx/s is multiplied and α and β divided by {_g(c)} to that scale: "
                     "the sugar and product simulated are the fit's, the cells the person's scale (OF-BLD-020 §3.R).")
    if model == LOGISTIC and "yps" in specs:
        flowsheet = next((f for f, made in proforma.PRODUCTS.items() if made == ctx.product), None)
        if flowsheet is None:
            notes.append(f"A {LOGISTIC} fit gives Yp/s through its forecast, read for the product a shelf flowsheet "
                         f"makes ({', '.join(sorted(set(proforma.PRODUCTS.values())))}); "
                         + (f"{ctx.product} is not one" if ctx.product else "no product is named")
                         + f", so fit {fit_id} does not bind yps.")
        else:
            info = proforma.fit_info(art, flowsheet)
            feed = next((f for f in info.feeds if f.key == "yield"), None)
            why = info.refused or (feed.refused if feed else "it gives no yield")
            if why or feed is None or feed.value is None:
                notes.append(f"Fit {fit_id} gives no Yp/s: {why}.")
            else:
                k = units.convert(1.0, feed.unit, specs["yps"].unit)
                out["yps"] = ParameterValue(
                    key="yps", value=feed.value * k, low=feed.low * k if feed.low is not None else None,
                    high=feed.high * k if feed.high is not None else None, identified=True, origin="fit",
                    source=BasisSource(kind="artifact", id=fit_id, note=f"Yp/s of {what}: {feed.derivation}"),
                    detail=f"Yp/s of {what}: {feed.derivation}")
    ran = _named(art.inputs, "duration") if under else None
    if preset == FIT_LENGTH and "t_end" in specs and ran is not None:
        # The length the forecast was drawn over, as its basis names it.
        who = f", set by {ran.source.by}" if ran.source.by else ", as asked"
        note = f"the length forecast {fit_id} ran{who}"
        out["t_end"] = ParameterValue(key="t_end", value=float(ran.value), origin="fit",
                                      source=BasisSource(kind="artifact", id=fit_id, note=note), detail=note)
    elif preset == FIT_LENGTH and "t_end" in specs:
        hours = [pt.t for sr in fit_.series for pt in sr.points]
        if hours and max(hours) > 0:
            out["t_end"] = ParameterValue(
                key="t_end", value=float(max(hours)), origin="fit",
                source=BasisSource(kind="artifact", id=fit_id, note=f"the length of the run {what}: its last reading"),
                detail=f"the length of the run {what}: its last reading")
        else:
            notes.append(f"Fit {fit_id} holds no reading after its start, so it gives no run length.")
    if model == fam.id:
        held = {i.name: i for i in art.inputs if i.source.kind == "convention"}
        for key in HELD_INTO_SIMULATION:
            i = held.get(key)
            if i is None or key not in specs or "fit" not in specs[key].sourceRule:
                continue
            note = f"{specs[key].symbol or key} as {what} held it, a convention of the fit: {i.source.note}"
            value = i.value if isinstance(i.value, str) else float(i.value)
            out[key] = ParameterValue(key=key, value=value, low=None if isinstance(value, str) else value,
                                      high=None if isinstance(value, str) else value, identified=None, origin="fit",
                                      source=BasisSource(kind="artifact", id=fit_id, note=note), detail=note)
        rest = ", ".join(k for k, _, _ in FIT_HELD if k not in HELD_INTO_SIMULATION)
        notes.append(f"Fit {fit_id} held what one batch's readings cannot pin as conventions; a simulation from it "
                     f"takes {', '.join(HELD_INTO_SIMULATION)} as the fit held them, so it is the model that was "
                     f"fitted, and a person's override still wins. {rest} shape no state the fit read, so they bind "
                     "as their specs say.")
    return out, notes


def _simulation_candidates(sim_id: str, specs: dict[str, ParameterSpec]) -> tuple[dict[str, ParameterValue], list[str]]:
    """A kept simulation's values for the keys this family shares with it:
    each one it took from a fit, the records, another simulation or a named
    person (a convention binds here as its spec says)."""
    art = kept_simulation(sim_id)
    fid = _named(art.inputs, "family")
    other = kinetics.family(str(fid.value)) if fid else None
    if other is None:
        raise SimulationRefused(f"kept simulation {sim_id} names no family")
    out: dict[str, ParameterValue] = {}
    for v in _values_of(other.specs(), art.inputs):
        if v.key not in specs or v.origin in ("waiting", "convention") or v.value is None:
            continue
        how = f"{v.origin} by {v.overriddenBy}" if v.overriddenBy else v.origin
        note = f"{v.key} of kept simulation {sim_id} ({other.id}), where it was bound to {how}"
        out[v.key] = ParameterValue(key=v.key, value=v.value, low=v.low, high=v.high, origin="simulation",
                                    source=BasisSource(kind="artifact", id=sim_id, note=note), detail=note)
    return out, [f"Starting from kept simulation {sim_id} ({other.id}): its values bind where no fit or record "
                 "does, before a person's (D6)."]


def _persons_x0(fam: kinetics.Family, req: SimulationRequest) -> float | None:
    """The X0 a person gave in this request's overrides of the family's
    scope, when it is a number above zero: what a gauged fit's Yx/s, α and β
    are rescaled to (§3.R). Anything else rescales nothing, and the
    override's own check refuses it where it cannot stand."""
    scope = family_scope(fam.id)
    x = next((o.value for o in req.overrides if o.key == "x0" and o.scope == scope), None)
    return float(x) if kinetics._finite(x) and x > 0 else None


class _Binding:
    def __init__(self, specs, sources, notes, ctx, named=()) -> None:
        self.specs: list[ParameterSpec] = specs
        self.sources: dict[str, dict[str, ParameterValue | None]] = sources
        self.notes: list[str] = notes
        self.ctx: _Context = ctx
        # The keys bound to the records the request named for them (§3.4).
        self.named: frozenset[str] = frozenset(named)


def _bound(fam: kinetics.Family, req: SimulationRequest, pool: Any) -> _Binding:
    """Each spec's candidates by sourceRule entry (params.Provided's
    `sources`), and the notes that say what was bound from where."""
    specs = fam.specs()
    by_key = {s.key: s for s in specs}
    ctx = _Context(fam, req)
    notes: list[str] = []
    if fam.socket:
        notes.append(fam.refusal())
    fits: dict[str, ParameterValue] = {}
    if req.fitArtifact:
        fits, said = _fit_candidates(req.fitArtifact, fam, by_key, ctx, req.durationPreset,
                                     _persons_x0(fam, req))
        notes += said
    start = req.startFrom or "records"
    kept: dict[str, ParameterValue] = {}
    if start.startswith(SIM_PREFIX):
        kept, said = _simulation_candidates(start[len(SIM_PREFIX):], by_key)
        notes += said
    named = dict(req.recordsByParam or {})
    stray = [k for k in named if k not in by_key]
    if stray:
        raise SimulationRefused(f"recordsByParam names {', '.join(stray)}, which {'is' if len(stray) == 1 else 'are'} "
                                f"no parameter of {fam.id}; its parameters are {', '.join(by_key)}")
    sources: dict[str, dict[str, ParameterValue | None]] = {}
    for spec in specs:
        if spec.key in named:
            # Exactly these records bind it (§3.4): the first record entry of
            # its sourceRule holds them, and nothing else is offered, so a
            # fit or a kept simulation does not stand in their place; a
            # person's override still wins (params.resolve).
            value = _named_records(spec, list(named[spec.key]), ctx, pool)
            entry = next(e for e in spec.sourceRule if e.startswith("record:"))
            set_aside = [w for w, there in (("the fit", spec.key in fits), ("the kept simulation", spec.key in kept))
                         if there]
            notes.append(f"{spec.key} is bound to the records named for it ({', '.join(value.recordIds)})"
                         + (f"; {' and '.join(set_aside)} would have bound it, and {'is' if len(set_aside) == 1 else 'are'} "
                            "set aside for it" if set_aside else "") + ".")
            sources[spec.key] = {entry: value}
            continue
        cands: dict[str, ParameterValue | None] = {}
        why: list[str] = []
        for entry in spec.sourceRule:
            if entry == "fit" and spec.key in fits:
                cands["fit"] = fits[spec.key]
            elif entry.startswith("record:"):
                found, words = _record_candidate(spec, entry, ctx, pool)
                if found is not None:
                    cands[entry] = found
                elif words:
                    why.append(words)
            elif entry == "simulation" and spec.key in kept:
                cands["simulation"] = kept[spec.key]
        if why:
            said = "; ".join(why)
            cands["waiting"] = ParameterValue(key=spec.key, value=None, source=None, origin="waiting",
                                              detail=said[:1].upper() + said[1:])
        sources[spec.key] = cands
    sugar = f", naming {ctx.sugar} as their carbon source" if ctx.sugar else ", and no sugar is named"
    notes.insert(0, f"Records bind from {ctx.pool_words}, through the aggregate gate, of "
                    + (f"{ctx.strain_label} (by its aliases; the medium's records of {ctx.organism_words})"
                       if ctx.strain else ctx.organism_words)
                    + f"{sugar}; each is converted into its parameter's unit, and the value is their median with their "
                      "range (Proforma's statistic). A fit a person chose comes first; a person's override wins over "
                      "all of them.")
    return _Binding(specs, sources, notes, ctx, named)


def bind_parameters(family: str, strain: str | None, product: str | None, sugar: str | None, pool: Any,
                    overrides: list[Override] | None, fit: str | None, by: str | None = None, *,
                    simulation: str | None = None,
                    duration_preset: str = UNTIL_RUN_OUT_PRESET,
                    records_by_param: dict[str, list[str]] | None = None) -> tuple[list[ParameterValue], list[str]]:
    """Each parameter of a family's specs with its value and source (D6): a
    fit a person chose, the records through the aggregate gate, a kept
    simulation (`simulation`, its artifact id), then a named person's
    override (which wins over all of them), then the spec's convention; and
    the keys that wait, as a run would refuse them (a key the request does
    not read waits for nothing). A key in `records_by_param` is bound to
    exactly the records named for it (§3.4), ahead of a fit or a kept
    simulation. Starts no integration and keeps nothing. Refused in words
    (SimulationRefused): a fit or simulation not on file, a fit of another
    family, an id that is not one, an unknown family, a named record that is
    not in the pool, of another field, kept out by the aggregate gate or in a
    unit units.py does not convert."""
    fam = kinetics.family(family)
    req = SimulationRequest(family=family, strain=strain, product=product, sugar=sugar, overrides=list(overrides or []),
                            fitArtifact=fit, startFrom=f"{SIM_PREFIX}{simulation}" if simulation else "records",
                            durationPreset=duration_preset, recordsByParam=dict(records_by_param or {}))
    _check_request(req)
    got = _bound(fam, req, pool)
    return _resolved(fam, got, req.overrides, by)


def _resolved(fam: kinetics.Family, got: _Binding, overrides: list[Override],
              by: str | None) -> tuple[list[ParameterValue], list[str]]:
    try:
        values = params.resolve(got.specs, got.sources, overrides, by)
    except params.ParamRefused as e:
        raise SimulationRefused(str(e)) from None
    return values, _waiting(fam, got.specs, values)


def _waiting(fam: kinetics.Family, specs: list[ParameterSpec], values: list[ParameterValue]) -> list[str]:
    """The keys a run would refuse for: every value that waits, but a key
    the request does not read (a feed's rate under an exponential profile)."""
    spec_of = {s.key: s for s in specs}
    p: dict[str, Any] = {}
    for v in values:
        x = v.value
        p[v.key] = (x if spec_of[v.key].choices else None) if isinstance(x, str) else x
    skip = fam.irrelevant(p)
    return [v.key for v in values if v.origin == "waiting" and v.key not in skip]


def bind(req: SimulationRequest, *, pool: Any = None) -> FermosBinding:
    """GET /api/fermos/bind: a family's parameters bound for a strain,
    product and sugar, from a fit or a kept simulation when one is named,
    over the evidence pool; what waits; and the notes that
    say what bound from where. Starts no integration and keeps nothing."""
    fam = kinetics.family(req.family)
    _check_request(req)
    _own_scope(fam, req.overrides)
    got = _bound(fam, req, pool if pool is not None else _load_pool())
    values, waiting = _resolved(fam, got, req.overrides, None)
    refused = None if waiting else run_refusal(fam, got.specs, values)
    return FermosBinding(values=values, waiting=waiting, refused=refused, notes=got.notes)


def _own_scope(fam: kinetics.Family, overrides: list[Override]) -> None:
    """An override names the scope it changes; one of another scope is
    refused in words, never laid on."""
    scope = family_scope(fam.id)
    stray = sorted({o.scope for o in overrides if o.scope != scope})
    if stray:
        raise SimulationRefused(f"an override names the scope it changes, and these were sent to {scope}: "
                                f"{', '.join(stray)}")


def _binding_inputs(got: _Binding, values: list[ParameterValue]) -> list[BasisInput]:
    """What the basis says of the binding beyond each value's own source:
    whose records bound (when any did), and, beside each value bound to a fit
    or a kept simulation, which it was (`<key> origin`)."""
    out: list[BasisInput] = []
    if any(v.origin == "record" and v.key not in got.named for v in values):
        ctx = got.ctx
        whose = (f"{ctx.strain} by its aliases, and the medium's records of {ctx.organism_words}" if ctx.strain
                 else ctx.organism_words)
        out.append(BasisInput(name=RECORDS_OF, value=whose, unit="", source=BasisSource(
            kind="convention", note=f"whose records bound the values bound to records: {ctx.pool_words}, through "
                                    "the aggregate gate (OF-BLD-020 §3.2)")))
    for v in values:
        if v.origin == "fit":
            word = next(w for w, i in ORIGIN_WORDS.items() if i is v.identified)
        elif v.origin == "simulation":
            word = "simulation"
        elif v.origin == "record" and v.key in got.named:
            word = NAMED
        else:
            continue
        out.append(BasisInput(name=f"{v.key} {ORIGIN}", value=word, unit="",
                              source=BasisSource(kind="convention", note=NAMED_NOTE if word == NAMED else ORIGIN_NOTE)))
    return out


def simulate(req: SimulationRequest, *, by_pool: Any = None) -> SimulationResult:
    """One simulation, kept as a `fermos.simulation` artifact. The family's
    specs bind as `bind_parameters` binds them (D6): a fit a person chose,
    the records of the evidence pool (`by_pool`, else
    evidence_pool.load), a kept simulation, a person's override (an
    `assumption` by name, which wins), the spec's stated convention; a
    parameter with none refuses the run naming it and the record field that
    would bind it (SimulationRefused, a 422). The basis names every value's
    source, the records each one rests on, and whose records they were."""
    fam = kinetics.family(req.family)
    if fam.socket:
        raise SimulationRefused(fam.refusal())
    _check_request(req)
    _own_scope(fam, req.overrides)
    pool = by_pool if by_pool is not None else _load_pool()
    got = _bound(fam, req, pool)
    specs = got.specs
    values, _ = _resolved(fam, got, req.overrides, None)
    _numbers(fam, specs, values)
    why = run_refusal(fam, specs, values)
    if why:
        raise SimulationRefused(why)
    named = [BasisInput(name="family", value=fam.id, unit="",
                        source=BasisSource(kind="convention", note=f"the model family: {fam.title} (kinetics.py)"))]
    for word, value in (("strain", req.strain), ("product", req.product), ("sugar", req.sugar)):
        if value:
            named.append(BasisInput(name=word, value=value, unit="",
                                    source=BasisSource(kind="convention", note=f"the {word} simulated, as named")))
    ceilings, _ = _ceiling_inputs(req)
    inputs = (named + params.basis_inputs(specs, values) + _binding_inputs(got, values) + _solver_inputs()
              + ceilings)
    art = artifacts.compute(SIMULATION, inputs, records_by_id=getattr(pool, "records_by_id", None))
    return result_of(art)


def result_of(art: Any) -> SimulationResult:
    return SimulationResult(**art.output, artifactId=art.id, provenance=art.provenance, basis=artifacts.basis_of(art))


def _values_of(specs: list[ParameterSpec], inputs: list[BasisInput]) -> list[ParameterValue]:
    """Each spec's value read back from a simulation's basis: its input,
    its low and high, the records behind it, and its origin from its
    source (the inverse of params.basis_inputs), a fit's or a kept
    simulation's from the `<key> origin` input beside it, with whether the
    fit's run identified it. Reads the basis alone."""
    by_name: dict[str, BasisInput] = {i.name: i for i in inputs}
    out = []
    for spec in specs:
        i = by_name.get(spec.key)
        if i is None:
            out.append(ParameterValue(key=spec.key, value=None, source=None, origin="waiting",
                                      detail=params._waiting_words(spec)))
            continue
        records = [str(x.value) for x in inputs if x.name == f"{spec.key} record" and x.source.kind == "record"]
        low, high = by_name.get(f"{spec.key} low"), by_name.get(f"{spec.key} high")
        kind = i.source.kind
        said = by_name.get(f"{spec.key} {ORIGIN}")
        word = str(said.value) if said is not None and said.source.kind == "convention" else None
        identified = ORIGIN_WORDS.get(word) if word in ORIGIN_WORDS else None
        origin = ("record" if records else "assumption" if kind == "assumption"
                  else "fit" if word in ORIGIN_WORDS or kind == "deposition"
                  else "simulation" if word == "simulation" else "artifact" if kind == "artifact" else "convention")
        v = ParameterValue(key=spec.key, value=i.value, low=float(low.value) if low else None,
                           high=float(high.value) if high else None, source=i.source, origin=origin,
                           identified=identified if origin == "fit" else None,
                           overriddenBy=i.source.by if kind == "assumption" else None, recordIds=records,
                           detail=i.source.note)
        v.outOfBounds = params.bounds_check(spec, v.value, v.low, v.high)
        out.append(v)
    return out


def _trajectory(inputs: list[BasisInput]) -> tuple[kinetics.Family, list[ParameterSpec], list[ParameterValue],
                                                    dict[str, Any], kinetics.Trajectory]:
    fid = _named(inputs, "family")
    if fid is None:
        raise SimulationRefused("a simulation's basis names its family")
    fam = kinetics.family(str(fid.value))
    specs = fam.specs()
    values = _values_of(specs, inputs)
    p, y0, t_end = _numbers(fam, specs, values)
    return fam, specs, values, p, fam.simulate(p, y0, t_end)


def _ceiling_block(inputs: list[BasisInput], yps: float | None, achieved: float | None) -> SimulationCeiling | None:
    from . import geneos_models

    strain, product, sugar = (_named(inputs, k) for k in ("strain", "product", "sugar"))
    marks = [i for i in inputs if i.name.startswith("ceiling ")]
    if not (strain and product and sugar) or str(product.value) not in geneos_models.PRODUCTS:
        return None
    product_label = geneos_models.PRODUCTS[str(product.value)]["label"]
    rows, waiting = [], []
    for i in marks:
        model_id = i.name.split(" ", 1)[1]
        how, _, words = (i.source.note or "").partition(": ")
        words = words.rsplit("; ", 1)[0]
        if i.source.kind != "artifact":
            waiting.append(model_id)
            continue
        art = artifacts.get(str(i.source.id))
        ceiling = float(art.output["gPerG"])
        above = yps is not None and yps > ceiling
        m = geneos_models.SHELF.get(model_id)
        rows.append(SimulationCeilingRow(
            modelId=model_id, modelName=m.name if m else model_id, match="strain" if how == "strain" else "species",
            matchWords=words, artifactId=art.id, provenance=art.provenance, ceilingGPerG=ceiling, ypsGPerG=yps,
            yieldAchievedGPerG=achieved, above=above,
            words=(f"Yp/s is above the most {model_id} makes from {sugar.value}: a yield above the network's ceiling "
                   "rests on another basis, or is wrong, so a reviewer should check what it was typed or bound from. "
                   "It is flagged, not clamped." if above else
                   f"Yp/s is at or under the most {model_id} makes from {sugar.value}.")))
    first = (rows[0].modelId if rows else waiting[0] if waiting else "")
    compute_at = f"/geneos/model?product={product.value}&substrate={sugar.value}" + (f"&model={first}" if first else "")
    empty = None
    if not marks:
        empty = (f"No reaction network on geneOS's shelf is of {strain.value}'s strain or species with a route to "
                 f"{product_label}, so no ceiling is read beside this simulation.")
    elif not rows:
        empty = (f"No geneOS ceiling for {product_label} on {sugar.value} is on file for {', '.join(waiting)}. One is "
                 f"computed in geneOS → Model, and a simulation made after it reads it.")
    return SimulationCeiling(product=str(product.value), sugar=str(sugar.value), strain=str(strain.value), rows=rows,
                             flagged=any(r.above for r in rows), empty=empty, computeAt=compute_at)


def _why_unidentified(v: ParameterValue) -> str:
    """Why a value bound to a fit is unidentified, as its own source says it
    (the binding wrote the fit's reason after NOT_IDENTIFIED): read from the
    basis alone, as a simulation reads everything."""
    said = (v.detail or "").partition(NOT_IDENTIFIED)[2]
    return said or "its source gives no reason"


def _steady_state(fam: kinetics.ChemostatV1, p: dict[str, Any], traj: kinetics.Trajectory) -> SteadyState:
    """chemostat_v1's steady state with the service's numbers in its words
    (OF-BLD-020 §3.R, findings 1 and 17): the culture's X, S, P and D·P, or
    washout; whether washout is a second stable state; which one this run's
    path reached by its end. A steady state the solver cannot find is a
    refusal in words, never a 500 (finding 2)."""
    try:
        ss = fam.steady_state(p)
    except kinetics.FamilyRefused:
        raise
    except (ValueError, FloatingPointError, ZeroDivisionError, OverflowError) as e:
        raise SimulationRefused(f"the chemostat's steady state cannot be solved for these parameters: {e}") from None
    reached = fam.reached(ss, traj)
    D, d5, dmax = ss["dilutionRate"], ss["dWashoutD5"], ss["dWashoutMax"]
    rates = (f"μ(Sf) − kd is {_g(ss['dWashout'])} h⁻¹, D5's μmax·Sf/(Ks + Sf) reads {_g(d5)}, and the most μ − kd "
             f"reaches over 0 to Sf with no product is {_g(dmax)}")
    if ss["washout"]:
        prod = None
        words = (f"No steady culture at D = {_g(D)} h⁻¹: μ(S, P) − kd stays under D at every sugar from 0 to Sf, so "
                 f"the cells wash out ({rates}). "
                 + ("This run's path washed out by its end." if reached == "washout"
                    else "This run's path had not washed out by its end."))
    else:
        prod = D * ss["P"]
        words = (f"Steady state at D = {_g(D)} h⁻¹: X {_g(ss['X'])}, S {_g(ss['S'])} and P {_g(ss['P'])} {G_L}; its "
                 f"productivity, D·P, is {_g(prod)} {G_L} h⁻¹. ")
        if ss["bistable"]:
            words += (f"Washout is a second stable state: μ(Sf) − kd is at or under D while μ − kd rises above it at "
                      f"low sugar ({rates}), so a run reaches one or the other by where it starts. ")
        else:
            words += f"D is under the washout rate ({rates}). "
        words += {"culture": "This run's path reached it by its end.",
                  "washout": "This run's path washed out instead.",
                  None: "This run's path had not reached it by its end."}[reached]
    return SteadyState(washout=ss["washout"], dilutionRate=D, dWashout=ss["dWashout"], dWashoutD5=d5, X=ss["X"],
                       S=ss["S"], P=ss["P"], productivity=prod, words=words, dWashoutMax=dmax,
                       bistable=ss["bistable"], reached=reached)


def _harvest_hour(fam: kinetics.Family, traj: kinetics.Trajectory) -> float:
    """A batch is harvested the hour its sugar runs out; a fed culture, and
    a batch whose sugar does not run out in its run, at the run's end."""
    return traj.runout_h if fam.feed == "none" and traj.runout_h is not None else traj.t_final


def _run_simulation(inputs, seed):
    fam, specs, values, p, traj = _trajectory(inputs)
    group = {s.key: s.group for s in specs}
    harvest_h = _harvest_hour(fam, traj)
    # OF-BLD-020 §6.R (seam-0): the harvest hour is a kept point. A batch run
    # past the hour its sugar runs out (a run length a person or a fit set)
    # does not end there, and the display grid and the segment ends need not
    # hold it, so it joins them: every reader of the broth at harvest (pureOS's
    # inlet, the vessel, GET /api/fermos/harvest) then reads the state the
    # titre and the residual sugar below describe, never a grid neighbour.
    times = np.array(sorted(set(traj.times().tolist()) | {float(harvest_h)}))
    Y = traj.sample(times)
    series = {"t": [float(t) for t in times], **{s: [float(x) for x in Y[kinetics.IX[s]]] for s in fam.states}}
    our = kinetics.oxygen(p, traj, times)
    peak, peak_h = kinetics.oxygen_peak(p, traj)
    aerobic = p.get("yxo") is not None
    at_harvest = kinetics.harvest(traj, harvest_h)
    product = fam.product_state()
    final_titre = at_harvest["state"][product] if product else None
    made, used = kinetics.made_and_used(traj, harvest_h)
    achieved = made / used if used > 0 else None
    productivity = final_titre / harvest_h if final_titre is not None and harvest_h > 0 else None
    mb = traj.balance
    ok = mb["closure"] <= kinetics.BALANCE_TOL
    balance = MassBalance(
        closure=mb["closure"], ok=ok,
        note=(f"Sugar consumed, {mb['consumed']:.6g} g, against the consumption states and against what the cells, "
              f"product and store say through the yields: within {mb['closure']:.2g} of it"
              + ("" if ok else f", outside the {kinetics.BALANCE_TOL:.0%} closure, so the rate laws or their "
                               "parameters do not hold together")
              + ". The check catches a wrong rate law, not the integrator's error, which the tests hold."))
    flags = [v.outOfBounds for v in values if v.outOfBounds]
    flags += [f"{v.key} is bound to fit {v.source.id if v.source else ''}, whose run did not identify it: "
              f"{_why_unidentified(v)}" for v in values if v.origin == "fit" and v.identified is False]
    if not ok:
        flags.append(f"The mass balance does not close: {mb['closure']:.2g} against {kinetics.BALANCE_TOL:.0%}.")
    if traj.runout_h is None and fam.id == "batch_v1":
        flags.append("The sugar did not run out within the run length; the harvest is at the run's end.")
    yps = p.get("yps")
    ceiling = _ceiling_block(inputs, yps, achieved)
    if ceiling and ceiling.flagged:
        flags.append("Yp/s is above a geneOS ceiling for this strain on this sugar: flagged, not clamped.")
    steady = None
    notes = list(traj.notes)
    if isinstance(fam, kinetics.ChemostatV1):
        steady = _steady_state(fam, p, traj)
        if steady.washout:
            flags.append("No steady culture holds at this dilution rate: the cells wash out.")
        elif steady.bistable and steady.reached == "washout":
            flags.append("This run's cells washed out, though a steady culture holds at this dilution rate from "
                         "another start: washout is a second stable state.")
        notes.append("A chemostat's productivity is D·P at its steady state, given with the steady state; the end "
                     "state's productivity is the final titre over the run's hours, a batch's measure, not a "
                     "chemostat's.")
    for v in values:
        if v.origin == "convention" and isinstance(v.value, str) and v.detail:
            notes.append(f"{v.key}: {v.detail}")
    out = {
        "family": fam.id, "title": fam.title,
        "strain": (_named(inputs, "strain").value if _named(inputs, "strain") else None),
        "product": (_named(inputs, "product").value if _named(inputs, "product") else None),
        "sugar": (_named(inputs, "sugar").value if _named(inputs, "sugar") else None),
        "parameters": [v.model_dump(mode="json") for v in values if group[v.key] != START_GROUP],
        "start": [v.model_dump(mode="json") for v in values if group[v.key] == START_GROUP],
        "series": series, "units": {"t": "h", **fam.state_units},
        "our": OxygenUptake(t=series["t"], value=our, unit=OUR_UNIT, peak=peak, peakH=peak_h,
                            note=None if aerobic else ANAEROBIC_NOTE).model_dump(mode="json"),
        "end": {**{s: float(traj.y_final[kinetics.IX[s]]) for s in fam.states}, "t": float(traj.t_final)},
        "sugarRunsOutH": traj.runout_h, "harvestH": float(harvest_h), "finalTitre": final_titre,
        "yieldAchieved": achieved, "productivity": productivity, "massBalance": balance.model_dump(mode="json"),
        "ceiling": ceiling.model_dump(mode="json") if ceiling else None, "flags": flags, "aerobic": aerobic,
        "steadyState": steady.model_dump(mode="json") if steady else None, "notes": notes,
    }
    return out


artifacts.register(SIMULATION, SIMULATION_STEM, _run_simulation, version_of=_simulation_version)


# A kept vessel design replays on a service just started (OF-BLD-020 §8.R,
# finding 1): `vessel` registers its tool when it is imported, and nothing
# the service imports at start imports it, so this module, which the service
# always imports, names the hook; the worker starts only when a replay runs.
VESSEL_TOOL = "fermos.vessel"


def _register_vessel() -> None:
    from . import vessel

    vessel._register()


artifacts.register_lazy(VESSEL_TOOL, _register_vessel)


def kept_simulation(key: Any) -> Any:
    """A kept simulation, by id or as given; refused in words otherwise."""
    if isinstance(key, str):
        try:
            art = artifacts.get(key)
        except artifacts.ArtifactNotFound:
            raise SimulationRefused(f"there is no kept simulation {key}") from None
        except artifacts.ArtifactDamaged as e:
            # OF-BLD-020 §3.R (finding 9): in words, as a damaged fit is
            # (_fit_art), never a bare 500 on bind or simulate.
            raise SimulationRefused(f"kept simulation {key} cannot be read: {e}") from None
    else:
        art = key
    if art.tool != SIMULATION:
        raise SimulationRefused(f"{art.id} is a {art.tool}, not a simulation fermOS keeps")
    return art


# ── the harvest stream (OF-BLD-020 §6.2, D10) ──────────────────────────
#
# The broth that leaves fermOS is the stream that enters pureOS. A kept
# simulation's broth at an hour is READ from the series its artifact keeps,
# never integrated again (OF-BLD-019 D1: every reader reads the one
# artifact). The artifact keeps its series on the display grid and every
# segment's end (kinetics.Trajectory.times), not the solver's dense output,
# so an hour that is not a kept point is read at the nearest kept point and
# the read says so; nothing is interpolated between kept points, since only
# the solver's own dense output could do that honestly. A batch run until
# its sugar runs out ends at that hour, so its harvest is a kept point and
# reads as its end state; since OF-BLD-020 §6.R (seam-0) every simulation
# keeps its harvest hour among its hours (`_run_simulation`, version 2), so a
# run that goes on past it reads its broth there too. A simulation kept
# before, whose harvest hour is no kept point, is refused at its own harvest
# hour in words (a grid neighbour is never handed back as the broth at its
# harvest); a person's hour still reads the nearest kept point, said so.
HARVEST_HOUR = "the simulation's harvest hour"
PERSONS_HOUR = "a person's hour"
# The state a train's inlet carries as its product: the product in the broth.
BROTH_PRODUCT = "P"


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _no_broth_product(art: Any, family: str, fam: Any, kept: list[str]) -> str:
    """Why a simulation keeps no product in the broth, in words naming what
    it lacks and what it keeps."""
    if fam is None:
        what = f"its family {family or 'unnamed'} is none fermOS has"
    elif fam.product_state() not in (None, BROTH_PRODUCT):
        what = (f"its family {fam.id} keeps its product as a store inside the cells ({fam.product_state()}), not in "
                "the broth")
    elif fam.product_state() is None:
        what = f"its family {fam.id} has no product state"
    else:
        what = f"its family {fam.id} has one, and the artifact keeps no series of it"
    return (f"simulation {art.id} keeps no product series ({BROTH_PRODUCT}, the product in the broth): {what}; it "
            f"keeps {', '.join(kept) or 'no state'}, so its broth is no train's inlet")


def harvest(simulation_artifact: Any, hour: float | None = None) -> FermosHarvest:
    """A kept simulation's broth at an hour (its id, or the artifact): its
    own harvest hour when none is named (the hour its sugar runs out, else
    its run's end), else the hour a person named, read from the series the
    artifact keeps, each state in its unit. An artifact-free read: nothing
    is integrated again and nothing is kept. Refused in words: an hour
    outside the simulated span, a simulation that keeps no product series
    in the broth (P), a file whose series cannot be read, and, at its own harvest hour, one kept
    before that hour was a kept point (OF-BLD-020 §6.R)."""
    art = kept_simulation(simulation_artifact)
    o = art.output if isinstance(art.output, dict) else {}
    family = str(o.get("family") or "")
    fam = kinetics.FAMILIES.get(family)
    series = o.get("series") if isinstance(o.get("series"), dict) else {}
    units_of = o.get("units") if isinstance(o.get("units"), dict) else {}
    t = series.get("t")
    if not (isinstance(t, list) and t and all(_finite(x) for x in t) and all(a <= b for a, b in zip(t, t[1:]))):
        raise SimulationRefused(f"simulation {art.id} keeps no series of hours its broth can be read on")
    own = [s for s in (fam.states if fam is not None else ()) if s in series]
    kept = own + sorted(k for k in series if k != "t" and k not in own)
    for k in kept:
        col = series[k]
        if not (isinstance(col, list) and len(col) == len(t) and all(_finite(x) for x in col)):
            raise SimulationRefused(f"simulation {art.id}'s series of {k} cannot be read on its {len(t)} hours")
    if BROTH_PRODUCT not in series:
        raise SimulationRefused(_no_broth_product(art, family, fam, kept))
    harvest_h = o.get("harvestH")
    if not _finite(harvest_h):
        raise SimulationRefused(f"simulation {art.id} keeps no harvest hour (harvestH)")
    start, end = float(t[0]), float(t[-1])
    if hour is None:
        asked, source = float(harvest_h), HARVEST_HOUR
        runs_out = o.get("sugarRunsOutH")
        how = ("the hour its sugar runs out" if _finite(runs_out) and float(runs_out) == asked else
               "its run's end: a fed culture's sugar is fed again" if fam is not None and fam.feed != "none" else
               "its run's end: its sugar does not run out in this simulation")
    else:
        if not _finite(hour):
            raise SimulationRefused("the hour asked is not a number of hours")
        asked, source, how = float(hour), PERSONS_HOUR, "an hour a person named"
        tol = kinetics.TIME_EPS * max(1.0, abs(asked))
        if not start - tol <= asked <= end + tol:
            raise SimulationRefused(f"the hour {asked:.6g} h lies outside simulation {art.id}, which keeps its broth "
                                    f"from {start:.6g} to {end:.6g} h")
    k = min(range(len(t)), key=lambda i: (abs(float(t[i]) - asked), i))
    at = float(t[k])
    exact = abs(at - asked) <= kinetics.TIME_EPS * max(1.0, abs(asked))
    if source == HARVEST_HOUR and not exact:
        raise SimulationRefused(
            f"simulation {art.id} keeps no point at its own harvest hour, {asked:.6g} h ({how}): it was kept by an "
            f"earlier fermOS, before a simulation kept its harvest hour among its hours ({art.toolVersion}), so its broth "
            f"at harvest is not on file and is not read from a neighbouring hour ({at:.6g} h); simulate it again in "
            "fermOS → Simulate, and the run kept then holds its broth at harvest")
    read = (f"the kept point at {at:.6g} h, as the simulation keeps it" if exact else
            f"the nearest kept point, {at:.6g} h, to the hour asked, {asked:.6g} h: the simulation keeps its series on "
            f"{len(t)} hours, not the solver's own steps, so a broth between two of them is read at the nearer one, and "
            "nothing is integrated again")
    return FermosHarvest(
        artifactId=art.id, family=family, strain=o.get("strain"), product=o.get("product"), sugar=o.get("sugar"),
        provenance=art.provenance, asked=asked, hourSource=source, how=how, hour=at, exact=exact, read=read,  # type: ignore[arg-type]
        harvestH=float(harvest_h), runEndH=end,
        states=[HarvestState(state=s, value=float(series[s][k]), unit=str(units_of.get(s) or "")) for s in kept],
        absent=kinetics.ABSENT)


def simulations() -> list[SimulationSummary]:
    """The kept simulations, newest first. A file that does not read as a
    simulation is skipped."""
    out = []
    for a in artifacts.all_artifacts():
        if a.tool != SIMULATION:
            continue
        o = a.output
        try:
            out.append(SimulationSummary(artifactId=a.id, family=o["family"], title=o.get("title") or o["family"],
                                         strain=o.get("strain"), product=o.get("product"), sugar=o.get("sugar"),
                                         finalTitre=o.get("finalTitre"), harvestH=o.get("harvestH"),
                                         createdAt=a.createdAt, provenance=a.provenance))
        except (KeyError, TypeError, ValueError):
            continue
    return out
