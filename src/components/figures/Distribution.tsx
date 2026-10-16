// A price as a distribution (OF-BLD-014 §8.4). The histogram of every
// feasible sample, with the 5th, 25th, 50th, 75th and 95th percentiles as
// rules, all in the stroke the run's provenance gives it: a run that rests on
// an assumption is demo, and draws amber and dashed like every modeled thing.
// The infeasible samples are counted beside it, never drawn.
import type { ComputedBasis, HistogramBin, Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, lineStroke, type FigureTable } from './FigureFrame';

export interface DistributionProps {
  title: string;
  /** What the axis measures, with its unit. */
  quantity: string;
  unit: string;
  bins: HistogramBin[];
  quantiles: Record<string, number>;
  provenance: Provenance;
  /** Samples drawn, and those the flowsheet could not hold, by reason in words. */
  samples: number;
  infeasible: { reason: string; count: number }[];
  basis?: ComputedBasis[];
  notes?: string[];
  csvName?: string;
}

const ORDER = ['p5', 'p25', 'p50', 'p75', 'p95'];

export function toTable(props: DistributionProps): FigureTable {
  const rows: (string | number)[][] = props.bins.map((b) => ['bin', `${fmt(b.low)} to ${fmt(b.high)}`, b.count, props.provenance]);
  for (const q of ORDER) if (q in props.quantiles) rows.push([`percentile ${q.slice(1)}`, fmt(props.quantiles[q]), '', props.provenance]);
  return { headers: ['Mark', `Price (${props.unit})`, 'Samples', 'Provenance'], rows };
}

const W = 640;
const H = 200;
const L = 44;
const R = 16;
const T = 18;
const B = 30;

export function Distribution(props: DistributionProps) {
  const { bins, quantiles, provenance } = props;
  const feasible = bins.reduce((n, b) => n + b.count, 0);
  const lo = bins[0]?.low ?? 0;
  const hi = bins[bins.length - 1]?.high ?? 1;
  const top = Math.max(1, ...bins.map((b) => b.count));
  const x = (v: number) => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
  const y = (c: number) => H - B - (c / top) * (H - T - B);
  const color = markColor(provenance);
  const dash = DASH_ARRAY[ENCODING[provenance].line.dash];
  const notes = [
    `${feasible} of ${props.samples} samples ran; ${props.infeasible.map((i) => `${i.count} ${i.reason}`).join(', ') || 'none failed'}.`,
    ...(props.notes ?? []),
  ];
  return (
    <FigureFrame
      title={props.title}
      drawn={`Every feasible sample's price as a histogram, with percentile rules; drawn as ${provenance} (${ENCODING[provenance].words}).`}
      axes={[`${props.quantity} (${props.unit})`, 'samples']}
      table={toTable(props)}
      csvName={props.csvName ?? 'distribution'}
      basis={props.basis}
      notes={notes}
      empty={bins.length ? null : { what: 'no sample of this scenario ran.', where: 'Run the scenario in Proforma once every input has a source.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="distribution">
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        {bins.map((b) => (
          <rect
            key={b.low}
            x={x(b.low) + 0.5}
            y={y(b.count)}
            width={Math.max(0.5, x(b.high) - x(b.low) - 1)}
            height={H - B - y(b.count)}
            fill={color}
            fillOpacity={0.18}
            stroke={color}
            strokeDasharray={dash}
            data-testid="distribution-bin"
          />
        ))}
        {ORDER.filter((q) => q in quantiles).map((q) => (
          <g key={q} data-testid="distribution-quantile">
            <line x1={x(quantiles[q])} x2={x(quantiles[q])} y1={T} y2={H - B} {...lineStroke(provenance)} strokeWidth={q === 'p50' ? 2 : 1} />
            <text x={x(quantiles[q])} y={T - 4} fontSize={10} textAnchor="middle" fill="currentColor">
              {q === 'p50' ? 'median' : q.slice(1)}
            </text>
          </g>
        ))}
        <text x={L} y={H - 8} fontSize={10} fill="currentColor">
          {fmt(lo)}
        </text>
        <text x={W - R} y={H - 8} fontSize={10} textAnchor="end" fill="currentColor">
          {fmt(hi)} {props.unit}
        </text>
      </svg>
    </FigureFrame>
  );
}
