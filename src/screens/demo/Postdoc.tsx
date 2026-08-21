// Postdoc — Archetype 5, the decomposition tree.
//
// This is the archetype that opens the walkthrough and it is the one that
// REJECTS THE QUESTION AS POSED. A question like "how do we make a burger"
// is not answerable; it is six questions about six molecules with six
// different patent positions, and restructuring it is the answer.
//
// The tree terminates by SPAWNING Archetype 2 instances rather than by
// concluding. That is the composability demonstration — a leaf is a query, not
// a verdict — and it is why `spawnsFlowId` lives on the node.
import { useMemo } from 'react';

import { DELIVERABLES, DELIVERABLE_BY_ID, DISCLOSURES, ROUTES_3HP } from '@/data/demo/archetypes';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, Callout } from '@/components/ui';
import { BURGER_PROGRAMME, programmeTotals } from '@/data/demo/runbook';
import { ProblemTree, PatentDensity } from '@/components/demo/ProblemTree';
import { DisclosureSection } from './Fermos';
import { DemoFooter } from '@/components/demo/DemoFooter';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('postdoc', 'demo');
export function ProblemTreePage({ deliverableId }: { deliverableId: string }) {
  const dlv =
    DELIVERABLE_BY_ID[deliverableId] ?? DELIVERABLES.find((d) => d.payload.kind === 'problem-tree');

  const disclosures = useMemo(
    () => (dlv ? DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id)) : []),
    [dlv],
  );

  if (!dlv || dlv.payload.kind !== 'problem-tree') {
    return <EmptyState title="No tree" body={`No deliverable ${deliverableId} of that kind.`} />;
  }

  const { rootId, nodes, handoffFlowIds } = dlv.payload;

  // The asymmetry, computed rather than asserted: how lopsided is the patent
  // density across the branches? This is the line the room remembers, so it is
  // derived from the tree and moves if the tree does.
  const density = useMemo(() => {
    const leaves = nodes.filter((n) => !nodes.some((m) => m.parentId === n.id));
    const heavy = leaves.filter((n) => n.patentDensity === 'high' || n.patentDensity === 'very-high');
    const light = leaves.filter((n) => n.patentDensity === 'low');
    return { leaves, heavy, light };
  }, [nodes]);

  return (
    <div className="p-6 max-w-[1000px]">
      <PageHeader eyebrow={EYEBROW} title={dlv.title} subtitle={dlv.query} />

      <Callout>
        The question was not answerable as asked. What follows is the restructuring — and the
        restructuring is the answer. Of {density.leaves.length} leaves, {density.heavy.length} sit
        under heavy enclosure and {density.light.length} are effectively open. That asymmetry is
        not a fact about the biology.
      </Callout>

      <Card className="mt-4">
        <ProblemTree
          rootId={rootId}
          nodes={nodes}
          onSpawn={(n) => {
            // A leaf spawns a route comparison. Deep-linking rather than
            // opening a chat: the deliverable is a screen, and a capacity table
            // rendered inside a chat bubble is a screenshot of a screen.
            const product = n.molecularTarget ?? '';
            const route = ROUTES_3HP.find((r) => r.productId === product);
            navigate(route ? `/geneos/routes/${route.productId}` : '/geneos');
          }}
        />
      </Card>

      <Card className="mt-4">
        <SectionTitle>Patent density across the leaves</SectionTitle>
        <div className="text-caption text-ink-soft mb-2">
          Four steps, filled left to right, readable without colour. The scale is here so the
          asymmetry is visible before anybody reads a label.
        </div>
        <div className="space-y-1">
          {density.leaves.map((n) => (
            <div key={n.id} className="flex items-center gap-2 text-caption">
              <PatentDensity level={n.patentDensity} />
              <span className="min-w-0 truncate">{n.label}</span>
              <span className="text-ink-soft ml-auto shrink-0">{n.recommendation}</span>
            </div>
          ))}
        </div>
      </Card>

      {handoffFlowIds.length > 0 && (
        <Card className="mt-4">
          <SectionTitle>Terminates by spawning</SectionTitle>
          <div className="text-caption text-ink-soft">
            This deliverable does not end in a conclusion. It ends in{' '}
            {handoffFlowIds.length} further quer{handoffFlowIds.length === 1 ? 'y' : 'ies'} —{' '}
            <span className="font-num">{handoffFlowIds.join(', ')}</span> — which is what makes the
            decomposition worth doing rather than worth reading.
          </div>
        </Card>
      )}

      <Card className="mt-4">
        <SectionTitle>What to do about it</SectionTitle>
        <div className="text-caption text-ink-soft max-w-prose">
          A tree is a diagram, and a diagram is not a plan. The programme takes the branches above
          and orders them by how much each would reduce uncertainty per bench-week — naming, for
          each, the one measurement that would settle it and what a result would have to say to move
          the recommendation.
        </div>
        <a
          href={href(`/runbook/design/${BURGER_PROGRAMME.id}`)}
          className="text-caption text-accent hover:underline mt-2 inline-block"
        >
          open the decision programme — {programmeTotals().decisions} decisions, {programmeTotals().weeks} bench weeks →
        </a>
      </Card>

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </div>
  );
}
