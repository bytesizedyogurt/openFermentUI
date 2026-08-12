// The three plants.
//
// Each one is a feed-forward train of sized, costed equipment, built fresh at
// every parameter point. Nothing is cached inside a plant and nothing is
// authored as a result: change the titer and the fermenter gets smaller, the
// centrifuge gets cheaper, the electricity bill falls, and the DCF re-solves.
// That chain is the reason for the whole exercise — the old cost engines moved
// a headline number without anything physical moving underneath it.
//
// Where a number is a modelling choice rather than a measurement it is bound
// with `{kind:'model'}` and the justification says so out loud. Where a number
// has neither, it is bound `{kind:'unsourced'}` and the app treats it as a
// defect, which is exactly what it is.
import { BioSystem } from '@/engine/biosteam/system';
import type { Stream } from '@/engine/biosteam/types';
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
} from './units';
import { baseTEA, OPERATING_HOURS, type FlowsheetSpec } from './spec';

/** Broth is water with things in it, so it weighs and heats like water. */
const RHO_BROTH = 1000;

function stream(ID: string, flow: Record<string, number>, opts: Partial<Stream> = {}): Stream {
  return { ID, flow, T: 303, P: 101325, price: 0, rho: RHO_BROTH, phase: 'l', ...opts };
}

// ══ S2 — K. phaffii secreted β-casein ══════════════════════════════════
//
// The comparator, and the easiest of the three to defend, because every unit in
// it has a published correlation. Sized on a batch basis: the installed
// fermenter volume and the cycle time between them set how much broth the plant
// makes in a year, and everything downstream follows from that.

function buildS2(p: Record<string, number>): BioSystem {
  const titer = Math.max(1e-4, p.titer); // g/L secreted
  const scale = p.scale; // m³ installed fermenter working volume
  const dspYield = Math.min(0.995, Math.max(0.05, p.dspYield));
  const tau = 96; // hr of fed-batch
  const tauClean = 12;

  // Hourly-equivalent broth throughput: one turn of the installed volume per
  // reaction-plus-turnaround cycle.
  const F_broth = scale / (tau + tauClean); // m³/hr
  const brothL = F_broth * 1000;

  // High-cell-density fed-batch. The oxygen demand follows from the biomass,
  // which is what makes electricity scale with the culture rather than the tank.
  const X = 100; // g DCW/L at harvest
  const qO2 = 0.0015; // mol O₂ per g DCW per hour
  const OUR = qO2 * X; // mol O₂ per litre per hour

  const product_kg_hr = titer * F_broth; // g/L × m³/hr = kg/hr
  const biomass_kg_hr = (X * brothL) / 1000;

  const media = stream(
    'media',
    { water: brothL * 0.96, nutrients: brothL * 0.04 },
    { price: 0.55, T: 293 },
  );

  const mediaPrep = new MixTank('T101 media prep', [media], 8);
  const feedPump = new Pump('P101 feed pump', [media], 3e5, 100);
  // Sterilisation: heat the medium to 121 °C and hold.
  const steriliser = new HXutility('H101 steriliser', [media], {
    duty: brothL * CP_BROTH * (394 - 293),
    agent: 'low_pressure_steam',
    dT_lm: 40,
    area: 100,
  });

  const brothIn = stream('broth-feed', {
    water: brothL * 0.96,
    nutrients: brothL * 0.04,
  });
  const fermenter = new AeratedBioreactor('R301 fermenter', [brothIn], {
    tau,
    tau_cleaning: tauClean,
    V_max: 500,
    OUR,
    T: 303,
  });

  const broth = stream('broth', {
    water: brothL * 0.93,
    biomass: biomass_kg_hr,
    product: product_kg_hr,
  });

  // Secreted product stays in the centrate; the loss is what leaves wet with
  // the cell cake, which is a physical loss and not an adjustable one.
  const centrifuge = new SolidsCentrifuge('C401 disc stack', [broth], {
    solidsSplit: 0.97,
    productToCake: 0.04,
  });
  const centrate = centrifuge.outs.length ? centrifuge.outs[0] : broth;

  // The membrane step carries whatever recovery the scenario asks for, after
  // the centrifuge has taken its physical cut.
  const uf = new MembraneSkid('M501 UF/DF', [
    stream('centrate', {
      water: brothL * 0.9,
      product: product_kg_hr * 0.96,
    }),
  ], {
    flux: 35,
    productYield: Math.min(0.995, dspYield / 0.96),
    label: 'Ultrafiltration',
    diavolumes: 4,
  });

  const concentrate = stream('concentrate', {
    water: (product_kg_hr * dspYield) / 0.12,
    product: product_kg_hr * dspYield,
  });
  const dryer = new SprayDryer('D601 spray dryer', [concentrate]);

  const powder = stream(
    'product',
    { product: product_kg_hr * dspYield, water: product_kg_hr * dspYield * 0.05 },
    { phase: 's' },
  );
  const silo = new StorageTank('T801 product silo', [powder], 7);

  const units = [mediaPrep, feedPump, steriliser, fermenter, centrifuge, uf, dryer, silo];
  const sys = new BioSystem({
    ID: 'S2 — K. phaffii secreted',
    units,
    feeds: [media],
    products: [powder],
    operatingHours: OPERATING_HOURS,
  });
  sys.simulate();
  // The centrate reference above is informational only; the mass balance the
  // TEA consumes is the explicit stream list, so a stale `outs` cannot leak in.
  void centrate;
  return sys;
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
      note: 'Sets the broth volume behind every kilogram, so it moves the fermenter, the centrifuge and the membrane together.',
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
    'The ultrafiltration skid has no published cost correlation; its capital is a vendor-class figure written here, not borrowed from bioSTEAM.',
  ],
};

// ══ S1 — cw15 intracellular β-casein in a photobioreactor ══════════════
//
// The expensive one, and the honest one: two of its four significant units have
// no published correlation, and the plant view says so before the reader gets
// to the number.

function buildS1(p: Record<string, number>): BioSystem {
  const density = Math.max(0.05, p.density); // g/L biomass
  const share = Math.max(1e-4, p.pctTsp) / 100; // product per g biomass
  const recovery = Math.min(0.98, Math.max(0.02, p.dispYield / 100));
  const tau = 120; // hr, ~5-day mixotrophic batch
  const volumeM3 = 120; // fixed plant size for this surface

  const F_broth = volumeM3 / (tau + 24); // m³/hr
  const brothL = F_broth * 1000;

  const biomass_kg_hr = (density * brothL) / 1000;
  const productInCells_kg_hr = biomass_kg_hr * share;

  const media = stream(
    'TAP medium',
    { water: brothL * 0.99, acetate: brothL * 0.01 },
    { price: 0.42, T: 293 },
  );
  const mediaPrep = new MixTank('T101 TAP prep', [media], 12);

  const pbr = new Photobioreactor(
    'R301 tubular loops',
    [stream('broth-feed', { water: brothL * 0.99, acetate: brothL * 0.01 })],
    { tau, lightingWPerM3: 60, T: 298 },
  );

  const broth = stream('broth', {
    water: brothL * 0.99,
    biomass: biomass_kg_hr,
    product: productInCells_kg_hr,
  });

  // Harvest first — the cells are the product here, so the centrifuge keeps
  // the cake and the centrate is the waste stream.
  const harvest = new SolidsCentrifuge('C401 harvest', [broth], {
    solidsSplit: 0.95,
    productToCake: 0.95,
  });

  const paste = stream('paste', {
    water: biomass_kg_hr * 4,
    biomass: biomass_kg_hr * 0.95,
    product: productInCells_kg_hr * 0.95,
  });
  const pef = new PEFDisruption('E402 PEF', [paste], recovery);

  const lysate = stream('lysate', {
    water: biomass_kg_hr * 4,
    biomass: biomass_kg_hr * 0.95,
    product: productInCells_kg_hr * 0.95 * recovery,
  });
  const clarifier = new SolidsCentrifuge('C403 debris removal', [lysate], {
    solidsSplit: 0.98,
    productToCake: 0.08,
  });

  const product_kg_hr = productInCells_kg_hr * 0.95 * recovery * 0.92;
  const uf = new MembraneSkid(
    'M501 UF/DF',
    [stream('clarified', { water: biomass_kg_hr * 4, product: product_kg_hr })],
    { flux: 25, productYield: 0.9, label: 'Ultrafiltration', diavolumes: 5 },
  );

  const finalProduct = product_kg_hr * 0.9;
  const dryer = new SprayDryer(
    'D601 spray dryer',
    [stream('concentrate', { water: finalProduct / 0.12, product: finalProduct })],
  );
  const powder = stream(
    'product',
    { product: finalProduct, water: finalProduct * 0.05 },
    { phase: 's' },
  );
  const silo = new StorageTank('T801 product silo', [powder], 7);

  const sys = new BioSystem({
    ID: 'S1 — cw15 photobioreactor',
    units: [mediaPrep, pbr, harvest, pef, clarifier, uf, dryer, silo],
    feeds: [media],
    products: [powder],
    operatingHours: OPERATING_HOURS,
  });
  sys.simulate();
  return sys;
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
      note: 'Everything downstream is sized on the paste this produces, and the photobioreactor is sized on the volume it takes to make it.',
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
    'The photobioreactor has no published cost correlation. Its capital is six-tenths scaling from a single real 3 m³ plant, and dominates the answer.',
    'The PEF disruptor is priced off pilot skid quotes. It is the least defensible capital number in this plant.',
    'Light delivery is modelled as a flat W/m³ rather than as a function of culture depth and optical density, so the density axis does not pay the light-attenuation penalty it would pay in reality.',
    'No vapour–liquid equilibrium, and no CO₂ mass transfer.',
  ],
};

// ══ S3 — conventional β-casein from milk ═══════════════════════════════
//
// Not a fermentation plant, but a real process plant, and it is modelled with
// the same equipment classes rather than waved through as a market price. The
// point of the comparison is that the incumbent's cost is dominated by
// feedstock, and that only shows up if you actually process the milk.

function buildS3(p: Record<string, number>): BioSystem {
  const milkPrice = p.milkPrice; // USD/L
  const recovery = Math.min(0.98, Math.max(0.05, p.recovery));
  const betaInMilk = 2.6; // g/L, Atamer et al.

  // Basis: a 500 m³/day dairy fractionation line.
  const F_milk = 500 / 24; // m³/hr
  const milkL = F_milk * 1000;

  const milk = stream(
    'raw milk',
    { water: milkL * 0.87, protein: milkL * 0.034, fat: milkL * 0.04, lactose: milkL * 0.048 },
    { price: milkPrice, T: 277 },
  );

  const receiving = new StorageTank('T101 milk silo', [milk], 1, 100);
  // Chill to the 4 °C where β-casein leaves the micelle. Without this step the
  // separation does not exist, so it is not an optional utility line.
  const chiller = new HXutility('H101 chiller', [milk], {
    duty: -milkL * CP_BROTH * 6,
    agent: 'chilled_water',
    dT_lm: 8,
    area: 100,
  });
  const feedPump = new Pump('P101 feed pump', [milk], 4e5, 100);

  const beta_kg_hr = (betaInMilk * milkL) / 1000;
  const mf = new MembraneSkid('M401 cold microfiltration', [milk], {
    flux: 55,
    productYield: recovery,
    label: 'Microfiltration',
    diavolumes: 2,
    area: 400,
  });

  const permeate = stream('serum', {
    water: milkL * 0.6,
    product: beta_kg_hr * recovery,
  });
  const uf = new MembraneSkid('M501 UF/DF', [permeate], {
    flux: 30,
    productYield: 0.95,
    label: 'Ultrafiltration',
    diavolumes: 4,
  });

  const product_kg_hr = beta_kg_hr * recovery * 0.95;
  const dryer = new SprayDryer(
    'D601 spray dryer',
    [stream('concentrate', { water: product_kg_hr / 0.15, product: product_kg_hr })],
  );
  const powder = stream(
    'product',
    { product: product_kg_hr, water: product_kg_hr * 0.05 },
    { phase: 's' },
  );
  const silo = new StorageTank('T801 product silo', [powder], 7);

  const sys = new BioSystem({
    ID: 'S3 — dairy microfiltration',
    units: [receiving, chiller, feedPump, mf, uf, dryer, silo],
    feeds: [milk],
    products: [powder],
    operatingHours: OPERATING_HOURS,
  });
  sys.simulate();
  return sys;
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
  ],
};

export const FLOWSHEETS: FlowsheetSpec[] = [S1_FLOWSHEET, S2_FLOWSHEET, S3_FLOWSHEET];

export const FLOWSHEET_BY_MODEL: Record<string, FlowsheetSpec> = {
  S1: S1_FLOWSHEET,
  S2: S2_FLOWSHEET,
  S3: S3_FLOWSHEET,
};
