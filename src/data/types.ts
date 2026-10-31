// openFerment — the client's entity types (OF-DES-001 §15), hand-kept beside
// the generated src/api/types.gen.ts and held to the service by check:plan.

/**
 * Provenance classes (OF-DES-001 §7.4, revised by OF-COR-001 §20).
 *
 * 'assumed' (alpha 1.0's 'demo', renamed by ADR-006) marks a value that rests
 * on a named person's assumption or a model's estimate rather than a
 * measurement: a simulation run on a typed value, a stand-in model's answer,
 * and anything derived from them.
 *
 * 'curated' marks what is written by hand rather than read off a source: the
 * fields' definitions and canonical units, a strain's description. It is
 * weaker than 'verified' and never passes as a source-span extraction.
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
   * above 'gold', which is a reviewer's reading of somebody else's paper.
   * Created by reconciling a Deposition against the Runbook that predicted it.
   */
  | 'measured'
  | 'gold'
  | 'verified'
  | 'curated'
  /**
   * A deterministic calculation whose every input names a source
   * (OF-BLD-014 E.4): a converted value, a yield ceiling, a fitted rate, a
   * price. No experiment stands behind it, so it follows every experimental
   * class; anyone can reproduce it from its basis, so it precedes
   * 'unverified'. The service sets it through `basis_provenance` and the
   * browser shows what the service computed.
   */
  | 'computed'
  | 'unverified'
  | 'user'
  | 'industry-estimate'
  | 'assumed';

export type ParameterFamily =
  | 'expression'
  | 'cultivation'
  | 'downstream'
  | 'kinetics';

/**
 * The record fields (`core/openferment_core/schema/fields.yaml`, mirrored in
 * data/ontology.ts): thirty-four fields in four families.
 */
export type FieldId =
  // Expression performance
  | 'expression_pct_tsp'
  | 'titer_intracellular'
  | 'titer_secreted'
  | 'secreted_fraction'
  | 'fold_improvement'
  | 'transformation_efficiency'
  | 'time_to_colony'
  // Cultivation
  | 'growth_rate_mu'
  | 'final_biomass_density'
  | 'volumetric_productivity'
  | 'medium_component_conc'
  // Downstream & economics
  | 'disruption_protein_yield'
  | 'disruption_energy'
  | 'minimum_selling_price'
  | 'step_recovery'
  | 'product_purity'
  | 'partition_coefficient'
  | 'sieving_coefficient'
  | 'cake_moisture'
  // Growth and product kinetics
  | 'monod_ks'
  | 'biomass_yield_substrate'
  | 'ethanol_yield_substrate'
  | 'ethanol_titre'
  | 'ethanol_productivity'
  | 'ethanol_inhibition_ki'
  | 'ethanol_max_conc'
  | 'substrate_inhibition_ki'
  | 'ethanol_lp_alpha'
  | 'ethanol_lp_beta'
  | 'ethanol_mesp'
  | 'maintenance_coefficient'
  | 'biomass_yield_oxygen'
  | 'specific_oxygen_uptake'
  | 'kla_measured';

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
  // OF-BLD-014 §2.1 — how a polymer is measured: its content (GC, GC-MS,
  // NMR, FTIR, Nile red), its chain length (GPC) and its thermal behaviour (DSC).
  | 'GC'
  | 'GC-MS'
  | 'GPC'
  | 'NMR'
  | 'FTIR'
  | 'DSC'
  | 'Nile red'
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
  | `stage:${IngestStage}`
  /** The source document could not be retrieved at all. */
  | 'failed:fetch'
  | 'failed:parse'
  | 'shelf';

export type SourceType =
  | 'journal-article'
  | 'review'
  | 'thesis'
  | 'patent'
  | 'book'
  | 'industry-report'
  | 'preprint'
  /** An entry in a curated database, such as a strain page of the Saccharomyces Genome Database. */
  | 'database-entry';

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
  /** Unset when the source does not say. */
  year?: number;
  venue: string;
  organisms: string[];
  topics: string[];
  /** The publisher's abstract when the source gives one; empty otherwise. */
  abstract: string;
  sections: PaperSection[];
  ingest: IngestStatus;

  // ── the document's identity ────────────────────────────────────────
  sourceType?: SourceType;
  /** The authoritative record key — never the author string. */
  doi?: string;
  pmcid?: string;
  pmid?: string;
  /**
   * Where Intake fetches the text of a source Europe PMC does not hold: an
   * OSTI report's purl, an SGD strain entry's address. Written by
   * the collector from the source's identifier (`SGD:<id>`, an OSTI id); a strain entry has
   * no other identifier.
   */
  sourceUrl?: string;
  /** `sections` hold the document's own text, as the project holds it. */
  textSource: 'full-text';
  /** Openly retrievable vs. needs institutional access, from its licence class. */
  openAccess: boolean;

  // ── set by the service overlay (OF-BLD-012 §2.1) ──────────────────
  /** A document the open project holds in its literature (ADR-002), made from the overlay. */
  held?: boolean;
  /** Its licence class in the kit's taxonomy. */
  licenceClass?: string;
  /** The licence the fetched full text carried, when `textSource` is 'full-text'. */
  license?: string;
  /** Who served the fetched full text, when `textSource` is 'full-text'. */
  fetchedFrom?: FetchSource;
  /** Why the last fetch halted, when `ingest` is a failure state. */
  ingestReason?: string;
}

export type RecordStatus = 'unverified' | 'verified' | 'rejected';
// 'claude-1', the extractor that runs (OF-BLD-012 §6).
export type ExtractorRun = 'claude-1';

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
   * Explicit provenance. Extractor output is 'unverified' until reviewed, and
   * a decision gives it the class `biorepo.provenance_of` computes; market
   * figures are 'industry-estimate' and never enter the gold set.
   */
  provenance: Provenance;
  /**
   * The strain id when the paper's wording names a known strain (OF-BLD-014
   * §2.1), which is what every screen matches on; otherwise the wording as
   * the paper wrote it.
   */
  organism?: string;
  /**
   * The paper's own wording for the organism, kept when anchoring resolved it
   * to a strain id in `organism`. Absent when nothing was resolved, because
   * `organism` then already holds the wording.
   */
  organismText?: string;
  /**
   * The carbon source or feedstock the value was measured on, in the paper's
   * own words (OF-BLD-014 §2.1). Kept only when those words stand in the
   * cited section and carry no number; `carbonSourceId` in vocabulary.ts
   * resolves them to a name, or to nothing.
   */
  carbonSource?: string;
  componentTag?: string;
  gold?: { value: number | string; unit: string };
  goldOnly?: boolean;
  /** The extractor run that produced the record. */
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
  /** Where an alpha 1.0 curated value was transcribed from, kept on imported records. */
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
   * record itself.
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
 * A value the source states as an interval. The record carries it; §2.4
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
/** Where a number came from (ADR-006). */
export type OriginKind = 'record' | 'artifact' | 'person-assumption' | 'model-estimate' | 'library-default' | 'convention';
/** The origins a value set for one run can have (an Override's origin). */
export type OverrideOrigin = 'person-assumption' | 'model-estimate';

export interface Origin {
  kind: OriginKind;
  /** The record, the artifact or the library entry it was read from. */
  ref?: string | null;
  /** The person who typed it, or the id of the model that estimated it. */
  by?: string | null;
  /** The day it was typed, or the moment it was estimated. */
  at?: string | null;
  /** What it rests on, in words. */
  note?: string | null;
}

/**
 * A value and its unit (ADR-006). A number a model, a person or a library
 * supplies carries its origin; a value code derives from another (the SI
 * form of a record's value) carries none, and the service leaves an absent
 * basis, range or origin out.
 */
export interface Quantity {
  value: number | string;
  unit: string;
  /** What the value is reckoned on, in words (dry basis, per litre of broth). */
  basis?: string | null;
  low?: number | null;
  high?: number | null;
  origin?: Origin | null;
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
  /** The models that answered the run's papers, from their usage records
   *  (core/openferment_core/witness.py). */
  models?: string[];
}

/** A note written by hand about a strain. */
export interface StrainNote {
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
  notes: StrainNote[];
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
  /**
   * The skills a person needs to perform this step (OF-BLD-013 §1.1), as ids
   * from Guild's skills (none ship with alpha 2.0). Guild's Matrix reads these to say who can run
   * a protocol, and the run-mode gate reads them to decide whether a step
   * needs a cosigner. A step with no skills needs no qualification. Versioned
   * with the protocol, so a new version that changes a step can change what
   * it asks of the person doing it.
   */
  skills?: string[];
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
  /**
   * Who is performing the steps, from Guild's ledger (OF-BLD-013 §2). Starts
   * as whoever is signing in Guild; a handover changes it. Null when the
   * ledger has nobody on it, and then no step is gated.
   */
  operatorId?: string | null;
  /** Who stood beside the operator, per step, for a step that needed a cosigner. */
  cosigned?: Record<string, string>;
  /** Steps whose completion has already written to Guild's ledger, so a redo does not count twice. */
  guildRecorded?: Record<string, true>;
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
  /** The BioSTEAM flowsheet the scenario runs (§8.4). */
  modelId: string;
  /** A flowsheet the service simulates. */
  kind: 'biosteam';
  name: string;
  description: string;
  product: string;
  dims: ScenarioDim[];
  point: Record<string, number>;
  assumptions: ScenarioAssumption[];
  pinned: boolean;
  /**
   * The shelf flowsheet a `biosteam` scenario runs (OF-BLD-019 D2): an id
   * from `GET /api/proforma/shelf`, and nothing else about its structure.
   * Absent on an authored surface. A scenario a person makes with New
   * scenario always names one (§3.1).
   */
  flowsheetId?: string;
  /**
   * The id of the newest `proforma.run` artifact this browser saw for the
   * scenario (OF-BLD-019 D6), or absent/null when it has not run here. The
   * price on Proforma's index is read from that artifact, never kept here.
   */
  lastRunId?: string | null;
  /** When a person made the scenario (ISO time). */
  createdAt?: string;
  /**
   * OF-BLD-020 §6.1 (D11): what a scenario on `custom_train_v1` is built
   * from, kept with it in the project's rows (`scenarios`) and sent with
   * every binding and run: the kept `fermos.vessel` design (its artifact id)
   * and the kept `pureos.train_run` (its artifact id). Absent on any other.
   */
  vessel?: string;
  trainRun?: string;
}

export interface SensitivityRow {
  assumption: string;
  lowPct: number;
  hiPct: number;
}

/** A sweep's prices over its grid (§15 ResultGrid). */
export interface ResultGrid {
  modelId: string;
  dims: { key: string; values: number[] }[];
  msp: Float64Array;
  costLines: Record<CostLine, Float64Array>;
  sensitivity: SensitivityRow[];
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
  /**
   * The skills this lesson teaches toward (OF-BLD-013 §3.1), as ids from
   * Guild's skills (none ship with alpha 2.0). Passing its checkpoint writes a knowledge entry for
   * each one on the learner's ledger, which puts them at Learning. Only an
   * assessor's training sign-off moves them to Supervised.
   */
  skills?: string[];
}

export type LessonBlock =
  | { kind: 'prose'; md: string }
  | {
      kind: 'embed';
      embed:
        | 'chip-demo'
        | 'record-card'
        | 'mini-queue'
        | 'metrics-tiles'
        | 'strip-plot'
        | 'protocol-card'
        | 'ask-prompt'
        | 'scenario-widget'
        | 'skill-steps';
      arg?: string;
    };

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
  | 'finishing'
  // OF-BLD-020 §5.1: a pump, a tank, a heat exchanger, a mixer or a splitter
  // serves a train without being a step of it.
  | 'utility';

export interface UnitOperation {
  id: string;
  label: string;
  stage: UnitOperationStage;
  /** Scale band where the operation is used at all, when it is not universal. */
  scale?: string;
  /** Chemistry detail, e.g. the resin family for a chromatography step. */
  resin?: string;
  note?: string;
  /**
   * The BioSTEAM unit classes this step is (OF-BLD-019 §4.1), so a unit in a
   * train a flowsheet ran links to the step it performs. Names only, as
   * BioSTEAM spells its classes; a step BioSTEAM has no class for names none.
   */
  biosteamClasses?: string[];
}

/**
 * A carbon source a value can be measured on (OF-BLD-014 §2.1): a name and
 * the spellings a paper uses for it, lower-case. Words only — no number, no
 * concentration — because what is resolved is the paper's wording, not a
 * medium. `carbonSourceId` in vocabulary.ts matches against `spellings`.
 */
export interface CarbonSource {
  id: string;
  label: string;
  spellings: string[];
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
  regulatoryIds: string[];
  pathwayIds: string[];
  tags: string[];
  valueDensityBand: ValueDensityBand;
  /**
   * Always 'assumed' — every product record is modeled, not measured, and renders
   * as "Assumed · not measured" through the existing provenance system.
   */
  provenance: Provenance;
  note: string | null;
  /**
   * Always 'industry-estimate'. Value density and scale come from market
   * framing, not from evidence, and `aggregateExclusion()` already holds that
   * class out of every median, range and count.
   */
  economicsProvenance: Provenance;
  /**
   * The one-letter amino-acid sequence of the product's own chain
   * (OF-BLD-020 §7.1), from which Biopython's ProtParam computes its
   * molecular weight, isoelectric point, extinction coefficients and GRAVY
   * (`core/openferment_core/protparam.py`). Present only where it was read
   * from a named source; never invented. No entry carries one yet, so every
   * product's properties are missing and pureOS's proposer says so.
   */
  sequence?: string;
  /** Where `sequence` was read, e.g. a UniProt accession and the chain's residues. Required beside a sequence. */
  sequenceSource?: string;
  /**
   * Where the product is when the fermentation ends (OF-BLD-020 §7.2): secreted
   * into the broth, or held in the cells. pureOS's proposer splits a protein's
   * and a polymer's train on it. Present only where a named source says so;
   * no entry carries one yet, so the proposer names it missing.
   */
  location?: 'secreted' | 'intracellular';
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
  /**
   * Hours into the run, by entry id (OF-BLD-014 §7.1). An entry with a time
   * is a reading in a series; one without keeps its old meaning, where a
   * later entry on the same measure corrects an earlier one. Absent on
   * depositions saved before series.
   */
  sampleTimes?: Record<string, number>;
  /** What each measure's series is, by measure id, as a person assigned it. */
  seriesRoles?: Record<string, SeriesRole>;
}

export type SeriesRole = 'biomass' | 'product' | 'substrate';

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
  /**
   * OF-BLD-014 §9.1. A prediction with no kind is a point, held within the
   * ten percent band. An interval holds when the observed value lies inside
   * `interval`. A bound is a ceiling: it holds while the observed value stays
   * at or below `value` (the only bounds the service writes are ceilings).
   */
  kind?: 'point' | 'interval' | 'bound';
  interval?: Range;
  /** The computed evidence behind it, when there is one. */
  artifactId?: string;
  /** The records behind it, when it is a range of reported values. */
  recordIds?: string[];
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
  /** The runbook's framing — why it is worth looking at. */
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
  /** OF-BLD-014 §5.1: sentences it quotes, each checked verbatim against its passage. Absent on older plans. */
  passages?: PassageRef[];
  /** Computed values it rests on, by evidence id. Absent on older plans. */
  evidenceIds?: string[];
  /** OF-BLD-015 §7.2: module rows it rests on, as `<module>/<kind>/<id>`. Absent on older plans. */
  moduleRefs?: string[];
  /** ADR-006: the numbers it states, each typed with its origin; its text holds none. Absent on older plans. */
  values?: ClaimValue[];
}

/**
 * A number a claim states (ADR-006): what it is, and the quantity with its
 * origin, which the validator computed. A value read from a computed value or
 * a record names it in `source`; a model's estimate carries `model-estimate`
 * with the model's id, and the claim stating it is `assumed`.
 */
export interface ClaimValue {
  label: string;
  quantity: Quantity;
  source?: string | null;
}

/** A sentence a claim quotes, and the passage it stands in. */
export interface PassageRef {
  passageId: string;
  quote: string;
}

export type TraceKind = 'coverage' | 'tool' | 'restart' | 'final';
export type StopReason = 'done' | 'rounds' | 'calls' | 'cost' | 'time';

/** One step of Postdoc's loop, as the browser shows it (OF-BLD-014 §5.1). */
export interface TraceStep {
  n: number;
  kind: TraceKind;
  tool: string | null;
  input: Record<string, unknown> | null;
  /** One line, written by code. */
  summary: string;
  ms: number;
  ok: boolean;
}

// ── Coverage (OF-BLD-015 §7.1) ─────────────────────────────────────────
// Mirrors of the Pydantic models in core/openferment_core/models.py. Before
// Postdoc's first turn, code sweeps every module store for what the question
// names; the trace shows it as its first step and the footer reports it.

/** The one state every module row reads as, computed by the service. */
export type ModuleState = 'open' | 'fenced' | 'approved' | 'locked' | 'proposed' | 'retired';
export type ModuleName =
  | 'runbooks'
  | 'geneos'
  | 'fermos'
  | 'pureos'
  | 'proforma'
  | 'biorepo'
  | 'guild'
  | 'primer'
  | 'intake'
  | 'home';

/** One row of one module that the question names. */
export interface CoverageHit {
  /** `<module>/<kind>/<id>`, the id a claim cites it by. */
  ref: string;
  id: string;
  kind: string;
  label: string;
  state: ModuleState;
}

/** What the sweep found in one module. */
export interface ModuleCoverage {
  module: ModuleName;
  label: string;
  count: number;
  hits: CoverageHit[];
  /** The question names the module itself. */
  named: boolean;
  /** Set when a read leaves part of the module out, in words. */
  partial: string | null;
  /** Set when the module's store could not be read. */
  error: string | null;
}

/** One row a module's read tool returns (OF-BLD-015 §7.2). */
export interface ModuleRow {
  module: ModuleName;
  kind: string;
  id: string;
  /** `<module>/<kind>/<id>`, what a claim cites. */
  ref: string;
  label: string;
  /** Computed by the service from `status`, never by a model. */
  state: ModuleState;
  /** The module's own word for where the row stands. */
  status: string;
  /** Null for a row that carries no mark. */
  provenance: Provenance | null;
  detail: Record<string, unknown>;
}

/**
 * A project (alpha 2.0, ADR-005): what scopes a lab's documents, records,
 * flowsheets, runs, artifacts, runbooks, depositions, conversations and Guild
 * entries. Every row the service keeps belongs to one.
 */
export interface Project {
  id: string;
  name: string;
  description: string;
  createdBy: string;
  createdAt: string;
}

/** POST /api/projects. `id` is made from the name when left out. */
export interface ProjectCreate {
  name: string;
  description?: string;
  id?: string | null;
  /** The person creating it, as the reviewer name they sign with. */
  by: string;
}

/** One line of the audit log (OF-BLD-015 §7.3). */
export interface AuditEntry {
  at: string;
  agent: 'model' | 'person';
  who: string;
  module: ModuleName;
  action: string;
  state: string;
  target: string | null;
  askId: string | null;
  effort: string | null;
  detail: Record<string, unknown>;
}

export type ProposalState = 'proposed' | 'done' | 'dismissed';

/** What a model asked for at a gate (OF-BLD-015 §7.4), until a person acts on Home. */
export interface Proposal {
  id: string;
  at: string;
  module: ModuleName;
  action: string;
  gate: string;
  title: string;
  why: string;
  how: string;
  route: string | null;
  server: boolean;
  target: string | null;
  fields: Record<string, string>;
  note: string;
  by: string;
  askId: string | null;
  state: ProposalState;
  carriedOutBy: string | null;
  carriedOutAt: string | null;
  result: string | null;
}

export interface ProposalAction {
  person: string;
  reason: string;
  /**
   * The Guild person id the browser is acting as: a check is asked for by a
   * person on Guild, which knows people by id, never by the reviewer name
   * (OF-BLD-016 §1.R finding 11). Null when nobody is chosen.
   */
  actingId?: string | null;
}

export interface CoverageMap {
  entities: string[];
  searched: number;
  found: number;
  modules: ModuleCoverage[];
}

export interface AnswerPlanUsage {
  inputTokens: number;
  outputTokens: number;
  /**
   * Prompt tokens read from and written to the prompt cache (OF-BLD-014
   * §3.3); `inputTokens` excludes both. Absent on a plan saved before them.
   */
  cacheReadTokens?: number;
  cacheWriteTokens?: number;
  /** Computed from the response's own token counts, not estimated. */
  costUsd: number;
  /**
   * The models that answered, in order: Claude Opus 5.5, or Opus then the
   * Claude Sonnet 5.5 it fell back to (core/openferment_core/llm.py). Absent
   * or empty for a saved fixture that never called one.
   */
  models?: string[];
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
  /** OF-BLD-014 §5.1: computed values the claims cite. Absent on older plans. */
  evidence?: Evidence[];
  /** Passages the claims quote. Absent on older plans. */
  passages?: Passage[];
  /** The loop's steps. Absent on older plans. */
  trace?: TraceStep[];
  /** Why the loop stopped. */
  stopped?: StopReason;
  /** A runbook the agent drafted, its numbers written by the service (OF-BLD-014 §9.2). */
  runbookDraft?: RunbookDraft | null;
  /** OF-BLD-015 §7.1: the modules swept before the first turn. Absent on older plans. */
  coverage?: CoverageMap | null;
  /** OF-BLD-015 §7.2: the module rows the claims cite. Absent on older plans. */
  rows?: ModuleRow[];
  /** The conversation and turn the service kept this answer as; null when none was kept. */
  conversationId?: string | null;
  turnId?: string | null;
}

/**
 * One earlier turn sent with a follow-up (models.py PriorTurn): the question
 * and the plan's words. No id, value or quote travels; the follow-up's own
 * tools find whatever it cites.
 */
export interface PriorTurn {
  question: string;
  claims: string[];
  gaps: string[];
  declined: string | null;
}

/** What the browser posts to /api/ask and /api/ask/stream (models.py AskRequest). */
export interface AskRequest {
  question: string;
  /** The conversation's earlier turns, oldest first, for a caller that names no conversation; the service reads its own otherwise. */
  history: PriorTurn[];
  /** The conversation this question continues or starts, and the turn it is, by the page's ids. */
  conversationId?: string | null;
  turnId?: string | null;
  /** Who asks. */
  by?: string;
}

/**
 * One question asked in Live mode, and what came back: the steps as they
 * arrived, then the plan or the failure in words. Kept in its conversation,
 * so a follow-up reads it, and a citation followed and returned from, or a
 * reload, finds it where it was.
 */
export interface LiveTurn {
  id: string;
  question: string;
  askedAt: string;
  steps: TraceStep[];
  plan: AnswerPlan | null;
  error: { message: string; remedy: string } | null;
  /** `running` until the plan or the failure arrives. A turn a reload cut short reads `interrupted`. */
  status: 'running' | 'answered' | 'failed' | 'stopped' | 'interrupted';
  /** Who asked, as the service kept the turn. */
  by?: string | null;
  /** The artifacts the turn's tool calls produced or read, as the service kept it. */
  artifactIds?: string[];
}

/** A Live-mode conversation: its turns, oldest first. Kept by the service (postdoc/conversations.py). */
export interface LiveConversation {
  id: string;
  title: string;
  startedAt: string;
  turns: LiveTurn[];
}

/** One tool call a turn made (GET /api/conversations/{id}/turns/{turn}/calls). */
export interface ToolCallRecord {
  seq: number;
  turnId: string;
  tool: string;
  input: Record<string, unknown>;
  /** What the tool answered the model. */
  summary: Record<string, unknown>;
  error: string | null;
  /** What it offered to cite, by id. */
  evidenceIds: string[];
  recordIds: string[];
  passageIds: string[];
  artifactIds: string[];
  by: string;
  at: string;
}

// ── Intake (OF-BLD-012 §2.5, §5) ────────────────────────────────────────
//
// Mirrors of the Pydantic models in core/openferment_core/models.py; `pnpm
// check:plan` fails the build if a field exists on one side only. The service's
// `FetchedSection` is the same shape as `PaperSection` above and is compared
// against it.

/**
 * What the JATS <license> element said, or what an OSTI report or an SGD
 * strain entry states of itself, stored beside every fetched text.
 */
export interface FetchLicense {
  href: string | null;
  text: string | null;
}

export type FetchStatus = Extract<IngestStatus, 'complete' | 'failed:fetch' | 'failed:parse'>;

/**
 * Who served a fetched text: Europe PMC's JATS, an OSTI report's PDF, or a
 * Saccharomyces Genome Database strain entry. Absent from what an older
 * service sent, which was always Europe PMC.
 */
export type FetchSource = 'europepmc' | 'osti' | 'sgd' | 'upload' | 'paste';

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
  /** Size of the document as received: the XML, the PDF or the JSON. */
  bytes: number;
  source?: FetchSource;
}

/**
 * What Intake did with one document (ADR-002): `ingested`, stored in the kit
 * for the first time; `linked`, the kit held the same text already and the
 * project now holds it too; `held`, the project held it before; `failed`,
 * nothing stored, and `reason` says why. `transient` marks a failure that was
 * the network's condition, worth asking again. Mirrors models.py
 * `CollectOutcome`.
 */
export interface CollectOutcome {
  status: 'ingested' | 'linked' | 'held' | 'failed';
  documentId: string | null;
  collector: string;
  identifier: string;
  title: string;
  licenceClass: string;
  licence: FetchLicense | null;
  sections: number;
  tables: number;
  chunks: number;
  reason: string | null;
  transient: boolean;
}

/** POST /api/intake/collect. Mirrors models.py `CollectRequest`. */
export interface CollectRequest {
  identifier: string;
  by: string;
  reason?: string;
}

/** POST /api/intake/paste. Mirrors models.py `PasteRequest`. */
export interface PasteRequest {
  title: string;
  text: string;
  by: string;
  url?: string;
  licenceClass?: string;
  licence?: string;
  reason?: string;
}

/** One passage a search found (GET /api/literature/search). Mirrors models.py `SearchHit`. */
export interface SearchHit {
  documentId: string;
  passageId: string;
  title: string;
  text: string;
  sectionPath: string | null;
  citation: string | null;
  licenceClass: string;
  year: number | null;
  score: number;
  layers: string[];
  isTable: boolean;
}

/** GET /api/literature/search. Mirrors models.py `SearchResponse`. */
export interface SearchResponse {
  query: string;
  profile: string;
  hits: SearchHit[];
  degradedStages: string[];
}

/** POST /api/literature/answer. Mirrors models.py `LiteratureQuestion`. */
export interface LiteratureQuestion {
  question: string;
  topK?: number;
}

/** One document a project holds (GET /api/literature/documents). Mirrors models.py `LiteratureDocument`. */
export interface LiteratureDocument {
  documentId: string;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  journal: string | null;
  citation: string | null;
  source: string;
  sourceRef: string | null;
  licenceClass: string;
  chunks: number;
  collector: string | null;
  selection: Record<string, unknown>;
  linkedBy: string;
  linkedAt: string;
}

/**
 * What the overlay says about one document the project holds (§2.1): its
 * passages as its sections, its citation and its licence.
 */
export interface OverlayPaper {
  ingest: IngestStatus;
  textSource: 'full-text';
  sections: PaperSection[];
  license: string | null;
  fetchedAt: string | null;
  reason: string | null;
  /** Who served the text, so the reader names it rather than assuming Europe PMC. */
  source?: FetchSource;
  // The citation the kit holds for a document the project holds (ADR-002),
  // from which the store makes its paper, and its licence class.
  title?: string | null;
  authors?: string[];
  year?: number | null;
  journal?: string | null;
  doi?: string | null;
  pmcid?: string | null;
  url?: string | null;
  licenceClass?: string | null;
}

/**
 * GET /api/biorepo/overlay. Applied in one action when the service answers;
 * a project's papers, records and runs reach the page through it.
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
  organismText?: string;
  carbonSource?: string;
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
 * so the run can be scored honestly (§6.2): one whose value agreed with a
 * value a reviewer typed and whose quote failed is a span_error in Witness.
 * Never a record.
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
  /**
   * Fields anchoring removed from a candidate it KEPT, counted by reason
   * (OF-BLD-014 §2.1). Not rejections: the candidate is in `candidates`
   * without the field. Today the one reason is `carbonSource`, for words not
   * in the cited section or carrying a number.
   */
  fieldDrops: Record<string, number>;
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
 * and, for a decision that re-anchors the record to another sentence of
 * the paper, the replacement span.
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

// ── Guild: skills and competence (OF-BLD-013) ──────────────────────────
//
// The workforce layer. A Skill is reference data, like a protocol; no skills
// ship with alpha 2.0, and the tests hand theirs in. Protocol steps name the skills
// they need (`Step.skills`). Everything a person has done to earn a skill is
// an entry in Guild's ledger, and their level on that skill is computed from
// those entries by `src/engine/competence.ts`. Nothing stores a level.

/** The six trunk families. Working names until the skills content pass. */
export type SkillFamilyId = 'contamination' | 'vessel' | 'monitoring' | 'qc' | 'records' | 'safety';

export interface SkillFamily {
  id: SkillFamilyId;
  name: string;
  /** Column-header form for the Matrix. */
  short: string;
}

export interface Skill {
  /** `SK-` followed by capitals, stable forever once a ledger names it. */
  id: string;
  name: string;
  family: SkillFamilyId;
  /** One line on what the skill is, in plain words. */
  summary: string;
  /**
   * What an assessor watches for, each one a behaviour that can be seen at
   * the bench. A criterion nobody can observe cannot be signed off.
   */
  mastery: string[];
  /** A critical skill is one where a mistake hurts a person or loses a batch. */
  criticality: 'routine' | 'critical';
  /** How long a qualification stands without anyone seeing the person perform. */
  recencyDays: number;
  /** Cosigned performances needed before a witnessed check can qualify. */
  supervisedRuns: number;
  /** Skills that must be at Supervised or above before this one moves past Learning. */
  prerequisites: string[];
}

// ── Guild: the ledger (OF-BLD-013 §1.2) ────────────────────────────────
//
// Mirrored exactly from `core/openferment_core/models.py`; `check:plan` fails
// the build if a field exists on one side only. The ledger is
// core/data/guild.json, which only `guild.write_*` writes and git never sees.

export type GuildRole = 'member' | 'lead' | 'auditor';

/**
 * Every kind the ledger will hold. Sign-offs and designations come from Guild;
 * runs alone, cosigned runs and deviations from Deposition as the operator
 * completes a step; a lesson passed and a practice session from Primer, each
 * with nobody watching.
 */
export type EvidenceKind =
  | 'witnessed'
  | 'supervised'
  | 'independent'
  | 'deviation'
  | 'scenario'
  | 'knowledge'
  | 'designation';

export type EvidenceSourceKind = 'signoff' | 'lead' | 'deposition' | 'lesson' | 'scenario' | 'check';

export interface GuildPerson {
  /** Chosen by the browser, so a person added offline keeps their id. */
  id: string;
  name: string;
  role: GuildRole;
  title: string;
  joinedAt: string;
  active: boolean;
  addedBy: string | null;
  addedAt: string;
  updatedBy?: string | null;
  updatedAt?: string | null;
}

export interface EvidenceSource {
  kind: EvidenceSourceKind;
  /** A protocol id, a lesson id, or what a sign-off names. */
  ref: string;
  stepId?: string | null;
}

/** One thing a person did that bears on one skill. Append-only. */
export interface GuildEvidence {
  id: string;
  personId: string;
  skillId: string;
  kind: EvidenceKind;
  outcome: 'pass' | 'fail';
  /** When it happened, YYYY-MM-DD or a full ISO time. */
  at: string;
  observerId: string | null;
  source: EvidenceSource;
  /** The observer's own words, verbatim. */
  raw: string;
  /** Stamped by the service when it stored the entry. */
  recordedAt?: string | null;
  withdrawnAt?: string | null;
  withdrawnBy?: string | null;
  withdrawReason?: string | null;
}

export interface GuildWithdrawal {
  evidenceId: string;
  by: string;
  at: string;
  reason: string;
}

export type GateMode = 'advise' | 'enforce';

/**
 * The lead's choices for the team (OF-BLD-013 §5.1). In advise mode the
 * run-mode gate warns and records a deviation; in enforce mode it holds the
 * step until a cosigner is recorded, or someone qualified takes over.
 */
export interface GuildPolicy {
  routineGate: GateMode;
  criticalGate: GateMode;
  /** The witnessed checks each holder of a critical skill gets at least, every quarter. */
  checksPerQuarter: number;
  updatedBy?: string | null;
  updatedAt?: string | null;
}

export interface Guild {
  version: 1;
  people: GuildPerson[];
  evidence: GuildEvidence[];
  /** Absent in a ledger written before Phase 5; `policyOf` supplies the default. */
  policy?: GuildPolicy;
}

// ── Practice (OF-BLD-013 §4) ───────────────────────────────────────────
//
// Mirrored exactly from `core/openferment_core/models.py`. The model writes
// words and cites sources; every value the trainee sees is copied by the
// service from the source it cites. core/data/practice.json never enters git.

export type PracticeSourceKind = 'step' | 'material' | 'entry' | 'observation';
export type PracticeMove = 'why' | 'change' | 'next' | 'close';

export interface PracticeStepRef {
  protocolId: string;
  stepId: string;
}

/** What a value in the evidence pane was copied from. */
export interface PracticeSource {
  kind: PracticeSourceKind;
  protocolId?: string | null;
  stepId?: string | null;
  material?: string | null;
  depositionId?: string | null;
  itemId?: string | null;
}

/** One item in the evidence pane: the model's label, the source's words and number. */
export interface PracticeValue {
  id: string;
  label: string;
  source: PracticeSource;
  text: string;
  value?: number | null;
  unit?: string | null;
  at?: string | null;
  /** For a run's entry, the runbook's name for what was measured. */
  measure?: string | null;
  /** For a protocol's step or material, the batch its amounts are written for. */
  basis?: string | null;
}

export interface PracticeScenario {
  id: string;
  skillId: string;
  title: string;
  /** [v1] marks where an item of the evidence pane belongs. */
  situation: string;
  prompt: string;
  /** What a sound answer would reach. The tutor reads it; the trainee does not. */
  watchFor: string[];
  evidence: PracticeValue[];
  steps: PracticeStepRef[];
  depositionIds: string[];
  model: string;
  usage: AnswerPlanUsage;
  createdAt: string;
}

export interface PracticeDepositionEntry {
  id: string;
  stepId: string;
  at: string;
  value: number;
  unit: string;
  raw: string;
  label?: string | null;
  /** An unconfirmed entry may be a misheard number, so Practice never teaches from one. */
  confirmed: boolean;
}

export interface PracticeDepositionObservation {
  id: string;
  stepId: string;
  at: string;
  raw: string;
}

/** A Deposition as the browser sends it for drafting. */
export interface PracticeDeposition {
  id: string;
  protocolId: string;
  startedAt: string;
  entries: PracticeDepositionEntry[];
  observations: PracticeDepositionObservation[];
}

export interface PracticeDraftRequest {
  skillId: string;
  depositions: PracticeDeposition[];
}

export interface PracticeTurn {
  role: 'trainee' | 'tutor';
  text: string;
  move?: PracticeMove | null;
  steps: PracticeStepRef[];
  at: string;
}

/** What the tutor observed, with the steps it bears on. No grade. */
export interface PracticeObservation {
  text: string;
  steps: PracticeStepRef[];
}

export interface PracticeSession {
  id: string;
  scenarioId: string;
  skillId: string;
  /** A person on Guild's ledger, or null for a session nobody's record keeps. */
  personId?: string | null;
  turns: PracticeTurn[];
  observed: PracticeObservation[];
  startedAt: string;
  closedAt?: string | null;
  /** The ledger entry written when the session closed, when there is one. */
  evidenceId?: string | null;
  usage: AnswerPlanUsage;
}

export interface PracticeTurnRequest {
  scenarioId: string;
  sessionId?: string | null;
  personId?: string | null;
  answer: string;
}

/** core/data/practice.json — every scenario drafted and every session held. */
export interface Practice {
  version: 1;
  scenarios: PracticeScenario[];
  sessions: PracticeSession[];
}

// ── Checks (OF-BLD-013 §5) ─────────────────────────────────────────────
//
// Mirrored exactly from `core/openferment_core/models.py`. A check is
// proposed by fixed rules over the ledger (src/engine/checks.ts), or asked
// for, then scheduled and run at the bench by an assessor; running it writes
// one witnessed entry per skill with the check as its source.

export type CheckState = 'proposed' | 'scheduled' | 'done' | 'dismissed';
export type CheckReasonKind = 'suspended' | 'lapsed' | 'lapsing' | 'ready' | 'deviation' | 'confidence' | 'rate' | 'requested';

/** Why a check is proposed, written by fixed rules from the ledger. */
export interface CheckReason {
  kind: CheckReasonKind;
  skillId: string;
  text: string;
}

/** One of a skill's mastery criteria, by its place in the skill's list (Guild's skills; none ship with alpha 2.0). */
export interface CheckCriterion {
  skillId: string;
  index: number;
}

/** What the model suggests the assessor watch for: references and questions with no number. */
export interface CheckBrief {
  steps: PracticeStepRef[];
  criteria: CheckCriterion[];
  questions: string[];
  model: string;
  usage: AnswerPlanUsage;
  draftedAt: string;
}

/** The assessor's call on one criterion, with their own words. */
export interface CheckResult {
  skillId: string;
  criterion: number;
  meets: boolean;
  note: string;
}

export interface Check {
  id: string;
  personId: string;
  skillIds: string[];
  reasons: CheckReason[];
  state: CheckState;
  score: number;
  proposedAt: string;
  /** Null for the nightly ranking; otherwise who asked for it. */
  proposedBy?: string | null;
  /** Who scheduled or ran it. */
  assessorId?: string | null;
  /** The day the assessor picked. The person is not told. */
  scheduledFor?: string | null;
  brief?: CheckBrief | null;
  results: CheckResult[];
  evidenceIds: string[];
  closedAt?: string | null;
  dismissedBy?: string | null;
  dismissReason?: string | null;
}

/** core/data/checks.json — every check proposed, asked for, run or dismissed. */
export interface Checks {
  version: 1;
  checks: Check[];
}

export interface CheckRequest {
  personId: string;
  skillIds: string[];
  by: string;
}

export interface CheckSchedule {
  by: string;
  scheduledFor: string;
}

export interface CheckDismiss {
  by: string;
  reason: string;
}

/** The assessor's own words on one skill, kept verbatim as the entry's raw. */
export interface CheckNote {
  skillId: string;
  text: string;
}

export interface CheckRecord {
  by: string;
  at: string;
  results: CheckResult[];
  notes: CheckNote[];
}

// ── computed values (OF-BLD-014 §3.1, E.4) ─────────────────────────────
//
// A number no paper states: a converted value, a yield ceiling, a fitted rate,
// a price. It carries the calculation that produced it, and every input names
// where it came from. Its provenance is what the service's `basis_provenance`
// computed; the browser shows it and keeps no copy of the rule.

/** `assumption` is a named person's value; `model-estimate` a model's, its id in `by` (ADR-006). */
export type BasisSourceKind = 'record' | 'deposition' | 'artifact' | 'model' | 'convention' | 'assumption' | 'model-estimate';

export interface BasisSource {
  kind: BasisSourceKind;
  /** The record, deposition, artifact or model file the input was read from. */
  id: string | null;
  /** What the convention is, or what the assumption rests on. */
  note: string | null;
  /** The named person, for an assumption; the model's id, for an estimate. */
  by: string | null;
}

export interface BasisInput {
  name: string;
  value: number | string;
  unit: string;
  source: BasisSource;
}

export interface ComputedBasis {
  tool: string;
  /** Package versions and model file hash, joined. */
  toolVersion: string;
  inputs: BasisInput[];
  artifactId: string;
  at: string;
  /** For anything sampled. */
  seed: number | null;
}

/** A computed value a plan may cite. Its label is built by code. */
export interface Evidence {
  id: string;
  label: string;
  value: number | string;
  unit: string;
  interval: Range | null;
  provenance: Provenance;
  basis: ComputedBasis;
  /** Which figure draws this artifact: 'ceiling', 'frontier', 'trajectory', 'distribution'. */
  figure: string | null;
}

// ── artifacts (OF-BLD-014 §3.2, E.5) ───────────────────────────────────

/** What was computed, kept so it can be read and replayed. */
export interface Artifact {
  /** First 16 hex of sha256 over tool, toolVersion, canonical inputs (and the seed, when there is one). */
  id: string;
  tool: string;
  toolVersion: string;
  inputs: BasisInput[];
  /** Tool-specific; small enough to read on a page. */
  output: Record<string, unknown>;
  /** sha256 of the canonical output JSON. */
  outputHash: string;
  provenance: Provenance;
  createdAt: string;
  durationMs: number;
  seed: number | null;
}

/** One place a replayed output differs from the stored one. */
export interface ReplayDifference {
  /** Where in the output, as `a.b[2]`; empty for the output as a whole. */
  path: string;
  stored: unknown;
  replayed: unknown;
}

/** How near a replayed number must come to the stored one: within atol + rtol·|stored|. */
export interface ReplayTolerance {
  rtol: number;
  atol: number;
  why: string;
}

export interface ReplayResult {
  artifactId: string;
  identical: boolean;
  storedHash: string;
  replayedHash: string;
  differences: ReplayDifference[];
  durationMs: number;
  /** The precision the tool's basis states, when it states one. */
  tolerance?: ReplayTolerance | null;
  /** Every difference a number within the tolerance; true for an identical replay. */
  withinTolerance?: boolean;
}

// ── tools (OF-BLD-014 §3.4, E.6) ───────────────────────────────────────

/** One tool as `GET /api/tools` lists it. */
export interface ToolInfo {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/** What a tool returns: to Postdoc's loop, the HTTP endpoint or the MCP server. */
export interface ToolResult {
  /** What the model reads; at most 9,000 characters as JSON. */
  summary: Record<string, unknown>;
  /** Computed values a plan may cite. */
  evidence: Evidence[];
  /** Records a plan may cite. */
  recordIds: string[];
  /** Passages a plan may quote (OF-BLD-014 §5.2). */
  passages: Passage[];
  /** A refusal or an unavailable tool, in words. */
  error: string | null;
  /** What the tool spent on models, charged to the question (OF-BLD-014 §5.R). */
  usage: AnswerPlanUsage;
  /** A runbook draft the service assembled (§9.2). */
  draft: RunbookDraft | null;
  /** Module rows a plan may cite (OF-BLD-015 §7.2). */
  rows: ModuleRow[];
  /** The whole of what a summary cuts to the cap, for the endpoint and the MCP server; never citable (OF-BLD-019 §6.1). */
  data: Record<string, unknown> | null;
}

// ── Runbook drafts (OF-BLD-014 §9.2) ─────────────────────────────────────

/** One prediction the agent asks for: one evidence id, or records of one field. */
export interface DraftItem {
  label: string;
  evidenceId: string;
  field: string;
  recordIds: string[];
}

export interface DraftMeasure {
  label: string;
  unit: string;
  timepoint: 'start' | 'mid-run' | 'harvest' | 'after recovery';
  itemLabel: string;
}

/** Assembled by the service; a person adopts it as a research runbook and locks it. */
export interface RunbookDraft {
  title: string;
  productId: string;
  strainId: string;
  predictions: Prediction[];
  measures: Measure[];
}

// ── geneOS (OF-BLD-014 §6.3) ───────────────────────────────────────────

/** One model on geneOS's shelf. Mirrors `GeneosModelInfo` in models.py. */
export interface GeneosModelInfo {
  id: string;
  name: string;
  /** The strain id the model describes, when the catalogue has one. */
  host: string | null;
  scope: string;
  route: string;
  licence: string;
  source: string;
  /** Why it cannot be loaded here (its file is not fetched), or null. */
  unavailable: string | null;
  /** The sugar a view opens on: one the model can take up. */
  feed: string;
  notes: string[];
  /**
   * The product a view opens on, and every product the shelf names a route
   * to in this model ('phb', 'ethanol'); the worker decides what it makes.
   */
  product: string;
  products: string[];
}

export type GeneosKind = 'ceiling' | 'frontier' | 'mix';

/**
 * A ceiling, a frontier or a sugar mix: an artifact and its evidence, or a
 * finding in words with no number. Mirrors `GeneosResult` in models.py.
 */
export interface GeneosResult {
  kind: GeneosKind;
  modelId: string;
  product: string;
  substrates: string[];
  finding: string | null;
  artifactId: string | null;
  evidence: Evidence | null;
  /** The worker's output as the artifact stores it. */
  output: Record<string, unknown>;
}

// ── fermOS (OF-BLD-014 §7.2) ───────────────────────────────────────────
// Mirrors of the fit shapes in models.py.

export interface FermosPoint {
  /** Hours into the run. */
  t: number;
  value: number;
  entryId: string;
  confirmed: boolean;
}

export interface FermosSeries {
  measureId: string;
  label: string;
  unit: string;
  role: SeriesRole | null;
  points: FermosPoint[];
}

export interface FermosFitRequest {
  depositionId: string;
  series: FermosSeries[];
  /** The sample run: computed inline, kept nowhere. */
  sample: boolean;
  /** The model fitted: 'logistic_v0' (the default) or a kinetics family by id ('batch_v1'). */
  family?: string;
}

/** One fitted parameter, its 95 % interval and its unit. */
export interface FitParam {
  name: string;
  value: number;
  low: number;
  high: number;
  unit: string;
  identified: boolean | null;
  indistinguishableFromZero: boolean | null;
  /**
   * Why a kinetics family's fit reports it unidentified (OF-BLD-020 §3.R), in
   * the order a reader names them; absent where it does not apply (a logistic
   * fit's parameters, an identified one).
   */
  unidentifiedBy?: UnidentifiedReason[] | null;
}

/** Why a fitted parameter is unidentified: the gauge X0 of a run with no biomass series, the no-biomass rule on μmax, the optimizer's budget, the Jacobian's null space, the interval reaching zero. */
export type UnidentifiedReason = 'gauge' | 'rule' | 'budget' | 'null-space' | 'interval';

export interface GrowthFit {
  measureId: string;
  unit: string;
  mu: FitParam | null;
  doublingTimeH: number | null;
  r2: number | null;
  window: number[];
  points: number;
  reason: string | null;
}

export interface SeriesFitQuality {
  measureId: string;
  role: SeriesRole;
  r2: number;
  scatter: number;
  residuals: number[];
}

export interface KineticFit {
  params: FitParam[];
  quality: SeriesFitQuality[];
  covariance: number[][];
  series: FermosSeries[];
  reason: string | null;
  /** The model fitted; a fit kept before OF-BLD-020 holds none and reads as 'logistic_v0'. */
  model?: string;
  /** What the fit says of itself in words: the terms it held, a parameter unidentified by rule. */
  notes?: string[];
}

export interface FermosFitResponse {
  depositionId: string;
  growth: GrowthFit | null;
  kinetic: KineticFit | null;
  growthArtifactId: string | null;
  kineticArtifactId: string | null;
  /** The share of the readings a person confirmed. */
  confirmedShare: number;
  sample: boolean;
  notes: string[];
}

/** A forecast's starting values; unset ones are the fitted run's own. */
export interface StartValues {
  X0: number | null;
  P0: number | null;
  S0: number | null;
}

export interface ForecastRequest {
  fitArtifactId: string | null;
  fit: KineticFit | null;
  start: StartValues;
  /** Who changed a starting value; a changed one is that person's assumption. */
  changedBy: string | null;
  durationH: number | null;
  /** Who set the length; a length a person set is that person's assumption (OF-BLD-020 §3.R). */
  durationBy: string | null;
  sample: boolean;
}

export interface Band {
  role: SeriesRole;
  unit: string;
  low: number[];
  median: number[];
  high: number[];
}

export interface Interval {
  role: string;
  unit: string;
  low: number;
  median: number;
  high: number;
}

export interface ForecastResult {
  times: number[];
  bands: Band[];
  finals: Interval[];
  yieldInterval: Interval | null;
  /** Where the median substrate curve reaches zero, the forecast ends. */
  substrateRunsOutH: number | null;
  draws: number;
  seed: number;
  artifactId: string | null;
  evidence: Evidence | null;
  sample: boolean;
  notes: string[];
}

// ── passages (OF-BLD-014 §4.1) ─────────────────────────────────────────

export type PassageKind = 'abstract' | 'prose' | 'table' | 'figure';

/** A piece of a fetched paper's own text, as a search returns it. */
export interface Passage {
  /** `<paperId>:<sectionId>:<n>` */
  id: string;
  paperId: string;
  sectionId: string;
  heading: string;
  kind: PassageKind;
  text: string;
  /** Offsets into the section's text. */
  start: number;
  end: number;
}

// ── Proforma's BioSTEAM scenario (OF-BLD-014 §8.3) ──────────────────────
// Mirrors of core/openferment_core/models.py; check:plan diffs the fields.

/** One record an input was bound to, in the input's unit. */
export interface BoundRecord {
  id: string;
  paperId: string;
  value: number;
  organism: string | null;
  carbonSource: string | null;
  provenance: Provenance;
}

export interface ScenarioInput {
  key: string;
  label: string;
  unit: string;
  /**
   * 'records': bound records; 'assumption': a named person typed it;
   * 'artifact': a fermOS fit or forecast a person chose computes it, its
   * source naming the artifact (OF-BLD-019 §5.1, D10); 'waiting': none of
   * these, so the run is refused.
   */
  binding: 'records' | 'assumption' | 'artifact' | 'waiting';
  value: number | null;
  low: number | null;
  high: number | null;
  sampling: 'triangular' | 'uniform' | 'fixed' | null;
  source: BasisSource | null;
  recordIds: string[];
  records: BoundRecord[];
  leftOutNoCarbon: number;
  leftOutOtherCarbon: number;
  flags: string[];
}

/** A value a named person typed for one input, with its range. */
export interface InputAssumption {
  key: string;
  value: number;
  low: number;
  high: number;
  by: string;
  at: string;
  note: string | null;
}

export interface ProformaScenarioInfo {
  id: string;
  name: string;
  product: string;
  flowsheet: string;
  host: string | null;
  hosts: string[];
  inputs: ScenarioInput[];
  waiting: string[];
  leavesOut: string[];
  priceBasis: string;
}

export interface ProformaRunRequest {
  scenarioId: string;
  /**
   * The older field (OF-BLD-014 §8.4): a named person's values by input key.
   * The service reads it as overrides for one release (OF-BLD-020 §2.2); this
   * browser sends `overrides` instead.
   */
  assumptions?: InputAssumption[];
  /**
   * A person's changes in the parameter panel (OF-BLD-020 D3), each an
   * Override of scope `proforma:<scenarioId>`: a named assumption that wins
   * over the records and any fermOS fit for its input, named in the run's
   * basis. The service keeps none.
   */
  overrides?: Override[];
  host: string | null;
  seed: number;
  /** Latin hypercube samples to draw (OF-BLD-019 D7); the service defaults it and caps it. */
  samples?: number;
  /**
   * The shelf flowsheet the scenario runs (OF-BLD-019 §2.3, D6). A scenario
   * the project keeps runs its own; one not yet saved runs this flowsheet,
   * bound as `GET /api/proforma/bind` binds it.
   */
  flowsheet?: string | null;
  /**
   * The fermOS fits a person chose, by input key (titre, yield,
   * productivity), each a kept `kinetic_fit` or `growth_forecast` artifact id
   * (OF-BLD-019 §5.1, D10). The service computes each value from it.
   */
  fits?: Record<string, string>;
  /**
   * OF-BLD-020 §6.1 (D11): a scenario on `custom_train_v1` names the kept
   * `fermos.vessel` design its fermenter is rebuilt from and the kept
   * `pureos.train_run` whose units follow it; refused for any other flowsheet.
   */
  vessel?: string | null;
  trainRun?: string | null;
}

/**
 * What one fermOS artifact gives one input of a flowsheet (OF-BLD-019 §5.1):
 * the value in the input's unit with the 5th and 95th percentile of the
 * forecast's band for readings, or why it gives nothing, naming the parameter.
 */
export interface FitFeed {
  key: string;
  unit: string;
  value: number | null;
  low: number | null;
  high: number | null;
  /** How the value is computed from the artifact, in words. */
  derivation: string;
  /** Why it gives nothing; null when it gives the value. */
  refused: string | null;
}

/**
 * A kinetic fit or forecast fermOS keeps, and what it can feed one shelf
 * flowsheet (`GET /api/fermos/fits?flowsheet=`). A person picks it; a model
 * never does.
 */
export interface FermosFitInfo {
  artifactId: string;
  /** 'kinetic_fit' or 'growth_forecast'. */
  tool: string;
  provenance: Provenance;
  createdAt: string;
  flowsheet: string;
  /** The run the fit was made on, and the kinetic fit a forecast rests on. */
  depositionId: string | null;
  fitArtifactId: string | null;
  productSeries: string | null;
  substrateSeries: string | null;
  /** The hour the forecast's median sugar runs out: the batch time a productivity is the titre over. */
  batchTimeH: number | null;
  /** How that hour was found, in the words of the tool that kept it (§8.R). */
  batchTimeNote: string | null;
  feeds: FitFeed[];
  flags: string[];
  /** Why it feeds nothing at all, in words. */
  refused: string | null;
}

// ── The geneOS ceiling check (OF-BLD-019 §5.2, D11) ─────────────────────
//
// A scenario's fermenter yield beside the newest stored geneOS ceiling of
// each shelf model of its organism, on its flowsheet's sugar, as
// `GET /api/proforma/ceiling-check` computes it on read. A flag, never a
// bound: the browser shows it and computes no number of its own.

/** One stored ceiling beside the scenario's yield, both in the ceiling's basis. */
export interface CeilingRow {
  modelId: string;
  /** The model as geneOS's shelf names it, and as the ceiling's basis names it. */
  modelName: string;
  modelBasis: string;
  /** The strain the reconstruction describes. */
  host: string | null;
  /** How the scenario's organism maps to the model: the same strain, or another strain of its species. */
  match: 'strain' | 'species';
  matchWords: string;
  product: string;
  substrate: string;
  /** The newest stored `geneos.ceiling` of this model, product and sugar; how many older ones it stands in front of. */
  artifactId: string;
  provenance: Provenance;
  createdAt: string;
  older: number;
  ceilingGPerG: number;
  ceilingMolPerMol: number | null;
  /** The product and sugar conventions the ceiling's basis names, in its words. */
  conventions: string[];
  /** The scenario's yield in the ceiling's basis: g per g, and mol per mol at the ceiling's own conventions. */
  yieldGPerG: number | null;
  yieldLowGPerG: number | null;
  yieldHighGPerG: number | null;
  yieldMolPerMol: number | null;
  /** 'above' when the yield or its high end exceeds the ceiling; never a clamp. */
  flag: 'above' | 'within' | 'no-yield';
  words: string;
  /** The bound records whose own value is above the ceiling, each for a reviewer to check its basis. */
  recordsAbove: string[];
}

/** `GET /api/proforma/ceiling-check`: one scenario's yield beside every stored ceiling of its organism on its sugar. */
export interface CeilingCheck {
  scenarioId: string;
  flowsheet: string;
  product: string;
  substrate: string;
  sugarWords: string;
  host: string | null;
  /** The scenario's organism: its host filter, else its yield's records' strains. */
  strains: string[];
  species: string[];
  organismWords: string;
  /** The shelf models of that organism with a route to the product. */
  models: string[];
  yieldBinding: 'records' | 'assumption' | 'artifact' | 'waiting';
  yieldValue: number | null;
  yieldLow: number | null;
  yieldHigh: number | null;
  yieldUnit: string;
  yieldSource: BasisSource | null;
  yieldRecords: number;
  yieldWords: string;
  /** The tool of the artifact the yield came from, when one did (§8.R). */
  yieldTool: string | null;
  rows: CeilingRow[];
  flagged: boolean;
  /** With no ceiling on file: what is missing, and where one is computed. */
  empty: string | null;
  computeAt: string;
  /** Sugars other stored ceilings of these models are on, left aside here. */
  otherSugars: string[];
  notes: string[];
}

export interface HistogramBin {
  low: number;
  high: number;
  count: number;
}

export interface InputSensitivity {
  key: string;
  rho: number;
  sourceKind: string;
}

export interface ProformaGrid {
  dims: { key: string; values: number[] }[];
  msp: (number | null)[];
  costLines: Record<string, (number | null)[]>;
  infeasible: number;
}

export interface ProformaRunResult {
  scenarioId: string;
  artifactId: string;
  provenance: Provenance;
  inputs: ScenarioInput[];
  basePrice: number | null;
  baseCostLines: Record<string, number> | null;
  baseInfeasible: string | null;
  quantiles: Record<string, number>;
  histogram: HistogramBin[];
  sensitivity: InputSensitivity[];
  samples: number;
  feasible: number;
  infeasible: Record<string, number>;
  grid: ProformaGrid;
  readBack: Record<string, number>;
  leavesOut: string[];
  priceBasis: string;
  evidence: Evidence;
  // OF-BLD-019 §2.1 (D1): the base case's tables, read from the one run
  // artifact; ProformaTables says what each holds.
  flowsheet: string | null;
  tablesSource: string | null;
  tea: TeaBreakdown | null;
  streams: StreamRow[];
  units: UnitRow[];
  utilities: UtilityDuties | null;
  diagram: string | null;
  diagramNote: string | null;
  unitOrder: string[];
  tableUnits: Record<string, string>;
}

// ── Proforma's shelf and the run's tables (OF-BLD-019 §2.1) ─────────────
// Mirrors of core/openferment_core/models.py; check:plan diffs the fields.
// The shelf is data (flowsheets/shelf.py, D2), served at
// GET /api/proforma/shelf. A run is one `proforma.run` artifact (D1) whose
// output holds every table below, read by the worker from BioSTEAM's own
// objects. Units are BioSTEAM's: T in K, P in Pa, flows in kg/hr, a unit's
// duties in kJ/hr and power in kW, costs in USD, annual amounts in USD/yr
// (`tableUnits`); UtilityDuties carries the unit the UnitGroup states.

/** One input a shelf flowsheet takes: the ontology fields that bind it, or none for an assumption or a convention. */
export interface FlowsheetInput {
  key: string;
  name: string;
  /** The unit table's family where the unit has one (massConc, yield, volProd, costUSD), else massFlow or fraction. */
  dimension: string;
  unit: string;
  fields: string[];
  kind: 'process' | 'economic' | 'convention';
  note: string;
}

export interface FlowsheetInfo {
  id: string;
  title: string;
  description: string;
  /** The package and version ('biorefineries 2.35.1, cornstover'), or 'this repository'. */
  source: string;
  /** The chemical-set key (`yeast`); null for a general flowsheet. */
  program: string | null;
  /** A published reference biorefinery, run whole on its package's defaults. */
  reference: boolean;
  inputs: FlowsheetInput[];
  outputs: string[];
  priceOutput: string | null;
  priceBasis: string | null;
  leavesOut: string[];
  gridInputs: string[];
  /** A reference biorefinery's own regression test, cited as file::test; its values come from the installed file (PackageRegression). */
  packageTest: string | null;
  /**
   * OF-BLD-020 §6.1 (D11): the kept artifacts a scenario on this flowsheet
   * names besides the flowsheet, by tool (`custom_train_v1`: a `fermos.vessel`
   * design and a `pureos.train_run`); empty for a flowsheet whole on its own.
   */
  builtFrom: string[];
  /**
   * OF-BLD-020 §6.2 (D10): the stream the flowsheet names as its fermenter's
   * broth (its beer), by the id its run's stream table gives it: what a
   * train's inlet takes from a scenario's newest run. Null: it names none.
   */
  brothStream: string | null;
}

// OF-BLD-019 §2.2 (D3) — a reference biorefinery runs whole on its package's
// defaults and is kept as one `proforma.reference` artifact: the package's
// outputs, the quantities its own test asserts as this installation
// computed them (`measured`), the defaults read back (`readBack`), the
// test's values beside them (`regression`, `checks`), and every table a
// `proforma.run` artifact holds. The test's values are parsed from the
// installed test file; none is typed here.

/** One value a package's own test asserts, as its test file writes it. */
export interface RegressionValue {
  /** The expression the test asserts on ('tea.IRR', 'units.get_heating_duty()'). */
  expression: string;
  label: string;
  unit: string;
  package: number;
  rtol: number;
}

/** A reference biorefinery's regression values, read from the package's installed test file. */
export interface PackageRegression {
  package: string;
  file: string;
  test: string;
  values: RegressionValue[];
}

/** One of the package test's values beside what this installation computed. */
export interface RegressionCheck {
  expression: string;
  label: string;
  unit: string;
  measured: number | null;
  package: number;
  rtol: number;
  /** |measured − package| / |package|; null when the package's value is zero. */
  relDiff: number | null;
  within: boolean;
}

/** GET and POST /api/proforma/reference/:id. */
export interface ProformaReference {
  flowsheet: FlowsheetInfo;
  /** The newest stored `proforma.reference` run, or null before the first. */
  artifact: Artifact | null;
  regression: PackageRegression | null;
  simulator: { status: 'cold' | 'starting' | 'ready' | 'failed'; error: string | null };
}

/** One stream of the base case: source and sink unit (null for a feed or a product). */
export interface StreamRow {
  id: string;
  source: string | null;
  sink: string | null;
  phase: string;
  T: number;
  P: number;
  massFlow: number;
  massFlows: Record<string, number>;
  price: number | null;
}

/** One unit operation, in run order. Duties and power are null where the unit has none. */
export interface UnitRow {
  id: string;
  unitClass: string;
  line: string | null;
  order: number;
  ins: string[];
  outs: string[];
  installedCost: number;
  purchaseCost: number;
  heatingDuty: number | null;
  coolingDuty: number | null;
  power: number | null;
}

/** BioSTEAM's UnitGroup totals, each with the unit the UnitGroup states. */
export interface UtilityDuties {
  group: string;
  heating: number;
  heatingUnit: string;
  cooling: number;
  coolingUnit: string;
  electricityConsumption: number;
  electricityConsumptionUnit: string;
  electricityProduction: number;
  electricityProductionUnit: string;
}

/** One line of the price, per year and per unit of the price's basis; the lines sum to the product's revenue. */
export interface TeaLine {
  key: 'feedstock' | 'otherMaterials' | 'utilities' | 'otherVariable' | 'fixedOperating' | 'capitalRecovery' | 'coproductCredits';
  label: string;
  usdPerYear: number;
  perUnit: number | null;
  reads: string;
}

/** The TEA object's own numbers for the base case, read through its attributes. */
export interface TeaBreakdown {
  teaClass: string;
  product: string;
  feedstock: string | null;
  productPrice: number | null;
  basisFlow: number | null;
  basis: string | null;
  operatingHours: number;
  sales: number;
  materialCost: number;
  feedstockCost: number | null;
  otherMaterialCost: number;
  utilityCost: number;
  purchaseCost: number;
  installedEquipmentCost: number;
  FCI: number;
  TCI: number;
  FOC: number;
  laborCost: number | null;
  capitalRecovery: number;
  coproductCredits: number;
  IRR: number | null;
  incomeTax: number | null;
  lines: TeaLine[];
}

/** What a reader takes from a `proforma.run` artifact (proforma.tables_of). */
export interface ProformaTables {
  flowsheet: string | null;
  tablesSource: string | null;
  tea: TeaBreakdown | null;
  streams: StreamRow[];
  units: UnitRow[];
  utilities: UtilityDuties | null;
  /** SVG text when Graphviz's dot was on the path (D8); else null, with the words why and the units in run order. */
  diagram: string | null;
  diagramNote: string | null;
  unitOrder: string[];
  tableUnits: Record<string, string>;
}

// ── pureOS reads the train (OF-BLD-019 §4.1, D1) ────────────────────────
//
// Mirrors models.py. A train is read by the service (pureos.train_of) from
// one `proforma.run` artifact's stream and unit tables; the browser shows it
// and computes nothing. Masses are the product's kg/hr in the run's base case.

/** One unit of a run's train, in run order. */
export interface TrainUnit {
  id: string;
  unitClass: string;
  line: string | null;
  order: number;
  ins: string[];
  outs: string[];
  /** Whether any of its outlets leads on to the product stream. */
  onPath: boolean;
  massIn: number;
  massOut: number;
  /** The product's kg/hr; null when the run names no product. */
  productIn: number | null;
  productOut: number | null;
  productOnward: number | null;
  productLost: number | null;
  /** The outlets that carry product off the path. */
  lostTo: string[];
  /** productOnward / productIn; null, with `note` saying why, when none enters or the unit is off the path. */
  recovery: number | null;
  /** 1 less the product lost here and at every on-path unit before, over all the path delivers or loses. */
  cumulative: number | null;
  note: string | null;
}

/** A run's train as pureOS reads it (`GET /api/pureos/train/:key`). */
export interface Train {
  scenarioId: string | null;
  scenarioName: string | null;
  artifactId: string;
  flowsheet: string | null;
  createdAt: string;
  provenance: Provenance;
  program: string | null;
  tablesSource: string | null;
  productStream: string | null;
  product: string | null;
  /** How the product was read from the run, in words. */
  productBasis: string;
  productOut: number | null;
  productLost: number | null;
  overallRecovery: number | null;
  units: TrainUnit[];
  streams: StreamRow[];
  tableUnits: Record<string, string>;
  /** How many runs of this scenario are on file; the newest is read. */
  runs: number;
  note: string | null;
  /** OF-BLD-020 §5.2: the artifact read, `proforma.run` or `pureos.train_run`; for a train run, the train it ran. */
  tool: string;
  trainId: string | null;
  trainName: string | null;
}

/** One train on file, for pureOS's index (`GET /api/pureos/trains`). */
export interface TrainSummary {
  scenarioId: string | null;
  scenarioName: string | null;
  artifactId: string;
  flowsheet: string | null;
  createdAt: string;
  provenance: Provenance;
  program: string | null;
  product: string | null;
  unitCount: number;
  overallRecovery: number | null;
  runs: number;
  note: string | null;
  /** As Train's (OF-BLD-020 §5.2). */
  tool: string;
  trainId: string | null;
  trainName: string | null;
}

// ── thermosteam answers property questions (OF-BLD-019 §4.2, D9) ───────
//
// A question names a mixture on file, never a number: a stream of a Proforma
// run, or a preset the service fills (`ethanol-water-azeotrope`, or
// `beer-at-titre-of` an ethanol titre record). The answer is one
// `thermo_props` artifact whose `output` is a `ThermoProps`.

/** `POST /api/thermo/props` (and the same question as `GET` query parameters). */
export interface ThermoPropsRequest {
  artifactId?: string | null;
  streamId?: string | null;
  preset?: string | null;
  recordId?: string | null;
}

/** What a `thermo_props` artifact holds: thermosteam's answer for one mixture, in the library's units. */
export interface ThermoProps {
  /** stream, ethanol-water-azeotrope or beer-at-titre-of. */
  kind: string;
  /** The mixture in words. */
  subject: string;
  runArtifactId: string | null;
  streamId: string | null;
  preset: string | null;
  recordId: string | null;
  /** "thermosteam <version>", read in the worker. */
  library: string;
  T: number;
  P: number;
  phase: string;
  /** "given" (the stream's own) or "thermosteam's Stream default". */
  TSource: string;
  PSource: string;
  massFractions: Record<string, number>;
  density: number | null;
  Cp: number | null;
  viscosity: number | null;
  /** Temperatures at the mixture's own pressure. */
  bubblePoint: number | null;
  dewPoint: number | null;
  /** The first bubble's mole fractions. */
  vapourAtBubble: Record<string, number> | null;
  /** The library's unit for each key above. */
  units: Record<string, string>;
  /** A preset's solve: what was found, and how, in words. */
  solved: Record<string, unknown> | null;
  /** A property the library could not compute, with its reason; what the mixture leaves out. */
  notes: string[];
}

// ── A product's properties (OF-BLD-020 §7.1, D12) ──────────────────────
//
// What pureOS's proposer reads about a product: from its sequence, through
// Biopython's ProtParam (one `protparam` artifact), and from its
// thermodynamics, through thermosteam in the Proforma worker (one
// `volatility` artifact). A question names a product by id, never a sequence
// or a number.

/** `POST /api/protparam` and `POST /api/thermo/volatility`: the product, by its id. */
export interface ProductPropertyRequest {
  product: string;
}

/** What a `protparam` artifact holds: Biopython's ProtParam on one sequence, every number the library's. */
export interface ProtParam {
  /** "the sequence of product <id>", "the sequence of record <id>". */
  subject: string;
  product: string | null;
  /** Where the sequence was read, in words. */
  sequenceSource: string;
  /** Residues in the chain. */
  length: number;
  /** "Biopython <version>". */
  library: string;
  molecularWeight: number;
  isoelectricPoint: number;
  /** At 280 nm: every cysteine reduced, and every pair of cysteines a cystine. */
  extinctionReduced: number;
  extinctionCystines: number;
  gravy: number;
  /** The unit of each key above ("" for none). */
  units: Record<string, string>;
  /** How the library computes each, in words. */
  how: Record<string, string>;
  notes: string[];
}

/** What a `volatility` artifact holds: thermosteam's boiling points and whether the pair has a minimum-boiling azeotrope. */
export interface Volatility {
  product: string;
  /** The library's own name for the product, and the partner it is asked with (water). */
  chemical: string;
  partner: string;
  subject: string;
  /** "thermosteam <version>", read in the worker. */
  library: string;
  P: number;
  /** "given", or "thermosteam's Stream default". */
  PSource: string;
  /** The library's normal boiling point (Tb) of each; null when it holds none. */
  boilingPoint: number | null;
  partnerBoilingPoint: number | null;
  /** Which of the two boils lower, the one whose mole fraction is scanned. */
  lighter: string | null;
  /** true: found; false: none on the grid searched; null: not searched, or the library could not say. */
  azeotrope: boolean | null;
  azeotropeMoleFraction: number | null;
  azeotropeMassFraction: number | null;
  azeotropeT: number | null;
  /** The grid searched: the lighter chemical's mole fraction from, to, the points, and the halvings. */
  searched: Record<string, unknown> | null;
  units: Record<string, string>;
  how: string;
  notes: string[];
}

// ── One parameter panel (OF-BLD-020 §2.1, D2–D4) ────────────────────────
//
// Every model family, vessel design, catalogue unit and shelf flowsheet
// declares its parameters once, in Python (`core/openferment_core/params.py`);
// `GET /api/params/{scope}` serves a scope's specs with each value and where
// it came from. A person's change is an `Override`: a named assumption the
// project keeps in its rows (`parameterOverrides`, D3) and a run
// carries; the basis names it as an `assumption`, so the result is `assumed`.
// Bounds are conventions with a written reason (D4): a value outside them is
// kept and flagged in words, never clamped. A model never sets one.

/** The chip a value shows: finer than `BasisSourceKind` (a fit and a simulation are artifacts; a library default is a model source). */
export type ParamOrigin = 'fit' | 'record' | 'artifact' | 'simulation' | 'assumption' | 'model-estimate' | 'convention' | 'library-default' | 'waiting' | 'not-read';

/** What a scope parameterises. */
export type ParamScopeKind = 'fermos-family' | 'fermos-vessel' | 'fermos-forecast' | 'pureos-unit' | 'proforma' | 'library';

/** One parameter as its model, unit or flowsheet declares it. */
export interface ParameterSpec {
  key: string;
  label: string;
  /** As written in the equations, plain Unicode; '' when it has none. */
  symbol: string;
  /** What the symbol means, in words: the panel's Why. */
  gloss: string;
  /** A units.ts family (massConc, yield, volProd, costUSD) or a word. */
  dimension: string;
  /** '' for a share, a dimensionless number or a choice. */
  unit: string;
  min: number | null;
  max: number | null;
  step: number | null;
  scale: 'linear' | 'log';
  group: string;
  /**
   * Ordered: 'fit', 'record:<field id>', 'artifact', 'simulation',
   * 'assumption', 'convention', 'library-default'. The first with a value
   * wins; an Override wins over all of them.
   */
  sourceRule: string[];
  note: string | null;
  /** Required (D4): a physical limit, an ontology plausibility range, or the library's validity range. */
  boundsReason: string;
  /** A parameter chosen from words (a feed profile, a kLa method); null for a number. */
  choices: string[] | null;
  /** The stated convention, when the rule holds 'convention'; its reason is in `note`. */
  convention: number | string | null;
}

/** A parameter's value in one scope, with where it came from. */
export interface ParameterValue {
  key: string;
  /** null while it waits. */
  value: number | string | null;
  low: number | null;
  high: number | null;
  /** null while it waits. */
  source: BasisSource | null;
  origin: ParamOrigin;
  /** Set only when the origin is a fit. */
  identified: boolean | null;
  /** The person's name, when an Override set it. */
  overriddenBy: string | null;
  /** BioSTEAM's default read from its code at import, else null. */
  libraryDefault: number | string | null;
  /** The records behind it, when its origin is records. */
  recordIds: string[];
  /** Words: how many records and their range, or why it waits and which field would bind it. */
  detail: string | null;
  /** The warning in words when the value lies outside the bounds; kept, never clamped. */
  outOfBounds: string | null;
}

/** A person's change to one parameter of one scope: a named assumption, kept here and sent with the run (D3). */
export interface Override {
  scope: string;
  key: string;
  value: number | string;
  low: number | null;
  high: number | null;
  by: string;
  at: string;
  note: string | null;
  /** A person's assumption unless it says otherwise; a model's estimate names the model in `by` (ADR-006). */
  origin?: OverrideOrigin;
}

/** `GET /api/params/{scope}`: a scope's specs with their current values. */
export interface ParamScope {
  scope: string;
  kind: ParamScopeKind;
  title: string;
  specs: ParameterSpec[];
  values: ParameterValue[];
  /** The keys with no source yet. */
  waiting: string[];
  notes: string[];
}

/** `POST /api/params/{scope}/resolve`. Runs nothing. */
export interface ParamResolveRequest {
  overrides: Override[];
  /** A Proforma scenario not yet saved names the shelf flowsheet it runs. */
  flowsheet?: string | null;
  /** A strain filter on the records, as `/api/proforma/bind` takes it. */
  host?: string | null;
  /** The fermOS fits a person chose, by parameter key (artifact ids). */
  fits?: Record<string, string>;
  /** fermOS's vessel scope (OF-BLD-020 §4.1): the aerated design; null is BioSTEAM's own default. */
  vesselType?: 'stirred-tank' | 'bubble-column' | null;
  /**
   * fermOS's family scope (OF-BLD-020 §3.2), bound as a simulation binds: the
   * strain whose records bind (null: every strain the evidence pool holds),
   * the product, the sugar the records must name, the fit a person chose, where
   * the simulation starts ('records', 'fit', 'simulation:<artifact id>'), and
   * the run-length preset.
   */
  strain?: string | null;
  product?: string | null;
  sugar?: string | null;
  fit?: string | null;
  startFrom?: string | null;
  durationPreset?: 'until-sugar-runs-out' | 'fit-length' | null;
  /** pureOS's unit scope (OF-BLD-020 §5.1): the unit's catalogue type, when no train is sent. */
  unitType?: string | null;
  /**
   * pureOS's unit scope (§5.2): the whole train, so per-component keys expand
   * over its chemicals and records bind by its program and product; the scope
   * `pureos:unit:<train id>:inlet` is its inlet. Its typed values are not laid
   * on here: the resolve's `overrides` are.
   */
  train?: TrainSpec | null;
  /** A Proforma scenario on `custom_train_v1` (OF-BLD-020 §6.1): the vessel design and the train run it is built from. */
  vessel?: string | null;
  trainRun?: string | null;
}

export interface ParamResolveResult {
  scope: string;
  values: ParameterValue[];
  waiting: string[];
  /** What the overrides would add to a run's basis, each an `assumption` naming the person. */
  basisInputs: BasisInput[];
  /** A value outside its bounds, in words. */
  warnings: string[];
  /** What the scope's provider says of its values. */
  notes: string[];
}

// ── fermOS's vessel on BioSTEAM (OF-BLD-020 §4.1, D7) ──────────────────

/** POST /api/fermos/vessel. Exactly one of `simulation` and `fit`. */
export interface VesselRequest {
  /** A `fermos.simulation` artifact id. */
  simulation?: string | null;
  /** A `kinetic_fit` or `growth_forecast` artifact id: anaerobic only. */
  fit?: string | null;
  /** The aerated design; null is BioSTEAM's own default. A person's override of `design` says the same, and the two must agree. */
  vesselType?: 'stirred-tank' | 'bubble-column' | null;
  /** A kLa correlation by BioSTEAM's registered name, one its class runs for the design (fermos_vessel's klaMethod); null is the class's own. */
  klaMethod?: string | null;
  /** A person's changes, each a named assumption, scope `fermos:vessel:<id>`. */
  overrides: Override[];
}

/** One line of the design table, read from BioSTEAM's objects. */
export interface VesselDesignRow {
  label: string;
  value: number | string | boolean | null;
  /** BioSTEAM's unit for it; empty for a count or a word. */
  unit: string;
  /** Where it was read: a design_results key, an auxiliary unit, an attribute. */
  readFrom: string;
}

/** The oxygen balance over the batch: the simulated uptake against the vessel's transfer. */
export interface VesselOxygen {
  t: number[];
  our: number[];
  otr: number;
  unit: string;
  /** [[from, to], …] hours the simulated uptake rises above `otr`. */
  short: number[][];
  kLa: number | null;
  kLaNeededAtPeak: number | null;
  kLaUnit: string;
  method: string | null;
  aerated: boolean;
  oxygenBasis: string | null;
  targetUptake: number | null;
  sized: number | null;
  balancedUptake: number | null;
  scale: number;
  cStar: number | null;
  cL: number | null;
  drivingForce: number | null;
  reactionO2KmolPerH: number | null;
  /** OF-BLD-020 §4.R: the oxygen the vessel's reaction consumes as designed, the oxygen the simulation took up per hour of the plant, and BioSTEAM's aeration floor, each kmol h⁻¹. */
  scaledO2KmolPerH: number | null;
  simulatedO2KmolPerH: number | null;
  floorKmolPerH: number | null;
}

/** BioSTEAM's duty as it found it, beside a cross-check from the oxygen the simulation took up at a stated convention (D7, §4.R). */
export interface VesselHeat {
  bst: number;
  convention: number | null;
  conventionNote: string;
  unit: string;
  /** 'heats-of-formation' or 'forced-per-oxygen' (a person's Q_O2_consumption times the oxygen consumed); null on a design kept before §4.R. */
  method: string | null;
  consumedKmolPerH: number | null;
  /** The oxygen the convention's estimate rests on (the simulation's), kmol h⁻¹. */
  oxygenKmolPerH: number | null;
  /** BioSTEAM's duty in words: how it was found, and whose heat per oxygen when a person forced one. */
  dutyNote: string | null;
}

export interface VesselCostItem {
  purchase: number;
  installed: number;
}

/** BioSTEAM's own cost correlations, read; nothing summed here. */
export interface VesselCost {
  purchase: number;
  installed: number;
  byItem: Record<string, VesselCostItem>;
  /** USD per hour. */
  utility: number;
  costIndex: number;
  costIndexYear: number | null;
  note: string;
}

/** POST /api/fermos/vessel: one `fermos.vessel` artifact, read. */
export interface VesselDesign {
  artifactId: string;
  provenance: Provenance;
  createdAt: string;
  source: string;
  sourceTool: string;
  aerobic: boolean;
  unitClass: string;
  unitId: string;
  vesselType: string | null;
  design: VesselDesignRow[];
  /** null for an anaerobic vessel, and `oxygenNote` says so. */
  oxygen: VesselOxygen | null;
  oxygenNote: string | null;
  heat: VesselHeat;
  cost: VesselCost;
  parameters: ParameterValue[];
  used: Record<string, number | string | boolean | null>;
  scale: Record<string, unknown>;
  reaction: Record<string, unknown>;
  flags: string[];
  versions: Record<string, string>;
  /** The design as one citable value with its basis: its id is the artifact's, as fermos_vessel returns it. */
  evidence: Evidence;
}

/** GET /api/fermos/vessels: one kept `fermos.vessel` artifact. */
export interface VesselSummary {
  artifactId: string;
  provenance: Provenance;
  createdAt: string;
  source: string;
  sourceTool: string;
  unitClass: string;
  vesselType: string | null;
  vessels: number | null;
  volume: number | null;
  installed: number | null;
}

// ── fermOS simulates (OF-BLD-020 §3.1, D1, D5) ─────────────────────────
//
// A model family (`core/openferment_core/kinetics.py`) is code with its
// equations in its docstring and its parameters declared as
// `ParameterSpec`s; a simulation resolves them with their sources, integrates
// on scipy, and keeps one `fermos.simulation` artifact whose basis names
// every parameter, start value and override. A person's override makes it
// `assumed`; nothing here is computed in the browser.

/** `GET /api/fermos/families`: a model family as the panel shows it. */
export interface FamilyInfo {
  id: string;
  title: string;
  /** One plain line: what it is. */
  what: string;
  /** Its equations, plain Unicode, as its docstring writes them. */
  equations: string;
  states: string[];
  /** 'g L⁻¹' for a concentration, 'L' for V. */
  stateUnits: Record<string, string>;
  /** A socket is declared with its parameters and refuses to run. */
  socket: boolean;
  specs: ParameterSpec[];
  /** The panel's groups this family's specs fall into, in order. */
  groups: string[];
}

/** `POST /api/fermos/simulate`. */
export interface SimulationRequest {
  family: string;
  strain?: string | null;
  product?: string | null;
  sugar?: string | null;
  /** A person's changes, each an Override of scope `fermos:family:<family>`. */
  overrides?: Override[];
  fitArtifact?: string | null;
  /** 'records', 'fit', or 'simulation:<artifact id>'. */
  startFrom?: string;
  durationPreset?: 'until-sugar-runs-out' | 'fit-length';
  /**
   * A parameter bound to exactly these records of the evidence pool, by spec
   * key (OF-BLD-020 §3.4, D13): each must be in the pool, carry a field the
   * parameter binds from, pass the aggregate gate and convert into its unit,
   * or the request is refused in words. Ids, never values.
   */
  recordsByParam?: Record<string, string[]>;
}

/**
 * `GET /api/fermos/bind` (OF-BLD-020 §3.2): a family's parameters bound for a
 * strain, product and sugar from a fit, the records, a kept simulation and the
 * conventions, starting no integration.
 */
export interface FermosBinding {
  values: ParameterValue[];
  /** The keys a simulation would refuse for; each value's detail names the field that would bind it. */
  waiting: string[];
  /** What the family would refuse these values for though nothing waits (§8.R), else null. */
  refused: string | null;
  /** What bound from where: the evidence pool's papers, whose records, the sugar, the fit, the kept simulation. */
  notes: string[];
}

/** OUR(t) = qO2·X on the time course's hours; its peak read on the solver's own steps. */
export interface OxygenUptake {
  t: number[];
  value: number[];
  unit: string;
  peak: number;
  peakH: number | null;
  /** Why it is zero, when the culture is anaerobic. */
  note: string | null;
}

export interface MassBalance {
  /** The larger relative error of the two checks. */
  closure: number;
  ok: boolean;
  note: string;
}

/** Yp/s beside the newest stored geneOS ceiling of one host model on the sugar: read, never clamped. */
export interface SimulationCeilingRow {
  modelId: string;
  modelName: string;
  match: 'strain' | 'species';
  matchWords: string;
  artifactId: string;
  provenance: Provenance;
  ceilingGPerG: number;
  ypsGPerG: number | null;
  yieldAchievedGPerG: number | null;
  above: boolean;
  words: string;
}

export interface SimulationCeiling {
  product: string;
  sugar: string;
  strain: string;
  rows: SimulationCeilingRow[];
  flagged: boolean;
  /** Why no row, in words. */
  empty: string | null;
  /** Where a ceiling is computed (geneOS → Model). */
  computeAt: string;
}

/** chemostat_v1's steady state and washout. */
export interface SteadyState {
  washout: boolean;
  dilutionRate: number;
  /** The general washout rate, μ(Sf, P = 0) − kd, and D5's expression. */
  dWashout: number;
  dWashoutD5: number;
  X: number;
  S: number;
  P: number;
  /** D·P at the steady state; null at washout. */
  productivity: number | null;
  words: string;
  /** The most μ(S, P = 0) − kd reaches over S from 0 to Sf: no culture holds at or above it (OF-BLD-020 §3.R). */
  dWashoutMax: number | null;
  /** A culture holds and washout is stable too: which one a run reaches depends on where it starts. */
  bistable: boolean;
  /** Which steady state this run's path reached by its end; null while it is still on its way to one. */
  reached: 'culture' | 'washout' | null;
}

/** One kept `fermos.simulation` artifact as every reader reads it. */
export interface SimulationResult {
  artifactId: string;
  provenance: Provenance;
  family: string;
  title: string;
  strain: string | null;
  product: string | null;
  sugar: string | null;
  parameters: ParameterValue[];
  start: ParameterValue[];
  /** { t: hours, <state>: values } in `units`. */
  series: Record<string, number[]>;
  units: Record<string, string>;
  our: OxygenUptake;
  /** The state where the integration ended, and its hour as `t`. */
  end: Record<string, number>;
  sugarRunsOutH: number | null;
  harvestH: number;
  /** The product (the store, for storage_v1) at harvest, g L⁻¹. */
  finalTitre: number | null;
  /** Product made over sugar used to harvest, g g⁻¹. */
  yieldAchieved: number | null;
  /** The final titre over the harvest hour, g L⁻¹ h⁻¹. */
  productivity: number | null;
  massBalance: MassBalance;
  ceiling: SimulationCeiling | null;
  flags: string[];
  aerobic: boolean;
  steadyState: SteadyState | null;
  notes: string[];
  basis: ComputedBasis;
}

/** `GET /api/fermos/simulations`: one kept simulation, newest first. */
export interface SimulationSummary {
  artifactId: string;
  family: string;
  title: string;
  strain: string | null;
  product: string | null;
  sugar: string | null;
  finalTitre: number | null;
  harvestH: number | null;
  createdAt: string;
  provenance: Provenance;
}

// ── The harvest stream (OF-BLD-020 §6.2, D10) ───────────────────────────
//
// A kept simulation's broth at an hour, read from the series the artifact
// keeps (`GET /api/fermos/harvest`): nothing is integrated again and nothing
// is kept. A train's simulation inlet reads its composition through the
// same read, so the broth that leaves fermOS is the stream that enters pureOS.

/** Where the hour a harvest is read at comes from. */
export type HarvestHourSource = "the simulation's harvest hour" | "a person's hour";

/** One state of the simulation at the hour read, in the unit it keeps. */
export interface HarvestState {
  /** The family's state: X (cells), S (sugar), P (product), V, N, Q. */
  state: string;
  value: number;
  unit: string;
}

/** `GET /api/fermos/harvest`: a kept simulation's broth at an hour. */
export interface FermosHarvest {
  artifactId: string;
  family: string;
  strain: string | null;
  product: string | null;
  sugar: string | null;
  provenance: Provenance;
  /** The hour asked: the simulation's own harvest hour, or a person's. */
  asked: number;
  hourSource: HarvestHourSource;
  /** Why that hour, in words. */
  how: string;
  /** The kept point the states are read at, and whether it is the hour asked. */
  hour: number;
  exact: boolean;
  /** How the states were read, in words (the kept point, or the nearest one, and why). */
  read: string;
  /** The simulation's own harvest hour, and the last hour it keeps. */
  harvestH: number;
  runEndH: number;
  /** Every state the simulation keeps a series of, in its family's order. */
  states: HarvestState[];
  /** What the family does not model is absent from the broth, in words. */
  absent: string;
}

// ── pureOS's unit catalogue (OF-BLD-020 §5.1, D8) ──────────────────────
//
// Each entry is one unit type a train can hold: a BioSTEAM class, or one of
// the three in-house units BioSTEAM lacks, with every parameter its
// constructor takes either a ParameterSpec or named as not offered, with why.
// Its id is a `UNIT_OPERATIONS` id. Served by `GET /api/pureos/catalogue`
// (from data, no simulator) and `GET /api/pureos/catalogue/{id}/specs`
// (BioSTEAM's defaults, read in the Proforma worker).

/** Where a unit sits in a train, fermenter to product. */
export type UnitStage =
  | 'harvest'
  | 'disruption'
  | 'clarification'
  | 'concentration'
  | 'capture'
  | 'polish'
  | 'formulation'
  | 'drying'
  | 'utility';

/** One inlet or outlet of a catalogue unit, in words. */
export interface UnitPort {
  side: 'in' | 'out';
  index: number;
  name: string;
  what: string;
  /** An outlet the product goes on by, by default. */
  onward: boolean;
  /** An inlet's stream: from the unit before, one the train supplies beside the line, or one the unit sizes itself. */
  source: 'upstream' | 'side' | 'unit' | null;
  /** Takes any number of streams here, which the class mixes. */
  many: boolean;
}

/** A constructor parameter the panel does not offer, and why. */
export interface NotOffered {
  name: string;
  why: string;
}

/** What a unit needs set before it runs: one of the alternatives, each a list of keys that must all hold a value. */
export interface UnitNeed {
  alternatives: string[][];
  why: string;
}

/** A catalogue entry without its specs. */
export interface UnitType {
  id: string;
  name: string;
  line: string;
  stage: UnitStage;
  biosteamClass: string | null;
  inhouseClass: string | null;
  insOuts: UnitPort[];
  /** Whether BioSTEAM costs it; the in-house units have no cost model. */
  costModel: boolean;
  notes: string[];
  notOffered: NotOffered[];
  needs: UnitNeed[];
  /** The vocabulary ids it stands for beside its own. */
  maps: string[];
  specCount: number;
}

/** A parameter's default as the class gives it, read from its code, and where. */
export interface UnitDefault {
  key: string;
  value: number | string | null;
  readFrom: string;
}

/** How one spec reaches the class; a template key is expanded per component or per effect. */
export interface UnitParamMap {
  key: string;
  name: string;
  via: 'argument' | 'attribute';
  per: 'component' | 'effect' | null;
  how: string | null;
}

/** An entry's specs with the choices and bounds its class gives, each default as read, and how each reaches it. */
export interface UnitSpecs {
  id: string;
  biosteamClass: string | null;
  inhouseClass: string | null;
  specs: ParameterSpec[];
  defaults: UnitDefault[];
  params: UnitParamMap[];
  notOffered: NotOffered[];
  needs: UnitNeed[];
  /** The chemicals a chemical-valued parameter chooses from: the yeast program's set, until a train names its own. */
  chemicals: string[];
  versions: Record<string, string>;
  notes: string[];
}

// ── pureOS builds the train (OF-BLD-020 §5.2, D9, D10, E.2‴) ──────────
//
// A train is data: an inlet, then units in order, each a catalogue type with
// what a person typed (Override-shaped, D3), the records named for a
// parameter, each outlet's routing and optionally a shelf flowsheet's own unit
// to read its values from. The worker builds and runs it; one
// `pureos.train_run` artifact keeps it; `pureos.train_of` reads it.

/** A value a person typed for one parameter of a train's unit or inlet: an Override without scope and key. */
export interface TrainParam {
  value: number | string;
  low?: number | null;
  high?: number | null;
  by: string;
  at: string;
  note?: string | null;
}

/** Where a train's broth comes from (D10). */
export interface TrainInlet {
  kind: 'simulation' | 'run-stream' | 'typed';
  /** A `fermos.simulation`, or a run (`proforma.run`, `proforma.reference`, `pureos.train_run`) whose stream it is; null when typed. */
  ref?: string | null;
  /** The run's stream (run-stream alone). */
  streamId?: string | null;
  /** A `fermos.vessel` design of the simulation, which gives the broth flow (simulation alone). */
  vessel?: string | null;
  /** The inlet's typed values by key (broth_flow, harvest_hour, conc.<chemical>, T, P). */
  params?: Record<string, TrainParam>;
}

/** A shelf flowsheet's own unit whose values a train's unit takes, read in the worker, never typed. */
export interface TrainUnitReadFrom {
  flowsheet: string;
  unit: string;
}

/** One unit of a train, in order (D9). */
export interface TrainUnitSpec {
  /** The BioSTEAM unit id: a letter, then letters, digits or underscores. */
  id: string;
  /** A catalogue id. */
  type: string;
  params?: Record<string, TrainParam>;
  /** Outlet name → 'onward' | 'waste' | 'recycle:<earlier unit id>'; one not named takes the catalogue's default. */
  outlets?: Record<string, string>;
  /** Record ids named for a parameter, by key. */
  records?: Record<string, string[]>;
  readFrom?: TrainUnitReadFrom | null;
}

/** A train as data (D9), kept whole in the project's rows and sent with a run. */
export interface TrainSpec {
  id: string;
  name: string;
  program: string;
  /** A product id; thermo's CHEMICALS names the library chemical it is. */
  product: string;
  inlet: TrainInlet;
  units: TrainUnitSpec[];
}

/** `POST /api/pureos/train/validate`: every refusal at once; runs nothing. `POST /api/pureos/train/check` answers the same shape with everything a run would refuse (OF-BLD-020 §5.3). */
export interface TrainValidation {
  ok: boolean;
  refusals: string[];
  /** The same refusals by their place: a unit's id, `inlet`, or `train`. */
  places: Record<string, string[]>;
}

/** `POST /api/pureos/train/run`. */
export interface TrainRunRequest {
  train: TrainSpec;
  /** Overrides of `pureos:unit:<train id>:<unit id | inlet>`, each replacing the train's value of its key. */
  overrides?: Override[];
  by?: string | null;
}

export interface StreamImpurity {
  chemical: string;
  massFraction: number;
}

/** One stream of a train run: the product's mass share and its largest other components. */
export interface StreamPurity {
  stream: string;
  massFlow: number;
  productFraction: number | null;
  impurities: StreamImpurity[];
}

export interface TrainPurity {
  /** The chemical traced. */
  product: string;
  productStream: string | null;
  productFraction: number | null;
  streams: StreamPurity[];
  /** How many of each stream's largest other components are named (a reading convention). */
  impuritiesShown: number;
  note: string;
}

/** One unit's cost as BioSTEAM gives it, or why there is none. */
export interface TrainUnitCost {
  unit: string;
  type: string;
  unitClass: string;
  costModel: boolean;
  purchaseCost: number | null;
  installedCost: number | null;
  /** BioSTEAM's purchase cost by item, USD. */
  items: Record<string, number>;
  note: string | null;
}

/** What a train run's inlet was and where it came from (D10). */
export interface TrainInletRead {
  kind: 'simulation' | 'run-stream' | 'typed';
  ref: string | null;
  refTool: string | null;
  streamId: string | null;
  vessel: string | null;
  chemicals: string[];
  /** g L⁻¹ by chemical, water aside (a simulation's harvest, or typed). */
  concentrations: Record<string, number> | null;
  /** kg/hr by chemical as the worker built the stream, water included. */
  flows: Record<string, number>;
  water: number | null;
  waterNote: string | null;
  /** m³/hr. */
  brothFlow: number | null;
  harvestHour: number | null;
  T: number;
  P: number;
  phase: string;
  absent: string | null;
  notes: string[];
}

/** One unit's parameters as its run's basis holds them. */
export interface TrainUnitParameters {
  unit: string;
  type: string;
  unitClass: string;
  values: ParameterValue[];
}

/** `POST /api/pureos/train/run`: the one `pureos.train_run` artifact, read. */
export interface TrainRun {
  artifactId: string;
  provenance: Provenance;
  createdAt: string;
  spec: TrainSpec;
  train: Train;
  purity: TrainPurity;
  costs: TrainUnitCost[];
  inlet: TrainInletRead;
  parameters: TrainUnitParameters[];
  notes: string[];
  flags: string[];
  basis: ComputedBasis;
  /** The run's own tables beside the train (OF-BLD-020 §5.3): the unit table, the utilities, the diagram or the words why not and the units in run order. */
  units: UnitRow[];
  utilities: UtilityDuties | null;
  diagram: string | null;
  diagramNote: string | null;
  unitOrder: string[];
}

/** `POST /api/pureos/train/from-run` (OF-BLD-020 §5.3): a kept run's units read into a train. */
export interface TrainFromRunRequest {
  /** A `proforma.run`, `proforma.reference` or `pureos.train_run` artifact. */
  artifactId: string;
  /** The id the train takes; by default `from-<artifact id>`. */
  trainId?: string | null;
}

/** A unit of the run the train does not take, and why. */
export interface TrainUnmapped {
  unitId: string;
  unitClass: string;
  why: string;
}

/** A run's train as data, what it leaves out, what it says, and its structural refusals (validate's). */
export interface TrainFromRun {
  train: TrainSpec;
  unmapped: TrainUnmapped[];
  notes: string[];
  refusals: string[];
}

/**
 * A train a model built with `pureos_build` or `pureos_write` (OF-BLD-020
 * §5.4), kept on the service as rows of `trains` marked `kept`:
 * `GET /api/pureos/trains-kept`. A person's trains are the project's rows the
 * Builder keeps (`trains` marked `made`).
 */
export interface KeptTrain {
  spec: TrainSpec;
  /** A model, always. */
  agent: 'model';
  /** The model id that made it. */
  madeBy: string;
  effort: string | null;
  /** The ask that made it; null for a call from the endpoint or the MCP server. */
  askId: string | null;
  /** ISO 8601, UTC. */
  at: string;
  updatedAt: string;
}

/** `core/data/pureos-trains.json`. */
export interface KeptTrains {
  trains: KeptTrain[];
}

// ── pureOS proposes a train (OF-BLD-020 §7.2, D12) ──────────────────────

/** `POST /api/pureos/propose`: ids and words, never a number. */
export interface ProposeRequest {
  /** A products catalogue id, or a product thermosteam's library is asked about by name (ethanol). */
  product: string;
  /** A geneOS host (strain) id: the cells the product is made in. */
  host: string;
  /** A kept fermOS simulation's id, or `<run artifact id>/<stream id>`; none, and the inlet is typed. */
  inletRef?: string | null;
}

/** Why one unit of a proposal is there: its rule, the property it read and the artifact that holds it. */
export interface ProposalReason {
  unitId: string;
  rule: string;
  /** boilingPoint, azeotrope, molecularWeight, isoelectricPoint (an artifact's), or class, location (the products catalogue's). */
  property: string;
  /** Null when the products catalogue states the property. */
  artifactId: string | null;
  /** Words, with no number in them. */
  words: string;
}

/** A property the rules needed and nothing holds, and why. */
export interface ProposalMissing {
  property: string;
  why: string;
}

/**
 * A train proposed by written rules, or none with what is missing. Named apart
 * from `Proposal`, a write a model proposed at a gate (OF-BLD-015 §7.4).
 */
export interface TrainProposal {
  product: string;
  host: string;
  program: string | null;
  /** protein, small molecule, polymer; null when nothing states it. */
  productClass: string | null;
  /** Null when nothing is proposed; every unit's params and records are empty. */
  train: TrainSpec | null;
  /** One a unit, in the train's order. */
  reasons: ProposalReason[];
  missing: ProposalMissing[];
  /** The property artifacts read (volatility, protparam), by id. */
  artifacts: string[];
  notes: string[];
}

// ── SFF flowsheet records (execution prompt §7.5; ADR-003) ─────────────
//
// Mirrored from core/openferment_core/models.py; `pnpm check:plan` pairs
// each. Stage 7 generates these from the Pydantic models.

/** How a record came: a run of this project, one of the toolkit's reference files, or any other file. */
export type SFFOrigin = 'run' | 'library' | 'imported';

/** One result of the toolkit's validator that did not pass. */
export interface SFFFinding {
  checkId: string;
  severity: string;
  status: string;
  message: string;
  path: string;
}

/** The toolkit's verdict against the schema it ships. */
export interface SFFValidation {
  valid: boolean;
  schemaVersion: string;
  summary: Record<string, Record<string, number>>;
  findings: SFFFinding[];
}

/** One criterion of the toolkit's completeness registry, as it scored. */
export interface SFFCriterion {
  id: string;
  category: string;
  criticality: string;
  weight: number;
  representable: boolean;
  status: string;
  score: number | null;
  message: string;
  missing: string[];
}

/** How much of what BioSTEAM needs to rebuild, simulate and cost the plant the file states. */
export interface SFFCompleteness {
  score: number | null;
  representableScore: number | null;
  categories: Record<string, number | null>;
  criticalities: Record<string, number | null>;
  criteria: SFFCriterion[];
  sffVersion: string | null;
  recipe: Record<string, unknown>;
  report: string;
}

/** One of the toolkit's tags: earned (null: not evaluated), declared, and what blocks it. */
export interface SFFTag {
  earned: boolean | null;
  declared: boolean;
  blocking: string[];
}

/** A unit operation: a node of the graph, `rank` its column counted from the feeds. */
export interface SFFNode {
  id: string;
  type: string;
  method: string | null;
  rank: number;
}

/** A stream from one unit to another. */
export interface SFFEdge {
  id: string;
  source: string;
  sink: string;
  massFlow: number | null;
}

/** A stream crossing the plant's boundary: a feed entering `unit`, or a product leaving it. */
export interface SFFBoundary {
  id: string;
  unit: string;
  name: string | null;
  massFlow: number | null;
  price: number | null;
}

/** The flowsheet as the UI draws it, read from the file's units and streams. */
export interface SFFGraph {
  nodes: SFFNode[];
  edges: SFFEdge[];
  feeds: SFFBoundary[];
  products: SFFBoundary[];
  dangling: string[];
  massFlowUnit: string;
}

/** An SFF flowsheet record (GET /api/flowsheets/{id}); `graph` is left out of a listing. */
export interface SFFFlowsheet {
  id: string;
  title: string;
  origin: SFFOrigin;
  source: string;
  sffVersion: string | null;
  sha256: string;
  bytes: number;
  simulator: string | null;
  runArtifactId: string | null;
  libraryId: string | null;
  units: number;
  streams: number;
  validation: SFFValidation;
  completeness: SFFCompleteness;
  tags: Record<string, SFFTag>;
  graph: SFFGraph | null;
  toolkit: string;
  createdBy: string;
  createdAt: string;
}

// ── Engine runs (execution prompt §7.4; engine/runs.py) ────────────────

export type RunStatus = 'done' | 'refused';

/** One input of an engine run: its name, and its value as a quantity with its origin (ADR-006). */
export interface RunInput {
  name: string;
  quantity: Quantity;
}

/** The SFF file a run wrote: its flowsheet record and what the toolkit said of it. */
export interface RunSFF {
  recordId: string;
  valid: boolean;
  score: number | null;
  tags: string[];
}

/** One engine run in a project: a row of `runs` (GET /api/runs). */
export interface EngineRun {
  /** Its computation's id: the artifact id of its basis. */
  id: string;
  plant: string;
  configuration: string | null;
  status: RunStatus;
  tool: string;
  toolVersion: string;
  inputs: RunInput[];
  /** The artifact's, computed on its basis; null for a refused run. */
  provenance: Provenance | null;
  artifactId: string | null;
  /** The price, a flowsheet's own outputs, and how the package's test held it. */
  outputs: Record<string, unknown>;
  versions: Record<string, string>;
  sff: RunSFF | null;
  /** Why no SFF file could be written, in the toolkit's or the worker's words. */
  sffRefused: string | null;
  /** The plant's own words, for a refused run. */
  refused: string | null;
  /** The study scenario that asked for it first. */
  scenarioId: string | null;
  by: string;
  at: string;
  durationMs: number | null;
}

/** GET /api/runs/{id}: a run, its computation, its SFF record, and its parameters as the panel reads them. */
export interface RunReport {
  run: EngineRun;
  artifact: Artifact | null;
  flowsheet: SFFFlowsheet | null;
  /** Each value the run's own, with its origin; null for a refused run. */
  parameters: ParamScope | null;
}

// ── Studies (execution prompt §7.2, §9.1 step 5; studies/) ─────────────

/** One value a scenario sets: the parameter's key, and a quantity whose origin is a person's assumption or a model's estimate. */
export interface ScenarioValue {
  key: string;
  quantity: Quantity;
}

/** POST /api/studies/scenarios. */
export interface ScenarioCreate {
  title: string;
  plant: string;
  configuration?: string | null;
  values: ScenarioValue[];
  note?: string | null;
  by: string;
}

/** A study's scenario: a plant, its configuration and the values it sets, and the engine runs made of it. */
export interface StudyScenario {
  id: string;
  kind: 'engine';
  title: string;
  plant: string;
  configuration: string | null;
  values: ScenarioValue[];
  note: string | null;
  /** Oldest first; a refused run's receipt among them. */
  runIds: string[];
  by: string;
  at: string;
}

/** Who asks: a run of a scenario, a lock. */
export interface StudyRequest {
  by: string;
}

/** POST /api/studies/comparisons: the runs in the order the comparison reads them (each change is reckoned from the first). */
export interface ComparisonCreate {
  title: string;
  runIds: string[];
  by: string;
}

/** A comparison of engine runs, under the id of the `study.comparison` artifact that computes it. */
export interface StudyComparison {
  id: string;
  title: string;
  runIds: string[];
  artifactId: string;
  /** The weakest of the runs' (ADR-006). */
  provenance: Provenance;
  by: string;
  at: string;
}

/** GET /api/studies/comparisons/{id}: the comparison and its artifact (runs, rows, values). */
export interface ComparisonReport {
  comparison: StudyComparison;
  artifact: Artifact;
}

/** One output of an engine run a runbook predicts: `outputs.<key>` or `price.<key>`, and what the bench calls it. */
export interface PredictedOutput {
  output: string;
  label: string;
}

/** POST /api/studies/runbooks: a runbook predicting outputs of one engine run, in its units, measured at harvest. */
export interface RunbookCreate {
  title: string;
  runId: string;
  predict: PredictedOutput[];
  by: string;
}
