/**
 * Seed invariant checker (BUILD-SPEC.md "Hard invariants").
 * Run with `pnpm check:seed` before any bundle.
 *
 * The invariants exist because the UI reads seed data structurally: the reader
 * locates extraction spans by searching for `quote` inside the section text, so
 * a quote that isn't present silently loses its highlight rather than erroring.
 */
import type { Provenance } from '../src/data/types';
import { PAPERS } from '../src/data/papers';
import { RECORDS } from '../src/data/records';
import { RUN_OUTPUTS } from '../src/data/runOutputs';
import { STRAINS } from '../src/data/strains';
import { PRODUCTS } from '../src/data/products';
import { RUNBOOKS } from '../src/data/runbooks';
import { CLEARANCE_FINDINGS } from '../src/data/clearanceFindings';
import { COMPONENTS, FULL_NAME, LAYERS, UNNAMED, isBuilt } from '../src/data/components';
import { ALL_SURFACES, ELEVEN, RAIL, REDIRECTS, SUB_VIEWS, redirectFor } from '../src/data/nav';
import { readFileSync, existsSync } from 'node:fs';
import { lockIntact, runbookLockHash, shouldBeLocked } from '../src/engine/lock';
import { PROVENANCE_LABEL, PROVENANCE_RANK, aggregateExclusion, tickClass } from '../src/store';
import { provMeta } from '../src/components/Provenance';
import { JURISDICTIONS } from '../src/engine/clearance';
import {
  CLEARANCE_STATES,
  PATHWAYS,
  REGULATORY_PATHWAYS,
  SCALES,
  STORAGE_FORMATS,
  UNIT_OPERATIONS,
} from '../src/data/vocabulary';
import { PROTOCOLS } from '../src/data/protocols';
import { SCENARIOS, COST_MODELS } from '../src/data/scenarios';
import { FLOWS, SUGGESTED_PROMPTS } from '../src/data/flows';
import { STRAIN_ALIASES } from '../src/data/strains';
import { MODULES } from '../src/data/learn';
import { COLLECTIONS, ACTIVITY, SEED_SESSIONS } from '../src/data/misc';
import { ONTOLOGY_BY_ID } from '../src/data/ontology';
import { toSI, normalizeUnit, convert, explainRefusal } from '../src/engine/units';
import { buildGrid } from '../src/engine/grids';

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
    if (a.paperId && !paperIds.has(a.paperId))
      fail(`${s.id}: assumption "${a.label}" paperId ${a.paperId} unresolved`);
    if ((a.recordId || a.paperId) && a.provenance === 'demo')
      warn(`${s.id}: assumption "${a.label}" cites a source but is marked demo`);
    if (!a.recordId && !a.paperId && a.provenance !== 'demo' && a.provenance !== 'industry-estimate')
      warn(`${s.id}: assumption "${a.label}" claims provenance '${a.provenance}' with no source`);
  }
  for (const d of s.dims) {
    if (d.sourceRecordId && !recordIds.has(d.sourceRecordId))
      fail(`${s.id}: dim ${d.key} sourceRecordId ${d.sourceRecordId} unresolved`);
    if (d.paperId && !paperIds.has(d.paperId))
      fail(`${s.id}: dim ${d.key} paperId ${d.paperId} unresolved`);
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

// ── 3. record integrity for the real corpus ────────────────────────────
const strainIdsCanonical = new Set(Object.values(STRAIN_ALIASES));
for (const r of RECORDS) {
  const def = ONTOLOGY_BY_ID[r.field];
  if (!def) {
    fail(`${r.id}: field "${r.field}" is not in the ontology`);
    continue;
  }

  // Categorical fields carry a string; numeric fields must not.
  if (def.categorical) {
    if (typeof r.value !== 'string')
      fail(`${r.id}: ${r.field} is categorical but the value is not a string`);
  } else {
    if (typeof r.value !== 'number') {
      fail(`${r.id}: ${r.field} is numeric but the value is a string`);
      continue;
    }
    if (normalizeUnit(r.unit) === null) {
      fail(`${r.id}: unit "${r.unit}" is not recognized by the converter`);
      continue;
    }
    const expect = toSI(r.value, r.unit);
    if (Math.abs(expect.value - r.si.value) > 1e-9 || expect.unit !== r.si.unit)
      fail(`${r.id}: si mismatch — expected ${expect.value} ${expect.unit}, got ${r.si.value} ${r.si.unit}`);

    if (def.canonicalUnit !== '') {
      try {
        const canonical = convert(r.value, r.unit, def.canonicalUnit);
        if (canonical < def.range[0] || canonical > def.range[1])
          warn(
            `${r.id}: ${r.field} = ${canonical.toPrecision(3)} ${def.canonicalUnit} is outside the ontology range ${def.range[0]}–${def.range[1]}`,
          );
      } catch {
        const why = explainRefusal(r.unit, def.canonicalUnit);
        // A refusal the engine can EXPLAIN is the guardrail working, not a
        // defect in the seed: recording a cost in EUR is legitimate, and
        // declining to convert it without a dated rate is the correct
        // behaviour. Only an unexplained dimension mismatch is a real fault.
        if (why)
          warn(
            `${r.id}: ${def.name} recorded in "${r.unit}", which the engine will not convert to ${def.canonicalUnit} — ${why}`,
          );
        else
          fail(
            `${r.id}: unit "${r.unit}" is not compatible with ${def.canonicalUnit} (${def.name})`,
          );
      }
    }
  }

  // OF-COR-001 §17 Rule 1 — a PTM or functional value without its method is
  // not interpretable. 'undetermined' is a legitimate answer; absent is not.
  if (def.requiresMethod && !r.method)
    fail(`${r.id}: ${r.field} requires a \`method\` (use 'undetermined' if the source never reported one)`);

  // §19 first trap — a residue position without its numbering convention
  // mislocates every phospho-site by 15.
  if (r.field === 'phospho_site_position' && !r.numbering)
    fail(`${r.id}: phospho_site_position requires \`numbering\` ('mature' or 'precursor')`);

  // §19 fifth trap — a record that recites someone else's measurement must say
  // whose, or aggregates silently double-count it.
  if (r.isPrimary === false && !r.citesRecordId)
    warn(`${r.id}: marked non-primary but does not name the record it cites`);
  if (r.citesRecordId && !recordIds.has(r.citesRecordId))
    fail(`${r.id}: citesRecordId ${r.citesRecordId} does not resolve`);
  if (r.citesRecordId && r.isPrimary !== false)
    fail(`${r.id}: cites another record but is still marked primary`);

  // §16 O8 — market figures are never evidence.
  if (r.provenance === 'industry-estimate' && r.gold)
    fail(`${r.id}: an industry estimate must never be in the gold set`);

  // A curated value must say where it was transcribed from.
  if (r.provenance === 'curated' && !r.curationRef)
    warn(`${r.id}: curated but carries no curationRef`);

  // §19 third trap — strain names must normalise, or measurements on different
  // organisms get silently merged.
  if (r.organism && !strainIdsCanonical.has(r.organism))
    warn(`${r.id}: organism "${r.organism}" is not a canonical strain id`);

  if (r.range && typeof r.value === 'number') {
    if (r.range.low > r.range.high) fail(`${r.id}: range low > high`);
    else if (r.value < r.range.low || r.value > r.range.high)
      warn(`${r.id}: point value ${r.value} sits outside its own stated range`);
  }
}

// No fabricated authorship: an entry either names real authors or names none.
for (const p of PAPERS) {
  if (p.authors.some((a) => !a.trim()))
    fail(`${p.id}: empty author string — use [] and verifyNeeded rather than a blank`);
  if (p.textSource === 'curation-note' && p.ingest !== 'catalogued')
    fail(`${p.id}: curation-note text must be marked ingest 'catalogued'`);
  if (p.sections.length === 0) fail(`${p.id}: has no sections`);
}

// ── 4. run outputs (may legitimately be empty) ─────────────────────────
const goldIds = new Set(RECORDS.filter((r) => r.gold).map((r) => r.id));
if (RUN_OUTPUTS.length === 0) {
  console.log(
    '  note: no extractor runs — nothing has been ingested, so nothing has been scored (expected for corpus v1)',
  );
} else {
  for (const run of RUN_OUTPUTS) {
    for (const res of run.results)
      if (!goldIds.has(res.goldRecordId))
        fail(`run ${run.run}: result references ${res.goldRecordId}, which is not a gold record`);
    for (const fp of run.falsePositives)
      if (!paperIds.has(fp.paperId)) fail(`run ${run.run}: false positive ${fp.id} paperId unresolved`);
  }
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


// ── 6. molecules, vocabulary and runbooks (OF-BLD-005 §9) ──────────────
//
// These already hold. The point of writing them down is that they keep
// holding: a product whose default host does not resolve renders a strain
// page link into nothing, and a runbook pointing at a molecule that is not
// there renders a detail page with an empty clearance summary. Both fail
// quietly in the UI rather than loudly, which is exactly the class of bug a
// seed check is for.
const productIds = new Set(PRODUCTS.map((p) => p.id));
const vocab = {
  unitOperationIds: new Set(UNIT_OPERATIONS.map((x) => x.id)),
  storageIds: new Set(STORAGE_FORMATS.map((x) => x.id)),
  regulatoryIds: new Set(REGULATORY_PATHWAYS.map((x) => x.id)),
  pathwayIds: new Set(PATHWAYS.map((x) => x.id)),
} as const;
// Widened to string: these sets are tested against free-text stage values
// as well as typed product fields.
const clearanceIds = new Set<string>(CLEARANCE_STATES.map((x) => x.id));
const scaleIds = new Set(SCALES.map((x) => x.id));

for (const p of PRODUCTS) {
  if (!strainIds.has(p.defaultStrainId))
    fail(`product ${p.id}: defaultStrainId ${p.defaultStrainId} does not resolve against STRAINS`);
  for (const [field, allowed] of Object.entries(vocab)) {
    for (const id of p[field as keyof typeof vocab]) {
      if (!allowed.has(id)) fail(`product ${p.id}: ${field} entry "${id}" is not in the vocabulary`);
    }
  }
  if (!clearanceIds.has(p.clearanceState))
    fail(`product ${p.id}: clearanceState "${p.clearanceState}" is not a known state`);
  if (!scaleIds.has(p.scaleId)) fail(`product ${p.id}: scaleId "${p.scaleId}" is not a known scale`);

  // §4 — one provenance vocabulary, and the economics half never counts as
  // evidence. A product marked anything but 'industry-estimate' here would
  // slip market framing past aggregateExclusion() into a median.
  if (p.provenance !== 'demo')
    fail(`product ${p.id}: provenance is "${p.provenance}" — catalogue entries are modeled, not measured`);
  if (p.economicsProvenance !== 'industry-estimate')
    fail(
      `product ${p.id}: economicsProvenance is "${p.economicsProvenance}" — value bands are market framing and must be excluded from aggregates`,
    );
  if (p.unitOperationIds.length === 0)
    warn(`product ${p.id}: declares no unit operations, so its process train will be empty`);
}

for (const r of RUNBOOKS) {
  if (r.productId && !productIds.has(r.productId))
    fail(`runbook ${r.id}: productId ${r.productId} does not resolve against PRODUCTS`);
  if (r.strainId && !strainIds.has(r.strainId))
    fail(`runbook ${r.id}: strainId ${r.strainId} does not resolve against STRAINS`);
  if (r.stages.length === 0) fail(`runbook ${r.id}: has no stages`);
  if (r.progressPct < 0 || r.progressPct > 100)
    fail(`runbook ${r.id}: progressPct ${r.progressPct} is outside 0-100`);
  // A complete runbook with unfinished stages, or the reverse, would make the
  // board disagree with the page it links to.
  const unfinished = r.stages.filter((st) => st.status !== 'done').length;
  if (r.status === 'complete' && unfinished > 0)
    fail(`runbook ${r.id}: marked complete but ${unfinished} stage(s) are not done`);
  if (r.progressPct === 100 && !['complete', 'cache_hit'].includes(r.status))
    warn(`runbook ${r.id}: reads 100% but its status is "${r.status}"`);
  if (r.status === 'blocked_unverified' && !r.stages.some((st) => st.status === 'blocked'))
    fail(`runbook ${r.id}: blocked_unverified but no stage is marked blocked`);
  if (r.status === 'needs_review' && !r.stages.some((st) => st.status === 'review'))
    fail(`runbook ${r.id}: needs_review but no stage is held for review`);

  // A stage `value` is free text by design, but one written as a hyphenated
  // lowercase token reads as a vocabulary id. When it does not resolve, the
  // detail page labels it rather than printing it as a finding — this surfaces
  // the same thing at seed time so it is a known gap, not a silent one.
  for (const st of r.stages) {
    if (st.value && /^[a-z]+(-[a-z]+)+$/.test(st.value) && !clearanceIds.has(st.value))
      warn(
        `runbook ${r.id} stage "${st.name}": value "${st.value}" reads as a clearance state but is not one — rendered as an unrecognised term`,
      );
  }
}

// ── 6c. the component map (OF-BLD-006 §2.3) ────────────────────────────
//
// COMPONENTS.md is the reference every future spec points at, and src/data/
// components.ts is what the UI renders. Two copies of the same table drift the
// moment somebody edits one, and the drift is invisible: the doc keeps saying
// a component lives somewhere it no longer does. So the doc is checked against
// the module, row for row, and a mismatch fails the build.
{
  const doc = 'COMPONENTS.md';
  if (!existsSync(doc)) {
    fail(`${doc} is missing — it is the canonical map §2.3 requires`);
  } else {
    const md = readFileSync(doc, 'utf8');
    // Scoped to the map section: the doc carries a second table ("Named
    // nothing yet") whose rows must not be counted as components.
    const section = (heading: string) =>
      md.split(`\n## ${heading}\n`)[1]?.split('\n## ')[0] ?? '';
    const tableRows = (heading: string) =>
      section(heading)
        .split('\n')
        .filter((l) => l.startsWith('| ') && !/^\|\s*-+/.test(l))
        .slice(1)
        .map((l) => l.split('|').map((c) => c.trim()).filter(Boolean));

    const rows = tableRows('The full component map');

    if (rows.length !== COMPONENTS.length)
      fail(`${doc}: ${rows.length} component rows, but components.ts defines ${COMPONENTS.length}`);

    for (const c of COMPONENTS) {
      const display = FULL_NAME[c.name] ?? c.name;
      const row = rows.find((r) => r[0] === display);
      if (!row) {
        fail(`${doc}: no row for "${display}"`);
        continue;
      }
      if (row[1] !== c.layer)
        fail(`${doc}: "${display}" is layer "${row[1]}" in the doc, "${c.layer}" in components.ts`);

      const docPaths = row[2] === 'not built' ? [] : row[2].split(',').map((x) => x.replace(/`/g, '').trim());
      const codePaths = c.livesIn;
      if (docPaths.join(' | ') !== codePaths.join(' | '))
        fail(
          `${doc}: "${display}" paths disagree\n      doc:  ${docPaths.join(', ') || '(none)'}\n      code: ${codePaths.join(', ') || '(none)'}`,
        );

      const docSurface = row[3] === '\u2014' ? null : row[3];
      if (docSurface !== c.surfacedAs)
        fail(
          `${doc}: "${display}" is surfaced as "${docSurface}" in the doc, "${c.surfacedAs}" in components.ts`,
        );
    }
    // The prose count is checked as well as the table. A doc that says "six"
    // over a table of seven is the kind of error a reader trusts and a
    // reviewer skims past.
    // §3 — the unnamed table. The unit engine lost its name when Primer moved
    // to the Learn screens, and it is on the map as unnamed rather than
    // quietly dropped; a component that vanishes from the map still exists in
    // the code, which is exactly the drift this doc is supposed to prevent.
    const unnamedRows = tableRows('Named nothing yet');
    if (unnamedRows.length !== UNNAMED.length)
      fail(`${doc}: ${unnamedRows.length} unnamed rows, but components.ts declares ${UNNAMED.length}`);
    for (const u of UNNAMED) {
      const row = unnamedRows.find((r) => r[0].replace(/_/g, '') === u.what);
      if (!row) {
        fail(`${doc}: no unnamed row for "${u.what}"`);
        continue;
      }
      if (row[1] !== u.layer)
        fail(`${doc}: "${u.what}" is layer "${row[1]}" in the doc, "${u.layer}" in components.ts`);
      const docPaths = row[2].split(',').map((x) => x.replace(/`/g, '').trim());
      if (docPaths.join(' | ') !== u.livesIn.join(' | '))
        fail(`${doc}: "${u.what}" paths disagree — doc ${docPaths.join(', ')}, code ${u.livesIn.join(', ')}`);
    }
    for (const c of COMPONENTS)
      for (const u of UNNAMED)
        for (const path of u.livesIn)
          if (c.livesIn.includes(path))
            fail(`${path} is claimed by both "${c.name}" and the unnamed "${u.what}"`);

    const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
    const notBuilt = COMPONENTS.filter((c) => !isBuilt(c)).length;
    const claimed = md.match(/\*\*"not built" is a real entry\.\*\*\s+(\w+) of the components/i)?.[1];
    if (claimed && claimed.toLowerCase() !== WORDS[notBuilt])
      fail(
        `${doc}: prose says "${claimed} of the eighteen" have no code, but ${notBuilt} components are not built`,
      );
  }

  // Every built component must point at code that exists, or the map is a
  // promise rather than a description.
  for (const c of COMPONENTS) {
    for (const path of c.livesIn) {
      const file = path.replace(/^aggregateExclusion\(\) in /, '');
      if (!existsSync(file)) fail(`component ${c.name}: declares ${file}, which does not exist`);
    }
    if (isBuilt(c) && !c.surfacedAs)
      warn(`component ${c.name}: has code but no stated surface — how does anyone reach it?`);
    if (!isBuilt(c) && c.surfacedAs)
      fail(`component ${c.name}: claims a surface but has no code behind it`);
  }

  const layerIds = new Set(LAYERS.map((l) => l.id));
  for (const c of COMPONENTS)
    if (!layerIds.has(c.layer)) fail(`component ${c.name}: layer "${c.layer}" is not a known layer`);
}

// ── 6b. the Assay layer (OF-BLD-006 §3) ────────────────────────────────
//
// Locking is what stops the platform grading its own homework, so the seed has
// to demonstrate it working rather than merely declaring it. Three things get
// checked: that a runbook which has executed is frozen, that its hash still
// matches its content, and that every measure points at a prediction that
// exists. A dangling predictionId would silently drop a row out of the
// reconciliation, which is the one comparison the Assay layer exists to make.
for (const r of RUNBOOKS) {
  const seenPred = new Set<string>();
  for (const p of r.predictions) {
    if (seenPred.has(p.id)) fail(`runbook ${r.id}: duplicate prediction id ${p.id}`);
    seenPred.add(p.id);
    if (!p.label.trim()) fail(`runbook ${r.id}: prediction ${p.id} has no label`);
    if (!p.unit.trim()) fail(`runbook ${r.id}: prediction ${p.id} has no unit`);
    if (!p.basis.trim())
      fail(`runbook ${r.id}: prediction ${p.id} does not say what produced it`);
    if (!isFinite(p.value)) fail(`runbook ${r.id}: prediction ${p.id} value is not finite`);
  }

  const seenMeas = new Set<string>();
  for (const m of r.measurementSchema) {
    if (seenMeas.has(m.id)) fail(`runbook ${r.id}: duplicate measure id ${m.id}`);
    seenMeas.add(m.id);
    if (!m.unit.trim()) fail(`runbook ${r.id}: measure ${m.id} has no unit`);
    if (!m.timepoint.trim()) fail(`runbook ${r.id}: measure ${m.id} has no timepoint`);
    if (m.predictionId && !seenPred.has(m.predictionId))
      fail(
        `runbook ${r.id}: measure ${m.id} tests prediction ${m.predictionId}, which this runbook does not make`,
      );
  }

  // §3.3 — predictions freeze before execution.
  const mustLock = shouldBeLocked(r.status, r.progressPct);
  if (mustLock && !r.lockedAt)
    fail(
      `runbook ${r.id}: status "${r.status}" at ${r.progressPct}% but predictions are not locked — it would be grading its own homework`,
    );
  if (!mustLock && r.lockedAt)
    warn(`runbook ${r.id}: locked while still "${r.status}" — nothing has run against these yet`);

  if (r.lockedAt) {
    if (r.predictions.length === 0)
      fail(`runbook ${r.id}: locked with no predictions — freezing nothing means nothing`);
    // The seed derives its hashes at module load, so comparing them back is
    // near-vacuous here — it catches a broken derivation and nothing else.
    // Runtime drift is guarded in the store, where content can actually be
    // mutated after locking.
    if (!r.lockHash) fail(`runbook ${r.id}: locked but carries no content hash`);
    else if (!lockIntact(r)) fail(`runbook ${r.id}: stored hash does not match stored content`);
  } else if (r.lockHash) {
    fail(`runbook ${r.id}: carries a lockHash but is not locked`);
  }
}

// The hash itself is worth testing, because every lock check downstream trusts
// it. Three properties: deterministic, sensitive to content, and indifferent to
// the order keys happen to be written in — the last one matters because a hash
// that changed when someone reordered two properties would cry wolf forever.
{
  const p0 = [
    { id: 'a', label: 'Titre', value: 8, unit: 'g/L', confidence: 'medium' as const, basis: 'model' },
  ];
  const m0 = [
    { id: 'm', label: 'Titre', unit: 'g/L', timepoint: 'harvest', predictionId: 'a' },
  ];
  if (runbookLockHash(p0, m0) !== runbookLockHash(p0, m0))
    fail('lock hash: not deterministic across calls');

  const bumped = [{ ...p0[0], value: 8.1 }];
  if (runbookLockHash(p0, m0) === runbookLockHash(bumped, m0))
    fail('lock hash: a changed prediction value produced the same digest');

  const reordered = [
    { basis: 'model', unit: 'g/L', value: 8, confidence: 'medium' as const, label: 'Titre', id: 'a' },
  ];
  if (runbookLockHash(p0, m0) !== runbookLockHash(reordered, m0))
    fail('lock hash: key order in the literal changed the digest');

  if (runbookLockHash(p0, m0) === runbookLockHash(p0, []))
    fail('lock hash: dropping the measurement schema produced the same digest');
}

// ── 7. authored clearance findings (OF-BLD-005 §8) ─────────────────────
//
// Jurisdiction cells are populated ONLY from this list; everything else reads
// unknown. That makes the list the whole trust surface for the feature, so it
// is checked harder than the data around it. A finding that names no patent,
// cites no source, or claims a provenance it has not earned is worse than no
// finding at all — it puts a specific, actionable-looking verdict in front of
// somebody on the one screen where being wrong is expensive.
const jurisdictionIds = new Set(JURISDICTIONS.map((j) => j.id));
const seenFinding = new Set<string>();
for (const f of CLEARANCE_FINDINGS) {
  const where = `clearance finding ${f.productId}/${f.jurisdictionId}`;
  if (!productIds.has(f.productId)) fail(`${where}: productId does not resolve against PRODUCTS`);
  if (!jurisdictionIds.has(f.jurisdictionId))
    fail(`${where}: jurisdictionId is not a known office`);
  if (!clearanceIds.has(f.state)) fail(`${where}: state "${f.state}" is not a known clearance state`);

  const key = `${f.productId}/${f.jurisdictionId}`;
  if (seenFinding.has(key)) fail(`${where}: duplicate finding for this product and office`);
  seenFinding.add(key);

  // A finding must name what it rests on and where it was read. Without both,
  // it is an assertion, and an assertion is what this feature was rebuilt to
  // stop rendering.
  if (f.patents.length === 0) fail(`${where}: names no patent — a finding must cite what it rests on`);
  if (f.sources.length === 0) fail(`${where}: cites no source`);
  for (const src of f.sources)
    if (!/^https?:\/\//.test(src.url)) fail(`${where}: source "${src.label}" has no resolvable URL`);
  for (const pt of f.patents) {
    if (!pt.number.trim()) fail(`${where}: a patent entry has no number`);
    if (!pt.status.trim()) fail(`${where}: ${pt.number} has no status`);

    // Term expiry is arithmetic and usually decides the clearance question,
    // where a litigation outcome is contingent and may never resolve at all.
    // So the field is mandatory: a date, or an explicit null that says why it
    // is not known. Silently omitting it would let a finding lead with a
    // dispute when the patent had simply run out.
    if (pt.expiresOnTerm === undefined)
      fail(
        `${where}: ${pt.number} has no expiresOnTerm — give a date, or null with a termBasis saying why it is not established`,
      );
    if (pt.expiresOnTerm !== null && !/^\d{4}-\d{2}(-\d{2})?$/.test(pt.expiresOnTerm))
      fail(`${where}: ${pt.number} expiresOnTerm "${pt.expiresOnTerm}" is not an ISO date`);
    if (pt.expiresOnTerm === null && !pt.termBasis?.trim())
      fail(`${where}: ${pt.number} has no term date and does not say why not`);
    // A date that was computed rather than read must say so, or a reader will
    // take arithmetic for a register readout.
    if (pt.expiresOnTerm !== null && !pt.termBasis?.trim())
      warn(`${where}: ${pt.number} gives a term date with no basis — say whether it was read or computed`);
  }
  if (!f.readAt.trim()) fail(`${where}: no read date`);
  if (!f.toVerify.trim())
    fail(`${where}: does not say what would promote it to verified`);

  // 'verified' means checked against the source document. Nothing reaches that
  // from secondary reporting, so the bar is explicit rather than assumed.
  if (f.provenance === 'verified' && !/register|file wrapper|opinion|primary/i.test(f.toVerify))
    warn(
      `${where}: claims 'verified' — confirm a primary document was actually pulled, not just cited`,
    );
  if (!['curated', 'verified'].includes(f.provenance))
    fail(
      `${where}: provenance "${f.provenance}" — a jurisdiction finding must be curated or verified, never modeled`,
    );
}

// ── 6d. the measured provenance level (OF-BLD-006 §6) ──────────────────
//
// A provenance class that exists in the union but is missing from one of the
// surfaces that render it fails silently: the value shows up with an
// undefined tick class or a blank label, and nobody notices until a screenshot
// looks wrong. §6 names five places it has to land, so all five are checked.
{
  const ALL: Provenance[] = [
    'measured', 'gold', 'verified', 'curated', 'unverified', 'user', 'industry-estimate', 'demo',
  ];
  for (const p of ALL) {
    if (!PROVENANCE_LABEL[p]) fail(`provenance ${p}: no label in PROVENANCE_LABEL`);
    if (!tickClass(p)?.includes('tick-')) fail(`provenance ${p}: tickClass() returns no tick class`);
    if (!provMeta(p)) fail(`provenance ${p}: missing from META in Provenance.tsx`);
    if (PROVENANCE_RANK[p] === undefined) fail(`provenance ${p}: no entry in PROVENANCE_RANK`);
  }

  if (PROVENANCE_LABEL.measured !== 'Measured · first-party')
    fail(`provenance measured: label is "${PROVENANCE_LABEL.measured}", §6 specifies "Measured · first-party"`);

  // §6: ranks above gold. First-party data with its conditions attached beats
  // a hand-curated reading of somebody else's paper.
  if (!(PROVENANCE_RANK.measured < PROVENANCE_RANK.gold))
    fail('provenance measured: must rank above gold');

  // §6: included in aggregation. It is the strongest evidence the system can
  // hold, so an exclusion here would be exactly backwards.
  const probe = { status: 'verified', provenance: 'measured', isPrimary: true } as never;
  if (aggregateExclusion(probe) !== null)
    fail('provenance measured: held out of aggregates, but §6 says it is included');

  const css = readFileSync('src/styles.css', 'utf8');
  if (!css.includes('.tick-measured::before'))
    fail('provenance measured: no .tick-measured rule in styles.css');
}

// ── 6e. the navigation vocabulary (OF-BLD-008 §1, §10) ─────────────────
//
// THE LIST IS CLOSED: Home plus eleven destinations, twelve rail entries
// exactly. That is the one rule of OF-BLD-008 and the only place it can be
// enforced rather than remembered — a rail that quietly grows to thirteen
// looks fine in review and is the whole failure.
//
// Four other things can break the vocabulary silently, and all four are
// checked here rather than found by a user: a rail item pointing at a route
// the dispatcher does not handle, two items claiming the same chord key, a
// retired word that no longer resolves in search, and a redirect that lands
// somewhere as dead as the path it replaced.
{
  const app = readFileSync('src/App.tsx', 'utf8');
  const handled = new Set(
    [...app.matchAll(/case '([a-z]+)':/g)].map((m) => m[1]),
  );

  const seenKey = new Map<string, string>();
  for (const item of RAIL) {
    const first = item.to.split('/').filter(Boolean)[0];
    if (first && !handled.has(first))
      fail(`nav: rail item "${item.label}" points at ${item.to}, which App.tsx does not dispatch`);
    const clash = seenKey.get(item.key);
    if (clash) fail(`nav: "${item.label}" and "${clash}" both claim the chord key '${item.key}'`);
    seenKey.set(item.key, item.label);
    if (!item.descriptor) fail(`nav: "${item.label}" has no descriptor — §7 requires one per rail item`);
  }
  // Not <=, not >=. Exactly twelve, because the failure this guards against
  // is a thirteenth destination appearing rather than the rail getting long.
  if (RAIL.length !== 12)
    fail(
      `nav: ${RAIL.length} rail entries. The list is CLOSED at Home plus eleven — ` +
        'anything new lives inside one of the eleven, and the question is which ' +
        'one owns it, never whether to add a twelfth.',
    );
  if (ELEVEN.length !== 11) fail(`nav: ${ELEVEN.length} destinations besides Home, expected 11`);
  const EXPECTED_ORDER = [
    'Home', 'Intake', 'BioRepo', 'Postdoc', 'geneOS', 'fermOS',
    'pureOS', 'Proforma', 'Runbooks', 'Dominion', 'Primer', 'Guild',
  ];
  const actual = RAIL.map((r) => r.label);
  if (actual.join(' · ') !== EXPECTED_ORDER.join(' · '))
    fail(`nav: rail order is\n      ${actual.join(' · ')}\n      expected\n      ${EXPECTED_ORDER.join(' · ')}`);

  for (const item of SUB_VIEWS) {
    const first = item.to.split('/').filter(Boolean)[0];
    if (first && !handled.has(first))
      fail(`nav: "${item.label}" points at ${item.to}, which App.tsx does not dispatch`);
  }

  // §6 — the old words must still resolve. This is the list the spec names,
  // and it is checked by resolution rather than by reading the alias arrays,
  // so a word that is present but attached to the wrong surface still fails.
  // Retired words must still find their thing. Checked by resolution rather
  // than by reading the alias arrays, so a word that is present but attached
  // to the wrong surface still fails. Several words legitimately resolve to
  // two places now — "organisms" reaches both fermOS and its Organisms view —
  // so the assertion is that the RIGHT one is among them, and that the first
  // (rail before sub-view) is the destination.
  const REQUIRED_ALIASES: [string, string][] = [
    // OF-BLD-008: the five that stopped being destinations.
    ['organisms', 'fermOS'],
    ['strains', 'fermOS'],
    ['molecules', 'Dominion'],
    ['products', 'Dominion'],
    ['protocols', 'Runbooks'],
    ['run mode', 'Runbooks'],
    ['deposition', 'Runbooks'],
    ['witness', 'BioRepo'],
    ['validation', 'BioRepo'],
    // OF-BLD-006 legacy, still typed daily.
    ['ask', 'Postdoc'],
    ['library', 'BioRepo'],
    ['extract', 'Intake'],
    ['simulate', 'Proforma'],
    ['learn', 'Primer'],
    ['review', 'Guild'],
  ];
  for (const [word, label] of REQUIRED_ALIASES) {
    const hits = ALL_SURFACES.filter((sf) => sf.aliases.includes(word));
    if (hits.length === 0) fail(`nav: "${word}" resolves to nothing — it must reach ${label}`);
    else if (!hits.some((h) => h.label === label))
      fail(`nav: "${word}" resolves to ${hits.map((h) => h.label).join(', ')}, not ${label}`);
    else if (hits[0].label !== label)
      fail(
        `nav: "${word}" reaches ${label} but ${hits[0].label} is ranked first — ` +
          'the destination must outrank the view inside it',
      );
  }

  // Every sub-view is owned by one of the eleven, and the owner is real.
  const railLabels = new Set(RAIL.map((r) => r.label));
  for (const view of SUB_VIEWS) {
    const owner = RAIL.find((r) => r.label === view.owner);
    if (!owner) {
      // Bail before the path check rather than dereferencing an owner that is
      // not there: a stack trace fails the build too, and tells the reader
      // considerably less than the sentence above it would have.
      fail(`nav: "${view.label}" is owned by "${view.owner}", which is not one of the eleven`);
      continue;
    }
    if (!view.to.startsWith(owner.to + '/'))
      fail(`nav: "${view.label}" lives at ${view.to}, which is not under its owner ${owner.to}`);
  }

  // §8 — every redirect target is a path the dispatcher actually serves, and
  // no redirect target is itself redirected (which would bounce the reader).
  for (const [from, to] of Object.entries(REDIRECTS)) {
    const first = to.split('/').filter(Boolean)[0];
    if (first && !handled.has(first))
      fail(`nav: ${from} redirects to ${to}, which App.tsx does not dispatch`);
    if (redirectFor(to)) fail(`nav: ${from} redirects to ${to}, which is itself redirected`);
    if (!redirectFor(from)) fail(`nav: ${from} is in REDIRECTS but redirectFor() does not resolve it`);
  }
  // The tail has to survive, or a deep link lands on an index page and the
  // reader has to find their paper again.
  // Every retired path, resolved to where it must actually land. Written as
  // pairs rather than as prose because "no 404 from an old link" is only true
  // if somebody checks each one, and two of these moved twice.
  const LANDINGS: [string, string | null][] = [
    ['/organisms', '/fermos/organisms'],
    ['/organisms/cw15', '/fermos/organisms/cw15'],
    ['/molecules', '/dominion/molecules'],
    ['/molecules/taq-dna-polymerase', '/dominion/molecules/taq-dna-polymerase'],
    ['/protocols', '/runbooks/protocols'],
    ['/protocols/PR-TAP-01', '/runbooks/protocols/PR-TAP-01'],
    ['/protocols/PR-TAP-01/edit', '/runbooks/protocols/PR-TAP-01/edit'],
    ['/witness', '/biorepo/witness'],
    ['/depositions/dep-1', '/runbooks/depositions/dep-1'],
    // Moved twice: /library/papers → /biorepo/papers → /biorepo/paper. Longest
    // prefix wins, so this must not stop at the intermediate form.
    ['/library/papers/H4', '/biorepo/paper/H4'],
    ['/biorepo/papers/H4', '/biorepo/paper/H4'],
    ['/library/ingest', '/intake/ingest'],
    ['/biorepo/ingest', '/intake/ingest'],
    ['/extract/review', '/guild'],
    ['/extract/validation', '/biorepo/witness'],
    ['/simulate/compare', '/biorepo/compare'],
    ['/proforma/compare', '/biorepo/compare'],
    // Tail changes shape, not just prefix.
    ['/simulate/sc-s1', '/proforma/scenario/sc-s1'],
    ['/proforma/sc-s1', '/proforma/scenario/sc-s1'],
    ['/learn/m0/l0-1', '/primer/l0-1'],
    // Current paths must NOT redirect, or the reader bounces on arrival.
    ['/postdoc', null],
    ['/fermos/organisms/cw15', null],
    ['/dominion/molecules', null],
    ['/runbooks/protocols/PR-TAP-01', null],
    ['/biorepo/paper/H4', null],
    ['/proforma/scenario/sc-s1', null],
    ['/primer/l0-1', null],
    ['/geneos', null],
    ['/pureos', null],
  ];
  for (const [from, to] of LANDINGS) {
    const got = redirectFor(from);
    if (got !== to)
      fail(`nav: ${from} lands on ${got ?? '(no redirect)'}, expected ${to ?? '(no redirect)'}`);
  }

  // The screen files carry the names now (§4), so a rename that misses the
  // map leaves the map pointing at a file that is no longer there. Entries
  // that name a symbol rather than a path ("aggregateExclusion() in ...") are
  // prose and are skipped.
  const isPath = (x: string) => !x.includes(' ') && !x.includes('(');
  for (const c of COMPONENTS)
    for (const path of c.livesIn.filter(isPath))
      if (!existsSync(path)) fail(`components: "${c.name}" claims ${path}, which does not exist`);
  for (const u of UNNAMED)
    for (const path of u.livesIn.filter(isPath))
      if (!existsSync(path)) fail(`components: the unnamed "${u.what}" claims ${path}, which does not exist`);
}

// ── report ─────────────────────────────────────────────────────────────
console.log('\nopenFerment seed check');
console.log('──────────────────────');
console.log(`  papers            ${PAPERS.length} catalogued (${PAPERS.filter((p) => p.textSource === 'full-text').length} full-text, ${PAPERS.filter((p) => p.openAccess).length} open access)`);
console.log(`  threads           ${new Set(PAPERS.map((p) => p.thread)).size} · tranche 1: ${PAPERS.filter((p) => p.tranche === 1).length}, 2: ${PAPERS.filter((p) => p.tranche === 2).length}, 3: ${PAPERS.filter((p) => p.tranche === 3).length}`);
console.log(`  needs [verify]    ${PAPERS.filter((p) => p.verifyNeeded).length} author strings`);
console.log(`  sections          ${PAPERS.reduce((n, p) => n + p.sections.length, 0)}`);
console.log(`  records           ${RECORDS.length} (${RECORDS.filter((r) => r.provenance === 'curated').length} curated, ${RECORDS.filter((r) => r.provenance === 'industry-estimate').length} industry estimate)`);
console.log(`  non-primary       ${RECORDS.filter((r) => r.isPrimary === false).length} (citations of other records, excluded from aggregates)`);
console.log(`  with method       ${RECORDS.filter((r) => r.method).length}, of which ${RECORDS.filter((r) => r.method === 'undetermined').length} undetermined`);
console.log(`  gold set          ${goldIds.size} annotated (60 planned across 14 papers — pending tranche-1 ingest)`);
console.log(`  strains           ${STRAINS.length}`);
console.log(`  molecules         ${PRODUCTS.length} across ${new Set(PRODUCTS.map((p) => p.category)).size} categories, ${new Set(PRODUCTS.map((p) => p.processCode)).size} process families (all modeled)`);
console.log(`  clearance         ${PRODUCTS.filter((p) => p.clearanceState === 'blocked').length} blocked, ${PRODUCTS.filter((p) => p.clearanceState === 'unknown').length} unassessed, ${PRODUCTS.filter((p) => p.clearanceState.startsWith('clear')).length} clear`);
console.log(`  vocabulary        ${UNIT_OPERATIONS.length} unit operations, ${STORAGE_FORMATS.length} storage formats, ${REGULATORY_PATHWAYS.length} regulatory routes, ${PATHWAYS.length} pathways`);
const patentEntries = CLEARANCE_FINDINGS.flatMap((f) => f.patents);
console.log(`  patents on file   ${patentEntries.length} across ${CLEARANCE_FINDINGS.length} findings · ${patentEntries.filter((p) => p.expiresOnTerm !== null).length} with an established term date`);
console.log(`  clearance cells   ${CLEARANCE_FINDINGS.length} authored of ${PRODUCTS.length * JURISDICTIONS.length} (${PRODUCTS.length} molecules x ${JURISDICTIONS.length} offices) — every other cell reads 'not assessed'`);
const preds = RUNBOOKS.flatMap((r) => r.predictions);
console.log(`  components        ${COMPONENTS.length} in ${LAYERS.length} layers (${COMPONENTS.filter(isBuilt).length} built, ${COMPONENTS.filter((c) => !isBuilt(c)).length} named only) — COMPONENTS.md matches`);
console.log(`  predictions       ${preds.length} across ${RUNBOOKS.filter((r) => r.predictions.length > 0).length} runbooks (${preds.filter((p) => p.confidence === 'high').length} high, ${preds.filter((p) => p.confidence === 'medium').length} medium, ${preds.filter((p) => p.confidence === 'low').length} low)`);
console.log(`  measures          ${RUNBOOKS.flatMap((r) => r.measurementSchema).length}, of which ${RUNBOOKS.flatMap((r) => r.measurementSchema).filter((m) => m.predictionId === null).length} recorded without a prediction to test`);
console.log(`  locked            ${RUNBOOKS.filter((r) => r.lockedAt).length}/${RUNBOOKS.length} runbooks frozen, all hashes recomputed and matching`);
console.log(`  runbooks          ${RUNBOOKS.length} over ${new Set(RUNBOOKS.map((r) => r.status)).size} states (${RUNBOOKS.filter((r) => r.kind === 'industrial').length} industrial, ${RUNBOOKS.filter((r) => r.kind === 'research').length} research)`);
console.log(`  protocols         ${PROTOCOLS.length} (${PROTOCOLS.reduce((n, p) => n + p.versions.length, 0)} versions, ${PROTOCOLS.reduce((n, p) => n + p.versions.reduce((m, v) => m + v.steps.length, 0), 0)} steps)`);
console.log(`  scenarios         ${SCENARIOS.length} over ${COST_MODELS.length} cost models`);
console.log(`  chat flows        ${FLOWS.length}`);
console.log(`  learn modules     ${MODULES.length} (${MODULES.reduce((n, m) => n + m.lessons.length, 0)} lessons, ${MODULES.reduce((n, m) => n + m.lessons.reduce((k, l) => k + l.checkpoint.length, 0), 0)} checkpoint questions)`);


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
