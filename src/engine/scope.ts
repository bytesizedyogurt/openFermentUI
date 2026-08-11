// Patent scope arithmetic (OF-FE-003 §5.4).
//
// `anticipates` is the genuinely novel capability here: a Ledger record that
// predates a claim's priority date and falls inside its bounds is prior art
// against that claim. Nobody searches prior art with a structured parameter
// database, and the reason they cannot is that claim scope and literature
// values are never expressed in the same units. Parchment's whole value is
// putting them in one ontology.
//
// Pure, and deliberately conservative: every function here returns false when
// it does not have what it needs, rather than guessing in the direction that
// would produce a more interesting screen.
import type { ClaimScope, ExtractionRecord, Patent } from '@/data/types';
import { asNumber, convert } from '@/engine/units';

function satisfies(
  value: number,
  bound: ClaimScope['bounds'][number],
): boolean {
  const v = bound.value;
  switch (bound.op) {
    case '<':
      return typeof v === 'number' && value < v;
    case '<=':
      return typeof v === 'number' && value <= v;
    case '>':
      return typeof v === 'number' && value > v;
    case '>=':
      return typeof v === 'number' && value >= v;
    case 'in':
      return Array.isArray(v) && value >= v[0] && value <= v[1];
    case 'eq':
      return typeof v === 'number' && value === v;
    default:
      return false;
  }
}

/**
 * Does a design configuration fall inside a claim? A claim with no parsed
 * bounds cannot answer, and says so by returning false — an unparsed claim is
 * not a claim that covers nothing.
 */
export function inScope(
  config: Record<string, string | number>,
  claim: ClaimScope,
): boolean {
  if (claim.bounds.length === 0) return false;
  return claim.bounds.every((b) => {
    const raw = config[b.field];
    if (raw === undefined) return false;
    if (typeof raw === 'string') return b.op === 'eq' && raw === b.value;
    return satisfies(raw, b);
  });
}

/**
 * Does a record anticipate a claim — published before its priority date, and
 * inside its bounds?
 *
 * Requires a real date on both sides and at least one parsed bound. Anything
 * less returns false: announcing prior art on the strength of an unparsed claim
 * would be the most damaging thing this module could get wrong.
 */
export function anticipates(
  record: ExtractionRecord,
  patent: Patent,
  recordDate?: string,
): boolean {
  if (!recordDate || !patent.priorityDate) return false;
  if (!(recordDate < patent.priorityDate)) return false;

  const n = asNumber(record.value);
  if (n === null) return false;

  return patent.claims.some((claim) =>
    claim.bounds.some((b) => {
      if (b.field !== record.field) return false;
      let v = n;
      if (b.unit && b.unit !== record.unit) {
        try {
          v = convert(n, record.unit, b.unit);
        } catch {
          return false;
        }
      }
      return satisfies(v, b);
    }),
  );
}

/** Claims carrying no parsed bounds — the work Parchment still owes. */
export function unparsedClaims(patents: Patent[]): { patent: Patent; claim: ClaimScope }[] {
  const out: { patent: Patent; claim: ClaimScope }[] = [];
  for (const p of patents) {
    for (const c of p.claims) {
      if (c.bounds.length === 0 || c.parseUncertain) out.push({ patent: p, claim: c });
    }
  }
  return out;
}
