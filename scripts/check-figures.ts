/**
 * The figure grammar's guard (OF-BLD-014 §6.1, E.8 rules 2 to 4).
 *
 *   pnpm check:figures
 *
 * 1. Every provenance draws exactly the mark E.8's table gives it, and so a
 *    point no other provenance draws; a filled point stands for an observed
 *    value alone (rule 3).
 * 2. The two classes that are never evidence are dashed, point and line.
 * 3. Each figure's `toTable` returns one row per mark of the gallery's sample.
 * 4. `recharts` is imported only under src/components/figures/ and in the two
 *    screens that used it before the grammar, by any import form.
 * 5. What the review of Phase 6 found (§6.R): a modeled mark is held out of
 *    the median, a ceiling's rule keeps its own provenance, and a yield is
 *    held against a sugar's ceiling only when it was measured on that sugar.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import type { ExtractionRecord, Provenance } from '../src/data/types';
import samples from '../src/data/figureSamples.json';
import { ENCODING, NEVER_EVIDENCE, pointKey } from '../src/components/figures/encoding';
import { stripPoints, toTable as stripTable } from '../src/components/figures/EvidenceStrip';
import { toTable as ceilingTable } from '../src/components/figures/CeilingGap';
import { toTable as frontierTable } from '../src/components/figures/Frontier';
import { toTable as distributionTable } from '../src/components/figures/Distribution';
import { toTable as tornadoTable } from '../src/components/figures/Tornado';
import { yieldsOnSugar } from '../src/lib/geneos';

const problems: string[] = [];
const ok: string[] = [];

// 1 — E.8's table, written out here as the check's own copy.
type Row = [shape: string, filled: boolean, ring: boolean, outline: string, dash: string, weight: string, amber: boolean];
const E8: Record<Provenance, Row> = {
  measured: ['diamond', true, false, 'solid', 'solid', 'heavy', false],
  gold: ['circle', true, true, 'solid', 'solid', 'normal', false],
  verified: ['circle', true, false, 'solid', 'solid', 'normal', false],
  curated: ['square', true, false, 'solid', 'solid', 'normal', false],
  unverified: ['circle', false, false, 'solid', 'solid', 'thin', false],
  computed: ['square', false, false, 'solid', 'dotted', 'normal', false],
  user: ['triangle', false, false, 'solid', 'solid', 'thin', false],
  'industry-estimate': ['diamond', false, false, 'dashed', 'long', 'normal', false],
  demo: ['circle', false, false, 'dashed', 'short', 'normal', true],
};
for (const p of Object.keys(E8) as Provenance[]) {
  const m = ENCODING[p];
  const got: Row = [m.point.shape, m.point.filled, m.point.ring, m.point.outline, m.line.dash, m.line.weight, m.amber];
  if (JSON.stringify(got) !== JSON.stringify(E8[p])) problems.push(`${p} draws ${JSON.stringify(got)}; E.8 gives ${JSON.stringify(E8[p])}`);
}
const OBSERVED: Provenance[] = ['measured', 'gold', 'verified', 'curated'];
for (const p of Object.keys(ENCODING) as Provenance[]) {
  if (ENCODING[p].point.filled && !OBSERVED.includes(p)) problems.push(`${p} draws a filled point, which stands for an observed value alone`);
}
ok.push('every provenance draws the mark E.8 gives it; filled points are observed values alone');

const seen = new Map<string, Provenance>();
for (const p of Object.keys(ENCODING) as Provenance[]) {
  const key = pointKey(p);
  const other = seen.get(key);
  if (other) problems.push(`${p} and ${other} draw the same point (${key})`);
  seen.set(key, p);
}
if (!problems.length) ok.push(`${seen.size} provenances, ${seen.size} distinct points`);

// 2 — never evidence, never solid.
for (const p of NEVER_EVIDENCE) {
  const m = ENCODING[p];
  if (m.point.outline !== 'dashed') problems.push(`${p} draws a solid outline; it is never evidence`);
  if (m.line.dash === 'solid' || m.line.dash === 'dotted') problems.push(`${p} draws a ${m.line.dash} line; it is never evidence`);
}
for (const p of Object.keys(ENCODING) as Provenance[]) {
  if (!NEVER_EVIDENCE.includes(p) && ENCODING[p].point.outline === 'dashed') problems.push(`${p} is evidence but draws a dashed outline`);
}
ok.push('industry-estimate and demo are dashed, and no class of evidence is');

// 3 — a table row per mark.
const records = samples.strip.records as unknown as ExtractionRecord[];
const strip = { title: 't', records, unit: samples.strip.unit, quantity: samples.strip.quantity, groupBy: 'organism' as const };
const drawn = stripPoints(strip).points.length;
if (drawn !== records.length) problems.push(`the sample's strip draws ${drawn} of its ${records.length} records`);
const stripRows = stripTable(strip).rows.length;
// Counted from the sample itself, never from the function the table is built on.
if (stripRows !== records.length) problems.push(`EvidenceStrip's table has ${stripRows} rows for the sample's ${records.length} records`);
const ceilings = samples.strip.rules.map((r) => ({ value: r.value, model: r.label }));
const ceilingRows = ceilingTable({ title: 't', records, unit: strip.unit, quantity: strip.quantity, ceilings }).rows.length;
if (ceilingRows !== records.length + ceilings.length) problems.push(`CeilingGap's table has ${ceilingRows} rows for ${records.length + ceilings.length} marks`);
const f = samples.frontier;
const frontierRows = frontierTable({ title: 't', points: f.points, growthUnit: f.growthUnit, productUnit: f.productUnit, productLabel: f.productLabel, model: f.model }).rows.length;
if (frontierRows !== f.points.length) problems.push(`Frontier's table has ${frontierRows} rows for ${f.points.length} points`);
const provs = new Set(stripPoints(strip).points.map((p) => p.provenance));
for (const p of Object.keys(ENCODING) as Provenance[]) if (!provs.has(p)) problems.push(`the sample draws no ${p} mark`);
// §8.4 — a histogram bin or a percentile rule is a mark; so is a tornado row.
const bins = [0, 1, 2].map((i) => ({ low: i, high: i + 1, count: i + 1 }));
const quantiles = { p5: 0.2, p25: 0.8, p50: 1.5, p75: 2.2, p95: 2.9 };
const distRows = distributionTable({ title: 't', quantity: 'q', unit: 'u', bins, quantiles, provenance: 'demo', samples: 6, infeasible: [] }).rows;
if (distRows.length !== bins.length + 5) problems.push(`Distribution's table has ${distRows.length} rows for ${bins.length + 5} marks`);
if (distRows.some((r) => r[3] !== 'demo')) problems.push("a Distribution's marks lose the run's provenance");
const tRows = tornadoTable({ title: 't', drawn: 'd', series: ['a'], unit: 'u', provenance: 'demo', rows: [{ label: 'x', values: [0.2] }, { label: 'y', values: [-0.7] }] }).rows;
if (tRows.length !== 2 || tRows[0][0] !== 'y') problems.push('the Tornado table is not one row per input, strongest first');
ok.push(`tables: distribution ${distRows.length}, tornado ${tRows.length}, one row per mark, strongest input first`);
ok.push(`tables: strip ${stripRows}, ceiling ${ceilingRows}, frontier ${frontierRows}, one row per mark; the sample draws all ${provs.size} classes`);

// 4 — recharts stays where it was.
const ALLOWED = ['src/screens/Compare.tsx', 'src/screens/ProformaScenario.tsx'];
function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}
for (const file of walk('src').filter((f) => /\.(ts|tsx)$/.test(f))) {
  const rel = relative('.', file).split('\\').join('/');
  if (!/(from\s*|import\s*\(\s*|require\s*\(\s*)['"]recharts(\/[^'"]*)?['"]/.test(readFileSync(file, 'utf8'))) continue;
  if (rel.startsWith('src/components/figures/') || ALLOWED.includes(rel)) continue;
  problems.push(`${rel} imports recharts; charts are drawn from src/components/figures/`);
}
ok.push('recharts is imported only under src/components/figures/ and in Compare and ProformaScenario');

// 5 — what the review of Phase 6 found.
const demoPoint = stripPoints(strip).points.find((p) => p.provenance === 'demo');
if (!demoPoint?.heldOut) problems.push('a modeled (demo) mark enters the median');
const demoRule = ceilingTable({ title: 't', records: [], unit: 'g g-1', quantity: 'q', ceilings: [{ value: 0.5, model: 'stand-in', provenance: 'demo' }] }).rows;
if (demoRule[0]?.[4] !== 'demo') problems.push(`a demo ceiling's rule draws as ${demoRule[0]?.[4]}, not demo`);
const mk = (id: string, carbonSource?: string) => ({ ...records[0], id, field: 'pha_yield_substrate', carbonSource }) as unknown as ExtractionRecord;
const sorted = yieldsOnSugar([mk('a', 'glucose'), mk('b', 'glycerol'), mk('c'), mk('d', 'D-glucose syrup')], 'glucose');
if (sorted.on.map((r) => r.id).join() !== 'a,d' || sorted.elsewhere !== 2) problems.push(`yieldsOnSugar kept ${sorted.on.map((r) => r.id).join()} for glucose`);
ok.push('a demo mark is held out of the median, a ceiling keeps its provenance, a yield meets only its own sugar\'s ceiling');

if (problems.length) {
  for (const p of problems) console.error(`✗ ${p}`);
  process.exit(1);
}
for (const line of ok) console.log(`✓ ${line}`);
