// A project's studies (execution prompt §7.2, §9.1 step 5): /proforma/studies.
//
// What the project asked of its plants and kept of the answers, each list as
// the service holds it (studies/):
//
//   engine runs   every run of every engine, newest first, each a link to
//                 its page: a library plant's or a flowsheet's, a Proforma
//                 scenario's (BioSTEAM's since alpha 2.2 D6, its scenario
//                 named), a kinetics run, a train run; two or more chosen are
//                 set side by side as a comparison (POST /api/studies/comparisons);
//   scenarios     a plant, its configuration and the values it sets, each a
//                 person's assumption or a model's estimate with its author,
//                 or a reading deposited at the bench, linked to its
//                 deposition, and the runs made of it; Run makes one more
//                 (POST /api/studies/scenarios/{id}/run);
//   comparisons   each a link to its page;
//   runbooks      the runbooks studies made from a run's outputs, each a link
//                 to the runbook's page, where it is locked;
//   the package   the export: study.json, study.md, each run's SFF file and the
//                 versions, one zip that opens without the service.
//
// RUN A PLANT (alpha 2.1 stage B; every engine, alpha 2.2). A person runs any
// plant the installed package holds, or openFerment's composed flowsheet, in a
// configuration it built in when discovery built it (GET /api/library), on the
// package's own values (POST /api/library/{plant}/run, in the person's name);
// the run lands in the list and its page is a link away. Configurations that
// did not build here are named with the package's words. With another engine
// registered (GET /api/engines; docs/api/engines.md), the card offers its
// things too, each run on the engine's own defaults
// (POST /api/engines/{name}/run); an engine that cannot be used is named with
// its error.
//
// Nothing here is typed as a number: a scenario's values are set on a run's
// page, each a person's assumption or a deposition's reading, or by Postdoc,
// each a labelled estimate.
import { useEffect, useState } from 'react';
import { BookOpen, Download, GitCompare, Network, Play } from 'lucide-react';
import type { EngineRun, RunReport, Runbook, StudyComparison, StudyScenario } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { stamp } from '@/lib/proforma';
import {
  StudiesDown,
  StudiesRefused,
  compareRuns,
  downloadExport,
  libraryShelf,
  listComparisons,
  listRuns,
  listScenarios,
  listEngines,
  listStudyRunbooks,
  runEngine,
  runPlant,
  runScenario,
  type EngineInfo,
  type EngineThing,
} from '@/lib/studies';
import { runnable, type LibraryPlant } from '@/lib/library';
import { NEW_TRAIN, builderCopyPath, builderPath, ranWhat } from '@/lib/pureos';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ReadingOrigin, readingNote } from '@/components/ReadingOrigin';
import { ORIGIN_WORDS } from '@/screens/ProformaRun';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

interface Held {
  runs: EngineRun[];
  scenarios: StudyScenario[];
  comparisons: StudyComparison[];
  runbooks: Runbook[];
}

const where = (plant: string, configuration: string | null) => plant + (configuration ? ` (${configuration})` : '');

/** A configuration as a person reads it: the plant's own when it names none. */
const configurationWords = (c: string | null) => c ?? 'its own';

/** What a run answered, a link to its page and to its SFF file, or the engine's words. */
function Ran({ ran }: { ran: RunReport }) {
  return (
    <p className="text-body mt-2" data-testid="run-plant-ran" data-run={ran.run.id} data-status={ran.run.status} data-engine={ran.run.engine}>
      {ran.run.status === 'done' ? 'Ran' : 'Refused'} {ranWhat(ran.run)}
      {ran.run.engine !== 'biosteam' && <> on {ran.run.engine}</>}
      {ran.run.refused && <>: {ran.run.refused}</>}.{' '}
      <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${ran.run.id}`)}>
        Run {ran.run.id}
      </a>
      {ran.run.provenance && (
        <>
          {' '}
          <ProvenanceBadge p={ran.run.provenance} compact />
        </>
      )}
      {ran.run.sff && (
        <>
          {' '}
          · its SFF file{' '}
          <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/flowsheets/${ran.run.sff.recordId}`)}>
            {ran.run.sff.recordId}
          </a>
        </>
      )}
      {ran.run.sffRefused && <span className="text-caption text-ink-soft"> · no SFF file: {ran.run.sffRefused}</span>}
    </p>
  );
}

/** BioSTEAM's things: the installed package's plants and openFerment's flowsheet, each in a configuration it built in here. */
function BiosteamPlants({ onRan }: { onRan: () => void }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [plants, setPlants] = useState<LibraryPlant[] | null>(null);
  const [plantId, setPlantId] = useState('');
  const [configuration, setConfiguration] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [ran, setRan] = useState<RunReport | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    libraryShelf(ctrl.signal)
      .then((shelf) => {
        // A plant with an entry point, or one of openFerment's flowsheets, that built here in some configuration.
        const shown = (shelf.plants ?? []).filter((p) => (p.kind === 'plant' || p.kind === 'flowsheet') && runnable(p).configurations.length > 0);
        setPlants(shown);
        const first = shown.find((p) => p.kind === 'flowsheet') ?? shown[0];
        if (first) {
          setPlantId(first.id);
          setConfiguration(runnable(first).configurations[0] ?? null);
        }
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);

  const plant = plants?.find((p) => p.id === plantId) ?? null;
  const { configurations, failed } = plant ? runnable(plant) : { configurations: [], failed: [] };
  const choose = (id: string) => {
    setPlantId(id);
    const p = plants?.find((x) => x.id === id);
    setConfiguration(p ? (runnable(p).configurations[0] ?? null) : null);
    setRan(null);
    setProblem(null);
  };
  const run = () => {
    if (!plant) return;
    setBusy(true);
    setProblem(null);
    setRan(null);
    runPlant(plant.id, configuration, reviewer)
      .then((report) => {
        setRan(report);
        onRan();
      })
      .catch((e: unknown) => setProblem(e instanceof StudiesRefused ? `${plant.id} refused: ${e.message}` : problemOf(e)))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <p className="text-caption text-ink-soft mb-2">
        Any plant the installed package holds, or openFerment&rsquo;s composed flowsheet, run whole by BioSTEAM on the package&rsquo;s own values in a
        configuration it built in here, and kept with its basis, its artifact and its SFF file.
      </p>
      {plants === null && !problem && <p className="text-body text-ink-soft">Reading the installed package…</p>}
      {plants && plants.length === 0 && <p className="text-body text-ink-soft">No plant of the installed package built here.</p>}
      {plants && plants.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-caption text-ink-soft">
            Plant
            <select className="input text-body block mt-0.5" aria-label="Plant" value={plantId} onChange={(e) => choose(e.target.value)} data-testid="run-plant-plant">
              {plants.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id}
                  {p.kind === 'flowsheet' ? ` (openFerment, composed from ${p.composedFrom ?? 'the package'})` : p.title ? ` (${p.title})` : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            Configuration
            <select
              className="input text-body block mt-0.5"
              aria-label="Configuration"
              value={configuration ?? ''}
              onChange={(e) => setConfiguration(e.target.value === '' ? null : e.target.value)}
              disabled={configurations.length <= 1}
              data-testid="run-plant-configuration"
            >
              {configurations.map((c) => (
                <option key={c ?? ''} value={c ?? ''}>
                  {configurationWords(c)}
                </option>
              ))}
            </select>
          </label>
          <Button variant="primary" disabled={busy || !reviewer || !plant} onClick={run} data-testid="run-plant-go">
            <Play size={14} /> {busy ? 'Running…' : 'Run it'}
          </Button>
        </div>
      )}
      {plant && failed.length > 0 && (
        <p className="text-caption text-ink-soft mt-2" data-testid="run-plant-failed">
          Did not build here, so not offered:{' '}
          {failed.map((f, i) => (
            <span key={f.configuration ?? ''} title={f.error}>
              {i > 0 && '; '}
              {configurationWords(f.configuration)}
            </span>
          ))}
          .
        </p>
      )}
      {!reviewer && plants && plants.length > 0 && (
        <p className="text-caption text-ink-soft mt-2">A run is asked for in a person&rsquo;s name: set yours in Settings first.</p>
      )}
      {busy && <p className="text-caption text-ink-soft mt-2">A first run starts the simulator and takes a minute or two; it stays warm after.</p>}
      {ran && <Ran ran={ran} />}
      {problem && <p className="text-caption text-signal-warn mt-2" data-testid="run-plant-problem">{problem}</p>}
    </>
  );
}

/**
 * Where a person sets the values of a thing of a core engine, by the thing's kind (docs/api/engines.md, The core's
 * `kinetics` and `train`): a family's parameters on fermOS → Simulate, a vessel's scale on fermOS → Vessel, a train's
 * values in pureOS → Builder (a train a model built, on a copy of it). Each value set there is the person's
 * assumption, and the run is kept as one row of the engine. `says` is what the thing's values are, when it is more
 * than the words for a thing whose parameters wait. `waits` marks a kind no run on the engine's own defaults can
 * compute: every kinetics family has parameters with no default (D4), so the card offers its page alone.
 */
const SETS_VALUES: Record<string, Record<string, { to: (thing: string) => string; words: string; says?: string; waits?: boolean }>> = {
  kinetics: {
    family: { to: (id) => `/fermos/simulate?family=${encodeURIComponent(id)}`, words: 'fermOS → Simulate', waits: true },
    vessel: { to: () => '/fermos/vessel', words: 'fermOS → Vessel' },
  },
  train: {
    made: {
      to: (id) => builderPath(id),
      words: 'pureOS → Builder',
      says: 'runs with the values the train holds, its records, its inlet and BioSTEAM’s own defaults: set its values on',
    },
    kept: {
      to: (id) => builderCopyPath(id),
      words: 'a copy of it in pureOS → Builder',
      says: 'runs with its records, its inlet and BioSTEAM’s own defaults: set its values on',
    },
  },
};

/**
 * Where a person makes a thing of an engine whose things are a project's own (`EngineInfo.thingsAre`), for the card of
 * a project that holds none yet: a train is saved in pureOS → Builder.
 */
const MAKES_THINGS: Record<string, { to: string; words: string }> = {
  train: { to: builderPath(NEW_TRAIN), words: 'pureOS → Builder saves one' },
};

/** Another engine's things (docs/api/engines.md), each run on the engine's own defaults in a configuration it names. */
function EngineThings({ engine, onRan }: { engine: EngineInfo; onRan: () => void }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const things = engine.things ?? [];
  const [thingId, setThingId] = useState(things[0]?.id ?? '');
  const thing = things.find((t) => t.id === thingId) ?? null;
  const configurationsOf = (t: EngineThing | null): (string | null)[] => {
    if (!t || !(t.configurations ?? []).length) return [null];
    const own = t.defaultConfiguration ?? null;
    return [own, ...(t.configurations ?? []).filter((c) => c !== own)].filter((c): c is string => c !== null);
  };
  const [configuration, setConfiguration] = useState<string | null>(configurationsOf(thing)[0] ?? null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [ran, setRan] = useState<RunReport | null>(null);
  const configurations = configurationsOf(thing);
  const setsValues = thing ? SETS_VALUES[engine.name]?.[thing.kind ?? ''] : undefined;
  const choose = (id: string) => {
    setThingId(id);
    setConfiguration(configurationsOf(things.find((t) => t.id === id) ?? null)[0] ?? null);
    setRan(null);
    setProblem(null);
  };
  const run = () => {
    if (!thing) return;
    setBusy(true);
    setProblem(null);
    setRan(null);
    runEngine(engine.name, thing.id, configuration, reviewer)
      .then((report) => {
        setRan(report);
        onRan();
      })
      .catch((e: unknown) => setProblem(e instanceof StudiesRefused ? `${thing.id} refused: ${e.message}` : problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <>
      <p className="text-caption text-ink-soft mb-2">
        What the {engine.name} engine runs ({Object.entries(engine.version ?? {}).map(([d, v]) => `${d} ${v}`).join(', ') || 'no distribution named'}),
        each on the engine&rsquo;s own defaults, kept with its basis, its artifact and its SFF file or the engine&rsquo;s words for why it has none.
      </p>
      {things.length === 0 ? (
        engine.thingsAre ? (
          <p className="text-body text-ink-soft" data-testid="run-engine-none-yet">
            The {engine.name} engine&rsquo;s things are {engine.thingsAre}, and this project holds none yet
            {MAKES_THINGS[engine.name] && (
              <>
                :{' '}
                <a className="text-accent hover:underline" href={href(MAKES_THINGS[engine.name].to)}>
                  {MAKES_THINGS[engine.name].words}
                </a>
              </>
            )}
            .
          </p>
        ) : (
          <p className="text-body text-ink-soft">The {engine.name} engine names nothing it runs.</p>
        )
      ) : (
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-caption text-ink-soft">
            Thing
            <select className="input text-body block mt-0.5" aria-label="Thing" value={thingId} onChange={(e) => choose(e.target.value)} data-testid="run-engine-thing">
              {things.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id}
                  {t.title ? ` (${t.title})` : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            Configuration
            <select
              className="input text-body block mt-0.5"
              aria-label="Configuration"
              value={configuration ?? ''}
              onChange={(e) => setConfiguration(e.target.value === '' ? null : e.target.value)}
              disabled={configurations.length <= 1}
              data-testid="run-engine-configuration"
            >
              {configurations.map((c) => (
                <option key={c ?? ''} value={c ?? ''}>
                  {configurationWords(c)}
                </option>
              ))}
            </select>
          </label>
          {!setsValues?.waits && (
            <Button variant="primary" disabled={busy || !reviewer || !thing} onClick={run} data-testid="run-engine-go">
              <Play size={14} /> {busy ? 'Running…' : 'Run it'}
            </Button>
          )}
        </div>
      )}
      {!reviewer && things.length > 0 && !setsValues?.waits && (
        <p className="text-caption text-ink-soft mt-2">A run is asked for in a person&rsquo;s name: set yours in Settings first.</p>
      )}
      {thing && setsValues && (
        <p className="text-caption text-ink-soft mt-2" data-testid="run-engine-sets-values" data-waits={setsValues.waits ? 'true' : 'false'}>
          {engine.name === 'train' && thing.title ? `${thing.title} (${thing.id})` : thing.id}{' '}
          {setsValues.waits
            ? 'has parameters with no default, which a run sets: set them on'
            : (setsValues.says ?? 'runs with values its parameters have no default for: set them on')}{' '}
          <a className="text-accent hover:underline" href={href(setsValues.to(thing.id))}>
            {setsValues.words}
          </a>
          , each your assumption; that run is one of the {engine.name} engine&rsquo;s, listed with the project&rsquo;s runs.
        </p>
      )}
      {ran && <Ran ran={ran} />}
      {problem && <Refusal words={problem} />}
    </>
  );
}

/**
 * A refusal in the engine's words: its first sentence, and the rest (each parameter that waits, each bound) folded
 * under it when there is more.
 */
function Refusal({ words }: { words: string }) {
  const cut = words.search(/[.:;](\s|$)/);
  const head = cut > 0 ? words.slice(0, cut + 1) : words;
  const rest = cut > 0 ? words.slice(cut + 1).trim() : '';
  return (
    <div className="text-caption text-signal-warn mt-2" data-testid="run-plant-problem">
      {rest ? (
        <details>
          <summary className="cursor-pointer">{head}</summary>
          <p className="mt-1">{rest}</p>
        </details>
      ) : (
        <p>{head}</p>
      )}
    </div>
  );
}

/** biosteam's scenario flowsheets (alpha 2.2 D6): a run of one is a Proforma scenario's, made on Proforma. */
function ScenarioThings({ engine }: { engine: EngineInfo | null }) {
  const things = (engine?.things ?? []).filter((t) => t.kind === 'scenario');
  if (things.length === 0) return null;
  return (
    <p className="text-caption text-ink-soft mt-2" data-testid="run-plant-scenario-things">
      BioSTEAM also runs the shelf&rsquo;s scenario flowsheets ({things.map((t) => t.title || t.id).join(', ')}): a run of one is a
      Proforma scenario&rsquo;s, with the values a person sets on it. Make one with{' '}
      <a className="text-accent hover:underline" href={href('/proforma')}>
        Proforma → New scenario
      </a>
      ; its runs are listed with the project&rsquo;s runs below.
    </p>
  );
}

/** Run a thing of any engine registered here (GET /api/engines); BioSTEAM's plants first. */
function RunAPlant({ onRan }: { onRan: () => void }) {
  const [engines, setEngines] = useState<EngineInfo[] | null>(null);
  const [engine, setEngine] = useState('biosteam');
  useEffect(() => {
    const ctrl = new AbortController();
    // With no engine list (a service that cannot read it), BioSTEAM's plants are still offered.
    listEngines(ctrl.signal)
      .then(setEngines)
      .catch(() => !ctrl.signal.aborted && setEngines([]));
    return () => ctrl.abort();
  }, []);
  const usable = (engines ?? []).filter((e) => !e.error);
  const unusable = (engines ?? []).filter((e) => e.error);
  const other = usable.find((e) => e.name === engine && e.name !== 'biosteam') ?? null;
  return (
    <Card className="p-4" data-testid="studies-run-plant">
      <h2 className="font-serif text-section-title font-semibold mb-1">Run a plant</h2>
      {usable.length > 1 && (
        <label className="text-caption text-ink-soft block mb-2">
          Engine
          <select className="input text-body block mt-0.5" aria-label="Engine" value={engine} onChange={(e) => setEngine(e.target.value)} data-testid="run-plant-engine">
            {usable.map((e) => (
              <option key={e.name} value={e.name}>
                {e.name}
                {e.conformance ? (e.conformance.ok ? ' (every conformance check holds)' : ' (a conformance check fails)') : ''}
              </option>
            ))}
          </select>
        </label>
      )}
      {other ? <EngineThings key={other.name} engine={other} onRan={onRan} /> : <BiosteamPlants onRan={onRan} />}
      {!other && <ScenarioThings engine={usable.find((e) => e.name === 'biosteam') ?? null} />}
      {unusable.length > 0 && (
        <p className="text-caption text-ink-soft mt-2" data-testid="run-plant-unusable">
          Registered and not usable here:{' '}
          {unusable.map((e, i) => (
            <span key={e.name}>
              {i > 0 && '; '}
              {e.name}: {e.error}
            </span>
          ))}
          .
        </p>
      )}
    </Card>
  );
}

/** A Proforma scenario's run kept done whose samples held no price: its outputs.values hold none (docs/api/runs.md). */
const holdsNoPrice = (r: EngineRun) =>
  r.tool === 'proforma.run' && r.status === 'done' && !(Array.isArray(r.outputs?.values) && r.outputs.values.length > 0);

function Runs({ runs, scenarios }: { runs: EngineRun[]; scenarios: StudyScenario[] }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [chosen, setChosen] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [engine, setEngine] = useState('');
  // A run's scenario by its title: a study's, or a Proforma scenario's name (its run is BioSTEAM's since alpha 2.2 D6).
  const proformaScenarios = useStore((s) => s.scenarios);
  const titles = new Map<string, string>([...proformaScenarios.map((s) => [s.id, s.name] as const), ...scenarios.map((s) => [s.id, s.title] as const)]);
  // The engines the project's runs name (docs/api/engines.md); the filter shows one engine's runs.
  const engines = [...new Set(runs.map((r) => r.engine))].sort();
  const shown = engine ? runs.filter((r) => r.engine === engine) : runs;
  // A run kept done that holds no price (a Proforma run whose samples all failed) has nothing to compare.
  const comparable = (r: EngineRun) => r.status === 'done' && !holdsNoPrice(r);
  const done = shown.filter(comparable);
  const compare = () => {
    setBusy(true);
    setProblem(null);
    compareRuns({ title: title.trim(), runIds: chosen, by: reviewer })
      .then((rep) => navigate(`/proforma/comparisons/${rep.comparison.id}`))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-4" data-testid="studies-runs">
      <h2 className="font-serif text-section-title font-semibold mb-1">Engine runs</h2>
      {runs.length === 0 ? (
        <EmptyState
          title="No engine run yet"
          body={
            <>
              A run is one computation of a registered engine, kept with its basis, its artifact and, where the engine has a plant, its SFF file.
              BioSTEAM runs a library plant or openFerment&rsquo;s flowsheet whole, and a Proforma scenario: run a plant above, or a scenario below,
              and Postdoc runs the scenarios it proposes. The kinetics engine keeps each simulation, forecast and vessel design made on{' '}
              <a className="text-accent hover:underline" href={href('/fermos/simulate')}>
                fermOS
              </a>
              , and the train engine each train run made in{' '}
              <a className="text-accent hover:underline" href={href(builderPath(NEW_TRAIN))}>
                pureOS → Builder
              </a>
              ; each one is listed here.
            </>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <p className="text-caption text-ink-soft">Newest first. Choose two or more in the order a comparison should read them: each change is reckoned from the first chosen.</p>
            <label className="text-caption text-ink-soft flex items-center gap-1">
              Engine
              <select className="input text-caption" value={engine} onChange={(e) => setEngine(e.target.value)} data-testid="studies-runs-engine">
                <option value="">every engine</option>
                {engines.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-caption">
              <thead>
                <tr className="border-b border-line text-ink-soft">
                  {['', 'Run', 'Engine', 'What it ran', 'Status', 'Provenance', 'Scenario', 'By', 'At'].map((h) => (
                    <th key={h} className="text-left py-1 pr-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.id} className="border-b border-line/50 align-top" data-testid="studies-run" data-status={r.status} data-engine={r.engine}>
                    <td className="py-1 pr-2">
                      {comparable(r) && (
                        <input
                          type="checkbox"
                          aria-label={`Compare run ${r.id}`}
                          checked={chosen.includes(r.id)}
                          onChange={(e) => setChosen((c) => (e.target.checked ? [...c, r.id] : c.filter((x) => x !== r.id)))}
                        />
                      )}
                      {chosen.includes(r.id) && <span className="font-num text-ink-soft ml-1">{chosen.indexOf(r.id) + 1}</span>}
                    </td>
                    <td className="py-1 pr-2">
                      <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${r.id}`)}>
                        {r.id}
                      </a>
                    </td>
                    <td className="py-1 pr-2 font-num">{r.engine}</td>
                    <td className="py-1 pr-2">{ranWhat(r)}</td>
                    <td className="py-1 pr-2" data-testid="studies-run-status">
                      {r.status !== 'done' ? `refused: ${r.refused ?? ''}` : holdsNoPrice(r) ? 'done, and it holds no price: its page says why' : 'done'}
                    </td>
                    <td className="py-1 pr-2">{r.provenance ? <ProvenanceBadge p={r.provenance} compact /> : '—'}</td>
                    <td className="py-1 pr-2">{r.scenarioId ? (titles.get(r.scenarioId) ?? r.scenarioId) : '—'}</td>
                    <td className="py-1 pr-2">{r.by}</td>
                    <td className="py-1 pr-2 font-num">{stamp(r.at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {done.length >= 2 && (
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <input className="input text-body" aria-label="The comparison's title" placeholder="What the comparison asks" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Button variant="primary" disabled={busy || !reviewer || chosen.length < 2 || !title.trim()} onClick={compare} data-testid="studies-compare">
                <GitCompare size={14} /> Compare the {chosen.length >= 2 ? chosen.length : ''} chosen runs
              </Button>
              {!reviewer && <span className="text-caption text-ink-soft">A comparison is made in a person&rsquo;s name: set yours in Settings first.</span>}
            </div>
          )}
          {problem && <p className="text-caption text-signal-warn mt-1">{problem}</p>}
        </>
      )}
    </Card>
  );
}

function Scenarios({ scenarios }: { scenarios: StudyScenario[] }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ id: string; words: string } | null>(null);
  const run = (s: StudyScenario) => {
    setBusy(s.id);
    setProblem(null);
    runScenario(s.id, reviewer)
      .then((rep) => navigate(`/proforma/runs/${rep.run.id}`))
      .catch((e: unknown) => setProblem({ id: s.id, words: problemOf(e) }))
      .finally(() => setBusy(null));
  };
  return (
    <Card className="p-4" data-testid="studies-scenarios">
      <h2 className="font-serif text-section-title font-semibold mb-1">Scenarios</h2>
      {scenarios.length === 0 ? (
        <EmptyState
          title="No study scenario yet"
          body={
            <>
              A scenario names a plant, its configuration and the values it sets, each a named person&rsquo;s assumption, a model&rsquo;s estimate or a
              reading deposited at the bench, checked against the plant&rsquo;s parameters. A run&rsquo;s page makes one from the values that run read
              back, each set as your assumption or to a reading, and Postdoc proposes them with each estimate labelled.
            </>
          }
        />
      ) : (
        <div className="space-y-3">
          {scenarios.map((s) => (
            <section key={s.id} className="border-t border-line/50 pt-2" data-testid="studies-scenario">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{s.title}</div>
                  <div className="text-caption text-ink-soft">
                    <span className="font-num">{s.id}</span> · on {where(s.plant, s.configuration)} · made by {s.by}, {stamp(s.at)}
                    {s.note && <> · {s.note}</>}
                  </div>
                </div>
                <Button size="sm" disabled={!!busy || !reviewer} onClick={() => run(s)} data-testid="studies-scenario-run">
                  <Play size={12} /> {busy === s.id ? 'Running…' : 'Run'}
                </Button>
              </div>
              <table className="w-full text-caption mt-1">
                <tbody>
                  {s.values.map((v) => (
                    <tr key={v.key} className="border-b border-line/40 align-top" data-origin={v.quantity.origin?.kind}>
                      <td className="py-0.5 pr-2 font-num">{v.key}</td>
                      <td className="py-0.5 pr-2 font-num">
                        {String(v.quantity.value)} {v.quantity.unit}
                      </td>
                      <td className="py-0.5 pr-2">
                        {v.quantity.origin?.kind === 'measurement' ? <ReadingOrigin origin={v.quantity.origin} /> : (ORIGIN_WORDS[v.quantity.origin?.kind ?? ''] ?? '—')}
                      </td>
                      <td className="py-0.5 pr-2">{v.quantity.origin?.by ?? '—'}</td>
                      <td className="py-0.5 pr-2 text-ink-soft">
                        {v.quantity.origin?.kind === 'measurement' ? readingNote(v.quantity.origin.note) : (v.quantity.origin?.note ?? '')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-caption text-ink-soft mt-1">
                Its runs:{' '}
                {s.runIds.length === 0
                  ? 'none yet'
                  : s.runIds.map((id, i) => (
                      <span key={id}>
                        {i > 0 && ', '}
                        <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${id}`)}>
                          {id}
                        </a>
                      </span>
                    ))}
                .{!reviewer && ' A run is asked for in a person’s name: set yours in Settings first.'}
              </p>
              {problem?.id === s.id && <p className="text-caption text-signal-warn mt-1">{problem.words}</p>}
            </section>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function ProformaStudies() {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [held, setHeld] = useState<Held | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportProblem, setExportProblem] = useState<string | null>(null);
  // Bumped when a run is made here, so the lists read the service again.
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    Promise.all([listRuns(ctrl.signal), listScenarios(ctrl.signal), listComparisons(ctrl.signal), listStudyRunbooks(ctrl.signal)])
      .then(([runs, scenarios, comparisons, runbooks]) => {
        setHeld({ runs, scenarios, comparisons, runbooks });
        setProblem(null);
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [version]);

  const exportPackage = () => {
    setExporting(true);
    setExportProblem(null);
    downloadExport(reviewer)
      .catch((e: unknown) => setExportProblem(problemOf(e)))
      .finally(() => setExporting(false));
  };

  return (
    <div data-testid="proforma-studies">
      <PageHeader
        eyebrow="Proforma · studies"
        title="Studies"
        subtitle="What this project asked of its plants and kept of the answers: engine runs, the scenarios that asked for them, comparisons and runbooks, each as the service holds it."
        actions={
          <>
            <Button onClick={exportPackage} disabled={exporting} data-testid="studies-export">
              <Download size={14} /> {exporting ? 'Packing…' : 'The export package'}
            </Button>
            <LinkButton to="/flowsheets">
              <Network size={14} /> SFF flowsheets
            </LinkButton>
            <LinkButton to="/proforma">
              <BookOpen size={14} /> Proforma
            </LinkButton>
          </>
        }
      />
      <div className="mb-4">
        <RunAPlant onRan={() => setVersion((v) => v + 1)} />
      </div>
      {exportProblem && (
        <div className="mb-4">
          <Callout kind="warn">{exportProblem}</Callout>
        </div>
      )}
      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="studies-problem">{problem}</span>
          </Callout>
        </div>
      )}
      {held && (
        <div className="space-y-4">
          <Runs runs={held.runs} scenarios={held.scenarios} />
          <Scenarios scenarios={held.scenarios} />
          <Card className="p-4" data-testid="studies-comparisons">
            <h2 className="font-serif text-section-title font-semibold mb-1">Comparisons</h2>
            {held.comparisons.length === 0 ? (
              <p className="text-body text-ink-soft">No comparison yet: choose two or more runs above and compare them.</p>
            ) : (
              <ul className="space-y-1 text-body">
                {held.comparisons.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-2" data-testid="studies-comparison">
                    <a className="underline underline-offset-2 hover:text-accent" href={href(`/proforma/comparisons/${c.id}`)}>
                      {c.title}
                    </a>
                    <ProvenanceBadge p={c.provenance} compact />
                    <span className="text-caption text-ink-soft">
                      {c.runIds.length} runs · {c.by || 'this browser'}, {stamp(c.at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-4" data-testid="studies-runbooks">
            <h2 className="font-serif text-section-title font-semibold mb-1">Runbooks</h2>
            {held.runbooks.length === 0 ? (
              <p className="text-body text-ink-soft">No study has made a runbook: a run&rsquo;s page makes one from its numbers.</p>
            ) : (
              <ul className="space-y-1 text-body">
                {held.runbooks.map((b) => (
                  <li key={b.id} className="flex flex-wrap items-center gap-2" data-testid="studies-runbook" data-locked={b.lockedAt ? 'true' : 'false'}>
                    <a className="underline underline-offset-2 hover:text-accent" href={href(`/runbooks/${b.id}`)}>
                      {b.title}
                    </a>
                    <span className="text-caption text-ink-soft">
                      {b.predictions.length} prediction{b.predictions.length === 1 ? '' : 's'} ·{' '}
                      {b.lockedAt ? (
                        <>
                          locked {stamp(b.lockedAt)} under <span className="font-num">{b.lockHash}</span>
                        </>
                      ) : (
                        'a draft, not locked'
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
