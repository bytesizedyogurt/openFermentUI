// Multilinear interpolation over precomputed sweep grids (OF-DES-001 §17).
// Grids are flattened row-major over dims in declaration order.

export interface Grid {
  dims: { key: string; values: number[] }[];
  /** flat array, length = product of dim lengths */
  data: Float64Array | number[];
}

export function gridIndex(dims: { values: number[] }[], idx: number[]): number {
  let flat = 0;
  for (let d = 0; d < dims.length; d++) {
    flat = flat * dims[d].values.length + idx[d];
  }
  return flat;
}

/** Clamp a point to grid bounds; returns [clampedPoint, wasClamped]. */
export function clampPoint(
  dims: { key: string; values: number[] }[],
  point: Record<string, number>,
): [Record<string, number>, boolean] {
  const out: Record<string, number> = {};
  let clamped = false;
  for (const d of dims) {
    const lo = d.values[0];
    const hi = d.values[d.values.length - 1];
    const v = point[d.key] ?? lo;
    const c = Math.min(hi, Math.max(lo, v));
    if (c !== v) clamped = true;
    out[d.key] = c;
  }
  return [out, clamped];
}

/** Multilinear interpolation of `grid` at `point` (clamped to bounds). */
export function interpolate(grid: Grid, point: Record<string, number>): number {
  const { dims, data } = grid;
  const [p] = clampPoint(dims, point);
  // per-dim lower index + fraction
  const lower: number[] = [];
  const frac: number[] = [];
  for (const d of dims) {
    const v = p[d.key];
    const vs = d.values;
    let i = vs.length - 2;
    for (let j = 0; j < vs.length - 1; j++) {
      if (v <= vs[j + 1]) {
        i = j;
        break;
      }
    }
    lower.push(i);
    const span = vs[i + 1] - vs[i];
    frac.push(span === 0 ? 0 : (v - vs[i]) / span);
  }
  // sum over 2^n corners
  const n = dims.length;
  let acc = 0;
  for (let corner = 0; corner < 1 << n; corner++) {
    let w = 1;
    const idx: number[] = [];
    for (let d = 0; d < n; d++) {
      const hi = (corner >> d) & 1;
      w *= hi ? frac[d] : 1 - frac[d];
      idx.push(lower[d] + hi);
    }
    if (w === 0) continue;
    acc += w * (data as number[])[gridIndex(dims, idx)];
  }
  return acc;
}

/** 1-D slice of the grid along `axisKey`, other dims held at `point`. */
export function sweepLine(
  grid: Grid,
  axisKey: string,
  point: Record<string, number>,
  samples = 60,
): { x: number; y: number }[] {
  const dim = grid.dims.find((d) => d.key === axisKey);
  if (!dim) return [];
  const lo = dim.values[0];
  const hi = dim.values[dim.values.length - 1];
  const out: { x: number; y: number }[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = lo + ((hi - lo) * i) / samples;
    out.push({ x, y: interpolate(grid, { ...point, [axisKey]: x }) });
  }
  return out;
}
