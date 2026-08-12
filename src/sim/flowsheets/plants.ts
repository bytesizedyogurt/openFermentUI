// The three plants.
//
// Each one is a connected train: a unit declares where its inlets come from, the
// System resolves the graph and runs it in order, and the mass balance
// propagates from the feed to the powder. Nothing is hand-built in the middle.
// That matters for more than tidiness — the flowsheet diagram and the stream
// table are read off this same graph, so a picture that disagrees with the model
// is not expressible.
//
// Change the titer and the reaction stoichiometry changes, which changes how
// much broth the centrifuge sees, which changes the membrane area, the pumping
// load and the electricity bill, and the price falls out of the cash flow.
//
// Where a number is a modelling choice rather than a measurement it is bound
// with `{kind:'model'}` and the justification says so out loud. Where a number
// has neither, it is bound `{kind:'unsourced'}` and the app treats it as a
// defect, which is exactly what it is.
import { BioSystem } from '@/engine/biosteam/system';
import type { Stream } from '@/engine/biosteam/types';
import type { Reaction } from '@/engine/biosteam/reaction';
import type { BioUnit } from '@/engine/biosteam/unit';
import {
  AeratedBioreactor,
  HXutility,
  MembraneSkid,
  MixTank,
  PEFDisruption,
  Photobioreactor,
  Pump,
  SolidsCentrifuge,
  SprayDryer,
  StorageTank,
  CP_BROTH,
  fromFeed,
  fromUnit,
} from './units';
import { baseTEA, OPERATING_HOURS, type FlowsheetSpec } from './spec';

/** Broth is water with things in it, so it weighs and heats like water. */
const RHO_BROTH = 1000;

function stream(ID: string, flow: Record<string, number>, opts: Partial<Stream> = {}): Stream {
  return { ID, flow, T: 303, P: 101325, price: 0, rho: RHO_BROTH, phase: 'l', ...opts };
}

/**
 * Assemble a system and resolve its product stream after the train has run.
 *
 * The product is an outlet of the last unit, which does not exist until the
 * graph has been simulated — so it is picked up afterwards rather than
 * constructed alongside. Identity matters here: the TEA mutates the price on
 * this object while solving, so it has to be the same object the unit produced
 * and not a copy of it.
 */
function assemble(opts: {
  ID: string;
  units: BioUnit[];
  feeds: Stream[];
  productUnit: string;
  productPort?: number;
}): BioSystem {
  const sys = new BioSystem({
    ID: opts.ID,
    units: opts.units,
    feeds: opts.feeds,
    products: [],
    operatingHours: OPERATING_HOURS,
  });
  sys.simulate();
  const last = opts.units.find((u) => u.ID === opts.productUnit);
  if (!last) throw new Error(`${opts.ID}: no unit '${opts.productUnit}' to take the product from`);
  const product = last.outs[opts.productPort ?? 0];
  if (!product) throw new Error(`${opts.ID}: '${opts.productUnit}' produced no outlet to sell`);
  sys.products = [product];
  return sys;
}

// ══ S2 — K. phaffii secreted β-casein ══════════════════════════════════
//
// The comparator, and the easiest of the three to defend, because every unit in
// it has a published correlation. Sized on a batch basis: the installed
// fermenter volume and the cycle time between them set how much broth the plant
// makes in a year, and everything downstream follows from that.

/** Biomass yield on glycerol, kg/kg. Typical for a Crabtree-negative yeast. */
const Y_XS_YEAST = 0.5;
/** Cell density at harvest, g/L. High-cell-density fed-batch. */
const X_YEAST = 100;

function buildS2(p: Record<string, number>): BioSystem {
  const titer = Math.max(1e-4, p.titer); // g/L secreted
  const scale = p.scale; // m³ installed fermenter working volume
  const dspYield = Math.min(0.995, Math.max(0.05, p.dspYield));
  const tau = 96;
  const tauClean = 12;
  const conversion = 0.98;

  // One turn of the installed volume per reaction-plus-turnaround cycle.
  const F_broth = scale / (tau + tauClean); // m³/hr

  // Substrate is set by the biomass the culture has to build; the product yield
  // is whatever the scenario's titer asks of that same substrate. That is the
  // honest way round — the titer is the question being asked, and the
  // stoichiometry is what asking it implies.
  const substrate_kg_m3 = X_YEAST / Y_XS_YEAST / conversion;
  const reaction: Reaction = {
    equation: 'glycerol -> biomass + β-casein + CO₂',
    reactant: 'substrate',
    X: conversion,
    yields: {
      biomass: X_YEAST / substrate_kg_m3 / conversion,
      product: titer / substrate_kg_m3 / conversion,
    },
  };

  // Oxygen demand follows the biomass, which is what makes electricity scale
  // with the culture rather than with the tank.
  const qO2 = 0.0015; // mol O₂ per g DCW per hour
  const OUR = qO2 * X_YEAST; // mol O₂ per litre per hour

  const media = stream(
    'media',
    { water: F_broth * 950, substrate: F_broth * substrate_kg_m3 },
    { price: 0.55, T: 293 },
  );

  const mediaPrep = new MixTank('T101 media prep', [fromFeed(media)], 8);
  const feedPump = new Pump('P101 feed pump', [fromUnit('T101 media prep')], 3e5, 100);
  // Sterilise at 121 °C and hold. Only the net duty is charged: a real steriliser
  // regenerates against the incoming feed, and pretending otherwise would put a
  // heating and a cooling bill on the same stream.
  const steriliser = new HXutility('H101 steriliser', [fromUnit('P101 feed pump')], {
    duty: F_broth * 1000 * CP_BROTH * 25,
    agent: 'low_pressure_steam',
    T_out: 303,
    dT_lm: 40,
    area: 100,
  });
  const fermenter = new AeratedBioreactor('R301 fermenter', [fromUnit('H101 steriliser')], {
    tau,
    tau_cleaning: tauClean,
    V_max: 500,
    OUR,
    T: 303,
    reaction,
  });
  // Secreted product stays in the centrate; the loss is what leaves wet with the
  // cell cake, which is physical and not adjustable.
  const centrifuge = new SolidsCentrifuge('C401 disc stack', [fromUnit('R301 fermenter', 0)], {
    split: 0.97,
    productToCake: 0.04,
    cakeMoisture: 2,
  });
  // Clarify before concentrating. The first cut of this flowsheet went straight
  // from the centrifuge to the ultrafiltration, and the mass balance said the
  // powder was a fifth product and four fifths yeast: a disc stack leaves about
  // 3 g/L of cells behind, an ultrafiltration rejects cells and protein alike,
  // and concentrating both together gives you a cell paste with some casein in
  // it. A 0.2 µm microfiltration passes the protein and holds the cells, which
  // is what every real recovery train does and what the model was asking for.
  const clarify = new MembraneSkid('M402 clarification', [fromUnit('C401 disc stack', 0)], {
    flux: 60,
    productYield: 0.97,
    label: 'Microfiltration',
    diavolumes: 1,
    area: 400,
    waterRemoval: 0.2,
    productInRetentate: false,
    usdPerM2: 600,
  });
  clarify.rejection = 0.999;
  // The ultrafiltration carries whatever recovery the scenario asks for, after
  // the centrifuge and the clarifier have taken their physical cuts.
  const uf = new MembraneSkid('M501 UF/DF', [fromUnit('M402 clarification', 1)], {
    flux: 35,
    productYield: Math.min(0.995, dspYield / (0.96 * 0.97)),
    label: 'Ultrafiltration',
    diavolumes: 4,
    waterRemoval: 0.97,
  });
  const dryer = new SprayDryer('D601 spray dryer', [fromUnit('M501 UF/DF', 0)]);
  const silo = new StorageTank('T801 product silo', [fromUnit('D601 spray dryer', 0)], 7);
  silo.outIDs = ['product'];

  return assemble({
    ID: 'S2 — K. phaffii secreted',
    units: [mediaPrep, feedPump, steriliser, fermenter, centrifuge, clarify, uf, dryer, silo],
    feeds: [media],
    productUnit: 'T801 product silo',
  });
}

export const S2_FLOWSHEET: FlowsheetSpec = {
  modelId: 'S2',
  name: 'K. phaffii secreted β-casein',
  productStreamID: 'product',
  productLabel: 'β-casein powder',
  build: buildS2,
  tea: baseTEA({ laborCost: 2.1e6 }),
  parameters: [
    {
      key: 'titer',
      label: 'Secreted titer',
      unit: 'g L⁻¹',
      baseline: 1,
      bounds: [0.05, 5],
      distribution: 'triangular',
      field: 'titer_secreted',
      paperId: 'K1',
      basis: { kind: 'record', recordId: 'r-K1-1' },
      note: 'Sets the product yield on substrate, so it moves the fermenter, the centrifuge and the membrane together.',
    },
    {
      key: 'scale',
      label: 'Installed fermenter volume',
      unit: 'm³',
      baseline: 110,
      bounds: [20, 200],
      distribution: 'uniform',
      basis: {
        kind: 'model',
        justification:
          'Plant sizing decision. How big a plant somebody chooses to build is not a property of the organism and the corpus holds no record for it.',
      },
      note: 'Sets annual output at a given titer, and buys the six-tenths capital discount.',
    },
    {
      key: 'dspYield',
      label: 'Downstream recovery',
      unit: 'fraction',
      baseline: 0.75,
      bounds: [0.55, 0.9],
      distribution: 'triangular',
      basis: {
        kind: 'model',
        justification:
          'Overall recovery across centrifugation and ultrafiltration. Ontology v1 has no field for a recovery yield, so no record exists to bind — an ontology gap, not an unsourced number.',
      },
      note: 'Applied after the centrifuge takes its physical cut with the wet cake.',
    },
  ],
  limitations: [
    'No vapour–liquid equilibrium: the steriliser and the dryer are sized on latent and sensible heat, not on a property package.',
    'Aeration is modelled at a single oxygen uptake rate rather than over the fed-batch profile, so the peak demand that actually sizes the compressor is not resolved.',
    'The sparged gas is treated as air all the way up the column. Real off-gas is oxygen-depleted, so the driving force here is optimistic and the agitator power correspondingly low.',
    'Neither membrane skid has a published cost correlation; their capital is a vendor-class figure written here, not borrowed from bioSTEAM.',
    'Components are lumped. The clarification step separates “cells” from “protein” and cannot distinguish the target protein from any other one the host secretes, so the purity below is an upper bound.',
  ],
};

// ══ S1 — cw15 intracellular β-casein in a photobioreactor ══════════════
//
// The expensive one, and the honest one: two of its four significant units have
// no published correlation, and the plant view says so before the reader gets to
// the number.

/** Biomass yield on acetate, kg/kg, for mixotrophic Chlamydomonas. */
const Y_XS_ALGAE = 0.35;

function buildS1(p: Record<string, number>): BioSystem {
  const density = Math.max(0.05, p.density); // g/L biomass
  const share = Math.max(1e-4, p.pctTsp) / 100; // product per g biomass
  const recovery = Math.min(0.98, Math.max(0.02, p.dispYield / 100));
  const tau = 120; // ~5-day mixotrophic batch
  const volumeM3 = 120; // fixed plant size for this surface
  const conversion = 0.9;

  const F_broth = volumeM3 / (tau + 24); // m³/hr
  const acetate_kg_m3 = density / Y_XS_ALGAE / conversion;
  const reaction: Reaction = {
    equation: 'acetate -> biomass + β-casein + O₂',
    reactant: 'acetate',
    X: conversion,
    yields: {
      biomass: density / acetate_kg_m3 / conversion,
      product: (density * share) / acetate_kg_m3 / conversion,
    },
  };

  const media = stream(
    'TAP medium',
    { water: F_broth * 990, acetate: F_broth * acetate_kg_m3 },
    { price: 0.42, T: 293 },
  );

  const mediaPrep = new MixTank('T101 TAP prep', [fromFeed(media)], 12);
  const pbr = new Photobioreactor('R301 tubular loops', [fromUnit('T101 TAP prep')], {
    tau,
    lightingWPerM3: 60,
    T: 298,
    reaction,
  });
  // The cells are the product here, so the harvest keeps the cake.
  const harvest = new SolidsCentrifuge('C401 harvest', [fromUnit('R301 tubular loops', 0)], {
    split: 0.95,
    productToCake: 0.95,
    cakeMoisture: 4,
  });
  const pef = new PEFDisruption('E402 PEF', [fromUnit('C401 harvest', 1)], recovery);
  // The product is in solution now and the debris is waste, so this one keeps
  // the centrate.
  const clarifier = new SolidsCentrifuge('C403 debris removal', [fromUnit('E402 PEF', 0)], {
    split: 0.98,
    productToCake: 0.08,
    cakeMoisture: 3,
  });
  // The same clarification the yeast route needs, and for a sharper reason. At
  // 2 g/L of cells and 3% of cell mass as casein, the debris outweighs the
  // product thirty-fold: two per cent carried past the centrifuge is still
  // twice the protein, and an ultrafiltration would concentrate both. Passing
  // the protein through a 0.2 µm membrane and holding the debris is the only
  // way this train produces a powder rather than a cell paste.
  const clarify = new MembraneSkid('M502 clarification', [fromUnit('C403 debris removal', 0)], {
    flux: 40,
    productYield: 0.96,
    label: 'Microfiltration',
    diavolumes: 2,
    area: 500,
    waterRemoval: 0.2,
    productInRetentate: false,
    usdPerM2: 600,
  });
  clarify.rejection = 0.999;
  const uf = new MembraneSkid('M501 UF/DF', [fromUnit('M502 clarification', 1)], {
    flux: 25,
    productYield: 0.9,
    label: 'Ultrafiltration',
    diavolumes: 5,
    waterRemoval: 0.95,
  });
  const dryer = new SprayDryer('D601 spray dryer', [fromUnit('M501 UF/DF', 0)]);
  const silo = new StorageTank('T801 product silo', [fromUnit('D601 spray dryer', 0)], 7);
  silo.outIDs = ['product'];

  return assemble({
    ID: 'S1 — cw15 photobioreactor',
    units: [mediaPrep, pbr, harvest, pef, clarifier, clarify, uf, dryer, silo],
    feeds: [media],
    productUnit: 'T801 product silo',
  });
}

export const S1_FLOWSHEET: FlowsheetSpec = {
  modelId: 'S1',
  name: 'cw15 intracellular β-casein',
  productStreamID: 'product',
  productLabel: 'β-casein powder',
  build: buildS1,
  tea: baseTEA({ laborCost: 1.68e6 }),
  parameters: [
    {
      key: 'density',
      label: 'Biomass density',
      unit: 'g L⁻¹',
      baseline: 2,
      bounds: [0.5, 5],
      distribution: 'triangular',
      field: 'final_biomass_density',
      paperId: 'M5',
      basis: { kind: 'record', recordId: 'r-M5-1' },
      note: 'Sets the acetate the culture consumes and the paste the harvest produces. Everything downstream is sized on it.',
    },
    {
      key: 'pctTsp',
      label: 'β-casein as % of cell mass',
      unit: '% TSP',
      baseline: 3,
      bounds: [0.1, 20],
      distribution: 'triangular',
      field: 'expression_pct_tsp',
      paperId: 'A1',
      basis: { kind: 'record', recordId: 'r-A1-1' },
      note: 'The axis with no measurement on it above 0.2%: no casein has been expressed in any alga, so the upper bound is extrapolation.',
    },
    {
      key: 'dispYield',
      label: 'Disruption + recovery yield',
      unit: '%',
      baseline: 31,
      bounds: [10, 50],
      distribution: 'triangular',
      field: 'disruption_protein_yield',
      paperId: 'J10',
      basis: { kind: 'record', recordId: 'r-J10-1' },
      note: 'The cell-wall-deficient chassis exists for this number: 31% released against 11% for the walled wild type.',
    },
  ],
  limitations: [
    'The photobioreactor has no published cost correlation. Its capital is six-tenths scaling from a single real 3 m³ plant, and it dominates the answer.',
    'The PEF disruptor is priced off pilot skid quotes. It is the least defensible capital number in this plant.',
    'Light delivery is modelled as a flat W/m³ rather than as a function of culture depth and optical density, so the density axis does not pay the light-attenuation penalty it would pay in reality.',
    'No vapour–liquid equilibrium, and no CO₂ mass transfer.',
    'Components are lumped, so the clarification separates “debris” from “protein” and cannot tell β-casein from the rest of the algal proteome. The purity below is an upper bound.',
  ],
};

// ══ S3 — conventional β-casein from milk ═══════════════════════════════
//
// Not a fermentation plant, but a real process plant, and it is modelled with
// the same equipment classes rather than waved through as a market price. The
// point of the comparison is that the incumbent's cost is dominated by
// feedstock, and that only shows up if you actually process the milk.

function buildS3(p: Record<string, number>): BioSystem {
  const milkPrice = p.milkPrice; // USD/L, and USD/kg at water density
  const recovery = Math.min(0.98, Math.max(0.05, p.recovery));
  const betaInMilk = 2.6; // g/L, Atamer et al.

  // Basis: a 500 m³/day dairy fractionation line.
  const F_milk = 500 / 24; // m³/hr
  const milkL = F_milk * 1000;

  const milk = stream(
    'raw milk',
    {
      water: milkL * 0.87,
      product: (betaInMilk * milkL) / 1000,
      protein: milkL * 0.0314,
      fat: milkL * 0.04,
      lactose: milkL * 0.048,
    },
    { price: milkPrice, T: 281 },
  );

  const receiving = new StorageTank('T101 milk silo', [fromFeed(milk)], 1, 100);
  // Chill to the 4 °C where β-casein leaves the micelle. Without this step the
  // separation does not exist, so it is not an optional utility line.
  //
  // Brine, not chilled water: chilled water is supplied at 280.4 K and cannot
  // take a stream down to 277 K. Passing the process temperature into the
  // utility turns that from a number nobody checks into an exception.
  const chiller = new HXutility('H101 chiller', [fromUnit('T101 milk silo')], {
    duty: -milkL * CP_BROTH * 6,
    agent: 'chilled_brine',
    T_out: 277,
    dT_lm: 8,
    area: 100,
  });
  const feedPump = new Pump('P101 feed pump', [fromUnit('H101 chiller')], 4e5, 100);
  // Cold microfiltration: β-casein dissociates into the serum and passes the
  // membrane while the remaining micelle is retained. The product leaves in the
  // permeate, which is the entire trick of this route.
  const mf = new MembraneSkid('M401 cold microfiltration', [fromUnit('P101 feed pump')], {
    flux: 55,
    productYield: recovery,
    label: 'Microfiltration',
    diavolumes: 2,
    area: 400,
    waterRemoval: 0.6,
    productInRetentate: false,
  });
  // A 0.1 µm ceramic membrane holds fat globules and casein micelles better than
  // the generic default, and what leaks past it is what dilutes the powder.
  mf.rejection = 0.997;
  const uf = new MembraneSkid('M501 UF/DF', [fromUnit('M401 cold microfiltration', 1)], {
    flux: 30,
    productYield: 0.95,
    label: 'Ultrafiltration',
    diavolumes: 4,
    waterRemoval: 0.95,
  });
  const dryer = new SprayDryer('D601 spray dryer', [fromUnit('M501 UF/DF', 0)]);
  const silo = new StorageTank('T801 product silo', [fromUnit('D601 spray dryer', 0)], 7);
  silo.outIDs = ['product'];

  return assemble({
    ID: 'S3 — dairy microfiltration',
    units: [receiving, chiller, feedPump, mf, uf, dryer, silo],
    feeds: [milk],
    productUnit: 'T801 product silo',
  });
}

export const S3_FLOWSHEET: FlowsheetSpec = {
  modelId: 'S3',
  name: 'Conventional β-casein from milk',
  productStreamID: 'product',
  productLabel: 'β-casein powder',
  build: buildS3,
  tea: baseTEA({ laborCost: 1.4e6, IRR: 0.08 }),
  parameters: [
    {
      key: 'milkPrice',
      label: 'Raw milk price',
      unit: 'USD L⁻¹',
      baseline: 0.45,
      bounds: [0.3, 0.75],
      distribution: 'uniform',
      basis: {
        kind: 'model',
        justification:
          'Commodity price input. Market data rather than literature, and outside the ontology.',
      },
      note: 'You process a litre to recover two and a half grams, so the feedstock line dominates everything else.',
    },
    {
      key: 'recovery',
      label: 'β-casein recovery',
      unit: 'fraction',
      baseline: 0.6,
      bounds: [0.3, 0.9],
      distribution: 'triangular',
      paperId: 'J3',
      basis: {
        kind: 'model',
        justification:
          'Cold-microfiltration recovery from the J3 process description. Ontology v1 has no field for a separation recovery, so no record exists to bind — an ontology gap, not an unsourced number.',
      },
      note: 'Sets how much milk has to move through the plant per kilogram out.',
    },
  ],
  limitations: [
    'The membrane skids are priced on installed area at a module price, not on a published correlation.',
    'Co-product credit for the retentate — micellar casein concentrate, which is a saleable product — is not taken. That makes this route look worse than it is, and the direction of the bias is stated rather than corrected.',
    'No vapour–liquid equilibrium; the dryer is sized on latent heat.',
    'Whey proteins and caseins are one lumped “protein” component, so the model cannot resolve the separation that actually sets purity here. Two membrane passes give a β-casein-enriched powder rather than an isolate, and the purity reported below reflects that.',
  ],
};

export const FLOWSHEETS: FlowsheetSpec[] = [S1_FLOWSHEET, S2_FLOWSHEET, S3_FLOWSHEET];

export const FLOWSHEET_BY_MODEL: Record<string, FlowsheetSpec> = {
  S1: S1_FLOWSHEET,
  S2: S2_FLOWSHEET,
  S3: S3_FLOWSHEET,
};
