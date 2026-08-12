/**
 * Phase 0 of the Python migration: pin what `src/engine/` does today, as
 * language-neutral JSON, before anything moves.
 *
 * The fixtures this writes are the only thing that will tell us whether the
 * Python port in Phase 2 actually reproduces the TypeScript, and whether the
 * generated types in Phase 1 still accept the real corpus. So the bar is
 * exhaustiveness, not coverage: the tables are enumerated from the engine's own
 * exports rather than transcribed, because the one alias nobody remembered to
 * type into a fixture is exactly the one that would diverge silently.
 *
 * Nothing here changes behaviour. It only observes it.
 *
 * Errors are recorded rather than avoided. `convert` across families throws,
 * and that throw is behaviour the Python must reproduce — a fixture that only
 * captured the calls which succeed would let the port replace a refusal with a
 * guess and still pass.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

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
} from '../src/engine/units';
import { scaleMaterial, scaleMaterials, inoculumVolume } from '../src/engine/scale';
import { diffVersions } from '../src/engine/diff';
import { computeRunMetrics } from '../src/engine/metrics';
import {
  PAPERS,
  RECORDS,
  STRAINS,
  PROTOCOLS,
  ONTOLOGY,
  SCENARIOS,
  MODULES,
} from '../src/data/source';
import type { ExtractionRecord, FieldId, ProtocolVersion, RunOutput } from '../src/data/types';

const OUT = join(process.cwd(), 'fixtures');
mkdirSync(OUT, { recursive: true });

/** Sampling points. Zero, unity, an awkward decimal, a round number, and the
 *  two ends of the range where float formatting starts to matter. */
const VALUES = [0, 1, 3.7, 100, 1e-6, 1e6];

/**
 * One shape with both members optional, rather than a discriminated union.
 *
 * A union cannot be spread into an object literal in TypeScript, and every call
 * site here wants to splice the outcome next to the inputs that produced it. The
 * cost is that `out` and `error` are both optional in the type; the fixture
 * itself only ever carries one of them, because `attempt` only ever sets one.
 */
interface Outcome {
  out?: unknown;
  error?: string;
}

function attempt(f: () => unknown): Outcome {
  try {
    return { out: f() };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

function write(name: string, data: unknown): number {
  const path = join(OUT, name);
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return JSON.stringify(data).length;
}

/** Deterministic ordering, so two consecutive runs are byte-identical. */
function sorted<T>(xs: T[], key: (x: T) => string): T[] {
  return [...xs].sort((a, b) => key(a).localeCompare(key(b)));
}

// ══ 1. units.json ══════════════════════════════════════════════════════

const canonicalUnits = Object.keys(UNIT_TABLE).sort();
const aliases = Object.keys(UNIT_ALIASES).sort();
const families = [...new Set(Object.values(UNIT_TABLE).map((u) => u.family))].sort();
const unitsByFamily: Record<string, string[]> = {};
for (const u of canonicalUnits) {
  const f = UNIT_TABLE[u].family;
  (unitsByFamily[f] ??= []).push(u);
}
/** One unit per family, for the cross-family sweep. */
const representative = Object.fromEntries(families.map((f) => [f, unitsByFamily[f][0]]));

// Every distinct value+unit pair the seed corpus actually carries, so
// parseQuantity is exercised on real strings rather than invented ones.
const corpusQuantities = new Set<string>();
for (const r of RECORDS) corpusQuantities.add(`${r.value} ${r.unit}`.trim());
for (const p of PROTOCOLS) {
  for (const v of p.versions) {
    for (const m of v.materials) corpusQuantities.add(`${m.amount} ${m.unit}`.trim());
  }
}
for (const s of SCENARIOS) {
  for (const a of s.assumptions) corpusQuantities.add(`${a.value} ${a.unit}`.trim());
  for (const d of s.dims) {
    for (const v of d.values) corpusQuantities.add(`${v} ${d.unit}`.trim());
  }
}

const unitsFixture = {
  meta: {
    generatedFrom: 'src/engine/units.ts',
    families,
    familyCount: families.length,
    canonicalUnitCount: canonicalUnits.length,
    aliasCount: aliases.length,
    siUnitByFamily: SI_UNIT_BY_FAMILY,
    refusalPairs: REFUSAL_PAIRS,
    sampleValues: VALUES,
  },
  // Every canonical spelling and every alias, plus the shapes normalizeUnit is
  // expected to reject.
  normalizeUnit: [
    ...canonicalUnits,
    ...aliases,
    ...canonicalUnits.map((u) => u.toUpperCase()),
    ...canonicalUnits.map((u) => ` ${u} `),
    'not a unit',
    'g/L/L',
    'kg m-3',
    'G L⁻¹',
  ].map((raw) => ({ in: raw, out: normalizeUnit(raw) })),

  unitFamily: [...canonicalUnits, ...aliases, 'not a unit'].map((u) => ({
    in: u,
    out: unitFamily(u),
  })),

  sameFamily: families.flatMap((fa) =>
    families.map((fb) => ({
      a: representative[fa],
      b: representative[fb],
      out: sameFamily(representative[fa], representative[fb]),
    })),
  ),

  // Every ordered within-family pair, at every sample value. Identity pairs are
  // included deliberately: convert(x, u, u) must be exactly x, and an affine
  // family is where a port most easily loses that.
  convert: families.flatMap((f) =>
    unitsByFamily[f].flatMap((from) =>
      unitsByFamily[f].flatMap((to) =>
        VALUES.map((value) => ({ value, from, to, ...attempt(() => convert(value, from, to)) })),
      ),
    ),
  ),

  // And every ordered cross-family pair, which must throw rather than guess.
  convertCrossFamily: families.flatMap((fa) =>
    families
      .filter((fb) => fb !== fa)
      .map((fb) => ({
        value: 1,
        from: representative[fa],
        to: representative[fb],
        ...attempt(() => convert(1, representative[fa], representative[fb])),
      })),
  ),

  toSI: canonicalUnits.flatMap((unit) =>
    VALUES.map((value) => ({ value, unit, ...attempt(() => toSI(value, unit)) })),
  ),

  // Every ordered pair of representatives, so the three explained refusals are
  // covered along with the several hundred that return null.
  explainRefusal: families.flatMap((fa) =>
    families.map((fb) => ({
      from: representative[fa],
      to: representative[fb],
      out: explainRefusal(representative[fa], representative[fb]),
    })),
  ),

  parseQuantity: [
    ...sorted([...corpusQuantities], (s) => s),
    '2 g/L',
    '0.15 h⁻¹',
    '200 mg/dL',
    '25 °C',
    '-3.5 %',
    '1,5 g/L',
    '2e-3 mol/l',
    '7.2',
    '  4 mL  ',
    'not a quantity',
    '',
  ].map((text) => ({ in: text, out: parseQuantity(text) })),

  asNumber: [
    ...VALUES.map((v) => v as number | string),
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    'CrPKG-like kinase',
    '',
    '12',
  ].map((v) => ({ in: typeof v === 'number' && !isFinite(v) ? String(v) : v, out: asNumber(v) })),

  fmt: [
    ...VALUES,
    -0.0004,
    0.0012,
    12345.678,
    2.04e4,
    999999,
    1000000,
    1e-7,
    123456789,
  ].flatMap((v) => [0, 1, 3].map((d) => ({ value: v, maxDecimals: d, out: fmt(v, d) }))),

  roundToPrecision: [
    [3.14159, 0.1],
    [3.14159, 0.01],
    [3.14159, 1],
    [0, 0.1],
    [-2.55, 0.1],
    [1e6, 1000],
  ].map(([value, increment]) => ({ value, increment, out: roundToPrecision(value, increment) })),

  // Including the default tolerance and an explicit one, since 2% is a product
  // decision rather than a mathematical constant and a port could silently pick
  // a different default.
  quantityEquals: (
    [
      [{ value: 1, unit: 'g L⁻¹' }, { value: 1000, unit: 'mg L⁻¹' }, undefined],
      [{ value: 1, unit: 'g L⁻¹' }, { value: 1, unit: 'mg L⁻¹' }, undefined],
      [{ value: 25, unit: '°C' }, { value: 298.15, unit: 'K' }, undefined],
      [{ value: 1, unit: '% TSP' }, { value: 1, unit: '%' }, undefined],
      [{ value: 1, unit: 'USD kg⁻¹' }, { value: 1, unit: 'EUR kg⁻¹' }, undefined],
      [{ value: 100, unit: 'g L⁻¹' }, { value: 101, unit: 'g L⁻¹' }, undefined],
      [{ value: 100, unit: 'g L⁻¹' }, { value: 103, unit: 'g L⁻¹' }, undefined],
      [{ value: 100, unit: 'g L⁻¹' }, { value: 103, unit: 'g L⁻¹' }, 5],
      [{ value: 0, unit: 'g L⁻¹' }, { value: 0, unit: 'g L⁻¹' }, undefined],
    ] as [{ value: number; unit: string }, { value: number; unit: string }, number | undefined][]
  ).map(([a, b, tolerancePct]) => ({
    a,
    b,
    tolerancePct: tolerancePct ?? null,
    ...attempt(() =>
      tolerancePct === undefined ? quantityEquals(a, b) : quantityEquals(a, b, tolerancePct),
    ),
  })),
};

// ══ 2. scale.json ══════════════════════════════════════════════════════

const SCALES = [0.5, 1, 2, 10];

const scaleFixture = {
  meta: {
    generatedFrom: 'src/engine/scale.ts',
    scales: SCALES,
    protocolCount: PROTOCOLS.length,
    versionCount: PROTOCOLS.reduce((n, p) => n + p.versions.length, 0),
  },
  scaleMaterial: PROTOCOLS.flatMap((p) =>
    p.versions.flatMap((v) =>
      v.materials.flatMap((m) =>
        SCALES.map((scale) => ({
          protocol: p.id,
          version: v.version,
          material: m.name,
          scale,
          ...attempt(() => scaleMaterial(m, scale)),
        })),
      ),
    ),
  ),
  scaleMaterials: PROTOCOLS.flatMap((p) =>
    p.versions.flatMap((v) =>
      SCALES.map((scale) => ({
        protocol: p.id,
        version: v.version,
        scale,
        ...attempt(() => scaleMaterials(v, scale)),
      })),
    ),
  ),
  // Seed density above, at and below the target, plus the two refusal cases:
  // a seed no denser than the target, and a seed at zero.
  inoculumVolume: [
    [0.1, 100, 2],
    [0.1, 1000, 2],
    [0.5, 250, 4.8],
    [1, 500, 1],
    [1, 500, 0.5],
    [1, 500, 0],
    [0, 500, 3],
    [0.2, 50, 6.4],
  ].map(([targetOD, cultureVolumeML, seedOD]) => ({
    targetOD,
    cultureVolumeML,
    seedOD,
    out: inoculumVolume(targetOD, cultureVolumeML, seedOD),
  })),
};

// ══ 3. diff.json ═══════════════════════════════════════════════════════

// Exactly one protocol in the corpus has more than one version, so the real
// pairs exercise `modified` and `unchanged` on steps but never `added` or
// `removed`. A port verified only against those would be free to get step
// insertion wrong. The synthetic pair below covers the two missing branches and
// is labelled so nobody mistakes it for a protocol anybody ran.
const [baseVersion] = PROTOCOLS[0].versions;
const syntheticFrom: ProtocolVersion = {
  ...baseVersion,
  version: 'synthetic-a',
  steps: baseVersion.steps.slice(0, 3),
  materials: baseVersion.materials.slice(0, 2),
};
const syntheticTo: ProtocolVersion = {
  ...baseVersion,
  version: 'synthetic-b',
  steps: [
    // reordered, one dropped, one inserted, one edited
    { ...baseVersion.steps[1], text: `${baseVersion.steps[1].text} (edited)` },
    { ...baseVersion.steps[0], id: 'synthetic-inserted-step', text: 'Inserted step.' },
    baseVersion.steps[2],
  ],
  materials: [
    baseVersion.materials[0],
    { ...baseVersion.materials[1], amount: baseVersion.materials[1].amount * 2 },
    { ...baseVersion.materials[0], name: 'Synthetic added material' },
  ],
};

const diffFixture = {
  meta: {
    generatedFrom: 'src/engine/diff.ts',
    realPairs: PROTOCOLS.reduce((n, p) => n + Math.max(0, p.versions.length - 1), 0),
    note:
      'Only PR-TAP-01 carries a second version, so the real pairs never produce an added or removed STEP. The synthetic pair covers those branches and describes nothing that happened.',
  },
  diffVersions: PROTOCOLS.flatMap((p) =>
    p.versions.slice(1).map((v, i) => ({
      protocol: p.id,
      from: p.versions[i].version,
      to: v.version,
      ...attempt(() => diffVersions(p.versions[i], v)),
    })),
  ),
  syntheticInputs: { from: syntheticFrom, to: syntheticTo },
  diffVersionsSynthetic: [
    { label: 'added, removed, modified and reordered steps', ...attempt(() => diffVersions(syntheticFrom, syntheticTo)) },
    { label: 'reverse direction', ...attempt(() => diffVersions(syntheticTo, syntheticFrom)) },
    { label: 'a version against itself', ...attempt(() => diffVersions(syntheticFrom, syntheticFrom)) },
  ],
};

// ══ 4. metrics.json ════════════════════════════════════════════════════
//
// RUN_OUTPUTS is empty and stays empty — no extractor has been run, and
// inventing one would be the fabrication the honesty policy forbids. The inputs
// below are explicitly synthetic and labelled as such: they exist to exercise
// every branch of computeRunMetrics, not to describe anything that happened.

const goldRecords = RECORDS.filter((r) => r.gold);
// The seed gold set is empty — 60 are planned across 14 papers and none has been
// annotated yet — so when it is, the metric branches are exercised against
// records marked gold here and nowhere else. These never enter the app.
const syntheticGold: ExtractionRecord[] =
  goldRecords.length > 0
    ? goldRecords
    : RECORDS.slice(0, 6).map(
        (r, i): ExtractionRecord => ({
          ...r,
          id: `synthetic-gold-${i + 1}`,
          // `gold` is the annotated ground truth, not a flag — an annotator
          // writes down what the paper actually says. Reusing the record's own
          // value is the only honest stand-in: it invents no measurement.
          gold: { value: r.value, unit: r.unit },
        }),
      );

const outcomes = ['match', 'value_mismatch', 'unit_error', 'span_error', 'miss'] as const;

// `ExtractorRun` is a string literal union of the extractor versions the design
// document names. There is no synthetic member and adding one would be a
// fabricated run, so the fixtures reuse the declared labels and distinguish the
// three cases by name in the output instead.
const syntheticRun: RunOutput = {
  run: 'v0.4',
  results: syntheticGold.map((r, i) => ({
    goldRecordId: r.id,
    outcome: outcomes[i % outcomes.length],
    extracted: { value: 1 + i, unit: r.unit },
  })),
  falsePositives: [
    {
      id: 'synthetic-fp-1',
      paperId: syntheticGold[0]?.paperId ?? 'H4',
      field: (syntheticGold[0]?.field ?? 'titer_secreted') as FieldId,
      extracted: { value: 99, unit: 'g L⁻¹' },
      note: 'Spurious extraction, synthetic.',
    },
  ],
};

/** A run naming a gold record that no longer exists — the drop-from-metrics branch. */
const staleRun: RunOutput = {
  ...syntheticRun,
  run: 'v0.4r',
  results: [
    { goldRecordId: 'record-that-was-deleted', outcome: 'match' },
    ...syntheticRun.results.slice(0, 2),
  ],
  falsePositives: [],
};

/** An empty run: no results, no false positives. */
const emptyRun: RunOutput = {
  run: 'v0.3',
  results: [],
  falsePositives: [],
};

const metricsFixture = {
  meta: {
    generatedFrom: 'src/engine/metrics.ts',
    note:
      'Inputs are synthetic and exist only to exercise every branch. RUN_OUTPUTS in the app is empty and stays empty until a real extractor has been run.',
    goldRecordsInSeed: goldRecords.length,
    syntheticGoldUsed: goldRecords.length === 0,
  },
  inputs: { syntheticGold, runs: [syntheticRun, staleRun, emptyRun] },
  computeRunMetrics: (
    [
      ['every outcome, plus a false positive', syntheticRun],
      ['a result naming a gold record that no longer exists', staleRun],
      ['no results and no false positives', emptyRun],
    ] as [string, RunOutput][]
  ).map(([label, run]) => ({
    label,
    extractorRun: run.run,
    ...attempt(() => computeRunMetrics(run, syntheticGold)),
  })),
};

// ══ 5. schema-instances.json ═══════════════════════════════════════════

const schemaFixture = {
  meta: {
    generatedFrom: 'src/data/*',
    counts: {
      papers: PAPERS.length,
      records: RECORDS.length,
      strains: STRAINS.length,
      protocols: PROTOCOLS.length,
      ontology: ONTOLOGY.length,
      scenarios: SCENARIOS.length,
      learnModules: MODULES.length,
    },
    note:
      'Every seeded entity, verbatim. Phase 1 Pydantic models must accept all of these. Where a real corpus instance fails to parse, the model is wrong — never the data.',
  },
  papers: PAPERS,
  records: RECORDS,
  strains: STRAINS,
  protocols: PROTOCOLS,
  ontology: ONTOLOGY,
  scenarios: SCENARIOS.map((s) => ({
    ...s,
    // Scenario dims carry no functions; cost models do, and a function cannot
    // be serialised. The model layer only needs the data-bearing shape.
    dims: s.dims,
  })),
  learnModules: MODULES,
};

// ══ write ══════════════════════════════════════════════════════════════

function count(x: unknown): number {
  if (Array.isArray(x)) return x.length;
  if (x && typeof x === 'object') {
    return Object.values(x as Record<string, unknown>).reduce<number>(
      (n, v) => n + (Array.isArray(v) ? v.length : 0),
      0,
    );
  }
  return 0;
}

const files: [string, unknown][] = [
  ['units.json', unitsFixture],
  ['scale.json', scaleFixture],
  ['diff.json', diffFixture],
  ['metrics.json', metricsFixture],
  ['schema-instances.json', schemaFixture],
];

console.log('openFerment fixture capture');
console.log('───────────────────────────');
for (const [name, data] of files) {
  const bytes = write(name, data);
  const cases = count(data);
  console.log(`  ${name.padEnd(24)} ${String(cases).padStart(6)} cases   ${(bytes / 1024).toFixed(0)} KB`);
}

console.log('\nunits.json by function');
for (const [k, v] of Object.entries(unitsFixture)) {
  if (Array.isArray(v)) console.log(`  ${k.padEnd(20)} ${String(v.length).padStart(6)}`);
}
console.log(
  `\n  ${families.length} families · ${canonicalUnits.length} canonical units · ${aliases.length} aliases · ${corpusQuantities.size} distinct corpus quantities`,
);
