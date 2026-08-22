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
import { fieldName } from '@/data/ontology';
import { Card, PageHeader, SectionTitle, Callout, Button, LinkButton, cx } from '@/components/ui';
import type { FieldId, ResultField, RunOutcome, RunState } from '@/data/types';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('openlab', 'corpus');
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
  const mintExperimentRecords = useStore((s) => s.mintExperimentRecords);

  const depositedIds = useMemo(() => new Set(deposits.map((d) => d.runId)), [deposits]);
  const finished = useMemo(
    () =>
      Object.values(runs)
        .filter((r): r is RunState => Boolean(r.finishedAt) && !depositedIds.has(r.id))
        .sort((a, b) => (b.finishedAt ?? 0) - (a.finishedAt ?? 0)),
    [runs, depositedIds],
  );

  // The result form comes from the protocol version the run was started at, so
  // a deposit collects exactly what that protocol exists to measure.
  const schemaFor = (r: RunState): ResultField[] => {
    const proto = protocols.find((p) => p.id === r.protocolId);
    const v = proto?.versions.find((x) => x.version === r.version) ?? proto?.versions[0];
    return v?.resultSchema ?? [];
  };

  // Protocols that declare a decisive measurement — what to run first when the
  // feed is empty.
  const decisive = useMemo(
    () =>
      protocols.flatMap((p) =>
        p.versions
          .filter((v) => v.version === p.currentVersion && v.decisive)
          .map((v) => ({
            protocol: p,
            field: v.decisive!.field,
            uncertainty: v.decisive!.currentUncertainty,
          })),
      ),
    [protocols],
  );

  const failures = deposits.filter((d) => d.outcome === 'failure').length;
  const rate = deposits.length ? Math.round((failures / deposits.length) * 100) : null;

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
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

          {decisive.length > 0 && (
            <section className="mt-4">
              <SectionTitle>Where a run would count most</SectionTitle>
              <p className="text-caption text-ink-soft mb-2">
                Protocols that declare which uncertainty they exist to resolve. An empty feed is
                a starting point, not a dead end.
              </p>
              <div className="space-y-1.5">
                {decisive.map(({ protocol, field, uncertainty }) => (
                  <Card key={protocol.id} className="px-3 py-2">
                    <div className="flex items-baseline justify-between gap-3 flex-wrap">
                      <a
                        href={href(`/runbook/${protocol.id}`)}
                        className="text-body text-accent hover:underline"
                      >
                        {protocol.title}
                      </a>
                      <a
                        href={href(`/ledger/p/${field}`)}
                        className="text-caption text-ink-soft hover:text-accent whitespace-nowrap"
                      >
                        settles {fieldName(field)} →
                      </a>
                    </div>
                    <p className="text-caption text-ink-soft mt-1 line-clamp-2">{uncertainty}</p>
                  </Card>
                ))}
              </div>
            </section>
          )}
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
                schema={schemaFor(r)}
                onDeposit={(outcome, measured) => {
                  // The form promises "becomes a record" beside every field
                  // bound to an ontology field. Mint them first, so the deposit
                  // carries real ids and the promise is kept.
                  const produced =
                    outcome.outcome === 'success'
                      ? mintExperimentRecords(r.id, r.protocolId, measured)
                      : [];
                  depositRun({ ...outcome, producedRecordIds: produced });
                }}
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
    </>
  );
}

function DepositCard({
  run,
  protocolTitle,
  schema,
  onDeposit,
}: {
  run: RunState;
  protocolTitle: string;
  schema: ResultField[];
  onDeposit: (
    o: RunOutcome,
    measured: { field: FieldId; value: number; unit: string }[],
  ) => void;
}) {
  const [outcome, setOutcome] = useState<RunOutcome['outcome']>('success');
  const [reason, setReason] = useState('');
  const [results, setResults] = useState<Record<string, string>>({});

  // A failed run has no results to report — that is what failure means here, and
  // demanding them would push an operator toward calling a failure a success.
  const needed = outcome === 'success' ? schema.filter((f) => f.required) : [];
  const missing = needed.filter((f) => !String(results[f.id] ?? '').trim());

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
      {/* One choice, not three switches — exposed as a radiogroup so it is
          announced and arrow-navigable as the single decision it is. */}
      <div
        className="flex flex-wrap gap-1.5 mt-2.5"
        role="radiogroup"
        aria-label="Run outcome"
      >
        {(['success', 'failure', 'abandoned'] as const).map((o) => {
          const meta = OUTCOME_META[o];
          return (
            <button
              key={o}
              onClick={() => setOutcome(o)}
              role="radio"
              aria-checked={outcome === o}
              className={cx(
                'text-caption border rounded-btn px-2.5 py-1 motion-colors',
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

      {outcome === 'success' && schema.length > 0 && (
        <div className="mt-2.5 space-y-1.5">
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            Results — generated from this protocol's schema
          </div>
          {schema.map((f) => (
            <label key={f.id} className="flex items-center gap-2 text-caption">
              <span className="w-[240px] shrink-0">
                {f.label}
                {f.unit && <span className="text-ink-soft"> ({f.unit})</span>}
                {f.required && <span className="text-signal-warn"> *</span>}
                {f.field && (
                  <span className="text-ink-soft"> · becomes a record</span>
                )}
              </span>
              {f.type === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={results[f.id] === 'true'}
                  onChange={(e) => setResults((r) => ({ ...r, [f.id]: String(e.target.checked) }))}
                />
              ) : (
                <input
                  className="input flex-1"
                  inputMode={f.type === 'number' ? 'decimal' : undefined}
                  value={results[f.id] ?? ''}
                  onChange={(e) => setResults((r) => ({ ...r, [f.id]: e.target.value }))}
                />
              )}
            </label>
          ))}
        </div>
      )}

      <div className="mt-2.5 flex items-center gap-3 flex-wrap">
        <Button
          disabled={
            (outcome === 'failure' && reason.trim().length === 0) || missing.length > 0
          }
          onClick={() => {
            const typed: Record<string, number | string | boolean> = {};
            const measured: { field: FieldId; value: number; unit: string }[] = [];
            if (outcome === 'success') {
              for (const f of schema) {
                const raw = results[f.id];
                if (raw === undefined || raw === '') continue;
                typed[f.label] =
                  f.type === 'number' ? Number(raw) : f.type === 'boolean' ? raw === 'true' : raw;
                // Only a numeric field bound to the ontology can become a record.
                if (f.field && f.type === 'number' && Number.isFinite(Number(raw))) {
                  measured.push({ field: f.field, value: Number(raw), unit: f.unit ?? '' });
                }
              }
            }
            onDeposit(
              {
                runId: run.id,
                outcome,
                failureReason: outcome === 'failure' ? reason.trim() : undefined,
                results: typed,
                operator: 'you',
                producedRecordIds: [],
              },
              measured,
            );
          }}
        >
          Deposit
        </Button>
        {missing.length > 0 && (
          <span className="text-caption text-ink-soft">
            {missing.map((f) => f.label.toLowerCase()).join(', ')} required
          </span>
        )}
      </div>
    </Card>
  );
}
