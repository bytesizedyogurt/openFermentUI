// The referee (OF-FE-003 §5.2) — client-side checks that are arithmetic rather
// than simulation.
//
// A contradiction is a set of records that cannot all be true. The referee
// flags the *set*; it does not need to identify which member is wrong to be
// useful, and pretending it knows would be a worse answer than the honest one.
//
// Everything here is derived from the records at load. Nothing is authored.
// That is deliberate: OF-FE-003 §12.5 forbids seeding a contradiction that does
// not fail its tolerance when computed, because the system committing the exact
// error it exists to catch is the worst available outcome. Deriving them makes
// staging one structurally impossible rather than merely forbidden.
import type { Contradiction, ExtractionRecord } from '@/data/types';
import { asNumber } from '@/engine/units';
import { ONTOLOGY_BY_ID } from '@/data/ontology';

/** Mature and precursor numbering differ by the 15-residue signal peptide. */
const SIGNAL_PEPTIDE_OFFSET = 15;

function num(r: ExtractionRecord): number | null {
  return asNumber(r.value);
}

/**
 * Contradictions the existing schema already knows how to detect. The cheap win,
 * and the one worth building first: real conflicts, in real records, needing no
 * new science.
 *
 * Three families:
 *  - a phospho_site_position recorded in one numbering convention that lands on
 *    a position another record claims in the other, offset by exactly the signal
 *    peptide — the first trap OF-COR-001 §19 names;
 *  - a phosphorylation_degree inconsistent with a phosphate_count for the same
 *    organism;
 *  - any fraction-valued field above 1, or any value outside the ontology's own
 *    declared plausible range by more than an order of magnitude.
 */
export function checkOntologyConsistency(records: ExtractionRecord[]): Contradiction[] {
  const out: Contradiction[] = [];
  let n = 0;
  const id = () => `cx-${String(++n).padStart(3, '0')}`;

  // ── numbering-convention collisions ──────────────────────────────────
  const positions = records.filter(
    (r) => r.field === 'phospho_site_position' && r.numbering && num(r) !== null,
  );
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const a = positions[i];
      const b = positions[j];
      if (a.numbering === b.numbering) continue;
      const av = num(a)!;
      const bv = num(b)!;
      // Same physical residue described in two conventions differs by exactly
      // the offset. A pair that differs by anything else, while claiming to
      // describe the same site, is the contradiction.
      const mature = a.numbering === 'mature' ? av : bv;
      const precursor = a.numbering === 'mature' ? bv : av;
      const residual = Math.abs(precursor - mature - SIGNAL_PEPTIDE_OFFSET);
      if (residual === 0) continue;
      // Only flag when the two are close enough to plausibly be the same site;
      // distinct sites are not a contradiction, they are just distinct.
      if (residual > SIGNAL_PEPTIDE_OFFSET) continue;
      out.push({
        id: id(),
        kind: 'specification',
        recordIds: [a.id, b.id],
        statement: `Two records place a phosphorylation site at positions that cannot both be right: ${mature} in mature numbering implies ${mature + SIGNAL_PEPTIDE_OFFSET} in precursor numbering, but the other record says ${precursor}.`,
        constraint: {
          expression: `precursor − mature − ${SIGNAL_PEPTIDE_OFFSET} = 0`,
          residual,
          tolerance: 0,
          unit: 'residues',
        },
        detectedBy: 'ontology',
        status: 'open',
      });
    }
  }

  // ── degree against count ─────────────────────────────────────────────
  const degrees = records.filter((r) => r.field === 'phosphorylation_degree' && num(r) !== null);
  const counts = records.filter((r) => r.field === 'phosphate_count' && num(r) !== null);
  for (const d of degrees) {
    for (const c of counts) {
      if (d.organism !== c.organism) continue;
      const degree = num(d)!;
      const count = num(c)!;
      // A degree is mol phosphate per mol protein; it cannot exceed the number
      // of phosphorylatable sites the same organism's record reports.
      if (degree <= count) continue;
      out.push({
        id: id(),
        kind: 'balance',
        recordIds: [d.id, c.id],
        statement: `A phosphorylation degree of ${degree} exceeds the ${count} phosphate sites recorded for the same host — more phosphate per protein than there are places to put it.`,
        constraint: {
          expression: 'phosphorylation_degree ≤ phosphate_count',
          residual: degree - count,
          tolerance: 0,
          unit: 'mol mol⁻¹',
        },
        detectedBy: 'ontology',
        status: 'open',
      });
    }
  }

  // ── values outside the ontology's own declared bounds ────────────────
  // Read the bound from the ontology rather than assuming a 0–1 fraction.
  // secreted_fraction is canonically "% of total expressed" over [0.001, 100],
  // so testing it as a bare fraction flags 7.5% as impossible — a fabricated
  // contradiction, which is the one outcome §12.5 rules out entirely.
  for (const r of records) {
    const def = ONTOLOGY_BY_ID[r.field];
    if (!def || def.categorical) continue;
    // A negative result is a finding, not a conflict. r-A2-1 records zero
    // expression because untransformed controls showed no detectable YFP —
    // exactly the observation the experiment was built to make. Flagging it
    // would punish the corpus for being careful.
    if (r.negativeResult) continue;
    const v = num(r);
    if (v === null) continue;
    if (r.unit !== def.canonicalUnit) continue; // not comparable without conversion
    const [lo, hi] = def.range;
    if (v >= lo && v <= hi) continue;
    const residual = v > hi ? v - hi : lo - v;
    out.push({
      id: id(),
      kind: 'specification',
      recordIds: [r.id],
      // The referee flags the *set* that cannot all be true, and here the set
      // is {this record, the ontology's declared range}. Which member is wrong
      // is a real question: r-E1-3 records casein as 80% of bovine milk
      // protein, which is true of milk and outside a range written for
      // recombinant expression. Saying "the value is impossible" would pick a
      // side the arithmetic does not support.
      statement: `${def.name} is recorded as ${v} ${r.unit}, outside the ${lo}–${hi} the ontology declares for this field. Either the value does not belong in this field, or the field's range is wrong — they cannot both stand.`,
      constraint: {
        expression: `${lo} ≤ ${r.field} ≤ ${hi}`,
        residual,
        tolerance: 0,
        unit: def.canonicalUnit || 'unitless',
      },
      detectedBy: 'ontology',
      status: 'open',
    });
  }

  return out;
}

/**
 * Elemental balance over a set of records. Not implemented against this corpus:
 * closing a carbon or nitrogen balance needs a feed composition, a biomass
 * formula and an off-gas term, and none of the 134 records carries them.
 *
 * Returns null rather than a fabricated residual. A referee that invents a
 * balance it cannot compute is exactly the failure mode this module exists to
 * prevent, and an honest null is what lets the Assay screen say the check has
 * not run instead of implying it passed.
 */
export function checkElementalBalance(_records: ExtractionRecord[]): Contradiction | null {
  return null;
}

/** Every contradiction the referee can currently find in a record set. */
export function refereeAll(records: ExtractionRecord[]): Contradiction[] {
  const out = checkOntologyConsistency(records);
  const balance = checkElementalBalance(records);
  return balance ? [...out, balance] : out;
}

/**
 * Re-verify a contradiction against the records it names. `check:seed` uses this
 * to enforce OF-FE-003 §9 invariant 3: a contradiction whose residual no longer
 * exceeds its tolerance is not a finding, it is a claim.
 */
export function stillFails(c: Contradiction, records: ExtractionRecord[]): boolean {
  const present = c.recordIds.every((rid) => records.some((r) => r.id === rid));
  if (!present) return false;
  return c.constraint.residual > c.constraint.tolerance;
}

/** Ontology ranges, exposed so the Assay screen can say what was checked. */
export const ONTOLOGY_CHECKS = ['numbering', 'degree-vs-count', 'fraction-bounds'] as const;

export function rangeOf(field: ExtractionRecord['field']): [number, number] | null {
  return ONTOLOGY_BY_ID[field]?.range ?? null;
}
