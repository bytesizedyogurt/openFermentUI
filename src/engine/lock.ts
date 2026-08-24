// Prediction locking (OF-BLD-006 §3.3).
//
// Predictions freeze before execution. Without that the system grades its own
// homework: a prediction edited after the result is in will always look
// prescient, and the hit rate the platform reports about itself becomes
// meaningless. Locking is therefore not a convenience — it is the thing that
// makes Deposition's ground truth worth having.
//
// WHAT THIS HASH IS AND IS NOT. It is a content digest over the predictions
// and the measurement schema, used to answer one question: is what I am
// reading the same content that was frozen? It is NOT cryptographic, it is not
// a signature, and it proves nothing about *when* the content existed — a
// reader who does not trust the store can detect drift with it, but cannot
// detect a determined rewrite of both the content and the hash.
//
// Real attestation — a timestamp somebody else can vouch for — belongs to
// Common Seal, which is not built (COMPONENTS.md). Naming that gap is more
// useful than dressing FNV-1a up as tamper-proofing.
import type { Measure, Prediction } from '@/data/types';

/**
 * Canonical serialization. Field order is fixed here rather than left to
 * `JSON.stringify` over the objects, because key order in a literal is an
 * authoring accident and a hash that changes when someone reorders two
 * properties would fire false alarms forever.
 */
function canonical(predictions: Prediction[], schema: Measure[]): string {
  const p = predictions.map((x) => [x.id, x.label, x.value, x.unit, x.confidence, x.basis]);
  const m = schema.map((x) => [x.id, x.label, x.unit, x.timepoint, x.predictionId]);
  return JSON.stringify({ p, m });
}

/** FNV-1a, 32-bit. Two passes over different offsets give a 16-char digest. */
function fnv1a(input: string, seed: number): number {
  let h = seed;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/**
 * Deterministic digest of a runbook's frozen content. Same predictions and
 * schema always give the same string, in any session and any browser.
 */
export function runbookLockHash(predictions: Prediction[], schema: Measure[]): string {
  const text = canonical(predictions, schema);
  const a = fnv1a(text, 2166136261);
  const b = fnv1a(text + String(text.length), 2166136243);
  return a.toString(16).padStart(8, '0') + b.toString(16).padStart(8, '0');
}

/**
 * Whether a runbook's stored hash still matches its stored content.
 *
 * An unlocked runbook is vacuously intact — there is nothing to drift from.
 * A locked one whose content no longer hashes to `lockHash` has been edited
 * after freezing, which is the exact failure locking exists to catch, so the
 * caller should surface it rather than swallow it.
 */
export function lockIntact(runbook: {
  predictions: Prediction[];
  measurementSchema: Measure[];
  lockedAt: string | null;
  lockHash: string | null;
}): boolean {
  if (!runbook.lockedAt || !runbook.lockHash) return true;
  return runbookLockHash(runbook.predictions, runbook.measurementSchema) === runbook.lockHash;
}

/**
 * Predictions freeze once a runbook has done anything. Draft and
 * awaiting-budget runbooks have not started, so theirs are still editable;
 * everything else has consumed compute against them and must be frozen.
 */
export function shouldBeLocked(status: string, progressPct: number): boolean {
  if (status === 'draft' || status === 'awaiting_budget') return false;
  return progressPct > 0 || status !== 'draft';
}
