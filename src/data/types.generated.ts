/* eslint-disable */
/**
 * GENERATED — do not edit.
 *
 * Source of truth: the Pydantic models in `packages/core/openferment_core/schema`.
 * Regenerate with `pnpm gen:types`.
 *
 * Editing this file is the failure the migration exists to prevent: a schema
 * maintained in two languages is two schemas, and they diverge on the day
 * nobody is looking. Change the Python and run the generator.
 *
 * Two types are NOT here and cannot be: `CostModel` carries a function and
 * `ResultGrid` carries `Float64Array`. Neither is a data shape and neither
 * survives JSON Schema. They are hand-written in `types.ts`, which re-exports
 * everything below.
 */

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
 *
 * 'unsourced' is a defect class, not a value class. It marks a quantity that
 * reached the interface with no provenance record behind it — the interface
 * expression of Rule 1 of the agent contract, that no quantity may come from
 * model weights. It is unreachable in the seeded build, `check:seed` enforces
 * that no record carries it, and `Tick` shouts in the console when one renders.
 * It is kept reachable on one Settings route so a reviewer can see what the
 * system does when the rule is broken rather than be asked to believe it cannot
 * be.
 */
export type Provenance =
  | 'gold'
  | 'verified'
  | 'curated'
  | 'unverified'
  | 'user'
  | 'industry-estimate'
  | 'demo'
  | 'unsourced';
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
export type AssumptionBasis = BasisRecord | BasisModel | BasisUnsourced;
export type ChatMessage =
  UserMessage | PlanMessage | ToolMessage | AnswerMessage | ClarifyMessage | SystemMessage;
/**
 * Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families.
 */
export type FieldId =
  | 'expression_pct_tsp'
  | 'titer_intracellular'
  | 'titer_secreted'
  | 'secreted_fraction'
  | 'fold_improvement'
  | 'transformation_efficiency'
  | 'time_to_colony'
  | 'phosphate_count'
  | 'phosphorylation_degree'
  | 'phospho_site_position'
  | 'glycan_species'
  | 'kinase_identity'
  | 'micelle_diameter'
  | 'micellar_fraction'
  | 'gelation_ph'
  | 'calcium_binding'
  | 'melt_stretch_length'
  | 'growth_rate_mu'
  | 'final_biomass_density'
  | 'volumetric_productivity'
  | 'medium_component_conc'
  | 'disruption_protein_yield'
  | 'disruption_energy'
  | 'minimum_selling_price';
export type DetectedBy = 'balance' | 'flux' | 'reactor' | 'ontology' | 'manual';
export type ContradictionKind = 'balance' | 'specification' | 'scale' | 'direct';
export type ContradictionStatus = 'open' | 'explained' | 'resolved';
/**
 * Which corpus thread an entry belongs to (OF-COR-001 §1).
 */
export type CorpusThread =
  'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' | 'J' | 'K' | 'L' | 'M' | 'N' | 'O';
export type CostLine = 'capex' | 'media' | 'utilities' | 'labor' | 'downstream' | 'other';
/**
 * A tier either ran or it did not. `absent` is a first-class state, not a
 * failure and not a pass: T1 needs a genome-scale model and T2 a reactor model,
 * and neither exists in this build. Rendering an absent tier as passed would
 * claim the biology was checked when only the economics were modelled.
 */
export type TierState = 'passed' | 'failed' | 'absent';
export type Tier = 'T0' | 'T1' | 'T2' | 'T3';
/**
 * Which live component a lesson block mounts.
 *
 * A closed set: a lesson embeds the real interface element it is teaching, so
 * every member here corresponds to a component the Learn renderer knows how to
 * mount. Adding a value without adding the component leaves a lesson with a
 * hole in it.
 */
export type EmbedKind =
  | 'chip-demo'
  | 'record-card'
  | 'unit-playground'
  | 'mini-queue'
  | 'metrics-tiles'
  | 'strip-plot'
  | 'protocol-card'
  | 'ask-prompt'
  | 'scenario-widget';
/**
 * Where a value came from, orthogonal to how far it has been verified.
 * `Provenance` answers "how much has this been checked?";
 * `EvidenceClass` answers "what kind of thing produced it?".
 *
 * Both are needed once the system holds predictions and bench results
 * alongside literature: a `curated` prediction and a `curated` measurement
 * are the same verification state and completely different claims.
 *
 * Encoded as tick *geometry*, never as a second hue — the ambient-texture
 * property of the provenance palette depends on hue meaning one thing only.
 */
export type EvidenceClass = 'literature' | 'patent' | 'computed' | 'experiment' | 'correction';
/**
 * What kind of thing produced this value. Every seeded record is 'literature'; the field is required so that a prediction written by geneOS or a measurement deposited by openLab cannot enter the store wearing the same face as a paper. `check:seed` enforces its presence.
 */
export type EvidenceClass1 = 'literature' | 'patent' | 'computed' | 'experiment' | 'correction';
/**
 * Absent for curated records — they did not come from an extractor run.
 */
export type ExtractorRun = 'v0.3' | 'v0.4' | 'v0.4r';
/**
 * How the value was measured. Mandatory for PTM and functional fields (OF-COR-001 §17 Rule 1) — 'undetermined' is a legitimate answer and means the analysis was never done, not that the result was negative.
 */
export type AnalysisMethod1 =
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
/**
 * Required on phospho_site_position — mature and precursor differ by 15.
 */
export type NumberingConvention = 'precursor' | 'mature';
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
 *
 * 'unsourced' is a defect class, not a value class. It marks a quantity that
 * reached the interface with no provenance record behind it — the interface
 * expression of Rule 1 of the agent contract, that no quantity may come from
 * model weights. It is unreachable in the seeded build, `check:seed` enforces
 * that no record carries it, and `Tick` shouts in the console when one renders.
 * It is kept reachable on one Settings route so a reviewer can see what the
 * system does when the rule is broken rather than be asked to believe it cannot
 * be.
 */
export type Provenance1 =
  | 'gold'
  | 'verified'
  | 'curated'
  | 'unverified'
  | 'user'
  | 'industry-estimate'
  | 'demo'
  | 'unsourced';
export type RecordStatus = 'unverified' | 'verified' | 'rejected';
export type ExtractorRun1 = 'v0.3' | 'v0.4' | 'v0.4r';
export type IngestStage = 'fetch' | 'parse' | 'chunk' | 'embed' | 'extract';
/**
 * Where a corpus entry is in the ingest pipeline.
 *
 * The TypeScript writes the five in-progress members as a template literal,
 * `` `stage:${IngestStage}` ``, which is a genuinely nicer way to say it and a
 * thing JSON Schema cannot express — a schema can enumerate strings but cannot
 * describe a string built from another enum. They are therefore written out
 * here. If `IngestStage` ever grows a member, this enum has to grow the
 * matching `stage:` member by hand, and there is a test that fails if it does
 * not.
 */
export type IngestStatus =
  | 'complete'
  | 'catalogued'
  | 'stage:fetch'
  | 'stage:parse'
  | 'stage:chunk'
  | 'stage:embed'
  | 'stage:extract'
  | 'failed:fetch'
  | 'failed:parse'
  | 'shelf';
export type JobKind = 'ingest' | 'extraction' | 'simulation' | 'run';
export type JobStatus = 'running' | 'done' | 'failed';
export type LessonBlock = ProseBlock | EmbedBlock;
export type ScalingClass = 'per_batch_volume' | 'fixed' | 'per_unit_biomass';
/**
 * Residue-numbering convention (OF-COR-001 §19, first trap).
 */
export type NumberingConvention1 = 'precursor' | 'mature';
export type SourceType =
  'journal-article' | 'review' | 'thesis' | 'patent' | 'book' | 'industry-report' | 'preprint';
export type ParameterFamily = 'expression' | 'ptm' | 'functional' | 'cultivation' | 'downstream';
export type PatentStatus = 'pending' | 'granted' | 'lapsed' | 'revoked';
export type ProtocolCategory =
  'media' | 'culture' | 'analytics' | 'harvest' | 'fermentation' | 'sop';
export type PublicationStatus =
  ('draft' | 'counsel-review' | 'hold' | 'publish' | 'published') | EmbargoStatus;
export type RefereeStatus = UncheckedStatus | ConsistentStatus | ContradictedStatus;
/**
 * How one gold record fared in an extractor run.
 *
 * Named `RunOutcomeKind` rather than `RunOutcome` because that name belongs
 * to a different type in `protocol.py`.
 */
export type RunOutcomeKind = 'match' | 'value_mismatch' | 'unit_error' | 'span_error' | 'miss';
/**
 * Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families.
 */
export type FieldId1 =
  | 'expression_pct_tsp'
  | 'titer_intracellular'
  | 'titer_secreted'
  | 'secreted_fraction'
  | 'fold_improvement'
  | 'transformation_efficiency'
  | 'time_to_colony'
  | 'phosphate_count'
  | 'phosphorylation_degree'
  | 'phospho_site_position'
  | 'glycan_species'
  | 'kinase_identity'
  | 'micelle_diameter'
  | 'micellar_fraction'
  | 'gelation_ph'
  | 'calcium_binding'
  | 'melt_stretch_length'
  | 'growth_rate_mu'
  | 'final_biomass_density'
  | 'volumetric_productivity'
  | 'medium_component_conc'
  | 'disruption_protein_yield'
  | 'disruption_energy'
  | 'minimum_selling_price';
/**
 * Parameter ontology v1 (OF-COR-001 §17) — 24 fields in five families.
 */
export type FieldId2 =
  | 'expression_pct_tsp'
  | 'titer_intracellular'
  | 'titer_secreted'
  | 'secreted_fraction'
  | 'fold_improvement'
  | 'transformation_efficiency'
  | 'time_to_colony'
  | 'phosphate_count'
  | 'phosphorylation_degree'
  | 'phospho_site_position'
  | 'glycan_species'
  | 'kinase_identity'
  | 'micelle_diameter'
  | 'micellar_fraction'
  | 'gelation_ph'
  | 'calcium_binding'
  | 'melt_stretch_length'
  | 'growth_rate_mu'
  | 'final_biomass_density'
  | 'volumetric_productivity'
  | 'medium_component_conc'
  | 'disruption_protein_yield'
  | 'disruption_energy'
  | 'minimum_selling_price';

/**
 * GENERATED from the Pydantic models in packages/core/openferment_core/schema. Do not edit. Edit the models and re-run `pnpm gen:types`.
 */
export interface GeneratedSchemaIndex {
  ActivityEvent?: ActivityEvent;
  Aggregate?: Aggregate;
  AggregateStratum?: AggregateStratum;
  AnalysisMethod?: AnalysisMethod;
  AnswerMessage?: AnswerMessage;
  AssumptionBasis?: AssumptionBasis;
  AuditEvent?: AuditEvent;
  BaseBatch?: BaseBatch;
  BasisModel?: BasisModel;
  BasisRecord?: BasisRecord;
  BasisUnsourced?: BasisUnsourced;
  ChatFlow?: ChatFlow;
  ChatMessage?: ChatMessage;
  ChatRetrievalHit?: ChatRetrievalHit;
  ChatSession?: ChatSession;
  ChatToolCall?: ChatToolCall;
  CheckpointQuestion?: CheckpointQuestion;
  ClaimBound?: ClaimBound;
  ClaimScope?: ClaimScope;
  ClarifyMessage?: ClarifyMessage;
  ClarifyOption?: ClarifyOption;
  ClarifyPrompt?: ClarifyPrompt;
  Collection?: Collection;
  ConsistentStatus?: ConsistentStatus;
  ConstraintCheck?: ConstraintCheck;
  ContradictedStatus?: ContradictedStatus;
  Contradiction?: Contradiction;
  ContradictionKind?: ContradictionKind;
  ContradictionStatus?: ContradictionStatus;
  CorpusThread?: CorpusThread;
  CorrectedValue?: CorrectedValue;
  CostLine?: CostLine;
  CoverageDispute?: CoverageDispute;
  CuratorNote?: CuratorNote;
  DecisiveMeasurement?: DecisiveMeasurement;
  DesignRecord?: DesignRecord;
  DetectedBy?: DetectedBy;
  Deviation?: Deviation;
  EmbargoStatus?: EmbargoStatus;
  EmbedBlock?: EmbedBlock;
  EmbedKind?: EmbedKind;
  EstimatedMinutes?: EstimatedMinutes;
  EvidenceClass?: EvidenceClass;
  ExcludedRecord?: ExcludedRecord;
  ExtractedValue?: ExtractedValue;
  ExtractionRecord?: ExtractionRecord;
  ExtractorRun?: ExtractorRun1;
  FalsePositive?: FalsePositive;
  FieldId?: FieldId;
  GoldValue?: GoldValue;
  GridPointResult?: GridPointResult;
  IngestStage?: IngestStage;
  IngestStatus?: IngestStatus;
  Job?: Job;
  JobKind?: JobKind;
  JobStage?: JobStage;
  JobStatus?: JobStatus;
  LearnModule?: LearnModule;
  Lesson?: Lesson;
  LessonBlock?: LessonBlock;
  MSPDistribution?: MSPDistribution1;
  Material?: Material;
  NumberingConvention?: NumberingConvention1;
  NumericAnswer?: NumericAnswer1;
  Paper?: Paper;
  PaperSection?: PaperSection;
  ParameterDef?: ParameterDef;
  ParameterFamily?: ParameterFamily;
  ParameterView?: ParameterView;
  Patent?: Patent;
  PatentStatus?: PatentStatus;
  PlanMessage?: PlanMessage;
  ProseBlock?: ProseBlock;
  Protocol?: Protocol;
  ProtocolCategory?: ProtocolCategory;
  ProtocolReference?: ProtocolReference;
  ProtocolVersion?: ProtocolVersion;
  Provenance?: Provenance;
  PublicationStatus?: PublicationStatus;
  RecordStatus?: RecordStatus;
  RefereeStatus?: RefereeStatus;
  RefuseConversion?: RefuseConversion;
  ResultField?: ResultField;
  RunOutcome?: RunOutcome;
  RunOutcomeKind?: RunOutcomeKind;
  RunOutput?: RunOutput;
  RunResult?: RunResult;
  RunState?: RunState;
  SIValue?: SIValue;
  ScalingClass?: ScalingClass;
  Scenario?: Scenario;
  ScenarioAssumption?: ScenarioAssumption;
  ScenarioDim?: ScenarioDim;
  ScopeHit?: ScopeHit;
  SensitivityEntry?: SensitivityEntry;
  SensitivityRow?: SensitivityRow;
  SessionScope?: SessionScope;
  SourceType?: SourceType;
  Step?: Step;
  StockSolution?: StockSolution;
  Strain?: Strain;
  SystemMessage?: SystemMessage;
  Tier?: Tier;
  TierResult?: TierResult;
  TierState?: TierState;
  TierValue?: TierValue;
  TimerState?: TimerState;
  ToolMessage?: ToolMessage;
  UncheckedStatus?: UncheckedStatus;
  UserMessage?: UserMessage;
  ValueRange?: ValueRange1;
}
export interface ActivityEvent {
  at: string;
  href?: string;
  icon: string;
  provenance: Provenance;
  text: string;
}
/**
 * Deliberately not a Bayesian posterior. With 134 curated records and none
 * verified, a hierarchical fit would be false precision. Median-of-primary with
 * a visible interquartile range is honest at this corpus size, and this shape
 * lets a posterior replace the internals later without any screen changing.
 */
export interface Aggregate {
  max: number;
  median: number;
  /**
   * Named, so a screen can say how the number was produced.
   */
  method: string;
  min: number;
  n: number;
  nPrimary: number;
  p25: number;
  p75: number;
  /**
   * Grouping actually used — by organism, by method, by year.
   */
  strata: AggregateStratum[];
  unit: string;
}
/**
 * One grouping in `Aggregate.strata` — by organism, by method, by year.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface AggregateStratum {
  key: string;
  label: string;
  median: number;
  n: number;
}
/**
 * The answer arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface AnswerMessage {
  flowId?: string;
  followups: string[];
  id: string;
  kind: 'answer';
  md: string;
  streaming: boolean;
}
/**
 * Bound to a Ledger record. The value must equal that record's SI value.
 */
export interface BasisRecord {
  kind: 'record';
  recordId: string;
}
/**
 * A deliberate modeling choice, or a literature value the ontology has no
 * field to hold. Legitimate, but must declare itself in writing.
 */
export interface BasisModel {
  justification: string;
  kind: 'model';
}
/**
 * DEFECT. A number with no record and no declared justification.
 */
export interface BasisUnsourced {
  kind: 'unsourced';
}
export interface AuditEvent {
  action: string;
  at: string;
  from?: unknown;
  to?: unknown;
  who: string;
}
/**
 * The batch size every material amount in this version is stated at.
 *
 * Inline in the TypeScript (`baseBatch: { value: number; unit: string; label:
 * string }`); named here because Pydantic has no anonymous model.
 */
export interface BaseBatch {
  label: string;
  unit: string;
  value: number;
}
export interface ChatFlow {
  /**
   * chips as [[ex-0112]] / [[SP-004]]
   */
  answerMd: string;
  clarify?: ClarifyPrompt;
  /**
   * may be "flow:F2|label"
   */
  followups: string[];
  id: string;
  plan: string[];
  toolCalls: ChatToolCall[];
  triggers: string[];
}
/**
 * The clarifying question a flow asks before it will answer.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ClarifyPrompt {
  options: ClarifyOption[];
  question: string;
}
/**
 * One branch a clarifying question can send the conversation down.
 *
 * Inline in the TypeScript — shared by `ChatFlow.clarify` and the `clarify`
 * arm of `ChatMessage` — and named here because Pydantic has no anonymous
 * model.
 */
export interface ClarifyOption {
  flowId: string;
  label: string;
}
export interface ChatToolCall {
  args: {
    [k: string]: unknown;
  };
  /**
   * Milliseconds.
   */
  durationMs: number;
  name: string;
  retrieval?: ChatRetrievalHit[];
}
export interface ChatRetrievalHit {
  paperId: string;
  score: number;
  sectionId: string;
  snippet: string;
}
/**
 * The user arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface UserMessage {
  id: string;
  kind: 'user';
  text: string;
}
/**
 * The plan arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface PlanMessage {
  collapsed: boolean;
  done: number;
  id: string;
  kind: 'plan';
  steps: string[];
}
/**
 * The tool arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ToolMessage {
  call: ChatToolCall;
  expanded: boolean;
  id: string;
  kind: 'tool';
}
/**
 * The clarify arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ClarifyMessage {
  id: string;
  kind: 'clarify';
  options: ClarifyOption[];
  question: string;
}
/**
 * The system arm of `ChatMessage`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface SystemMessage {
  id: string;
  kind: 'system';
  retry?: boolean;
  text: string;
}
export interface ChatSession {
  id: string;
  messages: (
    UserMessage | PlanMessage | ToolMessage | AnswerMessage | ClarifyMessage | SystemMessage
  )[];
  pinned: ChatRetrievalHit[];
  scope?: SessionScope;
  startedAt: string;
  title: string;
}
/**
 * What a chat session is scoped to — one paper, or a collection of them.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface SessionScope {
  id: string;
  kind: 'paper' | 'collection';
  label: string;
}
/**
 * One end-of-lesson check.
 *
 * Multiple-choice questions carry `options` and `answerIndex`; numeric ones
 * carry `answer`. Both shapes live in one interface in the TypeScript, so both
 * sets of fields are optional here and the `kind` says which apply.
 */
export interface CheckpointQuestion {
  answer?: NumericAnswer;
  /**
   * Index of the correct entry in `options`. Present when `kind` is 'mc'.
   */
  answerIndex?: number;
  /**
   * Evidence chip backing the answer, e.g. 'ex-0112' or 'SP-004' — the lesson cites the corpus for its own claims on the same terms it asks the reader to.
   */
  evidenceChip?: string;
  explanation: string;
  id: string;
  kind: 'mc' | 'numeric';
  /**
   * Multiple-choice options. Present when `kind` is 'mc'.
   */
  options?: string[];
  prompt: string;
}
/**
 * Expected value, unit and tolerance. Present when `kind` is 'numeric'.
 */
export interface NumericAnswer {
  tolerancePct: number;
  unit: string;
  value: number;
}
/**
 * One bound in `ClaimScope.bounds`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ClaimBound {
  field: FieldId;
  op: '<' | '<=' | '>' | '>=' | 'in' | 'eq';
  unit?: string;
  value: number | [number, number] | string;
}
export interface ClaimScope {
  /**
   * Claim scope expressed in the SAME ontology as the literature. This comparability is the entire value of Parchment: it is what lets a Ledger record be tested against a claim instead of read beside it.
   */
  bounds: ClaimBound[];
  independent: boolean;
  number: number;
  /**
   * True when the parse is uncertain. Never render a shaky parse as confident.
   */
  parseUncertain?: boolean;
  rawText: string;
}
/**
 * A reader-assembled set of corpus papers.
 */
export interface Collection {
  id: string;
  name: string;
  paperIds: string[];
}
export interface ConsistentStatus {
  checks: string[];
  state: 'consistent';
}
/**
 * The machine form of a contradiction, for the referee panel.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ConstraintCheck {
  expression: string;
  residual: number;
  tolerance: number;
  unit: string;
}
export interface ContradictedStatus {
  contradictionIds: string[];
  state: 'contradicted';
}
/**
 * A set of entries that cannot all be true. The referee flags the *set*;
 * it does not need to identify which member is wrong to be useful.
 */
export interface Contradiction {
  constraint: ConstraintCheck1;
  detectedBy: DetectedBy;
  id: string;
  kind: ContradictionKind;
  /**
   * Required when status leaves 'open'. Displayed permanently.
   */
  note?: string;
  /**
   * Every participating record. Minimum two.
   */
  recordIds: string[];
  /**
   * One plain sentence a non-specialist can read. Rendered as the headline.
   */
  statement: string;
  status: ContradictionStatus;
}
/**
 * Machine form for the referee panel.
 */
export interface ConstraintCheck1 {
  expression: string;
  residual: number;
  tolerance: number;
  unit: string;
}
/**
 * `ExtractionRecord.corrected` — the reviewer's replacement value.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. See `GoldValue` on why this one's `value` is numeric only.
 */
export interface CorrectedValue {
  unit: string;
  value: number;
}
/**
 * A reader filed "something's missing" against a source (OF-FE-003 §8.4).
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface CoverageDispute {
  at: string;
  note: string;
}
export interface CuratorNote {
  at: string;
  text: string;
  who: string;
}
/**
 * The single uncertainty this protocol exists to resolve (OF-FE-003 §4.5).
 *
 * This is the return leg of the experiment loop: a sensitivity tornado names
 * the parameter whose uncertainty moves the answer most, and a protocol that
 * declares itself the measurement for that parameter is what turns the naming
 * into work someone can do. Without it the loop points at a parameter page and
 * stops.
 *
 * Inline in the TypeScript (`decisive?: { ... }`); named here because Pydantic
 * has no anonymous model.
 */
export interface DecisiveMeasurement {
  /**
   * Plain sentence: what is not known, and why it matters here.
   */
  currentUncertainty: string;
  field: FieldId;
  /**
   * What a result would settle — "if below X, design D2 wins".
   */
  whatWouldChange: string;
}
export interface DesignRecord {
  config: {
    [k: string]: number;
  };
  /**
   * Exact records consumed — the basis for staleness.
   */
  consumedRecordIds: string[];
  id: string;
  label: string;
  publication: ('draft' | 'counsel-review' | 'hold' | 'publish' | 'published') | EmbargoStatus;
  scenarioId: string;
  /**
   * 'clear' means Parchment has not evaluated this design, NOT that it is unencumbered. Parchment holds no parsed claim bounds, so it cannot decide; the word must never imply it did.
   */
  scope: 'clear' | 'adjacent' | 'claimed';
  scopeEvaluated: boolean;
  scopeHits: ScopeHit[];
  tiers: TierResult[];
}
/**
 * The one object member of `PublicationStatus`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. An embargo is the only publication state that carries data — the date
 * it lifts — which is why it alone is an object.
 */
export interface EmbargoStatus {
  kind: 'embargo';
  until: string;
}
/**
 * One patent claim this design falls within, in `DesignRecord.scopeHits`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ScopeHit {
  claim: number;
  patentId: string;
}
export interface TierResult {
  /**
   * Why the tier is absent, when it is. Shown in place of a result.
   */
  absentReason?: string;
  /**
   * The constraint that bound the result — the most useful string on the page.
   */
  bindingConstraint: string;
  engineVersion: string;
  msp?: MSPDistribution;
  /**
   * T3 only, sorted by |rho| descending. Drives the experiment loop.
   */
  sensitivity?: SensitivityEntry[];
  state: TierState;
  tier: Tier;
  values: {
    [k: string]: TierValue;
  };
}
/**
 * T3 only. Never a bare point estimate presented as a distribution.
 */
export interface MSPDistribution {
  median: number;
  p05: number;
  p95: number;
  unit: string;
}
/**
 * One row of `TierResult.sensitivity`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface SensitivityEntry {
  field?: FieldId;
  label: string;
  rho: number;
}
/**
 * One entry in `TierResult.values` — a number with the unit it was computed in.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface TierValue {
  unit: string;
  value: number;
}
export interface Deviation {
  at: string;
  stepId: string;
  text: string;
}
/**
 * The embed arm of `LessonBlock`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface EmbedBlock {
  /**
   * Component-specific argument, e.g. the record or protocol id the embed should show. Absent where the embed needs no target.
   */
  arg?: string;
  embed: EmbedKind;
  kind: 'embed';
}
/**
 * Hands-on and wall-clock time for a version.
 *
 * Inline in the TypeScript (`estMinutes: { active: number; total: number }`);
 * named here because Pydantic has no anonymous model. These are minutes and
 * may be fractional, so float rather than int.
 */
export interface EstimatedMinutes {
  active: number;
  total: number;
}
/**
 * One record held out of the aggregate, with the reason.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ExcludedRecord {
  reason: string;
  recordId: string;
}
/**
 * What an extractor actually produced for a record.
 *
 * Inline in the TypeScript, in both `RunResult.extracted` and
 * `FalsePositive.extracted`; named once here because Pydantic has no
 * anonymous model and the two shapes are identical.
 */
export interface ExtractedValue {
  unit: string;
  value: number;
}
export interface ExtractionRecord {
  audit: AuditEvent[];
  /**
   * When not primary, the record this one is quoting.
   */
  citesRecordId?: string;
  /**
   * For comparative claims ("12-fold higher than X"), the baseline.
   */
  comparativeBaseline?: string;
  componentTag?: string;
  confidence: number;
  corrected?: CorrectedValue;
  /**
   * Where in OF-COR-001 a 'curated' value was transcribed from, e.g. '§9 H4'.
   */
  curationRef?: string;
  evidenceClass: EvidenceClass1;
  extractorRun?: ExtractorRun;
  field: FieldId;
  gold?: GoldValue;
  goldOnly?: boolean;
  id: string;
  /**
   * False. This paper is quoting someone else's measurement (OF-COR-001 §19, fifth trap). Citation-of-a-citation is the most common false-independence error in literature aggregation: 15 mg/L appears in both C2 (the measurement) and C6 (a citation of it), and a strip plot that counts both overstates consensus. Aggregate statistics must filter on this.
   */
  isPrimary: boolean;
  method?: AnalysisMethod1;
  /**
   * Value is a reported negative/absent result, not a missing measurement.
   */
  negativeResult?: boolean;
  numbering?: NumberingConvention;
  organism?: string;
  paperId: string;
  provenance: Provenance1;
  quote: string;
  range?: ValueRange;
  rejectReason?: string;
  reviewer?: string;
  sectionId: string;
  si: SIValue;
  status: RecordStatus;
  unit: string;
  /**
   * Categorical fields (kinase_identity, glycan_species) carry a string.
   */
  value: number | string;
}
/**
 * `ExtractionRecord.gold` — the gold-set answer this record is scored
 * against.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. Its `value` is `number | string` where `CorrectedValue.value` is
 * `number` alone: a gold answer may be categorical (kinase_identity,
 * glycan_species) while a reviewer correction, as the TypeScript has it, may
 * not. That asymmetry is in the TypeScript and is reproduced, not fixed —
 * changing it here would put the two implementations out of agreement, which
 * is the exact failure this migration exists to prevent.
 */
export interface GoldValue {
  unit: string;
  value: number | string;
}
/**
 * A value the source states as a range rather than a point.
 */
export interface ValueRange {
  high: number;
  low: number;
}
/**
 * `ExtractionRecord.si` — the value in its canonical SI unit.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface SIValue {
  unit: string;
  value: number;
}
/**
 * A value an extractor produced that no gold record claims.
 *
 * Inline in the TypeScript as an element of `RunOutput.falsePositives`;
 * named here because Pydantic has no anonymous model.
 */
export interface FalsePositive {
  extracted: ExtractedValue;
  field: FieldId;
  id: string;
  note: string;
  paperId: string;
}
export interface GridPointResult {
  costLines: {
    capex: number;
    downstream: number;
    labor: number;
    media: number;
    other: number;
    utilities: number;
  };
  msp: number;
}
export interface Job {
  failReason?: string;
  href?: string;
  id: string;
  kind: JobKind;
  stageIndex: number;
  /**
   * 0-1 within current stage
   */
  stageProgress: number;
  stages: JobStage[];
  /**
   * Epoch milliseconds.
   */
  startedAt: number;
  status: JobStatus;
  title: string;
}
export interface JobStage {
  label: string;
  /**
   * Milliseconds.
   */
  ms: number;
}
export interface LearnModule {
  blurb: string;
  id: string;
  /**
   * Ordering index of the module within the Learn track.
   */
  index: number;
  lessons: Lesson[];
  /**
   * Planned lesson headings for a module whose lessons are not written yet. An empty `lessons` list with an outline is a stated gap, not a defect.
   */
  outline?: string[];
  title: string;
}
export interface Lesson {
  blocks: (ProseBlock | EmbedBlock)[];
  checkpoint: CheckpointQuestion[];
  id: string;
  /**
   * Estimated reading time in whole minutes.
   */
  minutes: number;
  title: string;
}
/**
 * The prose arm of `LessonBlock`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ProseBlock {
  kind: 'prose';
  md: string;
}
/**
 * The minimum selling price as a distribution, in `TierResult.msp`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface MSPDistribution1 {
  median: number;
  p05: number;
  p95: number;
  unit: string;
}
export interface Material {
  amount: number;
  name: string;
  /**
   * The rounding INCREMENT the scaled amount is snapped to, not a count of decimal places: 0.05 means 'to the nearest 0.05 g', and the corpus uses 0.001 through 0.5. `roundToPrecision` in src/engine/units.ts is what consumes it, so that a scaled recipe stays pipettable at the bench rather than asking for 3.847 g.
   */
  precision: number;
  scaling: ScalingClass;
  sourceRecordId?: string;
  stock?: StockSolution;
  unit: string;
}
/**
 * The stock a material is made up from, where it is not weighed out neat.
 *
 * Inline in the TypeScript (`stock?: { conc: number; unit: string }`); named
 * here because Pydantic has no anonymous model.
 */
export interface StockSolution {
  conc: number;
  unit: string;
}
/**
 * The expected answer to a `kind: 'numeric'` checkpoint question.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. The tolerance is carried with the answer rather than applied globally
 * because a unit-conversion question and an order-of-magnitude question are not
 * marked to the same precision.
 */
export interface NumericAnswer1 {
  tolerancePct: number;
  unit: string;
  value: number;
}
export interface Paper {
  /**
   * For 'catalogued' papers this is the curator's summary from OF-COR-001, NOT the publisher's abstract. `textSource` says which.
   */
  abstract: string;
  authors: string[];
  /**
   * Why this entry earns its place, from the corpus document.
   */
  corpusRole?: string;
  coverageDisputed?: CoverageDispute1;
  /**
   * The authoritative record key — never the author string (OF-COR-001 header).
   */
  doi?: string;
  /**
   * Corpus entry id, e.g. 'H1' — thread letter plus index (OF-COR-001 §1).
   */
  id: string;
  ingest: IngestStatus;
  /**
   * Openly retrievable vs. needs institutional access (OF-COR-001 §19).
   */
  openAccess: boolean;
  organisms: string[];
  pmcid?: string;
  pmid?: string;
  sections: PaperSection[];
  sourceType: SourceType;
  /**
   * Whether `sections` hold the paper's own text or the curator's notes.
   */
  textSource: 'full-text' | 'curation-note';
  thread: CorpusThread;
  title: string;
  topics: string[];
  /**
   * Ingestion tranche: 1 = open-access core, 2 = remainder, 3 = v1.1.
   */
  tranche: 1 | 2 | 3;
  venue: string;
  /**
   * Author string not fully resolved — must be checked at ingest ([verify]).
   */
  verifyNeeded?: boolean;
  /**
   * 0 where the year is genuinely unknown. A sentinel rather than a guess: see invariant 4 in CLAUDE.md.
   */
  year: number;
}
/**
 * A reader filed "something's missing" against this source (OF-FE-003 §8.4). Recall failure is the failure that hides: a wrong value gets clicked and corrected, a missed one is invisible forever. This flag is the only thing in the system that surfaces it, so it returns the source to the review queue rather than sitting as a passive annotation.
 */
export interface CoverageDispute1 {
  at: string;
  note: string;
}
export interface PaperSection {
  heading: string;
  id: string;
  text: string;
}
export interface ParameterDef {
  /**
   * '' for categorical fields (kinase_identity, glycan_species).
   */
  canonicalUnit: string;
  /**
   * Categorical fields hold a string value, not a number.
   */
  categorical?: boolean;
  definition: string;
  family: ParameterFamily;
  id: FieldId;
  name: string;
  notes: string;
  /**
   * @minItems 2
   * @maxItems 2
   */
  range: [number, number];
  /**
   * Unit families this field must NOT be auto-converted into, with the reason. OF-COR-001 §17 Rule 2: %TSP and g/L are not interconvertible without cell density and total-protein fraction. The engine refuses and says why.
   */
  refuseConversionTo?: RefuseConversion[];
  /**
   * OF-COR-001 §17 Rule 1: a value without its method is not interpretable.
   */
  requiresMethod?: boolean;
}
/**
 * One entry in `ParameterDef.refuseConversionTo`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. The `because` string is user-facing product copy and is reproduced
 * verbatim wherever it appears — a refusal that cannot say why is just an
 * error message.
 */
export interface RefuseConversion {
  because: string;
  field: FieldId;
}
/**
 * Derived at load from RECORDS. Never seeded — see engine/posterior.ts.
 */
export interface ParameterView {
  /**
   * Only records passing isAggregatable() contribute.
   */
  aggregate: Aggregate | null;
  contradictions: Contradiction[];
  def: ParameterDef;
  /**
   * Records held out of the aggregate, each with the reason.
   */
  excluded: ExcludedRecord[];
  field: FieldId;
  recordIds: string[];
  referee: UncheckedStatus | ConsistentStatus | ContradictedStatus;
}
export interface UncheckedStatus {
  state: 'unchecked';
}
export interface Patent {
  assignee: string;
  claims: ClaimScope[];
  id: string;
  jurisdiction: string;
  number: string;
  /**
   * The corpus entry this was catalogued from.
   */
  paperId?: string;
  priorityDate: string;
  status: PatentStatus;
  title: string;
  /**
   * Same discipline as papers: no invented identifiers, ever.
   */
  verifyNeeded?: boolean;
}
export interface Protocol {
  bsl: 1 | 2;
  category: ProtocolCategory;
  currentVersion: string;
  id: string;
  organisms: string[];
  provenanceNote: string;
  purpose: string;
  title: string;
  versions: ProtocolVersion[];
}
export interface ProtocolVersion {
  baseBatch: BaseBatch;
  changelog?: string;
  decisive?: DecisiveMeasurement;
  equipment: string[];
  estMinutes: EstimatedMinutes;
  materials: Material[];
  references: ProtocolReference[];
  /**
   * Shape of the result form an openLab deposit generates from a run.
   */
  resultSchema?: ResultField[];
  safety: string[];
  steps: Step[];
  version: string;
}
/**
 * One entry in `ProtocolVersion.references`.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model. Every member is optional in the TypeScript and stays optional here —
 * a reference may point at a corpus entry, at an extraction record, or be a
 * bare note.
 */
export interface ProtocolReference {
  note?: string;
  paperId?: string;
  recordId?: string;
}
export interface ResultField {
  field?: FieldId;
  id: string;
  label: string;
  required: boolean;
  type: 'number' | 'text' | 'boolean';
  unit?: string;
}
export interface Step {
  id: string;
  multiCheck?: string[];
  note?: string;
  /**
   * record or paper ids
   */
  refs?: string[];
  /**
   * may contain {{qty:materialName}} placeholders
   */
  text: string;
  timerLabel?: string;
  timerSec?: number;
}
/**
 * A failed run is a first-class outcome, not an error.
 */
export interface RunOutcome {
  depositedAt?: string;
  /**
   * Real bench prose: contamination, a pump, an ambiguous reading.
   */
  failureReason?: string;
  operator: string;
  outcome: 'success' | 'failure' | 'abandoned';
  /**
   * Records created by this deposit — evidenceClass: 'experiment'.
   */
  producedRecordIds: string[];
  results: {
    [k: string]: number | string | boolean;
  };
  runId: string;
}
/**
 * The scored output of one extractor run.
 *
 * No instance of this is seeded. `RUN_OUTPUTS` stays empty until a real
 * extractor runs (invariant 2 in CLAUDE.md) — the shape exists so that real
 * output has somewhere to land, not so that plausible numbers can be written
 * into it.
 */
export interface RunOutput {
  falsePositives: FalsePositive[];
  results: RunResult[];
  run: ExtractorRun1;
}
/**
 * One gold record's outcome in an extractor run.
 *
 * Inline in the TypeScript as an element of `RunOutput.results`; named here
 * because Pydantic has no anonymous model.
 */
export interface RunResult {
  extracted?: ExtractedValue;
  goldRecordId: string;
  outcome: RunOutcomeKind;
}
export interface RunState {
  /**
   * stepId -> multiCheck states
   */
  checks: {
    [k: string]: boolean[];
  };
  /**
   * stepId -> epoch ms completed
   */
  completed: {
    [k: string]: number;
  };
  currentStep: number;
  deviations: Deviation[];
  /**
   * epoch ms
   */
  finishedAt?: number;
  id: string;
  protocolId: string;
  /**
   * multiplier vs baseBatch
   */
  scale: number;
  /**
   * stepId -> reason
   */
  skipped: {
    [k: string]: string;
  };
  /**
   * epoch ms
   */
  startedAt: number;
  timers: TimerState[];
  version: string;
}
export interface TimerState {
  id: string;
  label: string;
  remainingSec: number;
  running: boolean;
  /**
   * epoch ms
   */
  startedAt?: number;
  stepId: string;
  totalSec: number;
}
export interface Scenario {
  assumptions: ScenarioAssumption[];
  description: string;
  dims: ScenarioDim[];
  id: string;
  modelId: 'S1' | 'S2' | 'S3';
  name: string;
  pinned: boolean;
  point: {
    [k: string]: number;
  };
  product: string;
}
export interface ScenarioAssumption {
  /**
   * Required. `check:seed` verifies a record binding against the record.
   */
  basis: BasisRecord | BasisModel | BasisUnsourced;
  label: string;
  note: string;
  /**
   * Cite a paper when the assumption rests on a source but no single record.
   */
  paperId?: string;
  provenance: Provenance;
  recordId?: string;
  unit: string;
  value: number;
}
export interface ScenarioDim {
  field?: FieldId1;
  key: string;
  label: string;
  /**
   * Cite a paper where a sweep default came from the literature.
   */
  paperId?: string;
  sourceRecordId?: string;
  unit: string;
  values: number[];
}
export interface SensitivityRow {
  assumption: string;
  field?: FieldId2;
  hiPct: number;
  lowPct: number;
}
export interface Strain {
  badges: string[];
  binomial: string;
  bsl: 1 | 2;
  description: string;
  designation: string;
  id: string;
  notes: CuratorNote[];
  taxonomy: string[];
}
/**
 * `ExtractionRecord.range` — a value the source states as an interval.
 *
 * Inline in the TypeScript; named here because Pydantic has no anonymous
 * model.
 */
export interface ValueRange1 {
  high: number;
  low: number;
}
