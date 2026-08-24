// Single store (OF-DES-001 §13.3). All mutations flow through actions so
// provenance-affecting changes fan out to derived views in one place.
// No localStorage/sessionStorage anywhere — session-only by design (§9.5).
import { create } from 'zustand';
import type {
  ActivityEvent,
  ChatMessage,
  ClearanceStateId,
  ChatSession,
  Collection,
  Deposition,
  Deviation,
  ExtractionRecord,
  Job,
  MeasuredEvidence,
  LearnModule,
  Paper,
  Product,
  Protocol,
  Provenance,
  RecordStatus,
  ResultGrid,
  Runbook,
  RunbookStage,
  RunOutput,
  RunState,
  Scenario,
  Strain,
  TimerState,
} from '@/data/types';
import { PAPERS } from '@/data/papers';
import { RECORDS } from '@/data/records';
import { RUN_OUTPUTS } from '@/data/runOutputs';
import { STRAINS } from '@/data/strains';
import { PRODUCTS } from '@/data/products';
import { RUNBOOKS } from '@/data/runbooks';
import { PROTOCOLS } from '@/data/protocols';
import { SCENARIOS, COST_MODELS } from '@/data/scenarios';
import { MODULES } from '@/data/learn';
import { COLLECTIONS, ACTIVITY, SEED_SESSIONS } from '@/data/misc';
import { buildGrid } from '@/engine/grids';
import { toSI } from '@/engine/units';
import { runbookLockHash } from '@/engine/lock';
import { computeDeltas } from '@/engine/reconcile';
import {
  EMPTY_SNAPSHOT,
  clearDurable,
  durableAvailable,
  flushDurable,
  loadDurable,
  saveDurable,
  type DurableSnapshot,
} from '@/lib/durable';

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
  queueIndex: number;
  label: string;
}

let seq = 0;
export const nextId = (prefix: string) => `${prefix}-${++seq}`;

/** Deterministic clock-free timestamp label for audit entries. */
function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
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
   * The Durable tier (OF-BLD-006 §4.6). A deposition is a record, not a
   * session: a fermentation at hour 14 cannot be lost to a page reload.
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
  grids: Record<string, ResultGrid>;
  collections: Collection[];
  modules: LearnModule[];
  activity: ActivityEvent[];
  sessions: ChatSession[];

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
  checkpointAnswers: Record<string, boolean>;
  exports: { name: string; at: string; rows: number }[];

  ui: {
    theme: Theme;
    density: Density;
    simSpeed: number; // 1, 4, or Infinity (instant)
    reducedMotion: boolean;
    unitMode: UnitMode;
    bannerDismissed: boolean;
    paletteOpen: boolean;
    jobsOpen: boolean;
    inspectorOpen: boolean;
    sessionsOpen: boolean;
    railCollapsed: boolean;
    tourStop: number | null;
    helpOpen: boolean;
    chatMode: 'scripted' | 'live';
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
  tickJobs: (dtMs: number) => void;
  failJob: (id: string, reason: string) => void;
  clearJobs: () => void;

  // ingest
  ingestPaper: (paperId: string) => void;
  setPaperIngest: (paperId: string, status: Paper['ingest']) => void;

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
  /**
   * Blocked → research handoff (§8). Builds a research runbook that enumerates
   * around whatever fence the product is behind, and is honest when
   * enumeration would not help: a claim reciting a functional class is not
   * escaped by molecular diversity, and the runbook says so instead of
   * spending compute to find out again.
   */
  handoffToResearchRunbook: (productId: string) => string | null;
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
  setScenarioPoint: (id: string, point: Record<string, number>) => void;
  togglePin: (id: string) => void;
  duplicateScenario: (id: string) => string;

  // chat
  createSession: (title: string, scope?: ChatSession['scope']) => string;
  appendMessage: (sessionId: string, msg: ChatMessage) => void;
  updateMessage: (sessionId: string, msgId: string, patch: Partial<ChatMessage>) => void;
  pinEvidence: (sessionId: string, hits: ChatSession['pinned']) => void;

  // learn
  completeLesson: (lessonId: string) => void;
  recordCheckpoint: (qid: string, correct: boolean) => void;

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
  /** Whether this browser can persist at all — surfaced honestly in Settings. */
  durableReady: boolean;

  // misc
  logActivity: (e: ActivityEvent) => void;
  logExport: (name: string, rows: number) => void;
  addCollectionPapers: (collectionId: string, paperIds: string[]) => void;
  resetDemo: () => void;
}

/**
 * How a claim reads, per clearance state — the input to the blocked → research
 * handoff (OF-BLD-005 §8).
 *
 * The distinction that matters is what the claim RECITES. A claim reciting a
 * sequence or a structure fences a region you can walk around, and enumeration
 * is worth paying for. A claim reciting a function or an application fences the
 * job itself, and no amount of molecular diversity gets you out — the
 * cross-kingdom substitution that still infringed is the documented case. The
 * handoff therefore declines as readily as it accepts, and says which.
 */
const CLAIM_READING: Record<
  ClearanceStateId,
  { reading: string; enumerable: boolean; stages: RunbookStage[] }
> = {
  blocked: {
    reading: 'Structure-reciting — the claims name sequences, so the genus around them is enumerable',
    enumerable: true,
    stages: [
      { name: 'Homolog retrieval', status: 'running', detail: 'Cross-genus sequence search', value: null },
      { name: 'Identity-band mapping', status: 'pending', detail: 'Where the claimed band ends', value: null },
      { name: 'Activity prediction', status: 'pending', detail: null, value: null },
      { name: 'Enablement package', status: 'pending', detail: null, value: null },
    ],
  },
  'watch-variant': {
    reading: 'Core free, engineered variants fenced — the boundary is worth mapping precisely',
    enumerable: true,
    stages: [
      { name: 'Boundary map', status: 'running', detail: 'Where the fenced variants start', value: null },
      { name: 'Free-region candidates', status: 'pending', detail: null, value: null },
      { name: 'Enablement package', status: 'pending', detail: null, value: null },
    ],
  },
  'watch-process': {
    reading:
      'Process-reciting — the fence is on the route, not the molecule, so enumerating sequences would not move it',
    enumerable: false,
    stages: [
      {
        name: 'Recommendation',
        status: 'done',
        detail: 'Design around the process. Enumerating the molecule spends compute on the wrong axis.',
        value: null,
      },
    ],
  },
  unknown: {
    reading: 'Not yet assessed — classification has to happen before anything else is worth running',
    enumerable: true,
    stages: [
      { name: 'Clearance sweep', status: 'running', detail: 'Claim classification first', value: null },
      { name: 'Claim classification', status: 'pending', detail: null, value: null },
      { name: 'Recommendation', status: 'pending', detail: null, value: null },
    ],
  },
  'clear-none': {
    reading: 'No blocking claims found — there is no fence here to enumerate around',
    enumerable: false,
    stages: [
      {
        name: 'Recommendation',
        status: 'done',
        detail: 'Proceed with counsel confirmation. Enumeration compute would buy nothing.',
        value: null,
      },
    ],
  },
  'clear-expired': {
    reading: 'Foundational IP expired — the region is open and the evidence trail is the deliverable',
    enumerable: false,
    stages: [
      {
        name: 'Recommendation',
        status: 'done',
        detail: 'Proceed and document the expiry evidence. Nothing to design around.',
        value: null,
      },
    ],
  },
};

const seedGrids = (): Record<string, ResultGrid> =>
  Object.fromEntries(COST_MODELS.map((m) => [m.modelId, buildGrid(m)]));

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

const seedState = () => ({
  papers: structuredClone(PAPERS),
  records: structuredClone(RECORDS),
  runOutputs: structuredClone(RUN_OUTPUTS),
  strains: structuredClone(STRAINS),
  products: structuredClone(PRODUCTS),
  runbooks: freezeLocked(structuredClone(RUNBOOKS)),
  depositions: [] as Deposition[],
  measuredEvidence: [] as MeasuredEvidence[],
  protocols: structuredClone(PROTOCOLS),
  scenarios: structuredClone(SCENARIOS),
  collections: structuredClone(COLLECTIONS),
  modules: structuredClone(MODULES),
  activity: structuredClone(ACTIVITY),
  sessions: structuredClone(SEED_SESSIONS),
  runs: {} as Record<string, RunState>,
  activeRunId: null,
  jobs: [] as Job[],
  reviewQueue: [] as string[],
  reviewIndex: 0,
  reviewStats: { accepted: 0, rejected: 0, edited: 0, skipped: 0, gold: 0, startedAt: Date.now() },
  undoStack: [] as UndoFrame[],
  learnProgress: {} as Record<string, boolean>,
  checkpointAnswers: {} as Record<string, boolean>,
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

export const useStore = create<OFState>()((set, get) => ({
  ...seedState(),
  grids: seedGrids(),
  toasts: [],
  durableReady: false,
  ui: {
    theme: initialTheme(),
    density: 'comfortable',
    simSpeed: 1,
    reducedMotion: false,
    unitMode: 'published',
    bannerDismissed: false,
    paletteOpen: false,
    jobsOpen: false,
    inspectorOpen: true,
    sessionsOpen: true,
    railCollapsed: false,
    tourStop: null,
    helpOpen: false,
    chatMode: 'scripted',
  },

  setUI: (patch) => set((s) => ({ ui: { ...s.ui, ...patch } })),

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
    const frame: UndoFrame = {
      records: structuredClone(s.records),
      queueIndex: s.reviewIndex,
      label: action,
    };
    const stats = { ...s.reviewStats };
    const records = s.records.map((r) => {
      if (r.id !== id) return r;
      const audit = [...r.audit];
      if (action === 'accept') {
        audit.push({ at: stamp(), who: 'you', action: 'verified' });
        stats.accepted++;
        return { ...r, status: 'verified' as RecordStatus, reviewer: 'you', audit };
      }
      if (action === 'reject') {
        audit.push({ at: stamp(), who: 'you', action: `rejected — ${payload?.reason ?? 'unspecified'}` });
        stats.rejected++;
        return {
          ...r,
          status: 'rejected' as RecordStatus,
          reviewer: 'you',
          rejectReason: payload?.reason,
          audit,
        };
      }
      if (action === 'gold') {
        audit.push({ at: stamp(), who: 'you', action: 'flagged for gold set' });
        stats.gold++;
        return {
          ...r,
          status: 'verified' as RecordStatus,
          reviewer: 'you',
          gold: r.gold ?? { value: r.corrected?.value ?? r.value, unit: r.corrected?.unit ?? r.unit },
          audit,
        };
      }
      stats.skipped++;
      return r;
    });
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: stats,
      reviewIndex: Math.min(s.reviewIndex + 1, s.reviewQueue.length),
    });
  },

  editRecord: (id, value, unit) => {
    const s = get();
    const frame: UndoFrame = {
      records: structuredClone(s.records),
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
            who: 'you',
            action: 'edited value',
            from: `${r.value} ${r.unit}`,
            to: `${value} ${unit}`,
          },
        ],
      };
    });
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: { ...s.reviewStats, edited: s.reviewStats.edited + 1 },
    });
  },

  setRecordStatus: (id, status, reason) =>
    set((s) => ({
      records: s.records.map((r) =>
        r.id === id
          ? {
              ...r,
              status,
              reviewer: 'you',
              rejectReason: reason ?? r.rejectReason,
              audit: [...r.audit, { at: stamp(), who: 'you', action: `set ${status}` }],
            }
          : r,
      ),
    })),

  undoReview: () => {
    const s = get();
    const frame = s.undoStack[s.undoStack.length - 1];
    if (!frame) return;
    set({
      records: frame.records,
      reviewIndex: frame.queueIndex,
      undoStack: s.undoStack.slice(0, -1),
    });
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

  tickJobs: (dtMs) => {
    const speed = get().ui.simSpeed;
    const dt = speed === Infinity ? 1e9 : dtMs * speed;
    const finishedJobs: Job[] = [];
    set((s) => ({
      jobs: s.jobs.map((j) => {
        if (j.status !== 'running') return j;
        let { stageIndex, stageProgress } = j;
        let budget = dt;
        while (budget > 0 && stageIndex < j.stages.length) {
          const stage = j.stages[stageIndex];
          const remaining = stage.ms * (1 - stageProgress);
          if (budget >= remaining) {
            budget -= remaining;
            stageIndex += 1;
            stageProgress = 0;
          } else {
            stageProgress += budget / stage.ms;
            budget = 0;
          }
        }
        if (stageIndex >= j.stages.length) {
          const done: Job = { ...j, stageIndex: j.stages.length, stageProgress: 1, status: 'done' };
          finishedJobs.push(done);
          return done;
        }
        return { ...j, stageIndex, stageProgress };
      }),
    }));
    for (const j of finishedJobs) {
      get().toast({
        text: `${j.title} — complete`,
        kind: 'success',
        href: j.href,
        hrefLabel: j.href ? 'View' : undefined,
      });
      if (j.kind === 'ingest') {
        const paperId = j.href?.split('/').pop() ?? '';
        if (paperId) get().setPaperIngest(paperId, 'complete');
      }
    }
  },

  failJob: (id, reason) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, status: 'failed', failReason: reason } : j)),
    })),

  clearJobs: () => set((s) => ({ jobs: s.jobs.filter((j) => j.status === 'running') })),

  // ── ingest ───────────────────────────────────────────────────────────
  ingestPaper: (paperId) => {
    const paper = get().papers.find((p) => p.id === paperId);
    if (!paper) return;
    // With a real corpus, ingestion needs the source document — and this build
    // has none. Open-access entries would be fetchable with network access;
    // paywalled ones need institutional credentials. Either way the pipeline
    // halts at Fetch rather than pretending to parse something it never got.
    const fails = true;
    get().setPaperIngest(paperId, 'stage:fetch');
    const id = get().startJob({
      title: `Ingest ${paperId}`,
      kind: 'ingest',
      stages: [
        { label: 'Fetch', ms: 900 },
        { label: 'Parse', ms: 1400 },
        { label: 'Chunk', ms: 700 },
        { label: 'Embed', ms: 1100 },
        { label: 'Extract', ms: 1800 },
      ],
      href: `#/library/papers/${paperId}`,
    });
    if (fails) {
      // Scripted failure path (§8.5): halts at Parse with a specific reason.
      const speed = get().ui.simSpeed;
      const wait = speed === Infinity ? 50 : 900 / speed;
      const reason = paper.openAccess
        ? `Source not retrieved — ${paper.doi ? `DOI ${paper.doi}` : paper.pmcid ?? 'the record'} is open access, but this build makes no network requests.`
        : 'Source not retrieved — publisher requires institutional access. Fetch this one manually and re-run.';
      setTimeout(() => {
        get().failJob(id, reason);
        get().setPaperIngest(paperId, 'failed:fetch');
        get().toast({
          text: `Ingest ${paperId} halted at Fetch`,
          kind: 'error',
          href: '#/library/ingest',
          hrefLabel: 'Review',
        });
      }, wait);
    }
    get().logActivity({
      at: stamp(),
      icon: 'download',
      text: `Ingest started for ${paperId}`,
      href: `#/library/ingest`,
      provenance: 'demo',
    });
  },

  setPaperIngest: (paperId, status) =>
    set((s) => ({
      papers: s.papers.map((p) => (p.id === paperId ? { ...p, ingest: status } : p)),
    })),

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
    const speed = s.ui.simSpeed === Infinity ? 60 : s.ui.simSpeed;
    const dt = (dtMs / 1000) * speed;
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
        href: `#/protocols/${proto.id}`,
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

  handoffToResearchRunbook: (productId) => {
    const s = get();
    const product = s.products.find((p) => p.id === productId);
    if (!product) return null;

    const id = nextId('rb');
    const stages: RunbookStage[] = [
      {
        name: 'Claim classification',
        status: 'done',
        detail: CLAIM_READING[product.clearanceState].reading,
        value: null,
      },
      ...CLAIM_READING[product.clearanceState].stages,
    ];
    const enumerable = CLAIM_READING[product.clearanceState].enumerable;

    const runbook: Runbook = {
      id,
      kind: 'research',
      title: `${product.name} — enumeration around the claim`,
      status: enumerable ? 'running' : 'complete',
      stages,
      note: enumerable
        ? 'Handed off from the molecule catalogue. The industrial route is fenced, so this asks the question the fence does not cover: what else does the job, and does any of it fall outside the claim.'
        : 'Handed off from the molecule catalogue and stopped immediately, on purpose. Claim architecture, not molecular diversity, decides whether enumeration is worth paying for — and here it is not. Recorded so nobody funds the same sweep next quarter.',
      eta: enumerable ? '~3 h' : null,
      outputs: enumerable ? [] : ['Claim reading', 'Recommendation not to enumerate'],
      productId: product.id,
      progressPct: enumerable ? 18 : 100,
      estCostUsd: enumerable ? 140 : 2,
      strainId: product.defaultStrainId,
      // The prediction IS the claim being handed off. When the claim recites a
      // function rather than a sequence the honest prediction is zero escapes
      // — the same call rb-heme-calib records, reached the same way.
      predictions: [
        {
          id: `${id}-escapes`,
          label: 'Candidates falling outside the claim',
          value: enumerable ? 120 : 0,
          unit: 'candidates',
          confidence: enumerable ? 'low' : 'high',
          basis: enumerable
            ? 'Structure-reciting claim, so the genus around it is enumerable. Count is an opening estimate and is what the sweep will test.'
            : 'The claim recites a functional class rather than a sequence, so molecular diversity does not escape it.',
        },
      ],
      measurementSchema: [
        {
          id: `${id}-ms-escapes`,
          label: 'Candidates outside the claim on counsel review',
          unit: 'candidates',
          timepoint: 'analysis',
          predictionId: `${id}-escapes`,
        },
      ],
      // Locked at creation: it starts consuming compute immediately, and a
      // prediction editable after the sweep runs is not a prediction.
      lockedAt: new Date().toISOString(),
      lockHash: null,
    };
    runbook.lockHash = runbookLockHash(runbook.predictions, runbook.measurementSchema);

    set((st) => ({ runbooks: [runbook, ...st.runbooks] }));

    if (enumerable) {
      get().startJob({
        title: `Enumerating around ${product.name}`,
        kind: 'runbook',
        stages: [
          { label: 'Classify', ms: 1200 },
          { label: 'Retrieve', ms: 2600 },
          { label: 'Rank', ms: 2200 },
          { label: 'Package', ms: 1400 },
        ],
        href: `#/runbooks/${id}`,
      });
    }

    get().logActivity({
      at: stamp(),
      icon: 'runbook',
      text: enumerable
        ? `Research runbook opened — enumerating around the claims on ${product.name}`
        : `Enumeration declined for ${product.name} — the claim recites a function, not a sequence`,
      href: `#/runbooks/${id}`,
      provenance: 'user',
    });
    get().toast({
      text: enumerable
        ? `Enumerating around ${product.name}. This is a research lead, not clearance.`
        : `Enumeration would not help ${product.name} — opened the reasoning instead.`,
      kind: enumerable ? 'info' : 'warn',
      href: `#/runbooks/${id}`,
      hrefLabel: 'Open',
    });
    return id;
  },

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
      status: 'running',
      stages: [
        {
          name: 'Clearance sweep',
          status: 'done',
          detail: carried || `Carried from ${source.id}`,
          value: product?.clearanceState ?? null,
        },
        {
          name: 'Host & construct selection',
          status: 'running',
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
      eta: '~50 min',
      outputs: [],
      productId: source.productId,
      progressPct: 14,
      estCostUsd: 52,
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
      lockedAt: new Date().toISOString(),
      lockHash: null,
    };
    runbook.lockHash = runbookLockHash(runbook.predictions, runbook.measurementSchema);

    set((st) => ({ runbooks: [runbook, ...st.runbooks] }));
    get().startJob({
      title: `Industrial runbook — ${product?.name ?? source.title}`,
      kind: 'runbook',
      stages: [
        { label: 'Host', ms: 1800 },
        { label: 'Train', ms: 2400 },
        { label: 'Titre', ms: 2600 },
        { label: 'CAPEX', ms: 2000 },
      ],
      href: `#/runbooks/${id}`,
    });
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
        return { ...r, status: 'running' as const, stages, eta: '~90 min' };
      }),
    }));

    const r = get().runbooks.find((x) => x.id === runbookId);
    get().startJob({
      title: `Resuming ${r?.title ?? 'runbook'}`,
      kind: 'runbook',
      stages: [
        { label: 'Re-check', ms: 1200 },
        { label: 'Cascade', ms: 3000 },
      ],
      href: `#/runbooks/${runbookId}`,
    });
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
    // A Job with no stages would divide by zero in tickJobs, so the tray gets
    // at least one even for a runbook whose stages are all already done.
    const jobStages = r.stages
      .filter((st) => st.status !== 'done')
      .slice(0, 4)
      .map((st) => ({ label: st.name.split(' ')[0], ms: 2400 }));
    get().startJob({
      title: r.title,
      kind: 'runbook',
      stages: jobStages.length > 0 ? jobStages : [{ label: 'Run', ms: 2400 }],
      href: `#/runbooks/${runbookId}`,
    });
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
      operatorId: null, // Guild will populate this once people exist.
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
      href: `#/protocols/${protocolId}/run/${runId}`,
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
        return {
          ...d,
          entries: [
            ...d.entries,
            {
              ...original,
              id: nextId('de'),
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
      href: `#/depositions/${depositionId}`,
      provenance: 'user',
    });
  },

  // ── scenarios ────────────────────────────────────────────────────────
  setScenarioPoint: (id, point) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, point: { ...sc.point, ...point } } : sc)),
    })),

  togglePin: (id) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, pinned: !sc.pinned } : sc)),
    })),

  duplicateScenario: (id) => {
    const s = get();
    const src = s.scenarios.find((x) => x.id === id);
    if (!src) return id;
    const copy: Scenario = {
      ...structuredClone(src),
      id: nextId('sc'),
      name: `${src.name} (copy)`,
      pinned: false,
    };
    set({ scenarios: [...s.scenarios, copy] });
    return copy.id;
  },

  // ── chat ─────────────────────────────────────────────────────────────
  createSession: (title, scope) => {
    const id = nextId('sess');
    const session: ChatSession = { id, title, startedAt: stamp(), scope, messages: [], pinned: [] };
    set((s) => ({ sessions: [session, ...s.sessions] }));
    return id;
  },

  appendMessage: (sessionId, msg) =>
    set((s) => ({
      sessions: s.sessions.map((x) =>
        x.id === sessionId ? { ...x, messages: [...x.messages, msg] } : x,
      ),
    })),

  updateMessage: (sessionId, msgId, patch) =>
    set((s) => ({
      sessions: s.sessions.map((x) =>
        x.id === sessionId
          ? {
              ...x,
              messages: x.messages.map((m) =>
                m.id === msgId ? ({ ...m, ...patch } as ChatMessage) : m,
              ),
            }
          : x,
      ),
    })),

  pinEvidence: (sessionId, hits) =>
    set((s) => ({
      sessions: s.sessions.map((x) => {
        if (x.id !== sessionId) return x;
        const seen = new Set(x.pinned.map((p) => `${p.paperId}:${p.sectionId}`));
        const add = hits.filter((h) => !seen.has(`${h.paperId}:${h.sectionId}`));
        return { ...x, pinned: [...x.pinned, ...add] };
      }),
    })),

  // ── learn ────────────────────────────────────────────────────────────
  completeLesson: (lessonId) =>
    set((s) => ({ learnProgress: { ...s.learnProgress, [lessonId]: true } })),

  recordCheckpoint: (qid, correct) =>
    set((s) => ({ checkpointAnswers: { ...s.checkpointAnswers, [qid]: correct } })),

  // ── misc ─────────────────────────────────────────────────────────────
  logActivity: (e) => set((s) => ({ activity: [e, ...s.activity].slice(0, 40) })),

  logExport: (name, rows) =>
    set((s) => ({ exports: [{ name, at: stamp(), rows }, ...s.exports].slice(0, 30) })),

  addCollectionPapers: (collectionId, paperIds) =>
    set((s) => ({
      collections: s.collections.map((c) =>
        c.id === collectionId
          ? { ...c, paperIds: Array.from(new Set([...c.paperIds, ...paperIds])) }
          : c,
      ),
    })),

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
      href: `#/depositions/${depositionId}`,
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
      set({ durableReady: durableAvailable() });
      return;
    }
    set((s) => {
      // Review decisions are re-applied over the seeded records rather than
      // replacing them, so a corpus update ships new records without
      // discarding what a reviewer already decided.
      const records = s.records.map((r) => {
        const d = snap.reviewDecisions[r.id];
        return d ? { ...r, ...d } : r;
      });
      // Locks re-apply only to runbooks that still exist. A lock whose runbook
      // was created in a previous session and is not in this one is dropped —
      // a lock with nothing under it is not worth keeping.
      const runbooks = s.runbooks.map((r) => {
        const l = snap.runbookLocks[r.id];
        return l ? { ...r, lockedAt: l.lockedAt, lockHash: l.lockHash } : r;
      });
      return {
        records,
        runbooks: freezeLocked(runbooks),
        depositions: snap.depositions,
        measuredEvidence: snap.measuredEvidence ?? [],
        durableReady: durableAvailable(),
      };
    });
  },

  resetDemo: () => {
    // Clear persistence as well as memory. A reset that leaves a durable
    // snapshot behind would restore itself on the next reload, which is the
    // opposite of what the button says.
    void clearDurable();
    set({ ...seedState(), grids: seedGrids(), toasts: [] });
    get().toast({
      text: 'Workspace restored to the seeded corpus — depositions, review decisions, runs and scenario edits discarded',
      kind: 'info',
    });
  },
}));

// ── durable persistence (OF-BLD-006 §4.6) ──────────────────────────────
//
// Only the Durable tier is written. Reference data is never mutated so there
// is nothing to save, and Ephemeral UI state is deliberately excluded — a
// collapsed panel that followed you across sessions would be a bug, not a
// feature.

function snapshotOf(s: OFState): DurableSnapshot {
  const reviewDecisions: DurableSnapshot['reviewDecisions'] = {};
  for (const r of s.records) {
    // Only records a reviewer has actually touched. Persisting all 134 every
    // time would write the seed back to disk on every keystroke.
    if (r.status === 'unverified' && !r.gold && !r.corrected && !r.reviewer) continue;
    reviewDecisions[r.id] = {
      status: r.status,
      provenance: r.provenance,
      gold: r.gold,
      corrected: r.corrected,
      rejectReason: r.rejectReason,
      reviewer: r.reviewer,
    };
  }
  const runbookLocks: DurableSnapshot['runbookLocks'] = {};
  for (const r of s.runbooks) {
    if (r.lockedAt && r.lockHash) runbookLocks[r.id] = { lockedAt: r.lockedAt, lockHash: r.lockHash };
  }
  return {
    ...EMPTY_SNAPSHOT,
    savedAt: new Date().toISOString(),
    depositions: s.depositions,
    measuredEvidence: s.measuredEvidence,
    reviewDecisions,
    runbookLocks,
  };
}

if (durableAvailable()) {
  useStore.subscribe((s, prev) => {
    if (
      s.depositions === prev.depositions &&
      s.records === prev.records &&
      s.runbooks === prev.runbooks &&
      s.measuredEvidence === prev.measuredEvidence
    )
      return;
    saveDurable(snapshotOf(s));
  });
  // A tab closing mid-run must not lose the last few hundred milliseconds.
  window.addEventListener('pagehide', flushDurable);
}

// ── derived selectors ──────────────────────────────────────────────────

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
export type AggregateExclusion = 'rejected' | 'industry-estimate' | 'not-primary';

export function aggregateExclusion(r: ExtractionRecord): AggregateExclusion | null {
  if (r.status === 'rejected') return 'rejected';
  if (r.provenance === 'industry-estimate') return 'industry-estimate';
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
  unverified: 4,
  user: 5,
  'industry-estimate': 6,
  demo: 7,
};

export const tickClass = (p: Provenance | 'rejected'): string =>
  ({
    measured: 'tick tick-measured',
    gold: 'tick tick-gold',
    verified: 'tick tick-verified',
    curated: 'tick tick-curated',
    unverified: 'tick tick-unverified',
    user: 'tick tick-user',
    'industry-estimate': 'tick tick-industry-estimate',
    demo: 'tick tick-demo',
    rejected: 'tick tick-rejected',
  })[p];

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  measured: 'Measured · first-party',
  gold: 'Curated · gold set',
  verified: 'Verified against source',
  curated: 'Curated · pending source check',
  unverified: 'Extracted · unverified',
  user: 'User-entered',
  'industry-estimate': 'Industry estimate · not evidence',
  demo: 'Modeled · not measured',
};
