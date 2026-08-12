// openLab (OF-FE-003 §8.7) — the deposit feed.
//
// The whole argument of this part is that a failed run is worth as much as a
// successful one, so the interface must not quietly disagree with the
// architecture. Failures render in the same card, at the same size, in the same
// order — not greyed, not sorted down, not behind a filter.
//
// Seeded empty on purpose. §9 asks for 8-12 deposits with at least three
// failures and warns that placeholder text kills this surface; the honest
// reading is that fabricated bench prose stamped `evidenceClass: 'experiment'`
// would be worse than placeholder text, because it would launder invented data
// as measurement in the one class reserved for things somebody actually did.
// A deposit here comes from a protocol run executed in this session.
import { useMemo, useState } from 'react';
import { Users, CheckCircle2, XCircle, CircleSlash } from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { Card, PageHeader, SectionTitle, Callout, Button, LinkButton, cx } from '@/components/ui';
import type { RunOutcome, RunState } from '@/data/types';

const OUTCOME_META = {
  success: { label: 'Success', Icon: CheckCircle2, tone: 'text-accent' },
  failure: { label: 'Failure', Icon: XCircle, tone: 'text-signal-warn' },
  abandoned: { label: 'Abandoned', Icon: CircleSlash, tone: 'text-ink-soft' },
} as const;

export function OpenLab() {
  const runs = useStore((s) => s.runs);
  const deposits = useStore((s) => s.deposits);
  const protocols = useStore((s) => s.protocols);
  const depositRun = useStore((s) => s.depositRun);

  const depositedIds = useMemo(() => new Set(deposits.map((d) => d.runId)), [deposits]);
  const finished = useMemo(
    () =>
      Object.values(runs)
        .filter((r): r is RunState => Boolean(r.finishedAt) && !depositedIds.has(r.id))
        .sort((a, b) => (b.finishedAt ?? 0) - (a.finishedAt ?? 0)),
    [runs, depositedIds],
  );

  const failures = deposits.filter((d) => d.outcome === 'failure').length;
  const rate = deposits.length ? Math.round((failures / deposits.length) * 100) : null;

  return (
    <div className="p-6 max-w-[1000px]">
      <PageHeader
        eyebrow="Return · openLab"
        title="Deposits"
        subtitle="Runs from this session, successes and failures at equal weight."
        actions={<LinkButton to="/runbook">Open the Runbook</LinkButton>}
      />

      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1 mb-4 text-body">
        <span>
          <span className="font-num text-ink">{deposits.length}</span>{' '}
          <span className="text-ink-soft">deposited</span>
        </span>
        <span>
          <span className="font-num text-ink">{failures}</span>{' '}
          <span className="text-ink-soft">failures</span>
        </span>
        {rate !== null && (
          <span
            className="text-ink-soft"
            title="Presented neutrally. A network reporting zero failures is hiding them."
          >
            failure rate <span className="font-num text-ink">{rate}%</span>
          </span>
        )}
      </div>

      {deposits.length === 0 && (
        <div className="max-w-3xl mb-5">
          <Callout kind="info" title="No deposits yet, and none were seeded">
            <p className="mb-2">
              This feed fills from protocol runs executed in Run Mode. Nothing is pre-loaded,
              because a fabricated bench deposit stamped as an experiment would launder invented
              data as measurement — in the one evidence class reserved for things somebody
              actually did.
            </p>
            <p>
              Start a run from the{' '}
              <a href={href('/runbook')} className="text-accent hover:underline">
                Runbook
              </a>
              , finish it, and it appears here for deposit — with failure as a first-class choice
              at equal visual weight.
            </p>
          </Callout>
        </div>
      )}

      {finished.length > 0 && (
        <section className="mb-6">
          <SectionTitle>Ready to deposit</SectionTitle>
          <div className="space-y-2">
            {finished.map((r) => (
              <DepositCard
                key={r.id}
                run={r}
                protocolTitle={protocols.find((p) => p.id === r.protocolId)?.title ?? r.protocolId}
                onDeposit={depositRun}
              />
            ))}
          </div>
        </section>
      )}

      {deposits.length > 0 && (
        <section>
          <SectionTitle>Feed</SectionTitle>
          <div className="space-y-2">
            {deposits.map((d) => {
              const meta = OUTCOME_META[d.outcome];
              const Icon = meta.Icon;
              return (
                // Same card, same size, same order for every outcome. Greying a
                // failure or sorting it down would make the interface argue
                // against the part it belongs to.
                <Card key={d.runId} className="p-3">
                  <div className="flex items-start gap-2">
                    <Icon size={15} className={cx('mt-0.5 shrink-0', meta.tone)} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-3 flex-wrap">
                        <span className="text-body">
                          <span className={meta.tone}>{meta.label}</span>{' '}
                          <span className="font-mono text-caption text-ink-soft">{d.runId}</span>
                        </span>
                        <span className="text-caption text-ink-soft">
                          {d.operator} · {d.depositedAt}
                        </span>
                      </div>
                      {d.failureReason && (
                        <div className="text-body mt-1 border-l-2 border-signal-warn pl-2">
                          {d.failureReason}
                        </div>
                      )}
                      {Object.keys(d.results).length > 0 && (
                        <div className="text-caption text-ink-soft mt-1.5">
                          {Object.entries(d.results).map(([k, v]) => (
                            <span key={k} className="mr-3">
                              {k} <span className="font-num text-ink">{String(v)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                      {d.producedRecordIds.length === 0 && (
                        <div className="text-caption text-ink-soft mt-1.5">
                          No records produced — a run can be worth depositing without yielding a
                          number.
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

function DepositCard({
  run,
  protocolTitle,
  onDeposit,
}: {
  run: RunState;
  protocolTitle: string;
  onDeposit: (o: RunOutcome) => void;
}) {
  const [outcome, setOutcome] = useState<RunOutcome['outcome']>('success');
  const [reason, setReason] = useState('');

  return (
    <Card className="p-3">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="text-body">{protocolTitle}</span>
        <span className="font-mono text-caption text-ink-soft">{run.id}</span>
      </div>
      <div className="text-caption text-ink-soft mt-0.5">
        {Object.keys(run.completed).length} steps completed ·{' '}
        {run.deviations.length} deviation{run.deviations.length === 1 ? '' : 's'} · scale{' '}
        <span className="font-num">{run.scale}×</span>
      </div>

      {/* Failure is offered at the same visual weight as success. A radio row
          where one option is quieter than the other is a thumb on the scale. */}
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        {(['success', 'failure', 'abandoned'] as const).map((o) => {
          const meta = OUTCOME_META[o];
          return (
            <button
              key={o}
              onClick={() => setOutcome(o)}
              aria-pressed={outcome === o}
              className={cx(
                'text-caption border rounded-btn px-2.5 py-1 transition-colors',
                outcome === o
                  ? 'border-accent bg-accent-wash text-accent font-medium'
                  : 'border-line text-ink-soft hover:text-ink',
              )}
            >
              {meta.label}
            </button>
          );
        })}
      </div>

      {outcome === 'failure' && (
        <textarea
          className="input w-full text-body mt-2"
          rows={2}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="What went wrong, in the words you would use in a lab book."
        />
      )}

      <div className="mt-2">
        <Button
          disabled={outcome === 'failure' && reason.trim().length === 0}
          onClick={() =>
            onDeposit({
              runId: run.id,
              outcome,
              failureReason: outcome === 'failure' ? reason.trim() : undefined,
              results: {},
              operator: 'you',
              producedRecordIds: [],
            })
          }
        >
          Deposit
        </Button>
      </div>
    </Card>
  );
}
