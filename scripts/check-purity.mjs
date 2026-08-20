/**
 * Is src/engine/ still pure?
 *
 *   pnpm check:purity   (→ node scripts/check-purity.mjs)
 *
 * The restructuring brief's Phase 2 rule: engine modules import nothing from
 * the store, nothing from the seed data at runtime, and no React. Purity is
 * what makes the engine reusable and testable without dragging the app along —
 * and it is a property that erodes one convenient import at a time, so it is
 * enforced here rather than remembered.
 *
 * Type-only imports are allowed: `import type { Paper } from '@/data/types'`
 * is erased at compile time and couples nothing at runtime — and the brief's
 * own Phase 3 exit condition makes the same distinction.
 *
 * Three modules import `@/data/ontology` at runtime today. They are carried as
 * an explicit allowlist below, each with the reason, so the debt is a ledger
 * rather than a fog: a NEW violation fails this check, and a resolved entry
 * must be pruned (a stale allowlist is a gate quietly widened, so that fails
 * too).
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const ENGINE = join(ROOT, 'src', 'engine');

/** Runtime-forbidden import targets. */
const FORBIDDEN = [
  { test: (s) => s === '@/store', label: '@/store — the engine must not read app state' },
  { test: (s) => /^react($|\/)/.test(s) || /^react-dom($|\/)/.test(s), label: 'react — the engine renders nothing' },
  { test: (s) => /^zustand($|\/)/.test(s), label: 'zustand — the store, by another door' },
  { test: (s) => s.startsWith('@/data/'), label: "@/data/* at runtime — seed data flows INTO the engine as parameters" },
];

/**
 * (file, specifier) pairs that violate the rule today, each with why it is
 * tolerated. Everything here predates the gate. The remedy the brief names —
 * "extract the offending dependency into a parameter" — is the right one, and
 * it touches every caller of these three, so it is recorded rather than done.
 */
const ALLOWLIST = [
  ['src/engine/designs.ts', '@/data/ontology', 'ONTOLOGY_BY_ID for canonical units when assembling derived designs'],
  ['src/engine/balance.ts', '@/data/ontology', 'ONTOLOGY_BY_ID for the unit each balance check is stated in'],
  ['src/engine/posterior.ts', '@/data/ontology', 'ONTOLOGY_BY_ID for the canonical unit a parameter view converts to'],
];

function* tsFiles(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* tsFiles(p);
    else if (name.endsWith('.ts')) yield p;
  }
}

const violations = [];
const matchedAllowlist = new Set();
let files = 0;
let imports = 0;

for (const file of tsFiles(ENGINE)) {
  files += 1;
  const rel = relative(ROOT, file);
  const src = readFileSync(file, 'utf8');
  for (const m of src.matchAll(/^import\s+(type\s+)?(?:[^'"]*?from\s+)?['"]([^'"]+)['"]/gm)) {
    imports += 1;
    const typeOnly = Boolean(m[1]);
    const spec = m[2];
    if (typeOnly) continue;
    const hit = FORBIDDEN.find((f) => f.test(spec));
    if (!hit) continue;
    const allowed = ALLOWLIST.find(([f, s]) => f === rel && s === spec);
    if (allowed) {
      matchedAllowlist.add(allowed);
      continue;
    }
    const line = src.slice(0, m.index).split('\n').length;
    violations.push(`${rel}:${line} imports '${spec}' — ${hit.label}`);
  }
}

const stale = ALLOWLIST.filter((e) => !matchedAllowlist.has(e));

console.log('openFerment engine purity');
console.log('─────────────────────────');
console.log(`  ${files} modules scanned · ${imports} import statements`);
console.log(`  allowlisted debt: ${matchedAllowlist.size} of ${ALLOWLIST.length} entries in use`);

if (violations.length) {
  console.error(`\n✗ ${violations.length} runtime import(s) violate engine purity:`);
  for (const v of violations) console.error(`  - ${v}`);
  console.error('\n  Pass the value in as a parameter instead. The engine is reusable only');
  console.error('  for as long as it does not reach out for app state or seed data.');
  process.exit(1);
}
if (stale.length) {
  console.error(`\n✗ ${stale.length} allowlist entr${stale.length === 1 ? 'y' : 'ies'} no longer match anything:`);
  for (const [f, s] of stale) console.error(`  - ${f} ← '${s}'`);
  console.error('\n  The debt was paid — prune the entry. A stale allowlist is a gate');
  console.error('  quietly widened.');
  process.exit(1);
}
console.log('\n✓ the engine imports no store, no React, and no seed data at runtime.\n');
