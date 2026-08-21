// Parameter aggregation (OF-FE-003 §5.1).
//
// The Ledger's primary object is the parameter, not the record. This module
// derives that view from the records at load, so it can never drift from them.
//
// Deliberately not a Bayesian posterior. With 134 curated records and none
// verified, a hierarchical fit would be false precision — it would report a
// credible interval narrower than the evidence supports and attach authority to
// the narrowing. Median of primary records with a visible interquartile range
// is what this corpus can honestly carry. `Aggregate.method` names the scheme
// so a screen states how the number was made, and the shape is stable enough
// that a real posterior can replace these internals later without any screen
// changing.
import type {
  Aggregate,
  Contradiction,
  ExtractionRecord,
  FieldId,
  ParameterView,
  RefereeStatus,
} from '@/data/types';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { convert, asNumber } from '@/engine/units';
import { aggregateExclusion, isAggregatable, EXCLUSION_NOTE } from '@/engine/aggregation';
// One median for the whole repository. `median-of-primary-v1` is a named,
// versioned statistic, so a second implementation drifting from it would be
// a reported number disagreeing with itself across two screens.
import { quantile } from '@/lib/stats';

export const AGGREGATE_METHOD = 'median-of-primary-v1';

/**
 * Convert a record into the field's canonical unit, or null when it cannot be
 * expressed there. A refusal is not a failure to handle — %TSP and g/L are not
 * interconvertible without a cell density, and the engine says so rather than
 * guessing. Such a record simply does not enter this statistic.
 */
function canonical(r: ExtractionRecord, unit: string): number | null {
  const n = asNumber(r.value);
  if (n === null) return null; // categorical — not summarisable as a range
  if (unit === '' || r.unit === unit) return n;
  try {
    return convert(n, r.unit, unit);
  } catch {
    return null;
  }
}

function stratify(
  rows: { r: ExtractionRecord; v: number }[],
  key: (r: ExtractionRecord) => string | undefined,
  label: (k: string) => string,
): { key: string; label: string; n: number; median: number }[] {
  const groups = new Map<string, number[]>();
  for (const { r, v } of rows) {
    const k = key(r);
    if (!k) continue;
    const list = groups.get(k) ?? [];
    list.push(v);
    groups.set(k, list);
  }
  return [...groups.entries()]
    .map(([k, vals]) => {
      const sorted = [...vals].sort((a, b) => a - b);
      return { key: k, label: label(k), n: sorted.length, median: quantile(sorted, 0.5) };
    })
    .sort((a, b) => b.n - a.n);
}

/**
 * The aggregate over a set of records, or null when there is nothing honest to
 * report. Returns null rather than a one-record "median": a single value is a
 * value, and dressing it as a statistic invents a consensus that does not exist.
 */
export function aggregate(
  records: ExtractionRecord[],
  /**
   * Publication year per paper id. The record does not carry a year — it lives
   * on the Paper — and this module stays pure rather than reaching for the
   * corpus, so the caller supplies the lookup. Omitted means no year stratum,
   * which is honest: better an absent grouping than an invented one.
   */
  yearOf?: (paperId: string) => number | undefined,
): Aggregate | null {
  if (records.length === 0) return null;
  const unit = ONTOLOGY_BY_ID[records[0].field]?.canonicalUnit ?? records[0].unit;

  const usable = records
    .filter(isAggregatable)
    .map((r) => ({ r, v: canonical(r, unit) }))
    .filter((x): x is { r: ExtractionRecord; v: number } => x.v !== null);

  if (usable.length < 2) return null;

  const values = usable.map((x) => x.v).sort((a, b) => a - b);
  return {
    median: quantile(values, 0.5),
    p25: quantile(values, 0.25),
    p75: quantile(values, 0.75),
    min: values[0],
    max: values[values.length - 1],
    n: usable.length,
    nPrimary: usable.filter((x) => x.r.isPrimary).length,
    unit,
    strata: [
      ...stratify(usable, (r) => r.organism, (k) => `organism · ${k}`),
      ...stratify(usable, (r) => r.method, (k) => `method · ${k}`),
      ...(yearOf
        ? stratify(
            usable,
            (r) => {
              const y = yearOf(r.paperId);
              return y ? String(Math.floor(y / 5) * 5) : undefined;
            },
            (k) => `${k}–${Number(k) + 4}`,
          )
        : []),
    ],
    method: AGGREGATE_METHOD,
  };
}

/**
 * The full parameter view. Everything held out of the statistic is listed with
 * the reason taken from EXCLUSION_NOTE rather than reworded here, so one wording
 * serves the whole app.
 */
export function buildParameterView(
  field: FieldId,
  records: ExtractionRecord[],
  contradictions: Contradiction[] = [],
  yearOf?: (paperId: string) => number | undefined,
): ParameterView {
  const mine = records.filter((r) => r.field === field);
  const def = ONTOLOGY_BY_ID[field];

  const excluded = mine
    .map((r) => {
      const why = aggregateExclusion(r);
      return why ? { recordId: r.id, reason: EXCLUSION_NOTE[why] } : null;
    })
    .filter((x): x is { recordId: string; reason: string } => x !== null);

  // A record that cannot be converted into the canonical unit is held out too,
  // and for a reason worth stating — it is usually an explained refusal.
  const unit = def?.canonicalUnit ?? '';
  for (const r of mine) {
    if (!isAggregatable(r)) continue;
    if (canonical(r, unit) === null) {
      excluded.push({
        recordId: r.id,
        reason:
          asNumber(r.value) === null
            ? 'categorical — has no median'
            : `not convertible to ${unit || 'the canonical unit'} — excluded from statistics`,
      });
    }
  }

  const mineContradictions = contradictions.filter((c) =>
    c.recordIds.some((id) => mine.some((r) => r.id === id)),
  );

  const referee: RefereeStatus = mineContradictions.length
    ? { state: 'contradicted', contradictionIds: mineContradictions.map((c) => c.id) }
    : mine.length === 0
      ? { state: 'unchecked' }
      : { state: 'consistent', checks: ['ontology', 'numbering', 'range'] };

  return {
    field,
    def,
    recordIds: mine.map((r) => r.id),
    aggregate: aggregate(mine, yearOf),
    contradictions: mineContradictions,
    referee,
    excluded,
  };
}
