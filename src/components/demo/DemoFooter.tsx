// `SEED_DISCLAIMER`, rendered somewhere persistent.
//
// OF-DEMO-001 §2.2 requires this to be reachable, and `check:demo-seed` proves
// the string says what it must. Rendering it is the other half: a disclaimer
// that exists in a constant and never reaches a screen is a comment.
//
// It sits at the FOOT of every demo screen rather than in a dismissible banner
// for one reason — a banner a reviewer closes on the first screen is a
// disclaimer they do not see on the twentieth, and by then they are reading
// patent numbers.
import { SEED_DISCLAIMER, DEMO_NOW } from '@/data/demo/core';

export function DemoFooter() {
  return (
    <footer className="mt-8 pt-3 border-t border-line text-caption text-ink-soft max-w-prose">
      <span
        className="inline-block w-[3px] h-3 rounded-[1px] mr-1.5 align-middle"
        style={{
          backgroundImage:
            'repeating-linear-gradient(to bottom, rgb(var(--signal-warn)) 0 3px, transparent 3px 6px)',
        }}
        aria-hidden
      />
      {SEED_DISCLAIMER}{' '}
      <span className="font-num">
        Dates are computed against a frozen present of {DEMO_NOW}, so an expiry countdown reads the
        same today as it did when it was written.
      </span>
    </footer>
  );
}
