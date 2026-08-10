// Build frozen ResultGrids from authored cost models (OF-DES-001 §17.1).
// In production these grids become caches in front of a BioSTEAM worker;
// the Scenario/ResultGrid contract does not change (§17.4).
import type { CostModel, CostLine, ResultGrid } from '@/data/types';
import { interpolate, clampPoint, type Grid } from './interp';

export const COST_LINES: CostLine[] = [
  'capex',
  'media',
  'utilities',
  'labor',
  'downstream',
  'other',
];

export const COST_LINE_LABEL: Record<CostLine, string> = {
  capex: 'CAPEX (annualized)',
  media: 'Media & feedstock',
  utilities: 'Utilities',
  labor: 'Labor',
  downstream: 'Downstream processing',
  other: 'Other fixed',
};

export function buildGrid(model: CostModel): ResultGrid {
  const dims = model.dims.map((d) => ({ key: d.key, values: d.values }));
  const total = dims.reduce((n, d) => n * d.values.length, 1);
  const msp = new Float64Array(total);
  const costLines = Object.fromEntries(
    COST_LINES.map((l) => [l, new Float64Array(total)]),
  ) as Record<CostLine, Float64Array>;

  const idx = new Array(dims.length).fill(0);
  for (let flat = 0; flat < total; flat++) {
    // decode flat -> per-dim index (row-major, matching interp.gridIndex)
    let rem = flat;
    for (let d = dims.length - 1; d >= 0; d--) {
      idx[d] = rem % dims[d].values.length;
      rem = Math.floor(rem / dims[d].values.length);
    }
    const point: Record<string, number> = {};
    for (let d = 0; d < dims.length; d++) point[dims[d].key] = dims[d].values[idx[d]];
    const lines = model.evaluate(point);
    let sum = 0;
    for (const l of COST_LINES) {
      costLines[l][flat] = lines[l];
      sum += lines[l];
    }
    msp[flat] = sum;
  }

  return { modelId: model.modelId, dims, msp, costLines, sensitivity: model.sensitivity };
}

export interface EvaluatedPoint {
  msp: number;
  costLines: Record<CostLine, number>;
  clamped: boolean;
}

/** Interpolate the grid at an arbitrary point; clamps to modeled bounds. */
export function evaluateGrid(
  grid: ResultGrid,
  point: Record<string, number>,
): EvaluatedPoint {
  const [p, clamped] = clampPoint(grid.dims, point);
  const asGrid = (data: Float64Array): Grid => ({ dims: grid.dims, data: data as unknown as number[] });
  const costLines = Object.fromEntries(
    COST_LINES.map((l) => [l, interpolate(asGrid(grid.costLines[l]), p)]),
  ) as Record<CostLine, number>;
  // Sum the interpolated lines so the waterfall and the headline can never
  // disagree, even by float noise (§8.13 acceptance).
  const msp = COST_LINES.reduce((s, l) => s + costLines[l], 0);
  return { msp, costLines, clamped };
}

/** MSP along one axis with other dims held fixed (sweep chart). */
export function mspSweep(
  grid: ResultGrid,
  axisKey: string,
  point: Record<string, number>,
  samples = 48,
): { x: number; msp: number }[] {
  const dim = grid.dims.find((d) => d.key === axisKey);
  if (!dim) return [];
  const lo = dim.values[0];
  const hi = dim.values[dim.values.length - 1];
  const out: { x: number; msp: number }[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = lo + ((hi - lo) * i) / samples;
    out.push({ x, msp: evaluateGrid(grid, { ...point, [axisKey]: x }).msp });
  }
  return out;
}
