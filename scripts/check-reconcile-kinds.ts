/**
 * The three prediction kinds, held and missed (OF-BLD-014 §9.1). One
 * scenario per kind through `computeDeltas` and `suggestOutcome`, the code
 * the deposition page draws from. Run by `pnpm test:reconcile` before the
 * browser loop in check-reconcile.mjs.
 */
import { computeDeltas, suggestOutcome } from '../src/engine/reconcile';
import type { Deposition, Prediction, Runbook } from '../src/data/types';

let fails = 0;
const check = (l: string, ok: boolean, x = '') => {
  console.log((ok ? '✓' : '✗') + ' ' + l + (x ? '  ' + x : ''));
  if (!ok) fails++;
};

function scenario(p: Prediction, observed: number) {
  const rb = { predictions: [p], measurementSchema: [{ id: 'm', label: p.label, unit: p.unit, timepoint: 'harvest', predictionId: p.id }] } as unknown as Runbook;
  const dep = { entries: [{ measureId: 'm', value: observed, unit: p.unit, confirmed: true }] } as unknown as Deposition;
  const [d] = computeDeltas(dep, rb);
  return { d, outcome: suggestOutcome([d], 0).outcome };
}

const base = { id: 'p', label: 'Final titre', unit: 'g L-1', confidence: 'medium' as const, basis: 'test' };
const point = { ...base, value: 8 };
const interval = { ...base, value: 6, kind: 'interval' as const, interval: { low: 4, high: 9 } };
const bound = { ...base, value: 0.59, kind: 'bound' as const, unit: 'g g-1' };

const cases: [string, Prediction, number, boolean, number][] = [
  ['a point held within ten percent', point, 8.5, true, 6.25],
  ['a point missed outside ten percent', point, 5.1, false, -36.25],
  ['an interval held inside its ends', interval, 8.9, true, 0],
  ['an interval missed below its low', interval, 3, false, -25],
  ['an interval missed above its high, measured from that edge', interval, 9.9, false, 10],
  ['a bound held at or below its value', bound, 0.59, true, 0],
  ['a bound missed above it', bound, 0.649, false, 10],
];
for (const [label, p, obs, held, delta] of cases) {
  const { d, outcome } = scenario(p, obs);
  check(label, d.held === held && Math.abs(d.pctDelta - delta) < 1e-9 && outcome === (held ? 'confirmed' : 'refuted'), `held ${d.held}, delta ${d.pctDelta.toFixed(2)}, ${outcome}`);
}

console.log(fails === 0 ? '\nTHE THREE KINDS RECONCILE' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
