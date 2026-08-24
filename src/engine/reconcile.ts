// Reconciliation (OF-BLD-006 §5).
//
// Predicted beside observed, with the delta. This is the one thing in the
// system that exists in no other tool, and the only ground truth the platform
// ever gets about its own predictions — nothing in the literature can tell you
// whether a yield model works.
//
// THE OUTCOME IS SUGGESTED, NEVER DECIDED. This module computes deltas, which
// is arithmetic, and proposes an outcome, which is judgement. A person records
// the verdict. That split matters most for 'inconclusive': whether a run's
// deviations were large enough to void the comparison is a call about what
// actually happened in the room, and a threshold cannot make it.
import type { Deposition, Prediction, Runbook } from '@/data/types';

export interface Delta {
  predictionId: string;
  label: string;
  predicted: number;
  observed: number;
  unit: string;
  pctDelta: number;
  /** Whether the operator ever read the observed value back (§4.4). */
  confirmed: boolean;
}

/**
 * Within this band a prediction counts as held.
 *
 * Ten percent is a convention, not a derived quantity, and it is stated here
 * rather than buried so that anyone reading a "confirmed" knows exactly what
 * it claims. A tighter band would make the platform look worse and would not
 * make it more honest; a looser one would let it grade itself generously.
 */
export const CONFIRM_BAND_PCT = 10;

/**
 * Deltas for every prediction the deposition actually measured.
 *
 * A prediction with no matching entry is absent rather than scored zero: not
 * measuring something is not evidence against it, and counting it as a miss
 * would make an incomplete run look like a refuted one.
 *
 * Where a measure was recorded more than once — a correction appends rather
 * than overwrites — the LAST entry wins, because that is the operator's final
 * word on the value.
 */
export function computeDeltas(deposition: Deposition, runbook: Runbook): Delta[] {
  const out: Delta[] = [];
  for (const prediction of runbook.predictions) {
    const measures = runbook.measurementSchema.filter((m) => m.predictionId === prediction.id);
    if (measures.length === 0) continue;
    const ids = new Set(measures.map((m) => m.id));
    const entries = deposition.entries.filter((e) => ids.has(e.measureId));
    if (entries.length === 0) continue;
    const last = entries[entries.length - 1];
    const pctDelta =
      prediction.value === 0
        ? last.value === 0
          ? 0
          : 100
        : ((last.value - prediction.value) / Math.abs(prediction.value)) * 100;
    out.push({
      predictionId: prediction.id,
      label: prediction.label,
      predicted: prediction.value,
      observed: last.value,
      unit: last.unit,
      pctDelta,
      confirmed: last.confirmed,
    });
  }
  return out;
}

/** Predictions the run simply never got to. */
export function unmeasured(deposition: Deposition, runbook: Runbook): Prediction[] {
  const measured = new Set(computeDeltas(deposition, runbook).map((d) => d.predictionId));
  return runbook.predictions.filter((p) => !measured.has(p.id));
}

export interface OutcomeSuggestion {
  outcome: 'confirmed' | 'refuted' | 'inconclusive';
  /** Why, in one sentence, for the person who has to agree or disagree. */
  why: string;
}

/**
 * Propose an outcome. The caller decides.
 *
 * 'inconclusive' is checked first and deliberately so: a run with large
 * deviations, or one whose numbers were never read back, cannot support either
 * of the other two verdicts however the arithmetic lands. Recording that
 * honestly is what keeps the hit rate real — a platform that resolves every
 * ambiguous run into confirmed or refuted is reporting a number about itself
 * that it has not earned.
 */
export function suggestOutcome(deltas: Delta[], deviationCount: number): OutcomeSuggestion {
  if (deltas.length === 0)
    return {
      outcome: 'inconclusive',
      why: 'Nothing that was predicted was measured, so there is nothing to compare.',
    };

  const unread = deltas.filter((d) => !d.confirmed).length;
  if (unread > 0)
    return {
      outcome: 'inconclusive',
      why: `${unread} of ${deltas.length} measured values were never read back, so the parse behind them was never checked.`,
    };

  if (deviationCount >= 3)
    return {
      outcome: 'inconclusive',
      why: `${deviationCount} deviations were logged during the run — enough that the comparison may be measuring the deviations rather than the prediction.`,
    };

  const missed = deltas.filter((d) => Math.abs(d.pctDelta) > CONFIRM_BAND_PCT);
  if (missed.length === 0)
    return {
      outcome: 'confirmed',
      why: `Every measured prediction landed within ${CONFIRM_BAND_PCT}%.`,
    };

  return {
    outcome: 'refuted',
    why: `${missed.length} of ${deltas.length} predictions fell outside ${CONFIRM_BAND_PCT}% — ${missed
      .map((d) => `${d.label} by ${d.pctDelta > 0 ? '+' : ''}${d.pctDelta.toFixed(0)}%`)
      .join(', ')}.`,
  };
}

/** Formatted delta, signed, for display beside the pair it came from. */
export function deltaLabel(d: Delta): string {
  const sign = d.pctDelta > 0 ? '+' : '';
  return `${sign}${d.pctDelta.toFixed(Math.abs(d.pctDelta) < 10 ? 1 : 0)}%`;
}
