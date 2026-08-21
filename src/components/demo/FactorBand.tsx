// The one-dimensional factor band (OF-DEMO-002 §3.4, §4.4).
//
// A range on one factor, with what has been explored, what has been excluded,
// and — the point of the whole screen — what has not been looked at.
//
// THE UNEXPLORED REGION IS THE SUBJECT, not the leftover. It renders as bare
// graph-paper ground rather than as absence, which is the one job the ground
// does here: an empty stretch has to read as "nobody has been here" and not as
// "the chart failed to draw". Everything else on the band is quieter than it.
//
// A single-source exclusion gets a warning triangle rather than a confidence
// interval, because a confidence interval computed from one record is a
// decoration (OF-DEMO-003 §6).
import { useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';

import type { FactorMapEntry } from '@/data/demo/types';
import { FIELD_BY_ID } from '@/data/demo/core';
import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { demoTickClass, demoTickTitle, SOURCE_LABEL } from './DemoTick';

const H = 34;

export function FactorBand({
  factor,
  className,
  /** Extra points to mark inside the band — e.g. a de-rated design point. */
  marks,
  onSelect,
}: {
  factor: FactorMapEntry;
  className?: string;
  marks?: { at: number; label: string; accessionId?: string }[];
  onSelect?: () => void;
}) {
  const def = FIELD_BY_ID[factor.field];
  const { low, high } = factor.domain;
  const span = Math.max(1e-9, high - low);
  const x = (v: number) => ((v - low) / span) * 100;
  const w = (a: number, b: number) => Math.max(0.4, ((b - a) / span) * 100);

  /**
   * The stretches nobody has visited. Computed by subtracting explored and
   * excluded from the domain rather than authored, because an authored gap is
   * a claim about absence and a computed one is the absence itself.
   */
  const unexplored = useMemo(() => {
    const covered = [
      ...factor.explored.map((e) => [e.low, e.high] as const),
      ...factor.excluded.map((e) => [e.low, e.high] as const),
    ].sort((a, b) => a[0] - b[0]);
    const gaps: [number, number][] = [];
    let cursor = low;
    for (const [a, b] of covered) {
      if (a > cursor) gaps.push([cursor, a]);
      cursor = Math.max(cursor, b);
    }
    if (cursor < high) gaps.push([cursor, high]);
    // Sub-pixel slivers are rounding, not findings.
    return gaps.filter(([a, b]) => (b - a) / span > 0.01);
  }, [factor, low, high, span]);

  return (
    <div className={cx('min-w-0', className)}>
      <div className="flex items-baseline justify-between gap-2 mb-1">
        <div className="text-caption text-ink-soft">
          {def?.name ?? factor.field}{' '}
          <span className="font-num">{factor.unit}</span>
        </div>
        {onSelect && (
          <button className="text-caption text-accent hover:underline" onClick={onSelect}>
            open factor
          </button>
        )}
      </div>

      <div
        className="relative border border-line of-grid"
        style={{ height: H }}
        role="img"
        aria-label={`${def?.name ?? factor.field}: ${unexplored.length} unexplored region(s)`}
      >
        {/* Recommended, first so everything else sits over it. */}
        <div
          className="absolute inset-y-0"
          style={{
            left: `${x(factor.recommended.low)}%`,
            width: `${w(factor.recommended.low, factor.recommended.high)}%`,
            background: 'rgb(var(--accent-wash))',
          }}
          title={`Recommended ${factor.recommended.low}–${factor.recommended.high} ${factor.unit}`}
        />

        {/* Explored — a quiet underline, not a fill. Being visited is not being
            recommended, and the two must not look alike. */}
        {factor.explored.map((e, i) => (
          <div
            key={`e${i}`}
            className="absolute bottom-0 h-[2px]"
            style={{ left: `${x(e.low)}%`, width: `${w(e.low, e.high)}%`, background: 'rgb(var(--ink-soft))', opacity: 0.55 }}
            title={`Explored ${e.low}–${e.high} ${factor.unit} — ${e.accessionIds.length} Accession(s)`}
          />
        ))}

        {/* Excluded — hatched at 45°. */}
        {factor.excluded.map((e, i) => (
          <div
            key={`x${i}`}
            className="absolute inset-y-0"
            style={{
              left: `${x(e.low)}%`,
              width: `${w(e.low, e.high)}%`,
              backgroundImage:
                'repeating-linear-gradient(45deg, rgb(var(--signal-warn)) 0 1px, transparent 1px 5px)',
              opacity: 0.85,
            }}
            title={`Excluded ${e.low}–${e.high} ${factor.unit} — ${e.reason}`}
          />
        ))}

        {/* An FTO recitation is a different kind of boundary from a physical
            exclusion: the space works, someone has claimed it. Outlined rather
            than filled, so it reads as a fence and not as a wall. */}
        {factor.ftoFlag && (
          <div
            className="absolute inset-y-0 border-x-2 border-dashed border-signal-closed"
            style={{
              left: `${x(factor.ftoFlag.recitedRange.low)}%`,
              width: `${w(factor.ftoFlag.recitedRange.low, factor.ftoFlag.recitedRange.high)}%`,
            }}
            title={`Recited by ${factor.ftoFlag.patentFamilyId} in ${factor.ftoFlag.jurisdiction}`}
          />
        )}

        {/* Extra marks last. */}
        {(marks ?? []).map((m, i) => (
          <div
            key={`m${i}`}
            className="absolute inset-y-0 w-[2px]"
            style={{ left: `${x(m.at)}%`, background: 'rgb(var(--ink))' }}
            title={m.label}
          />
        ))}
      </div>

      <div className="flex justify-between text-caption text-ink-soft font-num mt-0.5">
        <span>{low}</span>
        <span>{high}</span>
      </div>

      {/* The reading. Unexplored comes FIRST, because it is the finding. */}
      {unexplored.length > 0 && (
        <div className="text-caption mt-1">
          <span className="text-ink">Unexplored:</span>{' '}
          <span className="font-num text-ink-soft">
            {unexplored.map(([a, b]) => `${+a.toFixed(2)}–${+b.toFixed(2)}`).join(', ')} {factor.unit}
          </span>
          <span className="text-ink-soft"> — no Accession in this pool speaks to it.</span>
        </div>
      )}

      {factor.excluded.map((e, i) => {
        const accs = e.accessionIds.map((id) => ACCESSION_BY_ID[id]).filter(Boolean);
        // The seed states it and the count derives it. They must agree — if a
        // curator marks an exclusion single-source while citing three records,
        // one of the two is wrong and `check:demo-seed` says which.
        const single = e.singleSource;
        return (
          <div key={`r${i}`} className="text-caption text-ink-soft mt-1 flex gap-1.5">
            {single && (
              <AlertTriangle
                className="w-3 h-3 mt-0.5 shrink-0 text-signal-warn"
                aria-label="single-source exclusion"
              />
            )}
            <span>
              <span className="font-num">
                {e.low}–{e.high}
              </span>{' '}
              excluded: {e.reason}
              {single && ' — on one record. No confidence interval is shown, because one computed from a single record would be a decoration.'}
              {accs.length > 0 && (
                <>
                  {' '}
                  {accs.map((acc) => (
                    <a
                      key={acc.id}
                      href={href(`/repo/a/${acc.id}`)}
                      className={cx(demoTickClass(acc.provenance, acc.sourceType), acc.hold && 'held', 'pl-1.5 mr-1 font-num hover:text-accent')}
                      title={demoTickTitle(acc.provenance, acc.sourceType, acc.hold)}
                    >
                      {acc.id}
                      <span className="text-ink-soft"> ({SOURCE_LABEL[acc.sourceType]})</span>
                    </a>
                  ))}
                </>
              )}
            </span>
          </div>
        );
      })}

      {factor.ftoFlag && (
        <div className="text-caption mt-1 text-signal-closed">
          <span className="font-num">
            {factor.ftoFlag.recitedRange.low}–{factor.ftoFlag.recitedRange.high}
          </span>{' '}
          is recited by{' '}
          <a href={href(`/parchment/families#${factor.ftoFlag.patentFamilyId}`)} className="font-num hover:underline">
            {factor.ftoFlag.patentFamilyId}
          </a>{' '}
          in {factor.ftoFlag.jurisdiction}. The space works; someone has claimed it.
        </div>
      )}
    </div>
  );
}
