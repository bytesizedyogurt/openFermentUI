// Client-side keyword retrieval over seeded section texts (OF-DES-001 §16).
// BM25-flavored scoring; used by the entity-lookup fallback and body search.
import type { Paper } from '@/data/types';

export interface RetrievalResult {
  paperId: string;
  sectionId: string;
  score: number;
  snippet: string;
}

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

export function searchCorpus(
  papers: Paper[],
  query: string,
  k = 6,
): RetrievalResult[] {
  const weights = expandQuery(tokenize(query));
  if (weights.size === 0) return [];
  const results: RetrievalResult[] = [];
  const N = papers.reduce((n, p) => n + p.sections.length, 0) || 1;
  // document frequency per token
  const df = new Map<string, number>();
  for (const p of papers) {
    for (const s of p.sections) {
      const toks = new Set(tokenize(s.text + ' ' + s.heading + ' ' + p.title));
      for (const t of weights.keys()) if (toks.has(t)) df.set(t, (df.get(t) ?? 0) + 1);
    }
  }
  for (const p of papers) {
    if (p.ingest === 'shelf' || p.ingest === 'failed:parse') continue;
    for (const s of p.sections) {
      const toks = tokenize(s.text + ' ' + s.heading + ' ' + p.title);
      const tf = new Map<string, number>();
      for (const t of toks) if (weights.has(t)) tf.set(t, (tf.get(t) ?? 0) + 1);
      if (tf.size === 0) continue;
      let score = 0;
      for (const [t, f] of tf) {
        const idf = Math.log(1 + (N - (df.get(t) ?? 0) + 0.5) / ((df.get(t) ?? 0) + 0.5));
        score += (weights.get(t) ?? 0) * idf * (f / (f + 1.2));
      }
      if (score > 0) {
        results.push({
          paperId: p.id,
          sectionId: s.id,
          score,
          snippet: makeSnippet(s.text, weights),
        });
      }
    }
  }
  results.sort((a, b) => b.score - a.score);
  const top = results.slice(0, k);
  // normalize scores to 0..1 for display
  const max = top[0]?.score ?? 1;
  return top.map((r) => ({ ...r, score: Math.round((r.score / max) * 100) / 100 }));
}

function makeSnippet(text: string, weights: Map<string, number>): string {
  const sentences = text.split(/(?<=\.)\s+/);
  let best = sentences[0] ?? '';
  let bestScore = -1;
  for (const s of sentences) {
    const toks = tokenize(s);
    let score = 0;
    for (const t of toks) if (weights.has(t)) score += weights.get(t)!;
    if (score > bestScore) {
      bestScore = score;
      best = s;
    }
  }
  return best.length > 220 ? best.slice(0, 217) + '…' : best;
}
