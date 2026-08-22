// The thirteen parts, grouped by movement.
//
// WHY THIS EXISTS. The rail lists the parts and the foot of every screen names
// one of them, but the Bench never explained any of it — a reader who had not
// been told could not learn from this product what its parts were, only that it
// had a lot of screens. That is the largest orientation gap in the build and it
// is closed by rendering the table the architecture already keeps.
//
// EVERYTHING HERE IS READ, NOT RESTATED. Labels and `owns` clauses come from
// `UPSTREAM`; movements, routes and rail keys from `data/parts.ts`. There is no
// copy in this file about any individual part, so the map cannot drift from the
// navigation it describes.
//
// THE UPSTREAM KEY IS AGGREGATE, DELIBERATELY. Printing three dependency marks
// against each of thirteen rows turns a map into a bibliography and doubles the
// height on a phone. The summary carries the honest argument — how much of this
// system is code versus a written-down intention — and `UpstreamNote` at the
// foot of each screen carries the per-part detail for anyone who wants it.
import { UPSTREAM, UPSTREAM_BY_PART, type UpstreamStatus } from '@/data/demo/upstream';
import { MOVEMENTS, PART_KEY, PART_ROUTE, partsIn } from '@/data/parts';
import { href } from '@/router';
import { StatusMark, STATUS_SHORT } from '@/components/Upstream';
import { Card, cx } from '@/components/ui';

/** What each movement is FOR, in the reader's terms rather than the architecture's. */
const MOVEMENT_GLOSS: Record<string, string> = {
  Read: 'Get evidence in, and know what it is worth.',
  Reason: 'Turn evidence into an answer you can check.',
  Return: 'Put something back — a procedure, a publication, a lab.',
};

export function PartsMap({ className }: { className?: string }) {
  // Counted, not asserted: how much of this system is code today.
  const deps = UPSTREAM.flatMap((p) => p.deps);
  const tally = (s: UpstreamStatus) => deps.filter((d) => d.status === s).length;
  const projects = new Set(deps.map((d) => d.name)).size;

  return (
    <div className={className}>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {MOVEMENTS.map((m) => (
          <Card key={m} className="p-3">
            <div className="text-caption uppercase tracking-wide text-ink-soft">{m}</div>
            <div className="text-caption text-ink-soft mt-0.5 mb-2">{MOVEMENT_GLOSS[m]}</div>
            <ul className="space-y-2">
              {partsIn(m).map((part) => {
                const u = UPSTREAM_BY_PART[part];
                if (!u) return null;
                return (
                  <li key={part}>
                    <a
                      href={href(PART_ROUTE[part] ?? '/')}
                      className="group flex items-baseline gap-1.5"
                    >
                      <span className="font-medium group-hover:text-accent">{u.label}</span>
                      {/* The chord, beside the name it reaches. The rail is
                          `hidden md:flex`, so on a phone this is the only way
                          the navigation is visible at all. */}
                      <span className="font-num text-caption text-ink-soft shrink-0">
                        g {PART_KEY[part]}
                      </span>
                    </a>
                    <div className="text-caption text-ink-soft">{u.owns}</div>
                  </li>
                );
              })}
            </ul>
          </Card>
        ))}
      </div>

      <Card className="p-3 mt-3">
        <div className="text-caption text-ink-soft">
          Each part is a replacement boundary, and for most the thing that will sit behind it
          already exists as open-source software. Across the thirteen there are{' '}
          <span className="font-num text-ink">{deps.length}</span> declarations naming{' '}
          <span className="font-num text-ink">{projects}</span> projects:
        </div>
        <ul className="flex flex-wrap gap-x-5 gap-y-1 mt-2 text-caption">
          {(['ported', 'named', 'candidate'] as UpstreamStatus[]).map((s) => (
            <li key={s} className="inline-flex items-baseline gap-1.5">
              <StatusMark status={s} />
              <span className="font-num text-ink">{tally(s)}</span>
              <span>{STATUS_SHORT[s]}</span>
              <span className="text-ink-soft">
                {s === 'ported'
                  ? '— code is in this repository now'
                  : s === 'named'
                    ? '— decided and written down; nothing calls it yet'
                    : '— an obvious fit nobody has committed to'}
              </span>
            </li>
          ))}
        </ul>
        <div className={cx('text-caption text-ink-soft mt-2 max-w-prose')}>
          Status is per part, not per project — Inspect AI is ported for Audit&rsquo;s scorer and
          only named for Intake, so one project honestly carries two marks.
        </div>
      </Card>
    </div>
  );
}
