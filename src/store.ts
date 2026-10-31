// Single store (OF-DES-001 §13.3). All mutations flow through actions so
// provenance-affecting changes fan out to derived views in one place.
// The scientific records live on the service, in the open project
// (lib/projectState.ts and the service's own stores); what this browser keeps
// is its preferences and the writes the service has not yet acknowledged
// (src/lib/durable.ts), and localStorage holds the last-open project alone.
import { useMemo } from 'react';
import { create } from 'zustand';
import type {
  Project,
  InputAssumption,
  Override,
  RunbookDraft,
  AuditEvent,
  ReviewDecision,
  ActivityEvent,
  LiveConversation,
  LiveTurn,
  TraceStep,
  Deposition,
  Deviation,
  ExtractionRecord,
  Job,
  MeasuredEvidence,
  LearnModule,
  OverlayPaper,
  Paper,
  Product,
  Protocol,
  Provenance,
  RecordStatus,
  Runbook,
  SeriesRole,
  FermosFitResponse,
  TrainProposal,
  TrainFromRun,
  TrainRun,
  KeptTrain,
  RunOutput,
  RunState,
  Scenario,
  Strain,
  TimerState,
  Overlay,
  Guild,
  GuildEvidence,
  GuildPerson,
  GuildPolicy,
  GuildWithdrawal,
  Practice,
  PracticeScenario,
  PracticeSession,
  Check,
  CheckNote,
  CheckResult,
  Checks,
  Skill,
  TrainSpec,
} from '@/data/types';
import { toSI } from '@/engine/units';
import { runbookLockHash } from '@/engine/lock';
import { computeDeltas } from '@/engine/reconcile';
import { parseReadingsCsv, placeRow } from '@/engine/series';
import {
  type DurableReviewDecision,
  EMPTY_SNAPSHOT,
  clearDurable,
  durableAvailable,
  flushDurable,
  loadDurable,
  saveDurable,
  type DurableSnapshot,
  type TrainMade,
} from '@/lib/durable';
import { DecisionRefused, IntakeDown, extractPaper, loadOverlay, postDecision } from '@/lib/intake';
import { blocks, carryOverSpan, isNewCandidate, spanChangesNumber, writeRefusal, type ReviewAction } from '@/lib/review';
import { call } from '@/lib/http';
import { openProjectId, projectSettled, setOpenProjectId } from '@/lib/project';
import {
  EMPTY_STATE,
  applyEntries,
  changes,
  enqueue,
  flush,
  loadProjectState,
  type OutboxEntry,
  type ProjectState,
} from '@/lib/projectState';
import {
  EMPTY_GUILD,
  GuildRefused,
  loadGuild,
  newEvidenceId,
  personIdFor,
  postEvidence,
  postPerson,
  postWithdrawal,
  postPolicy,
} from '@/lib/guild';
import { loadPractice as loadPracticeFromService } from '@/lib/practice';
import { CheckRefused, loadChecks as loadChecksFromService, postBrief, postDismiss, postPropose, postRecord, postRequest, postSchedule, whyNot } from '@/lib/checks';
import { competenceOf, localToday, mayCosign, statusOf } from '@/engine/competence';

export type Theme = 'bench' | 'night';
export type Density = 'comfortable' | 'dense';
export type UnitMode = 'published' | 'si';

export interface Toast {
  id: string;
  text: string;
  kind: 'info' | 'success' | 'warn' | 'error';
  href?: string;
  hrefLabel?: string;
}

interface UndoFrame {
  records: ExtractionRecord[];
  /** The records this action changed. Undo restores these and only these (§7.3). */
  recordIds: string[];
  queueIndex: number;
  label: string;
}

let seq = 0;
export const nextId = (prefix: string) => `${prefix}-${++seq}`;

/** An id that stays unique across reloads: the time, and a counter for ties. */
export const timeId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${++seq}`;

/** How many Live conversations the page holds, newest first; the project keeps every one. */
const MAX_LIVE_CONVERSATIONS = 30;

/** Deterministic clock-free timestamp label for audit entries. */
function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/**
 * The decision a record's current state amounts to (OF-BLD-012 §7.3): the
 * Durable tier's six fields, the record id, an ISO stamp the service can
 * order against a snapshot's savedAt, and — when a promotion re-anchored the
 * record — the span it now stands on.
 */
function decisionOf(
  r: ExtractionRecord,
  span: { quote: string; sectionId: string } | null,
  at: string,
): ReviewDecision {
  return {
    status: r.status,
    provenance: r.provenance,
    gold: r.gold,
    corrected: r.corrected,
    rejectReason: r.rejectReason,
    // The CURRENT name, not the one the record was stamped with: a decision
    // made before a name was set is posted under the name once there is one,
    // and an undo is signed by whoever undid it.
    reviewer: reviewerName() ?? r.reviewer ?? '',
    recordId: r.id,
    at,
    ...(span ? { quote: span.quote, sectionId: span.sectionId } : {}),
  };
}

/**
 * The span a promotion re-anchored a curated record to (§7.3), when it did:
 * the record's quote and section differ from the seed's. Null for a record on
 * its own quote, and for a candidate, whose quote anchored when it was
 * extracted and is never carried. What the Durable tier persists and what a
 * synced decision posts, so a carry-over made offline survives a reload and
 * reaches the service with the sentence it stands on — a decision posted
 * without it would be anchored on the seed quote, which is not in the paper.
 */
function reanchoredSpan(r: ExtractionRecord): { quote: string; sectionId: string } | null {
  const was = r.original;
  if (!was || (r.quote === was.quote && r.sectionId === was.sectionId)) return null;
  return { quote: r.quote, sectionId: r.sectionId };
}

/**
 * What a record was published as, stamped once as it ENTERS the store
 * (OF-BLD-012.1 F7) and never touched by a decision. Answering "has this been
 * re-anchored?" by diffing against the seed module was right until a corpus
 * update moved the seed underneath a decided record: the record then looked
 * re-anchored and the sync posted the seed's new sentence as though a
 * reviewer had chosen it.
 */
function stampOriginal(r: ExtractionRecord): ExtractionRecord {
  return r.original
    ? r
    : { ...r, original: { value: r.value, unit: r.unit, quote: r.quote, sectionId: r.sectionId } };
}

/**
 * Who is deciding (OF-BLD-012.1 F2), or null when nobody has said. The one
 * place the name is read: `biorepo.write` refuses a decision signed by a
 * placeholder, and a corpus whose decisions are all signed the same
 * non-name is a corpus nobody can be asked about.
 */
export function reviewerName(): string | null {
  return useStore.getState().reviewer.trim() || null;
}

/**
 * What an audit line is signed with. A decision made before a name is set is
 * still a real decision in this browser — it simply cannot be posted, because
 * `writeRefusal` blocks it — so the trail says where it was made rather than
 * inventing a person.
 */
function decidedBy(): string {
  return reviewerName() ?? 'this browser';
}

/** The review action a record's current state amounts to, for the refusal predicate. */
function actionOf(r: ExtractionRecord): ReviewAction {
  if (r.gold) return 'gold';
  if (r.status === 'verified') return 'accept';
  return 'reject';
}

/**
 * A decision applied to a record — the service's or the Durable tier's. The
 * six review fields, the span a promotion re-anchored to, and the corrected
 * value AS the value: a record whose correction is shown beside a stale
 * number is two records.
 */
function applyDecision(r: ExtractionRecord, d: DurableReviewDecision | ReviewDecision): ExtractionRecord {
  const next: ExtractionRecord = {
    ...r,
    status: d.status,
    provenance: d.provenance,
    gold: d.gold,
    corrected: d.corrected,
    rejectReason: d.rejectReason,
    reviewer: d.reviewer,
  };
  if ('quote' in d && d.quote) next.quote = d.quote;
  if ('sectionId' in d && d.sectionId) next.sectionId = d.sectionId;
  if (d.corrected && typeof d.corrected.value === 'number') {
    next.value = d.corrected.value;
    next.unit = d.corrected.unit;
    next.si = toSI(d.corrected.value, d.corrected.unit);
  } else if (r.corrected && r.original) {
    // A newer decision with no correction withdraws the one this record
    // carried: the PUBLISHED number comes back as the value, not the edit —
    // and the published SENTENCE with it, unless the decision brought its
    // own. A promotion carried the extractor's span together with the
    // paper's number; putting the number back beside the carried sentence
    // leaves a record whose quote no longer states its value.
    next.corrected = undefined;
    next.value = r.original.value;
    next.unit = r.original.unit;
    if (typeof r.original.value === 'number') next.si = toSI(r.original.value, r.original.unit);
    if (!('quote' in d && d.quote)) {
      next.quote = r.original.quote;
      next.sectionId = r.original.sectionId;
    }
  }
  return next;
}

function sameDecision(a: ExtractionRecord, b: ExtractionRecord): boolean {
  return (
    a.status === b.status &&
    a.rejectReason === b.rejectReason &&
    JSON.stringify(a.gold ?? null) === JSON.stringify(b.gold ?? null) &&
    JSON.stringify(a.corrected ?? null) === JSON.stringify(b.corrected ?? null)
  );
}

export interface OFState {
  // ── seeded data (session-mutable) ────────────────────────────────────
  papers: Paper[];
  records: ExtractionRecord[];
  runOutputs: RunOutput[];
  strains: Strain[];
  /** The molecule catalogue (OF-BLD-005). Session-mutable like the rest. */
  products: Product[];
  /**
   * Synthesised runbooks. Kept separate from `jobs` on purpose: a Job is a
   * progress bar the tray owns and discards, a Runbook is a record with
   * content. A running runbook borrows the tray for its progress affordance.
   */
  runbooks: Runbook[];
  /**
   * The open project's depositions (OF-BLD-006 §4.6; lib/projectState.ts).
   * A deposition is a record, not a session: a fermentation at hour 14
   * cannot be lost to a page reload, so a change the service has not yet
   * acknowledged waits in the outbox.
   */
  depositions: Deposition[];
  /**
   * First-party measurements released by reconciliation. Durable, and
   * deliberately a separate list from `records`: these are evidence about a
   * run, not extractions from a paper (OF-BLD-006 §5).
   */
  measuredEvidence: MeasuredEvidence[];
  protocols: Protocol[];
  scenarios: Scenario[];
  modules: LearnModule[];
  /** A lab's skills (stage 2 serves them); none ship with the app. */
  skills: Skill[];
  activity: ActivityEvent[];
  /**
   * Postdoc's Live conversations, newest first. Durable: a question asked
   * here is still on the page after a citation is followed and after a
   * reload, and a follow-up reads the turns before it.
   */
  liveConversations: LiveConversation[];

  // ── runtime ──────────────────────────────────────────────────────────
  runs: Record<string, RunState>;
  activeRunId: string | null;
  jobs: Job[];
  toasts: Toast[];
  reviewQueue: string[];
  reviewIndex: number;
  reviewStats: { accepted: number; rejected: number; edited: number; skipped: number; gold: number; startedAt: number };
  undoStack: UndoFrame[];
  learnProgress: Record<string, boolean>;
  /** Runbooks adopted from a Postdoc draft, by id (OF-BLD-014 §9.2). Durable. */
  adoptedRunbookIds: string[];
  /**
   * Proforma scenarios a person made here from a shelf flowsheet, by id
   * (OF-BLD-019 §3.1, D6). Durable: they live in `scenarios` beside the
   * seeded ones and are saved whole, keyed by id.
   */
  createdScenarioIds: string[];
  /** A research runbook, unlocked, from a draft; returns its id. */
  adoptRunbookDraft: (draft: RunbookDraft) => string;
  /**
   * Proforma's typed assumptions, by scenario id (§8.4). Durable. Since
   * OF-BLD-020 §2.1 it is DERIVED from `parameterOverrides`: each
   * `proforma:<id>` scope's numeric overrides, as `assumptionsFromOverrides`
   * reads them, kept in step by every action that writes an override. Since
   * OF-BLD-020 §2.2 no screen reads it: the scenario page, the index and
   * geneOS read the overrides, and the field is kept, derived, for the
   * snapshot an older build reads and the one-time migration.
   */
  proformaAssumptions: Record<string, InputAssumption[]>;
  /** Writes the override `proforma:<scenarioId>` holds for the input, through `setOverride`. */
  setProformaAssumption: (scenarioId: string, a: InputAssumption) => void;
  /** Removes it, through `clearOverride`. */
  clearProformaAssumption: (scenarioId: string, key: string) => void;
  /**
   * Every change a person made in the parameter panel, by scope
   * (OF-BLD-020 D3): a named assumption this browser keeps and a run
   * carries. Durable; the service keeps none. Read one scope with
   * `useStore(overridesFor(scope))`.
   */
  parameterOverrides: Record<string, Override[]>;
  /** Keep a person's override, replacing any for the same scope and key. */
  setOverride: (o: Override) => void;
  /** Reset to source: drop the override of one parameter in one scope. */
  clearOverride: (scope: string, key: string) => void;
  /**
   * The fermOS fits a person chose for a scenario's inputs, by scenario id
   * and then input key: the id of a kept kinetic fit or forecast
   * (OF-BLD-019 §5.1, D10). Durable, like assumptions; the service computes
   * every value from the artifact.
   */
  proformaFits: Record<string, Record<string, string>>;
  /** Bind these inputs of a scenario to these fermOS artifacts (each key to its id). */
  setProformaFits: (scenarioId: string, fits: Record<string, string>) => void;
  /** Stop using a fermOS fit for one input of a scenario, or for every input when no key is named. */
  clearProformaFit: (scenarioId: string, key?: string) => void;
  /**
   * pureOS's trains built here, by train id (OF-BLD-020 §5.3, D9): each saved
   * whole as data, with when and by whom. Durable; the service keeps the
   * train runs and no train. The values typed into a train's panels live in
   * `parameterOverrides` under its scopes, and a saved train carries them as
   * they stood when it was saved.
   */
  trainsMade: Record<string, TrainMade>;
  /** Save a train built in the Builder under a reviewer name, replacing the one saved by its id. */
  saveTrain: (train: TrainSpec, by: string) => void;
  exports: { name: string; at: string; rows: number }[];

  ui: {
    theme: Theme;
    density: Density;
    reducedMotion: boolean;
    unitMode: UnitMode;
    paletteOpen: boolean;
    jobsOpen: boolean;
    sessionsOpen: boolean;
    railCollapsed: boolean;
    tourStop: number | null;
    helpOpen: boolean;
    /** Proforma's New scenario dialog (OF-BLD-019 §3.1); the palette opens it too. */
    newScenarioOpen: boolean;
  };

  // ── actions ──────────────────────────────────────────────────────────
  setUI: (patch: Partial<OFState['ui']>) => void;
  toast: (t: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;

  // records / review
  startReview: (ids: string[]) => void;
  reviewDecide: (
    id: string,
    action: 'accept' | 'reject' | 'skip' | 'gold',
    payload?: { reason?: string },
  ) => void;
  editRecord: (id: string, value: number, unit: string) => void;
  setRecordStatus: (id: string, status: RecordStatus, reason?: string) => void;
  undoReview: () => void;
  advanceReview: (delta: number) => void;

  // jobs
  startJob: (job: Omit<Job, 'id' | 'stageIndex' | 'stageProgress' | 'status' | 'startedAt'>) => string;
  failJob: (id: string, reason: string) => void;
  clearJobs: () => void;

  // ingest

  // protocols / runs
  startRun: (protocolId: string, version: string, scale: number) => string;
  completeStep: (runId: string, stepId: string) => void;
  uncompleteStep: (runId: string, stepId: string) => void;
  skipStep: (runId: string, stepId: string, reason: string) => void;
  setRunStep: (runId: string, index: number) => void;
  toggleCheck: (runId: string, stepId: string, idx: number) => void;
  addDeviation: (runId: string, d: Deviation) => void;
  addTimer: (runId: string, t: Omit<TimerState, 'running' | 'remainingSec'>) => void;
  toggleTimer: (runId: string, timerId: string) => void;
  extendTimer: (runId: string, timerId: string, sec: number) => void;
  dismissTimer: (runId: string, timerId: string) => void;
  tickTimers: (dtMs: number) => void;
  finishRun: (runId: string) => void;
  addProtocolVersion: (protocolId: string, version: Protocol['versions'][number]) => void;

  // runbooks (OF-BLD-005 §7) — a slice of its own, never folded into jobs
  /** Research → industrial in one action, carrying the finding across. */
  promoteRunbook: (runbookId: string) => string | null;
  /**
   * Unblock a runbook halted on an unsourced value. Two honest ways forward:
   * attach a source, or mark the number an explicit assumption and continue
   * with it labelled as one.
   */
  resolveRunbookInput: (runbookId: string, mode: 'source' | 'assumption') => void;
  /** Authorise the priced compute for a runbook waiting on a budget decision. */
  authoriseRunbookBudget: (runbookId: string) => void;
  /** Record that a person has ruled on a runbook held for review. */
  resolveRunbookReview: (runbookId: string, verdict: string) => void;
  /**
   * Freeze a runbook's predictions and schema (§3.3). After this the content
   * is immutable at the object level, not merely by agreement.
   */
  lockRunbook: (runbookId: string) => void;
  /**
   * Change one prediction's value. Refuses on a locked runbook and says why —
   * the refusal is the feature, and silently succeeding would let the platform
   * grade its own homework.
   */
  reviseRunbookPrediction: (runbookId: string, predictionId: string, value: number) => boolean;
  /**
   * The legitimate way past a lock: a new, unlocked revision carrying the same
   * content. Supersede, never edit.
   */
  supersedeRunbook: (runbookId: string) => string | null;

  // scenarios
  togglePin: (id: string) => void;
  duplicateScenario: (id: string) => string;
  /**
   * A `biosteam` scenario on a shelf flowsheet (OF-BLD-019 §3.1): its name,
   * no inputs of its own, not run.
   * Durable, under a time-based id; returns the id.
   */
  /**
   * OF-BLD-020 §6.1: `parts` names the vessel design and the train run a
   * scenario on `custom_train_v1` is built from; kept with it (Durable).
   */
  createScenario: (
    flowsheetId: string,
    name: string,
    parts?: { vessel: string; trainRun: string } | null,
  ) => string;
  /** The newest run artifact of a scenario, as a run on its page returned it (D6). */
  recordScenarioRun: (id: string, artifactId: string) => void;

  // Postdoc's Live conversations — the only conversations there are
  /** A new Live conversation, first in the list; returns its id. */
  startLiveConversation: (title: string) => string;
  /** Add a turn to a Live conversation. */
  addLiveTurn: (conversationId: string, turn: LiveTurn) => void;
  /** Change a turn; a step is appended with `step`. */
  patchLiveTurn: (conversationId: string, turnId: string, patch: Partial<LiveTurn> & { step?: TraceStep }) => void;
  /** Remove a Live conversation. */
  dropLiveConversation: (conversationId: string) => void;
  /**
   * Take back a turn the service never received (it was not running), and
   * the conversation with it when that turn was its only one. Nothing was
   * asked, so nothing is kept as if it had been.
   */
  dropLiveTurn: (conversationId: string, turnId: string) => void;

  // learn
  completeLesson: (lessonId: string) => void;

  // deposition (OF-BLD-006 §4)
  /**
   * Open a Deposition in `staged` and start the run session that writes into
   * it. Staged is the last moment the measurement schema can change (§4.5).
   */
  openDeposition: (runbookId: string, protocolId: string, scale: number) => { depositionId: string; runId: string } | null;
  /** Staged → running. Nothing is recorded before this. */
  beginDeposition: (depositionId: string) => void;
  /**
   * Record something the operator reported. A value matching the runbook's
   * schema becomes an entry; everything else becomes an observation, kept
   * verbatim (§4.3).
   */
  captureDeposition: (
    depositionId: string,
    stepId: string,
    raw: string,
    match: { measureId: string; value: number; unit: string } | null,
  ) => void;
  /** The read-back beat on a number (§4.4). */
  confirmEntry: (depositionId: string, entryId: string) => void;
  /** Correct a mis-parse by appending, never by overwriting `raw`. */
  amendEntry: (depositionId: string, entryId: string, value: number) => void;
  /** Attach a later structured reading to an observation, leaving raw alone. */
  structureObservation: (depositionId: string, observationId: string, structured: string) => void;
  /** OF-BLD-014 §7.1 — an entry's hours into the run, or null to take it out of its series. */
  setSampleTime: (depositionId: string, entryId: string, hours: number | null) => void;
  /** What a measure's series is (biomass, product, substrate), or null. */
  setSeriesRole: (depositionId: string, measureId: string, role: SeriesRole | null) => void;
  /**
   * Readings logged elsewhere, as CSV (`time_h, measure, value, unit`). Each
   * placed row becomes an unconfirmed entry with its time; every other line
   * is kept verbatim as an observation. Rows attach in time order.
   */
  attachReadings: (depositionId: string, csv: string) => { attached: number; kept: number };
  /** Running → closed. Append-only throughout; closing stops new entries. */
  closeDeposition: (depositionId: string) => void;
  /**
   * Record the verdict and release the measured values into BioRepo as
   * evidence. Never writes a parameter override (§5).
   */
  reconcileDeposition: (
    depositionId: string,
    outcome: 'confirmed' | 'refuted' | 'inconclusive',
    note: string,
  ) => void;

  // durable tier (OF-BLD-006 §4.6)
  /** Re-apply a persisted snapshot over the seeded state. Idempotent. */
  hydrateDurable: () => Promise<void>;
  applyDurable: (snap: DurableSnapshot) => void;
  /** Whether this browser can persist at all — surfaced honestly in Settings. */
  durableReady: boolean;
  /**
   * The person deciding, as typed in Settings (OF-BLD-012.1 F2). Read through
   * `reviewerName()` rather than directly, so every decision and every audit
   * line is signed the same way. Empty until set.
   */
  reviewer: string;
  setReviewerName: (name: string) => void;
  /**
   * The projects the service holds (alpha 2.0, ADR-005), oldest first; null
   * until asked. Every record the service keeps belongs to one of them.
   */
  projects: Project[] | null;
  /** Why the projects could not be listed, in words; null when they were. */
  projectsProblem: string | null;
  /** The project this page acts in, named on every call to the service. */
  projectId: string | null;
  /**
   * Ask the service for its projects. The project remembered here stays open
   * while the service holds it; with none open and exactly one held, that one
   * opens.
   */
  loadProjects: () => Promise<void>;
  /** Open another project. The page reloads, so nothing of the last one is left showing. */
  openProject: (id: string) => void;
  /** Make a project, signed with the reviewer name, and open it. */
  createProject: (asked: { name: string; description?: string }) => Promise<Project>;
  /**
   * What the open project holds of its pages, as last loaded or sent: the
   * base the next change is compared with (lib/projectState.ts). Null until
   * the project's rows have loaded, and nothing is sent before then.
   */
  stateSeen: ProjectState | null;
  /** Project rows the service has not yet acknowledged, oldest first. */
  stateOutbox: OutboxEntry[];
  /** Rows this browser kept itself before alpha 2.0, until a project is open to carry them to. */
  stateLegacy: ProjectState | null;
  /** Why the open project's rows could not be loaded, in words; null when they were. */
  stateProblem: string | null;
  /** Load the open project's rows, lay the unsent ones over them, and send what is owed. */
  hydrateProjectState: () => Promise<void>;
  /** Put a project's rows in the page. */
  applyProjectState: (state: ProjectState) => void;
  /** Send the outbox; what the service does not answer stays for the next try. */
  flushProjectState: () => Promise<void>;
  /**
   * The review decisions the Durable tier restored, with the snapshot's
   * savedAt — kept so a server decision for the same record can be compared
   * against them: the later of the two wins (OF-BLD-012 §7.3).
   */
  durableReview: { savedAt: string; decisions: Record<string, DurableReviewDecision> } | null;
  /** ISO time of the decision currently applied to each record, whoever made it; persisted as the Durable decision's `at`. */
  decisionAt: Record<string, string>;
  /** Decisions the service refused this session, by record id, with the rule — not posted again until the record changes. */
  refusedDecisions: Record<string, string>;

  // service overlay (OF-BLD-012 §2.1)
  /** Whether openferment-core answered /api/health this session. null = not asked yet. */
  serviceUp: boolean | null;
  /** The overlay as last received, merged. Later views (runs, candidates) read it here. */
  overlay: Overlay | null;
  /** Apply an overlay over the seed. Idempotent; merges into any overlay already applied. */
  applyOverlay: (overlay: Overlay) => void;
  /** Ask the service for its overlay and apply it. Silent when there is no service. */
  hydrateOverlay: () => Promise<void>;
  /** One structured model response over a fetched paper, through the service (§6.3); then the overlay again. */
  extractPaperLive: (paperId: string) => Promise<void>;
  completeJob: (id: string) => void;
  /** Put one record's card in front of the reviewer — the reader's rail links here. */
  focusReview: (recordId: string) => void;
  /** Post one decision to the service; `biorepo.write` stores it or refuses it (§7.2–7.3). */
  postReviewDecision: (decision: ReviewDecision) => Promise<void>;
  /** Post every decision this browser made that the service lacks or has an older one of (§7.3). */
  syncDecisions: () => Promise<void>;

  // ── Guild: the competence ledger (OF-BLD-013 §1.3) ────────────────────
  /**
   * The ledger as this browser knows it: the service's when it answers,
   * otherwise what the Durable tier kept. Levels are computed from it by
   * `competenceOf` wherever a screen needs them; nothing here stores one.
   */
  guild: Guild;
  /** People and entries made here that the service has not stored yet, by id. */
  guildPending: string[];
  /** Withdrawals made here that the service has not stored yet. */
  guildPendingWithdrawals: GuildWithdrawal[];
  /** Who is signing, as chosen in Guild's header. A claim, until there is sign-in. */
  guildActingId: string | null;
  /**
   * OF-BLD-014 §7.4 — fermOS's fits made in this session, by deposition id,
   * so Forecast can offer them. Ephemeral: a fit is kept by the service as
   * an artifact.
   */
  fermosFits: Record<string, FermosFitResponse>;
  keepFermosFit: (fit: FermosFitResponse) => void;
  /**
   * OF-BLD-020 §7.2 — the trains pureOS's proposer proposed in this session,
   * by the train id this browser gave each (time-based, `tr-…`): the service's
   * proposal whole, its train carrying that id, its reasons and what is
   * missing. pureOS's Builder opens one at /pureos/build/<id>. Ephemeral: the
   * proposal is the service's, and a person keeps a train by saving it from
   * the Builder.
   */
  proposedTrains: Record<string, TrainProposal>;
  /** Keep a proposal that proposed a train under a new train id, and return the id; null when it proposed none. */
  keepProposedTrain: (proposal: TrainProposal) => string | null;
  /**
   * OF-BLD-020 §5.R (finding 13) — what pureOS's Builder shows of a train in
   * this session, by the train's id: the newest run made on the page, what
   * the service said reading the train from a run (`?from=`), the train a
   * model built that it copies (`?copy=`), and whether Price this in Proforma
   * is open. Save moves a new train to its own address, which mounts the page
   * afresh; the page reads these back, so nothing it showed is lost.
   * Ephemeral: the run is the service's artifact, and the train is kept by
   * Save.
   */
  builderShown: Record<string, BuilderShown>;
  showInBuilder: (trainId: string, shown: Partial<BuilderShown>) => void;
  /** Whether the Durable tier's copy of the ledger has been read this session. */
  guildHydrated: boolean;
  /**
   * Practice as the service last answered it (OF-BLD-013 §4.3): every
   * scenario drafted and every session held. Null until asked, and while the
   * service is down. The service's state, so it is never in the Durable tier.
   */
  practice: Practice | null;
  loadPractice: () => Promise<Practice | null>;
  /** A drafted scenario, or a session the tutor just answered, merged into `practice`. */
  mergePractice: (item: { scenario?: PracticeScenario; session?: PracticeSession }) => void;
  /**
   * A session just closed. For a learner on the ledger the service has
   * already put practice on it, so the ledger is fetched again.
   */
  practiceClosed: (session: PracticeSession, title: string) => Promise<void>;
  /** Guild's checks as the service last answered (OF-BLD-013 §5.4), or null. */
  checks: Checks | null;
  loadChecks: () => Promise<void>;
  /** Each returns null when it worked, or why it did not, in words. */
  checksPropose: () => Promise<{ made: number } | { why: string }>;
  checksRequest: (personId: string, skillIds: string[]) => Promise<string | null>;
  checksSchedule: (checkId: string, day: string) => Promise<string | null>;
  checksDismiss: (checkId: string, reason: string) => Promise<string | null>;
  checksBrief: (checkId: string) => Promise<string | null>;
  checksRecord: (checkId: string, results: CheckResult[], notes: CheckNote[], at: string) => Promise<string | null>;
  guildAddPerson: (input: Pick<GuildPerson, 'name' | 'title' | 'role' | 'joinedAt'>) => Promise<GuildPerson | null>;
  guildUpdatePerson: (person: GuildPerson) => Promise<GuildPerson | null>;
  guildRecord: (entry: Omit<GuildEvidence, 'id' | 'recordedAt'>) => Promise<GuildEvidence | null>;
  guildWithdraw: (evidenceId: string, reason: string) => Promise<boolean>;
  /**
   * The lead's gate modes and check rate (OF-BLD-013 §5.1). Needs the
   * service, which holds them for every device; with the sample shown it
   * changes the sample alone. False when nothing changed, and a toast says why.
   */
  guildSetPolicy: (policy: Pick<GuildPolicy, 'routineGate' | 'criticalGate' | 'checksPerQuarter'>) => Promise<boolean>;
  guildSetActing: (id: string | null) => void;
  /** Who is performing this run's steps (OF-BLD-013 §2). A handover is a change of operator. */
  setRunOperator: (runId: string, personId: string | null) => void;
  /** Who stood beside the operator for one step, or null to clear it. */
  setRunCosigner: (runId: string, stepId: string, personId: string | null) => void;
  /**
   * What completing a step writes to Guild's ledger, once per step per run:
   * a run alone where the operator holds every skill, a supervised run where a
   * cosigner stood beside them, a deviation where the step went ahead without
   * the level it needs. Returns how many deviations it wrote.
   */
  recordStepForGuild: (runId: string, stepId: string) => Promise<number>;
  /**
   * A step the gate holds was skipped (OF-BLD-013 §5.5). The skip stands,
   * with its reason, and goes on the operator's ledger as a deviation on each
   * skill the step needs, so an assessor sees a held step that was passed
   * over. Returns how many deviations it wrote.
   */
  recordHeldSkipForGuild: (runId: string, stepId: string, reason: string, hold: string) => Promise<number>;
  /**
   * A lesson's checkpoint was just passed (OF-BLD-013 §3.2). Writes one
   * knowledge entry per skill the lesson counts toward, for whoever is
   * signing in Guild, once per person, lesson and skill. Null when the lesson
   * counts toward no skill or nobody who can hold skills is signing.
   */
  recordLessonForGuild: (lessonId: string) => Promise<{ personId: string; skills: string[] } | null>;
  /** Post what this browser made offline, then take the service's ledger as the truth. */
  syncGuild: () => Promise<void>;

  // misc
  logActivity: (e: ActivityEvent) => void;
  logExport: (name: string, rows: number) => void;
  /** Settings → Clear this browser's data: the Durable tier, and the copies in memory it restores. */
  clearBrowserData: () => void;
}

/**
 * Enforcement rather than convention (OF-BLD-006 §3.3).
 *
 * A comment saying "do not mutate this after locking" is a comment. Freezing
 * the arrays and the objects inside them means a stray `push` or an assignment
 * throws in module strict mode, at the line that did it, instead of quietly
 * shifting a prediction toward a result somebody has already seen.
 *
 * Applied after `structuredClone`, because cloning produces fresh mutable
 * objects and freezing the module constant would not protect the store's copy.
 */
function freezeLocked(runbooks: Runbook[]): Runbook[] {
  for (const r of runbooks) {
    if (!r.lockedAt) continue;
    r.predictions.forEach((p) => Object.freeze(p));
    r.measurementSchema.forEach((m) => Object.freeze(m));
    Object.freeze(r.predictions);
    Object.freeze(r.measurementSchema);
  }
  return runbooks;
}

// alpha 2.0 ships no seeded science (ADR-010): every list starts empty and is
// filled from the service, a project's records from stage 2 on.
const seedState = () => ({
  papers: [] as Paper[],
  records: [] as ExtractionRecord[],
  runOutputs: [],
  strains: [] as Strain[],
  products: [] as Product[],
  runbooks: freezeLocked([] as Runbook[]),
  skills: [] as Skill[],
  depositions: [] as Deposition[],
  measuredEvidence: [] as MeasuredEvidence[],
  protocols: [] as Protocol[],
  scenarios: [] as Scenario[],
  // Activity starts empty: what lands in it is what a person did in this
  // browser, never an authored history (OF-BLD-016 §3.1).
  modules: [] as LearnModule[],
  activity: [] as ActivityEvent[],
  liveConversations: [] as LiveConversation[],
  runs: {} as Record<string, RunState>,
  activeRunId: null,
  jobs: [] as Job[],
  serviceUp: null as boolean | null,
  overlay: null as Overlay | null,
  reviewQueue: [] as string[],
  reviewIndex: 0,
  reviewStats: { accepted: 0, rejected: 0, edited: 0, skipped: 0, gold: 0, startedAt: Date.now() },
  undoStack: [] as UndoFrame[],
  learnProgress: {} as Record<string, boolean>,
  proformaAssumptions: {} as Record<string, InputAssumption[]>,
  parameterOverrides: {} as Record<string, Override[]>,
  proformaFits: {} as Record<string, Record<string, string>>,
  trainsMade: {} as Record<string, TrainMade>,
  adoptedRunbookIds: [] as string[],
  createdScenarioIds: [] as string[],
  exports: [] as { name: string; at: string; rows: number }[],
});

/**
 * Open in the viewer's theme rather than always in Bench. Night Shift exists
 * for late lab sessions and projector-hostile rooms (§6.2); starting in the
 * wrong one and making the user find the toggle is a small rudeness. The top
 * bar toggle still wins once touched.
 */
function initialTheme(): Theme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'bench';
  const stamped = document.documentElement.dataset.theme;
  if (stamped === 'dark') return 'night';
  if (stamped === 'light') return 'bench';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'bench';
}

/** What kind of source a collector serves, for a paper made from the overlay. */
const SOURCE_TYPES: Partial<Record<NonNullable<OverlayPaper['source']>, Paper['sourceType']>> = {
  europepmc: 'journal-article',
  osti: 'industry-report',
  sgd: 'database-entry',
};

/**
 * A document the project holds, as a paper (ADR-002): the citation the kit
 * holds, its passages as its sections, its licence. Nothing is filled in
 * that the kit does not hold; a year it does not know stays unset.
 */
function paperOf(id: string, o: OverlayPaper): Paper {
  return {
    id,
    title: o.title ?? id,
    authors: o.authors ?? [],
    year: o.year ?? undefined,
    venue: o.journal ?? '',
    organisms: [],
    topics: [],
    abstract: '',
    sections: o.sections,
    ingest: o.ingest,
    textSource: o.textSource,
    openAccess: o.licenceClass === 'public' || o.licenceClass === 'open_commercial' || o.licenceClass === 'open_noncommercial',
    doi: o.doi ?? undefined,
    pmcid: o.pmcid ?? undefined,
    sourceUrl: o.url ?? undefined,
    sourceType: o.source ? SOURCE_TYPES[o.source] : undefined,
    license: o.license ?? undefined,
    licenceClass: o.licenceClass ?? undefined,
    fetchedFrom: o.source,
    held: true,
  };
}

export const useStore = create<OFState>()((set, get) => ({
  ...seedState(),
  toasts: [],
  durableReady: false,
  durableReview: null as { savedAt: string; decisions: Record<string, DurableReviewDecision> } | null,
  decisionAt: {} as Record<string, string>,
  refusedDecisions: {} as Record<string, string>,
  ui: {
    theme: initialTheme(),
    density: 'comfortable',
    reducedMotion: false,
    unitMode: 'published',
    paletteOpen: false,
    jobsOpen: false,
    sessionsOpen: true,
    railCollapsed: false,
    tourStop: null,
    helpOpen: false,
    newScenarioOpen: false,
  },

  setUI: (patch) => set((s) => ({ ui: { ...s.ui, ...patch } })),

  reviewer: '',
  setReviewerName: (name) => set({ reviewer: name }),

  projects: null,
  projectsProblem: null,
  projectId: openProjectId(),
  stateSeen: null,
  stateOutbox: [],
  stateLegacy: null,
  stateProblem: null,

  loadProjects: async () => {
    let listed: Project[];
    try {
      listed = await call<Project[]>('/api/projects');
    } catch (e) {
      set({ projectsProblem: e instanceof Error ? e.message : String(e) });
      projectSettled();
      return;
    }
    const open = get().projectId;
    const keep = open && listed.some((p) => p.id === open) ? open : listed.length === 1 ? listed[0].id : null;
    if (keep !== open) setOpenProjectId(keep);
    set({ projects: listed, projectsProblem: null, projectId: keep });
    projectSettled();
  },

  openProject: (id) => {
    if (id === get().projectId) return;
    setOpenProjectId(id);
    set({ projectId: id });
    window.location.reload();
  },

  createProject: async (asked) => {
    const by = reviewerName();
    if (!by) throw new Error('Set your reviewer name in Settings first: a project is made in a person\'s name.');
    const made = await call<Project>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: asked.name, description: asked.description ?? '', by }),
    });
    set((s) => ({ projects: [...(s.projects ?? []), made] }));
    get().openProject(made.id);
    return made;
  },

  hydrateProjectState: async () => {
    const project = get().projectId;
    if (!project) return;
    let held: ProjectState;
    try {
      held = await loadProjectState();
    } catch (e) {
      set({ stateProblem: e instanceof Error ? e.message : String(e) });
      return;
    }
    // Rows this browser kept before alpha 2.0 go to the open project, once.
    const legacy = get().stateLegacy;
    const outbox = legacy ? enqueue(get().stateOutbox, changes(EMPTY_STATE, legacy, project, decidedBy())) : get().stateOutbox;
    // What this browser still owes the service stands over what it holds.
    get().applyProjectState(applyEntries(held, outbox.filter((e) => e.project === project)));
    set({ stateSeen: projectStateOf(get()), stateOutbox: outbox, stateLegacy: null, stateProblem: null });
    if (legacy)
      get().logActivity({
        at: stamp(),
        icon: 'upload',
        text: 'The depositions, locks, scenarios, trains and conversations this browser kept itself are being sent to the open project',
        href: '#/',
        provenance: 'user',
      });
    void get().flushProjectState();
  },

  applyProjectState: (state) =>
    set((s) => {
      const adopted = new Set(state.runbooks.map((r) => r.id));
      // Runbooks adopted from a draft first, then every lock laid on by id.
      const runbooks = [...state.runbooks, ...s.runbooks.filter((r) => !adopted.has(r.id) && !s.adoptedRunbookIds.includes(r.id))].map(
        (r) => {
          const l = state.runbookLocks[r.id];
          return l && !r.lockedAt ? { ...r, lockedAt: l.lockedAt, lockHash: l.lockHash } : r;
        },
      );
      const made = new Set(state.scenarios.map((sc) => sc.id));
      return {
        depositions: state.depositions,
        measuredEvidence: state.measuredEvidence,
        runbooks: freezeLocked(runbooks),
        adoptedRunbookIds: [...adopted],
        parameterOverrides: state.overrides,
        proformaAssumptions: assumptionsFromOverrides(state.overrides),
        proformaFits: state.fits,
        scenarios: [...s.scenarios.filter((sc) => !made.has(sc.id) && !s.createdScenarioIds.includes(sc.id)), ...state.scenarios],
        createdScenarioIds: [...made],
        trainsMade: state.trains,
        // A turn the service reads as running is being answered there; the screen follows it.
        liveConversations: mergeConversations(state.conversations, []),
      };
    }),

  flushProjectState: async () => {
    if (stateFlushing) return;
    stateFlushing = true;
    try {
      for (;;) {
        const pending = get().stateOutbox;
        if (!pending.length) return;
        const { left, sent, refused } = await flush(pending);
        set((s) => ({ stateOutbox: [...left, ...s.stateOutbox.filter((e) => !pending.includes(e))] }));
        for (const { entry, why } of refused)
          get().logActivity({
            at: stamp(),
            icon: 'alert',
            text: `The service refused ${entry.kind} ${entry.id} and it was dropped: ${why}`,
            href: '#/',
            provenance: 'user',
          });
        if (refused.length)
          get().toast({ text: `The service refused ${refused.length} change${refused.length === 1 ? '' : 's'}: ${refused[0].why}`, kind: 'error' });
        if (left.length) {
          // The service did not answer; try again shortly, and on the next change.
          if (stateRetry === null) stateRetry = setTimeout(() => {
            stateRetry = null;
            void get().flushProjectState();
          }, STATE_RETRY_MS);
          return;
        }
        if (!sent) return;
      }
    } finally {
      stateFlushing = false;
    }
  },

  // Outside seedState: a reset discards the session's work, not what the
  // person chose to see.

  guild: EMPTY_GUILD,
  guildPending: [] as string[],
  guildPendingWithdrawals: [] as GuildWithdrawal[],
  guildActingId: null as string | null,
  fermosFits: {} as Record<string, FermosFitResponse>,
  // By run, and by family when it is not the logistic (OF-BLD-020 §3.3): a run keeps one fit of each family.
  keepFermosFit: (fit: FermosFitResponse) =>
    set((s) => {
      const model = fit.kinetic?.model ?? 'logistic_v0';
      const key = model === 'logistic_v0' ? fit.depositionId : `${fit.depositionId} · ${model}`;
      return { fermosFits: { ...s.fermosFits, [key]: fit } };
    }),
  proposedTrains: {} as Record<string, TrainProposal>,
  // OF-BLD-020 §7.2: a new id (as a made scenario's, `nextId` restarting on a
  // reload); the service's train, reasons and missing list kept as it sent them.
  keepProposedTrain: (proposal: TrainProposal) => {
    if (!proposal.train) return null;
    const id = timeId('tr');
    const train = { ...proposal.train, id };
    set((s) => ({ proposedTrains: { ...s.proposedTrains, [id]: { ...proposal, train } } }));
    return id;
  },
  builderShown: {} as Record<string, BuilderShown>,
  showInBuilder: (trainId: string, shown: Partial<BuilderShown>) =>
    set((s) => ({ builderShown: { ...s.builderShown, [trainId]: { ...(s.builderShown[trainId] ?? {}), ...shown } } })),
  guildHydrated: false,
  practice: null as Practice | null,
  checks: null as Checks | null,

  toast: (t) => {
    const id = nextId('toast');
    set((s) => ({ toasts: [...s.toasts.slice(-2), { ...t, id }] }));
    setTimeout(() => get().dismissToast(id), 6000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  // ── review ───────────────────────────────────────────────────────────
  startReview: (ids) =>
    set({
      reviewQueue: ids,
      reviewIndex: 0,
      undoStack: [],
      reviewStats: { accepted: 0, rejected: 0, edited: 0, skipped: 0, gold: 0, startedAt: Date.now() },
    }),

  reviewDecide: (id, action, payload) => {
    const s = get();
    const before = s.records.find((r) => r.id === id);
    if (!before) return;
    // OF-BLD-012 §7.3 — what the service would say, said here first.
    const paper = s.papers.find((p) => p.id === before.paperId);
    const candidates = s.overlay?.candidates ?? [];
    // A refusal that blocks (no full text, no anchoring sentence) stops here.
    // The one that does not — the paper has no identifier — lets the review
    // go on in this browser and keeps the decision from the service.
    const refusal =
      action === 'skip' ? null : writeRefusal(action, before, paper, candidates, s.serviceUp, reviewerName());
    if (blocks(refusal)) {
      get().toast({ text: refusal!.why, kind: 'error' });
      return;
    }
    // A promotion on a curated record whose quote is not in the fetched text
    // carries the extractor's agreeing span — and the paper's own number, as
    // the correction — so the promoted record anchors in the paper's words
    // and the service finds that number inside them (§2.4 rule 3).
    const span = action === 'accept' || action === 'gold' ? carryOverSpan(before, paper, candidates) : null;
    const reanchor = (r: ExtractionRecord, audit: AuditEvent[]): ExtractionRecord => {
      if (!span) return r;
      audit.push({
        at: stamp(),
        who: decidedBy(),
        action: `span re-anchored to the extractor's quote (${span.candidateId})`,
        from: r.quote,
        to: span.quote,
      });
      if (!spanChangesNumber(r, span)) return { ...r, quote: span.quote, sectionId: span.sectionId };
      audit.push({
        at: stamp(),
        who: decidedBy(),
        action: 'value taken as the paper writes it',
        from: `${r.value} ${r.unit}`,
        to: `${span.value} ${span.unit}`,
      });
      // spanChangesNumber holds only for two numbers.
      const corrected = { value: span.value as number, unit: span.unit };
      return {
        ...r,
        quote: span.quote,
        sectionId: span.sectionId,
        corrected,
        value: corrected.value,
        unit: corrected.unit,
        si: toSI(corrected.value, corrected.unit),
      };
    };
    const frame: UndoFrame = {
      records: structuredClone(s.records),
      recordIds: [id],
      queueIndex: s.reviewIndex,
      label: action,
    };
    const stats = { ...s.reviewStats };
    const records = s.records.map((r) => {
      if (r.id !== id) return r;
      const audit = [...r.audit];
      if (action === 'accept') {
        audit.push({ at: stamp(), who: decidedBy(), action: 'verified' });
        stats.accepted++;
        return { ...reanchor(r, audit), status: 'verified' as RecordStatus, reviewer: decidedBy(), audit };
      }
      if (action === 'reject') {
        audit.push({ at: stamp(), who: decidedBy(), action: `rejected — ${payload?.reason ?? 'unspecified'}` });
        stats.rejected++;
        // A rejected record is not in the gold set, whatever it was before.
        const { gold: _gold, ...rest } = r;
        return {
          ...rest,
          status: 'rejected' as RecordStatus,
          reviewer: decidedBy(),
          rejectReason: payload?.reason,
          audit,
        };
      }
      if (action === 'gold') {
        audit.push({ at: stamp(), who: decidedBy(), action: 'flagged for gold set' });
        stats.gold++;
        // The gold value is the number the record carries AFTER re-anchoring:
        // the paper's own, inside the sentence the service will anchor it in.
        const re = reanchor(r, audit);
        return {
          ...re,
          status: 'verified' as RecordStatus,
          reviewer: decidedBy(),
          gold: re.gold ?? { value: re.corrected?.value ?? re.value, unit: re.corrected?.unit ?? re.unit },
          audit,
        };
      }
      stats.skipped++;
      return r;
    });
    const now = new Date().toISOString();
    const { [id]: _refused, ...refusedDecisions } = s.refusedDecisions;
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: stats,
      reviewIndex: Math.min(s.reviewIndex + 1, s.reviewQueue.length),
      decisionAt: action === 'skip' ? s.decisionAt : { ...s.decisionAt, [id]: now },
      refusedDecisions: action === 'skip' ? s.refusedDecisions : refusedDecisions,
    });
    // §7.3 — the Durable tier keeps the decision offline; when the service is
    // up it is posted too, and `biorepo.write` is what stores it there.
    if (action !== 'skip' && s.serviceUp && !refusal) {
      const after = get().records.find((r) => r.id === id);
      if (after) void get().postReviewDecision(decisionOf(after, span, now));
    }
  },

  editRecord: (id, value, unit) => {
    const s = get();
    const frame: UndoFrame = {
      records: structuredClone(s.records),
      recordIds: [id],
      queueIndex: s.reviewIndex,
      label: 'edit',
    };
    const records = s.records.map((r) => {
      if (r.id !== id) return r;
      const si = toSI(value, unit);
      return {
        ...r,
        corrected: { value, unit },
        value,
        unit,
        si,
        audit: [
          ...r.audit,
          {
            at: stamp(),
            who: decidedBy(),
            action: 'edited value',
            from: `${r.value} ${r.unit}`,
            to: `${value} ${unit}`,
          },
        ],
      };
    });
    const now = new Date().toISOString();
    // A refusal was about the record as it was; an edit is a new decision.
    const { [id]: _refused, ...refusedDecisions } = s.refusedDecisions;
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: { ...s.reviewStats, edited: s.reviewStats.edited + 1 },
      decisionAt: { ...s.decisionAt, [id]: now },
      refusedDecisions,
    });
    // §7.3 — a correction is part of the decision about a record, and the
    // service holds it to §2.4 rule 5 (the range) like anything typed.
    if (s.serviceUp) {
      const after = get().records.find((r) => r.id === id);
      const paper = s.papers.find((p) => p.id === after?.paperId);
      if (after && !writeRefusal(actionOf(after), after, paper, s.overlay?.candidates ?? [], true, reviewerName())) {
        void get().postReviewDecision(decisionOf(after, reanchoredSpan(after), now));
      }
    }
  },

  setRecordStatus: (id, status, reason) =>
    set((s) => ({
      records: s.records.map((r) =>
        r.id === id
          ? {
              ...r,
              status,
              reviewer: decidedBy(),
              rejectReason: reason ?? r.rejectReason,
              audit: [...r.audit, { at: stamp(), who: decidedBy(), action: `set ${status}` }],
            }
          : r,
      ),
    })),

  undoReview: () => {
    const s = get();
    const frame = s.undoStack[s.undoStack.length - 1];
    if (!frame) return;
    // Restore only the records the undone action touched. The frame holds
    // every record, but a record another reviewer changed since — applied
    // here by a mid-session overlay — is not this browser's to take back,
    // and a candidate that arrived since is not the frame's to take away.
    const touched = new Set(frame.recordIds);
    const restored = new Map(frame.records.filter((r) => touched.has(r.id)).map((r) => [r.id, r]));
    const now = new Date().toISOString();
    const changed = [...restored.values()].filter((r) => {
      const current = s.records.find((c) => c.id === r.id);
      return current && !sameDecision(current, r);
    });
    const decisionAt = { ...s.decisionAt };
    const refusedDecisions = { ...s.refusedDecisions };
    for (const r of changed) {
      decisionAt[r.id] = now;
      delete refusedDecisions[r.id];
    }
    set({
      records: s.records.map((r) => restored.get(r.id) ?? r),
      reviewIndex: frame.queueIndex,
      undoStack: s.undoStack.slice(0, -1),
      decisionAt,
      refusedDecisions,
    });
    // §7.3 — an undo is a decision as well: the service must not keep a
    // status this browser has taken back. What the service would refuse —
    // an accept on an unfetched paper being restored — stays here.
    if (s.serviceUp) {
      for (const r of changed) {
        const paper = s.papers.find((p) => p.id === r.paperId);
        if (writeRefusal(actionOf(r), r, paper, s.overlay?.candidates ?? [], true, reviewerName())) continue;
        void get().postReviewDecision(decisionOf(r, reanchoredSpan(r), now));
      }
    }
  },

  advanceReview: (delta) =>
    set((s) => ({
      reviewIndex: Math.max(0, Math.min(s.reviewIndex + delta, s.reviewQueue.length)),
    })),

  // ── jobs ─────────────────────────────────────────────────────────────
  startJob: (job) => {
    const id = nextId('job');
    set((s) => ({
      jobs: [
        ...s.jobs,
        { ...job, id, stageIndex: 0, stageProgress: 0, status: 'running', startedAt: Date.now() },
      ],
    }));
    return id;
  },

  failJob: (id, reason) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, status: 'failed', failReason: reason } : j)),
    })),

  completeJob: (id) =>
    set((s) => ({
      jobs: s.jobs.map((j) =>
        j.id === id ? { ...j, stageIndex: j.stages.length, stageProgress: 1, status: 'done' } : j,
      ),
    })),

  clearJobs: () => set((s) => ({ jobs: s.jobs.filter((j) => j.status === 'running') })),

  // ── ingest ───────────────────────────────────────────────────────────
  //
  // When openferment-core answers /api/health the paper is fetched for real
  // from Europe PMC and its own text replaces the curation note (OF-BLD-012
  // §5.4). When it does not, nothing is fetched, and the toast names the
  // missing service and the command that starts it.
  extractPaperLive: async (paperId) => {
    const id = get().startJob({
      title: `Extract ${paperId}`,
      kind: 'ingest',
      stages: [{ label: 'Extract', ms: 30000 }],
      href: `#/biorepo/witness`,
    });
    get().logActivity({
      at: stamp(),
      icon: 'sparkles',
      text: `Extracting ${paperId} — one structured model response over its full text`,
      href: '#/intake/ingest',
      provenance: 'user',
    });
    try {
      const result = await extractPaper(paperId);
      get().completeJob(id);
      const dropped = Object.entries(result.rejectionReasons)
        .filter(([, n]) => n > 0)
        .map(([rule, n]) => `${rule} ${n}`)
        .join(', ');
      get().toast({
        text: `${paperId} extracted — ${result.candidates.length} candidate${result.candidates.length === 1 ? '' : 's'} anchored, ${result.rejected} refused${dropped ? ` (${dropped})` : ''}, $${result.usage.costUsd.toFixed(4)}`,
        kind: 'success',
        href: '#/biorepo/witness',
        hrefLabel: 'Open Witness',
      });
    } catch (e) {
      const message =
        e instanceof IntakeDown ? `${e.message} ${e.remedy}` : e instanceof Error ? e.message : String(e);
      get().failJob(id, message);
      if (e instanceof IntakeDown && /not running/.test(e.message)) set({ serviceUp: false });
      get().toast({ text: `Extract ${paperId} failed — ${message}`, kind: 'error' });
      return;
    }
    // The run, the candidates and the decisions are recomputed server-side;
    // ask for them again so Witness and Guild move.
    await get().hydrateOverlay();
  },

  // ── runs ─────────────────────────────────────────────────────────────
  startRun: (protocolId, version, scale) => {
    const id = nextId('run');
    const run: RunState = {
      id,
      protocolId,
      version,
      scale,
      startedAt: Date.now(),
      currentStep: 0,
      completed: {},
      skipped: {},
      checks: {},
      deviations: [],
      timers: [],
      // OF-BLD-013 §2 — whoever is signing in Guild runs it, when they can hold skills.
      operatorId: runOperatorDefault(get()),
      cosigned: {},
      guildRecorded: {},
    };
    set((s) => ({ runs: { ...s.runs, [id]: run }, activeRunId: id }));
    return id;
  },

  completeStep: (runId, stepId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: { ...run, completed: { ...run.completed, [stepId]: Date.now() } },
        },
      };
    }),

  uncompleteStep: (runId, stepId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      const completed = { ...run.completed };
      delete completed[stepId];
      return { runs: { ...s.runs, [runId]: { ...run, completed } } };
    }),

  skipStep: (runId, stepId, reason) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, skipped: { ...run.skipped, [stepId]: reason } } },
      };
    }),

  setRunStep: (runId, index) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return { runs: { ...s.runs, [runId]: { ...run, currentStep: Math.max(0, index) } } };
    }),

  toggleCheck: (runId, stepId, idx) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      const arr = [...(run.checks[stepId] ?? [])];
      arr[idx] = !arr[idx];
      return { runs: { ...s.runs, [runId]: { ...run, checks: { ...run.checks, [stepId]: arr } } } };
    }),

  addDeviation: (runId, d) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return { runs: { ...s.runs, [runId]: { ...run, deviations: [...run.deviations, d] } } };
    }),

  addTimer: (runId, t) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      if (run.timers.some((x) => x.id === t.id)) return {};
      const timer: TimerState = { ...t, remainingSec: t.totalSec, running: true, startedAt: Date.now() };
      return { runs: { ...s.runs, [runId]: { ...run, timers: [...run.timers, timer] } } };
    }),

  toggleTimer: (runId, timerId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: {
            ...run,
            timers: run.timers.map((t) => (t.id === timerId ? { ...t, running: !t.running } : t)),
          },
        },
      };
    }),

  extendTimer: (runId, timerId, sec) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: {
            ...run,
            timers: run.timers.map((t) =>
              t.id === timerId
                ? { ...t, remainingSec: t.remainingSec + sec, totalSec: t.totalSec + sec }
                : t,
            ),
          },
        },
      };
    }),

  dismissTimer: (runId, timerId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, timers: run.timers.filter((t) => t.id !== timerId) } },
      };
    }),

  tickTimers: (dtMs) => {
    const s = get();
    // A bench timer runs at wall-clock speed, always (OF-BLD-016 §3.R).
    const dt = dtMs / 1000;
    const finishedTimers: TimerState[] = [];
    const runs = { ...s.runs };
    let changed = false;
    for (const [id, run] of Object.entries(runs)) {
      if (!run.timers.some((t) => t.running && t.remainingSec > 0)) continue;
      changed = true;
      runs[id] = {
        ...run,
        timers: run.timers.map((t) => {
          if (!t.running || t.remainingSec <= 0) return t;
          const remainingSec = Math.max(0, t.remainingSec - dt);
          if (remainingSec === 0) finishedTimers.push({ ...t, remainingSec, running: false });
          return { ...t, remainingSec, running: remainingSec > 0 };
        }),
      };
    }
    if (changed) set({ runs });
    for (const f of finishedTimers) {
      get().toast({ text: `Timer complete — ${f.label}`, kind: 'success' });
    }
  },

  finishRun: (runId) => {
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, finishedAt: Date.now() } },
        activeRunId: s.activeRunId === runId ? null : s.activeRunId,
      };
    });
    const run = get().runs[runId];
    const proto = get().protocols.find((p) => p.id === run?.protocolId);
    if (proto) {
      get().logActivity({
        at: stamp(),
        icon: 'check',
        text: `Run completed — ${proto.title}`,
        href: `#/runbooks/protocols/${proto.id}`,
        provenance: 'user',
      });
    }
  },

  addProtocolVersion: (protocolId, version) =>
    set((s) => ({
      protocols: s.protocols.map((p) =>
        p.id === protocolId
          ? { ...p, versions: [...p.versions, version], currentVersion: version.version }
          : p,
      ),
    })),

  // ── runbooks (OF-BLD-005 §7, §8) ─────────────────────────────────────

  promoteRunbook: (runbookId) => {
    const s = get();
    const source = s.runbooks.find((r) => r.id === runbookId);
    if (!source || source.kind !== 'research') return null;

    const product = source.productId
      ? s.products.find((p) => p.id === source.productId)
      : undefined;
    const id = nextId('rb');

    // The research runbook's own findings become the industrial one's first
    // stage. Promotion carries the answer across; it does not restart the work.
    const carried = source.stages
      .filter((st) => st.status === 'done' && (st.value || st.detail))
      .map((st) => st.value ?? st.detail)
      .filter(Boolean)
      .join('; ');

    const runbook: Runbook = {
      id,
      kind: 'industrial',
      title: `${product?.name ?? source.title} — process definition`,
      // Nothing runs behind the process stages yet: a draft (OF-BLD-016 §3.R).
      status: 'draft',
      stages: [
        {
          name: 'Research findings',
          status: 'done',
          detail: carried || `Carried from ${source.id}`,
          value: null,
        },
        {
          name: 'Host & construct selection',
          status: 'pending',
          detail: product ? `Starting from ${product.defaultStrainId}` : null,
          value: null,
        },
        { name: 'Process train', status: 'queued', detail: null, value: null },
        { name: 'Titre & yield model', status: 'pending', detail: null, value: null },
        { name: 'Equipment & CAPEX', status: 'pending', detail: null, value: null },
        { name: 'Quality spec', status: 'pending', detail: null, value: null },
        {
          name: 'Storage & export',
          status: 'pending',
          detail: 'The cold-chain decision — ambient if the molecule tolerates it',
          value: null,
        },
      ],
      note: `Promoted from ${source.id}. A research runbook that finds something becomes an industrial one in a single action, and the finding travels with it rather than being retyped.`,
      eta: null,
      outputs: [],
      productId: source.productId,
      progressPct: 0,
      estCostUsd: null,
      strainId: source.strainId ?? product?.defaultStrainId ?? null,
      // Promotion carries the research finding across verbatim. It does NOT
      // invent process predictions: the titre and recovery models have not run,
      // so those are measured with `predictionId: null` rather than predicted
      // against a number somebody made up at promotion time. When the process
      // stages do produce predictions, that is a new version — this one is
      // locked, and locked means superseded, not edited.
      predictions: source.predictions.map((p) => ({ ...p, id: `${id}-${p.id}` })),
      measurementSchema: [
        ...source.measurementSchema.map((m) => ({
          ...m,
          id: `${id}-${m.id}`,
          predictionId: m.predictionId ? `${id}-${m.predictionId}` : null,
        })),
        {
          id: `${id}-ms-titre`,
          label: 'Titre at harvest',
          unit: 'g/L',
          timepoint: 'harvest',
          predictionId: null,
        },
        {
          id: `${id}-ms-recovery`,
          label: 'Overall recovery',
          unit: '%',
          timepoint: 'post-purification',
          predictionId: null,
        },
      ],
      lockedAt: null,
      lockHash: null,
    };

    set((st) => ({ runbooks: [runbook, ...st.runbooks] }));
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: `Promoted ${source.title} to an industrial runbook`,
      href: `#/runbooks/${id}`,
      provenance: 'user',
    });
    get().toast({
      text: 'Promoted to an industrial runbook — the clearance finding came across with it',
      kind: 'success',
      href: `#/runbooks/${id}`,
      hrefLabel: 'Open',
    });
    return id;
  },

  resolveRunbookInput: (runbookId, mode) => {
    set((s) => ({
      runbooks: s.runbooks.map((r) => {
        if (r.id !== runbookId || r.status !== 'blocked_unverified') return r;
        let unblocked = false;
        const stages = r.stages.map((st) => {
          if (st.status === 'blocked') {
            unblocked = true;
            return {
              ...st,
              status: 'running' as const,
              detail:
                mode === 'source'
                  ? 'Source attached — the value now carries a citation and the cascade may consume it'
                  : 'Continuing on an explicit assumption — the value is labelled, and every number downstream of it inherits the label',
            };
          }
          // The stage that was waiting behind the block moves to the queue.
          if (unblocked && st.status === 'pending') {
            unblocked = false;
            return { ...st, status: 'queued' as const };
          }
          return st;
        });
        return { ...r, status: 'running' as const, stages, eta: null };
      }),
    }));

    const r = get().runbooks.find((x) => x.id === runbookId);
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text:
        mode === 'source'
          ? `Source attached — ${r?.title ?? runbookId} resumed`
          : `Marked an input an explicit assumption — ${r?.title ?? runbookId} resumed, labelled`,
      href: `#/runbooks/${runbookId}`,
      provenance: 'user',
    });
    get().toast({
      text:
        mode === 'source'
          ? 'Source attached. The cascade may consume the value now.'
          : 'Continuing on a labelled assumption. Everything downstream inherits the label.',
      kind: mode === 'source' ? 'success' : 'warn',
    });
  },

  authoriseRunbookBudget: (runbookId) => {
    set((s) => ({
      runbooks: s.runbooks.map((r) =>
        r.id === runbookId && r.status === 'awaiting_budget'
          ? {
              ...r,
              status: 'running' as const,
              stages: r.stages.map((st, i) =>
                st.status === 'queued' && i === r.stages.findIndex((x) => x.status === 'queued')
                  ? { ...st, status: 'running' as const }
                  : st,
              ),
            }
          : r,
      ),
    }));
    const r = get().runbooks.find((x) => x.id === runbookId);
    if (!r) return;
    // No timed job: nothing runs behind a runbook's stages yet (OF-BLD-016 §3.R).
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: `Budget authorised — ${r.title} started`,
      href: `#/runbooks/${runbookId}`,
      provenance: 'user',
    });
    get().toast({
      text: `Authorised. Estimated spend ${r.estCostUsd === null ? 'unpriced' : `$${r.estCostUsd}`}.`,
      kind: 'info',
    });
  },

  resolveRunbookReview: (runbookId, verdict) => {
    set((s) => ({
      runbooks: s.runbooks.map((r) =>
        r.id === runbookId && r.status === 'needs_review'
          ? {
              ...r,
              status: 'complete' as const,
              progressPct: 100,
              stages: r.stages.map((st) =>
                st.status === 'review'
                  ? { ...st, status: 'done' as const, detail: `Ruled on by a person — ${verdict}` }
                  : st,
              ),
              outputs: [...r.outputs, 'Boundary map', 'Reviewer decision'],
            }
          : r,
      ),
    }));
    const r = get().runbooks.find((x) => x.id === runbookId);
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: `Review recorded on ${r?.title ?? runbookId} — ${verdict}`,
      href: `#/runbooks/${runbookId}`,
      provenance: 'user',
    });
    get().toast({ text: 'Decision recorded against the runbook.', kind: 'success' });
  },

  lockRunbook: (runbookId) => {
    const r = get().runbooks.find((x) => x.id === runbookId);
    if (!r) return;
    if (r.lockedAt) {
      get().toast({ text: 'Already locked — supersede it to change anything.', kind: 'warn' });
      return;
    }
    if (r.predictions.length === 0) {
      get().toast({
        text: 'Nothing to lock. A runbook with no predictions has made no claim.',
        kind: 'warn',
      });
      return;
    }
    const lockedAt = new Date().toISOString();
    const lockHash = runbookLockHash(r.predictions, r.measurementSchema);
    set((s) => ({
      runbooks: freezeLocked(
        s.runbooks.map((x) => (x.id === runbookId ? { ...x, lockedAt, lockHash } : x)),
      ),
    }));
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: `Predictions frozen on ${r.title} — ${r.predictions.length} claim${r.predictions.length === 1 ? '' : 's'}`,
      href: `#/runbooks/${runbookId}`,
      provenance: 'user',
    });
    get().toast({
      text: `Locked. ${r.predictions.length} prediction${r.predictions.length === 1 ? '' : 's'} frozen against hash ${lockHash.slice(0, 8)}.`,
      kind: 'success',
    });
  },

  reviseRunbookPrediction: (runbookId, predictionId, value) => {
    const r = get().runbooks.find((x) => x.id === runbookId);
    if (!r) return false;
    if (r.lockedAt) {
      // The refusal names the way forward, in the house style: a dead end that
      // explains itself is a next step.
      get().toast({
        text: 'Refused — these predictions were frozen before the run. Supersede the runbook to revise them.',
        kind: 'warn',
      });
      return false;
    }
    if (!isFinite(value)) return false;
    set((s) => ({
      runbooks: s.runbooks.map((x) =>
        x.id === runbookId
          ? {
              ...x,
              predictions: x.predictions.map((p) => (p.id === predictionId ? { ...p, value } : p)),
            }
          : x,
      ),
    }));
    return true;
  },

  // OF-BLD-014 §9.2 — a draft becomes a research runbook, unlocked, with the
  // predictions and measures the service wrote. The person reads it and locks
  // it on the runbook's page. Its id is unique across reloads, because the
  // runbook outlives this page in the project's rows.
  adoptRunbookDraft: (draft) => {
    const id = `rb-draft-${Date.now().toString(36)}-${nextId('d').slice(2)}`;
    const runbook: Runbook = {
      id,
      kind: 'research',
      title: draft.title,
      status: 'draft',
      stages: [],
      note: 'Drafted by Postdoc from the evidence its tools returned; every value and interval was written by the service from the artifacts and records each prediction names. Read it, then lock it.',
      eta: null,
      outputs: [],
      productId: draft.productId,
      progressPct: 0,
      estCostUsd: null,
      strainId: draft.strainId,
      predictions: structuredClone(draft.predictions),
      measurementSchema: structuredClone(draft.measures),
      lockedAt: null,
      lockHash: null,
    };
    set((st) => ({ runbooks: [runbook, ...st.runbooks], adoptedRunbookIds: [...st.adoptedRunbookIds, id] }));
    get().logActivity({ at: stamp(), icon: 'runbook', text: `Runbook drafted by Postdoc adopted: ${draft.title}`, href: `#/runbooks/${id}`, provenance: 'user' });
    return id;
  },

  supersedeRunbook: (runbookId) => {
    const s = get();
    const source = s.runbooks.find((x) => x.id === runbookId);
    if (!source) return null;
    const id = nextId('rb');
    const revision: Runbook = {
      ...structuredClone({ ...source, predictions: source.predictions, measurementSchema: source.measurementSchema }),
      id,
      title: `${source.title} — revised`,
      status: 'draft',
      progressPct: 0,
      eta: null,
      outputs: [],
      note: `Supersedes ${source.id}, whose predictions were frozen on ${source.lockedAt?.slice(0, 10) ?? 'an unknown date'}. The original is left exactly as it was: a locked runbook is replaced, never rewritten, so the record of what was actually predicted survives the revision.`,
      lockedAt: null,
      lockHash: null,
    };
    set((st) => ({ runbooks: [revision, ...st.runbooks] }));
    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: `${source.title} superseded — predictions editable again in the revision`,
      href: `#/runbooks/${id}`,
      provenance: 'user',
    });
    get().toast({
      text: 'Revision opened. The locked original is untouched.',
      kind: 'info',
      href: `#/runbooks/${id}`,
      hrefLabel: 'Open',
    });
    return id;
  },

  // ── deposition (OF-BLD-006 §4) ───────────────────────────────────────

  openDeposition: (runbookId, protocolId, scale) => {
    const s = get();
    const protocol = s.protocols.find((p) => p.id === protocolId);
    if (!protocol) return null;
    const depositionId = nextId('dep');
    const deposition: Deposition = {
      id: depositionId,
      runbookId,
      protocolId,
      // OF-BLD-013 §2 — Guild's acting person, when the ledger has one who
      // holds skills.
      operatorId: runOperatorDefault(s),
      startedAt: new Date().toISOString(),
      closedAt: null,
      state: 'staged',
      entries: [],
      observations: [],
      reconciliation: null,
    };
    const runId = s.startRun(protocolId, protocol.currentVersion, scale);
    set((st) => ({
      depositions: [deposition, ...st.depositions],
      runs: { ...st.runs, [runId]: { ...st.runs[runId], depositionId } },
    }));
    get().logActivity({
      at: stamp(),
      icon: 'run',
      text: `Deposition staged — ${protocol.title}`,
      href: `#/runbooks/protocols/${protocolId}/run/${runId}`,
      provenance: 'user',
    });
    return { depositionId, runId };
  },

  beginDeposition: (depositionId) =>
    set((s) => ({
      depositions: s.depositions.map((d) =>
        d.id === depositionId && d.state === 'staged' ? { ...d, state: 'running' } : d,
      ),
    })),

  captureDeposition: (depositionId, stepId, raw, match) => {
    const at = new Date().toISOString();
    set((s) => ({
      depositions: s.depositions.map((d) => {
        if (d.id !== depositionId || d.state === 'closed') return d;
        if (match) {
          return {
            ...d,
            entries: [
              ...d.entries,
              {
                id: nextId('de'),
                measureId: match.measureId,
                stepId,
                at,
                value: match.value,
                unit: match.unit,
                raw,
                // Numbers entering the schema wait for a read-back (§4.4).
                confirmed: false,
              },
            ],
          };
        }
        // Everything the schema has no field for. This is the point: an
        // unexpected result has no column waiting for it, by definition.
        return {
          ...d,
          observations: [
            ...d.observations,
            { id: nextId('ob'), stepId, at, raw, structured: null },
          ],
        };
      }),
    }));
  },

  confirmEntry: (depositionId, entryId) =>
    set((s) => ({
      depositions: s.depositions.map((d) =>
        d.id === depositionId
          ? {
              ...d,
              entries: d.entries.map((e) => (e.id === entryId ? { ...e, confirmed: true } : e)),
            }
          : d,
      ),
    })),

  amendEntry: (depositionId, entryId, value) => {
    // Append-only: the mis-parse stays in the record with its raw text, and the
    // correction arrives as a new entry against the same measure. Overwriting
    // would destroy the evidence that the parse was ever wrong.
    const at = new Date().toISOString();
    set((s) => ({
      depositions: s.depositions.map((d) => {
        if (d.id !== depositionId || d.state === 'closed') return d;
        const original = d.entries.find((e) => e.id === entryId);
        if (!original) return d;
        const id = nextId('de');
        // A correction is the same reading: it keeps the reading's time (§7.1).
        const t = d.sampleTimes?.[entryId];
        return {
          ...d,
          ...(t !== undefined ? { sampleTimes: { ...d.sampleTimes, [id]: t } } : {}),
          entries: [
            ...d.entries,
            {
              ...original,
              id,
              at,
              value,
              raw: `${original.raw} → corrected to ${value} ${original.unit}`,
              confirmed: true,
            },
          ],
        };
      }),
    }));
  },

  setSampleTime: (depositionId, entryId, hours) =>
    set((s) => ({
      depositions: s.depositions.map((d) => {
        if (d.id !== depositionId) return d;
        const times = { ...(d.sampleTimes ?? {}) };
        if (hours === null || !Number.isFinite(hours)) delete times[entryId];
        else times[entryId] = hours;
        return { ...d, sampleTimes: times };
      }),
    })),

  setSeriesRole: (depositionId, measureId, role) =>
    set((s) => ({
      depositions: s.depositions.map((d) => {
        if (d.id !== depositionId) return d;
        const roles = { ...(d.seriesRoles ?? {}) };
        if (role === null) delete roles[measureId];
        else roles[measureId] = role;
        return { ...d, seriesRoles: roles };
      }),
    })),

  attachReadings: (depositionId, csv) => {
    let attached = 0;
    let kept = 0;
    set((s) => ({
      depositions: s.depositions.map((d) => {
        if (d.id !== depositionId || d.state === 'staged') return d;
        const rb = s.runbooks.find((r) => r.id === d.runbookId);
        const schema = rb?.measurementSchema ?? [];
        const { rows, unreadable } = parseReadingsCsv(csv);
        const at = new Date().toISOString();
        const entries = [...d.entries];
        const observations = [...d.observations];
        const times = { ...(d.sampleTimes ?? {}) };
        for (const row of rows) {
          const measureId = placeRow(row, schema);
          if (measureId) {
            const id = nextId('de');
            entries.push({ id, measureId, stepId: 'attached', at, value: row.value, unit: row.unit, raw: row.line, confirmed: false });
            times[id] = row.time;
            attached += 1;
          } else {
            observations.push({ id: nextId('ob'), stepId: 'attached', at, raw: row.line, structured: null });
            kept += 1;
          }
        }
        for (const line of unreadable) {
          observations.push({ id: nextId('ob'), stepId: 'attached', at, raw: line, structured: null });
          kept += 1;
        }
        return { ...d, entries, observations, sampleTimes: times };
      }),
    }));
    return { attached, kept };
  },

  structureObservation: (depositionId, observationId, structured) =>
    set((s) => ({
      depositions: s.depositions.map((d) =>
        d.id === depositionId
          ? {
              ...d,
              // `raw` is untouched. `structured` is derived and can be
              // re-derived; raw is its provenance.
              observations: d.observations.map((o) =>
                o.id === observationId ? { ...o, structured } : o,
              ),
            }
          : d,
      ),
    })),

  closeDeposition: (depositionId) => {
    set((s) => ({
      depositions: s.depositions.map((d) =>
        d.id === depositionId
          ? { ...d, state: 'closed' as const, closedAt: new Date().toISOString() }
          : d,
      ),
    }));
    const d = get().depositions.find((x) => x.id === depositionId);
    get().logActivity({
      at: stamp(),
      icon: 'check',
      text: `Deposition closed — ${d?.entries.length ?? 0} measured, ${d?.observations.length ?? 0} observed`,
      href: `#/runbooks/depositions/${depositionId}`,
      provenance: 'user',
    });
  },

  // ── scenarios ────────────────────────────────────────────────────────
  togglePin: (id) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, pinned: !sc.pinned } : sc)),
    })),

  duplicateScenario: (id) => {
    const s = get();
    const src = s.scenarios.find((x) => x.id === id);
    if (!src) return id;
    // A copy of a scenario on a shelf flowsheet is a scenario a person made:
    // Durable, time-based id, not run (OF-BLD-019 D6).
    if (src.kind === 'biosteam' && src.flowsheetId)
      return get().createScenario(
        src.flowsheetId,
        `${src.name} (copy)`,
        src.vessel && src.trainRun ? { vessel: src.vessel, trainRun: src.trainRun } : null,
      );
    const copy: Scenario = {
      ...structuredClone(src),
      id: nextId('sc'),
      name: `${src.name} (copy)`,
      pinned: false,
    };
    set({ scenarios: [...s.scenarios, copy] });
    return copy.id;
  },

  // OF-BLD-019 §3.1 (D5, D6) — New scenario makes a `biosteam` scenario and
  // nothing else. Its id is time-based, because nextId restarts on a reload
  // and this outlives one (as adopted runbooks and Live conversations do).
  // It holds no input value: the service binds records, and a named person
  // types an assumption on its page, kept in proformaAssumptions under its id.
  createScenario: (flowsheetId, name, parts) => {
    const id = timeId('sc');
    const made: Scenario = {
      id,
      modelId: flowsheetId,
      flowsheetId,
      kind: 'biosteam',
      name: name.trim() || flowsheetId,
      description: '',
      product: '',
      dims: [],
      point: {},
      assumptions: [],
      pinned: false,
      // OF-BLD-020 §6.1: what a scenario on custom_train_v1 is built from.
      ...(parts ? { vessel: parts.vessel, trainRun: parts.trainRun } : {}),
      lastRunId: null,
      createdAt: new Date().toISOString(),
    };
    set((s) => ({ scenarios: [...s.scenarios, made], createdScenarioIds: [...s.createdScenarioIds, id] }));
    return id;
  },

  recordScenarioRun: (id, artifactId) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, lastRunId: artifactId } : sc)),
    })),

  // ── Postdoc ──────────────────────────────────────────────────────────
  // Live conversations take time-based ids, because nextId restarts on a
  // reload and these outlive one (the same reason adopted runbooks do).
  startLiveConversation: (title) => {
    const id = timeId('lc');
    const conversation: LiveConversation = { id, title, startedAt: stamp(), turns: [] };
    set((s) => ({ liveConversations: [conversation, ...s.liveConversations].slice(0, MAX_LIVE_CONVERSATIONS) }));
    return id;
  },

  addLiveTurn: (conversationId, turn) =>
    set((s) => ({
      liveConversations: s.liveConversations.map((c) =>
        c.id === conversationId ? { ...c, turns: [...c.turns, turn] } : c,
      ),
    })),

  patchLiveTurn: (conversationId, turnId, { step, ...patch }) =>
    set((s) => ({
      liveConversations: s.liveConversations.map((c) =>
        c.id !== conversationId
          ? c
          : {
              ...c,
              turns: c.turns.map((t) =>
                t.id !== turnId ? t : { ...t, ...patch, steps: step ? [...t.steps, step] : (patch.steps ?? t.steps) },
              ),
            },
      ),
    })),

  dropLiveConversation: (conversationId) =>
    set((s) => ({ liveConversations: s.liveConversations.filter((c) => c.id !== conversationId) })),

  dropLiveTurn: (conversationId, turnId) =>
    set((s) => ({
      liveConversations: s.liveConversations.flatMap((c) => {
        if (c.id !== conversationId) return [c];
        const turns = c.turns.filter((t) => t.id !== turnId);
        return turns.length ? [{ ...c, turns }] : [];
      }),
    })),

  // ── learn ────────────────────────────────────────────────────────────
  // Lesson progress is this browser's and Durable (OF-BLD-013 §3.2): the map
  // remembers which lessons were finished here across a refresh. Whether a
  // person has passed one is the ledger's question, answered by
  // `recordLessonForGuild` at the moment the checkpoint is passed.
  completeLesson: (lessonId) =>
    set((s) => ({ learnProgress: { ...s.learnProgress, [lessonId]: true } })),

  // ── Proforma's assumptions (OF-BLD-014 §8.4) ──────────────────────────
  // A typed value carries the person and the day; the service refuses one
  // without a name, so the screen asks for a reviewer name first. Since
  // OF-BLD-020 §2.1 an assumption is the override its scenario's scope
  // holds for the input, and proformaAssumptions is read from the overrides.
  setProformaAssumption: (scenarioId, a) => get().setOverride(overrideOfAssumption(scenarioId, a)),
  clearProformaAssumption: (scenarioId, key) => get().clearOverride(proformaScope(scenarioId), key),

  // ── the parameter panel's overrides (OF-BLD-020 §2.1, D3) ─────────────
  // A person's change, under their name, by scope and key: one a parameter.
  // Reset to source removes it. proformaAssumptions follows every write.
  setOverride: (o) =>
    set((s) => {
      const parameterOverrides = {
        ...s.parameterOverrides,
        [o.scope]: [...(s.parameterOverrides[o.scope] ?? []).filter((x) => x.key !== o.key), o],
      };
      return { parameterOverrides, proformaAssumptions: assumptionsFromOverrides(parameterOverrides) };
    }),
  clearOverride: (scope, key) =>
    set((s) => {
      const parameterOverrides = {
        ...s.parameterOverrides,
        [scope]: (s.parameterOverrides[scope] ?? []).filter((x) => x.key !== key),
      };
      return { parameterOverrides, proformaAssumptions: assumptionsFromOverrides(parameterOverrides) };
    }),

  // ── pureOS's trains built here (OF-BLD-020 §5.3, D9) ───────────────────
  // Saved whole, by id, with when and by whom; the Builder sends the train
  // with every value its panels hold laid in (lib/pureos.trainSpecOf).
  saveTrain: (train, by) =>
    set((s) => ({ trainsMade: { ...s.trainsMade, [train.id]: { train: structuredClone(train), savedAt: new Date().toISOString(), by } } })),

  // ── Proforma's fermOS fits (OF-BLD-019 §5.1, D10) ─────────────────────
  // A person picks the fit; the browser keeps which artifact feeds which
  // input and nothing else: every value is the service's, from the artifact.
  setProformaFits: (scenarioId, fits) =>
    set((s) => ({ proformaFits: { ...s.proformaFits, [scenarioId]: { ...(s.proformaFits[scenarioId] ?? {}), ...fits } } })),
  clearProformaFit: (scenarioId, key) =>
    set((s) => {
      const kept = key ? Object.fromEntries(Object.entries(s.proformaFits[scenarioId] ?? {}).filter(([k]) => k !== key)) : {};
      return { proformaFits: { ...s.proformaFits, [scenarioId]: kept } };
    }),

  // ── misc ─────────────────────────────────────────────────────────────
  logActivity: (e) => set((s) => ({ activity: [e, ...s.activity].slice(0, 40) })),

  logExport: (name, rows) =>
    set((s) => ({ exports: [{ name, at: stamp(), rows }, ...s.exports].slice(0, 30) })),

  reconcileDeposition: (depositionId, outcome, note) => {
    const s = get();
    const d = s.depositions.find((x) => x.id === depositionId);
    if (!d) return;
    const runbook = s.runbooks.find((r) => r.id === d.runbookId);
    if (!runbook) return;
    const deltas = computeDeltas(d, runbook);
    const at = new Date().toISOString();

    // The run's deviations travel with the evidence. A number measured during
    // a run that went sideways is still a number, but it is not the same
    // number as one measured during a clean run, and stripping that context is
    // how a single result quietly becomes a global truth.
    const run = Object.values(s.runs).find((r) => r.depositionId === depositionId);
    const deviations = (run?.deviations ?? []).map((x) => x.text);

    const evidence: MeasuredEvidence[] = deltas.map((delta) => ({
      id: nextId('me'),
      depositionId,
      runbookId: runbook.id,
      productId: runbook.productId,
      predictionId: delta.predictionId,
      label: delta.label,
      value: delta.observed,
      unit: delta.unit,
      provenance: 'measured',
      conditions: {
        protocolId: d.protocolId,
        scale: run?.scale ?? 1,
        strainId: runbook.strainId,
      },
      deviations,
      confirmed: delta.confirmed,
      at,
    }));

    set((st) => ({
      depositions: st.depositions.map((x) =>
        x.id === depositionId
          ? {
              ...x,
              reconciliation: {
                at,
                outcome,
                deltas: deltas.map((delta) => ({
                  predictionId: delta.predictionId,
                  predicted: delta.predicted,
                  observed: delta.observed,
                  unit: delta.unit,
                  pctDelta: delta.pctDelta,
                })),
                note,
              },
            }
          : x,
      ),
      measuredEvidence: [...evidence, ...st.measuredEvidence],
    }));

    get().logActivity({
      at: stamp(),
      icon: 'check',
      text: `Reconciled — ${outcome}, ${evidence.length} measured value${evidence.length === 1 ? '' : 's'} released as evidence`,
      href: `#/runbooks/depositions/${depositionId}`,
      provenance: 'measured',
    });
    get().toast({
      text:
        outcome === 'refuted'
          ? 'Recorded as refuted. That is the useful one — it is ground truth about the model.'
          : outcome === 'inconclusive'
            ? 'Recorded as inconclusive. The hit rate stays honest because of entries like this.'
            : 'Recorded as confirmed.',
      kind: outcome === 'refuted' ? 'warn' : 'success',
    });
  },

  hydrateDurable: async () => {
    const snap = await loadDurable();
    if (!snap) {
      set({ durableReady: durableAvailable(), guildHydrated: true });
      if (get().serviceUp) void get().syncGuild();
      return;
    }
    get().applyDurable(snap);
  },

  // The apply half of hydrate, on a snapshot already read; check:store
  // round-trips a snapshot through it with no IndexedDB (§9.2).
  applyDurable: (snap) => {
    set((s) => {
      // Review decisions are re-applied over the seeded records rather than
      // replacing them, so a corpus update ships new records without
      // discarding what a reviewer already decided.
      const decisionAt = { ...s.decisionAt };
      const records = s.records.map((r) => {
        const d = snap.reviewDecisions[r.id];
        if (!d) return r;
        // §7.3 — the service may already have applied its decision for this
        // record; the later of the two wins. The decision's own `at` when the
        // snapshot carries one, the snapshot's savedAt for older snapshots.
        const madeAt = d.at ?? snap.savedAt;
        const server = s.overlay?.records[r.id];
        if (server && server.at > madeAt) return r;
        decisionAt[r.id] = madeAt;
        return applyDecision(r, d);
      });
      return {
        records,
        // The project rows still owed to the service, and the rows this
        // browser kept itself before alpha 2.0, carried to the open project
        // when its rows load (hydrateProjectState).
        stateOutbox: enqueue(snap.outbox ?? [], s.stateOutbox),
        stateLegacy: legacyStateOf(snap),
        durableReady: durableAvailable(),
        durableReview: { savedAt: snap.savedAt, decisions: snap.reviewDecisions },
        decisionAt,
        // Older snapshots predate the field; an unnamed reviewer is the
        // same as one who has not said yet (OF-BLD-012.1 F2).
        reviewer: snap.reviewerName ?? '',
        // OF-BLD-016 §2.1 — older snapshots predate the switch; the current
        // position (off unless changed since load) stands.
        // OF-BLD-013 §1.3 — what Guild's ledger still owes the service, laid
        // beside the ledger the page holds. Older snapshots predate the field.
        guild: owedLedger(s.guild, snap.guild?.ledger),
        guildPending: snap.guild?.pending ?? [],
        guildPendingWithdrawals: snap.guild?.withdrawals ?? [],
        guildActingId: snap.guild?.actingId ?? s.guildActingId,
        guildHydrated: true,
        // §3.2 — lessons finished in this browser. Anything finished since the
        // page loaded is kept beside what the snapshot remembers.
        learnProgress: { ...(snap.learnProgress ?? {}), ...s.learnProgress },
      };
    });
    if (get().serviceUp) void get().syncGuild();
    // Both sides are known once the overlay is in too; whichever hydrate
    // finishes second pushes the browser's later decisions to the service.
    if (get().serviceUp && get().overlay) void get().syncDecisions();
  },

  // ── service overlay (OF-BLD-012 §2.1) ─────────────────────────────────

  applyOverlay: (overlay) =>
    set((s) => {
      const merged: Overlay = {
        papers: { ...(s.overlay?.papers ?? {}), ...overlay.papers },
        records: { ...(s.overlay?.records ?? {}), ...overlay.records },
        // F3 — a list REPLACES, whatever its length. The service always
        // sends the full list, so an empty one means the extractor produced
        // nothing; only null means "not supplied". Before F3 the two were
        // indistinguishable and a cleared cache left stale candidates on
        // screen until a reload.
        candidates: overlay.candidates ?? s.overlay?.candidates ?? [],
        runs: overlay.runs ?? s.overlay?.runs ?? [],
      };
      const currentCandidates = merged.candidates ?? [];
      const currentRuns = merged.runs ?? [];
      // Papers, runs, decisions and new records. A decision here came through
      // `biorepo.write` on the service (§2.3); this is the only other place a
      // record's status moves, and only to what the service already stored.
      // The documents the project holds (ADR-002) are papers made from the
      // overlay, all of them every time: the service sends the project's
      // whole set, so a paper the last project held and this one does not
      // leaves with it.
      const notHeld = s.papers.filter((p) => !p.held);
      const held = Object.entries(overlay.papers)
        .filter(([id, o]) => o.title != null && !notHeld.some((p) => p.id === id))
        .map(([id, o]) => paperOf(id, o));
      const papers = [...notHeld.map((p) => {
        const o = overlay.papers[p.id];
        if (!o) return p;
        const fetched = o.textSource === 'full-text' && o.sections.length > 0;
        return {
          ...p,
          ingest: o.ingest,
          textSource: fetched ? 'full-text' : p.textSource,
          // A failed fetch keeps the curation note: the reader must show
          // SOMETHING, and the curator's words labelled as such beat nothing.
          sections: fetched ? o.sections : p.sections,
          license: fetched ? (o.license ?? undefined) : p.license,
          fetchedFrom: fetched ? (o.source ?? 'europepmc') : p.fetchedFrom,
          ingestReason: o.reason ?? undefined,
        } as Paper;
      }), ...held];
      // §6.4 — Witness reads runs from the store: the overlay's when present,
      // the seed's RUN_OUTPUTS otherwise. An overlay run replaces a seed run
      // of the same id; the seed keeps any run the overlay does not carry.
      const runOutputs = currentRuns.length
        ? [...s.runOutputs.filter((r) => !currentRuns.some((o) => o.run === r.run)), ...currentRuns]
        : s.runOutputs;

      // §7.3 — the service's decisions, over seed records and candidates
      // alike. The later of the two wins, judged against the time of the
      // decision currently on the record — the live one, not the snapshot
      // this session loaded with, so a decision made a minute ago is not
      // overwritten by an older server one a fetch or an extraction brings
      // back. A server decision applied here takes its own `at`, so the
      // Durable tier persists it as the server's and never re-posts it.
      const decisionAt = { ...s.decisionAt };
      const decide = (r: ExtractionRecord): ExtractionRecord => {
        const d = merged.records[r.id];
        if (!d) return r;
        const mine = decisionAt[r.id];
        if (mine && mine > d.at) return r;
        decisionAt[r.id] = d.at;
        return applyDecision(r, d);
      };
      // §7.3 — candidates for a field the seed has no record of join the
      // records, after the seed, as unverified records extracted by claude-1.
      // A candidate that matches a seed record's field stays in the overlay,
      // beside that record on its review card. Idempotent: a candidate
      // already here is not added twice, and a Durable decision on one that
      // just arrived is applied to it.
      const local = s.durableReview;
      const seed = s.records.filter((r) => r.extractorRun !== 'claude-1');
      const present = new Set(s.records.map((r) => r.id));
      const arrivingIds: string[] = [];
      const arriving: ExtractionRecord[] = currentCandidates
        .filter((c) => !present.has(c.id) && isNewCandidate(c, seed))
        .map((c) => {
          arrivingIds.push(c.id);
          const record: ExtractionRecord = stampOriginal({ ...c, audit: [] });
          const mine = local?.decisions[c.id];
          if (!mine) return record;
          decisionAt[c.id] = mine.at ?? local!.savedAt;
          return applyDecision(record, mine);
        });
      // F3 — what happens to the records earlier candidates became. A
      // candidate nobody decided on is the extractor's current opinion, and
      // goes when the opinion does. One a reviewer decided is a DECISION, and
      // a decision does not evaporate because a re-extraction stopped
      // producing the sentence: it stays, marked, so the card can say so.
      // Only meaningful when a list actually arrived.
      const stillExtracted = new Set(currentCandidates.map((c) => c.id));
      const wasDecided = (id: string) =>
        !!decisionAt[id] || !!merged.records[id] || !!local?.decisions[id];
      const surviving =
        overlay.candidates === null || overlay.candidates === undefined
          ? s.records
          : s.records.filter((r) => r.extractorRun !== 'claude-1' || stillExtracted.has(r.id) || wasDecided(r.id));
      const records = [...surviving, ...arriving]
        .map(decide)
        .map((r) =>
          r.extractorRun !== 'claude-1' || overlay.candidates == null
            ? r
            : { ...r, absentFromRun: stillExtracted.has(r.id) ? undefined : true },
        );
      // New records still undecided join an open review queue after
      // everything already in it (§7.3). A queue seeded before the overlay
      // arrived would otherwise never see them.
      const queued = new Set(s.reviewQueue);
      const arrived = new Set(arrivingIds);
      const joining = records
        .filter((r) => arrived.has(r.id) && r.status === 'unverified' && !r.gold && !queued.has(r.id))
        .map((r) => r.id);
      // A record that is gone is gone from the queue too; a reviewer should
      // not be shown a card for a sentence the extractor no longer reads.
      const alive = new Set(records.map((r) => r.id));
      const kept = s.reviewQueue.filter((id) => alive.has(id));
      const reviewQueue = kept.length && joining.length ? [...kept, ...joining] : kept;
      // The index follows the RECORD, not the position: a reviewer on card
      // four of six whose first three cards just went is on card one of
      // three, and one whose own card went lands on the next survivor —
      // never on a different card at the same number, never past the end.
      const under = s.reviewQueue[s.reviewIndex];
      const reviewIndex =
        under !== undefined && alive.has(under)
          ? reviewQueue.indexOf(under)
          : Math.min(s.reviewQueue.slice(0, s.reviewIndex).filter((id) => alive.has(id)).length, reviewQueue.length);
      return { overlay: merged, papers, runOutputs, records, reviewQueue, reviewIndex, decisionAt };
    }),

  hydrateOverlay: async () => {
    const overlay = await loadOverlay();
    if (!overlay) {
      set({ serviceUp: false });
      return;
    }
    set({ serviceUp: true });
    get().applyOverlay(overlay);
    if (get().durableReview) void get().syncDecisions();
    if (get().guildHydrated) void get().syncGuild();
  },

  focusReview: (recordId) => {
    const s = get();
    const at = s.reviewQueue.indexOf(recordId);
    if (at >= 0) {
      set({ reviewIndex: at });
      return;
    }
    if (!s.records.some((r) => r.id === recordId)) return;
    // Not in the current queue — already decided, or no queue yet. Put it in
    // front and the rest of the unverified records behind it.
    const rest = s.records
      .filter((r) => r.status === 'unverified' && r.id !== recordId)
      .map((r) => r.id);
    get().startReview([recordId, ...rest]);
  },

  syncDecisions: async () => {
    // The Durable tier is the offline cache (§7.3): a decision made with the
    // service down reaches it here, the next time both are known. Later
    // wins in both directions — a server decision newer than the browser's
    // was already applied over it, and is left alone.
    const s = get();
    const local = s.durableReview;
    if (!local || !s.overlay || !s.serviceUp) return;
    const pending: ReviewDecision[] = [];
    let kept = 0;
    for (const [id, mine] of Object.entries(local.decisions)) {
      const madeAt = s.decisionAt[id] ?? mine.at ?? local.savedAt;
      const server = s.overlay.records[id];
      if (server && server.at >= madeAt) continue; // the service has this one, or a newer one
      if (s.refusedDecisions[id]) continue; // refused this session; the record has not changed since
      const record = s.records.find((r) => r.id === id);
      if (!record) continue; // a candidate not in this overlay; nothing to post it about
      // What the service would refuse is not posted, and not posted again on
      // every load: an accept on an unfetched paper stays this browser's.
      const paper = s.papers.find((p) => p.id === record.paperId);
      if (writeRefusal(actionOf(record), record, paper, s.overlay.candidates ?? [], true, reviewerName())) {
        kept++;
        continue;
      }
      pending.push(decisionOf(record, reanchoredSpan(record), madeAt));
    }
    for (const d of pending) await get().postReviewDecision(d);
    if (pending.length || kept) {
      get().logActivity({
        at: stamp(),
        icon: 'upload',
        text:
          `${pending.length} review decision${pending.length === 1 ? '' : 's'} made offline sent to the service` +
          (kept ? `; ${kept} kept in this browser only (the service would refuse them — unfetched or unidentified papers)` : ''),
        href: '#/guild',
        provenance: 'user',
      });
    }
  },

  postReviewDecision: async (decision) => {
    try {
      const stored = await postDecision(decision);
      set((s) => {
        const { [stored.recordId]: _refused, ...refusedDecisions } = s.refusedDecisions;
        return {
          overlay: s.overlay
            ? { ...s.overlay, records: { ...s.overlay.records, [stored.recordId]: stored } }
            : s.overlay,
          refusedDecisions,
        };
      });
    } catch (e) {
      if (e instanceof DecisionRefused) {
        // The service said no and said why. The browser's decision stands in
        // the Durable tier; the reviewer hears the rule, and nothing is
        // repaired on either side. Remembered, so it is not posted again
        // until the record changes.
        set((s) => ({ refusedDecisions: { ...s.refusedDecisions, [decision.recordId]: e.rule } }));
        get().toast({ text: `${decision.recordId} — the service refused this decision (${e.rule}): ${e.why}`, kind: 'error' });
        get().logActivity({
          at: stamp(),
          icon: 'flag',
          text: `biorepo.write refused ${decision.recordId} on rule ‘${e.rule}’ — ${e.why}`,
          href: '#/guild',
          provenance: 'user',
        });
        return;
      }
      if (e instanceof IntakeDown) {
        set({ serviceUp: false });
        get().toast({ text: `${e.message} The decision on ${decision.recordId} is kept in this browser only.`, kind: 'error' });
        return;
      }
      throw e;
    }
  },

  // ── Guild (OF-BLD-013 §1.3) ─────────────────────────────────────────
  //
  // Every write is applied here first, then posted. The service stores it or
  // refuses it with a rule: a refusal takes the write back out and says why;
  // no service keeps it, marked pending, for `syncGuild` to post later.

  guildAddPerson: async (input) => {
    const s = get();
    const ledger = s.guild;
    const person: GuildPerson = {
      id: personIdFor(input.name, ledger.people.map((p) => p.id)),
      name: input.name.trim(),
      title: input.title.trim(),
      role: input.role,
      joinedAt: input.joinedAt,
      active: true,
      addedBy: ledger.people.length === 0 ? null : actingIdOf(s),
      addedAt: new Date().toISOString(),
    };
    set({ guild: { ...s.guild, people: [...s.guild.people, person] } });
    if (ledger.people.length === 0 && !s.guildActingId) set({ guildActingId: person.id });
    return guildPost(set, get, person.id, () => postPerson(person), (stored) => ({
      guild: { ...get().guild, people: get().guild.people.map((p) => (p.id === person.id ? stored : p)) },
    }), () => ({ guild: { ...get().guild, people: get().guild.people.filter((p) => p.id !== person.id) } }), person);
  },

  guildUpdatePerson: async (person) => {
    const s = get();
    const changed: GuildPerson = { ...person, updatedBy: actingIdOf(s), updatedAt: new Date().toISOString() };
    const before = s.guild.people.find((p) => p.id === person.id);
    set({ guild: { ...s.guild, people: s.guild.people.map((p) => (p.id === person.id ? changed : p)) } });
    return guildPost(set, get, person.id, () => postPerson(changed), (stored) => ({
      guild: { ...get().guild, people: get().guild.people.map((p) => (p.id === person.id ? stored : p)) },
    }), () => ({
      guild: { ...get().guild, people: get().guild.people.map((p) => (p.id === person.id && before ? before : p)) },
    }), changed);
  },

  guildRecord: async (input) => {
    const s = get();
    const entry: GuildEvidence = { ...input, id: newEvidenceId(), recordedAt: null };
    set({ guild: { ...s.guild, evidence: [...s.guild.evidence, entry] } });
    return guildPost(set, get, entry.id, () => postEvidence(entry), (stored) => ({
      guild: { ...get().guild, evidence: get().guild.evidence.map((e) => (e.id === entry.id ? stored : e)) },
    }), () => ({ guild: { ...get().guild, evidence: get().guild.evidence.filter((e) => e.id !== entry.id) } }), entry);
  },

  guildWithdraw: async (evidenceId, reason) => {
    const s = get();
    const by = actingIdOf(s);
    if (!by) {
      get().toast({ text: 'Choose who you are with Acting as before withdrawing an entry.', kind: 'error' });
      return false;
    }
    const w: GuildWithdrawal = { evidenceId, by, at: localToday(), reason: reason.trim() };
    const mark = (e: GuildEvidence): GuildEvidence =>
      e.id === evidenceId ? { ...e, withdrawnAt: w.at, withdrawnBy: by, withdrawReason: w.reason } : e;
    const before = s.guild.evidence.find((e) => e.id === evidenceId);
    set({ guild: { ...s.guild, evidence: s.guild.evidence.map(mark) } });
    const unmark = () => ({
      guild: { ...get().guild, evidence: get().guild.evidence.map((e) => (e.id === evidenceId && before ? before : e)) },
    });
    // An entry the service does not hold yet is withdrawn after it is sent.
    if (!s.serviceUp || s.guildPending.includes(evidenceId)) {
      set((x) => ({ guildPendingWithdrawals: [...x.guildPendingWithdrawals, w] }));
      return true;
    }
    try {
      const stored = await postWithdrawal(w);
      set((x) => ({ guild: { ...x.guild, evidence: x.guild.evidence.map((e) => (e.id === evidenceId ? stored : e)) } }));
      return true;
    } catch (e) {
      if (e instanceof GuildRefused) {
        set(unmark());
        get().toast({ text: `The service kept that entry (${e.rule}): ${e.why}`, kind: 'error' });
        return false;
      }
      if (e instanceof IntakeDown) {
        set((x) => ({ serviceUp: false, guildPendingWithdrawals: [...x.guildPendingWithdrawals, w] }));
        get().toast({ text: 'The service stopped answering. The withdrawal is kept in this browser and sent when it is back.', kind: 'warn' });
        return true;
      }
      throw e;
    }
  },

  guildSetActing: (id) => set({ guildActingId: id }),

  guildSetPolicy: async (choice) => {
    const s = get();
    const by = actingIdOf(s);
    const ledger = guildView(s);
    const lead = ledger.people.find((p) => p.id === by && p.active && p.role === 'lead');
    if (!lead) {
      get().toast({ text: 'Only the lead changes the gate and the check rate. Choose who you are with Acting as.', kind: 'error' });
      return false;
    }
    const policy: GuildPolicy = { ...choice, updatedBy: lead.id, updatedAt: new Date().toISOString() };
    if (!s.serviceUp) {
      get().toast({ text: 'The gate and the check rate are kept by the service, which is not answering here.', kind: 'error' });
      return false;
    }
    try {
      const stored = await postPolicy(policy);
      set((x) => ({ guild: { ...x.guild, policy: stored } }));
      return true;
    } catch (e) {
      get().toast({ text: e instanceof GuildRefused ? `The service kept the old policy (${e.rule}): ${e.why}` : String(e), kind: 'error' });
      return false;
    }
  },

  // ── Checks (OF-BLD-013 §5.4) ─────────────────────────────────────────
  //
  // The service's rules decide every write.

  loadChecks: async () => {
    set({ checks: await loadChecksFromService() });
  },

  // `made` counts only the checks the proposer may see: one that names them
  // stays out of the count as it stays out of the queue.
  checksPropose: async () => {
    const s = get();
    const by = actingIdOf(s);
    if (!by) return { why: 'Choose who you are with Acting as: the ranking is run by an assessor or the lead.' };
    try {
      const made = await postPropose(by);
      await get().loadChecks();
      return { made: made.filter((c) => c.personId !== by).length };
    } catch (e) {
      return { why: whyNot(e) };
    }
  },

  checksRequest: async (personId, skillIds) => {
    const s = get();
    const by = actingIdOf(s);
    if (!by) return 'Choose who you are first.';
    // Asking for your own check says the same whether or not one is already
    // open: a duplicate is the queue's to know, and the person never sees a
    // check that names them before it is run.
    const own = by === personId;
    try {
      await postRequest({ personId, skillIds, by });
      await get().loadChecks();
      return null;
    } catch (e) {
      if (own && e instanceof CheckRefused && e.rule === 'duplicate') return null;
      return whyNot(e);
    }
  },

  checksSchedule: async (checkId, day) => checkMove(get, (by) => postSchedule(checkId, { by, scheduledFor: day })),

  checksDismiss: async (checkId, reason) => checkMove(get, (by) => postDismiss(checkId, { by, reason })),

  checksBrief: async (checkId) => {
    const s = get();
    const by = actingIdOf(s);
    if (!by) return 'Choose who you are first.';
    try {
      await postBrief(checkId, by);
      await get().loadChecks();
      return null;
    } catch (e) {
      return whyNot(e);
    }
  },

  checksRecord: async (checkId, results, notes, at) => {
    const s = get();
    const by = actingIdOf(s);
    if (!by) return 'Choose who you are first: a check is signed by the assessor who ran it.';
    try {
      await postRecord(checkId, { by, at, results, notes });
      await get().loadChecks();
      await get().syncGuild();
      return null;
    } catch (e) {
      return whyNot(e);
    }
  },

  // ── Practice (OF-BLD-013 §4.3) ──────────────────────────────────────

  loadPractice: async () => {
    const practice = await loadPracticeFromService();
    set({ practice });
    return practice;
  },

  mergePractice: ({ scenario, session }) =>
    set((s) => {
      const p: Practice = s.practice ?? { version: 1, scenarios: [], sessions: [] };
      return {
        practice: {
          ...p,
          scenarios: scenario ? [...p.scenarios.filter((x) => x.id !== scenario.id), scenario] : p.scenarios,
          sessions: session ? [...p.sessions.filter((x) => x.id !== session.id), session] : p.sessions,
        },
      };
    }),

  practiceClosed: async (session) => {
    if (!session.closedAt) return;
    // A session the service named somebody on is theirs, whatever is shown
    // now: the service has put it on their ledger, so fetch the ledger back.
    if (session.personId && session.evidenceId) await get().syncGuild();
  },

  setRunOperator: (runId, personId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, operatorId: personId } },
        // The deposition names whoever is performing now; each step's entry
        // on the ledger names who performed that step.
        depositions:
          run.depositionId
            ? s.depositions.map((d) => (d.id === run.depositionId ? { ...d, operatorId: personId } : d))
            : s.depositions,
      };
    }),

  setRunCosigner: (runId, stepId, personId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      const cosigned = { ...(run.cosigned ?? {}) };
      if (personId) cosigned[stepId] = personId;
      else delete cosigned[stepId];
      return { runs: { ...s.runs, [runId]: { ...run, cosigned } } };
    }),

  recordStepForGuild: async (runId, stepId) => {
    const s = get();
    const run = s.runs[runId];
    if (!run || run.guildRecorded?.[stepId]) return 0;
    const operatorId = run.operatorId ?? null;
    const ledger = guildView(s);
    const canHold = (id: string | null): id is string => !!id && ledger.people.some((p) => p.id === id && p.active && p.role !== 'auditor');
    // The gate shows "Nobody chosen" for anyone else, and nothing is written for them.
    if (!canHold(operatorId)) return 0;
    const protocol = s.protocols.find((p) => p.id === run.protocolId);
    const step = protocol?.versions.find((v) => v.version === run.version)?.steps.find((x) => x.id === stepId);
    const tags = step?.skills ?? [];
    if (!protocol || tags.length === 0) return 0;
    set((x) => ({
      runs: { ...x.runs, [runId]: { ...x.runs[runId], guildRecorded: { ...(x.runs[runId].guildRecorded ?? {}), [stepId]: true } } },
    }));
    const today = localToday();
    const map = competenceOf(ledger.evidence, ledger.people, skillById(s.skills), today);
    const chosen = run.cosigned?.[stepId] ?? null;
    const cosigner = canHold(chosen) ? chosen : null;
    const where = `${run.depositionId ? `Deposition ${run.depositionId}` : `Run ${runId}`}, step ${stepId}`;
    let deviations = 0;
    for (const skillId of tags) {
      const e = statusOf(map, operatorId, skillId).effective;
      const base = {
        personId: operatorId,
        skillId,
        outcome: 'pass' as const,
        at: today,
        source: { kind: 'deposition' as const, ref: protocol.id, stepId },
      };
      // A run the service will not take as a run alone or a cosigned run (its
      // ledger knew something this browser did not) still happened: it is
      // kept as a deviation, so the step leaves its mark either way.
      const orDeviation = async (stored: GuildEvidence | null, as: string) => {
        if (stored) return;
        deviations += 1;
        await get().guildRecord({
          ...base,
          kind: 'deviation',
          observerId: null,
          raw: `${where}: performed, and the service refused it as ${as}, so it stands as a deviation`,
        });
      };
      if (e >= 3) {
        await orDeviation(
          await get().guildRecord({ ...base, kind: 'independent', observerId: null, raw: `${where}: performed alone` }),
          'a run alone',
        );
      } else if (e === 2 && cosigner && mayCosign(map, cosigner, [skillId])) {
        await orDeviation(
          await get().guildRecord({ ...base, kind: 'supervised', observerId: cosigner, raw: `${where}: performed with a cosigner beside them` }),
          'a cosigned run',
        );
      } else {
        deviations += 1;
        await get().guildRecord({
          ...base,
          kind: 'deviation',
          observerId: null,
          raw:
            e === 2
              ? `${where}: performed without the cosigner it needs`
              : `${where}: performed below Supervised, which needs a qualified operator`,
        });
      }
    }
    return deviations;
  },

  recordHeldSkipForGuild: async (runId, stepId, reason, hold) => {
    const s = get();
    const run = s.runs[runId];
    if (!run || run.guildRecorded?.[stepId]) return 0;
    const operatorId = run.operatorId ?? null;
    const ledger = guildView(s);
    if (!operatorId || !ledger.people.some((p) => p.id === operatorId && p.active && p.role !== 'auditor')) return 0;
    const protocol = s.protocols.find((p) => p.id === run.protocolId);
    const tags = protocol?.versions.find((v) => v.version === run.version)?.steps.find((x) => x.id === stepId)?.skills ?? [];
    if (!protocol || tags.length === 0) return 0;
    set((x) => ({
      runs: { ...x.runs, [runId]: { ...x.runs[runId], guildRecorded: { ...(x.runs[runId].guildRecorded ?? {}), [stepId]: true } } },
    }));
    const where = `${run.depositionId ? `Deposition ${run.depositionId}` : `Run ${runId}`}, step ${stepId}`;
    for (const skillId of tags)
      await get().guildRecord({
        personId: operatorId,
        skillId,
        kind: 'deviation',
        outcome: 'pass',
        at: localToday(),
        observerId: null,
        source: { kind: 'deposition', ref: protocol.id, stepId },
        raw: `${where}: skipped while held (${hold}); the reason given was \u201c${reason}\u201d`,
      });
    return tags.length;
  },

  recordLessonForGuild: async (lessonId) => {
    const s = get();
    const lesson = s.modules.flatMap((m) => m.lessons).find((l) => l.id === lessonId);
    const counts = lesson?.skills ?? [];
    const personId = runOperatorDefault(s);
    if (!lesson || counts.length === 0 || !personId) return null;
    const ledger = guildView(s);
    const missing = counts.filter(
      (skillId) =>
        !ledger.evidence.some(
          (e) =>
            e.personId === personId &&
            e.skillId === skillId &&
            e.kind === 'knowledge' &&
            e.source.kind === 'lesson' &&
            e.source.ref === lessonId &&
            !e.withdrawnAt,
        ),
    );
    // Every entry is applied before the first post is awaited, so a second
    // call made meanwhile finds them and writes nothing.
    const writes = missing.map((skillId) =>
      get().guildRecord({
        personId,
        skillId,
        kind: 'knowledge',
        outcome: 'pass',
        at: localToday(),
        observerId: null,
        source: { kind: 'lesson', ref: lessonId },
        raw: `Primer lesson ${lessonId}, \u201c${lesson.title}\u201d: every checkpoint question answered correctly`,
      }),
    );
    await Promise.all(writes);
    return { personId, skills: missing };
  },

  syncGuild: async () => {
    if (guildSyncing) return;
    guildSyncing = true;
    try {
      if (!get().serviceUp) return;
      const server = await loadGuild();
      if (!server) return;
      const s = get();
      const pending = new Set(s.guildPending);
      // Already on the service: stored, with the answer lost on the way back.
      const stored = new Set([...server.people.map((p) => p.id), ...server.evidence.map((e) => e.id)]);
      const refused: string[] = [];
      let posted = 0;
      const attempt = async (
        label: string,
        post: () => Promise<unknown>,
        onRefused?: (e: GuildRefused) => Promise<void>,
      ): Promise<boolean> => {
        try {
          await post();
          posted += 1;
          return true;
        } catch (e) {
          if (e instanceof GuildRefused) {
            refused.push(`${label} (${e.rule}: ${e.why})`);
            if (onRefused) await onRefused(e);
            return true;
          }
          if (e instanceof IntakeDown) {
            set({ serviceUp: false });
            return false;
          }
          throw e;
        }
      };
      // A run made offline that the service will not take as a run alone or a
      // cosigned run still happened, and is sent again as a deviation.
      const asDeviation = (e: GuildEvidence) => async (r: GuildRefused) => {
        if (e.source.kind !== 'deposition' || (e.kind !== 'independent' && e.kind !== 'supervised')) return;
        if (r.rule !== 'authority' && r.rule !== 'observer') return;
        const deviation: GuildEvidence = {
          ...e,
          id: newEvidenceId(),
          kind: 'deviation',
          observerId: null,
          raw: `${e.raw}; refused as ${e.kind === 'independent' ? 'a run alone' : 'a cosigned run'} (${r.why}), so it stands as a deviation`,
          recordedAt: null,
        };
        await attempt(`deviation on ${e.skillId}`, () => postEvidence(deviation));
      };
      // People first, then entries, then withdrawals: each may name the one before.
      for (const p of s.guild.people)
        if (pending.has(p.id) && !stored.has(p.id) && !(await attempt(p.name, () => postPerson(p)))) return;
      for (const e of s.guild.evidence)
        if (pending.has(e.id) && !stored.has(e.id) && !(await attempt(`${e.kind} on ${e.skillId}`, () => postEvidence(e), asDeviation(e))))
          return;
      for (const w of s.guildPendingWithdrawals)
        if (!(await attempt(`withdrawal of ${w.evidenceId}`, () => postWithdrawal(w)))) return;
      const fresh = (await loadGuild()) ?? server;
      // The service's ledger is the truth for everything this sync sent.
      // Anything made while it ran, and anything it did not send, stays.
      const sent = new Set(s.guildPending);
      const before = new Set([...s.guild.people.map((p) => p.id), ...s.guild.evidence.map((e) => e.id)]);
      set((x) => {
        const inFresh = new Set([...fresh.people.map((p) => p.id), ...fresh.evidence.map((e) => e.id)]);
        const still = x.guildPending.filter((id) => !sent.has(id));
        const keep = (id: string) => !inFresh.has(id) && (still.includes(id) || !before.has(id));
        return {
          guild: {
            ...fresh,
            people: [...fresh.people, ...x.guild.people.filter((p) => keep(p.id))],
            evidence: [...fresh.evidence, ...x.guild.evidence.filter((e) => keep(e.id))],
          },
          guildPending: still,
          guildPendingWithdrawals: x.guildPendingWithdrawals.filter((w) => !s.guildPendingWithdrawals.includes(w)),
        };
      });
      // The queue reads the ledger it was ranked from, so it is fetched with it.
      await get().loadChecks();
      if (posted || refused.length)
        get().logActivity({
          at: stamp(),
          icon: 'upload',
          text:
            `${posted} Guild change${posted === 1 ? '' : 's'} made offline sent to the service` +
            (refused.length ? `; refused and dropped: ${refused.join('; ')}` : ''),
          href: '#/guild/people',
          provenance: 'user',
        });
      if (refused.length)
        get().toast({ text: `The service refused ${refused.length} Guild change${refused.length === 1 ? '' : 's'} made offline: ${refused[0]}`, kind: 'error' });
    } finally {
      guildSyncing = false;
    }
  },

  clearBrowserData: () => {
    // Clear persistence as well as memory. A reset that leaves a durable
    // snapshot behind would restore itself on the next reload, which is the
    // opposite of what the button says.
    void clearDurable();
    // The overlay is the service's state, not the session's: it survives a
    // reset the way it survives a reload.
    const overlay = get().overlay;
    const serviceUp = get().serviceUp;
    // The open project's rows are the service's, and survive a reset the way
    // the overlay does: they are loaded again, and nothing is taken back on
    // the service. What this browser still owed it goes with the browser's data.
    set({
      ...seedState(),
      toasts: [],
      serviceUp,
      durableReview: null,
      decisionAt: {},
      refusedDecisions: {},
      stateSeen: null,
      stateOutbox: [],
      stateLegacy: null,
    });
    void get().hydrateProjectState();
    if (overlay) get().applyOverlay(overlay);
    // Guild's ledger is the service's when there is one, and survives a reset
    // the way the overlay does; what was only ever in this browser goes.
    set({
      guild: serviceUp ? get().guild : EMPTY_GUILD,
      guildPending: [],
      guildPendingWithdrawals: [],
      guildActingId: serviceUp ? get().guildActingId : null,
    });
    if (serviceUp) void get().syncGuild();
    get().toast({
      text: 'This browser’s data is cleared: the lessons finished here and every change it had not yet sent to the service are gone; the project’s rows load again from the service',
      kind: 'info',
    });
  },
}));

// ── Guild helpers (OF-BLD-013 §1.3) ────────────────────────────────────

/** The ledger every Guild screen reads. */
export function guildView(s: Pick<OFState, 'guild'>): Guild {
  return s.guild;
}

/** The checks every Guild screen reads, as the service last answered. */
export function checksView(s: Pick<OFState, 'checks'>): Check[] {
  return s.checks?.checks ?? [];
}

/** One move on one open check: `post` asks the service and the queue is fetched again. */
async function checkMove(get: () => OFState, post: (by: string) => Promise<unknown>): Promise<string | null> {
  const by = actingIdOf(get());
  if (!by) return 'Choose who you are first.';
  try {
    await post(by);
    await get().loadChecks();
    return null;
  } catch (e) {
    return whyNot(e);
  }
}

/** Who is signing, as chosen in Guild's header. */
export function actingIdOf(s: Pick<OFState, 'guildActingId'>): string | null {
  return s.guildActingId;
}

let guildSyncing = false;

/** Whoever is signing in Guild, when they are on the ledger and can hold skills. */
function runOperatorDefault(s: OFState): string | null {
  const id = actingIdOf(s);
  const p = id ? guildView(s).people.find((x) => x.id === id) : undefined;
  return p && p.active && p.role !== 'auditor' ? p.id : null;
}

type StoreSet = (partial: Partial<OFState> | ((s: OFState) => Partial<OFState>)) => void;

/**
 * Post one write that is already applied locally. Stored: replace it with what
 * the service kept. Refused: take it back out and say which rule. No service:
 * keep it, pending, for `syncGuild`.
 */
async function guildPost<T>(
  set: StoreSet,
  get: () => OFState,
  id: string,
  post: () => Promise<T>,
  onStored: (stored: T) => Partial<OFState>,
  onRefused: () => Partial<OFState>,
  local: T,
): Promise<T | null> {
  const pend = () => set((x) => ({ guildPending: x.guildPending.includes(id) ? x.guildPending : [...x.guildPending, id] }));
  if (!get().serviceUp) {
    pend();
    return local;
  }
  try {
    const stored = await post();
    set(onStored(stored));
    return stored;
  } catch (e) {
    if (e instanceof GuildRefused) {
      set(onRefused());
      get().toast({ text: `The service refused this (${e.rule}): ${e.why}`, kind: 'error' });
      return null;
    }
    if (e instanceof IntakeDown) {
      set({ serviceUp: false });
      pend();
      get().toast({ text: 'The service stopped answering. This is kept in this browser and sent when it is back.', kind: 'warn' });
      return local;
    }
    throw e;
  }
}

// ── durable persistence (OF-BLD-006 §4.6) ──────────────────────────────
//
// Only the Durable tier is written. Reference data is never mutated so there
// is nothing to save, and Ephemeral UI state is deliberately excluded — a
// collapsed panel that followed you across sessions would be a bug, not a
// feature.

// ── the parameter panel's overrides (OF-BLD-020 §2.1, D3) ────────────────
//
// An override is a person's change to one parameter of one scope, kept in
// this browser and sent with the run; the service keeps none. Proforma's
// older `proformaAssumptions` is the same thing for one kind of scope: a
// scenario's assumptions are the overrides of `proforma:<scenario id>`, and
// the old field is derived from them. Since OF-BLD-020 §2.2 the scenario page
// is the panel and nothing on a screen reads the old field.

const PROFORMA_SCOPE = 'proforma:';
const NO_OVERRIDES: Override[] = [];

/** The scope a Proforma scenario's parameters live under. */
export function proformaScope(scenarioId: string): string {
  return `${PROFORMA_SCOPE}${scenarioId}`;
}

/** One scope's overrides, for `useStore(overridesFor(scope))`: the same empty list every time when there are none. */
export function overridesFor(scope: string): (s: Pick<OFState, 'parameterOverrides'>) => Override[] {
  return (s) => s.parameterOverrides[scope] ?? NO_OVERRIDES;
}

/**
 * A Proforma assumption as the override of its scenario's scope. The old
 * form (OF-BLD-019's Keep assumption) asked for a value, a low and a high
 * every time, so a fixed value was typed with both ends at itself; such ends
 * say nothing the value does not, and are read as none (OF-BLD-020 §2.R,
 * finding 10: kept, they held every later value to the old one, and the
 * service refused it as outside its own low and high).
 */
export function overrideOfAssumption(scenarioId: string, a: InputAssumption): Override {
  const fixed = a.low === a.value && a.high === a.value;
  return {
    scope: proformaScope(scenarioId),
    key: a.key,
    value: a.value,
    low: fixed ? null : a.low,
    high: fixed ? null : a.high,
    by: a.by,
    at: a.at,
    note: a.note ?? null,
  };
}

/**
 * An override's interval as every reader takes it (OF-BLD-020 §2.R,
 * findings 1 and 14; the service's `params.held`): one end typed and the
 * other left empty, the empty end is the value itself; with neither, the
 * value is held at itself and both stay empty. The panel's row, the
 * scenario page's binding and `assumptionOfOverride` read it so, as the
 * service's resolve and run do.
 */
export function overrideEnds(o: Pick<Override, 'value' | 'low' | 'high'>): { low: number | null; high: number | null } {
  if (typeof o.value !== 'number' || (o.low == null && o.high == null)) return { low: o.low ?? null, high: o.high ?? null };
  return { low: o.low ?? o.value, high: o.high ?? o.value };
}

/** An override as a Proforma assumption; null for a value in words, which no Proforma input takes. */
export function assumptionOfOverride(o: Override): InputAssumption | null {
  if (typeof o.value !== 'number' || !Number.isFinite(o.value)) return null;
  const ends = overrideEnds(o);
  return { key: o.key, value: o.value, low: ends.low ?? o.value, high: ends.high ?? o.value, by: o.by, at: o.at, note: o.note ?? null };
}

/** `proformaAssumptions` as the overrides of every `proforma:` scope give it, by scenario id. */
export function assumptionsFromOverrides(overrides: Record<string, Override[]>): Record<string, InputAssumption[]> {
  const out: Record<string, InputAssumption[]> = {};
  for (const [scope, list] of Object.entries(overrides)) {
    if (!scope.startsWith(PROFORMA_SCOPE)) continue;
    out[scope.slice(PROFORMA_SCOPE.length)] = list.map(assumptionOfOverride).filter((a): a is InputAssumption => a !== null);
  }
  return out;
}

/**
 * A snapshot's overrides, with its `proformaAssumptions` read once into
 * `proforma:<id>` for every scenario whose scope the snapshot holds no entry
 * for (D3: a snapshot written before the panel carries only the old field).
 */
export function overridesOfSnapshot(snap: Pick<DurableSnapshot, 'parameterOverrides' | 'proformaAssumptions'>): Record<string, Override[]> {
  const out: Record<string, Override[]> = { ...(snap.parameterOverrides ?? {}) };
  for (const [id, typed] of Object.entries(snap.proformaAssumptions ?? {})) {
    const scope = proformaScope(id);
    if (!(scope in out)) out[scope] = typed.map((a) => overrideOfAssumption(id, a));
  }
  return out;
}

export function snapshotOf(s: OFState): DurableSnapshot {
  const reviewDecisions: DurableSnapshot['reviewDecisions'] = {};
  for (const r of s.records) {
    // Only records a reviewer has actually touched.
    if (r.status === 'unverified' && !r.gold && !r.corrected && !r.reviewer) continue;
    // And only decisions the service does not hold yet: one it holds at this
    // time or later is its own, and loads with the overlay.
    const server = s.overlay?.records[r.id];
    if (server && s.decisionAt[r.id] && server.at >= s.decisionAt[r.id]) continue;
    reviewDecisions[r.id] = {
      status: r.status,
      provenance: r.provenance,
      gold: r.gold,
      corrected: r.corrected,
      rejectReason: r.rejectReason,
      reviewer: r.reviewer,
      at: s.decisionAt[r.id],
      // The sentence a promotion re-anchored to, when it did (§7.3).
      ...(reanchoredSpan(r) ?? {}),
    };
  }
  const owed = new Set(s.guildPending);
  const legacy = s.stateLegacy;
  return {
    ...EMPTY_SNAPSHOT,
    savedAt: new Date().toISOString(),
    reviewDecisions,
    reviewerName: s.reviewer,
    guild: {
      // Only what the service has not acknowledged; the ledger loads from it.
      ledger: { ...s.guild, people: s.guild.people.filter((x) => owed.has(x.id)), evidence: s.guild.evidence.filter((x) => owed.has(x.id)) },
      pending: s.guildPending,
      withdrawals: s.guildPendingWithdrawals,
      actingId: s.guildActingId,
    },
    learnProgress: Object.fromEntries(Object.keys(s.learnProgress).filter((k) => s.learnProgress[k]).map((k) => [k, true as const])),
    outbox: s.stateOutbox,
    // Rows kept here before alpha 2.0 stay until a project is open to take them.
    ...(legacy
      ? {
          depositions: legacy.depositions,
          measuredEvidence: legacy.measuredEvidence,
          runbookLocks: legacy.runbookLocks,
          adoptedRunbooks: legacy.runbooks,
          parameterOverrides: legacy.overrides,
          proformaFits: legacy.fits,
          createdScenarios: Object.fromEntries(legacy.scenarios.map((sc) => [sc.id, sc])),
          trainsMade: legacy.trains,
          liveConversations: legacy.conversations,
        }
      : {}),
  };
}

/** The open project's rows as the page holds them (lib/projectState.ts). */
export function projectStateOf(s: OFState): ProjectState {
  const runbookLocks: ProjectState['runbookLocks'] = {};
  for (const r of s.runbooks) if (r.lockedAt && r.lockHash) runbookLocks[r.id] = lockOf(r.id, r.lockedAt, r.lockHash);
  return {
    depositions: s.depositions,
    measuredEvidence: s.measuredEvidence,
    runbooks: s.runbooks.filter((r) => s.adoptedRunbookIds.includes(r.id)),
    runbookLocks,
    overrides: s.parameterOverrides,
    fits: s.proformaFits,
    scenarios: s.scenarios.filter((sc) => s.createdScenarioIds.includes(sc.id)),
    trains: s.trainsMade,
    conversations: s.liveConversations,
  };
}

// One object per lock, so a runbook object that changes for another reason
// does not read as a new lock (a lock is sent once, and kept as made).
const LOCKS = new Map<string, { lockedAt: string; lockHash: string }>();
function lockOf(id: string, lockedAt: string, lockHash: string): { lockedAt: string; lockHash: string } {
  const key = `${id}\u0000${lockedAt}\u0000${lockHash}`;
  let lock = LOCKS.get(key);
  if (!lock) LOCKS.set(key, (lock = { lockedAt, lockHash }));
  return lock;
}

/** The rows a snapshot from before alpha 2.0 kept in this browser, or null when it kept none. */
function legacyStateOf(snap: DurableSnapshot): ProjectState | null {
  const state: ProjectState = {
    depositions: snap.depositions ?? [],
    measuredEvidence: snap.measuredEvidence ?? [],
    runbooks: snap.adoptedRunbooks ?? [],
    runbookLocks: snap.runbookLocks ?? {},
    overrides: overridesOfSnapshot(snap),
    fits: snap.proformaFits ?? {},
    scenarios: Object.values(snap.createdScenarios ?? {}),
    trains: snap.trainsMade ?? {},
    conversations: snap.liveConversations ?? [],
  };
  const held = Object.values(state).some((v) => (Array.isArray(v) ? v.length > 0 : Object.keys(v).length > 0));
  return held ? state : null;
}

/** The ledger the page holds, with what a snapshot still owes the service laid beside it. */
function owedLedger(ledger: Guild, owed: Guild | undefined): Guild {
  if (!owed) return ledger;
  const people = new Set(ledger.people.map((p) => p.id));
  const evidence = new Set(ledger.evidence.map((e) => e.id));
  return {
    ...ledger,
    people: [...ledger.people, ...owed.people.filter((p) => !people.has(p.id))],
    evidence: [...ledger.evidence, ...owed.evidence.filter((e) => !evidence.has(e.id))],
  };
}

let stateFlushing = false;
let stateRetry: ReturnType<typeof setTimeout> | null = null;
/** How long a project row the service did not answer waits before it is sent again. */
const STATE_RETRY_MS = 15_000;

/**
 * The Live conversations after a hydrate: those this page started since it
 * loaded, then the service's (which it lists in the order they were made),
 * newest first, one per id. Each turn's status is the service's: a turn it is
 * answering reads `running`, and one nobody is answering any longer reads
 * `interrupted` (postdoc/conversations.py).
 */
function mergeConversations(saved: LiveConversation[], current: LiveConversation[]): LiveConversation[] {
  const ids = new Set(current.map((c) => c.id));
  return [...current, ...saved.filter((c) => !ids.has(c.id)).reverse()].slice(0, MAX_LIVE_CONVERSATIONS);
}

// Every change to the open project's rows goes to the outbox and is sent
// (lib/projectState.ts); nothing is compared before the rows have loaded.
if (typeof window !== 'undefined') {
  useStore.subscribe((s, prev) => {
    if (
      !s.stateSeen ||
      !s.projectId ||
      (s.depositions === prev.depositions &&
        s.measuredEvidence === prev.measuredEvidence &&
        s.runbooks === prev.runbooks &&
        s.adoptedRunbookIds === prev.adoptedRunbookIds &&
        s.parameterOverrides === prev.parameterOverrides &&
        s.proformaFits === prev.proformaFits &&
        s.scenarios === prev.scenarios &&
        s.createdScenarioIds === prev.createdScenarioIds &&
        s.trainsMade === prev.trainsMade &&
        s.liveConversations === prev.liveConversations)
    )
      return;
    const now = projectStateOf(s);
    const owed = changes(s.stateSeen, now, s.projectId, decidedBy());
    useStore.setState(owed.length ? { stateSeen: now, stateOutbox: enqueue(s.stateOutbox, owed) } : { stateSeen: now });
    if (owed.length) void useStore.getState().flushProjectState();
  });
}

if (durableAvailable()) {
  useStore.subscribe((s, prev) => {
    if (
      s.records === prev.records &&
      s.decisionAt === prev.decisionAt &&
      s.overlay === prev.overlay &&
      s.reviewer === prev.reviewer &&
      s.guild === prev.guild &&
      s.guildPending === prev.guildPending &&
      s.guildPendingWithdrawals === prev.guildPendingWithdrawals &&
      s.guildActingId === prev.guildActingId &&
      s.learnProgress === prev.learnProgress &&
      s.stateOutbox === prev.stateOutbox &&
      s.stateLegacy === prev.stateLegacy
    )
      return;
    saveDurable(snapshotOf(s));
  });
  // A tab closing mid-run must not lose the last few hundred milliseconds.
  window.addEventListener('pagehide', flushDurable);
}

/**
 * OF-BLD-020 §5.R — what pureOS's Builder showed of one train this session
 * (`builderShown`): each part absent until the page has shown it.
 */
export interface BuilderShown {
  /** The newest run made on the page, as the service returned it. */
  run?: TrainRun | null;
  /** What the service said reading the train from a kept run's units. */
  fromRun?: { artifactId: string; answer: TrainFromRun | null; problem: string | null } | null;
  /** The train a model built that this train copies, as the service listed it. */
  copyOf?: KeptTrain | null;
  /** Whether Price this in Proforma is open. */
  pricing?: boolean;
}

/** Skills by id, for the competence engine: a lab's own skills (stage 2). */
export function skillById(skills: readonly Skill[]): Record<string, Skill> {
  return Object.fromEntries(skills.map((sk) => [sk.id, sk]));
}

/** The lab's skills, for a component: none ship with the app (ADR-010). */
export function useSkills(): Skill[] {
  return useStore((s) => s.skills);
}

/** The lab's skills by id, for a component. */
export function useSkillById(): Record<string, Skill> {
  const skills = useSkills();
  return useMemo(() => skillById(skills), [skills]);
}

/**
 * A record's display provenance. The stored `provenance` field is
 * authoritative — a curated or industry-estimate record does not become
 * 'verified' just because someone accepted it in the queue without opening the
 * source. Review promotes 'curated' → 'verified'; nothing promotes
 * 'industry-estimate'.
 */
export function provenanceOf(r: ExtractionRecord): Provenance {
  if (r.provenance === 'measured') return 'measured';
  if (r.gold) return 'gold';
  if (r.provenance === 'industry-estimate') return 'industry-estimate';
  if (r.status === 'verified') return 'verified';
  if (r.status === 'rejected') return 'unverified';
  return r.provenance ?? 'unverified';
}

/**
 * Why a record is held out of aggregate statistics, or null when nothing holds
 * it out (OF-COR-001 §16 O8 and §19). Industry estimates are not evidence, and
 * a paper reciting someone else's number is not an independent measurement —
 * counting either one overstates consensus.
 *
 * This is the reason, not just the verdict, so a screen can say which records
 * it left out of a median instead of silently dropping them. Exclusion applies
 * to the statistic only: the records stay visible in per-record tables and
 * plots, because they are real values, just not independent evidence.
 */
export type AggregateExclusion = 'rejected' | 'industry-estimate' | 'computed' | 'assumed' | 'not-primary';

export function aggregateExclusion(r: ExtractionRecord): AggregateExclusion | null {
  if (r.status === 'rejected') return 'rejected';
  if (r.provenance === 'industry-estimate') return 'industry-estimate';
  // A computed value is derived from inputs already counted on their own
  // (OF-BLD-014 E.4); counting it beside them counts them twice.
  if (r.provenance === 'computed') return 'computed';
  // A person's assumption or a model's estimate is never evidence (ADR-006).
  if (r.provenance === 'assumed') return 'assumed';
  if (r.isPrimary === false) return 'not-primary';
  return null;
}

/** Records that may enter a median, range or count-based summary. */
export function isAggregatable(r: ExtractionRecord): boolean {
  return aggregateExclusion(r) === null;
}

/** Short phrase a per-record view can print next to a held-out value. */
export const EXCLUSION_NOTE: Record<AggregateExclusion, string> = {
  rejected: 'rejected — excluded from statistics',
  'industry-estimate': 'industry estimate — excluded from statistics',
  computed: 'computed from other values — excluded from statistics',
  assumed: 'an assumption or an estimate — excluded from statistics',
  'not-primary': 'reports another study\u2019s measurement — excluded from statistics',
};

/**
 * Strength order, strongest first (OF-BLD-006 §6). 'measured' outranks 'gold'
 * because a gold-set value is a careful reading of somebody else's paper,
 * while a measured one is data this platform holds with its own conditions
 * attached.
 */
export const PROVENANCE_RANK: Record<Provenance, number> = {
  measured: 0,
  gold: 1,
  verified: 2,
  curated: 3,
  computed: 4,
  unverified: 5,
  user: 6,
  'industry-estimate': 7,
  assumed: 8,
};

export const tickClass = (p: Provenance | 'rejected'): string =>
  ({
    measured: 'tick tick-measured',
    gold: 'tick tick-gold',
    verified: 'tick tick-verified',
    curated: 'tick tick-curated',
    computed: 'tick tick-computed',
    unverified: 'tick tick-unverified',
    user: 'tick tick-user',
    'industry-estimate': 'tick tick-industry-estimate',
    assumed: 'tick tick-assumed',
    rejected: 'tick tick-rejected',
  })[p];
