/**
 * AnswerPlan drift guard (OF-BLD-007 §3, §10.4).
 *
 * The plan shape is defined twice — Pydantic in `core/openferment_core/models.py`,
 * TypeScript in `src/data/types.ts` — because the service validates it and the
 * browser renders it, and neither can import the other's definition.
 *
 * A shape that exists twice and is enforced once is a shape that is about to
 * disagree with itself, and the disagreement is silent: the service starts
 * returning a field the UI never reads, or the UI reads a field the service
 * stopped sending, and the plan renders with a hole in it. So the two are
 * compared field for field here, and a mismatch fails the build.
 *
 * Deliberately text-level and pure Node. Verify must run with no Python
 * toolchain and no service, so this parses rather than imports — which is
 * enough to catch the only failure that actually happens: somebody adds a
 * field to one side.
 */
import { readFileSync } from 'node:fs';

const errors = [];
const fail = (m) => errors.push(m);

const py = readFileSync('core/openferment_core/models.py', 'utf8');
const ts = readFileSync('src/data/types.ts', 'utf8');

/** Field names declared in a Pydantic model body. */
function pydanticFields(source, className) {
  const body = source.split(`class ${className}(BaseModel):`)[1]?.split('\nclass ')[0];
  if (body === undefined) {
    fail(`models.py: no class ${className}`);
    return null;
  }
  return new Set(
    [...body.matchAll(/^ {4}([a-zA-Z_][a-zA-Z0-9_]*)\s*:/gm)].map((m) => m[1]),
  );
}

/** Field names declared in a TS interface body, comments stripped. */
function tsFields(source, name) {
  const body = source.split(`export interface ${name} {`)[1]?.split('\n}')[0];
  if (body === undefined) {
    fail(`types.ts: no interface ${name}`);
    return null;
  }
  const clean = body.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  return new Set(
    [...clean.matchAll(/^\s{2}([a-zA-Z_][a-zA-Z0-9_]*)\??\s*:/gm)].map((m) => m[1]),
  );
}

const PAIRS = [
  ['Claim', 'Claim'],
  ['Usage', 'AnswerPlanUsage'],
  ['AnswerPlan', 'AnswerPlan'],
];

let compared = 0;
for (const [pyName, tsName] of PAIRS) {
  const a = pydanticFields(py, pyName);
  const b = tsFields(ts, tsName);
  if (!a || !b) continue;
  compared += a.size;
  for (const f of a) {
    if (!b.has(f)) fail(`${pyName}.${f} exists in models.py but not in types.ts ${tsName}`);
  }
  for (const f of b) {
    if (!a.has(f)) fail(`${tsName}.${f} exists in types.ts but not in models.py ${pyName}`);
  }
}

// ── the provenance vocabulary ──────────────────────────────────────────
// Both sides must know the same classes. A class the service can emit and the
// browser has no tick for renders as a blank, which reads as "no provenance"
// rather than as "a provenance this build does not understand".
const pyProv = new Set(
  [...(py.split('Provenance = Literal[')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g)].map(
    (m) => m[1],
  ),
);
// Comments are stripped first: the union is documented inline and one of those
// comments contains an apostrophe ("somebody else's paper"), which a naive
// quote match reads as the start of a member.
const tsProvSource = (ts.split('export type Provenance =')[1]?.split(';')[0] ?? '')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/\/\/.*$/gm, '');
const tsProv = new Set([...tsProvSource.matchAll(/'([^']+)'/g)].map((m) => m[1]));
for (const p of pyProv) if (!tsProv.has(p)) fail(`provenance '${p}' is in models.py but not types.ts`);
for (const p of tsProv) if (!pyProv.has(p)) fail(`provenance '${p}' is in types.ts but not models.py`);

// PROVENANCE_ORDER is the ranking `weakest_provenance` walks. A class missing
// from it would sort as unknown-and-weakest without anybody saying so.
const order = [
  ...(py.split('PROVENANCE_ORDER: list[str] = [')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g),
].map((m) => m[1]);
for (const p of pyProv) {
  if (!order.includes(p)) fail(`provenance '${p}' is in the union but missing from PROVENANCE_ORDER`);
}
if (order[0] !== 'measured') fail(`PROVENANCE_ORDER starts at '${order[0]}', expected 'measured' as the strongest`);
if (order.indexOf('gold') <= order.indexOf('measured')) fail('PROVENANCE_ORDER: measured must outrank gold');
if (order.indexOf('industry-estimate') < order.indexOf('unverified')) {
  fail('PROVENANCE_ORDER: an industry estimate must not outrank an unverified extraction');
}

console.log('\nopenFerment AnswerPlan shape check');
console.log('──────────────────────────────────');
console.log(`  fields        ${compared} compared across ${PAIRS.length} types, Python ↔ TypeScript`);
console.log(`  provenance    ${pyProv.size} classes agree, ranked ${order.length} deep`);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\n✓ The plan shape is the same on both sides.');
