// Provenance badge (explicit) and evidence tick (ambient) — both derive from
// one `provenance` value so they can never disagree (OF-DES-001 §7.4).
import type { ReactNode } from 'react';
import { Award, ShieldCheck, CircleDashed, UserPen, FlaskConical, Ban, BookMarked, Microscope, TrendingUp } from 'lucide-react';
import type { Provenance } from '@/data/types';
import { referenceFor } from '@/data/reference';
import { Explain, cx } from './ui';

export type ProvKind = Provenance | 'rejected';

const META: Record<ProvKind, { label: string; Icon: typeof Award; color: string; tick: string }> = {
  measured: {
    label: 'Measured · first-party',
    Icon: Microscope,
    color: 'text-gold',
    tick: 'tick-measured',
  },
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
};

export function provMeta(p: ProvKind) {
  return META[p];
}

/** Ambient form: the 3px notched left border used in tables and stats. */
export function Tick({
  p,
  children,
  className,
  title,
}: {
  p: ProvKind;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <div className={cx('tick', META[p].tick, className)} title={title ?? META[p].label}>
      <span className="sr-only">{META[p].label}. </span>
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
    measured: 'bg-gold',
    gold: 'bg-gold',
    verified: 'bg-accent',
    curated: 'bg-accent/45',
    'industry-estimate': 'bg-ink-soft/60',
    unverified: 'bg-ink-soft',
    user: 'bg-signal-info',
    demo: 'bg-signal-warn',
    rejected: 'bg-signal-error',
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
 * The legend, and — behind a disclosure — what each level means for aggregates.
 *
 * OF-BLD-010 §5 puts the `biorepo.audit` provenance table here, because a
 * legend that names eight levels without saying which of them are held out of a
 * median is telling a reader half of what the tick means. The rows come from
 * `reference.ts` so there is ONE source rather than a copy per screen, and
 * `pnpm check:reference` fails the build if that source disagrees with
 * `PROVENANCE_LABEL` or with what `aggregateExclusion()` actually does.
 *
 * Collapsed by default. Eight levels inline is the compact form eight screens
 * already rely on; the table is for the reader who stops to ask.
 */
export function ProvenanceLegend() {
  const table = referenceFor('biorepo.audit')?.tables.find((t) => t.title === 'Provenance levels');
  const excluded = (table?.rows ?? []).filter((r) => r[2] === 'No');

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft">
      {(
        ['measured', 'gold', 'verified', 'curated', 'unverified', 'industry-estimate', 'user', 'demo'] as ProvKind[]
      ).map((p) => (
        <span key={p} className="inline-flex items-center gap-1.5">
          <ProvDot p={p} />
          {META[p].label}
        </span>
      ))}
      {table && (
        <Explain label={`${excluded.length} of these are held out of aggregates`}>
          <div className="text-body">
            <p className="mb-2 text-ink">
              A tick says where a number came from. Two of these levels are excluded from any
              aggregate: an industry estimate is not evidence, and a modelled value is not a
              measurement. Counting either one would overstate what the corpus knows.
            </p>
            <table className="w-full border-collapse text-body">
              <thead>
                <tr className="border-b border-line">
                  {table.cols.map((c) => (
                    <th key={c} className="text-caption font-medium text-ink-soft px-1.5 py-1 text-left">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((r) => (
                  <tr key={r[0]} className="border-b border-line/60 last:border-0">
                    <td className="font-num px-1.5 py-1 text-ink whitespace-nowrap">{r[0]}</td>
                    <td className="px-1.5 py-1 text-ink-soft">{r[1]}</td>
                    <td
                      className={cx(
                        'px-1.5 py-1 font-num',
                        r[2] === 'No' ? 'text-signal-warn' : 'text-ink-soft',
                      )}
                    >
                      {r[2]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Explain>
      )}
    </div>
  );
}
