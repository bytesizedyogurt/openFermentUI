// A production envelope (OF-BLD-014 §6.1): growth rate on one axis, the most
// product the network allows at that growth on the other, drawn as a computed
// curve over the shaded region a cell could occupy. Computed, so dotted
// (E.8 rule 2), and the basis travels with it.
import type { ComputedBasis } from '@/data/types';
import { fmt } from '@/engine/units';
import { FigureFrame, lineStroke, type FigureTable } from './FigureFrame';

export interface FrontierPoint {
  growth: number;
  product: number;
}

export interface FrontierProps {
  title: string;
  points: FrontierPoint[];
  growthUnit: string;
  productUnit: string;
  /** What the product axis measures. */
  productLabel: string;
  model: string;
  basis?: ComputedBasis;
  csvName?: string;
}

export function toTable(props: FrontierProps): FigureTable {
  return {
    headers: ['Growth rate', 'Unit', 'Most product', 'Unit', 'Provenance'],
    rows: props.points.map((p) => [fmt(p.growth), props.growthUnit, fmt(p.product), props.productUnit, 'computed']),
  };
}

const W = 640;
const H = 260;
const L = 56;
const R = 20;
const T = 14;
const B = 40;

export function Frontier(props: FrontierProps) {
  const pts = [...props.points].sort((a, b) => a.growth - b.growth);
  const gx = Math.max(1e-9, ...pts.map((p) => p.growth));
  const py = Math.max(1e-9, ...pts.map((p) => p.product));
  const x = (v: number) => L + (v / (gx * 1.05)) * (W - L - R);
  const y = (v: number) => H - B - (v / (py * 1.1)) * (H - T - B);
  const curve = pts.map((p) => `${x(p.growth)},${y(p.product)}`).join(' ');
  const region = pts.length ? `${x(pts[0].growth)},${y(0)} ${curve} ${x(pts[pts.length - 1].growth)},${y(0)}` : '';
  return (
    <FigureFrame
      title={props.title}
      drawn={`The most product ${props.model} allows at each growth rate: ${pts.length} computed points, the region beneath them shaded.`}
      axes={[`growth rate (${props.growthUnit})`, `${props.productLabel} (${props.productUnit})`]}
      table={toTable(props)}
      csvName={props.csvName ?? 'frontier'}
      basis={props.basis ? [props.basis] : undefined}
      empty={pts.length ? null : { what: 'no envelope computed for this model and feed.', where: 'Envelopes are computed in geneOS → Model.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="frontier">
        <polygon points={region} fill="currentColor" fillOpacity={0.07} />
        <polyline points={curve} fill="none" {...lineStroke('computed')} />
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        <line x1={L} x2={L} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <text x={x(t * gx)} y={H - B + 14} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
              {fmt(t * gx, 2)}
            </text>
            <text x={L - 6} y={y(t * py) + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.7}>
              {fmt(t * py, 2)}
            </text>
          </g>
        ))}
        <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="currentColor">
          growth rate ({props.growthUnit})
        </text>
        <text transform={`translate(14 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize={11} fill="currentColor">
          {props.productLabel} ({props.productUnit})
        </text>
      </svg>
    </FigureFrame>
  );
}
