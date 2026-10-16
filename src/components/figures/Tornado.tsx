// What moves a price (OF-BLD-014 §8.4). One row per input, sorted by how far
// it moves the price, each bar drawn from zero. A row names where its input
// came from (records, a person's assumption, a reference model), so a long
// bar resting on an assumption reads as the question to ask next. The bars
// take the stroke of the result's provenance: demo for an authored surface
// or a run that rests on an assumption.
import type { Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, type FigureTable } from './FigureFrame';

export interface TornadoRow {
  label: string;
  /** One value per series, signed, drawn from zero. */
  values: number[];
  /** Where the input came from, printed beside its bar. */
  tag?: string;
}

export interface TornadoProps {
  title: string;
  drawn: string;
  /** The series' names, e.g. ['−20%', '+20%'] or ['Spearman ρ']. */
  series: string[];
  unit: string;
  rows: TornadoRow[];
  provenance: Provenance;
  notes?: string[];
  csvName?: string;
}

const magnitude = (r: TornadoRow) => Math.max(...r.values.map(Math.abs));

export function sorted(rows: TornadoRow[]): TornadoRow[] {
  return [...rows].sort((a, b) => magnitude(b) - magnitude(a));
}

export function toTable(props: TornadoProps): FigureTable {
  return {
    headers: ['Input', ...props.series.map((s) => `${s} (${props.unit})`), 'Source'],
    rows: sorted(props.rows).map((r) => [r.label, ...r.values.map((v) => fmt(v, 3)), r.tag ?? '']),
  };
}

const W = 640;
const ROW = 22;
const L = 190;
const R = 110;
const T = 8;

export function Tornado(props: TornadoProps) {
  const rows = sorted(props.rows);
  const span = Math.max(1e-9, ...rows.map(magnitude));
  const H = T * 2 + rows.length * ROW;
  const mid = L + (W - L - R) / 2;
  const x = (v: number) => mid + (v / span) * ((W - L - R) / 2);
  const color = markColor(props.provenance);
  const dash = DASH_ARRAY[ENCODING[props.provenance].line.dash];
  const n = props.series.length;
  return (
    <FigureFrame
      title={props.title}
      drawn={props.drawn}
      axes={[props.unit]}
      table={toTable(props)}
      csvName={props.csvName ?? 'tornado'}
      notes={props.notes}
      empty={rows.length ? null : { what: 'nothing varies in this run.', where: 'An input with a range moves the price; a fixed input draws no bar.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="tornado">
        <line x1={mid} x2={mid} y1={T} y2={H - T} stroke="currentColor" strokeOpacity={0.4} />
        {rows.map((r, i) => {
          const y0 = T + i * ROW;
          return (
            <g key={r.label} data-testid="tornado-row">
              <text x={L - 6} y={y0 + ROW / 2 + 4} fontSize={11} textAnchor="end" fill="currentColor">
                {r.label}
              </text>
              {r.values.map((v, j) => {
                const h = (ROW - 6) / n;
                return (
                  <rect
                    key={j}
                    x={Math.min(x(0), x(v))}
                    y={y0 + 3 + j * h}
                    width={Math.max(0.5, Math.abs(x(v) - x(0)))}
                    height={h - 1}
                    fill={color}
                    fillOpacity={j === 0 ? 0.35 : 0.15}
                    stroke={color}
                    strokeDasharray={dash}
                  />
                );
              })}
              {r.tag && (
                <text x={W - R + 6} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.7}>
                  {r.tag}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </FigureFrame>
  );
}
