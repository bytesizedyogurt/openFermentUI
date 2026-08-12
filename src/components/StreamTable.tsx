// bioSTEAM's `report.stream_table`, in this app's table idiom.
//
// Upstream prints streams across the top and properties down the side, which is
// the wrong way round for most tables and exactly right for this one: a reader
// checking a mass balance reads one stream at a time, top to bottom, and
// compares the column beside it. The orientation is what makes the table
// recognisable to anyone who has read a bioSTEAM report, so it is kept, and the
// property names are pinned to the left edge so the labels survive the sideways
// scroll a wide flowsheet forces.
import { useMemo, useState, type ReactNode } from 'react';
import { Waves } from 'lucide-react';
import type { StreamRow } from '@/engine/biosteam/system';
import { fmt } from '@/engine/units';
import { Button, EmptyState, cx } from '@/components/ui';

type CompositionMode = 'percent' | 'flow';

const PHASE_NAME: Record<StreamRow['phase'], string> = {
  l: 'liquid',
  g: 'gas',
  s: 'solid',
};

/**
 * Every component that appears anywhere in the set, product first.
 *
 * The union is taken over `flow` rather than `composition` because the engine
 * drops zero entries from the composition, and a component that a stream
 * carries at zero is a different claim from one the stream never had. The
 * target product leads because it is the row the reader came for; the rest go
 * alphabetically so a component keeps its position between renders.
 */
function componentOrder(streams: StreamRow[]): string[] {
  const seen = new Set<string>();
  for (const s of streams) {
    for (const k of Object.keys(s.flow)) seen.add(k);
    for (const k of Object.keys(s.composition)) seen.add(k);
  }
  return [...seen].sort((a, b) => {
    if (a === 'product') return -1;
    if (b === 'product') return 1;
    return a.localeCompare(b);
  });
}

/**
 * The stream the TEA solves a price for.
 *
 * It leaves the plant — something made it and nothing consumes it — and it
 * carries a price. Feeds are priced too, but a feed has no source, and a waste
 * stream has no sink and no price, so the three cases separate cleanly.
 */
function isPricedProduct(s: StreamRow): boolean {
  return s.source !== null && s.sink === null && s.price > 0;
}

/** Whether the stream carries this component at all, zero included. */
function carries(s: StreamRow, component: string): boolean {
  return Object.prototype.hasOwnProperty.call(s.flow, component);
}

function Absent({ title }: { title: string }): JSX.Element {
  return (
    <span className="text-ink-soft/70" title={title}>
      —
    </span>
  );
}

/** A source or sink cell: the unit that made or consumes the stream. */
function UnitCell({
  id,
  absentTitle,
  onSelectUnit,
}: {
  id: string | null;
  absentTitle: string;
  onSelectUnit?: (id: string) => void;
}): JSX.Element {
  if (id === null) return <Absent title={absentTitle} />;
  if (!onSelectUnit) return <span className="font-num">{id}</span>;
  return (
    <button
      type="button"
      className="font-num text-accent px-1 py-0.5 -mx-1 rounded hover:underline"
      onClick={() => onSelectUnit(id)}
      aria-label={`Show unit ${id}`}
    >
      {id}
    </button>
  );
}

interface PropertyRow {
  label: string;
  /** Shown beside the label, small — the unit of measure and where it came from. */
  note?: string;
  cell: (s: StreamRow) => ReactNode;
}

export function StreamTable({
  streams,
  onSelectUnit,
}: {
  streams: StreamRow[];
  onSelectUnit?: (id: string) => void;
}): JSX.Element {
  const [mode, setMode] = useState<CompositionMode>('percent');
  const components = useMemo(() => componentOrder(streams), [streams]);
  const priced = useMemo(() => streams.map(isPricedProduct), [streams]);

  if (streams.length === 0) {
    return (
      <EmptyState
        icon={<Waves size={20} />}
        title="No streams"
        body="The flowsheet produced no streams, which means it did not build. There is no mass balance to show and none will be invented."
      />
    );
  }

  const properties: PropertyRow[] = [
    {
      label: 'Source',
      cell: (s) => (
        <UnitCell
          id={s.source}
          absentTitle="No source — this is a feed, bought at the plant gate."
          onSelectUnit={onSelectUnit}
        />
      ),
    },
    {
      label: 'Sink',
      cell: (s) => (
        <UnitCell
          id={s.sink}
          absentTitle="No sink — this stream leaves the plant as a product or a waste."
          onSelectUnit={onSelectUnit}
        />
      ),
    },
    {
      label: 'Phase',
      cell: (s) => (
        <span className="font-num" title={PHASE_NAME[s.phase]}>
          {s.phase}
        </span>
      ),
    },
    { label: 'Temperature', note: 'K', cell: (s) => <span className="font-num">{s.T.toFixed(1)}</span> },
    {
      label: 'Pressure',
      note: 'kPa, from Pa',
      cell: (s) => <span className="font-num">{(s.P / 1000).toFixed(1)}</span>,
    },
    {
      label: 'Flow',
      note: 'kg/hr',
      cell: (s) => <span className="font-num">{fmt(s.massFlow)}</span>,
    },
  ];

  const compositionLabel = mode === 'percent' ? 'Composition [%]' : 'Component flow [kg/hr]';

  return (
    <div>
      <div className="flex items-end justify-between gap-4 flex-wrap mb-2">
        <p className="text-caption text-ink-soft max-w-2xl">
          Every stream the flowsheet carries, streams across and properties down as bioSTEAM prints
          them — this is where you check that the mass the plant buys is the mass it sells.
        </p>
        <div role="group" aria-label="Composition units" className="flex items-center gap-1 shrink-0">
          <Button
            size="sm"
            aria-pressed={mode === 'percent'}
            className={cx(mode === 'percent' && 'bg-accent-wash border-accent/40')}
            onClick={() => setMode('percent')}
          >
            %
          </Button>
          <Button
            size="sm"
            aria-pressed={mode === 'flow'}
            className={cx(mode === 'flow' && 'bg-accent-wash border-accent/40')}
            onClick={() => setMode('flow')}
          >
            kg/hr
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="text-caption border-collapse" data-table="streams">
          <caption className="sr-only">
            Stream table: one column per stream, with source, sink, phase, temperature in kelvin,
            pressure in kilopascals, total mass flow in kilograms per hour, and the composition of
            each stream {mode === 'percent' ? 'as a percentage of its mass' : 'in kilograms per hour'}.
          </caption>
          <thead>
            <tr className="border-b border-line">
              <th
                scope="col"
                className="sticky left-0 z-20 bg-surface-1 border-r border-line text-left align-bottom py-1.5 pr-3 font-medium text-ink-soft whitespace-nowrap"
              >
                Stream
              </th>
              {streams.map((s, i) => (
                <th
                  key={`${s.ID}-${i}`}
                  scope="col"
                  className={cx(
                    'text-right align-bottom py-1.5 px-3 font-num font-medium whitespace-nowrap min-w-[6rem]',
                    priced[i] && 'bg-accent-wash',
                  )}
                >
                  {s.ID}
                  {priced[i] && (
                    <div className="font-sans font-normal text-ink-soft">price solved here</div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {properties.map((row) => (
              <tr key={row.label} className="border-b border-line/50">
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-surface-1 border-r border-line text-left py-1.5 pr-3 font-normal text-ink-soft whitespace-nowrap"
                >
                  {row.label}
                  {row.note && <span className="text-ink-soft/70"> [{row.note}]</span>}
                </th>
                {streams.map((s, i) => (
                  <td
                    key={`${s.ID}-${i}`}
                    className={cx(
                      'py-1.5 px-3 text-right whitespace-nowrap',
                      priced[i] && 'bg-accent-wash',
                    )}
                  >
                    {row.cell(s)}
                  </td>
                ))}
              </tr>
            ))}

            <tr className="border-y border-line">
              <th
                scope="row"
                className="sticky left-0 z-10 bg-surface-1 border-r border-line text-left py-1.5 pr-3 font-medium uppercase tracking-wide text-ink-soft whitespace-nowrap"
              >
                {compositionLabel}
              </th>
              {streams.map((s, i) => (
                <td
                  key={`${s.ID}-${i}`}
                  className={cx('py-1.5 px-3', priced[i] && 'bg-accent-wash')}
                />
              ))}
            </tr>

            {components.map((component) => (
              <tr key={component} className="border-b border-line/50">
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-surface-1 border-r border-line text-left py-1 pr-3 pl-3 font-normal whitespace-nowrap"
                >
                  {component}
                </th>
                {streams.map((s, i) => (
                  <td
                    key={`${s.ID}-${i}`}
                    className={cx(
                      'py-1 px-3 text-right font-num whitespace-nowrap',
                      priced[i] && 'bg-accent-wash',
                    )}
                  >
                    {carries(s, component) ? (
                      mode === 'percent' ? (
                        (s.composition[component] ?? 0).toFixed(1)
                      ) : (
                        fmt(s.flow[component])
                      )
                    ) : (
                      <Absent title={`${s.ID} does not carry ${component} at all.`} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
