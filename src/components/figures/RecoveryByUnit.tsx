// How much of the product each unit passes on (OF-BLD-019 §4.1).
//
// One row per unit of a run's train, in run order. A bar is the unit's
// recovery: the product leaving it on the way to the product stream over the
// product entering it, as the service read it from the run's stream table
// (pureos.train_of). A tick on the same row is the cumulative share still on
// the path after that unit. A unit no product enters, or one off the path,
// draws no bar and says why in words: a recovery is never divided out of a
// zero here. Bars take the stroke the run's provenance gives them, so a run
// that rests on an assumption reads as modeled.
import type { Provenance, TrainUnit } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, type FigureTable } from './FigureFrame';

export interface RecoveryByUnitProps {
  title: string;
  /** The component traced; null when the run names no product. */
  product: string | null;
  units: TrainUnit[];
  provenance: Provenance;
  /** The mass flow's unit, as the run's tables state it. */
  massUnit: string;
  notes?: string[];
  csvName?: string;
  /** Why the run kept no unit table, in the train's own words (its note). */
  why?: string | null;
  /** The unit picked on the page, outlined. */
  selected?: string | null;
  onSelect?: (unitId: string) => void;
}

const pct = (v: number | null) => (v == null || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(1)}%`);
const mass = (v: number | null) => (v == null || !Number.isFinite(v) ? '—' : fmt(v, 3));

/** Why a row draws no bar, or null when it draws one. */
export function noBar(u: TrainUnit): string | null {
  if (u.recovery != null && Number.isFinite(u.recovery)) return null;
  return u.note ?? (u.onPath ? 'no recovery is read for this unit' : "off the product's path");
}

export function toTable(props: RecoveryByUnitProps): FigureTable {
  const m = props.massUnit;
  return {
    headers: [
      'Unit',
      'Class',
      'On the path',
      `Product in (${m})`,
      `Product out (${m})`,
      `Onward (${m})`,
      `Lost (${m})`,
      'Recovery',
      'Cumulative',
      'Provenance',
      'Note',
    ],
    rows: props.units.map((u) => [
      u.id,
      u.unitClass,
      u.onPath ? 'yes' : 'no',
      mass(u.productIn),
      mass(u.productOut),
      mass(u.productOnward),
      mass(u.productLost),
      pct(u.recovery),
      pct(u.cumulative),
      props.provenance,
      u.note ?? '',
    ]),
  };
}

const W = 640;
const ROW = 24;
const L = 170;
const R = 150;
const T = 8;

/**
 * What the figure says instead of drawing, or null when it draws. A run that
 * kept no unit table names no product either; it says the table is missing
 * first, with the train's own words for why (a run kept before the tables, a
 * base case that could not run), never that its flowsheet prices nothing.
 */
export function emptyOf(props: RecoveryByUnitProps): { what: string; where: string } | null {
  if (props.units.length === 0)
    return {
      what: 'this run kept no unit table.',
      where: props.why || 'Run the scenario again in Proforma: every run keeps its tables.',
    };
  if (!props.product)
    return { what: 'this run names no product, so no recovery is read.', where: 'A run whose flowsheet prices a product stream names one; Proforma runs it.' };
  return null;
}

export function RecoveryByUnit(props: RecoveryByUnitProps) {
  const units = props.units;
  const top = Math.max(1, ...units.map((u) => (u.recovery != null && Number.isFinite(u.recovery) ? u.recovery : 0)));
  const H = T * 2 + units.length * ROW + 14;
  const x = (v: number) => L + (Math.max(0, v) / top) * (W - L - R);
  const color = markColor(props.provenance);
  const dash = DASH_ARRAY[ENCODING[props.provenance].line.dash];
  const empty = emptyOf(props);
  return (
    <FigureFrame
      title={props.title}
      drawn={`One row per unit in run order: the bar is the share of the ${props.product ?? 'product'} entering the unit that leaves it on the way to the product stream; the tick is the share still on the path after it.`}
      axes={['recovery (share of the product entering the unit)']}
      table={toTable(props)}
      csvName={props.csvName ?? 'recovery-by-unit'}
      notes={props.notes}
      empty={empty}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="recovery-by-unit">
        <line x1={x(1)} x2={x(1)} y1={T} y2={H - T - 12} stroke="currentColor" strokeOpacity={0.35} strokeDasharray="2 3" />
        <text x={x(1)} y={H - 4} fontSize={10} textAnchor="middle" fill="currentColor" opacity={0.6}>
          all of it
        </text>
        <line x1={x(0)} x2={x(0)} y1={T} y2={H - T - 12} stroke="currentColor" strokeOpacity={0.4} />
        {units.map((u, i) => {
          const y0 = T + i * ROW;
          const why = noBar(u);
          const picked = props.selected === u.id;
          return (
            <g
              key={u.id}
              data-testid="recovery-row"
              data-unit={u.id}
              data-bar={why ? 'none' : 'drawn'}
              role={props.onSelect ? 'button' : undefined}
              tabIndex={props.onSelect ? 0 : undefined}
              aria-pressed={props.onSelect ? picked : undefined}
              aria-label={props.onSelect ? `${u.id}, ${why ?? `recovery ${pct(u.recovery)}`}` : undefined}
              onClick={props.onSelect ? () => props.onSelect!(u.id) : undefined}
              onKeyDown={
                props.onSelect
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        props.onSelect!(u.id);
                      }
                    }
                  : undefined
              }
              style={props.onSelect ? { cursor: 'pointer' } : undefined}
            >
              {picked && <rect x={2} y={y0 + 1} width={W - 4} height={ROW - 2} fill="currentColor" fillOpacity={0.06} rx={3} />}
              <text x={L - 6} y={y0 + ROW / 2 + 4} fontSize={11} textAnchor="end" fill="currentColor" opacity={u.onPath ? 1 : 0.6}>
                {u.id} · {u.unitClass}
              </text>
              {why ? (
                <text x={L + 4} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.65}>
                  {why.length > 70 ? `${why.slice(0, 69)}…` : why}
                </text>
              ) : (
                <rect
                  x={x(0)}
                  y={y0 + 5}
                  width={Math.max(0.5, x(u.recovery!) - x(0))}
                  height={ROW - 10}
                  fill={color}
                  fillOpacity={0.3}
                  stroke={color}
                  strokeDasharray={dash}
                />
              )}
              {u.cumulative != null && Number.isFinite(u.cumulative) && (
                <line
                  data-testid="recovery-cumulative"
                  x1={x(u.cumulative)}
                  x2={x(u.cumulative)}
                  y1={y0 + 2}
                  y2={y0 + ROW - 2}
                  stroke={color}
                  strokeWidth={2}
                />
              )}
              <text x={W - R + 8} y={y0 + ROW / 2 + 4} fontSize={10} fill="currentColor" opacity={0.75} className="font-num">
                {why ? '' : pct(u.recovery)}
                {u.cumulative != null ? `${why ? '' : ' · '}on path ${pct(u.cumulative)}` : ''}
              </text>
            </g>
          );
        })}
      </svg>
    </FigureFrame>
  );
}
