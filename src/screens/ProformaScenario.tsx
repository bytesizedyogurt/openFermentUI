// Scenario workspace (OF-DES-001 §8.13). Read it like an instrument: every
// assumption ticked, the waterfall always summing to the headline, and
// simulation treated as work rather than magic.
//
// OF-BLD-019 §3.2 (D1, D5, D6): the BioSTEAM page is THE scenario page. A
// seed BioSTEAM scenario and one a person made here with New scenario open
// the same page (BiosteamScenario, below): header, inputs with their sources,
// Run with the worker's status line, and every section of the newest run read
// from its one artifact (ProformaBiosteam.tsx). The authored branch
// (AuthoredScenario, the cost surfaces S1–S3 swept by src/engine/grids.ts)
// steps aside but is not deleted: it opens the archived casein examples,
// under their banner, and recharts stays allowed here for it alone.
//
// PROGRAMS (OF-BLD-016 §2.2). A scenario in an archived program has left
// Proforma's index, but its link still opens it here, under the banner that
// names the program and the switch, for an authored surface and a BioSTEAM
// scenario alike.
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
import { AlertTriangle, Copy, Download, GitCompare, Pin, PinOff, Play, Route, Table2, SlidersHorizontal } from 'lucide-react';
import { archivedProgramOf, useProgramLookup, useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import type { Artifact, CeilingCheck, CeilingRow, FermosFitInfo, FlowsheetInfo, InputAssumption, ProformaScenarioInfo, Scenario, ScenarioInput } from '@/data/types';
import { PROGRAM_BY_ID } from '@/data/programs';
import { durableAvailable } from '@/lib/durable';
import {
  FIT_TOOL_WORDS,
  ProformaDown,
  SIMULATOR_SAYS,
  ceilingCheck,
  fermosFits,
  fitsFrom,
  leftOutWords,
  modellerQuestions,
  newestRunId,
  proformaArtifact,
  proformaNewestRun,
  proformaBind,
  proformaScenarios,
  proformaShelf,
  proformaStatus,
  questionsText,
  runProformaScenario,
  runViewOfArtifact,
  runViewOfResult,
  stamp,
  type RunView,
  type SimulatorStatus,
} from '@/lib/proforma';
import { trainPath } from '@/lib/pureos';
import { inputSourceWords } from '@/components/NewScenarioDialog';
import { evaluateGrid, mspSweep, COST_LINES, COST_LINE_LABEL } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { exportCSV, exportText } from '@/lib/csv';
import { useChartTheme, useSeriesColor, tooltipStyle } from '@/lib/viz';
import { PageHeader, Card, Button, Sheet, Callout, cx, EmptyState } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { Tick, ProvenanceBadge } from '@/components/Provenance';
import { CEILING_NOTES, Tornado } from '@/components/figures';
import { ArchivedBanner } from '@/components/ArchivedBanner';
import { RunReport, SOURCE_WORDS, inputLabels } from './ProformaBiosteam';


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

function AuthoredScenario({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const grids = useStore((s) => s.grids);
  const setScenarioPoint = useStore((s) => s.setScenarioPoint);
  const togglePin = useStore((s) => s.togglePin);
  const duplicateScenario = useStore((s) => s.duplicateScenario);
  const toast = useStore((s) => s.toast);

  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const [activeDim, setActiveDim] = useState(0);
  const lastConverged = useRef<Record<string, number> | null>(null);

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
      else if (e.key === 'c') navigate('/biorepo/compare');
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
        action={<Button onClick={() => navigate('/proforma')}>Back to Proforma</Button>}
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

  const tornado = grid.sensitivity;

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
        ? [['Result', 'Minimum selling price', result.msp.toFixed(2), '$/kg', 'demo', '', 'Cost model v0 — illustrative, not validated']]
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
                navigate(`/proforma/scenario/${id}`);
                toast({ text: 'Scenario duplicated', kind: 'success' });
              }}
            >
              <Copy size={14} /> Duplicate
            </Button>
            <Button onClick={exportAll}>
              <Download size={14} /> Export CSV
            </Button>
            <Button onClick={() => navigate('/biorepo/compare')} title="Compare (c)">
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
              are linked to corpus records; the rest are labelled industry estimates or modelling assumptions.
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
                    <div className="font-num text-display leading-none">
                      ${result ? fmt(result.msp, 1) : '—'}
                      <span className="text-section-title text-ink-soft ml-1">/kg</span>
                    </div>
                    <div className="text-caption text-ink-soft mt-1">
                      Cost model v0 — illustrative economics, not validated
                    </div>
                  </Tick>

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
                {/* Tornado (§8.4: drawn by the figure grammar's Tornado) */}
                <div>
                  <Tornado
                    title="Which assumption moves the price most?"
                    drawn="Each bar varies one assumption at a time by ±20% and plots the swing in MSP, precomputed per model at its reference point, not at your slider position. One-at-a-time analysis ignores interactions."
                    series={['−20%', '+20%']}
                    unit="% change in MSP"
                    provenance="demo"
                    rows={tornado.map((t) => ({ label: t.assumption, values: [t.lowPct, t.hiPct], tag: 'authored' }))}
                    csvName={`${scenario.id}-tornado`}
                  />
                </div>

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
          Every row is either linked to a corpus record or explicitly labelled an industry estimate or a modelling assumption.
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

// ── The BioSTEAM scenario page (OF-BLD-014 §8.4; OF-BLD-019 §3.2) ───────
//
// ONE page for a seed BioSTEAM scenario and for one a person made here with
// New scenario (D6). It reads, and never types:
//
//   the shelf       the flowsheet's title, source, program and each input's
//                   dimension (GET /api/proforma/shelf, asked with archived
//                   programs: the page was opened by id);
//   the binding     a seed scenario from GET /api/proforma/scenarios, one
//                   made here from GET /api/proforma/bind?flowsheet= (the
//                   scenario run contract, src/lib/proforma.ts), each input
//                   bound to records, an artifact, a named person's
//                   assumption, or waiting; this browser's assumptions are
//                   laid over the inputs that wait, as the service lays them
//                   on the run;
//   the run         POST /api/proforma/run, one `proforma.run` artifact
//                   (D1); after a run the store keeps its id
//                   (recordScenarioRun), and on load the page reads the newest
//                   run back from GET /api/biorepo/artifacts/{id}. Every
//                   section under the Run (ProformaBiosteam.tsx) reads that
//                   one run.
//
// The program switch: the page asks for its own scenario's program even when
// the switch hides it, because a link opens what it names, under
// ArchivedBanner (useProgramScope's rule); anything of another archived
// program stays out. A binding the service refuses is said in its words, and
// the inputs the flowsheet takes are still listed from the shelf.

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** Where one input's value comes from, as the inputs table says it. */
function SourceCell({ input }: { input: ScenarioInput }) {
  const src = input.source;
  if (input.binding === 'records') {
    const n = input.records.length;
    const range = input.low == null || input.high == null || input.low === input.high ? fmt(input.value ?? Number.NaN, 4) : `${fmt(input.low, 4)}–${fmt(input.high, 4)}`;
    return (
      <div data-testid="source-records">
        <span className="chip">
          {n} record{n === 1 ? '' : 's'}, <span className="font-num">{range}</span>
          {input.unit && <span className="font-num">&nbsp;{input.unit}</span>}
        </span>
        <details className="mt-1">
          <summary className="text-caption text-ink-soft cursor-pointer hover:text-accent">{src?.note ?? 'the records'}</summary>
          <div className="flex flex-col gap-1 mt-1">
            {input.records.map((r) => (
              <span key={r.id} className="inline-flex flex-wrap items-center gap-1">
                <CitationChip recordId={r.id} paperId={r.paperId} />
                <span className="text-caption text-ink-soft">
                  {r.organism ?? 'organism not stated'} · {r.carbonSource ?? 'carbon source not stated'} ·{' '}
                  <span className="font-num">{fmt(r.value, 3)}</span>
                </span>
              </span>
            ))}
          </div>
        </details>
      </div>
    );
  }
  if (src?.kind === 'artifact' && src.id) {
    return (
      <a className="chip font-num hover:text-accent" href={href(`/biorepo/artifacts/${src.id}`)} data-testid="source-artifact">
        artifact {src.id}
        {src.note ? ` · ${src.note}` : ''}
      </a>
    );
  }
  if (input.binding === 'assumption' && src) {
    return (
      <span className="chip" data-testid="assumption-chip">
        assumption by {src.by ?? 'nobody named'} · <span className="font-num">{fmt(input.value ?? Number.NaN, 4)}</span>, low{' '}
        <span className="font-num">{fmt(input.low ?? Number.NaN, 4)}</span>, high <span className="font-num">{fmt(input.high ?? Number.NaN, 4)}</span>
        {src.note ? ` · ${src.note}` : ''}
      </span>
    );
  }
  if (src && input.binding !== 'waiting') {
    return (
      <span className="chip">
        {SOURCE_WORDS[src.kind] ?? src.kind}
        {src.note ? `: ${src.note}` : ''}
      </span>
    );
  }
  return <span className="chip text-signal-warn">waiting for a source</span>;
}

function AssumptionForm({ input, onSave }: { input: ScenarioInput; onSave: (a: { value: number; low: number; high: number; note: string }) => void }) {
  const [value, setValue] = useState('');
  const [low, setLow] = useState('');
  const [high, setHigh] = useState('');
  const [note, setNote] = useState('');
  const v = Number(value);
  const lo = Number(low);
  const hi = Number(high);
  const ok = value !== '' && low !== '' && high !== '' && [v, lo, hi].every(Number.isFinite) && lo <= v && v <= hi;
  return (
    <div className="flex flex-wrap items-end gap-2 mt-1" data-testid={`assume-${input.key}`}>
      {(
        [
          ['Value', value, setValue],
          ['Low', low, setLow],
          ['High', high, setHigh],
        ] as const
      ).map(([label, val, set]) => (
        <label key={label} className="text-caption text-ink-soft">
          <span className="block">{label}</span>
          <input className="input w-[88px] font-num" inputMode="decimal" aria-label={`${input.label} ${label.toLowerCase()}`} value={val} onChange={(e) => set(e.target.value)} />
        </label>
      ))}
      <label className="text-caption text-ink-soft flex-1 min-w-[140px]">
        <span className="block">What it rests on</span>
        <input className="input w-full" aria-label={`${input.label} basis`} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <Button disabled={!ok} onClick={() => onSave({ value: v, low: lo, high: hi, note })}>
        Keep assumption
      </Button>
    </div>
  );
}

function InputsTable({
  inputs,
  flowsheet,
  onAssume,
  onClear,
  onClearFit,
}: {
  inputs: ScenarioInput[];
  flowsheet: FlowsheetInfo | null;
  onAssume: (key: string, a: { value: number; low: number; high: number; note: string }) => void;
  onClear: (key: string) => void;
  onClearFit: (key: string) => void;
}) {
  const reviewer = useStore((s) => s.reviewer);
  const declared = new Map((flowsheet?.inputs ?? []).map((i) => [i.key, i]));
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-body" data-testid="proforma-inputs">
        <thead>
          <tr className="text-caption text-ink-soft text-left">
            <th className="py-1 pr-2 font-medium">Input</th>
            <th className="py-1 pr-2 font-medium">Dimension</th>
            <th className="py-1 pr-2 font-medium">Unit</th>
            <th className="py-1 pr-2 font-medium">Value</th>
            <th className="py-1 font-medium">Source</th>
          </tr>
        </thead>
        <tbody>
          {inputs.map((i) => (
            <tr key={i.key} className="border-t border-line/60 align-top" data-testid={`input-${i.key}`}>
              <td className="py-1.5 pr-2">
                <div className="font-medium">{i.label}</div>
                {declared.get(i.key)?.note && <div className="text-caption text-ink-soft">{declared.get(i.key)?.note}</div>}
              </td>
              <td className="py-1.5 pr-2 text-caption">{declared.get(i.key)?.dimension ?? '—'}</td>
              <td className="py-1.5 pr-2 font-num text-caption">{i.unit || 'share'}</td>
              <td className="py-1.5 pr-2 font-num">
                {i.value == null ? '—' : fmt(i.value, 4)}
                {i.sampling && <div className="text-caption text-ink-soft">{i.sampling}</div>}
              </td>
              <td className="py-1.5">
                <SourceCell input={i} />
                {i.flags.map((f) => (
                  <div key={f} className="text-caption text-signal-warn">
                    {f}
                  </div>
                ))}
                {(i.leftOutNoCarbon > 0 || i.leftOutOtherCarbon > 0) && (
                  <div className="text-caption text-ink-soft">
                    {leftOutWords(i, flowsheet?.id ?? null)}
                  </div>
                )}
                {i.binding === 'assumption' && (
                  <button className="text-caption text-ink-soft hover:text-accent underline" onClick={() => onClear(i.key)}>
                    Withdraw this assumption
                  </button>
                )}
                {i.binding === 'artifact' && (
                  <button className="text-caption text-ink-soft hover:text-accent underline" onClick={() => onClearFit(i.key)}>
                    Stop using the fermOS fit here
                  </button>
                )}
                {i.binding === 'waiting' &&
                  (reviewer.trim() ? (
                    <AssumptionForm input={i} onSave={(a) => onAssume(i.key, a)} />
                  ) : (
                    <div className="text-caption text-ink-soft">
                      An assumption carries a person's name: set yours in{' '}
                      <a className="text-accent hover:underline" href={href('/settings/corpus')}>
                        Settings
                      </a>{' '}
                      to type one.
                    </div>
                  ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Use a fermOS fit (OF-BLD-019 §5.1, D10). A source, not a copy: the fits
 * fermOS keeps (GET /api/fermos/fits) are listed with their provenance, the
 * run each was fitted to and what each can feed this flowsheet's titre,
 * yield and productivity, each value as the service computed it from the
 * artifact, or why not, in its words. Choosing one keeps which artifact
 * feeds which input (`proformaFits`, Durable, like assumptions), and the
 * binding then names it as the inputs' source. A fit sent from fermOS →
 * Forecast arrives as `?fit=` and is attached here, once, for the inputs it
 * can feed. With no fit on file it says how one gets made.
 */
function FermosFitSlot({
  flowsheetId,
  chosen,
  onChoose,
  onStop,
}: {
  flowsheetId: string;
  chosen: Record<string, string>;
  onChoose: (fits: Record<string, string>) => void;
  /** Stop using these artifacts: only the inputs each feeds are cleared (§5.R). */
  onStop: (artifactIds: string[]) => void;
}) {
  const route = useRoute();
  const sent = route.query.get('fit');
  const [fits, setFits] = useState<FermosFitInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [arrived, setArrived] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setFits(null);
    setProblem(null);
    fermosFits(flowsheetId, ctrl.signal)
      .then(setFits)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [flowsheetId]);

  // A fit sent from fermOS → Forecast: attached once, for the inputs it can
  // feed, then the address loses its ?fit= so a reload attaches nothing.
  useEffect(() => {
    if (!sent || !fits) return;
    const found = fits.find((f) => f.artifactId === sent);
    const feeds = found ? fitsFrom(found) : {};
    if (Object.keys(feeds).length > 0) onChoose(feeds);
    setArrived(
      !found
        ? `${sent} was sent from fermOS, but it is not a kinetic fit or forecast on file here.`
        : Object.keys(feeds).length > 0
          ? `${FIT_TOOL_WORDS[found.tool] ?? found.tool} ${sent}, sent from fermOS, now feeds ${Object.keys(feeds).join(', ')}.`
          : `${FIT_TOOL_WORDS[found.tool] ?? found.tool} ${sent} was sent from fermOS, but it feeds nothing here: ${found.refused ?? found.feeds.map((f) => `${f.key}: ${f.refused}`).join('; ')}`,
    );
    navigate(route.path, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sent, fits]);

  const using = new Set(Object.values(chosen));
  const missing = [...using].filter((id) => fits && !fits.some((f) => f.artifactId === id));
  return (
    <div className="mt-4 border-t border-line/60 pt-3" data-testid="fermos-fit-slot">
      <h3 className="font-medium text-body">Use a fermOS fit</h3>
      <p className="text-caption text-ink-soft mb-2">
        A fit of a deposited run can give the fermenter its titre, its yield on sugar and its batch time. The service computes each
        from the fit&rsquo;s forecast, drawn again to the hour its median sugar runs out (found between the forecast&rsquo;s points, so
        the length it was asked to run does not move them): titre from the final product, yield from product made over sugar used,
        and productivity as that titre over that hour. A fit&rsquo;s productivity feeds the fermenter only beside its own titre, since
        the batch time is the titre over the productivity. The run then names the fit as the source of each.
      </p>
      {arrived && (
        <p className="text-caption mb-2" data-testid="fermos-fit-arrived">
          {arrived}
        </p>
      )}
      {problem && <p className="text-caption text-signal-warn">The fits fermOS keeps could not be read: {problem}</p>}
      {!problem && fits === null && <p className="text-caption text-ink-soft">Reading the fits fermOS keeps…</p>}
      {fits !== null && fits.length === 0 && (
        <p className="text-caption" data-testid="fermos-fit-none">
          No fermOS fit is on file yet. One is made from a run: deposit its readings in{' '}
          <a className="text-accent hover:underline" href={href('/runbooks/depositions')}>
            Runbooks → Depositions
          </a>{' '}
          (the time of each sample, biomass at four or more times, product and sugar at the same times), then fit it in{' '}
          <a className="text-accent hover:underline" href={href('/fermos')}>
            fermOS
          </a>
          . A forecast on{' '}
          <a className="text-accent hover:underline" href={href('/fermos/forecast')}>
            fermOS → Forecast
          </a>{' '}
          run until the sugar is spent gives the batch time as well.
        </p>
      )}
      {missing.length > 0 && (
        <p className="text-caption text-signal-warn">
          The fit this scenario uses, {missing.join(', ')}, is not on file here any more.{' '}
          <button className="underline hover:text-accent" onClick={() => onStop(missing)}>
            Stop using it
          </button>
        </p>
      )}
      {fits !== null && fits.length > 0 && (
        <ul className="space-y-2">
          {fits.map((f) => {
            const feeds = fitsFrom(f);
            const inUse = using.has(f.artifactId);
            return (
              <li key={f.artifactId} className="card p-3" data-testid="fermos-fit-option" data-artifact={f.artifactId} data-feeds={Object.keys(feeds).length}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{FIT_TOOL_WORDS[f.tool] ?? f.tool}</span>
                  <a className="font-num text-caption hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${f.artifactId}`)}>
                    {f.artifactId}
                  </a>
                  <ProvenanceBadge p={f.provenance} />
                  <span className="text-caption text-ink-soft">
                    run {f.depositionId ?? 'not named'}
                    {f.productSeries && <> · product: {f.productSeries}</>}
                    {f.substrateSeries && <> · sugar: {f.substrateSeries}</>}
                  </span>
                </div>
                <ul className="text-caption mt-1">
                  {f.feeds.map((x) => (
                    <li key={x.key} data-testid="fermos-fit-feed" data-key={x.key}>
                      <span className="font-medium">{x.key}</span>:{' '}
                      {x.refused || x.value == null ? (
                        <span className="text-ink-soft">{x.refused}</span>
                      ) : (
                        <>
                          <span className="font-num">{fmt(x.value, 4)}</span> {x.unit} (
                          <span className="font-num">
                            {fmt(x.low ?? Number.NaN, 4)}–{fmt(x.high ?? Number.NaN, 4)}
                          </span>
                          )
                        </>
                      )}
                    </li>
                  ))}
                </ul>
                {f.batchTimeH != null && (
                  <div className="text-caption text-ink-soft">
                    Batch time <span className="font-num">{fmt(f.batchTimeH, 4)}</span> h, where the forecast&rsquo;s median sugar runs out.
                  </div>
                )}
                {f.flags.map((w) => (
                  <div key={w} className="text-caption text-signal-warn">
                    {w}
                  </div>
                ))}
                <div className="mt-2">
                  {inUse ? (
                    <span className="text-caption">
                      In use for {Object.entries(chosen).filter(([, id]) => id === f.artifactId).map(([k]) => k).join(', ')}.{' '}
                      <button className="underline hover:text-accent" onClick={() => onStop([f.artifactId])} data-testid="fermos-fit-stop">
                        Stop using this fit
                      </button>
                    </span>
                  ) : (
                    <Button onClick={() => onChoose(feeds)} disabled={Object.keys(feeds).length === 0} data-testid="fermos-fit-use">
                      Use this fit for {Object.keys(feeds).join(', ') || 'nothing it can feed'}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** How a ceiling-check row's flag reads in its chip. */
const CEILING_FLAG_WORDS: Record<CeilingRow['flag'], string> = {
  above: 'Above the ceiling: check the basis',
  within: 'At or under the ceiling',
  'no-yield': 'No yield to read yet',
};

/** A g g⁻¹ or mol mol⁻¹ value, or a dash where there is none. */
const ceilingNum = (v: number | null | undefined, digits = 4) => (v == null ? '—' : fmt(v, digits));

/** The scenario's yield as the check read it: where it comes from. */
function CeilingYieldSource({ check }: { check: CeilingCheck }) {
  const src = check.yieldSource;
  if (check.yieldBinding === 'records')
    return (
      <span className="chip" data-testid="ceiling-yield-source" data-binding="records">
        {check.yieldRecords} record{check.yieldRecords === 1 ? '' : 's'}
      </span>
    );
  if (check.yieldBinding === 'assumption')
    return (
      <span className="chip" data-testid="ceiling-yield-source" data-binding="assumption">
        assumption by {src?.by ?? 'a named person'}
      </span>
    );
  if (check.yieldBinding === 'artifact' && src?.id)
    return (
      <a className="chip hover:text-accent" href={href(`/biorepo/artifacts/${src.id}`)} data-testid="ceiling-yield-source" data-binding="artifact">
        fermOS fit {src.id}
      </a>
    );
  return (
    <span className="chip" data-testid="ceiling-yield-source" data-binding={check.yieldBinding}>
      waiting
    </span>
  );
}

/**
 * The ceiling check (OF-BLD-019 §5.2, D11): the fermenter's yield, as this
 * scenario binds it, beside the newest stored geneOS ceiling of each shelf
 * model of its organism, on its flowsheet's sugar, both on the ceiling's own
 * footing (g per g, and mol per mol at its conventions), as the service
 * computes it on read. A yield above a ceiling is flagged in words for a
 * reviewer; nothing is clamped and the run keeps the yield as bound. With no
 * ceiling on file it says so and links to where one is computed.
 */
function CeilingCheckSlot({ check, problem }: { check: CeilingCheck | null; problem: string | null }) {
  if (!check && !problem) return null;
  return (
    <Card className={cx('p-4', check?.flagged && 'border-signal-warn/50')} data-testid="ceiling-check" data-flagged={check?.flagged ? 'true' : 'false'}>
      <h2 className="font-serif text-section-title font-semibold mb-1">Ceiling check</h2>
      <p className="text-caption text-ink-soft mb-2">
        The fermenter&rsquo;s yield beside the most a published reaction network of its organism can make from its sugar, as geneOS
        computed and kept it. A flag, never a bound: a yield above a ceiling is marked for a reviewer to check its basis, and the run
        keeps the yield as bound.
      </p>
      {problem && (
        <p className="text-caption text-signal-warn" data-testid="ceiling-problem">
          The ceiling check could not be read: {problem}
        </p>
      )}
      {check && (
        <div className="space-y-3">
          <div className="text-body" data-testid="ceiling-yield">
            <span className="font-medium">The scenario&rsquo;s yield: </span>
            {check.yieldValue == null ? (
              <span className="text-ink-soft">none yet</span>
            ) : (
              <>
                <span className="font-num">{fmt(check.yieldValue, 4)}</span>
                {check.yieldLow != null && check.yieldHigh != null && check.yieldLow !== check.yieldHigh && (
                  <span className="font-num">
                    {' '}
                    ({fmt(check.yieldLow, 4)}–{fmt(check.yieldHigh, 4)})
                  </span>
                )}{' '}
                <span className="font-num">{check.yieldUnit}</span>
              </>
            )}{' '}
            <CeilingYieldSource check={check} /> <span className="text-caption text-ink-soft">{check.yieldWords}.</span>
          </div>
          <p className="text-caption text-ink-soft" data-testid="ceiling-organism">
            Organism: {check.organismWords}. Sugar: {check.sugarWords}.
          </p>
          {check.rows.length === 0 && check.empty && (
            <p className="text-body" data-testid="ceiling-empty">
              {check.empty}{' '}
              <a className="text-accent hover:underline" href={href(check.computeAt)} data-testid="ceiling-compute">
                Open geneOS → Model
              </a>
            </p>
          )}
          {check.rows.map((r) => (
            <div
              key={r.artifactId}
              className={cx('rounded-card border p-3', r.flag === 'above' ? 'border-signal-warn/45 bg-signal-warn/[0.06]' : 'border-line')}
              data-testid="ceiling-row"
              data-model={r.modelId}
              data-flag={r.flag}
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="font-medium">{r.modelName}</span>
                <span className={cx('chip', r.flag === 'above' && 'text-signal-warn')} data-testid="ceiling-flag">
                  {CEILING_FLAG_WORDS[r.flag]}
                </span>
              </div>
              <table className="w-full text-body">
                <thead>
                  <tr className="text-caption text-ink-soft text-left">
                    <th className="py-1 pr-2 font-medium" />
                    <th className="py-1 pr-2 font-medium">g {r.product} per g {r.substrate}</th>
                    <th className="py-1 pr-2 font-medium">mol per mol</th>
                    <th className="py-1 font-medium">Its basis</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-line/60 align-top" data-testid="ceiling-ceiling">
                    <td className="py-1.5 pr-2">Ceiling, {r.modelId} on {r.substrate}</td>
                    <td className="py-1.5 pr-2 font-num" data-testid="ceiling-value">
                      {fmt(r.ceilingGPerG, 4)}
                    </td>
                    <td className="py-1.5 pr-2 font-num">{ceilingNum(r.ceilingMolPerMol)}</td>
                    <td className="py-1.5 text-caption">
                      <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/biorepo/artifacts/${r.artifactId}`)} data-testid="ceiling-artifact">
                        {r.artifactId}
                      </a>{' '}
                      <ProvenanceBadge p={r.provenance} /> {r.modelBasis}, kept {stamp(r.createdAt)}
                      {r.older > 0 && `; the newest of ${r.older + 1} on file`}
                    </td>
                  </tr>
                  <tr className="border-t border-line/60 align-top" data-testid="ceiling-scenario">
                    <td className="py-1.5 pr-2">This scenario&rsquo;s yield</td>
                    <td className="py-1.5 pr-2 font-num">
                      {ceilingNum(r.yieldGPerG)}
                      {r.yieldLowGPerG != null && r.yieldHighGPerG != null && r.yieldLowGPerG !== r.yieldHighGPerG && (
                        <span className="text-caption">
                          {' '}
                          ({fmt(r.yieldLowGPerG, 4)}–{fmt(r.yieldHighGPerG, 4)})
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 pr-2 font-num">{ceilingNum(r.yieldMolPerMol)}</td>
                    <td className="py-1.5 text-caption">{check.yieldWords}, at the ceiling&rsquo;s conventions</td>
                  </tr>
                </tbody>
              </table>
              <p className="text-body mt-2" data-testid="ceiling-words">
                {r.words}
              </p>
              {r.recordsAbove.length > 0 && (
                <ul className="text-caption mt-1 space-y-0.5">
                  {r.recordsAbove.map((id) => (
                    <li key={id} data-testid="ceiling-record-above">
                      <span className="font-num">{id}</span> is above this ceiling.{' '}
                      <a className="text-accent hover:underline" href={href(`/guild?record=${id}`)}>
                        Ask a reviewer to check its basis
                      </a>
                      .
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-caption text-ink-soft mt-1">{r.matchWords}.</p>
              {r.conventions.length > 0 && (
                <details className="mt-1">
                  <summary className="text-caption text-ink-soft cursor-pointer hover:text-accent">The conventions the ceiling&rsquo;s basis names</summary>
                  <ul className="text-caption text-ink-soft mt-1">
                    {r.conventions.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}
          {check.otherSugars.length > 0 && (
            <p className="text-caption text-ink-soft">
              Ceilings of {check.models.join(', ')} on {check.otherSugars.join(', ')} are on file too; this scenario&rsquo;s sugar is{' '}
              {check.substrate}, so they are left aside.
            </p>
          )}
          <ul className="text-caption text-ink-soft space-y-0.5">
            {check.rows.length > 0 && CEILING_NOTES.map((n) => <li key={n}>{n}</li>)}
            {check.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

/** The worker's status in words, with the seconds a run in hand has taken. */
function StatusLine({ status, problem, running, elapsed }: { status: SimulatorStatus | null; problem: string | null; running: boolean; elapsed: number }) {
  return (
    <span className="text-caption text-ink-soft" data-testid="run-status" data-status={status?.status ?? 'unknown'}>
      {status ? SIMULATOR_SAYS[status.status] : problem ? `The simulator's status could not be read: ${problem}` : "Asking the service for the simulator's status."}
      {status?.error && ` ${status.error}`}
      {running && (
        <>
          {' '}
          Running for <span className="font-num">{elapsed}</span> s.
        </>
      )}
    </span>
  );
}

function BiosteamScenario({ scenario, madeHere }: { scenario: Scenario; madeHere: boolean }) {
  const assumptions = useStore((s) => s.proformaAssumptions[scenario.id]) ?? EMPTY;
  const setAssumption = useStore((s) => s.setProformaAssumption);
  const clearAssumption = useStore((s) => s.clearProformaAssumption);
  const chosenFits = useStore((s) => s.proformaFits[scenario.id]) ?? EMPTY_FITS;
  const setFits = useStore((s) => s.setProformaFits);
  const clearFit = useStore((s) => s.clearProformaFit);
  const togglePin = useStore((s) => s.togglePin);
  const recordScenarioRun = useStore((s) => s.recordScenarioRun);
  const reviewer = useStore((s) => s.reviewer);
  const showArchived = useStore((s) => s.showArchived);
  const lookup = useProgramLookup();
  const ownArchived = archivedProgramOf('scenario', scenario.id, lookup) !== null;
  const includeArchived = showArchived || ownArchived;
  const flowsheetId = scenario.flowsheetId ?? scenario.modelId;

  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [shelfProblem, setShelfProblem] = useState<string | null>(null);
  const [host, setHost] = useState<string | null>(null);
  const [info, setInfo] = useState<ProformaScenarioInfo | null>(null);
  const [bindProblem, setBindProblem] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [statusProblem, setStatusProblem] = useState<string | null>(null);
  const [view, setView] = useState<RunView | null>(null);
  const [loadProblem, setLoadProblem] = useState<string | null>(null);
  const [runProblem, setRunProblem] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [ceiling, setCeiling] = useState<CeilingCheck | null>(null);
  const [ceilingProblem, setCeilingProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    proformaShelf(true, ctrl.signal)
      .then(setShelf)
      .catch((e: unknown) => !ctrl.signal.aborted && setShelfProblem(problemOf(e)));
    proformaStatus(ctrl.signal)
      .then(setStatus)
      .catch((e: unknown) => !ctrl.signal.aborted && setStatusProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);

  // The binding: a seed scenario by (b), one made here by its flowsheet (c);
  // with a fermOS fit chosen, either by (c) with the fits (OF-BLD-019 §5.1),
  // which binds a seed scenario's flowsheet exactly as (b) does.
  const fitsKey = JSON.stringify(Object.entries(chosenFits).sort());
  useEffect(() => {
    const ctrl = new AbortController();
    setInfo(null);
    setBindProblem(null);
    const fits = Object.fromEntries(JSON.parse(fitsKey) as [string, string][]);
    const ask = { host, includeArchived };
    const bound =
      madeHere || Object.keys(fits).length > 0
        ? proformaBind(flowsheetId, { ...ask, fits }, ctrl.signal)
        : proformaScenarios(ask, ctrl.signal).then((all) => {
            const found = all.find((x) => x.id === scenario.id);
            if (!found) throw new Error(`The service binds no scenario ${scenario.id}: it is not among the BioSTEAM scenarios this service holds.`);
            return found;
          });
    bound.then(setInfo).catch((e: unknown) => !ctrl.signal.aborted && setBindProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [madeHere, flowsheetId, scenario.id, host, includeArchived, fitsKey]);

  // The ceiling check (OF-BLD-019 §5.2, D11): the yield as this page binds
  // it (host, fits, and the yield's assumption when a person typed one),
  // read by the service against the newest stored geneOS ceilings.
  const yieldAssumed = JSON.stringify(assumptions.filter((a) => a.key === 'yield'));
  useEffect(() => {
    const ctrl = new AbortController();
    setCeiling(null);
    setCeilingProblem(null);
    const fits = Object.fromEntries(JSON.parse(fitsKey) as [string, string][]);
    ceilingCheck(
      { scenarioId: scenario.id, flowsheet: madeHere ? flowsheetId : null, host, includeArchived, fits, assumptions: JSON.parse(yieldAssumed) as InputAssumption[] },
      ctrl.signal,
    )
      .then(setCeiling)
      .catch((e: unknown) => !ctrl.signal.aborted && setCeilingProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [madeHere, flowsheetId, scenario.id, host, includeArchived, fitsKey, yieldAssumed]);


  // The newest run: the service's, which holds every run any browser, the
  // API or Postdoc made of this scenario (§3.R, findings 8 and 21), else the
  // one this browser kept (D6), read back from its artifact. `served` is
  // undefined until the service answers.
  const [served, setServed] = useState<Artifact | null | undefined>(undefined);
  useEffect(() => {
    const ctrl = new AbortController();
    proformaNewestRun(scenario.id, ctrl.signal)
      .then(setServed)
      .catch(() => !ctrl.signal.aborted && setServed(null));
    return () => ctrl.abort();
  }, [scenario.id]);
  const runId = newestRunId(served, scenario.lastRunId);
  useEffect(() => {
    setLoadProblem(null);
    if (!runId) return;
    if (served && served.id === runId) {
      const v = runViewOfArtifact(served);
      if (v) setView(v);
      else setLoadProblem(`${runId} is not a scenario run: it was kept by ${served.tool}.`);
      return;
    }
    const ctrl = new AbortController();
    proformaArtifact(runId, ctrl.signal)
      .then((art) => {
        const v = runViewOfArtifact(art);
        if (v) setView(v);
        else setLoadProblem(`${runId} is not a scenario run: it was kept by ${art.tool}.`);
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setLoadProblem(problemOf(e)));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, served]);

  // While a run is in hand: its seconds.
  useEffect(() => {
    if (!running) return;
    const t0 = Date.now();
    setElapsed(0);
    const tick = window.setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => window.clearInterval(tick);
  }, [running]);

  // While a run is in hand, or the simulator is starting, the worker's
  // status every few seconds: Run waits while it starts (§3.R, finding 7),
  // and comes back when it is ready.
  const starting = status?.status === 'starting';
  useEffect(() => {
    if (!running && !starting) return;
    const poll = window.setInterval(() => {
      proformaStatus()
        .then(setStatus)
        .catch(() => {
          /* the line keeps the last status it read */
        });
    }, 3000);
    return () => window.clearInterval(poll);
  }, [running, starting]);

  const flowsheet = shelf?.find((f) => f.id === flowsheetId) ?? null;

  // What the service bound, with this browser's assumptions laid over the
  // inputs that wait for one; the service applies the same rule on the run.
  const bound = useMemo<ProformaScenarioInfo | null>(() => {
    if (!info) return null;
    const by = new Map(assumptions.map((a) => [a.key, a]));
    const inputs = info.inputs.map((i): ScenarioInput => {
      const a = by.get(i.key);
      if (i.binding !== 'waiting' || !a) return i;
      return {
        ...i,
        binding: 'assumption',
        value: a.value,
        low: a.low,
        high: a.high,
        sampling: a.low === a.high ? 'fixed' : 'uniform',
        source: { kind: 'assumption', id: null, by: a.by, note: `typed on ${a.at}${a.note ? `: ${a.note}` : ''}` },
      };
    });
    return { ...info, id: scenario.id, name: scenario.name, inputs, waiting: inputs.filter((i) => i.binding === 'waiting').map((i) => i.key) };
  }, [info, assumptions, scenario.id, scenario.name]);

  const priceBasis = bound?.priceBasis || flowsheet?.priceBasis || 'on the basis its flowsheet states';
  const labels = inputLabels(bound?.inputs ?? null, flowsheet);
  const unitLabels = inputLabels(bound?.inputs ?? null, flowsheet, true);
  const programId = scenario.program ?? (flowsheet?.program as Scenario['program'] | null | undefined) ?? null;
  const program = programId ? PROGRAM_BY_ID[programId] : null;
  const today = new Date().toISOString().slice(0, 10);

  const go = () => {
    if (!bound) return;
    setRunning(true);
    setRunProblem(null);
    const used = assumptions.filter((a) => bound.inputs.find((i) => i.key === a.key)?.binding === 'assumption');
    const fits = Object.fromEntries(Object.entries(chosenFits).filter(([k]) => bound.inputs.find((i) => i.key === k)?.binding === 'artifact'));
    runProformaScenario({ scenarioId: scenario.id, flowsheet: madeHere ? flowsheetId : null, assumptions: used, host, fits })
      .then((r) => {
        setView(runViewOfResult(r));
        // The index and this page read the newest run from its artifact (D6).
        recordScenarioRun(scenario.id, r.artifactId);
      })
      .catch((e: unknown) => setRunProblem(problemOf(e)))
      .finally(() => {
        setRunning(false);
        proformaStatus()
          .then(setStatus)
          .catch(() => {
            /* the line keeps the last status it read */
          });
      });
  };

  const questions = bound ? modellerQuestions(bound.inputs, view, flowsheetId) : [];

  return (
    <div data-testid="proforma-biosteam">
      <PageHeader
        eyebrow={`${flowsheetId} · BioSTEAM scenario`}
        title={scenario.name}
        subtitle={scenario.description || (flowsheet ? `${flowsheet.title}, from ${flowsheet.source}` : `Flowsheet ${flowsheetId}`)}
        actions={
          <>
            <Button onClick={() => togglePin(scenario.id)} title="Pin to compare" data-testid="scenario-pin" aria-pressed={scenario.pinned}>
              {scenario.pinned ? <Pin size={14} /> : <PinOff size={14} />}
              {scenario.pinned ? 'Pinned' : 'Pin'}
            </Button>
            <a className="btn" href={href('/biorepo/compare')} data-testid="compare-link">
              <GitCompare size={14} /> Compare
            </a>
            {view && (
              <a className="btn" href={href(trainPath({ scenarioId: null, artifactId: view.artifactId }))} data-testid="train-link">
                <Route size={14} /> pureOS train
              </a>
            )}
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4 text-caption text-ink-soft" data-testid="scenario-meta">
        <span>
          Flowsheet: <span className="text-ink">{flowsheet ? flowsheet.title : flowsheetId}</span>
          {flowsheet && <>, from {flowsheet.source}</>}
        </span>
        <span>· Program: <span className="text-ink">{program ? program.name : 'none (general)'}</span></span>
        <span>· {madeHere ? `made in this browser${scenario.createdAt ? ` ${stamp(scenario.createdAt)}` : ''}` : 'shipped with openFerment'}</span>
        {view ? <ProvenanceBadge p={view.provenance} /> : <span className="chip">not run yet</span>}
      </div>

      {(shelfProblem || (shelf && !flowsheet)) && (
        <div className="mb-4">
          {shelfProblem && <Callout kind="warn">The shelf could not be read: {shelfProblem}</Callout>}
          {shelf && !flowsheet && (
            <Callout kind="warn">The service&rsquo;s shelf holds no flowsheet {flowsheetId}, so this scenario cannot run on it.</Callout>
          )}
        </div>
      )}

      <div className="space-y-4">
        {!view && !runId && served !== undefined && (
          <Card className="p-4" data-testid="scenario-not-run">
            <h2 className="font-serif text-section-title font-semibold mb-1">This scenario has not run yet</h2>
            <p className="text-body text-ink-soft">
              {madeHere
                ? `Made in this browser${scenario.createdAt ? ` on ${stamp(scenario.createdAt)}` : ''}${program ? `, in ${program.name}` : ''}. `
                : ''}
              Neither this browser nor the service holds a run of it. It holds no input value of its own: a run binds its process inputs to
              records and takes every other input from a named person&rsquo;s assumption. Give every input that waits a source, then run it.
            </p>
          </Card>
        )}

        <Card className="p-4">
          <div className="flex flex-wrap items-end justify-between gap-3 mb-2">
            <h2 className="font-serif text-section-title font-semibold">Inputs, and where each came from</h2>
            {bound && bound.hosts.length > 0 && (
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Host</span>
                <select className="input" aria-label="Host" value={host ?? ''} onChange={(e) => setHost(e.target.value || null)}>
                  <option value="">Every organism the binding reads</option>
                  {bound.hosts.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {flowsheet && <p className="text-caption text-ink-soft mb-2">{flowsheet.description}</p>}
          <p className="text-caption text-ink-soft mb-3">
            Records of an input&rsquo;s field pass the same gate statistics pass. Three or more give their median and range, sampled
            triangular; two a pair, sampled uniform; one is held fixed. Every other input is a named person&rsquo;s assumption, or a
            convention the run states.
          </p>
          {bindProblem && (
            <Callout kind="warn">
              <span data-testid="bind-problem">The service could not bind this scenario&rsquo;s inputs: {bindProblem}</span>
            </Callout>
          )}
          {bound ? (
            <InputsTable
              inputs={bound.inputs}
              flowsheet={flowsheet}
              onAssume={(key, a) => setAssumption(scenario.id, { key, ...a, by: reviewer.trim(), at: today, note: a.note || null } satisfies InputAssumption)}
              onClear={(key) => clearAssumption(scenario.id, key)}
              onClearFit={(key) => clearFit(scenario.id, key)}
            />
          ) : (
            flowsheet &&
            bindProblem && (
              <table className="w-full text-body mt-2" data-testid="shelf-inputs">
                <thead>
                  <tr className="text-caption text-ink-soft text-left">
                    <th className="py-1 pr-2 font-medium">Input the flowsheet takes</th>
                    <th className="py-1 pr-2 font-medium">Dimension</th>
                    <th className="py-1 pr-2 font-medium">Unit</th>
                    <th className="py-1 font-medium">Where it comes from</th>
                  </tr>
                </thead>
                <tbody>
                  {flowsheet.inputs.map((i) => (
                    <tr key={i.key} className="border-t border-line/60 align-top">
                      <td className="py-1.5 pr-2">{i.name}</td>
                      <td className="py-1.5 pr-2 text-caption">{i.dimension}</td>
                      <td className="py-1.5 pr-2 font-num text-caption">{i.unit || 'share'}</td>
                      <td className="py-1.5 text-caption">{inputSourceWords(i)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
          {flowsheet && flowsheet.inputs.some((i) => FIT_INPUTS.includes(i.key)) && (
            <FermosFitSlot
              flowsheetId={flowsheetId}
              chosen={chosenFits}
              onChoose={(fits) => setFits(scenario.id, fits)}
              onStop={(ids) =>
                Object.entries(chosenFits)
                  .filter(([, id]) => ids.includes(id))
                  .forEach(([key]) => clearFit(scenario.id, key))
              }
            />
          )}
          <div className="mt-3 text-caption text-ink-soft">
            <div>The price is {priceBasis}.</div>
            {(bound?.leavesOut ?? flowsheet?.leavesOut ?? []).length > 0 && (
              <div>What this flowsheet leaves out: {(bound?.leavesOut ?? flowsheet?.leavesOut ?? []).join('; ')}.</div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button variant="primary" onClick={go} disabled={running || starting || !bound || bound.waiting.length > 0}>
              <Play size={14} /> {running ? 'Simulating…' : view ? 'Run the scenario again' : 'Run the scenario'}
            </Button>
            <StatusLine status={status} problem={statusProblem} running={running} elapsed={elapsed} />
            {starting && !running && (
              <span className="text-caption text-ink-soft" data-testid="run-waits">
                Run waits until it has started; this line asks again every few seconds.
              </span>
            )}
          </div>
          {bound && bound.waiting.length > 0 && (
            <p className="text-caption text-signal-warn mt-2" data-testid="proforma-waiting">
              Waiting for a source: {bound.waiting.map((k) => bound.inputs.find((i) => i.key === k)?.label ?? k).join(', ')}.
            </p>
          )}
          {runProblem && (
            <div className="mt-2">
              <Callout kind="warn">
                <span data-testid="run-problem">The run was refused: {runProblem}</span>
              </Callout>
            </div>
          )}
        </Card>

        <CeilingCheckSlot check={ceiling} problem={ceilingProblem} />

        {runId && loadProblem && !view && (
          <Callout kind="warn">
            Its newest run, {runId}, could not be read: {loadProblem}
          </Callout>
        )}

        {view && (
          <RunReport view={view} priceBasis={priceBasis} labels={labels} unitLabels={unitLabels} scenarioId={scenario.id} csvName={scenario.id} flowsheet={flowsheet} />
        )}

        {view && (
          <p className="text-caption text-ink-soft">
            pureOS reads this run&rsquo;s train, unit by unit:{' '}
            <a className="text-accent hover:underline" href={href(trainPath({ scenarioId: null, artifactId: view.artifactId }))}>
              pureOS → Train
            </a>
            .
          </p>
        )}

        {bound && (
          <Card className="p-4" data-testid="modeller-questions">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Questions for a process modeller</h2>
              <Button onClick={() => exportText(`${scenario.id}-questions.txt`, questionsText(bound, view))}>
                <Download size={14} /> Export as text
              </Button>
            </div>
            <p className="text-caption text-ink-soft mb-2">
              The inputs that rest on an assumption, the strongest mover first once a run has ranked them, and what the flowsheet leaves out.
            </p>
            <ol className="list-decimal pl-5 space-y-1 text-body">
              {questions.map((q) => (
                <li key={q.key}>
                  <span className="font-medium">{q.label}</span>
                  {q.rho != null && <span className="font-num text-caption text-ink-soft"> (ρ {fmt(q.rho, 2)})</span>}: {q.question}
                </li>
              ))}
            </ol>
            <ul className="list-disc pl-5 mt-2 text-caption text-ink-soft">
              {bound.leavesOut.map((l) => (
                <li key={l}>left out: {l}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

const EMPTY: InputAssumption[] = [];
const EMPTY_FITS: Record<string, string> = {};
/** The inputs a fermOS fit can feed (proforma.FIT_KEYS). */
const FIT_INPUTS = ['titre', 'yield', 'productivity'];

/** An authored surface (kept for the archived examples, D5), or a BioSTEAM scenario the service simulates. */
export default function ProformaScenario({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const madeHere = useStore((s) => s.createdScenarioIds.includes(scenarioId));
  const durableReady = useStore((s) => s.durableReady);
  // A scenario made here lives in this browser's Durable tier, which is read
  // just after the page loads: a deep link waits for it rather than say the
  // scenario does not exist.
  if (!scenario && !durableReady && durableAvailable())
    return <p className="text-body text-ink-soft">Reading the scenarios kept in this browser…</p>;
  return (
    <>
      {scenario && <ArchivedBanner kind="scenario" id={scenario.id} />}
      {scenario?.kind === 'biosteam' ? (
        <BiosteamScenario key={scenario.id} scenario={scenario} madeHere={madeHere} />
      ) : (
        <AuthoredScenario scenarioId={scenarioId} />
      )}
    </>
  );
}
