// Rank statistics, standing in for scipy.
//
// bioSTEAM ranks a Monte Carlo with `scipy.stats.spearmanr`. Spearman rather
// than Pearson is not a detail: an MSP that goes as 1/titer is a perfectly
// monotone relationship and a badly non-linear one, and Pearson would report it
// as weak. Ranking first measures "does this parameter reliably move the answer
// in one direction", which is the question a tornado chart is actually asking.

/**
 * Fractional ranks, averaging ties.
 *
 * Ties matter here because a parameter clamped at a bound produces many
 * identical values, and giving them arbitrary distinct ranks would manufacture
 * a correlation out of the sort order.
 */
export function rank(values: number[]): number[] {
  const idx = values.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
  const out = new Array<number>(values.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j += 1;
    const avg = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) out[idx[k][1]] = avg;
    i = j + 1;
  }
  return out;
}

/** Pearson correlation. */
export function pearsonR(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 2) return NaN;
  let mx = 0;
  let my = 0;
  for (let i = 0; i < n; i++) {
    mx += x[i];
    my += y[i];
  }
  mx /= n;
  my /= n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - mx;
    const dy = y[i] - my;
    sxy += dx * dy;
    sxx += dx * dx;
    syy += dy * dy;
  }
  const denom = Math.sqrt(sxx * syy);
  return denom === 0 ? 0 : sxy / denom;
}

/** Spearman's ρ: Pearson on the ranks. */
export function spearmanRho(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 3) return NaN;
  return pearsonR(rank(x.slice(0, n)), rank(y.slice(0, n)));
}
