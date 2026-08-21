// "What this part will be derived from" — one line per screen.
//
// Every part of this system is a replacement boundary, and for most of them the
// thing that eventually sits behind the boundary already exists. The note names
// it, and names how far along that decision is, because "will wrap BioSTEAM"
// and "wraps BioSTEAM" are very different claims and a demo is exactly the
// setting where they get conflated.
//
// The three states are visually distinct and the distinction is the content:
//
//   ported     a solid tick. Code from that project is in this repository now.
//   named      an open tick. The decision is recorded somewhere in the repo;
//              nothing calls it yet.
//   candidate  a dashed tick. An obvious fit nobody has committed to.
//
// Collapsed by default to one line. A demo where every screen shouts its
// dependencies is a demo about dependencies.
import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

import { UPSTREAM_BY_PART, type UpstreamStatus } from '@/data/demo/upstream';
import { cx } from '@/components/ui';

const STATUS_LABEL: Record<UpstreamStatus, string> = {
  ported: 'in the repo now',
  named: 'decided, not yet called',
  candidate: 'candidate — nobody has committed',
};

/** Tick geometry, reusing the house rule: form carries the epistemic state. */
function StatusMark({ status }: { status: UpstreamStatus }) {
  const base = 'inline-block w-[3px] h-3.5 align-middle shrink-0';
  if (status === 'ported')
    return <span className={base} style={{ background: 'rgb(var(--accent))' }} aria-hidden />;
  if (status === 'named')
    return (
      <span
        className={base}
        style={{ border: '1px solid rgb(var(--accent))', background: 'transparent' }}
        aria-hidden
      />
    );
  return (
    <span
      className={base}
      style={{
        backgroundImage:
          'repeating-linear-gradient(to bottom, rgb(var(--ink-soft)) 0 2px, transparent 2px 4px)',
      }}
      aria-hidden
    />
  );
}

export function UpstreamNote({ part, className }: { part: string; className?: string }) {
  const u = UPSTREAM_BY_PART[part];
  const [open, setOpen] = useState(false);
  if (!u) return null;

  const summary = u.deps.length
    ? u.deps.map((d) => d.name).join(' · ')
    : 'no upstream decided';

  return (
    <div className={cx('border-l-2 border-line pl-3 py-1', className)}>
      <button
        className="flex items-baseline gap-1.5 text-caption text-ink-soft hover:text-ink text-left w-full"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0 mt-0.5" aria-hidden />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 mt-0.5" aria-hidden />
        )}
        <span>
          <span className="text-ink">{u.label}</span> will be derived from{' '}
          <span className="text-ink">{summary}</span>
        </span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          <div className="text-caption text-ink-soft max-w-prose">{u.owns}</div>

          {u.deps.map((d) => (
            <div key={d.name} className="flex gap-2 text-caption">
              <span className="mt-0.5">
                <StatusMark status={d.status} />
              </span>
              <div className="min-w-0">
                <div>
                  {d.url ? (
                    <a
                      href={d.url}
                      target="_blank"
                      rel="noreferrer"
                      className="hover:text-accent underline decoration-dotted underline-offset-2"
                    >
                      {d.name}
                    </a>
                  ) : (
                    d.name
                  )}
                  <span className="text-ink-soft"> — {STATUS_LABEL[d.status]}</span>
                </div>
                <div className="text-ink-soft">{d.role}</div>
                {d.recordedIn && (
                  <div className="text-ink-soft font-num text-[11px]">recorded in {d.recordedIn}</div>
                )}
              </div>
            </div>
          ))}

          {u.openQuestion && (
            <div className="text-caption text-ink-soft border-l-2 pl-2 max-w-prose" style={{ borderColor: 'rgb(var(--signal-warn))' }}>
              {u.openQuestion}
            </div>
          )}

          {!u.deps.length && !u.openQuestion && (
            <div className="text-caption text-ink-soft">
              No upstream has been decided for this part.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
