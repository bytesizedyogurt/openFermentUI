// `AccessionValue` — the load-bearing primitive (OF-DEMO-002 §4.3).
//
// It NEVER renders the normalised value alone. OF-DEMO-001 §2.4 calls this the
// single most persuasive detail in the suite and it is unglamorous on purpose:
//
//     2.4 g L⁻¹ h⁻¹   (orig. 0.10 g gDCW⁻¹ h⁻¹ @ 24 g L⁻¹ DCW)
//
// A normalised number on its own is a claim the reader has to take on trust. A
// normalised number beside the thing the source actually said is a claim the
// reader can check, and the auxiliary that closed the conversion is itself an
// Accession with its own id — which is what makes the provenance graph
// recursive rather than decorative.
//
// The component is deliberately small and has one rule: if it cannot show the
// original, it does not render the value.
import { useMemo } from 'react';

import type { Accession } from '@/data/demo/types';
import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import { normalise } from '@/lib/demo';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { DemoTick } from './DemoTick';

const round = (v: number, d = 4) => {
  const r = +v.toFixed(d);
  return Object.is(r, -0) ? 0 : r;
};

/** `0.10 g gDCW⁻¹ h⁻¹` — what the source said, verbatim in its own units. */
export function reportedText(acc: Accession): string {
  const q = acc.reported;
  const base = q.range
    ? `${q.range.low}–${q.range.high}`
    : `${q.value}`;
  return `${base}${q.unit ? ` ${q.unit}` : ''}`;
}

/**
 * `@ 24 g L⁻¹ DCW` — the auxiliary quantities the normalisation consumed.
 *
 * Each is an Accession, so each is shown in ITS normalised unit and can be
 * clicked through. An auxiliary that does not resolve is rendered as a visible
 * defect rather than dropped: a conversion resting on a missing quantity is
 * exactly the thing a reader must be told about.
 */
export function auxiliaryText(acc: Accession): string {
  const ids = acc.derivation.usingAccessionIds;
  if (!ids.length) return '';
  return ids
    .map((id) => {
      const aux = ACCESSION_BY_ID[id];
      return aux ? `${aux.normalized.value} ${aux.normalized.unit}` : `«${id} missing»`;
    })
    .join(', ');
}

/** The whole display string, for places that need text rather than nodes. */
export function accessionText(acc: Accession): string {
  const v = round(normalise(acc, ACCESSION_BY_ID));
  const aux = auxiliaryText(acc);
  const orig = reportedText(acc);
  const sameUnits = acc.reported.unit === acc.normalized.unit && !aux;
  return sameUnits
    ? `${v}${acc.normalized.unit ? ` ${acc.normalized.unit}` : ''}`
    : `${v}${acc.normalized.unit ? ` ${acc.normalized.unit}` : ''} (orig. ${orig}${aux ? ` @ ${aux}` : ''})`;
}

export function AccessionValue({
  id,
  className,
  /** Suppress the link when the value is already inside the Accession page. */
  link = true,
  /** Larger form for the top of an Accession page. */
  size = 'inline',
}: {
  id: string;
  className?: string;
  link?: boolean;
  size?: 'inline' | 'lead';
}) {
  const acc = ACCESSION_BY_ID[id];

  const body = useMemo(() => {
    if (!acc) return null;
    const v = round(normalise(acc, ACCESSION_BY_ID));
    const aux = auxiliaryText(acc);
    const orig = reportedText(acc);
    // The one case where the original is not repeated: it IS the normalised
    // form, in the same units, with nothing consumed to get there. Repeating it
    // would be noise, and §2.4's rule is about never hiding a conversion.
    const identical = acc.reported.unit === acc.normalized.unit && !aux && acc.reported.value === v;
    return { v, aux, orig, identical };
  }, [acc]);

  if (!acc || !body) {
    // A missing Accession renders as a fault, not as blank. Rule 1 says no
    // quantity appears without provenance; a dangling id is that rule breaking,
    // and it should look like it.
    return (
      <span className="font-num text-signal-error" title={`No Accession ${id} in the pool`}>
        ⚠ {id}
      </span>
    );
  }

  const inner = (
    <span className={cx('font-num', size === 'lead' && 'text-page-title font-semibold')}>
      {body.v}
      {acc.normalized.unit ? ` ${acc.normalized.unit}` : ''}
      {!body.identical && (
        <span
          className={cx(
            'text-ink-soft ml-1.5',
            size === 'lead' ? 'text-body block mt-1 ml-0' : 'text-caption',
          )}
        >
          (orig. {body.orig}
          {body.aux ? ` @ ${body.aux}` : ''})
        </span>
      )}
    </span>
  );

  const titled = (
    <DemoTick p={acc.provenance} st={acc.sourceType} hold={acc.hold} className="pl-2">
      {inner}
    </DemoTick>
  );

  if (!link) return <span className={className}>{titled}</span>;
  return (
    <a
      href={href(`/repo/a/${acc.id}`)}
      className={cx('hover:text-accent', className)}
      title={`${acc.id} — ${acc.derivation.note}`}
    >
      {titled}
    </a>
  );
}
