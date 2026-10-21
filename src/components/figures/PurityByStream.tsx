// How pure is the product in each stream of the train? (OF-BLD-020 §5.3, D14.)
//
// One row per stream of a train run, in the order the run's stream table
// lists them (inlet first, then each unit's outlets in run order): a bar is
// the product's share of the stream's mass, a computed value read from the
// run's table by the service (`TrainPurity`, pureos.purity_of), drawn with
// the run's provenance, so a train resting on a person's assumption reads as
// modeled. The stream the train delivers its product in is the one the
// service names (`productStream`), outlined and said in words; the figure
// never picks it. A stream that carries nothing has no share: it draws no bar
// and says so, and nothing is divided here. The largest other components are
// the service's too, named beside each row.
import type { ComputedBasis, Provenance, StreamPurity } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, type FigureTable } from './FigureFrame';

export interface PurityByStreamProps {
  title: string;
  /** The chemical the run traced (the library's name for the train's product). */
  product: string;
  /** The stream the train delivers its product in, as the service names it. */
  productStream: string | null;
  /** Every stream's share, in the order the service gives them. */
  streams: StreamPurity[];
  /** Where each stream comes from and goes, as the run's table says (by stream id). */
  routes?: Record<string, { source: string | null; sink: string | null }>;
  /** The run's provenance, which every bar takes. */
  provenance: Provenance;
  /** The mass flow's unit, as the run's tables state it. */
  massUnit?: string;
  basis?: ComputedBasis;
  csvName?: string;
  notes?: string[];
}

const pct = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(2)}%`);
const mass = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '—' : fmt(v, 4));

/** Why a stream draws no bar, or null when it draws one. */
export function noBar(s: StreamPurity): string | null {
  return s.productFraction == null || !Number.isFinite(s.productFraction) ? 'carries nothing, so it has no share' : null;
}

/** A stream's route in words, from the run's table. */
function routeOf(props: PurityByStreamProps, id: string): [string, string] {
  const r = props.routes?.[id];
  return [r?.source ?? 'the inlet', r?.sink ?? 'leaves the train'];
}

export function toTable(props: PurityByStreamProps): FigureTable {
  const m = props.massUnit ?? 'kg/hr';
  return {
    headers: ['Stream', 'From', 'To', `Mass flow (${m})`, `${props.product} share of the mass`, 'Largest other components', 'Product stream', 'Provenance'],
    rows: props.streams.map((s) => {
      const [from, to] = routeOf(props, s.stream);
      return [
        s.stream,
        from,
        to,
        mass(s.massFlow),
        pct(s.productFraction),
        s.impurities.map((i) => `${i.chemical} ${pct(i.massFraction)}`).join('; '),
        s.stream === props.productStream ? 'yes' : 'no',
        props.provenance,
      ];
    }),
  };
}

/** What the figure says instead of drawing, or null when it draws. */
export function emptyOf(props: PurityByStreamProps): { what: string; where: string } | null {
  if (props.streams.length === 0)
    return { what: 'this run kept no stream table.', where: 'Run the train in pureOS → Builder; its run keeps every stream and its share.' };
  return null;
}

const W = 640;
const ROW = 26;
const L = 190;
const R = 210;
const T = 8;

export function PurityByStream(props: PurityByStreamProps) {
  const H = T * 2 + props.streams.length * ROW + 14;
  const x = (v: number) => L + Math.max(0, Math.min(1, v)) * (W - L - R);
  const color = markColor(props.provenance);
  const dash = DASH_ARRAY[ENCODING[props.provenance].line.dash];
  return (
    <FigureFrame
      title={props.title}
      drawn={`One row per stream of the train, in the order the run's table lists them: the bar is the ${props.product} share of the stream's mass, a computed value read from the run's table and drawn as ${props.provenance} (${ENCODING[props.provenance].words}); the product stream the service names is outlined.`}
      axes={[`${props.product} share of the stream's mass (0 to the whole)`]}
      table={toTable(props)}
      csvName={props.csvName ?? 'purity-by-stream'}
      basis={props.basis ? [props.basis] : undefined}
      empty={emptyOf(props)}
      notes={props.notes}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="purity-by-stream">
        <line x1={x(1)} x2={x(1)} y1={T} y2={H - T - 12} stroke="currentColor" strokeOpacity={0.35} strokeDasharray="2 3" />
        <text x={x(1)} y={H - 4} fontSize={10} textAnchor="middle" fill="currentColor" opacity={0.6}>
          all of it
        </text>
        <line x1={x(0)} x2={x(0)} y1={T} y2={H - T - 12} stroke="currentColor" strokeOpacity={0.4} />
        {props.streams.map((s, i) => {
          const y0 = T + i * ROW;
          const why = noBar(s);
          const isProduct = s.stream === props.productStream;
          const [from, to] = routeOf(props, s.stream);
          return (
            <g key={s.stream} data-testid="purity-row" data-stream={s.stream} data-product={isProduct ? 'true' : 'false'} data-bar={why ? 'none' : 'drawn'}>
              {isProduct && <rect x={2} y={y0 + 1} width={W - 4} height={ROW - 2} fill="none" stroke={color} strokeOpacity={0.7} rx={3} data-testid="purity-product" />}
              <text x={L - 6} y={y0 + ROW / 2 + 4} fontSize={11} textAnchor="end" fill="currentColor">
                {s.stream}
                <tspan opacity={0.6}>{` · ${from} → ${to}`}</tspan>
              </text>
              {why ? (
                <text x={L + 4} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.65}>
                  {why}
                </text>
              ) : (
                <rect
                  data-testid="purity-bar"
                  x={x(0)}
                  y={y0 + 6}
                  width={Math.max(0.5, x(s.productFraction!) - x(0))}
                  height={ROW - 12}
                  fill={color}
                  fillOpacity={0.3}
                  stroke={color}
                  strokeDasharray={dash}
                />
              )}
              <text x={W - R + 8} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.8} className="font-num">
                {why ? '' : pct(s.productFraction)}
                {isProduct ? ' · product stream' : ''}
                {s.impurities.length > 0 ? ` · ${s.impurities[0].chemical} ${pct(s.impurities[0].massFraction)}` : ''}
              </text>
            </g>
          );
        })}
      </svg>
    </FigureFrame>
  );
}
