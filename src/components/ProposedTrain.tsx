// A train pureOS's proposer proposed, as the service sent it (OF-BLD-020 §7.2,
// D12): what is missing at the top, then each unit in order with its reason
// beside it — the rule, the property it read and the artifact that holds
// that property (a link to BioRepo → Artifacts), in the service's words.
//
// Nothing here decides or computes. The units, their order, every reason and
// every missing property are the service's (`core/openferment_core/pureos/
// proposer.py`), and no number on it comes from the browser: a reason's words
// carry none, and a property's value is read on its artifact's page. A
// proposal types no parameter value; every one stays at its library default
// or waits for a person in the Builder.
//
// pureOS's index shows a proposal here once it comes back; the Builder
// (/pureos/build/:trainId, OF-BLD-020 §5.3) opens the same proposal from the
// store (`proposedTrains`) and mounts `ProposalMissingList` above its steps
// and `ProposalReasonLine` beside each unit's card.
import type { ProposalMissing, ProposalReason, TrainProposal } from '@/data/types';
import { UNIT_OPERATIONS_BY_ID } from '@/data/vocabulary';
import { href } from '@/router';
import { builderPath } from '@/lib/pureos';
import { Callout, Card } from '@/components/ui';

const LINK = 'text-accent hover:underline inline-flex min-h-[44px] items-center';

/** The properties the rules needed and nothing holds, each with why: shown first. */
export function ProposalMissingList({ missing }: { missing: ProposalMissing[] }) {
  if (!missing.length) return null;
  return (
    <div data-testid="proposal-missing-list">
      <Callout kind="warn" title="What the rules need and nothing holds">
        <ul className="space-y-1">
          {missing.map((m) => (
            <li key={`${m.property}-${m.why}`} data-testid="proposal-missing" data-property={m.property}>
              <span className="font-num">{m.property}</span>: {m.why}
            </li>
          ))}
        </ul>
      </Callout>
    </div>
  );
}

/** One unit's reason: the rule, the property it read, the artifact that holds it, and why. */
export function ProposalReasonLine({ reason }: { reason: ProposalReason }) {
  return (
    <div
      className="text-caption text-ink-soft"
      data-testid="proposal-reason"
      data-unit={reason.unitId}
      data-rule={reason.rule}
      data-property={reason.property}
      data-artifact={reason.artifactId ?? ''}
    >
      <div>
        Rule <span className="font-num text-ink">{reason.rule}</span>, reading{' '}
        <span className="font-num text-ink">{reason.property}</span>
        {reason.artifactId ? (
          <>
            {' '}from artifact{' '}
            <a className={LINK} href={href(`/biorepo/artifacts/${reason.artifactId}`)} data-testid="proposal-artifact">
              <span className="font-num">{reason.artifactId}</span>
            </a>
          </>
        ) : (
          ' from the products catalogue'
        )}
      </div>
      <div className="text-body text-ink-soft" data-testid="proposal-words">
        {reason.words}
      </div>
    </div>
  );
}

/**
 * A proposal whole: what it is for, what is missing, the units in order each
 * with its reason, the notes, and where it opens in the Builder (`trainId` is
 * the id this browser kept it under, or null when nothing was proposed).
 */
export function ProposedTrainView({ proposal, trainId }: { proposal: TrainProposal; trainId: string | null }) {
  const reasons = new Map(proposal.reasons.map((r) => [r.unitId, r]));
  const units = proposal.train?.units ?? [];
  return (
    <div className="space-y-3" data-testid="pureos-proposal" data-product={proposal.product} data-train={trainId ?? ''}>
      <p className="text-body text-ink">
        For <span className="font-num">{proposal.product}</span> made in <span className="font-num">{proposal.host}</span>
        {proposal.productClass ? `, a ${proposal.productClass}` : ', whose class nothing states'}
        {proposal.program ? `, on the ${proposal.program} chemicals` : ''}.
      </p>
      <ProposalMissingList missing={proposal.missing} />
      {units.length === 0 ? (
        <p className="text-body text-ink-soft" data-testid="proposal-none">
          Nothing is proposed: the rules need the properties named above.
        </p>
      ) : (
        <Card className="px-4 py-1">
          <ol>
            {units.map((u) => {
              const reason = reasons.get(u.id);
              const outlets = Object.entries(u.outlets ?? {});
              return (
                <li key={u.id} className="py-2.5 border-b border-line/70 last:border-0" data-testid="proposal-unit" data-unit={u.id} data-type={u.type}>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="font-num text-body text-ink">{u.id}</span>
                    <span className="text-body text-ink">{UNIT_OPERATIONS_BY_ID[u.type]?.label ?? u.type}</span>
                    <span className="font-num text-caption text-ink-soft">{u.type}</span>
                    {outlets.length > 0 && (
                      <span className="text-caption text-ink-soft">
                        {outlets.map(([port, route]) => `${port} ${route}`).join(' · ')}
                      </span>
                    )}
                  </div>
                  {reason && <ProposalReasonLine reason={reason} />}
                </li>
              );
            })}
          </ol>
        </Card>
      )}
      {proposal.notes.length > 0 && (
        <ul className="text-caption text-ink-soft list-disc pl-5 space-y-0.5" data-testid="proposal-notes">
          {proposal.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      {trainId && (
        <p className="text-body">
          <a className={LINK} href={href(builderPath(trainId))} data-testid="proposal-open-builder">
            Open it in the Builder
          </a>{' '}
          <span className="text-caption text-ink-soft">
            to fill what waits under your name and run it: every parameter is at its library default or waiting.
          </span>
        </p>
      )}
    </div>
  );
}
