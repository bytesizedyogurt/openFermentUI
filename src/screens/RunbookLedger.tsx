// Runbooks → Ledger (OF-BLD-014 §9.3). Every locked prediction across
// runbooks, grouped by runbook, drawn against what the runs reconciled
// against it measured. The counts come from `ledgerCounts` (engine/ledger.ts),
// which Home's Predictions card reads too. A hit rate is shown only once
// HIT_RATE_MIN_TESTED predictions have been tested; below that the screen
// says there are too few, because a rate over two tests is a coin toss.
import { useMemo, useState } from 'react';
import { useStore } from '@/store';
import { href } from '@/router';
import { Card, PageHeader, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { RUNBOOK_TABS } from '@/data/tabs';
import { IntervalLedger } from '@/components/figures';
import { HIT_RATE_MIN_TESTED, ledgerCounts, ledgerRows, type LedgerCounts } from '@/engine/ledger';

export function LedgerCountsLine({ c }: { c: LedgerCounts }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-body" data-testid="ledger-counts">
      <span><span className="font-num">{c.locked}</span> predictions locked</span>
      <span><span className="font-num">{c.tested}</span> tested</span>
      <span><span className="font-num">{c.held}</span> held</span>
      <span><span className="font-num">{c.missed}</span> missed</span>
      <span><span className="font-num">{c.inconclusiveRuns}</span> runs recorded as inconclusive</span>
      <span data-testid="hit-rate">
        {c.hitRate === null
          ? `Hit rate: too few tested to state (shown from ${HIT_RATE_MIN_TESTED})`
          : `Hit rate ${Math.round(c.hitRate * 100)} % of ${c.tested} tested`}
      </span>
    </div>
  );
}

type Filter = 'all' | 'tested' | 'untested';

export default function RunbookLedger() {
  const runbooks = useStore((s) => s.runbooks);
  const depositions = useStore((s) => s.depositions);
  const [filter, setFilter] = useState<Filter>('all');
  const rows = useMemo(() => ledgerRows(runbooks, depositions), [runbooks, depositions]);
  const counts = useMemo(() => ledgerCounts(runbooks, depositions), [runbooks, depositions]);
  const shown = rows.filter((r) => filter === 'all' || (filter === 'tested') === (r.held !== null));
  const groups = [...new Set(shown.map((r) => r.runbookId))];

  return (
    <div data-testid="runbook-ledger">
      <PageHeader
        eyebrow="Runbooks"
        title="Prediction ledger"
        subtitle="Every locked prediction, and what the runs reconciled against it measured. A run recorded inconclusive tests nothing and is counted as a run."
      />
      <OwnerTabs tabs={RUNBOOK_TABS} />
      <Card className="p-4 mb-4">
        <LedgerCountsLine c={counts} />
        <div className="flex gap-2 mt-3" role="group" aria-label="Show">
          {(['all', 'tested', 'untested'] as Filter[]).map((f) => (
            <button key={f} className={cx('chip', filter === f && 'chip-active')} aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f === 'tested' ? 'Tested' : 'Untested'}
            </button>
          ))}
        </div>
      </Card>
      <div className="space-y-4">
        {groups.map((id) => {
          const mine = shown.filter((r) => r.runbookId === id);
          return (
            <section key={id} aria-label={mine[0].runbookTitle}>
              <a className="font-serif text-section-title font-semibold hover:text-accent" href={href(`/runbooks/${id}`)}>
                {mine[0].runbookTitle}
              </a>
              <IntervalLedger
                title={`What did ${mine[0].runbookTitle} predict, and what was measured?`}
                rows={mine.map((r) => ({
                  key: `${r.runbookId}:${r.prediction.id}`,
                  label: r.prediction.label,
                  prediction: r.prediction,
                  lockedAt: r.lockedAt,
                  observed: r.observed,
                  held: r.held,
                }))}
                csvName={`ledger-${id}`}
              />
            </section>
          );
        })}
        {groups.length === 0 && <p className="text-body text-ink-soft">No locked prediction matches this filter.</p>}
      </div>
    </div>
  );
}
