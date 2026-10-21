// pureOS → Builder (OF-BLD-020 §5.3; D9, D10, D14, D15, E.1‴; Appendix 2 §B).
//
//     Which units does the product pass through, with what in hand, and
//     what comes out of each?
//
// /pureos/build/:trainId opens a train this browser saved; /pureos/build/new
// (and /pureos/build) starts a fresh one, and `?from=<run artifact id>` starts
// it from a kept run's units, read by the service (`POST
// /api/pureos/train/from-run`): every unit the product passes through whose
// BioSTEAM class is a catalogue type, its outlets routed as the run routed
// them, and the units it left out with why.
//
// A TRAIN IS DATA (D9). The page holds the train's structure: its name,
// program and product; its inlet (a kept simulation's harvest, a kept run's
// stream, or a composition typed under a reviewer name, D10); its units in
// order, each a catalogue type with each outlet routed onward, to waste or
// back to an earlier unit (a later unit is never offered). Every value a
// person types is a parameter-panel override of the place's scope,
// `pureos:unit:<train id>:<unit id | inlet>` (D3), kept in the Durable tier,
// and laid into the train's params as it is sent (lib/pureos.trainSpecOf), so
// the panel and the run read the same values. Save keeps the train whole in
// `trainsMade`, with when and by whom.
//
// THE SERVICE DECIDES. The palette is the catalogue the service serves (each
// type with what it does, its inlets and outlets, what it needs, and *no cost
// model* where BioSTEAM has none); each unit's parameters are its scope as
// the service binds it over the train's chemicals; what a run would refuse
// is the service's answer (`POST /api/pureos/train/validate`, then
// `/check`), each refusal on the card of the unit it belongs to, and Run
// stays off while any stands, saying what. Run posts the whole train and
// every override of its scopes; the result is the one `pureos.train_run`
// artifact the service keeps: purity by stream (PurityByStream), recovery by
// unit (RecoveryByUnit), the stream table, the unit table with BioSTEAM's
// costs or *no cost model*, the utilities, the diagram or the units in order
// with the words why, the parameters with their sources, the basis naming
// every override with its person, and CSVs of the artifact's own numbers.
//
// THE PAGE COMPUTES NOTHING. Every number on it is the service's or a
// person's, and no numeric control is written here: every number is typed
// in the parameter panel (E.1‴).
//
// **Price this in Proforma** waits for Phase 6 (§6.1, `custom_train_v1`):
// until then it says what that adds and makes nothing.
import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDown, ArrowLeft, ArrowUp, Download, Plus, Trash2 } from 'lucide-react';
import type {
  ParamScope,
  SimulationSummary,
  StreamRow,
  TrainFromRun,
  TrainRun,
  TrainSpec,
  TrainUnitSpec,
  TrainValidation,
  UnitSpecs,
  UnitType,
  VesselSummary,
} from '@/data/types';
import { PROGRAMS, isArchived } from '@/data/programs';
import { href, navigate, useRoute } from '@/router';
import { overridesFor, timeId, useProgramFilter, useStore } from '@/store';
import { durableAvailable } from '@/lib/durable';
import { paramScope, type ParamAsk } from '@/lib/params';
import { PRODUCT_WORDS, productWords } from '@/lib/geneos';
import { fermosSimulations } from '@/lib/fermos';
import { NO_DIAGRAM, diagramSrc, stamp } from '@/lib/proforma';
import { exportCSV } from '@/lib/csv';
import {
  INLET,
  NEW_TRAIN,
  PureosDown,
  PureosRefused,
  builderFromRunPath,
  builderPath,
  checkTrain,
  fermosVessels,
  nextUnitId,
  pureosCatalogue,
  routeChoices,
  routeWords,
  runChoices,
  runTrain,
  sameTrain,
  share,
  trainFromRun,
  trainOverrides,
  trainSpecOf,
  unitOf,
  unitScope,
  unitSpecs,
  validateTrain,
  type RunChoice,
} from '@/lib/pureos';
import { fmt } from '@/engine/units';
import { Button, Callout, Card, EmptyState, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { ParameterPanel } from '@/components/ParameterPanel';
import { SourceChip, shown } from '@/components/ParameterRow';
import { ProvenanceBadge } from '@/components/Provenance';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemReference } from '@/components/ReferenceView';
import { PurityByStream, RecoveryByUnit } from '@/components/figures';
import { PUREOS_TABS } from '@/data/tabs';
import { StreamTable } from './PureOSTrain';

/** What §6.1 adds, said where the button would otherwise make a scenario. */
export const PRICE_TRAIN_WORDS =
  'Pricing a train needs a flowsheet that takes one, and Proforma’s shelf has none yet: Phase 6 (§6.1) adds custom_train_v1, a fermenter built from a fermOS vessel design followed by a train run here, priced with the TEA the shelf flowsheets use. Until then nothing is made: no scenario is created from this train.';

/** How long the page waits after a change before asking the service what a run would refuse. */
const CHECK_AFTER_MS = 400;
/** How long a place's panel waits after the train changes before asking its scope again. */
const SCOPE_AFTER_MS = 300;

const problemOf = (e: unknown) =>
  e instanceof PureosDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof PureosRefused ? e.message : e instanceof Error ? e.message : String(e);

/**
 * The BioSTEAM scenarios made in this browser, by id and name: their newest
 * runs are among the runs a train can take a stream of. Selected as the
 * store holds them and filtered here, so a render never sees a new list
 * from the store's own snapshot (React's error 185, an endless update).
 */
function useMadeScenarios(): { id: string; name: string }[] {
  const scenarios = useStore((s) => s.scenarios);
  const ids = useStore((s) => s.createdScenarioIds);
  return useMemo(
    () => scenarios.filter((sc) => ids.includes(sc.id) && sc.kind === 'biosteam').map((sc) => ({ id: sc.id, name: sc.name })),
    [scenarios, ids],
  );
}

/** A fresh train: typed broth, no unit, the active program and its product (a person changes either). */
function freshTrain(program: string, product: string): TrainSpec {
  return { id: timeId('tr'), name: 'A new train', program, product, inlet: { kind: 'typed', ref: null, streamId: null, vessel: null, params: {} }, units: [] };
}

/** The train's structure alone: what the page holds, the values living in the panel's overrides. */
const structureOf = (t: TrainSpec): TrainSpec => ({
  ...t,
  inlet: { ...t.inlet, params: {} },
  units: t.units.map((u) => ({ ...u, params: {} })),
});

export default function PureOSBuilder({ trainId }: { trainId: string }) {
  const route = useRoute();
  const fromRun = route.query.get('from');
  const durableReady = useStore((s) => s.durableReady);
  const saved = useStore((s) => (trainId !== NEW_TRAIN ? (s.trainsMade[trainId] ?? null) : null));
  const showArchived = useStore((s) => s.showArchived);
  const shows = useProgramFilter();
  const programs = PROGRAMS.filter((p) => showArchived || !isArchived(p.id));
  const products = useMemo(() => Object.keys(PRODUCT_WORDS).filter((p) => shows('product', p)), [shows]);
  const defaultProgram = programs.find((p) => p.status === 'active')?.id ?? programs[0]?.id ?? '';
  const defaultProduct = products.includes('ethanol') ? 'ethanol' : (products[0] ?? '');
  const [draft, setDraft] = useState<TrainSpec | null>(() =>
    trainId === NEW_TRAIN ? freshTrain(defaultProgram, defaultProduct) : saved ? structureOf(saved.train) : null,
  );
  const [fromInfo, setFromInfo] = useState<{ artifactId: string; answer: TrainFromRun | null; problem: string | null } | null>(null);

  // A saved train arrives with the Durable tier, read just after the page loads.
  useEffect(() => {
    if (!draft && saved) setDraft(structureOf(saved.train));
  }, [draft, saved]);

  // ?from=<run>: a fresh train read from the run's units by the service.
  useEffect(() => {
    if (trainId !== NEW_TRAIN || !fromRun) return;
    const ctrl = new AbortController();
    const id = timeId('tr');
    setFromInfo({ artifactId: fromRun, answer: null, problem: null });
    trainFromRun({ artifactId: fromRun, trainId: id, includeArchived: showArchived }, ctrl.signal)
      .then((answer) => {
        setDraft(structureOf(answer.train));
        setFromInfo({ artifactId: fromRun, answer, problem: null });
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setFromInfo({ artifactId: fromRun, answer: null, problem: problemOf(e) }));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trainId, fromRun]);

  if (!draft && !saved && trainId !== NEW_TRAIN && !durableReady && durableAvailable())
    return <p className="text-body text-ink-soft">Reading the trains kept in this browser…</p>;

  return (
    <div data-testid="pureos-builder">
      <a href={href('/pureos')} className="inline-flex items-center gap-1 text-caption text-ink-soft hover:text-accent mb-2">
        <ArrowLeft size={13} aria-hidden /> pureOS
      </a>
      <PageHeader
        eyebrow="pureOS · Builder"
        title={draft?.name ?? trainId}
        subtitle="A train, unit by unit: where its broth comes from, each unit from the catalogue with every parameter in hand and where its value comes from, and where each outlet goes. The service runs it on BioSTEAM and keeps the run; this page shows what comes back and computes nothing."
      />
      <OwnerTabs tabs={PUREOS_TABS} />

      {fromInfo && <FromRunNote info={fromInfo} />}

      {!draft ? (
        <div data-testid="builder-not-found">
          <EmptyState
            icon={<Plus size={28} />}
            title={`No train ${trainId} is saved in this browser`}
            body={
              <>
                A train built here is kept in this browser when it is saved. Start one with{' '}
                <a href={href(builderPath(NEW_TRAIN))} className="text-accent hover:underline">
                  New train
                </a>
                , or read one from a run on{' '}
                <a href={href('/pureos')} className="text-accent hover:underline">
                  pureOS
                </a>
                .
              </>
            }
          />
        </div>
      ) : (
        <Builder key={draft.id} draft={draft} setDraft={setDraft} routeId={trainId} programs={programs.map((p) => ({ id: p.id, name: p.name }))} products={products} />
      )}

      {/* D15: harvest, capture, polish and recovery are live; their reference sits where the units are chosen. */}
      <section className="mt-8" aria-label="What the field says">
        <SubsystemReference id="pureos.harvest" />
        <SubsystemReference id="pureos.capture" />
        <SubsystemReference id="pureos.polish" />
        <SubsystemReference id="pureos.recovery" />
      </section>

      <div className="mt-5">
        <ComponentTag component="pureOS" action={draft ? `train of ${draft.units.length} units, built here` : 'train builder'} />
      </div>
    </div>
  );
}

function FromRunNote({ info }: { info: { artifactId: string; answer: TrainFromRun | null; problem: string | null } }) {
  if (info.problem)
    return (
      <Callout kind="warn" title={`No train was read from run ${info.artifactId}`}>
        <p className="text-ink" data-testid="builder-from-run-refused">
          {info.problem}
        </p>
      </Callout>
    );
  if (!info.answer) return <p className="text-caption text-ink-soft">Reading the units of run {info.artifactId}…</p>;
  const a = info.answer;
  return (
    <div className="mb-4">
      <Callout kind="info" title={`Read from run ${info.artifactId}: ${a.train.units.length} units by their class`}>
        <ul className="text-caption space-y-0.5" data-testid="builder-from-run">
          {a.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        {a.unmapped.length > 0 && (
          <div className="mt-2" data-testid="builder-unmapped">
            <p className="text-caption font-medium">Left out of the train:</p>
            <ul className="text-caption space-y-0.5">
              {a.unmapped.map((m) => (
                <li key={m.unitId} data-unit={m.unitId}>
                  <span className="font-num">{m.unitId}</span> ({m.unitClass}): {m.why}
                </li>
              ))}
            </ul>
          </div>
        )}
        {a.refusals.length > 0 && (
          <ul className="text-caption text-signal-warn mt-2 space-y-0.5">
            {a.refusals.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </Callout>
    </div>
  );
}

function Builder({
  draft,
  setDraft,
  routeId,
  programs,
  products,
}: {
  draft: TrainSpec;
  setDraft: (t: TrainSpec) => void;
  routeId: string;
  programs: { id: string; name: string }[];
  products: string[];
}) {
  const overridesAll = useStore((s) => s.parameterOverrides);
  const reviewer = useStore((s) => s.reviewer).trim();
  const showArchived = useStore((s) => s.showArchived);
  const saved = useStore((s) => s.trainsMade[draft.id] ?? null);
  const saveTrain = useStore((s) => s.saveTrain);
  const clearOverride = useStore((s) => s.clearOverride);
  // Only this train's scopes: a change elsewhere asks the service nothing.
  const prefix = unitScope(draft.id, '');
  const mine = useMemo(
    () => Object.fromEntries(Object.entries(overridesAll).filter(([scope]) => scope.startsWith(prefix))),
    [overridesAll, prefix],
  );
  const spec = useMemo(() => trainSpecOf(draft, mine), [draft, mine]);
  const specKey = JSON.stringify(spec);
  const overrides = useMemo(() => trainOverrides(spec, mine), [spec, mine]);

  const [catalogue, setCatalogue] = useState<UnitType[] | null>(null);
  const [catalogueProblem, setCatalogueProblem] = useState<string | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    pureosCatalogue(ctrl.signal)
      .then(setCatalogue)
      .catch((e: unknown) => !ctrl.signal.aborted && setCatalogueProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);
  const typeOf = useMemo(() => new Map((catalogue ?? []).map((t) => [t.id, t])), [catalogue]);

  // What a run would refuse: the structure first (no worker), then the values.
  const [check, setCheck] = useState<{ key: string; answer: TrainValidation } | null>(null);
  const [checkProblem, setCheckProblem] = useState<string | null>(null);
  useEffect(() => {
    setCheckProblem(null);
    const ctrl = new AbortController();
    const asked = specKey;
    const timer = window.setTimeout(() => {
      validateTrain(spec, ctrl.signal)
        .then((v) => (v.ok ? checkTrain({ train: spec, overrides, by: reviewer || null, includeArchived: showArchived }, ctrl.signal) : v))
        .then((answer) => setCheck({ key: asked, answer }))
        .catch((e: unknown) => !ctrl.signal.aborted && setCheckProblem(problemOf(e)));
    }, CHECK_AFTER_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
    // `specKey` names the train and its values; the overrides are in it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specKey, showArchived]);
  const fresh = check && check.key === specKey ? check.answer : null;

  const [run, setRun] = useState<TrainRun | null>(null);
  const [runProblem, setRunProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef<AbortController | null>(null);
  useEffect(() => () => inFlight.current?.abort(), []);
  const canRun = !!fresh && fresh.ok && !busy;
  const doRun = () => {
    if (!canRun) return;
    inFlight.current?.abort();
    const ctrl = new AbortController();
    inFlight.current = ctrl;
    setBusy(true);
    setRunProblem(null);
    runTrain({ train: spec, overrides, by: reviewer || null, includeArchived: showArchived }, ctrl.signal)
      .then((r) => !ctrl.signal.aborted && setRun(r))
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setRunProblem(problemOf(e));
      })
      .finally(() => {
        if (inFlight.current !== ctrl) return;
        inFlight.current = null;
        setBusy(false);
      });
  };

  const change = (patch: Partial<TrainSpec>) => setDraft({ ...draft, ...patch });
  const clearScope = (place: string) => {
    for (const o of mine[unitScope(draft.id, place)] ?? []) clearOverride(o.scope, o.key);
  };
  const addUnit = (type: UnitType) => change({ units: [...draft.units, unitOf(type, nextUnitId(draft.units))] });
  const moveUnit = (i: number, by: -1 | 1) => {
    const units = [...draft.units];
    const [u] = units.splice(i, 1);
    units.splice(i + by, 0, u);
    change({ units });
  };
  const removeUnit = (i: number) => {
    clearScope(draft.units[i].id);
    change({ units: draft.units.filter((_, n) => n !== i) });
  };
  const routeOutlet = (i: number, port: string, to: string) =>
    change({ units: draft.units.map((u, n) => (n === i ? { ...u, outlets: { ...u.outlets, [port]: to } } : u)) });

  const savedSame = saved ? sameTrain(saved.train, spec) : false;
  const doSave = () => {
    if (!reviewer) return;
    saveTrain(spec, reviewer);
    if (routeId !== draft.id) navigate(builderPath(draft.id), { replace: true });
  };
  const [pricing, setPricing] = useState(false);
  const placeRefusals = (place: string) => fresh?.places[place] ?? [];

  return (
    <div className="space-y-5">
      <section aria-labelledby="builder-train" data-testid="builder-train">
        <SectionTitle>
          <span id="builder-train">The train</span>
        </SectionTitle>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Name</span>
            <input className="input min-h-[44px] w-[280px]" aria-label="Train name" data-testid="builder-name" value={draft.name} onChange={(e) => change({ name: e.target.value })} />
          </label>
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Program</span>
            <select className="input min-h-[44px]" aria-label="Program" data-testid="builder-program" value={draft.program} onChange={(e) => change({ program: e.target.value })}>
              {programs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
              {!programs.some((p) => p.id === draft.program) && <option value={draft.program}>{draft.program}</option>}
            </select>
          </label>
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Product</span>
            <select className="input min-h-[44px]" aria-label="Product" data-testid="builder-product" value={draft.product} onChange={(e) => change({ product: e.target.value })}>
              {products.map((p) => (
                <option key={p} value={p}>
                  {productWords(p).option}
                </option>
              ))}
              {!products.includes(draft.product) && <option value={draft.product}>{draft.product}</option>}
            </select>
          </label>
          <Button variant="primary" onClick={doSave} disabled={!reviewer} className="min-h-[44px]" data-testid="builder-save">
            Save
          </Button>
          <Button onClick={() => setPricing(true)} className="min-h-[44px]" data-testid="builder-price">
            Price this in Proforma
          </Button>
        </div>
        <p className="text-caption text-ink-soft mt-1" data-testid="builder-saved" data-saved={saved ? (savedSame ? 'same' : 'changed') : 'no'}>
          {!reviewer ? (
            <>
              <a className="text-accent hover:underline" href={href('/settings/corpus')}>
                Set a reviewer name in Settings
              </a>{' '}
              to save: a train is kept under the name of who saved it.
            </>
          ) : saved ? (
            savedSame ? (
              `Saved in this browser ${stamp(saved.savedAt)} by ${saved.by}.`
            ) : (
              `Saved ${stamp(saved.savedAt)} by ${saved.by}; changed since. Save keeps it as it is now.`
            )
          ) : (
            'Not saved yet: Save keeps it in this browser, with every value typed into its panels.'
          )}
        </p>
        {pricing && (
          <p className="text-caption text-ink-soft max-w-3xl mt-1" role="status" data-testid="builder-price-words">
            {PRICE_TRAIN_WORDS}
          </p>
        )}
      </section>

      <InletSection draft={draft} spec={spec} change={change} clearInlet={() => clearScope(INLET)} refusals={placeRefusals(INLET)} />

      <section aria-labelledby="builder-steps" data-testid="builder-steps">
        <SectionTitle right={<span className="font-num text-caption text-ink-soft">{draft.units.length} units</span>}>
          <span id="builder-steps">Steps, in order</span>
        </SectionTitle>
        {draft.units.length === 0 && (
          <p className="text-body text-ink-soft" data-testid="builder-no-units">
            No unit yet: add the first from the palette below. A train sends one outlet of each unit on to the next, and the last unit&rsquo;s is the product stream.
          </p>
        )}
        <div className="space-y-3">
          {draft.units.map((u, i) => (
            <UnitCard
              key={u.id}
              unit={u}
              index={i}
              count={draft.units.length}
              units={draft.units}
              type={typeOf.get(u.type) ?? null}
              spec={spec}
              refusals={placeRefusals(u.id)}
              move={(by) => moveUnit(i, by)}
              remove={() => removeUnit(i)}
              route={(port, to) => routeOutlet(i, port, to)}
            />
          ))}
        </div>
        <Palette catalogue={catalogue} problem={catalogueProblem} add={addUnit} />
      </section>

      <section aria-labelledby="builder-run" data-testid="builder-run">
        <SectionTitle>
          <span id="builder-run">Run</span>
        </SectionTitle>
        {checkProblem && <Callout kind="warn">{checkProblem}</Callout>}
        {!fresh && !checkProblem && <p className="text-caption text-ink-soft">Asking the service what a run of this train would refuse…</p>}
        {fresh && !fresh.ok && (
          <div className="text-caption" data-testid="builder-waiting" data-count={fresh.refusals.length}>
            <p className="font-medium text-signal-warn">
              {fresh.refusals.length === 1 ? 'One thing holds the run' : `${fresh.refusals.length} things hold the run`}, in the service&rsquo;s words:
            </p>
            <ul className="ml-3 list-disc">
              {fresh.refusals.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}
        {fresh && fresh.ok && (
          <p className="text-caption text-ink-soft" data-testid="builder-ready">
            Nothing holds the run: every unit and the inlet have what they need.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3 mt-2">
          <Button variant="primary" onClick={doRun} disabled={!canRun} className="min-h-[44px]" data-testid="builder-run-button">
            {busy ? 'Running…' : 'Run'}
          </Button>
          <StartFromRun />
        </div>
        {runProblem && (
          <Callout kind="warn">
            <p data-testid="builder-run-refused">{runProblem}</p>
          </Callout>
        )}
      </section>

      {run && <RunResult run={run} changed={!sameTrain(run.spec, spec)} />}
    </div>
  );
}

/** One place's parameters, as the service binds them with the train: the panel, asked again as the train changes. */
function PlacePanel({ scope, ask, groups }: { scope: string; ask: ParamAsk; groups?: string[] }) {
  const [data, setData] = useState<ParamScope | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const askKey = JSON.stringify(ask);
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      paramScope(scope, ask, ctrl.signal)
        .then((d) => {
          setData(d);
          setProblem(null);
        })
        .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    }, SCOPE_AFTER_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
    // `askKey` names the ask.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, askKey]);
  return (
    <div data-testid="place-panel" data-scope={scope}>
      {problem && (
        <p className="text-caption text-signal-warn" data-testid="place-problem">
          {problem}
        </p>
      )}
      {!data && !problem && <p className="text-caption text-ink-soft">Asking the service for these parameters…</p>}
      <ParameterPanel scope={scope} data={data} request={ask} groups={groups} />
      <StrayOverrides scope={scope} data={data} />
    </div>
  );
}

/** Values typed for a key the place no longer has (its chemicals changed): named, and each can be dropped. */
function StrayOverrides({ scope, data }: { scope: string; data: ParamScope | null }) {
  const overrides = useStore(overridesFor(scope));
  const clearOverride = useStore((s) => s.clearOverride);
  if (!data) return null;
  const keys = new Set(data.specs.map((s) => s.key));
  const stray = overrides.filter((o) => !keys.has(o.key));
  if (stray.length === 0) return null;
  return (
    <div className="text-caption text-signal-warn mt-1" data-testid="place-stray">
      Typed for a key this place no longer takes:{' '}
      {stray.map((o) => (
        <span key={o.key} className="inline-flex items-center gap-1 mr-2">
          <span className="font-num">{o.key}</span>
          <Button size="sm" className="min-h-[44px]" onClick={() => clearOverride(scope, o.key)}>
            Drop it
          </Button>
        </span>
      ))}
    </div>
  );
}

function InletSection({
  draft,
  spec,
  change,
  clearInlet,
  refusals,
}: {
  draft: TrainSpec;
  spec: TrainSpec;
  change: (patch: Partial<TrainSpec>) => void;
  clearInlet: () => void;
  refusals: string[];
}) {
  const showArchived = useStore((s) => s.showArchived);
  const inlet = draft.inlet;
  const [sims, setSims] = useState<SimulationSummary[] | null>(null);
  const [vessels, setVessels] = useState<VesselSummary[]>([]);
  const [runs, setRuns] = useState<{ choices: RunChoice[]; problems: string[] } | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const made = useMadeScenarios();
  const madeKey = made.map((m) => m.id).join();
  useEffect(() => {
    setProblem(null);
    const ctrl = new AbortController();
    if (inlet.kind === 'simulation') {
      fermosSimulations(showArchived, ctrl.signal)
        .then(setSims)
        .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
      fermosVessels(showArchived, ctrl.signal)
        .then(setVessels)
        .catch(() => undefined);
    }
    if (inlet.kind === 'run-stream')
      runChoices(showArchived, made, ctrl.signal)
        .then((r) => !ctrl.signal.aborted && setRuns(r))
        .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inlet.kind, showArchived, madeKey]);

  const setKind = (kind: TrainSpec['inlet']['kind']) => {
    if (kind === inlet.kind) return;
    // Where the broth comes from changed: the values typed for the old inlet go with it.
    clearInlet();
    change({ inlet: { kind, ref: null, streamId: null, vessel: null, params: {} } });
  };
  const chosenRun = runs?.choices.find((r) => r.artifactId === inlet.ref) ?? null;
  const complete = inlet.kind === 'typed' || (inlet.kind === 'simulation' && !!inlet.ref) || (inlet.kind === 'run-stream' && !!inlet.ref && !!inlet.streamId);
  const ofSim = vessels.filter((v) => v.source === inlet.ref);
  return (
    <section aria-labelledby="builder-inlet" data-testid="builder-inlet" data-kind={inlet.kind}>
      <SectionTitle>
        <span id="builder-inlet">Inlet: where the broth comes from</span>
      </SectionTitle>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-caption text-ink-soft">
          <span className="block mb-0.5">The broth</span>
          <select className="input min-h-[44px]" aria-label="Inlet kind" data-testid="builder-inlet-kind" value={inlet.kind} onChange={(e) => setKind(e.target.value as TrainSpec['inlet']['kind'])}>
            <option value="typed">Typed under your name, component by component</option>
            <option value="simulation">A kept fermOS simulation&rsquo;s harvest</option>
            <option value="run-stream">A stream of a kept run</option>
          </select>
        </label>
        {inlet.kind === 'simulation' && sims && (
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Simulation</span>
            <select className="input min-h-[44px]" aria-label="Simulation" data-testid="builder-inlet-simulation" value={inlet.ref ?? ''} onChange={(e) => change({ inlet: { ...inlet, ref: e.target.value || null, vessel: null } })}>
              <option value="">choose one</option>
              {sims.map((s) => (
                <option key={s.artifactId} value={s.artifactId}>
                  {s.title} · {s.strain ?? 'every strain'} · {s.artifactId}
                </option>
              ))}
            </select>
          </label>
        )}
        {inlet.kind === 'simulation' && inlet.ref && (
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Broth flow from a vessel design</span>
            <select className="input min-h-[44px]" aria-label="Vessel design" data-testid="builder-inlet-vessel" value={inlet.vessel ?? ''} onChange={(e) => change({ inlet: { ...inlet, vessel: e.target.value || null } })}>
              <option value="">none: type the broth flow below</option>
              {ofSim.map((v) => (
                <option key={v.artifactId} value={v.artifactId}>
                  {v.unitClass} · {v.artifactId}
                </option>
              ))}
            </select>
          </label>
        )}
        {inlet.kind === 'run-stream' && runs && (
          <>
            <label className="text-caption text-ink-soft">
              <span className="block mb-0.5">Run</span>
              <select className="input min-h-[44px]" aria-label="Run" data-testid="builder-inlet-run" value={inlet.ref ?? ''} onChange={(e) => change({ inlet: { ...inlet, ref: e.target.value || null, streamId: null } })}>
                <option value="">choose one</option>
                {runs.choices.map((r) => (
                  <option key={r.artifactId} value={r.artifactId}>
                    {r.label} · {r.artifactId}
                  </option>
                ))}
              </select>
            </label>
            {chosenRun && (
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Stream</span>
                <select className="input min-h-[44px]" aria-label="Stream" data-testid="builder-inlet-stream" value={inlet.streamId ?? ''} onChange={(e) => change({ inlet: { ...inlet, streamId: e.target.value || null } })}>
                  <option value="">choose one</option>
                  {chosenRun.streams.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.id} · {composition(s)}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
      </div>
      {inlet.kind === 'simulation' && sims && sims.length === 0 && (
        <p className="text-caption mt-1">
          No simulation is kept yet:{' '}
          <a className="text-accent hover:underline" href={href('/fermos/simulate')}>
            fermOS → Simulate
          </a>{' '}
          keeps one.
        </p>
      )}
      {inlet.kind === 'run-stream' && runs && runs.choices.length === 0 && (
        <p className="text-caption mt-1">No run with a stream table is kept yet: run a scenario in Proforma, a reference run, or a train here.</p>
      )}
      {runs && runs.problems.length > 0 && <p className="text-caption text-ink-soft mt-1">{runs.problems.join(' · ')}</p>}
      {problem && <Callout kind="warn">{problem}</Callout>}
      {refusals.length > 0 && (
        <ul className="text-caption text-signal-warn mt-1 space-y-0.5" data-testid="inlet-refusals">
          {refusals.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {complete ? (
        <div className="card p-3 mt-2">
          <PlacePanel scope={unitScope(draft.id, INLET)} ask={{ train: spec }} />
        </div>
      ) : (
        <p className="text-caption text-ink-soft mt-1">Choose the {inlet.kind === 'simulation' ? 'simulation' : 'run and its stream'} the broth is; its values then show here, each with its source.</p>
      )}
    </section>
  );
}

/** A stream's composition in words: its largest components and their kg/hr, as the run's table holds them. */
function composition(s: StreamRow): string {
  const top = Object.entries(s.massFlows)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  return top.length ? top.map(([k, v]) => `${k} ${fmt(v, 3)}`).join(', ') + ' kg/hr' : 'carries nothing';
}

function UnitCard({
  unit,
  index,
  count,
  units,
  type,
  spec,
  refusals,
  move,
  remove,
  route,
}: {
  unit: TrainUnitSpec;
  index: number;
  count: number;
  units: TrainUnitSpec[];
  type: UnitType | null;
  spec: TrainSpec;
  refusals: string[];
  move: (by: -1 | 1) => void;
  remove: () => void;
  route: (port: string, to: string) => void;
}) {
  const ports = (type?.insOuts ?? []).filter((p) => p.side === 'out');
  const choices = routeChoices(units, index);
  return (
    <Card className="p-3" data-testid="builder-unit" data-unit={unit.id} data-type={unit.type}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-num font-medium">{unit.id}</span>
        <span className="text-body">{type?.name ?? unit.type}</span>
        <span className="font-num text-caption text-ink-soft">{type?.biosteamClass ?? (type?.inhouseClass ? `in-house ${type.inhouseClass}` : '')}</span>
        {type && !type.costModel && (
          <span className="chip text-caption" data-testid="unit-no-cost">
            no cost model
          </span>
        )}
        <span className="ml-auto flex items-center gap-1">
          <Button onClick={() => move(-1)} disabled={index === 0} aria-label={`Move ${unit.id} up`} className="min-h-[44px]" data-testid="unit-up">
            <ArrowUp size={14} aria-hidden />
          </Button>
          <Button onClick={() => move(1)} disabled={index === count - 1} aria-label={`Move ${unit.id} down`} className="min-h-[44px]" data-testid="unit-down">
            <ArrowDown size={14} aria-hidden />
          </Button>
          <Button onClick={remove} aria-label={`Remove ${unit.id}`} className="min-h-[44px]" data-testid="unit-remove">
            <Trash2 size={14} aria-hidden />
          </Button>
        </span>
      </div>
      {type && <p className="text-caption text-ink-soft">{type.line}</p>}
      {unit.readFrom && (
        <p className="text-caption text-ink-soft" data-testid="unit-reads">
          Reads its values from unit <span className="font-num">{unit.readFrom.unit}</span> of {unit.readFrom.flowsheet}, as the package builds it.
        </p>
      )}
      <div className="flex flex-wrap items-end gap-3 mt-2" data-testid="unit-outlets">
        {ports.map((p) => (
          <label key={p.name} className="text-caption text-ink-soft">
            <span className="block mb-0.5">
              Outlet <span className="font-num">{p.name}</span> ({p.what})
            </span>
            <select
              className="input min-h-[44px]"
              aria-label={`${unit.id} outlet ${p.name}`}
              data-testid="unit-route"
              data-port={p.name}
              value={unit.outlets?.[p.name] ?? (p.onward ? 'onward' : 'waste')}
              onChange={(e) => route(p.name, e.target.value)}
            >
              {choices.map((c) => (
                <option key={c} value={c}>
                  {routeWords(c)}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {refusals.length > 0 && (
        <ul className="text-caption text-signal-warn mt-2 space-y-0.5" data-testid="unit-needs">
          {refusals.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      <details className="mt-2" open data-testid="unit-params">
        <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">Its parameters, each with its source</summary>
        <PlacePanel scope={unitScope(spec.id, unit.id)} ask={{ train: spec, unitType: unit.type }} />
      </details>
    </Card>
  );
}

function Palette({ catalogue, problem, add }: { catalogue: UnitType[] | null; problem: string | null; add: (t: UnitType) => void }) {
  const stages = useMemo(() => {
    const out: { stage: string; types: UnitType[] }[] = [];
    for (const t of catalogue ?? []) {
      const last = out[out.length - 1];
      if (last && last.stage === t.stage) last.types.push(t);
      else out.push({ stage: t.stage, types: [t] });
    }
    return out;
  }, [catalogue]);
  return (
    <section className="mt-4" aria-labelledby="builder-palette" data-testid="builder-palette">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{catalogue ? `${catalogue.length} unit types` : ''}</span>}>
        <span id="builder-palette">The palette: the catalogue&rsquo;s unit types, by stage</span>
      </SectionTitle>
      {problem && <Callout kind="warn">{problem}</Callout>}
      {!catalogue && !problem && <p className="text-caption text-ink-soft">Asking the service for its catalogue…</p>}
      <div className="space-y-3">
        {stages.map(({ stage, types }) => (
          <div key={stage} data-testid="palette-stage" data-stage={stage}>
            <h3 className="text-caption uppercase tracking-wide text-ink-soft mb-1">{stage}</h3>
            <ul className="grid md:grid-cols-2 gap-2">
              {types.map((t) => (
                <li key={t.id} className="card p-2" data-testid="palette-type" data-type={t.id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{t.name}</span>
                    <span className="font-num text-caption text-ink-soft">{t.biosteamClass ?? `in-house ${t.inhouseClass}`}</span>
                    {!t.costModel && <span className="chip text-caption">no cost model</span>}
                    <Button size="sm" className="ml-auto min-h-[44px]" onClick={() => add(t)} data-testid="palette-add" data-type={t.id} aria-label={`Add ${t.name}`}>
                      <Plus size={13} aria-hidden /> Add
                    </Button>
                  </div>
                  <p className="text-caption text-ink-soft">{t.line}</p>
                  <TypeDetails type={t} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/** What a type takes, asked when opened: its inlets and outlets, its needs, and its parameters with BioSTEAM's defaults read from its code. */
function TypeDetails({ type }: { type: UnitType }) {
  const [open, setOpen] = useState(false);
  const [specs, setSpecs] = useState<UnitSpecs | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    if (!open || specs) return;
    const ctrl = new AbortController();
    unitSpecs(type.id, ctrl.signal)
      .then(setSpecs)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [open, specs, type.id]);
  const defaults = new Map((specs?.defaults ?? []).map((d) => [d.key, d]));
  return (
    <details onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} data-testid="palette-details">
      <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">What it takes</summary>
      <ul className="text-caption space-y-0.5">
        {type.insOuts.map((p) => (
          <li key={`${p.side}-${p.name}`}>
            {p.side === 'in' ? 'In' : 'Out'} <span className="font-num">{p.name}</span>: {p.what}
            {p.onward ? ' (goes on by default)' : ''}
          </li>
        ))}
        {type.needs.map((n) => (
          <li key={n.why} className="text-ink-soft">
            Needs {n.alternatives.map((a) => a.join(' and ')).join(' or ')}: {n.why}
          </li>
        ))}
        {type.notes.map((n) => (
          <li key={n} className="text-ink-soft">
            {n}
          </li>
        ))}
      </ul>
      {problem && <p className="text-caption text-signal-warn">{problem}</p>}
      {open && !specs && !problem && <p className="text-caption text-ink-soft">Asking BioSTEAM for its parameters…</p>}
      {specs && (
        <table className="w-full text-caption mt-1" data-testid="palette-specs">
          <tbody>
            {specs.specs.map((sp) => (
              <tr key={sp.key} className="border-t border-line/60">
                <td className="py-0.5 pr-2">{sp.label}</td>
                <td className="py-0.5 pr-2 font-num">{shown(defaults.get(sp.key)?.value ?? null)}</td>
                <td className="py-0.5 text-ink-soft">{defaults.get(sp.key)?.readFrom ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </details>
  );
}

/** Start a fresh train from a kept run's units, read by the service. */
function StartFromRun() {
  const showArchived = useStore((s) => s.showArchived);
  const made = useMadeScenarios();
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState<{ choices: RunChoice[]; problems: string[] } | null>(null);
  const [chosen, setChosen] = useState('');
  useEffect(() => {
    if (!open) return;
    const ctrl = new AbortController();
    runChoices(showArchived, made, ctrl.signal)
      .then((r) => !ctrl.signal.aborted && setRuns(r))
      .catch(() => undefined);
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, showArchived]);
  return (
    <details onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} data-testid="builder-from-run-chooser">
      <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">Start from a run&rsquo;s train</summary>
      {!runs && open && <p className="text-caption text-ink-soft">Reading the runs on file…</p>}
      {runs && (
        <div className="flex flex-wrap items-end gap-2 mt-1">
          <label className="text-caption text-ink-soft">
            <span className="block mb-0.5">Run</span>
            <select className="input min-h-[44px]" aria-label="Run to start from" data-testid="builder-from-run-select" value={chosen} onChange={(e) => setChosen(e.target.value)}>
              <option value="">choose one</option>
              {runs.choices.map((r) => (
                <option key={r.artifactId} value={r.artifactId}>
                  {r.label} · {r.artifactId}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => chosen && navigate(builderFromRunPath(chosen))} disabled={!chosen} className="min-h-[44px]" data-testid="builder-from-run-go">
            Read its train
          </Button>
          {runs.choices.length === 0 && <p className="text-caption">No run with a stream table is kept yet.</p>}
        </div>
      )}
    </details>
  );
}

function RunResult({ run, changed }: { run: TrainRun; changed: boolean }) {
  const t = run.train;
  const massUnit = t.tableUnits.massFlow ?? 'kg/hr';
  const routes = Object.fromEntries(t.streams.map((s) => [s.id, { source: s.source, sink: s.sink }]));
  const [picked, setPicked] = useState<string | null>(null);
  const unit = t.units.find((u) => u.id === picked) ?? null;
  return (
    <section className="space-y-4" aria-labelledby="builder-result" data-testid="builder-result" data-artifact={run.artifactId}>
      <SectionTitle>
        <span id="builder-result">The run</span>
      </SectionTitle>
      {changed && (
        <p className="text-caption text-signal-warn" data-testid="builder-result-stale">
          The train has changed since this run: what follows is the train as it was run. Run it again to see the change.
        </p>
      )}
      <Card className="p-3">
        <div className="flex flex-wrap items-center gap-2 text-caption">
          <ProvenanceBadge p={run.provenance} />
          <span className="text-ink-soft">
            Kept as{' '}
            <a className="font-num text-ink hover:text-accent" href={href(`/biorepo/artifacts/${run.artifactId}`)}>
              {run.artifactId}
            </a>{' '}
            on {stamp(run.createdAt)} · {t.tablesSource ?? 'tables'}
          </span>
          <a className="chip" href={href(`/pureos/train/${encodeURIComponent(run.spec.id)}`)} data-testid="builder-open-train">
            Open as a train
          </a>
        </div>
      </Card>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Product" value={t.product ?? '—'} sub={t.productStream ? `in ${t.productStream}` : 'no product stream'} />
        <Stat label="Purity" value={share(run.purity.productFraction, 2)} sub="of the product stream's mass" />
        <Stat label="Overall recovery" value={share(t.overallRecovery)} sub="of what the path delivers or loses" />
        <Stat label="Units" value={String(t.units.length)} sub={`${run.costs.filter((c) => !c.costModel).length} with no cost model`} />
      </div>

      <div data-testid="builder-purity">
        <PurityByStream
          title={`How pure is the ${run.purity.product} in each stream of the train?`}
          product={run.purity.product}
          productStream={run.purity.productStream}
          streams={run.purity.streams}
          routes={routes}
          provenance={run.provenance}
          massUnit={massUnit}
          basis={run.basis}
          csvName={`purity-${run.artifactId}`}
          notes={[run.purity.note]}
        />
      </div>
      <div data-testid="builder-recovery">
        <RecoveryByUnit
          title={`How much of the ${t.product ?? 'product'} does each unit pass on?`}
          product={t.product}
          units={t.units}
          provenance={run.provenance}
          massUnit={massUnit}
          why={t.note}
          selected={picked}
          onSelect={(id) => setPicked((now) => (now === id ? null : id))}
          csvName={`recovery-${run.artifactId}`}
          notes={['Click a unit to cut the stream table below to its streams.']}
        />
      </div>
      <StreamTable train={t} unit={unit} clear={() => setPicked(null)} />
      <UnitTable run={run} />
      <Utilities run={run} />
      <Diagram run={run} />
      <InletRead run={run} />
      <Parameters run={run} />
      {(run.notes.length > 0 || run.flags.length > 0) && (
        <div className="space-y-1" data-testid="builder-notes">
          {run.notes.map((n) => (
            <p key={n} className="text-caption text-ink-soft">
              {n}
            </p>
          ))}
          {run.flags.map((f) => (
            <p key={f} className="text-caption text-signal-warn">
              {f}
            </p>
          ))}
        </div>
      )}
      <details data-testid="builder-basis">
        <summary className="cursor-pointer text-caption text-ink-soft hover:text-accent inline-flex items-center min-h-[44px]">The basis: every input of the run, with its source</summary>
        <ul className="mt-1 space-y-0.5 text-caption">
          {run.basis.inputs.map((i, n) => (
            <li key={`${i.name}-${n}`} className="text-ink-soft" data-testid="builder-basis-input" data-kind={i.source.kind} data-by={i.source.by ?? ''}>
              {i.name}: <span className="font-num text-ink">{String(i.value).length > 160 ? `${String(i.value).slice(0, 159)}…` : String(i.value)}</span> {i.unit} — {i.source.kind}
              {i.source.by ? ` by ${i.source.by}` : ''}
              {i.source.id ? ` ${i.source.id}` : ''}
              {i.source.note ? ` (${i.source.note})` : ''}
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function UnitTable({ run }: { run: TrainRun }) {
  const cost = new Map(run.costs.map((c) => [c.unit, c]));
  const headers = ['Unit', 'Type', 'Class', 'Purchase cost (USD)', 'Installed cost (USD)', 'Heating duty', 'Cooling duty', 'Power', 'Cost note'];
  const rows = run.units.map((u) => {
    const c = cost.get(u.id);
    const model = c ? c.costModel : true;
    return [
      u.id,
      c?.type ?? '',
      u.unitClass,
      model ? (c?.purchaseCost ?? u.purchaseCost) : 'no cost model',
      model ? (c?.installedCost ?? u.installedCost) : 'no cost model',
      u.heatingDuty ?? '',
      u.coolingDuty ?? '',
      u.power ?? '',
      c?.note ?? '',
    ];
  });
  return (
    <section aria-labelledby="builder-units" data-testid="builder-unit-table">
      <SectionTitle
        right={
          <button className="chip" onClick={() => exportCSV(`units-${run.artifactId}.csv`, headers, rows)}>
            <Download size={12} aria-hidden /> CSV
          </button>
        }
      >
        <span id="builder-units">Units, as BioSTEAM ran and costed them</span>
      </SectionTitle>
      <Card className="overflow-x-auto">
        <table className="w-full text-caption">
          <thead>
            <tr className="text-left text-ink-soft border-b border-line">
              {headers.map((h, i) => (
                <th key={h} className={cx('px-2 py-1.5 font-medium', i >= 3 && i <= 7 && 'text-right')}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r[0])} className="border-b border-line/60" data-testid="builder-unit-row" data-unit={String(r[0])} data-cost-model={r[3] === 'no cost model' ? 'false' : 'true'}>
                {r.map((c, i) => (
                  <td key={i} className={cx('px-2 py-1.5', i >= 3 && i <= 7 && 'font-num text-right')}>
                    {typeof c === 'number' ? fmt(c, 4) : c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-caption text-ink-soft mt-1">
        Costs are BioSTEAM&rsquo;s purchase and installed costs at its default plant cost index; an in-house unit carries no cost model and BioSTEAM costs it at nothing, which is said, never priced. Duties and power are as the run&rsquo;s unit table holds them.
      </p>
    </section>
  );
}

function Utilities({ run }: { run: TrainRun }) {
  const u = run.utilities;
  return (
    <section aria-label="Utilities" data-testid="builder-utilities">
      <SectionTitle>Utilities</SectionTitle>
      {u ? (
        <p className="text-body">
          Heating <span className="font-num">{fmt(u.heating, 4)} {u.heatingUnit}</span>, cooling{' '}
          <span className="font-num">
            {fmt(u.cooling, 4)} {u.coolingUnit}
          </span>
          , electricity{' '}
          <span className="font-num">
            {fmt(u.electricityConsumption, 4)} {u.electricityConsumptionUnit}
          </span>{' '}
          consumed and{' '}
          <span className="font-num">
            {fmt(u.electricityProduction, 4)} {u.electricityProductionUnit}
          </span>{' '}
          produced, over {u.group}.
        </p>
      ) : (
        <p className="text-caption text-ink-soft">This run keeps no utility totals.</p>
      )}
    </section>
  );
}

function Diagram({ run }: { run: TrainRun }) {
  return (
    <section aria-label="Diagram" data-testid="builder-diagram">
      <SectionTitle>Diagram</SectionTitle>
      {run.diagram ? (
        <img src={diagramSrc(run.diagram)} alt={`The train's diagram: ${run.unitOrder.join(', ')}`} className="max-w-full h-auto" />
      ) : (
        <>
          <p className="text-caption text-ink-soft" data-testid="builder-diagram-note">
            {run.diagramNote ?? NO_DIAGRAM}
          </p>
          <ol className="list-decimal pl-5 text-body font-num" data-testid="builder-unit-order">
            {run.unitOrder.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

function InletRead({ run }: { run: TrainRun }) {
  const i = run.inlet;
  return (
    <section aria-label="The inlet as built" data-testid="builder-inlet-read">
      <SectionTitle>The inlet, as the worker built it</SectionTitle>
      <p className="text-caption">
        {i.kind === 'typed' ? 'Typed' : i.kind === 'simulation' ? `Simulation ${i.ref}` : `Stream ${i.streamId} of run ${i.ref}`} · {i.phase} · {fmt(i.T, 5)} K ·{' '}
        {fmt(i.P, 6)} Pa{i.brothFlow != null ? ` · ${fmt(i.brothFlow, 4)} m³/hr` : ''}
        {i.harvestHour != null ? ` · harvested at ${fmt(i.harvestHour, 4)} h` : ''}
      </p>
      <p className="text-caption font-num">
        {Object.entries(i.flows)
          .map(([k, v]) => `${k} ${fmt(v, 4)} kg/hr`)
          .join(' · ')}
      </p>
      {i.waterNote && <p className="text-caption text-ink-soft">{i.waterNote}</p>}
      {i.absent && <p className="text-caption text-ink-soft">Absent: {i.absent}</p>}
      {i.notes.map((n) => (
        <p key={n} className="text-caption text-ink-soft">
          {n}
        </p>
      ))}
    </section>
  );
}

function Parameters({ run }: { run: TrainRun }) {
  const headers = ['Unit', 'Parameter', 'Value', 'Low', 'High', 'Origin', 'By', 'Source'];
  const rows = run.parameters.flatMap((p) =>
    p.values.map((v) => [p.unit, v.key, v.value ?? '', v.low ?? '', v.high ?? '', v.origin, v.overriddenBy ?? '', v.source?.id ?? v.source?.note ?? '']),
  );
  return (
    <section aria-labelledby="builder-params" data-testid="builder-params">
      <SectionTitle
        right={
          <button className="chip" onClick={() => exportCSV(`parameters-${run.artifactId}.csv`, headers, rows)}>
            <Download size={12} aria-hidden /> CSV
          </button>
        }
      >
        <span id="builder-params">Every parameter the run took, with its source</span>
      </SectionTitle>
      <div className="space-y-2">
        {run.parameters.map((p) => (
          <Card key={p.unit} className="p-2 overflow-x-auto">
            <p className="text-caption font-medium">
              {p.unit} · {p.type} · <span className="font-num">{p.unitClass}</span>
            </p>
            {p.values.length === 0 ? (
              <p className="text-caption text-ink-soft">Every parameter left to the class&rsquo;s own defaults.</p>
            ) : (
              <table className="w-full text-caption">
                <tbody>
                  {p.values.map((v) => (
                    <tr key={v.key} className="border-t border-line/60" data-testid="builder-param" data-unit={p.unit} data-key={v.key} data-origin={v.origin}>
                      <td className="py-1 pr-2 font-num">{v.key}</td>
                      <td className="py-1 pr-2 font-num">{shown(v.value)}</td>
                      <td className="py-1">
                        <SourceChip value={v} />
                        {v.outOfBounds && <span className="block text-signal-warn">{v.outOfBounds}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}
