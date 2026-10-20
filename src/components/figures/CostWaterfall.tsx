// What the price is made of (OF-BLD-019 §3.2). One row per line of a run's
// TEA breakdown, as the service read it from BioSTEAM's TEA object
// (`TeaBreakdown.lines`: main feedstock, other materials, utilities, other
// variable cost, fixed operating with labour, capital recovery, co-product
// credits), each per unit of the price's basis. The rows stack from zero: a
// bar starts where the line before it ended, and a credit runs back. The last
// row is the price the run solved, read from the run, never a sum the browser
// made; the lines sum to it by construction in the service. A line with no
// per-unit value draws no bar and says so. Bars take the stroke the run's
// provenance gives them, so a run that rests on an assumption reads as
// modeled.
import type { ComputedBasis, Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, type FigureTable } from './FigureFrame';

export interface WaterfallLine {
  key: string;
  label: string;
  /** Per unit of the price's basis, as the run holds it; null when the run has no basis flow to divide by. */
  perUnit: number | null;
  usdPerYear: number;
  /** Which attribute or method of the TEA object it was read from, in words. */
  reads: string;
}

export interface CostWaterfallProps {
  title: string;
  lines: WaterfallLine[];
  /** The price the run solved, on the lines' basis: the last row. Null when the run has none. */
  total: { label: string; value: number } | null;
  /** The per-unit basis, e.g. "USD per kg of PHA contained in dried cell mass". */
  unit: string;
  /** The annual amounts' unit, as the run's tables state it. */
  annualUnit: string;
  provenance: Provenance;
  basis?: ComputedBasis[];
  notes?: string[];
  csvName?: string;
}

/** One drawn bar: where it starts and ends on the price axis. A line with no per-unit value has none. */
export interface WaterfallBar {
  key: string;
  label: string;
  from: number;
  to: number;
  total: boolean;
}

/** The bars, in the lines' order, then the total from zero. Geometry only: no number is made here. */
export function bars(props: Pick<CostWaterfallProps, 'lines' | 'total'>): WaterfallBar[] {
  const out: WaterfallBar[] = [];
  let at = 0;
  for (const l of props.lines) {
    if (l.perUnit == null || !Number.isFinite(l.perUnit)) continue;
    out.push({ key: l.key, label: l.label, from: at, to: at + l.perUnit, total: false });
    at += l.perUnit;
  }
  if (props.total && Number.isFinite(props.total.value)) out.push({ key: 'total', label: props.total.label, from: 0, to: props.total.value, total: true });
  return out;
}

const money = (v: number) => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-US') : fmt(v, 2));

export function toTable(props: CostWaterfallProps): FigureTable {
  const rows: (string | number)[][] = props.lines.map((l) => [
    l.label,
    l.perUnit == null || !Number.isFinite(l.perUnit) ? '—' : fmt(l.perUnit, 4),
    money(l.usdPerYear),
    l.reads,
    props.provenance,
  ]);
  if (props.total) rows.push([props.total.label, fmt(props.total.value, 4), '', "the price the run solved", props.provenance]);
  return { headers: ['Line', `Per unit (${props.unit})`, `Per year (${props.annualUnit})`, 'Read from', 'Provenance'], rows };
}

const W = 640;
const ROW = 24;
const L = 200;
const R = 90;
const T = 8;

export function CostWaterfall(props: CostWaterfallProps) {
  const drawn = bars(props);
  const ends = drawn.flatMap((b) => [b.from, b.to]);
  const lo = Math.min(0, ...ends);
  const hi = Math.max(1e-9, ...ends);
  const x = (v: number) => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
  const color = markColor(props.provenance);
  const dash = DASH_ARRAY[ENCODING[props.provenance].line.dash];
  const rows = [...props.lines.map((l) => ({ line: l, bar: drawn.find((b) => !b.total && b.key === l.key) ?? null })), ...(props.total ? [{ line: null, bar: drawn.find((b) => b.total) ?? null }] : [])];
  const H = T * 2 + rows.length * ROW;
  return (
    <FigureFrame
      title={props.title}
      drawn={`One row per line of the run's TEA breakdown, per unit of the price's basis, each starting where the line before it ended; the last row is the price the run solved. Drawn as ${props.provenance} (${ENCODING[props.provenance].words}).`}
      axes={[props.unit]}
      table={toTable(props)}
      csvName={props.csvName ?? 'cost-breakdown'}
      basis={props.basis}
      notes={props.notes}
      empty={props.lines.length ? null : { what: 'this run kept no TEA breakdown.', where: 'A run of a flowsheet with a TEA keeps one from OF-BLD-019 on; run the scenario again.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="waterfall">
        <line x1={x(0)} x2={x(0)} y1={T} y2={H - T} stroke="currentColor" strokeOpacity={0.4} />
        {rows.map(({ line, bar }, i) => {
          const y0 = T + i * ROW;
          const label = line ? line.label : props.total!.label;
          return (
            <g key={line?.key ?? 'total'} data-testid={line ? 'waterfall-row' : 'waterfall-total'} data-line={line?.key ?? 'total'}>
              <text x={L - 6} y={y0 + ROW / 2 + 4} fontSize={11} textAnchor="end" fill="currentColor" fontWeight={line ? undefined : 600}>
                {label}
              </text>
              {bar ? (
                <rect
                  x={Math.min(x(bar.from), x(bar.to))}
                  y={y0 + 4}
                  width={Math.max(0.5, Math.abs(x(bar.to) - x(bar.from)))}
                  height={ROW - 8}
                  fill={color}
                  fillOpacity={bar.total ? 0.45 : 0.22}
                  stroke={color}
                  strokeDasharray={dash}
                />
              ) : (
                <text x={L + 4} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.65}>
                  no per-unit value: the run has no basis flow to divide by
                </text>
              )}
              {bar && (
                <text x={W - R + 6} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.8} className="font-num">
                  {fmt(line ? (line.perUnit as number) : props.total!.value, 4)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </FigureFrame>
  );
}
