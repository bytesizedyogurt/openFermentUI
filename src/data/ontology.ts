// Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families,
// replacing the 16-field synthetic ontology of OF-DES-001 Appendix C — the
// polymer family OF-BLD-014 §2.1 adds for thread P, and the kinetics family
// the yeast-ethanol program adds for thread Q: 40 fields in seven.
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
  polymer: 'Polymer',
  kinetics: 'Growth and product kinetics',
};

/**
 * Who chose the validation ranges OF-BLD-014 §2.1 sets, and what they are
 * for (its decision D9; OF-BLD-014 E.1). A range is a guard, not a result.
 */
const D9_RANGE_NOTE =
  'Validation range proposed in OF-BLD-014 and accepted by Sean Creighton on 2026-10-14. It rejects implausible extractions and states nothing about what has been achieved.';

/**
 * The same, for the kinetics family the yeast-ethanol program (thread Q)
 * adds, written in D9's form. One constant, so that recording Sean's answer
 * is a one-line edit.
 */
const Y1_RANGE_NOTE =
  'Validation range proposed on 2026-10-20 for the yeast-ethanol program (thread Q), awaiting acceptance by Sean Creighton. It rejects implausible extractions and states nothing about what has been achieved.';

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
    // Widened from the 10 g/L of OF-COR-001 §17: that ceiling reflected casein
    // specifically, but the field also carries the general-fermentation titers
    // the TEA sources quote (24 g/L published average, 42 g/L private benchmark).
    range: [1e-5, 50],
    notes:
      'C. reinhardtii UVM4 0.012–0.015; T. reesei β-lactoglobulin 1.0; ovalbumin 2.0 — a ~65× gap. Industry fermentation averages run 24–42.',
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
    // The upper bound was set for algae; OF-BLD-014 §2.1 widened it, under
    // D9, so a bacterium's growth rate passes.
    range: [0.005, 2.5],
    notes: `C. reinhardtii cc124 mixotrophic 0.087. Accepts d⁻¹ input. The upper bound was widened for bacteria under OF-BLD-014 §2.1. ${D9_RANGE_NOTE}`,
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

  // ── Family 6 — polymer (OF-BLD-014 §2.1) ────────────────────────────
  // Thread P's polyhydroxyalkanoates. Every range here is a guard Sean
  // Creighton accepted under D9, not a value anybody measured.
  {
    id: 'pha_content_cdw',
    family: 'polymer',
    name: 'PHA content',
    definition: 'Mass fraction of polymer in dry cell mass.',
    canonicalUnit: '% CDW',
    range: [0.1, 95],
    notes: D9_RANGE_NOTE,
    requiresMethod: true,
    refuseConversionTo: [
      {
        field: 'pha_titre',
        because:
          'Needs the biomass density of that culture. Without it, a share of dry cell mass cannot become a concentration.',
      },
    ],
  },
  {
    id: 'pha_titre',
    family: 'polymer',
    name: 'PHA titre',
    definition: 'Polymer mass per culture volume.',
    canonicalUnit: 'g L⁻¹',
    range: [0.01, 250],
    notes: D9_RANGE_NOTE,
    refuseConversionTo: [
      {
        field: 'pha_content_cdw',
        because:
          'Needs the biomass density of that culture. Without it, a concentration cannot become a share of dry cell mass.',
      },
    ],
  },
  {
    id: 'pha_yield_substrate',
    family: 'polymer',
    name: 'PHA yield on substrate',
    definition: 'Grams of polymer per gram of carbon source consumed.',
    canonicalUnit: 'g g⁻¹',
    range: [0.001, 1],
    notes: D9_RANGE_NOTE,
  },
  {
    id: 'pha_productivity',
    family: 'polymer',
    name: 'PHA volumetric productivity',
    definition: 'Polymer formed per litre per hour.',
    canonicalUnit: 'g L⁻¹ h⁻¹',
    range: [0.001, 10],
    notes: D9_RANGE_NOTE,
  },
  {
    id: 'pha_mw',
    family: 'polymer',
    name: 'Polymer molecular weight',
    definition: 'Weight-average or number-average; the quote says which.',
    canonicalUnit: 'kDa',
    range: [1, 10000],
    notes: D9_RANGE_NOTE,
    requiresMethod: true,
  },

  // ── Family 7 — growth and product kinetics (thread Q) ───────────────
  // The yeast-ethanol program: wild-type S. cerevisiae on glucose in batch.
  // The parameters a kinetics paper fits, the titre, yield and productivity
  // it fits them to, and the selling price a techno-economic analysis
  // computes. The extraction model reads each definition, so each names the
  // fields it must not be mistaken for and carries no number. Every range is
  // a guard proposed for Sean Creighton's acceptance, not a value anybody
  // measured.
  {
    id: 'monod_ks',
    family: 'kinetics',
    name: 'Substrate saturation constant (Ks)',
    definition:
      'The substrate concentration at which the specific growth rate is half its maximum in a Monod-type growth model, as a mass concentration of the limiting substrate. A fitted or reported model parameter: not a substrate concentration supplied to or measured in the medium (medium_component_conc), and not the constant of a substrate-inhibition term (substrate_inhibition_ki).',
    canonicalUnit: 'g L⁻¹',
    range: [1e-5, 100],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'biomass_yield_substrate',
    family: 'kinetics',
    name: 'Biomass yield on substrate (Yx/s)',
    definition:
      'Grams of dry biomass formed per gram of substrate consumed, over the phase or run the quote states, whether observed or fitted as a model parameter. Not a yield on oxygen or on a product, and not a yield per mole or per C-mole, which belongs to no field.',
    canonicalUnit: 'g g⁻¹',
    range: [0.001, 1],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_yield_substrate',
    family: 'kinetics',
    name: 'Ethanol yield on substrate (Yp/s)',
    definition:
      'Grams of ethanol formed per gram of substrate consumed, over the phase or run the quote states, whether observed or fitted as a model parameter. A yield given as a percentage of the theoretical maximum is a different quantity and belongs to no field.',
    canonicalUnit: 'g g⁻¹',
    range: [0.001, 0.6],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_titre',
    family: 'kinetics',
    name: 'Ethanol titre',
    definition:
      'Ethanol concentration in the broth, as mass per volume, at the time the quote states — commonly the final or peak concentration of a run. A measured concentration, not the model parameter at which ethanol stops growth (ethanol_max_conc). A concentration given as a percentage by volume needs the density of ethanol to become a mass, and belongs to no field.',
    canonicalUnit: 'g L⁻¹',
    range: [0.01, 250],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_productivity',
    family: 'kinetics',
    name: 'Ethanol volumetric productivity',
    definition:
      'Ethanol formed per litre of broth per hour, over the period the quote states. Use it rather than volumetric_productivity when the product is ethanol. Not a specific rate per gram of biomass, which belongs to no field.',
    canonicalUnit: 'g L⁻¹ h⁻¹',
    range: [0.001, 100],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_inhibition_ki',
    family: 'kinetics',
    name: 'Ethanol inhibition constant (Ki)',
    definition:
      'The ethanol concentration constant of a product-inhibition term in a growth or production rate model, such as the non-competitive term Ki/(Ki + P) where P is the ethanol concentration, in concentration units. A constant in litres per gram, the reciprocal of a concentration as in an exponential term, belongs to no field; the concentration at which ethanol stops growth is ethanol_max_conc.',
    canonicalUnit: 'g L⁻¹',
    range: [0.01, 300],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_max_conc',
    family: 'kinetics',
    name: 'Maximum ethanol concentration (Pmax)',
    definition:
      'The ethanol concentration at which growth or ethanol formation stops in a Levenspiel-type or linear product-inhibition model, where the inhibition term falls to nothing as the ethanol concentration P reaches Pmax. A model parameter: not the highest titre a run reached (ethanol_titre), and not the constant of a non-competitive term (ethanol_inhibition_ki).',
    canonicalUnit: 'g L⁻¹',
    range: [1, 300],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'substrate_inhibition_ki',
    family: 'kinetics',
    name: 'Substrate inhibition constant (KiS)',
    definition:
      'The substrate concentration constant of a substrate-inhibition term in an Andrews- or Haldane-type growth model, the term that lowers the specific growth rate as substrate accumulates. Not the saturation constant (monod_ks), and not an ethanol constant.',
    canonicalUnit: 'g L⁻¹',
    range: [0.01, 1000],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_lp_alpha',
    family: 'kinetics',
    name: 'Luedeking–Piret growth-associated coefficient (α)',
    definition:
      'The growth-associated coefficient α of the Luedeking–Piret model dP/dt = α dX/dt + β X, where P is ethanol and X is biomass: grams of ethanol formed per gram of biomass formed. A fitted model coefficient, not a yield on substrate.',
    canonicalUnit: 'g g⁻¹',
    range: [0, 50],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_lp_beta',
    family: 'kinetics',
    name: 'Luedeking–Piret non-growth-associated coefficient (β)',
    definition:
      'The non-growth-associated coefficient β of the Luedeking–Piret model dP/dt = α dX/dt + β X, where P is ethanol and X is biomass: grams of ethanol formed per gram of biomass per hour. A fitted model coefficient; a specific ethanol production rate measured in a run belongs to no field.',
    canonicalUnit: 'g g⁻¹ h⁻¹',
    range: [0, 10],
    notes: Y1_RANGE_NOTE,
  },
  {
    id: 'ethanol_mesp',
    family: 'kinetics',
    name: 'Minimum ethanol selling price',
    definition:
      'The ethanol price per US gallon at which a modelled plant breaks even over its life, as a techno-economic analysis states it. Its method is the costing basis the analysis names, such as a discounted cash flow analysis, or "undetermined" when it names none. A price per kilogram is minimum_selling_price; a price per litre belongs to no field.',
    canonicalUnit: 'USD gal⁻¹',
    range: [0.1, 50],
    notes: Y1_RANGE_NOTE,
    requiresMethod: true,
    refuseConversionTo: [
      {
        field: 'minimum_selling_price',
        because:
          'Needs the density of the product the analysis assumes. Without it, a price per gallon cannot become a price per kilogram.',
      },
    ],
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
