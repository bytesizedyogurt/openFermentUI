// The ceiling across mixtures of two sugars at equal total carbon
// (OF-BLD-014 §6.3, §6.4): a computed line, so dotted, with its basis. It
// answers how a hydrolysate's sugar ratio bounds the yield.
import type { ComputedBasis } from '@/data/types';
import { fmt } from '@/engine/units';
import { FigureFrame, lineStroke, type FigureTable } from './FigureFrame';

export interface MixPoint {
  /** The share of the carbon fed as the first sugar, 0 to 1. */
  share: number;
  value: number;
}

export interface MixLineProps {
  title: string;
  points: MixPoint[];
  a: string;
  b: string;
  unit: string;
  quantity: string;
  model: string;
  basis?: ComputedBasis;
  csvName?: string;
}

export function toTable(props: MixLineProps): FigureTable {
  return {
    headers: [`Share of carbon as ${props.a}`, `Share as ${props.b}`, props.quantity, 'Unit', 'Provenance'],
    rows: props.points.map((p) => [fmt(p.share, 2), fmt(1 - p.share, 2), fmt(p.value), props.unit, 'computed']),
  };
}

const W = 640;
const H = 220;
const L = 56;
const R = 20;
const T = 14;
const B = 40;

export function MixLine(props: MixLineProps) {
  const pts = [...props.points].sort((x, y) => y.share - x.share);
  const vals = pts.map((p) => p.value);
  const lo = vals.length ? Math.min(...vals) : 0;
  const hi = vals.length ? Math.max(...vals) : 1;
  // A spread under a millionth of the value is the solver's rounding, not a
  // change across the mixtures: drawn flat, with one label, so float noise is
  // never stretched across the whole axis.
  const flat = hi - lo <= Math.abs(hi) * 1e-6;
  const pad = (flat ? Math.abs(hi) || 1 : hi - lo) * 0.15;
  const x = (share: number) => L + (1 - share) * (W - L - R);
  const y = (v: number) => (flat ? (T + H - B) / 2 : H - B - ((v - (lo - pad)) / (hi + pad - (lo - pad))) * (H - T - B));
  return (
    <FigureFrame
      title={props.title}
      drawn={`The most product ${props.model} allows at ${pts.length} mixtures of ${props.a} and ${props.b}, at the same total carbon.`}
      axes={[`share of carbon fed as ${props.b}`, `${props.quantity} (${props.unit})`]}
      table={toTable(props)}
      csvName={props.csvName ?? 'sugar-mix'}
      basis={props.basis ? [props.basis] : undefined}
      empty={pts.length ? null : { what: 'no mixture computed for this model.', where: 'Mixtures are computed in geneOS → Model.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="mix-line">
        <polyline points={pts.map((p) => `${x(p.share)},${y(p.value)}`).join(' ')} fill="none" {...lineStroke('computed')} />
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        <line x1={L} x2={L} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        {[0, 0.5, 1].map((t) => (
          <text key={t} x={x(1 - t)} y={H - B + 14} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
            {t === 0 ? `all ${props.a}` : t === 1 ? `all ${props.b}` : 'half and half'}
          </text>
        ))}
        {(flat ? [hi] : [lo, hi]).map((v) => (
          <text key={v} x={L - 6} y={y(v) + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.7}>
            {fmt(v, 3)}
          </text>
        ))}
      </svg>
    </FigureFrame>
  );
}
