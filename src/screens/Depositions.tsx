// Depositions, as a Runbooks tab (OF-BLD-008 §2, §6).
//
// A Deposition stopped being a rail destination and became a view inside
// Runbooks, which is where it belongs: a deposition is the inbound account of
// what happened when a runbook's claim was tested, and it is launched from the
// runbook that predicted it.
//
// THIS LIST IS USUALLY EMPTY, AND SAYS SO HONESTLY. Depositions live in the
// Durable tier — they are written at the bench and survive a reload, but a
// fresh session has none. An empty list here means nobody has run anything in
// this browser, not that the feature is missing, and the two read very
// differently if the screen does not say which.
import { ClipboardList } from 'lucide-react';
import { useStore } from '@/store';
import { href } from '@/router';
import { Card, EmptyState, LinkButton, PageHeader, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { RUNBOOK_TABS } from '@/data/tabs';
import { ComponentTag } from '@/components/ComponentTag';

const STATE_TONE: Record<string, string> = {
  staged: 'text-ink-soft',
  running: 'text-accent',
  closed: 'text-ink-soft',
};

export default function Depositions() {
  const depositions = useStore((s) => s.depositions);
  const runbooks = useStore((s) => s.runbooks);
  const protocols = useStore((s) => s.protocols);

  const runbookTitle = (id: string | null | undefined) =>
    runbooks.find((r) => r.id === id)?.title ?? null;
  const protocolTitle = (id: string | null | undefined) =>
    protocols.find((p) => p.id === id)?.title ?? null;

  return (
    <>
      <PageHeader
        eyebrow="Module 6 · Runbooks"
        title="Depositions"
        subtitle="What actually happened at the bench, against what a runbook predicted. A deposition is opened from the runbook it tests and closed by reconciling its measurements against that runbook's predictions."
      />
      <OwnerTabs tabs={RUNBOOK_TABS} />

      {depositions.length === 0 ? (
        <Card>
          <EmptyState
            icon={<ClipboardList size={22} />}
            title="No depositions in this browser"
            body="Depositions are written at the bench and kept in the durable tier, so they survive a reload — but they start empty. Open a runbook and stage a run against one of its protocols, and the record appears here."
            action={<LinkButton to="/runbooks">Open the runbook board</LinkButton>}
          />
        </Card>
      ) : (
        <Card className="px-4 py-1">
          <ul>
            {depositions.map((d) => {
              const rb = runbookTitle(d.runbookId);
              const pr = protocolTitle(d.protocolId);
              return (
                <li key={d.id} className="py-3 border-b border-line/70 last:border-0">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <a
                      href={href(`/runbooks/depositions/${d.id}`)}
                      className="font-num text-body text-ink hover:text-accent"
                    >
                      {d.id}
                    </a>
                    <span className={cx('chip text-[11px] py-0', STATE_TONE[d.state] ?? 'text-ink-soft')}>
                      {d.state}
                    </span>
                    <span className="ml-auto font-num text-caption text-ink-soft shrink-0">
                      {d.entries.length} measured · {d.observations.length} observed
                    </span>
                  </div>
                  <div className="text-body text-ink-soft mt-0.5">
                    {pr ?? d.protocolId}
                    {rb && <> · testing {rb}</>}
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      <div className="mt-5">
        <ComponentTag
          component="Deposition"
          action={`${depositions.length} in this browser`}
        />
      </div>
    </>
  );
}
