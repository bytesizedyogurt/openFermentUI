// The frame a price is quoted in, rendered wherever a price appears.
//
// ── WHY THIS EXISTS ───────────────────────────────────────────────────────
//
// `BiosteamSettings.tsx` opens with the argument: "A techno-economic result is a
// function of two things: the flowsheet, and the basis it is discounted and
// indexed against. The flowsheet gets a whole screen. The basis usually gets a
// footnote, which is how two plants end up compared at two different discount
// rates and nobody notices."
//
// Proforma's charter is "techno-economics against an explicit regional and
// temporal basis". This component is that charter made into something a reader
// can see next to the number it governs.
//
// ── WHY THIS TAKES A RESOLVED BASIS AND NOT AN ID ─────────────────────────
//
// The same rule `Trace.tsx` follows, for the same reason. A component that took
// an id would have to dispatch on its prefix, which means importing both object
// pools' resolvers into one module. The two pools are held apart on purpose. So
// the call site — which always knows which pool it is in — resolves the basis,
// and this file renders it and never imports a `Scenario` or a `Candidate`.
//
// ── THE TWO ABSENCES ARE DIFFERENT, AND BOTH ARE SHOWN ────────────────────
//
// A basis that is entirely missing means the price should not be on screen at
// all — that is Proforma's own `openQuestion`, and the caller enforces it by
// not rendering. A basis with a `region: undeclared` or an `accuracy: unstated`
// arm is a DECLARED gap: the price is real, and what nobody has established
// about it is stated in the same breath. Those arms render as prominently as
// the numbers do, because the whole argument of this build is that an absence a
// reader cannot see is worse than one they can.
import { useState } from 'react';
import { ChevronRight, MapPin } from 'lucide-react';

import type { QuotationBasis } from '@/data/types';
import { cx } from '@/components/ui';

/** A percentage from a fraction, with no decimal it has not earned. */
function pct(v: number | undefined): string {
  if (v === undefined || !Number.isFinite(v)) return '—';
  const p = v * 100;
  return `${Number.isInteger(p) ? p : p.toFixed(1)}%`;
}

/** The one-line summary: the three things that most often differ between two quotes. */
export function basisSummary(b: QuotationBasis): string {
  const parts: string[] = [];
  parts.push(
    b.costIndex.year
      ? `${b.costIndex.name} ${b.costIndex.value} (${b.costIndex.year})`
      : `${b.costIndex.name} ${b.costIndex.value}`,
  );
  if (b.discountRate !== undefined) {
    parts.push(
      b.discountRateKind === 'capital-charge'
        ? `${pct(b.discountRate)} capital charge`
        : `${pct(b.discountRate)} IRR`,
    );
  }
  if (b.projectLife) parts.push(`${b.projectLife[0]}–${b.projectLife[1]}`);
  parts.push(b.region.kind === 'declared' ? b.region.jurisdiction : 'no regional basis');
  return parts.join(' · ');
}

/**
 * One line, beside a price.
 *
 * Not a footnote and not a tooltip: a reader comparing two numbers has to be
 * able to see that they are on different bases without hovering anything.
 */
export function BasisLine({ basis, className }: { basis: QuotationBasis; className?: string }) {
  return (
    <div className={cx('text-caption text-ink-soft', className)}>
      <span className="font-num">{basisSummary(basis)}</span>
    </div>
  );
}

/**
 * The full declaration.
 *
 * Collapsed by default, following `UpstreamNote`: the summary line carries the
 * argument and the panel carries the detail for anyone who wants it. What is
 * NOT collapsible is the pair of declared gaps — a region nobody stated and an
 * accuracy class nobody assigned sit above the fold, because they are the two
 * things a reader is most likely to assume were handled.
 */
export function BasisPanel({ basis, className }: { basis: QuotationBasis; className?: string }) {
  const [open, setOpen] = useState(false);

  const rows: { label: string; value: string; note?: string }[] = [
    {
      label: 'Cost index',
      value: basis.costIndex.year
        ? `${basis.costIndex.name} ${basis.costIndex.value} — ${basis.costIndex.year} basis`
        : `${basis.costIndex.name} ${basis.costIndex.value} — set directly`,
      note: basis.costIndex.note,
    },
    {
      label: basis.discountRateKind === 'capital-charge' ? 'Capital charge' : 'Discount rate',
      value: pct(basis.discountRate),
      note:
        basis.discountRateKind === 'capital-charge'
          ? 'A flat charge on installed capital, not an internal rate of return solved against a cash flow. The two are different claims.'
          : 'The price is solved to drive net present value to zero at this rate.',
    },
    ...(basis.projectLife
      ? [
          {
            label: 'Project life',
            value: `${basis.projectLife[0]}–${basis.projectLife[1]}`,
            note: `${basis.projectLife[1] - basis.projectLife[0]} years including construction.`,
          },
        ]
      : []),
    ...(basis.incomeTax !== undefined
      ? [{ label: 'Income tax', value: pct(basis.incomeTax), note: basis.taxNote }]
      : []),
    ...(basis.operatingDays !== undefined
      ? [
          {
            label: 'Operating days',
            value: `${basis.operatingDays} per year`,
            note: 'Availability. Everything annual on this screen is scaled by it.',
          },
        ]
      : []),
    {
      label: 'Currency',
      value: basis.currency ?? 'USD',
      note: basis.fx
        ? `${basis.fx.pair} fixed at ${basis.fx.rate}${basis.fx.asOf ? ` as of ${basis.fx.asOf}` : ''}. ${basis.fx.note}`
        : 'No conversion is performed — which is a different statement from a rate of 1.0.',
    },
  ];

  return (
    <div className={className}>
      {/* The two declared gaps, above the fold. */}
      <div className="grid gap-2 sm:grid-cols-2">
        <div
          className={cx(
            'card p-3',
            basis.region.kind === 'undeclared' && 'border-dashed border-signal-warn/50',
          )}
        >
          <div className="flex items-baseline gap-1.5">
            <MapPin size={12} className="text-ink-soft shrink-0 translate-y-[1px]" aria-hidden />
            <span className="text-caption uppercase tracking-wide text-ink-soft">
              Regional basis
            </span>
          </div>
          {basis.region.kind === 'declared' ? (
            <>
              <div className="text-body mt-1">
                {basis.region.locality ? `${basis.region.locality}, ` : ''}
                <span className="font-num">{basis.region.jurisdiction}</span>
                {basis.region.locationFactor !== undefined && (
                  <span className="text-ink-soft">
                    {' '}
                    · location factor{' '}
                    <span className="font-num">{basis.region.locationFactor}</span>
                  </span>
                )}
              </div>
              <div className="text-caption text-ink-soft mt-1">{basis.region.source}</div>
            </>
          ) : (
            <>
              <div className="font-num text-page-title leading-none mt-1 text-ink-soft" aria-hidden>
                —
              </div>
              <div className="text-caption text-ink-soft mt-1.5">{basis.region.why}</div>
            </>
          )}
        </div>

        <div
          className={cx(
            'card p-3',
            basis.accuracy.kind === 'unstated' && 'border-dashed border-signal-warn/50',
          )}
        >
          <div className="text-caption uppercase tracking-wide text-ink-soft">Accuracy class</div>
          {basis.accuracy.kind === 'class' ? (
            <>
              <div className="text-body mt-1 font-num">{basis.accuracy.label}</div>
              <div className="text-caption text-ink-soft mt-1">
                The band this estimate is entitled to, drawn rather than footnoted.
              </div>
            </>
          ) : (
            <>
              <div className="font-num text-page-title leading-none mt-1 text-ink-soft" aria-hidden>
                —
              </div>
              <div className="text-caption text-ink-soft mt-1.5">{basis.accuracy.why}</div>
            </>
          )}
        </div>
      </div>

      <button
        className="mt-2 inline-flex items-center gap-1 text-caption text-ink-soft hover:text-ink motion-colors"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <ChevronRight
          size={12}
          className={cx('transition-transform', open && 'rotate-90')}
          aria-hidden
        />
        {open ? 'Hide the rest of the basis' : `The rest of the basis — ${basisSummary(basis)}`}
      </button>

      {open && (
        <div className="mt-2 card p-3">
          <dl className="divide-y divide-line">
            {rows.map((r) => (
              <div key={r.label} className="py-2 grid gap-x-4 sm:grid-cols-[10rem_1fr]">
                <dt className="text-caption uppercase tracking-wide text-ink-soft">{r.label}</dt>
                <dd>
                  <div className="text-body font-num">{r.value}</div>
                  {r.note && (
                    <div className="text-caption text-ink-soft mt-0.5 max-w-prose">{r.note}</div>
                  )}
                </dd>
              </div>
            ))}
          </dl>

          <div className="mt-3 pt-3 border-t border-line">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
              What this price does not include
            </div>
            <ul className="space-y-1 max-w-prose">
              {basis.excludes.map((e) => (
                <li key={e} className="text-caption text-ink-soft flex gap-1.5">
                  <span className="text-ink-soft/60 shrink-0">·</span>
                  <span>{e}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
