// Three prices, on a scale that can hold all three.
//
// The Proforma index used to show 145,307.3 · 1644.2 · 214.5 USD kg⁻¹ in three
// identical boxes at identical size. The most important fact available — that
// the algal route costs several hundred times what the incumbent does — was
// invisible, because three orders of magnitude in three equal boxes look like
// three numbers.
//
// A log axis is not a stylistic choice here. It is the only axis on which these
// three points are simultaneously visible, and the reason to draw them at all is
// to be able to see them at once.
//
// ── BESPOKE SVG, LIKE CapexCurve AND Flowsheet ────────────────────────────
//
// Recharts would draw the axis; it would not draw the thing this chart is for,
// which is the MULTIPLE against the incumbent stated on the mark. That is the
// sentence a reader takes away, and a chart that made them compute it from two
// tick labels would have failed at its one job.
import { fmt } from '@/engine/units';
import { href } from '@/router';
import { cx } from '@/components/ui';

export interface PricePoint {
  id: string;
  /** Short tag — the model id. */
  tag: string;
  label: string;
  msp: number;
  /** The one the others are measured against. */
  incumbent?: boolean;
}

const W = 940;
const H = 132;
const PAD = { l: 46, r: 52, t: 34, b: 30 };

/**
 * Decade ticks spanning the data.
 *
 * `ceil` on the top would spend a whole empty decade whenever the largest point
 * sits just above a power of ten — $145,307 would push the axis to $1,000,000
 * and squeeze every mark into the left two thirds. `round` keeps the axis
 * proportionate; the top tick may sit slightly below the largest point, which
 * is fine because the marks are drawn from the data and not from the ticks.
 */
function decades(lo: number, hi: number): number[] {
  const out: number[] = [];
  const top = Math.max(Math.floor(Math.log10(lo)) + 1, Math.round(Math.log10(hi)));
  for (let e = Math.floor(Math.log10(lo)); e <= top; e += 1) out.push(10 ** e);
  return out;
}

function money(v: number): string {
  if (v >= 1000) return `$${Math.round(v).toLocaleString('en-US')}`;
  return `$${fmt(v, 1)}`;
}

export function PriceScale({ points, className }: { points: PricePoint[]; className?: string }) {
  const priced = points.filter((p) => Number.isFinite(p.msp) && p.msp > 0);
  if (priced.length < 2) return null;

  const lo = Math.min(...priced.map((p) => p.msp));
  const hi = Math.max(...priced.map((p) => p.msp));
  const ticks = decades(lo, hi);
  const dLo = Math.min(ticks[0], lo);
  const dHi = Math.max(ticks[ticks.length - 1], hi);

  const x = (v: number) =>
    PAD.l + ((Math.log10(v) - Math.log10(dLo)) / (Math.log10(dHi) - Math.log10(dLo))) * (W - PAD.l - PAD.r);
  const axisY = H - PAD.b;

  const incumbent = priced.find((p) => p.incumbent) ?? priced.reduce((a, b) => (a.msp < b.msp ? a : b));

  // Labels alternate above and below the axis so two nearby points cannot
  // overprint each other.
  const ordered = [...priced].sort((a, b) => a.msp - b.msp);

  return (
    <div className={cx('overflow-x-auto', className)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto select-none"
        style={{ maxWidth: '100%', minWidth: 560 }}
        role="img"
        aria-label={
          `Minimum selling price on a logarithmic scale. ` +
          ordered
            .map(
              (p) =>
                `${p.label}, ${money(p.msp)} per kilogram` +
                (p.id === incumbent.id
                  ? ', the incumbent'
                  : `, ${(p.msp / incumbent.msp).toFixed(p.msp / incumbent.msp > 20 ? 0 : 1)} times the incumbent`),
            )
            .join('. ')
        }
      >
        {/* decade gridlines */}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={x(t)}
              x2={x(t)}
              y1={PAD.t - 12}
              y2={axisY}
              className="stroke-line"
              strokeWidth={1}
            />
            <text
              x={x(t)}
              y={axisY + 14}
              // The first and last decade sit on the viewBox edge, so a centred
              // label overhangs and is clipped. They anchor inward instead.
              textAnchor={t === dLo ? 'start' : t === dHi ? 'end' : 'middle'}
              className="fill-ink-soft font-num"
              fontSize={10}
            >
              {money(t)}
            </text>
          </g>
        ))}

        {/* the axis itself */}
        <line x1={PAD.l} x2={W - PAD.r} y1={axisY} y2={axisY} className="stroke-ink-soft" strokeWidth={1} />

        {/* the incumbent's reference line, drawn first so marks sit over it */}
        <line
          x1={x(incumbent.msp)}
          x2={x(incumbent.msp)}
          y1={PAD.t - 18}
          y2={axisY}
          className="stroke-accent"
          strokeWidth={1}
          strokeDasharray="3 3"
        />

        {ordered.map((p, i) => {
          const px = x(p.msp);
          const isIncumbent = p.id === incumbent.id;
          const multiple = p.msp / incumbent.msp;
          const above = i % 2 === 0;
          const labelY = above ? PAD.t - 2 : axisY - 30;
          const anchor = px > W - 150 ? 'end' : px < 150 ? 'start' : 'middle';
          return (
            <g key={p.id}>
              {/* the mark: a 3px stem, the same width the whole app uses for a
                  tick, so it reads as part of this product's vocabulary */}
              <rect
                x={px - 1.5}
                y={axisY - 20}
                width={3}
                height={20}
                rx={1}
                className={isIncumbent ? 'fill-accent' : 'fill-ink'}
              />
              <text
                x={px}
                y={labelY}
                textAnchor={anchor}
                className="fill-ink font-num"
                fontSize={15}
                fontWeight={500}
              >
                {money(p.msp)}
              </text>
              <text
                x={px}
                y={labelY + 13}
                textAnchor={anchor}
                className="fill-ink-soft"
                fontSize={10}
              >
                {p.tag}
                {isIncumbent
                  ? ' · the incumbent'
                  : ` · ${multiple >= 20 ? Math.round(multiple) : multiple.toFixed(1)}× it`}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** The same three points as text, for anyone the chart does not reach. */
export function PriceScaleTable({ points }: { points: PricePoint[] }) {
  const priced = points.filter((p) => Number.isFinite(p.msp) && p.msp > 0);
  const incumbent = priced.find((p) => p.incumbent) ?? priced.reduce((a, b) => (a.msp < b.msp ? a : b));
  return (
    <dl className="ledger text-caption mt-2">
      {[...priced]
        .sort((a, b) => a.msp - b.msp)
        .map((p) => (
          <div key={p.id} className="ledger-row">
            <dt className="text-ink-soft">
              <a href={href(`/proforma/price/${p.id}`)} className="hover:text-accent">
                <span className="font-num">{p.tag}</span> {p.label}
              </a>
            </dt>
            <dd className="font-num">
              {money(p.msp)}
              <span className="text-ink-soft ml-2">
                {p.id === incumbent.id
                  ? '—'
                  : `${p.msp / incumbent.msp >= 20 ? Math.round(p.msp / incumbent.msp) : (p.msp / incumbent.msp).toFixed(1)}×`}
              </span>
            </dd>
          </div>
        ))}
    </dl>
  );
}
