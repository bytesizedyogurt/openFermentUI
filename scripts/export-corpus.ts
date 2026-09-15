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
import { provenanceOf } from '../src/store';
import type { BioRepo, ExtractionRecord, ReviewDecision } from '../src/data/types';

const OUT = 'core/openferment_core/data/corpus.json';

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

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ papers, records, ontology, units }, null, 2) + '\n');

const withConditions = records.filter((r) => r.conditions !== null).length;
const nonPrimary = records.filter((r) => !r.primary).length;
const sections = papers.reduce((n, p) => n + p.sections.length, 0);

console.log('\nopenFerment corpus export');
console.log('─────────────────────────');
console.log(`  papers      ${papers.length} (${sections} sections; ${papers.filter((p) => p.pmcid).length} with a PMCID, ${papers.filter((p) => !p.pmcid && p.doi).length} DOI-only, ${papers.filter((p) => !p.pmcid && !p.doi && p.pmid).length} PMID-only)`);
const decisionList = Object.values(biorepo.decisions);
console.log(`  records     ${records.length} (${seedRecords.length} seed, ${newRecords.length} accepted new records from biorepo.json)`);
console.log(`  decisions   ${decisionList.length} (${decisionList.filter((d) => d.status === 'verified').length} verified, ${decisionList.filter((d) => d.status === 'rejected').length} rejected, ${decisionList.filter((d) => d.provenance === 'gold' || d.gold).length} gold)`);
console.log(`  conditions  ${withConditions} carry recorded conditions, ${records.length - withConditions} carry none and say so`);
console.log(`  primary     ${records.length - nonPrimary} first-hand, ${nonPrimary} quoting another record`);
console.log(`  ontology    ${ontology.length} fields, ${ontology.filter((d) => d.categorical).length} categorical, ${ontology.filter((d) => d.requiresMethod).length} require a method`);
console.log(`  units       ${Object.keys(U).length} units in ${new Set(Object.values(U).map((u) => u.family)).size} families, ${Object.keys(ALIASES).length} aliases, ${REFUSALS.length} explained refusals`);
console.log(`\n✓ ${OUT}`);
