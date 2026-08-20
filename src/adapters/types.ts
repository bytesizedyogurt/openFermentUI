/**
 * The adapter seam — the five interfaces the production servers plug into.
 *
 * `src/data/source.ts` is the seam for the CORPUS COLLECTIONS: seven arrays,
 * one synchronous surface, two backends. This module is the seam for the
 * SUBSYSTEMS that will answer over a network — BioRepo, geneOS, fermOS,
 * Proforma and the Guild — and it is deliberately a different shape, for one
 * reason stated at length in `source.ts`: that surface is synchronous because
 * nineteen files read those collections as plain arrays and two derive from
 * them at module scope. Nothing reads these five yet, so there is nothing to
 * hold synchronous, and a synchronous interface cannot grow latency later
 * without touching every caller.
 *
 * ── EVERY METHOD IS ASYNC ─────────────────────────────────────────────────
 * Including the ones the fixture answers from an array it already holds. That
 * is the point. The fixture has no latency; a corpus server, a COBRApy solve
 * and a BioSTEAM cash flow all do. `Promise<T>` costs a caller one `await`
 * today and saves rewriting every call site the day the answer arrives over a
 * wire.
 *
 * ── EVERY RESPONSE CARRIES VERSIONING ─────────────────────────────────────
 * See `ResponseMeta`. A trace recorded without it cannot be replayed, and the
 * time to add it is before there is anything to replay.
 *
 * ── WHAT MAY BE DECLARED HERE ─────────────────────────────────────────────
 * Entity types come from `@/data/types`, which is GENERATED from the Pydantic
 * models in `packages/core`. Nothing in this file redeclares one, and nothing
 * in this file may: `check:types` polices the generated file, and a
 * hand-written twin of a generated entity is the exact failure this migration
 * exists to prevent (CLAUDE.md, "the one rule").
 *
 * What IS declared here is transport shape — request objects, the response
 * envelope, and a small number of payloads for capabilities that have no
 * Pydantic model yet because they have no implementation yet
 * (`WhitespaceRegion`, `GuildChapter`, `Seal`, `FluxPrediction`). Each is
 * marked. When the server that produces one exists, ITS model becomes
 * canonical and the TypeScript is generated like everything else; these are
 * placeholders for a wire format, not a second home for an entity that already
 * has one. Where a shape can be DERIVED from an existing one it is derived
 * (`CostModelSummary`, `SensitivityBar`) rather than retyped, so the two
 * cannot drift.
 */
import type {
  CostModel,
  DesignRecord,
  ExtractionRecord,
  FieldId,
  JobStage,
  JobStatus,
  Paper,
  Patent,
  PublicationStatus,
  RunOutcome,
  Scenario,
  ScopeHit,
  Strain,
} from '@/data/types';
import type { CorpusSearchOptions, CorpusSearchResult } from '@/data/source';
// The gold-set plan's row type, imported rather than restated — see
// `GoldSetPlanEntry`'s own docstring, and `CorpusAdapter.getGoldSetPlan` for
// why BioRepo is the subsystem that serves it.
import type { GoldSetPlanEntry } from '@/data/runOutputs';
import type { EvaluatedPoint } from '@/engine/grids';
// `PlantResult` and `deriveSensitivity` are the TypeScript bioSTEAM port's
// shapes. They are imported rather than restated for the same reason as the
// generated entities: one definition. When the plant solve moves to BioSTEAM
// proper, `PlantResult` becomes a generated type and only these two import
// lines change.
import type { PlantResult, deriveSensitivity } from '@/engine/plant';
// The job model is `src/sim/jobs.ts`'s, reused rather than re-invented — see
// `ProcessAdapter.submitEvaluation`. That file is retired in the last
// migration phase; its three INTERFACES (`PacedJob`, `JobPosition`,
// `JobRunner`) are what its own header says has to survive, and this module is
// where they land when it goes. Until then the import points at the one
// declaration, so a runner written against the store and a runner written
// against this seam cannot disagree about what a position is.
import type { JobPosition, JobRunner } from '@/sim/jobs';

export type { JobPosition, JobRunner };

// ── The response envelope ─────────────────────────────────────────────────

/**
 * The versioning every response carries.
 *
 * A response without this is a fact with no way back to what produced it. That
 * matters before it looks like it matters: the traces worth replaying are the
 * ones recorded early, when the servers are still moving, and a trace that
 * cannot name the corpus it was answered from is a screenshot.
 */
export interface ResponseMeta {
  /**
   * Build identifier of whatever answered. Under the fixture backend it begins
   * `fixture-`, and that prefix is load-bearing: it says no server was
   * involved, so a trace carrying it cannot be mistaken for a server trace.
   */
  serverVersion: string;
  /**
   * Identifier of the corpus revision the answer was computed against.
   *
   * A real server returns something immutable that IT holds — a git commit of
   * `data/corpus`, a Postgres transaction/snapshot id, a digest written by the
   * exporter — because only the server knows what it served. The fixture
   * derives one from the corpus contents (see `fixture/meta.ts`), which is the
   * nearest honest equivalent and, unlike a constant, actually changes when
   * the corpus does.
   */
  corpusSnapshotId: string;
  /**
   * Version of the model or engine that produced the payload, when one did.
   *
   * ABSENT MEANS NO MODEL RAN — a corpus read, a lookup — not "version
   * unknown". Anything computed (a tier cascade, a plant solve, a flux
   * prediction) must name what computed it.
   */
  modelVersion?: string;
}

/**
 * A payload plus its provenance-of-answer.
 *
 * `notice` follows the rule `CorpusSearchResult.method` already sets in
 * `src/data/source.ts`: where the shape of an answer cannot show what produced
 * it, the statement travels in the same object, never separately. It is how an
 * empty payload says whether it means "nothing matched" or "nothing computed
 * this" — an empty array that looks like an answer is worse than a stub that
 * says it is one.
 */
export interface AdapterResponse<T> extends ResponseMeta {
  data: T;
  /**
   * One sentence, written for a reader rather than a developer, present only
   * when the payload alone would mislead. Callers that render a payload with a
   * notice on it must render the notice.
   */
  notice?: string;
}

// ── Failure ───────────────────────────────────────────────────────────────
//
// Two classes, because there are two different things a backend can mean by
// "no". Both are declared here rather than in either backend: how a method
// fails is part of the contract, not an implementation detail of one side.

/**
 * The method exists in the contract and this backend has no implementation of
 * it yet. Thrown by everything under `mcp/`.
 */
export class NotImplementedError extends Error {
  readonly adapter: string;
  readonly method: string;
  constructor(adapter: string, method: string, detail?: string) {
    super(
      `openFerment adapters: ${adapter}.${method}() is not implemented by the MCP backend.` +
        (detail ? ` ${detail}` : ''),
    );
    this.name = 'NotImplementedError';
    this.adapter = adapter;
    this.method = method;
  }
}

/**
 * The backend could return something and declines to, because the only answer
 * available would have to be manufactured.
 *
 * This is a narrower thing than "not implemented" and a deliberate one. The
 * fixture hands back what it was given (`writeRecord`, `submitDeposit`) and
 * computes what it can compute; it refuses only where answering would mean
 * minting an artifact that carries authority nobody granted. `search()` in
 * `src/data/source.ts` rejects for the same reason it gives there — a visible
 * failure beats an answer that cannot be told from a real one.
 */
export class AdapterRefusal extends Error {
  readonly adapter: string;
  readonly method: string;
  constructor(adapter: string, method: string, reason: string) {
    super(`openFerment adapters: ${adapter}.${method}() refused — ${reason}`);
    this.name = 'AdapterRefusal';
    this.adapter = adapter;
    this.method = method;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// 1. CorpusAdapter — BioRepo
// ══════════════════════════════════════════════════════════════════════════

/** Filters over the record set. Every member is optional; absent means "any". */
export interface RecordQuery {
  paperId?: string;
  field?: FieldId;
  /** Strain id, matched against `ExtractionRecord.organism`. */
  organism?: string;
  /** Ids to fetch directly, e.g. a design's `consumedRecordIds`. */
  ids?: readonly string[];
}

/** A configuration to test against parsed claim bounds. */
export interface ScopeRequest {
  /**
   * The point to test. `string | number` because a claim bound may be
   * categorical — `@/engine/scope`'s `inScope` takes exactly this.
   */
  config: Record<string, string | number>;
  /** The design the config came from, when it came from one. */
  designId?: string;
}

/** Where to look for unclaimed space. */
export interface WhitespaceRequest {
  /** Ontology fields to bound the search to. Empty means the whole space. */
  fields?: readonly FieldId[];
  /** Restrict to space adjacent to these patents. */
  patentIds?: readonly string[];
}

/**
 * A region of the parameter space no claim covers.
 *
 * NO PYDANTIC MODEL — nothing computes one yet. Deliberately expressed in
 * `ClaimBound`s rather than in bare intervals, because whitespace is only
 * meaningful in the same ontology as the claims it is the complement of; that
 * comparability is the whole of what Parchment is for.
 */
export interface WhitespaceRegion {
  id: string;
  /** The interval on each field that bounds the region. */
  bounds: import('@/data/types').ClaimBound[];
  /**
   * Patents whose claims ABUT the region. Never "patents that cover it" — a
   * region with a covering claim is not whitespace.
   */
  adjacentPatentIds: string[];
  /** What established the region, in the words of whatever computed it. */
  basis: string;
}

/**
 * The planned gold set, as one answer.
 *
 * TRANSPORT SHAPE, not an entity — the two arrays are rendered together by
 * every caller and are one artifact of OF-COR-001 §18, so they travel as one
 * payload with one `corpusSnapshotId` on it. Splitting them into two methods
 * would let a caller pair a plan with the difficulty cases of a different
 * corpus revision, which is the failure `ResponseMeta` exists to prevent.
 */
export interface GoldSetPlan {
  entries: GoldSetPlanEntry[];
  /**
   * The deliberate difficulty cases (§18), each one sentence of prose. A bare
   * `string[]` because that is all they are — no id, no structure, nothing a
   * model would add — and inventing a record type for six sentences would be
   * inventing a schema, not describing one.
   */
  difficultyCases: string[];
}

/**
 * BioRepo — papers, records, patents, patent scope, and the gold-set plan.
 *
 * The read half fronts what `src/data/source.ts` already serves; the write
 * half and the two scope methods front work that does not exist in this repo
 * at all.
 */
export interface CorpusAdapter {
  /**
   * Retrieval. Returns `CorpusSearchResult` whole, so the `method` string
   * stating what actually ran travels with the hits — under the fixture that
   * is a substring filter, and it says so.
   */
  searchPapers(
    query: string,
    options?: CorpusSearchOptions,
  ): Promise<AdapterResponse<CorpusSearchResult>>;

  /** One paper, or `null` when the corpus has no such id. */
  getPaper(paperId: string): Promise<AdapterResponse<Paper | null>>;

  /** Records, filtered. No filter returns the whole set. */
  getRecords(query?: RecordQuery): Promise<AdapterResponse<ExtractionRecord[]>>;

  /**
   * The catalogued patents.
   *
   * WHY BIOREPO AND NOT THE GUILD. A patent is catalogued literature that
   * happens to carry claims: each of the six is keyed by `paperId` to a corpus
   * entry (H17a–f), and `getScope` below already reads them to test a
   * configuration. The Guild's business is attestation — chapters, deposits,
   * seals — and a patent is not something a chapter issued. Parchment is the
   * SCREEN that renders these; a screen is not a server, and routing a
   * collection to the adapter named after the page that draws it is how a UI
   * layout becomes an architecture.
   *
   * NO `notice`, deliberately, and this is the test `AdapterResponse.notice`
   * sets rather than an omission: the payload does not mislead on its own.
   * Every claim comes back carrying `parseUncertain: true` and `bounds: []`,
   * so the limitation is IN the entities rather than hidden by them. The
   * notices on `getScope` and `getWhitespace` exist because an empty array
   * cannot say why it is empty; a patent can say what it is missing.
   *
   * NOT YET A CORPUS COLLECTION. Unlike the seven in `src/data/source.ts`,
   * patents have no `data/corpus/patents.json` — the exporter maps seven keys
   * to seven Pydantic models and `Patent` is not among them, though the model
   * exists (`packages/core/.../schema/design.py`). When it is exported, the
   * fixture below reads it through `@/data/source` like everything else and
   * nothing above this line changes.
   */
  listPatents(): Promise<AdapterResponse<Patent[]>>;

  /**
   * The gold set as planned in OF-COR-001 §18: which papers get annotated, on
   * which fields, how many records, and the six cases chosen to be hard.
   *
   * WHY BIOREPO AND NOT AUDIT. Audit owns the SCORE; it does not own the SET.
   * `packages/assay` is an Inspect AI scorer — it consumes gold annotations
   * and extractor output and returns metrics — and CLAUDE.md's table gives it
   * "gold-set scoring", not gold-set authoring. Every field of a plan row is a
   * BioRepo coordinate (a paper id, ontology fields, a record count), and one
   * row's `blocked` flag is a fact about ONTOLOGY_GAPS that a scorer holding
   * no ontology could not evaluate. When the annotation actually happens those
   * rows become `ExtractionRecord`s with `provenance: 'gold'` in this same
   * store, and the plan degrades into a query over it — which is the clearest
   * sign of who was holding it all along. Putting it behind Audit would make
   * Inspect AI the authority on which papers exist.
   *
   * `RUN_OUTPUTS` is the other half of `src/data/runOutputs.ts` and goes the
   * OTHER WAY: it is a scorer's output, it is empty, it stays empty until an
   * extractor has run, and it belongs to Audit whenever that seam is built.
   * The two share a file because one screen renders both, not because they
   * share an owner.
   *
   * NO `notice`, for the reason `listPatents` gives: the payload is named
   * `GoldSetPlan`, its counts sit under `entries[].records`, and both callers
   * already state on the face of the screen that this is a plan and nothing
   * has been annotated. A notice no caller renders would break the rule that
   * a caller receiving one must render it.
   */
  getGoldSetPlan(): Promise<AdapterResponse<GoldSetPlan>>;

  /**
   * Write one record. Returns the STORED form, which may differ from what was
   * submitted — the SI twin is a derivation of (value, unit) and is recomputed
   * at the boundary, exactly as `source.ts` recomputes it on read.
   */
  writeRecord(record: ExtractionRecord): Promise<AdapterResponse<ExtractionRecord>>;

  /**
   * NEW. Which patent claims a configuration falls inside.
   *
   * An empty result does NOT mean "unencumbered" — `DesignRecord.scope`'s own
   * docstring makes the same point about the word `clear`. It means no claim
   * this backend can read placed the configuration inside itself, which is a
   * different sentence, and `notice` carries the difference.
   */
  getScope(request: ScopeRequest): Promise<AdapterResponse<ScopeHit[]>>;

  /**
   * NEW. Regions of the parameter space no claim covers.
   *
   * Empty under the fixture, and empty is the only defensible answer there;
   * see `fixture/corpus.ts` for why, at length.
   */
  getWhitespace(request?: WhitespaceRequest): Promise<AdapterResponse<WhitespaceRegion[]>>;
}

// ══════════════════════════════════════════════════════════════════════════
// 2. CellAdapter — geneOS
// ══════════════════════════════════════════════════════════════════════════

/** A flux prediction to run. */
export interface FluxRequest {
  strainId: string;
  /** Reaction or objective to maximise, in the genome-scale model's own ids. */
  objective: string;
  /** Bounds to impose, keyed by reaction id. */
  constraints?: Record<string, [number, number]>;
}

/**
 * One predicted flux.
 *
 * NO PYDANTIC MODEL — nothing predicts one yet. `modelId` is not optional on
 * purpose: a flux without the genome-scale model that produced it is a number
 * with no way to check it, and `evidenceClass: 'computed'` exists in the
 * schema precisely so a prediction cannot enter the Ledger wearing a paper's
 * face.
 */
export interface FluxPrediction {
  strainId: string;
  objective: string;
  value: number;
  unit: string;
  /** The genome-scale model, e.g. an identifier of the SBML that was solved. */
  modelId: string;
}

/**
 * geneOS — hosts, and what is known or predicted about them.
 */
export interface CellAdapter {
  listStrains(): Promise<AdapterResponse<Strain[]>>;

  getStrain(strainId: string): Promise<AdapterResponse<Strain | null>>;

  /**
   * Every record attributable to a strain — tagged with it, or, absent a tag,
   * belonging to a paper whose organism list names it.
   */
  getStrainRecords(strainId: string): Promise<AdapterResponse<ExtractionRecord[]>>;

  /**
   * Flux balance. COBRApy's, in Python, always — CLAUDE.md names it among the
   * libraries a second TypeScript implementation would have to agree with
   * forever.
   *
   * `null` when no model can answer. That is the fixture's permanent state and
   * it is the same fact `T1` states in every design in the build: absent, with
   * a reason, rather than a plausible number.
   */
  predictFlux(request: FluxRequest): Promise<AdapterResponse<FluxPrediction | null>>;
}

// ══════════════════════════════════════════════════════════════════════════
// 3. ProcessAdapter — fermOS
// ══════════════════════════════════════════════════════════════════════════

/**
 * Handle to a submitted evaluation.
 *
 * Opaque: only the adapter that issued one may interpret it. A caller that
 * parses a JobId has coupled itself to a backend.
 */
export type JobId = string;

/** A configuration to evaluate through the tier cascade. */
export interface EvaluationRequest {
  scenarioId: string;
  config: Record<string, number>;
  /** Display label for the resulting design. Defaults to a generated one. */
  label?: string;
}

/**
 * Where a submitted evaluation has got to.
 *
 * `position` is `src/sim/jobs.ts`'s `JobPosition`, which is REPORTED and never
 * derived — the store is forbidden from inferring completion from
 * `stageIndex >= stages.length`, and so is anything reading this. `status` and
 * `position.done` come from the same source and cannot be assembled from each
 * other by a caller.
 */
export interface EvaluationStatus {
  jobId: JobId;
  status: JobStatus;
  position: JobPosition;
  /**
   * The stages the backend is running. A server declares its own; a client
   * never invents them, and never invents their durations.
   */
  stages: readonly JobStage[];
  /** Present once `status` is `done`. */
  result?: DesignRecord;
  /** Present once `status` is `failed`. */
  failReason?: string;
}

/**
 * fermOS — scenarios, designs, and the tier cascade over a configuration.
 */
export interface ProcessAdapter {
  listScenarios(): Promise<AdapterResponse<Scenario[]>>;

  getScenario(scenarioId: string): Promise<AdapterResponse<Scenario | null>>;

  /** Designs, optionally narrowed to one scenario. */
  listDesigns(scenarioId?: string): Promise<AdapterResponse<DesignRecord[]>>;

  getDesign(designId: string): Promise<AdapterResponse<DesignRecord | null>>;

  /**
   * Submit a configuration for tier evaluation, and get back a handle.
   *
   * ASYNCHRONOUS BECAUSE T2 AND T3 ARE EXPENSIVE. A reactor model and a Monte
   * Carlo cash flow will both exceed any request/response timeout, so the
   * result is collected by handle rather than returned — and that has to be
   * true from the first call site, because retrofitting it means touching all
   * of them. The fixture finishes before it returns and issues the handle
   * anyway; that is the shape being fixed now, not a simulation of slowness.
   */
  submitEvaluation(request: EvaluationRequest): Promise<AdapterResponse<JobId>>;

  /** Collect an evaluation by handle. Rejects on a handle this backend never issued. */
  getEvaluation(jobId: JobId): Promise<AdapterResponse<EvaluationStatus>>;

  /**
   * Progress for the jobs this adapter is running.
   *
   * NOT async, and the one method here that is not. `JobRunner.report` is
   * called from a requestAnimationFrame loop — `src/sim/jobs.ts` says so, and
   * says a server-backed runner keeps the last report it received from a
   * socket, an SSE stream or a poll and returns that, with the network work
   * happening outside the frame. Making it async would put a promise in the
   * animation loop and change nothing about when the news arrives.
   *
   * A runner reports only the jobs it has an opinion about, and jobs it omits
   * are left exactly as they are. That is why one store can drive a simulated
   * runner and a server-backed one at the same time during the changeover.
   */
  jobRunner(): JobRunner;
}

// ══════════════════════════════════════════════════════════════════════════
// 4. EconomicsAdapter — Proforma
// ══════════════════════════════════════════════════════════════════════════

/**
 * A cost model without its `evaluate`.
 *
 * DERIVED, not restated. `CostModel.evaluate` is a function and `ResultGrid`
 * holds `Float64Array`s; `src/data/types.ts` records both as the two types
 * that cannot round-trip through JSON Schema, which makes them exactly the two
 * things that must never appear on this interface. Grid interpolation for
 * sliders stays in TypeScript by CLAUDE.md's own table — it is a UI
 * convenience over a grid the client already holds, not a call.
 */
export type CostModelSummary = Omit<CostModel, 'evaluate'>;

/** A point in a cost model's parameter space. */
export interface PointRequest {
  modelId: CostModel['modelId'];
  point: Record<string, number>;
}

/**
 * One local sensitivity bar — the MSP change when a single parameter is taken
 * to each of its bounds, everything else held fixed.
 *
 * DERIVED from `deriveSensitivity`'s own return type so the two cannot drift.
 */
export type SensitivityBar = ReturnType<typeof deriveSensitivity>[number];

/**
 * Proforma — the cost model, and the plant behind the price.
 */
export interface EconomicsAdapter {
  listCostModels(): Promise<AdapterResponse<CostModelSummary[]>>;

  getCostModel(modelId: string): Promise<AdapterResponse<CostModelSummary | null>>;

  /**
   * Evaluate one point: MSP and the cost lines that sum to it.
   *
   * `EvaluatedPoint.clamped` says the request fell outside the modelled
   * envelope and was pulled to its edge — a fact about the answer, and one a
   * caller must be able to see rather than infer.
   */
  evaluatePoint(request: PointRequest): Promise<AdapterResponse<EvaluatedPoint | null>>;

  /**
   * The whole flowsheet solve — equipment sized, costed, and priced by a
   * discounted cash flow. BioSTEAM's work; `null` when no flowsheet exists for
   * the model.
   */
  solvePlant(request: PointRequest): Promise<AdapterResponse<PlantResult | null>>;

  /** Two plant solves per parameter. Local: it cannot see interactions. */
  getSensitivity(request: PointRequest): Promise<AdapterResponse<SensitivityBar[]>>;
}

// ══════════════════════════════════════════════════════════════════════════
// 5. GuildAdapter — chapters, deposits, seals
// ══════════════════════════════════════════════════════════════════════════

/**
 * A guild chapter — a place with benches, people and a biosafety level.
 *
 * NO PYDANTIC MODEL — no chapter registry exists. `bsl` is here rather than in
 * a note because it is a constraint, not a description: `Protocol.bsl` already
 * bounds which protocols a chapter could run, and a chapter record that did
 * not carry it would let the two be paired by a screen with no basis for it.
 */
export interface GuildChapter {
  id: string;
  name: string;
  /** Institution or site hosting the chapter. */
  host: string;
  bsl: 1 | 2;
  /** Protocols the chapter is equipped to run. */
  protocolIds: string[];
}

/** What a seal attests to. */
export interface SealSubject {
  kind: 'design' | 'protocol-version' | 'deposit';
  id: string;
  /** Protocol version, when `kind` is `protocol-version`. */
  version?: string;
}

/**
 * A seal — a chapter's attestation that it checked something.
 *
 * NO PYDANTIC MODEL — nothing issues one. `digest` is required: a seal that
 * does not commit to specific bytes attests to nothing, and would be worse
 * than no seal because it would look like something.
 */
export interface Seal {
  id: string;
  subject: SealSubject;
  /** The chapter that issued it. */
  chapterId: string;
  /** ISO timestamp. */
  issuedAt: string;
  /** Digest of the sealed artifact. */
  digest: string;
  /** What the chapter checked, in its own words. */
  attestation: string;
}

export interface SealRequest {
  subject: SealSubject;
  chapterId: string;
  /** The publication state being sought. */
  publication?: PublicationStatus;
}

export interface DepositQuery {
  protocolId?: string;
  chapterId?: string;
  outcome?: RunOutcome['outcome'];
}

export interface SealQuery {
  subjectId?: string;
  chapterId?: string;
}

/**
 * The Guild — who is doing the work, what they contributed, what got checked.
 */
export interface GuildAdapter {
  listChapters(): Promise<AdapterResponse<GuildChapter[]>>;

  getChapter(chapterId: string): Promise<AdapterResponse<GuildChapter | null>>;

  /** Deposited run outcomes. A failure is a first-class outcome, not an error. */
  listDeposits(query?: DepositQuery): Promise<AdapterResponse<RunOutcome[]>>;

  /** Deposit a run outcome. Returns the stored form. */
  submitDeposit(outcome: RunOutcome): Promise<AdapterResponse<RunOutcome>>;

  listSeals(query?: SealQuery): Promise<AdapterResponse<Seal[]>>;

  /**
   * Ask a chapter to seal something.
   *
   * The one method on this seam that a backend may refuse rather than answer:
   * issuing a seal means MINTING an attestation, and a fixture that minted one
   * would be stamping a disclosure nobody checked. See `fixture/guild.ts`.
   */
  requestSeal(request: SealRequest): Promise<AdapterResponse<Seal>>;
}

// ══════════════════════════════════════════════════════════════════════════

/** The five, as one backend hands them over. */
/** What a submitted turn did besides stream, mirroring `SlashResult` in the sim. */
export interface TurnResult {
  /** True when the input was consumed as a slash command rather than a question. */
  handled: boolean;
  /** A new session scope, when the turn set one (`/scope`). */
  scope?: { kind: 'paper' | 'collection'; id: string; label: string };
}

/**
 * The agent behind the Postdoc screen.
 *
 * The conversation itself STREAMS THROUGH THE STORE — messages, plan steps,
 * tool rows and retrieval cards are pushed as they happen, which is how the
 * screen renders a turn in progress. What comes back here is only what the
 * caller must act on immediately: whether the input was a command, and any
 * scope it set. A real agent honours the same split; the transport of the
 * stream changes, the seam does not.
 *
 * `sendFlow` is SCRIPTED-MODE VOCABULARY, kept on the interface deliberately:
 * a clarify option in the scripted player names the flow it continues into,
 * and the real agent treats a clarify reply as ordinary text. It retires with
 * `src/sim/` (whose headers name their own removal), not with this file.
 */
export interface AgentAdapter {
  /** Submit a user turn into a session. */
  send(sessionId: string, input: string): Promise<AdapterResponse<TurnResult>>;
  /** Continue a scripted clarify into the flow its option names. */
  sendFlow(sessionId: string, flowId: string, label: string): Promise<AdapterResponse<null>>;
}

export interface OpenFermentAdapters {
  corpus: CorpusAdapter;
  cell: CellAdapter;
  process: ProcessAdapter;
  economics: EconomicsAdapter;
  guild: GuildAdapter;
  agent: AgentAdapter;
}

/** Which implementation is in front of the five. */
export type AdapterBackend = 'fixture' | 'mcp';
