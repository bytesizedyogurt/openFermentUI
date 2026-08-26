// Scenario comparison (OF-DES-001 §8.13). Deltas are arithmetically exact:
// every number here comes from the same evaluateGrid outputs the workspace
// shows, never from a separately recomputed total.
import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { GitCompare, Pin } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import type { CostLine, Scenario } from '@/data/types';
import { evaluateGrid, COST_LINES, COST_LINE_LABEL } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { exportCSV } from '@/lib/csv';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import { PageHeader, Card, Button, EmptyState, Callout, cx } from '@/components/ui';
import { Tick } from '@/components/Provenance';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';

interface Evaluated {
  scenario: Scenario;
  msp: number;
  costLines: Record<CostLine, number>;
}

/**
 * One sentence naming the cost line that accounts for most of the gap between
 * two scenarios. Generated from the actual largest delta, never hardcoded.
 */
function summarize(a: Evaluated, b: Evaluated): string {
  const cheaper = a.msp <= b.msp ? a : b;
  const dearer = a.msp <= b.msp ? b : a;
  const gap = dearer.msp - cheaper.msp;
  if (gap < 0.01) {
    return `${a.scenario.name} and ${b.scenario.name} land within a cent per kilogram of each other at these settings.`;
  }
  let biggest: CostLine = 'capex';
  let biggestDelta = -Infinity;
  for (const line of COST_LINES) {
    const d = dearer.costLines[line] - cheaper.costLines[line];
    if (d > biggestDelta) {
      biggestDelta = d;
      biggest = line;
    }
  }
  const share = (biggestDelta / gap) * 100;
  const label = COST_LINE_LABEL[biggest].toLowerCase();
  return `${cheaper.scenario.name} undercuts ${dearer.scenario.name} by $${fmt(gap, 1)}/kg, and ${share >= 50 ? 'most' : 'the largest single share'} of that gap (${share.toFixed(0)}%) is ${label}.`;
}

export default function Compare() {
  const scenarios = useStore((s) => s.scenarios);
  const grids = useStore((s) => s.grids);

  const pinned = scenarios.filter((s) => s.pinned);
  const shown = pinned.slice(0, 3);

  const evaluated = useMemo<Evaluated[]>(
    () =>
      shown
        .map((scenario) => {
          const grid = grids[scenario.modelId];
          if (!grid) return null;
          const r = evaluateGrid(grid, scenario.point);
          return { scenario, msp: r.msp, costLines: r.costLines };
        })
        .filter(Boolean) as Evaluated[],
    [shown, grids],
  );

  const theme = useChartTheme();
  const seriesColor = useSeriesColor();
  const tip = tooltipStyle(theme);

  const crossModel = new Set(shown.map((s) => s.modelId)).size > 1;

  if (pinned.length === 0) {
    return (
      <div>
        <PageHeader title="Compare scenarios" subtitle="Pin scenarios to line them up side by side." />
        <OwnerTabs tabs={BIOREPO_TABS} />
        <EmptyState
          title="Nothing pinned yet"
          body="Open a scenario and use Pin to compare (or press p) to add it here. Up to three can be compared at once."
          icon={<GitCompare size={28} />}
          action={<Button onClick={() => navigate('/proforma')}>Browse scenarios</Button>}
        />
      </div>
    );
  }

  const exportDeltas = () => {
    const headers = ['Cost line', ...evaluated.map((e) => `${e.scenario.name} ($/kg)`)];
    const rows: (string | number)[][] = COST_LINES.map((l) => [
      COST_LINE_LABEL[l],
      ...evaluated.map((e) => e.costLines[l].toFixed(2)),
    ]);
    rows.push(['Minimum selling price', ...evaluated.map((e) => e.msp.toFixed(2))]);
    exportCSV('scenario-comparison.csv', headers, rows);
  };

  return (
    <div>
      <PageHeader
        title="Compare scenarios"
        subtitle={`${evaluated.length} pinned scenario${evaluated.length === 1 ? '' : 's'} at their current settings. Every delta is computed from the same interpolated cost lines the workspaces show.`}
        actions={<Button onClick={exportDeltas}>Export deltas CSV</Button>}
      />
      <OwnerTabs tabs={BIOREPO_TABS} />

      {pinned.length > 3 && (
        <div className="mb-4">
          <Callout kind="info">
            {pinned.length} scenarios are pinned; showing the first three. Unpin one to swap it out.
          </Callout>
        </div>
      )}

      {crossModel && (
        <div className="mb-4">
          <Callout kind="warn" title="Cross-model comparison">
            These scenarios come from different cost models with different products and boundaries.
            The deltas below are arithmetically correct but not directly meaningful — a dollar of
            downstream cost in an algal biomass model is not the same quantity as a dollar in a
            fed-batch protein model.
          </Callout>
        </div>
      )}

      {/* Headline row */}
      <div
        className="grid gap-4 mb-5"
        style={{ gridTemplateColumns: `repeat(${Math.min(3, evaluated.length)}, minmax(0, 1fr))` }}
      >
        {evaluated.map((e) => (
          <Card key={e.scenario.id} className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <span className="chip font-num">{e.scenario.modelId}</span>
              <Pin size={12} className="text-accent" />
            </div>
            <a
              href={`#/proforma/scenario/${e.scenario.id}`}
              className="font-serif text-section-title font-semibold hover:text-accent block leading-snug"
            >
              {e.scenario.name}
            </a>
            <Tick p="demo" className="mt-2">
              <div className="font-num text-display leading-none">
                ${fmt(e.msp, 1)}
                <span className="text-body text-ink-soft ml-1">/kg</span>
              </div>
              <div className="text-caption text-ink-soft">
                Demo model v0 — illustrative economics, not validated
              </div>
            </Tick>
            <div className="text-caption text-ink-soft mt-2 space-y-0.5">
              {e.scenario.dims.map((d) => (
                <div key={d.key} className="flex justify-between gap-2">
                  <span className="truncate">{d.label}</span>
                  <span className="font-num shrink-0">
                    {fmt(e.scenario.point[d.key])} {d.unit}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Small-multiple waterfalls */}
      <h2 className="font-serif text-section-title font-semibold mb-2">Cost build-up</h2>
      <div
        className="grid gap-4 mb-5"
        style={{ gridTemplateColumns: `repeat(${Math.min(3, evaluated.length)}, minmax(0, 1fr))` }}
      >
        {evaluated.map((e) => {
          const data = COST_LINES.map((l) => ({
            name: COST_LINE_LABEL[l],
            value: e.costLines[l],
          }));
          const max = Math.max(...evaluated.flatMap((x) => COST_LINES.map((l) => x.costLines[l])));
          return (
            <Card key={e.scenario.id} className="p-3">
              <div className="text-caption text-ink-soft mb-1 truncate">{e.scenario.name}</div>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data} margin={{ top: 4, right: 6, bottom: 40, left: 0 }}>
                    <CartesianGrid stroke={theme.grid} vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: theme.axis, fontSize: 9 }}
                      angle={-32}
                      textAnchor="end"
                      interval={0}
                      height={52}
                    />
                    {/* Shared domain so the small multiples are comparable by eye */}
                    <YAxis
                      domain={[0, Math.ceil(max)]}
                      tick={{ fill: theme.axis, fontSize: 10 }}
                      tickFormatter={(v) => `$${v}`}
                      width={44}
                    />
                    <Tooltip {...tip} formatter={(v: number) => [`$${v.toFixed(2)}/kg`, 'Cost']} />
                    <Bar dataKey="value" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                      {data.map((_, i) => (
                        <Cell key={i} fill={seriesColor(i)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Delta table */}
      {evaluated.length >= 2 && (
        <Card className="p-4 mb-5">
          <h2 className="font-serif text-section-title font-semibold mb-3">
            Line-by-line deltas
            <span className="font-sans text-caption text-ink-soft font-normal ml-2">
              relative to {evaluated[0].scenario.name}
            </span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-line text-caption text-ink-soft">
                  <th className="text-left py-2">Cost line</th>
                  {evaluated.map((e) => (
                    <th key={e.scenario.id} className="text-right px-3">
                      {e.scenario.name}
                    </th>
                  ))}
                  {evaluated.slice(1).map((e) => (
                    <th key={`d-${e.scenario.id}`} className="text-right px-3">
                      Δ vs {evaluated[0].scenario.modelId}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COST_LINES.map((line) => (
                  <tr key={line} className="border-b border-line/60">
                    <td className="py-1.5">{COST_LINE_LABEL[line]}</td>
                    {evaluated.map((e) => (
                      <td key={e.scenario.id} className="text-right font-num px-3">
                        ${e.costLines[line].toFixed(2)}
                      </td>
                    ))}
                    {evaluated.slice(1).map((e) => {
                      const base = evaluated[0].costLines[line];
                      const d = e.costLines[line] - base;
                      const pct = base === 0 ? 0 : (d / base) * 100;
                      return (
                        <td
                          key={`d-${e.scenario.id}`}
                          className={cx(
                            'text-right font-num px-3',
                            d > 0 ? 'text-signal-warn' : d < 0 ? 'text-signal-info' : 'text-ink-soft',
                          )}
                        >
                          {d >= 0 ? '+' : ''}
                          {d.toFixed(2)}{' '}
                          <span className="text-caption opacity-70">
                            ({pct >= 0 ? '+' : ''}
                            {pct.toFixed(0)}%)
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr className="border-t-2 border-line font-medium">
                  <td className="py-2">Minimum selling price</td>
                  {evaluated.map((e) => (
                    <td key={e.scenario.id} className="text-right font-num px-3">
                      ${e.msp.toFixed(2)}
                    </td>
                  ))}
                  {evaluated.slice(1).map((e) => {
                    const d = e.msp - evaluated[0].msp;
                    const pct = (d / evaluated[0].msp) * 100;
                    return (
                      <td
                        key={`d-${e.scenario.id}`}
                        className={cx(
                          'text-right font-num px-3',
                          d > 0 ? 'text-signal-warn' : 'text-signal-info',
                        )}
                      >
                        {d >= 0 ? '+' : ''}
                        {d.toFixed(2)}{' '}
                        <span className="text-caption opacity-70">
                          ({pct >= 0 ? '+' : ''}
                          {pct.toFixed(0)}%)
                        </span>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Auto-summary, one line per pair */}
      {evaluated.length >= 2 && (
        <Card className="p-4">
          <h2 className="font-serif text-section-title font-semibold mb-2">What the numbers say</h2>
          <ul className="space-y-2">
            {evaluated.flatMap((a, i) =>
              evaluated.slice(i + 1).map((b) => (
                <li key={`${a.scenario.id}-${b.scenario.id}`} className="tick tick-demo text-body">
                  {summarize(a, b)}
                </li>
              )),
            )}
          </ul>
          <p className="text-caption text-ink-soft mt-3">
            Generated from the largest cost-line difference at the current points — not a stored
            sentence. Move a slider and it changes.
          </p>
        </Card>
      )}
    </div>
  );
}
