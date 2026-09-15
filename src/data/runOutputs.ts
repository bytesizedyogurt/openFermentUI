// Extractor runs in the SEED (OF-DES-001 §8.8, OF-BLD-012 §6.4).
//
// EMPTY, AND IT STAYS EMPTY.
//
// The synthetic corpus once shipped three seeded extractor runs with authored
// confusion data. The real corpus never did: no extractor had read these
// papers, so there was nothing to score, and the validation screen showed an
// honest empty state instead of a fabricated F1.
//
// Now one has. OF-BLD-012 §6 fetches the open-access papers' full text, runs
// Claude Haiku once per paper with a forced tool call, anchors every candidate
// to a verbatim quote, and scores the run against the curated records
// (`match_run`, core/openferment_core/witness.py). That run — `haiku-1` — does
// NOT land in this file. It arrives through the service's overlay,
// `GET /api/biorepo/overlay` → `overlay.runs`, recomputed from
// core/data/candidates/ on every request, and the store merges it into
// `runOutputs` at load. Witness scores it live, in provisional mode until a
// reviewer flags real gold in Guild.
//
// So this array is what the app has with the service down, and it is empty
// because a run is a measurement and a measurement is not seed data. With the
// service up, Witness shows the run that ran.
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
  /** Cannot be annotated until the ontology is extended (see ONTOLOGY_GAPS). */
  blocked?: boolean;
}[] = [
  { paperId: 'H1', fields: 'expression_pct_tsp, titer_*, phosphorylation status + method, kinase_identity', records: 18, rationale: 'Tables 1–3 are already structured; the highest-density extraction target and the best test of table parsing.' },
  { paperId: 'H4', fields: 'expression_pct_tsp, titer, secreted_fraction, phosphate_count, glycan_species', records: 6, rationale: 'Multi-field, single paper, all numeric — an ideal precision test.' },
  { paperId: 'I1', fields: 'micellar_fraction, gelation_ph, calcium_binding, phosphorylation_degree', records: 6, rationale: 'The functional-threshold anchor.' },
  { paperId: 'C2', fields: 'titer_secreted, fold_improvement', records: 4, rationale: 'The algal secretion benchmark.' },
  { paperId: 'K1', fields: 'titer_secreted, glycan_species', records: 4, rationale: 'Cross-host benchmark.' },
  {
    paperId: 'F1',
    fields: 'gene length, exon count, precursor/mature length, variant count',
    records: 5,
    rationale:
      'Tests non-quantity structured extraction — BLOCKED: ontology v1 has no field for any of these four. See ONTOLOGY_GAPS in data/ontology.ts.',
    blocked: true,
  },
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
