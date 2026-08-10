// Extractor runs against the gold set (OF-DES-001 §8.8).
//
// EMPTY, AND THAT IS THE POINT.
//
// The synthetic corpus shipped three seeded extractor runs with authored
// confusion data. The real corpus cannot: no extractor has been run against
// these papers, because their full texts have not been ingested (every entry is
// `catalogued`, with the curator's notes standing in for the source). Scoring
// precision and recall now would mean scoring an extractor that never ran,
// against a gold set that was never annotated from source spans.
//
// So the validation dashboard shows an honest empty state instead of a number.
// That is a better artifact than a fabricated F1: it tells a faculty reader
// exactly where the project is, which is *catalogued and planned, not yet
// measured* (OF-COR-001 §22, actions 6 and 7).
//
// This file is populated after tranche-1 ingest, when:
//   1. the 40 open-access core papers have real parsed text,
//   2. the 60-record gold set of OF-COR-001 §18 has been annotated against
//      those source spans by a human, and
//   3. an extractor has actually been run.
import type { RunOutput } from './types';

export const RUN_OUTPUTS: RunOutput[] = [];

/**
 * The gold set planned in OF-COR-001 §18, kept here so the validation screen
 * can report progress against it rather than against nothing. These counts are
 * a plan, not an achievement — the screen must say so.
 */
export const GOLD_SET_PLAN: {
  paperId: string;
  fields: string;
  records: number;
  rationale: string;
}[] = [
  { paperId: 'H1', fields: 'expression_pct_tsp, titer_*, phosphorylation status + method, kinase_identity', records: 18, rationale: 'Tables 1–3 are already structured; the highest-density extraction target and the best test of table parsing.' },
  { paperId: 'H4', fields: 'expression_pct_tsp, titer, secreted_fraction, phosphate_count, glycan_species', records: 6, rationale: 'Multi-field, single paper, all numeric — an ideal precision test.' },
  { paperId: 'I1', fields: 'micellar_fraction, gelation_ph, calcium_binding, phosphorylation_degree', records: 6, rationale: 'The functional-threshold anchor.' },
  { paperId: 'C2', fields: 'titer_secreted, fold_improvement', records: 4, rationale: 'The algal secretion benchmark.' },
  { paperId: 'K1', fields: 'titer_secreted, glycan_species', records: 4, rationale: 'Cross-host benchmark.' },
  { paperId: 'F1', fields: 'gene length, exon count, precursor/mature length, variant count', records: 5, rationale: 'Tests non-quantity structured extraction.' },
  { paperId: 'J10', fields: 'disruption_protein_yield', records: 3, rationale: 'Includes a comparison pair (mutant vs WT) — tests whether extraction preserves the contrast.' },
  { paperId: 'O4', fields: 'minimum_selling_price, productivity', records: 4, rationale: 'Two cost points in one paper — tests scale-conditional extraction.' },
  { paperId: 'O2', fields: 'minimum_selling_price, titer, production volume', records: 5, rationale: 'Tests distribution-valued extraction (ranges, not points).' },
  { paperId: 'M5', fields: 'final_biomass_density, volumetric_productivity', records: 2, rationale: 'Per-field statistics backbone.' },
  { paperId: 'M6', fields: 'final_biomass_density', records: 2, rationale: 'Per-field statistics backbone.' },
  { paperId: 'M7', fields: 'growth_rate_mu', records: 2, rationale: 'The corpus’s cleanest growth-rate record.' },
  { paperId: 'A1', fields: 'expression_pct_tsp', records: 2, rationale: 'The canonical 0.2% figure.' },
  { paperId: 'B5', fields: 'time_to_colony', records: 3, rationale: 'Three strains, one field — tests entity-conditional extraction.' },
];

/** The six deliberate difficulty cases the gold set must include (§18). */
export const GOLD_SET_DIFFICULTY_CASES: string[] = [
  'A value reported only as a range ($4–6/kg) — does the extractor produce a range or invent a midpoint?',
  'A value with a compound unit requiring conversion (24.30 mg L⁻¹ h⁻¹ against daily productivity elsewhere).',
  'A comparative claim ("12-fold higher than Venus without the glycomodule") — the extractor must capture the baseline or mark the record incomplete.',
  'A negative result ("not phosphorylated") — does the extractor record it as a value or drop the row?',
  'An "undetermined" cell from Mora Vásquez Table 1 — the correct extraction is a null with a reason, not a null.',
  'The D1/D4 sialylation conflict — two papers, contradictory claims, both gold-annotated as stated. The metric must not penalise an extractor for reproducing a real disagreement.',
];
