// Techno-economic scenarios (OF-COR-001 §20). Replaces the three synthetic
// algal cases with the comparison a faculty reviewer will actually ask for:
// the algal route, the incumbent yeast route, and the cow.
//
// HONESTY: the response surfaces below are authored cost engines, not process
// simulations. Their SHAPE is grounded — scaling exponents, the density and
// protein-content sensitivities from the formate-dehydrogenase TEA (O3), the
// biomass cost points from Acién (O4) and the GFI meta-analysis (O2) — but the
// absolute numbers are modeled, not measured. Every headline carries that
// label, and the whole surface is provenance 'demo'.
import type { CostLine, CostModel, Scenario } from './types';

// ── shared cost primitives ────────────────────────────────────────────
const CAPITAL_CHARGE = 0.12; // annualisation factor
const OPERATING_DAYS = 330;
const SCALE_EXPONENT = 0.6; // O1/O3: capital scales ~capacity^0.6

/** Annualised capital per kg, given a reference cost and the six-tenths rule. */
function capexPerKg(refCostUSD: number, refScale: number, scale: number, kgPerYear: number) {
  const cost = refCostUSD * Math.pow(scale / refScale, SCALE_EXPONENT);
  return (cost * CAPITAL_CHARGE) / Math.max(1, kgPerYear);
}

const lines = (o: Partial<Record<CostLine, number>>): Record<CostLine, number> => ({
  capex: o.capex ?? 0,
  media: o.media ?? 0,
  utilities: o.utilities ?? 0,
  labor: o.labor ?? 0,
  downstream: o.downstream ?? 0,
  other: o.other ?? 0,
});

// ══ S1 — cw15 intracellular β-casein ═══════════════════════════════════
// Sweep chosen per OF-COR-001 §20 and parameterised on exactly the two
// variables O3 identifies as dominant: biomass density and target protein as a
// share of cell mass. Both axes are marked with where the literature actually
// sits today, which is at the very bottom of each.
const S1: CostModel = {
  modelId: 'S1',
  dims: [
    { key: 'density', label: 'Biomass density', unit: 'g L⁻¹', values: [0.5, 1.25, 2, 3, 4, 5] },
    { key: 'pctTsp', label: 'β-casein as % of cell mass', unit: '% TSP', values: [0.1, 1, 3, 6, 12, 20] },
    { key: 'dispYield', label: 'Disruption + recovery yield', unit: '%', values: [10, 20, 30, 40, 50] },
  ],
  referencePoint: { density: 2, pctTsp: 3, dispYield: 31 },
  evaluate: (p) => {
    const density = p.density; // g/L biomass
    const share = p.pctTsp / 100; // product per g biomass
    const recovery = p.dispYield / 100;
    // grams of recovered product per litre of broth
    const gPerL = Math.max(1e-6, density * share * recovery);
    const volumeM3 = 120; // fixed plant size for this surface
    const batchesPerYear = OPERATING_DAYS / 5; // ~5-day mixotrophic batch
    const kgPerYear = Math.max(1, (gPerL * volumeM3 * 1000 * batchesPerYear) / 1000);

    // Photobioreactor capital is the algal penalty: Acién's 3 m³ tubular plant
    // at 69 €/kg biomass is the anchor for how expensive this hardware is.
    const capex = capexPerKg(9.5e6, 120, volumeM3, kgPerYear);
    // TAP with acetate — you pay per litre processed, sell per kg product.
    const mediaPerL = 0.42;
    const media = (mediaPerL * 1000 * volumeM3) / kgPerYear * batchesPerYear / 1000 * 1000;
    // Lighting and mixing dominate algal utilities.
    const utilities = (0.31 * 1000 * volumeM3 * batchesPerYear) / 1000 / kgPerYear * 1000;
    const labor = (420000 * 4) / kgPerYear;
    // Mild PEF disruption is cheap; the penalty is in the yield term above.
    const downstream = 18 + 240 * (1 - recovery);
    const other = 6 + capex * 0.05;
    return lines({ capex, media, utilities, labor, downstream, other });
  },
  sensitivity: [
    { assumption: 'β-casein as % of cell mass', field: 'expression_pct_tsp' as const, lowPct: 92.4, hiPct: -38.1 },
    { assumption: 'Biomass density', field: 'final_biomass_density' as const, lowPct: 61.7, hiPct: -28.4 },
    { assumption: 'Disruption + recovery yield', field: 'disruption_protein_yield' as const, lowPct: 22.8, hiPct: -14.9 },
    { assumption: 'Photobioreactor capital', lowPct: -12.6, hiPct: 12.6 },
    { assumption: 'Medium cost', lowPct: -9.1, hiPct: 9.1 },
    { assumption: 'Labour', lowPct: -6.4, hiPct: 6.4 },
  ],
};

// ══ S2 — K. phaffii secreted comparator ════════════════════════════════
// Anchored on the two real eukaryotic data points: Choi & Jiménez-Flores
// (0.7–1.0 g/L bovine β-casein, intracellular) and Aro et al. (1 g/L secreted
// β-lactoglobulin from T. reesei) as the upper end of what secretion achieves.
const S2: CostModel = {
  modelId: 'S2',
  dims: [
    { key: 'titer', label: 'Secreted titer', unit: 'g L⁻¹', values: [0.05, 0.25, 0.5, 1, 2, 3, 5] },
    { key: 'scale', label: 'Fermenter scale', unit: 'm³', values: [20, 65, 110, 155, 200] },
    { key: 'dspYield', label: 'Downstream yield', unit: 'fraction', values: [0.55, 0.65, 0.75, 0.85] },
  ],
  referencePoint: { titer: 1, scale: 110, dspYield: 0.75 },
  evaluate: (p) => {
    const gPerL = Math.max(1e-6, p.titer * p.dspYield);
    const batchesPerYear = OPERATING_DAYS / 4; // ~4-day fed-batch cycle
    const kgPerYear = Math.max(1, (gPerL * p.scale * 1000 * batchesPerYear) / 1000);
    const capex = capexPerKg(7.2e6, 110, p.scale, kgPerYear);
    // Defined medium plus methanol feed; cheaper per litre than TAP but the
    // whole line still scales inversely with titer.
    const media = (0.55 * 1000 * p.scale * batchesPerYear) / kgPerYear;
    const utilities = (0.38 * 1000 * p.scale * batchesPerYear) / kgPerYear;
    const labor = (420000 * 5) / kgPerYear;
    // Secretion avoids disruption but adds chromatography-free capture cost;
    // Keppler & Boom argue purity should yield to functionality here.
    const downstream = 14 / p.dspYield + 6;
    const other = 5 + capex * 0.05;
    return lines({ capex, media, utilities, labor, downstream, other });
  },
  sensitivity: [
    { assumption: 'Secreted titer', field: 'titer_secreted' as const, lowPct: 118.3, hiPct: -41.2 },
    { assumption: 'Downstream yield', lowPct: 24.6, hiPct: -17.8 },
    { assumption: 'Fermenter scale', lowPct: 19.4, hiPct: -11.2 },
    { assumption: 'Medium cost', lowPct: -13.7, hiPct: 13.7 },
    { assumption: 'Fermenter capital', lowPct: -11.1, hiPct: 11.1 },
    { assumption: 'Labour', lowPct: -5.2, hiPct: 5.2 },
  ],
  nonConvergent: (p) => p.titer <= 0.05 && p.dspYield <= 0.55 && p.scale >= 200,
};

// ══ S3 — conventional β-casein isolation from milk ═════════════════════
// The incumbent baseline, and the comparison a faculty reviewer asks about
// first. Grounded in Atamer's review: β-casein is present in milk at ~2.6 g/L,
// and cold microfiltration recovers a fraction of it.
const S3: CostModel = {
  modelId: 'S3',
  dims: [
    { key: 'milkPrice', label: 'Raw milk price', unit: 'USD L⁻¹', values: [0.3, 0.4, 0.5, 0.6, 0.75] },
    { key: 'recovery', label: 'β-casein recovery', unit: 'fraction', values: [0.3, 0.45, 0.6, 0.75, 0.9] },
  ],
  referencePoint: { milkPrice: 0.45, recovery: 0.6 },
  evaluate: (p) => {
    const betaInMilk = 2.6; // g/L (Atamer et al. 2017)
    const gPerL = Math.max(1e-6, betaInMilk * p.recovery);
    const litresPerKg = 1000 / gPerL;
    // Milk is the feedstock; the rest of the cost is fractionation.
    const media = litresPerKg * p.milkPrice;
    const capex = 4.1;
    const utilities = litresPerKg * 0.004;
    const labor = 2.6;
    const downstream = 7.5 + 9 * (1 - p.recovery);
    const other = 1.8;
    return lines({ capex, media, utilities, labor, downstream, other });
  },
  sensitivity: [
    { assumption: 'Raw milk price', lowPct: -28.4, hiPct: 28.4 },
    { assumption: 'β-casein recovery', field: 'titer_secreted' as const, lowPct: 41.9, hiPct: -18.7 },
    { assumption: 'Microfiltration capital', lowPct: -6.2, hiPct: 6.2 },
    { assumption: 'Labour', lowPct: -3.9, hiPct: 3.9 },
    { assumption: 'Utilities', lowPct: -2.1, hiPct: 2.1 },
  ],
};

export const COST_MODELS: CostModel[] = [S1, S2, S3];

// ── Scenarios ─────────────────────────────────────────────────────────

export const SCENARIOS: Scenario[] = [
  {
    id: 'sc-s1',
    modelId: 'S1',
    name: 'cw15 intracellular β-casein',
    description:
      'Mixotrophic Chlamydomonas accumulating β-casein intracellularly, recovered by mild pulsed-electric-field disruption. The reference point sits where the literature actually is today — which is the bottom-left corner of this surface.',
    product: 'Bovine β-casein (intracellular)',
    dims: S1.dims.map((d) =>
      d.key === 'density'
        ? { ...d, paperId: 'M5' }
        : d.key === 'dispYield'
          ? { ...d, paperId: 'J10' }
          : { ...d, paperId: 'A1' },
    ),
    point: { ...S1.referencePoint },
    pinned: false,
    assumptions: [
      { label: 'Biomass density achieved (CC-137c, TAP)', value: 1.23, unit: 'g L⁻¹', provenance: 'curated', paperId: 'M5', basis: { kind: 'record', recordId: 'r-M5-1' }, note: 'Wild-type C. reinhardtii in TAP reached 1.23 g/L in 96 h. The reference point assumes 2 g/L — already optimistic against this.' },
      { label: 'Intracellular expression achieved (UVM4 reporters)', value: 0.2, unit: '% TSP', provenance: 'curated', paperId: 'A1', basis: { kind: 'record', recordId: 'r-A1-1' }, note: 'UVM4/UVM11 reach ~0.2% TSP for intracellular reporters. No casein has been expressed in any alga, so the % TSP axis is entirely extrapolation beyond this point.' },
      { label: 'PEF protein release, cell-wall-deficient', value: 31, unit: '% of total protein', provenance: 'curated', paperId: 'J10', basis: { kind: 'record', recordId: 'r-J10-1' }, note: 'Versus 11% for the walled wild type. The single strongest economic argument for cw15 as the chassis.' },
      { label: 'Safe-harbor integration uplift', value: 8.6, unit: '×', provenance: 'curated', paperId: 'A7', basis: { kind: 'record', recordId: 'r-A7-1' }, note: 'LHCBM1 locus integration gave 8.6-fold higher accumulation than random insertion — the most actionable published route up the % TSP axis.' },
      { label: 'Capital charge factor', value: 0.12, unit: '', provenance: 'demo', basis: { kind: 'model', justification: 'Financial convention, not a measurement. The annualisation rate applied to CAPEX is a modelling choice the corpus has no opinion on.' }, note: 'Annualisation rate. A modelling convention, not a measurement.' },
      { label: 'Operating days per year', value: 330, unit: 'd', provenance: 'demo', basis: { kind: 'model', justification: 'Plant availability assumption. A scheduling choice, not a property of the organism.' }, note: 'Standard availability assumption for a continuous plant.' },
      { label: 'CAPEX scaling exponent', value: 0.6, unit: '', provenance: 'demo', basis: { kind: 'model', justification: 'The six-tenths rule, standard practice for capacity scaling. Convention, not literature.' }, note: 'Six-tenths rule. Doubling capacity costs ~52% more, which is the main argument for building big.' },
      { label: 'Photobioreactor reference capital', value: 9500000, unit: 'USD', provenance: 'demo', basis: { kind: 'model', justification: 'Reference capital for the sizing basis. A vendor-class figure the corpus holds no record for.' }, note: 'Order-of-magnitude for a 120 m³ tubular installation, shaped by Acién’s real plant costs but not derived from them.' },
      { label: 'TAP medium cost', value: 0.42, unit: 'USD L⁻¹', provenance: 'demo', basis: { kind: 'model', justification: 'Media cost basis, priced from components rather than measured. Ontology v1 has no field for a per-litre medium price.' }, note: 'Includes acetate as the dominant carbon cost. Demo assumption — no citable price was retrieved.' },
      { label: 'Batch duration', value: 5, unit: 'd', provenance: 'curated', paperId: 'M6', basis: { kind: 'model', justification: 'From the M6 cultivation description. Ontology v1 has no field for batch duration, so no record exists to bind — an ontology gap, not an unsourced number.' }, note: 'Mixotrophic cultures reached maximum biomass in about 5 days.' },
      { label: 'Real plant biomass cost, 3.8 t/y', value: 69, unit: 'EUR kg⁻¹', provenance: 'curated', paperId: 'O4', basis: { kind: 'record', recordId: 'r-O4-1' }, note: 'Two years of operating data from a real 30 m³ tubular plant. Currency deliberately not converted.' },
      { label: 'Real plant biomass cost, scaled to 200 t/y', value: 12.6, unit: 'EUR kg⁻¹', provenance: 'curated', paperId: 'O4', basis: { kind: 'record', recordId: 'r-O4-2' }, note: 'The same plant simplified and scaled up — a 5.5× cost reduction from scale alone.' },
    ],
  },
  {
    id: 'sc-s2',
    modelId: 'S2',
    name: 'K. phaffii secreted comparator',
    description:
      'The incumbent precision-fermentation route: a secreting yeast at fed-batch density. Anchored on the two real eukaryotic data points — Choi & Jiménez-Flores for bovine β-casein and Aro et al. for what secretion achieves at its best.',
    product: 'Bovine β-casein (secreted)',
    dims: S2.dims.map((d) => (d.key === 'titer' ? { ...d, paperId: 'K1' } : d)),
    point: { ...S2.referencePoint },
    pinned: false,
    assumptions: [
      { label: 'β-lactoglobulin secreted titer (T. reesei)', value: 1.0, unit: 'g L⁻¹', provenance: 'curated', paperId: 'K1', basis: { kind: 'record', recordId: 'r-K1-1' }, note: 'The current benchmark for a secreted milk protein. No casein has reached this in any host.' },
      { label: 'β-casein intracellular (P. pastoris)', value: 0.85, unit: 'g L⁻¹', provenance: 'curated', paperId: 'H4', basis: { kind: 'record', recordId: 'r-H4-2' }, note: 'Reported as 0.7–1.0 g/L at 15–18% TSP. Note this was intracellular: secretion with the native signal peptide reached only 0.005%.' },
      { label: 'Secreted fraction, native signal peptide', value: 0.005, unit: '% of total expressed', provenance: 'curated', paperId: 'H4', basis: { kind: 'record', recordId: 'r-H4-3' }, note: 'The warning that a native bovine signal peptide will not work in a non-mammalian eukaryote.' },
      { label: 'Fed-batch cycle time', value: 4, unit: 'd', provenance: 'demo', basis: { kind: 'model', justification: 'Process schedule for the comparator. A modelling choice, not a measured quantity.' }, note: 'Typical methanol-induction fed-batch duration. Demo assumption.' },
      { label: 'Defined medium cost', value: 0.55, unit: 'USD L⁻¹', provenance: 'demo', basis: { kind: 'model', justification: 'Media cost basis for the yeast comparator. Priced, not measured, and outside the ontology.' }, note: 'Includes glycerol and methanol feed. Demo assumption.' },
      { label: 'Media share of COGS (industry claim)', value: 42, unit: '%', provenance: 'industry-estimate', basis: { kind: 'unsourced' }, note: 'Vendor and market sources put media at 35–50% of cost of goods. Non-peer-reviewed — excluded from aggregate statistics and never gold.' },
      { label: 'Published-model average titer', value: 24, unit: 'g L⁻¹', provenance: 'curated', paperId: 'O2', basis: { kind: 'record', recordId: 'r-O2-3' }, note: 'Across 55 published TEA models — an order of magnitude above anything achieved for casein.' },
      { label: 'Private-benchmark average titer', value: 42, unit: 'g L⁻¹', provenance: 'curated', paperId: 'O2', basis: { kind: 'record', recordId: 'r-O2-4' }, note: 'The gap between this and the published average is why GFI concludes published models systematically overstate cost.' },
      { label: 'Capital charge factor', value: 0.12, unit: '', provenance: 'demo', basis: { kind: 'model', justification: 'Financial convention, not a measurement. The annualisation rate applied to CAPEX is a modelling choice the corpus has no opinion on.' }, note: 'Annualisation rate, same convention as S1 so the two are comparable.' },
      { label: 'CAPEX scaling exponent', value: 0.6, unit: '', provenance: 'demo', basis: { kind: 'model', justification: 'The six-tenths rule, standard practice for capacity scaling. Convention, not literature.' }, note: 'Six-tenths rule.' },
    ],
  },
  {
    id: 'sc-s3',
    modelId: 'S3',
    name: 'Conventional β-casein from milk',
    description:
      'The incumbent baseline. Cold microfiltration of micellar casein concentrate, exploiting β-casein’s dissociation from the micelle at low temperature. This is what any recombinant route has to beat.',
    product: 'Bovine β-casein (dairy-derived)',
    dims: S3.dims,
    point: { ...S3.referencePoint },
    pinned: false,
    assumptions: [
      { label: 'β-casein concentration in bovine milk', value: 2.6, unit: 'g L⁻¹', provenance: 'curated', paperId: 'E1', basis: { kind: 'record', recordId: 'r-E1-1' }, note: 'The feedstock concentration that sets the whole cost structure — you process a litre to recover a couple of grams.' },
      { label: 'Casein share of total milk protein', value: 80, unit: '%', provenance: 'curated', paperId: 'E1', basis: { kind: 'record', recordId: 'r-E1-3' }, note: 'Caseins are ~80% of bovine milk protein; β-casein is ~36% of the casein fraction.' },
      { label: 'Isoelectric point', value: 4.65, unit: '', provenance: 'curated', paperId: 'E1', basis: { kind: 'record', recordId: 'r-E1-2' }, note: 'Caseins precipitate readily at pI on acidification — the basis of the simplest isolation route.' },
      { label: 'Cold microfiltration temperature', value: 4, unit: '°C', provenance: 'curated', paperId: 'J3', basis: { kind: 'model', justification: 'From the J3 process description. Ontology v1 has no field for a process temperature, so no record exists to bind — an ontology gap, not an unsourced number.' }, note: 'β-casein dissociates from the micelle into the serum phase at ≤4 °C, which is what makes the separation possible.' },
      { label: 'Raw milk price', value: 0.45, unit: 'USD L⁻¹', provenance: 'demo', basis: { kind: 'model', justification: 'Commodity price input. Market data rather than literature, and outside the ontology.' }, note: 'Commodity price varies by region and season. Demo assumption — swept as a dimension because it dominates.' },
      { label: 'Fractionation capital, annualised', value: 4.1, unit: 'USD kg⁻¹', provenance: 'demo', basis: { kind: 'model', justification: 'Annualised capital for the incumbent train. A modelling choice on the sizing basis.' }, note: 'Membrane plant capital per kg of β-casein. Demo assumption.' },
      { label: 'Residual biomass co-product value', value: 0.44, unit: 'EUR kg⁻¹', provenance: 'curated', paperId: 'O6', basis: { kind: 'record', recordId: 'r-O6-1' }, note: 'Protein-rich residual streams are worth very little, which limits how much credit any process can claim for them.' },
    ],
  },
];
