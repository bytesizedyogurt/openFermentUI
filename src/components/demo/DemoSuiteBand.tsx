// The demo suite's state, on the Bench.
//
// This is what is left of `screens/demo/Bench.tsx`. That screen was a second
// home: a composer that handed every question to Postdoc, six archetype
// prompts, and three context bands. The composer and the prompts are on the
// Postdoc screen now — the place that actually answers them — so a second
// home, a second rail entry and a second `g` key were paying for three cards.
//
// It is a COMPONENT rather than a section of `Home.tsx` for the same reason
// the demo patent families are their own screen: `Home` reads the casein
// corpus through the adapter seam, and the demo pool reads its modules
// directly. Home composes this; it does not import an Accession.
//
// The band leads with the contradiction. The first thing a reviewer should see
// about this system is it declining to resolve something, and putting that
// last would make it a footnote to a feature list.
import { useMemo } from 'react';

import { DELIVERABLES, DISCLOSURES } from '@/data/demo/archetypes';
import { ARCHETYPE_PROMPTS } from '@/data/demo/flows';
import { ACCESSIONS } from '@/data/demo/accessions';
import { FIELD_BY_ID } from '@/data/demo/core';
import { accessionsOnField, conflictPairs, deliverableRoute } from '@/lib/demo';
import { href } from '@/router';
import { Card, SectionTitle } from '@/components/ui';
import { DemoContradictionRail } from './DemoContradictionRail';

/** The question each archetype answers, in the reader's words rather than ours. */
const QUESTION: Record<string, string> = {
  AR1: 'Which factor combinations are already excluded, and what has nobody tried?',
  AR2: 'Which route to this molecule, and is it available to use?',
  AR3: 'What can this plant actually make, and what stops it?',
  AR4: 'What would a greenfield facility on this feedstock look like?',
  AR5: 'This is not answerable as asked — what is it really six of?',
  AR6: 'Did this run deviate, and may its numbers be pooled with the others?',
};

export function DemoSuiteBand() {
  const contradiction = useMemo(() => {
    const fields = [...new Set(ACCESSIONS.map((a) => a.field))];
    for (const f of fields) {
      if (conflictPairs(accessionsOnField(f as never)).length) return f;
    }
    return null;
  }, []);

  const byArchetype = useMemo(() => new Map(DELIVERABLES.map((d) => [d.archetype, d])), []);
  const urgentNow = DISCLOSURES.filter((d) => d.urgency === 'now').length;

  return (
    <section className="mt-8" aria-labelledby="home-demo-suite">
      <SectionTitle>
        <span id="home-demo-suite">Demo suite</span>
      </SectionTitle>
      <div className="text-body text-ink-soft mb-3 max-w-prose">
        A second pool, held apart from the β-casein corpus on purpose. It holds{' '}
        <span className="font-num">{ACCESSIONS.length}</span> Accessions — a normalised quantity
        each, with complete provenance under a permanent identifier — where the corpus holds
        catalogued claims awaiting verification. They are not the same object and nothing averages
        across them.{' '}
        <a href={href('/postdoc')} className="text-accent hover:underline">
          Ask the Postdoc
        </a>{' '}
        to watch one of the six questions below decompose into work across the parts.
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Card>
          <div className="text-caption text-ink-soft">Unresolved</div>
          {contradiction ? (
            <>
              <div className="text-caption text-ink-soft mb-2 mt-1">
                {FIELD_BY_ID[contradiction]?.name ?? contradiction} — two records disagree and this
                system is not resolving them.
              </div>
              <DemoContradictionRail
                field={contradiction as never}
                accessions={accessionsOnField(contradiction as never)}
                height={72}
              />
            </>
          ) : (
            <div className="text-caption text-ink-soft mt-1">
              Nothing in this pool disagrees with itself, which would be more surprising than it
              sounds.
            </div>
          )}
        </Card>

        <Card>
          <div className="text-caption text-ink-soft">Notary queue</div>
          <div className="mt-1">
            <span className="font-num text-page-title">{DISCLOSURES.length}</span>
            <span className="text-caption text-ink-soft ml-2">candidates</span>
          </div>
          {urgentNow > 0 && (
            <div className="text-caption mt-1 text-signal-closed">
              {urgentNow} marked <span className="font-medium">now</span>
            </div>
          )}
          <div className="text-caption text-ink-soft mt-1">
            Every archetype ends by naming what should be defensively published. That is the
            difference between a search product and this one.
          </div>
          <a
            href={href('/notary/disclosures')}
            className="text-caption text-accent hover:underline mt-2 inline-block"
          >
            open the queue →
          </a>
        </Card>

        <Card>
          <div className="text-caption text-ink-soft">Object pool</div>
          <div className="mt-1">
            <span className="font-num text-page-title">{ACCESSIONS.length}</span>
            <span className="text-caption text-ink-soft ml-2">Accessions</span>
          </div>
          <div className="text-caption text-ink-soft mt-1">
            One quantity each, normalised, with the source it was read out of and the context it
            was measured in.
          </div>
          <a href={href('/repo')} className="text-caption text-accent hover:underline mt-2 inline-block">
            open BioRepo →
          </a>
        </Card>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        {ARCHETYPE_PROMPTS.map((p) => {
          const dlv = byArchetype.get(p.id as never);
          return (
            <Card key={p.id} className="p-3">
              <div className="flex items-baseline gap-2">
                <span className="font-num text-caption text-ink-soft">{p.id}</span>
                <span className="text-caption text-ink-soft">{p.label}</span>
              </div>
              <div className="text-body mt-0.5">{QUESTION[p.id] ?? p.label}</div>
              <div className="text-caption text-ink-soft mt-1">
                <a
                  href={href(`/postdoc?q=${encodeURIComponent(p.prompt)}`)}
                  className="text-accent hover:underline"
                >
                  ask it
                </a>
                {dlv && (
                  <>
                    {' · '}
                    <a href={href(deliverableRoute(dlv.id))} className="text-accent hover:underline">
                      skip to the deliverable
                    </a>{' '}
                    · <span className="font-num">{dlv.accessionIds.length} Accessions</span> ·{' '}
                    <span
                      className={
                        dlv.disclosureCandidateIds.length ? 'font-num' : 'font-num text-signal-error'
                      }
                    >
                      {dlv.disclosureCandidateIds.length} to publish
                    </span>
                  </>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
