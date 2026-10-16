// The records of one field as points along a value axis (OF-BLD-014 §6.1).
//
// One row per group (organism or paper). Each point's mark is its
// provenance's (`ENCODING`); a record held out of statistics is drawn faint
// and says why (`aggregateExclusion`); the median of the records that may be
// aggregated is a tick on the axis. Computed limits are rule lines. A record
// whose unit does not convert to the axis unit is not drawn, and the count of
// those is stated.
import type { ComputedBasis, ExtractionRecord, Provenance } from '@/data/types';
import { aggregateExclusion, provenanceOf } from '@/store';
import { asNumber, convert, fmt } from '@/engine/units';
import { FigureFrame, Mark, lineStroke, type FigureTable } from './FigureFrame';

export interface StripRule {
  value: number;
  /** What made the line, e.g. the model's name. */
  label: string;
  provenance?: Provenance;
}

export interface EvidenceStripProps {
  title: string;
  drawn?: string;
  records: ExtractionRecord[];
  /** The axis unit; every record is converted to it or left out. */
  unit: string;
  /** What the axis measures, e.g. "PHB yield on substrate". */
  quantity: string;
  groupBy: 'organism' | 'paper';
  rules?: StripRule[];
  /** Ring every point above the lowest rule (a ceiling's figure). */
  flagAbove?: boolean;
  basis?: ComputedBasis[];
  csvName?: string;
  notes?: string[];
  empty?: { what: string; where: string };
}

export interface StripPoint {
  record: ExtractionRecord;
  group: string;
  value: number;
  provenance: Provenance;
  heldOut: string | null;
  above: string | null;
}

const EXCLUSION_WORDS: Record<string, string> = {
  rejected: 'rejected by a reviewer',
  'industry-estimate': 'an industry estimate, never evidence',
  computed: 'computed from values already counted',
  'not-primary': 'cites another paper’s measurement',
};

function groupOf(r: ExtractionRecord, by: EvidenceStripProps['groupBy']): string {
  if (by === 'paper') return r.paperId;
  const carbon = r.carbonSource ? ` · ${r.carbonSource}` : '';
  return `${r.organism ?? 'organism not stated'}${carbon}`;
}

/** The marks the strip draws, in order; what the chart and its table share. */
export function stripPoints(props: EvidenceStripProps): { points: StripPoint[]; notDrawn: number } {
  const lowest = props.rules && props.rules.length ? Math.min(...props.rules.map((r) => r.value)) : null;
  const points: StripPoint[] = [];
  let notDrawn = 0;
  for (const r of props.records) {
    const raw = asNumber(r.value);
    let value: number | null = null;
    if (raw !== null) {
      try {
        value = convert(raw, r.unit, props.unit);
      } catch {
        value = null;
      }
    }
    if (value === null || !Number.isFinite(value)) {
      notDrawn += 1;
      continue;
    }
    const excl = aggregateExclusion(r);
    const prov = provenanceOf(r);
    const overRule = props.flagAbove && props.rules ? props.rules.filter((rule) => value! > rule.value) : [];
    points.push({
      record: r,
      group: groupOf(r, props.groupBy),
      value,
      provenance: prov,
      // A modeled value is never evidence (E.8), so it stays out of the median.
      heldOut: excl ? EXCLUSION_WORDS[excl] ?? excl : prov === 'demo' ? 'modeled, never evidence' : null,
      above: lowest !== null && overRule.length ? `above ${overRule.map((x) => x.label).join(', ')}` : null,
    });
  }
  return { points, notDrawn };
}

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function toTable(props: EvidenceStripProps): FigureTable {
  const { points } = stripPoints(props);
  const rows: (string | number)[][] = points.map((p) => [
    p.group,
    p.record.id,
    fmt(p.value),
    props.unit,
    p.provenance,
    p.heldOut ?? '',
    p.above ?? '',
  ]);
  for (const rule of props.rules ?? []) rows.push([`limit: ${rule.label}`, '', fmt(rule.value), props.unit, rule.provenance ?? 'computed', '', '']);
  return { headers: ['Group', 'Record', 'Value', 'Unit', 'Provenance', 'Held out of statistics', 'Above a limit'], rows };
}

const W = 640;
const LEFT = 190;
const RIGHT = 24;
const ROW = 26;
// Room above the first row for each rule's label, stacked so none collide.
const LABEL = 14;

export function EvidenceStrip(props: EvidenceStripProps) {
  const { points, notDrawn } = stripPoints(props);
  const rules = props.rules ?? [];
  const TOP = 18 + rules.length * LABEL;
  const groups = [...new Set(points.map((p) => p.group))];
  const values = [...points.map((p) => p.value), ...rules.map((r) => r.value)];
  const max = values.length ? Math.max(...values) : 1;
  const lo = Math.min(0, ...values);
  const hi = max === lo ? lo + 1 : max + (max - lo) * 0.08;
  const x = (v: number) => LEFT + ((v - lo) / (hi - lo)) * (W - LEFT - RIGHT);
  const H = TOP + Math.max(1, groups.length) * ROW + 34;
  // An empty strip keeps one row, where it says what would fill it.
  const axisY = TOP + Math.max(1, groups.length) * ROW + 6;
  const H2 = groups.length ? H : H + ROW;
  const med = median(points.filter((p) => !p.heldOut).map((p) => p.value));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + t * (hi - lo));
  const drawn =
    props.drawn ??
    `${points.length} record${points.length === 1 ? '' : 's'} by ${props.groupBy}${rules.length ? `, ${rules.length} computed limit${rules.length === 1 ? '' : 's'}` : ''}${notDrawn ? `; ${notDrawn} not drawn: their unit does not convert to ${props.unit}` : ''}.`;
  const sources = [...new Set(points.map((p) => p.record.paperId))];
  return (
    <FigureFrame
      title={props.title}
      drawn={drawn}
      axes={[`${props.quantity} (${props.unit})`]}
      table={toTable(props)}
      csvName={props.csvName ?? 'evidence-strip'}
      sources={sources}
      basis={props.basis}
      notes={props.notes}
      empty={points.length === 0 && rules.length === 0 ? props.empty ?? { what: 'no record of this field.', where: 'Records arrive through Intake and are kept in BioRepo.' } : null}
    >
      <svg viewBox={`0 0 ${W} ${H2}`} className="w-full h-auto" role="img" aria-label={props.title} data-testid="evidence-strip">
        {groups.map((g, i) => (
          <g key={g}>
            <line x1={LEFT} x2={W - RIGHT} y1={TOP + i * ROW} y2={TOP + i * ROW} stroke="currentColor" strokeOpacity={0.08} />
            <text x={LEFT - 8} y={TOP + i * ROW + 4} textAnchor="end" fontSize={11} fill="currentColor">
              {g.length > 30 ? `${g.slice(0, 29)}…` : g}
            </text>
          </g>
        ))}
        {rules.map((r, i) => {
          const rx = x(r.value);
          const inward = rx > W * 0.6;
          const ly = 10 + i * LABEL;
          return (
            <g key={r.label} data-testid="strip-rule">
              <line x1={rx} x2={rx} y1={ly + 2} y2={axisY} {...lineStroke(r.provenance ?? 'computed')} />
              <text x={inward ? rx - 4 : rx + 4} y={ly} textAnchor={inward ? 'end' : 'start'} fontSize={10} fill="currentColor">
                {r.label}
              </text>
            </g>
          );
        })}
        {points.map((p) => (
          <g key={p.record.id}>
            <title>
              {`${p.record.id} · ${fmt(p.value)} ${props.unit} · ${p.provenance}${p.heldOut ? ` · held out: ${p.heldOut}` : ''}${p.above ? ` · ${p.above}` : ''}`}
            </title>
            <Mark p={p.provenance} x={x(p.value)} y={TOP + groups.indexOf(p.group) * ROW} faint={Boolean(p.heldOut)} flagged={Boolean(p.above)} />
          </g>
        ))}
        {points.length === 0 && (
          <text x={8} y={TOP + 2} fontSize={11} fill="currentColor" opacity={0.8} data-testid="strip-no-records">
            <tspan x={8}>{props.empty?.what ? `No record yet: ${props.empty.what}` : 'No record of this field yet.'}</tspan>
            {props.empty?.where && (
              <tspan x={8} dy={14}>
                {props.empty.where}
              </tspan>
            )}
          </text>
        )}
        <line x1={LEFT} x2={W - RIGHT} y1={axisY} y2={axisY} stroke="currentColor" strokeOpacity={0.4} />
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={axisY + 14} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.7}>
            {fmt(t, 2)}
          </text>
        ))}
        {med !== null && (
          <g data-testid="strip-median">
            <line x1={x(med)} x2={x(med)} y1={axisY - 6} y2={axisY + 4} stroke="currentColor" strokeWidth={2} />
            <text x={x(med)} y={axisY + 26} textAnchor="middle" fontSize={10} fill="currentColor">
              median
            </text>
          </g>
        )}
      </svg>
    </FigureFrame>
  );
}
