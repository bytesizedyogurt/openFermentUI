/**
 * The figure grammar's guard (OF-BLD-014 §6.1, E.8 rules 2 to 4).
 *
 *   pnpm check:figures
 *
 * 1. Every provenance draws a point no other provenance draws: shape (a ring
 *    counts as part of it), fill and outline dash.
 * 2. The two classes that are never evidence are dashed, point and line.
 * 3. Each figure's `toTable` returns one row per mark of the gallery's sample.
 * 4. `recharts` is imported only under src/components/figures/ and in the two
 *    screens that used it before the grammar.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import type { ExtractionRecord, Provenance } from '../src/data/types';
import samples from '../src/data/figureSamples.json';
import { ENCODING, NEVER_EVIDENCE, pointKey } from '../src/components/figures/encoding';
import { stripPoints, toTable as stripTable } from '../src/components/figures/EvidenceStrip';
import { toTable as ceilingTable } from '../src/components/figures/CeilingGap';
import { toTable as frontierTable } from '../src/components/figures/Frontier';

const problems: string[] = [];
const ok: string[] = [];

// 1 — one point per provenance.
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
if (stripRows !== drawn) problems.push(`EvidenceStrip's table has ${stripRows} rows for ${drawn} marks`);
const ceilings = samples.strip.rules.map((r) => ({ value: r.value, model: r.label }));
const ceilingRows = ceilingTable({ title: 't', records, unit: strip.unit, quantity: strip.quantity, ceilings }).rows.length;
if (ceilingRows !== drawn + ceilings.length) problems.push(`CeilingGap's table has ${ceilingRows} rows for ${drawn + ceilings.length} marks`);
const f = samples.frontier;
const frontierRows = frontierTable({ title: 't', points: f.points, growthUnit: f.growthUnit, productUnit: f.productUnit, productLabel: f.productLabel, model: f.model }).rows.length;
if (frontierRows !== f.points.length) problems.push(`Frontier's table has ${frontierRows} rows for ${f.points.length} points`);
const provs = new Set(stripPoints(strip).points.map((p) => p.provenance));
for (const p of Object.keys(ENCODING) as Provenance[]) if (!provs.has(p)) problems.push(`the sample draws no ${p} mark`);
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
  if (!/from ['"]recharts['"]/.test(readFileSync(file, 'utf8'))) continue;
  if (rel.startsWith('src/components/figures/') || ALLOWED.includes(rel)) continue;
  problems.push(`${rel} imports recharts; charts are drawn from src/components/figures/`);
}
ok.push('recharts is imported only under src/components/figures/ and in Compare and ProformaScenario');

if (problems.length) {
  for (const p of problems) console.error(`✗ ${p}`);
  process.exit(1);
}
for (const line of ok) console.log(`✓ ${line}`);
