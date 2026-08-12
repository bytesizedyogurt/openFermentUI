// Monte Carlo over a whole plant.
//
// Each sample is a complete rebuild: new parameter draw, new equipment sizes,
// new capital, new cash flow, new solved price. That is expensive and it is the
// point — a sensitivity analysis that perturbs a cost coefficient instead of
// re-sizing the plant cannot see that halving the titer doubles the fermenter
// count, and the fermenter count is where the money is.
import { evaluatePlant } from '@/engine/plant';
import type { FlowsheetSpec } from '@/sim/flowsheets/spec';
import { evaluateModel, percentiles, type ModelParameter } from '@/engine/biosteam/model';
import type { FieldId } from '@/data/types';

export interface SpearmanRow {
  key: string;
  name: string;
  rho: number;
  field?: FieldId;
}

export interface PlantUncertainty {
  n: number;
  requested: number;
  failed: number;
  seed: number;
  values: number[];
  percentiles: { p5: number; p25: number; p50: number; p75: number; p95: number };
  histogram: { x: number; n: number }[];
  spearman: SpearmanRow[];
}

function histogram(values: number[], bins = 24): { x: number; n: number }[] {
  if (values.length === 0) return [];
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  if (!(hi > lo)) return [{ x: lo, n: values.length }];
  const width = (hi - lo) / bins;
  const counts = new Array<number>(bins).fill(0);
  for (const v of values) {
    const i = Math.min(bins - 1, Math.floor((v - lo) / width));
    counts[i] += 1;
  }
  return counts.map((n, i) => ({ x: lo + width * (i + 0.5), n }));
}

export function runPlantUncertainty(
  spec: FlowsheetSpec,
  basePoint: Record<string, number>,
  opts: { n?: number; seed?: number } = {},
): PlantUncertainty {
  const n = opts.n ?? 200;
  const seed = opts.seed ?? 20260812;

  const parameters: ModelParameter[] = spec.parameters.map((p) => ({
    key: p.key,
    name: p.label,
    units: p.unit,
    baseline: basePoint[p.key] ?? p.baseline,
    bounds: p.bounds,
    distribution: p.distribution,
  }));

  const table = evaluateModel(
    parameters,
    [{ key: 'msp', name: 'Minimum selling price', units: 'USD/kg', get: (r: { msp: number }) => r.msp }],
    (point) => evaluatePlant(spec, point),
    { n, seed, basePoint },
  );

  const values = table.metrics.map((m) => m.msp);
  const [p5, p25, p50, p75, p95] = percentiles(values, [0.05, 0.25, 0.5, 0.75, 0.95]);

  const spearman: SpearmanRow[] = spec.parameters
    .map((p) => ({
      key: p.key,
      name: p.label,
      rho: table.rho[p.key]?.msp ?? NaN,
      field: p.field,
    }))
    .filter((r) => Number.isFinite(r.rho))
    .sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho));

  return {
    n: values.length,
    requested: n,
    failed: table.failed,
    seed,
    values,
    percentiles: { p5, p25, p50, p75, p95 },
    histogram: histogram(values),
    spearman,
  };
}
