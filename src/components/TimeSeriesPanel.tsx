// A deposition's readings as time series (OF-BLD-014 §7.1).
//
// Per measure, each reading with its hours into the run, which a person
// types; the role a series plays (biomass, product, substrate), which a
// person assigns because a Measure carries no such marker; and readings
// logged elsewhere, attached as CSV. Nothing here fits anything: fermOS
// reads these series (§7.2).
import { useState } from 'react';
import type { Deposition, Runbook, SeriesRole } from '@/data/types';
import { useStore } from '@/store';
import { seriesOf } from '@/engine/series';
import { Button } from './ui';
import { TrajectoryBand } from './figures';

const ROLES: (SeriesRole | '')[] = ['', 'biomass', 'product', 'substrate'];

export function TimeSeriesPanel({ deposition, runbook }: { deposition: Deposition; runbook: Runbook }) {
  const setSampleTime = useStore((s) => s.setSampleTime);
  const setSeriesRole = useStore((s) => s.setSeriesRole);
  const attachReadings = useStore((s) => s.attachReadings);
  const [csv, setCsv] = useState('');
  const [said, setSaid] = useState<string | null>(null);
  const times = deposition.sampleTimes ?? {};
  const series = seriesOf(deposition, runbook);
  const measures = runbook.measurementSchema.filter((m) => deposition.entries.some((e) => e.measureId === m.id));

  return (
    <div className="space-y-4" data-testid="time-series">
      {series.length > 0 && (
        <TrajectoryBand
          title="What did this run measure, over time?"
          series={series.map((x) => ({ role: x.role ?? x.measureId, label: x.label, unit: x.unit, readings: x.points.map((p) => ({ t: p.t, value: p.value })) }))}
          csvName={`series-${deposition.id}`}
        />
      )}
      {measures.length === 0 && <p className="text-body text-ink-soft">No reading yet. Type them in run mode, or attach them below.</p>}
      {measures.map((m) => {
        const s = series.find((x) => x.measureId === m.id);
        return (
          <div key={m.id} data-testid="series-measure">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium text-body">
                {m.label} <span className="text-caption text-ink-soft font-num">{m.unit}</span>
              </span>
              <label className="text-caption text-ink-soft">
                Series role{' '}
                <select
                  className="input py-0.5"
                  aria-label={`Series role for ${m.label}`}
                  value={deposition.seriesRoles?.[m.id] ?? ''}
                  onChange={(e) => setSeriesRole(deposition.id, m.id, (e.target.value || null) as SeriesRole | null)}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r || 'none'}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="text-caption text-ink-soft">
              {s ? `A series of ${s.points.length} readings in time order.` : 'Not a series yet: it needs two readings with a time.'}
            </p>
            <ul className="mt-1 space-y-1">
              {deposition.entries
                .filter((e) => e.measureId === m.id)
                .map((e) => (
                  <li key={e.id} className="flex flex-wrap items-center gap-2 text-body">
                    <label className="text-caption text-ink-soft">
                      <span className="sr-only">Hours into the run for {e.raw}</span>
                      <input
                        className="input w-20 py-0.5 font-num"
                        type="number"
                        step="any"
                        aria-label={`Hours into the run for ${e.id}`}
                        defaultValue={times[e.id] ?? ''}
                        onBlur={(ev) => setSampleTime(deposition.id, e.id, ev.target.value === '' ? null : Number(ev.target.value))}
                      />{' '}
                      h
                    </label>
                    <span className="font-num">
                      {e.value} {e.unit}
                    </span>
                    {!e.confirmed && <span className="text-caption text-signal-warn">unconfirmed</span>}
                    <span className="text-caption text-ink-soft truncate max-w-[40ch]">“{e.raw}”</span>
                  </li>
                ))}
            </ul>
          </div>
        );
      })}
      {deposition.state !== 'staged' && (
        <div>
          <label className="block text-caption text-ink-soft mb-1" htmlFor={`csv-${deposition.id}`}>
            Attach readings (CSV): <span className="font-num">time_h, measure, value, unit</span>, one reading a line. A line the
            schema cannot place is kept word for word as an observation.
          </label>
          <textarea id={`csv-${deposition.id}`} className="input w-full font-num" rows={4} value={csv} onChange={(e) => setCsv(e.target.value)} />
          <div className="mt-1 flex items-center gap-2">
            <Button
              disabled={!csv.trim()}
              onClick={() => {
                const r = attachReadings(deposition.id, csv);
                setSaid(`${r.attached} reading${r.attached === 1 ? '' : 's'} attached, unconfirmed; ${r.kept} line${r.kept === 1 ? '' : 's'} kept as observation${r.kept === 1 ? '' : 's'}.`);
                setCsv('');
              }}
            >
              Attach readings
            </Button>
            {said && (
              <span className="text-caption text-ink-soft" data-testid="attach-result">
                {said}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
