// MIRROR of packages/assay/openferment_assay/metrics.py. Python is canonical.
// Changes go there first, then here, and parity is enforced by pnpm verify.
//
// Scoring an extractor run belongs to Inspect AI, which is Python only, so the
// scorer lives in packages/assay. This copy stays because the validation screen
// recomputes live in the browser as a reviewer corrects records — a round trip
// to a server per keystroke is not a thing that screen can do. Both sides
// replay fixtures/metrics.json, so the agreement is checked rather than
// remembered: `pnpm check:metrics` here, `packages/assay/tests` there.
//
// Validation metrics (OF-DES-001 §8.8): P/R/F1 against the gold set,
// recomputed live from seeded per-run confusion data.
import type { ExtractionRecord, FieldId, RunOutput } from '@/data/types';

export interface FieldMetrics {
  field: FieldId;
  nGold: number;
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
  topFailure: string;
}

export interface RunMetrics {
  run: string;
  micro: { precision: number; recall: number; f1: number; tp: number; fp: number; fn: number };
  perField: FieldMetrics[];
  goldSize: number;
  papersCovered: number;
}

function prf(tp: number, fp: number, fn: number) {
  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
  return { precision, recall, f1 };
}

const FAILURE_LABEL: Record<string, string> = {
  value_mismatch: 'value mismatch',
  unit_error: 'unit normalization',
  span_error: 'wrong span',
  miss: 'missed entirely',
};

/**
 * Compute metrics for one extractor run. A gold record counts TP when the
 * run's outcome is 'match'; mismatch outcomes count both FP and FN (the run
 * produced a wrong record AND missed the gold one); 'miss' counts FN only.
 * Seeded false positives (spurious extractions) add FP.
 */
export function computeRunMetrics(
  run: RunOutput,
  records: ExtractionRecord[],
): RunMetrics {
  const goldRecords = records.filter((r) => r.gold);
  const byId = new Map(goldRecords.map((r) => [r.id, r]));
  const perFieldCounts = new Map<FieldId, { tp: number; fp: number; fn: number; failures: Map<string, number> }>();
  const ensure = (f: FieldId) => {
    if (!perFieldCounts.has(f)) perFieldCounts.set(f, { tp: 0, fp: 0, fn: 0, failures: new Map() });
    return perFieldCounts.get(f)!;
  };

  for (const res of run.results) {
    const rec = byId.get(res.goldRecordId);
    if (!rec) continue; // gold record removed during session — drop from metrics
    const c = ensure(rec.field);
    if (res.outcome === 'match') c.tp += 1;
    else if (res.outcome === 'miss') {
      c.fn += 1;
      c.failures.set('miss', (c.failures.get('miss') ?? 0) + 1);
    } else {
      c.fp += 1;
      c.fn += 1;
      c.failures.set(res.outcome, (c.failures.get(res.outcome) ?? 0) + 1);
    }
  }
  for (const fpRow of run.falsePositives) {
    const c = ensure(fpRow.field);
    c.fp += 1;
    c.failures.set('spurious', (c.failures.get('spurious') ?? 0) + 1);
  }

  const goldByField = new Map<FieldId, number>();
  for (const r of goldRecords) goldByField.set(r.field, (goldByField.get(r.field) ?? 0) + 1);

  const perField: FieldMetrics[] = [];
  let tp = 0,
    fp = 0,
    fn = 0;
  for (const [field, c] of perFieldCounts) {
    tp += c.tp;
    fp += c.fp;
    fn += c.fn;
    let topFailure = '—';
    let max = 0;
    for (const [k, v] of c.failures) {
      if (v > max) {
        max = v;
        topFailure = FAILURE_LABEL[k] ?? k;
      }
    }
    perField.push({
      field,
      nGold: goldByField.get(field) ?? 0,
      tp: c.tp,
      fp: c.fp,
      fn: c.fn,
      ...prf(c.tp, c.fp, c.fn),
      topFailure,
    });
  }
  perField.sort((a, b) => b.nGold - a.nGold);

  const papers = new Set(goldRecords.map((r) => r.paperId));
  return {
    run: run.run,
    micro: { ...prf(tp, fp, fn), tp, fp, fn },
    perField,
    goldSize: goldRecords.length,
    papersCovered: papers.size,
  };
}
