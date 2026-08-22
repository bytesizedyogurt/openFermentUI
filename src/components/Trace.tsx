// A number's address, wherever it appears.
//
// The Bench teaches this in four boxes: the source it came from, the record
// somebody wrote down, the check that has not happened, and the model that
// already uses it. That was a lesson on one screen about one record. This is
// the same four steps as a GESTURE — hover, click, or focus and press `t` on
// any provenance-bearing value in the app, and it unfolds its own chain in
// place, without navigating away.
//
// It is the product's argument made physical. Everything this software claims
// rests on "every number has an address"; until now a reader had to take that
// on faith everywhere except the front door.
//
// ── THE THIRD STEP IS THE POINT ────────────────────────────────────────────
//
// For an unverified value — which today is every value in the corpus — the
// third box is an em dash and says nobody has checked it. A trace that quietly
// skipped that step when it had nothing to show would turn the product's
// central admission into a footnote, which is the exact failure mode this
// component exists to make impossible. `missing` is therefore not an edge
// case in the renderer; it is a first-class step kind.
//
// ── WHY THIS TAKES A RESOLVED TRACE AND NOT AN ID ──────────────────────────
//
// A component that took an id would have to dispatch on its prefix, which
// means importing both object pools' resolvers into one module. The two pools
// are held apart on purpose. So the call site — which always knows which pool
// it is in — resolves the trace, and this file renders it and never imports a
// record or an Accession.
import { type ReactNode } from 'react';
import { ArrowUpRight } from 'lucide-react';

import { href } from '@/router';
import { Tick, type ProvKind } from '@/components/Provenance';
import { Popover, cx } from '@/components/ui';

export interface TraceStepSpec {
  /** Short label naming the OBJECT, not the part — "The source", "The record". */
  label: string;
  /** The part that owns this step, as a quiet second line. */
  part: string;
  /** Where the step goes. Omitted renders the step unlinked. */
  to?: string;
  /** The step's headline — an id, a value, a name. */
  headline?: ReactNode;
  /** One or two lines under the headline. */
  body?: ReactNode;
  /**
   * Provenance hue. Omitted means the step carries no datum, so it wears no
   * tick — a hue standing for nothing is worse than no hue.
   */
  prov?: ProvKind;
  /** The step that has not happened. Renders an em dash and a dashed border. */
  missing?: boolean;
}

export interface Trace {
  /** The id this trace is of, for the popover's label. */
  id: string;
  steps: TraceStepSpec[];
}

/**
 * One step. Used both by the Bench's full-width strip and by the popover, so
 * the two cannot drift into different vocabularies for the same idea.
 */
export function TraceStep({
  n,
  step,
  compact,
}: {
  n: string;
  step: TraceStepSpec;
  compact?: boolean;
}) {
  const inner = (
    <>
      <div className="flex items-baseline gap-1.5">
        <span className="font-num text-caption text-ink-soft">{n}</span>
        <span className="text-caption uppercase tracking-wide text-ink-soft">{step.label}</span>
        {step.to && (
          <ArrowUpRight size={12} className="text-ink-soft shrink-0 ml-auto" aria-hidden />
        )}
      </div>
      <div className="text-caption text-ink-soft">{step.part}</div>
      <div className={cx(compact ? 'text-caption mt-0.5' : 'text-body mt-1.5')}>
        {step.missing && (
          <div
            className={cx(
              'font-num leading-none text-ink-soft',
              compact ? 'text-page-title' : 'text-display',
            )}
            aria-hidden
          >
            —
          </div>
        )}
        {step.headline && <div className={cx(step.missing && 'mt-1.5')}>{step.headline}</div>}
        {step.body && <div className="text-caption text-ink-soft mt-1">{step.body}</div>}
      </div>
    </>
  );

  const body = step.prov ? (
    <Tick p={step.prov} className="h-full">
      {inner}
    </Tick>
  ) : (
    inner
  );

  const shell = cx(
    // `trace-step` staggers the chain so its ORDER reads: a source precedes a
    // record precedes a check precedes a use, and that sequence is the argument.
    'card block motion-colors trace-step',
    compact ? 'p-2' : 'p-3',
    step.to && 'hover:border-accent/45 hover:bg-accent-wash/40',
    step.missing && 'border-dashed',
  );

  return step.to ? (
    <a href={href(step.to)} className={shell}>
      {body}
    </a>
  ) : (
    <div className={shell}>{body}</div>
  );
}

/** The four steps as a strip. The Bench's band and the popover share it. */
export function TraceSteps({
  trace,
  compact,
  className,
}: {
  trace: Trace;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cx(
        'grid grid-cols-1 gap-2',
        compact ? '' : 'sm:grid-cols-2 xl:grid-cols-4',
        className,
      )}
    >
      {trace.steps.map((s, i) => (
        <TraceStep key={s.label} n={String(i + 1).padStart(2, '0')} step={s} compact={compact} />
      ))}
    </div>
  );
}

/**
 * The gesture. Wraps any value in a trigger that unfolds its trace.
 *
 * `Popover` already handles hover intent, click, Escape, outside-click,
 * scroll-repositioning and the portal, so this adds the one thing it does not
 * have: a keyboard verb. `t` on the focused trigger opens the chain, which is
 * the same key the shortcut sheet documents.
 */
export function TraceAffordance({
  trace,
  children,
  className,
}: {
  trace: Trace | null;
  children: ReactNode;
  className?: string;
}) {
  // No trace resolved is not an error state and must not look like one — the
  // value simply renders as it did before the gesture existed.
  if (!trace) return <>{children}</>;

  return (
    <Popover
      width={320}
      label={`Where ${trace.id} comes from`}
      trigger={(p) => (
        <button
          {...p}
          onKeyDown={(e) => {
            if (e.key === 't' || e.key === 'T') {
              e.preventDefault();
              p.onClick();
            }
          }}
          className={cx(
            'text-left align-baseline underline decoration-dotted decoration-ink-soft/50',
            'underline-offset-[3px] hover:decoration-accent motion-colors',
            className,
          )}
          title={`${trace.id} — press t to follow this number back to its source`}
        >
          {children}
        </button>
      )}
    >
      <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
        Where <span className="font-num normal-case">{trace.id}</span> comes from
      </div>
      {/* Four steps stacked will outrun a short viewport, and `Popover`'s
          flip-up only moves the panel — it does not shrink it. Bounded here so
          the last step is always reachable. */}
      <div className="max-h-[min(60vh,420px)] overflow-y-auto -mx-1 px-1">
        <TraceSteps trace={trace} compact />
      </div>
    </Popover>
  );
}
