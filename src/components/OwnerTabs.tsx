// The sub-view tab strip (OF-BLD-008 §6).
//
// Five things stopped being destinations and became views inside their owner.
// This is the one component that renders that relationship, so the pattern is
// the same everywhere rather than reinvented per screen.
//
// THE ACTIVE TAB IS IN THE URL, ALWAYS. A tab strip that holds its state in
// React looks identical and is broken in three ways a reader will hit within a
// minute: the tab cannot be linked, the back button leaves the page instead of
// the tab, and a reload lands somewhere else. Every tab here is a real route,
// so `/dominion/clearance` is a thing you can send somebody.
//
// Tabs mount the EXISTING screens unmodified. Moving a screen under an owner
// is a routing change, not a rewrite — Organisms.tsx is the same file it was.
import { href, useRoute } from '@/router';
import { cx } from './ui';

export interface OwnerTab {
  /** What the tab says. */
  label: string;
  /** The route it owns. The first tab is the owner's own path. */
  to: string;
  /** Count or state, shown quietly beside the label when there is one. */
  badge?: string | number;
  /** Greyed and non-navigating when the view has nothing behind it yet. */
  disabled?: boolean;
}

/**
 * Which tab a path is inside.
 *
 * Longest match wins, so `/runbooks/protocols/PR-TAP-01` selects Protocols
 * rather than Runbooks — a detail page belongs to the tab it was reached
 * through, and highlighting the parent instead would tell the reader they are
 * somewhere they are not.
 */
export function activeTab(path: string, tabs: OwnerTab[]): string {
  let best = tabs[0]?.to ?? '';
  let bestLength = -1;
  for (const tab of tabs) {
    const matches = path === tab.to || path.startsWith(tab.to + '/');
    if (matches && tab.to.length > bestLength) {
      best = tab.to;
      bestLength = tab.to.length;
    }
  }
  return best;
}

export function OwnerTabs({ tabs }: { tabs: OwnerTab[] }) {
  const route = useRoute();
  const active = activeTab(route.path, tabs);

  return (
    <div
      className="flex flex-wrap items-center gap-1 -mt-2 mb-5 border-b border-line"
      role="tablist"
      aria-label="Views"
    >
      {tabs.map((tab) => {
        const isActive = tab.to === active;
        if (tab.disabled) {
          return (
            <span
              key={tab.to}
              className="px-3 py-1.5 text-body text-ink-soft/50 cursor-default"
              title="Nothing here yet"
              role="tab"
              aria-selected={false}
              aria-disabled
            >
              {tab.label}
            </span>
          );
        }
        return (
          <a
            key={tab.to}
            href={href(tab.to)}
            role="tab"
            aria-selected={isActive}
            aria-current={isActive ? 'page' : undefined}
            className={cx(
              'px-3 py-1.5 text-body border-b-2 -mb-px transition-colors inline-flex items-baseline gap-1.5',
              isActive
                ? 'border-accent text-accent font-medium'
                : 'border-transparent text-ink-soft hover:text-ink',
            )}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span className="font-num text-caption text-ink-soft">{tab.badge}</span>
            )}
          </a>
        );
      })}
    </div>
  );
}
