"""fermOS's model families (OF-BLD-020 §3.1, D5): code written once, each
integrated on scipy's `solve_ivp` and fitted on `least_squares`.

A family declares its states, its parameters (`ParameterSpec`s, Appendix 2
§A: what each symbol means, its unit, its bounds with their reason, and the
ordered rule for where its value comes from), its rate laws, and nothing
else. No process number lives in this file: every parameter value arrives in
`p` and every start value in `y0` (`fermos.simulate` resolves them through
`params.resolve`, each with its source). The numbers here are the solver's
own settings, each a named constant in SETTINGS with its reason, which every
simulation's basis states as a convention.

THE FAMILIES, AS D5 WRITES THEM

batch_v1
    dX/dt = μ·X − kd·X
    μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ
    dP/dt = (α·μ + β)·X
    dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dP/dt − m·X
    states X, S, P; optional kd, Ki, m (zero when absent, said so)

fedbatch_v1
    adds V with dV/dt = F(t), feed concentration Sf, profile `constant` |
    `exponential` (set μ_set, F = μ_set·X·V/(Yxs·(Sf − S))) | `steps` (a
    table), dilution terms on every state

chemostat_v1
    dilution D on every state, feed Sf, steady state solved and the dynamic
    path integrated; washout reported when D ≥ μmax·Sf/(Ks + Sf)

storage_v1
    a second substrate N with its own Monod term limiting growth, a storage
    product Q accumulating when N is exhausted at rate
    qQ,max·S/(Ks+S)·(1 − Q/Qmax)

light_v1
    declared with its parameters (incident irradiance, path length,
    attenuation coefficient, photoinhibition constant) and no `rhs`: a socket
    that refuses to run in words

Oxygen, every family
    qO2 = μ/Yxo + mo
    OUR(t) = qO2·X
    (parameters Yxo, mo; zero and said so for anaerobic families)

AS BUILT: where the measurement departs from D5's text (the spike of
2026-10-21, scratchpad spike020-kinetics/REPORT.md; STATE.md §3.1 records
each as this step's choice)

1. The sugar never goes negative. D5's equations as written take S below
   zero (to −0.006 g L⁻¹ on the spike's stand-in, −13 with Monod alone
   clipped, because β·X and m·X keep eating). A terminal event at S = 0 ends
   the segment; after it the culture is starved: S is held at zero, μ is
   zero, and β·X and m·X are cut by φ = min(1, supply/demand) to what a feed
   brings (nothing in a batch). A second event, the supply overtaking the
   demand, returns a fed culture to growth.
2. "The hour the sugar runs out" is the first hour S falls to RUN_OUT_SHARE
   of its start. Under Monod with no maintenance and no β the sugar decays
   toward zero and never reaches it, and the hour S crosses zero wanders
   with the solver's tolerance; the share's hour does not. N in storage_v1
   is exhausted at RUN_OUT_SHARE of KN, where N/(KN + N) has stopped growth.
   "Until the sugar runs out" integrates over horizons doubling from 1/μmax,
   at most HORIZON_DOUBLINGS times, and a run whose sugar stops falling
   (growth stopped at Pmax, or by the second nutrient) is refused in words.
3. Pmax stops the product as well as growth: dP/dt = (α·μ + β·fP)·X with
   fP = (1 − P/Pmax)ⁿ on a base clipped at zero (a negative base to a
   fractional power is a complex number in Python, nan in numpy). As
   written, β·X carried the product to 52–59 g L⁻¹ past a Pmax of 20.
4. Ki absent means the Haldane term is off (Ki → ∞), never Ki = 0.
5. The exponential feed pays for the whole demand at μset:
   F = (μset/Yxs + (α·μset + β)/Yps + m)·X·V/(Sf − S). D5's
   F = μset·X·V/(Yxs·(Sf − S)) pays for growth alone, and the culture grew
   at 0.079 h⁻¹ against a μset of 0.15 (0.151 with the whole demand).
   The `steps` profile waits: a ParameterSpec holds one number or one word,
   not a table. The feed carries sugar alone.
6. Washout is D ≥ μ(Sf, P = 0) − kd, which is D5's μmax·Sf/(Ks + Sf) when
   kd and Ki are off; both are reported. With kd or Ki set D5's expression
   is optimistic (0.396 against 0.339 h⁻¹ on the spike's stand-in). The
   steady state is solved by root-finding on S, the low-S root taken when a
   Haldane μ crosses twice.
7. A feed's start and end split the integration, so LSODA never steps over
   a change of feed.
8. storage_v1, where Appendix 2 §A is silent: Yps is the store's yield on S
   (the store is the product here), so α, β, Pmax and n are not this
   family's; Q starts at zero, said so; Q/Qmax reads Q as a share of the
   cell dry weight, Q/(X + Q), X the residual biomass, because Qmax's source
   is pha_content_cdw. With kd set, decay of X alone lifts that share past
   Qmax (measured): the flag says so.
       μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · N/(KN + N)
       dN/dt = −(1/Yx/N)·μ·X
       dQ/dt = qQ,max·S/(Ks+S)·(1 − (Q/(X + Q))/Qmax)·X   once N is exhausted
       dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dQ/dt − m·X
9. The mass balance is checked after every integration on cumulative
   consumption states (grams of sugar to growth, to product, to the store,
   to maintenance; grams fed and drawn off), and again through X, P and Q
   and the yields. Both are invariants of the equations, which LSODA keeps
   to rounding: the check catches a wrong right-hand side (a dropped 1/Yps
   reads 30 % off), never integrator error, which the tests hold against a
   run at rtol 1e-12. Within BALANCE_TOL, or the result carries a flag.
10. OUR's peak is read on the solver's own steps: a display grid misses it
   (1.170 against 1.192 on the spike's stand-in).
"""
from __future__ import annotations

import inspect
import math
import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, least_squares
from scipy.stats import t as student_t

from .models import ParameterSpec

# ── the solver's settings (each named, each stated in a simulation's basis) ─

RTOL = 1e-6
ATOL = 1e-9
RUN_OUT_SHARE = 1e-3
BALANCE_TOL = 1e-2
POINTS = 201
HORIZON_DOUBLINGS = 40
MAX_RHS_EVALS = 50000
MAX_SEGMENTS = 500
STALL_STEPS = 3
TIME_EPS = 1e-12
ROOT_TOL = 1e-14
SCAN_POINTS = 401
CONFIDENCE = 0.95
DIFF_STEP = 1e-4
FIT_BOX = 1e3
FIT_MAX_NFEV = 200
RANK_TOL = 1e-8
NULL_WEIGHT = 1e-3
FAILED_RESIDUAL = 1e6

SETTINGS: dict[str, str] = {
    "RTOL": "the integrator's relative tolerance, as OF-BLD-020 D5 and §3.1 set it",
    "ATOL": "the integrator's absolute tolerance in g L⁻¹: tight enough near S = 0 that the run-out hour does not "
            "move with it (a looser one, 1e-6, moved it; spike020-kinetics)",
    "RUN_OUT_SHARE": "the share of its start below which a substrate counts as run out (S of S0, N of KN): under Monod "
                     "a substrate decays toward zero and never reaches it, so 'runs out' needs a tolerance, and a "
                     "thousandth of the start is below any assay of the broth's sugar",
    "BALANCE_TOL": "the mass balance's closure, 1 %, as OF-BLD-020 §3.1 sets it: past it the result carries a flag",
    "POINTS": "evenly spaced hours a time course is reported on, plus every segment's end: enough for a figure, "
              "small enough for an artifact",
    "HORIZON_DOUBLINGS": "how many times 'until the sugar runs out' doubles its horizon from 1/μmax before it refuses",
    "MAX_RHS_EVALS": "rate evaluations one simulation may take: a fit that wanders to an extreme parameter set makes "
                     "the system so stiff that one integration ran for minutes (spike020-kinetics)",
    "MAX_SEGMENTS": "pieces one integration may split into at its mode switches before it refuses as chattering",
    "STALL_STEPS": "segments in a row that may end where they began before the integration refuses as stuck",
    "TIME_EPS": "the relative gap under which two hours are one, so a segment never restarts at its own end",
    "ROOT_TOL": "the steady state's root-finding tolerance, absolute and relative",
    "SCAN_POINTS": "points the steady state scans S on to find the low root first (a Haldane μ can cross twice)",
    "CONFIDENCE": "the coverage of a fit's interval, as fermos.CONFIDENCE",
    "DIFF_STEP": "least_squares' relative finite-difference step: the default step on simulations at RTOL gave a noisy "
                 "Jacobian and a 260 % error; this one 0.05 % (spike020-kinetics)",
    "FIT_BOX": "how far, as a factor either way, a fitted parameter with no bound of its own may move from its start: "
               "an unbounded fit wandered to values whose integration hung",
    "FIT_MAX_NFEV": "least_squares' evaluations per pass (the Jacobian's not counted)",
    "RANK_TOL": "the share of the largest singular value under which the Jacobian's direction is null",
    "NULL_WEIGHT": "the weight in a null direction past which a parameter is unidentified",
    "FAILED_RESIDUAL": "the residual a simulation that cannot run returns inside a fit: residuals are scaled by each "
                       "series' range, so a fit's own are of order one",
}


class FamilyRefused(ValueError):
    """A family cannot run this request, in words: the light socket, a
    missing parameter, an impossible start, a run that never ends."""


class BudgetExceeded(FamilyRefused):
    pass


def versions() -> dict[str, str]:
    return {"scipy": scipy.__version__, "numpy": np.__version__}


# ── the state vector ───────────────────────────────────────────────────
# One layout for every family; a family uses the slots its states name.
# After the six states come cumulative amounts in grams: sugar to growth,
# to product, to the store, to maintenance; ∫X·V and ∫φ·X·V; sugar fed; and
# sugar, cells, product and store drawn off.
NAMES = ("X", "S", "P", "V", "N", "Q",
         "Cg", "Cp", "Cq", "Cm", "IXV", "IXVphi", "Min", "MoutS", "MoutX", "MoutP", "MoutQ")
IX = {n: k for k, n in enumerate(NAMES)}
NY = len(NAMES)
_X, _S, _P, _V, _N, _Q = (IX[n] for n in ("X", "S", "P", "V", "N", "Q"))
(_CG, _CP, _CQ, _CM, _IXV, _IXVPHI, _MIN, _MOUT_S, _MOUT_X, _MOUT_P, _MOUT_Q) = (
    IX[n] for n in NAMES[NAMES.index("Cg"):])
G_L = "g L⁻¹"


@dataclass(frozen=True)
class Mode:
    # S held at zero; the non-growth terms cut to what the feed brings.
    starved: bool = False
    # storage_v1: N exhausted, the store forms.
    storing: bool = False


@dataclass
class Segment:
    t0: float
    t1: float
    sol: Any
    mode: Mode
    t_regime: float
    y_start: np.ndarray


@dataclass
class Trajectory:
    family: str
    p: dict[str, Any]
    y0: np.ndarray
    segments: list[Segment]
    t_final: float
    y_final: np.ndarray
    runout_h: float | None
    n_exhausted_h: float | None
    events: list[dict[str, Any]]
    notes: list[str]
    nfev: int
    seconds: float
    points: int = POINTS
    balance: dict[str, float] = field(default_factory=dict)

    def segment_at(self, t: float) -> Segment:
        for s in self.segments:
            if s.t0 <= t <= s.t1 and s.t1 > s.t0:
                return s
        return self.segments[0] if t <= self.segments[0].t0 else self.segments[-1]

    def at(self, t: float) -> np.ndarray:
        s = self.segment_at(t)
        if s.sol is None:
            return s.y_start.copy()
        return np.asarray(s.sol(min(max(t, s.t0), s.t1)), float)

    def sample(self, times: Any) -> np.ndarray:
        """The state vector at each hour, (NY, len(times)), each segment's
        hours read in one call of its dense output."""
        times = np.asarray(times, float)
        out = np.empty((NY, len(times)))
        filled = np.zeros(len(times), bool)
        for s in self.segments:
            if s.sol is None or s.t1 <= s.t0:
                continue
            m = ~filled & (times >= s.t0) & (times <= s.t1)
            if m.any():
                out[:, m] = np.asarray(s.sol(times[m]), float).reshape(NY, -1)
                filled |= m
        for k in np.nonzero(~filled)[0]:
            out[:, k] = self.at(float(times[k]))
        return out

    def times(self, steps: bool = False) -> np.ndarray:
        """The display grid (POINTS hours) and every segment's ends; with
        `steps`, every step the solver took too (a peak is read there)."""
        ts = set(np.linspace(0.0, self.t_final, self.points).tolist())
        for s in self.segments:
            ts.update((s.t0, s.t1))
            if steps and s.sol is not None:
                ts.update(np.asarray(s.sol.ts, float).tolist())
        return np.array(sorted(ts))


# ── the rate laws: one place, every family and every reader ────────────


def _f_product(v: dict[str, Any], P: float) -> float:
    """(1 − P/Pmax)ⁿ on a base clipped at zero; 1 with no Pmax."""
    pmax = v.get("p_max")
    if pmax is None:
        return 1.0
    base = 1.0 - P / pmax
    return 0.0 if base <= 0.0 else base ** v["n_inhibition"]


def _mu_of(fam: "Family", v: dict[str, Any], S: float, P: float, N: float) -> float:
    ks, ki = v["ks"], v.get("ki_substrate")
    monod = S / (ks + S) if ks + S > 0.0 else 0.0
    haldane = 1.0 if ki is None else 1.0 / (1.0 + S / ki)
    f_n = N / (v["k_n"] + N) if fam.has_N else 1.0
    return v["mu_max"] * monod * haldane * (_f_product(v, P) if fam.has_P else 1.0) * f_n


def _feed(fam: "Family", v: dict[str, Any], t_regime: float, y: Any) -> tuple[float, float]:
    """(F in, F out) in L h⁻¹. Which feed is on is fixed per segment from
    `t_regime`, so a rate never switches inside one LSODA call."""
    if fam.feed == "none":
        return 0.0, 0.0
    V = y[_V]
    if fam.feed == "chemostat":
        f = v["dilution_rate"] * V
        return f, f
    end = v.get("feed_end_h")
    if t_regime < v["feed_start_h"] or (end is not None and t_regime >= end):
        return 0.0, 0.0
    if v["feed_profile"] == "constant":
        return v["feed_rate"], 0.0
    gap = v["feed_conc"] - max(y[1], 0.0)
    if gap <= 0.0:
        return 0.0, 0.0
    ms = v["mu_set"]
    per_x = ms / v["yxs"] + (v["alpha"] * ms + v["beta"]) / v["yps"] + v["maintenance"]
    return per_x * max(y[0], 0.0) * V / gap, 0.0


def _rates(fam: "Family", v: dict[str, Any], y: Any, mode: Mode, t_regime: float) -> tuple[float, ...]:
    """Every rate at state y, in g L⁻¹ h⁻¹ (flows in L h⁻¹): μ, growth,
    growth-associated and non-growth-associated product, store, maintenance,
    the starved share φ, flow in, flow out, the feed's sugar."""
    X = y[0] if y[0] > 0.0 else 0.0
    S = y[1] if y[1] > 0.0 else 0.0
    P = y[2] if y[2] > 0.0 else 0.0
    N = y[_N] if y[_N] > 0.0 else 0.0
    Q = y[_Q] if y[_Q] > 0.0 else 0.0
    mu = 0.0 if mode.starved else _mu_of(fam, v, S, P, N)
    r_x = mu * X
    if fam.has_P:
        r_pg = v["alpha"] * mu * X
        r_png = v["beta"] * _f_product(v, P) * X
    else:
        r_pg = r_png = 0.0
    r_q = 0.0
    if fam.has_Q and mode.storing:
        cdw = X + Q
        share = Q / cdw if cdw > 0.0 else 0.0
        monod = S / (v["ks"] + S) if v["ks"] + S > 0.0 else 0.0
        r_q = v["q_storage_max"] * monod * max(0.0, 1.0 - share / v["q_max"]) * X
    d_m = v["maintenance"] * X
    f_in, f_out = _feed(fam, v, t_regime, y)
    sf = v.get("feed_conc") or 0.0
    phi = 1.0
    if mode.starved:
        supply = f_in * sf / y[_V]
        demand = r_png / v["yps"] + d_m + r_q / v["yps"]
        phi = min(1.0, supply / demand) if demand > 0.0 else 1.0
        r_png, d_m, r_q = r_png * phi, d_m * phi, r_q * phi
    return mu, r_x, r_pg, r_png, r_q, d_m, phi, f_in, f_out, sf


def _terms(fam: "Family", v: dict[str, Any], y: Any, mode: Mode, t_regime: float) -> dict[str, float]:
    """`_rates` by name, with what each costs in sugar, for the readers."""
    mu, r_x, r_pg, r_png, r_q, d_m, phi, f_in, f_out, sf = _rates(fam, v, y, mode, t_regime)
    return {"mu": mu, "r_x": r_x, "r_pg": r_pg, "r_png": r_png, "r_q": r_q, "d_g": r_x / v["yxs"],
            "d_p": (r_pg + r_png) / v["yps"], "d_q": r_q / v["yps"], "d_m": d_m, "phi": phi,
            "f_in": f_in, "f_out": f_out, "sf": sf}


def _supply_demand(fam: "Family", v: dict[str, Any], y: Any, t_regime: float) -> tuple[float, float]:
    """At S = 0: what the feed brings and what the non-growth terms want."""
    X = max(y[0], 0.0)
    f_in, _ = _feed(fam, v, t_regime, y)
    sf = v.get("feed_conc") or 0.0
    fP = _f_product(v, max(y[2], 0.0)) if fam.has_P else 1.0
    demand = (v["beta"] * fP * X / v["yps"] if fam.has_P else 0.0) + v["maintenance"] * X
    return f_in * sf / y[_V], demand


def _rhs(fam: "Family", v: dict[str, Any], mode: Mode, t_regime: float, counter: list[int]) -> Callable:
    kd, yxs, yps = v["kd"], v["yxs"], v["yps"]

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        counter[0] += 1
        if counter[0] > MAX_RHS_EVALS:
            raise BudgetExceeded(f"the integration took more than {MAX_RHS_EVALS} rate evaluations (at {t:.6g} h): "
                                 "the parameter set makes the system too stiff to integrate here")
        mu, r_x, r_pg, r_png, r_q, d_m, phi, f_in, f_out, sf = _rates(fam, v, y, mode, t_regime)
        X, S, P, V, Q = y[_X], y[_S], y[_P], y[_V], y[_Q]
        Xe = X if X > 0.0 else 0.0
        D = f_in / V
        d_g, d_p, d_q = r_x / yxs, (r_pg + r_png) / yps, r_q / yps
        d = np.zeros(NY)
        d[_X] = r_x - kd * Xe - D * X
        d[_S] = D * (sf - S) - (d_g + d_p + d_q + d_m)
        if mode.starved and S <= 0.0:
            d[_S] = max(d[_S], 0.0)
        d[_P] = r_pg + r_png - D * P
        d[_V] = f_in - f_out
        d[_N] = -r_x / v["yxn"] - D * y[_N] if fam.has_N else 0.0
        d[_Q] = r_q - D * Q
        d[_CG], d[_CP], d[_CQ], d[_CM] = V * d_g, V * d_p, V * d_q, V * d_m
        d[_IXV], d[_IXVPHI] = V * Xe, V * Xe * phi
        d[_MIN] = f_in * sf
        d[_MOUT_S], d[_MOUT_X], d[_MOUT_P], d[_MOUT_Q] = f_out * S, f_out * X, f_out * P, f_out * Q
        return d

    return rhs


# ── the parameters (Appendix 2 §A) ─────────────────────────────────────


def _ontology_bounds(field_id: str, unit: str) -> tuple[float | None, float | None, str] | None:
    """The ontology's plausibility range of a field, in `unit`, with its
    reason; None when it is not exported here or does not convert."""
    from . import params, units

    f = params._ontology(field_id)
    if f is None:
        return None
    lo, hi = f["range"]
    try:
        low, high = units.convert(float(lo), f["canonicalUnit"], unit), units.convert(float(hi), f["canonicalUnit"], unit)
    except (TypeError, ValueError):
        return None
    return low, high, (f"the ontology's plausibility range for {field_id} ({f['name']}), {lo:g} to {hi:g} "
                       f"{f['canonicalUnit']}: the range that refuses an implausible extraction, not a result")


def _spec(key: str, label: str, symbol: str, gloss: str, dimension: str, unit: str, group: str, rule: list[str], *,
          bounds: str = "nonnegative", reason: str = "", scale: str = "linear", choices: list[str] | None = None,
          convention: float | str | None = None, note: str | None = None) -> ParameterSpec:
    """One ParameterSpec. `bounds`: 'ontology' (the first record field's
    plausibility range, else the physical limit), 'share' (0 to 1),
    'nonnegative' (at least 0) or 'none' (a word)."""
    low: float | None = None
    high: float | None = None
    why = reason
    if bounds == "ontology":
        fields = [e.split(":", 1)[1] for e in rule if e.startswith("record:")]
        found = _ontology_bounds(fields[0], unit) if fields else None
        if found is not None:
            low, high, why = found
        else:
            bounds = "nonnegative"
            reason = reason or (f"a physical limit: no negative {label}"
                                + (f" (the ontology's range for {fields[0]} is not exported here)" if fields else ""))
    if bounds == "share":
        low, high = 0.0, 1.0
        why = reason or "a physical limit: a share lies between none and the whole"
    elif bounds == "nonnegative":
        low = 0.0
        why = reason or f"a physical limit: no negative {label}"
    elif bounds == "none":
        why = reason or "a choice of words, so it has no bounds"
    return ParameterSpec(key=key, label=label, symbol=symbol, gloss=gloss, dimension=dimension, unit=unit, min=low,
                         max=high, scale=scale if low is not None and low > 0 else "linear", group=group,
                         sourceRule=rule, note=note, boundsReason=why, choices=choices, convention=convention)


ZERO_SAID = "zero when absent, said so (D5)"
OFF = "off"
ANAEROBIC = "anaerobic"
PER_LITRE = "per litre"
UNTIL_RUN_OUT = "until the sugar runs out"
TO_THE_END = "to the end"
# A convention stated in words reads as no number: the term it names is off.
WORDS = (OFF, ANAEROBIC, PER_LITRE, UNTIL_RUN_OUT, TO_THE_END)
# The parameters whose absence (None) the rate laws read: no Pmax is no
# product inhibition, no Ki the Haldane term off, no Yx/o an anaerobic
# culture, no feed end a feed to the end of the run.
OPTIONAL = ("ki_substrate", "p_max", "yxo", "feed_end_h")


def _growth() -> list[ParameterSpec]:
    return [
        _spec("mu_max", "maximum specific growth rate", "μmax", "the fastest the cells can grow with nothing limiting",
              "rate", "h⁻¹", "Growth", ["fit", "record:growth_rate_mu", "assumption"], bounds="ontology", scale="log"),
        _spec("ks", "half-saturation constant", "Ks", "the substrate concentration at which growth runs at half speed",
              "massConc", G_L, "Growth", ["fit", "record:monod_ks", "assumption"], bounds="ontology", scale="log"),
        _spec("kd", "death rate", "kd", "the death or decay rate of cells", "rate", "h⁻¹", "Growth",
              ["fit", "assumption", "convention"], convention=0, note=f"No death or decay term: {ZERO_SAID}."),
        _spec("yxs", "biomass yield on substrate", "Yx/s", "grams of cells made per gram of substrate used", "yield",
              "g g⁻¹", "Growth", ["fit", "record:biomass_yield_substrate", "assumption"], bounds="share",
              reason="a physical limit: a gram of substrate makes at most a gram of cells"),
    ]


def _product() -> list[ParameterSpec]:
    return [
        _spec("alpha", "growth-associated product coefficient", "α",
              "product made per unit of growth (growth-associated)", "yield", "g g⁻¹", "Product",
              ["fit", "record:ethanol_lp_alpha", "assumption"]),
        _spec("beta", "non-growth-associated product rate", "β",
              "product made per gram of cells per hour whatever the growth (non-growth-associated)", "specProd",
              "g g⁻¹ h⁻¹", "Product", ["fit", "record:ethanol_lp_beta", "assumption", "convention"], convention=0,
              note=f"No non-growth-associated product: {ZERO_SAID}."),
        _spec("yps", "product yield on substrate", "Yp/s", "grams of product per gram of substrate", "yield", "g g⁻¹",
              "Product", ["fit", "record:ethanol_yield_substrate", "assumption"],
              reason=("a physical limit: no negative yield. Its ceiling is the geneOS ceiling for the strain on the "
                      "sugar, which a simulation sets beside its result (flagged, never clamped), else the "
                      "reaction's theoretical yield; neither is known to a family's declaration")),
        _spec("maintenance", "maintenance coefficient", "m",
              "substrate the cells burn just to stay alive per gram per hour", "specProd", "g g⁻¹ h⁻¹", "Product",
              ["fit", "assumption", "convention"], convention=0,
              note=(f"No maintenance: {ZERO_SAID}. Appendix 2 §A names maintenance_coefficient, a field the "
                    "ontology does not hold yet; until it does a record cannot bind this.")),
    ]


def _inhibition() -> list[ParameterSpec]:
    return [
        _spec("p_max", "maximum product concentration", "Pmax", "the product concentration at which growth stops",
              "massConc", G_L, "Inhibition", ["fit", "record:ethanol_max_conc", "assumption"], bounds="ontology"),
        _spec("n_inhibition", "product inhibition exponent", "n",
              "how sharply growth falls as product builds toward Pmax", "exponent", "", "Inhibition",
              ["fit", "assumption", "convention"], convention=1,
              note="1 by convention (Appendix 2 §A): growth falls in proportion to the room left below Pmax.",
              reason=("a physical limit: above zero, since at zero (1 − P/Pmax)⁰ = 1 and Pmax stops nothing. "
                      "Appendix 2 §A's convention range, 0.5 to 3, is not typed here: kinetics.py holds no number "
                      "but its solver's settings")),
        _spec("ki_substrate", "substrate inhibition constant", "Ki",
              "the substrate concentration above which it inhibits (Haldane)", "massConc", G_L, "Inhibition",
              ["fit", "record:substrate_inhibition_ki", "assumption", "convention"], bounds="ontology", scale="log",
              convention=OFF, note=("Off when absent, said so: Ki → ∞, the Haldane term 1, never Ki = 0, which "
                                    "would stop growth (D5 as built, 4).")),
    ]


def _oxygen() -> list[ParameterSpec]:
    return [
        _spec("yxo", "biomass yield on oxygen", "Yx/o", "grams of cells per gram of oxygen", "yield", "g g⁻¹",
              "Oxygen", ["fit", "assumption", "convention"], convention=ANAEROBIC,
              note=("Anaerobic when absent: the culture takes up no oxygen and its OUR is zero, said so (D5). "
                    "Appendix 2 §A names biomass_yield_oxygen, a field the ontology does not hold yet.")),
        _spec("mo", "oxygen maintenance coefficient", "mO", "oxygen for maintenance per gram of cells per hour",
              "specProd", "g g⁻¹ h⁻¹", "Oxygen", ["assumption", "convention"], convention=0,
              note=f"No oxygen for maintenance: {ZERO_SAID}."),
    ]


def _feed_conc(group: str) -> ParameterSpec:
    return _spec("feed_conc", "substrate in the feed", "Sf", "substrate concentration in the feed", "massConc", G_L,
                 group, ["record:medium_component_conc", "assumption"],
                 reason=("a physical limit: no negative concentration. The substrate's solubility bounds it above "
                         "(Appendix 2 §A), and no solubility is on file here"))


def _start(*, volume: bool, product: bool = True) -> list[ParameterSpec]:
    out = [
        _spec("x0", "cells at the start", "X0", "cells at time zero", "massConc", G_L, "Start values",
              ["fit", "assumption"]),
        _spec("s0", "substrate at the start", "S0", "substrate at time zero", "massConc", G_L, "Start values",
              ["fit", "record:medium_component_conc", "assumption"]),
    ]
    if product:
        out.append(_spec("p0", "product at the start", "P0", "product at time zero", "massConc", G_L, "Start values",
                         ["fit", "assumption"]))
    if volume:
        out.append(_spec("v0", "working volume at the start", "V0", "working volume at the start", "volume", "L",
                         "Start values", ["assumption"],
                         reason="a physical limit: above zero, since every concentration is per litre of it"))
    else:
        out.append(_spec("v0", "working volume at the start", "V0", "working volume at the start", "volume", "L",
                         "Start values", ["assumption", "convention"], convention=PER_LITRE,
                         note="Per litre of broth: the volume does not change, so no concentration depends on it.",
                         reason="a physical limit: above zero, since every concentration is per litre of it"))
    return out


def _run_length(*, until_run_out: bool) -> ParameterSpec:
    if until_run_out:
        return _spec("t_end", "run length", "", "how long to integrate", "time", "h", "Run length",
                     ["convention", "assumption"], convention=UNTIL_RUN_OUT,
                     note=("Until the sugar runs out (Appendix 2 §A): the first hour the sugar falls to a "
                           "thousandth of its start (kinetics.RUN_OUT_SHARE). A run whose sugar stops falling is "
                           "refused in words, and then a person names the length."))
    return _spec("t_end", "run length", "", "how long to integrate", "time", "h", "Run length", ["assumption"],
                 note="A feed keeps bringing sugar, so the sugar need not run out: a person names the length.")


def _feed_specs() -> list[ParameterSpec]:
    return [
        _spec("feed_profile", "feed profile", "F(t)", "constant, exponential or a step table", "profile", "", "Feed",
              ["assumption"], bounds="none", choices=["constant", "exponential"],
              note=("D5's third profile, a step table, waits: a parameter holds one number or one word, not a "
                    "table.")),
        _spec("feed_rate", "feed rate", "F", "litres fed per hour (constant)", "flow", "L h⁻¹", "Feed",
              ["assumption"], note="Read when the profile is constant."),
        _spec("mu_set", "set growth rate", "μset", "the growth rate an exponential feed holds", "rate", "h⁻¹", "Feed",
              ["assumption"], reason=("a physical limit: no negative rate; above μmax no feed can hold it, which the "
                                      "simulation refuses in words"),
              note="Read when the profile is exponential: the feed pays for growth, product and maintenance at μset."),
        _feed_conc("Feed"),
        _spec("feed_start_h", "feed start", "", "when the feed starts", "time", "h", "Feed",
              ["assumption", "convention"], convention=0, note="From the start when absent, said so.",
              reason="a physical limit: no negative hour; past the run length the feed never starts"),
        _spec("feed_end_h", "feed end", "", "when the feed stops", "time", "h", "Feed",
              ["assumption", "convention"], convention=TO_THE_END, note="To the end of the run when absent, said so.",
              reason="a physical limit: no negative hour; past the run length the feed never stops"),
    ]


def _storage_specs() -> list[ParameterSpec]:
    return [
        _spec("n_initial", "second nutrient at the start", "N0", "the second nutrient at the start", "massConc", G_L,
              "Storage", ["record:medium_component_conc", "assumption"]),
        _spec("k_n", "half-saturation constant of the second nutrient", "KN",
              "half-speed concentration of the second nutrient", "massConc", G_L, "Storage", ["fit", "assumption"]),
        _spec("yxn", "biomass yield on the second nutrient", "Yx/N", "cells per gram of the second nutrient",
              "yield", "g g⁻¹", "Storage", ["fit", "assumption"]),
        _spec("q_storage_max", "maximum storage rate", "qQ,max",
              "the fastest storage-product formation per gram of cells", "specProd", "g g⁻¹ h⁻¹", "Storage",
              ["fit", "assumption"],
              note=("Appendix 2 §A derives it from pha_productivity, which is per litre of broth: deriving it needs "
                    "the run's biomass, so no record binds it directly.")),
        _spec("q_max", "most storage product the cells hold", "Qmax", "the most storage product the cells can hold",
              "yield", "g g⁻¹", "Storage", ["fit", "record:pha_content_cdw", "assumption"], bounds="share",
              reason=("a physical limit: a share of the cell dry weight lies between none and the whole; the "
                      "ontology's range for pha_content_cdw is in % CDW, which units.py does not convert into a share")),
    ]


def _light_specs() -> list[ParameterSpec]:
    return [
        _spec("irradiance", "incident irradiance", "I0", "the light reaching the culture's surface", "light",
              "µmol m⁻² s⁻¹", "Growth", ["assumption"]),
        _spec("path_length", "light path length", "L", "the light's path through the culture", "length", "m", "Growth",
              ["assumption"]),
        _spec("attenuation", "attenuation coefficient", "Ka", "how strongly the culture absorbs light per gram of cells",
              "attenuation", "m² g⁻¹", "Growth", ["assumption"]),
        _spec("k_photoinhibition", "photoinhibition constant", "KI,light",
              "the irradiance above which light inhibits growth", "light", "µmol m⁻² s⁻¹", "Growth", ["assumption"]),
    ]


# ── the families ───────────────────────────────────────────────────────

GROUPS = ("Growth", "Product", "Substrate", "Inhibition", "Oxygen", "Feed", "Dilution", "Storage", "Start values",
          "Run length")
# Which start value fills which state.
START_STATE = {"x0": "X", "s0": "S", "p0": "P", "v0": "V", "n_initial": "N"}


@dataclass
class FitResult:
    keys: list[str]
    values: dict[str, float]
    low: dict[str, float]
    high: dict[str, float]
    identified: dict[str, bool]
    identified_by_numbers: dict[str, bool]
    covariance: list[list[float]]
    rank: int
    singular_values: list[float]
    quality: dict[str, dict[str, Any]]
    notes: list[str]
    start: dict[str, float]
    simulations: int
    nfev: int
    seconds: float


class Family:
    id = ""
    title = ""
    what = ""
    states: tuple[str, ...] = ()
    socket = False
    program: str | None = None
    feed = "none"
    has_P = True
    has_N = False
    has_Q = False

    @property
    def equations(self) -> str:
        return inspect.cleandoc(type(self).__doc__ or "")

    @property
    def state_units(self) -> dict[str, str]:
        return {s: ("L" if s == "V" else G_L) for s in self.states}

    def specs(self) -> list[ParameterSpec]:
        raise NotImplementedError

    def groups(self) -> list[str]:
        present = {s.group for s in self.specs()}
        return [g for g in GROUPS if g in present]

    def product_state(self) -> str | None:
        return "P" if self.has_P else "Q" if self.has_Q else None

    def irrelevant(self, p: dict[str, Any]) -> set[str]:
        """Keys this request does not read, so they need no value."""
        return set()

    # ── checks ──

    def _prepared(self, p: dict[str, Any]) -> dict[str, Any]:
        """The values the rate laws read, refused in words when one is
        missing or cannot stand. A key a family does not use reads as off."""
        if self.socket:
            raise FamilyRefused(self.refusal())
        v = dict(p)
        if not self.has_P:
            v.update(alpha=0.0, beta=0.0, p_max=None, n_inhibition=1)
        for k in OPTIONAL:
            v.setdefault(k, None)
        skip = self.irrelevant(v) | set(OPTIONAL) | set(START_STATE) | {"t_end"}
        missing = []
        for s in self.specs():
            if s.key in skip:
                continue
            x = v.get(s.key)
            if (x not in s.choices) if s.choices else not _number(x):
                missing.append(s.key)
        if missing:
            raise FamilyRefused(f"{self.id} cannot run: no value for {', '.join(missing)}")
        bad = [k for k, x in v.items() if x is not None and not isinstance(x, str) and not _finite(x)]
        if bad:
            raise FamilyRefused(f"{', '.join(sorted(bad))} must be finite numbers")
        for k in ("yxs", "yps", "n_inhibition", "yxn", "k_n", "q_max", "yxo", "p_max", "ki_substrate"):
            if k in v and v[k] is not None and not v[k] > 0:
                raise FamilyRefused(f"{k} must be above zero: the rate laws divide by it, or raise to it")
        for k in ("mu_max", "ks", "kd", "alpha", "beta", "maintenance", "mo", "feed_rate", "mu_set", "feed_conc",
                  "dilution_rate", "q_storage_max", "feed_start_h"):
            if _number(v.get(k)) and v[k] < 0:
                raise FamilyRefused(f"{k} cannot be negative")
        return v

    def y0_of(self, y0: dict[str, Any], v: dict[str, Any]) -> np.ndarray:
        y = np.zeros(NY)
        for s in ("X", "S"):
            if not _number(y0.get(s)) or not _finite(y0[s]):
                raise FamilyRefused(f"{self.id} cannot run: no start value for {s}")
        if self.has_P and not _number(y0.get("P")):
            raise FamilyRefused(f"{self.id} cannot run: no start value for P")
        y[_X], y[_S] = float(y0["X"]), float(y0["S"])
        y[_P] = float(y0.get("P") or 0.0) if self.has_P else 0.0
        vol = y0.get("V")
        y[_V] = float(vol) if _number(vol) else 1.0
        if self.has_N:
            if not _number(y0.get("N")):
                raise FamilyRefused(f"{self.id} cannot run: no start value for N (n_initial)")
            y[_N] = float(y0["N"])
        if min(y[_X], y[_S], y[_P], y[_N]) < 0:
            raise FamilyRefused("a start value cannot be negative")
        if not y[_V] > 0:
            raise FamilyRefused("the working volume at the start must be above zero")
        return y

    def check(self, v: dict[str, Any], t_end: float | None) -> None:
        """A family's own refusals, before it integrates."""
        if t_end is not None and not (_finite(t_end) and t_end > 0):
            raise FamilyRefused("the run length must be a number of hours above zero")

    def breakpoints(self, v: dict[str, Any]) -> list[float]:
        return []

    def refusal(self) -> str:
        return f"{self.id} cannot run"

    # ── the integrator ──

    def simulate(self, p: dict[str, Any], y0: dict[str, Any], t_end: float | None, *,
                 points: int = POINTS) -> Trajectory:
        """Integrate from `y0` to `t_end` hours, or until the sugar runs out
        when `t_end` is None. Refused in words when it cannot run."""
        v = self._prepared(p)
        y = self.y0_of(y0, v)
        self.check(v, t_end)
        traj = _integrate(self, v, y, t_end)
        traj.points = points
        traj.balance = mass_balance(traj)
        return traj

    # ── the fit ──

    def fit(self, series: dict[str, tuple[Any, Any]], p0: dict[str, float], fixed: dict[str, Any], *,
            unbounded: tuple[str, ...] = ()) -> FitResult:
        """The parameters in `p0` (their starting values; start values by
        their keys x0, s0, p0) fitted to `series` ({state: (hours, values)})
        on least_squares, every other value held as `fixed` gives it. Two
        passes as fermos.kinetic_fit weighs them (each series' residuals by
        its range, then by its own scatter); in log space, inside each spec's
        bounds and FIT_BOX of the start; the covariance pinv(JᵀJ)·s² in the
        parameters' own units and Student's t; a parameter in the
        Jacobian's null space is unidentified. With no X series μmax is
        reported unidentified by rule (OF-BLD-018 D4), the numbers noted.
        A key in `unbounded` keeps FIT_BOX alone, not its spec's bounds: a
        yield read against a gauge is no physical yield."""
        started = time.perf_counter()
        if self.socket:
            raise FamilyRefused(self.refusal())
        roles = [s for s in self.states if s in series and len(series[s][0])]
        if not roles:
            raise FamilyRefused(f"no series of {', '.join(self.states)} to fit {self.id} to")
        data = {s: (np.asarray(series[s][0], float), np.asarray(series[s][1], float)) for s in roles}
        keys = list(p0)
        specs = {s.key: s for s in self.specs()}
        unknown = [k for k in keys if k not in specs]
        if unknown:
            raise FamilyRefused(f"{self.id} has no parameter {', '.join(unknown)} to fit")
        t_end = max(float(t.max()) for t, _ in data.values())
        if not t_end > 0:
            raise FamilyRefused("the readings span no time")
        n_obs = sum(len(t) for t, _ in data.values())
        if n_obs <= len(keys):
            raise FamilyRefused(f"{n_obs} readings cannot pin down {len(keys)} parameters")
        linear = np.array([k in ("s0", "p0") for k in keys])
        lo, hi, q0 = [], [], []
        for k, lin in zip(keys, linear):
            s = specs[k]
            start = float(p0[k])
            if lin:
                rng = next((float(np.ptp(y)) for st, (_, y) in data.items() if START_STATE.get(k) == st), abs(start))
                half = max(rng, abs(start), ATOL)
                lo.append(max(s.min, start - half) if s.min is not None else start - half)
                hi.append(start + half)
                q0.append(start)
                continue
            floor = s.min if s.min is not None and s.min > 0 and k not in unbounded else None
            top = s.max if s.max is not None and s.max > 0 and k not in unbounded else None
            start = min(max(start, floor or start), top if top is not None else start)
            if not start > 0:
                raise FamilyRefused(f"{k} needs a starting value above zero to fit in log space")
            box = math.log(FIT_BOX)
            z = math.log(start)
            lo.append(max(math.log(floor), z - box) if floor else z - box)
            hi.append(min(math.log(top), z + box) if top is not None else z + box)
            q0.append(z)
        lo_a, hi_a = np.array(lo), np.array(hi)
        z0 = np.clip(np.array(q0, float), lo_a, hi_a)
        sims = [0]

        def to_q(z: np.ndarray) -> np.ndarray:
            return np.where(linear, z, np.exp(np.where(linear, 0.0, z)))

        def predict(q: np.ndarray) -> dict[str, np.ndarray]:
            given = dict(fixed)
            given.update(zip(keys, (float(x) for x in q)))
            y0 = {st: given.pop(k) for k, st in START_STATE.items() if k in given}
            sims[0] += 1
            traj = self.simulate(given, y0, t_end)
            return {s: traj.sample(t)[IX[s]] for s, (t, _) in data.items()}

        def residuals(z: np.ndarray, scales: list[float]) -> np.ndarray:
            try:
                q = to_q(z)
                if not np.all(np.isfinite(q)):
                    raise FloatingPointError("a parameter ran off to infinity")
                pr = predict(q)
            except (FamilyRefused, ZeroDivisionError, FloatingPointError, OverflowError, ValueError):
                return np.full(n_obs, FAILED_RESIDUAL)
            return np.concatenate([(pr[s] - y) / sc for (s, (_, y)), sc in zip(data.items(), scales)])

        ranges = [max(float(np.ptp(y)), ATOL) for _, y in data.values()]
        kw = {"x_scale": "jac", "diff_step": DIFF_STEP, "max_nfev": FIT_MAX_NFEV, "bounds": (lo_a, hi_a)}
        first = least_squares(residuals, z0, args=(ranges,), **kw)
        try:
            pr = predict(to_q(first.x))
        except FamilyRefused as e:
            raise FamilyRefused(f"the fit found no parameter set the family can run: {e}") from None
        scatters = [max(math.sqrt(float(((pr[s] - y) ** 2).mean())), ATOL) for s, (_, y) in data.items()]
        res = least_squares(residuals, first.x, args=(scatters,), **kw)
        q = to_q(res.x)
        dof = n_obs - len(q)
        s2 = float((res.fun ** 2).sum()) / dof
        # The Jacobian in the parameters' own units, so each interval is
        # symmetric in its value, as kinetic_fit's are, and can reach zero.
        J = res.jac / np.where(linear, 1.0, q)[None, :]
        sv = np.linalg.svd(J, compute_uv=False)
        rank = int((sv > RANK_TOL * sv[0]).sum()) if sv.size and sv[0] > 0 else 0
        cov = np.linalg.pinv(J.T @ J) * s2
        tcrit = float(student_t.ppf((1 + CONFIDENCE) / 2, dof))
        values, low, high, ident = {}, {}, {}, {}
        notes: list[str] = []
        for k, key in enumerate(keys):
            se = math.sqrt(max(float(cov[k, k]), 0.0))
            values[key] = float(q[k])
            low[key], high[key] = float(q[k] - tcrit * se), float(q[k] + tcrit * se)
            ident[key] = low[key] > 0
        if rank < len(keys):
            _, _, vt = np.linalg.svd(J)
            null = vt[rank:]
            lost = [key for k, key in enumerate(keys) if np.abs(null[:, k]).max() > NULL_WEIGHT]
            for key in lost:
                ident[key] = False
            notes.append(f"The Jacobian has rank {rank} of {len(keys)}: {', '.join(lost)} lie in its null space, so "
                         "the run does not pin them; they are unidentified, and their intervals, read through the "
                         "pseudo-inverse, understate how far they can move.")
        by_numbers = dict(ident)
        if res.status == 0:
            for key in keys:
                ident[key] = False
            notes.append(f"The optimizer stopped at its budget of {FIT_MAX_NFEV} evaluations before it converged, so "
                         "no parameter is reported identified.")
        if "X" not in data and "mu_max" in ident:
            ident["mu_max"] = False
            notes.append(f"No biomass series: μmax is reported unidentified by rule (OF-BLD-018 D4); the product and "
                         f"substrate alone gave {low['mu_max']:.4g} to {high['mu_max']:.4g} h⁻¹, because the curves' "
                         "shape carries it while the scale of the cells is free.")
        final = predict(q)
        quality = {}
        for s, (_, y) in data.items():
            rr = y - final[s]
            sst = float(((y - y.mean()) ** 2).sum())
            quality[s] = {"r2": 1 - float((rr ** 2).sum()) / sst if sst > 0 else 0.0,
                          "scatter": math.sqrt(float((rr ** 2).sum()) / max(len(rr) - 1, 1)),
                          "residuals": [float(x) for x in rr]}
        notes.append(f"least_squares: {first.nfev} and {res.nfev} evaluations in its two passes, status {res.status}.")
        return FitResult(keys=keys, values=values, low=low, high=high, identified=ident, identified_by_numbers=by_numbers,
                         covariance=[[float(x) for x in row] for row in cov], rank=rank,
                         singular_values=[float(x) for x in sv], quality=quality, notes=notes,
                         start={k: float(p0[k]) for k in keys}, simulations=sims[0], nfev=int(first.nfev + res.nfev),
                         seconds=time.perf_counter() - started)


def _number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _finite(x: Any) -> bool:
    return _number(x) and math.isfinite(x)


class BatchV1(Family):
    """batch_v1 — a batch culture: Monod growth with substrate (Haldane) and
    product inhibition, Luedeking–Piret product, Pirt maintenance.

    dX/dt = μ·X − kd·X
    μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ
    dP/dt = (α·μ + β)·X
    dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dP/dt − m·X
    states X, S, P; optional kd, Ki, m (zero when absent, said so)
    qO2 = μ/Yxo + mo
    OUR(t) = qO2·X

    As built: β·X is gated by (1 − P/Pmax)ⁿ too, so no product forms at
    Pmax; when S reaches zero the culture is starved (S held at zero, β·X and
    m·X cut to nothing); Ki absent is the Haldane term off.
    """

    id = "batch_v1"
    title = "Batch"
    what = "A batch culture: sugar and cells at the start, nothing added, run until the sugar runs out."
    states = ("X", "S", "P")

    def specs(self) -> list[ParameterSpec]:
        return [*_growth(), *_product(), *_inhibition(), *_oxygen(), *_start(volume=False),
                _run_length(until_run_out=True)]


class FedBatchV1(Family):
    """fedbatch_v1 — batch_v1 with a feed: adds V with dV/dt = F(t), feed
    concentration Sf, profile constant | exponential (set μ_set,
    F = μ_set·X·V/(Yxs·(Sf − S))) | steps (a table), dilution terms on every
    state.

    dX/dt = μ·X − kd·X − (F/V)·X
    μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ
    dP/dt = (α·μ + β)·X − (F/V)·P
    dS/dt = (F/V)·(Sf − S) − (1/Yxs)·μ·X − (1/Yps)·(α·μ + β)·X − m·X
    dV/dt = F(t)
    states X, S, P, V
    qO2 = μ/Yxo + mo
    OUR(t) = qO2·X

    As built: the exponential feed pays for the whole demand at μset,
    F = (μset/Yxs + (α·μset + β)/Yps + m)·X·V/(Sf − S); the steps profile
    waits for a parameter that holds a table; the feed carries sugar alone;
    its start and end split the integration; when S reaches zero and the
    feed brings less than β·X/Yps + m·X, those terms are cut to the supply.
    """

    id = "fedbatch_v1"
    title = "Fed-batch"
    what = "A batch fed sugar over the run, at a constant rate or one that holds a set growth rate."
    states = ("X", "S", "P", "V")
    feed = "fed"

    def specs(self) -> list[ParameterSpec]:
        return [*_growth(), *_product(), *_inhibition(), *_oxygen(), *_feed_specs(), *_start(volume=True),
                _run_length(until_run_out=False)]

    def irrelevant(self, p: dict[str, Any]) -> set[str]:
        return {"constant": {"mu_set"}, "exponential": {"feed_rate"}}.get(p.get("feed_profile"), set())

    def check(self, v: dict[str, Any], t_end: float | None) -> None:
        if t_end is None:
            raise FamilyRefused("fedbatch_v1 needs a run length: a feed keeps bringing sugar, so it need not run out")
        super().check(v, t_end)
        if v.get("feed_profile") not in ("constant", "exponential"):
            raise FamilyRefused(f"the feed profile is constant or exponential; {v.get('feed_profile')!r} is neither")
        if v["feed_profile"] == "exponential" and v["mu_set"] > v["mu_max"]:
            raise FamilyRefused("μset is above μmax: no exponential feed can hold a growth rate the cells cannot reach")
        end = v.get("feed_end_h")
        if end is not None and end < v["feed_start_h"]:
            raise FamilyRefused("the feed ends before it starts")

    def breakpoints(self, v: dict[str, Any]) -> list[float]:
        return [b for b in (v["feed_start_h"], v.get("feed_end_h")) if b is not None]


class ChemostatV1(Family):
    """chemostat_v1 — continuous culture: dilution D on every state, feed
    Sf, steady state solved and the dynamic path integrated; washout reported
    when D ≥ μmax·Sf/(Ks + Sf).

    dX/dt = μ·X − kd·X − D·X
    μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ
    dP/dt = (α·μ + β)·X − D·P
    dS/dt = D·(Sf − S) − (1/Yxs)·μ·X − (1/Yps)·(α·μ + β)·X − m·X
    states X, S, P
    qO2 = μ/Yxo + mo
    OUR(t) = qO2·X

    As built: washout is D ≥ μ(Sf, P = 0) − kd, which is D5's expression
    when kd and Ki are off, and both are reported; the steady state is the
    low-S root of μ(S, P(S)) = D + kd.
    """

    id = "chemostat_v1"
    title = "Chemostat"
    what = "A continuous culture: fresh medium in and broth out at one dilution rate, toward a steady state."
    states = ("X", "S", "P")
    feed = "chemostat"

    def specs(self) -> list[ParameterSpec]:
        dilution = _spec("dilution_rate", "dilution rate", "D", "feed flow over working volume", "rate", "h⁻¹",
                         "Dilution", ["assumption"],
                         reason=("a physical limit: no negative rate; above the washout rate the cells wash out, "
                                 "which the simulation computes and shows"))
        return [*_growth(), *_product(), *_inhibition(), *_oxygen(), dilution, _feed_conc("Dilution"),
                *_start(volume=False), _run_length(until_run_out=False)]

    def check(self, v: dict[str, Any], t_end: float | None) -> None:
        if t_end is None:
            raise FamilyRefused("chemostat_v1 needs a run length for its dynamic path: the sugar is fed continuously")
        super().check(v, t_end)

    def washout(self, p: dict[str, Any]) -> dict[str, Any]:
        """The dilution rate at which the cells wash out: D5's expression
        and the general one, μ(Sf, P = 0) − kd."""
        v = self._prepared(p)
        d5 = v["mu_max"] * v["feed_conc"] / (v["ks"] + v["feed_conc"])
        general = _mu_of(self, v, v["feed_conc"], 0.0, 0.0) - v["kd"]
        return {"dWashoutD5": d5, "dWashout": general, "washout": v["dilution_rate"] >= general}

    def steady_state(self, p: dict[str, Any]) -> dict[str, Any]:
        """X, S and P where every derivative is zero, or washout."""
        v = self._prepared(p)
        w = self.washout(v)
        D, sf, kd = v["dilution_rate"], v["feed_conc"], v["kd"]
        out = {"washout": True, "X": 0.0, "S": sf, "P": 0.0, "dWashout": w["dWashout"], "dWashoutD5": w["dWashoutD5"],
               "dilutionRate": D}
        if w["washout"]:
            return out
        mu_s = D + kd

        def x_of(S: float, P: float) -> tuple[float, float]:
            npg = v["beta"] * _f_product(v, P)
            sigma = mu_s / v["yxs"] + (v["alpha"] * mu_s + npg) / v["yps"] + v["maintenance"]
            return D * (sf - S) / sigma, npg

        def p_of(S: float) -> float:
            if v.get("p_max") is None:
                x, npg = x_of(S, 0.0)
                return (v["alpha"] * mu_s + npg) * x / D

            def h(P: float) -> float:
                x, npg = x_of(S, P)
                return P - (v["alpha"] * mu_s + npg) * x / D

            return v["p_max"] if h(v["p_max"]) <= 0 else brentq(h, 0.0, v["p_max"], xtol=ROOT_TOL, rtol=ROOT_TOL)

        def g(S: float) -> float:
            return _mu_of(self, v, S, p_of(S), 0.0) - mu_s

        grid = np.linspace(0.0, sf, SCAN_POINTS)[1:]
        prev_s, prev_g = grid[0] * TIME_EPS, g(grid[0] * TIME_EPS)
        root = None
        for s in grid:
            gs = g(float(s))
            if prev_g < 0.0 <= gs:
                root = brentq(g, prev_s, float(s), xtol=ROOT_TOL, rtol=ROOT_TOL)
                break
            prev_s, prev_g = float(s), gs
        if root is None:
            return out
        P = p_of(root)
        X, _ = x_of(root, P)
        return {**out, "washout": False, "X": float(X), "S": float(root), "P": float(P), "mu": mu_s}


class StorageV1(Family):
    """storage_v1 — two-phase growth then storage: a second substrate N
    with its own Monod term limiting growth, a storage product Q
    accumulating when N is exhausted at rate qQ,max·S/(Ks+S)·(1 − Q/Qmax);
    the PHA and lipid shape, archived with the PHA program but general.

    μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · N/(KN + N)
    dX/dt = μ·X − kd·X
    dN/dt = −(1/Yx/N)·μ·X
    dQ/dt = qQ,max·S/(Ks+S)·(1 − (Q/(X + Q))/Qmax)·X   once N is exhausted, else 0
    dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dQ/dt − m·X
    states X, S, N, Q
    qO2 = μ/Yxo + mo
    OUR(t) = qO2·X

    As built: Yps is the store's yield on S, so α, β, Pmax and n are not this
    family's; Q starts at zero, said so; Q/Qmax is the store's share of the
    cell dry weight, X the residual biomass; N is exhausted at RUN_OUT_SHARE
    of KN; with kd set, decay of X alone lifts the share past Qmax.
    """

    id = "storage_v1"
    title = "Growth then storage"
    what = "Cells grow until a second nutrient runs out, then store a product (the PHA and lipid shape)."
    states = ("X", "S", "N", "Q")
    program = "pha"
    has_P = False
    has_N = True
    has_Q = True

    def specs(self) -> list[ParameterSpec]:
        product = [s for s in _product() if s.key in ("yps", "maintenance")]
        inhibition = [s for s in _inhibition() if s.key == "ki_substrate"]
        return [*_growth(), *product, *inhibition, *_oxygen(), *_storage_specs(), *_start(volume=False, product=False),
                _run_length(until_run_out=True)]


class LightV1(Family):
    """light_v1 — light-limited growth: declared with its parameters
    (incident irradiance, path length, attenuation coefficient,
    photoinhibition constant) and no rhs: a socket that refuses to run in
    words."""

    id = "light_v1"
    title = "Light-limited (a socket)"
    what = "Growth limited by the light the culture receives: declared, not built; it refuses to run."
    states = ("X",)
    socket = True

    def specs(self) -> list[ParameterSpec]:
        return _light_specs()

    def refusal(self) -> str:
        return ("light_v1 is declared and not built: it names incident irradiance, path length, attenuation and "
                "photoinhibition, and holds no rate law. What would build it: the mean irradiance over the path by "
                "Beer–Lambert on the cells' attenuation, a growth-on-light curve with photoinhibition fitted to a "
                "photobioreactor run, and a deposition that records irradiance.")


FAMILIES: dict[str, Family] = {f.id: f for f in (BatchV1(), FedBatchV1(), ChemostatV1(), StorageV1(), LightV1())}


def family(family_id: str) -> Family:
    try:
        return FAMILIES[family_id]
    except KeyError:
        raise FamilyRefused(f"there is no model family {family_id!r}: the families are {', '.join(FAMILIES)}") from None


# ── the integrator: segments split at the feed's breakpoints and at mode changes ─


def _integrate(fam: Family, v: dict[str, Any], y0: np.ndarray, t_end: float | None) -> Trajectory:
    started = time.perf_counter()
    until_run_out = t_end is None
    if until_run_out:
        if not y0[1] > 0:
            raise FamilyRefused("there is no sugar at the start, so it cannot run out: name a run length")
        if not v["mu_max"] > 0:
            raise FamilyRefused("μmax is zero, so the cells never grow and the sugar never runs out: name a run length")
        horizon = 1.0 / v["mu_max"]
    else:
        horizon = float(t_end)
    y = y0.copy()
    s_out = RUN_OUT_SHARE * max(y[1], 0.0)
    n_out = RUN_OUT_SHARE * v["k_n"] if fam.has_N else None
    mode = Mode(storing=bool(fam.has_N and y[_N] <= n_out))
    bps = sorted({b for b in fam.breakpoints(v) if b > 0})
    counter = [0]
    t = 0.0
    segs: list[Segment] = []
    events: list[dict[str, Any]] = []
    notes: list[str] = []
    runout = None
    n_exhausted = 0.0 if mode.storing else None
    doublings = 0
    s_at_horizon_start = y[1]
    stuck = 0
    while True:
        if t >= horizon * (1 - TIME_EPS):
            if not until_run_out or runout is not None:
                break
            # The horizon reached with sugar left: double it, unless the sugar
            # has stopped falling.
            if s_at_horizon_start - y[1] <= RTOL * max(y0[1], 0.0) + ATOL and not mode.starved:
                raise FamilyRefused(
                    f"the sugar does not run out: it stopped falling at {max(y[1], 0.0):.4g} g L⁻¹ after "
                    f"{t:.4g} h, so growth stopped with sugar left (product inhibition or the second nutrient); "
                    "name a run length")
            doublings += 1
            if doublings > HORIZON_DOUBLINGS:
                raise FamilyRefused(f"the sugar does not run out within {t:.4g} h; name a run length")
            s_at_horizon_start = y[1]
            horizon *= 2
            continue
        if len(segs) >= MAX_SEGMENTS:
            raise FamilyRefused(f"the integration split into more than {MAX_SEGMENTS} pieces: its mode switches chatter")
        t_stop = next((b for b in bps if b > t * (1 + TIME_EPS) + TIME_EPS and b < horizon), horizon)
        t_reg = (t + t_stop) / 2
        demand_pos = False
        if y[1] <= 0.0:
            y[1] = 0.0
            supply, demand = _supply_demand(fam, v, y, t_reg)
            demand_pos = demand > 0.0
            mode = replace(mode, starved=supply < demand or (supply == 0.0 and not demand_pos))
        elif mode.starved:
            mode = replace(mode, starved=False)
        evs: list[Callable] = []
        kinds: list[str] = []
        if not mode.starved:
            def ev_zero(_t: float, yy: np.ndarray) -> float:
                return yy[1]
            ev_zero.terminal, ev_zero.direction = True, -1
            evs.append(ev_zero)
            kinds.append("S=0")
        # Never attach an event that is identically zero: scipy counts 0 → 0
        # as a crossing and the integration stops making progress.
        if mode.starved and fam.feed != "none" and demand_pos:
            def ev_fed(_t: float, yy: np.ndarray, _r: float = t_reg) -> float:
                s, d = _supply_demand(fam, v, yy, _r)
                return s - d
            ev_fed.terminal, ev_fed.direction = True, 1
            evs.append(ev_fed)
            kinds.append("fed")
        if runout is None and s_out > 0.0 and not mode.starved:
            def ev_out(_t: float, yy: np.ndarray) -> float:
                return yy[1] - s_out
            ev_out.terminal, ev_out.direction = until_run_out, -1
            evs.append(ev_out)
            kinds.append("runout")
        if fam.has_N and not mode.storing:
            def ev_n(_t: float, yy: np.ndarray) -> float:
                return yy[_N] - n_out
            ev_n.terminal, ev_n.direction = True, -1
            evs.append(ev_n)
            kinds.append("N exhausted")
        sol = solve_ivp(_rhs(fam, v, mode, t_reg, counter), (t, t_stop), y, method="LSODA", rtol=RTOL, atol=ATOL,
                        events=evs or None, dense_output=True)
        if sol.status < 0:
            raise FamilyRefused(f"the integrator failed at {t:.6g} h: {sol.message}")
        t1 = float(sol.t[-1])
        segs.append(Segment(t, t1, sol.sol if t1 > t else None, mode, t_reg, y.copy()))
        fired = None
        for kind, te in zip(kinds, sol.t_events or []):
            for tev in te:
                events.append({"kind": kind, "t": float(tev)})
                if kind == "runout" and runout is None:
                    runout = float(tev)
            if len(te) and abs(float(te[-1]) - t1) <= TIME_EPS * max(1.0, t1) and (kind != "runout" or until_run_out):
                fired = kind
        stuck = stuck + 1 if t1 - t <= TIME_EPS * max(1.0, t) else 0
        if stuck > STALL_STEPS:
            raise FamilyRefused(f"no progress at {t:.6g} h: an event fires at its own start")
        t = t1
        y = np.array(sol.y[:, -1], float)
        if fired == "S=0":
            y[1] = 0.0
        elif fired == "fed":
            mode = replace(mode, starved=False)
            y[1] = max(y[1], 0.0)
        elif fired == "N exhausted":
            n_exhausted = t
            mode = replace(mode, storing=True)
        elif fired == "runout":
            break
    if until_run_out and runout is None:
        raise FamilyRefused("the sugar does not run out; name a run length")
    if mode.starved or any(e["kind"] == "S=0" for e in events):
        notes.append("The sugar reached zero; from then on the culture was starved: it did not grow, and what it made "
                     "and burned without growing was cut to what a feed brought.")
    return Trajectory(family=fam.id, p=v, y0=y0.copy(), segments=segs, t_final=t, y_final=y, runout_h=runout,
                      n_exhausted_h=n_exhausted, events=events, notes=notes, nfev=counter[0],
                      seconds=time.perf_counter() - started)


# ── readers: balance, oxygen, harvest ───────────────────────────────────


def mass_balance(traj: Trajectory, at: float | None = None) -> dict[str, float]:
    """Sugar consumed (start + fed − drawn off − left, in grams) against the
    auxiliary consumption states, and against what X, P and Q say through
    the yields. Relative errors; `closure` is the larger."""
    fam = FAMILIES[traj.family]
    v = traj.p
    y0 = traj.y0
    y = traj.y_final if at is None else traj.at(at)
    V0, V = y0[_V], y[_V]
    consumed = y0[_S] * V0 + y[_MIN] - y[_MOUT_S] - y[_S] * V
    aux = y[IX["Cg"]] + y[IX["Cp"]] + y[IX["Cq"]] + y[IX["Cm"]]
    grown = y[_X] * V - y0[_X] * V0 + v["kd"] * y[_IXV] + y[_MOUT_X]
    cross = grown / v["yxs"] + v["maintenance"] * y[IX["IXVphi"]]
    if fam.has_P:
        cross += (y[_P] * V - y0[_P] * V0 + y[_MOUT_P]) / v["yps"]
    if fam.has_Q:
        cross += (y[_Q] * V - y0[_Q] * V0 + y[_MOUT_Q]) / v["yps"]
    scale = max(abs(consumed), ATOL)
    rel_aux, rel_cross = abs(consumed - aux) / scale, abs(consumed - cross) / scale
    return {"consumed": float(consumed), "aux": float(aux), "cross": float(cross), "relAux": float(rel_aux),
            "relCross": float(rel_cross), "closure": float(max(rel_aux, rel_cross))}


def made_and_used(traj: Trajectory, at: float) -> tuple[float, float]:
    """Grams of product (or store) made and of sugar used, start to `at`."""
    fam = FAMILIES[traj.family]
    y0, y = traj.y0, traj.at(at)
    used = y[IX["Cg"]] + y[IX["Cp"]] + y[IX["Cq"]] + y[IX["Cm"]]
    k, out = (_P, _MOUT_P) if fam.has_P else (_Q, _MOUT_Q)
    made = y[k] * y[_V] - y0[k] * y0[_V] + y[out]
    return float(made), float(used)


def _q_o2(fam: Family, v: dict[str, Any], col: np.ndarray, seg: Segment) -> float:
    tt = _terms(fam, v, col, seg.mode, seg.t_regime)
    return tt["mu"] / v["yxo"] + v["mo"] * tt["phi"]


def oxygen(p: dict[str, Any], traj: Trajectory, times: Any = None) -> list[float]:
    """OUR(t) = qO2·X in g O₂ L⁻¹ h⁻¹ on `times` (the display grid when
    None), qO2 = μ/Yxo + mO, mO cut by the starved share as maintenance is.
    All zero when Yx/o is absent: the culture is anaerobic, and the caller
    says so."""
    fam = FAMILIES[traj.family]
    times = traj.times() if times is None else np.asarray(times, float)
    if p.get("yxo") is None:
        return [0.0] * len(times)
    v = traj.p
    cols = traj.sample(times)
    return [float(_q_o2(fam, v, col, traj.segment_at(float(t))) * max(col[0], 0.0)) for t, col in zip(times, cols.T)]


def oxygen_peak(p: dict[str, Any], traj: Trajectory) -> tuple[float, float | None]:
    """The peak OUR and its hour, read on the solver's own steps."""
    if p.get("yxo") is None:
        return 0.0, None
    times = traj.times(steps=True)
    our = oxygen(p, traj, times)
    k = int(np.argmax(our))
    return float(our[k]), float(times[k])


def harvest(traj: Trajectory, when: float | None = None) -> dict[str, Any]:
    """The state at harvest: the hour the sugar runs out (a batch's), the
    run's end (a fed culture's: its sugar is fed again), or `when`."""
    fam = FAMILIES[traj.family]
    if when is None and fam.feed != "none":
        when = traj.t_final
    if when is None:
        if traj.runout_h is None:
            raise FamilyRefused("the sugar does not run out in this simulation; name the harvest hour")
        t, how = traj.runout_h, "the hour the sugar runs out"
    else:
        if not (_finite(when) and 0.0 <= when <= traj.t_final * (1 + TIME_EPS)):
            raise FamilyRefused(f"the harvest hour lies outside the simulation, 0 to {traj.t_final:.4g} h")
        t, how = min(float(when), traj.t_final), "an hour a person set"
    y = traj.at(t)
    state = {s: float(y[IX[s]]) for s in fam.states}
    if "V" not in state:
        state["V"] = float(y[_V])
    return {"hour": float(t), "how": how, "state": state, "units": {**fam.state_units, "V": "L"},
            "amounts": {s: float(y[IX[s]] * y[_V]) for s in fam.states if s != "V"},
            "absent": "By-products the family does not model (carbon dioxide, glycerol, acids) are absent."}
