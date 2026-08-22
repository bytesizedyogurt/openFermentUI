// The contradiction rail (OF-DEMO-002 §3.3, §4.2).
//
// Every Accession on one field, on a shared normalised axis. One mark per
// Accession, hue by provenance, geometry by source type, median as a full-width
// 2px line. Held records render dimmed and NEVER move the median.
//
// THE RULE THIS COMPONENT EXISTS TO ENFORCE (OF-DEMO-001 §2.5): where two
// Accessions disagree, both are shown and the system states that it is not
// resolving them. It does not average. The median line is a summary of what is
// there, not a reconciliation of it, and where the spread is bimodal the rail
// says so in words rather than letting a centre line imply agreement.
//
// AND THE RULE ABOUT NOT RENDERING (OF-DEMO-003 §5, contradiction 4): furfural
// tolerance at 1.9 and 0.9 g L⁻¹ is not a contradiction — the two are different
// organisms and the context field says which. `isContradiction` is what keeps
// this component from flagging it, because a system that flags everything is as
// useless as one that flags nothing.
import { useMemo } from 'react';

import type { Accession, FieldId } from '@/data/demo/types';
import { FIELD_BY_ID } from '@/data/demo/core';
import { ACCESSIONS, ACCESSION_BY_ID } from '@/data/demo/accessions';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { demoTickClass, demoTickTitle, HOLD_LABEL } from './DemoTick';
// The statistics and the contradiction predicate live in lib/demo.ts, not here:
// `check:demo-seed` has to assert over them and it runs under node, where this
// file's `href` import touches `window`. A rule the gate cannot reach is a rule
// nobody is holding.
import { accessionsOnField, countable, median, quartiles, isContradiction, conflictPairs, reconciledPairs } from '@/lib/demo';

export function DemoContradictionRail({
  field,
  accessions,
  className,
  height = 132,
}: {
  field: FieldId;
  accessions?: Accession[];
  className?: string;
  height?: number;
}) {
  const def = FIELD_BY_ID[field];
  const accs = useMemo(() => accessions ?? accessionsOnField(field), [field, accessions]);

  const stats = useMemo(() => {
    const live = countable(accs);
    const vals = live.map((a) => a.normalized.value);
    const all = accs.map((a) => a.normalized.value);
    const lo = Math.min(...all);
    const hi = Math.max(...all);
    // A field where every value is identical still needs a band to draw in.
    const pad = hi === lo ? Math.max(Math.abs(hi) * 0.1, 1) : (hi - lo) * 0.08;
    return {
      live,
      med: median(vals),
      iqr: quartiles(vals),
      lo: lo - pad,
      hi: hi + pad,
      n: live.length,
    };
  }, [accs]);

  if (!accs.length) {
    return (
      <div className={cx('text-caption text-ink-soft', className)}>
        No Accession on {def?.name ?? field} in this pool.
      </div>
    );
  }

  const y = (v: number) => {
    const t = (v - stats.lo) / Math.max(1e-9, stats.hi - stats.lo);
    return (1 - t) * height;
  };

  const contradicted = isContradiction(accs);
  const reconciled = reconciledPairs(accs);
  const held = accs.filter((a) => a.hold);
  const aggregatable = def?.aggregatable !== false;

  return (
    <div className={cx('flex gap-4', className)}>
      {/* The rail itself. Narrow on purpose — it is a distribution, not a chart. */}
      <div className="shrink-0" style={{ width: 'var(--rail-w, 18px)' }}>
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 18 ${height}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`${def?.name ?? field}: ${accs.length} Accessions`}
          className="border border-line bg-accent-wash/20 rail-settle"
        >
          {/* IQR, behind everything. */}
          {stats.iqr && aggregatable && (
            <rect
              x="0"
              y={y(stats.iqr.q3)}
              width="18"
              height={Math.max(1, y(stats.iqr.q1) - y(stats.iqr.q3))}
              fill="rgb(var(--accent))"
              opacity="0.10"
            />
          )}
          {/* One mark per Accession, 7px wide, offset so a cluster reads as one. */}
          {accs.map((a, i) => (
            <rect
              key={a.id}
              x={i % 2 === 0 ? 1.5 : 9.5}
              y={y(a.normalized.value) - 0.5}
              width="7"
              height="1"
              fill={a.hold ? 'rgb(var(--ink-soft))' : 'rgb(var(--ink))'}
              opacity={a.hold ? 0.4 : 0.85}
            >
              <title>{`${a.id} — ${a.reported.value} ${a.reported.unit}${a.hold ? ` (held: ${HOLD_LABEL[a.hold]})` : ''}`}</title>
            </rect>
          ))}
          {/* Median last, so it sits over the marks. Only where a median means
              something: on a categorical or design-choice field it does not. */}
          {stats.med !== null && aggregatable && (
            <rect x="0" y={y(stats.med) - 1} width="18" height="2" fill="rgb(var(--ink))" />
          )}
        </svg>
      </div>

      {/* The reading of it. */}
      <div className="min-w-0 flex-1">
        <div className="text-caption text-ink-soft">{def?.name ?? field}</div>
        {aggregatable && stats.med !== null ? (
          <div className="font-num text-body">
            {+stats.med.toFixed(4)} {def?.canonicalUnit}
            <span className="text-caption text-ink-soft ml-2">
              median of {stats.n} primary
              {stats.iqr && ` · IQR ${+stats.iqr.q1.toFixed(3)}–${+stats.iqr.q3.toFixed(3)}`}
            </span>
          </div>
        ) : (
          <div className="text-caption text-ink-soft">
            No median. {def?.name ?? field} is a design choice, not a measurement — a centre line
            over it would invent a consensus that no one holds.
          </div>
        )}

        {held.length > 0 && (
          <div className="text-caption text-ink-soft mt-1">
            {held.length} held, not in the median:{' '}
            {held.map((h, i) => (
              <span key={h.id}>
                {i > 0 && ', '}
                <a href={href(`/repo/a/${h.id}`)} className="font-num hover:text-accent">
                  {h.id}
                </a>{' '}
                ({HOLD_LABEL[h.hold!]})
              </span>
            ))}
          </div>
        )}

        {reconciled.length > 0 && (
          <div className="mt-2 border-l-2 border-signal-open pl-2 text-caption">
            <div className="font-medium text-signal-open">
              Closed by normalisation
            </div>
            {reconciled.map(([a, b]) => (
              <div key={`${a.id}|${b.id}`} className="text-ink-soft mt-0.5">
                <a href={href(`/repo/a/${a.id}`)} className="font-num hover:text-accent">{a.id}</a>{' '}
                and{' '}
                <a href={href(`/repo/a/${b.id}`)} className="font-num hover:text-accent">{b.id}</a>{' '}
                looked like a disagreement and were not — they were stated in different units.
                {a.conflictNote ? ` ${a.conflictNote}` : ''}
              </div>
            ))}
          </div>
        )}

        {contradicted && (
          <div className="mt-2 border-l-2 border-signal-warn pl-2 text-caption">
            <div className="text-signal-warn font-medium">Unresolved</div>
            {conflictPairs(accs).map(([a, b]) => (
              <div key={`${a.id}|${b.id}`} className="text-ink-soft mt-0.5">
                <a href={href(`/repo/a/${a.id}`)} className="font-num hover:text-accent">
                  {a.id}
                </a>{' '}
                and{' '}
                <a href={href(`/repo/a/${b.id}`)} className="font-num hover:text-accent">
                  {b.id}
                </a>{' '}
                disagree. Both are stored as stated. This system is not resolving them, and the
                median above is a summary of what is on record rather than a reconciliation of it.
                {a.conflictNote && <div className="mt-0.5">{a.conflictNote}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** One mark, for inline use in a table row. */
export function AccessionMark({ acc }: { acc: Accession }) {
  return (
    <span
      className={cx(demoTickClass(acc.provenance, acc.sourceType), acc.hold && 'held', 'inline-block w-2 h-4 align-middle')}
      title={demoTickTitle(acc.provenance, acc.sourceType, acc.hold)}
      aria-hidden
    />
  );
}
