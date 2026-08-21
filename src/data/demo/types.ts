// openFerment demo suite — canonical types (OF-DEMO-002 §6).
//
// WHY `src/data/demo/` AND NOT `src/data/`. OF-DEMO-001 §3 says to drop this
// beside the corpus types; it lives one directory down instead, for the reason
// that brief's own §8 gives — "do not merge the two object pools". Two modules
// in one directory would both export a type called `Provenance`, and they are
// NOT the same type: `src/data/types.ts`'s is GENERATED from the Pydantic
// models in `packages/core` and has eight members, this one has eleven. A
// reader who imports the wrong one gets a compile error at best and a silently
// different union at worst. The directory boundary is what makes the two
// impossible to confuse, and it is why nothing here imports from the corpus
// types and nothing there imports from here.
//
// Nothing in this file is generated, and nothing in it may be: no entity here
// has a Pydantic model, because no server produces one yet. If one ever does,
// that model becomes canonical and this file is generated from it like
// `types.generated.ts` — the repo rails' one rule applies to this pool exactly
// as it does to the other.
//
// These live alongside the existing casein-corpus types, not inside them.
// The only shared symbol is `Provenance`, widened here. An `Accession` and an
// `ExtractionRecord` are different epistemic objects: a record is a catalogued
// literature claim awaiting source verification; an Accession is one quantity
// with complete provenance under a permanent citable identifier. Keeping the
// two apart is what lets the interface tell the truth about both.

// ── Provenance and evidence ────────────────────────────────────────────

/**
 * How far a value has been checked. Widened from the corpus union with four
 * values this suite needs. `unsourced` is the fault state — a quantity with no
 * provenance record at all — and must be unreachable in the seeded build.
 */
export type Provenance =
  | 'gold'
  | 'verified'
  | 'curated'
  | 'unverified'
  | 'user'
  | 'industry-estimate'
  | 'demo'
  | 'computed'        // derived from other Accessions by a named function
  | 'deposited'       // measured at a Guild Chapter bench, carries a Common Seal
  | 'excursion'       // measured, but the run carried a flagged deviation
  | 'unsourced';      // DEFECT

/**
 * What kind of thing produced the value. Orthogonal to Provenance: a verified
 * patent example and a verified journal measurement are the same verification
 * state and completely different claims. Encoded as tick GEOMETRY, never as a
 * second hue axis.
 */
export type SourceType =
  | 'journal'
  | 'patent-example'
  | 'patent-claim'
  | 'defensive-publication'
  | 'thesis'
  | 'bench-deposit'
  | 'trade-statistic'
  | 'vendor-datasheet'
  | 'computed';

/** Why an Accession may not enter a statistic. Visible, never silent. */
export type HoldReason =
  | 'recitation'          // reports another study's measurement
  | 'industry-estimate'   // vendor or market claim, not evidence
  | 'excursion-flagged'   // the run behind it deviated
  | 'superseded'          // a correction replaced it
  | 'upper-reported-case' // best observed, not expected
  | 'unit-ambiguous';     // normalisation could not be closed

// ── Quantities ─────────────────────────────────────────────────────────

export interface Quantity {
  value: number;
  unit: string;
  /** Present when the value is a range rather than a point. */
  range?: { low: number; high: number };
  /** Present when the source reported dispersion. */
  sd?: number;
  n?: number;
}

/**
 * The auxiliary quantities a normalisation consumed. Every entry is itself an
 * Accession id, which is what makes the provenance graph recursive rather than
 * decorative — converting g gDCW⁻¹ h⁻¹ to g L⁻¹ h⁻¹ requires a biomass
 * concentration, and that concentration has its own provenance.
 */
/**
 * The arithmetic a normalisation performed, in machine-readable form.
 *
 * WHY THIS EXISTS. `note` states the arithmetic in prose — "90.08 / 92.09" —
 * and prose cannot be replayed. `verifyNormalisation` originally handled the
 * two cases below by setting `computed = acc.normalized.value`, which makes the
 * comparison true by construction: six Accessions were passing a check that
 * asked them nothing. A perturbation sweep found them (128 of 134 caught).
 * OF-DEMO-001 §3 is explicit — "Do not trust the authored normalisation;
 * verify it in code" — so the inputs the arithmetic needs are typed here.
 *
 * Species are NAMED rather than given as numbers, so a molar mass appears in
 * exactly one place (`MOLAR_MASS`) and a correction to it reaches every
 * Accession that used it.
 */
export type DerivationParams =
  /** mol mol⁻¹ → g g⁻¹. Both names must be keys of `MOLAR_MASS`. */
  | { kind: 'molar-ratio'; numerator: string; denominator: string }
  /** mM → g L⁻¹, or any single-species molar conversion. */
  | { kind: 'molar-mass'; species: string }
  /**
   * An additive correction the unit table cannot carry because it is not a
   * property of the unit. A pH offset is medium-specific, so it belongs to the
   * measurement rather than to the scale.
   */
  | { kind: 'offset'; delta: number; because: string };

export interface Derivation {
  fn: 'identity' | 'linear' | 'specific-to-volumetric' | 'temperature' | 'molar-to-mass' | 'yield-basis';
  usingAccessionIds: string[];
  note: string;
  /**
   * Required wherever `note` states arithmetic that `fn` and the unit table do
   * not by themselves determine — every `molar-to-mass`, and any `temperature`
   * carrying a medium-specific offset. `verifyNormalisation` reports a missing
   * one as a failure rather than skipping it, because a skipped Accession is an
   * unchecked Accession.
   */
  params?: DerivationParams;
}

// ── Field ontology ─────────────────────────────────────────────────────

export type FieldFamily =
  | 'process'        // T, pH, DO, feed, agitation
  | 'performance'    // titer, yield, productivity, qp
  | 'transport'      // kLa, OTR, OUR, heat
  | 'physiology'     // mu, byproducts, tolerance
  | 'pathway'        // enzyme activity, flux, cofactor demand
  | 'downstream'     // separation yield, purity
  | 'economics'      // capex, opex, MSP, import value
  | 'regulatory';

export type FieldId =
  // process
  | 'temperature' | 'ph' | 'dissolved_oxygen' | 'feed_rate' | 'mu_setpoint'
  | 'agitation_power' | 'aeration_rate' | 'co2_overlay' | 'biotin_conc'
  // performance
  | 'titer' | 'yield_product_substrate' | 'volumetric_productivity'
  | 'specific_productivity' | 'byproduct_conc' | 'carbon_balance_closure'
  // transport
  | 'kla' | 'otr' | 'our' | 'cer' | 'rq' | 'metabolic_heat' | 'cooling_duty'
  // physiology
  | 'growth_rate_mu' | 'biomass_density' | 'inhibitor_tolerance' | 'critical_do'
  // pathway
  | 'enzyme_activity' | 'cofactor_demand' | 'theoretical_yield' | 'flux_split'
  // downstream
  | 'separation_yield' | 'purity' | 'broth_viscosity'
  // economics
  | 'capex' | 'opex' | 'minimum_selling_price' | 'feedstock_cost'
  | 'import_volume' | 'import_cif'
  // regulatory
  | 'regulatory_class';

export interface FieldDef {
  id: FieldId;
  name: string;
  family: FieldFamily;
  canonicalUnit: string;
  definition: string;
  /** Fields where a median is meaningless — categorical or design choices. */
  aggregatable: boolean;
}

// ── The Accession ──────────────────────────────────────────────────────

/**
 * One quantity with complete provenance under a permanent citable identifier.
 * The unit of record. Everything in the suite either is one, references one,
 * or is computed from several.
 */
export interface Accession {
  id: string;                    // OF-A-00112
  field: FieldId;

  /** Exactly as the source stated it. Never overwritten, never hidden. */
  reported: Quantity;
  /** Normalised to the field's canonical unit. RECOMPUTED at load. */
  normalized: Quantity;
  derivation: Derivation;

  sourceId: string;
  sourceType: SourceType;
  /** Section, table, figure, or working-example number. */
  locator: string;
  /** Verbatim from the source. Short. */
  quote?: string;

  provenance: Provenance;
  confidence: number;            // 0–1, extraction confidence
  isPrimary: boolean;
  hold?: HoldReason;
  citesAccessionId?: string;     // set when this is a recitation

  /** Conditions under which the quantity holds. Without these it is noise. */
  context: {
    organismId?: string;
    productId?: string;
    scale?: string;              // '5 L', '300 m³', 'shake flask'
    mode?: 'batch' | 'fed-batch' | 'continuous' | 'shake-flask' | 'plate';
    temperatureC?: number;
    ph?: number;
    doPercent?: number;
    feedstock?: string;
    jurisdiction?: string;
  };

  /** Patent family, when sourceType is patent-example or patent-claim. */
  patentFamilyId?: string;
  /** Run, when sourceType is bench-deposit. */
  runId?: string;

  /** Set when this Accession disagrees with another on the same field. */
  conflictsWith?: string[];

  poolOnly?: boolean;            // in the pool, not yet used by an archetype
  ledger: LedgerEntry[];
}

export interface LedgerEntry {
  at: string;                    // ISO
  who: string;
  action: string;
  /** Accessions whose values moved because of this entry. */
  propagatedTo?: string[];
}

export interface Contradiction {
  field: FieldId;
  accessionIds: string[];
  /** What would have to be true for both to be right. May be empty. */
  reconciliations: string[];
  status: 'open' | 'resolved' | 'irreconcilable';
  note: string;
}

// ── Sources ────────────────────────────────────────────────────────────

export interface Source {
  id: string;                    // SRC-0041
  type: SourceType;
  title: string;
  authors: string[];
  year: number;
  venue: string;
  doi?: string;
  /** Set for patent sources. */
  patentFamilyId?: string;
  openAccess: boolean;
  ingestState: 'catalogued' | 'parsed' | 'verified';
}

// ── Patents ────────────────────────────────────────────────────────────

export type ClaimStatus =
  | 'enclosed'              // in force, claim reads on the step
  | 'expiring'              // in force, expiry within DEMO_HORIZON_MONTHS
  | 'expired'
  | 'never-nationalised'    // PCT filed, never entered this jurisdiction
  | 'no-claim-found'
  | 'pending';

export interface PatentFamily {
  id: string;                    // PF-004
  /** Synthetic. Out-of-range series so it cannot collide with a real filing. */
  representativeNumber: string;  // 'US 2029/0114872 A1'
  assignee: string;              // synthetic
  title: string;
  priorityDate: string;          // ISO
  termYears: number;             // 20 from priority, adjusted where stated
  /** One entry per jurisdiction the family actually entered. */
  jurisdictions: {
    code: string;                // 'US' | 'EP' | 'CN' | 'JP' | 'KR' | 'BR' | 'IN' | 'RW' | 'ARIPO' | 'ZA' | 'KE'
    status: ClaimStatus;
    expiry?: string;
  }[];
  /** Independent claim scope, expressed in corpus field vocabulary. */
  claimScope: {
    element: string;
    fields: FieldId[];
    /** Ranges recited in the claim, normalised. */
    recitedRange?: { field: FieldId; low: number; high: number; unit: string };
  }[];
  /** Working examples, including comparative examples that fail on purpose. */
  examples: {
    number: string;              // 'Example 7'
    comparative: boolean;
    summary: string;
    accessionIds: string[];
  }[];
  notes: string;
}

// ── Organisms and pathways ─────────────────────────────────────────────

export interface Organism {
  id: string;                    // ORG-CGL-01
  binomial: string;
  designation: string;
  description: string;
  gramClass: 'gram-positive' | 'gram-negative' | 'yeast' | 'filamentous-fungus' | 'archaeon';
  /** What the chassis can and cannot do. Competence findings, not opinions. */
  competence: {
    capability: string;
    status: 'yes' | 'no' | 'partial' | 'unknown';
    basisAccessionIds: string[];
    note: string;
  }[];
  optima: {
    temperatureC: { low: number; high: number };
    ph: { low: number; high: number };
    criticalDoPercent?: number;
  };
  /** Constraints this organism imposes on any process built around it. */
  constraints: string[];
  gras: boolean;
  regulatoryNote: string;
}

export interface EnzymeStep {
  id: string;                    // STP-MCR-02
  name: string;
  ec?: string;
  substrate: string;
  product: string;
  cofactors: string[];
  /** Per mole product. Negative means net production. */
  cofactorStoich: { species: string; molPerMolProduct: number }[];
  sourceOrganism: string;
  /** Claim status per jurisdiction for this specific step. */
  claims: { patentFamilyId: string; jurisdictions: string[]; status: ClaimStatus }[];
  knownIssues: string[];
  accessionIds: string[];
}

export interface Route {
  id: string;                    // RTE-3HP-MCR
  productId: string;
  name: string;
  summary: string;
  steps: EnzymeStep[];
  /** Compatible hosts, with per-host achieved performance where known. */
  hosts: {
    organismId: string;
    bestTiter?: string;          // Accession id
    bestYield?: string;          // Accession id
    note: string;
  }[];
  theoreticalYieldAccessionId: string;
  oxygenDemand: 'none' | 'low' | 'moderate' | 'high';
  byproducts: string[];
  downstreamDifficulty: 'low' | 'moderate' | 'high';
  /** The count that drives the headline finding. */
  openSurface: { totalSteps: number; enclosedSteps: number; expiringSteps: number };
}

// ── Plant, envelope, candidates ────────────────────────────────────────

export interface Plant {
  id: string;                    // PLT-KGL-01
  name: string;
  location: { city: string; country: string; jurisdiction: string; ambientC: number };
  vessels: {
    count: number;
    workingVolumeM3: number;
    material: string;
    sipCapable: boolean;
    impeller: string;
    hOverD: number;
    installedPowerPerVolume: number; // W m⁻³
    maxAerationVvm: number;
  };
  utilities: {
    chilledWaterKW: number;
    chilledWaterSupplyC: number;
    coolingTowerSupplyC: number;
    steamKgPerH: number;
    gridReliability: 'firm' | 'intermittent';
    outageProfile?: string;
  };
  downstream: {
    unit: string;
    capacity: string;
  }[];
  feedstocksWithinKm: { name: string; km: number; costPerTonneUSD: number; accessionId: string }[];
}

/** What a process needs. Same axes as the plant's supply envelope. */
export interface DemandVector {
  otrRequired: number;           // mmol L⁻¹ h⁻¹
  coolingDutyKW: number;
  powerPerVolume: number;        // W m⁻³
  viscosityClass: 'newtonian-low' | 'newtonian-high' | 'non-newtonian';
  sterilityClass: 'aseptic' | 'clean' | 'open';
  separationClass: 'centrifuge' | 'filtration' | 'extraction' | 'distillation' | 'crystallisation';
  cycleTimeH: number;
  temperatureC: number;
}

export interface Candidate {
  id: string;                    // CND-007
  product: string;
  hsCode?: string;
  organismId: string;
  demand: DemandVector;
  /** Filled by lib/envelope.ts at load. Never authored. */
  match?: EnvelopeMatchResult;
  patentPosition: { jurisdiction: string; status: ClaimStatus; familyIds: string[] }[];
  feedstock: string;
  feedstockCostAccessionId: string;
  tradeAccessionIds: string[];
  regulatoryClass: string;
  timeToRevenueMonths: number;
  verdict?: 'promoted' | 'viable' | 'marginal' | 'excluded';
  /** Set when the naive operating point fails but a de-rated one survives. */
  rescue?: { byDeliverableId: string; change: string; cost: string };
  note: string;
}

export interface EnvelopeMatchResult {
  axes: {
    axis: string;
    demand: number | string;
    supply: number | string;
    headroom: number;            // fraction; negative means violated
    binding: boolean;
  }[];
  feasible: boolean;
  bindingAxis?: string;
}

// ── Runs ───────────────────────────────────────────────────────────────

export interface Channel {
  id: string;
  label: string;
  unit: string;
  derived: boolean;              // computed channels carry a computed Tick
  values: number[];              // one per Tick
}

export interface Excursion {
  id: string;
  startTick: number;
  endTick: number;
  channel: string;
  description: string;
  /** Filled by lib/excursion.ts. */
  integrals?: {
    o2DeficitMmolPerL: number;
    cerDeviationMmolPerL: number;
    estimatedCarbonDivertedCmolPerL: number;
  };
}

export interface RunRecord {
  id: string;                    // RUN-047
  plantId: string;
  organismId: string;
  productId: string;
  startedAt: string;
  ticksPerHour: number;
  setpoints: Record<string, number>;
  channels: Channel[];
  excursions: Excursion[];
  /** Runs used as the comparability basis. */
  comparisonBasis: string[];
  verdict?: ExcursionVerdict;
  /** Accessions this run deposited. */
  depositedAccessionIds: string[];
  commonSeal?: {
    id: string;
    operator: string;
    chapterId: string;
    sealedAt: string;
  };
}

export interface ExcursionVerdict {
  comparable: boolean;
  recommendation: 'continue' | 'continue-flagged' | 'terminate';
  reasoning: string[];
  basisRunIds: string[];
  /** The annotation that propagates downstream. */
  annotation: {
    accessionIds: string[];
    hold: HoldReason;
    note: string;
  };
}

// ── Archetype deliverables ─────────────────────────────────────────────

export type ArchetypeId = 'AR1' | 'AR2' | 'AR3' | 'AR4' | 'AR5' | 'AR6';

export interface DisclosureCandidate {
  id: string;                    // DC-011
  archetype: ArchetypeId;
  what: string;
  /** What must be published for the disclosure to be enabling. */
  enablingDetail: string[];
  reason:
    | 'unclaimed-process-region'
    | 'parameter-region-open'
    | 'enzyme-variant-at-risk'
    | 'jurisdictional-gap'
    | 'negative-result-unpublished';
  urgency: 'now' | 'months' | 'watch';
  estimatedWindowMonths?: number;
  supportingAccessionIds: string[];
  venue: string;
}

export interface FactorExclusion {
  low: number;
  high: number;
  reason: string;
  accessionIds: string[];
  singleSource: boolean;
}

export interface FactorMapEntry {
  field: FieldId;
  unit: string;
  domain: { low: number; high: number };
  recommended: { low: number; high: number };
  excluded: FactorExclusion[];
  explored: { low: number; high: number; accessionIds: string[] }[];
  ftoFlag?: { patentFamilyId: string; recitedRange: { low: number; high: number }; jurisdiction: string };
}

export interface RunDesignPoint {
  run: number;
  setpoints: Record<string, number>;
  rationale: string;
  /** Which unexplored cell this lands in. */
  cell: string;
}

export interface Deliverable {
  id: string;                    // DLV-AR1-001
  archetype: ArchetypeId;
  title: string;
  query: string;
  createdAt: string;
  accessionIds: string[];
  disclosureCandidateIds: string[];
  /** One of the payload shapes below, discriminated by `archetype`. */
  payload:
    | { kind: 'factor-map'; factors: FactorMapEntry[]; design: RunDesignPoint[]; excludedAccessionIds: string[] }
    | { kind: 'route-comparison'; productId: string; routeIds: string[]; recommendation: string; asymmetry: string }
    | { kind: 'capacity-screen'; plantId: string; candidateIds: string[]; promotedId: string }
    | { kind: 'facility-concept'; concepts: FacilityConcept[] }
    | { kind: 'problem-tree'; rootId: string; nodes: ProblemNode[]; handoffFlowIds: string[] }
    | { kind: 'excursion-verdict'; runId: string; verdict: ExcursionVerdict };
}

export interface FacilityConcept {
  id: string;
  name: string;
  scaleTonnesPerYear: number;
  riskLevel: 'low' | 'moderate' | 'high';
  blockFlow: { block: string; detail: string; accessionIds: string[] }[];
  majorEquipment: { item: string; sizingBasis: string; costUSD: number }[];
  capexUSD: number;
  capexAccuracyClass: string;    // 'AACE Class 5 (−30/+50%)'
  opexPerTonneUSD: number;
  npvSensitivity: { parameter: string; lowPct: number; highPct: number }[];
  patentOverlay: { step: string; status: ClaimStatus; familyIds: string[] }[];
  breakevenTonnesPerYear: number;
}

export interface ProblemNode {
  id: string;
  parentId?: string;
  label: string;
  molecularTarget?: string;
  candidateOrganismIds: string[];
  patentDensity: 'low' | 'moderate' | 'high' | 'very-high';
  technicalMaturity: 'demonstrated' | 'pilot' | 'lab' | 'speculative';
  recommendation: 'build' | 'license' | 'avoid' | 'partner';
  rationale: string;
  accessionIds: string[];
  /** Set on leaves that spawn an Archetype 2 query. */
  spawnsFlowId?: string;
}
