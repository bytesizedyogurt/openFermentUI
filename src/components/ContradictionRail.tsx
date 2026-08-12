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
import { fmt, asNumber, convert } from '@/engine/units';
import { useStore } from '@/store';
import { cx } from './ui';

/**
 * Convert records into plottable marks, in the field's canonical unit.
 *
 * Lives beside the rail because three screens had grown their own copy and they
 * had already diverged — one silently dropped anything it could not convert,
 * another kept it at its published value and plotted it on the wrong axis.
 * A record that will not convert is not plotted, and an explained refusal is
 * exactly such a case.
 */
export function toRailMarks(records: ExtractionRecord[], unit: string): RailMark[] {
  const out: RailMark[] = [];
  for (const r of records) {
    const n = asNumber(r.value);
    if (n === null) continue;
    let v = n;
    if (unit && r.unit !== unit) {
      try {
        v = convert(n, r.unit, unit);
      } catch {
        continue;
      }
    }
    out.push({ record: r, value: v });
  }
  return out;
}

/** Marks for every field present in `records`, keyed by field. */
export function railMarksByField(
  records: ExtractionRecord[],
  unitOf: (field: ExtractionRecord['field']) => string,
): Map<ExtractionRecord['field'], RailMark[]> {
  const m = new Map<ExtractionRecord['field'], RailMark[]>();
  for (const r of records) {
    const list = m.get(r.field);
    if (list) continue;
    m.set(
      r.field,
      toRailMarks(records.filter((x) => x.field === r.field), unitOf(r.field)),
    );
  }
  return m;
}

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
  curated: 'bg-accent/85',
  unverified: 'bg-ink-soft',
  user: 'bg-signal-info',
  'industry-estimate': 'bg-ink-soft',
  demo: 'bg-signal-warn',
  unsourced: 'bg-signal-error',
};

/**
 * Inline rail height per density, mirroring --rail-h in the stylesheet.
 *
 * Read from the store rather than from getComputedStyle: a computed style is
 * sampled during render and nothing re-renders when the custom property
 * changes, so Shift+D switched every other measurement on the page and left
 * the rails — and therefore the row height they pin open — exactly as they
 * were. Subscribing means the same keystroke moves both.
 */
const RAIL_H = { comfortable: 34, dense: 24 } as const;

export function ContradictionRail({
  marks,
  aggregate,
  contradictions = [],
  height,
  highlightId,
  showScale = false,
  className,
}: {
  marks: RailMark[];
  aggregate: Aggregate | null;
  contradictions?: Contradiction[];
  /**
   * Explicit height in px, or omitted to follow --rail-h, which density
   * shrinks. A hardcoded inline height made dense mode make tables *taller*,
   * because the type shrank while the row stayed pinned open by the rail.
   */
  height?: number;
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
  // Above the early return: a hook that runs conditionally is not a hook.
  const density = useStore((s) => s.ui.density);

  // A single value is a value, not a spread. An empty frame around one mark
  // reads as "we looked and found agreement", which would be a lie.
  if (marks.length < 2) return null;

  const h = height ?? RAIL_H[density];

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
    return 3 + (1 - t) * (h - 6);
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
    <div className={cx('relative inline-flex items-start gap-1', className)}>
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
        style={{ width: h >= 120 ? 34 : 26, height: h }}
      >
        {aggregate && (
          <div
            className="absolute bg-ink rounded-[1px]"
            style={{ top: project(aggregate.median) - 1, height: 2, left: -3, right: -3 }}
            title={`median ${fmt(aggregate.median)} ${unit}`}
          />
        )}

        {/* The marks are not controls. §7 asks for click-a-mark-to-open, but a
            mark is 2px tall and 24px wide and they overlap wherever values
            cluster — a target that cannot reliably be hit is a dead control
            wearing a cursor. The rail is a picture; the Evidence list beneath it
            is the interactive surface, and it reaches every record including
            the ones plotted on top of each other. */}
        {marks.map(({ record, value }) => {
          const held = !isAggregatable(record);
          const why = aggregateExclusion(record);
          const on = record.id === highlightId;
          return (
            <span
              key={record.id}
              className={cx(
                'absolute left-1/2 -translate-x-1/2 rounded-[1px] block',
                PROV_BG[provenanceOf(record)] ?? 'bg-ink-soft',
                markClass(record),
                held && !on && 'opacity-70',
                on && 'ring-1 ring-ink ring-offset-0 z-10',
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
        <div className="relative shrink-0" style={{ height: h, width: 92 }} aria-hidden>
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
