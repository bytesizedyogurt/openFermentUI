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
 *    §4.R: a run that kept no unit table says so, with the train's own words
 *    for why, before it says the run names no product.
 * 7. OF-BLD-019 §3.2: CostWaterfall draws one row per TEA line and closes on
 *    the price the run solved, never a sum it made; a line with no per-unit
 *    value draws no bar; a credit runs back; every row keeps the run's
 *    provenance. CostWaterfall and Tornado each stand on the grammar (their
 *    own toTable, ENCODING, FigureFrame, no recharts), are exported from the
 *    figures index, and the BioSTEAM scenario's sections draw with them.
 * 8. OF-BLD-020 §3.3 (D14): TimeCourse draws one row per mark (every curve
 *    point, OUR's, each reading, each band point, each ceiling rule, each
 *    yield point); a simulation's curves keep its provenance, a reading is
 *    measured, a ceiling's rule keeps its own, and a yield is flagged above a
 *    ceiling only where the service said so, never by a comparison the figure
 *    makes. It stands on the grammar, and fermOS → Simulate and Forecast draw
 *    with it.
 * 9. OF-BLD-020 §4.2 (D14): OxygenBalance draws one row per hour of the
 *    simulated uptake, the vessel's transfer the one value the design gives
 *    on every row, the short hours exactly the service's intervals, every row
 *    the design's provenance; it finds no short hour of its own (rendered,
 *    it shades exactly the intervals the service named, none when it named
 *    none though the uptake rises above the transfer, §8.R); it says what
 *    would fill it when there is no uptake to draw; it stands on the grammar,
 *    is exported from the index, and fermOS → Vessel draws with it.
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
import { emptyOf as recoveryEmpty, noBar, toTable as recoveryTable } from '../src/components/figures/RecoveryByUnit';
import { bars as waterfallBars, toTable as waterfallTable } from '../src/components/figures/CostWaterfall';
import { OxygenBalance as OxygenBalanceFigure, emptyOf as oxygenEmpty, toTable as oxygenTable } from '../src/components/figures/OxygenBalance';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { fmt } from '../src/engine/units';
import { toTable as timeCourseTable, type TimeCourseProps } from '../src/components/figures/TimeCourse';
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
  // §4.R: a run with no tables names no product too; the figure says the
  // tables are missing and why, in the train's words, never that the run's
  // flowsheet prices nothing.
  const why = 'this run was kept before runs carried their tables (OF-BLD-019 §2.1); run the scenario again';
  const old = recoveryEmpty({ title: 't', product: null, units: [], provenance: 'demo', massUnit: 'kg/hr', why });
  if (!old || !/kept no unit table/.test(old.what) || /names no product/.test(old.what) || old.where !== why)
    problems.push(`a run that kept no unit table is drawn as one naming no product: ${JSON.stringify(old)}`);
  const toy = recoveryEmpty({ title: 't', product: null, units, provenance: 'demo', massUnit: 'kg/hr' });
  if (!toy || !/names no product/.test(toy.what)) problems.push('a run with units and no product does not say it names none');
  if (recoveryEmpty({ title: 't', product: 'E', units, provenance: 'demo', massUnit: 'kg/hr' }) !== null) problems.push('a train with a product and units is drawn empty');
  ok.push(`tables: recovery by unit ${rows.length}, one row per unit; a unit with no product in says why and draws no bar; a run with no unit table says so before naming no product`);
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

// 8 — OF-BLD-020 §3.3, D14: the time course of a simulation.
{
  const props: TimeCourseProps = {
    title: 't',
    t: [0, 1, 2],
    states: [
      { key: 'X', label: 'Cells (X)', unit: 'g L⁻¹', values: [0.1, 0.5, 1.2] },
      { key: 'S', label: 'Substrate (S)', unit: 'g L⁻¹', values: [50, 40, 20] },
    ],
    provenance: 'demo',
    our: { unit: 'g O2 L⁻¹ h⁻¹', values: [0, 0.1, 0.2] },
    readings: [{ key: 'X', points: [{ t: 0, value: 0.1 }, { t: 2, value: 1.1 }] }],
    bands: [{ key: 'S', t: [0, 1], low: [48, 37], high: [52, 43], provenance: 'computed' }],
    // The service flagged Yp/s above the ceiling; the achieved yield, below
    // it, carries no word, and the figure makes no comparison of its own.
    yields: {
      unit: 'g g⁻¹',
      points: [{ label: 'Yp/s, the parameter', value: 0.5, above: true }, { label: 'yield achieved', value: 0.6 }],
      ceilings: [{ label: 'Yeast9 ceiling', value: 0.47, provenance: 'computed', above: true }],
    },
  };
  const rows = timeCourseTable(props).rows;
  const marks = 2 * 3 + 3 + 2 + 2 + 1 + 2;
  if (rows.length !== marks) problems.push(`TimeCourse's table has ${rows.length} rows for ${marks} marks`);
  if (rows.some((r) => r.some((c) => /NaN|Infinity/.test(String(c))))) problems.push('a TimeCourse cell holds NaN or Infinity');
  const curves = rows.filter((r) => String(r[1]).startsWith('computed curve'));
  if (curves.length !== 9 || curves.some((r) => r[5] !== 'demo')) problems.push("a simulation's curves lose its provenance in TimeCourse's table");
  if (rows.filter((r) => r[1] === 'reading').some((r) => r[5] !== 'measured')) problems.push('a reading drawn against a simulation is not measured');
  const rule = rows.find((r) => r[1] === 'ceiling, a rule');
  if (!rule || rule[5] !== 'computed') problems.push("a ceiling's rule does not keep its own provenance");
  const yps = rows.find((r) => r[0] === 'Yp/s, the parameter');
  const achieved = rows.find((r) => r[0] === 'yield achieved');
  if (!yps || !/flagged, not clamped/.test(String(yps[1])) || yps[3] !== '0.5') problems.push('Yp/s above a ceiling is not flagged, or is moved');
  if (!achieved || /flagged/.test(String(achieved[1]))) problems.push('TimeCourse flags a yield the service did not flag: it compares on its own');
  const src = readFileSync('src/components/figures/TimeCourse.tsx', 'utf8');
  if (!/export function toTable\(/.test(src)) problems.push('TimeCourse exports no toTable');
  if (!/from '\.\/FigureFrame'/.test(src) || !/<FigureFrame\b/.test(src)) problems.push('TimeCourse is not framed by FigureFrame');
  if (!/from '\.\/encoding'/.test(src) || !/\bENCODING\[/.test(src)) problems.push('TimeCourse does not take its marks from ENCODING');
  if (/['"]recharts/.test(src)) problems.push('TimeCourse draws with recharts');
  if (!/export \{ TimeCourse,/.test(readFileSync('src/components/figures/index.ts', 'utf8'))) problems.push('the figures index does not export TimeCourse');
  for (const screen of ['src/screens/FermOSSimulate.tsx', 'src/screens/FermOSForecast.tsx'])
    if (!/<TimeCourse\b/.test(readFileSync(screen, 'utf8'))) problems.push(`${screen} does not draw its simulation through TimeCourse`);
  ok.push(`tables: time course ${rows.length}, one row per mark; curves keep the simulation's provenance, a ceiling's rule its own, and only the service's flag rings a yield`);
}

// 9 — OF-BLD-020 §4.2: the oxygen balance, on the grammar.
{
  const t = [0, 1, 2, 3, 4];
  const our = [0.5, 1.5, 2.5, 1.5, 0.5];
  const props = { title: 't', t, our, otr: 2, unit: 'mmol L⁻¹ h⁻¹', short: [[1.5, 2.5]], provenance: 'demo' as const };
  const rows = oxygenTable(props).rows;
  if (rows.length !== t.length) problems.push(`OxygenBalance's table has ${rows.length} rows for ${t.length} hours of uptake`);
  if (rows.some((r) => r[5] !== 'demo')) problems.push("an OxygenBalance row loses the design's provenance");
  if (rows.some((r) => r.some((c) => /NaN|Infinity/.test(String(c))))) problems.push('an OxygenBalance cell holds NaN or Infinity');
  if (rows.some((r) => r[2] !== fmt(2))) problems.push("OxygenBalance's transfer is not the design's one value on every row");
  if (rows.map((r) => r[4]).join() !== 'no,no,yes,no,no') problems.push(`OxygenBalance's short hours are not the service's intervals (${rows.map((r) => r[4]).join()})`);
  // The service said nothing is short: the figure finds no short hour of its own, though the uptake rises above the rule.
  if (oxygenTable({ ...props, short: [] }).rows.some((r) => r[4] === 'yes')) problems.push('OxygenBalance marks a short hour the service did not name');
  if (!oxygenEmpty({ ...props, t: [0], our: [1] }) || !oxygenEmpty({ ...props, our: [1, 2] }) || oxygenEmpty(props) !== null)
    problems.push('OxygenBalance draws an uptake it does not have, or calls a whole one empty');
  const src = readFileSync('src/components/figures/OxygenBalance.tsx', 'utf8');
  if (!/export function toTable\(/.test(src)) problems.push('OxygenBalance exports no toTable');
  if (!/from '\.\/FigureFrame'/.test(src) || !/<FigureFrame\b/.test(src)) problems.push('OxygenBalance is not framed by FigureFrame');
  if (!/from '\.\/encoding'/.test(src) || !/\bENCODING\[/.test(src)) problems.push('OxygenBalance does not take its marks from ENCODING');
  if (/['"]recharts/.test(src)) problems.push('OxygenBalance draws with recharts');
  if (/our\[[^\]]*\]\s*[<>]=?\s*props\.otr|props\.otr\s*[<>]=?\s*props\.our|\.otr\s*[<>]/.test(src)) problems.push('OxygenBalance compares the uptake with the transfer itself: the short hours are the service\'s');
  // §8.R (finding 9): the drawing is held by what it draws, not by a spelling
  // of its source. Rendered with the uptake above the transfer and the
  // service naming no short hour, it shades nothing; with one interval named,
  // exactly one; with two, two. A figure that found short hours of its own,
  // however it spelled the comparison, shades where the service did not.
  const shaded = (p: typeof props) =>
    (renderToStaticMarkup(createElement(OxygenBalanceFigure, p)).match(/data-testid="oxygen-short"/g) ?? []).length;
  const drawn = [shaded({ ...props, short: [] }), shaded(props), shaded({ ...props, short: [[0.5, 1], [2.5, 3.5]] })];
  if (drawn.join() !== '0,1,2') problems.push(`OxygenBalance shades hours the service did not name: ${drawn.join(', ')} shaded where it named 0, 1 and 2`);
  if (!/export \{ OxygenBalance,/.test(readFileSync('src/components/figures/index.ts', 'utf8'))) problems.push('the figures index does not export OxygenBalance');
  if (!/<OxygenBalance\b/.test(readFileSync('src/screens/FermOSVessel.tsx', 'utf8'))) problems.push('fermOS → Vessel does not draw the oxygen balance through the grammar');
  ok.push(`tables: oxygen balance ${rows.length}, one row per hour of uptake, the transfer the design's value, the short hours the service's; OxygenBalance stands on toTable, ENCODING and FigureFrame`);
}

if (problems.length) {
  for (const p of problems) console.error(`✗ ${p}`);
  process.exit(1);
}
for (const line of ok) console.log(`✓ ${line}`);
