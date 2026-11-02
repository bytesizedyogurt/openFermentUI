// Runbook board (OF-BLD-005 §6) — every runbook grouped by status.
//
// The board is ordered by what needs a person, not by what is newest. Running
// work first, then the three states waiting on a decision — a halted input, a
// boundary a model should not rule on, an unauthorised spend — then the
// finished ones and the drafts. A board is read top-left first, and what is
// waiting on you belongs there.
//
// A runbook is not a job. The jobs tray shows the progress bar for whatever is
// in flight; this board shows the records, including the ones that are not
// running at all and will not be until somebody acts.
import { useMemo } from 'react';
import { GitBranch } from 'lucide-react';
import type { Runbook, RunbookStatus } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { RUNBOOK_STATUS_LABEL, RUNBOOK_STATUS_NOTE, RUNBOOK_STATUS_ORDER } from '@/data/labels';
import { PRODUCT_CATEGORY_LABEL } from '@/data/labels';
import { RunbookStatusIcon, StageDot } from '@/components/RunbookBits';
import { Bar, Card, EmptyState, Explain, LinkButton, PageHeader, SectionTitle, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { RUNBOOK_TABS } from '@/data/tabs';

function RunbookCard({ r }: { r: Runbook }) {
  const products = useStore((s) => s.products);
  const product = r.productId ? products.find((p) => p.id === r.productId) : undefined;
  const done = r.stages.filter((s) => s.status === 'done').length;
  const halted = r.stages.find((s) => s.status === 'blocked' || s.status === 'review');

  return (
    <a
      href={href(`/runbooks/${r.id}`)}
      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium leading-snug">{r.title}</span>
        <span
          className={cx(
            'chip shrink-0 text-[11px] py-0',
            r.kind === 'research' ? 'text-signal-info border-signal-info/40' : 'text-ink-soft',
          )}
          title={
            r.kind === 'research'
              ? 'Open question — outputs a prediction and the experiments that would test it'
              : 'Established product — outputs a process you could build and defend'
          }
        >
          {r.kind}
        </span>
      </div>

      {product && (
        <div className="text-caption text-ink-soft mt-1 truncate">
          {product.name} · {PRODUCT_CATEGORY_LABEL[product.category]}
        </div>
      )}

      <div className="mt-2 flex items-center gap-1" aria-hidden>
        {r.stages.map((s, i) => (
          <StageDot key={`${s.name}-${i}`} status={s.status} />
        ))}
      </div>
      <div className="mt-1.5">
        <Bar
          value={r.progressPct}
          max={100}
          className={
            r.status === 'blocked_unverified'
              ? 'bg-signal-error'
              : r.status === 'needs_review'
                ? 'bg-signal-warn'
                : undefined
          }
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-caption text-ink-soft mt-1.5">
        <span className="font-num">{r.progressPct}%</span>
        <span>
          <span className="font-num">{done}</span>/<span className="font-num">{r.stages.length}</span>{' '}
          stages
        </span>
        {r.eta && <span className="font-num">{r.eta}</span>}
        {r.estCostUsd !== null && (
          <span className="font-num" title="Modeled compute spend, not a quotation">
            ${r.estCostUsd < 1 ? r.estCostUsd.toFixed(2) : r.estCostUsd}
          </span>
        )}
      </div>

      {halted && (
        <div className="text-caption text-signal-warn mt-1.5 leading-snug">
          {halted.name}: {halted.detail ?? 'waiting on a person'}
        </div>
      )}
    </a>
  );
}

export default function Runbooks() {
  const runbooks = useStore((s) => s.runbooks);

  const columns = useMemo(() => {
    const by = new Map<RunbookStatus, Runbook[]>();
    for (const r of runbooks) {
      const arr = by.get(r.status);
      if (arr) arr.push(r);
      else by.set(r.status, [r]);
    }
    return RUNBOOK_STATUS_ORDER.filter((s) => (by.get(s)?.length ?? 0) > 0).map((status) => ({
      status,
      items: by.get(status)!,
    }));
  }, [runbooks]);

  const waiting = useMemo(
    () =>
      runbooks.filter((r) =>
        ['blocked_unverified', 'needs_review', 'awaiting_budget'].includes(r.status),
      ).length,
    [runbooks],
  );
  const spend = useMemo(
    () => runbooks.reduce((n, r) => n + (r.estCostUsd ?? 0), 0),
    [runbooks],
  );

  const subtitle =
    'A runbook is a synthesised, followable answer to a question about making something. Industrial runbooks output a process you could build and defend; research runbooks output a prediction and the experiments that would test it. Same toolchain, different question.';

  return (
    <>
      <PageHeader eyebrow="Claims to be tested" title="Runbooks" subtitle={subtitle} />
      <OwnerTabs tabs={RUNBOOK_TABS} />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-4 text-caption text-ink-soft">
        <span className="inline-flex items-center gap-1.5">
          <GitBranch size={13} aria-hidden />
          <span className="font-num text-ink">{runbooks.length}</span> runbooks
        </span>
        <span>
          <span className="font-num text-ink">
            {runbooks.filter((r) => r.kind === 'industrial').length}
          </span>{' '}
          industrial ·{' '}
          <span className="font-num text-ink">
            {runbooks.filter((r) => r.kind === 'research').length}
          </span>{' '}
          research
        </span>
        <span>
          <span className={cx('font-num', waiting > 0 ? 'text-signal-warn' : 'text-ink')}>
            {waiting}
          </span>{' '}
          waiting on a person
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="font-num text-ink">${spend.toFixed(2)}</span> modeled compute spend
          <Explain label="What the cost figure means">
            An estimate of the compute a runbook consumes — retrieval, prediction, enumeration —
            not a quotation and not a process cost. It is here because enumeration compute is the
            one input a person authorises before it is spent, which is why{' '}
            <span className="font-medium">awaiting budget</span> is a state on this board rather
            than a footnote.
          </Explain>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {columns.map(({ status, items }) => (
          <section key={status} aria-labelledby={`col-${status}`}>
            <SectionTitle
              right={<span className="font-num text-caption text-ink-soft">{items.length}</span>}
            >
              <span id={`col-${status}`} className="inline-flex items-center gap-2">
                <RunbookStatusIcon status={status} />
                {RUNBOOK_STATUS_LABEL[status]}
              </span>
            </SectionTitle>
            <p className="text-caption text-ink-soft mb-2 leading-snug">
              {RUNBOOK_STATUS_NOTE[status]}
            </p>
            <div className="space-y-3">
              {items.map((r) => (
                <RunbookCard key={r.id} r={r} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {runbooks.length === 0 && (
        <Card data-testid="runbooks-empty">
          <EmptyState
            icon={<GitBranch size={22} aria-hidden />}
            title="No runbooks in this session"
            body="A runbook starts as a draft in Postdoc: ask it to draft one from the evidence, then press Turn into a runbook, and it lands here."
            action={<LinkButton to="/postdoc">Draft a runbook in Postdoc</LinkButton>}
          />
        </Card>
      )}
    </>
  );
}
