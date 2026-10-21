// Does the vessel transfer the oxygen the culture takes up? (OF-BLD-020
// §4.2, D7, D14.) The simulated uptake over the batch (OUR) is a computed
// curve, drawn as a line; what the vessel BioSTEAM designed transfers while it
// reacts (OTR = kLa · ΔC) is a computed limit, drawn as a rule; the hours the
// uptake rises above the rule are shaded. Both are read from one
// `fermos.vessel` artifact, so both take its provenance, and the figure
// computes nothing: the hours that fall short are the service's (`short`),
// never found here.
import type { ComputedBasis, Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { ENCODING } from './encoding';
import { FigureFrame, lineStroke, type FigureTable } from './FigureFrame';

export interface OxygenBalanceProps {
  title: string;
  /** Hours, and the simulated uptake at each, in `unit` (VesselOxygen.t, .our). */
  t: number[];
  our: number[];
  /** What the vessel transfers while it reacts, in `unit` (VesselOxygen.otr). */
  otr: number;
  unit: string;
  /** [[from, to], …] hours the uptake rises above the transfer, as the service found them. */
  short: number[][];
  /** The design's provenance, which both marks take. */
  provenance: Provenance;
  /** The kLa correlation, by BioSTEAM's name, and whether BioSTEAM designed any aeration. */
  method?: string | null;
  aerated?: boolean;
  basis?: ComputedBasis;
  csvName?: string;
  notes?: string[];
}

/** Whether hour `t` lies inside one of the short intervals the service named. */
export const isShort = (t: number, short: number[][]) => short.some(([a, b]) => t >= a && t <= b);

export function toTable(props: OxygenBalanceProps): FigureTable {
  return {
    headers: ['Hour', 'Uptake, OUR (simulated)', 'Transfer, OTR (the vessel)', 'Unit', 'Short', 'Provenance'],
    rows: props.t.map((t, i) => [fmt(t), fmt(props.our[i]), fmt(props.otr), props.unit, isShort(t, props.short) ? 'yes' : 'no', props.provenance]),
  };
}

/** What the figure has nothing to draw for, or null. */
export function emptyOf(props: OxygenBalanceProps): { what: string; where: string } | null {
  if (props.t.length < 2 || props.our.length !== props.t.length)
    return {
      what: 'the simulation kept no oxygen uptake over its hours.',
      where: 'An aerobic simulation (Yx/o set) keeps one; fermOS → Simulate makes it, and Design reads it here.',
    };
  return null;
}

const W = 640;
const H = 260;
const L = 56;
const R = 120;
const T = 14;
const B = 40;

export function OxygenBalance(props: OxygenBalanceProps) {
  const empty = emptyOf(props);
  const tmax = Math.max(1e-9, ...props.t);
  const ymax = Math.max(1e-9, props.otr, ...props.our);
  const x = (v: number) => L + (v / tmax) * (W - L - R);
  const y = (v: number) => H - B - (v / (ymax * 1.1)) * (H - T - B);
  const stroke = lineStroke(props.provenance);
  const curve = props.t.map((t, i) => `${x(t)},${y(props.our[i])}`).join(' ');
  const shortWords = props.short.length
    ? `the uptake rises above the transfer from ${props.short.map(([a, b]) => `${fmt(a, 3)} to ${fmt(b, 3)} h`).join(', ')}, shaded`
    : 'the uptake stays at or under the transfer at every hour';
  return (
    <FigureFrame
      title={props.title}
      drawn={`The simulated oxygen uptake over the batch as a computed curve, and what the vessel transfers while it reacts as a computed rule${props.method ? ` (kLa by ${props.method})` : ''}; ${shortWords}. Both are read from the design and drawn as ${props.provenance} (${ENCODING[props.provenance].words}).`}
      axes={['hours into the batch (h)', `oxygen (${props.unit})`]}
      table={toTable(props)}
      csvName={props.csvName ?? 'oxygen-balance'}
      basis={props.basis ? [props.basis] : undefined}
      empty={empty}
      notes={props.notes}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="oxygen-balance">
        {props.short.map(([a, b]) => (
          <rect
            key={`${a}-${b}`}
            x={x(a)}
            y={T}
            width={Math.max(1, x(b) - x(a))}
            height={H - T - B}
            fill="rgb(var(--signal-warn))"
            fillOpacity={0.14}
            data-testid="oxygen-short"
          />
        ))}
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        <line x1={L} x2={L} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
        <line x1={L} x2={W - R} y1={y(props.otr)} y2={y(props.otr)} {...stroke} data-testid="oxygen-otr" />
        <text x={W - R + 6} y={y(props.otr) + 3} fontSize={10} fill="currentColor">
          OTR, the vessel
        </text>
        <polyline points={curve} fill="none" {...stroke} data-testid="oxygen-our" />
        {props.t.length > 0 && (
          <text x={W - R + 6} y={y(props.our[props.our.length - 1]) + 3} fontSize={10} fill="currentColor" opacity={0.8}>
            OUR, simulated
          </text>
        )}
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <text x={x(f * tmax)} y={H - B + 14} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
              {fmt(f * tmax, 2)}
            </text>
            <text x={L - 6} y={y(f * ymax) + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.7}>
              {fmt(f * ymax, 2)}
            </text>
          </g>
        ))}
        <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="currentColor">
          hours into the batch (h)
        </text>
        <text transform={`translate(14 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize={11} fill="currentColor">
          oxygen ({props.unit})
        </text>
      </svg>
    </FigureFrame>
  );
}
