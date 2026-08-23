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
import { PRODUCTS } from '../src/data/products';
import { RUNBOOKS } from '../src/data/runbooks';
import { CLEARANCE_FINDINGS } from '../src/data/clearanceFindings';
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
