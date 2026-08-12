// Scripted agent: intent matching and staged flow playback (OF-DES-001 §16).
//
// A turn is flow selection followed by staged playback. All content comes from
// the flow object, so the Inspector's trace is the literal data that produced
// the answer — honest by construction rather than reconstructed afterward.
import type { ChatFlow, ChatMessage, ChatRetrievalHit, ExtractionRecord } from '@/data/types';
import { FLOWS } from '@/data/flows';
import { useStore, nextId, isAggregatable } from '@/store';
import { tokenize, expandQuery, searchCorpus } from '@/engine/retrieval';
import { PAPERS, STRAINS } from '@/data/source';
import { ONTOLOGY } from '@/data/source';
import { fieldName } from '@/data/ontology';
import { convert, fmt, asNumber } from '@/engine/units';
import { delay, scaled, streamInterval } from './latency';

// ── Intent matching (§16.3) ────────────────────────────────────────────

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9µ⁻¹\s-]/g, ' ').replace(/\s+/g, ' ').trim();

/**
 * Every token the corpus can actually speak about: paper titles and curator
 * prose, strain names and aliases, ontology field names, and the flow triggers
 * themselves. ~2.5k tokens — small enough that a word missing from it is real
 * evidence the question is about something else entirely.
 */
const CORPUS_VOCAB: Set<string> = (() => {
  const v = new Set<string>();
  const add = (text: unknown) => {
    if (typeof text !== 'string') return;
    for (const tok of tokenize(text)) v.add(tok);
  };
  for (const p of PAPERS) {
    add(p.title);
    add(p.venue);
    for (const sec of p.sections) {
      add(sec.heading);
      add(sec.text);
    }
  }
  for (const st of STRAINS) {
    add(st.binomial);
    add(st.designation);
    add(st.description);
    for (const t of st.taxonomy) add(t);
  }
  for (const d of ONTOLOGY) {
    add(d.name);
    add(d.definition);
  }
  for (const f of FLOWS) for (const t of f.triggers) add(t);
  return v;
})();

/**
 * How much to trust a match given words the corpus has never seen. "max
 * secreted yield from tomatoes" overlaps a titer trigger on three tokens out of
 * four and used to answer, confidently, about Chlamydomonas. Each unseen token
 * is one more reason to hand the turn to the fallback ladder, which declines
 * and names what the corpus does cover.
 */
const CORPUS_DF: Map<string, number> = (() => {
  const df = new Map<string, number>();
  for (const p of PAPERS) {
    for (const sec of p.sections) {
      const seen = new Set(tokenize(`${sec.heading} ${sec.text} ${p.title}`));
      for (const tok of seen) df.set(tok, (df.get(tok) ?? 0) + 1);
    }
  }
  return df;
})();

/**
 * How much a query token counts when asking "did the trigger account for this?".
 * A rare, specific term carries the question's subject; a common one is
 * connective tissue. "maximum secreted protein yield from soybean" shares four
 * common tokens with a titer trigger and differs on the one word that says what
 * the question is actually about — so that word has to outweigh the other four.
 */
function salience(tok: string): number {
  const df = CORPUS_DF.get(tok) ?? 0;
  if (df === 0) return 4;
  if (df <= 3) return 10;
  if (df <= 10) return 3;
  return 1;
}

function domainConfidence(qTokens: string[]): number {
  if (qTokens.length === 0) return 1;
  const unseen = qTokens.filter((t) => !CORPUS_VOCAB.has(t)).length;
  return Math.pow(0.4, unseen);
}

/**
 * Score input against a flow's triggers: exact match beats whole-phrase
 * containment beats weighted keyword overlap with synonym expansion.
 */
export function scoreFlow(input: string, flow: ChatFlow): number {
  const q = norm(input);
  if (!q) return 0;
  let best = 0;
  const qTokens = tokenize(q);
  const qExpanded = expandQuery(qTokens);
  const confidence = domainConfidence(qTokens);

  for (const trigger of flow.triggers) {
    const t = norm(trigger);
    if (t === q) return 100;

    const tTokens = tokenize(t);
    if (tTokens.length === 0) continue;

    // Whole-phrase containment, but only in the direction that carries
    // evidence. A user who typed a superset of the trigger meant it. A user who
    // typed two characters that happen to occur inside the trigger did not:
    // "hi" sits inside "which host", and scoring that as a phrase match let
    // single words select a flow and answer with total confidence.
    const contains =
      (q.includes(t) && tTokens.length >= 2) ||
      (t.includes(q) && qTokens.length >= 2 && q.length >= t.length * 0.6);
    if (contains) {
      best = Math.max(best, (70 + Math.min(10, t.length / 8)) * confidence);
      continue;
    }

    // Keyword overlap, scored on BOTH directions of coverage. Trigger coverage
    // alone rewards a query for the tokens it happens to share and ignores the
    // ones it does not: "max secreted yield from tomatoes" covers two thirds of
    // a titer trigger and says "tomatoes" for free. Weighing how much of the
    // *query* the trigger accounts for is what makes an out-of-domain noun
    // cost something.
    let overlap = 0;
    for (const tok of tTokens) overlap += qExpanded.get(tok) ?? 0;
    const triggerCoverage = overlap / tTokens.length;

    const tExpanded = expandQuery(tTokens);
    let qHit = 0;
    let qTotal = 0;
    for (const tok of qTokens) {
      const w = salience(tok);
      qTotal += w;
      if ((tExpanded.get(tok) ?? 0) > 0) qHit += w;
    }
    const queryCoverage = qTotal > 0 ? qHit / qTotal : 0;

    const denom = triggerCoverage + queryCoverage;
    const f1 = denom > 0 ? (2 * triggerCoverage * queryCoverage) / denom : 0;
    best = Math.max(best, f1 * 70 * confidence);
  }
  return best;
}

export function matchFlow(input: string, flows: ChatFlow[] = FLOWS): { flow: ChatFlow; score: number } | null {
  let best: { flow: ChatFlow; score: number } | null = null;
  for (const flow of flows) {
    const score = scoreFlow(input, flow);
    if (!best || score > best.score) best = { flow, score };
  }
  return best;
}

// Raised from 34. Everything between the old bar and this one was a weak
// keyword coincidence — "cost" alone selecting the TEA flow, a soybean question
// answered with a Chlamydomonas titer. Below this the turn goes to the fallback
// ladder, which looks the entity up for real and otherwise declines by name.
// Declining a question we half-recognised is the cheaper error.
export const MATCH_THRESHOLD = 48;

// ── Entity recognition for the fallback ladder (§16.3a) ────────────────

interface Entities {
  organism?: string;
  field?: string;
  paperId?: string;
  protocolId?: string;
}

const ORGANISM_ALIASES: Record<string, string> = {
  cw15: 'cw15',
  chlamydomonas: 'cw15',
  reinhardtii: 'cw15',
  uvm4: 'uvm4',
  uvm11: 'uvm4',
  gs115: 'gs115',
  phaffii: 'gs115',
  pichia: 'gs115',
  komagataella: 'gs115',
  trichoderma: 'treesei',
  reesei: 'treesei',
  'e. coli': 'ecoli',
  ecoli: 'ecoli',
  coli: 'ecoli',
  bovine: 'bovine',
  casein: 'bovine',
};

/** Synonyms onto ontology v1. "casein kinase" is deliberately absent: it names
 *  three different enzymes, so it must disambiguate rather than resolve. */
const FIELD_ALIASES: Record<string, string> = {
  'growth rate': 'growth_rate_mu',
  mu: 'growth_rate_mu',
  µ: 'growth_rate_mu',
  density: 'final_biomass_density',
  biomass: 'final_biomass_density',
  productivity: 'volumetric_productivity',
  medium: 'medium_component_conc',
  media: 'medium_component_conc',
  'total soluble protein': 'expression_pct_tsp',
  tsp: 'expression_pct_tsp',
  expression: 'expression_pct_tsp',
  titer: 'titer_secreted',
  titre: 'titer_secreted',
  secreted: 'titer_secreted',
  secretion: 'secreted_fraction',
  intracellular: 'titer_intracellular',
  'fold improvement': 'fold_improvement',
  transformation: 'transformation_efficiency',
  colony: 'time_to_colony',
  phosphate: 'phosphate_count',
  phosphorylation: 'phosphorylation_degree',
  phosphorylated: 'phosphorylation_degree',
  glycan: 'glycan_species',
  glycosylation: 'glycan_species',
  sialyl: 'glycan_species',
  kinase: 'kinase_identity',
  fam20c: 'kinase_identity',
  micelle: 'micelle_diameter',
  micellar: 'micellar_fraction',
  gelation: 'gelation_ph',
  coagulation: 'gelation_ph',
  calcium: 'calcium_binding',
  melt: 'melt_stretch_length',
  stretch: 'melt_stretch_length',
  disruption: 'disruption_protein_yield',
  'cell disruption': 'disruption_protein_yield',
  energy: 'disruption_energy',
  cost: 'minimum_selling_price',
  price: 'minimum_selling_price',
  msp: 'minimum_selling_price',
};

export function recognizeEntities(input: string): Entities {
  const q = ' ' + norm(input) + ' ';
  const out: Entities = {};

  const paper = input.match(/\b[A-O]\d{1,2}m?\b/);
  if (paper) out.paperId = paper[0].toUpperCase();

  const protocol = input.match(/\bPR-[A-Z]+-\d+\b/i);
  if (protocol) out.protocolId = protocol[0].toUpperCase();

  for (const [alias, id] of Object.entries(ORGANISM_ALIASES)) {
    if (q.includes(' ' + alias + ' ') || q.includes(alias)) {
      out.organism = id;
      break;
    }
  }
  for (const [alias, id] of Object.entries(FIELD_ALIASES)) {
    if (q.includes(' ' + alias)) {
      out.field = id;
      break;
    }
  }
  if (!out.field) {
    for (const def of ONTOLOGY) {
      if (q.includes(norm(def.name))) {
        out.field = def.id;
        break;
      }
    }
  }
  return out;
}

// ── Message helpers ────────────────────────────────────────────────────

function push(sessionId: string, msg: ChatMessage) {
  useStore.getState().appendMessage(sessionId, msg);
}

function patch(sessionId: string, id: string, p: Partial<ChatMessage>) {
  useStore.getState().updateMessage(sessionId, id, p);
}

/** Stream text into an answer message at ~40 tokens/s (§13.5). */
async function streamAnswer(sessionId: string, msgId: string, md: string) {
  const chunks = md.match(/\S+\s*/g) ?? [md];
  const step = Math.max(1, Math.round(chunks.length / 90));
  let acc = '';
  for (let i = 0; i < chunks.length; i += step) {
    acc += chunks.slice(i, i + step).join('');
    patch(sessionId, msgId, { md: acc } as Partial<ChatMessage>);
    const iv = streamInterval();
    if (iv > 0) await new Promise((r) => setTimeout(r, iv));
  }
  patch(sessionId, msgId, { md, streaming: false } as Partial<ChatMessage>);
}

// ── Flow playback (§16.2) ──────────────────────────────────────────────

export async function playFlow(flow: ChatFlow, sessionId: string): Promise<void> {
  // a) the plan, whose steps tick one at a time
  const planId = nextId('m');
  push(sessionId, { kind: 'plan', id: planId, steps: flow.plan, done: 0, collapsed: false });
  await delay(320);
  for (let i = 0; i < flow.plan.length; i++) {
    await delay(260);
    patch(sessionId, planId, { done: i + 1 } as Partial<ChatMessage>);
  }

  // b) each tool call, then its retrieval set
  for (const call of flow.toolCalls) {
    const toolId = nextId('m');
    push(sessionId, { kind: 'tool', id: toolId, call, expanded: false });
    await delay(call.durationMs);
  }

  // The plan collapses to a one-line summary once its work is done.
  patch(sessionId, planId, { collapsed: true } as Partial<ChatMessage>);

  // c) a clarifying question short-circuits the answer
  if (flow.clarify) {
    await delay(200);
    push(sessionId, {
      kind: 'clarify',
      id: nextId('m'),
      question: flow.clarify.question,
      options: flow.clarify.options,
    });
    if (flow.answerMd.trim()) {
      const preId = nextId('m');
      push(sessionId, { kind: 'answer', id: preId, md: '', streaming: true, flowId: flow.id, followups: [] });
      await streamAnswer(sessionId, preId, flow.answerMd);
    }
    return;
  }

  // d) the answer streams, then the follow-up chips land
  const answerId = nextId('m');
  push(sessionId, {
    kind: 'answer',
    id: answerId,
    md: '',
    streaming: true,
    flowId: flow.id,
    followups: [],
  });
  await streamAnswer(sessionId, answerId, flow.answerMd);
  await delay(180);
  patch(sessionId, answerId, { followups: flow.followups } as Partial<ChatMessage>);
}

// ── Fallback (a): entity lookup answered from live store data ──────────

function summarizeRecords(records: ExtractionRecord[], field: string): string {
  const def = ONTOLOGY.find((d) => d.id === field);
  if (!def) return '';
  // Same gate as the strain pages and the strip plots: an industry estimate or a
  // paper reciting someone else's number can be listed, but must not shift a
  // median. Answering with a statistic built from a citation-of-a-citation is
  // exactly the error this fallback exists to avoid.
  const held = records.filter((r) => !isAggregatable(r)).length;
  const converted = records
    .filter(isAggregatable)
    .map((r) => {
      try {
        const n = asNumber(r.value);
        if (n === null) return null; // categorical — not summarisable as a range
        return { r, v: def.canonicalUnit === '' ? n : convert(n, r.unit, def.canonicalUnit) };
      } catch {
        return null;
      }
    })
    .filter(Boolean) as { r: ExtractionRecord; v: number }[];
  if (converted.length === 0) return '';
  converted.sort((a, b) => b.v - a.v);
  const values = converted.map((c) => c.v);
  const median = values[Math.floor(values.length / 2)];
  const verified = converted.filter((c) => c.r.status === 'verified').length;
  const heldNote = held
    ? ` ${held} further record${held === 1 ? ' is' : 's are'} held out of the median — industry estimates, or a paper reporting another study's measurement.`
    : '';

  const rows = converted
    .slice(0, 8)
    .map((c) => `| [[${c.r.paperId}]] | ${fmt(c.v)} | ${c.r.status} | [[${c.r.id}]] |`)
    .join('\n');

  return `The corpus has **${converted.length} record${converted.length === 1 ? '' : 's'}** for ${def.name.toLowerCase()}${verified ? ` (${verified} verified)` : ''}, spanning **${fmt(values[values.length - 1])}–${fmt(values[0])} ${def.canonicalUnit}** with a median of **${fmt(median)} ${def.canonicalUnit}**.${heldNote}

| Paper | ${def.canonicalUnit || 'Value'} | Status | Record |
|---|---:|---|---|
${rows}
${converted.length > 8 ? `\n…and ${converted.length - 8} more.` : ''}

This answer was assembled from the live record store rather than a scripted flow, so it reflects any verification decisions you have made in this session.`;
}

async function playEntityLookup(input: string, entities: Entities, sessionId: string): Promise<boolean> {
  const state = useStore.getState();

  const planId = nextId('m');
  const plan = [
    'Parse question — no scripted flow matched',
    `Recognize entities${entities.organism ? ` (organism: ${entities.organism})` : ''}${entities.field ? ` (field: ${entities.field})` : ''}`,
    'Query the record store directly',
    'Retrieve supporting passages',
    'Synthesize from live data',
  ];
  push(sessionId, { kind: 'plan', id: planId, steps: plan, done: 0, collapsed: false });
  for (let i = 0; i < plan.length; i++) {
    await delay(230);
    patch(sessionId, planId, { done: i + 1 } as Partial<ChatMessage>);
  }

  const hits: ChatRetrievalHit[] = searchCorpus(state.papers, input, 5).map((h) => ({
    paperId: h.paperId,
    sectionId: h.sectionId,
    score: h.score,
    snippet: h.snippet,
  }));

  push(sessionId, {
    kind: 'tool',
    id: nextId('m'),
    call: {
      name: 'corpus.search',
      args: { query: input, k: 5, ...(entities.organism ? { organism: entities.organism } : {}) },
      durationMs: 780,
      retrieval: hits,
    },
    expanded: false,
  });
  await delay(700);

  let md = '';

  if (entities.paperId) {
    const paper = state.papers.find((p) => p.id === entities.paperId);
    if (paper) {
      const recs = state.records.filter((r) => r.paperId === paper.id);
      md = `[[${paper.id}]] — *${paper.title}* (${paper.authors[0]}${paper.authors.length > 1 ? ' et al.' : ''}, ${paper.year}, ${paper.venue}).

${paper.abstract.split('. ').slice(0, 3).join('. ')}.

It carries **${recs.length} extraction record${recs.length === 1 ? '' : 's'}** (${recs.filter((r) => r.status === 'verified').length} verified), covering ${[...new Set(recs.map((r) => fieldName(r.field)))].slice(0, 5).join(', ')}.

Assembled from the live store — open the paper to read it with every span anchored in place.`;
    }
  } else if (entities.protocolId) {
    const proto = state.protocols.find((p) => p.id === entities.protocolId);
    if (proto) {
      const v = proto.versions.find((x) => x.version === proto.currentVersion);
      md = `**${proto.title}** (${proto.id}, v${proto.currentVersion}) — ${proto.purpose}

It has **${v?.steps.length ?? 0} steps** and **${v?.materials.length ?? 0} materials**, with an estimated ${v?.estMinutes.active} min active / ${v?.estMinutes.total} min total. ${proto.provenanceNote}

Open it to scale the batch and start a run.`;
    }
  } else if (entities.field) {
    const recs = state.records.filter(
      (r) =>
        r.field === entities.field &&
        r.status !== 'rejected' &&
        (!entities.organism || r.organism === entities.organism),
    );
    md = recs.length > 0 ? summarizeRecords(recs, entities.field) : '';
  } else if (entities.organism) {
    const strain = state.strains.find((s) => s.id === entities.organism);
    const recs = state.records.filter((r) => r.organism === entities.organism && r.status !== 'rejected');
    const fields = [...new Set(recs.map((r) => r.field))];
    if (strain) {
      md = `**${strain.binomial} ${strain.designation}** — ${strain.description}

The corpus holds **${recs.length} records** across **${fields.length} parameters** for this strain: ${fields.map((f) => fieldName(f)).slice(0, 6).join(', ')}${fields.length > 6 ? ', and others' : ''}.

Ask about a specific parameter for the values, or open the strain page to see every record plotted with its provenance.`;
    }
  }

  if (!md.trim()) return false;

  patch(sessionId, planId, { collapsed: true } as Partial<ChatMessage>);
  const answerId = nextId('m');
  push(sessionId, { kind: 'answer', id: answerId, md: '', streaming: true, followups: [] });
  await streamAnswer(sessionId, answerId, md);
  patch(sessionId, answerId, {
    followups: [
      'flow:F1|Growth rates for cw15',
      'flow:F5|K. phaffii titers',
      'flow:F7|How was the gold set built?',
    ],
  } as Partial<ChatMessage>);
  return true;
}

// ── Fallback (b): the honest decline (§16.3b) ──────────────────────────

async function playDecline(input: string, sessionId: string) {
  const declineFlow = FLOWS.find((f) => f.id === 'F9');
  const planId = nextId('m');
  const plan = ['Parse question', 'Retrieve candidate passages', 'Assess support', 'Decline rather than infer'];
  push(sessionId, { kind: 'plan', id: planId, steps: plan, done: 0, collapsed: false });
  for (let i = 0; i < plan.length; i++) {
    await delay(230);
    patch(sessionId, planId, { done: i + 1 } as Partial<ChatMessage>);
  }

  const hits = searchCorpus(useStore.getState().papers, input, 3);
  push(sessionId, {
    kind: 'tool',
    id: nextId('m'),
    call: {
      name: 'corpus.search',
      args: { query: input, k: 6 },
      durationMs: 820,
      // Real (weak) hits — the trace shows what was actually retrieved, even
      // when nothing cleared the support threshold.
      retrieval: hits.filter((h) => h.score > 0.55),
    },
    expanded: false,
  });
  await delay(620);
  patch(sessionId, planId, { collapsed: true } as Partial<ChatMessage>);

  const md = `That's outside this demo corpus — nothing in it supports an answer to that, and I'd rather say so than assemble a plausible one.

The corpus covers:

- **cw15 growth kinetics** — growth rates, doubling times, and light response
- **TAP media** — standard composition and buffer/nitrogen variants
- ***K. phaffii* fed-batch** — methanol induction and recombinant protein titers
- **Downstream processing** — disruption, harvest recovery, OD-to-DCW calibration
- **Extraction methodology** — the gold set and how quality is measured

Three questions it answers well:`;

  const answerId = nextId('m');
  push(sessionId, { kind: 'answer', id: answerId, md: '', streaming: true, followups: [] });
  await streamAnswer(sessionId, answerId, md);
  patch(sessionId, answerId, {
    followups: declineFlow?.followups ?? [
      'flow:F1|What growth rates are reported for cw15 in TAP?',
      'flow:F4|What is the OD₇₅₀-to-DCW conversion?',
      'flow:F5|What titers are reported for K. phaffii?',
    ],
  } as Partial<ChatMessage>);
}

// ── Slash commands ─────────────────────────────────────────────────────

export interface SlashResult {
  handled: boolean;
  scope?: { kind: 'paper' | 'collection'; id: string; label: string };
}

async function handleSlash(input: string, sessionId: string): Promise<SlashResult> {
  const state = useStore.getState();
  const [cmd, ...rest] = input.trim().split(/\s+/);
  const arg = rest.join(' ').trim();

  if (cmd === '/extract') {
    const paper = state.papers.find(
      (p) => p.id.toLowerCase() === arg.toLowerCase() || p.title.toLowerCase().includes(arg.toLowerCase()),
    );
    if (!paper) {
      push(sessionId, {
        kind: 'system',
        id: nextId('m'),
        text: `No paper matches “${arg}”. Try a paper id such as SP-004.`,
      });
      return { handled: true };
    }
    state.startJob({
      title: `Re-extract ${paper.id}`,
      kind: 'extraction',
      stages: [
        { label: 'Chunk', ms: 700 },
        { label: 'Embed', ms: 1100 },
        { label: 'Extract', ms: 1900 },
      ],
      href: `#/ledger/records?paper=${paper.id}`,
    });
    push(sessionId, {
      kind: 'system',
      id: nextId('m'),
      text: `Extraction queued for ${paper.id}. Track it in the Jobs tray — results land in the Extract table.`,
    });
    return { handled: true };
  }

  if (cmd === '/scope') {
    if (!arg) {
      push(sessionId, { kind: 'system', id: nextId('m'), text: 'Usage: /scope SP-004 — or /scope none to clear.' });
      return { handled: true };
    }
    if (arg.toLowerCase() === 'none') {
      push(sessionId, { kind: 'system', id: nextId('m'), text: 'Scope cleared — retrieval now covers the whole corpus.' });
      return { handled: true, scope: undefined };
    }
    const paper = state.papers.find((p) => p.id.toLowerCase() === arg.toLowerCase());
    const collection = state.collections.find((c) => c.name.toLowerCase().includes(arg.toLowerCase()));
    if (paper) {
      push(sessionId, { kind: 'system', id: nextId('m'), text: `Scoped to ${paper.id}. Retrieval will draw only from this paper.` });
      return { handled: true, scope: { kind: 'paper', id: paper.id, label: paper.id } };
    }
    if (collection) {
      push(sessionId, { kind: 'system', id: nextId('m'), text: `Scoped to the “${collection.name}” collection (${collection.paperIds.length} papers).` });
      return { handled: true, scope: { kind: 'collection', id: collection.id, label: collection.name } };
    }
    push(sessionId, { kind: 'system', id: nextId('m'), text: `No paper or collection matches “${arg}”.` });
    return { handled: true };
  }

  // /compare and /protocol fall through to normal matching, which routes them
  // to F11 / F12 when a flow covers them and to entity lookup otherwise.
  return { handled: false };
}

// ── Entry point ────────────────────────────────────────────────────────

export async function send(input: string, sessionId: string): Promise<SlashResult> {
  const text = input.trim();
  if (!text) return { handled: false };

  push(sessionId, { kind: 'user', id: nextId('m'), text });
  await delay(160);

  if (text.startsWith('/')) {
    const res = await handleSlash(text, sessionId);
    if (res.handled) return res;
  }

  const match = matchFlow(text);
  if (match && match.score >= MATCH_THRESHOLD) {
    await playFlow(match.flow, sessionId);
    return { handled: true };
  }

  const entities = recognizeEntities(text);
  if (entities.organism || entities.field || entities.paperId || entities.protocolId) {
    const answered = await playEntityLookup(text, entities, sessionId);
    if (answered) return { handled: true };
  }

  await playDecline(text, sessionId);
  return { handled: true };
}

/** Play a flow by id — used by clarify options and follow-up chips. */
export async function sendFlow(flowId: string, label: string, sessionId: string) {
  const flow = FLOWS.find((f) => f.id === flowId);
  push(sessionId, { kind: 'user', id: nextId('m'), text: label });
  await delay(160);
  if (!flow) {
    await playDecline(label, sessionId);
    return;
  }
  await playFlow(flow, sessionId);
}

export { scaled };
