// pureOS — everything downstream of the fermenter (OF-BLD-008 §4, OF-BLD-011 §4).
//
// THE THIRD OF THE THREE STAGES. geneOS asks what the cell CAN do; fermOS asks
// what a vessel DOES achieve; pureOS asks how product becomes vial. The seam
// arriving here is the harvest step, and it carries a decision made two
// components upstream — SECRETED OR INTRACELLULAR — which dictates the entire
// train. That is stated on the screen rather than left in COMPONENTS.md,
// because a reader who does not know where the decision was made will look for
// it in the wrong place.
//
// NOT EMPTY, BUT NEARLY. The unit-operation vocabulary and `ProcessTrain.tsx`
// belong here rather than to Proforma, and the distinction is the point of the
// split: PROFORMA PRICES A TRAIN, PUREOS DECIDES IT. Asking what a
// centrifugation step costs at 10 m³ is an economics question; asking whether
// centrifugation or filtration is the right step for a cell-wall-deficient
// alga is a process question, and the two were sitting in the same place.
//
// So this screen surfaces the vocabulary that already exists — real entries,
// no invention — and names the decisions that would need code. Nothing here is
// fabricated: every operation listed is one a molecule in the catalogue
// actually declares.
import { useMemo } from 'react';
import { Filter } from 'lucide-react';
import { STORAGE_FORMATS, UNIT_OPERATIONS, UNIT_OP_STAGE_ORDER } from '@/data/vocabulary';
import { PRODUCTS } from '@/data/products';
import type { UnitOperationStage } from '@/data/types';
import { href } from '@/router';
import { Callout, Card, PageHeader, SectionTitle, Stat, cx } from '@/components/ui';
import { ComponentTag } from '@/components/ComponentTag';
import { UnbuiltList } from '@/components/Unbuilt';
import { SubsystemShelf } from '@/components/ReferenceView';

const PLANNED = [
  {
    what: 'Train selection',
    why: 'Propose a train for a molecule and a host, rather than reading back one somebody already wrote down.',
  },
  {
    what: 'Recovery and yield modelling',
    why: 'Carry a step yield through the train, so the number at the vial is derived rather than asserted.',
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

export default function PureOS() {
  // Usage is counted from the catalogue rather than declared, so an operation
  // no molecule uses shows as zero instead of being quietly dropped.
  const usage = useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of PRODUCTS) {
      for (const id of product.unitOperationIds ?? []) {
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return counts;
  }, []);

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
        subtitle="Everything after the fermenter: harvest, disruption, capture, polishing, recovery and storage. Proforma prices a train; pureOS decides it — whether centrifugation or filtration suits a cell-wall-deficient host is a process question, not an economics one."
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
          value={String(PRODUCTS.filter((p) => (p.unitOperationIds ?? []).length > 0).length)}
          sub={`of ${PRODUCTS.length} in the catalogue`}
        />
        <Stat
          label="Operations unused"
          value={String(unused)}
          sub={unused === 0 ? 'every one is on a train' : 'in the vocabulary, on no train'}
        />
      </div>

      <Callout kind="info" title="This is a vocabulary, not a process model">
        Everything below is a name for a step and the stage it belongs to. Nothing here computes a
        yield, chooses an operation, or knows whether a train is a good one — those are the pieces
        that are not built. What exists is the shared language the rest of the platform describes a
        train in, which is worth surfacing because it is real.
      </Callout>

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
                    <li key={op.id} className="py-2.5 border-b border-line/70 last:border-0">
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
          note="The vocabulary above is the part that exists. Everything here would need code, and none of it has any."
          items={PLANNED}
        />
      </div>

      <SubsystemShelf owner="pureOS" />

      <div className="mt-5">
        <ComponentTag component="pureOS" action={`${UNIT_OPERATIONS.length} operations, no process model`} />
      </div>
    </>
  );
}
