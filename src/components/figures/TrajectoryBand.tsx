// A run over time (OF-BLD-014 §7.4): measured readings as filled points (a
// deposition's readings are measurements), the fitted curve as a dotted line
// (computed), and a forecast as a band for readings with its median. One
// panel per series. The table twin lists every reading with its residual
// from the fit, and every forecast time.
import type { Band, ComputedBasis, Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, Mark, lineStroke, type FigureTable } from './FigureFrame';

export interface TrajectorySeries {
  role: string;
  label: string;
  unit: string;
  readings: { t: number; value: number; residual?: number | null }[];
  /** The fitted curve, sampled. */
  fitted?: { t: number; value: number }[];
}

export interface TrajectoryBandProps {
  title: string;
  series: TrajectorySeries[];
  /** The forecast, when there is one: times and a band per role. */
  forecast?: { times: number[]; bands: Band[]; provenance?: Provenance } | null;
  /** The readings' provenance: measured for a deposition, demo for the sample run. */
  readingProvenance?: Provenance;
  basis?: ComputedBasis[];
  notes?: string[];
  csvName?: string;
}

export function toTable(props: TrajectoryBandProps): FigureTable {
  const rows: (string | number)[][] = [];
  for (const s of props.series) {
    for (const r of s.readings) rows.push([s.label, 'reading', fmt(r.t), fmt(r.value), s.unit, r.residual == null ? '' : fmt(r.residual)]);
  }
  for (const b of props.forecast?.bands ?? []) {
    const label = props.series.find((s) => s.role === b.role)?.label ?? b.role;
    props.forecast!.times.forEach((t, i) =>
      rows.push([label, `forecast ${fmt(b.low[i])} to ${fmt(b.high[i])}`, fmt(t), fmt(b.median[i]), b.unit, '']),
    );
  }
  return { headers: ['Series', 'Kind', 'Hours', 'Value', 'Unit', 'Residual from the fit'], rows };
}

const W = 640;
const H = 182;
const L = 56;
const R = 16;
const T = 24;
const B = 28;

function Panel({ s, band, times, tmax, readingProvenance, bandProvenance }: { s: TrajectorySeries; band?: Band; times?: number[]; tmax: number; readingProvenance: Provenance; bandProvenance: Provenance }) {
  const vals = [...s.readings.map((r) => r.value), ...(s.fitted ?? []).map((f) => f.value), ...(band ? [...band.low, ...band.high] : [])];
  const lo = Math.min(0, ...vals);
  const hi = Math.max(...vals, lo + 1e-9);
  const x = (t: number) => L + (t / (tmax || 1)) * (W - L - R);
  const y = (v: number) => H - B - ((v - lo) / (hi - lo || 1)) * (H - T - B);
  const color = markColor(bandProvenance);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={`${s.label} over time`} data-testid="trajectory-panel">
      <text x={L} y={12} fontSize={11} fill="currentColor">
        {s.label} ({s.unit})
      </text>
      {band && times && (
        <g data-testid="trajectory-forecast">
          <polygon
            points={[...times.map((t, i) => `${x(t)},${y(band.high[i])}`), ...[...times].reverse().map((t, j) => `${x(t)},${y(band.low[times.length - 1 - j])}`)].join(' ')}
            fill={color}
            fillOpacity={0.12}
            stroke="none"
          />
          <polyline points={times.map((t, i) => `${x(t)},${y(band.median[i])}`).join(' ')} fill="none" stroke={color} strokeWidth={1.5} strokeDasharray={DASH_ARRAY[ENCODING[bandProvenance].line.dash]} />
        </g>
      )}
      {s.fitted && s.fitted.length > 1 && (
        <polyline points={s.fitted.map((f) => `${x(f.t)},${y(f.value)}`).join(' ')} fill="none" {...lineStroke('computed')} data-testid="trajectory-fit" />
      )}
      {s.readings.map((r) => (
        <g key={`${r.t}-${r.value}`}>
          <title>{`${fmt(r.t)} h · ${fmt(r.value)} ${s.unit}${r.residual == null ? '' : ` · residual ${fmt(r.residual)}`}`}</title>
          <Mark p={readingProvenance} x={x(r.t)} y={y(r.value)} size={3.5} />
        </g>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
      <line x1={L} x2={L} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <text x={x(f * tmax)} y={H - B + 13} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
            {fmt(f * tmax, 1)} h
          </text>
          <text x={L - 5} y={y(lo + f * (hi - lo)) + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.7}>
            {fmt(Math.abs(lo + f * (hi - lo)) < 0.005 ? 0 : lo + f * (hi - lo), 2)}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function TrajectoryBand(props: TrajectoryBandProps) {
  const times = props.forecast?.times;
  const tmax = Math.max(1e-9, ...props.series.flatMap((s) => s.readings.map((r) => r.t)), ...(times ?? []));
  const readings = props.series.reduce((n, s) => n + s.readings.length, 0);
  return (
    <FigureFrame
      title={props.title}
      drawn={`${readings} readings as points${props.series.some((s) => s.fitted) ? ', the fit as a dotted line' : ''}${props.forecast ? ', the forecast as a band for readings (5th to 95th percentile) with its median' : ''}.`}
      axes={['hours into the run', ...props.series.map((s) => `${s.label} (${s.unit})`)]}
      table={toTable(props)}
      csvName={props.csvName ?? 'trajectory'}
      basis={props.basis}
      notes={props.notes}
      empty={readings === 0 && !props.forecast ? { what: 'no reading with a time.', where: 'Readings arrive through a deposition: type them in run mode, or attach them on the deposition page.' } : null}
    >
      <div className="space-y-1" data-testid="trajectory-band">
        {props.series.map((s) => (
          <Panel
            key={s.role + s.label}
            s={s}
            band={props.forecast?.bands.find((b) => b.role === s.role)}
            times={times}
            tmax={tmax}
            readingProvenance={props.readingProvenance ?? 'measured'}
            bandProvenance={props.forecast?.provenance ?? 'computed'}
          />
        ))}
      </div>
    </FigureFrame>
  );
}
