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
  /**
   * First-party experimental measurement (OF-BLD-006 §6). The strongest
   * evidence the system can hold, and the only class it produces itself: you
   * have the raw data and you know the conditions it was taken under. Ranks
   * above 'gold', which is a hand-curated reading of somebody else's paper.
   * Created by reconciling a Deposition against the Runbook that predicted it.
   */
  | 'measured'
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

  // ── set by the service overlay (OF-BLD-012 §2.1), never by the seed ──
  /** The licence the fetched full text carried, when `textSource` is 'full-text'. */
  license?: string;
  /** Why the last fetch halted, when `ingest` is a failure state. */
  ingestReason?: string;
}

export type RecordStatus = 'unverified' | 'verified' | 'rejected';
// 'haiku-1' is the first run that actually ran (OF-BLD-012 §6). The three
// before it are the seed's names for runs that never happened.
export type ExtractorRun = 'v0.3' | 'v0.4' | 'v0.4r' | 'haiku-1';

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
  range?: Range;
  /** For comparative claims ("12-fold higher than X"), the baseline. */
  comparativeBaseline?: string;
  /** Value is a reported negative/absent result, not a missing measurement. */
  negativeResult?: boolean;
  /**
   * What this record was PUBLISHED as, stamped once as it enters the store
   * and never touched by a decision (OF-BLD-012.1 F7). A promotion may move a
   * record onto the paper's own sentence and take the paper's own number;
   * this is what it was before that, so "has this been re-anchored?" and
   * "what do I restore when a correction is withdrawn?" are answered by the
   * record itself rather than by diffing it against the seed it was loaded
   * from — which a corpus update would silently change under it.
   */
  original?: { value: number | string; unit: string; quote: string; sectionId: string };
  /**
   * A candidate a reviewer decided on that the extractor's CURRENT run no
   * longer produces (OF-BLD-012.1 F3). The decision stays — it is a decision,
   * not an opinion — and the card says the sentence behind it is gone, so a
   * reviewer is not left wondering. Browser-side only: the service recomputes
   * this every time it assembles an overlay.
   */
  absentFromRun?: boolean;
  /**
   * How §2.4 rule 3 found this value in its sentence (OF-BLD-012.1 F1.2).
   * Computed by the service's anchoring and by nothing else — no model output
   * and no reviewer sets it — so the review card can say "midpoint of 7-10 d"
   * or "zero read from a negative result" beside the number.
   */
  valueBasis?: ValueBasis;
}

/**
 * A value the source states as an interval. The curators record it; §2.4
 * rule 3 anchors a midpoint or an endpoint against the sentence that states
 * it. Mirrors `Range` in models.py.
 */
export interface Range {
  low: number;
  high: number;
}

/**
 * What `POST /api/biorepo/check` answers (OF-BLD-012.1 F1.5): whether the
 * service would keep this decision, and the rule it would refuse it under.
 * The screen asks before the reviewer presses the key, so what it says is
 * what `biorepo.write` would say rather than a browser copy of the rules.
 * Mirrors `DecisionCheck` in models.py.
 */
export interface DecisionCheck {
  ok: boolean;
  rule?: string | null;
  why?: string | null;
}

/** How rule 3 found a value in its sentence. Mirrors `ValueBasis` in models.py. */
export type ValueBasis =
  | 'exact'
  | 'converted'
  | 'range-midpoint'
  | 'range-low'
  | 'range-high'
  | 'negation';

/** A value and its unit. Categorical fields carry a string value. */
export interface Quantity {
  value: number | string;
  unit: string;
}

/** One gold record scored against a run. */
export interface RunResult {
  goldRecordId: string;
  outcome: 'match' | 'value_mismatch' | 'unit_error' | 'span_error' | 'miss';
  extracted?: { value: number; unit: string };
}

/** A candidate a reviewer rejected — the only way one gets here (OF-BLD-012 §6.2). */
export interface RunFalsePositive {
  id: string;
  paperId: string;
  field: FieldId;
  extracted: { value: number; unit: string };
  note: string;
}

// Named rather than inline so the service's ExtractRun mirrors them field for
// field (OF-BLD-012 §2.5). Same shape as before; nothing here changed.
export interface RunOutput {
  run: ExtractorRun;
  results: RunResult[];
  falsePositives: RunFalsePositive[];
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
  /**
   * The durable Deposition this session is writing into, when there is one
   * (OF-BLD-006 §4.2).
   *
   * A RunState is the transient half — current step, live timers, scroll
   * position — and it legitimately dies with the tab. The Deposition is the
   * record, and it does not. Keeping the link here rather than putting a runId
   * on Deposition keeps the durable object free of a reference to something
   * that will not survive alongside it.
   */
  depositionId?: string;
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
  /**
   * A job whose progress is set by a real request rather than by the clock
   * (OF-BLD-012 §5.4). `tickJobs` leaves these alone; the fetch that started
   * one completes or fails it.
   */
  real?: boolean;
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

// ── Deposition (OF-BLD-006 §4) ─────────────────────────────────────────
//
// The inbound account of what actually happened, against a Runbook's outbound
// claim. This is the only ground truth the platform gets about its own
// predictions — nothing in the literature can tell you whether a yield model
// works — which is why a Deposition is a record rather than a session.

export type DepositionState = 'staged' | 'running' | 'closed';

/**
 * One value the operator reported that matched something in the runbook's
 * measurement schema.
 */
export interface DepositionEntry {
  id: string;
  /** The `Measure` this satisfies, from the runbook's schema. */
  measureId: string;
  stepId: string;
  at: string;
  value: number;
  unit: string;
  /**
   * Exactly what the operator said or typed, before anything parsed it.
   *
   * Never overwritten. "Four two" is 4.2 or 42 and the failure is silent, so
   * the parse has to stay auditable against the words that produced it.
   */
  raw: string;
  /**
   * Whether a person has confirmed the parsed number. Numbers entering the
   * schema get one confirmation beat; narrative does not (§4.4).
   */
  confirmed: boolean;
}

/**
 * Something the operator reported that fits no field — which is the whole
 * point. An unexpected result has no column waiting for it, by definition, and
 * a schema-first capture would discard exactly the observation worth having.
 */
export interface Observation {
  id: string;
  stepId: string;
  at: string;
  /** Free text, kept verbatim. The provenance of anything derived from it. */
  raw: string;
  /**
   * A later structured reading of `raw`, or null.
   *
   * Derived, never authoritative. `raw` is not replaced by it: a mis-reading
   * stays recoverable, and a better model in six months can re-derive from
   * source. This is OF-COR-001 Rule 1 applied one level below where it was
   * designed.
   */
  structured: string | null;
}

/**
 * Predicted beside observed, with the delta (OF-BLD-006 §5). The one thing in
 * this system that exists in no other tool.
 */
export interface Reconciliation {
  at: string;
  /**
   * 'refuted' is the valuable one — it is the only ground truth the system
   * gets about itself. 'inconclusive' is the honest one: deviations too large
   * for the comparison to mean anything, recorded rather than rounded into a
   * verdict, which is what keeps the hit rate real.
   */
  outcome: 'confirmed' | 'refuted' | 'inconclusive';
  deltas: {
    predictionId: string;
    predicted: number;
    observed: number;
    unit: string;
    pctDelta: number;
  }[];
  note: string;
}

/**
 * A measured value released into BioRepo by a reconciliation (§5).
 *
 * EVIDENCE, NEVER AN OVERRIDE. One result under one set of conditions must not
 * silently shift a global parameter: a titre of 7.4 g/L in one 2,000 L run
 * with two logged deviations is a fact about that run, not a correction to
 * every model that mentions titre. So this is a record with its conditions and
 * deviations attached, and it passes the same aggregation gate as everything
 * else rather than jumping the queue because it is first-party.
 *
 * It is a separate type from ExtractionRecord because that type is bound to
 * the corpus — a paper, a section, a verbatim quote — and a bench result has
 * none of those. It reuses the same `Provenance` union rather than inventing a
 * second confidence vocabulary.
 */
export interface MeasuredEvidence {
  id: string;
  depositionId: string;
  runbookId: string;
  /** The molecule this was measured for, when the runbook names one. */
  productId: string | null;
  /** The prediction it tests, so the claim and the result stay linked. */
  predictionId: string;
  label: string;
  value: number;
  unit: string;
  /** Always 'measured'. Present so the field reads the same as everywhere else. */
  provenance: Provenance;
  /** What it was true under. Without these the number is not reusable. */
  conditions: {
    protocolId: string;
    scale: number;
    strainId: string | null;
  };
  /** Verbatim deviations logged during the run that produced it. */
  deviations: string[];
  /** False when the operator never read the value back (§4.4). */
  confirmed: boolean;
  at: string;
}

export interface Deposition {
  id: string;
  runbookId: string;
  protocolId: string;
  /** Guild will populate this once people and permissions exist. */
  operatorId: string | null;
  startedAt: string;
  closedAt: string | null;
  state: DepositionState;
  entries: DepositionEntry[];
  observations: Observation[];
  reconciliation: Reconciliation | null;
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

// ── AnswerPlan (OF-BLD-007 §3) ─────────────────────────────────────────
//
// The only representation of an answer in the system. Mirrored exactly from
// `core/openferment_core/models.py`; `pnpm check:plan` fails the build if the
// two drift, because a shape that exists twice and is enforced once is a shape
// that is about to disagree with itself.
//
// A PLAN IS NOT A TRANSCRIPT. The scripted path this replaces replayed prose a
// human wrote, and the UI printed it. A plan is a set of claims, each a
// sentence with NO NUMBER IN IT plus the records it rests on. The browser
// renders every value from the cited record, never from the model's text.
// That is the whole mechanism of Rule 1 here: the model has no slot to put a
// quantity in, so it cannot originate one.

export type ClaimSupport = 'direct' | 'inferred' | 'unsupported';

export interface Claim {
  id: string;
  /** Prose WITHOUT numbers. The interface renders the value from the record. */
  text: string;
  /** Must resolve against RECORDS. A claim citing a ghost is dropped, not repaired. */
  recordIds: string[];
  /** Must resolve against PAPERS. */
  paperIds: string[];
  support: ClaimSupport;
  /**
   * The WEAKEST provenance across the cited records, computed server-side and
   * never chosen by the model — a model that grades its own evidence grades it
   * generously. A claim is worth exactly as much as its worst citation.
   */
  provenance: Provenance;
}

export interface AnswerPlanUsage {
  inputTokens: number;
  outputTokens: number;
  /** Computed from the response's own token counts, not estimated. */
  costUsd: number;
}

export interface AnswerPlan {
  question: string;
  claims: Claim[];
  /** What evidence is missing. Naming an absence is a useful answer. */
  gaps: string[];
  /** Set when the corpus cannot support an answer, and says what is missing. */
  declined: string | null;
  usage: AnswerPlanUsage;
  /** How many claims the validator dropped (§5). Never repaired — dropped and counted. */
  rejected: number;
  /** Why each was dropped. A rising rate is the signal that the prompt has drifted. */
  rejectionReasons: string[];
}

// ── Intake (OF-BLD-012 §2.5, §5) ────────────────────────────────────────
//
// Mirrors of the Pydantic models in core/openferment_core/models.py; `pnpm
// check:plan` fails the build if a field exists on one side only. The service's
// `FetchedSection` is the same shape as `PaperSection` above and is compared
// against it.

/** What the JATS <license> element said, stored beside every fetched text. */
export interface FetchLicense {
  href: string | null;
  text: string | null;
}

export type FetchStatus = Extract<IngestStatus, 'complete' | 'failed:fetch' | 'failed:parse'>;

/**
 * What one fetch produced. A failure is a result with a reason rather than an
 * error — the ingest board already renders both failure states.
 */
export interface FetchResult {
  paperId: string;
  pmcid: string | null;
  status: FetchStatus;
  reason: string | null;
  fetchedAt: string;
  license: FetchLicense | null;
  sections: PaperSection[];
  /** Size of the XML as received. */
  bytes: number;
}

/** One row of GET /api/intake/status. */
export interface IntakeStatus {
  paperId: string;
  pmcid: string | null;
  ingest: IngestStatus;
  textSource: 'full-text' | 'curation-note';
  sections: number;
  tables: number;
  license: string | null;
  fetchedAt: string | null;
  reason: string | null;
}

/**
 * What the overlay says about one paper (§2.1). A failed fetch is here too,
 * with its reason and no sections — the store keeps the seed's curation note
 * for it and the ingest board says why it halted.
 */
export interface OverlayPaper {
  ingest: IngestStatus;
  textSource: 'full-text' | 'curation-note';
  sections: PaperSection[];
  license: string | null;
  fetchedAt: string | null;
  reason: string | null;
}

/**
 * GET /api/biorepo/overlay. Applied over the seed in one action at load when
 * the service answers; with the service down the app is exactly the seed.
 * `records`, `candidates` and `runs` are typed loosely until §7 and §6 define
 * their shapes — the field names are fixed now so the shape does not move.
 */
export interface Overlay {
  papers: Record<string, OverlayPaper>;
  records: Record<string, ReviewDecision>;
  /**
   * The extractor's current candidates, or null for "not supplied"
   * (OF-BLD-012.1 F3). The service always sends the full list, so an EMPTY
   * list means it produced nothing and the store drops what it had. Only
   * null keeps it. Before F3 the two were the same value, and a cleared
   * cache on the service left stale candidates on screen until a reload.
   */
  candidates: Candidate[] | null;
  runs: RunOutput[] | null;
}

/**
 * An extraction the anchoring rules accepted (OF-BLD-012 §2.4), before any
 * human has looked at it. ExtractionRecord minus the four fields review owns
 * — audit, gold, corrected, reviewer — listed out because `check:plan` reads
 * field names as text. `CandidateMirror` below makes the compiler hold this to
 * ExtractionRecord: add a field to one and not the other and the build fails.
 */
export interface Candidate {
  id: string;
  paperId: string;
  sectionId: string;
  quote: string;
  field: FieldId;
  value: number | string;
  unit: string;
  si: { value: number; unit: string };
  confidence: number;
  status: RecordStatus;
  provenance: Provenance;
  organism?: string;
  componentTag?: string;
  goldOnly?: boolean;
  extractorRun?: ExtractorRun;
  rejectReason?: string;
  isPrimary: boolean;
  citesRecordId?: string;
  method?: AnalysisMethod;
  numbering?: NumberingConvention;
  curationRef?: string;
  range?: Range;
  comparativeBaseline?: string;
  negativeResult?: boolean;
  valueBasis?: ValueBasis;
}

/**
 * What one extraction produced (OF-BLD-012 §6.1, §6.3). `candidates` are the
 * survivors of anchoring; `audit` is the event they all share, kept beside
 * them because a Candidate carries none; `rejectionReasons` is keyed by
 * anchoring rule — field, section, quote, value, unit, range, method.
 */
/**
 * core/data/biorepo.json (OF-BLD-012 §2.2, §7.1) — the one data file the
 * increment commits: human decisions keyed by record id, and the candidates
 * those decisions were about (accepted ones are new records; rejected ones
 * are Witness's false positives), copied here because candidates/ is not
 * committed. Written by `biorepo.write` alone.
 */
export interface BioRepo {
  version: 1;
  decisions: Record<string, ReviewDecision>;
  records: Candidate[];
}

/**
 * A candidate anchoring refused (OF-BLD-012 §2.4), kept beside the survivors
 * so the run can be scored honestly (§6.2): one whose value agreed with the
 * seed and whose quote failed is a span_error in Witness. Never a record.
 */
export interface DroppedCandidate {
  paperId: string;
  sectionId: string;
  field: string;
  value: number | string | null;
  unit: string;
  rule: string;
  detail: string;
}

export interface ExtractResponse {
  paperId: string;
  run: ExtractorRun;
  extractedAt: string;
  candidates: Candidate[];
  audit: AuditEvent[];
  rejected: number;
  rejectionReasons: Record<string, number>;
  rejectionDetails: string[];
  dropped: DroppedCandidate[];
  usage: AnswerPlanUsage;
  notes: string[];
  /**
   * How many model calls this extraction took (OF-BLD-012.1 F8). One is the
   * ordinary case; more means the response hit the token limit and the paper
   * was halved and asked again rather than discarded.
   */
  calls: number;
  /**
   * The sections that still would not fit after splitting, and so were not
   * extracted. The honest gap in this paper's extraction, rather than the
   * silent zero Witness used to score.
   */
  truncatedSections: string[];
}

// `absentFromRun` joins the four review fields here: it is the browser's note
// about the extractor's current run (OF-BLD-012.1 F3), recomputed on every
// overlay, and a Candidate the service just sent is by definition in it.
type RecordMinusReview = Omit<
  ExtractionRecord,
  'audit' | 'gold' | 'corrected' | 'reviewer' | 'absentFromRun' | 'original'
>;
/**
 * `true` when A and B declare exactly the same keys, `never` otherwise.
 * Assignability alone is not enough here: an extra OPTIONAL property is
 * assignable in both directions, so a mirror built on assignability lets a
 * field added to one side slip past — which is what the first version of this
 * did, and what a negative test caught.
 */
type SameKeys<A, B> = [keyof A] extends [keyof B] ? ([keyof B] extends [keyof A] ? true : never) : never;
/** Compile-time proof that Candidate is ExtractionRecord minus review: same keys, assignable both ways. */
export const CandidateMirror: [
  SameKeys<Candidate, RecordMinusReview>,
  (c: Candidate) => RecordMinusReview,
  (r: RecordMinusReview) => Candidate,
] = [true, (c) => c, (r) => r];

/**
 * What a reviewer decided about one record (OF-BLD-012 §7.1). The first six
 * fields are exactly DurableReviewDecision in src/lib/durable.ts — the shape
 * the Durable tier already persists — so a decision made offline and one
 * posted to the service are the same object. The rest say which record, when,
 * and, for a promotion that re-anchors a curated quote to the paper's own
 * words, the replacement span.
 */
export interface ReviewDecision {
  status: RecordStatus;
  provenance: Provenance;
  gold?: { value: number | string; unit: string };
  corrected?: { value: number; unit: string };
  rejectReason?: string;
  reviewer?: string;
  recordId: string;
  at: string;
  quote?: string;
  sectionId?: string;
}
