// What was predicted beside what was measured (OF-BLD-014 §9.3). One row per
// prediction, each on its own axis, because a ledger mixes units. The
// prediction is outlined: an interval as an outlined bar, a point as an
// outlined point with its ten percent band, a bound as a rule with its
// allowed side shaded. The observed value, once reconciled, is a filled
// diamond: a run's reading is a measurement. Held and missed differ by a mark
// beside the row (a tick, a cross) and by the word.
import type { Prediction } from '@/data/types';
import { fmt } from '@/engine/units';
import { CONFIRM_BAND_PCT, kindOf } from '@/engine/reconcile';
import { FigureFrame, Mark, type FigureTable } from './FigureFrame';

export interface IntervalLedgerRow {
  key: string;
  label: string;
  prediction: Prediction;
  lockedAt: string | null;
  observed: { value: number; unit: string } | null;
  held: boolean | null;
}

export interface IntervalLedgerProps {
  title: string;
  rows: IntervalLedgerRow[];
  csvName?: string;
  empty?: { what: string; where: string } | null;
}

function predictedWords(p: Prediction): string {
  const k = kindOf(p);
  if (k === 'interval' && p.interval) return `${fmt(p.interval.low)} to ${fmt(p.interval.high)}`;
  if (k === 'bound') return `at most ${fmt(p.value)}`;
  return `${fmt(p.value)} within ${CONFIRM_BAND_PCT} %`;
}

export function toTable(props: IntervalLedgerProps): FigureTable {
  return {
    headers: ['Prediction', 'Kind', 'Predicted', 'Unit', 'Locked', 'Observed', 'Verdict'],
    rows: props.rows.map((r) => [
      r.label,
      kindOf(r.prediction),
      predictedWords(r.prediction),
      r.prediction.unit,
      r.lockedAt ? r.lockedAt.slice(0, 10) : 'not locked',
      r.observed ? fmt(r.observed.value) : '',
      r.held === null ? 'untested' : r.held ? 'held' : 'missed',
    ]),
  };
}

const W = 640;
const ROW = 46;
const L = 200;
const R = 90;

function extent(r: IntervalLedgerRow): [number, number] {
  const p = r.prediction;
  const k = kindOf(p);
  const vals = [p.value, ...(r.observed ? [r.observed.value] : [])];
  if (k === 'interval' && p.interval) vals.push(p.interval.low, p.interval.high);
  if (k === 'point') vals.push(p.value * (1 - CONFIRM_BAND_PCT / 100), p.value * (1 + CONFIRM_BAND_PCT / 100));
  let lo = Math.min(...vals, 0);
  let hi = Math.max(...vals);
  if (k === 'bound') hi = Math.max(hi, p.value * 1.25);
  if (hi === lo) hi = lo + 1;
  const pad = (hi - lo) * 0.06;
  return [lo - (lo === 0 ? 0 : pad), hi + pad];
}

export function IntervalLedger(props: IntervalLedgerProps) {
  const H = props.rows.length * ROW + 8;
  return (
    <FigureFrame
      title={props.title}
      drawn="Each prediction as locked, outlined: an interval as a bar, a point with its ten percent band, a bound as a rule with its allowed side shaded. A reconciled reading is a filled diamond; a tick or a cross says held or missed."
      axes={['each row on its own axis, in its prediction’s unit']}
      table={toTable(props)}
      csvName={props.csvName ?? 'prediction-ledger'}
      empty={props.rows.length ? null : props.empty ?? { what: 'no prediction to draw.', where: 'A runbook’s predictions appear here once they are written.' }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="interval-ledger">
        {props.rows.map((r, i) => {
          const [lo, hi] = extent(r);
          const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R);
          const y = 4 + i * ROW + ROW / 2;
          const p = r.prediction;
          const k = kindOf(p);
          return (
            <g key={r.key} data-testid="ledger-row" data-verdict={r.held === null ? 'untested' : r.held ? 'held' : 'missed'}>
              <text x={L - 8} y={y - 4} fontSize={11} textAnchor="end" fill="currentColor">
                {r.label}
              </text>
              <text x={L - 8} y={y + 10} fontSize={9} textAnchor="end" fill="currentColor" opacity={0.65}>
                {p.unit}
                {r.lockedAt ? ` · locked ${r.lockedAt.slice(0, 10)}` : ' · not locked'}
              </text>
              <line x1={L} x2={W - R} y1={y + 12} y2={y + 12} stroke="currentColor" strokeOpacity={0.2} />
              {k === 'interval' && p.interval && (
                <rect x={x(p.interval.low)} y={y - 6} width={Math.max(1, x(p.interval.high) - x(p.interval.low))} height={12}
                  fill="none" stroke="currentColor" strokeWidth={1.5} data-testid="ledger-interval" />
              )}
              {k === 'point' && (
                <g data-testid="ledger-point">
                  <line x1={x(p.value * (1 - CONFIRM_BAND_PCT / 100))} x2={x(p.value * (1 + CONFIRM_BAND_PCT / 100))} y1={y} y2={y}
                    stroke="currentColor" strokeWidth={1} />
                  <circle cx={x(p.value)} cy={y} r={5} fill="none" stroke="currentColor" strokeWidth={1.5} />
                </g>
              )}
              {k === 'bound' && (
                <g data-testid="ledger-bound">
                  <rect x={x(lo)} y={y - 8} width={Math.max(0, x(p.value) - x(lo))} height={16} fill="currentColor" fillOpacity={0.08} />
                  <line x1={x(p.value)} x2={x(p.value)} y1={y - 10} y2={y + 10} stroke="currentColor" strokeWidth={1.5} />
                </g>
              )}
              {r.observed && <Mark p="measured" x={x(r.observed.value)} y={y} size={5} />}
              <text x={W - R + 10} y={y + 4} fontSize={11} fill="currentColor">
                {r.held === null ? 'untested' : r.held ? '✓ held' : '✗ missed'}
              </text>
            </g>
          );
        })}
      </svg>
    </FigureFrame>
  );
}
