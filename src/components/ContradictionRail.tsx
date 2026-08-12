// The contradiction rail (OF-FE-003 §7).
//
// One new visual element, and the only place in this design system to spend
// boldness. Every record for a parameter is a mark on a shared vertical axis,
// so agreement and disagreement are a shape rather than a number you have to
// read. A contested parameter and an agreed one must not look alike across a
// room — the test is legibility at three metres from a 1080p projection.
//
// Colour carries provenance and geometry carries evidence class, exactly as on
// the tick. Nothing here introduces a third encoding.
import type { Contradiction, ExtractionRecord } from '@/data/types';
import type { Aggregate } from '@/data/types';
import { provenanceOf, isAggregatable, aggregateExclusion, EXCLUSION_NOTE } from '@/engine/aggregation';
import { fmt } from '@/engine/units';
import { cx } from './ui';

export interface RailMark {
  record: ExtractionRecord;
  /** Value already converted to the aggregate's canonical unit. */
  value: number;
}

/** Mark geometry per evidence class — the same vocabulary as the tick. */
function markClass(r: ExtractionRecord): string {
  switch (r.evidenceClass) {
    case 'patent':
      return 'rail-mark-patent';
    case 'computed':
      return 'rail-mark-computed';
    case 'experiment':
      return 'rail-mark-experiment';
    case 'correction':
      return 'rail-mark-correction';
    default:
      return '';
  }
}

const PROV_BG: Record<string, string> = {
  gold: 'bg-gold',
  verified: 'bg-accent',
  curated: 'bg-accent/60',
  unverified: 'bg-ink-soft',
  user: 'bg-signal-info',
  'industry-estimate': 'bg-ink-soft',
  demo: 'bg-signal-warn',
  unsourced: 'bg-signal-error',
};

export function ContradictionRail({
  marks,
  aggregate,
  contradictions = [],
  height = 48,
  onPick,
  highlightId,
  showScale = false,
  className,
}: {
  marks: RailMark[];
  aggregate: Aggregate | null;
  contradictions?: Contradiction[];
  /** 48 inline, 160 on the parameter page, 28 inside a list row. */
  height?: number;
  onPick?: (recordId: string) => void;
  /** Ring one mark — "this record, among its peers". */
  highlightId?: string;
  /**
   * Endpoint and median labels, positioned by the same projection that places
   * the marks. Laying them out with justify-between instead floats the median
   * label at the vertical centre while the line sits wherever the data puts it,
   * which points the reader at the wrong number.
   */
  showScale?: boolean;
  className?: string;
}) {
  // A single value is a value, not a spread. An empty frame around one mark
  // reads as "we looked and found agreement", which would be a lie.
  if (marks.length < 2) return null;

  const values = marks.map((m) => m.value);
  const lo = Math.min(...values);
  const hi = Math.max(...values);

  // Log scale once the spread would otherwise collapse every low value onto the
  // floor. Chosen by the data, not by a prop, so two rails in one table are
  // never scaled differently without saying so.
  const logScale = lo > 0 && hi / lo > 100;
  const project = (v: number): number => {
    const t = logScale
      ? (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo) || 1)
      : (v - lo) / (hi - lo || 1);
    // 0 at the bottom of the frame, 1 at the top; inset 3px so a mark at an
    // extreme is not clipped by the frame.
    return 3 + (1 - t) * (height - 6);
  };

  const contradicted = contradictions.length > 0;
  const unit = aggregate?.unit ?? marks[0].record.unit;

  const summary = [
    `${marks.length} records`,
    aggregate ? `median ${fmt(aggregate.median)} ${unit}` : 'no median — too few comparable records',
    `range ${fmt(lo)} to ${fmt(hi)} ${unit}`,
    logScale ? 'plotted on a log scale' : null,
    contradicted
      ? `contradicted: ${contradictions.map((c) => c.statement).join('; ')}`
      : 'no contradiction recorded',
  ]
    .filter(Boolean)
    .join('. ');

  return (
    <div className={cx('inline-flex items-start gap-1', className)}>
      {/* The rail itself carries no accessible name — a scatter of absolutely
          positioned divs is noise to a screen reader. The sentence beside it
          says what the picture says, which is the same rule the DataTable ticks
          follow. */}
      {/* A narrow bordered box with hairlines in it reads as a scrollbar track,
          which is what the first cut of this looked like. A soft band with no
          hard edge, wide enough for a mark to be a mark, reads as a plot. */}
      <div
        aria-hidden
        className={cx(
          'relative shrink-0 rounded-[3px]',
          contradicted
            ? 'bg-signal-error/[0.09] ring-1 ring-signal-error/70'
            : 'bg-ink-soft/[0.09]',
        )}
        style={{ width: height >= 120 ? 34 : 26, height }}
      >
        {aggregate && (
          <div
            className="absolute bg-ink rounded-[1px]"
            style={{ top: project(aggregate.median) - 1, height: 2, left: -3, right: -3 }}
            title={`median ${fmt(aggregate.median)} ${unit}`}
          />
        )}

        {marks.map(({ record, value }) => {
          const held = !isAggregatable(record);
          const why = aggregateExclusion(record);
          const on = record.id === highlightId;
          // A plain span unless something can be done with a click. The rail
          // renders inside list rows that are themselves buttons, and nesting
          // one button in another is invalid HTML that browsers resolve by
          // dropping the inner element.
          const Mark = onPick ? 'button' : 'span';
          return (
            <Mark
              key={record.id}
              {...(onPick
                ? { type: 'button' as const, tabIndex: -1, onClick: () => onPick(record.id) }
                : {})}
              className={cx(
                'absolute left-1/2 -translate-x-1/2 rounded-[1px] block',
                PROV_BG[provenanceOf(record)] ?? 'bg-ink-soft',
                markClass(record),
                held && !on && 'opacity-45',
                on && 'ring-1 ring-ink ring-offset-0 z-10',
                onPick && 'cursor-pointer',
              )}
              style={{
                top: project(value) - (on ? 1.5 : 1),
                width: on ? '100%' : '72%',
                height: on ? 3 : 2,
              }}
              title={`${fmt(value)} ${unit}${why ? ` · ${EXCLUSION_NOTE[why]}` : ''}`}
            />
          );
        })}

        {contradicted && (
          // The fault glyph at the head is how a contradiction becomes visible
          // without anyone opening anything.
          <span
            className="absolute -top-[7px] left-1/2 -translate-x-1/2 text-signal-error leading-none"
            style={{ fontSize: 11 }}
          >
            ▲
          </span>
        )}
      </div>
      {showScale && (
        <div className="relative shrink-0" style={{ height, width: 92 }} aria-hidden>
          <span
            className="absolute left-0 text-caption text-ink-soft leading-none"
            style={{ top: project(hi) - 4 }}
          >
            {fmt(hi)}
          </span>
          {aggregate && (
            <span
              className="absolute left-0 text-caption text-ink leading-none whitespace-nowrap"
              style={{ top: project(aggregate.median) - 4 }}
            >
              median {fmt(aggregate.median)}
            </span>
          )}
          <span
            className="absolute left-0 text-caption text-ink-soft leading-none"
            style={{ top: project(lo) - 4 }}
          >
            {fmt(lo)}
          </span>
          {logScale && (
            // Above the high label, not below the low one — the low label sits
            // at the floor of the band and the two collided.
            <span
              className="absolute left-0 text-caption text-ink-soft/70 whitespace-nowrap"
              style={{ top: -14 }}
            >
              log scale
            </span>
          )}
        </div>
      )}
      <span className="sr-only">{summary}</span>
    </div>
  );
}
