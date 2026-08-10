// openFerment Sim — scenarios and cost models (OF-DES-001 §17).
//
// SYNTHETIC CONTENT. These are authored, spreadsheet-grade reduced-form models
// written for the working simulation. They are deterministic and auditable, but
// they are not validated process designs and no number here should be used to
// cost a real plant. Every headline the UI renders from them carries the
// subtitle "Demo model v0 — illustrative economics, not validated." (§20).
//
// Contract (src/data/types.ts):
//   evaluate(point) returns the six cost lines in US$ per kg of product. The
//   engine SUMS them to the minimum selling price (src/engine/grids.ts), so each
//   line is authored as a genuine contribution, never as a share of a total.
//
// Shape of every model:
//   annual product (kg/yr) = batches per year × working volume × concentration
//                            × the mass yield of the recovery train
//   capex        installed capital scaled as (scale)^0.6, annualised at a
//                capital charge factor, divided by annual product
//   media        substrate charged per kg of biomass formed (so it is density
//                independent) plus a salt/buffer package charged per litre of
//                broth (so it falls as 1/density)
//   utilities    agitation, aeration and illumination charged per litre of
//                broth, therefore also 1/density, plus a product-side term
//   labor        a fixed crew spread over more output as scale rises
//   downstream   harvest charged per litre plus conversion charged per kg,
//                divided by the downstream yield where the model carries one
//   other        small fixed overhead per kg
//
// All lines are strictly positive and finite at every grid coordinate.

import type { Scenario, CostModel, CostLine, ScenarioDim } from './types';

/** Fraction of installed capital charged to each operating year (§17.1). */
const CAPITAL_CHARGE_FACTOR = 0.12;
/** Annual operating time. 330 days leaves 35 days for turnaround and shutdown. */
const OPERATING_DAYS = 330;
const OPERATING_HOURS = OPERATING_DAYS * 24;

// ═══════════════════════════════════════════════════════════════════════════
// S1 — Chlamydomonas reinhardtii cw15, mixotrophic on acetate, protein isolate
// ═══════════════════════════════════════════════════════════════════════════

/** Reference cultivation scale for the S1 capital and labour correlations. */
const S1_REF_SCALE_M3 = 65;
/** 36 h mixotrophic batch on acetate plus 12 h drain, CIP and refill. */
const S1_CYCLE_HOURS = 48;
const S1_BATCHES_PER_YEAR = OPERATING_HOURS / S1_CYCLE_HOURS;

/**
 * Mass of protein isolate obtained per kg of dry biomass in the reactor:
 * centrifuge recovery × bead-mill disruption × protein content × the yield of
 * the extraction, precipitation and drying train.
 */
const S1_HARVEST_RECOVERY = 0.964;
const S1_DISRUPTION_EFFICIENCY = 0.942;
const S1_PROTEIN_CONTENT = 0.384;
const S1_ISOLATE_TRAIN_YIELD = 0.885;
const S1_MASS_YIELD =
  S1_HARVEST_RECOVERY * S1_DISRUPTION_EFFICIENCY * S1_PROTEIN_CONTENT * S1_ISOLATE_TRAIN_YIELD;

const S1_ACETATE_PRICE = 1.11; // $ per kg acetate delivered
const S1_YIELD_ON_ACETATE = 0.45; // g dry biomass per g acetate
const S1_SALTS_PER_LITRE = 0.0074; // $ per litre of medium, buffer and trace metals
const S1_UTILITIES_PER_LITRE = 0.003086; // $ per litre per batch, agitation + air + light
const S1_UTILITIES_PER_KG = 1.68; // $ per kg, drying and product-side services
const S1_HARVEST_PER_LITRE = 0.002469; // $ per litre, centrifugation and pre-concentration
const S1_CONVERSION_PER_KG = 21.8; // $ per kg, milling, extraction, UF/DF, spray drying
const S1_CAPITAL_AT_REF = 270000; // $ installed at the 65 m³ reference scale
const S1_LABOUR_AT_REF = 11.0; // $ per kg at 65 m³ and 1 g L⁻¹
const S1_OVERHEAD_SCALED = 2.84; // $ per kg at the reference scale
const S1_OVERHEAD_FIXED = 1.29; // $ per kg, scale independent

function evaluateS1(point: Record<string, number>): Record<CostLine, number> {
  const density = point.density;
  const mediaCost = point.mediaCost;
  const scale = point.scale;
  const scaleRatio = scale / S1_REF_SCALE_M3;

  // kg of isolate per year, and the litres of broth behind each kg of it.
  const annualProduct = S1_BATCHES_PER_YEAR * scale * density * S1_MASS_YIELD;
  const litresPerKg = 1000 / (density * S1_MASS_YIELD);

  const installedCapital = S1_CAPITAL_AT_REF * Math.pow(scaleRatio, 0.6);
  const capex = (installedCapital * CAPITAL_CHARGE_FACTOR) / annualProduct;

  // Acetate is charged against biomass formed, so it does not move with density;
  // the salt and buffer package is charged against broth volume, so it does.
  const substrate = S1_ACETATE_PRICE / S1_YIELD_ON_ACETATE / S1_MASS_YIELD;
  const media = mediaCost * (substrate + S1_SALTS_PER_LITRE * litresPerKg);

  const utilities = S1_UTILITIES_PER_LITRE * litresPerKg + S1_UTILITIES_PER_KG;

  const labor = S1_LABOUR_AT_REF * Math.pow(scaleRatio, -0.55) / density;

  const downstream =
    (S1_HARVEST_PER_LITRE * litresPerKg + S1_CONVERSION_PER_KG) * Math.pow(scaleRatio, -0.12);

  const other = S1_OVERHEAD_SCALED * Math.pow(scaleRatio, -0.22) + S1_OVERHEAD_FIXED;

  return { capex, media, utilities, labor, downstream, other };
}

// ═══════════════════════════════════════════════════════════════════════════
// S2 — Komagataella phaffii GS115, fed-batch, secreted recombinant protein
// ═══════════════════════════════════════════════════════════════════════════

const S2_REF_SCALE_M3 = 110;
/** 24 h glycerol batch, 12 h glycerol fed-batch, 74 h methanol induction, 22 h turnaround. */
const S2_CYCLE_HOURS = 132;
const S2_BATCHES_PER_YEAR = OPERATING_HOURS / S2_CYCLE_HOURS;

const S2_MEDIA_PER_LITRE = 0.155; // $ per litre of final broth: salts, trace, glycerol, methanol
const S2_UTILITIES_PER_LITRE = 0.035; // $ per litre: agitation, air, chilled water, sterilisation
const S2_UTILITIES_PER_KG = 1.5; // $ per kg, product-side cold chain and services
const S2_CAPITAL_AT_REF = 10_600_000; // $ installed at the 110 m³ reference scale
const S2_CREW_AT_REF = 850_000; // $ per year of direct labour at 110 m³
const S2_CLARIFY_PER_LITRE = 0.042; // $ per litre: centrifugation, depth filtration, UF/DF
const S2_PURIFY_PER_KG = 24; // $ per kg fed to polishing: resin, buffers, filters
const S2_OVERHEAD_FIXED = 3.5;
const S2_OVERHEAD_SCALED = 4.0;

function evaluateS2(point: Record<string, number>): Record<CostLine, number> {
  const titer = point.titer;
  const scale = point.scale;
  const dspYield = point.dspYield;
  const scaleRatio = scale / S2_REF_SCALE_M3;

  // Each m³ of broth at t g L⁻¹ delivers t × dspYield kg of purified protein.
  const annualProduct = S2_BATCHES_PER_YEAR * scale * titer * dspYield;
  const litresPerKg = 1000 / (titer * dspYield);

  const installedCapital = S2_CAPITAL_AT_REF * Math.pow(scaleRatio, 0.6);
  const capex = (installedCapital * CAPITAL_CHARGE_FACTOR) / annualProduct;

  const media = S2_MEDIA_PER_LITRE * litresPerKg;
  const utilities = S2_UTILITIES_PER_LITRE * litresPerKg + S2_UTILITIES_PER_KG;
  const labor = (S2_CREW_AT_REF * Math.pow(scaleRatio, 0.4)) / annualProduct;

  // Clarification is charged against broth volume; chromatography is charged
  // against the protein loaded onto the column, which is 1/dspYield per kg sold.
  const downstream =
    (S2_CLARIFY_PER_LITRE * litresPerKg + S2_PURIFY_PER_KG / dspYield) *
    Math.pow(scaleRatio, -0.1);

  const other = S2_OVERHEAD_FIXED + S2_OVERHEAD_SCALED * Math.pow(scaleRatio, -0.25);

  return { capex, media, utilities, labor, downstream, other };
}

/**
 * The authored engine fails to close its oxygen and heat balances at the single
 * coordinate where a dilute broth is processed at the largest modelled scale
 * with the poorest recovery: the clarified stream exceeds the modelled hold
 * capacity and the solver runs out of iterations (§17.3).
 */
function nonConvergentS2(point: Record<string, number>): boolean {
  return point.titer <= 5 && point.dspYield <= 0.55 && point.scale >= 200;
}

// ═══════════════════════════════════════════════════════════════════════════
// S3 — Flat-panel photobioreactor, photoautotrophic biomass (route comparison)
// ═══════════════════════════════════════════════════════════════════════════

const S3_REF_SCALE_M3 = 70;
const S3_REF_LIGHT_PATH_CM = 6;
/** Steady-state dry cell weight achievable at the 6 cm reference light path. */
const S3_REF_DENSITY = 4.6;
/**
 * Volumetric productivity is areal productivity divided by light path, so a
 * panel half as thick is twice as productive per litre. 27 g m⁻² d⁻¹ over a
 * two-sided panel gives 5.4 / L(cm) in g L⁻¹ d⁻¹.
 */
const S3_AREAL_COEFFICIENT = 5.4;
const S3_TURNAROUND_DAYS = 0.5;
const S3_HARVEST_RECOVERY = 0.964;
const S3_DRYING_YIELD = 0.97;
const S3_MASS_YIELD = S3_HARVEST_RECOVERY * S3_DRYING_YIELD;

const S3_CO2_PER_KG_BIOMASS = 0.2492; // $ per kg dry biomass at 65 % carbon capture
const S3_SALTS_PER_LITRE = 0.0018; // $ per litre: nitrate, phosphate, trace metals
const S3_POWER_PER_LITRE_DAY = 0.001518; // $ per litre per cultivation day
const S3_UTILITIES_PER_KG = 2.6; // $ per kg, drying and product-side services
const S3_CAPITAL_AT_REF = 2_400_000; // $ installed at 70 m³ and a 6 cm light path
const S3_CREW_AT_REF = 220_000; // $ per year of direct labour at 70 m³
const S3_HARVEST_PER_LITRE = 0.0028; // $ per litre, disc-stack centrifugation
const S3_DRYING_PER_KG = 6.5; // $ per kg, drum drying, milling and packaging
const S3_OVERHEAD_FIXED = 1.0;
const S3_OVERHEAD_SCALED = 2.6;

function evaluateS3(point: Record<string, number>): Record<CostLine, number> {
  const lightPath = point.lightPath;
  const scale = point.scale;
  const scaleRatio = scale / S3_REF_SCALE_M3;
  const pathRatio = S3_REF_LIGHT_PATH_CM / lightPath;

  // Thin panels hold more cells per litre and turn over faster; they also cost
  // disproportionately more per unit volume, which is the trade-off S3 exists
  // to display against the stirred mixotrophic route in S1.
  const density = S3_REF_DENSITY * Math.pow(pathRatio, 0.45);
  const volumetricRate = S3_AREAL_COEFFICIENT / lightPath; // g L⁻¹ d⁻¹
  const cultivationDays = density / volumetricRate;
  const cyclesPerYear = OPERATING_DAYS / (cultivationDays + S3_TURNAROUND_DAYS);

  const annualProduct = cyclesPerYear * scale * density * S3_MASS_YIELD;
  const litresPerKg = 1000 / (density * S3_MASS_YIELD);

  const installedCapital =
    S3_CAPITAL_AT_REF * Math.pow(scaleRatio, 0.65) * Math.pow(pathRatio, 1.1);
  const capex = (installedCapital * CAPITAL_CHARGE_FACTOR) / annualProduct;

  const media = S3_CO2_PER_KG_BIOMASS / S3_MASS_YIELD + S3_SALTS_PER_LITRE * litresPerKg;

  // Circulation and gas transfer run continuously, so the utility charge follows
  // cultivation days per kg, which collapses to 1 / volumetric productivity.
  const utilities = S3_POWER_PER_LITRE_DAY * cultivationDays * litresPerKg + S3_UTILITIES_PER_KG;

  const labor = (S3_CREW_AT_REF * Math.pow(scaleRatio, 0.4)) / annualProduct;

  const downstream =
    S3_HARVEST_PER_LITRE * litresPerKg + S3_DRYING_PER_KG * Math.pow(scaleRatio, -0.12);

  const other = S3_OVERHEAD_FIXED + S3_OVERHEAD_SCALED * Math.pow(scaleRatio, -0.2);

  return { capex, media, utilities, labor, downstream, other };
}

// ═══════════════════════════════════════════════════════════════════════════
// Dimension declarations — shared between each model and its scenario
// ═══════════════════════════════════════════════════════════════════════════

const S1_DIMS: ScenarioDim[] = [
  {
    key: 'density',
    label: 'Final biomass density',
    unit: 'g L⁻¹',
    values: [1, 2, 3, 4, 5, 6],
    sourceRecordId: 'ex-0050',
  },
  { key: 'mediaCost', label: 'Media cost factor', unit: '× base', values: [0.6, 0.8, 1.0, 1.2, 1.4, 1.6] },
  { key: 'scale', label: 'Cultivation scale', unit: 'm³', values: [10, 37, 65, 92, 120] },
];

const S2_DIMS: ScenarioDim[] = [
  {
    key: 'titer',
    label: 'Product titer',
    unit: 'g L⁻¹',
    values: [5, 9, 13, 17, 21, 26, 30],
    sourceRecordId: 'ex-0091',
  },
  { key: 'scale', label: 'Fermenter scale', unit: 'm³', values: [20, 65, 110, 155, 200] },
  { key: 'dspYield', label: 'Downstream yield', unit: 'fraction', values: [0.55, 0.65, 0.75, 0.85] },
];

const S3_DIMS: ScenarioDim[] = [
  { key: 'lightPath', label: 'Light path / density proxy', unit: 'cm', values: [2, 4, 6, 8, 10] },
  { key: 'scale', label: 'Cultivation scale', unit: 'm³', values: [10, 40, 70, 100, 130] },
];

const S1_REFERENCE_POINT = { density: 3, mediaCost: 1.0, scale: 65 };
const S2_REFERENCE_POINT = { titer: 13, scale: 110, dspYield: 0.75 };
const S3_REFERENCE_POINT = { lightPath: 6, scale: 70 };

// ═══════════════════════════════════════════════════════════════════════════
// Cost models
// ═══════════════════════════════════════════════════════════════════════════

export const COST_MODELS: CostModel[] = [
  {
    modelId: 'S1',
    dims: S1_DIMS,
    referencePoint: S1_REFERENCE_POINT,
    evaluate: evaluateS1,
    sensitivity: [
      // One-at-a-time perturbation about the reference point. Recoveries are
      // perturbed to their physical ceiling rather than a symmetric +20 %,
      // which is why several rows are strongly asymmetric.
      { assumption: 'Downstream conversion cost per kg', lowPct: -7.9, hiPct: 7.9 },
      { assumption: 'Cell disruption efficiency', lowPct: 13.3, hiPct: -2.8 },
      { assumption: 'Protein content of harvested biomass', lowPct: 12.6, hiPct: -8.4 },
      { assumption: 'Harvest recovery', lowPct: 12.6, hiPct: -1.8 },
      { assumption: 'Biomass yield on acetate', lowPct: 3.6, hiPct: -2.4 },
      { assumption: 'Medium salt and buffer package cost', lowPct: -2.9, hiPct: 2.9 },
      { assumption: 'Installed capital intensity', lowPct: -1.2, hiPct: 1.2 },
    ],
  },
  {
    modelId: 'S2',
    dims: S2_DIMS,
    referencePoint: S2_REFERENCE_POINT,
    evaluate: evaluateS2,
    nonConvergent: nonConvergentS2,
    sensitivity: [
      { assumption: 'Annual operating time', lowPct: 8.6, hiPct: -5.7 },
      { assumption: 'Batch cycle time', lowPct: -7.6, hiPct: 7.6 },
      { assumption: 'Chromatography resin and buffer cost', lowPct: -6.4, hiPct: 6.4 },
      { assumption: 'Installed capital base', lowPct: -4.0, hiPct: 4.0 },
      { assumption: 'Fermentation medium cost', lowPct: -3.3, hiPct: 3.3 },
      { assumption: 'Direct labour cost', lowPct: -2.7, hiPct: 2.7 },
      { assumption: 'Aeration and agitation power draw', lowPct: -0.9, hiPct: 0.9 },
    ],
  },
  {
    modelId: 'S3',
    dims: S3_DIMS,
    referencePoint: S3_REFERENCE_POINT,
    evaluate: evaluateS3,
    sensitivity: [
      { assumption: 'Harvest recovery', lowPct: 17.9, hiPct: -2.6 },
      { assumption: 'Areal biomass productivity', lowPct: 15.7, hiPct: -10.4 },
      { assumption: 'Installed photobioreactor capital', lowPct: -7.3, hiPct: 7.3 },
      { assumption: 'Direct labour cost', lowPct: -5.6, hiPct: 5.6 },
      { assumption: 'Drying and packaging cost per kg', lowPct: -2.9, hiPct: 2.9 },
      { assumption: 'Steady-state density at the reference light path', lowPct: 2.0, hiPct: -1.4 },
      { assumption: 'Circulation and gas-transfer power draw', lowPct: -0.8, hiPct: 0.8 },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════════════
// Scenarios
// ═══════════════════════════════════════════════════════════════════════════

const DEMO_BASIS = 'Order-of-magnitude estimate for the demo model — not derived from the corpus.';

export const SCENARIOS: Scenario[] = [
  {
    id: 'sc-s1',
    modelId: 'S1',
    name: 'Mixotrophic cw15 protein isolate',
    description:
      'Stirred mixotrophic cultivation of Chlamydomonas reinhardtii cw15 on acetate, harvested by disc-stack centrifugation and converted to a protein isolate by bead milling, alkaline extraction and spray drying. Media cost dominates the delivered price below about 2 g L⁻¹, where the buffer and salt package is charged against a large volume of broth for very little biomass.',
    product: 'Algal protein isolate',
    dims: S1_DIMS,
    point: { ...S1_REFERENCE_POINT },
    pinned: false,
    assumptions: [
      {
        label: 'Specific growth rate, mixotrophic on acetate',
        value: 0.118,
        unit: 'h⁻¹',
        provenance: 'gold',
        recordId: 'ex-0001',
        note: 'Sets how quickly a batch reaches its target density and therefore how many batches the plant turns over in a year; a 20 % error here moves the capital and labour lines by roughly the same fraction.',
      },
      {
        label: 'Biomass yield on acetate (Y_X/S)',
        value: 0.45,
        unit: 'g g⁻¹',
        provenance: 'verified',
        recordId: 'ex-0087',
        note: 'Grams of dry biomass per gram of acetate consumed, taken from the fed-batch harmonised baseline rather than a batch culture, because a plant would not be run in a regime that discards a quarter of its carbon.',
      },
      {
        label: 'Protein content of harvested biomass',
        value: 38.4,
        unit: '% DW',
        provenance: 'gold',
        recordId: 'ex-0062',
        note: 'Total protein as a percentage of dry weight by the Lowry assay; it fixes how much isolate a kilogram of biomass can yield, so it divides straight into every cost line.',
      },
      {
        label: 'Harvest recovery, disc-stack centrifuge',
        value: 96.4,
        unit: '%',
        provenance: 'gold',
        recordId: 'ex-0046',
        note: 'Fraction of culture biomass reaching the disruption step, from a pilot-scale gravimetric closure rather than a vendor specification; losses here are unrecoverable and propagate to every downstream line.',
      },
      {
        label: 'Cell disruption efficiency, bead mill',
        value: 94.2,
        unit: '%',
        provenance: 'gold',
        recordId: 'ex-0043',
        note: 'Fraction of cells lysed at a 12 m s⁻¹ tip speed; unlysed cells carry their protein into the spent-solids stream, so this is the second most influential physical assumption in the model.',
      },
      {
        label: 'Medium Tris base concentration',
        value: 2.42,
        unit: 'g L⁻¹',
        provenance: 'gold',
        recordId: 'ex-0005',
        note: 'Tris is the single most expensive component of the standard acetate medium and is the main reason the salt package is charged per litre rather than per kilogram of biomass.',
      },
      {
        label: 'Medium ammonium chloride concentration',
        value: 0.375,
        unit: 'g L⁻¹',
        provenance: 'gold',
        recordId: 'ex-0006',
        note: 'The nitrogen source in the reference medium; it is in excess at harvest in the source study, which is why the model assumes protein content is not nitrogen limited.',
      },
      {
        label: 'Medium potassium phosphate concentration',
        value: 1.61,
        unit: 'g L⁻¹',
        provenance: 'gold',
        recordId: 'ex-0010',
        note: 'Phosphate is the second-largest contributor to the salt package cost and the component most likely to be reformulated when the media cost factor is moved below 1.0.',
      },
      {
        label: 'Isolate train yield (extraction to dried powder)',
        value: 88.5,
        unit: '%',
        provenance: 'demo',
        note: `Protein surviving alkaline extraction, isoelectric precipitation, diafiltration and spray drying. ${DEMO_BASIS}`,
      },
      {
        label: 'Acetate delivered price',
        value: 1.11,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Bulk technical-grade acetate at the plant gate; combined with the yield on acetate it sets the density-independent part of the media line. ${DEMO_BASIS}`,
      },
      {
        label: 'Salt, buffer and trace metal package',
        value: 0.0074,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Everything in the medium except the carbon source, charged against broth volume, which is why this term dominates at 1 g L⁻¹ and nearly vanishes at 6 g L⁻¹. ${DEMO_BASIS}`,
      },
      {
        label: 'Cultivation utilities per batch',
        value: 0.003086,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Agitation, aeration and supplemental illumination for a 36 h batch at roughly 0.67 kW m⁻³; like the salt package it is a per-litre charge and therefore falls as 1/density. ${DEMO_BASIS}`,
      },
      {
        label: 'Drying and product-side utilities',
        value: 1.68,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Evaporative load of taking a 20 % solids paste to a stable powder plus product-side chilling; charged against product mass, so it does not move with density. ${DEMO_BASIS}`,
      },
      {
        label: 'Harvest and pre-concentration consumables',
        value: 0.002469,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Centrifuge power, bowl wear and membrane replacement, charged against the broth volume that must physically pass the separation each batch. ${DEMO_BASIS}`,
      },
      {
        label: 'Downstream conversion cost per kg of isolate',
        value: 21.8,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Bead-milling energy and media wear, extraction chemicals, diafiltration membranes and dryer operation and maintenance; this is the largest single line at high density and the top of the tornado. ${DEMO_BASIS}`,
      },
      {
        label: 'Installed capital at the 65 m³ reference scale',
        value: 4154,
        unit: '$ m⁻³',
        provenance: 'demo',
        note: `Reduced-form intensity for a simple stirred mixotrophic train with basic instrumentation; it is well below vendor pricing for closed photobioreactor systems and must not be used for design. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital scaling exponent',
        value: 0.6,
        unit: '',
        provenance: 'demo',
        note: `Installed capital rises as scale raised to this power, so capital per kilogram falls as scale to the power minus 0.4 once the extra output is counted. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital charge factor',
        value: 0.12,
        unit: 'yr⁻¹',
        provenance: 'demo',
        note: `Fraction of installed capital charged to each operating year, standing in for depreciation, return and maintenance capital in a single term. ${DEMO_BASIS}`,
      },
      {
        label: 'Annual operating time',
        value: 330,
        unit: 'd',
        provenance: 'demo',
        note: `Days the plant is in production, leaving 35 days for planned shutdown; it converts installed capacity into the annual output that every fixed cost is divided by. ${DEMO_BASIS}`,
      },
      {
        label: 'Batch cycle time',
        value: 48,
        unit: 'h',
        provenance: 'demo',
        note: `36 h of mixotrophic growth plus 12 h of drain, clean-in-place and refill; shortening it raises annual output and dilutes capital and labour without touching the media line. ${DEMO_BASIS}`,
      },
      {
        label: 'Direct labour at 65 m³ and 1 g L⁻¹',
        value: 11.0,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Reduced-form labour intensity scaled as scale to the power minus 0.55; the demo model does not size a crew, so this figure must not be read as a headcount. ${DEMO_BASIS}`,
      },
      {
        label: 'Fixed overhead per kg',
        value: 4.13,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Quality control, analytical consumables, insurance and site services at the reference scale, of which about two thirds dilutes with scale and one third does not. ${DEMO_BASIS}`,
      },
    ],
  },
  {
    id: 'sc-s2',
    modelId: 'S2',
    name: 'K. phaffii fed-batch recombinant protein',
    description:
      'Methanol-induced fed-batch cultivation of Komagataella phaffii GS115 secreting a recombinant enzyme, clarified and polished to a purified bulk. Titer governs the delivered price below roughly 12 g L⁻¹, above which chromatography consumables and downstream yield take over.',
    product: 'Purified recombinant enzyme',
    dims: S2_DIMS,
    point: { ...S2_REFERENCE_POINT },
    pinned: false,
    assumptions: [
      {
        label: 'Reference product titer',
        value: 12.4,
        unit: 'g L⁻¹',
        provenance: 'gold',
        recordId: 'ex-0091',
        note: 'Secreted lipase concentration at the end of a DO-stat methanol induction; it anchors the low-middle of the modelled titer axis and is the value the sweep is centred on.',
      },
      {
        label: 'Upper observed titer for this host',
        value: 25.8,
        unit: 'g L⁻¹',
        provenance: 'gold',
        recordId: 'ex-0109',
        note: 'A secreted albumin reached this concentration at pilot scale, which is why the titer axis is extended to 30 g L⁻¹ rather than stopping at the enzyme case.',
      },
      {
        label: 'Biomass yield on carbon source',
        value: 0.52,
        unit: 'g g⁻¹',
        provenance: 'gold',
        recordId: 'ex-0099',
        note: 'Grams of dry cell weight per gram of glycerol and methanol consumed; it converts the target cell density into the substrate mass that the media line pays for.',
      },
      {
        label: 'Yield on carbon under methanol induction',
        value: 0.39,
        unit: 'g g⁻¹',
        provenance: 'gold',
        recordId: 'ex-0117',
        note: 'The lower yield during induction reflects methanol dissimilated for maintenance and heat; the media line uses a blend of this and the growth-phase yield.',
      },
      {
        label: 'Final biomass density at harvest',
        value: 96,
        unit: 'g L⁻¹',
        provenance: 'verified',
        recordId: 'ex-0096',
        note: 'Dry cell weight at the end of induction; it sets the solids load the clarification train must handle and therefore the per-litre part of the downstream line.',
      },
      {
        label: 'Upper cell density with enhanced oxygen transfer',
        value: 128,
        unit: 'g L⁻¹',
        provenance: 'verified',
        recordId: 'ex-0111',
        note: 'Achieved only where oxygen transfer was the binding constraint and addressed directly; the utilities line assumes the plant runs nearer the 96 g L⁻¹ case.',
      },
      {
        label: 'Volumetric productivity of the induction phase',
        value: 0.115,
        unit: 'g L⁻¹ h⁻¹',
        provenance: 'verified',
        recordId: 'ex-0102',
        note: 'Product formed per litre per hour during induction; dividing the target titer by it is what fixes the 74 h induction leg of the batch cycle.',
      },
      {
        label: 'Induction temperature',
        value: 26,
        unit: '°C',
        provenance: 'verified',
        recordId: 'ex-0112',
        note: 'Reduced from the growth-phase setpoint to limit proteolysis of the secreted product; the lower setpoint raises the chilled-water duty carried in the utilities line.',
      },
      {
        label: 'Specific productivity floor used for sizing',
        value: 2.9,
        unit: 'mg g⁻¹ h⁻¹',
        provenance: 'gold',
        recordId: 'ex-0108',
        note: 'Product per gram of biomass per hour at the conservative end of the observed range; using the floor rather than the best case keeps the modelled cycle time honest.',
      },
      {
        label: 'Fermentation medium cost',
        value: 0.155,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Basal salts, trace metals, antifoam, glycerol and methanol per litre of final broth; divided by titer and downstream yield it becomes the dominant line below about 9 g L⁻¹. ${DEMO_BASIS}`,
      },
      {
        label: 'Cultivation utilities per batch',
        value: 0.035,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Agitation and aeration at roughly 2.5 kW m⁻³ for 110 h, plus sterilisation steam and the chilled water needed to remove the heat of methanol oxidation. ${DEMO_BASIS}`,
      },
      {
        label: 'Product-side utilities',
        value: 1.5,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Cold-chain and buffer-preparation services charged against purified product mass rather than broth volume. ${DEMO_BASIS}`,
      },
      {
        label: 'Clarification and concentration consumables',
        value: 0.042,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Disc-stack centrifugation, depth filtration and ultrafiltration charged against the broth volume that must be processed for each kilogram sold. ${DEMO_BASIS}`,
      },
      {
        label: 'Chromatography resin and buffer cost',
        value: 24,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Charged per kilogram of protein loaded onto the column, so the line carries a 1/dspYield term: a plant at 0.55 recovery buys the resin cycles for product it never sells. ${DEMO_BASIS}`,
      },
      {
        label: 'Installed capital at the 110 m³ reference scale',
        value: 10600000,
        unit: '$',
        provenance: 'demo',
        note: `Fermentation train, utilities and downstream suite as a single installed figure, roughly $96 per litre of working volume; it is at the low end of published fermentation capital and should be treated as illustrative. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital scaling exponent',
        value: 0.6,
        unit: '',
        provenance: 'demo',
        note: `The classic six-tenths rule; it is why moving from 20 to 200 m³ cuts the capital line by roughly a factor of six rather than a factor of ten. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital charge factor',
        value: 0.12,
        unit: 'yr⁻¹',
        provenance: 'demo',
        note: `Fraction of installed capital charged to each operating year; at the reference point it accounts for about a fifth of the minimum selling price. ${DEMO_BASIS}`,
      },
      {
        label: 'Direct labour at the reference scale',
        value: 850000,
        unit: '$ yr⁻¹',
        provenance: 'demo',
        note: `Operators, supervision and quality control for a 110 m³ plant, scaled as scale to the power 0.4 so a larger site does not need proportionally more people. ${DEMO_BASIS}`,
      },
      {
        label: 'Batch cycle time',
        value: 132,
        unit: 'h',
        provenance: 'demo',
        note: `24 h glycerol batch, 12 h glycerol fed-batch, 74 h methanol induction and 22 h turnaround; it fixes the 60 batches a year that all fixed costs are spread over. ${DEMO_BASIS}`,
      },
      {
        label: 'Annual operating time',
        value: 330,
        unit: 'd',
        provenance: 'demo',
        note: `Production days per year; because capital and labour are annual and product is not, this is the second strongest lever in the tornado after chromatography. ${DEMO_BASIS}`,
      },
      {
        label: 'Fixed overhead per kg',
        value: 7.5,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Analytics, release testing, waste treatment and site services at the reference scale, about half of which dilutes as the plant grows. ${DEMO_BASIS}`,
      },
      {
        label: 'Non-convergent corner of the authored engine',
        value: 5,
        unit: 'g L⁻¹',
        provenance: 'demo',
        note: `At 5 g L⁻¹ with 0.55 downstream yield and a 200 m³ fermenter the model cannot close its oxygen and heat balances and returns no result; the workspace shows the failure rather than a fabricated number. ${DEMO_BASIS}`,
      },
    ],
  },
  {
    id: 'sc-s3',
    modelId: 'S3',
    name: 'Photoautotrophic PBR route',
    description:
      'Flat-panel photobioreactor cultivation of cw15 on CO₂ and light alone, harvested and dried to a biomass powder, costed on the same per-kilogram basis as the mixotrophic stirred route in S1. Media almost disappears when there is no organic carbon to buy, and capital and labour take its place.',
    product: 'Dry algal biomass',
    dims: S3_DIMS,
    point: { ...S3_REFERENCE_POINT },
    pinned: false,
    assumptions: [
      {
        label: 'Photoautotrophic specific growth rate',
        value: 0.061,
        unit: 'h⁻¹',
        provenance: 'gold',
        recordId: 'ex-0021',
        note: 'Roughly half the mixotrophic rate under matched illumination, which is the single physiological fact that separates this route from S1 and lengthens every batch.',
      },
      {
        label: 'Volumetric productivity in a flat-panel array',
        value: 0.048,
        unit: 'g L⁻¹ h⁻¹',
        provenance: 'gold',
        recordId: 'ex-0052',
        note: 'Mean productivity over the linear growth phase at pilot scale; it anchors the areal productivity correlation that turns light path into cycles per year.',
      },
      {
        label: 'Biomass density delivered by the array',
        value: 3.8,
        unit: 'g L⁻¹',
        provenance: 'verified',
        recordId: 'ex-0053',
        note: 'Dry cell weight at harvest in the pilot photobioreactor; the model reaches 4.6 g L⁻¹ at the 6 cm reference path and less as the panel thickens.',
      },
      {
        label: 'Incident photon flux at the panel surface',
        value: 420,
        unit: 'µmol m⁻² s⁻¹',
        provenance: 'verified',
        recordId: 'ex-0055',
        note: 'Photosynthetically active flux at the illuminated face; the areal productivity assumption is only valid at this order of irradiance and would not transfer to a dimly lit indoor array.',
      },
      {
        label: 'CO₂ enrichment of the sparge gas',
        value: 2.5,
        unit: '% v/v',
        provenance: 'gold',
        recordId: 'ex-0057',
        note: 'Inlet CO₂ fraction during the linear phase; combined with the capture efficiency it fixes how much CO₂ must be bought per kilogram of biomass.',
      },
      {
        label: 'Harvest recovery, disc-stack centrifuge',
        value: 96.4,
        unit: '%',
        provenance: 'gold',
        recordId: 'ex-0046',
        note: 'The same pilot separation as S1, deliberately held constant so a comparison between the two routes is not confounded by different harvest technology.',
      },
      {
        label: 'OD to dry weight conversion factor',
        value: 0.42,
        unit: 'g L⁻¹ OD⁻¹',
        provenance: 'gold',
        recordId: 'ex-0080',
        note: 'Dry cell weight per unit optical density at 750 nm; online density in a panel array is read optically, so this factor sits between the sensor and every mass balance in the model.',
      },
      {
        label: 'Steady-state density at the 6 cm reference path',
        value: 4.6,
        unit: 'g L⁻¹',
        provenance: 'demo',
        note: `Achievable dry cell weight before self-shading stalls the culture, scaled as light path to the power minus 0.45 across the axis. ${DEMO_BASIS}`,
      },
      {
        label: 'Areal biomass productivity',
        value: 27,
        unit: 'g m⁻² d⁻¹',
        provenance: 'demo',
        note: `Productivity per square metre of illuminated panel, divided by light path to give volumetric productivity; halving the path doubles the litres of output per year and is the reason thin panels win. ${DEMO_BASIS}`,
      },
      {
        label: 'Turnaround between cultivation cycles',
        value: 0.5,
        unit: 'd',
        provenance: 'demo',
        note: `Drain, clean-in-place and refill of the panel array between batches; it is a fixed penalty that hurts the fast thin-panel cases proportionally more. ${DEMO_BASIS}`,
      },
      {
        label: 'Drying yield of the harvested paste',
        value: 97,
        unit: '%',
        provenance: 'demo',
        note: `Solids surviving drying, milling and packaging; the loss is small but it multiplies against harvest recovery in every per-kilogram figure. ${DEMO_BASIS}`,
      },
      {
        label: 'CO₂ cost per kg of dry biomass',
        value: 0.2492,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `1.8 kg of CO₂ fixed per kg of biomass at 65 % capture efficiency and a delivered CO₂ price; it is the only feedstock this route buys, which is why its media line is under a dollar. ${DEMO_BASIS}`,
      },
      {
        label: 'Nutrient salt package',
        value: 0.0018,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Nitrate, phosphate and trace metals per litre of culture; a photoautotrophic medium needs no buffer or organic carbon, so it costs about a quarter of the acetate medium in S1. ${DEMO_BASIS}`,
      },
      {
        label: 'Circulation and gas-transfer power',
        value: 0.001518,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `About 0.55 kW m⁻³ of pumping, sparging and thermal control charged for every day the culture is in the panel, so slow thick-panel cases pay it for longer. ${DEMO_BASIS}`,
      },
      {
        label: 'Drying and product-side utilities',
        value: 2.6,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Evaporative duty of drying a centrifuge paste to a stable powder; higher than S1 per kilogram because the paste leaving a dilute photoautotrophic culture is wetter. ${DEMO_BASIS}`,
      },
      {
        label: 'Installed capital at 70 m³ and a 6 cm path',
        value: 34286,
        unit: '$ m⁻³',
        provenance: 'demo',
        note: `Panel array, frames, pumps, gas handling and instrumentation, scaled as light path to the power minus 1.1 so a 2 cm panel costs more than three times as much per cubic metre. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital scaling exponent',
        value: 0.65,
        unit: '',
        provenance: 'demo',
        note: `Slightly weaker economy of scale than a stirred vessel, because a panel array grows mostly by replication rather than by building one larger unit. ${DEMO_BASIS}`,
      },
      {
        label: 'Capital charge factor',
        value: 0.12,
        unit: 'yr⁻¹',
        provenance: 'demo',
        note: `Fraction of installed capital charged annually; at the reference point capital is the largest single line in this route, which is the headline contrast with S1. ${DEMO_BASIS}`,
      },
      {
        label: 'Direct labour at the reference scale',
        value: 220000,
        unit: '$ yr⁻¹',
        provenance: 'demo',
        note: `Two to three loaded staff for a 70 m³ array, scaled as scale to the power 0.4; at 10 m³ this crew is spread over so little output that labour overtakes capital. ${DEMO_BASIS}`,
      },
      {
        label: 'Harvest consumables',
        value: 0.0028,
        unit: '$ L⁻¹',
        provenance: 'demo',
        note: `Centrifuge power and wear charged against the culture volume processed, which is the cost that thin high-density panels are buying down. ${DEMO_BASIS}`,
      },
      {
        label: 'Drying, milling and packaging',
        value: 6.5,
        unit: '$ kg⁻¹',
        provenance: 'demo',
        note: `Charged against dried product mass with a mild scale credit; it is the floor the route cannot go below no matter how cheap cultivation becomes. ${DEMO_BASIS}`,
      },
    ],
  },
];
