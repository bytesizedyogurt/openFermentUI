// Scenario workspace (OF-DES-001 §8.13). Read it like an instrument: every
// assumption ticked, the waterfall always summing to the headline, and
// simulation treated as work rather than magic.
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart as RLineChart,
  Line,
  ReferenceDot,
  Cell,
  Legend,
} from 'recharts';
import { AlertTriangle, Copy, Download, GitCompare, Pin, PinOff, Table2, SlidersHorizontal } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import type { CostLine } from '@/data/types';
import { evaluateGrid, mspSweep, COST_LINES, COST_LINE_LABEL } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { scaled } from '@/sim/latency';
import { exportCSV } from '@/lib/csv';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import { PageHeader, Card, Button, Sheet, Callout, cx, EmptyState, Explain } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { Tick, ProvenanceBadge } from '@/components/Provenance';

const CONVERGE_STAGES = ['Building flowsheet', 'Converging', 'Costing'];

/** A "view as table" disclosure — the accessibility floor for every chart (§6.6). */
function ChartTable({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  return (
    <details className="mt-2">
      <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
        <Table2 size={12} /> View as table
      </summary>
      <div className="overflow-x-auto mt-1.5">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {headers.map((h, i) => (
                <th key={h} className={cx('py-1', i === 0 ? 'text-left' : 'text-right')}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-line/50">
                {r.map((c, j) => (
                  <td key={j} className={cx('py-1', j === 0 ? 'text-left' : 'text-right font-num')}>
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default function ScenarioWorkspace({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const grids = useStore((s) => s.grids);
  const setScenarioPoint = useStore((s) => s.setScenarioPoint);
  const togglePin = useStore((s) => s.togglePin);
  const duplicateScenario = useStore((s) => s.duplicateScenario);
  const toast = useStore((s) => s.toast);

  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const [converging, setConverging] = useState<number | null>(null);
  const [activeDim, setActiveDim] = useState(0);
  const lastPoint = useRef<Record<string, number> | null>(null);
  const lastConverged = useRef<Record<string, number> | null>(null);
  const convergeTimer = useRef<number>();

  const grid = scenario ? grids[scenario.modelId] : undefined;

  // The S2 model declares a non-convergent corner (§17.3). Grids are pure data
  // and carry no predicate, so detect the corner from the scenario's own dims.
  const nonConvergent = useMemo(() => {
    if (!scenario || scenario.modelId !== 'S2') return false;
    const dim = (k: string) => scenario.dims.find((d) => d.key === k);
    const titer = dim('titer');
    const dsp = dim('dspYield');
    const sc = dim('scale');
    if (!titer || !dsp || !sc) return false;
    return (
      scenario.point.titer <= titer.values[0] &&
      scenario.point.dspYield <= dsp.values[0] &&
      scenario.point.scale >= sc.values[sc.values.length - 1]
    );
  }, [scenario]);

  const result = useMemo(
    () => (grid && scenario && !nonConvergent ? evaluateGrid(grid, scenario.point) : null),
    [grid, scenario, nonConvergent],
  );

  // Job feel: a move crossing more than one grid cell in any dimension enters a
  // staged "converging" state. Small moves resolve instantly (§17.3).
  useEffect(() => {
    if (!scenario || !grid) return;
    const prev = lastPoint.current;
    lastPoint.current = { ...scenario.point };
    if (!prev) return;

    let crossed = 0;
    for (const d of grid.dims) {
      const cellOf = (v: number) => {
        let i = 0;
        while (i < d.values.length - 1 && v > d.values[i + 1]) i++;
        return i;
      };
      crossed = Math.max(crossed, Math.abs(cellOf(scenario.point[d.key]) - cellOf(prev[d.key])));
    }
    if (crossed < 2) return;

    window.clearTimeout(convergeTimer.current);
    setConverging(0);
    const stageMs = scaled(700 + crossed * 220);
    let stage = 0;
    const advance = () => {
      stage += 1;
      if (stage >= CONVERGE_STAGES.length) {
        setConverging(null);
        return;
      }
      setConverging(stage);
      convergeTimer.current = window.setTimeout(advance, stageMs);
    };
    convergeTimer.current = window.setTimeout(advance, stageMs);
  }, [scenario?.point, grid, scenario]);

  useEffect(() => {
    if (!nonConvergent && scenario) lastConverged.current = { ...scenario.point };
  }, [nonConvergent, scenario]);

  // Keyboard: p pin, c compare, [ ] nudge the active slider (Appendix A).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.isContentEditable) return;
      if (!scenario) return;
      if (e.key === 'p') togglePin(scenario.id);
      else if (e.key === 'c') navigate('/simulate/compare');
      else if (e.key === '[' || e.key === ']') {
        const d = scenario.dims[activeDim];
        if (!d) return;
        const span = d.values[d.values.length - 1] - d.values[0];
        const delta = (span / 40) * (e.key === ']' ? 1 : -1);
        const next = Math.max(
          d.values[0],
          Math.min(d.values[d.values.length - 1], scenario.point[d.key] + delta),
        );
        setScenarioPoint(scenario.id, { [d.key]: next });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [scenario, activeDim, togglePin, setScenarioPoint]);

  const theme = useChartTheme();
  const seriesColor = useSeriesColor();
  const tip = tooltipStyle(theme);

  if (!scenario || !grid) {
    return (
      <EmptyState
        title="Scenario not found"
        body={`No scenario with id ${scenarioId} exists in this session.`}
        action={<Button onClick={() => navigate('/simulate')}>Back to Simulate</Button>}
      />
    );
  }

  const primaryDim = scenario.dims[0];
  const secondaryDim = scenario.dims[1];

  // Waterfall: a transparent base plus a visible delta per cost line, so the
  // bars stack up to the headline. They sum exactly because evaluateGrid
  // computes the total from these same interpolated lines.
  const waterfall = useMemo(() => {
    if (!result) return [];
    let cum = 0;
    const rows = COST_LINES.map((line) => {
      const value = result.costLines[line];
      const row = { name: COST_LINE_LABEL[line], base: cum, value, line };
      cum += value;
      return row;
    });
    return [...rows, { name: 'MSP', base: 0, value: cum, line: 'total' as const }];
  }, [result]);

  const sweep = useMemo(
    () => (primaryDim ? mspSweep(grid, primaryDim.key, scenario.point, 48) : []),
    [grid, primaryDim, scenario.point],
  );

  // Small multiples: the primary sweep repeated at each value of dim 2.
  const smallMultiples = useMemo(() => {
    if (!secondaryDim || !primaryDim) return [];
    return secondaryDim.values.map((v) => ({
      label: `${fmt(v)} ${secondaryDim.unit}`,
      data: mspSweep(grid, primaryDim.key, { ...scenario.point, [secondaryDim.key]: v }, 24),
    }));
  }, [grid, primaryDim, secondaryDim, scenario.point]);

  const tornado = [...grid.sensitivity]
    .map((s) => ({ ...s, mag: Math.max(Math.abs(s.lowPct), Math.abs(s.hiPct)) }))
    .sort((a, b) => b.mag - a.mag);

  const exportAll = () => {
    const headers = ['Section', 'Item', 'Value', 'Unit', 'Provenance', 'Record', 'Note'];
    const rows: (string | number)[][] = [
      ...scenario.dims.map((d) => [
        'Input',
        d.label,
        fmt(scenario.point[d.key]),
        d.unit,
        d.sourceRecordId ? 'verified' : 'demo',
        d.sourceRecordId ?? '',
        'Sweep dimension at its current point',
      ]),
      ...scenario.assumptions.map((a) => [
        'Assumption',
        a.label,
        fmt(a.value),
        a.unit,
        a.provenance,
        a.recordId ?? '',
        a.note,
      ]),
      ...(result
        ? COST_LINES.map((l) => [
            'Result',
            COST_LINE_LABEL[l],
            result.costLines[l].toFixed(2),
            '$/kg',
            'demo',
            '',
            'Interpolated from the precomputed grid',
          ])
        : []),
      ...(result
        ? [['Result', 'Minimum selling price', result.msp.toFixed(2), '$/kg', 'demo', '', 'Demo model v0 — illustrative, not validated']]
        : []),
    ];
    exportCSV(`${scenario.id}-assumptions-results.csv`, headers, rows);
  };

  return (
    <div>
      <PageHeader
        eyebrow={`${scenario.modelId} · scenario`}
        title={scenario.name}
        subtitle={scenario.description}
        actions={
          <>
            <Button onClick={() => togglePin(scenario.id)} title="Pin to compare (p)">
              {scenario.pinned ? <Pin size={14} /> : <PinOff size={14} />}
              {scenario.pinned ? 'Pinned' : 'Pin'}
            </Button>
            <Button
              onClick={() => {
                const id = duplicateScenario(scenario.id);
                navigate(`/simulate/${id}`);
                toast({ text: 'Scenario duplicated', kind: 'success' });
              }}
            >
              <Copy size={14} /> Duplicate
            </Button>
            <Button onClick={exportAll}>
              <Download size={14} /> Export CSV
            </Button>
            <Button onClick={() => navigate('/simulate/compare')} title="Compare (c)">
              <GitCompare size={14} /> Compare
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-5 items-start">
        {/* ── Inputs ──────────────────────────────────────────────────── */}
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-serif text-section-title font-semibold">Inputs</h2>
              <SlidersHorizontal size={14} className="text-ink-soft" />
            </div>

            <div className="space-y-5">
              {scenario.dims.map((d, i) => {
                const lo = d.values[0];
                const hi = d.values[d.values.length - 1];
                const value = scenario.point[d.key];
                return (
                  <div key={d.key} onFocus={() => setActiveDim(i)}>
                    <div className="flex items-baseline justify-between gap-2 mb-1">
                      <label htmlFor={`dim-${d.key}`} className="text-body font-medium">
                        {d.label}
                      </label>
                      <div className="flex items-center gap-1">
                        <input
                          id={`dim-${d.key}-exact`}
                          type="number"
                          className="input w-[86px] font-num text-right py-0.5"
                          value={Number(value.toFixed(3))}
                          step={(hi - lo) / 100}
                          min={lo}
                          max={hi}
                          onChange={(e) =>
                            setScenarioPoint(scenario.id, { [d.key]: Number(e.target.value) })
                          }
                          aria-label={`${d.label} exact value`}
                        />
                        <span className="text-caption text-ink-soft w-12">{d.unit}</span>
                      </div>
                    </div>
                    <input
                      id={`dim-${d.key}`}
                      type="range"
                      min={lo}
                      max={hi}
                      step={(hi - lo) / 200}
                      value={value}
                      onChange={(e) =>
                        setScenarioPoint(scenario.id, { [d.key]: Number(e.target.value) })
                      }
                      onMouseDown={() => setActiveDim(i)}
                      aria-label={d.label}
                    />
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-caption text-ink-soft font-num">
                        {fmt(lo)}–{fmt(hi)} {d.unit}
                      </span>
                      {d.sourceRecordId && <CitationChip recordId={d.sourceRecordId} />}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="text-caption text-ink-soft mt-4">
              <span className="kbd">[</span> <span className="kbd">]</span> nudge the active slider
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Assumptions</h2>
              <span className="font-num text-caption text-ink-soft">
                {scenario.assumptions.length} locked
              </span>
            </div>
            <p className="text-caption text-ink-soft mb-3">
              <span className="font-num">
                {scenario.assumptions.filter((a) => a.recordId).length}
              </span>{' '}
              are linked to corpus records; the rest are labelled demo assumptions.
            </p>
            <Button className="w-full justify-center" onClick={() => setAssumptionsOpen(true)}>
              Open assumptions drawer
            </Button>
          </Card>
        </div>

        {/* ── Results ─────────────────────────────────────────────────── */}
        <div className="space-y-4">
          {nonConvergent ? (
            <Card className="p-6 border-signal-error/40">
              <div className="flex items-start gap-3">
                <AlertTriangle size={22} className="text-signal-error shrink-0 mt-0.5" />
                <div>
                  <h2 className="font-serif text-section-title font-semibold mb-1">
                    The model did not converge at this point
                  </h2>
                  <p className="text-body text-ink-soft mb-3 max-w-xl">
                    At the minimum titer and minimum downstream yield, the largest fermenter scale
                    produces a mass balance the cost engine cannot close — the plant cannot produce
                    enough product to justify the utilities it consumes, and the solver runs away.
                    Rather than show you a number from a failed solve, the workspace shows nothing.
                  </p>
                  <Button
                    variant="primary"
                    onClick={() => {
                      const target = lastConverged.current;
                      if (target) setScenarioPoint(scenario.id, target);
                      else
                        setScenarioPoint(
                          scenario.id,
                          Object.fromEntries(
                            scenario.dims.map((d) => [d.key, d.values[Math.floor(d.values.length / 2)]]),
                          ),
                        );
                    }}
                  >
                    Return to last converged point
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <>
              <Card className="p-4">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <Tick p="demo">
                    <div className="text-caption uppercase tracking-wide text-ink-soft">
                      Minimum selling price
                    </div>
                    <div
                      className={cx(
                        'font-num text-display leading-none transition-opacity',
                        converging !== null && 'opacity-40',
                      )}
                    >
                      ${result ? fmt(result.msp, 1) : '—'}
                      <span className="text-section-title text-ink-soft ml-1">/kg</span>
                    </div>
                    <div className="text-caption text-ink-soft mt-1">
                      Demo model v0 — illustrative economics, not validated
                    </div>
                  </Tick>

                  {converging !== null && (
                    <div className="flex items-center gap-2 text-body text-signal-info">
                      <span className="inline-block w-3 h-3 rounded-full border-2 border-signal-info border-t-transparent animate-spin" />
                      {CONVERGE_STAGES[converging]}…
                    </div>
                  )}
                </div>

                {result?.clamped && (
                  <div className="mt-3">
                    <Callout kind="warn">
                      Outside the modeled range — showing the nearest modeled point (
                      {scenario.dims
                        .map((d) => {
                          const lo = d.values[0];
                          const hi = d.values[d.values.length - 1];
                          const v = scenario.point[d.key];
                          if (v < lo) return `${fmt(lo)} ${d.unit}`;
                          if (v > hi) return `${fmt(hi)} ${d.unit}`;
                          return null;
                        })
                        .filter(Boolean)
                        .join(', ')}
                      ). The model is not extrapolated beyond its grid.
                    </Callout>
                  </div>
                )}
              </Card>

              {/* Waterfall */}
              <Card className="p-4">
                <h2 className="font-serif text-section-title font-semibold mb-1">Cost build-up</h2>
                <p className="text-caption text-ink-soft mb-3">
                  The six lines are computed together and sum to the headline exactly.
                </p>
                <div style={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={waterfall} margin={{ top: 5, right: 8, bottom: 40, left: 4 }}>
                      <CartesianGrid stroke={theme.grid} vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: theme.axis, fontSize: 11 }}
                        angle={-28}
                        textAnchor="end"
                        interval={0}
                        height={54}
                      />
                      <YAxis
                        tick={{ fill: theme.axis, fontSize: 11 }}
                        tickFormatter={(v) => `$${v}`}
                        width={52}
                      />
                      <Tooltip
                        {...tip}
                        formatter={(v: number, name: string) =>
                          name === 'value' ? [`$${v.toFixed(2)}/kg`, 'Contribution'] : null
                        }
                      />
                      <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
                      <Bar dataKey="value" stackId="w" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                        {waterfall.map((row, i) => (
                          <Cell
                            key={row.name}
                            fill={row.line === 'total' ? theme.accent : seriesColor(i)}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <ChartTable
                  headers={['Cost line', '$/kg', 'Share']}
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

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Tornado */}
                <Card className="p-4">
                  <h2 className="font-serif text-section-title font-semibold mb-1">
                    Sensitivity{' '}
                    <Explain label="How to read a tornado">
                      Each bar varies one assumption at a time by ±20% and plots the resulting swing
                      in MSP. Longer bars matter more. Asymmetric bars mean the risk is one-sided,
                      which is usually more decision-relevant than the length. One-at-a-time analysis
                      ignores interactions between assumptions.
                    </Explain>
                  </h2>
                  <p className="text-caption text-ink-soft mb-3">
                    Precomputed per model and evaluated at the model’s reference point — not at your
                    current slider position.
                  </p>
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={tornado}
                        layout="vertical"
                        margin={{ top: 4, right: 12, bottom: 4, left: 8 }}
                      >
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
                        <Bar dataKey="lowPct" name="−20%" fill={seriesColor(0)} isAnimationActive={false} />
                        <Bar dataKey="hiPct" name="+20%" fill={seriesColor(1)} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <ChartTable
                    headers={['Assumption', '−20%', '+20%']}
                    rows={tornado.map((t) => [
                      t.assumption,
                      `${t.lowPct.toFixed(1)}%`,
                      `${t.hiPct.toFixed(1)}%`,
                    ])}
                  />
                </Card>

                {/* Sweep */}
                <Card className="p-4">
                  <h2 className="font-serif text-section-title font-semibold mb-1">
                    MSP vs {primaryDim?.label}
                  </h2>
                  <p className="text-caption text-ink-soft mb-3">
                    {secondaryDim
                      ? `Small multiples hold ${primaryDim?.label.toLowerCase()} on the axis and step ${secondaryDim.label.toLowerCase()}.`
                      : 'Current point marked.'}
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
                          tick={{ fill: theme.axis, fontSize: 11 }}
                          tickFormatter={(v) => `$${v}`}
                          width={50}
                        />
                        <Tooltip
                          {...tip}
                          formatter={(v: number) => [`$${v.toFixed(1)}/kg`, 'MSP']}
                          labelFormatter={(l) => `${fmt(Number(l))} ${primaryDim?.unit}`}
                        />
                        {smallMultiples.length > 0
                          ? smallMultiples.map((sm, i) => (
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
                          : (
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
                    headers={[primaryDim?.label ?? 'x', 'MSP ($/kg)']}
                    rows={sweep
                      .filter((_, i) => i % 6 === 0)
                      .map((p) => [fmt(p.x), p.msp.toFixed(1)])}
                  />
                </Card>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Assumptions drawer */}
      <Sheet
        open={assumptionsOpen}
        onClose={() => setAssumptionsOpen(false)}
        title="Locked assumptions"
        width={640}
      >
        <p className="text-body text-ink-soft mb-4">
          Every row is either linked to a corpus record or explicitly labelled a demo assumption.
          Nothing here is left ambiguous.
        </p>
        <div className="space-y-2">
          {scenario.assumptions.map((a, i) => (
            <div key={i} className="card p-3">
              <div className="flex items-start justify-between gap-3">
                <Tick p={a.provenance} className="flex-1 min-w-0">
                  <div className="font-medium text-body">{a.label}</div>
                  <div className="font-num text-body">
                    {fmt(a.value)} <span className="text-ink-soft">{a.unit}</span>
                  </div>
                </Tick>
                <div className="shrink-0 flex flex-col items-end gap-1">
                  <ProvenanceBadge p={a.provenance} compact />
                  {a.recordId && <CitationChip recordId={a.recordId} />}
                </div>
              </div>
              <p className="text-caption text-ink-soft mt-1.5">{a.note}</p>
            </div>
          ))}
        </div>
      </Sheet>
    </div>
  );
}
