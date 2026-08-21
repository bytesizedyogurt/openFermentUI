// The demo home — Postdoc first.
//
// The earlier version of this screen was a grid of six deliverable cards, which
// is a menu of ANSWERS. That gets the demo backwards: the thing being shown is
// not six artifacts, it is a system you can ask a question and that decomposes
// it into work across the parts. So the agent composer is the first thing on
// the page and the six archetypes are PROMPTS you can run, not links you can
// follow.
//
// The deliverables are still reachable — one line under each prompt — because a
// reviewer who has already seen a flow play should not have to sit through it
// again to reach the artifact.
//
// Everything below the fold is context: the queue depth, the recent Ledger, and
// one contradiction. The contradiction is there deliberately: the first thing a
// reviewer should see about this system is it declining to resolve something.
import { useMemo, useState } from 'react';
import { CornerDownLeft } from 'lucide-react';

import { DELIVERABLES, DISCLOSURES } from '@/data/demo/archetypes';
import { ARCHETYPE_PROMPTS } from '@/data/demo/flows';
import { ACCESSIONS } from '@/data/demo/accessions';
import { FIELD_BY_ID } from '@/data/demo/core';
import { UPSTREAM_BY_PART, ARCHETYPE_PART } from '@/data/demo/upstream';
import { accessionsOnField, conflictPairs } from '@/lib/demo';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, cx } from '@/components/ui';
import { DemoContradictionRail } from '@/components/demo/DemoContradictionRail';
import { deliverableRoute } from './Repo';
import { DemoFooter } from '@/components/demo/DemoFooter';

/** The question each archetype answers, in the reader's words rather than ours. */
const QUESTION: Record<string, string> = {
  AR1: 'Which factor combinations are already excluded, and what has nobody tried?',
  AR2: 'Which route to this molecule, and is it available to use?',
  AR3: 'What can this plant actually make, and what stops it?',
  AR4: 'What would a greenfield facility on this feedstock look like?',
  AR5: 'This is not answerable as asked — what is it really six of?',
  AR6: 'Did this run deviate, and may its numbers be pooled with the others?',
};

export function Bench() {
  const [draft, setDraft] = useState('');

  const contradiction = useMemo(() => {
    const fields = [...new Set(ACCESSIONS.map((a) => a.field))];
    for (const f of fields) {
      if (conflictPairs(accessionsOnField(f as never)).length) return f;
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

  const byArchetype = useMemo(
    () => new Map(DELIVERABLES.map((d) => [d.archetype, d])),
    [],
  );
  const urgentNow = DISCLOSURES.filter((d) => d.urgency === 'now').length;

  /** Hand the prompt to Postdoc. The agent screen runs whatever arrives in `q`. */
  const ask = (text: string) => {
    const q = text.trim();
    if (q) navigate(`/postdoc?q=${encodeURIComponent(q)}`);
  };

  return (
    <div className="p-6 max-w-[1200px]">
      <PageHeader
        title="Ask the Postdoc"
        subtitle="One question, decomposed into work across the parts. Every number it answers with traces to an Accession or to a computation over Accessions — none of them come from model weights."
      />

      {/* The composer. First thing on the page, because asking is the demo. */}
      <Card className="p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(draft);
          }}
        >
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="Ask about a process space, a route, a plant, a run…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label="Ask the Postdoc"
            />
            <button type="submit" className="btn inline-flex items-center gap-1.5" disabled={!draft.trim()}>
              Ask
              <CornerDownLeft className="w-3.5 h-3.5" aria-hidden />
            </button>
          </div>
        </form>
        <div className="text-caption text-ink-soft mt-2 max-w-prose">
          Six questions below are scripted end to end and will play in full. Anything else gets an
          honest decline rather than an improvised answer — which is the behaviour worth
          demonstrating, so it is worth trying.
        </div>
      </Card>

      {/* The six, as prompts. */}
      <div className="mt-5">
        <SectionTitle>Six questions this system is built to take</SectionTitle>
        <div className="text-caption text-ink-soft mb-3 max-w-prose">
          They compose: one archetype's output is another's input. Archetype 6 produces the
          excursion that Archetype 1 excludes; Archetype 1 produces the setpoint that rescues a
          candidate in Archetype 3; Archetype 5 terminates by spawning Archetype 2.
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          {ARCHETYPE_PROMPTS.map((p) => {
            const dlv = byArchetype.get(p.id as never);
            const part = ARCHETYPE_PART[p.id as never];
            const upstream = part ? UPSTREAM_BY_PART[part] : undefined;
            return (
              <Card key={p.id} className="flex flex-col">
                <div className="flex items-baseline gap-2">
                  <span className="font-num text-caption text-ink-soft">{p.id}</span>
                  <span className="text-caption text-ink-soft">{p.label}</span>
                  {upstream && (
                    <span className="text-caption text-ink-soft ml-auto" title={`${upstream.label} — ${upstream.deps.map((d) => d.name).join(', ') || 'no upstream decided'}`}>
                      {upstream.label}
                    </span>
                  )}
                </div>

                <div className="mt-1 flex-1">{QUESTION[p.id] ?? p.label}</div>

                <button
                  className="mt-3 text-left w-full border border-line px-2 py-1.5 hover:border-accent hover:bg-[rgb(var(--accent-wash))]/40 transition-colors"
                  onClick={() => ask(p.prompt)}
                >
                  <span className="text-caption text-ink-soft">ask </span>
                  <span className="font-num text-caption">“{p.prompt}”</span>
                </button>

                {dlv && (
                  <div className="text-caption text-ink-soft mt-2">
                    or{' '}
                    <a href={href(deliverableRoute(dlv.id))} className="text-accent hover:underline">
                      skip to the deliverable
                    </a>{' '}
                    ·{' '}
                    <span className="font-num">{dlv.accessionIds.length} Accessions</span> ·{' '}
                    <span
                      className="font-num"
                      style={{ color: dlv.disclosureCandidateIds.length ? undefined : 'rgb(var(--signal-error))' }}
                    >
                      {dlv.disclosureCandidateIds.length} to publish
                    </span>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </div>

      {/* Context. */}
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
          <div className="text-caption text-ink-soft mt-1 max-w-prose">
            Every archetype ends by naming what should be defensively published. That is the
            difference between a search product and this one.
          </div>
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
