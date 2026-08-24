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
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { PAPERS } from '../src/data/papers';
import { RECORDS } from '../src/data/records';
import { fieldName } from '../src/data/ontology';
import { provenanceOf } from '../src/store';
import type { ExtractionRecord } from '../src/data/types';

const OUT = 'core/openferment_core/data/corpus.json';

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
}));

const records = RECORDS.map((r) => ({
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
   * False means this paper is quoting somebody else's measurement. The model is
   * told, so it can avoid presenting a citation-of-a-citation as corroboration
   * (OF-COR-001 §19, fifth trap).
   */
  primary: r.isPrimary,
  citesRecordId: r.citesRecordId ?? null,
  strainId: r.organism ?? null,
  conditions: conditionsOf(r),
}));

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ papers, records }, null, 2) + '\n');

const withConditions = records.filter((r) => r.conditions !== null).length;
const nonPrimary = records.filter((r) => !r.primary).length;
const sections = papers.reduce((n, p) => n + p.sections.length, 0);

console.log('\nopenFerment corpus export');
console.log('─────────────────────────');
console.log(`  papers      ${papers.length} (${sections} sections)`);
console.log(`  records     ${records.length}`);
console.log(`  conditions  ${withConditions} carry recorded conditions, ${records.length - withConditions} carry none and say so`);
console.log(`  primary     ${records.length - nonPrimary} first-hand, ${nonPrimary} quoting another record`);
console.log(`\n✓ ${OUT}`);
