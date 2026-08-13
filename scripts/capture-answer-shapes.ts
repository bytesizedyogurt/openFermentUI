/**
 * Pin the ANSWER SHAPES of the scripted agent, as language-neutral JSON, before
 * the scripted agent is retired.
 *
 * WHY THIS EXISTS
 * ---------------
 * `src/data/flows.ts` is going away. A real model will answer instead. What the
 * model produces still has to LOOK like this: the same plan granularity, the
 * same tool sequence, citation chips in the same places relative to the claims
 * they support, the same standing note at the foot of the answer. Those are the
 * formatter's job, and a formatter has no regression harness unless the current
 * shape is written down before it is deleted.
 *
 * So this captures SHAPE, not prose. It does not copy `answerMd`. It records how
 * many plan steps there are and what each one is FOR; the order and names of the
 * tool calls and what each is GIVEN; which calls carry a retrieval set and how
 * that set renders; every citation chip's position relative to the sentence and
 * the claim around it; and what the closing standing note asserts. A different
 * answer, written by a different model about the same question, can be checked
 * against this. A copy of flows.ts could not.
 *
 * WHAT IS DERIVED AND WHAT IS ASSERTED
 * ------------------------------------
 * Everything under `flows` and `aggregate` is DERIVED from the `FLOWS` array by
 * the code below — nothing is transcribed by hand, because the one case somebody
 * forgot to type in is the one that would drift silently.
 *
 * Two things are ASSERTED rather than derived, and both say so in the JSON:
 *   - `renderingContract` — what `src/screens/Ask.tsx` and `src/sim/chat.ts` do
 *     with a flow. It is read out of those files, not computed, so it carries
 *     the file it was read from and will need re-reading if they change.
 *   - `flows[].shape.name` — a human name for the answer's overall form. The
 *     features that justify each name are derived alongside it, so the name is
 *     auditable rather than decorative.
 *
 * THE PROSE THAT IS KEPT, AND WHY
 * -------------------------------
 * Four kinds of verbatim text survive, because in each case the text IS the
 * shape and a paraphrase would destroy the thing being pinned:
 *   - plan step text — a plan step is not prose, it is the plan;
 *   - bold lead-in labels — they are the answer's section structure;
 *   - table headers — they are the table's schema;
 *   - the closing standing note — CLAUDE.md forbids deleting the honesty policy,
 *     so the regression target is the sentence itself, not a gloss of it.
 * Answer body prose, retrieval snippets and `corpus.search` query strings are
 * deliberately NOT captured. The real agent writes its own.
 *
 * Nothing here changes behaviour. It only observes it.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { FLOWS, SUGGESTED_PROMPTS } from '../src/data/flows';
import { PAPERS, RECORDS } from '../src/data/source';
import type { ChatFlow, ChatToolCall } from '../src/data/types';

const OUT = join(process.cwd(), 'fixtures');
mkdirSync(OUT, { recursive: true });

/** Codepoint order, not locale order. `localeCompare` depends on the ICU build;
 *  two machines must produce the same bytes. */
const byCode = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** A counter map with keys emitted in codepoint order, so the JSON is stable. */
function tally(xs: string[]): Record<string, number> {
  const m = new Map<string, number>();
  for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1);
  return Object.fromEntries([...m.entries()].sort((a, b) => byCode(a[0], b[0])));
}

const uniq = (xs: string[]) => [...new Set(xs)];

// ══ Taxonomies ═════════════════════════════════════════════════════════
//
// Each is a small ordered rule list. Order is load-bearing: the first rule that
// fires wins, and the rule that fired is recorded next to the answer so a
// reader can disagree with the classification without having to re-derive it.

/**
 * What a plan step is FOR. This is the granularity a real agent's plan has to
 * reproduce — five steps that parse, retrieve, guard and deliver, not one step
 * saying "answer the question" and not fifteen saying nothing.
 */
const PLAN_ROLE_RULES: [role: string, verbs: RegExp][] = [
  ['parse', /^Parse\b/],
  ['retrieve', /^(Retrieve|Search)\b/],
  ['query', /^Query\b/],
  // A step that must pass before the answer may be written: look for
  // counter-evidence, check isPrimary before double-counting, detect a
  // disagreement, refuse a conversion, flag a negative result.
  ['guard', /^(Check|Detect|Verify|Flag|Normalise|Normalize)\b/],
  // Organise the evidence: split it, separate it, rank it, map it onto records.
  ['shape', /^(Split|Separate|Rank|Map|Partition|Attach)\b/],
  // Emit it.
  ['deliver', /^(Assemble|Report|Present|State|Connect|Compose)\b/],
];

const PLAN_ROLE_DOC: Record<string, string> = {
  parse: 'Restate the question in ontology terms — field ids, organism ids, target.',
  retrieve: 'Pull passages from the corpus.',
  query: 'Query the structured record store.',
  guard: 'A check that must pass before the answer may be written — counter-evidence, isPrimary, conflict detection, a refused unit conversion, a negative result to flag.',
  shape: 'Organise the retrieved evidence: split, separate, rank, map.',
  deliver: 'Assemble, report or state the answer.',
  unclassified: 'No rule fired. Add a rule rather than leaving this in a fixture.',
};

/** What immediately precedes a chip. The distinction that matters: a record
 *  chip trailing a QUANTITY is discharging that number's citation; a paper chip
 *  at BLOCK-START is the subject of the sentence it opens. */
const PRECEDED_BY_DOC: Record<string, string> = {
  'block-start': 'Chip is the first token of its block — paper chip in subject position.',
  'cell-start': 'Chip is the first token of a table cell.',
  'bold-quantity': 'Immediately after a bolded number — "**500 mg/L** [[r-H2-1]]".',
  quantity: 'Immediately after an unbolded number within the last three tokens.',
  'bold-word': 'Immediately after a bolded non-numeric span.',
  word: 'Mid-prose, after ordinary words — the chip discharges a clause, not a number.',
  chip: 'Immediately after another chip — a chip run.',
  punctuation: 'After a comma, dash or colon.',
};

const FOLLOWED_BY_DOC: Record<string, string> = {
  period: 'Sentence ends immediately after the chip.',
  comma: 'Clause ends immediately after the chip.',
  semicolon: 'Clause ends immediately after the chip.',
  'em-dash': 'An aside opens immediately after the chip.',
  chip: 'Another chip follows — a chip run.',
  word: 'The sentence continues past the chip.',
  'block-end': 'Chip is the last token of its block.',
  'cell-end': 'Chip is the last token of its table cell.',
};

const SLOT_DOC: Record<string, string> = {
  'sentence-lead': 'First token of a sentence. The dominant paper-chip position: the entry is the grammatical subject of the claim it supports.',
  'sentence-final': 'Last token before the sentence terminator.',
  'clause-final': 'Last token before a comma or semicolon.',
  'mid-sentence': 'Inside a sentence with words on both sides.',
  'cell-only': 'The table cell contains nothing but the chip.',
  'cell-lead': 'First token of a table cell, with more after it.',
  'cell-trailing': 'Last token of a table cell — the cell states a value, the chip cites it.',
  'cell-mid': 'Inside a table cell with content on both sides.',
};

/** What the closing standing note asserts. Multiple tags may fire on one note. */
const FOOTER_CLAIM_RULES: [tag: string, re: RegExp][] = [
  ['curator-transcription', /curator|curation note|transcri/i],
  ['catalogued-not-ingested', /catalogued/i],
  ['verify-before-citing', /verif|confirmed against|before it is quoted|pending/i],
  ['not-read-from-source', /not read|has not been read|reading the PDF|source PDF|both PDFs|read in full/i],
  ['authored-judgement', /is mine|I decline|honesty note/i],
  ['scope-limit', /never on a casein|does not say|were measured on|rather than cw15|no extraction record|unnamed/i],
  ['absence-is-a-finding', /nothing exists|returns nothing|took curation/i],
];

const FOOTER_CLAIM_DOC: Record<string, string> = {
  'curator-transcription': 'States the numbers came from a curator note, not a source PDF.',
  'catalogued-not-ingested': 'Names the entries as catalogued — metadata plus a note, no full text.',
  'verify-before-citing': 'Tells the reader to verify before citing.',
  'not-read-from-source': 'Names something the corpus has not read and therefore cannot claim.',
  'authored-judgement': 'Marks part of the answer as the agent’s own judgement rather than corpus fact.',
  'scope-limit': 'Bounds what the cited evidence covers — measured on a reporter, on the wild type, on a different organism.',
  'absence-is-a-finding': 'States that the absence itself is the curated result.',
};

/**
 * The two decline shapes. These are the ones most likely to be lost when a real
 * model takes over, because a model's default is to answer.
 *
 * Each move is a structural obligation, matched against the answer by a marker.
 * A marker that stops matching means the shape has been lost.
 */
const DECLINE_MOVES: Record<string, { kind: string; moves: [name: string, marker: RegExp][] }> = {
  F6: {
    kind: 'absence',
    moves: [
      ['verdict-first', /^\*\*No\.\*\*/],
      ['absence-is-structural-not-retrieval-failure', /structural, not a retrieval failure/],
      ['show-the-search-that-was-done', /systematic search/],
      ['enumerate-what-was-found-instead', /bacterial studies/],
      ['name-the-nearest-adjacent-thing', /nearest published work/],
      ['state-what-the-absence-means', /\*\*What the absence means\.\*\*/],
      ['name-what-could-overturn-it', /caveats|flagged for verification/],
      ['absence-is-the-curated-result', /Recording why nothing exists/],
    ],
  },
  'F-SIALYL': {
    kind: 'adjudication',
    moves: [
      ['refuse-up-front', /not going to resolve it for you/],
      ['label-position-a', /\*\*Position A/],
      ['label-position-b', /\*\*Position B/],
      ['state-the-incompatibility', /\*\*These are incompatible\.\*\*/],
      ['refuse-to-average', /I decline to adjudicate/],
      ['name-why-neither-wins', /method: undetermined|no third entry/],
      ['bound-the-stake', /the stake is bounded/],
    ],
  },
};

/** A human name for the answer's overall form. Asserted, not derived — the
 *  derived features that justify each one travel next to it in the JSON. */
const SHAPE_NAMES: Record<string, string> = {
  F1: 'table-enumeration',
  F2: 'partitioned-verdicts',
  F3: 'product-fork',
  F4: 'single-value-with-provenance-chain',
  F5: 'reasons-and-counterweights',
  F6: 'decline-absence',
  F7: 'ranked-recommendation',
  F8: 'method-table',
  F9: 'head-to-head',
  F10: 'provenance-partition',
  F11: 'mechanism-with-limit',
  F12: 'jurisdiction-split',
  'F-SIALYL': 'decline-adjudication',
};

// ══ Markdown block grammar ═════════════════════════════════════════════
//
// Mirrors the grammar in src/components/Markdown.tsx — table, list, ordered
// list, heading, blockquote, paragraph — because the block a chip sits in is a
// rendering fact and has to be counted the way the renderer counts it. This is
// an analysis of the text, not a second renderer: it produces no output.

interface Block {
  index: number;
  kind: 'paragraph' | 'table' | 'list' | 'ordered-list' | 'heading' | 'blockquote';
  /** Paragraph / list-item / heading text, joined the way Markdown.tsx joins it. */
  text: string;
  /** Table only. */
  headers?: string[];
  aligns?: ('left' | 'right')[];
  rows?: string[][];
  items?: string[];
}

function parseBlocks(md: string): Block[] {
  const lines = md.split('\n');
  const blocks: Block[] = [];
  let i = 0;
  const push = (b: Omit<Block, 'index'>) => blocks.push({ index: blocks.length, ...b });

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith('|') && lines[i + 1]?.includes('---')) {
      const cells = (l: string) => l.split('|').slice(1, -1).map((c) => c.trim());
      const headers = cells(line);
      const aligns = cells(lines[i + 1]).map((c) => (c.endsWith(':') ? 'right' : 'left') as 'left' | 'right');
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]));
      push({ kind: 'table', text: '', headers, aligns, rows });
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s+/, ''));
      push({ kind: 'list', text: items.join(' '), items });
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+\.\s+/, ''));
      push({ kind: 'ordered-list', text: items.join(' '), items });
      continue;
    }

    if (/^#{2,4}\s+/.test(line)) {
      push({ kind: 'heading', text: line.replace(/^#+\s+/, '') });
      i++;
      continue;
    }

    if (line.trim().startsWith('> ')) {
      const quoted: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) quoted.push(lines[i++].replace(/^\s*>\s?/, ''));
      push({ kind: 'blockquote', text: quoted.join(' ') });
      continue;
    }

    if (line.trim() === '') {
      i++;
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^\s*([-*]|\d+\.)\s+/.test(lines[i]) &&
      !lines[i].trim().startsWith('|') &&
      !/^#{2,4}\s/.test(lines[i]) &&
      !lines[i].trim().startsWith('> ')
    ) {
      para.push(lines[i]);
      i++;
    }
    if (para.length === 0) para.push(lines[i++]);
    push({ kind: 'paragraph', text: para.join(' ') });
  }
  return blocks;
}

// ══ Citation chip placement ════════════════════════════════════════════

const CHIP_RE = /\[\[([A-Za-z0-9-]+)\]\]/g;
/** Same pattern, unsticky. A `/g` regex carries `lastIndex` between `.test()`
 *  calls, which silently halves the count on the second cell. */
const CHIP_TEST = /\[\[[A-Za-z0-9-]+\]\]/;

/** Sentence boundary: a terminator, optionally inside a bold run, then space.
 *  "**No.** And the absence" breaks after "**No.**", not after "No." */
const SENTENCE_SPLIT = /(?<=[.!?]\*{0,2})\s+/;

/** The renderer's own rule (src/components/Markdown.tsx): an id starting `r-`
 *  is a record chip, anything else is a paper chip. */
const chipKind = (id: string) => (id.startsWith('r-') ? 'record' : 'paper');

/**
 * Does this token open with a number?
 *
 * "any digit anywhere" is the wrong test and was the first thing tried. This
 * corpus is full of identifiers that carry digits without being quantities —
 * CK2, FAM20C, GS115, D478A, Man5GlcNAc2, UVM4, and every chip id — and a chip
 * after "…with CK2 — yes.**" is discharging a verdict, not a measurement.
 * Requiring the digit to LEAD the token separates "500 mg/L" and "$4–6/kg" from
 * "CK2", and leading markdown or bracketing is stripped first so that "**500"
 * and "~**0.2" still read as numbers.
 */
const opensWithNumber = (tok: string) => /^\d/.test(tok.replace(/^[*_~(\[$≈±]+/, ''));

function classifyBefore(before: string, atCellStart: boolean): string {
  const t = before.trimEnd();
  if (t === '') return atCellStart ? 'cell-start' : 'block-start';
  if (t.endsWith(']]')) return 'chip';
  const boldAdjacent = t.endsWith('**');
  const bare = t.replace(/\*+$/, '').trimEnd();
  if (bare === '') return atCellStart ? 'cell-start' : 'block-start';
  // Three tokens is the window a quantity fits in: "reached 500 mg/L".
  const window = bare.split(/\s+/).slice(-3);
  if (window.some(opensWithNumber)) return boldAdjacent ? 'bold-quantity' : 'quantity';
  if (/[,;:—–-]$/.test(bare)) return 'punctuation';
  return boldAdjacent ? 'bold-word' : 'word';
}

function classifyAfter(after: string, inCell: boolean): string {
  const t = after.replace(/^\s+/, '');
  if (t === '') return inCell ? 'cell-end' : 'block-end';
  if (t.startsWith('[[')) return 'chip';
  if (t.startsWith('.')) return 'period';
  if (t.startsWith(',')) return 'comma';
  if (t.startsWith(';')) return 'semicolon';
  if (t.startsWith('—') || t.startsWith('–')) return 'em-dash';
  return 'word';
}

function proseSlot(before: string, after: string): string {
  const startsSentence = before.trim() === '' || /(?:[.!?]\*{0,2})\s+$/.test(before);
  if (startsSentence) return 'sentence-lead';
  const t = after.replace(/^\s+/, '');
  if (t === '' || /^[.!?]/.test(t)) return 'sentence-final';
  if (/^[,;]/.test(t)) return 'clause-final';
  return 'mid-sentence';
}

function cellSlot(cell: string, before: string, after: string): string {
  if (/^\s*(\[\[[A-Za-z0-9-]+\]\]\s*)+$/.test(cell)) return 'cell-only';
  if (before.trim() === '') return 'cell-lead';
  if (after.trim() === '') return 'cell-trailing';
  return 'cell-mid';
}

interface Placement {
  id: string;
  kind: 'paper' | 'record';
  block: number;
  blockKind: Block['kind'];
  /** Table only. */
  row?: number;
  column?: number;
  columnHeader?: string;
  slot: string;
  precededBy: string;
  followedBy: string;
  /** 1 for a lone chip; 2+ for consecutive chips like "[[r-G9-3]] [[r-G9-4]]". */
  runLength: number;
  runPosition: number;
}

/** Walk one text fragment, emitting a placement per chip. */
function walkFragment(
  text: string,
  base: Omit<Placement, 'id' | 'kind' | 'slot' | 'precededBy' | 'followedBy' | 'runLength' | 'runPosition'>,
  inCell: { cell: string } | null,
): Placement[] {
  const out: Placement[] = [];
  const hits = [...text.matchAll(new RegExp(CHIP_RE.source, 'g'))];
  // Runs: chips separated by nothing but whitespace.
  const runIndex: number[] = [];
  const runSize: number[] = [];
  let r = 0;
  for (let n = 0; n < hits.length; n++) {
    if (n > 0) {
      const gap = text.slice(hits[n - 1].index! + hits[n - 1][0].length, hits[n].index!);
      if (gap.trim() !== '') r++;
    }
    runIndex.push(r);
  }
  for (let n = 0; n < hits.length; n++) runSize[n] = runIndex.filter((x) => x === runIndex[n]).length;

  for (let n = 0; n < hits.length; n++) {
    const h = hits[n];
    const before = text.slice(0, h.index!);
    const after = text.slice(h.index! + h[0].length);
    out.push({
      ...base,
      id: h[1],
      kind: chipKind(h[1]),
      slot: inCell ? cellSlot(inCell.cell, before, after) : proseSlot(before, after),
      precededBy: classifyBefore(before, inCell !== null),
      followedBy: classifyAfter(after, inCell !== null),
      runLength: runSize[n],
      runPosition: runIndex.slice(0, n).filter((x) => x === runIndex[n]).length + 1,
    });
  }
  return out;
}

function placements(blocks: Block[]): Placement[] {
  const out: Placement[] = [];
  for (const b of blocks) {
    if (b.kind === 'table') {
      b.headers?.forEach((h, c) =>
        out.push(...walkFragment(h, { block: b.index, blockKind: b.kind, row: -1, column: c, columnHeader: h }, { cell: h })),
      );
      b.rows?.forEach((row, ri) =>
        row.forEach((cell, ci) =>
          out.push(
            ...walkFragment(
              cell,
              { block: b.index, blockKind: b.kind, row: ri, column: ci, columnHeader: b.headers?.[ci] ?? '' },
              { cell },
            ),
          ),
        ),
      );
      continue;
    }
    if (b.items) {
      b.items.forEach((it) => out.push(...walkFragment(it, { block: b.index, blockKind: b.kind }, null)));
      continue;
    }
    out.push(...walkFragment(b.text, { block: b.index, blockKind: b.kind }, null));
  }
  return out;
}

// ══ Per-flow derivation ════════════════════════════════════════════════

const PAPER_IDS = new Set(PAPERS.map((p) => p.id));
const RECORD_IDS = new Set(RECORDS.map((r) => r.id));

function planShape(flow: ChatFlow) {
  const steps = flow.plan.map((text, index) => {
    const role = PLAN_ROLE_RULES.find(([, re]) => re.test(text))?.[0] ?? 'unclassified';
    const dash = text.indexOf(' — ');
    return {
      index,
      role,
      verb: text.split(/\s+/)[0],
      /** The clause after the em dash, where a step names its ontology terms. */
      qualifier: dash >= 0 ? text.slice(dash + 3) : null,
      words: text.split(/\s+/).length,
      text,
    };
  });
  const roles = steps.map((s) => s.role);
  return {
    stepCount: steps.length,
    roles,
    signature: roles.join(' → '),
    opensWithParse: roles[0] === 'parse',
    hasGuardStep: roles.includes('guard'),
    endsWithDelivery: roles[roles.length - 1] === 'deliver',
    steps,
  };
}

/** What a tool call is GIVEN, with the free-text query dropped on purpose. */
function callShape(call: ChatToolCall, index: number) {
  const args = call.args as Record<string, unknown>;
  const argKeys = Object.keys(args).sort(byCode);
  const filters = (args.filters ?? null) as Record<string, unknown> | null;
  const fields = Array.isArray(args.fields)
    ? (args.fields as string[])
    : typeof args.field === 'string'
      ? [args.field as string]
      : [];
  /** Every arg that is neither the query nor the field list: the qualifiers
   *  that tell the store how to behave — isPrimary, requireMethod, groupBy. */
  const flags = Object.fromEntries(
    argKeys
      .filter((k) => !['query', 'k', 'filters', 'fields', 'field'].includes(k))
      .map((k) => [k, args[k] as unknown]),
  );
  const retrieval = call.retrieval;
  return {
    index,
    name: call.name,
    argKeys,
    /** Retrieval breadth the call asked for. */
    k: typeof args.k === 'number' ? args.k : null,
    /** Corpus dimensions the call narrowed on — thread letters, organism ids. */
    filterKeys: filters ? Object.keys(filters).sort(byCode) : [],
    filters: filters ?? null,
    /** Ontology field ids the record store was asked for. */
    fields,
    fieldCount: fields.length,
    flags,
    /** How src/screens/Ask.tsx renders this call's result. */
    retrievalRendering: retrieval === undefined ? 'none' : retrieval.length === 0 ? 'empty-callout' : 'cards',
    hitCount: retrieval?.length ?? 0,
  };
}

function toolShape(flow: ChatFlow) {
  const calls = flow.toolCalls.map(callShape);
  const signature = calls
    .map((c) => {
      const parts: string[] = [];
      if (c.k !== null) parts.push(`k=${c.k}`);
      if (c.filterKeys.length) parts.push(`filters:${c.filterKeys.join('+')}`);
      if (c.fieldCount) parts.push(`fields×${c.fieldCount}`);
      for (const f of Object.keys(c.flags).sort(byCode)) parts.push(`+${f}`);
      return `${c.name}(${parts.join(', ')})`;
    })
    .join(' → ');
  return {
    count: calls.length,
    names: calls.map((c) => c.name),
    signature,
    opensWithCorpusSearch: calls[0]?.name === 'corpus.search',
    searchCallCount: calls.filter((c) => c.name === 'corpus.search').length,
    /** Which calls carry a retrieval set. In every scripted flow this is the
     *  search call only; the record queries render as a bare tool row. */
    callsCarryingRetrieval: calls.filter((c) => c.retrievalRendering === 'cards').map((c) => c.index),
    calls,
  };
}

function retrievalShape(flow: ChatFlow, citedIds: string[]) {
  const hits = flow.toolCalls.flatMap((c) => c.retrieval ?? []);
  const papers = hits.map((h) => h.paperId);
  const scores = hits.map((h) => h.score);
  const citedPapers = uniq(citedIds.filter((id) => chipKind(id) === 'paper'));
  const citedViaRecord = uniq(
    citedIds
      .filter((id) => chipKind(id) === 'record')
      .map((id) => RECORDS.find((r) => r.id === id)?.paperId ?? '')
      .filter(Boolean),
  );
  const citedAnyway = uniq([...citedPapers, ...citedViaRecord]).sort(byCode);
  const repeats = Object.entries(tally(papers)).filter(([, n]) => n > 1);
  return {
    hitCount: hits.length,
    papers,
    distinctPapers: uniq(papers).length,
    /** A paper retrieved twice is two different passages scored separately —
     *  the card grid shows both, and the second card is not a duplicate. */
    papersRetrievedTwice: repeats.map(([id, n]) => ({ paperId: id, hits: n })),
    sectionIds: uniq(hits.map((h) => h.sectionId)).sort(byCode),
    scores,
    scoresDescending: scores.every((s, i) => i === 0 || s <= scores[i - 1]),
    scoreRange: scores.length ? [Math.min(...scores), Math.max(...scores)] : [],
    snippetChars: scores.length
      ? {
          min: Math.min(...hits.map((h) => h.snippet.length)),
          max: Math.max(...hits.map((h) => h.snippet.length)),
        }
      : null,
    /** The two directions the answer and its retrieval can disagree. Neither is
     *  a defect on its own — an answer may cite a paper it did not need to
     *  re-retrieve — but a real agent that never cites outside its retrieval
     *  set, or never uses what it retrieved, has a different shape from this. */
    retrievedAndCited: uniq(papers).filter((p) => citedAnyway.includes(p)).sort(byCode),
    retrievedNotCited: uniq(papers).filter((p) => !citedAnyway.includes(p)).sort(byCode),
    citedNotRetrieved: citedAnyway.filter((p) => !papers.includes(p)),
  };
}

function firstSentence(text: string): string {
  return text.split(SENTENCE_SPLIT)[0] ?? text;
}

function answerShape(flow: ChatFlow, blocks: Block[]) {
  const table = blocks.find((b) => b.kind === 'table');
  /** A paragraph opening with a bolded label is a section head in disguise;
   *  the labels are the answer's outline. */
  const leadIns = blocks
    .filter((b) => b.kind === 'paragraph')
    .map((b) => b.text.match(/^\*\*(.+?)\*\*/)?.[1] ?? null)
    .filter((x): x is string => x !== null);
  const opening = blocks[0];
  const verdict = firstSentence(opening.text);
  return {
    blockCount: blocks.length,
    blockKinds: blocks.map((b) => b.kind),
    blockSignature: blocks.map((b) => b.kind).join(' → '),
    /** The answer's first sentence. Short and assertive in every flow: the
     *  verdict lands before the evidence, not after it. */
    opening: {
      blockKind: opening.kind,
      firstSentence: verdict,
      words: verdict.split(/\s+/).length,
      leadsWithBold: /^\*\*/.test(opening.text),
    },
    leadInCount: leadIns.length,
    leadIns,
    table: table
      ? {
          headers: table.headers ?? [],
          columns: table.headers?.length ?? 0,
          rows: table.rows?.length ?? 0,
          alignments: table.aligns ?? [],
          /** "An em dash below means the corpus states nothing" (F1). Counted,
           *  because a real agent must be able to leave a cell empty. */
          emDashCells: (table.rows ?? []).flat().filter((c) => c === '—').length,
          cells: (table.rows ?? []).flat().length,
          chipBearingCells: (table.rows ?? []).flat().filter((c) => CHIP_TEST.test(c)).length,
        }
      : null,
  };
}

function footerShape(blocks: Block[]) {
  const last = blocks[blocks.length - 1];
  const t = last.text.trim();
  /** The closing standing note is a whole-paragraph italic run: it opens with a
   *  single `*` and closes with one, and is not a bold `**` lead-in. */
  const isNote = last.kind === 'paragraph' && /^\*[^*]/.test(t) && /[^*]\*$/.test(t);
  const text = isNote ? t.slice(1, -1) : null;
  const claims = isNote ? FOOTER_CLAIM_RULES.filter(([, re]) => re.test(text!)).map(([tag]) => tag) : [];
  return {
    hasStandingNote: isNote,
    /** Verbatim. CLAUDE.md forbids deleting the honesty policy, so the
     *  regression target is the sentence, not a summary of it. */
    text,
    style: isNote ? 'whole-paragraph italic, last block, no chips required' : null,
    words: text ? text.split(/\s+/).length : 0,
    claims,
    closingBlockKind: last.kind,
    /** Flows without a standing note close on a limitation instead — a sentence
     *  saying what the evidence does NOT establish. Same job, different form. */
    closingCarriesNegation: /\bnot\b|\bno\b|\bnever\b|\bbounded\b/i.test(t),
  };
}

function clarifyShape(flow: ChatFlow) {
  if (!flow.clarify) return null;
  const q = flow.clarify.question;
  const sentences = q.split(SENTENCE_SPLIT);
  return {
    /** Verbatim: the question is the shape. Two sentences in both flows — the
     *  fork, then why the fork exists. */
    question: q,
    questionSentences: sentences.length,
    interrogativeFirst: sentences[0].trim().endsWith('?'),
    /** The second sentence justifies asking rather than guessing. */
    justificationSentence: sentences.length > 1 ? sentences.slice(1).join(' ') : null,
    optionCount: flow.clarify.options.length,
    options: flow.clarify.options.map((o) => {
      const dash = o.label.indexOf(' — ');
      return {
        branch: dash >= 0 ? o.label.slice(0, dash) : o.label,
        consequence: dash >= 0 ? o.label.slice(dash + 3) : null,
        label: o.label,
        flowId: o.flowId,
        targetExists: FLOWS.some((f) => f.id === o.flowId),
      };
    }),
    optionLabelForm: flow.clarify.options.every((o) => o.label.includes(' — '))
      ? 'branch — consequence, em-dash separated'
      : 'mixed',
  };
}

function followupShape(flow: ChatFlow) {
  const parsed = flow.followups.map((f) => {
    const isFlow = f.startsWith('flow:');
    const [flowId, label] = isFlow ? f.slice(5).split('|') : ['', f];
    return { flowId, label: label ?? f, targetExists: FLOWS.some((x) => x.id === flowId) };
  });
  return {
    count: parsed.length,
    form: flow.followups.every((f) => /^flow:[^|]+\|.+$/.test(f)) ? 'flow:<id>|<label>' : 'mixed',
    allTargetsResolve: parsed.every((p) => p.targetExists),
    targets: parsed.map((p) => p.flowId),
    labelsAreQuestions: parsed.filter((p) => p.label.trim().endsWith('?')).length,
    followups: parsed,
    /** src/sim/chat.ts pushes a clarify flow's answer with `followups: []` and
     *  never patches them in. A clarify flow's declared follow-ups are DEAD —
     *  the chips the flow object declares never render. Recorded here because
     *  it is invisible in flows.ts and a real agent could easily "fix" it into
     *  a different shape without noticing it was ever the shape. */
    renderedInUI: !flow.clarify,
  };
}

/** The footer src/screens/Ask.tsx actually draws under an answer. */
function renderedFooterShape(flow: ChatFlow, chipIds: string[]) {
  // Mirrors `countSourcePapers` in src/screens/Ask.tsx: the papers behind the
  // answer, counting a paper cited directly and the paper behind every cited
  // record. If that function changes, this must change with it — the fixture is
  // the contract the real agent's formatter will be checked against, so a
  // footer captured here wrong is a footer specified wrong.
  const papers = new Set<string>();
  for (const m of flow.answerMd.matchAll(/\[\[([A-O]\d+[a-z]?)\]\]/g)) papers.add(m[1]);
  for (const m of flow.answerMd.matchAll(/\[\[(r-[A-Za-z0-9]+-\d+)\]\]/g)) {
    const rec = RECORDS.find((r) => r.id === m[1]);
    if (rec) papers.add(rec.paperId);
  }
  const sourceCount = papers.size;
  const supportLabel =
    sourceCount >= 4
      ? 'Well supported across several papers'
      : sourceCount > 0
        ? 'Supported, but from few sources'
        : 'No corpus support — see the decline above';
  const distinctPapers = uniq(chipIds.filter((id) => chipKind(id) === 'paper')).length;
  return {
    countedBy: 'countSourcePapers() in src/screens/Ask.tsx — papers, not citations',
    sourceCount,
    supportLabel,
    provenanceTick: 'scripted answer prose',
    /** FIXED IN THIS PHASE, recorded because the fixture would otherwise have
     *  pinned the defect as the specification. The count used to be
     *  `/\[\[(SP-\d+)\]\]/g`, a citation form from the retired synthetic
     *  corpus — real ids are `A1`, `C2`, `H17e`, `r-H4-4`, and the `SP-` form
     *  survives only in the `ChatFlow.answerMd` docstring. It matched nothing,
     *  so every answer in the app was footed "No corpus support — see the
     *  decline above" directly beneath its own citations. Under-claiming is
     *  still claiming wrongly. Whatever replaces this footer counts the chips
     *  the corpus actually uses. */
    distinctPaperChipsInAnswer: distinctPapers,
    distinctRecordChipsInAnswer: uniq(chipIds.filter((id) => chipKind(id) === 'record')).length,
    footerContradictsAnswer: sourceCount === 0 && distinctPapers > 0,
  };
}

function buildFlow(flow: ChatFlow) {
  const blocks = parseBlocks(flow.answerMd);
  const chips = placements(blocks);
  const chipIds = chips.map((c) => c.id);
  const decline = DECLINE_MOVES[flow.id];
  const answer = answerShape(flow, blocks);
  const footer = footerShape(blocks);
  const clarify = clarifyShape(flow);

  /** The derived features the asserted name rests on, so the name can be
   *  argued with rather than taken on trust. */
  const basis = [
    answer.table ? `table ${answer.table.columns}×${answer.table.rows} [${answer.table.headers.join('|')}]` : 'no table',
    `${answer.leadInCount} bold lead-in${answer.leadInCount === 1 ? '' : 's'}`,
    `opens in ${answer.opening.words} word${answer.opening.words === 1 ? '' : 's'}`,
    clarify ? `clarifies with ${clarify.optionCount} options` : 'no clarify',
    decline ? `declines by ${decline.kind}` : 'answers',
    footer.hasStandingNote ? 'closes on a standing note' : 'closes without a standing note',
  ].join('; ');

  return {
    id: flow.id,
    shape: {
      /** ASSERTED — a human name for the answer's overall form. `basis` is
       *  derived, and is what the name is claiming. */
      name: SHAPE_NAMES[flow.id] ?? 'unnamed',
      asserted: true,
      basis,
    },
    triggerCount: flow.triggers.length,
    plan: planShape(flow),
    toolCalls: toolShape(flow),
    retrieval: retrievalShape(flow, chipIds),
    answer,
    citations: {
      total: chips.length,
      paper: chips.filter((c) => c.kind === 'paper').length,
      record: chips.filter((c) => c.kind === 'record').length,
      distinct: uniq(chipIds).length,
      allResolve: chipIds.every((id) => (chipKind(id) === 'record' ? RECORD_IDS.has(id) : PAPER_IDS.has(id))),
      unresolved: uniq(chipIds)
        .filter((id) => (chipKind(id) === 'record' ? !RECORD_IDS.has(id) : !PAPER_IDS.has(id)))
        .sort(byCode),
      byBlockKind: tally(chips.map((c) => c.blockKind)),
      bySlot: tally(chips.map((c) => c.slot)),
      paperBySlot: tally(chips.filter((c) => c.kind === 'paper').map((c) => c.slot)),
      recordBySlot: tally(chips.filter((c) => c.kind === 'record').map((c) => c.slot)),
      paperPrecededBy: tally(chips.filter((c) => c.kind === 'paper').map((c) => c.precededBy)),
      recordPrecededBy: tally(chips.filter((c) => c.kind === 'record').map((c) => c.precededBy)),
      runs: uniq(
        chips.filter((c) => c.runLength > 1).map((c) => `${c.block}:${c.row ?? '-'}:${c.column ?? '-'}`),
      ).length,
      placements: chips,
    },
    footer,
    clarify,
    followups: followupShape(flow),
    renderedFooter: renderedFooterShape(flow, chipIds),
    decline: decline
      ? {
          kind: decline.kind,
          moves: decline.moves.map(([name, marker]) => ({
            move: name,
            present: marker.test(flow.answerMd),
          })),
          allMovesPresent: decline.moves.every(([, m]) => m.test(flow.answerMd)),
        }
      : null,
  };
}

const flows = FLOWS.map(buildFlow);

// ══ Cross-flow aggregate ═══════════════════════════════════════════════
//
// The per-flow records say what each answer does. These say what ALL of them
// do, which is the part a formatter has to reproduce for questions nobody has
// written a flow for.

const allPlacements = flows.flatMap((f) => f.citations.placements);
const allPlanSteps = flows.flatMap((f) => f.plan.steps);

const aggregate = {
  flows: flows.length,
  plan: {
    stepCounts: tally(flows.map((f) => String(f.plan.stepCount))),
    signatures: tally(flows.map((f) => f.plan.signature)),
    roleCounts: tally(allPlanSteps.map((s) => s.role)),
    everyPlanOpensWithParse: flows.every((f) => f.plan.opensWithParse),
    everyPlanHasRetrieve: flows.every((f) => f.plan.roles.includes('retrieve')),
    flowsWithGuardStep: flows.filter((f) => f.plan.hasGuardStep).length,
    flowsEndingInDelivery: flows.filter((f) => f.plan.endsWithDelivery).length,
    unclassifiedSteps: allPlanSteps.filter((s) => s.role === 'unclassified').map((s) => s.text),
  },
  toolCalls: {
    callCounts: tally(flows.map((f) => String(f.toolCalls.count))),
    names: tally(flows.flatMap((f) => f.toolCalls.names)),
    everyFlowOpensWithCorpusSearch: flows.every((f) => f.toolCalls.opensWithCorpusSearch),
    /** One search then zero or more record queries. No flow searches twice, and
     *  no flow queries records before it has retrieved. */
    everyFlowSearchesExactlyOnce: flows.every((f) => f.toolCalls.searchCallCount === 1),
    kValues: tally(flows.flatMap((f) => f.toolCalls.calls.map((c) => (c.k === null ? 'none' : String(c.k))))),
    filterDimensions: tally(flows.flatMap((f) => f.toolCalls.calls.flatMap((c) => c.filterKeys))),
    recordQueryFlags: tally(
      flows.flatMap((f) => f.toolCalls.calls.flatMap((c) => Object.keys(c.flags))),
    ),
    fieldsRequested: tally(flows.flatMap((f) => f.toolCalls.calls.flatMap((c) => c.fields))),
    /** Only the search call ever renders retrieval cards. */
    retrievalRendering: tally(flows.flatMap((f) => f.toolCalls.calls.map((c) => c.retrievalRendering))),
  },
  retrieval: {
    hitCounts: tally(flows.map((f) => String(f.retrieval.hitCount))),
    everyFlowScoresDescending: flows.every((f) => f.retrieval.scoresDescending),
    everyHitOnSectionS1: flows.every((f) => f.retrieval.sectionIds.every((s) => s === 's1')),
    totalHits: flows.reduce((n, f) => n + f.retrieval.hitCount, 0),
    flowsRetrievingAPaperTwice: flows.filter((f) => f.retrieval.papersRetrievedTwice.length > 0).map((f) => f.id),
    totalRetrievedNotCited: flows.reduce((n, f) => n + f.retrieval.retrievedNotCited.length, 0),
    totalCitedNotRetrieved: flows.reduce((n, f) => n + f.retrieval.citedNotRetrieved.length, 0),
  },
  citations: {
    total: allPlacements.length,
    paper: allPlacements.filter((p) => p.kind === 'paper').length,
    record: allPlacements.filter((p) => p.kind === 'record').length,
    distinct: uniq(allPlacements.map((p) => p.id)).length,
    allResolveAgainstCorpus: flows.every((f) => f.citations.allResolve),
    byBlockKind: tally(allPlacements.map((p) => p.blockKind)),
    bySlot: tally(allPlacements.map((p) => p.slot)),
    /** The load-bearing asymmetry, and the single most likely thing to be lost:
     *  a PAPER chip opens the sentence it supports, a RECORD chip closes the
     *  number it discharges. A formatter that puts every chip at the end of the
     *  sentence produces a different document. */
    paperBySlot: tally(allPlacements.filter((p) => p.kind === 'paper').map((p) => p.slot)),
    recordBySlot: tally(allPlacements.filter((p) => p.kind === 'record').map((p) => p.slot)),
    paperPrecededBy: tally(allPlacements.filter((p) => p.kind === 'paper').map((p) => p.precededBy)),
    recordPrecededBy: tally(allPlacements.filter((p) => p.kind === 'record').map((p) => p.precededBy)),
    paperFollowedBy: tally(allPlacements.filter((p) => p.kind === 'paper').map((p) => p.followedBy)),
    recordFollowedBy: tally(allPlacements.filter((p) => p.kind === 'record').map((p) => p.followedBy)),
    chipRuns: allPlacements.filter((p) => p.runLength > 1).length,
    maxRunLength: Math.max(...allPlacements.map((p) => p.runLength)),
    /**
     * Measured, not asserted — each is computed from the placements above and
     * would flip to false the moment the shape changed. These are the checks a
     * formatter regression should actually run: they are what makes an answer
     * READ like this one rather than merely contain the same ids.
     */
    invariants: {
      noRecordChipEverLeadsASentence: allPlacements
        .filter((p) => p.kind === 'record')
        .every((p) => p.slot !== 'sentence-lead'),
      noRecordChipEverOpensABlockOrCell: allPlacements
        .filter((p) => p.kind === 'record')
        .every((p) => p.precededBy !== 'block-start' && p.precededBy !== 'cell-start'),
      everyChipAloneInACellIsAPaperChip: allPlacements
        .filter((p) => p.slot === 'cell-only')
        .every((p) => p.kind === 'paper'),
      everySentenceFinalChipIsARecordChip: allPlacements
        .filter((p) => p.slot === 'sentence-final')
        .every((p) => p.kind === 'record'),
      recordChipsImmediatelyAfterAQuantity: allPlacements.filter(
        (p) => p.kind === 'record' && (p.precededBy === 'quantity' || p.precededBy === 'bold-quantity'),
      ).length,
      paperChipsImmediatelyAfterAQuantity: allPlacements.filter(
        (p) => p.kind === 'paper' && (p.precededBy === 'quantity' || p.precededBy === 'bold-quantity'),
      ).length,
    },
  },
  answer: {
    blockCounts: tally(flows.map((f) => String(f.answer.blockCount))),
    flowsWithTable: flows.filter((f) => f.answer.table !== null).map((f) => f.id),
    tableShapes: flows
      .filter((f) => f.answer.table !== null)
      .map((f) => ({ id: f.id, columns: f.answer.table!.columns, rows: f.answer.table!.rows })),
    /** The verdict lands in the first sentence, before the evidence. Reported as
     *  a distribution rather than a threshold, because the threshold would be
     *  something this fixture invented rather than something it observed. */
    openingSentenceWords: {
      min: Math.min(...flows.map((f) => f.answer.opening.words)),
      max: Math.max(...flows.map((f) => f.answer.opening.words)),
      atOrUnderFifteen: flows.filter((f) => f.answer.opening.words <= 15).length,
      longest: flows.reduce((a, b) => (b.answer.opening.words > a.answer.opening.words ? b : a)).id,
    },
    openingWordCounts: flows.map((f) => ({ id: f.id, words: f.answer.opening.words })),
    leadInCounts: tally(flows.map((f) => String(f.answer.leadInCount))),
  },
  footer: {
    flowsWithStandingNote: flows.filter((f) => f.footer.hasStandingNote).map((f) => f.id),
    flowsWithoutStandingNote: flows.filter((f) => !f.footer.hasStandingNote).map((f) => f.id),
    /**
     * The obligation is "close by naming what this answer does not establish".
     * Ten flows discharge it with the italic standing note. Of the three that
     * do not, two close on an explicit negation instead ("It does **not** show
     * …", "the stake is bounded … not a capability to acquire"). F10 closes on
     * a caution phrased without a negation keyword — "a blended mean describes
     * neither … reads as corroboration only if you let it" — so the marker does
     * not fire on it. Listed rather than asserted away: the marker is a keyword
     * test, and widening it until it returned true would be fitting the test to
     * the answer.
     */
    closingDischarge: {
      byStandingNote: flows.filter((f) => f.footer.hasStandingNote).map((f) => f.id),
      byExplicitNegation: flows
        .filter((f) => !f.footer.hasStandingNote && f.footer.closingCarriesNegation)
        .map((f) => f.id),
      noMarkerFired: flows
        .filter((f) => !f.footer.hasStandingNote && !f.footer.closingCarriesNegation)
        .map((f) => f.id),
    },
    claims: tally(flows.flatMap((f) => f.footer.claims)),
    noteWordCounts: flows.filter((f) => f.footer.hasStandingNote).map((f) => ({ id: f.id, words: f.footer.words })),
  },
  clarify: {
    flows: flows.filter((f) => f.clarify).map((f) => f.id),
    optionCounts: tally(flows.filter((f) => f.clarify).map((f) => String(f.clarify!.optionCount))),
    everyQuestionIsTwoSentences: flows
      .filter((f) => f.clarify)
      .every((f) => f.clarify!.questionSentences === 2),
    everyOptionTargetsAnExistingFlow: flows
      .filter((f) => f.clarify)
      .every((f) => f.clarify!.options.every((o) => o.targetExists)),
  },
  decline: {
    flows: flows.filter((f) => f.decline).map((f) => f.id),
    kinds: tally(flows.filter((f) => f.decline).map((f) => f.decline!.kind)),
    allMovesPresent: flows.filter((f) => f.decline).every((f) => f.decline!.allMovesPresent),
    missingMoves: flows
      .filter((f) => f.decline)
      .flatMap((f) => f.decline!.moves.filter((m) => !m.present).map((m) => `${f.id}:${m.move}`)),
  },
  followups: {
    counts: tally(flows.map((f) => String(f.followups.count))),
    allTargetsResolve: flows.every((f) => f.followups.allTargetsResolve),
    flowsWhoseFollowupsNeverRender: flows.filter((f) => !f.followups.renderedInUI).map((f) => f.id),
  },
  renderedFooter: {
    /** See the defect note on `flows[].renderedFooter`. */
    flowsFootedAsUnsupported: flows.filter((f) => f.renderedFooter.footerContradictsAnswer).map((f) => f.id),
  },
};

// ══ Asserted: how a flow is played and drawn ═══════════════════════════

const renderingContract = {
  assertedNotDerived: true,
  note: 'Read out of the files named below at capture time. Nothing here is computed from FLOWS, so it goes stale if those files change and must be re-read rather than trusted.',
  playback: {
    source: 'src/sim/chat.ts — playFlow()',
    messageOrder: ['plan', 'tool (one per toolCall, in order)', 'clarify (only if flow.clarify)', 'answer'],
    planTicksStepByStepThenCollapses: true,
    oneToolMessagePerToolCall: true,
    retrievalCardsFollowTheirToolRow: true,
    clarifyIsPushedBeforeTheAnswer: true,
    clarifyAnswerIsPushedWithEmptyFollowups: true,
    followupsArePatchedInAfterStreamingEnds: true,
    answerStreamsInAboutNinetyChunks: true,
  },
  answerRendering: {
    source: 'src/screens/Ask.tsx, src/components/Markdown.tsx, src/components/Chip.tsx',
    chipSyntax: '[[id]]',
    chipRegex: '/\\[\\[([A-Za-z0-9\\-]+)\\]\\]/g',
    recordChipRule: 'an id starting "r-" renders as a record chip (deep-links to the span); anything else renders as a paper chip',
    unresolvedChipRendering: 'red error chip reading "Source unavailable", never silent',
    blockGrammar: ['table', 'list', 'ordered-list', 'heading', 'blockquote', 'paragraph'],
    inlineGrammar: ['**bold**', '*italic*', '`code`', '[[chip]]'],
    stripChartAppearsWhen: 'four or more cited records share one ontology field and convert to its canonical unit',
    answerActions: ['Copy', 'Export', 'Pin sources', 'Insert into…', 'Helpful', 'Not helpful'],
  },
  retrievalRendering: {
    source: 'src/screens/Ask.tsx — RetrievalCards',
    layout: 'two-column card grid beneath the tool row',
    perCard: ['paper citation chip', 'section heading', 'score bar', 'score to two decimals', 'snippet clamped to two lines', 'Inspect', 'Open source'],
    emptyRetrievalArray: 'renders the "No passages in this corpus match" callout',
    absentRetrievalKey: 'renders nothing beneath the tool row',
  },
  toolRowRendering: {
    source: 'src/screens/Ask.tsx — ToolMessage',
    collapsed: 'wrench icon, tool name, args joined as "k=v · k=v", durationMs',
    expanded: 'pretty-printed { tool, args, durationMs, hits }',
    methodLine: 'args.method, when present, is printed unfolded beneath the row — scripted flows do not set it, live retrieval does',
  },
};

// ══ How the demo enters a flow ═════════════════════════════════════════

const normalizePrompt = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();

const promptEntryPoints = {
  note: 'The six chips on the empty Ask screen. Each is one flow trigger verbatim, so a click is an exact match rather than a fuzzy one — this is the demo’s entry path and the first thing to break if triggers are edited. Matched here by a documented normalizer (lowercase; non-alphanumerics to space; collapse whitespace), which is deliberately looser than the matcher in src/sim/chat.ts. This fixture pins the entry RELATION, not the matcher.',
  prompts: SUGGESTED_PROMPTS.map((prompt) => {
    const hit = FLOWS.find((f) => f.triggers.some((t) => normalizePrompt(t) === normalizePrompt(prompt)));
    return { prompt, entersFlow: hit?.id ?? null, relation: hit ? 'exact-trigger-after-normalization' : 'unmatched' };
  }),
  allPromptsEnterAFlow: SUGGESTED_PROMPTS.every((p) =>
    FLOWS.some((f) => f.triggers.some((t) => normalizePrompt(t) === normalizePrompt(p))),
  ),
};

// ══ Write ══════════════════════════════════════════════════════════════

const fixture = {
  meta: {
    generatedFrom: 'src/data/flows.ts',
    generatedBy: 'scripts/capture-answer-shapes.ts',
    renderedBy: ['src/screens/Ask.tsx', 'src/components/Markdown.tsx', 'src/components/Chip.tsx'],
    playedBy: 'src/sim/chat.ts',
    purpose:
      'Regression fixtures for the FORMATTER of the real agent that replaces the scripted flows. A real model will write its own prose; it must still produce this shape — the same plan granularity, the same tool sequence, citation chips in the same places relative to the claims they support, and the same closing standing note.',
    capturedFromProse: [
      'plan step text — a plan step is not prose, it is the plan',
      'bold lead-in labels — the answer’s section structure',
      'table headers — the table’s schema',
      'the closing standing note — the honesty policy, kept verbatim because a paraphrase is not a regression target',
      'clarify questions and option labels — the fork is the shape',
    ],
    deliberatelyNotCaptured: [
      'answerMd body prose',
      'retrieval snippet text',
      'corpus.search query strings',
      'toolCall durationMs — playback timing, not answer shape',
    ],
    counts: {
      flows: FLOWS.length,
      planSteps: allPlanSteps.length,
      toolCalls: flows.reduce((n, f) => n + f.toolCalls.count, 0),
      retrievalHits: aggregate.retrieval.totalHits,
      citationChips: allPlacements.length,
      distinctChipIds: aggregate.citations.distinct,
      clarifyFlows: aggregate.clarify.flows.length,
      declineFlows: aggregate.decline.flows.length,
      corpusPapers: PAPERS.length,
      corpusRecords: RECORDS.length,
    },
    taxonomies: {
      planStepRole: PLAN_ROLE_DOC,
      chipSlot: SLOT_DOC,
      chipPrecededBy: PRECEDED_BY_DOC,
      chipFollowedBy: FOLLOWED_BY_DOC,
      footerClaim: FOOTER_CLAIM_DOC,
    },
    determinism: 'Derived from a fixed array in declaration order; maps are keyed in codepoint order, never locale order. Two consecutive runs are byte-identical.',
  },
  renderingContract,
  promptEntryPoints,
  aggregate,
  flows,
};

const path = join(OUT, 'answer-shapes.json');
const serialised = `${JSON.stringify(fixture, null, 2)}\n`;

// `--check` compares and writes nothing. Without it this fixture is a 165 KB
// pin that NOTHING replays: it is the contract the real agent's formatter will
// be checked against, and it could silently stop describing the flows it was
// captured from. It is also the fixture that would have caught the flow-
// selection regression, had anything been replaying it.
if (process.argv.includes('--check')) {
  const committed = existsSync(path) ? readFileSync(path, 'utf8') : '';
  if (committed !== serialised) {
    console.error('\n✗ fixtures/answer-shapes.json no longer matches the flows it pins.');
    console.error(`  committed ${committed.length} bytes, the flows imply ${serialised.length}.`);
    console.error('  Run `pnpm capture:answer-shapes` and READ the diff before committing it:');
    console.error('  this file is the contract for the real agent\'s answer formatter, so a');
    console.error('  change here is a change to what that agent will be held to.');
    process.exit(1);
  }
  console.log(`  fixtures/answer-shapes.json   ${flows.length} flows, up to date`);
  process.exit(0);
}

writeFileSync(path, serialised, 'utf8');

// ══ Report ═════════════════════════════════════════════════════════════

const bytes = Buffer.byteLength(JSON.stringify(fixture, null, 2)) + 1;
console.log('openFerment answer-shape capture');
console.log('────────────────────────────────');
console.log(`  fixtures/answer-shapes.json   ${(bytes / 1024).toFixed(0)} KB`);
console.log('');
console.log('  flow        shape                                plan  tools  hits  chips  p/r      footer  clarify  decline');
for (const f of flows) {
  console.log(
    `  ${f.id.padEnd(10)}  ${f.shape.name.padEnd(35)}  ${String(f.plan.stepCount).padStart(4)}  ${String(
      f.toolCalls.count,
    ).padStart(5)}  ${String(f.retrieval.hitCount).padStart(4)}  ${String(f.citations.total).padStart(5)}  ${`${f.citations.paper}/${f.citations.record}`.padEnd(7)}  ${(f.footer.hasStandingNote ? 'note' : '—').padEnd(6)}  ${(f.clarify ? `${f.clarify.optionCount} opts` : '—').padEnd(7)}  ${f.decline?.kind ?? '—'}`,
  );
}
console.log('');
console.log(`  plan signatures      ${Object.keys(aggregate.plan.signatures).length} distinct over ${flows.length} flows`);
console.log(`  chip placement       paper ${aggregate.citations.paper} · record ${aggregate.citations.record} · ${aggregate.citations.distinct} distinct ids · all resolve: ${aggregate.citations.allResolveAgainstCorpus}`);
console.log(`  paper chips          ${aggregate.citations.paperBySlot['sentence-lead'] ?? 0} lead a sentence, ${aggregate.citations.paperBySlot['cell-only'] ?? 0} stand alone in a table cell`);
console.log(`  record chips         ${aggregate.citations.invariants.recordChipsImmediatelyAfterAQuantity} of ${aggregate.citations.record} sit immediately after a quantity; none ever leads a sentence: ${aggregate.citations.invariants.noRecordChipEverLeadsASentence}`);
console.log(`  standing notes       ${aggregate.footer.closingDischarge.byStandingNote.length} of ${flows.length}; ${aggregate.footer.closingDischarge.byExplicitNegation.length} close on a negation; no marker fired on ${aggregate.footer.closingDischarge.noMarkerFired.join(', ') || 'none'}`);
console.log(`  clarify              ${aggregate.clarify.flows.join(', ')}`);
console.log(`  decline              ${aggregate.decline.flows.join(', ')} — every structural move present: ${aggregate.decline.allMovesPresent}`);
if (aggregate.plan.unclassifiedSteps.length) {
  console.log(`\n  ! ${aggregate.plan.unclassifiedSteps.length} plan steps hit no role rule:`);
  for (const s of aggregate.plan.unclassifiedSteps) console.log(`      ${s}`);
}
if (aggregate.decline.missingMoves.length) {
  console.log(`\n  ! decline moves not found: ${aggregate.decline.missingMoves.join(', ')}`);
}
if (aggregate.renderedFooter.flowsFootedAsUnsupported.length) {
  console.log(
    `\n  ! ${aggregate.renderedFooter.flowsFootedAsUnsupported.length} answers render footed "No corpus support — see the decline above"`,
  );
  console.log('      Ask.tsx counts sources with /\\[\\[(SP-\\d+)\\]\\]/g; no corpus id has that form.');
}
