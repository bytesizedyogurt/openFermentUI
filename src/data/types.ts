// openFerment Sim — canonical entity types (OF-DES-001 §15)

/**
 * Provenance classes (OF-DES-001 §7.4, revised by OF-COR-001 §20).
 *
 * With a real corpus, 'demo' no longer means "this whole platform is fake" —
 * it is reserved for the three surfaces that remain modeled rather than
 * measured: simulation response grids, scripted agent answer text, and
 * anything derived from them.
 *
 * 'curated' is new and load-bearing. It marks a value transcribed from the
 * curation document (OF-COR-001) rather than read off the source PDF. The
 * claim is real and attributable, but it has not yet been checked against the
 * paper itself, so it is weaker than 'verified' and must never silently pass
 * as a source-span extraction.
 *
 * 'industry-estimate' marks market and vendor figures (OF-COR-001 §16 O8).
 * They are useful for framing and useless as evidence: excluded from the gold
 * set and from aggregate statistics by default.
 */
export type Provenance =
  | 'gold'
  | 'verified'
  | 'curated'
  | 'unverified'
  | 'user'
  | 'industry-estimate'
  | 'demo';

export type ParameterFamily =
  | 'expression'
  | 'ptm'
  | 'functional'
  | 'cultivation'
  | 'downstream';

/** Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families. */
export type FieldId =
  // Family 1 — expression performance
  | 'expression_pct_tsp'
  | 'titer_intracellular'
  | 'titer_secreted'
  | 'secreted_fraction'
  | 'fold_improvement'
  | 'transformation_efficiency'
  | 'time_to_colony'
  // Family 2 — post-translational modification
  | 'phosphate_count'
  | 'phosphorylation_degree'
  | 'phospho_site_position'
  | 'glycan_species'
  | 'kinase_identity'
  // Family 3 — functional performance
  | 'micelle_diameter'
  | 'micellar_fraction'
  | 'gelation_ph'
  | 'calcium_binding'
  | 'melt_stretch_length'
  // Family 4 — cultivation
  | 'growth_rate_mu'
  | 'final_biomass_density'
  | 'volumetric_productivity'
  | 'medium_component_conc'
  // Family 5 — downstream and economics
  | 'disruption_protein_yield'
  | 'disruption_energy'
  | 'minimum_selling_price';

/**
 * Analytical method behind a PTM or functional measurement (OF-COR-001 §17
 * Rule 1). 'undetermined' is a first-class value: Mora Vásquez et al. record
 * it for most bacterial studies because the analysis was never done, and the
 * platform must distinguish *absence of measurement* from *measurement of
 * absence*.
 */
export type AnalysisMethod =
  | 'LC-ESI-MS'
  | 'MALDI-MS'
  | 'Phos-tag'
  | 'urea-PAGE'
  | 'urea-PAGE + phosphatase'
  | 'SDS-PAGE mobility'
  | 'Ethyl Stains-All'
  | 'CD spectroscopy'
  | 'SAXS'
  | 'SANS'
  | 'DLS'
  | 'cryo-TEM'
  | 'HPLC'
  | 'gravimetric'
  | 'spectrophotometric'
  | 'process model'
  | 'undetermined';

/** Residue-numbering convention (OF-COR-001 §19, first trap). */
export type NumberingConvention = 'precursor' | 'mature';

export interface ParameterDef {
  id: FieldId;
  family: ParameterFamily;
  name: string;
  definition: string;
  /** '' for categorical fields (kinase_identity, glycan_species). */
  canonicalUnit: string;
  range: [number, number];
  notes: string;
  /** Categorical fields hold a string value, not a number. */
  categorical?: boolean;
  /** OF-COR-001 §17 Rule 1: a value without its method is not interpretable. */
  requiresMethod?: boolean;
  /**
   * Unit families this field must NOT be auto-converted into, with the reason.
   * OF-COR-001 §17 Rule 2: %TSP and g/L are not interconvertible without cell
   * density and total-protein fraction. The engine refuses and says why.
   */
  refuseConversionTo?: { field: FieldId; because: string }[];
}

export type IngestStage = 'fetch' | 'parse' | 'chunk' | 'embed' | 'extract';
export type IngestStatus =
  /** Full text parsed into sections; spans anchor to the paper's own words. */
  | 'complete'
  /**
   * Bibliographically real, full text NOT yet ingested (OF-COR-001 §22.6).
   * The reader shows the curation entry from OF-COR-001, clearly labelled as
   * the curator's words rather than the paper's, with a DOI link out.
   */
  | 'catalogued'
  | `stage:${IngestStage}`
  /** The source document could not be retrieved at all. */
  | 'failed:fetch'
  | 'failed:parse'
  | 'shelf';

/** Which corpus thread an entry belongs to (OF-COR-001 §1). */
export type CorpusThread =
  | 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H'
  | 'I' | 'J' | 'K' | 'L' | 'M' | 'N' | 'O';

export type SourceType =
  | 'journal-article'
  | 'review'
  | 'thesis'
  | 'patent'
  | 'book'
  | 'industry-report'
  | 'preprint';

export interface PaperSection {
  id: string;
  heading: string;
  text: string;
}

export interface Paper {
  /** Corpus entry id, e.g. 'H1' — thread letter plus index (OF-COR-001 §1). */
  id: string;
  title: string;
  authors: string[];
  year: number;
  venue: string;
  organisms: string[];
  topics: string[];
  /**
   * For 'catalogued' papers this is the curator's summary from OF-COR-001,
   * NOT the publisher's abstract. `textSource` says which.
   */
  abstract: string;
  sections: PaperSection[];
  ingest: IngestStatus;

  // ── real-corpus identity (OF-COR-001) ──────────────────────────────
  thread: CorpusThread;
  sourceType: SourceType;
  /** The authoritative record key — never the author string (OF-COR-001 header). */
  doi?: string;
  pmcid?: string;
  pmid?: string;
  /** Whether `sections` hold the paper's own text or the curator's notes. */
  textSource: 'full-text' | 'curation-note';
  /** Openly retrievable vs. needs institutional access (OF-COR-001 §19). */
  openAccess: boolean;
  /** Ingestion tranche: 1 = open-access core, 2 = remainder, 3 = v1.1. */
  tranche: 1 | 2 | 3;
  /** Author string not fully resolved — must be checked at ingest ([verify]). */
  verifyNeeded?: boolean;
  /** Why this entry earns its place, from the corpus document. */
  corpusRole?: string;
}

export type RecordStatus = 'unverified' | 'verified' | 'rejected';
export type ExtractorRun = 'v0.3' | 'v0.4' | 'v0.4r';

export interface AuditEvent {
  at: string;
  who: string;
  action: string;
  from?: unknown;
  to?: unknown;
}

export interface ExtractionRecord {
  id: string;
  paperId: string;
  sectionId: string;
  quote: string;
  field: FieldId;
  /** Categorical fields (kinase_identity, glycan_species) carry a string. */
  value: number | string;
  unit: string;
  si: { value: number; unit: string };
  confidence: number;
  status: RecordStatus;
  /**
   * Explicit provenance. Extractor output is 'unverified' until reviewed;
   * values transcribed from OF-COR-001 are 'curated'; market figures are
   * 'industry-estimate' and never enter the gold set.
   */
  provenance: Provenance;
  organism?: string;
  componentTag?: string;
  gold?: { value: number | string; unit: string };
  goldOnly?: boolean;
  /** Absent for curated records — they did not come from an extractor run. */
  extractorRun?: ExtractorRun;
  rejectReason?: string;
  corrected?: { value: number; unit: string };
  reviewer?: string;
  audit: AuditEvent[];

  // ── OF-COR-001 additions ───────────────────────────────────────────
  /**
   * False. This paper is quoting someone else's measurement (OF-COR-001 §19,
   * fifth trap). Citation-of-a-citation is the most common false-independence
   * error in literature aggregation: 15 mg/L appears in both C2 (the
   * measurement) and C6 (a citation of it), and a strip plot that counts both
   * overstates consensus. Aggregate statistics must filter on this.
   */
  isPrimary: boolean;
  /** When not primary, the record this one is quoting. */
  citesRecordId?: string;
  /**
   * How the value was measured. Mandatory for PTM and functional fields
   * (OF-COR-001 §17 Rule 1) — 'undetermined' is a legitimate answer and means
   * the analysis was never done, not that the result was negative.
   */
  method?: AnalysisMethod;
  /** Required on phospho_site_position — mature and precursor differ by 15. */
  numbering?: NumberingConvention;
  /** Where in OF-COR-001 a 'curated' value was transcribed from, e.g. '§9 H4'. */
  curationRef?: string;
  /** A value the source states as a range rather than a point. */
  range?: { low: number; high: number };
  /** For comparative claims ("12-fold higher than X"), the baseline. */
  comparativeBaseline?: string;
  /** Value is a reported negative/absent result, not a missing measurement. */
  negativeResult?: boolean;
}

export interface RunOutput {
  run: ExtractorRun;
  results: {
    goldRecordId: string;
    outcome: 'match' | 'value_mismatch' | 'unit_error' | 'span_error' | 'miss';
    extracted?: { value: number; unit: string };
  }[];
  falsePositives: {
    id: string;
    paperId: string;
    field: FieldId;
    extracted: { value: number; unit: string };
    note: string;
  }[];
}

export interface CuratorNote {
  at: string;
  who: string;
  text: string;
}

export interface Strain {
  id: string;
  binomial: string;
  designation: string;
  taxonomy: string[];
  description: string;
  badges: string[];
  bsl: 1 | 2;
  notes: CuratorNote[];
}

export type ProtocolCategory =
  | 'media'
  | 'culture'
  | 'analytics'
  | 'harvest'
  | 'fermentation'
  | 'sop';

export type ScalingClass = 'per_batch_volume' | 'fixed' | 'per_unit_biomass';

export interface Material {
  name: string;
  amount: number;
  unit: string;
  scaling: ScalingClass;
  precision: number;
  stock?: { conc: number; unit: string };
  sourceRecordId?: string;
}

export interface Step {
  id: string;
  text: string; // may contain {{qty:materialName}} placeholders
  timerSec?: number;
  timerLabel?: string;
  multiCheck?: string[];
  note?: string;
  refs?: string[]; // record or paper ids
}

export interface ProtocolVersion {
  version: string;
  changelog?: string;
  baseBatch: { value: number; unit: string; label: string };
  materials: Material[];
  equipment: string[];
  safety: string[];
  steps: Step[];
  estMinutes: { active: number; total: number };
  references: { paperId?: string; recordId?: string; note?: string }[];
}

export interface Protocol {
  id: string;
  title: string;
  category: ProtocolCategory;
  organisms: string[];
  bsl: 1 | 2;
  purpose: string;
  versions: ProtocolVersion[];
  currentVersion: string;
  provenanceNote: string;
}

export interface Deviation {
  at: string;
  stepId: string;
  text: string;
}

export interface RunState {
  id: string;
  protocolId: string;
  version: string;
  scale: number; // multiplier vs baseBatch
  startedAt: number; // epoch ms
  currentStep: number;
  completed: Record<string, number>; // stepId -> epoch ms completed
  skipped: Record<string, string>; // stepId -> reason
  checks: Record<string, boolean[]>; // stepId -> multiCheck states
  deviations: Deviation[];
  timers: TimerState[];
  finishedAt?: number;
}

export interface TimerState {
  id: string;
  stepId: string;
  label: string;
  totalSec: number;
  remainingSec: number;
  running: boolean;
  startedAt?: number;
}

export type CostLine =
  | 'capex'
  | 'media'
  | 'utilities'
  | 'labor'
  | 'downstream'
  | 'other';

export interface ScenarioDim {
  /** Cite a paper where a sweep default came from the literature. */
  paperId?: string;
  key: string;
  label: string;
  unit: string;
  values: number[];
  sourceRecordId?: string;
}

export interface ScenarioAssumption {
  /** Cite a paper when the assumption rests on a source but no single record. */
  paperId?: string;
  label: string;
  value: number;
  unit: string;
  provenance: Provenance;
  recordId?: string;
  note: string;
}

export interface Scenario {
  id: string;
  modelId: 'S1' | 'S2' | 'S3';
  name: string;
  description: string;
  product: string;
  dims: ScenarioDim[];
  point: Record<string, number>;
  assumptions: ScenarioAssumption[];
  pinned: boolean;
}

export interface GridPointResult {
  msp: number;
  costLines: Record<CostLine, number>;
}

export interface SensitivityRow {
  assumption: string;
  lowPct: number;
  hiPct: number;
}

/**
 * A cost model is authored once (spreadsheet-grade engine, §17.1) and swept
 * over its grid at load time. Cost lines are $/kg product and sum to MSP by
 * construction, so the waterfall always agrees with the headline.
 */
export interface CostModel {
  modelId: 'S1' | 'S2' | 'S3';
  dims: ScenarioDim[];
  referencePoint: Record<string, number>;
  evaluate: (point: Record<string, number>) => Record<CostLine, number>;
  sensitivity: SensitivityRow[];
  /** Grid coordinates where the authored engine fails to converge (§17.3). */
  nonConvergent?: (point: Record<string, number>) => boolean;
}

/** Precomputed sweep of a CostModel (§15 ResultGrid). */
export interface ResultGrid {
  modelId: string;
  dims: { key: string; values: number[] }[];
  msp: Float64Array;
  costLines: Record<CostLine, Float64Array>;
  sensitivity: SensitivityRow[];
}

export interface ChatRetrievalHit {
  paperId: string;
  sectionId: string;
  score: number;
  snippet: string;
}

export interface ChatToolCall {
  name: string;
  args: Record<string, unknown>;
  durationMs: number;
  retrieval?: ChatRetrievalHit[];
}

export interface ChatFlow {
  id: string;
  triggers: string[];
  plan: string[];
  toolCalls: ChatToolCall[];
  answerMd: string; // chips as [[ex-0112]] / [[SP-004]]
  followups: string[]; // may be "flow:F2|label"
  clarify?: {
    question: string;
    options: { label: string; flowId: string }[];
  };
}

export type ChatMessage =
  | { kind: 'user'; id: string; text: string }
  | { kind: 'plan'; id: string; steps: string[]; done: number; collapsed: boolean }
  | { kind: 'tool'; id: string; call: ChatToolCall; expanded: boolean }
  | { kind: 'answer'; id: string; md: string; streaming: boolean; flowId?: string; followups: string[] }
  | { kind: 'clarify'; id: string; question: string; options: { label: string; flowId: string }[] }
  | { kind: 'system'; id: string; text: string; retry?: boolean };

export interface ChatSession {
  id: string;
  title: string;
  startedAt: string;
  scope?: { kind: 'paper' | 'collection'; id: string; label: string };
  messages: ChatMessage[];
  pinned: ChatRetrievalHit[];
}

export interface Collection {
  id: string;
  name: string;
  paperIds: string[];
}

export interface CheckpointQuestion {
  id: string;
  prompt: string;
  kind: 'mc' | 'numeric';
  options?: string[];
  answerIndex?: number;
  answer?: { value: number; unit: string; tolerancePct: number };
  explanation: string;
  evidenceChip?: string;
}

export interface Lesson {
  id: string;
  title: string;
  minutes: number;
  blocks: LessonBlock[];
  checkpoint: CheckpointQuestion[];
}

export type LessonBlock =
  | { kind: 'prose'; md: string }
  | { kind: 'embed'; embed: 'chip-demo' | 'record-card' | 'unit-playground' | 'mini-queue' | 'metrics-tiles' | 'strip-plot' | 'protocol-card' | 'ask-prompt' | 'scenario-widget'; arg?: string };

export interface LearnModule {
  id: string;
  index: number;
  title: string;
  blurb: string;
  lessons: Lesson[];
  outline?: string[];
}

export interface ActivityEvent {
  at: string;
  icon: string;
  text: string;
  href?: string;
  provenance: Provenance;
}

export interface JobStage {
  label: string;
  ms: number;
}

export interface Job {
  id: string;
  title: string;
  /**
   * 'runbook' is a Job that fronts a Runbook, not a Runbook itself — the tray
   * shows the progress bar while the record it belongs to lives in its own
   * slice (OF-BLD-005 §7). The two cooperate; they never merge.
   */
  kind: 'ingest' | 'extraction' | 'simulation' | 'run' | 'runbook';
  stages: JobStage[];
  stageIndex: number;
  stageProgress: number; // 0-1 within current stage
  status: 'running' | 'done' | 'failed';
  failReason?: string;
  href?: string;
  startedAt: number;
}

// ── OF-BLD-005 · molecules, vocabulary and runbooks ────────────────────
//
// Breadth alongside the Chlamydomonas β-casein throughline. Products are the
// molecules a facility could make; the vocabulary below is the facet set they
// are described with; runbooks are synthesised answers to "how would we make
// this". None of it touches the corpus — PAPERS, RECORDS and PROTOCOLS are
// unaffected, and every value here carries a modeled provenance.

/**
 * Where a unit operation sits in a downstream train, fermenter to vial. The
 * order of `UNIT_OP_STAGE_ORDER` in `vocabulary.ts` is the display order; a
 * product's own `unitOperationIds` array is the authority on its actual train,
 * because two products can use the same operation at different points.
 */
export type UnitOperationStage =
  | 'harvest'
  | 'clarification'
  | 'cell disruption'
  | 'recovery'
  | 'capture'
  | 'capture/polish'
  | 'polish'
  | 'concentration'
  | 'desalting'
  | 'isolation'
  | 'purification'
  | 'drying'
  | 'formulation'
  | 'finishing';

export interface UnitOperation {
  id: string;
  label: string;
  stage: UnitOperationStage;
  /** Scale band where the operation is used at all, when it is not universal. */
  scale?: string;
  /** Chemistry detail, e.g. the resin family for a chromatography step. */
  resin?: string;
  note?: string;
}

export type GeneticElementKind =
  | 'promoter'
  | 'signal_peptide'
  | 'fusion_tag'
  | 'maintenance'
  | 'sequence_design'
  | 'dosage';

export interface GeneticElement {
  id: string;
  label: string;
  kind: GeneticElementKind;
  /**
   * Hosts the element is described for, as vocabulary labels — NOT `Strain`
   * ids. The construct vocabulary predates the host catalogue and names
   * organisms at a coarser grain ('e-coli-bl21' covers every BL21 derivative),
   * so these must never be resolved against STRAINS.
   */
  hostFit?: string[];
  induction?: string;
  strength?: string;
  purification?: string;
  /** `true` needs a protease; 'autocatalytic' cleaves itself and costs nothing. */
  cleavable?: boolean | 'autocatalytic';
  stability?: string;
  copy?: string;
  tool?: string;
  note?: string;
}

export interface Pathway {
  id: string;
  label: string;
  products: string[];
  /** The metabolic branch point flux has to be pushed through. */
  fluxNode: string;
  note?: string;
}

export type CostBand = 'low' | 'moderate' | 'high';

export interface StorageFormat {
  id: string;
  label: string;
  tempC: number;
  shelfLife: string;
  /** What shipping this format actually requires — the cold-chain question. */
  logistics: string;
  cost: CostBand;
  note?: string;
}

export type RegulatoryBurden = 'low' | 'low-moderate' | 'moderate' | 'high' | 'very high';

export interface RegulatoryPathway {
  id: string;
  label: string;
  burden: RegulatoryBurden;
  note?: string;
}

export interface ProcessScale {
  id: string;
  label: string;
  volumeL: string;
  role: string;
}

/**
 * Patent clearance is an ambient property of every molecule, never a separate
 * mode (OF-BLD-005 §8). Six states, each with the action it implies. None of
 * them is a legal opinion — every clearance surface carries the counsel
 * callout alongside.
 */
export type ClearanceStateId =
  | 'clear-expired'
  | 'clear-none'
  | 'watch-variant'
  | 'watch-process'
  | 'blocked'
  | 'unknown';

export type ClearanceRisk = 'low' | 'low-moderate' | 'moderate' | 'high' | 'unknown';

export interface ClearanceState {
  id: ClearanceStateId;
  label: string;
  risk: ClearanceRisk;
  /** What a team should do next, in the platform's voice — not counsel's. */
  action: string;
}

export type ProductCategory =
  | 'molecular_biology_enzyme'
  | 'diagnostic'
  | 'research_protein'
  | 'food_protein'
  | 'hmo'
  | 'sweet_protein'
  | 'structural_protein'
  | 'terpene'
  | 'glycoside'
  | 'industrial_enzyme'
  | 'therapeutic_protein';

/**
 * Value per kilogram, banded rather than priced. A band is defensible from
 * public catalogue prices; a number would imply an economics model the
 * platform does not have.
 */
export type ValueDensityBand = 'low-moderate' | 'moderate' | 'high' | 'very high' | 'extreme';

export interface Product {
  id: string;
  name: string;
  aliases: string[];
  category: ProductCategory;
  /** Process family code (P1–P11) — the downstream train archetype. */
  processCode: string;
  /** Resolves against STRAINS once the OF-BLD-005 hosts are appended. */
  defaultStrainId: string;
  /** Ordered fermenter to vial. This array, not stage order, is the train. */
  unitOperationIds: string[];
  storageIds: string[];
  regulatoryIds: string[];
  clearanceState: ClearanceStateId;
  scaleId: string;
  pathwayIds: string[];
  tags: string[];
  valueDensityBand: ValueDensityBand;
  /**
   * Always 'demo' — every product record is modeled, not measured, and renders
   * as "Modeled · not measured" through the existing provenance system.
   */
  provenance: Provenance;
  note: string | null;
  /**
   * Always 'industry-estimate'. Value density and scale come from market
   * framing, not from evidence, and `aggregateExclusion()` already holds that
   * class out of every median, range and count.
   */
  economicsProvenance: Provenance;
}

/**
 * A runbook is a synthesised, followable answer to a question about making
 * something. It is deliberately NOT a `Job` (OF-BLD-005 §7): `Job` models a
 * progress bar and is owned by the jobs tray; `Runbook` is a record with
 * content that outlives the run that produced it. The tray still provides the
 * running affordance — the two types cooperate, they do not merge.
 */
export type RunbookKind = 'industrial' | 'research';

export type RunbookStatus =
  | 'draft'
  | 'running'
  | 'complete'
  /** Enumeration compute priced but not authorised. */
  | 'awaiting_budget'
  /** Resolved from a prior run's artifacts at near-zero cost. */
  | 'cache_hit'
  /** Held for a human — the model declines to rule on it. */
  | 'needs_review'
  /** Halted: a stage tried to consume a value with no source. */
  | 'blocked_unverified';

export type RunbookStageStatus =
  | 'done'
  | 'running'
  | 'queued'
  | 'pending'
  | 'review'
  | 'blocked'
  | 'draft';

export interface RunbookStage {
  name: string;
  status: RunbookStageStatus;
  /** What the stage did or is doing, in one line. */
  detail: string | null;
  /**
   * The stage's headline result when it has one — a titre, a CAPEX figure, a
   * candidate count, or a clearance verdict. Free text on purpose: stages
   * produce different kinds of answer and forcing a shape would lose them.
   */
  value: string | null;
}

/**
 * A single falsifiable claim a runbook makes before anything is run
 * (OF-BLD-006 §3.1). A report says here is what we found; a runbook says do
 * this and you will get that. Being testable is exactly why the Assay layer is
 * terminal — software cannot go further than a prediction.
 */
export interface Prediction {
  id: string;
  /** What is being predicted, in bench language. "Final titre". */
  label: string;
  value: number;
  unit: string;
  /**
   * How much prior support the number has. Not a probability — nobody has
   * calibrated one — but an honest three-way sort a person can act on.
   */
  confidence: 'high' | 'medium' | 'low';
  /** What produced it. A model, a precedent, an assumption someone made. */
  basis: string;
}

/**
 * One value the bench will record, declared before the run so the operator
 * knows what is being asked of them and the comparison is fixed in advance.
 */
export interface Measure {
  id: string;
  label: string;
  unit: string;
  /** When it is taken: 't=0', 'harvest', 'post-purification'. */
  timepoint: string;
  /** The prediction this tests, or null for context nobody predicted. */
  predictionId: string | null;
}

export interface Runbook {
  id: string;
  kind: RunbookKind;
  title: string;
  status: RunbookStatus;
  stages: RunbookStage[];
  /** Curator's framing — why this runbook is worth looking at. */
  note: string;
  eta: string | null;
  /** Artifacts a complete runbook hands over. */
  outputs: string[];
  /** Resolves against PRODUCTS, or null for a cross-cutting question. */
  productId: string | null;
  progressPct: number;
  /** Modeled compute spend, in USD. Null before a run is priced. */
  estCostUsd: number | null;
  /** Resolves against STRAINS, or null when no host has been chosen. */
  strainId: string | null;

  // ── Assay (OF-BLD-006 §3) ────────────────────────────────────────────
  /** What the runbook commits to, before a fermenter is touched. */
  predictions: Prediction[];
  /** What the bench will record, and when. */
  measurementSchema: Measure[];
  /**
   * When the predictions and schema were frozen, or null if still editable.
   *
   * Locking exists because without it the system grades its own homework:
   * predictions drift toward results and the hit rate stops meaning anything.
   * A locked runbook may be superseded by a new version; it may not be edited.
   */
  lockedAt: string | null;
  /**
   * Content hash over the predictions and schema at lock time, so a later
   * reader can tell whether what they are looking at is what was frozen.
   * Full timestamping and attestation belong to Common Seal; a hash plus an
   * ISO timestamp is what this build can honestly offer.
   */
  lockHash: string | null;
}
