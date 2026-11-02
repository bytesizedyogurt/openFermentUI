/**
 * Lock digests written by the browser's own code (`src/engine/lock.ts`), for
 * the service's port (`core/openferment_core/runbook_lock.py`) to be held to:
 * a runbook the service locks must read as intact on the runbook's page.
 *
 *   pnpm export:lock-fixtures   → core/tests/fixtures/lock-digests.json
 *
 * The cases cover what the canonical form touches: integral and fractional
 * values, the exponent forms JavaScript writes, negative zero, a point with
 * no optional field and one with each, an absent and a null prediction id,
 * quotes, backslashes, control characters, letters beyond Latin and
 * characters beyond the Basic Multilingual Plane.
 */
import { writeFileSync } from 'node:fs';
import type { Measure, Prediction } from '../src/data/types';
import { runbookLockHash } from '../src/engine/lock';

const point = (id: string, value: number, extra: Partial<Prediction> = {}): Prediction => ({
  id, label: `Final titre ${id}`, value, unit: 'g L⁻¹', confidence: 'medium', basis: 'a named person’s value', ...extra,
});
const measure = (id: string, predictionId: string | null | undefined): Measure =>
  ({ id, label: `Titre ${id}`, unit: 'g L⁻¹', timepoint: 'harvest', ...(predictionId === undefined ? {} : { predictionId }) }) as Measure;

const cases: { name: string; predictions: Prediction[]; schema: Measure[] }[] = [
  { name: 'one point, its measure', predictions: [point('p1', 3)], schema: [measure('m1', 'p1')] },
  { name: 'fractions', predictions: [point('p1', 0.1), point('p2', 2.5), point('p3', 12345678.9)], schema: [] },
  { name: 'small and large', predictions: [point('p1', 1e-7), point('p2', 0.000001), point('p3', 1.5e-6), point('p4', 1e16),
    point('p5', 1e21), point('p6', 123456789012345680000), point('p7', -0.0004)], schema: [] },
  { name: 'negative zero', predictions: [point('p1', -0)], schema: [] },
  { name: 'every optional field', predictions: [point('p1', 0.6588136420, {
    kind: 'interval', interval: { low: 0.61, high: 0.71 }, artifactId: 'eab962e1fd3d4b31', recordIds: ['r-1', 'r-2'] })],
  schema: [measure('m1', 'p1')] },
  { name: 'a bound, nothing more', predictions: [point('p1', 0.48, { kind: 'bound' })], schema: [] },
  { name: 'an artifact alone', predictions: [point('p1', 1, { artifactId: '00000000000000aa' })], schema: [] },
  { name: 'prediction ids absent and null', predictions: [point('p1', 1)], schema: [measure('m1', undefined), measure('m2', null)] },
  { name: 'words to escape', predictions: [point('p1', 1, { label: 'a "quoted" \\ back\nslash\t\u0001 word', basis: 'Ethanol – 99.5 % (w/w); µmax' })],
    schema: [] },
  { name: 'beyond the basic plane', predictions: [point('p1', 1, { label: 'Titre 🧪 of 発酵 ethanol' })], schema: [] },
];

const out = cases.map((c) => ({ ...c, digest: runbookLockHash(c.predictions, c.schema) }));
writeFileSync(
  'core/tests/fixtures/lock-digests.json',
  JSON.stringify({ _fixture: 'TEST FIXTURE: lock digests from src/engine/lock.ts, written by `pnpm export:lock-fixtures`.', cases: out }, null, 2) + '\n',
);
console.log(`✓ core/tests/fixtures/lock-digests.json — ${out.length} digests from the browser's lock`);
