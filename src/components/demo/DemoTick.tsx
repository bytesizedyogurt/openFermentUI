// The demo pool's tick — same two axes as the corpus one, different vocabulary.
//
// `src/components/Provenance.tsx` establishes the house rule and this file
// obeys it rather than restating it: HUE is the verification axis (how far has
// this been checked) and GEOMETRY is the evidence axis (what kind of thing
// produced it). One axis owning colour is what makes the ambient texture
// readable at all, and both axes stay apart in greyscale and to a deuteranope.
//
// WHY A SECOND FILE. The corpus tick is typed on the GENERATED `Provenance`
// (eight members) and `EvidenceClass` (five). The demo pool has eleven
// provenance values and nine source types, and they are not a superset — the
// demo pool has no `gold`, and the corpus has no `deposited`. A single
// component typed on the union of both would accept combinations neither pool
// can produce. Two components, one rule.
//
// The CSS classes are SHARED wherever the geometry is the same thing: a patent
// example gets `tick-ev-patent` here exactly as a patent-class record does
// there. Only the two geometries the corpus has no equivalent for
// (`defensive-publication`, `trade-statistic`) are new, and they live beside
// the others in `styles.css` rather than in a demo stylesheet.
import type { ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

import type { Provenance, SourceType, HoldReason } from '@/data/demo/types';
import { cx } from '@/components/ui';

/**
 * Hue by verification state.
 *
 * The three the corpus does not have:
 *  - `computed` reuses the info hue, because a derived quantity is a statement
 *    about other quantities rather than about the world;
 *  - `deposited` takes the gold slot, because a Chapter bench measurement under
 *    a Common Seal is the strongest provenance this pool can carry;
 *  - `excursion` takes the warn hue — measured, but the run deviated, so it is
 *    a real number that must not enter a statistic.
 */
const HUE: Record<Provenance, { tick: string; label: string }> = {
  gold: { tick: 'tick-gold', label: 'Gold set' },
  verified: { tick: 'tick-verified', label: 'Verified against source' },
  curated: { tick: 'tick-curated', label: 'Curated · pending source check' },
  unverified: { tick: 'tick-unverified', label: 'Extracted · unverified' },
  user: { tick: 'tick-user', label: 'User-entered' },
  'industry-estimate': { tick: 'tick-industry-estimate', label: 'Industry estimate · not evidence' },
  demo: { tick: 'tick-demo', label: 'Modeled · not measured' },
  computed: { tick: 'tick-user', label: 'Computed from other Accessions' },
  deposited: { tick: 'tick-gold', label: 'Bench deposit · Common Seal' },
  excursion: { tick: 'tick-demo', label: 'Measured, but the run was flagged' },
  unsourced: { tick: 'tick-unsourced', label: 'UNSOURCED — no provenance record' },
};

/**
 * Geometry by source type (OF-DEMO-002 §4.1).
 *
 * `journal` is the baseline and takes no class, so every existing screen reads
 * unchanged. A patent example and a journal measurement can be the same
 * verification state and are completely different claims, which is exactly why
 * this axis exists.
 */
const GEOMETRY: Record<SourceType, string> = {
  journal: '',
  'patent-example': 'tick-ev-patent',
  'patent-claim': 'tick-ev-patent',
  'defensive-publication': 'tick-ev-defensive',
  thesis: '',
  'bench-deposit': 'tick-ev-experiment',
  'trade-statistic': 'tick-ev-trade',
  'vendor-datasheet': 'tick-ev-trade',
  computed: 'tick-ev-computed',
};

const SOURCE_LABEL: Record<SourceType, string> = {
  journal: 'journal',
  'patent-example': 'patent working example',
  'patent-claim': 'patent claim',
  'defensive-publication': 'defensive publication',
  thesis: 'thesis',
  'bench-deposit': 'bench deposit',
  'trade-statistic': 'trade statistic',
  'vendor-datasheet': 'vendor datasheet',
  computed: 'computed',
};

export const HOLD_LABEL: Record<HoldReason, string> = {
  recitation: 'recites another study’s measurement',
  'industry-estimate': 'vendor or market claim, not evidence',
  'excursion-flagged': 'the run behind it deviated',
  superseded: 'a correction replaced it',
  'upper-reported-case': 'best observed, not expected',
  'unit-ambiguous': 'normalisation could not be closed',
};

export function demoTickClass(p: Provenance, st: SourceType): string {
  return cx('tick-cell', HUE[p].tick, GEOMETRY[st]);
}

/** The sentence a tick's title attribute carries. Both axes, always both. */
export function demoTickTitle(p: Provenance, st: SourceType, hold?: HoldReason): string {
  const base = `${HUE[p].label} · ${SOURCE_LABEL[st]}`;
  return hold ? `${base} — HELD: ${HOLD_LABEL[hold]}` : base;
}

/**
 * Ambient form: the 3px notched left border, carrying both axes.
 *
 * `hold` is not a third axis — a held Accession keeps its own hue and geometry
 * and is dimmed instead, because holding is a statement about what a value may
 * be USED for, not about what it is. A reader must still be able to see that a
 * held record was a verified patent example.
 */
export function DemoTick({
  p,
  st,
  hold,
  children,
  className,
}: {
  p: Provenance;
  st: SourceType;
  hold?: HoldReason;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cx(demoTickClass(p, st), hold && 'held', className)}
      title={demoTickTitle(p, st, hold)}
    >
      {p === 'unsourced' && (
        <AlertTriangle className="inline w-3 h-3 mr-1 text-signal-error" aria-hidden />
      )}
      {children}
    </span>
  );
}

/**
 * The legend. Rendered wherever a screen uses more than two source types,
 * because the geometry is only self-explanatory once.
 */
export function DemoTickLegend({ types }: { types?: SourceType[] }) {
  const shown = types ?? (['journal', 'patent-example', 'defensive-publication', 'computed', 'bench-deposit', 'trade-statistic'] as SourceType[]);
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-ink-soft">
      {shown.map((st) => (
        <span key={st} className="inline-flex items-center gap-1.5">
          <span className={cx('tick-cell', 'tick-verified', GEOMETRY[st], 'w-3 h-4 inline-block')} aria-hidden />
          {SOURCE_LABEL[st]}
        </span>
      ))}
    </div>
  );
}

export { SOURCE_LABEL };
