// The review boundary, browser side (OF-BLD-012 §7.3).
//
// Pure functions over a record, its paper and the extractor's candidates:
// what the card shows beside a curated record on a fetched paper, what a
// promotion carries, and why `gold` would be refused before the reviewer
// presses it. `biorepo.write` on the service is the authority (§2.3); these
// exist so the screen says the same thing the service would, one keystroke
// earlier, and so the store and the card cannot disagree about which
// candidate is "the extractor's best".
import type { Candidate, ExtractionRecord, Paper } from '@/data/types';
import { convert, quantityEquals, sameFamily } from '@/engine/units';

/** The extractor's run, the only one that ever ran (§6). */
export const EXTRACTOR_RUN = 'haiku-1';

/** Match tolerance, the same 2 % Witness scores with (§6.2). */
export const AGREE_PCT = 2;

type Quoted = Pick<ExtractionRecord, 'quote' | 'sectionId'>;
type Valued = Pick<ExtractionRecord, 'value' | 'unit'>;

export function paperFetched(paper: Paper | undefined): paper is Paper {
  return !!paper && paper.textSource === 'full-text' && paper.sections.length > 0;
}

/**
 * Whether the record's own quote is in its section of the FETCHED text, the
 * way the reader looks for it (exact substring, the same test that draws the
 * highlight). null when the paper has no fetched text: there is nothing to
 * anchor to, which is a different fact from "not found".
 */
export function quoteAnchors(record: Quoted, paper: Paper | undefined): boolean | null {
  if (!paperFetched(paper)) return null;
  const section = paper.sections.find((s) => s.id === record.sectionId);
  return !!section && !!record.quote && section.text.includes(record.quote);
}

/**
 * A candidate for a field the seed has no record of on that paper — the
 * corpus growing (§6.2). These join the review queue after the seed records;
 * a candidate that matches a seed record's field is evidence about that
 * record and stays beside it instead.
 */
export function isNewCandidate(c: Pick<Candidate, 'paperId' | 'field'>, records: ExtractionRecord[]): boolean {
  return !records.some(
    (r) => r.extractorRun !== EXTRACTOR_RUN && r.paperId === c.paperId && r.field === c.field,
  );
}

/** Two values agree: strings case-insensitively, numbers within AGREE_PCT after conversion. */
export function agrees(a: Valued, b: Valued): boolean {
  if (typeof a.value === 'string' || typeof b.value === 'string') {
    return String(a.value).trim().toLowerCase() === String(b.value).trim().toLowerCase();
  }
  return quantityEquals({ value: b.value, unit: b.unit }, { value: a.value, unit: a.unit }, AGREE_PCT);
}

/** The candidate's value relative to the curated one, in percent, after conversion; null when not comparable. */
export function relativeDelta(curated: Valued, candidate: Valued): number | null {
  if (typeof curated.value !== 'number' || typeof candidate.value !== 'number') return null;
  if (!sameFamily(candidate.unit, curated.unit) || curated.value === 0) return null;
  try {
    const cv = convert(candidate.value, candidate.unit, curated.unit);
    return ((cv - curated.value) / Math.abs(curated.value)) * 100;
  } catch {
    return null;
  }
}

export interface CandidateMatch {
  candidate: Candidate;
  /** Its value agrees with the curated one within AGREE_PCT. */
  agrees: boolean;
  deltaPct: number | null;
}

/**
 * The extractor's best candidate for a curated record: same paper and field;
 * one that agrees with the curated value if there is one, otherwise the most
 * confident. null when the extractor produced nothing for that field.
 */
export function bestCandidate(record: ExtractionRecord, candidates: Candidate[]): CandidateMatch | null {
  const pool = candidates.filter(
    (c) => c.id !== record.id && c.paperId === record.paperId && c.field === record.field,
  );
  if (pool.length === 0) return null;
  const agreeing = pool.find((c) => agrees(record, c));
  const candidate = agreeing ?? [...pool].sort((a, b) => b.confidence - a.confidence)[0];
  return { candidate, agrees: !!agreeing, deltaPct: relativeDelta(record, candidate) };
}

/**
 * The span a promotion carries (§7.3): when the curated quote is NOT in the
 * fetched text and an agreeing candidate's is, accept and gold re-anchor the
 * record to the candidate's quote and section, so the promoted record stands
 * in the paper's own words. null when the record's quote already anchors,
 * when nothing is fetched, or when no candidate agrees — a disagreeing span
 * is not carried, because the reviewer is promoting the curated value.
 */
export function carryOverSpan(
  record: ExtractionRecord,
  paper: Paper | undefined,
  candidates: Candidate[],
): { quote: string; sectionId: string; candidateId: string } | null {
  if (quoteAnchors(record, paper) !== false) return null;
  const best = bestCandidate(record, candidates);
  if (!best || !best.agrees) return null;
  return { quote: best.candidate.quote, sectionId: best.candidate.sectionId, candidateId: best.candidate.id };
}

/**
 * Why `biorepo.write` would refuse a gold decision on this record (§2.3), in
 * words the reviewer can act on — or null when it would be stored. Applies
 * only while the service is up: offline, the Durable tier keeps behaving as
 * it always has, and the decision reaches the service later or never.
 */
export function goldRefusal(
  record: ExtractionRecord,
  paper: Paper | undefined,
  candidates: Candidate[],
  serviceUp: boolean | null,
): string | null {
  if (!serviceUp) return null;
  // A candidate's quote anchored when it was extracted; the service will find it.
  if (record.extractorRun === EXTRACTOR_RUN) return null;
  if (!paperFetched(paper)) {
    return `Gold needs the paper's full text, and ${record.paperId} has not been fetched. Fetch it from Intake first.`;
  }
  if (quoteAnchors(record, paper)) return null;
  if (carryOverSpan(record, paper, candidates)) return null;
  return 'Gold needs a sentence in the fetched text that says this number. The curated quote is not in it, and the extractor found no span that agrees.';
}
