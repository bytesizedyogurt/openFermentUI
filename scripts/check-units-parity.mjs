/**
 * Does the TypeScript unit engine still agree with the canon?
 *
 * `fixtures/units.json` is the language-neutral pin of what `src/engine/units.ts`
 * did at Phase 0 of the Python migration, and it is what the Python port is
 * being written against. Once the Python owns the engine, this file is what
 * keeps the TypeScript honest: it replays every captured case back through the
 * TypeScript and fails on any disagreement. A mirror that has quietly drifted is
 * worse than no mirror, because both sides still answer confidently.
 *
 *   pnpm check:units      →  tsx scripts/check-units-parity.mjs
 *
 * It is a .mjs like the other checkers, but it imports a .ts module directly.
 * That resolves because tsx's loader transpiles `../src/engine/units.ts` on the
 * fly — the same mechanism `check:biosteam` already relies on. (Node ≥ 22.18
 * strips the types natively and runs this under plain `node` too, but tsx is
 * what the repo pins, so tsx is what the script line names.)
 *
 * Nothing here is a new expectation. Every expected value in this file comes
 * out of the fixture; the script contains no remembered numbers of its own.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  UNIT_TABLE,
  UNIT_ALIASES,
  SI_UNIT_BY_FAMILY,
  REFUSAL_PAIRS,
  asNumber,
  convert,
  explainRefusal,
  fmt,
  normalizeUnit,
  parseQuantity,
  quantityEquals,
  roundToPrecision,
  sameFamily,
  toSI,
  unitFamily,
} from '../src/engine/units.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const FIXTURE = join(ROOT, 'fixtures', 'units.json');

/** Floats compare relatively, never exactly: the Python side of this pin will
 *  do the same arithmetic in a different order. 1e-12 is tight enough that a
 *  transposed factor cannot hide and loose enough to survive reassociation. */
const REL_TOL = 1e-12;

/** The twelve collections that must be present. A fixture missing one, or
 *  carrying one this script does not replay, is itself a drift. */
const COLLECTIONS = [
  'normalizeUnit',
  'unitFamily',
  'sameFamily',
  'convert',
  'convertCrossFamily',
  'toSI',
  'explainRefusal',
  'parseQuantity',
  'asNumber',
  'fmt',
  'roundToPrecision',
  'quantityEquals',
];

const fixture = JSON.parse(readFileSync(FIXTURE, 'utf8'));

const failures = [];
const tally = [];

function record(collection, input, expected, actual) {
  failures.push({ collection, input, expected, actual });
}

function show(v) {
  if (v === undefined) return 'undefined';
  if (typeof v === 'number' && !Number.isFinite(v)) return String(v);
  return JSON.stringify(v);
}

/** Run a call, distinguishing "returned x" from "threw m" instead of losing the
 *  difference. A refusal replaced by a guess is the failure that matters most. */
function safe(f) {
  try {
    return { value: f() };
  } catch (e) {
    return { threw: e instanceof Error ? e.message : String(e) };
  }
}

function closeEnough(got, want) {
  if (typeof got !== 'number' || typeof want !== 'number') return false;
  if (Number.isNaN(got) || Number.isNaN(want)) return Number.isNaN(got) && Number.isNaN(want);
  if (!Number.isFinite(got) || !Number.isFinite(want)) return got === want;
  return Math.abs(got - want) <= REL_TOL * Math.max(Math.abs(got), Math.abs(want));
}

/** Scalars compare identically; numbers compare at REL_TOL. */
function scalarEquals(got, want) {
  if (typeof want === 'number') return closeEnough(got, want);
  return got === want;
}

/** `{ value, unit }` pairs, or null. The unit is a label and must match exactly;
 *  only the value gets a tolerance. */
function quantityMatches(got, want) {
  if (want === null) return got === null;
  if (got === null || typeof got !== 'object') return false;
  return got.unit === want.unit && closeEnough(got.value, want.value);
}

/**
 * Replay one collection.
 *
 * `each` returns { input, expected, actual, ok } for a row — the input and both
 * sides are carried through so a failure can name all three rather than only
 * report that something disagreed.
 */
function run(name, each) {
  const rows = fixture[name];
  if (!Array.isArray(rows)) {
    record(name, '(collection)', 'an array of cases', show(rows));
    tally.push({ name, cases: 0, bad: 1 });
    return;
  }
  let bad = 0;
  for (const row of rows) {
    const r = each(row);
    if (!r.ok) {
      bad += 1;
      record(name, r.input, r.expected, r.actual);
    }
  }
  tally.push({ name, cases: rows.length, bad });
}

/** A collection whose calls must not throw: a throw is reported as the answer. */
function returned(result, expected, matches) {
  if ('threw' in result) return { ok: false, actual: `threw Error: ${result.threw}` };
  return { ok: matches(result.value, expected), actual: show(result.value) };
}

// ── 1. normalizeUnit ───────────────────────────────────────────────────
run('normalizeUnit', (row) => ({
  input: show(row.in),
  expected: show(row.out),
  ...returned(safe(() => normalizeUnit(row.in)), row.out, scalarEquals),
}));

// ── 2. unitFamily ──────────────────────────────────────────────────────
run('unitFamily', (row) => ({
  input: show(row.in),
  expected: show(row.out),
  ...returned(safe(() => unitFamily(row.in)), row.out, scalarEquals),
}));

// ── 3. sameFamily ──────────────────────────────────────────────────────
run('sameFamily', (row) => ({
  input: `${show(row.a)}, ${show(row.b)}`,
  expected: show(row.out),
  ...returned(safe(() => sameFamily(row.a, row.b)), row.out, scalarEquals),
}));

// ── 4. convert (within family) ─────────────────────────────────────────
run('convert', (row) => ({
  input: `${show(row.value)} ${show(row.from)} → ${show(row.to)}`,
  expected: show(row.out),
  ...returned(safe(() => convert(row.value, row.from, row.to)), row.out, closeEnough),
}));

// ── 5. convertCrossFamily (must throw, with the exact message) ─────────
//
// These rows carry `error`, not `out`. The message is checked verbatim because
// it is the user-visible refusal, and a port that threw a different sentence
// would be a different product decision wearing the same behaviour.
run('convertCrossFamily', (row) => {
  const input = `${show(row.value)} ${show(row.from)} → ${show(row.to)}`;
  const expected = `throws ${show(row.error)}`;
  const r = safe(() => convert(row.value, row.from, row.to));
  if (!('threw' in r)) {
    return { input, expected, actual: `returned ${show(r.value)} — no refusal`, ok: false };
  }
  return { input, expected, actual: `throws ${show(r.threw)}`, ok: r.threw === row.error };
});

// ── 6. toSI ────────────────────────────────────────────────────────────
run('toSI', (row) => ({
  input: `${show(row.value)} ${show(row.unit)}`,
  expected: show(row.out),
  ...returned(safe(() => toSI(row.value, row.unit)), row.out, quantityMatches),
}));

// ── 7. explainRefusal ──────────────────────────────────────────────────
run('explainRefusal', (row) => ({
  input: `${show(row.from)} → ${show(row.to)}`,
  expected: show(row.out),
  ...returned(safe(() => explainRefusal(row.from, row.to)), row.out, scalarEquals),
}));

// ── 8. parseQuantity ───────────────────────────────────────────────────
run('parseQuantity', (row) => ({
  input: show(row.in),
  expected: show(row.out),
  ...returned(safe(() => parseQuantity(row.in)), row.out, quantityMatches),
}));

// ── 9. asNumber ────────────────────────────────────────────────────────
//
// JSON cannot hold NaN or ±Infinity, so the capture wrote those three inputs as
// strings (capture-fixtures.ts: `typeof v === 'number' && !isFinite(v) ? String(v) : v`).
// Decoding them back to numbers replays what was actually called — passing the
// literal string would exercise the typeof branch instead of the isFinite one
// and quietly stop testing the case the fixture was capturing.
const NON_FINITE = { NaN: Number.NaN, Infinity: Number.POSITIVE_INFINITY, '-Infinity': Number.NEGATIVE_INFINITY };
run('asNumber', (row) => {
  const arg = typeof row.in === 'string' && row.in in NON_FINITE ? NON_FINITE[row.in] : row.in;
  return {
    input: show(row.in),
    expected: show(row.out),
    ...returned(safe(() => asNumber(arg)), row.out, scalarEquals),
  };
});

// ── 10. fmt ────────────────────────────────────────────────────────────
// Display strings compare exactly: the grouping comma, the × and the
// superscript digits are the output, not decoration on it.
run('fmt', (row) => ({
  input: `${show(row.value)}, maxDecimals ${show(row.maxDecimals)}`,
  expected: show(row.out),
  ...returned(safe(() => fmt(row.value, row.maxDecimals)), row.out, (g, w) => g === w),
}));

// ── 11. roundToPrecision ───────────────────────────────────────────────
run('roundToPrecision', (row) => ({
  input: `${show(row.value)}, increment ${show(row.increment)}`,
  expected: show(row.out),
  ...returned(safe(() => roundToPrecision(row.value, row.increment)), row.out, closeEnough),
}));

// ── 12. quantityEquals ─────────────────────────────────────────────────
//
// `tolerancePct: null` means the case was captured through the default, so it
// is replayed through the default — passing null would test a 0% tolerance and
// silently stop pinning the 2% the product chose.
run('quantityEquals', (row) => ({
  input: `${show(row.a)} vs ${show(row.b)}, tolerancePct ${show(row.tolerancePct)}`,
  expected: show(row.out),
  ...returned(
    safe(() =>
      row.tolerancePct === null
        ? quantityEquals(row.a, row.b)
        : quantityEquals(row.a, row.b, row.tolerancePct),
    ),
    row.out,
    scalarEquals,
  ),
}));

// ── the tables themselves ──────────────────────────────────────────────
//
// Case replay can only see units the fixture already knows about. A unit added
// to units.ts after the capture would pass every case above while leaving the
// pin silently incomplete — so the exported tables are checked against the
// fixture's own census too.
const guard = [];
function guardCheck(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  guard.push({ what, ok });
  if (!ok) record('meta', what, show(want), show(got));
}

{
  const canonical = Object.keys(UNIT_TABLE).sort();
  const aliases = Object.keys(UNIT_ALIASES).sort();
  const families = [...new Set(Object.values(UNIT_TABLE).map((u) => u.family))].sort();
  const m = fixture.meta ?? {};
  guardCheck('canonical unit count', canonical.length, m.canonicalUnitCount);
  guardCheck('alias count', aliases.length, m.aliasCount);
  guardCheck('family count', families.length, m.familyCount);
  guardCheck('family names', families, m.families);
  guardCheck('SI unit by family', SI_UNIT_BY_FAMILY, m.siUnitByFamily);
  guardCheck('refusal pairs', REFUSAL_PAIRS, m.refusalPairs);
  guardCheck(
    'collections present',
    Object.keys(fixture).filter((k) => k !== 'meta').sort(),
    [...COLLECTIONS].sort(),
  );
}

// ── hostile input guard ────────────────────────────────────────────────
//
// Also not from the fixture, and for a sharper reason. Phase 0 captured real
// units, so no fixture case can catch a lookup that walks the PROTOTYPE CHAIN.
// `t in U` and `ALIASES[t]` did exactly that: every `Object.prototype` member
// name was accepted as a unit, so `normalizeUnit('toString')` returned
// 'toString', `sameFamily('toString', 'constructor')` returned TRUE, `convert`
// across that pair returned NaN with no throw, and `toSI` crashed.
//
// A Python dict has no prototype, so the canonical engine never behaved that
// way. This pins the mirror to the canon on inputs the fixture will never
// contain — and it is the one check here that would have failed before Phase 2.
{
  const PROTOTYPE_KEYS = [
    'toString', 'valueOf', 'constructor', 'hasOwnProperty',
    '__proto__', 'isPrototypeOf', 'propertyIsEnumerable', 'toLocaleString',
  ];
  for (const k of PROTOTYPE_KEYS) {
    guardCheck(`normalizeUnit(${JSON.stringify(k)}) refuses`, normalizeUnit(k), null);
    guardCheck(`unitFamily(${JSON.stringify(k)}) refuses`, unitFamily(k), null);
    guardCheck(`parseQuantity("1 ${k}") refuses`, parseQuantity(`1 ${k}`), null);
  }
  guardCheck('two prototype keys are not the same family', sameFamily('toString', 'constructor'), false);
  let threw = false;
  try { convert(1, 'toString', 'constructor'); } catch { threw = true; }
  guardCheck('convert across two prototype keys throws', threw, true);
}

// ── report ─────────────────────────────────────────────────────────────
console.log('openFerment unit parity — fixtures/units.json replayed against src/engine/units.ts');
console.log('─────────────────────────────────────────────────────────────────────────────────');

const order = new Map(COLLECTIONS.map((c, i) => [c, i]));
tally.sort((a, b) => (order.get(a.name) ?? 99) - (order.get(b.name) ?? 99));

let total = 0;
for (const t of tally) {
  total += t.cases;
  const mark = t.bad === 0 ? '✓' : `✗ ${t.bad} mismatch${t.bad === 1 ? '' : 'es'}`;
  console.log(`  ${t.name.padEnd(20)} ${String(t.cases).padStart(6)} cases   ${mark}`);
}

const missing = COLLECTIONS.filter((c) => !tally.some((t) => t.name === c));
for (const c of missing) console.log(`  ${c.padEnd(20)} ${'—'.padStart(6)}         ✗ absent from the fixture`);

console.log(`  ${''.padEnd(20)} ${'──────'}`);
console.log(`  ${'total'.padEnd(20)} ${String(total).padStart(6)} cases across ${tally.length} collections`);
console.log(
  `  ${'table guard'.padEnd(20)} ${String(guard.length).padStart(6)} checks   ` +
    `${guard.every((g) => g.ok) ? '✓' : `✗ ${guard.filter((g) => !g.ok).length} disagree`}`,
);

if (failures.length) {
  console.error(`\n✗ ${failures.length} mismatch(es) between fixtures/units.json and src/engine/units.ts:`);
  const SHOWN = 40;
  for (const f of failures.slice(0, SHOWN)) {
    console.error(`  - ${f.collection}(${f.input})`);
    console.error(`      expected: ${f.expected}`);
    console.error(`      actual:   ${f.actual}`);
  }
  if (failures.length > SHOWN) console.error(`  … and ${failures.length - SHOWN} more.`);
  console.error(
    '\nThe TypeScript mirror has drifted from the pinned canon. Either the change to\n' +
      'src/engine/units.ts is wrong, or it is right and fixtures/units.json must be\n' +
      're-captured — and re-captured in step with the Python. Do not edit the fixture by hand.',
  );
  process.exit(1);
}

console.log(`\n✓ ${total} cases replay identically. The TypeScript mirror matches the pin.\n`);
