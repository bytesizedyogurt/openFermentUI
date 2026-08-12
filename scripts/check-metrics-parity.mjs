/**
 * Does the TypeScript metrics mirror still agree with the pinned scorer?
 *
 *   pnpm check:metrics   (→ tsx scripts/check-metrics-parity.mjs)
 *
 * `packages/assay` is the canonical home of P/R/F1 now — Inspect AI is Python
 * only, and scoring an extractor run is its job. `src/engine/metrics.ts` stays
 * because the validation screen recomputes live in the browser, and the moment
 * two implementations of the same arithmetic exist, one of them starts drifting.
 *
 * `fixtures/metrics.json` is the language-neutral pin captured in Phase 0. The
 * Python side replays it in `packages/assay/tests`; this replays the same cases
 * against the TypeScript. Both sides pinned to one fixture is what makes them a
 * mirror rather than two opinions.
 *
 * The inputs are SYNTHETIC and say so in the fixture, because RUN_OUTPUTS is
 * empty and stays empty until a real extractor has run. That is the point of
 * the screen this scores: no extractor has been run against this corpus, so
 * there is no precision to report. The synthetic cases exist to exercise every
 * branch of the counting rules — not to stand in for a result.
 */
import { readFileSync } from 'node:fs';

import { computeRunMetrics } from '../src/engine/metrics.ts';

const FIXTURE = new URL('../fixtures/metrics.json', import.meta.url);
const REL_TOL = 1e-12;

const fx = JSON.parse(readFileSync(FIXTURE, 'utf8'));
const failures = [];
let checked = 0;

function numEq(a, b) {
  if (Object.is(a, b)) return true;
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  return Math.abs(a - b) <= REL_TOL * Math.max(Math.abs(a), Math.abs(b));
}

/** Structural equality with numbers compared at REL_TOL wherever they appear. */
function deepEq(got, want) {
  if (typeof want === 'number' || typeof got === 'number') {
    return typeof got === 'number' && typeof want === 'number' && numEq(got, want);
  }
  if (want === null || got === null) return got === want;
  if (Array.isArray(want) || Array.isArray(got)) {
    // Array ORDER is checked, not just membership: perField is sorted by nGold
    // descending, and which field a reader sees first is a product decision.
    if (!Array.isArray(want) || !Array.isArray(got) || got.length !== want.length) return false;
    return want.every((w, i) => deepEq(got[i], w));
  }
  if (typeof want === 'object' || typeof got === 'object') {
    if (typeof got !== 'object' || typeof want !== 'object') return false;
    const kw = Object.keys(want).sort();
    const kg = Object.keys(got).sort();
    if (kw.length !== kg.length || kw.some((k, i) => k !== kg[i])) return false;
    return kw.every((k) => deepEq(got[k], want[k]));
  }
  return got === want;
}

/** First differing path, so a failure names the field rather than dumping two blobs. */
function firstDiff(got, want, path = '') {
  if (deepEq(got, want)) return '';
  if (got === null || want === null || typeof got !== 'object' || typeof want !== 'object') {
    return `${path}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`;
  }
  if (Array.isArray(want)) {
    if (!Array.isArray(got) || got.length !== want.length) {
      return `${path}: length ${want.length} expected, got ${Array.isArray(got) ? got.length : 'not an array'}`;
    }
    for (let i = 0; i < want.length; i += 1) {
      const d = firstDiff(got[i], want[i], `${path}[${i}]`);
      if (d) return d;
    }
    return '';
  }
  for (const k of [...new Set([...Object.keys(want), ...Object.keys(got)])].sort()) {
    if (!(k in got)) return `${path}.${k} is missing`;
    if (!(k in want)) return `${path}.${k} was not expected`;
    const d = firstDiff(got[k], want[k], `${path}.${k}`);
    if (d) return d;
  }
  return '';
}

console.log('openFerment metrics parity — fixtures/metrics.json replayed against src/engine/metrics.ts');
console.log('─────────────────────────────────────────────────────────────────────────────────────────');

const { syntheticGold, runs } = fx.inputs;
const byRun = new Map(runs.map((r) => [r.run, r]));

for (const c of fx.computeRunMetrics) {
  checked += 1;
  const run = byRun.get(c.extractorRun);
  if (!run) {
    failures.push(`${c.label}: fixture names extractorRun "${c.extractorRun}", which inputs.runs does not contain`);
    continue;
  }
  const got = computeRunMetrics(run, syntheticGold);
  const d = firstDiff(got, c.out);
  if (d) failures.push(`${c.label}: ${d}`);
}

if (fx.computeRunMetrics.length === 0) {
  failures.push('fixtures/metrics.json carries no computeRunMetrics cases — nothing was checked');
}

console.log(`  computeRunMetrics ${String(checked).padStart(6)} cases   ${failures.length === 0 ? '✓' : `✗ ${failures.length}`}`);

if (failures.length) {
  console.error('\n✗ the TypeScript mirror has drifted from the pinned scorer:');
  for (const f of failures) console.error(`  - ${f}`);
  console.error(
    '\nEither src/engine/metrics.ts is wrong, or it is right and packages/assay plus\n' +
      'fixtures/metrics.json must change with it. Python is canonical; change it there\n' +
      'first. Do not edit the fixture by hand.',
  );
  process.exit(1);
}

console.log(`\n✓ ${checked} cases replay identically. The TypeScript mirror matches the pin.\n`);
