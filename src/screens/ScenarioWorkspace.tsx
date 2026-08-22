// Scenario workspace (OF-DES-001 §8.13). Read it like an instrument: every
// assumption ticked, the waterfall always summing to the headline, and
// simulation treated as work rather than magic.
import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Copy, Download, Factory, GitCompare, Pin, PinOff, Table2, SlidersHorizontal } from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import type { CostLine } from '@/data/types';
import { evaluateGrid } from '@/engine/grids';
import { plantFails } from '@/lib/use-plant';
import { fmt } from '@/engine/units';
import { scaled } from '@/sim/latency';
import { exportCSV } from '@/lib/csv';
import { PageHeader, Card, Button, Sheet, Callout, cx, EmptyState, Explain } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { Tick, ProvenanceBadge } from '@/components/Provenance';

import { ArrowUpRight } from 'lucide-react';
import { corpusBasis } from '@/lib/basis-corpus';
import { BasisLine } from '@/components/Basis';
import { ProcessConsequence } from '@/components/ProcessConsequence';
import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('fermos', 'corpus');
const CONVERGE_STAGES = ['Building flowsheet', 'Converging', 'Costing'];

/** A "view as table" disclosure — the accessibility floor for every chart (§6.6). */
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

  // Asked of the plant, not asserted about it. This used to be a predicate on
  // S2 naming one corner of its grid as non-convergent; that corner solves
  // perfectly well now, it is just ruinously expensive, and a failure that does
  // not fail when computed is the same defect the contradiction engine exists to
  // refuse.
  const nonConvergent = useMemo(
    () => (scenario ? plantFails(scenario.modelId, scenario.point) : false),
    [scenario],
  );

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
      else if (e.key === 'c') navigate('/fermos/compare');
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


  if (!scenario || !grid) {
    return (
      <EmptyState
        title="Scenario not found"
        body={`No scenario with id ${scenarioId} exists in this session.`}
        action={<Button onClick={() => navigate('/fermos')}>Back to Simulate</Button>}
      />
    );
  }

  const basis = corpusBasis(scenario.modelId);
  const primaryDim = scenario.dims[0];
  const secondaryDim = scenario.dims[1];




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
      // `a.basis.recordId`, not `a.recordId`. The top-level field is the
      // pre-discriminator binding and is populated on ZERO assumptions in the
      // corpus, so this column exported an empty string for every row that
      // actually had a record behind it.
      ...scenario.assumptions.map((a) => [
        'Assumption',
        a.label,
        fmt(a.value),
        a.unit,
        a.provenance,
        a.basis.kind === 'record' ? a.basis.recordId : '',
        a.note,
      ]),
      // The cost lines are Proforma's and are exported from its own screen.
      // What leaves fermOS is the point, its assumptions, and the price that
      // point is quoted at — named as a quotation, not as this part's result.
      ...(result
        ? [['Quoted by Proforma', 'Minimum selling price', result.msp.toFixed(2), 'USD kg⁻¹', 'demo', '', 'Interpolated from the precomputed sweep — no regional basis, no accuracy class']]
        : []),
    ];
    exportCSV(`${scenario.id}-assumptions-results.csv`, headers, rows);
  };

  return (
    <div>
      <PageHeader
        eyebrow={`${EYEBROW} · ${scenario.modelId}`}
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
            <Button onClick={() => navigate('/fermos/compare')} title="Compare (c)">
              <GitCompare size={14} /> Compare
            </Button>
            <Button
              variant="primary"
              onClick={() => navigate(`/fermos/s/${scenario.id}/plant`)}
              title="The sized flowsheet, the capital ladder and the cash flow behind this price"
            >
              <Factory size={14} /> Open the plant
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
                {scenario.assumptions.filter((a) => a.basis.kind === 'record').length}
              </span>{' '}
              bind to a Ledger record —{' '}
              <span className="font-num">
                {scenario.assumptions.filter((a) => a.basis.kind === 'model').length}
              </span>{' '}
              are declared modelling choices.
            </p>
            {scenario.assumptions.some((a) => a.basis.kind === 'unsourced') && (
              <p className="text-caption text-signal-error mb-3">
                <span className="font-num">
                  {scenario.assumptions.filter((a) => a.basis.kind === 'unsourced').length}
                </span>{' '}
                carries no record and no declared justification. That is a defect, not a
                category — it is shown rather than averaged away.
              </p>
            )}
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
                    The plant did not size at this point
                  </h2>
                  <p className="text-body text-ink-soft mb-3 max-w-xl">
                    Either the flowsheet could not be built here — a vessel count that runs away, a
                    stream with no mass in it — or the cash flow found no price at which net present
                    value reaches zero. Rather than show you a number from a failed solve, the
                    workspace shows nothing.
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
              {/* ── The seam ──────────────────────────────────────────────
                  The price is Proforma's, quoted here the same way the plant
                  screen quotes it. Moving a slider moves it, which is the whole
                  argument — but this screen no longer decomposes it, ranks it or
                  sweeps it. Those are economics and they are on Proforma. */}
              <a
                href={href(`/proforma/price/${scenario.id}`)}
                className="card block p-4 motion-colors hover:border-accent/45 hover:bg-accent-wash/40"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                  <div>
                    <div className="text-caption uppercase tracking-wide text-ink-soft">
                      Priced by Proforma
                    </div>
                    <div
                      className={cx(
                        'font-num text-page-title leading-none mt-0.5 transition-opacity',
                        converging !== null && 'opacity-40',
                      )}
                    >
                      {result ? fmt(result.msp, 1) : '—'}
                      <span className="text-body text-ink-soft ml-1.5">USD kg⁻¹</span>
                    </div>
                    {basis && <BasisLine basis={basis} className="mt-1" />}
                  </div>
                  <div className="text-caption text-ink-soft max-w-prose flex items-start gap-1.5">
                    <span>
                      Interpolated off the sweep grid. The build-up, the tornado and the cash flow
                      behind it are Proforma&rsquo;s.
                    </span>
                    <ArrowUpRight size={14} className="shrink-0 mt-[2px]" aria-hidden />
                  </div>
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
              </a>

              {/* What the point actually builds — fermOS's own subject, and
                  what this screen was missing while it held the economics. */}
              <ProcessConsequence scenarioId={scenario.id} />
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
                <Tick
                  p={a.basis.kind === 'unsourced' ? 'unsourced' : a.provenance}
                  className="flex-1 min-w-0"
                >
                  <div className="font-medium text-body">{a.label}</div>
                  <div className="font-num text-body">
                    {fmt(a.value)} <span className="text-ink-soft">{a.unit}</span>
                  </div>
                </Tick>
                <div className="shrink-0 flex flex-col items-end gap-1">
                  <ProvenanceBadge
                    p={a.basis.kind === 'unsourced' ? 'unsourced' : a.provenance}
                    compact
                  />
                  {a.basis.kind === 'record' && <CitationChip recordId={a.basis.recordId} />}
                </div>
              </div>
              {a.basis.kind === 'model' && (
                <p className="text-caption text-ink-soft mt-1.5 border-l-2 border-line pl-2">
                  <span className="text-ink">Modelling choice.</span> {a.basis.justification}
                </p>
              )}
              {a.basis.kind === 'unsourced' && (
                <p className="text-caption text-signal-error mt-1.5">
                  No record, no declared justification. This number is in the model and nothing
                  in the corpus stands behind it.
                </p>
              )}
              <p className="text-caption text-ink-soft mt-1.5">{a.note}</p>
            </div>
          ))}
        </div>
      </Sheet>
    </div>
  );
}
