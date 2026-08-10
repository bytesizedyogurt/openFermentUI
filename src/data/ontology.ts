// Parameter ontology v0 — 16 fields (OF-DES-001 Appendix C)
import type { ParameterDef, FieldId } from './types';

export const ONTOLOGY: ParameterDef[] = [
  {
    id: 'growth_rate_mu',
    name: 'Specific growth rate (μ)',
    definition:
      'First-order rate constant of exponential biomass increase; slope of ln(X) vs time during unrestricted growth.',
    canonicalUnit: 'h⁻¹',
    range: [0.005, 0.35],
    notes: 'Accepts d⁻¹ input.',
  },
  {
    id: 'doubling_time',
    name: 'Doubling time',
    definition: 'Time for biomass to double during exponential growth; ln(2)/μ.',
    canonicalUnit: 'h',
    range: [2, 140],
    notes: 'Derived-consistent with μ.',
  },
  {
    id: 'yield_biomass_substrate',
    name: 'Biomass yield on substrate (Y_X/S)',
    definition: 'Grams dry biomass formed per gram substrate consumed.',
    canonicalUnit: 'g g⁻¹',
    range: [0.05, 1.2],
    notes: 'Substrate tagged.',
  },
  {
    id: 'final_biomass_density',
    name: 'Final biomass density',
    definition: 'Dry cell weight concentration at harvest or end of batch.',
    canonicalUnit: 'g L⁻¹',
    range: [0.05, 150],
    notes: 'DCW basis.',
  },
  {
    id: 'protein_content',
    name: 'Protein content',
    definition: 'Total protein as a percentage of dry weight.',
    canonicalUnit: '% DW',
    range: [5, 75],
    notes: 'Method tagged.',
  },
  {
    id: 'product_titer',
    name: 'Product titer',
    definition: 'Concentration of target product in broth at end of process.',
    canonicalUnit: 'g L⁻¹',
    range: [0.01, 120],
    notes: 'Product tagged.',
  },
  {
    id: 'volumetric_productivity',
    name: 'Volumetric productivity',
    definition: 'Product formed per reactor volume per unit time.',
    canonicalUnit: 'g L⁻¹ h⁻¹',
    range: [0.0001, 6],
    notes: '',
  },
  {
    id: 'specific_productivity',
    name: 'Specific productivity (q_p)',
    definition: 'Product formed per gram biomass per unit time.',
    canonicalUnit: 'mg g⁻¹ h⁻¹',
    range: [0.01, 80],
    notes: '',
  },
  {
    id: 'od_dcw_factor',
    name: 'OD→DCW conversion factor',
    definition: 'Dry cell weight per unit optical density at the stated wavelength.',
    canonicalUnit: 'g L⁻¹ OD⁻¹',
    range: [0.1, 1.2],
    notes: 'Wavelength tagged.',
  },
  {
    id: 'medium_component_conc',
    name: 'Medium component concentration',
    definition: 'Concentration of a named component in a defined medium recipe.',
    canonicalUnit: 'g L⁻¹',
    range: [0.00001, 120],
    notes: 'Component tagged; mol conversions.',
  },
  {
    id: 'ph_setpoint',
    name: 'pH setpoint',
    definition: 'Controlled or initial pH of the culture.',
    canonicalUnit: '',
    range: [2, 11],
    notes: 'Dimensionless.',
  },
  {
    id: 'temperature',
    name: 'Temperature',
    definition: 'Culture temperature setpoint.',
    canonicalUnit: '°C',
    range: [4, 65],
    notes: 'Accepts K, °F.',
  },
  {
    id: 'light_intensity',
    name: 'Light intensity',
    definition: 'Photosynthetically active photon flux density at culture surface.',
    canonicalUnit: 'µmol m⁻² s⁻¹',
    range: [5, 3000],
    notes: '',
  },
  {
    id: 'co2_enrichment',
    name: 'CO₂ enrichment',
    definition: 'CO₂ fraction in sparge gas, percent by volume.',
    canonicalUnit: '% v/v',
    range: [0.04, 15],
    notes: '',
  },
  {
    id: 'harvest_recovery',
    name: 'Harvest recovery',
    definition: 'Percentage of culture biomass recovered by the harvest step.',
    canonicalUnit: '%',
    range: [20, 100],
    notes: 'Method tagged.',
  },
  {
    id: 'disruption_efficiency',
    name: 'Disruption efficiency',
    definition: 'Percentage of cells lysed by the disruption step.',
    canonicalUnit: '%',
    range: [10, 100],
    notes: 'Method tagged.',
  },
];

export const ONTOLOGY_BY_ID: Record<FieldId, ParameterDef> = Object.fromEntries(
  ONTOLOGY.map((d) => [d.id, d]),
) as Record<FieldId, ParameterDef>;

export function fieldName(id: FieldId): string {
  return ONTOLOGY_BY_ID[id]?.name ?? id;
}
