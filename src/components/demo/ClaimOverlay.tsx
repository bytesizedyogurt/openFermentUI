// Per-step jurisdiction chips, coloured by claim status (OF-DEMO-002 §4.6).
//
// THE VISUAL TARGET: a route with an open surface should LOOK open at a glance,
// before the text says so. That is the whole reason this component exists — in
// Archetype 2 the biochemistry ranks the routes one way and the expiry dates
// reverse it, and the eye has to get there before the paragraph does.
//
// So enclosure is the loud state and openness is the quiet one. `signal-closed`
// is a filled chip; `expired` and `never-nationalised` are bare outlines that
// recede. A wall of filled chips beside a row of outlines is the finding.
import type { ClaimStatus } from '@/data/demo/types';
import { PATENT_BY_ID } from '@/data/demo/patents';
import { DEMO_NOW } from '@/data/demo/core';
import { monthsToExpiry } from '@/lib/demo';
import { cx } from '@/components/ui';

const STATUS: Record<ClaimStatus, { label: string; className: string; style?: React.CSSProperties }> = {
  enclosed: {
    label: 'enclosed',
    className: 'text-[rgb(var(--signal-closed))] border-[rgb(var(--signal-closed))]',
    style: { background: 'rgb(var(--signal-closed) / 0.14)' },
  },
  expiring: {
    label: 'expiring',
    className: 'text-signal-warn border-signal-warn',
    style: { background: 'rgb(var(--signal-warn) / 0.12)' },
  },
  expired: { label: 'expired', className: 'text-ink-soft border-line' },
  'never-nationalised': { label: 'never nationalised', className: 'text-ink-soft border-line' },
  'no-claim-found': { label: 'no claim found', className: 'text-ink-soft border-line border-dashed' },
  pending: { label: 'pending', className: 'text-signal-info border-signal-info border-dashed' },
};

/** Order matters: the loud states first, so a scan hits enclosure immediately. */
const RANK: Record<ClaimStatus, number> = {
  enclosed: 0,
  expiring: 1,
  pending: 2,
  'never-nationalised': 3,
  expired: 4,
  'no-claim-found': 5,
};

export function ClaimChip({
  jurisdiction,
  status,
  familyIds,
}: {
  jurisdiction: string;
  status: ClaimStatus;
  familyIds?: string[];
}) {
  const s = STATUS[status];
  const detail = (familyIds ?? [])
    .map((id) => {
      const fam = PATENT_BY_ID[id];
      if (!fam) return id;
      const j = fam.jurisdictions.find((x) => x.code === jurisdiction);
      const months = j?.expiry ? monthsToExpiry(j.expiry, DEMO_NOW) : null;
      return `${id} (${fam.assignee})${j?.expiry ? ` — expires ${j.expiry}${months !== null ? `, ${months} months` : ''}` : ''}`;
    })
    .join('\n');

  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 border rounded-[2px] px-1 text-[11px] leading-4 font-num whitespace-nowrap',
        s.className,
      )}
      style={s.style}
      title={`${jurisdiction}: ${s.label}${detail ? `\n${detail}` : ''}`}
    >
      {jurisdiction}
      <span className="opacity-70 font-sans">{s.label}</span>
    </span>
  );
}

export function ClaimOverlay({
  rows,
  className,
}: {
  rows: { step: string; status?: ClaimStatus; positions?: { jurisdiction: string; status: ClaimStatus; familyIds: string[] }[]; familyIds?: string[] }[];
  className?: string;
}) {
  return (
    <div className={cx('min-w-0', className)}>
      {rows.map((r, i) => {
        const positions = r.positions ?? (r.status ? [{ jurisdiction: '—', status: r.status, familyIds: r.familyIds ?? [] }] : []);
        const sorted = [...positions].sort((a, b) => RANK[a.status] - RANK[b.status]);
        const enclosed = positions.filter((p) => p.status === 'enclosed').length;
        return (
          <div key={`${r.step}-${i}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 py-1 border-b border-line/60 last:border-0">
            <div className="min-w-[13rem] flex-1 text-caption">
              {r.step}
              {enclosed > 0 && (
                <span className="ml-1.5 text-[11px]" style={{ color: 'rgb(var(--signal-closed))' }}>
                  {enclosed} enclosed
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {sorted.length ? (
                sorted.map((p) => (
                  <ClaimChip key={`${p.jurisdiction}-${p.status}`} jurisdiction={p.jurisdiction} status={p.status} familyIds={p.familyIds} />
                ))
              ) : (
                <span className="text-caption text-ink-soft">no position recorded</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** The one-line summary a route card carries. */
export function OpenSurfaceSummary({
  totalSteps,
  enclosedSteps,
  expiringSteps,
}: {
  totalSteps: number;
  enclosedSteps: number;
  expiringSteps: number;
}) {
  const open = totalSteps - enclosedSteps;
  return (
    <span className="text-caption font-num">
      <span style={{ color: open > 0 ? 'rgb(var(--signal-open))' : 'rgb(var(--signal-closed))' }}>
        {open}/{totalSteps} open
      </span>
      {enclosedSteps > 0 && (
        <span style={{ color: 'rgb(var(--signal-closed))' }} className="ml-2">
          {enclosedSteps} enclosed
        </span>
      )}
      {expiringSteps > 0 && (
        <span className="ml-2 text-signal-warn">{expiringSteps} expiring</span>
      )}
    </span>
  );
}
