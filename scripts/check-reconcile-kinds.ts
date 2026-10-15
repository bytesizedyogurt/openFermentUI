/**
 * The three prediction kinds, held and missed (OF-BLD-014 §9.1). One
 * scenario per kind through `computeDeltas` and `suggestOutcome`, the code
 * the deposition page draws from. Run by `pnpm test:reconcile` before the
 * browser loop in check-reconcile.mjs.
 */
import { computeDeltas, suggestOutcome } from '../src/engine/reconcile';
import { HIT_RATE_MIN_TESTED, ledgerCounts } from '../src/engine/ledger';
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

// §9.3 — the ledger's counts: a locked runbook's predictions, tested by the
// latest conclusive run; an inconclusive run counts as a run and tests nothing.
{
  const rb = { id: 'rb', title: 'r', lockedAt: '2026-10-01T00:00:00Z', predictions: [point, { ...interval, id: 'pi' }, { ...bound, id: 'pb' }] } as unknown as Runbook;
  const open = { id: 'rb-open', title: 'o', lockedAt: null, predictions: [point] } as unknown as Runbook;
  const rec = (id: string, at: string, outcome: string, deltas: [string, number][]) =>
    ({ id, runbookId: 'rb', reconciliation: { at, outcome, note: '', deltas: deltas.map(([predictionId, observed]) => ({ predictionId, observed, predicted: 0, unit: 'u', pctDelta: 0 })) } }) as unknown as Deposition;
  const deps = [
    rec('d1', '2026-10-02', 'refuted', [['p', 5.1]]),
    rec('d2', '2026-10-03', 'confirmed', [['p', 8.2]]),
    rec('d3', '2026-10-04', 'inconclusive', [['p', 1]]),
  ];
  const c = ledgerCounts([rb, open], deps);
  check('the ledger counts locked, tested, held, missed and inconclusive runs',
    c.locked === 3 && c.tested === 1 && c.held === 1 && c.missed === 0 && c.inconclusiveRuns === 1 && c.hitRate === null, JSON.stringify(c));
  const many = Array.from({ length: HIT_RATE_MIN_TESTED }, (_, i) => ({ ...rb, id: `rb${i}`, predictions: [point] }) as Runbook);
  const manyDeps = many.map((r, i) => ({ ...rec(`m${i}`, '2026-10-05', 'refuted', [['p', i === 0 ? 8 : 1]]), runbookId: r.id }) as Deposition);
  const c5 = ledgerCounts(many, manyDeps);
  check(`a hit rate appears at ${HIT_RATE_MIN_TESTED} tested`, c5.tested === HIT_RATE_MIN_TESTED && c5.hitRate === 1 / HIT_RATE_MIN_TESTED, JSON.stringify(c5));
}

console.log(fails === 0 ? '\nTHE THREE KINDS RECONCILE' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
