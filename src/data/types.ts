// openFerment Sim — canonical entity types (OF-DES-001 §15)

export type Provenance = 'gold' | 'verified' | 'unverified' | 'user' | 'demo';

export type FieldId =
  | 'growth_rate_mu'
  | 'doubling_time'
  | 'yield_biomass_substrate'
  | 'final_biomass_density'
  | 'protein_content'
  | 'product_titer'
  | 'volumetric_productivity'
  | 'specific_productivity'
  | 'od_dcw_factor'
  | 'medium_component_conc'
  | 'ph_setpoint'
  | 'temperature'
  | 'light_intensity'
  | 'co2_enrichment'
  | 'harvest_recovery'
  | 'disruption_efficiency';

export interface ParameterDef {
  id: FieldId;
  name: string;
  definition: string;
  canonicalUnit: string;
  range: [number, number];
  notes: string;
}

export type IngestStage = 'fetch' | 'parse' | 'chunk' | 'embed' | 'extract';
export type IngestStatus =
  | 'complete'
  | `stage:${IngestStage}`
  | 'failed:parse'
  | 'shelf';

export interface PaperSection {
  id: string;
  heading: string;
  text: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  venue: string;
  organisms: string[];
  topics: string[];
  abstract: string;
  sections: PaperSection[];
  ingest: IngestStatus;
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
  value: number;
  unit: string;
  si: { value: number; unit: string };
  confidence: number;
  status: RecordStatus;
  organism?: string;
  componentTag?: string;
  gold?: { value: number; unit: string };
  goldOnly?: boolean;
  extractorRun: ExtractorRun;
  rejectReason?: string;
  corrected?: { value: number; unit: string };
  reviewer?: string;
  audit: AuditEvent[];
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
  key: string;
  label: string;
  unit: string;
  values: number[];
  sourceRecordId?: string;
}

export interface ScenarioAssumption {
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
