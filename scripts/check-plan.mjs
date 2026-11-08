/**
 * The provenance ranking (OF-BLD-014 §3.1; ADR-011, and ADR-007's note of alpha 2.2 E.15).
 *
 * One ranking orders the provenance classes on both sides: `PROVENANCE_ORDER` in
 * `core/openferment_core/models.py`, which `weakest_provenance` walks, and
 * `PROVENANCE_RANK` in `src/store.ts`, the browser's copy of it. A value the
 * service calls weaker must never draw as stronger, so this check holds three
 * things, and any difference fails the build:
 *
 *   - models.py's `Provenance` union and `PROVENANCE_ORDER` name the same classes;
 *   - the order starts at `measured`, ranks `measured` above `gold`, and ranks an
 *     unverified extraction at least as high as an industry estimate;
 *   - `PROVENANCE_RANK` gives each class a rank of its own, in the order's order,
 *     member for member.
 *
 * The browser's union is generated from models.py into `src/api/types.gen.ts`
 * (`pnpm gen:api`, held by `gen:api --check`), and `PROVENANCE_RANK` is declared
 * as `Record<Provenance, number>` over it, so `pnpm typecheck` holds the rank's
 * keys to the union. The command keeps the name it had while it also held the
 * hand-kept browser types, the AnswerPlan's first among them, to models.py field
 * for field; those pairs retired with the hand-kept file at alpha 2.2 E.15.
 *
 * Text-level and pure Node: verify runs it with no Python toolchain and no
 * service, so it reads the two declarations from the files as text.
 */
import { readFileSync } from 'node:fs';

const errors = [];
const fail = (m) => errors.push(m);

const py = readFileSync('core/openferment_core/models.py', 'utf8');

// ── the service's classes and their order ───────────────────────────────
const pyProv = new Set(
  [...(py.split('Provenance = Literal[')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g)].map(
    (m) => m[1],
  ),
);
if (pyProv.size === 0) fail('models.py: no Provenance union');

// PROVENANCE_ORDER is the ranking `weakest_provenance` walks. A class missing
// from it would sort as unknown-and-weakest without anybody saying so, and a
// class only the order names is one the service never emits.
const order = [
  ...(py.split('PROVENANCE_ORDER: list[str] = [')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g),
].map((m) => m[1]);
if (order.length === 0) fail('models.py: no PROVENANCE_ORDER');
for (const p of pyProv) {
  if (!order.includes(p)) fail(`provenance '${p}' is in the union but missing from PROVENANCE_ORDER`);
}
for (const p of order) {
  if (!pyProv.has(p)) fail(`PROVENANCE_ORDER names '${p}', a class the union lacks`);
}
if (new Set(order).size !== order.length) fail(`PROVENANCE_ORDER names a class twice: ${order.join(', ')}`);
if (order[0] !== 'measured') fail(`PROVENANCE_ORDER starts at '${order[0]}', expected 'measured' as the strongest`);
if (order.indexOf('gold') <= order.indexOf('measured')) fail('PROVENANCE_ORDER: measured must outrank gold');
if (order.indexOf('industry-estimate') < order.indexOf('unverified')) {
  fail('PROVENANCE_ORDER: an industry estimate must not outrank an unverified extraction');
}

// OF-BLD-014 §3.1, E.4 — one ranking. PROVENANCE_RANK in src/store.ts is the
// browser's copy; it must hold the same members in the same order, so a value
// the service calls weaker never draws as stronger. Membership alone let the
// two disagree about `user` and `unverified` until §3.1.
const store = readFileSync('src/store.ts', 'utf8');
const rankBody = store.split('export const PROVENANCE_RANK: Record<Provenance, number> = {')[1]?.split('};')[0];
if (rankBody === undefined) {
  fail('src/store.ts: no PROVENANCE_RANK');
} else {
  const rank = [...rankBody.replace(/\/\/.*$/gm, '').matchAll(/^\s*'?([a-z-]+)'?\s*:\s*(\d+)\s*,?\s*$/gm)]
    .map((m) => [m[1], Number(m[2])])
    .sort((x, y) => x[1] - y[1]);
  const tsOrder = rank.map(([p]) => p);
  const ranks = rank.map(([, n]) => n);
  if (new Set(ranks).size !== ranks.length) fail(`PROVENANCE_RANK gives two classes one rank: ${ranks.join(', ')}`);
  if (tsOrder.join(' ') !== order.join(' ')) {
    fail(`PROVENANCE_RANK orders ${tsOrder.join(' > ')}; PROVENANCE_ORDER orders ${order.join(' > ')}`);
  }
}

console.log('\nopenFerment provenance ranking check');
console.log('────────────────────────────────────');
console.log(`  provenance    ${pyProv.size} classes in models.py, ranked ${order.length} deep in one order on both sides`);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\n✓ PROVENANCE_RANK holds PROVENANCE_ORDER, member for member.');
