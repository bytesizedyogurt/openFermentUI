// Every figure's frame (OF-BLD-014 E.8, rule 4).
//
// A title that states the question, one line saying what is drawn, the axis
// units, a "View as table" twin built from the same rows the chart draws, the
// sources as chips, CSV export, and the basis of anything computed. An empty
// figure says what would fill it and which screen produces that (rule 6).
import { useState, type ReactNode } from 'react';
import { Download, Table2 } from 'lucide-react';
import type { ComputedBasis, Provenance } from '@/data/types';
import { exportCSV } from '@/lib/csv';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { DASH_ARRAY, ENCODING, LINE_WIDTH, markColor } from './encoding';

export interface FigureTable {
  headers: string[];
  rows: (string | number)[][];
}

export interface FigureFrameProps {
  /** The question the figure answers. */
  title: string;
  /** One line: what is drawn. */
  drawn: string;
  /** Axis labels, each with its unit. */
  axes?: string[];
  table: FigureTable;
  csvName: string;
  /** Paper ids the marks come from. */
  sources?: string[];
  /** The basis of each computed thing drawn. */
  basis?: ComputedBasis[];
  /** Shown in place of the chart when there is nothing to draw. */
  empty?: { what: string; where: string } | null;
  /** Lines under the chart that the figure always states. */
  notes?: string[];
  children: ReactNode;
}

export function FigureFrame({ title, drawn, axes, table, csvName, sources, basis, empty, notes, children }: FigureFrameProps) {
  const [asTable, setAsTable] = useState(false);
  return (
    <figure className="rounded-card border border-line bg-surface-0 p-3" data-testid="figure">
      <figcaption className="mb-2">
        <div className="font-medium text-reading text-ink">{title}</div>
        <div className="text-caption text-ink-soft">{drawn}</div>
        {axes && axes.length > 0 && <div className="text-caption text-ink-soft font-num">{axes.join(' · ')}</div>}
      </figcaption>
      {empty ? (
        <div className="rounded-input border border-dashed border-line p-4 text-body text-ink-soft" data-testid="figure-empty">
          <p className="text-ink">Nothing to draw yet: {empty.what}</p>
          <p className="mt-1">{empty.where}</p>
        </div>
      ) : asTable ? (
        <TableTwin table={table} />
      ) : (
        <div className="text-ink">{children}</div>
      )}
      {notes && notes.length > 0 && (
        <div className="mt-2 space-y-1">
          {notes.map((n) => (
            <p key={n} className="text-caption text-ink-soft">
              {n}
            </p>
          ))}
        </div>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-caption">
        {!empty && (
          <button className={cx('chip', asTable && 'chip-active')} aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
            <Table2 size={12} aria-hidden /> View as table
          </button>
        )}
        {!empty && (
          <button className="chip" onClick={() => exportCSV(`${csvName}.csv`, table.headers, table.rows)}>
            <Download size={12} aria-hidden /> CSV
          </button>
        )}
        {sources && sources.length > 0 && (
          <span className="flex flex-wrap items-center gap-1 text-ink-soft">
            Sources:
            {sources.map((id) => (
              <a key={id} className="chip font-num" href={href(`/biorepo/paper/${id}`)}>
                {id}
              </a>
            ))}
          </span>
        )}
      </div>
      {basis && basis.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent">How the computed lines were made</summary>
          <ul className="mt-1 space-y-1.5">
            {basis.map((b) => (
              <li key={b.artifactId} className="text-caption">
                <div className="text-ink">
                  {b.tool} <span className="font-num text-ink-soft">{b.toolVersion}</span> ·{' '}
                  <a className="font-num hover:text-accent" href={href(`/biorepo/artifacts/${b.artifactId}`)}>
                    {b.artifactId}
                  </a>
                </div>
                <ul className="ml-3">
                  {b.inputs.map((i) => (
                    <li key={`${i.name}-${i.source.kind}-${i.source.id ?? ''}`} className="text-ink-soft">
                      {i.name}: <span className="font-num text-ink">{String(i.value)} {i.unit}</span> — {i.source.kind}
                      {i.source.id ? ` ${i.source.id}` : ''}
                      {i.source.note ? ` (${i.source.note})` : ''}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </details>
      )}
    </figure>
  );
}

function TableTwin({ table }: { table: FigureTable }) {
  return (
    <div className="overflow-x-auto" data-testid="figure-table">
      <table className="w-full text-caption">
        <thead>
          <tr>
            {table.headers.map((h) => (
              <th key={h} className="text-left font-medium text-ink-soft px-1.5 py-1 border-b border-line">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className="border-b border-line/50">
              {r.map((c, j) => (
                <td key={j} className="px-1.5 py-1 font-num text-ink">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** One point, drawn by its provenance (E.8 rule 2). */
export function Mark({ p, x, y, size = 5, faint = false, flagged = false }: { p: Provenance; x: number; y: number; size?: number; faint?: boolean; flagged?: boolean }) {
  const m = ENCODING[p].point;
  const color = markColor(p);
  const common = {
    stroke: color,
    strokeWidth: 1.5,
    fill: m.filled ? color : 'none',
    strokeDasharray: m.outline === 'dashed' ? '2 1.5' : undefined,
  };
  const s = size;
  const shape =
    m.shape === 'circle' ? (
      <circle cx={x} cy={y} r={s} {...common} />
    ) : m.shape === 'square' ? (
      <rect x={x - s} y={y - s} width={2 * s} height={2 * s} {...common} />
    ) : m.shape === 'diamond' ? (
      <polygon points={`${x},${y - s * 1.3} ${x + s * 1.3},${y} ${x},${y + s * 1.3} ${x - s * 1.3},${y}`} {...common} />
    ) : (
      <polygon points={`${x},${y - s * 1.2} ${x + s * 1.1},${y + s * 0.9} ${x - s * 1.1},${y + s * 0.9}`} {...common} />
    );
  return (
    <g opacity={faint ? 0.35 : 1} data-provenance={p}>
      {m.ring && <circle cx={x} cy={y} r={s + 3} fill="none" stroke={color} strokeWidth={1} />}
      {/* Dashed, so in greyscale it stays apart from gold's solid ring (§6.R). */}
      {flagged && <circle cx={x} cy={y} r={s + 5} fill="none" stroke="rgb(var(--signal-warn))" strokeWidth={1.5} strokeDasharray="2 2" data-flag="above" />}
      {shape}
    </g>
  );
}

/** A line's stroke props, by provenance (E.8 rule 2). */
export function lineStroke(p: Provenance) {
  const l = ENCODING[p].line;
  return { stroke: markColor(p), strokeWidth: LINE_WIDTH[l.weight], strokeDasharray: DASH_ARRAY[l.dash] };
}

/** The legend: every provenance's point and line, in words beside each. */
export function EncodingLegend({ only }: { only?: Provenance[] }) {
  const classes = (only ?? (Object.keys(ENCODING) as Provenance[])) as Provenance[];
  return (
    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1" data-testid="encoding-legend">
      {classes.map((p) => (
        <li key={p} className="flex items-center gap-2 text-caption">
          <svg width={52} height={16} aria-hidden className="text-ink shrink-0">
            <Mark p={p} x={8} y={8} size={4} />
            <line x1={20} x2={50} y1={8} y2={8} {...lineStroke(p)} />
          </svg>
          <span className="text-ink">{p}</span>
          <span className="text-ink-soft">{ENCODING[p].words}</span>
        </li>
      ))}
    </ul>
  );
}
