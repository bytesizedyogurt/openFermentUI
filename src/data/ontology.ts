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
import type { FieldId, ParameterDef, ParameterFamily } from './types';

export const FAMILY_LABEL: Record<ParameterFamily, string> = {
  expression: 'Expression performance',
  ptm: 'Post-translational modification',
  functional: 'Functional performance',
  cultivation: 'Cultivation',
  downstream: 'Downstream & economics',
};

export const ONTOLOGY: ParameterDef[] = [
  // ── Family 1 — expression performance ───────────────────────────────
  {
    id: 'expression_pct_tsp',
    family: 'expression',
    name: 'Expression level (% TSP)',
    definition:
      'Accumulated recombinant protein as a percentage of total soluble protein in the host. The standard currency for intracellular expression, and not convertible to a titer without biomass concentration.',
    canonicalUnit: '% TSP',
    range: [0.001, 40],
    notes:
      'UVM4/UVM11 reporters ≈0.2; P. pastoris β-casein 15–18; Nobell patent claims ≥1 in plants.',
    refuseConversionTo: [
      {
        field: 'titer_intracellular',
        because:
          'Needs cell density and the total-protein fraction of the biomass. Without both, a percentage cannot become a concentration.',
      },
    ],
  },
  {
    id: 'titer_intracellular',
    family: 'expression',
    name: 'Intracellular titer',
    definition:
      'Recombinant protein accumulated inside the cell, per litre of culture. Requires disruption to recover.',
    canonicalUnit: 'g L⁻¹',
    range: [1e-5, 5],
    notes: 'P. pastoris β-casein 0.7–1.0 (Choi & Jiménez-Flores 2001).',
  },
  {
    id: 'titer_secreted',
    family: 'expression',
    name: 'Secreted titer',
    definition:
      'Recombinant protein released into the culture medium, per litre. Avoids cell disruption, which is why it is the preferred route for caseins.',
    canonicalUnit: 'g L⁻¹',
    range: [1e-5, 10],
    notes:
      'C. reinhardtii UVM4 0.012–0.015; T. reesei β-lactoglobulin 1.0; ovalbumin 2.0 — a ~65× gap.',
  },
  {
    id: 'secreted_fraction',
    family: 'expression',
    name: 'Secreted fraction',
    definition:
      'Proportion of total expressed protein that reaches the extracellular medium. Exposes secretion failures that a titer alone hides.',
    canonicalUnit: '% of total expressed',
    range: [0.001, 100],
    notes:
      'P. pastoris with the native bovine signal peptide: 0.005. S. cerevisiae: 5–10.',
  },
  {
    id: 'fold_improvement',
    family: 'expression',
    name: 'Fold improvement',
    definition:
      'Relative gain over a stated baseline. Meaningless without that baseline, which the record must carry.',
    canonicalUnit: '×',
    range: [0.1, 100],
    notes: 'Glycomodule 12×; safe-harbor integration 8.6×; valencene 60×.',
  },
  {
    id: 'transformation_efficiency',
    family: 'expression',
    name: 'Transformation efficiency',
    definition: 'Transformant colonies recovered per microgram of DNA delivered.',
    canonicalUnit: 'colonies µg⁻¹',
    range: [1, 1e5],
    notes: 'Strain- and method-dependent; cell-wall-deficient strains are far higher.',
  },
  {
    id: 'time_to_colony',
    family: 'expression',
    name: 'Time to colony',
    definition: 'Days from transformation to visible colonies on selection.',
    canonicalUnit: 'd',
    range: [3, 30],
    notes: 'cw15 and UVM4 7–10 d; walled WT12 15–20 d.',
  },

  // ── Family 2 — post-translational modification ──────────────────────
  {
    id: 'phosphate_count',
    family: 'ptm',
    name: 'Phosphate count',
    definition:
      'Moles of covalently bound phosphate per mole of protein. For β-casein the native state is 5, clustered at the N-terminus.',
    canonicalUnit: 'mol mol⁻¹',
    range: [0, 13],
    notes: 'β-CN 5; αs1 8–9; αs2 10–13; κ 1–3 (and uniquely can carry phospho-Thr).',
    requiresMethod: true,
  },
  {
    id: 'phosphorylation_degree',
    family: 'ptm',
    name: 'Phosphorylation degree',
    definition:
      'Achieved phosphorylation as a percentage of the native site count. The corpus’s central success metric.',
    canonicalUnit: '% of native sites',
    range: [0, 100],
    notes:
      'Drives micelle assembly, calcium binding and coagulation (Che et al. 2025).',
    requiresMethod: true,
  },
  {
    id: 'phospho_site_position',
    family: 'ptm',
    name: 'Phospho-site position',
    definition:
      'Residue index of a phosphorylation site. Meaningless without its numbering convention: β-casein is 224 residues as translated and 209 after signal-peptide removal.',
    canonicalUnit: 'residue',
    range: [1, 224],
    notes:
      'Literature quotes mature numbering. A record without a convention mislocates every site by 15.',
    requiresMethod: true,
  },
  {
    id: 'glycan_species',
    family: 'ptm',
    name: 'Glycan species',
    definition:
      'Glycan structure attached by the host. Relevant because β-casein is not natively glycosylated, so host glycosylation is a risk rather than a requirement.',
    canonicalUnit: '',
    range: [0, 0],
    notes:
      'C. reinhardtii: linear Man2–Man5, ~70% oligomannosidic, partially 6-O-methylated, xylosylated. Yeast: mannan. T. reesei: 5-sugar mannose.',
    categorical: true,
    requiresMethod: true,
  },
  {
    id: 'kinase_identity',
    family: 'ptm',
    name: 'Kinase identity',
    definition:
      'The kinase responsible for phosphorylation. An enum on purpose: "casein kinase" names three different enzymes, and CK1/CK2 do not recognise the S-x-E motif that FAM20C does.',
    canonicalUnit: '',
    range: [0, 0],
    notes:
      'FAM20C (human/bovine) · CK2 · CK1 · PrkC/PrkD/YabT (B. subtilis) · endogenous · none.',
    categorical: true,
  },

  // ── Family 3 — functional performance ───────────────────────────────
  {
    id: 'micelle_diameter',
    family: 'functional',
    name: 'Micelle diameter',
    definition: 'Hydrodynamic diameter of the assembled casein micelle.',
    canonicalUnit: 'nm',
    range: [20, 1000],
    notes:
      'Native radius ≈70 nm (so ≈140 nm diameter); dephosphorylated artificial micelles ≈3× larger and irregular.',
    requiresMethod: true,
  },
  {
    id: 'micellar_fraction',
    family: 'functional',
    name: 'Micellar fraction',
    definition:
      'Proportion of total protein that sediments as micelles rather than remaining in serum.',
    canonicalUnit: '% sedimentable',
    range: [0, 100],
    notes:
      '≈87% for fully phosphorylated reassembled micelles; fully dephosphorylated caseins hardly form micelles at all.',
    requiresMethod: true,
  },
  {
    id: 'gelation_ph',
    family: 'functional',
    name: 'Gelation pH',
    definition:
      'pH at which the protein system forms a gel on acidification. Rises as phosphorylation falls.',
    canonicalUnit: '',
    range: [4.0, 6.5],
    notes:
      'Fully dephosphorylated caseins fail to gel entirely, precipitating at ≈pH 5.5 — a binary product failure, not a quality gradient.',
    requiresMethod: true,
  },
  {
    id: 'calcium_binding',
    family: 'functional',
    name: 'Calcium binding',
    definition: 'Moles of calcium bound per mole of protein.',
    canonicalUnit: 'mol mol⁻¹',
    range: [0, 20],
    notes: 'Decreases with phosphorylation degree; the mechanism behind micelle assembly.',
    requiresMethod: true,
  },
  {
    id: 'melt_stretch_length',
    family: 'functional',
    name: 'Melt–stretch length',
    definition:
      'Extension before break in a stretch test — the attribute plant-based cheese analogues most conspicuously lack.',
    canonicalUnit: 'mm',
    range: [0, 200],
    notes: 'No standardised method; the fork test still dominates (Andrigo et al. 2025).',
    requiresMethod: true,
  },

  // ── Family 4 — cultivation ──────────────────────────────────────────
  {
    id: 'growth_rate_mu',
    family: 'cultivation',
    name: 'Specific growth rate (μ)',
    definition:
      'First-order rate constant of exponential biomass increase — the slope of ln(X) against time during unrestricted growth.',
    canonicalUnit: 'h⁻¹',
    range: [0.005, 0.35],
    notes: 'C. reinhardtii cc124 mixotrophic 0.087. Accepts d⁻¹ input.',
  },
  {
    id: 'final_biomass_density',
    family: 'cultivation',
    name: 'Final biomass density',
    definition: 'Dry cell weight per litre at harvest.',
    canonicalUnit: 'g L⁻¹',
    range: [0.05, 150],
    notes:
      'C. reinhardtii 1.2–2.2; heterotrophic algae 50–100; K. phaffii fed-batch ≈130. The harshest number in the corpus for the algal thesis.',
  },
  {
    id: 'volumetric_productivity',
    family: 'cultivation',
    name: 'Volumetric productivity',
    definition: 'Biomass or product formed per litre per hour.',
    canonicalUnit: 'mg L⁻¹ h⁻¹',
    range: [0.1, 500],
    notes: 'CC-137c in TAP: 24.3 mg L⁻¹ h⁻¹.',
  },
  {
    id: 'medium_component_conc',
    family: 'cultivation',
    name: 'Medium component concentration',
    definition: 'Concentration of a named component in the cultivation medium.',
    canonicalUnit: 'g L⁻¹',
    range: [1e-5, 120],
    notes: 'TAP components; sodium acetate optimum 4.12; NH₄Cl 0.20–0.38.',
  },

  // ── Family 5 — downstream and economics ─────────────────────────────
  {
    id: 'disruption_protein_yield',
    family: 'downstream',
    name: 'Disruption protein yield',
    definition:
      'Protein released as a percentage of total cellular protein, by a stated disruption method.',
    canonicalUnit: '% of total protein',
    range: [0, 100],
    notes:
      'PEF on cell-wall-deficient 31±6 vs walled 11±3; bead milling / HPH ≈50. The economic keystone for a cw15 intracellular strategy.',
    requiresMethod: true,
  },
  {
    id: 'disruption_energy',
    family: 'downstream',
    name: 'Disruption energy',
    definition: 'Specific energy consumed per kilogram of biomass disrupted.',
    canonicalUnit: 'kWh kg⁻¹',
    range: [0.01, 50],
    notes: 'HPH and bead milling <0.5 kWh kg⁻¹ at >95% disintegration.',
  },
  {
    id: 'minimum_selling_price',
    family: 'downstream',
    name: 'Minimum selling price',
    definition:
      'Price per kilogram at which a process breaks even over its lifetime. Collapses a whole process into one comparable number — which is its use and its danger.',
    canonicalUnit: 'USD kg⁻¹',
    range: [1, 1e5],
    notes:
      'Crude FDH 75–2,300; purified 970–99,000; biomass-fermentation protein 4–6. Currency is not auto-converted.',
    requiresMethod: true,
  },
];

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
