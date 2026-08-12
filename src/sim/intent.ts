/**
 * Query lexicon for the scripted agent: tokenisation and domain synonym
 * expansion (OF-DES-001 §16.3).
 *
 * THIS IS NOT RETRIEVAL. Both functions arrived here from
 * `src/engine/retrieval.ts`, which also held a BM25-flavoured `searchCorpus`.
 * That scoring is gone: corpus retrieval is PaperQA2's job, and a second
 * ranking function in TypeScript that has to agree with it is the failure this
 * migration exists to prevent. These two never served it. `src/sim/chat.ts`
 * uses them to decide WHICH SCRIPTED FLOW a question selects (`scoreFlow`) and
 * how much of the question the corpus can speak to at all (`CORPUS_VOCAB`,
 * `CORPUS_DF`, `domainConfidence`) — intent matching and domain-confidence
 * scoring for a simulated agent, with no Python counterpart to agree with. That
 * is simulation logic, so it lives in `src/sim` with the rest of the
 * simulation rather than in an engine module.
 *
 * Because flow selection is calibrated against these exact token sets — the
 * MATCH_THRESHOLD of 48 was tuned against them — the two functions moved
 * VERBATIM. Changing the tokenizer changes which flow answers a question.
 */

const STOP = new Set(
  'the a an and or of in on for with to from by at is are was were be been what which how why does do did this that these those it its as'.split(' '),
);

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9µ⁻%°.\-]+/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 1 && !STOP.has(t));
}

// Domain synonym expansion (OF-DES-001 §16.3).
const SYNONYMS: Record<string, string[]> = {
  'growth': ['µ', 'mu', 'specific', 'rate'],
  'µ': ['growth', 'mu', 'rate'],
  'mu': ['growth', 'µ', 'rate'],
  'titer': ['titre', 'concentration', 'product'],
  'media': ['medium', 'tap'],
  'medium': ['media', 'tap'],
  'protein': ['%dw', 'content'],
  'dcw': ['od750', 'dry', 'weight', 'biomass'],
  'od': ['od750', 'optical', 'density'],
  'cw15': ['chlamydomonas', 'reinhardtii'],
  'chlamydomonas': ['cw15', 'reinhardtii', 'algae'],
  'phaffii': ['pichia', 'komagataella', 'gs115'],
  'pichia': ['phaffii', 'komagataella'],
  'spirulina': ['arthrospira', 'platensis'],
  'mixotrophic': ['acetate', 'mixotrophy'],
  'photoautotrophic': ['light', 'phototrophic', 'autotrophic'],
};

export function expandQuery(tokens: string[]): Map<string, number> {
  const weights = new Map<string, number>();
  for (const t of tokens) {
    weights.set(t, Math.max(weights.get(t) ?? 0, 1));
    for (const syn of SYNONYMS[t] ?? []) {
      weights.set(syn, Math.max(weights.get(syn) ?? 0, 0.5));
    }
  }
  return weights;
}
