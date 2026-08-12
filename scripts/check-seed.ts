/**
 * Seed invariant checker (BUILD-SPEC.md "Hard invariants").
 * Run with `pnpm check:seed` before any bundle.
 *
 * The invariants exist because the UI reads seed data structurally: the reader
 * locates extraction spans by searching for `quote` inside the section text, so
 * a quote that isn't present silently loses its highlight rather than erroring.
 */
import { PAPERS } from '../src/data/papers';
import { CONTRADICTIONS } from '../src/data/contradictions';
import { PATENTS } from '../src/data/patents';
import { DESIGNS } from '../src/data/designs';
import type { RunOutcome } from '../src/data/types';

/** Deposits are never seeded (OF-FE-004 §7.1); the constant exists so the
 *  invariant is written down rather than assumed. */
const DEPOSITS: RunOutcome[] = [];
import { stillFails } from '../src/engine/balance';
import { RECORDS } from '../src/data/records';
import { RUN_OUTPUTS } from '../src/data/runOutputs';
import { STRAINS } from '../src/data/strains';
import { PROTOCOLS } from '../src/data/protocols';
import { SCENARIOS, COST_MODELS } from '../src/data/scenarios';
import { FLOWS, SUGGESTED_PROMPTS } from '../src/data/flows';
import { STRAIN_ALIASES } from '../src/data/strains';
import { MODULES } from '../src/data/learn';
import { COLLECTIONS, ACTIVITY, SEED_SESSIONS } from '../src/data/misc';
import { ONTOLOGY, ONTOLOGY_BY_ID } from '../src/data/ontology';
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

// ── report ─────────────────────────────────────────────────────────────
console.log('\nopenFerment seed check');
console.log('──────────────────────');
console.log(`  papers            ${PAPERS.length} catalogued (${PAPERS.filter((p) => p.textSource === 'full-text').length} full-text, ${PAPERS.filter((p) => p.openAccess).length} open access)`);
console.log(`  threads           ${new Set(PAPERS.map((p) => p.thread)).size} · tranche 1: ${PAPERS.filter((p) => p.tranche === 1).length}, 2: ${PAPERS.filter((p) => p.tranche === 2).length}, 3: ${PAPERS.filter((p) => p.tranche === 3).length}`);
console.log(`  needs [verify]    ${PAPERS.filter((p) => p.verifyNeeded).length} author strings`);
console.log(`  sections          ${PAPERS.reduce((n, p) => n + p.sections.length, 0)}`);
// ── every quantity in an agent answer carries its source (§8.9, §9.6) ──
// Rule 1 says no quantity may come from model weights, and an agent answer is
// the most visible place in the app to break it.
//
// Scoped to quantities rather than to every numeral, deliberately. OF-FE-003
// §8.9 asks that "every numeral" be a chip; run literally that flags 114 across
// the 13 flows, most of them years, ordinals ("reason 2") and counts of rows on
// the page — chipping those would make the answers worse, not more honest. A
// numeral carrying a UNIT is the thing Rule 1 is about, and there the check is
// strict: 28 such lines exist and every one must name a source.
const QUANTITY =
  /\d+(?:[.,]\d+)?\s*(mg|g|kg|L|mL|h|min|d|%|USD|EUR|€|\$|µ|mol|Da|nt|aa|t\/y|kg⁻¹|L⁻¹|h⁻¹)/;
for (const f of FLOWS) {
  for (const line of String(f.answerMd ?? '').split('\n')) {
    if (!QUANTITY.test(line)) continue;
    if (/\[\[[^\]]+\]\]/.test(line)) continue;
    fail(
      `flow ${f.id}: a quantity with no citation on its line — "${line.trim().slice(0, 80)}"`,
    );
  }
}

// ── every assumption declares its basis (OF-FE-004 §1.1.5) ────────────
// A record binding must actually match the record: an assumption that claims a
// Ledger source and then carries a different number is worse than one that
// admits it is a modelling choice, because it looks bound and is not.
for (const sc of SCENARIOS) {
  for (const a of sc.assumptions) {
    if (!a.basis) {
      fail(`${sc.id}: assumption "${a.label}" declares no basis`);
      continue;
    }
    if (a.basis.kind === 'record') {
      const bound = RECORDS.find((r) => r.id === (a.basis as { recordId: string }).recordId);
      if (!bound) {
        fail(`${sc.id}: assumption "${a.label}" binds unresolved record ${(a.basis as { recordId: string }).recordId}`);
      } else if (typeof bound.value === 'number' && Math.abs(bound.value - a.value) > 1e-9) {
        fail(
          `${sc.id}: assumption "${a.label}" says ${a.value} but record ${bound.id} says ${bound.value} — a binding that does not match is worse than none`,
        );
      }
    } else if (a.basis.kind === 'model' && !a.basis.justification.trim()) {
      fail(`${sc.id}: assumption "${a.label}" is a model parameter with no justification`);
    }
  }
}

// Shared by the decisive, patent-bound and design checks below.
const FIELD_IDS = new Set(ONTOLOGY.map((d) => d.id));

// ── decisive measurements and result schemas (OF-FE-003 §4.5, §9) ─────
// A protocol that claims to settle a parameter must name a real one, and a
// result field that claims to produce a record must name a field that can hold
// it. Either one wrong makes the experiment loop point somewhere that does not
// exist.
let decisiveCount = 0;
for (const p of PROTOCOLS) {
  for (const v of p.versions) {
    if (v.decisive) {
      decisiveCount++;
      if (!FIELD_IDS.has(v.decisive.field)) {
        fail(`${p.id}@${v.version}: decisive names unknown field '${v.decisive.field}'`);
      }
      if (!v.decisive.currentUncertainty.trim() || !v.decisive.whatWouldChange.trim()) {
        fail(`${p.id}@${v.version}: decisive must say what is unknown and what a result changes`);
      }
    }
    for (const f of v.resultSchema ?? []) {
      if (f.field && !FIELD_IDS.has(f.field)) {
        fail(`${p.id}@${v.version}: result field '${f.id}' names unknown ontology field '${f.field}'`);
      }
    }
    // A protocol that declares a decisive measurement should be able to collect
    // it, otherwise running it produces nothing the Ledger can absorb.
    if (v.decisive && !(v.resultSchema ?? []).some((f) => f.field === v.decisive!.field)) {
      fail(
        `${p.id}@${v.version}: declares ${v.decisive.field} decisive but no result field produces it`,
      );
    }
  }
}
if (decisiveCount < 4) {
  warn(`only ${decisiveCount} protocol versions declare a decisive measurement (OF-FE-003 §9 asks for at least 4)`);
}

// ── design records resolve what they consume (OF-FE-003 §9.5) ─────────
// A design that names a record it did not consume, or one that does not exist,
// breaks staleness silently: the correction would never reach it.
for (const d of DESIGNS) {
  for (const rid of d.consumedRecordIds) {
    if (!recordIds.has(rid)) fail(`${d.id}: consumedRecordIds names unresolved record ${rid}`);
  }
  if (!SCENARIOS.some((s) => s.id === d.scenarioId)) {
    fail(`${d.id}: scenarioId ${d.scenarioId} does not resolve`);
  }
  // An absent tier must never carry a result, and a passed one must say what
  // bound it. Rendering an absent tier as passed is the §2 failure mode.
  for (const t of d.tiers) {
    if (t.state === 'absent' && !t.absentReason) {
      fail(`${d.id} ${t.tier}: absent with no reason given`);
    }
    if (t.state === 'absent' && Object.keys(t.values).length > 0) {
      fail(`${d.id} ${t.tier}: absent but carries values — an absent tier has no result`);
    }
    if (t.state !== 'absent' && !t.bindingConstraint.trim()) {
      fail(`${d.id} ${t.tier}: ran but names no binding constraint`);
    }
    // A point estimate must not occupy the interval field.
    if (t.msp && t.msp.p05 === t.msp.p95) {
      fail(`${d.id} ${t.tier}: msp interval has zero width — a point estimate is not a distribution`);
    }
  }
  if (d.scope !== 'clear' && !d.scopeEvaluated) {
    fail(`${d.id}: scope '${d.scope}' claimed without evaluation`);
  }
}

// ── deposits produce experiment records (OF-FE-003 §9.7) ──────────────
// Vacuous today by design: §7.1 forbids seeding openLab deposits, so DEPOSITS
// is empty and this guards the case where someone seeds one anyway. The check
// that bites is in store.depositRun, because deposits are made at runtime.
for (const d of DEPOSITS) {
  for (const rid of d.producedRecordIds) {
    const rec = RECORDS.find((r) => r.id === rid);
    if (!rec) {
      fail(`${d.runId}: producedRecordIds names unresolved record ${rid}`);
    } else if (rec.evidenceClass !== 'experiment') {
      fail(
        `${d.runId}: produced record ${rid} carries evidenceClass '${rec.evidenceClass}' — a bench deposit must produce 'experiment'`,
      );
    }
  }
}

// ── patent claim bounds name real fields (OF-FE-003 §9.4) ─────────────
// A claim whose bound names a field the ontology does not have cannot be tested
// against anything, and would sit on the screen looking like scope.
for (const pt of PATENTS) {
  if (pt.paperId && !paperIds.has(pt.paperId)) {
    fail(`${pt.id}: paperId ${pt.paperId} does not resolve`);
  }
  for (const c of pt.claims) {
    for (const b of c.bounds) {
      if (!FIELD_IDS.has(b.field)) {
        fail(`${pt.id} claim ${c.number}: bound names unknown field '${b.field}'`);
      }
    }
    // A parsed bound and an "uncertain parse" flag are contradictory states.
    if (c.bounds.length > 0 && c.parseUncertain) {
      warn(`${pt.id} claim ${c.number}: has bounds but is still flagged parseUncertain`);
    }
  }
}

// ── contradictions must still fail when recomputed (OF-FE-003 §9.3) ───
// A contradiction that does not fail its tolerance is not a finding, it is a
// claim — and a system that stages the exact error it exists to catch is worse
// than one with no referee at all. These are derived rather than authored, so
// this check is a genuine re-verification of the derivation, not a formality.
for (const c of CONTRADICTIONS) {
  for (const rid of c.recordIds) {
    if (!recordIds.has(rid)) fail(`${c.id}: recordId ${rid} does not resolve`);
  }
  if (c.recordIds.length === 0) fail(`${c.id}: names no records`);
  if (!stillFails(c, RECORDS)) {
    fail(
      `${c.id}: residual ${c.constraint.residual} does not exceed tolerance ${c.constraint.tolerance} — a contradiction that does not fail is a claim, not a finding`,
    );
  }
  if (c.status !== 'open' && !c.note) {
    fail(`${c.id}: status '${c.status}' requires a note explaining the resolution`);
  }
}

// ── evidence class and the unsourced defect (OF-FE-003 §3, §9) ─────────
// Invariant 1: every record declares what kind of thing produced it. Without
// it a prediction and a measurement are indistinguishable in the store.
// Invariant 2: 'unsourced' is a defect class. Zero records may carry it — it
// exists so the interface can show what a Rule 1 violation looks like, not so
// data can ship in that state.
const EVIDENCE_CLASSES = new Set([
  'literature',
  'patent',
  'computed',
  'experiment',
  'correction',
]);
for (const r of RECORDS) {
  if (!r.evidenceClass) {
    fail(`${r.id}: no evidenceClass — every record must declare what produced it`);
  } else if (!EVIDENCE_CLASSES.has(r.evidenceClass)) {
    fail(`${r.id}: evidenceClass '${r.evidenceClass}' is not a known class`);
  }
  if (r.provenance === 'unsourced') {
    fail(`${r.id}: provenance 'unsourced' is a defect class — no record may carry it`);
  }
}

console.log(`  records           ${RECORDS.length} (${RECORDS.filter((r) => r.provenance === 'curated').length} curated, ${RECORDS.filter((r) => r.provenance === 'industry-estimate').length} industry estimate)`);
console.log(`  non-primary       ${RECORDS.filter((r) => r.isPrimary === false).length} (citations of other records, excluded from aggregates)`);
console.log(`  with method       ${RECORDS.filter((r) => r.method).length}, of which ${RECORDS.filter((r) => r.method === 'undetermined').length} undetermined`);
console.log(`  gold set          ${goldIds.size} annotated (60 planned across 14 papers — pending tranche-1 ingest)`);
console.log(`  strains           ${STRAINS.length}`);
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
