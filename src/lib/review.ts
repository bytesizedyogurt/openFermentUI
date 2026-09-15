// The review boundary, browser side (OF-BLD-012 §7.3).
//
// Pure functions over a record, its paper and the extractor's candidates:
// how a quote is looked for in the fetched text, what the card shows beside
// a curated record, what a promotion carries, and why the service would
// refuse a decision before the reviewer presses the key. `biorepo.write` on
// the service is the authority (§2.3); these exist so the screen says the
// same thing the service would, one keystroke earlier, and so the store and
// the card cannot disagree about which candidate is "the extractor's best".
import type { Candidate, ExtractionRecord, Paper } from '@/data/types';
import { convert, quantityEquals, sameFamily } from '@/engine/units';

/** The extractor's run, the only one that ever ran (§6). */
export const EXTRACTOR_RUN = 'haiku-1';

/** Match tolerance, the same 2 % Witness scores with (§6.2). */
export const AGREE_PCT = 2;

type Quoted = Pick<ExtractionRecord, 'quote' | 'sectionId'>;
type Valued = Pick<ExtractionRecord, 'value' | 'unit'>;

// ── §2.4 rule 2's normalisation, the browser's copy ─────────────────────
//
// The service looks for a quote in a section AFTER folding both through
// validate.normalize_text: soft hyphens dropped, every dash variant to '-',
// a superscript on a unit to '-1', a superscript on a number to '^6',
// whitespace runs to one space. The browser must look the same way, or a
// candidate the service anchored renders as "quote not located" here and a
// curated quote the service would accept is refused by goldRefusal below.
// Kept in step with validate.py by hand; the smoke test's candidate quotes
// and test_anchor's cases are the shared examples.

const SUP = '⁰¹²³⁴⁵⁶⁷⁸⁹';
const SUP_TO_DIGIT: Record<string, string> = {};
for (let i = 0; i < 10; i++) SUP_TO_DIGIT[SUP[i]] = String(i);
const foldSup = (s: string) => s.replace(/./g, (ch) => SUP_TO_DIGIT[ch] ?? ch);
const POWER = new RegExp(`(\\d) ?(\\u207b?)([${SUP}]+)`, 'g');
const UNIT_EXP = new RegExp(`\\u207b([${SUP}]+)`, 'g');
const DASHES = /[−‐‑‒–—―⁻]/g;
const SUP_ANY = new RegExp(`[${SUP}]`, 'g');

/** Rule 2's normalisation of a quote or a section, character for character with the service. */
export function normalizeText(text: string): string {
  let out = text.replace(/­/g, '');
  out = out.replace(POWER, (_m, d: string, minus: string, digits: string) => `${d}^${minus ? '-' : ''}${foldSup(digits)}`);
  out = out.replace(UNIT_EXP, (_m, digits: string) => `-${foldSup(digits)}`);
  out = out.replace(DASHES, '-').replace(SUP_ANY, (ch) => SUP_TO_DIGIT[ch] ?? ch);
  return out.replace(/\s+/g, ' ').trim();
}

/**
 * Where a quote sits in a section's ORIGINAL text, found the way the service
 * finds it: both normalised, then the match mapped back to the original
 * offsets, so a highlight lands on the paper's own characters. Exact first,
 * because it is cheap and usually right. null when the quote is not there.
 */
export function locateQuote(text: string, quote: string): { start: number; end: number } | null {
  if (!quote) return null;
  const exact = text.indexOf(quote);
  if (exact >= 0) return { start: exact, end: exact + quote.length };

  const needle = normalizeText(quote);
  if (!needle) return null;
  // Normalise the text one character at a time, remembering where each
  // output character came from. Soft hyphens vanish; dashes and superscript
  // digits map one to one; a superscript on a number gains a caret that maps
  // to the same source position; whitespace runs collapse to their first
  // character.
  const out: string[] = [];
  const from: number[] = [];
  const push = (s: string, i: number) => {
    for (const ch of s) {
      out.push(ch);
      from.push(i);
    }
  };
  let prevSpace = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '­') continue;
    if (/\s/.test(ch)) {
      if (!prevSpace) push(' ', i);
      prevSpace = true;
      continue;
    }
    prevSpace = false;
    if (ch === '⁻') {
      // Superscript minus: a power on a preceding digit ('10⁻⁶' → '10^-6'),
      // a unit exponent otherwise ('L⁻¹' → 'L-1').
      const lastDigit = out.length > 0 && /\d/.test(out[out.length - 1]);
      push(lastDigit ? '^-' : '-', i);
      continue;
    }
    if (SUP_TO_DIGIT[ch] !== undefined) {
      const prev = out[out.length - 1];
      const prevPrev = out[out.length - 2];
      const afterDigit = /\d/.test(prev ?? '') || (prev === ' ' && /\d/.test(prevPrev ?? ''));
      const afterCaret = prev === '-' && prevPrev === '^';
      const inPower = afterCaret || (SUP_TO_DIGIT[text[i - 1] ?? ''] !== undefined && out.includes('^'));
      if (afterDigit && !inPower) {
        if (prev === ' ') {
          out.pop();
          from.pop();
        }
        push('^', i);
      }
      push(SUP_TO_DIGIT[ch], i);
      continue;
    }
    if (DASHES.test(ch)) {
      DASHES.lastIndex = 0;
      push('-', i);
      continue;
    }
    DASHES.lastIndex = 0;
    push(ch, i);
  }
  const hay = out.join('');
  const at = hay.indexOf(needle);
  if (at < 0) return null;
  const start = from[at];
  const last = from[at + needle.length - 1];
  return { start, end: last + 1 };
}

export function paperFetched(paper: Paper | undefined): paper is Paper {
  return !!paper && paper.textSource === 'full-text' && paper.sections.length > 0;
}

export function paperIdentified(paper: Paper | undefined): boolean {
  return !!paper && !!(paper.pmcid || paper.doi || paper.pmid);
}

/**
 * Whether the record's own quote is in its section of the FETCHED text, the
 * way the service looks for it. null when the paper has no fetched text:
 * there is nothing to anchor to, which is a different fact from "not found".
 */
export function quoteAnchors(record: Quoted, paper: Paper | undefined): boolean | null {
  if (!paperFetched(paper)) return null;
  const section = paper.sections.find((s) => s.id === record.sectionId);
  return !!section && locateQuote(section.text, record.quote) !== null;
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

export interface CarriedSpan {
  quote: string;
  sectionId: string;
  candidateId: string;
  /**
   * The number as the paper's sentence writes it. The service anchors a
   * promotion's value inside its quote to 0.5 % with no unit conversion
   * (§2.4 rule 3), so a record re-anchored to a candidate's sentence takes
   * the candidate's value and unit — within 2 % of the curated one, which is
   * why the span was carried at all — as its correction.
   */
  value: number | string;
  unit: string;
}

/**
 * The span a promotion carries (§7.3): when the curated quote is NOT in the
 * fetched text and an agreeing candidate's is, accept and gold re-anchor the
 * record to the candidate's quote, section, value and unit, so the promoted
 * record stands in the paper's own words and says the paper's own number.
 * null when the record's quote already anchors, when nothing is fetched, or
 * when no candidate agrees — a disagreeing span is not carried, because the
 * reviewer is promoting the curated value.
 */
export function carryOverSpan(
  record: ExtractionRecord,
  paper: Paper | undefined,
  candidates: Candidate[],
): CarriedSpan | null {
  if (quoteAnchors(record, paper) !== false) return null;
  const best = bestCandidate(record, candidates);
  if (!best || !best.agrees) return null;
  const c = best.candidate;
  return { quote: c.quote, sectionId: c.sectionId, candidateId: c.id, value: c.value, unit: c.unit };
}

export type ReviewAction = 'accept' | 'reject' | 'gold';

/**
 * Why `biorepo.write` would refuse this decision (§2.3), in words the
 * reviewer can act on — or null when it would be stored. Applies only while
 * the service is up: offline, the Durable tier keeps behaving as it always
 * has, and `syncDecisions` asks this again before posting.
 *
 *   paper     no PMCID, DOI or PMID — the committed file may not name it
 *   fulltext  a promotion (accept, gold) needs the paper's fetched text
 *   quote     gold needs a sentence in that text that says this number
 */
export function writeRefusal(
  action: ReviewAction,
  record: ExtractionRecord,
  paper: Paper | undefined,
  candidates: Candidate[],
  serviceUp: boolean | null,
): string | null {
  if (!serviceUp) return null;
  if (!paperIdentified(paper)) {
    return `${record.paperId} carries no PMCID, DOI or PMID, so the service keeps no decision about it. It can still be reviewed in this browser.`;
  }
  if (action === 'reject') return null;
  if (!paperFetched(paper)) {
    return `${action === 'gold' ? 'Gold' : 'Accept'} needs the paper's full text, and ${record.paperId} has not been fetched. Fetch it from Intake first.`;
  }
  if (action !== 'gold') return null;
  // A candidate's quote anchored when it was extracted; the service will find it.
  if (record.extractorRun === EXTRACTOR_RUN) return null;
  if (quoteAnchors(record, paper)) return null;
  if (carryOverSpan(record, paper, candidates)) return null;
  return 'Gold needs a sentence in the fetched text that says this number. The curated quote is not in it, and the extractor found no span that agrees.';
}

/** Kept for callers that only ask about gold. */
export function goldRefusal(
  record: ExtractionRecord,
  paper: Paper | undefined,
  candidates: Candidate[],
  serviceUp: boolean | null,
): string | null {
  return writeRefusal('gold', record, paper, candidates, serviceUp);
}
