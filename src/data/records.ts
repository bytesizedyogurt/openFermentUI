// Extraction-record assembly. The SI twin is recomputed here from
// (value, unit) so the invariant holds by construction rather than by
// authoring discipline. Categorical records carry a string value and are
// passed through untouched.
import type { ExtractionRecord } from './types';
import { toSI } from '@/engine/units';
import { RECORDS_AB } from './corpus/threadAB';
import { RECORDS_CD } from './corpus/threadCD';
import { RECORDS_EF } from './corpus/threadEF';
import { RECORDS_G } from './corpus/threadG';
import { RECORDS_H } from './corpus/threadH';
import { RECORDS_IJ } from './corpus/threadIJ';
import { RECORDS_KL } from './corpus/threadKL';
import { RECORDS_MNO } from './corpus/threadMNO';

function normalize(r: ExtractionRecord): ExtractionRecord {
  if (typeof r.value !== 'number') return { ...r, si: { value: 0, unit: r.unit } };
  return { ...r, si: toSI(r.value, r.unit) };
}

export const RECORDS: ExtractionRecord[] = [
  ...RECORDS_AB,
  ...RECORDS_CD,
  ...RECORDS_EF,
  ...RECORDS_G,
  ...RECORDS_H,
  ...RECORDS_IJ,
  ...RECORDS_KL,
  ...RECORDS_MNO,
].map(normalize);

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
