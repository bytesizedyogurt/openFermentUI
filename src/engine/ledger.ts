// The prediction ledger (OF-BLD-014 §9.3). Every locked prediction across
// runbooks, and what the runs reconciled against it measured. Read from the
// store, never kept: the counts are computed here and nowhere else, so the
// ledger page, Home's Predictions card and the checks agree.
//
// A prediction is TESTED once a reconciled run measured it and was not
// recorded inconclusive: an inconclusive run is counted as a run, never as a
// test of anything. The latest such run decides held or missed, through
// `holds` in reconcile.ts, the one place that decides it for every kind.
import type { Deposition, Prediction, Runbook } from '@/data/types';
import { holds } from './reconcile';

/** The tested count below which a hit rate is not shown (the screen says so). */
export const HIT_RATE_MIN_TESTED = 5;

export interface LedgerRow {
  runbookId: string;
  runbookTitle: string;
  lockedAt: string;
  prediction: Prediction;
  /** The latest conclusive reconciliation that measured this prediction. */
  observed: { value: number; unit: string; depositionId: string; at: string } | null;
  held: boolean | null;
}

export interface LedgerCounts {
  locked: number;
  tested: number;
  held: number;
  missed: number;
  inconclusiveRuns: number;
  /** held / tested, or null below HIT_RATE_MIN_TESTED. */
  hitRate: number | null;
}

export function ledgerRows(runbooks: Runbook[], depositions: Deposition[]): LedgerRow[] {
  const rows: LedgerRow[] = [];
  for (const rb of runbooks) {
    if (!rb.lockedAt) continue;
    const runs = depositions
      .filter((d) => d.runbookId === rb.id && d.reconciliation && d.reconciliation.outcome !== 'inconclusive')
      .sort((a, b) => (a.reconciliation!.at < b.reconciliation!.at ? -1 : 1));
    for (const p of rb.predictions) {
      let observed: LedgerRow['observed'] = null;
      for (const d of runs) {
        const delta = d.reconciliation!.deltas.find((x) => x.predictionId === p.id);
        if (delta) observed = { value: delta.observed, unit: delta.unit, depositionId: d.id, at: d.reconciliation!.at };
      }
      rows.push({
        runbookId: rb.id,
        runbookTitle: rb.title,
        lockedAt: rb.lockedAt,
        prediction: p,
        observed,
        held: observed ? holds(p, observed.value) : null,
      });
    }
  }
  return rows;
}

export function ledgerCounts(runbooks: Runbook[], depositions: Deposition[]): LedgerCounts {
  const rows = ledgerRows(runbooks, depositions);
  const tested = rows.filter((r) => r.held !== null);
  const held = tested.filter((r) => r.held).length;
  const locked = new Set(runbooks.filter((r) => r.lockedAt).map((r) => r.id));
  return {
    locked: rows.length,
    tested: tested.length,
    held,
    missed: tested.length - held,
    inconclusiveRuns: depositions.filter((d) => locked.has(d.runbookId) && d.reconciliation?.outcome === 'inconclusive').length,
    hitRate: tested.length >= HIT_RATE_MIN_TESTED ? held / tested.length : null,
  };
}
