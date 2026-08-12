// Uncertainty and sensitivity, in bioSTEAM's `evaluation.Model` idiom.
//
// Ported in shape from BioSTEAM v2.53.11 `evaluation/_model.py` and
// `evaluation/_parameter.py` (UIUC/NCSA licence; see NOTICE.md). Upstream draws
// samples with chaospy and computes rank correlation with scipy; both are
// reimplemented here because neither is available in a browser.
//
// The reason this replaces the tornado bars the app used to ship: those bars
// were authored percentages. They said "titer moves the answer 118% down and
// 41% up" because somebody typed 118 and 41. A Spearman coefficient over a
// Latin hypercube says the same kind of thing, but it is a measurement of the
// model rather than an assertion about it, and it changes when the model
// changes. A sensitivity analysis that cannot be wrong is not one.
import { spearmanRho } from './stats';

/** A parameter to vary, and how far. */
export interface ModelParameter {
  key: string;
  name: string;
  units: string;
  baseline: number;
  bounds: [number, number];
  distribution: 'triangular' | 'uniform';
}

/** Something to measure at each sample. */
export interface ModelMetric<T> {
  key: string;
  name: string;
  units: string;
  get: (result: T) => number;
}

export interface ModelTable {
  /** One row per sample: the drawn parameter values. */
  samples: Record<string, number>[];
  /** One row per sample: the metric values. */
  metrics: Record<string, number>[];
  /** Spearman ρ of each parameter against each metric. */
  rho: Record<string, Record<string, number>>;
  /** Samples that failed to evaluate, kept as a count rather than hidden. */
  failed: number;
}

/**
 * mulberry32 — a small, fast, well-distributed PRNG.
 *
 * Seeded deliberately. An uncertainty analysis that gives a different tornado
 * on every render is not reproducible, and a reader who cannot get the same
 * picture twice has no way to check it. The seed is part of the result.
 */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function next(): number {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Latin hypercube sample on the unit interval, one column per parameter.
 *
 * Stratified rather than uniform: N samples cover N equal strata of each
 * parameter exactly once, so a hundred draws explore the space about as well as
 * several hundred independent ones. This is what bioSTEAM uses by default and
 * the reason its Monte Carlo converges at sample counts a browser can afford.
 */
export function latinHypercube(n: number, dims: number, rand: () => number): number[][] {
  const out: number[][] = Array.from({ length: n }, () => new Array<number>(dims).fill(0));
  for (let d = 0; d < dims; d++) {
    const perm = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [perm[i], perm[j]] = [perm[j], perm[i]];
    }
    for (let i = 0; i < n; i++) out[i][d] = (perm[i] + rand()) / n;
  }
  return out;
}

/** Inverse CDF of a triangular distribution with mode `c` on [a, b]. */
export function triangularInverseCDF(u: number, a: number, c: number, b: number): number {
  if (b <= a) return a;
  const mode = Math.min(Math.max(c, a), b);
  const f = (mode - a) / (b - a);
  if (u < f) return a + Math.sqrt(u * (b - a) * (mode - a));
  return b - Math.sqrt((1 - u) * (b - a) * (b - mode));
}

function drawValue(p: ModelParameter, u: number): number {
  const [lo, hi] = p.bounds;
  if (p.distribution === 'uniform') return lo + u * (hi - lo);
  return triangularInverseCDF(u, lo, p.baseline, hi);
}

/**
 * Evaluate a model over a Latin hypercube and rank-correlate the result.
 *
 * A sample that throws is counted, not silently dropped into the middle of the
 * distribution: a plant configuration the flowsheet cannot size is a real
 * finding about the design space, and burying it would flatter the model.
 */
export function evaluateModel<T>(
  parameters: ModelParameter[],
  metrics: ModelMetric<T>[],
  evaluate: (point: Record<string, number>) => T,
  opts: { n?: number; seed?: number; basePoint?: Record<string, number> } = {},
): ModelTable {
  const n = opts.n ?? 200;
  const rand = mulberry32(opts.seed ?? 20260812);
  const lhs = latinHypercube(n, parameters.length, rand);

  const samples: Record<string, number>[] = [];
  const metricRows: Record<string, number>[] = [];
  let failed = 0;

  for (let i = 0; i < n; i++) {
    const point: Record<string, number> = { ...(opts.basePoint ?? {}) };
    const drawn: Record<string, number> = {};
    parameters.forEach((p, d) => {
      const v = drawValue(p, lhs[i][d]);
      point[p.key] = v;
      drawn[p.key] = v;
    });
    let row: Record<string, number>;
    try {
      const result = evaluate(point);
      row = {};
      for (const m of metrics) {
        const v = m.get(result);
        if (!Number.isFinite(v)) throw new Error(`${m.key} is not finite`);
        row[m.key] = v;
      }
    } catch {
      failed += 1;
      continue;
    }
    samples.push(drawn);
    metricRows.push(row);
  }

  const rho: Record<string, Record<string, number>> = {};
  for (const p of parameters) {
    rho[p.key] = {};
    const xs = samples.map((s) => s[p.key]);
    for (const m of metrics) {
      rho[p.key][m.key] = spearmanRho(xs, metricRows.map((r) => r[m.key]));
    }
  }

  return { samples, metrics: metricRows, rho, failed };
}

/** Percentiles of one metric column, for the uncertainty band. */
export function percentiles(values: number[], ps: number[]): number[] {
  if (values.length === 0) return ps.map(() => NaN);
  const sorted = [...values].sort((a, b) => a - b);
  return ps.map((p) => {
    const idx = (sorted.length - 1) * p;
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    if (lo === hi) return sorted[lo];
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  });
}
