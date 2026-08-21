// Order statistics. Pool-neutral, dependency-free.
//
// There were four implementations of the median in this repository: the
// corpus aggregate in `engine/posterior.ts` (as `quantile(sorted, 0.5)`), one
// in `lib/demo.ts` for the demo pool, and hand-rolled copies inside
// `screens/Review.tsx` and `screens/StrainPage.tsx`. They agreed — but only by
// coincidence, and the aggregate one is named and versioned
// (`median-of-primary-v1`), which means a divergence would be a reported
// number quietly disagreeing with itself across two screens.
//
// This file has no imports on purpose. It is reachable from `engine/`, which
// `check:purity` forbids from importing seed data, and from both object pools,
// which must not import each other.
//
// Every function takes an UNSORTED array and sorts a copy. The previous
// `quantile` took a pre-sorted one and silently returned nonsense if handed an
// unsorted array — an easy call site to get wrong, and impossible to see in
// the output.

/**
 * The q-quantile by linear interpolation between order statistics.
 *
 * This is the R-7 / Excel `PERCENTILE` convention: for an even-length array
 * the median is the mean of the two middle values, which is what the three
 * hand-rolled copies did.
 */
export function quantile(xs: number[], q: number): number {
  if (xs.length === 0) return NaN;
  const s = [...xs].sort((a, b) => a - b);
  if (s.length === 1) return s[0];
  const pos = (s.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return s[lo];
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}

/** `null` for an empty set rather than NaN — the caller has nothing to report. */
export function median(xs: number[]): number | null {
  return xs.length ? quantile(xs, 0.5) : null;
}

/**
 * The interquartile box. `null` below four values: a q1/q3 drawn from three
 * points is a picture of the sample size, not of the spread.
 */
export function quartiles(xs: number[]): { q1: number; q3: number } | null {
  if (xs.length < 4) return null;
  return { q1: quantile(xs, 0.25), q3: quantile(xs, 0.75) };
}

/**
 * The element-wise median across several equal-length series.
 *
 * A run's baseline is the median of its comparison runs at each tick, not the
 * median of their means — an excursion in one run must not move the baseline
 * everywhere. `data/demo/runs.ts` had written this out inline while the
 * exported version sat unused two modules away.
 */
export function medianSeries(rows: number[][]): number[] {
  if (!rows.length) return [];
  return rows[0].map((_, i) => quantile(rows.map((r) => r[i]), 0.5));
}
