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
// pureos.py`) and this page lists the trains on file, one a scenario, with the
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
// invented, and choosing a train is still not built.
import { useEffect, useMemo, useState } from 'react';
import { STORAGE_FORMATS, UNIT_OPERATIONS, UNIT_OP_STAGE_ORDER } from '@/data/vocabulary';
import { PRODUCTS } from '@/data/products';
import { PROGRAMS, isArchived } from '@/data/programs';
import type { ProgramId, TrainSummary, UnitOperationStage } from '@/data/types';
import { href, useRoute } from '@/router';
import { useProgramFilter, useStore } from '@/store';
import { PureosDown, PureosRefused, pureosTrains, share, trainPath } from '@/lib/pureos';
import { Callout, Card, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ComponentTag } from '@/components/ComponentTag';
import { HiddenByArchive } from '@/components/HiddenByArchive';
import { UnbuiltList } from '@/components/Unbuilt';
import { SubsystemShelf } from '@/components/ReferenceView';

// Recovery per unit is no longer here: the trains above read it from a run.
const PLANNED = [
  {
    what: 'Train selection',
    why: 'Propose a train for a molecule and a host, rather than reading back one a flowsheet already ran.',
  },
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
  const listed = (trains ?? []).filter(visible);
  const hidden = (trains ?? []).filter((t) => !visible(t));
  const hiddenPrograms = PROGRAMS.filter((p) => hidden.some((t) => t.program === p.id));
  return (
    <section className="mt-5" aria-labelledby="pureos-trains" data-testid="pureos-trains">
      <SectionTitle right={<span className="font-num text-caption text-ink-soft">{trains ? `${listed.length} on file` : ''}</span>}>
        <span id="pureos-trains">Trains on file</span>
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

  return (
    <>
      <PageHeader
        eyebrow="Harvest, capture, recovery"
        title="pureOS"
        subtitle="Everything after the fermenter: harvest, disruption, capture, polishing, recovery and storage. pureOS reads the train a flowsheet ran, unit by unit, from the run Proforma priced; Proforma prices a train, pureOS decides it — whether centrifugation or filtration suits a cell-wall-deficient host is a process question, not an economics one."
      />

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

      <TrainsOnFile />

      <div className="mt-5">
        <Callout kind="info" title="The vocabulary is names, not a process model">
          Everything below is a name for a step and the stage it belongs to, with the BioSTEAM classes
          that perform it. A train above is read from a run somebody made; nothing here chooses an
          operation or knows whether a train is a good one — those are the pieces that are not built.
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
          note="The trains on file and the vocabulary are the parts that exist. Everything here would need code, and none of it has any."
          items={PLANNED}
        />
      </div>

      <SubsystemShelf owner="pureOS" />

      <div className="mt-5">
        <ComponentTag component="pureOS" action={`${UNIT_OPERATIONS.length} operations; trains read from Proforma's runs`} />
      </div>
    </>
  );
}
