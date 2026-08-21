// `/runbook/design/:id` — the burger question, carried to a programme of work.
//
// This is where Archetype 5 ends. The tree restructures the question; this says
// what to DO about it, in what order, and what each answer would have to say to
// change the recommendation sitting on that branch.
//
// The ordering is derived and the screen says so, because a runbook whose order
// is authored is a to-do list with a thesis stapled to it. Change a cost in the
// seed and the sequence moves.
import { useMemo } from 'react';
import { ArrowUpRight, Lock } from 'lucide-react';

import {
  BURGER_PROGRAMME,
  programmeOrder,
  programmeTotals,
  type Decision,
} from '@/data/demo/runbook';
import { BURGER_TREE, DELIVERABLE_BY_ID } from '@/data/demo/archetypes';
import { FIELD_BY_ID } from '@/data/demo/core';
import { href } from '@/router';
import { PageHeader, Card, SectionTitle, Callout, EmptyState, cx } from '@/components/ui';
import { AccessionValue } from '@/components/demo/AccessionValue';
import { PatentDensity } from '@/components/demo/ProblemTree';
import { DemoFooter } from '@/components/demo/DemoFooter';

const STATUS: Record<Decision['status'], { label: string; style: React.CSSProperties }> = {
  open: { label: 'open', style: { color: 'rgb(var(--signal-warn))' } },
  leaning: { label: 'leaning', style: { color: 'rgb(var(--signal-info))' } },
  'settled-enough': { label: 'settled enough', style: { color: 'rgb(var(--signal-open))' } },
};

const gbp = (n: number) => `£${n.toLocaleString()}`;

export function RunbookDesign({ programmeId }: { programmeId: string }) {
  const p = programmeId === BURGER_PROGRAMME.id ? BURGER_PROGRAMME : BURGER_PROGRAMME;
  const order = useMemo(() => programmeOrder(p), [p]);
  const totals = useMemo(() => programmeTotals(p), [p]);
  const parent = DELIVERABLE_BY_ID[p.fromDeliverableId];
  const nodeById = useMemo(() => new Map(BURGER_TREE.map((n) => [n.id, n])), []);

  if (!p) return <EmptyState title="No programme" body={`Nothing under ${programmeId}.`} />;

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        title={p.title}
        subtitle={
          <>
            “{p.question}” ·{' '}
            {parent && (
              <a href={href(`/postdoc/tree/${parent.id}`)} className="hover:text-accent">
                ← the decomposition it came from
              </a>
            )}
          </>
        }
      />

      <Callout>
        <span className="text-ink">What is being optimised.</span> {p.objective}
      </Callout>

      <div className="grid sm:grid-cols-4 gap-3 mt-4">
        <Stat k="Decisions" v={String(totals.decisions)} />
        <Stat k="Bench weeks" v={`${totals.weeks} / ${totals.criticalPathWeeks}`} note="one bench / unlimited benches" />
        <Stat k="Consumables + analysis" v={gbp(totals.costGBP)} note="estimate, not a quote" />
        <Stat k="Dependent" v={`${totals.blocked} of ${totals.decisions}`} note="cannot be run first" />
      </div>

      <div className="text-caption text-ink-soft mt-2 max-w-prose">
        {totals.weeks} weeks is one bench running the programme in order. {totals.criticalPathWeeks} is
        the critical path — the longest chain of decisions that genuinely depend on each other, so
        it is the floor no amount of parallelism gets under. Both are computed from the table below
        rather than asserted; change a duration and they move. The costs are estimates and carry no
        tick, because a bench week and a pound figure are not measurements and must not wear the
        same mark as one.
      </div>

      <div className="mt-6">
        <SectionTitle>The programme, in order</SectionTitle>
        <div className="text-caption text-ink-soft mb-3 max-w-prose">
          Derived from information value per pound-week, subject to dependencies — not authored.
          Each row names the one measurement that would settle it and what a result would have to
          say to move the recommendation. A decisive measurement without that second half is just a
          measurement.
        </div>

        <ol className="space-y-3">
          {order.map((d, i) => {
            const node = nodeById.get(d.nodeId);
            const s = STATUS[d.status];
            const blockers = (d.blockedBy ?? []).filter((b) => order.some((x) => x.id === b));
            return (
              <li key={d.id}>
                <Card>
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="font-num text-page-title text-ink-soft">{i + 1}</span>
                    <span className="font-num text-caption text-ink-soft">{d.id}</span>
                    <span className="text-caption" style={s.style}>
                      {s.label}
                    </span>
                    {node && <PatentDensity level={node.patentDensity} />}
                    <span className="text-caption text-ink-soft ml-auto font-num whitespace-nowrap">
                      {d.weeks} wk · {gbp(d.costGBP)}
                    </span>
                  </div>

                  <div className="mt-1">{d.question}</div>

                  {node && (
                    <div className="text-caption text-ink-soft mt-0.5">
                      settles{' '}
                      <a href={href(`/postdoc/tree/${p.fromDeliverableId}`)} className="hover:text-accent">
                        {node.label}
                      </a>
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-x-6 gap-y-2 mt-3">
                    <div>
                      <div className="text-caption text-ink-soft">Standing recommendation</div>
                      <div className="text-caption">{d.standing}</div>
                    </div>
                    <div>
                      <div className="text-caption text-ink-soft">Decisive measurement</div>
                      <div className="text-caption">{d.decisiveMeasurement}</div>
                      {d.protocolId && (
                        <div className="text-caption mt-0.5">
                          under{' '}
                          <a
                            href={href(`/runbook/${d.protocolId}`)}
                            className="font-num text-accent hover:underline inline-flex items-center gap-1"
                          >
                            {d.protocolId}
                            <ArrowUpRight className="w-3 h-3" />
                          </a>
                        </div>
                      )}
                    </div>
                  </div>

                  <div
                    className="mt-3 border-l-2 pl-3"
                    style={{ borderColor: 'rgb(var(--signal-warn))' }}
                  >
                    <div className="text-caption text-ink-soft">This flips if</div>
                    <div className="text-caption">{d.flipsIf}</div>
                  </div>

                  <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 mt-3 text-caption text-ink-soft">
                    <span>
                      would produce an Accession on{' '}
                      <a href={href(`/repo/p/${d.wouldProduce}`)} className="hover:text-accent">
                        {FIELD_BY_ID[d.wouldProduce]?.name ?? d.wouldProduce}
                      </a>
                    </span>
                    {blockers.length > 0 && (
                      <span className="inline-flex items-center gap-1">
                        <Lock className="w-3 h-3" aria-hidden />
                        after {blockers.join(', ')}
                      </span>
                    )}
                  </div>

                  {d.restsOn.length > 0 && (
                    <div className="mt-2">
                      <div className="text-caption text-ink-soft">On the list because of</div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-0.5">
                        {d.restsOn.map((id) => (
                          <AccessionValue key={id} id={id} />
                        ))}
                      </div>
                    </div>
                  )}

                  {d.restsOn.length === 0 && (
                    <div className="text-caption text-ink-soft mt-2">
                      No Accession puts this on the list. It is here because the question was asked,
                      not because the record raised it — which is a different and weaker reason, and
                      the row says so rather than borrowing a citation.
                    </div>
                  )}
                </Card>
              </li>
            );
          })}
        </ol>
      </div>

      <Card className="mt-6">
        <SectionTitle>What this programme cannot decide</SectionTitle>
        <ul className="mt-2 space-y-1.5">
          {p.outOfScope.map((x, i) => (
            <li key={i} className="text-caption pl-3 relative max-w-prose">
              <span className="absolute left-0 text-ink-soft">·</span>
              {x}
            </li>
          ))}
        </ul>
        <div className="text-caption text-ink-soft mt-3 max-w-prose">
          A runbook that listed only what it can settle would read as a complete answer to the
          question at the top, and it is not one. The last row of the programme is the triangle test
          — the thing actually asked for — and it sits behind five dependencies for a reason.
        </div>
      </Card>

      <DemoFooter />
    </div>
  );
}

function Stat({ k, v, note }: { k: string; v: string; note?: string }) {
  return (
    <Card>
      <div className="text-caption text-ink-soft">{k}</div>
      <div className="font-num text-page-title mt-0.5">{v}</div>
      {note && <div className="text-caption text-ink-soft">{note}</div>}
    </Card>
  );
}
