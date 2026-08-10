// Extraction-record assembly. The SI twin is recomputed here from
// (value, unit) so BUILD-SPEC invariant 3 holds by construction rather than by
// authoring discipline.
import type { ExtractionRecord } from './types';
import { toSI } from '@/engine/units';
import { RECORDS_A } from './corpus/setA';
import { RECORDS_B } from './corpus/setB';
import { RECORDS_C } from './corpus/setC';

function normalize(r: ExtractionRecord): ExtractionRecord {
  return { ...r, si: toSI(r.value, r.unit) };
}

export const RECORDS: ExtractionRecord[] = [...RECORDS_A, ...RECORDS_B, ...RECORDS_C]
  .map(normalize)
  .sort((a, b) => a.id.localeCompare(b.id));

export const RECORDS_BY_ID: Record<string, ExtractionRecord> = Object.fromEntries(
  RECORDS.map((r) => [r.id, r]),
);

/** The hand-curated gold set (§14.3). */
export const GOLD_RECORDS: ExtractionRecord[] = RECORDS.filter((r) => r.gold);
