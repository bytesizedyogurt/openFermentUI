// Where the price comes from, and what moves it — Proforma's three charts.
//
// These lived on `/fermos/s/:id` until the tandem pass. They are economics:
// a decomposition of the minimum selling price, a ranking of parameters by
// their effect on it, and a sweep of it against one axis. fermOS owns the
// process; a chart whose y-axis is a price is not the process.
//
// They read the precomputed grid rather than solving a plant, which is
// deliberate and is why they can sit on a screen a reader drags a slider on:
// `evaluateGrid` is the interpolation CLAUDE.md keeps in TypeScript on purpose.
//
// ── TWO CHART DEFECTS FIXED ON THE WAY ────────────────────────────────────
//
// The waterfall's x-axis rotated `COST_LINE_LABEL` at -28°, and two of the six
// are long enough that they clipped into unreadable fragments — a reader saw
// "…pital recovery — upstream". The axis now carries a short form and the
// table below keeps the full label, so nothing is lost and everything is legible.
//
// The sweep's y-axis was linear. MSP against titer is a hyperbola: the
// lowest-titer corner is two orders of magnitude above the rest, so the axis
// was set by the corner and the region a reader actually works in was a flat
// line on the floor. It is logarithmic now, which is the honest scale for a
// quantity that spans decades and is what makes the knee visible at all.
import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart as RLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceDot,
} from 'recharts';

import { COST_LINES, COST_LINE_LABEL, mspSweep, type EvaluatedPoint } from '@/engine/grids';
import { fmt } from '@/engine/units';
import type { ResultGrid, Scenario } from '@/data/types';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import { ChartTable } from '@/components/ChartTable';
import { Card, Explain } from '@/components/ui';

/**
 * The axis form of each cost line.
 *
 * `COST_LINE_LABEL` is written for a reader — "Capital recovery — recovery &
 * purification" says exactly what the line is. At -28° in a 260px chart it says
 * "…recovery & purification". The full label stays on every table and tooltip;
 * this is the axis tick only.
 */
const AXIS_LABEL: Record<string, string> = {
  capex: 'Capital · upstream',
  downstream: 'Capital · recovery',
  media: 'Feedstock',
  utilities: 'Utilities',
  labor: 'Labour',
  other: 'Overhead',
};

export function CostBuildUp({
  scenario,
  grid,
  result,
}: {
  scenario: Scenario;
  grid: ResultGrid;
  result: EvaluatedPoint | null;
}) {
  const theme = useChartTheme();
  const seriesColor = useSeriesColor();
  const tip = tooltipStyle(theme);

  const primaryDim = scenario.dims[0];
  const secondaryDim = scenario.dims[1];

  // A transparent base plus a visible delta per cost line, so the bars stack up
  // to the headline. They sum exactly because `evaluateGrid` computes the total
  // from these same interpolated lines.
  const waterfall = useMemo(() => {
    if (!result) return [];
    let cum = 0;
    const rows = COST_LINES.map((line) => {
      const value = result.costLines[line];
      const row = { name: AXIS_LABEL[line] ?? line, base: cum, value, line };
      cum += value;
      return row;
    });
    return [...rows, { name: 'MSP', base: 0, value: cum, line: 'total' as const }];
  }, [result]);

  const sweep = useMemo(
    () => (primaryDim ? mspSweep(grid, primaryDim.key, scenario.point, 48) : []),
    [grid, primaryDim, scenario.point],
  );

  const smallMultiples = useMemo(() => {
    if (!secondaryDim || !primaryDim) return [];
    return secondaryDim.values.map((v) => ({
      label: `${fmt(v)} ${secondaryDim.unit}`,
      data: mspSweep(grid, primaryDim.key, { ...scenario.point, [secondaryDim.key]: v }, 24),
    }));
  }, [grid, primaryDim, secondaryDim, scenario.point]);

  // Every row, sorted by the larger of its two excursions. No `.slice()`: the
  // three flowsheets carry two or three parameters each today, so a cap would
  // protect nothing and would silently drop a bar the day one gained a fourth.
  const tornado = [...grid.sensitivity].sort(
    (a, b) =>
      Math.max(Math.abs(b.lowPct), Math.abs(b.hiPct)) -
      Math.max(Math.abs(a.lowPct), Math.abs(a.hiPct)),
  );

  /**
   * The sweep's y-domain, floored away from zero.
   *
   * A log axis cannot render a zero or a negative, and a failed grid corner
   * returns zero. Those points are dropped from the domain rather than from the
   * series — recharts simply does not plot them — and the floor is the smallest
   * price the sweep actually produced.
   */
  const sweepValues = [...sweep, ...smallMultiples.flatMap((s) => s.data)]
    .map((p) => p.msp)
    .filter((v) => Number.isFinite(v) && v > 0);
  const sweepDomain: [number, number] | undefined = sweepValues.length
    ? [Math.min(...sweepValues) * 0.9, Math.max(...sweepValues) * 1.1]
    : undefined;

  return (
    <>
      <Card className="p-4">
        <h2 className="font-serif text-section-title font-semibold mb-1">Cost build-up</h2>
        <p className="text-caption text-ink-soft mb-3">
          The six lines are computed together and sum to the headline exactly.
        </p>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={waterfall} margin={{ top: 5, right: 8, bottom: 24, left: 4 }}>
              <CartesianGrid stroke={theme.grid} vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: theme.axis, fontSize: 11 }}
                interval={0}
                height={38}
              />
              <YAxis
                tick={{ fill: theme.axis, fontSize: 11 }}
                tickFormatter={(v) => `$${v}`}
                width={52}
              />
              <Tooltip
                {...tip}
                formatter={(v: number, name: string) =>
                  name === 'value' ? [`${v.toFixed(2)} USD kg⁻¹`, 'Contribution'] : null
                }
              />
              <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="value" stackId="w" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                {waterfall.map((row, i) => (
                  <Cell key={row.name} fill={row.line === 'total' ? theme.accent : seriesColor(i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <ChartTable
          headers={['Cost line', 'USD kg⁻¹', 'Share']}
          rows={
            result
              ? COST_LINES.map((l) => [
                  COST_LINE_LABEL[l],
                  result.costLines[l].toFixed(2),
                  `${((result.costLines[l] / result.msp) * 100).toFixed(1)}%`,
                ]).concat([['Minimum selling price', result.msp.toFixed(2), '100%']])
              : []
          }
        />
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-3">
        <Card className="p-4">
          <h2 className="font-serif text-section-title font-semibold mb-1">
            Sensitivity{' '}
            <Explain label="How to read a tornado">
              Each bar takes one parameter to the bottom and the top of its modelled range, holds
              the rest at the reference point, and rebuilds the entire plant — new equipment sizes,
              new capital, a fresh cash flow — to see what the price does. Longer bars matter more.
              Asymmetric bars mean the risk is one-sided, which is usually more decision-relevant
              than the length. One-at-a-time analysis cannot see interactions; the rank correlation
              below can.
            </Explain>
          </h2>
          <p className="text-caption text-ink-soft mb-3">
            Derived by re-solving the plant at each parameter’s bounds, evaluated at the model’s
            reference point — not at the scenario’s current position. Move a slider in fermOS to a
            bound and the headline will agree with the bar.
          </p>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tornado} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 8 }}>
                <CartesianGrid stroke={theme.grid} horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: theme.axis, fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="assumption"
                  tick={{ fill: theme.axis, fontSize: 10 }}
                  width={124}
                />
                <Tooltip {...tip} formatter={(v: number) => [`${v.toFixed(1)}%`, 'MSP change']} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="lowPct" name="at the lower bound" fill={seriesColor(0)} isAnimationActive={false} />
                <Bar dataKey="hiPct" name="at the upper bound" fill={seriesColor(1)} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ChartTable
            headers={['Parameter', 'At the lower bound', 'At the upper bound']}
            rows={tornado.map((t) => [t.assumption, `${t.lowPct.toFixed(1)}%`, `${t.hiPct.toFixed(1)}%`])}
          />
        </Card>

        <Card className="p-4">
          <h2 className="font-serif text-section-title font-semibold mb-1">
            Price against {primaryDim?.label?.toLowerCase()}
          </h2>
          <p className="text-caption text-ink-soft mb-3">
            {secondaryDim
              ? `Small multiples hold ${primaryDim?.label.toLowerCase()} on the axis and step ${secondaryDim.label.toLowerCase()}. `
              : 'Current point marked. '}
            Logarithmic, because the low corner is two orders above the rest and a linear axis
            flattens the region worth reading into a line on the floor.
          </p>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RLineChart margin={{ top: 4, right: 10, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={theme.grid} />
                <XAxis
                  type="number"
                  dataKey="x"
                  domain={['dataMin', 'dataMax']}
                  tick={{ fill: theme.axis, fontSize: 11 }}
                  label={{
                    value: `${primaryDim?.label} (${primaryDim?.unit})`,
                    position: 'insideBottom',
                    offset: -2,
                    fill: theme.axis,
                    fontSize: 10,
                  }}
                />
                <YAxis
                  scale="log"
                  domain={sweepDomain ?? ['auto', 'auto']}
                  allowDataOverflow
                  tick={{ fill: theme.axis, fontSize: 11 }}
                  tickFormatter={(v: number) => `$${fmt(v, v < 100 ? 0 : 0)}`}
                  width={58}
                />
                <Tooltip
                  {...tip}
                  formatter={(v: number) => [`${v.toFixed(1)} USD kg⁻¹`, 'MSP']}
                  labelFormatter={(l) => `${fmt(Number(l))} ${primaryDim?.unit}`}
                />
                {smallMultiples.length > 0 ? (
                  smallMultiples.map((sm, i) => (
                    <Line
                      key={sm.label}
                      data={sm.data}
                      dataKey="msp"
                      name={sm.label}
                      stroke={seriesColor(i)}
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={false}
                    />
                  ))
                ) : (
                  <Line
                    data={sweep}
                    dataKey="msp"
                    stroke={seriesColor(0)}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                )}
                {result && primaryDim && (
                  <ReferenceDot
                    x={scenario.point[primaryDim.key]}
                    y={result.msp}
                    r={5}
                    fill={theme.accent}
                    stroke={theme.surface}
                    strokeWidth={2}
                    isFront
                  />
                )}
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </RLineChart>
            </ResponsiveContainer>
          </div>
          <ChartTable
            headers={[primaryDim?.label ?? 'x', 'MSP (USD kg⁻¹)']}
            rows={sweep.filter((_, i) => i % 6 === 0).map((p) => [fmt(p.x), p.msp.toFixed(1)])}
          />
        </Card>
      </div>
    </>
  );
}
