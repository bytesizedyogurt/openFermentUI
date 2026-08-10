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
  kind: 'ingest' | 'extraction' | 'simulation' | 'run';
  stages: JobStage[];
  stageIndex: number;
  stageProgress: number; // 0-1 within current stage
  status: 'running' | 'done' | 'failed';
  failReason?: string;
  href?: string;
  startedAt: number;
}
