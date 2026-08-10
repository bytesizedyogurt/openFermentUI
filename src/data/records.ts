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

/** Hand-curated reference annotations. Empty until tranche-1 ingest. */
export const GOLD_RECORDS: ExtractionRecord[] = RECORDS.filter((r) => r.gold);

/**
 * Records that may enter aggregate statistics: primary measurements only,
 * excluding industry estimates and rejected rows (OF-COR-001 §16 O8, §19).
 */
export const AGGREGATABLE: ExtractionRecord[] = RECORDS.filter(
  (r) => r.isPrimary !== false && r.provenance !== 'industry-estimate' && r.status !== 'rejected',
);
