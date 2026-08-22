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

/**
 * The rail key and route for each part.
 *
 * The rail in `App.tsx` used to hold these inline. They are here so the Bench's
 * parts map and the rail cannot disagree about where a part lives or which `g`
 * chord reaches it — the map's whole job is to teach the navigation, and a map
 * that taught a stale shortcut would be worse than no map.
 */
export const PART_ROUTE: Record<string, string> = {
  trawl: '/trawl',
  repo: '/repo',
  ledger: '/ledger',
  assay: '/assay',
  geneos: '/geneos',
  fermos: '/fermos',
  proforma: '/proforma',
  parchment: '/parchment',
  postdoc: '/postdoc',
  runbook: '/runbook',
  notary: '/notary',
  openlab: '/openlab',
  learn: '/learn',
};

export const PART_KEY: Record<string, string> = {
  trawl: 't',
  repo: 'r',
  ledger: 'd',
  assay: 'v',
  geneos: 'o',
  fermos: 's',
  proforma: 'f',
  parchment: 'c',
  postdoc: 'a',
  runbook: 'p',
  notary: 'y',
  openlab: 'b',
  learn: 'n',
};

/** The parts of one movement, in the order the architecture lists them. */
export function partsIn(movement: Movement): string[] {
  return Object.keys(MOVEMENT).filter((p) => MOVEMENT[p] === movement);
}

export const MOVEMENTS: Movement[] = ['Read', 'Reason', 'Return'];
