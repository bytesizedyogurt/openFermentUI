/**
 * Run the Python test suites — the CANONICAL side of every parity gate.
 *
 *   pnpm check:python   (→ node scripts/check-python.mjs)
 *
 * Why this exists. `check:units`, `check:protocol` and `check:metrics` replay a
 * fixture against the TypeScript MIRROR. That proves the mirror still matches
 * the pin. It proves nothing whatever about the Python, which is the canon —
 * and an audit demonstrated the consequence: mutating `scale.py`, `metrics.py`
 * or `diff.py` left `pnpm verify` green while pytest went red. A gate that
 * watches one of two implementations is half a gate, and CLAUDE.md invariant 1
 * names `pnpm verify` as THE regression harness for this migration.
 *
 * Both sides replaying the same pinned fixture is what makes them a mirror
 * rather than two opinions. This is the second side.
 *
 * It needs pytest. `pnpm verify` already needs python3 for `check:corpus` and
 * `check:aggregation`, so this deepens an existing dependency rather than
 * adding a new kind of one — but it is a real requirement and it is stated
 * here rather than discovered from a stack trace.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const PACKAGES = ['packages/core', 'packages/assay'];

console.log('openFerment Python suites — the canonical side of the parity gates');
console.log('──────────────────────────────────────────────────────────────────');

const probe = spawnSync('python3', ['-m', 'pytest', '--version'], { encoding: 'utf8' });
if (probe.status !== 0) {
  console.error('✗ pytest is not available to python3, so the canonical implementations');
  console.error('  went unchecked. Install it (pip install pytest) — do not skip this step:');
  console.error('  the TypeScript gates cannot see a change to the Python at all.');
  process.exit(1);
}

let failed = 0;
for (const pkg of PACKAGES) {
  const cwd = join(ROOT, pkg);
  if (!existsSync(cwd)) {
    console.error(`✗ ${pkg} is missing`);
    failed += 1;
    continue;
  }
  const run = spawnSync('python3', ['-m', 'pytest', '-q'], { cwd, encoding: 'utf8' });
  const tail = (run.stdout ?? '').trim().split('\n').filter(Boolean).pop() ?? '';
  if (run.status === 0) {
    console.log(`  ${pkg.padEnd(16)} ✓  ${tail}`);
  } else {
    failed += 1;
    console.log(`  ${pkg.padEnd(16)} ✗  ${tail}`);
    console.error(`\n${run.stdout ?? ''}${run.stderr ?? ''}`);
  }
}

if (failed) {
  console.error(`\n✗ ${failed} Python suite(s) failed. These are the canonical implementations —`);
  console.error('  the TypeScript mirrors can be green while these are wrong, which is exactly');
  console.error('  the situation this check exists to make impossible.');
  process.exit(1);
}
console.log('\n✓ the canonical Python implementations pass their own suites.\n');
