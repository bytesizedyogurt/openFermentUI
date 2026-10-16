// The figure grammar's one table (OF-BLD-014 E.8, rule 2).
//
// Provenance decides a mark's shape, fill and dash, so a chart reads the same
// in greyscale and a reader can tell a measurement from a computed limit from
// a market guess without a legend. `ENCODING` is a Record over every
// provenance: a new class with no mark fails the type check, and
// `pnpm check:figures` fails when two classes share a mark or a class that
// is never evidence is drawn solid.
import type { Provenance } from '@/data/types';

export type PointShape = 'diamond' | 'circle' | 'square' | 'triangle';
export type Dash = 'solid' | 'dotted' | 'long' | 'short';

export interface MarkStyle {
  /** The point a record of this provenance draws as. */
  point: {
    shape: PointShape;
    filled: boolean;
    /** A ring drawn round the point (gold). */
    ring: boolean;
    /** The outline's dash; solid for every class that is evidence. */
    outline: 'solid' | 'dashed';
  };
  /** A line or band of this provenance. */
  line: { dash: Dash; weight: 'heavy' | 'normal' | 'thin' };
  /** Amber, for the modeled class alone. */
  amber: boolean;
  /** In words, for the legend and the table twin. */
  words: string;
}

export const ENCODING: Record<Provenance, MarkStyle> = {
  measured: {
    point: { shape: 'diamond', filled: true, ring: false, outline: 'solid' },
    line: { dash: 'solid', weight: 'heavy' },
    amber: false,
    words: 'filled diamond; heavy solid line',
  },
  gold: {
    point: { shape: 'circle', filled: true, ring: true, outline: 'solid' },
    line: { dash: 'solid', weight: 'normal' },
    amber: false,
    words: 'filled circle inside a ring; solid line',
  },
  verified: {
    point: { shape: 'circle', filled: true, ring: false, outline: 'solid' },
    line: { dash: 'solid', weight: 'normal' },
    amber: false,
    words: 'filled circle; solid line',
  },
  curated: {
    point: { shape: 'square', filled: true, ring: false, outline: 'solid' },
    line: { dash: 'solid', weight: 'normal' },
    amber: false,
    words: 'filled square; solid line',
  },
  unverified: {
    point: { shape: 'circle', filled: false, ring: false, outline: 'solid' },
    line: { dash: 'solid', weight: 'thin' },
    amber: false,
    words: 'hollow circle; thin solid line',
  },
  computed: {
    point: { shape: 'square', filled: false, ring: false, outline: 'solid' },
    line: { dash: 'dotted', weight: 'normal' },
    amber: false,
    words: 'hollow square; dotted line',
  },
  user: {
    point: { shape: 'triangle', filled: false, ring: false, outline: 'solid' },
    line: { dash: 'solid', weight: 'thin' },
    amber: false,
    words: 'hollow triangle; thin solid line',
  },
  'industry-estimate': {
    point: { shape: 'diamond', filled: false, ring: false, outline: 'dashed' },
    line: { dash: 'long', weight: 'normal' },
    amber: false,
    words: 'hollow diamond, dashed outline; long dashes',
  },
  demo: {
    point: { shape: 'circle', filled: false, ring: false, outline: 'dashed' },
    line: { dash: 'short', weight: 'normal' },
    amber: true,
    words: 'hollow circle, dashed outline, amber; short dashes, amber',
  },
};

/** The two classes that are never evidence (E.8 rule 2). */
export const NEVER_EVIDENCE: Provenance[] = ['industry-estimate', 'demo'];

/** What makes a point distinct; two provenances may never share one. */
export function pointKey(p: Provenance): string {
  const m = ENCODING[p].point;
  return `${m.shape}|${m.filled ? 'filled' : 'hollow'}|${m.ring ? 'ring' : 'plain'}|${m.outline}`;
}

export const DASH_ARRAY: Record<Dash, string | undefined> = {
  solid: undefined,
  dotted: '1.5 3',
  long: '8 4',
  short: '3 3',
};

export const LINE_WIDTH: Record<MarkStyle['line']['weight'], number> = { heavy: 2.5, normal: 1.5, thin: 1 };

/** Ink for data marks: the text colour, or amber for the modeled class.
 * The accent green is never a data series (E.8 rule 5). */
export function markColor(p: Provenance): string {
  return ENCODING[p].amber ? 'rgb(var(--signal-warn))' : 'currentColor';
}
