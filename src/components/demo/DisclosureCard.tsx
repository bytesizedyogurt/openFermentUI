// One `DisclosureCandidate` (OF-DEMO-002 §4.10).
//
// This is the component the project's reason lives in. Every archetype ends by
// naming what should be defensively published, and OF-DEMO-001 §2.6 makes the
// field required rather than optional: if an archetype produces none, that is a
// signal the archetype is wrong.
//
// THE ENABLING DETAIL IS THE HARD PART and the card leads with it after the
// claim. A disclosure that is not enabling does not bar anything — it is a
// press release. Listing exactly what would have to be published to make the
// disclosure count is worth more than a queue of publishable-looking cards,
// because it makes the gap precise instead of implying there isn't one.
//
// DELIBERATELY ABSENT: a button that publishes. The action is "add to the
// Notary queue", which is reversible and human-initiated. Publication with a
// provable date is irreversible, and nothing in this interface should be one
// click away from it.
import { Clock, ShieldAlert } from 'lucide-react';

import type { DisclosureCandidate } from '@/data/demo/types';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { AccessionValue } from './AccessionValue';

const REASON_LABEL: Record<DisclosureCandidate['reason'], string> = {
  'unclaimed-process-region': 'unclaimed process region',
  'parameter-region-open': 'parameter region left open',
  'enzyme-variant-at-risk': 'enzyme variant likely to be filed',
  'jurisdictional-gap': 'jurisdictional gap',
  'negative-result-unpublished': 'negative result nobody has published',
};

const URGENCY: Record<DisclosureCandidate['urgency'], { label: string; className: string }> = {
  now: { label: 'now', className: 'text-signal-closed' },
  months: { label: 'months', className: 'text-signal-warn' },
  watch: { label: 'watch', className: 'text-ink-soft' },
};

export const URGENCY_RANK: Record<DisclosureCandidate['urgency'], number> = {
  now: 0,
  months: 1,
  watch: 2,
};

export function DisclosureCard({
  dc,
  showArchetype = true,
  className,
}: {
  dc: DisclosureCandidate;
  showArchetype?: boolean;
  className?: string;
}) {
  const u = URGENCY[dc.urgency];
  return (
    // `id` is the anchor for `/notary/disclosures#DC-003`, which every
    // archetype's deliverable links back to. `scroll-mt` keeps the card clear
    // of the sticky header when `useFragmentScroll` brings it into view.
    <div id={dc.id} className={cx('border border-line p-3 scroll-mt-4', className)}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-1">
        <span className="font-num text-caption text-ink-soft">{dc.id}</span>
        <span className={cx('text-caption', u.className)}>
          {u.label}
          {dc.estimatedWindowMonths !== undefined && (
            <span className="ml-1 font-num">· ~{dc.estimatedWindowMonths} mo window</span>
          )}
        </span>
        <span className="text-caption text-ink-soft">{REASON_LABEL[dc.reason]}</span>
        {showArchetype && (
          <a href={href(`/notary/disclosures#${dc.id}`)} className="text-caption font-num text-ink-soft hover:text-accent ml-auto">
            {dc.archetype}
          </a>
        )}
      </div>

      <div className="text-body">{dc.what}</div>

      <div className="mt-2">
        <div className="text-caption text-ink-soft flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" aria-hidden />
          To be enabling, a disclosure would have to publish:
        </div>
        <ul className="mt-0.5 space-y-0.5">
          {dc.enablingDetail.map((d, i) => (
            <li key={i} className="text-caption pl-3 relative">
              <span className="absolute left-0 text-ink-soft">·</span>
              {d}
            </li>
          ))}
        </ul>
        {dc.enablingDetail.length === 0 && (
          <div className="text-caption text-signal-error">
            No enabling detail listed. A disclosure without it does not bar anything.
          </div>
        )}
      </div>

      {dc.supportingAccessionIds.length > 0 && (
        <div className="mt-2">
          <div className="text-caption text-ink-soft">Rests on</div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-0.5">
            {dc.supportingAccessionIds.map((id) => (
              <AccessionValue key={id} id={id} />
            ))}
          </div>
        </div>
      )}

      <div className="mt-2 text-caption text-ink-soft flex items-center gap-1">
        <Clock className="w-3 h-3" aria-hidden />
        Venue: {dc.venue}
      </div>
    </div>
  );
}
