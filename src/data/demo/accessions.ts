// openFerment demo suite — the Accession pool.
//
// One quantity, complete provenance, permanent identifier. Every number the
// six archetypes display resolves here or is computed from several of these.
//
// NORMALISATION IS VERIFIED, NOT TRUSTED. `verifyNormalisation()` at the
// bottom recomputes every `normalized` from `reported` and throws on mismatch.
// Wire it into scripts/check-seed.ts. The authored value is a convenience for
// reading the file; the computed value is the one the UI must display.
//
// Substance real, identifiers synthetic. See SEED_DISCLAIMER in seed-core.ts.
import type { Accession, FieldId, Provenance, SourceType, HoldReason, Derivation } from './types';
import { MOLAR_MASS, UNIT_TABLE } from './core';

const LED = (action: string, who = 'Intake', at = '2026-07-14T09:00:00Z') => [{ at, who, action }];

interface AccInput {
  id: string;
  field: FieldId;
  rep: [number, string];
  norm: [number, string];
  der?: Derivation;
  src: string;
  st: SourceType;
  loc: string;
  q?: string;
  prov?: Provenance;
  conf?: number;
  primary?: boolean;
  hold?: HoldReason;
  cites?: string;
  ctx?: Accession['context'];
  pf?: string;
  run?: string;
  conflicts?: string[];
  reconciled?: string[];
  conflictNote?: string;
  range?: [number, number];
  sd?: number;
  n?: number;
  poolOnly?: boolean;
  note?: string;
}

function a(i: AccInput): Accession {
  return {
    id: i.id,
    field: i.field,
    reported: {
      value: i.rep[0], unit: i.rep[1],
      ...(i.range ? { range: { low: i.range[0], high: i.range[1] } } : {}),
      ...(i.sd !== undefined ? { sd: i.sd } : {}),
      ...(i.n !== undefined ? { n: i.n } : {}),
    },
    normalized: { value: i.norm[0], unit: i.norm[1] },
    derivation: i.der ?? { fn: 'identity', usingAccessionIds: [], note: 'Reported in the canonical unit.' },
    sourceId: i.src,
    sourceType: i.st,
    locator: i.loc,
    quote: i.q,
    provenance: i.prov ?? 'verified',
    confidence: i.conf ?? 0.92,
    isPrimary: i.primary ?? true,
    hold: i.hold,
    citesAccessionId: i.cites,
    context: i.ctx ?? {},
    patentFamilyId: i.pf,
    runId: i.run,
    conflictsWith: i.conflicts,
    reconciledWith: i.reconciled,
    conflictNote: i.conflictNote,
    poolOnly: i.poolOnly,
    ledger: LED(i.note ?? 'Extracted and normalised from source.'),
  };
}

const CGL = { organismId: 'ORG-CGL-02', productId: 'L-lysine', scale: '5 L', mode: 'fed-batch' as const };

// ══════════════════════════════════════════════════════════════════════
// CLUSTER 1 — Corynebacterium glutamicum, L-lysine, process space
// Consumed by Archetype 1 (factor map), Archetype 3 (capacity), Archetype 6.
// ══════════════════════════════════════════════════════════════════════

export const ACCESSIONS_LYSINE: Accession[] = [
  // --- strain and stoichiometry ---
  a({ id: 'OF-A-00101', field: 'titer', rep: [0, 'g L⁻¹'], norm: [0, 'g L⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§3.1 Table 1',
      q: 'no lysine detected in culture supernatant of the parental strain', ctx: { ...CGL, organismId: 'ORG-CGL-01' },
      note: 'Negative control for the whole cluster. Wild-type aspartokinase is feedback-inhibited, so the parent makes none.' }),
  a({ id: 'OF-A-00102', field: 'titer', rep: [118, 'g L⁻¹'], norm: [118, 'g L⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§4.2 Fig. 3', prov: 'gold',
      q: 'final titer of 118 g/L at 54 h', ctx: CGL }),
  a({ id: 'OF-A-00103', field: 'cofactor_demand', rep: [4, 'mol mol⁻¹'], norm: [4, 'mol mol⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§2 Eq. 4',
      q: 'four moles NADPH per mole lysine', ctx: { productId: 'L-lysine' },
      note: 'The stoichiometric fact that makes pentose phosphate flux the ceiling. Feeding harder does not raise it.' }),
  a({ id: 'OF-A-00104', field: 'specific_productivity', rep: [0.121, 'g gDCW⁻¹ h⁻¹'], norm: [0.121, 'g gDCW⁻¹ h⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§4.4', ctx: CGL }),

  // --- temperature ---
  a({ id: 'OF-A-00105', field: 'temperature', rep: [30, '°C'], norm: [30, '°C'], src: 'SRC-0001', st: 'journal', loc: '§3.2 Methods', ctx: CGL }),
  a({ id: 'OF-A-00106', field: 'titer', rep: [104.8, 'g L⁻¹'], norm: [104.8, 'g L⁻¹'], src: 'SRC-0003', st: 'journal', loc: '§4.1 Table 2',
      q: 'shifting to 33 °C at 20 h raised final titer by 9 % against the isothermal control',
      ctx: { ...CGL, temperatureC: 33 }, conflicts: ['OF-A-00107'],
      note: 'Side A of the temperature-shift disagreement. Cell density at shift was 31 g/L.' , conflictNote: 'A 9 % titer gain on temperature shift at 31 g L⁻¹ cell density, against OF-A-00107 which records no improvement at 58 g L⁻¹ and attributes the null result to oxygen limitation. Both stored as stated. The reconciliation candidate — that the shift only helps below a density where oxygen stops being the limit — is plausible, untested, and is not stored as a conclusion.'}),
  a({ id: 'OF-A-00107', field: 'titer', rep: [95.1, 'g L⁻¹'], norm: [95.1, 'g L⁻¹'], src: 'SRC-0003', st: 'patent-example', loc: 'Example 4', pf: 'PF-002',
      q: 'no improvement was observed over the unshifted control', ctx: { ...CGL, temperatureC: 33 }, conflicts: ['OF-A-00106'],
      note: 'Side B. Cell density at shift was 58 g/L, and the specification attributes the null result to oxygen limitation rather than to the shift itself. That attribution is the reconciliation candidate, and it is untested.' , conflictNote: 'No improvement on temperature shift at 58 g L⁻¹, attributed by the source to oxygen limitation, against OF-A-00106 which records a 9 % gain at 31 g L⁻¹. A journal and a patent working example disagreeing is the shape most literature tools cannot represent at all.'}),
  a({ id: 'OF-A-00108', field: 'temperature', rep: [306.15, 'K'], norm: [33, '°C'], der: { fn: 'temperature', usingAccessionIds: [], note: 'K → °C by subtraction of 273.15.' },
      src: 'SRC-0004', st: 'journal', loc: '§2.3 Methods', q: 'cultivations were held at 306.15 K', ctx: CGL,
      note: 'One of two Accessions in this cluster reported in Kelvin. Kept in the original unit on the Accession page precisely so the conversion is visible.' }),
  a({ id: 'OF-A-00109', field: 'temperature', rep: [303.15, 'K'], norm: [30, '°C'], der: { fn: 'temperature', usingAccessionIds: [], note: 'K → °C by subtraction of 273.15.' },
      src: 'SRC-0004', st: 'journal', loc: '§2.3 Methods', ctx: CGL }),
  a({ id: 'OF-A-00110', field: 'yield_product_substrate', rep: [0.248, 'g g⁻¹'], norm: [0.248, 'g g⁻¹'], src: 'SRC-0003', st: 'journal', loc: '§4.3 Fig. 5',
      q: 'at 39 °C growth continued but lysine yield fell to 0.248 g/g', ctx: { ...CGL, temperatureC: 39 },
      note: 'Growth continues; yield collapses. The exclusion above 37 °C is on yield, not on viability, and stating it the other way would be wrong.' }),

  // --- pH ---
  a({ id: 'OF-A-00111', field: 'ph', rep: [7.0, ''], norm: [7.0, ''], src: 'SRC-0005', st: 'journal', loc: '§2.1', ctx: { ...CGL, ph: 7.0, temperatureC: 30 } }),
  a({ id: 'OF-A-00112', field: 'titer', rep: [92.4, 'g L⁻¹'], norm: [92.4, 'g L⁻¹'], src: 'SRC-0005', st: 'journal', loc: '§3.4 Table 3',
      q: 'titer fell 12 % at pH 6.5', ctx: { ...CGL, ph: 6.5 } }),
  a({ id: 'OF-A-00113', field: 'byproduct_conc', rep: [6.8, 'g L⁻¹'], norm: [6.8, 'g L⁻¹'], src: 'SRC-0005', st: 'journal', loc: '§3.5',
      q: 'trehalose accumulated to 6.8 g/L at pH 7.6', ctx: { ...CGL, ph: 7.6 } }),
  a({ id: 'OF-A-00114', field: 'ph', rep: [7.06, ''], norm: [7.0, ''], der: { fn: 'temperature', usingAccessionIds: ['OF-A-00105'], note: 'Source reported pH measured at 25 °C. Corrected to the 30 °C process temperature; the offset is −0.06 units for a phosphate-buffered medium.', params: { kind: 'offset', delta: -0.06, because: 'phosphate-buffered medium, 25 °C reading corrected to the 30 °C process temperature' } },
      src: 'SRC-0007', st: 'journal', loc: '§2.2', q: 'pH was measured at 25 °C', ctx: { ...CGL, ph: 7.0, temperatureC: 30 },
      note: 'A pH reported without its measurement temperature is not the same quantity as a pH reported with one. This Accession exists so the interface can show that.' }),

  // --- dissolved oxygen ---
  a({ id: 'OF-A-00115', field: 'dissolved_oxygen', rep: [30, '%'], norm: [30, '%'], src: 'SRC-0002', st: 'journal', loc: '§2.1', ctx: { ...CGL, doPercent: 30 } }),
  a({ id: 'OF-A-00116', field: 'titer', rep: [116.2, 'g L⁻¹'], norm: [116.2, 'g L⁻¹'], src: 'SRC-0002', st: 'journal', loc: '§3.2 Fig. 2',
      q: 'reducing the setpoint to 20 % produced no measurable penalty', ctx: { ...CGL, doPercent: 20 },
      note: 'The Accession that makes the twelve-run design worth running. The patent claim floor sits at 20 % and this says 20 % is fine, which says nothing about 18 %.' }),
  a({ id: 'OF-A-00117', field: 'byproduct_conc', rep: [3.2, 'g L⁻¹'], norm: [3.2, 'g L⁻¹'], src: 'SRC-0002', st: 'journal', loc: '§3.3 Table 2',
      q: 'lactate reached 3.2 g/L at a 10 % setpoint', ctx: { ...CGL, doPercent: 10 } }),
  a({ id: 'OF-A-00118', field: 'byproduct_conc', rep: [15.5, 'g L⁻¹'], norm: [15.5, 'g L⁻¹'], src: 'SRC-0002', st: 'journal', loc: '§3.3 Table 2',
      q: 'combined lactate and succinate reached 15.5 g/L', ctx: { ...CGL, doPercent: 5 } }),
  a({ id: 'OF-A-00119', field: 'critical_do', rep: [8, '%'], norm: [8, '%'], src: 'SRC-0002', st: 'journal', loc: '§3.1', prov: 'gold',
      q: 'the critical dissolved oxygen tension was 8 % of saturation', ctx: { organismId: 'ORG-CGL-02', temperatureC: 30 },
      note: 'The physiological boundary the whole DO exclusion rests on, and the reason the RUN-047 excursion to 8 % is adjudicated the way it is.' }),
  a({ id: 'OF-A-00120', field: 'titer', rep: [112, 'g L⁻¹'], norm: [112, 'g L⁻¹'], range: [96, 112], src: 'SRC-0001', st: 'patent-example', loc: 'Example 3', pf: 'PF-001',
      q: 'titers of 96 to 112 g/L were obtained across the recited range', ctx: { ...CGL, doPercent: 30 },
      note: 'A range, not a point. The extractor must not invent a midpoint, and the rail must render a band.' }),
  a({ id: 'OF-A-00121', field: 'our', rep: [118, 'mmol L⁻¹ h⁻¹'], norm: [118, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0002', st: 'journal', loc: '§3.4 Fig. 4', prov: 'gold',
      q: 'peak oxygen uptake reached 118 mmol L⁻¹ h⁻¹ at 62 g/L dry cell weight', ctx: { ...CGL, doPercent: 30 },
      note: 'The number that decides Archetype 3. A 5 m³ Rushton vessel at 1.5 kW/m³ cannot transfer this, and no amount of process tuning changes that.' }),
  a({ id: 'OF-A-00122', field: 'rq', rep: [1.34, ''], norm: [1.34, ''], src: 'SRC-0002', st: 'journal', loc: '§3.4',
      q: 'RQ rose to 1.34 during the limitation window', ctx: { ...CGL, doPercent: 5 },
      note: 'The diagnostic signature of the fermentative shift. Used directly by the RUN-047 adjudication.' }),

  // --- growth rate and feed ---
  a({ id: 'OF-A-00123', field: 'mu_setpoint', rep: [0.15, 'h⁻¹'], norm: [0.15, 'h⁻¹'], src: 'SRC-0006', st: 'journal', loc: '§2.4', ctx: CGL }),
  a({ id: 'OF-A-00124', field: 'specific_productivity', rep: [0.119, 'g gDCW⁻¹ h⁻¹'], norm: [0.119, 'g gDCW⁻¹ h⁻¹'], src: 'SRC-0006', st: 'journal', loc: '§3.2 Table 1',
      q: 'qp rose 21 % at the lower feed setpoint', ctx: { ...CGL, mode: 'fed-batch' },
      note: 'μ 0.10 h⁻¹. The Accession that rescues the lysine candidate in Archetype 3 — lower μ means lower peak OUR, which is the only way this process fits a 5 m³ vessel.' }),
  a({ id: 'OF-A-00125', field: 'yield_product_substrate', rep: [0.353, 'g g⁻¹'], norm: [0.353, 'g g⁻¹'], src: 'SRC-0006', st: 'journal', loc: '§3.3',
      q: 'yield fell 16 % at μ = 0.22 h⁻¹ as carbon partitioned to biomass', ctx: { ...CGL, mode: 'fed-batch' } }),
  a({ id: 'OF-A-00126', field: 'volumetric_productivity', rep: [1.34, 'g L⁻¹ h⁻¹'], norm: [1.34, 'g L⁻¹ h⁻¹'], src: 'SRC-0006', st: 'journal', loc: '§3.3 Fig. 2',
      q: 'the 96 h cycle gave 1.34 g L⁻¹ h⁻¹', ctx: { ...CGL, mode: 'fed-batch' },
      note: 'μ 0.05 h⁻¹. Not an exclusion on biology — an exclusion on economics, and the factor band must say which.' }),

  // --- the unit-normalisation showpieces ---
  a({ id: 'OF-A-00127', field: 'volumetric_productivity', rep: [0.10, 'g gDCW⁻¹ h⁻¹'], norm: [2.4, 'g L⁻¹ h⁻¹'],
      der: { fn: 'specific-to-volumetric', usingAccessionIds: ['OF-A-00128'], note: 'q · X. Biomass concentration from OF-A-00128, 24 g L⁻¹, reported in the same table.' },
      src: 'SRC-0006', st: 'journal', loc: '§3.2 Table 1', q: 'specific productivity of 0.10 g gDCW⁻¹ h⁻¹', ctx: CGL,
      note: 'The display case for the whole platform. Two papers reporting the same performance in different units are not comparable until this conversion is done, and the auxiliary quantity that closes it is itself an Accession.' }),
  a({ id: 'OF-A-00128', field: 'biomass_density', rep: [24, 'g L⁻¹'], norm: [24, 'g L⁻¹'], src: 'SRC-0006', st: 'journal', loc: '§3.2 Table 1', ctx: CGL }),
  a({ id: 'OF-A-00129', field: 'volumetric_productivity', rep: [1.20, 'mmol gDCW⁻¹ h⁻¹'], norm: [3.859, 'g L⁻¹ h⁻¹'],
      der: { fn: 'specific-to-volumetric', usingAccessionIds: ['OF-A-00130'], note: 'q · M · X / 1000, with M = 146.19 g mol⁻¹ for L-lysine and X = 22 g L⁻¹ from OF-A-00130.' },
      src: 'SRC-0001', st: 'journal', loc: '§4.4 Table 4', q: '1.20 mmol gDCW⁻¹ h⁻¹', ctx: CGL,
      note: 'Molar and mass bases in the same field. Without normalisation this sits three orders of magnitude away from OF-A-00127 and looks like a contradiction.' }),
  a({ id: 'OF-A-00130', field: 'biomass_density', rep: [22, 'g L⁻¹'], norm: [22, 'g L⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§4.4 Table 4', ctx: CGL }),

  // --- anaplerosis and biotin ---
  a({ id: 'OF-A-00131', field: 'co2_overlay', rep: [40, 'mM'], norm: [40, 'mM'], src: 'SRC-0004', st: 'journal', loc: '§3.1',
      q: 'bicarbonate supplementation at 40 mM', ctx: CGL }),
  a({ id: 'OF-A-00132', field: 'yield_product_substrate', rep: [0.466, 'g g⁻¹'], norm: [0.466, 'g g⁻¹'], src: 'SRC-0004', st: 'journal', loc: '§3.2 Table 1',
      q: 'yield rose 11 % with bicarbonate supplementation in the pyruvate carboxylase overexpressing background', ctx: CGL,
      note: 'Conditional on the strain background. Applying it to a strain without pyc overexpression would be an error, and the context field is what prevents that.' }),
  a({ id: 'OF-A-00133', field: 'flux_split', rep: [0.38, 'fraction'], norm: [0.38, 'fraction'], src: 'SRC-0004', st: 'journal', loc: '§3.3 Fig. 3',
      q: '38 % of oxaloacetate derived from direct carboxylation', ctx: CGL }),
  a({ id: 'OF-A-00134', field: 'biotin_conc', rep: [30, 'µg L⁻¹'], norm: [0.03, 'mg L⁻¹'],
      der: { fn: 'linear', usingAccessionIds: [], note: 'µg L⁻¹ → mg L⁻¹, factor 1e-3.' },
      src: 'SRC-0007', st: 'journal', loc: '§2.1', q: 'biotin-limited medium containing 30 µg/L', ctx: CGL,
      note: 'Biotin limitation drives glutamate excretion. It is a product-spectrum switch, not a growth knob, which is why it is a hard exclusion rather than a soft one.' }),
  a({ id: 'OF-A-00135', field: 'biotin_conc', rep: [200, 'µg L⁻¹'], norm: [0.2, 'mg L⁻¹'],
      der: { fn: 'linear', usingAccessionIds: [], note: 'µg L⁻¹ → mg L⁻¹, factor 1e-3.' },
      src: 'SRC-0007', st: 'journal', loc: '§2.1', ctx: CGL }),

  // --- yield ---
  a({ id: 'OF-A-00136', field: 'yield_product_substrate', rep: [0.42, 'g g⁻¹'], norm: [0.42, 'g g⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§4.2', prov: 'gold', ctx: CGL }),
  a({ id: 'OF-A-00137', field: 'theoretical_yield', rep: [0.75, 'mol mol⁻¹'], norm: [0.75, 'mol mol⁻¹'], src: 'SRC-0001', st: 'journal', loc: '§2 Eq. 6',
      q: 'the cofactor-balanced maximum on glucose is 0.75 mol/mol', ctx: { productId: 'L-lysine' } }),
  a({ id: 'OF-A-00138', field: 'yield_product_substrate', rep: [0.55, 'mol mol⁻¹'], norm: [0.4463, 'g g⁻¹'],
      der: { fn: 'molar-to-mass', usingAccessionIds: [], note: 'mol mol⁻¹ → g g⁻¹ by 146.19 / 180.16 (L-lysine over glucose).', params: { kind: 'molar-ratio', numerator: 'L-lysine', denominator: 'glucose' } },
      src: 'SRC-0001', st: 'journal', loc: '§4.2 Table 3', q: '0.55 mol lysine per mol glucose', ctx: CGL }),

  // --- patent working examples: the negative data ---
  a({ id: 'OF-A-00139', field: 'byproduct_conc', rep: [6.8, 'g L⁻¹'], norm: [6.8, 'g L⁻¹'], src: 'SRC-0001', st: 'patent-example', loc: 'Example 5 (comparative)', pf: 'PF-001',
      q: 'lactate accumulated to 6.8 g/L notwithstanding increased agitation', ctx: { ...CGL, doPercent: 15 }, conf: 0.88,
      note: 'A comparative example. The applicant is motivated to report this failure accurately, because non-obviousness depends on it. No journal would publish it.' }),
  a({ id: 'OF-A-00140', field: 'titer', rep: [71, 'g L⁻¹'], norm: [71, 'g L⁻¹'], src: 'SRC-0003', st: 'patent-example', loc: 'Example 7 (comparative)', pf: 'PF-002',
      q: 'titer of 71 g/L against 96 g/L for the unshifted control', ctx: { ...CGL, temperatureC: 37 }, conf: 0.9,
      note: 'The 37 °C exclusion. It rests on this single comparative example and nothing else in the corpus, which is why the factor band carries a single-source marker on that boundary.' }),
  a({ id: 'OF-A-00141', field: 'titer', rep: [104, 'g L⁻¹'], norm: [104, 'g L⁻¹'], src: 'SRC-0005', st: 'patent-example', loc: 'Example 2', pf: 'PF-003', ctx: CGL, conf: 0.87 }),
  a({ id: 'OF-A-00142', field: 'dissolved_oxygen', rep: [30, '%'], norm: [30, '%'], range: [20, 45], src: 'SRC-0001', st: 'patent-claim', loc: 'Claim 1', pf: 'PF-001',
      q: 'a dissolved oxygen tension of from 20 % to 45 % of saturation', ctx: CGL,
      note: 'Claim scope expressed as a field range. This is what makes an FTO flag renderable on a factor band rather than only in a legal memo.' }),
  a({ id: 'OF-A-00143', field: 'ph', rep: [6.3, ''], norm: [6.3, ''], src: 'SRC-0003', st: 'patent-example', loc: 'Example 9 (comparative)', pf: 'PF-002',
      q: 'growth arrested at 40 h', ctx: { ...CGL, ph: 6.3 }, conf: 0.85 }),

  // --- feedstock ---
  a({ id: 'OF-A-00144', field: 'yield_product_substrate', rep: [82, '% (w/w)'], norm: [0.82, 'g g⁻¹'],
      der: { fn: 'linear', usingAccessionIds: [], note: '% (w/w) → g g⁻¹, factor 0.01.' },
      src: 'SRC-0009', st: 'journal', loc: '§3.1 Table 2', q: '82 % of dry mass recovered as fermentable sugar', ctx: { feedstock: 'cassava starch' } }),
  a({ id: 'OF-A-00145', field: 'inhibitor_tolerance', rep: [0.9, 'g L⁻¹'], norm: [0.9, 'g L⁻¹'], src: 'SRC-0009', st: 'journal', loc: '§3.4',
      q: 'growth rate halved at 0.9 g/L of the phenolic fraction', ctx: { organismId: 'ORG-CGL-02', feedstock: 'cassava hydrolysate' } }),

  // --- bench deposits: the Kigali campaign, and the seam into Archetype 6 ---
  a({ id: 'OF-A-00146', field: 'titer', rep: [42.0, 'g L⁻¹'], norm: [42.0, 'g L⁻¹'], src: 'SRC-0032', st: 'bench-deposit', loc: 'RUN-045', prov: 'deposited', run: 'RUN-045',
      ctx: { ...CGL, doPercent: 30, temperatureC: 30, ph: 7.0 }, note: 'Deposited by CH-KGL-01 under Common Seal CS-2026-0091. The operating point the Archetype 1 query starts from.' }),
  a({ id: 'OF-A-00147', field: 'titer', rep: [39.4, 'g L⁻¹'], norm: [39.4, 'g L⁻¹'], src: 'SRC-0032', st: 'bench-deposit', loc: 'RUN-047', prov: 'excursion',
      hold: 'excursion-flagged', run: 'RUN-047', ctx: { ...CGL, doPercent: 30, temperatureC: 30, ph: 7.0 },
      note: 'THE SEAM. Adjudicated in Archetype 6 and excluded from the Archetype 1 gap map by that adjudication. Held, visible, never silently dropped.' }),
  a({ id: 'OF-A-00148', field: 'byproduct_conc', rep: [0.47, 'g L⁻¹'], norm: [0.47, 'g L⁻¹'], src: 'SRC-0032', st: 'bench-deposit', loc: 'RUN-047 harvest', prov: 'excursion',
      hold: 'excursion-flagged', run: 'RUN-047', ctx: { ...CGL, doPercent: 8 },
      note: 'Lactate at harvest. Small, and it has to be — eleven minutes cannot produce more. A larger number here would be the tell that the excursion story was written backwards from a dramatic value. It is corroboration for the verdict, not the basis of it.' }),
  a({ id: 'OF-A-00149', field: 'carbon_balance_closure', rep: [96.2, '%'], norm: [96.2, '%'], src: 'SRC-0032', st: 'bench-deposit', loc: 'RUN-042 to RUN-046', prov: 'deposited', sd: 0.4, n: 5,
      ctx: CGL, note: 'The comparison basis. Five runs, standard deviation 0.4 points — set reported.sd and reported.n on this Accession so the rail can render the spread. A gap only means something against a spread.' }),
  a({ id: 'OF-A-00150', field: 'carbon_balance_closure', rep: [94.9, '%'], norm: [94.9, '%'], src: 'SRC-0032', st: 'bench-deposit', loc: 'RUN-047', prov: 'excursion',
      hold: 'excursion-flagged', run: 'RUN-047', ctx: CGL,
      note: 'A 1.3-point gap against a basis whose run-to-run spread is 0.4 points — roughly three standard deviations. Small enough that nobody eyeballing the chart would flag it, which is the entire argument for adjudicating against a basis rather than against an impression.' }),

  // --- what this project has already published ---
  a({ id: 'OF-A-00151', field: 'dissolved_oxygen', rep: [20, '%'], norm: [20, '%'], range: [18, 22], src: 'SRC-0033', st: 'defensive-publication', loc: 'Disclosure 2026-014',
      prov: 'verified', ctx: { ...CGL, doPercent: 20 },
      note: 'openFerment disclosed this region on 14 July 2026: reduced DO setpoint with 40 mM bicarbonate, in a Corynebacterium with overexpressed pyruvate carboxylase. Published to make it unclaimable, not to claim it.' }),
  a({ id: 'OF-A-00152', field: 'our', rep: [2.4, 'mmol gDCW⁻¹ h⁻¹'], norm: [48, 'mmol L⁻¹ h⁻¹'],
      der: { fn: 'specific-to-volumetric', usingAccessionIds: ['OF-A-00153'], note: 'qO₂ · X, with X = 20 g L⁻¹ from the de-rated design point in OF-A-00153.' },
      src: 'SRC-0008', st: 'thesis', loc: '§5.2', ctx: { ...CGL, mode: 'fed-batch' },
      note: 'Peak OUR for the de-rated operating point. This is the number that has to fit under the plant OTR ceiling in Archetype 3, and it does, by 2 mmol.' }),
  a({ id: 'OF-A-00153', field: 'biomass_density', rep: [20, 'g L⁻¹'], norm: [20, 'g L⁻¹'], src: 'SRC-0008', st: 'thesis', loc: '§5.2', ctx: CGL }),
];

// ══════════════════════════════════════════════════════════════════════
// CLUSTER 2 — 3-hydroxypropionic acid, three routes
// ══════════════════════════════════════════════════════════════════════

const HP = { productId: '3-HP' };

export const ACCESSIONS_3HP: Accession[] = [
  // malonyl-CoA
  a({ id: 'OF-A-00201', field: 'theoretical_yield', rep: [1.0, 'mol mol⁻¹'], norm: [0.5, 'g g⁻¹'],
      der: { fn: 'molar-to-mass', usingAccessionIds: [], note: '3-HP over glucose, 90.08 / 180.16.', params: { kind: 'molar-ratio', numerator: '3-HP', denominator: 'glucose' } },
      src: 'SRC-0015', st: 'journal', loc: '§2 Table 1', ctx: HP }),
  a({ id: 'OF-A-00202', field: 'cofactor_demand', rep: [2, 'mol mol⁻¹'], norm: [2, 'mol mol⁻¹'], src: 'SRC-0015', st: 'journal', loc: '§2 Table 1',
      q: 'two NADPH per 3-HP via the malonyl-CoA route', ctx: HP }),
  a({ id: 'OF-A-00203', field: 'titer', rep: [40.6, 'g L⁻¹'], norm: [40.6, 'g L⁻¹'], src: 'SRC-0010', st: 'journal', loc: '§3.4 Fig. 4', prov: 'gold',
      ctx: { ...HP, organismId: 'ORG-ECO-01', mode: 'fed-batch' } }),
  a({ id: 'OF-A-00204', field: 'volumetric_productivity', rep: [0.85, 'g L⁻¹ h⁻¹'], norm: [0.85, 'g L⁻¹ h⁻¹'], src: 'SRC-0010', st: 'journal', loc: '§3.4',
      ctx: { ...HP, organismId: 'ORG-ECO-01' } }),
  a({ id: 'OF-A-00205', field: 'flux_split', rep: [0.31, 'fraction'], norm: [0.31, 'fraction'], src: 'SRC-0010', st: 'journal', loc: '§3.2',
      q: '31 % of acetyl-CoA entering the carboxylase', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),
  a({ id: 'OF-A-00220', field: 'our', rep: [82, 'mmol L⁻¹ h⁻¹'], norm: [82, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0010', st: 'journal', loc: '§3.5', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),
  a({ id: 'OF-A-00224', field: 'titer', rep: [38, 'g L⁻¹'], norm: [38, 'g L⁻¹'], src: 'SRC-0010', st: 'patent-example', loc: 'Example 11', pf: 'PF-004', conf: 0.86,
      ctx: { ...HP, organismId: 'ORG-ECO-01' } }),

  // β-alanine
  a({ id: 'OF-A-00206', field: 'theoretical_yield', rep: [1.24, 'mol mol⁻¹'], norm: [0.62, 'g g⁻¹'],
      der: { fn: 'molar-to-mass', usingAccessionIds: [], note: '3-HP over glucose, 90.08 / 180.16, times 1.24.', params: { kind: 'molar-ratio', numerator: '3-HP', denominator: 'glucose' } },
      src: 'SRC-0015', st: 'journal', loc: '§2 Table 1', prov: 'gold',
      q: 'carboxylation at phosphoenolpyruvate raises the ceiling above unity', ctx: HP,
      note: 'The highest theoretical yield of the three routes, because the route fixes CO₂ on the way in. This is the finding that survives the patent overlay reversing the ranking.' }),
  a({ id: 'OF-A-00207', field: 'cofactor_demand', rep: [1, 'mol mol⁻¹'], norm: [1, 'mol mol⁻¹'], src: 'SRC-0015', st: 'journal', loc: '§2 Table 1', ctx: HP }),
  a({ id: 'OF-A-00208', field: 'titer', rep: [31.2, 'g L⁻¹'], norm: [31.2, 'g L⁻¹'], src: 'SRC-0011', st: 'journal', loc: '§3.3 Table 2',
      ctx: { ...HP, organismId: 'ORG-ECO-01', mode: 'fed-batch' } }),
  a({ id: 'OF-A-00209', field: 'flux_split', rep: [0.44, 'fraction'], norm: [0.44, 'fraction'], src: 'SRC-0011', st: 'journal', loc: '§3.4',
      q: 'pyruvate recycling accounted for 44 % of the amino acceptor demand', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),
  a({ id: 'OF-A-00210', field: 'enzyme_activity', rep: [3.1, ''], norm: [3.1, ''], src: 'SRC-0011', st: 'patent-example', loc: 'Example 3', pf: 'PF-008', conf: 0.83,
      q: 'the variant retained activity over a 3.1-fold longer production window', ctx: HP,
      note: 'Assay-dependent, so the field is non-aggregatable and the rail must not render a median for it.' }),
  a({ id: 'OF-A-00222', field: 'our', rep: [58, 'mmol L⁻¹ h⁻¹'], norm: [58, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0011', st: 'journal', loc: '§3.5', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),

  // glycerol
  a({ id: 'OF-A-00211', field: 'theoretical_yield', rep: [1.0, 'mol mol⁻¹'], norm: [0.9782, 'g g⁻¹'],
      der: { fn: 'molar-to-mass', usingAccessionIds: [], note: '3-HP over glycerol, 90.08 / 92.09. One carbon in, one carbon out.', params: { kind: 'molar-ratio', numerator: '3-HP', denominator: 'glycerol' } },
      src: 'SRC-0015', st: 'journal', loc: '§2 Table 1', ctx: HP,
      note: 'On a mass basis this is the best yield in the pool by a wide margin, and it is entirely an artefact of the substrate being one oxidation state away from the product.' }),
  a({ id: 'OF-A-00212', field: 'opex', rep: [340, 'USD t⁻¹'], norm: [340, 'USD t⁻¹'], src: 'SRC-0012', st: 'patent-example', loc: 'Example 12 (comparative)', pf: 'PF-006', conf: 0.81,
      q: 'without supplementation conversion did not proceed beyond the dehydratase step', ctx: HP,
      note: 'Coenzyme B12 supplementation cost per tonne of product. The comparative example establishes that it is not optional, which is what turns a cost line into a route-level constraint.' }),
  a({ id: 'OF-A-00213', field: 'titer', rep: [0.21, 'g L⁻¹'], norm: [0.21, 'g L⁻¹'], src: 'SRC-0012', st: 'journal', loc: '§4.1',
      ctx: { productId: 'coenzyme B12', organismId: 'ORG-PDN-01' },
      note: 'Native B12 production. The reason a slower, less tractable host is on the comparison at all.' }),
  a({ id: 'OF-A-00214', field: 'inhibitor_tolerance', rep: [15, 'mM'], norm: [1.111, 'g L⁻¹'],
      der: { fn: 'molar-to-mass', usingAccessionIds: [], note: 'mM → g L⁻¹ using 74.08 g mol⁻¹ for 3-hydroxypropionaldehyde.', params: { kind: 'molar-mass', species: '3-hydroxypropionaldehyde' } },
      src: 'SRC-0013', st: 'journal', loc: '§3.2 Fig. 3', q: 'half-maximal inhibition at 15 mM', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),
  a({ id: 'OF-A-00218', field: 'titer', rep: [71.9, 'g L⁻¹'], norm: [71.9, 'g L⁻¹'], src: 'SRC-0012', st: 'patent-example', loc: 'Example 8', pf: 'PF-006', prov: 'verified', conf: 0.89,
      ctx: { ...HP, organismId: 'ORG-ECO-01', mode: 'fed-batch', feedstock: 'crude glycerol' },
      note: 'The highest 3-HP titer in the pool and it comes from a patent example rather than a journal. Excluding patent literature from the corpus would lose the best data point in the field.' }),
  a({ id: 'OF-A-00219', field: 'feedstock_cost', rep: [260, 'USD t⁻¹'], norm: [260, 'USD t⁻¹'], src: 'SRC-0012', st: 'journal', loc: '§5.1', ctx: { feedstock: 'crude glycerol' } }),
  a({ id: 'OF-A-00221', field: 'our', rep: [44, 'mmol L⁻¹ h⁻¹'], norm: [44, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0012', st: 'journal', loc: '§4.3', ctx: { ...HP, organismId: 'ORG-ECO-01' } }),

  // pH and downstream
  a({ id: 'OF-A-00215', field: 'opex', rep: [210, 'USD t⁻¹'], norm: [210, 'USD t⁻¹'], src: 'SRC-0014', st: 'journal', loc: '§3.2 Table 1',
      q: 'neutralisation and subsequent acid springing', ctx: { ...HP, ph: 7.0 },
      note: 'What producing above the pKa costs. Every neutral-pH route in this comparison carries it and none of them report it, because it is a downstream number in an upstream paper.' }),
  a({ id: 'OF-A-00216', field: 'titer', rep: [13.7, 'g L⁻¹'], norm: [13.7, 'g L⁻¹'], src: 'SRC-0014', st: 'patent-example', loc: 'Example 2', pf: 'PF-007', conf: 0.88,
      ctx: { ...HP, organismId: 'ORG-SCE-01', ph: 3.5 },
      note: 'A third of the bacterial titer, and it avoids OF-A-00215 entirely. Whether that trade closes is a Proforma question, not a strain question.' }),
  a({ id: 'OF-A-00217', field: 'cofactor_demand', rep: [2, 'mol mol⁻¹'], norm: [2, 'mol mol⁻¹'], src: 'SRC-0014', st: 'journal', loc: '§2.3',
      q: 'two ATP per cytosolic acetyl-CoA', ctx: { organismId: 'ORG-SCE-01' } }),
  a({ id: 'OF-A-00223', field: 'separation_yield', rep: [0.78, 'fraction'], norm: [0.78, 'fraction'], src: 'SRC-0014', st: 'journal', loc: '§4.1', ctx: HP }),
];

// ══════════════════════════════════════════════════════════════════════
// CLUSTER 3 — plant envelope, candidates, trade
// ══════════════════════════════════════════════════════════════════════

const RW = { jurisdiction: 'RW' };

export const ACCESSIONS_CAPACITY: Accession[] = [
  a({ id: 'OF-A-00301', field: 'feedstock_cost', rep: [380, 'USD t⁻¹'], norm: [380, 'USD t⁻¹'], src: 'SRC-0009', st: 'journal', loc: '§5.2', ctx: { ...RW, feedstock: 'cassava starch' } }),
  a({ id: 'OF-A-00302', field: 'feedstock_cost', rep: [15, 'USD t⁻¹'], norm: [15, 'USD t⁻¹'], src: 'SRC-0009', st: 'journal', loc: '§5.2', ctx: { ...RW, feedstock: 'coffee pulp' },
      note: 'Collection and transport only. A residue with a disposal cost attached is not the same economic object as a purchased feedstock, and the cost surface has to treat it differently.' }),
  a({ id: 'OF-A-00303', field: 'feedstock_cost', rep: [25, 'USD t⁻¹'], norm: [25, 'USD t⁻¹'], src: 'SRC-0009', st: 'journal', loc: '§5.2', ctx: { ...RW, feedstock: 'brewery spent grain' } }),
  a({ id: 'OF-A-00304', field: 'feedstock_cost', rep: [8, 'USD t⁻¹'], norm: [8, 'USD t⁻¹'], src: 'SRC-0009', st: 'journal', loc: '§5.2', ctx: { ...RW, feedstock: 'liquid whey' } }),

  a({ id: 'OF-A-00305', field: 'temperature', rep: [52, '°C'], norm: [52, '°C'], range: [50, 55], src: 'SRC-0018', st: 'journal', loc: '§2.1', prov: 'gold', ctx: { organismId: 'ORG-BCG-01' },
      note: 'The single fact that reorders the capacity screen. At 52 °C against 28 °C cooling-tower water the driving force is 24 K; at 30 °C it is 2 K. Thermophily is a heat-transfer decision before it is a microbiology decision.' }),
  a({ id: 'OF-A-00306', field: 'our', rep: [12, 'mmol L⁻¹ h⁻¹'], norm: [12, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0018', st: 'journal', loc: '§3.1', ctx: { organismId: 'ORG-BCG-01' } }),

  // The two inputs to the van 't Riet correlation, as Accessions.
  //
  // WHY THEY EXIST. OF-A-00307 is `provenance: 'computed'` and was citing
  // nothing: its note named P/V = 1500 and vs = 0.049 in prose, and prose is
  // not a citation. Rule 1 says no number renders unless it traces to an
  // Accession or to a computation over Accessions, and a computation over two
  // numbers that are not Accessions does not satisfy it. It also left the
  // Accession page's derivation recursion one hop deep, so the seam-matrix row
  // that calls for a two-deep chain did not hold.
  a({ id: 'OF-A-00327', field: 'agitation_power', rep: [1500, 'W m⁻³'], norm: [1500, 'W m⁻³'], src: 'SRC-0035', st: 'vendor-datasheet', loc: 'Vessel package, sheet 2', prov: 'curated', conf: 0.88,
      ctx: { scale: '5 m³' },
      note: 'Installed specific power for the three-stage Rushton configuration. A vendor figure, so it is what the package is rated for rather than what a given batch draws.' }),
  a({ id: 'OF-A-00328', field: 'superficial_gas_velocity', rep: [0.049, 'm s⁻¹'], norm: [0.049, 'm s⁻¹'], src: 'SRC-0035', st: 'computed', loc: 'derived from sheet 1 geometry', prov: 'computed', conf: 0.95,
      der: { fn: 'identity', usingAccessionIds: [], note: '1 VVM through a 5 m³ working volume at H/D = 2 gives D = 1.47 m and a cross-section of 1.70 m²; 5 m³ min⁻¹ over that area is 0.049 m s⁻¹. Recomputed at load by superficialGasVelocity().' },
      ctx: { scale: '5 m³' },
      note: 'The input a reader is most likely to assume rather than check, which is why it is an Accession rather than a number in a note.' }),

  a({ id: 'OF-A-00307', field: 'kla', rep: [385, 'h⁻¹'], norm: [385, 'h⁻¹'], src: 'SRC-0016', st: 'journal', loc: '§4 Eq. 7', prov: 'computed',
      der: { fn: 'linear', usingAccessionIds: ['OF-A-00327', 'OF-A-00328'], note: 'van \u2019t Riet coalescing correlation, kLa = 0.026 (P/V)^0.4 vs^0.5, over the installed specific power in OF-A-00327 and the superficial gas velocity in OF-A-00328. Recomputed at load by lib/transport.ts.' },
      ctx: { scale: '5 m³' },
      note: 'Clean water. A kLa quoted without a broth factor is the most common way a plant gets specified wrong.' }),
  a({ id: 'OF-A-00308', field: 'kla', rep: [0.46, 'fraction'], norm: [177.1, 'h⁻¹'],
      der: { fn: 'linear', usingAccessionIds: ['OF-A-00307'], note: 'Broth factor 0.46 applied to the clean-water value in OF-A-00307. High-solids amino acid broth with antifoam.' },
      src: 'SRC-0016', st: 'journal', loc: '§5.2 Table 4', ctx: { scale: '5 m³' },
      note: 'Effective kLa. Every OTR number in Archetype 3 derives from this, and the derivation chain is two Accessions deep by design.' }),
  a({ id: 'OF-A-00309', field: 'broth_viscosity', rep: [3200, ''], norm: [3200, ''], src: 'SRC-0021', st: 'journal', loc: '§3.1 Fig. 2',
      q: 'apparent viscosity of 3,200 mPa·s at a shear rate of 10 s⁻¹', ctx: { productId: 'xanthan gum' }, conf: 0.9,
      note: 'A viscosity without a shear rate is unit-ambiguous for a non-Newtonian broth. The shear rate is in the quote and the field definition makes it mandatory.' }),

  a({ id: 'OF-A-00310', field: 'import_volume', rep: [340, 't a⁻¹'], norm: [340, 't a⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2922.41', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW,
      note: 'Synthetic trade aggregate. Held out of every statistic and used only for market sizing, which is the one thing it is fit for.' }),
  a({ id: 'OF-A-00311', field: 'import_cif', rep: [2100, 'USD t⁻¹'], norm: [2100, 'USD t⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2922.41', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00312', field: 'import_volume', rep: [180, 't a⁻¹'], norm: [180, 't a⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2918.11', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00313', field: 'import_cif', rep: [1450, 'USD t⁻¹'], norm: [1450, 'USD t⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2918.11', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00314', field: 'import_volume', rep: [620, 't a⁻¹'], norm: [620, 't a⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2918.14', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00315', field: 'import_cif', rep: [9800, 'USD t⁻¹'], norm: [9800, 'USD t⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 3507.90', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00316', field: 'import_volume', rep: [210, 't a⁻¹'], norm: [210, 't a⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2102.20', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00317', field: 'import_volume', rep: [26, 't a⁻¹'], norm: [26, 't a⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 3101.00', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00318', field: 'import_cif', rep: [3400, 'USD t⁻¹'], norm: [3400, 'USD t⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2905.44', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),
  a({ id: 'OF-A-00319', field: 'import_cif', rep: [1180, 'USD t⁻¹'], norm: [1180, 'USD t⁻¹'], src: 'SRC-0020', st: 'trade-statistic', loc: 'HS 2918.14', prov: 'industry-estimate', hold: 'industry-estimate', ctx: RW }),

  a({ id: 'OF-A-00320', field: 'our', rep: [165, 'mmol L⁻¹ h⁻¹'], norm: [165, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0017', st: 'journal', loc: '§2 Table 1', ctx: { productId: 'single-cell protein' } }),
  a({ id: 'OF-A-00321', field: 'our', rep: [145, 'mmol L⁻¹ h⁻¹'], norm: [145, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0022', st: 'journal', loc: '§3.2', ctx: { productId: 'citric acid' },
      note: 'Citric acid is famously intolerant of transient oxygen limitation — a short interruption does not reduce the rate, it changes the product. In a plant with an intermittent grid that is a different kind of risk from a yield penalty.' }),
  a({ id: 'OF-A-00322', field: 'our', rep: [88, 'mmol L⁻¹ h⁻¹'], norm: [88, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0017', st: 'journal', loc: '§2 Table 1', ctx: { productId: 'baker\u2019s yeast' } }),
  a({ id: 'OF-A-00323', field: 'our', rep: [18, 'mmol L⁻¹ h⁻¹'], norm: [18, 'mmol L⁻¹ h⁻¹'], src: 'SRC-0019', st: 'journal', loc: '§2.2', ctx: { productId: 'rhizobial inoculant' } }),
  a({ id: 'OF-A-00324', field: 'cooling_duty', rep: [80, 'kW'], norm: [80, 'kW'], src: 'SRC-0034', st: 'vendor-datasheet', loc: 'Chiller nameplate', prov: 'user', conf: 1.0, ctx: { ...RW, scale: '5 m³ × 2' },
      note: 'Installed chiller capacity at the Kigali site. User-entered from the plant survey, which is why it carries a user Tick and not a literature one.' }),
  a({ id: 'OF-A-00325', field: 'temperature', rep: [26, '°C'], norm: [26, '°C'], src: 'SRC-0017', st: 'journal', loc: '§1', ctx: RW,
      note: 'Mean ambient. Against a 30 °C mesophilic broth this leaves 4 K of driving force to cooling-tower water, which is why the site has a chiller and why the chiller is the constraint.' }),
  a({ id: 'OF-A-00326', field: 'separation_yield', rep: [0.91, 'fraction'], norm: [0.91, 'fraction'], src: 'SRC-0034', st: 'vendor-datasheet', loc: 'Performance curve 3', prov: 'unverified', conf: 0.7, ctx: { scale: '4 m³ h⁻¹' },
      note: 'Vendor curve. Unverified against any broth this plant will actually run, and flagged as such wherever it feeds a number.' }),
];

// ══════════════════════════════════════════════════════════════════════
// CLUSTER 4 — lignocellulose, greenfield
// ══════════════════════════════════════════════════════════════════════

const BAG = { feedstock: 'sugarcane bagasse' };

export const ACCESSIONS_LIGNO: Accession[] = [
  a({ id: 'OF-A-00401', field: 'purity', rep: [42, '% (w/w)'], norm: [42, '% (w/w)'], src: 'SRC-0023', st: 'journal', loc: '§2.1 Table 1', ctx: BAG, note: 'Cellulose fraction, dry basis.' }),
  a({ id: 'OF-A-00402', field: 'purity', rep: [27, '% (w/w)'], norm: [27, '% (w/w)'], src: 'SRC-0023', st: 'journal', loc: '§2.1 Table 1', ctx: BAG, note: 'Hemicellulose. This is the pentose stream and it is 27 % of the feedstock, which is too much to burn.' }),
  a({ id: 'OF-A-00403', field: 'purity', rep: [21, '% (w/w)'], norm: [21, '% (w/w)'], src: 'SRC-0023', st: 'journal', loc: '§2.1 Table 1', ctx: BAG }),
  a({ id: 'OF-A-00404', field: 'inhibitor_tolerance', rep: [1.9, 'g L⁻¹'], norm: [1.9, 'g L⁻¹'], src: 'SRC-0024', st: 'journal', loc: '§3.1 Table 2', prov: 'gold',
      q: 'half-maximal growth inhibition at 1.9 g/L furfural', ctx: { organismId: 'ORG-BCG-01' } }),
  a({ id: 'OF-A-00405', field: 'growth_rate_mu', rep: [0.82, 'fraction'], norm: [0.82, 'fraction'], src: 'SRC-0024', st: 'journal', loc: '§3.3',
      q: 'retained 82 % of the control growth rate on undetoxified hydrolysate', ctx: { organismId: 'ORG-RTO-01' },
      note: 'Reported as a fraction of control rather than as an absolute μ. Kept in that form because converting it would require a control μ the source does not state.' }),
  a({ id: 'OF-A-00406', field: 'yield_product_substrate', rep: [0.88, 'g g⁻¹'], norm: [0.88, 'g g⁻¹'], src: 'SRC-0018', st: 'patent-example', loc: 'Example 7', pf: 'PF-012', conf: 0.87,
      q: 'lactate yield of 0.88 g/g on mixed C5 and C6 sugars', ctx: { organismId: 'ORG-BCG-01', temperatureC: 52 } }),
  a({ id: 'OF-A-00407', field: 'yield_product_substrate', rep: [0.61, 'g g⁻¹'], norm: [0.61, 'g g⁻¹'], src: 'SRC-0023', st: 'journal', loc: '§3.2 Table 3', ctx: { ...BAG, mode: 'batch' }, note: 'Dilute acid. Sugar recovered per gram of dry bagasse.' }),
  a({ id: 'OF-A-00408', field: 'yield_product_substrate', rep: [0.58, 'g g⁻¹'], norm: [0.58, 'g g⁻¹'], src: 'SRC-0023', st: 'journal', loc: '§3.2 Table 3', ctx: BAG, note: 'Steam explosion.' }),
  a({ id: 'OF-A-00409', field: 'yield_product_substrate', rep: [0.72, 'g g⁻¹'], norm: [0.72, 'g g⁻¹'], src: 'SRC-0025', st: 'patent-example', loc: 'Example 2', pf: 'PF-014', conf: 0.88, ctx: BAG, note: 'Organosolv. The best sugar yield, and it is claimed.' }),
  a({ id: 'OF-A-00410', field: 'yield_product_substrate', rep: [0.66, 'g g⁻¹'], norm: [0.66, 'g g⁻¹'], src: 'SRC-0023', st: 'journal', loc: '§3.2 Table 3', ctx: BAG, note: 'Alkaline.' }),
  a({ id: 'OF-A-00411', field: 'byproduct_conc', rep: [2.4, 'g L⁻¹'], norm: [2.4, 'g L⁻¹'], src: 'SRC-0023', st: 'journal', loc: '§3.4 Fig. 4', ctx: BAG,
      note: 'Furfural in dilute-acid hydrolysate. Against OF-A-00404 this sits above the tolerance of the chosen organism, which is why severity has to come down or detoxification has to go in.' }),
  a({ id: 'OF-A-00412', field: 'byproduct_conc', rep: [0.6, 'g L⁻¹'], norm: [0.6, 'g L⁻¹'], src: 'SRC-0025', st: 'patent-example', loc: 'Example 2', pf: 'PF-014', conf: 0.86, ctx: BAG,
      note: 'Furfural in organosolv hydrolysate. Comfortably below tolerance, which is the second reason organosolv wins on technical grounds and the reason its capital cost has to be argued against rather than dismissed.' }),
  a({ id: 'OF-A-00413', field: 'capex', rep: [1.9, 'fraction'], norm: [1.9, 'fraction'], src: 'SRC-0025', st: 'journal', loc: '§5.1', ctx: BAG, note: 'Organosolv installed capital as a multiple of dilute acid at equal throughput, solvent recovery included.' }),
  a({ id: 'OF-A-00414', field: 'inhibitor_tolerance', rep: [0.9, 'g L⁻¹'], norm: [0.9, 'g L⁻¹'], src: 'SRC-0024', st: 'journal', loc: '§3.1 Table 2', ctx: { organismId: 'ORG-SCE-01' } }),
  a({ id: 'OF-A-00415', field: 'opex', rep: [140, 'USD t⁻¹'], norm: [140, 'USD t⁻¹'], src: 'SRC-0026', st: 'journal', loc: '§4.2', ctx: BAG, note: 'Cellulase loading cost per tonne of sugar released.' }),
  a({ id: 'OF-A-00416', field: 'capex', rep: [3167, 'USD t⁻¹'], norm: [3167, 'USD t⁻¹'], src: 'SRC-0027', st: 'journal', loc: '§3 Table 2',
      q: 'installed capital of 38 M USD for a 12,000 t/yr lactate facility', ctx: { scale: '12,000 t a⁻¹' },
      note: 'The scaling anchor for every capex number in Archetype 4. 38,000,000 / 12,000. Everything else is the six-tenths rule applied to this point.' }),
  a({ id: 'OF-A-00417', field: 'minimum_selling_price', rep: [2900, 'USD t⁻¹'], norm: [2900, 'USD t⁻¹'], src: 'SRC-0026', st: 'journal', loc: '§5.1', ctx: { productId: 'xylitol' } }),
  a({ id: 'OF-A-00418', field: 'minimum_selling_price', rep: [1150, 'USD t⁻¹'], norm: [1150, 'USD t⁻¹'], src: 'SRC-0026', st: 'journal', loc: '§5.1', ctx: { productId: 'L-lactic acid' } , reconciled: ['OF-A-00419'], conflictNote: 'Stated in USD t⁻¹ against OF-A-00419 in EUR kg⁻¹. The two look like a disagreement and are not: converted at the fixed corpus rate they agree within 1.5 %. The gap was in the units, and it is closed.'}),
  a({ id: 'OF-A-00419', field: 'minimum_selling_price', rep: [1.05, 'EUR kg⁻¹'], norm: [1134, 'USD t⁻¹'],
      der: { fn: 'linear', usingAccessionIds: [], note: 'EUR kg⁻¹ → USD t⁻¹ at the fixed demo rate of 1.08. The rate is fixed corpus-wide; a floating rate would make two identical Accessions disagree by the date they were viewed.' },
      src: 'SRC-0026', st: 'journal', loc: '§5.1 Table 5', ctx: { productId: 'L-lactic acid' },
      note: 'Same quantity as OF-A-00418 from a European cost basis. Within 1.5 % after conversion, which is the kind of agreement that only becomes visible once units are closed.' , reconciled: ['OF-A-00418'], conflictNote: 'Stated in EUR kg⁻¹ against OF-A-00418 in USD t⁻¹. Converted at the fixed corpus rate the two agree within 1.5 % — an apparent disagreement that normalisation resolves.'}),
];

// ══════════════════════════════════════════════════════════════════════
// CLUSTER 5 — meat-analogue decomposition
// ══════════════════════════════════════════════════════════════════════

export const ACCESSIONS_ANALOGUE: Accession[] = [
  a({ id: 'OF-A-00501', field: 'purity', rep: [0.8, '% (w/w)'], norm: [0.8, '% (w/w)'], src: 'SRC-0028', st: 'journal', loc: '§3.1',
      q: 'sensory discrimination was lost below 0.8 % of formulation mass', ctx: { productId: 'heme protein' },
      note: 'The concentration that has to be reached. It also sits inside the range recited by PF-009 claim 1, which is what makes the branch a licensing question rather than a formulation question.' }),
  a({ id: 'OF-A-00502', field: 'titer', rep: [3.6, 'g L⁻¹'], norm: [3.6, 'g L⁻¹'], src: 'SRC-0028', st: 'patent-example', loc: 'Example 1', pf: 'PF-009', conf: 0.86,
      ctx: { productId: 'heme protein', organismId: 'ORG-KPH-01', mode: 'fed-batch' } }),
  a({ id: 'OF-A-00503', field: 'purity', rep: [62, '% (w/w)'], norm: [62, '% (w/w)'], src: 'SRC-0028', st: 'patent-example', loc: 'Example 1', pf: 'PF-009', conf: 0.84,
      q: 'heme occupancy of 62 %', ctx: { productId: 'heme protein', organismId: 'ORG-KPH-01' },
      note: 'Apoprotein without its cofactor is inactive for this purpose. Occupancy is the quality attribute and titer alone is misleading.' }),
  a({ id: 'OF-A-00504', field: 'temperature', rep: [68, '°C'], norm: [68, '°C'], src: 'SRC-0028', st: 'journal', loc: '§2.4', ctx: { productId: 'heme protein' },
      note: 'Where the colour transition happens on cooking. The reason this branch is about flavour chemistry and visual behaviour together rather than either alone.' }),
  a({ id: 'OF-A-00505', field: 'temperature', rep: [45, '°C'], norm: [45, '°C'], range: [28, 45], src: 'SRC-0029', st: 'journal', loc: '§2.1 Fig. 1', ctx: { productId: 'structured fat' },
      note: 'Beef fat melts across a wide band, and the width is what gives the release profile. A sharp-melting fat is wrong even at the right midpoint.' }),
  a({ id: 'OF-A-00506', field: 'temperature', rep: [25, '°C'], norm: [25, '°C'], range: [24, 26], src: 'SRC-0029', st: 'journal', loc: '§2.1 Fig. 1', ctx: { productId: 'plant fat' },
      note: 'The incumbent plant fat melts in a two-degree window well below the target band. This gap is the technical statement of the whole fat-phase problem.' }),
  a({ id: 'OF-A-00507', field: 'purity', rep: [58, '% (w/w)'], norm: [58, '% (w/w)'], src: 'SRC-0031', st: 'journal', loc: '§3.2', prov: 'gold',
      q: 'lipid accumulation reached 58 % of dry cell weight under nitrogen limitation', ctx: { organismId: 'ORG-RTO-01' } }),
  a({ id: 'OF-A-00508', field: 'purity', rep: [48, '% (w/w)'], norm: [48, '% (w/w)'], src: 'SRC-0031', st: 'journal', loc: '§3.3 Table 2',
      q: 'oleate accounted for 48 % of total fatty acids', ctx: { organismId: 'ORG-RTO-01' },
      note: 'Tunable by nitrogen regime and temperature, which is what makes the melting profile a design variable rather than a property.' }),
  a({ id: 'OF-A-00509', field: 'purity', rep: [3.4, ''], norm: [3.4, ''], src: 'SRC-0030', st: 'journal', loc: '§3.1', ctx: { organismId: 'ORG-FVE-01' },
      q: 'native hyphal alignment gave an anisotropy index of 3.4 without texturisation' , conflicts: ['OF-A-00511'], conflictNote: 'Identical measured anisotropy reached two ways: native hyphal morphology here, claimed shear-cell texturisation in OF-A-00511. The values agree and what they imply does not — one route is enclosed and one is not, so a reader who sees only the number learns the wrong thing.'}),
  a({ id: 'OF-A-00510', field: 'purity', rep: [1000, ''], norm: [1000, ''], src: 'SRC-0030', st: 'journal', loc: '§4.2', ctx: { organismId: 'ORG-FVE-01' },
      q: 'colonial mutants dominated after approximately 1,000 h', note: 'Run length ceiling for continuous culture. A hard operational constraint that sets the turnaround economics of the whole branch.' }),
  a({ id: 'OF-A-00511', field: 'purity', rep: [3.4, ''], norm: [3.4, ''], src: 'SRC-0030', st: 'patent-example', loc: 'Example 5', pf: 'PF-011', conf: 0.85,
      ctx: { productId: 'texturised protein' },       note: 'The claimed unit operation reaches the same anisotropy index as the native morphology in OF-A-00509. Identical outcome, one route claimed and one not — the cleanest possible argument for routing around a patent instead of licensing it.' , conflicts: ['OF-A-00509'], conflictNote: 'Identical measured anisotropy reached two ways: claimed shear-cell texturisation here, native hyphal morphology in OF-A-00509. The values agree and what they imply does not.'}),
  a({ id: 'OF-A-00512', field: 'purity', rep: [2, '% (w/w)'], norm: [2, '% (w/w)'], src: 'SRC-0030', st: 'journal', loc: '§5.1', ctx: { organismId: 'ORG-FVE-01' },
      note: 'RNA content ceiling for food use. A real unit operation with real yield loss, and it is invisible in every paper about the organism.' }),
];

// ══════════════════════════════════════════════════════════════════════

export const ACCESSIONS: Accession[] = [
  ...ACCESSIONS_LYSINE,
  ...ACCESSIONS_3HP,
  ...ACCESSIONS_CAPACITY,
  ...ACCESSIONS_LIGNO,
  ...ACCESSIONS_ANALOGUE,
];

export const ACCESSION_BY_ID: Record<string, Accession> = Object.fromEntries(ACCESSIONS.map((x) => [x.id, x]));

// ── Verification ───────────────────────────────────────────────────────

/**
 * Recompute every normalisation from its reported original. The authored
 * `normalized` value is a reading convenience; this is the check that it is
 * not a lie. Wire into scripts/check-seed.ts and fail the build on mismatch.
 */
export function verifyNormalisation(accs: Accession[] = ACCESSIONS, tol = 1e-3): string[] {
  const errs: string[] = [];
  const byId = Object.fromEntries(accs.map((x) => [x.id, x]));
  const unit = (u: string) => UNIT_TABLE.find((d) => d.unit === u);

  for (const acc of accs) {
    const { fn, usingAccessionIds } = acc.derivation;
    const r = acc.reported.value;
    let computed: number | null = null;

    if (fn === 'identity') {
      computed = r;
    } else if (fn === 'temperature') {
      // A pH correction is not a unit conversion: the offset is a property of
      // the medium, not of the scale, so it cannot come from UNIT_TABLE. It
      // comes from the derivation's own params instead. This branch previously
      // read `computed = acc.normalized.value`, which asked the Accession
      // nothing — see DerivationParams for how that was found.
      const off = acc.derivation.params;
      if (off && off.kind === 'offset') computed = r + off.delta;
      else if (acc.field === 'ph') {
        errs.push(`${acc.id}: a pH correction needs derivation.params { kind: 'offset' } — the offset is medium-specific and cannot be read off the unit table`);
        continue;
      } else {
        const u = unit(acc.reported.unit);
        if (u) computed = acc.reported.unit === '°C' ? r : r + (u.offset ?? 0);
      }
    } else if (fn === 'linear') {
      const u = unit(acc.reported.unit);
      if (acc.reported.unit === 'µg L⁻¹') computed = r * 1e-3;
      else if (acc.reported.unit === '% (w/w)' && acc.normalized.unit === 'g g⁻¹') computed = r * 0.01;
      else if (acc.reported.unit === 'EUR kg⁻¹') computed = r * 1080;
      else if (acc.reported.unit === 'fraction' && usingAccessionIds.length === 1) {
        const base = byId[usingAccessionIds[0]];
        computed = base ? r * base.normalized.value : null;
      } else computed = u ? r * u.toCanonical : null;
    } else if (fn === 'specific-to-volumetric') {
      const x = byId[usingAccessionIds[0]];
      if (!x) { errs.push(`${acc.id}: auxiliary ${usingAccessionIds[0]} not found`); continue; }
      const targetIsMolar = acc.normalized.unit.startsWith('mmol') || acc.normalized.unit.startsWith('mol');
      const isMolar = acc.reported.unit.startsWith('mmol');
      const m = isMolar && !targetIsMolar ? (MOLAR_MASS['L-lysine'] ?? 1) : 1;
      computed = targetIsMolar ? r * x.normalized.value : (isMolar ? (r * m / 1000) : r) * x.normalized.value;
    } else if (fn === 'molar-to-mass') {
      // Replayed from named species rather than trusted. The note states the
      // arithmetic in prose and prose cannot be checked; `params` carries the
      // same statement in a form this function can execute.
      const pr = acc.derivation.params;
      if (!pr) {
        errs.push(`${acc.id}: molar-to-mass without derivation.params — nothing to recompute from, so the value would be accepted unchecked`);
        continue;
      }
      if (pr.kind === 'molar-ratio') {
        const num = MOLAR_MASS[pr.numerator];
        const den = MOLAR_MASS[pr.denominator];
        if (num === undefined || den === undefined) {
          errs.push(`${acc.id}: molar-ratio names ${num === undefined ? pr.numerator : pr.denominator}, which is not in MOLAR_MASS`);
          continue;
        }
        computed = r * (num / den);
      } else if (pr.kind === 'molar-mass') {
        const m = MOLAR_MASS[pr.species];
        if (m === undefined) { errs.push(`${acc.id}: molar-mass names ${pr.species}, which is not in MOLAR_MASS`); continue; }
        // mM · g mol⁻¹ = mg L⁻¹; the canonical unit is g L⁻¹.
        computed = acc.reported.unit === 'mM' ? (r * m) / 1000 : r * m;
      } else {
        errs.push(`${acc.id}: molar-to-mass carries params of kind '${pr.kind}', which this rule cannot use`);
        continue;
      }
    }

    if (computed === null) { errs.push(`${acc.id}: no rule for ${fn} / ${acc.reported.unit}`); continue; }
    const rel = Math.abs(computed - acc.normalized.value) / Math.max(1e-9, Math.abs(acc.normalized.value));
    if (rel > tol) errs.push(`${acc.id}: authored ${acc.normalized.value}, recomputed ${computed.toFixed(6)}`);
  }
  return errs;
}

/** Every Accession that may not enter a statistic, with its reason. */
export function heldAccessions(accs: Accession[] = ACCESSIONS) {
  return accs.filter((x) => x.hold).map((x) => ({ id: x.id, field: x.field, reason: x.hold! }));
}
