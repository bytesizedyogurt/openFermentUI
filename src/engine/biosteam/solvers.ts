// The two root-finders and the one fixed-point accelerator that bioSTEAM leans
// on, ported from flexsolve.
//
// flexsolve is a separate package by the same author and is *not* vendored in
// the BioSTEAM v2.53.11 tarball, so these are implemented from the standard
// textbook definitions rather than transliterated line by line: Wegstein's
// accelerated substitution, Brent's bracketing method, and the plain secant.
// Where flexsolve's behaviour is observable from a bioSTEAM call site it is
// matched — `size_batch` calls `wegstein(f, 0.5, checkconvergence=False,
// checkiter=False)`, and `TEA.solve_IRR` calls `aitken_secant(NPV_at_IRR, IRR,
// 1.0001 * IRR + 1e-3, ..., checkiter=False)`, so neither of those may raise on
// a failure to converge.
//
// `wegstein` has since been checked against flexsolve 0.5.10 directly and
// agrees with it to the last digit on the one call bioSTEAM makes; see its
// doctest. `solveBrentq` and `solveSecant` have NOT been reconciled that far,
// and the gaps below are larger than iteration counts.
//
// Left behind, and what it costs:
//
//  - Aitken acceleration. The secant here is unaccelerated. bioSTEAM's IRR
//    solve calls `aitken_secant`, so the iterate sequences differ; both reach
//    the same root.
//  - The `ytol` criterion. This is not a "second" criterion in flexsolve, it is
//    the *primary* one: `secant`/`aitken_secant` default to `xtol=0.,
//    ytol=5e-8`, so with default arguments `abs(dx) < xtol` can never fire and
//    convergence is decided entirely on |f(x)|. `solveSecant` below has no
//    y-criterion at all, only xtol. bioSTEAM always passes both (`xtol=1e-6,
//    ytol=10.` for IRR, `xtol=10, ytol=100.` for price), and a caller porting
//    those sites must supply the y-side itself.
//  - flexsolve's secant recurrence. Upstream steps `x1 = x0 - y1*dx/(y1-y0)`
//    off the *previous* point with a carried `dx`; the textbook step used here
//    is `x1 - y1*dx/(y1-y0)`. Different sequences, same root.
//  - The sign-change handoff. Both flexsolve secants bail out into
//    `IQ_interpolation` the moment `y1*y0 < 0`, so once the iterates straddle
//    the root upstream is running a *bounded* solver and cannot run away.
//    `solveSecant` has no such guard.
//  - `checkiter`. NOT every bioSTEAM call site passes False: `_tea.py:1204`
//    (`TEA.solve_price`) passes `checkiter=True` and wraps the call in
//    try/except, *relying on the raise* to fall back to `find_bracket` plus
//    `IQ_interpolation`. A port of `solve_price` therefore cannot be built on
//    `solveSecant` alone, because it never raises — see its note below.
//  - `IQ_interpolation` itself. bioSTEAM never calls brentq; every bracketed
//    solve goes through `IQ_interpolation`. `solveBrentq` is a substitute of
//    the same class, not a transliteration: on x² − 2 over [0, 2] upstream
//    returns 1.4142135623734062 and this returns 1.4142135623731364, both
//    inside the requested xtol but by different routes. Also left behind are
//    `find_bracket`, `false_position`, IQ's optional x-guess, vector-valued
//    fixed points, and the numba-compiled variants.

/** Convergence controls. `xtol` is on the solver's own variable, not on f. */
export interface SolverOptions {
  xtol?: number;
  maxiter?: number;
}

/**
 * Wegstein's accelerated fixed-point iteration: solve x = f(x).
 *
 * The step is a secant extrapolation of direct substitution,
 *
 *   w = (f(xₙ) − f(xₙ₋₁)) / (xₙ − xₙ₋₁),  q = w / (w − 1),
 *   xₙ₊₁ = q·xₙ + (1 − q)·f(xₙ),
 *
 * which is what makes it useful here: direct substitution diverges whenever
 * |w| > 1, and Wegstein converges on exactly those maps. At w = 0 it degenerates
 * to plain substitution, which is why the first step — where there is no slope
 * yet — is taken as substitution.
 *
 * Returns the best iterate found rather than raising when it fails to converge,
 * because `size_batch` asks for it that way (`checkconvergence=False,
 * checkiter=False`) and would rather size a vessel off a near-fixed-point than
 * fail the whole flowsheet. Callers who need certainty must check the residual
 * themselves.
 *
 * On convergence this returns f(xₙ), not xₙ — the same as flexsolve, whose
 * `wegstein` returns `g1` from inside the loop. The two differ by less than
 * `xtol`, but f(xₙ) is one more contraction along and is measurably the better
 * of the pair: on the doctest below it is 35x closer to the exact answer.
 *
 * Doctest — the loading-time fixed point inside bioSTEAM's `size_batch`, with
 * F_vol = 1000 m³/hr, τ_reaction = 30 hr, τ_cleaning = 3 hr, V_wf = 0.95,
 * V_max = 1000 m³, started from 0.5 hr (exact fixed point 0.95, the positive
 * root of τ² + 32.05τ − 31.35):
 *
 *   wegstein(f, 0.5)                 -> 0.950000000001627 hr
 *   wegstein(f, 0.5, {xtol: 1e-14})  -> 0.95 hr
 *
 * matching upstream's reported 'Loading time': 0.950000000001627 exactly, and
 * matching `flx.wegstein(f, 0.5, checkconvergence=False, checkiter=False)` run
 * against flexsolve 0.5.10 itself. The iterate sequence is identical to
 * flexsolve's: 0.5, 0.96313364055299544, 0.95000507685299118,
 * 0.94999999994348261, with f of that last one being the returned value.
 *
 * Two deviations from flexsolve, both confined to cases upstream leaves
 * unspecified:
 *
 *  - flexsolve's default is xtol = 5e-8, not 1e-8. `size_batch` passes no xtol,
 *    so upstream runs this solve at 5e-8; both tolerances stop on the same
 *    iterate here, so the doctest above is unaffected.
 *  - out of iterations, flexsolve returns its last (possibly diverged) iterate
 *    while this returns the best residual seen. On the divergent map x ↦ x + 1
 *    from 0, flexsolve returns 51 and this returns 0. Neither is a fixed point;
 *    neither function certifies its result.
 */
export function wegstein(
  f: (x: number) => number,
  x0: number,
  opts: SolverOptions = {},
): number {
  const xtol = opts.xtol ?? 1e-8;
  const maxiter = opts.maxiter ?? 50;

  let x = x0;
  let g = f(x);
  let best = x;
  let bestResidual = Math.abs(g - x);
  // Already a fixed point: hand back f(x₀) rather than x₀, for the same reason
  // the loop below hands back f(xₙ).
  if (bestResidual < xtol) return g;

  // No slope estimate exists yet, so the opening step is direct substitution.
  let xNew = g;

  for (let i = 0; i < maxiter; i++) {
    const gNew = f(xNew);
    const residual = Math.abs(gNew - xNew);
    if (residual < bestResidual) {
      bestResidual = residual;
      best = xNew;
    }
    // Convergence is on the fixed-point residual |f(x) − x|, matching
    // flexsolve, which forms `e = abs(g1 - x1)` and tests that — not the step
    // length. Returning gNew rather than xNew is also flexsolve's choice
    // (`return g1`), and is what reproduces the upstream doctest digit for
    // digit; returning xNew instead costs a factor of 35 in accuracy there.
    if (residual < xtol) return gNew;

    const dx = xNew - x;
    const w = dx === 0 ? 1 : (gNew - g) / dx;
    x = xNew;
    g = gNew;
    // w → 1 sends q to infinity: the two secant points lie on a line parallel
    // to the fixed-point line and the extrapolation has nowhere to land, so
    // fall back to substitution and let the next pair of points recover.
    xNew =
      Number.isFinite(w) && Math.abs(w - 1) > 1e-12 ? (w * x - g) / (w - 1) : g;
  }
  return best;
}

/**
 * Brent's method: the root of f between `a` and `b`, which must bracket it.
 *
 * Inverse quadratic interpolation where the interpolant behaves and bisection
 * where it does not, so it keeps the bracket at every step and cannot wander
 * off the way a secant can. This is the shape of solve that bioSTEAM reaches
 * for when it has bounds — `flx.IQ_interpolation` on a known IRR range, or on a
 * product price bracketed by `find_bracket`.
 *
 * Raises on a bad bracket, naming both endpoint values, because that is nearly
 * always a modelling error worth reading (an NPV that never crosses zero over
 * the whole range of prices offered) rather than a numerical hiccup to paper
 * over.
 *
 * Doctest:
 *
 *   solveBrentq(x => x * x - 2, 0, 2)        -> 1.4142135623731364
 *   solveBrentq(x => Math.cos(x) - x, 0, 2)  -> 0.7390851332251661
 */
export function solveBrentq(
  f: (x: number) => number,
  a: number,
  b: number,
  opts: SolverOptions = {},
): number {
  const xtol = opts.xtol ?? 1e-8;
  // 200 matches the maxiter bioSTEAM passes on its IRR and price solves; with
  // the bisection fallback underneath, that is far more than a bracket of any
  // sane width needs.
  const maxiter = opts.maxiter ?? 200;

  let fa = f(a);
  let fb = f(b);
  if (fa === 0) return a;
  if (fb === 0) return b;
  if (fa > 0 === fb > 0) {
    throw new Error(
      `Root is not bracketed: f(${a}) = ${fa} and f(${b}) = ${fb} have the same sign.`,
    );
  }

  // `c` is the counterpoint that keeps the root bracketed with `b`; `d` is the
  // step actually taken and `e` the one before it, which is what decides
  // whether interpolation has been making enough progress to be trusted.
  let c = b;
  let fc = fb;
  let d = b - a;
  let e = d;

  for (let i = 0; i < maxiter; i++) {
    if (fb > 0 === fc > 0) {
      c = a;
      fc = fa;
      d = b - a;
      e = d;
    }
    if (Math.abs(fc) < Math.abs(fb)) {
      a = b;
      b = c;
      c = a;
      fa = fb;
      fb = fc;
      fc = fa;
    }
    const tol = 2 * Number.EPSILON * Math.abs(b) + 0.5 * xtol;
    const xm = 0.5 * (c - b);
    if (Math.abs(xm) <= tol || fb === 0) return b;

    if (Math.abs(e) >= tol && Math.abs(fa) > Math.abs(fb)) {
      const s = fb / fa;
      let p: number;
      let q: number;
      if (a === c) {
        // Only two distinct points, so the interpolant is a secant.
        p = 2 * xm * s;
        q = 1 - s;
      } else {
        const r = fa / fc;
        const t = fb / fc;
        p = s * (2 * xm * r * (r - t) - (b - a) * (t - 1));
        q = (r - 1) * (t - 1) * (s - 1);
      }
      if (p > 0) q = -q;
      p = Math.abs(p);
      // Accept the interpolated step only if it stays inside the bracket and is
      // no worse than half the step before it; otherwise bisect, which is what
      // bounds the iteration count.
      if (2 * p < Math.min(3 * xm * q - Math.abs(tol * q), Math.abs(e * q))) {
        e = d;
        d = p / q;
      } else {
        d = xm;
        e = d;
      }
    } else {
      d = xm;
      e = d;
    }

    a = b;
    fa = fb;
    b += Math.abs(d) > tol ? d : xm >= 0 ? tol : -tol;
    fb = f(b);
  }
  // Out of iterations, but the bracket was never given up, so `b` is still
  // within the last interval known to contain the root.
  return b;
}

/**
 * Secant method for the unbracketed case: the root of f near `x0`.
 *
 * `TEA.solve_IRR` has no bounds unless the caller supplies them, so it opens
 * with an unbounded solve from the previous IRR, offsetting the second point by
 * `1.0001 * x0 + 1e-3` — the same offset is used here so that a solve started
 * from zero still gets a finite first slope.
 *
 * Like `wegstein`, this returns the best iterate instead of raising. That
 * matches `solve_IRR`'s `checkiter=False` but NOT `solve_price`, which passes
 * `checkiter=True` at `_tea.py:1204` precisely so that a failed secant raises
 * and it can retry with `find_bracket` + `IQ_interpolation`. That fallback
 * cannot be expressed on top of this function; a `solve_price` port needs
 * either a raising variant or an explicit residual test to trigger the bracket
 * path.
 *
 * The return value is in no case certified to be a root. On x² + 1, which has
 * none, this returns 0.0005496976663723618 with f = 1.0000003 — a number that
 * looks like an answer and is not one. (flexsolve is no better here: with
 * checkiter=False it returns 0.6836040863220265.) Anything that shows this
 * result to a reader must evaluate f there and report the residual.
 *
 * Doctest — the IRR of the cashflow [-1000, 400, 400, 400] USD:
 *
 *   solveSecant(npv, 0.01)  -> 0.09701025740327299   (NPV there: -5.7e-14 USD)
 *   solveSecant(x => x * x - 2, 1)  -> 1.414213562373095
 *
 * flexsolve 0.5.10 on the same cashflow, tightened to xtol=1e-8/ytol=1e-12:
 * `secant` -> 0.09701025740327293, `aitken_secant` -> 0.09701025740327301. At
 * the tolerances bioSTEAM actually uses (xtol=1e-6, ytol=10 USD) upstream stops
 * much earlier, at 0.0970114854865835.
 */
export function solveSecant(
  f: (x: number) => number,
  x0: number,
  opts: SolverOptions = {},
): number {
  const xtol = opts.xtol ?? 1e-8;
  const maxiter = opts.maxiter ?? 200;

  let x = x0;
  let y = f(x);
  if (y === 0) return x;
  let best = x;
  let bestResidual = Math.abs(y);

  let xNext = 1.0001 * x + 1e-3;

  for (let i = 0; i < maxiter; i++) {
    const yNext = f(xNext);
    const residual = Math.abs(yNext);
    if (residual < bestResidual) {
      bestResidual = residual;
      best = xNext;
    }
    if (yNext === 0) return xNext;

    const dy = yNext - y;
    // A flat secant has no root to point at; give up with what we have rather
    // than stepping to infinity.
    if (dy === 0 || !Number.isFinite(dy)) return best;

    const step = (yNext * (xNext - x)) / dy;
    x = xNext;
    y = yNext;
    xNext = x - step;
    if (!Number.isFinite(xNext)) return best;

    if (Math.abs(step) < xtol) {
      const yFinal = f(xNext);
      if (Math.abs(yFinal) < bestResidual) {
        bestResidual = Math.abs(yFinal);
        best = xNext;
      }
      return best;
    }
  }
  return best;
}
