// Extraction-record assembly. The SI twin is recomputed here from
// (value, unit) so the invariant holds by construction rather than by
// authoring discipline. Categorical records carry a string value and are
// passed through untouched.
// The collection itself now comes from the adapter; this module keeps only
// the derived views built on top of it.
import { RECORDS } from '@/data/source';

export { RECORDS };

import type { ExtractionRecord } from './types';
import { toSI } from '@/engine/units';

function normalize(r: ExtractionRecord): ExtractionRecord {
  if (typeof r.value !== 'number') return { ...r, si: { value: 0, unit: r.unit } };
  return { ...r, si: toSI(r.value, r.unit) };
}


export const RECORDS_BY_ID: Record<string, ExtractionRecord> = Object.fromEntries(
  RECORDS.map((r) => [r.id, r]),
);

/**
 * Hand-curated reference annotations. Empty in the seed: no paper's full text
 * has been retrieved, so there are no source spans to annotate a gold set
 * against. The gold set exists as a plan (Validation) plus whatever a reviewer
 * flags during a session.
 */
export const GOLD_RECORDS: ExtractionRecord[] = RECORDS.filter((r) => r.gold);

// Which records may enter a statistic is decided by `aggregateExclusion` in
// store.ts, applied at each aggregation site. A precomputed array here would be
// a second, silently divergent answer to the same question.
