/**
 * Does the TypeScript protocol engine still agree with the canon?
 *
 * `fixtures/scale.json` and `fixtures/diff.json` are the language-neutral pin of
 * what `src/engine/scale.ts` and `src/engine/diff.ts` did at Phase 0 of the
 * Python migration, and they are what `openferment_core.protocol` was written
 * against. `packages/core/tests/test_protocol.py` replays them on the Python
 * side; this file replays the same cases on the TypeScript side. Between the
 * two, neither mirror can drift without something going red. A mirror that has
 * quietly drifted is worse than no mirror, because both sides still answer
 * confidently — and here the answer is a mass on a balance in a real lab.
 *
 *   pnpm check:protocol   →  tsx scripts/check-protocol-parity.mjs
 *
 * It is a .mjs like the other checkers, but it imports .ts modules directly.
 * That resolves because tsx's loader transpiles them on the fly — the same
 * mechanism `check:units` and `check:biosteam` already rely on.
 *
 * INPUTS ARE NOT READ BACK OUT OF THE OUTPUTS. `ScaledMaterial` extends
 * `Material`, so every `scale.json` row echoes its own input inside its result;
 * a lazy replay could feed each expectation to itself and pass without calling
 * the engine at all. Instead the inputs come from `PROTOCOLS` — the same corpus
 * `scripts/capture-fixtures.ts` iterated — looked up by the identifying keys the
 * fixture carries, with the full enumeration guarded below so a material added
 * or renamed since the capture cannot slip through unreplayed. The Python
 * replay reaches the same corpus through `fixtures/schema-instances.json` and
 * takes the same care for the same reason.
 *
 * The synthetic diff cases are the exception, and deliberately so: `diff.json`
 * ships `syntheticInputs` precisely because the corpus cannot produce them.
 * Only PR-TAP-01 has a second version, so the real pairs never exercise an
 * added or a removed STEP. Replaying the three synthetic cases from those
 * stored inputs is the only thing that covers those two branches.
 *
 * Nothing here is a new expectation. Every expected value comes out of a
 * fixture; the script contains no remembered numbers of its own. Three exports
 * of scale.ts — `renderStepText`, `batchLabel` and `materialsChecklist` — have
 * no fixture collection, because the Phase 0 capture did not record them. They
 * are therefore not gated here. Extending `capture-fixtures.ts` is the fix;
 * inventing expected strings in this file would not be.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { inoculumVolume, scaleMaterial, scaleMaterials } from '../src/engine/scale.ts';
import { diffVersions } from '../src/engine/diff.ts';
import { PROTOCOLS } from '../src/data/source.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCALE_FIXTURE = join(ROOT, 'fixtures', 'scale.json');
const DIFF_FIXTURE = join(ROOT, 'fixtures', 'diff.json');

/** Floats compare relatively, never exactly: the Python side of this pin does
 *  the same arithmetic in a different order. 1e-12 is tight enough that a
 *  transposed factor cannot hide and loose enough to survive reassociation. */
const REL_TOL = 1e-12;

/** The collections each fixture must carry, `meta` aside. A fixture missing one,
 *  or carrying one this script does not replay, is itself a drift. */
const SCALE_COLLECTIONS = ['scaleMaterial', 'scaleMaterials', 'inoculumVolume'];
const DIFF_COLLECTIONS = ['diffVersions', 'syntheticInputs', 'diffVersionsSynthetic'];

/**
 * `syntheticInputs` carries the two versions but not which way round each
 * synthetic case was called, so the direction lives here — asserted against the
 * fixture's own labels below rather than assumed. A fourth synthetic case added
 * to the capture would fail that assertion instead of being skipped in silence,
 * which is the whole point of pinning the branches the corpus cannot reach.
 * `packages/core/tests/test_protocol.py` carries the identical mapping.
 */
const SYNTHETIC_DIRECTIONS = [
  { label: 'added, removed, modified and reordered steps', a: 'from', b: 'to' },
  { label: 'reverse direction', a: 'to', b: 'from' },
  { label: 'a version against itself', a: 'from', b: 'from' },
];

const scaleFixture = JSON.parse(readFileSync(SCALE_FIXTURE, 'utf8'));
const diffFixture = JSON.parse(readFileSync(DIFF_FIXTURE, 'utf8'));

const failures = [];
const tally = [];

function record(collection, input, expected, actual) {
  failures.push({ collection, input, expected, actual });
}

function show(v) {
  if (v === undefined) return 'undefined';
  if (typeof v === 'number' && !Number.isFinite(v)) return String(v);
  const s = JSON.stringify(v);
  // A whole scaled 30-material batch is not a readable failure message. The
  // path reported alongside it is what actually names the disagreement.
  return s !== undefined && s.length > 220 ? `${s.slice(0, 217)}…` : String(s);
}

/** Run a call, distinguishing "returned x" from "threw m" instead of losing the
 *  difference. A refusal replaced by a guess is the failure that matters most:
 *  `inoculumVolume` returns null rather than a volume when the seed is no
 *  denser than the target, and null is an answer, not an absence of one. */
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

/**
 * The first place two values disagree, as `{ path, want, got }`, or null.
 *
 * Returning the PATH rather than a boolean is what lets a failure name the one
 * field that moved inside a forty-material scale-up instead of printing both
 * structures and leaving the reader to diff them by eye.
 *
 * Numbers compare at REL_TOL; everything else — a `kind`, a unit label, a step
 * id — compares exactly, because those are the output rather than decoration on
 * it. `undefined` and an absent key are the same thing here: `diffVersions`
 * returns `changelog: b.changelog`, which JSON drops entirely when the newer
 * version carries no changelog, and `{ kind: 'added', b }` never has an `a`.
 * Treating absent and undefined as different would fail cases for a reason that
 * is an artefact of the file format, not of the engine.
 */
function firstDifference(got, want, path = '') {
  if (want === null || got === null) return want === got ? null : { path, want, got };
  if (typeof want === 'number' || typeof got === 'number') {
    return closeEnough(got, want) ? null : { path, want, got };
  }
  if (Array.isArray(want) || Array.isArray(got)) {
    if (!Array.isArray(want) || !Array.isArray(got)) return { path, want, got };
    if (want.length !== got.length) {
      return { path: `${path}.length`, want: want.length, got: got.length };
    }
    for (let i = 0; i < want.length; i += 1) {
      const d = firstDifference(got[i], want[i], `${path}[${i}]`);
      if (d) return d;
    }
    return null;
  }
  if (typeof want === 'object' || typeof got === 'object') {
    if (typeof want !== 'object' || typeof got !== 'object') return { path, want, got };
    for (const k of [...new Set([...Object.keys(want), ...Object.keys(got)])].sort()) {
      const d = firstDifference(got[k], want[k], `${path}.${k}`);
      if (d) return d;
    }
    return null;
  }
  return got === want ? null : { path, want, got };
}

/**
 * Replay one collection.
 *
 * `each` returns { input, expected, actual, ok } for a row — the input and both
 * sides are carried through so a failure can name all three rather than only
 * report that something disagreed.
 */
function run(name, rows, each) {
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

/** A collection whose calls must not throw: a throw is reported as the answer,
 *  and the reported expected/actual is the first path that disagrees. */
function returned(result, expected) {
  if ('threw' in result) {
    return { ok: false, expected: show(expected), actual: `threw Error: ${result.threw}` };
  }
  const d = firstDifference(result.value, expected);
  if (!d) return { ok: true, expected: show(expected), actual: show(result.value) };
  const at = d.path === '' ? '' : ` at ${d.path}`;
  return { ok: false, expected: `${show(d.want)}${at}`, actual: `${show(d.got)}${at}` };
}

// ── the corpus the capture iterated ────────────────────────────────────
//
// Keyed the way the fixture identifies its rows. Looked up rather than zipped
// by index, so a fixture that has gone out of step with the corpus reports the
// case it could not find instead of silently replaying the wrong material.
const versionByKey = new Map();
const materialByKey = new Map();
const corpusScaleKeys = [];
const corpusVersionKeys = [];
const corpusPairKeys = [];
const SCALES = scaleFixture.meta?.scales ?? [];
for (const p of PROTOCOLS) {
  for (const [i, v] of p.versions.entries()) {
    versionByKey.set(`${p.id}|${v.version}`, v);
    for (const m of v.materials) {
      materialByKey.set(`${p.id}|${v.version}|${m.name}`, m);
      for (const scale of SCALES) corpusScaleKeys.push(`${p.id}|${v.version}|${m.name}|${scale}`);
    }
    for (const scale of SCALES) corpusVersionKeys.push(`${p.id}|${v.version}|${scale}`);
    if (i > 0) corpusPairKeys.push(`${p.id}|${p.versions[i - 1].version}|${v.version}`);
  }
}

// ── 1. scaleMaterial ───────────────────────────────────────────────────
run('scaleMaterial', scaleFixture.scaleMaterial, (row) => {
  const input = `${row.protocol} v${row.version} ${show(row.material)} × ${show(row.scale)}`;
  const m = materialByKey.get(`${row.protocol}|${row.version}|${row.material}`);
  if (!m) {
    return { input, expected: show(row.out), actual: 'no such material in PROTOCOLS', ok: false };
  }
  return { input, ...returned(safe(() => scaleMaterial(m, row.scale)), row.out) };
});

// ── 2. scaleMaterials (the whole batch, in the version's own order) ────
run('scaleMaterials', scaleFixture.scaleMaterials, (row) => {
  const input = `${row.protocol} v${row.version} × ${show(row.scale)}`;
  const v = versionByKey.get(`${row.protocol}|${row.version}`);
  if (!v) {
    return { input, expected: show(row.out), actual: 'no such version in PROTOCOLS', ok: false };
  }
  return { input, ...returned(safe(() => scaleMaterials(v, row.scale)), row.out) };
});

// ── 3. inoculumVolume ──────────────────────────────────────────────────
//
// Three of these eight rows expect null: a seed no denser than the target, and
// a seed at zero. `returned` compares null to null exactly, so a port that
// answered with a number there would fail rather than round to something
// plausible-looking.
run('inoculumVolume', scaleFixture.inoculumVolume, (row) => ({
  input: `targetOD ${show(row.targetOD)}, ${show(row.cultureVolumeML)} mL, seedOD ${show(row.seedOD)}`,
  ...returned(
    safe(() => inoculumVolume(row.targetOD, row.cultureVolumeML, row.seedOD)),
    row.out,
  ),
}));

// ── 4. diffVersions, the real pairs ────────────────────────────────────
run('diffVersions', diffFixture.diffVersions, (row) => {
  const input = `${row.protocol} ${row.from} → ${row.to}`;
  const a = versionByKey.get(`${row.protocol}|${row.from}`);
  const b = versionByKey.get(`${row.protocol}|${row.to}`);
  if (!a || !b) {
    return { input, expected: show(row.out), actual: 'no such version in PROTOCOLS', ok: false };
  }
  return { input, ...returned(safe(() => diffVersions(a, b)), row.out) };
});

// ── 5. diffVersionsSynthetic ───────────────────────────────────────────
//
// The two branches the corpus cannot reach: a step added and a step removed.
// Replayed from `syntheticInputs`, which is exactly why that collection was
// captured. Skipping these would leave `added` and `removed` on STEPS
// unexercised on this side of the mirror while the tally still read green.
const synthetic = diffFixture.syntheticInputs ?? {};
run('diffVersionsSynthetic', diffFixture.diffVersionsSynthetic, (row) => {
  const input = `synthetic: ${show(row.label)}`;
  const dir = SYNTHETIC_DIRECTIONS.find((d) => d.label === row.label);
  if (!dir) {
    return { input, expected: show(row.out), actual: 'unmapped synthetic case', ok: false };
  }
  const a = synthetic[dir.a];
  const b = synthetic[dir.b];
  if (!a || !b) {
    return { input, expected: show(row.out), actual: 'syntheticInputs is incomplete', ok: false };
  }
  return { input, ...returned(safe(() => diffVersions(a, b)), row.out) };
});

// ── the census itself ──────────────────────────────────────────────────
//
// Case replay can only see what the fixture already knows about. A material
// added to the corpus, a scale dropped from the capture, or a protocol grown a
// third version would all pass every case above while leaving the pin silently
// incomplete — so the enumeration the capture walked is rebuilt from the live
// corpus and compared against the keys the fixture actually carries.
const guard = [];
function guardCheck(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  guard.push({ what, ok });
  if (!ok) record('census', what, show(want), show(got));
}

{
  const m = scaleFixture.meta ?? {};
  guardCheck('protocol count', PROTOCOLS.length, m.protocolCount);
  guardCheck('version count', PROTOCOLS.reduce((n, p) => n + p.versions.length, 0), m.versionCount);
  guardCheck(
    'scaleMaterial enumeration',
    (scaleFixture.scaleMaterial ?? []).map((r) => `${r.protocol}|${r.version}|${r.material}|${r.scale}`),
    corpusScaleKeys,
  );
  guardCheck(
    'scaleMaterials enumeration',
    (scaleFixture.scaleMaterials ?? []).map((r) => `${r.protocol}|${r.version}|${r.scale}`),
    corpusVersionKeys,
  );
  guardCheck(
    'scale.json collections',
    Object.keys(scaleFixture).filter((k) => k !== 'meta').sort(),
    [...SCALE_COLLECTIONS].sort(),
  );

  const dm = diffFixture.meta ?? {};
  guardCheck(
    'real version pairs',
    PROTOCOLS.reduce((n, p) => n + Math.max(0, p.versions.length - 1), 0),
    dm.realPairs,
  );
  guardCheck(
    'diffVersions enumeration',
    (diffFixture.diffVersions ?? []).map((r) => `${r.protocol}|${r.from}|${r.to}`),
    corpusPairKeys,
  );
  guardCheck('syntheticInputs carries from and to', Object.keys(synthetic).sort(), ['from', 'to']);
  guardCheck(
    'synthetic cases mapped',
    (diffFixture.diffVersionsSynthetic ?? []).map((r) => r.label),
    SYNTHETIC_DIRECTIONS.map((d) => d.label),
  );
  guardCheck(
    'diff.json collections',
    Object.keys(diffFixture).filter((k) => k !== 'meta').sort(),
    [...DIFF_COLLECTIONS].sort(),
  );
}

// ── report ─────────────────────────────────────────────────────────────
console.log(
  'openFerment protocol parity — fixtures/scale.json + fixtures/diff.json replayed against',
);
console.log('src/engine/scale.ts + src/engine/diff.ts');
console.log('─────────────────────────────────────────────────────────────────────────────────');

const ORDER = [...SCALE_COLLECTIONS, 'diffVersions', 'diffVersionsSynthetic'];
const order = new Map(ORDER.map((c, i) => [c, i]));
tally.sort((a, b) => (order.get(a.name) ?? 99) - (order.get(b.name) ?? 99));

let total = 0;
for (const t of tally) {
  total += t.cases;
  const mark = t.bad === 0 ? '✓' : `✗ ${t.bad} mismatch${t.bad === 1 ? '' : 'es'}`;
  console.log(`  ${t.name.padEnd(22)} ${String(t.cases).padStart(6)} cases   ${mark}`);
}

const missing = ORDER.filter((c) => !tally.some((t) => t.name === c));
for (const c of missing) {
  console.log(`  ${c.padEnd(22)} ${'—'.padStart(6)}         ✗ absent from the fixture`);
}

console.log(`  ${''.padEnd(22)} ${'──────'}`);
console.log(`  ${'total'.padEnd(22)} ${String(total).padStart(6)} cases across ${tally.length} collections`);
console.log(
  `  ${'census guard'.padEnd(22)} ${String(guard.length).padStart(6)} checks   ` +
    `${guard.every((g) => g.ok) ? '✓' : `✗ ${guard.filter((g) => !g.ok).length} disagree`}`,
);

if (failures.length) {
  console.error(
    `\n✗ ${failures.length} mismatch(es) between the protocol fixtures and src/engine/:`,
  );
  const SHOWN = 40;
  for (const f of failures.slice(0, SHOWN)) {
    console.error(`  - ${f.collection}(${f.input})`);
    console.error(`      expected: ${f.expected}`);
    console.error(`      actual:   ${f.actual}`);
  }
  if (failures.length > SHOWN) console.error(`  … and ${failures.length - SHOWN} more.`);
  console.error(
    '\nThe TypeScript mirror has drifted from the pinned canon. Either the change to\n' +
      'src/engine/scale.ts or src/engine/diff.ts is wrong, or it is right and the\n' +
      'fixtures must be re-captured — and re-captured in step with\n' +
      'openferment_core/protocol/. Do not edit the fixtures by hand.',
  );
  process.exit(1);
}

console.log(`\n✓ ${total} cases replay identically. The TypeScript mirror matches the pin.\n`);
