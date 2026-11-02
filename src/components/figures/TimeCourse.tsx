// A simulated run over time (OF-BLD-020 §3.3, D14).
//
// A simulation is computed, never measured (D1), so each state it integrates
// (cells, substrate, product, the volume where it varies) draws as a computed
// curve, its line taking the simulation's own provenance: dotted when it is
// `computed`, short amber dashes when a person's value made it `assumed`. When a
// deposition is drawn against it, its readings are filled points (a
// measurement is the only filled mark, E.8 rule 3); a forecast is a band. The
// oxygen uptake rate rides on the cells' panel against a second axis, on the
// right, in its own unit. The yield panel sets Yp/s and the yield the run
// achieved beside each geneOS ceiling as a rule, in the ceiling's own
// provenance: a point above a ceiling is ringed, never moved (D11).
//
// The figure draws what it is given and computes nothing: every number in it
// and in its table is the artifact's own.
import type { ComputedBasis, Provenance } from '@/data/types';
import { fmt } from '@/engine/units';
import { DASH_ARRAY, ENCODING, markColor } from './encoding';
import { FigureFrame, Mark, lineStroke, type FigureTable } from './FigureFrame';

export interface TimeCourseState {
  /** The state's letter: X, S, P, V, N, Q. */
  key: string;
  label: string;
  unit: string;
  values: number[];
}

export interface TimeCourseProps {
  title: string;
  /** Hours, shared by every state. */
  t: number[];
  states: TimeCourseState[];
  /** The curves' provenance: the simulation's (or the fit's), computed or assumed. */
  provenance: Provenance;
  /** The oxygen uptake rate on the cells' panel's second axis; omitted when the culture takes up none. */
  our?: { unit: string; values: number[] } | null;
  /** A deposition's readings drawn against the curves, by state key: filled points. */
  readings?: { key: string; points: { t: number; value: number }[]; provenance?: Provenance }[];
  /** A forecast band, by state key. */
  bands?: { key: string; t: number[]; low: number[]; high: number[]; provenance: Provenance }[];
  /**
   * Yp/s and the yield achieved beside each ceiling, as a rule. Whether a
   * point is above a ceiling is the service's word (`above`), never a
   * comparison made here.
   */
  yields?: {
    unit: string;
    points: { label: string; value: number | null; above?: boolean }[];
    ceilings: { label: string; value: number; provenance: Provenance; above: boolean }[];
  } | null;
  basis?: ComputedBasis[];
  notes?: string[];
  csvName?: string;
}

/** One row per mark the figure draws: each curve's every point, OUR's, each reading, each band point, each ceiling rule and each yield point. */
export function toTable(props: TimeCourseProps): FigureTable {
  const rows: (string | number)[][] = [];
  for (const s of props.states) {
    s.values.forEach((v, i) => rows.push([s.label, 'computed curve', fmt(props.t[i]), fmt(v), s.unit, props.provenance]));
  }
  if (props.our) props.our.values.forEach((v, i) => rows.push(['Oxygen uptake rate (OUR)', 'computed curve, second axis', fmt(props.t[i]), fmt(v), props.our!.unit, props.provenance]));
  for (const r of props.readings ?? []) {
    const label = props.states.find((s) => s.key === r.key)?.label ?? r.key;
    const unit = props.states.find((s) => s.key === r.key)?.unit ?? '';
    for (const p of r.points) rows.push([label, 'reading', fmt(p.t), fmt(p.value), unit, r.provenance ?? 'measured']);
  }
  for (const b of props.bands ?? []) {
    const label = props.states.find((s) => s.key === b.key)?.label ?? b.key;
    const unit = props.states.find((s) => s.key === b.key)?.unit ?? '';
    b.t.forEach((t, i) => rows.push([label, `band ${fmt(b.low[i])} to ${fmt(b.high[i])}`, fmt(t), '', unit, b.provenance]));
  }
  if (props.yields) {
    for (const c of props.yields.ceilings) rows.push([c.label, 'ceiling, a rule', '', fmt(c.value), props.yields.unit, c.provenance]);
    for (const p of props.yields.points) {
      if (p.value == null) continue;
      const above = p.above ? props.yields.ceilings.filter((c) => c.above).map((c) => c.label) : [];
      rows.push([p.label, p.above ? `above ${above.join(', ') || 'a ceiling'}: flagged, not clamped` : 'yield', '', fmt(p.value), props.yields.unit, props.provenance]);
    }
  }
  return { headers: ['Series', 'Mark', 'Hours', 'Value', 'Unit', 'Provenance'], rows };
}

const W = 640;
const H = 170;
const L = 56;
const R = 56;
const T = 24;
const B = 28;

function ticks(lo: number, hi: number) {
  return [0, 0.5, 1].map((f) => lo + f * (hi - lo));
}

function StatePanel({
  state,
  t,
  tmax,
  provenance,
  readings,
  band,
  our,
}: {
  state: TimeCourseState;
  t: number[];
  tmax: number;
  provenance: Provenance;
  readings?: { points: { t: number; value: number }[]; provenance?: Provenance };
  band?: { t: number[]; low: number[]; high: number[]; provenance: Provenance };
  our?: { unit: string; values: number[] } | null;
}) {
  const vals = [...state.values, ...(readings?.points.map((p) => p.value) ?? []), ...(band ? [...band.low, ...band.high] : [])];
  const lo = Math.min(0, ...vals);
  const hi = Math.max(...vals, lo + 1e-9);
  const x = (h: number) => L + (h / (tmax || 1)) * (W - L - R);
  const y = (v: number) => H - B - ((v - lo) / (hi - lo || 1)) * (H - T - B);
  const ourHi = our ? Math.max(...our.values, 1e-9) : 1;
  const y2 = (v: number) => H - B - (v / ourHi) * (H - T - B);
  const ourStyle = ENCODING[provenance].line;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={`${state.label} over time`} data-testid="timecourse-panel" data-state={state.key}>
      <text x={L} y={12} fontSize={11} fill="currentColor">
        {state.label} ({state.unit}){our ? `; oxygen uptake rate (${our.unit}) on the right axis` : ''}
      </text>
      {band && (
        <polygon
          data-testid="timecourse-band"
          points={[...band.t.map((h, i) => `${x(h)},${y(band.high[i])}`), ...[...band.t].reverse().map((h, j) => `${x(h)},${y(band.low[band.t.length - 1 - j])}`)].join(' ')}
          fill={markColor(band.provenance)}
          fillOpacity={0.12}
          stroke="none"
        />
      )}
      <polyline points={state.values.map((v, i) => `${x(t[i])},${y(v)}`).join(' ')} fill="none" {...lineStroke(provenance)} data-testid="timecourse-curve" data-provenance={provenance} />
      {our && (
        <polyline
          points={our.values.map((v, i) => `${x(t[i])},${y2(v)}`).join(' ')}
          fill="none"
          stroke={markColor(provenance)}
          strokeOpacity={0.55}
          strokeWidth={1}
          strokeDasharray={DASH_ARRAY[ourStyle.dash]}
          data-testid="timecourse-our"
        />
      )}
      {readings?.points.map((p) => (
        <g key={`${p.t}-${p.value}`}>
          <title>{`${fmt(p.t)} h · ${fmt(p.value)} ${state.unit}`}</title>
          <Mark p={readings.provenance ?? 'measured'} x={x(p.t)} y={y(p.value)} size={3.5} />
        </g>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
      <line x1={L} x2={L} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.4} />
      {our && <line x1={W - R} x2={W - R} y1={T} y2={H - B} stroke="currentColor" strokeOpacity={0.25} />}
      {ticks(0, tmax).map((h) => (
        <text key={`t${h}`} x={x(h)} y={H - B + 13} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
          {fmt(h, 1)} h
        </text>
      ))}
      {ticks(lo, hi).map((v) => (
        <text key={`v${v}`} x={L - 5} y={y(v) + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.7}>
          {fmt(Math.abs(v) < 0.005 ? 0 : v, 2)}
        </text>
      ))}
      {our &&
        ticks(0, ourHi).map((v) => (
          <text key={`o${v}`} x={W - R + 5} y={y2(v) + 3} textAnchor="start" fontSize={10} fill="currentColor" opacity={0.6}>
            {fmt(v, 2)}
          </text>
        ))}
    </svg>
  );
}

function YieldPanel({ yields, provenance }: { yields: NonNullable<TimeCourseProps['yields']>; provenance: Provenance }) {
  const vals = [...yields.ceilings.map((c) => c.value), ...yields.points.map((p) => p.value ?? 0)];
  const hi = Math.max(...vals, 1e-9) * 1.15;
  const x = (v: number) => L + (v / hi) * (W - L - R);
  const rowH = 20;
  const shown = yields.points.filter((p) => p.value != null);
  const h = T + rowH * Math.max(1, shown.length) + B;
  return (
    <svg viewBox={`0 0 ${W} ${h}`} className="w-full h-auto" role="img" aria-label="Yield beside the ceiling" data-testid="timecourse-yield">
      <text x={L} y={12} fontSize={11} fill="currentColor">
        Yield ({yields.unit}): each ceiling is a rule, never a bound
      </text>
      {yields.ceilings.map((c) => (
        <g key={c.label} data-testid="timecourse-ceiling" data-provenance={c.provenance}>
          <line x1={x(c.value)} x2={x(c.value)} y1={T - 4} y2={h - B} {...lineStroke(c.provenance)} />
          <text x={x(c.value) + 3} y={T + 2} fontSize={10} fill="currentColor" opacity={0.75}>
            {c.label}
          </text>
        </g>
      ))}
      {shown.map((p, i) => {
        const above = p.above === true;
        const cy = T + rowH * i + rowH / 2;
        return (
          <g key={p.label} data-testid="timecourse-yield-point" data-above={above ? 'true' : 'false'}>
            <title>{`${p.label}: ${fmt(p.value!)} ${yields.unit}${above ? ', above a ceiling: flagged, not clamped' : ''}`}</title>
            <Mark p={provenance} x={x(p.value!)} y={cy} size={4} flagged={above} />
            <text x={L - 5} y={cy + 3} textAnchor="end" fontSize={10} fill="currentColor" opacity={0.8}>
              {p.label}
            </text>
          </g>
        );
      })}
      <line x1={L} x2={W - R} y1={h - B} y2={h - B} stroke="currentColor" strokeOpacity={0.4} />
      {ticks(0, hi).map((v) => (
        <text key={v} x={x(v)} y={h - B + 13} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
          {fmt(v, 2)}
        </text>
      ))}
    </svg>
  );
}

export function TimeCourse(props: TimeCourseProps) {
  const tmax = Math.max(1e-9, ...props.t, ...(props.readings ?? []).flatMap((r) => r.points.map((p) => p.t)));
  const first = props.states[0]?.key;
  const empty = props.t.length === 0 || props.states.length === 0;
  return (
    <FigureFrame
      title={props.title}
      drawn={`${props.states.length} computed curve${props.states.length === 1 ? '' : 's'} (${ENCODING[props.provenance].words.split('; ')[1] ?? ''}, the simulation's ${props.provenance})${props.our ? ', the oxygen uptake rate on the right axis' : ''}${props.readings?.length ? ', the run’s readings as filled points' : ''}${props.bands?.length ? ', a band' : ''}${props.yields ? ', and the yield beside each ceiling as a rule' : ''}. A simulation is computed, never a measurement.`}
      axes={['hours into the run', ...props.states.map((s) => `${s.label} (${s.unit})`), ...(props.our ? [`oxygen uptake rate (${props.our.unit})`] : []), ...(props.yields ? [`yield (${props.yields.unit})`] : [])]}
      table={toTable(props)}
      csvName={props.csvName ?? 'time-course'}
      basis={props.basis}
      notes={props.notes}
      empty={empty ? { what: 'no time course.', where: 'fermOS → Simulate integrates one from a family, its parameters and their sources.' } : null}
    >
      <div className="space-y-1" data-testid="timecourse">
        {props.states.map((s) => (
          <StatePanel
            key={s.key}
            state={s}
            t={props.t}
            tmax={tmax}
            provenance={props.provenance}
            readings={props.readings?.find((r) => r.key === s.key)}
            band={props.bands?.find((b) => b.key === s.key)}
            our={s.key === first ? props.our : null}
          />
        ))}
        {props.yields && (props.yields.ceilings.length > 0 || props.yields.points.some((p) => p.value != null)) && (
          <YieldPanel yields={props.yields} provenance={props.provenance} />
        )}
      </div>
    </FigureFrame>
  );
}
