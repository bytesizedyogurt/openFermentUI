// pureOS — everything downstream of the fermenter (OF-BLD-008 §4, OF-BLD-011 §4,
// OF-BLD-019 §4.1).
//
// THE THIRD OF THE THREE STAGES. geneOS asks what the cell CAN do; fermOS asks
// what a vessel DOES achieve; pureOS asks how product becomes vial. The seam
// arriving here is the harvest step, and it carries a decision made two
// components upstream — SECRETED OR INTRACELLULAR — which dictates the entire
// train. That is stated on the screen rather than left in COMPONENTS.md,
// because a reader who does not know where the decision was made will look for
// it in the wrong place.
//
// PUREOS READS THE TRAIN A FLOWSHEET RAN (OF-BLD-019 §4.1, D1). Proforma's run
// is one artifact holding BioSTEAM's stream and unit tables for its base case;
// the service reads that artifact unit by unit (`core/openferment_core/
// pureos/__init__.py`) and this page lists the trains on file, one a scenario, with the
// overall recovery the service read from the stream table. Each opens at
// /pureos/train/:scenarioId (PureOSTrain.tsx). Nothing here types a recovery
// or simulates anything: a train exists when somebody ran a scenario.
//
// THE VOCABULARY STAYS. The unit-operation vocabulary belongs here rather than
// to Proforma, and the distinction is the point of the split: PROFORMA PRICES
// A TRAIN, PUREOS DECIDES IT. Asking what a centrifugation step costs at 10 m³
// is an economics question; asking whether centrifugation or filtration is the
// right step for a cell-wall-deficient alga is a process question. Each entry
// names the BioSTEAM classes that perform it, so a unit in a run's train links
// to its step (`?op=` highlights it below). Every operation listed is one a
// molecule in the catalogue declares or a train BioSTEAM ships runs; none is
// invented.
//
// PUREOS BUILDS A TRAIN (OF-BLD-020 §5.3, D9). **New train** opens the
// Builder (/pureos/build/new, PureOSBuilder.tsx), where a person puts units
// from the catalogue in order with every parameter in hand and the service
// runs them on BioSTEAM. This page lists the trains built in this browser
// (the Durable tier's `trainsMade`, filtered by the program switch), the
// train runs the service keeps (`GET /api/pureos/train-runs`, an archived
// program's hidden and said so), and the trains read from Proforma's runs.
//
// A MODEL'S TRAINS ARE LISTED (OF-BLD-020 §5.R). Postdoc builds a train with
// `pureos_build` and the service keeps it as the model's (`GET
// /api/pureos/trains-kept`); *Made by Postdoc* lists each with its name,
// product, units, the model that made it and when, and its newest run (the
// service's train runs, joined by the run's `trainId`), an archived program's
// hidden with the switch and said so. **Open a copy** opens it in the Builder
// as a new train of this browser (`?copy=`); the kept train stays the model's.
//
// A TRAIN IS PROPOSED BY RULES (OF-BLD-020 §7.2, D12). **Propose a train**
// (PureOSPropose.tsx) sends a product, a host and optionally an inlet, and
// shows the service's proposal: catalogue unit types in order, each with the
// rule, the property it read and the artifact that holds it, or what is
// missing. The rules are the service's (`pureos/proposer.py`); the page
// decides nothing, and the Builder opens the proposal by its train id.
import { useEffect, useMemo, useState } from 'react';
import { STORAGE_FORMATS, UNIT_OPERATIONS, UNIT_OP_STAGE_ORDER } from '@/data/vocabulary';
import { PRODUCTS } from '@/data/products';
import { PROGRAMS, isArchived } from '@/data/programs';
import type { KeptTrain, ProgramId, TrainSummary, UnitOperationStage } from '@/data/types';
import { href, navigate, useRoute } from '@/router';
import { useProgramFilter, useStore } from '@/store';
import { NEW_TRAIN, PureosDown, PureosRefused, builderCopyPath, builderPath, pureosTrainRuns, pureosTrains, pureosTrainsKept, share, trainPath } from '@/lib/pureos';
import { stamp } from '@/lib/proforma';
import { Button, Callout, Card, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { PUREOS_TABS } from '@/data/tabs';
import { ProvenanceBadge } from '@/components/Provenance';
import { ComponentTag } from '@/components/ComponentTag';
import { HiddenByArchive } from '@/components/HiddenByArchive';
import { UnbuiltList } from '@/components/Unbuilt';
import { SubsystemShelf } from '@/components/ReferenceView';
import { ProposeTrain } from '@/screens/PureOSPropose';

// Recovery per unit is no longer here: the trains above read it from a run.
// Train selection left this list with OF-BLD-020 §7.2: Propose a train, below.
const PLANNED = [
  {
    what: 'Formulation and storage',
    why: 'Which format a product survives in, and what that costs in stability rather than in dollars.',
  },
  {
    what: 'Resin and consumable selection',
    why: 'The chemistry behind a capture step, and what it rules out downstream.',
  },
];

/**
 * The trains on file (OF-BLD-019 §4.1): the newest Proforma run of each
 * scenario, with the overall recovery the service read from its stream table.
 * The service sends every train; the program switch filters them here, so
 * the list can say what it hides and whose.
 */
function TrainsOnFile() {
  const [trains, setTrains] = useState<TrainSummary[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const showArchived = useStore((s) => s.showArchived);
  const shows = useProgramFilter();
  useEffect(() => {
    const ctrl = new AbortController();
    pureosTrains(ctrl.signal)
      .then(setTrains)
      .catch((e) => {
        if (ctrl.signal.aborted) return;
        setProblem(e instanceof PureosDown ? `${e.message} ${e.remedy}` : e instanceof PureosRefused ? e.message : String(e));
      });
    return () => ctrl.abort();
  }, []);
  const visible = (t: TrainSummary) =>
    (showArchived || !isArchived(t.program as ProgramId | null)) && (!t.scenarioId || shows('scenario', t.scenarioId));
  // A train run built in pureOS is listed with the train runs below, never twice.
  const read = (trains ?? []).filter((t) => t.tool !== TRAIN_RUN_TOOL);
  const listed = read.filter(visible);
  const hidden = read.filter((t) => !visible(t));
  const hiddenPrograms = PROGRAMS.filter((p) => hidden.some((t) => t.program === p.id));
  return (
    <section className="mt-5" aria-labelledby="pureos-trains" data-testid="pureos-trains">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{trains ? `${listed.length} on file` : ''}</span>}>
        <span id="pureos-trains">Trains read from Proforma&rsquo;s runs</span>
      </SectionTitle>
      {problem && (
        <Callout kind="warn" title="The trains are read from the service">
          <p className="text-ink">{problem}</p>
        </Callout>
      )}
      {!problem && !trains && <p className="text-body text-ink-soft">Reading the runs on file…</p>}
      {trains && listed.length === 0 && (
        <Card className="p-4" data-testid="pureos-trains-empty">
          <p className="text-body text-ink">No train for an active program is on file yet.</p>
          <p className="text-body text-ink-soft mt-1">
            A train is read from a Proforma run: open a scenario in{' '}
            <a className="text-accent hover:underline" href={href('/proforma')}>
              Proforma
            </a>
            , give each input a source (records, or an assumption under your name), and run it. pureOS then reads the
            run's units and streams here, with the recovery at each step.
          </p>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft mt-2">
              <HiddenByArchive
                subject={`${hidden.length} ${hidden.length === 1 ? 'train' : 'trains'} on file`}
                plural={hidden.length !== 1}
                programs={hiddenPrograms}
              />
            </p>
          )}
        </Card>
      )}
      {listed.length > 0 && (
        <Card className="px-4 py-1">
          <ul>
            {listed.map((t) => (
              <li key={t.artifactId} className="py-2.5 border-b border-line/70 last:border-0" data-testid="pureos-train-row">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <a className="text-body text-ink hover:text-accent" href={href(trainPath(t))}>
                    {t.scenarioName ?? t.flowsheet ?? t.artifactId}
                  </a>
                  <span className="text-caption text-ink-soft font-num">{t.flowsheet}</span>
                  <ProvenanceBadge p={t.provenance} compact />
                  <span className="ml-auto font-num text-caption text-ink" title="the share of the product the path delivers to the product stream">
                    {t.overallRecovery == null ? 'no recovery read' : `${share(t.overallRecovery)} recovered`}
                  </span>
                </div>
                <div className="text-caption text-ink-soft mt-0.5">
                  {t.unitCount} units · product {t.product ?? 'not named'} · run {t.createdAt}
                  {t.runs > 1 ? ` · newest of ${t.runs}` : ''}
                  {t.note ? ` · ${t.note}` : ''}
                </div>
              </li>
            ))}
          </ul>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft py-2">
              <HiddenByArchive
                subject={`${hidden.length} more ${hidden.length === 1 ? 'train' : 'trains'}`}
                plural={hidden.length !== 1}
                programs={hiddenPrograms}
              />
            </p>
          )}
        </Card>
      )}
    </section>
  );
}

/** The tool that keeps a train run built in pureOS (OF-BLD-020 §5.2). */
const TRAIN_RUN_TOOL = 'pureos.train_run';

/**
 * The trains built in this browser (OF-BLD-020 §5.3): the Durable tier's
 * `trainsMade`, each with when and by whom it was saved, and the newest run
 * the service keeps of it. The program switch filters them like any list.
 */
function TrainsBuiltHere({ runs, problem }: { runs: TrainSummary[] | null; problem: string | null }) {
  const made = useStore((s) => s.trainsMade);
  const showArchived = useStore((s) => s.showArchived);
  const all = Object.values(made).sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  const visible = (program: string) => showArchived || !isArchived(program as ProgramId);
  const listed = all.filter((m) => visible(m.train.program));
  const hidden = all.filter((m) => !visible(m.train.program));
  const hiddenPrograms = PROGRAMS.filter((p) => hidden.some((m) => m.train.program === p.id));
  return (
    <section className="mt-5" aria-labelledby="pureos-built" data-testid="pureos-built">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{listed.length} saved</span>}>
        <span id="pureos-built">Trains built here</span>
      </SectionTitle>
      {listed.length === 0 ? (
        <Card className="p-4" data-testid="pureos-built-empty">
          <p className="text-body text-ink">No train is saved in this browser yet.</p>
          <p className="text-body text-ink-soft mt-1">
            <strong>New train</strong> opens the Builder: choose where the broth comes from, add units from the catalogue in order, give each what it
            needs, run it, and Save.
          </p>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft mt-2">
              <HiddenByArchive subject={`${hidden.length} ${hidden.length === 1 ? 'train' : 'trains'} built here`} plural={hidden.length !== 1} programs={hiddenPrograms} />
            </p>
          )}
        </Card>
      ) : (
        <Card className="px-4 py-1">
          <ul>
            {listed.map((m) => {
              const run = runs?.find((r) => r.trainId === m.train.id) ?? null;
              return (
                <li key={m.train.id} className="py-2.5 border-b border-line/70 last:border-0" data-testid="pureos-built-row" data-train={m.train.id}>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <a className="text-body text-ink hover:text-accent" href={href(builderPath(m.train.id))}>
                      {m.train.name}
                    </a>
                    <span className="text-caption text-ink-soft font-num">{m.train.id}</span>
                    <span className="ml-auto text-caption text-ink-soft">
                      {run ? (
                        <a className="hover:text-accent" href={href(`/pureos/train/${encodeURIComponent(m.train.id)}`)}>
                          ran: {share(run.overallRecovery)} recovered
                        </a>
                      ) : problem ? (
                        'its runs are read from the service'
                      ) : runs === null ? (
                        'reading its runs on the service…'
                      ) : (
                        'no run on the service'
                      )}
                    </span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">
                    {m.train.units.length} units · product {m.train.product} · inlet {m.train.inlet.kind} · saved {stamp(m.savedAt)} by {m.by}
                  </div>
                </li>
              );
            })}
          </ul>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft py-2">
              <HiddenByArchive subject={`${hidden.length} more ${hidden.length === 1 ? 'train' : 'trains'} built here`} plural={hidden.length !== 1} programs={hiddenPrograms} />
            </p>
          )}
        </Card>
      )}
    </section>
  );
}

/**
 * The trains a model built, kept on the service (OF-BLD-020 §5.4, §5.R): each
 * with its name, product, units, the model that made it and when, and its
 * newest run on the service (joined by the run's `trainId`). The program
 * switch filters them like any list, and the list says what it hides. Open a
 * copy opens one in the Builder as a new train of this browser.
 */
function TrainsMadeByPostdoc({ runs, problem: runsProblem }: { runs: TrainSummary[] | null; problem: string | null }) {
  const [kept, setKept] = useState<KeptTrain[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const showArchived = useStore((s) => s.showArchived);
  useEffect(() => {
    const ctrl = new AbortController();
    pureosTrainsKept(ctrl.signal)
      .then(setKept)
      .catch((e) => {
        if (ctrl.signal.aborted) return;
        setProblem(e instanceof PureosDown ? `${e.message} ${e.remedy}` : e instanceof PureosRefused ? e.message : String(e));
      });
    return () => ctrl.abort();
  }, []);
  const visible = (k: KeptTrain) => showArchived || !isArchived(k.spec.program as ProgramId);
  const listed = (kept ?? []).filter(visible);
  const hidden = (kept ?? []).filter((k) => !visible(k));
  const hiddenPrograms = PROGRAMS.filter((p) => hidden.some((k) => k.spec.program === p.id));
  const hiddenLine = hidden.length > 0 && (
    <HiddenByArchive
      subject={`${hidden.length} ${listed.length ? 'more ' : ''}${hidden.length === 1 ? 'train' : 'trains'} a model built`}
      plural={hidden.length !== 1}
      programs={hiddenPrograms}
    />
  );
  return (
    <section className="mt-5" aria-labelledby="pureos-kept" data-testid="pureos-kept">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{kept ? `${listed.length} kept` : ''}</span>}>
        <span id="pureos-kept">Made by Postdoc</span>
      </SectionTitle>
      {problem && (
        <Callout kind="warn" title="The trains a model built are kept on the service">
          <p className="text-ink">{problem}</p>
        </Callout>
      )}
      {!problem && !kept && <p className="text-body text-ink-soft">Reading the trains a model built…</p>}
      {kept && listed.length === 0 && (
        <Card className="p-4" data-testid="pureos-kept-empty">
          <p className="text-body text-ink">No train built by a model is kept on this service yet.</p>
          <p className="text-body text-ink-soft mt-1">
            Postdoc builds one with <span className="font-num">pureos_build</span> when a question asks for a train, from unit type names and record ids; the
            service keeps it as the model&rsquo;s, and it is listed here, ready to open as a copy you can change and save.
          </p>
          {hiddenLine && <p className="text-caption text-ink-soft mt-2">{hiddenLine}</p>}
        </Card>
      )}
      {listed.length > 0 && (
        <Card className="px-4 py-1">
          <ul>
            {listed.map((k) => {
              const run = runs?.find((r) => r.trainId === k.spec.id) ?? null;
              return (
                <li key={k.spec.id} className="py-2.5 border-b border-line/70 last:border-0" data-testid="pureos-kept-row" data-train={k.spec.id}>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="text-body text-ink">{k.spec.name}</span>
                    <span className="text-caption text-ink-soft font-num">{k.spec.id}</span>
                    <a className="chip min-h-[44px] inline-flex items-center" href={href(builderCopyPath(k.spec.id))} data-testid="pureos-kept-copy">
                      Open a copy in the Builder
                    </a>
                    <span className="ml-auto text-caption text-ink-soft">
                      {run ? (
                        <a className="hover:text-accent" href={href(`/pureos/train/${encodeURIComponent(k.spec.id)}`)}>
                          ran: {share(run.overallRecovery)} recovered
                        </a>
                      ) : runsProblem ? (
                        'its runs are read from the service'
                      ) : runs === null ? (
                        'reading its runs on the service…'
                      ) : (
                        'no run on the service'
                      )}
                    </span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">
                    product {k.spec.product} · {k.spec.units.length} {k.spec.units.length === 1 ? 'unit' : 'units'}
                    {k.spec.units.length ? `: ${k.spec.units.map((u) => `${u.id} ${u.type}`).join(', ')}` : ''} · inlet {k.spec.inlet.kind} · built by {k.madeBy}
                    {k.effort ? ` at effort ${k.effort}` : ''}, {stamp(k.at)}
                    {k.updatedAt !== k.at ? `, last changed ${stamp(k.updatedAt)}` : ''}
                  </div>
                </li>
              );
            })}
          </ul>
          {hiddenLine && <p className="text-caption text-ink-soft py-2">{hiddenLine}</p>}
        </Card>
      )}
    </section>
  );
}

/**
 * The train runs the service keeps (OF-BLD-020 §5.2): one row a run, newest
 * first, opening at its train's id. An archived program's run is hidden with
 * the switch, and the list says so.
 */
function TrainRunsOnFile({ runs, problem }: { runs: TrainSummary[] | null; problem: string | null }) {
  const showArchived = useStore((s) => s.showArchived);
  const made = useStore((s) => s.trainsMade);
  const visible = (t: TrainSummary) => showArchived || !isArchived(t.program as ProgramId | null);
  const listed = (runs ?? []).filter(visible);
  const hidden = (runs ?? []).filter((t) => !visible(t));
  const hiddenPrograms = PROGRAMS.filter((p) => hidden.some((t) => t.program === p.id));
  return (
    <section className="mt-5" aria-labelledby="pureos-train-runs" data-testid="pureos-train-runs">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{runs ? `${listed.length} on file` : ''}</span>}>
        <span id="pureos-train-runs">Train runs on the service</span>
      </SectionTitle>
      {problem && (
        <Callout kind="warn" title="Train runs are read from the service">
          <p className="text-ink">{problem}</p>
        </Callout>
      )}
      {!problem && !runs && <p className="text-body text-ink-soft">Reading the train runs on file…</p>}
      {runs && listed.length === 0 && (
        <Card className="p-4" data-testid="pureos-train-runs-empty">
          <p className="text-body text-ink">No train built in pureOS has run on this service yet.</p>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft mt-2">
              <HiddenByArchive subject={`${hidden.length} ${hidden.length === 1 ? 'train run' : 'train runs'} on file`} plural={hidden.length !== 1} programs={hiddenPrograms} />
            </p>
          )}
        </Card>
      )}
      {listed.length > 0 && (
        <Card className="px-4 py-1">
          <ul>
            {listed.map((t) => (
              <li key={t.artifactId} className="py-2.5 border-b border-line/70 last:border-0" data-testid="pureos-train-run-row" data-train={t.trainId ?? ''}>
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <a className="text-body text-ink hover:text-accent" href={href(`/pureos/train/${encodeURIComponent(t.trainId ?? t.artifactId)}`)}>
                    {t.trainName ?? t.trainId ?? t.artifactId}
                  </a>
                  <span className="text-caption text-ink-soft font-num">{t.artifactId}</span>
                  <ProvenanceBadge p={t.provenance} compact />
                  <span className="ml-auto font-num text-caption text-ink">
                    {t.overallRecovery == null ? 'no recovery read' : `${share(t.overallRecovery)} recovered`}
                  </span>
                </div>
                <div className="text-caption text-ink-soft mt-0.5">
                  {t.unitCount} units · product {t.product ?? 'not named'} · run {t.createdAt}
                  {t.trainId && made[t.trainId] ? (
                    <>
                      {' · '}
                      <a className="text-accent hover:underline" href={href(builderPath(t.trainId))}>
                        open in the Builder
                      </a>
                    </>
                  ) : (
                    ' · built in another browser or by a tool'
                  )}
                </div>
              </li>
            ))}
          </ul>
          {hidden.length > 0 && (
            <p className="text-caption text-ink-soft py-2">
              <HiddenByArchive subject={`${hidden.length} more ${hidden.length === 1 ? 'train run' : 'train runs'}`} plural={hidden.length !== 1} programs={hiddenPrograms} />
            </p>
          )}
        </Card>
      )}
    </section>
  );
}

export default function PureOS() {
  // A unit in a train links here with `?op=<id>`: the step is outlined and
  // brought into view, so a BioSTEAM class reads as the vocabulary's word.
  const focus = useRoute().query.get('op');
  useEffect(() => {
    if (focus) document.getElementById(`op-${focus}`)?.scrollIntoView({ block: 'center' });
  }, [focus]);
  // The catalogue as it shows under the program switch (OF-BLD-016 §2), so
  // these counts agree with Dominion's and Home's.
  const shows = useProgramFilter();
  const products = useMemo(() => PRODUCTS.filter((p) => shows('product', p.id)), [shows]);
  // Usage is counted from the catalogue rather than declared, so an operation
  // no molecule uses shows as zero instead of being quietly dropped.
  const usage = useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of products) {
      for (const id of product.unitOperationIds ?? []) {
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return counts;
  }, [products]);

  const byStage = useMemo(() => {
    const groups = new Map<UnitOperationStage, typeof UNIT_OPERATIONS>();
    for (const op of UNIT_OPERATIONS) {
      const list = groups.get(op.stage) ?? [];
      list.push(op);
      groups.set(op.stage, list);
    }
    // Stage order is the vocabulary's, which is fermenter-to-vial. A product's
    // own array is the authority on its actual train; this is the display axis.
    return UNIT_OP_STAGE_ORDER.filter((s) => groups.has(s)).map((stage) => ({
      stage,
      ops: groups.get(stage)!,
    }));
  }, []);

  const unused = UNIT_OPERATIONS.filter((op) => !usage.has(op.id)).length;

  // The service's train runs, read once for both lists that show them.
  const [runs, setRuns] = useState<TrainSummary[] | null>(null);
  const [runsProblem, setRunsProblem] = useState<string | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    pureosTrainRuns(ctrl.signal)
      .then(setRuns)
      .catch((e) => {
        if (ctrl.signal.aborted) return;
        setRunsProblem(e instanceof PureosDown ? `${e.message} ${e.remedy}` : e instanceof PureosRefused ? e.message : String(e));
      });
    return () => ctrl.abort();
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Harvest, capture, recovery"
        title="pureOS"
        subtitle="Everything after the fermenter: harvest, disruption, capture, polishing, recovery and storage. pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it, and reads the train a flowsheet ran from the run Proforma priced; Proforma prices a train, pureOS decides it — whether centrifugation or filtration suits a cell-wall-deficient host is a process question, not an economics one."
      />
      <OwnerTabs tabs={PUREOS_TABS} />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <Button variant="primary" className="min-h-[44px]" onClick={() => navigate(builderPath(NEW_TRAIN))} data-testid="pureos-new-train">
          New train
        </Button>
      </div>

      <Callout kind="warn" title="The train starts with a decision made in geneOS">
        <p className="text-ink">
          <strong>Secreted or intracellular</strong> is the single choice with the largest effect
          on downstream cost, and it is a genetic design choice — made in{' '}
          <a href={href('/geneos')} className="text-accent hover:underline">
            geneOS
          </a>{' '}
          when the chassis and signal peptide are picked, long before anybody touches a column. A
          secreted product starts at centrifuge and filter. An intracellular one starts at lysis
          and inherits every problem after it. So the handoff from{' '}
          <a href={href('/fermos')} className="text-accent hover:underline">
            fermOS
          </a>{' '}
          has to carry product location, not just a titre.
        </p>
        <p className="text-ink mt-2">
          Properties flow downstream and are stored once. Thermostability is predicted in geneOS
          and consumed here, where it decides whether a heat step can replace most of the capture
          chromatography — it is not a pureOS field, and duplicating it would create two answers
          to one question.
        </p>
      </Callout>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-5">
        <Stat label="Unit operations" value={String(UNIT_OPERATIONS.length)} sub={`across ${byStage.length} stages`} />
        <Stat label="Storage formats" value={String(STORAGE_FORMATS.length)} sub="how a product is kept" />
        <Stat
          label="Molecules with a train"
          value={String(products.filter((p) => (p.unitOperationIds ?? []).length > 0).length)}
          sub={`of ${products.length} in the catalogue`}
        />
        <Stat
          label="Operations unused"
          value={String(unused)}
          sub={unused === 0 ? 'every one is on a train' : 'in the vocabulary, on no train'}
        />
      </div>

      <TrainsBuiltHere runs={runs} problem={runsProblem} />

      <TrainsMadeByPostdoc runs={runs} problem={runsProblem} />

      <TrainRunsOnFile runs={runs} problem={runsProblem} />

      <TrainsOnFile />

      <ProposeTrain />

      <div className="mt-5">
        <Callout kind="info" title="The vocabulary is names, not a process model">
          Everything below is a name for a step and the stage it belongs to, with the BioSTEAM classes
          that perform it. A train above is built by a person in the Builder or read from a run somebody
          made, and a proposed one is the service's rules, each naming the property it read; nothing here
          knows whether a train is a good one — that is the piece that is not built.
          What exists is the shared language the rest of the platform describes a train in.
        </Callout>
      </div>

      <div className="mt-5 space-y-5">
        {byStage.map(({ stage, ops }) => (
          <section key={stage} aria-labelledby={`stage-${stage}`}>
            <SectionTitle
              right={
                <span className="font-num text-caption text-ink-soft">
                  {ops.length} {ops.length === 1 ? 'operation' : 'operations'}
                </span>
              }
            >
              <span id={`stage-${stage}`} className="capitalize">
                {stage}
              </span>
            </SectionTitle>
            <Card className="px-4 py-1">
              <ul>
                {ops.map((op) => {
                  const used = usage.get(op.id) ?? 0;
                  return (
                    <li
                      key={op.id}
                      id={`op-${op.id}`}
                      data-testid="pureos-operation"
                      data-focused={focus === op.id ? 'true' : undefined}
                      className={cx(
                        'py-2.5 border-b border-line/70 last:border-0',
                        focus === op.id && 'rounded-input ring-2 ring-accent/60 px-2 -mx-2',
                      )}
                    >
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span className="font-num text-body text-ink">{op.label}</span>
                        {op.resin && (
                          <span className="text-caption text-ink-soft">{op.resin}</span>
                        )}
                        {op.scale && (
                          <span className="chip text-[11px] py-0 text-ink-soft">{op.scale}</span>
                        )}
                        <span
                          className={cx(
                            'ml-auto font-num text-caption shrink-0',
                            used > 0 ? 'text-ink-soft' : 'text-ink-soft/55',
                          )}
                          title={
                            used > 0
                              ? `${used} molecule${used === 1 ? '' : 's'} in the catalogue declare this step`
                              : 'no molecule in the catalogue declares this step'
                          }
                        >
                          {used > 0 ? `on ${used}` : 'on none'}
                        </span>
                      </div>
                      {op.note && (
                        <div className="text-body text-ink-soft mt-0.5">{op.note}</div>
                      )}
                      {op.biosteamClasses && op.biosteamClasses.length > 0 && (
                        <div className="text-caption text-ink-soft mt-0.5">
                          BioSTEAM: <span className="font-num">{op.biosteamClasses.join(', ')}</span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </Card>
          </section>
        ))}
      </div>

      <div className="mt-6">
        <UnbuiltList
          title="What pureOS will hold"
          note="The Builder, the trains on file and the vocabulary are the parts that exist. Everything here would need code, and none of it has any."
          items={PLANNED}
        />
      </div>

      <SubsystemShelf owner="pureOS" />

      <div className="mt-5">
        <ComponentTag component="pureOS" action={`${UNIT_OPERATIONS.length} operations; trains built here and read from runs`} />
      </div>
    </>
  );
}
