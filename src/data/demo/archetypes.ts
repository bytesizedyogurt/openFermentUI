// openFerment demo suite — archetype payloads.
//
// The six deliverables. Everything here references the shared pool in
// seed-core / seed-patents / seed-accessions; nothing invents a new number.
// Anything computable (envelope match, capex curve, expiry countdown) is left
// undefined here and filled by lib/* at load — see 00-BRIEF.md §4.
import type {
  Organism, Route, EnzymeStep, Candidate, FacilityConcept, ProblemNode,
  FactorMapEntry, RunDesignPoint, DisclosureCandidate, Deliverable, DemandVector,
} from './types';

// ══════════════════════════════════════════════════════════════════════
// Auxiliary organisms — pool extension for the capacity screen.
// Thin by design: these appear as candidate hosts, not as chassis pages.
// ══════════════════════════════════════════════════════════════════════

const aux = (id: string, binomial: string, designation: string, tC: [number, number], gras: boolean, note: string): Organism => ({
  id, binomial, designation, description: note, gramClass: 'gram-positive',
  competence: [], optima: { temperatureC: { low: tC[0], high: tC[1] }, ph: { low: 5, high: 7 } },
  constraints: [], gras, regulatoryNote: gras ? 'Established food or feed use.' : 'Product-by-product clearance.',
});

export const AUX_ORGANISMS: Organism[] = [
  { ...aux('ORG-ANI-01', 'Aspergillus niger', 'citric acid production strain', [30, 33], true, 'Filamentous, extremely high oxygen demand, pellet morphology governs everything.'), gramClass: 'filamentous-fungus' },
  { ...aux('ORG-ATE-01', 'Aspergillus terreus', 'itaconic acid production strain', [33, 37], false, 'Itaconate producer. Aerobic, morphology-sensitive, and it does not like transient limitation.'), gramClass: 'filamentous-fungus' },
  { ...aux('ORG-XCA-01', 'Xanthomonas campestris', 'xanthan production strain', [28, 30], true, 'Produces a broth so viscous that the installed power decides the process, not the biology.'), gramClass: 'gram-negative' },
  aux('ORG-RTR-01', 'Rhizobium tropici', 'CIAT 899-type inoculant strain', [28, 30], true, 'Legume inoculant. Low oxygen demand, low heat, and the product is the biomass.'),
  aux('ORG-BSU-01', 'Bacillus subtilis', 'enzyme production strain', [30, 37], true, 'Secretes at high titer. Moderate to high oxygen demand.'),
  aux('ORG-LPL-01', 'Lactiplantibacillus plantarum', 'starter culture strain', [30, 37], true, 'Microaerophilic, cheap to cool, and the product is a viable-cell count rather than a mass.'),
  { ...aux('ORG-TRE-01', 'Trichoderma reesei', 'cellulase production strain', [28, 30], false, 'Cellulase workhorse. Viscous, aerobic, long cycle.'), gramClass: 'filamentous-fungus' },
  { ...aux('ORG-YLI-01', 'Yarrowia lipolytica', 'oleaginous production strain', [28, 30], true, 'Oleaginous, aerobic, tolerant of hydrophobic substrates.'), gramClass: 'yeast' },
  aux('ORG-ASU-01', 'Actinobacillus succinogenes', 'succinate production strain', [37, 39], false, 'Capnophilic. Fixes CO₂, needs almost no oxygen, and generates almost no heat.'),
];

// ══════════════════════════════════════════════════════════════════════
// ARCHETYPE 1 — parameter gap. C. glutamicum, lysine, 5 L, twelve runs.
// ══════════════════════════════════════════════════════════════════════

export const LYSINE_FACTOR_MAP: FactorMapEntry[] = [
  {
    field: 'temperature', unit: '°C',
    domain: { low: 26, high: 42 },
    recommended: { low: 30, high: 33 },
    excluded: [
      { low: 37, high: 42, reason: 'Yield collapse. Growth continues, which is why this reads as viable in a growth-only screen and is not.', accessionIds: ['OF-A-00140', 'OF-A-00110'], singleSource: false },
      { low: 26, high: 28, reason: 'Rate penalty with no yield benefit. Excluded on economics, not on biology.', accessionIds: ['OF-A-00105'], singleSource: true },
    ],
    explored: [
      { low: 30, high: 30, accessionIds: ['OF-A-00105', 'OF-A-00109'] },
      { low: 33, high: 33, accessionIds: ['OF-A-00106', 'OF-A-00107', 'OF-A-00108'] },
      { low: 37, high: 37, accessionIds: ['OF-A-00140'] },
      { low: 39, high: 39, accessionIds: ['OF-A-00110'] },
    ],
    ftoFlag: { patentFamilyId: 'PF-002', recitedRange: { low: 32, high: 36 }, jurisdiction: 'RW' },
  },
  {
    field: 'ph', unit: '',
    domain: { low: 6.0, high: 8.0 },
    recommended: { low: 6.8, high: 7.4 },
    excluded: [
      { low: 6.0, high: 6.5, reason: 'Growth arrest at 40 h in the one working example that tested it; a 12 % titer penalty at 6.5 in the journal literature.', accessionIds: ['OF-A-00143', 'OF-A-00112'], singleSource: false },
      { low: 7.6, high: 8.0, reason: 'Trehalose accumulation. Carbon leaves the balance as a compatible solute.', accessionIds: ['OF-A-00113'], singleSource: true },
    ],
    explored: [
      { low: 6.3, high: 6.3, accessionIds: ['OF-A-00143'] },
      { low: 6.5, high: 6.5, accessionIds: ['OF-A-00112'] },
      { low: 7.0, high: 7.0, accessionIds: ['OF-A-00111', 'OF-A-00114'] },
      { low: 7.6, high: 7.6, accessionIds: ['OF-A-00113'] },
    ],
  },
  {
    field: 'dissolved_oxygen', unit: '%',
    domain: { low: 0, high: 60 },
    recommended: { low: 18, high: 30 },
    excluded: [
      { low: 0, high: 12, reason: 'Below the critical tension. Fermentative overflow to lactate and succinate; RQ rises above unity and carbon leaves as organic acid.', accessionIds: ['OF-A-00119', 'OF-A-00117', 'OF-A-00118', 'OF-A-00122'], singleSource: false },
      { low: 45, high: 60, reason: 'No titer benefit above 30 % and a 14 % power penalty. Excluded on cost.', accessionIds: ['OF-A-00120'], singleSource: true },
    ],
    explored: [
      { low: 5, high: 5, accessionIds: ['OF-A-00118'] },
      { low: 10, high: 10, accessionIds: ['OF-A-00117'] },
      { low: 15, high: 15, accessionIds: ['OF-A-00139'] },
      { low: 20, high: 20, accessionIds: ['OF-A-00116', 'OF-A-00151'] },
      { low: 30, high: 30, accessionIds: ['OF-A-00115', 'OF-A-00120', 'OF-A-00146'] },
    ],
    ftoFlag: { patentFamilyId: 'PF-001', recitedRange: { low: 20, high: 45 }, jurisdiction: 'RW' },
  },
  {
    field: 'mu_setpoint', unit: 'h⁻¹',
    domain: { low: 0.02, high: 0.30 },
    recommended: { low: 0.08, high: 0.15 },
    excluded: [
      { low: 0.20, high: 0.30, reason: 'Carbon partitions to biomass. Yield falls 16 % and the oxygen demand rises past what most vessels can transfer.', accessionIds: ['OF-A-00125'], singleSource: true },
      { low: 0.02, high: 0.06, reason: 'Cycle time to 96 h. Volumetric productivity falls 38 % even though specific productivity holds. Economic exclusion.', accessionIds: ['OF-A-00126'], singleSource: true },
    ],
    explored: [
      { low: 0.05, high: 0.05, accessionIds: ['OF-A-00126'] },
      { low: 0.10, high: 0.10, accessionIds: ['OF-A-00124'] },
      { low: 0.15, high: 0.15, accessionIds: ['OF-A-00123', 'OF-A-00127'] },
      { low: 0.22, high: 0.22, accessionIds: ['OF-A-00125'] },
    ],
  },
  {
    field: 'co2_overlay', unit: 'mM',
    domain: { low: 0, high: 120 },
    recommended: { low: 30, high: 60 },
    excluded: [
      { low: 100, high: 120, reason: 'No further yield gain and a pH control burden that shows up as base consumption rather than as a titer number.', accessionIds: ['OF-A-00132'], singleSource: true },
    ],
    explored: [
      { low: 0, high: 0, accessionIds: ['OF-A-00136'] },
      { low: 40, high: 40, accessionIds: ['OF-A-00131', 'OF-A-00132', 'OF-A-00133'] },
    ],
  },
  {
    field: 'biotin_conc', unit: 'mg L⁻¹',
    domain: { low: 0.01, high: 0.5 },
    recommended: { low: 0.15, high: 0.3 },
    excluded: [
      { low: 0.01, high: 0.06, reason: 'Biotin limitation switches the product spectrum to glutamate. This is a categorical switch, not a gradient, so the whole region is out rather than derated.', accessionIds: ['OF-A-00134'], singleSource: true },
    ],
    explored: [
      { low: 0.03, high: 0.03, accessionIds: ['OF-A-00134'] },
      { low: 0.2, high: 0.2, accessionIds: ['OF-A-00135'] },
    ],
  },
];

/**
 * Twelve runs, all landing in unexplored space. A 2³ factorial on the three
 * factors the map leaves genuinely open, two centre points for curvature, and
 * two confirmation runs at the predicted optimum.
 */
export const LYSINE_RUN_DESIGN: RunDesignPoint[] = [
  { run: 1, setpoints: { dissolved_oxygen: 14, co2_overlay: 0, mu_setpoint: 0.10 }, cell: 'DO−/HCO₃−/μ−', rationale: 'Corner. Tests whether the 12 % floor holds without bicarbonate support.' },
  { run: 2, setpoints: { dissolved_oxygen: 14, co2_overlay: 0, mu_setpoint: 0.15 }, cell: 'DO−/HCO₃−/μ+', rationale: 'Corner. Highest oxygen demand at the lowest supply — the most likely failure and worth knowing early.' },
  { run: 3, setpoints: { dissolved_oxygen: 14, co2_overlay: 40, mu_setpoint: 0.10 }, cell: 'DO−/HCO₃+/μ−', rationale: 'The predicted optimum region. Bicarbonate supports anaplerosis where oxygen is tight.' },
  { run: 4, setpoints: { dissolved_oxygen: 14, co2_overlay: 40, mu_setpoint: 0.15 }, cell: 'DO−/HCO₃+/μ+', rationale: 'Corner. Tests whether bicarbonate rescues the high-demand case.' },
  { run: 5, setpoints: { dissolved_oxygen: 18, co2_overlay: 0, mu_setpoint: 0.10 }, cell: 'DO+/HCO₃−/μ−', rationale: 'Corner at the edge of the disclosed region.' },
  { run: 6, setpoints: { dissolved_oxygen: 18, co2_overlay: 0, mu_setpoint: 0.15 }, cell: 'DO+/HCO₃−/μ+', rationale: 'Corner. Closest to the current 42 g/L operating point and the internal control for the block.' },
  { run: 7, setpoints: { dissolved_oxygen: 18, co2_overlay: 40, mu_setpoint: 0.10 }, cell: 'DO+/HCO₃+/μ−', rationale: 'Corner. Directly inside the region openFerment disclosed on 14 July 2026.' },
  { run: 8, setpoints: { dissolved_oxygen: 18, co2_overlay: 40, mu_setpoint: 0.15 }, cell: 'DO+/HCO₃+/μ+', rationale: 'Corner completing the factorial.' },
  { run: 9, setpoints: { dissolved_oxygen: 16, co2_overlay: 20, mu_setpoint: 0.125 }, cell: 'centre', rationale: 'Centre point. Curvature and pure-error estimate.' },
  { run: 10, setpoints: { dissolved_oxygen: 16, co2_overlay: 20, mu_setpoint: 0.125 }, cell: 'centre', rationale: 'Centre replicate. Without a replicate the block has no error term and every effect is uninterpretable.' },
  { run: 11, setpoints: { dissolved_oxygen: 15, co2_overlay: 40, mu_setpoint: 0.10 }, cell: 'confirmation', rationale: 'Confirmation at the predicted optimum, held for the last two slots so the prediction comes from runs 1–10.' },
  { run: 12, setpoints: { dissolved_oxygen: 15, co2_overlay: 40, mu_setpoint: 0.10 }, cell: 'confirmation', rationale: 'Confirmation replicate. Two points, or the confirmation is an anecdote.' },
];

// ══════════════════════════════════════════════════════════════════════
// ARCHETYPE 2 — 3-HP route selection.
// ══════════════════════════════════════════════════════════════════════

const step = (id: string, name: string, sub: string, prod: string, cof: string[], stoich: EnzymeStep['cofactorStoich'], org: string, claims: EnzymeStep['claims'], issues: string[], accs: string[]): EnzymeStep =>
  ({ id, name, substrate: sub, product: prod, cofactors: cof, cofactorStoich: stoich, sourceOrganism: org, claims, knownIssues: issues, accessionIds: accs });

export const ROUTES_3HP: Route[] = [
  {
    id: 'RTE-3HP-MCR', productId: '3-HP', name: 'Malonyl-CoA route',
    summary: 'Acetyl-CoA carboxylated to malonyl-CoA, then reduced twice to 3-HP by a bifunctional reductase expressed as two fragments.',
    steps: [
      step('STP-MCR-01', 'Acetyl-CoA carboxylase', 'acetyl-CoA', 'malonyl-CoA', ['ATP', 'HCO₃⁻'], [{ species: 'ATP', molPerMolProduct: 1 }], 'E. coli, native',
        [{ patentFamilyId: 'PF-004', jurisdictions: ['US', 'EP', 'CN', 'JP', 'BR', 'IN'], status: 'enclosed' }],
        ['Native regulation caps flux; overexpression is required and carries a growth penalty.'], ['OF-A-00205']),
      step('STP-MCR-02', 'Malonyl-CoA reductase, N-fragment', 'malonyl-CoA', 'malonate semialdehyde', ['NADPH'], [{ species: 'NADPH', molPerMolProduct: 1 }], 'Chloroflexus-type',
        [{ patentFamilyId: 'PF-004', jurisdictions: ['US', 'EP', 'CN', 'JP', 'BR', 'IN'], status: 'enclosed' }],
        ['The fragment split is the step that made the route work and it is the step that is claimed.'], ['OF-A-00224']),
      step('STP-MCR-03', 'Malonyl-CoA reductase, C-fragment', 'malonate semialdehyde', '3-HP', ['NADPH'], [{ species: 'NADPH', molPerMolProduct: 1 }], 'Chloroflexus-type',
        [{ patentFamilyId: 'PF-004', jurisdictions: ['US', 'EP', 'CN', 'JP', 'BR', 'IN'], status: 'enclosed' }],
        ['Aldehyde intermediate is not accumulated, which is the route\u2019s main advantage over the glycerol path.'], ['OF-A-00203']),
    ],
    hosts: [
      { organismId: 'ORG-ECO-01', bestTiter: 'OF-A-00203', note: 'The reference host. 40.6 g/L fed-batch.' },
      { organismId: 'ORG-SCE-01', bestTiter: 'OF-A-00216', note: 'Lower titer, and it is the only host that can produce below the pKa.' },
    ],
    theoreticalYieldAccessionId: 'OF-A-00201',
    oxygenDemand: 'high', byproducts: ['acetate', 'ethanol (yeast host)'], downstreamDifficulty: 'moderate',
    openSurface: { totalSteps: 3, enclosedSteps: 3, expiringSteps: 0 },
  },
  {
    id: 'RTE-3HP-BAL', productId: '3-HP', name: 'β-alanine route',
    summary: 'Aspartate decarboxylated to β-alanine, transaminated to malonate semialdehyde with pyruvate as acceptor, then reduced to 3-HP.',
    steps: [
      step('STP-BAL-01', 'Aspartate 1-decarboxylase', 'L-aspartate', 'β-alanine', ['pyruvoyl cofactor'], [], 'bacterial',
        [{ patentFamilyId: 'PF-005', jurisdictions: ['US', 'EP', 'CN'], status: 'enclosed' },
         { patentFamilyId: 'PF-008', jurisdictions: ['US', 'EP', 'CN', 'KR'], status: 'enclosed' }],
        ['Wild-type enzyme suffers mechanism-based inactivation. The variant that fixes it is separately claimed by PF-008.'], ['OF-A-00210']),
      step('STP-BAL-02', 'β-alanine–pyruvate aminotransferase', 'β-alanine', 'malonate semialdehyde', ['PLP', 'pyruvate'], [], 'bacterial',
        [{ patentFamilyId: 'PF-005', jurisdictions: ['US', 'EP', 'CN'], status: 'enclosed' }],
        ['Consumes pyruvate as acceptor; recycling determines whether the route is carbon-efficient or not.'], ['OF-A-00209']),
      step('STP-BAL-03', '3-hydroxypropionate dehydrogenase', 'malonate semialdehyde', '3-HP', ['NADPH'], [{ species: 'NADPH', molPerMolProduct: 1 }], 'E. coli, native',
        [{ patentFamilyId: 'PF-005', jurisdictions: ['US', 'EP', 'CN'], status: 'enclosed' }],
        ['Native activity is often sufficient, which makes this the least differentiated step in the route.'], ['OF-A-00208']),
    ],
    hosts: [{ organismId: 'ORG-ECO-01', bestTiter: 'OF-A-00208', note: '31.2 g/L. The lowest bacterial titer of the three and the highest theoretical ceiling.' }],
    theoreticalYieldAccessionId: 'OF-A-00206',
    oxygenDemand: 'moderate', byproducts: ['acetate', 'β-alanine carry-over'], downstreamDifficulty: 'moderate',
    openSurface: { totalSteps: 3, enclosedSteps: 3, expiringSteps: 0 },
  },
  {
    id: 'RTE-3HP-GLY', productId: '3-HP', name: 'Glycerol route',
    summary: 'Glycerol dehydrated to 3-hydroxypropionaldehyde by a B12-dependent dehydratase, then oxidised to 3-HP.',
    steps: [
      step('STP-GLY-01', 'Glycerol dehydratase, B12-dependent', 'glycerol', '3-HPA', ['coenzyme B12'], [], 'Klebsiella-type',
        [{ patentFamilyId: 'PF-006', jurisdictions: ['EP', 'US', 'CN'], status: 'expiring' }],
        ['Suicide inactivation requires a reactivase.', 'Coenzyme B12 must be fed unless the host makes it — the cost line, not a technical blocker.'], ['OF-A-00212']),
      step('STP-GLY-02', 'Aldehyde dehydrogenase', '3-HPA', '3-HP', ['NAD⁺'], [{ species: 'NADH', molPerMolProduct: -1 }], 'E. coli / Pseudomonas',
        [{ patentFamilyId: 'PF-006', jurisdictions: ['EP', 'US', 'CN'], status: 'expiring' }],
        ['3-HPA is toxic at 1.1 g/L; the oxidation must keep pace with the dehydration or the route poisons itself.'], ['OF-A-00214', 'OF-A-00218']),
    ],
    hosts: [
      { organismId: 'ORG-ECO-01', bestTiter: 'OF-A-00218', note: '71.9 g/L on crude glycerol. The highest titer in the pool, from a patent working example.' },
      { organismId: 'ORG-PDN-01', bestTiter: 'OF-A-00213', note: 'Makes its own B12, which removes the cost line that dominates the E. coli version.' },
    ],
    theoreticalYieldAccessionId: 'OF-A-00211',
    oxygenDemand: 'low', byproducts: ['1,3-propanediol', 'glycerol carry-over'], downstreamDifficulty: 'low',
    openSurface: { totalSteps: 2, enclosedSteps: 0, expiringSteps: 2 },
  },
];

// ══════════════════════════════════════════════════════════════════════
// ARCHETYPE 3 — capacity-first screen against PLT-KGL-01.
// `match` and `verdict` are computed by lib/envelope.ts. Left undefined.
// ══════════════════════════════════════════════════════════════════════

const dv = (otr: number, cool: number, pv: number, visc: DemandVector['viscosityClass'], sep: DemandVector['separationClass'], cyc: number, t: number): DemandVector =>
  ({ otrRequired: otr, coolingDutyKW: cool, powerPerVolume: pv, viscosityClass: visc, sterilityClass: 'aseptic', separationClass: sep, cycleTimeH: cyc, temperatureC: t });

const cnd = (
  id: string, product: string, hs: string | undefined, org: string, demand: DemandVector,
  fto: Candidate['patentPosition'], feed: string, feedAcc: string, trade: string[], reg: string, ttm: number, note: string,
): Candidate => ({ id, product, hsCode: hs, organismId: org, demand, patentPosition: fto, feedstock: feed, feedstockCostAccessionId: feedAcc, tradeAccessionIds: trade, regulatoryClass: reg, timeToRevenueMonths: ttm, note });

const FREE_RW: Candidate['patentPosition'] = [{ jurisdiction: 'RW', status: 'never-nationalised', familyIds: [] }];

export const CANDIDATES: Candidate[] = [
  cnd('CND-001', 'L-lysine HCl, feed grade', '2922.41', 'ORG-CGL-02', dv(118, 62, 1500, 'newtonian-low', 'centrifuge', 54, 30),
    [{ jurisdiction: 'RW', status: 'never-nationalised', familyIds: ['PF-001', 'PF-002', 'PF-003'] }],
    'cassava starch', 'OF-A-00301', ['OF-A-00310', 'OF-A-00311'], 'Feed additive', 22,
    'Fails at the published operating point on oxygen transfer before it fails on cooling. Survives only de-rated — see rescue.'),
  cnd('CND-002', 'L-lactic acid, thermophilic', '2918.11', 'ORG-BCG-01', dv(12, 9, 900, 'newtonian-low', 'filtration', 40, 52),
    [{ jurisdiction: 'RW', status: 'never-nationalised', familyIds: ['PF-012'] },
     { jurisdiction: 'US', status: 'enclosed', familyIds: ['PF-012'] },
     { jurisdiction: 'CN', status: 'enclosed', familyIds: ['PF-012'] },
     { jurisdiction: 'BR', status: 'enclosed', familyIds: ['PF-012'] }],
    'cassava starch', 'OF-A-00301', ['OF-A-00312', 'OF-A-00313'], 'Food acidulant', 14,
    'Free to make and sell in RW and across the EAC. Blocked for export to the US, China and Brazil by PF-012. The FTO failure here is a market failure, not a production one, and that distinction is the finding.'),
  cnd('CND-003', 'Citric acid', '2918.14', 'ORG-ANI-01', dv(145, 78, 2200, 'non-newtonian', 'crystallisation', 168, 32),
    FREE_RW, 'cassava starch', 'OF-A-00301', ['OF-A-00314', 'OF-A-00319'], 'Food acidulant', 20,
    'Largest import line in the survey and the process cannot be run here. Transient oxygen limitation does not slow citrate formation, it stops it, and the grid is intermittent.'),
  cnd('CND-004', 'Single-cell protein', '2102.20', 'ORG-YLI-01', dv(165, 88, 2000, 'newtonian-high', 'centrifuge', 36, 30),
    FREE_RW, 'brewery spent grain', 'OF-A-00303', ['OF-A-00316'], 'Feed ingredient', 26,
    'Highest oxygen demand in the screen. Nothing about the plant is close.'),
  cnd('CND-005', 'Rhizobial legume inoculant', '3101.00', 'ORG-RTR-01', dv(18, 14, 700, 'newtonian-low', 'centrifuge', 48, 29),
    FREE_RW, 'brewery spent grain', 'OF-A-00303', ['OF-A-00317'], 'Agricultural inoculant', 10,
    'Comfortable on every axis, small import line, and the spray dryer is the whole downstream train. The safe answer.'),
  cnd('CND-006', 'Xanthan gum', undefined, 'ORG-XCA-01', dv(55, 34, 4200, 'non-newtonian', 'extraction', 72, 28),
    FREE_RW, 'cassava starch', 'OF-A-00301', [], 'Food hydrocolloid', 24,
    'Fails on installed power, not on oxygen. At 3,200 mPa·s the Rushton train cannot move the broth, and adding power adds heat.'),
  cnd('CND-007', 'Itaconic acid', undefined, 'ORG-ATE-01', dv(95, 52, 1800, 'non-newtonian', 'crystallisation', 144, 35),
    FREE_RW, 'cassava starch', 'OF-A-00301', [], 'Chemical intermediate', 30, 'Aerobic and morphology-sensitive. Fails transfer.'),
  cnd('CND-008', 'Fungal cellulase concentrate', '3507.90', 'ORG-TRE-01', dv(72, 41, 2400, 'non-newtonian', 'filtration', 168, 29),
    FREE_RW, 'brewery spent grain', 'OF-A-00303', ['OF-A-00315'], 'Industrial enzyme', 28,
    'Highest unit value in the survey at 9,800 USD/t and the plant cannot transfer the oxygen. Worth revisiting if the vessels are ever re-impellered.'),
  cnd('CND-009', 'Bacterial α-amylase', '3507.90', 'ORG-BSU-01', dv(48, 31, 1500, 'newtonian-low', 'filtration', 60, 34),
    FREE_RW, 'cassava starch', 'OF-A-00301', ['OF-A-00315'], 'Industrial enzyme', 24,
    'Sits just under both ceilings. The second-place candidate and the one to promote if the lysine de-rating turns out to be unstable.'),
  cnd('CND-010', 'Lactic acid bacteria starter culture', undefined, 'ORG-LPL-01', dv(15, 11, 600, 'newtonian-low', 'centrifuge', 24, 34),
    FREE_RW, 'liquid whey', 'OF-A-00304', [], 'Food culture', 12,
    'Cheapest to run and the product is a viable-cell count, which makes the spray dryer a risk rather than an asset.'),
  cnd('CND-011', 'Succinic acid', undefined, 'ORG-ASU-01', dv(20, 13, 800, 'newtonian-low', 'crystallisation', 48, 38),
    FREE_RW, 'cassava starch', 'OF-A-00301', [], 'Chemical intermediate', 26,
    'Capnophilic and near-anaerobic. Fits the envelope easily and has no local market, which is the opposite failure from citric acid.'),
  cnd('CND-012', 'Baker\u2019s yeast, active dry', '2102.20', 'ORG-SCE-01', dv(88, 47, 1600, 'newtonian-low', 'centrifuge', 18, 30),
    FREE_RW, 'cassava starch', 'OF-A-00301', ['OF-A-00316'], 'Food ingredient', 16,
    'Classic tropical failure. Molasses-grade aerobic yeast propagation is a heat-transfer process wearing a biology costume.'),
  cnd('CND-013', 'Coffee-pulp protein hydrolysate', undefined, 'ORG-BSU-01', dv(26, 18, 1200, 'newtonian-high', 'filtration', 40, 34),
    FREE_RW, 'coffee pulp', 'OF-A-00302', [], 'Feed ingredient', 18,
    'Uses the residue with a disposal cost attached. Fits, and the market has to be created rather than displaced.'),
  cnd('CND-014', '2,3-butanediol', undefined, 'ORG-BSU-01', dv(35, 23, 1100, 'newtonian-low', 'distillation', 48, 34),
    FREE_RW, 'cassava starch', 'OF-A-00301', [], 'Chemical intermediate', 32,
    'Fits the vessels and fails downstream. There is no distillation column on site and adding one changes the plant.'),
  cnd('CND-015', 'Yeast extract from spent grain', '2102.20', 'ORG-SCE-01', dv(42, 28, 1300, 'newtonian-high', 'centrifuge', 30, 30),
    FREE_RW, 'brewery spent grain', 'OF-A-00303', ['OF-A-00316'], 'Food ingredient', 15, 'Marginal on cooling with the spent-grain solids load.'),
  cnd('CND-016', 'Bacillus biofungicide', undefined, 'ORG-BSU-01', dv(28, 19, 900, 'newtonian-low', 'centrifuge', 36, 32),
    FREE_RW, 'brewery spent grain', 'OF-A-00303', [], 'Biopesticide, registered', 34,
    'Fits comfortably. Registration is the long pole at 34 months, which is a regulatory constraint the envelope cannot see.'),
  cnd('CND-017', 'Vinegar-grade acetic acid', undefined, 'ORG-LPL-01', dv(60, 38, 1000, 'newtonian-low', 'distillation', 72, 30),
    FREE_RW, 'cassava starch', 'OF-A-00301', [], 'Food acidulant', 14, 'Acetification is more aerobic than people expect, and there is no column.'),
  cnd('CND-018', 'Xylitol from spent-grain pentose', '2905.44', 'ORG-YLI-01', dv(22, 16, 1200, 'newtonian-low', 'crystallisation', 60, 30),
    [{ jurisdiction: 'RW', status: 'never-nationalised', familyIds: ['PF-013'] }],
    'brewery spent grain', 'OF-A-00303', ['OF-A-00318'], 'Food ingredient', 28,
    'Xylitol bioconversion runs oxygen-limited by design — the cofactor balance requires it — so the modest OUR is a feature of the chemistry rather than a concession. Fits, high unit value, and PF-013 has expired almost everywhere. The bridge candidate into the greenfield concept.'),
];

/**
 * Attach the Archetype 1 de-rating to the candidate it rescues.
 *
 * ── THIS USED TO BE CALLED BY NOTHING BUT A GATE ──────────────────────────
 *
 * `scripts/check-demo-seed.ts` invoked it, asserted against the result, and the
 * app never did — so `Candidate.rescue` was `undefined` at runtime for every
 * candidate, and the rescue card on `/proforma/screen/:plant/c/CND-001` never
 * rendered. That card holds the only Proforma → fermOS link in the build, and
 * `screens/demo/Proforma.tsx`'s own header calls it "the argument for the
 * shared object pool". The argument was unreachable in a browser.
 *
 * Applied at module scope now, which is this pool's established shape for
 * anything derived rather than authored (`data/designs.ts` sweeps its grids the
 * same way). Idempotent, so a double invocation under StrictMode sets the same
 * object twice and changes nothing.
 */
export function applyRescues(cands: Candidate[]): void {
  const c = cands.find((x) => x.id === LYSINE_RESCUE.candidateId);
  if (c) c.rescue = { byDeliverableId: LYSINE_RESCUE.byDeliverableId, change: LYSINE_RESCUE.change, cost: LYSINE_RESCUE.cost };
}

export const LYSINE_RESCUE = {
  candidateId: 'CND-001',
  byDeliverableId: 'DLV-AR1-001',
  change:
    'Vessel head pressure to 1.5 bar absolute, raising C* by half; feed setpoint to μ = 0.10 h⁻¹ per OF-A-00124; final biomass de-rated to 20 g L⁻¹ per OF-A-00153. Peak OUR falls from 118 to 48 mmol L⁻¹ h⁻¹ (OF-A-00152).',
  cost:
    'Volumetric productivity falls roughly 45 % and cycle time extends. Cooling headroom at the de-rated point is 4.6 %, which is not a comfortable margin — it is the reason this candidate is promoted with a named risk rather than promoted clean.',
};

// Derived at load, never authored: the rescue is a fact Archetype 1 produced
// about an Archetype 3 candidate, and it has to be on the object before any
// screen reads it.
applyRescues(CANDIDATES);

// ══════════════════════════════════════════════════════════════════════
// ARCHETYPE 4 — bagasse greenfield. Capex left for lib/economics.ts.
// ══════════════════════════════════════════════════════════════════════

export const BAGASSE_CONCEPTS: FacilityConcept[] = [
  {
    id: 'FC-001', name: 'Two-stream: pentose to xylitol, hexose to thermophilic lactate',
    scaleTonnesPerYear: 18000, riskLevel: 'moderate',
    blockFlow: [
      { block: 'Feed handling', detail: '200,000 t/yr dry bagasse at 50 % moisture as received.', accessionIds: ['OF-A-00401', 'OF-A-00402', 'OF-A-00403'] },
      { block: 'Pretreatment', detail: 'Dilute acid at reduced severity. Sugar yield 0.61 g/g, furfural 2.4 g/L — above the organism tolerance, so severity is traded down against yield rather than detoxification being added.', accessionIds: ['OF-A-00407', 'OF-A-00411', 'OF-A-00404'] },
      { block: 'C5/C6 split', detail: 'Liquor and solids separated at the pretreatment discharge. This split is the concept.', accessionIds: ['OF-A-00402'] },
      { block: 'Enzymatic hydrolysis', detail: 'Cellulase on the solids fraction at 140 USD per tonne of sugar.', accessionIds: ['OF-A-00415'] },
      { block: 'C6 fermentation', detail: 'B. coagulans at 52 °C, lactate yield 0.88 g/g. No chiller: 24 K driving force against ambient cooling water.', accessionIds: ['OF-A-00406', 'OF-A-00305', 'OF-A-00306'] },
      { block: 'C5 conversion', detail: 'Xylose liquor to xylitol. PF-013 expired in the US and EP, expiring in China.', accessionIds: ['OF-A-00417'] },
      { block: 'Recovery', detail: 'Lactate by filtration and crystallisation; xylitol by crystallisation.', accessionIds: ['OF-A-00418', 'OF-A-00419'] },
    ],
    majorEquipment: [
      { item: 'Continuous dilute-acid reactor', sizingBasis: '25 t/h dry solids', costUSD: 9_400_000 },
      { item: 'Hydrolysis train, 4 × 400 m³', sizingBasis: '20 % solids loading, 72 h', costUSD: 7_100_000 },
      { item: 'Fermenters, 6 × 300 m³', sizingBasis: '40 h cycle at 52 °C, no chiller', costUSD: 8_800_000 },
      { item: 'Xylitol conversion and crystallisation', sizingBasis: 'C5 liquor at 4,800 t/yr sugar', costUSD: 11_200_000 },
      { item: 'Lactate recovery and purification', sizingBasis: '13,200 t/yr', costUSD: 6_900_000 },
      { item: 'Utilities, offsites, buildings', sizingBasis: '35 % of ISBL', costUSD: 15_200_000 },
    ],
    capexUSD: 58_600_000, capexAccuracyClass: 'AACE Class 5 (−30 / +50 %)',
    opexPerTonneUSD: 610,
    npvSensitivity: [
      { parameter: 'Xylitol price', lowPct: 41.2, highPct: -38.4 },
      { parameter: 'Pretreatment sugar yield', lowPct: 33.7, highPct: -24.9 },
      { parameter: 'Enzyme loading cost', lowPct: 19.8, highPct: -18.1 },
      { parameter: 'Lactate price', lowPct: 16.4, highPct: -15.2 },
      { parameter: 'Installed capital', lowPct: -12.8, highPct: 12.8 },
    ],
    patentOverlay: [
      { step: 'Dilute-acid pretreatment', status: 'expired', familyIds: [] },
      { step: 'Thermophilic C5/C6 lactate fermentation', status: 'never-nationalised', familyIds: ['PF-012'] },
      { step: 'Xylose to xylitol', status: 'expired', familyIds: ['PF-013'] },
    ],
    breakevenTonnesPerYear: 11200,
  },
  {
    id: 'FC-002', name: 'Single-stream organosolv to lactate, higher yield and higher capital',
    scaleTonnesPerYear: 22000, riskLevel: 'high',
    blockFlow: [
      { block: 'Pretreatment', detail: 'Organosolv with solvent recovery. Sugar yield 0.72 g/g and furfural 0.6 g/L, comfortably under tolerance. Both the best technical numbers in the comparison.', accessionIds: ['OF-A-00409', 'OF-A-00412'] },
      { block: 'Capital consequence', detail: 'Installed capital 1.9× the dilute-acid case at equal throughput, and the pretreatment step is claimed by PF-014 in EP, US and BR.', accessionIds: ['OF-A-00413'] },
      { block: 'Fermentation', detail: 'B. coagulans at 52 °C on the combined stream.', accessionIds: ['OF-A-00406'] },
    ],
    majorEquipment: [
      { item: 'Organosolv reactor and solvent recovery', sizingBasis: '25 t/h dry solids', costUSD: 26_800_000 },
      { item: 'Hydrolysis and fermentation train', sizingBasis: '22,000 t/yr lactate', costUSD: 14_300_000 },
      { item: 'Recovery and purification', sizingBasis: '22,000 t/yr', costUSD: 8_400_000 },
      { item: 'Utilities, offsites, buildings', sizingBasis: '35 % of ISBL', costUSD: 17_300_000 },
    ],
    capexUSD: 66_800_000, capexAccuracyClass: 'AACE Class 5 (−30 / +50 %)',
    opexPerTonneUSD: 545,
    npvSensitivity: [
      { parameter: 'Solvent recovery efficiency', lowPct: 52.6, highPct: -31.4 },
      { parameter: 'Installed capital', lowPct: -24.1, highPct: 24.1 },
      { parameter: 'Lactate price', lowPct: 22.9, highPct: -21.0 },
      { parameter: 'Licence royalty on PF-014', lowPct: 8.8, highPct: -8.8 },
    ],
    patentOverlay: [
      { step: 'Organosolv fractionation with solvent recovery', status: 'enclosed', familyIds: ['PF-014'] },
      { step: 'Thermophilic lactate fermentation', status: 'never-nationalised', familyIds: ['PF-012'] },
    ],
    breakevenTonnesPerYear: 17400,
  },
  {
    id: 'FC-003', name: 'Minimum-viable: hexose only, lactate, no C5 valorisation',
    scaleTonnesPerYear: 8000, riskLevel: 'low',
    blockFlow: [
      { block: 'Pretreatment', detail: 'Steam explosion. Lowest capital, lowest sugar yield at 0.58 g/g.', accessionIds: ['OF-A-00408'] },
      { block: 'C5 disposal', detail: 'Pentose liquor to the existing boiler. Twenty-seven percent of the feedstock keeps being burned, which is the thing this concept concedes.', accessionIds: ['OF-A-00402'] },
      { block: 'Fermentation and recovery', detail: 'B. coagulans at 52 °C, filtration and crystallisation.', accessionIds: ['OF-A-00406', 'OF-A-00418'] },
    ],
    majorEquipment: [
      { item: 'Steam explosion unit', sizingBasis: '11 t/h dry solids', costUSD: 5_600_000 },
      { item: 'Fermentation train, 3 × 300 m³', sizingBasis: '8,000 t/yr', costUSD: 5_200_000 },
      { item: 'Recovery', sizingBasis: '8,000 t/yr', costUSD: 4_100_000 },
      { item: 'Utilities and offsites', sizingBasis: '30 % of ISBL', costUSD: 4_500_000 },
    ],
    capexUSD: 19_400_000, capexAccuracyClass: 'AACE Class 4 (−20 / +30 %)',
    opexPerTonneUSD: 720,
    npvSensitivity: [
      { parameter: 'Lactate price', lowPct: 38.1, highPct: -35.7 },
      { parameter: 'Feedstock cost', lowPct: 14.2, highPct: -14.2 },
      { parameter: 'Installed capital', lowPct: -11.6, highPct: 11.6 },
    ],
    patentOverlay: [
      { step: 'Steam explosion', status: 'expired', familyIds: [] },
      { step: 'Thermophilic lactate fermentation', status: 'never-nationalised', familyIds: ['PF-012'] },
    ],
    breakevenTonnesPerYear: 6300,
  },
];

// ══════════════════════════════════════════════════════════════════════
// ARCHETYPE 5 — decomposition. Structurally rich, numerically light.
// ══════════════════════════════════════════════════════════════════════

export const BURGER_TREE: ProblemNode[] = [
  { id: 'PN-000', label: 'A burger a normal consumer cannot distinguish from beef',
    candidateOrganismIds: [], patentDensity: 'high', technicalMaturity: 'pilot', recommendation: 'build',
    rationale: 'Not a fermentation target. It decomposes into three independent problems with different organisms, different processes and — the finding — dramatically different patent landscapes.',
    accessionIds: [] },

  { id: 'PN-100', parentId: 'PN-000', label: 'Flavour and colour: the heme carrier', molecularTarget: 'Recombinant heme-containing globin at ≥0.8 % of formulation mass',
    candidateOrganismIds: ['ORG-KPH-01'], patentDensity: 'very-high', technicalMaturity: 'demonstrated', recommendation: 'avoid',
    rationale: 'Technically solved and commercially closed. PF-009 covers both the composition and the production method across eight jurisdictions, and the required concentration in OF-A-00501 sits inside the recited range. Occupancy at 62 % is the real quality attribute and titer alone is misleading.',
    accessionIds: ['OF-A-00501', 'OF-A-00502', 'OF-A-00503', 'OF-A-00504'], spawnsFlowId: 'AR2' },
  { id: 'PN-110', parentId: 'PN-100', label: 'Alternative: non-globin Maillard precursor system',
    candidateOrganismIds: ['ORG-SCE-01'], patentDensity: 'low', technicalMaturity: 'lab', recommendation: 'build',
    rationale: 'Cysteine, ribose and thiamine precursors generate much of the same thermal flavour chemistry without a heme protein. Loses the raw-to-cooked colour transition, which OF-A-00504 says happens at 68 °C and which consumers read as doneness. A partial substitute with a named deficit.',
    accessionIds: ['OF-A-00504'] },

  { id: 'PN-200', parentId: 'PN-000', label: 'Mouthfeel: the structured fat phase', molecularTarget: 'Triacylglycerol blend solid at 20 °C, substantially melted at 35 °C',
    candidateOrganismIds: ['ORG-RTO-01', 'ORG-YLI-01'], patentDensity: 'low', technicalMaturity: 'lab', recommendation: 'build',
    rationale: 'The open field, and the asymmetry against PN-100 is the whole answer to the query. PF-010 is in force in one jurisdiction and pending in one more; no microbial route to the target profile is claimed by anyone in this pool. The technical gap is well posed: beef fat melts across 28–45 °C, the incumbent plant fat across 24–26 °C, and R. toruloides reaches 58 % lipid with a profile tunable by nitrogen regime.',
    accessionIds: ['OF-A-00505', 'OF-A-00506', 'OF-A-00507', 'OF-A-00508'], spawnsFlowId: 'AR2' },
  { id: 'PN-210', parentId: 'PN-200', label: 'Constraint inherited from Archetype 3',
    candidateOrganismIds: ['ORG-RTO-01'], patentDensity: 'low', technicalMaturity: 'lab', recommendation: 'build',
    rationale: 'Lipid accumulation is aerobic and high-OUR. Any plant in a warm ambient hits the same cooling wall the capacity screen found, so this branch inherits a siting constraint from a completely different archetype.',
    accessionIds: ['OF-A-00507', 'OF-A-00325'] },

  { id: 'PN-300', parentId: 'PN-000', label: 'Bite: the fibrous protein matrix', molecularTarget: 'Anisotropic protein structure, index ≈ 3.4',
    candidateOrganismIds: ['ORG-FVE-01'], patentDensity: 'moderate', technicalMaturity: 'demonstrated', recommendation: 'build',
    rationale: 'Two structurally different routes to the same measured outcome. Shear-cell texturisation reaches an anisotropy index of 3.4 and is claimed by PF-011 in three jurisdictions; native hyphal morphology reaches the same 3.4 and is claimed by nobody. Identical outcome, one route enclosed. Route around rather than license.',
    accessionIds: ['OF-A-00509', 'OF-A-00511'] },
  { id: 'PN-310', parentId: 'PN-300', label: 'Hidden unit operation: RNA reduction',
    candidateOrganismIds: ['ORG-FVE-01'], patentDensity: 'low', technicalMaturity: 'demonstrated', recommendation: 'build',
    rationale: 'Food use requires RNA below 2 % w/w. A real unit operation with real yield loss, invisible in every paper about the organism, and it changes the process economics of the whole branch. Run length is separately capped at about 1,000 h by colonial mutants.',
    accessionIds: ['OF-A-00512', 'OF-A-00510'] },

  { id: 'PN-400', parentId: 'PN-000', label: 'Binding and cook-loss', molecularTarget: 'Gelling protein or polysaccharide system',
    candidateOrganismIds: ['ORG-BSU-01'], patentDensity: 'moderate', technicalMaturity: 'demonstrated', recommendation: 'license',
    rationale: 'Well served by existing ingredients. Nothing here justifies a fermentation programme, and saying so is more useful than adding a fourth branch.',
    accessionIds: [] },
];

// ══════════════════════════════════════════════════════════════════════
// Disclosure candidates — the thesis, one per archetype minimum.
// ══════════════════════════════════════════════════════════════════════

export const DISCLOSURES: DisclosureCandidate[] = [
  { id: 'DC-001', archetype: 'AR1', what: 'Lysine fed-batch at 12–18 % dissolved oxygen with 30–60 mM bicarbonate in a pyruvate carboxylase overexpressing Corynebacterium.',
    enablingDetail: ['Strain genotype', 'Medium composition including bicarbonate salt and counter-ion', 'Feed profile and μ setpoint', 'DO control cascade and agitation limits', 'Titer, yield and byproduct spectrum at harvest'],
    reason: 'parameter-region-open', urgency: 'now',
    supportingAccessionIds: ['OF-A-00116', 'OF-A-00131', 'OF-A-00132', 'OF-A-00151'], venue: 'Research Disclosure, plus deposit to BioRepo with a provable date',
  },
  { id: 'DC-002', archetype: 'AR1', what: 'The negative result at 15 % dissolved oxygen without bicarbonate support, published as a bounded failure rather than left as a patent comparative example.',
    enablingDetail: ['Conditions', 'Byproduct time course', 'The cell density at which the boundary was measured, which the existing comparative example does not state'],
    reason: 'negative-result-unpublished', urgency: 'months',
    supportingAccessionIds: ['OF-A-00139', 'OF-A-00117'], venue: 'Research Disclosure',
  },
  { id: 'DC-003', archetype: 'AR2', what: 'Aspartate 1-decarboxylase variants outside the PF-008 substitution set that address mechanism-based inactivation.',
    enablingDetail: ['Substitution positions and rationale', 'Activity retention over a production window', 'Expression construct and host'],
    reason: 'enzyme-variant-at-risk', urgency: 'now', estimatedWindowMonths: 12,
    supportingAccessionIds: ['OF-A-00210', 'OF-A-00208'], venue: 'Preprint plus sequence deposit',
  },
  { id: 'DC-004', archetype: 'AR2', what: 'Glycerol-route process improvements timed to PF-006 expiry in 2030, disclosed now so the post-expiry space cannot be re-enclosed by improvement patents.',
    enablingDetail: ['Reactivase co-expression ratio', '3-HPA accumulation control strategy', 'B12 feeding schedule or native-producer host substitution'],
    reason: 'jurisdictional-gap', urgency: 'watch', estimatedWindowMonths: 48,
    supportingAccessionIds: ['OF-A-00212', 'OF-A-00214', 'OF-A-00218'], venue: 'Research Disclosure',
  },
  { id: 'DC-005', archetype: 'AR3', what: 'De-rated lysine operation for oxygen-transfer-limited vessels: elevated head pressure with reduced μ and de-rated final biomass.',
    enablingDetail: ['Head pressure and its effect on C*', 'Feed profile', 'Peak OUR and the cooling duty it implies', 'Volumetric productivity penalty, stated honestly'],
    reason: 'unclaimed-process-region', urgency: 'now',
    supportingAccessionIds: ['OF-A-00152', 'OF-A-00153', 'OF-A-00124', 'OF-A-00308'], venue: 'Research Disclosure',
    // The most strategically loaded entry in the queue: it discloses the exact
    // process region that makes under-specified plants viable, which is the
    // region an incumbent would most want to claim.
  },
  { id: 'DC-006', archetype: 'AR4', what: 'Two-stream bagasse conversion with pentose to xylitol and hexose to thermophilic lactate, at reduced pretreatment severity matched to organism inhibitor tolerance.',
    enablingDetail: ['Severity factor and resulting inhibitor profile', 'C5/C6 split point and stream compositions', 'Fermentation conditions for both streams', 'Mass balance closure'],
    reason: 'unclaimed-process-region', urgency: 'months',
    supportingAccessionIds: ['OF-A-00404', 'OF-A-00406', 'OF-A-00407', 'OF-A-00411'], venue: 'Peer-reviewed publication plus Research Disclosure',
  },
  { id: 'DC-007', archetype: 'AR5', what: 'Microbial routes to a triacylglycerol profile solid at 20 °C and substantially melted at 35 °C.',
    enablingDetail: ['Organism and nitrogen regime', 'Fatty acid profile and solid fat content curve', 'Extraction and fractionation route', 'The measured melting band against the beef reference'],
    reason: 'unclaimed-process-region', urgency: 'now', estimatedWindowMonths: 18,
    supportingAccessionIds: ['OF-A-00505', 'OF-A-00506', 'OF-A-00507', 'OF-A-00508'], venue: 'Preprint plus Research Disclosure',
  },
  { id: 'DC-008', archetype: 'AR5', what: 'Native-morphology fibrous matrix reaching the same anisotropy index as claimed shear-cell texturisation.',
    enablingDetail: ['Organism and culture conditions', 'Harvest and alignment measurement method', 'Anisotropy index against the texturised reference'],
    reason: 'enzyme-variant-at-risk', urgency: 'months',
    supportingAccessionIds: ['OF-A-00509', 'OF-A-00511'], venue: 'Research Disclosure',
  },
  { id: 'DC-009', archetype: 'AR6', what: 'Excursion adjudication criteria for dissolved oxygen transients in amino acid fed-batch, including the integrated-deficit threshold above which a run stops being comparable.',
    enablingDetail: ['Channel set and sampling rate', 'Integration method for O₂ deficit and CER deviation', 'The carbon-balance closure gap that corresponds to a given transient', 'Decision rule and its false-positive behaviour'],
    reason: 'unclaimed-process-region', urgency: 'months',
    supportingAccessionIds: ['OF-A-00119', 'OF-A-00122', 'OF-A-00148', 'OF-A-00150'], venue: 'Research Disclosure plus method paper',
  },
];

// ══════════════════════════════════════════════════════════════════════
// Deliverables — addressable artifacts. Payloads reference the above.
// ══════════════════════════════════════════════════════════════════════

export const DELIVERABLES: Deliverable[] = [
  { id: 'DLV-AR1-001', archetype: 'AR1', title: 'Lysine process-space gap map, 5 L, twelve runs',
    query: 'C. glutamicum ATCC 13032 derivative, lysine, 5 L Sartorius, currently 42 g/L at 30 °C / pH 7.0 / DO 30 % / exponential feed at μ = 0.15. Twelve runs before a Q3 review. Which factor combinations are covered, and which are excluded — including the ones nobody published as failures?',
    createdAt: '2026-08-19T11:04:00Z',
    accessionIds: LYSINE_FACTOR_MAP.flatMap((f) => [...f.excluded.flatMap((e) => e.accessionIds), ...f.explored.flatMap((e) => e.accessionIds)]),
    disclosureCandidateIds: ['DC-001', 'DC-002'],
    payload: { kind: 'factor-map', factors: LYSINE_FACTOR_MAP, design: LYSINE_RUN_DESIGN, excludedAccessionIds: ['OF-A-00147', 'OF-A-00148', 'OF-A-00150'] } },

  { id: 'DLV-AR2-001', archetype: 'AR2', title: '3-HP route comparison with claim overlay',
    query: 'Compare the malonyl-CoA, β-alanine and glycerol routes to 3-HP across E. coli, S. cerevisiae and P. pastoris. Which enzyme steps are enclosed by live patents, and which route has the most open surface?',
    createdAt: '2026-08-20T09:22:00Z',
    accessionIds: ['OF-A-00201', 'OF-A-00203', 'OF-A-00206', 'OF-A-00208', 'OF-A-00211', 'OF-A-00212', 'OF-A-00215', 'OF-A-00216', 'OF-A-00218'],
    disclosureCandidateIds: ['DC-003', 'DC-004'],
    payload: { kind: 'route-comparison', productId: '3-HP', routeIds: ['RTE-3HP-MCR', 'RTE-3HP-BAL', 'RTE-3HP-GLY'],
      recommendation: 'Glycerol route, and it is the technically second-best answer on yield ceiling.',
      asymmetry: 'The β-alanine route has the highest theoretical ceiling at 1.24 mol/mol and every one of its three steps is enclosed, one of them by a variant claim filed in 2020 that runs to 2040. The glycerol route has the lowest step count, the highest achieved titer, and both of its steps sit under a single family expiring in 2030. Route selection here is decided by expiry dates rather than by biochemistry.' } },

  { id: 'DLV-AR3-001', archetype: 'AR3', title: 'Capacity screen — Kigali, two 5 m³ vessels',
    query: 'Two 5 m³ jacketed SIP-capable vessels, Rushton, 1.5 kW/m³, 1 VVM, 80 kW chilled water at 12 °C, disc-stack centrifuge, 50 kg/h spray dryer. Feedstocks within 200 km. What can I make that fits, carries no live patent here, and currently enters the region as an import at volume?',
    createdAt: '2026-08-20T15:40:00Z',
    accessionIds: ['OF-A-00307', 'OF-A-00308', 'OF-A-00321', 'OF-A-00320', 'OF-A-00305', 'OF-A-00310', 'OF-A-00311', 'OF-A-00324', 'OF-A-00325', 'OF-A-00152'],
    disclosureCandidateIds: ['DC-005'],
    payload: { kind: 'capacity-screen', plantId: 'PLT-KGL-01', candidateIds: CANDIDATES.map((c) => c.id), promotedId: 'CND-001' } },

  { id: 'DLV-AR4-001', archetype: 'AR4', title: 'Bagasse facility concepts, three scales',
    query: '400,000 t/yr sugarcane bagasse currently burned for low-value steam. Design the highest-return lignocellulosic conversion pathway and give me capital cost against scale.',
    createdAt: '2026-08-21T08:15:00Z',
    accessionIds: ['OF-A-00401', 'OF-A-00402', 'OF-A-00404', 'OF-A-00407', 'OF-A-00409', 'OF-A-00411', 'OF-A-00412', 'OF-A-00413', 'OF-A-00416', 'OF-A-00417', 'OF-A-00418', 'OF-A-00419'],
    disclosureCandidateIds: ['DC-006'],
    payload: { kind: 'facility-concept', concepts: BAGASSE_CONCEPTS } },

  { id: 'DLV-AR5-001', archetype: 'AR5', title: 'Burger decomposition',
    query: 'I want to make a burger through precision fermentation that a normal consumer cannot distinguish from beef. Where do I start?',
    createdAt: '2026-08-21T10:02:00Z',
    accessionIds: ['OF-A-00501', 'OF-A-00502', 'OF-A-00503', 'OF-A-00505', 'OF-A-00506', 'OF-A-00507', 'OF-A-00509', 'OF-A-00511', 'OF-A-00512'],
    disclosureCandidateIds: ['DC-007', 'DC-008'],
    payload: { kind: 'problem-tree', rootId: 'PN-000', nodes: BURGER_TREE, handoffFlowIds: ['AR2'] } },

  { id: 'DLV-AR6-001', archetype: 'AR6', title: 'RUN-047 excursion adjudication',
    query: 'Run 47, Tick 340. DO crashed to 8 % for eleven minutes and recovered. Off-gas CO₂ shifted 0.4 % and has not returned to trajectory. Is this batch still comparable to the prior runs in the Ledger?',
    createdAt: '2026-08-18T16:47:00Z',
    accessionIds: ['OF-A-00119', 'OF-A-00122', 'OF-A-00147', 'OF-A-00148', 'OF-A-00149', 'OF-A-00150'],
    disclosureCandidateIds: ['DC-009'],
    payload: { kind: 'excursion-verdict', runId: 'RUN-047', verdict: {
      comparable: false, recommendation: 'continue-flagged',
      reasoning: [
        'DO fell to 8 %, which is the critical tension for this organism rather than a margin above it (OF-A-00119). At the critical point respiration becomes transport-limited and the fermentative branch opens.',
        'RQ rose above unity during the window, the same signature recorded under sustained limitation (OF-A-00122). The transient was metabolically real, not an instrument artefact.',
        'Lactate at harvest reached 0.47 g L⁻¹ (OF-A-00148) against a basis where it is not detected. Carbon that should have gone to product left as organic acid.',
        'Carbon balance closure fell to 94.9 % against a five-run basis of 96.2 ± 0.4 (OF-A-00150, OF-A-00149). A 1.3-point gap is about three standard deviations of the basis, and it is small enough that nobody watching the chart would have flagged it.',
        'Respiratory quotient settled above its pre-excursion baseline and stayed there for the remainder of the run, which is what the operator saw as a shifted off-gas CO₂ reading. Dissolved oxygen did recover; the metabolism did not. That divergence is the discriminator, and a run where both recovered would be continued unflagged.',
      ],
      basisRunIds: ['RUN-042', 'RUN-043', 'RUN-044', 'RUN-045', 'RUN-046'],
      annotation: { accessionIds: ['OF-A-00147', 'OF-A-00148', 'OF-A-00150'], hold: 'excursion-flagged',
        note: 'Product formed and the run is worth finishing for material. It is not comparable to the basis and must not enter a factor map, a median, or a yield claim. The flag propagates: OF-A-00147 renders held on the Archetype 1 gap map with this run as the reason.' },
    } } },
];

export const DELIVERABLE_BY_ID: Record<string, Deliverable> = Object.fromEntries(DELIVERABLES.map((d) => [d.id, d]));
