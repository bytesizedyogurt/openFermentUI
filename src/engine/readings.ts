// A deposition's readings as the service's lookup reads them
// (core/openferment_core/measurements.py `corrected_by`; ADR-006's
// measurement). An entry is a reading that stands for its measure until a
// later entry on the same measure corrects it: one with no sample time
// corrects an earlier one with none, and a reading in a series (an entry with
// a sample time) is corrected by a later entry at its own time alone, as the
// bench's correction carries the time across (store `amendEntry`). The bench
// reads back the entries that stand, and the record says which entry corrects
// which, so the two pages and a run's lookup read one rule.
import type { Deposition, DepositionEntry } from '@/lib/studies';

/** The id of the entry that corrects `entry` in `deposition`, or null when `entry` stands for its measure. */
export function correctedBy(deposition: Deposition, entry: DepositionEntry): string | null {
  const times = deposition.sampleTimes ?? {};
  const at = deposition.entries.findIndex((e) => e.id === entry.id);
  if (at < 0) return null;
  const when = times[entry.id];
  const later = deposition.entries
    .slice(at + 1)
    .filter((e) => e.measureId === entry.measureId && times[e.id] === when);
  return later.length ? later[later.length - 1].id : null;
}

/** The entries that wait to be read back: each unconfirmed entry that stands for its measure. */
export function awaitingReadBack(deposition: Deposition): DepositionEntry[] {
  return deposition.entries.filter((e) => !e.confirmed && correctedBy(deposition, e) === null);
}

/**
 * The entry that corrects `original` to `value` (store `amendEntry`), with
 * id `id`, typed at `now`: the same reading, so it keeps the time the reading
 * was taken (`at`, the time a measurement names) and says when it was
 * corrected, confirmed by the person who typed it.
 */
export function correctionOf(original: DepositionEntry, id: string, value: number, now: string): DepositionEntry {
  return { ...original, id, value, raw: `${original.raw} → corrected to ${value} ${original.unit}`, confirmed: true, correctedAt: now };
}
