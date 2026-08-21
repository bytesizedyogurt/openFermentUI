// The run time-series panel and its scrubber (OF-DEMO-002 §3.5, §4.7).
//
// Stacked channels on one shared x-axis in Ticks. The excursion window renders
// as a band across EVERY channel simultaneously — that simultaneity is the
// finding, because an operator looking at DO alone would see a dip and an
// operator looking at RQ alone would see nothing.
//
// TWO THINGS THE READOUT MUST SAY, and they are the reason this is not a chart
// library call:
//
//  1. Derived channels carry a computed tick. OUR, CER and RQ are calculated
//     from off-gas, not measured, and a readout that showed them beside a pH
//     probe reading without saying so would be presenting arithmetic as
//     instrumentation.
//  2. Prior runs render ghosted BEHIND the current one. A single trajectory
//     cannot show that a deviation is a deviation; the comparison basis is what
//     makes it one, and it has to be visible rather than cited.
//
// Keyboard: arrows step one Tick, shift-arrow ten, `[` and `]` jump to the
// excursion boundaries.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { Channel, RunRecord } from '@/data/demo/types';
import { cx } from '@/components/ui';

const ROW_H = 40;

function pathFor(values: number[], w: number, h: number, lo: number, hi: number): string {
  const span = Math.max(1e-9, hi - lo);
  const n = values.length;
  if (n < 2) return '';
  return values
    .map((v, i) => {
      const x = (i / (n - 1)) * w;
      const y = h - ((v - lo) / span) * h;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');
}

export function TickScrubber({
  run,
  priorRuns = [],
  className,
}: {
  run: RunRecord;
  priorRuns?: RunRecord[];
  className?: string;
}) {
  const n = run.channels[0]?.values.length ?? 0;
  const [tick, setTick] = useState(() => Math.floor(n / 2));
  const boxRef = useRef<HTMLDivElement>(null);

  const bounds = useMemo(() => {
    const m = new Map<string, { lo: number; hi: number }>();
    for (const ch of run.channels) {
      // Prior runs share the scale, or a ghost would sit off-canvas and the
      // comparison would silently stop being one.
      const all = [
        ...ch.values,
        ...priorRuns.flatMap((r) => r.channels.find((c) => c.id === ch.id)?.values ?? []),
      ];
      const lo = Math.min(...all);
      const hi = Math.max(...all);
      const pad = hi === lo ? Math.max(Math.abs(hi) * 0.1, 1) : (hi - lo) * 0.08;
      m.set(ch.id, { lo: lo - pad, hi: hi + pad });
    }
    return m;
  }, [run, priorRuns]);

  const exc = run.excursions[0];

  const step = useCallback(
    (d: number) => setTick((t) => Math.max(0, Math.min(n - 1, t + d))),
    [n],
  );

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      const mult = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowLeft') { e.preventDefault(); step(-mult); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); step(mult); }
      else if (e.key === '[' && exc) { e.preventDefault(); setTick(exc.startTick); }
      else if (e.key === ']' && exc) { e.preventDefault(); setTick(exc.endTick); }
    };
    el.addEventListener('keydown', onKey);
    return () => el.removeEventListener('keydown', onKey);
  }, [step, exc]);

  if (!n) return <div className="text-caption text-ink-soft">This run carries no channels.</div>;

  const inExcursion = !!exc && tick >= exc.startTick && tick <= exc.endTick;

  return (
    <div className={cx('flex flex-col lg:flex-row gap-4', className)}>
      <div
        ref={boxRef}
        tabIndex={0}
        role="group"
        aria-label={`${run.id} time series, Tick ${tick} of ${n - 1}`}
        className="min-w-0 flex-1 outline-none focus:ring-1 focus:ring-accent/40"
        onKeyDown={(e) => {
          // Arrow keys must not scroll the page while the scrubber has focus.
          if (['ArrowLeft', 'ArrowRight'].includes(e.key)) e.preventDefault();
        }}
      >
        <div className="text-caption text-ink-soft mb-1">
          Tick {tick} / {n - 1} · arrows step, shift-arrow ten
          {exc && ', [ and ] jump to the excursion boundaries'}
        </div>

        <div
          className="relative border border-line of-grid"
          onPointerDown={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            const set = (clientX: number) =>
              setTick(Math.round(((clientX - r.left) / r.width) * (n - 1)));
            set(e.clientX);
            const move = (ev: PointerEvent) => set(ev.clientX);
            const up = () => {
              window.removeEventListener('pointermove', move);
              window.removeEventListener('pointerup', up);
            };
            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', up);
          }}
        >
          {run.channels.map((ch) => {
            const b = bounds.get(ch.id)!;
            return (
              <div key={ch.id} className="relative border-b border-line/50 last:border-0" style={{ height: ROW_H }}>
                <svg width="100%" height={ROW_H} viewBox={`0 0 1000 ${ROW_H}`} preserveAspectRatio="none" className="block">
                  {/* Prior runs first, behind. */}
                  {priorRuns.map((pr) => {
                    const pc = pr.channels.find((c) => c.id === ch.id);
                    if (!pc) return null;
                    return (
                      <path
                        key={pr.id}
                        d={pathFor(pc.values, 1000, ROW_H, b.lo, b.hi)}
                        fill="none"
                        stroke="rgb(var(--ink))"
                        strokeOpacity="var(--ghost-alpha, 0.25)"
                        strokeWidth="1"
                        vectorEffect="non-scaling-stroke"
                      />
                    );
                  })}
                  {/* The excursion band, on every channel at once. */}
                  {exc && (
                    <rect
                      x={(exc.startTick / (n - 1)) * 1000}
                      y="0"
                      width={((exc.endTick - exc.startTick) / (n - 1)) * 1000}
                      height={ROW_H}
                      fill="rgb(var(--signal-warn))"
                      opacity="0.14"
                    />
                  )}
                  <path
                    d={pathFor(ch.values, 1000, ROW_H, b.lo, b.hi)}
                    fill="none"
                    stroke="rgb(var(--ink))"
                    strokeWidth="1.25"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
                <div className="absolute left-1 top-0.5 text-[10px] text-ink-soft pointer-events-none">
                  {ch.label}
                  <span className="font-num"> {ch.unit}</span>
                  {ch.derived && <span className="ml-1 opacity-70">computed</span>}
                </div>
              </div>
            );
          })}

          {/* The cursor, over everything. */}
          <div
            className="absolute inset-y-0 w-px bg-accent pointer-events-none"
            style={{ left: `${(tick / (n - 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* The readout. */}
      <div className="lg:w-72 shrink-0">
        <div className="text-caption text-ink-soft mb-1">
          At Tick {tick}
          {inExcursion && (
            <span className="ml-2 text-signal-warn">inside the excursion window</span>
          )}
        </div>
        <table className="w-full text-caption">
          <tbody>
            {run.channels.map((ch: Channel) => (
              <tr key={ch.id}>
                <td className="text-ink-soft pr-2 py-px whitespace-nowrap">{ch.label}</td>
                <td className="py-px text-right">
                  {/* A computed channel is marked HERE, in the readout, not only
                      in the axis label — this is where a number gets copied out
                      of, and it must not leave without its provenance. */}
                  <span
                    className={cx('font-num tick-cell', ch.derived ? 'tick-user tick-ev-computed' : 'tick-verified', 'pl-2')}
                    title={ch.derived ? 'Computed from off-gas, not measured' : 'Measured'}
                  >
                    {+(ch.values[tick] ?? 0).toFixed(2)}
                  </span>
                  <span className="text-ink-soft font-num ml-1">{ch.unit}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {priorRuns.length > 0 && (
          <div className="text-caption text-ink-soft mt-2">
            {priorRuns.length} prior run{priorRuns.length > 1 ? 's' : ''} ghosted behind:{' '}
            <span className="font-num">{priorRuns.map((r) => r.id).join(', ')}</span>. A single
            trajectory cannot show that a deviation is one — the basis is what makes it a
            deviation, so it is drawn rather than cited.
          </div>
        )}
      </div>
    </div>
  );
}
