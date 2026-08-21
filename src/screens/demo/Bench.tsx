// The Bench — six archetype entry cards (OF-DEMO-002 §3.1).
//
// The card copy is the archetype's QUESTION, not its name. "Which factor
// combinations are already excluded?" reads better than "Parameter gap", and
// more importantly it is what a reader would actually have wanted to ask; a
// menu of internal taxonomy is a menu nobody knows how to use.
//
// Below the cards: recent Ledger entries, the Notary queue depth, and one
// contradiction. The contradiction is there because the first thing a reviewer
// should see is the system declining to resolve something.
import { useMemo } from 'react';

import { DELIVERABLES, DISCLOSURES } from '@/data/demo/archetypes';
import { ACCESSIONS } from '@/data/demo/accessions';
import { FIELD_BY_ID } from '@/data/demo/core';
import { accessionsOnField, conflictPairs } from '@/lib/demo';
import { href } from '@/router';
import { PageHeader, Card, SectionTitle, cx } from '@/components/ui';
import { DemoContradictionRail } from '@/components/demo/DemoContradictionRail';
import { deliverableRoute } from './Repo';
import { DemoFooter } from '@/components/demo/DemoFooter';

/** The question each archetype answers, in the reader's words. */
const QUESTION: Record<string, string> = {
  AR1: 'Which factor combinations are already excluded, and what has nobody tried?',
  AR2: 'Which route to this molecule, and is it available to use?',
  AR3: 'What can this plant actually make, and what stops it?',
  AR4: 'What would a greenfield facility on this feedstock look like?',
  AR5: 'This question is not answerable as asked — what is it really six of?',
  AR6: 'Did this run deviate, and may its numbers be pooled with the others?',
};

const KIND_LABEL: Record<string, string> = {
  'factor-map': 'factor map + run design',
  'route-comparison': 'route comparison + claim overlay',
  'capacity-screen': 'ranked capacity screen',
  'facility-concept': 'facility concepts + capex curve',
  'problem-tree': 'problem decomposition tree',
  'excursion-verdict': 'excursion verdict',
};

export function Bench() {
  const contradiction = useMemo(() => {
    const fields = [...new Set(ACCESSIONS.map((a) => a.field))];
    for (const f of fields) {
      const accs = accessionsOnField(f as never);
      if (conflictPairs(accs).length) return f;
    }
    return null;
  }, []);

  const recent = useMemo(
    () =>
      ACCESSIONS.flatMap((a) => a.ledger.map((e) => ({ ...e, accessionId: a.id })))
        .sort((x, y) => (x.at < y.at ? 1 : -1))
        .slice(0, 4),
    [],
  );

  const urgentNow = DISCLOSURES.filter((d) => d.urgency === 'now').length;

  return (
    <div className="p-6 max-w-[1300px]">
      <PageHeader
        title="Bench"
        subtitle="Six questions, one object pool. Each one's output is another's input."
      />

      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {DELIVERABLES.map((d) => (
          <a key={d.id} href={href(deliverableRoute(d.id))} className="block">
            <Card className="h-full hover:border-accent transition-colors">
              <div className="text-caption text-ink-soft font-num">{d.archetype}</div>
              <div className="mt-1">{QUESTION[d.archetype] ?? d.query}</div>
              <div className="text-caption text-ink-soft mt-2">
                {KIND_LABEL[d.payload.kind] ?? d.payload.kind}
              </div>
              <div className="text-caption text-ink-soft mt-2 flex flex-wrap gap-x-3">
                <span className="font-num">{d.accessionIds.length} Accessions</span>
                <span
                  className="font-num"
                  style={{ color: d.disclosureCandidateIds.length ? undefined : 'rgb(var(--signal-error))' }}
                >
                  {d.disclosureCandidateIds.length} to publish
                </span>
              </div>
            </Card>
          </a>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mt-6">
        <Card>
          <SectionTitle>Notary queue</SectionTitle>
          <div className="mt-1">
            <span className="font-num text-page-title">{DISCLOSURES.length}</span>
            <span className="text-caption text-ink-soft ml-2">candidates</span>
          </div>
          {urgentNow > 0 && (
            <div className="text-caption mt-1" style={{ color: 'rgb(var(--signal-closed))' }}>
              {urgentNow} marked <span className="font-medium">now</span>
            </div>
          )}
          <a href={href('/notary/disclosures')} className="text-caption text-accent hover:underline mt-2 inline-block">
            open the queue →
          </a>
        </Card>

        <Card>
          <SectionTitle>Recent Ledger</SectionTitle>
          <ol className="mt-2 space-y-1.5">
            {recent.map((e, i) => (
              <li key={i} className="text-caption">
                <a href={href(`/repo/a/${e.accessionId}`)} className="font-num hover:text-accent">
                  {e.accessionId}
                </a>
                <span className="text-ink-soft"> · {e.at}</span>
                <div className="text-ink-soft truncate" title={e.action}>
                  {e.action}
                </div>
              </li>
            ))}
          </ol>
        </Card>

        <Card>
          <SectionTitle>Unresolved</SectionTitle>
          {contradiction ? (
            <>
              <div className="text-caption text-ink-soft mb-2">
                {FIELD_BY_ID[contradiction]?.name ?? contradiction} — two records disagree and this
                system is not resolving them.
              </div>
              <DemoContradictionRail
                field={contradiction as never}
                accessions={accessionsOnField(contradiction as never)}
                height={80}
              />
            </>
          ) : (
            <div className="text-caption text-ink-soft">
              Nothing in this pool disagrees with itself, which would be more surprising than it
              sounds.
            </div>
          )}
        </Card>
      </div>

      <DemoFooter />
    </div>
  );
}
