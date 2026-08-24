// Freeform in, structured out (OF-BLD-006 §4.3).
//
// The operator never fills a form. They describe what they see, and this
// decides whether what they said lands in the measurement schema or is kept as
// an observation.
//
// THE ASYMMETRY IS THE DESIGN. A schema-first capture would discard exactly
// the observation worth having, because an unexpected result has no field
// waiting for it — by definition. So matching is deliberately conservative:
// when in doubt this returns null and the text is kept verbatim as an
// Observation. A false negative costs a person one reclassification later; a
// false positive silently writes a number into a slot it does not belong in
// and the reconciliation is quietly wrong.
import type { Measure } from '@/data/types';

export interface CaptureMatch {
  measureId: string;
  value: number;
  unit: string;
  /** Which words in the raw text produced the match, for the read-back. */
  matchedOn: string;
}

/** Strip the noise a person types or dictates without meaning anything by it. */
function normalise(text: string): string {
  return text
    .toLowerCase()
    .replace(/[,]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Unit spellings a bench actually uses, mapped to the schema's own notation.
 * Deliberately small: this is not a unit engine — Primer is — it only has to
 * recognise the handful of forms a measurement schema declares.
 */
const UNIT_FORMS: Record<string, string[]> = {
  'g/L': ['g/l', 'g per l', 'grams per litre', 'grams per liter', 'gpl'],
  '%': ['%', 'percent', 'per cent', 'pct'],
  'C': ['c', '°c', 'degrees c', 'deg c', 'celsius'],
  'OD600': ['od600', 'od 600', 'od'],
  'g': ['g', 'grams', 'gram'],
  'EU/mg': ['eu/mg', 'eu per mg'],
  'pg/U': ['pg/u', 'pg per u'],
  'U/mg': ['u/mg', 'u per mg'],
  'IMCU/mg': ['imcu/mg', 'imcu per mg'],
  'candidates': ['candidates', 'candidate', 'hits'],
  'months': ['months', 'month'],
  'USD': ['usd', 'dollars', '$'],
  'ratio': ['ratio', 'x', 'fold'],
  'x sucrose': ['x sucrose', 'times sucrose'],
  'configurations': ['configurations', 'configs'],
};

function unitAliases(unit: string): string[] {
  // Longest first: "grams per litre" must win over the bare "g" it contains.
  return (UNIT_FORMS[unit] ?? [unit.toLowerCase()]).slice().sort((a, b) => b.length - a.length);
}

const escapeRe = (t: string) => t.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');

/**
 * Find a token as a WORD, not as a substring.
 *
 * Naive `includes` is how "g" matches inside "logs" and turns "smelled off
 * around 3am" into a purified mass of 3 grams. Boundaries are hand-rolled
 * rather than \b because most of these tokens are not word characters at all —
 * '%', 'g/L', '$' — and \b behaves differently on each side of them.
 */
function findToken(text: string, token: string): { start: number; end: number } | null {
  const re = new RegExp(`(?<![a-z0-9])${escapeRe(token)}(?![a-z0-9])`);
  const m = text.match(re);
  if (!m || m.index === undefined) return null;
  return { start: m.index, end: m.index + m[0].length };
}

/**
 * Significant words from a measure's label, used to tell two measures apart
 * when both share a unit. "Titre at harvest" and "Overall recovery" are both
 * numbers; only the words separate them.
 */
function labelTokens(label: string): string[] {
  const STOP = new Set(['at', 'the', 'of', 'a', 'an', 'in', 'on', 'after', 'per', 'and', 'to']);
  return normalise(label)
    .split(' ')
    .filter((w) => w.length > 2 && !STOP.has(w));
}

/**
 * Try to place a spoken or typed line into the schema.
 *
 * Requires BOTH a number and corroboration — either the declared unit or a
 * word from the measure's label. A bare number matches nothing, because "it
 * came out at about four" could be any row in the schema and guessing which
 * is how a reconciliation ends up comparing the wrong things.
 */
export function matchToSchema(raw: string, schema: Measure[]): CaptureMatch | null {
  const text = normalise(raw);
  const numbers = [...text.matchAll(/(-?\d+(?:\.\d+)?)/g)];
  if (numbers.length === 0) return null;

  let best: (CaptureMatch & { score: number }) | null = null;

  for (const measure of schema) {
    const unitSpan = unitAliases(measure.unit)
      .map((a) => ({ a, span: findToken(text, a) }))
      .find((x) => x.span !== null);
    const tokenSpans = labelTokens(measure.label)
      .map((t) => ({ t, span: findToken(text, t) }))
      .filter((x) => x.span !== null);
    if (!unitSpan && tokenSpans.length === 0) continue;

    // Numbers living INSIDE whatever corroborated the match are part of the
    // token, not a reading: "OD600 of 82" must be 82, never 600.
    const claimed = [unitSpan?.span, ...tokenSpans.map((x) => x.span)].filter(
      (sp): sp is { start: number; end: number } => sp !== null && sp !== undefined,
    );
    const usable = numbers.filter((n) => {
      const i = n.index ?? 0;
      return !claimed.some((sp) => i >= sp.start && i < sp.end);
    });
    if (usable.length === 0) continue;

    // Of what is left, take the number nearest the corroborating token.
    const anchor = (unitSpan?.span ?? tokenSpans[0].span)!.start;
    let chosen = usable[0];
    let bestDistance = Infinity;
    for (const n of usable) {
      const d = Math.abs((n.index ?? 0) - anchor);
      if (d < bestDistance) {
        bestDistance = d;
        chosen = n;
      }
    }

    const value = Number(chosen[1]);
    if (!isFinite(value)) continue;
    const unitHit = unitSpan?.a;
    const tokenHits = tokenSpans.map((x) => x.t);

    // A declared unit is stronger corroboration than a label word, and both
    // together are stronger still.
    const score = (unitHit ? 2 : 0) + tokenHits.length;
    if (!best || score > best.score) {
      best = {
        measureId: measure.id,
        value,
        unit: measure.unit,
        matchedOn: [unitHit, ...tokenHits].filter(Boolean).join(', '),
        score,
      };
    }
  }

  if (!best) return null;
  const { score, ...match } = best;
  void score;
  return match;
}

/**
 * Whether a line is worth a read-back beat.
 *
 * Only numbers entering the schema. Confirm everything and the screen is
 * unusable at the bench; confirm nothing and "four two" is 4.2 or 42 and the
 * failure is silent. One extra tap on the handful of values that matter.
 */
export function needsReadBack(match: CaptureMatch | null): boolean {
  return match !== null;
}

/**
 * The read-back sentence. Says the number the way a person would check it,
 * not the way a parser stored it.
 */
export function readBackText(match: CaptureMatch): string {
  return `${match.value} ${match.unit}`;
}
