// The parts of the architecture, and which pool a screen is reading.
//
// `UPSTREAM` in `data/demo/upstream.ts` already names the thirteen parts and
// what each will be derived from. This adds the two things a screen header
// needs and that table does not carry: which movement a part belongs to, and
// which of the two object pools the screen in front of you is showing.
//
// ── WHY THE POOL IS IN THE HEADER OF EVERY SCREEN ────────────────────────
//
// There is one rail and there are two pools. That is only honest if every
// screen says which pool it is reading, because the alternative — a reader
// crossing from `/ledger` to `/repo` without noticing the object changed —
// is the interface implying one corpus. An `ExtractionRecord` is a catalogued
// claim awaiting verification and an `Accession` is a normalised quantity with
// complete provenance; nothing aggregates across them, and the header is where
// a reader finds that out rather than in a docstring.
//
// The eyebrow used to be nine different things — "Module 0 · Evidence",
// "Read · Ledger", "fermOS", "Organisms", "Not built yet", and twenty-odd
// screens with none at all — which is why it is computed here now.
import { UPSTREAM_BY_PART } from './demo/upstream';

/** The whitepaper's three movements. Rail group order, and eyebrow prefix. */
export type Movement = 'Read' | 'Reason' | 'Return';

export const MOVEMENT: Record<string, Movement> = {
  trawl: 'Read',
  repo: 'Read',
  ledger: 'Read',
  assay: 'Read',
  geneos: 'Reason',
  fermos: 'Reason',
  proforma: 'Reason',
  parchment: 'Reason',
  postdoc: 'Reason',
  runbook: 'Return',
  notary: 'Return',
  openlab: 'Return',
  learn: 'Return',
};

export type Pool = 'corpus' | 'demo';

/**
 * How each pool is named to a reader. Not the type's name — a header is not
 * the place to teach `ExtractionRecord` — but the pool's, which is what the
 * reader needs to know is different.
 */
export const POOL_LABEL: Record<Pool, string> = {
  corpus: 'β-casein corpus',
  demo: 'demo suite',
};

/**
 * The header eyebrow: movement, part, pool.
 *
 * The part's name comes from `UPSTREAM`, the same table the rail reads, so a
 * screen cannot be labelled with a part name the rail does not show.
 */
export function partEyebrow(part: string, pool: Pool): string {
  const label = UPSTREAM_BY_PART[part]?.label ?? part;
  const movement = MOVEMENT[part];
  return [movement, label, POOL_LABEL[pool]].filter(Boolean).join(' · ');
}
