/**
 * Seed invariant checker (BUILD-SPEC.md "Hard invariants").
 * Run with `pnpm check:seed` before any bundle.
 *
 * The invariants exist because the UI reads seed data structurally: the reader
 * locates extraction spans by searching for `quote` inside the section text, so
 * a quote that isn't present silently loses its highlight rather than erroring.
 */
import { PAPERS } from '../src/data/papers';
import { RECORDS } from '../src/data/records';
import { RUN_OUTPUTS } from '../src/data/runOutputs';
import { STRAINS } from '../src/data/strains';
import { PROTOCOLS } from '../src/data/protocols';
import { SCENARIOS, COST_MODELS } from '../src/data/scenarios';
import { FLOWS, SUGGESTED_PROMPTS } from '../src/data/flows';
import { MODULES } from '../src/data/learn';
import { COLLECTIONS, ACTIVITY, SEED_SESSIONS } from '../src/data/misc';
import { ONTOLOGY_BY_ID } from '../src/data/ontology';
import { toSI, normalizeUnit, convert } from '../src/engine/units';
import { buildGrid } from '../src/engine/grids';
import { computeRunMetrics } from '../src/engine/metrics';

const errors: string[] = [];
const warnings: string[] = [];
const fail = (m: string) => errors.push(m);
const warn = (m: string) => warnings.push(m);

const paperIds = new Set(PAPERS.map((p) => p.id));
const recordIds = new Set(RECORDS.map((r) => r.id));
const strainIds = new Set(STRAINS.map((s) => s.id));
const protocolIds = new Set(PROTOCOLS.map((p) => p.id));

// ── 1. quote is a verbatim substring of its section text ────────────────
for (const r of RECORDS) {
  const paper = PAPERS.find((p) => p.id === r.paperId);
  if (!paper) {
    fail(`${r.id}: paperId ${r.paperId} does not resolve`);
    continue;
  }
  const section = paper.sections.find((s) => s.id === r.sectionId);
  if (!section) {
    fail(`${r.id}: sectionId ${r.sectionId} not found in ${r.paperId}`);
    continue;
  }
  if (!section.text.includes(r.quote)) {
    fail(
      `${r.id}: quote is not a verbatim substring of ${r.paperId}/${r.sectionId}\n      quote: "${r.quote.slice(0, 90)}"`,
    );
  }
}

// ── 2. references resolve ──────────────────────────────────────────────
for (const p of PROTOCOLS) {
  for (const v of p.versions) {
    for (const m of v.materials) {
      if (m.sourceRecordId && !recordIds.has(m.sourceRecordId))
        fail(`${p.id}@${v.version}: material "${m.name}" sourceRecordId ${m.sourceRecordId} unresolved`);
    }
    for (const ref of v.references) {
      if (ref.paperId && !paperIds.has(ref.paperId))
        fail(`${p.id}@${v.version}: reference paperId ${ref.paperId} unresolved`);
      if (ref.recordId && !recordIds.has(ref.recordId))
        fail(`${p.id}@${v.version}: reference recordId ${ref.recordId} unresolved`);
    }
    for (const s of v.steps) {
      for (const ref of s.refs ?? []) {
        if (!paperIds.has(ref) && !recordIds.has(ref))
          fail(`${p.id}@${v.version} step ${s.id}: ref ${ref} unresolved`);
      }
      // {{qty:Name}} placeholders must name a real material
      for (const match of s.text.matchAll(/\{\{(?:qty|stock):([^}]+)\}\}/g)) {
        if (!v.materials.some((m) => m.name === match[1]))
          fail(`${p.id}@${v.version} step ${s.id}: placeholder material "${match[1]}" not in materials`);
      }
    }
  }
  if (!p.versions.some((v) => v.version === p.currentVersion))
    fail(`${p.id}: currentVersion ${p.currentVersion} is not among its versions`);
  for (const o of p.organisms) if (!strainIds.has(o)) warn(`${p.id}: organism "${o}" is not a seeded strain`);
}

for (const s of SCENARIOS) {
  for (const a of s.assumptions) {
    if (a.recordId && !recordIds.has(a.recordId))
      fail(`${s.id}: assumption "${a.label}" recordId ${a.recordId} unresolved`);
    if (a.recordId && a.provenance === 'demo')
      warn(`${s.id}: assumption "${a.label}" links a record but is marked demo`);
  }
  for (const d of s.dims) {
    if (d.sourceRecordId && !recordIds.has(d.sourceRecordId))
      fail(`${s.id}: dim ${d.key} sourceRecordId ${d.sourceRecordId} unresolved`);
  }
  if (!COST_MODELS.some((m) => m.modelId === s.modelId))
    fail(`${s.id}: modelId ${s.modelId} has no cost model`);
}

for (const c of COLLECTIONS)
  for (const pid of c.paperIds) if (!paperIds.has(pid)) fail(`${c.id}: paperId ${pid} unresolved`);

for (const sess of SEED_SESSIONS)
  if (sess.scope?.kind === 'paper' && !paperIds.has(sess.scope.id))
    fail(`${sess.id}: scope paper ${sess.scope.id} unresolved`);

// chips inside authored markdown
const CHIP_RE = /\[\[([A-Za-z0-9\-]+)\]\]/g;
const checkChips = (text: string, where: string) => {
  for (const m of text.matchAll(CHIP_RE)) {
    const id = m[1];
    if (!paperIds.has(id) && !recordIds.has(id)) fail(`${where}: chip [[${id}]] unresolved`);
  }
};
for (const f of FLOWS) {
  checkChips(f.answerMd, `flow ${f.id}`);
  for (const tc of f.toolCalls)
    for (const hit of tc.retrieval ?? []) {
      const paper = PAPERS.find((p) => p.id === hit.paperId);
      if (!paper) fail(`flow ${f.id}: retrieval paperId ${hit.paperId} unresolved`);
      else {
        const sec = paper.sections.find((s) => s.id === hit.sectionId);
        if (!sec) fail(`flow ${f.id}: retrieval section ${hit.paperId}/${hit.sectionId} unresolved`);
        else if (!sec.text.includes(hit.snippet.replace(/…$/, '').trim()))
          warn(`flow ${f.id}: retrieval snippet is not verbatim in ${hit.paperId}/${hit.sectionId}`);
      }
    }
  for (const opt of f.clarify?.options ?? [])
    if (!FLOWS.some((x) => x.id === opt.flowId)) fail(`flow ${f.id}: clarify routes to unknown flow ${opt.flowId}`);
  for (const fu of f.followups) {
    if (fu.startsWith('flow:')) {
      const target = fu.slice(5).split('|')[0];
      if (!FLOWS.some((x) => x.id === target)) fail(`flow ${f.id}: followup routes to unknown flow ${target}`);
    }
  }
}
for (const prompt of SUGGESTED_PROMPTS) {
  const hit = FLOWS.some((f) =>
    f.triggers.some((t) => {
      const a = t.toLowerCase().replace(/[^a-z0-9 ]/g, '');
      const b = prompt.toLowerCase().replace(/[^a-z0-9 ]/g, '');
      return a.includes(b) || b.includes(a) || a === b;
    }),
  );
  if (!hit) warn(`suggested prompt has no exact trigger match: "${prompt}"`);
}

for (const mod of MODULES)
  for (const lesson of mod.lessons) {
    for (const b of lesson.blocks) if (b.kind === 'prose') checkChips(b.md, `${mod.id}/${lesson.id}`);
    for (const q of lesson.checkpoint) {
      if (q.kind === 'mc' && (q.answerIndex === undefined || !q.options?.length))
        fail(`${mod.id}/${lesson.id}/${q.id}: mc question missing options or answerIndex`);
      if (q.kind === 'numeric' && !q.answer)
        fail(`${mod.id}/${lesson.id}/${q.id}: numeric question missing answer`);
      if (q.kind === 'numeric' && q.answer && q.answer.unit !== '' && normalizeUnit(q.answer.unit) === null)
        fail(`${mod.id}/${lesson.id}/${q.id}: answer unit "${q.answer.unit}" not recognized by the converter`);
      if (q.evidenceChip && !paperIds.has(q.evidenceChip) && !recordIds.has(q.evidenceChip))
        fail(`${mod.id}/${lesson.id}/${q.id}: evidenceChip ${q.evidenceChip} unresolved`);
    }
  }

for (const a of ACTIVITY) {
  if (!a.href) continue;
  const path = a.href.replace(/^#/, '');
  const known = /^\/(|ask|library|extract|organisms|protocols|simulate|learn|settings)/.test(path);
  if (!known) warn(`activity href does not look like a real route: ${a.href}`);
}

// ── 3. si equals the converter's output ────────────────────────────────
for (const r of RECORDS) {
  if (normalizeUnit(r.unit) === null) {
    fail(`${r.id}: unit "${r.unit}" is not recognized by the converter`);
    continue;
  }
  const expect = toSI(r.value, r.unit);
  if (Math.abs(expect.value - r.si.value) > 1e-9 || expect.unit !== r.si.unit)
    fail(`${r.id}: si mismatch — expected ${expect.value} ${expect.unit}, got ${r.si.value} ${r.si.unit}`);

  const def = ONTOLOGY_BY_ID[r.field];
  if (!def) {
    fail(`${r.id}: field "${r.field}" is not in the ontology`);
    continue;
  }
  if (def.canonicalUnit !== '') {
    try {
      const canonical = convert(r.value, r.unit, def.canonicalUnit);
      if (canonical < def.range[0] || canonical > def.range[1])
        warn(
          `${r.id}: ${r.field} = ${canonical.toPrecision(3)} ${def.canonicalUnit} is outside the ontology range ${def.range[0]}–${def.range[1]}`,
        );
    } catch {
      fail(`${r.id}: unit "${r.unit}" is not dimensionally compatible with ${def.canonicalUnit}`);
    }
  }
  if (r.organism && !strainIds.has(r.organism)) warn(`${r.id}: organism "${r.organism}" is not a seeded strain`);
}

// ── 4. run outputs reference only gold records ─────────────────────────
const goldIds = new Set(RECORDS.filter((r) => r.gold).map((r) => r.id));
for (const run of RUN_OUTPUTS) {
  for (const res of run.results)
    if (!goldIds.has(res.goldRecordId))
      fail(`run ${run.run}: result references ${res.goldRecordId}, which is not a gold record`);
  const covered = new Set(run.results.map((r) => r.goldRecordId));
  if (covered.size !== goldIds.size)
    warn(`run ${run.run}: covers ${covered.size} of ${goldIds.size} gold records`);
  for (const fp of run.falsePositives)
    if (!paperIds.has(fp.paperId)) fail(`run ${run.run}: false positive ${fp.id} paperId unresolved`);
}

// ── 5. grid dims ascending; grids finite and positive ──────────────────
for (const m of COST_MODELS) {
  for (const d of m.dims) {
    for (let i = 1; i < d.values.length; i++)
      if (d.values[i] <= d.values[i - 1]) fail(`model ${m.modelId}: dim ${d.key} values are not ascending`);
  }
  const grid = buildGrid(m);
  const expected = m.dims.reduce((n, d) => n * d.values.length, 1);
  if (grid.msp.length !== expected)
    fail(`model ${m.modelId}: grid length ${grid.msp.length} != product of dims ${expected}`);
  let bad = 0;
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < grid.msp.length; i++) {
    const v = grid.msp[i];
    if (!isFinite(v) || v <= 0) bad++;
    min = Math.min(min, v);
    max = Math.max(max, v);
  }
  if (bad > 0) fail(`model ${m.modelId}: ${bad} grid points are non-finite or non-positive`);
  else console.log(`  model ${m.modelId}: MSP range $${min.toFixed(1)}–$${max.toFixed(1)}/kg over ${expected} points`);
  // waterfall must sum to msp at every grid point
  for (let i = 0; i < grid.msp.length; i += Math.max(1, Math.floor(grid.msp.length / 20))) {
    const sum = Object.values(grid.costLines).reduce((s, arr) => s + arr[i], 0);
    if (Math.abs(sum - grid.msp[i]) > 1e-6)
      fail(`model ${m.modelId}: cost lines do not sum to MSP at grid index ${i}`);
  }
}

// ── report ─────────────────────────────────────────────────────────────
console.log('\nopenFerment seed check');
console.log('──────────────────────');
console.log(`  papers            ${PAPERS.length} (${PAPERS.filter((p) => p.ingest === 'complete').length} ingested, ${PAPERS.filter((p) => p.ingest === 'shelf').length} on the demo shelf)`);
console.log(`  sections          ${PAPERS.reduce((n, p) => n + p.sections.length, 0)}`);
console.log(`  records           ${RECORDS.length} (${RECORDS.filter((r) => r.status === 'verified').length} verified, ${RECORDS.filter((r) => r.status === 'unverified').length} unverified, ${RECORDS.filter((r) => r.status === 'rejected').length} rejected)`);
console.log(`  gold set          ${goldIds.size} across ${new Set(RECORDS.filter((r) => r.gold).map((r) => r.paperId)).size} papers`);
console.log(`  strains           ${STRAINS.length}`);
console.log(`  protocols         ${PROTOCOLS.length} (${PROTOCOLS.reduce((n, p) => n + p.versions.length, 0)} versions, ${PROTOCOLS.reduce((n, p) => n + p.versions.reduce((m, v) => m + v.steps.length, 0), 0)} steps)`);
console.log(`  scenarios         ${SCENARIOS.length} over ${COST_MODELS.length} cost models`);
console.log(`  chat flows        ${FLOWS.length}`);
console.log(`  learn modules     ${MODULES.length} (${MODULES.reduce((n, m) => n + m.lessons.length, 0)} lessons, ${MODULES.reduce((n, m) => n + m.lessons.reduce((k, l) => k + l.checkpoint.length, 0), 0)} checkpoint questions)`);

for (const run of RUN_OUTPUTS) {
  const m = computeRunMetrics(run, RECORDS);
  console.log(
    `  extractor ${run.run.padEnd(5)}   P ${m.micro.precision.toFixed(3)}  R ${m.micro.recall.toFixed(3)}  F1 ${m.micro.f1.toFixed(3)}`,
  );
}

if (warnings.length) {
  console.log(`\n⚠ ${warnings.length} warning(s):`);
  for (const w of warnings.slice(0, 40)) console.log(`  - ${w}`);
  if (warnings.length > 40) console.log(`  … and ${warnings.length - 40} more`);
}

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors.slice(0, 60)) console.error(`  - ${e}`);
  if (errors.length > 60) console.error(`  … and ${errors.length - 60} more`);
  process.exit(1);
}

console.log('\n✓ All seed invariants hold.\n');
