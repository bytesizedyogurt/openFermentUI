// Patent clearance, per jurisdiction (OF-BLD-005 §8).
//
// The load-bearing idea is that clearance is not a single global verdict.
// Territoriality is structural: a patent that was never filed in Rwanda does
// not stop you manufacturing there, and does not let you sell into Germany.
// A product that reads "clear" on one line and then gets exported is the
// failure mode this module exists to prevent.
//
// So the matrix is the point, not the cells. A per-office table makes a global
// verdict structurally impossible to express, and it does that whether or not
// anybody has filled it in. An EMPTY matrix satisfies §8.
//
// WHAT THIS MODULE DOES NOT DO. It does not infer a jurisdiction's position
// from the product's stored state. An earlier version did: it walked the
// stored state down a severity ladder per office using a filing-propensity
// weight plus a deterministic jitter, and produced a specific, plausible,
// actionable-looking divergence for all 117 molecules out of nothing at all.
// It was labelled "modeled · not searched" and that did not rescue it — on
// this surface a fabricated divergence is worse than no divergence, because
// it looks like a finding and reads as a reason to act. It is gone. Cells are
// populated from authored, sourced findings in `data/clearanceFindings.ts` or
// they are `unknown`.
import type { ClearanceStateId, Product } from '@/data/types';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';
import { findingFor, type ClearanceFinding } from '@/data/clearanceFindings';

export interface Jurisdiction {
  id: string;
  /** Two-letter office code as it would appear on a family member. */
  code: string;
  name: string;
  /** Where the facility is, versus where the product would be sold. */
  role: 'manufacture' | 'export';
  /** Why this office is on the list at all — never a claim about coverage. */
  why: string;
}

/**
 * The six offices that decide whether a Kigali facility can build and sell.
 * Rwanda first, because manufacture is the question you answer before export.
 *
 * Note what these entries carry and what they do not: a reason the office
 * matters commercially, and nothing whatsoever about how likely a patent is to
 * exist there. That judgement is what the removed model was making up.
 */
export const JURISDICTIONS: Jurisdiction[] = [
  {
    id: 'rw',
    code: 'RW',
    name: 'Rwanda',
    role: 'manufacture',
    why: 'Where the facility would be built, so this is the office that decides whether you may make the molecule at all.',
  },
  {
    id: 'us',
    code: 'US',
    name: 'United States',
    role: 'export',
    why: 'Largest research-reagent and diagnostics market; the usual first filing jurisdiction.',
  },
  {
    id: 'ep',
    code: 'EP',
    name: 'European Patent Office',
    role: 'export',
    why: 'One examination, then validation in the states that matter for food, feed and diagnostics.',
  },
  {
    id: 'cn',
    code: 'CN',
    name: 'China',
    role: 'export',
    why: 'Large fermentation and enzyme market, and a major source of competing supply.',
  },
  {
    id: 'jp',
    code: 'JP',
    name: 'Japan',
    role: 'export',
    why: 'High-value reagent and diagnostics market.',
  },
  {
    id: 'in',
    code: 'IN',
    name: 'India',
    role: 'export',
    why: 'Large generics and reagent manufacturing base, and a regional export route.',
  },
];

export const JURISDICTIONS_BY_ID: Record<string, Jurisdiction> = Object.fromEntries(
  JURISDICTIONS.map((j) => [j.id, j]),
);

/**
 * Severity ladder, used only to compare two states that are both KNOWN. The
 * two watch states sit at the same height because they are equally live — they
 * differ in what you design around, not in how much they cost you. 'unknown'
 * is off the ladder at -1 and never compares: not assessed is not a verdict,
 * and must never sort as though it were a mild one.
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

export interface JurisdictionVerdict {
  jurisdiction: Jurisdiction;
  state: ClearanceStateId;
  /** The authored finding behind this cell, or null when nobody has looked. */
  finding: ClearanceFinding | null;
  /**
   * True only when this office and the manufacturing office are BOTH known and
   * this one is materially stricter. Two unknowns never produce a divergence,
   * because the absence of a finding is not evidence of a difference.
   */
  blocksExport: boolean;
}

/**
 * The per-jurisdiction matrix for one product.
 *
 * Every cell defaults to `unknown` and is populated only from an authored,
 * sourced finding. Nothing is derived from the product's stored state.
 */
export function clearanceMatrix(product: Product): JurisdictionVerdict[] {
  const rows: JurisdictionVerdict[] = JURISDICTIONS.map((jurisdiction) => {
    const finding = findingFor(product.id, jurisdiction.id);
    return {
      jurisdiction,
      state: finding ? finding.state : 'unknown',
      finding,
      blocksExport: false,
    };
  });

  const home = rows.find((r) => r.jurisdiction.role === 'manufacture');
  const homeSeverity = home ? SEVERITY[home.state] : -1;
  if (homeSeverity >= 0) {
    for (const r of rows) {
      r.blocksExport =
        r.jurisdiction.role === 'export' &&
        SEVERITY[r.state] >= 2 &&
        SEVERITY[r.state] > homeSeverity;
    }
  }
  return rows;
}

/** How much of the matrix anybody has actually looked at. */
export function matrixCoverage(product: Product): {
  assessed: number;
  total: number;
  resolved: number;
} {
  const rows = clearanceMatrix(product);
  return {
    assessed: rows.filter((r) => r.finding !== null).length,
    total: rows.length,
    resolved: rows.filter((r) => r.finding !== null && r.state !== 'unknown').length,
  };
}

/**
 * Export markets known to be stricter than the manufacturing jurisdiction.
 * Empty whenever the comparison would rest on an unknown, which — until
 * somebody does the work — is almost always.
 */
export function exportBlockers(product: Product): JurisdictionVerdict[] {
  return clearanceMatrix(product).filter((r) => r.blocksExport);
}

/** The action the headline state implies, from the shared vocabulary. */
export function clearanceAction(state: ClearanceStateId): string {
  return CLEARANCE_STATES_BY_ID[state]?.action ?? 'Run clearance before any commitment.';
}

/**
 * One sentence naming a real divergence, or null. Returns null when the
 * offices simply have not been compared, which is not the same as agreeing —
 * so the caller must not print "every office agrees" on a null.
 */
export function territorialityNote(product: Product): string | null {
  const blockers = exportBlockers(product);
  if (blockers.length === 0) return null;
  const names = blockers.map((b) => b.jurisdiction.code).join(', ');
  return `Manufacture in Rwanda reads clearer than export to ${names}. The molecule is the same; the fence is not.`;
}

/**
 * Shown wherever the matrix is. Says what the table is and, more importantly,
 * what an empty cell means — because the failure mode here is reading a blank
 * as a green light.
 */
export const CLEARANCE_MODEL_NOTE =
  'Cells are populated only from authored findings that name the patents they rest on and cite where they were read. Nothing is inferred from the molecule’s headline state, and nothing is inferred from one office to another. An empty cell means nobody has looked — it is not a clearance, and it is not a lack of a patent.';

/** The one sentence that must sit next to the stored state, everywhere. */
export const HEADLINE_SCOPE_NOTE =
  'Not resolved to any jurisdiction. This describes claim architecture — what the claims recite and therefore whether designing around them is possible — not whether a patent is in force in any particular office.';
