// A deposition's readings as time series (OF-BLD-014 §7.1).
//
// An entry with a sample time is one reading in its measure's series; the
// series is in time order, in the measure's own unit, and needs two points.
// Two entries on one measure at one time are a reading and its correction:
// the later stands (amendEntry appends, and carries the time across). An
// entry with no time keeps today's meaning and is in no series.
//
// CSV attachment lives here too: `time_h, measure, value, unit`, each row an
// unconfirmed entry whose `raw` is the line itself, matched to the schema by
// the capture matcher; a row it cannot place stays verbatim as an
// observation.
import type { Deposition, DepositionEntry, Measure, Runbook, SeriesRole } from '@/data/types';
import { matchToSchema } from './capture';
import { convert } from './units';

export interface SeriesPoint {
  t: number;
  value: number;
  entryId: string;
  confirmed: boolean;
}

export interface Series {
  measureId: string;
  label: string;
  unit: string;
  role: SeriesRole | null;
  points: SeriesPoint[];
}

function inUnit(e: DepositionEntry, unit: string): number | null {
  if (e.unit === unit) return e.value;
  try {
    return convert(e.value, e.unit, unit);
  } catch {
    return null;
  }
}

/** Every measure with two or more timed readings, each in time order. */
export function seriesOf(dep: Deposition, runbook: Pick<Runbook, 'measurementSchema'>): Series[] {
  const times = dep.sampleTimes ?? {};
  const out: Series[] = [];
  for (const m of runbook.measurementSchema) {
    const byTime = new Map<number, SeriesPoint>();
    for (const e of dep.entries) {
      if (e.measureId !== m.id || times[e.id] === undefined) continue;
      const v = inUnit(e, m.unit);
      if (v === null || !Number.isFinite(v)) continue;
      // Entries are appended, so a later one at the same time replaces it.
      byTime.set(times[e.id], { t: times[e.id], value: v, entryId: e.id, confirmed: e.confirmed });
    }
    const points = [...byTime.values()].sort((a, b) => a.t - b.t);
    if (points.length >= 2) out.push({ measureId: m.id, label: m.label, unit: m.unit, role: dep.seriesRoles?.[m.id] ?? null, points });
  }
  return out;
}

export interface CsvRow {
  line: string;
  time: number;
  measure: string;
  value: number;
  unit: string;
}

export interface ParsedCsv {
  rows: CsvRow[];
  /** Lines that are not a row of four fields with a time and a value. */
  unreadable: string[];
}

/** Read `time_h, measure, value, unit`, header first; rows come back in time order. */
export function parseReadingsCsv(text: string): ParsedCsv {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const rows: CsvRow[] = [];
  const unreadable: string[] = [];
  for (const [i, line] of lines.entries()) {
    const cells = line.split(',').map((c) => c.trim());
    if (i === 0 && cells[0]?.toLowerCase() === 'time_h') continue;
    const time = Number(cells[0]);
    const value = Number(cells[2]);
    if (cells.length !== 4 || !cells[0] || !cells[2] || !Number.isFinite(time) || !Number.isFinite(value)) {
      unreadable.push(line);
      continue;
    }
    rows.push({ line, time, measure: cells[1], value, unit: cells[3] });
  }
  // Stable: rows at one time keep their order in the file.
  rows.sort((a, b) => a.time - b.time);
  return { rows, unreadable };
}

/** The measure a row names, by the capture matcher, or null. */
export function placeRow(row: CsvRow, schema: Measure[]): string | null {
  return matchToSchema(`${row.measure} ${row.value} ${row.unit}`, schema)?.measureId ?? null;
}
