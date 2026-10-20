/**
 * Corpus export (OF-BLD-007 §4.1).
 *
 * Emits core/openferment_core/data/corpus.json — the evidence the Python
 * service retrieves over and the ONLY thing Postdoc is allowed to reason from.
 *
 * The corpus lives in TypeScript and stays there. This is a projection, not a
 * migration: the seed modules remain the source of truth, check-seed keeps
 * enforcing their invariants, and the JSON is gitignored so there is never a
 * second copy to drift. Regenerate with `pnpm export:corpus` before starting
 * the service.
 *
 * NOTHING IS INVENTED IN HERE. Every exported field is either copied straight
 * across or composed from fields the record actually carries. `conditions` in
 * particular is built only from recorded method/numbering/range/negative-result
 * facts and is null when none of them are present — a plausible-sounding
 * condition string attached to a real measurement is worse than no condition
 * string, because downstream it reads as something somebody established.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import { PAPERS } from '../src/data/papers';
import { RECORDS } from '../src/data/records';
import { ONTOLOGY, fieldName } from '../src/data/ontology';
import { ALIASES, REFUSALS, SI_UNIT, U, toSI } from '../src/engine/units';
import { isExample, programOf, provenanceOf } from '../src/store';
import { PROGRAMS } from '../src/data/programs';
import { SKILLS } from '../src/data/skills';
import { MODULES } from '../src/data/learn';
import { PROTOCOLS } from '../src/data/protocols';
import { renderStepText } from '../src/engine/scale';
import { STRAIN_ALIASES, STRAINS } from '../src/data/strains';
import { PRODUCTS } from '../src/data/products';
import { CARBON_SOURCES, CLEARANCE_STATES_BY_ID, PATHWAYS, UNIT_OPERATIONS } from '../src/data/vocabulary';
import { CLEARANCE_FINDINGS } from '../src/data/clearanceFindings';
import { RUNBOOKS } from '../src/data/runbooks';
import { SCENARIOS } from '../src/data/scenarios';
import type { BioRepo, ExtractionRecord, ReviewDecision } from '../src/data/types';

/**
 * Where the projection lands. Overridable (OF-BLD-012.1 F4–F5) so a guard can
 * export into a temp directory and read it back without touching the one the
 * service uses — `check:biorepo` brings its own export, and `test:export`
 * exports the demo's decisions to prove the merge happens.
 */
const OUT = process.env.OPENFERMENT_CORPUS_OUT?.trim() || 'core/openferment_core/data/corpus.json';

/**
 * The reviewers' decisions (OF-BLD-012 §7.4). corpus.json reflects
 * biorepo.json: a promoted record carries its promoted status and provenance
 * and the quote a reviewer re-anchored it to; an accepted new record is
 * appended. The seed modules stay untouched — this is the one place the two
 * are combined, and `check:biorepo` checks that the combination happened.
 */
// The same override the service reads (OPENFERMENT_DATA_DIR), so the demo's
// scratch decisions reach the corpus the demo's service retrieves over.
const DATA_DIR = process.env.OPENFERMENT_DATA_DIR?.trim() || 'core/data';
const BIOREPO = join(isAbsolute(DATA_DIR) ? DATA_DIR : join(process.cwd(), DATA_DIR), 'biorepo.json');
const biorepo: BioRepo = existsSync(BIOREPO)
  ? (JSON.parse(readFileSync(BIOREPO, 'utf8')) as BioRepo)
  : { version: 1, decisions: {}, records: [] };

/** A record as the reviewer left it. Nothing is invented: every field comes off the decision. */
function decided(r: ExtractionRecord, d: ReviewDecision | undefined): ExtractionRecord {
  if (!d) return r;
  const value = d.corrected?.value ?? r.value;
  const unit = d.corrected?.unit ?? r.unit;
  return {
    ...r,
    status: d.status,
    provenance: d.provenance,
    gold: d.gold,
    corrected: d.corrected,
    rejectReason: d.rejectReason,
    reviewer: d.reviewer,
    quote: d.quote ?? r.quote,
    sectionId: d.sectionId ?? r.sectionId,
    value,
    unit,
    si: d.corrected && typeof value === 'number' ? toSI(value, unit) : r.si,
  };
}

/**
 * What was actually recorded about how this measurement was taken.
 *
 * Null when nothing was recorded. 'undetermined' as a method means the analysis
 * was never done (OF-COR-001 §17 Rule 1) — that is a real fact about the
 * record and is stated rather than dropped, because "nobody ran the assay" and
 * "the assay came back negative" are different answers.
 */
function conditionsOf(r: ExtractionRecord): string | null {
  const parts: string[] = [];
  if (r.method === 'undetermined') parts.push('method undetermined — the analysis was not performed');
  else if (r.method) parts.push(`method: ${r.method}`);
  if (r.numbering) parts.push(`residue numbering: ${r.numbering}`);
  if (r.range) parts.push(`source states a range: ${r.range.low}–${r.range.high}`);
  if (r.negativeResult) parts.push('reported as a negative/absent result, not a missing measurement');
  if (r.comparativeBaseline) parts.push(`stated relative to ${r.comparativeBaseline}`);
  return parts.length > 0 ? parts.join('; ') : null;
}

const papers = PAPERS.map((p) => ({
  id: p.id,
  title: p.title,
  year: p.year,
  authors: p.authors,
  venue: p.venue,
  /**
   * Whether `sections` hold the paper's own text or a curator's note. The
   * service passes this through so a claim built on a curation note is not
   * silently presented as built on the source (OF-COR-001).
   */
  textSource: p.textSource,
  sections: p.sections.map((s) => ({ id: s.id, heading: s.heading, text: s.text })),
  /**
   * The identifiers Intake resolves and fetches by (OF-BLD-012 §5.1), and the
   * state the ingest board reads. Absent until §10.4's API test asked the
   * service to fetch B5 and it answered "no identifier" — the seed had a PMCID
   * the projection never carried. Null rather than missing, so the Python
   * side reads a fixed shape.
   */
  doi: p.doi ?? null,
  pmcid: p.pmcid ?? null,
  pmid: p.pmid ?? null,
  /**
   * Where Intake fetches the text of a source Europe PMC does not hold (an
   * OSTI report, an SGD strain entry; thread Q), and what kind of source it
   * is. Null when the paper has no address of its own.
   */
  sourceUrl: p.sourceUrl ?? null,
  sourceType: p.sourceType,
  openAccess: p.openAccess,
  ingest: p.ingest,
  tranche: p.tranche,
}));

function exportRecord(r: ExtractionRecord, source: 'seed' | 'biorepo') {
  return {
    id: r.id,
    paperId: r.paperId,
    sectionId: r.sectionId,
    field: r.field,
    /** The ontology's human name for the field — 'Titre', not 'titre_g_per_l'. */
    fieldLabel: fieldName(r.field),
    value: r.value,
    unit: r.unit,
    /** Normalised value, so retrieval and the UI agree on magnitude. */
    si: r.si,
    quote: r.quote,
    /**
     * The EFFECTIVE provenance, via the same `provenanceOf` the UI renders from.
     * Exporting the raw field instead would let the service and the screen
     * disagree about what a record is worth, which is the one disagreement that
     * must not exist.
     */
    provenance: provenanceOf(r),
    /**
     * The review status as biorepo.json has it (OF-BLD-012 §7.4). Retrieval
     * skips 'rejected'; `check:biorepo` checks this column against the file.
     */
    status: r.status,
    /** For anchoring a promotion (§2.4 rule 6): the ontology may require one. */
    method: r.method ?? null,
    /**
     * False means this paper is quoting somebody else's measurement. The model is
     * told, so it can avoid presenting a citation-of-a-citation as corroboration
     * (OF-COR-001 §19, fifth trap).
     */
    primary: r.isPrimary,
    citesRecordId: r.citesRecordId ?? null,
    strainId: r.organism ?? null,
    /**
     * What the curators recorded ABOUT the value, as data rather than prose
     * (OF-BLD-012.1 F1.1). `conditions` below still says both in words for
     * the model to read; these two are for §2.4 rule 3, which anchors a
     * midpoint against the range the sentence states and reads a zero out of
     * the absence it reports. Folded only into the prose, as they were, the
     * service could not see either — and 27 of the 34 curated records whose
     * value is not literally in their own quote are one of these two.
     */
    range: r.range ?? null,
    negativeResult: r.negativeResult ?? false,
    conditions: conditionsOf(r),
    /** 'seed' from src/data; 'biorepo' for a new record a reviewer accepted. */
    source,
  };
}

const seedRecords = RECORDS.map((r) => exportRecord(decided(r, biorepo.decisions[r.id]), 'seed'));
// Accepted new records: the corpus growing (§7.4). A rejected candidate is
// not a record and an undecided one is not in biorepo.json at all.
const newRecords = biorepo.records
  .filter((c) => biorepo.decisions[c.id]?.status === 'verified')
  .map((c) => exportRecord(decided({ ...c, audit: [] }, biorepo.decisions[c.id]), 'biorepo'));
const records = [...seedRecords, ...newRecords];

/**
 * The ontology, for the extractor and the anchoring validator (OF-BLD-012 §5.3).
 *
 * Every field the spec names, and NOT `notes`. The notes carry example values
 * — "P. pastoris β-casein 15–18", "industry fermentation averages run 24–42" —
 * which are exactly what must never sit in front of a model being asked to
 * find numbers in a paper. The definition says what a field means; the notes
 * say what values people have seen, and the second is a prime.
 *
 * Optional fields are filled with their defaults so the Python side reads a
 * fixed shape rather than probing for keys.
 */
const ontology = ONTOLOGY.map((d) => ({
  id: d.id,
  family: d.family,
  name: d.name,
  definition: d.definition,
  canonicalUnit: d.canonicalUnit,
  range: d.range,
  categorical: d.categorical ?? false,
  requiresMethod: d.requiresMethod ?? false,
  refuseConversionTo: d.refuseConversionTo ?? [],
}));

/**
 * The unit engine's tables, verbatim. This is the split OF-BLD-002 §0 asked
 * for: on the Python side `units.ts` becomes a generated table; on this side
 * it stays the reference implementation, proven by the fixture that
 * `export-unit-fixtures.ts` records from it.
 */
const units = { table: U, aliases: ALIASES, si: SI_UNIT, refusals: REFUSALS };

/**
 * The two vocabularies anchoring resolves a paper's wording against
 * (OF-BLD-014 §2.1), verbatim: the strain alias table, so `validate.py` can
 * store a strain id where the extractor wrote "C. reinhardtii UVM4", and the
 * carbon sources with their spellings. The rule that reads them is
 * `matchWholeWord` in src/data/strains.ts, mirrored in validate.py.
 */
const strainAliases = STRAIN_ALIASES;
const carbonSources = CARBON_SOURCES;
// OF-BLD-014 §9.2 — the ids a drafted runbook's product and strain must resolve against.
const products = PRODUCTS.map((p) => ({ id: p.id, name: p.name }));
const strains = STRAINS.map((s) => ({ id: s.id, name: `${s.binomial} ${s.designation}`.trim() }));

/**
 * The programs (OF-BLD-016 §2.1, E.2′), verbatim from src/data/programs.ts:
 * which thread letters are whose, and which are archived. A paper's program
 * is its thread letter's and a record's is its paper's, so neither carries a
 * copy; `programs.py` resolves both from this list.
 */
const programs = PROGRAMS.map((p) => ({ id: p.id, name: p.name, letters: p.letters, status: p.status, summary: p.summary }));

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(
  OUT,
  JSON.stringify({ papers, records, ontology, units, strainAliases, carbonSources, products, strains, programs }, null, 2) + '\n',
);

/**
 * Guild's projection (OF-BLD-013 §1.2), written beside the corpus as
 * skills.json. `guild.write_evidence` needs to know which skills exist, which
 * protocol steps carry which tag, and which lessons count toward which skill,
 * and Practice needs the tagged protocols' own words; all of it lives in the
 * TypeScript seed, and this is the same arrangement the corpus uses. It is separate from corpus.json because Postdoc retrieves over
 * the corpus, and a skill definition is no evidence about anything.
 */
const guildProjection = {
  skills: SKILLS,
  steps: PROTOCOLS.flatMap((p) =>
    p.versions.flatMap((v) =>
      v.steps.map((st) => ({ protocolId: p.id, version: v.version, stepId: st.id, skills: st.skills ?? [] })),
    ),
  ),
  // §3.1 — which lessons count toward which skills, so a knowledge entry
  // from a lesson names one that does.
  lessons: MODULES.flatMap((m) => m.lessons.map((l) => ({ lessonId: l.id, skills: l.skills ?? [] }))),
  // §4.1 — what Practice may quote. The current version of every protocol a
  // skill is tagged on, its steps rendered at the base batch by the same code
  // run mode uses, so a value a scenario shows is the protocol's own.
  protocols: PROTOCOLS.flatMap((p) => {
    const v = p.versions.find((x) => x.version === p.currentVersion) ?? p.versions[0];
    if (!v.steps.some((st) => (st.skills ?? []).length > 0)) return [];
    return [
      {
        protocolId: p.id,
        version: v.version,
        title: p.title,
        baseBatch: `${v.baseBatch.value} ${v.baseBatch.unit} ${v.baseBatch.label}`,
        steps: v.steps.map((st) => ({ stepId: st.id, text: renderStepText(st, v, 1), note: st.note ?? null, skills: st.skills ?? [] })),
        materials: v.materials.map((m) => ({ name: m.name, amount: m.amount, unit: m.unit })),
      },
    ];
  }),
};
writeFileSync(join(dirname(OUT), 'skills.json'), JSON.stringify(guildProjection, null, 2) + '\n');

/**
 * The modules' projection (OF-BLD-015 §7.1), written beside the corpus as
 * modules.json. Postdoc's coverage pass and its read tools sweep every
 * module, and the modules that live in the TypeScript seed reach Python
 * here, the same arrangement skills.json uses. Each row carries the module's
 * own state word (a clearance state, a runbook status); the one `state` enum
 * Postdoc reads is computed from it in `module_stores.py`, never here. Words
 * and ids only where a row is matched by name; the values a module shows stay
 * in the module.
 */
const modulesProjection = {
  // OF-BLD-016 §2.1 — the same programs as corpus.json, and on every row
  // below the program `programOf` gives it (null: general, always shown).
  programs,
  dominion: {
    molecules: PRODUCTS.map((p) => ({
      id: p.id,
      name: p.name,
      aliases: p.aliases,
      category: p.category,
      clearanceState: p.clearanceState,
      clearanceLabel: CLEARANCE_STATES_BY_ID[p.clearanceState]?.label ?? p.clearanceState,
      defaultStrainId: p.defaultStrainId,
      pathwayIds: p.pathwayIds,
      processCode: p.processCode,
      unitOperationIds: p.unitOperationIds,
      provenance: p.provenance,
      note: p.note,
      program: programOf('product', p.id),
    })),
    findings: CLEARANCE_FINDINGS.map((f) => ({
      productId: f.productId,
      jurisdictionId: f.jurisdictionId,
      state: f.state,
      provenance: f.provenance,
      summary: f.summary,
      readAt: f.readAt,
      patents: f.patents.map((x) => ({ office: x.office, number: x.number, title: x.title, expiresOnTerm: x.expiresOnTerm })),
    })),
  },
  runbooks: {
    runbooks: RUNBOOKS.map((r) => ({
      id: r.id,
      title: r.title,
      kind: r.kind,
      status: r.status,
      productId: r.productId,
      strainId: r.strainId,
      lockedAt: r.lockedAt,
      predictions: r.predictions.map((x) => x.label),
      program: programOf('runbook', r.id),
      // OF-BLD-016 §3.3 (D3): a run nobody made. The browser hides it with
      // the archive; the service lists it, marked, so a read can say so.
      example: isExample('runbook', r.id),
    })),
    protocols: PROTOCOLS.map((p) => ({
      id: p.id,
      title: p.title,
      category: p.category,
      organisms: p.organisms,
      purpose: p.purpose,
      currentVersion: p.currentVersion,
      versions: p.versions.map((v) => v.version),
      program: programOf('protocol', p.id),
      example: isExample('protocol', p.id),
    })),
  },
  geneos: {
    hosts: STRAINS.map((s) => ({ id: s.id, name: `${s.binomial} ${s.designation}`.trim(), bsl: s.bsl, badges: s.badges, program: programOf('strain', s.id) })),
    pathways: PATHWAYS.map((x) => ({ id: x.id, label: x.label, products: x.products })),
  },
  pureos: {
    // OF-BLD-019 §4.1 — the BioSTEAM classes an entry names, so a train's unit reads as the vocabulary's step.
    unitOperations: UNIT_OPERATIONS.map((u) => ({ id: u.id, label: u.label, stage: u.stage, note: u.note ?? null, biosteamClasses: u.biosteamClasses ?? [] })),
  },
  proforma: {
    scenarios: SCENARIOS.map((x) => ({ id: x.id, name: x.name, kind: x.kind, product: x.product, modelId: x.modelId, program: programOf('scenario', x.id), example: isExample('scenario', x.id) })),
  },
  primer: {
    lessons: MODULES.flatMap((m) =>
      m.lessons.map((l) => ({ id: l.id, title: l.title, moduleId: m.id, moduleTitle: m.title, blurb: m.blurb, skills: l.skills ?? [], program: programOf('lesson', l.id), example: isExample('lesson', l.id) })),
    ),
  },
};
writeFileSync(join(dirname(OUT), 'modules.json'), JSON.stringify(modulesProjection, null, 2) + '\n');

const withConditions = records.filter((r) => r.conditions !== null).length;
const nonPrimary = records.filter((r) => !r.primary).length;
const sections = papers.reduce((n, p) => n + p.sections.length, 0);

console.log('\nopenFerment corpus export');
console.log('─────────────────────────');
console.log(`  papers      ${papers.length} (${sections} sections; ${papers.filter((p) => p.pmcid).length} with a PMCID, ${papers.filter((p) => !p.pmcid && p.doi).length} DOI-only, ${papers.filter((p) => !p.pmcid && !p.doi && p.pmid).length} PMID-only, ${papers.filter((p) => p.sourceUrl).length} with a source address of their own)`);
const decisionList = Object.values(biorepo.decisions);
console.log(`  records     ${records.length} (${seedRecords.length} seed, ${newRecords.length} accepted new records from biorepo.json)`);
console.log(`  decisions   ${decisionList.length} (${decisionList.filter((d) => d.status === 'verified').length} verified, ${decisionList.filter((d) => d.status === 'rejected').length} rejected, ${decisionList.filter((d) => d.provenance === 'gold' || d.gold).length} gold)`);
console.log(`  conditions  ${withConditions} carry recorded conditions, ${records.length - withConditions} carry none and say so`);
console.log(`  primary     ${records.length - nonPrimary} first-hand, ${nonPrimary} quoting another record`);
console.log(`  ontology    ${ontology.length} fields, ${ontology.filter((d) => d.categorical).length} categorical, ${ontology.filter((d) => d.requiresMethod).length} require a method`);
console.log(`  units       ${Object.keys(U).length} units in ${new Set(Object.values(U).map((u) => u.family)).size} families, ${Object.keys(ALIASES).length} aliases, ${REFUSALS.length} explained refusals`);
console.log(`  strains     ${Object.keys(strainAliases).length} aliases to ${new Set(Object.values(strainAliases)).size} strain ids`);
console.log(`  carbon      ${carbonSources.length} sources, ${carbonSources.reduce((n, c) => n + c.spellings.length, 0)} spellings`);
console.log(`  programs    ${programs.map((p) => `${p.id} (${p.letters.length === 1 ? p.letters[0] : `${p.letters[0]}–${p.letters[p.letters.length - 1]}`}, ${p.status})`).join(', ')}`);
console.log(`\n✓ ${OUT}`);
