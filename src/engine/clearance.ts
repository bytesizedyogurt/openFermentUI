// Patent clearance, per jurisdiction (OF-BLD-005 §8).
//
// The load-bearing idea is that clearance is not a single global verdict.
// Territoriality is structural: a patent that was never filed in Rwanda does
// not stop you manufacturing there, and does not let you sell into Germany.
// A product that reads "clear" on one line and then gets exported is the
// failure mode this module exists to prevent.
//
// A product's stored `clearanceState` is the WORST case across jurisdictions —
// the headline. This module spreads that headline back out over the
// jurisdictions that matter for a landlocked East African facility, using a
// filing-propensity model rather than a search of national registers. It is
// modeled, it says so on every surface that renders it, and it is never legal
// advice. openFerment produces research leads; counsel produces opinions.
import type { ClearanceStateId, Product } from '@/data/types';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';

export interface Jurisdiction {
  id: string;
  /** Two-letter office code as it would appear on a family member. */
  code: string;
  name: string;
  /** Where the facility is, versus where the product would be sold. */
  role: 'manufacture' | 'export';
  /**
   * How reliably a biotech family is actually prosecuted and maintained here,
   * expressed as how many severity steps the headline relaxes by. 0 means
   * assume the family is live; 2 means assume it usually is not.
   */
  relax: 0 | 1 | 2;
  because: string;
}

/**
 * The six offices that decide whether a Kigali facility can build and sell.
 * Rwanda first, because manufacture is the question you answer before export.
 */
export const JURISDICTIONS: Jurisdiction[] = [
  {
    id: 'rw',
    code: 'RW',
    name: 'Rwanda',
    role: 'manufacture',
    relax: 2,
    because:
      'Few biotech families are filed and maintained here. Manufacture is usually clear where export is not — which is exactly why a single global verdict misleads.',
  },
  {
    id: 'us',
    code: 'US',
    name: 'United States',
    role: 'export',
    relax: 0,
    because: 'Primary filing jurisdiction. Assume any live family is prosecuted here.',
  },
  {
    id: 'ep',
    code: 'EP',
    name: 'European Patent Office',
    role: 'export',
    relax: 0,
    because:
      'Primary filing jurisdiction, and the validation states that matter for food and diagnostics are almost always designated.',
  },
  {
    id: 'cn',
    code: 'CN',
    name: 'China',
    role: 'export',
    relax: 0,
    because: 'Heavily filed in fermentation and enzymes; assume coverage unless shown otherwise.',
  },
  {
    id: 'jp',
    code: 'JP',
    name: 'Japan',
    role: 'export',
    relax: 1,
    because: 'Filed selectively. Coverage is common for high-value families and patchy below them.',
  },
  {
    id: 'in',
    code: 'IN',
    name: 'India',
    role: 'export',
    relax: 1,
    because:
      'Filed selectively, and the excluded-subject-matter rules narrow what survives. A family live in the US is often narrower or absent here.',
  },
];

export const JURISDICTIONS_BY_ID: Record<string, Jurisdiction> = Object.fromEntries(
  JURISDICTIONS.map((j) => [j.id, j]),
);

/**
 * Severity ladder. The two watch states sit at the same height because they
 * are equally live — they differ in what you design around, not in how much
 * they cost you. 'unknown' is off the ladder: not assessed is not a verdict.
 */
const SEVERITY: Record<ClearanceStateId, number> = {
  'clear-expired': 0,
  'clear-none': 1,
  'watch-variant': 2,
  'watch-process': 2,
  blocked: 3,
  unknown: -1,
};

export function clearanceSeverity(state: ClearanceStateId): number {
  return SEVERITY[state];
}

/** Cheap deterministic hash — the matrix must not change between renders. */
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

/**
 * Walk a headline state down the severity ladder by `steps`. The watch flavour
 * is preserved on the way down, because "core free, variants fenced" and
 * "process claims live" imply different work and collapsing them would lose
 * the only useful thing the state says.
 */
function relaxState(headline: ClearanceStateId, steps: number): ClearanceStateId {
  if (headline === 'unknown') return 'unknown';
  const target = Math.max(0, SEVERITY[headline] - steps);
  if (target >= 3) return 'blocked';
  if (target === 2) return headline === 'watch-process' ? 'watch-process' : 'watch-variant';
  if (target === 1) return 'clear-none';
  return 'clear-expired';
}

export interface JurisdictionVerdict {
  jurisdiction: Jurisdiction;
  state: ClearanceStateId;
  /** Whether this office is stricter than where the facility would build. */
  blocksExport: boolean;
}

/**
 * The per-jurisdiction matrix for one product.
 *
 * Modeled, not searched. Each office relaxes the headline by its own filing
 * propensity plus one deterministic step of variation drawn from the product
 * and office ids, so the matrix is stable across renders and sessions but not
 * uniform across a catalogue. No office is ever stricter than the headline,
 * because the headline is defined as the worst case.
 */
export function clearanceMatrix(product: Product): JurisdictionVerdict[] {
  const headline = product.clearanceState;
  const rows = JURISDICTIONS.map((jurisdiction) => {
    const jitter = hash(`${product.id}:${jurisdiction.id}`) % 3 === 0 ? 1 : 0;
    return {
      jurisdiction,
      state: relaxState(headline, jurisdiction.relax + jitter),
      blocksExport: false,
    };
  });
  const home = rows.find((r) => r.jurisdiction.role === 'manufacture');
  const homeSeverity = home ? SEVERITY[home.state] : SEVERITY[headline];
  for (const r of rows) {
    r.blocksExport =
      r.jurisdiction.role === 'export' &&
      SEVERITY[r.state] > homeSeverity &&
      SEVERITY[r.state] >= 2;
  }
  return rows;
}

/**
 * Export markets strictly worse than the manufacturing jurisdiction — the
 * cases where "we can make it" and "we can sell it" give different answers.
 */
export function exportBlockers(product: Product): JurisdictionVerdict[] {
  return clearanceMatrix(product).filter((r) => r.blocksExport);
}

/** The action the headline state implies, from the shared vocabulary. */
export function clearanceAction(state: ClearanceStateId): string {
  return CLEARANCE_STATES_BY_ID[state]?.action ?? 'Run clearance before any commitment.';
}

/**
 * One sentence naming the divergence, for a summary line. Null when every
 * office agrees, so a caller can stay quiet rather than printing a non-fact.
 */
export function territorialityNote(product: Product): string | null {
  const blockers = exportBlockers(product);
  if (blockers.length === 0) return null;
  const names = blockers.map((b) => b.jurisdiction.code).join(', ');
  return `Manufacture in Rwanda reads clearer than export to ${names}. The molecule is the same; the fence is not.`;
}

/**
 * Shown wherever the matrix is. Says what the model is and what it is not, in
 * the platform's own voice — the counsel warning is a separate, fixed callout
 * and this does not stand in for it.
 */
export const CLEARANCE_MODEL_NOTE =
  'Modeled from filing propensity per office, not read off national registers. The stored state is the worst case across jurisdictions; the rows below spread it back out. Treat it as where to look, never as what is true.';
