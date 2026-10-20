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
 * 6. OF-BLD-019 §4.1: RecoveryByUnit draws one row per unit, never divides a
 *    recovery out of a unit no product enters, and keeps the run's provenance.
 * 7. OF-BLD-019 §3.2: CostWaterfall draws one row per TEA line and closes on
 *    the price the run solved, never a sum it made; a line with no per-unit
 *    value draws no bar; a credit runs back; every row keeps the run's
 *    provenance. CostWaterfall and Tornado each stand on the grammar (their
 *    own toTable, ENCODING, FigureFrame, no recharts), are exported from the
 *    figures index, and the BioSTEAM scenario's sections draw with them.
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
import { toTable as ledgerTable } from '../src/components/figures/IntervalLedger';
import { noBar, toTable as recoveryTable } from '../src/components/figures/RecoveryByUnit';
import { bars as waterfallBars, toTable as waterfallTable } from '../src/components/figures/CostWaterfall';
import type { TrainUnit } from '../src/data/types';
import { gatherLinks } from '../src/components/Dossier';
import { ArtifactsDown, ArtifactRefused } from '../src/lib/artifacts';
import { YIELD_FIELD, yieldFieldKnown, yieldsOnSugar } from '../src/lib/geneos';

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
// §9.3 — one ledger row per prediction, each saying its kind and verdict.
const lp = (id: string, extra: object) => ({ id, label: id, value: 5, unit: 'g L-1', confidence: 'low' as const, basis: 'b', ...extra });
const lRows = ledgerTable({ title: 't', rows: [
  { key: 'a', label: 'a', prediction: lp('a', {}), lockedAt: '2026-10-15', observed: { value: 5.2, unit: 'g L-1' }, held: true },
  { key: 'b', label: 'b', prediction: lp('b', { kind: 'interval', interval: { low: 4, high: 6 } }), lockedAt: '2026-10-15', observed: { value: 7, unit: 'g L-1' }, held: false },
  { key: 'c', label: 'c', prediction: lp('c', { kind: 'bound' }), lockedAt: null, observed: null, held: null },
] }).rows;
if (lRows.length !== 3 || lRows.map((r) => `${r[1]}:${r[6]}`).join() !== 'point:held,interval:missed,bound:untested')
  problems.push(`IntervalLedger's table is not one row per prediction with its kind and verdict: ${JSON.stringify(lRows)}`);
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
// A ceiling meets only its own product's yields: a PHA yield never stands
// beside an ethanol ceiling, and a product whose field the ontology lacks
// draws nothing.
const etoh = { ...mk('e', 'glucose'), field: YIELD_FIELD.ethanol } as unknown as ExtractionRecord;
const onEthanol = yieldsOnSugar([mk('a', 'glucose'), etoh], 'glucose', 'ethanol');
const wantEthanol = yieldFieldKnown('ethanol') ? 'e' : '';
if (onEthanol.on.map((r) => r.id).join() !== wantEthanol) problems.push(`an ethanol ceiling meets ${onEthanol.on.map((r) => r.id).join() || 'nothing'}, not ${wantEthanol || 'nothing'}`);
const unknown = yieldsOnSugar([mk('a', 'glucose')], 'glucose', 'no-such-product');
if (unknown.on.length || unknown.elsewhere) problems.push('a product with no yield field in the ontology draws records');
ok.push('a demo mark is held out of the median, a ceiling keeps its provenance, a yield meets only its own sugar\'s and its own product\'s ceiling');

// §9.R — the dossier keeps what came back, in the chain's order, and names
// what did not; one missing artifact no longer blanks the band.
{
  const art = (id: string, tool: string) => ({ id, tool }) as never;
  const store: Record<string, unknown> = { p: art('p', 'proforma.run'), f: art('f', 'growth_forecast'), c: art('c', 'geneos.ceiling') };
  const fetch = async (id: string) => {
    if (id === 'gone') throw new ArtifactRefused(404, 'there is no artifact gone');
    return store[id] as never;
  };
  const g = await gatherLinks([{ label: 'price', artifactId: 'p' }, { label: 'gone', artifactId: 'gone' }, { label: 'final', artifactId: 'f' }, { label: 'ceiling', artifactId: 'c' }], fetch);
  const order = g.links.map((l) => l.artifact.tool).join();
  if (order !== 'geneos.ceiling,growth_forecast,proforma.run') problems.push(`the dossier orders its chain as ${order}`);
  if (g.failed.length !== 1 || g.failed[0].predictionLabel !== 'gone' || g.down) problems.push('a missing artifact is not named on its own');
  const d = await gatherLinks([{ label: 'x', artifactId: 'p' }], async () => { throw new ArtifactsDown('The service is not running.'); });
  if (!d.down || d.links.length) problems.push('a service that is down is not said');
  ok.push('the dossier draws ceiling, forecast, price in that order, names an artifact that is missing, and says when the service is down');
}

// 6 — OF-BLD-019 §4.1: a train's recovery, one row per unit. A unit no
// product enters, or one off the path, has no recovery: it says why in words
// and draws no bar, and no cell holds NaN or Infinity.
{
  const unit = (id: string, over: Partial<TrainUnit>): TrainUnit => ({
    id, unitClass: 'Unit', line: null, order: 0, ins: [], outs: [], onPath: true, massIn: 1, massOut: 1,
    productIn: 1, productOut: 1, productOnward: 1, productLost: 0, lostTo: [], recovery: 1, cumulative: 1, note: null, ...over,
  });
  const units = [
    unit('R', { productIn: 0, recovery: null, note: 'no E enters R: the product is formed here' }),
    unit('C', { productIn: 52, productOnward: 47, productLost: 5, recovery: 47 / 52, cumulative: 0.9, lostTo: ['centrate'] }),
    unit('W', { onPath: false, recovery: null, cumulative: null, productOnward: null, productLost: null, note: "off the product's path" }),
  ];
  const rows = recoveryTable({ title: 't', product: 'E', units, provenance: 'demo', massUnit: 'kg/hr' }).rows;
  if (rows.length !== units.length) problems.push(`RecoveryByUnit's table has ${rows.length} rows for ${units.length} units`);
  if (rows.some((r) => r.some((c) => /NaN|Infinity/.test(String(c))))) problems.push('a RecoveryByUnit cell holds NaN or Infinity');
  if (rows[0][7] !== '—' || !String(rows[0][10]).includes('formed here')) problems.push('a unit no product enters is given a recovery, or not told why');
  if (noBar(units[0]) == null || noBar(units[2]) == null || noBar(units[1]) != null) problems.push('RecoveryByUnit draws a bar for a unit with no recovery, or none for one with');
  if (rows.some((r) => r[9] !== 'demo')) problems.push("a RecoveryByUnit row loses the run's provenance");
  ok.push(`tables: recovery by unit ${rows.length}, one row per unit; a unit with no product in says why and draws no bar`);
}

// 7 — OF-BLD-019 §3.2: the cost breakdown and the tornado, on the grammar.
{
  const line = (key: string, perUnit: number | null) => ({ key, label: key, perUnit, usdPerYear: 1000, reads: `TEA ${key}` });
  // The lines sum to 1.3; the run's price is 1.5, so a total the figure made itself shows.
  const lines = [line('feedstock', 1.0), line('utilities', 0.4), line('otherVariable', null), line('coproductCredits', -0.1)];
  const props = { title: 't', lines, total: { label: 'Base-case price', value: 1.5 }, unit: 'USD per kg', annualUnit: 'USD/yr', provenance: 'demo' as const };
  const rows = waterfallTable(props).rows;
  if (rows.length !== lines.length + 1) problems.push(`CostWaterfall's table has ${rows.length} rows for ${lines.length} lines and the price`);
  const last = rows[rows.length - 1];
  if (last?.[1] !== '1.5') problems.push(`CostWaterfall's last row is ${last?.[1]}, not the price the run solved`);
  if (rows.some((r) => r[4] !== 'demo')) problems.push("a CostWaterfall row loses the run's provenance");
  if (rows.some((r) => r.some((c) => /NaN|Infinity/.test(String(c))))) problems.push('a CostWaterfall cell holds NaN or Infinity');
  const drawn = waterfallBars(props);
  if (drawn.some((b) => b.key === 'otherVariable')) problems.push('CostWaterfall draws a bar for a line with no per-unit value');
  const total = drawn.find((b) => b.total);
  if (!total || total.from !== 0 || total.to !== 1.5) problems.push('CostWaterfall closes on a total of its own, not the price the run solved');
  const credit = drawn.find((b) => b.key === 'coproductCredits');
  if (!credit || !(credit.to < credit.from)) problems.push('a co-product credit does not run back');
  const util = drawn.find((b) => b.key === 'utilities');
  if (!util || util.from !== 1.0) problems.push('a CostWaterfall bar does not start where the line before it ended');
  const index = readFileSync('src/components/figures/index.ts', 'utf8');
  for (const name of ['CostWaterfall', 'Tornado']) {
    const src = readFileSync(`src/components/figures/${name}.tsx`, 'utf8');
    if (!/export function toTable\(/.test(src)) problems.push(`${name} exports no toTable`);
    if (!/from '\.\/FigureFrame'/.test(src) || !/<FigureFrame\b/.test(src)) problems.push(`${name} is not framed by FigureFrame`);
    if (!/from '\.\/encoding'/.test(src) || !/\bENCODING\[/.test(src)) problems.push(`${name} does not take its marks from ENCODING`);
    if (/['"]recharts/.test(src)) problems.push(`${name} draws with recharts`);
    if (!new RegExp(`export \\{ ${name},`).test(index)) problems.push(`the figures index does not export ${name}`);
  }
  const page = readFileSync('src/screens/ProformaBiosteam.tsx', 'utf8');
  if (!/<CostWaterfall\b/.test(page) || !/<Tornado\b/.test(page)) problems.push("the BioSTEAM scenario's sections do not draw the cost breakdown and the sensitivity through the grammar");
  ok.push(`tables: cost breakdown ${rows.length}, one row per line and the run's price; CostWaterfall and Tornado stand on toTable, ENCODING and FigureFrame`);
}

if (problems.length) {
  for (const p of problems) console.error(`✗ ${p}`);
  process.exit(1);
}
for (const line of ok) console.log(`✓ ${line}`);
