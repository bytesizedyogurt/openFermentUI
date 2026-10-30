// Ingest (OF-DES-001 §8.5; ADR-002). A document enters the open project's
// literature on the left (CollectCard): a paper, a report or a strain entry by
// its identifier, a file, or pasted text, split into passages and embedded on
// this machine by Sci RAG Kit. The board on the right lists every document the
// project holds, as the overlay brings it, with its extraction: one
// structured model response over the document's passages, every candidate
// anchored to a verbatim quote (extract.py). Extraction spends on the model
// and runs when a person presses Extract; nothing on this screen is timed or
// simulated, and with the service down the board says so and offers nothing.
import { useMemo } from 'react';
import { CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import type { Candidate } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { START_COMMAND } from '@/lib/postdoc';
import { fetchSourceName } from '@/lib/intake';
import { OwnerTabs } from '@/components/OwnerTabs';
import { CollectCard } from '@/components/CollectCard';
import { INTAKE_TABS } from '@/data/tabs';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader, SectionTitle } from '@/components/ui';

const NO_CANDIDATES: Candidate[] = [];

export default function IntakeIngest() {
  const papers = useStore((s) => s.papers);
  const candidates = useStore((s) => s.overlay?.candidates ?? NO_CANDIDATES);
  const jobs = useStore((s) => s.jobs);
  const extractPaperLive = useStore((s) => s.extractPaperLive);
  const serviceUp = useStore((s) => s.serviceUp);

  const held = useMemo(() => papers.filter((p) => p.held), [papers]);
  const extracted = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of candidates) counts.set(c.paperId, (counts.get(c.paperId) ?? 0) + 1);
    return counts;
  }, [candidates]);
  const running = (paperId: string) =>
    jobs.some((j) => j.status === 'running' && j.title === `Extract ${paperId}`);

  return (
    <>
      <PageHeader
        eyebrow="Intake"
        title="Ingest papers"
        subtitle={
          <>
            A document enters the open project here: a paper from Europe PMC, a report from OSTI, a
            strain entry from the Saccharomyces Genome Database, a file or pasted text. It is split
            into passages, embedded on this machine and kept with the licence it states, so a
            record&rsquo;s quote can anchor to the document&rsquo;s own words.
          </>
        }
        actions={<LinkButton to="/biorepo">Back to BioRepo</LinkButton>}
      />
      <OwnerTabs tabs={INTAKE_TABS} />

      {serviceUp === false && (
        <div className="mb-4">
          <Callout kind="warn" title="Offline — nothing can be collected or extracted">
            The Intake service is not running. Start it with{' '}
            <span className="font-num">{START_COMMAND}</span> from <span className="font-num">core/</span>{' '}
            and reload.
          </Callout>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-5 items-start">
        <div className="space-y-4">
          <CollectCard />
        </div>

        <Card className="p-3">
          <SectionTitle
            right={<span className="text-caption text-ink-soft font-num">{held.length} held</span>}
          >
            The project&rsquo;s documents
          </SectionTitle>
          <p className="text-caption text-ink-soft mb-3">
            Extract asks the model once for every measurement a document reports. A candidate whose
            quote is not verbatim in the passage it cites is refused and counted; the rest wait for a
            reviewer in BioRepo, and Witness scores them against the values reviewers type.
          </p>
          {held.length === 0 ? (
            <EmptyState
              title="Nothing collected yet"
              body="Add a document on the left; it appears here once the project holds it."
            />
          ) : (
            <ul className="divide-y divide-line" aria-label="Documents the project holds">
              {held.map((p) => {
                const n = extracted.get(p.id) ?? 0;
                const busy = running(p.id);
                return (
                  <li key={p.id} className="py-2 flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <a href={href(`/biorepo/paper/${p.id}`)} className="text-body leading-snug">
                        {p.title}
                      </a>
                      <div className="text-caption text-ink-soft">
                        {fetchSourceName(p.fetchedFrom)}
                        {p.year ? ` · ${p.year}` : ''} · <span className="font-num">{p.sections.length}</span>{' '}
                        passages
                        {p.licenceClass ? ` · ${p.licenceClass.replace('_', ' ')}` : ''}
                      </div>
                    </div>
                    <div className="shrink-0 flex items-center gap-2 text-caption">
                      {n > 0 ? (
                        <span className="inline-flex items-center gap-1 text-ink-soft">
                          <CheckCircle2 size={13} aria-hidden /> <span className="font-num">{n}</span> candidate
                          {n === 1 ? '' : 's'}
                        </span>
                      ) : (
                        <span className="text-ink-soft">not extracted</span>
                      )}
                      <Button
                        size="sm"
                        disabled={busy || serviceUp === false}
                        onClick={() => void extractPaperLive(p.id)}
                      >
                        {busy ? (
                          <Loader2 size={12} className="animate-spin" aria-hidden />
                        ) : (
                          <Sparkles size={12} aria-hidden />
                        )}
                        {busy ? 'Extracting…' : 'Extract'}
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
