// A Deposition, as a record (OF-BLD-006 §4).
//
// RunMode is where a deposition is written; this is where it is read. The
// distinction matters because a Deposition outlives the session that produced
// it: the run state died with the tab, and this did not.
//
// The page is organised around the one thing that makes the record worth
// keeping — measured values sit above observations, because the measurements
// are what can be reconciled and the observations are what nobody predicted.
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ClipboardList, Eye, FlaskConical, GitBranch, Ruler } from 'lucide-react';
import type { Deposition } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { ComponentTag } from '@/components/ComponentTag';
import {
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

const STATE_COPY: Record<Deposition['state'], { label: string; note: string; tone: string }> = {
  staged: {
    label: 'Staged',
    note: 'Quantities are scaled and the measurement schema is fixed. Nothing has been recorded yet.',
    tone: 'text-ink-soft',
  },
  running: {
    label: 'Running',
    note: 'Open for entries. The record is append-only: corrections add, nothing overwrites.',
    tone: 'text-signal-info',
  },
  closed: {
    label: 'Closed',
    note: 'No further entries. What is here is what happened.',
    tone: 'text-accent',
  },
};

export default function DepositionDetail({ depositionId }: { depositionId: string }) {
  const depositions = useStore((s) => s.depositions);
  const runbooks = useStore((s) => s.runbooks);
  const protocols = useStore((s) => s.protocols);
  const structure = useStore((s) => s.structureObservation);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    setReady(false);
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, [depositionId]);

  const deposition = depositions.find((d) => d.id === depositionId);
  const runbook = runbooks.find((r) => r.id === deposition?.runbookId);
  const protocol = protocols.find((p) => p.id === deposition?.protocolId);

  const measureById = useMemo(
    () => Object.fromEntries((runbook?.measurementSchema ?? []).map((m) => [m.id, m])),
    [runbook],
  );

  if (!deposition) {
    return (
      <>
        <PageHeader
          eyebrow="Assay"
          title="Deposition not found"
          subtitle="Depositions are durable, so this id was either never created in this browser or the durable store was reset."
        />
        <Card>
          <EmptyState
            icon={<ClipboardList size={22} aria-hidden />}
            title={`No deposition with the id “${depositionId}”`}
            body="A deposition is started from a runbook, which is what supplies the predictions it will be judged against."
            action={<LinkButton to="/runbooks">Open the runbook board</LinkButton>}
          />
        </Card>
      </>
    );
  }

  if (!ready) {
    return (
      <>
        <PageHeader eyebrow="Assay · Deposition" title={protocol?.title ?? deposition.id} />
        <Card>
          <Skeleton rows={8} />
        </Card>
      </>
    );
  }

  const state = STATE_COPY[deposition.state];
  const unconfirmed = deposition.entries.filter((e) => !e.confirmed).length;

  return (
    <>
      <PageHeader
        eyebrow="Assay · Deposition"
        title={protocol?.title ?? 'Bench run'}
        subtitle={state.note}
        actions={
          runbook && (
            <LinkButton to={`/runbooks/${runbook.id}`}>
              <GitBranch size={14} /> {runbook.title}
            </LinkButton>
          )
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className={cx('chip', state.tone)}>{state.label}</span>
        <span className="chip text-ink-soft font-num">{deposition.id}</span>
        <span className="chip text-ink-soft">
          started <span className="font-num">{deposition.startedAt.slice(0, 16).replace('T', ' ')}</span>
        </span>
        {deposition.closedAt && (
          <span className="chip text-ink-soft">
            closed{' '}
            <span className="font-num">{deposition.closedAt.slice(0, 16).replace('T', ' ')}</span>
          </span>
        )}
        {deposition.operatorId === null && (
          <span className="chip text-ink-soft" title="Guild will populate this once people and permissions exist">
            operator unattributed
          </span>
        )}
      </div>

      {unconfirmed > 0 && (
        <div className="mb-4">
          <Callout kind="warn" title={`${unconfirmed} value${unconfirmed === 1 ? '' : 's'} never read back`}>
            These entered the schema without the confirmation beat, so the parse was never checked
            against what the operator actually said. They stay in the record and stay labelled —
            removing them would lose data, and silently trusting them is how &ldquo;four two&rdquo;
            becomes 42.
          </Callout>
        </div>
      )}

      {/* ── measured ─────────────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-measured">
        <SectionTitle
          right={<span className="font-num text-caption text-ink-soft">{deposition.entries.length}</span>}
        >
          <span id="band-measured" className="inline-flex items-center gap-2">
            <Ruler size={15} aria-hidden /> Measured
          </span>
        </SectionTitle>
        <Card className="p-4">
          {deposition.entries.length === 0 ? (
            <EmptyState
              title="Nothing measured"
              body="No reported value matched the runbook's measurement schema. That is not necessarily a failure — it may mean the run has not reached a declared timepoint yet."
            />
          ) : (
            <ul className="space-y-3">
              {deposition.entries.map((e) => (
                <li key={e.id}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-body">
                      {measureById[e.measureId]?.label ?? e.measureId}
                    </span>
                    <span className="font-num text-body shrink-0">
                      {e.value} <span className="text-ink-soft text-caption">{e.unit}</span>
                      {!e.confirmed && (
                        <span className="text-signal-warn text-caption"> · unconfirmed</span>
                      )}
                    </span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">
                    <span className="font-num">{e.at.slice(11, 16)}</span> · reported as &ldquo;
                    {e.raw}&rdquo;
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      {/* ── observed ─────────────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-observed">
        <SectionTitle
          right={
            <span className="font-num text-caption text-ink-soft">
              {deposition.observations.length}
            </span>
          }
        >
          <span id="band-observed" className="inline-flex items-center gap-2">
            <Eye size={15} aria-hidden /> Observed
          </span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Everything the operator reported that no field was waiting for.{' '}
          <Explain label="Why these are not a failure of the schema">
            An unexpected result has no column by definition — if a schema had anticipated it, it
            would not be unexpected. A capture that only accepted declared fields would discard
            exactly the observation worth having, so these are kept word for word. Anything derived
            from them later is stored beside the original, never over it: a mis-reading stays
            recoverable, and a better model in six months can re-derive from source.
          </Explain>
        </p>
        <Card className="p-4">
          {deposition.observations.length === 0 ? (
            <EmptyState
              title="Nothing unexpected recorded"
              body="Either the run went exactly to plan, or nobody wrote down the part that did not. The second is more common than the first."
            />
          ) : (
            <ul className="space-y-3">
              {deposition.observations.map((o) => (
                <li key={o.id}>
                  <div className="tick tick-user">
                    <p className="font-serif text-reading">{o.raw}</p>
                    <div className="text-caption text-ink-soft mt-0.5">
                      <span className="font-num">{o.at.slice(11, 16)}</span>
                      {o.structured ? (
                        <>
                          {' · read as '}
                          <span className="text-ink">{o.structured}</span>
                        </>
                      ) : (
                        <>
                          {' · not yet structured'}
                          {deposition.state === 'closed' && (
                            <button
                              className="text-accent hover:underline ml-2"
                              onClick={() =>
                                structure(deposition.id, o.id, 'flagged for follow-up')
                              }
                            >
                              flag for follow-up
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <ComponentTag
          component="Deposition"
          action={`${deposition.entries.length} measured · ${deposition.observations.length} observed`}
        />
        {protocol && (
          <a
            href={href(`/protocols/${protocol.id}`)}
            className="text-caption text-accent hover:underline inline-flex items-center gap-1"
          >
            <FlaskConical size={12} aria-hidden /> {protocol.title} <ArrowRight size={12} />
          </a>
        )}
      </div>
    </>
  );
}
