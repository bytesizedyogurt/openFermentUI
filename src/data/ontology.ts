// Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families,
// replacing the 16-field synthetic ontology of OF-DES-001 Appendix C.
//
// Two rules this literature forces and the synthetic version did not:
//
//   Rule 1 — every PTM and functional field carries a mandatory `method`
//   qualifier. "Phosphorylated: yes" is worthless without knowing whether it
//   came from LC-ESI-MS, Phos-tag, urea-PAGE with phosphatase, or an SDS-PAGE
//   mobility inference. `undetermined` is a legitimate answer meaning the
//   analysis was never done — which is different from a negative result.
//
//   Rule 2 — `expression_pct_tsp` and the titer fields are NOT
//   interconvertible without cell density and total-protein fraction. The unit
//   engine refuses and says why (see engine/units.ts `explainRefusal`).
// The collection itself now comes from the adapter; this module keeps only
// the derived views built on top of it.
import { ONTOLOGY } from '@/data/source';

export { ONTOLOGY };

import type { FieldId, ParameterDef, ParameterFamily } from './types';

export const FAMILY_LABEL: Record<ParameterFamily, string> = {
  expression: 'Expression performance',
  ptm: 'Post-translational modification',
  functional: 'Functional performance',
  cultivation: 'Cultivation',
  downstream: 'Downstream & economics',
};


export const ONTOLOGY_BY_ID: Record<FieldId, ParameterDef> = Object.fromEntries(
  ONTOLOGY.map((d) => [d.id, d]),
) as Record<FieldId, ParameterDef>;

export const ONTOLOGY_BY_FAMILY: Record<ParameterFamily, ParameterDef[]> = ONTOLOGY.reduce(
  (acc, d) => {
    (acc[d.family] ??= []).push(d);
    return acc;
  },
  {} as Record<ParameterFamily, ParameterDef[]>,
);

export function fieldName(id: FieldId): string {
  return ONTOLOGY_BY_ID[id]?.name ?? id;
}

/** Fields where a value without its analytical method is not interpretable. */
export function requiresMethod(id: FieldId): boolean {
  return ONTOLOGY_BY_ID[id]?.requiresMethod ?? false;
}

/**
 * Real values in the corpus that ontology v1 has NO field for.
 *
 * Recorded rather than forced. Filing C4's 97% sequence coverage under
 * `secreted_fraction` — the only numerically-shaped candidate — would assert
 * that 97% of expressed xylanase was secreted, which the paper does not say,
 * and would sit on the same strip plot as P. pastoris's 0.005%. An ontology
 * that quietly absorbs values it was not designed for produces confident
 * nonsense; one that refuses leaves a visible gap. This is the gap.
 *
 * Note the consequence for OF-COR-001 §18: the gold-set plan plans five
 * records from F1 on gene length, exon count, precursor/mature length and
 * variant count. None of those is expressible in ontology v1, so that row of
 * the plan cannot be built until the ontology is extended.
 */
export const ONTOLOGY_GAPS: {
  entry: string;
  values: string;
  wouldNeed: string;
}[] = [
  {
    entry: 'B2',
    values: 'Nuclear genome ~64% GC overall and ~68% in coding regions; mature β-casein CDS 627 nt',
    wouldNeed: 'genome_gc_content (%), cds_length (nt)',
  },
  {
    entry: 'C4',
    values: 'LC-MS/MS peptide coverage of 97% cytoplasmic and 89% secreted sequence',
    wouldNeed: 'sequence_coverage (%) — distinct from secreted_fraction, which means something else entirely',
  },
  {
    entry: 'E3',
    values: '209 aa; 23,946–24,097 Da; 15–60 molecules per micelle; CMC 0.05–0.2%',
    wouldNeed: 'protein_length (aa), molecular_mass (Da), aggregation_number, critical_micelle_conc (%)',
  },
  {
    entry: 'F1',
    values: 'CSN2 10,338 bp; 9 exons, 8 introns; 224-aa precursor, 209-aa mature; 15 coding variants',
    wouldNeed: 'gene_length (bp), exon_count, protein_length (aa), variant_count — blocks §18’s F1 gold-set row',
  },
  {
    entry: 'F3',
    values: '35 of 209 residues in the A2 variant are proline (~16.7 mol%)',
    wouldNeed: 'residue_composition (mol%) with a residue tag',
  },
  {
    entry: 'L3',
    values: 'Cheddar hardness 126.8 N, firmness 98.81 N, Young’s modulus 953.3 kPa',
    wouldNeed: 'texture_hardness (N), youngs_modulus (kPa) — the melt_stretch_length field covers only one texture attribute',
  },
  {
    entry: 'O2 · O4 · O5 · O7',
    values:
      'Production volumes in t/y; percentage cost breakdowns (centrifugation 10.65%, freeze-drying 20.15%); photosynthetic efficiency 3.6%',
    wouldNeed: 'production_volume (t/y), cost_share (%), photosynthetic_efficiency (%)',
  },
  {
    entry: 'B5',
    values: 'PSAD and CA1 terminators gave significantly higher transformant counts (p<0.01)',
    wouldNeed:
      'a way to hold a comparative-significance claim with no absolute value — the source states no transformant count, so transformation_efficiency has nothing to carry',
  },
];
