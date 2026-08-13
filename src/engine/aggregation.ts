// MIRROR of the gate on ExtractionRecord in
// packages/core/openferment_core/schema/records.py. Python is canonical.
// Changes go there first, then here, and parity is enforced by pnpm verify.
//
// This copy stays because the Ledger recomputes as a reviewer corrects a
// record, in the browser, with no server in the loop. Because it stays, the two
// are checked against each other rather than trusted: `pnpm check:aggregation`
// runs BOTH over the real corpus and compares every answer, including which
// exclusion each reports — the reason string is displayed, so a multiply-
// excluded record naming a different reason on each side is a visible
// disagreement, not an implementation detail.
//
// `provenanceOf` below is NOT mirrored and has no Python counterpart: it
// decides which tick a record renders with, which is display logic.
//
// Aggregation policy (OF-COR-001 §16 O8, §19; OF-FE-003 §1).
//
// These live in engine/ rather than store/ because they are pure functions of a
// record, and because engine/ is the layer that ships to production unchanged.
// posterior.ts and balance.ts both need them, and importing app state into the
// engine would invert the dependency direction the repo otherwise maintains.
//
// store.ts re-exports all four names, so every existing import site is unaffected.
import type { ExtractionRecord, Provenance } from '@/data/types';

/**
 * A record's display provenance. The stored `provenance` field is
 * authoritative — a curated or industry-estimate record does not become
 * 'verified' just because someone accepted it in the queue without opening the
 * source. Review promotes 'curated' → 'verified'; nothing promotes
 * 'industry-estimate'.
 */
export function provenanceOf(r: ExtractionRecord): Provenance {
  if (r.gold) return 'gold';
  if (r.provenance === 'industry-estimate') return 'industry-estimate';
  if (r.status === 'verified') return 'verified';
  if (r.status === 'rejected') return 'unverified';
  return r.provenance ?? 'unverified';
}

/**
 * Why a record is held out of aggregate statistics, or null when nothing holds
 * it out (OF-COR-001 §16 O8 and §19). Industry estimates are not evidence, and
 * a paper reciting someone else's number is not an independent measurement —
 * counting either one overstates consensus.
 *
 * This is the reason, not just the verdict, so a screen can say which records
 * it left out of a median instead of silently dropping them. Exclusion applies
 * to the statistic only: the records stay visible in per-record tables and
 * plots, because they are real values, just not independent evidence.
 */
export type AggregateExclusion = 'rejected' | 'industry-estimate' | 'demo' | 'not-primary';

export function aggregateExclusion(r: ExtractionRecord): AggregateExclusion | null {
  if (r.status === 'rejected') return 'rejected';
  if (r.provenance === 'industry-estimate') return 'industry-estimate';
  // CLAUDE.md invariant 3 names `demo` alongside `industry-estimate`, and both
  // implementations omitted it — a modeled value would have entered a median
  // unremarked. No record carries it today, which is why nothing noticed.
  if (r.provenance === 'demo') return 'demo';
  if (r.isPrimary === false) return 'not-primary';
  return null;
}

/** Records that may enter a median, range or count-based summary. */
export function isAggregatable(r: ExtractionRecord): boolean {
  return aggregateExclusion(r) === null;
}

/** Short phrase a per-record view can print next to a held-out value. */
export const EXCLUSION_NOTE: Record<AggregateExclusion, string> = {
  rejected: 'rejected — excluded from statistics',
  'industry-estimate': 'industry estimate — excluded from statistics',
  demo: 'modeled, not measured — excluded from statistics',
  'not-primary': 'reports another study\u2019s measurement — excluded from statistics',
};
