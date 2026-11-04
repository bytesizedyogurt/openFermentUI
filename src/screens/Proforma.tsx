// Proforma's index (OF-DES-001 §8.13), rebuilt around the shelf of
// flowsheets (OF-BLD-019 §3.1, D2, D5, D6).
//
// Three rows, each read from the service or the store, none written here:
//
//   Reference runs  the library shelf's reference plants (alpha 2.2 D8), the
//                   corn stover plant (the NREL 2011 design, OF-BLD-014
//                   §8.2's benchmark) and the dry-grind corn plant, each run
//                   whole on its package's own values: the price of its
//                   newest run the project keeps, when it ran, its provenance
//                   and how many of its package test's values it holds, a Run
//                   or Rerun in the person's name with the simulator's status
//                   line, and a link to its page (/proforma/reference/:plant,
//                   OF-BLD-019 §3.3), read at GET /api/library and
//                   GET /api/runs. Before Proforma prices anything new, they
//                   reproduce published biorefineries.
//   Flowsheets      every flowsheet on the shelf, with the inputs it takes
//                   and New scenario from this.
//   Scenarios       every BioSTEAM scenario of the project (alpha 2.2 D9):
//                   the price of the newest run (read from its artifact) or
//                   "not run yet", how its inputs stand as the service binds
//                   each (GET /api/proforma/scenarios), and pin.
//
// New scenario opens a chooser over the shelf (components/NewScenarioDialog)
// and makes a `biosteam` scenario that opens on its page. NOTHING here is
// disabled because a list is empty: an empty row says why and what fills it.
import { useEffect, useMemo, useState } from 'react';
import { BookOpen, FlaskConical, GitCompare, LineChart, Pin, PinOff, Play, Plus } from 'lucide-react';
import type { FlowsheetInfo, ProformaScenarioInfo, Scenario } from '@/lib/proforma';
import type { Artifact, EngineRun } from '@/lib/studies';
import { overridesFor, proformaScope, useStore } from '@/store';
import { href } from '@/router';
import { fmt } from '@/engine/units';
import { PageHeader, Card, Button, LinkButton, cx, EmptyState } from '@/components/ui';
import { Tick, ProvenanceBadge } from '@/components/Provenance';
import { SubsystemShelf } from '@/components/ReferenceView';
import { NewScenarioDialog, NoFlowsheetLine, inputSourceWords } from '@/components/NewScenarioDialog';
import {
  ProformaDown,
  REFERENCE_PLANTS,
  SIMULATOR_SAYS,
  type PriceRead,
  type SimulatorStatus,
  inputCounts,
  keptReferenceRuns,
  keptRunsOf,
  libraryPrice,
  newestRunId,
  packageChecks,
  proformaArtifact,
  proformaNewestRun,
  proformaScenarios,
  proformaShelf,
  proformaStatus,
  referencePath,
  referenceRunOf,
  retiredEntryOf,
  runPrice,
  stamp,
} from '@/lib/proforma';
import { runnable, type LibraryPlant, type LibraryShelf } from '@/lib/library';
import { StudiesRefused, libraryShelf, listRuns, runPlant } from '@/lib/studies';

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** When an artifact was computed, as a date and a minute, in UTC as the service writes it (§3.R, finding 4). */
const when = stamp;

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

function ReferenceCard({
  plant,
  shelf,
  run,
  kept,
  status,
  onRan,
}: {
  plant: LibraryPlant;
  shelf: LibraryShelf;
  /**
   * The plant's newest run on its package's own values the project keeps; null when none, undefined until the runs
   * answer, 'unread' when they could not be read.
   */
  run: EngineRun | null | undefined | 'unread';
  /** The runs the project kept from the retired reference entry for this plant (alpha 2.2 D8), newest first. */
  kept: Artifact[];
  status: SimulatorStatus | null;
  onRan: () => void;
}) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [art, setArt] = useState<Artifact | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const artifactId = run && run !== 'unread' ? run.artifactId : null;
  useEffect(() => {
    setArt(null);
    if (!artifactId) return;
    const ctrl = new AbortController();
    proformaArtifact(artifactId, ctrl.signal)
      .then(setArt)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [artifactId]);

  const go = () => {
    setBusy(true);
    setProblem(null);
    runPlant(plant.id, null, reviewer)
      .then((report) => {
        if (report.artifact) setArt(report.artifact);
        onRan();
      })
      .catch((e: unknown) => setProblem(e instanceof StudiesRefused ? `${plant.id} refused: ${e.message}` : problemOf(e)))
      .finally(() => setBusy(false));
  };

  const price = art ? libraryPrice(art) : null;
  // How many of the package test's values this run holds (§3.R, finding 30).
  const checks = packageChecks(art);
  const within = checks.filter((c) => c.within).length;
  const test = plant.tests?.find((t) => t === `test_${plant.id}`) ?? plant.tests?.[0] ?? null;
  return (
    <Card className="p-4 flex flex-col" data-testid="reference-card" data-plant={plant.id}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="chip font-num">{plant.id}</span>
        <span className="chip">reference</span>
      </div>
      <a href={href(referencePath(plant.id))} className="font-serif text-section-title font-semibold leading-snug hover:text-accent" data-testid="reference-title">
        {plant.title ?? plant.id}
      </a>
      <p className="text-caption text-ink-soft mb-2">
        From <span className="font-num">{shelf.package}, {plant.module}</span>
        {test && (
          <>
            {' '}
            · held to <span className="font-num">{test}</span>
          </>
        )}
      </p>
      <p className="text-body text-ink-soft mb-3 flex-1">
        A plant of the library shelf, run whole by BioSTEAM on the package&rsquo;s own values, and held to the values its package&rsquo;s own test
        asserts.
      </p>
      {problem && <p className="text-body text-signal-warn mb-2">{problem}</p>}
      {run === 'unread' && !art && (
        <p className="text-body text-signal-warn mb-2" data-testid="reference-runs-unread">
          Its newest run could not be read: the project&rsquo;s runs did not answer.
        </p>
      )}
      {run === null && !art && (
        <p className="text-body mb-2" data-testid="reference-not-run">
          {kept.length > 0 ? 'The library plant has not run in this project yet.' : 'Not run in this project yet.'}
        </p>
      )}
      {art && (
        <div className="space-y-1.5 mb-2" data-testid="reference-result">
          {price ? (
            <Price price={price} provenance={art.provenance} testid="reference-price" />
          ) : (
            <p className="text-body text-ink-soft">The run holds no price: the plant carries no TEA here, or its TEA solved none.</p>
          )}
          {checks.length > 0 && (
            <p className="text-caption font-num" data-testid="reference-within">
              {within} of {checks.length} values of <span className="font-num">{test ?? 'its package’s test'}</span> within the package&rsquo;s
              tolerance on this run.
            </p>
          )}
          <p className="text-caption text-ink-soft flex flex-wrap items-center gap-1.5">
            <ProvenanceBadge p={art.provenance} compact /> Ran <span className="font-num">{when(art.createdAt)}</span> ·
            kept as{' '}
            <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/proforma/runs/${art.id}`)}>
              {art.id}
            </a>
          </p>
        </div>
      )}
      {kept.length > 0 && (
        <div className="text-caption text-ink-soft mb-2" data-testid="reference-kept">
          {kept.length === 1 ? 'One run' : `${kept.length} runs`} kept from the retired entry{' '}
          <span className="font-num">{retiredEntryOf(kept[0])}</span>, the newest{' '}
          <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${encodeURIComponent(kept[0].id)}`)}>
            {kept[0].id}
          </a>{' '}
          of <span className="font-num">{when(kept[0].createdAt)}</span>; its page lists them.
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 mt-auto pt-1">
        <Button onClick={go} disabled={busy || !reviewer} data-testid="reference-run">
          <Play size={13} /> {busy ? 'Running…' : art ? 'Rerun' : 'Run'}
        </Button>
        <LinkButton to={referencePath(plant.id)}>
          <BookOpen size={13} /> Its page
        </LinkButton>
        <span className="text-caption text-ink-soft" data-testid="reference-status">
          {status ? SIMULATOR_SAYS[status.status] : 'The simulator is the service’s.'}
          {status?.error && <> {status.error}</>}
          {busy && ' A first run starts the simulator and takes a minute or two; it stays warm after.'}
          {!reviewer && ' A run is asked for in a person’s name: set yours in Settings first.'}
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
  /** The service's binding of this scenario: null when it lists none for it, undefined until it answers. */
  info: ProformaScenarioInfo | null | undefined;
}) {
  // OF-BLD-020 §2.2: a person's changes to the scenario's inputs, its scope's overrides.
  const overrides = useStore(overridesFor(proformaScope(scenario.id)));
  const fits = useStore((s) => s.proformaFits[scenario.id]);
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
  // The service's binding of the scenario (GET /api/proforma/scenarios, every scenario the project's, alpha 2.2 D9):
  // until it answers, the card counts nothing; a scenario it does not list yet (this browser's, not yet saved,
  // ADR-014) or one it could not be asked about counts from the shelf, which says what can bind.
  const refused = info?.refused ?? null;
  const counts = info === undefined || refused ? null : inputCounts(scenario, info, shelf, overrides, fits ?? {});
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
        {scenario.createdAt && (
          <>
            {' '}
            · made <span className="font-num">{when(scenario.createdAt)}</span>
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
            <a className="font-num hover:text-accent underline underline-offset-2" href={href(`/proforma/runs/${art.id}`)}>
              {art.id}
            </a>{' '}
            (<a className="hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${art.id}`)}>its artifact</a>)
          </p>
        )}
      </div>
      {refused && (
        <p className="text-caption text-signal-warn mb-3" data-testid="scenario-refused">
          The service refused its binding as it stands: {refused}
        </p>
      )}
      {counts && (
        <p className="text-caption text-ink-soft mb-3 font-num" data-testid="scenario-inputs">
          {counts.total} inputs: {counts.records} {counts.bound ? 'bound to records' : 'can bind to records'}
          {counts.computed > 0 && `, ${counts.computed} with a fermOS fit chosen`}
          {counts.kept > 0 && `, ${counts.kept} bound to ${counts.keptBy.join(' and ')}`}
          {counts.measured > 0 && `, ${counts.measured} set to a reading from the bench`}
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

// ── the index ───────────────────────────────────────────────────────────

export default function Proforma() {
  const allScenarios = useStore((s) => s.scenarios);
  const dialogOpen = useStore((s) => s.ui.newScenarioOpen);
  const setUI = useStore((s) => s.setUI);
  const scenarios = useMemo(() => allScenarios.filter((sc) => sc.kind === 'biosteam'), [allScenarios]);

  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [shelfProblem, setShelfProblem] = useState<string | null>(null);
  const [preset, setPreset] = useState<string | null>(null);
  // The service's binding of every scenario of the project; null until it answers, [] when it cannot be asked.
  const [bound, setBound] = useState<ProformaScenarioInfo[] | null>(null);
  const [library, setLibrary] = useState<LibraryShelf | null>(null);
  const [libraryProblem, setLibraryProblem] = useState<string | null>(null);
  // The project's runs of the biosteam engine, newest first; undefined until they answer, null when they cannot be read.
  const [runs, setRuns] = useState<EngineRun[] | null | undefined>(undefined);
  // The runs kept from the shelf's retired reference entries (alpha 2.2 D8); [] until they answer or when unread.
  const [kept, setKept] = useState<Artifact[]>([]);
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [ranAt, setRanAt] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setShelfProblem(null);
    proformaShelf(ctrl.signal)
      .then(setShelf)
      .catch((e: unknown) => !ctrl.signal.aborted && setShelfProblem(problemOf(e)));
    libraryShelf(ctrl.signal)
      .then(setLibrary)
      .catch((e: unknown) => !ctrl.signal.aborted && setLibraryProblem(problemOf(e)));
    // The service binds every scenario of the project (GET /api/proforma/scenarios, OF-BLD-019 §3.2's contract (b)).
    proformaScenarios({ host: null }, ctrl.signal)
      .then(setBound)
      .catch(() => !ctrl.signal.aborted && setBound([]));
    return () => ctrl.abort();
  }, []);

  // The reference plants' runs, read again after a card runs one; the simulator's status with them.
  useEffect(() => {
    const ctrl = new AbortController();
    listRuns(ctrl.signal, 'biosteam')
      .then(setRuns)
      .catch(() => !ctrl.signal.aborted && setRuns(null));
    keptReferenceRuns(ctrl.signal).then(
      (k) => !ctrl.signal.aborted && setKept(k),
      () => !ctrl.signal.aborted && setKept([]),
    );
    proformaStatus(ctrl.signal).then(setStatus, () => !ctrl.signal.aborted && setStatus(null));
    return () => ctrl.abort();
  }, [ranAt]);

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

  const references = REFERENCE_PLANTS.map((id) => library?.plants?.find((p) => p.id === id)).filter((p): p is LibraryPlant => !!p);
  const flowsheets = shelf ?? [];
  const pinnedCount = scenarios.filter((s) => s.pinned).length;

  return (
    <div>
      <PageHeader
        eyebrow="Cost and scale"
        title="Proforma"
        subtitle="Techno-economics on BioSTEAM: published plants of the library shelf run whole on their package's own values, and scenarios made from a flowsheet on the shelf, each input bound to records or to a named person's assumption."
        actions={
          <>
            <LinkButton to="/proforma/studies">
              <BookOpen size={14} /> Studies
            </LinkButton>
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

      {(shelfProblem || libraryProblem) && (
        <Card className="p-4 mb-5" data-testid="shelf-down">
          <p className="text-body text-signal-warn">The shelf and the reference runs are the service&rsquo;s. {shelfProblem ?? libraryProblem}</p>
        </Card>
      )}

      <section className="mb-6" data-testid="reference-runs">
        <h2 className="font-serif text-section-title font-semibold mb-1 flex items-center gap-2">
          <BookOpen size={16} className="text-ink-soft" /> Reference runs
        </h2>
        <p className="text-body text-ink-soft mb-3">
          Published biorefineries from the BioSTEAM project&rsquo;s own <span className="font-num">biorefineries</span>{' '}
          package, on the library shelf, run whole with every setting the package&rsquo;s own, before Proforma prices anything
          new. Each run is held to the values the package&rsquo;s own test asserts, and its card says how many of them it
          holds: how close this installation comes to the plant as its authors built it. Studies runs every other plant of
          the shelf.
        </p>
        {library && references.length === 0 && (
          <p className="text-body text-ink-soft">The library shelf holds no reference plant here.</p>
        )}
        {runs === null && <p className="text-caption text-ink-soft mb-2">The project&rsquo;s runs could not be read, so no card names its newest run.</p>}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {library &&
            references.map((p) => (
              <ReferenceCard
                key={p.id}
                plant={p}
                shelf={library}
                run={runs === undefined ? undefined : runs === null ? 'unread' : referenceRunOf(p.id, runs, runnable(p).configurations[0] ?? null)}
                kept={keptRunsOf(p.id, kept)}
                status={status}
                onRan={() => setRanAt(Date.now())}
              />
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
            <NoFlowsheetLine />
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
            title="No scenario yet"
            body="A scenario runs one flowsheet from the shelf above: New scenario picks the flowsheet, names it and opens it, with its inputs listed."
            icon={<LineChart size={28} />}
            action={
              <Button variant="primary" onClick={() => openDialog(null)}>
                <Plus size={14} /> New scenario
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {scenarios.map((sc) => (
              <BiosteamCard key={sc.id} scenario={sc} shelf={shelf ?? []} info={bound === null ? undefined : (bound.find((b) => b.id === sc.id) ?? null)} />
            ))}
          </div>
        )}
      </section>

      <SubsystemShelf owner="Proforma" />

      <NewScenarioDialog open={dialogOpen} onClose={() => setUI({ newScenarioOpen: false })} initialFlowsheet={preset} />
    </div>
  );
}
