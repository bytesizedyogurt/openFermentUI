// The record fields (alpha 2.0): what an extracted record may hold, in four
// families. `core/openferment_core/schema/fields.yaml` is the source; this
// file mirrors it until stage 7 serves the fields from the API, and
// core/tests/test_schema.py holds the two equal through the fixture
// `pnpm export:unit-fixtures` writes. A field carries no range and no example
// value: a definition states what a number means and never what one is
// (ADR-010).
//
// Two rules a field keeps:
//
//   Rule 1 — a field marked `requiresMethod` is not interpretable without
//   the analytical method that produced its value.
//
//   Rule 2 — `expression_pct_tsp` and the titer fields are NOT
//   interconvertible without cell density and total-protein fraction. The unit
//   engine refuses and says why (see engine/units.ts `explainRefusal`).
import type { FieldId, ParameterDef, ParameterFamily } from './types';

export const FAMILY_LABEL: Record<ParameterFamily, string> = {
  expression: 'Expression performance',
  cultivation: 'Cultivation',
  downstream: 'Downstream & economics',
  kinetics: 'Growth and product kinetics',
};

export const ONTOLOGY: ParameterDef[] = [
  // ── Expression performance ────────────────────────────────────────────
  {
    id: 'expression_pct_tsp',
    family: 'expression',
    name: 'Expression level (% TSP)',
    definition:
      'Accumulated recombinant protein as a percentage of total soluble protein in the host. The standard currency for intracellular expression, and not convertible to a titer without biomass concentration.',
    canonicalUnit: '% TSP',
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
    definition: 'Recombinant protein accumulated inside the cell, per litre of culture. Requires disruption to recover.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'titer_secreted',
    family: 'expression',
    name: 'Secreted titer',
    definition: 'Recombinant protein released into the culture medium, per litre. Avoids cell disruption.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'secreted_fraction',
    family: 'expression',
    name: 'Secreted fraction',
    definition:
      'Proportion of total expressed protein that reaches the extracellular medium. Exposes secretion failures that a titer alone hides.',
    canonicalUnit: '% of total expressed',
  },
  {
    id: 'fold_improvement',
    family: 'expression',
    name: 'Fold improvement',
    definition: 'Relative gain over a stated baseline. Meaningless without that baseline, which the record must carry.',
    canonicalUnit: '×',
  },
  {
    id: 'transformation_efficiency',
    family: 'expression',
    name: 'Transformation efficiency',
    definition: 'Transformant colonies recovered per microgram of DNA delivered.',
    canonicalUnit: 'colonies µg⁻¹',
  },
  {
    id: 'time_to_colony',
    family: 'expression',
    name: 'Time to colony',
    definition: 'Days from transformation to visible colonies on selection.',
    canonicalUnit: 'd',
  },
  // ── Cultivation ───────────────────────────────────────────────────────
  {
    id: 'growth_rate_mu',
    family: 'cultivation',
    name: 'Specific growth rate (μ)',
    definition:
      'First-order rate constant of exponential biomass increase — the slope of ln(X) against time during unrestricted growth.',
    canonicalUnit: 'h⁻¹',
  },
  {
    id: 'final_biomass_density',
    family: 'cultivation',
    name: 'Final biomass density',
    definition: 'Dry cell weight per litre at harvest.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'volumetric_productivity',
    family: 'cultivation',
    name: 'Volumetric productivity',
    definition: 'Biomass or product formed per litre per hour.',
    canonicalUnit: 'mg L⁻¹ h⁻¹',
  },
  {
    id: 'medium_component_conc',
    family: 'cultivation',
    name: 'Medium component concentration',
    definition: 'Concentration of a named component in the cultivation medium.',
    canonicalUnit: 'g L⁻¹',
  },
  // ── Downstream & economics ────────────────────────────────────────────
  {
    id: 'disruption_protein_yield',
    family: 'downstream',
    name: 'Disruption protein yield',
    definition: 'Protein released as a percentage of total cellular protein, by a stated disruption method.',
    canonicalUnit: '% of total protein',
    requiresMethod: true,
  },
  {
    id: 'disruption_energy',
    family: 'downstream',
    name: 'Disruption energy',
    definition: 'Specific energy consumed per kilogram of biomass disrupted.',
    canonicalUnit: 'kWh kg⁻¹',
  },
  {
    id: 'minimum_selling_price',
    family: 'downstream',
    name: 'Minimum selling price',
    definition:
      'Price per kilogram at which a process breaks even over its lifetime. Collapses a whole process into one comparable number — which is its use and its danger.',
    canonicalUnit: 'USD kg⁻¹',
    requiresMethod: true,
  },
  {
    id: 'step_recovery',
    family: 'downstream',
    name: 'Step recovery',
    definition:
      'The share of the product entering one named downstream step that leaves it in the stream carried on, by mass: a centrifuge, a filter, a membrane or a column. Not an overall yield over several steps, not a purity (product_purity), and not a yield on substrate.',
    canonicalUnit: '%',
  },
  {
    id: 'product_purity',
    family: 'downstream',
    name: 'Product purity',
    definition:
      'The product\'s share of what a step delivers, by the measure the paper names (of total protein, or of dry matter). Not a recovery (step_recovery), and not a concentration such as a titre.',
    canonicalUnit: '%',
  },
  {
    id: 'partition_coefficient',
    family: 'downstream',
    name: 'Partition coefficient',
    definition:
      'A solute\'s concentration in the extract phase over its concentration in the raffinate phase at equilibrium, for a named solvent system: a ratio with no unit. Not a recovery over a step (step_recovery), and not a sieving coefficient (sieving_coefficient), which is a membrane\'s.',
    canonicalUnit: '',
  },
  {
    id: 'sieving_coefficient',
    family: 'downstream',
    name: 'Sieving coefficient',
    definition:
      'The share of a solute\'s concentration that passes a named membrane into the permeate, permeate over retentate concentration: one less the rejection, a ratio with no unit. Not a recovery over a whole step (step_recovery), and not a partition coefficient (partition_coefficient).',
    canonicalUnit: '',
  },
  {
    id: 'cake_moisture',
    family: 'downstream',
    name: 'Cake moisture',
    definition:
      'Water as a share of a filter or centrifuge cake\'s mass as it is discharged, wet basis. Not a dried product\'s moisture, and not the solids content of a broth.',
    canonicalUnit: '%',
  },
  // ── Growth and product kinetics ───────────────────────────────────────
  {
    id: 'monod_ks',
    family: 'kinetics',
    name: 'Substrate saturation constant (Ks)',
    definition:
      'The substrate concentration at which the specific growth rate is half its maximum in a Monod-type growth model, as a mass concentration of the limiting substrate. A fitted or reported model parameter: not a substrate concentration supplied to or measured in the medium (medium_component_conc), and not the constant of a substrate-inhibition term (substrate_inhibition_ki).',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'biomass_yield_substrate',
    family: 'kinetics',
    name: 'Biomass yield on substrate (Yx/s)',
    definition:
      'Grams of dry biomass formed per gram of substrate consumed, over the phase or run the quote states, whether observed or fitted as a model parameter. Not a yield on oxygen or on a product, and not a yield per mole or per C-mole, which belongs to no field.',
    canonicalUnit: 'g g⁻¹',
  },
  {
    id: 'ethanol_yield_substrate',
    family: 'kinetics',
    name: 'Ethanol yield on substrate (Yp/s)',
    definition:
      'Grams of ethanol formed per gram of substrate consumed, over the phase or run the quote states, whether observed or fitted as a model parameter. A yield given as a percentage of the theoretical maximum is a different quantity and belongs to no field.',
    canonicalUnit: 'g g⁻¹',
  },
  {
    id: 'ethanol_titre',
    family: 'kinetics',
    name: 'Ethanol titre',
    definition:
      'Ethanol concentration in the broth, as mass per volume, at the time the quote states — commonly the final or peak concentration of a run. A measured concentration, not the model parameter at which ethanol stops growth (ethanol_max_conc). A concentration given as a percentage by volume needs the density of ethanol to become a mass, and belongs to no field.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'ethanol_productivity',
    family: 'kinetics',
    name: 'Ethanol volumetric productivity',
    definition:
      'Ethanol formed per litre of broth per hour, over the period the quote states. Use it rather than volumetric_productivity when the product is ethanol. Not a specific rate per gram of biomass, which belongs to no field.',
    canonicalUnit: 'g L⁻¹ h⁻¹',
  },
  {
    id: 'ethanol_inhibition_ki',
    family: 'kinetics',
    name: 'Ethanol inhibition constant (Ki)',
    definition:
      'The ethanol concentration constant of a product-inhibition term in a growth or production rate model, such as the non-competitive term Ki/(Ki + P) where P is the ethanol concentration, in concentration units. A constant in litres per gram, the reciprocal of a concentration as in an exponential term, belongs to no field; the concentration at which ethanol stops growth is ethanol_max_conc.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'ethanol_max_conc',
    family: 'kinetics',
    name: 'Maximum ethanol concentration (Pmax)',
    definition:
      'The ethanol concentration at which growth or ethanol formation stops in a Levenspiel-type or linear product-inhibition model, where the inhibition term falls to nothing as the ethanol concentration P reaches Pmax. A model parameter: not the highest titre a run reached (ethanol_titre), and not the constant of a non-competitive term (ethanol_inhibition_ki).',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'substrate_inhibition_ki',
    family: 'kinetics',
    name: 'Substrate inhibition constant (KiS)',
    definition:
      'The substrate concentration constant of a substrate-inhibition term in an Andrews- or Haldane-type growth model, the term that lowers the specific growth rate as substrate accumulates. Not the saturation constant (monod_ks), and not an ethanol constant.',
    canonicalUnit: 'g L⁻¹',
  },
  {
    id: 'ethanol_lp_alpha',
    family: 'kinetics',
    name: 'Luedeking–Piret growth-associated coefficient (α)',
    definition:
      'The growth-associated coefficient α of the Luedeking–Piret model dP/dt = α dX/dt + β X, where P is ethanol and X is biomass: grams of ethanol formed per gram of biomass formed. A fitted model coefficient, not a yield on substrate.',
    canonicalUnit: 'g g⁻¹',
  },
  {
    id: 'ethanol_lp_beta',
    family: 'kinetics',
    name: 'Luedeking–Piret non-growth-associated coefficient (β)',
    definition:
      'The non-growth-associated coefficient β of the Luedeking–Piret model dP/dt = α dX/dt + β X, where P is ethanol and X is biomass: grams of ethanol formed per gram of biomass per hour. A fitted model coefficient; a specific ethanol production rate measured in a run belongs to no field.',
    canonicalUnit: 'g g⁻¹ h⁻¹',
  },
  {
    id: 'ethanol_mesp',
    family: 'kinetics',
    name: 'Minimum ethanol selling price',
    definition:
      'The ethanol price per US gallon at which a modelled plant breaks even over its life, as a techno-economic analysis states it. Its method is the costing basis the analysis names, such as a discounted cash flow analysis, or "undetermined" when it names none. A price per kilogram is minimum_selling_price; a price per litre belongs to no field.',
    canonicalUnit: 'USD gal⁻¹',
    requiresMethod: true,
    refuseConversionTo: [
      {
        field: 'minimum_selling_price',
        because:
          'Needs the density of the product the analysis assumes. Without it, a price per gallon cannot become a price per kilogram.',
      },
    ],
  },
  {
    id: 'maintenance_coefficient',
    family: 'kinetics',
    name: 'Maintenance coefficient (m)',
    definition:
      'Grams of substrate consumed per gram of dry biomass per hour to keep the cells alive rather than to grow, as the maintenance term of a Pirt-type substrate balance, whether fitted or reported. A model parameter: not a specific substrate uptake rate measured in a run, not an oxygen maintenance coefficient, and not a yield on substrate (biomass_yield_substrate).',
    canonicalUnit: 'g g⁻¹ h⁻¹',
  },
  {
    id: 'biomass_yield_oxygen',
    family: 'kinetics',
    name: 'Biomass yield on oxygen (Yx/o)',
    definition:
      'Grams of dry biomass formed per gram of oxygen consumed, over the phase or run the quote states, whether observed or fitted as a model parameter. Not a yield on substrate (biomass_yield_substrate), and not a yield per mole of oxygen or a respiratory quotient, which belong to no field.',
    canonicalUnit: 'g g⁻¹',
  },
  {
    id: 'specific_oxygen_uptake',
    family: 'kinetics',
    name: 'Specific oxygen uptake rate (qO2)',
    definition:
      'Oxygen consumed per gram of dry biomass per hour, in moles, as measured in a run or fitted as a model parameter. Not a volumetric oxygen uptake or transfer rate per litre of broth, and not a mass-transfer coefficient (kla_measured).',
    canonicalUnit: 'mmol g⁻¹ h⁻¹',
  },
  {
    id: 'kla_measured',
    family: 'kinetics',
    name: 'Volumetric oxygen mass-transfer coefficient (kLa)',
    definition:
      'The volumetric mass-transfer coefficient of oxygen from gas to liquid that a paper measured or reports for its vessel and conditions, per unit time. A property of the vessel, the broth and how it is stirred and aerated, not of the cells: not an oxygen uptake rate (specific_oxygen_uptake) and not a transfer rate per litre of broth.',
    canonicalUnit: 'h⁻¹',
  },
];

export const ONTOLOGY_BY_ID: Record<FieldId, ParameterDef> = Object.fromEntries(
  ONTOLOGY.map((d) => [d.id, d]),
) as Record<FieldId, ParameterDef>;

export function fieldName(id: FieldId): string {
  return ONTOLOGY_BY_ID[id]?.name ?? id;
}

/** Fields where a value without its analytical method is not interpretable. */
export function requiresMethod(id: FieldId): boolean {
  return ONTOLOGY_BY_ID[id]?.requiresMethod ?? false;
}
