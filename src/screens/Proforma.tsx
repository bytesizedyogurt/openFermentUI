// Proforma's index (OF-DES-001 §8.13), rebuilt around the shelf of
// flowsheets (OF-BLD-019 §3.1, D2, D5, D6).
//
// Three rows, each read from the service or the store, none written here:
//
//   Reference runs  every reference biorefinery on the shelf, run whole on
//                   its package's own defaults: the price of its newest
//                   stored run, when it ran, its provenance, a Run or Rerun
//                   with the simulator's status line, and a link to its page
//                   (/proforma/reference/:id, OF-BLD-019 §3.3), every one read
//                   at /api/proforma/reference/:id, the benchmark included.
//                   The corn stover benchmark (OF-BLD-014 §8.2) is the first:
//                   before Proforma prices anything new, it reproduces a
//                   published biorefinery.
//   Flowsheets      every other flowsheet on the shelf, with the inputs it
//                   takes and New scenario from this.
//   Scenarios       the programs' scenarios: the price of the newest run
//                   (read from its artifact) or "not run yet", how its
//                   inputs stand, and pin.
//
// New scenario opens a chooser over the shelf (components/NewScenarioDialog)
// and makes a `biosteam` scenario that opens on its page. NOTHING here is
// disabled because a list is empty: an empty row says why and what fills it.
//
// PROGRAMS (OF-BLD-016 §2.2). The shelf is asked with the program switch
// (`includeArchived`), and the scenarios, the pinned count and every card
// read through the store's program filter: a scenario in an archived
// program leaves the index while the switch is off, the index says whose,
// and its link still opens it under the banner.
import { useEffect, useMemo, useState } from 'react';
import { BookOpen, FlaskConical, GitCompare, LineChart, Pin, PinOff, Play, Plus } from 'lucide-react';
import type { Artifact, FlowsheetInfo, ProformaScenarioInfo, Scenario } from '@/data/types';
import { PROGRAMS, PROGRAM_BY_ID } from '@/data/programs';
import { programOf, useProgramFilter, useStore } from '@/store';
import { href } from '@/router';
import { evaluateGrid } from '@/engine/grids';
import { fmt } from '@/engine/units';
import { PageHeader, Card, Button, LinkButton, cx, EmptyState } from '@/components/ui';
import { Tick, ProvenanceBadge } from '@/components/Provenance';
import { SubsystemReference, SubsystemShelf } from '@/components/ReferenceView';
import { HiddenByArchive } from '@/components/HiddenByArchive';
import { NewScenarioDialog, NoFlowsheetLine, inputSourceWords } from '@/components/NewScenarioDialog';
import {
  BENCHMARK_EXPECTED,
  BENCHMARK_FLOWSHEET,
  LEGACY_BENCHMARK_TOOL,
  ProformaDown,
  SIMULATOR_SAYS,
  type BenchmarkOutput,
  type PriceRead,
  type ReferenceResponse,
  inputCounts,
  newestRunId,
  proformaArtifact,
  proformaBind,
  proformaNewestRun,
  proformaReference,
  referenceChecks,
  stamp,
  referencePath,
  proformaScenarios,
  proformaShelf,
  referencePrice,
  runPrice,
  runProformaReference,
} from '@/lib/proforma';

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** When an artifact was computed, as a date and a minute, in UTC as the service writes it (§3.R, finding 4). */
const when = stamp;

const programName = (id: string | null | undefined) => (id ? (PROGRAM_BY_ID[id as keyof typeof PROGRAM_BY_ID]?.name ?? id) : null);

function Price({ price, provenance, testid }: { price: PriceRead; provenance: Artifact['provenance']; testid?: string }) {
  return (
    <Tick p={provenance}>
      <div className="font-num text-display leading-none" data-testid={testid}>
        {fmt(price.value, 4)}
      </div>
      <div className="text-caption text-ink-soft mt-0.5">
        {price.basis}; {price.reads}
        {price.low != null && price.high != null && (
          <>
            , <span className="font-num">{fmt(price.low, 4)}</span> to <span className="font-num">{fmt(price.high, 4)}</span>{' '}
            between the 5th and 95th percentiles
          </>
        )}
      </div>
    </Tick>
  );
}

// ── Reference runs ──────────────────────────────────────────────────────

function ReferenceCard({ info }: { info: FlowsheetInfo }) {
  const [state, setState] = useState<ReferenceResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    proformaReference(info.id, ctrl.signal)
      .then(setState)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [info.id]);

  const run = () => {
    setBusy(true);
    setProblem(null);
    runProformaReference(info.id)
      .then(setState)
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };

  const art = state?.artifact ?? null;
  const price = art ? referencePrice(info, art) : null;
  const isBenchmark = info.id === BENCHMARK_FLOWSHEET;
  const bench = isBenchmark && art ? (art.output as unknown as BenchmarkOutput) : null;
  // The benchmark kept before reference runs held their tables (§3.R,
  // findings 0, 15, 22): its price, said to be what it is.
  const legacy = art?.tool === LEGACY_BENCHMARK_TOOL;
  // How many of the package test's values this run holds (§3.R, finding 30).
  const checks = referenceChecks(art);
  const within = checks.filter((c) => c.within).length;
  return (
    <Card className="p-4 flex flex-col" data-testid="reference-card" data-flowsheet={info.id}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="chip font-num">{info.id}</span>
        <span className="chip">reference</span>
      </div>
      <a href={href(referencePath(info.id))} className="font-serif text-section-title font-semibold leading-snug hover:text-accent" data-testid="reference-title">
        {info.title}
      </a>
      <p className="text-caption text-ink-soft mb-2">
        From <span className="font-num">{info.source}</span>
        {info.program && <> · {programName(info.program)}</>}
        {info.packageTest && (
          <>
            {' '}
            · held to <span className="font-num">{info.packageTest.split('::').pop()}</span>
          </>
        )}
      </p>
      <p className="text-body text-ink-soft mb-3 flex-1">{info.description}</p>
      {problem && <p className="text-body text-signal-warn mb-2">{problem}</p>}
      {state && !art && (
        <p className="text-body mb-2" data-testid="reference-not-run">
          Not run on this service yet.{' '}
          {isBenchmark && (
            <>
              Expected: <span className="font-num">{BENCHMARK_EXPECTED.usdPerGal} USD per gallon</span> within{' '}
              <span className="font-num">{BENCHMARK_EXPECTED.tolerance * 100} %</span> for{' '}
              <span className="font-num">{BENCHMARK_EXPECTED.package}</span>, the price its package gives on its own
              defaults.
            </>
          )}
          {state.note && <span className="block text-caption text-ink-soft mt-1">{state.note}</span>}
        </p>
      )}
      {art && (
        <div className="space-y-1.5 mb-2" data-testid="reference-result">
          {price ? (
            <Price price={price} provenance={art.provenance} testid="reference-price" />
          ) : (
            <p className="text-body text-ink-soft">The run holds no price the shelf names for this flowsheet.</p>
          )}
          {legacy && state?.note && (
            <p className="text-caption text-ink-soft" data-testid="reference-legacy">
              {state.note}
            </p>
          )}
          {checks.length > 0 && (
            <p className="text-caption font-num" data-testid="reference-within">
              {within} of {checks.length} values of <span className="font-num">{info.packageTest?.split('::').pop() ?? 'its package’s test'}</span> within
              the package&rsquo;s tolerance on this run.
            </p>
          )}
          {bench && typeof bench.mespUsdPerGal === 'number' && (
            <p className="text-caption text-ink-soft">
              Expected <span className="font-num">{BENCHMARK_EXPECTED.usdPerGal}</span>, as this build measured it when Proforma was first built
              on BioSTEAM; this run is{' '}
              <span className="font-num">
                {fmt(((bench.mespUsdPerGal - BENCHMARK_EXPECTED.usdPerGal) / BENCHMARK_EXPECTED.usdPerGal) * 100, 2)} %
              </span>{' '}
              from it.
            </p>
          )}
          <p className="text-caption text-ink-soft flex flex-wrap items-center gap-1.5">
            <ProvenanceBadge p={art.provenance} compact /> Ran <span className="font-num">{when(art.createdAt)}</span> ·
            kept as{' '}
            <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${art.id}`)}>
              {art.id}
            </a>
          </p>
          {bench?.settings && Array.isArray(bench.references) && (
            <details className="text-caption text-ink-soft">
              <summary className="cursor-pointer hover:text-ink">What the package set, read back from it</summary>
              <p className="mt-1">
                From <span className="font-num">{bench.package}</span> on{' '}
                <span className="font-num">{bench.simulator ?? (bench.biosteam ? `biosteam ${bench.biosteam}` : 'BioSTEAM')}</span>; rate of return{' '}
                <span className="font-num">{fmt(bench.settings.rateOfReturn * 100, 3)} %</span>, income tax{' '}
                <span className="font-num">{fmt(bench.settings.incomeTax * 100, 3)} %</span>,{' '}
                <span className="font-num">{fmt(bench.settings.operatingDays, 4)}</span> operating days, plant life{' '}
                <span className="font-num">
                  {bench.settings.startYear} to {bench.settings.endYear}
                </span>
                .
              </p>
              <ul className="list-disc pl-5 mt-1">
                {bench.references.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 mt-auto pt-1">
        <Button onClick={run} disabled={busy} data-testid="reference-run">
          <Play size={13} /> {busy ? 'Running…' : art && !legacy ? 'Rerun' : 'Run'}
        </Button>
        <LinkButton to={referencePath(info.id)}>
          <BookOpen size={13} /> Its page
        </LinkButton>
        <span className="text-caption text-ink-soft" data-testid="reference-status">
          {state ? SIMULATOR_SAYS[state.simulator.status] : problem ? 'The simulator is the service’s.' : 'Asking the service…'}
          {state?.simulator.error && <> {state.simulator.error}</>}
          {busy && ' A first run starts the simulator and takes a minute or two; it stays warm after.'}
        </span>
      </div>
    </Card>
  );
}

// ── Flowsheets ──────────────────────────────────────────────────────────

function FlowsheetCard({ info, onNew }: { info: FlowsheetInfo; onNew: () => void }) {
  return (
    <Card className="p-4 flex flex-col" data-testid="flowsheet-card" data-flowsheet={info.id}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="chip font-num">{info.id}</span>
        {info.program && <span className="chip">{programName(info.program)}</span>}
      </div>
      <h3 className="font-serif text-section-title font-semibold leading-snug">{info.title}</h3>
      <p className="text-caption text-ink-soft mb-2">
        From <span className="font-num">{info.source}</span>
      </p>
      <p className="text-body text-ink-soft mb-2">{info.description}</p>
      <div className="text-caption uppercase tracking-wide text-ink-soft mb-0.5">Inputs</div>
      <ul className="text-caption mb-2 space-y-0.5 flex-1" data-testid="flowsheet-inputs">
        {info.inputs.map((i) => (
          <li key={i.key}>
            <span className="text-ink">{i.name}</span>
            {i.unit && <span className="font-num text-ink-soft"> ({i.unit})</span>}
            <span className="text-ink-soft">: {inputSourceWords(i)}</span>
          </li>
        ))}
      </ul>
      {info.priceBasis && <p className="text-caption text-ink-soft mb-3">The price is {info.priceBasis}.</p>}
      <Button variant="primary" className="justify-center" onClick={onNew} data-testid="new-from-flowsheet">
        <Plus size={14} /> New scenario from this
      </Button>
    </Card>
  );
}

// ── Scenarios ───────────────────────────────────────────────────────────

function PinButton({ scenario }: { scenario: Scenario }) {
  const togglePin = useStore((s) => s.togglePin);
  return (
    <button
      className={cx('btn btn-sm', scenario.pinned && 'text-accent border-accent/40')}
      onClick={() => togglePin(scenario.id)}
      aria-pressed={scenario.pinned}
      title={scenario.pinned ? 'Unpin from compare' : 'Pin to compare'}
    >
      {scenario.pinned ? <Pin size={13} /> : <PinOff size={13} />}
    </button>
  );
}

function BiosteamCard({
  scenario,
  shelf,
  info,
}: {
  scenario: Scenario;
  shelf: FlowsheetInfo[];
  /** The service's binding of this scenario, when it holds it. */
  info: ProformaScenarioInfo | null;
}) {
  const assumptions = useStore((s) => s.proformaAssumptions[scenario.id]);
  const fits = useStore((s) => s.proformaFits[scenario.id]);
  const madeHere = useStore((s) => s.createdScenarioIds.includes(scenario.id));
  const showArchived = useStore((s) => s.showArchived);
  const [art, setArt] = useState<Artifact | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  // The service's newest run of this scenario, made in any browser, by the
  // API or by Postdoc (§3.R, findings 8 and 21), else the one this browser
  // kept; undefined until the service answers.
  const [served, setServed] = useState<Artifact | null | undefined>(undefined);
  useEffect(() => {
    const ctrl = new AbortController();
    proformaNewestRun(scenario.id, ctrl.signal)
      .then(setServed)
      .catch(() => !ctrl.signal.aborted && setServed(null));
    return () => ctrl.abort();
  }, [scenario.id]);
  const runId = newestRunId(served, scenario.lastRunId);
  const flowsheetId = scenario.flowsheetId ?? scenario.modelId;

  // OF-BLD-019 §2.R: a scenario made here is bound by the service as its page
  // binds it (`GET /api/proforma/bind`, contract (c), with the fits chosen),
  // so the card counts what the page lists. Until the service answers, the
  // card counts nothing; if it cannot be asked, the shelf says what can bind.
  const [made, setMade] = useState<{ info: ProformaScenarioInfo | null } | null>(null);
  const fitsKey = JSON.stringify(Object.entries(fits ?? {}).sort());
  useEffect(() => {
    setMade(null);
    if (!madeHere || info) return;
    const ctrl = new AbortController();
    const chosen = Object.fromEntries(JSON.parse(fitsKey) as [string, string][]);
    proformaBind(flowsheetId, { host: null, includeArchived: showArchived, fits: chosen }, ctrl.signal)
      .then((b) => setMade({ info: b }))
      .catch(() => !ctrl.signal.aborted && setMade({ info: null }));
    return () => ctrl.abort();
  }, [madeHere, info, flowsheetId, showArchived, fitsKey]);

  useEffect(() => {
    setArt(null);
    setProblem(null);
    if (!runId) return;
    if (served && served.id === runId) {
      setArt(served);
      return;
    }
    const ctrl = new AbortController();
    proformaArtifact(runId, ctrl.signal)
      .then(setArt)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [runId, served]);

  const flowsheet = shelf.find((f) => f.id === flowsheetId) ?? null;
  const asked = madeHere && !info;
  const counts = asked && !made ? null : inputCounts(scenario, info ?? made?.info ?? null, shelf, assumptions ?? [], fits ?? {});
  const price = art ? runPrice(art, shelf) : null;
  return (
    <Card className="p-4 flex flex-col" data-testid="biosteam-card" data-scenario={scenario.id}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="chip font-num">{flowsheetId}</span>
        <div className="flex items-center gap-1.5">
          <span className="chip">BioSTEAM</span>
          <PinButton scenario={scenario} />
        </div>
      </div>
      <a href={href(`/proforma/scenario/${scenario.id}`)} className="font-serif text-section-title font-semibold hover:text-accent leading-snug">
        {scenario.name}
      </a>
      <p className="text-caption text-ink-soft mb-2">
        {flowsheet ? flowsheet.title : `Flowsheet ${flowsheetId}`}
        {scenario.program && <> · {programName(scenario.program)}</>}
        {scenario.createdAt && (
          <>
            {' '}
            · made here <span className="font-num">{when(scenario.createdAt)}</span>
          </>
        )}
      </p>
      {scenario.description && <p className="text-body text-ink-soft mb-2">{scenario.description}</p>}
      <div className="mb-3 flex-1">
        {!runId && served !== undefined && (
          <p className="text-body" data-testid="scenario-not-run">
            Not run yet.
          </p>
        )}
        {runId && problem && <p className="text-caption text-signal-warn">Its newest run, {runId}, could not be read: {problem}</p>}
        {art && price && <Price price={price} provenance={art.provenance} testid="scenario-price" />}
        {art && !price && <p className="text-body text-ink-soft">Its newest run has no sample the flowsheet could hold, so no price.</p>}
        {art && (
          <p className="text-caption text-ink-soft mt-1">
            Ran <span className="font-num">{when(art.createdAt)}</span> ·{' '}
            <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${art.id}`)}>
              {art.id}
            </a>
          </p>
        )}
      </div>
      {counts && (
        <p className="text-caption text-ink-soft mb-3 font-num" data-testid="scenario-inputs">
          {counts.total} inputs: {counts.records} {counts.bound ? 'bound to records' : 'can bind to records'}
          {counts.computed > 0 && `, ${counts.computed} with a fermOS fit chosen`}
          {counts.assumed > 0 && `, ${counts.assumed} assumed`}
          {counts.conventions > 0 && `, ${counts.conventions} by convention`}, {counts.waiting} waiting for an assumption
        </p>
      )}
      <LinkButton to={`/proforma/scenario/${scenario.id}`} variant="primary" className="justify-center">
        Open scenario
      </LinkButton>
    </Card>
  );
}

function AuthoredCard({ scenario }: { scenario: Scenario }) {
  const grids = useStore((s) => s.grids);
  const grid = grids[scenario.modelId];
  const result = grid ? evaluateGrid(grid, scenario.point) : null;
  const linked = scenario.assumptions.filter((a) => a.recordId).length;
  return (
    <Card className="p-4 flex flex-col">
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="chip font-num">{scenario.modelId}</span>
        <PinButton scenario={scenario} />
      </div>

      <a href={`#/proforma/scenario/${scenario.id}`} className="font-serif text-section-title font-semibold hover:text-accent leading-snug">
        {scenario.name}
      </a>
      <p className="text-body text-ink-soft mt-1 mb-3 flex-1">{scenario.description}</p>

      <Tick p="demo" className="mb-3">
        <div className="text-caption uppercase tracking-wide text-ink-soft">Minimum selling price</div>
        <div className="font-num text-display leading-none">
          {result ? `$${fmt(result.msp, 1)}` : '—'}
          <span className="text-body text-ink-soft ml-1">/kg</span>
        </div>
        <div className="text-caption text-ink-soft mt-0.5">Cost model v0 — illustrative economics, not validated</div>
      </Tick>

      <div className="text-caption text-ink-soft space-y-0.5 mb-3">
        <div>
          Sweep: <span className="text-ink">{scenario.dims.map((d) => d.label).join(' × ')}</span>
        </div>
        <div className="font-num">
          {linked} of {scenario.assumptions.length} assumptions linked to corpus records
        </div>
      </div>

      <LinkButton to={`/proforma/scenario/${scenario.id}`} variant="primary" className="justify-center">
        Open scenario
      </LinkButton>
    </Card>
  );
}

// ── the index ───────────────────────────────────────────────────────────

export default function Proforma() {
  const allScenarios = useStore((s) => s.scenarios);
  const createdIds = useStore((s) => s.createdScenarioIds);
  const showArchived = useStore((s) => s.showArchived);
  const dialogOpen = useStore((s) => s.ui.newScenarioOpen);
  const setUI = useStore((s) => s.setUI);
  const shows = useProgramFilter();
  const scenarios = useMemo(() => allScenarios.filter((sc) => shows('scenario', sc.id)), [allScenarios, shows]);
  const hidden = useMemo(() => allScenarios.filter((sc) => !shows('scenario', sc.id)), [allScenarios, shows]);
  const hiddenPrograms = useMemo(() => {
    const ids = new Set(hidden.map((sc) => programOf('scenario', sc.id, { scenarios: allScenarios })));
    return PROGRAMS.filter((p) => ids.has(p.id));
  }, [hidden, allScenarios]);

  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [shelfProblem, setShelfProblem] = useState<string | null>(null);
  const [preset, setPreset] = useState<string | null>(null);
  const [bound, setBound] = useState<ProformaScenarioInfo[]>([]);

  useEffect(() => {
    const ctrl = new AbortController();
    setShelfProblem(null);
    proformaShelf(showArchived, ctrl.signal)
      .then(setShelf)
      .catch((e: unknown) => !ctrl.signal.aborted && setShelfProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [showArchived]);

  // The service binds the seed scenarios the switch shows (GET
  // /api/proforma/scenarios, OF-BLD-019 §3.2's contract (b)); asked only
  // when one of them is on the index.
  const needsBinding = scenarios.some((sc) => sc.kind === 'biosteam' && !createdIds.includes(sc.id));
  useEffect(() => {
    if (!needsBinding) return;
    const ctrl = new AbortController();
    proformaScenarios({ host: null, includeArchived: showArchived }, ctrl.signal)
      .then(setBound)
      .catch(() => {
        /* the cards count from the shelf instead */
      });
    return () => ctrl.abort();
  }, [needsBinding, showArchived]);

  // The dialog belongs to this page: leaving the page closes it, so it does
  // not reopen on the next visit. (StrictMode's rehearsal unmount leaves the
  // route where it is, and the palette's open survives it.)
  useEffect(
    () => () => {
      if (!/^#\/proforma\/?(\?.*)?$/.test(window.location.hash)) useStore.getState().setUI({ newScenarioOpen: false });
    },
    [],
  );

  const openDialog = (flowsheetId: string | null) => {
    setPreset(flowsheetId);
    setUI({ newScenarioOpen: true });
  };

  const references = (shelf ?? []).filter((f) => f.reference);
  const flowsheets = (shelf ?? []).filter((f) => !f.reference);
  const pinnedCount = scenarios.filter((s) => s.pinned).length;
  const hiddenLine =
    hiddenPrograms.length > 0 ? (
      <HiddenByArchive
        subject={`${hidden.length} scenario${hidden.length === 1 ? '' : 's'} on file`}
        plural={hidden.length !== 1}
        programs={hiddenPrograms}
      />
    ) : null;

  return (
    <div>
      <PageHeader
        eyebrow="Cost and scale"
        title="Proforma"
        subtitle="Techno-economics on BioSTEAM: published reference biorefineries run whole on their package's defaults, and scenarios made from a flowsheet on the shelf, each input bound to records or to a named person's assumption."
        actions={
          <>
            <LinkButton to="/biorepo/compare">
              <GitCompare size={14} /> Compare
              {pinnedCount > 0 && <span className="font-num text-caption ml-1">({pinnedCount} pinned)</span>}
            </LinkButton>
            <Button variant="primary" onClick={() => openDialog(null)} data-testid="new-scenario">
              <Plus size={14} /> New scenario
            </Button>
          </>
        }
      />

      {shelfProblem && (
        <Card className="p-4 mb-5" data-testid="shelf-down">
          <p className="text-body text-signal-warn">The shelf and the reference runs are the service&rsquo;s. {shelfProblem}</p>
        </Card>
      )}

      <section className="mb-6" data-testid="reference-runs">
        <h2 className="font-serif text-section-title font-semibold mb-1 flex items-center gap-2">
          <BookOpen size={16} className="text-ink-soft" /> Reference runs
        </h2>
        <p className="text-body text-ink-soft mb-3">
          Published biorefineries from the BioSTEAM project&rsquo;s own <span className="font-num">biorefineries</span>{' '}
          package, run whole with every setting the package&rsquo;s own, before Proforma prices anything new. Each run is
          held to the values the package&rsquo;s own test asserts, and its card says how many of them it holds: how close
          this installation comes to the plant as its authors built it.
        </p>
        {shelf && references.length === 0 && (
          <p className="text-body text-ink-soft">The shelf holds no reference biorefinery for the programs showing.</p>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {references.map((f) => (
            <ReferenceCard key={f.id} info={f} />
          ))}
        </div>
      </section>

      <section className="mb-6" data-testid="flowsheets">
        <h2 className="font-serif text-section-title font-semibold mb-1 flex items-center gap-2">
          <FlaskConical size={16} className="text-ink-soft" /> Flowsheets
        </h2>
        <p className="text-body text-ink-soft mb-3">
          The flowsheets a scenario can run. None holds a process number of its own: records bind the process inputs,
          and a named person types the rest.
        </p>
        {shelf && flowsheets.length === 0 && (
          <p className="text-body">
            <NoFlowsheetLine showArchived={showArchived} />
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {flowsheets.map((f) => (
            <FlowsheetCard key={f.id} info={f} onNew={() => openDialog(f.id)} />
          ))}
        </div>
      </section>

      <section data-testid="scenarios">
        <h2 className="font-serif text-section-title font-semibold mb-1 flex items-center gap-2">
          <LineChart size={16} className="text-ink-soft" /> Scenarios
        </h2>
        {scenarios.length === 0 ? (
          <EmptyState
            title="No scenario in the programs showing yet"
            body={
              <span>
                A scenario runs one flowsheet from the shelf above: New scenario picks the flowsheet, names it and opens
                it, with its inputs listed.{hiddenLine && <> {hiddenLine}</>}
              </span>
            }
            icon={<LineChart size={28} />}
            action={
              <Button variant="primary" onClick={() => openDialog(null)}>
                <Plus size={14} /> New scenario
              </Button>
            }
          />
        ) : (
          <>
            {hiddenLine && <p className="text-caption text-ink-soft mb-3">{hiddenLine}</p>}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {scenarios.map((sc) =>
                sc.kind === 'biosteam' ? (
                  <BiosteamCard key={sc.id} scenario={sc} shelf={shelf ?? []} info={bound.find((b) => b.id === sc.id) ?? null} />
                ) : (
                  <AuthoredCard key={sc.id} scenario={sc} />
                ),
              )}
            </div>
          </>
        )}
      </section>

      {/* §8.4 — Uncertainty is live, so its reference sits on this view, below its own line. */}
      <div className="mt-8">
        <SubsystemReference id="proforma.uncertainty" />
      </div>

      <SubsystemShelf owner="Proforma" />

      <NewScenarioDialog open={dialogOpen} onClose={() => setUI({ newScenarioOpen: false })} initialFlowsheet={preset} />
    </div>
  );
}
