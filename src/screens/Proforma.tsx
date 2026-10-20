// Scenario index (OF-DES-001 §8.13), and the benchmark (OF-BLD-014 §8.2):
// before Proforma prices anything new with BioSTEAM, it runs a published
// biorefinery end to end and shows the price that run arrives at.
//
// PROGRAMS (OF-BLD-016 §2.2). The scenario grid, the pinned count and the
// scenario that "New scenario" copies all read through the store's program
// filter: a scenario in an archived program leaves the index while the switch
// is off, and its link still opens it under the banner. The benchmark is
// general and always shows.
import { useEffect, useMemo, useState } from 'react';
import { LineChart, Pin, PinOff, Plus, GitCompare } from 'lucide-react';
import { PROGRAMS, PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { programOf, useProgramFilter, useStore } from '@/store';
import { navigate } from '@/router';
import { evaluateGrid } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { PageHeader, Card, Button, LinkButton, cx, EmptyState } from '@/components/ui';
import { Tick } from '@/components/Provenance';
import { SubsystemReference, SubsystemShelf } from '@/components/ReferenceView';
import { href } from '@/router';
import {
  BENCHMARK_EXPECTED,
  ProformaDown,
  type BenchmarkOutput,
  type BenchmarkResponse,
  proformaBenchmark,
  runProformaBenchmark,
} from '@/lib/proforma';

const SIMULATOR_SAYS: Record<string, string> = {
  cold: 'The simulator has not started on this service yet.',
  starting: 'The simulator is starting: importing BioSTEAM takes most of a minute.',
  ready: 'The simulator is warm.',
  failed: 'The simulator failed to start.',
};

function BenchmarkCard() {
  const [state, setState] = useState<BenchmarkResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    proformaBenchmark(ctrl.signal)
      .then(setState)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(e instanceof ProformaDown ? e.message : String(e)));
    return () => ctrl.abort();
  }, []);

  const run = () => {
    setBusy(true);
    setProblem(null);
    runProformaBenchmark()
      .then(setState)
      .catch((e: unknown) => setProblem(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  const art = state?.artifact ?? null;
  const out = art?.output as BenchmarkOutput | undefined;
  return (
    <Card className="p-4 mb-5" data-testid="benchmark-card">
      <div className="flex items-start justify-between gap-3 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Benchmark: a published biorefinery, run here</h2>
        {state && !art && (
          <Button onClick={run} disabled={busy}>
            {busy ? 'Running…' : 'Run the benchmark'}
          </Button>
        )}
      </div>
      <p className="text-body text-ink-soft mb-3">
        Before Proforma prices a new flowsheet with BioSTEAM, it runs the corn stover ethanol biorefinery that ships with
        the <span className="font-num">biorefineries</span> package, with every setting the package's own. Arriving at
        the minimum selling price measured for that package version shows this installation runs a published
        biorefinery model from end to end as its authors do.
      </p>
      {problem && <p className="text-body text-signal-warn">{problem}</p>}
      {state && !art && (
        <p className="text-body" data-testid="benchmark-empty">
          Not run on this service yet. {SIMULATOR_SAYS[state.simulator.status]} The run takes about a minute; expected:{' '}
          <span className="font-num">{BENCHMARK_EXPECTED.usdPerGal} USD per gallon</span> within{' '}
          <span className="font-num">{BENCHMARK_EXPECTED.tolerance * 100} %</span> for{' '}
          <span className="font-num">{BENCHMARK_EXPECTED.package}</span>.
        </p>
      )}
      {art && out && (
        <div className="space-y-2" data-testid="benchmark-result">
          <Tick p={art.provenance}>
            <div className="text-caption uppercase tracking-wide text-ink-soft">Minimum ethanol selling price</div>
            <div className="font-num text-display leading-none">
              {fmt(out.mespUsdPerGal, 4)}
              <span className="text-body text-ink-soft ml-1">USD per gallon</span>
            </div>
            <div className="text-caption text-ink-soft mt-0.5">
              Expected <span className="font-num">{BENCHMARK_EXPECTED.usdPerGal}</span>; this run is{' '}
              <span className="font-num">
                {fmt(((out.mespUsdPerGal - BENCHMARK_EXPECTED.usdPerGal) / BENCHMARK_EXPECTED.usdPerGal) * 100, 2)} %
              </span>{' '}
              from it.
            </div>
          </Tick>
          <p className="text-caption text-ink-soft">
            From <span className="font-num">{out.package}</span> on BioSTEAM <span className="font-num">{out.biosteam}</span>
            ; rate of return <span className="font-num">{fmt(out.settings.rateOfReturn * 100, 3)} %</span>, income tax{' '}
            <span className="font-num">{fmt(out.settings.incomeTax * 100, 3)} %</span>,{' '}
            <span className="font-num">{fmt(out.settings.operatingDays, 4)}</span> operating days, plant life{' '}
            <span className="font-num">
              {out.settings.startYear} to {out.settings.endYear}
            </span>
            , all read back from the package. Kept as{' '}
            <a className="font-num hover:text-accent" href={href(`/biorepo/artifacts/${art.id}`)}>
              {art.id}
            </a>
            .
          </p>
          <ul className="text-caption text-ink-soft list-disc pl-5">
            {out.references.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export default function Proforma() {
  const allScenarios = useStore((s) => s.scenarios);
  const shows = useProgramFilter();
  const scenarios = useMemo(() => allScenarios.filter((sc) => shows('scenario', sc.id)), [allScenarios, shows]);
  const hiddenPrograms = useMemo(() => {
    const ids = new Set(
      allScenarios
        .filter((sc) => !shows('scenario', sc.id))
        .map((sc) => programOf('scenario', sc.id, { scenarios: allScenarios })),
    );
    return PROGRAMS.filter((p) => ids.has(p.id));
  }, [allScenarios, shows]);
  const grids = useStore((s) => s.grids);
  const duplicateScenario = useStore((s) => s.duplicateScenario);
  const togglePin = useStore((s) => s.togglePin);

  const pinnedCount = scenarios.filter((s) => s.pinned).length;

  return (
    <div>
      <PageHeader
        eyebrow="Cost and scale"
        title="Proforma"
        subtitle="Turn verified parameters into economics. Each scenario is a sweep over a techno-economic model; every assumption carries its provenance."
        actions={
          <>
            <LinkButton to="/biorepo/compare">
              <GitCompare size={14} /> Compare
              {pinnedCount > 0 && (
                <span className="font-num text-caption ml-1">({pinnedCount} pinned)</span>
              )}
            </LinkButton>
            <Button
              variant="primary"
              onClick={() => {
                const id = duplicateScenario(scenarios[0]?.id ?? '');
                navigate(`/proforma/scenario/${id}`);
              }}
              disabled={scenarios.length === 0}
            >
              <Plus size={14} /> New scenario
            </Button>
          </>
        }
      />

      <BenchmarkCard />

      {scenarios.length === 0 && hiddenPrograms.length > 0 ? (
        <EmptyState
          title="Every scenario here is in an archived program"
          body={
            <span data-testid="hidden-by-archive">
              The scenarios on file belong to {hiddenPrograms.map((p) => p.name).join(' and ')}, and{' '}
              {hiddenPrograms.length === 1 ? 'that program is archived' : 'those programs are archived'}, so this index
              hides them. Settings → Programs shows archived programs again; a link to a scenario still opens it.
            </span>
          }
          icon={<LineChart size={28} />}
          action={<LinkButton to={PROGRAMS_SETTINGS_PATH}>Open Settings → Programs</LinkButton>}
        />
      ) : scenarios.length === 0 ? (
        <EmptyState
          title="No scenarios yet"
          body="A scenario pairs a cost model with a point in its sweep space."
          icon={<LineChart size={28} />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {scenarios.map((sc) => {
            if (sc.kind === 'biosteam')
              return (
                <Card key={sc.id} className="p-4 flex flex-col" data-testid="biosteam-card">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="chip font-num">{sc.modelId}</span>
                    <span className="chip">BioSTEAM</span>
                  </div>
                  <a href={`#/proforma/scenario/${sc.id}`} className="font-serif text-section-title font-semibold hover:text-accent leading-snug">
                    {sc.name}
                  </a>
                  <p className="text-body text-ink-soft mt-1 mb-3 flex-1">{sc.description}</p>
                  <p className="text-caption text-ink-soft mb-3">
                    BioSTEAM flowsheet, draft v0 — fermentation, harvest and drying only. Its price is a distribution the service
                    simulates once every input has a source.
                  </p>
                  <LinkButton to={`/proforma/scenario/${sc.id}`} variant="primary" className="justify-center">
                    Open scenario
                  </LinkButton>
                </Card>
              );
            const grid = grids[sc.modelId];
            const result = grid ? evaluateGrid(grid, sc.point) : null;
            const linked = sc.assumptions.filter((a) => a.recordId).length;
            return (
              <Card key={sc.id} className="p-4 flex flex-col">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="chip font-num">{sc.modelId}</span>
                  <button
                    className={cx('btn btn-sm', sc.pinned && 'text-accent border-accent/40')}
                    onClick={() => togglePin(sc.id)}
                    aria-pressed={sc.pinned}
                    title={sc.pinned ? 'Unpin from compare' : 'Pin to compare'}
                  >
                    {sc.pinned ? <Pin size={13} /> : <PinOff size={13} />}
                  </button>
                </div>

                <a
                  href={`#/proforma/scenario/${sc.id}`}
                  className="font-serif text-section-title font-semibold hover:text-accent leading-snug"
                >
                  {sc.name}
                </a>
                <p className="text-body text-ink-soft mt-1 mb-3 flex-1">{sc.description}</p>

                <Tick p="demo" className="mb-3">
                  <div className="text-caption uppercase tracking-wide text-ink-soft">
                    Minimum selling price
                  </div>
                  <div className="font-num text-display leading-none">
                    {result ? `$${fmt(result.msp, 1)}` : '—'}
                    <span className="text-body text-ink-soft ml-1">/kg</span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">
                    Demo model v0 — illustrative economics, not validated
                  </div>
                </Tick>

                <div className="text-caption text-ink-soft space-y-0.5 mb-3">
                  <div>
                    Sweep:{' '}
                    <span className="text-ink">{sc.dims.map((d) => d.label).join(' × ')}</span>
                  </div>
                  <div className="font-num">
                    {linked} of {sc.assumptions.length} assumptions linked to corpus records
                  </div>
                </div>

                <LinkButton to={`/proforma/scenario/${sc.id}`} variant="primary" className="justify-center">
                  Open scenario
                </LinkButton>
              </Card>
            );
          })}
        </div>
      )}

      {/* §8.4 — Uncertainty is live, so its reference sits on this view, below its own line. */}
      <div className="mt-8">
        <SubsystemReference id="proforma.uncertainty" />
      </div>

      <SubsystemShelf owner="Proforma" />
    </div>
  );
}
