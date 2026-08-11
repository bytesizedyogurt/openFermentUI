// Provenance badge (explicit) and evidence tick (ambient) — both derive from
// one `provenance` value so they can never disagree (OF-DES-001 §7.4).
import type { ReactNode } from 'react';
import { Award, ShieldCheck, CircleDashed, UserPen, FlaskConical, Ban, BookMarked, TrendingUp, TriangleAlert } from 'lucide-react';
import type { EvidenceClass, Provenance } from '@/data/types';
import { cx } from './ui';

export type ProvKind = Provenance | 'rejected';

const META: Record<ProvKind, { label: string; Icon: typeof Award; color: string; tick: string }> = {
  gold: { label: 'Curated · gold set', Icon: Award, color: 'text-gold', tick: 'tick-gold' },
  verified: { label: 'Verified against source', Icon: ShieldCheck, color: 'text-accent', tick: 'tick-verified' },
  curated: {
    label: 'Curated · pending source check',
    Icon: BookMarked,
    color: 'text-accent/70',
    tick: 'tick-curated',
  },
  'industry-estimate': {
    label: 'Industry estimate · not evidence',
    Icon: TrendingUp,
    color: 'text-ink-soft',
    tick: 'tick-industry-estimate',
  },
  unverified: {
    label: 'Extracted · unverified',
    Icon: CircleDashed,
    color: 'text-ink-soft',
    tick: 'tick-unverified',
  },
  user: { label: 'User-entered', Icon: UserPen, color: 'text-signal-info', tick: 'tick-user' },
  demo: { label: 'Modeled · not measured', Icon: FlaskConical, color: 'text-signal-warn', tick: 'tick-demo' },
  rejected: { label: 'Rejected', Icon: Ban, color: 'text-signal-error', tick: 'tick-rejected' },
  unsourced: {
    label: 'UNSOURCED — no provenance record',
    Icon: TriangleAlert,
    color: 'text-signal-error',
    tick: 'tick-unsourced',
  },
};

/**
 * Evidence class rides on tick geometry, never on hue. Hue is spoken for by
 * provenance, and the ambient-texture property the palette exists to create
 * survives only while one axis owns colour. All five variants stay apart in
 * greyscale and to a deuteranope, which the existing solid/dashed split already
 * establishes as the house rule.
 */
const EVIDENCE_TICK: Record<EvidenceClass, string> = {
  literature: '',                    // the baseline — no existing screen changes
  patent: 'tick-ev-patent',          // a 1px gap at mid-height: a boundary marker
  computed: 'tick-ev-computed',      // an inner light stripe: derived, not observed
  experiment: 'tick-ev-experiment',  // overshoots top and bottom: a bench mark
  correction: 'tick-ev-correction',  // a caret at the head: an amendment
};

export function evidenceTickClass(e?: EvidenceClass): string {
  return e ? EVIDENCE_TICK[e] : '';
}

export function provMeta(p: ProvKind) {
  return META[p];
}

/** Ambient form: the 3px notched left border used in tables and stats. */
export function Tick({
  p,
  e,
  children,
  className,
  title,
  demonstration,
}: {
  p: ProvKind;
  /** Evidence class. Omitted means literature — the baseline geometry. */
  e?: EvidenceClass;
  children: ReactNode;
  className?: string;
  title?: string;
  /**
   * Set only by the fault-state demonstration in Settings. The alarm below
   * exists to catch a quantity that reached the interface by accident; a
   * demonstration that announces itself is not that, and silencing it here
   * keeps the alarm meaningful everywhere else — including in the route smoke
   * test, which fails a screen on any console error.
   */
  demonstration?: boolean;
}) {
  // A quantity with no provenance behind it is a defect, not a display state.
  // Fail loudly rather than let it render quietly in grey.
  if (p === 'unsourced' && !demonstration) {
    console.error('[of] unsourced quantity rendered', { title });
  }
  return (
    <div
      className={cx('tick', META[p].tick, evidenceTickClass(e), className)}
      title={title ?? META[p].label}
    >
      <span className="sr-only">
        {META[p].label}
        {e && e !== 'literature' ? `, ${e}` : ''}.{' '}
      </span>
      {children}
    </div>
  );
}

/** Explicit form: icon + label, used in detail views and popovers. */
export function ProvenanceBadge({
  p,
  confidence,
  compact,
}: {
  p: ProvKind;
  confidence?: number;
  compact?: boolean;
}) {
  const { label, Icon, color } = META[p];
  const text =
    p === 'unverified' && confidence !== undefined ? `${label} · ${confidence.toFixed(2)}` : label;
  return (
    <span className={cx('chip', compact && 'text-[11px] py-0', color)} title={text}>
      <Icon size={12} aria-hidden />
      {text}
    </span>
  );
}

/** Just the colored dot — for dense strip plots and legends. */
export function ProvDot({ p, size = 8 }: { p: ProvKind; size?: number }) {
  const bg: Record<ProvKind, string> = {
    gold: 'bg-gold',
    verified: 'bg-accent',
    curated: 'bg-accent/45',
    'industry-estimate': 'bg-ink-soft/60',
    unverified: 'bg-ink-soft',
    user: 'bg-signal-info',
    demo: 'bg-signal-warn',
    rejected: 'bg-signal-error',
    unsourced: 'bg-signal-error',
  };
  return (
    <span
      className={cx('inline-block rounded-full', bg[p])}
      style={{ width: size, height: size }}
      aria-label={META[p].label}
    />
  );
}

/**
 * The evidence-class axis, shown as geometry over a single provenance hue so a
 * reader can see that shape carries the distinction and colour does not.
 */
export function EvidenceLegend() {
  const rows: { e: EvidenceClass; note: string }[] = [
    { e: 'literature', note: 'a paper, thesis or report' },
    { e: 'patent', note: 'a claim, gapped at mid-height' },
    { e: 'computed', note: 'a prediction — hollow, derived not observed' },
    { e: 'experiment', note: 'a bench measurement — overshoots its box' },
    { e: 'correction', note: 'supersedes an earlier entry' },
  ];
  return (
    <div className="space-y-1.5">
      {rows.map(({ e, note }) => (
        <Tick key={e} p="curated" e={e} className="py-0.5">
          <span className="text-caption">
            <span className="font-mono">{e}</span>
            <span className="text-ink-soft"> — {note}</span>
          </span>
        </Tick>
      ))}
    </div>
  );
}

/**
 * The fault state, rendered deliberately. `unsourced` marks a quantity that
 * reached the interface with no provenance behind it — Rule 1 of the agent
 * contract violated. check:seed proves no seeded record can be in this state,
 * so this is the only place it appears: a reviewer should be able to see what
 * the system does when the rule breaks rather than take it on trust.
 */
export function UnsourcedDemo() {
  return (
    <Tick
      p="unsourced"
      demonstration
      title="Demonstration of the fault state — not real data"
    >
      <div className="text-body">
        Secreted titer <span className="font-num">18 mg L⁻¹</span>
      </div>
      <div className="text-caption text-signal-error mt-0.5">
        No provenance record. A quantity in this state is a defect, not a datum — it means a
        number reached the interface without a source behind it.
      </div>
    </Tick>
  );
}

export function ProvenanceLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft">
      {(
        ['gold', 'verified', 'curated', 'unverified', 'industry-estimate', 'user', 'demo'] as ProvKind[]
      ).map((p) => (
        <span key={p} className="inline-flex items-center gap-1.5">
          <ProvDot p={p} />
          {META[p].label}
        </span>
      ))}
    </div>
  );
}
