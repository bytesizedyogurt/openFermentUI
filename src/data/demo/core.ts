// openFerment demo suite — core object pool.
//
// SUBSTANCE IS REAL. IDENTIFIERS ARE SYNTHETIC.
// Every mechanism, constraint, optimum and causal claim below is drawn from
// real bioprocess engineering and should survive a domain expert reading it.
// Every author name, DOI, patent number and assignee is invented. Patent
// numbers use provably-impossible series so nothing here can collide with a
// live filing. See SEED_DISCLAIMER, which must render somewhere persistent.
import type {
  FieldDef, Source, Organism, Plant, Accession,
} from './types';

export const SEED_DISCLAIMER =
  'Demonstration corpus. Technical substance is drawn from published bioprocess engineering; ' +
  'all citation identifiers, author names, patent numbers and assignees are synthetic. ' +
  'Patent numbers use out-of-range series (US 2029/…, EP 4 9…, WO 2028/…) and cannot correspond to a live filing.';

/** Frozen. A demo whose expiry countdowns drift over a weekend breaks on stage. */
export const DEMO_NOW = '2026-08-21';
export const DEMO_HORIZON_MONTHS = 24;

// ── Physical constants used by lib/transport.ts ────────────────────────

/** O₂ solubility in water at 1 atm air, mmol L⁻¹, by temperature °C. */
export const O2_SOLUBILITY: Record<number, number> = {
  20: 0.284, 25: 0.256, 30: 0.234, 35: 0.215, 40: 0.199, 45: 0.185, 50: 0.174, 55: 0.164,
};

/** Heat of aerobic catabolism per mole O₂ consumed. Thornton's constant. */
export const HEAT_PER_MOL_O2_KJ = 460;

/**
 * van 't Riet coefficients for kLa = C · (P/V)^a · vs^b, SI in, s⁻¹ out.
 * Coalescing is clean water; non-coalescing is electrolyte broth, which is
 * what any real fermentation is. Use `nonCoalescing` for every candidate.
 */
export const KLA_CORRELATION = {
  coalescing: { C: 0.026, a: 0.4, b: 0.5 },
  nonCoalescing: { C: 0.002, a: 0.7, b: 0.2 },
};

/** Six-tenths rule. */
export const CAPEX_SCALE_EXPONENT = 0.6;
export const CAPITAL_CHARGE = 0.12;
export const OPERATING_DAYS = 330;

// ── Unit table — normalisation is the moat, so it is code, not prose ───

export interface UnitDef {
  unit: string;
  dimension: string;
  /** Multiply by this to reach the canonical unit of the dimension. */
  toCanonical: number;
  /** Set for units needing an offset (temperature). */
  offset?: number;
  /** Set for units that cannot be converted without an auxiliary quantity. */
  requiresAuxiliary?: 'biomass' | 'molarMass' | 'temperature';
}

export const UNIT_TABLE: UnitDef[] = [
  // concentration → g L⁻¹
  { unit: 'g L⁻¹', dimension: 'concentration', toCanonical: 1 },
  { unit: 'kg m⁻³', dimension: 'concentration', toCanonical: 1 },
  { unit: 'mg L⁻¹', dimension: 'concentration', toCanonical: 1e-3 },
  { unit: 'g kg⁻¹', dimension: 'concentration', toCanonical: 1 },
  { unit: 'mM', dimension: 'concentration', toCanonical: 1, requiresAuxiliary: 'molarMass' },
  // volumetric rate → g L⁻¹ h⁻¹
  { unit: 'g L⁻¹ h⁻¹', dimension: 'volumetric-rate', toCanonical: 1 },
  { unit: 'g L⁻¹ d⁻¹', dimension: 'volumetric-rate', toCanonical: 1 / 24 },
  { unit: 'mg L⁻¹ h⁻¹', dimension: 'volumetric-rate', toCanonical: 1e-3 },
  { unit: 'g gDCW⁻¹ h⁻¹', dimension: 'volumetric-rate', toCanonical: 1, requiresAuxiliary: 'biomass' },
  { unit: 'mmol gDCW⁻¹ h⁻¹', dimension: 'volumetric-rate', toCanonical: 1, requiresAuxiliary: 'biomass' },
  // molar volumetric rate → mmol L⁻¹ h⁻¹
  { unit: 'mmol L⁻¹ h⁻¹', dimension: 'molar-rate', toCanonical: 1 },
  { unit: 'mol m⁻³ h⁻¹', dimension: 'molar-rate', toCanonical: 1 },
  { unit: 'mol L⁻¹ h⁻¹', dimension: 'molar-rate', toCanonical: 1000 },
  // temperature → °C
  { unit: '°C', dimension: 'temperature', toCanonical: 1 },
  { unit: 'K', dimension: 'temperature', toCanonical: 1, offset: -273.15 },
  { unit: '°F', dimension: 'temperature', toCanonical: 5 / 9, offset: -32 },
  // rate constants → h⁻¹
  { unit: 'h⁻¹', dimension: 'first-order', toCanonical: 1 },
  { unit: 's⁻¹', dimension: 'first-order', toCanonical: 3600 },
  { unit: 'd⁻¹', dimension: 'first-order', toCanonical: 1 / 24 },
  // yield → g g⁻¹
  { unit: 'g g⁻¹', dimension: 'yield', toCanonical: 1 },
  { unit: '% (w/w)', dimension: 'yield', toCanonical: 0.01 },
  { unit: 'mol mol⁻¹', dimension: 'yield', toCanonical: 1, requiresAuxiliary: 'molarMass' },
  { unit: 'C-mol C-mol⁻¹', dimension: 'yield', toCanonical: 1, requiresAuxiliary: 'molarMass' },
  // power, duty
  { unit: 'W m⁻³', dimension: 'power-density', toCanonical: 1 },
  { unit: 'kW m⁻³', dimension: 'power-density', toCanonical: 1000 },
  { unit: 'hp per 1000 gal', dimension: 'power-density', toCanonical: 197 },
  { unit: 'kW', dimension: 'power', toCanonical: 1 },
  // dimensionless
  { unit: '%', dimension: 'fraction', toCanonical: 0.01 },
  { unit: 'fraction', dimension: 'fraction', toCanonical: 1 },
  { unit: '', dimension: 'dimensionless', toCanonical: 1 },
  // economics
  { unit: 'USD t⁻¹', dimension: 'unit-cost', toCanonical: 1 },
  { unit: 'USD kg⁻¹', dimension: 'unit-cost', toCanonical: 1000 },
  { unit: 'EUR kg⁻¹', dimension: 'unit-cost', toCanonical: 1080 },  // fixed demo FX, stated
  { unit: 't a⁻¹', dimension: 'throughput', toCanonical: 1 },
];

export const DEMO_FX_NOTE =
  'EUR→USD fixed at 1.08 for the whole corpus and stated on every converted Accession. ' +
  'A floating rate would make two identical Accessions disagree by the date they were viewed.';

/** Molar masses used by molar↔mass conversions. g mol⁻¹. */
export const MOLAR_MASS: Record<string, number> = {
  'L-lysine': 146.19,
  'L-lysine·HCl': 182.65,
  glucose: 180.16,
  '3-HP': 90.08,
  glycerol: 92.09,
  'L-lactic acid': 90.08,
  xylose: 150.13,
  xylitol: 152.15,
  O2: 31.998,
  CO2: 44.009,
  acetate: 59.04,
  succinate: 118.09,
  // Used by OF-A-00214's normalisation. Named rather than inlined there so the
  // mass lives in one place, like every other species here.
  '3-hydroxypropionaldehyde': 74.08,
};

// ── Field ontology ─────────────────────────────────────────────────────

export const FIELDS: FieldDef[] = [
  { id: 'temperature', name: 'Cultivation temperature', family: 'process', canonicalUnit: '°C', definition: 'Broth temperature setpoint during the phase named in context.', aggregatable: true },
  { id: 'ph', name: 'pH setpoint', family: 'process', canonicalUnit: '', definition: 'Controlled broth pH. Measurement temperature recorded in context where the source states it.', aggregatable: true },
  { id: 'dissolved_oxygen', name: 'Dissolved oxygen setpoint', family: 'process', canonicalUnit: '%', definition: 'Percent of air saturation at process temperature and pressure.', aggregatable: true },
  { id: 'mu_setpoint', name: 'Specific growth rate setpoint', family: 'process', canonicalUnit: 'h⁻¹', definition: 'Target μ imposed by an exponential feed profile.', aggregatable: true },
  { id: 'feed_rate', name: 'Feed rate', family: 'process', canonicalUnit: 'g L⁻¹ h⁻¹', definition: 'Substrate delivery rate to the vessel.', aggregatable: true },
  { id: 'agitation_power', name: 'Installed power per volume', family: 'process', canonicalUnit: 'W m⁻³', definition: 'Ungassed impeller power divided by working volume.', aggregatable: true },
  { id: 'aeration_rate', name: 'Aeration rate', family: 'process', canonicalUnit: 'h⁻¹', definition: 'Volume of gas per volume of broth per minute, expressed as VVM and normalised.', aggregatable: true },
  { id: 'co2_overlay', name: 'CO₂ / bicarbonate supplementation', family: 'process', canonicalUnit: 'mM', definition: 'Dissolved inorganic carbon available for anaplerotic carboxylation.', aggregatable: true },
  { id: 'biotin_conc', name: 'Biotin concentration', family: 'process', canonicalUnit: 'mg L⁻¹', definition: 'Medium biotin. Load-bearing for Corynebacterium membrane permeability.', aggregatable: true },
  { id: 'titer', name: 'Final product titer', family: 'performance', canonicalUnit: 'g L⁻¹', definition: 'Product concentration in broth at harvest.', aggregatable: true },
  { id: 'yield_product_substrate', name: 'Product yield on substrate', family: 'performance', canonicalUnit: 'g g⁻¹', definition: 'Mass of product per mass of carbon substrate consumed.', aggregatable: true },
  { id: 'volumetric_productivity', name: 'Volumetric productivity', family: 'performance', canonicalUnit: 'g L⁻¹ h⁻¹', definition: 'Product formed per litre per hour, averaged over the stated window.', aggregatable: true },
  { id: 'specific_productivity', name: 'Specific productivity', family: 'performance', canonicalUnit: 'g gDCW⁻¹ h⁻¹', definition: 'qp. Normalising to volumetric requires a biomass Accession.', aggregatable: true },
  { id: 'byproduct_conc', name: 'Byproduct concentration', family: 'performance', canonicalUnit: 'g L⁻¹', definition: 'Named byproduct at harvest or at the stated timepoint.', aggregatable: true },
  { id: 'carbon_balance_closure', name: 'Carbon balance closure', family: 'performance', canonicalUnit: '%', definition: 'Carbon accounted for as biomass, product, byproducts and CO₂, over carbon fed.', aggregatable: true },
  { id: 'kla', name: 'Volumetric mass transfer coefficient', family: 'transport', canonicalUnit: 'h⁻¹', definition: 'kLa for oxygen at the stated geometry, power input and aeration.', aggregatable: true },
  { id: 'otr', name: 'Oxygen transfer rate', family: 'transport', canonicalUnit: 'mmol L⁻¹ h⁻¹', definition: 'kLa · (C* − C_L) at the stated driving force.', aggregatable: true },
  { id: 'our', name: 'Oxygen uptake rate', family: 'transport', canonicalUnit: 'mmol L⁻¹ h⁻¹', definition: 'Measured from off-gas by mass balance.', aggregatable: true },
  { id: 'cer', name: 'Carbon evolution rate', family: 'transport', canonicalUnit: 'mmol L⁻¹ h⁻¹', definition: 'CO₂ produced per litre per hour, from off-gas.', aggregatable: true },
  { id: 'rq', name: 'Respiratory quotient', family: 'transport', canonicalUnit: '', definition: 'CER divided by OUR. Diagnostic for metabolic mode.', aggregatable: true },
  { id: 'metabolic_heat', name: 'Metabolic heat generation', family: 'transport', canonicalUnit: 'kW', definition: 'OUR · volume · 460 kJ per mol O₂.', aggregatable: true },
  { id: 'cooling_duty', name: 'Cooling duty required', family: 'transport', canonicalUnit: 'kW', definition: 'Metabolic heat plus agitation heat, less evaporative loss.', aggregatable: true },
  { id: 'growth_rate_mu', name: 'Specific growth rate', family: 'physiology', canonicalUnit: 'h⁻¹', definition: 'Observed μ, distinct from an imposed setpoint.', aggregatable: true },
  { id: 'biomass_density', name: 'Biomass concentration', family: 'physiology', canonicalUnit: 'g L⁻¹', definition: 'Dry cell weight per litre of broth.', aggregatable: true },
  { id: 'inhibitor_tolerance', name: 'Inhibitor tolerance', family: 'physiology', canonicalUnit: 'g L⁻¹', definition: 'Concentration of the named inhibitor at which growth rate falls by half.', aggregatable: true },
  { id: 'critical_do', name: 'Critical dissolved oxygen', family: 'physiology', canonicalUnit: '%', definition: 'DO below which respiration becomes transport-limited for this organism.', aggregatable: true },
  { id: 'enzyme_activity', name: 'Enzyme specific activity', family: 'pathway', canonicalUnit: '', definition: 'U per mg protein under the stated assay. Assay-dependent and rarely comparable across sources.', aggregatable: false },
  { id: 'cofactor_demand', name: 'Cofactor demand', family: 'pathway', canonicalUnit: 'mol mol⁻¹', definition: 'Moles of the named cofactor consumed per mole of product.', aggregatable: true },
  { id: 'theoretical_yield', name: 'Theoretical yield', family: 'pathway', canonicalUnit: 'mol mol⁻¹', definition: 'Stoichiometric maximum on the stated substrate, cofactor-balanced.', aggregatable: true },
  { id: 'flux_split', name: 'Flux split', family: 'pathway', canonicalUnit: 'fraction', definition: 'Fraction of carbon entering the named branch.', aggregatable: true },
  { id: 'separation_yield', name: 'Separation step yield', family: 'downstream', canonicalUnit: 'fraction', definition: 'Product recovered over product entering the named unit operation.', aggregatable: true },
  { id: 'purity', name: 'Product purity', family: 'downstream', canonicalUnit: '% (w/w)', definition: 'Product over total solids in the isolated stream.', aggregatable: true },
  { id: 'broth_viscosity', name: 'Broth apparent viscosity', family: 'downstream', canonicalUnit: '', definition: 'mPa·s at the stated shear rate. Shear rate is mandatory; a viscosity without one is unit-ambiguous.', aggregatable: false },
  { id: 'capex', name: 'Capital cost', family: 'economics', canonicalUnit: 'USD t⁻¹', definition: 'Installed capital per annual tonne of capacity, with accuracy class stated.', aggregatable: true },
  { id: 'opex', name: 'Operating cost', family: 'economics', canonicalUnit: 'USD t⁻¹', definition: 'Cash operating cost per tonne at the stated factor prices.', aggregatable: true },
  { id: 'minimum_selling_price', name: 'Minimum selling price', family: 'economics', canonicalUnit: 'USD t⁻¹', definition: 'Price at which NPV is zero at the stated discount rate and life.', aggregatable: true },
  { id: 'feedstock_cost', name: 'Feedstock cost', family: 'economics', canonicalUnit: 'USD t⁻¹', definition: 'Delivered cost at the plant gate, at the stated location and date.', aggregatable: true },
  { id: 'import_volume', name: 'Import volume', family: 'economics', canonicalUnit: 't a⁻¹', definition: 'Annual imports under the stated HS code into the stated jurisdiction.', aggregatable: true },
  { id: 'import_cif', name: 'Import CIF value', family: 'economics', canonicalUnit: 'USD t⁻¹', definition: 'Cost, insurance and freight per tonne at the port of entry.', aggregatable: true },
  { id: 'regulatory_class', name: 'Regulatory classification', family: 'regulatory', canonicalUnit: '', definition: 'Classification in the stated jurisdiction. Categorical.', aggregatable: false },
];

export const FIELD_BY_ID: Record<string, FieldDef> = Object.fromEntries(FIELDS.map((f) => [f.id, f]));

// ── Sources ────────────────────────────────────────────────────────────
// Author names, DOIs and venue-issue numbers are synthetic. Venues are real
// journals because a fabricated journal name reads as a fabricated field.

export const SOURCES: Source[] = [
  // --- Corynebacterium / lysine ---
  { id: 'SRC-0001', type: 'journal', title: 'Systems-level analysis of NADPH supply constraints in lysine-overproducing Corynebacterium glutamicum', authors: ['Halvard, T.', 'Osei, N.', 'Brennecke, L.'], year: 2019, venue: 'Metabolic Engineering', doi: '10.9999/me.2019.0417', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0002', type: 'journal', title: 'Oxygen limitation and organic acid overflow in fed-batch L-lysine fermentation', authors: ['Ferreira, M.', 'Adeyeye, K.'], year: 2020, venue: 'Biotechnology and Bioengineering', doi: '10.9999/bit.2020.1188', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0003', type: 'journal', title: 'Temperature shift strategies in amino acid fed-batch processes: a re-examination at high cell density', authors: ['Nakagome, R.', 'Vrolijk, S.'], year: 2022, venue: 'Journal of Biotechnology', doi: '10.9999/jbiotec.2022.0553', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0004', type: 'journal', title: 'Bicarbonate supplementation and anaplerotic flux in pyruvate carboxylase overexpressing strains', authors: ['Sarr, A.', 'Lindqvist, H.'], year: 2021, venue: 'Applied Microbiology and Biotechnology', doi: '10.9999/amb.2021.0904', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0005', type: 'journal', title: 'pH control strategy and lysine export in Corynebacterium glutamicum', authors: ['Berhane, S.'], year: 2018, venue: 'Bioprocess and Biosystems Engineering', doi: '10.9999/bpbse.2018.0231', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0006', type: 'journal', title: 'Growth-rate partitioning between biomass and product in exponentially fed amino acid processes', authors: ['Oyelaran, D.', 'Kask, T.'], year: 2023, venue: 'Biochemical Engineering Journal', doi: '10.9999/bej.2023.0118', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0007', type: 'journal', title: 'Biotin sufficiency, membrane permeability and product spectrum in Corynebacterium', authors: ['Marchetti, P.'], year: 2017, venue: 'Journal of Industrial Microbiology and Biotechnology', doi: '10.9999/jimb.2017.0662', openAccess: false, ingestState: 'catalogued' },
  { id: 'SRC-0008', type: 'thesis', title: 'Scale-down characterisation of dissolved oxygen excursions in amino acid fermentation', authors: ['Uwase, N.'], year: 2024, venue: 'Doctoral thesis, synthetic', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0009', type: 'journal', title: 'Cassava hydrolysate as a fermentation substrate: composition, inhibitors and process implications', authors: ['Abiodun, T.', 'Nkurunziza, J.'], year: 2023, venue: 'Bioresource Technology', doi: '10.9999/biortech.2023.1402', openAccess: true, ingestState: 'parsed' },
  // --- 3-HP ---
  { id: 'SRC-0010', type: 'journal', title: 'Malonyl-CoA reductase fragment engineering for 3-hydroxypropionic acid production', authors: ['Vondra, E.', 'Iwu, C.'], year: 2021, venue: 'Metabolic Engineering', doi: '10.9999/me.2021.0288', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0011', type: 'journal', title: 'β-alanine route to 3-HP: aminotransferase selection and pyruvate cycling', authors: ['Norstrand, K.', 'Diallo, M.'], year: 2022, venue: 'Applied and Environmental Microbiology', doi: '10.9999/aem.2022.0771', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0012', type: 'journal', title: 'Coenzyme B12 dependence as a cost driver in glycerol-based 3-HP processes', authors: ['Perrone, G.'], year: 2020, venue: 'Biotechnology for Biofuels and Bioproducts', doi: '10.9999/btfb.2020.0339', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0013', type: 'journal', title: '3-hydroxypropionaldehyde toxicity and its mitigation in dehydratase-based routes', authors: ['Kask, T.', 'Ferreira, M.'], year: 2019, venue: 'Biotechnology and Bioengineering', doi: '10.9999/bit.2019.0955', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0014', type: 'journal', title: 'Low-pH organic acid production in yeast and the economics of avoided neutralisation', authors: ['Halvard, T.'], year: 2023, venue: 'Biotechnology Advances', doi: '10.9999/biotechadv.2023.0126', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0015', type: 'journal', title: 'Comparative NADPH demand across three 3-HP biosynthetic routes', authors: ['Iwu, C.', 'Brennecke, L.'], year: 2024, venue: 'Metabolic Engineering Communications', doi: '10.9999/mec.2024.0044', openAccess: true, ingestState: 'parsed' },
  // --- capacity / candidates ---
  { id: 'SRC-0016', type: 'journal', title: 'Oxygen transfer in Rushton-agitated vessels at industrial power inputs: a correlation review', authors: ['Bekele, A.'], year: 2021, venue: 'Chemical Engineering Science', doi: '10.9999/ces.2021.0871', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0017', type: 'journal', title: 'Cooling as the binding constraint on aerobic fermentation in tropical climates', authors: ['Nkurunziza, J.', 'Uwase, N.'], year: 2024, venue: 'Biochemical Engineering Journal', doi: '10.9999/bej.2024.0209', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0018', type: 'journal', title: 'Thermophilic lactic acid fermentation of starch hydrolysates without external cooling', authors: ['Diallo, M.'], year: 2022, venue: 'Bioresource Technology', doi: '10.9999/biortech.2022.1119', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0019', type: 'journal', title: 'Rhizobium inoculant production and shelf life in low-infrastructure settings', authors: ['Osei, N.'], year: 2020, venue: 'Applied Soil Ecology', doi: '10.9999/apsoil.2020.0388', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0020', type: 'trade-statistic', title: 'Harmonised System import statistics, synthetic regional aggregate', authors: ['—'], year: 2025, venue: 'Synthetic trade dataset', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0021', type: 'journal', title: 'Xanthan gum rheology and impeller power requirements at production scale', authors: ['Vrolijk, S.'], year: 2018, venue: 'Journal of Food Engineering', doi: '10.9999/jfoodeng.2018.0447', openAccess: false, ingestState: 'catalogued' },
  { id: 'SRC-0022', type: 'journal', title: 'Citric acid fermentation oxygen demand and the consequences of transient limitation', authors: ['Marchetti, P.', 'Sarr, A.'], year: 2019, venue: 'Process Biochemistry', doi: '10.9999/procbio.2019.0612', openAccess: false, ingestState: 'parsed' },
  // --- lignocellulose / greenfield ---
  { id: 'SRC-0023', type: 'journal', title: 'Pretreatment severity, inhibitor formation and downstream fermentability of sugarcane bagasse', authors: ['Adeyeye, K.', 'Perrone, G.'], year: 2023, venue: 'Bioresource Technology', doi: '10.9999/biortech.2023.1288', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0024', type: 'journal', title: 'Furfural and HMF tolerance across industrial fermentation organisms', authors: ['Brennecke, L.'], year: 2021, venue: 'Applied Microbiology and Biotechnology', doi: '10.9999/amb.2021.0771', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0025', type: 'journal', title: 'Organosolv pretreatment with solvent recovery: capital intensity against sugar yield', authors: ['Norstrand, K.'], year: 2022, venue: 'Industrial Crops and Products', doi: '10.9999/indcrop.2022.0533', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0026', type: 'journal', title: 'Two-stream lignocellulose valorisation: pentose to xylitol, hexose to lactate', authors: ['Diallo, M.', 'Abiodun, T.'], year: 2024, venue: 'Green Chemistry', doi: '10.9999/greenchem.2024.0091', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0027', type: 'journal', title: 'Capital cost correlations for modular fermentation plants in the 5,000 to 50,000 t/yr range', authors: ['Bekele, A.', 'Kask, T.'], year: 2023, venue: 'Chemical Engineering Research and Design', doi: '10.9999/cherd.2023.0345', openAccess: false, ingestState: 'parsed' },
  // --- burger decomposition ---
  { id: 'SRC-0028', type: 'journal', title: 'Heme iron and the thermal flavour chemistry of cooked muscle analogues', authors: ['Lindqvist, H.'], year: 2022, venue: 'Food Chemistry', doi: '10.9999/foodchem.2022.1402', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0029', type: 'journal', title: 'Melting profile requirements for structured fat phases in meat analogues', authors: ['Ferreira, M.', 'Osei, N.'], year: 2023, venue: 'Journal of Food Science', doi: '10.9999/jfs.2023.0655', openAccess: true, ingestState: 'parsed' },
  { id: 'SRC-0030', type: 'journal', title: 'Shear-cell texturisation and fibre alignment in high-moisture protein systems', authors: ['Vrolijk, S.', 'Norstrand, K.'], year: 2021, venue: 'Food Hydrocolloids', doi: '10.9999/foodhyd.2021.0288', openAccess: false, ingestState: 'parsed' },
  { id: 'SRC-0031', type: 'journal', title: 'Oleaginous yeast triacylglycerol profiles and their tunability by nitrogen limitation', authors: ['Iwu, C.'], year: 2024, venue: 'Microbial Cell Factories', doi: '10.9999/mcf.2024.0177', openAccess: true, ingestState: 'parsed' },
  // --- bench deposits ---
  { id: 'SRC-0032', type: 'bench-deposit', title: 'RUN-042 through RUN-047, Chapter CH-KGL-01 lysine campaign', authors: ['Uwase, N.'], year: 2026, venue: 'Guild of Applied Life deposit', openAccess: true, ingestState: 'verified' },
  // --- defensive publications ---
  { id: 'SRC-0033', type: 'defensive-publication', title: 'Process region disclosure: reduced dissolved oxygen setpoint with elevated bicarbonate in lysine fed-batch', authors: ['openFerment'], year: 2026, venue: 'Research Disclosure, synthetic', openAccess: true, ingestState: 'verified' },
  { id: 'SRC-0034', type: 'vendor-datasheet', title: 'Disc-stack separator performance envelope, synthetic vendor sheet', authors: ['—'], year: 2024, venue: 'Vendor documentation', openAccess: false, ingestState: 'catalogued' },
];

export const SOURCE_BY_ID: Record<string, Source> = Object.fromEntries(SOURCES.map((s) => [s.id, s]));

// ── Organisms ──────────────────────────────────────────────────────────

export const ORGANISMS: Organism[] = [
  {
    id: 'ORG-CGL-01',
    binomial: 'Corynebacterium glutamicum',
    designation: 'ATCC 13032',
    description: 'The type strain. Wild type, biotin-auxotrophic, the reference background for essentially all amino acid process literature.',
    gramClass: 'gram-positive',
    competence: [
      { capability: 'Lysine biosynthesis, deregulated', status: 'no', basisAccessionIds: ['OF-A-00101'], note: 'Wild type carries feedback-inhibited aspartokinase. Any producing strain is a derivative.' },
      { capability: 'Aerobic respiration to high OUR', status: 'yes', basisAccessionIds: ['OF-A-00121'], note: 'Sustains OUR above 100 mmol L⁻¹ h⁻¹ at high cell density, which is what makes cooling the binding constraint.' },
      { capability: 'Anaerobic growth', status: 'no', basisAccessionIds: ['OF-A-00122'], note: 'Shifts to lactate and succinate under oxygen limitation without growing. Diagnostic, and the basis of the DO exclusion.' },
      { capability: 'Growth above 37 °C', status: 'partial', basisAccessionIds: ['OF-A-00110'], note: 'Growth continues; product yield falls. The exclusion is on yield, not viability.' },
    ],
    optima: { temperatureC: { low: 30, high: 33 }, ph: { low: 6.8, high: 7.4 }, criticalDoPercent: 8 },
    constraints: [
      'Biotin auxotroph — biotin level changes the product spectrum, not just the growth rate.',
      'Four NADPH per lysine. Pentose phosphate flux is the ceiling, and it is not raised by feeding harder.',
      'High OUR means high metabolic heat. In a warm ambient this is a plant constraint before it is a biology constraint.',
    ],
    gras: true,
    regulatoryNote: 'Long history of use in food-grade amino acid manufacture. Feed-grade lysine HCl is an established product class.',
  },
  {
    id: 'ORG-CGL-02',
    binomial: 'Corynebacterium glutamicum',
    designation: 'LYS-3 (synthetic designation)',
    description: 'A production derivative of ATCC 13032 in the demo pool: feedback-resistant aspartokinase, attenuated homoserine dehydrogenase, pyruvate carboxylase and lysine exporter overexpressed, glucose-6-phosphate dehydrogenase deregulated.',
    gramClass: 'gram-positive',
    competence: [
      { capability: 'Lysine biosynthesis, deregulated', status: 'yes', basisAccessionIds: ['OF-A-00102'], note: 'Aspartokinase feedback resistance is the single edit without which nothing else matters.' },
      { capability: 'NADPH supply matched to lysine demand', status: 'partial', basisAccessionIds: ['OF-A-00103'], note: 'Deregulated G6PDH raises PPP flux; the corpus records this as necessary and not sufficient.' },
      { capability: 'Product export', status: 'yes', basisAccessionIds: ['OF-A-00104'], note: 'Exporter overexpression removes intracellular accumulation as the limit.' },
    ],
    optima: { temperatureC: { low: 30, high: 33 }, ph: { low: 6.8, high: 7.4 }, criticalDoPercent: 8 },
    constraints: [
      'Attenuated homoserine dehydrogenase makes the strain threonine- and methionine-limited if the medium is not supplemented.',
      'Everything inherited from ATCC 13032 still applies.',
    ],
    gras: true,
    regulatoryNote: 'Genetically modified production strain; product is purified away from biomass. Feed-additive pathway in most jurisdictions is well-trodden.',
  },
  {
    id: 'ORG-ECO-01',
    binomial: 'Escherichia coli',
    designation: 'K-12 W3110 derivative',
    description: 'The default heterologous host. Fast, tractable, and carries the largest patent overhang of any chassis in the pool.',
    gramClass: 'gram-negative',
    competence: [
      { capability: 'Cytosolic NADPH-dependent reduction at high flux', status: 'partial', basisAccessionIds: ['OF-A-00203'], note: 'Supports the malonyl-CoA route; NADPH regeneration becomes the constraint above moderate flux.' },
      { capability: 'Coenzyme B12 synthesis de novo', status: 'no', basisAccessionIds: ['OF-A-00212'], note: 'B12 must be fed for the glycerol route. This is the cost driver, not a technical blocker.' },
      { capability: 'Low-pH organic acid production', status: 'no', basisAccessionIds: ['OF-A-00215'], note: 'Requires neutralisation, which means salt splitting downstream.' },
    ],
    optima: { temperatureC: { low: 30, high: 37 }, ph: { low: 6.7, high: 7.2 }, criticalDoPercent: 5 },
    constraints: ['Acetate overflow above μ ≈ 0.25 h⁻¹.', 'Endotoxin removal burden for any product entering a regulated stream.'],
    gras: false,
    regulatoryNote: 'Not GRAS as an organism. Purified products from E. coli are routine; whole-cell or minimally-purified products are not.',
  },
  {
    id: 'ORG-SCE-01',
    binomial: 'Saccharomyces cerevisiae',
    designation: 'CEN.PK113-7D',
    description: 'The low-pH chassis. Slower and lower-yielding on most routes, and it makes the downstream economics of an organic acid completely different.',
    gramClass: 'yeast',
    competence: [
      { capability: 'Production below pH 4', status: 'yes', basisAccessionIds: ['OF-A-00216'], note: 'The reason to accept a yield penalty: 3-HP pKa is 4.5, so producing below it avoids the neutralisation-and-splitting loop.' },
      { capability: 'Cytosolic acetyl-CoA at high flux', status: 'partial', basisAccessionIds: ['OF-A-00217'], note: 'Native routing is mitochondrial; cytosolic supply requires engineering and carries an ATP cost.' },
    ],
    optima: { temperatureC: { low: 28, high: 33 }, ph: { low: 3.5, high: 6.0 } },
    constraints: ['Crabtree effect diverts carbon to ethanol at high glucose.', 'Lower volumetric productivity than bacterial hosts on every route in this pool.'],
    gras: true,
    regulatoryNote: 'GRAS. The easiest regulatory path of any chassis here.',
  },
  {
    id: 'ORG-KPH-01',
    binomial: 'Komagataella phaffii',
    designation: 'GS115',
    description: 'Secretion host. Present in this pool for the heme-protein branch of the burger decomposition, where it is also the most heavily enclosed option.',
    gramClass: 'yeast',
    competence: [
      { capability: 'Secretion of heterologous protein at gram scale', status: 'yes', basisAccessionIds: ['OF-A-00502'], note: 'Established. The constraint on this branch is not technical.' },
      { capability: 'Heme cofactor loading of a recombinant globin', status: 'partial', basisAccessionIds: ['OF-A-00503'], note: 'Requires heme pathway augmentation or exogenous supply; occupancy is the quality attribute that matters.' },
    ],
    optima: { temperatureC: { low: 28, high: 30 }, ph: { low: 5.0, high: 6.5 } },
    constraints: ['Methanol induction carries a fire-safety and utility burden at scale.', 'Hypermannosylation is a downstream problem for any secreted product.'],
    gras: false,
    regulatoryNote: 'Widely used; product-by-product approval rather than organism-level clearance.',
  },
  {
    id: 'ORG-BCG-01',
    binomial: 'Bacillus coagulans',
    designation: 'DSM 1 derivative',
    description: 'Thermophilic, homofermentative lactic acid producer that ferments both pentose and hexose. The chassis that makes tropical cooling stop being the binding constraint.',
    gramClass: 'gram-positive',
    competence: [
      { capability: 'Growth and production at 52–55 °C', status: 'yes', basisAccessionIds: ['OF-A-00305'], note: 'A 25 °C driving force against 28 °C cooling-tower water instead of 2 °C. This single fact reorders the capacity screen.' },
      { capability: 'Pentose utilisation', status: 'yes', basisAccessionIds: ['OF-A-00406'], note: 'Ferments xylose and arabinose, which is why the two-stream bagasse concept works at all.' },
      { capability: 'Inhibitor tolerance to furfural and HMF', status: 'partial', basisAccessionIds: ['OF-A-00404'], note: 'Tolerant relative to yeast, and pretreatment severity still has to be held down.' },
      { capability: 'High-OUR aerobic operation', status: 'no', basisAccessionIds: ['OF-A-00306'], note: 'Microaerophilic. Low heat load is the point, and it forecloses any aerobic product.' },
    ],
    optima: { temperatureC: { low: 50, high: 55 }, ph: { low: 5.5, high: 6.5 } },
    constraints: ['Thermophilic operation needs a heated seed train and raises SIP cycle cost.', 'Homofermentative on the named substrates; a mixed feed shifts the product spectrum.'],
    gras: true,
    regulatoryNote: 'Established as a probiotic and as a lactic acid production organism. Straightforward.',
  },
  {
    id: 'ORG-RTO-01',
    binomial: 'Rhodosporidium toruloides',
    designation: 'IFO 0880',
    description: 'Oleaginous, unusually tolerant of lignocellulosic hydrolysate inhibitors. Present for both the greenfield and the structured-fat branch.',
    gramClass: 'yeast',
    competence: [
      { capability: 'Growth on unconditioned hydrolysate', status: 'yes', basisAccessionIds: ['OF-A-00405'], note: 'The tolerance that removes a detoxification unit operation from the block flow.' },
      { capability: 'Lipid accumulation above 50 % of dry weight', status: 'yes', basisAccessionIds: ['OF-A-00507'], note: 'Under nitrogen limitation. The profile is tunable, which is what the fat-phase branch needs.' },
    ],
    optima: { temperatureC: { low: 28, high: 32 }, ph: { low: 4.5, high: 6.5 } },
    constraints: ['Aerobic and high-OUR during lipid accumulation — fails the same cooling test as any other aerobe in a warm ambient.', 'Cell disruption required; lipid recovery is the cost centre.'],
    gras: false,
    regulatoryNote: 'No established food clearance. A regulatory programme, not a filing.',
  },
  {
    id: 'ORG-PDN-01',
    binomial: 'Pseudomonas denitrificans',
    designation: 'production derivative',
    description: 'Native coenzyme B12 producer, which is the one thing that makes the glycerol route to 3-HP economically arguable.',
    gramClass: 'gram-negative',
    competence: [
      { capability: 'De novo coenzyme B12 synthesis', status: 'yes', basisAccessionIds: ['OF-A-00213'], note: 'Removes the fed-B12 cost line that dominates the E. coli version of the same route.' },
      { capability: '3-HPA tolerance', status: 'partial', basisAccessionIds: ['OF-A-00214'], note: 'The aldehyde intermediate is toxic in every host. Tolerance sets the achievable titer.' },
    ],
    optima: { temperatureC: { low: 28, high: 32 }, ph: { low: 6.8, high: 7.5 } },
    constraints: ['Slower than E. coli on every metric except the one that matters here.', 'Less genetic toolkit maturity.'],
    gras: false,
    regulatoryNote: 'Industrial B12 production organism. Product-purified route only.',
  },
  {
    id: 'ORG-FVE-01',
    binomial: 'Fusarium venenatum',
    designation: 'A3/5',
    description: 'Filamentous mycoprotein organism. Present in the fibrous-matrix branch as the alternative to texturising an isolated protein.',
    gramClass: 'filamentous-fungus',
    competence: [
      { capability: 'Native fibrous morphology', status: 'yes', basisAccessionIds: ['OF-A-00509'], note: 'Hyphal alignment gives bite without an extrusion step, which removes the most patent-dense unit operation from the branch.' },
      { capability: 'Continuous culture at production scale', status: 'yes', basisAccessionIds: ['OF-A-00510'], note: 'Established, and it carries a colonial-mutant stability constraint that sets run length.' },
    ],
    optima: { temperatureC: { low: 28, high: 30 }, ph: { low: 5.8, high: 6.2 } },
    constraints: ['Non-Newtonian broth. Power input and oxygen transfer both degrade as biomass rises.', 'RNA content must be reduced for food use, which is a real unit operation.'],
    gras: false,
    regulatoryNote: 'Approved as a food ingredient in several jurisdictions under specific process conditions. Process-linked approval, so a process change is a regulatory event.',
  },
];

export const ORGANISM_BY_ID: Record<string, Organism> = Object.fromEntries(ORGANISMS.map((o) => [o.id, o]));

// ── The plant ──────────────────────────────────────────────────────────

export const PLANTS: Plant[] = [
  {
    id: 'PLT-KGL-01',
    name: 'Kigali contract fermentation facility',
    location: { city: 'Kigali', country: 'Rwanda', jurisdiction: 'RW', ambientC: 26 },
    vessels: {
      count: 2,
      workingVolumeM3: 5,
      material: '316L stainless, jacketed',
      sipCapable: true,
      impeller: 'Rushton, 3 stages',
      hOverD: 2.0,
      installedPowerPerVolume: 1500,
      maxAerationVvm: 1.0,
    },
    utilities: {
      chilledWaterKW: 80,
      chilledWaterSupplyC: 12,
      coolingTowerSupplyC: 28,
      steamKgPerH: 350,
      gridReliability: 'intermittent',
      outageProfile: 'Two to four unplanned interruptions per month, typically under 20 minutes. Generator start is manual.',
    },
    downstream: [
      { unit: 'Disc-stack centrifuge', capacity: '4 m³ h⁻¹ at 8,000 g' },
      { unit: 'Spray dryer', capacity: '50 kg h⁻¹ evaporative' },
      { unit: 'Plate-and-frame filtration', capacity: '12 m² area' },
    ],
    feedstocksWithinKm: [
      { name: 'Cassava starch', km: 60, costPerTonneUSD: 380, accessionId: 'OF-A-00301' },
      { name: 'Coffee pulp', km: 45, costPerTonneUSD: 15, accessionId: 'OF-A-00302' },
      { name: 'Brewery spent grain', km: 12, costPerTonneUSD: 25, accessionId: 'OF-A-00303' },
      { name: 'Liquid whey', km: 80, costPerTonneUSD: 8, accessionId: 'OF-A-00304' },
    ],
  },
];

export const PLANT_BY_ID: Record<string, Plant> = Object.fromEntries(PLANTS.map((p) => [p.id, p]));

// ── Trade reference ────────────────────────────────────────────────────
// HS codes are real. Volumes and values are synthetic and marked as such on
// every Accession derived from them.

export const HS_CODES: { code: string; description: string; accessionIds: string[] }[] = [
  { code: '2922.41', description: 'Lysine and its esters; salts thereof', accessionIds: ['OF-A-00310', 'OF-A-00311'] },
  { code: '2918.11', description: 'Lactic acid, its salts and esters', accessionIds: ['OF-A-00312', 'OF-A-00313'] },
  { code: '2918.14', description: 'Citric acid', accessionIds: ['OF-A-00314'] },
  { code: '3507.90', description: 'Enzymes; enzyme preparations not elsewhere specified', accessionIds: ['OF-A-00315'] },
  { code: '2102.20', description: 'Inactive yeasts; other single-cell micro-organisms, dead', accessionIds: ['OF-A-00316'] },
  { code: '3101.00', description: 'Fertilisers of animal or vegetable origin, including microbial inoculants', accessionIds: ['OF-A-00317'] },
  { code: '2905.44', description: 'D-glucitol (sorbitol) — proxy line used for polyol imports including xylitol', accessionIds: ['OF-A-00318'] },
];

// ── Guild chapters ─────────────────────────────────────────────────────

export const CHAPTERS = [
  { id: 'CH-KGL-01', name: 'Ubuzima Applied Bioprocess', city: 'Kigali', country: 'Rwanda' },
  { id: 'CH-SYR-02', name: 'Onondaga Bench Collective', city: 'Syracuse', country: 'United States' },
  { id: 'CH-LPZ-03', name: 'Elsterwerk Labor für Bioverfahren', city: 'Leipzig', country: 'Germany' },
  { id: 'CH-BLR-04', name: 'Nandi Hills Fermentation Unit', city: 'Bengaluru', country: 'India' },
];

/**
 * Sanity check run at load. A broken cross-reference here propagates into all
 * six archetypes, so it fails loudly rather than rendering an error chip.
 */
export function assertCoreIntegrity(accessions: Accession[]): void {
  const ids = new Set(accessions.map((a) => a.id));
  const missing: string[] = [];
  for (const o of ORGANISMS) {
    for (const c of o.competence) for (const id of c.basisAccessionIds) if (!ids.has(id)) missing.push(`${o.id} → ${id}`);
  }
  for (const p of PLANTS) for (const f of p.feedstocksWithinKm) if (!ids.has(f.accessionId)) missing.push(`${p.id} → ${f.accessionId}`);
  for (const h of HS_CODES) for (const id of h.accessionIds) if (!ids.has(id)) missing.push(`HS ${h.code} → ${id}`);
  for (const a of accessions) if (!SOURCE_BY_ID[a.sourceId]) missing.push(`${a.id} → source ${a.sourceId}`);
  if (missing.length) throw new Error(`[of] broken core references:\n${missing.join('\n')}`);
}
