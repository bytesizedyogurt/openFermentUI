// The review boundary, browser side (OF-BLD-012 §7.3).
//
// Pure functions over a record and its paper: how a quote is looked for in
// the document's text, and why the service would refuse a decision before the
// reviewer presses the key. `biorepo.write` on the service is the authority
// (§2.3); these exist so the screen says the same thing the service would, one
// keystroke earlier.
//
// The review family is named here, each a generated schema of the service's
// answers (ADR-007): a candidate, a reviewer's decision on it, the service's
// verdict on a decision before it is sent, an extractor run as witness.py
// scores it, and the overlay that carries them with the documents the project
// holds. The record and the paper are the store's own shapes of them.
import type { components } from '@/api/types.gen';
import { isFieldId, type FieldId } from '@/data/ontology';

type S = components['schemas'];

/** An extraction the anchoring rules kept (OF-BLD-012 §2.4), before a reviewer has looked at it. */
export type Candidate = S['Candidate'];
/** What a reviewer decided about one record (§7.1), as the service keeps it and the Durable tier holds it. */
export type ReviewDecision = S['ReviewDecision'];
/** POST /api/biorepo/check: whether the service would keep a decision, and the rule it would refuse it under. */
export type DecisionCheck = S['DecisionCheck'];
export type RecordStatus = Candidate['status'];
/** The extractor run a candidate came from: 'claude-1', the run that runs (§6). */
export type ExtractorRun = Candidate['extractorRun'];
/**
 * One line of a record's audit trail, as the page writes it: who did what and
 * when, with the value before and after when a value changed.
 */
export type AuditLine = Omit<S['AuditEvent'], 'from' | 'to'> & Partial<Pick<S['AuditEvent'], 'from' | 'to'>>;
/** One extractor run as witness.py scores it against the values reviewers typed (§6.2). */
export type RunOutput = S['ExtractRun'];
/** GET /api/biorepo/overlay: the documents the project holds, its decisions, its candidates and its runs. */
export type Overlay = S['Overlay'];
/** One document the project holds, as the overlay carries it (ADR-002). */
export type OverlayPaper = S['OverlayPaper'];

/**
 * A document the project holds, as the store keeps it: the overlay's entry
 * under its id, its title the kit's citation or, when the kit holds none, the
 * id itself.
 */
export type Paper = OverlayPaper & { id: string; title: string };

/**
 * A record: a candidate with the review layer over it (§7.3). The decision's
 * gold, correction and reviewer; the audit trail; what it was published as,
 * stamped once as it enters the store (OF-BLD-012.1 F7); and whether the
 * extractor's current run still reads it (F3). Its field is one the ontology
 * names, checked as it enters the store (`recordOf`).
 */
export type ExtractionRecord = Omit<Candidate, 'field'> & {
  field: FieldId;
  gold?: ReviewDecision['gold'];
  corrected?: ReviewDecision['corrected'];
  reviewer?: ReviewDecision['reviewer'];
  audit: AuditLine[];
  original?: { value: number | string; unit: string; quote: string; sectionId: string };
  absentFromRun?: boolean;
};

/**
 * A candidate as a record entering the store, with no decision yet and an
 * empty audit trail; null when its field is one the ontology does not name,
 * since every reader of a record indexes the ontology by its field.
 */
export function recordOf(c: Candidate): ExtractionRecord | null {
  const { field } = c;
  return isFieldId(field) ? { ...c, field, audit: [] } : null;
}

// ── §2.4 rule 2's normalisation, the browser's copy ─────────────────────
//
// The service looks for a quote in a section AFTER folding both through
// validate.normalize_text: soft hyphens dropped, every dash variant to '-',
// a superscript on a unit to '-1', a superscript on a number to '^6',
// whitespace runs to one space. The browser must look the same way, or a
// candidate the service anchored renders as "quote not located" here.
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
  // output character came from, with the same decisions validate.py's
  // regexes make on the RAW text — which is why every look-back below reads
  // `text`, never `out`. Soft hyphens vanish. A superscript run is a power
  // ('10⁶' → '10^6', '10⁻⁶' → '10^-6') when the raw character before it is a
  // digit, or exactly one ASCII space after a digit (the space is dropped);
  // a superscript digit after another superscript digit or a superscript
  // minus continues that run; anywhere else a superscript minus is a unit
  // exponent ('L⁻¹' → 'L-1') and a superscript digit is just its digit.
  // Dashes map one to one; whitespace runs collapse to their first character.
  const out: string[] = [];
  const from: number[] = [];
  const push = (s: string, i: number) => {
    for (const ch of s) {
      out.push(ch);
      from.push(i);
    }
  };
  const isDigit = (ch: string | undefined) => !!ch && ch >= '0' && ch <= '9';
  const isSupDigit = (ch: string | undefined) => !!ch && SUP_TO_DIGIT[ch] !== undefined;
  // The raw character n places before i, skipping soft hyphens, as the
  // service sees it after its first replace.
  const rawBefore = (i: number, n: number): string | undefined => {
    let j = i;
    for (let k = 0; k < n; k++) {
      j--;
      while (j >= 0 && text[j] === '\u00ad') j--;
      if (j < 0) return undefined;
    }
    return text[j];
  };
  const rawAfter = (i: number): string | undefined => {
    let j = i + 1;
    while (j < text.length && text[j] === '\u00ad') j++;
    return text[j];
  };
  // Whether a superscript at i starts a power: `(?<=\d) ?` in validate.py.
  const startsPower = (i: number): 'digit' | 'space' | null => {
    const p1 = rawBefore(i, 1);
    if (isDigit(p1)) return 'digit';
    if (p1 === ' ' && isDigit(rawBefore(i, 2))) return 'space';
    return null;
  };
  const dropSpace = () => {
    // The single space the power swallows is the last output character.
    if (out[out.length - 1] === ' ') {
      out.pop();
      from.pop();
    }
  };
  let prevSpace = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '\u00ad') continue;
    if (/\s/.test(ch)) {
      if (!prevSpace) push(' ', i);
      prevSpace = true;
      continue;
    }
    prevSpace = false;
    if (ch === '⁻') {
      const power = isSupDigit(rawAfter(i)) ? startsPower(i) : null;
      if (power === 'space') dropSpace();
      push(power ? '^-' : '-', i);
      continue;
    }
    if (isSupDigit(ch)) {
      const before = rawBefore(i, 1);
      const continues = isSupDigit(before) || before === '⁻';
      const power = continues ? null : startsPower(i);
      if (power === 'space') dropSpace();
      if (power) push('^', i);
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

/**
 * Whether the project holds the paper, the service's rule for a decision
 * (`biorepo._held`): a decision stands on a document a reader can look up.
 * Every paper the store keeps is one the overlay names as held (ADR-002).
 */
export function paperHeld(paper: Paper | undefined): boolean {
  return paper !== undefined;
}

export type ReviewAction = 'accept' | 'reject' | 'gold';

/**
 * Why `biorepo.write` would refuse a decision, by the rule it would name
 * (§2.3). `browserOnly` marks the one refusal that does not stop the review:
 * a paper with no identifier can still be decided here — the Durable tier
 * keeps the decision, the service is simply never asked — where the other
 * two mean the action cannot be taken at all until something changes.
 */
/** The rules `biorepo.write` refuses under (§2.3). The service names one; the fallback below can only see three of them. */
export type RefusalRule = 'record' | 'reviewer' | 'fulltext' | 'quote' | 'paper' | 'unit' | 'status';

export interface Refusal {
  rule: RefusalRule;
  why: string;
  browserOnly: boolean;
}

/**
 * THE OFFLINE FALLBACK (OF-BLD-012.1 F1.5). While the service is up, Guild
 * asks `POST /api/biorepo/check` and gates on THAT answer: the rules live in
 * `biorepo.write` and are not mirrored here, because a mirror of a rule is a
 * second rule that drifts. This function is what the screen falls back to
 * when the check has not answered yet, and what `syncDecisions` asks before
 * posting a decision made while the service was away. It can only see the
 * four conditions the browser has the facts for:
 *
 *   reviewer  nobody has set a name in Settings (F2)
 *   paper     a document the project does not hold; decided in this
 *             browser only
 *   fulltext  a promotion (accept, gold) needs the document's text
 *
 * A candidate's quote anchored in that text when it was extracted, so gold
 * asks nothing more here.
 *
 * It cannot see `range`, `status` or `record`, and it does not try: those
 * come back from the check.
 */
export function writeRefusal(
  action: ReviewAction,
  record: ExtractionRecord,
  paper: Paper | undefined,
  serviceUp: boolean | null,
  reviewer: string | null,
): Refusal | null {
  if (!serviceUp) return null;
  // A decision nobody signed is not a decision the project can keep
  // (OF-BLD-012.1 F2). Asked first, because it is the one refusal the
  // reviewer can clear in five seconds.
  if (!reviewer || !reviewer.trim()) {
    return {
      rule: 'reviewer',
      browserOnly: false,
      why: 'Set your reviewer name in Settings before deciding — the project records who decided what.',
    };
  }
  if (!paperHeld(paper)) {
    return {
      rule: 'paper',
      browserOnly: true,
      why: `${record.paperId} is not a document this project holds, so the service keeps no decision about it. It is reviewed in this browser only.`,
    };
  }
  if (action === 'reject') return null;
  if (!paperFetched(paper)) {
    return {
      rule: 'fulltext',
      browserOnly: false,
      why: `${action === 'gold' ? 'Gold' : 'Accept'} needs the document's text, and the project holds none for ${record.paperId}. Collect it again from Intake first.`,
    };
  }
  return null;
}

/**
 * The service's answer as a refusal the card can render. The rule is the
 * service's; the WORDS are this file's when it names the same rule, because
 * `biorepo.write`'s reasons are written for a log and these are written for
 * a reviewer holding a pipette.
 */
export function refusalOf(check: DecisionCheck, fallback: Refusal | null): Refusal | null {
  if (check.ok) return null;
  const rule = (check.rule ?? 'fulltext') as RefusalRule;
  return {
    rule,
    why:
      fallback && fallback.rule === rule
        ? fallback.why
        : (check.why ?? 'The service would not keep this decision.'),
    // A paper with no identifier is still reviewable here; everything else stops the action.
    browserOnly: rule === 'paper',
  };
}

/**
 * The decision an action would post, built the way the store builds it, so
 * the question the screen asks is the decision it would send (F1.5).
 */
export function decisionToCheck(action: 'accept' | 'gold', record: ExtractionRecord, reviewer: string): ReviewDecision {
  const corrected = record.corrected;
  return {
    status: 'verified',
    provenance: record.provenance,
    corrected,
    gold:
      action === 'gold'
        ? (record.gold ?? { value: corrected?.value ?? record.value, unit: corrected?.unit ?? record.unit })
        : undefined,
    rejectReason: undefined,
    reviewer,
    recordId: record.id,
    at: new Date().toISOString(),
  };
}

/** A refusal that stops the action, as opposed to one that only keeps it out of the service. */
export function blocks(refusal: Refusal | null): boolean {
  return !!refusal && !refusal.browserOnly;
}
