// The Notary queue — every `DisclosureCandidate` from every archetype.
//
// OF-DEMO-002 §3.7: "This is the screen that makes the project's reason
// legible." Six archetypes each end by naming what should be defensively
// published, and this is where those land, sorted by urgency, each traceable
// back to the deliverable that produced it.
//
// AT `/notary/disclosures` AND NOT `/notary`, because `/notary` already serves
// the casein corpus's enablement checklist. The two pools are deliberately not
// merged (OF-DEMO-001 §8) and a screen serving both would be the merge in the
// one place it would be hardest to notice. The existing index links here.
//
// DELIBERATELY ABSENT: anything that publishes. A queue is a working list; a
// disclosure with a provable date is irreversible, and the step between them is
// a human's.
import { useMemo, useState } from 'react';

import type { DisclosureCandidate } from '@/data/demo/types';
import { DISCLOSURES, DELIVERABLES } from '@/data/demo/archetypes';
import { href } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, Callout, cx } from '@/components/ui';
import { DisclosureCard, URGENCY_RANK } from '@/components/demo/DisclosureCard';
import { deliverableRoute } from './Repo';
import { DemoFooter } from '@/components/demo/DemoFooter';

export function NotaryQueue() {
  const [reason, setReason] = useState<string>('all');

  const rows = useMemo(() => {
    const filtered = reason === 'all' ? DISCLOSURES : DISCLOSURES.filter((d) => d.reason === reason);
    return [...filtered].sort((a, b) => {
      const u = URGENCY_RANK[a.urgency] - URGENCY_RANK[b.urgency];
      if (u !== 0) return u;
      return (a.estimatedWindowMonths ?? 999) - (b.estimatedWindowMonths ?? 999);
    });
  }, [reason]);

  const reasons = useMemo(() => [...new Set(DISCLOSURES.map((d) => d.reason))], []);

  /** Which archetype produced each, so a row can be followed backwards. */
  const producer = useMemo(() => {
    const m = new Map<string, string>();
    for (const d of DELIVERABLES) {
      for (const id of d.disclosureCandidateIds) m.set(id, d.id);
    }
    return m;
  }, []);

  const orphans = DISCLOSURES.filter((d) => !producer.has(d.id));

  return (
    <div className="p-6 max-w-[1200px]">
      <PageHeader
        title="Notary queue"
        subtitle={`${DISCLOSURES.length} disclosure candidates, from ${new Set(DISCLOSURES.map((d) => d.archetype)).size} archetypes.`}
      />

      <Callout>
        Every archetype in this suite ends by naming what should be defensively published. That is
        the difference between a search product and this one: a search tells you what is known,
        and this tells you what is unclaimed and running out of time. None of these is published
        by clicking anything here — a disclosure with a provable date is irreversible, and the
        step between a queue and a filing is a person's.
      </Callout>

      <div className="flex flex-wrap items-center gap-2 mt-4 mb-3">
        <button
          className={cx('btn', reason === 'all' && 'chip-active')}
          onClick={() => setReason('all')}
        >
          all · {DISCLOSURES.length}
        </button>
        {reasons.map((r) => (
          <button key={r} className={cx('btn', reason === r && 'chip-active')} onClick={() => setReason(r)}>
            {r.replace(/-/g, ' ')} · {DISCLOSURES.filter((d) => d.reason === r).length}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <EmptyState title="Nothing in the queue" body="No archetype named anything to publish." />
      ) : (
        <div className="grid lg:grid-cols-2 gap-3">
          {rows.map((d) => (
            <div key={d.id} id={d.id}>
              <DisclosureCard dc={d} showArchetype={false} />
              <div className="text-caption text-ink-soft mt-1">
                produced by{' '}
                {producer.has(d.id) ? (
                  <a href={href(deliverableRoute(producer.get(d.id)!))} className="font-num hover:text-accent">
                    {producer.get(d.id)}
                  </a>
                ) : (
                  <span className="text-signal-error font-num">
                    nothing — {d.id} is in the queue with no deliverable behind it
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {orphans.length > 0 && (
        <Card className="mt-4 border-signal-error">
          <SectionTitle>Unattributed · {orphans.length}</SectionTitle>
          <div className="text-caption text-ink-soft">
            A disclosure candidate with no deliverable behind it cannot be checked, because there
            is nothing to check it against. These are defects, shown rather than hidden.
          </div>
        </Card>
      )}

      <DemoFooter />
    </div>
  );
}
